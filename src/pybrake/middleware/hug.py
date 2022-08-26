import time
import hug  # pylint: disable=import-error
from ..metrics import (
    set_active as set_active_metric,
    get_active as get_active_metric,
    start_span, end_span
)
from ..notifier import Notifier
from ..route_metric import RouteMetric

try:
    from sqlalchemy import event
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True


_UNKNOWN_ROUTE = "UNKNOWN"


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

    if hug.directives.user:  # pylint: disable=using-constant-test
        curr_user = {}
        for s in ["username", "name"]:
            if hasattr(hug.directives.user, s):
                curr_user[s] = getattr(hug.directives.user, s)
        ctx["user"] = curr_user

    notice["params"]["request"] = dict(
        json=request.params,
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        environ=request.env,
        url_rule=request.uri_template,
    )

    return notice


def before_request_middleware(notifier, req):
    if notifier and not notifier.config.get("performance_stats"):
        return

    if req.url:
        route = req.url
    else:
        route = _UNKNOWN_ROUTE

    metric = RouteMetric(method=req.method, route=route)
    set_active_metric(metric)


def after_request_middleware(notifier, req, resp):
    if notifier and not notifier.config.get("performance_stats"):
        return
    metric = get_active_metric()

    if metric is not None:
        metric.status_code = int(resp.status.split(" ")[0]) if isinstance(
            resp.status, str) else resp.status
        metric.content_type = resp.content_type
        metric.end_time = time.time()
        notifier.routes.notify(metric)
        set_active_metric(None)


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


def init_app(api, config, sqlEngine=None):
    if "pybrake" in config:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in config:
        raise ValueError("config['PYBRAKE'] is not defined")

    notifier = Notifier(**config['PYBRAKE'])

    # Route stats
    @hug.middleware_class(api=api)
    class PybrakeMiddleware:  # pylint: disable=unused-variable

        def __init__(self):
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

        async def process_response_async(self, req, resp, resource,
                                         req_succeeded):
            after_request_middleware(notifier=self.notifier, req=req,
                                     resp=resp)
            return resp

    # Route Breakdown stats
    old_html = hug.output_format.html

    @hug.format.content_type("text/html; charset=utf-8")
    def _patch_html_output_format(content, **kwargs):
        start_span("template")
        res = old_html(content, *kwargs)
        end_span("template")
        return res

    hug.output_format.html = _patch_html_output_format

    # Patch Error handler
    http_call = hug.interface.HTTP.__call__

    def _patch_call__(self, request, response, api_version=None, **kwargs):
        try:
            return http_call(self, request, response, api_version=None, **kwargs)
        except Exception as e:
            notice = notifier.build_notice(e)
            notice = request_filter(request, notice)
            notifier.send_notice(notice)
            response.status = '500 Internal Server Error'
            raise e

    hug.interface.HTTP.__call__ = _patch_call__

    # Query Stats
    if sqlEngine and _sqla_available:
        event.listen(sqlEngine, "before_cursor_execute",
                     _before_sql_cursor(notifier))
        event.listen(sqlEngine, "after_cursor_execute",
                     _after_sql_cursor(notifier))

    return config
