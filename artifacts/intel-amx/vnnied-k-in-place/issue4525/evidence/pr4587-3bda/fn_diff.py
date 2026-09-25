# Compare the machine code of KV-cache functions between two objdump -d -C files.
# Usage: fn_diff.py before.txt after.txt
# A function counts as identical when its instruction list is the same after
# removing addresses and the absolute targets of jumps and calls.
import re, sys
PATTERN = re.compile(r'book<|page<|kv_block|scaled_v_expr|v_vnni|append_v_row|load_row|copy_token')
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
        if m:
            ops = re.sub(r'\b[0-9a-f]{5,}\b', 'ADDR', m.group(2))
            ops = re.sub(r'<[^>]*\+0x[0-9a-f]+>', '<LOCAL>', ops)
            funcs[cur].append(m.group(1) + ' ' + ops.strip())
    return funcs
a, b = load(sys.argv[1]), load(sys.argv[2])
common = sorted(set(a) & set(b))
same = [n for n in common if a[n] == b[n]]
print(f"instructions parsed: before {sum(len(v) for v in a.values())}, after {sum(len(v) for v in b.values())}")
diff = [n for n in common if a[n] != b[n]]
print(f"functions matched: {len(common)}, identical: {len(same)}, changed: {len(diff)}, only before: {len(set(a)-set(b))}, only after: {len(set(b)-set(a))}")
for n in diff[:40]:
    print(f"  changed: {len(a[n])} -> {len(b[n])} insns  {n[:180]}")
for n in sorted(set(a)-set(b))[:20]: print(f"  only before: {n[:180]}")
for n in sorted(set(b)-set(a))[:20]: print(f"  only after: {n[:180]}")
