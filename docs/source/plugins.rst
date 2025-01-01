=======
Plugins
=======

rez-pip can be extended using plugins. Plugins can be used to do various things, such as
modifying packages (both metadata and files), etc.

This page documents the hooks available to plugins and how to implement plugins.

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

.. autohook:: rez_pip.plugins.PluginSpec.prePipResolve
.. autohook:: rez_pip.plugins.PluginSpec.postPipResolve
.. autohook:: rez_pip.plugins.PluginSpec.groupPackages
.. autohook:: rez_pip.plugins.PluginSpec.cleanup
.. autohook:: rez_pip.plugins.PluginSpec.metadata

Built-in plugins
================

rez-pip comes with some built-in plugins that are enabled by default. They exists mostly
to fix packages that are known to be "broken" if we don't fix them using plugins.

This lists the plugin names and the hooks they implement.

.. rez-pip-autoplugins::

Example
=======

.. todo:: Add an example plugin
