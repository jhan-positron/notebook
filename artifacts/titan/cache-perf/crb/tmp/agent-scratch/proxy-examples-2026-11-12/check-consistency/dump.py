import re,sys,html
L=open('../worker/draft-full.html').read().split('\n')
out=[]
for i,l in enumerate(L,1):
    if i>=470 and not re.search(r"'[^']{25,}'",l): continue
    t=l if i>=470 else html.unescape(re.sub(r'<[^>]+>',' ',l))
    t=re.sub(r'\s+',' ',t).strip()
    if t: out.append(f'{i}: {t}')
open('text.txt','w').write('\n'.join(out))
