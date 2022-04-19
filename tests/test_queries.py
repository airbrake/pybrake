import time

from pybrake.queries import QueryStat, QueryStats


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


def _test_query_stats_notify():
    # TODO: refactor QueryStats class code before enable this test case
    stats = QueryStats(**{"config": {
        "performance_stats": True,
        "query_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})
    assert stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    ) is None


def test_queue_ab_url():
    stats = QueryStats(**{"config": {
        "performance_stats": True,
        "query_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})
    res = stats._ab_url()
    assert res == "https://api.airbrake.io/api/v5/projects/0/queries-stats"
