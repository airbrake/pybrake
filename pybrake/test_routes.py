import calendar
import json
import requests_mock

from .routes import RouteStats


def test_route_stat():
    def _request_callback(request, context):
        return request.body

    route_stats = RouteStats(project_id=1, project_key="token1", host="http://test.com")
    route_stats._flush_period = 1

    with requests_mock.mock() as m:
        url = "http://test.com/api/v5/projects/1/routes-stats"
        m.post(url, json=_request_callback)

        start_time = calendar.timegm((2000, 1, 1, 0, 0, 0, 0, 0, 0))
        end_time = start_time + 0.123
        route_stats.notify("GET", "ping", 200, start_time, end_time)
        route_stats.notify("GET", "pong", 200, start_time, end_time)
        route_stats.notify("GET", "pong", 200, start_time, end_time)

        route_stats._thread.join()
        assert m.call_count == 1

        hist = m.request_history[0]
        headers = hist.headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer token1"

        route_stats = json.loads(hist.text)
        route_stats = sorted(route_stats["routes"], key=lambda k: k["route"])
        assert route_stats == [
            {
                "method": "GET",
                "route": "ping",
                "statusCode": 200,
                "count": 1,
                "sum": 123,
                "sumsq": 15129,
                "time": "2000-01-01T00:00:00Z",
                "tdigest": "AAAAAkA5AAAAAAAAAAAAAUL2AAAB",
            },
            {
                "method": "GET",
                "route": "pong",
                "statusCode": 200,
                "count": 2,
                "sum": 246,
                "sumsq": 30258,
                "time": "2000-01-01T00:00:00Z",
                "tdigest": "AAAAAkA5AAAAAAAAAAAAAUL2AAAC",
            },
        ]
