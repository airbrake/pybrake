import base64
import json
import time as pytime
from threading import Lock, Timer
import urllib.request
import urllib.error

from .tdigest import tdigest_supported, as_bytes, TDigestStat
from .utils import logger, time_trunc_minute
from .route_trace import RouteBreakdowns


_FLUSH_PERIOD = 15


class _Routes:
    def __init__(self, **kwargs):
        self._apm_disabled = (
            kwargs.get("apm_disabled", False) or not tdigest_supported()
        )
        if self._apm_disabled:
            return

        self.stats = RouteStats(**kwargs)
        self.breakdowns = RouteBreakdowns(**kwargs)

    def notify(self, trace):
        if self._apm_disabled:
            return

        if trace.end_time is None:
            trace.end_time = pytime.time()

        self.stats.notify(trace)
        self.breakdowns.notify(trace)


class RouteStat(TDigestStat):
    __slots__ = [
        "method",
        "route",
        "statusCode",
        "time",
        "count",
        "sum",
        "sumsq",
        "td",
        "tdigest",
    ]

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
    def __init__(self, *, project_id=0, project_key="", host="", **kwargs):
        self._apm_disabled = (
            kwargs.get("apm_disabled", False) or not tdigest_supported()
        )
        if self._apm_disabled:
            return

        self._project_id = project_id
        self._ab_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + project_key,
        }
        self._ab_url = "{}/api/v5/projects/{}/routes-stats".format(host, project_id)
        self._env = kwargs.get("environment")

        self._thread = None
        self._lock = Lock()
        self._stats = None

    def notify(self, trace):
        if self._apm_disabled:
            return

        if self._stats is None:
            self._stats = {}
            self._thread = Timer(_FLUSH_PERIOD, self._flush)
            self._thread.start()

        key = route_stat_key(
            method=trace.method,
            route=trace.route,
            status_code=trace.status_code,
            time=trace.start_time,
        )
        with self._lock:
            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = RouteStat(
                    method=trace.method,
                    route=trace.route,
                    status_code=trace.status_code,
                    time=trace.start_time,
                )
                self._stats[key] = stat

            ms = (trace.end_time - trace.start_time) * 1000
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
            self._ab_url, data=out, headers=self._ab_headers, method="PUT"
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


def route_stat_key(*, method="", route="", status_code=0, time=None):
    time = time // 60 * 60
    return (method, route, status_code, time)
