"""Needed to corectly track coverage in subprocesses from the integration tests"""

import coverage

coverage.process_startup()
