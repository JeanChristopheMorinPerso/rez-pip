# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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
import rez_pip.plugins
import rez_pip.exceptions

if typing.TYPE_CHECKING:
    import rez_pip.compat

_LOG = logging.getLogger(__name__)


@dataclasses.dataclass
class Metadata(dataclasses_json.DataClassJsonMixin):
    """Represents metadata for a package"""

    version: str
    name: str


@dataclasses.dataclass
class ArchiveInfo(dataclasses_json.DataClassJsonMixin):
    #: Archive hash
    hash: str

    #: Archive hashes
    hashes: typing.Dict[str, str]


@dataclasses.dataclass
class DownloadInfo(dataclasses_json.DataClassJsonMixin):
    #: Download URL
    url: str

    #: Archive information
    archive_info: ArchiveInfo

    dataclass_json_config = dataclasses_json.config(
        undefined=dataclasses_json.Undefined.EXCLUDE
    )


@dataclasses.dataclass(frozen=True)
class PackageInfo(dataclasses_json.DataClassJsonMixin):
    """Represents data returned by pip for a single package"""

    #: Download information
    download_info: DownloadInfo

    #: Is this a direct dependency?
    is_direct: bool

    #: Is this a requested package?
    requested: bool

    #: Metadata about the package
    metadata: Metadata

    dataclass_json_config = dataclasses_json.config(
        undefined=dataclasses_json.Undefined.EXCLUDE
    )

    @property
    def name(self) -> str:
        """Package name"""
        return self.metadata.name

    @property
    def version(self) -> str:
        """Package version"""
        return self.metadata.version

    def isDownloadRequired(self) -> bool:
        return not self.download_info.url.startswith("file://")


@dataclasses.dataclass(frozen=True)  # Nonsense, but we have to do this here too...
class DownloadedArtifact(PackageInfo):
    """
    This is a subclass of :class:`PackageInfo`. It's used to represent a local wheel.
    It is immutable so that we can clearly express immutability in plugins.
    """

    _localPath: str

    @property
    def path(self) -> str:
        """Path to the package on disk."""
        if not self.isDownloadRequired():
            # It's a local file, so we can return the URL (without file://)
            return self.download_info.url[7:]

        return self._localPath


T = typing.TypeVar("T", PackageInfo, DownloadedArtifact)


class PackageGroup(typing.Generic[T]):
    """A group of package. The order of packages and dists must be the same."""

    #: List of packages
    packages: tuple[T, ...]

    #: List of distributions
    dists: list[rez_pip.compat.importlib_metadata.Distribution]

    # Using a tuple to make it immutable
    def __init__(self, packages: tuple[T, ...]) -> None:
        self.packages = packages
        self.dists = []

    def __str__(self) -> str:
        return "PackageGroup({})".format(
            [f"{p.name}=={p.version}" for p in self.packages]
        )

    def __repr__(self) -> str:
        return "PackageGroup({})".format(
            [f"{p.name}=={p.version}" for p in self.packages]
        )

    def __bool__(self) -> bool:
        return bool(self.packages)

    def __eq__(self, value: typing.Any) -> bool:
        """Needed for tests"""
        if not isinstance(value, PackageGroup):
            return False

        return self.packages == value.packages and self.dists == value.dists

    @property
    def downloadUrls(self) -> list[str]:
        """List of download URLs"""
        return [p.download_info.url for p in self.packages]


def getBundledPip() -> str:
    return os.path.join(os.path.dirname(rez_pip.data.__file__), "pip.pyz")


def getPackages(
    packageNames: list[str],
    pip: str,
    pythonVersion: str,
    pythonExecutable: str,
    requirements: list[str],
    constraints: list[str],
    extraArgs: list[str],
) -> list[PackageInfo]:
    rez_pip.plugins.getHook().prePipResolve(
        packages=tuple(packageNames), requirements=tuple(requirements)
    )

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
        reportContent = _readPipReport(reportPath=tmpFile)
    finally:
        os.remove(tmpFile)

    rawPackages = reportContent["install"]

    packages: list[PackageInfo] = []

    for rawPackage in rawPackages:
        packageInfo = PackageInfo.from_dict(rawPackage)
        packages.append(packageInfo)

    rez_pip.plugins.getHook().postPipResolve(packages=tuple(packages))

    return packages


def _readPipReport(reportPath: str) -> dict[str, typing.Any]:
    """
    Retrieve the json report generated by pip as json dict object.
    """
    with open(reportPath, encoding="utf-8") as reportFile:
        reportContent: dict[typing.Any, typing.Any] = json.load(reportFile)
    return reportContent
