import logging

from .notifier import Notifier
from .global_notifier import get_global_notifier


def _log_record_attrs():
    record = logging.LogRecord("", logging.ERROR, "", 0, "", None, None)
    attrs = set()
    for k in vars(record).keys():
        attrs.add(k)
    attrs.add("message")  # set by Formatter
    return attrs


_LOG_RECORD_ATTRS = _log_record_attrs()


_LOG_RECORD_ATTRS_TO_COPY = [
    "created",
    "msecs",
    "process",
    "processName",
    "relativeCreated",
    "thread",
    "threadName",
]


class LoggingHandler(logging.Handler):
    def __init__(self, notifier=None, level=logging.ERROR, **kwargs):
        logging.Handler.__init__(self, level=level)
        if notifier is None:
            notifier = get_global_notifier() or Notifier(**kwargs)
        self._notifier = notifier

    def emit(self, record):
        try:
            notice = self.build_notice(record)
            self._notifier.send_notice(notice)
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)

    def build_notice(self, record):
        notice = self._notifier.build_notice(None)
        notice["errors"].append(self._build_error(record))
        self._update_context(notice["context"], record)
        self._update_params(notice["params"], record)
        return notice

    def _build_error(self, record):
        if record.exc_info:
            return self._build_error_from_exc_info(record.exc_info)

        error = dict(
            type=record.name,
            message=record.getMessage(),
            backtrace=self._build_backtrace(record),
        )
        return error

    def _build_error_from_exc_info(self, exc_info):
        cls, err, tb = exc_info
        backtrace = self._notifier._build_backtrace_tb(tb)
        error = dict(type=cls.__name__, message=str(err), backtrace=backtrace)
        return error

    def _build_backtrace(self, record):
        frame = self._notifier._frame_with_code(
            record.pathname, record.funcName, record.lineno
        )
        backtrace = [frame]
        return backtrace

    def _update_context(self, context, record):
        context["messagePattern"] = record.msg
        context["severity"] = record.levelname
        context["component"] = record.module

    def _update_params(self, params, record):
        extra = self._build_extra(record)
        if extra is not None:
            params["extra"] = extra

        for attr in _LOG_RECORD_ATTRS_TO_COPY:
            v = getattr(record, attr)
            if v is not None:
                params[attr] = v

    def _build_extra(self, record):
        extra = None
        for k, v in vars(record).items():
            if k not in _LOG_RECORD_ATTRS:
                if extra is None:
                    extra = {k: v}
                else:
                    extra[k] = v
        return extra
