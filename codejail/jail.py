"""
Core Jail class and supporting code
"""

from collections import namedtuple
import json
import logging
import os
import shutil

from .exceptions import JailError, SafeExecException
from . import languages
from . import limits
from .proxy import run_subprocess_through_proxy
from .subproc import run_subprocess
from .util import json_safe, temp_directory

log = logging.getLogger("codejail")


JailResult = namedtuple('JailResult', ['status', 'stdout', 'stderr'])


class Jail(object):
    """
    Self contained codejail type.

    This is the main class for working with codejails.  New codejails are
    configured and registered with `codejail.jail.configure()`.

    Creating a Jail takes four arguments:

        `command` is the abstract name of the command to run.  Each code jail
        can be configured and accessed using this name.

        Examples: `"python"`, `"nodejs"`.

        `bin_path` is the path to the system executable to be run.

        Examples: `"/edx/app/edxapp-sandbox/bin/python3"`, `"/usr/bin/ruby"`.

        `user` is the name of a system user to run jailed code as.  The user
        should be configured under AppArmor to protect it from executing
        malicious code, but codejail does not check this.  If set to `None`,
        the code will be run as the same user that is running the codejail
        instance.

        Examples: `"sandbox"`, `None`

        `lang` is a reference to a `codejail.languages.Language` object.  This
        tells codejail how to run a particular command, including what
        command-line arguments to pass to the bin_path executable, and how
        to wrap code to run under safe_exec, if desired.

    Jails can be retrieved with `codejail.jail.get_codejail(cmd)`, where
    `cmd` is the abstract command name of the Jail.

    To use a codejail, call either its `jail_code()` or `safe_exec()` method
    with the documented arguments.

    `jail_code()` runs a snippet of code under the given command, and returns
    its exit code and output.

    `safe_exec()` runs the code with an explicitly defined dict of global
    variables, and updates the dict with any variables assigned during
    execution of the code.
    """
    default_language = languages.other

    known_commands = {
        'python': languages.python2,
    }

    def __init__(self, command, bin_path, user, lang=None):
        self.command = command
        self.bin_path = bin_path
        self.user = user
        if lang is None:
            self.lang = self.known_commands.get(command, self.default_language)
        else:
            self.lang = lang

    @property
    def cmdline_start(self):
        """
        The command line for this program.
        """
        return [self.bin_path] + self.lang.argv

    def __getitem__(self, item):
        """
        For refactoring ease, mimic the old COMMANDS[x] dict
        """
        if item == 'user':
            return self.user
        elif item == 'cmdline_start':
            return self.cmdline_start
        else:
            raise KeyError(item)

    def safe_exec(self, code, globals_dict, files=None, python_path=None, slug=None, extra_files=None):
        """
        Execute code as "exec" does, but safely.

        `code` is a string of Python code.  `globals_dict` is used as the globals
        during execution.  Modifications the code makes to `globals_dict` are
        reflected in the dictionary on return.

        `files` is a list of file paths, either files or directories.  They will be
        copied into the temp directory used for execution.  No attempt is made to
        determine whether the file is appropriate or safe to copy.  The caller must
        determine which files to provide to the code.

        `python_path` is a list of directory or file paths.  These names will be
        added to `sys.path` so that modules they contain can be imported.  Only
        directories and zip files are supported.  If the name is not provided in
        `extra_files`, it will be copied just as if it had been listed in `files`.

        `slug` is an arbitrary string, a description that's meaningful to the
        caller, that will be used in log messages.

        `extra_files` is a list of pairs, each pair is a filename and a bytestring
        of contents to write into that file.  These files will be created in the
        temp directory and cleaned up automatically.  No subdirectories are
        supported in the filename.

        Returns None.  Changes made by `code` are visible in `globals_dict`.  If
        the code raises an exception, this function will raise `SafeExecException`
        with the stderr of the sandbox process, which usually includes the original
        exception message and traceback.
        """
        if self.lang.safe_exec_template is None:
            error_template = "Code Jail {} not configured to run in safe_exec mode.  Try jail_code() instead"
            raise JailError(error_template.format(self.command))
        files = list(files or ())
        extra_files = extra_files or ()
        # TODO: Make this code language-agnostic (See: TNL-4946)
        python_path = python_path or ()

        extra_names = {name for name, contents in extra_files}

        pypath_code = []
        for pydir in python_path:
            pybase = os.path.basename(pydir)
            pypath_code.append("sys.path.append(%r)" % pybase)
            if pybase not in extra_names:
                files.append(pydir)

        stdin = json.dumps([code, json_safe(globals_dict)])
        jailed_code = self.lang.safe_exec_template % {'python_path': '\n'.join(pypath_code)}

        log.debug("Jailed code: %s", jailed_code)
        log.debug("Exec: %s", code)
        log.debug("Stdin: %s", stdin)

        response = self.jail_code(
            code=jailed_code,
            stdin=stdin,
            files=files,
            slug=slug,
            extra_files=extra_files,
        )
        if response.status != 0:
            raise SafeExecException((
                "Couldn't execute jailed code: stdout: {res.stdout!r}, "
                "stderr: {res.stderr!r} with status code: {res.status}"
            ).format(res=response))
        try:
            resulting_globals = json.loads(response.stdout)
        except (TypeError, ValueError):
            raise JailError("Returned value was not valid JSON: {!r}".format(response.stdout))
        if not isinstance(resulting_globals, dict):
            raise JailError("Returned value was not a JSON object: {!r}".format(response.stdout))
        globals_dict.update(resulting_globals)

    def jail_code(self, code=None, files=None, extra_files=None, argv=None, stdin=None, slug=None):
        """
        Run code in the current jail.

        `code` is a string containing the code to run.  If no code is supplied,
        then the code to run must be in one of the `files` copied, and must be
        named in the `argv` list.

        `files` is a list of file paths, they are all copied to the jailed
        directory.  Note that no check is made here that the files don't contain
        sensitive information.  The caller must somehow determine whether to allow
        the code access to the files.  Symlinks will be copied as symlinks.  If the
        linked-to file is not accessible to the sandbox, the symlink will be
        unreadable as well.

        `extra_files` is a list of pairs, each pair is a filename and a bytestring
        of contents to write into that file.  These files will be created in the
        temp directory and cleaned up automatically.  No subdirectories are
        supported in the filename.

        `argv` is the command-line arguments to supply.

        `stdin` is a string, the data to provide as the stdin for the process.

        `slug` is an arbitrary string, a description that's meaningful to the
        caller, that will be used in log messages.

        Return a JailResult namedtuple with:

            .status: exit status of the process: an int, 0 for success
            .stdout: stdout of the program, a string
            .stderr: stderr of the program, a string

        """
        # We make a temp directory to serve as the home of the sandboxed code.
        # It has a writable "tmp" directory within it for temp files.
        with temp_directory() as homedir:

            # Make directory readable by other users ('sandbox' user needs to be
            # able to read it).
            os.chmod(homedir, 0775)

            # Make a subdir to use for temp files, world-writable so that the
            # sandbox user can write to it.
            tmptmp = os.path.join(homedir, "tmp")
            os.mkdir(tmptmp)
            os.chmod(tmptmp, 0777)

            argv = argv or []
            env = {'TMPDIR': 'tmp'}

            # All the supporting files are copied into our directory.
            for filename in files or ():
                dest = os.path.join(homedir, os.path.basename(filename))
                if os.path.islink(filename):
                    os.symlink(os.readlink(filename), dest)
                elif os.path.isfile(filename):
                    shutil.copy(filename, homedir)
                else:
                    shutil.copytree(filename, dest, symlinks=True)

            # Create the main file.
            if code:
                with open(os.path.join(homedir, "jailed_code"), "wb") as jailed:
                    jailed.write(code)

                argv = ["jailed_code"] + argv

            # Create extra files requested by the caller:
            for name, content in extra_files or ():
                with open(os.path.join(homedir, name), "wb") as extra:
                    extra.write(content)

            cmd = []

            # Build the command to run.
            if self.user:
                # Run as the specified user
                cmd.extend(['sudo', '-u', self.user, 'TMPDIR=tmp'])

            # Add the command-specific pieces
            cmd.extend(self.cmdline_start)
            # Add the code-specific command line pieces.
            cmd.extend(argv)

            # Use the configuration and maybe an environment variable to determine
            # whether to use a proxy process.
            use_proxy = limits.LIMITS["PROXY"]
            if use_proxy is None:
                use_proxy = int(os.environ.get("CODEJAIL_PROXY", "0"))
            if use_proxy:
                run_subprocess_fn = run_subprocess_through_proxy
            else:
                run_subprocess_fn = run_subprocess

            # Run the subprocess.
            status, stdout, stderr = run_subprocess_fn(
                cmd=cmd, cwd=homedir, env=env, slug=slug,
                stdin=stdin,
                realtime=limits.LIMITS["REALTIME"], rlimits=limits.create_rlimits(),
            )

            # TODO: limit too much stdout/stderr data?
            result = JailResult(status, stdout, stderr)

            # Remove the tmptmp directory as the sandbox user since the sandbox
            # user may have written files that the application user can't
            # delete.
            run_subprocess_fn(self._build_rm_command(tmptmp), cwd=homedir)

        return result

    def _build_rm_command(self, directory):
        """
        Collect the command line arguments to remove the specified directory
        """
        rm_cmd = []
        if self.user:
            rm_cmd.extend(['sudo', '-u', self.user])
        rm_cmd.extend([
            '/usr/bin/find', directory,
            '-mindepth', '1', '-maxdepth', '1',
            '-exec', 'rm', '-rf', '{}', ';'
        ])
        return rm_cmd


# Configure the commands

# COMMANDS is a map from an abstract command name to a list of command-line
# pieces, such as subprocess.Popen wants.
COMMANDS = {}


def configure(command, bin_path, user=None, lang=None):
    """
    Configure a Jail object

    `command` is the abstract command you're configuring, such as "python" or
    "node".  `bin_path` is the path to the binary.  `user`, if provided, is the
    user name to run the command under, `lang`.  These options are documented
    more thoroughly on the `Jail` class, above.
    """
    jail = Jail(command, bin_path, user, lang)
    COMMANDS[command] = jail
    return jail


def get_codejail(command):
    """
    Return a configured `Jail` object configured with the specified `command`.

    Raises a `JailError` if the command is not configured.
    """
    try:
        return COMMANDS[command]
    except KeyError:
        raise JailError("CodeJail not found for {}".format(command))


def is_configured(command):
    """
    Has a `Jail` been configured for `command`?

    Returns `True` if the a `Jail` has been configured for the abstract command
    `command`.
    """
    return command in COMMANDS
