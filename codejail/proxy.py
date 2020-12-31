"""A proxy subprocess-making process for CodeJail."""

import ast
import logging
import os
import os.path
import subprocess
import sys
import time

import six

from .subproc import run_subprocess

log = logging.getLogger("codejail")

# We use .readline to get data from the pipes between the processes, so we need
# to ensure that a newline does not appear in the data.  We also need a way to
# communicate a few values, and unpack them.  Lastly, we need to be sure we can
# handle binary data.  Serializing with repr() and deserializing the literals
# that result give us all the properties we need.
# Python 3: the outside of subprocess talks in bytes (the pipes from
# subprocess.* are all about bytes). The inside of the Python code it runs
# talks in text (reading from sys.stdin is text, writing to sys.stdout
# expects text).


def serialize_out(val):
    """Send data out of the proxy process. Needs to make unicode."""
    return repr(val)


def serialize_in(val):
    """Send data into the proxy process. Needs to make bytes."""
    return serialize_out(val).encode('utf8')


def deserialize_in(ustr):
    """Get data into the proxy process. Needs to take unicode."""
    return ast.literal_eval(ustr)


def deserialize_out(bstr):
    """Get data from the proxy process. Needs to take bytes."""
    return deserialize_in(bstr.decode('utf8'))


##
# Client code, runs in the parent CodeJail process.
##

def run_subprocess_through_proxy(*args, **kwargs):  # pylint: disable=inconsistent-return-statements
    """
    Works just like :ref:`run_subprocess`, but through the proxy process.

    This will retry a few times if need be.

    """
    last_exception = None
    for _tries in range(3):
        try:
            proxy = get_proxy()

            # Write the args and kwargs to the proxy process.
            proxy_stdin = serialize_in((args, kwargs))
            proxy.stdin.write(proxy_stdin+b"\n")
            proxy.stdin.flush()

            # Read the result from the proxy.  This blocks until the process
            # is done.
            proxy_stdout = proxy.stdout.readline()
            if not proxy_stdout:
                # EOF: the proxy must have died.
                raise Exception("Proxy process died unexpectedly!")
            status, stdout, stderr, log_calls = deserialize_out(proxy_stdout.rstrip())

            # Write all the log messages to the log, and return.
            for level, msg, args in log_calls:
                log.log(level, msg, *args)
            return status, stdout, stderr
        except Exception:  # pylint: disable=broad-except
            log.exception("Proxy process failed")
            # Give the proxy process a chance to die completely if it is dying.
            time.sleep(.001)
            last_exception = sys.exc_info()
            continue

    # If we finished all the tries, then raise the last exception we got.
    if last_exception:
        six.reraise(*last_exception)


# There is one global proxy process.
PROXY_PROCESS = None


def get_proxy():
    # pylint: disable=missing-function-docstring
    global PROXY_PROCESS  # pylint: disable=global-statement

    # If we had a proxy process, but it died, clean up.
    if PROXY_PROCESS is not None:
        status = PROXY_PROCESS.poll()
        if status is not None:
            log.info(
                "CodeJail proxy process (pid %d) ended with status code %d",
                PROXY_PROCESS.pid,
                status
            )
            PROXY_PROCESS = None

    # If we need a proxy, make a proxy.
    if PROXY_PROCESS is None:
        # Start the proxy by invoking proxy_main.py in our root directory.
        root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        proxy_main_py = os.path.join(root, "proxy_main.py")

        # Run proxy_main.py with the same Python that is running us. "-u" makes
        # the stdin and stdout unbuffered. We pass the log level of the
        # "codejail" log so that the proxy can send back an appropriate level
        # of detail in the log messages.
        log_level = log.getEffectiveLevel()
        cmd = [sys.executable, '-u', proxy_main_py, str(log_level)]

        PROXY_PROCESS = subprocess.Popen(
            args=cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            )
        log.info("Started CodeJail proxy process (pid %d)", PROXY_PROCESS.pid)

    return PROXY_PROCESS

##
# Proxy process code
##


class CapturingHandler(logging.Handler):
    """
    A logging Handler that captures all the log calls, for later replay.

    NOTE: this doesn't capture all aspects of the log record.  It only captures
    the log level, the message string, and the arguments.  It does not capture
    the caller, the current exception, the current time, etc.

    """
    # pylint wants us to override emit().
    # pylint: disable=abstract-method

    def __init__(self):
        super().__init__()
        self.log_calls = []

    def createLock(self):
        self.lock = None

    def handle(self, record):
        self.log_calls.append((record.levelno, record.msg, record.args))

    def get_log_calls(self):
        # pylint: disable=missing-function-docstring
        retval = self.log_calls
        self.log_calls = []
        return retval


def proxy_main(argv):
    """
    The main program for the proxy process.

    It does this:

        * Reads a line from stdin with the repr of a tuple: (args, kwargs)
        * Calls :ref:`run_subprocess` with *args, **kwargs
        * Writes one line to stdout: the repr of the return value from
          `run_subprocess` and the log calls made:
          (status, stdout, stderr, log_calls) .

    The process ends when its stdin is closed.

    `argv` is the argument list of the process, from sys.argv. The only
    argument is the logging level for the "codejail" log in the parent
    process. Since we tunnel our logging back to the parent, we don't want to
    send everything, just the records that the parent will actually log.

    """
    # We don't want to see any noise on stderr.
    sys.stderr = open(os.devnull, "w")

    # Capture all logging messages.
    capture_log = CapturingHandler()
    log.addHandler(capture_log)
    log.setLevel(int(argv[1]) or logging.DEBUG)

    log.debug("Starting proxy process")

    try:
        while True:
            stdin = sys.stdin.readline()
            log.debug("proxy stdin: %r", stdin)
            if not stdin:
                break
            args, kwargs = deserialize_in(stdin.rstrip())
            status, stdout, stderr = run_subprocess(*args, **kwargs)
            log.debug(
                "run_subprocess result: status=%r\nstdout=%r\nstderr=%r",
                status, stdout, stderr,
            )
            log_calls = capture_log.get_log_calls()
            stdout = serialize_out((status, stdout, stderr, log_calls))
            sys.stdout.write(stdout+"\n")
            sys.stdout.flush()
    except Exception:  # pylint: disable=broad-except
        # Note that this log message will not get back to the parent, because
        # we are dying and not communicating back to the parent. This will be
        # useful only if you add another handler at the top of this function.
        log.exception("Proxy dying due to exception")

    log.debug("Exiting proxy process")
