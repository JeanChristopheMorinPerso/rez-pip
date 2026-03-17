# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import typing
import asyncio
import hashlib
import logging
import collections

import aiohttp
import rich.progress

from rez_pip import exceptions
import rez_pip.pip
import rez_pip.utils
from rez_pip.compat import importlib_metadata

_LOG = logging.getLogger(__name__)
_lock = asyncio.Lock()


def downloadPackages(
    packageGroups: list[rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo]],
    dest: str,
    runner: rez_pip.pip.PipRunner,
) -> list[rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact]]:
    return asyncio.run(_downloadPackages(packageGroups, dest, runner))


async def _downloadPackages(
    packageGroups: list[rez_pip.pip.PackageGroup[rez_pip.pip.PackageInfo]],
    dest: str,
    runner: rez_pip.pip.PipRunner,
) -> list[rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact]]:
    newPackageGroups: list[
        rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact]
    ] = []

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
            tasks: dict[str, rich.progress.TaskID] = {}

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

            futures: list[
                typing.Coroutine[
                    typing.Any,
                    typing.Any,
                    rez_pip.pip.DownloadedArtifact | None,
                ]
            ] = []

            groupMapping: collections.defaultdict[int, list[str]] = (
                collections.defaultdict(list)
            )

            for index, group in enumerate(packageGroups):
                for package in group.packages:
                    wheelName: str = os.path.basename(package.download_info.url)
                    wheelPath = os.path.join(dest, wheelName)

                    groupMapping[index].append(package.name)

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
                                runner,
                            )
                        )

            artifacts = tuple(await asyncio.gather(*futures))

            if not all(artifacts):
                raise RuntimeError("Some wheels failed to be downloaded")

            artifacts = typing.cast(
                typing.Tuple[rez_pip.pip.DownloadedArtifact], artifacts
            )

            # Return artifacts in the same groups as they arrived in.
            # TODO: The amount of looping and gymnastic is a big code smell.
            for packageNames in groupMapping.values():
                newPackageGroups.append(
                    rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact](
                        tuple(
                            artifact
                            for artifact in artifacts
                            if artifact.name in packageNames
                        )
                    )
                )

    return newPackageGroups


# TODO: Should we support weak hashes md5, sha1, sha224?  Do any repositories still use them?
HASHES = {"md5", "sha1", "sha224", "sha256", "sha384", "sha512"}


def checkHashes(path: str, hashes: dict[str, str]) -> bool:
    # Accept file without hashes.  The Simple Repository API says each URL SHOULD include a hash and not a MUST
    if not hashes:
        return True

    buf = bytearray(2**18)  # Reusable buffer to reduce allocations.
    view = memoryview(buf)

    # Support multiple hash functions on a URL
    digests = {algo: hashlib.new(algo) for algo in HASHES if algo in hashes}

    # Reject files if all the hashes are unknown
    if not digests:
        return False

    with open(path, "rb") as fd:
        while True:
            size = fd.readinto(buf)
            if size == 0:
                break  # EOF
            for digest in digests.values():
                digest.update(view[:size])

    return all(digests[algo].hexdigest() == hashes[algo] for algo in digests)


async def _download(
    package: rez_pip.pip.PackageInfo,
    session: aiohttp.ClientSession,
    progress: rich.progress.Progress,
    taskID: rich.progress.TaskID,
    mainTaskID: rich.progress.TaskID,
    wheelName: str,
    wheelPath: str,
    runner: rez_pip.pip.PipRunner,
) -> rez_pip.pip.DownloadedArtifact | None:
    # TODO: Handle case where hash doesn't exist.

    mainTask = [task for task in progress.tasks if task.id == mainTaskID][0]

    if os.path.exists(wheelPath) and checkHashes(
        wheelPath, package.download_info.archive_info.hashes
    ):
        _LOG.info(f"{wheelName} found in cache at {wheelPath!r}. Skipping download.")
    else:
        _LOG.debug(
            f"Downloading {package.name}-{package.version} from {package.download_info.url}"
        )

        tryPipFallback = False

        async with session.get(
            package.download_info.url,
            headers={
                "Content-Type": "application/octet-stream",
                "User-Agent": f"rez-pip/{importlib_metadata.version('rez-pip')}",
            },
        ) as response:
            if response.status == 401:
                _LOG.debug(
                    f"unauthorized to download {package.download_info.url}. Trying to download with pip."
                )
                tryPipFallback = True
            elif response.status != 200:
                _LOG.error(
                    f"failed to download {package.download_info.url}: {response.status} - {response.reason}, {response.request_info}"
                )

                return None
            else:
                size = int(response.headers.get("content-length", 0))
                progress.update(taskID, total=size)

                async with _lock:
                    progress.update(
                        mainTaskID,
                        total=typing.cast(int, mainTask.total) + size,
                    )

                with open(wheelPath, "wb") as fd:
                    async for chunk, asd in response.content.iter_chunks():
                        if not chunk:
                            break
                        _ = fd.write(chunk)
                        progress.update(taskID, advance=len(chunk))
                        progress.update(mainTaskID, advance=len(chunk))

        if tryPipFallback:
            try:
                await runner.runAsync(
                    "download",
                    [
                        "--no-deps",
                        "--dest",
                        os.path.dirname(wheelPath),
                        f"{package.name}=={package.version}",
                    ],
                )
            except exceptions.PipError as e:
                _LOG.error(f"failed to download {package.name}-{package.version}: {e}")
                return None
            if not os.path.exists(wheelPath):
                _LOG.error(
                    f"failed downloading {package.name}-{package.version} to {wheelPath}"
                )
                return None

            size = os.stat(wheelPath).st_size
            progress.update(taskID, total=size)
            progress.update(taskID, advance=size)
            async with _lock:
                progress.update(
                    mainTaskID, total=typing.cast(int, mainTask.total) + size
                )
            progress.update(mainTaskID, advance=size)

        if not checkHashes(wheelPath, package.download_info.archive_info.hashes):
            _LOG.error(
                f"failed to download {package.download_info.url}: invalid file hash"
            )
            return None

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
