#!/usr/bin/env python3
"""Per-token pure-attention time from stamp 7605 (worker-0 attention wall, TSC cycles,
summed over the 36 attention operations) in a kvwait .bin file.
Decode-only windows: between consecutive F3 (7600) ends with exactly one 7601, 7602, 7603, 7604, 7605.
Prints medians in microseconds (TSC 2.7 GHz unless --tsc-ghz=)."""
import struct, sys, statistics as st, json

def load(path):
    b = open(path, 'rb').read()
    n = struct.unpack('<Q', b[:8])[0]
    recs = [struct.unpack_from('<QQQ', b, 8 + 24 * i) for i in range(min(n, (len(b) - 8) // 24))]
    recs.sort(key=lambda r: r[0])
    return recs

def windows(recs, ghz):
    tags = {t: [r for r in recs if r[2] == t] for t in (7600, 7601, 7602, 7603, 7604, 7605)}
    f3 = [t0 + d for t0, d, _ in tags[7600]]
    c = 1e6 / (ghz * 1e9)
    rows = []
    for i in range(1, len(f3)):
        lo, hi = f3[i - 1], f3[i]
        inw = {t: [r for r in tags[t] if lo < r[0] <= hi] for t in (7601, 7602, 7603, 7604, 7605)}
        if any(len(v) != 1 for v in inw.values()):
            continue
        f1 = inw[7601][0][0] + inw[7601][0][1]
        rows.append(dict(period=(hi - lo) * c, f3f1=(f1 - lo) * c, f1f3=(hi - f1) * c,
                         span=(inw[7604][0][0] - inw[7603][0][0]) * c,
                         attn=inw[7605][0][1] * c))
    return rows

if __name__ == '__main__':
    ghz = 2.7
    files = []
    for a in sys.argv[1:]:
        if a.startswith('--tsc-ghz='): ghz = float(a.split('=')[1])
        else: files.append(a)
    rows = []
    for f in files:
        rows += windows(load(f), ghz)
    if not rows:
        print('no decode windows'); sys.exit(1)
    out = {'windows': len(rows)}
    for k in ('period', 'f3f1', 'f1f3', 'span', 'attn'):
        v = sorted(r[k] for r in rows)
        out[k] = dict(median=st.median(v), p10=v[int(.1 * (len(v) - 1))], p90=v[int(.9 * (len(v) - 1))])
    print(json.dumps(out))
