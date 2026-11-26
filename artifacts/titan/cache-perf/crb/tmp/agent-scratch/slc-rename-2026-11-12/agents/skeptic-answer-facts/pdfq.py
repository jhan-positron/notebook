import fitz, sys, re
chi='/home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf'
trm='/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf'
def norm(s): return re.sub(r'\s+',' ',s)
def show(path, page_index, pats, ctx=220):
    d=fitz.open(path)
    t=norm(d[page_index].get_text())
    for p in pats:
        i=t.find(p)
        print('   [%s] idx %d: %s'%(p[:40], i, t[max(0,i-ctx):i+len(p)+ctx] if i>=0 else 'NOT FOUND'))
d=fitz.open(chi); print('CHI pages', len(d))
# printed page numbers equal the PDF page index (per task): page 32 -> index 32? check label
for idx in (31,32,33):
    t=norm(d[idx].get_text())
    print('CHI idx',idx,'tail:',t[-80:], '| has Flit def:', 'FLow control unIT' in t)
print('--- CHI p32')
show(chi,32,['FLow control unIT','PHysical layer transfer unIT','For CHI, all flits consist','For CHI, all packets consist','A packet can be made up'])
for idx in (454,455,456):
    t=norm(d[idx].get_text()); print('CHI idx',idx,'has basic unit:', 'A flit is the basic unit of transfer' in t, '| head:', t[:90])
show(chi,455,['A flit is the basic unit of transfer'])
for idx in (517,518,519):
    t=norm(d[idx].get_text()); print('CHI idx',idx,'has L-Credit sentence:', 'consumes one L-Credit' in t)
show(chi,518,['consumes one L-Credit'])
