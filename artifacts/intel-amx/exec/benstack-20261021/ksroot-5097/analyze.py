#!/usr/bin/env python3
"""Split an objdump -d listing into functions, report the functions that hold vdpbf16ps,
and for each such function print basic-block-level stats of the loops holding vdpbf16ps."""
import re, sys, collections
path = sys.argv[1]
funcs = collections.OrderedDict()
cur = None
hdr = re.compile(r'^([0-9a-f]+) <(.*)>:$')
ins = re.compile(r'^\s*([0-9a-f]+):\s+(\S+)\s*(.*)$')
for line in open(path, errors='replace'):
    m = hdr.match(line)
    if m:
        cur = m.group(2); funcs[cur] = []; continue
    m = ins.match(line)
    if m and cur is not None:
        funcs[cur].append((int(m.group(1), 16), m.group(2), m.group(3).strip()))
for name, body in funcs.items():
    n_dp = sum(1 for _, op, _ in body if op == 'vdpbf16ps')
    if n_dp == 0: continue
    print(f"=== {name}\n    total insns {len(body)}, vdpbf16ps {n_dp}, size {body[-1][0]-body[0][0] if body else 0} bytes")
    # find backward jumps (loops) whose range contains vdpbf16ps
    addr_index = {a: i for i, (a, _, _) in enumerate(body)}
    for i, (a, op, arg) in enumerate(body):
        if op.startswith('j'):
            m = re.match(r'([0-9a-f]+)\s', arg)
            if not m: continue
            tgt = int(m.group(1), 16)
            if tgt <= a and tgt in addr_index:
                j = addr_index[tgt]
                blk = body[j:i+1]
                dp = sum(1 for _, o, _ in blk if o == 'vdpbf16ps')
                if dp == 0: continue
                loads = sum(1 for _, o, g in blk if o.startswith('vmov') and '(' in g.split(',')[0]) 
                stores = sum(1 for _, o, g in blk if (o.startswith('vmov') or o.startswith('mov')) and '(' in g.split(',')[-1])
                stack = sum(1 for _, o, g in blk if 'rsp' in g or 'rbp' in g)
                calls = [g for _, o, g in blk if o == 'call']
                print(f"    loop {tgt:x}..{a:x} ({op}): {len(blk)} insns, vdpbf16ps {dp}, vector loads from mem {loads}, stores {stores}, rsp/rbp refs {stack}, calls {len(calls)}")
