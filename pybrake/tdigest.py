import base64
import struct
import tdigest


class TDigestStat:
    __slots__ = ("count", "sum", "sumsq", "td", "tdigest")

    def __init__(self):
        self.count = 0
        self.sum = 0
        self.sumsq = 0
        self.td = tdigest.TDigest(K=10)
        self.tdigest = None

    @property
    def __dict__(self):
        b = as_bytes(self.td)
        self.tdigest = base64.b64encode(b).decode("ascii")
        return {s: getattr(self, s) for s in self.__slots__ if s != "td"}

    def add(self, ms):
        self.count += 1
        self.sum += ms
        self.sumsq += ms * ms
        self.td.update(ms)


class TDigestStatGroups(TDigestStat):
    __slots__ = TDigestStat.__slots__ + ("groups",)

    def __init__(self):
        super().__init__()
        self.groups = {}

    def add_groups(self, total_ms, groups):
        self.add(total_ms)

        for name, ms in groups.items():
            self.add_group(name, ms)

    def add_group(self, name, ms):
        stat = self.groups.get(name)
        if stat is None:
            stat = TDigestStat()
            self.groups[name] = stat
        stat.add(ms)


_SMALL_ENCODING = 2


def from_bytes(b):
    encoding = int.from_bytes(b[:4], byteorder="big")
    if encoding != _SMALL_ENCODING:
        raise ValueError("unsupported encoding version: %s" % encoding)

    compression = struct.unpack(">d", b[4:12])[0]
    num_centroids = int.from_bytes(b[12:16], byteorder="big")
    if num_centroids < 0 or num_centroids > 1 << 22:
        raise ValueError("bad number of centroids")

    b = b[16:]
    digest = tdigest.TDigest(K=int(compression))

    x = 0
    means = []
    for i in range(num_centroids):
        delta = struct.unpack(">f", b[:4])[0]
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

    b += _SMALL_ENCODING.to_bytes(4, byteorder="big")
    b += struct.pack(">d", digest.K)
    b += len(digest).to_bytes(4, byteorder="big")

    x = 0
    for key in digest.C.keys():
        delta = key - x
        x = key
        b += struct.pack(">f", delta)

    for value in digest.C.values():
        encode_varint(b, int(value.count))

    return b


def encode_varint(b, num):
    while True:
        c = num & 0x7F
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
        value += (c & 0x7F) * base
        if c & 0x80:
            base <<= 7
        else:
            yield value
            value = 0
            base = 1
