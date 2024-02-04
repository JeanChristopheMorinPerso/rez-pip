=======
Plugins
=======


.. py:decorator:: rez_pip.plugins.hookimpl

   Decorator used to register a plugin hook.

Hooks
=====

.. py:function:: prePipResolve(packages: list[str], requirements: list[str]) -> None

   The pre-pip resolve hook allows a plugin to run some checks *before* resolving the
   requested packages using pip. The hook **must** not modify the content of the
   arguments passed to it.

   Some use cases are allowing or disallowing the installation of some packages.

   :param packages: List of packages requested by the user.
   :param requirements: List of `requirements files <https://pip.pypa.io/en/stable/reference/requirements-file-format/#requirements-file-format>`_ if any.

.. py:function:: postPipResolve(packages: list[rez_pip.pip.PackageInfo]) -> None

   The post-pip resolve hook allows a plugin to run some checks *after* resolving the
   requested packages using pip. The hook **must** not modify the content of the
   arguments passed to it.

   Some use cases are allowing or disallowing the installation of some packages.

   :param packages: List of resolved packages.

.. py:function:: groupPackages(packages: list[rez_pip.pip.PackageInfo]) -> list[rez_pip.pip.PackageGroup]:

   Merge packages into groups of packages. The name and version of the first package
   in the group will be used as the name and version for the rez package.

   The hook **must** pop grouped packages out of the "packages" variable.

   :param packages: List of resolved packages.
   :returns: A list of package groups.

.. py:function:: metadata(package: rez.package_maker.PackageMaker) -> None

   Modify/inject metadata in the rez package. The plugin is expected to modify
   "package" in place.

   :param package: An instanciate PackageMaker.

.. py:function:: cleanup(dist: importlib.metadata.Distribution, path: str) -> None

   Cleanup a package post-installation.

   :param dist: Python distribution.
   :param path: Root path of the rez variant.
