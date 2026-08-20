#!/usr/bin/env python3
"""HBM allocation audit: per draw, sha256 of the ordered (dev, addr, size)
allocation sequence (tag 7900+dev), plus counts and total bytes.
Identical hashes across draws => per-launch HBM placement identical."""
import struct, sys, hashlib
raw = open(sys.argv[1], "rb").read()
n = struct.unpack_from("<Q", raw, 0)[0]
n = min(n, (len(raw) - 8) // 24)
allocs = []
for i in range(n):
    addr, size, tag = struct.unpack_from("<QQQ", raw, 8 + 24 * i)
    if 7900 <= tag < 7999:
        allocs.append((tag - 7900, addr, size))
h = hashlib.sha256(repr(allocs).encode()).hexdigest()[:16]
tot = sum(a[2] for a in allocs)
devs = sorted(set(a[0] for a in allocs))
print(f"{len(allocs)},{h},{tot},{devs}")
