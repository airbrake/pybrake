import pytest

from .notice import jsonify_notice



@pytest.mark.parametrize('param, wanted_size', [
  (list(range(100000)), 558),
  (set(range(100000)), 558),
  ({i:i for i in range(100000)}, 1339),
  ('x' * 100000, 1049),
  (b'x' * 100000, 1049),
  (bytearray([64] * 100000), 1049),
  (bytearray([64] * 100000 + [128]), 1049), # UnicodeDecodeError
])
def test_truncation(param, wanted_size):
  notice = dict(
    params=dict(param=param),
  )

  b = jsonify_notice(notice)
  assert len(b) == wanted_size
