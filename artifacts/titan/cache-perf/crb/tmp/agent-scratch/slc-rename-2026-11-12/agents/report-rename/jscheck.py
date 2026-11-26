import re, sys
A = open('/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html', encoding='utf-8').read()
B = open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html', encoding='utf-8').read()

def scripts(src):
    out = []
    for m in re.finditer(r'<script>(.*?)</script>', src, flags=re.S):
        start_line = src.count('\n', 0, m.start(1)) + 1
        out.append((start_line, m.group(1)))
    return out

def tokenize(js):
    """Return list of (kind, text, line_offset). kinds: code, str, tpl, lcom, bcom."""
    toks = []; i = 0; n = len(js); buf = []; line = 0; bufline = 0
    def flush():
        nonlocal buf
        if buf: toks.append(('code', ''.join(buf), bufline)); buf = []
    while i < n:
        c = js[i]
        if c == '/' and i + 1 < n and js[i+1] == '/':
            flush(); j = js.find('\n', i); j = n if j < 0 else j
            toks.append(('lcom', js[i:j], line)); i = j; continue
        if c == '/' and i + 1 < n and js[i+1] == '*':
            flush(); j = js.find('*/', i + 2); j = n if j < 0 else j + 2
            toks.append(('bcom', js[i:j], line)); line += js.count('\n', i, j); i = j; continue
        if c in '\'"`':
            flush(); q = c; j = i + 1
            while j < n and js[j] != q:
                if js[j] == '\\': j += 1
                j += 1
            toks.append(('str', js[i:j+1], line)); line += js.count('\n', i, j+1); i = j + 1; continue
        if not buf: bufline = line
        buf.append(c)
        if c == '\n': line += 1
        i += 1
    flush()
    return toks

sa, sb = scripts(A), scripts(B)
print("script blocks before/after:", len(sa), len(sb), "start lines", [s[0] for s in sa], [s[0] for s in sb])
allok = True
for (la, ja), (lb, jb) in zip(sa, sb):
    ta, tb = tokenize(ja), tokenize(jb)
    print(f"block at line {la}: tokens {len(ta)} / {len(tb)}; kinds equal: {[t[0] for t in ta] == [t[0] for t in tb]}")
    code_a = [t[1] for t in ta if t[0] == 'code']; code_b = [t[1] for t in tb if t[0] == 'code']
    print("   code (non-string, non-comment) identical:", code_a == code_b, f"({sum(map(len, code_a))} chars)")
    allok &= code_a == code_b and [t[0] for t in ta] == [t[0] for t in tb]
    for x, y in zip(ta, tb):
        if x[1] != y[1]:
            print(f"   line {la + x[2]:4d} {x[0]:4s}: {x[1]!r}\n                 -> {y[1]!r}")
print("ALL OK:", allok)
# numbers: compare all numeric literals in code parts
