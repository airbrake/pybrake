import json
import collections.abc


_MAX_JSON_SIZE = 64000 # 64kb
_NOTICE_KEYS = ['context', 'params', 'session', 'environment']


def jsonify_notice(notice):
  b = json.dumps(notice)
  if len(b) < _MAX_JSON_SIZE:
    return b.encode('utf8')

  t = Truncator(0)
  for i, error in enumerate(notice['errors']):
    notice['errors'][i] = t.truncate_dict(error)

  for level in range(10):
    b = json.dumps(notice)
    if len(b) < _MAX_JSON_SIZE:
      break

    t = Truncator(level)
    for key in _NOTICE_KEYS:
      notice[key] = t.truncate_dict(notice[key])

  return b.encode('utf8')


class Truncator:
  def __init__(self, level=0):
    self.max_dict_len = scale(128, level)
    self.max_list_len = scale(128, level)
    self.max_str_len = scale(1024, level)

  def truncate_dict(self, d):
    res = dict()
    i = 0
    for k, v in d:
      res[k] = self.truncate(v)
      i += 1
      if i >= self.max_dict_len:
        break
    return res

  def truncate_list(self, l):
    res = list()
    for i, v in enumerate(l):
      res.append(self.truncate(v))
      if i >= self.max_list_len:
        break
    return res

  def truncate_str(self, s):
    if len(s) <= self.max_str_len:
      return s
    return s[:self.max_str_len]

  def truncate(self, v):
    if isinstance(v, collections.abc.Mapping):
      return self.truncate_dict(v)

    if isinstance(v, collections.abc.Iterable):
      return self.truncate_list(v)

    if isinstance(v, (str, bytearray)):
      return self.truncate_str(v)

    return v


def scale(num, level):
  return (num >> level) or 1
