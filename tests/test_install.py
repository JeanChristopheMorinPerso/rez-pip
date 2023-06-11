import os
import sys
import glob
import pathlib
import platform
import subprocess

import pytest
import installer.utils

import rez_pip.pip
import rez_pip.install

from . import utils


def test_installer_schemes():
    # Make sure we support all schemes and also future prrof in case installer adds
    # new schesm to its supported list of schemes.
    assert installer.utils.SCHEME_NAMES == (
        "purelib",
        "platlib",
        "headers",
        "scripts",
        "data",
    )


# @pytest.fixture(scope="module")
def buildPackage(name: str, outputDir: str):
    sourcePath = os.path.join(os.path.dirname(__file__), "data", "src_packages", name)

    subprocess.run(
        [sys.executable, "-m", "build", "-w", ".", "--outdir", outputDir],
        cwd=sourcePath,
        check=True,
    )

    return glob.glob(os.path.join(outputDir, "*.whl"))[0]


@pytest.mark.integration
def test_console_scripts(pythonRezPackage: str, rezRepo: str, tmp_path: pathlib.Path):
    executable, ctx = utils.getPythonRezPackageExecutablePath(pythonRezPackage, rezRepo)

    wheel = buildPackage("console_scripts", str(tmp_path / "wheels"))

    installPath = tmp_path / "install"
    rez_pip.install.installWheel(
        rez_pip.pip.PackageInfo(
            rez_pip.pip.DownloadInfo(
                f"url",
                rez_pip.pip.ArchiveInfo(
                    "sha256=af266720050a66c893a6096a2f410989eeac74ff9a68ba194b3f6473e8e26171",
                    {
                        "sha256": "af266720050a66c893a6096a2f410989eeac74ff9a68ba194b3f6473e8e26171"
                    },
                ),
            ),
            False,
            True,
            rez_pip.pip.Metadata("0.1.0", "console_scripts"),
        ),
        wheel,
        os.fspath(installPath),
    )

    consoleScript = os.fspath(installPath / "scripts" / "console_scripts_cmd")
    if platform.system() == "Windows":
        consoleScript += ".exe"

    assert os.path.exists(consoleScript), f"{consoleScript!r} does not exists!"

    code, stdout, _ = ctx.execute_shell(
        command=[consoleScript],
        block=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        parent_environ={"PYTHONPATH": os.fspath(installPath / "python")},
        text=True,
    )

    # Use dirnames to avoid having to deal woth python vs python2 or python vs python3
    assert os.path.dirname(stdout) == os.path.dirname(
        executable
    ), f"stdout is {stdout!r} and executable is {executable!r}"
