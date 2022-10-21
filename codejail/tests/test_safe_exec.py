"""Test safe_exec.py"""

import os.path
import textwrap
import zipfile
from io import BytesIO
from unittest import SkipTest, TestCase

from codejail import safe_exec
from codejail.jail_code import set_limit


class TestJsonSafe(TestCase):
    # pylint: disable=missing-class-docstring
    def test_decodable_dict(self):
        test_dict = {1: bytes('a', 'utf8'), 2: 'b', 3: {1: bytes('b', 'utf8'), 2: (1, bytes('a', 'utf8'))}}
        cleaned_dict = safe_exec.json_safe(test_dict)

        self.assertDictEqual(cleaned_dict, {'1': 'a', '2': 'b', '3': {'1': 'b', '2': [1, 'a']}})

    def test_bad_key(self):
        test_dict = {b'\x99bad_key': b'good_value', 'a': 'b'}
        cleaned_dict = safe_exec.json_safe(test_dict)

        self.assertDictEqual(cleaned_dict, {'a': 'b'})

    def test_bad_value(self):
        test_dict = {b'good_key': b'\x99bad_value', 'a': 'b'}
        cleaned_dict = safe_exec.json_safe(test_dict)

        self.assertDictEqual(cleaned_dict, {'a': 'b'})


class SafeExecTests(TestCase):
    """The tests for `safe_exec`, to be mixed into specific test classes."""

    # SafeExecTests is a TestCase so pylint understands the methods it can
    # call, but it's abstract, so stop pytest from running the tests.
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

    def test_complex_globals(self):
        globs = {}
        self.safe_exec(
            textwrap.dedent("""\
            from builtins import bytes
            test_dict = {1: bytes('a', 'utf8'), 2: 'b', 3: {1: bytes('b', 'utf8'), 2: (1, bytes('a', 'utf8'))}}
            bad_val = b'\\x99'
            """),
            globs
        )
        self.assertDictEqual(globs['test_dict'], {'1': 'a', '2': 'b', '3': {'1': 'b', '2': [1, 'a']}})
        assert 'bad_val' not in globs

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
        self.safe_exec("from __future__ import print_function; a = 17; print('hi!')", globs)
        self.assertEqual(globs['a'], 17)

    def test_importing_lots_of_crap(self):
        set_limit('REALTIME', 10)
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
        self.assertRegex(
            msg,
            r"ValueError: That\\?'s not how you pour soup!"
        )

    def test_extra_files(self):
        globs = {}
        extras = [
            ("extra.txt", b"I'm extra!\n"),
            ("also.dat", b"\x01\xff\x02\xfe"),
        ]
        self.safe_exec(textwrap.dedent("""\
            import six
            import io
            with io.open("extra.txt", 'r') as f:
                extra = f.read()
            with open("also.dat", 'rb') as f:
                if six.PY2:
                    also = f.read().encode("hex")
                else:
                    also = f.read().hex()
            """), globs, extra_files=extras)

        self.assertEqual(globs['extra'], "I'm extra!\n")
        self.assertEqual(globs['also'], "01ff02fe")

    def test_extra_files_as_pythonpath_zipfile(self):
        zipstring = BytesIO()
        zipf = zipfile.ZipFile(zipstring, "w")
        zipf.writestr("zipped_module1.py", bytes(textwrap.dedent("""\
            def func1(x):
                return 2*x + 3
            """), 'utf-8'))
        zipf.writestr("zipped_module2.py", bytes(textwrap.dedent("""\
            def func2(s):
                return "X" + s + s + "X"
            """), 'utf-8'))
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


class TestSafeExec(SafeExecTests, TestCase):
    """Run SafeExecTests, with the real safe_exec."""

    __test__ = True

    def safe_exec(self, *args, **kwargs):
        safe_exec.safe_exec(*args, **kwargs)


class TestNotSafeExec(SafeExecTests, TestCase):
    """Run SafeExecTests, with not_safe_exec."""

    __test__ = True

    def setUp(self):
        # If safe_exec is actually an alias to not_safe_exec, then there's no
        # point running these tests.
        if safe_exec.UNSAFE:                    # pragma: no cover
            raise SkipTest

    def safe_exec(self, *args, **kwargs):
        safe_exec.not_safe_exec(*args, **kwargs)
