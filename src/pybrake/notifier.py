import os
import platform
import re
import socket
import sys
import time
import warnings
from concurrent import futures
from pathlib import Path

from .backlog import Backlog
from .blocklist_filter import make_blocklist_filter
from .code_hunks import get_code_hunk
from .constant import (
    AIRBRAKE_HOST, AIRBRAKE_CONFIG_HOST, notifier_name, version
)
from .git import find_git_dir
from .git import get_git_revision
from . import metrics
from .queries import QueryStats
from .queues import QueueStats
from .remote_settings import RemoteSettings
from .routes import _Routes

_ERR_IP_RATE_LIMITED = "IP is rate limited"

_AB_URL_FORMAT = "{}/api/v3/projects/{}/notices"

_CONTEXT = dict(
    notifier=dict(
        name=notifier_name, version=version,
        url="https://github.com/airbrake/pybrake"
    ),
    os=platform.platform(),
    language=f"Python/{platform.python_version()}",
    hostname=socket.gethostname(),
    versions=dict(python=platform.python_version()),
)


class Notifier:
    """
    Notifier is used to generate an error notification from an exception
    object, as well as application performance statistics (Route,
    Route breakdown, Query, Queue), and send it to Airbrake.
    """

    def __init__(
            self, *, project_id=0, project_key="", host=AIRBRAKE_HOST, **kwargs
    ):
        """
        Constructor that defines a particular configuration for the notifier
        object.
        :param project_id: Integer Airbrake project id.
        :param project_key: Secret key of Airbrake project in string format.
        :param performance_stats: Enable/disable performance monitoring,
                default: True.
        :param query_stats: Enable/disable query stats monitoring,
                default: True.
        :param queue_stats: Enable/disable queue stats monitoring,
                default: True.
        :param max_queue_size: Maximum number for thread pool queue size,
                default value 1000.
        :param max_workers: Maximum number of thread pool can make by
                Notifier, default value number CPU count * 5.
        :param root_directory: Root directory path of project.
        :param environment: Project running environment, Like: development,
                testing, production. Can make own environment.
        :param keys_blocklist: To transmit an airbrake on an error
                notification, a list of parameter's value must be blocked.,
                default value [re.compile("password"), re.compile("secret")]
        :param remote_config: Set up configuration from the Airbrake server,
                default value False
        :param max_backlog_size: Set up length of failed stats queue
        :param backlog_enabled: If backlog_enabled set as true then
                pybrake will manage failed stats and error notification and
                try to send it again. Default value: False
        """

        self.config = {
            "error_notifications": True,
            "performance_stats": kwargs.get("performance_stats", True),
            "query_stats": kwargs.get("query_stats", True),
            "queue_stats": kwargs.get("queue_stats", True),
            "max_backlog_size": kwargs.get("max_backlog_size", 100),
            "backlog_enabled": kwargs.get("backlog_enabled", True),
            "error_host": host,
            "apm_host": host,
        }
        kwargs["config"] = self.config

        self.routes = _Routes(
            project_id=project_id, project_key=project_key, **kwargs
        )
        self.queries = QueryStats(
            project_id=project_id,
            project_key=project_key,
            host=host,
            **kwargs
        )
        self.queues = QueueStats(
            project_id=project_id,
            project_key=project_key,
            host=host,
            **kwargs
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
        self._context["rootDirectory"] = kwargs.get("root_directory",
                                                    os.getcwd())
        self._backlog = None
        if self.config.get('backlog_enabled'):
            if metrics.Error_Backlog is None:
                metrics.Error_Backlog = Backlog(
                    header=self._ab_headers,
                    method="POST",
                    maxlen=self.config.get('max_backlog_size'),
                    error_notice=True,
                    notifier=self,
                )
            self._backlog = metrics.Error_Backlog

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
                AIRBRAKE_CONFIG_HOST,
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
        for fn in self._filters[::-1]:
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

        return metrics.send_notice(
            notifier=self, notice=notice, url=self._ab_url,
            headers=self._ab_headers, method="POST"
        )

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
        """
        Asynchronously notifies Airbrake about exception from separate thread.

        Returns concurrent.futures.Future.
        """
        notice = self.build_notice(err)
        return self.send_notice(notice)

    def send_notice(self, notice):
        """
        Asynchronously sends notice to Airbrake from separate thread.

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
        error = dict(type=err.__class__.__name__, message=str(err),
                     backtrace=backtrace)
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
        frame = dict(file=self._clean_filename(filename), function=func,
                     line=line)

        lines = get_code_hunk(filename, line, loader=loader,
                              module_name=module_name)
        if lines is not None:
            frame["code"] = lines

        return frame

    def _clean_filename(self, s):
        if "/lib/python" in s and "/site-packages/" in s:
            needed = "/site-packages/"
            ind = s.find(needed)
            if ind > -1:
                s = "/SITE_PACKAGES/" + s[ind + len(needed):]
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
            self._thread_pool = futures.ThreadPoolExecutor(
                max_workers=self._max_workers)
        return self._thread_pool


def pybrake_error_filter(notice):
    backtrace = []
    for frame in notice["errors"][0]["backtrace"]:
        path = Path(frame["file"])
        if (
                (
                        path.parent.name == "middleware" and
                        path.parent.parent and
                        path.parent.parent.name == 'pybrake'
                ) or
                path.parent.name == "pybrake"
        ):
            continue
        backtrace.append(frame)
    notice["errors"][0]["backtrace"] = backtrace
    return notice
