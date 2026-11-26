#!/usr/bin/env python3
"""notes.py FACTS.json BASELINE.json OUT.json: the text blocks of ASCT-cross-check.html.
Every number in the text is taken from FACTS or BASELINE by this script, so the text cannot drift from the data.
Blocks that depend on what the data shows are written in dyn_notes.py (imported below) after the runs."""
import json
import sys

F = json.load(open(sys.argv[1]))
B = json.load(open(sys.argv[2]))
MI = 1 << 20
N = {}


def p(*s):
    return '<p>' + ' '.join(s) + '</p>'


def ul(*items):
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def ref(*n):
    return ' '.join(f'[Ref{i}]' for i in n)


first = B['first']
g8 = (first['bw_new.read.2.8388608']['median'] / first['bw_old.read.2.8388608']['median'] - 1) * 100
g1 = (first['bw_new.read.2.1048576']['median'] / first['bw_old.read.2.1048576']['median'] - 1) * 100
L = {r[0]: r for r in B['chip']['loops']}
old, new = L['old read'], L['new read (asmread)']

N['words'] = [ul(
    '<b>CRB</b>: the Arm Phoenix Reference Server in our lab, 128 cores (Arm part 0xd83), one NUMA node.',
    '<b>ASCT</b>: the Arm System Characterization Tool, version 0.7.1+77461b3. It is Arm\'s tool for memory latency and bandwidth tests.',
    '<b>read loop</b>: the few instructions that a benchmark repeats to read a buffer. This report compares three read loops.',
    '<b>old read</b>: the read loop of our benchmark before 2026-11-13. It loads every byte and adds the loaded values.',
    '<b>new read</b>: the read loop of our benchmark since 2026-11-13. It loads every byte and does no other work. '
    'Its values here are those of the assembly form (<code>asmread</code>) unless a line says otherwise.',
    '<b>ASCT read</b>: the read loop of ASCT (function <code>my_read_no_nops_rep_64b</code>). It loads 8 bytes of each 64-byte line.',
    '<b>line</b>: one 64-byte cache line. Caches and memory move data in lines.',
    '<b>L1, L2</b>: the two private caches of a core, 64 KiB and 2 MiB.',
    '<b>SLC</b>: the system-level cache, 128 MiB, shared by all cores. Linux calls it L3.',
    '<b>mesh</b>: the on-chip network that links cores, SLC and memory ports. CRB has two meshes: mesh 0 holds CPUs 0 to 63, mesh 1 holds CPUs 64 to 127.',
    '<b>64+56</b>: 64 threads on CPUs 0 to 63 and 56 threads on CPUs 64 to 119, one thread per CPU, 256 MiB per thread.',
    '<b>injected NOPs (N)</b>: an ASCT option (<code>--bw-fine-delay N</code>). ASCT then runs an empty loop of N rounds after each load. ASCT calls the rounds NOPs. One round has 3 instructions.',
    '<b>window</b>: the instructions that a core holds in flight at one moment. A read loop with few instructions per line puts many lines into one window.',
    '<b>prefetcher</b>: the part of a core that requests lines before the program asks for them.',
    '<b>core counter</b>: a hardware counter inside a core, for example cycles or cache refills. ASCT reads them through its capture code named dietperf.',
    '<b>probe build</b>: the variant of the ASCT benchmark binary that contains the capture code.',
    '<b>mesh counter</b>: a hardware counter of the mesh (Linux units <code>arm_cmn_0</code> and <code>arm_cmn_1</code>). Reading it needs root.',
    '<b>L2 refill</b>: one line that enters L2 from the SLC or from memory. The counter is <code>l2d_cache_refill</code>.',
    '<b>long-latency miss</b>: a load that had to wait for its line. A load whose line was prefetched in time is not counted.',
    '<b>L1 prefetches, L2 prefetches</b>: the counts of the counters <code>l1d_cache_hwprf</code> and <code>l2d_cache_hwprf</code>. One count is one request of the hardware prefetcher of that cache.',
    '<b>busy level</b>: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. The core counts the answers of each level (counters <code>l2_chi_cbusy0</code> to <code>l2_chi_cbusy3</code>).',
    '<b>hop</b>: one step from one crosspoint of the mesh to the next.',
    '<b>slow state</b>: the condition at 64+56 in which a thread reads about 2 GB/s. In the fast condition it reads about 5 GB/s.',
    '<b>lower bound of a total</b>: all bytes that the threads of one process read, divided by the time of the slowest thread. ASCT itself adds the rates of the threads.',
    '<b>huge page</b>: a memory page of 2 MiB or more. A normal page has 4 KiB. With transparent huge pages the kernel gives huge pages to a program that did not ask for them.',
    '<b>P-A1, R-A3, D-A2 and similar names</b>: the predictions (P), rules (R) and descriptive items (D) of the decisions file. They were written before the data that they judge.',
    '<b>part U, N, C, NC</b>: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.',
    '<b>marker file</b>: the file <code>/tmp/positron-perf.RUNNING</code> on CRB. The other user of CRB creates it while his tests run.',
    '<b>process</b>: one start of the ASCT benchmark binary. It prints one rate.',
    '<b>median, range</b>: the middle value of the processes of a cell, and the smallest to the largest value.',
    '<b>GB</b>: 10<sup>9</sup> bytes. <b>KiB, MiB, GiB</b>: 2<sup>10</sup>, 2<sup>20</sup>, 2<sup>30</sup> bytes.',
    '<b>Arm reference machines A0 and A1</b>: the two machines of the vendor baseline runs in the Arm welcome kit. They have firmware v0.9.0 and two NUMA nodes.',
    '<b>NUMA node</b>: a group of cores and the memory that the firmware declares as local to them.',
    '<b>block</b>: a time window that Jeremy Conner reserves on CRB in Slack channel #phoenix-crb.',
    '<b>est.</b>: an estimate, not a measurement.')]

N['asked'] = [
    p('Two results of our own read benchmark on CRB are not understood.'),
    ul(f'<b>Question 1, 8 MiB.</b> The new read loop is {g1:.1f} % faster than the old read loop at 1 MiB on one core. '
       f'At 8 MiB the gain was {g8:.2f} % in the first run of 2026-11-13 {ref(1)}. The runs of 2026-11-15 found 0.2 to 6.7 % {ref(2)}.',
       f'<b>Question 2, whole chip.</b> At 64+56 threads the old read loop reads {old[3]:.1f} to {old[4]:.1f} GB/s in total. '
       f'The new read loop reads {new[3]:.1f} to {new[4]:.1f} GB/s {ref(3)}.'),
    p('The request for this work: repeat both tests with ASCT on the same cores and sizes, compare the rates with the old and the new loop, '
      'and capture the counters and registers that ASCT can reach, with a focus on the prefetchers.')]

N['cap_path'] = ('<b>Figure 1.</b> The ASCT front end fixes its core and needs huge pages. So the runs called the ASCT benchmark binary directly, '
                 'with the command line that the front end builds.')
N['cap_loops'] = ('<b>Figure 2.</b> The ASCT loop loads one eighth of the bytes that it counts. Its rate is comparable with ours only when the '
                  'transfer of lines is the limit, not the work inside the core.')

N['refs'] = [
    '[Ref1] First run of the new loops, 2026-11-13: <code>crb/results/kernels-20261113T181222Z/one-thread.csv</code> and <code>threads120.csv</code>. The gain uses the medians of 6 repetitions on CPU 2.',
    '[Ref2] The 8 MiB work of 2026-11-15: <code>crb/new-test-kernel/tackle-8mb-results.md</code>. Numbers from <code>tackle-8mb-analysis/final8.json</code>, blocks <code>size_curve</code>, <code>ZS</code>, <code>evict</code> (step <code>ZC</code>) and <code>prefetch</code> (step <code>YC</code>).',
    '[Ref3] The whole-chip work of 2026-11-15: <code>crb/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md</code>, sections F2 to F4. Report <code>crb/new-test-kernel/whole-chip-read-drop.html</code>.',
    '[Ref4] ASCT source, tarball <code>~/asct/asct-0.7.1+77461b3/asct-0.7.1+77461b3.tar.gz</code> on CRB: <code>src/core/recipes/impl/memory_load_latency.py</code> and <code>recipe_benchmark_base.py</code> (choice of CPUs), <code>src/core/recipes/configuration/schema.py</code> (user settings), <code>src/core/benchspec/memory_benchspec.py</code> (command line).',
    '[Ref5] ASCT benchmark source in the same tarball: <code>extern/infra-microbenchmarks/loaded-latency/bandwidth.c</code> (read loops, timing), <code>alloc.c</code> (buffer), <code>main.c</code> (total).',
    '[Ref6] ASCT counter and register code in the same tarball: <code>extern/dietperf/dietperf.h</code>, <code>src/core/asct_pmu_api.py</code>, <code>src/core/asct_env.py</code>, <code>src/core/config/ubench.json</code>, <code>src/core/recipes/impl/sysreg.py</code>, <code>src/core/recipes/impl/cmn.py</code>, <code>src/lib/cmn-tools/cmn_api.py</code>.',
    '[Ref7] ASCT manual, <code>~/asct/asct-0.7.1+77461b3/asct_docs/index.html</code> on CRB, section "Huge-page requirements for runs without root privileges".',
    '[Ref8] Decisions and predictions of this work, written before the first run: <code>crb/tmp/agent-scratch/asct-2026-11-16/DECISIONS.md</code>.',
    '[Ref9] Run scripts of this work: <code>crb/tmp/agent-scratch/asct-2026-11-16/crb/</code> (<code>prep.sh</code>, <code>run_single.sh</code>, <code>run_chip.sh</code>, <code>run_mesh.sh</code>, event lists).',
    '[Ref10] Results of this work: folders <code>crb/results/asct-*</code>. All numbers of this page are in <code>crb/tmp/agent-scratch/asct-2026-11-16/asct.json</code> and <code>facts.json</code> (built by <code>analyze.py</code> and <code>facts.py</code>).',
    '[Ref11] Vendor baseline runs: <code>vendor-resources/ARM/agi-cpu-welcome-kit/tools/asct/reports/</code> (two console outputs and two result archives). The file <code>raw/bandwidth-sweep/bandwidth-sweep.ubench.json</code> of each archive holds the one-core sweep.',
    '[Ref12] CRB machine record: <code>crb/inspection-record-2026-10-30.md</code> (firmware, NUMA) and <code>crb/results/dmidecode-t17-2026-10-30.txt</code> (memory modules).',
    '[Ref13] Rules for the shared machine: <code>crb/jeremy-plan-constraints-2026-10-30.md</code>. Block announcement in Slack #phoenix-crb of 2026-11-16 16:14 UTC.',
    '[Ref14] Positions of the cores on the mesh: <code>crb/results/sudo-20261102T054936Z/core-positions.json</code> and <code>crb/results/cmn-map.txt</code>.',
]

import dyn_notes  # noqa: E402  (the blocks written after the runs)
dyn_notes.fill(N, F, B, p, ul, ref)

need = ['subtitle', 'short', 'words', 'asked', 'how', 'loops', 'q1_intro', 'q1_rates', 'q1_cost_intro', 'q1_cost', 'q1_pf_intro', 'q1_pf',
        'q1_pad_intro', 'q1_pad', 'q1_mesh_intro', 'q1_mesh', 'q1_verdict', 'q2_intro', 'q2_rates', 'q2_layouts', 'q2_cnt_intro', 'q2_cnt',
        'q2_mesh_intro', 'q2_mesh', 'q2_verdict', 'vendor', 'vendor2', 'capture', 'runs', 'open', 'refs', 'cap_path', 'cap_loops', 'cap_size',
        'cap_fall', 'cap_cost', 'cap_prefetch', 'cap_pad', 'cap_chip', 'cap_nops', 'cap_threads', 'mesh_tag_names', 'mesh_chip_tags',
        'mesh_single_tags', 'peer_counters']
missing = [k for k in need if k not in N]
if missing:
    sys.exit(f'notes blocks missing: {missing}')
blob = json.dumps(N)
for bad in ('TODO', 'PLACEHOLDER', 'FAKE'):
    if bad in blob:
        sys.exit(f'notes contain the marker {bad}')
json.dump(N, open(sys.argv[3], 'w'), indent=1)
print('notes written', len(N), 'blocks')
