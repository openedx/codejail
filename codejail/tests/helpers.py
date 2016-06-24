"""
Helper code to facilitate testing
"""

from contextlib import contextmanager
import os.path
import sys
from unittest import TestCase

from codejail import jail
from codejail import languages


SAME = object()


@contextmanager
def override_configuration(command, bin_path=SAME, user=SAME, lang=SAME):
    """
    Context manager to temporarily alter the configuration of a codejail
    command.
    """
    old = jail.COMMANDS.get(command)
    if bin_path is SAME:
        bin_path = old.bin_path
    if user is SAME:
        user = old.user
    if lang is SAME:
        lang = old.lang
    try:
        jail.configure(command, bin_path, user, lang)
        yield
    finally:
        if old is None:
            del jail.COMMANDS[command]
        else:
            jail.COMMANDS[command] = old


class JailMixin(TestCase):
    """
    Mixin to add a default "python" jail environment.

    Can be configured by specifying `CODEJAIL_TEST_VENV` and
    `CODEJAIL_TEST_USER` environment variables.  Defaults to the path of the
    current virtualenv with -sandbox appended and the user named `'sandbox'`.
    """

    _codejail_venv = os.environ.get('CODEJAIL_TEST_VENV')
    _codejail_user = os.environ.get('CODEJAIL_TEST_USER', 'sandbox')

    def setUp(self):
        super(JailMixin, self).setUp()
        if not jail.is_configured("python"):
            if not self._codejail_venv:
                self._codejail_venv = self._autoconfigure_codejail_venv()
            if not self._codejail_user:
                # User explicitly requested no su user via environment variable
                self._codejail_user = None
            bin_path = os.path.join(self._codejail_venv, 'bin/python2')
            jail.configure("python", bin_path, user=self._codejail_user, lang=languages.python2)

    def _autoconfigure_codejail_venv(self):
        """
        For the purposes of tests, look for a sandbox alongside the currently
        running python.
        """
        codejail_venv = '{}-sandbox'.format(sys.prefix)
        if os.path.isdir(codejail_venv):
            return codejail_venv
        else:
            self.fail("No virtualenv found for codejail")


class Python3Mixin(object):
    """
    TestCase Mixin to set up a python3 codejail.  Skips all tests if no python3 executable can be found
    """
    def setUp(self):
        super(Python3Mixin, self).setUp()
        for path in ['/usr/bin/python3', '/usr/local/bin/python3']:
            if os.path.exists(path):
                self.python3_jail = jail.configure('python3', path, lang=languages.python3)
                break
        else:  # nobreak
            self.fail("No Python 3 executable found")
