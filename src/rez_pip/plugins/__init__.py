"""Plugin system."""
import sys
import typing
import logging
import functools

import pluggy

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import rez.package_maker

if typing.TYPE_CHECKING:
    import rez_pip.pip

__all__ = [
    "hookimpl",
]


def __dir__() -> typing.List[str]:
    return __all__


__LOG = logging.getLogger(__name__)

F = typing.TypeVar("F", bound=typing.Callable[..., typing.Any])
hookspec = typing.cast(typing.Callable[[F], F], pluggy.HookspecMarker("rez-pip"))
hookimpl = typing.cast(typing.Callable[[F], F], pluggy.HookimplMarker("rez-pip"))


class PluginSpec:
    @hookspec
    def prePipResolve(
        self, packages: typing.List[str], requirements: typing.List[str]
    ) -> None:
        """
        Take an action before resolving the packages using pip.
        The packages argument should not be modified in any way.
        """

    @hookspec
    def postPipResolve(self, packages: typing.List["rez_pip.pip.PackageInfo"]) -> None:
        """
        Take an action after resolving the packages using pip.
        The packages argument should not be modified in any way.
        """

    @hookspec
    def groupPackages(  # type: ignore[empty-body]
        self, packages: typing.List["rez_pip.pip.PackageInfo"]
    ) -> typing.List["rez_pip.pip.PackageGroup"]:
        """
        Merge packages into groups of packages. The name and version of the first package
        in the group will be used as the name and version for the rez package.

        The hook must pop grouped packages out of the "packages" variable.
        """

    @hookspec
    def cleanup(self, dist: importlib_metadata.Distribution, path: str) -> None:
        """Cleanup installed distribution"""

    @hookspec
    def metadata(self, package: rez.package_maker.PackageMaker) -> None:
        """
        Modify/inject metadata in the rez package. The plugin is expected to modify
        "package" in place.
        """


@functools.lru_cache()
def getManager() -> pluggy.PluginManager:
    """
    Returns the plugin manager. The return value will be cached on first call
    and the cached value will be return in subsequent calls.
    """
    import rez_pip.plugins.PySide6
    import rez_pip.plugins.shiboken6

    manager = pluggy.PluginManager("rez-pip")
    # manager.trace.root.setwriter(print)
    # manager.enable_tracing()

    manager.add_hookspecs(PluginSpec)

    manager.register(rez_pip.plugins.PySide6)
    manager.register(rez_pip.plugins.shiboken6)

    manager.load_setuptools_entrypoints("rez-pip")

    # print(list(itertools.chain(*manager.hook.prePipResolve(packages=["asd"]))))
    return manager


def getHook() -> PluginSpec:
    """
    Returns the hook attribute from the manager. This is allows
    to have type hints at the caller sites.

    Inspired by https://stackoverflow.com/a/54695761.
    """
    manager = getManager()
    return typing.cast(PluginSpec, manager.hook)


def _getHookImplementations() -> typing.Dict[str, typing.List[str]]:
    manager = getManager()

    implementations = {}
    for name, plugin in manager.list_name_plugin():
        implementations[name] = [
            caller.name for caller in manager.get_hookcallers(plugin)
        ]
    return implementations
