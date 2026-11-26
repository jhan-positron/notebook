import re, collections
body=open('body.txt').read()
svg=open('svg.txt').read()
titles=open('titles.txt').read()
# split body: word list section and rest
i=body.find('Words used here'); j=body.find('## 1. Is the new')
k=body.find('## References')
words=body[i:j]
main=body[:i]+body[j:k]
refs=body[k:]
alltxt=main+'\n'+svg+'\n'+titles
# candidate tokens: all-caps >=2, tokens with digits+letters, tokens with underscore, CamelCase, .ext
cands=collections.Counter()
for m in re.finditer(r"[A-Za-z][A-Za-z0-9_./\-]*", alltxt):
    t=m.group(0).strip('.,')
    if re.search(r'^R/|^S/',t): continue
    if (re.fullmatch(r'[A-Z]{2,}[a-z]?',t) or re.search(r'[a-z][A-Z]',t) or '_' in t or re.search(r'[A-Za-z]\d|\d[A-Za-z]',t) or re.search(r'\.(c|sh|txt|md|json|csv|py)$',t)):
        cands[t]+=1
for t,c in sorted(cands.items()):
    inw = t in words
    print(f'{t:28s} n={c:4d} in_wordlist={inw}')
