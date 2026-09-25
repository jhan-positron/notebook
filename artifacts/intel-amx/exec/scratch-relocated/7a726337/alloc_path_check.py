# Allocation-path check of the rebased t_llama_unit: for every function whose name
# contains one of the KV allocation entry points, count instructions, rep stos,
# memset/memcpy calls, other calls and backward jumps (loops).
import re, sys
path = sys.argv[1]
keys = ['allocate_reclaimable_chunk', 'allocate_retained_storage', 'construct_kv_blocks',
        'reserve_token_range', 'restore_reclaimable_kv_storage', 'initialize_reclaimable_chunks']
funcs, cur = {}, None
for line in open(path, errors='replace'):
    m = re.match(r'^([0-9a-f]+) <(.*)>:$', line)
    if m:
        cur = m.group(2); funcs[cur] = []; continue
    if cur is None: continue
    m = re.match(r'^\s*([0-9a-f]+):\s+(\S+)\s*(.*)$', line)
    if m: funcs[cur].append((int(m.group(1), 16), m.group(2), m.group(3)))
print(f"{'insns':>6} {'repstos':>7} {'memfn':>5} {'loops':>5} {'calls':>5}  function")
for name, ins in funcs.items():
    if not any(k in name for k in keys): continue
    rep = sum(1 for a, mn, ops in ins if mn.startswith('rep') and 'stos' in (mn + ops))
    memfn = sum(1 for a, mn, ops in ins if mn.startswith('call') and re.search(r'mem(set|cpy|move)', ops))
    loops = 0
    for a, mn, ops in ins:
        if mn.startswith('j'):
            t = re.match(r'\s*([0-9a-f]+)\b', ops)
            if t and int(t.group(1), 16) < a: loops += 1
    calls = sorted(set(re.sub(r'@plt|\+0x[0-9a-f]+', '', re.search(r'<([^>]*)>', ops).group(1))[:70] for a, mn, ops in ins if mn.startswith('call') and '<' in ops))
    short = re.sub(r'std::array<tron::kv_slot_spec, \d+ul>\{[^}]*\}\}', 'SPECS', name)[:150]
    print(f"{len(ins):6d} {rep:7d} {memfn:5d} {loops:5d} {len(calls):5d}  {short}")
    for c in calls: print(f"{'':36}call -> {c}")
