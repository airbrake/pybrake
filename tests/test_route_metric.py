import time

import pytest
import pybrake.metrics as metrics
from pybrake.route_metric import RouteMetric, _RouteBreakdown, RouteBreakdowns
from pybrake.routes import _Routes

metrics.FLUSH_PERIOD = 0
CONFIG = {
    "config": {
        "performance_stats": False,
        "backlog_enabled": True,
        "error_host": "http://localhost:5000",
        "apm_host": "http://localhost:5000",
    }
}


def _test_setup(config: dict, status_code=200):
    routes = RouteBreakdowns(**config)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = status_code
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


def test_routes_breakdowns_flash_empty_stats():
    routes = _Routes(**CONFIG)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.end_time = time.time()
    with pytest.raises(ValueError, match=r"stats is empty"):
        routes.breakdowns._env = "Test"
        routes.breakdowns._flush()


def test_routes_breakdowns_notify_flush(mocker):
    mocker.patch(
        "pybrake.metrics.send",
        return_value=None
    )
    routes, metric = _test_setup(config=CONFIG)
    assert routes._flush() is None


def test_routes_breakdowns_notify(mocker):
    mocker.patch(
        "pybrake.route_metric.RouteBreakdowns._flush",
        return_value=None
    )
    routes, metric = _test_setup(config=CONFIG)
    assert routes.notify(metric) is None


def test_routes_breakdowns_notify_with_performance(mocker):
    mocker.patch(
        "pybrake.route_metric.RouteBreakdowns._flush",
        return_value=None
    )
    CONFIG.get('config').update({
        'performance_stats': True,
    })
    routes, metric = _test_setup(config=CONFIG)
    routes._stats = None
    assert routes.notify(metric) is None


def test_routes_breakdowns_notify_response_500(mocker):
    mocker.patch(
        "pybrake.route_metric.RouteBreakdowns._flush",
        return_value=None
    )
    CONFIG.get('config').update({
        'performance_stats': True,
    })
    routes, metric = _test_setup(config=CONFIG, status_code=500)
    routes._stats = None
    assert routes.notify(metric) is None


def test_routes_breakdowns_notify_response_400(mocker):
    mocker.patch(
        "pybrake.route_metric.RouteBreakdowns._flush",
        return_value=None
    )
    CONFIG.get('config').update({
        'performance_stats': True,
    })
    routes, metric = _test_setup(config=CONFIG, status_code=400)
    routes._stats = None
    assert routes.notify(metric) is None


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
