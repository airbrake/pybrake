import base64
import time as pytime
import json
import threading
import urllib.request
import urllib.error

from .tdigest import as_bytes, TDigestStat
from .utils import logger, time_trunc_minute

_FLUSH_PERIOD = 15

threadLocal = threading.local()


class RouteBreakdown(TDigestStat):
    __slots__ = [
        "method",
        "route",
        "responseType",
        "time",
        "count",
        "sum",
        "sumsq",
        "td",
        "tdigest",
        "groups",
    ]

    def __init__(self, *, method="", route="", responseType="", time=None):
        super().__init__()
        self.method = method
        self.route = route
        self.responseType = responseType
        self.time = time_trunc_minute(time)
        self.groups = {}

    @property
    def __dict__(self):
        b = as_bytes(self.td)
        self.tdigest = base64.b64encode(b).decode("ascii")
        d = {s: getattr(self, s) for s in self.__slots__ if s != "td"}

        groups = d["groups"]
        for k, v in groups.items():
            groups[k] = v.__dict__

        return d

    def add_groups(self, groups):
        for name, ms in groups.items():
            stat = self.groups.get(name)
            if stat is None:
                stat = TDigestStat()
                self.groups[name] = stat
            stat.add(ms)


class RouteBreakdowns:
    def __init__(self, *, project_id=0, project_key="", host="", **kwargs):
        self._project_id = project_id
        self._ab_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + project_key,
        }
        self._ab_url = "{}/api/v5/projects/{}/routes-breakdowns".format(
            host, project_id
        )
        self._env = kwargs.get("environment")

        self._thread = None
        self._lock = threading.Lock()
        self._stats = None

    def notify(self, trace):
        if trace.status_code < 200 or (
            trace.status_code >= 300 and trace.status_code < 400
        ):
            return

        if self._stats is None:
            self._stats = {}
            self._thread = threading.Timer(_FLUSH_PERIOD, self._flush)
            self._thread.start()

        key = trace.key()
        with self._lock:
            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = RouteBreakdown(
                    method=trace.method,
                    route=trace.route,
                    responseType=trace.response_type,
                    time=trace.start_time,
                )
                self._stats[key] = stat

            ms = (trace.end_time - trace.start_time) * 1000
            stat.add(ms)
            stat.add_groups(trace.groups)

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
        req = urllib.request.Request(self._ab_url, data=out, headers=self._ab_headers)

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


class RouteTrace:
    def __init__(self, *, method="", route="", status_code=0, content_type=""):
        self.method = method
        self.route = route
        self.status_code = status_code
        self.content_type = content_type
        self.start_time = pytime.time()
        self.end_time = None
        self.spans = {}
        self.groups = {}

    def key(self):
        time = self.start_time // 60 * 60
        return (self.method, self.route, self.response_type, time)

    @property
    def response_type(self):
        if self.status_code >= 400:
            return "error"
        return self.content_type.split(";")[0].split("/")[-1]

    def span(self, name):
        return RouteSpan(trace=self, name=name)

    def start_span(self, name):
        if name in self.spans:
            raise ValueError("span={} is already started".format(name))

        span = self.span(name)
        self.spans[name] = span

    def end_span(self, name):
        if name not in self.spans:
            raise ValueError("span={} does not exist".format(name))

        span = self.spans[name]
        self.spans.pop(name)
        span.end()

    def inc_group(self, name, ms):
        self.groups[name] = self.groups.get(name, 0) + ms


class RouteSpan:
    def __init__(self, *, trace=None, name=""):
        self.trace = trace
        self.name = name
        self.start_time = pytime.time()

    def end(self):
        end_time = pytime.time()
        ms = (end_time - self.start_time) * 1000
        self.trace.inc_group(self.name, ms)
