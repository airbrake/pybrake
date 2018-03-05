from functools import lru_cache

from .notifier import Notifier


@lru_cache()
def get_django_notifier():
  try:
    from django.conf import settings
  except ImportError:
    return

  if not hasattr(settings, 'AIRBRAKE'):
    if settings.DEBUG:
      logger.info('pybrake is not configured - set settings.AIRBRAKE')
      return

  return Notifier(**settings.AIRBRAKE)
