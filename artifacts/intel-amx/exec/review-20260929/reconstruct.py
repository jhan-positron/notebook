"""Rebuild the merged+verified findings of workflow wf_9d1f4e76-619 from its journal (fallback if synthesis fails)."""
import json, re, sys
J='/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/c1e2475d-c671-4e92-9fc3-579c9ced20ea/subagents/workflows/wf_9d1f4e76-619/journal.jsonl'
starts={}; results={}
order=[]
for line in open(J):
    e=json.loads(line)
    if e.get('label') and e.get('agentId'):
        starts[e['agentId']]=e; order.append(e['agentId'])
    if e.get('type')=='result' and e.get('agentId'):
        results[e['agentId']]=e.get('result')
bylabel={}
for aid,e in starts.items():
    bylabel[e['label']]=results.get(aid)
finders=[l for l in bylabel if l.startswith('find:') or l.startswith('find2:')]
def keyOf(f):
    file=(f.get('location') or '').split(':')[0].strip()
    t=re.sub(r'[^a-z0-9]+',' ',(f.get('title') or '').lower()).strip()
    return file+'|'+t
def merge(raw, roundLabel, res):
    items=[dict(id=f'{roundLabel}-{i+1}',**f) for i,f in enumerate(raw)]
    byId={f['id']:f for f in items}; merged=[]; used=set()
    if res and res.get('groups'):
        for g in res['groups']:
            keep=byId.get(g['keep_id'])
            if not keep or g['keep_id'] in used: continue
            used.add(g['keep_id'])
            dups=[byId[i] for i in g.get('merged_ids',[]) if i in byId and i not in used]
            for d in dups: used.add(d['id'])
            locs=[]
            for l in (keep.get('other_locations') or [])+[x for d in dups for x in [d['location']]+(d.get('other_locations') or [])]:
                if l and l!=keep['location'] and l not in locs: locs.append(l)
            m=dict(keep); m['title']=g.get('title') or keep['title']; m['other_locations']=locs
            m['merged_from']=[keep['id']]+[d['id'] for d in dups]; m['lenses']=[keep['lens']]+[d['lens'] for d in dups]
            m['extra_evidence']='\n'.join(f"[{d['id']} {d['lens']}] {d['evidence']}" for d in dups)[:3000]
            merged.append(m)
        for i in res.get('dropped_as_duplicate_of_seen',[]): used.add(i)
    for f in items:
        if f['id'] not in used:
            m=dict(f); m['merged_from']=[f['id']]; m['lenses']=[f['lens']]; m['extra_evidence']=''; merged.append(m)
    return [dict(m, id=f'{roundLabel}-M{i+1}') for i,m in enumerate(merged)]
r1=[bylabel[l] for l in finders if l.startswith('find:') and bylabel[l]]
raw1=[dict(lens=r['lens'],**f) for r in r1 for f in r['findings']]
merged1=merge(raw1,'R1',bylabel.get('dedup:R1'))
seen={keyOf(f) for f in merged1}
r2=[bylabel[l] for l in finders if l.startswith('find2:') and bylabel[l]]
raw2=[dict(lens=r['lens'],**f) for r in r2 for f in r['findings']]
fresh=[f for f in raw2 if keyOf(f) not in seen]
merged2=merge(fresh,'R2',bylabel.get('dedup:R2'))
LENS=['reach','evidence','intent']
out=[]
for f in merged1+merged2:
    votes=[]
    for ln in LENS:
        v=bylabel.get(f'verify:{ln}:{f["id"]}')
        if v: votes.append(dict(lens=ln,**v))
    ref=sum(1 for v in votes if v['refuted'])
    out.append(dict(f, votes=votes, refutations=ref, survives=len(votes)>0 and ref<2))
cov=[dict(lens=r['lens'],checked=r['conditions_checked'],not_checked=r['conditions_not_checked'],verified_correct=r['verified_correct']) for r in r1+r2]
res=dict(verified=out, lensCoverage=cov, testTable=bylabel.get('map:tests'), changeMap=bylabel.get('map:change'), critic=bylabel.get('critic'))
json.dump(res, open(sys.argv[1],'w'), indent=1)
print('raw1',len(raw1),'merged1',len(merged1),'raw2',len(raw2),'fresh',len(fresh),'merged2',len(merged2))
print('survive',sum(1 for f in out if f['survives']),'of',len(out))
import collections
print(collections.Counter((f['severity'],f['category']) for f in out if f['survives']))
for f in out:
    if f['survives'] and f['severity'] in ('must_fix','should_fix'):
        print('-',f['id'],f['severity'],f['category'],'|',f['title'][:90],'|',f['location'][:60], '| ref',f['refutations'])
