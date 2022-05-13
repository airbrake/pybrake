import logging
import sys
import time

from .. import Notifier
from .. import RouteMetric
from ..metrics import (
    set_active as set_active_metrics,
    get_active as get_active_metrics,
    start_span,
    end_span,
)

logger = logging.getLogger(__name__)

try:
    from pyramid.httpexceptions import HTTPException
    from pyramid.request import Request
    from pyramid.threadlocal import get_current_request
    from pyramid.config import Configurator
    from pyramid import renderers, router
except ImportError as e:
    logger.error(str(e))
    sys.exit()

try:
    from sqlalchemy import event
    from pyramid_basemodel import Base
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True

try:
    from pyramid_fullauth.request import request_user as current_user
except ImportError:
    _pyramid_login_available = False
else:
    _pyramid_login_available = True

_UNKNOWN_ROUTE = "UNKNOWN"


def request_filter(notice):
    request = get_current_request()

    if request is None:
        return notice

    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.url
    ctx["route"] = str(request.path)
    ctx["userAddr"] = request.remote_addr

    if _pyramid_login_available:
        curr_user = current_user(request)
        user = dict(id=curr_user.id)
        for s in ["username", "firstname", "lastname"]:
            if hasattr(curr_user, s):
                user[s] = getattr(curr_user, s)
        ctx["user"] = user

    notice["params"]["Request"] = dict(
        get=dict(request.GET),
        post=dict(request.POST),
        params=dict(request.params),
        body=dict(request.body),
        files=dict(request.body_file),
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        environ=request.environ,
        view_args=request.urlargs,
    )

    return notice


def _sqla_instrument(notifier):
    try:
        sqla = Base.metadata.bind
    except Exception as err:  # pylint: disable=broad-except
        raise err
    event.listen(sqla.engine, "before_cursor_execute",
                 _before_cursor(notifier))
    event.listen(sqla.engine, "after_cursor_execute", _after_cursor(notifier))


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


def route_stats_tween_factory(handler, registry):
    notifier = registry.settings.get('pybrake')
    if notifier.config.get('performance_stats'):
        # if stats support is enabled, return a wrapper
        def stats_tween(request):
            response = None
            metric = RouteMetric(
                method=request.method,
                route=str(request.path)
            )
            set_active_metrics(metric)
            try:
                response = handler(request)
            finally:
                metric = get_active_metrics()
                if metric is not None and response:
                    metric.status_code = response.status_code
                    metric.content_type = response.headers.get("Content-Type")
                    metric.end_time = time.time()
                    notifier.routes.notify(metric)
                    set_active_metrics(None)
            return response

        return stats_tween
    # if stats support is not enabled, return the original
    # handler
    return handler


def init_pybrake_config(config):
    if "pybrake" in config.registry.settings:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in config.registry.settings:
        raise ValueError("config.registry.settings['PYBRAKE'] is not defined")

    notifier = Notifier(**config.registry.settings["PYBRAKE"])

    notifier.add_filter(request_filter)
    config.registry.settings.update({"pybrake": notifier})

    # Error Notification Patch
    if hasattr(Request, "invoke_exception_view"):

        old_handle_exception_view = Request.invoke_exception_view
        Request.old_handle_exception_view = old_handle_exception_view

        def _handle_exception(self, *args, **kwargs):
            try:
                res = old_handle_exception_view(self, *args, **kwargs)
            except HTTPException as err:
                notifier.notify(err)
                raise err
            if res and res.status_int == 500 and self.exception:
                notifier.notify(res)
            return res

        Request.invoke_exception_view = _handle_exception

    # Patch for error notification on route call
    old_route_call = router.Router.__call__

    def _handle_exception_route_call(self, environ, start_response):
        try:
            return old_route_call(self, environ, start_response)
        except Exception as err:
            notifier.notify(err)
            raise err
    router.Router.__call__ = _handle_exception_route_call

    # Route Stats patch
    config.add_tween(
        'pybrake.middleware.pyramid.route_stats_tween_factory')

    # Patch for Template Render Stats
    old_render = renderers.render
    old_render_to_response = renderers.render_to_response

    def patch_render(*args, **kwargs):
        start_span("template")
        res = old_render(*args, **kwargs)
        end_span("template")
        return res

    def patch_render_to_response(*args, **kwargs):
        start_span("template")
        res = old_render_to_response(*args, **kwargs)
        end_span("template")
        return res

    renderers.render = patch_render
    renderers.render_to_response = patch_render_to_response

    # Patch for set up query stats
    old_make_wsgi_app = Configurator.make_wsgi_app

    def patch_make_wsgi_app(self):
        res = old_make_wsgi_app(self=self)
        notifier = res.registry.settings.get('pybrake')
        if _sqla_available and notifier:
            _sqla_instrument(notifier)

        return res

    Configurator.make_wsgi_app = patch_make_wsgi_app

    return config
