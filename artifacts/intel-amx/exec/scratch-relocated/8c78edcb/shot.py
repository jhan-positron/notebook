import sys
from playwright.sync_api import sync_playwright
src, out = sys.argv[1], sys.argv[2]
widths = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [1280, 400]
html = "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'></head><body>" + open(src).read() + "</body></html>"
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in widths:
        pg = b.new_page(viewport={"width": w, "height": 900})
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.set_content(html, wait_until="load")
        pg.wait_for_timeout(400)
        d = pg.evaluate("() => ({scroll: document.documentElement.scrollWidth, w: innerWidth, h: document.documentElement.scrollHeight})")
        print(w, d, "errors:", errs[:3])
        step, y, i = (1300 if w > 600 else 1500), 0, 0
        while y < d["h"]:
            pg.screenshot(path="%s-%d-p%d.png" % (out, w, i), full_page=True, clip={"x": 0, "y": y, "width": w, "height": min(step, d["h"] - y)})
            y += step; i += 1
        print(w, "parts", i)
    b.close()
