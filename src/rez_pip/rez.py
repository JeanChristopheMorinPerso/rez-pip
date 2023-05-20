import os
import sys
import typing
import shutil
import logging

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import rez.config
import rez.packages
import rez.package_maker
import rez.resolved_context
import rez.vendor.version.version

import rez_pip.pip
import rez_pip.utils

_LOG = logging.getLogger(__name__)


def createPackage(
    dist: importlib_metadata.Distribution,
    isPure: bool,
    pythonVersion: rez.vendor.version.version.Version,
    nameCasings: typing.List[str],
    installedWheelsDir: str,
    prefix: typing.Optional[str] = None,
    release: bool = False,
) -> None:
    _LOG.info(f"Creating rez package for {dist.name}")
    name = rez_pip.utils.pythontDistributionNameToRez(dist.name)
    version = rez_pip.utils.pythonDistributionVersionToRez(dist.version)

    requirements = rez_pip.utils.getRezRequirements(dist, pythonVersion, isPure, [])

    requires = requirements.requires
    variant_requires = requirements.variant_requires
    metadata = requirements.metadata

    if prefix:
        packagesPath = prefix
    else:
        packagesPath = (
            rez.config.config.release_packages_path
            if release
            else rez.config.config.local_packages_path
        )

    def make_root(variant: rez.packages.Variant, path: str) -> None:
        """Using distlib to iterate over all installed files of the current
        distribution to copy files to the target directory of the rez package
        variant
        """
        formattedRequirements = ", ".join(str(req) for req in variant.variant_requires)

        _LOG.info(
            rf"Installing {variant.qualified_package_name} \[{formattedRequirements}]"
        )
        if not dist.files:
            raise RuntimeError(
                f"{dist.name} package has no files registered! Something is wrong maybe?"
            )

        for src in dist.files:
            srcAbsolute = src.locate().resolve()

            dest = os.path.join(
                path, srcAbsolute.relative_to(os.path.realpath(installedWheelsDir))
            )
            if not os.path.exists(os.path.dirname(dest)):
                os.makedirs(os.path.dirname(dest))

            _LOG.debug(f"Copying {str(srcAbsolute)!r} to {str(dest)!r}")
            shutil.copyfile(srcAbsolute, dest)
            shutil.copystat(srcAbsolute, dest)

    with rez.package_maker.make_package(
        name, packagesPath, make_root=make_root, skip_existing=True, warn_on_skip=False
    ) as pkg:
        # basics (version etc)
        pkg.version = version

        if dist.metadata["summary"]:
            pkg.description = dist.metadata["summary"]

        # requirements and variants
        if requires:
            pkg.requires = requires

        if variant_requires:
            pkg.variants = [variant_requires]

        # commands
        # TODO: Don't hardcode python in here.
        # TODO: WHat about "python less" packages, like cmake, etc?
        commands = ["env.PYTHONPATH.append('{root}/python')"]

        console_scripts = [
            ep.name for ep in dist.entry_points if ep.group == "console_scripts"
        ]
        if console_scripts:
            pkg.tools = console_scripts
            # TODO: Don't hardcode scripts here.
            commands.append("env.PATH.append('{root}/scripts')")

        pkg.commands = "\n".join(commands)

        # Make the package use hashed variants. This is required because we
        # can't control what ends up in its variants, and that can easily
        # include problematic chars (>, +, ! etc).
        # TODO: #672
        #
        pkg.hashed_variants = True

        # add some custom attributes to retain pip-related info
        pkg.pip_name = f"{dist.name}-{dist.version}"
        pkg.from_pip = True
        pkg.is_pure_python = metadata["is_pure_python"]

        # distribution_metadata = dist.metadata.json

        # help_ = []

        # if "home_page" in distribution_metadata:
        #     help_.append(["Documentation", distribution_metadata["home_page"]])

        # if "download_url" in distribution_metadata:
        #     help_.append(["Source Code", distribution_metadata["download_url"]])

        # if help_:
        #     pkg.help = help_

        if dist.metadata["Author"]:
            author = dist.metadata["Author"]

            if dist.metadata["Author-email"]:
                author += f" <{dist.metadata['Author-email']}>"

            pkg.authors = [author]

    _LOG.info(
        f"[bold]Installed {len(pkg.installed_variants)} variants and skipped {len(pkg.skipped_variants)}"
    )


def getPythonExecutables(
    range_: typing.Optional[str], packageFamily: str = "python"
) -> typing.Dict[str, str]:
    """
    Get the available python executable from rez packages.

    :param range_: version specifier
    :param packageFamily: Name of the rez package family for the python package. This allows ot support PyPy, etc.
    :returns: Dict where the keys are the python versions and values are abolute paths to executables.
    """
    packages = sorted(
        rez.packages.iter_packages(
            packageFamily, range_=range_ if range_ != "latest" else None
        ),
        key=lambda x: x.version,  # type: ignore
    )

    if range_ == "latest":
        packages = [packages[-1]]

    pythons: typing.Dict[str, str] = {}
    for package in packages:
        resolvedContext = rez.resolved_context.ResolvedContext(
            [f"{package.name}=={package.version}"]
        )

        for trimmedVersion in map(package.version.trim, [2, 1, 0]):
            path = resolvedContext.which(f"python{trimmedVersion}")
            if path:
                pythons[str(package.version)] = path
                break
        else:
            _LOG.warning(
                f"Failed to find a Python executable in the {package.qualified_name!r} rez package"
            )

    return pythons
