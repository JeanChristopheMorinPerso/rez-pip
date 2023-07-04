import os
import sys
import logging
import pathlib
import argparse
import subprocess
import unittest.mock

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import pytest
import rich.console

import rez_pip.cli
import rez_pip.pip
import rez_pip.rez
import rez_pip.exceptions


def test_parseArgs_empty():
    args, pipArgs = rez_pip.cli._parseArgs([])
    assert vars(args) == {
        "constraint": None,
        "keep_tmp_dirs": False,
        "log_level": "info",
        "packages": [],
        "pip": rez_pip.pip.getBundledPip(),
        "prefix": None,
        "python_version": "3.7+",
        "release": False,
        "requirement": None,
        "debug_info": False,
    }

    assert pipArgs == []


@pytest.mark.parametrize("packages", [["package-a"], ["package-a", "package-b"]])
def test_parseArgs_packages(packages):
    args, pipArgs = rez_pip.cli._parseArgs(packages)
    assert vars(args) == {
        "constraint": None,
        "keep_tmp_dirs": False,
        "log_level": "info",
        "packages": packages,
        "pip": rez_pip.pip.getBundledPip(),
        "prefix": None,
        "python_version": "3.7+",
        "release": False,
        "requirement": None,
        "debug_info": False,
    }

    assert pipArgs == []


@pytest.mark.parametrize("files", [["-r=req1"], ["--requirement=req1", "-r=req2"]])
def test_parseArgs_no_package_with_requirements(files):
    args, pipArgs = rez_pip.cli._parseArgs(files)
    assert vars(args) == {
        "constraint": None,
        "keep_tmp_dirs": False,
        "log_level": "info",
        "packages": [],
        "pip": rez_pip.pip.getBundledPip(),
        "prefix": None,
        "python_version": "3.7+",
        "release": False,
        "requirement": [req.split("=")[-1] for req in files],
        "debug_info": False,
    }

    assert pipArgs == []


def test_parseArgs_constraints():
    args, pipArgs = rez_pip.cli._parseArgs(["-c", "asd", "-c", "adasdasd"])
    assert vars(args) == {
        "constraint": ["asd", "adasdasd"],
        "keep_tmp_dirs": False,
        "log_level": "info",
        "packages": [],
        "pip": rez_pip.pip.getBundledPip(),
        "prefix": None,
        "python_version": "3.7+",
        "release": False,
        "requirement": None,
        "debug_info": False,
    }

    assert pipArgs == []


def test_parseArgs_pipArgs():
    args, pipArgs = rez_pip.cli._parseArgs(
        ["-l", "info", "--", "adasdasd", "--requirement", "asd.txt"]
    )
    assert vars(args) == {
        "constraint": None,
        "keep_tmp_dirs": False,
        "log_level": "info",
        "packages": [],
        "pip": rez_pip.pip.getBundledPip(),
        "prefix": None,
        "python_version": "3.7+",
        "release": False,
        "requirement": None,
        "debug_info": False,
    }

    assert pipArgs == ["adasdasd", "--requirement", "asd.txt"]


def test_validateArgs_pip_good(tmp_path: pathlib.Path):
    path = pathlib.Path(tmp_path / "asd.pyz")

    path.touch()

    rez_pip.cli._validateArgs(
        argparse.Namespace(pip=os.fspath(path), packages=["asd"], requirement=None)
    )


def test_validateArgs_pip_bad(tmp_path: pathlib.Path):
    path = tmp_path / "asd.txt"

    path.touch()

    with pytest.raises(rez_pip.exceptions.RezPipError):
        rez_pip.cli._validateArgs(
            argparse.Namespace(pip=os.fspath(path), packages=["asd"], requirement=None)
        )


def test_validateArgs_pip_not_exists(tmp_path: pathlib.Path):
    path = tmp_path / "asd.pyz"

    with pytest.raises(rez_pip.exceptions.RezPipError) as exc:
        rez_pip.cli._validateArgs(
            argparse.Namespace(pip=os.fspath(path), packages=["asd"], requirement=None)
        )

    assert exc.value.message == f"zipapp at {os.fspath(path)!r} does not exist"


def test_validateArgs_no_packages_or_requirement(tmp_path: pathlib.Path):
    path = tmp_path / "asd.pyz"

    path.touch()

    with pytest.raises(
        rez_pip.exceptions.RezPipError,
        match="no packages were passed and --requirements was not used. At least one of them must be passed.",
    ) as exc:
        rez_pip.cli._validateArgs(
            argparse.Namespace(pip=os.fspath(path), packages=None, requirement=None)
        )


@pytest.fixture()
def resetLogger():
    logger = logging.getLogger("rez_pip")
    level = logger.level
    handlers = logger.handlers

    yield

    logger = logging.getLogger("rez_pip")
    logger.setLevel(level)

    for handler in logger.handlers:
        logger.removeHandler(handler)

    for handler in handlers:
        logger.addHandler(handler)


@pytest.mark.usefixtures("resetLogger")
def test_run_without_arguments(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "argv", ["rez-pip"])
    assert rez_pip.cli.run() == 1


@pytest.mark.usefixtures("resetLogger")
def test_run(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory):
    monkeypatch.setattr(sys, "argv", ["rez-pip", "example"])

    tmppath = tmp_path_factory.mktemp("test_run")

    def mkdtemp(*args, **kwargs) -> str:
        return os.fspath(tmppath)

    with unittest.mock.patch("rez_pip.cli._run") as mocked:
        with unittest.mock.patch(
            "rez_pip.cli.tempfile.mkdtemp", side_effect=mkdtemp
        ) as mockedMkdtemp:
            assert rez_pip.cli.run() == 0

    assert mocked.called
    assert mockedMkdtemp.called

    assert not tmppath.exists()


@pytest.mark.usefixtures("resetLogger")
def test_run_removes_tmp_dirs_even_with_exceptions(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
):
    monkeypatch.setattr(sys, "argv", ["rez-pip", "example"])

    tmppath = tmp_path_factory.mktemp("test_run")

    def mkdtemp(*args, **kwargs) -> str:
        return os.fspath(tmppath)

    with unittest.mock.patch("rez_pip.cli._run", side_effect=RuntimeError) as mocked:
        with unittest.mock.patch(
            "rez_pip.cli.tempfile.mkdtemp", side_effect=mkdtemp
        ) as mockedMkdtemp:
            with pytest.raises(RuntimeError):
                assert rez_pip.cli.run() == 0

    assert mocked.called
    assert mockedMkdtemp.called

    assert not tmppath.exists()


@pytest.mark.usefixtures("resetLogger")
def test_run_keep_tmp_dirs_even_with_exceptions(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
):
    monkeypatch.setattr(sys, "argv", ["rez-pip", "example", "--keep-tmp-dirs"])

    tmppath = tmp_path_factory.mktemp("test_run")

    def mkdtemp(*args, **kwargs) -> str:
        return os.fspath(tmppath)

    with unittest.mock.patch("rez_pip.cli._run", side_effect=RuntimeError) as mocked:
        with unittest.mock.patch(
            "rez_pip.cli.tempfile.mkdtemp", side_effect=mkdtemp
        ) as mockedMkdtemp:
            with pytest.raises(RuntimeError):
                assert rez_pip.cli.run() == 0

    assert mocked.called
    assert mockedMkdtemp.called

    assert tmppath.exists()


@pytest.mark.usefixtures("resetLogger")
def test_run_keep_tmp_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
):
    monkeypatch.setattr(sys, "argv", ["rez-pip", "example", "--keep-tmp-dirs"])

    tmppath = tmp_path_factory.mktemp("test_run")

    def mkdtemp(*args, **kwargs) -> str:
        return os.fspath(tmppath)

    with unittest.mock.patch("rez_pip.cli._run") as mocked:
        with unittest.mock.patch(
            "rez_pip.cli.tempfile.mkdtemp", side_effect=mkdtemp
        ) as mockedMkdtemp:
            assert rez_pip.cli.run() == 0

    assert mocked.called
    assert mockedMkdtemp.called

    assert tmppath.exists()


@pytest.mark.usefixtures("resetLogger")
def test_run_with_debug_info(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "argv", ["rez-pip", "example", "--debug-info"])
    with unittest.mock.patch("rez_pip.cli._run") as mockedRun:
        with unittest.mock.patch("rez_pip.cli._debug") as mockedDebug:
            assert rez_pip.cli.run() == 0

    assert not mockedRun.called
    assert mockedDebug.called


@pytest.mark.skip("TODO: Figure out why it is failing")
def test_debug(capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        rez_pip.rez,
        "getPythonExecutables",
        lambda x: {
            "3.7.15": "/path/to/python-3.7.15",
            "3.100.7": "/path/to/another/python-3.100.7",
        },
    )

    monkeypatch.setitem(os.environ, "TERM", "dumb")
    with unittest.mock.patch(
        "subprocess.run",
        side_effect=(
            unittest.mock.Mock(stdout="mocked pip --version"),
            unittest.mock.Mock(stdout="mocked pip config debug"),
            unittest.mock.Mock(stdout="mocked pip config list"),
        ),
    ) as mocked:
        rez_pip.cli._debug(
            argparse.Namespace(pip=None, python_version="2.7+"),
            console=rich.console.Console(),
        )

    assert mocked.call_args_list == [
        unittest.mock.call(
            [sys.executable, rez_pip.pip.getBundledPip(), "--version"],
            stdout=subprocess.PIPE,
            text=True,
        ),
        unittest.mock.call(
            [sys.executable, rez_pip.pip.getBundledPip(), "config", "debug"],
            stdout=subprocess.PIPE,
            text=True,
        ),
        unittest.mock.call(
            [sys.executable, rez_pip.pip.getBundledPip(), "config", "list"],
            stdout=subprocess.PIPE,
            text=True,
        ),
    ]

    captured = capsys.readouterr()

    assert (
        captured.out
        == f"""rez-pip version: {importlib_metadata.version("rez-pip")}
rez version: 2.112.0
python version: {sys.version}
python executable: {sys.executable}
pip: {rez_pip.pip.getBundledPip()}
pip version: mocked pip --version
rez-pip provided arguments:
  {{
      "pip": null,
      "python_version": "2.7+"
  }}
pip config debug:
  mocked pip config debug
pip config list:
  mocked pip config list
rez python packages:
  /path/to/python-3.7.15 (3.7.15)
  /path/to/another/python-3.100.7 (3.100.7)

"""
    )
