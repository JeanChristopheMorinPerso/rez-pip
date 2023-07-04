import os
import time
import typing
import pathlib
import zipfile
import platform
import textwrap
import subprocess
import http.client
import urllib.request

import pytest
import rez.config
import rez.packages
import rez.package_bind
import rez.package_maker

from . import utils

DOWNLOAD_DIR = os.path.abspath(os.path.join("tests", "data", "_tmp_download"))


phaseReportKey = pytest.StashKey[typing.Dict[str, pytest.CollectReport]]()


# Token from https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # store test results for each phase of a call, which can
    # be "setup", "call", "teardown"
    item.stash.setdefault(phaseReportKey, {})[rep.when] = rep


@pytest.fixture(scope="session")
def index(tmpdir_factory: pytest.TempdirFactory) -> utils.PyPIIndex:
    """Build PyPI Index and return the path"""

    srcPackages = os.path.join(os.path.dirname(__file__), "data", "src_packages")

    indexPath = tmpdir_factory.mktemp("pypi_index").dirpath()

    for pkg in os.listdir(srcPackages):
        dest = indexPath.mkdir(pkg)
        utils.buildPackage(pkg, os.fspath(dest))

    return utils.PyPIIndex(pathlib.Path(indexPath.strpath))


@pytest.fixture(scope="function")
def pypi(
    printer_session: typing.Callable[[str], None],
    index: utils.PyPIIndex,
    request: pytest.FixtureRequest,
) -> typing.Generator[str, None, None]:
    """Start a PyPI instance and return the URL to talk to it."""
    port = 45678
    host = "localhost"

    proc = subprocess.Popen(
        [
            "pypi-server",
            "run",
            os.fspath(index.path),
            f"--port={port}",
            f"--host={host}",
            "--disable-fallback",
            "--log-stream=stdout",
            "--hash-algo=sha256",  # Defaults to md5
            "-v",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url = f"http://{host}:{port}"

    retries = 50
    while retries > 0:
        conn = http.client.HTTPConnection(f"{host}:{port}")
        try:
            conn.request("HEAD", "/health")
            response = conn.getresponse()
            if response is not None:
                print(response.read())
                yield url
                break
        except ConnectionRefusedError:
            time.sleep(0.1)
            retries -= 1

    proc.terminate()
    proc.wait()

    output = textwrap.indent(proc.stdout.read(), "\t\t")

    if proc.returncode and proc.returncode != -15 and platform.system() != "Windows":
        pytest.fail(
            f"pypi-server returned a non zero error code ({proc.returncode}):\n\n{proc.stdout.read()}"
        )

    if (
        request.node.stash[phaseReportKey].get("call")
        and request.node.stash[phaseReportKey]["call"].failed
    ):
        printer_session(f"pypi-server output:\n{output}")

    if not retries:
        raise RuntimeError("Failed to start pypi-server")


# Use function scope to make sure each test starts with a fresh default config
@pytest.fixture(scope="function", autouse=True)
def hardenRezConfig(tmp_path_factory: pytest.TempPathFactory):
    """Make sure that rez doesn't use any of the user configs"""

    # We can't just put None, so override with a dummy directory to make sure
    # that we don't pick up packages from anywhere else.
    tmpRepoPath = tmp_path_factory.mktemp("tmp_fake_rez_repo_do_not_use")

    # Do not load user configs
    defaultConfig = rez.config._create_locked_config(
        {
            "packages_path": [os.fspath(tmpRepoPath)],
            "release_packages_path": os.fspath(tmpRepoPath),
            "local_packages_path": os.fspath(tmpRepoPath),
        }
    )
    with rez.config._replace_config(defaultConfig):
        yield


@pytest.fixture(scope="session")
def rezRepo() -> typing.Generator[str, None, None]:
    path = os.path.join(os.path.dirname(__file__), "data", "rez_repo")

    rez.package_bind.bind_package("platform", path=path, no_deps=True, quiet=True)
    rez.package_bind.bind_package("arch", path=path, no_deps=True, quiet=True)
    rez.package_bind.bind_package("os", path=path, no_deps=True, quiet=True)

    originalConfig = rez.config.config.copy()

    rez.config.config.packages_path = [path]
    rez.config.config.release_packages_path = path
    yield path

    rez.config.config.packages_path = originalConfig.packages_path
    rez.config.config.release_packages_path = originalConfig.release_packages_path


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

    url = f"https://globalcdn.nuget.org/packages/python.{version}.nupkg"

    path = os.path.join(
        DOWNLOAD_DIR, f"python-{version}-{platform.system().lower()}.nupkg"
    )

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
        pytest.param(
            # Nuget doesn't have 3.7.16
            "3.7.9" if platform.system() == "Windows" else "3.7.16",
            marks=pytest.mark.py37,
        ),
        pytest.param(
            # Nuget doesn't have 3.9.16
            "3.9.13" if platform.system() == "Windows" else "3.9.16",
            marks=pytest.mark.py39,
        ),
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

    def make_root(variant: rez.packages.Variant, path: str) -> None:
        """Using distlib to iterate over all installed files of the current
        distribution to copy files to the target directory of the rez package
        variant
        """
        printer_session(f"Creating rez package for Python {version} in {rezRepo!r}")

        dest = os.path.join(path, "python")

        if platform.system() == "Windows":
            archivePath = downloadPythonVersion(version, printer_session)
            with zipfile.ZipFile(archivePath) as archive:
                printer_session(f"Extracting {archivePath!r} to {dest!r}")
                archive.extractall(path=dest)
        else:
            import conda.cli.python_api

            printer_session(
                f"Installing Python {version} by creating a conda environment at {dest!r}"
            )
            conda.cli.python_api.run_command(
                conda.cli.python_api.Commands.CREATE,
                "--prefix",
                dest,
                f"conda-forge:python={version}",
                "pip",
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
        ]
        if platform.system() == "Windows":
            commands = [
                "env.PATH.prepend('{root}/python/tools')",
                "env.PATH.prepend('{root}/python/tools/DLLs')",
            ]

        pkg.commands = "\n".join(commands)

    if pkg.skipped_variants:
        printer_session(
            f"Python {version} rez package already exists at {pkg.skipped_variants[0].uri}"
        )

    return version
