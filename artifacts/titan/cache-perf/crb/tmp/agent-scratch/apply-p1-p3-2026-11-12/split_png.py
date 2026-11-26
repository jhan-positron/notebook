#!/usr/bin/env python3
"""Cut a tall screenshot into pieces of at most H pixels (default 1500) with 60 pixels of overlap, for viewing.
Usage: split_png.py <png> [H]"""
import sys
from PIL import Image
p = sys.argv[1]; H = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
im = Image.open(p); w, h = im.size
if h <= H + 200:
    print(p.split("/")[-1], (w, h), "one piece"); sys.exit(0)
k, y = 1, 0
while y < h:
    y2 = min(h, y + H)
    im.crop((0, y, w, y2)).save(p.replace(".png", f".part{k}.png"))
    print(p.split("/")[-1], f"part{k}", (y, y2))
    if y2 == h: break
    y = y2 - 60; k += 1
