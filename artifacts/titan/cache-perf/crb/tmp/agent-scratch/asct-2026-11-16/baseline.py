#!/usr/bin/env python3
"""baseline.py OUT.json: collect the numbers of the earlier work that the ASCT cross-check is compared with.
Sources: final8.json of the 8 MiB work (2026-11-15), the first kernel run (2026-11-13), FINDINGS.md of the
whole-chip work (2026-11-15), and the two vendor ASCT baseline archives of the Arm welcome kit."""
import collections
import json
import re
import statistics as st
import sys
import tarfile

C = '/home/jhan/workspace/titan/cache-perf/crb'
KIT = '/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/tools/asct/reports'
out = {}

# 1. one core: old read, new read (C and assembly) per size and CPU
d = json.load(open(f'{C}/new-test-kernel/tackle-8mb-analysis/final8.json'))
cells = collections.defaultdict(list)
for r in d['size_curve']['rows']:
    cells[(r['kernel'], r['cpu'], r['size_bytes'])].append(r)
single = {}
for (k, cpu, b), rows in sorted(cells.items()):
    single[f'{k}.{cpu}.{b}'] = {'median': st.median(r['median'] for r in rows), 'lo': min(r['p5'] for r in rows),
                                'hi': max(r['p95'] for r in rows), 'rows': len(rows),
                                'processes': sum(r['n'] for r in rows), 'steps': sorted({r['step'] for r in rows})}
out['single'] = single
# counters of step ZS (per line): cycles, L2 refills, L1 long misses, bus accesses
zs = collections.defaultdict(list)
for r in d['ZS']['rows']:
    zs[(r['kernel'], r['cpu'], r['size_bytes'])].append(r)
out['zs'] = {f'{k}.{cpu}.{b}': {f: st.median(r[f] for r in rows) for f in ('rate', 'cyc', 'r', 'l1_long_miss', 'l2_wb', 'bus_access')}
             for (k, cpu, b), rows in sorted(zs.items())}

# 2. the first run of 2026-11-13 (program bandwidth.c, CPU 0 and CPU 2, sizes 32K 1M 8M 1G)
first = collections.defaultdict(list)
cur = None
for line in open(f'{C}/results/kernels-20261113T181222Z/one-thread.csv'):
    m = re.match(r'-- binary (\S+) kernel (\S+) threads 1 cpus (\d+) bytes (\S+) ', line)
    if m:
        cur = m.groups()
        continue
    f = line.strip().split(',')
    if cur and len(f) > 6 and f[3].isdigit():
        first[(cur[0], cur[1], int(cur[2]), int(f[2]))].append(float(f[6]))
out['first'] = {f'{b}.{k}.{cpu}.{size}': {'median': st.median(v), 'lo': min(v), 'hi': max(v), 'n': len(v)}
                for (b, k, cpu, size), v in sorted(first.items()) if k == 'read'}

# 3. whole chip, 64+56, 256 MiB per thread (FINDINGS.md of 2026-11-15, section F2 and the question section)
out['chip'] = {
    'source': 'tmp/agent-scratch/w120-2026-11-15/FINDINGS.md',
    'loops': [
        # name, what, window depth in lines, total GB/s low, high, intervals
        ['old read', '4 ldp q + 8 vector adds per 128 B', '18-22', 465.5, 470.1, 22],
        ['new read (asmread)', '8 ldp q per 256 B, no other work', '36-40', 288.5, 309.8, 22],
        ['read_1pl', '4 ldr q per 256 B, one load per line', '156-164', 230.2, 235.0, 16],
        ['read_nop64', '8 ldp q + 64 nop', '28-32', 325.5, 333.9, 13],
        ['read_nop96', '8 ldp q + 96 nop', '20-24', 465.5, 470.6, 16],
        ['read_1pl_nop96', '4 ldr q + 96 nop', '24-28', 460.8, 460.9, 2],
        ['read_nop256', '8 ldp q + 256 nop', '8-12', 543.9, 549.0, 9],
    ],
    'first_run': {'old': [464.4, 466.7], 'new_c': [279.7, 304.1], 'asm': [271.1, 305.9], 'n': 6},
    'layouts': {  # oldread, asmread, read_nop96, read_nop128, one interval per cell
        '56+56': [534.8, 300.1, 538.1, 547.1], '64+0': [348.0, 348.4, 349.0, 351.0], '0+56': [318.0, 318.1, 319.2, 321.7]},
    'per_thread': {'slow': {'mesh0': [2.5, 2.75], 'mesh1': [2.25, 2.45]}, 'fast': {'mesh0': [4.27, 5.45], 'mesh1': [2.51, 2.78]}},
    'core_counters_per_line': {'bus_access': 2.08, 'l2d_cache_refill': 1.000, 'l2d_cache_hwprf': 1.000,
                               'cycles_slow': [66, 77], 'cycles_fast_mesh0': [35, 37]},
    'mesh_per_line': {  # slow asmread 299 GB/s | fast read_nop96 470 | fast oldread 468 (run w120-RC1)
        'hns_pocq_retry_all': [0.047, 0.072, 0.069], 'hns_qos_pocq_occupancy_all': [0.087, 0.121, 0.118],
        'hns_mc_retries_local_all': [0.0046, 0.043, 0.039], 'ccra_chidat_stalls': [0.21, 0.73, 0.73],
        'hns_cbusy11_all': [0.21, 1.49, 1.53], 'mxp_e_req_txflit_stall': [0.013, 0.167, 0.163],
        'mxp_e_dat_txflit_stall': [0.162, 0.344, 0.351], 'mxp_n_dat_txflit_stall': [0.119, 0.069, 0.073],
        'mxp_s_dat_txflit_stall': [0.027, 0.020, 0.025]},
    'one_thread_256M_cpu2': {'asmread': 35.7},
}

# 4. vendor ASCT baseline runs
vend = {}
for name in ('a0_numa2_ddr_7200', 'a1_numa2_ddr_8000'):
    t = tarfile.open(f'{KIT}/asct_run_results_{name}.tar.gz')
    base = f'asct_run_results_{name}/raw'
    def js(p):
        return json.load(t.extractfile(f'{base}/{p}'))
    bs = js('bandwidth-sweep/bandwidth-sweep.ubench.json')
    sweep = sorted((int(bs['sizes'][k]), bs['total_bandwidth_mbps'][k] / 1e3) for k in bs['sizes'])
    meta = js('bandwidth-sweep/metadata.json')
    txt = open(f'{KIT}/asct_run_output_{name}.txt').read()
    def grab(pat):
        m = re.search(pat, txt)
        return m.group(1).strip() if m else None
    ll = re.findall(r'^\s+(\d+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*$', txt.split('LOADED-LATENCY')[1].split('C2C-LATENCY')[0], re.M)
    pk = re.findall(r'^\s*(All Reads|3:1 Reads-Writes|2:1 Reads-Writes|1:1 Reads-Writes|2:1 Rd-Wr \(Non-Temporal\))\s+([0-9.]+)\s+([0-9.]+)', txt, re.M)
    cn = re.findall(r'^Node (\d)\s+([0-9.]+)\s+([0-9.]+)\s*$', txt.split('CROSS-NUMA-BANDWIDTH')[1].split('LATENCY-SWEEP')[0], re.M)
    vend[name] = {'sweep': sweep, 'cpu': meta['config']['target_cpus'], 'duration': meta['config']['duration'],
                  'binary': meta['benchmark_binary'], 'cpus': grab(r'CPUs:\s+(\d+)'), 'numa': grab(r'NUMA nodes:\s+(\d+)'),
                  'bios': grab(r'Version:\s+(AGI-CPU-CRB-\S+)'), 'speed': grab(r'Speed:\s+(\d+)'),
                  'channels': grab(r'# of channels:\s+(\d+)'), 'board': grab(r'Version:\s+(EVT\d)'),
                  'kernel_cfg': grab(r'Config:\s+(\S+)'), 'thp': grab(r'Transparent HP:\s+(\S+)'),
                  'nops': [[int(a), float(b), float(c)] for a, b, c, _ in ll],
                  'peak': {a: [float(b), float(c)] for a, b, c in pk},
                  'cross_numa': [[float(b), float(c)] for _, b, c in cn]}
out['vendor'] = vend
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print('single cells', len(single), 'zs cells', len(out['zs']), 'first', len(out['first']))
for k in ('oldread.2.8388608', 'asmread.2.8388608', 'read.2.8388608', 'oldread.41.1048576', 'asmread.41.1048576'):
    print(k, single.get(k))
print({k: v for k, v in out['first'].items() if '.2.' in k})
for n, v in vend.items():
    print(n, v['cpus'], v['numa'], v['bios'], v['speed'], v['channels'], v['board'], v['cpu'], v['peak'].get('All Reads'), v['cross_numa'], v['nops'][-3:])
    print('   sweep 1M 8M:', [x for x in v['sweep'] if x[0] in (1048576, 8388608, 4194304, 16777216, 33554432, 268435456, 1073741824, 32768)])
