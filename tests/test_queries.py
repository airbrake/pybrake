import time

import pytest
import pybrake.metrics as metrics
from pybrake.queries import QueryStat, QueryStats, query_stat_key

metrics.FLUSH_PERIOD = 0
CONFIG = {"config": {
    "performance_stats": True,
    "query_stats": True,
    "error_host": "http://localhost:5000",
    "apm_host": "http://localhost:5000",
}}
start_time = time.time()
query = "SELECT * FROM foos"
method = "GET"
route = '/test'


def _test_setup(config: dict):
    stats = QueryStats(**config)
    key = query_stat_key(
        query=query,
        method=method,
        route=route,
        time=start_time,
    )
    stat = QueryStat(
        query=query, method=method, route=route, time=start_time
    )
    stats._stats = {key: stat}
    return stats


def test_query_metric_start_end():
    stats = QueryStat(time=1648551580.0367732)
    assert stats.__dict__ == {
        'count': 0,
        'sum': 0,
        'sumsq': 0,
        'tdigest': 'AAAAAkAkAAAAAAAAAAAAAA==',
        'query': '',
        'method': '',
        'route': '',
        'time': '2022-03-29T10:59:00Z'
    }


def test_query_stats_performance_stats():
    """
    To see what happens if performance_stats is set to false, run this test.
    :return:
    """
    stats = QueryStats(**{"config": {
        "performance_stats": False,
    }})
    assert stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    ) is None


def test_query_stats_query_stats():
    """
    To see what happens if query_stats is set to false, run this test.
    :return:
    """
    stats = QueryStats(**{"config": {
        "performance_stats": True,
        "query_stats": False,
    }})
    assert stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    ) is None


@pytest.mark.server(url='/api/v5/projects/0/queries-stats',
                    response="", method='POST')
def test_query_stats_notify():
    stats = QueryStats(**CONFIG)
    assert stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    ) is None


@pytest.mark.server(url='/api/v5/projects/1/queries-stats',
                    response="", method='POST')
def test_query_stats_notify_key_in_stats():
    CONFIG.update({"project_id": 1})
    stats = _test_setup(CONFIG)
    assert stats.notify(
        query=query,
        method=method,
        route=route,
        start_time=start_time,
        end_time=time.time(),
    ) is None


@pytest.mark.server(url='/api/v5/projects/2/queries-stats',
                    response="", method='POST')
def test_query_stats_notify_flash_empty_stats():
    CONFIG.update({"project_id": 2})
    stats = _test_setup(CONFIG)
    stats._stats = None
    with pytest.raises(ValueError, match=r"stats is empty"):
        stats._flush()


@pytest.mark.server(url='/api/v5/projects/3/queries-stats',
                    response={}, method='POST')
def test_query_stats_notify_flash_200():
    CONFIG.update({
        'project_id': 3,
    })
    stats = _test_setup(config=CONFIG)
    assert stats._flush() is None


@pytest.mark.server(url='/api/v5/projects/4/queries-stats',
                    response="", method='POST', status_code=306)
def test_query_stats_notify_flash_306():
    CONFIG.update({
        'project_id': 4,
    })
    stats = _test_setup(config=CONFIG)
    assert stats._flush() is None


@pytest.mark.server(url='/api/v5/projects/5/queries-stats',
                    response="", method='POST', status_code=429)
def test_query_stats_notify_flash_429():
    CONFIG.update({
        'project_id': 5,
    })
    stats = _test_setup(config=CONFIG)
    assert stats._flush() is None


@pytest.mark.server(url='/api/v5/projects/6/queries-stats',
                    response={"message": "in_data _flash Test"},
                    method='POST', status_code=400)
def test_query_stats_notify_flash_in_data():
    CONFIG.update({
        'project_id': 6,
    })
    stats = _test_setup(config=CONFIG)
    assert stats._flush() is None


def test_queue_ab_url():
    CONFIG.update({"project_id": 0})
    stats = QueryStats(**CONFIG)
    res = stats._ab_url()
    assert res == "http://localhost:5000/api/v5/projects/0/queries-stats"
