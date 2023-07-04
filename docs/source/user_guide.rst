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
   By default, rez-pip will install packages in your configured `local_packages_path`_.
   To install in your `release_packages_path`_,
   use the ``--release`` command line argument.

.. _local_packages_path: https://github.com/AcademySoftwareFoundation/rez/wiki/Configuring-Rez#local_packages_path
.. _release_packages_path: https://github.com/AcademySoftwareFoundation/rez/wiki/Configuring-Rez#release_packages_path

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
