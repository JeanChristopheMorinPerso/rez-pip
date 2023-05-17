==========
User guide
==========


Selecting the python version
============================

``rez-pip`` will look for python packages that are available based on your
rez configuration. By default, it will use all available versions.

By using ``--python-version``, you can select which version of python
to use for the requested packages. You can use the same version selecton syntax
that rez supports (``>=3``, ``3.7|3.9``, etc) or you can also use ``latest``.

.. note::
    Your rez package that contains python needs to be named ``python``.
    It will not work if your package is named differently.

