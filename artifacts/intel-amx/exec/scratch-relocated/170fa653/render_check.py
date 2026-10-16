import asyncio, os, sys
from playwright.async_api import async_playwright
SRC='/home/jhan/workspace/intel-AMX/CI-test/status/CI-AMX-regression-20261009.html'
body=open(SRC).read()
wrapped='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body style="margin:0">'+body+'</body></html>'
tmp=os.path.join(os.path.dirname(os.path.abspath(__file__)),'wrapped.html'); open(tmp,'w').write(wrapped)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for w in (400, 800, 1200):
            pg=await b.new_page(viewport={'width':w,'height':900})
            errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
            await pg.goto('file://'+tmp); await pg.wait_for_timeout(300)
            sw=await pg.evaluate('document.documentElement.scrollWidth'); sh=await pg.evaluate('document.documentElement.scrollHeight')
            print(f'width {w}: scrollWidth {sw} (overflow {"YES" if sw>w else "no"}), height {sh}, errors {errs}')
            if w==800:
                figs=await pg.query_selector_all('figure')
                for i,f in enumerate(figs,1):
                    await f.screenshot(path=f'shots/fig{i}-800.png')
                await pg.screenshot(path='shots/top-800.png', clip={'x':0,'y':0,'width':800,'height':900})
            if w==400:
                figs=await pg.query_selector_all('figure')
                await figs[2].screenshot(path='shots/fig3-400.png')
                await pg.screenshot(path='shots/top-400.png', clip={'x':0,'y':0,'width':400,'height':900})
            await pg.close()
        await b.close()
asyncio.run(main())
