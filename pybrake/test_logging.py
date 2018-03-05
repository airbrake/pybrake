import logging

from .notifier import Notifier
from .logging import LoggingHandler, _LOG_RECORD_ATTRS_TO_COPY
from .test_helper import build_logging_record_error, build_logging_record_exception


def test_logging_handler_record_error():
  record = build_logging_record_error('hello', extra=dict(foo='bar'))

  h = LoggingHandler(notifier=Notifier())
  notice = h.build_notice(record)

  errors = notice['errors']
  assert len(errors) == 1

  error = errors[0]
  assert error['type'] == 'test'
  assert error['message'] == 'hello'

  backtrace = error['backtrace']
  assert len(backtrace) == 1

  frame = backtrace[0]
  assert frame['file'] == '[PROJECT_ROOT]/pybrake/test_helper.py'
  assert frame['function'] == 'build_logging_record_error'
  assert frame['line'] == 14
  assert frame['code'] == {
    12: 'def build_logging_record_error(*args, **kwargs):',
    13: '  logger, dh = logger_dummy_handler()',
    14: '  logger.error(*args, **kwargs)',
    15: '  return dh.record',
    16: '',
  }

  ctx = notice['context']
  assert ctx['severity'] == 'ERROR'
  assert ctx['component'] == 'test_helper'

  params = notice['params']
  assert params['extra'] == {'foo': 'bar'}
  for attr in _LOG_RECORD_ATTRS_TO_COPY:
    assert attr in params


def test_logging_handler_record_exception():
  record = build_logging_record_exception()

  h = LoggingHandler(notifier=Notifier())
  notice = h.build_notice(record)

  errors = notice['errors']
  assert len(errors) == 1

  error = errors[0]
  assert error['type'] == 'ValueError'
  assert error['message'] == 'hello'

  backtrace = error['backtrace']
  assert len(backtrace) == 1

  frame = backtrace[0]
  assert frame['file'] == '[PROJECT_ROOT]/pybrake/test_helper.py'
  assert frame['function'] == 'build_logging_record_exception'
  assert frame['line'] == 21
  assert frame['code'] == {
    19: '  logger, dh = logger_dummy_handler()',
    20: '  try:',
    21: "    raise ValueError('hello')",
    22: '  except Exception as err:',
    23: '    logger.exception(err)',
  }
