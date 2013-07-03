"""Safe execution of untrusted Python code."""

import logging
import os.path
import shutil
import sys
import textwrap

try:
    import simplejson as json
except ImportError:
    import json

from codejail import jail_code
from codejail.util import temp_directory, change_directory

log = logging.getLogger(__name__)


# Flags to let developers temporarily change some behavior in this file.

# Set this to True to log all the code and globals being executed.
LOG_ALL_CODE = False
# Set this to True to use the unsafe code, so that you can debug it.
ALWAYS_BE_UNSAFE = False


class SafeExecException(Exception):
    """
    Python code running in the sandbox has failed.

    The message will be the stdout of the sandboxed process, which will usually
    contain the original exception message.

    """
    pass


def safe_exec(code, globals_dict, files=None, python_path=None, slug=None):
    """
    Execute code as "exec" does, but safely.

    `code` is a string of Python code.  `globals_dict` is used as the globals
    during execution.  Modifications the code makes to `globals_dict` are
    reflected in the dictionary on return.

    `files` is a list of file paths, either files or directories.  They will be
    copied into the temp directory used for execution.  No attempt is made to
    determine whether the file is appropriate or safe to copy.  The caller must
    determine which files to provide to the code.

    `python_path` is a list of directory paths.  They will be copied just as
    `files` are, but will also be added to `sys.path` so that modules there can
    be imported.

    `slug` is an arbitrary string, a description that's meaningful to the
    caller, that will be used in log messages.

    Returns None.  Changes made by `code` are visible in `globals_dict`.  If
    the code raises an exception, this function will raise `SafeExecException`
    with the stderr of the sandbox process, which usually includes the original
    exception message and traceback.

    """
    the_code = []
    files = list(files or ())

    the_code.append(textwrap.dedent(
        """
        import sys
        try:
            import simplejson as json
        except ImportError:
            import json
        """
        # We need to prevent the sandboxed code from printing to stdout,
        # or it will pollute the json we print there.  This isn't a
        # security concern (they can put any values in the json output
        # anyway, either by writing to sys.__stdout__, or just by defining
        # global values), but keeps accidents from happening.
        """
        class DevNull(object):
            def write(self, *args, **kwargs):
                pass
        sys.stdout = DevNull()
        """
        # Read the code and the globals from the stdin.
        """
        code, g_dict = json.load(sys.stdin)
        """))

    for pydir in python_path or ():
        pybase = os.path.basename(pydir)
        the_code.append("sys.path.append(%r)\n" % pybase)
        files.append(pydir)

    the_code.append(textwrap.dedent(
        # Execute the sandboxed code.
        """
        exec code in g_dict
        """
        # Clean the globals for sending back as JSON over stdout.
        """
        ok_types = (
            type(None), int, long, float, str, unicode, list, tuple, dict
        )
        bad_keys = ("__builtins__",)
        def jsonable(v):
            if not isinstance(v, ok_types):
                return False
            try:
                json.dumps(v)
            except Exception:
                return False
            return True
        g_dict = {
            k:v
            for k,v in g_dict.iteritems()
            if jsonable(v) and k not in bad_keys
        }
        """
        # Write the globals back to the calling process.
        """
        json.dump(g_dict, sys.__stdout__)
        """))

    stdin = json.dumps([code, json_safe(globals_dict)])
    jailed_code = "".join(the_code)

    # Turn this on to see what's being executed.
    if LOG_ALL_CODE:        # pragma: no cover
        log.debug("Jailed code: %s", jailed_code)
        log.debug("Exec: %s", code)
        log.debug("Stdin: %s", stdin)

    res = jail_code.jail_code(
        "python", code=jailed_code, stdin=stdin, files=files, slug=slug,
    )
    if res.status != 0:
        raise SafeExecException(
            "Couldn't execute jailed code: %s" % res.stderr
        )
    globals_dict.update(json.loads(res.stdout))


def json_safe(d):
    """
    Return only the JSON-safe part of d.

    Used to emulate reading data through a serialization straw.

    """
    ok_types = (type(None), int, long, float, str, unicode, list, tuple, dict)
    bad_keys = ("__builtins__",)
    jd = {}
    for k, v in d.iteritems():
        if not isinstance(v, ok_types):
            continue
        if k in bad_keys:
            continue
        try:
            # Python's JSON encoder will produce output that
            # the JSON decoder cannot parse if the input string
            # contains unicode "unpaired surrogates" (only on Linux)
            # To test for this, we try decoding the output and check
            # for a ValueError
            json.loads(json.dumps(v))

            # Also ensure that the keys encode/decode correctly
            json.loads(json.dumps(k))
        except (TypeError, ValueError):
            continue
        else:
            jd[k] = v
    return json.loads(json.dumps(jd))


def not_safe_exec(code, globals_dict, files=None, python_path=None, slug=None):
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

            original_path = sys.path
            if python_path:
                sys.path.extend(python_path)
            try:
                exec code in g_dict
            except Exception as e:
                # Wrap the exception in a SafeExecException, but we don't
                # try here to include the traceback, since this is just a
                # substitute implementation.
                msg = "{0.__class__.__name__}: {0!s}".format(e)
                raise SafeExecException(msg)
            finally:
                sys.path = original_path

    globals_dict.update(json_safe(g_dict))


# If the developer wants us to be unsafe (ALWAYS_BE_UNSAFE), or if there isn't
# a configured jail for Python, then we'll be UNSAFE.
UNSAFE = ALWAYS_BE_UNSAFE or not jail_code.is_configured("python")

if UNSAFE:   # pragma: no cover
    # Make safe_exec actually call not_safe_exec, but log that we're doing so.

    def safe_exec(*args, **kwargs):                 # pylint: disable=E0102
        """An actually-unsafe safe_exec, that warns it's being used."""

        # Because it would be bad if this function were used in production,
        # let's log a warning when it is used.  Developers can live with
        # one more log line.
        slug = kwargs.get('slug', None)
        log.warning("Using codejail/safe_exec.py:not_safe_exec for %s", slug)

        return not_safe_exec(*args, **kwargs)
