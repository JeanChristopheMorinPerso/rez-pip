import os
import pathlib
import argparse

import pytest

import rez_pip.cli
import rez_pip.pip
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
        "python_version": None,
        "release": False,
        "requirement": None,
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
        "python_version": None,
        "release": False,
        "requirement": None,
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
        "python_version": None,
        "release": False,
        "requirement": [req.split("=")[-1] for req in files],
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
        "python_version": None,
        "release": False,
        "requirement": None,
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
        "python_version": None,
        "release": False,
        "requirement": None,
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
        match="no packages were passed and --requirements was not used. At least one of the must be passed.",
    ) as exc:
        rez_pip.cli._validateArgs(
            argparse.Namespace(pip=os.fspath(path), packages=None, requirement=None)
        )
