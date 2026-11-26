import fitz, sys, re
chi='/home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf'
def norm(s): return re.sub(r'\s+',' ',s)
d=fitz.open(chi)
def show(idx, pats, ctx=260):
    t=norm(d[idx].get_text())
    for p in pats:
        i=t.find(p)
        print('   [%s] p%d: %s'%(p[:40], idx+1, ('...'+t[max(0,i-ctx):i+len(p)+ctx]+'...') if i>=0 else 'NOT FOUND'))
show(31,['FLow control unIT','PHysical layer transfer unIT','For CHI, all'])
show(454,['A flit is the basic unit of transfer'])
show(517,['consumes one L-Credit'])
t=norm(d[0].get_text()); print('title page:', t[:300])
t=norm(d[1].get_text()); print('p2:', t[:400])
