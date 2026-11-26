#!/usr/bin/env python3
"""Count instructions per kernel function in an llvm-objdump listing. Usage: count_ins.py <amx_attn.dis> ..."""
import re, sys, collections
for path in sys.argv[1:]:
    fn = None; ins = collections.OrderedDict()
    for line in open(path, errors='replace'):
        s = line.rstrip('\n')
        m = re.match(r'^<(.+)>:$', s)
        if m:
            fn = m.group(1); ins[fn] = []; continue
        m = re.match(r'^\s+([a-z][a-z0-9]*)\b', s)
        if fn and m:
            ins[fn].append(m.group(1))
    print(path.split('/')[-2])
    for f, l in ins.items():
        m = re.search(r'(pack_q_group_128x4|qk_rowmajor_128x4|weights_times_v_128x4)(?:ILm(\d+)E)?', f)
        if not m: continue
        c = collections.Counter(l)
        print(f'  {m.group(1)}<{m.group(2) or "-"}>: {len(l)} instructions, vpextrw {c.get("vpextrw", 0)}, vshuff64x2 {c.get("vshuff64x2", 0)}, vinsertf64x4 {c.get("vinsertf64x4", 0)}, vinsertf128 {c.get("vinsertf128", 0)}')
