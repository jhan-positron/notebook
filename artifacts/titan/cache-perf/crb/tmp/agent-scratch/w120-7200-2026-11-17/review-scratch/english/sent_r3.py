import re
txt=open('body-r3.txt').read()
k=txt.find('## References')
lines=txt.split('\n')
out=[]
for n,ln in enumerate(lines,1):
    for cell in ln.split(' | '):
        c=cell.strip()
        if not c: continue
        parts=re.split(r'(?<=[.?!])\s+(?=[A-Z"(\[0-9])',c)
        for p in parts:
            w=len(p.split())
            flags=[]
            if ';' in p: flags.append('SEMI')
            for kw in ['because','since','which means','so that',', so ',', which',' while ',' although ',' whereas ']:
                if kw in p: flags.append(kw.strip())
            if w>=28 or flags:
                out.append((n,w,flags,p))
for n,w,f,p in out:
    print(f'L{n} w={w} {f}\n   {p}\n')
print('SEMICOLONS body:', txt.count(';'), 'svg:', open('svg-r3.txt').read().count(';'), 'titles:', open('titles-r3.txt').read().count(';'))
