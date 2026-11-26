#!/usr/bin/env python3
"""test_stage0.py: checks of stage0.py. Prints one line per check. Exit status 0 only if every check passed.

Three groups:
1. Rules on constructed inputs. Each rule has a case that it must reject.
2. Check values that the design and its review record state, recomputed from the saved files.
3. The page and the JSON file that stage0.py writes.
"""
import copy, json, os, re, sys, tempfile
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import stage0 as s          # noqa: E402

FAILED = []
SCRATCH = os.path.join(HERE, 'stage0-render')      # scratch folder of this part
os.makedirs(SCRATCH, exist_ok=True)


def check(name, ok, detail=''):
    print('%s  %s%s' % ('PASS' if ok else 'FAIL', name, ('  [' + detail + ']') if detail else ''))
    if not ok:
        FAILED.append(name)


def near(a, b, tol):
    return abs(a - b) <= tol


def proc(cpu, rates_by_pos, tag='p', thp=True):
    """A constructed bwx process. rates_by_pos: {position: [rate of round 0, round 1, ...]}."""
    T = [dict(round=rd, pos=q, kernel='k', bytes=0, elapsed_s=0.3, t_start=rd * 10 + q, t_end=rd * 10 + q + 0.3, rate=r)
         for q, v in rates_by_pos.items() for rd, r in enumerate(v)]
    return dict(cpu=cpu, tag=tag, thp=thp, count=False, T=T, P=[], seq=['k'] * 13, utc='-', load1=0.0)


# ---------------------------------------------------------------- 1. rules on constructed inputs

# A/A value: median of repeats 1 and 3 minus median of repeats 2 and 4.
check('aa_value: {1,3} against {2,4}', near(s.aa_value([10.0, 20.0, 12.0, 26.0]), 11.0 - 23.0, 1e-12))
check('aa_value: equal halves give 0', s.aa_value([5.0, 5.0, 7.0, 7.0]) == 0.0)
check('aa_value: is not the split {1,2} against {3,4}', s.aa_value([1.0, 1.0, 9.0, 9.0]) == 0.0 and s.aa_value([1.0, 9.0, 1.0, 9.0]) == -8.0)

# Blocks of four successive intervals. A jump inside a block is a transition block and stays in the list.
calm = [67.0, 67.1, 67.0, 67.1] * 3
jump = [67.0, 67.0, 67.0, 67.0, 67.0, 71.0, 71.0, 71.0, 71.0, 71.0, 71.0, 71.0]
bc, bj = s.block_aa(calm), s.block_aa(jump)
check('block_aa: 12 intervals give 3 blocks', len(bc) == 3 and len(bj) == 3)
check('block_aa: a partial last block is not used', len(s.block_aa(calm + [67.0, 67.0])) == 3)
check('block_aa: calm blocks are not transitions', not any(b['transition'] for b in bc))
check('block_aa: the block with the jump is a transition and keeps its value', [b['transition'] for b in bj] == [False, True, False] and near(bj[1]['aa'], 69.0 - 71.0, 1e-12))

# Feasibility: the largest value per process, then per CPU and session. Transitions are not deleted.
quiet_b6 = {1: [proc(2, {2: [67.1, 67.1, 67.1, 67.1], 4: [67.1, 67.1, 67.1, 67.1], 5: [67.00, 67.02, 67.00, 67.02]}, 'a'),
                proc(2, {2: [67.1, 67.1, 67.1, 67.1], 4: [67.1, 67.1, 67.1, 67.1], 5: [67.00, 67.06, 67.00, 67.06]}, 'b')]}
b4_jump = {1: [proc(2, {0: jump}, 'thp-j'), proc(2, {0: calm}, 'thp-c'), proc(2, {0: [60.0, 70.0, 60.0, 70.0]}, 'nothp', thp=False)]}
c1_calm = {1: [proc(2, {0: calm}, 'c')]}
fe = s.feasibility(quiet_b6, b4_jump, c1_calm)
row = lambda src: [r for r in fe['rows'] if r['source'] == src][0]
check('feasibility: B6 spread is the largest process value', near(row('B6 position 5')['spread'], 0.06, 1e-9))
check('feasibility: limits are 2, 4 and 8 times the spread', near(row('B6 position 5')['limit2'], 0.12, 1e-9) and near(row('B6 position 5')['limit4'], 0.24, 1e-9)
      and near(row('B6 position 5')['limit8'], 0.48, 1e-9))
check('feasibility: a transition block stays in the spread', near(row('B4')['spread'], 2.0, 1e-9) and row('B4')['transitions'] == 1)
check('feasibility: the value without transition blocks is shown beside it, not used', near(row('B4')['spread_no_transition'], 0.1, 1e-9))
check('feasibility: processes without huge pages are a separate row', near(row('B4 without huge pages')['spread'], 10.0, 1e-9) and row('B4')['n_proc'] == 2)
check('limit_of: rows without huge pages do not enter L0', near(s.limit_of(fe['rows'], s.ASM8), 4.0, 1e-9))
check('limit_of: a CPU outside the design does not enter L0', s.limit_of(s.feasibility({1: [proc(94, {2: [1, 2, 1, 2], 4: [1, 2, 1, 2], 5: [1, 2, 1, 2]})]}, {}, {})['rows'], s.OLD8) is None)

# Margin rule, design lines 189 to 191.
check('roundup05: 0.31 goes up to 0.35', near(s.roundup05(0.31), 0.35, 1e-9))
check('roundup05: 0.30 stays 0.30', near(s.roundup05(0.30), 0.30, 1e-9))
check('roundup05: never rounds down', s.roundup05(0.3001) > 0.30)
m = s.margin_rule(0.0, 0.10, 0.30)
check('margin_rule: L0 = 0 gives the lower bound and is feasible', near(m['margin'], 0.10, 1e-9) and m['forecast'] == 'feasible')
m = s.margin_rule(0.04, 0.10, 0.30)
check('margin_rule: L0 = 0.04 gives 0.10, largest passing median 0.06', near(m['margin'], 0.10, 1e-9) and near(m['largest_passing_median'], 0.06, 1e-9) and not m['clipped'])
m = s.margin_rule(0.11, 0.10, 0.30)
check('margin_rule: L0 = 0.11 gives 0.25 (twice L0, rounded up)', near(m['margin'], 0.25, 1e-9) and m['forecast'] == 'feasible')
m = s.margin_rule(0.20, 0.10, 0.30)
check('margin_rule: L0 = 0.20 is clipped to 0.30 and still feasible', near(m['margin'], 0.30, 1e-9) and m['clipped'] and near(m['largest_passing_median'], 0.10, 1e-9))
m = s.margin_rule(0.30, 0.10, 0.30)
check('margin_rule: L0 at the margin is rejected', m['forecast'] == 'precision insufficient' and m['largest_passing_median'] is None)
m = s.margin_rule(2.84, 0.10, 0.30)
check('margin_rule: a noisy condition is rejected, the margin is not widened', m['forecast'] == 'precision insufficient' and near(m['margin'], 0.30, 1e-9))
m = s.margin_rule(0.31, 0.20, 0.60)
check('margin_rule: the four-rate bounds are 0.20 to 0.60', near(m['margin'], 0.60, 1e-9) and m['forecast'] == 'feasible')

# L0 per selected use (note 3): a noisy condition fails only the uses that need it.
U = {u['use']: u for u in s.uses(fe['rows'])}
check('uses: P3G is rejected by assembly read', U['P3G']['forecast'] == 'precision insufficient' and U['P3G']['scheduled_by_default'] is False)
check('uses: S3G does not inherit the assembly-read limit', U['S3G']['forecast'] == 'feasible' and near(U['S3G']['L0'], 0.12, 1e-9))
check('uses: BIN and CS are decided per kernel and size', U['BIN old read at 1 MiB']['forecast'] == 'feasible' and U['CS assembly read at 8 MiB']['forecast'] == 'precision insufficient')
check('uses: the two-rate use has four spreads', near(U['CM history contrast']['L0'], 0.24, 1e-9))
calm_all = s.feasibility(quiet_b6, {1: [proc(2, {0: [67.00, 67.02, 67.00, 67.02] * 3})]}, c1_calm)
U2 = {u['use']: u for u in s.uses(calm_all['rows'])}
check('uses: P3G with calm saved kernels is not called feasible, new read is missing', U2['P3G']['forecast'] == s.ID and U2['P3G']['largest_passing_median'] is None)
check('uses: CM one rate needs new read too', U2['CM one rate']['forecast'] == s.ID)
check('uses: the four-rate interaction uses the bounds 0.20 to 0.60 (4 x 0.06 = 0.24 gives 0.50, not 0.30)', near(U['CM interaction']['margin'], 0.50, 1e-9))
check('uses: the two-rate contrast uses the bounds 0.10 to 0.30 (0.24 gives 0.30, not 0.50)', near(U['CM history contrast']['margin'], 0.30, 1e-9))
for step in ('BIN', 'CS'):
    o = U2[step + ' other selections']
    check('uses: %s selections without saved repeats are Insufficient data, also when every saved kernel is calm' % step,
          o['forecast'] == s.ID and o['parts'] == {} and o['scheduled_by_default'] is False and 'step S2' in o['missing'])
sel = s.other_selections()
check('uses: 12 of the 15 Stage 2 selections have no saved repeats, all 5 sizes of new read among them',
      sum(len(v) for v in sel.values()) == 12 and sel['new read'] == ['32K', '1M', '4M', '8M', '16M'] and sel['old read'] == ['32K', '4M', '16M']
      and sel['assembly read'] == ['32K', '1M', '4M', '16M'] and all(s.SIZE_NAME[z] in s.OTHER_MISSING for z in s.STAGE2_SIZES))
check('uses: CM interaction counts only the 4 known of 8 spreads', U2['CM interaction']['spreads'] == 8 and U2['CM interaction']['spreads_known'] == 4 and U2['CM interaction']['forecast'] == s.ID)

# B6 pairs: the count of "first slower" must fall when one pair is reversed.
mk = lambda first, second: {q: [67.0] * 4 for q in range(13)} | {7: first, 8: second, 10: first, 11: second}
facts = s.b6_facts({1: [proc(2, mk([63.0] * 4, [66.0] * 4))]})
ps = s.pair_summary(facts['pairs'])
check('pairs: 4 rounds and 2 places give 8 pairs, all with the first slower', sum(x['n'] for x in ps) == 8 and sum(x['first_slower'] for x in ps) == 8)
facts = s.b6_facts({1: [proc(2, mk([63.0, 63.0, 66.5, 63.0], [66.0] * 4))]})
ps = s.pair_summary(facts['pairs'])
check('pairs: a round with the first interval faster is counted as not slower', sum(x['first_slower'] for x in ps) == 6)
one = {q: [67.0] * 4 for q in range(13)} | {7: [63.0, 63.0, 66.5, 63.0], 8: [66.0] * 4, 10: [63.0] * 4, 11: [66.0] * 4}
two = s.b6_facts({1: [proc(2, one)], 2: [proc(2, mk([63.0] * 4, [66.0] * 4))]})
bs = s.pairs_by_session(two['pairs'])
check('pairs per session: one reversed pair gives 7 of 8, the other session keeps 8 of 8', bs[1] == dict(n=8, first_slower=7) and bs[2] == dict(n=8, first_slower=8), str(bs))
check('pairs: the difference is first minus second of the same round', near(facts['pairs'][0]['diff'], -3.0, 1e-12))
facts = s.b6_facts({1: [proc(2, {q: [67.0] * 4 for q in range(13)} | {1: [62.0] * 4, 2: [67.1] * 4, 4: [67.3] * 4, 5: [67.0] * 4})]})
check('size difference: position 1 minus 2 (not minus 4), and position 5 minus 4 (not minus 2)', near(facts['sizediff'][0]['first'], -5.1, 1e-9) and near(facts['sizediff'][0]['second'], -0.3, 1e-9))
hp = lambda total, huge: dict(proc(2, {q: [67.0] * 4 for q in range(13)}), P=[dict(kb_total='8192', kb_huge='8192'), dict(kb_total=total, kb_huge=huge)])
check('huge pages: one page record with partial coverage makes the process not fully covered',
      s.b6_facts({1: [hp('8192', '8192')]})['processes'][0]['huge_full'] and not s.b6_facts({1: [hp('8192', '6144')]})['processes'][0]['huge_full'])
tr = s.trace_facts({1: [proc(2, {0: [68.0, 69.5, 70.0, 71.0]})]}, 'B4')[0]
check('reference trace: intervals are counted below 69 and above 70.5 GB/s separately', tr['below_low'] == 1 and tr['above_high'] == 1 and tr['n'] == 4)

# P1 emulation: one set outside the margin must fail, also with a small median.
ok6 = [proc(2, {4: [67.10] * 4, 5: [67.00, 67.02, 67.00, 67.02]}, 'p%d' % i) for i in range(6)]
check('p1 emulation: small differences fit 0.30', s.p1_emulation({1: ok6})[0]['within_030'])
bad = ok6[:5] + [proc(2, {4: [67.10] * 4, 5: [66.70] * 4}, 'out')]
e1 = s.p1_emulation({1: bad})[0]
check('p1 emulation: one process outside the margin fails, the median stays small', not e1['within_030'] and abs(median(e1['diffs'])) < 0.15)

# Machine code: a changed instruction and a moved loop must both be seen.
LIST = """=== %s %s ===
0000000000001000 <%s>:
    %x:\tadd\tx1, x0, x1, lsl #3
    %x:\tldp\tq0, q1, [x0]
    %x:\t%s
    %x:\tcmp\tx0, x1
    %x:\tb.cc\t%x <%s+0x4>  // b.lo
    %x:\tret
"""


def listing(binary, name, base, third='add\tx0, x0, #0x100'):
    a = [base + 4 * i for i in range(6)]
    return LIST % (binary, name, name, a[0], a[1], a[2], third, a[3], a[4], a[1], name, a[5])


with tempfile.TemporaryDirectory(dir=SCRATCH) as d:
    def parse(text):
        p = os.path.join(d, 'l.txt')
        open(p, 'w').write(text)
        return s.parse_listing(p)
    A = parse(listing('bwx', 'k_a', 0x3a20))[('bwx', 'k_a')]
    B = parse(listing('bw', 'k_b', 0x1c60))[('bw', 'k_b')]
    C = parse(listing('bw', 'k_b', 0x1c60, 'add\tx0, x0, #0x80'))[('bw', 'k_b')]
    Dm = parse(listing('bw', 'k_b', 0x1c68))[('bw', 'k_b')]
check('listing: 6 instructions are read, comments removed', len(A) == 6 and '//' not in A[4][1])
check('listing: the same code at another address is equal after normalising', s.normalise(A, A[0][0]) == s.normalise(B, B[0][0]) and [t for _, t in A] != [t for _, t in B])
check('listing: one changed instruction is NOT equal', s.normalise(A, A[0][0]) != s.normalise(C, C[0][0]))
check('listing: the loop is the target of the backward branch', s.loop_of(A) == (0x3a24, 0x3a30))
check('listing: equal loop offset modulo 64 at 0x3a24 and 0x1c64', s.loop_of(A)[0] % 64 == s.loop_of(B)[0] % 64 == 36)
check('listing: a function moved by 8 bytes has another loop offset', s.loop_of(Dm)[0] % 64 == 44)

check('find_line: counts lines from 1', s.find_line('a\nb\nc d\n', '', 'c d') == 3)
check('find_line: searches after the anchor', s.find_line('x\nmain\nx\n', 'main', 'x') == 3)
check('find_line: a missing text gives None', s.find_line('a\nb\n', '', 'zzz') is None)

# ---------------------------------------------------------------- 2. check values from the saved files

D = s.compute()

design = {'32K': (66.76, 133.22, 99.55), '1M': (67.13, 85.26, 27.01), '8M': (67.08, 67.71, 0.94), '1G': (28.72, 30.89, 7.56)}
for r in D['item1']['best']:
    o, n, g = design[r['size']]
    check('design table, %s: %.2f / %.2f GB/s, gain %.2f %%' % (r['size'], o, n, g), near(r['old'], o, 0.0051) and near(r['new'], n, 0.0051) and near(r['gain_pct'], g, 0.0051),
          '%.2f %.2f %.2f' % (r['old'], r['new'], r['gain_pct']))
g8 = sorted(round(p['gain_pct'], 2) for p in D['item1']['pairs'] if p['size'] == '8M')
check('process-median gains at 8 MiB: 0.51, 0.51, 0.69, 0.94 %', g8 == [0.51, 0.51, 0.69, 0.94], str(g8))
check('original run: 32 read processes, one kernel each, 3 repetitions each', len(D['item1']['rows']) == 32 and D['item1']['one_kernel_per_process'])
check('original run keeps CPU, binary, round and run order', all(k in D['item1']['rows'][0] for k in ('cpu', 'binary', 'kernel', 'round', 'order'))
      and [r['order'] for r in D['item1']['rows']] == sorted(r['order'] for r in D['item1']['rows']))

for ses in (1, 2):
    b = D['pairs_by_session'][ses]
    check('B6 session %d: first old-read interval slower in all 192 pairs' % ses, b['n'] == 192 and b['first_slower'] == 192, '%d of %d' % (b['first_slower'], b['n']))
check('B6: the session counts equal the sums of the chart rows', all(
    D['pairs_by_session'][ses]['first_slower'] == sum(x['first_slower'] for x in D['pair_summary'] if x['session'] == ses) for ses in (1, 2)))
check('B6 pair chart rows: 2 sessions x 3 CPUs x 2 places, 32 pairs each', len(D['pair_summary']) == 12 and all(x['n'] == 32 for x in D['pair_summary']))
check('B6 pair difference is not the 8 MiB minus 1 MiB value', all(x['pos_first'] in (7, 10) and x['pos_second'] in (8, 11) for x in D['b6']['pairs']))

pm = [x['median'] for x in D['b6']['pooled_second']]
check('pooled medians of positions 8 and 11: 64.98 to 66.97 GB/s', near(min(pm), 64.98, 0.0051) and near(max(pm), 66.97, 0.0051) and all(x['n'] == 64 for x in D['b6']['pooled_second']),
      '%.3f to %.3f' % (min(pm), max(pm)))
check('position 5 intervals: 66.91 to 67.08 GB/s', near(D['pos5_range'][0], 66.91, 0.0051) and near(D['pos5_range'][1], 67.08, 0.0051), '%.3f to %.3f' % tuple(D['pos5_range']))
sd = D['b6']['sizediff']
check('old 8 MiB minus old 1 MiB directly after assembly read: -3.44 to -5.54 GB/s', near(max(x['first'] for x in sd), -3.44, 0.0051) and near(min(x['first'] for x in sd), -5.54, 0.0051),
      '%.3f to %.3f' % (max(x['first'] for x in sd), min(x['first'] for x in sd)))
check('old 8 MiB minus old 1 MiB after old read at 1 MiB: -0.06 to -0.11 GB/s', near(max(x['second'] for x in sd), -0.06, 0.0051) and near(min(x['second'] for x in sd), -0.11, 0.0051),
      '%.3f to %.3f' % (max(x['second'] for x in sd), min(x['second'] for x in sd)))

fr = D['feasibility']['rows']
p5 = {(r['session'], r['cpu']): r['limit2'] for r in fr if r['source'] == 'B6 position 5'}
check('two-spread limits of position 5 on CPU 2: 0.1546 and 0.1178 GB/s', near(p5[(1, 2)], 0.1546, 0.00005) and near(p5[(2, 2)], 0.1178, 0.00005), '%.4f %.4f' % (p5[(1, 2)], p5[(2, 2)]))
check('a fixed 0.10 GB/s gate would fail there (design line 125)', p5[(1, 2)] >= 0.10 and p5[(2, 2)] >= 0.10)
ap = [x['limit2'] for x in D['asm_pooled']]
check('assembly read at 8 MiB, B4 and C1 together: two-spread limit 0.335 to 2.840 GB/s', near(min(ap), 0.335, 0.0005) and near(max(ap), 2.840, 0.0005), '%.4f to %.4f' % (min(ap), max(ap)))
check('about 100 block values per source, CPU and session', all(r['n_values'] == 100 for r in fr if r['source'] in ('B4', 'C1')))
Ur = {u['use']: u for u in D['uses']}
check('forecast for P3G (it includes assembly read at 8 MiB): precision insufficient', Ur['P3G']['forecast'] == 'precision insufficient' and min(ap) >= Ur['P3G']['margin'])
check('P3G names the rate without saved data', 'new read at 8 MiB' in Ur['P3G']['missing'])
check('P3G says what is missing: a process with four repeats of new read (the original run has 3 repetitions)', 'four repeats' in Ur['P3G']['missing'] and 'no saved one-thread interval' not in Ur['P3G']['missing'])
check('every use has a forecast word', all(u['forecast'] in ('feasible', 'precision insufficient', s.ID) for u in D['uses']) and len(D['uses']) == 13)
check('S3G on the saved data: twice L0 rounds to 0.35 GB/s and is clipped to the one-rate bound 0.30 GB/s', near(Ur['S3G']['twice_rounded'], 0.35, 1e-9) and near(Ur['S3G']['margin'], 0.30, 1e-9) and Ur['S3G']['clipped'])
check('permitted margin ranges (design lines 185 to 187): 0.10 to 0.30 GB/s, and 0.20 to 0.60 GB/s for the four-rate interaction',
      all((u['lower'], u['upper']) == ((0.20, 0.60) if u['quantity'] == 'four-rate interaction' else (0.10, 0.30)) for u in D['uses']) and Ur['CM interaction']['quantity'] == 'four-rate interaction')
check('uses without a forecast: CM one rate, CM interaction, and the BIN and CS selections without saved repeats',
      D['stop']['missing'] == ['BIN other selections', 'CS other selections', 'CM one rate', 'CM interaction'], str(D['stop']['missing']))

p1 = [x for x in D['p1'] if x['cpu'] in (2, 41)]
lo, hi = min(x['diff_min'] for x in p1), max(x['diff_max'] for x in p1)
check('P1 emulation, single differences: -0.139 to -0.054 GB/s', near(lo, -0.139, 0.0005) and near(hi, -0.054, 0.0005), '%.4f to %.4f' % (lo, hi))
w = [x['worst'] for x in p1]
check('P1 emulation, largest difference plus limit: 0.162 to 0.222 GB/s', near(min(w), 0.162, 0.0005) and near(max(w), 0.222, 0.0005), '%.4f to %.4f' % (min(w), max(w)))

# B1 reference medians. The design quotes them from the rate column that the file rounds to 2 decimals.
# This page uses bytes / elapsed time of the T rows. The two agree within 0.005 GB/s.
b1 = D['b1']['processes']
q = lambda size, cpus: [x['median'] for x in b1 if x['size'] == size and x['cpu'] in cpus]
for name, size, cpus, a, b in (('8 MiB, CPUs 41 and 94', '8M', (41, 94), 70.070, 70.460), ('8 MiB, CPUs 0 and 2', '8M', (0, 2), 67.880, 68.755),
                               ('4 MiB', '4M', (0, 2, 41, 94), 73.075, 75.735), ('16 MiB', '16M', (0, 2, 41, 94), 64.830, 66.255)):
    v = q(size, cpus)
    check('B1 process medians, %s: %.3f to %.3f GB/s within 0.005' % (name, a, b), near(min(v), a, 0.005) and near(max(v), b, 0.005), '%.3f to %.3f from T rows' % (min(v), max(v)))


def irow_medians(size, cpus):
    out = []
    for ses in (1, 2):
        cur = None
        for line in open(s.csv_path('B1', ses)):
            if line.startswith('-- step'):
                keep = ('--bytes %s ' % size) in line and int(re.search(r'--cpus (\d+)', line).group(1)) in cpus
                cur = [] if keep else None
                if keep:
                    out.append(cur)
            elif line.startswith('I,') and cur is not None and line.split(',')[3] == 'asmread':
                cur.append(float(line.split(',')[8]))
    return [median(x) for x in out]


v = irow_medians('8M', (41, 94))
check('the rounded rate column gives exactly the 70.070 to 70.460 of the design', near(min(v), 70.070, 1e-9) and near(max(v), 70.460, 1e-9), '%.3f to %.3f' % (min(v), max(v)))
check('B1 processes hold two buffers', all(x['buffers'] == 2 for x in b1))

hi3 = [x for x in D['cread_8m'] if x['asm_minus_old'] > 2.0]
check('06:05 run: three processes pair old read near 67 with assembly read near 71 GB/s',
      len(hi3) == 3 and all(near(x['old'], 67.0, 0.2) and near(x['asm'], 71.0, 0.2) for x in hi3), ', '.join('%.2f/%.2f' % (x['old'], x['asm']) for x in hi3))
check('cache sizes are found in the hardware report', all(c['found'] for c in D['caches']) and [c['bytes'] for c in D['caches']] == [65536, 2 << 20, 128 << 20])
check('1 MiB fits L2 and 8 MiB does not', s.level_of(1 << 20, D['caches']) == 'fits L2' and s.level_of(8 << 20, D['caches']) == 'fits SLC')

check('B6 positions: 13 x 3 CPUs x 2 sessions, 32 intervals each, position 5 included', len(D['b6']['positions']) == 78 and all(x['n'] == 32 for x in D['b6']['positions']))
check('every B6 process carries its own reference rate', len(D['b6']['processes']) == 48 and all(len(p['refs']) == 20 for p in D['b6']['processes']))
check('reference traces keep every process', len(D['b4']) == 16 and len(D['c1']) == 8 and all(p['n'] == 200 for p in D['b4'] + D['c1']))
check('C1 has no interval above 70.5 GB/s, B4 with huge pages has some', sum(p['above_high'] for p in D['c1']) == 0 and sum(p['above_high'] for p in D['b4'] if p['thp']) > 0)

code = {(r['bwx_function'], r['reference']): r for r in D['code']}
check('old read: bwx equals bw_old k_read, loop offset 40', code[('k_oldread', 'bw_old k_read')]['sequence_equal'] and code[('k_oldread', 'bw_old k_read')]['bwx_loop_mod64'] == 40
      and code[('k_oldread', 'bw_old k_read')]['ref_loop_mod64'] == 40)
check('new read: bwx equals bw_new k_read, loop offset 36', code[('k_read', 'bw_new k_read')]['sequence_equal'] and code[('k_read', 'bw_new k_read')]['bwx_loop_mod64'] == 36
      and code[('k_read', 'bw_new k_read')]['ref_loop_mod64'] == 36)
check('assembly read: bwx equals bw_new k_asmread, loop offset 20', code[('k_asmread', 'bw_new k_asmread')]['sequence_equal'] and code[('k_asmread', 'bw_new k_asmread')]['ref_loop_mod64'] == 20)
check('assembly read of bw_old has another loop offset (28) and the page says so', code[('k_asmread', 'bw_old k_asmread')]['ref_loop_mod64'] == 28)
check('the saved offsets file agrees with the listing', all(r['offsets_tsv_agrees'] for r in D['code']))
check('every listed operation is found in its source file', all(o['line'] for o in D['operations']), str([o['what'] for o in D['operations'] if not o['line']]))
ops = {o['what'][:24]: o['line'] for o in D['operations']}
check('the warm-up pass lies before the timed interval in worker()', ops['One untimed pass of the '] < ops['Clock read. The timed in'])
g = {x['pos']: x for x in D['gaps']}
check('measured gap before an 8 MiB entry is longer than one pass of it (est.)', all(x['median_ms'] > x['pass_ms_est'] for x in D['gaps']))
check('gap before a 1 MiB entry is shorter than before an 8 MiB entry', g[2]['median_ms'] < g[1]['median_ms'])

check('system load is recorded for every source run', len(D['load']) == 10 and all(x['n'] > 0 for x in D['load']))
check('stop decision: evidence complete, sources consistent, candidate not contradicted, so proceed', D['stop']['complete'] and D['stop']['consistent']
      and D['stop']['candidate']['not_contradicted'] and D['stop']['proceed'])
PROCEED, RECONCILE, CONTRA = 'the work proceeds through runner acceptance', 'stop for reconciliation before a machine run', 'contradicts a part of the candidate'


def stop_text(change):
    """Section 10 of the page after one change of the computed facts."""
    D2 = copy.deepcopy(D)
    change(D2)
    D2['stop'] = s.stop_decision(D2)
    return D2['stop'], re.sub(r'<[^>]+>', ' ', ''.join(s.sec_stop(D2)))


S0, txt = stop_text(lambda d: None)
check('stop decision: the unchanged facts print "proceeds" and no stop sentence', PROCEED in txt and RECONCILE not in txt and CONTRA not in txt)


def ch_table(d):
    d['item1']['best'][2]['new'] = 70.0
    d['item1']['best'][2]['gain_pct'] = 4.35


def ch_gain(d):
    p = [x for x in d['item1']['pairs'] if x['size'] == '8M'][0]
    p['gain_pct'] = 3.0


def ch_kernel(d):
    d['item1']['one_kernel_per_process'] = False


def ch_offset(d):
    r = [x for x in d['code'] if x['reference'] == 'bw_new k_read'][0]
    r['ref_loop_mod64'] = 44


def ch_instr(d):
    r = [x for x in d['code'] if x['reference'] == 'bw_old k_read'][0]
    r['sequence_equal'] = False


def ch_line(d):
    d['operations'][3]['line'] = None


for name, change, flag in (('a changed size table', ch_table, 'table_reproduced'), ('a changed median gain at 8 MiB', ch_gain, 'median_gains_reproduced'),
                           ('a process with more than one kernel', ch_kernel, 'one_kernel_per_process'), ('a primary loop with another offset', ch_offset, 'loops_equal_to_original'),
                           ('a primary loop with another instruction', ch_instr, 'loops_equal_to_original'), ('a missing source line', ch_line, 'complete')):
    S2, txt = stop_text(change)
    check('stop decision: %s clears "%s", and the page says stop for reconciliation, not proceed' % (name, flag),
          not S2[flag] and not S2['proceed'] and not (S2['complete'] and S2['consistent']) and RECONCILE in txt and PROCEED not in txt)


def ch_old(d):
    for x in d['item1']['pairs']:
        if x['size'] == '8M' and x['cpu'] == 2 and x['round'] == 1:
            x['old'] -= 0.5


def ch_new(d):
    for x in d['item1']['pairs']:
        if x['size'] == '8M' and x['cpu'] == 0 and x['round'] == 2:
            x['new'] = 86.0


def ch_asm(d):
    a = [x for x in d['orig_asm'] if x['size'] == '8M'][0]
    a['median'] = 86.0


for name, change, flag in (('old read 0.5 GB/s lower at 8 MiB in one pair', ch_old, 'old_nearly_constant'), ('new read higher at 8 MiB than at 1 MiB in one pair', ch_new, 'new_lower_at_8m'),
                           ('assembly read higher at 8 MiB than at 1 MiB in one pair', ch_asm, 'asm_lower_at_8m')):
    S2, txt = stop_text(change)
    check('stop decision, candidate: %s clears "%s", and the page does not say proceed' % (name, flag),
          not S2['candidate'][flag] and not S2['candidate']['not_contradicted'] and not S2['proceed'] and CONTRA in txt and PROCEED not in txt)
K = D['stop']['candidate']
check('candidate facts of the original run: old read 8 MiB minus 1 MiB is -0.12 to -0.05 GB/s in 4 pairs', len(K['old_diff']) == 4 and near(min(K['old_diff']), -0.12, 0.0051) and near(max(K['old_diff']), -0.05, 0.0051),
      ', '.join('%.2f' % x for x in K['old_diff']))
check('candidate facts of the original run: new read 8 MiB minus 1 MiB is -17.88 to -17.60 GB/s in 4 pairs', len(K['new_diff']) == 4 and near(min(K['new_diff']), -17.88, 0.0051) and near(max(K['new_diff']), -17.60, 0.0051),
      ', '.join('%.2f' % x for x in K['new_diff']))
check('candidate facts of the original run: 8 pairs of assembly read, all lower at 8 MiB', len(K['asm_diff']) == 8 and max(K['asm_diff']) < 0)
orig2 = s.parse_bandwidth_csv(s.SRC['orig'], True)
check('one kernel per process: true for the saved file', s.item1(orig2)['one_kernel_per_process'])
[p for p in orig2 if p['kernel'] == 'read'][0]['reps'][1]['kernel'] = 'write'
check('one kernel per process: a repetition of another kernel inside a read process is seen', not s.item1(orig2)['one_kernel_per_process'])
check('loop comparison: 4 of 4 with the binaries of the size comparison, and assembly read of bw_old is outside the count', D['stop']['loops_compared'] == 4 and D['stop']['loops_equal'] == 4
      and [r['reference'] for r in D['code'] if not r['primary']] == ['bw_old k_asmread'])

# ---------------------------------------------------------------- 3. the page and the JSON file

with tempfile.TemporaryDirectory(dir=SCRATCH) as d:
    page_path, json_path = os.path.join(d, 'p.html'), os.path.join(d, 'p.json')
    s.main(['-o', page_path, '--json', json_path])
    page = open(page_path).read()
    J = json.load(open(json_path))
body = page[page.index('<body>'):]
plain = re.sub(r'<[^>]+>', ' ', body)
check('page: starts with "Short version"', re.search(r'<h1>[^<]*</h1>\s*<p><b>Short version\.</b>', body) is not None)
sv = re.sub(r'<[^>]+>', '', re.search(r'<p><b>Short version\.</b>(.*?)</p>', body, re.S).group(1))
n_sent = len(re.findall(r'[.:](?:\s|$)', re.sub(r'est\. ', 'est ', sv.strip()))) - sv.count(': ')
check('page: the short version has at most three sentences', 1 <= n_sent <= 3, '%d' % n_sent)
check('page: "Words used here" follows the short version', body.index('Words used here') < body.index('What this page is') and body.index('Short version') < body.index('Words used here'))
check('page: says that it establishes no causal history effect', 'does not establish a causal history effect' in plain)
check('page: every limit of item 8 is labelled est. for the new trial wrapper', plain.count('est. for the new trial wrapper') >= 3)
check('page: light background only', 'color-scheme:light' in page and 'prefers-color-scheme' not in page and 'background:#ffffff' in page)
check('page: self-contained', '<script' not in page and 'http://' not in page and 'https://' not in page and '<link' not in page and '<img' not in page)
check('page: charts are inline SVG', page.count('<svg') >= 9)
check('page: 69 and 70.5 GB/s appear as annotation lines', 'stroke-dasharray' in page and 'annotation' in plain)
cited = set(re.findall(r'\[Ref(\d+)\]', body[:body.index('<h2>References')]))
listed = set(re.findall(r'<li>\[Ref(\d+)\]', body))
check('page: every cited reference is in the reference list', cited and cited <= listed, 'cited %s' % sorted(cited - listed))
check('page: file paths only in the reference list', '/home/' not in body[:body.index('<h2>References')])
check('page: the stop decision is the last section before the references', body.index('Stage 0 stop decision') > body.index('System load of each source run'))
check('page: the Insufficient data label names its measurement', 'Insufficient data' in plain and 'The measurement that resolves it' in plain)
check('page: the NEW runner comparison is named as later work on CRB', 'compared again after it is linked on CRB' in plain)
check('page: the short version numbers are the computed numbers', '0.94 %' in sv and '192 of 192' in sv and '0.335 to 2.840 GB/s' in sv)
sec10 = plain[plain.index('10. Stage 0 stop decision'):plain.index('References', plain.index('10. Stage 0 stop decision'))]
check('page, section 10: the proceed sentence names the candidate, and the candidate rows are in the table',
      'The original run does not contradict the candidate' in sec10 and PROCEED in sec10 and 'Old read at 8 MiB minus old read at 1 MiB' in sec10 and 'New read is lower at 8 MiB' in sec10)
check('page, section 10: the loop row gives its count and names the comparison that is not equal', '4 of 4 comparisons' in sec10 and 'assembly read of  bw_old  has loop offset 28 bytes' in sec10
      and 'equal the loops of the original binaries' not in sec10)
check('page, section 10: the list of uses without a forecast holds the BIN and CS selections', 'BIN other selections, CS other selections, CM one rate, CM interaction' in sec10)
urow = lambda use: re.sub(r'<[^>]+>', ' ', re.search(r'<tr><td class="l">%s</td>.*?</tr>' % re.escape(use), body, re.S).group(0))
check('page: the P3G row says that P3G and the P3 branch are not scheduled by default', 'No. Not scheduled by default. So the P3 branch is not scheduled by default either.' in urow('P3G'))
check('page: every use with the forecast "precision insufficient" says "Not scheduled by default"', all(
    'No. Not scheduled by default.' in urow(u['use']) for u in D['uses'] if u['forecast'] == 'precision insufficient'))
check('page: the BIN and CS rows of the other selections name new read and say Insufficient data', all(
    'Insufficient data' in urow(x) and 'new read at 32 KiB, 1 MiB, 4 MiB, 8 MiB, 16 MiB' in urow(x) and 'Not scheduled until' in urow(x) for x in ('BIN other selections', 'CS other selections')))
check('page: no cell says that no one-thread interval of new read is saved', 'no saved one-thread interval' not in plain)
check('page: the three limit column heads carry "est."', all('<th>%s-spread limit, GB/s est.</th>' % w in body for w in ('Two', 'Four', 'Eight')))
check('page: all B1 sizes are plotted, one line per process (16 B4 + 8 C1 + 48 B6 + 128 B1 lines)', all(
    '<h3>B1 at %s: the 20 reference intervals of each process' % z in body for z in ('4 MiB', '8 MiB', '16 MiB', '32 MiB')) and body.count('<polyline') == 200, '%d lines' % body.count('<polyline'))
check('page: charts of B1 at 4, 16 and 32 MiB are present', page.count('<svg') >= 12)
words = body[body.index('Words used here'):body.index('What this page is')]
check('page: the terms of sections 2, 6 and 8 are in "Words used here"', all(w in words for w in (
    'T row, P row, I row, C row', 'Interval wrapper', 'Trial wrapper', 'Window-only records', 'Step S2, step S3', 'P3 branch', 'Trigger of Stage 3')))
sec9 = body[body.index('9. System load of each source run'):body.index('10. Stage 0 stop decision')]
check('page: the load section cites its sources', all('[Ref%d]' % n in sec9 for n in (1, 5, 10, 11, 12, 17, 18)))
check('page: every listed reference is cited in the body', listed <= cited and '14' in cited, 'not cited %s' % sorted(listed - cited))
check('page: the rate and offset column heads carry units', all(h in body for h in (
    '<th>Lowest, GB/s</th>', '<th>Highest, GB/s</th>', '<th>Intervals below 69 GB/s</th>', '<th>Intervals at 69 to 70.5 GB/s</th>', '<th>Intervals above 70.5 GB/s</th>', '<th>Loop offset modulo 64, bytes</th>'))
      and '<th>Lowest</th>' not in body and '<th>Below 69</th>' not in body)
lines = [100.0, 60.0]
check('label_y: a label above its dots moves below when a dashed line would cross it', s.label_y(104.0, 150.0, False, lines) == 150.0)
check('label_y: a label that no line crosses stays where it is preferred', s.label_y(80.0, 150.0, False, lines) == 80.0 and s.label_y(80.0, 150.0, True, lines) == 150.0)
check('label_y: a label below its dots moves above when a dashed line would cross it', s.label_y(80.0, 62.0, True, lines) == 80.0)
check('json: holds the tables of all eight items', all(k in J for k in ('item1', 'pair_summary', 'b4', 'c1', 'operations', 'code', 'cread', 'b1', 'b6', 'feasibility', 'uses', 'p1', 'stop', 'load')))
check('json: same numbers as the computation', near(J['item1']['best'][2]['gain_pct'], D['item1']['best'][2]['gain_pct'], 1e-12) and J['pairs_by_session']['1']['first_slower'] == 192)

print('%d checks failed' % len(FAILED) if FAILED else 'all checks passed')
sys.exit(1 if FAILED else 0)
