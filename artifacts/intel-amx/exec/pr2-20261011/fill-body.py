#!/usr/bin/env python3
"""Fill the {{PLACEHOLDERS}} of exec/pr2-20261011/pr-body.md from the pr2-20261011 chain results (PR2-handoff.md step 7).
Usage: python3 fill-body.py [--check]   (--check parses everything and prints the values without writing)
Sources: exec/results/pr2-E-cpu/summary.md and rt-results.txt (cells), exec/results/pr2-20261011/ (tests-<suffix>.txt,
build-<suffix>.log keyed by suffix, mutation-run.out, mutation-result.txt, smoke/<cell>/smoke.txt, host-suite-pr2.txt, steps.txt).
Every expected input is asserted; an unfilled placeholder is an error. Interpretation sentences are not generated here: the
subsections receive the factual bullets only, and the author reads the numbers before posting."""
import pathlib, re, sys
E = pathlib.Path('/home/jhan/workspace/intel-AMX/exec')
RES = E / 'results' / 'pr2-20261011'; CELLS = E / 'results' / 'pr2-E-cpu'
body_p = E / 'pr2-20261011' / 'pr-body.md'; body = body_p.read_text()
check = '--check' in sys.argv
HEAD = (RES / 'tests-pr2.txt').read_text().split('tip=')[1].split()[0]; HEAD_SHORT = HEAD[:10]

# ---- cells ----
summ = (CELLS / 'summary.md').read_text().splitlines()
arms, pairs = {}, {}
for line in summ:
    c = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(c) == 14 and c[0].startswith('q3-4b-tp2-8u-p') and c[1] == 'cpu':
        prompt = int(c[0].split('-p')[1]); arms[(prompt, c[5])] = dict(n=int(c[6]), tps=float(c[7]), tps_sd=float(c[8]), ttft=float(c[9]), ttft_sd=float(c[10]), early=int(c[11]), ver=c[13])
    if len(c) == 8 and c[0].startswith('q3-4b-tp2-8u-p') and c[1] == 'cpu' and ' vs ' in c[2]:
        prompt = int(c[0].split('-p')[1]); a, b = c[2].split(' vs ')
        m = re.match(r'([+-][\d.]+) \(([\d.]+), (\d+), ([+-][\d.]+)\)', c[6]); m2 = re.match(r'([+-]?\d+) \((\d+), (\d+), ([+-][\d.]+)\)', c[7])
        pairs[(prompt, a, b)] = dict(tps_pct=float(c[3]), ttft_pct=float(c[4]), ttft_ms=int(c[5]), tps_mean=float(m.group(1)), tps_sd=float(m.group(2)), tps_n=int(m.group(3)), tps_t=float(m.group(4)), ttft_mean=int(m2.group(1)), ttft_sd=int(m2.group(2)), ttft_n=int(m2.group(3)), ttft_t=float(m2.group(4)))
ARMS = ['base', 'new', 'newoff', 'head', 'headoff']
PAIRS = [('new', 'base'), ('new', 'head'), ('newoff', 'new'), ('newoff', 'headoff'), ('head', 'headoff')]
assert len(arms) == 10 and len(pairs) == 10, (sorted(arms), sorted(pairs))
for k, a in arms.items(): assert a['n'] == 3, ('n != 3', k, a)
for k, p in pairs.items(): assert p['tps_n'] == 3 and p['ttft_n'] == 3, ('pair n != 3', k, p)
assert arms[(1024, 'new')]['ver'] == HEAD_SHORT and arms[(1024, 'head')]['ver'] == '82d05e94be' and arms[(1024, 'base')]['ver'] == '72308ec90c', [arms[(1024, a)]['ver'] for a in ARMS]
rt = (CELLS / 'rt-results.txt').read_text()
assert 'tron-pr1/gen/runtron.pr1 (82d05e94be)' in rt and 'tron-pr2/gen/runtron.pr2' in rt and 'headoff=[TRON_AMX_DISABLE=1]' in rt and 'newoff=[TRON_AMX_DISABLE=1]' in rt, 'rt-results.txt arms header'
E_DATE = re.search(r'started (\d{4}-\d\d-\d\d)T', rt).group(1)
def band(prompt, a, b):
    bt = max(2 * max(arms[(prompt, a)]['tps_sd'], arms[(prompt, b)]['tps_sd']), 0.4)
    bf = max(2 * max(arms[(prompt, a)]['ttft_sd'], arms[(prompt, b)]['ttft_sd']), 0.15)
    return bt, bf
def inside(v, b): return 'inside' if abs(v) <= b else 'beyond'
def ttft_str(ms, pct, t):
    if abs(ms) >= 1000: return f"{ms/1000:+.1f} s ({pct:+.1f} %, t {t:+.1f})"
    return f"{ms:+d} ms ({pct:+.1f} %, t {t:+.1f})"
def ttft_plain(ms, pct):
    return f"{ms/1000:+.1f} s ({pct:+.1f} %)" if abs(ms) >= 1000 else f"{ms:+d} ms ({pct:+.1f} %)"
arm_rows = [f"| {p} | {a} | {arms[(p,a)]['tps']:.2f} ({arms[(p,a)]['tps_sd']:.2f}) | {arms[(p,a)]['ttft']:.3f} ({arms[(p,a)]['ttft_sd']:.3f}) |" for p in (1024, 8192) for a in ARMS]
pair_rows = []
for p in (1024, 8192):
    for a, b in PAIRS:
        q = pairs[(p, a, b)]; bt, bf = band(p, a, b)
        pair_rows.append(f"| {p} | {a} vs {b} | {q['tps_pct']:+.1f} % ({q['tps_mean']:+.2f} TPS, t {q['tps_t']:+.1f}), {inside(q['tps_mean'], bt)} | {ttft_str(q['ttft_ms'], q['ttft_pct'], q['ttft_t'])}, {inside(q['ttft_ms']/1000, bf)} | {bt:.2f} TPS / {bf:.2f} s |")
P = lambda pr, a, b, k: pairs[(pr, a, b)][k]
def pair_bullets(a, b, subject):
    out = []
    for metric in ('TPS', 'TTFT'):
        parts = []
        for p in (1024, 8192):
            q = pairs[(p, a, b)]; bt, bf = band(p, a, b)
            if metric == 'TPS': parts.append(f"{q['tps_pct']:+.1f} % ({q['tps_mean']:+.2f} TPS, {inside(q['tps_mean'], bt)} the {bt:.2f} TPS band, paired t {q['tps_t']:+.1f})")
            else: parts.append(f"{ttft_plain(q['ttft_ms'], q['ttft_pct'])}, {inside(q['ttft_ms']/1000, bf)} the {bf:.2f} s band, paired t {q['ttft_t']:+.1f}")
        out.append(f"- {metric} of {subject}: {parts[0]} at prompt length 1,024 tokens and {parts[1]} at 8,192 tokens.")
    return '\n'.join(out)
against_main = pair_bullets('new', 'base', '`new` against `base`')
recovery = pair_bullets('new', 'head', '`new` against `head`')
kill_switch = pair_bullets('newoff', 'new', '`newoff` against `new`')
ctrl1 = pair_bullets('newoff', 'headoff', '`newoff` against `headoff`')
ctrl2 = pair_bullets('head', 'headoff', '`head` against `headoff`')
short_1024 = f"{P(1024,'new','base','tps_pct'):+.1f} %"; short_8192 = f"{P(8192,'new','base','tps_pct'):+.1f} %"
scatter = f"Measured here as `new` against `base` TTFT: {ttft_plain(P(1024,'new','base','ttft_ms'), P(1024,'new','base','ttft_pct'))} at prompt length 1,024 tokens and {ttft_plain(P(8192,'new','base','ttft_ms'), P(8192,'new','base','ttft_pct'))} at 8,192 tokens, {inside(P(1024,'new','base','ttft_ms')/1000, band(1024,'new','base')[1])} and {inside(P(8192,'new','base','ttft_ms')/1000, band(8192,'new','base')[1])} the band."

# ---- builds and tests ----
def build_secs(suffix):
    log = (RES / f'build-{suffix}.log').read_text()
    m = re.findall(r'build rc=0 in (\d+) s', log); assert m, ('build time', suffix); return int(m[-1])
BUILD = {s: build_secs(s) for s in ('pr2', 'pr2nd', 'pr2rm')}
BUILD_DATE = re.search(r'started (\d{4}-\d\d-\d\d)T', (RES / 'build-pr2.log').read_text()).group(1)
def counts(suffix):
    out = {}
    for line in (RES / f'tests-{suffix}.txt').read_text().splitlines():
        m = re.match(r'(\w+) rc=(\d+) tip=(\w+) env=\[([^\]]*)\] args=\[[^\]]*\] (.*)', line)
        if not m: continue
        t, rc, tip, env, rest = m.groups(); assert rc == '0' and tip == HEAD, line
        c = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', rest); assert c, line
        out[(t, env)] = (int(c.group(1)), int(c.group(2)), rest)
    return out
C_ON, C_ND, C_RM = counts('pr2'), counts('pr2nd'), counts('pr2rm')
TESTS = ['t_k_vnni_layout', 't_amx_dispatch_dtype', 't_amx_numerics', 't_llama_unit', 't_heterogeneous_scheduler', 't_phase1_integration']
def cell(cnt, t, note=''):
    if (t, '') not in cnt: return 'not built'
    a, c, _ = cnt[(t, '')]; return f"{a} / {c}{note}"
amx_on_out = (RES / 'tests-pr2-t_amx_numerics.out').read_text(); rm_out = (RES / 'tests-pr2rm-t_amx_numerics.out').read_text()
assert 'AMX unavailable' not in amx_on_out and 'AMX unavailable' not in rm_out, 'identity case did not run on AMX'
assert C_ON[('t_amx_numerics', '')][1] == 5 and C_RM[('t_amx_numerics', '')][1] == 5, 't_amx_numerics case count'
assert C_ND[('t_amx_numerics', '')] [:2] == (1, 1) and C_ND[('t_amx_dispatch_dtype', '')][:2] == (1, 1), 'placeholders'
test_rows = []
for t in TESTS:
    on = cell(C_ON, t, ' (AMX cases ran, no "AMX unavailable" line)' if t == 't_amx_numerics' else '')
    nd = cell(C_ND, t, ' (placeholder without dispatch)' if t in ('t_amx_numerics', 't_amx_dispatch_dtype') else '')
    rm = cell(C_RM, t, ' (AMX cases ran)' if t == 't_amx_numerics' else '')
    test_rows.append(f"| `{t}` | {on} | {nd} | {rm} |")
ks_text = (RES / 'tests-pr2.txt').read_text()
ks = {}
for line in ks_text.splitlines():
    m = re.match(r'(\w+) killswitch rc=(\d+) env=\[TRON_AMX_DISABLE=1\] (.*)', line)
    if m: assert m.group(2) == '0', line; ks[m.group(1)] = m.group(3)
assert set(ks) == {'t_llama_unit', 't_amx_numerics'}, ks
def passed(rest):
    c = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', rest); assert c, rest; return int(c.group(1)), int(c.group(2))
lu, lu_c = passed(ks['t_llama_unit']); an, an_c = passed(ks['t_amx_numerics'])
ks_out = (RES / 'tests-pr2-t_amx_numerics-killswitch.out').read_text()
skipped = [n for n, pat in (('QK precision', 'QK precision check skipped'), ('identity', 'VNNI QK identity check skipped'), ('PV precision', 'PV precision check skipped')) if pat in ks_out]
assert len(skipped) == 3, skipped
lu_note = 'This matches the AMX-on count.' if lu == C_ON[('t_llama_unit', '')][0] else f"The AMX-on count is {C_ON[('t_llama_unit', '')][0]}."
killswitch_lines = f"- `t_llama_unit`: {lu} assertions passed in {lu_c} cases. {lu_note}\n- `t_amx_numerics`: {an} assertions passed in {an_c} cases. Its {', '.join(skipped[:-1])} and {skipped[-1]} cases reported \"AMX unavailable\"."
# ---- mutation ----
mrun = (RES / 'mutation-run.out').read_text(); mres = (RES / 'mutation-result.txt').read_text()
tc = re.search(r'test cases:\s*(\d+)\s*\|(?:\s*\d+ passed\s*\|)?\s*(\d+) failed', mrun); asr = re.search(r'assertions:\s*(\d+)\s*\|\s*(\d+) passed\s*\|\s*(\d+) failed', mrun)
loc = re.search(r'(t/t_amx_numerics\.cpp):(\d+): FAILED', mrun); assert tc and asr and loc, 'mutant summary lines'
cap = {k: v for k, v in re.findall(r'(seed|qi|t) := (\d+)', mrun)}
assert re.search(r'^mutant t_amx_numerics rc=[1-9]', mres, re.M) and re.search(r'^restored t_amx_numerics rc=0', mres, re.M), mres
restored = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', (RES / 'tests-pr2-t_amx_numerics-restored.out').read_text()); assert restored
assert (int(restored.group(1)), int(restored.group(2))) == C_ON[('t_amx_numerics', '')][:2], 'restored counts differ from step A'
mutation = (f"The run reports {tc.group(2)} of {tc.group(1)} test cases failed and {asr.group(3)} of {asr.group(1)} assertions failed, at the `REQUIRE` of `{loc.group(1)}:{loc.group(2)}`"
            + (f", with seed {cap['seed']}, query row {cap['qi']} and token {cap['t']} captured ({asr.group(2)} earlier comparisons passed)." if cap else '.'))
restored_counts = f"{restored.group(1)} assertions in {restored.group(2)} cases"
# ---- smokes ----
def first_diff(cell, a, b):
    t = (RES / 'smoke' / cell / 'smoke.txt').read_text()
    m = re.findall(rf"^{a} vs {b}: (identical for (\d+) tokens|first difference at generated token (\d+) of (\d+))", t, re.M)
    assert m, (cell, a, b); m = m[-1]
    return f"identical, {m[1]} of {m[1]} tokens" if m[1] else f"first difference at generated token {m[2]}"
# The validator must say ok for every cell (every arm rc 0 and 256 tokens). smoke.done is reported as measured: the
# handoff's rule for a newoff-vs-new difference is to report it and stop before opening, not to hide it.
for c in ('cpu-p1024', 'cpu-p8192', 'fpga-p1024'):
    assert (RES / 'smoke' / c / 'validate.txt').read_text().strip() == 'VALIDATE ok', c
SMOKE_VERDICTS = {c: (RES / 'smoke' / c / 'smoke.done').read_text().strip() for c in ('cpu-p1024', 'cpu-p8192', 'fpga-p1024')}
SPAIRS = [('new', 'new2'), ('newoff', 'new'), ('new', 'head'), ('new', 'base'), ('head', 'base')]
labels = [('cpu-p1024', 'CPU attention, prompt length 1024 tokens'), ('cpu-p8192', 'CPU attention, prompt length 8192 tokens'), ('fpga-p1024', 'FPGA attention, prompt length 1024 tokens')]
smoke_rows = [f"| {lab} | " + ' | '.join(first_diff(c, a, b) for a, b in SPAIRS) + ' |' for c, lab in labels]
SMOKE_DATE = re.search(r' (\d{4}-\d\d-\d\d)T\d\d:\d\d:\d\dZ load=', (RES / 'smoke' / 'cpu-p1024' / 'smoke.txt').read_text()).group(1)
d1, d2, d3 = first_diff('cpu-p1024', 'new', 'base'), first_diff('cpu-p8192', 'new', 'base'), first_diff('fpga-p1024', 'new', 'base')
t1, t3 = re.search(r'token (\d+)', d1), re.search(r'token (\d+)', d3)
if t1 and t3 and t1.group(1) == t3.group(1) and d2.startswith('identical'):
    divergence = f"At prompt length 1,024 tokens, both CPU and FPGA attention first differ from `main` at generated token {t1.group(1)} of 256. At prompt length 8,192 tokens with CPU attention, all 256 generated tokens match. [Verification above]"
else:
    divergence = f"CPU attention, prompt length 1,024 tokens: {d1}. FPGA attention, prompt length 1,024 tokens: {d3}. CPU attention, prompt length 8,192 tokens: {d2}. [Verification above]"
def first_diff_ids(cell, a, b):
    t = (RES / 'smoke' / cell / 'smoke.txt').read_text()
    m = re.findall(rf"^{a} vs {b}: first difference at generated token (\d+) of (\d+) \((-?\d+) vs (-?\d+)\)", t, re.M)
    return m[-1] if m else None
nn = [first_diff(c, 'newoff', 'new') for c, _ in labels]
if all(x.startswith('identical') for x in nn):
    newoff_new = "`newoff` and `new` produce the same 256 generated tokens in each of the three token-identity cells. [Verification above]"
else:
    parts = []
    for (c, lab), x in zip(labels, nn):
        ids = first_diff_ids(c, 'newoff', 'new')
        parts.append(f"{lab}: {x} of {ids[1]} (token id {ids[2]} under the kill switch, {ids[3]} without it)" if ids else f"{lab}: {x}")
    newoff_new = "`newoff` against `new`. " + '. '.join(parts) + ". [Verification above]"
# ---- host suite ----
h = (RES / 'host-suite-pr2.txt').read_text()
m = re.search(r'(\d+) passed, (\d+) skipped, (\d+) failed\s+•\s+makespan ([\d.]+)s', h); assert m, 'host summary line'
hp, hs, hf, mk = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
assert '^build-test-host rc=0' and re.search(r'^build-test-host rc=0', h, re.M), 'build-test-host rc'
assert (hs, hf) == (1, 1) and 'failed: t_proxy_llama31' in h, (hp, hs, hf)
hlog = (RES / 'host-suite-pr2.log').read_text()
assert 'cache after:' in hlog and 'TRON_K_VNNI:BOOL=ON' in hlog.split('cache after:')[1], 'TRON_K_VNNI kept'
host_lines = (f"- All test targets compiled.\n- {hp} tests passed.\n- {hs} test skipped: `t_proxy_lib`. Its per-test log reports \"SKIP: t/proxy/.venv missing\".\n"
              f"- {hf} test failed: `t_proxy_llama31`, reporting \"ERROR: t/proxy/.venv missing\".\n- Total suite time: {mk:.0f} s.\n- The CMake cache retained `TRON_K_VNNI=ON` throughout the make targets.")
# ---- fill ----
F = {'SHORT_TPS_1024': short_1024, 'SHORT_TPS_8192': short_8192, 'HEAD_SHORT': HEAD_SHORT, 'E_DATE': E_DATE, 'ARM_ROWS': '\n'.join(arm_rows), 'PAIR_ROWS': '\n'.join(pair_rows),
     'AGAINST_MAIN': against_main, 'RECOVERY': recovery, 'KILL_SWITCH': kill_switch, 'CONTROL_NEWOFF_HEADOFF': ctrl1, 'CONTROL_HEAD_HEADOFF': ctrl2, 'BUILD_DATE': BUILD_DATE,
     'BUILD_PR2': str(BUILD['pr2']), 'BUILD_PR2ND': str(BUILD['pr2nd']), 'BUILD_PR2RM': str(BUILD['pr2rm']), 'TEST_ROWS': '\n'.join(test_rows), 'KILLSWITCH_LINES': killswitch_lines,
     'MUTATION': mutation, 'RESTORED_COUNTS': restored_counts, 'SMOKE_DATE': SMOKE_DATE, 'HOST_LINES': host_lines, 'SMOKE_ROWS': '\n'.join(smoke_rows), 'DIVERGENCE': divergence, 'NEWOFF_NEW': newoff_new, 'SCATTER_TTFT': scatter}
for k, v in F.items():
    assert f'{{{{{k}}}}}' in body, ('placeholder missing in body', k)
    body = body.replace(f'{{{{{k}}}}}', v)
left = re.findall(r'\{\{[A-Z_0-9]+\}\}', body); assert not left, ('unfilled', left)
if check:
    for k, v in F.items(): print(f'--- {k}\n{v}')
    print('smoke verdicts:', SMOKE_VERDICTS); print('check ok (nothing written)')
else:
    body_p.write_text(body); print('filled', body_p, {k: arms[k]['tps'] for k in sorted(arms)})
