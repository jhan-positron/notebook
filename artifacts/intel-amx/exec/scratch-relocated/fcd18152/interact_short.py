from playwright.sync_api import sync_playwright
src='/home/jhan/workspace/random/from-claude/TRON-concepts-claude-short.html'
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1200,'height':900})
    pg.on('pageerror',lambda e: errs.append('pageerror: '+str(e)))
    pg.on('console',lambda m: errs.append('console.'+m.type+': '+m.text) if m.type in ('error','warning') else None)
    pg.goto('file://'+src); pg.wait_for_timeout(500)
    def click(sel, n=1, wait=40):
        for _ in range(n): pg.click(sel); pg.wait_for_timeout(wait)
    click('#fig-tree button[data-view=tree]'); click('#fig-tree button[data-view=lanes]')
    click('#fig-trav [data-act=reset]'); click('#fig-trav [data-act=step]', 18, 15); assert pg.is_disabled('#fig-trav [data-act=step]')
    chips=pg.query_selector_all('#own-chips .tchip'); chips[0].click(); chips[3].click(); assert 'Lowest common owner' in pg.inner_text('#own-readout'); pg.click('#own-chips button:not(.tchip)')
    for st in range(5): click(f'#fig-page button[data-st="{st}"]')
    click('#fig-mask [data-act=build]'); click('#fig-mask [data-act=step]', 7, 15); assert pg.is_disabled('#fig-mask [data-act=step]'); click('#fig-mask [data-act=reset]')
    pg.query_selector_all('#svg-mask rect[role=button]')[30].click(); assert 'find_range' in pg.inner_text('#mask-status')
    click('#fig-mb [data-act=reset]'); click('#fig-mb [data-act=step]', 3, 20)
    for v in ['llama','ingest','mock']: pg.select_option('#fig-mb [data-act=consts]', v); pg.wait_for_timeout(30)
    w='#fig-walk1'; click(f'{w} [data-act=reset]'); click(f'{w} [data-act=step]', 30, 8); pg.select_option(f'{w} [data-act=mb]','1'); pg.select_option(f'{w} [data-act=q]','5'); pg.select_option(f'{w} [data-act=layer]','0'); click(f'{w} [data-act=play]'); pg.wait_for_timeout(400); click(f'{w} [data-act=reset]')
    for v in ['1','14','6']: pg.evaluate("(v)=>{const s=document.querySelector('#fig-strips1 [data-act=w]'); s.value=v; s.dispatchEvent(new Event('input'));}", v)
    click('#fig-strips1 [data-act=inf]'); click('#fig-strips1 [data-act=reset6]'); pg.check('#fig-strips1 [data-act=mbdrop]')
    for v in ['0','8','17']: pg.evaluate("(v)=>{const s=document.querySelector('#fig-lanes [data-act=scrub]'); s.value=v; s.dispatchEvent(new Event('input'));}", v)
    click('#fig-lanes [data-act=play]'); pg.wait_for_timeout(300); click('#fig-lanes [data-act=next]')
    pg.query_selector_all('#matrix .cellm a')[1].click(); pg.wait_for_timeout(80); assert 'Lowest common owner' in pg.inner_text('#own-readout')
    print('matrix cards:', len(pg.query_selector_all('#matrix .cellm:not(.blank)')), '| glossary rows:', pg.evaluate("document.querySelectorAll('#s12 ~ .tablewrap tbody tr').length"), '| dumb table rows:', pg.evaluate("document.querySelectorAll('#dumb-table tbody tr').length"), '| mask table rows:', pg.evaluate("document.querySelectorAll('#mask-table tbody tr').length"))
    pg.query_selector('table.concepts').screenshot(path='short-table.png')
    b.close()
print('errors:', errs if errs else 'none'); print('SHORT INTERACTION OK')
