===
FAQ
===

List of commonly asked questions.

Why does the rez package created by rez-pip creates a variant per platform?
===========================================================================

Sometimes rez-pip creates rez packages that have variants for the platform and arch on which they were installed,
and sometimes it even creates variants for Python versions. Bellow are the scenarios
where this can happen with an explanation and example for each.

Command-line tools
------------------

When a package provides command-line tools, rez-pip creates a rez package that looks like this:

.. code:: python

    name = 'package'
    version = '1.0.0'

    requires = ['python']

    variants = [
        ['platform-linux', 'arch-x86_64']
    ]

This can happen because the package has `entry points`_ that use the ``console_script`` group. In other words,
the package provides command-line tools. For example, installing `pytest <https://docs.pytest.org/en/latest/>`_ results
in such a variant.

In such cases, a platform specific variant gets created because of the way these console scripts are implemented.
On Unix like systems (Linux, macOS, etc), console scripts are pure python files while on Windows
they are executables.

Because of that difference, per platform variants are used when the package provides console scripts. One could argue
that it only applies to Windows and that Linux and macOS should not required variants, but that wouldn't work and it
would also be inconsistent.

.. _entry points: https://packaging.python.org/en/latest/specifications/entry-points/

Python extensions (compiled)
----------------------------

When a package contains compiled code (or more commonly called an extension), the generated rez package looks like this:

.. code:: python

    name = 'package'
    version = '1.0.0'

    variants = [
        ['platform-linux', 'arch-x86_64', 'python-3.10']
    ]

In this case, the ``rez-pip`` command was run with `--python-version 3.10` and it installed the package ``package``
it created a rez package with a ``python-3.10`` variant.

This is because the package contains compiled code and so is only compatible with this version of python.
