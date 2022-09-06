import base64
import json
import threading

from . import constant
from . import metrics
from .backlog import Backlog
from .tdigest import as_bytes, TDigestStatGroups
from .utils import time_trunc_minute


class QueueMetric(metrics.Metric):
    def __init__(self, *, queue=""):
        super().__init__()
        self.queue = queue
        self.start_span(constant.QUEUE_HANDLER, start_time=self.start_time)

    def end(self):
        super().end()
        self.end_span(constant.QUEUE_HANDLER, end_time=self.end_time)

    def _key(self):
        time = self.start_time // 60 * 60
        return (self.queue, time)


class _QueueStat(TDigestStatGroups):

    def __new__(cls, *, queue="", time=None):
        instance = super(_QueueStat, cls).__new__(cls)
        instance.__slots__ = instance.__slots__ + (
            "queue", "time"
        )
        return instance

    def __init__(self, *, queue="", time=None):
        super().__init__()
        self.queue = queue
        self.time = time_trunc_minute(time)

    @property
    def __dict__(self):
        b = as_bytes(self.td)
        self.tdigest = base64.b64encode(b).decode("ascii")
        d = {s: getattr(self, s) for s in self.__slots__ if s != "td"}

        groups = d["groups"]
        for k, v in groups.items():
            groups[k] = v.__dict__

        return d


class QueueStats:
    """
    Queue (background task, cron task) stats are transmitted to the Airbrake
    site using QueueStats.
    QueueStats will collect query execution statistics such as queue task
    start time, end time, task name.
    """

    def __init__(self, *, project_id=0, project_key="", **kwargs):
        self._config = kwargs["config"]

        self._project_id = project_id
        self._ab_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + project_key,
        }
        self._env = kwargs.get("environment")

        self._thread = None
        self._lock = threading.Lock()
        self._stats = None
        self._backlog = None
        if self._config.get('backlog_enabled'):
            if not metrics.APM_Backlog:
                metrics.APM_Backlog = Backlog(
                    header=self._ab_headers,
                    method="POST",
                    maxlen=self._config.get('max_backlog_size'),
                )
            self._backlog = metrics.APM_Backlog

    def notify(self, metric):
        if not self._config.get("performance_stats"):
            return
        if not self._config.get("queue_stats"):
            return
        if len(metric._groups) <= 1:
            return

        metric.end()

        key = metric._key()
        with self._lock:
            if self._stats is None:
                self._stats = {}
                self._thread = threading.Timer(constant.FLUSH_PERIOD,
                                               self._flush)
                self._thread.start()

            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = _QueueStat(queue=metric.queue, time=metric.start_time)
                self._stats[key] = stat

            total_ms = (metric.end_time - metric.start_time) * 1000
            stat.add_groups(total_ms, metric._groups)

    def _flush(self):
        """
        TODO: Below disabled pylint will remove in refactoring
        """
        # pylint: disable=too-many-branches
        stats = None
        with self._lock:
            stats = self._stats
            self._stats = None

        if not stats:
            raise ValueError("stats is empty")

        out = {"queues": [v.__dict__ for v in stats.values()]}
        if self._env:
            out["environment"] = self._env

        out_json = json.dumps(out).encode("utf8")
        metrics.send(
            url=self._ab_url(), headers=self._ab_headers,
            payload=out_json, method="POST",
        )

    def _ab_url(self):
        return f"{self._config.get('apm_host')}/api/v5/projects/{self._project_id}/queues-stats"
