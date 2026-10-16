import sys, json, re, hashlib, faulthandler
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
sys.path.insert(0,'/tmp')
from build_pr4424_diagrams import OUT, PROMPT, HEAD, BASE, source, FILES
faulthandler.dump_traceback_later(30,repeat=True)

report={'scope':'Artifact validation only; no C++ execution','static':[],'browser':[],'failures':[]}
def check(ok,description):
 if not ok:report['failures'].append(description)

for path in sorted(OUT.glob('*.html')):
 print('STATIC',path.name,flush=True)
 soup=BeautifulSoup(path.read_text(),'html.parser')
 check(soup.select_one('.literal-prompt').get_text()==PROMPT,path.name+': literal prompt differs')
 ids=[e['id'] for e in soup.select('[id]')]
 check(len(ids)==len(set(ids)),path.name+': duplicate ids')
 links=soup.select('a[href]')
 for a in links:
  href=a['href']
  if href.startswith('#'):check(href[1:] in ids,path.name+': missing anchor '+href)
  elif not href.startswith('https://'):check((OUT/href.split('#')[0]).exists(),path.name+': missing local link '+href)
 for section in soup.select('.change'):
  check(bool(section.select('.diagram')),path.name+': unit without diagram '+section['id'])
 for node in soup.select('.node'):
  check(bool(node.select_one('.node-description').get_text(strip=True)),path.name+': missing node description')
  check(bool(node.select_one('.source-link')),path.name+': missing node citation')
  file,line=node['data-source'].rsplit(':',1)
  check(0<int(line)<=len(source(file)),path.name+': invalid source line '+node['data-source'])
 for card in soup.select('.source-card'):
  href=card.select_one('.source-link')['href']
  match=re.search(r'/blob/([0-9a-f]+)/(.+)#L(\d+)(?:-L(\d+))?$',href)
  revision,file,start,end=match.groups();start=int(start);end=int(end or start)
  shown=[line.get_text() for line in card.select('.line-text')]
  check(shown==source(file,revision)[start-1:end],path.name+': source excerpt differs '+href)
 report['static'].append({'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'units':len(soup.select('.change')),'diagrams':len(soup.select('.diagram')),'cited_nodes':len(soup.select('.node'))})

with sync_playwright() as p:
 print('LAUNCH',flush=True)
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'],timeout=20000)
 report['browser_version']=browser.version
 for path in sorted(OUT.glob('*.html')):
  for width in (1600,1280,390,320):
   print('BROWSER',path.name,width,flush=True)
   page=browser.new_page(viewport={'width':width,'height':1000},color_scheme='dark')
   errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('https://**/*',lambda route:route.abort())
   page.route('http://**/*',lambda route:route.abort())
   page.goto(path.as_uri(),wait_until='load')
   metrics=page.evaluate('''()=>({
    width:innerWidth,documentWidth:document.documentElement.scrollWidth,
    colorScheme:getComputedStyle(document.documentElement).colorScheme,
    background:getComputedStyle(document.body).backgroundColor,
    clipped:[...document.querySelectorAll('.node-name,.node-description,.edge-label,h1,h2,h3,p,li')].filter(e=>e.clientWidth>0&&e.scrollWidth>e.clientWidth+2&&getComputedStyle(e).overflowX==='visible').map(e=>({class:e.className,text:e.innerText.slice(0,60),width:e.clientWidth,scroll:e.scrollWidth})),
    columns:document.querySelector('.change-grid')?getComputedStyle(document.querySelector('.change-grid')).gridTemplateColumns:null
   })''')
   check(metrics['documentWidth']<=width+1,f'{path.name}: page overflow at {width}: {metrics}')
   check(metrics['colorScheme']=='light',f'{path.name}: theme not light at {width}')
   check(not errors,f'{path.name}: JS errors {errors}')
   check(not metrics['clipped'],f'{path.name}: clipped text at {width}: {metrics["clipped"]}')
   report['browser'].append({'file':path.name,'width':width,**metrics,'errors':errors})
   if path.name=='diagramming-code-changes.html':
    page.locator('#token').fill('63');page.locator('#dim').fill('127')
    check('8191 bf16 elements = 16382 bytes' in page.locator('#index-result').inner_text(),'index explorer last element failed')
    page.locator('#token').fill('17');page.locator('#dim').fill('35')
    check('2595 bf16 elements = 5190 bytes' in page.locator('#index-result').inner_text(),'index explorer sample failed')
    if width in (1600,390):
     page.locator('#layout-explorer').screenshot(path=f'/tmp/pr4424-overview-layout-{width}.png')
   else:
    button=page.locator('[data-wrap]');button.click()
    check(button.get_attribute('aria-pressed')=='false','wrap toggle failed')
    check(page.locator('.source-code.wrap').count()==0,'code unwrapping failed')
    button.click()
    if width in (1600,390):
     page.locator('.change').nth(3).screenshot(path=f'/tmp/pr4424-{path.stem}-{width}.png')
   if width==1600:
    page.locator('#base-models').screenshot(path=f'/tmp/pr4424-{path.stem}-base.png')
   page.close()
 browser.close()

target=OUT/'diagramming-code-changes-validation.json'
existing=json.loads(target.read_text());existing['artifact_validation']=report
target.write_text(json.dumps(existing,indent=2)+'\n')
print(json.dumps(report,indent=2))
if report['failures']:sys.exit(1)
