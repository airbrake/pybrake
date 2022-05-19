import contextvars
import time
import types

from fastapi import FastAPI, Request
from starlette.exceptions import ExceptionMiddleware
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from ..metrics import (
    set_active as set_active_metrics,
    get_active as get_active_metrics,
    start_span,
    end_span,
)
from ..notifier import Notifier
from ..route_metric import RouteMetric

current_request = contextvars.ContextVar("request_global",
                                         default=types.SimpleNamespace())


try:
    from sqlalchemy import future
    from sqlalchemy import event
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True

_UNKNOWN_ROUTE = "UNKNOWN"


async def form_data(req):
    return await req.form()


def request_filter(notice):
    request = current_request.get()
    request_values = dict(request.items())
    if request is None:
        return notice

    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.url
    ctx["userAddr"] = request.client.host

    try:
        user = request.user
    except AssertionError:
        user = {}

    ctx["user"] = user

    try:
        session = request.session
    except AssertionError:
        session = {}

    notice["params"]["request"] = dict(
        session=session,
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        path=request_values.get('path'),
        path_params=dict(request.path_params),
        query_params=dict(request.query_params),
    )

    return notice


def _before_request(request):
    if request.url:
        route = request.url.path
    else:
        route = _UNKNOWN_ROUTE

    metric = RouteMetric(method=request.method, route=route)
    set_active_metrics(metric)


def _after_request(response, notifier):
    metric = get_active_metrics()
    if metric is not None:
        metric.status_code = response.status_code
        metric.content_type = response.headers.get("Content-Type")
        metric.end_time = time.time()
        notifier.routes.notify(metric)
        set_active_metrics(None)


def _before_cursor(notifier):
    def _sqla_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if notifier and not notifier.config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_cursor(notifier):
    def _sqla_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if notifier and not notifier.config.get("performance_stats"):
            return
        end_span("sql")
        metric = get_active_metrics()
        if metric is not None:
            notifier.queries.notify(
                query=statement,
                method=getattr(metric, "method", ""),
                route=getattr(metric, "route", ""),
                start_time=metric.start_time,
                end_time=time.time(),
            )

    return _sqla_after_cursor_execute


def init_app(app: FastAPI, sqlEngine: future.Engine = None) -> FastAPI:
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

    @app.middleware("http")
    async def init_request_vars(request: Request, call_next):
        current_request.set(request)
        response = await call_next(request)
        return response

    notifier = Notifier(**app.extra["PYBRAKE"])
    app.extra["pybrake"] = notifier
    config = notifier.config

    notifier.add_filter(request_filter)

    # Error notification patch
    old_exception_error_call = ExceptionMiddleware.__call__

    async def patch_exception_error_call(
            self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await old_exception_error_call(self, scope, receive, send)
        except Exception as exc:
            notifier.notify(exc)
            raise exc

    ExceptionMiddleware.__call__ = patch_exception_error_call

    # Route Stats monitoring
    @app.middleware("http")
    async def process_route_stats(request: Request, call_next):
        if config.get("performance_stats"):
            _before_request(request)
        response = await call_next(request)
        if config.get("performance_stats"):
            _after_request(response, notifier)
        return response

    # Route breakdown stats monitoring
    old_render = Response.render

    def patch_render(self, content) -> bytes:
        if self.media_type == 'text/html':
            start_span("template")
        res = old_render(
            self, content
        )
        if self.media_type == 'text/html':
            end_span("template")
        return res

    Response.render = patch_render

    # Query Stats monitoring
    if _sqla_available and sqlEngine is not None:
        event.listen(sqlEngine, "before_cursor_execute",
                     _before_cursor(notifier))
        event.listen(sqlEngine, "after_cursor_execute",
                     _after_cursor(notifier))

    return app
