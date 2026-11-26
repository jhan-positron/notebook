#!/usr/bin/env python3
# Extract the visible text of the report page (outside <svg>, <style>), one block per line.
import re, sys, html
from html.parser import HTMLParser
src = open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html', encoding='utf-8').read()
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.out=[]; s.skip=0; s.buf=''
        s.insvg=0
    def flush(s):
        t=re.sub(r'\s+',' ',s.buf).strip()
        if t: s.out.append(t)
        s.buf=''
    def handle_starttag(s,tag,attrs):
        if tag in('style','script'): s.skip+=1
        if tag=='svg': s.insvg+=1; s.flush(); s.out.append('[SVG START]')
        if tag in('p','li','h1','h2','h3','h4','tr','div','summary','details','figcaption','table','ul','ol','dt','dd','section','caption','br'):
            s.flush()
        if tag in('td','th'): s.buf+=' | '
    def handle_endtag(s,tag):
        if tag in('style','script'): s.skip-=1
        if tag=='svg': s.insvg-=1; s.flush(); s.out.append('[SVG END]')
        if tag in('p','li','h1','h2','h3','h4','tr','div','summary','details','figcaption','table','ul','ol','dt','dd','section','caption'):
            s.flush()
    def handle_data(s,d):
        if s.skip: return
        if s.insvg and '--svg' not in sys.argv: return
        s.buf+=d
p=P(); p.feed(src); p.flush()
for i,l in enumerate(p.out): print(l)
