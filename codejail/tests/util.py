"""
Shared utilities for codejail tests.
"""

from .. import jail_code


class ResetJailCodeStateMixin:
    """
    The jail_code module has global state held in ``_default_config``.

    Use this mixin to reset codejail to its initial state before running a test
    function, and then restore the existing state once the test function is
    complete.

    The three module-level names ``COMMANDS``, ``LIMITS``, and
    ``LIMIT_OVERRIDES`` are backward-compat aliases that reference the *same*
    dict objects stored inside ``_default_config``.  We therefore mutate those
    dicts in-place (``clear`` + ``update``) rather than rebinding the names, so
    that both access paths stay consistent throughout the test.
    """

    def setUp(self):
        """
        Reset global variables back to defaults, copying and saving existing values.
        """
        super().setUp()
        cfg = jail_code._default_config
        # pylint: disable=invalid-name
        self._COMMANDS = dict(cfg.COMMANDS)
        self._LIMITS = dict(cfg.LIMITS)
        self._LIMIT_OVERRIDES = {k: dict(v) for k, v in cfg.LIMIT_OVERRIDES.items()}
        cfg.COMMANDS.clear()
        cfg.LIMITS.clear()
        cfg.LIMITS.update(jail_code.DEFAULT_LIMITS)
        cfg.LIMIT_OVERRIDES.clear()

    def tearDown(self):
        """
        Restore global variables to the values they had before running the test.
        """
        super().setUp()
        cfg = jail_code._default_config
        cfg.COMMANDS.clear()
        cfg.COMMANDS.update(self._COMMANDS)
        cfg.LIMITS.clear()
        cfg.LIMITS.update(self._LIMITS)
        cfg.LIMIT_OVERRIDES.clear()
        cfg.LIMIT_OVERRIDES.update(self._LIMIT_OVERRIDES)
