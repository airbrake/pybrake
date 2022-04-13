import threading
from contextlib import contextmanager
import time as pytime

from .utils import logger


threadLocal = threading.local()

FLUSH_PERIOD = 15
_METRIC_KEY = "_ab_metric"


@contextmanager
def activated_metric(metric):
    set_active(metric)
    yield
    set_active(None)


def set_active(metric):
    setattr(threadLocal, _METRIC_KEY, metric)


def get_active():
    return getattr(threadLocal, _METRIC_KEY, None)


def start_span(name, **kwargs):
    metric = get_active()
    if metric is not None:
        metric.start_span(name, **kwargs)


def end_span(name, **kwargs):
    metric = get_active()
    if metric is not None:
        metric.end_span(name, **kwargs)


class Metric:
    def __init__(self):
        self.start_time = pytime.time()
        self.end_time = None

        self._spans = {}
        self._curr_span = None

        self._groups = {}

    def end(self):
        if self.end_time is None:
            self.end_time = pytime.time()

    def _new_span(self, name, **kwargs):
        return Span(metric=self, name=name, **kwargs)

    def start_span(self, name, *, start_time=None):
        if self._curr_span is not None:
            if self._curr_span.name == name:
                self._curr_span._level += 1
                return
            self._curr_span._pause()

        span = self._spans.get(name)
        if span is None:
            span = self._new_span(name, start_time=start_time)
            self._spans[name] = span
        else:
            span._resume()

        span._parent = self._curr_span
        self._curr_span = span

    def end_span(self, name, *, end_time=None):
        if self._curr_span is not None and self._curr_span.name == name:
            if self._end_span(self._curr_span):
                self._curr_span = self._curr_span._parent
                if self._curr_span is not None:
                    self._curr_span._resume()
            return

        span = self._spans.get(name)
        if span is None:
            logger.error("pybrake: span=%s does not exist", name)
            return
        self._end_span(span, end_time=end_time)

    def _end_span(self, span, *, end_time=None):
        if span._level > 0:
            span._level -= 1
            return False

        span.end(end_time=end_time)
        self._spans.pop(span.name)
        return True

    def _inc_group(self, name, ms):
        self._groups[name] = self._groups.get(name, 0) + ms


class Span:
    def __init__(self, *, metric=None, name="", start_time=None):
        self._metric = metric
        self._parent = None

        self.name = name
        if start_time is not None:
            self.start_time = start_time
        else:
            self.start_time = pytime.time()
        self.end_time = None

        self._dur = 0
        self._level = 0

    def end(self, end_time=None):
        if end_time is not None:
            self.end_time = end_time
        else:
            self.end_time = pytime.time()
        self._dur += (self.end_time - self.start_time) * 1000
        self._metric._inc_group(self.name, self._dur)
        self._metric = None

    def _pause(self):
        if self._paused():
            return
        self._dur += (pytime.time() - self.start_time) * 1000
        self.start_time = 0

    def _paused(self):
        return self.start_time == 0

    def _resume(self):
        if not self._paused():
            return
        self.start_time = pytime.time()
