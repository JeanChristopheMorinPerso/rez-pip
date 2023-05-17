================
Transition guide
================

Transitioning to the new rez-pip should be pretty straight forward. There is differences between the
two tools, but there is nothing "major" in terms of installing packages `from` PyPI.

Some functionalities didn't make it into the new rez-pip. The most obvious one is the ability
to ``rez-pip -i .``, or in other words, install packages from a working directory.
This functionality is completely gone and there is no plan to re-implement it.
