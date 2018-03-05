import logging
from functools import lru_cache


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

  from .notifier import Notifier
  return Notifier(**settings.AIRBRAKE)


@lru_cache()
def get_logger():
  logger = logging.getLogger('pybrake')
  fmter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  sh = logging.StreamHandler()
  sh.setFormatter(fmter)
  logger.addHandler(sh)

  return logger
