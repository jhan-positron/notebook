import fitz, sys
p = '/home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf'
d = fitz.open(p)
print('pages', len(d))
for key in ['FLow control unIT', 'all packets consist of a single flit', 'basic unit of transfer in the Link layer']:
    for i, pg in enumerate(d):
        t = pg.get_text()
        k = t.find(key)
        if k >= 0:
            lines = [l for l in t.strip().split('\n') if l.strip()]
            print('KEY', repr(key), 'pdf index (1-based)', i+1, 'zero-based', i, 'footer', lines[-4:])
            print('   ', repr(t[max(0,k-200):k+300]))
# title page info
t0 = d[0].get_text()
print(repr(t0[:600]))
print(d.metadata)
