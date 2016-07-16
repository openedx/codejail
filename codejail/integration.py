"""
Integrate with application settings files.
"""

from __future__ import absolute_import
from . import jail
from . import limits


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
    """

    python_bin = settings.CODE_JAIL.get('python_bin')
    if python_bin:
        user = settings.CODE_JAIL['user']
        jail.configure("python", python_bin, user=user)
    requested_limits = settings.CODE_JAIL.get('limits', {})
    for name, value in requested_limits.items():
        limits.set_limit(name, value)
