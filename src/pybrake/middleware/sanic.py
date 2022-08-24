import time
from typing import (
    Dict,
    Optional,
)

from sanic import Sanic
from sanic import response
from sanic.handlers import ErrorHandler

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

_UNKNOWN_ROUTE = "UNKNOWN"


def request_filter(request, notice):
    if request is None:
        return notice
    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.url
    ctx["route"] = str(request.route)
    ctx["userAddr"] = request.remote_addr if request.remote_addr else \
        request.ip

    user = {}
    try:
        if request.parsed_credentials:
            for s in ["username", "name"]:
                if hasattr(request.parsed_credentials, s):
                    user[s] = getattr(request.parsed_credentials, s)
            ctx["user"] = user
    except AttributeError:
        ctx["user"] = user

    notice["params"]["request"] = dict(
        query_args=request.query_args,
        query_string=request.query_string,
        form=dict(request.form),
        forwarded=dict(request.forwarded),
        json=dict(request.json) if request.json else {},
        files=dict(request.files),
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        endpoint=request.name,
        url=request.path,
        args=request.args,
        match_info=request.match_info,
    )

    return notice


class PybrakeErrorHandler(ErrorHandler):
    def default(self, request, exception):
        """
        handles errors that have no error handlers assigned and send it to
        Airbrake.
        :param request: Request object
        :param exception: Exception object
        :return:
        """
        notifier = request.app.config.get('pybrake')
        notice = notifier.build_notice(exception)
        if request:
            notice = request_filter(request, notice)
        notifier.send_notice(notice)
        return super().default(request, exception)


def init_app(app, sqlEngine=None) -> Sanic:
    if "pybrake" in app.config:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in app.config:
        raise ValueError("app.config['PYBRAKE'] is not defined")

    notifier = Notifier(**app.config["PYBRAKE"])
    config = notifier.config

    app.config["pybrake"] = notifier

    # Error Handler
    app.error_handler = PybrakeErrorHandler()

    # Route Stats Monitoring
    @app.middleware("request")
    async def before_request(request):
        if not config.get("performance_stats"):
            return
        metric = RouteMetric(method=request.method, route=request.url)
        set_active_metric(metric)

    @app.middleware("response")
    async def after_request(request, resp):
        if not config.get("performance_stats"):
            return

        metric = get_active_metric()
        if metric is not None:
            metric.status_code = resp.status
            metric.content_type = resp.content_type
            metric.end_time = time.time()
            notifier.routes.notify(metric)
            set_active_metric(None)

    # Query Stats Monitoring

    if _sqla_available and sqlEngine:
        _sqla_instrument(notifier, sqlEngine)

    # TODO: Add query stats for tortoise ORM  # pylint: disable=fixme

    # Route Breakdown Monitoring
    old_html_render = response.html

    def patch_html(
            body,
            status: int = 200,
            headers: Optional[Dict[str, str]] = None,
    ) -> response.HTTPResponse:
        start_span("template")
        res = old_html_render(body, status, headers)
        end_span("template")
        return res

    response.html = patch_html

    return app


def _sqla_instrument(notifier, sqlEngine):
    event.listen(sqlEngine.sync_engine, "before_cursor_execute",
                 _before_cursor(notifier))
    event.listen(sqlEngine.sync_engine, "after_cursor_execute",
                 _after_cursor(notifier))


def _before_cursor(notifier):
    def _sqla_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if not notifier.config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_cursor(notifier):
    def _sqla_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if not notifier.config.get("performance_stats"):
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
