"""Django integration for codejail.

Code to glue codejail into a Django environment.

"""

from django.conf import settings as django_settings
from django.core.exceptions import MiddlewareNotUsed

from .integration import configure_from_settings


class ConfigureCodeJailMiddleware(object):
    """
    Middleware to configure codejail on startup.

    This is a Django idiom to have code run once on server startup: put the
    code in the `__init__` of some middleware, and have it do the work, then
    raise `MiddlewareNotUsed` to disable the middleware.

    """
    def __init__(self):
        configure_from_settings(django_settings)
        raise MiddlewareNotUsed
