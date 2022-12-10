import os
import typing
import aiohttp
import asyncio

import rez_pip.pip


def downloadPackages(packages: list[rez_pip.pip.PackageInfo], dest: str) -> str:
    return asyncio.run(_downloadPackages(packages, dest))


async def _downloadPackages(packages: list[rez_pip.pip.PackageInfo], dest: str) -> str:
    items: list[typing.Coroutine] = []

    wheels = []
    async with aiohttp.ClientSession() as session:
        for package in packages:
            items.append(download(package, dest, session))

        wheels = await asyncio.gather(*items)
    return wheels


async def download(
    package: rez_pip.pip.PackageInfo, target: str, session: aiohttp.ClientSession
) -> str:
    print(
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
        print(f"failed to download {package.download_info['url']}")
        return

    wheelName: str = os.path.basename(package.download_info["url"])
    wheelPath = os.path.join(target, wheelName)
    with open(wheelPath, "wb") as fd:
        fd.write(content)

    print(f"Downloaded {package.name}-{package.version} to {wheelPath!r}")
    return wheelPath
