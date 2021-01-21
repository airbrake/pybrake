import os
import re
import sys
import platform
import socket
import urllib.request
import urllib.error
from concurrent import futures
import json
import time
import warnings

from .notice import jsonify_notice
from .git import find_git_dir
from .routes import _Routes
from .queries import QueryStats
from .queues import QueueStats
from .blocklist_filter import make_blocklist_filter
from .code_hunks import get_code_hunk
from .git import get_git_revision
from .utils import logger
from .version import version
from .notifier_name import notifier_name
from .remote_settings import RemoteSettings


_ERR_IP_RATE_LIMITED = "IP is rate limited"

_AB_URL_FORMAT = "{}/api/v3/projects/{}/notices"

_CONTEXT = dict(
    notifier=dict(
        name=notifier_name, version=version, url="https://github.com/airbrake/pybrake"
    ),
    os=platform.platform(),
    language="Python/%s" % platform.python_version(),
    hostname=socket.gethostname(),
    versions=dict(python=platform.python_version()),
)


class Notifier:
    def __init__(
        self, *, project_id=0, project_key="", host="https://api.airbrake.io", **kwargs
    ):
        self.config = {
            "error_notifications": True,
            "performance_stats": kwargs.get("performance_stats", False),
            "query_stats": kwargs.get("query_stats", True),
            "queue_stats": kwargs.get("queue_stats", True),
            "error_host": host,
            "apm_host": host,
        }
        kwargs["config"] = self.config

        self.routes = _Routes(
            project_id=project_id, project_key=project_key, **kwargs
        )
        self.queries = QueryStats(
            project_id=project_id, project_key=project_key, host=host, **kwargs
        )
        self.queues = QueueStats(
            project_id=project_id, project_key=project_key, host=host, **kwargs
        )

        self._filters = []
        self._rate_limit_reset = 0
        self._max_queue_size = kwargs.get("max_queue_size", 1000)
        self._thread_pool = None
        self._max_workers = kwargs.get('max_workers')

        self._ab_url = _AB_URL_FORMAT.format(host, project_id)
        self._ab_headers = {
            "authorization": "Bearer " + project_key,
            "content-type": "application/json",
        }

        self._context = _CONTEXT.copy()
        self._context["rootDirectory"] = kwargs.get("root_directory", os.getcwd())

        rev = kwargs.get("revision")
        if rev is None:
            # https://devcenter.heroku.com/changelog-items/630
            rev = os.environ.get("SOURCE_VERSION")
        if rev is None:
            git_dir = find_git_dir(self._context["rootDirectory"])
            if git_dir != "":
                rev = get_git_revision(git_dir)

        if rev is not None:
            self._context["revision"] = rev

        if "environment" in kwargs:
            self._context["environment"] = kwargs["environment"]

        self.add_filter(pybrake_error_filter)

        keys_blacklist = kwargs.get("keys_blacklist")
        keys_blocklist = kwargs.get("keys_blocklist")

        if keys_blacklist is not None:
            keys_blocklist = keys_blacklist
            warnings.warn(
                    "keys_blacklist is a deprecated option. "
                    "Use keys_blocklist instead.",
                    DeprecationWarning
                )

        if keys_blocklist is None:
            keys_blocklist = [re.compile("password"), re.compile("secret")]

        self.add_filter(make_blocklist_filter(keys_blocklist))

        if "filter" in kwargs:
            self.add_filter(kwargs["filter"])

        if kwargs.get("remote_config"):
            RemoteSettings(
                project_id,
                "https://notifier-configs.airbrake.io",
                self.config,
            ).poll()

    def close(self):
        if self._thread_pool is not None:
            self._thread_pool.shutdown()

    def add_filter(self, filter_fn):
        """Appends filter to the list.

        Filter is a function that accepts notice. Filter can modify passed
        notice or return None if notice must be ignored.
        """
        self._filters.append(filter_fn)

    def notify_sync(self, err):
        """Notifies Airbrake about exception.

        Under the hood notify is a shortcut for build_notice and send_notice.
        """
        notice = self.build_notice(err)
        return self.send_notice_sync(notice)

    def build_notice(self, err):
        """Builds Airbrake notice from the exception."""
        notice = dict(
            errors=self._build_errors(err),
            context=self._build_context(),
            params=dict(sys_executable=sys.executable, sys_path=sys.path),
        )
        return notice

    def _filter_notice(self, notice):
        for fn in self._filters:
            r = fn(notice)
            if r is None:
                notice["error"] = "notice is filtered out"
                return notice, False
            notice = r

        return notice, True

    def send_notice_sync(self, notice):
        """Sends notice to Airbrake.

        It returns notice with 2 possible new keys:
        - {'id' => str} - notice id on success.
        - {'error' => str|Exception} - error on failure.
        """
        notice, ok = self._filter_notice(notice)
        if not ok:
            return notice

        if not self.config.get("error_notifications"):
            return notice

        return self._send_notice_sync(notice)

    def _send_notice_sync(self, notice):
        if time.time() < self._rate_limit_reset:
            notice["error"] = _ERR_IP_RATE_LIMITED
            return notice

        data = jsonify_notice(notice)
        req = urllib.request.Request(self._ab_url, data=data, headers=self._ab_headers)

        try:
            resp = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as err:
            resp = err
        except Exception as err:  # pylint: disable=broad-except
            notice["error"] = err
            logger.error(notice["error"])
            return notice

        try:
            body = resp.read()
        except IOError as err:
            notice["error"] = err
            logger.error(notice["error"])
            return notice

        if not (200 <= resp.code < 300 or 400 <= resp.code < 500):
            notice["error"] = "airbrake: unexpected response status_code={}".format(
                resp.code
            )
            notice["error_info"] = dict(code=resp.code, body=body)
            logger.error(notice["error"])
            return notice

        if resp.code == 429:
            return self._rate_limited(notice, resp)

        try:
            body = body.decode("utf-8")
        except UnicodeDecodeError as err:
            notice["error"] = err
            logger.error(notice["error"])
            return notice

        try:
            data = json.loads(body)
        except ValueError as err:  # json.JSONDecodeError requires Python 3.5+
            notice["error"] = err
            logger.error(notice["error"])
            return notice

        if "id" in data:
            notice["id"] = data["id"]
            return notice

        if "message" in data:
            notice["error"] = data["message"]
            logger.error(notice["error"])
            return notice

        notice["error"] = "unexpected Airbrake response"
        notice["error_info"] = dict(data=data)
        logger.error(notice["error"])
        return notice

    def _rate_limited(self, notice, resp):
        v = resp.headers.get("X-RateLimit-Delay")
        if v is None:
            notice["error"] = "X-RateLimit-Delay header is missing"
            return notice

        try:
            delay = int(v)
        except ValueError as err:
            notice["error"] = err
            return notice

        self._rate_limit_reset = time.time() + delay

        notice["error"] = _ERR_IP_RATE_LIMITED
        return notice

    def notify(self, err):
        """Asynchronously notifies Airbrake about exception from separate thread.

        Returns concurrent.futures.Future.
        """
        notice = self.build_notice(err)
        return self.send_notice(notice)

    def send_notice(self, notice):
        """Asynchronously sends notice to Airbrake from separate thread.

        Returns concurrent.futures.Future.
        """
        if not self.config.get("error_notifications"):
            notice["error"] = "error notifications are disabled"
            f = futures.Future()
            f.set_result(notice)
            return f

        notice, ok = self._filter_notice(notice)
        if not ok:
            f = futures.Future()
            f.set_result(notice)
            return f

        pool = self._get_thread_pool()
        if pool._work_queue.qsize() >= self._max_queue_size:
            notice["error"] = "queue is full"
            f = futures.Future()
            f.set_result(notice)
            return f

        return pool.submit(self._send_notice_sync, notice)

    def _build_errors(self, err):
        if err is None:
            return []

        if isinstance(err, str):
            frame = sys._getframe()
            while frame is not None:
                if frame.f_code.co_filename.endswith("pybrake/notifier.py"):
                    frame = frame.f_back
                else:
                    break

            backtrace = self._build_backtrace_frame(frame)
            return [{"message": err, "backtrace": backtrace}]

        errors = []
        while err is not None:
            errors.append(self._build_error(err))
            err = err.__cause__ or err.__context__
        return errors

    def _build_error(self, err):
        backtrace = self._build_backtrace_tb(err.__traceback__)
        error = dict(type=err.__class__.__name__, message=str(err), backtrace=backtrace)
        return error

    def _build_backtrace_tb(self, tb):
        backtrace = []
        for frame, lineno in self._walk_tb(tb):
            f = self._build_frame(frame, lineno)
            if f:
                backtrace.insert(0, f)
        return backtrace

    def _walk_tb(self, tb):
        while tb is not None:
            yield tb.tb_frame, tb.tb_lineno
            tb = tb.tb_next

    def _build_backtrace_frame(self, f):
        backtrace = []
        for frame, lineno in self._walk_stack(f):
            f = self._build_frame(frame, lineno)
            if f:
                backtrace.append(f)
        return backtrace

    def _walk_stack(self, f):
        while f is not None:
            yield f, f.f_lineno
            f = f.f_back

    def _build_frame(self, f, line):
        if f.f_locals.get("__traceback_hide__"):
            return None

        filename = f.f_code.co_filename
        func = f.f_code.co_name

        loader = f.f_globals.get("__loader__")
        module_name = f.f_globals.get("__name__")
        return self._frame_with_code(
            filename, func, line, loader=loader, module_name=module_name
        )

    def _frame_with_code(
        self, filename, func, line, loader=None, module_name=None
    ):  # pylint: disable=too-many-arguments
        frame = dict(file=self._clean_filename(filename), function=func, line=line)

        lines = get_code_hunk(filename, line, loader=loader, module_name=module_name)
        if lines is not None:
            frame["code"] = lines

        return frame

    def _clean_filename(self, s):
        if "/lib/python" in s and "/site-packages/" in s:
            needed = "/site-packages/"
            ind = s.find(needed)
            if ind > -1:
                s = "/SITE_PACKAGES/" + s[ind + len(needed) :]
                return s

        s = s.replace(self._context["rootDirectory"], "/PROJECT_ROOT")
        return s

    def _build_context(self):
        ctx = self._context.copy()

        versions = ctx["versions"]
        for name, mod in sys.modules.copy().items():
            if name.startswith("_"):
                continue
            if hasattr(mod, "__version__"):
                versions[name] = mod.__version__

        return ctx

    def _get_thread_pool(self):
        if self._thread_pool is None:
            if self._max_workers is None:
                self._max_workers = (os.cpu_count() or 1) * 5
            self._thread_pool = futures.ThreadPoolExecutor(max_workers=self._max_workers)
        return self._thread_pool


def pybrake_error_filter(notice):
    backtrace = notice["errors"][0]["backtrace"]
    for frame in backtrace:
        dirname = os.path.dirname(frame["file"])
        file_name = os.path.basename(dirname)
        if file_name == "pybrake":
            if os.path.basename(frame["file"]).startswith("test_"):
                break

            return None

    return notice
