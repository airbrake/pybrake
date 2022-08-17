import time
from collections import deque
from threading import Timer

from . import metrics


class Backlog(Timer):
    def __init__(self, interval, url, method, header, maxlen=100,
                 test_backlog_enabled=False, args=None, kwargs=None):
        super().__init__(interval, self.send, args, kwargs)
        self._backlog = deque(maxlen=maxlen)
        self._url = url
        self._method = method
        self._header = header
        self._test_backlog_enabled = test_backlog_enabled

    def send(self):
        # pop out queue items every 1 sec
        # (please ignore empty deque for now)
        while len(self._backlog) > 0:
            payload = self._backlog.popleft()
            if self._test_backlog_enabled:
                break
            metrics.send(url=self._url, headers=self._header,
                         method=self._method, payload=payload,
                         backlog=self)
            time.sleep(self.interval)

    def append_stats(self, val):
        self._backlog.append(val)
        if not self._started.is_set():
            self.start()
