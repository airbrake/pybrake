import platform
import urllib.request
import json
import threading
import time

from urllib.parse import urlencode
from .version import version
from .notifier_name import notifier_name
from .settings_data import SettingsData, _CONFIG_ROUTE_PATTERN, _API_VER


# Query params to be appended to each GET request.
_NOTIFIER_INFO = {
    "notifier_name": notifier_name,
    "notifier_version": version,
    "os": platform.platform(),
    "language": platform.python_version(),
}


class RemoteSettings:
    def __init__(self, project_id, host, config):
        self._project_id = project_id
        self._host = host
        self._config = config

        self._orig_error_notifications = config["error_notifications"]
        self._orig_performance_stats = config["performance_stats"]

    def poll(self):
        thread = threading.Thread(target=self._run, kwargs={"config": self._config})
        thread.daemon = True
        thread.start()

    def _run(self, **kwargs):
        while True:
            resp = urllib.request.urlopen(self._poll_url())
            json_data = json.loads(resp.read().decode('utf-8'))
            data = SettingsData(self._project_id, json_data)

            self._config["error_host"] = data.error_host()
            self._config["apm_host"] = data.apm_host()

            self._process_error_notifications(data)
            self._process_performance_stats(data)

            time.sleep(data.interval())

    def _poll_url(self):
        url = _CONFIG_ROUTE_PATTERN % (self._host, _API_VER, self._project_id)
        return url + '?' + urlencode(_NOTIFIER_INFO)

    def _process_error_notifications(self, data):
        if not self._orig_error_notifications:
            return

        self._config["error_notifications"] = data.error_notifications()


    def _process_performance_stats(self, data):
        if not self._orig_performance_stats:
            return

        self._config["performance_stats"] = data.performance_stats()
