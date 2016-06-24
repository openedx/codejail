"""
Primary codejail exports.

    import codejail
    codejail.configure('python78', '/path/to/python3', user='root', lang=codejail.python3)
    try:
        jail = codejail.get_codejail('python78')
    except JailError:
        raise
    try:
        jail.safe_exec("print('foo')", {'print': print}, slug='hotcode')
    except codejail.CodeJailException:
        # raises a JailError if the jail can't handle safe_exec.
        # raises a SafeExecException if the code fails.
        raise
    jail.jail_code("print('foo')", slug='hotcode')
"""

from .exceptions import CodeJailException, JailError, SafeExecException
from .jail import configure, is_configured, get_codejail
from .languages import python2, python3, other
