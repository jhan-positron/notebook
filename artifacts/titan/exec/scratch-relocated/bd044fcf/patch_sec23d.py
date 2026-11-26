#!/usr/bin/env python3
"""Section 2.3: the question in one table (sequential read against the random read chain, CPU 2), asked by Jibin 2026-11-08."""
path = "/home/jhan/workspace/titan/cache-perf/asimov/gen_perf_core.py"
s = open(path).read()
def sub(old, new):
    global s
    assert s.count(old) == 1, ("sub", old[:70], s.count(old)); s = s.replace(old, new)
sub('''    ratio = lambda name: next(v for n, v in groups if n == name)
''', '''    ratio = lambda name: next(v for n, v in groups if n == name)
    # the question in one table: sequential read against the random read chain, CPU 2, 2 and 32 MiB
    e2, c2 = RV[("read", 2097152)]["e"]["E"], RV[("read", 2097152)]["e"]["C"]
    ch_gbs = lambda R, sz: 64 / R[(sz, "fresh")]["ns"]
    q_rows = []
    for sz, e_, c_ in ((33554432, e32, c32), (2097152, e2, c2)):
        q_rows.append([f"sequential read {kib(sz)}, GB/s", f"{ONE3[sz]['read']:.1f}", f"{ONE1[sz]['read']:.1f}", f"{ONE1[sz]['read'] / ONE3[sz]['read']:.2f}",
                       f"{c_['l2d_refill']:.2f} / {e_['l2d_refill']:.2f} (boots C / E)", f"{c_['l3d_refill_rd']:.4f} / {e_['l3d_refill_rd']:.4f} (boots C / E)"])
        q_rows.append([f"random read chain {kib(sz)}, GB/s", f"{ch_gbs(R3, sz):.2f}", f"{ch_gbs(R1, sz):.2f}", f"{ch_gbs(R1, sz) / ch_gbs(R3, sz):.2f}",
                       f"{R3[(sz, 'fresh')]['l2']:.2f} / {R1[(sz, 'fresh')]['l2']:.2f}", f"{R3[(sz, 'fresh')]['l3']:.2f} / {R1[(sz, 'fresh')]['l3']:.2f}"])
    q_rows.append(["write 32 MiB, GB/s", f"{ONE3[33554432]['write']:.1f}", f"{ONE1[33554432]['write']:.1f}", f"{ONE1[33554432]['write'] / ONE3[33554432]['write']:.2f}", "no counters on any boot", "no counters on any boot"])
    t_q = table(["Row, CPU 2", "Run 3 (L3 off)", "F1 (L3 on)", "Ratio, F1 over run 3", "L2 refills per line or per load (L3 off / L3 on)", "L3 refills from the mesh, event 0xA2 (L3 off / L3 on)"], q_rows,
                note=f"Best rep of each row, GB = 1e9 bytes. The chain rows are 64 bytes per load divided by the measured ns per load ({R3[(33554432, 'fresh')]['ns']:.1f} and {R1[(33554432, 'fresh')]['ns']:.1f} ns at 32 MiB, {R3[(2097152, 'fresh')]['ns']:.1f} and {R1[(2097152, 'fresh')]['ns']:.1f} at 2 MiB). "
                     "Event 0xA2 is the Arm PMU event L3D_CACHE_REFILL_RD: a read that the L3 could not serve and that brought the line in from outside the cluster, that is from the mesh (SLC, OCM or DRAM). It is counted per load on the chain rows and per 64-byte line on the stream rows. "
                     f"On the streams it reads near zero on both boots while the L2 refills read about one per line. This page's reading, not a measurement: the event counts the demand reads that miss the L3 and not the lines the hardware prefetcher brings in; the streams run on the prefetcher ({c32['l1d_refill_hwprf']:.2f} and {e32['l1d_refill_hwprf']:.2f} L1 prefetcher refills per line at 32 MiB) and the chains do not (F1's 32 MiB chain: {R1[(33554432, 'fresh')]['e']['l1d_refill_hwprf']:.2f} per load; run 3's latency rows did not count the prefetch events). "
                     "Run 3's bandwidth rows carry no core counters, so the stream refill columns are boots C (L3 off) and E (L3 on), the same build with the L3 as the one change; the chain columns are run 3 and F1 [bandwidth-dram-1core.csv and latency-dram-large.csv of 004 and 011; bandwidth-read-prefetch.csv of 007 and 010].")
''')
sub('''<ul>
<li><b>Hypotheses.</b>''', '''<ul>
<li><b>The question in one table.</b> The rows below put the sequential read (k_read: independent loads in address order, which the hardware prefetcher follows) beside the random read chain of the same footprint (one dependent load at a time, in a random cycle over the lines), both on CPU 2, with the write stream. The chain's rate did not change, and every one of its loads still comes from the mesh on F1. The sequential read moved {ONE1[33554432]['read'] / ONE3[33554432]['read']:.1f} times at 32 MiB, a footprint {33554432 // 262144} times the L3, with the same refills per line. One DRAM load costs {R1[(33554432, 'fresh')]['ns']:.1f} ns on both boots, so the 32 MiB stream overlaps about {R3[(33554432, 'fresh')]['ns'] / (64 / ONE3[33554432]['read']):.1f} loads est. with the L3 off and about {R1[(33554432, 'fresh')]['ns'] / (64 / ONE1[33554432]['read']):.0f} est. with it on. How many reads the cluster keeps in flight is what changed, and why is what the hypotheses below have to explain.</li>
</ul>
{t_q}
<ul>
<li><b>Hypotheses.</b>''')
open(path, "w").write(s); print("patch_sec23d ok")
