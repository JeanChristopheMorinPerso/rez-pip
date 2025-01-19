==========
User guide
==========

Installing packages
===================

To install a single package, you can run ``rez-pip example``. Similarly to pip,
multiple packages can be passed, like ``rez-pip example1 example2``.

On top of that, you can also use the ``-r``/``--requirement`` command line argument
to install packages from a requirements file. The behavior is exaclty the same as with pip,
so you can use it multiple times to install from multiple requriement files.

The ``-c``/``--constraint`` argument is also available and can also be used multiple times.

.. note::
   By default, rez-pip will install packages in your configured :external:data:`local_packages_path`.
   To install in your :external:data:`release_packages_path`,
   use the ``--release`` command line argument.

Selecting the python version
============================

``rez-pip`` will look for python packages that are available based on your
rez configuration. By default, it will use all available versions.

By using ``--python-version``, you can select which version of python
to use for the requested packages. You can use the same version specifier syntax
that rez supports (``>=3``, ``3.7|3.9``, etc) or you can also use ``latest``.

.. note::
    Your rez package that contains python needs to be named ``python``.
    It will not work if your package is named differently.

Installing packages into a custom location
==========================================

In some situations, you might need to install packages in a custom location. In such cases, you can
use the ``-p``/``--prefix`` command line argument.

Passing arguments to pip directly
=================================

Passing command line arguments to pip can be achieved by using ``--``. All arguments specified
after ``--`` will be forwarded to pip. For example, ``rez-pip example -- --index-url https://example.com/simple``
will result in a pip command that looks like ``pip install example --index-url https://example.com/simple``.

Changing log level
==================

The log level can be adjusted by using the ``-l``/``--log-level`` command line argument.
Use ``--help`` to see the accepted values.

Configuring pip
===============

Since pip is used under the hood, pip can be configured as usual. See the `pip configuration documentation`_
for more information on the subject. Alternatively, you can also :ref:`pass custom command line arguments to pip <user_guide:passing arguments to pip directly>`.

.. _pip configuration documentation: https://pip.pypa.io/en/stable/topics/configuration/

Writing a plugin
================

As documented in :ref:`plugins:register a plugin`, plugins must be registered using entry points.
This also means that your plugin will have to be packaged using standard Python packaging tools.

.. note:: Even if you package it using standard Python packaging tools, you won't need
          to distribute it to PyPI.

Our plugin will have the following file structure:

.. code-block:: text

   my_plugin/
   ├── pyproject.toml
   └── src/
       └── my_plugin/
           └── __init__.py

In ``pyproject.toml``, we will define our package and plugin entry point:

.. code-block:: toml
   :caption: pyproject.toml

   [project]
   name = "my_plugin"
   version = "0.1.0"

   [project.entry-points."rez-pip"]
   my_plugin = "my_plugin"

   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

This is the absolute minimum required to create a plugin. For more details
on how to package a python project, please refer to `the official documentation`_.

.. _the official documentation: https://packaging.python.org/en/latest/tutorials/packaging-projects/

Now that this is out of the way, let's write our plugin.

.. code-block:: python
   :caption: src/my_plugin/__init__.py

   import logging

   import rez_pip.plugins
   import rez.package_maker

   _LOG = logging.getLogger(__name__)


   @rez_pip.plugins.hookimpl
   def metadata(package: rez.package_maker.PackageMaker) -> None
       _LOG.info(
           "Adding my_custom_attr to the package definition of %s %s",
           package.name,
           package.version,
       )
       package.my_custom_attr = "my_custom_value"

.. tip::
   :name: Logs

   It is highly recommended to add logs to your plugins. You can use :func:`logging.getLogger`
   to get a pre-configured logger. Make sure to pass a unique name to the logger.

   Your logs should clearly describe what your plugin is doing. If your plugin modifies
   something, then it should log that. If it is just reading something, then you might
   not need to log.

The plugin we defined in ``src/my_plugin/__init__.py`` registers a hook called ``metadata`` that
modifies the package definition. More particularly, it adds an attribute called ``my_custom_attr``
to the package definition. Here we use a dummy attribute name just to illustrate the concept.
But this is a common scenario.

For brevity, we only implement one hook. ``rez-pip`` provides many other hooks that you can implement.
Hooks are documented in :ref:`plugins:hooks`.

Once this is done, you can test your plugin by installing it. For example, you can use ``pip install -e .``
to install it in `editable mode <https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs>`_.
