import time
import typing as t

from falcon import App

from ..metrics import (
    set_active as set_active_metric,
    get_active as get_active_metric,
    start_span, end_span)
from ..notifier import Notifier
from ..route_metric import RouteMetric

try:
    from sqlalchemy import event
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True

try:
    from jinja2 import Template
except ImportError:
    _jinja_available = False
else:
    _jinja_available = True

try:
    import falcon_auth  # pylint: disable=unused-import
except ImportError:
    _falcon_auth_available = False
else:
    _falcon_auth_available = True

try:
    import falcon_auth2  # pylint: disable=unused-import
except ImportError:
    _falcon_auth2_available = False
else:
    _falcon_auth2_available = True

_UNKNOWN_ROUTE = "UNKNOWN"


def before_request_middleware(notifier, req):
    if notifier and not notifier.config.get("performance_stats"):
        return

    metric = RouteMetric(method=req.method)
    set_active_metric(metric)


def after_request_middleware(notifier, req, resp):
    if notifier and not notifier.config.get("performance_stats"):
        return
    metric = get_active_metric()

    if req.uri_template:
        route = req.uri_template
    elif req.url:
        route = req.url
    else:
        route = _UNKNOWN_ROUTE
    if metric is not None:
        metric.route = route
        metric.status_code = int(resp.status.split(" ")[0]) if isinstance(
            resp.status, str) else resp.status
        metric.content_type = resp.content_type
        metric.end_time = time.time()
        notifier.routes.notify(metric)
        set_active_metric(None)


class PybrakeMiddleware:

    def __init__(self, notifier):
        self.notifier = notifier

    def process_request(self, req, resp):
        before_request_middleware(self.notifier, req=req)
        return resp

    async def process_request_async(self, req, resp):
        before_request_middleware(self.notifier, req=req)
        return resp

    def process_response(self, req, resp, resource, req_succeeded):
        after_request_middleware(notifier=self.notifier, req=req, resp=resp)
        return resp

    async def process_response_async(self, req, resp, resource, req_succeeded):
        after_request_middleware(notifier=self.notifier, req=req, resp=resp)
        return resp


def _before_sql_cursor(notifier):
    def _sqla_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if notifier and not notifier.config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_sql_cursor(notifier):
    def _sqla_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if notifier and not notifier.config.get("performance_stats"):
            return
        end_span("sql")
        metric = get_active_metric()
        if metric is not None:
            notifier.queries.notify(
                query=statement,
                method=getattr(metric, "method", ""),
                route=getattr(metric, "route", ""),
                start_time=metric.start_time,
                end_time=time.time(),
            )

    return _sqla_after_cursor_execute


def request_filter(request, notice):
    if request is None:
        return notice

    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.uri_template
    ctx["route"] = request.url

    try:
        user_addr = request.access_route[0]
    except IndexError:
        user_addr = request.remote_addr
    if user_addr:
        ctx["userAddr"] = user_addr

    if _falcon_auth_available:
        curr_user = request.context['user']
        user = {}
        for s in ["username", "name"]:
            if hasattr(curr_user, s):
                user[s] = getattr(curr_user, s)
        ctx["user"] = user

    if _falcon_auth2_available:
        curr_user = request.context.auth["user"]
        user = {}
        for s in ["username", "name"]:
            if hasattr(curr_user, s):
                user[s] = getattr(curr_user, s)
        ctx["user"] = user

    notice["params"]["request"] = dict(
        json=request.params,
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        environ=request.env,
        url_rule=request.uri_template,
    )

    return notice


def init_app(app: App, config: dict, sqlEngine=None) -> (App, dict):
    if "pybrake" in config:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in config:
        raise ValueError("config['PYBRAKE'] is not defined")

    notifier = Notifier(**config['PYBRAKE'])

    config["pybrake"] = notifier
    old_handle_exception = App._handle_exception

    def _patch_handle_exception(self, req, resp, ex, params):
        notice = notifier.build_notice(ex)
        notice = request_filter(req, notice)
        notifier.send_notice(notice)
        return old_handle_exception

    App._handle_exception = _patch_handle_exception

    # Patch of route stats
    app.add_middleware(PybrakeMiddleware(notifier=notifier))

    # Patch of route breakdown
    if _jinja_available:
        old_template_render = Template.render

        def patch_template_render(self, *args: t.Any, **kwargs: t.Any):
            start_span("template")
            res = old_template_render(self, *args, *kwargs)
            end_span("template")
            return res

        Template.render = patch_template_render

    if sqlEngine and _sqla_available:
        event.listen(sqlEngine, "before_cursor_execute",
                     _before_sql_cursor(notifier))
        event.listen(sqlEngine, "after_cursor_execute",
                     _after_sql_cursor(notifier))

    return app, config
