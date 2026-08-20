#!/usr/bin/env python3
"""Dump hugetlbfs-backed VMA ranges and their PFNs for a pid.

Usage: sudo python3 pagemap_dump.py <pid>
Output lines: <vma_start_hex> <vma_end_hex> <path> <pfn0> <pfn1> ...
PFNs are sampled once per 1 GiB huge page (offset 0 of each page).
"""
import struct, sys

pid = sys.argv[1]
GB = 1 << 30
PAGE = 4096

vmas = []
for line in open(f"/proc/{pid}/maps"):
    parts = line.split()
    if len(parts) >= 6 and ("hugepages" in parts[5] or "hugetlbfs" in parts[5] or "anon_hugepage" in parts[5]):
        lo, hi = (int(x, 16) for x in parts[0].split("-"))
        vmas.append((lo, hi, parts[5]))

with open(f"/proc/{pid}/pagemap", "rb") as pm:
    for lo, hi, path in vmas:
        pfns = []
        addr = lo
        while addr < hi:
            pm.seek(addr // PAGE * 8)
            data = pm.read(8)
            if len(data) == 8:
                ent = struct.unpack("<Q", data)[0]
                pfns.append(ent & ((1 << 55) - 1) if ent >> 63 else 0)
            else:
                pfns.append(-1)
            addr += GB
        print("%x %x %s %s" % (lo, hi, path, " ".join(str(p) for p in pfns)))
