from warnings import warn, simplefilter

from .middleware import flask


def __getattr__(name):
    if name == 'init_app':
        simplefilter("always", DeprecationWarning)
        warn(DeprecationWarning('pybrake.flask.init_app has been '
                                'renamed to '
                                'pybrake.middleware.flask.init_app'))
        return flask.init_app
    raise AttributeError('No module named ' + name)
