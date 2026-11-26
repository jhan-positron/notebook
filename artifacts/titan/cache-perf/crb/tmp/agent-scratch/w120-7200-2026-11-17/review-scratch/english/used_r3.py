import re
body=open('body-r3.txt').read()
svg=open('svg-r3.txt').read()
titles=open('titles-r3.txt').read()
i=body.find('Words used here'); j=body.find('## 1. Is the new')
words=body[i:j]
rest=body[:i]+body[j:]+'\n'+svg+'\n'+titles
# word list terms: odd lines after header
lines=[l for l in words.split('\n')[1:] if l.strip()]
terms=lines[0::2]
defs=lines[1::2]
for t,d in zip(terms,defs):
    for part in [p.strip() for p in t.split(',')]:
        n=len(re.findall(re.escape(part), rest, flags=re.I))
        print(f'{part:40s} uses outside list: {n}')
print('---- kernel uses without read/old/new/Linux context')
allt=body+'\n'+svg
for m in re.finditer(r'kernel', allt):
    ctx=allt[max(0,m.start()-25):m.end()+25].replace('\n',' ')
    pre=allt[max(0,m.start()-12):m.start()]
    if re.search(r'(read|Read|old|Old|new|New|Linux|Old read|old-)\s*$', pre): continue
    print(repr(ctx))
