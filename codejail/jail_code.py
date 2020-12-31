"""Run code in a jail."""

import logging
import os
import os.path
import resource
import shutil
import sys

from .proxy import run_subprocess_through_proxy
from .subproc import run_subprocess
from .util import temp_directory

log = logging.getLogger("codejail")

# TODO: limit too much stdout data?  # pylint: disable=fixme

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
# The check for sys.real_prefix covers virtualenv
# the equality of non-empty sys.base_prefix with sys.prefix covers venv
running_in_virtualenv = (
    hasattr(sys, 'real_prefix') or
    (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
)

if running_in_virtualenv:
    # On jenkins
    sandbox_user = os.getenv('CODEJAIL_TEST_USER')
    sandbox_env = os.getenv('CODEJAIL_TEST_VENV')
    if sandbox_env and sandbox_user:
        configure("python", f"{sandbox_env}/bin/python", sandbox_user)
    # or fall back to defaults
    elif os.path.isdir(sys.prefix + "-sandbox"):
        configure("python", sys.prefix + "-sandbox/bin/python", "sandbox")


# The resource limits that we unless otherwise configured.
DEFAULT_LIMITS = {
    # CPU seconds, defaulting to 1.
    "CPU": 1,
    # Real time, defaulting to 1 second.
    "REALTIME": 1,
    # Total process virutal memory, in bytes, defaulting to unlimited.
    "VMEM": 0,
    # Size of files creatable, in bytes, defaulting to nothing can be written.
    "FSIZE": 0,
    # The number of processes and threads to allow.
    "NPROC": 15,
    # Whether to use a proxy process or not.  None means use an environment
    # variable to decide. NOTE: using a proxy process is NOT THREAD-SAFE, only
    # one thread can use CodeJail at a time if you are using a proxy process.
    "PROXY": None,
}

# Configured resource limits.
# Modified by calling `set_limit`.
LIMITS = DEFAULT_LIMITS.copy()

# Map from limit_overrides_contexts (strings) to dictionaries in the shape of LIMITS.
# Modified by calling `override_limit`.
LIMIT_OVERRIDES = {}


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

        * `"NPROC"`: the maximum number of process or threads creatable by the
            jailed code.  The default is 15.

        * `"PROXY"`: 1 to use a proxy process, 0 to not use one. This isn't
            really a limit, sorry about that.

    Limits are process-wide, and will affect all future calls to jail_code.
    Providing a limit of 0 will disable that limit.

    """
    LIMITS[limit_name] = value


def get_effective_limits(overrides_context=None):
    """
    Calculate the effective limits dictionary.

    Arguments:
        overrides_context (str|None): Identifies which set of overrides to use.
            If None or missing from `LIMIT_OVERRIDES`, then just return `LIMITS` as-is.
    """
    overrides = LIMIT_OVERRIDES.get(overrides_context, {}) if overrides_context else {}
    return {**LIMITS, **overrides}


def override_limit(limit_name, value, limit_overrides_context):
    """
    Override a limit for `jail_code`, but only in the context of `limit_overrides_context`.

    See `set_limit` for the meaning of `limit_name` and `value`.

    All limits may be overriden except PROXY. Having this setting be different between
    executions of code is not supported. If one attempts to override PROXY, the override
    will be ignored and the globally-configured value will be used instead.
    """
    if limit_name == 'PROXY' and LIMITS['PROXY'] != value:
        log.error(
            'Tried to override value of PROXY to %s. '
            'Overriding PROXY on a per-context basis is not permitted. '
            'Will use globally-configured value instead: %s.',
            value,
            LIMITS['PROXY'],
        )
        return
    if limit_overrides_context not in LIMIT_OVERRIDES:
        LIMIT_OVERRIDES[limit_overrides_context] = {}
    LIMIT_OVERRIDES[limit_overrides_context][limit_name] = value


class JailResult:
    """
    A passive object for us to return from jail_code.
    """
    def __init__(self):
        self.stdout = self.stderr = self.status = None


def jail_code(command, code=None, files=None, extra_files=None, argv=None,
              stdin=None, limit_overrides_context=None, slug=None):
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

    `limit_overrides_context` is an optional string to use as a key against the
    configured limit overrides contexts. If omitted or if no such limit override context
    has been configured, then use the default limits.

    `slug` is an arbitrary string, a description that's meaningful to the
    caller, that will be used in log messages.

    Return an object with:

        .stdout: stdout of the program, a string
        .stderr: stderr of the program, a string
        .status: exit status of the process: an int, 0 for success

    """
    # pylint: disable=too-many-statements

    if not is_configured(command):
        raise Exception("jail_code needs to be configured for %r" % command)

    # We make a temp directory to serve as the home of the sandboxed code.
    # It has a writable "tmp" directory within it for temp files.

    with temp_directory() as homedir:

        # Make directory readable by other users ('sandbox' user needs to be
        # able to read it).
        os.chmod(homedir, 0o775)

        # Make a subdir to use for temp files, world-writable so that the
        # sandbox user can write to it.
        tmptmp = os.path.join(homedir, "tmp")
        os.mkdir(tmptmp)
        os.chmod(tmptmp, 0o777)

        argv = argv or []

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
                code_bytes = bytes(code, 'utf8')
                jailed.write(code_bytes)

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
            cmd.extend(['sudo', '-u', user])
            rm_cmd.extend(['sudo', '-u', user])

        # Point TMPDIR at our temp directory.
        cmd.extend(['TMPDIR=tmp'])
        # Start with the command line dictated by "python" or whatever.
        cmd.extend(COMMANDS[command]['cmdline_start'])

        # Add the code-specific command line pieces.
        cmd.extend(argv)

        # Determine effective resource limits.
        effective_limits = get_effective_limits(limit_overrides_context)
        if slug:
            log.info(
                "Preparing to execute jailed code %r "
                "(overrides context = %r, resource limits = %r).",
                slug,
                limit_overrides_context,
                effective_limits,
            )

        # Use the configuration and maybe an environment variable to determine
        # whether to use a proxy process.
        use_proxy = effective_limits["PROXY"]
        if use_proxy is None:
            use_proxy = int(os.environ.get("CODEJAIL_PROXY", "0"))
        if use_proxy:
            run_subprocess_fn = run_subprocess_through_proxy
        else:
            run_subprocess_fn = run_subprocess

        if stdin:
            stdin = bytes(stdin, 'utf-8')

        # Run the subprocess.
        status, stdout, stderr = run_subprocess_fn(
            cmd=cmd, cwd=homedir, env={}, slug=slug,
            stdin=stdin,
            realtime=effective_limits["REALTIME"],
            rlimits=create_rlimits(effective_limits),
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


def create_rlimits(effective_limits):
    """
    Create a list of resource limits for our jailed processes.

    Arguments:
        effective_limits (dict)
    """
    rlimits = []

    # Allow a small number of subprocess and threads.  One limit controls both,
    # and at least OpenBLAS (imported by numpy) requires threads.
    nproc = effective_limits["NPROC"]
    if nproc:
        rlimits.append((resource.RLIMIT_NPROC, (nproc, nproc)))

    # CPU seconds, not wall clock time.
    cpu = effective_limits["CPU"]
    if cpu:
        # Set the soft limit and the hard limit differently.  When the process
        # reaches the soft limit, a SIGXCPU will be sent, which should kill the
        # process.  If you set the soft and hard limits the same, then the hard
        # limit is reached, and a SIGKILL is sent, which is less distinctive.
        rlimits.append((resource.RLIMIT_CPU, (cpu, cpu+1)))

    # Total process virtual memory.
    vmem = effective_limits["VMEM"]
    if vmem:
        rlimits.append((resource.RLIMIT_AS, (vmem, vmem)))

    # Size of written files.  Can be zero (nothing can be written).
    fsize = effective_limits["FSIZE"]
    rlimits.append((resource.RLIMIT_FSIZE, (fsize, fsize)))

    return rlimits
