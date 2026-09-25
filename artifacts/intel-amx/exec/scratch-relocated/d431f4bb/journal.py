import re, json, datetime, collections
J="/home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921/hbm-journal-20260921.txt"
C=json.load(open("/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/hbm-exhaustion-cells.json"))
pat=re.compile(r'^(\S+) \S+ rinzler\[(\d+)\]: \[(\d\d:\d\d:\d\d\.\d+)\|rz(\d)/4\|thread (\d+)\|cpu \d+\] \[warning\] shard base tok_ix (\d+) on dev (\d+): HBM exhausted at (0x[0-9A-Fa-f]+) per KV slot; (\d+) of (\d+) slots lose HW attention')
ex=re.compile(r'^(\S+) \S+ rinzler\[(\d+)\]: \[(\d\d:\d\d:\d\d\.\d+)\|rz(\d)/4\|.*\] \[warning\] (\S+) HBM bypass space exhausted; .* requires (0x[0-9A-Fa-f]+)B but there is only (0x[0-9A-Fa-f]+) available')
rows=[]; exs=[]
for line in open(J):
    m=pat.match(line)
    if m:
        ts=datetime.datetime.strptime(m.group(1),"%Y-%m-%dT%H:%M:%S%z").timestamp()
        frac=float("0."+m.group(3).split(".")[1]); ts+=frac
        rows.append(dict(ts=ts,pid=m.group(2),rz=int(m.group(4)),thread=m.group(5),tok=int(m.group(6)),dev=int(m.group(7)),per=m.group(8),lost=int(m.group(9)),of=int(m.group(10))))
        continue
    m=ex.match(line)
    if m:
        ts=datetime.datetime.strptime(m.group(1),"%Y-%m-%dT%H:%M:%S%z").timestamp()
        exs.append(dict(ts=ts,rz=int(m.group(4)),card=m.group(5),req=int(m.group(6),16),avail=int(m.group(7),16)))
print("lose rows",len(rows),"exhausted rows",len(exs))
print("all 36 of 36?",collections.Counter((r['lost'],r['of']) for r in rows))
print("per-slot sizes",collections.Counter(r['per'] for r in rows))
print("requires",collections.Counter(hex(e['req']) for e in exs))
print("avail distribution (hex):",sorted(collections.Counter(hex(e['avail']) for e in exs).items(), key=lambda kv:-kv[1])[:12])
print("cards:",collections.Counter(e['card'] for e in exs))
print("rz x dev:",collections.Counter((r['rz'],r['dev']) for r in rows))
def fmt(ts): return datetime.datetime.utcfromtimestamp(ts).strftime("%H:%M:%S")
cells=[c for c in C['cells'] if c['tag'].startswith('fpga')]
cells.sort(key=lambda c:c['t_start'])
assigned=set()
print()
for c in cells:
    inside=[r for r in rows if c['t_start']<=r['ts']<=c['t_end']]
    for r in inside: assigned.add(id(r))
    dur=c['t_end']-c['t_start']
    print(f"{c['tag']:22s} p{c['prompt']:<5d} {fmt(c['t_start'])}-{fmt(c['t_end'])} dur {dur:6.0f}s n={len(inside):4d} json={c['lose']}")
    if inside:
        ts=[r['ts'] for r in inside]
        print(f"   first warn at +{min(ts)-c['t_start']:.0f}s ({100*(min(ts)-c['t_start'])/dur:.0f}% of cell), last at +{max(ts)-c['t_start']:.0f}s ({100*(max(ts)-c['t_start'])/dur:.0f}%)")
        # deciles
        dec=collections.Counter(int(10*(r['ts']-c['t_start'])/dur) for r in inside)
        print("   per-decile counts:",[dec.get(i,0) for i in range(10)])
        print("   per engine:",dict(sorted(collections.Counter(r['rz'] for r in inside).items())))
        print("   per dev:",dict(sorted(collections.Counter(r['dev'] for r in inside).items())))
        print("   per tok base:",dict(sorted(collections.Counter(r['tok'] for r in inside).items())))
        print("   per (engine,dev):",dict(sorted(collections.Counter((r['rz'],r['dev']) for r in inside).items())))
        # distinct (engine, dev, tok, second) ~ distinct shard-alloc attempts
        nsh=c['prompt']//1024 + (1 if c['prompt']%1024 else 0)
        tot_tok=c['prompt']+1536
        nsh_tot=(tot_tok+1023)//1024
        print(f"   shards per request: prompt-only {nsh}, prompt+1536 gen {nsh_tot}; 80 req -> {80*nsh} / {80*nsh_tot} shards; x2 devs -> {160*nsh} / {160*nsh_tot}")
        print(f"   share if 1 warn=1 shard(dev-agnostic): {100*len(inside)/(80*nsh_tot):.0f}% (all shards) .. {100*len(inside)/(80*nsh):.0f}% (prompt shards only); if 1 warn = 1 (shard,dev): {100*len(inside)/(160*nsh_tot):.0f}% .. {100*len(inside)/(160*nsh):.0f}%")
outside=[r for r in rows if id(r) not in assigned]
print("\noutside cells:",len(outside))
# where do the outside ones fall: nearest cell before
for c in cells:
    nxt=[x for x in cells if x['t_start']>c['t_end']]
    gap_end=min(x['t_start'] for x in nxt) if nxt else c['t_end']+3600
    o=[r for r in outside if c['t_end']<r['ts']<gap_end]
    if o:
        print(f"  after {c['tag']} p{c['prompt']} ({fmt(c['t_end'])}): {len(o)} warnings from +{min(r['ts'] for r in o)-c['t_end']:.0f}s to +{max(r['ts'] for r in o)-c['t_end']:.0f}s; per engine {dict(collections.Counter(r['rz'] for r in o))}; tok {dict(sorted(collections.Counter(r['tok'] for r in o).items()))}")
pre=[r for r in outside if r['ts']<cells[0]['t_start']]
print("  before first cell:",len(pre))
# also: time-adjacent pairs (same engine, same thread, within 0.01 s, dev0 and dev1)
print()
print("first 12 lose rows:")
for r in rows[:12]: print("  ",fmt(r['ts']),f"{r['ts']%1:.3f}",'rz',r['rz'],'dev',r['dev'],'tok',r['tok'],'thread',r['thread'])
