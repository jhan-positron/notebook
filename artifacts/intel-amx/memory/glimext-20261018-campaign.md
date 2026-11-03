---
name: glimext-20261018-campaign
description: "2026-10-18 extended test of PR #5015 (kv_mul-16 AMX kernels) with and without the change: scripts exec/glimext-20261018/ (build base g16b = main 6198824246 + head g16h = 5061623a34 with one plain-shell clang-19 recipe; identity smokes; perf cells llama-8b cpu / qwen3-4b fpga / gpt-oss-120b fpga / Glimmer; margin probe for issue #4444); tracking issue #5021 (rename + new-shape-minimal-change requirement) referenced in the PR body"
metadata:
  type: project
---

jhan 2026-10-18: extend PR #5015 testing: include other 128x16 models if any; add llama3.1-8b, qwen3-4b (hw attn), one
gpt-oss (hw attn), which must show no perf degradation; compare with and without the PR; test token identity (expect
issue #4444 on Glimmer: add the test data to #4444, PR #5015 only references the issue); runtron is fine. Later the same
day: file a tracking issue for the namespace rename (names say kv_mul 4 but kernels serve 4 and 16) and reference it in
the PR body; the issue states one requirement: more shapes will come, look for implementation improvements so that a new
shape is a minimal code change -> issue #5021 (https://github.com/positron-ai/tron/issues/5021), referenced in the PR
5015 body "Open items" (patched onto the LIVE body: jhan had trimmed the Words table in the meantime).

Design: exec/glimext-20261018/ (README.md has the words, files, cells, launch line, traps). chain.sh steps B (two builds in
parallel, per-tag flock in build.sh), T (head tests + preservation vs base, same compiler), I (smoke.sh per identity cell:
arms base head head2 headoff; must-match head:head2 everywhere, head:base for llama/qwen/gpt-oss, headoff:base for Glimmer),
D (campaign.sh two binaries, arms base/head, REPS 4, arm order alternates per rep, TRON_ATTN_STATS=1, SKIP_SERVING_UP=1), E
(margin.sh: teacher-forced --intermediates-file runs of Glimmer tp2 cpu p1024, dd_logits_step.py at MARK = first-diff
index + 1), R (gen_report.py results.md/json + sync4424 summarize.py with WEDPERF_ARMS/PAIRS). Base = merge base, not
current main: main's 7 newer commits touch only rinzler.cpp, build-model.py and tests.

Traps hit while writing: (1) an apostrophe inside an unquoted ${VAR:?message} starts a quoted string (bash -n error far
away); (2) `pgrep -f glimext-20261018/build[.]sh` in the chain matched the sandbox's own bash -c wrapper -> replaced by a
per-tag flock in build.sh; (3) `pkill -f <pattern>` in a tool call killed the tool shell itself (exit 144) -> kill by pid;
(4) the sandbox dry run (scratchpad dry.sh: sed path rewrites, stub runtron/build/guard/dut, HugePages_Free awk replaced by
echo 512, rev-parse checks replaced by true) cannot run taskset -c 72-143 on claude-box (tests/margin steps fail there
only) and dd_logits_step rejects the stub's logits line format (real format: "... Logits of token N (vocab): values").

**How to apply:** launch = `bash exec/glimext-20261018/launch.sh chain` (or the README one-liner by hand on 3bda if the
classifier refuses); after chain.done: results in exec/results/glimext-20261018/results.md, then update the PR 5015 body
(sections Token identity + a new "Other models with and without this PR"; re-fetch the body first), the results page
muse-glimmer/muse-glimmer-amx-results.html, and post the Glimmer identity/margin data as a comment on issue #4444.
Related: [[glimmer-kvmul16-implementation]], [[i4444-root-cause-campaign]], [[bash-local-expansion-trap]],
[[nfs-running-script-stale-handle-trap]], [[platformd-011-restarts-stopped-units]].

RESULTS (chain 19:03-21:54 UTC on 3bda, 72/72 perf runs + 28 identity runs + 2 forced runs, serving restored): builds ok
(clang 19.1.7; kernel symbols base 4 / head 8), head tests 17424/5756/265452 + kill-switch 4110 with 2 skips; preservation by
mangled symbol (tests/preservation2/, preservation2.txt): pack and QK byte-identical (509/204 instructions), PV same 120
instructions in order, TLS addressing differs. Identity: 7/7 cells ok; llama head==base==head2 (headoff differs at token
12 = AMX vs AVX); qwen/gpt-oss (FPGA attention) all pairs identical; Glimmer headoff==base exactly in all 4 cells, head vs
base first difference at token 5 (tp2 fpga p1024), 53 (tp2 cpu p1024), 12 (tp2 fpga p2048), 30 (tp4 fpga p1024). Perf
(4 reps, paired, band = 2 x larger sd): llama p1024 +0.1 %, qwen +0.4 / +0.1 %, gpt-oss +0.3 / -0.2 % (sd 1.5 at tp4),
Glimmer +9.3 / +15.6 / +4.3 % decode, prefill -2.8 / -8.9 / -0.5 %; ONE flagged cell llama p8192 -0.09 TPS (-0.3 %, t -18,
band 0.05, 4/4 reps) with prefill -1.2 % -> 4 extra reps launched 22:0x UTC (chain2 STEPS='D R' REPS=8). Margin probe
(Glimmer tp2 cpu p1024, forced base ids, 51 GB records per run, 847 s): flips at steps 54/99/104; step 54 base margin
1.3125 = 21 ulps of 12.625, head delta_pair -1.5625; step 99 exact tie; step 104 margin 4.5 (9 ulps); nonflip median
|delta_pair| 0.75, median margin 69, max TVD 0.49. Issue #4444 comment posted (issuecomment-6255615621).
TRAPS of the day: (1) dd_logits_step.py --prompt-len PROMPT is wrong for Glimmer (BOS token -> 1025 prompt tokens, first
'Logits of token 1024'): every step shifted by one (first_flip 55 vs free-running index 53); derive P from the log instead
(margin.sh fixed; v1 analysis kept as steps-base-vs-head.v1-promptlen1024.json). (2) exec/logs/<NAME>.done = ok from round
1 makes chain2 skip step D: move it aside (.done.round1) before a relaunch with more reps. (3) 3bda's clock is ~32 min
behind claude-box's (log timestamps vs local time). (4) Review workflow (108 agents): 34 confirmed findings; applied in
place to not-yet-running scripts (campaign.sh latch seeding, margin.sh cleanup/reuse, gen_report n<2, launch.sh env
forwarding) and in chain2.sh/smoke2.sh (step I pass loop + in-cell deadline, current-pass fail count, D deadline check,
E relative bound E_MIN_HOURS, --dont-stop for identity runs).
FINAL 2026-10-18 22:2x UTC: llama p8192 after 8 paired reps = -0.07 TPS (-0.3 %, t -3.7, band 0.12 -> inside, negative in
6 of 8); recorded as an open item in the PR body (perf-counter comparison would settle it). PR 5015 body updated (3,128
words: Token identity filled, new section "Other models with and without this PR", open items; patched onto the LIVE body
twice, jhan edits kept). Results page muse-glimmer-amx-results.html regenerated with section 10 (gen_page.py read_ext,
EXT_RESULTS env; backup in the session scratchpad). Round-1 report copies: results.round1.{md,json}. Not published as an
artifact (not asked). Production serving restored; Bill marker untouched.


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): 2026-10-18 base-vs-head on llama/qwen/gpt-oss/Glimmer + identity + #4444 margin probe; issue #5021 rename tracker referenced in the PR body
