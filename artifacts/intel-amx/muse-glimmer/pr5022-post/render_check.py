#!/usr/bin/env python3
"""Render the replies with GitHub's markdown API (nothing is published) and report the HTML elements produced.
Usage: render_check.py <md dir> <out dir> [names...]"""
import collections, json, os, re, subprocess, sys
md, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
names = sys.argv[3:] or (['COMBINED'] + [f'I{i}' for i in range(1, 27)])
for n in names:
    text = open(os.path.join(md, n + '.md'), encoding='utf-8').read()
    p = subprocess.run(['gh', 'api', 'markdown', '--input', '-'],
                       input=json.dumps({'text': text, 'mode': 'gfm', 'context': 'positron-ai/tron'}), capture_output=True, text=True)
    if p.returncode != 0:
        print(n, 'RENDER FAILED', p.stderr[:200]); continue
    open(os.path.join(out, n + '.html'), 'w', encoding='utf-8').write(p.stdout)
    tags = collections.Counter(re.findall(r'<([a-z0-9]+)[ >]', p.stdout))
    odd = {t: c for t, c in tags.items() if t in ('em', 'del', 'h1', 'h2', 'h3', 'blockquote', 'table', 'ol', 'hr', 's', 'sub', 'sup', 'input')}
    links = len(re.findall(r'<a [^>]*href=', p.stdout))
    plain = re.sub(r'<[^>]+>', '', p.stdout)
    print(f'{n:8} p={tags.get("p",0):2} li={tags.get("li",0):2} pre={tags.get("pre",0)} code={tags.get("code",0):3} links={links:2} unexpected={odd or "none"} stray_backticks={plain.count("`")} stray_stars={plain.count("**")}')
