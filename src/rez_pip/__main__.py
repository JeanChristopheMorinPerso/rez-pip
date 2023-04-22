import sys
import logging
import argparse
import pathlib
import tempfile
import importlib.metadata

import rich.logging
import rez.vendor.version.version

import rez_pip.pip
import rez_pip.rez
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
    parser.add_argument("package", help="Package to install")
    parser.add_argument(
        "--target", required=True, metavar="path", help="Target directory"
    )
    parser.add_argument("--install-path", help="Technically this should be --target")

    parser.add_argument(
        "--python-version",
        default=f"{sys.version_info[0]}.{sys.version_info[1]}",
        metavar="version",
        help="Python version of the package",
    )
    parser.add_argument(
        "--pip",
        default="/home/jcmorin/jcmenv/aswf/rez-pip/pip.pyz",
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
    with tempfile.TemporaryDirectory(prefix="rez-pip") as tempDir:
        packages = rez_pip.pip.get_packages(args.package, args.pip, args.python_version)

        # TODO: Should we postpone downloading to the last minute if we can?
        _LOG.info("[bold]Downloading...")
        wheels = rez_pip.download.downloadPackages(packages, tempDir)
        _LOG.info(f"[bold]Downloaded {len(wheels)} wheels")

        dists: dict[importlib.metadata.Distribution, bool] = {}
        _LOG.info(f"[bold]Installing wheels into {args.target!r}")

        for package, wheel in zip(packages, wheels):
            _LOG.debug(f"[bold]Installing {package.name}-{package.version} wheel")
            dist, isPure = rez_pip.install.installWheel(
                package, pathlib.Path(wheel), args.target
            )

            dists[dist] = isPure

        distNames = [dist.name for dist in dists.keys()]

        for dist in dists:
            isPure = dists[dist]
            rez_pip.rez.createPackage(
                dist,
                isPure,
                rez.vendor.version.version.Version(args.python_version),
                distNames,
                args.install_path,
            )
