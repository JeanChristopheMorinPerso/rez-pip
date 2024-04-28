"""
Code that takes care of installing (extracting) wheels.
"""

import io
import os
import sys
import typing
import zipfile
import logging
import pathlib
import sysconfig

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

if typing.TYPE_CHECKING:
    if sys.version_info >= (3, 8):
        from typing import Literal
    else:
        from typing_extensions import Literal

import installer
import installer.utils
import installer.records
import installer.scripts
import installer.sources
import installer.destinations

import rez_pip.pip

_LOG = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    LauncherKind = Literal["posix", "win-ia32", "win-amd64", "win-arm", "win-arm64"]
    ScriptSection = Literal["console", "gui"]


def isWheelPure(source: installer.sources.WheelSource) -> bool:
    stream = source.read_dist_info("WHEEL")
    metadata = installer.utils.parse_metadata_file(stream)
    return typing.cast(str, metadata["Root-Is-Purelib"]) == "true"


# Taken from https://github.com/pypa/installer/blob/main/src/installer/__main__.py#L49
def getSchemeDict(name: str, target: str) -> typing.Dict[str, str]:
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
    wheelPath: pathlib.Path,
    targetPath: str,
) -> typing.Tuple[importlib_metadata.Distribution, bool]:
    # TODO: Technically, target should be optional. We will always want to install in "pip install --target"
    #       mode. So right now it's a CLI option for debugging purposes.

    destination = CustomWheelDestination(
        getSchemeDict(package.name, targetPath),
        # TODO: Use Python from rez package, or simply use "/usr/bin/env python"?
        interpreter=sys.executable,
        script_kind=installer.utils.get_launcher_kind(),
    )

    isPure = True
    _LOG.debug(f"Installing {wheelPath} into {targetPath!r}")
    with installer.sources.WheelFile.open(wheelPath) as source:
        isPure = isWheelPure(source)

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
    path = os.path.join(
        targetPathPython,
        f"{package.name.replace('-', '_')}-{package.version}.dist-info",
    )
    dist = importlib_metadata.Distribution.at(path)

    if not dist.files:
        path = os.path.join(
            targetPathPython,
            # Some packages like sphinx will have have a sphinx.dist-info instead of Sphinx.dist-info.
            f"{package.name.replace('-', '_').lower()}-{package.version}.dist-info",
        )
        dist = importlib_metadata.Distribution.at(path)
        if not dist.files:
            raise RuntimeError(f"{path!r} does not exist!")

    return dist, isPure


# TODO: Document where this code comes from.
class CustomWheelDestination(installer.destinations.SchemeDictionaryDestination):
    # Exactly the same as SchemeDictionaryDestination, but uses our custom Script class.
    def write_script(
        self, name: str, module: str, attr: str, section: "ScriptSection"
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
    def generate(
        self, executable: str, kind: "LauncherKind"
    ) -> typing.Tuple[str, bytes]:
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
