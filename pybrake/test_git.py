import os

from .git import find_git_dir


def test_find_git_dir():
    work_dir = os.getcwd()

    tests = [
        {"dir": "", "ok": True},
        {"dir": "./", "ok": True},
        {"dir": "...", "ok": False},
        {"dir": "../pybrake", "ok": True},
        {"dir": work_dir, "ok": True},
        {"dir": os.path.join(work_dir, "pybrake"), "ok": True},
        {"dir": os.path.join(work_dir, "pybrake", "__pycache__"), "ok": True},
        {"dir": "../", "ok": False},
        {"dir": "abc", "ok": False},
        {"dir": os.path.join(work_dir, "abc"), "ok": False},
        {"dir": os.path.join(work_dir, ".."), "ok": False},
    ]

    for test in tests:
        git_dir = find_git_dir(test["dir"])
        if test["ok"]:
            assert git_dir == work_dir
        else:
            assert git_dir == ""
