import asyncio
import inspect
import time
import typing as t

from aiohttp import web

from ..metrics import (
    set_active as set_active_metric,
    get_active as get_active_metric,
    start_span, end_span)
from ..notifier import Notifier
from ..route_metric import RouteMetric

try:
    from jinja2 import Template
except ImportError:
    pass
else:
    # Patch of route breakdown
    old_template_render = Template.render


    def patch_template_render(self, *args: t.Any, **kwargs: t.Any):
        start_span("template")
        res = old_template_render(self, *args, *kwargs)
        end_span("template")
        return res


    Template.render = patch_template_render

try:
    from sqlalchemy import event
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True


def _before_sql_cursor(notifier):
    def _sqla_before_cursor_execute(
            conn, cursor, statement, parameters, context,
            executemany
    ):
        if not notifier.config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_sql_cursor(notifier):
    def _sqla_after_cursor_execute(
            conn, cursor, statement, parameters, context,
            executemany
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


def pybrake_middleware(overrides=None, sqlEngine=None):
    if overrides is None:
        overrides = {}

    async def factory(app, handler):
        init_pybrake(app, sqlEngine)

        async def middleware(request: web.Request):
            resp = None
            notifier = app["pybrake"]
            if notifier.config.get("performance_stats"):
                metric = RouteMetric(method=request.method, route=request.path)
                set_active_metric(metric)
            try:
                resp = await handler(request)
                override = overrides.get(resp.status)
                if override:
                    resp = await override(request)
                return resp

            except web.HTTPException as ex:
                override = overrides.get(ex.status)
                if override:
                    resp = await override(request)
                raise ex

            except asyncio.CancelledError as cancelErr:
                raise cancelErr

            except Exception as err:
                handle_exception(err, app["pybrake"], request)
                override = overrides.get(500)
                if override:
                    resp = await override(request)
                raise err
            finally:
                if notifier.config.get("performance_stats"):
                    metric = get_active_metric()
                    if metric is not None:
                        metric.status_code = resp.status if resp else 500
                        metric.content_type = \
                            resp.content_type if resp else request.content_type
                        metric.end_time = time.time()
                        notifier.routes.notify(metric)
                        set_active_metric(None)

        return middleware

    return factory


def init_pybrake(app, sqlEngine=None):
    if "PYBRAKE" not in app:
        raise ValueError("app['PYBRAKE'] is not defined")
    if "pybrake" not in app:
        app["pybrake"] = Notifier(**app["PYBRAKE"])
        if sqlEngine and _sqla_available:
            event.listen(sqlEngine, "before_cursor_execute",
                         _before_sql_cursor(app['pybrake']))
            event.listen(sqlEngine, "after_cursor_execute",
                         _after_sql_cursor(app['pybrake']))


def handle_exception(ex, notifier, request):
    notice = notifier.build_notice(ex)
    notice["context"].update(additional_context(request))
    notice["params"].update(get_headers(request))
    notifier.send_notice(notice)


def additional_context(request):
    return dict(
        userAgent=get_user_agent(request),
        userAddr=attr_from_request(request, "remote"),
        httpMethod=attr_from_request(request, "method"),
        url=attr_from_request(request, "url"),
    )


def get_user_agent(request):
    headers = get_headers(request)
    return headers.get("User-Agent") if headers else None


def get_headers(request):
    headers = attr_from_request(request, "headers")
    return dict(headers=headers) if headers else {}


def attr_from_request(request, attr_name):
    if hasattr(request, attr_name):
        attr = getattr(request, attr_name)
        return attr() if inspect.ismethod(attr) else attr
    return None
