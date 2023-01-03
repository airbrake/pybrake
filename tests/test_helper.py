import logging
import urllib


def get_exception():
    try:
        raise ValueError("hello")
    except ValueError as err:
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
        raise ValueError("hello")
    except ValueError as err:
        logger.exception(err)
        return dh.record


def logger_dummy_handler():
    class DummyHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.record = None

        def emit(self, record):
            self.record = record

    logger = logging.getLogger("test")
    dh = DummyHandler()
    logger.addHandler(dh)

    return logger, dh


def get_nested_exception():
    try:
        raise get_exception()
    except ValueError as err:
        try:
            raise ValueError("world") from err
        except ValueError as subErr:
            return subErr


def get_exception_in_cython():
    # accumulation_tree is required by tdigest
    from accumulation_tree import AccumulationTree  # pylint: disable=import-outside-toplevel
    t = AccumulationTree(lambda x: x)
    t.insert(1, '1')
    try:
        return t.insert('1', '1')
    except TypeError as err:
        return err


class MockResponse(object):

    def __init__(self, resp_data, code=200, headers=None, msg='OK'):
        if headers is None:
            headers = {}
        self.resp_data = resp_data
        self.code = code
        self.msg = msg
        self.headers = {'content-type': 'text/plain; charset=utf-8'}
        self.headers.update(headers)

    def read(self):
        if self.resp_data == "IOError":
            raise IOError("IOError: for test")
        if self.resp_data == "HTTPError":
            raise urllib.error.HTTPError(*[None] * 5)
        return self.resp_data

    def getcode(self):
        return self.code


class TestBacklog(object):
    def append_stats(self, val, url, retry_count=0):
        pass
