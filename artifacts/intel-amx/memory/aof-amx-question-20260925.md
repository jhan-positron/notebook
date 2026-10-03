---
name: aof-amx-question-20260925
description: "2026-09-25: jhan's question 'does the AMX path still run in decode when attention is on the FPGA (USE_HW_ATTN=1)?' answered in counter.html sections 2.2/2.3 (new-counters/); verified facts (tail = (p mod 4)+1 tokens, states that give AMX work under AoF, the 2026-09-17 501 M busy cycles unexplained by the small states); two measurement campaigns queued on 3bda (attnstats-20260925-fpga, -warm); artifact BDw6g8QYbCUKdZkGAmbdMQ republish state"
metadata:
  node_type: memory
  type: project
  originSessionId: 266ec0d5-0cad-41a6-b043-9787af43528d
  modified: 2026-09-25T05:22:06.873Z
---

Question (jhan 2026-09-25, PR3879/new-PRs/new-counters/counter.html): Table 1 puts AMX = 0 in every FPGA-attention row;
jhan's impression = in decode a partial newest KV page splits the work between AVX and AMX even under AoF; the figure-2
caption deserved its own sub-section.

Answer (page sections 2.2 and 2.3, generator exec/counter-20260922/gen_counter.py, patches in the session scratch;
verification workflow wf_12412298-770 = 6 readers / 2 refuters per claim / synth / critic, 79 claims kept, 6 dropped;
result JSON + claims/refutations dumps in exec/counter-20260922/):
- The AVX/AMX split of one decode step is a fact of the software path. CPU attention runs it every step. Under FPGA
  attention the CPU keeps only the tail behind the boundary L: (p mod 4)+1 tokens (1 to 4, mean 2.5) when every GOF copy
  landed, +4 per un-landed GOF; the tail never crosses a page edge, so the steady state has 0 AMX visits [full.hpp:2757-2759,
  2791-2794; ranged_mask.cpp:42-49; self_attention.hpp:1609-1611]. The DMA ring bounds in-flight copies at about 25 GOFs
  (100 tokens est.), above one page, so a whole-page lag is possible but unobserved.
- Table 1 zeros stay, relabelled "DMA keeps up: CPU tail 1 to 4 tokens (est.)" with footnote (a); decode FPGA AVX share
  now 640 K tokens per 256 steps (was 1,024 with a fixed 4-token lag).
- States that give AMX work under AoF (Table 2): 1 query below 127 (page 0 dense from p = 64); 2 first shard not engaged
  (32 GOFs x all layers landed AND boundary >= 127; earliest offload p = 128; prefill forward 2 sits on this gate); 3 copy
  lag of a whole page; 4 degraded shard (sw_fallback: its 1024 tokens + everything after, retried when the edge goes dirty
  with capacity); 5 prefix-cache branch INSIDE a shard (new branch builds its own shard, backfills; counts for the card only
  when the copied prefix reaches the branch start = at least 2 forwards all-CPU; est. 1-2 % of the CPU-attention count);
  5b hole in the copied prefix (branch never engages, no warning, fpga_queries 0); 6 prefill copy lag; 7 layers/models that
  are not card candidates. Not a case: a cached prefix ending exactly at a shard end reuses the landed shard.
- 2026-09-17 measurement (rinzler, 1 user, 910 cached tokens, 3 requests): 501 M AMX-busy cycles under AoF = 57 % of CPU
  attention, kill switch 0 -> AMX kernels DID run in a decode-dominated AoF cell (est. 1 M dense visits at 512 busy
  cycles per visit); states 1/2/5 give a few percent at most -> cause OPEN; candidates 5b and 7.
- USE_HW_ATTN=1 keeps the engagement point at 127 (same as unset); N >= 128 gives ((N+128)/128)*128 - 1.

Measurements queued on our half of 3bda (wait for the CI lease; launched by this session at 04:27 / 04:51 UTC):
- exec/attnstats-20260924/fpga-cell.sh -> NAME attnstats-20260925-fpga: runtron.attnhead2 (cbf1bb6c0c, PR #4596) with
  USE_HW_ATTN unset, TRON_ATTN_STATS=1; cells q3-4b-tp2-{8u-p1024,1u-p1024,8u-p64,8u-p8192}; arms headon2 + headkill2;
  results exec/results/attnstats-20260925-fpga/exit-reports.txt (written by the wrapper after campaign.sh).
- exec/attnstats-20260924/fpga-cell3.sh -> NAME attnstats-20260925-warm (waits for the -fpga .done marker): campaign-iter.sh
  (copy of campaign.sh with cell field 6 = extra runtron args) runs --iterations 3 cells: 1u/8u prompt 1000 (branch inside
  shard 0 = state 5/5b) + their it1 baselines + 1u prompt 1024 it3 (contrast, shard reuse); pass 2 = headkill2 + cpu control.
  Warm-iteration counters = (it3 - it1)/2. fpga-cell2.sh (prompt 1024 only) was superseded and killed before it ran.
- Predictions in page Table 3 (function _pred_cells in gen_counter.py): 8u p64 -> ready_amx 147,456 + pending_amx 2,304;
  warm p1000 -> 8,640-12,960 per user (state 5) or 1,258,272 (state 5b) or 0.
- TRAP: pgrep -f inside an ssh command self-matches the ssh shell; kill by explicit pid.

Page state (final, 2026-09-25 ~06:00 UTC): counter.html moved to new-counters/ (jhan, 2026-09-24); another session added
section 13.1 (per-layer K-token arithmetic) to the same generator on top of my 2.2/2.3 (both coexist). Generator copies:
gen_counter.py.v5-20260924 (before my patches), .v6-20260925-before-13.1 (after patch 1), .v7-20260925 (final). Page-text
verification workflow wf_aa9cf9e7-4bf (6 lenses x 2 refuters): 73 findings confirmed and applied (result JSON in
exec/counter-20260922/). Notable corrections it forced: STEPS = 255 decode forwards (Table 1 CPU row now equals the measured
4,464 AMX visits per user/layer/KV head); new state 5c "request that repeats a cached answer" (temperature 0 + repeated
prompt = each followed step is a re-score query with the whole context on the CPU; fits the 2026-09-17 count at ~75 followed
steps, est.); state 5 lasts (4 - s mod 4) K/V forwards + the re-score forward (5 to 6 at s = 1000); state 8 = hit at a shard
end followed >= 64 tokens grows a tail (floor((p-1023)/64) pages); DMA ring bound is per card (shared by users); figure 3
state 5 redrawn with no card range (p = 1001). Artifact BDw6g8QYbCUKdZkGAmbdMQ republished by this session as Version 5
(1790315516-8842); republish with url= from any session. Warm cells: runtron --iterations reproduces the same tokens when
sampling is deterministic -> expect state 5c (fully followed) rather than state 5; the runtron "[Iteration k/3] ... reused
tokens" line tells them apart.

**Why:** the FPGA-attention AMX question will recur when the queued exit reports arrive; the predictions and the
state list are what to compare them with.
**How to apply:** after the campaigns finish, read exit-reports.txt of both result dirs, compare with Table 3, fill the
"evidence" column of Table 2, and decide the 2026-09-17 cause (5b: fpga_queries 0 in warm iterations; 7: per-layer line).
Related: [[attn-path-counters-design]], [[attn-stats-pr-implementation]], [[prefill-amx-vs-fpga-qwen3-4b]],
[[issue-4500-root-cause-campaign]], [[amx-busy-perf-counter]].

RESULTS 2026-09-25 (both campaigns DONE: fpga 13:33 UTC 8 runs, warm 14:04 UTC 9 runs, 0 HBM warnings; page section 2.4 + Table 4,
generator v8 reads exit-reports.txt and asserts Table 3 predictions; artifact republished):
- steady state EXACT: 8u/1u p1024 and 8u p8192 decode ready_amx = pending_amx = 0, pending_avx_k_tokens 1,465,344 = prediction
  (mean tail 2.49 tokens -> zero copy lag at every poll), ready_empty 0, path sets fpga+avx only; prefill p1024 forward 2 card-assisted.
- states 1+2 EXACT at prompt 64: ready_amx 147,456, pending_amx 2,304, sets amx 8 / avx+amx 504 / fpga+avx 1,528; kill switch shows
  the same as avx_full_page visits.
- state 6 at prompt 8192 prefill: 3 of 64 forwards per user with 8 whole pages (512 tokens) lag, 7,077,888 AMX visits, 0.6 % of card
  prefill K tokens, IDENTICAL in the kill-switch arm (structural; which forwards = open).
- state 7 EXCLUDED for qwen-3-4b (per-layer line: all 36 layers fpga > 0, amx 0).
- warm p1000 (runtron --iterations 3 diverged after 0-6 tokens -> state 5, not 5c): 38,304 AMX visits per warm request (1u) /
  44,856 per user (8u) = est. 9-10 all-CPU forwards x 15 pages = 3.0-3.6 % of the CPU-attention count (1.5-1.8x the code estimate).
- state 8 zero REFUTED: p1024 warm followed 12-20 tokens then branched at 1036; whole 1,024 prefix on the CPU for est. 4 forwards
  (18,432 visits per warm request); shard reuse does not hold during the branch's first forwards (mechanism open).
- 2026-09-17 57 % still unexplained: candidates 5c (needs rinzler at temperature 0 + counters) and 5b.
- open oddities: path set "amx" alone (no AVX) for 7 jobs per warm iteration; the 'fpga' alone set = re-score queries of a token
  already on the card.
