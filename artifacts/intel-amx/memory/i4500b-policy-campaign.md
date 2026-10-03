---
name: i4500b-policy-campaign
description: "2026-09-30: issue #4500 round 2 = policy commit 452b2052c9 (blocks completed under FPGA attention stay row-major; no forward-end VNNI conversion for HW-scored KV slots) on jhan-amx-vnniK-i4500 (deb line 2fd11e32ca); fact sheet refuted the 'positions 64..126 scored on CPU' claim; campaign exec/i4500b-20260930/ (chain A0 A B C T D E, NOT_BEFORE 13:00Z, REPS 4) waits for the nightly; goal = qwen TPS not worse than canonical AMX while TTFT already better"
metadata:
  node_type: memory
  type: project
  originSessionId: b0cfc925-5b1e-4504-94b7-d6d1505d5718
  modified: 2026-09-30T05:13:46.558Z
---

Request (jhan 2026-09-30 ~04:25 UTC, ultracode): "fix-results.html and fix-4500.html showed that the fix delivered worse
perf on qwen compared to canonical AMX. Investigate and find the solution. Deliver better TPS and TTFT using the VNNI-K
layout on llama-8b-tp2 and qwen3-4b (tp2, tp4) than canonical AMX; if not both, at least one better and the other not worse."

Where the requirement stands after the 09-29 cells (exec/results/i4500fix-20260928, n=3, canonical AMX deb = base):
- llama-8b tp2 8u p4096 (CPU attention): TPS +8.5 % (resolved), TTFT +0.35 % (+47 ms, t 10.6: resolved, small).
- qwen tp2 2u: TPS -2.3 % (t 3.2 n.r.), TTFT -1.4 % better (t -6.7 resolved).
- qwen tp4 4u: TPS -8.8 % (n.r., bimodal), TTFT -5.1 % better (t -37 resolved).
So the open item is qwen decode TPS "not worse" (TTFT is already better under FPGA attention: the AMX kernel in prefill).

FACT SHEET (workflow wf_6861a5cc-c84, 25 agents, scratchpad factsheet.md of session b0cfc925): under FPGA attention the CPU
scores only the tail above the DMA-complete GOFs (measured 2.49 tokens per job at prompt 1024); keys the card covers take the
software loop with NO K bytes read; the earlier claim "positions 64..126 scored on the CPU every step (engagement-prefix page)"
is REFUTED (engagement 127 gates query positions and the first shard's DMA prefix, never keys); the dense AMX kernel never
runs in steady FPGA decode at prompt 1024 (0 visits, PR 4596 counters) and prefill at 1024 had 0 dense visits in runtron;
gof::populate reads K once per (GOF, layer) per staging lifetime. Remaining FIX-vs-canonical per-step extras in FPGA decode
= main-thread bookkeeping (note loop atomics, 4 vs 1 page lookups) + convert_pending_k_blocks at the forward end (36 x 8
blocks x 16 KiB traffic per user every 16th step, serial on main) + 256 B staging memcpy. TRAP: main 3faba6d0fd carries PR
#4191 (workless-range dismissal), absent from the PR/fix runtron builds (merge-base c7844ca2ce), but the rinzler DEB packages
(ci-mimic 29a8a54740, fix 98a5accb8b, 2fd11e32ca) all contain main 3faba6d0fd, so the rinzler cells are NOT confounded;
runtron trace comparisons must use base = tron-main0916 (c7844ca2ce). EXE.AMX_BUSY 583 M (base/early launch) vs 1239 M
(VNNI late launch) per 20 s stays unexplained (LDTILECFG/TILERELEASE per non-empty section is the only code-supported source).

POLICY COMMIT 452b2052c9 (branch jhan-amx-vnniK-i4500, worktree VNNIed-K-in-place/tron-i4500; deb line 2fd11e32ca in
~/workspace/ai-runs/tron-i4500-deb): save_k_impl's note loop skips the pending-block push when cached_operation_uses_hw
(binding.operation); convert_pending_k_blocks early-returns on empty + TRACE_EVENT("model","convert_k_blocks","blocks",n);
Note [Row-major blocks under hardware attention] in kv_cache.hpp; t_llama_unit save_k case gains a SECTION setting
state.attention_operation_uses_hw[op]=1. Syntax-checked (lcheck2.sh VNNI + row-major), clang-format clean. Review workflow wf_f9b3a62f-255 (60 agents): 0 blockers; applied 06:1x UTC (amended, was d5e446805b): note loop hoisted
under !uses_hw (no row bits either, so copy_from never converts), staging reads row-major rows in place (page::k_row_if_row_major),
k_forget_row skips locked RMWs when no bit is set, notes + 6 stale comments fixed, test = 2 SECTIONs (op flagged / other op flagged,
named literal OPERATION_USES_HW_1). ACCEPTED LIMITATION (documented in the Note): the policy is static per operation, so a
software-scored range under a HW operation (before engagement 127, prompt < 128, degraded shard, USE_HW_ATTN=N) uses the dotter
where the old fix let the AMX kernel score decode-built pages; tokens identical either way.

CAMPAIGN exec/i4500b-20260930/ (README there): chain.sh steps A0 (runtron.fix of f34b0fe2ec in /var/tmp/jhan/tron-i4500),
A (452b2052c9 -> /var/tmp/jhan/tron-i4500b, runtron.fixS1 + tests), B (deb 2fd11e32ca -> /var/tmp/jhan/i4500b-20260930/root),
C smoke (fixS1 vs fix must be IDENTICAL under both attention modes; fixS1 vs fixS12 A/A), T traces (runtron base main0916 /
fix / fixS1, tp2 2u + tp4 4u, catA, gen 40, passes 10-; perfetto python works on claude-box now), D rinzler cells (arms base
fix fixS1 (+ basekill fixS1kill at tp4), llama base fixS1; REPS 4 planned), E row-major build tests. Launch: launch.sh
(NOT_BEFORE 2026-09-30T13:00:00Z); classifier may deny the ssh launch -> hand jhan the `! bash launch.sh` line.

**How to apply:** after the chain, run summarize.py (pairs fixS1 vs base / fix, kill arms), trace_analyze.py with
"convert_k_blocks" added to NAMES; verdict = fixS1 vs base paired t on both qwen cells; then decide push/PR update with jhan.
Separate lever noted, NOT folded into the PR: TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 (+7.7 % base, +11 % VNNI at tp2 2u, m6 09-19).
Related: [[issue-4500-fix-implementation]], [[issue-4500-root-cause-campaign]], [[vnnied-k-in-place-project]].

UPDATE 2026-09-30 14:1x UTC: chain b steps A0/A/B/C/T done (tests 5/5 pass at 452b2052c9; smoke fixS1 == fix in all 4 cells; 6 traces).
Traces (runtron catA, mean of 38 decode passes): tp2 2u pass base 5.052 / fix 5.164 / fixS1 5.112 ms; tp4 4u 7.523 / 7.651 / 7.377;
the fix's forward-end conversion burst is visible at passes 14 and 30 (+0.7 ms at tp2, +2.5 ms at tp4 per burst) and gone in fixS1;
main-thread Save K stays ~2x base (105 vs 58 us/pass tp2; 171 vs 111 tp4) = the remaining serial delta (~0.9 %). A store rewrite
(0bb74c2ab0 / deb f6aa724144, "view store instead of memcpy") was DROPPED after review wf_d9d0ea63-7ca: production K buffer is
bf16 (btensor = dmatensor<bf16>), so the old path was one memcpy already; the gap's cause is open (run-cut loop, per-row state
reads, panel placement are the candidates). Chain c (exec/i4500c-20260930/, perf-only: step W waits for results/i4500b-20260930/
chain.done, step P = perf record base vs fixS1 runtron tp2 2u -> results/i4500c-20260930/perf/<arm>/report-*.txt) launched 14:05Z.
Rep 1 rinzler cells (one rep, NOT resolved): tp2 2u base 191.7 / fix 190.7 / fixS1 193.2 TPS; tp4 4u 150.9 / 141.9 / 155.8; TTFT
fixS1 690/808 vs base 708/861 ms. Review nits left for later: no test instantiates store_k_block with a bf16 K buffer, and the
"row re-saved into a converted block" arm is untested through store_k_block.

RESULTS 2026-09-30 (chain b DONE 16:47Z, 40/40 cells ok, n=4, our half, rinzler + nightly client; summary exec/results/i4500b-20260930/summary.md;
report VNNIed-K-in-place/issue4500/policy-4500.html from exec/i4500b-20260930/gen_report.py):
- qwen tp2 2u: base 193.08 / fix 189.83 / fixS1 193.90 TPS -> fixS1 vs base +0.43 % (t -2.0 n.r.), fixS1 vs fix +2.15 % (t -6.2 resolved); TTFT 709/706/704.
- qwen tp4 4u: base 145.24 (sd 13.5, one slow rep) / fix 144.00 / fixS1 149.35 -> +2.83 % (t -1.6 n.r.); TTFT 882 -> 826 (-6.35 %, t -4.3 resolved);
  kill arms: basekill +0.55 %, fixS1kill vs fixS1 +0.33 % (both n.r.): the AMX bracket costs nothing measurable at tp4.
- llama 8u p4096: fixS1 42.95 vs base 39.60 (+8.44 %, resolved); TTFT 13455 vs 13409 (+0.34 %, +46 ms, t +4.1 RESOLVED at n=4; the PR head
  showed +23 ms and the 09-29 fix +47 ms) -> strict "not worse" fails by 46 ms on 13.4 s; candidate = whole-block VNNI store on main in the
  hand-written llama plugin (no shared block save); jhan decides.
- Verdict vs the requirement: qwen tp4 met (TTFT better, TPS not worse); qwen tp2 not worse on both (neither resolved, both slightly positive);
  llama TPS better, TTFT +0.34 % resolved. Tests 5/5 (VNNI) + 3/3 (row-major) at 452b2052c9; smoke identical.
- Chain c (perf record base vs fixS1 runtron tp2 2u) ran from 16:47Z; results exec/results/i4500c-20260930/perf/.
- PERF (chain c, 17:2x UTC, reports by hand: perf report --tid <96/?-work_queue tid> -g none; the chain's --tid $pid was the wrong thread):
  Save K gap explained: K store symbols ~0.03 % in both; fixS1 main thread spends 0.91 % of all samples in latch_ref::count_down
  (base < 0.015 %) = the K/V latch release at the end of save_k/save_v, contended by workers parked on it with mwaitx (workers arrive
  earlier: Ready 141 vs 171 us). A threading-side follow-up (release without waking every core), not a store issue.
- Report VNNIed-K-in-place/issue4500/policy-4500.html (gen_report.py; 2 dumbbell charts checked with cairosvg). Memory index line updated.
- REPORT (jhan 2026-09-30 ~17:40 UTC: "generate HTML report, /plain-english, diagrams"): VNNIed-K-in-place/issue4500/round2-4500.html from
  exec/i4500b-20260930/gen_round2.py (7 inline SVG figures: key coverage, block life, per-pass series, wall-clock lanes of pass row 14,
  TPS/TTFT dumbbells on a percent axis, latch release; data via traces_passes.py -> traces/passes.json + lanes14.json). Reviewed by
  wf_c6c82f11-841 (89 agents: plain English, facts, diagrams; 84 confirmed findings applied). Facts fixed there: perf shares are relative to
  the filtered thread (--tid), paired t sign turned so positive = better, tracing overhead source = 09-19 rt-results (124.9 vs 113.5 TPS),
  analysis.md means include a 0-ms final forward (use passes.json), the wait is TSX xbegin+tpause (mwaitx name is historical), 25/50 workers.
  TRAP: cairosvg renders blank when the inline svg style has height:auto (put it in CSS); SVG text is not reflowed at phone width.
