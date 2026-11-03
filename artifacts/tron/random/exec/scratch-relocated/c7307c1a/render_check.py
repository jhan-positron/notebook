import sys, json
from playwright.sync_api import sync_playwright
path, out = sys.argv[1], sys.argv[2]
res = {"errors": [], "overflow": {}, "figs": {}}
with sync_playwright() as p:
    b = p.chromium.launch()
    for vw in (360, 768, 1200):
        pg = b.new_page(viewport={"width": vw, "height": 900})
        pg.on("pageerror", lambda e: res["errors"].append(f"{vw}: {e}"))
        pg.on("console", lambda m: res["errors"].append(f"{vw} console {m.type}: {m.text}") if m.type in ("error","warning") else None)
        pg.goto("file://" + path); pg.wait_for_timeout(300)
        sw = pg.evaluate("document.documentElement.scrollWidth"); res["overflow"][vw] = {"scrollWidth": sw, "ok": sw <= vw}
        if vw == 1200:
            for fid in ("figA","figB","figC","figD","figE"):
                e = pg.locator("#"+fid); e.screenshot(path=f"{out}/{fid}.png")
                bb = e.bounding_box(); res["figs"][fid] = {"w": bb["width"], "h": bb["height"]}
                # text overflow inside svg: any <text> whose bbox exceeds the svg viewBox width
                ov = pg.evaluate("""(fid)=>{const svg=document.querySelector('#'+fid+' svg');const W=svg.viewBox.baseVal.width,H=svg.viewBox.baseVal.height;const bad=[];svg.querySelectorAll('text').forEach(t=>{const b=t.getBBox();if(b.x+b.width>W+1||b.y+b.height>H+1||b.x<0)bad.push(t.textContent.slice(0,40)+' @'+Math.round(b.x+b.width)+'x'+Math.round(b.y+b.height));});return {W,H,bad};}""", fid)
                res["figs"][fid]["svg_text_overflow"] = ov
            pg.screenshot(path=f"{out}/full.png", full_page=True)
        pg.close()
    b.close()
print(json.dumps(res, indent=1))
