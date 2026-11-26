import fitz, sys, re
p = '/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf'
d = fitz.open(p)
print('pages', len(d), d.metadata.get('title'))
def show(i, key=None, w=700):
    t = d[i-1].get_text()
    lines = [l for l in t.strip().split('\n') if l.strip()]
    print(f'--- pdf page (1-based) {i}; first lines {lines[:3]}; last lines {lines[-3:]}')
    if key:
        for m in re.finditer(key, t):
            print('   ', repr(t[max(0, m.start()-w//2): m.end()+w//2]))
    else:
        print(t)
for key in ['Data_Width', 'Fixed to 256']:
    for i, pg in enumerate(d, 1):
        t = pg.get_text()
        if key in t:
            lines = [l for l in t.strip().split('\n') if l.strip()]
            k = t.find(key)
            print('KEY', repr(key), 'pdf page', i, 'footer', lines[-3:], '| header', lines[:2])
            print('    ', repr(t[max(0,k-250):k+250]))
