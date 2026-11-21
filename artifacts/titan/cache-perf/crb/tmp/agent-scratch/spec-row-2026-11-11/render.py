#!/usr/bin/env python3
"""Render the hierarchy figure (the first <svg role="img"> of an HTML file) to PNG
with the page's font (IBM Plex Sans, copied into ./fonts). Needs cairosvg.
Usage: render.py <html file> <out.png> [scale, default 1.4286 = 1320 px wide for a 924 viewBox]"""
import sys, re, os, tempfile
here = os.path.dirname(os.path.abspath(__file__))
conf = os.path.join(tempfile.mkdtemp(), "fonts.conf")
open(conf, "w").write(f'<?xml version="1.0"?>\n<fontconfig><dir>{here}/fonts</dir><cachedir>{os.path.dirname(conf)}/cache</cachedir></fontconfig>\n')
os.environ["FONTCONFIG_FILE"] = conf
import cairosvg
src, out = sys.argv[1], sys.argv[2]
scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.4286
s = open(src, encoding="utf-8").read()
s = re.search(r"<svg viewBox=\"0 0 \d+ \d+\" role=\"img\".*?</svg>", s, flags=re.S).group(0)
s = s.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans" ', 1)
w = int(re.search(r'viewBox="0 0 (\d+) (\d+)"', s).group(1))
cairosvg.svg2png(bytestring=s.encode("utf-8"), write_to=out, output_width=int(w * scale), background_color="white")
print("rendered", out)
