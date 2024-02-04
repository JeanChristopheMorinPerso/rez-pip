import os
import sys
import shutil

import packaging.utils

import rez_pip.plugins

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata


@rez_pip.plugins.hookimpl
def cleanup(dist: importlib_metadata.Distribution, path: str) -> None:
    if packaging.utils.canonicalize_name(dist.name) == "shiboken6":
        path = os.path.join(path, "python", "PySide6")
        print(f"Removing {path!r}")
        shutil.rmtree(path)
