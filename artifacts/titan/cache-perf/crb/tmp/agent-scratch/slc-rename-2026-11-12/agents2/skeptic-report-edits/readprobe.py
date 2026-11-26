import re,json,sys
for f in sys.argv[1:]:
    t=open(f,encoding='utf-8').read()
    m=re.search(r'<script type="application/json" id="probe-result">(.*?)</script>',t,flags=re.S)
    r=json.loads(m.group(1))
    print('=====',f)
    print('errs',r['errs'])
    print('doc scrollW',r['docScrollW'],'clientW',r['docClientW'],'winW',r['winW'],'mainW',r['mainW'])
    print('svgs',r['svgs'])
    print('lattab rows',r['lattabRows'])
    print('pres',r['pres'])
    print('h3',r['h3'])
    print('tables',r['tables'],'elems in subsection',r['sectionElems'],'next h2',r['nextH2'],r['nextH2top'])
    print('nesting: preInP',r['preInP'],'ulInP',r['ulInP'],'tableInP',r['tableInP'],'hInP',r['hInP'],'emptyP',r['emptyP'])
    print('overflowing elements',len(r['over']))
    for o in r['over'][:60]: print('   ',o)
    heads=r['heads']; toc=r['toc']
    print('headings',len(heads),'toc entries',len(toc))
    hd={h[1]:h for h in heads}
    for id_,txt,tag,ttxt in toc:
        if tag is None or txt!=ttxt: print('   TOC MISMATCH',id_,repr(txt),tag,repr(ttxt))
    tocids=[x[0] for x in toc]
    for h in heads:
        if h[1] not in tocids: print('   heading not in toc',h)
