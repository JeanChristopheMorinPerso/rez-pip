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
import rez_pip.exceptions

_LOG = logging.getLogger("rez_pip")


def _run() -> None:
    handler = rich.logging.RichHandler(show_time=False, markup=True, show_path=False)
    handler.setFormatter(logging.Formatter(fmt="%(message)s"))
    _LOG.addHandler(handler)

    parser = argparse.ArgumentParser(
        description="Ingest and convert python packages to rez packages.",
        add_help=False,
    )
    parser.add_argument("packages", nargs="*", help="Packages to install.")
    parser.add_argument(
        "-r",
        "--requirement",
        action="append",
        metavar="<file>",
        help="Install from the given requirements file. This option can be used multiple times.",
    )
    parser.add_argument(
        "-c",
        "--constraint",
        action="append",
        metavar="<file>",
        help="Constrain versions using the given constraints file. This option can be used multiple times.",
    )
    parser.add_argument(
        "--target", required=True, metavar="<path>", help="Target directory"
    )
    parser.add_argument(
        "--install-path",
        metavar="<path>",
        help="Technically this should be --target",
    )

    parser.add_argument(
        "--python-version",
        metavar="<version>",
        help="Range of python versions. It can also be a single version or 'latest'",
    )
    parser.add_argument(
        "--pip",
        default=os.path.join(os.path.dirname(rez_pip.data.__file__), "pip.pyz"),
        metavar="<path>",
        help="Standalone pip (https://pip.pypa.io/en/stable/installation/#standalone-zip-application) (default: bundled).",
    )

    parser.add_argument(
        "-l",
        "--log-level",
        default="info",
        choices=["info", "debug", "warning", "error"],
        help="Logging level.",
    )

    # Manually define just to keep the style consistent (capital letters, dot, etc.)
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit."
    )

    parser.usage = f"""

  %(prog)s [options] <package(s)>
  %(prog)s <package(s)> [-- [pip options]]
"""
    ownArgs = []
    pipArgs = []
    if "--" in sys.argv:
        # anything after -- will be passed as is to pip.
        splitIndex = sys.argv[1:].index("--")
        ownArgs = sys.argv[1:][:splitIndex]
        pipArgs = sys.argv[1:][splitIndex + 1 :]
    else:
        ownArgs = sys.argv[1:]

    args = parser.parse_args(ownArgs)
    _LOG.setLevel(args.log_level.upper())

    if not args.pip.endswith(".pyz"):
        raise rez_pip.exceptions.RezPipError(
            f"[bold red]{args.pip!r} does not look like a valid zipapp. A zipapp should end with '.pyz'.[/]\n\n"
            "  [grey74]Standalone pip documentation[/]: https://pip.pypa.io/en/stable/installation/#standalone-zip-application\n"
            "  [grey74]zipapp documentation[/]: https://docs.python.org/3/library/zipapp.html"
        )

    if not os.path.exists(args.pip):
        raise rez_pip.exceptions.RezPipError(f"zipapp at {args.pip!r} does not exists")

    if not args.packages and not args.requirement:
        raise rez_pip.exceptions.RezPipError(
            "no packages were passed and --requirements was not used. At least one of the must be passed."
        )

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
                    args.packages,
                    args.pip,
                    pythonVersion,
                    pythonExecutable,
                    args.requirement or [],
                    args.constraint or [],
                    pipArgs,
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


def run() -> None:
    try:
        _run()
    except rez_pip.exceptions.RezPipError as exc:
        rich.get_console().print(exc, soft_wrap=True)
        sys.exit(1)
