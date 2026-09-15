"""
Utility functions to support Django integration for codejail.

Split out from `django_integration` to allow testing without installing Django.
"""

from . import jail_code


def apply_django_settings(code_jail_settings):
    """
    Apply a settings.CODE_JAIL dictionary to the `jail_code` module.
    """
    python_bin = code_jail_settings.get('python_bin')
    if python_bin:
        user = code_jail_settings['user']
        jail_code.configure("python", python_bin, user=user)
    limits = code_jail_settings.get('limits', {})
    for name, value in limits.items():
        jail_code.set_limit(
            limit_name=name,
            value=value,
        )
    limit_overrides = code_jail_settings.get('limit_overrides', {})
    for context, overrides in limit_overrides.items():
        for name, value in overrides.items():
            jail_code.override_limit(
                limit_name=name,
                value=value,
                limit_overrides_context=context,
            )
