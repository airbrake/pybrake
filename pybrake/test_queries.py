import time

from .queries import QueryStat, QueryStats


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
    stats = QueryStats(**{"config": {"performance_stats": False}})
    stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    )


def test_query_stats_query_stats():
    stats = QueryStats(**{"config": {
        "performance_stats": True,
        "query_stats": False
    }})
    stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    )


def test_query_stats_notify():
    stats = QueryStats(**{"config": {
        "performance_stats": True,
        "query_stats": True
    }})
    stats.notify(
        query="SELECT * FROM foos",
        method="GET",
        route='test',
        start_time=time.time(),
        end_time=time.time(),
    )


def test_queue_ab_url():
    stats = QueryStats(**{"config": {
        "performance_stats": True,
        "query_stats": True
    }})
    stats._ab_url()
