"""Test safe_exec.py"""

from cStringIO import StringIO
import os.path
import textwrap
import unittest
import zipfile

from mock import patch

from codejail.exceptions import JailError, SafeExecException
from codejail.jail import get_codejail
from codejail import languages
from codejail import safe_exec
from . import helpers


class SafeExecTests(helpers.JailMixin, unittest.TestCase):
    """The tests for `safe_exec`, to be mixed into specific test classes."""

    # SafeExecTests is a TestCase so pylint understands the methods it can
    # call, but it's abstract, so stop nose from running the tests.
    __test__ = False

    def safe_exec(self, *args, **kwargs):
        """The function under test.

        This class will be mixed into subclasses that implement `safe_exec` to
        give the tests something to test.

        """
        raise NotImplementedError       # pragma: no cover

    def test_set_values(self):
        globs = {}
        self.safe_exec("a = 17", globs)
        self.assertEqual(globs['a'], 17)

    def test_files_are_copied(self):
        globs = {}
        self.safe_exec(
            "a = 'Look: ' + open('hello.txt').read()", globs,
            files=[os.path.dirname(__file__) + "/hello.txt"]
        )
        self.assertEqual(globs['a'], 'Look: Hello there.\n')

    def test_python_path(self):
        globs = {}
        self.safe_exec(
            "import module; a = module.const", globs,
            python_path=[os.path.dirname(__file__) + "/pylib"]
        )
        self.assertEqual(globs['a'], 42)

    def test_functions_calling_each_other(self):
        globs = {}
        self.safe_exec(textwrap.dedent("""\
            def f():
                return 1723
            def g():
                return f()
            x = g()
            """), globs)
        self.assertEqual(globs['x'], 1723)

    def test_printing_stuff_when_you_shouldnt(self):
        globs = {}
        self.safe_exec("a = 17; print 'hi!'", globs)
        self.assertEqual(globs['a'], 17)

    def test_importing_lots_of_crap(self):
        globs = {}
        self.safe_exec(textwrap.dedent("""\
            from numpy import *
            a = 1723
            """), globs)
        self.assertEqual(globs['a'], 1723)

    def test_raising_exceptions(self):
        globs = {}
        with self.assertRaises(safe_exec.SafeExecException) as what_happened:
            self.safe_exec(textwrap.dedent("""\
                raise ValueError("That's not how you pour soup!")
                """), globs)
        msg = str(what_happened.exception)
        # The result may be repr'd or not, so the backslash needs to be
        # optional in this match.
        self.assertRegexpMatches(
            msg,
            r"ValueError: That\\?'s not how you pour soup!"
        )

    def test_extra_files(self):
        globs = {}
        extras = [
            ("extra.txt", "I'm extra!\n"),
            ("also.dat", "\x01\xff\x02\xfe"),
        ]
        self.safe_exec(textwrap.dedent("""\
            with open("extra.txt") as f:
                extra = f.read()
            with open("also.dat") as f:
                also = f.read().encode("hex")
            """), globs, extra_files=extras)
        self.assertEqual(globs['extra'], "I'm extra!\n")
        self.assertEqual(globs['also'], "01ff02fe")

    def test_extra_files_as_pythonpath_zipfile(self):
        zipstring = StringIO()
        zipf = zipfile.ZipFile(zipstring, "w")
        zipf.writestr("zipped_module1.py", textwrap.dedent("""\
            def func1(x):
                return 2*x + 3
            """))
        zipf.writestr("zipped_module2.py", textwrap.dedent("""\
            def func2(s):
                return "X" + s + s + "X"
            """))
        zipf.close()
        globs = {}
        extras = [("code.zip", zipstring.getvalue())]
        self.safe_exec(textwrap.dedent("""\
            import zipped_module1 as zm1
            import zipped_module2 as zm2
            a = zm1.func1(10)
            b = zm2.func2("hello")
            """), globs, python_path=["code.zip"], extra_files=extras)

        self.assertEqual(globs['a'], 23)
        self.assertEqual(globs['b'], "XhellohelloX")


class TestSafeExec(SafeExecTests, unittest.TestCase):
    """Run SafeExecTests, with the real safe_exec."""

    __test__ = True

    def safe_exec(self, *args, **kwargs):
        safe_exec.safe_exec(*args, **kwargs)

    @patch('codejail.safe_exec.not_safe_exec')
    def test_not_safe_exec_not_called(self, mock_not_safe_exec):
        # Make sure safe_exec doesn't alias not_safe_exec
        # Otherwise, our test suite won't be useful
        self.safe_exec('x = 1', {})
        self.assertFalse(mock_not_safe_exec.called)


class TestNotSafeExec(SafeExecTests, unittest.TestCase):
    """Run SafeExecTests, with not_safe_exec."""

    __test__ = True

    def safe_exec(self, *args, **kwargs):
        safe_exec.not_safe_exec(*args, **kwargs)


class TestPython3SafeExec(helpers.Python3Mixin, unittest.TestCase):
    """
    Test that python 3 codejails can run safe_exec
    """

    def test_safe_exec_basic(self):
        globals_dict = {
            'starter': 8
        }
        self.python3_jail.safe_exec('happy_result = str(starter) + "-)"', globals_dict)
        self.assertEqual(globals_dict, {'starter': 8, 'happy_result': '8-)'})

    def test_safe_exec_error(self):
        with self.assertRaises(SafeExecException) as exc:
            self.python3_jail.safe_exec('"foo".decode("utf-8")', {})
        self.assertIn('object has no attribute', exc.exception.message)

    def test_safe_exec_unconfigured(self):
        with helpers.override_configuration('python3', lang=languages.other):
            jail = get_codejail('python3')
            with self.assertRaises(JailError):
                jail.safe_exec('print("hello")', {})
