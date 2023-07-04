# 0.2.0 (2023-07-04)

This release fixes a lot of bugs and gets us closer to a more official release.

Most notable changes:
* Dropped support for installing Python 2 packages. Python 3.7+ is supported. See [PR #39](https://github.com/JeanChristopheMorinPerso/rez-pip/pull/39).
* A lot more documentation. It now includes a transition guide, a user guide, information on the metadata conversion process, etc.
* The command line arguments have been cleaned up (`--install-path` renamed to `--prefix`, `--release` was added, etc).
* A lightweigth weehl cache was added to avoid re-downloading the same wheel for multiple python versions.
* New `--debug-info` command line argument to help debugging when there is issues.
