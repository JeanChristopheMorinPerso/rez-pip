import os
import typing

import pytest
import pytest_httpserver

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
def test_download_single_package(
    packages: typing.Dict[str, str],
    httpserver: pytest_httpserver.HTTPServer,
    tmp_path: pytest.TempPathFactory,
):
    for package, content in packages.items():
        httpserver.expect_request(
            f"/{package}", method="GET", headers={"User-Agent": "rez-pip/0.1.0"}
        ).respond_with_data(content)

    wheels = rez_pip.download.downloadPackages(
        [
            rez_pip.pip.PackageInfo(
                metadata={"name": package, "version": "1.0.0"},
                download_info=rez_pip.pip.DownloadInfo(
                    url=httpserver.url_for(f"/{package}"), archive_info="asdasd"
                ),
                is_direct=True,
                requested=True,
            )
            for package in packages
        ],
        os.fspath(tmp_path),
    )

    assert wheels == [os.fspath(tmp_path / package) for package in packages]
    for wheel in wheels:
        with open(wheel, "r") as fd:
            content = fd.read()
        assert packages[os.path.basename(wheel)] == content


def test_download_multiple_packages_with_failure(
    httpserver: pytest_httpserver.HTTPServer, tmp_path: pytest.TempPathFactory
):
    httpserver.expect_request(
        "/package-a", method="GET", headers={"User-Agent": "rez-pip/0.1.0"}
    ).respond_with_data("package-a data")
    httpserver.expect_request(
        "/package-b", method="GET", headers={"User-Agent": "rez-pip/0.1.0"}
    ).respond_with_data(response_data="package-b data", status=202)

    with pytest.raises(RuntimeError):
        rez_pip.download.downloadPackages(
            [
                rez_pip.pip.PackageInfo(
                    metadata={"name": "package-a", "version": "1.0.0"},
                    download_info=rez_pip.pip.DownloadInfo(
                        url=httpserver.url_for("/package-a"), archive_info="asdasd"
                    ),
                    is_direct=True,
                    requested=True,
                ),
                rez_pip.pip.PackageInfo(
                    metadata={"name": "package-b", "version": "1.0.0"},
                    download_info=rez_pip.pip.DownloadInfo(
                        url=httpserver.url_for("/package-b"), archive_info="asdasd"
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
