"""dyn_notes.py: the text blocks of ASCT-cross-check.html that were written after the runs.
fill() is called by notes.py. Every number comes from FACTS (facts.json) or BASELINE (baseline.json)."""
import re

MI = 1 << 20
M1, M8 = str(MI), str(8 * MI)


def env_fact(env, pattern, default='not recorded'):
    m = re.search(pattern, env, re.M)
    return m.group(1).strip() if m else default


def static_blocks(N, F, B, p, ul, ref):
    env = F['prep']['env']
    thp = env_fact(env, r'^thp enabled (.*?) defrag')
    thp_on = re.search(r'\[(\w+)\]', thp).group(1)
    vend_thp = sorted({v['thp'] for v in B['vendor'].values()})

    N['how'] = [
        p('The ASCT front end (the command <code>asct run</code>) could not be used on CRB as it is. There are four reasons.'),
        ul(f'<b>Fixed core.</b> The ASCT benchmark <code>bandwidth-sweep</code> takes its one core from the code: the last CPU of NUMA node 0. '
           f'On CRB that is CPU 127 {ref(4)}. CPU 127 is isolated and must not be used {ref(13)}.',
           f'<b>All CPUs.</b> The ASCT benchmark <code>peak-bandwidth</code> uses every CPU of the node. On CRB that includes CPUs 120 to 127. '
           f'Our runs may use CPUs 0 to 119 only {ref(4, 13)}.',
           f'<b>Huge pages.</b> Both benchmarks first run the ASCT benchmark <code>latency-sweep</code>, which needs huge pages. CRB has 0 free huge pages. '
           f'Adding huge pages needs root and changes a system setting {ref(7, 10)}.',
           f'<b>One user setting.</b> <code>bandwidth-sweep</code> has one user setting, <code>cycle_base</code>. It has no setting for the core or for the buffer sizes {ref(4)}.'),
        p(f'So each run started the ASCT benchmark binary directly. The command line is the one that the front end builds {ref(4)}:'),
        '<pre>numactl --membind 0 loaded-latency-asct-sve.bin --duration D --delay-seconds 0 \\\n'
        '    --bw-cpu C [--bw-cpu C ...] --bw-buflen BYTES --bw-fine-delay N --bw-write=0 --bw-cacheline-bytes 64</pre>',
        ul('<b>D</b> is the length of the measured phase in seconds. The ASCT default is 0.25 s.',
           '<b>C</b> is a CPU. One thread runs on each CPU that the command line names.',
           '<b>BYTES</b> is the buffer size of each thread.',
           '<b>N</b> is the number of injected NOPs.'),
        p('What is the same as in a run through the front end, and what is not:'),
        ul(f'<b>Same binary.</b> Runs without counters used the binary that the ASCT installer built on CRB {ref(10)}.',
           f'<b>Same loop in the counted runs.</b> Runs with counters used the probe build. It was built on CRB from the ASCT source archive, '
           f'with the compiler flags of the ASCT configuration file {ref(6, 9)}. {N["_loop_same"]}',
           '<b>Timing.</b> One-core runs used the ASCT default of 0.25 s. Whole-chip runs used 2 s. Three whole-chip processes used 0.25 s as a check.',
           f'<b>Pages.</b> The ASCT bandwidth code allocates its buffer with <code>posix_memalign</code> and does not ask for huge pages {ref(5)}. '
           f'The CRB kernel setting for transparent huge pages is "{thp_on}". A 64 MiB test buffer on CRB was backed by 2 MiB pages for all of its 64 MiB {ref(10)}. '
           f'The Arm reference machines record the setting "{", ".join(vend_thp)}" {ref(11)}. '
           'So their buffers used 4 KiB pages (est. from the setting, not measured).',
           '<b>Different by design.</b> The CPUs, the buffer sizes and the thread layout are ours, not those of the front end.'),
    ]

    lp = {r[0]: r for r in B['chip']['loops']}
    N['loops'] = [
        ul(f'<b>Old read.</b> It loads all 64 bytes of a line with 2 pair-load instructions (<code>ldp q</code>, 32 bytes each). '
           f'Then it adds the loaded values with 4 vector add instructions {ref(3)}.',
           f'<b>New read.</b> It loads all 64 bytes of a line with 2 <code>ldp q</code> instructions. It does no other work {ref(3)}.',
           f'<b>ASCT read.</b> It loads the first 8 bytes of a line with 1 load instruction (<code>ldr x</code>). It does no other work. '
           f'One loop round covers 8 lines and has 3 more instructions for the loop itself {ref(5)}. {N["_loop_inst"]}',
           f'<b>ASCT read with N injected NOPs.</b> ASCT then uses the function <code>my_read</code>. It loads 8 bytes of a line and then runs an empty loop of N rounds {ref(5)}.',
           '<b>All three count 64 bytes per line.</b> So a rate in this report is a rate of lines: 64 GB/s is 1.0 &times; 10<sup>9</sup> lines per second for each loop.'),
        p('The machine code of the ASCT read loop on CRB, from the installed binary (8 loads, then 3 loop instructions):'),
        N['_loop_listing'],
        p(f'The window of a loop matters for question 2. The work of 2026-11-15 estimated how many lines one window covers: '
          f'{lp["old read"][2].replace("-", " to ")} lines for the old read loop and {lp["new read (asmread)"][2].replace("-", " to ")} lines for the new read loop {ref(3)}. '
          'The ASCT read loop has fewer instructions per line than both. So its window covers more lines than that of the new read loop (est., not measured for this loop).'),
    ]

    paranoid = env_fact(env, r'^perf_event_paranoid (\d+)')
    sysreg_missing = 'No such file' in env_fact(env, r'^sysreg dir: (.*)$')
    nres = len(re.findall(r'^resolved', F['prep']['resolve'], re.M))
    N['capture'] = [
        p('The request asked for every counter and register that ASCT can capture. ASCT has four ways. One gave data without root. The other three need root or a kernel module, and they gave nothing in this work.'),
        ul(f'<b>Core counters: captured.</b> The probe build contains the ASCT capture code named dietperf. It reads a list of raw event codes from the '
           f'environment variable <code>DIETPERF_PMUv3</code> {ref(6)}. It counts in user mode. It counts only the measured phase of each thread. It needs no root. '
           f'This work counted {nres} events in 7 sets of 7 {ref(9)}. The sets include the 9 prefetch events that CRB lists for the data caches: '
           '4 for the hardware prefetchers and 5 for prefetch instructions. '
           'Not counted: 2 events for address-translation work caused by prefetch instructions, and the events of the instruction cache.',
           f'<b>The front-end switch for core counters: not used.</b> The switch <code>ASCT_DEBUG_ENABLE_PMU=1</code> selects a fixed list of events. '
           f'That list holds no prefetch event {ref(6)}. So the runs passed their own event codes to the capture code.',
           f'<b>Mesh counters: not captured.</b> The ASCT capture code has a setting for mesh counters (<code>DIETPERF_CMN</code>). '
           f'It opens them as system-wide events {ref(6)}. CRB allows system-wide events to root only (the kernel setting <code>perf_event_paranoid</code> is {paranoid}) {ref(10)}. '
           'So the benchmark itself would have to run as root. The plan was to read the same kernel counters with the Linux command <code>perf stat -a</code> as root, while the benchmark runs without root. '
           'That root command was refused by the permission system of this agent session.',
           '<b>Core registers: not captured.</b> The report <code>asct report sysreg</code> needs a kernel module that shows registers under <code>/sys/kernel/sysreg</code>. '
           + (f'CRB has no such folder {ref(10)}. ' if sysreg_missing else f'CRB has that folder {ref(10)}. ')
           + f'The ASCT source lists three core types for this report (Neoverse N1, N2 and V2). The core type of CRB is not in that list {ref(6)}.',
           f'<b>Mesh registers: not captured.</b> The report <code>asct report cmn</code> reads the mesh registers through <code>/dev/mem</code> as root {ref(6)}. '
           'Its option <code>--detect</code> also puts a load on every CPU in turn, which includes the isolated CPUs 126 and 127. '
           'No root command ran in this work. So this report was not run. '
           f'The layout of the mesh is known from the kernel record of 2026-11-02 {ref(14)}.'),
        p('<b>Insufficient data on the prefetcher settings.</b> No run of this work read a control register of a prefetcher. '
          'The measurement that would resolve it: the register report of ASCT after Arm supplies the kernel module with support for this core type, '
          'or a statement from Arm on the prefetcher settings of firmware v0.7.2.'),
    ]


# ---------------------------------------------------------------- helpers for the result blocks
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CRB = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
FINAL8 = os.path.join(CRB, 'new-test-kernel', 'tackle-8mb-analysis', 'final8.json')


def peer_counters():
    """Counted values of our own loops on 2026-11-15 (final8.json): step ZC at 8 MiB, step YC at 1 MiB."""
    J = json.load(open(FINAL8))
    out = {}
    for e in J['evict']['ZC']:
        if e['kernel'] == 'asmread' and e['size'] == '8M' and e['evict_mb'] == 0 and e['session'] == 1:
            out[f'new.8M.{e["cpu"]}'] = dict(e['per64'], rate=e['rate_median'])
    for e in J['prefetch']['YC']:
        if e['size'] == '1M' and e['session'] == 1 and e['kernel'] in ('asmread', 'oldread', 'read_1pl'):
            name = {'asmread': 'new', 'oldread': 'old', 'read_1pl': '1pl'}[e['kernel']]
            out[f'{name}.1M.{e["cpu"]}'] = dict(e['per64'], rate=e['yc_rate'])
    return out


def loop_facts(F):
    """Machine code of the ASCT read loops from the prep folder: is it the same in the plain and the probe binary?"""
    folder = os.path.join(CRB, 'results', F['prep']['folder'])

    def funcs(path):
        d, cur = {}, None
        for line in open(path):
            m = re.match(r'(?:[0-9a-f]+ )?<(\w+)>:', line)
            if m:
                cur = m.group(1)
                d[cur] = []
            elif cur and line.strip():
                d[cur].append(line.rstrip())
        return d
    plain = funcs(os.path.join(folder, 'listing.loaded-latency-asct-sve.bin.noaddr.txt'))
    probe = funcs(os.path.join(folder, 'listing.loaded-latency-asct-probe-sve.bin.noaddr.txt'))
    same = all(plain[f] == probe[f] for f in ('my_read', 'my_read_no_nops_rep_64b'))
    full = funcs(os.path.join(folder, 'listing.loaded-latency-asct-sve.bin.txt'))['my_read_no_nops_rep_64b']
    # the main loop: from the first load of a run of 8 loads up to the backward branch
    start = next(i for i in range(len(full)) if all('ldr' in full[i + k] and f'#{64 * k}]' in full[i + k] for k in range(1, 8)) and 'ldr' in full[i])
    loop = full[start:start + 11]
    sha = dict((l.split()[1], l.split()[0]) for l in F['prep']['sha'].splitlines() if re.match(r'^[0-9a-f]{64} ', l))
    inst = [l for l in sha if l.endswith('asct_venv/bin/loaded-latency-asct-sve.bin')][0]
    reb = [l for l in sha if l.endswith('.rebuild.bin')][0]
    return {'same': same, 'loop': loop, 'rebuild_same': sha[inst] == sha[reb], 'sha8': sha[inst][:8]}


def med(d, nd=1):
    return f'{d["median"]:.{nd}f}'


def span(d, nd=2):
    return f'{d["lo"]:.{nd}f} to {d["hi"]:.{nd}f}'


def pct(new, old):
    return f'{(new / old - 1) * 100:+.1f} %'


def both(fn, sep=' and '):
    return f'{fn("2")} on CPU 2{sep}{fn("41")} on CPU 41'


def q1_blocks(N, F, B, p, ul, ref):
    one = F['one']
    PC = peer_counters()
    L = F['single_launch']
    a = lambda c, b: one[c]['asct'][b]          # noqa: E731
    k = lambda c, b: one[c]['cnt'][b]           # noqa: E731
    v0, v1 = F['vendor_ratio']['a0_numa2_ddr_7200'], F['vendor_ratio']['a1_numa2_ddr_8000']
    sizes = [str(b) for b in F['sizes']]
    lab = F['labels']

    def first_slower(c, key):
        """Smallest size from which the ASCT rate is below the rate of loop `key` at every larger measured size."""
        idx = None
        for b in reversed([x for x in sizes if MI <= int(x) <= 32 * MI]):
            o = one[c][key].get(b)
            if not o:
                continue
            if a(c, b)['median'] < o['median']:
                idx = b
            else:
                break
        return idx
    sl_new = {c: first_slower(c, 'new') for c in ('2', '41')}
    sl_old = {c: first_slower(c, 'old') for c in ('2', '41')}

    N['q1_intro'] = [
        p('The runs of this section use one thread on one CPU. One process gives one rate.'),
        ul(f'<b>ASCT read:</b> 16 buffer sizes on CPUs 2 and 41, 8 processes per size and CPU, measured phase 0.25 s {ref(9, 10)}.',
           f'<b>Old read and new read:</b> the values of 2026-11-15 on the same two CPUs {ref(2)}. They were not run again in this work.',
           f'<b>Load of CRB:</b> the 1-minute load average at the start of the {L["n"]} processes was {L["load1_min"]:.2f} to {L["load1_max"]:.2f}. '
           f'At most {L["runnable_max"]} tasks were runnable. A load near 1 is the test itself (est.) {ref(10)}.'),
    ]
    N['cap_size'] = (f'<b>Figure 3.</b> Up to 2.5 MiB the ASCT read loop is the fastest of the three loops. From {lab[sl_new["2"]]} to 32 MiB it is slower than the new read loop. '
                     f'From {lab[sl_old["2"]]} to 32 MiB it is the slowest of the three (CPU 2).')
    N['cap_fall'] = (f'<b>Figure 4.</b> Both load-only loops lose rate from 1 MiB to 8 MiB. The ASCT loop loses {-(one["2"]["ratio_asct"] - 1) * 100:.0f} %, '
                     f'the new read loop {-(one["2"]["ratio_new"] - 1) * 100:.0f} % (CPU 2). The old read loop keeps its rate. '
                     'The Arm reference machines show the same fall of the ASCT loop.')
    seq = [b for b in sizes if 2 * MI <= int(b) <= 32 * MI]
    falls = all(a(c, y)['median'] < a(c, x)['median'] for c in ('2', '41') for x, y in zip(seq, seq[1:]))
    mono = ('The ASCT rate falls at every size step from 2 MiB to 32 MiB on both CPUs.' if falls
            else 'The ASCT rate does not fall at every size step from 2 MiB to 32 MiB.')
    lv = 'On 2026-11-15 the new read loop moved between two rates at 8 MiB: about 67.5 and 71.1 GB/s on CPU 2, about 69.1 and 71.6 GB/s on CPU 41'
    N['q1_rates'] = [
        ul(f'<b>The ASCT loop loses about 40 % from 1 MiB to 8 MiB.</b> It reads '
           + both(lambda c: f'{med(a(c, M1))} GB/s at 1 MiB and {med(a(c, M8))} GB/s at 8 MiB') + f' {ref(10)}.',
           f'<b>Prediction P-A1 holds on both CPUs.</b> It said that the ratio of the two rates is below 0.90. The ratio is '
           + both(lambda c: f'{one[c]["ratio_asct"]:.3f}') + f' {ref(8)}.',
           f'<b>The Arm reference machines show the same fall.</b> The ASCT loop reads {v0["m1"]:.1f} and then {v0["m8"]:.1f} GB/s on machine A0 '
           f'(ratio {v0["ratio"]:.3f}). It reads {v1["m1"]:.1f} and then {v1["m8"]:.1f} GB/s on machine A1 (ratio {v1["ratio"]:.3f}). Each value is one process of the vendor run {ref(11)}.',
           f'<b>Our loops for comparison.</b> The new read loop reads {med(one["2"]["new"][M1])} GB/s at 1 MiB and {med(one["2"]["new"][M8])} GB/s at 8 MiB on CPU 2 '
           f'(ratio {one["2"]["ratio_new"]:.3f}). The old read loop reads {med(one["2"]["old"][M1])} and {med(one["2"]["old"][M8])} GB/s (ratio {one["2"]["ratio_old"]:.3f}) {ref(2)}.',
           f'<b>The order of the loops turns around.</b> At 1 MiB the order on CPU 2 is ASCT read ({med(a("2", M1))} GB/s), new read ({med(one["2"]["new"][M1])}), '
           f'old read ({med(one["2"]["old"][M1])}). At 8 MiB it is new read ({med(one["2"]["new"][M8])}), old read ({med(one["2"]["old"][M8])}), ASCT read ({med(a("2", M8))}).',
           f'<b>The ASCT loop shows one rate at 8 MiB.</b> Its 8 processes lie within ' + both(lambda c: f'{span(a(c, M8))} GB/s') + f'. {lv} {ref(2)}.',
           '<b>No step at 8 MiB.</b> ' + mono + ' The fall from 6 MiB to 8 MiB is '
           + both(lambda c: f'{a(c, str(6 * MI))["median"] - a(c, M8)["median"]:.2f} GB/s')
           + '. The fall from 8 MiB to 12 MiB is ' + both(lambda c: f'{a(c, M8)["median"] - a(c, str(12 * MI))["median"]:.2f} GB/s') + '.'),
    ]

    fit = lambda c: one[c]['fit']             # noqa: E731
    fn = lambda c: one[c]['fit_new']          # noqa: E731
    r8n = {c: B['zs'][f'asmread.{c}.{8 * MI}']['r'] for c in ('2', '41')}
    cyc_old = B['zs'][f'oldread.2.{8 * MI}']['cyc'] if f'oldread.2.{8 * MI}' in B['zs'] else None
    N['q1_cost_intro'] = [
        p(f'The counted runs use the probe build and the ASCT capture code. Each cell has 2 processes per event set. '
          f'Every value below is a count per 64-byte line of the measured phase {ref(6, 9)}.'),
        ul('<b>L2 refills per line</b> is the share of lines that enter L2 from outside, which means from the SLC or from memory. The work of 2026-11-15 named it r.',
           '<b>Check of the counted runs.</b> The rate of the counted processes differs from the rate of the uncounted processes by at most '
           + both(lambda c: f'{one[c]["counted_vs_plain_maxpct"]:.1f} %') + ' over the 16 sizes.',
           '<b>Clock.</b> Cycles per line times lines per second gives ' + both(lambda c: f'{one[c]["ghz"][0]:.3f} to {one[c]["ghz"][1]:.3f} GHz') + ' at every size.'),
    ]
    N['cap_cost'] = ('<b>Figure 5.</b> Both load-only loops cost more cycles when more lines come from outside L2. '
                     f'The ASCT loop pays about {fit("2")["b"]:.2f} cycles for such a line, the new read loop about {fn("2")["b"]:.2f} cycles (CPU 2).')
    N['q1_cost'] = [
        ul('<b>Fitted cost of the ASCT loop (item D-A2 of the decisions file).</b> Cycles per line = '
           + both(lambda c: f'{fit(c)["a"]:.2f} + {fit(c)["b"]:.2f} &times; r (largest distance of a point from the line: {fit(c)["maxres"]:.2f} cycles)')
           + f', over the {fit("2")["n"]} sizes from 1 to 32 MiB {ref(8, 10)}.',
           '<b>Fitted cost of the new read loop on 2026-11-15.</b> Cycles per line = '
           + both(lambda c: f'{fn(c)["a"]:.2f} + {fn(c)["b"]:.2f} &times; r') + f' {ref(2)}.',
           f'<b>The ASCT loop is cheaper while the lines come from L2.</b> Its fixed cost is {fit("2")["a"]:.2f} cycles per line against {fn("2")["a"]:.2f} for the new read loop (CPU 2). '
           'It has half the instructions per line.',
           f'<b>The ASCT loop pays more for a line from outside L2.</b> It pays {fit("2")["b"]:.2f} cycles against {fn("2")["b"]:.2f} for the new read loop (CPU 2). '
           f'That is {fit("2")["b"] / fn("2")["b"]:.1f} times as much.',
           f'<b>Both loops take the same share of lines from outside L2.</b> At 8 MiB r is {k("2", M8)["l2d_cache_refill"]:.3f} for the ASCT loop and {r8n["2"]:.3f} for the new read loop (CPU 2). '
           'So at this size r is almost the same for both loops.',
           f'<b>Cost at 8 MiB.</b> The ASCT loop needs {k("2", M8)["cpu_cycles"]:.2f} cycles per line, the new read loop {B["zs"][f"asmread.2.{8 * MI}"]["cyc"]:.2f}'
           + (f', the old read loop {cyc_old:.2f}' if cyc_old else '') + f' (CPU 2) {ref(2, 10)}.'),
    ]

    pf = one['2']['prefetch']
    hw = ['l1d_cache_hwprf', 'l2d_cache_hwprf', 'l2d_cache_l1hwprf', 'l2d_cache_refill_l1hwprf']
    sw = [n for n in F['RA3_counted'] if n not in hw]
    sw_zero = all(one[c]['prefetch'][n][x] == 0 for c in ('2', '41') for n in sw for x in ('v6', 'v8', 'v12'))
    N['q1_pf_intro'] = [
        p(f'CRB lists 9 prefetch events for the data caches. All 9 were counted at all 16 sizes on both CPUs {ref(9, 10)}.'),
        ul('<b><code>l1d_cache_hwprf</code>, <code>l2d_cache_hwprf</code>:</b> prefetches of the hardware prefetcher of L1 and of L2.',
           '<b><code>l2d_cache_l1hwprf</code>, <code>l2d_cache_refill_l1hwprf</code>:</b> L2 accesses and L2 refills that the L1 prefetcher caused.',
           '<b>5 events for prefetch instructions</b> (<code>' + '</code>, <code>'.join(sw) + '</code>). '
           + ('All 5 are 0 at every size. The ASCT loop holds no prefetch instruction.' if sw_zero else 'They are not all 0.'),
           '<b><code>l1d_cache_lmiss_rd</code>, <code>l2d_cache_lmiss_rd</code>:</b> long-latency read misses of L1 and of L2. '
           'They show the result of prefetching: a line that arrived in time causes no long-latency miss.'),
    ]
    N['cap_prefetch'] = ('<b>Figure 6.</b> No counter changes its course at 8 MiB (the vertical line). '
                         f'L2 long-latency read misses rise from {k("2", M1)["l2d_cache_lmiss_rd"]:.2f} per line at 1 MiB to {k("2", M8)["l2d_cache_lmiss_rd"]:.2f} per line at 8 MiB (CPU 2).')
    nd = len(F['RA3_different'])
    late = lambda c: k(c, M8)['l2d_cache_lmiss_rd'] / k(c, M8)['l2d_cache_refill'] * 100     # noqa: E731
    N['q1_pf'] = [
        ul(('<b>Rule R-A3: no prefetch counter is different at 8 MiB.</b> ' if nd == 0 else f'<b>Rule R-A3: {nd} prefetch counters are different at 8 MiB.</b> ')
           + f'The rule compares the value at 8 MiB with the values at 6 MiB and 12 MiB on both CPUs {ref(8)}. '
           + ('So these counters give no sign that a prefetcher behaves differently at 8 MiB than at the neighbour sizes.' if nd == 0
              else 'Different: <code>' + '</code>, <code>'.join(F['RA3_different']) + '</code>.'),
           '<b>The L1 prefetcher does almost nothing for the ASCT loop.</b> At 8 MiB it makes '
           + both(lambda c: f'{k(c, M8)["l1d_cache_hwprf"]:.3f} prefetches per line') + '. '
           f'Every line is an L1 long-latency miss: {k("2", M8)["l1d_cache_lmiss_rd"]:.2f} per line at 8 MiB and {k("2", M1)["l1d_cache_lmiss_rd"]:.2f} per line at 1 MiB (CPU 2).',
           f'<b>The new read loop had fewer L1 long-latency misses.</b> On 2026-11-15 it had {PC["new.1M.2"]["l1d_cache_lmiss_rd"]:.2f} per line at 1 MiB '
           f'and {PC["new.8M.2"]["l1d_cache_lmiss_rd"]:.2f} per line at 8 MiB (CPU 2, steps <code>YC</code> and <code>ZC</code>) {ref(2)}.',
           f'<b>The L2 prefetcher works for the ASCT loop, and it is late for a part of the lines.</b> It makes {k("2", M8)["l2d_cache_hwprf"]:.2f} prefetches per line at 8 MiB (CPU 2). '
           'The loop still has ' + both(lambda c: f'{k(c, M8)["l2d_cache_lmiss_rd"]:.3f} L2 long-latency read misses per line') + '. '
           f'That is {late("2"):.0f} % and {late("41"):.0f} % of the L2 refills.',
           f'<b>For the new read loop the L2 prefetcher was in time.</b> On 2026-11-15 the new read loop had at 8 MiB '
           + both(lambda c: f'{PC[f"new.8M.{c}"]["l2d_cache_lmiss_rd"]:.4f} L2 long-latency read misses per line') + f' (step <code>ZC</code>) {ref(2)}.',
           '<b>The part that grows with the size is the late lines.</b> L2 long-latency read misses per line of the ASCT loop on CPU 2: '
           + ', '.join(f'{k("2", b)["l2d_cache_lmiss_rd"]:.3f} at {lab[b]}' for b in (M1, str(4 * MI), M8, str(32 * MI))) + '.'),
        p('<b>Hypothesis (not proven by the counters above).</b> The ASCT loop has 1.375 instructions per line, and the new read loop has 2.75. '
          'So one window of the ASCT loop covers more lines. Its loads ask for lines that the L2 prefetcher has not fetched yet. '
          'The test for this hypothesis is the ASCT loop with injected NOPs, which follows.'),
    ]


def fill(N, F, B, p, ul, ref):
    import html
    lf = loop_facts(F)
    N['_loop_same'] = (('The machine code of the two ASCT read functions is identical in both binaries. ' if lf['same'] else 'The machine code of the ASCT read functions DIFFERS between the two binaries. ')
                       + ('A rebuild without the probe flag gave a file with the same SHA-256 sum as the installed binary '
                          f'(first 8 digits <code>{lf["sha8"]}</code>) {ref(10)}.' if lf['rebuild_same'] else f'A rebuild without the probe flag gave a different file {ref(10)}.'))
    N['_loop_inst'] = f'The counters give {F["one"]["2"]["cnt"][M8]["inst_retired"]:.3f} instructions per line.'
    N['_loop_listing'] = '<pre>' + html.escape('\n'.join(l.replace('\t', '  ') for l in lf['loop'])) + '</pre>'
    static_blocks(N, F, B, p, ul, ref)
    q1_blocks(N, F, B, p, ul, ref)
    for extra in ('q1_more', 'q2_blocks', 'tail_blocks'):
        if extra in globals():
            globals()[extra](N, F, B, p, ul, ref)
    for key in [x for x in N if x.startswith('_')]:
        del N[key]


MESH_REFUSED = ('The root command for the mesh counters (sudo perf stat -a) was refused by the permission system of this agent session. '
                'No mesh counter was read in this work.')


def q1_more(N, F, B, p, ul, ref):
    one = F['one']
    PC = peer_counters()
    N['peer_counters'] = PC
    pad, pc = F['pad'], F['padcnt']
    a = lambda c, b: one[c]['asct'][b]          # noqa: E731
    k = lambda c, b: one[c]['cnt'][b]           # noqa: E731
    L = F['nc_launch']
    inst_ok = all(abs(pc[f'{c}.{n}.{M8}']['inst_retired'] - (6 + 3 * n)) < 0.01 for c in ('2', '41') for n in (1, 2, 4))
    N['q1_pad_intro'] = [
        p('Injected NOPs slow the ASCT loop down by a known amount. '
          + ('With N injected NOPs the loop has 6 + 3 &times; N instructions per line. The counters give 9.0, 12.0 and 18.0 instructions per line for N = 1, 2 and 4 ' if inst_ok
             else 'The counted instructions per line do not match 6 + 3 &times; N ') + f'{ref(5, 10)}.'),
        ul(f'<b>Part N, no counters:</b> 1, 2, 4 and 8 injected NOPs at 32 KiB, 1 MiB and 8 MiB, 4 processes per CPU and cell {ref(9)}.',
           f'<b>Part NC, with counters:</b> 1, 2 and 4 injected NOPs at 1 MiB and 8 MiB, 6 processes per CPU and cell (2 for each of 3 event sets). '
           f'This part was defined after the first data. Its prediction P-A5 was written before its own data {ref(8)}.',
           f'<b>Load of CRB for part NC:</b> 1-minute load average {L["load1_min"]:.2f} to {L["load1_max"]:.2f} at the start of the {L["n"]} processes, at most {L["runnable_max"]} runnable tasks {ref(10)}.'),
    ]
    N['cap_pad'] = (f'<b>Figure 7.</b> With 1 or 2 injected NOPs the ASCT loop reads 8 MiB faster than without NOPs: {med(pad["2.1"][M8])} and {med(pad["2.2"][M8])} GB/s '
                    f'against {med(a("2", M8))} GB/s (CPU 2). With 4 or 8 injected NOPs the NOPs are the limit at both sizes.')
    n2, new8 = pc[f'2.2.{M8}'], PC['new.8M.2']
    N['q1_pad'] = [
        ul('<b>The padded loop reads 8 MiB faster.</b> Rate at 8 MiB with 0, 1 and 2 injected NOPs: '
           + both(lambda c: f'{med(a(c, M8))}, {med(pad[f"{c}.1"][M8])} and {med(pad[f"{c}.2"][M8])} GB/s') + f' (part N) {ref(10)}.',
           '<b>Prediction P-A5 holds on both CPUs.</b> It said that the L2 long-latency read misses per line at 8 MiB with 2 injected NOPs are below 0.8 times the value with 0 NOPs. '
           'They fall from ' + both(lambda c: f'{F["PA5"][c]["n0"]:.4f} to {F["PA5"][c]["n2"]:.4f}') + f' {ref(8)}.',
           '<b>With 2 injected NOPs both prefetchers work.</b> At 8 MiB the L1 prefetches per line rise from '
           + both(lambda c: f'{k(c, M8)["l1d_cache_hwprf"]:.3f} to {pc[f"{c}.2.{M8}"]["l1d_cache_hwprf"]:.2f}')
           + f'. The L2 accesses by the L1 prefetcher rise from {k("2", M8)["l2d_cache_l1hwprf"]:.2f} to {n2["l2d_cache_l1hwprf"]:.2f} per line (CPU 2).',
           f'<b>The ASCT loop with 2 injected NOPs then behaves like our new read loop.</b> At 8 MiB on CPU 2 it reads {n2["_rate"]:.1f} GB/s with {n2["cpu_cycles"]:.2f} cycles, '
           f'{n2["l1d_cache_lmiss_rd"]:.2f} L1 long-latency misses and {n2["l2d_cache_lmiss_rd"]:.4f} L2 long-latency misses per line. '
           f'The new read loop on 2026-11-15: {new8["rate"]:.1f} GB/s, {new8["cpu_cycles"]:.2f} cycles, {new8["l1d_cache_lmiss_rd"]:.2f} and {new8["l2d_cache_lmiss_rd"]:.4f} '
           f'(median of 2 counted processes of step <code>ZC</code>) {ref(2)}.',
           '<b>Prediction P-A4 holds on both CPUs.</b> It said that a loop which is limited by its own instructions keeps its rate within 3 % from 1 MiB to 8 MiB. '
           'With 4 injected NOPs the rate is ' + both(lambda c: f'{med(pad[f"{c}.4"][M1])} and then {med(pad[f"{c}.4"][M8])} GB/s')
           + '. With 8 it is ' + both(lambda c: f'{med(pad[f"{c}.8"][M1])} and then {med(pad[f"{c}.8"][M8])} GB/s') + f' {ref(8)}.',
           '<b>Not explained: the spread of the loop with 2 injected NOPs at 1 MiB.</b> Its 4 processes of part N lie within '
           + both(lambda c: f'{span(pad[f"{c}.2"][M1], 1)} GB/s') + '. The 6 counted processes of part NC lie within '
           + both(lambda c: f'{pc[f"{c}.2.{M1}"]["_rate_lo"]:.1f} to {pc[f"{c}.2.{M1}"]["_rate_hi"]:.1f} GB/s') + '. Prediction P-A4 does not cover this loop, because its median at 1 MiB is above 60 GB/s.'),
        p('<b>What this means.</b>'),
        ul('The explanation for the ASCT loop without NOPs at 8 MiB: its loads ask for lines before the prefetchers have fetched them. Prediction P-A5 was the test of this explanation, and it holds.',
           f'A loop with a slower pace gets its lines into L2 in time. Then it needs about {n2["cpu_cycles"]:.1f} cycles per line at 8 MiB, '
           f'against {k("2", M1)["cpu_cycles"]:.2f} cycles per line at 1 MiB for the fastest loop (ASCT read, 0 NOPs, CPU 2).',
           f'The handoff of 2026-11-15 reports 73.2 to 73.9 GB/s at 8 MiB for its padded loop <code>read_nop64</code>, and 71.0 to 71.6 GB/s for the upper level of the new read loop {ref(2)}. '
           f'The best ASCT form of this work reads {med(pad["2.2"][M8])} and {med(pad["41.2"][M8])} GB/s (2 injected NOPs, CPUs 2 and 41).'),
    ]

    r = F['cpu41_over_cpu2_pct']
    mid = [r[str(b)] for b in F['sizes'] if 4 * MI <= b <= 32 * MI]
    big = [r[str(b)] for b in F['sizes'] if b >= 256 * MI]
    small = [r[str(b)] for b in F['sizes'] if b <= 2 * MI]
    lvl = lambda c, b: sum(k(c, b)[f'l2_chi_cbusy{i}'] for i in (1, 2, 3))     # noqa: E731
    G = str(1 << 30)
    N['q1_mesh_intro'] = [
        p('The request asked for counters of the SLC, of the mesh and of the hops. The mesh has its own counters (Linux units <code>arm_cmn_0</code> and <code>arm_cmn_1</code>). Reading them needs root.'),
    ]
    N['mesh_single_missing'] = (MESH_REFUSED + ' The run script and its run list are ready (run_mesh.sh, spec_single.txt, sets_single.txt in the folder of [Ref9]). '
                                'They read 42 mesh events while one core runs the ASCT loop at 1, 6, 8, 12 and 32 MiB and at 1 GiB.')
    N['mesh_single_tags'], N['mesh_chip_tags'], N['mesh_tag_names'] = [], [], {}
    N['q1_mesh'] = [
        p('Three things about the SLC and the mesh are visible from the core counters, without root.'),
        ul(f'<b>The SLC holds the whole buffer up to 32 MiB.</b> The counter of last-level read misses (<code>ll_cache_miss_rd</code>) is 0.000 per line at every size up to 32 MiB on both CPUs. '
           f'It is {k("2", str(256 * MI))["ll_cache_miss_rd"]:.3f} per line at 256 MiB and {k("2", G)["ll_cache_miss_rd"]:.3f} at 1 GiB (CPU 2) {ref(10)}.',
           '<b>The mesh never reports itself busy at 8 MiB.</b> Each answer that a core receives from the mesh carries a busy level from 0 to 3. '
           f'At 8 MiB the core receives {k("2", M8)["l2_chi_cbusy0"]:.2f} answers per line with level 0 and {lvl("2", M8):.3f} with levels 1 to 3 (CPU 2). '
           f'At 1 GiB it receives {lvl("2", G):.2f} answers per line with levels 1 to 3.',
           f'<b>Distance.</b> CPU 2 sits in column 1 of its mesh, which is the outer column of the cores. CPU 41 sits in column 5, near the middle. '
           f'The mean distance to the 35 SLC slices of the mesh is 4.20 hops for CPU 2 and 3.06 hops for CPU 41 (est., from the kernel map and the inferred core positions) {ref(14)}. '
           f'The ASCT rate of CPU 41 is {min(mid):.1f} to {max(mid):.1f} % higher at every size from 4 to 32 MiB. It is {min(big):.1f} to {max(big):.1f} % higher at 256 MiB and 1 GiB. '
           f'At 2 MiB and below the two CPUs differ by {min(small):+.1f} to {max(small):+.1f} %.'),
        p('<b>Hypothesis.</b> The shorter mean distance of CPU 41 causes its higher rate above 4 MiB. Two CPUs cannot prove it. '
          'The measurement that would confirm or reject it: the same sweep on CPUs at other columns of the mesh.'),
    ]

    newr = one['2']['new']
    N['q1_verdict'] = [
        ul(f'<b>ASCT confirms the fall at 8 MiB.</b> A load-only loop loses rate when its buffer no longer fits L2. The ASCT loop loses {-(one["2"]["ratio_asct"] - 1) * 100:.0f} % on CRB '
           f'and {-(F["vendor_ratio"]["a0_numa2_ddr_7200"]["ratio"] - 1) * 100:.0f} % and {-(F["vendor_ratio"]["a1_numa2_ddr_8000"]["ratio"] - 1) * 100:.0f} % on the two Arm reference machines. '
           'So the fall is not an error of our new read loop.',
           f'<b>ASCT gives no higher rate at 8 MiB than our new read loop.</b> ASCT read: {med(a("2", M8))} GB/s. ASCT read with 2 injected NOPs: {med(F["pad"]["2.2"][M8])} GB/s. '
           f'New read: {med(newr[M8])} GB/s. Old read: {med(one["2"]["old"][M8])} GB/s (CPU 2).',
           f'<b>Why the gain is small at 8 MiB.</b> The old read loop is limited by its own work. It needs 2.67 cycles per line at every size from 1 to 16 MiB {ref(2)}. '
           'A load-only loop is limited by the supply of lines. From L2 a line costs about 1.9 to 2.1 cycles (ASCT read and new read at 1 MiB). '
           'At 8 MiB a line costs about 2.5 to 2.6 cycles, also when it is prefetched in time (new read, and ASCT read with 2 injected NOPs). '
           'So the two limits are 27 % apart at 1 MiB and a few percent apart at 8 MiB.',
           '<b>The prefetchers.</b> No prefetch counter changes its course at 8 MiB (rule R-A3). The prefetchers explain why the ASCT loop is slower than the new read loop at 8 MiB (prediction P-A5). '
           f'They do not explain the small gain of the new read loop: its lines were in L2 in time on 2026-11-15 ({PC["new.8M.2"]["l2d_cache_lmiss_rd"]:.4f} L2 long-latency misses per line) {ref(2)}.'),
        p('<b>Insufficient data:</b> why a line from the SLC costs about 0.5 to 0.7 cycles more than a line from L2 when it arrives in L2 in time. '
          'The measurements that would resolve it: the mesh and SLC counters while one core runs the loop (root), '
          'and the prefetch events of this work counted for our own new read loop.'),
    ]


def q2_blocks(N, F, B, p, ul, ref):
    ch = F['chip']
    nops = ch['nops']
    L = F['chip_launch']
    lp = {r[0]: r for r in B['chip']['loops']}
    old, new, pl1 = lp['old read'], lp['new read (asmread)'], lp['read_1pl']
    base, dflt = ch['base'], ch['default']
    bn = str(ch['bestN'])
    best = nops[bn]
    v0 = dict((n, x) for n, _, x in B['vendor']['a0_numa2_ddr_7200']['nops'])
    v1 = dict((n, x) for n, _, x in B['vendor']['a1_numa2_ddr_8000']['nops'])
    pt = B['chip']['per_thread']
    lay = ch['layouts']
    cnt = ch['cnt']
    slow, fast, m0 = cnt['6456.n0'], cnt['6456.n20'], cnt['6400.n0']
    e = lambda c, n, m='mesh0': c['ev'][n][m]     # noqa: E731

    N['q2_intro'] = [
        p('The runs of this section use one thread on each of 120 CPUs: CPUs 0 to 63 on mesh 0 and CPUs 64 to 119 on mesh 1. Each thread has a 256 MiB buffer, so the lines come from memory.'),
        ul(f'<b>ASCT read:</b> {base["n"]} processes with 0 injected NOPs and 2 processes for each of 15 other NOP counts, measured phase 2 s {ref(9, 10)}.',
           f'<b>Check with the ASCT default of 0.25 s:</b> {dflt["n"]} processes with 0 injected NOPs read {med(dflt)} GB/s (range {span(dflt, 1)}).',
           f'<b>Old read and new read:</b> the values of 2026-11-15 on the same 120 CPUs {ref(3)}. They were not run again in this work.',
           f'<b>Load of CRB:</b> before each process the script waited until at most 2 tasks were runnable, and then 5 s. At most {L["runnable_max"]} tasks were runnable at the start of the {L["n"]} processes. '
           f'No user was logged in. The 1-minute load average at the starts was {L["load1_min"]:.2f} to {L["load1_max"]:.1f}. Its high values are the trace of the process before (est.) {ref(10)}.',
           '<b>How ASCT builds its total.</b> Every thread runs the same number of passes and measures its own time. ASCT adds the rates of the threads. '
           f'When some threads finish early, the others then run with less competition, and the total is too high. So table 5 also gives a lower bound: all bytes of the process divided by the time of its slowest thread {ref(5, 8)}.'),
    ]
    N['cap_chip'] = (f'<b>Figure 8.</b> On CRB the ASCT loop without NOPs reads {med(base)} GB/s, less than both of our loops. With {bn} injected NOPs it reads {med(best)} GB/s, more than both. '
                     f'On the two Arm reference machines the ASCT loop reads {v0[0]:.1f} and {v1[0]:.1f} GB/s without NOPs.')
    N['cap_nops'] = (f'<b>Figure 9.</b> On CRB the total rises from {med(base)} GB/s at 0 injected NOPs to {med(best)} GB/s at {bn}. From 30 injected NOPs on it falls, because the NOPs become the limit. '
                     'On the Arm reference machines the total is highest at 0 injected NOPs.')
    fastN = ch['fastN']
    fast_floor = [x for x in fastN if nops[str(x)]['floor'] >= 459]
    n3, n4 = nops['3'], nops['4']
    N['q2_rates'] = [
        ul(f'<b>Prediction P-B1 holds.</b> It said that the ASCT total at 64+56 with 0 injected NOPs is below 334 GB/s. The median of {base["n"]} processes is {med(base)} GB/s (range {span(base, 1)}) {ref(8, 10)}.',
           f'<b>Prediction P-B2 holds.</b> It said that at least one NOP count from 1 to 40 gives 459 GB/s or more. {len(fastN)} counts do by the ASCT total: {", ".join(str(x) for x in fastN)}. '
           f'{len(fast_floor)} counts do by the lower bound: {", ".join(str(x) for x in fast_floor)} {ref(8)}.',
           f'<b>The highest total is {med(best)} GB/s at {bn} injected NOPs.</b> That is {best["median"] / base["median"]:.2f} times the total without NOPs. '
           f'The lower bounds are {base["floor"]:.1f} and {best["floor"]:.1f} GB/s, a factor of {best["floor"] / base["floor"]:.2f}.',
           f'<b>Mesh 0 becomes fast first.</b> With 4 injected NOPs a thread of mesh 0 reads {n4["thr0"][1]:.2f} GB/s and a thread of mesh 1 reads {n4["thr1"][1]:.2f} GB/s (median threads). '
           f'With {bn} injected NOPs they read {best["thr0"][1]:.2f} and {best["thr1"][1]:.2f} GB/s.',
           f'<b>Caution for 3 and 4 injected NOPs.</b> The threads of mesh 0 finish in about {n4["sec"][0]:.1f} s, and the slowest thread needs {n4["sec"][1]:.1f} s. '
           f'ASCT prints {med(n3)} and {med(n4)} GB/s. The lower bounds are {n3["floor"]:.1f} and {n4["floor"]:.1f} GB/s.',
           f'<b>Our loops for comparison.</b> New read: {new[3]:.1f} to {new[4]:.1f} GB/s. Old read: {old[3]:.1f} to {old[4]:.1f} GB/s. Our loop with one load per line (<code>read_1pl</code>): {pl1[3]:.1f} to {pl1[4]:.1f} GB/s {ref(3)}. '
           f'The ASCT loop without NOPs also has one load per line. Its {med(base)} GB/s is {(1 - base["median"] / pl1[3]) * 100:.1f} to {(1 - base["median"] / pl1[4]) * 100:.1f} % below that loop.',
           f'<b>The old read loop was not in the fastest state.</b> In its runs of 2026-11-15 a thread of mesh 1 read {pt["fast"]["mesh1"][0]:.2f} to {pt["fast"]["mesh1"][1]:.2f} GB/s {ref(3)}. '
           f'That is the rate of a mesh 1 thread of the ASCT loop with 3 or 4 injected NOPs ({n3["thr1"][1]:.2f} and {n4["thr1"][1]:.2f} GB/s). With {bn} injected NOPs a mesh 1 thread reads {best["thr1"][1]:.2f} GB/s.',
           f'<b>Above 30 injected NOPs the NOPs are the limit.</b> The total is {med(nops["40"])} GB/s at 40, {med(nops["100"])} GB/s at 100 and {med(nops["180"])} GB/s at 180.'),
    ]
    N['cap_threads'] = (f'<b>Figure 10.</b> With {bn} injected NOPs one thread reads {best["thr0"][1] / base["thr0"][1]:.1f} times as much as without NOPs on mesh 0, '
                        f'and {best["thr1"][1] / base["thr1"][1]:.1f} times as much on mesh 1.')
    l64, l56, l112 = lay['6400'], lay['0056'], lay['5656']
    ssum = l64['0']['median'] + l56['0']['median']
    N['q2_layouts'] = [
        ul(f'<b>Prediction P-B3 holds.</b> It said that one mesh alone reads within 5 % of its values of 2026-11-15. 64+0 reads {med(l64["0"])} GB/s (2026-11-15: 348.0 to 351.0). '
           f'0+56 reads {med(l56["0"])} GB/s (2026-11-15: 318.0 to 321.7) {ref(3, 8)}.',
           f'<b>One mesh alone is not slow.</b> Without NOPs a thread reads {l64["0"]["thr0"][1]:.2f} GB/s at 64+0 and {l56["0"]["thr1"][1]:.2f} GB/s at 0+56 (median threads). '
           f'At 64+56 it reads {base["thr0"][1]:.2f} and {base["thr1"][1]:.2f} GB/s.',
           f'<b>The slow state needs threads on both meshes, not 120 threads.</b> 56+56 (112 threads) reads {med(l112["0"])} GB/s without NOPs and {med(l112["20"])} GB/s with 20 injected NOPs.',
           f'<b>Count of processes.</b> Each cell of table 6 has {min(v["n"] for d in lay.values() for v in d.values())} or {max(v["n"] for d in lay.values() for v in d.values())} processes. The reason is a defect of the run script, see section 6.',
           f'<b>Share of the single-mesh sum.</b> 64+0 and 0+56 add up to {ssum:.1f} GB/s. 64+56 reaches {base["median"] / ssum * 100:.0f} % of that without NOPs and {best["median"] / ssum * 100:.0f} % with {bn} injected NOPs.'),
    ]
    tot = lambda c: f'{min(c["totals"].values()):.0f} to {max(c["totals"].values()):.0f} GB/s'     # noqa: E731
    permiss = lambda c, m: e(c, 'stall_backend_mem', m) / e(c, 'll_cache_miss_rd', m)               # noqa: E731
    answers = lambda c, m: sum(e(c, f'l2_chi_cbusy{i}', m) for i in range(4))                       # noqa: E731
    N['q2_cnt_intro'] = [
        p(f'The counted runs use the probe build on all 120 threads. Each of the 7 event sets ran once in each of three cases, with a 2 s measured phase {ref(9, 10)}.'),
        ul(f'<b>64+56, 0 injected NOPs</b> (slow): the 7 counted processes read {tot(slow)}.',
           f'<b>64+56, 20 injected NOPs</b> (fast): {tot(fast)}.',
           f'<b>64+0, 0 injected NOPs</b> (one mesh): {tot(m0)}.',
           'Table 7 gives each counter per 64-byte line as the median over the threads of a mesh.'),
    ]
    N['q2_cnt'] = [
        ul(f'<b>Cycles per line.</b> A thread needs {e(slow, "cpu_cycles"):.0f} cycles per line on mesh 0 and {e(slow, "cpu_cycles", "mesh1"):.0f} on mesh 1 in the slow case. '
           f'It needs {e(fast, "cpu_cycles"):.0f} cycles in the fast case and {e(m0, "cpu_cycles"):.0f} cycles with one mesh alone.',
           f'<b>In the fast case no load waits for memory.</b> L2 long-latency read misses: {e(fast, "l2d_cache_lmiss_rd"):.4f} per line. Last-level read misses: {e(fast, "ll_cache_miss_rd"):.4f} per line. '
           f'Stall cycles for memory: {e(fast, "stall_backend_mem"):.3f} per line. The prefetchers fetch every line: {e(fast, "l1d_cache_hwprf"):.2f} L1 prefetches '
           f'and {e(fast, "l2d_cache_l1hwprf"):.2f} L2 accesses by the L1 prefetcher per line.',
           f'<b>In the slow case 30 % of the loads wait for memory.</b> Last-level read misses: {e(slow, "ll_cache_miss_rd"):.2f} per line on both meshes. L1 prefetches: {e(slow, "l1d_cache_hwprf"):.2f} per line. '
           f'Stall cycles for memory: {e(slow, "stall_backend_mem"):.0f} and {e(slow, "stall_backend_mem", "mesh1"):.0f} per line.',
           f'<b>One mesh alone has almost the same miss pattern and is fast.</b> At 64+0 the last-level read misses are {e(m0, "ll_cache_miss_rd"):.2f} per line and the stall cycles for memory {e(m0, "stall_backend_mem"):.0f} per line.',
           f'<b>A load that waits for memory waits longer when both meshes are loaded.</b> Stall cycles for memory divided by last-level read misses: {permiss(slow, "mesh0"):.0f} and {permiss(slow, "mesh1"):.0f} cycles in the slow case, '
           f'{permiss(m0, "mesh0"):.0f} cycles with one mesh alone (est., a quotient of two medians).',
           f'<b>Busy level.</b> In the slow case {e(slow, "l2_chi_cbusy0") / answers(slow, "mesh0") * 100:.0f} % of the answers from the mesh carry busy level 0 (mesh 0). '
           f'In the fast case {e(fast, "l2_chi_cbusy0") / answers(fast, "mesh0") * 100:.0f} % do, and with one mesh alone {e(m0, "l2_chi_cbusy0") / answers(m0, "mesh0") * 100:.0f} %. '
           'So the mesh reports itself less busy in the slow case than in the two faster cases.',
           f'<b>Not involved.</b> Page-table walks are {e(slow, "dtlb_walk"):.4f} per line in all three cases. All counters for prefetch instructions are 0.'),
        p('<b>Hypothesis.</b> The slow state needs two things at the same time: loads that the prefetchers do not cover, and threads on both meshes. '
          'The counters support the first part: the slow case has uncovered loads and the fast case has none. They do not show which hardware part makes an uncovered load wait more than twice as long. '
          'The measurement that would show it: the mesh counters at 0, 4 and 20 injected NOPs (root).'),
    ]
    N['q2_mesh_intro'] = [p('The work of 2026-11-15 read 22 sets of mesh counters as root while our loops ran at 64+56. The plan of this work was the same read for the ASCT loop at 0, 4 and 20 injected NOPs.')]
    N['mesh_chip_missing'] = (MESH_REFUSED + ' The run script and its run list are ready (run_mesh.sh, spec_chip.txt, sets_chip.txt in the folder of [Ref9]).')
    N['q2_mesh'] = [p(f'The mesh counters of 2026-11-15 for the old read loop and the new read loop are in the report of that work {ref(3)}.')]
    N['q2_verdict'] = [
        ul(f'<b>ASCT reproduces the low whole-chip rate.</b> Its own loop reads {med(base)} GB/s on the same 120 CPUs. Our new read loop reads {new[3]:.1f} to {new[4]:.1f} GB/s {ref(3)}.',
           f'<b>The low rate is a state of CRB, not its capacity.</b> The same binary on the same CPUs reads {med(best)} GB/s with {bn} injected NOPs (lower bound {best["floor"]:.1f} GB/s). '
           f'That is above the old read loop ({old[3]:.1f} to {old[4]:.1f} GB/s).',
           '<b>What goes with the state.</b> The loop without NOPs is slow, and its counters show loads that the prefetchers do not cover. '
           'The loop with 20 injected NOPs is fast, and its counters show no such load. '
           f'This agrees with the result of 2026-11-15, where loops with a long window were slow {ref(3)}.',
           f'<b>The Arm reference machines do not show the state.</b> Their totals are highest without NOPs: {v0[0]:.1f} and {v1[0]:.1f} GB/s {ref(11)}.'),
        p('<b>Hypothesis.</b> The state belongs to the configuration of CRB: firmware v0.7.2 with one NUMA node. The Arm reference machines run firmware v0.9.0 with two NUMA nodes. '
          'The measurement that would confirm or reject it: the same ASCT runs on CRB after a change to firmware v0.9.0.'),
        p('<b>Insufficient data:</b> which hardware part causes the slow state. The measurement that would resolve it: the mesh counters for the ASCT loop at 0, 4 and 20 injected NOPs (root).'),
    ]


def tail_blocks(N, F, B, p, ul, ref):
    one, ch = F['one'], F['chip']
    V0, V1 = B['vendor']['a0_numa2_ddr_7200'], B['vendor']['a1_numa2_ddr_8000']
    s0, s1 = dict(V0['sweep']), dict(V1['sweep'])
    a = lambda c, b: one[c]['asct'][str(b)]['median']          # noqa: E731
    v0 = dict((n, x) for n, _, x in V0['nops'])
    v1 = dict((n, x) for n, _, x in V1['nops'])
    base = ch['base']
    bn = str(ch['bestN'])
    best = ch['nops'][bn]
    G = 1 << 30
    peak0 = int(V0['channels']) * int(V0['speed']) * 8 / 1000
    peak_crb = 10 * 8000 * 8 / 1000
    mid = [abs(a('2', b) / s0[b] - 1) * 100 for b in (4 * MI, 8 * MI, 16 * MI, 32 * MI)]
    N['vendor'] = [
        p(f'The Arm welcome kit holds two complete ASCT runs that Arm made on its own machines {ref(11)}. They ran through the ASCT front end, as root.'),
        ul(f'<b>Machine A0:</b> {V0["cpus"]} CPUs, {V0["numa"]} NUMA nodes, firmware v0.9.0, {V0["channels"]} memory channels at {V0["speed"]} MT/s. Its one-core runs use CPU {V0["cpu"][0]}.',
           f'<b>Machine A1:</b> {V1["cpus"]} CPUs, {V1["numa"]} NUMA nodes, firmware v0.9.0, {V1["channels"]} memory channels at {V1["speed"]} MT/s. Its one-core runs use CPU {V1["cpu"][0]}.',
           f'<b>CRB:</b> 128 CPUs (120 used), 1 NUMA node, firmware v0.7.2, 10 memory modules at 8000 MT/s {ref(12)}.'),
        p('<b>One core.</b>'),
        ul(f'<b>CRB and A0 agree from 4 to 32 MiB.</b> The ASCT rate of CRB CPU 2 differs from A0 by {min(mid):.1f} to {max(mid):.1f} % at 4, 8, 16 and 32 MiB. '
           f'At 8 MiB: {a("2", 8 * MI):.2f} GB/s on CRB and {s0[8 * MI]:.2f} GB/s on A0. So the fall at 8 MiB does not come from the firmware version of CRB.',
           f'<b>CRB is slower from memory.</b> At 1 GiB the ASCT loop reads {a("2", G):.1f} GB/s on CRB CPU 2 and {a("41", G):.1f} GB/s on CPU 41. It reads {s0[G]:.1f} GB/s on A0 and {s1[G]:.1f} GB/s on A1.'),
        p('<b>Whole chip.</b>'),
        ul(f'<b>Without NOPs the Arm machines are {v0[0] / base["median"]:.1f} and {v1[0] / base["median"]:.1f} times as fast as CRB.</b> A0 reads {v0[0]:.1f} GB/s and A1 reads {v1[0]:.1f} GB/s with the CPUs of the whole machine. '
           f'CRB reads {base["median"]:.1f} GB/s with 120 threads.',
           f'<b>On the Arm machines every injected NOP costs rate.</b> A0: {v0[0]:.1f}, {v0[10]:.1f}, {v0[20]:.1f} GB/s at 0, 10 and 20 injected NOPs. '
           f'CRB: {base["median"]:.1f}, {ch["nops"]["10"]["median"]:.1f}, {ch["nops"]["20"]["median"]:.1f} GB/s.',
           f'<b>Where the NOPs are the limit, the machines agree.</b> At 100 injected NOPs CRB reads {ch["nops"]["100"]["median"]:.1f} GB/s with 120 threads and A0 reads {v0[100]:.1f} GB/s. '
           f'At 180: {ch["nops"]["180"]["median"]:.1f} and {v0[180]:.1f} GB/s.',
           f'<b>Share of the memory channels.</b> ASCT gives a "peak theoretical" rate: channels &times; transfer rate &times; 8 bytes. For A0 that is {peak0:.1f} GB/s, and ASCT reports {V0["peak"]["All Reads"][1]:.1f} % for reads. '
           f'The same formula gives {peak_crb:.0f} GB/s for the 10 modules of CRB (est., computed here, not printed by ASCT). '
           f'The CRB total at {bn} injected NOPs is {best["median"] / peak_crb * 100:.0f} % of that, and its lower bound is {best["floor"] / peak_crb * 100:.0f} %.'),
        p('<b>Other traffic types.</b> The ASCT benchmark <code>peak-bandwidth</code> has four read-write types beside "All Reads". Table 8 gives them for the 120 CPUs of CRB.'),
    ]
    mix = ch['mix']
    N['vendor2'] = [
        ul(f'<b>On CRB one type stands out.</b> "1:1 Reads-Writes" reads and writes {med(mix["4"])} GB/s. The other three types and "All Reads" lie between {min(mix[t]["median"] for t in "235"):.1f} and {max(base["median"], max(mix[t]["median"] for t in "23")):.1f} GB/s.',
           '<b>On the Arm machines "All Reads" is the highest type.</b>',
           '<b>Hypothesis.</b> The four slower types on CRB are in the slow state of section 3, and the 1:1 loop has a slower pace. '
           'No counter was captured for these types. The measurement that would confirm or reject it: the counted runs of table 7 for each type.'),
    ]

    SL, CL, NL = F['single_launch'], F['chip_launch'], F['nc_launch']
    cf = CL['per_folder']
    f1, f2 = F['chip_folder']
    env = F['prep']['env']
    prep_load = env_fact(env, r'^loadavg (\S+ \S+ \S+)')
    prep_users = env_fact(env, r'^users (\d+)')
    N['runs'] = [
        p(f'All runs: CRB, 2026-11-16, after the end of the block that Jeremy Conner had announced for 17:30 to 23:10 UTC {ref(13)}. Nine logins: five ran one script each, and four copied result folders.'),
        ul(f'<b>23:12 UTC, preparation</b> (folder <code>{F["prep"]["folder"]}</code>): machine record, build of the probe binary, event codes, test processes. '
           f'Load average before the first process: {prep_load}. Users logged in: {prep_users}.',
           f'<b>23:12 to 23:19 UTC, one core</b> (folder <code>{F["single_folder"]}</code>): {SL["n"]} processes, {SL["rc_nonzero"]} with a non-zero exit code. '
           f'1-minute load average at the starts: {SL["load1_min"]:.2f} to {SL["load1_max"]:.2f}.',
           f'<b>23:19 to 23:33 UTC, whole chip</b> (folder <code>{f1}</code>): {cf[f1]["n"]} processes, {cf[f1]["rc_nonzero"]} with a non-zero exit code. '
           f'At most {cf[f1]["runnable_max"]} runnable tasks at a start.',
           f'<b>23:37 UTC, one core with injected NOPs and counters</b> (folder <code>{F["nc_folder"]}</code>): {NL["n"]} processes, {NL["rc_nonzero"]} with a non-zero exit code. '
           f'1-minute load average at the starts: {NL["load1_min"]:.2f} to {NL["load1_max"]:.2f}.',
           f'<b>23:44 to 23:47 UTC, whole chip, two steps again</b> (folder <code>{f2}</code>): {cf[f2]["n"]} processes, {cf[f2]["rc_nonzero"]} with a non-zero exit code.',
           '<b>Checks of the counters:</b> every counter row ran for the whole time that it was enabled, and that time is within 2 % of the measured phase of its thread. '
           f'Rows that fail: {len(F["single_problems"]) + len(F.get("nc_problems", [])) + len(F["chip_problems"])} {ref(10)}.',
           '<b>Shared machine:</b> Slack channel #phoenix-crb was read at 23:12, 23:19, 23:23, 23:32, 23:37 and 23:44 UTC. That is before every script and twice during the whole-chip run. No new block was announced. '
           'Every script checks the marker file of the other user (<code>/tmp/positron-perf.RUNNING</code>) before every process. It was never present.',
           '<b>CPUs:</b> only CPUs 0 to 119. Nothing ran on CPUs 120 to 127.',
           '<b>Root:</b> not used for any run. The preparation script ran <code>sudo -n true</code> once, to test whether sudo asks for a password. No setting of CRB was changed. No package was installed.',
           '<b>Files on CRB:</b> <code>~/cache-perf/asct-20261116/</code> (scripts, the build folder, the probe binary) and 5 folders <code>~/cache-perf/results/asct-*</code>.'),
        p('<b>Deviations.</b>'),
        ul('<b>Mesh counters were not captured.</b> ' + MESH_REFUSED + ' The request asked for them.',
           '<b>A defect of the whole-chip script overwrote 8 result files.</b> The function that starts a process used the same variable name as the loop that numbers the processes. '
           'In the steps for the other layouts and for the traffic types the second process of 8 cells got the file name of the first. '
           f'The script was corrected, and both steps ran again at 23:44 UTC. Tables 6 and 8 use every result file that exists: 3 or 4 processes per cell {ref(9, 10)}.',
           '<b>The counted whole-chip processes without NOPs read more than the uncounted ones.</b> '
           f'Counted: {min(ch["cnt"]["6456.n0"]["totals"].values()):.0f} to {max(ch["cnt"]["6456.n0"]["totals"].values()):.0f} GB/s. Uncounted: {span(base, 1)} GB/s. The cause was not examined.',
           f'<b>Three additions after data was seen:</b> part NC, the lower bound for the totals, and the list of mesh runs. Each is recorded with its time in the decisions file {ref(8)}.',
           '<b>Old read and new read were not run again.</b> Their values are one day older than the ASCT values.',
           '<b>Another account on CRB.</b> The process list of 23:19:56 UTC shows a session-manager process (<code>systemd</code>) of another account with 3.1 % CPU share. '
           f'No user was logged in at any start of a process, and the marker file was absent {ref(10)}.',
           '<b>No review by a second person or agent.</b> The scripts were tested on the development machine with stand-in binaries before the first login.'),
    ]
    N['open'] = [
        ul('<b>Mesh, SLC and hop counters for the ASCT loop.</b> They need an approval of a read-only root command on CRB (<code>sudo perf stat -a</code> on the units <code>arm_cmn_0</code> and <code>arm_cmn_1</code>). '
           f'The scripts and run lists are ready {ref(9)}. Run time: about 20 minutes (est.).',
           '<b>Registers.</b> ASCT can read core registers only with a kernel module that CRB does not have, and its mesh register report needs root and <code>/dev/mem</code>. '
           'A statement from Arm on the prefetcher settings of firmware v0.7.2 would also answer it.',
           '<b>Firmware.</b> The Arm reference machines with firmware v0.9.0 and two NUMA nodes do not show the slow whole-chip state. The same ASCT runs on CRB after a firmware change would show whether the firmware is the cause.',
           '<b>Prefetch counters for our own loops.</b> This work counted the prefetch events for the ASCT loop only. The same 7 event sets for the old and the new read loop would complete table 4.',
           '<b>The two rates of the new read loop at 8 MiB</b> stay open from 2026-11-15. The ASCT loop shows one rate.',
           '<b>The spread of the ASCT loop with 2 injected NOPs at 1 MiB</b> (58 to 87 GB/s between processes) is not explained.'),
    ]
    pad2 = F['pad']['2.2'][M8]
    N['subtitle'] = ('CRB is the Arm Phoenix Reference Server in our lab. ASCT is the Arm System Characterization Tool, version 0.7.1+77461b3. '
                     'Runs of 2026-11-16, 23:12 to 23:47 UTC. Page built from <code>facts.json</code> by <code>report.py</code>.')
    N['short'] = [
        ul(f'<b>8 MiB on one core.</b> The read loop of ASCT also loses rate from 1 MiB to 8 MiB ({a("2", MI):.1f} to {a("2", 8 * MI):.1f} GB/s on CPU 2), '
           f'and no form of it reads 8 MiB faster than our new read loop ({pad2["median"]:.1f} against {one["2"]["new"][M8]["median"]:.1f} GB/s).',
           f'<b>Whole chip.</b> On the same 120 CPUs the ASCT loop reads {base["median"]:.1f} GB/s, and with {bn} injected delay rounds it reads {best["median"]:.1f} GB/s, '
           'so the low whole-chip number is a state of CRB and not its capacity.',
           '<b>Counters.</b> In both slow cases the core counters show loads that run ahead of the hardware prefetchers, '
           'and the mesh counters are missing, because the root command for them was refused in this session.'),
    ]
