import re
txt=open('body-r3.txt').read()
k=txt.find('## References')
for n,ln in enumerate(txt[:k].split('\n'),1):
    for cell in ln.split(' | '):
        c=cell.strip()
        for p in re.split(r'(?<=[.?!])\s+(?=[A-Z"(\[0-9])',c):
            if re.search(r': [a-z0-9"A-Z]', p) and len(p.split())>=8:
                print(f'L{n} w={len(p.split())}: {p}\n')
