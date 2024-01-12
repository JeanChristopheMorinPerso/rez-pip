import os
import sys
import typing
import logging
import pathlib

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import rich
import rez.package_maker
import rez.version
import rich.markup

import rez_pip.pip
import rez_pip.rez
import rez_pip.install
import rez_pip.download
import rez_pip.exceptions

_LOG = logging.getLogger(__name__)


def pip_install_packages(
    pipPackages: typing.List[rez_pip.pip.PackageInfo],
    wheelsDir: pathlib.Path,
    installedWheelsDir: pathlib.Path,
) -> typing.Dict[importlib_metadata.Distribution, bool]:
    """
    Install the given pip packages for the given python version using their wheels.

    :param pipPackages: list of packages install.
    :param wheelsDir: filesystem path to an existing directory to use for downloading wheels
    :param installedWheelsDir: filesystem path to an existing directory to use for installing wheels
    :return:
        dict of an importlib Distribution instance for each pip package installed,
        with the information if it's a pure python package:
        ``dict[Distribution(), isPurePythonPackage]``
    """
    # TODO: Should we postpone downloading to the last minute if we can?
    _LOG.info("[bold]Downloading...")
    wheels = rez_pip.download.downloadPackages(pipPackages, str(wheelsDir))
    _LOG.info(f"[bold]Downloaded {len(wheels)} wheels")

    dists: typing.Dict[importlib_metadata.Distribution, bool] = {}

    with rich.get_console().status(
        f"[bold]Installing wheels into {installedWheelsDir!r}"
    ):
        for package, wheel in zip(pipPackages, wheels):
            _LOG.info(f"[bold]Installing {package.name}-{package.version} wheel")
            dist, isPure = rez_pip.install.installWheel(
                package, pathlib.Path(wheel), str(installedWheelsDir)
            )

            dists[dist] = isPure

    return dists


def run_full_installation(
    pipPackageNames: typing.List[str],
    pythonVersionRange: typing.Optional[str],
    pipPath: pathlib.Path,
    pipWorkArea: pathlib.Path,
    pipArgs: typing.Optional[typing.List[str]] = None,
    requirementPath: typing.Optional[typing.List[str]] = None,
    constraintPath: typing.Optional[typing.List[str]] = None,
    rezInstallPath: typing.Optional[str] = None,
    rezRelease: bool = False,
) -> typing.Dict[str, rez.package_maker.PackageMaker]:
    """
    Convert the given pip packages to rez packages compatibe with the given python versions.

    :param pipPackageNames: list of packages to install, in the syntax understood by pip.
    :param pythonVersionRange: a single or range of python versions in the rez syntax
    :param pipPath: filesystem path to the pip executable. If not provided use the bundled pip.
    :param requirementPath: optional filesystem path to an existing python requirement file.
    :param constraintPath: optional filesystem path to an existing python constraint file.
    :param rezInstallPath:
        optional filesystem path to an existing directory where to install the packages.
        Default is the "local_packages_path".
    :param rezRelease: True to release the package to the "release_packages_path"
    :param pipArgs: additional argument passed directly to pip
    :param pipWorkArea:
        filesystem path to an existing directory that can be used for pip to install packages.
    :return:
        dict of rez packages created per python version: ``{"pythonVersion": PackageMaker()}``
        Note the PackageMaker object are already "close" and written to disk.
    """
    pythonVersions = rez_pip.rez.getPythonExecutables(
        pythonVersionRange, packageFamily="python"
    )

    if not pythonVersions:
        raise rez_pip.exceptions.RezPipError(
            f'No "python" package found within the range {pythonVersionRange!r}.'
        )

    rezPackages: typing.Dict[str, rez.package_maker.PackageMaker] = {}

    for pythonVersion, pythonExecutable in pythonVersions.items():
        _LOG.info(
            f"[bold underline]Installing requested packages for Python {pythonVersion}"
        )

        wheelsDir = pipWorkArea / "wheels"
        os.makedirs(wheelsDir, exist_ok=True)

        # Suffix with the python version because we loop over multiple versions,
        # and package versions, content, etc can differ for each Python version.
        installedWheelsDir = pipWorkArea / "installed" / pythonVersion
        os.makedirs(installedWheelsDir, exist_ok=True)

        with rich.get_console().status(
            f"[bold]Resolving dependencies for {rich.markup.escape(', '.join(pipPackageNames))} (python-{pythonVersion})"
        ):
            pipPackages = rez_pip.pip.getPackages(
                pipPackageNames,
                str(pipPath),
                pythonVersion,
                os.fspath(pythonExecutable),
                requirementPath or [],
                constraintPath or [],
                pipArgs or [],
            )

        _LOG.info(
            f"Resolved {len(pipPackages)} dependencies for python {pythonVersion}"
        )

        dists = pip_install_packages(
            pipPackages=pipPackages,
            wheelsDir=wheelsDir,
            installedWheelsDir=installedWheelsDir,
        )

        distNames = [dist.name for dist in dists.keys()]

        with rich.get_console().status("[bold]Creating rez packages..."):
            for dist, package in zip(dists, pipPackages):
                isPure = dists[dist]
                rezPackage = rez_pip.rez.createPackage(
                    dist,
                    isPure,
                    rez.version.Version(pythonVersion),
                    distNames,
                    str(installedWheelsDir),
                    wheelURL=package.download_info.url,
                    prefix=rezInstallPath,
                    release=rezRelease,
                )
                rezPackages.setdefault(pythonVersion, []).append(rezPackage)

    return rezPackages
