import os
import re
import sys
import uuid
import typing
import pathlib
import subprocess

import rich
import pytest

import rez_pip.pip
import rez_pip.exceptions

from . import utils


def test_getBundledPip():
    """Test that the bundled pip exists and can be executed"""
    assert os.path.exists(rez_pip.pip.getBundledPip())

    subprocess.run([sys.executable, rez_pip.pip.getBundledPip(), "-h"])


@pytest.mark.parametrize(
    "packages,expectedPackages",
    [
        [
            ["package_a"],
            [
                rez_pip.pip.PackageInfo(
                    rez_pip.pip.DownloadInfo(
                        "{pypi}/packages/package_a/package_a-1.0.0-py2.py3-none-any.whl",
                        rez_pip.pip.ArchiveInfo(
                            "sha256=<val>",
                            {"sha256": "<val>"},
                        ),
                    ),
                    False,
                    True,
                    rez_pip.pip.Metadata("1.0.0", "package_a"),
                ),
            ],
        ],
        [
            ["package_a", "console_scripts"],
            [
                rez_pip.pip.PackageInfo(
                    rez_pip.pip.DownloadInfo(
                        "{pypi}/packages/package_a/package_a-1.0.0-py2.py3-none-any.whl",
                        rez_pip.pip.ArchiveInfo(
                            "sha256=<val>",
                            {"sha256": "<val>"},
                        ),
                    ),
                    False,
                    True,
                    rez_pip.pip.Metadata("1.0.0", "package_a"),
                ),
                rez_pip.pip.PackageInfo(
                    download_info=rez_pip.pip.DownloadInfo(
                        url="{pypi}/packages/console_scripts/console_scripts-0.1.0-py2.py3-none-any.whl",
                        archive_info=rez_pip.pip.ArchiveInfo(
                            hash="sha256=<val>",
                            hashes={"sha256": "<val>"},
                        ),
                    ),
                    is_direct=False,
                    requested=True,
                    metadata=rez_pip.pip.Metadata(
                        version="0.1.0", name="console_scripts"
                    ),
                ),
            ],
        ],
    ],
    ids=["package_a", "package_a+console_scripts"],
)
def test_getPackages_no_deps(
    packages: typing.List[str],
    expectedPackages: typing.List[rez_pip.pip.PackageInfo],
    pythonRezPackage: str,
    rezRepo: str,
    pypi: str,
    index: utils.PyPIIndex,
):
    """
    This just tests that the function returns PackageInfo objects
    and it's why we use --no-deps. The scenario with dependencies
    will be tested in another test.
    """
    executable, ctx = utils.getPythonRezPackageExecutablePath(pythonRezPackage, rezRepo)
    assert executable is not None

    for expectedPackage in expectedPackages:
        expectedPackage.download_info.archive_info.hash = (
            f"sha256={index.getWheelHash(expectedPackage.name)}"
        )
        expectedPackage.download_info.archive_info.hashes = {
            "sha256": index.getWheelHash(expectedPackage.name)
        }

    resolvedPackages = rez_pip.pip.getPackages(
        packages,
        rez_pip.pip.getBundledPip(),
        "3.11",
        executable,
        [],
        [],
        ["--index-url", pypi, "-vvv", "--no-deps", "--retries=0"],
    )

    for packageInfo in expectedPackages:
        packageInfo.download_info.url = packageInfo.download_info.url.format(pypi=pypi)

    assert resolvedPackages == expectedPackages


def test_getPackages_with_deps(
    pythonRezPackage: str,
    rezRepo: str,
    pypi: str,
):
    """
    Test that we get all dependencies
    """
    executable, ctx = utils.getPythonRezPackageExecutablePath(pythonRezPackage, rezRepo)
    assert executable is not None

    resolvedPackages = rez_pip.pip.getPackages(
        ["package_a"],
        rez_pip.pip.getBundledPip(),
        "3.11",
        executable,
        [],
        [],
        ["--index-url", pypi, "-vvv", "--retries=0"],
    )

    resolvedPackageNames = [pkg.name for pkg in resolvedPackages]

    assert sorted(resolvedPackageNames) == ["package_a", "package_b"]


def test_getPackages_error(
    pythonRezPackage: str, rezRepo: str, pypi: str, tmp_path: pathlib.Path
):
    executable, ctx = utils.getPythonRezPackageExecutablePath(pythonRezPackage, rezRepo)
    assert executable is not None

    packageName = str(uuid.uuid4())

    with pytest.raises(rez_pip.exceptions.PipError) as exc:
        rez_pip.pip.getPackages(
            [packageName],
            rez_pip.pip.getBundledPip(),
            ".".join(str(i) for i in sys.version_info[:2]),
            executable,
            [],
            [],
            # Disable retries to speed up the test
            [
                # Specify index to avoid pip complaining about OpenSSL not being available.
                f"--index-url={pypi}",
                "--find-links",
                os.fspath(tmp_path),
                "-v",
                "--retries",
                "0",
            ],
        )

    with rich.get_console().capture() as capture:
        rich.get_console().print(exc.value, soft_wrap=True)

    match = re.match(
        r"rez_pip\.exceptions\.PipError: Failed to run pip command\: '.*'",
        capture.get().splitlines()[0],
    )

    assert match is not None

    # Lowercase to avoid discrepencies between C:\ and c:\
    assert (
        "\n".join(capture.get().splitlines()[1:]).lower()
        == f"""
Pip reported this:

Looking in indexes: {pypi}
Looking in links: {os.fspath(tmp_path)}
ERROR: Could not find a version that satisfies the requirement {packageName} (from versions: none)
ERROR: No matching distribution found for {packageName}""".lower()
    )
