import re, sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1])
def page(n):
    return re.sub(r'\s+', ' ', r.pages[n-1].extract_text() or '')
wanted = [(54, ['exclusive', 'allocation policy']), (55, ['shared between', 'LCC', 'LCN', 'exclusive']),
          (63, ['CAL', 'two devices']), (335, ['percentage', 'artition']), (336, ['percentage', 'cmax', '7-bit', 'occupancy']),
          (1038, ['lbt_cfg_ctl', '0xA30']), (1039, ['hnf_mode', 'lcn_mode', 'slc_cmax_allowed', 'lcc_cmax_allowed', '0b1111111']),
          (1041, ['way_reserve', '0xA38']), (1216, ['LCC', 'LCN', 'HBT', 'LBT'])]
for n, keys in wanted:
    t = page(n)
    print(f'=== page {n} ({len(t)} chars)')
    for k in keys:
        m = re.search(re.escape(k), t)
        if not m:
            print(f'  [{k}] NOT FOUND'); continue
        s = max(0, m.start()-200); e = min(len(t), m.end()+260)
        print(f'  [{k}] ...{t[s:e]}...')
