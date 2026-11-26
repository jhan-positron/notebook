#!/usr/bin/env python3
"""Dump the page: body text with SVGs replaced by markers, and each SVG to its own file."""
import re, sys, html, os
src = sys.argv[1]; out = sys.argv[2]
t = open(src, encoding='utf-8').read()
svgs = re.findall(r'<svg\b.*?</svg>', t, flags=re.S)
for i, s in enumerate(svgs):
    open(os.path.join(out, 'svg%02d.txt' % i), 'w').write(s)
def repl(m, c=[0]):
    c[0] += 1
    return '\n[[SVG %d]]\n' % (c[0]-1)
b = re.sub(r'<svg\b.*?</svg>', repl, t, flags=re.S)
b = re.sub(r'<style\b.*?</style>', '', b, flags=re.S)
b = re.sub(r'<(br|/p|/li|/tr|/h\d|/div|/summary|/details|/figcaption|/caption|/dt|/dd)\s*/?>', '\n', b)
b = re.sub(r'</t[dh]>', ' | ', b)
b = re.sub(r'<[^>]+>', '', b)
b = html.unescape(b)
b = re.sub(r'[ \t]+', ' ', b)
b = re.sub(r'\n\s*\n+', '\n', b)
open(os.path.join(out, 'text.txt'), 'w').write(b)
print(len(svgs), 'svgs', len(b), 'chars text')
