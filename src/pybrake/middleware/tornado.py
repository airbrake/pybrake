import time
import traceback

from tornado.web import RequestHandler, HTTPError

from ..metrics import (
    set_active as set_active_metrics,
    get_active as get_active_metrics,
    start_span,
    end_span,
)
from ..notifier import Notifier
from ..route_metric import RouteMetric

try:
    import tornado_sqlalchemy as _
    from sqlalchemy import event
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True

_UNKNOWN_ROUTE = "UNKNOWN"


def request_filter(notice, handler):
    request = handler.request
    if request is None:
        return notice

    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.uri
    ctx["route"] = str(request.host)

    if request.remote_ip:
        ctx["userAddr"] = request.remote_ip

    if handler.current_user:
        user = dict(id=getattr(handler.current_user, 'id'))
        for s in ["username", "name"]:
            if hasattr(handler.current_user, s):
                user[s] = getattr(handler.current_user, s)
        ctx["user"] = user

    notice["params"]["request"] = dict(
        body_arguments=dict(request.body_arguments),
        body=dict(request.body),
        files=dict(request.files),
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        query_arguments=request.query_arguments,
        path_kwargs=handler.path_kwargs,
    )

    return notice


def init_app(app):
    if "pybrake" in app.settings:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in app.settings:
        raise ValueError("app.settings['PYBRAKE'] is not defined")

    notifier = Notifier(**app.settings["PYBRAKE"])
    config = notifier.config

    app.settings["pybrake"] = notifier

    # Exception handling
    old_log_exception = RequestHandler.log_exception

    def _patch_log_exception(self, ty, value, tb):
        if not isinstance(value, HTTPError):
            _handle_exception(notifier, value, self)
        return old_log_exception(self, ty, value, tb)

    RequestHandler.log_exception = _patch_log_exception

    # Route stats
    old_execute = RequestHandler._execute

    async def _patch_execute(self, transforms, *args, **kwargs):
        if config.get("performance_stats"):
            _before_request(self.request, self)
        res = await old_execute(self, transforms, *args, **kwargs)
        if config.get("performance_stats"):
            _after_request(self, notifier)
        return res

    RequestHandler._execute = _patch_execute

    # Route Breakdown stats
    old_render = RequestHandler.render

    def _patch_render(self, template_name, **kwargs):
        start_span("template")
        res = old_render(self, template_name, **kwargs)
        end_span("template")
        return res

    RequestHandler.render = _patch_render

    if _sqla_available:
        _sqla_instrument(config, app)

    return app


def _before_request(request, app):
    request_route = None
    for rule in app.application.wildcard_router.rules:
        match = rule.matcher.match(request)
        if match is not None:
            request_route = rule.matcher.regex.pattern

    for rule in app.application.default_router.rules:
        match = rule.matcher.match(request)
        if match is not None and not request_route:
            request_route = rule.matcher.regex.pattern

    if request_route:
        if request_route.endswith("$"):
            request_route = request_route[:len(request_route) - 1]
        route = request_route
    elif request.url:
        route = request.uri
    else:
        route = _UNKNOWN_ROUTE
    metric = RouteMetric(method=request.method, route=route)
    set_active_metrics(metric)


def _after_request(response, notifier):
    metric = get_active_metrics()
    if metric is not None:
        metric.status_code = response.get_status()
        if 'Content-Type' in response._headers:
            metric.content_type = response._headers.get('Content-Type')
        metric.end_time = time.time()
        notifier.routes.notify(metric)
        set_active_metrics(None)


def _before_render_template(sender, template, context, **extra):
    start_span("template")


def _template_rendered(sender, template, context, **extra):
    end_span("template")


def _handle_exception(notifier, exception, handler):
    notice = notifier.build_notice(exception)
    notice = request_filter(notice, handler)
    notifier.send_notice(notice)


def _sqla_instrument(config, app):
    sqla = app.settings.get('db')
    event.listen(sqla.engine, "before_cursor_execute", _before_cursor(config))
    event.listen(sqla.engine, "after_cursor_execute", _after_cursor(
        config, app))


def _before_cursor(config):
    def _sqla_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if not config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_cursor(config, app):
    def _sqla_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if not config.get("performance_stats"):
            return
        end_span("sql")
        metric = get_active_metrics()
        if metric is not None:
            try:
                traceback_frm = traceback.extract_stack(limit=12)[0]
            except IndexError as er:  # pylint: disable=unused-variable
                traceback_frm = None
            app.settings["pybrake"].queries.notify(
                query=statement,
                method=getattr(metric, "method", ""),
                route=getattr(metric, "route", ""),
                start_time=metric.start_time,
                end_time=time.time(),
                function=traceback_frm.name if traceback_frm else '',
                file=traceback_frm.filename if traceback_frm else '',
                line=traceback_frm.lineno if traceback_frm else 0,
            )

    return _sqla_after_cursor_execute
