import fitz, sys, re
trm='/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf'
def norm(s): return re.sub(r'\s+',' ',s)
d=fitz.open(trm); print('TRM pages', len(d))
def find(pat, lo=0, hi=None):
    out=[]
    for i in range(lo, hi or len(d)):
        t=norm(d[i].get_text())
        if pat in t: out.append(i+1)
    return out
def show(page1, pats, ctx=300):
    t=norm(d[page1-1].get_text())
    print('  page(1-based index) %d, footer: %s'%(page1, t[-90:]))
    for p in pats:
        i=t.find(p)
        print('   [%s]: %s'%(p[:50], ('...'+t[max(0,i-ctx):i+len(p)+ctx]+'...') if i>=0 else 'NOT FOUND'))
show(12,['scalable and configurable coherent'])
show(13,['RN-F','CHI Issue B','CHI Issue G'],ctx=200)
show(51,['Each XP supports four CHI channels'])
show(250,['CXL IDE can be enabled'])
show(621,['256B Flit mode-capable'])
show(2119,['Table A-2'],ctx=400)
show(2120,['Data_Width','Fixed to 256'],ctx=500)
print('pages with "Fixed to 256":', find('Fixed to 256'))
print('pages with "Flit mode":', find('Flit mode')[:30])
print('pages with "PCIe":', find('PCIe')[:30])
