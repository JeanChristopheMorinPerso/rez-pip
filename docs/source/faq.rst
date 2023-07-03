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

In this case, the ``rez-pip`` command was run with ``--python-version 3.10`` and it installed the package ``package``
it created a rez package with a ``python-3.10`` variant.

This is because the package contains compiled code and so is only compatible with this version of python.

Why can't it install Python 2 packages?
=======================================

This is due to the way ``rez-pip`` is implemented. The current implementation looks like this:

1. Call ``python pip.pyz <package> -q --dry-run --report`` to get the list of wheels to install.
2. ``rez-pip`` downloads the wheels found in step one in parallel.
3. Downloaded wheels are installed into a temporary directory.
4. ``rez-pip`` creates rez packages for each package and copies the files from the temporary
   directories into the rez packages.

As you can see, ``rez-pip`` does not rely on ``pip`` to install the packages. We only use pip to resolve
which package we need to download and then "manually" install the wheels. This allows to fix the notorious
`shebang <https://en.wikipedia.org/wiki/Shebang_(Unix)>`_ problem with pip. Pip always bakes the full Python
interpreter path into the `console scripts`_ shebang. The problem is that baking the full path goes against
the idea of rez. In rez, we want the use the resolve python package to executable console scripts,
not the Python interpreter that was used to install the package.

.. _console scripts: https://packaging.python.org/en/latest/specifications/entry-points/#use-for-scripts

So why can't we install Python 2 packages?

The first reason is that the ``--report`` command line argument is too recent and doesn't exist on the
last version fo pip that support Python 2. Secondly, we can't run pip with a Python version X to resolve
packages to install for a Python of version Y because it simply doesn't support that. This is well
documented in https://github.com/pypa/pip/issues/11664.

For example, let's say we have two packages; ``a`` and ``b`` where ``a`` depends on ``b`` if the python
version is 2. In our example the package ``a`` is compatible with both Python 2 and 3.

If we run ``python3 -m pip install "a" --dry-run --report --python-version 2.7``, pip will
happily resolve the packages and will return ``a`` but **not** ``b``!

How can I know which wheel was used to create a package?
========================================================

See the :ref:`metadata documentation <metadata:metadata>` on how to find this information.
