"""Development automation"""
import os

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


@nox.session()
def pyupgrade(session: nox.Session):
    session.install("pyupgrade")

    # print(__file__)

    def getPythonFiles(root, ignore=set()):
        toApply = []

        for root, dirs, files in os.walk(root):
            # Remove paths to ignore
            for path in ignore.intersection(
                {os.path.join(root, dir_) for dir_ in dirs}
            ):
                dirs.remove(os.path.basename(path))

            for file_ in files:
                absPath = os.path.join(root, file_)
                if file_.endswith(".py") and absPath not in ignore:
                    toApply.append(absPath)

        return toApply

    files = getPythonFiles(os.path.join(os.path.dirname(__file__), "src"))
    files.extend(
        getPythonFiles(
            os.path.join(os.path.dirname(__file__), "tests"),
            ignore={os.path.join(os.path.dirname(__file__), "tests", "data")},
        )
    )

    files.extend(getPythonFiles(os.path.join(os.path.dirname(__file__), "scripts")))
    files.append(__file__)

    # TODO: Remove --keep-mock when we drop support for Python 3.7
    session.run("pyupgrade", "--py37-plus", "--keep-mock", *sorted(files))


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11"])
def test(session: nox.Session):
    session.install("-r", "tests/requirements.txt")
    session.install(".")

    session.run(
        "pytest",
        *session.posargs,
    )


@nox.session()
def download_pip(session: nox.Session):
    session.install("packaging", "gidgethub", "aiohttp")

    session.run("python", "./scripts/download_pip.py")
