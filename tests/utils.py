import os
import sys
import glob
import hashlib
import pathlib
import platform
import subprocess
import collections

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


def buildPackage(name: str, outputDir: str) -> pathlib.Path:
    sourcePath = os.path.join(os.path.dirname(__file__), "data", "src_packages", name)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "-w",
            ".",
            "--outdir",
            outputDir,
            "--no-isolation",
        ],
        cwd=sourcePath,
        check=True,
    )

    return pathlib.Path(glob.glob(os.path.join(outputDir, f"{name}*.whl"))[0])


class PyPIIndex:
    def __init__(self, path: pathlib.Path):
        self._path = path
        self._cache = collections.defaultdict(dict)

    @property
    def path(self) -> pathlib.Path:
        return self._path

    def getWheel(self, name: str) -> pathlib.Path:
        return next(self.path.joinpath(name).glob("*.whl"))

    def getWheelHash(self, name: str, typ="sha256") -> str:
        path = self.getWheel(name)

        cachedValue = self._cache[typ].get(path)
        if cachedValue:
            return cachedValue

        buf = bytearray(2**18)  # Reusable buffer to reduce allocations.
        view = memoryview(buf)

        digestobj = hashlib.new(typ)
        with open(path, "rb") as fd:
            while True:
                size = fd.readinto(buf)
                if size == 0:
                    break  # EOF
                digestobj.update(view[:size])

        digest = digestobj.hexdigest()
        self._cache[typ][path] = digest
        return digest
