import sys, re, json, html
V='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r2'
for w in sys.argv[1:]:
    d=open(f'{V}/work/dom-{w}.html').read()
    m=list(re.finditer(r'<pre id="r2measure">(\{.*?)</pre>',d,re.S))[-1]
    j=json.loads(html.unescape(m.group(1)))
    print('=== width',w,'win',j['win'],'doc',j['doc'],'bg',j['bg'])
    print(' overflow elems without scroll ancestor:',len(j['overflowNoScrollAncestor']))
    for o in j['overflowNoScrollAncestor'][:10]: print('   ',o)
    for s in j['svgs']:
        print(f"  svg#{s['i']} cls={s['cls']} vb={s['viewBox']} box={s['box']} scale={s['scale']} nText={s['nText']} minFontPx={s['minFontPx']:.2f} marks={s['marks']} noTitle={s['noTitle']}")
        print('    clip:',len(s['clip']))
        for c in s['clip'][:10]: print('     ',c)
        print('    text-text overlaps:',len(s['overl']))
        for c in s['overl'][:30]: print('     ',c)
        print('    mark-text overlaps:',len(s['markText']))
        for c in s['markText'][:30]: print('     ',c)
    print('  details:',j['details'])
    for t in j['tables']: print('  table',t)
    for sc in j['scrollers']:
        if sc['scrollW']>sc['clientW']+1: print('  scroller',sc)
