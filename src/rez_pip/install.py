import os
import sys
import typing
import logging
import sysconfig
import importlib.metadata

import installer
import installer.utils
import installer.sources
import installer.destinations

import rez_pip.pip

_LOG = logging.getLogger(__name__)


def isWheelPure(source: installer.sources.WheelSource) -> bool:
    stream = source.read_dist_info("WHEEL")
    metadata = installer.utils.parse_metadata_file(stream)
    return metadata["Root-Is-Purelib"] == "true"


# Taken from https://github.com/pypa/installer/blob/main/src/installer/__main__.py#L49
def getSchemeDict(name: str, target: str) -> dict[str, str]:
    vars = {}
    vars["base"] = vars["platbase"] = installed_base = target

    schemeDict = sysconfig.get_paths(vars=vars)
    # calculate 'headers' path, not currently in sysconfig - see
    # https://bugs.python.org/issue44445. This is based on what distutils does.
    # TODO: figure out original vs normalised distribution names
    schemeDict["headers"] = os.path.join(
        sysconfig.get_path("include", vars={"installed_base": installed_base}),
        name,
    )

    if target:  # In practice this will always be set.
        schemeDict["purelib"] = os.path.join(target, "python")
        schemeDict["platlib"] = os.path.join(target, "python")
        schemeDict["headers"] = os.path.join(target, "headers", name)
        schemeDict["scripts"] = os.path.join(target, "scripts")
        # Potentiall handle data?
    return schemeDict


def installWheel(
    package: rez_pip.pip.PackageInfo,
    wheelPath: typing.Union[str, os.PathLike[str]],
    target: str,
) -> tuple[importlib.metadata.Distribution, bool]:
    """
    Technically, target should be optional. We will always want to install in "pip install --target"
    mode. So right now it's a CLI option for debugging purposes.
    """

    destination = installer.destinations.SchemeDictionaryDestination(
        getSchemeDict(package.name, target),
        interpreter=sys.executable,  # Can be used for shebang I think.
        script_kind=installer.utils.get_launcher_kind(),
    )

    isPure = True
    _LOG.debug(f"Installing {wheelPath} into {target!r}")
    with installer.sources.WheelFile.open(wheelPath) as source:
        isPure = isWheelPure(source)

        installer.install(
            source=source,
            destination=destination,
            # Additional metadata that is generated by the installation tool.
            additional_metadata={
                "INSTALLER": b"rez-pip 0.1.0",  # TODO: Should this be installer instead?
            },
        )

    # Use pathlib.Path so that it doesn't actually affect imports.
    # See https://docs.python.org/3/library/importlib.metadata.html#distribution-discovery
    # TODO: Don't hardcode path here.
    sys.path.insert(0, "/tmp/asd/python")

    dist = importlib.metadata.distribution(package.name)

    return dist, isPure
