import logging

from .notifier import Notifier
from .code_hunks import get_code_hunk
from .utils import get_django_notifier


def _log_record_attrs():
  record = logging.LogRecord('', logging.ERROR, '', 0, '', None, None)
  attrs = set()
  for k in vars(record).keys():
    attrs.add(k)
  attrs.add('message') # set by Formatter
  return attrs

_LOG_RECORD_ATTRS = _log_record_attrs()


_LOG_RECORD_ATTRS_TO_COPY = [
  'created',
  'msecs',
  'process',
  'processName',
  'relativeCreated',
  'thread',
  'threadName',
]


class LoggingHandler(logging.Handler):
  def __init__(self, notifier=None, level=logging.ERROR, **kwargs):
    logging.Handler.__init__(self, level=level)
    if notifier is None:
      notifier = get_django_notifier() or Notifier(**kwargs)
    self._notifier = notifier

  def emit(self, record):
    try:
      notice = self.build_notice(record)
      self._notifier.send_notice(notice)
    except Exception:
      self.handleError(record)

  def build_notice(self, record):
    notice = dict(
      errors=[self._build_error(record)],
      context=self._build_context(record),
      params=self._build_params(record),
    )
    return notice

  def _build_error(self, record):
    if record.exc_info:
      return self._build_error_from_exc_info(record.exc_info)

    error = dict(
      type=record.name,
      message=record.msg,
      backtrace=self._build_backtrace(record),
    )
    return error

  def _build_error_from_exc_info(self, exc_info):
    cls, err, tb = exc_info
    backtrace = self._notifier._build_backtrace_tb(tb)
    error = dict(
      type=cls.__name__,
      message=str(err),
      backtrace=backtrace,
    )
    return error

  def _build_backtrace(self, record):
    frame = self._notifier._frame_with_code(
      record.pathname, record.funcName, record.lineno)
    backtrace = [frame]
    return backtrace

  def _build_context(self, record):
    ctx = dict(
      severity=record.levelname,
      component=record.module,
    )
    return ctx

  def _build_params(self, record):
    params = dict()

    extra = self._build_extra(record)
    if extra is not None:
      params['extra'] = extra

    for attr in _LOG_RECORD_ATTRS_TO_COPY:
      v = getattr(record, attr)
      if v is not None:
        params[attr] = v
    return params

  def _build_extra(self, record):
    extra = None
    for k, v in vars(record).items():
      if k not in _LOG_RECORD_ATTRS:
        if extra is None:
          extra = {k: v}
        else:
          extra[k] = v
    return extra
