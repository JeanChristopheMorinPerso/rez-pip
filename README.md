<!--
SPDX-FileCopyrightText: 2022 Contributors to the rez project

SPDX-License-Identifier: Apache-2.0
-->

# rez-pip
[![Coverage](https://codecov.io/gh/JeanChristopheMorinPerso/rez-pip/branch/main/graph/badge.svg?token=SYLI4WI7F1)](https://codecov.io/gh/JeanChristopheMorinPerso/rez-pip)

rez-pip is a [rez](https://github.com/AcademySoftwareFoundation/rez) command-line plugin that you can use to make package from
the [Python Package Index](https://pypi.org) and other indexes available to your rez package ecosystem.

## Features

* Simpler to use thanks to the vendoring of pip.
* Does **not** support installing packages for Python 2.
* Only creates per python version variants when absolutely necessary. For example, it won't
  create per python version variants when installing a package that has console scripts.
* Better output logs.
* Implemented as an out-of-tree plugin, which means faster development cycle and more frequent releases.
* [Plugin system](https://rez-pip.readthedocs.io/en/stable/plugins.html) that allows for easy extensibility (experimental).
* Maintained by the rez maintainers.

## TODOs

* [x] Install packages without using pip
* [x] Specify Python version to use
* [x] Better logs and CLI experience
    * [x] Use logging
    * [x] Progress bars for download?
* [x] Confirm that Python 2 is supported
    * It is not...
* [x] Confirm that the theory works as expected
* [x] Windows support
* [ ] Hook into rez
    * [x] Install each package in a different `--target`
    * [x] Create rez package
    * [x] Copy distribution files to rez package.
    * [ ] Make it available as a rez plugin/sub-command
    * [x] Discover Python package using rez and use that when available. I think it's still fine to support non-rezified Python interpreters though.
* [x] Accept multiple package names as input
* [x] Accept requirements files as input
* [x] Accept wheel files as input
* [ ] Properly support platform tags (wheels tags) so that GLIBC is respected, min macOS is also supported.
* [ ] Correctly handle Requires-Python metadata.
* [ ] Review all TODOs in the code.
* ~~What whould we do with `rez.system` and `rez.vendor.version`?~~
* [ ] Gather a list of problematic packages from GitHub and test against them.
* [ ] Go through GitHub issues and summarize what needs to be covered by the new rez-pip.
* [ ] Support abi3 wheels (to avoid having to re-install C extensions for every python version).
    * https://docs.python.org/3/c-api/stable.html
    * https://peps.python.org/pep-0425/
    * Basically a tag like 'cp36-abi3-manylinux_2_24_x86_64' means
      that it is compatible with Python 3.6+ and doesn't need to be
      recompiled for newer python versions.

## Packages to test against

* pytest
* PySide, PySIde2, PySide6
* PyQt4, PyQt5
* psycopg2-binary
* ipython
* numpy
* protobuf
* click
* Pygments (https://github.com/AcademySoftwareFoundation/rez/issues/1430)
* google_api_core (https://github.com/AcademySoftwareFoundation/rez/issues/1414)
* sphinx
* networkx[default] (https://github.com/AcademySoftwareFoundation/rez/issues/1409)
* black (https://github.com/AcademySoftwareFoundation/rez/issues/1341)
* pylint (https://github.com/AcademySoftwareFoundation/rez/issues/1024)
* ampq (https://github.com/AcademySoftwareFoundation/rez/issues/906)
* cmd2 (https://github.com/AcademySoftwareFoundation/rez/issues/895)
* astroid (https://github.com/AcademySoftwareFoundation/rez/issues/876)
* Qt.py (https://github.com/AcademySoftwareFoundation/rez/issues/503)
* Pillow
* BeautifulSoup4
* python-dateutil (https://github.com/AcademySoftwareFoundation/rez/issues/390)
