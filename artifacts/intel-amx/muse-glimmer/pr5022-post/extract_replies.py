#!/usr/bin/env python3
"""Extract the reply blocks of respond-2-Isaac.html. Usage: extract_replies.py <page.html> <out.json>
Writes a JSON list of {card, index, label, html, discussion} in page order. Reads only."""
import json, re, sys
h = open(sys.argv[1], encoding='utf-8').read()
cards = [(m.start(), m.group(1)) for m in re.finditer(r'<div class="card[^"]*" id="([A-Za-z]{1,2}\d{0,2})"', h)]
def block_end(start):
    """Index just past the </div> that closes the <div ...> starting at `start`."""
    depth = 0
    for m in re.finditer(r'<div\b|</div>', h[start:]):
        depth += 1 if m.group(0) != '</div>' else -1
        if depth == 0:
            return start + m.end()
    raise SystemExit('unbalanced div at %d' % start)
out = []
for m in re.finditer(r'<div class="reply"[^>]*>', h):
    s = m.start(); e = block_end(s)
    inner = h[m.end():e - len('</div>')]
    card = [c for p, c in cards if p <= s][-1] if any(p <= s for p, c in cards) else '?'
    cpos = [p for p, c in cards if p <= s][-1]
    lbl = re.match(r'\s*<div class="lbl">(.*?)</div>', inner, re.S)
    label = re.sub(r'<[^>]+>', '', lbl.group(1)).strip() if lbl else ''
    body = inner[lbl.end():] if lbl else inner
    head = h[cpos:s]
    disc = re.findall(r'discussion_r(\d+)', head[:1500])
    out.append({'card': card, 'label': label, 'html': body.strip(), 'discussion': disc[0] if disc else None, 'pos': s})
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
tags = {}
for o in out:
    for t in re.findall(r'<([a-zA-Z0-9]+)(?:\s[^>]*)?>', o['html']):
        tags[t] = tags.get(t, 0) + 1
print(len(out), 'reply blocks; tags inside:', dict(sorted(tags.items())))
attrs = set()
for o in out:
    for t in re.findall(r'<[a-zA-Z0-9]+\s[^>]*>', o['html']):
        attrs.add(re.sub(r'="[^"]*"', '="…"', t))
print('tags with attributes:', sorted(attrs))
for o in out:
    print(f"{o['card']:4} disc={o['discussion']} len={len(o['html']):5} label={o['label'][:90]}")
