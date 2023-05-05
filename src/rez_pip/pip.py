import json
import shlex
import typing
import logging
import subprocess
import dataclasses

import dataclasses_json
import packaging.metadata

_LOG = logging.getLogger(__name__)


@dataclasses.dataclass
class ArchiveInfo(dataclasses_json.DataClassJsonMixin):
    hash: str


@dataclasses.dataclass
class DownloadInfo(dataclasses_json.DataClassJsonMixin):
    url: str
    archive_info: str


@dataclasses.dataclass
class PackageInfo(dataclasses_json.DataClassJsonMixin):
    download_info: DownloadInfo
    is_direct: bool
    requested: bool
    metadata: packaging.metadata.RawMetadata

    @property
    def name(self) -> str:
        return self.metadata["name"]

    @property
    def version(self) -> str:
        return self.metadata["version"]


def get_packages(
    packageNames: typing.List[str], pip: str, pythonVersion: str, pythonExecutable: str
) -> typing.List[PackageInfo]:
    # python pip.pyz install -q requests --dry-run --ignore-installed --python-version 2.7 --only-binary=:all: --target /tmp/asd --report -

    command = [
        pythonExecutable,
        pip,
        "install",
        "-q",
        *packageNames,
        "--dry-run",
        "--ignore-installed",
        f"--python-version={pythonVersion}" if pythonVersion else "",
        "--only-binary=:all:",
        "--target=/tmp/asd",
        "--disable-pip-version-check",
        "--report",
        "-",
    ]

    _LOG.debug(f"Running {shlex.join(command)!r}")
    output = subprocess.check_output(command)

    rawData = json.loads(output)
    rawPackages = rawData["install"]

    packages: typing.List[PackageInfo] = []

    for rawPackage in rawPackages:
        packageInfo = PackageInfo.from_dict(rawPackage)
        packages.append(packageInfo)

    return packages
