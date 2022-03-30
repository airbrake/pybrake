import platform
import urllib.request
import json
import threading
import time

from urllib.parse import urlencode
from copy import deepcopy
from .version import version
from .notifier_name import notifier_name
from .settings_data import SettingsData


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
        self._data = SettingsData(project_id, {})
        self._prev_data = None

        self._orig_error_notifications = config["error_notifications"]
        self._orig_performance_stats = config["performance_stats"]

    def poll(self):
        thread = threading.Thread(target=self._run)
        thread.daemon = True
        thread.start()

    def _run(self, **kwargs):
        while True:
            try:
                resp = urllib.request.urlopen(self._poll_url(self._data))
                self._prev_data = deepcopy(self._data)
            except urllib.error.HTTPError as err:
                try:
                    if self._prev_data is None:
                        raise err
                    resp = urllib.request.urlopen(self._poll_url(self._prev_data))
                except urllib.error.HTTPError:
                    time.sleep(self._data.interval())
                    continue

            json_data = json.loads(resp.read().decode('utf-8'))
            self._data.merge(json_data)

            error_host = self._data.error_host()
            if error_host is not None:
                self._config["error_host"] = self._data.error_host()

            apm_host = self._data.apm_host()
            if apm_host is not None:
                self._config["apm_host"] = self._data.apm_host()

            self._process_error_notifications(self._data)
            self._process_performance_stats(self._data)

            time.sleep(self._data.interval())

    def _poll_url(self, data):
        url = data.config_route(self._host)
        return url + '?' + urlencode(_NOTIFIER_INFO)

    def _process_error_notifications(self, data):
        if not self._orig_error_notifications:
            return

        self._config["error_notifications"] = data.error_notifications()

    def _process_performance_stats(self, data):
        if not self._orig_performance_stats:
            return

        self._config["performance_stats"] = data.performance_stats()
