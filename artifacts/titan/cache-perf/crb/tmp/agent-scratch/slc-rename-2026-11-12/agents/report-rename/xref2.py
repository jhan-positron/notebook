import re, html, sys
path = sys.argv[1]
src = open(path, encoding='utf-8').read()
lines = src.split('\n')
def strip_tags(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s))
heads = []
for i, l in enumerate(lines):
    for m in re.finditer(r'<h([1-6])(?:\s+id="([^"]*)")?[^>]*>(.*?)</h\1>', l):
        heads.append((i+1, strip_tags(m.group(3))))
htexts = {h[1]: h[0] for h in heads}
# dt terms
dts = {}
for i, l in enumerate(lines):
    for m in re.finditer(r'<dt>(.*?)</dt>', l):
        dts[strip_tags(m.group(1))] = i+1
# bold item names
bolds = {}
for i, l in enumerate(lines):
    for m in re.finditer(r'<b>(.*?)</b>', l):
        bolds.setdefault(strip_tags(m.group(1)).rstrip('.'), i+1)
changed = set(int(x) for x in open('changed_lines.txt').read().split())
# visible text only: lines up to </main> (line 474)
pat = re.compile(r'(?P<lead>(?:[Ss]ections?|[Ss]ee(?: the)?(?: open item)?|in|and|item|open item|table|of)\s+)"(?P<q>[^"]{3,140})"')
rows = []
for i, l in enumerate(lines[:474]):
    t = strip_tags(l)
    for m in pat.finditer(t):
        q = m.group('q'); lead = m.group('lead').strip()
        kind = 'HEADING-EXACT' if q in htexts else None
        if not kind:
            # prefix of a heading?
            pref = [h for h in htexts if h.startswith(q)]
            if pref: kind = 'heading-PREFIX of ' + repr(pref[0]) + f' (line {htexts[pref[0]]})'
        if not kind and q in dts: kind = f'dt-term exact (line {dts[q]})'
        if not kind:
            pd = [d for d in dts if q in d]
            if pd: kind = 'dt-term part of ' + repr(pd[0]) + f' (line {dts[pd[0]]})'
        if not kind and q in bolds: kind = f'bold item (line {bolds[q]})'
        if not kind: kind = 'NOT A HEADING'
        rows.append((i+1, lead, q, kind, (i+1) in changed))
for r in rows:
    print(f"{r[0]:4d} {'CHG' if r[4] else '   '} [{r[1]}] \"{r[2]}\" -> {r[3]}")
