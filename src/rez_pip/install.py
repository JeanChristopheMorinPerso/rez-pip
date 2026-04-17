# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""
Code that takes care of installing (extracting) wheels.
"""

from __future__ import annotations

import io
import os
import csv
import sys
import base64
import shutil
import typing
import hashlib
import logging
import pathlib
import zipfile
import itertools
import sysconfig
import collections.abc
import dataclasses

import packaging.utils

if typing.TYPE_CHECKING:
    from typing import Literal

import patch_ng
import installer
import installer.utils
import installer.records
import installer.scripts
import installer.sources
import installer.destinations

import rez_pip.pip
import rez_pip.patch
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


@dataclasses.dataclass(frozen=True)
class PackageFile:
    """Posix path to a package file and attributes."""

    file: str
    hash: str | None = None
    size: int | None = None

    @classmethod
    def fromPackagePath(cls, file: importlib_metadata.PackagePath) -> "PackageFile":
        """Build a PackageFile from an importlib_metadata.PackagePath."""
        return cls(
            file.as_posix(),
            f"{file.hash.mode}={file.hash.value}" if file.hash else None,
            file.size,
        )

    @classmethod
    def fromPath(cls, path: pathlib.Path) -> "PackageFile":
        """Build a PackageFile from a file on disk."""
        hasher = hashlib.sha256()
        with path.open(mode="rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        digest = base64.urlsafe_b64encode(hasher.digest()).decode("ascii").rstrip("=")

        return cls(path.resolve().as_posix(), f"sha256={digest}", path.stat().st_size)

    def toRelativePath(self, prefix: str) -> "PackageFile":
        """If the path is an absolute path, convert to its relative path from `prefix`."""
        if self.isAbsolutePath():
            try:
                return PackageFile(
                    pathlib.PurePath(os.path.relpath(self.file, prefix)).as_posix(),
                    self.hash,
                    self.size,
                )
            except ValueError:
                return self

        return self

    def toRow(self) -> tuple[str, str | None, int | None]:
        """Convert to a row suitable for writing to a csv file."""
        return self.file, self.hash, self.size

    def absolutePath(self, prefix: str) -> str:
        """Get the absolute posix path to the package file."""
        if self.isAbsolutePath():
            return pathlib.Path(self.file).resolve().as_posix()
        return pathlib.Path(os.path.join(prefix, self.file)).resolve().as_posix()

    def isAbsolutePath(self) -> bool:
        """Check if this package file is an absolute path."""
        return os.path.isabs(self.file)


class Installation:
    def __init__(self, package: rez_pip.pip.PackageInfo, installationPrefix: str):
        self.path: str = installationPrefix
        self.root: str = os.path.join(installationPrefix, "python")
        self.pythonDir: str = self.root
        self.scriptsDir: str = os.path.join(installationPrefix, "scripts")
        self.distInfoDir: str = self._findDistInfoDir(package, self.root)
        self.dist: importlib_metadata.PathDistribution = (
            importlib_metadata.Distribution.at(self.distInfoDir)
        )

        # Make sure files are relative to the distribution
        files = [
            PackageFile.fromPackagePath(file).toRelativePath(self.root)
            for file in self.dist.files or []
        ]
        self.files: dict[str, PackageFile] = {
            file.absolutePath(self.root): file for file in files
        }

    def iterSourceAndDestinationFiles(
        self, destinationPath: str
    ) -> collections.abc.Iterator[tuple[pathlib.Path, pathlib.Path]]:
        # Files are relative to the python directory
        installRoot = os.path.join(destinationPath, "python")

        for srcPath, relativeDstPath in self.files.items():
            if relativeDstPath.isAbsolutePath():
                raise RuntimeError(
                    f"{self.dist.name} package installs file {relativeDstPath.file!r} to an absolute path"
                )
            dstPath = pathlib.Path(relativeDstPath.absolutePath(installRoot))
            yield pathlib.Path(srcPath), dstPath

    def isWheelPure(self) -> bool:
        """
        Check if this installation is python only.
        """
        with open(os.path.join(self.distInfoDir, "WHEEL")) as fd:
            metadata = installer.utils.parse_metadata_file(fd.read())
        return bool(metadata["Root-Is-Purelib"] == "true")

    def cleanup(self) -> None:
        """Run cleanup hooks.

        Note that this lives in install because the cleanups
        are made on the installation (the wheel install).
        """
        actions: itertools.chain[rez_pip.plugins.CleanupAction] = (
            itertools.chain.from_iterable(
                rez_pip.plugins.getHook().cleanup(dist=self.dist, path=self.path)  # type: ignore[arg-type]
            )
        )

        for action in actions:
            actionPath = os.path.normpath(action.path)
            # Security measure. Only perform operations on paths that are within the install path.
            try:
                if os.path.commonpath([self.path, actionPath]) != self.path:
                    raise CleanupError(
                        f"Typing to {action.op} {action.path!r} which is outside of {self.path!r}"
                    )
            except ValueError as err:
                raise CleanupError(
                    f"Typing to {action.op} {action.path!r} which is outside of {self.path!r}"
                ) from err

            if action.op == "remove":
                self._removePath(actionPath)
            else:
                raise CleanupError(f"Unknown action: {action.op}")

    def patch(self) -> None:
        """Run patch hooks.

        Note that this lives in install because the patches
        are made on the installation (the wheel install).
        """
        _LOG.debug(f"[bold]Attempting to patch {self.dist.name!r} at {self.path!r}")

        patches: list[str] = list(
            itertools.chain.from_iterable(
                rez_pip.plugins.getHook().patches(dist=self.dist, path=self.path)
            )
        )
        if not patches:
            _LOG.debug("No patches found")
            return

        _LOG.info(
            f"Applying {len(patches)} patches for {self.dist.name!r} at {self.path!r}"
        )

        for patch in patches:
            _LOG.info(f"Applying patch {patch!r} on {self.path!r}")

            if not os.path.isabs(patch):
                raise rez_pip.patch.PatchError(f"{patch!r} is not an absolute path")

            if not os.path.exists(patch):
                raise rez_pip.patch.PatchError(f"Patch at {patch!r} does not exist")

            patchset = patch_ng.fromfile(patch)
            if not patchset:
                raise rez_pip.patch.PatchError(f"Could not load {patch!r}")

            with rez_pip.patch.logIfErrorOrRaises():
                if not patchset.apply(root=self.path):
                    # A logger that only gets flushed on demand would be better...
                    raise rez_pip.patch.PatchError(
                        f"Failed to apply patch {patch!r} on {self.path!r}"
                    )

            for item in typing.cast("list[patch_ng.Patch]", patchset.items):
                if not item.target:
                    continue
                target = item.target.decode()
                if "dev/null" in pathlib.PurePath(target).as_posix():
                    # The patch removed a file
                    if not item.source:
                        continue
                    source = item.source.decode()
                    fullPath = pathlib.Path(self.path) / source
                    _ = self.files.pop(fullPath.as_posix(), None)
                else:
                    # The patch created or modified a file
                    fullPath = pathlib.Path(self.path) / target
                    if not fullPath.is_file() or fullPath.is_symlink():
                        return

                    packageFile = PackageFile.fromPath(fullPath)
                    self.files[packageFile.absolutePath(self.root)] = (
                        packageFile.toRelativePath(self.root)
                    )

    def finalize(self) -> None:
        """Update distribution if any files have been modified."""

        # Do not remap to relative path.  We want to know if any files changed from an absolute path.
        packageFiles = [
            PackageFile.fromPackagePath(file) for file in self.dist.files or []
        ]
        files = {file.absolutePath(self.root): file for file in packageFiles}
        if files != self.files:
            _LOG.debug(f"Updating distribution info in {self.distInfoDir!r}")
            with open(
                os.path.join(self.distInfoDir, "RECORD"),
                "w",
                newline="",
                encoding="utf-8",
            ) as recordFile:
                writer = csv.writer(
                    recordFile, delimiter=",", quotechar='"', lineterminator="\n"
                )
                for file in self.files.values():
                    writer.writerow(file.toRow())
            # Reload the distribution with updated files
            self.dist = importlib_metadata.Distribution.at(self.distInfoDir)

    @staticmethod
    def _findDistInfoDir(package: rez_pip.pip.PackageInfo, root: str) -> str:
        # https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-dist-info-directory
        packageName = packaging.utils.canonicalize_name(package.name).replace("-", "_")

        distInfoPath = os.path.join(root, f"{packageName}-{package.version}.dist-info")
        if os.path.isdir(distInfoPath):
            return distInfoPath

        packageVersion = packaging.utils.canonicalize_version(package.version)
        distInfoPath = os.path.join(root, f"{packageName}-{packageVersion}.dist-info")
        if os.path.isdir(distInfoPath):
            return distInfoPath

        # Fallback to walking the filesystem
        distInfoDirs = [
            path
            for path in os.listdir(root)
            if path.endswith(".dist-info") and os.path.isdir(os.path.join(root, path))
        ]

        if len(distInfoDirs) == 0:
            raise rez_pip.exceptions.RezPipError(
                f"Could not find a dist-info folder for {package.name!r} in {root!r}"
            )

        if len(distInfoDirs) > 1:
            raise rez_pip.exceptions.RezPipError(
                f"Expected only one dist-info folders for {package.name!r} in {root!r}, but found {len(distInfoDirs)}"
            )

        return os.path.join(root, distInfoDirs[0])

    def _removePath(self, path: str) -> None:
        if not os.path.exists(path):
            return

        _LOG.info(f"Removing {path!r}")
        if os.path.isdir(path):
            for dirpath, _, filenames in os.walk(path):
                directory = pathlib.Path(dirpath)
                for filename in filenames:
                    _ = self.files.pop(directory.joinpath(filename).as_posix(), None)
            shutil.rmtree(path)
        else:
            _ = self.files.pop(pathlib.Path(path).as_posix(), None)
            os.remove(path)


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
        # Potential handle data?
    return schemeDict


def installWheel(
    package: rez_pip.pip.PackageInfo,
    wheelPath: str,
    targetPath: str,
) -> Installation:
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

    return Installation(package, targetPath)


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
