from pathlib import Path
from html import escape
import json, re, subprocess, collections

ROOT = Path('/home/jhan/workspace/intel-AMX/PR3879/new-PRs/merge-4737-2-4424')
REPO = ROOT / 'tron'
OUT = ROOT / 'from-codex'
HEAD = '9d5c7a389b23078398028bce0d1fe1a6c5c64e31'
BASE = 'be0d5565b355a90b6018529d3310565c3f5909cb'
PROMPT = '''Do the below at from-codex/ folder.

generate diagramming-code-changes.html:
- at the top, include this prompt literally
- have Table of Content at top
- use diagrams to explain code changes of PR4424
- each code change has at least 1 diagrams
- definition of "1 code change": a logical unit of code change. E.g.:
--- 5 lines of code update one data model which is used by other code, these 5 lines are 1 unit and there should be a diagram illustrating the change
--- 10 lines of code checks one data model based on another model
- trivial code changes do not need diagrams, but need to be listed
- code comments which explain the code need to keep with code
- code change and its corresponding diagram are best side to side
- use consistent font/color schemes for same concepts or data models across whole file
- at start, use some base diagrams to illustrate overall data models, function models, sequencing models, interaction models, etc.
--- individual diagrams beside code changes, if use base diagrams as context, or better yet, update base diagrams, would be great.
- no invented shorthand; take names from the code, and cite the comment or line that defines each box.
- Every function cell carries a one-line description of what the function does
- Label every arrow between data-model boxes with how many: for example, one page has n_slots entries, one entry covers n_kv_heads kv_blocks
- target files: pick the most important 3 files from the PR, each file has its own diagramming-code-changes.html, e.g. diagramming-code-changes-<file1>.html'''

FILES = {
 'tensor': ('h/tron/tensor/k_vnni.hpp','diagramming-code-changes-k_vnni.hpp.html'),
 'cache': ('h/tron/models/kv_cache.hpp','diagramming-code-changes-kv_cache.hpp.html'),
 'model': ('h/tron/models/model.hpp','diagramming-code-changes-model.hpp.html'),
}
def git(*args):
 return subprocess.check_output(['git', '-C', str(REPO), *args], text=True)

source_cache = {}
def source(file, revision=HEAD):
 key = (revision,file)
 if key not in source_cache:
  try: source_cache[key] = git('show', f'{revision}:{file}').splitlines()
  except subprocess.CalledProcessError: source_cache[key] = []
 return source_cache[key]

def cite(file, start, end=None, revision=HEAD, label=None):
 end = end or start
 path = f'https://github.com/positron-ai/tron/blob/{revision}/{file}#L{start}'
 if end != start: path += f'-L{end}'
 text = label or f'{file}:{start}' + (f'–{end}' if end != start else '')
 return f'<a class="source-link" href="{escape(path)}" target="_blank" rel="noopener">{escape(text)}</a>'

def prose(s):
 return re.sub(r'`([^`]+)`', lambda m:'<code>'+m.group(1)+'</code>', escape(s))
def bullets(items):
 return '<ul>' + ''.join('<li>'+prose(x)+'</li>' for x in items) + '</ul>'

CSS = '''
:root{color-scheme:light;--ink:#172638;--muted:#536176;--line:#d5dce6;--blue:#1465aa;--blue-bg:#eaf3fc;--amber:#8b5600;--amber-bg:#fff3d9;--purple:#7040a3;--purple-bg:#f4edfc;--teal:#086e60;--teal-bg:#e7f6f1;--neutral:#536176;--neutral-bg:#f0f3f7}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}body{margin:0;background:#f7f8fb;color:var(--ink);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:#145da0;text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:#06325b}main{max-width:1800px;margin:auto;padding:28px clamp(16px,3vw,52px) 90px}h1{font-size:clamp(28px,3.6vw,48px);line-height:1.13;letter-spacing:-.035em;margin:16px 0}h2{font-size:27px;line-height:1.25;margin:0 0 18px;letter-spacing:-.02em}h3{font-size:20px;line-height:1.35;margin:0 0 10px}p{margin:10px 0}p,li,dd,figcaption{overflow-wrap:anywhere}code,pre,.mono{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace}code{font-size:.9em;overflow-wrap:anywhere}p code,li code,td code{background:#edf1f6;border-radius:3px;padding:1px 4px}ul{padding-left:22px;margin:10px 0}li{margin:6px 0}section{scroll-margin-top:75px}.prompt-box{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:24px}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:12px;font-weight:750;color:var(--muted)}.literal-prompt{margin:10px 0 0;font-size:12px;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere;color:#35465d}.toc{background:#eef3f9;border:1px solid #d7e1ec;border-radius:12px;padding:24px;margin:24px 0}.toc h2{font-size:21px}.toc ul{columns:3;column-gap:34px;margin:0;padding-left:20px}.toc li{font-size:14px;break-inside:avoid;margin:6px 0}.nav-strip{position:sticky;top:0;z-index:20;background:#ffffffed;backdrop-filter:blur(8px);border-block:1px solid var(--line);display:flex;gap:20px;flex-wrap:wrap;padding:11px 24px;font-size:13px}.nav-strip a{text-decoration:none;font-weight:650}.hero{padding:12px 0 28px;max-width:1200px}.short-version{font-size:20px;line-height:1.55;max-width:1050px}.scope-note{border-left:4px solid #687993;padding:10px 16px;background:#edf1f7;font-size:14px}.revision{font-size:13px;color:var(--muted);overflow-wrap:anywhere}.legend{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}.legend span{padding:7px 13px;border-radius:6px;border:1px solid var(--line);font-size:13px;font-weight:600}.k{--concept:var(--blue);--fill:var(--blue-bg)}.cache{--concept:var(--amber);--fill:var(--amber-bg)}.work{--concept:var(--purple);--fill:var(--purple-bg)}.function{--concept:var(--teal);--fill:var(--teal-bg)}.value{--concept:var(--neutral);--fill:var(--neutral-bg)}.legend span,.node{background:var(--fill);border-color:var(--concept);color:var(--ink)}.section{margin:38px 0 48px}.base-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.diagram{margin:0;background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px;min-width:0}.diagram h4{margin:0 0 18px;font-size:16px}.diagram-flow{margin:18px 0}.diagram-flow.pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(80px,.64fr) minmax(0,1fr);align-items:center;gap:8px}.diagram-flow.long{display:flex;flex-direction:column;align-items:center;gap:7px}.diagram-flow.long .node{width:100%;max-width:410px}.node{border:1px solid var(--concept);border-top:4px solid var(--concept);border-radius:7px;padding:12px;min-width:0}.node-name{font-size:13px;font-weight:750;line-height:1.4;overflow-wrap:anywhere;display:block}.node-description{font-size:12px;line-height:1.45;margin:7px 0;color:#33475d}.node .source-link{font-size:10px;line-height:1.4;display:block;overflow-wrap:anywhere}.node-kind{font:10px system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:var(--concept);margin-bottom:5px}.connector{text-align:center;color:#44556b;min-width:0;padding:5px 0}.edge-label{font-size:11px;line-height:1.4;overflow-wrap:anywhere;display:block}.arrow{height:2px;background:#6d7f94;position:relative;display:block;margin:10px 5px}.arrow:after{content:"";position:absolute;right:-1px;top:-4px;border-left:8px solid #6d7f94;border-top:5px solid transparent;border-bottom:5px solid transparent}.long .connector{display:flex;align-items:center;gap:14px;min-height:55px;width:90%;max-width:360px;justify-content:center}.long .edge-label{max-width:290px;text-align:left}.long .arrow{width:2px;height:40px;flex:0 0 2px}.long .arrow:after{top:auto;bottom:-1px;left:-4px;border-top:8px solid #6d7f94;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:0}figcaption{color:var(--muted);font-size:13px;margin-top:15px;padding-top:12px;border-top:1px solid #e1e6ee}.change{background:#fff;border:1px solid var(--line);border-radius:14px;margin:28px 0;overflow:hidden}.change-heading{padding:22px 25px;background:#f1f5fa;border-bottom:1px solid var(--line)}.change-heading h2{font-size:24px;margin:0}.unit-num{font-size:12px;letter-spacing:.12em;text-transform:uppercase;display:block;color:var(--muted);margin-bottom:7px}.change-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px;padding:24px;align-items:start}.code-side,.explain-side{min-width:0}.explain-side>.diagram{margin:18px 0}.explain-side ul{font-size:15px;margin-top:0}.source-card{border:1px solid #d9e0e9;border-radius:8px;overflow:hidden;margin:0 0 17px;background:#fafbfd}.source-title{background:#eaf0f6;padding:10px 12px;font-size:12px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.source-title strong{color:#213b57}.source-code{font-size:12px;line-height:1.6;max-height:640px;overflow:auto;margin:0;padding:8px 0;tab-size:2}.code-line{display:flex;min-height:19px;min-width:max-content;padding:0 10px 0 0}.code-line.changed{background:#e8f5ec}.code-line.removed{background:#fceceb}.line-number{display:inline-block;color:#768397;text-decoration:none;text-align:right;min-width:47px;padding-right:10px;user-select:none;flex:none}.line-text{white-space:pre}.source-code.wrap .code-line{min-width:0}.source-code.wrap .line-text{white-space:pre-wrap;overflow-wrap:anywhere;min-width:0}.comment{color:#5a687a;font-style:italic}.badge{font-size:11px;border:1px solid #a9b9cc;padding:2px 7px;border-radius:10px}.code-tools{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:12px;color:var(--muted);margin:12px 0}.button,button{appearance:none;background:#fff;border:1px solid #899cb3;border-radius:5px;font:600 12px system-ui;color:#244564;padding:7px 10px;cursor:pointer}.button:hover,button:hover{background:#eef4fa}.terms{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.term{background:#fff;padding:14px;border:1px solid var(--line);border-radius:8px;min-width:0}.term dt{font-family:ui-monospace,monospace;font-size:13px;font-weight:700;overflow-wrap:anywhere}.term dd{font-size:13px;color:var(--muted);margin:6px 0 0}.file-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.file-card{background:#fff;border:1px solid var(--line);border-top:5px solid var(--concept);border-radius:10px;padding:24px;min-width:0}.file-card h3{font-size:19px}.file-card p{font-size:14px}.table-scroll{max-width:100%;overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px;background:#fff}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #dde3eb;vertical-align:top}th{background:#eaf0f6}details{border:1px solid var(--line);border-radius:8px;background:#fff;margin:12px 0;padding:14px}summary{cursor:pointer;font-weight:650;font-size:14px}.diff-pre{font:12px/1.5 ui-monospace,monospace;overflow:auto;max-height:700px;white-space:pre;padding:10px}.diff-add{color:#14633c;background:#e9f5ed}.diff-del{color:#8c3334;background:#fff0ef}.diff-hunk{color:#464292;background:#f1edfa}.coverage-bars{margin:18px 0}.coverage-row{display:grid;grid-template-columns:155px 1fr 210px;align-items:center;gap:14px;font-size:13px;margin:12px 0}.bar{height:20px;background:#e3e8ef;border-radius:5px;overflow:hidden}.bar-fill{height:100%;background:#1465aa;width:100%}.small{font-size:13px;color:var(--muted)}.explorer{background:#fff;border:1px solid var(--line);border-radius:12px;padding:24px}.explorer-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.controls{display:flex;gap:18px;flex-wrap:wrap}.controls label{font-size:14px}.controls input{width:70px;padding:7px;border:1px solid #9aabba;border-radius:4px;color:var(--ink);background:#fff}.panel-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin:14px 0}.panel-cell{padding:12px 4px;text-align:center;background:#edf3f9;border:1px solid #ccd9e6;border-radius:5px;font:12px ui-monospace,monospace}.panel-cell.selected{background:#d6eafb;border:2px solid #1465aa;padding:11px 3px;font-weight:700}.pair-grid{display:grid;grid-template-columns:repeat(16,minmax(0,1fr));gap:2px;margin:14px 0}.pair-cell{height:29px;background:#eaf0f6;border:1px solid #c6d3e0;font:10px/27px ui-monospace,monospace;text-align:center}.pair-cell.selected{background:#1465aa;color:#fff;font-weight:700}.formula{padding:13px;border-radius:6px;background:#eef3f9;font:13px/1.7 ui-monospace,monospace;overflow-wrap:anywhere}.takeaway{font-weight:650;color:#214b6d;margin-top:14px}.footer{border-top:1px solid var(--line);padding-top:24px;color:var(--muted);font-size:13px}
@media(min-width:1450px){.node-name{font-size:14px}.node-description{font-size:13px}.edge-label{font-size:12px}}
@media(max-width:1100px){.change-grid{grid-template-columns:1fr}.base-grid{grid-template-columns:1fr}.terms{grid-template-columns:repeat(2,minmax(0,1fr))}.toc ul{columns:2}.file-cards{grid-template-columns:1fr}.source-code{max-height:520px}.explain-side>.diagram{margin:16px 0}.explorer-grid{grid-template-columns:1fr}}
@media(max-width:600px){main{padding:16px 12px 50px}.nav-strip{padding:9px 12px;gap:9px;font-size:11px}.prompt-box{padding:14px}.literal-prompt{font-size:11px}.toc{padding:17px}.toc ul{columns:1}.hero{padding-bottom:8px}.short-version{font-size:17px}.terms{grid-template-columns:1fr}.change-heading{padding:18px}.change-heading h2{font-size:21px}.change-grid{padding:14px;gap:15px}.diagram{padding:16px}.diagram-flow.pair{display:flex;flex-direction:column;gap:7px}.diagram-flow.pair .node{width:100%}.pair .connector{display:flex;align-items:center;gap:14px;min-height:55px;width:90%;justify-content:center}.pair .edge-label{max-width:230px;text-align:left}.pair .arrow{width:2px;height:40px;flex:0 0 2px}.pair .arrow:after{top:auto;bottom:-1px;left:-4px;border-top:8px solid #6d7f94;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:0}.coverage-row{grid-template-columns:1fr;gap:3px}.source-code{font-size:11px}.explorer{padding:16px}.pair-cell{font-size:8px}.panel-cell{font-size:10px}.code-tools{flex-wrap:wrap}}
@media print{.nav-strip,.code-tools{display:none}body{background:#fff}.change-grid{display:block}.source-code{max-height:none;overflow:visible}.code-line{min-width:0}.line-text{white-space:pre-wrap}.change,.diagram{break-inside:avoid}.toc{break-after:page}main{max-width:none;padding:0}.base-grid,.terms{display:block}a{color:inherit}}
'''

SCRIPT = '''
document.querySelectorAll('[data-wrap]').forEach(button=>button.addEventListener('click',()=>{const wrapping=button.getAttribute('aria-pressed')!=='true';document.querySelectorAll('.source-code').forEach(el=>el.classList.toggle('wrap',wrapping));button.setAttribute('aria-pressed',wrapping);button.textContent=wrapping?'Code wrapping: on':'Code wrapping: off'}));
function updateIndex(){const tokenEl=document.getElementById('token'),dimEl=document.getElementById('dim');if(!tokenEl)return;const token=Math.min(63,Math.max(0,Math.trunc(Number(tokenEl.value))||0)),dim=Math.min(127,Math.max(0,Math.trunc(Number(dimEl.value))||0));tokenEl.value=token;dimEl.value=dim;const s=Math.floor(dim/32),c=Math.floor(token/16),dp=Math.floor(dim%32/2),t=token%16,j=dim%2,idx=(((s*4+c)*16+dp)*16+t)*2+j;document.getElementById('index-result').textContent='index('+token+', '+dim+') = '+idx+' bf16 elements = '+(idx*2)+' bytes from the plane start';document.getElementById('coordinates').textContent='s = '+s+'; c = '+c+'; dp = '+dp+'; t = '+t+'; j = '+j;document.querySelectorAll('.panel-cell').forEach(el=>{const yes=Number(el.dataset.s)===s&&Number(el.dataset.c)===c;el.classList.toggle('selected',yes);el.setAttribute('aria-label','panel s '+el.dataset.s+' c '+el.dataset.c+(yes?', selected':''))});document.querySelectorAll('.pair-cell').forEach(el=>el.classList.toggle('selected',Number(el.dataset.t)===t));document.getElementById('pair-label').textContent='Pair row dp = '+dp+' of panel (s = '+s+', c = '+c+'): each cell contains 2 bf16 values';document.getElementById('element-note').textContent='Token '+token+' selects lane t = '+t+'. Dimension '+dim+' selects j = '+j+' within that lane.';}
document.querySelectorAll('#token,#dim').forEach(el=>el.addEventListener('input',updateIndex));updateIndex();
'''

def node(n):
 kind=n['kind']; assert kind in ('k','cache','work','function','value'),n
 assert n.get('description') and n.get('line') and n.get('file'),n
 assert n['line']<=len(source(n['file'])),n
 label={'k':'K storage or view','cache':'Cache data','work':'Worker data','function':'Function','value':'Value or condition'}[kind]
 return f'<div class="node {kind}" data-source="{escape(n["file"])}:{n["line"]}"><div class="node-kind">{label}</div><code class="node-name">{escape(n["name"])}</code><p class="node-description">{prose(n["description"])}</p>{cite(n["file"],n["line"],n.get("end_line"))}</div>'

def diagram(d):
 flows=[]
 for flow in d['flows']:
  assert len(flow['edges'])==len(flow['nodes'])-1,flow
  bits=[]
  for i,n in enumerate(flow['nodes']):
   if i:
    bits.append('<div class="connector"><span class="edge-label">'+prose(flow['edges'][i-1])+'</span><span class="arrow" aria-hidden="true"></span></div>')
   bits.append(node(n))
  flows.append('<div class="diagram-flow '+('pair' if len(flow['nodes'])==2 else 'long')+'">'+''.join(bits)+'</div>')
 return '<figure class="diagram"><h4>'+escape(d['title'])+'</h4>'+''.join(flows)+'<figcaption>'+prose(d['caption'])+'</figcaption></figure>'

def legend():
 return '<div class="legend" aria-label="Consistent diagram colors">'+''.join(f'<span class="{cl}">{name}</span>' for cl,name in [('k','K storage and views'),('cache','Cache data'),('work','Worker data'),('function','Functions'),('value','Values and conditions')])+'</div>'

def terms(items):
 return '<dl class="terms">'+''.join('<div class="term"><dt>'+escape(t['name'])+'</dt><dd>'+prose(t['meaning'])+'</dd></div>' for t in items)+'</dl>'

COMMON_TERMS=[
 {'name':'Tron','meaning':'The inference program under test.'},
 {'name':'K / Q / V','meaning':'Keys, queries and values in attention. A query scores stored keys to choose how much each value contributes.'},
 {'name':'KV page','meaning':'A 64-token cache page. Each storage slot has the key and value data for its own head geometry.'},
 {'name':'bf16 / fp32','meaning':'16-bit brain floating-point values / 32-bit floating-point values.'},
 {'name':'VNNI','meaning':'Vector Neural Network Instructions. Here the name identifies the paired layout used by the matrix and vector instructions.'},
 {'name':'AMX / AVX-512','meaning':'Intel Advanced Matrix Extensions / Advanced Vector Extensions with 512-bit vectors. These are CPU instruction sets.'},
 {'name':'FPGA / DMA','meaning':'Field-programmable gate array, the accelerator card / direct memory access, used to move staging buffers to the card.'},
 {'name':'GOF','meaning':'Group of four consecutive tokens. The gof staging code prepares their K and V data for the accelerator.'},
 {'name':'row-major','meaning':'All dimensions for one token are contiguous. A short write can keep this form inside a block of the typed K owner.'},
]

def top(title,toc,current):
 links=[('diagramming-code-changes.html','Overview')]+[(v[1],Path(v[0]).name) for v in FILES.values()]
 nav=''.join(f'<a href="{name}"'+(' aria-current="page"' if name==current else '')+'>'+label+'</a>' for name,label in links)
 return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+escape(title)+'</title><style>'+CSS+'</style></head><body><main><section class="prompt-box" id="prompt"><div class="eyebrow">Original prompt · literal text</div><pre class="literal-prompt">'+escape(PROMPT)+'</pre></section><nav class="toc" aria-label="Table of Content"><h2>Table of Content</h2><ul>'+''.join('<li><a href="#'+id+'">'+escape(label)+'</a></li>' for id,label in toc)+'</ul></nav></main><nav class="nav-strip" aria-label="Report pages">'+nav+'<a href="#prompt">Back to top</a></nav><main>'

def end():
 return '<footer class="footer">Prepared from the exact PR4424 source revisions linked above. Diagrams describe source behavior and ordering. No new build, benchmark, or runtime test was performed for this explanation.</footer></main><script>'+SCRIPT+'</script></body></html>'

def revision_note():
 return '<p class="revision">PR <a href="https://github.com/positron-ai/tron/pull/4424">#4424</a> · source checked 9 October 2026 · head <code>'+HEAD+'</code><br>Compared with merge base <code>'+BASE+'</code>. All source links are pinned to these commits.</p>'

diff_cache={}
def changed_lines(file):
 if file in diff_cache:return diff_cache[file]
 patch=git('diff','--no-ext-diff','--unified=0',BASE,HEAD,'--',file)
 added=set();removed=set();old=0;new=0
 for line in patch.splitlines():
  m=re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@',line)
  if m: old,new=map(int,m.groups())
  elif line.startswith(('+++','---')):continue
  elif line.startswith('+'):added.add(new);new+=1
  elif line.startswith('-'):removed.add(old);old+=1
  elif line.startswith(' '):old+=1;new+=1
 diff_cache[file]=(added,removed)
 return added,removed

def code(file,ranges,old=False):
 if not ranges:return ''
 out=[];revision=BASE if old else HEAD;lines=source(file,revision);changed=changed_lines(file)[1 if old else 0]
 for start,end in ranges:
  assert start>=1 and end<=len(lines) and end>=start,(file,start,end,len(lines))
  rows=[]
  for i in range(start,end+1):
   line=lines[i-1];cl=' removed' if old and i in changed else ' changed' if i in changed else ''
   # Comments retain their original text and stay in the source excerpt.
   text='<span class="comment">'+escape(line)+'</span>' if line.lstrip().startswith(('//','/*',' *')) else escape(line)
   rows.append(f'<span class="code-line{cl}"><span class="line-number">{i}</span><span class="line-text">{text}</span></span>')
  out.append('<div class="source-card"><div class="source-title"><strong>'+('Before · base' if old else 'After · PR head')+'</strong>'+cite(file,start,end,revision)+'<span class="badge">'+('removed lines tinted red' if old else 'added lines tinted green')+'</span></div><pre class="source-code wrap"><code>'+''.join(rows)+'</code></pre></div>')
 return ''.join(out)

def coverage(data):
 file=data['file'];added,removed=changed_lines(file);covered=set();oldcovered=set()
 for item in data['units']+data.get('trivial',[]):
  for a,b in item.get('ranges',[]):covered.update(range(a,b+1))
  for a,b in item.get('old_ranges',[]):oldcovered.update(range(a,b+1))
 blank_add={i for i in added if not source(file)[i-1].strip()}
 blank_del={i for i in removed if not source(file,BASE)[i-1].strip()} if removed else set()
 missing=sorted(added-covered-blank_add);oldmissing=sorted(removed-oldcovered-blank_del)
 return {'file':file,'units':len(data['units']),'diagrams':len(data.get('base_diagrams',[]))+sum(len(u['diagrams']) for u in data['units']),'added_lines':len(added),'removed_lines':len(removed),'added_nonblank':len(added-blank_add),'removed_nonblank':len(removed-blank_del),'covered_added_nonblank':len((added-blank_add)&covered),'covered_removed_nonblank':len((removed-blank_del)&oldcovered),'missing_added':missing,'missing_removed':oldmissing}

def diff_appendix(file):
 text=git('diff','--no-ext-diff','--unified=5',BASE,HEAD,'--',file)
 bits=[]
 for line in text.splitlines():
  cl='diff-add' if line.startswith('+') else 'diff-del' if line.startswith('-') else 'diff-hunk' if line.startswith('@@') else ''
  bits.append('<span class="'+cl+'">'+escape(line)+'</span>')
 return '<details><summary>Full source diff, including comments and unchanged context</summary><pre class="diff-pre">'+'\n'.join(bits)+'</pre></details>'

def render_file(key,data):
 file,filename=FILES[key];assert data['file']==file
 cov=coverage(data)
 toc=[('short-version','Short version and source revisions'),('terms','Words used here'),('base-models','Base diagrams')]+[(u['id'],f'{i+1:02d}. '+u['title']) for i,u in enumerate(data['units'])]+[('trivial','Trivial changes'),('coverage','Change coverage and complete diff')]
 s=top(data['title']+' · PR4424',toc,filename)
 s+='<header class="hero" id="short-version"><div class="eyebrow">PR4424 · '+escape(file)+'</div><h1>'+escape(data['title'])+'</h1><h2>Short version</h2><div class="short-version">'+bullets(data['summary'])+'</div>'+revision_note()+'<p class="scope-note">This page explains every logical change in <code>'+file+'</code> at this head. Other files appear only as cited context. Code comments are preserved with their source. The complete diff is available below.</p></header>'
 s+='<section id="terms" class="section"><h2>Words used here</h2>'+terms(COMMON_TERMS+data.get('terms',[]))+legend()+'</section>'
 s+='<section id="base-models" class="section"><h2>Base diagrams</h2><p>The same names and colors recur beside the code below. Arrows state the operation or the number of objects in the relationship.</p><div class="base-grid">'+''.join(map(diagram,data['base_diagrams']))+'</div></section>'
 s+='<div class="code-tools"><span>Read each source excerpt beside its explanation. Diagram boxes link to their defining lines.</span><button data-wrap aria-pressed="true">Code wrapping: on</button></div>'
 for i,u in enumerate(data['units']):
  assert u.get('diagrams'),u['id']
  s+='<section class="change" id="'+u['id']+'"><header class="change-heading"><span class="unit-num">Logical change '+f'{i+1:02d}'+'</span><h2>'+escape(u['title'])+'</h2></header><div class="change-grid"><div class="code-side">'+code(file,u.get('ranges',[]))
  if u.get('old_ranges'):s+='<details><summary>Before this change</summary>'+code(file,u['old_ranges'],True)+'</details>'
  s+='</div><div class="explain-side">'+bullets(u['explanation'])+''.join(map(diagram,u['diagrams']))+'</div></div></section>'
 s+='<section id="trivial" class="section"><h2>Trivial changes</h2><p>These changes do not introduce a separate data or execution rule.</p>'
 for t in data.get('trivial',[]):
  s+='<details><summary>'+escape(t['description'])+'</summary>'+code(file,t.get('ranges',[]))+code(file,t.get('old_ranges',[]),True)+'</details>'
 s+='</section><section id="coverage" class="section"><h2>Change coverage and complete diff</h2>'+coverage_table([cov])+bullets(data.get('coverage_notes',[]))+'<p class="small">Coverage counts are computed from <code>git diff --unified=0</code>. Every nonblank added or removed line must belong to a displayed code range. Blank-only changes remain in the full diff.</p>'+diff_appendix(file)+'</section>'+end()
 (OUT/filename).write_text(s)
 return cov

def coverage_table(rows):
 return '<div class="table-scroll"><table><thead><tr><th>File</th><th>Logical changes</th><th>Diagrams</th><th>Added nonblank lines explained</th><th>Removed nonblank lines shown</th></tr></thead><tbody>'+''.join('<tr><td><code>'+r['file']+'</code></td><td>'+str(r['units'])+'</td><td>'+str(r['diagrams'])+'</td><td>'+str(r['covered_added_nonblank'])+' / '+str(r['added_nonblank'])+'</td><td>'+str(r['covered_removed_nonblank'])+' / '+str(r['removed_nonblank'])+'</td></tr>' for r in rows)+'</tbody></table></div>'

def main():
 data={key:json.loads(Path('/tmp/pr4424-'+key+'.json').read_text()) for key in FILES}
 stats=[render_file(key,d) for key,d in data.items()]
 render_index(data,stats)
 (OUT/'diagramming-code-changes-validation.json').write_text(json.dumps({'head':HEAD,'base':BASE,'coverage':stats},indent=2)+'\n')
 print(json.dumps(stats,indent=2))

if __name__=='__main__':
 from pr4424_overview import render_index
 main()
