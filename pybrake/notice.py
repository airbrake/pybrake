import json
import collections
import collections.abc


_MAX_JSON_SIZE = 64000 # 64kb
_NOTICE_KEYS = ['context', 'params', 'session', 'environment']


def jsonify_notice(notice):
  b = _jsonify(notice)
  if len(b) < _MAX_JSON_SIZE:
    return b.encode('utf8')

  if 'errors' in notice:
    t = Truncator(0)
    for i, error in enumerate(notice['errors']):
      notice['errors'][i] = t.truncate_dict(error)

  for level in range(10):
    b = _jsonify(notice)
    if len(b) < _MAX_JSON_SIZE:
      break

    t = Truncator(level)
    for key in _NOTICE_KEYS:
      if key in notice:
        notice[key] = t.truncate_dict(notice[key])

  return b.encode('utf8')


def _jsonify(obj):
  return json.dumps(obj, default=set_default)


def set_default(obj):
  if isinstance(obj, set):
    return list(obj)
  if isinstance(obj, (bytes, bytearray)):
    return obj.decode('utf8', 'replace')
  if isinstance(obj, (collections.UserDict,
                      collections.UserList,
                      collections.UserString)):
    return obj.data
  return str(obj)


class Truncator:
  def __init__(self, level=0):
    self._max_dict_len = _scale(128, level)
    self._max_list_len = _scale(128, level)
    self._max_str_len = _scale(1024, level)

  def truncate_dict(self, d):
    res = dict()
    i = 0
    for k, v in d.items():
      res[k] = self.truncate(v)
      i += 1
      if i >= self._max_dict_len:
        break
    return res

  def truncate_list(self, l):
    res = list()
    for i, v in enumerate(l):
      res.append(self.truncate(v))
      if i >= self._max_list_len:
        break
    return res

  def truncate_str(self, s):
    if len(s) <= self._max_str_len:
      return s
    return s[:self._max_str_len]

  def truncate(self, v):
    if isinstance(v, str):
      return self.truncate_str(v)
    if isinstance(v, (bytes, bytearray)):
      return self.truncate_str(v.decode('utf8', 'replace'))
    if isinstance(v, collections.UserString):
      return self.truncate_str(v.data)

    if isinstance(v, collections.abc.Mapping):
      return self.truncate_dict(v)

    if isinstance(v, collections.abc.Iterable):
      return self.truncate_list(v)

    return v


def _scale(num, level):
  return (num >> level) or 1
