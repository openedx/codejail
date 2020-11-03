"""
Read codejail configuration that is specified via Django settings.
"""
# Django is not a test requirement of codejail,
# so we cannot lint this file.
# pylint: skip-file

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property

from . import config
from .manual_configuration import ManualConfiguration


class DjangoCodejailConfiguration(config.CodejailConfiguration):
    """
    Concrete configuration class loading from `django.conf:settings.CODE_JAIL`.

    Intended for use in Django services (specifically, edx-platform).
    """
    def get_config_for_command(self, command):
        """
        Implements `CodejailConfiguration.get_config_for_command`.

        For DjablengoCodejailConfiguration, 'python' is the only configurable
        command.
        """
        if command != 'python':
            return None
        python_bin = self._settings_from_django.get('python_bin')
        if not python_bin:
            return None
        return config.CommandConfiguration(
            python_bin=python_bin,
            user=self._settings_from_django.get('user'),
        )

    def get_global_limits(self):
        """
        Implements `CodejailConfiguration.get_global_limits`.
        """
        # This function shares the same extract-from-dictionary logic
        # as `ManualConfiguration.get_global_limits`, so just re-use
        # that function.
        ManualConfiguration(self._settings_from_django).get_global_limits()

    def get_limit_overrides(self, overrides_context):
        """
        Implements `CodejailConfiguration.get_limit_overrides`.
        """
        # This function shares the same extract-from-dictionary logic
        # as `ManualConfiguration.get_limit_overrides`, so just re-use
        # that function.
        ManualConfiguration(self._settings_from_django).get_limit_overrides()

    @cached_property
    def _settings_from_django(self):
        """
        Fetch CODE_JAIL settings.

        If missing or falsy, return an empty dictionary.
        If provided but not a dictionary, raise `ImproperlyConfigured`.

        Returns: dict
        """
        try:
            codejail_settings = settings.CODE_JAIL
        except AttributeError:
            return {}
        if not codejail_settings:
            return {}
        if not isinstance(codejail_settings, dict):
            raise ImproperlyConfigured(
                "settings.CODE_JAIL should be a dict; instead has type: " +
                type(codejail_settings)
            )
        return codejail_settings

    def __repr__(self):
        """
        Return developer-friendly string representation.
        """
        return "{self.__class__.__name__}({self._settings_from_django!r})".format(self=self)
