from datetime import datetime
import json
import requests_mock

from .routes import RouteStats

def test_route_stat():
  def _request_callback(request, context):
    return request.body

  route_stats = RouteStats(
    project_id=1, project_key="token1", host='http://test.com')
  route_stats._flush_period = 1

  with requests_mock.mock() as m:
    url = "http://test.com/api/v4/projects/1/routes-stats"
    m.post(url, json=_request_callback)

    tm = datetime(2000, 1, 1, 0, 0)
    route_stats.inc_request("GET", "ping", 200, tm, 123)
    route_stats.inc_request("GET", "pong", 200, tm, 123)
    route_stats.inc_request("GET", "pong", 200, tm, 123)

    route_stats._thread.join()
    assert m.call_count == 1

    hist = m.request_history[0]
    headers = hist.headers
    assert headers['Content-Type'] == 'application/json'
    assert headers['Authorization'] == 'Bearer token1'

    route_stats = json.loads(hist.text)
    route_stats = sorted(route_stats["routes"], key=lambda k: k['route'])
    assert route_stats == [{
      'method': 'GET',
      'route': 'ping',
      'statusCode': 200,
      'count': 1,
      'sum': 123,
      'sumsq': 15129,
      'time': "2000-01-01T00:00:00Z",
    }, {
      'method': 'GET',
      'route': 'pong',
      'statusCode': 200,
      'count': 2,
      'sum': 246,
      'sumsq': 30258,
      'time': "2000-01-01T00:00:00Z",
    }]
