#!/usr/bin/env python3
"""Recompute, from the raw result files, the numbers of the sentences that the third pass of
2026-11-12 changed in the report, and the numbers that section 11 of the record cites for them.
Every block prints the file lines that it used. An assert fails if a number of the report
does not follow from the raw rows.
Usage: recheck_third_pass.py <crb dir> <report.html>"""
import re, sys
from decimal import Decimal, ROUND_HALF_UP

CRB, REPORT = sys.argv[1], sys.argv[2]
R = CRB + "/results/"


def lines(p):
    return open(R + p, encoding="utf-8", errors="replace").read().split("\n")


def r1(x):
    """round to one decimal, halves up, on the decimal text of the file"""
    return str(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def runs(L, kernels, nbytes, threads):
    """one entry per run: (header, [(line, rep, total, slowest thread, fastest thread)], (line of the best row, best total))"""
    label, cur, out = None, [], []
    for i, l in enumerate(L, 1):
        if l.startswith("--"): label = l
        f = l.split(",")
        if len(f) >= 10 and f[0] in kernels and f[1] == threads and f[2] == nbytes:
            if f[3] == "best":
                out.append((label, cur, (i, float(f[6])))); cur = []
            else:
                cur.append((i, f[3], float(f[6]), float(f[7]), float(f[8])))
    return out


rep = open(REPORT, encoding="utf-8").read().split("\n")
txt = lambda n: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", rep[n - 1]))
pr = lines("followup-20261030T194205Z/pair.csv"); am = lines("followup-20261030T194205Z/asm.csv"); bw = lines("20261030T193108Z/bandwidth.csv")
wp = lines("sudo-20261102T211150Z/writepath.csv")
M8, G1 = "8388608", "1073741824"

print("== 1. Line 213: rates by thread, two readers at 8 MiB, best repetition of each run")
part, diff = [], []
for name, L, kern in (("pair.csv", pr, ("read",)), ("asm.csv", am, ("asmread",)), ("bandwidth.csv", bw, ("read",))):
    for label, reps, best in runs(L, kern, M8, "2"):
        top = max(r[2] for r in reps)
        bestreps = [r for r in reps if r[2] == top]
        lo, hi = min(r[3] for r in bestreps), max(r[4] for r in bestreps)
        alo, ahi = min(r[3] for r in reps), max(r[4] for r in reps)
        cpus = (label or "main sweep, cpus 0-119").replace("-- ", "")
        if name == "pair.csv":
            a, b = [int(x) for x in cpus.replace("cpus ", "").split(",")]
            partners = (b == a + 1 and a % 2 == 0)
        else:
            partners = "0-118:2" not in cpus
        (part if partners else diff).append((lo, hi, alo, ahi, len(reps)))
        print(f"   {name:14s} {cpus[:46]:46s} best {best[1]:6.2f} (line {best[0]}); best repetition at line(s) {[r[0] for r in bestreps]}: "
              f"{lo:.2f} to {hi:.2f}; all {len(reps)} repetitions: {alo:.2f} to {ahi:.2f}; {'partners' if partners else 'different pairs'}")
d = (min(x[0] for x in diff), max(x[1] for x in diff), min(x[2] for x in diff), max(x[3] for x in diff), sum(x[4] for x in diff))
p = (min(x[0] for x in part), max(x[1] for x in part), min(x[2] for x in part), max(x[3] for x in part), sum(x[4] for x in part))
print(f"   different pairs: {len(diff)} runs, best repetitions {d[0]:.2f} to {d[1]:.2f} GB/s, all {d[4]} repetitions {d[2]:.2f} to {d[3]:.2f}")
print(f"   partners:        {len(part)} runs, best repetitions {p[0]:.2f} to {p[1]:.2f} GB/s, all {p[4]} repetitions {p[2]:.2f} to {p[3]:.2f}")
assert len(diff) == 7 and len(part) == 5
assert f"read {r1(d[0])} to {r1(d[1])} GB/s (seven runs, best repetition of each)" in txt(213)
assert f"read {r1(p[0])} to {r1(p[1])} GB/s (five runs, best repetition of each)" in txt(213)

print("== 2. Lines 121 and 429: runs with two partner cores (CPUs 0 and 1) that were not converted")
want = {("bandwidth.csv", "write", M8): "75.6", ("bandwidth.csv", "write", G1): "63.2", ("bandwidth.csv", "copy", M8): "77.9",
        ("bandwidth.csv", "copy", G1): "72.4", ("bandwidth.csv", "read", G1): "52.6", ("asm.csv", "asmcopy", M8): "80.9",
        ("asm.csv", "asmcopy", G1): "72.5", ("asm.csv", "asmread", G1): "56.7", ("pair.csv", "read", G1): "52.6"}
for (name, kern, nb), shown in want.items():
    L = {"bandwidth.csv": bw, "asm.csv": am, "pair.csv": pr}[name]
    rr = runs(L, (kern,), nb, "2")
    if name == "pair.csv": rr = [x for x in rr if x[0].startswith("-- cpus 0,1 ")]   # header "-- cpus 0,1 1G (DRAM regime)"
    assert len(rr) == 1, (name, kern, nb, len(rr))
    label, reps, best = rr[0]
    print(f"   {name:14s} {kern:8s} {'8 MiB' if nb == M8 else '1 GiB'}: best {best[1]:.2f} GB/s at line {best[0]} -> {r1(best[1])} (report: {shown})")
    assert r1(best[1]) == shown
for s in ("gave 75.6 GB/s at 8 MiB and 63.2 GB/s at 1 GiB", "gave 80.9 GB/s at 8 MiB and 72.5 GB/s at 1 GiB", "gave 77.9 GB/s at 8 MiB and 72.4 GB/s at 1 GiB",
          "gave 52.6 GB/s with the loop compiled from C and 56.7 GB/s with the asm loop"):
    assert s in txt(121), s
for s in ("gave 77.9 GB/s at 8 MiB and 72.4 GB/s at 1 GiB", "They gave 52.6 GB/s with the loop compiled from C and 56.7 GB/s with the asm loop"):
    assert s in txt(429), s
one = {nb: runs(bw, ("write",), nb, "1")[0][2] for nb in (M8, G1)}
print(f"   bandwidth.csv  write, one thread: {one[M8][1]:.2f} GB/s at 8 MiB (line {one[M8][0]}), {one[G1][1]:.2f} GB/s at 1 GiB (line {one[G1][0]})")
assert r1(one[M8][1]) == "44.8" and r1(one[G1][1]) == "44.8" and "one writer alone wrote 44.8 GB/s at 8 MiB and at 1 GiB (CPU 0, 2026-10-30)" in txt(289)

print("== 3. Line 289: write rates of part 5 by case (writepath.csv)")
case, rows = None, {}
for i, l in enumerate(wp, 1):
    if l.startswith("--"):
        q = l.split(); case = (q[1], q[2])
    f = l.split(",")
    if len(f) >= 10 and f[0].startswith("asm") and f[3] != "best":
        rows.setdefault(case, []).append((i, float(f[5]), float(f[6]), float(f[7]), float(f[8]), float(f[9]), int(f[4])))
res = {}
for (c, k), rs in rows.items():
    lo, hi = min(rs, key=lambda r: r[2]), max(rs, key=lambda r: r[2]); tlo, thi = min(rs, key=lambda r: r[3]), max(rs, key=lambda r: r[4])
    res[(c, k)] = (lo[2], hi[2], tlo[3], thi[4], min(r[5] for r in rs), max(r[5] for r in rs))
    print(f"   {c:13s} {k:5s} {len(rs)} runs of {rs[0][1]:.1f} s: total {lo[2]:.2f} (line {lo[0]}) to {hi[2]:.2f} (line {hi[0]}); "
          f"by thread {tlo[3]:.2f} (line {tlo[0]}) to {thi[4]:.2f} (line {thi[0]}); average thread {res[(c, k)][4]:.2f} to {res[(c, k)][5]:.2f}")
t289 = txt(289)
a = res[("w8M-c2", "long")]; assert f"CPU 2 wrote {r1(a[0])} to {r1(a[1])} GB/s in the nine runs of 2 s" in t289
a = res[("w8M-c2", "short")]; assert f"The nine runs of 0.2 s of one writer gave {r1(a[0])} to {r1(a[1])} GB/s" in t289
a = res[("w8M-c2c3", "long")]; assert f"the pair wrote {r1(a[0])} to {r1(a[1])} GB/s" in t289
a = res[("w8M-c2c4", "long")]; assert f"each of the two writers writes {a[2]:.2f} to {a[3]:.2f} GB/s" in t289
a = res[("w8M-c2c4c6c8", "long")]
assert "wrote 228 to 230 GB/s" in t289 and 228 <= a[0] and a[1] <= 230 and "57 GB/s on average (55 to 59 GB/s by writer)" in t289
assert 55 <= a[2] and a[3] <= 59 and round(a[4]) == 57 and round(a[5]) == 57

print("== 4. Counts of part 5: the 2 s run minus the 0.2 s run (count, counting time in s, per second)")


def cnt(n):
    f = wp[n - 1].split(",")   # count,,event,counting time in ns,percent of the run,, (the event name can hold commas)
    return int(f[0]), int(f[-4]) / 1e9, ",".join(f[2:-4]), f[-3]


def dif(a, b, what):
    (c0, t0, e0, p0), (c1, t1, e1, p1) = cnt(a), cnt(b)
    assert e0 == e1 and p0 == p1 == "100.00", (a, b, e0, e1, p0, p1)
    print(f"   lines {a} and {b}: {what}: {c1:,} - {c0:,} = {c1 - c0:,} in {t1 - t0:.4f} s = {(c1 - c0) / (t1 - t0):.4g} per second (2 s run alone: {c1 / t1:.4g})   [{e0[:44]}]")
    return c1 - c0, t1 - t0


def bytes_row(n):
    """bytes of the run that holds counter line n: the nearest loop row above it"""
    k = n
    while not (wp[k - 1].startswith("asm") and wp[k - 1].split(",")[3] == "0"): k -= 1
    assert n - k < 12, (n, k)
    return int(wp[k - 1].split(",")[4])


l1r, _ = dif(201, 212, "w8M-c2, L1 refills for writes"); l2r, _ = dif(203, 214, "w8M-c2, L2 refills for writes")
bwr, tb = dif(204, 215, "w8M-c2, bus writes of CPU 2")
l1w, _ = dif(180, 191, "w8M-c2, L1 write-backs"); l2w, _ = dif(183, 194, "w8M-c2, L2 write-backs")
# lines written in the two counter sets of case w8M-c2: bytes of the 2 s run minus bytes of the 0.2 s run, divided by 64
n2 = (bytes_row(212) - bytes_row(201)) / 64; n1 = (bytes_row(191) - bytes_row(180)) / 64
print(f"   w8M-c2: lines written {n2:,.0f} (set core2) and {n1:,.0f} (set core1); per line: L1 refills for writes {l1r / n2:.6f}, L2 refills for writes {l2r / n2:.6f}, "
      f"bus writes {bwr / n2:.4f}, L1 write-backs {l1w / n1:.6f}, L2 write-backs {l2w / n1:.6f}")
assert l1r / n2 < 0.0005 and l2r == 0 and l1w / n1 < 0.0005 and 0.0005 <= l2w / n1 < 0.001
st = sum(dif(n, n + 10, "w8M-c2, credit-stall cycles of one link")[0] for n in (118, 119, 120, 121))
cy, tcy = dif(122, 132, "w8M-c2, mesh cycles")
print(f"   w8M-c2: {st:,} credit-stall cycles on the four links in {cy:,} mesh cycles = {100 * st / cy:.5f} %; {st / tcy:.3g} per second")
assert st == 37976 and cy == 3599908867
s2, t2 = dif(628, 637, "w8M-c2c4, data stalls of the home nodes of mesh 0")
s4, t4 = dif(810, 819, "w8M-c2c4c6c8, data stalls of the home nodes of mesh 0"); s4b, _ = dif(811, 820, "w8M-c2c4c6c8, data stalls of the home nodes of mesh 1")
c4 = sum(dif(n, n + 10, "w8M-c2c4c6c8, credit-stall cycles of one link")[0] for n in (846, 847, 848, 849))
n4 = (bytes_row(819) - bytes_row(810)) / 64
print(f"   w8M-c2c4c6c8: {c4:,} credit-stall cycles on the four links; lines written {n4:,.0f}; data stalls per line: mesh 0 {s4 / n4:.5f}, both meshes {(s4 + s4b) / n4:.5f}")
b1, tb1 = dif(386, 397, "w1G-c2, bus writes of CPU 2")
assert s2 == 3116815 and s4 == 35180359 and c4 == 1252463 and f"{s4 / n4:.3f}" == "0.005"
assert f"{s2 / t2:.2g}" == "1.7e+06" and f"{s4 / t4:.2g}" == "2e+07" and f"{bwr / tb:.3g}" == "1.68e+09" and f"{b1 / tb1:.3g}" == "1.96e+09"
for s in ("1.7 × 10 6 data stalls per second with two busy ports and 2.0 × 10 7 per second with four busy ports",
          "the home nodes of mesh 0 show 0.005 data stalls per line written", "0.000 refills for writes per line and at most 0.001 write-backs per line"):
    assert s in t289, s

print("== 5. Sources in square brackets in the three texts")
for n in (214, 289, 380):
    src = re.findall(r"\[(results/[^\]]*)\]", rep[n - 1])
    print(f"   line {n}: {len(src)} sources:", src)
print("all checks passed")
