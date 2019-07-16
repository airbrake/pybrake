import base64
import time as pytime
import json
import threading
import urllib.request
import urllib.error

from .tdigest import tdigest_supported, as_bytes, TDigestStat
from .utils import logger, time_trunc_minute

_FLUSH_PERIOD = 15

threadLocal = threading.local()


class _RouteBreakdown(TDigestStat):
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

    def add_groups(self, total_ms, groups):
        self.add(total_ms)

        sum_ms = 0
        for name, ms in groups.items():
            sum_ms += ms
            self.add_group(name, ms)

        if sum_ms > total_ms:
            logger.error("sum=%d > total=%d", sum_ms, total_ms)
            self.add_group("other", 0)
        else:
            self.add_group("other", total_ms - sum_ms)

    def add_group(self, name, ms):
        stat = self.groups.get(name)
        if stat is None:
            stat = TDigestStat()
            self.groups[name] = stat
        stat.add(ms)


class RouteBreakdowns:
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
        self._ab_url = "{}/api/v5/projects/{}/routes-breakdowns".format(
            host, project_id
        )
        self._env = kwargs.get("environment")

        self._thread = None
        self._lock = threading.Lock()
        self._stats = None

    def notify(self, trace):
        if self._apm_disabled:
            return

        if trace.status_code < 200 or (
            trace.status_code >= 300 and trace.status_code < 400
        ):
            return

        if self._stats is None:
            self._stats = {}
            self._thread = threading.Timer(_FLUSH_PERIOD, self._flush)
            self._thread.start()

        key = trace._key()
        with self._lock:
            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = _RouteBreakdown(
                    method=trace.method,
                    route=trace.route,
                    responseType=trace.response_type,
                    time=trace.start_time,
                )
                self._stats[key] = stat

            total_ms = (trace.end_time - trace.start_time) * 1000
            stat.add_groups(total_ms, trace._groups)

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
            self._ab_url, data=out_json, headers=self._ab_headers, method="PUT"
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


class RouteTrace:
    def __init__(self, *, method="", route="", status_code=0, content_type=""):
        self.method = method
        self.route = route
        self.status_code = status_code
        self.content_type = content_type

        self.start_time = pytime.time()
        self.end_time = None

        self._spans = {}
        self._curr_span = None

        self._groups = {}

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

    def _new_span(self, name, **kwargs):
        return RouteSpan(trace=self, name=name, **kwargs)

    def start_span(self, name, *, start_time=None):
        if self._curr_span is not None:
            if self._curr_span.name == name:
                self._curr_span._level += 1
                return
            self._curr_span._pause()

        span = self._spans.get(name)
        if span is None:
            span = self._new_span(name, start_time=start_time)
            self._spans[name] = span
        else:
            span._resume()

        span._parent = self._curr_span
        self._curr_span = span

    def finish_span(self, name, *, end_time=None):
        if self._curr_span is not None and self._curr_span.name == name:
            if self._finish_span(self._curr_span):
                self._curr_span = self._curr_span._parent
                if self._curr_span is not None:
                    self._curr_span._resume()
            return

        span = self._spans.get(name)
        if span is None:
            logger.error("pybrake: span=%s does not exist", name)
            return
        self._finish_span(span, end_time=end_time)

    def _finish_span(self, span, *, end_time=None):
        if span._level > 0:
            span._level -= 1
            return False

        span.end(end_time=end_time)
        self._spans.pop(span.name)
        return True

    def _inc_group(self, name, ms):
        self._groups[name] = self._groups.get(name, 0) + ms


class RouteSpan:
    def __init__(self, *, trace=None, name="", start_time=None):
        self._trace = trace
        self._parent = None

        self.name = name
        if start_time is not None:
            self.start_time = start_time
        else:
            self.start_time = pytime.time()
        self.end_time = None

        self._dur = 0
        self._level = 0

    def end(self, end_time=None):
        if end_time is not None:
            self.end_time = end_time
        else:
            self.end_time = pytime.time()
        self._dur += (self.end_time - self.start_time) * 1000
        self._trace._inc_group(self.name, self._dur)
        self._trace = None

    def _pause(self):
        if self._paused():
            return
        self._dur += (pytime.time() - self.start_time) * 1000
        self.start_time = 0

    def _paused(self):
        return self.start_time == 0

    def _resume(self):
        if not self._paused():
            return
        self.start_time = pytime.time()


def set_trace(trace):
    threadLocal._ab_trace = trace


def get_trace():
    return getattr(threadLocal, "_ab_trace", None)


def start_span(name, **kwargs):
    if hasattr(threadLocal, "_ab_trace"):
        threadLocal._ab_trace.start_span(name, **kwargs)


def finish_span(name, **kwargs):
    if hasattr(threadLocal, "_ab_trace"):
        threadLocal._ab_trace.finish_span(name, **kwargs)
