# Same counting rules as alloc_path_check.py; classify by the method name at the end of the symbol.
import re, sys, collections
keys = ['allocate_reclaimable_chunk', 'allocate_retained_storage', 'construct_kv_blocks',
        'reserve_token_range', 'restore_reclaimable_kv_storage', 'initialize_reclaimable_chunks']
funcs, cur = {}, None
for line in open(sys.argv[1], errors='replace'):
    m = re.match(r'^([0-9a-f]+) <(.*)>:$', line)
    if m:
        cur = m.group(2); funcs[cur] = []; continue
    if cur is None: continue
    m = re.match(r'^\s*([0-9a-f]+):\s+(\S+)\s*(.*)$', line)
    if m: funcs[cur].append((int(m.group(1), 16), m.group(2), m.group(3)))
agg = collections.defaultdict(list)
for name, ins in funcs.items():
    meth = re.search(r'>::(\w+)\([^()]*(\([^()]*\))?[^()]*\)$', name)
    k = next((k for k in keys if meth and meth.group(1) == k), None)
    if k is None: continue
    rep = sum(1 for a, mn, ops in ins if mn.startswith('rep') and 'stos' in (mn + ops))
    stos = sum(1 for a, mn, ops in ins if 'stos' in mn)
    memfn = sum(1 for a, mn, ops in ins if mn.startswith('call') and re.search(r'mem(set|cpy|move)|bzero', ops))
    back = sum(1 for a, mn, ops in ins if mn.startswith('j') and (t := re.match(r'\s*([0-9a-f]+)\b', ops)) and int(t.group(1), 16) < a)
    avx_store = sum(1 for a, mn, ops in ins if re.match(r'v?movnt|vmovdq[au](8|16|32|64)?$|vmovup[sd]$|vmovap[sd]$', mn) and ops.rstrip().endswith(')'))
    calls = sorted(set(re.sub(r'@plt|\+0x[0-9a-f]+|\(.*', '', c.group(1)) for a, mn, ops in ins if mn.startswith('call') and (c := re.search(r'<(.*)>', ops))))
    agg[k].append((len(ins), rep, stos, memfn, back, avx_store, calls))
for k in keys:
    rows = agg.get(k, [])
    if not rows: print(f"{k}: 0 instantiations"); continue
    ins = [r[0] for r in rows]
    print(f"{k}: {len(rows)} instantiations, insns {min(ins)}-{max(ins)}, rep_stos {sum(r[1] for r in rows)}, any stos {sum(r[2] for r in rows)}, mem*/bzero calls {sum(r[3] for r in rows)}, backward jumps per fn {sorted(set(r[4] for r in rows))}, vector stores to memory {sum(r[5] for r in rows)}")
    allcalls = sorted(set(c for r in rows for c in r[6]))
    print("   call targets:", "; ".join(c[:60] for c in allcalls))
