#!/usr/bin/env python3
"""Convert the reply blocks (replies.json) to GitHub markdown. Usage: to_markdown.py <replies.json> <out dir>
Writes one <card>.md per reply (the second T13 block becomes COMBINED.md) and all.md with every reply. Reads only the json."""
import html, json, os, re, sys
blocks = json.load(open(sys.argv[1], encoding='utf-8'))
outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)

def inline(s):
    def code(m):
        t = html.unescape(m.group(1))
        return ('`` ' + t + ' ``') if '`' in t else ('`' + t + '`')
    parts = re.split(r'(<code>.*?</code>)', s, flags=re.S)
    res = []
    for p in parts:
        if p.startswith('<code>'):
            res.append(code(re.match(r'<code>(.*?)</code>', p, re.S)))
        else:
            p = re.sub(r'<strong>(.*?)</strong>', r'**\1**', p, flags=re.S)
            p = re.sub(r'<a href="([^"]+)">(.*?)</a>', r'[\2](\1)', p, flags=re.S)
            assert not re.search(r'<[a-zA-Z/]', p), 'unexpected tag in: ' + p[:200]
            res.append(html.unescape(p))
    return re.sub(r'\s*\n\s*', ' ', ''.join(res)).strip()

def convert(h):
    out = []; pos = 0
    for m in re.finditer(r'<p>(.*?)</p>|<pre>(.*?)</pre>|<ul>(.*?)</ul>', h, re.S):
        gap = h[pos:m.start()].strip()
        assert not gap, 'text between blocks: ' + gap[:200]
        pos = m.end()
        if m.group(1) is not None:
            out.append(inline(m.group(1)))
        elif m.group(2) is not None:
            body = m.group(2)
            w = re.fullmatch(r'\s*<code>(.*)</code>\s*', body, re.S)
            if w: body = w.group(1)
            assert '<' not in re.sub(r'&lt;', '', body) or not re.search(r'<[a-zA-Z/]', body), 'tag in pre: ' + body[:200]
            body = html.unescape(body).strip('\n')
            lines = body.split('\n')
            is_diff = any(re.match(r'^[+-](?![+-])', l) for l in lines) or any(l.startswith('@@') for l in lines)
            fence = '````' if '```' in body else '```'
            out.append(fence + ('diff' if is_diff else '') + '\n' + body + '\n' + fence)
        else:
            items = re.findall(r'<li>(.*?)</li>', m.group(3), re.S)
            rest = re.sub(r'<li>.*?</li>', '', m.group(3), flags=re.S).strip()
            assert not rest, 'text between list items: ' + rest[:200]
            out.append('\n'.join('- ' + inline(i) for i in items))
    assert not h[pos:].strip(), 'trailing text: ' + h[pos:][:200]
    return '\n\n'.join(out) + '\n'

seen = {}
allmd = []
for b in blocks:
    name = b['card']
    seen[name] = seen.get(name, 0) + 1
    if seen[name] == 2:
        assert name == 'T13', name
        name = 'COMBINED'
    md = convert(b['html'])
    open(os.path.join(outdir, name + '.md'), 'w', encoding='utf-8').write(md)
    allmd.append(f"<<<<< {name} | discussion {b['discussion']} | label: {b['label']} | {len(md)} chars, {len(md.split())} words >>>>>\n\n{md}")
open(os.path.join(outdir, 'all.md'), 'w', encoding='utf-8').write('\n'.join(allmd))
print(len(blocks), 'blocks converted;', 'all.md lines:', sum(x.count('\n') for x in allmd) + len(allmd))
