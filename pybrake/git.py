import os
from functools import lru_cache

from .utils import logger


@lru_cache(maxsize=1000)
def get_git_revision(dirpath):
    try:
        return _get_git_revision(dirpath)
    except (OSError, IOError) as err:
        logger.error("get_git_revision failed: %s", err)
        return None


def _get_git_revision(dirpath):
    head = get_git_head(dirpath)

    prefix = "ref: "
    if not head.startswith(prefix):
        return head
    head = head[len(prefix) :]

    ref_file = os.path.join(dirpath, ".git", head)
    try:
        with open(ref_file) as f:
            return f.read().rstrip()
    except (OSError, IOError):
        pass

    refs_file = os.path.join(dirpath, ".git", "packed-refs")
    with open(refs_file) as f:
        for line in f:
            if not line or line[0] in ("#", "^"):
                continue

            parts = line.rstrip().split(" ")
            if len(parts) != 2:
                continue

            if parts[1] == head:
                return parts[0]

    return None


def get_git_head(dirpath):
    head_file = os.path.join(dirpath, ".git", "HEAD")
    with open(head_file) as f:
        return f.read().rstrip()


def find_git_dir(directory):
    """Returns first directory containing .git file checking the dir and parent dirs."""
    directory = os.path.abspath(directory)
    if not os.path.exists(directory):
        return ""

    for _ in range(10):
        path = os.path.join(directory, ".git")
        if os.path.exists(path):
            return directory

        if directory == "/":
            return ""

        directory = os.path.abspath(os.path.join(directory, os.pardir))

    return ""
