import base64
import json
from threading import Lock, Timer
import urllib.request
import urllib.error

from . import metrics
from .tdigest import as_bytes, TDigestStat
from .utils import logger, time_trunc_minute
from .route_metric import RouteBreakdowns


class _Routes:
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
    __slots__ = TDigestStat.__slots__ + ("method", "route", "statusCode", "time")

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
                self._thread = Timer(metrics.FLUSH_PERIOD, self._flush)
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
        req = urllib.request.Request(
            self._ab_url(), data=out, headers=self._ab_headers, method="POST"
        )

        try:
            resp = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as err:
            resp = err
        except Exception as err:  # pylint: disable=broad-except
            logger.error(err)
            return

        try:
            body = resp.read()
        except IOError as err:
            logger.error(err)
            return

        if 200 <= resp.code < 300:
            return

        if not 400 <= resp.code < 500:
            err = "airbrake: unexpected response status_code={}".format(resp.code)
            logger.error(err)
            return

        if resp.code == 429:
            return

        try:
            body = body.decode("utf-8")
        except UnicodeDecodeError as err:
            logger.error(err)
            return

        try:
            in_data = json.loads(body)
        except ValueError as err:  # json.JSONDecodeError requires Python 3.5+
            logger.error(err)
            return

        if "message" in in_data:
            logger.error(in_data["message"])
            return

    def _ab_url(self):
        return "{}/api/v5/projects/{}/routes-stats".format(
            self._config.get("apm_host"), self._project_id
        )

def route_stat_key(*, method="", route="", status_code=0, time=None):
    time = time // 60 * 60
    return (method, route, status_code, time)
