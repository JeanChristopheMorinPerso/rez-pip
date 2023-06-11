import platform

import rez.packages
import rez.resolved_context
import rez.vendor.version.version


def getPythonRezPackageExecutablePath(version: str, repo: str):
    package = rez.packages.get_package("python", version, paths=[repo])
    assert package

    ctx = rez.resolved_context.ResolvedContext(
        [package.qualified_name], package_paths=[repo]
    )

    executable = f"python{str(package.version).split('.')[0]}"
    if platform.system() == "Windows":
        executable = "python.exe"

    return ctx.which(executable), ctx
