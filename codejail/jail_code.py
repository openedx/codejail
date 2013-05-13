"""Run code in a jail."""

import logging
import os
import os.path
import resource
import shutil
import subprocess
import sys
import threading
import time

from .util import temp_directory

log = logging.getLogger(__name__)

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
    cmd_argv = []

    if user:
        # Run as the specified user
        cmd_argv.extend(['sudo', '-u', user])

    # Run the command!
    cmd_argv.append(bin_path)

    # Command-specific arguments
    if command == "python":
        cmd_argv.append('-E')

    COMMANDS[command] = cmd_argv


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
    # Total process virutal memory, in bytes, defaulting to 30 Mb.
    "VMEM": 30000000,
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

        * `"VMEM"`: the total virtual memory available to the jailed code, in
            bytes.  The default is 30 Mb.

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


def jail_code(command, code=None, files=None, argv=None, stdin=None):
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
    the code access to the files.

    `argv` is the command-line arguments to supply.

    Return an object with:

        .stdout: stdout of the program, a string
        .stderr: stderr of the program, a string
        .status: exit status of the process: an int, 0 for success

    """
    if not is_configured(command):
        raise Exception("jail_code needs to be configured for %r" % command)

    with temp_directory() as tmpdir:

        log.debug("Executing jailed code: %r", code)

        argv = argv or []

        # All the supporting files are copied into our directory.
        for filename in files or ():
            if os.path.isfile(filename):
                shutil.copy(filename, tmpdir)
            else:
                dest = os.path.join(tmpdir, os.path.basename(filename))
                shutil.copytree(filename, dest)

        # Create the main file.
        if code:
            with open(os.path.join(tmpdir, "jailed_code"), "w") as jailed:
                jailed.write(code)

            argv = ["jailed_code"] + argv

        cmd = COMMANDS[command] + argv

        subproc = subprocess.Popen(
            cmd, preexec_fn=set_process_limits, cwd=tmpdir, env={},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        # TODO: time limiting.  The ProcessKillerThread doesn't work yet, so
        # don't launch it.
        #   killer = ProcessKillerThread(subproc)
        #   killer.start()

        result = JailResult()
        result.stdout, result.stderr = subproc.communicate(stdin)
        result.status = subproc.returncode

    return result


def set_process_limits():       # pragma: no cover
    """
    Set limits on this processs, to be used first in a child process.
    """
    # No subprocesses or files
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))

    # CPU seconds, not wall clock time.
    cpu = LIMITS["CPU"]
    if cpu:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))

    # Total process virtual memory.
    vmem = LIMITS["VMEM"]
    if vmem:
        resource.setrlimit(resource.RLIMIT_AS, (vmem, vmem))


class ProcessKillerThread(threading.Thread):
    """
    A thread to kill a process after a given time limit.
    """
    def __init__(self, subproc, limit=1):
        super(ProcessKillerThread, self).__init__()
        self.subproc = subproc
        self.limit = limit

    def run(self):
        start = time.time()
        while (time.time() - start) < self.limit:
            time.sleep(.1)
            if self.subproc.poll() is not None:
                # Process ended, no need for us any more.
                return

        if self.subproc.poll() is None:
            # Can't use subproc.kill because we launched the subproc with sudo.
            killargs = ["sudo", "kill", "-9", str(self.subproc.pid)]
            kill = subprocess.Popen(
                killargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            out, err = kill.communicate()
            # TODO: This doesn't actually kill the process.... :(
