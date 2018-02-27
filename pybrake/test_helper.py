def get_exception():
  try:
    raise ValueError('hello')
  except Exception as err:
    return err


def build_notice_from_str(notifier, s):
    return notifier.build_notice(s)


def build_logging_record_error(*args, **kwargs):
  logger, dh = logger_dummy_handler()
  logger.error(*args, **kwargs)
  return dh.record


def build_logging_record_exception():
  logger, dh = logger_dummy_handler()
  try:
    raise ValueError('hello')
  except Exception as err:
    logger.exception(err)
    return dh.record


def logger_dummy_handler():
  import logging

  class DummyHandler(logging.Handler):
    def emit(self, record):
      self.record = record

  logger = logging.getLogger('test')
  dh = DummyHandler()
  logger.addHandler(dh)

  return logger, dh
