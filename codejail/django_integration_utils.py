"""
Utility functions to support Django integration for codejail.

Split out from `django_integration` to allow testing without installing Django.
"""

from . import jail_code


def apply_django_settings(code_jail_settings, config=None):
    """
    Apply a settings.CODE_JAIL dictionary to a :class:`~codejail.jail_code.CodeJailConfig`.

    ``config`` is an optional :class:`~codejail.jail_code.CodeJailConfig` instance.
    When omitted the module-level default config (``jail_code._default_config``) is
    used, which preserves the original behaviour.  Pass an explicit instance in tests
    or multi-tenant scenarios where you need isolated configuration.
    """
    cfg = config if config is not None else jail_code._default_config
    python_bin = code_jail_settings.get('python_bin')
    if python_bin:
        user = code_jail_settings['user']
        cfg.configure("python", python_bin, user=user)
    limits = code_jail_settings.get('limits', {})
    for name, value in limits.items():
        cfg.set_limit(
            limit_name=name,
            value=value,
        )
    limit_overrides = code_jail_settings.get('limit_overrides', {})
    for context, overrides in limit_overrides.items():
        for name, value in overrides.items():
            cfg.override_limit(
                limit_name=name,
                value=value,
                limit_overrides_context=context,
            )
