import time
from collections import deque
from threading import Timer

from . import metrics


class Backlog(Timer):
    def __init__(self, interval, url, method, header, maxlen=100,
                 error_notice=False, notifier=None, args=None, kwargs=None):
        super().__init__(interval, self.send, args, kwargs)
        self._backlog = deque(maxlen=maxlen)
        self._url = url
        self._method = method
        self._header = header
        self._error_notice = error_notice
        self._notifier = notifier

    def send(self):
        # pop out queue items every 1 sec
        # (please ignore empty deque for now)
        while len(self._backlog) > 0:
            payload = self._backlog.popleft()
            if not self._error_notice:
                metrics.send(url=self._url, headers=self._header,
                             method=self._method, payload=payload.get('data'),
                             backlog=self,
                             retry_count=payload.get('retry_count') + 1
                             )
            else:
                metrics.send_notice(self._notifier, notice=payload.get('data'),
                                    url=self._url, headers=self._header,
                                    backlog=self, method=self._method,
                                    retry_count=payload.get('retry_count')+1
                                    )
            time.sleep(self.interval)

    def append_stats(self, val, retry_count=0):
        self._backlog.append({'retry_count': retry_count, 'data': val})
        if not self._started.is_set():
            self.start()
