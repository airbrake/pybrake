from .settings_data import SettingsData


def test_interval_when_no_poll_sec():
    s = SettingsData(1, {})
    assert s.interval() == 600

def test_interval_when_poll_sec_is_None():
    s = SettingsData(1, {"poll_sec": None})
    assert s.interval() == 600

def test_interval_when_poll_sec_is_less_than_zero():
    s = SettingsData(1, {"poll_sec": -2})
    assert s.interval() == 600

def test_interval_when_poll_sec_is_zero():
    s = SettingsData(1, {"poll_sec": 0})
    assert s.interval() == 600

def test_interval_when_poll_sec_is_greater_than_zero():
    s = SettingsData(1, {"poll_sec": 123})
    assert s.interval() == 123

def test_config_route_when_missing():
    s = SettingsData(1, {})
    assert s.config_route("http://example.com") == (
        "http://example.com/2020-06-18/config/1/config.json"
    )

def test_config_route_when_it_is_specified():
    s = SettingsData(1, {"config_route": "123/cfg/321/cfg.json"})
    assert s.config_route("http://example.com") == (
        "http://example.com/123/cfg/321/cfg.json"
    )

def test_config_route_when_the_given_host_ends_with_a_trailing_slash():
    s = SettingsData(1, {})
    assert s.config_route("http://example.com/") == (
        "http://example.com/2020-06-18/config/1/config.json"
    )

def test_config_route_when_it_is_None():
    s = SettingsData(1, {"config_route": None})
    assert s.config_route("http://example.com") == (
        "http://example.com/2020-06-18/config/1/config.json"
    )

def test_config_route_when_it_is_empty():
    s = SettingsData(1, {"config_route": ""})
    assert s.config_route("http://example.com") == (
        "http://example.com/2020-06-18/config/1/config.json"
    )

def test_error_notifications_when_it_is_present_and_enabled():
    s = SettingsData(1, {
        "settings": [{
            "name": "errors",
            "enabled": True,
        }],
    })
    assert s.error_notifications()

def test_error_notifications_when_it_is_present_and_disabled():
    s = SettingsData(1, {
        "settings": [{
            "name": "errors",
            "enabled": False,
        }],
    })
    assert not s.error_notifications()

def test_error_notifications_when_it_is_missing():
    s = SettingsData(1, {
        "settings": [],
    })
    assert s.error_notifications()

def test_error_notifications_when_settings_are_missing():
    s = SettingsData(1, {})
    assert s.error_notifications()

def test_performance_stats_when_it_is_present_and_enabled():
    s = SettingsData(1, {
        "settings": [{
            "name": "apm",
            "enabled": True,
        }],
    })
    assert s.performance_stats()

def test_performance_stats_when_it_is_present_and_disabled():
    s = SettingsData(1, {
        "settings": [{
            "name": "apm",
            "enabled": False,
        }],
    })
    assert not s.performance_stats()

def test_performance_stats_when_it_is_missing():
    s = SettingsData(1, {
        "settings": [],
    })
    assert s.performance_stats()

def test_performance_stats_when_settings_are_missing():
    s = SettingsData(1, {})
    assert s.performance_stats()

def test_error_host_when_the_errors_setting_is_present():
    s = SettingsData(1, {
        "settings": [{
            "name": "errors",
            "enabled": True,
            "endpoint": "http://api.example.com",
        }],
    })
    assert s.error_host() == "http://api.example.com"

def test_error_host_when_the_errors_setting_is_present_without_endpoint():
    s = SettingsData(1, {
        "settings": [{
            "name": "errors",
            "enabled": True,
        }],
    })
    assert s.error_host() is None

def test_error_host_when_the_errors_setting_is_missing():
    s = SettingsData(1, {
        "settings": [],
    })
    assert s.error_host() is None

def test_apm_host_when_the_apm_setting_is_present():
    s = SettingsData(1, {
        "settings": [{
            "name": "apm",
            "enabled": True,
            "endpoint": "http://api.example.com",
        }],
    })
    assert s.apm_host() == "http://api.example.com"

def test_apm_host_when_the_apm_setting_is_present_without_endpoint():
    s = SettingsData(1, {
        "settings": [{
            "name": "apm",
            "enabled": True,
        }],
    })
    assert s.apm_host() is None

def test_apm_host_when_the_apm_setting_is_missing():
    s = SettingsData(1, {
        "settings": [],
    })
    assert s.apm_host() is None
