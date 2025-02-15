# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""rez-pip2"""

import argparse

import rez.command


command_behavior = {
    "hidden": False,  # optional: bool
    "arg_mode": "grouped",  # optional: None, "passthrough", "grouped"
}


def setup_parser(parser: argparse.ArgumentParser, completions=False):
    import rez_pip.cli

    rez_pip.cli._setupParser(parser, fromRez=True)


def command(opts, parser=None, extra_arg_groups=None) -> int:
    import rez_pip.cli

    return rez_pip.cli.run(args=opts, pipArgs=extra_arg_groups)


class RezPip(rez.command.Command):
    """asd"""


def register_plugin():
    return RezPip
