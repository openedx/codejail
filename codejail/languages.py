"""
Language-specific configuration for codejails.

A language consists of:

    `name` A human readable name for the language.

    `argv` A list of extra language-arguments to pass to the Jail's
    executable.

    `safe_exec_template` Wrapper code to make safe_exec work properly.  If a
    language has safe_exec_template set to None, commands configured to use
    that language will not be able to use `codejail.jail.Jail.safe_exec`, and
    will need to use `codejail.jail.Jail.jail_code` instead.

Preconfigured `Language` objects exist for `python2`, `python3`, and `other`, but
applications can define their own languages by instantiating `Language`.
"""

from collections import namedtuple
import textwrap


Language = namedtuple('Language', ['name', 'argv', 'safe_exec_template'])


# Allow lowercased names at module level
# pylint: disable=invalid-name

other = Language(
    name='other',
    argv=[],
    safe_exec_template=None,
)

python2 = Language(
    name='python2',
    argv=[
        '-E',  # Ignore the environment variables PYTHON*
        '-B',  # Don't write .pyc files.
    ],
    safe_exec_template=textwrap.dedent(
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
        """
        # Update the python path (this will be generated outside the template)
        """
        %(python_path)s
        """
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
        """
    ),
)

python3 = Language(
    name='python3',
    argv=[
        '-E',  # Ignore the environment variables PYTHON*
        '-B',  # Don't write .pyc files.
    ],
    safe_exec_template=textwrap.dedent(
        # See explanatory comments in python2 version
        """
        import sys
        import json
        class DevNull:
            def write(self, *args, **kwargs):
                pass
        sys.stdout = DevNull()
        code, g_dict = json.load(sys.stdin)
        %(python_path)s
        exec(code, g_dict)
        ok_types = (
            type(None), int, float, str, bytes, list, tuple, dict
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
            for k,v in g_dict.items()
            if jsonable(v) and k not in bad_keys
        }
        json.dump(g_dict, sys.__stdout__)
        """
    ),
)
