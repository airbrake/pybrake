import re
import collections.abc

from .notice import _NOTICE_KEYS


_FILTERED = "[Filtered]"


def make_blocklist_filter(keys_blocklist):
    def blocklist_filter(notice):
        for key in _NOTICE_KEYS:
            if key in notice:
                _filter_dict(notice[key], keys_blocklist)
        return notice

    return blocklist_filter


def _filter_dict(d, keys_blocklist):
    for key, value in d.items():
        if _is_blocklisted(key, keys_blocklist):
            d[key] = _FILTERED
            continue
        if isinstance(value, collections.abc.Mapping):
            _filter_dict(value, keys_blocklist)


def _is_blocklisted(key, keys_blocklist):
    for k in keys_blocklist:
        if k == key:
            return True
        if _is_regexp(k) and k.match(key):
            return True
    return False


try:
    _pattern_type = re._pattern_type
except AttributeError:
    try:
        _pattern_type = re.Pattern
    except AttributeError:
        pass


def _is_regexp(v):
    return isinstance(v, _pattern_type)
