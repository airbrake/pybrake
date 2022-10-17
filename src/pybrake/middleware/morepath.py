import logging
import time
import traceback

from morepath.authentication import NoIdentity
from morepath.directive import HtmlAction
from morepath.view import View

from morepath import render_json, app as application, render_html
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

logger = logging.getLogger(__name__)


# Route breakdown
def renderer(function):
    def wrapper(*args, **kw):
        start_span("template")
        res = function(*args, **kw)
        end_span("template")
        return res

    return wrapper


def patch__init__(self, model, render=None, template=None, load=None,
                  permission=None, internal=False, **predicates):
    render = render or renderer(render_html)
    super(HtmlAction, self).__init__(
        model, render, template, load, permission, internal, **predicates
    )


HtmlAction.__init__ = patch__init__


# Route Stats Monitoring
old__call__view = View.__call__

def __patch_call__(self, app, obj, request):
    notifier = app.settings.pybrake
    before_request(request, notifier.config)
    try:
        res = old__call__view(self, app, obj, request)
        after_request(notifier, res)
        return res
    except Exception as er:

        raise er

View.__call__ = __patch_call__


def before_request(request, config):
    # pylint: disable=fixme
    # TODO: When there is a path variable, pass the route url as a dynamic
    #  one. Ex:- /weather/{location_name} rather then /weather/pune
    if not config.get("performance_stats"):
        return
    metric = RouteMetric(method=request.method, route=request.path)
    set_active_metric(metric)


def after_request(notifier, resp):
    if not notifier.config.get("performance_stats"):
        return
    metric = get_active_metric()
    if metric is not None:
        metric.status_code = resp.status_code
        metric.content_type = resp.content_type
        metric.end_time = time.time()
        notifier.routes.notify(metric)
        set_active_metric(None)


# Error Handler
def request_filter(request, notice):
    if request is None:
        return notice
    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.url
    ctx["path_code_info"] = str(request.path_code_info.sourceline)
    ctx["userAddr"] = request.remote_addr

    user = {}
    try:
        if request.identity and not isinstance(request.identity, NoIdentity):
            user_data = request.identity.as_dict()
            for s in ["userid", "username", "name"]:
                user[s] = user_data.get(s, None)
            ctx["user"] = user
    except AttributeError:
        ctx["user"] = user

    notice["params"]["request"] = dict(
        body=dict(request.body),
        params=dict(request.params) if request.params else {},
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        url=request.path,
        env=request.environ,
    )

    return notice


def handle_exception(notifier, request, exception):
    notice = notifier.build_notice(exception)
    if request:
        notice = request_filter(request, notice)
    notifier.send_notice(notice)


@application.App.tween_factory()
def report_error(app, handler):
    def tween(request):
        try:
            response = handler(request)
            return response
        except Exception as er:  # pylint: disable=broad-except
            logger.exception(er)
            handle_exception(app.settings.pybrake, request, er)
            response = render_json(
                {
                    "app": repr(type(request.app)),
                    "unconsumed": request.unconsumed,
                    "error": str(er.__class__) + ':' + str(er),
                },
                request,
            )
            response.status_code = 500
            after_request(app.settings.pybrake, response)
            return response

    return tween


def init_app(app, sqlEngine=None):
    if getattr(app.settings, 'pybrake', None):
        raise ValueError("pybrake is already injected")
    if not getattr(app.settings, 'PYBRAKE', None):
        raise ValueError("app.settings.PYBRAKE is not defined")

    notifier = Notifier(**app.settings.PYBRAKE.__dict__)

    app.settings.pybrake = notifier

    # Query Stats Monitoring
    if _sqla_available and sqlEngine:
        _sqla_instrument(notifier, sqlEngine)

    return app


def _sqla_instrument(notifier, sqlEngine):
    event.listen(sqlEngine, "before_cursor_execute",
                 _before_cursor(notifier))
    event.listen(sqlEngine, "after_cursor_execute",
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
            try:
                traceback_frm = traceback.extract_stack(limit=7)[0]
            except IndexError as er:  # pylint: disable=unused-variable
                traceback_frm = None
            notifier.queries.notify(
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
