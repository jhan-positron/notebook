# Recompute the derived numbers of draft answers A2.x from raw values read in the csv files.
# r8M-c2 xpport pair (writepath.csv lines 1046/1056 loop rows, 1051/1061 flit rows, 1052/1062 dtc rows)
fl_long, fl_short = 3666938605, 366049474
ns_long, ns_short = 2001035624, 200991088
by_long, by_short = 141960413184, 14159970304
el_long, el_short = 2.0001, 0.2000
dtc_long, dtc_short = 4002052091, 401963266
dtcns_long, dtcns_short = 2001032640, 200988184
flits = fl_long - fl_short; t = (ns_long - ns_short) / 1e9
lines = (by_long - by_short) / 64
print("flits", flits, "seconds", round(t, 6), "lines", lines)
print("flits per line", flits / lines, "share", flits / lines / 2)
print("port GB/s", flits / t * 32 / 1e9)
print("mesh Hz", (dtc_long - dtc_short) / ((dtcns_long - dtcns_short) / 1e9))
print("flits per mesh cycle (counted cycles)", flits / (dtc_long - dtc_short), " (at 2.0e9)", flits / t / 2.0e9)
print("loop GB/s long-short", (by_long - by_short) / (el_long - el_short) / 1e9, " long run 70.98")
print("port / loop", (flits / t * 32) / ((by_long - by_short) / (el_long - el_short)))
# L2 refills (lines 1092/1103, loop rows 1086/1097)
l2 = 1830294966 - 183229537; l2lines = (141725532160 - 14176747520) / 64
print("L2 refills per line", l2 / l2lines, l2)
share = flits / lines / 2
print()
for name, s in [("share 0.8265 (flits/2)", share), ("share 0.83", 0.83), ("share 0.826 (L2 refills)", l2 / l2lines), ("share 0.8275 (SLC accesses, CPU 0)", 0.8275), ("share 0.8217 (SLC accesses, 4 threads on CPUs 0-3)", 0.8217), ("share 0.81 (scaled run)", 0.81)]:
    vals = [77.51, 77.87, 78.26, 78.45, 77.5, 78.5, 78.0]
    print(f"{name:52s}", " ".join(f"{v}->{v*s:.2f}" for v in vals))
print()
print("78 x 0.17 =", 78 * 0.17, " 78 x 0.83 =", 78 * 0.83, " 78 x (1-share) =", 78 * (1 - share), " 77.51..78.45 x (1-share) =", 77.51 * (1 - share), 78.45 * (1 - share))
print("writes 8 MiB: 81.41 x 1.5241/2 =", 81.41 * 1.5241 / 2, " 82.05 ->", 82.05 * 1.5241 / 2, " 82.34 ->", 82.34 * 1.5241 / 2)
print("64 / (1.5241/2) =", 64 / (1.5241 / 2), " 64 / share =", 64 / share)
print("writes 1 GiB: 63.18 x 1.9982/2 =", 63.18 * 1.9982 / 2, " 63.19 ->", 63.19 * 1.9982 / 2, " 62.99 ->", 62.99 * 1.9982 / 2)
print("2 x 44.78 =", 2 * 44.78, " 113.25/2 =", 113.25 / 2, " 113.24/2 =", 113.24 / 2, " 63.18-62.99 =", 63.18 - 62.99, (63.18 - 62.99) / 62.99 * 100, "%")
print("63.18/64 =", 63.18 / 64, " 62.99/64 =", 62.99 / 64, " 63.19/64 =", 63.19 / 64, " 56.6/64 =", 56.62 / 64)
print("1 flit x 32 B x 2.0e9 =", 32 * 2.0e9 / 1e9, "GB/s")
print("w1G-c2 bus writes/s", 3553584520 / 1.8094, "per mesh cycle", 3553584520 / 1.8094 / 2e9, "GB/s", 3553584520 / 1.8094 * 32 / 1e9)
print("non-partner totals: 126.59/78.26 =", 126.59 / 78.26, " 134.11/78.26 =", 134.11 / 78.26, " 129.71/77.51 =", 129.71 / 77.51, "132.02/77.87", 132.02 / 77.87)
print("1 GiB / 128 MiB =", (1 << 30) / (128 << 20), " 2 x 1 GiB in GiB =", 2 * (1 << 30) / (1 << 30), " bytes_per_thread 1073741824 == 2^30:", 1073741824 == 1 << 30, " 8388608 == 8 MiB:", 8388608 == 8 << 20)
