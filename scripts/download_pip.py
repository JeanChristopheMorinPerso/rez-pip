import os
import sys
import asyncio
import tempfile
import subprocess

import aiohttp
import gidgethub.aiohttp
import packaging.version

BUNDLED_PIP_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "src", "rez_pip", "data", "pip.pyz")
)
TMP_DIR = os.environ.get("RUNNER_TEMP", tempfile.gettempdir())


async def getLatestPip(session: aiohttp.ClientSession) -> packaging.version.Version:
    response = await session.get(
        "https://pypi.org/pypi/pip/json",
        headers={"Content-Type": "application/json"},
    )

    pypiInfo = await response.json()
    releases = pypiInfo["releases"]

    latest = sorted(releases, key=lambda x: packaging.version.parse(x))[-1]
    return packaging.version.parse(latest)


def getVersionFromZipApp(path: str) -> packaging.version.Version:
    bundledVersion = (
        subprocess.check_output(
            [
                "python",
                path,
                "--version",
            ],
            text=True,
        )
        .strip()
        .split(" ")[1]
    )

    return packaging.version.parse(bundledVersion)


async def createPullRequest(session: aiohttp.ClientSession) -> None:
    pass


async def updatePullRequest(session: aiohttp.ClientSession, pr: dict) -> None:
    pass


async def downloadNewPip(
    session: aiohttp.ClientSession, version: packaging.version.Version
) -> str:
    downloadPath = os.path.join(TMP_DIR, f"pip-{version}.pyz")

    async with session.get(
        # TODO: Use specific version once https://github.com/pypa/get-pip/issues/189 gets merged and released.
        "https://bootstrap.pypa.io/pip/pip.pyz",
        headers={
            "Content-Type": "application/octet-stream",
            "User-Agent": "rez-pip/0.1.0",
        },
    ) as response:
        with open(downloadPath, "wb") as fd:
            fd.write(await response.read())

    downloadedVersion = getVersionFromZipApp(downloadPath)

    assert (
        downloadedVersion == version
    ), f"The downloaded pip version is {downloadedVersion} but expected it to be {version}"

    return downloadPath


def createGHAOutputVariable(name: str, value: str):
    if githubOutput := os.environ.get("GITHUB_OUTPUT", ""):
        with open(githubOutput, "a", encoding="utf-8") as fd:
            fd.write(f"{name}={value}\n")


async def main():
    async with aiohttp.ClientSession() as session:
        latestPipVersion = await getLatestPip(session)
        print(f"latest pip version on PyPI is {latestPipVersion}")

        bundledPipVersion = getVersionFromZipApp(BUNDLED_PIP_PATH)
        print(f"The bundled pip version is {bundledPipVersion}")

        createGHAOutputVariable("previous-pip-version", str(bundledPipVersion))

        if latestPipVersion <= bundledPipVersion:
            createGHAOutputVariable("downloaded-pip-path", "none")
            createGHAOutputVariable("new-pip-version", "none")
            return

        downloadPath = await downloadNewPip(session, latestPipVersion)
        print(
            f"Downloaded pip {latestPipVersion} to {downloadPath}. The path will be accessible as a step output using downloaded-pip-path."
        )

        createGHAOutputVariable("downloaded-pip-path", downloadPath)
        createGHAOutputVariable("new-pip-version", str(latestPipVersion))


if __name__ == "__main__":
    sys.exit(bool(asyncio.run(main())))
