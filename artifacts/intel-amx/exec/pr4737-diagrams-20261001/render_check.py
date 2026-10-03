"""Render every inline SVG of the generated page to PNG for a layout check.

Usage: python3 render_check.py PAGE.html OUT_DIR
Traps handled (memory svg-render-check): numeric entities only (the page uses
none inside SVG), per-figure marker ids, no page CSS needed (all styles are
inline attributes), explicit output width.
"""
import os
import re
import sys

import cairosvg

page, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
src = open(page, encoding="utf-8").read()
svgs = re.findall(r"<svg id=\"([a-z0-9]+)\".*?</svg>", src, flags=re.S)
blobs = re.findall(r"(<svg id=\"[a-z0-9]+\".*?</svg>)", src, flags=re.S)
for fid, blob in zip(svgs, blobs):
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', blob)
    w = int(m.group(1))
    path = os.path.join(out, f"{fid}.png")
    cairosvg.svg2png(bytestring=blob.encode("utf-8"), write_to=path,
                     output_width=min(1600, w * 2), background_color="white")
    print(path)
