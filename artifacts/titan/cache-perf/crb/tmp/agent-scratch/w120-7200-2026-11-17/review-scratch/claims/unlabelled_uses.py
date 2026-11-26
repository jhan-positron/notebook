#!/usr/bin/env python3
# List text units of the page that use the three visits of the 7200 MT/s boot (or a value that only F72d12 or
# control I gives) without naming and labelling F72d12 / control I in the same unit.
import re, html
src=open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html',encoding='utf-8').read()
src=re.sub(r'<svg\b.*?</svg>','',src,flags=re.S)
units=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x[1]))).strip() for x in re.findall(r'<(li|p|figcaption|dd|tr|h3)\b[^>]*>(.*?)</\1>',src,flags=re.S)]
pat=re.compile(r'three times|three visits|visits of|26\.03|35\.4 %|301\.90|all \d+ pairs|same test gave|same test line gave')
for u in units:
    if pat.search(u):
        ci='added after the first numbers were seen' in u
        f='not part of the rerun' in u
        print(('LABELLED ' if (ci and f) else 'MISSING(ctrlI=%s,F72=%s) '%(ci,f))+u[:330]); print()
