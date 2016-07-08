"""
Test configuring code jails from settings objects.
"""

from unittest import TestCase

from codejail import django_integration, jail, languages


class FakeJailSettings(object):
    def __init__(self, setting_value):
        self.CODE_JAIL = setting_value  # pylint: disable=invalid-name


class TestDjangoIntegration(TestCase):

    def setUp(self):
        super(TestDjangoIntegration, self).setUp()
        self.existing_commands = jail.COMMANDS
        jail.COMMANDS = {}

    def tearDown(self):
        jail.COMMANDS = self.existing_commands
        super(TestDjangoIntegration, self).tearDown()

    def test_configure_jail(self):
        codejail_setting = FakeJailSettings({
            'jails': [
                {
                    'command': 'fakey-fakey',
                    'user': 'nobody',
                    'bin_path': '/usr/bin/python',
                    'lang': languages.python3,
                }
            ]
        })
        django_integration.configure_from_settings(codejail_setting)
        self.assertTrue(jail.is_configured('fakey-fakey'))

    def test_configure_legacy_jail(self):
        codejail_setting = FakeJailSettings({
            'python_bin': '/usr/bin/python',
            'user': 'abc',
        })
        django_integration.configure_from_settings(codejail_setting)
        codejail = jail.get_codejail('python')
        self.assertEqual(codejail.command, 'python')
        self.assertEqual(codejail.bin_path, '/usr/bin/python')
        self.assertEqual(codejail.user, 'abc')
        self.assertEqual(codejail.lang, languages.python2)
