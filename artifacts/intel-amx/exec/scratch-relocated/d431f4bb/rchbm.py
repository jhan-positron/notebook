import json, math, re, datetime as dt
H=json.load(open('/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/hbm-exhaustion-cells.json'))
C=H['cells']; G=H['gaps']
print("totals", H['total_lose'], H['total_exhausted'], H['inside_cells'], H['outside_cells'], H['first_ts'], H['avail_counts'])
print("sum cells lose", sum(c['lose'] for c in C), "sum gaps lose", sum(g['lose'] for g in G), "cells+gaps", sum(c['lose'] for c in C)+sum(g['lose'] for g in G))
# gaps by after_prompt
from collections import defaultdict
gp=defaultdict(list)
for g in G:
    if g['tag'].startswith('fpga'): gp[g['after_prompt']].append((g['tag'],g['lose'],g['tok_bases']))
for k in sorted(gp): print("gap after",k, "passes with lose>0:", sum(1 for x in gp[k] if x[1]>0), "of", len(gp[k]), gp[k])
# per cell table
def mib(b): return None if b is None else b/2**20
tab={}
for c in C:
    tab.setdefault((c['tag'].split('-')[0], c['prompt'], 'cold' in c['tag']), []).append(c)
for key in sorted(tab, key=lambda k:(k[0],k[2],k[1])):
    cs=sorted(tab[key], key=lambda c:c['tag'])
    lose=[c['lose'] for c in cs]; fb=[c['fallback_counter'] for c in cs]
    share=[c['share_est_pct'] for c in cs if c['lose']]
    fr=[c['first_round'] for c in cs]; lp=[c['last_pct'] for c in cs]
    fm=[None if c['free_min_after'] is None else round(mib(c['free_min_after'])) for c in cs]
    eq=all((f is None) or (f==l) for f,l in zip(fb,lose))
    print(f"{key[0]:9s} p{key[1]:5d} {'cold' if key[2] else 'warm'} n={len(cs)} lose={lose} fb={fb} eq={eq} share={share} of {cs[0]['shards_est']} first_round={fr} last%={lp} freeMiB={fm} dur={[c['dur_s'] for c in cs]} tags={[c['tag'] for c in cs]}")
# free GB after cells (passes 2 and 3 min over arms)
print("\nfree after (GB = 1e9) min over arms passes2/3:")
for p in [1024,1536,2048,3000,6144,7168]:
    vals=[c['free_min_after'] for c in C if c['prompt']==p and c['free_min_after'] is not None and 'cold' not in c['tag']]
    print(p, [round(v/1e9,2) for v in vals], [round(v/2**30,2) for v in vals])
# 8192 first pass rounds 1-6
for tag in ['fpgacanon-pass1','fpgabase-pass1']:
    c=[c for c in C if c['tag']==tag and c['prompt']==8192][0]
    r=c['ttft_per_round_ms']; print(tag, "rounds", r, "mean 1-6", sum(r[:6])/6, "first_round", c['first_round'])
print(100*((sum([c for c in C if c['tag']=='fpgacanon-pass1' and c['prompt']==8192][0]['ttft_per_round_ms'][:6])/6)/(sum([c for c in C if c['tag']=='fpgabase-pass1' and c['prompt']==8192][0]['ttft_per_round_ms'][:6])/6)-1))
# first warning timing relative to first fpgabase pass 3000 end and 4096 start
c3=[c for c in C if c['tag']=='fpgabase-pass1' and c['prompt']==3000][0]; c4=[c for c in C if c['tag']=='fpgabase-pass1' and c['prompt']==4096][0]
t0=dt.datetime.fromisoformat(H['first_ts'].replace('Z','+00:00')).timestamp()
print("first warning - 3000 end:", t0-c3['t_end'], " 4096 start - first:", c4['t_start']-t0, "first_s in 4096 cell", c4['first_s'])
# capacity
shard_per_channel=4.5*2**20; card=2**30
print("shards per card no weights:", card/shard_per_channel, "tokens", card/shard_per_channel*1024)
print("59113472 B =", 59113472/2**20, "MiB", 59113472/1e6, "MB; 0x3000=",0x3000/1024,"KiB 0x5800=",0x5800/1024,"KiB")
print("capacity 34,359,738,368 B =", 34359738368/1e9, "GB")
for tag,p in [('fpgabase-cold2-p4096',4096),('fpgabase-cold2-p8192',8192),('fpgacanon-cold2-p4096',4096),('fpgacanon-cold2-p8192',8192)]:
    c=[c for c in C if c['tag']==tag][0]
    shards_eng=20*math.ceil((p+1536)/1024)
    own=shards_eng*144*2**20/2  # per card (2 cards per engine)
    for fm in [c['free_min_after'],c['free_max_after']]:
        est=fm+own
        print(tag, "free after min/max", round(fm/1e9,2), "GB + own", round(own/1e9,2), "GB =", round(est/1e9,2), "GB est fresh; weights take", round((34359738368-est)/1e9,2),"GB; shards", round(est/(144*2**20)), "tokens", round(est/(144*2**20)*1024))
