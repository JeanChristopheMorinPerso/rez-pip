import os
import sys
import json
import shutil
import typing
import logging
import argparse
import textwrap
import pathlib
import tempfile
import itertools
import subprocess

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import rich
import rich.text
import rich.panel
import rich.table
import rez.version
import rich.markup
import rich.logging

import rez_pip.pip
import rez_pip.rez
import rez_pip.data
import rez_pip.plugins
import rez_pip.install
import rez_pip.download
import rez_pip.exceptions

_LOG = logging.getLogger("rez_pip.cli")

__all__ = ["run"]


def __dir__() -> typing.List[str]:
    return __all__


def _createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest and convert python packages to rez packages.",
        prog=__package__.replace("_", "-"),
        add_help=False,
    )
    parser.add_argument("packages", nargs="*", help="Packages to install.")

    generalGroup = parser.add_argument_group(title="general options")
    generalGroup.add_argument(
        "-r",
        "--requirement",
        action="append",
        metavar="<file>",
        help="Install from the given requirements file. This option can be used multiple times.",
    )
    generalGroup.add_argument(
        "-c",
        "--constraint",
        action="append",
        metavar="<file>",
        help="Constrain versions using the given constraints file. This option can be used multiple times.",
    )
    generalGroup.add_argument(
        "-p",
        "--prefix",
        metavar="<path>",
        help="Custom repository path (can be any directory, even non rez repository path) (default: configured local_packages_path)",
    )
    generalGroup.add_argument(
        "--release",
        action="store_true",
        help="Release the converted packages (default: configured release_packages_path)",
    )

    generalGroup.add_argument(
        "--python-version",
        # 3.7+ because that's what pip supports
        default="3.7+",
        metavar="<version>",
        help="Range of python versions. It can also be a single version, any valid rez version specifier or range or 'latest' (default: 3.7+)",
    )
    generalGroup.add_argument(
        "--pip",
        default=rez_pip.pip.getBundledPip(),
        metavar="<path>",
        help="Standalone pip (https://pip.pypa.io/en/stable/installation/#standalone-zip-application) (default: bundled).",
    )

    # Manually define just to keep the style consistent (capital letters, dot, etc.)
    generalGroup.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit."
    )

    generalGroup.add_argument(
        "-v",
        "--version",
        action="version",
        version=importlib_metadata.version(__package__),
    )

    debugGroup = parser.add_argument_group(title="debug options")
    debugGroup.add_argument(
        "-l",
        "--log-level",
        default="info",
        choices=["info", "debug", "warning", "error"],
        help="Logging level.",
    )

    debugGroup.add_argument(
        "--keep-tmp-dirs",
        action="store_true",
        help="Keep some temporary directories at the end of the process for further inspection.",
    )

    debugGroup.add_argument(
        "--debug-info",
        action="store_true",
        help="Print debug information that you can use when reporting an issue on GitHub.",
    )

    debugGroup.add_argument(
        "--list-plugins", action="store_true", help="List all registered plugins"
    )

    parser.usage = f"""

  %(prog)s [options] <package(s)>
  %(prog)s <package(s)> [-- [pip options]]
"""
    return parser


def _parseArgs(
    args: typing.List[str],
) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
    parser = _createParser()

    knownArgs = []
    pipArgs = []
    if "--" in args:
        # anything after -- will be passed as is to pip.
        splitIndex = args.index("--")
        knownArgs = args[:splitIndex]
        pipArgs = args[splitIndex + 1 :]
    else:
        knownArgs = args

    ownArgs = parser.parse_args(knownArgs)

    return ownArgs, pipArgs


def _validateArgs(args: argparse.Namespace) -> None:
    if not args.pip.endswith(".pyz"):
        raise rez_pip.exceptions.RezPipError(
            f"[bold red]{args.pip!r} does not look like a valid zipapp. A zipapp should end with '.pyz'.[/]\n\n"
            "  [grey74]Standalone pip documentation[/]: https://pip.pypa.io/en/stable/installation/#standalone-zip-application\n"
            "  [grey74]zipapp documentation[/]: https://docs.python.org/3/library/zipapp.html"
        )

    if not os.path.exists(args.pip):
        raise rez_pip.exceptions.RezPipError(rf"zipapp at {args.pip!r} does not exist")

    if not args.packages and not args.requirement:
        raise rez_pip.exceptions.RezPipError(
            "no packages were passed and --requirements was not used. At least one of them must be passed."
        )


def _run(args: argparse.Namespace, pipArgs: typing.List[str], pipWorkArea: str) -> None:
    pythonVersions = rez_pip.rez.getPythonExecutables(
        args.python_version, packageFamily="python"
    )

    if not pythonVersions:
        raise rez_pip.exceptions.RezPipError(
            f'No "python" package found within the range {args.python_version!r}.'
        )

    for pythonVersion, pythonExecutable in pythonVersions.items():
        _LOG.info(
            f"[bold underline]Installing requested packages for Python {pythonVersion}"
        )

        wheelsDir = os.path.join(pipWorkArea, "wheels")
        os.makedirs(wheelsDir, exist_ok=True)

        # Suffix with the python version because we loop over multiple versions,
        # and package versions, content, etc can differ for each Python version.
        installedWheelsDir = os.path.join(pipWorkArea, "installed", pythonVersion)
        os.makedirs(installedWheelsDir, exist_ok=True)

        with rich.get_console().status(
            f"[bold]Resolving dependencies for {rich.markup.escape(', '.join(args.packages))} (python-{pythonVersion})"
        ):
            packages = rez_pip.pip.getPackages(
                args.packages,
                args.pip,
                pythonVersion,
                os.fspath(pythonExecutable),
                args.requirement or [],
                args.constraint or [],
                pipArgs,
            )

        _LOG.info(f"Resolved {len(packages)} dependencies for python {pythonVersion}")
        packageGroups: typing.List[rez_pip.pip.PackageGroup] = list(
            itertools.chain(*rez_pip.plugins.getHook().groupPackages(packages=packages))  # type: ignore[arg-type]
        )
        packageGroups += [rez_pip.pip.PackageGroup([package]) for package in packages]

        # TODO: Should we postpone downloading to the last minute if we can?
        _LOG.info("[bold]Downloading...")

        wheelsToDownload = []
        localWheels = []
        for group in packageGroups:
            for url in group.downloadUrls:
                print(url)
                if url.startswith("file://"):
                    localWheels.append(url[7:])
                else:
                    wheelsToDownload.extend(group.packages)

        downloadedWheels = rez_pip.download.downloadPackages(
            wheelsToDownload, wheelsDir
        )
        _LOG.info(f"[bold]Downloaded {len(downloadedWheels)} wheels")

        localWheels += downloadedWheels

        # Here, we could have a mapping of <merged package>: <dists> and pass that to installWheel
        with rich.get_console().status(
            f"[bold]Installing wheels into {installedWheelsDir!r}"
        ):
            for group in packageGroups:
                for package, wheel in zip(group.packages, group.downloadUrls):
                    _LOG.info(f"[bold]Installing {wheel}")
                    dist = rez_pip.install.installWheel(
                        package,
                        pathlib.Path(
                            wheel[7:] if wheel.startswith("file://") else wheel
                        ),
                        os.path.join(installedWheelsDir, package.name),
                    )
                    group.dists.append(dist)

        with rich.get_console().status("[bold]Creating rez packages..."):
            for group in packageGroups:
                print(list(package.name for package in group.packages))
                rez_pip.rez.createPackage(
                    group,
                    rez.version.Version(pythonVersion),
                    installedWheelsDir,
                    prefix=args.prefix,
                    release=args.release,
                )


def _debug(
    args: argparse.Namespace, console: rich.console.Console = rich.get_console()
) -> None:
    """Print debug information"""
    prefix = "  "
    console.print(
        f"[bold]rez-pip version[/]: {importlib_metadata.version(__package__)}"
    )

    console.print(f"[bold]rez version[/]: {importlib_metadata.version('rez')}")

    console.print(f"[bold]python version[/]: {sys.version}", highlight=False)
    console.print(f"[bold]python executable[/]: {sys.executable}", highlight=False)

    pip = args.pip or rez_pip.pip.getBundledPip()

    console.print(f"[bold]pip[/]: {pip}", highlight=False)

    completedProcess = subprocess.run(
        [sys.executable, pip, "--version"],
        stdout=subprocess.PIPE,
        text=True,
    )

    console.print(
        f"[bold]pip version[/]: {completedProcess.stdout.strip()}", highlight=False
    )

    completedProcess = subprocess.run(
        [sys.executable, pip, "config", "debug"],
        stdout=subprocess.PIPE,
        text=True,
    )

    console.print("[bold]rez-pip provided arguments[/]:")
    print(textwrap.indent(json.dumps(vars(args), indent=4), prefix))

    console.print(f"[bold]pip config debug[/]:", highlight=False)
    print(textwrap.indent(completedProcess.stdout.strip(), "  "))

    completedProcess = subprocess.run(
        [sys.executable, pip, "config", "list"],
        stdout=subprocess.PIPE,
        text=True,
    )

    console.print(f"[bold]pip config list[/]:", highlight=False)
    print(
        textwrap.indent(completedProcess.stdout.strip(), prefix)
        or f"{prefix}Returned nothing"
    )

    console.print(f"[bold]rez python packages[/]:", highlight=False)
    for pythonVersion, pythonExecutable in rez_pip.rez.getPythonExecutables(
        args.python_version
    ).items():
        print(textwrap.indent(f"{pythonExecutable} ({pythonVersion})", prefix))

    print()

    rich.print(
        rich.panel.Panel(
            rich.text.Text(
                "Please redact any sensitive information before giving this output to someone else!\n\n"
                "Don't remove things, only redact/replace. Look for IP addresses, domain names, passwords, etc.",
                justify="center",
            ),
            title="[bold red]WARNING!",
            expand=False,
            border_style="yellow",
        ),
        file=sys.stderr,
    )


def _printPlugins() -> None:
    table = rich.table.Table("Name", "Hooks", box=None)
    for plugin, hooks in rez_pip.plugins._getHookImplementations().items():
        table.add_row(plugin, ", ".join(hooks))
    rich.get_console().print(table)


def run() -> int:
    pipWorkArea = tempfile.mkdtemp(prefix="rez-pip-target")
    args, pipArgs = _parseArgs(sys.argv[1:])

    # Initialize the plugin system
    rez_pip.plugins.getManager()

    if args.list_plugins:
        _printPlugins()
        return 0

    try:
        _validateArgs(args)

        handler = rich.logging.RichHandler(
            show_time=False, markup=True, show_path=False
        )
        handler.setFormatter(logging.Formatter(fmt="%(message)s"))

        rootLogger = logging.getLogger("rez_pip")
        rootLogger.addHandler(handler)
        rootLogger.setLevel(args.log_level.upper())

        if args.debug_info:
            _debug(args)
            return 0

        _run(args, pipArgs, pipWorkArea)
        return 0
    except rez_pip.exceptions.RezPipError as exc:
        rich.get_console().print(exc, soft_wrap=True)
        return 1
    finally:
        if not args.keep_tmp_dirs:
            _LOG.debug(f"Removing {pipWorkArea}")
            shutil.rmtree(pipWorkArea)
