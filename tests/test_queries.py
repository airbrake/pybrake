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
        'file': '',
        'function': '',
        'line': 0,
        'sum': 0,
        'sumsq': 0,
        'tdigest': 'AAAAAkAkAAAAAAAAAAAAAA==',
        'query': '',
        'method': '',
        'route': '',
        'time': '2022-03-29T10:59:00Z'
    }


def test_query_stats_performance_stats(mocker):
    """
    To see what happens if performance_stats is set to false, run this test.
    :return:
    """
    mocker.patch(
        "pybrake.queries.QueryStats._flush",
        return_value=None
    )
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


def test_query_stats_query_stats(mocker):
    """
    To see what happens if query_stats is set to false, run this test.
    :return:
    """
    mocker.patch(
        "pybrake.queries.QueryStats._flush",
        return_value=None
    )
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


def test_query_stats_notify_flash(mocker):
    mocker.patch(
        "pybrake.metrics.send",
        return_value=None
    )
    stats = _test_setup(CONFIG)
    assert stats._flush() is None
    # Empty Stats
    stats._stats = None
    with pytest.raises(ValueError, match=r"stats is empty"):
        stats._flush()


def test_query_stats_notify(mocker):
    mocker.patch(
        "pybrake.queries.QueryStats._flush",
        return_value=None
    )
    stats = QueryStats(**CONFIG)
    assert stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    ) is None


def test_queue_ab_url():
    CONFIG.update({"project_id": 0})
    stats = QueryStats(**CONFIG)
    res = stats._ab_url()
    assert res == "http://localhost:5000/api/v5/projects/0/queries-stats"
