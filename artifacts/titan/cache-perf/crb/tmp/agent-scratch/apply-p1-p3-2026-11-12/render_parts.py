#!/usr/bin/env python3
"""Render parts of a report file with the offline headless browser and crop the white space.
A part page is lines 1 to 47 of the report (head and style) plus the chosen lines plus </main>.
Usage: render_parts.py <report.html> <out dir> name:first-last[:width] ..."""
import subprocess, sys, os
from PIL import Image, ImageChops
src, out = sys.argv[1], sys.argv[2]
CH = "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/render/chrome.sh"
L = open(src, encoding="utf-8").read().split("\n")
os.makedirs(out, exist_ok=True)
for spec in sys.argv[3:]:
    parts = spec.split(":")
    name, (a, b) = parts[0], map(int, parts[1].split("-"))
    width = int(parts[2]) if len(parts) > 2 else 1000
    page = os.path.join(out, name + ".html"); png = os.path.join(out, name + ".png")
    open(page, "w", encoding="utf-8").write("\n".join(L[:47] + L[a - 1:b] + ["</main>"]))
    r = subprocess.run([CH, "--hide-scrollbars", f"--window-size={width},9000", f"--screenshot={png}", "file://" + os.path.abspath(page)],
                       capture_output=True, text=True)
    im = Image.open(png).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    im = im.crop((0, 0, im.size[0], min(im.size[1], box[3] + 24)))
    im.save(png)
    print(name, im.size, "returncode", r.returncode)
