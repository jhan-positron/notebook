import json, re, statistics
R='/home/jhan/workspace/intel-AMX/exec/results/issue4500-20260918'
SJ=f'{R}/summary.json'; SM=f'{R}/summary.md'
d=json.load(open(SJ)); lines=open(SJ).read().splitlines(); md=open(SM).read().splitlines()
cell_ttft_lines=[i+1 for i,l in enumerate(lines) if re.match(r'^   "ttft_s": ',l)]
rep_ttft_lines=[i+1 for i,l in enumerate(lines) if re.match(r'^     "ttft_s": ',l)]
def md_line(c):
    for i,l in enumerate(md,1):
        if l.startswith(f"| {c['block']} | {c['tp']} | {c['users']} | {c['tag']} | {c['arm']} |"): return i
    return None
BUILD={'base':'runtron.main0916 c7844ca2ce (main 2026-09-16, TRON_AMX_DISPATCH=ON, row-major K), version 2026.09.16-c7844ca2, RelWithDebInfo built on 3bda',
       'headoff':'runtron.headoff0916 ff680c8020 (PR 4424 code built with TRON_K_VNNI=OFF, row-major K), version 2026.09.16-ff680c80',
       'vnni':'runtron.pr4424 ff680c8020 (PR 4424, TRON_K_VNNI=ON), version 2026.09.16-ff680c80',
       'vnni2':'runtron.pr4424 ff680c8020 (PR 4424, TRON_K_VNNI=ON), version 2026.09.16-ff680c80 (same binary as vnni, A/A control)',
       'vnnikill':'runtron.pr4424 ff680c8020 (PR 4424, TRON_K_VNNI=ON) + TRON_AMX_DISABLE=1, version 2026.09.16-ff680c80',
       'head30':'tron-tilec/gen/runtron 30c4ac82cb (PR 4424 GitHub head, TRON_K_VNNI=ON), version 2026.09.17-30c4ac82'}
KERNEL={'base':'amx-canon','headoff':'amx-canon','vnni':'amx-vnnik','vnni2':'amx-vnnik','vnnikill':'avx','head30':'amx-vnnik'}
GEN={'m1':256,'m1b':256,'m2':256,'m3':40,'m4':4096}
rows=[]; ri=0
for ci,c in enumerate(d['cells']):
    reps=c['reps']; rl=rep_ttft_lines[ri:ri+len(reps)]; ri+=len(reps)
    v=[r['ttft_s']*1000 for r in reps]
    sd=statistics.stdev(v) if len(v)>1 else 0.0
    arm=c['arm']; blk=c['block']; tag=c['tag']
    cav=[]
    if arm=='headoff': cav.append("headoff = PR 4424 source (ff680c8020) compiled with TRON_K_VNNI=OFF: row-major K, AMX dense kernel present -> classified amx-canon")
    if arm=='vnnikill': cav.append("kill switch TRON_AMX_DISABLE=1 removes the AMX kernels at run time but keeps the VNNI K layout")
    if arm=='vnni2': cav.append("A/A control: second run of the vnni binary in the same repetition")
    if arm=='head30': cav.append("one run only (n=1)")
    if blk=='m2': cav.append(f"env {reps[0]['env']} (early-launch knob: 1 = card launched before Save K even at 2 users; 100 = late launch forced); affects decode step, TTFT unaffected in the data")
    if blk=='m3': cav.append(f"Perfetto tracing on (TRON_TRACE_CATEGORIES {'A: model,scheduler,hwattention' if tag=='catA' else 'B: A + hwattention-detail'}); tracing costs 9-12 % TPS, TTFT effect small (values within the untraced m1 band); generated 40 tokens")
    if blk=='m4': cav.append("perf record/stat attached only after all 'Parsing the prompt took' lines, so TTFT is unaffected by perf; generated 4096 tokens")
    if blk=='m3' and arm=='base' and tag=='catA' and c['tp']==2:
        cav.append("summarize.py merged two runs both named rep1 into n=2: run a (2026-09-19T01:39:52Z, TTFT 3666.8 ms) is the run whose 108 MB trace was renamed prefill-only__m3__base__tp2__8u__catA.perfetto-trace (its rt log was overwritten by the rerun; its lines survive at rt-results.txt:1556-1571); run b (13:42:03Z, TTFT 3180.5 ms) is the clean traced rerun. Use 3180.5 ms for comparisons; the 3423.6 mean is an artifact of the merge")
    if blk in ('m1','m1b','m2','m3','m4'): cav.append("all N 'Parsing the prompt took' values of one run agree to <0.1 ms (prompts enqueued at once and prefilled back to back), so TTFT here = prefill time of all N prompts; per-prompt prefill est. = TTFT / N")
    if c['tp']==4 and blk=='m1': cav.append("tp4 decode TPS swings between runs (per-run state); TTFT is stable")
    row={
      "campaign":"issue4500-20260918","harness":"runtron",
      "model":f"ingested-qwen-3-4b-instruct-2507-tp{c['tp']}","tp":c['tp'],
      "prompt_length":1024,"gen_tokens":GEN[blk],
      "users_total":c['users'],"users_per_engine":c['users'],
      "layout":f"1 runtron engine (stream-generate-text) x {c['users']} users, no proxy, client = runtron itself on delphi-3bda; placement {'--instance 2,4 cards 90/93' if c['tp']==2 else '--instance 1,2 cards 90/93/b9/bc'}, numa 1, --dont-stop",
      "machine_share":"our half",
      "date_utc":reps[0]['ts'][:10],
      "arm_label":f"{blk}/{tag}/{arm}",
      "attention":"fpga","cpu_kernel":KERNEL[arm],"amx_kill_switch":arm=='vnnikill',
      "build":BUILD[arm],
      "n":len(v),"ttft_ms":round(statistics.mean(v),1),"ttft_sd_ms":round(sd,1),
      "ttft_per_rep_ms":[round(x,1) for x in v],
      "ttft_definition":f"runtron server-side 'Parsing the prompt took X s' per request, max over the {c['users']} users of one run, then mean over {len(v)} repetition(s) (summarize.py ttft_max); log line 'HW attention enabled' present in every run",
      "tps_per_user":round(c['tps_mean'],2),
      "caveats":"; ".join(cav),
      "file_refs":[f"{SM}:{md_line(c)}", f"{SJ}:{cell_ttft_lines[ci]} (cell mean ttft_s)"]+[f"{SJ}:{L} (rep {r['rep']} ttft_s, ts {r['ts']})" for L,r in zip(rl,reps)]+[f"{R}/rt/{blk}__{arm}__tp{c['tp']}__{c['users']}u__{tag}__rep{r['rep']}.log ('Parsing the prompt took' lines)" for r in reps]
    }
    rows.append(row)
# m6
M6=f'{R}/m6'; mj=json.load(open(f'{M6}/summary.json')); mlines=open(f'{M6}/summary.json').read().splitlines(); mmd=open(f'{M6}/summary.md').read().splitlines()
B6={'base':'installed nightly deb rinzler 2026.09.18-3faba6d0 (main 3faba6d0fd, deb preset without TRON_AMX_DISPATCH -> no AMX code; AMX-busy 0), /opt/positron/bin/rinzler sha256 27e6883c...',
    'baseminb1':'same nightly deb rinzler 2026.09.18-3faba6d0 (no AMX code) + TRON_HWATTN_EARLY_LAUNCH_MIN_B=1',
    'target':'ci-mimic target deb rinzler 2026.09.18-29a8a547-jhan-ci-mimic-target (main 3faba6d0 + PR 4424 30c4ac82cb, TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON), /var/tmp/jhan/ci-mimic-20260918/root/opt/positron/bin/rinzler sha256 3ee9c8f0...',
    'targetkill':'ci-mimic target deb rinzler 2026.09.18-29a8a547 (main + PR 4424, VNNI K on) + TRON_AMX_DISABLE=1',
    'targetminb1':'ci-mimic target deb rinzler 2026.09.18-29a8a547 (main + PR 4424, VNNI K on) + TRON_HWATTN_EARLY_LAUNCH_MIN_B=1'}
K6={'base':'avx','baseminb1':'avx','target':'amx-vnnik','targetkill':'avx','targetminb1':'amx-vnnik'}
for key in sorted(mj):
    m=re.match(r'tp(\d)__(\d+)u__(\w+)$',key); tp=int(m[1]); u=int(m[2]); arm=m[3]
    reps=mj[key]; rk=sorted(reps,key=int); v=[reps[r]['ttft'] for r in rk]; t=[reps[r]['tps'] for r in rk]
    sd=statistics.stdev(v) if len(v)>1 else 0.0
    mdl=[i for i,l in enumerate(mmd,1) if l.startswith(f"| {tp} | {u} | {arm} |")][0]
    kl=[i for i,l in enumerate(mlines,1) if l.strip()==f'"{key}": {{'][0]
    ttft_lines=[i for i,l in enumerate(mlines,1) if i>kl and '"ttft"' in l][:len(v)]
    pl=42 if tp==2 else 62
    cav=[]
    cav.append(f"harness prompt param 1024 (sharegpt prompts); actual mean prompt tokens {'980.15' if tp==2 else '971.075'}, cache hit {'1.26' if tp==2 else '1.30'} % (perf.json)")
    if arm in ('targetkill',): cav.append("kill switch TRON_AMX_DISABLE=1 removes the AMX kernels at run time but keeps the VNNI K layout; AMX-busy 0 in the 20 s probe")
    if arm in ('base','baseminb1'): cav.append("nightly deb has no AMX code (AMX-busy 0 cycles in the 20 s probe), CPU-scored share = AVX")
    if arm in ('target','targetminb1'): cav.append(f"AMX ran: EXE.AMX_BUSY cycles in the 20 s probe = {'/'.join(str(reps[r]['amx']) for r in rk)}")
    if 'minb1' in arm: cav.append("TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 = card launched before Save K at 2 users; affects decode step, TTFT unchanged vs the same binary without the knob")
    cav.append("TTFT is a client-side wall time (includes HTTP + tokenizer + queueing), not runtron's server-side prompt-parse time; rounds to whole ms")
    rows.append({
      "campaign":"issue4500-20260918 (block m6)","harness":"ci-harness",
      "model":f"ingested-qwen-3-4b-instruct-2507-tp{tp}","tp":tp,
      "prompt_length":1024,"gen_tokens":1536,
      "users_total":u,"users_per_engine":u,
      "layout":f"1 rinzler engine x {u} users, no proxy (client -> http://delphi-3bda:13100/v1 directly), client = systems_test testlib/tps.py via exec/more-testing-r1/st_perf.py on 3bda cores 87-95,231-239; engine placement {'--instance 2,4 cards 90/93' if tp==2 else '--instance 1,2 cards 90/93/b9/bc'}, numa 1; 10 rounds, TPS window tokens 896-1024",
      "machine_share":"our half",
      "date_utc":"2026-09-19",
      "arm_label":f"m6/{arm}",
      "attention":"fpga","cpu_kernel":K6[arm],"amx_kill_switch":arm=='targetkill',
      "build":B6[arm],
      "n":len(v),"ttft_ms":round(statistics.mean(v),1),"ttft_sd_ms":round(sd,1),
      "ttft_per_rep_ms":[float(x) for x in v],
      "ttft_definition":f"CI harness client-side TTFT: wall time from request send to first streamed chunk per (user, round), mean over all {u*10} samples ({u} users x 10 rounds) rounded to whole ms (perf.json ttft_mean_ms), then mean over {len(v)} repetitions; rinzler log 'HW attention enabled' in every cell",
      "tps_per_user":round(statistics.mean(t),2),
      "caveats":"; ".join(cav),
      "file_refs":[f"{M6}/summary.md:{mdl}", f"{M6}/summary.json:{kl}-{kl+len(v)*7} (per-rep ttft at lines {','.join(map(str,ttft_lines))})"]+[f"{M6}/cells/{key}__rep{r}/perf.json:{pl} (ttft_mean_ms; ttfts_ms list follows)" for r in rk]+[f"{M6}/cells/{key}__rep{r}/meta.json (binary, env, placement, started)" for r in rk]+[f"{M6}/cells/{key}__rep{rk[0]}/proof.txt:5-6 (Version, HW attention enabled)"]
    })
print(len(rows))
json.dump(rows,open('/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/d431f4bb-1f10-45d3-99fe-097238cabbde/scratchpad/i4500_ttft_rows_d431.json','w'),indent=0)
