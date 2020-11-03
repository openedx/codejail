"""
Backend-agnostic utilities to read configuration for codejail.
"""

import abc
from collections import namedtuple


def get_configuration():
    """
    Get a CodejailConfiguration instance.

    We check if there is a manual configuration instance.
    If not, we fall back to DjangoCodejailConfiguration.

    In the future, this function could be modified to support different
    configuration strategies instead of being Django-specific.

    It can also be mocked in unit tests to inject test-case-specific config.
    """
    # pylint: disable=import-outside-toplevel,cyclic-import
    # Use function-level imports so that this module doesn't directly
    # depend on the concrete config implementations.
    from . import config_manual
    if config_manual.MANUAL_CONFIGURATION:
        return config_manual.MANUAL_CONFIGURATION
    from .config_django import DjangoCodejailConfiguration
    return DjangoCodejailConfiguration()


# Configuration for a type of codejail command to run.
CommandConfiguration = namedtuple('CommandConfiguration', [
    # str: path to command binary.
    'bin_path',
    # str|None: if provided, specific user who should be used to run the
    # command.
    'user',
])


# Resource limits for `jail_code`.
# Limits are process-wide.
# Providing a limit of 0 will disable that limit
LimitsConfiguration = namedtuple('LimitsConfiguration', [
    # int: the maximum number of CPU seconds the jailed code can use.
    'CPU',
    # int: the maximum number of seconds the jailed code can run in real time.
    'REALTIME',
    # int: the total virtual memory available to the jailed code, in bytes.
    # A value of zero indicates no memory limit.
    'VMEM',
    # int: the maximum size of files creatable by the jailed code.
    # A value of zero indicates that no files may be created.
    'FSIZE',
    # int: the maximum number of process or threads creatable by jailed code.
    'NPROC',
    # int|None: Whether to use a proxy process or not.
    # 1 to use a proxy process, 0 to not use one.
    # None means use an environment variable to decide.
    # NOTE: using a proxy process is NOT THREAD-SAFE, only one thread can use
    # CodeJail at a time if you are using a proxy process.
    # (This isn't really a limit, sorry about that.)
    'PROXY',
])


class CodejailConfiguration(abc.ABC):
    """
    Abstract class encapsulating configurable Codejail options.
    """

    DEFAULT_LIMITS = LimitsConfiguration(
        CPU=1,
        REALTIME=1,
        VMEM=0,
        FSIZE=0,
        NPROC=15,
        PROXY=None,
    )

    @abc.abstractmethod
    def get_config_for_command(self, command):
        """
        Get configuration for `jail_code` to use on a command.

        Arguments:
            command (str): the abstract command you're configuring,
                such as "python" or "node".

        Returns: CommandConfiguration|None
            The configuration for the given `command`,
            or `None` if not configured.
        """

    @abc.abstractmethod
    def get_global_limits(self):
        """
        Get configured resource limits, ignoring context-specific overrides.

        Returns: LimitsConfiguration
        """

    @abc.abstractmethod
    def get_limit_overrides(self, overrides_context):
        """
        Get the resource limit overrides for a specific context, if configured.

        This does not take into account global or default limits.
        You probably want to use `get_effective_limits`.

        Arguments:
            overrides_context (str): Identifies which set of overrides to use.

        Returns: dict[str, int|None]
            A dictionary, whose keys are attributes of LimitsConfiguration.
        """

    def get_effective_limits(self, overrides_context=None):
        """
        Calculate the effective limits, optionally given an overrides context.

        Arguments:
            overrides_context (str|None): Identifies set of overrides to use.
                If this value is None, or if no overrides are configured for
                this context, then the return value will be identical to that
                of `get_global_limits`.

        Returns: LimitsConfiguration
        """
        return LimitsConfiguration(**{
            **dict(self.get_global_limits()),
            **self.get_limit_overrides(overrides_context),
        })
