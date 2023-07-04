import os
import sys
import copy
import shutil
import typing
import logging
import pathlib

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
    wheelURL: str,
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
        pkg.version = version

        # requirements and variants
        if requires:
            pkg.requires = requires

        if variant_requires:
            pkg.variants = [variant_requires]

        # commands
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
        # TODO: #672 (shortlinks for variants)
        pkg.hashed_variants = True

        pkg.pip = {
            "name": dist.name,
            "version": dist.version,
            "is_pure_python": metadata["is_pure_python"],
            "wheel_url": wheelURL,
        }

        # Take all the metadata that can be converted and put it
        # in the rez package definition.
        convertedMetadata, remainingMetadata = _convertMetadata(dist)
        for key, values in convertedMetadata.items():
            setattr(pkg, key, values)

        pkg.pip["metadata"] = remainingMetadata

    _LOG.info(
        f"[bold]Created {len(pkg.installed_variants)} variants and skipped {len(pkg.skipped_variants)}"
    )


def _convertMetadata(
    dist: importlib_metadata.Distribution,
) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Dict[str, typing.Any]]:
    metadata = {}
    originalMetadata = copy.deepcopy(dist.metadata.json)
    del originalMetadata["metadata_version"]
    del originalMetadata["name"]
    del originalMetadata["version"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#summary
    if dist.metadata["Summary"]:
        metadata["summary"] = dist.metadata["Summary"]
        del originalMetadata["summary"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#description
    if dist.metadata["Description"]:
        metadata["description"] = dist.metadata["Description"]
        del originalMetadata["description"]

    authors = []

    # https://packaging.python.org/en/latest/specifications/core-metadata/#author
    author = dist.metadata["Author"]
    if author:
        authors.append(author)
        del originalMetadata["author"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#author-email
    authorEmail = dist.metadata["Author-email"]
    if authorEmail:
        authors.extend([email.strip() for email in authorEmail.split(",")])
        del originalMetadata["author_email"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#maintainer
    maintainer = dist.metadata["Maintainer"]
    if maintainer:
        authors.append(maintainer)
        del originalMetadata["maintainer"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#maintainer-email
    maintainerEmail = dist.metadata["Maintainer-email"]
    if maintainerEmail:
        authors.extend([email.strip() for email in maintainerEmail.split(",")])
        del originalMetadata["maintainer_email"]

    if authors:
        metadata["authors"] = authors

    # https://packaging.python.org/en/latest/specifications/core-metadata/#license
    # Prefer the License field and fallback to classifiers if one is present.
    if dist.metadata["License"]:
        metadata["license"] = dist.metadata["License"]
        del originalMetadata["license"]
    else:
        licenseClassifiers = [
            item.split("::")[-1].strip()
            for item in dist.metadata.get_all("classifier", [])
            if item.startswith("License ::")
        ]

        # I don't know what to do in this case, so just skip license if more than one
        # classifier is found.
        if len(licenseClassifiers) == 1:
            metadata["license"] = licenseClassifiers[0]

    helpLinks = []

    # https://packaging.python.org/en/latest/specifications/core-metadata/#home-page
    if dist.metadata["Home-page"]:
        helpLinks.append(["Home-page", dist.metadata["Home-page"]])
        del originalMetadata["home_page"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#project-url-multiple-use
    if dist.metadata["Project-URL"]:
        urls = [
            url.strip()
            for value in dist.metadata.get_all("Project-URL")
            for url in value.split(",")
        ]
        helpLinks.extend([list(entry) for entry in zip(urls[::2], urls[1::2])])
        del originalMetadata["project_url"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#download-url
    if dist.metadata["Download-URL"]:
        helpLinks.append(["Download-URL", dist.metadata["Download-URL"]])
        del originalMetadata["download_url"]

    if helpLinks:
        metadata["help"] = helpLinks

    return metadata, originalMetadata


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
        key=lambda x: x.version,
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
