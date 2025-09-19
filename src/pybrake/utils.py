import logging
from datetime import datetime, UTC


def time_trunc_minute(time):
    t = datetime.fromtimestamp(time, UTC).replace(second=0, microsecond=0)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_logger():
    _logger = logging.getLogger("pybrake")
    fmter = logging.Formatter(
        "%(asctime)s %(filename)s:%(lineno)d %(name)s %(levelname)s - %(message)s"
    )

    sh = logging.StreamHandler()
    sh.setFormatter(fmter)
    _logger.addHandler(sh)

    return _logger


logger = _get_logger()
