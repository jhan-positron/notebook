import sys
P = "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
keys = [
 "The number of data channels at the pair port was not read from CRB",
 "An item that fits supports hypotheses 1 and 2 together",
 "Hypothesis 1, hypothesis 2 and the conversion each need their own test",
 "A run can reject hypothesis 1 only by a rate above 64 GB/s",
 "No run counted the share for two partner cores",
 "No run counted this share for two partner cores",
 "So the conversion cannot say whether the rate on the port is below or above 64 GB/s",
 "This report uses 8 MiB for the SLC tests and 1 GiB for the DRAM tests",
 "SLC uses 40 threads, one per pair, 3 MiB each",
 "256 MiB per thread, compiled loop",
 "asmwrite with 256 MiB per thread",
 "That is 32 B × 2.0 GHz = 64 GB/s",
 "The core was CPU 2 for the two counters of part 5 and CPU 0 for the count in writebw.csv",
 "A run of 2026-10-30 gave 0.81 for the second counter (est.)",
 "If both assumptions hold, 63.2 GB/s is also the rate through the port (est.)",
 "This report takes one transfer as 32 B",
 "Not checked against the hypotheses",
 "64.1 to 64.9 GB/s on the port (est.)",
 "A flit is one transfer unit on a mesh link or port",
 "CHI is the Coherent Hub Interface, the protocol of the mesh ports and links",
 "80.9 GB/s at 8 MiB and 72.5 GB/s at 1 GiB",
]
L = open(P, encoding="utf-8").read().split("\n")
for k in keys:
    hits = [i + 1 for i, l in enumerate(L) if k in l]
    print(hits, "|", k)
