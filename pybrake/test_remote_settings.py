from .remote_settings import RemoteSettings


def test_build_remote_setting():
    config = {
        "error_notifications": True,
        "performance_stats": True,
        "query_stats": True,
        "queue_stats": True,
        "error_host": "https://api.airbrake.io",
        "apm_host": "https://api.airbrake.io",
    }
    RemoteSettings(project_id="403427",
                   host="https://notifier-configs.airbrake.io",
                   config=config).poll()
