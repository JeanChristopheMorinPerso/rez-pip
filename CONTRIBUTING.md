<!--
SPDX-FileCopyrightText: 2022 Contributors to the rez project

SPDX-License-Identifier: Apache-2.0
-->

# Welcome to rez-pip docs contributing guide

Thank you for investing your time in contributing to our project!

Read our [Code of Conduct](./CODE_OF_CONDUCT.md) to keep our community approachable and respectable.

In this guide you will get an overview of the contribution workflow from opening an issue, creating a PR, reviewing, and merging the PR.

## New contributor guide

To get an overview of the project, read the [README](README.md) file. Here are some resources to help you get started with open source contributions:

- [Finding ways to contribute to open source on GitHub](https://docs.github.com/en/get-started/exploring-projects-on-github/finding-ways-to-contribute-to-open-source-on-github)
- [Set up Git](https://docs.github.com/en/get-started/quickstart/set-up-git)
- [GitHub flow](https://docs.github.com/en/get-started/quickstart/github-flow)
- [Collaborating with pull requests](https://docs.github.com/en/github/collaborating-with-pull-requests)


## Getting started

The repository is organized in 3 folders:

* [docs](./docs): Contains the documentation, written in reStructuredText and uses Sphinx.
* [src](./src): Contains the source code.
* [tests](./tests): Contains all the tests.

### Issues

#### Create a new issue

If you spot a problem with rez-pip, [search if an issue already exists](https://docs.github.com/en/github/searching-for-information-on-github/searching-on-github/searching-issues-and-pull-requests#search-by-the-title-body-or-comments). If a related issue doesn't exist, you can open a new issue using a relevant [issue form](https://github.com/JeanChristopheMorinPerso/rez-pip/issues/new).

#### Solve an issue

Scan through our [existing issues](https://github.com/JeanChristopheMorinPerso/rez-pip/issues) to find one that interests you. You can narrow down the search using `labels` as filters. As a general rule, we don’t assign issues to anyone. If you find an issue to work on, you are welcome to say so in the issue and open a PR with a fix.

### Make Changes

1. Fork the repository.
2. Install or update to **Python**, at the version specified in [pyproject.toml](./pyproject.toml).
3. Create a working branch and start with your changes!


### Write tests

All changes should be accompanied with tests. The complexity of the tests will vary based on the area
you made changes to, the size of the changes etc.

We have multiple types of tests. For example, we have pure unit tests and we also have integration tests.

Tests are written and run with [pytest](https://docs.pytest.org).

To run the tests, you have two options:

1. Use `pipx run nox -s test`.
2. ```
   python -m venv .venv
   source .venv/bin/activate

   pip install -r tests/requirements.txt
   pip install .

   pytest -v tests
   ```

There is no preference. Yuo can use whatever method you prefer.
If you are already a [nox](https://nox.thea.codes/en/stable/) user, it's pretty handy.
If not, then ddon't feel the necessity to use it.

### Linters, formetters, type checking

All code should be formatter using [Black](https://black.readthedocs.io/en/stable/). No linter is
currently configured. Type checking is mendatory and is also set to be strict.

You can format your code using `pipx run nox -s format` and type check the code
using `pipx run nox -s mypy`.

### Commit your update

Commit the changes and tests once you are happy with them.

### Pull Request

When you're finished with the changes, create a pull request, also known as a PR.

Try to write a more than one sentence in the description field. Explain why you are
doing the changes, why you did the changeds the way you did, tradeoffs. If there
is compatibility concerns, please mention them too. The description should be
as detailed as possible to help us better review your PR.
