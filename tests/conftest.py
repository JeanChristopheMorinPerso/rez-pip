import os
import re
import json
import typing
import tarfile
import zipfile
import platform
import urllib.request

import pytest
import rez.packages
import rez.package_maker

DOWNLOAD_DIR = os.path.abspath(os.path.join("tests", "data", "_tmp_download"))

# @pytest.fixture(scope="session")
# def pypi() -> typing.Generator[str, None, None]:
#     configPath = os.path.join(os.path.dirname(__file__), "simpleindex.toml")

#     @dataclasses.dataclass
#     class ServerConfig:
#         host: str
#         port: int

#     with open(configPath, encoding="utf-8") as fd:
#         config = ServerConfig(**toml.load(fd)["server"])

#     proc = subprocess.Popen(
#         ["simpleindex", configPath],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         cwd=os.path.dirname(__file__),
#     )

#     url = f"http://{config.host}:{config.port}"

#     retries = 50
#     while retries > 0:
#         conn = http.client.HTTPConnection(f"{config.host}:{config.port}")
#         try:
#             conn.request("HEAD", "/")
#             response = conn.getresponse()
#             if response is not None:
#                 yield url
#                 break
#         except ConnectionRefusedError:
#             time.sleep(0.1)
#             retries -= 1

#     proc.terminate()
#     proc.wait()

#     if not retries:
#         raise RuntimeError("Failed to start simpleindex")


@pytest.fixture(scope="session")
def rezRepo() -> str:
    return os.path.join(os.path.dirname(__file__), "data", "rez_repo")


@pytest.fixture(scope="session")
def downloadPythonVersions(
    printer_session: typing.Callable[[str], None]
) -> typing.List[typing.Tuple[str, str]]:
    try:
        os.makedirs(DOWNLOAD_DIR)
    except FileExistsError:
        pass

    urls: typing.Dict[str, str] = {}
    versions = ["2.7.18", "3.11.3"]

    if platform.system() == "Windows":
        for version in versions:
            nugetName = "python"
            if version[0] == "2":
                nugetName += "2"
            urls[
                version
            ] = f"https://globalcdn.nuget.org/packages/{nugetName}.{version}.nupkg"

    else:
        with urllib.request.urlopen(
            "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"
        ) as fd:
            versionsManifest = json.load(fd)

        for manifest in versionsManifest:
            if manifest["version"] in versions:
                for version in manifest["files"]:
                    if (
                        version["arch"] == "x64"
                        and version["platform"] == platform.system().lower()
                    ):
                        urls[manifest["version"]] = version["download_url"]
                        break
                else:
                    pytest.fail(f"Failed to find URL for Python {manifest['version']}")

    items = []
    for version, url in urls.items():
        ext = re.findall(r"\.([a-z]\w+(?:\.?[a-z0-9]+))", url.split("/")[-1])[0]
        filename = f"python-{version}-{platform.system().lower()}.{ext}"

        path = os.path.join(DOWNLOAD_DIR, filename)

        items.append([version, path])

        if os.path.exists(path):
            printer_session(f"Skipping {url} because {path!r} already exists")
            continue

        printer_session(f"Downloading {url} to {path!r}")
        with urllib.request.urlopen(url) as archive:
            with open(path, "wb") as targetFile:
                targetFile.write(archive.read())

    return items


@pytest.fixture(scope="session")
def setupRezPackages(
    downloadPythonVersions: typing.List[typing.Tuple[str, str]],
    rezRepo: str,
    printer_session: typing.Callable[[str], None],
) -> str:
    for version, archivePath in downloadPythonVersions:
        if not os.path.exists(archivePath):
            pytest.fail(f"Cannot install {archivePath!r} because it does not exist")

        if archivePath.endswith(".tar.gz"):
            openArchive = tarfile.open
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
                    "env.DYLD_LIBRARY_PATH.prepend('{root}/python/lib')",
                ]

            pkg.commands = "\n".join(commands)

        if pkg.skipped_variants:
            printer_session(
                f"Python {version} rez package already exists at {pkg.skipped_variants[0].uri}"
            )

    return rezRepo
