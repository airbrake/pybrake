import base64
import json
import threading

from . import metrics
from . import constant
from .backlog import Backlog
from .tdigest import TDigestStat, as_bytes
from .utils import time_trunc_minute


class QueryStat(TDigestStat):

    def __new__(cls, *, query="", method="", route="", time):
        instance = super(QueryStat, cls).__new__(cls)
        instance.__slots__ = instance.__slots__ + (
            "query", "method", "route", "time"
        )
        return instance

    @property
    def __dict__(self):
        tdigest = as_bytes(self.td)
        self.tdigest = base64.b64encode(tdigest).decode("ascii")

        return {s: getattr(self, s) for s in self.__slots__ if s != "td"}

    def __init__(self, *, query="", method="", route="", time=None):
        super().__init__()
        self.query = query
        self.method = method
        self.route = route
        self.time = time_trunc_minute(time)


class QueryStats:
    """
    Query stats are transmitted to the Airbrake site using QueryStats.
    QueryStat will collect query execution statistics such as query start time,
     end time, query statement, query route, and route method.
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

    def notify(
            self, *, query="", method="", route="", start_time=None,
            end_time=None
    ):
        if not self._config.get("performance_stats"):
            return
        if not self._config.get("query_stats"):
            return

        key = query_stat_key(
            query=query, method=method, route=route, time=start_time)
        ms = (end_time - start_time) * 1000

        with self._lock:
            if self._stats is None:
                self._stats = {}
                self._thread = threading.Timer(
                    constant.FLUSH_PERIOD, self._flush)
                self._thread.start()

            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = QueryStat(
                    query=query, method=method, route=route, time=start_time
                )
                self._stats[key] = stat
            stat.add(ms)

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

        out = {"queries": [v.__dict__ for v in stats.values()]}
        if self._env:
            out["environment"] = self._env

        out = json.dumps(out).encode("utf8")
        metrics.send(
            url=self._ab_url(), payload=out,
            headers=self._ab_headers, method="POST",
        )

    def _ab_url(self):
        return f"{self._config.get('apm_host')}/api/v5/projects" \
               f"/{self._project_id}/queries-stats"


def query_stat_key(*, query="", method="", route="", time=None):
    time = time // 60 * 60
    return query, method, route, time
