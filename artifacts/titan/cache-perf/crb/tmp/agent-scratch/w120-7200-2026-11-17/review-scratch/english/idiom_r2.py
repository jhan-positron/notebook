import re
txt=open('body.txt').read()+'\n'+open('svg.txt').read()+'\n'+open('titles.txt').read()
pats=['fall into','falls into','fell','jump','lies against','against the band','on record','set back','by its name','within \d','some hours','the life of','apart','kept','stays','moves','holds?','in turn','alternately','itself','driver','extra','still','own rows','keep their','at most','in place of','stands? in','span','visits?','idle','picture','takeaway','under the hood','noise','wash','spread','gap','boost','roughly','around','approximately','about ','nearly','almost','several','some ','a few','many','mostly','often','in the reverse','run of the machine','comes? from','point at','hover','fits?','the one ','no exact size','not fully','cannot exclude','e\.g\.','i\.e\.','etc','vs\.?',' via ','per se','in fact','of course','note that','respectively']
for p in pats:
    ms=list(re.finditer(p,txt,flags=re.I))
    if not ms: continue
    seen=set()
    out=[]
    for m in ms:
        ctx=txt[max(0,m.start()-45):m.end()+45].replace('\n',' ')
        key=ctx[30:70]
        if key in seen: continue
        seen.add(key); out.append(ctx)
    print(f'== {p}: {len(ms)} hits, {len(out)} distinct')
    for o in out[:6]: print('   ',o)
