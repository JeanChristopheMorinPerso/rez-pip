"""Development automation"""
import os
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
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"
    ) as fd:
        versionsManifest = json.load(fd)

    downloadDir = os.path.join("tests", "data", "python")
    try:
        os.makedirs(downloadDir)
    except FileExistsError:
        pass

    versions = ["2.7.18", "3.11.3"]

    platformMap = {"Linux": "linux", "Windows": "win32", "Darwin": "darwin"}

    for manifest in versionsManifest:
        if manifest["version"] in versions:
            for version in manifest["files"]:
                if (
                    version["arch"] == "x64"
                    and version["platform"] == platformMap[platform.system()]
                ):
                    path = f"{downloadDir}/{version['filename']}"
                    if os.path.exists(path):
                        break

                    with urllib.request.urlopen(version["download_url"]) as fd:
                        session.log(
                            f"Downloading {version['download_url']} to {path!r}"
                        )
                        with open(f"{downloadDir}/{version['filename']}", "wb") as fd2:
                            fd2.write(fd.read())
                            break

            else:
                session.error(f"Failed to find URL for Python {manifest['version']}")
