# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""
Code that takes care of installing (extracting) wheels.
"""

from __future__ import annotations

import io
import os
import re
import sys
import shutil
import typing
import logging
import pathlib
import zipfile
import sysconfig
import collections.abc

import rez_pip.exceptions

if typing.TYPE_CHECKING:
    from typing import Literal

import installer
import installer.utils
import installer.records
import installer.scripts
import installer.sources
import installer.destinations

import rez_pip.pip
import rez_pip.plugins
import rez_pip.exceptions
from rez_pip.compat import importlib_metadata

_LOG = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    LauncherKind = Literal["posix", "win-ia32", "win-amd64", "win-arm", "win-arm64"]
    ScriptSection = Literal["console", "gui"]


class CleanupError(rez_pip.exceptions.RezPipError):
    """
    Raised when a cleanup operation fails.
    """


def isWheelPure(dist: importlib_metadata.Distribution) -> bool:
    # dist.files should never be empty, but assert to silence mypy.
    assert dist.files is not None

    path = next(
        f
        for f in dist.files
        if os.fspath(f.locate()).endswith(os.path.join(".dist-info", "WHEEL"))
    )
    with open(path.locate()) as fd:
        metadata = installer.utils.parse_metadata_file(fd.read())
    return typing.cast(str, metadata["Root-Is-Purelib"]) == "true"


# Taken from https://github.com/pypa/installer/blob/main/src/installer/__main__.py#L49
def getSchemeDict(name: str, target: str) -> dict[str, str]:
    vars = {}
    vars["base"] = vars["platbase"] = installed_base = target

    schemeDict = sysconfig.get_paths(vars=vars)
    # calculate 'headers' path, not currently in sysconfig - see
    # https://bugs.python.org/issue44445. This is based on what distutils does.
    # TODO: figure out original vs normalised distribution names
    schemeDict["headers"] = os.path.join(
        sysconfig.get_path("include", vars={"installed_base": installed_base}),
        name,
    )

    if target:  # In practice this will always be set.
        schemeDict["purelib"] = os.path.join(target, "python")
        schemeDict["platlib"] = os.path.join(target, "python")
        schemeDict["headers"] = os.path.join(target, "headers", name)
        schemeDict["scripts"] = os.path.join(target, "scripts")
        # Potentiall handle data?
    return schemeDict


def installWheel(
    package: rez_pip.pip.PackageInfo,
    wheelPath: str,
    targetPath: str,
) -> importlib_metadata.Distribution:
    # TODO: Technically, target should be optional. We will always want to install in "pip install --target"
    #       mode. So right now it's a CLI option for debugging purposes.

    destination = CustomWheelDestination(
        getSchemeDict(package.name, targetPath),
        # TODO: Use Python from rez package, or simply use "/usr/bin/env python"?
        interpreter=sys.executable,
        script_kind=installer.utils.get_launcher_kind(),
    )

    _LOG.debug(f"Installing {wheelPath} into {targetPath!r}")
    with installer.sources.WheelFile.open(pathlib.Path(wheelPath)) as source:
        installer.install(
            source=source,
            destination=destination,
            # Additional metadata that is generated by the installation tool.
            additional_metadata={
                "INSTALLER": f"rez-pip {importlib_metadata.version(__package__)}".encode(
                    "utf-8"
                ),
            },
        )

    targetPathPython = os.path.join(targetPath, "python")

    # That's kind of dirty, but using any other method returns inconsistent results.
    # For example, importlib.metadata.Distribution.discover(path=['/path']) sometimes
    # won't find the freshly intalled package, even if it exists and everything.
    items = [
        item
        for item in os.listdir(targetPathPython)
        if item.endswith(".dist-info")
        and os.path.isdir(os.path.join(targetPathPython, item))
    ]

    if len(items) == 0:
        raise rez_pip.exceptions.RezPipError(
            f"Could not find a dist-info folder for {package.name!r} in {targetPathPython!r}"
        )

    elif len(items) > 1:
        raise rez_pip.exceptions.RezPipError(
            f"Expected only one dist-info folders for {package.name!r} in {targetPathPython!r}, but found {len(items)}: {items}"
        )

    dist = importlib_metadata.Distribution.at(os.path.join(targetPathPython, items[0]))

    return dist


# TODO: Document where this code comes from.
class CustomWheelDestination(installer.destinations.SchemeDictionaryDestination):
    # Exactly the same as SchemeDictionaryDestination, but uses our custom Script class.
    def write_script(
        self, name: str, module: str, attr: str, section: ScriptSection
    ) -> installer.records.RecordEntry:
        """Write a script to invoke an entrypoint.
        :param name: name of the script
        :param module: module path, to load the entry point from
        :param attr: final attribute access, for the entry point
        :param section: Denotes the "entry point section" where this was specified.
            Valid values are ``"gui"`` and ``"console"``.
        :type section: str
        - Generates a launcher using :any:`Script.generate`.
        - Writes to the "scripts" scheme.
        - Uses :py:meth:`SchemeDictionaryDestination.write_to_fs` for the
          filesystem interaction.
        """
        script = Script(name, module, attr, section)
        script_name, data = script.generate(self.interpreter, self.script_kind)

        with io.BytesIO(data) as stream:
            entry = self.write_to_fs(
                installer.utils.Scheme("scripts"),
                script_name,
                stream,
                is_executable=True,
            )

            path = self._path_with_destdir(
                installer.utils.Scheme("scripts"), script_name
            )
            mode = os.stat(path).st_mode
            mode |= (mode & 0o444) >> 2
            os.chmod(path, mode)

            return entry


_SCRIPT_TEMPLATE = """\
# -*- coding: utf-8 -*-
import re
import sys
from {module} import {import_name}
if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\\.pyw|\\.exe)?$", "", sys.argv[0])
    sys.exit({func_path}())
"""


# TODO: Document where this code comes from.
class Script(installer.scripts.Script):
    def generate(self, executable: str, kind: LauncherKind) -> tuple[str, bytes]:
        """Generate a launcher for this script.
        :param executable: Path to the executable to invoke.
        :param kind: Which launcher template should be used.
            Valid values are ``"posix"``, ``"win-ia32"``, ``"win-amd64"`` and
            ``"win-arm"``.
        :type kind: str
        :raises InvalidScript: if no appropriate template is available.
        :return: The name and contents of the launcher file.
        """
        launcher = self._get_launcher_data(kind)
        # shebang = _build_shebang(executable, forlauncher=bool(launcher))
        # TODO: Should we instead just pass that value to WheelDestination?
        shebang = b"#!/usr/bin/env python"
        code = _SCRIPT_TEMPLATE.format(
            module=self.module,
            import_name=self.attr.split(".")[0],
            func_path=self.attr,
        ).encode("utf-8")

        if launcher is None:
            return (self.name, shebang + b"\n" + code)

        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as zf:
            zf.writestr("__main__.py", code)
        name = f"{self.name}.exe"
        data = launcher + shebang + b"\n" + stream.getvalue()
        return (name, data)


def cleanup(dist: importlib_metadata.Distribution, path: str) -> None:
    """
    Run cleanup hooks.

    Note that this lives in install because the cleanups
    are made on the installs (the wheel install). We could move this somewhere
    else but it's not clear where.
    """
    actionsGroups: collections.abc.Sequence[
        collections.abc.Sequence[rez_pip.plugins.CleanupAction]
    ] = rez_pip.plugins.getHook().cleanup(
        dist=dist, path=path
    )  # type: ignore[assignment]

    # Flatten
    actions: list[rez_pip.plugins.CleanupAction] = [
        action for group in actionsGroups for action in group
    ]

    recordEntriesToRemove = []

    for action in actions:
        if not action.path.startswith(path):
            # Security measure. Only perform operations on
            # paths that are within the install path.
            raise CleanupError(
                f"Typing to {action.op} {action.path!r} which is outside of {path!r}"
            )

        if action.op == "remove":
            if not os.path.exists(action.path):
                continue

            _LOG.info(f"Removing {action.path!r}")
            if os.path.isdir(action.path):
                shutil.rmtree(action.path)
            else:
                os.remove(action.path)

            recordEntriesToRemove.append(
                os.path.normpath(os.path.relpath(action.path, path)).replace("\\", "/")
            )
        else:
            raise CleanupError(f"Unknown action: {action.op}")

    if recordEntriesToRemove:
        deleteEntryFromRecord(dist, path, recordEntriesToRemove)


def deleteEntryFromRecord(
    dist: importlib_metadata.Distribution, path: str, entries: list[str]
) -> None:
    """
    Delete an entry from the record file.

    This code is not great. I feel like updating the RECORD file should
    be simpler. Which means that we miht need to refactor things a bit.
    """
    items = [
        os.fspath(item)
        for item in dist.files
        if re.search(r"[a-zA-Z0-9._+]+\.dist-info/RECORD", os.fspath(item))
    ]

    if not items:
        raise CleanupError(f"RECORD file not found for {dist.name!r}")

    recordFilePathRel = items[0]
    recordFilePath = os.path.join(path, "python", recordFilePathRel)

    with open(recordFilePath) as f:
        lines = f.readlines()

    schemesRaw = getSchemeDict(dist.name, path)
    schemes = {
        key: os.path.relpath(value, path)
        for key, value in schemesRaw.items()
        if value.startswith(path)
    }

    # Format the entries to match the record file. This is important
    # because when we install the files, we use a custom scheme.
    # For example, we have to trim "python/" or "scripts/".
    for index, entry in enumerate(entries):
        for schemePath in schemes.values():
            if entry.startswith(schemePath):
                _LOG.debug(f"Stripping {schemePath!r}/ from {entry!r}")
                entries[index] = entry.lstrip(schemePath + "/")
                # Break on first match
                break

    for index, elements in enumerate(installer.records.parse_record_file(lines)):
        if elements[0] in entries:
            lines.pop(index)

    with open(recordFilePath, "w") as f:
        for line in lines:
            f.write(line)
