<!--
SPDX-FileCopyrightText: 2022 Contributors to the rez project

SPDX-License-Identifier: Apache-2.0
-->

# Changelog

<!-- start-here-sphinx-start-after -->

## 0.4.0 (2025-10-25)

This is a big release. It includes a lot of changes and improvements.

The most notable changes are:
* Convert to rez plugin. You can now call the new rez pip using `rez pip2`. It is not a native rez plugin (#136).
* Drop support for installing rez-pip with Python 3.8. You can still install Python 3.7 packages (#120).
* Add plugin system and local wheels support. See https://rez-pip.readthedocs.io/en/stable/plugins.html (#91).
* PySide6 can now be installed without issues, including on Windows. It now "just works".
* Update pip from 23.3.1 to 23.3.2 (#87).
* Support PEP 639 (#216).
* Add support for Python 3.12 and 3.13 (#215).

Other changes:
* Fix bad dist-info discovery in wheel installation process (#182).
* Fix logging bugs introduced by PR #91 (#126).
* Handle error cases in rez_pip.rez.getPythonExecutables explicitly (#125).
* Use py-rattler instead of conda to create the python packages (#90).
* Fix compatibility with importlib-metadata 8 and Python 3.13 (#114).
* Raise an exception when no python package found (#81, @MrLixm).
* Replace usage of rez.vendor.version with rez.version introduced in rez 2.114.0 (#84).
* Only return the latest version for major+minor python versions instead of returning all versions (#83).

## 0.3.2 (2023-12-09)

* Add changelog to docs (#68)
* Add GH Action workflow to do sanity checks on docs (#69)
* Fix mypy check failing due to recent aiohttp 3.9.0 release that dropped support for Python 3.7
* Add CLI reference to docs (#70)
* Fix missing `rez_pip_version` in rez package metadata (in the `pip` attribute) (#77)

## 0.3.1 (2023-11-17)

* Fix decoding error when reading pip dependency report (#63).
* Update vendored pip from 23.2.1 to 23.3.1.

## 0.3.0 (2023-10-12)

Most notable changes:
* Don't append system PATH to context when finding the python executables (#47).
* Update pip from 23.1.2 to 23.2 (#44).
* Ensure Windows short paths are resolved to long paths (#50).
* Read rez-pip version from distribution metadata (#53).

## 0.2.0 (2023-07-04)

This release fixes a lot of bugs and gets us closer to a more official release.

Most notable changes:
* Dropped support for installing Python 2 packages. Python 3.7+ is supported (#39).
* A lot more documentation. It now includes a transition guide, a user guide, information on the metadata conversion process, etc.
* The command line arguments have been cleaned up (`--install-path` renamed to `--prefix`, `--release` was added, etc).
* A lightweigth weehl cache was added to avoid re-downloading the same wheel for multiple python versions.
* New `--debug-info` command line argument to help debugging when there is issues.
