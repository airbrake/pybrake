import logging
from datetime import datetime


def time_trunc_minute(time):
    t = datetime.utcfromtimestamp(time).replace(second=0, microsecond=0)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_logger():
    l = logging.getLogger("pybrake")
    fmter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmter)
    l.addHandler(sh)

    return l


logger = _get_logger()
