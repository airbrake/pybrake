from warnings import warn, simplefilter

from .middleware import celery


def __getattr__(name):
    if name == 'patch_celery':
        simplefilter("always", DeprecationWarning)
        warn(DeprecationWarning('pybrake.celery has been '
                                'renamed to '
             'pybrake.middleware.celery'))
        return celery.patch_celery
    raise AttributeError('No module named ' + name)
