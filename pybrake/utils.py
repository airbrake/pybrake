import logging
from functools import lru_cache

try:
  from django.conf import settings
  _DJANGO = True
except ImportError:
  _DJANGO = False


def _get_logger():
  logger = logging.getLogger('pybrake')
  fmter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  sh = logging.StreamHandler()
  sh.setFormatter(fmter)
  logger.addHandler(sh)

  return logger

logger = _get_logger()


@lru_cache()
def get_django_notifier():
  if not _DJANGO:
    return

  if not hasattr(settings, 'AIRBRAKE'):
    if settings.DEBUG:
      logger.info('pybrake is not configured - set settings.AIRBRAKE')
      return

  from .notifier import Notifier
  return Notifier(**settings.AIRBRAKE)
