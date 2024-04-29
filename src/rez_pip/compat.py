import sys

if sys.version_info <= (3, 8):
    from typing import Sequence, MutableSequence, Mapping
else:
    from collections.abc import Sequence, MutableSequence, Mapping

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

__all__ = ["Sequence", "MutableSequence", "Mapping", "importlib_metadata"]
