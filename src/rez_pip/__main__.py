import os
import sys
import shutil
import typing
import logging
import argparse
import pathlib
import tempfile

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import rich
import rich.markup
import rich.logging
import rez.vendor.version.version

import rez_pip.pip
import rez_pip.rez
import rez_pip.data
import rez_pip.install
import rez_pip.download

_LOG = logging.getLogger("rez_pip")


def run() -> None:
    handler = rich.logging.RichHandler(show_time=False, markup=True, show_path=False)
    handler.setFormatter(logging.Formatter(fmt="%(message)s"))
    _LOG.addHandler(handler)
    _LOG.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("packages", nargs="+", help="Package to install")
    parser.add_argument(
        "--target", required=True, metavar="path", help="Target directory"
    )
    parser.add_argument("--install-path", help="Technically this should be --target")

    parser.add_argument(
        "--python-version",
        metavar="version",
        help="Range of python versions. It can also be a single version or 'latest'",
    )
    parser.add_argument(
        "--pip",
        default=os.path.join(os.path.dirname(rez_pip.data.__file__), "pip.pyz"),
        metavar="path",
        help="Standalone pip (https://pip.pypa.io/en/stable/installation/#standalone-zip-application)",
    )

    parser.add_argument("-d", "--debug", action="store_true")

    args = parser.parse_args()

    if args.debug:
        _LOG.setLevel(logging.DEBUG)

    # TODO: The temporary directory will be automatically deleted.
    # We should add an option to keep temporary files.
    # I also would like a structure like:
    #   /<temp dir>/
    #     /wheels/
    #     /install/
    # This would solve the problem with --target and --install-path
    # and would allow to just use --target to set the path where the rez packages will
    # be installed.

    pythonVersions = rez_pip.rez.getPythonExecutables(
        args.python_version, packageFamily="python"
    )

    for pythonVersion, pythonExecutable in pythonVersions.items():
        with tempfile.TemporaryDirectory(prefix="rez-pip") as tempDir:
            with rich.get_console().status(
                f"[bold]Resolving dependencies for {rich.markup.escape(', '.join(args.packages))} (python-{pythonVersion})"
            ):
                packages = rez_pip.pip.get_packages(
                    args.packages, args.pip, pythonVersion, pythonExecutable
                )

            _LOG.info(f"Resolved {len(packages)} dependencies")

            # TODO: Should we postpone downloading to the last minute if we can?
            _LOG.info("[bold]Downloading...")
            wheels = rez_pip.download.downloadPackages(packages, tempDir)
            _LOG.info(f"[bold]Downloaded {len(wheels)} wheels")

            dists: typing.Dict[importlib_metadata.Distribution, bool] = {}

            with rich.get_console().status(
                f"[bold]Installing wheels into {args.target!r}"
            ):
                for package, wheel in zip(packages, wheels):
                    _LOG.info(
                        f"[bold]Installing {package.name}-{package.version} wheel"
                    )
                    dist, isPure = rez_pip.install.installWheel(
                        package, pathlib.Path(wheel), args.target
                    )

                    dists[dist] = isPure

            distNames = [dist.name for dist in dists.keys()]

            with rich.get_console().status("[bold]Creating rez packages..."):
                for dist in dists:
                    isPure = dists[dist]
                    rez_pip.rez.createPackage(
                        dist,
                        isPure,
                        rez.vendor.version.version.Version(pythonVersion),
                        distNames,
                        args.target,
                        args.install_path,
                    )

            shutil.rmtree(args.target)
