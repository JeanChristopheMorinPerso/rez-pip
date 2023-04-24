import os
import glob
import tarfile
import zipfile

# import time
# import typing
# import subprocess
# import dataclasses
# import http.client

# import toml
import pytest
import rez.packages
import rez.package_maker


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
def createPythonRezPackages(rezRepo: str):
    pythonArchives = glob.glob(
        os.path.join(os.path.dirname(__file__), "data", "python", "*")
    )

    for pythonArchive in pythonArchives:
        print(f"Creating rez package for {pythonArchive} in {rezRepo!r}")

        def make_root(variant: rez.packages.Variant, path: str) -> None:
            """Using distlib to iterate over all installed files of the current
            distribution to copy files to the target directory of the rez package
            variant
            """
            if pythonArchive.endswith(".tar.gz"):
                with tarfile.open(pythonArchive) as tar:
                    tar.extractall(path=os.path.join(path, "python"))
            elif pythonArchive.endswith(".zip"):
                with zipfile.ZipFile(pythonArchive) as zipFd:
                    zipFd.extractall(path=os.path.join(path, "python"))
            else:
                raise RuntimeError(f"{pythonArchive} is of known type")

        with rez.package_maker.make_package(
            "python",
            rezRepo,
            make_root=make_root,
        ) as pkg:
            pass
            pkg.version = os.path.basename(pythonArchive).split("-")[1]

            pkg.commands = "\n".join(
                [
                    "env.PATH.prepend('{root}/python/bin')",
                    "env.LD_LIBRARY_PATH.prepend('{root}/python/lib')",
                    "env.DYLD_LIBRARY_PATH.prepend('{root}/python/lib')",
                ]
            )
