import functools

import django
from django.conf import settings
from django.utils.module_loading import import_string

from .global_notifier import get_global_notifier


class AirbrakeMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response
    self._notifier = get_global_notifier()

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
    notice['params']['request'] = dict(
      scheme=request.scheme,
      method=request.method,
      GET=request.GET,
      POST=req_filter.get_post_parameters(request),
      META=dict(request.META),
      FILES=request.FILES,
      COOKIES=request.COOKIES,
    )

    if request.user.is_authenticated:
      user = request.user
      user_info = dict(
        username=user.username,
        email=user.email,
      )

      names = [user.first_name, user.last_name]
      names = [x for x in names if x]
      if names:
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
