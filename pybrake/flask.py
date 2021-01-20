import time
from flask import (
    request,
    got_request_exception,
    before_render_template,
    template_rendered,
)

try:
    import flask_sqlalchemy as _
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True

try:
    from flask_login import current_user
except ImportError:
    _flask_login_available = False
else:
    _flask_login_available = True

from .notifier import Notifier
from .route_metric import RouteMetric
from . import metrics


_UNKNOWN_ROUTE = "UNKNOWN"


def request_filter(notice):
    if request is None:
        return notice

    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.url
    ctx["route"] = str(request.endpoint)

    try:
        user_addr = request.access_route[0]
    except IndexError:
        user_addr = request.remote_addr
    if user_addr:
        ctx["userAddr"] = user_addr

    if _flask_login_available and current_user.is_authenticated:
        user = dict(id=current_user.get_id())
        for s in ["username", "name"]:
            if hasattr(current_user, s):
                user[s] = getattr(current_user, s)
        ctx["user"] = user

    notice["params"]["request"] = dict(
        form=request.form,
        json=request.json,
        files=request.files,
        cookies=request.cookies,
        headers=dict(request.headers),
        environ=request.environ,
        blueprint=request.blueprint,
        url_rule=request.url_rule,
        view_args=request.view_args,
    )

    return notice


def init_app(app):
    if "pybrake" in app.extensions:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in app.config:
        raise ValueError("app.config['PYBRAKE'] is not defined")

    notifier = Notifier(**app.config["PYBRAKE"])
    config = notifier.config

    notifier.add_filter(request_filter)

    app.extensions["pybrake"] = notifier
    got_request_exception.connect(_handle_exception, sender=app)

    before_render_template.connect(_before_render_template, sender=app)
    template_rendered.connect(_template_rendered, sender=app)

    app.before_request(_before_request(config, notifier))
    app.after_request(_after_request(config, notifier))

    if _sqla_available:
        _sqla_instrument(config, app)

    return app


def _before_request(config, notifier):
    def before_request_middleware():
        if not config.get("performance_stats"):
            return

        if request.url_rule:
            route = request.url_rule.rule
        else:
            route = _UNKNOWN_ROUTE

        metric = RouteMetric(method=request.method, route=route)
        metrics.set_active(metric)

    return before_request_middleware


def _after_request(config, notifier):
    def after_request_middleware(response):
        if not config.get("performance_stats"):
            return None

        metric = metrics.get_active()
        if metric is not None:
            metric.status_code = response.status_code
            metric.content_type = response.headers.get("Content-Type")
            metric.end_time = time.time()
            notifier.routes.notify(metric)
            metrics.set_active(None)

        return response

    return after_request_middleware


def _before_render_template(sender, template, context, **extra):
    metrics.start_span("template")


def _template_rendered(sender, template, context, **extra):
    metrics.end_span("template")


def _handle_exception(sender, exception, **_):
    notifier = sender.extensions["pybrake"]

    notice = notifier.build_notice(exception)
    notifier.send_notice(notice)


def _sqla_instrument(config, app):
    try:
        sqla = app.extensions["sqlalchemy"]
    except Exception:  # pylint: disable=broad-except
        return

    from sqlalchemy import event  # pylint: disable=import-outside-toplevel

    engine = sqla.db.get_engine()
    event.listen(engine, "before_cursor_execute", _before_cursor(config))
    event.listen(engine, "after_cursor_execute", _after_cursor(config))

def _before_cursor(config):
    def _sqla_before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        if not config.get("performance_stats"):
            return
        metrics.start_span("sql")

    return _sqla_before_cursor_execute

def _after_cursor(config):
    def _sqla_after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        if not config.get("performance_stats"):
            return
        metrics.end_span("sql")

    return _sqla_after_cursor_execute
