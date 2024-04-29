"""Plugin system."""

import typing
import logging
import pkgutil
import functools
import importlib

import pluggy
import rez.package_maker

if typing.TYPE_CHECKING:
    import rez_pip.pip
    import rez_pip.compat

__all__ = [
    "hookimpl",
]


def __dir__() -> typing.List[str]:
    return __all__


_LOG = logging.getLogger(__name__)

F = typing.TypeVar("F", bound=typing.Callable[..., typing.Any])
hookspec = typing.cast(typing.Callable[[F], F], pluggy.HookspecMarker("rez-pip"))
hookimpl = typing.cast(typing.Callable[[F], F], pluggy.HookimplMarker("rez-pip"))


class PluginSpec:
    @hookspec
    def prePipResolve(
        self,
        packages: "rez_pip.compat.Sequence[str]",  # Immutable
        requirements: "rez_pip.compat.Sequence[str]",  # Immutable
    ) -> None:
        """
        Take an action before resolving the packages using pip.
        The packages argument should not be modified in any way.
        """

    @hookspec
    def postPipResolve(
        self,
        packages: 'rez_pip.compat.Sequence["rez_pip.pip.PackageInfo"]',  # Immutable
    ) -> None:
        """
        Take an action after resolving the packages using pip.
        The packages argument should not be modified in any way.
        """

    @hookspec
    def groupPackages(  # type: ignore[empty-body]
        self, packages: 'rez_pip.compat.MutableSequence["rez_pip.pip.PackageInfo"]'
    ) -> 'rez_pip.compat.Sequence["rez_pip.pip.PackageGroup"]':
        """
        Merge packages into groups of packages. The name and version of the first package
        in the group will be used as the name and version for the rez package.

        The hook must pop grouped packages out of the "packages" variable.
        """

    @hookspec
    def cleanup(
        self, dist: "rez_pip.compat.importlib_metadata.Distribution", path: str
    ) -> None:
        """Cleanup installed distribution"""

    @hookspec
    def metadata(self, package: rez.package_maker.PackageMaker) -> None:
        """
        Modify/inject metadata in the rez package. The plugin is expected to modify
        "package" in place.
        """


def before(
    hookName: str,
    hookImpls: "rez_pip.compat.Sequence[pluggy.HookImpl]",
    kwargs: "rez_pip.compat.Mapping[str, typing.Any]",
) -> None:
    """Function that will be called before each hook."""
    _LOG.debug("Calling the %r hooks", hookName)


def after(
    outcome: pluggy.Result[typing.Any],
    hookName: str,
    hookImpls: "rez_pip.compat.Sequence[pluggy.HookImpl]",
    kwargs: "rez_pip.compat.Mapping[str, typing.Any]",
) -> None:
    """Function that will be called after each hook."""
    _LOG.debug("Called the %r hooks", hookName)


@functools.lru_cache()
def getManager() -> pluggy.PluginManager:
    """
    Returns the plugin manager. The return value will be cached on first call
    and the cached value will be return in subsequent calls.
    """
    manager = pluggy.PluginManager("rez-pip")
    if _LOG.getEffectiveLevel() <= logging.DEBUG:
        manager.trace.root.setwriter(print)
        manager.enable_tracing()

    manager.add_hookspecs(PluginSpec)

    # Register the builtin plugins
    for module in pkgutil.iter_modules(__path__):
        manager.register(
            importlib.import_module(f"rez_pip.plugins.{module.name}"),
            name=f"rez_pip.{module.name}",
        )

    manager.load_setuptools_entrypoints("rez-pip")

    manager.add_hookcall_monitoring(before, after)
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
        hookcallers = manager.get_hookcallers(plugin)

        # hookcallers will never be None because we get the names from list_name_plugin.
        # But it silences mypy.
        assert hookcallers is not None

        implementations[name] = [caller.name for caller in hookcallers]
    return implementations
