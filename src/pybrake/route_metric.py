import base64
import json
import threading
import urllib.request
import urllib.error

from . import metrics
from .tdigest import as_bytes, TDigestStatGroups
from .utils import logger, time_trunc_minute


class _RouteBreakdown(TDigestStatGroups):

    def __new__(cls, *, method="", route="", responseType="", time=None):
        instance = super(_RouteBreakdown, cls).__new__(cls)
        instance.__slots__ = instance.__slots__ + (
            "method", "route", "responseType", "time"
        )
        return instance

    def __init__(self, *, method="", route="", responseType="", time=None):
        super().__init__()
        self.method = method
        self.route = route
        self.responseType = responseType
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


class RouteBreakdowns:
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

    def notify(self, metric):
        if not self._config.get("performance_stats"):
            return

        if (
            metric.status_code < 200
            or (metric.status_code >= 300 and metric.status_code < 400)
            or metric.status_code == 404
            or len(metric._groups) <= 1
        ):
            return

        if self._stats is None:
            self._stats = {}
            self._thread = threading.Timer(metrics.FLUSH_PERIOD, self._flush)
            self._thread.start()

        key = metric._key()
        with self._lock:
            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = _RouteBreakdown(
                    method=metric.method,
                    route=metric.route,
                    responseType=metric.response_type,
                    time=metric.start_time,
                )
                self._stats[key] = stat

            total_ms = (metric.end_time - metric.start_time) * 1000
            stat.add_groups(total_ms, metric._groups)

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

        out_json = json.dumps(out).encode("utf8")
        req = urllib.request.Request(
            self._ab_url(), data=out_json, headers=self._ab_headers, method="POST"
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
            err = f"airbrake: unexpected response status_code={resp.code}"
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
        return f"{self._config.get('apm_host')}/api/v5/projects/" \
               f"{self._project_id}/routes-breakdowns"


HTTP_HANDLER = "http.handler"


class RouteMetric(metrics.Metric):
    def __init__(self, *, method="", route="", status_code=0, content_type=""):
        super().__init__()
        self.method = method
        self.route = route
        self.status_code = status_code
        self.content_type = content_type
        self.start_span(HTTP_HANDLER, start_time=self.start_time)

    def end(self):
        super().end()
        self.end_span(HTTP_HANDLER, end_time=self.end_time)

    def _key(self):
        time = self.start_time // 60 * 60
        return (self.method, self.route, self.response_type, time)

    @property
    def response_type(self):
        if self.status_code >= 500:
            return "5xx"
        if self.status_code >= 400:
            return "4xx"
        return self.content_type.split(";")[0].split("/")[-1]
