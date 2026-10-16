#!/usr/bin/env python3
"""Fill the {{PLACEHOLDERS}} of exec/pr4-20261012/pr-body-template.md (= pr-body-template-part1.md + part2.md) from the
pr4-20261012 chain and campaign results into pr-body.md (PR4-handoff.md step 7). Fork of exec/pr3-20261012/fill-body.py
for the CPU cells (5 arms x 3 cells, 5 pairs), the FPGA cells (3 arms x 2 cells, 3 pairs, with the HW-attention-loss
column), the whole-machine campaign (3 configs), two mutation checks (M1 under CAPTURE(tok); M2 in check_blocks, no
capture), no Haskell suite (skipped: recorded from steps.txt), the plugin table, the two deb builds, lint-notes, the host
suite and the cost rows.
Usage: python3 fill-body.py [--check]   (--check parses everything and prints the values without writing)
Sources: exec/results/pr4-E-cpu/ and pr4-E-fpga/ (summary.md, rt-results.txt), exec/results/pr4-20261012/ (tests-<suffix>.txt,
build-<suffix>.log keyed by suffix, mutation<N>-run.out and -result.txt, tests-pr4-<t>-restored.out, plugin-calls-pr4.txt,
format-pr4.txt, lint-notes-pr4.txt, deb-base.log, deb-target.log, smoke/<cell>/smoke.txt and validate.txt, host-suite-pr4.txt/.log,
bench-update.log, bench-update.diff, steps.txt), exec/results/pr4ci-20261012/summary.md (campaign W). Every expected input is
asserted. The interpretation placeholders ({{*_TEXT}}, {{S_RESULTS}}, {{CI_STATUS}}, {{OPEN_EXTRA}}) are hand-written after
reading the numbers: the script leaves them in place and lists them."""
import json, pathlib, re, sys
E = pathlib.Path('/home/jhan/workspace/intel-AMX/exec')
RES = E / 'results' / 'pr4-20261012'; CPU = E / 'results' / 'pr4-E-cpu'; FPGA = E / 'results' / 'pr4-E-fpga'; WRES = E / 'results' / 'pr4ci-20261012'
D = E / 'pr4-20261012'
tmpl_p = D / 'pr-body-template.md'; body_p = D / 'pr-body.md'
if not tmpl_p.exists():
    tmpl_p.write_text((D / 'pr-body-template-part1.md').read_text() + (D / 'pr-body-template-part2.md').read_text())
body = tmpl_p.read_text()
check = '--check' in sys.argv
HAND = {'S_RESULTS', 'FPGA_TEXT', 'HEAD_TEXT', 'AGAINST_MAIN_TEXT', 'KILL_SWITCH_TEXT', 'AMX_OFF_TEXT', 'HEAD_BASE_TEXT', 'W_TEXT', 'W_MEM_TEXT', 'CI_STATUS', 'OPEN_EXTRA'}
HEAD = (RES / 'tests-pr4.txt').read_text().split('tip=')[1].split()[0]; HEAD_SHORT = HEAD[:10]
PR3_SHORT, BASE_SHORT = 'dfafd13dce', '72308ec90c'
PUSHED_SHORT = sys.argv[sys.argv.index('--pushed') + 1][:10] if '--pushed' in sys.argv else '{{PUSHED_SHORT}}'

# ---- cells ----
def parse_cells(folder, attn, arms_wanted, pairs_wanted, cells_wanted):
    summ = (folder / 'summary.md').read_text().splitlines()
    arms, pairs = {}, {}
    for line in summ:
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        m = re.match(r'q3-4b-tp(\d)-8u-p(\d+)$', c[0]) if c else None
        if not m or c[1] != attn: continue
        tp, prompt = int(m.group(1)), int(m.group(2))
        if len(c) == 14:
            arms[(tp, prompt, c[5])] = dict(n=int(c[6]), tps=float(c[7]), tps_sd=float(c[8]), ttft=float(c[9]), ttft_sd=float(c[10]), early=int(c[11]), hbm=float(c[12]), ver=c[13])
        elif len(c) == 8 and ' vs ' in c[2]:
            a, b = c[2].split(' vs ')
            q = re.match(r'([+-][\d.]+) \(([\d.]+), (\d+), ([+-][\d.]+)\)', c[6]); q2 = re.match(r'([+-]?\d+) \((\d+), (\d+), ([+-][\d.]+)\)', c[7])
            pairs[(tp, prompt, a, b)] = dict(tps_pct=float(c[3]), ttft_pct=float(c[4]), ttft_ms=int(c[5]), tps_mean=float(q.group(1)), tps_sd=float(q.group(2)), tps_n=int(q.group(3)), tps_t=float(q.group(4)), ttft_mean=int(q2.group(1)), ttft_sd=int(q2.group(2)), ttft_n=int(q2.group(3)), ttft_t=float(q2.group(4)))
    assert len(arms) == len(arms_wanted) * len(cells_wanted) and len(pairs) == len(pairs_wanted) * len(cells_wanted), (attn, sorted(arms), sorted(pairs))
    for k, a in arms.items(): assert a['n'] == 3, ('n != 3', attn, k, a)
    for k, p in pairs.items(): assert p['tps_n'] == 3 and p['ttft_n'] == 3, ('pair n != 3', attn, k, p)
    for tp, p in cells_wanted:
        assert arms[(tp, p, 'new')]['ver'] == HEAD_SHORT and arms[(tp, p, 'head')]['ver'] == PR3_SHORT and arms[(tp, p, 'base')]['ver'] == BASE_SHORT, [(a, arms[(tp, p, a)]['ver']) for a in arms_wanted]
        for a in arms_wanted: assert arms[(tp, p, a)]['early'] == 0, ('early-stop runs', attn, tp, p, a)
    rt = (folder / 'rt-results.txt').read_text()
    assert f'tron-pr3/gen/runtron.pr3 ({PR3_SHORT})' in rt and 'tron-pr4/gen/runtron.pr4' in rt and f'runtron.main1010 ({BASE_SHORT})' in rt, (attn, 'rt-results.txt arms header')
    if 'newoff' in arms_wanted: assert 'headoff=[TRON_AMX_DISABLE=1]' in rt and 'newoff=[TRON_AMX_DISABLE=1]' in rt, 'kill-switch env'
    date = re.search(r'started (\d{4}-\d\d-\d\d)T', rt).group(1)
    return arms, pairs, date
CPU_CELLS = [(2, 1024), (2, 8192), (4, 1024)]; FPGA_CELLS = [(2, 1024), (4, 1024)]
CPU_ARMS = ['base', 'new', 'newoff', 'head', 'headoff']; FPGA_ARMS = ['base', 'new', 'head']
CPU_PAIRS = [('new', 'base'), ('new', 'head'), ('newoff', 'new'), ('newoff', 'headoff'), ('head', 'base')]; FPGA_PAIRS = [('new', 'base'), ('new', 'head'), ('head', 'base')]
arms_c, pairs_c, E_DATE = parse_cells(CPU, 'cpu', CPU_ARMS, CPU_PAIRS, CPU_CELLS)
arms_f, pairs_f, E_DATE_F = parse_cells(FPGA, 'fpga', FPGA_ARMS, FPGA_PAIRS, FPGA_CELLS)
assert E_DATE == E_DATE_F, (E_DATE, E_DATE_F)
def label(tp, p): return f"tp{tp}, {p:,} tokens"
def band(arms, tp, p, a, b):
    bt = max(2 * max(arms[(tp, p, a)]['tps_sd'], arms[(tp, p, b)]['tps_sd']), 0.4)
    bf = max(2 * max(arms[(tp, p, a)]['ttft_sd'], arms[(tp, p, b)]['ttft_sd']), 0.15)
    return bt, bf
def inside(v, b): return 'inside' if abs(v) <= b else 'beyond'
def ttft_str(ms, pct, t): return (f"{ms/1000:+.1f} s" if abs(ms) >= 1000 else f"{ms:+d} ms") + f" ({pct:+.1f} %, t {t:+.1f})"
def ttft_plain(ms, pct): return (f"{ms/1000:+.1f} s" if abs(ms) >= 1000 else f"{ms:+d} ms") + f" ({pct:+.1f} %)"
def arm_rows(arms, cells, armlist, hbm=False):
    out = []
    for tp, p in cells:
        for a in armlist:
            r = arms[(tp, p, a)]
            out.append(f"| {label(tp,p)} | {a} | {r['tps']:.2f} ({r['tps_sd']:.2f}) | {r['ttft']:.3f} ({r['ttft_sd']:.3f}) |" + (f" {r['hbm']:.1f} |" if hbm else ''))
    return '\n'.join(out)
def pair_rows(arms, pairs, cells, pairlist):
    out = []
    for tp, p in cells:
        for a, b in pairlist:
            q = pairs[(tp, p, a, b)]; bt, bf = band(arms, tp, p, a, b)
            out.append(f"| {label(tp,p)} | {a} vs {b} | {q['tps_pct']:+.1f} % ({q['tps_mean']:+.2f} TPS, t {q['tps_t']:+.1f}), {inside(q['tps_mean'], bt)} | {ttft_str(q['ttft_ms'], q['ttft_pct'], q['ttft_t'])}, {inside(q['ttft_ms']/1000, bf)} | {bt:.2f} TPS / {bf:.2f} s |")
    return '\n'.join(out)
def pair_bullets(arms, pairs, cells, a, b, subject, metrics=('TPS', 'TTFT')):
    out = []
    for metric in metrics:
        parts = []
        for tp, p in cells:
            q = pairs[(tp, p, a, b)]; bt, bf = band(arms, tp, p, a, b)
            if metric == 'TPS': parts.append(f"{q['tps_pct']:+.1f} % ({q['tps_mean']:+.2f} TPS, {inside(q['tps_mean'], bt)} the {bt:.2f} TPS band, paired t {q['tps_t']:+.1f}) at {label(tp, p)}")
            else: parts.append(f"{ttft_plain(q['ttft_ms'], q['ttft_pct'])}, {inside(q['ttft_ms']/1000, bf)} the {bf:.2f} s band, paired t {q['ttft_t']:+.1f}, at {label(tp, p)}")
        out.append(f"- {metric} of {subject}:\n" + '\n'.join(f"  - {x}." for x in parts))
    return '\n'.join(out)
FPGA_PAIRS_TXT = '\n'.join(pair_bullets(arms_f, pairs_f, FPGA_CELLS, a, b, f"`{a}` against `{b}` (FPGA attention)") for a, b in [('head', 'base'), ('new', 'base'), ('new', 'head')])
FPGA_SD = '; '.join(f"{label(tp,p)}: " + ', '.join(f"{a} sd {arms_f[(tp,p,a)]['tps_sd']:.2f} TPS, HW-attention losses {arms_f[(tp,p,a)]['hbm']:.1f} per run" for a in FPGA_ARMS) for tp, p in FPGA_CELLS)
FPGA_PAIRS_TXT += f"\n- Standard deviations and HW-attention losses: {FPGA_SD}."

# ---- builds and tests ----
def build_secs(suffix):
    log = (RES / f'build-{suffix}.log').read_text()
    m = re.findall(r'build rc=0 in (\d+) s', log); assert m, ('build time', suffix); return int(m[-1])
BUILD = {s: build_secs(s) for s in ('pr4', 'pr4nd', 'pr4rm')}
BUILD_DATE = re.search(r'started (\d{4}-\d\d-\d\d)T', (RES / 'build-pr4.log').read_text()).group(1)
def counts(suffix):
    out = {}
    for line in (RES / f'tests-{suffix}.txt').read_text().splitlines():
        m = re.match(r'(\w+) rc=(\d+) tip=(\w+) env=\[([^\]]*)\] args=\[[^\]]*\] (.*)', line)
        if not m: continue
        t, rc, tip, env, rest = m.groups(); assert rc == '0' and tip == HEAD, line
        c = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', rest); assert c, line
        out[(t, env)] = (int(c.group(1)), int(c.group(2)), rest)
    return out
C_ON, C_ND, C_RM = counts('pr4'), counts('pr4nd'), counts('pr4rm')
TESTS = ['t_k_vnni_layout', 't_amx_dispatch_dtype', 't_amx_numerics', 't_llama_unit', 't_heterogeneous_scheduler', 't_phase1_integration']
def cell(cnt, t, note=''):
    if (t, '') not in cnt: return 'not built'
    a, c, _ = cnt[(t, '')]; return f"{a} / {c}{note}"
amx_on_out = (RES / 'tests-pr4-t_amx_numerics.out').read_text(); rm_out = (RES / 'tests-pr4rm-t_amx_numerics.out').read_text()
assert 'AMX unavailable' not in amx_on_out and 'AMX unavailable' not in rm_out, 'identity case did not run on AMX'
assert C_ON[('t_amx_numerics', '')][1] == 5 and C_RM[('t_amx_numerics', '')][1] == 5, 't_amx_numerics case count'
assert C_ND[('t_amx_numerics', '')][:2] == (1, 1) and C_ND[('t_amx_dispatch_dtype', '')][:2] == (1, 1), 'placeholders'
for cnt, nm in ((C_ON, 'on'), (C_ND, 'nd'), (C_RM, 'rm')): assert cnt[('t_k_vnni_layout', '')][1] == 10, ('t_k_vnni_layout cases', nm, cnt[('t_k_vnni_layout', '')])
test_rows = []
for t in TESTS:
    on = cell(C_ON, t, ' (AMX cases ran, no "AMX unavailable" line)' if t == 't_amx_numerics' else '')
    nd = cell(C_ND, t, ' (placeholder without dispatch)' if t in ('t_amx_numerics', 't_amx_dispatch_dtype') else '')
    rm = cell(C_RM, t, ' (AMX cases ran)' if t == 't_amx_numerics' else '')
    test_rows.append(f"| `{t}` | {on} | {nd} | {rm} |")
ks = {}
for line in (RES / 'tests-pr4.txt').read_text().splitlines():
    m = re.match(r'(\w+) killswitch rc=(\d+) env=\[TRON_AMX_DISABLE=1\] (.*)', line)
    if m: assert m.group(2) == '0', line; ks[m.group(1)] = m.group(3)
assert set(ks) == {'t_llama_unit', 't_amx_numerics'}, ks
def passed(rest):
    c = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', rest); assert c, rest; return int(c.group(1)), int(c.group(2))
lu, lu_c = passed(ks['t_llama_unit']); an, an_c = passed(ks['t_amx_numerics'])
ks_out = (RES / 'tests-pr4-t_amx_numerics-killswitch.out').read_text()
skipped = [n for n, pat in (('QK precision', 'QK precision check skipped'), ('identity', 'VNNI QK identity check skipped'), ('PV precision', 'PV precision check skipped')) if pat in ks_out]
assert len(skipped) == 3, skipped
lu_note = 'This matches the AMX-on count.' if lu == C_ON[('t_llama_unit', '')][0] else f"The AMX-on count is {C_ON[('t_llama_unit', '')][0]}."
killswitch_lines = f"- `t_llama_unit`: {lu} assertions passed in {lu_c} cases. {lu_note}\n- `t_amx_numerics`: {an} assertions passed in {an_c} cases. Its {', '.join(skipped[:-1])} and {skipped[-1]} cases reported \"AMX unavailable\"."

# ---- mutation checks ----
def mutation(n, binary, srcfile, capture=None):
    mrun = (RES / f'mutation{n}-run.out').read_text(); mres = (RES / f'mutation{n}-result.txt').read_text()
    tc = re.search(r'test cases:\s*(\d+)\s*\|(?:\s*(\d+) passed\s*\|)?\s*(\d+) failed', mrun); asr = re.search(r'assertions:\s*(\d+)\s*\|(?:\s*(\d+) passed\s*\|)?\s*(\d+) failed', mrun)
    locs = re.findall(rf'({re.escape(srcfile)}):(\d+): FAILED', mrun); assert tc and asr and locs, (f'mutant {n} summary lines', tc, asr, locs)
    assert 'No tests ran' not in mrun and tc.group(1) == '1' and tc.group(3) == '1', ('mutant ran exactly one case', tc.groups())
    assert re.search(rf'^mutant {binary} rc=[1-9]', mres, re.M) and re.search(rf'^restored {binary} rc=0', mres, re.M), mres
    restored = re.search(r'All tests passed \((\d+) assertions? in (\d+) test cases?\)', (RES / f'tests-pr4-{binary}-restored.out').read_text()); assert restored
    assert (int(restored.group(1)), int(restored.group(2))) == C_ON[(binary, '')][:2], f'restored counts of {binary} differ from step A'
    passed_n = int(asr.group(2)) if asr.group(2) else 0
    lines = sorted(set(l for _, l in locs), key=int)
    where = f"the `REQUIRE` of `{srcfile}:{lines[0]}`" if len(lines) == 1 else f"the `REQUIRE` of `{srcfile}:{', '.join(lines)}`"
    text = f"The run reports {tc.group(3)} of {tc.group(1)} test cases failed and {asr.group(3)} of {asr.group(1)} assertions failed ({len(locs)} \"FAILED\" line{'s' if len(locs) != 1 else ''}), at {where}"
    text += f" ({passed_n} earlier assertions passed)." if passed_n else "."
    if capture:
        cap = re.findall(rf'^\s*{capture} := (\d+)', mrun, re.M); assert cap, ('capture', capture); text += f" The captured value is {capture} = {cap[0]}."
    return text, f"{restored.group(1)} assertions in {restored.group(2)} cases"
MUT1, RESTORED1 = mutation(1, 't_k_vnni_layout', 't/t_k_vnni_layout.cpp', capture='tok')
MUT2, RESTORED2 = mutation(2, 't_llama_unit', 't/t_llama_unit.cpp')

# ---- A2 skipped, the plugin table ----
steps = (RES / 'steps.txt').read_text()
assert re.search(r'STEP A2: skipped: PR-4 changes no file under ingest/', steps), 'STEP A2 skipped line'
pl = (RES / 'plugin-calls-pr4.txt').read_text().splitlines()
assert pl[-1].startswith('PASS'), pl[-1]
PLUGIN_PASS = f"`{pl[-1].strip()}`"
plugin_rows = []
for line in pl:
    m = re.match(r'(\S+\.hpp)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+ok$', line)
    if m:
        assert m.group(2) == m.group(3) == m.group(4) and int(m.group(2)) > 0 and m.group(5) == '0' and m.group(6) == '0', line
        plugin_rows.append(f"| `{m.group(1)}` | {m.group(2)} | {m.group(3)} | {m.group(4)} |")
assert len(plugin_rows) == 19, len(plugin_rows)
pl3 = (E / 'results' / 'pr3-20261012' / 'plugin-calls-pr3.txt').read_text().splitlines()
assert [l.split()[:6] for l in pl if l.endswith(' ok')] == [l.split()[:6] for l in pl3 if l.endswith(' ok')], 'plugin counts differ from PR-3'

# ---- format, lint-notes ----
f = (RES / 'format-pr4.txt').read_text()
for k in ('clang-format rc=0', 'diff-check rc=0', 'cassert-in-diff 0', 'files: 10'): assert re.search(rf'^{re.escape(k)}\s*$', f, re.M), ('format', k)
ln = (RES / 'lint-notes-pr4.txt').read_text().strip().splitlines()[-1]
assert ln.strip() == 'lint-notes rc=0', ln
LINT_NOTES = "`make lint-notes`, the Note-reference check, in the repository's lint shell: the two new Notes are defined and every reference resolves."

# ---- the deb builds ----
def deb(arm):
    log = (RES / f'deb-{arm}.log').read_text()
    ver = re.search(r'deb Version field: (\S+)', log).group(1)
    pc = re.search(r'package checks: TRON_AMX_DISABLE literal=(\d+) AMX tile insns=(\d+) strings matching vnni=(\d+)', log)
    secs = re.search(r'make deb done in (\d+) s', log).group(1)
    preset = re.search(r'deb preset cacheVariables: (\{.*\})', log).group(1)
    assert re.search(rf'deb {arm} rc=0', log), ('deb rc', arm)
    d = json.loads(preset)
    assert d.get('TRON_AMX_DISPATCH') == 'ON' and ((arm == 'base' and 'TRON_K_VNNI' not in d) or (arm == 'target' and d.get('TRON_K_VNNI') == 'ON')), (arm, d)
    return ver, pc, secs, d
W_BASE_VERSION, pc_b, secs_b, d_b = deb('base'); W_TARGET_VERSION, pc_t, secs_t, d_t = deb('target')
DEB_LINES = (f"- The base deb, version `{W_BASE_VERSION}`, from `main` at `72308ec90c`, in {secs_b} s. The `deb` preset's cache variables as the configure step prints them: `TRON_AMX_DISPATCH` ON, no `TRON_K_VNNI`. Package checks on its rinzler: the `TRON_AMX_DISABLE` literal {pc_b.group(1)} time{'s' if pc_b.group(1) != '1' else ''}, {pc_b.group(2)} AMX tile instructions.\n"
             f"- The target deb, version `{W_TARGET_VERSION}`, from this branch at `{HEAD_SHORT}`, in {secs_t} s. The `deb` preset's cache variables: `TRON_AMX_DISPATCH` ON and `TRON_K_VNNI` ON. Package checks: the `TRON_AMX_DISABLE` literal {pc_t.group(1)} time{'s' if pc_t.group(1) != '1' else ''}, {pc_t.group(2)} AMX tile instructions.")

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
SPAIRS = [('new', 'new2'), ('new', 'base'), ('new', 'head'), ('newoff', 'new'), ('head', 'base')]
smoke_rows = [f"| {lab} | " + ' | '.join(first_diff(c, a, b) for a, b in SPAIRS) + ' |' for c, lab in SMOKE_CELLS]
SMOKE_DATE = re.search(r' (\d{4}-\d\d-\d\d)T\d\d:\d\d:\d\dZ load=', smoke_txt('cpu-p1024')).group(1)
def outcome(a, b, cells, expect_identical):
    xs = [(lab, first_diff(c, a, b), first_diff_ids(c, a, b)) for c, lab in SMOKE_CELLS if c in cells]
    if all(x.startswith('identical') for _, x, _ in xs): return f"`{a}` matched `{b}` for all 256 tokens in {'every cell' if len(xs) == 3 else 'the ' + ' and '.join(lab for lab, _, _ in xs)}." + (" This is the expected result." if expect_identical else "")
    return f"`{a}` against `{b}`: " + '. '.join(f"{lab}: {x}" + (f" of {ids[1]} (token id {ids[2]} for `{a}`, {ids[3]} for `{b}`)" if ids else '') for lab, x, ids in xs) + "." + (" This is NOT the expected result (see Open items)." if expect_identical else "")
IDENTITY_TEXT = '\n'.join([
    "- Every binary exited with status 0 and produced 256 tokens in every cell.",
    "- " + outcome('new', 'new2', {'cpu-p1024', 'cpu-p8192', 'fpga-p1024'}, True),
    "- " + outcome('new', 'base', {'cpu-p1024', 'cpu-p8192'}, True) + " This is the correctness claim of the PR for the measured CPU cells.",
    "- " + outcome('new', 'head', {'fpga-p1024'}, True),
    "- " + outcome('newoff', 'new', {'cpu-p1024', 'cpu-p8192', 'fpga-p1024'}, True),
    "- " + outcome('new', 'head', {'cpu-p1024', 'cpu-p8192'}, False) + " `head` differs from `base` at the same tokens where it differs from `new` (the block-save PR's reader on a page the dotter scores here).",
    "- " + outcome('head', 'base', {'cpu-p1024', 'cpu-p8192', 'fpga-p1024'}, False),
])
NEWOFF_NEW_V = outcome('newoff', 'new', {'cpu-p1024', 'cpu-p8192', 'fpga-p1024'}, True).replace(' This is the expected result.', '') + " [Measurements, Token identity]"
DIVERGENCE_V = outcome('new', 'base', {'cpu-p1024', 'cpu-p8192'}, True).replace(' This is the expected result.', '') + " " + outcome('new', 'base', {'fpga-p1024'}, False) + " [Measurements, Token identity]"

# ---- host suite ----
hs = (RES / 'host-suite-pr4.txt').read_text()
m = re.search(r'(\d+) passed, (\d+) skipped, (\d+) failed\s+•\s+makespan ([\d.]+)s', hs); assert m, 'host summary line'
hp, hsk, hf, mk = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
assert re.search(r'^build-test-host rc=0', hs, re.M), 'build-test-host rc'
assert (hsk, hf) == (1, 1) and 'failed: t_proxy_llama31' in hs, (hp, hsk, hf)
hlog = (RES / 'host-suite-pr4.log').read_text()
assert 'cache after:' in hlog and 'TRON_K_VNNI:BOOL=ON' in hlog.split('cache after:')[1], 'TRON_K_VNNI kept'
host_lines = (f"- All test targets compiled.\n- {hp} tests passed.\n- {hsk} test skipped. The captured suite output reports the count and not the test's name. The exception rules permit one skip, `t_proxy_lib`, for the missing `t/proxy/.venv`.\n"
              f"- {hf} test failed: `t_proxy_llama31`, reporting \"ERROR: t/proxy/.venv missing\".\n- Total suite time: {mk:.0f} s.\n- The CMake cache retained `TRON_K_VNNI=ON` throughout the make targets.")

# ---- the cost rows ----
blog = (RES / 'bench-update.log').read_text(); bdiff = (RES / 'bench-update.diff').read_text()
assert re.search(r'^bench-update rc=0', blog, re.M) and 'BENCH FAILURES' not in blog and '[FAILED]' not in blog and '[SKIPPED]' not in blog, 'bench'
before = json.load(open(RES / 'test-benchmarks.before.json'))
meas = re.findall(r'\[\s*\d+/\d+\]\s+(\S+)\s+@\s+(\d)slice\s+([\d.]+)s\s*/\s*(\d+)MB', blog)
assert len(meas) == 12, ('bench lines', meas)
new_vals = {}
for t, w, s, mb in meas: new_vals.setdefault(t, {})[int(w)] = float(s)
def old_vals(t):
    rows = [e for e in before['granite_rapids_6962p']['tests'] if e.get('name') == t]
    assert len(rows) == 1, ('old row', t, len(rows))
    return rows[0]['times']
after_json = json.loads(re.sub(r'^[-+ @].*$', '', '', flags=re.M) or '{}') if False else None
plus = {m.group(1): json.loads(m.group(2)) for m in re.finditer(r'^\+\s*(?:\{"name":"(\S+?)",.*?"times":(\{[^}]*\}))', bdiff, re.M)}
minus = {m.group(1): json.loads(m.group(2)) for m in re.finditer(r'^-\s*(?:\{"name":"(\S+?)",.*?"times":(\{[^}]*\}))', bdiff, re.M)}
assert set(plus) == set(minus) == {'t_k_vnni_layout', 't_llama_unit', 't_amx_numerics', 't_amx_dispatch_dtype'}, (sorted(plus), sorted(minus))
bench_rows = []
for t in ('t_k_vnni_layout', 't_llama_unit', 't_amx_numerics', 't_amx_dispatch_dtype'):
    o = old_vals(t); assert o == minus[t], ('old row vs diff', t, o, minus[t])
    n = plus[t]
    for w in (1, 2, 4): assert abs(n[str(w)] - new_vals[t][w]) < 0.051, ('new row vs log', t, w, n, new_vals[t])
    bench_rows.append(f"| `{t}` | {o['1']} / {o['2']} / {o['4']} | {n['1']} / {n['2']} / {n['4']} |")
BENCH_LINES = "| Test | Old (1 / 2 / 4 slices, s) | New (1 / 2 / 4 slices, s) |\n|---|---|---|\n" + '\n'.join(bench_rows) + f"\n\nThe diff of the record touches {bdiff.count(chr(10)+'+')-1} added and {bdiff.count(chr(10)+'-')-1} removed lines, the four rows of the `granite_rapids_6962p` block. `bin/slice bench --check` reads them."

# ---- campaign W ----
NO_W = '--no-w' in sys.argv   # leave the campaign placeholders for later (the chain parts only)
wsum = (WRES / 'summary.md').read_text() if not NO_W else ''
W_CONFIGS = ['llama-3.1-8b-instruct-good-tp2@8u-p1024', 'llama-3.1-8b-instruct-good-tp2@32u-p4096', 'ingested-gpt-oss-120b-tp4@8u-p1024']
w_rows = {}
if NO_W:
    W_ROWS = '{{W_ROWS}}'; W_PASSES = '{{W_PASSES}}'; W_DATES = '{{W_DATES}}'
for line in ([] if NO_W else wsum.splitlines()):
    c = [x.strip() for x in line.strip().strip('|').split('|')]
    if c and c[0] in W_CONFIGS and len(c) >= 13: w_rows[c[0]] = c
assert NO_W or set(w_rows) == set(W_CONFIGS), sorted(w_rows)
for k, c in w_rows.items(): assert 'n=2' in c[1] and 'n=2' in c[2], ('W passes', k, c[1], c[2])
if not NO_W: W_ROWS = '\n'.join(f"| {k} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} | {c[6]} | {c[7]} | {c[8]} | {c[9]} | {c[10]} | {c[11]} | {c[12]} |" for k, c in ((k, w_rows[k]) for k in W_CONFIGS))
if not NO_W:
    runs = re.search(r'Runs found: (.*)', wsum).group(1)
    W_PASSES = ', '.join(re.findall(r'(\w+-pass\d) \(', runs))
    outc = (WRES / 'outcome.txt').read_text().strip()
    assert outc.startswith('incomplete passes: none; stop reason: none; problems: none; known systematic failures: none'), outc
    sh = (WRES / 'status-history.log').read_text()
    dates = sorted(set(re.findall(r'(\d{4}-\d\d-\d\d)T', sh)))
    W_DATES = ' and '.join(dates) if len(dates) <= 2 else f"{dates[0]} to {dates[-1]}"
    W_DATES += f"; outcome: {outc.split(';')[-1].strip()}" if 'recovered' in outc else ''

# ---- fill ----
F = {'HEAD_SHORT': HEAD_SHORT, 'PR3_SHORT': PR3_SHORT, 'PUSHED_SHORT': PUSHED_SHORT, 'E_DATE': E_DATE,
     'ARM_ROWS_CPU': arm_rows(arms_c, CPU_CELLS, CPU_ARMS), 'PAIR_ROWS_CPU': pair_rows(arms_c, pairs_c, CPU_CELLS, CPU_PAIRS),
     'ARM_ROWS_FPGA': arm_rows(arms_f, FPGA_CELLS, FPGA_ARMS, hbm=True), 'PAIR_ROWS_FPGA': pair_rows(arms_f, pairs_f, FPGA_CELLS, FPGA_PAIRS),
     'FPGA_PAIRS': FPGA_PAIRS_TXT,
     'TPS_HEAD': pair_bullets(arms_c, pairs_c, CPU_CELLS, 'new', 'head', '`new` against `head`', ('TPS',)), 'TTFT_HEAD': pair_bullets(arms_c, pairs_c, CPU_CELLS, 'new', 'head', '`new` against `head`', ('TTFT',)),
     'AGAINST_MAIN': pair_bullets(arms_c, pairs_c, CPU_CELLS, 'new', 'base', '`new` against `base`'), 'KILL_SWITCH': pair_bullets(arms_c, pairs_c, CPU_CELLS, 'newoff', 'new', '`newoff` against `new`'),
     'AMX_OFF': pair_bullets(arms_c, pairs_c, CPU_CELLS, 'newoff', 'headoff', '`newoff` against `headoff`'), 'HEAD_BASE': pair_bullets(arms_c, pairs_c, CPU_CELLS, 'head', 'base', '`head` against `base`'),
     'W_BASE_VERSION': W_BASE_VERSION, 'W_TARGET_VERSION': W_TARGET_VERSION, **({} if NO_W else {'W_PASSES': W_PASSES, 'W_DATES': W_DATES, 'W_ROWS': W_ROWS}),
     'SMOKE_DATE': SMOKE_DATE, 'SMOKE_ROWS': '\n'.join(smoke_rows), 'IDENTITY_TEXT': IDENTITY_TEXT,
     'BUILD_DATE': BUILD_DATE, 'BUILD_PR4': str(BUILD['pr4']), 'BUILD_PR4ND': str(BUILD['pr4nd']), 'BUILD_PR4RM': str(BUILD['pr4rm']), 'TEST_ROWS': '\n'.join(test_rows),
     'KILLSWITCH_LINES': killswitch_lines, 'MUTATION1': MUT1, 'RESTORED1': RESTORED1, 'MUTATION2': MUT2, 'RESTORED2': RESTORED2,
     'DEB_LINES': DEB_LINES, 'PLUGIN_PASS': PLUGIN_PASS, 'PLUGIN_ROWS': '\n'.join(plugin_rows), 'LINT_NOTES': LINT_NOTES, 'HOST_LINES': host_lines, 'BENCH_LINES': BENCH_LINES,
     'NEWOFF_NEW_V': NEWOFF_NEW_V, 'DIVERGENCE_V': DIVERGENCE_V}
for k, v in F.items():
    assert f'{{{{{k}}}}}' in body, ('placeholder missing in body', k)
    body = body.replace(f'{{{{{k}}}}}', v)
left = set(re.findall(r'\{\{([A-Z_0-9]+)\}\}', body)); assert left <= HAND | {'PUSHED_SHORT'} | ({'W_PASSES', 'W_DATES', 'W_ROWS'} if NO_W else set()), ('unfilled placeholders other than the hand-written ones', left - HAND)
if check:
    for k, v in F.items(): print(f'--- {k}\n{v}')
    print('left for hand writing:', sorted(left)); print('check ok (nothing written)')
else:
    body_p.write_text(body); print('filled', body_p, 'left for hand writing:', sorted(left))
