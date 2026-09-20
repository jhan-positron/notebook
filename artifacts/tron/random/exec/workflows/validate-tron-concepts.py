import json
from pathlib import Path
from playwright.sync_api import sync_playwright

artifact=Path('/home/jhan/workspace/random/TRON-concepts-codex.html')
results=[]

def record(name,fn):
    fn()
    results.append(name)
    print('PASS:',name,flush=True)

def require(condition,detail):
    assert condition,detail

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],timeout=15000)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(artifact.as_uri(),timeout=15000)
    def default_case():
        require(page.locator('.chosen td.allowed').count()==6,'Query 11 must see exactly six keys')
        require(page.locator('.in-union').count()==9,'Four queries must need nine distinct keys')
        require(page.locator('.union-page').count()==3,'The group must span three 4-token pages')
        require(page.locator('.query-page').count()==2,'Query 11 must span two 4-token pages')
        require(page.locator('td.allowed').count()==24,'Four queries each see six keys')
    record('Default example: individual visibility differs from group union',default_case)
    def earlier_query():
        page.get_by_role('button',name='Select query at position 8',exact=True).click()
        require(page.locator('.chosen td.allowed').count()==6,'Query 8 window has six keys')
        require(page.locator('.query-page').count()==3,'Query 8 needs the earlier boundary page')
        require('positions 3–8' in page.locator('#live-summary').inner_text(),'Wrong early range')
    record('Earlier query retains its own mask and boundary page',earlier_query)
    def storage_independence():
        page.locator('#reset').click()
        before=page.locator('#matrix').inner_text()
        page.locator('#page-size').select_option('8')
        require(page.locator('#matrix').inner_text()==before,'Changing storage must not alter attention visibility')
        require(page.locator('.union-page').count()==2,'Larger pages group the same keys into two pages')
        require(page.locator('.slot.visible').count()==6,'Same six visible entries')
    record('Page size changes storage grouping without changing the mask',storage_independence)
    def full_causal():
        page.locator('#window').select_option('0')
        require(page.locator('.chosen td.allowed').count()==12,'Query 11 full causal range is 0–11')
        require(page.locator('.in-union').count()==12,'Full causal union is 0–11')
        page.get_by_role('button',name='Select query at position 8',exact=True).click()
        require(page.locator('.chosen td.allowed').count()==9,'Earlier query must still exclude future positions')
    record('Full causal visibility includes history and preserves causality',full_causal)
    def beginning():
        page.locator('#reset').click()
        page.locator('#end').fill('3')
        require(page.locator('td.allowed').count()==10,'At sequence start, four causal rows have 1+2+3+4 keys')
        require(page.locator('.in-union').count()==4,'Union at start is positions 0–3')
    record('Sequence start clips the window at position zero',beginning)
    def no_repeated_jobs():
        page.locator('#end').fill('18')
        require(page.locator('#next').is_disabled(),'Incomplete next group must not repeat token jobs')
        page.locator('#reset').click()
        page.locator('#next').click()
        require('positions 12–15' in page.locator('#live-summary').inner_text(),'Next group must follow current jobs')
        page.locator('#next').click()
        require('positions 16–19' in page.locator('#live-summary').inner_text(),'Final complete group must be positions 16–19')
        require(page.locator('#next').is_disabled(),'Must stop at final complete group')
    record('Advancing groups never repeats jobs at the final boundary',no_repeated_jobs)
    def animations():
        page.clock.install()
        page.locator('#reset').click()
        page.locator('#size').select_option('1')
        page.locator('#play').click()
        page.clock.fast_forward(1700)
        require('position 12' in page.locator('#live-summary').inner_text(),'Decode animation must advance one token')
        page.locator('#play').click()
        frozen=page.locator('#live-summary').inner_text()
        page.clock.fast_forward(4000)
        require(page.locator('#live-summary').inner_text()==frozen,'Paused animation must stay paused')
        page.locator('#phase-play').click()
        for _ in range(5):page.clock.fast_forward(2400)
        require(page.locator('#phase-count').inner_text()=='Step 6 of 6','Execution sequence must reach its final step')
        require(page.locator('#phase-play').get_attribute('aria-pressed')=='false','Execution animation must stop')
        page.locator('#phase-reset').click()
        page.locator('#phase-next').click()
        require(page.locator('#phase-count').inner_text()=='Step 2 of 6','Manual sequence control must work')
    record('Play, pause, stop, and manual step controls work',animations)
    def presets():
        page.locator('[data-preset="page"]').click()
        require(page.locator('#page-size').input_value()=='8','Page preset')
        page.locator('[data-preset="decode"]').click()
        require(page.locator('#size').input_value()=='1','Decode preset')
        page.locator('[data-preset="union"]').click()
        default_case()
    record('Guided experiments restore their intended state',presets)
    def document_integrity():
        require(page.locator('#original-prompt').text_content()==Path('/home/jhan/workspace/random/input-2-ai/internalize-concepts.md').read_text(),'Prompt content must be preserved exactly')
        broken=page.evaluate('''() => [...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(a.getAttribute('href').slice(1))).map(a=>a.getAttribute('href'))''')
        require(not broken,broken)
        require('will be pinned' not in page.locator('body').inner_text(),'No unfinished source notes')
        require(not page.locator('script[src],link[rel="stylesheet"]').count(),'Artifact must be self-contained')
    record('Prompt is exact, source anchors resolve, and artifact is self-contained',document_integrity)
    page.clock.resume()
    page.locator('#reset').click()
    page.locator('#phase-reset').click()
    for width in (1440,768,390,320):
        page.set_viewport_size({'width':width,'height':1000})
        page.emulate_media(color_scheme='dark',reduced_motion='reduce')
        for expanded in (False,True):
            page.locator('details').evaluate_all('(els,v)=>els.forEach(el=>el.open=v)',expanded)
            record(f'Light layout without page overflow at {width}px, details={expanded}',lambda:require(page.evaluate("document.documentElement.scrollWidth<=innerWidth && getComputedStyle(document.body).backgroundColor==='rgb(246, 247, 249)'"),'Overflow or incorrect theme'))
        page.locator('details').evaluate_all('(els)=>els.forEach(el=>el.open=false)')
        if width in (1440,390):
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path=f'/tmp/tron-concepts-{width}.png',full_page=True)
            page.locator('#lab').screenshot(path=f'/tmp/tron-concepts-lab-{width}.png',style='.nav{visibility:hidden}')
    record('No JavaScript runtime errors',lambda:require(not errors,errors))
    browser.close()
Path('/tmp/tron-concepts-validation.json').write_text(json.dumps({'passed':len(results),'checks':results,'page_errors':errors},indent=2))
print(json.dumps({'passed':len(results),'page_errors':errors}),flush=True)
