import time

from .route_metric import RouteMetric
from .routes import _Routes, RouteStats, RouteStat


def test_routes_performance_stats():
    routes = _Routes(**{"config": {
        "performance_stats": False,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.end_time = time.time()

    routes.notify(metric)


def test_routes_notify():
    routes = _Routes(**{"config": {
        "performance_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})

    metric = RouteMetric(method="GET", route="/test")
    metric.status_code = 200
    metric.content_type = "application/json"
    metric.end_time = time.time()

    routes.notify(metric)


def test_route_stat():
    routes = _Routes(**{"config": {
        "performance_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})

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
    stats = RouteStats(**{"config": {
        "performance_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})
    stats._ab_url()
