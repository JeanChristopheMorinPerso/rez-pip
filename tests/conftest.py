import os
import re
import json
import typing
import tarfile
import zipfile
import platform
import functools
import urllib.request
import xml.etree.ElementTree

import pytest
import rez.packages
import rez.package_maker

DOWNLOAD_DIR = os.path.abspath(os.path.join("tests", "data", "_tmp_download"))


@pytest.fixture(scope="session")
def rezRepo() -> str:
    return os.path.join(os.path.dirname(__file__), "data", "rez_repo")


def downloadPythonVersion(
    version: str, printer_session: typing.Callable[[str], None]
) -> str:
    """
    Download a Python interpreter for a given version

    :param version: Python version to download.
    :param printer_session: Pytest session printer.
    :returns: Path to downloaded artifact.
    """
    try:
        os.makedirs(DOWNLOAD_DIR)
    except FileExistsError:
        pass

    url = ""

    if platform.system() == "Windows":
        url = f"https://globalcdn.nuget.org/packages/python{'2' if version[0] == '2' else ''}.{version}.nupkg"

    elif platform.system() == "Darwin":
        # Use conda packages artifacts since they are portable and don't need to
        # be installed. That's quite dirty and I'm not sure if it goes against
        # their terms of use.
        arch = "64" if platform.machine() == "x86_64" else "arm64"
        with urllib.request.urlopen(
            f"https://repo.anaconda.com/pkgs/main/osx-{arch}/"
        ) as fd:
            repodata = fd.read()

        tree = xml.etree.ElementTree.fromstring(repodata)

        versionFlter = version.replace(".", "\\.")
        regex = re.compile(rf"python-(?P<version>{versionFlter}).*\.tar\.bz2")
        for row in tree.iter("td"):
            name = next(row.itertext(), "")
            if not name:
                continue

            match = regex.match(name)
            if match:
                url = f"https://repo.anaconda.com/pkgs/main/osx-{arch}/{name}"
                break

    else:
        with urllib.request.urlopen(
            "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"
        ) as fd:
            versionsManifest = json.load(fd)

        for manifest in versionsManifest:
            if manifest["version"] == version:
                for artifact in manifest["files"]:
                    if (
                        artifact["arch"] == "x64"
                        and artifact["platform"] == platform.system().lower()
                    ):
                        url = artifact["download_url"]
                        break
                else:
                    pytest.fail(f"Failed to find URL for Python {manifest['version']}")
                break

    if not url:
        pytest.fail("URL to download Python {version} not found")

    ext = re.findall(r"\.([a-z]\w+(?:\.?[a-z0-9]+))", url.split("/")[-1])[0]
    filename = f"python-{version}-{platform.system().lower()}.{ext}"

    path = os.path.join(DOWNLOAD_DIR, filename)

    if os.path.exists(path):
        printer_session(f"Skipping {url} because {path!r} already exists")
        return path

    printer_session(f"Downloading {url} to {path!r}")
    with urllib.request.urlopen(url) as archive:
        with open(path, "wb") as targetFile:
            targetFile.write(archive.read())

    return path


@pytest.fixture(
    scope="session",
    params=[
        pytest.param("2.7.18", marks=pytest.mark.py27),
        pytest.param("3.11.3", marks=pytest.mark.py311),
    ],
)
def pythonRezPackage(
    request: pytest.FixtureRequest,
    rezRepo: str,
    printer_session: typing.Callable[[str], None],
) -> str:
    """
    Create a Python rez package and return Python version number.
    """
    version = typing.cast(str, request.param)
    archivePath = downloadPythonVersion(version, printer_session)

    # for version, archivePath in downloadPythonVersions:
    if not os.path.exists(archivePath):
        pytest.fail(f"Cannot install {archivePath!r} because it does not exist")

    if archivePath.endswith(".tar.gz"):
        openArchive = tarfile.open
    elif archivePath.endswith(".tar.bz2"):
        openArchive = functools.partial(tarfile.open, mode="r:bz2")
    elif archivePath.endswith(".nupkg"):
        openArchive = zipfile.ZipFile
    else:
        raise RuntimeError(f"{archivePath} is of unknown type")

    def make_root(variant: rez.packages.Variant, path: str) -> None:
        """Using distlib to iterate over all installed files of the current
        distribution to copy files to the target directory of the rez package
        variant
        """
        printer_session(f"Creating rez package for {archivePath} in {rezRepo!r}")
        with openArchive(archivePath) as archive:
            archive.extractall(path=os.path.join(path, "python"))

        versionLessExec = os.path.join(path, "python", "bin", f"python")
        if not os.path.exists(versionLessExec):
            if (
                int(variant.version.as_tuple()[0]) >= 3
                and platform.system() != "Windows"
            ):
                os.symlink(
                    f"{versionLessExec}{variant.version.major}",
                    versionLessExec,
                )

    with rez.package_maker.make_package(
        "python",
        rezRepo,
        make_root=make_root,
        skip_existing=True,
        warn_on_skip=False,
    ) as pkg:
        pkg.version = version

        commands = [
            "env.PATH.prepend('{root}/python/bin')",
            "env.LD_LIBRARY_PATH.prepend('{root}/python/lib')",
        ]
        if platform.system() == "Windows":
            commands = [
                "env.PATH.prepend('{root}/python/tools')",
                "env.PATH.prepend('{root}/python/tools/DLLs')",
            ]
        elif platform.system() == "Darwin":
            commands = [
                "env.PATH.prepend('{root}/python/bin')",
            ]

        pkg.commands = "\n".join(commands)

    if pkg.skipped_variants:
        printer_session(
            f"Python {version} rez package already exists at {pkg.skipped_variants[0].uri}"
        )

    return version
