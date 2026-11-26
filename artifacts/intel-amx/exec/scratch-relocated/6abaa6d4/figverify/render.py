# Extract every <svg> of a page to its own file, render to PNG at scale 2.
# For figures 2 and 12 also render a copy with the monospace font replaced by DejaVu Sans Mono.
# usage: render.py <page.html> <out dir>
import sys, re, os
import cairosvg

page, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
src = open(page, encoding="utf-8").read()
svgs = re.findall(r"<svg\b.*?</svg>", src, flags=re.S)
print("svg elements:", len(svgs))
for i, s in enumerate(svgs, 1):
    if "xmlns=" not in s[:400]:
        s = s.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    p = os.path.join(out, "fig%02d.svg" % i)
    open(p, "w", encoding="utf-8").write(s)
    cairosvg.svg2png(bytestring=s.encode("utf-8"), write_to=p[:-4] + ".png", scale=2, background_color="white")
    n_mono = len(re.findall(r"JetBrains Mono", s))
    m = re.search(r'viewBox="([^"]+)"', s)
    print("fig%02d" % i, "viewBox", m.group(1) if m else None, "bytes", len(s), "mono refs", n_mono)
    if n_mono:
        s2 = re.sub(r"font-family=\"[^\"]*JetBrains Mono[^\"]*\"", 'font-family="DejaVu Sans Mono"', s)
        s2 = re.sub(r"font-family:\s*[^;\"]*JetBrains Mono[^;\"]*", "font-family: 'DejaVu Sans Mono'", s2)
        open(p[:-4] + "_mono.svg", "w", encoding="utf-8").write(s2)
        cairosvg.svg2png(bytestring=s2.encode("utf-8"), write_to=p[:-4] + "_mono.png", scale=2, background_color="white")
