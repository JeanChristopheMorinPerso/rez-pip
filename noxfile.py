# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""Development automation"""

import nox

# nox.options.sessions = ["lint", "test", "doctest"]
nox.options.reuse_existing_virtualenvs = True


@nox.session()
def lint(session: nox.Session):
    pass


@nox.session()
def mypy(session: nox.Session):
    session.install(".", "mypy")

    session.run("mypy")


@nox.session()
def format(session: nox.Session):
    session.install("black")

    session.run("black", ".", "--check")


@nox.session(python=["3.8", "3.9", "3.10", "3.11"])
def test(session: nox.Session):
    session.install(".", "-r", "tests/requirements.txt")

    session.run(
        "pytest",
        *session.posargs,
    )


@nox.session()
def download_pip(session: nox.Session):
    session.install("packaging", "gidgethub", "aiohttp")

    session.run("python", "./scripts/download_pip.py")


@nox.session()
def reuse(session: nox.Session):
    session.install("reuse")
    session.run("reuse", "lint", *session.posargs)
