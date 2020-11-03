"""Test django_integration_utils.py"""

from unittest import TestCase

from .. import jail_code
from ..django_integration_utils import apply_django_settings
from .util import ResetJailCodeStateMixin


class ApplyDjangoSettingsTest(ResetJailCodeStateMixin, TestCase):
    """
    Test `apply_settings_from_django` function.
    """

    def test_not_configured(self):
        """
        Test that conditions are sane if `apply_settings_from_django` is not run at all.
        """
        # No Python configuration.
        assert not jail_code.is_configured('python')

        # There are global limits.
        assert jail_code.LIMITS

        # No overrides, so the effective limits are the same as the global limits.
        assert jail_code.get_effective_limits() == jail_code.LIMITS

    def test_empty_config(self):
        """
        Test that conditions are sane if `apply_settings_from_django` receives an empty dict.
        """
        apply_django_settings({})

        # No Python configuration.
        assert not jail_code.is_configured('python')

        # There are global limits.
        assert jail_code.LIMITS

        # No overrides, so the effective limits are the same as the global limits.
        assert jail_code.get_effective_limits() == jail_code.LIMITS

    def test_command_config(self):
        """
        Test that Python path and user can be configured.
        """
        apply_django_settings({
            'python_bin': '/a/b/c/bin/python',
            'user': 'python_executor',
        })
        assert (
            jail_code.COMMANDS['python'] ==
            {
                'cmdline_start': ['/a/b/c/bin/python', '-E', '-B'],
                'user': 'python_executor',
            }
        )

    def test_limits_config(self):
        """
        Test that limits can be configured.
        """
        apply_django_settings({
            'limits': {
                'CPU': 5,
                "REALTIME": 7,
                'VMEM': 123456789,
                'PROXY': 1,
            },
        })
        assert (
            jail_code.get_effective_limits() ==
            {
                'CPU': 5,
                'REALTIME': 7,
                'VMEM': 123456789,
                'FSIZE': 0,
                'NPROC': 15,
                'PROXY': 1,
            }
        )

    def test_limits_with_overrides_config(self):
        """
        Test that limits can be configured and (besides PROXY) be overriden.
        """
        apply_django_settings({
            'limits': {
                'CPU': 5,
                "REALTIME": 7,
                'VMEM': 123456789,
                'PROXY': 1,
            },
            'limit_overrides': {
                'course-v1:a+b+c': {
                    'CPU': 50,
                    'FSIZE': 88,
                },
                'pathway-v1:x+y+z': {
                    'VMEM': 987654321,
                    'PROXY': 0,  # This override should not work.
                },
            },
        })

        # Global limits still apply.
        assert (
            jail_code.get_effective_limits() ==
            {
                'CPU': 5,
                'REALTIME': 7,
                'VMEM': 123456789,
                'FSIZE': 0,
                'NPROC': 15,
                'PROXY': 1,
            }
        )

        # Context without configured overrides just uses global limits.
        assert (
            jail_code.get_effective_limits() ==
            jail_code.get_effective_limits('arbitrary-context')
        )

        # CPU and FSIZE are overriden.
        assert (
            jail_code.get_effective_limits('course-v1:a+b+c') ==
            {
                'CPU': 50,
                'REALTIME': 7,
                'VMEM': 123456789,
                'FSIZE': 88,
                'NPROC': 15,
                'PROXY': 1,
            }
        )

        # VMEM is overriden, but PROXY override is ignored.
        assert (
            jail_code.get_effective_limits('pathway-v1:x+y+z') ==
            {
                'CPU': 5,
                'REALTIME': 7,
                'VMEM': 987654321,
                'FSIZE': 0,
                'NPROC': 15,
                'PROXY': 1,
            }
        )
