"""
Helper code to facilitate testing
"""

from contextlib import contextmanager

from codejail import jail_code

SAME = object()


@contextmanager
def override_configuration(command, bin_path, user):
    """
    Context manager to temporarily alter the configuration of a codejail
    command.
    """
    old = jail_code.COMMANDS.get(command)
    if bin_path is SAME:
        bin_path = old['cmdline_start'][0]
    if user is SAME:
        user = old['user']
    try:
        jail_code.configure(command, bin_path, user)
        yield
    finally:
        if old is None:
            del jail_code.COMMANDS[command]
        else:
            jail_code.COMMANDS[command] = old
