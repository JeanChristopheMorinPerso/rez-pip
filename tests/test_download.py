from __future__ import annotations

import os
import hashlib
import pathlib
import unittest.mock

import pytest
import aiohttp

import rez_pip.pip
import rez_pip.download
from rez_pip.compat import importlib_metadata


@pytest.fixture(scope="module", autouse=True)
def rezPipVersion():
    with unittest.mock.patch.object(
        importlib_metadata, "version", return_value="1.2.3.4.5"
    ):
        yield


class Package:
    def __init__(self, name: str, content: str, local: bool):
        self.name = name
        self.content = content
        self.local = local


class Group:
    def __init__(self, packages: list[Package]):
        self.packages = packages

    def getPackage(self, name: str) -> Package:
        for package in self.packages:
            if package.name == name:
                return package
        raise KeyError(name)


@pytest.mark.parametrize(
    "groups",
    [
        [Group([Package("package-a", "package-a data", False)])],
        [
            Group([Package("package-a", "package-a data", False)]),
            Group([Package("package-b", "package-b data", False)]),
        ],
    ],
    ids=["one-group-with-one-package", "multiple-groups-with-one-package"],
)
def test_download(groups: list[Group], tmp_path: pathlib.Path):
    sideEffects = tuple()
    for group in groups:
        for package in group.packages:
            mockedContent = unittest.mock.MagicMock()
            mockedContent.return_value.__aiter__.return_value = [
                [
                    package.content.encode("utf-8"),
                    None,
                ]
            ]

            sideEffects += (
                unittest.mock.Mock(
                    headers={"content-length": 100},
                    status=200,
                    content=unittest.mock.Mock(iter_chunks=mockedContent),
                ),
            )

    mockedGet = unittest.mock.AsyncMock()
    mockedGet.__aenter__.side_effect = sideEffects

    with unittest.mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet

        _groups = []
        for group in groups:
            infos = []
            for package in group.packages:
                infos.append(
                    rez_pip.pip.PackageInfo(
                        metadata=rez_pip.pip.Metadata(
                            name=package.name, version="1.0.0"
                        ),
                        download_info=rez_pip.pip.DownloadInfo(
                            url=f"https://example.com/{package.name}.whl",
                            archive_info=rez_pip.pip.ArchiveInfo("hash", {}),
                        ),
                        is_direct=True,
                        requested=True,
                    )
                )
            _groups.append(rez_pip.pip.PackageGroup(infos))

        new_groups = rez_pip.download.downloadPackages(_groups, os.fspath(tmp_path))

    assert len(new_groups) == len(groups)
    assert sum(len(group.packages) for group in new_groups) == sum(
        len(group.packages) for group in groups
    )

    wheelsMapping = {
        package.name: package.path for group in new_groups for package in group.packages
    }

    for group in groups:
        for package in group.packages:
            with open(wheelsMapping[package.name]) as fd:
                content = fd.read()
            assert content == package.content

    assert mocked.call_args_list == [
        unittest.mock.call(
            f"https://example.com/{package.name}.whl",
            headers={
                "Content-Type": "application/octet-stream",
                "User-Agent": "rez-pip/1.2.3.4.5",
            },
        )
        for group in groups
        for package in group.packages
    ]


def test_download_skip_local(tmp_path: pathlib.Path):
    """Test that wheels are not downloaded if they are local wheels"""
    groups = [
        rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo](
            [
                rez_pip.pip.PackageInfo(
                    metadata=rez_pip.pip.Metadata(name="package-a", version="1.0.0"),
                    download_info=rez_pip.pip.DownloadInfo(
                        url="file:///example.com/package-a",
                        archive_info=rez_pip.pip.ArchiveInfo("hash-a", {}),
                    ),
                    is_direct=True,
                    requested=True,
                )
            ]
        )
    ]

    mockedGet = unittest.mock.AsyncMock()

    with unittest.mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet
        wheels = rez_pip.download.downloadPackages(groups, os.fspath(tmp_path))

    assert not mocked.called
    data = rez_pip.pip.PackageGroup(
        (
            rez_pip.pip.DownloadedArtifact.from_dict(
                {
                    **groups[0].packages[0].to_dict(),
                    "_localPath": os.path.join(os.fspath(tmp_path), "package-a"),
                }
            ),
        )
    )
    assert wheels == [data]


def test_download_multiple_packages_with_failure(tmp_path: pathlib.Path):
    """
    Test that a failure in one package does not prevent other
    packages from being downloaded
    """
    mockedContent = unittest.mock.MagicMock()
    mockedContent.return_value.__aiter__.return_value = [
        [
            b"package-a data",
            None,
        ]
    ]

    mockedGet = unittest.mock.AsyncMock()
    mockedGet.__aenter__.side_effect = (
        unittest.mock.Mock(
            headers={"content-length": 100},
            status=200,
            content=unittest.mock.Mock(iter_chunks=mockedContent),
        ),
        unittest.mock.Mock(
            headers={"content-length": 100},
            status=400,
            reason="Expected to fail",
            request_info={"key": "here"},
            content=unittest.mock.Mock(iter_chunks=mockedContent),
        ),
    )

    with unittest.mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet
        with pytest.raises(RuntimeError):
            rez_pip.download.downloadPackages(
                [
                    rez_pip.pip.PackageGroup(
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
                            )
                        ]
                    ),
                    rez_pip.pip.PackageGroup(
                        [
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
                            )
                        ]
                    ),
                ],
                os.fspath(tmp_path),
            )

        # Check that package-a was downloaded even if even if package-b failed.
        with open(tmp_path / "package-a") as fd:
            assert fd.read() == "package-a data"

        assert mocked.call_args_list == [
            unittest.mock.call(
                "https://example.com/package-a",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
            unittest.mock.call(
                "https://example.com/package-b",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
        ]


def test_download_reuse_if_same_hash(tmp_path: pathlib.Path):
    """Test that wheels are re-used if the sha256 matches"""
    sideEffects = tuple()
    groups = []

    for package in ["package-a", "package-b"]:
        content = f"{package} data".encode("utf-8")

        hash = hashlib.new("sha256")
        hash.update(content)

        groups.append(
            rez_pip.pip.PackageGroup(
                [
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
                ]
            )
        )

        mockedContent = unittest.mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            unittest.mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=unittest.mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet1 = unittest.mock.AsyncMock()
    mockedGet1.__aenter__.side_effect = sideEffects

    with unittest.mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet1

        rez_pip.download.downloadPackages(groups, str(tmp_path))

        assert mocked.call_args_list == [
            unittest.mock.call(
                "https://example.com/package-a.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
            unittest.mock.call(
                "https://example.com/package-b.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
        ]

    groups = []
    # package-b will be re-used
    for package in ["package-c", "package-b"]:
        content = f"{package} data".encode("utf-8")

        hash = hashlib.new("sha256")
        hash.update(content)

        groups.append(
            rez_pip.pip.PackageGroup(
                [
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
                ]
            )
        )

        mockedContent = unittest.mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            unittest.mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=unittest.mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet2 = unittest.mock.AsyncMock()
    mockedGet2.__aenter__.side_effect = sideEffects

    with unittest.mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet2

        wheels = rez_pip.download.downloadPackages(groups, str(tmp_path))

        assert mocked.call_args_list == [
            unittest.mock.call(
                "https://example.com/package-c.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
        ]

    assert len(wheels) == 2
    assert len(wheels[0].packages) == 1
    assert len(wheels[1].packages) == 1


def test_download_redownload_if_hash_changes(tmp_path: pathlib.Path):
    """Test that wheels are re-downloaded if the sha256 changes"""
    sideEffects = tuple()
    groups = []

    for package in ["package-a", "package-b"]:
        content = f"{package} data".encode("utf-8")

        hash = hashlib.new("sha256")
        hash.update(content)

        groups.append(
            rez_pip.pip.PackageGroup(
                [
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
                ]
            )
        )

        mockedContent = unittest.mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            unittest.mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=unittest.mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet1 = unittest.mock.AsyncMock()
    mockedGet1.__aenter__.side_effect = sideEffects

    with unittest.mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet1

        rez_pip.download.downloadPackages(groups, str(tmp_path))

        assert mocked.call_args_list == [
            unittest.mock.call(
                "https://example.com/package-a.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
            unittest.mock.call(
                "https://example.com/package-b.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
        ]

    groups = []
    for package in ["package-a", "package-b"]:
        content = f"{package} data".encode("utf-8")

        groups.append(
            rez_pip.pip.PackageGroup(
                [
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
                ]
            )
        )

        mockedContent = unittest.mock.MagicMock()
        mockedContent.return_value.__aiter__.return_value = [
            [
                content,
                None,
            ]
        ]

        sideEffects += (
            unittest.mock.Mock(
                headers={"content-length": 100},
                status=200,
                content=unittest.mock.Mock(iter_chunks=mockedContent),
            ),
        )

    mockedGet2 = unittest.mock.AsyncMock()
    mockedGet2.__aenter__.side_effect = sideEffects

    with unittest.mock.patch.object(aiohttp.ClientSession, "get") as mocked:
        mocked.return_value = mockedGet2

        wheels = rez_pip.download.downloadPackages(groups, str(tmp_path))

        assert mocked.call_args_list == [
            unittest.mock.call(
                "https://example.com/package-a.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
            unittest.mock.call(
                "https://example.com/package-b.whl",
                headers={
                    "Content-Type": "application/octet-stream",
                    "User-Agent": "rez-pip/1.2.3.4.5",
                },
            ),
        ]

    assert len(wheels) == 2
    assert len(wheels[0].packages) == 1
    assert len(wheels[1].packages) == 1
