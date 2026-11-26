import re, sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1])
def page(n):
    return re.sub(r'\s+', ' ', r.pages[n-1].extract_text() or '')
t = page(1216); print('=== page 1216 first 600 chars:', t[:600])
print('=== pages containing "Home Bound Transaction" or "HBT" definition-like text (first 8 hits)')
hits = 0
for n in range(1, len(r.pages)+1):
    t = page(n)
    if re.search(r'Home Bound Transaction|LCN Bound Transaction', t):
        m = re.search(r'Home Bound Transaction|LCN Bound Transaction', t)
        print(f'  page {n}: ...{t[max(0,m.start()-100):m.end()+120]}...'); hits += 1
        if hits >= 8: break
print('=== pages with "exclusive for data lines"')
for n in range(1, len(r.pages)+1):
    if 'exclusive for data lines' in page(n): print('  page', n)
