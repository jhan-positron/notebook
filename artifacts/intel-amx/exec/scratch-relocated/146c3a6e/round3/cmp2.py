import re, difflib
def funcs(path):
    out = {}; cur = None
    for line in open(path):
        m = re.match(r'^[0-9a-f]+ <(.*)>:$', line)
        if m: cur = m.group(1); out[cur] = []; continue
        m = re.match(r'^\s*[0-9a-f]+:\t(.*)$', line)
        if m and cur:
            ins = re.sub(r'\s*#.*$', '', m.group(1)); ins = re.sub(r'<[^>]*>', '<t>', ins)
            ins = re.sub(r'(j[a-z]+|call)\s+[0-9a-f]+', r'\1 ADDR', ins); out[cur].append(ins.strip())
    return out
a = funcs('m5061.s'); h = funcs('head.s')
for k in sorted(a):
    if 'amx_attn_h128g4' not in k: continue
    if k not in h: print('MISSING in head:', k[:70]); continue
    d = [l for l in difflib.unified_diff(a[k], h[k], lineterm='', n=0) if l[:1] in '+-' and l[:3] not in ('+++','---')]
    print(f'{len(a[k]):5d} {len(h[k]):5d} diff={len(d):4d}  {k[:95]}')
print('head-only symbols:', [k[:60] for k in h if k not in a and 'amx_attn' in k])
