"""Plugin system."""

from __future__ import annotations

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
        packages: typing.Tuple[str, ...],  # Immutable
        requirements: typing.Tuple[str, ...],  # Immutable
    ) -> None:
        """
        The pre-pip resolve hook allows a plugin to run some checks *before* resolving the
        requested packages using pip. The hook **must** not modify the content of the
        arguments passed to it.

        Some use cases are allowing or disallowing the installation of some packages.

        :param packages: List of packages requested by the user.
        :param requirements: List of `requirements files <https://pip.pypa.io/en/stable/reference/requirements-file-format/#requirements-file-format>`_ if any.
        """

    @hookspec
    def postPipResolve(
        self,
        packages: typing.Tuple[rez_pip.pip.PackageInfo, ...],  # Immutable
    ) -> None:
        """
        The post-pip resolve hook allows a plugin to run some checks *after* resolving the
        requested packages using pip. The hook **must** not modify the content of the
        arguments passed to it.

        Some use cases are allowing or disallowing the installation of some packages.

        :param packages: List of resolved packages.
        """

    @hookspec
    def groupPackages(  # type: ignore[empty-body]
        self,
        packages: rez_pip.compat.MutableSequence[rez_pip.pip.PackageInfo],
    ) -> rez_pip.compat.Sequence[
        rez_pip.pip.PackageGroup[rez_pip.pip.DownloadedArtifact]
    ]:
        """
        Merge packages into groups of packages. The name and version of the first package
        in the group will be used as the name and version for the rez package.

        The hook **must** pop grouped packages out of the "packages" variable.

        :param packages: List of resolved packages.
        :returns: A list of package groups.
        """

    @hookspec
    def patches(
        self, dist: rez_pip.compat.importlib_metadata.Distribution, path: str
    ) -> typing.Sequence[str]:
        """
        Provide paths to patches to be applied on the source code of a package.

        :param dist: Python distribution.
        :param path: Root path of the installed content.
        """
        # TODO: This will alter files (obviously) and change their hashes.
        # This could be a problem to verify the integrity of the package.
        # https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file

    @hookspec
    def cleanup(
        self, dist: rez_pip.compat.importlib_metadata.Distribution, path: str
    ) -> None:
        """
        Cleanup a package post-installation.

        :param dist: Python distribution.
        :param path: Root path of the rez variant.
        """

    @hookspec
    def metadata(self, package: rez.package_maker.PackageMaker) -> None:
        """
        Modify/inject metadata in the rez package. The plugin is expected to modify
        "package" in place.

        :param package: An insatnce of :class:`rez.package_maker.PackageMaker`.
        """


def before(
    hookName: str,
    hookImpls: rez_pip.compat.Sequence[pluggy.HookImpl],
    kwargs: rez_pip.compat.Mapping[str, typing.Any],
) -> None:
    """Function that will be called before each hook."""
    _LOG.debug("Calling the %r hooks", hookName)


def after(
    outcome: pluggy.Result[typing.Any],
    hookName: str,
    hookImpls: rez_pip.compat.Sequence[pluggy.HookImpl],
    kwargs: rez_pip.compat.Mapping[str, typing.Any],
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
