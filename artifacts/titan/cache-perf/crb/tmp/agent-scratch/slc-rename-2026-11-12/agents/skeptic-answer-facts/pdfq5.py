import fitz, re
trm='/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf'
def norm(s): return re.sub(r'\s+',' ',s).replace('ﬁ','fi').replace('ﬂ','fl').replace('ﬀ','ff').replace('ﬃ','ffi')
d=fitz.open(trm)
n=0
for i in range(len(d)):
    t=norm(d[i].get_text())
    for m in re.finditer(r'Compute Express Link', t):
        print('p%d: ...%s...'%(i+1, t[max(0,m.start()-120):m.end()+160])); n+=1
        if n>=4: break
    if n>=4: break
# flit definition in TRM glossary?
n=0
for i in range(len(d)):
    t=norm(d[i].get_text())
    for m in re.finditer(r'[Ff]lit\b[^.]{0,40}(is|are) (a|the|an)\b', t):
        print('flitdef p%d: ...%s...'%(i+1, t[max(0,m.start()-100):m.end()+200])); n+=1
        if n>=5: break
    if n>=5: break
