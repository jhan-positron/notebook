import sys, re
import fitz
def show(path, pageno_printed, pats, offset=0, width=160):
    doc = fitz.open(path)
    idx = pageno_printed + offset
    txt = doc[idx].get_text()
    print(f"== {path.split('/')[-1]} pdf index {idx} ({len(txt)} chars)")
    for pat in pats:
        for m in re.finditer(pat, txt, re.I):
            s = max(0, m.start()-width); e = min(len(txt), m.end()+width)
            print("   ...", " ".join(txt[s:e].split()), "...")
            break
        else:
            print("   (no match for", pat, ")")
trm = "/home/jhan/workspace/titan/cache-perf/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf"
chi = "/home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf"
d = fitz.open(trm); print("TRM pages:", len(d))
# find the printed page 2120: search a window for 'Data_Width'
for i in range(2110, min(len(d), 2130)):
    t = d[i].get_text()
    if re.search(r"Data_?Width", t, re.I):
        m = re.search(r"Data_?Width.{0,200}", t, re.I | re.S)
        print("TRM pdf index", i, "footer:", " ".join(t.split())[-60:], "|", " ".join(m.group(0).split())[:220])
d2 = fitz.open(chi); print("CHI pages:", len(d2))
for i in (469, 470):
    t = d2[i].get_text()
    for pat in (r"FLITV", r"Figure B13\.14", r"Table B13\.5"):
        m = re.search(pat + r".{0,220}", t, re.S)
        if m: print("CHI pdf index", i, "|", " ".join(m.group(0).split())[:260])
