"""Django integration for codejail.

Code to glue codejail into a Django environment.

"""

# pylint: skip-file

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.utils.deprecation import MiddlewareMixin

from .django_integration_utils import try_load_configuration_from_django


class ConfigureCodeJailMiddleware(MiddlewareMixin):
    """
    Middleware to configure codejail on startup.

    This is a Django idiom to have code run once on server startup: put the
    code in the `__init__` of some middleware, and have it do the work, then
    raise `MiddlewareNotUsed` to disable the middleware.
    """
    def __init__(self, *args, **kwargs):
        try_load_configuration_from_django()
        raise MiddlewareNotUsed

