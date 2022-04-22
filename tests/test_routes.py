import time

import pytest
from pybrake.route_metric import RouteMetric
import pybrake.metrics as metrics
from pybrake.routes import _Routes, RouteStats, RouteStat, route_stat_key

metrics.FLUSH_PERIOD = 0
CONFIG = {
    "config": {
        "performance_stats": True,
        "error_host": "http://localhost:5000",
        "apm_host": "http://localhost:5000",
    }
}


def _test_setup(config: dict):
    routes = _Routes(**config)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.FLUSH_PERIOD = 5
    metric.end_time = time.time()

    key = route_stat_key(
        method=metric.method,
        route=metric.route,
        status_code=metric.status_code,
        time=metric.start_time,
    )

    stat = RouteStat(
        method=metric.method,
        route=metric.route,
        status_code=metric.status_code,
        time=metric.start_time,
    )
    routes.stats._stats = {key: stat}
    stat.add((metric.end_time - metric.start_time) * 1000)
    return routes


def test_routes_performance_stats():
    """
    To see what happens if performance_stats is set to false, run this test.
    :return:
    """
    routes = _Routes(**{"config": {
        "performance_stats": False,
    }})

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.end_time = time.time()

    assert routes.notify(metric) is None


@pytest.mark.server(url='/api/v5/projects/0/routes-stats',
                    response="", method='POST')
def test_routes_notify():
    routes = _Routes(**CONFIG)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.FLUSH_PERIOD = 5
    metric.end_time = time.time()
    assert routes.notify(metric) is None
    time.sleep(5)


def test_routes_flash_empty_stats():
    routes = _Routes(**CONFIG)

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.end_time = time.time()
    with pytest.raises(ValueError, match=r"stats is empty"):
        routes.stats._flush()


@pytest.mark.server(url='/api/v5/projects/1/routes-stats',
                    response="", method='POST')
def test_routes_flash_ok():
    CONFIG.update({'project_id': 1})
    routes = _test_setup(CONFIG)
    assert routes.stats._flush() is None


@pytest.mark.server(url='/api/v5/projects/2/routes-stats',
                    response={}, method='POST', status_code=502)
def test_routes_flash_json_load_error():
    CONFIG.update({'project_id': 2})
    routes = _test_setup(CONFIG)
    assert routes.stats._flush() is None


@pytest.mark.server(url='/api/v5/projects/3/routes-stats',
                    response={},
                    method='POST', status_code=429)
def test_routes_flash_json_too_many_redirects():
    CONFIG.update({'project_id': 3})
    routes = _test_setup(CONFIG)
    assert routes.stats._flush() is None


@pytest.mark.server(url='/api/v5/projects/4/routes-stats',
                    response={"message": "in_data _flash Test"},
                    method='POST', status_code=400)
def test_routes_flash_decode():
    CONFIG.update({'project_id': 4})
    routes = _test_setup(CONFIG)
    assert routes.stats._flush() is None


@pytest.mark.server(url='/api/v5/projects/5/routes-stats',
                    response={},
                    method='POST', status_code=306)
def test_routes_flash_unused():
    CONFIG.update({'project_id': 5})
    routes = _test_setup(CONFIG)
    assert routes.stats._flush() is None


def test_route_stat():
    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.end_time = time.time()

    stat = RouteStat(
        method=metric.method,
        route=metric.route,
        status_code=metric.status_code,
        time=1648551580.0367732,
    )

    assert stat.__dict__ == {
        'count': 0,
        'sum': 0,
        'sumsq': 0,
        'tdigest': 'AAAAAkAkAAAAAAAAAAAAAA==',
        'method': 'GET',
        'route': '/test',
        'statusCode': 200,
        'time': '2022-03-29T10:59:00Z'
    }


def test_routes_ab_url():
    CONFIG.update({'project_id': 0})
    stats = RouteStats(**CONFIG)
    assert stats._ab_url() == \
           'http://localhost:5000/api/v5/projects/0/routes-stats'
