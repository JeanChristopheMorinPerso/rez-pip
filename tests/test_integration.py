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

        code, stdout, _ = ctx.execute_shell(
            command=[f"python{str(package.version).split('.')[0]}", "--version"],
            block=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        assert code == 0
        assert stdout.decode("utf-8").strip().split(" ")[-1] == str(package.version)
