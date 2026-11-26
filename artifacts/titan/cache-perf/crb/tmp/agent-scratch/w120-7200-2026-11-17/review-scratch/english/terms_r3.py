import re, collections
body=open('body-r3.txt').read()
svg=open('svg-r3.txt').read()
titles=open('titles-r3.txt').read()
i=body.find('Words used here'); j=body.find('## 1. Is the new')
k=body.find('## References')
words=body[i:j]
main=body[:i]+body[j:k]
refs=body[k:]
print('wordlist chars',len(words),'main chars',len(main),'refs chars',len(refs))
srcs={'main':main,'svg':svg,'titles':titles,'refs':refs}
cands=collections.defaultdict(lambda: collections.Counter())
for name,txt in srcs.items():
    for m in re.finditer(r"[A-Za-z%][A-Za-z0-9_./\-]*", txt):
        t=m.group(0).strip('.,')
        if re.search(r'^R/|^S/|^/home',t): continue
        if (re.fullmatch(r'[A-Z]{2,}[a-z]?',t) or re.search(r'[a-z][A-Z]',t) or '_' in t or re.search(r'[A-Za-z]\d|\d[A-Za-z]',t) or re.search(r'\.(c|sh|txt|md|json|csv|py)$',t)):
            cands[t][name]+=1
for t in sorted(cands):
    inw = t in words
    print(f'{t:28s} {dict(cands[t])} in_wordlist={inw}')
