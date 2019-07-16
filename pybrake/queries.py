import base64
import json
from threading import Lock, Timer
import urllib.request
import urllib.error

from .tdigest import tdigest_supported, TDigestStat, as_bytes
from .utils import logger, time_trunc_minute


_FLUSH_PERIOD = 15


class QueryStat(TDigestStat):
    __slots__ = [
        "query",
        "method",
        "route",
        "count",
        "sum",
        "sumsq",
        "time",
        "td",
        "tdigest",
    ]

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
        self._ab_url = "{}/api/v5/projects/{}/queries-stats".format(host, project_id)
        self._env = kwargs.get("environment")

        self._thread = None
        self._lock = Lock()
        self._stats = None

    def notify(self, *, query="", method="", route="", start_time=None, end_time=None):
        if self._apm_disabled:
            return

        if self._stats is None:
            self._stats = {}
            self._thread = Timer(_FLUSH_PERIOD, self._flush)
            self._thread.start()

        key = query_stat_key(query=query, method=method, route=route, time=start_time)
        ms = (end_time - start_time) * 1000

        with self._lock:
            if key in self._stats:
                stat = self._stats[key]
            else:
                stat = QueryStat(
                    query=query, method=method, route=route, time=start_time
                )
                self._stats[key] = stat
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


def query_stat_key(*, query="", method="", route="", time=None):
    time = time // 60 * 60
    return (query, method, route, time)
