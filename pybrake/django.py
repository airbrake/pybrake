import sys
import logging
import functools

import django
from django.conf import settings
from django.views.debug import SafeExceptionReporterFilter
from django.utils.module_loading import import_string

from .utils import get_django_notifier


class AirbrakeMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response
    self._notifier = get_django_notifier()

  def __call__(self, request):
    response = self.get_response(request)
    return response

  def process_exception(self, request, exception):
    if not self._notifier:
      return

    notice = self._notifier.build_notice(exception)

    ctx = notice['context']
    ctx['url'] = request.build_absolute_uri()

    versions = notice['context'].get('versions', {})
    versions['django'] = django.get_version()
    ctx['versions'] = versions

    req_filter = get_exception_reporter_filter(request)
    notice['params'].update(dict(
      request_scheme=request.scheme,
      request_method=request.method,
      request_GET=request.GET,
      request_POST=req_filter.get_post_parameters(request),
      request_META=dict(request.META),
      request_FILES=request.FILES,
      request_COOKIES=request.COOKIES,
    ))

    if request.user.is_authenticated:
      user = request.user
      user_info = dict(
        username=user.username,
        email=user.email,
      )

      names = [user.first_name, user.last_name]
      names = [x for x in names if x]
      if len(names) > 0:
        user_info['name'] = ' '.join(names)

      notice['context']['user'] = user_info

    self._notifier.send_notice(notice)


@functools.lru_cache()
def get_default_exception_reporter_filter():
    # Instantiate the default filter for the first time and cache it.
    return import_string(settings.DEFAULT_EXCEPTION_REPORTER_FILTER)()


def get_exception_reporter_filter(request):
    default_filter = get_default_exception_reporter_filter()
    return getattr(request, 'exception_reporter_filter', default_filter)
