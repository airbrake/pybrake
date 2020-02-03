import logging


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
        except ValueError as err:
            return err


def get_exception_in_cython():
    # accumulation_tree is required by tdigest
    from accumulation_tree import AccumulationTree  # pylint: disable=import-outside-toplevel
    t = AccumulationTree(lambda x: x)
    t.insert(1, '1')
    try:
        return t.insert('1', '1')
    except TypeError as err:
        return err
