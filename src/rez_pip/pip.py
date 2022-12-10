import sys
import json
import typing
import subprocess
import dataclasses


@dataclasses.dataclass
class ArchiveInfo:
    hash: str


@dataclasses.dataclass
class DownloadInfo:
    url: str
    archive_info: str


@dataclasses.dataclass
class PackageInfo:
    download_info: DownloadInfo
    is_direct: bool
    requested: bool
    metadata: dict[str, typing.Any]

    # def __repr__(self) -> str:
    #     pass

    @property
    def name(self) -> str:
        return self.metadata["name"]

    @property
    def version(self) -> str:
        return self.metadata["version"]


def get_packages(package: str, pip: str, pythonVersion: str) -> list[PackageInfo]:
    # python pip.pyz install -q requests --dry-run --ignore-installed --python-version 2.7 --only-binary=:all: --target /tmp/asd --report -
    print(f"Resolving dependencies for {package}")
    output = subprocess.check_output(
        [
            sys.executable,
            pip,
            "install",
            "-q",
            package,
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
        packageInfo = PackageInfo(**rawPackage)
        packages.append(packageInfo)

    print(f"Resolve {len(packages)} dependencies")
    return packages
