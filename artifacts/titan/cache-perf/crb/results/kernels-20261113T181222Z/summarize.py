#!/usr/bin/env python3
"""Print best, median and lowest rate per (file, size, kernel, binary) from the two csv files in this folder."""
import re, statistics as st, collections
def load(fn):
    d = collections.defaultdict(list); loads = []
    for l in open(fn):
        l = l.strip()
        m = re.match(r'-- binary (\S+) kernel (\S+) threads (\d+) cpus (\S+) bytes (\S+) round (\d) load (\S+)', l)
        if m:
            ctx = m.groups(); loads.append(float(ctx[6])); continue
        p = l.split(',')
        if len(p) > 6 and p[3].isdigit():
            assert p[0] == ctx[1]
            d[ctx[4], ctx[1], ctx[0]].append(float(p[6]))
    return d, loads
if __name__ == '__main__':
    for fn in ('one-thread.csv', 'threads120.csv'):
        d, loads = load(fn)
        print(fn, 'load at process start: min', min(loads), 'max', max(loads), '| repetitions per cell:', set(len(v) for v in d.values()))
        for b in dict.fromkeys(k[0] for k in d):
            for k in ('read', 'asmread', 'write', 'asmwrite', 'copy', 'asmcopy'):
                o = d[b, k, 'bw_old']; n = d[b, k, 'bw_new']
                print(f'{b:5} {k:9} old best {max(o):8.2f} med {st.median(o):8.2f} min {min(o):8.2f} | new best {max(n):8.2f} med {st.median(n):8.2f} min {min(n):8.2f} | new/old best {max(n)/max(o):.4f} med {st.median(n)/st.median(o):.4f}')
