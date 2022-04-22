import pytest

import pybrake.metrics as metrics
from pybrake.queues import QueueMetric, QueueStats, _QueueStat

metrics.FLUSH_PERIOD = 0


def test_queue_metric_start_end():
    metric = QueueMetric(queue="test")
    metric.end()
    assert metric.end_time is not None


def test_queue_metric_key():
    metric = QueueMetric(queue="test")
    assert ("test", metric.start_time // 60 * 60) == metric._key()


def test_queue_stats_performance_stats():
    metric = QueueMetric(queue="foo_queue")
    metric._groups = {'redis': 24.0, 'sql': 0.4}
    stats = QueueStats(**{"config": {"performance_stats": False}})
    metric.end()
    assert stats.notify(metric) is None


def test_queue_stats_queue_stat_value():
    metric = QueueMetric(queue="foo_queue")
    stat = _QueueStat(queue=metric.queue, time=metric.start_time)
    assert stat.__dict__.get('queue') == 'foo_queue'


def test_queue_stats_queue_stats():
    """
    To see what happens if performance_stats is set to false, run this test.
    :return:
    """
    metric = QueueMetric(queue="foo_queue")
    stats = QueueStats(**{"config": {
        "performance_stats": False,
    }})
    metric.end()
    assert stats.notify(metric) is None


def test_queue_stats_false():
    """
    To see what happens if queue_stats is set to false, run this test.
    :return:
    """
    metric = QueueMetric(queue="foo_queue")
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": False,
    }})
    metric.end()
    assert stats.notify(metric) is None


def test_queue_stats_notify():
    metric = QueueMetric(queue="foo_queue")
    metric._groups = {'redis': 24.0, 'sql': 0.4}
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})
    metric.end()
    assert stats.notify(metric) is None


def test_queue_ab_url():
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }})
    assert stats._ab_url() == \
           'https://api.airbrake.io/api/v5/projects/0/queues-stats'


def test_queue_flush_blank_stet():
    stats = QueueStats(**{"config": {
        "performance_stats": True,
        "queue_stats": True
    }})
    with pytest.raises(ValueError, match=r"stats is empty"):
        stats._flush()
