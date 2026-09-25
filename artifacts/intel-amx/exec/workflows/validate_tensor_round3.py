from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlsplit, unquote
from collections import Counter
import datetime, hashlib, importlib.util, json, re, subprocess

root=Path('/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525')
artifact=root/'status/design-new-tensor-type.html'
repo=root.parent/'tron-VNNIed-K'
doc=BeautifulSoup(artifact.read_text(),'html.parser')
review=BeautifulSoup((root/'status/claude-review-design-new-tensor-type.html').read_text(),'html.parser')
errors=[]
ids=[x['id'] for x in doc.select('[id]')]
assert len(ids)==len(set(ids)), 'duplicate ids'
local=[]; pinned=[]; cache={}
for a in doc.select('a[href]'):
    href=a['href'];u=urlsplit(href)
    if u.scheme in ('http','https'):
        m=re.fullmatch(r'/positron-ai/tron/blob/([a-f0-9]{40})/(.+)',u.path)
        if m:
            commit,file=m.groups();key=(commit,file)
            if key not in cache:
                r=subprocess.run(['git','-C',str(repo),'show',commit+':'+file],text=True,capture_output=True)
                if r.returncode:errors.append({'missing_source':href,'stderr':r.stderr})
                cache[key]=r.stdout.splitlines()
            span=re.fullmatch(r'L(\d+)(?:-L(\d+))?',u.fragment)
            if span:
                lo=int(span[1]);hi=int(span[2] or span[1])
                if not 1<=lo<=hi<=len(cache[key]):errors.append({'bad_lines':href,'file_lines':len(cache[key])})
            pinned.append({'href':href,'label':a.get_text(' ',strip=True),'file_lines':len(cache[key])})
        continue
    target=(artifact.parent/unquote(u.path)).resolve() if u.path else artifact
    if not target.exists():errors.append({'missing_local':href})
    if u.fragment and target.exists():
        target_doc=doc if target==artifact else BeautifulSoup(target.read_text(),'html.parser')
        if not target_doc.find(id=unquote(u.fragment)):errors.append({'missing_anchor':href})
    local.append(href)

expected={f.get('id') for f in review.select('.finding') if re.fullmatch(r'[GH]\d+',f.get('id',''))}
# IDs are sometimes on the heading rather than the wrapper.
if not expected:
    expected={x['id'] for x in review.select('[id]') if re.fullmatch(r'[GH]\d+',x['id'])}
heading=next(h for h in doc.select('#disposition h3') if h.get_text().startswith('Round 3:'))
table=heading.find_next('table')
covered=[a.get_text(strip=True) for row in table.select('tr') for a in row.select('td:first-child a')]
if Counter(covered)!=Counter(expected):errors.append({'review_coverage':{'expected':sorted(expected),'actual':covered}})
residual_json=json.loads(Path('/tmp/round1-residuals.json').read_text())
expected_residual={x['id'] for x in residual_json}
detail=doc.select_one('#disposition details')
residual=[a.get_text(strip=True) for row in detail.select('tr') for a in row.select('td:first-child a')]
if Counter(residual)!=Counter(expected_residual):errors.append({'residual_coverage':residual})

spec=importlib.util.spec_from_file_location('layouts',root/'evidence/check_layouts.py')
layouts=importlib.util.module_from_spec(spec);spec.loader.exec_module(layouts)
formula={'kind':'design arithmetic checks, not C++ implementation tests','packed_v':[layouts.check_v(64,d) for d in (64,128,256,512)],'blocked_packed_k':layouts.check_k()}
for token in range(64):
    for dim in range(128):
        full=((((dim//32)*4+token//16)*16+(dim%32)//2)*16+token%16)*2+dim%2
        panel=(dim//32*4+token//16)*512
        inside=(dim%32//2)*32+2*(token%16)+dim%2
        assert full==panel+inside
formula['panel_decomposition']={'coordinates_checked':64*128,'units':'bf16 element offsets','passed':True}
(root/'evidence/design-round3-layout-checks.json').write_text(json.dumps(formula,indent=2)+'\n')

rule_files=['AGENTS.md','t/AGENTS.md','.agents/skills/run-tron-tests/SKILL.md']
rule_commits=['c7844ca2ce','f46e48ba','98bb8cb2','2880c3aa9b','30c4ac82cb']
rules={f:{c:subprocess.check_output(['git','-C',str(repo),'rev-parse',c+':'+f],text=True).strip() for c in rule_commits} for f in rule_files}
assert all(len(set(x.values()))==1 for x in rules.values())
audit={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Read-only git show and rev-parse at saved commits; no remote fetch','source_files':len(cache),'pinned_links':pinned,'rule_blobs':rules}
(root/'evidence/design-round3-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
result={'checked_at_utc':audit['checked_at_utc'],'artifact':str(artifact),'report_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'scope':'HTML structure, local links and anchors, review-ID coverage, existence of pinned source files and line spans. Source semantics were separately reviewed. No C++ build, test, or benchmark.','ids':len(ids),'local_links':len(local),'pinned_source_links':len(pinned),'round3_findings_covered':len(covered),'round1_residuals_covered':len(residual),'errors':errors,'checks_passed':not errors}
(root/'evidence/design-round3-artifact-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert not errors
