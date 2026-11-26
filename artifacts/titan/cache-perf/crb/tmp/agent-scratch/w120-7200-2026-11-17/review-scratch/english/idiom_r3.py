import re
txt=open('body-r3.txt').read()+'\n'+open('svg-r3.txt').read()+'\n'+open('titles-r3.txt').read()
pats=['fall into','falls into','fell','jump','lies against','by its name','within \\d','some hours','the life of','apart','in turn','alternately','driver','own rows','keep their','stands? in','picture','takeaway','under the hood','noise','wash','spread','gap','boost','roughly','around','approximately','nearly','almost','several','some ','a few','many','mostly','often','in the reverse','run of the machine','point at','fits?','no exact size','not fully','e\\.g\\.','i\\.e\\.','etc','vs\\.?',' via ','per se','in fact','of course','note that','respectively','like-for-like','back to back','on the fly','ballpark','rule of thumb','sanity','quick','deep dive','drill','bottleneck','head ?room','trade-?off','caveat','culprit','smoking','suspect','trivial','robust','leverage','utilize','thus','hence','whereas','albeit','whilst','moreover','furthermore','nevertheless','notwithstanding','aforementioned','carries','reached','gave','gives','holds the same','clean','dirty','warm','cold','hot ','quiet','busy','settle','drift','moved','moves','stays','shift','swing','bump','dip','spike','plateau','flat','steady','stable','cause','driven','thanks to','due to','owing','in order to','so as to','as well as','in terms of','with respect to','with regard','as such','per ']
for p in pats:
    ms=list(re.finditer(p,txt,flags=re.I))
    if not ms: continue
    seen=set(); out=[]
    for m in ms:
        ctx=txt[max(0,m.start()-50):m.end()+50].replace('\n',' ')
        key=ctx[35:75]
        if key in seen: continue
        seen.add(key); out.append(ctx)
    print(f'== {p}: {len(ms)} hits, {len(out)} distinct')
    for o in out[:5]: print('   ',o)
