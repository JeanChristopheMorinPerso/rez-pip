# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

"""Needed to corectly track coverage in subprocesses from the integration tests"""

import coverage

coverage.process_startup()
