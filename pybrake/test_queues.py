import pytest

from .queues import QueueMetric, QueueStats, _QueueStat


def test_queue_metric_start_end():
    metric = QueueMetric(queue="test")
    metric.end()


def test_queue_metric_key():
    metric = QueueMetric(queue="test")
    assert ("test", metric.start_time // 60 * 60) == metric._key()


def test_queue_stats_performance_stats():
    metric = QueueMetric(queue="foo_queue")
    metric._groups = {'redis': 24.0, 'sql': 0.4}
    stats = QueueStats(**{"config": {"performance_stats": False}})
    metric.end()
    stats.notify(metric)


def test_queue_stats_queue_stat_value():
    metric = QueueMetric(queue="foo_queue")
    metric._groups = {'redis': 24.0, 'sql': 0.4}
    metric.end()
    stat = _QueueStat(queue=metric.queue, time=metric.start_time)
    print(stat.__dict__)


def test_queue_stats_queue_stats():
    metric = QueueMetric(queue="foo_queue")
    metric._groups = {'redis': 24.0, 'sql': 0.4}
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": False
    }})
    metric.end()
    stats.notify(metric)


def test_queue_stats_group_length():
    metric = QueueMetric(queue="foo_queue")
    metric._groups = {'redis': 24.0}
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": False
    }})
    metric.end()
    stats.notify(metric)


def _test_queue_stats_notify():
    metric = QueueMetric(queue="foo_queue")
    metric._groups = {'redis': 24.0, 'sql': 0.4}
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": True
    }})
    metric.end()
    stats.notify(metric)


def test_queue_ab_url():
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": True
    }})
    stats._ab_url()


def test_queue_flush_blank_stet():
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": True
    }})
    with pytest.raises(ValueError, match=r"stats is empty"):
        stats._flush()
