import re, sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1])
def page(n):
    return re.sub(r'\s+', ' ', r.pages[n-1].extract_text() or '')
t = page(1040); print('=== page 1040'); 
for k in ['0xA38', 'lbt_aux_ctl']:
    m = re.search(re.escape(k), t); print(f'  [{k}]', '...'+t[max(0,m.start()-150):m.end()+150]+'...' if m else 'NOT FOUND')
t = page(1039); print('=== page 1039 lcn_mode / hnf_mode descriptions')
for k in ['lcn_mode', 'hnf_mode']:
    for m in list(re.finditer(re.escape(k), t))[1:3]:
        print(f'  [{k}] ...{t[max(0,m.start()-40):m.end()+220]}...')
print('=== glossary search for Home Bound / LCN Bound, pages 1190-1240')
for n in range(1190, 1241):
    t = page(n)
    for k in ['Home Bound', 'LCN Bound', 'Local Coherent Cache', 'Local Coherency Node']:
        m = re.search(k, t)
        if m: print(f'  page {n} [{k}] ...{t[max(0,m.start()-80):m.end()+160]}...')
