#!/usr/bin/env python3
"""Turn the reply block of the page (<div class="reply">) into GitHub markdown with the names in capitals kept.
Usage: make_reply_template.py PAGE.html OUT.md"""
import html, re, sys
page, out = sys.argv[1:3]
h = open(page, encoding='utf-8').read()
blocks = re.findall(r'<div class="reply">(.*?)</div>\n<ul>', h, re.S)
assert len(blocks) == 1, len(blocks)
b = blocks[0]
b = re.sub(r'<div class="lbl">.*?</div>', '', b, flags=re.S)
b = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r'[\2](\1)', b)
b = re.sub(r'<code>(.*?)</code>', r'`\1`', b)
b = re.sub(r'<li>(.*?)</li>', r'- \1', b, flags=re.S)
b = re.sub(r'</?ul>', '', b)
b = re.sub(r'<p>(.*?)</p>', r'\n\1\n', b, flags=re.S)
assert not re.search(r'<[a-z/]', b), re.findall(r'<[^>]*>', b)
b = html.unescape(b)
b = re.sub(r'\n{3,}', '\n\n', b).strip() + '\n'
open(out, 'w', encoding='utf-8').write(b)
print(b)
