import json,sys,os,re,collections
WS='/home/jhan/workspace/intel-AMX'; NB='/home/jhan/workspace/notebook'
L=json.load(open(sys.argv[1])); F=L['files']; OUT=sys.argv[2]
REMAP=[('PR3879/','pr3879/'),('VNNIed-K-in-place/','vnnied-k-in-place/')]
def repo_rel(p):
    rel=os.path.relpath(p,WS)
    for a,b in REMAP:
        if rel.startswith(a): rel=b+rel[len(a):]
    return 'artifacts/intel-amx/'+rel
prop=[f for f in F if f['decision'].startswith('proposed')]
t4logs=[f for f in prop if '/exec/results/t4/' in f['path'] and f['path'].endswith('.log')]
core=[f for f in prop if f not in t4logs]
def mib(fs): return sum(f['size'] or 0 for f in fs)/1048576
lb=collections.defaultdict(list)
for f in F:
    d=f['decision']
    if d.startswith('proposed'): continue
    if 'held by' in d: key='duplicate (held by compact text)'
    elif d.startswith('duplicate'): key='duplicate (already mirrored)'
    else: key=re.sub(r' on 2026.*','',d.split('(')[1].rstrip(')')) if '(' in d else 'other'
    lb[key].append(f)
g=[f"computed-from: mirror-vs-VNNI-K.html <- {len(prop)} files, {mib(prop):.2f} MiB; left behind: {sum(len(v) for v in lb.values())} files ({', '.join(f'{k}: {len(v)}' for k,v in sorted(lb.items()))})",
   f"  item A (core set): {len(core)} files, {mib(core):.2f} MiB; item B (t4 per-request runtron logs, cited by line for measured numbers, no compact text holds their lines): {len(t4logs)} files, {mib(t4logs):.2f} MiB",
   "  proposed repo paths (A):"]
for f in sorted(core,key=lambda x:x['path']): g.append(f"    {repo_rel(f['path'])}  {f['size']}")
g.append("  proposed repo paths (B, t4 logs):")
for f in sorted(t4logs,key=lambda x:x['path']): g.append(f"    {repo_rel(f['path'])}  {f['size']}")
g.append("  left behind:")
for k,v in sorted(lb.items()):
    g.append(f"    {k}: {len(v)} files, {mib(v):.2f} MiB")
    for f in sorted(v,key=lambda x:x['path']): g.append(f"      left behind ({k}) {os.path.relpath(f['path'],WS)} {f['size'] or 0}")
open(f'{OUT}/gate-computed-from.txt','w').write('\n'.join(g)+'\n')
inv=["# Lineage inventory: mirror-vs-VNNI-K.html","",
"Written 2026-09-20 by the handoff run (Step 4b, Computed-from files). One line per file the page's input cites, with the decision taken. Sizes in bytes. Paths are relative to the canonical root `claude-agentsrv:/home/jhan/workspace/intel-AMX`. A per-repetition log is a duplicate when the proposed compact text holds every cited line that carries a measured number (checked line by line on the `[Request N] ...` payload).","",
"- generator: `exec/vnnik-20260914/gen_compare.py` (mirrored at `artifacts/intel-amx/exec/vnnik-20260914/gen_compare.py`)",
"- input: `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json` (hand-edited after build)",
"- input built by: `exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` (Claude Workflow script; origin: `~/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/80bfb407-086b-42a0-a4b7-cb11b85eb459/workflows/scripts/`)",
"- regenerate: `run on claude-agentsrv: python3 /home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_compare.py /home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/mirror-vs-vnni-rows.json <OUT>` (one line differs: the \"Pulled from ... on <timestamp>\" sentence)","",
"| Decision | Canonical path (relative) | Repo path or reason | Bytes | Note |","|---|---|---|---|---|"]
for f in sorted(F,key=lambda x:(not x['decision'].startswith('proposed'),x['path'])):
    d=f['decision']; rel=os.path.relpath(f['path'],WS)
    if d.startswith('proposed'): tgt='`'+repo_rel(f['path'])+'`'
    elif d.startswith('duplicate (artifacts'): tgt='already at `'+d[len('duplicate ('):-1]+'`'
    else: tgt=d
    inv.append(f"| {'preserved' if d.startswith('proposed') else 'left behind'} | `{rel}` | {tgt} | {f['size'] or 0} | {(f['note'] or f['sample_desc'][:60]).replace('|','/')} |")
open(f'{OUT}/mirror-vs-VNNI-K.html.lineage.md','w').write('\n'.join(inv)+'\n')
json.dump(dict(core=[(f['path'],repo_rel(f['path']),f['size']) for f in core],t4logs=[(f['path'],repo_rel(f['path']),f['size']) for f in t4logs],workflow_script=L['workflow_script']),open(f'{OUT}/proposal.json','w'),indent=1)
print(g[0]); print(g[1]); print("inventory rows:",len(F)); print("t4 logs:",[os.path.basename(f['path']) for f in t4logs])
