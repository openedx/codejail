"""Django integration for codejail.

Code to glue codejail into a Django environment.

"""

from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

import codejail.jail_code


class ConfigureCodeJailMiddleware(object):
    """
    Middleware to configure codejail on startup.

    This is a Django idiom to have code run once on server startup: put the
    code in the `__init__` of some middleware, and have it do the work, then
    raise `MiddlewareNotUsed` to disable the middleware.

    """
    def __init__(self):
        python_bin = settings.CODE_JAIL.get('python_bin')
        if python_bin:
            user = settings.CODE_JAIL['user']
            codejail.jail_code.configure("python", python_bin, user=user)

        limits = settings.CODE_JAIL.get('limits', {})
        for name, value in limits.items():
            codejail.jail_code.set_limit(name, value)

        raise MiddlewareNotUsed
