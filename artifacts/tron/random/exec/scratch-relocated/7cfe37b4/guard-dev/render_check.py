import sys, json
from playwright.sync_api import sync_playwright
page_path, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch()
    errs = []
    for width in (360, 768, 1200):
        pg = b.new_page(viewport={"width": width, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto("file://" + page_path)
        pg.wait_for_timeout(300)
        sw = pg.evaluate("document.documentElement.scrollWidth")
        # text elements that stick out of their svg's box
        over = pg.evaluate("""() => { const out=[]; document.querySelectorAll('svg').forEach(s=>{ const r=s.getBoundingClientRect();
            s.querySelectorAll('text').forEach(t=>{ const q=t.getBoundingClientRect(); if(q.right>r.right+1||q.left<r.left-1) out.push(s.id+': '+t.textContent+' ['+Math.round(q.left-r.left)+','+Math.round(q.right-r.left)+'] of '+Math.round(r.width)); }); }); return out; }""")
        print("width", width, "scrollWidth", sw, "overflow" if sw > width else "ok", "| svg text outside:", over[:6])
        if width == 1200:
            for sel in ("#chartStall", "#chartSpeed", "#stripBefore", "#stripAfter", ".flow", ".budget"):
                pg.locator(sel).first.screenshot(path=f"{out}/{sel.strip('#.')}.png")
            pg.locator(".card").nth(1).screenshot(path=f"{out}/card-bars.png")
            pg.locator(".card").nth(2).screenshot(path=f"{out}/card-strip.png")
            pg.locator(".card").nth(0).screenshot(path=f"{out}/card-budget.png")
            pg.screenshot(path=f"{out}/top.png")
        if width == 360:
            pg.locator(".card").nth(1).screenshot(path=f"{out}/card-bars-360.png")
        pg.close()
    print("page errors:", errs)
    b.close()
