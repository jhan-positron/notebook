"""Render every figure of one figure module to PNG.

Usage: python3 render_one.py figs/<module>.py [OUT_DIR]
A module exposes b1(), b2(), ... (base) or fig() / figs() (change diagram).
Each returned HTML holds one <svg id="..."> which is rendered to
OUT_DIR/<id>.png at 2x width (max 1600 px) on a white background.
"""
import importlib.util
import os
import re
import sys

import cairosvg

G = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, G)
sys.path.insert(0, os.path.join(G, "figs"))

path = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(G, "png")
os.makedirs(out, exist_ok=True)
spec = importlib.util.spec_from_file_location("figmod", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

htmls = []
for name in sorted(dir(mod)):
    if re.fullmatch(r"b\d+[a-z]?", name) and callable(getattr(mod, name)):
        htmls.append(getattr(mod, name)())
if hasattr(mod, "figs"):
    htmls.extend(mod.figs())
elif hasattr(mod, "fig"):
    htmls.append(mod.fig())

n = 0
for h in htmls:
    for blob in re.findall(r"(<svg id=\"[A-Za-z0-9_-]+\".*?</svg>)", h, flags=re.S):
        fid = re.search(r'<svg id="([A-Za-z0-9_-]+)"', blob).group(1)
        w = int(re.search(r'viewBox="0 0 (\d+) (\d+)"', blob).group(1))
        non_ascii = [c for c in blob if ord(c) > 127]
        if non_ascii:
            print(f"WARNING {fid}: {len(non_ascii)} non-ASCII chars: {sorted(set(non_ascii))[:5]}")
        p = os.path.join(out, f"{fid}.png")
        cairosvg.svg2png(bytestring=blob.encode("utf-8"), write_to=p,
                         output_width=min(1600, w * 2), background_color="white")
        print(p)
        n += 1
print(f"{n} figure(s) rendered")
