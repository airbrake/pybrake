import re
import warnings
from urllib.error import URLError

from .notifier import Notifier
from .utils import time_trunc_minute
from .test_helper import (get_exception, get_nested_exception,
                          get_exception_in_cython, build_notice_from_str)


def test_build_notice_from_exception():
    notifier = Notifier()

    err = get_exception()
    notice = notifier.build_notice(err)

    errors = notice["errors"]
    assert len(errors) == 1

    error = errors[0]
    assert error["type"] == "ValueError"
    assert error["message"] == "hello"

    backtrace = error["backtrace"]
    assert len(backtrace) == 1

    frame = backtrace[0]
    assert frame["file"] == "/PROJECT_ROOT/pybrake/test_helper.py"
    assert frame["function"] == "get_exception"
    assert frame["line"] == 6
    assert frame["code"] == {
        4: "def get_exception():",
        5: "    try:",
        6: '        raise ValueError("hello")',
        7: "    except ValueError as err:",
        8: "        return err",
    }

    context = notice["context"]
    assert context["notifier"]["name"] == "pybrake"
    assert context["notifier"]["url"] == "https://github.com/airbrake/pybrake"
    assert context["notifier"]["version"]

    for k in ["os", "language", "hostname", "versions", "revision"]:
        assert context[k]


def test_build_notice_from_exception_cython():
    notifier = Notifier()

    err = get_exception_in_cython()
    notice = notifier.build_notice(err)

    errors = notice["errors"]
    assert len(errors) == 1

    error = errors[0]
    assert error["type"] == "TypeError"

    message = error["message"]
    if message.startswith('unorderable'):
        # python 3.5
        assert error["message"] == 'unorderable types: str() < int()'
    else:
        # python 3.6 and above
        assert error["message"] == "'<' not supported between instances of 'str' and 'int'"


def test_build_notice_from_nested_exception():
    notifier = Notifier()

    err = get_nested_exception()
    notice = notifier.build_notice(err)

    errors = notice["errors"]
    assert len(errors) == 2

    error = errors[0]
    assert error["type"] == "ValueError"
    assert error["message"] == "world"

    backtrace = error["backtrace"]
    assert len(backtrace) == 1

    frame = backtrace[0]
    assert frame["file"] == "/PROJECT_ROOT/pybrake/test_helper.py"
    assert frame["function"] == "get_nested_exception"
    assert frame["line"] == 51

    error = errors[1]
    assert error["type"] == "ValueError"
    assert error["message"] == "hello"

    backtrace = error["backtrace"]
    assert len(backtrace) == 2

    frame = backtrace[0]
    assert frame["file"] == "/PROJECT_ROOT/pybrake/test_helper.py"
    assert frame["function"] == "get_exception"
    assert frame["line"] == 6


def test_build_notice_from_str():
    notifier = Notifier()

    notice = build_notice_from_str(notifier, "hello")

    errors = notice["errors"]
    assert len(errors) == 1

    error = errors[0]
    assert error["message"] == "hello"

    backtrace = error["backtrace"]
    assert len(backtrace) >= 1

    frame = backtrace[0]
    assert frame["file"] == "/PROJECT_ROOT/pybrake/test_helper.py"
    assert frame["function"] == "build_notice_from_str"
    assert frame["line"] == 12
    assert frame["code"] == {
        10: "",
        11: "def build_notice_from_str(notifier, s):",
        12: "    return notifier.build_notice(s)",
        13: "",
        14: "",
    }


def test_build_notice_from_none():
    notifier = Notifier()
    notice = notifier.build_notice(None)

    errors = notice["errors"]
    assert not errors


def test_environment():
    notifier = Notifier(environment="production")

    notice = notifier.build_notice("hello")

    assert notice["context"]["environment"] == "production"


def test_root_directory():
    notifier = Notifier(root_directory="/root/dir")

    notice = notifier.build_notice("hello")

    assert notice["context"]["rootDirectory"] == "/root/dir"


def test_filter_data():
    def notifier_filter(notice):
        notice["params"]["param"] = "value"
        return notice

    notifier = Notifier()
    notifier.add_filter(notifier_filter)

    notice = notifier.notify_sync("hello")

    assert notice["params"]["param"] == "value"


def test_filter_ignore():
    notifier = Notifier()
    notifier.add_filter(lambda notice: None)

    notice = notifier.notify_sync("hello")

    assert notice["error"] == "notice is filtered out"


def test_filter_ignore_async():
    notifier = Notifier()
    notifier.add_filter(lambda notice: None)

    future = notifier.notify("hello")
    notice = future.result()

    assert notice["error"] == "notice is filtered out"


def test_pybrake_error_filter():
    notifier = Notifier()

    try:
        time_trunc_minute(None)
    except Exception as err:  # pylint: disable=broad-except
        notice = notifier.notify_sync(err)
        assert notice["error"] == "notice is filtered out"


def test_unauthorized():
    notifier = Notifier()

    notice = notifier.notify_sync("hello")

    assert notice["error"] == "Project API key is required"


def test_unknown_host():
    notifier = Notifier(host="http://airbrake123.com")

    notice = notifier.notify_sync("hello")

    assert isinstance(notice["error"], URLError)
    assert "not known>" in str(notice["error"])


def test_truncation():
    notifier = Notifier()

    notice = notifier.build_notice("hello")
    notice["params"]["param"] = "x" * 64000
    notice = notifier.send_notice_sync(notice)

    assert len(notice["params"]["param"]) == 1024


def test_revision_override():
    notifier = Notifier(revision="1234")
    assert notifier._context["revision"] == "1234"


def test_revision_from_git(monkeypatch):
    monkeypatch.setattr("pybrake.notifier.get_git_revision", lambda x: "4321")
    notifier = Notifier()
    assert notifier._context["revision"] == "4321"


def _test_keys_blocklist(keys_blocklist):
    notifier = Notifier(keys_blocklist=keys_blocklist)

    notice = notifier.build_notice("hello")
    notice["params"] = dict(key1="value1", key2="value2", key3=dict(key1="value1"))
    notice = notifier.send_notice_sync(notice)

    assert notice["params"] == {
        "key1": "[Filtered]",
        "key2": "value2",
        "key3": {"key1": "[Filtered]"},
    }


def _test_deprecated_filter_keys(keys_blacklist):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        notifier = Notifier(keys_blacklist=keys_blacklist)
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        deprecation_message = "keys_blacklist is a deprecated option. "\
                              "Use keys_blocklist instead."
        assert deprecation_message in str(w[-1].message)

    notice = notifier.build_notice("hello")
    notice["params"] = dict(key1="value1", key2="value2", key3=dict(key1="value1"))
    notice = notifier.send_notice_sync(notice)

    assert notice["params"] == {
        "key1": "[Filtered]",
        "key2": "value2",
        "key3": {"key1": "[Filtered]"},
    }


def test_keys_blocklist_exact():
    _test_keys_blocklist(["key1"])
    _test_deprecated_filter_keys(["key1"])


def test_keys_blocklist_regexp():
    _test_keys_blocklist([re.compile("key1")])
    _test_deprecated_filter_keys([re.compile("key1")])


def _test_full_queue():
    notifier = Notifier(max_queue_size=10)

    for _ in range(100):
        future = notifier.notify("hello")

    notifier.close()

    notice = future.result()
    assert notice["error"] == "queue is full"


def _test_rate_limited():
    notifier = Notifier()

    for _ in range(101):
        future = notifier.notify("hello")

    notice = future.result()
    assert notice["error"] == "IP is rate limited"


def test_clean_filename():
    notifier = Notifier()

    filename = notifier._clean_filename("home/lib/python3.6/site-packages/python.py")
    assert filename == "/SITE_PACKAGES/python.py"

def test_error_notifications_disabled():
    notifier = Notifier()
    notifier.config["error_notifications"] = False

    future = notifier.notify("hello")
    notifier.close()

    notice = future.result()
    assert notice["error"] == "error notifications are disabled"
