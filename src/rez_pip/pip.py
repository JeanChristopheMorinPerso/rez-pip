import os
import sys
import json
import typing
import logging
import tempfile
import itertools
import subprocess
import dataclasses

import dataclasses_json

import rez_pip.data
import rez_pip.exceptions

_LOG = logging.getLogger(__name__)


@dataclasses.dataclass
class Metadata(dataclasses_json.DataClassJsonMixin):
    version: str
    name: str


@dataclasses.dataclass
class ArchiveInfo(dataclasses_json.DataClassJsonMixin):
    hash: str
    hashes: typing.Dict[str, str]


@dataclasses.dataclass
class DownloadInfo(dataclasses_json.DataClassJsonMixin):
    url: str
    archive_info: ArchiveInfo

    dataclass_json_config = dataclasses_json.config(  # type: ignore
        undefined=dataclasses_json.Undefined.EXCLUDE
    )


@dataclasses.dataclass
class PackageInfo(dataclasses_json.DataClassJsonMixin):
    download_info: DownloadInfo
    is_direct: bool
    requested: bool
    metadata: Metadata

    dataclass_json_config = dataclasses_json.config(  # type: ignore
        undefined=dataclasses_json.Undefined.EXCLUDE
    )

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version


def getBundledPip() -> str:
    return os.path.join(os.path.dirname(rez_pip.data.__file__), "pip.pyz")


def getPackages(
    packageNames: typing.List[str],
    pip: str,
    pythonVersion: str,
    pythonExecutable: str,
    requirements: typing.List[str],
    constraints: typing.List[str],
    extraArgs: typing.List[str],
) -> typing.List[PackageInfo]:
    # python pip.pyz install -q requests --dry-run --ignore-installed --python-version 2.7 --only-binary=:all: --target /tmp/asd --report -

    _fd, tmpFile = tempfile.mkstemp(prefix="pip-install-output", text=True)
    os.close(_fd)
    # We can't with "with" (context manager) because it will fail on Windows.
    # Windows doesn't allow two different processes to write if the file is
    # already opened.
    try:
        command = [
            # We need to use the real interpreter because pip can't resolve
            # markers correctly even if --python-version is provided.
            # See https://github.com/pypa/pip/issues/11664.
            pythonExecutable,
            pip,
            "install",
            "-q",
            *packageNames,
            *list(itertools.chain(*zip(["-r"] * len(requirements), requirements))),
            *list(itertools.chain(*zip(["-c"] * len(constraints), constraints))),
            "--disable-pip-version-check",
            "--dry-run",
            "--ignore-installed",
            f"--python-version={pythonVersion}" if pythonVersion else "",
            "--only-binary=:all:",
            "--target=/tmp/asd",
            "--disable-pip-version-check",
            "--report",  # This is the "magic". Pip will generate a JSON with all the resolved URLs.
            tmpFile,
            *extraArgs,
        ]

        _LOG.debug(f"Running {' '.join(command)!r}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        pipOutput = []
        while True:
            stdout = typing.cast(typing.IO[str], process.stdout).readline()
            if process.poll() is not None:
                break
            if stdout:
                pipOutput.append(stdout.rstrip())
                sys.stdout.write(stdout)

        if process.poll() != 0:
            output = "\n".join(pipOutput)
            raise rez_pip.exceptions.PipError(
                f"[bold red]Failed to run pip command[/]: {' '.join(command)!r}\n\n"
                "[bold]Pip reported this[/]:\n\n"
                f"{output}",
            )

        with open(tmpFile, "r") as fd:
            rawData = json.load(fd)
    finally:
        os.remove(tmpFile)

    rawPackages = rawData["install"]

    packages: typing.List[PackageInfo] = []

    for rawPackage in rawPackages:
        packageInfo = PackageInfo.from_dict(rawPackage)
        packages.append(packageInfo)

    return packages
