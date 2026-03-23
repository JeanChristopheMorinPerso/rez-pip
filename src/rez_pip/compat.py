# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

import sys

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

__all__ = ["importlib_metadata"]
