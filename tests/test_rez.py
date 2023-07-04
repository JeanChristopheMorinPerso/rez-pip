import sys
import typing
import unittest.mock

import pytest
import rez.config
import rez.packages
import rez.package_repository

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import rez_pip.rez


def test_convertMetadata_nothing_to_convert(monkeypatch: pytest.MonkeyPatch):
    dist = importlib_metadata.Distribution()
    monkeypatch.setattr(
        dist,
        "read_text",
        lambda x: "Metadata-Version: 2.0\nName: package_a\nVersion: 1.0.0",
    )

    converted, remaining = rez_pip.rez._convertMetadata(dist)
    assert converted == {}
    assert remaining == {}

    # Assert that the original metadata is intact
    assert dist.metadata["Metadata-Version"]


@pytest.mark.parametrize(
    "metadataText,expectedConverted,expectedRemaining",
    [
        ["Summary: This is a summary", {"summary": "This is a summary"}, {}],
        [
            "Description: This is a description",
            {"description": "This is a description"},
            {},
        ],
        ["Author: Joe", {"authors": ["Joe"]}, {}],
        [
            "Author-email: Joe <joe@example.com>",
            {"authors": ["Joe <joe@example.com>"]},
            {},
        ],
        [
            "Author-email: Joe <joe@example.com>,Joe2 <joe2@example.com> , Joe3 asd <joe3@example.com> ",
            {
                "authors": [
                    "Joe <joe@example.com>",
                    "Joe2 <joe2@example.com>",
                    "Joe3 asd <joe3@example.com>",
                ]
            },
            {},
        ],
        ["Maintainer: Example", {"authors": ["Example"]}, {}],
        [
            "Maintainer-email: Example <example@example.com>",
            {"authors": ["Example <example@example.com>"]},
            {},
        ],
        [
            "Maintainer-email: Joe <joe@example.com>,Joe2 <joe2@example.com> , Joe3 asd <joe3@example.com> ",
            {
                "authors": [
                    "Joe <joe@example.com>",
                    "Joe2 <joe2@example.com>",
                    "Joe3 asd <joe3@example.com>",
                ]
            },
            {},
        ],
        [
            "Author: Jo1\nAuthor-email: asd@example.com\nMaintainer: <something@example.com>\nMaintainer-email: Joe <joe@example.com>",
            {
                "authors": [
                    "Jo1",
                    "asd@example.com",
                    "<something@example.com>",
                    "Joe <joe@example.com>",
                ]
            },
            {},
        ],
        # License from License field
        ["License: Apache-2.0", {"license": "Apache-2.0"}, {}],
        [
            "Classifier: asdasd :: something",
            {},
            {"classifier": ["asdasd :: something"]},
        ],
        # License from classifier
        [
            "Classifier: License :: Some license",
            {"license": "Some license"},
            {"classifier": ["License :: Some license"]},
        ],
        # When reading license from classifiers, skip if more than one license found
        [
            "Classifier: License :: Some license1\nClassifier: License :: Some license2",
            {},
            {"classifier": ["License :: Some license1", "License :: Some license2"]},
        ],
        [
            "Home-page: https://example.com",
            {"help": [["Home-page", "https://example.com"]]},
            {},
        ],
        [
            "Project-URL: Documentation, https://example.com/docs",
            {"help": [["Documentation", "https://example.com/docs"]]},
            {},
        ],
        [
            "Project-URL: Documentation, https://example.com/docs\nProject-URL: Other, https://example.com/other",
            {
                "help": [
                    ["Documentation", "https://example.com/docs"],
                    ["Other", "https://example.com/other"],
                ]
            },
            {},
        ],
        [
            "Download-URL: https://example.com/download",
            {"help": [["Download-URL", "https://example.com/download"]]},
            {},
        ],
        # Test additive links
        [
            "Home-page: https://example.com/home\nProject-URL: Documentation, https://example.com/docs\nProject-URL: Other, https://example.com/other\nDownload-URL: https://example.com/download",
            {
                "help": [
                    ["Home-page", "https://example.com/home"],
                    ["Documentation", "https://example.com/docs"],
                    ["Other", "https://example.com/other"],
                    ["Download-URL", "https://example.com/download"],
                ],
            },
            {},
        ],
        # Test remaining values
        [
            "Author: me\nTotally-random: some value here",
            {"authors": ["me"]},
            {"totally_random": "some value here"},
        ],
    ],
)
def test_convertMetadata(
    metadataText: str,
    expectedConverted,
    expectedRemaining,
    monkeypatch: pytest.MonkeyPatch,
):
    dist = importlib_metadata.Distribution()
    monkeypatch.setattr(
        dist,
        "read_text",
        lambda x: f"Metadata-Version: 2.0\nName: package_a\nVersion: 1.0.0\n{metadataText}",
    )

    converted, remaining = rez_pip.rez._convertMetadata(dist)
    assert converted == expectedConverted
    assert remaining == expectedRemaining

    # Assert that the original metadata is intact
    assert dist.metadata["Metadata-Version"]


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
