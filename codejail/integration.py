"""
Integrate with application settings files.
"""

from __future__ import absolute_import

import os.path

from . import jail
from . import limits
from .util import sibling_sandbox_venv


def configure_from_settings(settings):
    """

    Configure a set of code jails and limits from a django settings file of the
    form:

        import codejail.languages

        CODE_JAIL = {
            'jails': [
                {
                    'command': 'python',
                    'bin_path': '/edx/app/edxapp/venvs/edxapp-sandbox/bin/python',
                    'user': 'sandbox',
                    'lang': codejail.languages.python2,
                },
                {
                    'command': 'jail3',
                    'bin_path': '/edx/app/edxapp/venvs/edxapp-sandbox3/bin/python3',
                    'user': 'sandbox',
                    'lang': codejail.languages.python3,
                },
            ],
            'limits': {
                'CPU': 1,
            }
        }

    Each item in `CODE_JAIL['jails']` is a dict of kwargs for a `codejail.jail.Jail` object.
    """
    if 'jails' in settings.CODE_JAIL:
        for jail_config in settings.CODE_JAIL['jails']:
            jail.configure(**jail_config)
        requested_limits = settings.CODE_JAIL.get('limits', {})
        for name, value in requested_limits.items():
            limits.set_limit(name, value)
    else:
        legacy_configure_from_settings(settings)


def legacy_configure_from_settings(settings):
    """
    Configure a "python" code jail and limits from a django settings file where
    the settings look like this:

        CODE_JAIL = {
            "python_bin": "/edx/app/edxapp/venvs/edxapp-sandbox/bin/python",
            "user": "sandbox",
            "limits": {"CPU": 1},
        }

    The virtualenv used depends on the 'python_bin' setting:

    * If 'python_bin' is specified, it is the sandbox virtualenv to use.

    * If 'python_bin' is specified as None, then code will run unsafely.

    * If 'python_bin' isn't specified, then a virtualenv alongside the current
      one, with a suffix of '-sandbox' will be used.

    """
    python_bin = None
    if 'python_bin' in settings.CODE_JAIL:
        python_bin = settings.CODE_JAIL['python_bin']
    else:
        venv = sibling_sandbox_venv()
        if venv:
            python_bin = os.path.join(venv, "bin/python")

    if python_bin:
        user = settings.CODE_JAIL['user']
        jail.configure("python", python_bin, user=user)

    requested_limits = settings.CODE_JAIL.get('limits', {})
    for name, value in requested_limits.items():
        limits.set_limit(name, value)
