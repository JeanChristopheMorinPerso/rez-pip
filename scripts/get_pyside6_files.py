# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import ast
import sys
import bisect
import typing
import difflib
import zipfile
import tempfile
import itertools
import contextlib
import subprocess

import requests
import requests.models
import packaging.utils


# Token from https://github.com/pypa/pip/blob/bc553db53c264abe3bb63c6bcd6fc6f303c6f6e3/src/pip/_internal/network/lazy_wheel.py
class LazyZipOverHTTP:
    """File-like object mapped to a ZIP file over HTTP.

    This uses HTTP range requests to lazily fetch the file's content,
    which is supposed to be fed to ZipFile.  If such requests are not
    supported by the server, raise HTTPRangeRequestUnsupported
    during initialization.
    """

    def __init__(
        self,
        url: str,
        session: requests.Session,
        chunk_size: int = requests.models.CONTENT_CHUNK_SIZE,
    ) -> None:
        head = session.head(url, headers={"Accept-Encoding": "identity"})
        head.raise_for_status()
        assert head.status_code == 200
        self._session, self._url, self._chunk_size = session, url, chunk_size
        self._length = int(head.headers["Content-Length"])
        self._file = tempfile.NamedTemporaryFile()
        self.truncate(self._length)
        self._left: list[int] = []
        self._right: list[int] = []
        if "bytes" not in head.headers.get("Accept-Ranges", "none"):
            raise ValueError("range request is not supported")
        self._check_zip()

    @property
    def mode(self) -> str:
        """Opening mode, which is always rb."""
        return "rb"

    @property
    def name(self) -> str:
        """Path to the underlying file."""
        return self._file.name

    def seekable(self) -> bool:
        """Return whether random access is supported, which is True."""
        return True

    def close(self) -> None:
        """Close the file."""
        self._file.close()

    @property
    def closed(self) -> bool:
        """Whether the file is closed."""
        return self._file.closed

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the object and return them.

        As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.  Fewer than
        size bytes may be returned if EOF is reached.
        """
        download_size = max(size, self._chunk_size)
        start, length = self.tell(), self._length
        stop = length if size < 0 else min(start + download_size, length)
        start = max(0, stop - download_size)
        self._download(start, stop - 1)
        return self._file.read(size)

    def readable(self) -> bool:
        """Return whether the file is readable, which is True."""
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        """Change stream position and return the new absolute position.

        Seek to offset relative position indicated by whence:
        * 0: Start of stream (the default).  pos should be >= 0;
        * 1: Current position - pos may be negative;
        * 2: End of stream - pos usually negative.
        """
        return self._file.seek(offset, whence)

    def tell(self) -> int:
        """Return the current position."""
        return self._file.tell()

    def truncate(self, size: int | None = None) -> int:
        """Resize the stream to the given size in bytes.

        If size is unspecified resize to the current position.
        The current stream position isn't changed.

        Return the new file size.
        """
        return self._file.truncate(size)

    def writable(self) -> bool:
        """Return False."""
        return False

    def __enter__(self) -> LazyZipOverHTTP:
        self._file.__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._file.__exit__(*exc)

    @contextlib.contextmanager
    def _stay(self) -> typing.Generator[None]:
        """Return a context manager keeping the position.

        At the end of the block, seek back to original position.
        """
        pos = self.tell()
        try:
            yield
        finally:
            self.seek(pos)

    def _check_zip(self) -> None:
        """Check and download until the file is a valid ZIP."""
        end = self._length - 1
        for start in reversed(range(0, end, self._chunk_size)):
            self._download(start, end)
            with self._stay():
                try:
                    # For read-only ZIP files, ZipFile only needs
                    # methods read, seek, seekable and tell.
                    zipfile.ZipFile(self)
                except zipfile.BadZipFile:
                    pass
                else:
                    break

    def _stream_response(
        self,
        start: int,
        end: int,
        base_headers: dict[str, str] = {"Accept-Encoding": "identity"},
    ) -> requests.Response:
        """Return HTTP response to a range request from start to end."""
        headers = base_headers.copy()
        headers["Range"] = f"bytes={start}-{end}"
        # TODO: Get range requests to be correctly cached
        headers["Cache-Control"] = "no-cache"
        return self._session.get(self._url, headers=headers, stream=True)

    def _merge(
        self, start: int, end: int, left: int, right: int
    ) -> typing.Generator[tuple[int, int]]:
        """Return a generator of intervals to be fetched.

        Args:
            start (int): Start of needed interval
            end (int): End of needed interval
            left (int): Index of first overlapping downloaded data
            right (int): Index after last overlapping downloaded data
        """
        lslice, rslice = self._left[left:right], self._right[left:right]
        i = start = min([start] + lslice[:1])
        end = max([end] + rslice[-1:])
        for j, k in zip(lslice, rslice):
            if j > i:
                yield i, j - 1
            i = k + 1
        if i <= end:
            yield i, end
        self._left[left:right], self._right[left:right] = [start], [end]

    def _download(self, start: int, end: int) -> None:
        """Download bytes from start to end inclusively."""
        with self._stay():
            left = bisect.bisect_left(self._right, start)
            right = bisect.bisect_right(self._left, end)
            for start, end in self._merge(start, end, left, right):
                response = self._stream_response(start, end)
                response.raise_for_status()
                self.seek(start)
                for chunk in response.iter_content(self._chunk_size):
                    self._file.write(chunk)


# https://stackoverflow.com/a/66733795
def compare_ast(
    node1: ast.expr | list[ast.expr], node2: ast.expr | list[ast.expr]
) -> bool:
    if type(node1) is not type(node2):
        return False

    if isinstance(node1, ast.AST):
        for k, v in vars(node1).items():
            if k in {"lineno", "end_lineno", "col_offset", "end_col_offset", "ctx"}:
                continue
            if not compare_ast(v, getattr(node2, k)):
                return False
        return True

    elif isinstance(node1, list) and isinstance(node2, list):
        return all(
            compare_ast(n1, n2) for n1, n2 in itertools.zip_longest(node1, node2)
        )
    else:
        return node1 == node2


def run():
    with requests.get(
        "https://pypi.org/simple/pyside6",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    ) as resp:
        resp.raise_for_status()

        data = resp.json()

    versions: list[str] = []
    for entry in data["files"]:
        if not entry["filename"].endswith(".whl"):
            continue

        name, version, buildtag, tags = packaging.utils.parse_wheel_filename(
            entry["filename"]
        )
        if version.pre:
            continue

        if not any(
            tag.platform.startswith("win_") and not tag.interpreter.startswith("pp")
            for tag in tags
        ):
            continue

        print(entry["filename"])

        # Store raw files in patches/data/<wheel>
        # This will allow us ot inspect them before deciding on how
        # to create patches.

        directory = os.path.join("patches", "data", str(version))
        os.makedirs(directory, exist_ok=True)

        session = requests.Session()
        wheel = LazyZipOverHTTP(entry["url"], session)
        with zipfile.ZipFile(wheel) as zf:
            for info in zf.infolist():
                if info.filename != "PySide6/__init__.py":
                    continue

                with open(
                    os.path.join(directory, os.path.basename(info.filename)), "wb"
                ) as f:
                    f.write(zf.read(info))
                break

        versions.append(str(version))

    print("Comparing files")
    first = versions.pop(0)

    while len(versions) > 1:
        leftFile = f"patches/data/{versions[0]}/__init__.py"
        rightFile = f"patches/data/{versions[1]}/__init__.py"
        with open(leftFile) as lfh, open(rightFile) as rfh:
            lhs = ast.parse(lfh.read())
            rhs = ast.parse(rfh.read())

        leftAST = next(
            node
            for node in lhs.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_additional_dll_directories"
        )

        rightAST = next(
            node
            for node in rhs.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_additional_dll_directories"
        )

        if not compare_ast(leftAST, rightAST):
            print(
                f"{versions[0]} and {versions[1]}'s _additional_dll_directories function differ"
            )
            leftCode = ast.unparse(leftAST).splitlines(keepends=True)
            rightCode = ast.unparse(rightAST).splitlines(keepends=True)

            result = difflib.unified_diff(
                leftCode, rightCode, fromfile=leftFile, tofile=rightFile
            )

            sys.stdout.writelines(result)

        versions.pop(0)


run()
