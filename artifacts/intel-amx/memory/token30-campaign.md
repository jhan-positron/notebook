---
name: token30-campaign
description: "Token-30 root-cause campaign DONE 2026-08-30: verdict = exact bf16 tie flipped by admissible numerics (no AMX bug); results in exec/results/dd + definitive-decode/token30-results.html; debug branch jhan-dd-debug"
metadata: 
  node_type: memory
  type: project
  originSessionId: 528c65a4-1a65-45cc-a91c-9abf2f9fd11a
  modified: 2026-08-30T08:12:47.564Z
---

Goal (jhan 2026-08-30): exercise the determinism debug ladder on the real flip: qwen tp2, 2048-token
Moby Dick ch.1 prompt (-u 1), AMX off picks " but" and AMX on " and" at generated token 30
(archived exec/results/slot1/t1-quick/*.log; 222/256 tokens differ after it). Classify the cause
(H0 unpinned / H1 near-tie + admissible / H2 rounding-mode / H3 add-order / H4 dispatch-pages /
H5 kernel / H6 flip moved). Plan: intel-AMX/definitive-decode/debug-plan.html (v2 after a 4-lens
review, 45 findings applied). Predeclared rules: near-tie = OFF margin <= 1 bf16 ulp of top-1 OR
<= 2x p95 |delta pair| over non-flip steps; graded stat = mean|delta| over vocab; H2 if trunc
build / canonical median mean|delta| < 1/3; H5 = 'Attn out layer 0' first-page change > max(2 ulps,
add-order control) or changed fraction > 3x control (control = R3c: OFF with two fewer app cores).

RESULT (campaign done 12:52Z 2026-08-30, all runs rc=0, guard released): VERDICT H1 (+H3-leaning,
saturated): at the flip step the OFF arm's top-2 logits are an EXACT bf16 tie (margin 0 ulps; ids
11 vs 13), ON has them 1 ulp apart; 2 of 64 steps are 0-ulp ties; 3 flips in 256 forced steps
(22:0, 37:0, 145:3 ulps). Gates all held (A/A 0 differing keys over deterministic labels; forced
replay exact; mirror==canonical 0 keys; kernel tests 6158/6414/6157 assertions; AMX engaged
9.4M invocations ON / 0 OFF). First per-layer delta = 'WO layer 0 of token 128' (first query
seeing complete READY pages; pages filled in the same 128-token prefill chunk are not dense-
dispatched) - same key and same step-22 flip in the add-order control R3c (OFF, two fewer cores,
no AMX). Truncation build ratio 0.89 -> rounding mode not the driver; any 1-ulp perturbation
saturates into the same logit-level delta class. Flip moved from token 30 (archived binary gone;
today's OFF differs from 2026-08-18 OFF at token 4). inc1b CHECK (18:50Z): preserved runtron.inc1b
(2026-08-19) with the archived flags gives OFF words IDENTICAL to today's canonical build (256/256) and
the SAME step-22 flip to the same word; both differ from the archived 2026-08-18 run from token 4 (OFF
and ON) -> the archived divergence is environmental (weights/tokenizer/machine) or in code older than
inc1b; historical token-30 cause UNRESOLVED. Codex plan review (definitive-decode/codex-review/
review.html) answered point by point in exec/results/dd/codex-response.html (included in the results
page); open per codex: ON/ON repeat, production-tensor replay at the flip's attention call, page-id
trace, fail-closed marker, HF exact-id comparison. NOT run: R8 HF arbiter (Phase 1c tokenize_py
JSON parse failed because `nix develop --command` prints its banner on stdout - take the last
line; and a 0-ulp tie cannot be arbitrated anyway). INSTRUMENTATION BUG: P2 'Attn out' label
differs between identical OFF runs while WO is identical -> excluded via dd_report
--ignore-labels; placement (after attn_done_barrier, reading output[ix]) reads a buffer that is
already reused; fix on jhan-dd-debug only if needed. Report: definitive-decode/token30-results.html
(dd_report.py includes exec/results/dd/verdict.html). Campaign script v3 = exec/dd/dd-campaign-v3.sh
(idle criterion = SYSTEM_STATS Open/Busy over 10 min + connections; build skip).

Launch history: v2 launched ~08:06Z (builds canon 2452 s, mirror 2097 s, trunc 80 s at light
profile); v2's rinzler idle grep counted periodic '#EVT# SYSTEM_STATS ... Sessions' lines as
traffic -> replaced by v3 at 11:54Z; direct `sudo systemctl stop rinzler` from my tool was blocked
by the auto-mode classifier (the campaign script applies the standing policy itself). Original
launch details: exec/dd/dd-campaign.sh (log
exec/logs/dd-campaign.log, marker exec/logs/dd-campaign.done, results exec/results/dd/, big logs
/var/tmp/jhan/dd/). Stage B builds 3 variants in ~/workspace/ai-runs/tron-dd (branch jhan-dd-debug, commits
bd68d5cb50 + 2f268298e7; NEVER touch jhan-amx-p0): runtron.canon / .mirror / .trunc with
BUILD_INGEST_MODELS=ON, preset cross-avx512, traces copied from tron-amx; light profile (-j6
nice/taskset) while CI busy. Stage A waits for the lease + rinzler idle policy + guard. Stage C:
R1a/R1b/R2 (tokens), R1c (HF-tokenizer prompt ids -> --text-token-file if they reproduce r1a),
R3a/R3b (A/A values), R3c (add-order control), R4 (forced ON), R3x/R4x (256 forced steps, logits
only), R7 (t_amx_numerics.<variant> -s directly), R6 (mirror canary, footprint must be > 0 GB),
R5 (truncation). Intermediates filter: 'Logits|Top-k|Attn out|WO|WQ roped|WK roped|WV'.

Finish: (1) when the marker exists, `python3 exec/dd/dd_report.py --res exec/results/dd --out
definitive-decode/token30-results.html` (mechanical classification + charts), then write the
verdict by hand; (2) interactive Phase 3: `exec/dd/dd-phase3-hf.sh r8` (HF arbiter, needs
prompt.ids from R1c) and optionally `r9`; (3) update debug-plan.html status + link results;
(4) if the build failed (marker build-*-failed) read exec/logs/dd-campaign.log, fix on jhan-dd-debug,
relaunch. Traps already handled: -u N appends Moby Dick prompts (never with a token file); existing
tron-amx gen/runtron lacks ingested models (BUILD_INGEST_MODELS=OFF); ctest hides Catch2 WARN
(run binaries directly); extract_logits writes tokens AND logits as bare sha256 files (parse
'Saved tokens to:'); test binaries take SYSTEM_CONFIG env; hugepage files are slice-*-of-8.

**Why:** multi-hour unattended campaign; a fresh session must be able to read and finish it.
**How to apply:** check the marker/log first; do not relaunch while `pgrep -af dd-campaign.sh`
shows it running. Related: [[runtron-determinism-recipe]], [[debug-code-new-branch]].


FOLLOW-UP STATE (2026-08-30 later): results page now opens with jhan's question + answer
("no proof AMX introduced a regression" is the correct claim; "proved no regression"
overstates; the analysed flip's tie is a demonstrated mechanism). Plain-English section
rewritten after a 2-agent readability/numbers check (all terms defined; counts corrected to
0 of 304,176 outside Attn out). Handoff for the next agent: definitive-decode/HANDOFF.md
(8 prioritized work items; top: same-input replay at the flip's attention call, ON/ON repeat,
Attn-out label fix, page-id trace, HF arbiter with exact ids, historical event via reflog).

SOURCE SPLIT (2026-08-30, from existing logs, no machine time): at WO layer 0 (cascade-free;
layer-0 K/V come from embeddings), tokens 128-2047: rounding-only (r5 vs r4) median rel 0.00222
(100% of values); add-order-only (r5 vs r3a) 0.00007 (32%); both (r4 vs r3a) 0.00222; non-AMX
control (r3c vs r3a) 0.00202. Rounding dominates locally ~30x and equals the accepted control's
size; end-to-end both saturate (trunc ratio 0.89). Refines the earlier "rounding not dominant"
(that was the end-to-end statement). dd_report.py now computes this row (wo_layer0_stats).
Keep-RNE decision stands: truncation would buy no sameness and is the biased rounding.
