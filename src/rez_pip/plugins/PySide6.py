"""PySide6 plugin.

For PySide6, we need a merge hook. If User says "install PySide6", we need to install PySide6, PySide6-Addons and PySide6-Essentials and shiboken6.

But PySide6, PySide6-Addons and PySide6-Essentials have to be merged. Additionally, shiboken6 needs to be broken down to remove PySide6 (core).
Because shiboken6 vendors PySide6-core... See https://inspector.pypi.io/project/shiboken6/6.6.1/packages/bb/72/e54f758e49e8da0dcd9490d006c41a814b0e56898ce4ca054d60cdba97bd/shiboken6-6.6.1-cp38-abi3-manylinux_2_28_x86_64.whl/.

On Windows, the PySide6/openssl folder has to be added to PATH, see https://inspector.pypi.io/project/pyside6/6.6.1/packages/ec/3d/1da1b88d74cb5318466156bac91f17ad4272c6c83a973e107ad9a9085009/PySide6-6.6.1-cp38-abi3-win_amd64.whl/PySide6/__init__.py#line.81.

So it's at least a 3 steps process:
1. Merge PySide6, PySide6-Essentials and PySide6-Addons into the same install. Unvendor shiboken.
2. Install shiboken + cleanup. The Cleanup could be its own hook here specific to shiboken.
"""

from __future__ import annotations

import os
import shutil
import typing

import packaging.utils
import packaging.version
import packaging.specifiers
import packaging.requirements

import rez_pip.pip
import rez_pip.plugins
import rez_pip.exceptions

if typing.TYPE_CHECKING:
    from rez_pip.compat import importlib_metadata

# PySide6 was initiall a single package that had shiboken as a dependency.
# Starting from 6.3.0, the package was spit in 3, PySide6, PySide6-Essentials and
# PySide6-Addons.


@rez_pip.plugins.hookimpl
def prePipResolve(
    packages: typing.List[str],
) -> None:
    pyside6Seen = False
    variantsSeens = []

    for package in packages:
        req = packaging.requirements.Requirement(package)
        name = packaging.utils.canonicalize_name(req.name)

        if name == "pyside6":
            pyside6Seen = True
        elif name in ["pyside6-essentials", "pyside6-addons"]:
            variantsSeens.append(req.name)

    if variantsSeens and not pyside6Seen:
        variants = " and ".join(variantsSeens)
        verb = "was" if len(variantsSeens) == 1 else "were"
        raise rez_pip.exceptions.RezPipError(
            f"{variants} {verb} requested but PySide6 was not. You must explicitly request PySide6 in addition to {variants}."
        )


@rez_pip.plugins.hookimpl
def postPipResolve(packages: typing.List[rez_pip.pip.PackageInfo]) -> None:
    """
    This hook is implemented out of extra caution. We really don't want PySide6-Addons
    or PySide6-Essentials to be installed without PySide6.

    In this case, we cover cases where a user requests a package X and that package
    depends on PySide6-Addons or PySide6-Essentials.
    """
    pyside6Seen = False
    variantsSeens = []

    for package in packages:
        name = packaging.utils.canonicalize_name(package.name)
        if name == "pyside6":
            pyside6Seen = True
        elif name in ["pyside6-essentials", "pyside6-addons"]:
            variantsSeens.append(package.name)

    if variantsSeens and not pyside6Seen:
        variants = " and ".join(variantsSeens)
        verb = "is" if len(variantsSeens) == 1 else "are"
        raise rez_pip.exceptions.RezPipError(
            f"{variants} {verb} part of the resolved packages but PySide6 was not. Dependencies and or you must explicitly request PySide6 in addition to {variants}."
        )


@rez_pip.plugins.hookimpl
def groupPackages(
    packages: typing.List[rez_pip.pip.PackageInfo],
) -> typing.List[rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo]]:
    data = []
    for index, package in enumerate(packages[:]):
        if packaging.utils.canonicalize_name(package.name) in [
            "pyside6",
            "pyside6-addons",
            "pyside6-essentials",
        ]:
            data.append(package)
            packages.remove(package)

    return [rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo](tuple(data))]


@rez_pip.plugins.hookimpl
def cleanup(dist: "importlib_metadata.Distribution", path: str) -> None:
    if packaging.utils.canonicalize_name(dist.name) not in [
        "pyside6",
        "pyside6-addons",
        "pyside6-essentials",
    ]:
        return

    # Remove shiboken6 from PySide6 packages...
    # PySide6 >=6.3, <6.6.2 were shipping some shiboken6 folders by mistake.
    # Not removing these extra folders would stop python from being able to import
    # the correct shiboken (that lives in a separate rez package).
    shutil.rmtree(os.path.join(path, "python", "shiboken6"))
    shutil.rmtree(os.path.join(path, "python", "shiboken6_generator"))
