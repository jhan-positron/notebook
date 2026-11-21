#!/usr/bin/env python3
"""Geometry check of the hierarchy figure (the first <svg> of the report).

For every box (rect) it lists the text lines inside, their rendered width in
IBM Plex Sans, and the smallest horizontal padding. It also checks that the
boxes of the two rows share x and width column by column, and that nothing
leaves the viewBox. Exit code 1 if any check fails.
Usage: check_geometry.py <html or svg file> [min_padding_px]
"""
import re, sys, html
from PIL import ImageFont
import os
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_f = {}
def tw(text, size, weight):
    if weight not in _f:
        _f[weight] = ImageFont.truetype(f"{FD}/IBMPlexSans-{weight}.ttf", 1000)
    return _f[weight].getlength(text) * size / 1000.0
src = open(sys.argv[1], encoding="utf-8").read()
MINPAD = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
m = re.search(r"<svg viewBox=\"0 0 (\d+) (\d+)\" role=\"img\".*?</svg>", src, flags=re.S)
svg = m.group(0); W, H = int(m.group(1)), int(m.group(2))
base = float(re.search(r'<g font-size="([\d.]+)" fill="#1b1f24">', svg).group(1))
def attrs(tag):
    return dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
rects = [attrs(t) for t in re.findall(r"<rect [^>]*>", svg)]
texts = []
for t, body in re.findall(r"<text ([^>]*)>(.*?)</text>", svg, flags=re.S):
    a = attrs("<text " + t + ">")
    assert "<" not in body, "nested markup in text: " + body
    texts.append((a, html.unescape(body)))
ok = True
boxes = []
for r in rects:
    x, y, w, h = (float(r[k]) for k in ("x", "y", "width", "height"))
    inside = [(a, s) for a, s in texts if x <= float(a["x"]) <= x + w and y <= float(a["y"]) <= y + h]
    worst = 1e9; rows = []
    for a, s in inside:
        size = float(a.get("font-size", base)); weight = int(a.get("font-weight", 400))
        width = tw(s, size, weight); tx = float(a["x"]); anchor = a.get("text-anchor", "start")
        left = tx - width / 2 if anchor == "middle" else (tx - width if anchor == "end" else tx)
        pad = min(left - x, x + w - (left + width)); worst = min(worst, pad)
        ty = float(a["y"]); vpad = min(ty - size * 0.75 - y, y + h - (ty + size * 0.25))
        rows.append((s, width, pad, vpad))
        if pad < MINPAD or vpad < 3: ok = False
    if x < 0 or y < 0 or x + w > W or y + h > H: ok = False
    boxes.append((x, y, w, h, worst, rows))
    print(f"box x={x:g} y={y:g} w={w:g} h={h:g}  min horizontal padding {worst:.1f} px")
    for s, width, pad, vpad in rows:
        flag = "" if pad >= MINPAD and vpad >= 3 else "   <-- TOO TIGHT"
        print(f"    {width:6.1f} px  pad {pad:5.1f}  vpad {vpad:5.1f}  {s}{flag}")
# column alignment: group boxes by x
cols = {}
for b in boxes: cols.setdefault((b[0], b[2]), []).append(b)
print(f"\ncolumns (x, width) -> boxes: " + ", ".join(f"({k[0]:g},{k[1]:g})x{len(v)}" for k, v in sorted(cols.items())))
if any(len(v) != 2 for v in cols.values()) or len(cols) != 6:
    ok = False; print("ALIGNMENT FAIL: every column must have exactly 2 boxes with identical x and width, and there must be 6 columns")
# gaps between neighbouring columns and right margin
xs = sorted(cols)
for (x1, w1), (x2, w2) in zip(xs, xs[1:]):
    if x2 - (x1 + w1) < 8: ok = False; print("GAP FAIL", x1, x2)
print("gaps:", [round(x2 - (x1 + w1), 1) for (x1, w1), (x2, w2) in zip(xs, xs[1:])], " right margin:", W - (xs[-1][0] + xs[-1][1]))
# free text (row captions): must end left of the first column
for a, s in texts:
    if float(a["x"]) < xs[0][0]:
        width = tw(s, float(a.get("font-size", base)), int(a.get("font-weight", 400)))
        end = float(a["x"]) + width
        print(f"caption {s!r}: x {float(a['x']):g} to {end:.1f} (first box starts at {xs[0][0]:g})")
        if end > xs[0][0] - 4: ok = False; print("CAPTION OVERLAP")
print("viewBox", W, H, " scale at 880 px column:", round(880 / W, 3), " base text renders at", round(base * 880 / W, 2), "px")
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
