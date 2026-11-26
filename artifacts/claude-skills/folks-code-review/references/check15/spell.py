import re, sys
from spellchecker import SpellChecker
sp=SpellChecker(); allow=set(w.strip() for w in open(sys.argv[2]))
seen={}; hits=[]
def resolves(w):
    for p in ('un','de','re','non','sub','pre'):
        if w.startswith(p) and len(w)>len(p)+2 and sp.known([w[len(p):]]): return True
    for s in ('s','es','ed','ize','ized','ation','ization'):
        if w.endswith(s) and len(w)>len(s)+2 and sp.known([w[:-len(s)]]): return True
    return False
def prefix_of_code(w):
    return len(w)>=4 and any(a.startswith(w) and len(a)>len(w) for a in allow)
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    loc,_,rest=line.rstrip('\n').partition('\t'); kind,_,text=rest.partition('\t')
    t=re.sub(r'`[^`]*`',' ',text); t=re.sub(r'\b\w*[_0-9]\w*\b|\b\w+[A-Z]\w*\b',' ',t)
    words=[w.lower() for w in re.findall(r'\b[A-Za-z][a-z]{2,}\b',t)]
    for w in sp.unknown(words):
        if w in allow or (w.endswith('s') and w[:-1] in allow) or (w.endswith('es') and w[:-2] in allow): seen.setdefault(w,[]).append(loc)
        elif resolves(w): seen.setdefault('(affix)'+w,[]).append(loc)
        elif prefix_of_code(w): seen.setdefault('(prefix)'+w,[]).append(loc)
        else: hits.append((loc,w,sp.correction(w)))
from collections import Counter
cnt=Counter(w for _,w,c in set(hits))
for loc,w,c in hits:
    if cnt[w]>=2: print('VOCAB',loc,'|',w,f'(on {cnt[w]} added prose lines of this PR: author vocabulary, read once)')
    else: print('BAD',loc,'|',w,'->',c or '(no correction: run-together or shifted space? read it)')
for w,l in sorted(seen.items()): print('EXCUSED',w,len(l),l[0])
