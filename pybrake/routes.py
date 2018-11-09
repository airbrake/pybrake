import base64
import json
from threading import Lock, Timer
from tdigest import TDigest
import requests

from .tdigest import as_bytes

class RouteStat():
  __slots__ = [
    'method',
    'route',
    'statusCode',
    'count',
    'sum',
    'sumsq',
    'time',
    "td",
    "tdigest"
  ]

  @property
  def __dict__(self):
    tdigest = as_bytes(self.td)
    self.tdigest = base64.b64encode(tdigest).decode('ascii')

    return {s: getattr(self, s) for s in self.__slots__ if s != "td"}

  def __init__(self, method='', route='', status_code=0, time=None):
    self.method = method
    self.route = route
    self.statusCode = status_code
    self.count = 0
    self.sum = 0
    self.sumsq = 0
    self.time = time.replace(second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
    self.td = TDigest()
    self.tdigest = None

  def add(self, ms):
    self.count += 1
    self.sum += ms
    self.sumsq += ms * ms
    self.td.update(ms)

class RouteStats():
  def __init__(self, project_id=0, project_key='', host=''):
    self._project_id = project_id
    self._airbrake_headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + project_key,
    }
    self._api_url = "{}/api/v4/projects/{}/routes-stats".format(host, project_id)

    self._thread = None
    self._lock = Lock()
    self._flush_period = 15.0
    self._stats = None

  def _init(self):
    if self._stats is None:
      self._stats = {}
      self._thread = Timer(self._flush_period, self._flush)
      self._thread.start()

  def _flush(self):
    stats = dict()
    with self._lock:
      stats = self._stats
      self._stats = None

    if not stats:
      raise ValueError("Stats is empty")

    stats_json = json.dumps({"routes": [stat.__dict__ for _, stat in stats.items()]})
    requests.post(self._api_url, data=stats_json, headers=self._airbrake_headers)

  def inc_request(self, method='', route='', status_code=0, time=None, ms=0):
    self._init()

    statKey = route_stat_key(method, route, status_code, time)
    with self._lock:
      if statKey in self._stats:
        stat = self._stats.get(statKey)
      else:
        stat = RouteStat(method=method, route=route, status_code=status_code, time=time)
        self._stats[statKey] = stat

      stat.add(ms)

def route_stat_key(method='', route='', status_code=0, time=None):
  tm = time.replace(second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
  return "{}:{}:{}:{}".format(method, route, status_code, tm)
