# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import shutil
import logging
import pathlib
import platform
import subprocess
import contextlib
import collections.abc

import rich.logging
import pluggy
import pytest
import rez.rex
import packaging.utils
import installer.utils

import rez_pip.pip
import rez_pip.patch
import rez_pip.utils
import rez_pip.compat
import rez_pip.install
import rez_pip.plugins
import rez_pip.exceptions
from rez_pip.compat import importlib_metadata

from . import utils


def patchesPath() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "data" / "patches"


@pytest.fixture(scope="session")
def rezPipLogger() -> logging.Logger:
    handler = rich.logging.RichHandler(
        show_time=False,
        markup=True,
        show_path=False,
        console=rez_pip.utils.CONSOLE,
    )
    handler.setFormatter(logging.Formatter(fmt="%(message)s"))

    rootLogger = logging.getLogger("rez_pip")
    rootLogger.addHandler(handler)

    return rootLogger


@pytest.fixture(scope="session")
def installedWheelsPath() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "data" / "installed_wheels"


@pytest.fixture(scope="session")
def packagePath(installedWheelsPath: pathlib.Path) -> pathlib.Path:
    return installedWheelsPath / "package-a"


@pytest.fixture(scope="session")
def distInfoPath(packagePath: pathlib.Path) -> pathlib.Path:
    return packagePath / "python" / "package_a-1.0.0.post0.dist-info"


@pytest.fixture(scope="session")
def recordPath(distInfoPath: pathlib.Path) -> pathlib.Path:
    return distInfoPath / "RECORD"


@pytest.fixture(scope="session")
def relativeRecordPath(
    packagePath: pathlib.Path, recordPath: pathlib.Path
) -> pathlib.Path:
    return recordPath.relative_to(packagePath)


@pytest.fixture()
def tmpPackagePath(
    tmp_path: pathlib.Path,
    packagePath: pathlib.Path,
) -> collections.abc.Generator[pathlib.Path]:
    tmpPackage = shutil.copytree(packagePath.resolve(), tmp_path.joinpath("wheels"))
    yield tmpPackage
    shutil.rmtree(tmpPackage)


@contextlib.contextmanager
def pluginContextManager(plugin) -> collections.abc.Generator[pluggy.PluginManager]:
    manager = rez_pip.plugins.getManager()
    _ = manager.register(plugin)
    yield manager
    _ = manager.unregister(plugin)


class CleanupPlugin:
    PATH: list[str] = []
    ACTION: str = "remove"

    @rez_pip.plugins.hookimpl
    def cleanup(
        self, dist: rez_pip.compat.importlib_metadata.Distribution, path: str
    ) -> collections.abc.Sequence[rez_pip.plugins.CleanupAction]:
        if packaging.utils.canonicalize_name(dist.name) != "package-a":
            return []
        return [
            rez_pip.plugins.CleanupAction(self.ACTION, os.path.join(path, *self.PATH))
        ]


class CleanupOutOfTree(CleanupPlugin):
    PATH: list[str] = ["..", "foo"]


class CleanupSubdirectory(CleanupPlugin):
    PATH: list[str] = ["scripts"]


class CleanupFile(CleanupPlugin):
    PATH: list[str] = ["scripts", "package-a-cli"]


class CleanupUnknownAction(CleanupPlugin):
    PATH: list[str] = ["scripts", "package-a-cli"]
    ACTION: str = "unknown"


class PatchNoPatches:
    @rez_pip.plugins.hookimpl
    def patches(
        self, dist: rez_pip.compat.importlib_metadata.Distribution, path: str
    ) -> list[str]:
        return []


class PatchNotAbsolutePath:
    @rez_pip.plugins.hookimpl
    def patches(
        self, dist: rez_pip.compat.importlib_metadata.Distribution, path: str
    ) -> list[str]:
        if packaging.utils.canonicalize_name(dist.name) != "package-a":
            return []
        return ["not/absolute/path"]


class PatchPlugin:
    PATCH: str = ""

    @rez_pip.plugins.hookimpl
    def patches(
        self, dist: rez_pip.compat.importlib_metadata.Distribution, path: str
    ) -> list[str]:
        if packaging.utils.canonicalize_name(dist.name) != "package-a":
            return []
        return [str(patchesPath() / self.PATCH)]


class PatchNotFound(PatchPlugin):
    PATCH: str = "does-not-exist"


class PatchNotAPatch(PatchPlugin):
    PATCH: str = "not_a_patch"


class PatchDoesNotApply(PatchPlugin):
    PATCH: str = "patch_does_not_apply.patch"


class PatchCreatesFile(PatchPlugin):
    PATCH: str = "create_file.patch"


class PatchRemovesFile(PatchPlugin):
    PATCH: str = "remove_file.patch"


class PatchModifiesFile(PatchPlugin):
    PATCH: str = "modify_file.patch"


class TestPackageFile:
    RECORD_HASH: str = "sha256=uKaKQDGjWP6YoP-kgwHRttxpdzlvw1nmjAsaL1kIr1E"
    RECORD_SIZE: int = 642

    def test_fromPackagePath_without_metadata(self):
        packagePath = importlib_metadata.PackagePath("test/path")
        packagePath.hash = None
        packagePath.size = None
        packageFile = rez_pip.install.PackageFile.fromPackagePath(packagePath)
        assert packageFile == rez_pip.install.PackageFile("test/path")

    def test_fromPackagePath_with_metadata(self):
        packagePath = importlib_metadata.PackagePath("test/path")
        packagePath.hash = importlib_metadata.FileHash("sha256=somehash")
        packagePath.size = 42
        packageFile = rez_pip.install.PackageFile.fromPackagePath(packagePath)
        assert packageFile == rez_pip.install.PackageFile(
            "test/path", "sha256=somehash", 42
        )

    def test_fromPath(self, recordPath: pathlib.Path):
        packageFile = rez_pip.install.PackageFile.fromPath(recordPath)
        assert packageFile.file == recordPath.as_posix()
        assert packageFile.hash == self.RECORD_HASH
        assert packageFile.size == self.RECORD_SIZE

    def test_toRelativePath(
        self,
        packagePath: pathlib.Path,
        recordPath: pathlib.Path,
        relativeRecordPath: pathlib.Path,
    ):
        packageFile = rez_pip.install.PackageFile(recordPath.as_posix()).toRelativePath(
            packagePath
        )
        assert packageFile.file == relativeRecordPath.as_posix()

    def test_toRow_without_metadata(self, recordPath: pathlib.Path):
        packageFile = rez_pip.install.PackageFile(recordPath.as_posix())
        assert packageFile.toRow() == (recordPath.as_posix(), None, None)

    def test_toRow_with_metadata(self, recordPath: pathlib.Path):
        packageFile = rez_pip.install.PackageFile.fromPath(recordPath)
        assert packageFile.toRow() == (
            recordPath.as_posix(),
            self.RECORD_HASH,
            self.RECORD_SIZE,
        )

    def test_absolutePath_with_absolute_path(
        self,
        recordPath: pathlib.Path,
    ):
        packageFile = rez_pip.install.PackageFile.fromPath(recordPath)
        assert packageFile.absolutePath("foo") == recordPath.as_posix()

    def test_absolutePath_with_relative_path(
        self,
        packagePath: pathlib.Path,
        recordPath: pathlib.Path,
        relativeRecordPath: pathlib.Path,
    ):
        packageFile = rez_pip.install.PackageFile(relativeRecordPath.as_posix())
        assert packageFile.absolutePath(packagePath) == recordPath.as_posix()

    def test_isAbsolutePath_with_absolute_path(self, packagePath: pathlib.Path):
        assert rez_pip.install.PackageFile(packagePath.as_posix()).isAbsolutePath()

    def test_isAbsolutePath_with_relative_path(self, relativeRecordPath: pathlib.Path):
        assert not rez_pip.install.PackageFile(
            relativeRecordPath.as_posix()
        ).isAbsolutePath()


class TestInstallation:
    @pytest.fixture
    def tmpInstallation(
        self, tmpPackagePath: pathlib.Path
    ) -> rez_pip.install.Installation:
        return rez_pip.install.Installation(self.getPackageInfo(), str(tmpPackagePath))

    @staticmethod
    def getPackageInfo(
        name: str = "package-a", version: str = "1.0.0.post0"
    ) -> rez_pip.pip.PackageInfo:
        return rez_pip.pip.PackageInfo(
            metadata=rez_pip.pip.Metadata(name=name, version=version),
            download_info=rez_pip.pip.DownloadInfo(
                url="http://localhost/asd",
                archive_info=rez_pip.pip.ArchiveInfo("hash", {}),
            ),
            is_direct=True,
            requested=True,
        )

    def test_init(self, packagePath: pathlib.Path, distInfoPath: pathlib.Path):
        installation = rez_pip.install.Installation(
            self.getPackageInfo(), str(packagePath)
        )
        assert installation.path == str(packagePath)
        assert installation.pythonDir == os.path.join(packagePath, "python")
        assert installation.scriptsDir == os.path.join(packagePath, "scripts")
        assert installation.distInfoDir == str(distInfoPath)

        # TODO: test installation.dist
        # TODO: test installation.files

    def test_iterSourceAndDestinationFiles(self, packagePath: pathlib.Path):
        installation = rez_pip.install.Installation(
            self.getPackageInfo(), str(packagePath)
        )

        installation.files = {
            packagePath.joinpath(
                "python", "__init__.py"
            ).as_posix(): rez_pip.install.PackageFile("__init__.py"),
            packagePath.joinpath(
                "scripts", "hello_world"
            ).as_posix(): rez_pip.install.PackageFile("../scripts/hello_world"),
        }

        files = [
            (src, dest)
            for src, dest in installation.iterSourceAndDestinationFiles("/destination")
        ]

        assert files == [
            (
                packagePath.joinpath("python", "__init__.py"),
                pathlib.Path("/destination/python/__init__.py"),
            ),
            (
                packagePath.joinpath("scripts", "hello_world"),
                pathlib.Path("/destination/scripts/hello_world"),
            ),
        ]

    def test_iterSourceAndDestinationFiles_fails_with_absolute_path(
        self,
        packagePath: pathlib.Path,
    ):
        installation = rez_pip.install.Installation(
            self.getPackageInfo(), str(packagePath)
        )

        installation.files = {
            "/absolute/path": rez_pip.install.PackageFile("/absolute/path"),
        }

        with pytest.raises(
            RuntimeError, match=".* package installs file .* to an absolute path"
        ):
            for src, dst in installation.iterSourceAndDestinationFiles("/foo"):
                pass

    def test_isWheelPure(
        self, installedWheelsPath: pathlib.Path, packagePath: pathlib.Path
    ):
        installation = rez_pip.install.Installation(
            self.getPackageInfo(), str(packagePath)
        )
        assert not installation.isWheelPure()

        installation = rez_pip.install.Installation(
            self.getPackageInfo(name="multi_a", version="1.0.0"),
            str(installedWheelsPath / "multiple-dist-info"),
        )
        assert installation.isWheelPure()

    def test_findDistInfoDir_with_normalized_package_name(
        self,
        packagePath: pathlib.Path,
        distInfoPath: pathlib.Path,
    ):
        # dist-info directory matches the normalized package name
        root = str(packagePath / "python")
        assert rez_pip.install.Installation._findDistInfoDir(
            self.getPackageInfo(), root
        ) == str(distInfoPath)

    def test_findDistInfoDir_without_normalized_package_name(
        self,
        packagePath: pathlib.Path,
        distInfoPath: pathlib.Path,
    ):
        # dist-info directory does not match the normalized package name
        root = str(packagePath / "python")
        assert rez_pip.install.Installation._findDistInfoDir(
            self.getPackageInfo(version="1.0.0"), root
        ) == str(distInfoPath)

    def test_findDistInfoDir_with_no_dist_info_dir(
        self, installedWheelsPath: pathlib.Path
    ):
        root = str(installedWheelsPath / "no-dist-info" / "python")
        with pytest.raises(
            rez_pip.exceptions.RezPipError, match="Could not find a dist-info folder.*"
        ):
            _ = rez_pip.install.Installation._findDistInfoDir(
                self.getPackageInfo(name="no-dist-info", version="1.0.0"), root
            )

        # Multiple dist-info directories in a package and the dist-info
        # directories do # not match the normalized package name.
        root = str(installedWheelsPath / "multiple-dist-info" / "python")
        with pytest.raises(
            rez_pip.exceptions.RezPipError, match="Expected only one dist-info folder.*"
        ):
            _ = rez_pip.install.Installation._findDistInfoDir(
                self.getPackageInfo(name="multiple-dist-info", version="1.0.0"), root
            )

    def test_findDistInfoDir_with_multiple_dist_info_dir(
        self,
        installedWheelsPath: pathlib.Path,
    ):
        # Multiple dist-info directories in a package and the dist-info
        # directories do not match the normalized package name.
        root = str(installedWheelsPath / "multiple-dist-info" / "python")
        with pytest.raises(
            rez_pip.exceptions.RezPipError, match="Expected only one dist-info folder.*"
        ):
            _ = rez_pip.install.Installation._findDistInfoDir(
                self.getPackageInfo(name="multiple-dist-info", version="1.0.0"), root
            )

    def test_cleanup_with_file_outside_of_package(
        self, tmpInstallation: rez_pip.install.Installation
    ):
        with pluginContextManager(CleanupOutOfTree()):
            with pytest.raises(
                rez_pip.install.CleanupError,
                match="Trying to remove .* which is outside of .*",
            ):
                tmpInstallation.cleanup()

    def test_cleanup_subdirectory(self, tmpInstallation: rez_pip.install.Installation):
        with pluginContextManager(CleanupSubdirectory()):
            tmpPackagePath = pathlib.Path(tmpInstallation.path)

            assert (
                tmpPackagePath.joinpath("scripts", "package-a-cli").as_posix()
                in tmpInstallation.files
            )
            assert (
                tmpPackagePath.joinpath("scripts", "sub", "package-a-cli").as_posix()
                in tmpInstallation.files
            )

            tmpInstallation.cleanup()

            assert (
                tmpPackagePath.joinpath("scripts", "package-a-cli").as_posix()
                not in tmpInstallation.files
            )
            assert (
                tmpPackagePath.joinpath("scripts", "sub", "package-a-cli").as_posix()
                not in tmpInstallation.files
            )

    def test_cleanup_file(self, tmpInstallation: rez_pip.install.Installation):
        with pluginContextManager(CleanupFile()):
            tmpPackagePath = pathlib.Path(tmpInstallation.path)

            assert (
                tmpPackagePath.joinpath("scripts", "package-a-cli").as_posix()
                in tmpInstallation.files
            )
            assert (
                tmpPackagePath.joinpath("scripts", "sub", "package-a-cli").as_posix()
                in tmpInstallation.files
            )

            tmpInstallation.cleanup()

            assert (
                tmpPackagePath.joinpath("scripts", "package-a-cli").as_posix()
                not in tmpInstallation.files
            )
            assert (
                tmpPackagePath.joinpath("scripts", "sub", "package-a-cli").as_posix()
                in tmpInstallation.files
            )

    def test_cleanup_unknown_action(
        self, tmpInstallation: rez_pip.install.Installation
    ):
        with pluginContextManager(CleanupUnknownAction()):
            with pytest.raises(
                rez_pip.install.CleanupError, match="Unknown action: unknown"
            ):
                tmpInstallation.cleanup()

    def test_patch_no_patches(self, tmpInstallation: rez_pip.install.Installation):
        with pluginContextManager(PatchNoPatches()):
            tmpInstallation.patch()

    def test_patch_not_absolute_path(
        self, tmpInstallation: rez_pip.install.Installation
    ):
        with pluginContextManager(PatchNotAbsolutePath()):
            with pytest.raises(
                rez_pip.patch.PatchError, match=".* is not an absolute path"
            ):
                tmpInstallation.patch()

    def test_patch_not_found(self, tmpInstallation: rez_pip.install.Installation):
        with pluginContextManager(PatchNotFound()):
            with pytest.raises(
                rez_pip.patch.PatchError, match="Patch at .* does not exist"
            ):
                tmpInstallation.patch()

    def test_patch_is_not_a_patch(self, tmpInstallation: rez_pip.install.Installation):
        with pluginContextManager(PatchNotAPatch()):
            with pytest.raises(
                rez_pip.patch.PatchError, match="Could not load patch .*"
            ):
                tmpInstallation.patch()

    def test_patch_does_not_apply(
        self,
        tmpInstallation: rez_pip.install.Installation,
        rezPipLogger: logging.Logger,
    ):
        with pluginContextManager(PatchDoesNotApply()):
            with pytest.raises(
                rez_pip.patch.PatchError, match="Failed to apply patch .*"
            ):
                tmpInstallation.patch()

    def test_patch_creates_file(
        self,
        tmpInstallation: rez_pip.install.Installation,
        rezPipLogger: logging.Logger,
    ):
        with pluginContextManager(PatchCreatesFile()):
            path = pathlib.Path(tmpInstallation.path).joinpath("hello").as_posix()

            assert path not in tmpInstallation.files

            tmpInstallation.patch()

            assert path in tmpInstallation.files

    def test_patch_removes_file(
        self,
        tmpInstallation: rez_pip.install.Installation,
        rezPipLogger: logging.Logger,
    ):
        with pluginContextManager(PatchRemovesFile()):
            path = (
                pathlib.Path(tmpInstallation.path)
                .joinpath("scripts", "package-a-cli")
                .as_posix()
            )

            assert path in tmpInstallation.files

            tmpInstallation.patch()

            assert path not in tmpInstallation.files

    def test_patch_modifies_file(
        self,
        tmpInstallation: rez_pip.install.Installation,
        rezPipLogger: logging.Logger,
    ):
        with pluginContextManager(PatchModifiesFile()):
            path = (
                pathlib.Path(tmpInstallation.path)
                .joinpath("scripts", "package-a-cli")
                .as_posix()
            )

            assert path in tmpInstallation.files
            assert tmpInstallation.files[path].size == 19

            tmpInstallation.patch()

            assert path in tmpInstallation.files
            assert tmpInstallation.files[path].size == 27

    def test_finalize(self, tmpPackagePath: pathlib.Path):
        installation = rez_pip.install.Installation(
            self.getPackageInfo(), str(tmpPackagePath)
        )
        dist = installation.dist

        installation.finalize()
        # Nothing should be modified if the files are not modified
        assert installation.dist is dist

        installation.files[
            tmpPackagePath.joinpath("scripts", "hello_world").as_posix()
        ] = rez_pip.install.PackageFile("../scripts/hello_world")

        installation.finalize()
        # dist should be reloaded
        assert installation.dist is not dist

        new_installation = rez_pip.install.Installation(
            self.getPackageInfo(), str(tmpPackagePath)
        )

        # If the RECORD file was modified the new_installation should match
        assert new_installation.files == installation.files


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


@pytest.mark.integration
def test_console_scripts(
    pythonRezPackage: str, rezRepo: str, tmp_path: pathlib.Path, index: utils.PyPIIndex
):
    executable, ctx = utils.getPythonRezPackageExecutablePath(pythonRezPackage, rezRepo)

    assert executable is not None

    installPath = tmp_path / "install"
    _ = rez_pip.install.installWheel(
        rez_pip.pip.PackageInfo(
            rez_pip.pip.DownloadInfo(
                "url",
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
        str(index.getWheel("console_scripts")),
        os.fspath(installPath),
    )

    consoleScript = os.fspath(installPath / "scripts" / "console_scripts_cmd")
    if platform.system() == "Windows":
        consoleScript += ".exe"

    assert os.path.exists(consoleScript), f"{consoleScript!r} does not exists!"

    def injectEnvVars(executor: rez.rex.RexExecutor):
        executor.env.PYTHONPATH.prepend(os.fspath(installPath / "python"))

    code, stdout, _ = ctx.execute_shell(
        command=[consoleScript],
        block=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        actions_callback=injectEnvVars,
    )

    assert code == 0
    # Use dirnames to avoid having to deal with python vs python2 or python vs python3
    assert os.path.dirname(stdout) == os.path.dirname(executable), (
        f"stdout is {stdout!r} and executable is {executable!r}"
    )
