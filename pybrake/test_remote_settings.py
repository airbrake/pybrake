from .remote_settings import RemoteSettings


def test_build_remote_setting_poll_url():
    config = {
        "error_notifications": True,
        "performance_stats": True,
        "query_stats": True,
        "queue_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }
    res = RemoteSettings(project_id=403427,
                         host="https://notifier-configs.airbrake.io",
                         config=config)
    assert 'https://notifier-configs.airbrake.io/2020-06-18/config/403427' \
           '/config.json?notifier_name=pybrake&notifier_version=1.0.' in \
           res._poll_url(res._data)


def test_build_remote_setting_error_notifications():
    config = {
        "error_notifications": False,
        "performance_stats": True,
        "query_stats": True,
        "queue_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }
    res = RemoteSettings(project_id=403427,
                         host="https://notifier-configs.airbrake.io",
                         config=config)
    assert res._process_error_notifications(res._data) is None


def test_build_remote_setting_performance_stats():
    config = {
        "error_notifications": True,
        "performance_stats": False,
        "query_stats": True,
        "queue_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }
    res = RemoteSettings(project_id=403427,
                         host="https://notifier-configs.airbrake.io",
                         config=config)
    assert res._process_performance_stats(res._data) is None
