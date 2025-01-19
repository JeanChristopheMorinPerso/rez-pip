from __future__ import annotations

import os
import re
import sys
import pathlib
import platform
import subprocess

import pytest
import rez.version
import rez.packages
import rez.resolved_context


@pytest.mark.skipif(
    platform.system() == "Darwin" and not os.environ.get("CI"),
    reason="Skipping when running locally on macOS",
)
@pytest.mark.integration
def test_python_packages(pythonRezPackage: str, rezRepo: str):
    """Test that the python rez packages created by the pythonRezPackage fixture are functional"""

    package = rez.packages.get_package("python", pythonRezPackage, paths=[rezRepo])
    assert package

    ctx = rez.resolved_context.ResolvedContext(
        [package.qualified_name], package_paths=[rezRepo]
    )

    executableName = f"python{str(package.version).split('.')[0]}"

    expectedExecutablePath = os.path.join(
        rezRepo,
        "python",
        str(package.version),
        "python",
    )

    if platform.system() == "Windows":
        executableName = "python.exe"
        expectedExecutablePath = os.path.join(expectedExecutablePath, "Library")

    expectedExecutablePath = os.path.join(expectedExecutablePath, "bin", executableName)

    code, stdout, _ = ctx.execute_shell(
        command=[executableName, "-c", "import sys; print(sys.executable)"],
        block=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert code == 0
    assert stdout.strip().lower() == expectedExecutablePath.lower()

    code, stdout, _ = ctx.execute_shell(
        command=[executableName, "--version"],
        block=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert code == 0
    assert re.findall(r"\d\.\d+\.\d+", stdout, flags=re.MULTILINE)[0] == str(
        package.version
    )


@pytest.mark.parametrize(
    "packagesToInstall,imports", [[["PySide6"], ["PySide6"]]], ids=["PySide6"]
)
def test_installs(
    pythonRezPackage: str,
    rezRepo: str,
    packagesToInstall: list[str],
    imports: list[str],
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    """End to end integration test"""
    command = [
        sys.executable,
        "-m",
        "rez_pip",
        *packagesToInstall,
        "--prefix",
        os.fspath(tmp_path),
        "--python-version",
        pythonRezPackage,
    ]

    env = {
        "REZ_PACKAGES_PATH": os.pathsep.join([rezRepo, os.fspath(tmp_path)]),
        "REZ_DISABLE_HOME_CONFIG": "1",
        "COVERAGE_PROCESS_START": os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".coveragerc"
        ),
        "PYTHONPATH": os.path.dirname(__file__),
    }
    if platform.system() == "Windows":
        # https://stackoverflow.com/a/64706392
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        # Needed for getpass.getuser to work on Windows.
        env["USERNAME"] = os.environ["USERNAME"]

    with capsys.disabled():
        subprocess.check_call(command, env=env)

    ctx = rez.resolved_context.ResolvedContext(
        packagesToInstall + [f"python-{pythonRezPackage}"],
        package_paths=[rezRepo, os.fspath(tmp_path)],
    )
    assert ctx.status == rez.resolved_context.ResolverStatus.solved

    code, stdout, stderr = ctx.execute_shell(
        command=[
            "python",
            "-c",
            f"import {','.join(imports)}; [print(i.__path__[0]) for i in [{','.join(imports)}]]",
        ],
        block=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(stdout)
    print("****")
    print(stderr)
    assert code == 0

    for path in stdout.strip().split("\n"):
        assert path.lower().startswith(
            os.fspath(tmp_path).lower()
        ), f"{path!r} does not start with {os.fspath(tmp_path)!r}"

    assert not stderr
