# fn_diff with layout noise removed: rip-relative displacements, absolute addresses, jump/call offsets.
import re, sys
PATTERN = re.compile(sys.argv[3] if len(sys.argv) > 3 else r'book<|page<|kv_block|scaled_v_expr|v_vnni|append_v_row|load_row|copy_token')
def norm(ops):
    ops = re.sub(r'#.*$', '', ops)                      # objdump comments (<sym+off>)
    ops = re.sub(r'-?0x[0-9a-f]+\(%rip\)', 'RIP', ops)
    ops = re.sub(r'\b[0-9a-f]{4,}\b <([^>+]*)(\+0x[0-9a-f]+)?>', lambda m: 'TGT<' + m.group(1) + '>', ops)
    ops = re.sub(r'\b[0-9a-f]{5,}\b', 'ADDR', ops)
    return ops.strip()
def load(path):
    funcs, cur = {}, None
    for line in open(path, errors='replace'):
        m = re.match(r'^[0-9a-f]+ <(.*)>:$', line)
        if m:
            cur = m.group(1) if PATTERN.search(m.group(1)) else None
            if cur: funcs[cur] = []
            continue
        if cur is None: continue
        m = re.match(r'^\s*[0-9a-f]+:\s+(?:[0-9a-f]{2} )*\s*(\S+)\s*(.*)$', line)
        if m: funcs[cur].append(m.group(1) + ' ' + norm(m.group(2)))
    return funcs
a, b = load(sys.argv[1]), load(sys.argv[2])
common = sorted(set(a) & set(b))
same = [n for n in common if a[n] == b[n]]
diff = [n for n in common if a[n] != b[n]]
print(f"instructions parsed: before {sum(len(v) for v in a.values())}, after {sum(len(v) for v in b.values())}")
print(f"functions matched: {len(common)}, identical: {len(same)}, changed: {len(diff)}, only before: {len(set(a)-set(b))}, only after: {len(set(b)-set(a))}")
import collections
for n in diff:
    d = sum(1 for x, y in zip(a[n], b[n]) if x != y) + abs(len(a[n]) - len(b[n]))
    print(f"  changed: {len(a[n])} -> {len(b[n])} insns, {d} differing lines  {n[:150]}")
for n in sorted(set(a)-set(b)): print(f"  only before: {n[:200]}")
