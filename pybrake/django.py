import time
import functools

from django.conf import settings
from django.utils.module_loading import import_string
from django.db import connections
from django.template import Template

from .global_notifier import get_global_notifier
from .route_trace import RouteTrace, threadLocal


_UNKNOWN_ROUTE = "UNKNOWN"


def template_render(self, context):
    if not hasattr(threadLocal, "_ab_trace"):
        return self.nodelist.render(context)

    start_time = time.time()
    res = self.nodelist.render(context)
    end_time = time.time()

    ms = (end_time - start_time) * 1000
    threadLocal._ab_trace.inc_group("template", ms)

    return res


if Template._render != template_render:
    Template.original_render = Template._render
    Template._render = template_render


class AirbrakeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._notifier = get_global_notifier()

    def __call__(self, request):
        for conn in connections.all():
            wrap_cursor(conn, self._notifier)

        if request.resolver_match:
            route = request.resolver_match.view_name
        else:
            route = _UNKNOWN_ROUTE

        trace = RouteTrace(method=request.method, route=route)
        threadLocal._ab_trace = trace

        response = self.get_response(request)

        trace.status_code = response.status_code
        trace.content_type = response["Content-Type"]
        trace.end_time = time.time()

        self._notifier.routes.notify(trace)

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if (
            hasattr(threadLocal, "_ab_trace")
            and threadLocal._ab_trace.route == _UNKNOWN_ROUTE
        ):
            route = view_func.__module__
            route += "." + view_func.__name__
            threadLocal._ab_trace.route = route

    def process_exception(self, request, exception):
        if not self._notifier:
            return

        notice = self._notifier.build_notice(exception)

        ctx = notice["context"]
        ctx["url"] = request.build_absolute_uri()
        ctx["route"] = request.resolver_match.url_name

        user_addr = get_remote_addr(request)
        if user_addr:
            ctx["userAddr"] = user_addr

        req_filter = get_exception_reporter_filter(request)
        notice["params"]["request"] = dict(
            scheme=request.scheme,
            method=request.method,
            GET=request.GET,
            POST=req_filter.get_post_parameters(request),
            META=dict(request.META),
            FILES=request.FILES,
            COOKIES=request.COOKIES,
            session=dict(request.session),
        )

        if request.user.is_authenticated:
            user = request.user
            user_info = dict(username=user.get_username(), name=user.get_full_name())
            if hasattr(user, "get_email_field_name"):
                user_info["email"] = getattr(user, user.get_email_field_name())
            elif hasattr(user, "email"):
                user_info["email"] = user.email
            ctx["user"] = user_info

        self._notifier.send_notice(notice)


def get_remote_addr(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


@functools.lru_cache()
def get_default_exception_reporter_filter():
    # Instantiate the default filter for the first time and cache it.
    return import_string(settings.DEFAULT_EXCEPTION_REPORTER_FILTER)()


def get_exception_reporter_filter(request):
    default_filter = get_default_exception_reporter_filter()
    return getattr(request, "exception_reporter_filter", default_filter)


def wrap_cursor(conn, notifier):
    if hasattr(conn, "_ab_cursor"):
        return conn.cursor
    conn._ab_cursor = conn.cursor

    def cursor_wrapper(*args, **kwargs):
        cursor = conn._ab_cursor(*args, **kwargs)
        return CursorWrapper(conn, notifier, cursor)

    conn.cursor = cursor_wrapper
    return cursor_wrapper


class CursorWrapper:
    def __init__(self, conn, notifier, cursor):
        self._notifier = notifier
        self._cursor = cursor

    def callproc(self, procname, params=None):
        return self._record(self._cursor.callproc, procname, params)

    def execute(self, sql, params=None):
        return self._record(self._cursor.execute, sql, params)

    def executemany(self, sql, param_list):
        return self._record(self.cursor.executemany, sql, param_list)

    def _record(self, method, sql, params):
        start_time = time.time()
        try:
            return method(sql, params)
        finally:
            end_time = time.time()
            self._notifier.queries.notify(
                query=sql,
                method=threadLocal._ab_trace.method,
                route=threadLocal._ab_trace.route,
                start_time=start_time,
                end_time=end_time,
            )

    def __getattr__(self, attr):
        return getattr(self._cursor, attr)

    def __iter__(self):
        return iter(self._cursor)

    def __enter__(self):
        return self

    def __exit__(self, typ, value, traceback):
        self._cursor.close()
