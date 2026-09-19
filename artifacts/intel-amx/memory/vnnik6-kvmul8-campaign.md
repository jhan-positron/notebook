---
name: vnnik6-kvmul8-campaign
description: "2026-09-16 campaign for PR #4424 open item \"128-dimension heads with kv_mul other than 4\" (qwen-3-30b-a3b, kv_mul 8): plan, arms base/headoff/vnni, scripts exec/vnnik6-20260916/, report status/Wednesday-morning-report.html, status and traps"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9c1401f8-018d-4a39-9ba0-0f637d87af4c
  modified: 2026-09-16T05:57:48.335Z
---

Request (jhan, 2026-09-15 22:3x PDT = 2026-09-16 05:3x UTC): form an action plan for the PR #4424 open
item (qwen-3-30b-a3b, kv_mul 8: one run showed -5.4% decode TPS / -369 ms TTFT with the VNNI layout),
execute it after the CI window, report to VNNIed-K-in-place/status/Wednesday-morning-report.html.

Plan (exec/vnnik6-20260916/PLAN.md, pre-registered decision rule in section 6):
- Arms: base = runtron.main0916 (main c7844ca2ce = merge base of the PR, TRON_AMX_DISPATCH=ON, row-major K);
  headoff = runtron.headoff0916 (PR head ff680c8020 built with TRON_K_VNNI off = what a kv_mul gate would run
  for this model); vnni = runtron.vnnik5 (65a1c41d72 = PR head code; TRON_K_VNNI=ON). No AMX-off arms
  (AMX kernel not eligible for kv_mul 8; kill switch changes nothing).
- Cells (our half, 8 users, 256 tokens, USE_HW_ATTN=0): smoke base/base2/headoff/vnni/vnni2; tp2 prompt 1024
  x6; tp4 1024 x4; traces (every arm, tp2+tp4, 32 tokens, passes 1-24); tp2 2048 x3; tp2 8192 x3; tp4 8192 x2.
  Arms interleave inside each repetition. A tp2 prompt-1024 run of this model takes ~40 s (25 s load).
- Attribution logic: reader cost = per page (grows with prompt length); store cost = per token (flat);
  traces give Save K per layer + attention ms per worker per decode step (analyze.py adds worker metrics).
- Loss confirmed when paired t(vnni - base, tp2 prompt 1024) < -2 with 6 reps; headoff == base when |t| < 2.

Scripts: exec/vnnik6-20260916/{build.sh (generic: commit worktree suffix + cmake -D flags; waits for the
lease unless SKIP_LEASE_WAIT=1), chain.sh (lease wait -> build base -> build headoff -> campaign.sh),
campaign.sh (fork of vnnik2's; VNNIK6_FUNCTIONS_ONLY=1 for sourcing), trace.sh, analyze.py [DIR N_KV_HEADS],
summarize.py (paired deltas + t), compare_tokens.py, gen_report.py (reads summary.json, analysis.json,
smoke.txt, build-*.txt and the hand-written fragments sections/{remedies,recommendation,notes}.html;
pure-ASCII assert; VNNIK6_RES/VNNIK6_TRES env for dry runs), launch.sh (setsid nohup chain.sh on 3bda)}.
Results: exec/results/vnnik6-20260916/, exec/results/vnnik6-trace-20260916/; logs exec/logs/vnnik6-*.
Dry runs on synthetic data (scratchpad dry6/) passed; analyze.py reproduces the 2026-09-14 numbers on the
old qwen3-4b trace (Save K 273.6 us/layer).

Model facts: ingested-qwen-3-30b-a3b-instruct-2507-tp2/-tp4 exist in the binaries; generated plugin
qwen_3_30b_moe.hpp: n_layers 48, n_kv_heads 4, head_size 128, attention_geometry{32, kv_geometry{4,128}},
cache_t = uniform_kv_cache<48, kv_geometry{4,128}, ...> (the cache type knows head_size and n_kv_heads,
NOT n_query_heads/kv_mul -> a kv_mul gate needs plumbing; the code-analysis workflow wf_0818cf73-833 lists
the 27 layout_on sites and the options).

Machine at planning time (05:31 UTC): nightly CI run 35052594106 started 03:39 UTC (lease busy, load 127,
rinzler@0-3 up); expected clear 11:30-13:20 UTC; Bill's marker /bill-has-instance-0,2 present (our half
only); runtron.vnnik5 sha256 7f508484... (--version prints 65a1c41d because libversion.so was relinked;
runtron file identical to the d5b59b1101 build).

STATUS 2026-09-16 06:19 UTC: chain.sh LAUNCHED on 3bda (pid 2092029, exec/logs/vnnik6-chain.log says "CI lease busy; chain waits";
nightly run 35052594106 lease busy since 03:39 UTC). Script review (wf_1c950ab1-e03, 68 agents) -> 9 distinct fixes applied
before launch: GUARD_TAKEOVER_LAST exported to the trace.sh child; chain.sh writes fallback build markers, re-checks the lease
before the 2nd build, drops a failed arm (base+vnni or headoff+vnni) instead of killing the campaign; 3-consecutive-failure cap
(rt wrapper); watcher around the trace phase; smoke timeout = failure (no retry); instance flock /var/tmp/jhan/<NAME>.instance.lock
(replaces the pgrep self-match check); summarize.py excludes early-stop TPS (keeps TTFT) and dedupes repeated records;
trace.sh TTFT field via sed; build.sh asserts TRON_K_VNNI cache value (EXPECT_K_VNNI). Pre-review copies: campaign.sh.pre-review,
chain.sh.pre-review. Code analysis (wf_0818cf73-833, 15 agents) written into sections/remedies.html (gate needs kv_mul plumbed
into the cache type: options B kv_geometry field / D kv_layout template arg; reader counts identical VDPBF16PS vs dotter at kv_mul 8;
decode store est. 2.1-2.5 points of the step). sections/notes.html drafted; sections/recommendation.html pending the data.
NEVER edit chain.sh/build.sh/campaign.sh/trace.sh while the chain runs (bash byte-offset re-read).

SECOND REVIEW (wf_1a08b195-f6e, 47 agents, after launch; chain.sh running, campaign.sh/trace.sh/build.sh not yet started so
edited safely): rt cap ends only the current phase (|| break 2 + consec=0 per phase), primary cell still ends the campaign;
rc 137 no longer classified as a lease stop (timeout -k kill); fd-close groups use `[ -z ] ||` so they never gate the launch;
trace.sh writes $RES/takeover.last, campaign reads it back; compare_tokens knows headoff2; gen_report: REF arm = headoff when
the base build failed, all-early-stop guard, paired-n wording; 36 plain-English fixes applied to sections/remedies.html +
notes.html; Words table gained KV page, slot, bf16, AVX-512/gather/scatter, TRON_AMX_DISPATCH/TRON_K_VNNI, minibatch/main
helpers, worktree/sha256/libversion.so, the nightly.

RESULTS SO FAR (2026-09-16, lease cleared 13:18 UTC; builds base 674 s / headoff 703 s ok; takeover stopped the nightly's idle
rinzler@0/1 at 13:42; campaign started 13:42, 0 failed runs, Bill idle, load 12-16):
- smoke: base==base2, vnni==vnni2, base==headoff (128/128); base vs vnni diverge at token 5 (as on 09-15).
- tp2 prompt 1024 (6 reps): base 34.26 sd 0.66 / headoff 34.44 sd 0.75 / vnni 34.79 sd 0.86 TPS; vnni-base +0.53 (t +1.3, NOT resolved);
  TTFT 5.262 / 5.241 / 4.833 s -> -428 ms (t -35.9). The one-run -5.4% did NOT repeat. The 09-15 base (544ca05c7a) was 36.28 vs
  main c7844ca2ce 34.26 today -> "base moved" question -> extra cell queued (extra-oldbase.sh: p0perf13 vs main0916 x6, after the campaign).
- tp4 prompt 1024 (4 reps): 49.99 / 50.45 / 51.07; vnni-base +1.08 (t +0.9); TTFT -227 ms (t -23).
- tp2 prompt 2048 (3 reps): base 23.43 / headoff 23.12 / vnni 22.47 -> vnni-base -0.97 TPS = -4.1% (t -5.3, RESOLVED loss); TTFT -1720 ms.
- traces tp2 (1024): decode pass 27.70 base / 28.31 vnni; Save K 0.154 -> 0.914 ms/step (+0.76 ms, 3.2 -> 19.0 us/layer, 100 -> 595 ns/row);
  attention per worker 6.84 -> 6.05 ms (-0.79: reader faster than dotter at 1024); helper kernels ~10 ms. prefill pass 652 -> 602 ms
  (-50 ms x 8 = -401 ms = the TTFT gain): Save K 158 -> 52 us/layer, attention/worker 294 -> 246 ms. tp4 similar (403.6 -> 375.2 prefill).
- extra2-trace8192.sh queued (traces base/vnni tp2 prompt 8192, passes 1-90) to attribute the 2048/8192 loss; runs after the old-base cell.
- analyze.py needs tp.close() (added) else trace_processor daemons stay behind; the container killed a background waiter for "low memory"
  (swap full) -> use Monitor 30-min re-arms; a Monitor command must not `cd` (the shell prints a directory listing = event spam).

FINAL CELLS (campaign done 15:44 UTC, 54 runs, 0 failed): tp2 8192 (3 reps) base 11.30 / headoff 11.12 / vnni 14.02 -> +24.1% (t +12.2),
TTFT -25.8 s (-15.8%); tp4 8192 (2 reps) 21.87 / 21.87 / 24.34 -> +11.3% (t +6.4), TTFT -13.7 s. headoff == base everywhere (|t| <= 1.4).
EXTRA old-base cell (6 reps, 15:44-15:55): p0perf13 (544ca05c7a) 34.96 sd 1.35 vs main0916 33.92 sd 0.69 -> main -1.04 TPS (t -1.6, not
resolved); the 09-15 base 36.28 was a high single sample (~1 sd above the old base mean).
TRACES tp2 (one run each; analysis.json in results/vnnik6-trace{,8192,2048}-20260916): decode pass base/vnni 1024: 27.70/28.31 ms,
2048: 42.62/44.88 (+2.26), 8192: 87.41/70.47 (-16.9); attention ms/worker 6.84/6.05, 13.22/12.25, 54.46/45.85 (reader faster at every
length, -12/-7/-16%); Save K ms/step 0.15/0.91, 0.18/0.96, 0.17/0.85 (+0.7-0.8 scatter store on the main thread); helper kernels ~10-13 ms.
Prefill pass: 652/602 (1024), 931/830 (2048), 2541/2145 (8192) -> x passes = the TTFT gains (-401 ms, -1.6 s, -25.3 s). The 2048 decode
loss (+2.3 ms/step) is NOT explained by the Save K (+0.78) + attention (-0.97) spans -> hypothesis: attention (13 ms) and expert kernels
(13 ms) balanced at that length, so the serial store lands on the critical path while the workers' gain does not; measurement = per-layer
lanes of one decode step (lanes.py). Plain-English check of the page: 85 confirmed findings (wf_e16a8284-a9e) applied by wf_0b402318-e6c.

REPORT DONE 2026-09-16 ~16:30 UTC: status/Wednesday-morning-report.html (136 KB, pure ASCII, 0 pending blocks; generator
exec/vnnik6-20260916/gen_report.py + sections/{remedies,notes,recommendation}.html; publish copy = scratchpad
Wednesday-morning-report.artifact.html, wrapper-stripped). ARTIFACT https://claude.ai/artifact/8CcWsAee7224M3qr3ibiVk (republish the same scratchpad path). 85 plain-English findings applied (wf_0b402318-e6c) + 8 residuals by hand.
Verdict: NO kv_mul gate. Decode: 1024 +1.5% (t +1.3), 2048 -4.1% (t -5.3, real, unexplained by spans -> lanes hypothesis),
8192 +24.1% tp2 / +11.3% tp4; TTFT -7..-16% everywhere; headoff == base everywhere. PR body open item to be rewritten by jhan
(draft text in the final chat message / report section 7). Extra worktrees on 3bda: tron-main0916, tron-headoff0916 (11 GB each).

**Why:** the PR item says "measure before merging"; one run cannot separate noise, reader cost and store
cost, and the gate remedy needs to be shown to restore main's numbers (headoff arm) before anyone codes it.
**How to apply:** after the chain finishes: python3 analyze.py <trace dir> 4 on claude-box (perfetto module
is there, not on 3bda), write sections/*.html from the workflow results, run gen_report.py, render the SVGs
with cairosvg and inspect, plain-English check, then update PR #4424's open item. Related:
[[vnnied-k-in-place-project]], [[pr4424-description-on-github]], [[3bda-nightly-rinzler-cleanup]],
[[3bda-shared-with-bill]], [[runtron-determinism-recipe]].
