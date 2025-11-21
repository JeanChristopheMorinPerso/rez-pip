# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import stat
import pathlib
import unittest.mock
import importlib
import pytest

import rez_pip.plugins


@pytest.fixture(scope="module", autouse=True)
def setupPluginManager():
    manager = rez_pip.plugins.getManager()
    spec = importlib.util.spec_from_file_location(
        "set_permissions",
        os.path.join(os.path.dirname(__file__), "set_permissions.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manager.register(
        module,
        name="rez_pip.set_permissions",
    )
    try:
        yield manager
    finally:
        del manager
        rez_pip.plugins.getManager.cache_clear()


def fakeVariant(root: str, **kwargs) -> unittest.mock.Mock:
    value = unittest.mock.MagicMock()
    value.configure_mock(root=root, **kwargs)
    return value


def fakePackage(
    name: str, installed_variants: tuple[fakeVariant, ...], **kwargs
) -> unittest.mock.Mock:
    value = unittest.mock.MagicMock()
    value.configure_mock(name=name, installed_variants=installed_variants, **kwargs)
    return value


def test_postInstall(tmp_path: pathlib.Path):
    (tmp_path / "python" / "kiwisolver").mkdir(parents=True)
    file_path = tmp_path / "python" / "kiwisolver" / "test_file.exe"
    file_path.touch()
    os.chmod(file_path, stat.S_IREAD)

    package = fakePackage("kiwisolver", installed_variants=[fakeVariant(root=tmp_path)])

    assert not os.access(
        os.path.join(tmp_path, "python", "kiwisolver", "test_file.exe"), os.W_OK
    )

    rez_pip.plugins.getHook().postInstall(package=package)

    assert os.access(
        os.path.join(tmp_path, "python", "kiwisolver", "test_file.exe"), os.W_OK
    )
