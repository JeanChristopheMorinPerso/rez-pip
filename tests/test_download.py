import os
import sys
import typing
import hashlib
import pathlib

if sys.version_info[:2] < (3, 8):
    import mock
else:
    from unittest import mock

import pytest
import aiohttp

import rez_pip.pip
import rez_pip.download


@pytest.mark.parametrize(
    "packages",
    [
        {"package-a": "package-a data"},
        {"package-a": "package-a data", "package-b": "package-b data"},
    ],
    ids=["single-package", "multiple-packages"],
)
def test_download(packages: typing.Dict[str, str], tmp_path: pathlib.Path):
    sideEffects = tuple()
    for content in packages.values():
        mockedContent = mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content.encode("utf-8"),
                None,
            ]
        ]

        sideEffects += (
            mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet = mock.AsyncMock()
    mockedGet.__aenter__.side_effect = sideEffects

    with mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet

        wheels = rez_pip.download.downloadPackages(
            [
                rez_pip.pip.PackageInfo(
                    metadata=rez_pip.pip.Metadata(name=package, version="1.0.0"),
                    download_info=rez_pip.pip.DownloadInfo(
                        url=f"https://example.com/{package}.whl",
                        archive_info=rez_pip.pip.ArchiveInfo("hash", {}),
                    ),
                    is_direct=True,
                    requested=True,
                )
                for package in packages
            ],
            os.fspath(tmp_path),
        )

    assert sorted(wheels) == sorted(
        [os.fspath(tmp_path / f"{package}.whl") for package in packages]
    )

    for wheel in wheels:
        with open(wheel, "r") as fd:
            content = fd.read()
        assert packages[os.path.basename(wheel).split(".")[0]] == content

    assert mocked.call_args_list == [
        mock.call(
            f"https://example.com/{package}.whl",
            headers={
                "Content-Type": "application/octet-stream",
                "User-Agent": "rez-pip/0.1.0",
            },
        )
        for package in packages
    ]


def test_download_multiple_packages_with_failure(tmp_path: pathlib.Path):
    mockedContent = mock.MagicMock()
    mockedContent.return_value.__aiter__.return_value = [
        [
            b"package-a data",
            None,
        ]
    ]

    mockedGet = mock.AsyncMock()
    mockedGet.__aenter__.side_effect = (
        mock.Mock(
            headers={"content-length": 100},
            status=200,
            content=mock.Mock(iter_chunks=mockedContent),
        ),
        mock.Mock(
            headers={"content-length": 100},
            status=400,
            reason="Expected to fail",
            request_info={"key": "here"},
            content=mock.Mock(iter_chunks=mockedContent),
        ),
    )

    with mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet
        with pytest.raises(RuntimeError):
            rez_pip.download.downloadPackages(
                [
                    rez_pip.pip.PackageInfo(
                        metadata=rez_pip.pip.Metadata(
                            name="package-a", version="1.0.0"
                        ),
                        download_info=rez_pip.pip.DownloadInfo(
                            url="https://example.com/package-a",
                            archive_info=rez_pip.pip.ArchiveInfo("hash-a", {}),
                        ),
                        is_direct=True,
                        requested=True,
                    ),
                    rez_pip.pip.PackageInfo(
                        metadata=rez_pip.pip.Metadata(
                            name="package-b", version="1.0.0"
                        ),
                        download_info=rez_pip.pip.DownloadInfo(
                            url="https://example.com/package-b",
                            archive_info=rez_pip.pip.ArchiveInfo("hash-b", {}),
                        ),
                        is_direct=True,
                        requested=True,
                    ),
                ],
                os.fspath(tmp_path),
            )

        # Check that package-a was downloaded even if even if package-b failed.
        with open(tmp_path / "package-a", "r") as fd:
            assert fd.read() == "package-a data"

        assert mocked.call_args_list == [
            mock.call(
                "https://example.com/package-a",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
            mock.call(
                "https://example.com/package-b",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
        ]


def test_download_reuse_if_same_hash(tmp_path: pathlib.Path):
    """Test that wheels are re-used if the sha256 matches"""
    sideEffects = tuple()
    packages = []

    for package in ["package-a", "package-b"]:
        content = f"{package} data".encode("utf-8")

        hash = hashlib.new("sha256")
        hash.update(content)

        packages.append(
            rez_pip.pip.PackageInfo(
                metadata=rez_pip.pip.Metadata(name=package, version="1.0.0"),
                download_info=rez_pip.pip.DownloadInfo(
                    url=f"https://example.com/{package}.whl",
                    archive_info=rez_pip.pip.ArchiveInfo(
                        "hash-a", {"sha256": hash.hexdigest()}
                    ),
                ),
                is_direct=True,
                requested=True,
            )
        )

        mockedContent = mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet1 = mock.AsyncMock()
    mockedGet1.__aenter__.side_effect = sideEffects

    with mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet1

        rez_pip.download.downloadPackages(packages, str(tmp_path))

        assert mocked.call_args_list == [
            mock.call(
                "https://example.com/package-a.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
            mock.call(
                "https://example.com/package-b.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
        ]

    packages = []
    # package-b will be re-used
    for package in ["package-c", "package-b"]:
        content = f"{package} data".encode("utf-8")

        hash = hashlib.new("sha256")
        hash.update(content)

        packages.append(
            rez_pip.pip.PackageInfo(
                metadata=rez_pip.pip.Metadata(name=package, version="1.0.0"),
                download_info=rez_pip.pip.DownloadInfo(
                    url=f"https://example.com/{package}.whl",
                    archive_info=rez_pip.pip.ArchiveInfo(
                        "hash-a", {"sha256": hash.hexdigest()}
                    ),
                ),
                is_direct=True,
                requested=True,
            )
        )

        mockedContent = mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet2 = mock.AsyncMock()
    mockedGet2.__aenter__.side_effect = sideEffects

    with mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet2

        wheels = rez_pip.download.downloadPackages(packages, str(tmp_path))

        assert mocked.call_args_list == [
            mock.call(
                "https://example.com/package-c.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
        ]

    assert sorted(wheels) == [
        os.fspath(tmp_path / f"{package}.whl") for package in ["package-b", "package-c"]
    ]


def test_download_redownload_if_hash_changes(tmp_path: pathlib.Path):
    """Test that wheels are re-used if the sha256 matches"""
    sideEffects = tuple()
    packages = []

    for package in ["package-a", "package-b"]:
        content = f"{package} data".encode("utf-8")

        hash = hashlib.new("sha256")
        hash.update(content)

        packages.append(
            rez_pip.pip.PackageInfo(
                metadata=rez_pip.pip.Metadata(name=package, version="1.0.0"),
                download_info=rez_pip.pip.DownloadInfo(
                    url=f"https://example.com/{package}.whl",
                    archive_info=rez_pip.pip.ArchiveInfo(
                        "hash-a", {"sha256": hash.hexdigest()}
                    ),
                ),
                is_direct=True,
                requested=True,
            )
        )

        mockedContent = mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet1 = mock.AsyncMock()
    mockedGet1.__aenter__.side_effect = sideEffects

    with mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet1

        rez_pip.download.downloadPackages(packages, str(tmp_path))

        assert mocked.call_args_list == [
            mock.call(
                "https://example.com/package-a.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
            mock.call(
                "https://example.com/package-b.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
        ]

    packages = []
    # package-b will be re-used
    for package in ["package-a", "package-b"]:
        content = f"{package} data".encode("utf-8")

        packages.append(
            rez_pip.pip.PackageInfo(
                metadata=rez_pip.pip.Metadata(name=package, version="1.0.0"),
                download_info=rez_pip.pip.DownloadInfo(
                    url=f"https://example.com/{package}.whl",
                    archive_info=rez_pip.pip.ArchiveInfo(
                        #
                        # Bad sha256. This will trigger a new download
                        #
                        "hash-a",
                        {"sha256": "asd"},
                    ),
                ),
                is_direct=True,
                requested=True,
            )
        )

        mockedContent = mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet2 = mock.AsyncMock()
    mockedGet2.__aenter__.side_effect = sideEffects

    with mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet2

        wheels = rez_pip.download.downloadPackages(packages, str(tmp_path))

        assert mocked.call_args_list == [
            mock.call(
                "https://example.com/package-a.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
            mock.call(
                "https://example.com/package-b.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/0.1.0",
                },
            ),
        ]

    assert sorted(wheels) == [
        os.fspath(tmp_path / f"{package}.whl") for package in ["package-a", "package-b"]
    ]
