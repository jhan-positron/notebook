#!/usr/bin/env python3
"""Build r4/status.json: carry round-3 statuses for items in unchanged files; take the workflow's
verdicts for the nine changed-file items. Also dump the verifier/finder outputs for authoring."""
import json, sys
SP='/tmp/claude-0/-home-jhan-workspace-intel-AMX/5827c364-b93e-4e5c-aa49-89cb6addf5a4/scratchpad/pr3879'
J='/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/5827c364-b93e-4e5c-aa49-89cb6addf5a4/subagents/workflows/wf_06ebd45f-af6/journal.jsonl'
items=json.load(open(f'{SP}/r4/round3_comments.json'))
changed={'doc/intel-amx.md','t/CMakeLists.txt','t/t_amx_logit_ab.cpp'}
verdict={}; finder=None; refutes={}
for line in open(J):
    try: j=json.loads(line)
    except: continue
    if j.get('type')!='result': continue
    r=j.get('result')
    if isinstance(r,str):
        try: r=json.loads(r)
        except: pass
    if isinstance(r,dict) and 'items' in r:
        for it in r['items']: verdict[it['id']]=dict(it, group=r['group'], extra=r.get('extra_observations',''))
    elif isinstance(r,dict) and 'candidates' in r: finder=r
    elif isinstance(r,dict) and 'results' in r: refutes[r['group']]=r['results']
st={}
for c in items:
    cid=c['id']
    if c['file'] in changed and cid in verdict:
        v=verdict[cid]
        st[cid]=dict(status=v['status'], new_line=v['new_line'], snippet_start=v['snippet_start'], snippet_end=v['snippet_end'],
                     remaining=v.get('remaining',''), evidence='; '.join(f"{e['file']}:{e['line']}" for e in v.get('evidence',[])[:3]),
                     followup_voice=v.get('followup_voice',''), fixed_voice=v.get('fixed_voice',''), suggested_fix=v.get('suggested_fix'),
                     deviation=v.get('deviation_from_suggestion',''), still_blocker=v.get('still_blocker', c['blocker']))
    else:
        status='PARTIAL' if c['r3_status']=='PARTIAL' else 'NOT_ADDRESSED'
        st[cid]=dict(status=status, new_line=c['line'], snippet_start=c['snip'][0], snippet_end=c['snip'][1],
                     remaining=c.get('r3_remaining',''), evidence='file unchanged since 96b5a6c72', still_blocker=c['blocker'])
json.dump(st, open(f'{SP}/r4/status.json','w'), indent=1)
json.dump(dict(verdict=verdict, finder=finder, refutes=refutes), open(f'{SP}/r4/workflow_out.json','w'), indent=1)
print('status entries:', len(st), '| changed-file verdicts:', sorted(verdict), '| finder candidates:', len(finder['candidates']) if finder else None, '| refute groups:', sorted(refutes))
for cid,v in verdict.items():
    print(f"  {cid}: {v['status']} @ {v['new_line']} blocker={v.get('still_blocker')} | remaining: {v.get('remaining','')[:160]}")
