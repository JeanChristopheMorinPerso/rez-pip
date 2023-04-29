import os
import platform
import subprocess

import rez.packages
import rez.resolved_context
import rez.vendor.version.version


def test_python_packages(createPythonRezPackages, rezRepo: str):
    """Test that the python rez packages created by createPythonRezPackages are functional"""
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
        print("Version:", stdout)

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
