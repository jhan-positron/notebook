import fitz, sys, re
trm='/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf'
def norm(s): return re.sub(r'\s+',' ',s).replace('ﬁ','fi').replace('ﬂ','fl').replace('ﬀ','ff').replace('ﬃ','ffi')
d=fitz.open(trm)
def show(page1, pats, ctx=300):
    t=norm(d[page1-1].get_text())
    for p in pats:
        i=t.find(p)
        print('  p%d [%s]: %s'%(page1, p[:50], ('...'+t[max(0,i-ctx):i+len(p)+ctx]+'...') if i>=0 else 'NOT FOUND'))
show(12,['scalable and configurable','CHI interconnect'])
show(621,['Flit mode'],ctx=350)
show(839,['Flit mode'],ctx=250)
# PCIe 6 mention?
for i in range(len(d)):
    t=norm(d[i].get_text())
    if re.search(r'PCIe ?6|PCI Express 6|PCIe 6\.0', t): print('PCIe 6 on page', i+1)
