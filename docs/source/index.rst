.. rez-pip documentation master file, created by
   sphinx-quickstart on Sat May 13 17:23:33 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=======
rez-pip
=======

rez-pip is a rez_ command-line plugin that you can use to make package from
the `Python Package Index`_ and other indexes available to your rez package ecosystem.

.. _rez: https://github.com/AcademySoftwareFoundation/rez
.. _Python Package Index: https://pypi.org

Features
========

* Simpler to use thanks to the vendoring of pip.
* Does **not** support installing packages for Python 2.
* Only creates per python version variants when absolutely necessary. For example, it won't
  create per python version variants when installing a package that has console scripts.
* Better output logs.
* Implemented as an out-of-tree plugin, which means faster development cycle and more frequent releases.
* Maintained by the rez maintainers.

Prerequisites
=============

* A rez package named ``python`` that contains a CPython installation. PyPy and other interpreters are not yet supported.
* A working Python 3 based rez install.

Installation
============

``rez-pip`` can be installed by using pip. We highly recommend that you install
it into your rez's virtual environment (the virtualenv that is
automatically created by the `install.py <https://github.com/AcademySoftwareFoundation/rez/blob/master/install.py>`_ script).

.. tab:: Linux/macOS

   .. code:: bash

      $ source <rez>/bin/activate
      $ python -m pip install rez-pip

.. tab:: Windows

   .. code:: doscon

      C:> source <rez>\Scripts\activate
      C:> python -m pip install rez-pip

.. note::
   Pip is bundled with ``rez-pip``, so no need to install pip as a rez package of have pip available inside your python rez packages.
   See the :ref:`transition documentation <transition:pip is now bundled/vendored>` section for more information.

.. note::
   If you don't want or can't have a full rez install, you can also
   install rez-pip into its own virtualenv. Note that this should be a last
   resort option.


.. toctree::
   :maxdepth: 0
   :hidden:

   user_guide
   transition
   metadata
   faq.rst
