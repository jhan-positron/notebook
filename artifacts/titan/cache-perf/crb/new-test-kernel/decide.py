#!/usr/bin/env python3
"""decide.py - the decision rules of handoff.md section B.10, as code, with synthetic tests.

Words: a "process value" is one number per process (never one per interval). d is the process value
of a kernel difference, e is the process value of the A/A difference of the same process.
Every one-thread decision is made per CPU. Processes of different CPUs are never pooled.
Run "python3 decide.py" to execute the synthetic tests.
"""
from statistics import median

LOW_MAX, HIGH_MIN = 69.0, 70.5          # GB/s, provisional limits of the two levels at 8 MiB (plan, rule 5)

def level(rate):
    return 'low' if rate < LOW_MAX else 'high' if rate > HIGH_MIN else 'changing'

def process_value(ref_rates, kernel_pairs, aa_pairs, labelled=True):
    """One process -> (label, d, e), or None if the process gives no value.
    ref_rates: rates of all reference intervals of the process. kernel_pairs, aa_pairs: pair values.
    labelled=True (8 MiB): only a process whose references are all low or all high gives a value (plan, rule 4).
    labelled=False (4, 16, 32 MiB): no level is defined; every process gives a value with the label 'none'."""
    if not kernel_pairs or not aa_pairs:
        return None
    if labelled:
        labels = {level(r) for r in ref_rates}
        if len(labels) != 1 or labels == {'changing'}:
            return None
        label = labels.pop()
    else:
        label = 'none'
    return label, median(kernel_pairs), median(aa_pairs)

def resolved(d, e, min_n):
    """d, e: process values of one group (same session, size, CPU, label).
    -> ('not observed', None) with fewer than min_n processes; else ('resolved', sign) or ('not resolved', None).
    Resolved: |median d| larger than the A/A spread (largest |e|), and all d have one sign."""
    if len(d) < min_n or len(e) < min_n:
        return 'not observed', None
    spread = max(abs(x) for x in e)
    m = median(d)
    one_sign = all(x > 0 for x in d) or all(x < 0 for x in d)
    if abs(m) > spread and one_sign:
        return 'resolved', (1 if m > 0 else -1)
    return 'not resolved', None

def decide_one_thread(procs, min_n=3):
    """procs: list of dicts {cpu, label, d, e}, one per process, for one session and size.
    -> {label: (word, sign, per_cpu)}. A label is 'resolved' only if at least 2 CPUs have enough processes,
    every such CPU is resolved, and all have the same sign."""
    out = {}
    for label in sorted({p['label'] for p in procs}):
        per_cpu = {}
        for cpu in sorted({p['cpu'] for p in procs}):
            g = [p for p in procs if p['cpu'] == cpu and p['label'] == label]
            per_cpu[cpu] = resolved([p['d'] for p in g], [p['e'] for p in g], min_n)
        seen = [v for v in per_cpu.values() if v[0] != 'not observed']
        if len(seen) < 2:
            out[label] = ('not observed', None, per_cpu)
        elif all(v[0] == 'resolved' for v in seen) and len({v[1] for v in seen}) == 1:
            out[label] = ('resolved', seen[0][1], per_cpu)
        else:
            out[label] = ('not resolved', None, per_cpu)
    return out

def decide_b6_state(procs, min_n=2):
    """B6, first comparison: old read at 8 MiB in stable-low processes against stable-high processes ON THE SAME CPU.
    procs: list of dicts {cpu, label, rate (process median of oldread at 8 MiB), e (oldread2 - oldread)}.
    -> {cpu: (word, difference)}. A CPU without min_n processes of each label is 'not observed'."""
    out = {}
    for cpu in sorted({p['cpu'] for p in procs}):
        g = [p for p in procs if p['cpu'] == cpu]
        lo = [p['rate'] for p in g if p['label'] == 'low']; hi = [p['rate'] for p in g if p['label'] == 'high']
        if len(lo) < min_n or len(hi) < min_n:
            out[cpu] = ('not observed', None); continue
        spread = max(abs(p['e']) for p in g)
        diff = median(lo) - median(hi)
        separate = max(lo) < min(hi) or min(lo) > max(hi)
        out[cpu] = ('resolved' if abs(diff) > spread and separate else 'not resolved', diff)
    return out

def decide_setting(procs, min_n=4):
    """B7 or B10, one setting: procs = list of dicts {D, E}, ONE per process (the mean over the rounds of the process)."""
    return resolved([p['D'] for p in procs], [p['E'] for p in procs], min_n)

def decide_change(procs_x, procs_y, min_n=4):
    """Change of D between two settings that differ in one factor. -> (word, change)."""
    if len(procs_x) < min_n or len(procs_y) < min_n:
        return 'not observed', None
    dx = [p['D'] for p in procs_x]; dy = [p['D'] for p in procs_y]
    change = median(dx) - median(dy)
    spread = max(abs(p['E']) for p in procs_x) + max(abs(p['E']) for p in procs_y)
    separate = max(dx) < min(dy) or min(dx) > max(dy)
    return ('resolved' if abs(change) > spread and separate else 'not resolved'), change

def controls_from_aa(aa_intervals):
    """Controls of one setting from its A/A intervals.
    aa_intervals: list of (a, a2) for neighbouring intervals of the A/A pair in one process;
    a and a2 are (rate of mesh 0, rate of mesh 1) of the original and of its copy.
    -> (control of the total rate, (control of mesh 0, control of mesh 1)): largest absolute A/A differences."""
    tot = max(abs(sum(a2) - sum(a)) for a, a2 in aa_intervals)
    mesh = tuple(max(abs(a2[m] - a[m]) for a, a2 in aa_intervals) for m in (0, 1))
    return tot, mesh

def decide_h11(procs, ctrl_total, ctrl_mesh, min_n=2):
    """H11: in an interval with a higher total, one mesh is faster and the other is not.
    procs: one dict per process: {hi: (mesh0, mesh1), lo: (mesh0, mesh1)} = per-mesh rates of the interval with
    the highest and with the lowest total of one kernel in that process.
    A process counts only if its total differs by more than the control of the total rate.
    Each mesh is judged with the control of ITS OWN rate, never with a control of a total or of a range.
    Supported: in every counted process exactly one mesh changed by more than its control, that change is
    positive (the mesh got faster), and it is the same mesh in all processes.
    -> 'supported', 'contradicted', 'not resolved' or 'not observed'."""
    kinds = []
    for p in procs:
        if sum(p['hi']) - sum(p['lo']) <= ctrl_total:
            continue
        delta = [p['hi'][m] - p['lo'][m] for m in (0, 1)]
        moved = [abs(delta[m]) > ctrl_mesh[m] for m in (0, 1)]
        if moved[0] != moved[1]:
            m = 0 if moved[0] else 1
            # H11 says that one mesh runs FASTER: a mesh that only got slower is not support.
            kinds.append(('one', m) if delta[m] > 0 else ('other', None))
        elif moved[0] and moved[1] and (delta[0] > 0) == (delta[1] > 0):
            kinds.append(('both', None))
        else:
            kinds.append(('other', None))
    if len(kinds) < min_n:
        return 'not observed'
    if all(k[0] == 'one' for k in kinds) and len({k[1] for k in kinds}) == 1:
        return 'supported'
    if all(k[0] == 'both' for k in kinds):
        return 'contradicted'
    return 'not resolved'

def _tests():
    # 1. A negative difference can be resolved (rule 3 of the plan uses the absolute value).
    assert resolved([-2.0, -2.2, -1.7], [0.3, -0.2, 0.1], 3) == ('resolved', -1)
    assert resolved([-2.0, -2.2, +1.7], [0.3, -0.2, 0.1], 3)[0] == 'not resolved'      # signs differ
    assert resolved([-0.2, -0.25, -0.1], [0.3, -0.2, 0.1], 3)[0] == 'not resolved'     # inside the A/A spread
    assert resolved([-2.0, -2.2], [0.3, -0.2], 3)[0] == 'not observed'                 # too few processes

    # 2. A difference between CPUs must not become a difference between levels.
    #    CPU 2 is always low with old read at 67.0; CPU 41 is always high with old read at 68.0.
    procs = [dict(cpu=2, label='low', rate=67.0 + i * 0.01, e=0.02) for i in range(4)] + \
            [dict(cpu=41, label='high', rate=68.0 + i * 0.01, e=0.02) for i in range(4)]
    r = decide_b6_state(procs)
    assert r[2][0] == 'not observed' and r[41][0] == 'not observed', r
    #    Pooled over the CPUs the same data would look like a resolved level effect of -1.0 GB/s:
    pooled = median(p['rate'] for p in procs if p['label'] == 'low') - median(p['rate'] for p in procs if p['label'] == 'high')
    assert abs(pooled + 1.0) < 0.02
    #    With both levels on one CPU and equal rates, the result is 'not resolved'.
    procs = [dict(cpu=2, label=l, rate=67.0 + i * 0.01, e=0.05) for l in ('low', 'high') for i in range(3)]
    assert decide_b6_state(procs)[2][0] == 'not resolved'

    # 3. One process with many intervals counts once.
    small = [process_value([67.5] * 5, [0.1] * 4, [0.02] * 4) for _ in range(3)]
    big = process_value([67.5] * 101, [-5.0] * 100, [0.02] * 100)
    procs = [dict(cpu=2, label=v[0], d=v[1], e=v[2]) for v in small + [big]] + \
            [dict(cpu=41, label=v[0], d=v[1], e=v[2]) for v in small + [big]]
    assert decide_one_thread(procs)['low'][0] == 'not resolved'       # 3 processes say +0.1, one says -5
    all_pairs = [0.1] * 12 + [-5.0] * 100
    assert median(all_pairs) == -5.0                                  # pooling the intervals would say -5

    # 4. A process whose references change level gives no value at 8 MiB, and gives one at an unlabelled size.
    assert process_value([67.5, 71.0, 67.6], [0.1] * 4, [0.0] * 4) is None
    assert process_value([67.5, 69.8, 67.6], [0.1] * 4, [0.0] * 4) is None
    assert process_value([55.0, 58.0, 61.0], [0.1] * 4, [0.0] * 4, labelled=False)[0] == 'none'

    # 5. One-thread decision needs the same sign on at least 2 CPUs with enough processes.
    mk = lambda cpu, d: [dict(cpu=cpu, label='low', d=d + i * 0.01, e=0.1) for i in range(4)]
    assert decide_one_thread(mk(0, -2.0) + mk(2, -2.1))['low'][:2] == ('resolved', -1)
    assert decide_one_thread(mk(0, -2.0) + mk(2, +2.1))['low'][0] == 'not resolved'
    assert decide_one_thread(mk(0, -2.0))['low'][0] == 'not observed'

    # 6. Settings: one value per process; a change needs separate ranges.
    x = [dict(D=160 + i, E=5) for i in range(4)]; y = [dict(D=20 + i, E=6) for i in range(4)]
    assert decide_setting(x) == ('resolved', 1) and decide_change(x, y)[0] == 'resolved'
    assert decide_change(x, [dict(D=155 + i, E=6) for i in range(4)])[0] == 'not resolved'
    assert decide_setting(x[:3])[0] == 'not observed'
    # 7. H11 uses a control per mesh. A/A intervals with equal totals and opposite mesh rates:
    aa = [((50.0, 50.0), (55.0, 45.0)), ((55.0, 45.0), (50.0, 50.0))]
    ctrl_total, ctrl_mesh = controls_from_aa(aa)
    assert ctrl_total == 0.0 and ctrl_mesh == (5.0, 5.0)
    #    A change of (0.1, 0) GB/s is far inside the per-mesh control: it must not support H11.
    tiny = [dict(hi=(50.1, 50.0), lo=(50.0, 50.0)) for _ in range(3)]
    assert decide_h11(tiny, ctrl_total, ctrl_mesh) == 'not resolved'
    #    Constant totals with opposing mesh changes: no interval has a higher total, so nothing is observed.
    opposing = [dict(hi=(55.0, 45.0), lo=(50.0, 50.0)) for _ in range(3)]
    assert decide_h11(opposing, ctrl_total, ctrl_mesh) == 'not observed'
    #    One mesh rises by more than its control, the other does not: supported. Both rise: contradicted.
    assert decide_h11([dict(hi=(50.0, 80.0), lo=(50.0, 50.0))] * 2, 1.0, (5.0, 5.0)) == 'supported'
    assert decide_h11([dict(hi=(70.0, 80.0), lo=(50.0, 50.0))] * 2, 1.0, (5.0, 5.0)) == 'contradicted'
    assert decide_h11([dict(hi=(50.0, 80.0), lo=(50.0, 50.0)), dict(hi=(80.0, 50.0), lo=(50.0, 50.0))], 1.0, (5.0, 5.0)) == 'not resolved'
    #    The only mesh above its control got SLOWER (50 -> 48) while the total rose: not support for H11.
    slower = [dict(hi=(48.0, 53.0), lo=(50.0, 50.0)) for _ in range(2)]
    assert decide_h11(slower, 0.0, (1.0, 10.0)) == 'not resolved'
    print('decide.py: all synthetic tests passed')

if __name__ == '__main__':
    _tests()
