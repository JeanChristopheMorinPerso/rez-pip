================
Transition guide
================

Transitioning to the new rez-pip should be pretty straight forward. There is differences
between the two tools, but there is nothing "major" in terms of installing packages
`from` PyPI.

This page documents the differences between the old and the new rez-pip.

Python 3.7+ only
================

The new rez-pip can only be installed in a Python 3 rez install. You will be able to
install packages for Python 3.7+, but not anything older than that.

Argument differences
====================

==================== =========================== =======
Old rez-pip          New rez-pip                 Notes
==================== =========================== =======
package (positional) package(**s**) (positional) Now accepts multiple packages. Also accepts paths to wheels but local directory isn't allowed.
``--python-version`` ``--python-version``        Similar but now accepts any valid version range (``2.7\|3.7+``) which allows to install for multiple Python versions.
``--pip-version``    ``--pip``                   Pip is now bundled with rez-pip, but ``--pip`` can be used to specify a different pip zipapp.
``-i``/``--install`` Removed
``-r``/``--release`` Identical
``-p``/``--prefix``  ``--prefix``                Defaults to `local_packages_path`_.
``-e``/``--extra``   ``--``                      ``--extra`` was replaced with trailing ``--``. For example ``rez-pip ... -- --index-url https://example.com``
==================== =========================== =======

.. _local_packages_path: https://github.com/AcademySoftwareFoundation/rez/wiki/Configuring-Rez#local_packages_path

Local and editable installs
===========================

The ability to install a local (from source) package via ``rez-pip -i .`` as been removed
and will not make it back. The same can be said about editable installs. ``rez-pip`` is a
tool to ingest Python packages and convert them into rez packages. It's not a development
tool and has never been designed with local development in mind.

I believe these functionalities would be better implemented and would better serve rez's
users if implemented as a `build_system`_ plugin. It would allow for better integration
with rez and the user experience would be significantly better than it could with ``rez-pip``.

.. _build_system: https://github.com/AcademySoftwareFoundation/rez/tree/master/src/rezplugins/build_system

I also believe that python packaging/rez hybrids are bad and just causes more issues than
they solve. The python packaging ecosystem and tools have different objectives and goals
than rez and the two don't necessarily always play well together. This is obviously a very
personal opinion, but still an opinion from someone with lots of experience with packaging
in general.

Pip is now bundled/vendored
===========================

The previous ``rez-pip`` had a complex logic to find both Python and pip. It was error prone,
confusing and also annoying to setup.

The new ``rez-pip`` bundles pip, which means it's ready to be used as is without any extra work/steps.
We bundle the `standalone zip application`_ which is extremely convenient because it's a single file.

Bundling has multiple advantages:

#. We control the version of pip used. This is important to ensure rez-pip works as expected.
#. No setup required after installation of rez-pip.

If somehow you want or need to change the version of pip used, you can user the ``--pip`` command-line
argument. You need to provide a path to a zipapp.

.. _standalone zip application: https://pip.pypa.io/en/stable/installation/#standalone-zip-application
