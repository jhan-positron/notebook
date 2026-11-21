import json
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path('/home/jhan/workspace/titan/cache-perf/asimov')
out = Path('/tmp/asimov-mesh-review-browser')
out.mkdir(exist_ok=True)
report = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, timeout=20000, executable_path='/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell', args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1400, 'height': 1000})
    page.goto((root/'asimov-mesh-map.html').as_uri())
    for width in (1400,700):
        page.set_viewport_size({'width':width,'height':1000})
        report[width] = page.evaluate('''() => ({width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          clippedText: [...document.querySelectorAll('svg[viewBox]')].flatMap((svg,i) => {
            const vb = svg.viewBox.baseVal;
            return [...svg.querySelectorAll('text')].flatMap(t => {
              const r=t.getBBox(), m=svg.getCTM().inverse().multiply(t.getCTM());
              const pts=[[r.x,r.y],[r.x+r.width,r.y],[r.x,r.y+r.height],[r.x+r.width,r.y+r.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
              return pts.some(p=>p.x<vb.x-1||p.y<vb.y-1||p.x>vb.x+vb.width+1||p.y>vb.y+vb.height+1)?[{svg:i,text:t.textContent,box:pts.map(p=>[p.x,p.y])}]:[];
            });
          }), svgTitles:document.querySelectorAll('svg title').length})''')
        headings = page.locator('h2').all()
        for i,h in enumerate(headings):
            box=h.bounding_box()
            if not box: continue
            nextbox=headings[i+1].bounding_box() if i+1<len(headings) else None
            height=min(1500,(nextbox['y'] if nextbox else page.locator('main').bounding_box()['height'])-box['y'])
            if height>0:
                page.screenshot(path=str(out/f'{width}-section-{i}.png'),full_page=True,clip={'x':0,'y':box['y'],'width':width,'height':height})
        print(width,report[width],flush=True)
    browser.close()
(out/'results.json').write_text(json.dumps(report,indent=2))
