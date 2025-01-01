import sys
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


@pytest.fixture(scope="module")
def setupPluginManager():
    yield utils.initializePluginManager("shiboken6")


def fakePackage(name: str, **kwargs) -> mock.Mock:
    value = mock.MagicMock()
    value.configure_mock(name=name, **kwargs)
    return value


@pytest.mark.parametrize("package", [fakePackage("asd")])
def test_cleanup_noop(package, tmp_path: pathlib.Path):
    (tmp_path / "python" / "PySide6").mkdir(parents=True)

    rez_pip.plugins.getHook().cleanup(dist=package, path=tmp_path)

    assert (tmp_path / "python" / "PySide6").exists()


@pytest.mark.parametrize(
    "package",
    [
        fakePackage("shiboken6"),
        fakePackage("shiboken6_essentials"),
        fakePackage("ShIbOkEn6-AddoNs"),
    ],
)
def test_cleanup(package, tmp_path: pathlib.Path):
    (tmp_path / "python" / "PySide6").mkdir(parents=True)

    rez_pip.plugins.getHook().cleanup(dist=package, path=tmp_path)

    assert not (tmp_path / "python" / "shiboken6").exists()
