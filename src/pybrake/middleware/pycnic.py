import time

from pycnic.core import WSGI

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
    pass
else:
    # Patch of route breakdown
    old_template_render = Template.render


    def patch_template_render(self, *args, **kwargs):
        start_span("template")
        res = old_template_render(self, *args, *kwargs)
        end_span("template")
        return res


    Template.render = patch_template_render

_UNKNOWN_ROUTE = "UNKNOWN"


# Route Stats Monitoring
def before_request(handler):
    if not handler.notifier.config.get("performance_stats"):
        return
    metric = RouteMetric(method=handler.request.method,
                         route=handler.request.path)
    set_active_metric(metric)


def after_request(handler):
    if not handler.notifier.config.get("performance_stats"):
        return

    metric = get_active_metric()
    if metric is not None:
        metric.status_code = handler.response.status_code
        metric.content_type = handler.response.header_dict.get('Content-Type')
        metric.end_time = time.time()
        handler.notifier.routes.notify(metric)
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


def request_filter(request, notice):
    if request is None:
        return notice

    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["url"] = request.path
    try:
        ctx["userAddr"] = request.ip
    except IndexError:
        ctx["userAddr"] = request.remote_addr

    notice["params"]["request"] = dict(
        json=request.json_args,
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        environ=request.environ,
        url_rule=request.path,
    )

    return notice


class PybrakeEnableWSGI(WSGI):
    # Route Stats Monitoring
    before = before_request
    after = after_request

    def __init__(self, environ, start_response):
        if "pybrake" in getattr(self, "config"):
            raise ValueError("pybrake is already injected")
        if "PYBRAKE" not in getattr(self, "config"):
            raise ValueError("app.config['PYBRAKE'] is not defined")

        self.notifier = Notifier(**getattr(self, "config")["PYBRAKE"])
        if _sqla_available and getattr(self, "sqlDBEngine"):
            event.listen(getattr(self, "sqlDBEngine"), "before_cursor_execute",
                         _before_sql_cursor(self.notifier))
            event.listen(getattr(self, "sqlDBEngine"), "after_cursor_execute",
                         _after_sql_cursor(self.notifier))
        super().__init__(environ, start_response)

    # Error notice
    def delegate(self):
        try:
            return super().delegate()
        except AttributeError as e:
            raise e
        except Exception as err:
            notice = self.notifier.build_notice(err)
            notice = request_filter(self.request, notice)
            self.notifier.send_notice(notice)
            raise err
