import os
import typing
import shutil
import logging

import packaging.utils

import rez_pip.plugins

if typing.TYPE_CHECKING:
    from rez_pip.compat import importlib_metadata

_LOG = logging.getLogger(__name__)


@rez_pip.plugins.hookimpl
def cleanup(dist: "importlib_metadata.Distribution", path: str) -> None:
    if packaging.utils.canonicalize_name(dist.name) != "shiboken6":
        return

    # Remove PySide6 from shiboken6 packages...
    # shiboken6 >=6.3, <6.6.2 were shipping some PySide6 folders by mistake.
    # Not removing these extra folders would stop python from being able to import
    # the correct PySide6 (that lives in a separate rez package).
    path = os.path.join(path, "python", "PySide6")
    if os.path.exists(path):
        _LOG.debug(f"Removing {path!r}")
        shutil.rmtree(path)
