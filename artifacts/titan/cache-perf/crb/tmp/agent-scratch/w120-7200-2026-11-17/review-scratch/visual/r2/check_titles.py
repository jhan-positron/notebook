# check_titles.py - list the graphic elements of each chart SVG that are not inside a <g> with a <title>, and check the tooltip content.
import re, html, collections
P='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
h=open(P).read()
svgs=re.findall(r'<svg (class="f1[wmn]" )?viewBox="0 0 (\d+) (\d+)"[^>]*role="img"[^>]*>(.*?)</svg>',h,re.S)
for cls,W,H,body in svgs:
    name=cls.strip() or f'fig2 {W}x{H}'
    groups=re.findall(r'<g[^>]*>.*?</g>',body,re.S)
    nt=[g for g in groups if '<title>' not in g]
    outside=re.sub(r'<g[^>]*>.*?</g>','',body,flags=re.S)
    c=collections.Counter(re.findall(r'<(\w+)',outside))
    print(f'== {name}: groups {len(groups)}, groups without title {len(nt)}, elements outside groups {dict(c)}')
    for el in ('rect','path','circle'):
        for m in re.findall(r'<%s[^>]*>'%el,outside): print('   outside:',m[:160])
    lines=collections.Counter(re.sub(r'(x1|x2|y1|y2)="[\d.]+"','',m) for m in re.findall(r'<line[^>]*>',outside))
    for k,v in lines.items(): print('   outside lines:',v,k)
    # tooltip content: row name, value, n, source
    miss=collections.Counter()
    for g in groups:
        t=html.unescape(re.search(r'<title>(.*?)</title>',g,re.S).group(1)) if '<title>' in g else ''
        if 'GB/s' not in t and '%' not in t: miss['no value']+=1
        if 'n = ' not in t: miss['no n']+=1; 
        if 'Source: R/' not in t: miss['no source']+=1
        if len(t)<40: miss['short']+=1
    print('   tooltip gaps:',dict(miss))
    ex=[html.unescape(re.search(r'<title>(.*?)</title>',g,re.S).group(1)) for g in groups if 'n = ' not in g][:3]
    for e in ex: print('   example without n:',e[:400])
