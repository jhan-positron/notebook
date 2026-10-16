import re, sys, subprocess
WT, HEAD, D = sys.argv[1:4]
f=None; n=0; fence=set()
def ok(f): return f and (f.endswith('.md') or re.match(r'(h|src|t|doc)/', f) and f.endswith(('.hpp','.cpp','.h','.c','.inl')))
def fenced_lines(f):
    txt=subprocess.run(['git','-C',WT,'show',f'{HEAD}:{f}'],capture_output=True,text=True).stdout.split('\n')
    s=set(); inside=False
    for i,l in enumerate(txt,1):
        if l.lstrip().startswith('```'): inside=not inside; s.add(i)
        elif inside: s.add(i)
    return s
for raw in open(D, encoding='utf-8', errors='replace'):
    l=raw.rstrip('\n')
    if l.startswith('+++ '):
        f=l[4:]; f=f[2:] if f.startswith('b/') else f; n=0
        fence=fenced_lines(f) if f.endswith('.md') else set(); continue
    m=re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)', l)
    if m: n=int(m.group(1)); continue
    if l.startswith('-') or l.startswith('\\'): continue
    if l.startswith('+') and ok(f):
        b=l[1:]
        if f.endswith('.md'):
            if n not in fence: print(f'{f}:{n}\tM\t{b}')
        else:
            cm=re.search(r'(//|/\*|^\s*\*\s)(.*)', b); st=re.findall(r'"((?:[^"\\]|\\.)*)"', b)
            if cm: print(f'{f}:{n}\tC\t{cm.group(2)}')
            elif st: print(f'{f}:{n}\tS\t{" ".join(st)}')
    n+=1
