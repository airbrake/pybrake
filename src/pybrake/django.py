from warnings import warn, simplefilter

from .middleware import django


def __getattr__(name):
    if name == 'AirbrakeMiddleware':
        simplefilter("always", DeprecationWarning)
        warn(DeprecationWarning('pybrake.django.AirbrakeMiddleware has been '
                                'renamed to '
             'pybrake.middleware.django.AirbrakeMiddleware'))
        return django.AirbrakeMiddleware
    raise AttributeError('No module named ' + name)
