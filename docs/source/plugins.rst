=======
Plugins
=======

.. versionadded:: 0.4.0

.. warning::
   Plugins are new and have not been tested througfully. There might be bugs, missing
   features and rough edges.

   We encourage you to try them out and report any issues you might find.

rez-pip can be extended using plugins. Plugins can be used to do various things, such as
modifying packages (both metadata and files), etc.

This page documents the hooks available to plugins and how to implement plugins.

List installed plugins
======================

To list all installed plugins, use the :option:`rez-pip --list-plugins` command line argument.

Register a plugin
=================

rez-pip's plugin system is based on the `pluggy <https://pluggy.readthedocs.io/en/latest/>`_ framework,
and as such, plugins must be registered using `entry points <https://packaging.python.org/en/latest/specifications/entry-points/>`_.

The entry point group is named `rez-pip`.

In a `pyproject.toml` file, it can be set like this:

.. code-block:: toml
   :caption: pyproject.toml

   [project.entry-points."rez-pip"]
   my_plugin = "my_plugin_module"


Functions
=========

.. Not Using autodoc here because the decorator has a complex
   signature to help type hinters. That signature is not needed
   for the end user.
.. py:decorator:: rez_pip.plugins.hookimpl

   Decorator used to register a plugin hook.

Hooks
=====

.. rez-pip-autopluginhooks:: rez_pip.plugins.PluginSpec


Built-in plugins
================

rez-pip comes with some built-in plugins that are enabled by default. They exists mostly
to fix packages that are known to be "broken" if we don't fix them using plugins.

This lists the plugin names and the hooks they implement.

.. rez-pip-autoplugins::
