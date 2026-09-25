from playwright.sync_api import sync_playwright
src='/home/jhan/workspace/random/from-claude/TRON-concepts-claude-short.html'
with sync_playwright() as p:
    b=p.chromium.launch()
    for width in (360,420,1200):
        pg=b.new_page(viewport={'width':width,'height':900}); errs=[]
        pg.on('pageerror',lambda e: errs.append(str(e))); pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
        pg.goto('file://'+src); pg.wait_for_timeout(800)
        sw=pg.evaluate('document.documentElement.scrollWidth'); banner=pg.evaluate("getComputedStyle(document.getElementById('assertBanner')).display")
        print(f'width {width}: scrollWidth {sw} {"OK" if sw<=width else "OVERFLOW"}; banner {banner}; errors {errs}')
        if width==1200:
            n=pg.evaluate("document.querySelectorAll('.fig').length"); print('figures:', n)
            for sel in ['#svg-tree','#svg-trav','#own-tree','#svg-page','#svg-mask','#mask-table table','#mb-stage','#svg-mbpages','#svg-pipe','#fig-walk1 svg','#fig-strips1 svg','#fig-dumb svg','#dumb-table table','#fig-lanes svg','#matrix .cellm:not(.blank)']:
                print('  ', sel, pg.evaluate("(s)=>{const e=document.querySelector(s); return e? (e.children.length||e.childNodes.length) : 'MISSING'}", sel))
        pg.close()
    b.close()
