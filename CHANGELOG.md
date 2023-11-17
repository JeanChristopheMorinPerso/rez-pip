# 0.3.1 (2023-11-17)

* Fix decoding error when reading pip dependency report. See [PR #63](https://github.com/JeanChristopheMorinPerso/rez-pip/pull/63).
* Update vendored pip from 23.2.1 to 23.3.1

# 0.3.0 (2023-10-12)

Most notable changes:
* Don't append system PATH to context when finding the python executables (#47)
* Update pip from 23.1.2 to 23.2 (#44)
* Ensure Windows short paths are resolved to long paths (#50)
* Read rez-pip version from distribution metadata (#53)

# 0.2.0 (2023-07-04)

This release fixes a lot of bugs and gets us closer to a more official release.

Most notable changes:
* Dropped support for installing Python 2 packages. Python 3.7+ is supported. See [PR #39](https://github.com/JeanChristopheMorinPerso/rez-pip/pull/39).
* A lot more documentation. It now includes a transition guide, a user guide, information on the metadata conversion process, etc.
* The command line arguments have been cleaned up (`--install-path` renamed to `--prefix`, `--release` was added, etc).
* A lightweigth weehl cache was added to avoid re-downloading the same wheel for multiple python versions.
* New `--debug-info` command line argument to help debugging when there is issues.
