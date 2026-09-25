import json, re, statistics
R="/home/jhan/workspace/intel-AMX/exec/results/"
X="/home/jhan/workspace/intel-AMX/exec/"
BUILD={
 "runtron.p0perf13":"runtron.p0perf13 = commit 544ca05c7a (Version 2026.09.13-544ca05c), cmake cross-avx512 TRON_AMX_DISPATCH=ON, row-major K (PR #3879 canonical AMX)",
 "runtron.vnnik":"runtron.vnnik = commit 5e45ae55ae (Version 2026.09.14-5e45ae55), TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON, per-token scatter K store (Monday VNNI-K binary)",
 "runtron.vnnik2":"runtron.vnnik2 = commit 9928cb2849 (Version 2026.09.14-9928cb28), TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON, runtime switches TRON_K_VNNI_BLOCK / TRON_K_VNNI_STRIPE",
 "runtron.vnnik3":"runtron.vnnik3 = commit 10fc7c724c (Version 2026.09.15-10fc7c72), TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON, review-fixed block store (page-block work units, one join counter)",
 "runtron.vnnik4":"runtron.vnnik4 = commit dc950be5f2 (Version 2026.09.15-dc950be5), TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON, cleaned-up VNNI-K head (block store + striping default on)",
}
def arm_info(camp, arm, env):
    ks = "TRON_AMX_DISABLE=1" in env
    if arm=="off": return "avx", ks, "AMX kill switch TRON_AMX_DISABLE=1 on the canonical binary; the debug log has no AMX on/off line, so the switch is evidenced by the run-header env only"
    if arm=="vnnioff": return "avx", ks, "VNNI binary with the AMX kill switch TRON_AMX_DISABLE=1: VNNI K layout on (build flag), attention scored by the AVX-512 VNNI reader, no AMX (campaign.sh line 18); not the same AVX path as arm off"
    if arm=="base": return "amx-canon", False, "canonical AMX (PR #3879 binary 544ca05c7a), row-major K, kill switch unset; control arm"
    if arm=="vnni": return "amx-vnnik", False, "VNNI K layout on by build flag TRON_K_VNNI=ON (no runtime log line confirms); per-token scatter K store (old store)"
    if arm=="vnni0": return "amx-vnnik", False, "VNNI K layout on (build flag); TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=0 = the old per-token scatter store inside the new binary"
    if arm=="a": return "amx-vnnik", False, "VNNI K layout on (build flag); TRON_K_VNNI_BLOCK=1 TRON_K_VNNI_STRIPE=0 = 16-token block store only"
    if arm=="b": return "amx-vnnik", False, "VNNI K layout on (build flag); TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=1 = helper striping only"
    if arm=="ab": return "amx-vnnik", False, "VNNI K layout on (build flag); TRON_K_VNNI_BLOCK=1 TRON_K_VNNI_STRIPE=1 = block store + helper striping (became the branch default / later PR 4424 head)"
    raise SystemExit(arm)
TTFT_DEF_8U=("runtron 'Parsing the prompt took S s' per request = wall time of the batched prefill of the 8 prompts submitted together (time to the first generated token of each request); "
  "per run the campaign takes the max over the 8 requests (they agree within 0.4 ms); cell value = mean over n repetitions, sd = sample sd over repetitions [summarize.py docstring]")
LAYOUT="runtron stream-generate-text, 1 engine (one tron process, -u 8 users in-process), no proxy, no separate client host; tp2 = --instance 2,4 cards 90:00.0/93:00.0, tp4 = --instance 1,2 cards 90/93/b9/bc; app cores on socket 1; hugepage file /dev/hugepages/amx-vnnik; env -u SYSTEM_CONFIG, TRON_LOG_LEVEL=debug"
def summary_line(camp, tp, prompt, arm):
    lines=open(R+camp+"/summary.md").read().split("\n")
    sec=None
    for i,l in enumerate(lines,1):
        if l.startswith("## tp"): sec=int(l[5:])
        if sec==tp and l.startswith(f"| {prompt} | {arm} |"): return i
    return None
def runs(path):
    out=[];cur=None
    for i,line in enumerate(open(path,errors="replace"),1):
        m=re.match(r"### runtron tp=(\d) prompt=(\d+) arm=(\S+) rep=(\d+) attempt=(\d+) (.*)",line)
        if m:
            cur={"tp":int(m[1]),"prompt":int(m[2]),"arm":m[3],"rep":int(m[4]),"hdr":m[6].strip(),"line":i,"ttft":[],"tl":[],"hw":None,"status":"ok","tps":[]}
            out.append(cur);continue
        if cur is None: continue
        if line.startswith(("RUN-STOPPED","RUN-FAILED","RUN-GIVEN-UP")): cur["status"]="bad"
        m=re.search(r"Parsing the prompt took ([\d.]+) s",line)
        if m: cur["ttft"].append(float(m[1])); cur["tl"].append(i)
        if "HW attention disabled" in line: cur["hw"]=("disabled",i)
        if "HW attention enabled" in line: cur["hw"]=("enabled",i)
        m=re.search(r"at ([\d.]+) average tok/s",line)
        if m: cur["tps"].append(float(m[1]))
    return out
rows=[]
CAMPS={"vnnik-20260914":"vnnik-20260914","vnnik2-20260915":"vnnik2-20260915","vnnik2-confirm-20260915":"vnnik2-20260915","vnnik4-20260915":"vnnik2-20260915"}
for camp,execdir in CAMPS.items():
    rs=[r for r in runs(R+camp+"/rt-results.txt") if r["status"]=="ok" and r["tps"]]
    cells={}
    for r in rs: cells.setdefault((r["tp"],r["prompt"],r["arm"]),[]).append(r)
    for (tp,prompt,arm),reps in sorted(cells.items(), key=lambda kv:(kv[0][0],kv[0][1],["off","base","vnni","vnnioff","vnni0","a","b","ab"].index(kv[0][2]))):
        reps.sort(key=lambda r:r["rep"])
        vals=[max(r["ttft"]) for r in reps]
        mb=re.search(r"bin=\S+/(runtron\.\w+)",reps[0]["hdr"])[1]
        me=re.search(r"env=(.*?) len=",reps[0]["hdr"])[1]
        ck,ks,cav=arm_info(camp,arm,me)
        assert all(r["hw"] and r["hw"][0]=="disabled" for r in reps)
        dates=[re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)",r["hdr"])[1] for r in reps]
        sl=summary_line(camp,tp,prompt,arm)
        extra=""
        if camp=="vnnik2-confirm-20260915": extra=" Confirmation round: summary.md title and rt-results header line 5 still say 'vnnik2', but the run headers show runtron.vnnik3 (10fc7c724c) for vnni0/ab."
        if camp=="vnnik4-20260915": extra=" Source not in the task's list (same campaign family, added); summary.md title says 'vnnik2-20260915 summary' (script reuse) but the data are vnnik4's."
        if tp==4: extra+=" tp4 cells have n=2 only."
        rows.append({
          "campaign":camp,"harness":"runtron","model":f"ingested-qwen-3-4b-instruct-2507-tp{tp}","tp":tp,"prompt_length":prompt,"gen_tokens":256,
          "users_total":8,"users_per_engine":8,"layout":LAYOUT,"machine_share":"our half (socket 1, cards 90/93[/b9/bc]); Bill's half idle per header bill_procs=0",
          "arm_label":arm,"attention":"cpu","cpu_kernel":ck,"amx_kill_switch":ks,"build":BUILD[mb],
          "n":len(reps),"ttft_ms":round(statistics.mean(vals)*1000,1),"ttft_sd_ms":round((statistics.stdev(vals) if len(vals)>1 else 0.0)*1000,1),
          "ttft_per_rep_ms":[round(v*1000,1) for v in vals],"ttft_definition":TTFT_DEF_8U,
          "tps_per_user":round(statistics.mean([statistics.mean(r["tps"]) for r in reps]),2),
          "date_utc":" / ".join(dates),
          "caveats":cav+"; USE_HW_ATTN=0 confirmed by 'HW attention disabled ... USE_HW_ATTN=0' in every rep."+extra,
          "file_refs":[f"{R}{camp}/summary.md:{sl}"]+[f"{R}{camp}/rt-results.txt:{r['line']} (run header rep{r['rep']}: bin, tip, env), :{r['hw'][1]} (HW attention disabled), :{r['tl'][0]}-{r['tl'][-1]} (8 'Parsing the prompt' lines)" for r in reps]+[f"{X}{execdir}/summarize.py (TTFT = max over 8 requests, mean/sd over reps)"],
        })
# ---- smoke rows (1 user) ----
SMOKE_DEF="runtron 'Parsing the prompt took S s' of the single request (1 user, -u 1), one run; greedy smoke: --temperature 0 --pay-for-determinism -s 1, 128 generated tokens; no averaging over users"
def smoke_rows(camp, execdir):
    lines=open(R+camp+"/smoke/smoke.txt",errors="replace").read().split("\n")
    by={}
    for i,l in enumerate(lines,1):
        m=re.match(r"### smoke arm=(\S+) bin=\S+/(runtron\.\w+) env=(.*?) tip=(\S+) prompt=(\d+) len=(\d+) users=(\d+).*?(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)",l)
        if m:
            arm=m[1]; base_arm=re.sub(r"2$","",arm)
            nxt=lines[i]  # next line
            mt=re.search(r"Parsing the prompt took ([\d.]+) s",nxt)
            by.setdefault(base_arm,[]).append({"arm":arm,"bin":m[2],"env":m[3],"ttft":float(mt[1]),"date":m[8],"lines":(i,i+1)})
    out=[]
    for base_arm,reps in by.items():
        ck,ks,cav=arm_info(camp,base_arm,reps[0]["env"])
        vals=[r["ttft"] for r in reps]
        out.append({
          "campaign":camp+" (greedy smoke)","harness":"runtron","model":"ingested-qwen-3-4b-instruct-2507-tp2","tp":2,"prompt_length":1024,"gen_tokens":128,
          "users_total":1,"users_per_engine":1,"layout":"runtron stream-generate-text, 1 engine, -u 1 (single user), tp2 = --instance 2,4 cards 90/93, socket 1; no proxy, no client host; TRON_LOG_LEVEL=info",
          "machine_share":"our half","arm_label":base_arm+(" (+ repeat "+reps[1]["arm"]+")" if len(reps)>1 else ""),"attention":"cpu","cpu_kernel":ck,"amx_kill_switch":ks,"build":BUILD[reps[0]["bin"]],
          "n":len(reps),"ttft_ms":round(statistics.mean(vals)*1000,1),"ttft_sd_ms":round((statistics.stdev(vals) if len(vals)>1 else 0.0)*1000,1),
          "ttft_per_rep_ms":[round(v*1000,1) for v in vals],"ttft_definition":SMOKE_DEF,
          "date_utc":" / ".join(r["date"] for r in reps),
          "caveats":cav+"; smoke run for token-identity checks, not a perf cell: 1 user, pay-for-determinism, 128 tokens; USE_HW_ATTN=0 set by campaign.sh smoke line (TRON_LOG_LEVEL=info, so the 'HW attention disabled' line is not in smoke.txt; check smoke/<arm>.log). "+("The 'tip=' field in vnnik-20260914 smoke headers shows the VNNI tip for every arm (script quirk); the binary path is authoritative." if camp=="vnnik-20260914" else ""),
          "file_refs":[f"{R}{camp}/smoke/smoke.txt:{r['lines'][0]}-{r['lines'][1]}" for r in reps]+[f"{X}{execdir}/campaign.sh (smoke phase: env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 ... --prompt-length 1024 -l 128 -u 1 --temperature 0 --pay-for-determinism)"],
        })
    return out
for camp,execdir in CAMPS.items(): rows+=smoke_rows(camp,execdir)
# ---- vnnik4-models fpga cells ----
lines=open(R+"vnnik4-models-20260915/results.txt",errors="replace").read().split("\n")
cur=None; fp=[]
for i,l in enumerate(lines,1):
    m=re.match(r"### (smoke|rt) cell=fpga model=(\S+) arm=(\S+) bin=\S+/(runtron\.\w+) USE_HW_ATTN=(\S+) attempt=(\d+) (.*?) (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)",l)
    if m: cur={"kind":m[1],"model":m[2],"arm":m[3],"bin":m[4],"hw":m[5],"args":m[7],"date":m[8],"line":i,"ttft":[],"tl":[],"hwl":None,"tps":[]}; fp.append(cur); continue
    if l.startswith("### "): cur=None
    if cur is None: continue
    mt=re.search(r"Parsing the prompt took ([\d.]+) s",l)
    if mt: cur["ttft"].append(float(mt[1])); cur["tl"].append(i)
    if "HW attention enabled" in l: cur["hwl"]=i
    mt=re.search(r"at ([\d.]+) average tok/s",l)
    if mt: cur["tps"].append(float(mt[1]))
for c in fp:
    ck = "amx-canon" if c["bin"]=="runtron.p0perf13" else "amx-vnnik"
    rt = c["kind"]=="rt"
    rows.append({
      "campaign":"vnnik4-models-20260915 (cell fpga"+("" if rt else ", greedy smoke")+")","harness":"runtron","model":c["model"],"tp":2,"prompt_length":1024,"gen_tokens":256 if rt else 128,
      "users_total":8 if rt else 1,"users_per_engine":8 if rt else 1,
      "layout":("runtron stream-generate-text, 1 engine, -u 8 in-process, tp2 = --instance 2,4 cards 90/93, socket 1; no proxy, no client host; TRON_LOG_LEVEL=info" if rt else "runtron stream-generate-text, 1 engine, -u 1, tp2 cards 90/93; --temperature 0 --pay-for-determinism -s 1"),
      "machine_share":"our half","arm_label":c["arm"]+" (base = 544ca05c7a canonical, new = dc950be5f2 VNNI-K head) with USE_HW_ATTN unset","attention":"fpga","cpu_kernel":ck,"amx_kill_switch":False,"build":BUILD[c["bin"]],
      "n":1,"ttft_ms":round(max(c["ttft"])*1000,1),"ttft_sd_ms":0.0,"ttft_per_rep_ms":[round(max(c["ttft"])*1000,1)],
      "ttft_definition":(TTFT_DEF_8U.replace("cell value = mean over n repetitions, sd = sample sd over repetitions [summarize.py docstring]","single run (n=1), max over the 8 'Parsing the prompt' lines (spread 0.06 ms)") if rt else SMOKE_DEF),
      "tps_per_user":round(statistics.mean(c["tps"]),2) if c["tps"] else None,
      "date_utc":c["date"],
      "caveats":"FPGA attention: USE_HW_ATTN unset (env -u USE_HW_ATTN), log line 'HW attention enabled for model ... max_layers=36 engagement=127' at results.txt:"+str(c["hwl"])+"; kill switch unset (env -u TRON_AMX_DISABLE). cpu_kernel is inferred from the binary (AMX-capable, switch unset); which kernel scored the CPU share of attention under FPGA attention, and whether prefill attention ran on the FPGA at all, is not stated in these files. n=1, one attempt. Source not in the task's list (found in the same campaign family).",
      "file_refs":[f"{R}vnnik4-models-20260915/results.txt:{c['line']} (run header), :{c['hwl']} (HW attention enabled), :{c['tl'][0]}-{c['tl'][-1]} ('Parsing the prompt' lines)", f"{X}vnnik4-20260915/models.sh:9-10,29,43,51-52 (fpga cell definition: USE_HW_ATTN unset, env -u TRON_AMX_DISABLE)"],
    })
    if c["tps"]: rows[-1]["tps_per_user"]=round(statistics.mean(c["tps"]),2)
    else: rows[-1].pop("tps_per_user")
for r in rows:
    if "tps_per_user" in r and r["tps_per_user"] is None: r.pop("tps_per_user")
json.dump(rows,open("/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/d431f4bb-1f10-45d3-99fe-097238cabbde/scratchpad/rows.json","w"),indent=0)
print(len(rows),"rows")
for r in rows: print(f"{r['campaign'][:28]:28s} tp{r['tp']} p{r['prompt_length']} {r['arm_label'][:14]:14s} {r['attention']:4s} {r['cpu_kernel']:9s} n={r['n']} ttft={r['ttft_ms']} sd={r['ttft_sd_ms']} reps={r['ttft_per_rep_ms']} tps={r.get('tps_per_user')}")
