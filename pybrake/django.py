import time
import functools
import threading

from django.conf import settings
from django.utils.module_loading import import_string
from django.db import connections
from django.template import Template
from django.core import cache
from django.core.cache import CacheHandler
from django.middleware import cache as middleware_cache

from .global_notifier import get_global_notifier
from .route_metric import RouteMetric
from . import metrics


_UNKNOWN_ROUTE = "UNKNOWN"
_REQUEST_KEY = "_django_request"

threadLocal = threading.local()


def set_request(request):
    setattr(threadLocal, _REQUEST_KEY, request)


def get_request():
    return getattr(threadLocal, _REQUEST_KEY, None)


def request_filter(notice):
    request = getattr(threadLocal, _REQUEST_KEY, None)
    if request is None:
        return notice

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

    return notice


def template_render(self, context):
    metrics.start_span("template")
    res = self.nodelist.render(context)
    metrics.end_span("template")
    return res


if Template._render != template_render:  # pylint: disable=comparison-with-callable
    Template.original_render = Template._render
    Template._render = template_render


class AirbrakeMiddleware:
    def __init__(self, get_response):
        self._notifier = get_global_notifier()
        self._config = self._notifier.config
        self.get_response = get_response

        self._notifier.add_filter(request_filter)

    def __call__(self, request):
        if not self._config.get("performance_stats"):
            return self.get_response(request)

        set_request(request)

        for conn in connections.all():
            wrap_cursor(conn, self._notifier)

        metric = RouteMetric(method=request.method)
        with metrics.activated_metric(metric):
            response = self.get_response(request)

        metric.status_code = response.status_code
        if "Content-Type" in response:
            metric.content_type = response["Content-Type"]
        metric.end_time = time.time()
        self._notifier.routes.notify(metric)

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        metric = metrics.get_active()
        if metric is None:
            return

        if request.resolver_match.view_name:
            metric.route = request.resolver_match.view_name
        else:
            route = view_func.__module__
            route += "." + view_func.__name__
            metric.route = route

        set_request(None)

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
        metric = metrics.get_active()

        start_time = time.time()
        metrics.start_span("sql", start_time=start_time)
        try:
            return method(sql, params)
        finally:
            end_time = time.time()
            metrics.end_span("sql", end_time=end_time)
            self._notifier.queries.notify(
                query=sql,
                method=getattr(metric, "method", ""),
                route=getattr(metric, "route", ""),
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


def cache_span(fn):
    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        metrics.start_span("cache")
        res = fn(self, *args, **kwargs)
        metrics.end_span("cache")
        return res

    return wrapped


class CacheWrapper:
    def __init__(self, actual_cache):
        self.cache = actual_cache

    def __repr__(self):
        return str("<CacheWrapper for %s>") % repr(self.cache)

    def __contains__(self, key):
        return self.cache.__contains__(key)

    def __getattr__(self, name):
        return getattr(self.cache, name)

    @cache_span
    def add(self, *args, **kwargs):
        return self.cache.add(*args, **kwargs)

    @cache_span
    def get(self, *args, **kwargs):
        return self.cache.get(*args, **kwargs)

    @cache_span
    def set(self, *args, **kwargs):
        return self.cache.set(*args, **kwargs)

    @cache_span
    def touch(self, *args, **kwargs):
        return self.cache.touch(*args, **kwargs)

    @cache_span
    def delete(self, *args, **kwargs):
        return self.cache.delete(*args, **kwargs)

    @cache_span
    def clear(self, *args, **kwargs):
        return self.cache.clear(*args, **kwargs)

    @cache_span
    def has_key(self, *args, **kwargs):
        # Ignore flake8 rules for has_key since we need to support caches
        # that may be using has_key.
        return self.cache.has_key(*args, **kwargs)  # noqa

    @cache_span
    def incr(self, *args, **kwargs):
        return self.cache.incr(*args, **kwargs)

    @cache_span
    def decr(self, *args, **kwargs):
        return self.cache.decr(*args, **kwargs)

    @cache_span
    def get_many(self, *args, **kwargs):
        return self.cache.get_many(*args, **kwargs)

    @cache_span
    def set_many(self, *args, **kwargs):
        self.cache.set_many(*args, **kwargs)

    @cache_span
    def delete_many(self, *args, **kwargs):
        self.cache.delete_many(*args, **kwargs)

    @cache_span
    def incr_version(self, *args, **kwargs):
        return self.cache.incr_version(*args, **kwargs)

    @cache_span
    def decr_version(self, *args, **kwargs):
        return self.cache.decr_version(*args, **kwargs)


class AirbrakeCacheHandler(CacheHandler):
    def __getitem__(self, alias):
        actual_cache = super().__getitem__(alias)
        return CacheWrapper(actual_cache)


cache_handler = AirbrakeCacheHandler()
middleware_cache.caches = cache_handler
cache.caches = cache_handler
