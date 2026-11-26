import re, html, collections
src = open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html').read()
svgs = [m.group(0) for m in re.finditer(r'<svg[^>]*role="img"[^>]*>.*?</svg>', src, re.S)]
rowsets = []
for s in svgs[3:]:
    cur = collections.OrderedDict()
    for m in re.finditer(r'<g class="pt"><title>(.*?)</title>', s, re.S):
        t = html.unescape(m[1])
        v = re.search(r': ([\d.]+) GB/s\. Row: ([\d.]+ to [\d.]+) GB/s, n = (\d+)', t)
        cur.setdefault((t.split(':')[0][:60], v[2], v[3]), []).append(v[1])
    rowsets += [(k, sorted(v, key=float)) for k, v in cur.items()]
tables = re.findall(r'<table.*?</table>', src, re.S)
t = tables[5]
trs = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
tv = []
for tr in trs:
    c = [html.unescape(re.sub(r'<[^>]+>', ' ', x)).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
    if len(c) == 3 and c[1].isdigit():
        tv.append((re.sub(r'\s+', ' ', c[0])[:60], [x.strip() for x in c[2].split(',')]))
print(len(rowsets), len(tv))
ok = True
for (k, v), (name, vals) in zip(rowsets, tv):
    same = v == vals
    ok &= same
    print('%-5s svg[%s | %s n=%s]  table[%s]' % ('OK' if same else 'DIFF', k[0][:45], k[1], k[2], name[:45]))
print('all rows equal in order:', ok)
