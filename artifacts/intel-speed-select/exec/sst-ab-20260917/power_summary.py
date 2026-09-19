#!/usr/bin/env python3
"""Summarize one turbostat capture (5-s samples) of one runtron run.

Usage: power_summary.py power.tsv <app cpu list like 223-224,96-101>
Prints one line of key=value pairs:
  intervals, loaded (intervals whose app-core mean Busy% > 30), app_mhz (mean Bzy_MHz of app cpus with
  Busy% > 50 in loaded intervals), app_mhz_min/max (per-interval means), app_busy, dev_mhz (cpus 75,76,219,220),
  pkg1_w, pkg0_w, total_w, ram_w (means over loaded intervals), app_cpu_mhz_min/max (per-cpu means over loaded
  intervals), app_cpus_fast (app cpus whose mean is above the 2.7 GHz cap), app_cpus_seen.
Loaded intervals cover prefill and decode together; the values show that the arm took effect, they are not
decode-only values.
turbostat layout: one system row (Package "-") per interval, then per-cpu rows; package-level PkgWatt sits
on the first cpu row of each package; the header may repeat.
"""
import sys, statistics as st

def expand(spec):
    out = []
    for tok in spec.split(','):
        tok = tok.strip()
        if not tok: continue
        if '-' in tok:
            a, b = tok.split('-'); out.extend(range(int(a), int(b) + 1))
        else: out.append(int(tok))
    return set(out)

def main():
    path, app = sys.argv[1], expand(sys.argv[2])
    dev = {75, 76, 219, 220}
    cols = None; intervals = []; cur = None
    for line in open(path, errors='replace'):
        f = line.rstrip('\n').split('\t')
        if not f or not f[0]: continue
        if f[0] == 'Package':
            cols = {n: i for i, n in enumerate(f)}; continue
        if cols is None: continue
        def col(n):
            i = cols.get(n); 
            return f[i] if i is not None and i < len(f) and f[i] != '' else None
        if f[0] == '-':
            cur = {'total_w': col('PkgWatt'), 'ram_w': col('RAMWatt'), 'pkg': {}, 'app': [], 'dev': []}
            intervals.append(cur); continue
        if cur is None: continue
        try:
            pkg = int(f[0]); cpu = int(col('CPU')); busy = float(col('Busy%')); mhz = float(col('Bzy_MHz'))
        except (TypeError, ValueError):
            continue
        pw = col('PkgWatt')
        if pw is not None and pkg not in cur['pkg']:
            try: cur['pkg'][pkg] = float(pw)
            except ValueError: pass
        if cpu in app: cur['app'].append((cpu, busy, mhz))
        if cpu in dev: cur['dev'].append((busy, mhz))
    loaded = []
    for iv in intervals:
        if not iv['app']: continue
        mb = st.mean(b for _, b, _ in iv['app'])
        if mb > 30: loaded.append(iv)
    def fmean(vals):
        vals = [v for v in vals if v is not None]
        return st.mean(vals) if vals else None
    out = {'intervals': len(intervals), 'loaded': len(loaded)}
    if loaded:
        per_iv = []
        for iv in loaded:
            m = [mhz for _, b, mhz in iv['app'] if b > 50]
            if m: per_iv.append(st.mean(m))
        out['app_mhz'] = round(st.mean(per_iv)) if per_iv else None
        out['app_mhz_min'] = round(min(per_iv)) if per_iv else None
        out['app_mhz_max'] = round(max(per_iv)) if per_iv else None
        out['app_busy'] = round(st.mean(st.mean(b for _, b, _ in iv['app']) for iv in loaded), 1)
        pm = {}
        for iv in loaded:
            for cpu, b, mhz in iv['app']:
                if b > 50: pm.setdefault(cpu, []).append(mhz)
        pm = {c: st.mean(v) for c, v in pm.items()}
        out['app_cpu_mhz_min'] = round(min(pm.values())) if pm else None
        out['app_cpu_mhz_max'] = round(max(pm.values())) if pm else None
        out['app_cpus_fast'] = sum(1 for v in pm.values() if v > 2800)   # per-cpu mean above the 2.7 GHz CLOS3 cap; boot arm expects 2 (cpus 126,127), tuned/tunedplus 28
        out['app_cpus_seen'] = len(pm)
        dm = [mhz for iv in loaded for b, mhz in iv['dev'] if b > 20]
        out['dev_mhz'] = round(st.mean(dm)) if dm else None
        out['dev_busy'] = round(st.mean(b for iv in loaded for b, _ in iv['dev']), 1) if any(iv['dev'] for iv in loaded) else None
        p1 = fmean([iv['pkg'].get(1) for iv in loaded]); p0 = fmean([iv['pkg'].get(0) for iv in loaded])
        tw = fmean([float(iv['total_w']) if iv['total_w'] else None for iv in loaded])
        rw = fmean([float(iv['ram_w']) if iv['ram_w'] else None for iv in loaded])
        out['pkg1_w'] = round(p1, 1) if p1 is not None else None
        out['pkg0_w'] = round(p0, 1) if p0 is not None else None
        out['total_w'] = round(tw, 1) if tw is not None else None
        out['ram_w'] = round(rw, 1) if rw is not None else None
    print(' '.join(f'{k}={v}' for k, v in out.items()))

if __name__ == '__main__':
    main()
