import re, html, sys
path = sys.argv[1]
src = open(path, encoding='utf-8').read()
lines = src.split('\n')
def strip_tags(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s))
# headings
heads = []   # (line, level, id, text)
for i, l in enumerate(lines):
    for m in re.finditer(r'<h([1-6])(?:\s+id="([^"]*)")?[^>]*>(.*?)</h\1>', l):
        heads.append((i+1, int(m.group(1)), m.group(2), strip_tags(m.group(3))))
print("HEADINGS", len(heads))
for h in heads: print("  ", h)
htexts = {h[3] for h in heads}
hid = {h[2]: h for h in heads if h[2]}
# all ids
ids = {}
for i, l in enumerate(lines):
    for m in re.finditer(r'\bid="([^"]+)"', l):
        ids.setdefault(m.group(1), []).append(i+1)
dup = {k: v for k, v in ids.items() if len(v) > 1}
print("duplicate ids:", dup)
# TOC
print("\nTOC CHECK")
bad = 0
for i, l in enumerate(lines):
    if not (56 <= i+1 <= 72): continue
    for m in re.finditer(r'<a href="#([^"]+)">(.*?)</a>', l):
        tid, txt = m.group(1), strip_tags(m.group(2))
        if tid not in hid:
            print(f"  line {i+1}: href #{tid} has NO heading with that id"); bad += 1; continue
        ht = hid[tid][3]
        ok = (ht == txt)
        if not ok: bad += 1
        print(f"  line {i+1}: {'OK ' if ok else 'DIFF'} #{tid}\n       toc : {txt!r}\n       head: {ht!r} (line {hid[tid][0]})")
print("toc mismatches:", bad)
# all hrefs with #
print("\nALL INTERNAL HREFS")
for i, l in enumerate(lines):
    for m in re.finditer(r'href="#([^"]+)"', l):
        if m.group(1) not in ids: print("  BROKEN", i+1, m.group(1))
# headings not in TOC
toc_ids = set()
for i, l in enumerate(lines):
    if 56 <= i+1 <= 72:
        toc_ids.update(re.findall(r'href="#([^"]+)"', l))
print("\nheadings (h2/h3) not in TOC:", [(h[0], h[3]) for h in heads if h[1] in (2,3) and h[2] not in toc_ids])
