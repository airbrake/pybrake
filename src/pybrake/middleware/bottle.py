import sys
import time

try:
    from bottle import (
        Bottle,
        template,
        request as bottle_request,
        response as bottle_response,
        HTTPError,
        __version__ as BOTTLE_VERSION,
    )
except ImportError as e:
    sys.exit()

from .. import Notifier
from .. import RouteMetric
from ..metrics import (
    set_active as set_active_metrics,
    get_active as get_active_metrics,
    start_span,
    end_span,
)

try:
    from bottle.ext.sqlalchemy import SQLAlchemyPlugin
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True

try:
    from bottle_login import LoginPlugin
except ImportError:
    _bottle_login_available = False
else:
    _bottle_login_available = True

_UNKNOWN_ROUTE = "UNKNOWN"


def request_filter(notice):
    if bottle_request is None:
        return notice
    ctx = notice["context"]
    ctx["method"] = bottle_request.method
    ctx["url"] = bottle_request.url
    ctx["route"] = str(bottle_request.path)

    try:
        user_addr = bottle_request.remote_route[0]
    except IndexError:
        user_addr = bottle_request.environ.get('REMOTE_ADDR')
    if user_addr:
        ctx["userAddr"] = user_addr

    if _bottle_login_available:
        for plugin in bottle_request.app.plugins:
            if isinstance(plugin, LoginPlugin):
                current_user = plugin.get_user()
                user = dict(id=current_user.get_id())
                for s in ["username", "name"]:
                    if hasattr(current_user, s):
                        user[s] = getattr(current_user, s)
                ctx["user"] = user

    notice["params"]["request"] = dict(
        form=dict(bottle_request.forms),
        json=bottle_request.json and dict(bottle_request.json) or {},
        files=dict(bottle_request.files),
        cookies=dict(bottle_request.cookies),
        headers=dict(bottle_request.headers),
        url_rule=bottle_request.url,
        url_args=dict(bottle_request.url_args),
        script_name=bottle_request.script_name,
        query=bottle_request.query,
        query_string=dict(bottle_request.query_string),
    )
    return notice


def before_request_middleware():
    notifier = get_notifier()
    if notifier and not notifier.config.get("performance_stats"):
        return

    if bottle_request.url:
        route = bottle_request.url
    else:
        route = _UNKNOWN_ROUTE

    metric = RouteMetric(method=bottle_request.method, route=route)
    set_active_metrics(metric)


def after_request_middleware():
    notifier = get_notifier()
    if notifier and not notifier.config.get("performance_stats"):
        return bottle_response

    metric = get_active_metrics()
    if metric is not None:
        metric.status_code = bottle_response.status_code
        metric.content_type = bottle_response.content_type
        metric.end_time = time.time()
        notifier.routes.notify(metric)
        set_active_metrics(None)

    return bottle_response


def _handle_exception(app, environ):
    res = app.old_handle(environ)
    if isinstance(res, Exception) and isinstance(res, HTTPError):
        notifier = app.config["pybrake"]
        notice = notifier.build_notice(res)
        notifier.send_notice(notice)
    # scope cleanup
    return res


# Patch for set template render stats
old_template = template


def _template_render(*args, **kwargs):
    start_span("template")
    res = old_template(*args, **kwargs)
    end_span("template")
    return res


template = _template_render


def _sqla_instrument(app):
    try:
        sqla = None
        for plugin in app.plugins:
            if isinstance(plugin, SQLAlchemyPlugin):
                sqla = plugin
                break
        if sqla is None:
            return
    except Exception as err:  # pylint: disable=broad-except
        raise err

    from sqlalchemy import event  # pylint: disable=import-outside-toplevel

    event.listen(sqla.engine, "before_cursor_execute", _before_cursor())
    event.listen(sqla.engine, "after_cursor_execute", _after_cursor())


def _before_cursor():
    def _sqla_before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        notifier = get_notifier()
        if notifier and not notifier.config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_cursor():
    def _sqla_after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        notifier = get_notifier()
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


def get_notifier():
    return bottle_request.app.config.get('pybrake')  # pylint: disable=no-member


def init_app(app):
    if "pybrake" in app.config:
        raise ValueError("pybrake is already injected")
    if "PYBRAKE" not in app.config:
        raise ValueError("app.config['PYBRAKE'] is not defined")

    notifier = Notifier(**app.config["PYBRAKE"])

    notifier.add_filter(request_filter)

    app.config["pybrake"] = notifier

    # Patch for handle exception notification
    old_handle = Bottle._handle
    Bottle.old_handle = old_handle
    Bottle._handle = _handle_exception

    app.add_hook('before_request', before_request_middleware)
    app.add_hook('after_request', after_request_middleware)

    if _sqla_available:
        _sqla_instrument(app)

    return app
