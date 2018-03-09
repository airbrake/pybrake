import logging


def _get_logger():
  l = logging.getLogger('pybrake')
  fmter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  sh = logging.StreamHandler()
  sh.setFormatter(fmter)
  l.addHandler(sh)

  return l

logger = _get_logger()
