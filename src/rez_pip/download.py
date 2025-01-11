from __future__ import annotations

import os
import typing
import asyncio
import hashlib
import logging

import aiohttp
import rich.progress

import rez_pip.pip
import rez_pip.utils
from rez_pip.compat import importlib_metadata

_LOG = logging.getLogger(__name__)
_lock = asyncio.Lock()


def downloadPackages(
    packageGroups: typing.List[rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo]],
    dest: str,
) -> typing.List[rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact]]:
    return asyncio.run(_downloadPackages(packageGroups, dest))


async def _downloadPackages(
    packageGroups: typing.List[rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo]],
    dest: str,
) -> list[rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact]]:
    newPackageGroups: typing.List[
        rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact]
    ] = []
    someFailed = False

    async with aiohttp.ClientSession() as session:
        with rich.progress.Progress(
            "[progress.description]{task.description}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            rich.progress.BarColumn(),
            rich.progress.DownloadColumn(),
            rich.progress.TransferSpeedColumn(),
            transient=True,
            console=rez_pip.utils.CONSOLE,
        ) as progress:
            tasks: typing.Dict[str, rich.progress.TaskID] = {}

            # Create all the download tasks first
            numPackages = 0
            for group in packageGroups:
                for package in group.packages:
                    if not package.isDownloadRequired():
                        continue

                    numPackages += 1
                    tasks[package.name] = progress.add_task(package.name)

            # Then create the "total" progress bar. This ensures that total is at the bottom.
            mainTask = progress.add_task(f"[bold]Total (0/{numPackages})", total=0)

            futureGroups: list[
                list[
                    typing.Coroutine[
                        typing.Any,
                        typing.Any,
                        rez_pip.pip.DownloadedArtifact | None,
                    ]
                ]
            ] = []

            # loop = asyncio.get_event_loop()
            for group in packageGroups:
                futures: list[
                    typing.Coroutine[
                        typing.Any,
                        typing.Any,
                        rez_pip.pip.DownloadedArtifact | None,
                    ]
                ] = []
                for package in group.packages:
                    wheelName: str = os.path.basename(package.download_info.url)
                    wheelPath = os.path.join(dest, wheelName)

                    if not package.isDownloadRequired():

                        # Note the subtlety of having to pass variables in the function
                        # signature. We can't rely on the scoped variable.
                        async def _return_local(
                            _wheelPath: str, _package: rez_pip.pip.PackageInfo
                        ) -> rez_pip.pip.DownloadedArtifact:
                            return rez_pip.pip.DownloadedArtifact.from_dict(
                                {"_localPath": _wheelPath, **_package.to_dict()}
                            )

                        futures.append(_return_local(wheelPath, package))
                    else:
                        futures.append(
                            _download(
                                package,
                                session,
                                progress,
                                tasks[package.name],
                                mainTask,
                                wheelName,
                                wheelPath,
                            )
                        )
                futureGroups.append(futures)

            for _futures in futureGroups:
                artifacts = tuple(await asyncio.gather(*_futures))

                if not all(artifacts):
                    someFailed = True

                artifacts = typing.cast(
                    typing.Tuple[rez_pip.pip.DownloadedArtifact], artifacts
                )

                newPackageGroups.append(
                    rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact](artifacts)
                )

    if someFailed:
        raise RuntimeError("Some wheels failed to be downloaded")

    return newPackageGroups


def getSHA256(path: str) -> str:
    buf = bytearray(2**18)  # Reusable buffer to reduce allocations.
    view = memoryview(buf)

    digestobj = hashlib.new("sha256")

    with open(path, "rb") as fd:
        while True:
            size = fd.readinto(buf)
            if size == 0:
                break  # EOF
            digestobj.update(view[:size])

    return digestobj.hexdigest()


async def _download(
    package: rez_pip.pip.PackageInfo,
    session: aiohttp.ClientSession,
    progress: rich.progress.Progress,
    taskID: rich.progress.TaskID,
    mainTaskID: rich.progress.TaskID,
    wheelName: str,
    wheelPath: str,
) -> rez_pip.pip.DownloadedArtifact | None:
    # TODO: Handle case where sha256 doesn't exist. We should also support the other supported
    # hash types.
    if (
        os.path.exists(wheelPath)
        and getSHA256(wheelPath) == package.download_info.archive_info.hashes["sha256"]
    ):
        _LOG.info(f"{wheelName} found in cache at {wheelPath!r}. Skipping download.")
    else:
        _LOG.debug(
            f"Downloading {package.name}-{package.version} from {package.download_info.url}"
        )

        async with session.get(
            package.download_info.url,
            headers={
                "Content-Type": "application/octet-stream",
                "User-Agent": f"rez-pip/{importlib_metadata.version('rez-pip')}",
            },
        ) as response:
            size = int(response.headers.get("content-length", 0))
            progress.update(taskID, total=size)

            async with _lock:
                mainTask = [task for task in progress.tasks if task.id == mainTaskID][0]

                progress.update(
                    mainTaskID,
                    total=typing.cast(int, mainTask.total) + size,
                )

            if response.status != 200:
                _LOG.error(
                    f"failed to download {package.download_info.url}: {response.status} - {response.reason}, {response.request_info}"
                )
                return None

            with open(wheelPath, "wb") as fd:
                async for chunk, asd in response.content.iter_chunks():
                    if not chunk:
                        break
                    progress.update(taskID, advance=len(chunk))
                    progress.update(mainTaskID, advance=len(chunk))
                    fd.write(chunk)

            _LOG.info(
                f"Downloaded {package.name}-{package.version} to {wheelPath!r} ({os.stat(wheelPath).st_size} bytes)"
            )

    progress.update(taskID, visible=False)

    total = len(progress.tasks) - 1
    async with _lock:
        completedItems = [task for task in progress.tasks if not task.visible]
        progress.update(
            mainTaskID, description=f"[bold]Total ({len(completedItems)}/{total})"
        )

    return rez_pip.pip.DownloadedArtifact.from_dict(
        {"_localPath": wheelPath, **package.to_dict()}
    )
