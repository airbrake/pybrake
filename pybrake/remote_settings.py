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
    def __init__(self, project_id, host):
        self.project_id = project_id
        self.host = host

    def poll(self, config):
        thread = threading.Thread(target=self._run, kwargs={"config": config})
        thread.daemon = True
        thread.start()

    def _run(self, **kwargs):
        while True:
            resp = urllib.request.urlopen(self._poll_url())
            json_data = json.loads(resp.read().decode('utf-8'))
            remote_config = SettingsData(self.project_id, json_data)

            kwargs["config"]["error_notifications"] = remote_config.error_notifications()
            kwargs["config"]["performance_stats"] = remote_config.performance_stats()
            print(json_data)

            time.sleep(remote_config.interval())

    def _poll_url(self):
        url = _CONFIG_ROUTE_PATTERN % (self.host, _API_VER, self.project_id)
        return url + '?' + urlencode(_NOTIFIER_INFO)
