#!/usr/bin/env python3
"""Extract per-token fence/attention records from a kvwait .bin file.

Record: three little-endian uint64 (t0_tsc, dur, tag). Tags:
  7600 F3 bracket (end = t0+dur = Fence 3 instant)
  7601 F1 bracket (end = Fence 1 instant)
  7602 extend enqueued instant (dur = num_tokens_seen payload)
  7603 attention released, op 0 (dur = batch items payload)
  7604 attention joined, op 35 (dur = batch items payload)
Per token (bounded by consecutive F3 ends): period, legs, attention span,
extend lead (extend instant minus the F3 that closes its token; negative =
enqueued before F3). TSC at 2.7 GHz (3bda base clock) unless --tsc-ghz.
"""
import struct, sys, statistics as st

def load(path):
    b = open(path, 'rb').read()
    n = struct.unpack('<Q', b[:8])[0]
    recs = []
    for i in range(min(n, (len(b)-8)//24)):
        t0, dur, tag = struct.unpack_from('<QQQ', b, 8+24*i)
        recs.append((t0, dur, tag))
    recs.sort(key=lambda r: r[0])
    return recs

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    check = '--check' in sys.argv
    ghz = 2.7
    for a in sys.argv[1:]:
        if a.startswith('--tsc-ghz='): ghz = float(a.split('=')[1])
    recs = load(args[0])
    tags = {t: [r for r in recs if r[2] == t] for t in (7600, 7601, 7602, 7603, 7604)}
    if check:
        missing = [t for t, v in tags.items() if not v]
        print('records:', len(recs), {t: len(v) for t, v in tags.items()})
        sys.exit(1 if missing else 0)
    f3 = [(t0+dur) for t0, dur, _ in tags[7600]]
    f1 = [(t0+dur) for t0, dur, _ in tags[7601]]
    a0 = [t0 for t0, _, _ in tags[7603]]
    a1 = [t0 for t0, _, _ in tags[7604]]
    ex = [t0 for t0, _, _ in tags[7602]]
    rows = []
    for i in range(1, len(f3)):
        lo, hi = f3[i-1], f3[i]
        f1s  = [x for x in f1 if lo < x <= hi]
        a0s  = [x for x in a0 if lo < x <= hi]
        a1s  = [x for x in a1 if lo < x <= hi]
        exs  = [x for x in ex if lo < x <= hi]
        if len(f1s) != 1 or len(a0s) != 1 or len(a1s) != 1:
            continue  # prefill chunks / warmup windows
        c = 1e3/(ghz*1e9)*1e6  # cycles -> us
        rows.append(dict(period=(hi-lo)*c, f3f1=(f1s[0]-lo)*c, f1f3=(hi-f1s[0])*c,
                         attn=(a1s[0]-a0s[0])*c,
                         extend_lead=((exs[0]-hi)*c if exs else float('nan'))))
    if not rows:
        print('no complete decode windows'); sys.exit(1)
    def q(v, p): 
        v = sorted(v); return v[int(p*(len(v)-1))]
    print(f'windows: {len(rows)}   (all times us, TSC {ghz} GHz)')
    for k in ('period', 'f3f1', 'f1f3', 'attn', 'extend_lead'):
        v = [r[k] for r in rows if r[k] == r[k]]
        if v:
            print(f'{k:12} median {st.median(v):10.1f}  p10 {q(v,.1):10.1f}  p90 {q(v,.9):10.1f}  n={len(v)}')

if __name__ == '__main__':
    main()
