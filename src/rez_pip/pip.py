import sys
import json
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
    packages: list[str], pip: str, pythonVersion: str
) -> list[PackageInfo]:
    # python pip.pyz install -q requests --dry-run --ignore-installed --python-version 2.7 --only-binary=:all: --target /tmp/asd --report -
    output = subprocess.check_output(
        [
            sys.executable,
            pip,
            "install",
            "-q",
            *packages,
            "--dry-run",
            "--ignore-installed",
            f"--python-version={pythonVersion}" if pythonVersion else "",
            "--only-binary=:all:",
            "--target=/tmp/asd",
            "--report",
            "-",
        ]
    )

    rawData = json.loads(output)
    rawPackages = rawData["install"]

    packages: list[PackageInfo] = []

    for rawPackage in rawPackages:
        packageInfo = PackageInfo.from_dict(rawPackage)
        packages.append(packageInfo)

    return packages
