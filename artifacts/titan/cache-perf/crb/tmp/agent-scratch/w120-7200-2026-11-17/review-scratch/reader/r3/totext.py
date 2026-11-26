#!/usr/bin/env python3
"""Turn the report HTML into readable text. SVG <title> tooltips are dropped
in mode 'body'; SVG text is kept in [svg] lines."""
import sys, re, html
from html.parser import HTMLParser
src = open(sys.argv[1], encoding='utf-8').read()
mode = sys.argv[2] if len(sys.argv) > 2 else 'body'
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.out=[]; s.stack=[]; s.skip=0; s.insvg=0
    def handle_starttag(s, tag, attrs):
        s.stack.append(tag)
        if tag in ('style','script'): s.skip+=1
        if tag=='svg': s.insvg+=1; s.out.append('\n[SVG START]\n')
        if tag=='title' and s.insvg and mode=='body': s.skip+=1
        if tag in ('p','div','li','tr','h1','h2','h3','h4','section','details','summary','table','figcaption','figure','ul','ol','dt','dd'): s.out.append('\n')
        if tag in ('td','th'): s.out.append(' | ')
        if tag=='text': s.out.append('\n[svg] ')
        if tag=='br': s.out.append('\n')
        if tag in ('h1','h2','h3','h4'): s.out.append('#'*int(tag[1])+' ')
        if tag=='li': s.out.append('- ')
    def handle_endtag(s, tag):
        if tag in ('style','script'): s.skip-=1
        if tag=='title' and s.insvg and mode=='body': s.skip-=1
        if tag=='svg': s.insvg-=1; s.out.append('\n[SVG END]\n')
        if tag in ('p','div','li','tr','h1','h2','h3','h4','table','figcaption','details','summary'): s.out.append('\n')
    def handle_data(s, d):
        if s.skip: return
        s.out.append(d)
p=P(); p.feed(src)
t=''.join(p.out)
t=re.sub(r'[ \t]+',' ',t)
t=re.sub(r'\n\s*\n+','\n\n',t)
sys.stdout.write(t)
