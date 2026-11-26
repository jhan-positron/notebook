import fitz, re, sys
def scan(path, keys, maxhits=6):
    d = fitz.open(path); print('==', path.split('/')[-1], 'pages', len(d))
    hits = 0
    for i, pg in enumerate(d):
        t = pg.get_text()
        for key in keys:
            k = t.find(key)
            if k >= 0:
                tail = t.strip().split('\n')[-4:]
                print(f'pdf page index {i+1}; key {key!r}; footer lines {tail}')
                print('   ', repr(t[max(0, k-150):k+330]))
                hits += 1
        if hits >= maxhits: break
scan('/home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf', ['FLow control unIT', 'basic unit of transfer in the Link layer'])
