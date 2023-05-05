import typing
import unittest.mock

import pytest
import rez.config
import rez.packages
import rez.package_repository

import rez_pip.rez


@pytest.mark.parametrize(
    "availableVersions,range_,executables,expectedExecutables",
    [
        pytest.param(
            ["1.0.0"],
            "latest",
            ["python1.0"],
            {"1.0.0": "/path/python1.0"},
            id="latest",
        ),
        pytest.param(
            ["1.0.0"],
            None,
            ["python1.0"],
            {"1.0.0": "/path/python1.0"},
            id="all-single-version",
        ),
        pytest.param(
            ["1.0.0"],
            None,
            ["", "python1"],
            {"1.0.0": "/path/python1"},
            id="all-single-version-python1",
        ),
        pytest.param(
            ["1.0.0"],
            None,
            ["", "", "python"],
            {"1.0.0": "/path/python"},
            id="all-single-version-python-no-version",
        ),
        pytest.param(
            ["1.0.0"],
            None,
            ["", "", ""],
            {},
            id="all-single-version-no-exe",
        ),
        pytest.param(
            ["1.0.0", "2.0.0"],
            None,
            ["python1.0", "python2.0"],
            {"1.0.0": "/path/python1.0", "2.0.0": "/path/python2.0"},
            id="all-multi-version",
        ),
        pytest.param(
            ["1.0.0", "2.0.0"],
            None,
            ["", "", "", "python2.0"],
            {"2.0.0": "/path/python2.0"},
            id="all-multi-version-no-exe-1.0.0",
        ),
        pytest.param(
            ["1.0.0", "2.0.0"],
            "2+",
            ["python2.0"],
            {"2.0.0": "/path/python2.0"},
            id="with-range-2plus",
        ),
        pytest.param(
            ["1.0.0", "2.0.0"],
            "<2",
            ["python1.0"],
            {"1.0.0": "/path/python1.0"},
            id="with-range-less-than-2",
        ),
    ],
)
def test_getPythonExecutables(
    monkeypatch: pytest.MonkeyPatch,
    availableVersions: typing.List[str],
    range_: typing.Optional[str],
    executables: typing.List[str],
    expectedExecutables: typing.Dict[str, str],
) -> None:
    repoData: typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]] = {"python": {}}

    for version in availableVersions:
        repoData["python"][version] = {"version": version}

    repo = typing.cast(
        rez.package_repository.PackageRepository,
        rez.package_repository.create_memory_package_repository(repoData),
    )

    with monkeypatch.context() as context:
        context.setitem(
            rez.package_repository.package_repository_manager.repositories,
            f"memory@{repo.location}",
            repo,
        )

        context.setattr(rez.config.config, "packages_path", [f"memory@{repo.location}"])

        with unittest.mock.patch(
            "rez.resolved_context.ResolvedContext.which"
        ) as mocked:
            mocked.side_effect = ["/path/" + exe if exe else "" for exe in executables]

            assert (
                rez_pip.rez.getPythonExecutables(range_, "python")
                == expectedExecutables
            )
