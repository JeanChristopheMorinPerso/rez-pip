# rez-pip
[![Coverage](https://codecov.io/gh/JeanChristopheMorinPerso/rez-pip/branch/main/graph/badge.svg?token=SYLI4WI7F1)](https://codecov.io/gh/JeanChristopheMorinPerso/rez-pip)

Modern rez-pip implementation. Very WIP.

## TODOs

* [x] Install packages without using pip
* [x] Specify Python version to use
* [ ] Better logs and CLI experience
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
    * [ ] Discover Python package using rez and use that when available. I think it's still fine to support non-rezified Python interpreters though.
    * [ ] Only download+convert package if it's not already in the rez repositories.
    * etc
* [x] Accept multiple package names as input
* [x] Accept requirements files as input
* [ ] Accept wheel files as input
* [ ] Properly support platform tags (wheels tags) so that GLIBC is respected, min macOS is also supported.
* [ ] Correctly handle Requires-Python metadata.
* [ ] Review all TODOs in the code.
* What whould we do with `rez.system` and `rez.vendor.version`?
* [ ] Gather a list of problematic packages from GitHub and test against them.
* [ ] Go through GitHub issues and summarize what needs to be covered by the new rez-pip.
* [ ] Support abi3 wheels (to avoid having to re-install C extensions for every python version).
    * https://docs.python.org/3/c-api/stable.html
    * https://peps.python.org/pep-0425/
    * Basically a tag like 'cp36-abi3-manylinux_2_24_x86_64' means
      that it is compatible with Python 3.6+ and doesn't need to be
      recompiled for newer python versions.

## Tips

For now, it can be run like this:

```
rez-pip2 pytest
```

By default, rez packages will be released. You can choose a different path by passing the `--install-path` argument to rez-pip2.

# Packages to test against

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
