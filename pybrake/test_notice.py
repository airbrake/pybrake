import collections
import pytest

from .notice import jsonify_notice


def make_defaultdict():
  d = collections.defaultdict()
  for i in range(100000):
    d[i] = i
  return d


@pytest.mark.parametrize('param, wanted_size', [
  (list(range(100000)), 558),
  (set(range(100000)), 558),
  ({i:i for i in range(100000)}, 1339),
  ('x' * 100000, 1049),
  (b'x' * 100000, 1049),
  (bytearray([64] * 100000), 1049),
  (bytearray([64] * 100000 + [128]), 1049), # UnicodeDecodeError
  (make_defaultdict(), 1339),
  (collections.OrderedDict({i:i for i in range(100000)}), 1339),
  (collections.UserDict({i:i for i in range(100000)}), 1339),
  (collections.UserList(range(100000)), 558),
  (collections.UserString('x' * 100000), 1049),
  (collections.UserString(b'x' * 100000), 1049),
])
def test_truncation(param, wanted_size):
  notice = dict(
    params=dict(param=param),
  )

  b = jsonify_notice(notice)
  assert len(b) == wanted_size
