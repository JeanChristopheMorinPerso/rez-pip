# rez-pip
Modern rez-pip implementation. Very WIP.

## TODOs

* [x] Install packages without using pip
* [x] Specify Python version to use
* [ ] Better logs and CLI experience
    * [x] Use logging
    * [ ] Progress bars for download?
* [ ] Confirm that Python 2 is supported
* [ ] Confirm that the theory works as expected
* [ ] Windows support
* [ ] Hook into rez
    * [ ] Install each package in a different `--target`
    * [ ] Create rez package
    * [ ] Copy distribution files to rez package.
    * etc
* [ ] Accept multiple package names as input
* [ ] Accept requirements files as input
* [ ] Accept whee files as input
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
