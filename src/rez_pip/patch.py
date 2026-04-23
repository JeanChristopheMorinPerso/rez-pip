# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import math
import typing
import logging
import contextlib
import logging.handlers

import patch_ng

import rez_pip.exceptions
import rez_pip.data.patches


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
