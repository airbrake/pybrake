from collections import deque
from threading import Timer

from . import metrics


class FailedStats(Timer):
    def __init__(self, interval, function, url, method,
                 header, maxlen=100, args=None, kwargs=None):
        super(FailedStats, self).__init__(interval, function, args, kwargs)
        self._failed_stats = deque(maxlen=maxlen)
        self._url = url
        self._method = method
        self._header = header
        self.start()

    def run(self):
        # pop out queue items every 1 sec
        # (please ignore empty deque for now)
        while len(self._failed_stats) > 0:
            payload = self._failed_stats.popleft()
            metrics.send(url=self._url, headers=self._header,
                         method=self._method, payload=payload)

    def append_stats(self, val):
        self._failed_stats.append(val)
