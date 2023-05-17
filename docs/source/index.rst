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

Installation
============

``rez-pip`` can be installed by using pip. We highly recommend that you install
it into your rez's virtua;env environment, that is the virtualenv env that is
automatically created by the ``install.py`` script.

.. tab:: Linux/macOS

   .. code:: bash

      $ source <rez>/bin/activate
      $ python -m pip install rez-pip

.. tab:: Windows

   .. code:: doscon

      C:> source <rez>\Scripts\activate
      C:> python -m pip install rez-pip

If you don't want or can't have a full rez install, yuo can also simply
install rez-pip into it's own virtualenv. Note that this should be a last
resort option.


.. toctree::
   :maxdepth: 1
   :hidden:

   user_guide
   transition
   faq.rst
