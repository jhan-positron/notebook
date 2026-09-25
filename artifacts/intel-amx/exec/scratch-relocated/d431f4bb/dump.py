import json, statistics, re
R="/home/jhan/workspace/intel-AMX/exec/results"
def load(camp, tag):
    return json.load(open(f"{R}/{camp}/{tag}/perf.json"))
def cell(d):
    out={}
    for r in d.get('results',[]):
        m=re.search(r'_p(\d+)$', r['name']); p=int(m.group(1))
        out[p]={'ttft':r.get('ttft_mean'),'tps':r.get('tps_mean')}
    for r in d.get('raw',[]):
        m=re.search(r'_p(\d+)$', r['name']); p=int(m.group(1))
        t=r.get('ttfts_ms',[])
        out.setdefault(p,{})
        out[p].update({'n':len(t),'rawmean':statistics.mean(t) if t else None,'prompt_tokens':r.get('prompt_tokens'),'cached':r.get('cached_tokens'),'reqs':r.get('engine_requests'),'hw_ok':r.get('hwattn_ok'),'unset_ok':r.get('hwattn_unset_ok')})
    return out
tags={'q4b-fpga-20260921':['fpgabase-pass1','fpgacanon-pass1','canon-pass1','fpgacanon-cold-p4096','fpgacanon-cold-p8192','fpgabase-cold-p4096','fpgabase-cold-p8192'],
      'q4b-swattn-20260919':['base-pass1','base-pass2','base-pass3','canon-pass1','canon-pass2','canon-pass3','check-8u-p8192']}
for camp, ts in tags.items():
    for t in ts:
        d=load(camp,t)
        print(f"== {camp}/{t} started={d.get('started')} finished={d.get('finished')} arm={d.get('arm')}")
        c=cell(d)
        for p in sorted(c):
            v=c[p]
            pt=v.get('prompt_tokens'); ca=v.get('cached')
            cache_pct=None
            try:
                if isinstance(pt,(int,float)) and isinstance(ca,(int,float)) and pt: cache_pct=100*ca/pt
                elif isinstance(pt,list) and isinstance(ca,list) and sum(pt): cache_pct=100*sum(ca)/sum(pt)
            except Exception as e: cache_pct=str(e)
            print(f"  p{p:5d} ttft={v.get('ttft')} tps={v.get('tps')} n={v.get('n')} rawmean={v.get('rawmean')} cache%={cache_pct} reqs={v.get('reqs')} hw_ok={v.get('hw_ok')} unset_ok={v.get('unset_ok')}  prompt_tokens_type={type(pt).__name__} cached_type={type(ca).__name__}")
