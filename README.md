# rez-pip
Modern rez-pip implementation

## TODOs

* [x] Install packages without using pip
* [x] Specify Python version to use
* [ ] Better logs and CLI experience
    * Use logging
    * Progress bars for download?
* [ ] Confirm that Python 2 is supported
* [ ] Confirm that the theory works as expected
* [ ] Windows support
* [ ] Hook into rez
    * Install each package in a different `--target`
    * Create rez package
    * etc
* [ ] Accept multiple package names as input
* [ ] Accept requirements files as input
* [ ] Accept whee files as input
* [ ] Properly support platform tags (wheels tags) so that GLIBC is respected, min macOS is also supported.
* [ ] Correctly handle Requires-Python metadata.
