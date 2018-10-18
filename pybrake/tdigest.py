import struct

import tdigest


SMALL_ENCODING = 2


def from_bytes(b):
  encoding = int.from_bytes(b[:4], byteorder='big')
  if encoding != SMALL_ENCODING:
    raise ValueError('unsupported encoding version: %s' % encoding)

  compression = struct.unpack('>d', b[4:12])[0]
  num_centroids = int.from_bytes(b[12:16], byteorder='big')
  if num_centroids < 0 or num_centroids > 1<<22:
    raise ValueError('bad number of centroids')

  b = b[16:]
  digest = tdigest.TDigest(K=int(compression))

  x = 0
  means = []
  for i in range(num_centroids):
    delta = struct.unpack('>f', b[:4])[0]
    b = b[4:]
    x += delta
    means.append(x)

  stream = decode_varint_stream(b)
  for i in range(num_centroids):
    count = next(stream)
    digest.update(means[i], count)

  return digest


def as_bytes(digest):
  b = bytearray()

  b += SMALL_ENCODING.to_bytes(4, byteorder='big')
  b += struct.pack('>d', digest.K)
  b += len(digest).to_bytes(4, byteorder='big')

  x = 0
  for key in digest.C.keys():
    delta = key - x
    x = key
    b += struct.pack('>f', delta)

  for value in digest.C.values():
    encode_varint(b, int(value.count))

  return b


def encode_varint(b, num):
  while True:
    c = num & 0x7f
    num >>= 7
    if num:
      b += bytes([c | 0x80])
    else:
      b += bytes([c])
      break


def decode_varint_stream(b):
  value = 0
  base = 1
  for c in b:
    value += (c & 0x7f) * base
    if c & 0x80:
      base <<= 7
    else:
      yield value
      value = 0
      base = 1
