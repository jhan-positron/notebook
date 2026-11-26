import re, sys, subprocess
WT, HEAD, D = sys.argv[1:4]
f=None; n=0; hunk=[]; out=[]; fence=set()
def fenced_lines(f):
    txt=subprocess.run(['git','-C',WT,'show',f'{HEAD}:{f}'],capture_output=True,text=True).stdout.split('\n')
    s=set(); inside=False
    for i,l in enumerate(txt,1):
        if l.lstrip().startswith('```'): inside=not inside; s.add(i)
        elif inside: s.add(i)
    return s
def flush():
    ctx=[w for k,w,_ in hunk if k==' ']
    if ctx:
        for k,w,loc in hunk:
            if k=='+' and w>1.25*max(ctx): out.append((loc,w,max(ctx)))
for raw in open(D, encoding='utf-8', errors='replace'):
    l=raw.rstrip('\n')
    if l.startswith('+++ '):
        flush(); hunk=[]; f=l[4:]; f=f[2:] if f.startswith('b/') else f; n=0
        fence=fenced_lines(f) if f.endswith('.md') else set(); continue
    m=re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)', l)
    if m: flush(); hunk=[]; n=int(m.group(1)); continue
    if l.startswith('-') or l.startswith('\\'): continue
    k=l[0] if l else ' '; b=l[1:]
    if f and f.endswith('.md') and b.strip() and n not in fence and not re.match(r'^\s*(\||\S+://)', b): hunk.append((k,len(b),f'{f}:{n}'))
    n+=1
flush()
for loc,w,m in out: print(loc,'width',w,'hunk unchanged max',m)
