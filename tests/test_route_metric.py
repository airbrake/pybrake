import time

import pytest
import pybrake.metrics as metrics
from pybrake.route_metric import RouteMetric, _RouteBreakdown, RouteBreakdowns
from pybrake.routes import _Routes, RouteStats, RouteStat, route_stat_key

metrics.FLUSH_PERIOD = 0
CONFIG = {
    "config": {
        "performance_stats": False,
        "error_host": "http://localhost:5000",
        "apm_host": "http://localhost:5000",
    }
}


def _test_setup(config: dict):
    routes = RouteBreakdowns(**config)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.FLUSH_PERIOD = 5
    metric._groups = {'route': 24.0, 'test': 0.4}
    metric.end_time = time.time()

    key = metric._key()
    metric.end()
    stat = _RouteBreakdown(
        method=metric.method, route=metric.route,
        responseType="application/json",
        time=1648551580.0367732)
    routes._stats = {key: stat}
    stat.add((metric.end_time - metric.start_time) * 1000)
    return routes, metric


@pytest.mark.server(url='/api/v5/projects/0/routes-breakdowns',
                    response="", method='POST')
def test_routes_breakdowns_notify_performance_stats():
    routes = RouteBreakdowns(**CONFIG)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.FLUSH_PERIOD = 5
    metric.end_time = time.time()
    assert routes.notify(metric) is None
    time.sleep(5)


@pytest.mark.server(url='/api/v5/projects/1/routes-breakdowns',
                    response="", method='POST')
def test_routes_breakdowns_notify_metric_404():
    CONFIG.update({
        'project_id': 1,
        "config": {
            "performance_stats": True,
            "error_host": "http://localhost:5000",
            "apm_host": "http://localhost:5000",
        }
    })
    routes = RouteBreakdowns(**CONFIG)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 404
    metric.content_type = "application/json"
    metric.FLUSH_PERIOD = 5
    metric.end_time = time.time()
    assert routes.notify(metric) is None


@pytest.mark.server(url='/api/v5/projects/2/routes-breakdowns',
                    response="", method='POST')
def test_routes_breakdowns_notify_200():
    CONFIG.update({
        'project_id': 2,
    })
    routes = RouteBreakdowns(**CONFIG)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.FLUSH_PERIOD = 5
    metric.end_time = time.time()
    metric._groups = {'route': 24.0, 'test': 0.4}
    routes._stats = {}
    assert routes.notify(metric) is None


@pytest.mark.server(url='/api/v5/projects/3/routes-breakdowns',
                    response="", method='POST')
def test_routes_breakdowns_notify_key_in_stats():
    CONFIG.update({
        'project_id': 3,
    })
    routes, metric = _test_setup(config=CONFIG)
    assert routes.notify(metric) is None


def test_routes_breakdowns_flash_empty_stats():
    routes = _Routes(**CONFIG)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.end_time = time.time()
    with pytest.raises(ValueError, match=r"stats is empty"):
        routes.breakdowns._flush()


@pytest.mark.server(url='/api/v5/projects/4/routes-breakdowns',
                    response="", method='POST')
def test_routes_breakdowns_notify_flush_200():
    CONFIG.update({
        'project_id': 4,
    })
    routes, metric = _test_setup(config=CONFIG)
    assert routes._flush() is None


@pytest.mark.server(url='/api/v5/projects/5/routes-breakdowns',
                    response="",  method='POST', status_code=306)
def test_routes_breakdowns_notify_flush_306():
    CONFIG.update({
        'project_id': 5,
    })
    routes, metric = _test_setup(config=CONFIG)
    assert routes._flush() is None


@pytest.mark.server(url='/api/v5/projects/6/routes-breakdowns',
                    response="",  method='POST', status_code=429)
def test_routes_breakdowns_notify_flush_429():
    CONFIG.update({
        'project_id': 6,
    })
    routes, metric = _test_setup(config=CONFIG)
    assert routes._flush() is None


@pytest.mark.server(url='/api/v5/projects/7/routes-stats',
                    response={"message": "in_data _flash Test"},
                    method='POST', status_code=400)
def test_routes_breakdowns_notify_flush_400():
    CONFIG.update({'project_id': 7})
    routes, metric = _test_setup(config=CONFIG)
    assert routes._flush() is None


def test_initiate_route_breakdown():
    route = _RouteBreakdown(
        method="GET", route="/test",
        responseType="application/json",
        time=1648551580.0367732)
    assert route.__dict__ == {'count': 0,
                              'sum': 0,
                              'sumsq': 0,
                              'tdigest': 'AAAAAkAkAAAAAAAAAAAAAA==',
                              'groups': {},
                              'method': 'GET',
                              'route': '/test',
                              'responseType': 'application/json',
                              'time': '2022-03-29T10:59:00Z'}


def test_routes_ab_url():
    CONFIG.update({'project_id': 0})
    stats = RouteBreakdowns(**CONFIG)
    assert stats._ab_url() == \
           'http://localhost:5000/api/v5/projects/0/routes-breakdowns'
