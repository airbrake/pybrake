import re
from urllib.error import URLError

from .notifier import Notifier
from .test_helper import get_exception, build_notice_from_str


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
    assert frame["line"] == 3
    assert frame["code"] == {
        1: "def get_exception():",
        2: "    try:",
        3: '        raise ValueError("hello")',
        4: "    except ValueError as err:",
        5: "        return err",
    }

    context = notice["context"]
    assert context["notifier"]["name"] == "pybrake"
    assert context["notifier"]["url"] == "https://github.com/airbrake/pybrake"
    assert context["notifier"]["version"]

    for k in ["os", "language", "hostname", "versions", "revision"]:
        assert context[k]


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
    assert frame["line"] == 9
    assert frame["code"] == {
        7: "",
        8: "def build_notice_from_str(notifier, s):",
        9: "    return notifier.build_notice(s)",
        10: "",
        11: "",
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


def _test_keys_blacklist(keys_blacklist):
    notifier = Notifier(keys_blacklist=keys_blacklist)

    notice = notifier.build_notice("hello")
    notice["params"] = dict(key1="value1", key2="value2", key3=dict(key1="value1"))
    notice = notifier.send_notice_sync(notice)

    assert notice["params"] == {
        "key1": "[Filtered]",
        "key2": "value2",
        "key3": {"key1": "[Filtered]"},
    }


def test_keys_blacklist_exact():
    _test_keys_blacklist(["key1"])


def test_keys_blacklist_regexp():
    _test_keys_blacklist([re.compile("key1")])


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
