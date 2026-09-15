"""
Shared utilities for codejail tests.
"""

from .. import jail_code


class ResetJailCodeStateMixin:
    """
    The jail_code module has global state.

    Use this mixin to reset jail_code to its initial state before running a test function,
    and then restore the existing state once the test function is complete.
    """

    def setUp(self):
        """
        Reset global variables back to defaults, copying and saving existing values.
        """
        super().setUp()
        # pylint: disable=invalid-name
        self._COMMANDS = jail_code.COMMANDS
        self._LIMITS = jail_code.LIMITS
        self._LIMIT_OVERRIDES = jail_code.LIMIT_OVERRIDES
        jail_code.COMMANDS = {}
        jail_code.LIMITS = jail_code.DEFAULT_LIMITS.copy()
        jail_code.LIMIT_OVERRIDES = {}

    def tearDown(self):
        """
        Restore global variables to the values they had before running the test.
        """
        super().setUp()
        jail_code.COMMANDS = self._COMMANDS
        jail_code.LIMITS = self._LIMITS
        jail_code.LIMIT_OVERRIDES = self._LIMIT_OVERRIDES
