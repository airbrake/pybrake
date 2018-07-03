import re
import collections.abc

from .notice import _NOTICE_KEYS


_FILTERED = '[Filtered]'


def make_blacklist_filter(keys_blacklist):
  def blacklist_filter(notice):
    for key in _NOTICE_KEYS:
      if key in notice:
        filter_dict(notice[key], keys_blacklist)
    return notice

  return blacklist_filter


def filter_dict(d, keys_blacklist):
  for key, value in d.items():
    if is_blacklisted(key, keys_blacklist):
      d[key] = _FILTERED
      continue
    if isinstance(value, collections.abc.Mapping):
      filter_dict(value, keys_blacklist)


def is_blacklisted(key, keys_blacklist):
  for k in keys_blacklist:
    if k == key:
      return True
    if isinstance(k, re._pattern_type):
      if k.match(key):
        return True
  return False
