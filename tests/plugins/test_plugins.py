# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pluggy

import rez_pip.plugins


def test_getManager():
    assert isinstance(rez_pip.plugins.getManager(), pluggy.PluginManager)


def test_getHook():
    assert isinstance(rez_pip.plugins.getHook(), pluggy.HookRelay)


def test_getHookImplementations():
    implementations = rez_pip.plugins._getHookImplementations()
    assert implementations == {
        "rez_pip.PySide6": [
            "cleanup",
            "groupPackages",
            "patches",
            "postPipResolve",
            "prePipResolve",
        ],
        "rez_pip.shiboken6": ["cleanup"],
    }
