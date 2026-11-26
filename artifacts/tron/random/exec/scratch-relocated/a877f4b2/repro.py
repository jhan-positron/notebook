#!/usr/bin/env python3
"""Reproduce the conversion on a few pages of the C1-Nano PDF with the locally installed pymupdf4llm."""
import sys, fitz, pymupdf4llm
pdf = sys.argv[1]; doc = fitz.open(pdf)
print("pymupdf", fitz.__version__, "pymupdf4llm", pymupdf4llm.__version__, "pages", doc.page_count)
probes = {1: ["We believe that this document", "fill the following survey", "This document is Non-Confidential", "Arm recognizes that we"],
          17: ["high-efficiency", "Regardless of the cluster", "following figure shows an example of a dual", "Example configuration with a C1-Nano dual"],
          247: ["This feld always", "This field always", "Page**248**of**914**", "Page **248** of **914**"]}
for pno, keys in probes.items():
    try:
        md = pymupdf4llm.to_markdown(doc, pages=[pno], show_progress=False)
    except TypeError:
        md = pymupdf4llm.to_markdown(pdf, pages=[pno])
    print(f"\n#### page {pno+1}: md chars={len(md)}")
    for k in keys: print(f"   {k!r:60} count={md.count(k)}")
    if pno == 17:
        open("/tmp/claude-0/-home-jhan-workspace-random/a877f4b2-208b-4fca-b872-04c4b74aec5d/scratchpad/p18_local.md", "w").write(md)

# span-level view of page 18 lines that were dropped in the June conversion, plus one kept line on page 2
def show(pno, needles):
    page = doc[pno]; d = page.get_text("dict")
    clusters = page.cluster_drawings()
    print(f"\n#### page {pno+1}: text blocks={sum(1 for b in d['blocks'] if b['type']==0)} image blocks={sum(1 for b in d['blocks'] if b['type']==1)} drawing clusters={len(clusters)} drawings={len(page.get_drawings())}")
    for b in d["blocks"]:
        if b["type"] != 0: continue
        for l in b["lines"]:
            txt = "".join(s["text"] for s in l["spans"])
            if any(n in txt for n in needles):
                lb = fitz.Rect(l["bbox"])
                hit = [c for c in clusters if c.intersects(lb)]
                print(f"  LINE {txt[:90]!r}\n     bbox={[round(x,1) for x in lb]} dir={l['dir']} intersects_cluster={bool(hit)}")
                for s in l["spans"]:
                    print(f"     span font={s['font']!r} flags={s['flags']} size={s['size']} text={s['text'][:70]!r}")
show(1, ["We believe", "fill the following", "Arm recognizes", "Non-Confidential"])
show(17, ["high-efficiency", "Regardless", "following figure", "Example configuration", "C1-Nano core is a"])

# ---- page 262: where do the ~~Po~~ ~~et~~ ~~OO~~ fragments come from? ----
page = doc[261]; d = page.get_text("dict")
frag = {"Po","et","OO","GG","Pri","oT","OP","IE","JL","DR","L","ee","oo","P"}
print(f"\n#### page 262: drawings={len(page.get_drawings())} clusters={len(page.cluster_drawings())} rotation={page.rotation}")
n=0
for b in d["blocks"]:
    if b["type"] != 0: continue
    for l in b["lines"]:
        for s in l["spans"]:
            if s["text"].strip() in frag:
                n+=1
                if n<=12: print(f"  frag {s['text']!r:6} font={s['font']} size={s['size']} flags={s['flags']} color={s['color']:06x} dir={l['dir']} bbox={[round(x,1) for x in s['bbox']]}")
print(f"  fragment spans on page: {n}")
# any text spans with invisible render mode / white color / rotated direction?
dirs = {}; colors = {}
for b in d["blocks"]:
    if b["type"] != 0: continue
    for l in b["lines"]:
        dirs[l["dir"]] = dirs.get(l["dir"],0)+1
        for s in l["spans"]: colors[s["color"]] = colors.get(s["color"],0)+1
print("  line directions:", dirs); print("  span colors:", {f'{k:06x}':v for k,v in colors.items()})
try:
    md262 = pymupdf4llm.to_markdown(doc, pages=[261], show_progress=False)
    import re
    print("  local reconversion of page 262: ~~ fragments =", len(re.findall(r"~~[^~]*~~", md262)), " 'feld' =", md262.count("feld"), " 'field' =", md262.count("field"))
except Exception as e: print("  reconversion failed:", e)
