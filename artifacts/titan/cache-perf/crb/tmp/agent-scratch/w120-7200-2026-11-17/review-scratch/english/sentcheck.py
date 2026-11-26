import re
txt=open('body.txt').read()
lines=txt.split('\n')
# stop at references? keep all but mark
out=[]
for n,ln in enumerate(lines,1):
    for cell in ln.split(' | '):
        c=cell.strip()
        if not c: continue
        # split sentences
        parts=re.split(r'(?<=[.?!])\s+(?=[A-Z"(\[])',c)
        for p in parts:
            w=len(p.split())
            flags=[]
            if ';' in p: flags.append('SEMI')
            for k in ['because','since','which means','so that',', so ',' so ', 'So ', ' but ', ', which', ' that ', ' while ', ' although ', ' whereas ', ' when ', ' where ', ' if ']:
                if k in p: flags.append(k.strip())
            if w>=30 or 'SEMI' in flags or any(f in flags for f in ['because','since','which means','so that',', so','so']):
                out.append((n,w,flags,p))
for n,w,f,p in out:
    print(f'L{n} w={w} {f}\n   {p}\n')
