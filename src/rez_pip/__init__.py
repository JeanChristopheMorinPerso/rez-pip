# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""PyPI/python package ingester/converter for the rez package manager"""

from __future__ import annotations

import argparse


command_behavior = {
    "hidden": False,  # optional: bool
    "arg_mode": "grouped",  # optional: None, "passthrough", "grouped"
}


def setup_parser(parser: argparse.ArgumentParser) -> None:
    import rez_pip.cli

    rez_pip.cli._setupParser(parser, fromRez=True)


def command(
    opts: argparse.Namespace,
    _: argparse.ArgumentParser,
    extra_arg_groups: list[list[str]],
) -> int:
    import rez_pip.cli

    pipArgs = [arg for group in extra_arg_groups for arg in group]
    return rez_pip.cli.run(args=opts, pipArgs=pipArgs)


def register_plugin():  # type: ignore
    # Defined here to avoid cirlular imports
    import rez.command

    class RezPip(rez.command.Command):  # type: ignore
        """asd"""

    return RezPip
