"""Safe execution of untrusted Python code."""

import logging
import os.path
import shutil
import sys

from .exceptions import SafeExecException
from .jail import get_codejail, is_configured
from .util import temp_directory, change_directory, json_safe

log = logging.getLogger("codejail")


# Flags to let developers temporarily change some behavior in this file.

# Set this to True to use the unsafe code, so that you can debug it.
ALWAYS_BE_UNSAFE = False


def safe_exec(code, globals_dict, files=None, python_path=None, slug=None,
              extra_files=None):
    """
    Execute code as "exec" does, but safely.

    This function calls through to the `safe_exec()` method on the `Jail`
    object with the command name `"python"`.

    Arguments and behavior are documented at `codejail.jail.Jail.safe_exec`

    This function exists primarily for backwards compatibility, and to
    support the unsafe_exec functionality.  If you do not need these features,
    consider using `codejail.jail.Jail.safe_exec` instead.

    >>> import codejail.jail
    >>> jail = codejail.jail.get_codejail("python")
    >>> jail.safe_exec(...)
    """
    jail = get_codejail("python")

    jail.safe_exec(
        code=code,
        globals_dict=globals_dict,
        files=files,
        python_path=python_path,
        slug=slug,
        extra_files=extra_files
    )


def not_safe_exec(
        code,
        globals_dict,
        files=None,
        python_path=None,
        slug=None,
        extra_files=None
    ):  # pylint: disable=unused-argument
    """
    Another implementation of `safe_exec`, but not safe.

    This can be swapped in for debugging problems in sandboxed Python code.

    This is not thread-safe, due to temporarily changing the current directory
    and modifying sys.path.
    """
    g_dict = json_safe(globals_dict)

    with temp_directory() as tmpdir:
        with change_directory(tmpdir):
            # Copy the files here.
            for filename in files or ():
                dest = os.path.join(tmpdir, os.path.basename(filename))
                shutil.copyfile(filename, dest)
            for filename, contents in extra_files or ():
                dest = os.path.join(tmpdir, filename)
                with open(dest, "w") as target_file:
                    target_file.write(contents)

            original_path = sys.path
            if python_path:
                sys.path.extend(python_path)
            try:
                exec code in g_dict  # pylint: disable=exec-used
            except Exception as exc:
                # Wrap the exception in a SafeExecException, but we don't
                # try here to include the traceback, since this is just a
                # substitute implementation.
                msg = "{0.__class__.__name__}: {0!s}".format(exc)
                raise SafeExecException(msg)
            finally:
                sys.path = original_path

    globals_dict.update(json_safe(g_dict))


if ALWAYS_BE_UNSAFE:   # pragma: no cover
    # Make safe_exec actually call not_safe_exec, but log that we're doing so.

    def safe_exec(*args, **kwargs):                 # pylint: disable=E0102
        """An actually-unsafe safe_exec, that warns it's being used."""

        # Because it would be bad if this function were used in production,
        # let's log a warning when it is used.  Developers can live with
        # one more log line.
        slug = kwargs.get('slug', None)
        log.warning("Using codejail/safe_exec.py:not_safe_exec for %s", slug)

        return not_safe_exec(*args, **kwargs)
