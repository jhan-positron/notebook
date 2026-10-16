#!/usr/bin/env python3
"""Fill the {{PLACEHOLDERS}} of exec/pr3-20261012/pr-body-template.md from the pr3-20261012 chain results into pr-body.md
(PR3-handoff.md step 7). Fork of exec/pr2-20261011/fill-body.py for three cells (tp2 p1024, tp2 p8192, tp4 p1024), five
arms, five pairs, two mutation checks, the Haskell suite, the plugin table, fourmolu and lint-notes.
Usage: python3 fill-body.py [--check]   (--check parses everything and prints the values without writing)
Sources: exec/results/pr3-E-cpu/summary.md and rt-results.txt (cells), exec/results/pr3-20261012/ (tests-<suffix>.txt,
build-<suffix>.log keyed by suffix, mutation<N>-run.out and -result.txt, tests-pr3-<t>-restored.out, ingest-test-pr3.txt,
plugin-calls-pr3.txt, format-pr3.txt, lint-notes-pr3.txt, smoke/<cell>/smoke.txt and validate.txt, host-suite-pr3.txt/.log,
steps.txt). Every expected input is asserted. The interpretation placeholders ({{*_TEXT}}, {{CI_STATUS}}) are hand-written
after reading the numbers: the script leaves them in place and lists them."""
import pathlib, re, sys
E = pathlib.Path('/home/jhan/workspace/intel-AMX/exec')
RES = E / 'results' / 'pr3-20261012'; CELLS = E / 'results' / 'pr3-E-cpu'
tmpl_p = E / 'pr3-20261012' / 'pr-body-template.md'; body_p = E / 'pr3-20261012' / 'pr-body.md'
body = tmpl_p.read_text()
check = '--check' in sys.argv
HAND = {'TTFT_GAIN_TEXT', 'TPS_HEAD_TEXT', 'AGAINST_MAIN_TEXT', 'READER_STORE_TEXT', 'KILL_SWITCH_TEXT', 'HEAD_BASE_TEXT', 'CI_STATUS'}
HEAD = (RES / 'tests-pr3.txt').read_text().split('tip=')[1].split()[0]; HEAD_SHORT = HEAD[:10]
PR2_SHORT, BASE_SHORT = '0ee8671d35', '72308ec90c'

# ---- cells ----
CELL_KEYS = [(2, 1024), (2, 8192), (4, 1024)]
def label(tp, p): return f"tp{tp}, {p:,} tokens"
summ = (CELLS / 'summary.md').read_text().splitlines()
arms, pairs = {}, {}
for line in summ:
    c = [x.strip() for x in line.strip().strip('|').split('|')]
    m = re.match(r'q3-4b-tp(\d)-8u-p(\d+)$', c[0]) if c else None
    if not m or c[1] != 'cpu': continue
    tp, prompt = int(m.group(1)), int(m.group(2))
    if len(c) == 14:
        arms[(tp, prompt, c[5])] = dict(n=int(c[6]), tps=float(c[7]), tps_sd=float(c[8]), ttft=float(c[9]), ttft_sd=float(c[10]), early=int(c[11]), ver=c[13])
    elif len(c) == 8 and ' vs ' in c[2]:
        a, b = c[2].split(' vs ')
        q = re.match(r'([+-][\d.]+) \(([\d.]+), (\d+), ([+-][\d.]+)\)', c[6]); q2 = re.match(r'([+-]?\d+) \((\d+), (\d+), ([+-][\d.]+)\)', c[7])
        pairs[(tp, prompt, a, b)] = dict(tps_pct=float(c[3]), ttft_pct=float(c[4]), ttft_ms=int(c[5]), tps_mean=float(q.group(1)), tps_sd=float(q.group(2)), tps_n=int(q.group(3)), tps_t=float(q.group(4)), ttft_mean=int(q2.group(1)), ttft_sd=int(q2.group(2)), ttft_n=int(q2.group(3)), ttft_t=float(q2.group(4)))
ARMS = ['base', 'new', 'newoff', 'head', 'headoff']
PAIRS = [('new', 'base'), ('new', 'head'), ('newoff', 'new'), ('newoff', 'headoff'), ('head', 'base')]
assert len(arms) == 15 and len(pairs) == 15, (sorted(arms), sorted(pairs))
for k, a in arms.items(): assert a['n'] == 3, ('n != 3', k, a)
for k, p in pairs.items(): assert p['tps_n'] == 3 and p['ttft_n'] == 3, ('pair n != 3', k, p)
for tp, p in CELL_KEYS:
    assert arms[(tp, p, 'new')]['ver'] == HEAD_SHORT and arms[(tp, p, 'head')]['ver'] == PR2_SHORT and arms[(tp, p, 'base')]['ver'] == BASE_SHORT, [(a, arms[(tp, p, a)]['ver']) for a in ARMS]
rt = (CELLS / 'rt-results.txt').read_text()
assert f'tron-pr2/gen/runtron.pr2 ({PR2_SHORT})' in rt and 'tron-pr3/gen/runtron.pr3' in rt and f'runtron.main1010 ({BASE_SHORT})' in rt and 'headoff=[TRON_AMX_DISABLE=1]' in rt and 'newoff=[TRON_AMX_DISABLE=1]' in rt, 'rt-results.txt arms header'
E_DATE = re.search(r'started (\d{4}-\d\d-\d\d)T', rt).group(1)
def band(tp, p, a, b):
    bt = max(2 * max(arms[(tp, p, a)]['tps_sd'], arms[(tp, p, b)]['tps_sd']), 0.4)
    bf = max(2 * max(arms[(tp, p, a)]['ttft_sd'], arms[(tp, p, b)]['ttft_sd']), 0.15)
    return bt, bf
def inside(v, b): return 'inside' if abs(v) <= b else 'beyond'
def ttft_str(ms, pct, t): return (f"{ms/1000:+.1f} s" if abs(ms) >= 1000 else f"{ms:+d} ms") + f" ({pct:+.1f} %, t {t:+.1f})"
def ttft_plain(ms, pct): return (f"{ms/1000:+.1f} s" if abs(ms) >= 1000 else f"{ms:+d} ms") + f" ({pct:+.1f} %)"
arm_rows = [f"| {label(tp,p)} | {a} | {arms[(tp,p,a)]['tps']:.2f} ({arms[(tp,p,a)]['tps_sd']:.2f}) | {arms[(tp,p,a)]['ttft']:.3f} ({arms[(tp,p,a)]['ttft_sd']:.3f}) |" for tp, p in CELL_KEYS for a in ARMS]
pair_rows = []
for tp, p in CELL_KEYS:
    for a, b in PAIRS:
        q = pairs[(tp, p, a, b)]; bt, bf = band(tp, p, a, b)
        pair_rows.append(f"| {label(tp,p)} | {a} vs {b} | {q['tps_pct']:+.1f} % ({q['tps_mean']:+.2f} TPS, t {q['tps_t']:+.1f}), {inside(q['tps_mean'], bt)} | {ttft_str(q['ttft_ms'], q['ttft_pct'], q['ttft_t'])}, {inside(q['ttft_ms']/1000, bf)} | {bt:.2f} TPS / {bf:.2f} s |")
def pair_bullets(a, b, subject, metrics=('TPS', 'TTFT')):
    out = []
    for metric in metrics:
        parts = []
        for tp, p in CELL_KEYS:
            q = pairs[(tp, p, a, b)]; bt, bf = band(tp, p, a, b)
            if metric == 'TPS': parts.append(f"{q['tps_pct']:+.1f} % ({q['tps_mean']:+.2f} TPS, {inside(q['tps_mean'], bt)} the {bt:.2f} TPS band, paired t {q['tps_t']:+.1f}) at {label(tp, p)}")
            else: parts.append(f"{ttft_plain(q['ttft_ms'], q['ttft_pct'])}, {inside(q['ttft_ms']/1000, bf)} the {bf:.2f} s band, paired t {q['ttft_t']:+.1f}, at {label(tp, p)}")
        out.append(f"- {metric} of {subject}:\n  - {parts[0]}.\n  - {parts[1]}.\n  - {parts[2]}.")
    return '\n'.join(out)
P = lambda tp, p, a, b, k: pairs[(tp, p, a, b)][k]
short = {
    'S_TTFT_HEAD_TP2': ttft_plain(P(2, 1024, 'new', 'head', 'ttft_ms'), P(2, 1024, 'new', 'head', 'ttft_pct')),
    'S_TTFT_HEAD_TP4': ttft_plain(P(4, 1024, 'new', 'head', 'ttft_ms'), P(4, 1024, 'new', 'head', 'ttft_pct')),
    'S_TTFT_BASE_TP2': ttft_plain(P(2, 1024, 'new', 'base', 'ttft_ms'), P(2, 1024, 'new', 'base', 'ttft_pct')),
    'S_TTFT_BASE_TP4': ttft_plain(P(4, 1024, 'new', 'base', 'ttft_ms'), P(4, 1024, 'new', 'base', 'ttft_pct')),
    'S_TPS_HEAD_TP2': f"{P(2,1024,'new','head','tps_pct'):+.1f} % ({P(2,1024,'new','head','tps_mean'):+.2f} TPS, {inside(P(2,1024,'new','head','tps_mean'), band(2,1024,'new','head')[0])} the {band(2,1024,'new','head')[0]:.2f} TPS band)",
}

# ---- builds and tests ----
def build_secs(suffix):
    log = (RES / f'build-{suffix}.log').read_text()
    m = re.findall(r'build rc=0 in (\d+) s', log); assert m, ('build time', suffix); return int(m[-1])
BUILD = {s: build_secs(s) for s in ('pr3', 'pr3nd', 'pr3rm')}
BUILD_DATE = re.search(r'started (\d{4}-\d\d-\d\d)T', (RES / 'build-pr3.log').read_text()).group(1)
def counts(suffix):
    out = {}
    for line in (RES / f'tests-{suffix}.txt').read_text().splitlines():
        m = re.match(r'(\w+) rc=(\d+) tip=(\w+) env=\[([^\]]*)\] args=\[[^\]]*\] (.*)', line)
        if not m: continue
        t, rc, tip, env, rest = m.groups(); assert rc == '0' and tip == HEAD, line
        c = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', rest); assert c, line
        out[(t, env)] = (int(c.group(1)), int(c.group(2)), rest)
    return out
C_ON, C_ND, C_RM = counts('pr3'), counts('pr3nd'), counts('pr3rm')
TESTS = ['t_k_vnni_layout', 't_amx_dispatch_dtype', 't_amx_numerics', 't_llama_unit', 't_heterogeneous_scheduler', 't_phase1_integration']
def cell(cnt, t, note=''):
    if (t, '') not in cnt: return 'not built'
    a, c, _ = cnt[(t, '')]; return f"{a} / {c}{note}"
amx_on_out = (RES / 'tests-pr3-t_amx_numerics.out').read_text(); rm_out = (RES / 'tests-pr3rm-t_amx_numerics.out').read_text()
assert 'AMX unavailable' not in amx_on_out and 'AMX unavailable' not in rm_out, 'identity case did not run on AMX'
assert C_ON[('t_amx_numerics', '')][1] == 5 and C_RM[('t_amx_numerics', '')][1] == 5, 't_amx_numerics case count'
assert C_ND[('t_amx_numerics', '')][:2] == (1, 1) and C_ND[('t_amx_dispatch_dtype', '')][:2] == (1, 1), 'placeholders'
for cnt, nm in ((C_ON, 'on'), (C_ND, 'nd'), (C_RM, 'rm')): assert cnt[('t_k_vnni_layout', '')][1] == 5, ('t_k_vnni_layout cases', nm, cnt[('t_k_vnni_layout', '')])
test_rows = []
for t in TESTS:
    on = cell(C_ON, t, ' (AMX cases ran, no "AMX unavailable" line)' if t == 't_amx_numerics' else '')
    nd = cell(C_ND, t, ' (placeholder without dispatch)' if t in ('t_amx_numerics', 't_amx_dispatch_dtype') else '')
    rm = cell(C_RM, t, ' (AMX cases ran)' if t == 't_amx_numerics' else '')
    test_rows.append(f"| `{t}` | {on} | {nd} | {rm} |")
ks = {}
for line in (RES / 'tests-pr3.txt').read_text().splitlines():
    m = re.match(r'(\w+) killswitch rc=(\d+) env=\[TRON_AMX_DISABLE=1\] (.*)', line)
    if m: assert m.group(2) == '0', line; ks[m.group(1)] = m.group(3)
assert set(ks) == {'t_llama_unit', 't_amx_numerics'}, ks
def passed(rest):
    c = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', rest); assert c, rest; return int(c.group(1)), int(c.group(2))
lu, lu_c = passed(ks['t_llama_unit']); an, an_c = passed(ks['t_amx_numerics'])
ks_out = (RES / 'tests-pr3-t_amx_numerics-killswitch.out').read_text()
skipped = [n for n, pat in (('QK precision', 'QK precision check skipped'), ('identity', 'VNNI QK identity check skipped'), ('PV precision', 'PV precision check skipped')) if pat in ks_out]
assert len(skipped) == 3, skipped
lu_note = 'This matches the AMX-on count.' if lu == C_ON[('t_llama_unit', '')][0] else f"The AMX-on count is {C_ON[('t_llama_unit', '')][0]}."
killswitch_lines = f"- `t_llama_unit`: {lu} assertions passed in {lu_c} cases. {lu_note}\n- `t_amx_numerics`: {an} assertions passed in {an_c} cases. Its {', '.join(skipped[:-1])} and {skipped[-1]} cases reported \"AMX unavailable\"."

# ---- mutation checks ----
def mutation(n, binary, srcfile):
    mrun = (RES / f'mutation{n}-run.out').read_text(); mres = (RES / f'mutation{n}-result.txt').read_text()
    tc = re.search(r'test cases:\s*(\d+)\s*\|(?:\s*(\d+) passed\s*\|)?\s*(\d+) failed', mrun); asr = re.search(r'assertions:\s*(\d+)\s*\|(?:\s*(\d+) passed\s*\|)?\s*(\d+) failed', mrun)
    loc = re.search(rf'({re.escape(srcfile)}):(\d+): FAILED', mrun); assert tc and asr and loc, (f'mutant {n} summary lines', tc, asr, loc)
    assert 'No tests ran' not in mrun and tc.group(1) == '1' and tc.group(3) == '1', ('mutant ran exactly one case', tc.groups())
    assert re.search(rf'^mutant {binary} rc=[1-9]', mres, re.M) and re.search(rf'^restored {binary} rc=0', mres, re.M), mres
    restored = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', (RES / f'tests-pr3-{binary}-restored.out').read_text()); assert restored
    assert (int(restored.group(1)), int(restored.group(2))) == C_ON[(binary, '')][:2], f'restored counts of {binary} differ from step A'
    passed_n = int(asr.group(2)) if asr.group(2) else 0
    text = f"The run reports {tc.group(3)} of {tc.group(1)} test cases failed and {asr.group(3)} of {asr.group(1)} assertions failed, at the `REQUIRE` of `{loc.group(1)}:{loc.group(2)}`"
    text += f" ({passed_n} earlier assertions passed)." if passed_n else "."
    cap = {k: v for k, v in re.findall(r'^\s*(u|begin|end|t) := (\d+)', mrun, re.M)}
    return text, f"{restored.group(1)} assertions in {restored.group(2)} cases", cap
MUT1, RESTORED1, _ = mutation(1, 't_k_vnni_layout', 't/t_k_vnni_layout.cpp')
MUT2, RESTORED2, cap2 = mutation(2, 't_llama_unit', 't/t_llama_unit.cpp')
assert set(cap2) == {'u', 'begin', 'end', 't'}, cap2
MUT2 += f" The captured values are unit {cap2['u']}, items {cap2['begin']} to {cap2['end']}, item {cap2['t']}."

# ---- the Haskell suite ----
h = (RES / 'ingest-test-pr3.txt').read_text()
assert re.search(r'ingest-cabal-test rc=0\s*$', h, re.M) and 'Test suite ingest-tests: PASS' in h, 'Haskell suite'
hx = {k: int(re.search(rf'^\s*{k}:\s+(\d+)\s*$', h, re.M).group(1)) for k in ('Examples', 'Passed', 'Failed')}
assert hx['Failed'] == 0, hx
a2 = re.search(r'STEP A2: ok \((\d+) s\)', (RES / 'steps.txt').read_text()); assert a2, 'STEP A2 line'
HASKELL = f"return code 0, \"Test suite ingest-tests: PASS\", {hx['Examples']:,} examples, {hx['Passed']:,} passed, {hx['Failed']} failed, in {int(a2.group(1))} s including the package build."

# ---- the plugin table ----
pl = (RES / 'plugin-calls-pr3.txt').read_text().splitlines()
assert pl[-1].startswith('PASS'), pl[-1]
plugin_rows = []
for line in pl:
    m = re.match(r'(\S+\.hpp)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+ok$', line)
    if m:
        assert m.group(2) == m.group(3) == m.group(4) and int(m.group(2)) > 0 and m.group(5) == '0' and m.group(6) == '0', line
        plugin_rows.append(f"| `{m.group(1)}` | {m.group(2)} | {m.group(3)} | {m.group(4)} |")
assert len(plugin_rows) == 19, len(plugin_rows)

# ---- format and lint-notes ----
f = (RES / 'format-pr3.txt').read_text()
for k in ('clang-format rc=0', 'fourmolu rc=0', 'diff-check rc=0', 'cassert-in-diff 0', 'files: 7'): assert re.search(rf'^{re.escape(k)}\s*$', f, re.M), ('format', k)
ln = (RES / 'lint-notes-pr3.txt').read_text().strip().splitlines()[-1] if (RES / 'lint-notes-pr3.txt').exists() else 'lint-notes: not run'
LINT_NOTES = "`make lint-notes`, the Note-reference check, in the repository's lint shell." if ln.strip() == 'lint-notes rc=0' else f"`make lint-notes` was not run on the test machine ({ln.strip()}). The draft's Lint job runs it."

# ---- smokes ----
SMOKE_CELLS = [('cpu-p1024', 'CPU attention, prompt length 1024 tokens'), ('cpu-p8192', 'CPU attention, prompt length 8192 tokens'), ('fpga-p1024', 'FPGA attention, prompt length 1024 tokens')]
def smoke_txt(c): return (RES / 'smoke' / c / 'smoke.txt').read_text()
def first_diff(c, a, b):
    m = re.findall(rf"^{a} vs {b}: (identical for (\d+) tokens|first difference at generated token (\d+) of (\d+))", smoke_txt(c), re.M)
    assert m, (c, a, b); m = m[-1]
    return f"identical, {m[1]} of {m[1]} tokens" if m[1] else f"first difference at generated token {m[2]}"
def first_diff_ids(c, a, b):
    m = re.findall(rf"^{a} vs {b}: first difference at generated token (\d+) of (\d+) \((-?\d+) vs (-?\d+)\)", smoke_txt(c), re.M)
    return m[-1] if m else None
for c, _ in SMOKE_CELLS: assert (RES / 'smoke' / c / 'validate.txt').read_text().strip() == 'VALIDATE ok', c
SPAIRS = [('new', 'new2'), ('new', 'head'), ('newoff', 'new'), ('new', 'base'), ('head', 'base')]
smoke_rows = [f"| {lab} | " + ' | '.join(first_diff(c, a, b) for a, b in SPAIRS) + ' |' for c, lab in SMOKE_CELLS]
SMOKE_DATE = re.search(r' (\d{4}-\d\d-\d\d)T\d\d:\d\d:\d\dZ load=', smoke_txt('cpu-p1024')).group(1)
nh = [first_diff(c, 'new', 'head') for c, _ in SMOKE_CELLS]
NEW_HEAD = "`new` matched `head` for all 256 tokens in every cell." if all(x.startswith('identical') for x in nh) else "`new` against `head`. " + '. '.join(f"{lab}: {x}" for (c, lab), x in zip(SMOKE_CELLS, nh)) + "."
nn = [first_diff(c, 'newoff', 'new') for c, _ in SMOKE_CELLS]
if all(x.startswith('identical') for x in nn):
    NEWOFF_NEW = "`newoff` and `new` produce the same 256 generated tokens in each of the three token-identity cells. [Verification above]"
else:
    parts = []
    for (c, lab), x in zip(SMOKE_CELLS, nn):
        ids = first_diff_ids(c, 'newoff', 'new')
        parts.append(f"{lab}: {x} of {ids[1]} (token id {ids[2]} under the kill switch, {ids[3]} without it)" if ids else f"{lab}: {x}")
    NEWOFF_NEW = "`newoff` against `new`. " + '. '.join(parts) + ". [Verification above]"
d1, d2, d3 = first_diff('cpu-p1024', 'new', 'base'), first_diff('cpu-p8192', 'new', 'base'), first_diff('fpga-p1024', 'new', 'base')
t1, t3 = re.search(r'token (\d+)', d1), re.search(r'token (\d+)', d3)
if t1 and t3 and t1.group(1) == t3.group(1) and d2.startswith('identical'):
    DIVERGENCE = f"At prompt length 1,024 tokens, both CPU and FPGA attention first differ from `main` at generated token {t1.group(1)} of 256, with the same token ids as `head` against `base`. At prompt length 8,192 tokens with CPU attention, all 256 generated tokens match. [Verification above]"
else:
    DIVERGENCE = f"`new` against `base`. CPU attention, prompt length 1,024 tokens: {d1}. FPGA attention, prompt length 1,024 tokens: {d3}. CPU attention, prompt length 8,192 tokens: {d2}. [Verification above]"

# ---- host suite ----
hs = (RES / 'host-suite-pr3.txt').read_text()
m = re.search(r'(\d+) passed, (\d+) skipped, (\d+) failed\s+•\s+makespan ([\d.]+)s', hs); assert m, 'host summary line'
hp, hsk, hf, mk = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
assert re.search(r'^build-test-host rc=0', hs, re.M), 'build-test-host rc'
assert (hsk, hf) == (1, 1) and 'failed: t_proxy_llama31' in hs, (hp, hsk, hf)
hlog = (RES / 'host-suite-pr3.log').read_text()
assert 'cache after:' in hlog and 'TRON_K_VNNI:BOOL=ON' in hlog.split('cache after:')[1], 'TRON_K_VNNI kept'
host_lines = (f"- All test targets compiled.\n- {hp} tests passed.\n- {hsk} test skipped: `t_proxy_lib`. Its per-test log reports \"SKIP: t/proxy/.venv missing\".\n"
              f"- {hf} test failed: `t_proxy_llama31`, reporting \"ERROR: t/proxy/.venv missing\".\n- Total suite time: {mk:.0f} s.\n- The CMake cache retained `TRON_K_VNNI=ON` throughout the make targets.")

# ---- fill ----
F = {**short, 'HEAD_SHORT': HEAD_SHORT, 'E_DATE': E_DATE, 'ARM_ROWS': '\n'.join(arm_rows), 'PAIR_ROWS': '\n'.join(pair_rows),
     'TTFT_GAIN': pair_bullets('new', 'head', '`new` against `head`', ('TTFT',)), 'TPS_HEAD': pair_bullets('new', 'head', '`new` against `head`', ('TPS',)),
     'AGAINST_MAIN': pair_bullets('new', 'base', '`new` against `base`'), 'READER_STORE': pair_bullets('newoff', 'headoff', '`newoff` against `headoff`'),
     'KILL_SWITCH': pair_bullets('newoff', 'new', '`newoff` against `new`'), 'HEAD_BASE': pair_bullets('head', 'base', '`head` against `base`'),
     'BUILD_DATE': BUILD_DATE, 'BUILD_PR3': str(BUILD['pr3']), 'BUILD_PR3ND': str(BUILD['pr3nd']), 'BUILD_PR3RM': str(BUILD['pr3rm']), 'TEST_ROWS': '\n'.join(test_rows),
     'KILLSWITCH_LINES': killswitch_lines, 'MUTATION1': MUT1, 'RESTORED1': RESTORED1, 'MUTATION2': MUT2, 'RESTORED2': RESTORED2, 'HASKELL': HASKELL,
     'PLUGIN_ROWS': '\n'.join(plugin_rows), 'LINT_NOTES': LINT_NOTES, 'SMOKE_DATE': SMOKE_DATE, 'HOST_LINES': host_lines, 'SMOKE_ROWS': '\n'.join(smoke_rows),
     'NEW_HEAD': NEW_HEAD, 'NEWOFF_NEW': NEWOFF_NEW, 'DIVERGENCE': DIVERGENCE,
     'NEWOFF_NEW_V': NEWOFF_NEW.replace(' [Verification above]', '') + (' This matches the kernel PR\'s result.' if (nn[0].startswith('first difference at generated token 247') and nn[1].startswith('identical') and nn[2].startswith('identical')) else ''),
     'DIVERGENCE_V': DIVERGENCE.replace(' [Verification above]', ''),
     'CTRL_8192': (lambda q, bt, bf: f"{ttft_plain(q['ttft_ms'], q['ttft_pct'])} of TTFT, {inside(q['ttft_ms']/1000, bf)} the {bf:.2f} s band, paired t {q['ttft_t']:+.1f}; TPS {q['tps_pct']:+.1f} % ({q['tps_mean']:+.2f} TPS), {inside(q['tps_mean'], bt)} the {bt:.2f} TPS band.")(pairs[(2, 8192, 'newoff', 'headoff')], *band(2, 8192, 'newoff', 'headoff'))}
for k, v in F.items():
    assert f'{{{{{k}}}}}' in body, ('placeholder missing in body', k)
    body = body.replace(f'{{{{{k}}}}}', v)
left = set(re.findall(r'\{\{([A-Z_0-9]+)\}\}', body)); assert left == HAND, ('unfilled placeholders other than the hand-written ones', left ^ HAND)
if check:
    for k, v in F.items(): print(f'--- {k}\n{v}')
    print('left for hand writing:', sorted(left)); print('check ok (nothing written)')
else:
    body_p.write_text(body); print('filled', body_p, 'left for hand writing:', sorted(left))
