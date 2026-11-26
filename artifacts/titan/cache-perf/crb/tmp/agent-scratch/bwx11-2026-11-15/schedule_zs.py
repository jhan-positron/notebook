#!/usr/bin/env python3
"""schedule_zs.py - step ZS of round 4 ("size dose with counters"), added by hand after schedule11.py.
One trial per process: 20 windows of 300 ms with the counters read (binary bwx11).
Kernels asmread and oldread at 13 sizes from 1 MiB to 32 MiB, 1 process per kernel, size and CPU = 52 per session.
Writes sched11/s<session>/ZS.tsv, ZS.bin and ZS/NNNN.plan beside this script. Deterministic (seed in ZS.seed)."""
import os, random
HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = [1048576, 1572864, 2097152, 2621440, 3145728, 4194304, 5242880, 6291456, 8388608, 12582912, 16777216, 25165824, 33554432]
KERNELS = ["asmread", "oldread"]
EVENTS = "cpu_cycles=0x11,l1d_cache_lmiss_rd=0x39,l2d_cache_refill=0x17,l2d_cache_wb=0x18,bus_access=0x19,l2d_cache_lmiss_rd=0x4009"
BASE = 2026111504
def main():
    total = 0
    for session, cpus in ((1, (2, 41)), (2, (41, 2))):
        seed = BASE + session
        rng = random.Random(seed)
        sdir = os.path.join(HERE, "sched11", "s%d" % session)
        pdir = os.path.join(sdir, "ZS")
        os.makedirs(pdir, exist_ok=True)
        rows = []
        for cpu in cpus:
            cells = [(k, s) for k in KERNELS for s in SIZES]
            rng.shuffle(cells)
            for k, s in cells:
                idx = len(rows)
                plan = "%04d.plan" % idx
                with open(os.path.join(pdir, plan), "w") as f:
                    f.write("# bwx8-plan v1\n")
                    f.write("# step=ZS session=%d cpu=%d bytes=%d proc=%d kernel=%s size=%d seed=%d test=0\n" % (session, cpu, s, idx, k, s, seed))
                    f.write("# trial cond rep prev pfx pred tgt nwin win_ms count bins\n")
                    f.write("0 K=%s|S=%d|count=read 1 - - - %s@%d 20 300 read 0\n" % (k, s, k, s))
                args = "--trial --cpus %d --bytes %d --plan sched11/s%d/ZS/%s --pmu-type 11 --events %s" % (cpu, s, session, plan, EVENTS)
                rows.append((idx, "%s-%d-cpu%d" % (k, s, cpu), cpu, s, plan, args))
        with open(os.path.join(sdir, "ZS.tsv"), "w") as f:
            f.write("idx\ttag\tcpu\tbytes\tplan\targs\n")
            for r in rows:
                f.write("\t".join(str(x) for x in r) + "\n")
        with open(os.path.join(sdir, "ZS.bin"), "w") as f:
            f.write("bwx11\n")
        with open(os.path.join(sdir, "ZS.seed"), "w") as f:
            f.write("%d\n" % seed)
        print("ZS session %d: %d processes, nominal kernel work %.1f s" % (session, len(rows), len(rows) * 6.0))
        total += len(rows)
    assert total == 104
main()
