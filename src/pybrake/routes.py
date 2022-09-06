import base64
import json
from threading import Lock, Timer

from . import metrics
from . import constant
from .backlog import Backlog
from .route_metric import RouteBreakdowns
from .tdigest import as_bytes, TDigestStat
from .utils import time_trunc_minute


class _Routes:
    """
    Routes and route breakdown stats are transmitted to the Airbrake site
    using _Routes. When the notifier is initialized, it will initialize the
    RouteStats and RouteBreakdowns instances.
    """

    def __init__(self, **kwargs):
        self.config = kwargs["config"]
        self.stats = RouteStats(**kwargs)
        self.breakdowns = RouteBreakdowns(**kwargs)

    def notify(self, metric):
        if not self.config.get("performance_stats"):
            return

        metric.end()
        self.stats.notify(metric)
        self.breakdowns.notify(metric)


class RouteStat(TDigestStat):
    """
    RouteStat will collect request execution statistics such as request start
    time, end time, request endpoint, response status code, and route method.
    """

    def __new__(cls, *, method="", route="", status_code=0, time):
        instance = super(RouteStat, cls).__new__(cls)
        instance.__slots__ = instance.__slots__ + (
            "method", "route", "statusCode", "time"
        )
        return instance

    @property
    def __dict__(self):
        b = as_bytes(self.td)
        self.tdigest = base64.b64encode(b).decode("ascii")
        return {s: getattr(self, s) for s in self.__slots__ if s != "td"}

    def __init__(self, *, method="", route="", status_code=0, time=None):
        super().__init__()
        self.method = method
        self.route = route
        self.statusCode = status_code
        self.time = time_trunc_minute(time)


class RouteStats:
    def __init__(self, *, project_id=0, project_key="", **kwargs):
        self._config = kwargs["config"]

        self._project_id = project_id
        self._ab_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + project_key,
        }
        self._env = kwargs.get("environment")

        self._thread = None
        self._lock = Lock()
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

        key = route_stat_key(
            method=metric.method,
            route=metric.route,
            status_code=metric.status_code,
            time=metric.start_time,
        )
        with self._lock:
            if self._stats is None:
                self._stats = {}
                self._thread = Timer(constant.FLUSH_PERIOD, self._flush)
                self._thread.start()

            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = RouteStat(
                    method=metric.method,
                    route=metric.route,
                    status_code=metric.status_code,
                    time=metric.start_time,
                )
                self._stats[key] = stat

            ms = (metric.end_time - metric.start_time) * 1000
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

        out = {"routes": [v.__dict__ for v in stats.values()]}
        if self._env:
            out["environment"] = self._env

        out = json.dumps(out).encode("utf8")
        metrics.send(
            url=self._ab_url(), headers=self._ab_headers,
            method="POST", payload=out,
        )

    def _ab_url(self):
        return f"{self._config.get('apm_host')}/api/v5/projects" \
               f"/{self._project_id}/routes-stats"


def route_stat_key(*, method="", route="", status_code=0, time=None):
    time = time // 60 * 60
    return method, route, status_code, time
