#!/usr/bin/env python3
"""resolve_events.py EVENTS OUT: turn the event names of EVENTS (lines 'SET|name,name,...') into raw codes of the
core counter unit armv8_pmuv3_0. Sources, in this order: the sysfs event files, then 'perf list --details'.
OUT gets lines 'SET|name=0xCODE,...'. A name without a code is dropped and printed as 'unresolved'."""
import os, re, subprocess, sys
src, dst = sys.argv[1], sys.argv[2]
sysd = '/sys/bus/event_source/devices/armv8_pmuv3_0/events'
sets = [(l.split('|')[0], l.strip().split('|')[1].split(',')) for l in open(src) if '|' in l]
names = sorted({n for _, ns in sets for n in ns})
code = {}
for n in names:
    p = os.path.join(sysd, n)
    if os.path.exists(p):
        m = re.search(r'event=0x([0-9a-fA-F]+)', open(p).read())
        if m:
            code[n] = (int(m.group(1), 16), 'sysfs')
txt = subprocess.run(['perf', 'list', '--details'], capture_output=True, text=True).stdout
last = None
for line in txt.split('\n'):
    m = re.match(r'^\s{2}([a-z0-9_]+)\s*$', line)
    if m:
        last = m.group(1)
        continue
    m = re.match(r'^\s{2}([a-z0-9_]+) OR armv8_pmuv3_0/', line)
    if m:
        last = None
        continue
    m = re.search(r'armv8_pmuv3_0/event=(0x[0-9a-fA-F]+)/', line)
    if m and last and last in names and last not in code:
        code[last] = (int(m.group(1), 16), 'perf-list')
# Fallback: codes from ASCT's own table (src/core/asct_pmu_api.py) and two codes the 2026-11-15 runs used.
FALLBACK = {'cpu_cycles': 0x11, 'inst_retired': 0x08, 'l1d_cache_refill': 0x03, 'l2d_cache_refill': 0x17,
            'l1d_cache_lmiss_rd': 0x39, 'l2d_cache_lmiss_rd': 0x4009, 'll_cache_miss_rd': 0x37, 'bus_access': 0x19,
            'bus_access_rd': 0x60, 'l2d_cache_wb': 0x18, 'l2d_cache_wb_victim': 0x56, 'l2d_cache_wb_clean': 0x57,
            'l1d_cache_wb': 0x15, 'bus_cycles': 0x1d, 'stall_backend_mem': 0x4005, 'stall_backend': 0x24,
            'stall_frontend': 0x23, 'dtlb_walk': 0x34, 'l1d_tlb_refill': 0x05, 'l2d_tlb_refill': 0x2d,
            'l1d_cache_rd': 0x40, 'l2d_cache_rd': 0x50, 'll_cache_rd': 0x36, 'l3d_cache_lmiss_rd': 0x400b,
            'l1d_cache_refill_outer': 0x45, 'l1d_cache_refill_inner': 0x44, 'l1d_cache_hwprf': 0x8154,
            'l2d_cache_hwprf': 0x8155}
for n in names:
    if n not in code and n in FALLBACK:
        code[n] = (FALLBACK[n], 'fallback-table')
with open(dst, 'w') as f:
    for s, ns in sets:
        ok = [f'{n}=0x{code[n][0]:x}' for n in ns if n in code]
        f.write(f'{s}|{",".join(ok)}\n')
for n in names:
    print(('resolved   %-28s 0x%-5x %s' % (n, code[n][0], code[n][1])) if n in code else 'unresolved %s' % n)
