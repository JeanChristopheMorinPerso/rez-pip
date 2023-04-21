import os
import typing
import aiohttp
import asyncio
import logging

import rez_pip.pip

_LOG = logging.getLogger(__name__)


def downloadPackages(packages: list[rez_pip.pip.PackageInfo], dest: str) -> list[str]:
    return asyncio.run(_downloadPackages(packages, dest))


async def _downloadPackages(
    packages: list[rez_pip.pip.PackageInfo], dest: str
) -> list[str]:
    items: list[typing.Coroutine] = []

    wheels = []
    async with aiohttp.ClientSession() as session:
        for package in packages:
            items.append(download(package, dest, session))

        wheels = await asyncio.gather(*items)

    if not all(wheels):
        raise RuntimeError("Some wheels failed to be downloaded")

    return wheels


async def download(
    package: rez_pip.pip.PackageInfo, target: str, session: aiohttp.ClientSession
) -> str | None:
    _LOG.debug(
        f"Downloading {package.name}-{package.version} from {package.download_info['url']}"
    )
    async with session.get(
        package.download_info["url"],
        headers={
            "Content-Type": "application/octet-stream",
            "User-Agent": "rez-pip/0.1.0",
        },
    ) as response:
        content = await response.read()

    if response.status != 200:
        _LOG.error(f"failed to download {package.download_info['url']}")
        return None

    wheelName: str = os.path.basename(package.download_info["url"])
    wheelPath = os.path.join(target, wheelName)
    with open(wheelPath, "wb") as fd:
        fd.write(content)

    _LOG.info(f"Downloaded {package.name}-{package.version} to {wheelPath!r}")
    return wheelPath
