# API version to poll.
_API_VER = "2020-06-18"

# How frequently we should poll the config API.
_DEFAULT_INTERVAL = 600

# What path to poll.
_CONFIG_ROUTE_PATTERN = "%s/%s/config/%d/config.json"

# Remote config settings.
_ERROR_SETTING = "errors"
_APM_SETTING = "apm"


class SettingsData:
    def __init__(self, project_id, data):
        self.project_id = project_id
        self.data = data

    def interval(self):
        poll_sec = self.data.get("poll_sec")
        if poll_sec is None:
            return _DEFAULT_INTERVAL

        if poll_sec > 0:
            return poll_sec

        return _DEFAULT_INTERVAL

    def config_route(self, remote_config_host):
        host = remote_config_host.rstrip("/")

        config_route = self.data.get("config_route")
        if config_route:
            return host + "/" + config_route

        return _CONFIG_ROUTE_PATTERN % (host, _API_VER, self.project_id)

    def error_notifications(self):
        s = self._find_setting(_ERROR_SETTING)
        if s is None:
            return True

        return s.get("enabled")

    def performance_stats(self):
        s = self._find_setting(_APM_SETTING)
        if s is None:
            return True

        return s.get("enabled")

    def error_host(self):
        s = self._find_setting(_ERROR_SETTING)
        if s is None:
            return None

        return s.get("endpoint")

    def apm_host(self):
        s = self._find_setting(_APM_SETTING)
        if s is None:
            return None

        return s.get("endpoint")

    def _find_setting(self, name):
        settings = self.data.get("settings")
        if settings is None:
            return None

        for i in settings:
            if i.get("name") == name:
                return i

        return None
