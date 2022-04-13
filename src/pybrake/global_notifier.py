from functools import lru_cache

from .utils import logger


try:
    from django.conf import settings

    _DJANGO = True
except ImportError:
    _DJANGO = False


@lru_cache()
def get_global_notifier():
    if not _DJANGO:
        return None

    if not hasattr(settings, "AIRBRAKE"):
        if settings.DEBUG:
            logger.info("pybrake is not configured - set settings.AIRBRAKE")
            return None

    from .notifier import Notifier  # pylint: disable=import-outside-toplevel

    return Notifier(**settings.AIRBRAKE)
