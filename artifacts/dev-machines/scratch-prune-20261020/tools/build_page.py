import sys, os, re, json, html, collections
SP=sys.argv[1]; OUTDIR=sys.argv[2]
GiB=1024**3; MiB=1024**2
D=json.load(open(f"{SP}/data.json"))
E=D["entries"]; TOT=D["total"]
scratch={}
for l in open(f"{SP}/3bda-scratch-files.tsv", encoding="utf-8", errors="replace"):
    p=l.rstrip("\n").split("\t",2)
    if len(p)==3: scratch[p[2][len("/scratch/jhan/"):]]=(int(p[0]),p[1])
# content-identical copies (meaningful = >= 256 bytes)
repo_md5=collections.defaultdict(list)
for l in open(f"{SP}/repo-md5.txt", encoding="utf-8", errors="replace"):
    h,p=l.rstrip("\n").split("  ",1); repo_md5[h].append(p)
archived={}; checked=set()
for f in ["remote-md5.clean.txt","doccheck-md5.txt","fullcheck-md5.txt"]:
    for l in open(f"{SP}/{f}"):
        h,p=l.rstrip("\n").split("  ",1); checked.add(p)
        if h in repo_md5: archived[p]=repo_md5[h][0]
meaningful={p:rp for p,rp in archived.items() if scratch.get(p,(0,))[0]>=256}
trivial_n=len(archived)-len(meaningful)
def g(b): return f"{b/GiB:.1f}"
def g2(b): return f"{b/GiB:.2f}"
def mi(b): return f"{b/MiB:.1f}"
def esc(s): return html.escape(str(s))
# ---- groups for the chart ----
names=sorted(E, key=lambda t:-E[t]["ondisk"])
def pick(pred): return [t for t in names if pred(t)]
used=set()
def take(label, members, note=""):
    ms=[m for m in members if m in E and m not in used]
    for m in ms: used.add(m)
    agg={"ondisk":sum(E[m]["ondisk"] for m in ms),"files":sum(E[m]["files"] for m in ms),
         "by":{c:sum(E[m]["by"][c] for m in ms) for c in D["classes"]},
         "archived_n":sum(E[m]["archived_n"] for m in ms),"newest":max(E[m]["newest"] for m in ms),
         "members":ms,"label":label}
    return agg
groups=[]
groups.append(take("perf-fluctuation",["perf-fluctuation"]))
groups.append(take("pdjn",["pdjn"]))
groups.append(take("pr3244",["pr3244"]))
groups.append(take("ab22 to ab62 campaign kits", pick(lambda t: re.match(r"ab\d+b?$",t) or t=="ab62rounds")))
groups.append(take("tron-perfetto-* capture runs", pick(lambda t: t.startswith("tron-perfetto-") and "install" not in t)))
groups.append(take("workspace (story2814)",["workspace"]))
groups.append(take("tron-pr3070",["tron-pr3070"]))
groups.append(take("laptop-bkup",["laptop-bkup"]))
groups.append(take("pdjn-wt",["pdjn-wt"]))
groups.append(take("flat_freq_tests",["flat_freq_tests"]))
groups.append(take("claude-dev-migrate",["claude-dev-migrate"]))
groups.append(take("gate campaign dirs (g2*, ring20, gate15, analysis, simlot, ...)", pick(lambda t: t.startswith(("g2","ring20","gate15","preflight","approvals","builds","analysis","legacy-adjudicated","simlot","stage","from-claude-mining","f3kit")))))
groups.append(take("runtron installs (symbols, frozen, tron-perfetto-*install*)", pick(lambda t: t in ("symbols","frozen") or (t.startswith("tron-perfetto-") and "install" in t))))
groups.append(take("t1-goldens",["t1-goldens"]))
rest=[t for t in names if t not in used]
groups.append(take(f"everything else ({len(rest)} entries)", rest))
chart_rows=[{"label":gr["label"],"total":gr["ondisk"],"seg":{c:gr["by"][c] for c in D["classes"]},"members":gr["members"]} for gr in groups]
chart_rows=sorted(chart_rows[:-1], key=lambda r:-r["total"])+chart_rows[-1:]
# ---- per-entry descriptions (evidence gathered 2026-10-21) ----
DESC={
"perf-fluctuation":("Decode-speed campaigns of 2026-08-07 to 08-19 on delphi-3bda and delphi-3c51: deep-dive, pfgate-3bda and the tron-perfetto 5cat runs.",
  "The 51 analysis tools and 3 pfgate scripts (3bda-scratch mirror), and results.csv, identity.env, harness.sh and metrics.json of the campaigns the reports cite (alpha-scratch mirror). All 502 explicit mirrors match byte for byte.",
  "kvwait.bin timing dumps (one per draw, KVMED MiB each before compression, 589 files), perf.script and perf.data of perfcamp, the vtune database, and per-draw logs. The status-report lineage files record them as left behind because of size. CONTEXT.md of intra-pass says the kvwait tags 3000 and 4000 were never mined.",
  "Delete the traces. kvwait.bin is the one raw set that may still be wanted; decide before deleting. The 18 install-* binaries are rebuilds of worktrees that still exist under ~/workspace/ai-runs (tron-kvprobe, tron-pfgate, tron-wadefix, tron-wclsbypass, tron-fpgause)."),
"pdjn":("PDJN decode-jitter campaigns of 2026-08-09 to 08-12 (p4dab, txlat, addrmap, chunkab, u1, ctl-llama8b, shape and bare runs). The track was suspended on 2026-08-11.",
  "mine.py and the two campaign-v4.sh scripts (3bda-scratch mirror), the perfetto-5cat-report-v3.py copies, and the suspended-track handoff index in workspace/project-PDJN.",
  "The mine1 to mine7 outputs (txt and csv, about 0.8 GiB before compression), per-campaign metrics, and 4 runtron binaries (txlat and addrmap builds of pdjn-wt, 407 MiB each).",
  "Delete the traces (42.5 GiB on disk). The binaries are rebuildable from pdjn-wt plus the archived diff. The mining outputs are small; archive them if the track may resume."),
"pr3244":("Two clean git checkouts of tron for PR 3244 (head 5412ede and base 7cad9bf, 2026-07-27) with full builds, Rust toolchains and ingest virtual environments.",
  "Nothing, and nothing needs to be: both checkouts are clean (git status shows no changes).",
  "Only the model export traces under ingest/traces (8 MiB on disk per checkout). The llama-3.1-8b export was reused on 2026-08-15 because the Hugging Face repository was gated.",
  "Delete. Keep the two ingest/traces folders (16 MiB) if gated exports are still a problem."),
"workspace":("story2814/compare_perf: five PR 2906 perf-test runs of 2026-06-08 to 06-10. Each run holds two tron worktrees with builds, perf captures (.trace) and notes.",
  "Nothing by content. The codex handoff of 2026-06-08 cites the notes but does not mirror them.",
  "The notes (comparison_summary.md, run_config.txt, candidate_tracked_diff.patch, metrics csv) and the 8 PR2906 patch and note files: 12 small files, none in the notebook. The .trace captures are raw data of a closed investigation.",
  "Archive the 12 note and patch files (under 1 MiB), then delete the directory."),
"tron-pr3070":("A tron build of pull/3070/head from 2026-07-09, used by the flat-freq ladder runs.",
  "The ladder scripts that call it (delphi-flat-freq test-scripts).",
  "Nothing unique: it is a build output.",
  "Delete."),
"laptop-bkup":("A backup of the Windows laptop from 2026-05-28 and 05-29: Downloads (installers, two pftrace files, Arm design review, asimov-registers), the WSL home and the desktop.",
  "Copies of the intel-amd comparison scripts and write-up that also exist elsewhere (149 content matches, all duplicates of files archived from other locations).",
  "Everything else. This is personal data, not project data.",
  "Your decision. Nothing in the notebook depends on it."),
"pdjn-wt":("A tron worktree at trunk 12804a812 with 3 modified files (model.hpp, worker.cpp, memory.cpp) and 5 untracked build logs.",
  "The full tracked diff: worktree-snapshots/pdjn-wt-tracked-12804a812.diff is byte-identical to the live git diff (md5 25d250a9..., 13,000 bytes).",
  "Nothing: the build logs are untracked scratch.",
  "Delete. The worktree can be recreated from trunk plus the archived diff."),
"flat_freq_tests":("Results of the flat-frequency investigation of 2026-06-30 to 07-20 (24 h sweep, gpt-oss single runs, ladders, CI workload profiles), its scripts, README and the from-claude documents.",
  "README.md (identical), all 12 scripts, and 2 of the 43 from-claude files (bystander-probe.html, suspicion-ledger.html).",
  "41 from-claude files (problem definition, investigation plan, PAL consensus log, post-ab57 runbook, ab58-report.md, goal1-conclusion.html, handoff-run-ci-tests.md, simlot-S1-report.md, tron-architecture.html, analysis scripts, csv and svg data; about 1.3 MiB together) and the result trees.",
  "Archive from-claude/ first (1.3 MiB). The 9 traces (0.5 GiB on disk) can go. The result trees (1.4 GiB on disk) are your decision."),
"claude-dev-migrate":("Staging area of the 2026-08-27 to 08-28 container migration: the image tar, two writable-layer tars, dpkg lists, file lists and rsync logs.",
  "Nothing. The handoff records the migration as complete and verified on sw-dev-01 and agentsrv.",
  "rwlayer-tmp-20260827.tar (the alpha container's /tmp, 1.1 GiB) was never restored anywhere, by decision.",
  "Delete once the alpha container is no longer needed."),
"t1-goldens":("AMX T1 golden token and logit dumps saved on 2026-08-19 by p2-t1-ext.sh (8 files, 4 of them 39 to 345 MiB).",
  "Nothing. The AMX status page of 2026-08-19 points at this directory as the T1 golden location.",
  "All 8 files.",
  "Keep while the AMX T1 comparison is open; otherwise your decision."),
"documents":("27 Arm PDFs (CMN S3AE TRM, CHI, BSA, GIC-600) and their markdown conversions of 2026-06-14, the reference material of the Asimov CMN work.",
  "Nothing. The handoff says the Drive upload was left to you and was not confirmed.",
  "All 28 markdown files and the PDFs.",
  "Keep until the Drive upload is confirmed, or archive the md folder (about 10 MiB)."),
"Intel_vs_AMD":("The May 2026 Intel-vs-AMD memory tests (bandwidth, latency, core-to-core).",
  "The 16 tool sources and the 8 first-round csv logs, by content (intel-snc pre-work and data/).",
  "43 later-round csv files and logs.",
  "Your decision; the write-up in the notebook already carries the conclusions."),
"p43":("The July 13 to 21 loadgen and boost tests: talos harness virtual environment, blocks/ results and scripts.",
  "4 of the 5 scripts (p43_rinzler_boost.sh and others, delphi-flat-freq test-scripts).",
  "blocks/ (45 result files) and loadgen.pre-capture-window.py.",
  "Archive blocks/ (small) if the boost numbers are still cited; the venv is rebuildable."),
"analysis":("The 2026-08-02 gate1 analysis run: a 12,000-file Python virtual environment plus a few outputs.",
  "Nothing.",
  "The small outputs under gate1-20260802T035923Z-67c87aca and g15-orch-verify.",
  "Delete the virtual environment; archive the outputs if wanted (under 10 MiB)."),
"tron-src":("A clean git mirror of tron main (commit f69f04b).","Nothing needed.","Nothing unique.","Delete."),
"systest-b2":("A clean clone of systems_test on branch jhan/seed-offset-long-prompts (commit 660dc14), pushed to GitHub.","Nothing needed.","Nothing unique.","Delete."),
"codex-home-andoria-11":("A June 2026 Codex home directory (8 session files, config).","Nothing.","The session transcripts.","Your decision; small."),
}
def kit_desc(name):
    return ("Campaign kit of the July 16 to Aug 2 decode-variance work: orchestrator scripts, results, logs and traces.",
            "Only ab22 and ab23 scripts (4 kit scripts by content). The narrative of every kit is in the flat_freq_tests README mirror.",
            "The other kit scripts (109 files) and the results.",
            "Delete the traces. Archive the kit scripts (under 2 MiB together) before deleting the rest.")
kv_sizes=sorted(scratch[r][0] for r in scratch if r.startswith("perf-fluctuation/") and r.endswith("kvwait.bin"))
kv_med=kv_sizes[len(kv_sizes)//2]
for k,v in list(DESC.items()):
    DESC[k]=tuple(x.replace("KVMED", f"{kv_med/MiB:.0f}") for x in v)
# ---- unique small sets not archived ----
def setsize(pred): 
    fs=[r for r in scratch if pred(r)]; return len(fs), sum(scratch[r][0] for r in fs)
UNIQUE=[
 ("flat_freq_tests/from-claude/", "41 investigation documents, analysis scripts and data of July 26 to 30", setsize(lambda r: r.startswith("flat_freq_tests/from-claude/") and r not in archived)),
 ("workspace/story2814/.../notes and PR2906", "comparison notes, patches and metrics of the June PR 2906 perf test", setsize(lambda r: r.startswith("workspace/story2814/") and ("/notes/" in r or "/PR2906/" in r) and r not in archived)),
 ("ab22 to ab62 kit scripts", "orchestrator, client and wrapper scripts at the top of each kit", setsize(lambda r: re.match(r"ab\d+b?/[^/]+\.(sh|py|md|txt)$", r) and r not in archived)),
 ("top-level scripts", "orchestrator3af6.sh, orchestratorE.sh, gatec61.sh, chain60.sh, dut_idle_check.sh, ab62_rounds.sh", setsize(lambda r: "/" not in r and r.endswith((".sh",".py")) and r not in archived)),
 ("ef720667-inv/", "PLAN.md, PHASE3_HANDOFF.md and the run csv files of the ef720667 regression investigation", setsize(lambda r: r.startswith("ef720667-inv/") and r not in archived)),
 ("from-claude-mining/", "gpt-oss history mining scripts and outputs", setsize(lambda r: r.startswith("from-claude-mining/") and r not in archived)),
 ("f3kit/", "the F3 instrumentation kit (capture scripts, dramprobe.c, KIT-INSTRUMENTATION.md)", setsize(lambda r: r.startswith("f3kit/") and r not in archived)),
 ("tron-perfetto-*-tools-*/", "v1, v2 and expanded campaign and report scripts (v3 is archived)", setsize(lambda r: r.startswith("tron-perfetto-") and "tools" in r.split("/")[0] and r not in archived)),
 ("sysconfig_snapshots/", "12 machine-state snapshots of 2026-08-01 (3 are archived)", setsize(lambda r: r.startswith("sysconfig_snapshots/") and r not in archived)),
 ("p43/blocks/", "boost-test block summaries", setsize(lambda r: r.startswith("p43/blocks/") and r not in archived)),
 ("pdjn/mine1 to mine7", "trace-mining outputs of the PDJN track", setsize(lambda r: re.match(r"pdjn/mine\d", r) and r not in archived)),
 ("pdjn-3c51/", "delphi-3c51 machine snapshot files (lscpu, lspci, meminfo, ...)", setsize(lambda r: r.startswith("pdjn-3c51/") and r not in archived)),
 ("documents/ARM/md/", "28 markdown conversions of the Arm documents", setsize(lambda r: r.startswith("documents/ARM/md/") and r not in archived)),
 ("Intel_vs_AMD csv logs", "later-round measurement csv and log files", setsize(lambda r: r.startswith("Intel_vs_AMD/") and r.endswith((".csv",".log",".txt")) and r not in archived)),
 ("simlot/ and legacy-adjudicated/", "sim-lottery and legacy adjudication results (July 30 to Aug 2)", setsize(lambda r: r.startswith(("simlot/","legacy-adjudicated/")) and r not in archived)),
]
# ---- numbers for prose ----
by=TOT["by"]; byn=TOT["byn"]
pf_b=by["pftrace"]; regen_b=by["regen"]; raw_b=by["raw"]; pers_b=by["personal"]
kv_rel=[r for r in scratch if r.startswith("perf-fluctuation/") and r.endswith("kvwait.bin")]
ondisk={}
for l in open(f"{SP}/3bda-ondisk.tsv", encoding="utf-8", errors="replace"):
    p=l.rstrip("\n").split("\t",1)
    if len(p)==2: ondisk[p[1][len("/scratch/jhan/"):]]=int(p[0])*1024
kv_b=sum(ondisk.get(r,0) for r in kv_rel); kv_ap=sum(scratch[r][0] for r in kv_rel)
regen_entries=["pr3244","workspace","tron-pr3070","pdjn-wt","tron-src","systest-b2","symbols","frozen","tron-perfetto-install-20260809","tron-perfetto-vanilla-install-20260806"]
freed_now=pf_b+regen_b
remaining=TOT["ondisk"]-freed_now
mean_n=len(meaningful); mean_b=sum(scratch[p][0] for p in meaningful)
explicit_n=536
# ---- HTML ----
def row_html(t):
    v=E[t]; d=DESC.get(t) or (kit_desc(t) if re.match(r"ab\d+b?$",t) or t=="ab62rounds" else None)
    arch=v["archived_n"]; 
    archm=sum(1 for p in meaningful if (p.split('/',1)[0] if '/' in p else '(top-level files)')==t)
    cells=[esc(t), g2(v["ondisk"]), g2(v["by"]["pftrace"]), g2(v["ondisk"]-v["by"]["pftrace"]), f"{v['files']:,}", v["newest"], f"{archm:,}"]
    what=d[0] if d else ""; holds=d[1] if d else ""; missing=d[2] if d else ""; act=d[3] if d else ""
    return f"<tr><td class='mono'>{cells[0]}</td><td class='num'>{cells[1]}</td><td class='num'>{cells[2]}</td><td class='num'>{cells[3]}</td><td class='num'>{cells[4]}</td><td class='num'>{cells[5]}</td><td class='num'>{cells[6]}</td><td>{esc(what)}</td><td>{esc(holds)}</td><td>{esc(missing)}</td><td>{esc(act)}</td></tr>"
big=[t for t in names if E[t]["ondisk"]>=100*MiB]
table_rows="\n".join(row_html(t) for t in big)
small_total=sum(E[t]["ondisk"] for t in names if E[t]["ondisk"]<100*MiB); small_n=len(names)-len(big)
uniq_rows="\n".join(f"<tr><td class='mono'>{esc(a)}</td><td>{esc(b)}</td><td class='num'>{n:,}</td><td class='num'>{mi(s)}</td></tr>" for a,b,(n,s) in UNIQUE)
uniq_n=sum(n for _,_,(n,s) in UNIQUE); uniq_b=sum(s for _,_,(n,s) in UNIQUE)
chart_json=json.dumps(chart_rows)
regen_now=["pr3244","tron-pr3070","pdjn-wt","tron-src","systest-b2"]
regen_now_b=sum(E[t]["ondisk"] for t in regen_now)
installs_b=sum(E[t]["ondisk"] for t in ["symbols","frozen","tron-perfetto-install-20260809","tron-perfetto-vanilla-install-20260806"])+E["perf-fluctuation"]["by"]["regen"]+E["pdjn"]["by"]["regen"]
freed_step1=pf_b+regen_now_b+installs_b
camp_left=sum(gr["ondisk"]-gr["by"]["pftrace"] for gr in groups if gr["label"].startswith(("ab22","tron-perfetto-* capture","gate campaign")))
reply=f"""Hi Mitchell, thanks for the numbers. Here is the plan for /scratch/jhan.

Delete now ({g(freed_step1)} GiB of the {g(TOT['ondisk'])} GiB):
- every .pftrace file: {g(pf_b)} GiB on disk.
- pr3244, tron-pr3070, pdjn-wt, tron-src and systest-b2: tron checkouts and build trees, {g(regen_now_b)} GiB. They can be rebuilt from git.
- the runtron install copies (symbols, frozen, tron-perfetto-*install*, and the install-* folders under perf-fluctuation and pdjn): {g(installs_b)} GiB.

Delete after I copy a few small files out; I will tell you when, within [N days]:
- workspace/story2814: {g(E['workspace']['ondisk'])} GiB, mostly build trees. I need its notes folders first (under 1 MiB).
- the ab*, g2*, gate15, ring20 and tron-perfetto-* campaign folders: about {g(camp_left)} GiB once their traces are gone. I need their scripts first.

Keep for now; I will decide on them by [date]:
- perf-fluctuation/deep-dive kvwait.bin dumps ({g(kv_b)} GiB): raw timing data that was never fully mined.
- flat_freq_tests ({g(E['flat_freq_tests']['ondisk'])} GiB), t1-goldens ({g(E['t1-goldens']['ondisk'])} GiB), documents ({mi(E['documents']['ondisk'])} MiB), claude-dev-migrate ({g(E['claude-dev-migrate']['ondisk'])} GiB) and laptop-bkup ({g(E['laptop-bkup']['ondisk'])} GiB).

Jibin"""
page=f"""<title>/scratch/jhan prune review</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column for prose (68ch), full width for the chart and tables; light theme only (user rule). */
:root {{
  --bg:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7; --ring:rgba(11,11,11,0.10);
  --accent:#2a78d6; --c-pftrace:#bdbbb3; --c-regen:#2a78d6; --c-raw:#eb6834; --c-personal:#1baf7a;
  --font-text:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; --font-mono:"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  color-scheme: light;
}}
html,body{{background:var(--bg);color:var(--ink);font-family:var(--font-text);line-height:1.5;font-size:15px}}
body{{margin:0;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
.wrap{{max-width:1180px;margin:0 auto}}
.prose{{max-width:68ch}}
h1{{font-size:1.9rem;font-weight:600;line-height:1.2;margin:0 0 6px;text-wrap:balance;letter-spacing:-0.01em}}
h2{{font-size:1.25rem;font-weight:600;margin:40px 0 10px;text-wrap:balance}}
h3{{font-size:1rem;font-weight:600;margin:22px 0 6px}}
p{{margin:0 0 12px}}
.eyebrow{{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
.meta{{color:var(--ink-2);font-size:.9rem;margin-bottom:22px}}
.short{{border-left:3px solid var(--accent);padding:4px 0 4px 16px;margin:18px 0 26px}}
.short p{{margin:0 0 6px}}
code,.mono{{font-family:var(--font-mono);font-size:.86em}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0 8px}}
.tile{{background:var(--surface);border:1px solid var(--ring);border-radius:6px;padding:12px 14px;min-width:0}}
.tile .l{{font-size:.8rem;color:var(--ink-2)}}
.tile .v{{font-size:1.9rem;font-weight:600;line-height:1.15;margin-top:4px}}
.tile .v small{{font-size:.95rem;font-weight:500;color:var(--ink-2);margin-left:3px}}
.tile .s{{font-size:.8rem;color:var(--muted);margin-top:4px}}
.chart-card{{background:var(--surface);border:1px solid var(--ring);border-radius:6px;padding:16px 16px 10px;margin:14px 0 6px;min-width:0}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.84rem;color:var(--ink-2);margin:0 0 10px}}
.legend span{{display:inline-flex;align-items:center;gap:7px}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px}}
.chart-scroll{{overflow-x:auto}}
svg text{{font-family:var(--font-text)}}
.tip{{position:fixed;pointer-events:none;background:var(--ink);color:#fff;font-size:.8rem;padding:6px 9px;border-radius:4px;max-width:320px;line-height:1.35;z-index:20}}
.caption{{font-size:.84rem;color:var(--ink-2);margin:6px 0 0}}
.tscroll{{overflow-x:auto;margin:10px 0 4px}}
table{{border-collapse:collapse;font-size:.84rem;background:var(--surface);min-width:900px}}
th,td{{border-top:1px solid var(--grid);padding:7px 9px;text-align:left;vertical-align:top}}
th{{font-weight:600;color:var(--ink-2);background:#f3f2ee;position:sticky;top:0}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
tr:hover td{{background:#f6f5f1}}
.wide td:nth-child(n+8){{min-width:220px}}
ul{{padding-left:1.2em;margin:0 0 12px}}
li{{margin-bottom:5px}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:5px 14px;margin:0 0 12px;max-width:80ch}}
dt{{font-family:var(--font-mono);font-size:.84em;color:var(--ink);padding-top:2px}}
dd{{margin:0}}
pre.reply{{background:var(--surface);border:1px solid var(--ring);border-radius:6px;padding:14px 16px;white-space:pre-wrap;font-family:var(--font-text);font-size:.92rem;line-height:1.5;max-width:76ch}}
button{{font:inherit;font-size:.85rem;padding:6px 12px;border:1px solid var(--axis);background:var(--surface);border-radius:4px;cursor:pointer;color:var(--ink)}}
button:hover{{background:#f3f2ee}} button:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.note{{font-size:.84rem;color:var(--ink-2)}}
@media (max-width:640px){{ h1{{font-size:1.5rem}} dl{{grid-template-columns:1fr}} }}
@media (prefers-reduced-motion:reduce){{ *{{transition:none!important}} }}
</style>
<div class="wrap">
<div class="eyebrow">delphi-3bda · filer share /scratch · measured 2026-10-21 03:58 to 05:10 UTC</div>
<h1>/scratch/jhan prune review</h1>
<div class="meta">What the 268 GiB holds, what the notebook repo already archives, and what can go. Prepared for the reply to Mitchell's message of 2026-10-20.</div>

<div class="short prose">
<p><strong>Short version.</strong> The .pftrace files are {g(pf_b)} GiB on disk and can go, as you said. Another {g(regen_b)} GiB are tron checkouts, build trees, toolchains and runtron binaries that git can rebuild. The notebook holds {explicit_n} explicitly mirrored files (all byte-identical to the live copies) plus about {mean_n-explicit_n} further files by content, but none of the raw campaign data ({g(raw_b)} GiB) and none of the {uniq_n:,} small documents and scripts listed below.</p>
</div>

<div class="tiles">
 <div class="tile"><div class="l">On disk now</div><div class="v">{g(TOT['ondisk'])}<small>GiB</small></div><div class="s">{TOT['files']:,} files, 130 top-level entries, newest change 2026-08-28</div></div>
 <div class="tile"><div class="l">.pftrace (delete, your decision)</div><div class="v">{g(pf_b)}<small>GiB</small></div><div class="s">{byn['pftrace']} trace files; Mitchell counted 130 GiB</div></div>
 <div class="tile"><div class="l">Rebuildable from git</div><div class="v">{g(regen_b)}<small>GiB</small></div><div class="s">checkouts, build trees, toolchains, runtron installs</div></div>
 <div class="tile"><div class="l">Raw campaign data, not in the notebook</div><div class="v">{g(raw_b)}<small>GiB</small></div><div class="s">of which kvwait.bin dumps {g(kv_b)} GiB</div></div>
 <div class="tile"><div class="l">Personal backup and migration staging</div><div class="v">{g(pers_b)}<small>GiB</small></div><div class="s">laptop-bkup, claude-dev-migrate, old codex home</div></div>
</div>
<p class="note">Sizes are on-disk sizes as the filer reports them (what <code>du</code> prints and what deleting frees). The same files hold {g(TOT['apparent'])} GiB of content; the filer stores them smaller. Hypothesis: the filer compresses transparently. The measurement that would confirm it is <code>zfs get compression</code> on filer.positron.internal.</p>

<h2>Where the space is, by top-level entry</h2>
<div class="chart-card">
 <div class="legend"><span><i style="background:var(--c-pftrace)"></i>.pftrace (delete)</span><span><i style="background:var(--c-regen)"></i>rebuildable from git</span><span><i style="background:var(--c-raw)"></i>raw campaign data and documents, not in the notebook</span><span><i style="background:var(--c-personal)"></i>personal backup and migration staging</span></div>
 <div class="chart-scroll"><svg id="chart" role="img" aria-label="Stacked horizontal bars of on-disk GiB per directory group, split by class"></svg></div>
 <p class="caption">Bars are to scale in GiB on disk. Each row is one top-level entry, or a family of entries from one campaign. The value at the bar tip is the row total. Hover a segment for its size. The table below carries every number.</p>
</div>

<div class="prose">
<p>Reading the chart: after the gray and blue segments are deleted, {g(remaining)} GiB remain. The orange part of perf-fluctuation is the only large raw set, and it is almost entirely kvwait.bin ({len(kv_rel)} files, {g(kv_ap)} GiB of content stored as {g(kv_b)} GiB). Everything else that is not archived is small.</p>
</div>

<h2>Entry by entry</h2>
<p class="note">All entries of 100 MiB or more on disk, largest first. "Archived files" counts files of 256 bytes or more whose content is byte-identical to a file in the notebook (md5 on both sides). The remaining {small_n} entries hold {mi(small_total)} MiB together.</p>
<div class="tscroll"><table class="wide">
<thead><tr><th>Entry</th><th class="num">On disk GiB</th><th class="num">.pftrace GiB</th><th class="num">Other GiB</th><th class="num">Files</th><th class="num">Newest</th><th class="num">Archived files</th><th>What it is</th><th>What the notebook holds</th><th>What is not archived</th><th>Suggested action</th></tr></thead>
<tbody>
{table_rows}
</tbody></table></div>

<h2>Small sets that exist only here</h2>
<div class="prose"><p>These are documents and scripts that a handoff or README in the notebook refers to, but that have no copy in the notebook. Together they are {uniq_n:,} files and {mi(uniq_b)} MiB of content. Preserving them is a few minutes of work and costs no disk space worth counting. Delete the folders around them only after that.</p></div>
<div class="tscroll"><table>
<thead><tr><th>Location under /scratch/jhan</th><th>What it is</th><th class="num">Files</th><th class="num">MiB</th></tr></thead>
<tbody>
{uniq_rows}
</tbody></table></div>

<h2>What the notebook already archives</h2>
<div class="prose">
<ul>
<li><strong>{explicit_n} explicit mirrors.</strong> Files that a README, lineage table or handoff sidecar records with a canonical path under /scratch/jhan. All {explicit_n} are byte-identical to the live files (md5 compared on 2026-10-21). They live under artifacts/tron-perf-fluctuation/3bda-scratch and alpha-scratch, artifacts/delphi-flat-freq and artifacts/intel-snc.</li>
<li><strong>{mean_n-explicit_n} further files by content.</strong> A hash of every small document-like file on /scratch/jhan ({len(checked):,} files, build trees and virtual environments excluded) found these with an identical copy in the notebook under another path: the intel-amd tool sources and first-round csv logs, harness.sh and report-v3.py copies, and metrics.json duplicates. Another {trivial_n:,} matches are one-line status files (placement-count.txt, exit codes) and do not count as archives.</li>
<li><strong>The pdjn-wt worktree diff.</strong> worktree-snapshots/pdjn-wt-tracked-12804a812.diff equals the live <code>git diff</code> (13,000 bytes, same md5).</li>
<li><strong>The narrative.</strong> flat_freq_tests/README.md (157 KB, identical) and the handoffs describe every campaign, so the result trees are documented even where their files are not copied.</li>
</ul>
<p>Not archived anywhere in the notebook: all .pftrace files, all kvwait.bin, perf.script, perf.data and vtune files, the result trees of the ab, g2 and gate campaigns, the from-claude documents of flat_freq_tests, and the personal backup.</p>
</div>

<h2>Draft reply to Mitchell</h2>
<div class="prose"><p>Numbers below are from this measurement. The bracketed date is for you to fill in.</p></div>
<pre class="reply" id="reply">{esc(reply)}</pre>
<p><button type="button" id="copybtn">Copy the reply</button> <span class="note" id="copymsg"></span></p>

<h2>How this was measured</h2>
<div class="prose">
<ul>
<li>On delphi-3bda, 2026-10-21 03:58 to 05:10 UTC. The CI lease was busy the whole time (nightly run 39539984172), so only read-only listing commands ran, at low priority. No file was changed or deleted.</li>
<li>File list: <code>find /scratch/jhan -type f</code> with content size, on-disk size, modification date and path ({TOT['files']:,} files). Directory totals: <code>du -sk</code> per top-level entry; the sum agrees with Mitchell's 270 GiB.</li>
<li>Archive check: md5 of {len(checked):,} files on delphi-3bda compared with the md5 of all 8,684 files in the notebook checkout at commit 75273c3. The explicit mirror list came from the READMEs, the .lineage.md tables and the codex handoff sidecars in logs/.</li>
<li>Git state: pr3244/head, pr3244/base, tron-src and systest-b2 are clean checkouts; pdjn-wt has 3 modified files (archived diff) and 5 untracked build logs.</li>
<li>Classes: a file is ".pftrace" by extension; "rebuildable" when it sits in a git checkout, build tree, toolchain, virtual environment or an install-* folder; "personal" under laptop-bkup, claude-dev-migrate, codex-home-andoria-11 and tmp; everything else is "raw campaign data and documents".</li>
</ul>
</div>

<h2>Words used here</h2>
<dl>
<dt>/scratch</dt><dd>An NFS share from filer.positron.internal (23 TB, 87 % used). The same files are visible from delphi-3bda and the other hosts that mount it.</dd>
<dt>.pftrace</dt><dd>A Perfetto trace file: a recording of scheduler and application events captured during one benchmark draw. Large, and only useful while the draw is under analysis.</dd>
<dt>kvwait.bin</dt><dd>A binary dump of per-matmul timing stamps written by the instrumented runtron during the August deep-dive campaigns, one file per draw.</dd>
<dt>notebook</dt><dd>The git repository ~/workspace/notebook (jhan-positron/notebook on GitHub) that holds handoffs and mirrored artifacts.</dd>
<dt>mirror, canonical</dt><dd>A mirror is a copy in the notebook. The canonical file is the original on the machine where the work ran.</dd>
<dt>on-disk size</dt><dd>The space the filer reports for a file (du). Content size is the number of bytes in the file; here it is larger than the on-disk size.</dd>
<dt>tron, runtron</dt><dd>tron is the inference program under test. runtron is its command-line tool. A build of it is about 400 MiB.</dd>
<dt>worktree, checkout</dt><dd>A copy of the tron source at one git commit. A build tree is the compiler output next to it.</dd>
<dt>PR 3244, PR 3070, PR 2906</dt><dd>Pull requests of positron-ai/tron that the July and June tests compared against their base commits.</dd>
<dt>CI lease</dt><dd>The file the nightly System CI writes on delphi-3bda while it owns the machine. Only light work is allowed while it exists.</dd>
<dt>PDJN, deep-dive, pfgate, 5cat, ab kits, g2 and gate campaigns</dt><dd>Names of the July and August decode-performance investigation rounds. Each has a handoff in the notebook.</dd>
</dl>
</div>
<script>
(function(){{
const rows={chart_json};
const classes=[["pftrace","--c-pftrace",".pftrace (delete)"],["regen","--c-regen","rebuildable from git"],["raw","--c-raw","raw campaign data and documents, not in the notebook"],["personal","--c-personal","personal backup and migration staging"]];
const GiB=1024*1024*1024;
const css=getComputedStyle(document.documentElement);
const col=v=>css.getPropertyValue(v).trim();
const svg=document.getElementById("chart");
const W=Math.max(700, Math.min(1120, (svg.parentNode.clientWidth||1120)));
const labelW=Math.min(330, Math.max(220, W*0.3)), left=labelW+8, right=70, top=14, rowH=32, barH=18;
const maxV=Math.max(...rows.map(r=>r.total))/GiB;
const niceMax=Math.ceil(maxV/10)*10;
const plotW=W-left-right;
const x=v=>left+(v/GiB)/niceMax*plotW;
const H=top+rows.length*rowH+30;
svg.setAttribute("viewBox",`0 0 ${{W}} ${{H}}`); svg.setAttribute("width",W); svg.setAttribute("height",H);
const ns="http://www.w3.org/2000/svg";
function el(n,a,txt){{const e=document.createElementNS(ns,n);for(const k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e;}}
// gridlines + ticks
const step=niceMax>=80?20:10;
for(let v=0;v<=niceMax;v+=step){{
  const gx=x(v*GiB);
  svg.appendChild(el("line",{{x1:gx,x2:gx,y1:top-4,y2:top+rows.length*rowH,stroke:col("--grid"),"stroke-width":1}}));
  svg.appendChild(el("text",{{x:gx,y:top+rows.length*rowH+18,"text-anchor":"middle","font-size":11,fill:col("--muted")}},v+(v===niceMax?" GiB":"")));
}}
svg.appendChild(el("line",{{x1:left,x2:left,y1:top-4,y2:top+rows.length*rowH,stroke:col("--axis"),"stroke-width":1}}));
const tip=document.createElement("div"); tip.className="tip"; tip.hidden=true; document.body.appendChild(tip);
rows.forEach((r,i)=>{{
  const y=top+i*rowH+(rowH-barH)/2;
  const t=el("text",{{x:left-10,y:y+barH/2+4,"text-anchor":"end","font-size":12,fill:col("--ink")}},r.label.length>44?r.label.slice(0,43)+"…":r.label);
  svg.appendChild(t);
  let cx=left; const segs=classes.filter(c=>r.seg[c[0]]>0);
  segs.forEach((c,j)=>{{
    const w=Math.max(0,x(r.seg[c[0]])-left); const last=j===segs.length-1;
    const gap=last?0:2; const ww=Math.max(0,w-gap);
    if(ww<=0) return;
    let d;
    if(last && ww>=4){{ const rr=4; d=`M${{cx}},${{y}} h${{ww-rr}} a${{rr}},${{rr}} 0 0 1 ${{rr}},${{rr}} v${{barH-2*rr}} a${{rr}},${{rr}} 0 0 1 -${{rr}},${{rr}} h-${{ww-rr}} z`; }}
    else {{ d=`M${{cx}},${{y}} h${{ww}} v${{barH}} h-${{ww}} z`; }}
    const p=el("path",{{d:d,fill:col(c[1])}});
    p.addEventListener("mousemove",ev=>{{tip.hidden=false;tip.textContent=`${{r.label}} · ${{c[2]}}: ${{(r.seg[c[0]]/GiB).toFixed(2)}} GiB on disk (row total ${{(r.total/GiB).toFixed(2)}} GiB)`;tip.style.left=(ev.clientX+12)+"px";tip.style.top=(ev.clientY+12)+"px";}});
    p.addEventListener("mouseleave",()=>{{tip.hidden=true;}});
    svg.appendChild(p);
    cx+=w;
  }});
  svg.appendChild(el("text",{{x:x(r.total)+8,y:y+barH/2+4,"font-size":12,fill:col("--ink-2"),"font-variant-numeric":"tabular-nums"}},(r.total/GiB).toFixed(1)));
}});
const btn=document.getElementById("copybtn"), msg=document.getElementById("copymsg"), pre=document.getElementById("reply");
btn.addEventListener("click",()=>{{
  const txt=pre.textContent;
  const sel=()=>{{const rg=document.createRange();rg.selectNodeContents(pre);const s=window.getSelection();s.removeAllRanges();s.addRange(rg);msg.textContent="Text selected. Press Ctrl+C (or Cmd+C) to copy.";}};
  if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(txt).then(()=>{{msg.textContent="Copied.";}}).catch(sel);}} else sel();
}});
}})();
</script>
"""
os.makedirs(OUTDIR, exist_ok=True)
open(f"{OUTDIR}/page.html","w").write(page)
standalone='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n'+page+'\n</head></html>' # placeholder, fixed below
# proper standalone: head gets title/meta/style, body gets the rest
head_end=page.index("</style>")+len("</style>")
standalone='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n'+page[:head_end]+'\n</head><body>\n'+page[head_end:]+'\n</body></html>\n'
open(f"{OUTDIR}/scratch-jhan-prune-review.html","w").write(standalone)
open(f"{OUTDIR}/reply-to-mitchell.txt","w").write(reply+"\n")
json.dump({"chart_rows":chart_rows,"unique":[(a,b,n,s) for a,b,(n,s) in UNIQUE],"totals":{"ondisk":TOT["ondisk"],"apparent":TOT["apparent"],"pftrace":pf_b,"regen":regen_b,"raw":raw_b,"personal":pers_b,"kvwait":kv_b,"archived_meaningful":mean_n,"archived_trivial":trivial_n,"checked":len(checked)}}, open(f"{OUTDIR}/figures.json","w"), indent=1)
print("page written:", f"{OUTDIR}/scratch-jhan-prune-review.html", len(standalone), "bytes")
print(f"freed_now={g(freed_now)} remaining={g(remaining)} kv={g(kv_b)} unique={uniq_n} files {mi(uniq_b)} MiB; meaningful archived={mean_n} (explicit {explicit_n}), trivial={trivial_n}")
