import time
import functools

from django.conf import settings
from django.utils.module_loading import import_string

from .global_notifier import get_global_notifier


class AirbrakeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._notifier = get_global_notifier()

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        if request.resolver_match:
            route = request.resolver_match.view_name
        else:
            route = "UNKNOWN"
        self._notifier.routes.notify(
            method=request.method,
            route=route,
            status_code=response.status_code,
            start_time=start_time,
            end_time=time.time(),
        )

        return response

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
