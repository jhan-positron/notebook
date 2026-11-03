import csv, json, statistics, math, sys
RES="/home/jhan/workspace/intel-AMX/exec/results/td-20261016"
PAIRS=[("baseoff","pocoff"),("clean","baseoff"),("base","poc"),("base","new"),("baseoff","newoff"),("newoff","trunc"),("new","trunc"),("new","newoff"),("baseoff","base"),("clean","new")]
LABORDER={"Embedding":-1,"WQ":0,"WK":1,"WV":2,"WQ roped":3,"WK roped":4,"Attn out":5,"WO":6,"WFF1":7,"WFF3":8,"WFF2":9,"Logits":10,"Top-k Logits":11,"Top-k Token IDs for Logits":12}
def p95(v):
    v=sorted(v); pos=(len(v)-1)*0.95; lo=math.floor(pos); hi=min(lo+1,len(v)-1); return v[lo]+(v[hi]-v[lo])*(pos-lo)
for off,on in PAIRS:
    j=json.load(open(f"{RES}/layers-{off}-vs-{on}.json"))["summary"]
    wo0=[]; wo_any=[]; anyrec=[]; logits={}
    with open(f"{RES}/layers-{off}-vs-{on}.csv") as f:
        for r in csv.DictReader(f):
            rel=float(r["rel_l2"]); fc=float(r["frac_changed"]); tok=int(r["token"]); lay=int(r["layer"]) if r["layer"] else -1
            if r["label"]=="WO" and lay==0: wo0.append((tok,rel,fc,float(r["max_abs"])))
            if rel>0:
                if r["label"]=="WO": wo_any.append((tok,lay,rel,fc))
                anyrec.append((tok, lay if r["label"] not in ("Logits","Top-k Logits","Top-k Token IDs for Logits") else 99, LABORDER.get(r["label"],50), r["label"], rel, fc))
            if r["label"]=="Logits": logits[tok]=(rel,fc)
    wo0.sort(); wo_any.sort(); anyrec.sort()
    diff=[r for r in wo0 if r[1]>0]
    print(f"== {off} vs {on}: n={j['n_keys_compared']} over={j['n_over_threshold']} min_tok={j['min_token_over']} first_json={j['first_over']}")
    print(f"   first WO (tok,layer,rel,fc): {wo_any[0] if wo_any else None}")
    print(f"   first any record (fwd order): {anyrec[0] if anyrec else None}")
    print(f"   WO L0: n_tokens={len(wo0)} n_diff={len(diff)} first6={[r[0] for r in diff[:6]]} median_rel={statistics.median([r[1] for r in diff]) if diff else 0:.3e} max_rel={max([r[1] for r in diff]) if diff else 0:.3e} median_fc={statistics.median([r[2] for r in diff]) if diff else 0:.4f}")
    at128=[r for r in wo0 if r[0]==128]; print(f"   WO L0 at 128: {at128}")
    if diff: print(f"   WO L0 diff tokens all >=128? {all(r[0]>=128 for r in diff)}; n_diff decode={len([r for r in diff if r[0]>=1024])}; diff tokens (first 10) {[r[0] for r in diff[:10]]} last {[r[0] for r in diff[-3:]]}")
    mt=j['min_token_over']; print(f"   logits at min token {mt}: {logits.get(mt)}")
    s=json.load(open(f"{RES}/steps-{off}-vs-{on}.json")); st=s["steps"]; sm=s["summary"]
    fr=[x["frac_changed"] for x in st]; ma=[x["max_abs_delta"] for x in st]
    flips=[x for x in st if not x["same_top1"]]
    print(f"   steps: ident={sm['n_identical_steps']} flips={sm['flip_steps']} frac min={min(fr):.4f} med={statistics.median(fr):.4f} summ_med={sm['nonflip_median_frac_changed']:.4f} meanabs={sm['nonflip_median_mean_abs_delta']:.4f} mv med/p95={sm['nonflip_median_abs_delta_pair']}/{sm['nonflip_p95_abs_delta_pair']} maxabs med={statistics.median(ma):.3f} max={max(ma):.3f} margin={sm['median_margin_off']} tvd={sm['max_tvd']:.4f}")
    print(f"   step1 frac={st[0]['frac_changed']:.4f}; step65 frac={[x['frac_changed'] for x in st if x['step']==65]}")
    for x in flips: print(f"   flip step {x['step']} top {x['off_top1']}/{x['off_top2']} margin {x['margin_off']} ulps {x['margin_off_ulps']} delta {x['delta_pair']} = {x['delta_pair']/x['ulp_top1_off']} ulps on_top1={x['on_top1']} ulp_top1={x['ulp_top1_off']}")
    mv=[abs(x["delta_pair"])/x["ulp_top1_off"] for x in st if x["ulp_top1_off"]]
    print(f"   p95 movement ulps={p95(mv):.3f} max movement ulps={max(mv):.2f}; margin med ulps={statistics.median([x['margin_off_ulps'] for x in st])}")
