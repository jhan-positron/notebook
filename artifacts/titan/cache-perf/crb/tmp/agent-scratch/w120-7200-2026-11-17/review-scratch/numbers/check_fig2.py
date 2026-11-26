import re, sys, os, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lookup import value_at
def r2(x): return '%.2f' % x
total_dots = 0
allrows = {}
for name, x0, v0, k in (('fig2L', 190.0, 458.0, (450-190)/18.0), ('fig2R', 190.0, 276.0, (450-190)/64.0)):
    v = open(name + '.svg.txt').read()
    # ticks
    for m in re.finditer(r'<text x="([\d.]+)" y="60.0"[^>]*>(\d+)</text>', v):
        px, val = float(m.group(1)), float(m.group(2))
        if abs(px - (x0 + (val - v0) * k)) > 0.06: print('TICK MISMATCH', name, px, val)
    bad = 0
    rows = collections.OrderedDict()
    for body in re.findall(r'<g class="pt">\n(.*?)</g>', v, flags=re.S):
        t = re.search(r'<title>(.*?)</title>', body, flags=re.S).group(1)
        total_dots += 1
        m = re.search(r': ([\d.]+) GB/s\. Row: ([\d.]+) to ([\d.]+) GB/s, n = (\d+) intervals? / (\d+) process(?:es)?\. Source: R/(\S+) line (\d+)\.$', t)
        if not m: print('UNPARSED', t); bad += 1; continue
        val, lo, hi, n, npr, f, line = float(m.group(1)), m.group(2), m.group(3), int(m.group(4)), int(m.group(5)), m.group(6), int(m.group(7))
        raw = value_at(f, line)
        if r2(raw['v']) != r2(val): print('VALUE MISMATCH', t, raw['v']); bad += 1
        cx = float(re.search(r'<circle class="mk" cx="([\d.]+)"', body).group(1))
        ex = x0 + (raw['v'] - v0) * k
        if abs(cx - ex) > 0.06: print('CX MISMATCH', t[:80], cx, ex); bad += 1
        rowname = t.split(': ')[0]
        # round / pos / prev checks for bwx
        mm = re.search(r'process (\S+), round (\d), position (\d), directly after (.*?): [\d.]+ GB/s', t)
        if mm:
            if int(mm.group(2)) != raw['round']: print('ROUND MISMATCH', t); bad += 1
            if int(mm.group(3)) != raw['pos']: print('POS MISMATCH', t); bad += 1
            prev = mm.group(4)
            rp = raw['prev']
            if rp is None:
                if not prev.startswith('none'): print('PREV MISMATCH', t, rp); bad += 1
            else:
                if not prev.startswith(rp): print('PREV MISMATCH', t, rp); bad += 1
            kern = re.search(r': (\S+) \(', t).group(1)
            if kern != raw['kernel']: print('KERNEL MISMATCH', t, raw['kernel']); bad += 1
        else:
            mm = re.search(r'process (\d+) of the file, round (\d), interval (\d)', t)
            if not mm: print('UNPARSED2', t); bad += 1
            else:
                import raw as rawmod
                procs = rawmod.parse_bw(os.path.join(rawmod.R, f))
                idx = [i for i, p in enumerate(procs) if p['line'] == raw['hline']][0] + 1
                if idx != int(mm.group(1)): print('PROC IDX MISMATCH', t, idx); bad += 1
                if raw['rep'] + 1 != int(mm.group(3)): print('INTERVAL IDX MISMATCH', t); bad += 1
                # binary / round
                h = raw['hdr']
                bn = re.search(r': (bw_\w+) read', t).group(1)
                if ('binary ' + bn) not in h: print('BINARY MISMATCH', t, h); bad += 1
                rr = re.search(r'round (\d)', h)
                rnd = int(rr.group(1)) if rr else int(re.search(r'-r(\d) ', h).group(1)) if re.search(r'-r(\d) ', h) else None
                if rnd is not None and rnd != int(mm.group(2)): print('ROUND MISMATCH A', t, h); bad += 1
                if raw['kernel'] != 'read': print('KERNEL A', t)
        fill = re.search(r'<circle class="mk"[^>]*fill="([^"]+)"(?: stroke="([^"]+)")?', body).groups()
        rows.setdefault((name, rowname), []).append(dict(v=raw['v'], lo=lo, hi=hi, n=n, npr=npr, f=f, fill=fill, cy=float(re.search(r'<circle class="mk" cx="[\d.]+" cy="([\d.]+)"', body).group(1)), cx=cx))
    for (nm, rowname), ds in rows.items():
        vs = [d['v'] for d in ds]
        st = 'ok'
        if r2(min(vs)) != ds[0]['lo'] or r2(max(vs)) != ds[0]['hi']: st = 'ROW RANGE MISMATCH'; bad += 1
        if len(vs) != ds[0]['n']: st += ' N MISMATCH'; bad += 1
        nf = len(set(d['f'] for d in ds))
        fills = set(d['fill'] for d in ds)
        print('%-6s %-95s n=%d (page %d / %d proc; files %d) %s to %s  fills %s %s' % (nm, rowname[:95], len(vs), ds[0]['n'], ds[0]['npr'], nf, r2(min(vs)), r2(max(vs)), fills, st))
    print(name, 'bad', bad)
    allrows.update(rows)
print('total dots', total_dots)
import pickle
pickle.dump({k: [d['v'] for d in v] for k, v in allrows.items()}, open('fig2rows.pkl', 'wb'))
