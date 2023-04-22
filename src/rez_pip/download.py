import os
import typing
import asyncio
import logging

import aiohttp
import rich.console
import rich.progress

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
        with rich.progress.Progress(
            "[progress.description]{task.description}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            rich.progress.BarColumn(),
            rich.progress.DownloadColumn(),
            rich.progress.TransferSpeedColumn(),
            transient=True,
        ) as progress:
            for package in packages:
                items.append(download(package, dest, session, progress))

            wheels = await asyncio.gather(*items)

    if not all(wheels):
        raise RuntimeError("Some wheels failed to be downloaded")

    return wheels


async def download(
    package: rez_pip.pip.PackageInfo,
    target: str,
    session: aiohttp.ClientSession,
    progress: rich.progress.Progress,
) -> str | None:

    _LOG.debug(
        f"Downloading {package.name}-{package.version} from {package.download_info.url}"
    )

    async with session.get(
        package.download_info.url,
        headers={
            "Content-Type": "application/octet-stream",
            "User-Agent": "rez-pip/0.1.0",
        },
    ) as response:

        task = progress.add_task(
            package.name, total=int(response.headers.get("content-length", 0))
        )

        if response.status != 200:
            _LOG.error(f"failed to download {package.download_info.url}")
            return None

        wheelName: str = os.path.basename(package.download_info.url)
        wheelPath = os.path.join(target, wheelName)
        with open(wheelPath, "wb") as fd:
            async for chunk, asd in response.content.iter_chunks():
                if not chunk:
                    break
                progress.update(task, advance=len(chunk))
                fd.write(chunk)

    progress.update(task, visible=False)

    _LOG.info(
        f"Downloaded {package.name}-{package.version} to {wheelPath!r} ({os.stat(wheelPath).st_size} bytes)"
    )

    return wheelPath
