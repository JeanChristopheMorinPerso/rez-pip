import os
import platform
import subprocess

import pytest
import rez.packages
import rez.resolved_context
import rez.vendor.version.version


@pytest.mark.skipif(
    platform.system() == "Darwin" and not os.environ.get("CI"),
    reason="Skipping when running locally on macOS",
)
@pytest.mark.integration
def test_python_packages(setupRezPackages: str):
    """Test that the python rez packages created by createPythonRezPackages are functional"""
    rezRepo = setupRezPackages

    packages = list(rez.packages.iter_packages("python", paths=[rezRepo]))
    assert sorted([str(package.version) for package in packages]) == [
        "2.7.18",
        "3.11.3",
    ]

    for package in packages:
        ctx = rez.resolved_context.ResolvedContext(
            [package.qualified_name], package_paths=[rezRepo]
        )

        executable = f"python{str(package.version).split('.')[0]}"
        if platform.system() == "Windows":
            executable = "python.exe"

        code, stdout, _ = ctx.execute_shell(
            command=[executable, "--version"],
            block=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        assert code == 0
        assert stdout.decode("utf-8").strip().split(" ")[-1] == str(package.version)

        code, stdout, _ = ctx.execute_shell(
            command=[executable, "-c", "import sys; print(sys.executable)"],
            block=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        expectedPath = os.path.join(
            rezRepo,
            "python",
            str(package.version),
            "python",
            "tools" if platform.system() == "Windows" else "bin",
            executable,
        )

        assert code == 0
        assert stdout.decode("utf-8").strip().lower() == expectedPath.lower()
