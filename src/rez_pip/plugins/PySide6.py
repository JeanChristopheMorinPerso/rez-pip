# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""PySide6 plugin."""

from __future__ import annotations

import os
import typing
import logging
import platform

import packaging.utils
import packaging.version
import packaging.specifiers
import packaging.requirements

import rez_pip.pip
import rez_pip.patch
import rez_pip.plugins
import rez_pip.exceptions

if typing.TYPE_CHECKING:
    from rez_pip.compat import importlib_metadata

_LOG = logging.getLogger(__name__)


@rez_pip.plugins.hookimpl
def prePipResolve(
    packages: tuple[str],
) -> None:
    """
    PySide6 was initially a single package that had shiboken as a dependency.
    Starting from 6.3.0, the package was spit in 3, PySide6, PySide6-Essentials and
    PySide6-Addons.

    So we need to intercept what the user installs and install all 3 packages together.
    Not doing that would result in a broken install (eventually).
    """
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
def postPipResolve(packages: tuple[rez_pip.pip.PackageInfo]) -> None:
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
    packages: list[rez_pip.pip.PackageInfo],
) -> list[rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo]]:
    data = []
    for package in packages[:]:
        if packaging.utils.canonicalize_name(package.name) in [
            "pyside6",
            "pyside6-addons",
            "pyside6-essentials",
        ]:
            data.append(package)
            packages.remove(package)

    return [rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo](tuple(data))]


@rez_pip.plugins.hookimpl
def patches(dist: importlib_metadata.Distribution, path: str) -> list[str]:
    if dist.name != "PySide6" or platform.system() != "Windows":
        return []

    patches: list[str] = []

    # To generate the patches:
    # 1. run srcipts/get_pyside6_files.py
    # 2. Look at the output and get the different diffs.
    # 3. Generate a patch for each version range where there is a diff:
    # 3.1 cp patches/data/6.3.0/__init__.py patches/data/6.3.0/__init__.py.new
    # 3.2 vim patches/data/6.3.0/__init__.py.new
    # 3.3 diff --unified patches/data/6.3.0/__init__.py patches/data/6.3.0/__init__.py.new > src/rez_pip/data/patches/pyside6_6_3_0_win_dll_path.patch
    # 3.4 Edit src/rez_pip/data/patches/pyside6_6_3_0_win_dll_path.patch to make sure the paths
    #     are good in the patch header. Also make sure CRLF (line ending) is kept as-is.
    #
    # I think that it's important that the paths in the look like "python/PySide6/..."
    # so that it matches the file layout...
    version = packaging.version.Version(dist.version)
    if version in packaging.specifiers.SpecifierSet(">=6.0.0,<6.1.0"):
        patches.append(
            os.path.join(
                rez_pip.patch.getBuiltinPatchesDir(), "pyside6_6_0_0_win_dll_path.patch"
            )
        )

    elif version in packaging.specifiers.SpecifierSet(">=6.1.0,<6.2.4"):
        patches.append(
            os.path.join(
                rez_pip.patch.getBuiltinPatchesDir(), "pyside6_6_1_0_win_dll_path.patch"
            )
        )

    elif version in packaging.specifiers.SpecifierSet(">=6.2.4,<6.3.0"):
        patches.append(
            os.path.join(
                rez_pip.patch.getBuiltinPatchesDir(), "pyside6_6_2_4_win_dll_path.patch"
            )
        )

    elif version in packaging.specifiers.SpecifierSet(">=6.3.0,<6.7.3"):
        patches.append(
            os.path.join(
                rez_pip.patch.getBuiltinPatchesDir(), "pyside6_6_3_0_win_dll_path.patch"
            )
        )

    elif version in packaging.specifiers.SpecifierSet(">=6.7.3,<6.8.1"):
        patches.append(
            os.path.join(
                rez_pip.patch.getBuiltinPatchesDir(), "pyside6_6_7_3_win_dll_path.patch"
            )
        )
    elif version in packaging.specifiers.SpecifierSet(">=6.8.1"):
        patches.append(
            os.path.join(
                rez_pip.patch.getBuiltinPatchesDir(), "pyside6_6_8_1_win_dll_path.patch"
            )
        )
    return patches


@rez_pip.plugins.hookimpl
def cleanup(
    dist: importlib_metadata.Distribution, path: str
) -> list[rez_pip.plugins.CleanupAction]:
    actions: list[rez_pip.plugins.CleanupAction] = []

    if packaging.utils.canonicalize_name(dist.name) not in [
        "pyside6",
        "pyside6-addons",
        "pyside6-essentials",
    ]:
        return actions

    # Remove shiboken6 from PySide6 packages...
    # PySide6 >=6.3, <6.6.2 were shipping some shiboken6 folders by mistake.
    # Not removing these extra folders would stop python from being able to import
    # the correct shiboken (that lives in a separate rez package).
    actions.extend(
        [
            rez_pip.plugins.CleanupAction(
                "remove", os.path.join(path, "python", "shiboken6")
            ),
            rez_pip.plugins.CleanupAction(
                "remove", os.path.join(path, "python", "shiboken6_generator")
            ),
        ]
    )

    if packaging.utils.canonicalize_name(dist.name) in [
        "pyside6-addons",
        "pyside6-essentials",
    ]:
        # Because we patch __init__.py, we need to make sure that
        # PySide6-Addons and PySide6-Essentials' _init__.py won't
        # overrite our patched __init__.py.
        actions.append(
            rez_pip.plugins.CleanupAction(
                "remove", os.path.join(path, "python", "PySide6", "__init__.py")
            )
        )

    return actions
