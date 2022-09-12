from .starlette import init_pybrake


def init_app(app, sqlEngine=None):
    """
    Initiate the pybrake notifier and apply the patch for
    error monitoring and APM.
    :param app: instance of FastAPI application
    :param sqlEngine: SQLALCHEMY engine instance
    :return: FastAPI application instance after apply patch or new setting
    """
    if "pybrake" in app.extra:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in app.extra:
        raise ValueError("app.config['PYBRAKE'] is not defined")

    app, notifier = init_pybrake(app, app.extra["PYBRAKE"], sqlEngine)
    app.extra["pybrake"] = notifier
    return app
