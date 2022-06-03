import functools
import time

from masonite.middleware import Middleware
from masonite.views import View

from .. import Notifier
from .. import QueueMetric
from .. import RouteMetric
from ..metrics import (
    set_active as set_active_metric,
    get_active as get_active_metric,
    start_span,
    end_span,
)

try:
    from masoniteorm.connections.BaseConnection import BaseConnection
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True


def request_filter(request, notice):
    if request is None:
        return notice
    ctx = notice["context"]
    ctx["method"] = request.get_request_method()
    ctx["url"] = request.route.url
    ctx["route"] = str(request.route)
    ctx["userAddr"] = request.ip()

    user = {}
    try:
        if request.user():
            for s in ["username", "name", "email"]:
                if hasattr(request.user(), s):
                    user[s] = getattr(request.user(), s)
            ctx["user"] = user
    except AttributeError:
        ctx["user"] = user

    notice["params"]["request"] = dict(
        path_with_query=request.get_path_with_query,
        input=dict(request.all()),
        headers=request.header_bag.to_dict(),
        url=request.get_path(),
    )

    return notice


class PybrakeNotifier:

    def __init__(self, application):
        self.application = application

        if self.application.objects.get('pybrake') and \
                self.application.objects.get('pybrake').notifier:
            raise ValueError("pybrake is already injected")
        if not self.application.objects.get('config').has(
                'application.pybrake'):
            raise ValueError("app.config['PYBRAKE'] is not defined")

        self.notifier = Notifier(**self.application.objects.get('config').get(
            'application.pybrake'))
        self.application.objects['pybrake'] = self.notifier

        # Route Breakdown
        old_render = View.render

        def patch_render(selfC, template: str, dictionary: dict = None) -> \
                "View":
            start_span('template')
            res = old_render(selfC, template, dictionary)
            end_span('template')
            return res

        View.render = patch_render

        # Query Stats
        if _sqla_available:
            old_statement = BaseConnection.statement

            def patch_statement(selfC, query, bindings=()):
                if self.notifier.config.get('performance_stats'):
                    start_span("sql")
                res = old_statement(selfC, query, bindings)
                if self.notifier.config.get('performance_stats'):
                    end_span("sql")
                    metric = get_active_metric()
                    if metric is not None:
                        self.notifier.queries.notify(
                            query=query,
                            method=getattr(metric, "method", ""),
                            route=getattr(metric, "route", ""),
                            start_time=metric.start_time,
                            end_time=time.time(),
                        )
                return res

            BaseConnection.statement = patch_statement


# Error Notification
class PybrakeErrorListener:

    def handle(self, exception_type, exception):
        try:
            # pylint: disable=import-outside-toplevel
            from wsgi import application
        except ImportError:
            application = False
        if not application:
            return None
        request = application.make('request')
        notice = request.app.objects['pybrake'].notifier.build_notice(
            exception)
        if request:
            notice = request_filter(request, notice)
        request.app.objects['pybrake'].notifier.send_notice(notice)
        return None


# Route Stats
class PybrakeRouteMiddleware(Middleware):
    def before(self, request, response):
        if not request.app.objects['pybrake'].notifier.config.get(
                "performance_stats"):
            return None
        metric = RouteMetric(method=request.get_request_method(),
                             route=request.route.url)
        set_active_metric(metric)

        return request

    def after(self, request, response):
        notifier = request.app.objects['pybrake'].notifier
        if not notifier.config.get("performance_stats"):
            return
        metric = get_active_metric()
        if metric is not None:
            metric.status_code = response.get_status() or 500
            metric.content_type = response.header_bag.to_dict().get(
                'Content-Type')
            metric.end_time = time.time()
            notifier.routes.notify(metric)
            set_active_metric(None)


# Queue Stats
def schedule_task(fn):
    @functools.wraps(fn)
    def wrap(*args, **kwargs):
        try:
            # pylint: disable=import-outside-toplevel
            from wsgi import application
        except ImportError:
            application = False
        if application:
            metric = QueueMetric(queue=args[0].name)
            set_active_metric(metric)
            notifier = application.objects['pybrake'].notifier
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                notifier.notify(exc)
                raise exc
            finally:
                notifier.queues.notify(metric)
                set_active_metric(None)
        else:
            return fn(*args, **kwargs)

    return wrap
