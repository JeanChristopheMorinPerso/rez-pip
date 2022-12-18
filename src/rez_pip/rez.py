import os
import typing
import shutil
import logging

import rez.config
import rez.package_maker
import importlib.metadata

import rez_pip.pip
import rez_pip.utils

_LOG = logging.getLogger(__name__)


def createPackage(
    dist: importlib.metadata.Distribution,
    isPure: bool,
    pythonVersion: str,
    nameCasings: list[str],
    installPath: typing.Optional[str] = None,
):
    _LOG.info(f"Creating rez package for {dist.name}")
    name = rez_pip.utils.pythontDistributionNameToRez(dist.name)
    version = rez_pip.utils.pythonDistributionVersionToRez(dist.version)

    requirements = rez_pip.utils.getRezRequirements(dist, pythonVersion, isPure, [])
    requires = requirements["requires"]
    variant_requires = requirements["variant_requires"]
    metadata = requirements["metadata"]

    if installPath:
        packagesPath = installPath
    else:
        packagesPath = (
            rez.config.config.release_packages_path
            if True
            else config.local_packages_path
        )

    def make_root(variant, path):
        """Using distlib to iterate over all installed files of the current
        distribution to copy files to the target directory of the rez package
        variant
        """
        # print(dist.files)
        if not dist.files:
            raise RuntimeError(
                f"{dist.name} package has no files registered! Something is wrong maybe?"
            )

        for src in dist.files:
            srcAbsolute = src.locate().resolve()

            # TODO: Replace /tmp/asd with the path to the tmp dir
            dest = os.path.join(path, srcAbsolute.relative_to("/tmp/asd"))
            if not os.path.exists(os.path.dirname(dest)):
                os.makedirs(os.path.dirname(dest))

            _LOG.debug(f"Copying {str(srcAbsolute)!r} to {str(dest)!r}")
            shutil.copyfile(srcAbsolute, dest)
            shutil.copystat(srcAbsolute, dest)

    with rez.package_maker.make_package(name, packagesPath, make_root=make_root) as pkg:
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
