from __future__ import annotations

import os
import math
import typing
import logging
import contextlib
import collections.abc
import logging.handlers

import patch_ng

import rez_pip.utils
import rez_pip.compat
import rez_pip.plugins
import rez_pip.exceptions
import rez_pip.data.patches
from rez_pip.compat import importlib_metadata


_LOG = logging.getLogger(__name__)


class PatchError(rez_pip.exceptions.RezPipError):
    pass


def getBuiltinPatchesDir() -> str:
    """Get the built-in patches directory"""
    return os.path.dirname(rez_pip.data.patches.__file__)


@contextlib.contextmanager
def logIfErrorOrRaises() -> typing.Generator[None, None, None]:
    """
    Log patch_ng logs if any error is logged or if the wrapped body raises.
    Very slightly inspired by https://docs.python.org/3/howto/logging-cookbook.html#buffering-logging-messages-and-outputting-them-conditionally

    We basically don't want any logs from patch_ng is everything worked. We only
    want logs when something wrong happens.
    """
    patch_ng.debugmode = True
    logger = logging.getLogger("patch_ng")
    initialLevel = logger.level
    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.MemoryHandler(
        math.inf,  # type: ignore[arg-type]
        flushLevel=logging.ERROR,
        target=logging.getLogger("rez_pip").handlers[0],
    )
    handler.setFormatter(logging.Formatter("%(name)s %(levelname)8s %(message)s"))

    logger.addHandler(handler)

    try:
        yield
    except Exception as exc:
        handler.flush()
        raise exc from None
    finally:
        patch_ng.debugmode = False
        logger.setLevel(initialLevel)
        logger.removeHandler(handler)


def patch(dist: importlib_metadata.Distribution, path: str) -> None:
    """Patch an installed package (wheel)"""
    _LOG.debug(f"[bold]Attempting to patch {dist.name!r} at {path!r}")
    patchesGroups: collections.abc.Sequence[collections.abc.Sequence[str]] = (
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
        with logIfErrorOrRaises():
            if not patchset.apply(root=path):
                # A logger that only gets flushed on demand would be better...
                raise PatchError(f"Failed to apply patch {patch!r} on {path!r}")
