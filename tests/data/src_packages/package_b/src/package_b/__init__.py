# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

import sys


def run():
    # We want to test that the executable is really the correct one, the one we expect.
    # So printing it will allow us to compare it.
    sys.stdout.write(sys.executable)
