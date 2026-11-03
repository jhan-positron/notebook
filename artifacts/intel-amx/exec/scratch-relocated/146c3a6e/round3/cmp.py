import re, sys, difflib
def funcs(path):
    out = {}; cur = None
    for line in open(path):
        m = re.match(r'^[0-9a-f]+ <(.*)>:$', line)
        if m: cur = m.group(1); out[cur] = []; continue
        m = re.match(r'^\s*[0-9a-f]+:\t(.*)$', line)
        if m and cur:
            ins = m.group(1)
            ins = re.sub(r'\s*#.*$', '', ins)
            ins = re.sub(r'<[^>]*>', '<t>', ins)
            ins = re.sub(r'\b[0-9a-f]{3,}\b(?= <t>)', 'ADDR', ins)
            ins = re.sub(r'(j[a-z]+|call)\s+[0-9a-f]+', r'\1 ADDR', ins)
            out[cur].append(ins.strip())
    return out
b = funcs('base.s'); h = funcs('head.s')
pairs = [('pack_q_group_128x4', '18pack_q_group_128x4'), ('qk_rowmajor_128x4', '17qk_rowmajor_128x4'), ('weights_times_v_128x4', '21weights_times_v_128x4')]
for name, mg in pairs:
    bk = [k for k in b if mg in k and 'ILm' not in k]
    for g in ('4', '16'):
        hk = [k for k in h if mg + 'ILm' + g + 'E' in k and '__tls' not in k and 'guard' not in k]
        if not bk or not hk: print(name, g, 'missing', bk, hk); continue
        bi, hi = b[bk[0]], h[hk[0]]
        d = [l for l in difflib.unified_diff(bi, hi, lineterm='', n=0) if l[:1] in '+-' and l[:3] not in ('+++', '---')]
        print(f'{name}<{g}> vs main: main {len(bi)} instr, head {len(hi)} instr, diff lines {len(d)}')
        for l in d[:12]: print('   ', l)
