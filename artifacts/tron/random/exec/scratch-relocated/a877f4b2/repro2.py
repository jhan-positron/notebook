#!/usr/bin/env python3
import sys, re, fitz, pymupdf4llm
pdf, txtpath = sys.argv[1], sys.argv[2]; doc = fitz.open(pdf)
def conv(pno): return pymupdf4llm.to_markdown(doc, pages=[pno], show_progress=False)
# page 248 table: how is "This field always returns" rendered locally?
md = conv(247)
print("page 248 local: 'field'=%d 'feld'=%d 'This'=%d" % (md.count("field"), md.count("feld"), md.count("This")))
for m in re.finditer(r".{0,40}(field|feld).{0,40}", md): print("   ...", m.group(0).replace("\n","\\n"))
print("   table rows (lines starting with |):", sum(1 for l in md.splitlines() if l.startswith("|")))
# page 20: the dropped "Regardless of the cluster configuration" line
md20 = conv(19); print("\npage 20 local: 'Regardless of the cluster configuration'=%d" % md20.count("Regardless of the cluster configuration"))
# first txt page with the per-register "available in all configurations" line
pages = open(txtpath, encoding="utf-8", errors="replace").read().split("\f")
p = next(i for i,pg in enumerate(pages) if "available in all con" in pg)
mdp = conv(p); print(f"\npage {p+1} local: 'available in all configurations'={mdp.count('available in all configurations')}  'Configurations'={mdp.count('Configurations')}")
for m in re.finditer(r".{0,60}available in all con.{0,20}", mdp): print("   ...", m.group(0).replace("\n","\\n"))
# page 262 white spans: what text?
d = doc[261].get_text("dict"); w = [s["text"] for b in d["blocks"] if b["type"]==0 for l in b["lines"] for s in l["spans"] if s["color"]==0xffffff]
print("\npage 262 white-colored spans:", w)
