"""
Codejail exceptions.
"""


class CodeJailException(Exception):
    """
    Top of the hierarchy of codejail exceptions
    """
    pass


class JailError(CodeJailException):
    """
    There was a problem configuring a codejail or accessing a configured codejail.
    """
    pass


class SafeExecException(CodeJailException):
    """
    Python code running in the sandbox has failed.

    The message will be the stdout of the sandboxed process, which will usually
    contain the original exception message.

    """
    pass
