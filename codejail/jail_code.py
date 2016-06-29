"""Run code in a jail."""

import logging
import os
import os.path
import resource
import shutil
import sys

from .proxy import run_subprocess_through_proxy, get_proxy
from .subproc import run_subprocess
from .util import temp_directory

log = logging.getLogger("codejail")

# TODO: limit too much stdout data?

# Configure the commands

# COMMANDS is a map from an abstract command name to a list of command-line
# pieces, such as subprocess.Popen wants.
COMMANDS = {}


def configure(command, bin_path, user=None):
    """
    Configure a command for `jail_code` to use.

    `command` is the abstract command you're configuring, such as "python" or
    "node".  `bin_path` is the path to the binary.  `user`, if provided, is
    the user name to run the command under.

    """
    cmd_argv = [bin_path]

    # Command-specific arguments
    if command == "python":
        # -E means ignore the environment variables PYTHON*
        # -B means don't try to write .pyc files.
        cmd_argv.extend(['-E', '-B'])

    COMMANDS[command] = {
        # The start of the command line for this program.
        'cmdline_start': cmd_argv,
        # The user to run this as, perhaps None.
        'user': user,
    }


def is_configured(command):
    """
    Has `jail_code` been configured for `command`?

    Returns true if the abstract command `command` has been configured for use
    in the `jail_code` function.

    """
    return command in COMMANDS

# By default, look where our current Python is, and maybe there's a
# python-sandbox alongside.  Only do this if running in a virtualenv.
if hasattr(sys, 'real_prefix'):
    if os.path.isdir(sys.prefix + "-sandbox"):
        configure("python", sys.prefix + "-sandbox/bin/python", "sandbox")


# Configurable limits

LIMITS = {
    # CPU seconds, defaulting to 1.
    "CPU": 1,
    # Real time, defaulting to 1 second.
    "REALTIME": 1,
    # Total process virutal memory, in bytes, defaulting to unlimited.
    "VMEM": 0,
    # Size of files creatable, in bytes, defaulting to nothing can be written.
    "FSIZE": 0,
    # Whether to use a proxy process or not.  None means use an environment
    # variable to decide. NOTE: using a proxy process is NOT THREAD-SAFE, only
    # one thread can use CodeJail at a time if you are using a proxy process.
    "PROXY": None,
}


def set_limit(limit_name, value):
    """
    Set a limit for `jail_code`.

    `limit_name` is a string, the name of the limit to set. `value` is the
    value to use for that limit.  The type, meaning, default, and range of
    accepted values depend on `limit_name`.

    These limits are available:

        * `"CPU"`: the maximum number of CPU seconds the jailed code can use.
            The value is an integer, defaulting to 1.

        * `"REALTIME"`: the maximum number of seconds the jailed code can run,
            in real time.  The default is 1 second.

        * `"VMEM"`: the total virtual memory available to the jailed code, in
            bytes.  The default is 0 (no memory limit).

        * `"FSIZE"`: the maximum size of files creatable by the jailed code,
            in bytes.  The default is 0 (no files may be created).

        * `"PROXY"`: 1 to use a proxy process, 0 to not use one. This isn't
            really a limit, sorry about that.

    Limits are process-wide, and will affect all future calls to jail_code.
    Providing a limit of 0 will disable that limit.

    """
    LIMITS[limit_name] = value


class JailResult(object):
    """
    A passive object for us to return from jail_code.
    """
    def __init__(self):
        self.stdout = self.stderr = self.status = None


def jail_code(command, code=None, files=None, extra_files=None, argv=None,
              stdin=None, slug=None):
    """
    Run code in a jailed subprocess.

    `command` is an abstract command ("python", "node", ...) that must have
    been configured using `configure`.

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

    Return an object with:

        .stdout: stdout of the program, a string
        .stderr: stderr of the program, a string
        .status: exit status of the process: an int, 0 for success

    """
    if not is_configured(command):
        raise Exception("jail_code needs to be configured for %r" % command)

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
        rm_cmd = []

        # Build the command to run.
        user = COMMANDS[command]['user']
        if user:
            # Run as the specified user
            cmd.extend(['sudo', '-u', user, 'TMPDIR=tmp'])
            rm_cmd.extend(['sudo', '-u', user])

        # Start with the command line dictated by "python" or whatever.
        cmd.extend(COMMANDS[command]['cmdline_start'])

        # Add the code-specific command line pieces.
        cmd.extend(argv)

        if use_proxy():
            run_subprocess_fn = run_subprocess_through_proxy
        else:
            run_subprocess_fn = run_subprocess

        # Run the subprocess.
        status, stdout, stderr = run_subprocess_fn(
            cmd=cmd, cwd=homedir, env=env, slug=slug,
            stdin=stdin,
            realtime=LIMITS["REALTIME"], rlimits=create_rlimits(),
            )

        result = JailResult()
        result.status = status
        result.stdout = stdout
        result.stderr = stderr

        # Remove the tmptmp directory as the sandbox user since the sandbox
        # user may have written files that the application user can't delete.
        rm_cmd.extend([
            '/usr/bin/find', tmptmp,
            '-mindepth', '1', '-maxdepth', '1',
            '-exec', 'rm', '-rf', '{}', ';'
        ])

        # Run the rm command subprocess.
        run_subprocess_fn(rm_cmd, cwd=homedir)

    return result


def create_rlimits():
    """
    Create a list of resource limits for our jailed processes.
    """
    rlimits = []

    # No subprocesses.
    rlimits.append((resource.RLIMIT_NPROC, (0, 0)))

    # CPU seconds, not wall clock time.
    cpu = LIMITS["CPU"]
    if cpu:
        # Set the soft limit and the hard limit differently.  When the process
        # reaches the soft limit, a SIGXCPU will be sent, which should kill the
        # process.  If you set the soft and hard limits the same, then the hard
        # limit is reached, and a SIGKILL is sent, which is less distinctive.
        rlimits.append((resource.RLIMIT_CPU, (cpu, cpu+1)))

    # Total process virtual memory.
    vmem = LIMITS["VMEM"]
    if vmem:
        rlimits.append((resource.RLIMIT_AS, (vmem, vmem)))

    # Size of written files.  Can be zero (nothing can be written).
    fsize = LIMITS["FSIZE"]
    rlimits.append((resource.RLIMIT_FSIZE, (fsize, fsize)))

    return rlimits


def startup():
    """
    To be run when whatever process is running codejail starts up.
    If we're using a proxy process, start it. Otherwise, noop.
    """
    if use_proxy():
        return get_proxy()


def use_proxy():
    """
    Use the configuration and maybe an environment variable to determine
    whether to use a proxy process.
    """
    use_it = LIMITS["PROXY"]
    if use_it is None:
        use_it = bool(int(os.environ.get("CODEJAIL_PROXY", "0")))
    return use_it
