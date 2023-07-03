========
Metadata
========

``rez-pip`` does its best to convert the `PyPA core metadata`_ into rez's metadata.

It is able to to convert most of the `PyPA core metadata`_:

* Name
* Version
* Summary
* Description
* Author
* Author-email
* Maintainer
* Maintainer-email
* License
* Home-page
* Project-URL
* Download-URL

.. _PyPA core metadata: https://packaging.python.org/en/latest/specifications/core-metadata/

Name
====

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#name

Stored in ``name``.

.. warning::
   ``-`` will be converted to ``_``

Version
=======

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#name

Stored in ``version``. Versions will be converted from :pep:`440` format to
a rez compatible format.

Summary
=======

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#summary

Stored in ``summary`` as is.

Description
===========

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#description

Stored in ``description`` as is.

Author and Maintainer
=====================

Links:

* https://packaging.python.org/en/latest/specifications/core-metadata/#author
* https://packaging.python.org/en/latest/specifications/core-metadata/#maintainer

Appended to ``authors`` as is.

Author-email and Maintainer-email
=================================

Links:

* https://packaging.python.org/en/latest/specifications/core-metadata/#author-email
* https://packaging.python.org/en/latest/specifications/core-metadata/#maintainer-email

Each email is appended to ``authors`` as is.

License
=======

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#license

If present, it will be stored as in a custom attributed called ``license`` as is.

If not present, ``rez-pip`` will look into `classifiers`_ for any value that starts with ``License ::``.
If one is found, it will be used as the license. If more than one is found, ``license`` will not be set.

.. _classifiers: https://packaging.python.org/en/latest/specifications/core-metadata/#classifier-multiple-use


Home-page
=========

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#home-page

Appended to ``help`` like this:

.. code-block::

   help = [
       ['Home-page', 'https://example.com']
   ]

Project-URL
===========

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#project-url-multiple-use

Project URLs are appended to ``help``. For example, if a package defines

.. code-block::

   {
       'Documentation': 'https://example.com/docs',
       'Source': 'https://example.com/source'
   }

it will be converted to:

.. code-block::

   help = [
       ['Documentation', 'https://exmaple.com/docs'],
       ['Source', 'https://example.com/source']
   ]

Download-URL
============

Link: https://packaging.python.org/en/latest/specifications/core-metadata/#download-url

Appended to ``help`` like this:

.. code-block::

   help = [
       ['Download-URL', 'https://example.com/download']
   ]

Extra metadata added by rez-pip
===============================

``rez-pip`` will add a ``pip`` attribute in the installed package definitions.

.. code-block::

   pip = {
       "name": "",
       "version": "",
       "is_pure_python": "",
       "wheel_url": "",
       "rez_pip_version": "",
       "metadata": {}
   }

The definition for the fields is described in the table bellow.

=============== ==============
Attribute       Description
=============== ==============
name            Original name of the package
version         Original version
is_pure_python  Is the package a pure python package?
wheel_url       URL of the wheel downloaded and installed
rez_pip_version Version of rez-pip used to create the package
metadata        All metadata that was not converted will be stored in this field
=============== ==============
