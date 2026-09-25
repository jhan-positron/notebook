import json
from pathlib import Path
from playwright.sync_api import sync_playwright
artifact=Path('/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/shared-save-explained-codex.html')
report={'checks':[], 'viewports':[], 'console_errors':[]}
def check(name,condition,detail=None):
    report['checks'].append({'name':name,'pass':bool(condition),'detail':detail})
def set_time(page,t):
    page.locator('#time').fill(str(t)); page.locator('#time').dispatch_event('input')
def snapshot(page):
    return page.evaluate("""() => ({time:document.querySelector('#time').value,opened:document.querySelector('#opened').textContent,next:document.querySelector('#next-unit').textContent,finished:document.querySelector('#finished').textContent,latch:document.querySelector('#latch').textContent,state:document.querySelector('#state').textContent,stored:document.querySelectorAll('.unit.done').length,storing:document.querySelectorAll('.unit.busy').length})""")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],timeout=15000)
    for width in (1440,390,320):
        page=browser.new_page(viewport={'width':width,'height':1000},device_scale_factor=1)
        page.on('pageerror', lambda e: report['console_errors'].append(str(e)))
        page.on('console',lambda msg: report['console_errors'].append(msg.text) if msg.type=='error' else None)
        page.goto(artifact.as_uri(),wait_until='load')
        page.add_style_tag(content='html {scroll-behavior:auto!important}')
        dims=page.evaluate("""() => ({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth,bg:getComputedStyle(document.body).backgroundColor,overflows:[...document.querySelectorAll('main,section,.card,.grid2')].filter(e=>{let r=e.getBoundingClientRect();return r.right>innerWidth+1||r.left < -1}).map(e=>({tag:e.tagName,id:e.id,class:e.className,left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})),internalScroll:[...document.querySelectorAll('.scroll,.tablewrap')].filter(e=>e.scrollWidth>e.clientWidth).length})""")
        report['viewports'].append(dims)
        check(f'{width}px no page overflow',dims['document']==width,dims)
        page.screenshot(path=f'/tmp/shared-save-{width}-full.png',full_page=True)
        page.locator('#animation').screenshot(path=f'/tmp/shared-save-{width}-animation.png')
        if width==1440:
            check('initial controls',page.locator('#clock').inner_text()=='0.0 µs' and page.locator('#play').inner_text()=='Play')
            page.locator('#next').click();check('Next event goes to 2 µs',snapshot(page)['time']=='2',snapshot(page))
            page.locator('#restart').click();check('Restart resets',snapshot(page)['time']=='0')
            page.locator('#play').click();page.wait_for_timeout(350)
            check('Play advances',float(snapshot(page)['time'])>0 and page.locator('#play').inner_text()=='Pause',snapshot(page))
            page.locator('#play').click();frozen=float(snapshot(page)['time']);page.wait_for_timeout(200)
            check('Pause freezes',float(snapshot(page)['time'])==frozen and page.locator('#play').inner_text()=='Play')
            set_time(page,14);s=snapshot(page);check('Normal at14: 8 claims with stores outstanding',s['next']=='8' and s['stored']<8,s)
            page.locator('#animation').screenshot(path='/tmp/shared-save-normal-t14.png')
            set_time(page,16);s=snapshot(page);check('Normal at16: main joins',s['state'].startswith('Main has no more units.'),s)
            set_time(page,23);s=snapshot(page);check('Normal at23: K latch1',s['latch']=='1' and s['stored']==8 and s['finished']=='3 / 3',s)
            set_time(page,27);s=snapshot(page);check('Normal at27: latch0',s['latch']=='0',s)
            page.locator('#u-7').click();check('Unit selection',page.locator('#u-7').get_attribute('aria-pressed')=='true' and page.locator('#unit-detail').inner_text().startswith('U7:'))
            set_time(page,73);check('Next disabled at end',page.locator('#next').is_disabled())
            page.locator('#scenario').select_option('late');check('Scenario reset',snapshot(page)['time']=='0')
            set_time(page,24);s=snapshot(page);check('Late at24: 8 stores and only 2 helpers done',s['stored']==8 and s['finished']=='2 / 3' and s['latch']=='2',s)
            page.locator('#animation').screenshot(path='/tmp/shared-save-late-t24.png')
            set_time(page,40);s=snapshot(page);check('Late at40: helpers3',s['finished']=='3 / 3' and 'join is complete' in s['state'],s)
            set_time(page,42);s=snapshot(page);check('Late at42: K done',s['latch']=='1',s)
            page.locator('#pair').fill('63');page.locator('#pair').dispatch_event('input')
            check('Pair63 dimensions and values',page.locator('#pair-label').inner_text()=='63: dimensions 126 and 127' and page.locator('.pair').last.inner_text()=='token 15\n141, 142')
            counts=[]
            for i,b in enumerate(page.locator('#partition-tabs button').all()):
                b.click();counts.append(page.locator('#mask .on').count())
                check(f'Partition{i} selected',b.get_attribute('aria-pressed')=='true')
            check('Partition masks',counts==[8,0,8,6,1],counts)
            page.locator('#measurements').screenshot(path='/tmp/shared-save-measurements.png')
            page.locator('#data').screenshot(path='/tmp/shared-save-data.png')
            duplicates=page.evaluate("""() => {const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.filter((x,i)=>ids.indexOf(x)!==i)}""")
            check('Unique IDs',not duplicates,duplicates)
            missing=page.evaluate("""() => [...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.querySelector(a.getAttribute('href'))).map(a=>a.getAttribute('href'))""")
            check('Internal links resolve',not missing,missing)
            # SVG labels must stay inside their diagram's view box.
            bounds=page.evaluate("""() => [...document.querySelectorAll('svg')].flatMap(svg=>[...svg.querySelectorAll('text')].map(t=>{let r=t.getBBox(),v=svg.viewBox.baseVal;return {svg:svg.id,text:t.textContent,x:r.x,y:r.y,width:r.width,height:r.height,out:r.x < -1||r.y < -1||r.x+r.width > v.width+1||r.y+r.height > v.height+1}}).filter(x=>x.out))""")
            check('SVG text inside viewboxes',not bounds,bounds)
        else:
            page.locator('#scenario').select_option('late');set_time(page,24)
            page.locator('#animation').screenshot(path=f'/tmp/shared-save-{width}-late.png')
            page.locator('#pair').fill('63');page.locator('#pair').dispatch_event('input')
            page.locator('#partition-tabs button').last.click()
            page.locator('#data').screenshot(path=f'/tmp/shared-save-{width}-data.png')
            page.locator('#measurements').screenshot(path=f'/tmp/shared-save-{width}-measurements.png')
        page.close()
    browser.close()
check('No browser console errors',not report['console_errors'],report['console_errors'])
Path('/tmp/shared-save-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
