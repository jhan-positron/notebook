from pathlib import Path
import json
from playwright.sync_api import sync_playwright

root=Path('/home/jhan/workspace/intel-AMX/VNNIed-K-in-place')
url=(root/'status/block-store-explained-codex.html').as_uri()
chrome='/tmp/amx-browsers/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=chrome,headless=True,args=['--no-sandbox'],timeout=15000)
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    errors=[]
    requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    page.goto(url)
    assert not errors,errors
    assert page.locator('#loads').inner_text()=='0 / 64'
    page.screenshot(path='/tmp/block-store-desktop.png',full_page=True)
    page.select_option('#jump','1')
    assert '5204 B' in page.locator('#address-calculation').inner_text()
    page.click('#next')
    page.click('#next')
    page.locator('#animation').screenshot(path='/tmp/block-store-animation.png')
    for preset,n in [('full',16),('edge',6),('sparse',4),('single',1)]:
        page.select_option('#preset',preset)
        maximum=4 if n==1 else 72
        for event in range(maximum+1):
            page.locator('#event').evaluate('(el,v)=>{el.value=v;el.dispatchEvent(new Event("input",{bubbles:true}));}',event)
            assert page.locator('#event-label').inner_text()==f'{event} / {maximum}'
            if event:
                s=(event-1) if n==1 else (event-1)//18
                phase=3 if n==1 else (event-1)%18+1
                stored=16 if n==1 else max(0,phase-2)
                written=page.locator('.pair.written').count()
                assert written==(n if 1<stored else 0),(preset,event,written)
            assert not errors,errors
        assert page.locator('#payload').inner_text()==f'{n*256} / {n*256} B'
        assert page.locator('#loads').inner_text()==f'{n*4} / {n*4}'
        assert page.locator('.pair.untouched').count()==16-n
        if n==1:
            page.locator('#animation').screenshot(path='/tmp/block-store-single.png')
        page.click('#restart')
        assert page.locator('#payload').inner_text()==f'0 / {n*256} B'
    cells=json.loads((root/'exec/block-store-animation/token21.json').read_text())
    for cell in cells:
        actual=page.evaluate('(dim)=>byteOffset(21,dim)',cell['d'])
        assert actual==cell['byte']
    stores=json.loads((root/'exec/block-store-animation/block.json').read_text())['stores']
    for store in stores:
        actual=page.evaluate('([s,dp])=>byteOffset(16,32*s+2*dp)',[store['s'],store['dp']])
        assert actual==store['byte']
    indices=page.evaluate('Array.from({length:8192},(_,i)=>byteOffset(Math.floor(i/128),i%128))')
    assert sorted(indices)==list(range(0,16384,2))
    page.select_option('#preset','single')
    page.select_option('#speed','12')
    page.click('#play')
    page.wait_for_function('document.getElementById("play").textContent==="Play"')
    assert page.locator('#event-label').inner_text()=='4 / 4'
    page.select_option('#preset','full')
    page.select_option('#block','3')
    page.select_option('#jump','3')
    page.select_option('#token-lane','15')
    page.locator('#pair').fill('15')
    assert '16380 B' in page.locator('#address-calculation').inner_text()
    page.select_option('#block','1')
    page.select_option('#token-lane','5')
    page.locator('#pair').fill('1')
    page.click('#restart')
    sizes=[]
    for width in [1440,768,390,320]:
        page.set_viewport_size({'width':width,'height':900})
        dims=page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
        assert dims['width']==dims['scroll'],dims
        sizes.append(dims)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path='/tmp/block-store-mobile.png',full_page=True)
    page.locator('#event').focus()
    page.keyboard.press('ArrowRight')
    assert page.locator('#event-label').inner_text()=='1 / 72'
    assert len(requests)==1,requests
    static=browser.new_page(java_script_enabled=False)
    static.goto(url)
    assert static.locator('#measurements svg').count()==1
    assert static.locator('noscript').is_visible()
    assert not errors,errors
    print(json.dumps({'status':'passed','javascript_errors':errors,'viewports':sizes,'address_checks':128+64,'unique_plane_elements':8192,'playback_states_checked':73*3+5,'network_subresources':len(requests)-1}))
    browser.close()
