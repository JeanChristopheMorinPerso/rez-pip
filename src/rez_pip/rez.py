from __future__ import annotations

import os
import copy
import shutil
import typing
import logging
import pathlib
import itertools

import rez.config
import rez.version
import rez.packages
import rez.package_maker
import rez.resolved_context

import rez_pip.pip
import rez_pip.utils
import rez_pip.plugins
from rez_pip.compat import importlib_metadata

_LOG = logging.getLogger(__name__)


def createPackage(
    packageGroup: rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact],
    pythonVersion: rez.version.Version,
    installedWheelsDir: str,
    prefix: str | None = None,
    release: bool = False,
) -> None:
    _LOG.info(
        "Creating rez package for {0}".format(
            " + ".join(dist.name for dist in packageGroup.dists)
        )
    )

    rezNames = [
        rez_pip.utils.pythontDistributionNameToRez(dist.name)
        for dist in packageGroup.dists
    ]

    name = rezNames[0]
    version = rez_pip.utils.pythonDistributionVersionToRez(
        packageGroup.dists[0].version
    )

    requires = []
    variant_requires = []
    metadata: dict[str, typing.Any] = {}
    isPure = True
    for dist in packageGroup.dists:
        requirements = rez_pip.utils.getRezRequirements(dist, pythonVersion, [])
        if not metadata:
            # For now we only use the metadata from the first package. Far from ideal...
            metadata = requirements.metadata

        # TODO: Remove grouped packages (PySide-Addons, etc)
        requires += [
            require
            for require in requirements.requires
            if require not in requires
            # Check that the rez requirement isn't in the group name since it would be
            # an invalid requirement (because we merge them).
            and rez.version.Requirement(require).name not in rezNames[1:]
        ]
        variant_requires += [
            require
            for require in requirements.variant_requires
            if require not in variant_requires
            # Check that the rez requirement isn't in the group name since it would be
            # an invalid requirement (because we merge them).
            and rez.version.Requirement(require).name not in rezNames[1:]
        ]
        if isPure:
            isPure = metadata["is_pure_python"]

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
        for dist in packageGroup.dists:
            if not dist.files:
                raise RuntimeError(
                    f"{dist.name} package has no files registered! Something is wrong maybe?"
                )

            wheelsDirAbsolute = pathlib.Path(installedWheelsDir).resolve()
            for src in dist.files:
                srcAbsolute: pathlib.Path = typing.cast(
                    pathlib.Path, src.locate()
                ).resolve()
                dest = os.path.join(
                    path,
                    os.path.sep.join(
                        srcAbsolute.relative_to(wheelsDirAbsolute).parts[1:]
                    ),
                )
                # print(dest)
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
            "is_pure_python": isPure,
            "wheel_urls": packageGroup.downloadUrls,
            "rez_pip_version": importlib_metadata.version("rez-pip"),
        }

        # Take all the metadata that can be converted and put it
        # in the rez package definition.
        convertedMetadata, remainingMetadata = _convertMetadata(dist)
        for key, values in convertedMetadata.items():
            setattr(pkg, key, values)

        pkg.pip["metadata"] = remainingMetadata

        rez_pip.plugins.getHook().metadata(package=pkg)

    _LOG.info(
        f"[bold]Created {len(pkg.installed_variants)} variants and skipped {len(pkg.skipped_variants)}"
    )


def _convertMetadata(
    dist: importlib_metadata.Distribution,
) -> tuple[dict[str, typing.Any], dict[str, typing.Any]]:
    metadata: dict[str, typing.Any] = {}
    originalMetadata = copy.deepcopy(dist.metadata.json)
    del originalMetadata["metadata_version"]
    del originalMetadata["name"]
    del originalMetadata["version"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#summary
    if "Summary" in dist.metadata:
        metadata["summary"] = dist.metadata["Summary"]
        del originalMetadata["summary"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#description
    if "Description" in dist.metadata:
        metadata["description"] = dist.metadata["Description"]
        del originalMetadata["description"]

    authors = []

    # https://packaging.python.org/en/latest/specifications/core-metadata/#author
    if "Author" in dist.metadata:
        authors.append(dist.metadata["Author"])
        del originalMetadata["author"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#author-email
    if "Author-email" in dist.metadata:
        authors.extend(
            [email.strip() for email in dist.metadata["Author-email"].split(",")]
        )
        del originalMetadata["author_email"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#maintainer
    if "Maintainer" in dist.metadata:
        authors.append(dist.metadata["Maintainer"])
        del originalMetadata["maintainer"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#maintainer-email
    if "Maintainer-email" in dist.metadata:
        authors.extend(
            [email.strip() for email in dist.metadata["Maintainer-email"].split(",")]
        )
        del originalMetadata["maintainer_email"]

    if authors:
        metadata["authors"] = authors

    # https://packaging.python.org/en/latest/specifications/core-metadata/#license
    # Prefer the License field and fallback to classifiers if one is present.
    if "License" in dist.metadata:
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
    if "Home-page" in dist.metadata:
        helpLinks.append(["Home-page", dist.metadata["Home-page"]])
        del originalMetadata["home_page"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#project-url-multiple-use
    if "Project-URL" in dist.metadata:
        urls = [
            url.strip()
            for value in dist.metadata.get_all("Project-URL", failobj=[])
            for url in value.split(",")
        ]
        helpLinks.extend([list(entry) for entry in zip(urls[::2], urls[1::2])])
        del originalMetadata["project_url"]

    # https://packaging.python.org/en/latest/specifications/core-metadata/#download-url
    if "Download-URL" in dist.metadata:
        helpLinks.append(["Download-URL", dist.metadata["Download-URL"]])
        del originalMetadata["download_url"]

    if helpLinks:
        metadata["help"] = helpLinks

    return metadata, originalMetadata


def getPythonExecutables(
    range_: str | None, packageFamily: str = "python"
) -> dict[str, pathlib.Path]:
    """
    Get the available python executable from rez packages.

    :param range_: version specifier
    :param packageFamily: Name of the rez package family for the python package. This allows ot support PyPy, etc.
    :returns: Dict where the keys are the python versions and values are abolute paths to executables.
    """
    all_packages = sorted(
        rez.packages.iter_packages(
            packageFamily, range_=range_ if range_ != "latest" else None
        ),
        key=lambda x: x.version,
    )

    packages: list[rez.packages.Package]
    if range_ == "latest":
        packages = [list(all_packages)[-1]]
    else:
        # Get the latest x.x (major+minor) and ignore anything else.
        # We don't want to return 3.7.8 AND 3.7.9 for example. It doesn't
        # make sense. We only need 3.7.x.
        groups = [
            list(group)
            for _, group in itertools.groupby(
                all_packages, key=lambda x: x.version.as_tuple()[:2]
            )
        ]
        # Note that "pkgs" is already in the right order since all_packages is sorted.
        packages = [pkgs[-1] for pkgs in groups]

    pythons: dict[str, pathlib.Path] = {}
    for package in packages:
        resolvedContext = rez.resolved_context.ResolvedContext(
            [f"{package.name}=={package.version}"]
        )

        # Make sure that system PATH doens't interfere with the "which" method.
        resolvedContext.append_sys_path = False

        for trimmedVersion in map(package.version.trim, [2, 1, 0]):
            path = resolvedContext.which(f"python{trimmedVersion}", parent_environ={})
            if path:
                pythons[str(package.version)] = pathlib.Path(path)
                break
        else:
            _LOG.warning(
                f"Failed to find a Python executable in the {package.qualified_name!r} rez package"
            )

    return pythons
