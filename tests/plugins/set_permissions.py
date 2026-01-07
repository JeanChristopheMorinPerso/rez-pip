# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""Set permissions plugin."""

from __future__ import annotations

import os
import logging

import rez

import rez_pip.plugins
import rez.package_maker


_LOG = logging.getLogger(__name__)


def get_executables(package_root):
    """Get executables from package root."""
    executables = []
    for dirpath, _, files in os.walk(package_root):
        for filename in files:
            ext = os.path.splitext(filename)[-1]
            if ext in (".dll", ".exe", ".pyd"):
                executables.append(os.path.join(dirpath, filename))
    return executables


@rez_pip.plugins.hookimpl
def postInstall(package: rez.package_maker.PackageMaker) -> None:
    """
    Change persmissions post-installation to make sure all
    .dll, .exe, .pyd files are executables.
    """

    for variant in package.installed_variants:
        _LOG.info(f"Package root : {variant.root}")
        executables = get_executables(variant.root)
        for executable in executables:
            os.chmod(executable, 0o755)
        _LOG.info(f"Changed permissions on {len(executables)} executables.")
