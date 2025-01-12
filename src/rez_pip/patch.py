from __future__ import annotations

import os
import typing
import logging

import patch_ng

import rez_pip.data.patches
import rez_pip.compat
import rez_pip.plugins
import rez_pip.exceptions
from rez_pip.compat import importlib_metadata

_LOG = logging.getLogger(__name__)


class PatchError(rez_pip.exceptions.RezPipError):
    pass


def getBuiltinPatchesDir() -> str:
    """Get the built-in patches directory"""
    return os.path.dirname(rez_pip.data.patches.__file__)


def patch(dist: importlib_metadata.Distribution, path: str) -> None:
    """Patch an installed package (wheel)"""
    _LOG.debug(f"[bold]Attempting to patch {dist.name!r} at {path!r}")
    patchesGroups: rez_pip.compat.Sequence[rez_pip.compat.Sequence[str]] = (
        rez_pip.plugins.getHook().patches(dist=dist, path=path)
    )

    # Flatten the list
    patches = [path for group in patchesGroups for path in group]

    if not patches:
        _LOG.debug(f"No patches found")
        return

    _LOG.info(f"Applying {len(patches)} patches for {dist.name!r} at {path!r}")

    for patch in patches:
        _LOG.info(f"Applying patch {patch!r} on {path!r}")

        if not os.path.isabs(patch):
            raise PatchError(f"{patch!r} is not an absolute path")

        if not os.path.exists(patch):
            raise PatchError(f"Patch at {patch!r} does not exist")

        patchset = patch_ng.fromfile(patch)
        if not patchset.apply(root=path):
            raise PatchError(f"Failed to apply patch {patch!r} on {path!r}")
