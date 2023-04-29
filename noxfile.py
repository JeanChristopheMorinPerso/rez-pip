"""Development automation"""
import os
import re
import json
import platform
import urllib.request

import nox

# nox.options.sessions = ["lint", "test", "doctest"]
nox.options.reuse_existing_virtualenvs = True


@nox.session()
def lint(session: nox.Session):
    pass


@nox.session()
def mypy(session: nox.Session):
    session.install("mypy")
    session.install(".")

    session.run("mypy")


@nox.session()
def format(session: nox.Session):
    session.install("black")

    session.run("black", ".", "--check")


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11"])
def test(session: nox.Session):
    session.install("-r", "tests/requirements.txt")
    session.install(".")

    session.run(
        "pytest",
        "-v",
        "--strict-markers",
        "--cov=rez_pip",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-report=xml",
        *session.posargs,
    )


@nox.session()
def update_pip(session: nox.Session):
    pass


@nox.session(name="pre-test")
def pre_test(session: nox.Session):
    downloadDir = os.path.join("tests", "data", "_tmp_download")
    try:
        os.makedirs(downloadDir)
    except FileExistsError:
        pass

    versions = ["2.7.18", "3.11.3"]

    urls = {}
    if platform.system() == "Windows":
        for version in versions:
            nugetName = "python"
            if version[0] == "2":
                nugetName += "2"
            urls[
                version
            ] = f"https://globalcdn.nuget.org/packages/{nugetName}.{version}.nupkg"

    else:
        with urllib.request.urlopen(
            "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"
        ) as fd:
            versionsManifest = json.load(fd)

        for manifest in versionsManifest:
            if manifest["version"] in versions:
                for version in manifest["files"]:
                    if (
                        version["arch"] == "x64"
                        and version["platform"] == platform.system().lower()
                    ):
                        urls[manifest["version"]] = version["download_url"]
                        break
                else:
                    session.error(
                        f"Failed to find URL for Python {manifest['version']}"
                    )

    for version, url in urls.items():
        ext = re.findall(r"\.([a-z]\w+(?:\.?[a-z0-9]+))", url.split("/")[-1])[0]
        filename = f"python-{version}-{platform.system().lower()}.{ext}"

        path = os.path.join(downloadDir, filename)
        if os.path.exists(path):
            session.log(f"Skipping {url} because {path!r} already exists")
            continue

        session.log(f"Downloading {url} to {path!r}")
        with urllib.request.urlopen(url) as archive:
            with open(f"{downloadDir}/{filename}", "wb") as targetFile:
                targetFile.write(archive.read())
