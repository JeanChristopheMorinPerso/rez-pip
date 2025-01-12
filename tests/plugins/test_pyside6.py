import os
import sys
import typing
import pathlib

import pytest

import rez_pip.pip
import rez_pip.plugins
import rez_pip.exceptions

from . import utils


if sys.version_info[:2] < (3, 8):
    import mock
else:
    from unittest import mock


@pytest.fixture(scope="module", autouse=True)
def setupPluginManager():
    yield utils.initializePluginManager("pyside6")


@pytest.mark.parametrize(
    "packages",
    [
        ("asd",),
        ("pyside6",),
        ("PysiDe6",),
        ("pyside6", "pyside6-addons"),
        ("pyside6", "pyside6-essentials"),
        ("pyside6", "pyside6-essentials", "pyside6-addons"),
        ("pyside6", "pyside6-addons", "asdasdad"),
    ],
)
def test_prePipResolve_noop(packages: typing.Tuple[str, ...]):
    rez_pip.plugins.getHook().prePipResolve(packages=packages)


@pytest.mark.parametrize("packages", [("pyside6-addons",), ("PysiDe6_essentials",)])
def test_prePipResolve_raises(packages: typing.Tuple[str, ...]):
    with pytest.raises(rez_pip.exceptions.RezPipError):
        rez_pip.plugins.getHook().prePipResolve(packages=packages)


def fakePackage(name: str, **kwargs) -> mock.Mock:
    value = mock.MagicMock()
    value.configure_mock(name=name, **kwargs)
    return value


@pytest.mark.parametrize(
    "packages",
    [
        (fakePackage("asd"),),
        (fakePackage("pyside6"),),
        (fakePackage("PysiDe6"),),
        (fakePackage("pyside6"), fakePackage("pyside6-addons")),
        (fakePackage("pyside6"), fakePackage("pyside6-essentials")),
        (
            fakePackage("pyside6"),
            fakePackage("pyside6-essentials"),
            fakePackage("pyside6-addons"),
        ),
        (
            fakePackage("pyside6"),
            fakePackage("pyside6-addons"),
            fakePackage("asdasdad"),
        ),
    ],
)
def test_postPipResolve_noop(packages: typing.Tuple[str, ...]):
    rez_pip.plugins.getHook().postPipResolve(packages=packages)


@pytest.mark.parametrize(
    "packages",
    [
        (fakePackage("pyside6-addons"),),
        (fakePackage("PysiDe6_essentials"),),
        (fakePackage("PysiDe6_essentials"), fakePackage("asd")),
    ],
)
def test_postPipResolve_raises(packages: typing.Tuple[str, ...]):
    with pytest.raises(rez_pip.exceptions.RezPipError):
        rez_pip.plugins.getHook().postPipResolve(packages=packages)


@pytest.mark.parametrize(
    "packages",
    [[fakePackage("asd")]],
)
def test_groupPackages_noop(packages: typing.List[str]):
    assert rez_pip.plugins.getHook().groupPackages(packages=packages) == [
        [rez_pip.pip.PackageGroup(tuple())]
    ]


class FakePackageInfo:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    def __eq__(self, value):
        return self.name == value.name and self.version == value.version


@pytest.mark.parametrize(
    "packages,expectedGroups",
    [
        [
            [fakePackage("pyside6", version="1")],
            [[rez_pip.pip.PackageGroup((FakePackageInfo("pyside6", "1"),))]],
        ],
        [
            [
                fakePackage("pyside6", version="1"),
                fakePackage("pyside6_addons", version="1"),
            ],
            [
                [
                    rez_pip.pip.PackageGroup(
                        (
                            FakePackageInfo("pyside6", "1"),
                            FakePackageInfo("pyside6_addons", "1"),
                        )
                    )
                ]
            ],
        ],
        [
            [
                fakePackage("pyside6", version="1"),
                fakePackage("pyside6_essentials", version="1"),
            ],
            [
                [
                    rez_pip.pip.PackageGroup(
                        (
                            FakePackageInfo("pyside6", "1"),
                            FakePackageInfo("pyside6_essentials", "1"),
                        )
                    )
                ]
            ],
        ],
        [
            [
                fakePackage("pyside6", version="1"),
                fakePackage("pyside6_essentials", version="1"),
                fakePackage("pyside6-Addons", version="1"),
            ],
            [
                [
                    rez_pip.pip.PackageGroup(
                        (
                            FakePackageInfo("pyside6", "1"),
                            FakePackageInfo("pyside6_essentials", "1"),
                            FakePackageInfo("pyside6-Addons", "1"),
                        )
                    )
                ]
            ],
        ],
        [
            [
                fakePackage("pyside6", version="1"),
                fakePackage("asdasd", version=2),
                fakePackage("pyside6_essentials", version="1"),
                fakePackage("pyside6-Addons", version="1"),
            ],
            [
                [
                    rez_pip.pip.PackageGroup(
                        (
                            FakePackageInfo("pyside6", "1"),
                            FakePackageInfo("pyside6_essentials", "1"),
                            FakePackageInfo("pyside6-Addons", "1"),
                        )
                    )
                ]
            ],
        ],
    ],
)
def test_groupPackages(
    packages: typing.List[str], expectedGroups: typing.List[rez_pip.pip.PackageGroup]
):
    data = rez_pip.plugins.getHook().groupPackages(packages=packages)
    assert data == expectedGroups


@pytest.mark.parametrize("package", [fakePackage("asd")])
def test_cleanup_noop(package, tmp_path: pathlib.Path):
    (tmp_path / "python" / "shiboken6").mkdir(parents=True)
    (tmp_path / "python" / "shiboken6_generator").mkdir(parents=True)

    rez_pip.plugins.getHook().cleanup(dist=package, path=tmp_path)

    assert (tmp_path / "python" / "shiboken6").exists()
    assert (tmp_path / "python" / "shiboken6_generator").exists()


@pytest.mark.parametrize(
    "package,expectedPaths",
    [
        [fakePackage("pyside6"), ["shiboken6", "shiboken6_generator"]],
        [
            fakePackage("pyside6_essentials"),
            [
                "shiboken6",
                "shiboken6_generator",
                os.path.join("PySide6", "__init__.py"),
            ],
        ],
        [
            fakePackage("PySiDe6-AddoNs"),
            [
                "shiboken6",
                "shiboken6_generator",
                os.path.join("PySide6", "__init__.py"),
            ],
        ],
    ],
)
def test_cleanup(package, expectedPaths: typing.List[str], tmp_path: pathlib.Path):
    actions = rez_pip.plugins.getHook().cleanup(dist=package, path=tmp_path)

    expectedActions = []
    for path in expectedPaths:
        expectedActions.append(
            rez_pip.plugins.CleanupAction(
                "remove",
                str(tmp_path / "python" / path),
            )
        )
    assert actions == [[], expectedActions]
