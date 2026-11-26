#!/usr/bin/env python3
# Print visible SVG <text> content and <title> tooltips per svg of the report page.
import re, html
src=open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html',encoding='utf-8').read()
svgs=re.findall(r'<svg\b.*?</svg>',src,flags=re.S)
print(len(svgs),'svgs')
for i,s in enumerate(svgs):
    texts=re.findall(r'<text\b[^>]*>(.*?)</text>',s,flags=re.S)
    titles=re.findall(r'<title>(.*?)</title>',s,flags=re.S)
    al=re.search(r'aria-label="([^"]*)"',s)
    print('=== SVG',i,'len',len(s),'texts',len(texts),'titles',len(titles))
    if al: print('ARIA:',html.unescape(al.group(1)))
    if len(texts)>0:
        for t in texts:
            t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',html.unescape(t)).strip()
            print('T:',t)
    import sys
    if '--titles' in sys.argv:
        for t in titles:
            print('TT:',re.sub(r'\s+',' ',html.unescape(t)).strip())
