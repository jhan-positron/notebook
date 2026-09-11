#!/usr/bin/env python3
"""Summarize the G1 store-cost campaign (exec/results/g1-20260908) into summary.md and summary.json.

Words: TTFT = time to first token (ms, mean over the harness's 10 rounds x N users); TPS = decode tokens per
second per user; arm = which binary/switch served the run (off / canon / canon2 / mirror / g1mirror / sonly /
inplace, see g1-campaign.sh). Deltas are relative to the canonical arm at the same user count. The paired
column matches ROUNDS: round k uses the same set of prompts in every arm (systems_test testlib/tps.py seeds by
k*users+i and prunes each prompt to exactly prompt_length tokens); inside a round the harness appends the
per-request samples in completion order, so single positions are not the same prompt and the per-round mean
is what is paired. "prefill tok/s" is 1024 divided by the same TTFT, not a second measurement; the runtron
section's "Parsing the prompt took" values are the independent prefill numbers. Round-1 (2026-09-04) values
at 8 users are printed for reference, including its one A/A pair (off vs off rep2, +0.2% TTFT).
Interpretation: inplace vs canon = the end-to-end single-K proxy against canonical (the G1 kill comparison):
the inplace arm stores K once, in VNNI layout, inside the page's own hugepage K plane, and the AMX kernel
qk_mirror_128x4 reads that plane; the canon arm stores K contiguously and qk_canonical_128x4 reads it. This is
the comparison the gate needs, because production single-K would also use the mirror reader; but the delta
mixes the store cost with the reader difference (2026-09-01 single-attention measurement: mirror 2.66 us vs
canonical 2.89 us per attention unit at prompt 8192, so the mirror reader is about 8% faster per unit), and an
inplace result inside the spread can hide a store cost of that size. Every arm except off / canon / canon2
reads K through qk_mirror_128x4 (rinzler.mirror and rinzler.g1 are K-mirror builds). sonly vs inplace = arena
placement with the same store pattern and the same reader; mirror vs sonly = the extra canonical store plus
re-read (upper bound); g1mirror vs mirror = probe-binary fidelity (same code path, different build);
canon2 vs canon = ONE in-campaign A/A difference of means, an indication of the spread, not a spread estimate.
Probe arms have wrong numerics; their TPS column is timing only.
"""
import glob, json, os, statistics, sys

RES = sys.argv[1] if len(sys.argv) > 1 else '/home/jhan/workspace/intel-AMX/exec/results/g1-20260908'
ROUND1 = {  # model -> arm -> ttft_ms at 8 users (exec/results/more-testing-r1/cells/*/perf.json)
    'ingested-qwen-3-4b-instruct-2507-tp4': {'off': 1777, 'canon': 1618, 'mirror': 2009, 'off_rep2': 1781},
    'llama-3.1-8b-instruct-good-tp2': {'off': 2784, 'canon': 2683, 'mirror': 3148},
}
ARM_ORDER = ['canon', 'canon2', 'inplace', 'sonly', 'mirror', 'g1mirror', 'off']
rows = []
for st in sorted(glob.glob(os.path.join(RES, 'cells', '*', 'STATUS'))):
    cell = os.path.dirname(st); name = os.path.basename(cell)
    try:
        model, arm, u = name.rsplit('__', 2); users = int(u.lstrip('u'))
    except Exception:
        print(f'skipping cell dir with unexpected name: {name}', file=sys.stderr); continue
    d = {'model': model, 'arm': arm, 'users': users, 'status': open(st).read().strip(), 'ttfts': []}
    for f, key in (('meta.json', None), ('perf.json', 'perf')):
        p = os.path.join(cell, f)
        if os.path.exists(p):
            try:
                j = json.load(open(p))
                if key is None: d.update({k: v for k, v in j.items() if k not in ('model', 'arm', 'users')})
                else: d['ttfts'] = list(j.get('ttfts_ms', []))
            except Exception as e:
                d['error'] = f'{f}: {e}'; print(f'{name}: unreadable {f}: {e}', file=sys.stderr)
    rows.append(d)

def pct(a, b): return f'{100.0 * (a - b) / b:+.1f}%' if (a is not None and b) else ''
def paired(arm_t, canon_t, users):
    # per-round means: round k uses the same set of prompts in every arm, but inside a round the harness appends
    # samples in completion order, so single positions are not the same prompt; rounds are.
    n = min(len(arm_t), len(canon_t)) // users
    if n < 3: return ''
    a = [statistics.mean(arm_t[k * users:(k + 1) * users]) for k in range(n)]
    c = [statistics.mean(canon_t[k * users:(k + 1) * users]) for k in range(n)]
    diffs = [a[k] - c[k] for k in range(n)]
    worse = sum(1 for x in diffs if x > 0)
    return f'{statistics.median(diffs):+.0f} ms median over {n} rounds, {worse}/{n} rounds slower'

out = ['# G1 store-cost campaign, 2026-09-08: summary', '', __doc__.strip(), '']
summary = {'cells': [{k: v for k, v in r.items() if k != 'ttfts'} for r in rows], 'tables': {}}
for model in sorted({r['model'] for r in rows}):
    out += [f'## {model}', '', '| users | arm | TTFT ms | dTTFT vs canon | paired rounds vs canon | TPS | dTPS vs canon | sd | prefill tok/s (= 1024 / TTFT) | status | mode line |', '|---|---|---|---|---|---|---|---|---|---|---|']
    tab = []
    for users in sorted({r['users'] for r in rows if r['model'] == model}):
        sub = [r for r in rows if r['model'] == model and r['users'] == users]
        canon = next((r for r in sub if r['arm'] == 'canon' and r.get('ttft_mean_ms')), None)
        for r in sorted(sub, key=lambda r: ARM_ORDER.index(r['arm']) if r['arm'] in ARM_ORDER else 99):
            t, p = r.get('ttft_mean_ms'), r.get('tps_mean')
            dt = pct(t, canon['ttft_mean_ms']) if canon else ''
            dp = pct(p, canon.get('tps_mean')) if (canon and p is not None) else ''
            pr = paired(r['ttfts'], canon['ttfts'], users) if (canon and r['arm'] != 'canon') else ''
            mode = (r.get('dd_g1_line') or '')[-22:]
            if p is not None:
                out.append(f"| {users} | {r['arm']} | {t} | {dt} | {pr} | {p:.2f} | {dp} | {r.get('tps_std_dev') or 0:.2f} | {r.get('prefill_mean_tok_s') or 0:.0f} | {r['status']} | {mode} |")
            else:
                out.append(f"| {users} | {r['arm']} | | | | | | | | {r['status']}{(' (' + r['error'] + ')') if r.get('error') else ''} | |")
            tab.append({'users': users, 'arm': r['arm'], 'ttft_ms': t, 'dttft_vs_canon': dt, 'paired_vs_canon': pr, 'tps': p, 'dtps_vs_canon': dp, 'status': r['status']})
    summary['tables'][model] = tab
    if model in ROUND1:
        r1 = ROUND1[model]
        out += ['', f"Round 1 reference at 8 users (2026-09-04, same binaries, same placement): off {r1['off']} ms, canon {r1['canon']} ms, mirror {r1['mirror']} ms "
                f"(mirror vs canon {pct(r1['mirror'], r1['canon'])})." + (f" Round-1 A/A (off vs off rep2): {pct(r1['off_rep2'], r1['off'])}." if 'off_rep2' in r1 else '')]
    out.append('')
rt = os.path.join(RES, 'runtron-8u8k.txt')
if os.path.exists(rt):
    raw = open(rt).read()
    out += ['## runtron: qwen-3-4b tp2, 8 users, prompt 8192, 256 generated (August placement)', '']
    # per-arm means of "Parsing the prompt took X s" and "average tok/s"
    import re
    arms = {}; cur = None
    for line in raw.splitlines():
        m = re.match(r'### arm=(\S+) rep=(\d)', line)
        if m:
            # every header is an attempt; a BINARY-MISSING header has no run, and a RUN-FAILED / RUN-STOPPED marker
            # below a header takes that attempt back out of the completed count and drops its partial lines
            cur = m.group(1); arms.setdefault(cur, {'parse': [], 'tps': [], 'runs': 0, 'attempts': 0}); arms[cur]['attempts'] += 1
            if 'BINARY-MISSING' in line: cur = None
            else: arms[cur]['runs'] += 1
            continue
        if cur is None: continue
        if line.startswith(('RUN-FAILED', 'RUN-STOPPED')): arms[cur]['runs'] -= 1; cur = None; continue
        m = re.search(r'Parsing the prompt took ([0-9.]+) s', line)
        if m: arms[cur]['parse'].append(float(m.group(1)))
        m = re.search(r'at ([0-9.]+) average tok/s', line)  # the number AFTER "average tok/s" is ms/tok
        if m: arms[cur]['tps'].append(float(m.group(1)))
    out += ['| arm | completed runs / attempts | prefill s per request (mean) | decode tok/s lines (mean) |', '|---|---|---|---|']
    for a, v in arms.items():
        pm = f"{statistics.mean(v['parse']):.2f} ({len(v['parse'])} requests)" if v['parse'] else 'no data'
        tm = f"{statistics.mean(v['tps']):.3f} ({len(v['tps'])} lines)" if v['tps'] else 'no data'
        out.append(f"| {a} | {v['runs']} / {v['attempts']} | {pm} | {tm} |")
    out += ['', '```', raw.strip(), '```', '']
    summary['runtron_8u8k'] = {a: {'runs': v['runs'], 'attempts': v['attempts'], 'parse_mean_s': statistics.mean(v['parse']) if v['parse'] else None, 'tps_lines_mean': statistics.mean(v['tps']) if v['tps'] else None} for a, v in arms.items()}
soak = os.path.join(RES, 'soak__canon60', 'meta.json')
if os.path.exists(soak):
    try:
        d = json.load(open(soak)); st = open(os.path.join(RES, 'soak__canon60', 'STATUS')).read().strip() if os.path.exists(os.path.join(RES, 'soak__canon60', 'STATUS')) else '?'
        out += ['## canonical-arm soak', '', f"arm {d['arm']}, models {', '.join(d['models'])}, planned {d['minutes']} min, {d['users']} users, started {d['started']}, status {st}. "
                f"Memory-growth lines: see soak__canon60/soak.log (grep 'Memory Growth' and 'used memory').", '']
        summary['soak'] = {'meta': d, 'status': st}
    except Exception as e:
        out += ['## canonical-arm soak', '', f'meta.json unreadable: {e}', '']
pb = os.path.join(RES, 'probe-build.txt')
if os.path.exists(pb): out += ['Probe build: ' + open(pb).read().strip(), '']
open(os.path.join(RES, 'summary.md'), 'w').write('\n'.join(out))
json.dump(summary, open(os.path.join(RES, 'summary.json'), 'w'), indent=1)
print('\n'.join(out))
