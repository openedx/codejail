"""Test jail_code.py"""

import logging
import os
import os.path
import shutil
import signal
import tempfile
import textwrap
import time
from unittest import SkipTest, TestCase, mock

from codejail import proxy
from codejail.jail_code import LIMITS, is_configured, jail_code, set_limit


def jailpy(code=None, *args, **kwargs):  # pylint: disable=keyword-arg-before-vararg
    """Run `jail_code` on Python."""
    if code:
        code = textwrap.dedent(code)
    return jail_code("python", code, *args, **kwargs)


def file_here(fname):
    """Return the full path to a file alongside this code."""
    return os.path.join(os.path.dirname(__file__), fname)


def text_of_logs(mock_calls):
    """
    After capturing log messages, use this to get the full text.

    Like this::

        @mock.patch("codejail.subproc.log._log")
        def test_with_log_messages(self, log_log):
            do_something_that_makes_log_messages()
            log_text = text_of_logs(log_log.mock_calls)
            self.assertRegex(log_text, r"INFO: Something cool happened")

    """
    text = ""
    for call in mock_calls:
        level, msg, args = call[1]
        msg_formatted = msg % args
        text += "%s: %s\n" % (logging.getLevelName(level), msg_formatted)
    return text


class JailCodeHelpersMixin:
    """Assert helpers for jail_code tests."""
    def setUp(self):
        super().setUp()
        if not is_configured("python"):
            raise SkipTest

    def assertResultOk(self, res):
        """Assert that `res` exited well (0), and had no stderr output."""
        if res.stderr:
            print("---- stderr:\n%s" % res.stderr)
        self.assertEqual(res.stderr, b"")        # pylint: disable=E1101
        self.assertEqual(res.status, 0)         # pylint: disable=E1101


class TestFeatures(JailCodeHelpersMixin, TestCase):
    """Test features of how `jail_code` runs Python."""

    def test_hello_world(self):
        res = jailpy(code="""
            from __future__ import print_function; print('Hello, world!')
        """)
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b'Hello, world!\n')

    def test_argv(self):
        set_limit('REALTIME', 2)
        res = jailpy(
            code="""
                from __future__ import print_function
                import sys
                print(':'.join(sys.argv[1:]))
            """,
            argv=["Hello", "world", "-x"],
            slug="a/useful/slug",
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"Hello:world:-x\n")

    def test_ends_with_exception(self):
        res = jailpy(code="""raise Exception('FAIL')""")
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, b"")
        self.assertEqual(res.stderr, bytes(textwrap.dedent("""\
            Traceback (most recent call last):
              File "jailed_code", line 1, in <module>
                raise Exception('FAIL')
            Exception: FAIL
            """), 'utf-8'))

    def test_stdin_is_provided(self):
        res = jailpy(
            code="""
                from __future__ import print_function
                import json, sys
                print(sum(json.load(sys.stdin)))
            """,
            stdin="[1, 2.5, 33]"
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"36.5\n")

    def test_stdin_can_be_large_and_binary(self):
        res = jailpy(
            code="""
                from __future__ import print_function
                import sys
                print(sum(ord(c) for c in sys.stdin.read()))
            """,
            stdin="".join(chr(i) for i in range(256))*10000,
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"326400000\n")

    def test_stdout_can_be_large_and_binary(self):
        res = jailpy(
            code="""
                import sys
                sys.stdout.write("".join(chr(i) for i in range(256))*10000)
            """
        )
        self.assertResultOk(res)
        self.assertEqual(
            res.stdout,
            bytes("".join(chr(i) for i in range(256))*10000, 'utf-8')
        )

    def test_stderr_can_be_large_and_binary(self):
        res = jailpy(
            code="""
                import sys
                sys.stderr.write("".join(chr(i) for i in range(256))*10000)
                sys.stdout.write("OK!")
            """
        )
        self.assertEqual(res.status, 0)
        self.assertEqual(res.stdout, b"OK!")
        self.assertEqual(
            res.stderr,
            bytes("".join(chr(i) for i in range(256))*10000, 'utf-8')
        )

    def test_files_are_copied(self):
        res = jailpy(
            code="""
                from __future__ import print_function
                print('Look:', open('hello.txt').read())
            """,
            files=[file_here("hello.txt")]
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b'Look: Hello there.\n\n')

    def test_directories_are_copied(self):
        res = jailpy(
            code="""\
                from __future__ import print_function
                import os
                res = []
                for path, dirs, files in os.walk("."):
                    res.append((path, sorted(dirs), sorted(files)))
                for row in sorted(res):
                    print(row)
                """,
            files=[file_here("hello.txt"), file_here("pylib")]
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, bytes(textwrap.dedent("""\
            ('.', ['pylib', 'tmp'], ['hello.txt', 'jailed_code'])
            ('./pylib', [], ['module.py'])
            ('./tmp', [], [])
            """), 'utf-8'))

    def test_executing_a_copied_file(self):
        res = jailpy(
            files=[file_here("doit.py")],
            argv=["doit.py", "1", "2", "3"]
        )
        self.assertResultOk(res)
        self.assertEqual(
            res.stdout,
            b"This is doit.py!\nMy args are ['doit.py', '1', '2', '3']\n"
        )

    def test_executing_extra_files(self):
        res = jailpy(
            extra_files=[
                ("run.py", bytes(textwrap.dedent("""\
                            from __future__ import print_function
                            import os
                            print(sorted(os.listdir('.')))
                            print(open('also.txt', 'rb').read())
                            """), 'utf8')),
                # This file has some non-ASCII, non-UTF8, just binary data.
                ("also.txt", b"also here\xff\x00\xab"),
            ],
            argv=["run.py"],
        )
        self.assertResultOk(res)
        self.assertEqual(
            res.stdout,
            b"['also.txt', 'run.py', 'tmp']\nb'also here\\xff\\x00\\xab'\n"
        )

    def test_we_can_remove_tmp_files(self):
        # This test is meant to create a tmp file in a temp folder as the
        # sandbox user that the application user can't delete.
        # This is because the sandbox caller has the ability to delete
        # any toplevel files in the tmp directory but not the abilty
        # to delete files in folders that are only owned by the sandbox
        # user, such as the temp directory created below.
        set_limit('FSIZE', 1000)
        res = jailpy(
            code="""\
                from __future__ import print_function
                import os, shutil, tempfile
                temp_dir = tempfile.mkdtemp()
                with open("{}/myfile.txt".format(temp_dir), "w") as f:
                    f.write("This is my file!")
                shutil.move("{}/myfile.txt".format(temp_dir),
                            "{}/overthere.txt".format(temp_dir))
                with open("{}/overthere.txt".format(temp_dir)) as f:
                    print(f.read())
                with open("{}/.myfile.txt".format(temp_dir), "w") as f:
                    f.write("This is my dot file!")
                # Now make it secret!
                os.chmod("{}/overthere.txt".format(temp_dir), 0)
                print(sorted(os.listdir(temp_dir)))
            """)
        self.assertResultOk(res)
        self.assertEqual(
            res.stdout,
            b"This is my file!\n['.myfile.txt', 'overthere.txt']\n"
        )

    @mock.patch("codejail.subproc.log._log")
    def test_slugs_get_logged(self, log_log):
        jailpy(
            code="""
                from __future__ import print_function; print('Hello, world!')
            """,
            slug="HELLO"
        )
        log_text = text_of_logs(log_log.mock_calls)
        self.assertRegex(log_text, r"INFO: Executed jailed code HELLO in .*, with PID .*")


class TestLimits(JailCodeHelpersMixin, TestCase):
    """Tests of the resource limits, and changing them."""

    def setUp(self):
        super().setUp()
        self.old_limits = dict(LIMITS)

    def tearDown(self):
        for name, value in self.old_limits.items():
            set_limit(name, value)
        super().tearDown()

    def test_cant_use_too_much_memory(self):
        # This will fail after setting the limit to 30Mb.
        set_limit('VMEM', 80000000)
        res = jailpy(
            code="""
                from __future__ import print_function
                print(len(bytearray(100000000)))
            """
        )
        self.assertEqual(res.stdout, b"")
        self.assertIn(b"MemoryError", res.stderr)
        self.assertEqual(res.status, 1)

    def test_changing_vmem_limit(self):
        # Up the limit, it will succeed.
        set_limit('VMEM', 160000000)
        res = jailpy(
            code="""
                from __future__ import print_function
                print(len(bytearray(100000000)))
            """
        )
        self.assertEqual(res.stderr, b"")
        self.assertEqual(res.stdout, b"100000000\n")
        self.assertEqual(res.status, 0)

    def test_disabling_vmem_limit(self):
        # Disable the limit, it will succeed.
        set_limit('VMEM', 0)
        res = jailpy(
            code="""
                from __future__ import print_function
                print(len(bytearray(50000000)))
            """
        )
        self.assertEqual(res.stderr, b"")
        self.assertEqual(res.stdout, b"50000000\n")
        self.assertEqual(res.status, 0)

    def test_cant_use_too_much_cpu(self):
        set_limit('CPU', 1)
        set_limit('REALTIME', 10)
        res = jailpy(
            code="""
                from __future__ import print_function
                from six.moves import range
                print(sum(range(2**31-1)))
            """
        )
        self.assertEqual(res.stdout, b"")
        self.assertEqual(res.stderr, b"")
        self.assertEqual(res.status, -signal.SIGXCPU)    # 137

    @mock.patch("codejail.subproc.log._log")
    def test_cant_use_too_much_time(self, log_log):
        # Default time limit is 1 second.  Sleep for 1.5 seconds.
        set_limit('CPU', 100)
        set_limit('REALTIME', 1)
        res = jailpy(
            code="""
                from __future__ import print_function
                import time
                time.sleep(1.5)
                print('Done!')
            """
        )
        self.assertEqual(res.stdout, b"")
        self.assertEqual(res.status, -signal.SIGKILL)       # -9

        # Make sure we log that we are killing the process.
        log_text = text_of_logs(log_log.mock_calls)
        self.assertRegex(log_text, r"WARNING: Killing process \d+")

    def test_changing_realtime_limit(self):
        # Change time limit to 2 seconds, sleeping for 1.5 will be fine.
        set_limit('REALTIME', 2)
        res = jailpy(
            code="""
                from __future__ import print_function
                import time
                time.sleep(1.5)
                print('Done!')
            """
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"Done!\n")

    def test_disabling_realtime_limit(self):
        # Disable the time limit, sleeping for 1.5 will be fine.
        set_limit('REALTIME', 0)
        res = jailpy(
            code="""
                from __future__ import print_function
                import time
                time.sleep(1.5)
                print('Done!')
            """
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"Done!\n")

    def test_cant_write_files(self):
        res = jailpy(code="""\
                from __future__ import print_function
                print("Trying")
                with open("mydata.txt", "w") as f:
                    f.write("hello")
                with open("mydata.txt") as f2:
                    print("Got this:", f2.read())
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, b"Trying\n")
        self.assertIn(b"ermission denied", res.stderr)

    def test_can_write_temp_files(self):
        set_limit('FSIZE', 1000)
        res = jailpy(code="""\
                from __future__ import print_function
                import os, tempfile
                print("Trying mkstemp")
                f, path = tempfile.mkstemp()
                os.close(f)
                with open(path, "w") as f1:
                    f1.write("hello")
                with open(path) as f2:
                    print("Got this:", f2.read())
                """)
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"Trying mkstemp\nGot this: hello\n")

    def test_cant_write_large_temp_files(self):
        set_limit('FSIZE', 1000)
        res = jailpy(code="""\
                from __future__ import print_function
                import os, tempfile
                from six.moves import range
                print("Trying mkstemp")
                f, path = tempfile.mkstemp()
                os.close(f)
                with open(path, "w") as f1:
                    try:
                        f1.write(".".join("%05d" % i for i in range(1000)))
                    except IOError as e:
                        print("Expected exception: %s" % e)
                    else:
                        with open(path) as f2:
                            print("Got this:", f2.read())
                """)
        self.assertIn(b"OSError", res.stderr)
        self.assertIn(b"File too large", res.stderr)

    def test_cant_write_many_small_temp_files(self):
        # We would like this to fail, but there's nothing that checks total
        # file size written, so the sandbox does not prevent it yet.
        raise SkipTest("There's nothing checking total file size yet.")
        # pylint: disable=unreachable
        set_limit('FSIZE', 1000)
        res = jailpy(code="""\
                from __future__ import print_function
                import os, tempfile
                print("Trying mkstemp 250")
                for i in range(250):
                    f, path = tempfile.mkstemp()
                    os.close(f)
                    with open(path, "w") as f1:
                        f1.write("hello")
                    with open(path) as f2:
                        assert f2.read() == "hello"
                print("Finished 250")
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, b"Trying mkstemp 250\n")
        self.assertIn(b"IOError", res.stderr)

    def test_cant_use_network(self):
        res = jailpy(code="""\
                from __future__ import print_function
                try:
                    from urllib import urlopen
                except ImportError:
                    from urllib.request import urlopen
                print("Reading google")
                u = urlopen("http://google.com")
                google = u.read()
                print(len(google))
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, b"Reading google\n")
        self.assertIn(b"URLError", res.stderr)

    def test_cant_use_raw_network(self):
        res = jailpy(code="""\
                from __future__ import print_function
                try:
                    from urllib import urlopen
                except ImportError:
                    from urllib.request import urlopen
                print("Reading example.com")
                u = urlopen("http://93.184.216.119")
                example = u.read()
                print(len(example))
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, b"Reading example.com\n")
        self.assertIn(b"URLError", res.stderr)

    def test_cant_fork(self):
        set_limit('NPROC', 1)
        res = jailpy(
            code="""\
                from __future__ import print_function
                import os
                print("Forking")
                child_ppid = os.fork()
                print(child_ppid)
            """
        )
        # stdout should only contain the first print statement
        self.assertEqual(res.stdout, b"Forking\n")
        self.assertIn(b'BlockingIOError', res.stderr)
        self.assertNotEqual(res.status, 0)

    def test_cant_see_environment_variables(self):
        os.environ['HONEY_BOO_BOO'] = 'Look!'
        res = jailpy(
            code="""\
                from __future__ import print_function
                import os
                for name, value in os.environ.items():
                    print("%s: %r" % (name, value))
            """
        )
        self.assertResultOk(res)
        self.assertNotIn(b"HONEY", res.stdout)

    def test_reading_dev_random(self):
        # We can read 10 bytes just fine.
        res = jailpy(
            code="""
                from __future__ import print_function
                x = open('/dev/urandom', 'rb').read(10)
                print(len(x))
            """
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"10\n")

        # If we try to read all of it, we'll be killed by the real-time limit.
        res = jailpy(
            code="""
                from __future__ import print_function
                x = open('/dev/urandom', 'rb').read()
                print('Done!')
            """
        )
        self.assertNotEqual(res.status, 0)


class TestSymlinks(JailCodeHelpersMixin, TestCase):
    """Testing symlink behavior."""

    def setUp(self):
        # Make a temp dir, and arrange to have it removed when done.
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)

        # Make a directory that won't be copied into the sandbox.
        self.not_copied = os.path.join(tmp_dir, "not_copied")
        os.mkdir(self.not_copied)
        self.linked_txt = os.path.join(self.not_copied, "linked.txt")
        with open(self.linked_txt, "w") as linked:
            linked.write("Hi!")

        # Make a directory that will be copied into the sandbox, with a
        # symlink to a file we aren't copying in.
        self.copied = os.path.join(tmp_dir, "copied")
        os.mkdir(self.copied)
        self.here_txt = os.path.join(self.copied, "here.txt")
        with open(self.here_txt, "w") as here:
            here.write("012345")
        self.link_txt = os.path.join(self.copied, "link.txt")
        os.symlink(self.linked_txt, self.link_txt)
        self.herelink_txt = os.path.join(self.copied, "herelink.txt")
        os.symlink("here.txt", self.herelink_txt)

    def test_symlinks_in_directories_wont_copy_data(self):
        # Run some code in the sandbox, with a copied directory containing
        # the symlink.
        res = jailpy(
            code="""\
                from __future__ import print_function
                print(open('copied/here.txt').read())        # can read
                print(open('copied/herelink.txt').read())    # can read
                print(open('copied/link.txt').read())        # can't read
                """,
            files=[self.copied],
        )
        self.assertEqual(res.stdout, b"012345\n012345\n")
        self.assertIn(b"ermission denied", res.stderr)

    def test_symlinks_wont_copy_data(self):
        # Run some code in the sandbox, with a copied file which is a symlink.
        res = jailpy(
            code="""\
                from __future__ import print_function
                print(open('here.txt').read())       # can read
                print(open('herelink.txt').read())   # can read
                print(open('link.txt').read())       # can't read
                """,
            files=[self.here_txt, self.herelink_txt, self.link_txt],
        )
        self.assertEqual(res.stdout, b"012345\n012345\n")
        self.assertIn(b"ermission denied", res.stderr)


class TestMalware(JailCodeHelpersMixin, TestCase):
    """Tests that attempt actual malware against the interpreter or system."""

    def test_crash_cpython(self):
        # http://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html

        # the `new` module has been removed in Python 3, and replaced with the
        # `types` module. This test code needs to be refactored to support
        # both.
        raise SkipTest('Not supported in Python 3 yet')
        # pylint: disable=unreachable
        res = jailpy(code="""\
            from __future__ import print_function
            import new, sys
            bad_code = new.code(0,0,0,0,"KABOOM",(),(),(),"","",0,"")
            crash_me = new.function(bad_code, {})
            print("Here we go...")
            sys.stdout.flush()
            crash_me()
            print("The afterlife!")
            """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stderr, b"")
        self.assertEqual(res.stdout, b"Here we go...\n")

    def test_read_etc_passwd(self):
        res = jailpy(code="""\
            from __future__ import print_function
            bytes = len(open('/etc/passwd').read())
            print('Gotcha', bytes)
            """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, b"")
        self.assertIn(b"ermission denied", res.stderr)

    def test_find_other_sandboxes(self):
        res = jailpy(code="""
            from __future__ import print_function
            import os
            places = [
                "..", "/tmp", "/", "/home", "/etc", "/var"
                ]
            for place in places:
                try:
                    files = os.listdir(place)
                except Exception:
                    # darn
                    pass
                else:
                    print("Files in %r: %r" % (place, files))
            print("Done.")
            """)
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b"Done.\n")


class TestProxyProcess(JailCodeHelpersMixin, TestCase):
    """Tests of the proxy process."""

    def setUp(self):
        # During testing, the proxy is used if the environment variable is set.
        # Skip these tests if we aren't using the proxy.
        if not int(os.environ.get("CODEJAIL_PROXY", "0")):
            raise SkipTest()

        super().setUp()

    def run_ok(self):
        """Run some code to see that it works."""
        num = int(time.time()*100000)
        res = jailpy(code="from __future__ import print_function; print('Look: %d')" % num)
        self.assertResultOk(res)
        self.assertEqual(res.stdout, b'Look: %d\n' % num)

    def test_proxy_is_persistent(self):
        # Running code twice, you use the same proxy process.
        self.run_ok()
        pid = proxy.PROXY_PROCESS.pid
        self.run_ok()
        self.assertEqual(proxy.PROXY_PROCESS.pid, pid)

    def test_crash_proxy(self):
        # We can run some code.
        self.run_ok()
        pids = set()
        pids.add(proxy.PROXY_PROCESS.pid)

        # Run this a number of times, to try to catch some cases.
        for i in range(10):
            # The proxy process dies unexpectedly!
            proxy.PROXY_PROCESS.kill()

            # The behavior is slightly different if we rush immediately to the
            # next run, or if we wait a bit to let the process truly die, so
            # alternate whether we wait or not.
            if i % 2:
                time.sleep(.1)

            # Code can still run.
            self.run_ok()

            # We should have a new proxy process each time.
            pid = proxy.PROXY_PROCESS.pid
            self.assertNotIn(pid, pids)
            pids.add(pid)
