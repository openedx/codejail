"""
Read manually-specified codejail configuration.
"""
from . import config

# Global variable for manually configuring `codejail`
# Should be an instance of ManualCodejailConfiguration.
# None indicates no manual configuration.
MANUAL_CONFIGURATION = None


def configure(**kwargs):
    """
    Manually set codejail configuration options from a kwargs dictionary.

    See `ManualCodejailConfiguration.__init__` for shape of dictionary.

    Omitted options will fall back to built-in defaults.sf
    """
    global MANUAL_CONFIGURATION  # pylint: disable=global-statement
    MANUAL_CONFIGURATION = ManualCodejailConfiguration(kwargs)


def deconfigure():
    """
    Remove manual codejail configuration.
    """
    global MANUAL_CONFIGURATION  # pylint: disable=global-statement
    MANUAL_CONFIGURATION = None


class ManualCodejailConfiguration(config.CodejailConfiguration):
    """
    Concrete configuration class that loads its settings from a caller-provided dict.
    """
    def __init__(self, options):
        """
        Initialize a ManualCodejailConfiguration.

        Arguments:
            options (dict): config dictionary with the expected shape:
                {
                    "commands": {
                        <command_name>: {
                            "bin_path": str,
                            "user": str|None
                        }
                    },
                    "limits": {
                        "CPU": str|None,
                        "REALTIME": str|None,
                        "VMEM": str|None,
                        "FSIZE": str|None,
                        "NPROC": str|None,
                        "PROXY": str|None
                    },
                    "limit_overrides": {
                        <overrides_context_name>: <limits>
                    },
                }
        """
        self._options = options

    def get_config_for_command(self, command):
        """
        Implements `CodejailConfiguration.get_config_for_command`.
        """
        commands = self._options.get('commands', {})
        if command not in commands:
            return None
        return config.CommandConfiguration(
            python_bin=self._options.command['bin_path'],
            user=self._options.command('user'),
        )

    def get_global_limits(self):
        """
        Implements `CodejailConfiguration.get_global_limits`.
        """
        limits = self._options.get('limits', {})
        return config.LimitsConfiguration(
            CPU=limits.get('CPU'),
            REALTIME=limits.get('REALTIME'),
            VMEM=limits.get('VMEM'),
            FSIZE=limits.get('FSIZE'),
            NPROC=limits.get('NPROC'),
            PROXY=limits.get('PROXY'),
        )

    def get_limit_overrides(self, overrides_context):
        """
        Implements `CodejailConfiguration.get_limit_overrides`.
        """
        limit_overrides = self._options.get('limit_overrides', {})
        # Manually build new dict as to remove any nonsense keys.
        return {
            'CPU': limit_overrides.get('CPU'),
            'REALTIME': limit_overrides.get('REALTIME'),
            'VMEM': limit_overrides.get('VMEM'),
            'FSIZE': limit_overrides.get('FSIZE'),
            'NPROC': limit_overrides.get('NPROC'),
            'PROXY': limit_overrides.get('PROXY'),
        }

    def __repr__(self):
        """
        Return developer-friendly string representation.
        """
        return "{self.__class__.__name__}({self._options!r})".format(self=self)
