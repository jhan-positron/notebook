---
name: wade-pr4596-review-response
description: "2026-09-28: W1 Option B accepted + better unit-test coverage required this round; Wade's 5 inline comments on PR 4596 (head 1430736b2a) analysed in PR3879/new-PRs/new-counters/respond-Wade-comments.html (generator exec/counter-20260922/gen_wade.py + combined.html + 3 SVGs); PR NOT updated; verdicts, recommended fixes (W1 SW-poll stretch timer, W2 forward_scope, W3 README + listener/kv_only counts now + per-job split follow-up, W4 asserts + fixtures, W5 pool-worker rows + layer_timers + split record), open decisions for jhan, traps"
metadata:
  node_type: memory
  type: project
  originSessionId: b0414974-08b1-4a2b-bd67-8a3bb7964f33
  modified: 2026-09-28T22:41:12.807Z
---

Wade (Wado-posi) reviewed PR #4596 on 2026-09-28 17:16 UTC (review 5342222359, COMMENTED, 5 inline
comments 4125033634/653/664/677/686 at head 1430736b2a). jhan asked for an analysis page only, no PR
update, with a top-down intro (run -> forward -> attention job -> join -> visit) first.

Page: PR3879/new-PRs/new-counters/respond-Wade-comments.html (artifact published 2026-09-28; light theme,
pure ASCII, no doctype/body skeleton like review-round3-response.html). Generator + parts copied to
exec/counter-20260922/ (gen_wade.py, combined.html, intro_fig.svg, w1_fig.svg, w5_fig.svg); the scratch
originals die with the session. Workflows: wf_0345146e-957 (5 readers, 10 refuters, critic; results in
the session's tasks dir) and wf_e224ff90-fd4 (12 prose + 8 citation checkers, 273 citations).

Verified verdicts (all five hold):
- W1 (self_attention.hpp:1131): T5 rdtsc pair only in stream_hw_joins (:1132/:1147); the run_joins poll
  (:1258, `if (!join_hw && sections_left[kv_head]) continue`) is untimed -> CPU-attention rows read 0
  (6/6 in attnstats-20260924b); docs widened at rename cbf1bb6c0c (hw_join_wait_cycles -> join_wait_cycles),
  hook never moved; design page defined T5 as FPGA wait. REC: time no-progress stretches in run_joins into
  the same local (0 rdtsc off, 2 per stretch on); NOT Wade's per-head clock (double counts); docs "both modes,
  inside T2"; new SECTION in t_heterogeneous_scheduler; DONE 2026-09-29 (commit on the branch): SW-join section + HW-join T5 check in the mixed-attention section; t_llama_unit :2827/:2876 now pass a real accumulator and CHECK 0 (no wait there: every sweep progresses).
- W2 (full.hpp:2093): record has 2 layers/3 call sites (full.hpp:2100; model.hpp:1745/:1750; :2730-2735
  fpga_queries); only ONE caller of state.forward (full.hpp:2096); proxy/mock hold no state; EAGLE child =
  2nd full_scheduler (legacy_dispatch.cpp:76-77). REC: forward_scope : noncopyable<> at top of
  model::state::forward (after TRACE_EVENT :1655, before with_latch_arena :1658), ctor begin_forward + T1 start
  (+ n_listeners), dtor T1 stop -> note_forward_wall -> end_forward; full.hpp leaves the PR; T1 shrinks (no fold);
  forward() binds indexed_span (NO copies); run_forward is public (:1042) -> private: label. Scope top knows
  only token-job count + listener count; listener_job_index/n_empty_listeners are built inside run_forward.
- W3 (model.hpp:1746): per-forward class deliberate (design rule + 09-25 no-phase-state finding); Wade right:
  serving mixes a prompt chunk with other users' decode (full.hpp:1968/:1990 walk whole tree; chunk listener
  :2461-2470); runtron lockstep (exit reports 255x8 decode, prefill never mixed); per-q_batch REJECTED
  (chunk_evenly model.hpp:249-262 mixes users); per-job tag feasible (has_listener model.hpp:1800-1803,
  tok_ix.i index at self_attention.hpp:1616-1621, 1 byte load/visit inside the hoisted bool); timers can't split.
  REC: A (README sentence) + E (listener_jobs, kv_only_jobs per forward class, added keys) in this PR; C (per-job
  visit rows) as follow-up (breaks gen_counter.py:410 / decide.py:167 silently, ~300 lines, no on-state A/A,
  reopens jhan's naming). jhan's call; reply asks Wade.
- W4 (attn_stats.hpp:382): 9 guards, all dead in production (worker < n_attn_workers <= pool = rows; layer <
  n_layers; token_job < token_jobs.size() sized by begin_forward before plugin run); row() asserts 4 of them;
  fpga_at/note_fpga_query/end_forward (fpga_bits[job] :451 unguarded) need asserts added; note_token_path has NO
  production caller (delete). REC: asserts everywhere, token_path_span(worker, n_token_jobs) asserting both ->
  no per-visit compare; fixtures needing begin_forward/forward_scope: t_llama_unit :2204, after :2330, after the
  rebuild that follows :2542; t_amx_dispatch_dtype :164; heterogeneous_scheduler_compile after :459 AND :188-204
  case (its STATS_DISABLED_FALSE is the run_joins arg, not the state switch); keep negative test via
  assertion_signal (t_llama_unit.cpp:271-283, fork+SIGABRT) moved to a header; const row() overload lacks asserts.
- W5 (self_attention.hpp:498): rows sized pool (27) indexed by attention worker; split moves INSIDE a run
  (llama.hpp:593-609 per forward; recommend_n_main_helpers model.hpp:1994-2037: default 7, single-minibatch fixed
  7 clamped to largest-minibatch token count -> 1-user decode = 1 helper/26 attn workers; measured active_workers
  26 in 1-user, 20 in 8-user runs); 8-user decode split = Insufficient data (code predicts >=23, measured 20).
  Threads pinned per pool index (threading.hpp:762-767, :819-822). REC: key rows/path_bits by pool worker
  (pool_worker() asserting inputs; NO_WORKER placeholder never reaches a hook), T3/T4 into a SEPARATE
  layer_timers[class][layer] struct (not merged into layer_fpga_counters: W3-C re-keys FPGA by job class),
  note_attn_workers from assemble_attention_plan_impl (:2280) -> n_attn_workers_min/max per class + fold only last
  n rows (optional); B alone incomplete (T4 hook writes literal row 0 :392, T3 tests worker==0 :413).

Combined: 4 fixes in one patch (order W4 -> W5 -> W2(+W3-E) -> W1 -> docs); one verification pass (3 test
binaries switch unset/set + objdump-check.sh; 3bda CPU cell + FPGA cell regenerate PR-body samples; one A/A at
final head). PR-body samples that go stale: :105-110, :112-127 (T5 0, worker leaves/_w0, T1, new keys).
counter.html lines to regenerate: 653/658/785/854 (T1), 633/662/791 (T5), 667/851 (keying).

jhan decisions while reading (2026-09-28, evening): W1 Option B (no-progress stretch timer in run_joins)
ACCEPTED. jhan: the untimed run_joins poll shows a unit-test gap -> this round's patch must raise
unit-test coverage (at least: T5 in software-join mode AND in HW mode, the CPU-attention 0-row case as
a failing test first). 3bda was taken at that time; NO work started; jhan sends comments section by
section, wait for the rest before patching.

Open for jhan: C now vs follow-up; empty_listener_jobs (needs a 2nd hook after partition_listeners);
fold restriction worth it; reply wording (drafts on the page, none commits to the split); reviewer replies.

**Why:** the next step is jhan's decision and then the patch; every fact above was refuted/checked and
should not be re-derived.
**How to apply:** read the page first; line numbers are of 1430736b2a and shift after any push. TRAPS:
(1) text extraction for prose checks must escape/keep `<` in code (my regex tag-stripper ate `mask_t<64>` and
`if (tok_ix.i < n_path_bits)` -> false "cut-off code block" findings); (2) f-string sections need `{{}}` for a
literal `{}` but plain files (combined.html) must not; (3) refuters cite gen_counter.py line numbers as
counter.html lines (1027/1109 are generator lines); (4) the shell prints a directory listing on `cd` in
this environment, use absolute paths in agent prompts. Related: [[attn-stats-pr-implementation]],
[[attn-path-counters-design]], [[aof-amx-question-20260925]], [[pr-body-refetch-before-edit]].

UPDATE 2026-09-29 14:xx UTC: jhan asked to regenerate section 4 (W2) in plain English with +/- color-coded diffs and a
context diagram. Done in gen_wade.py (new helper diff(): "=== " header / "+" add / "-" del / context spans; CSS pre.diff,
.legend, .wA/.wB/.wC/.wS writer colors, td.cA/cB/cC; "In plain words" box; record table; figures w2_fig_today.svg /
w2_fig_fix.svg in exec/counter-20260922/, rendered + inspected with cairosvg; the W5 figure is now Figure 5). Section 4
cites the branch head 37bb2a4055 (attn_stats.hpp lines moved +4..5 after the W1 edit: forward_counters :247-254,
current_class_ix :339-341, note_forward_wall :441-447, end_forward :452-469, note_fpga_query :473-477). Verified by
wf_f55b1d12-561 (57 findings, 50 confirmed, all applied). Facts learned: run_forward is public because `state` is a
struct with no access label (:1043-3446), the `public:` at :1042 is model's; hunk 1 needs `#include "common/util.hpp"`
(noncopyable, util.hpp:54; attn_stats.hpp does not reach it today); construct_hw_plan (:2497) is called from
assemble_attention_plan (:2296) once per minibatch before any layer (llama.hpp:596); off-state cost today = 1 copy +
2 tests in full.hpp + begin/end_forward tests; note_forward_wall's test is unreachable when off. Page republished to
artifact WoobG3wdibRg1h3enPQSA4 (same URL).

UPDATE 2026-09-29 18:xx UTC: sections 5 (W3) and 6 (W4) regenerated like section 4 (In plain words box, figures
w3_fig_serving/units/tag.svg + w4_fig_indices/fixtures.svg, colored diff hunks); figure numbering now 1-10 (W5 figure = 10);
checked by wf_ffa9db0b-45b (115 findings, 109 confirmed, applied). Republished to WoobG3wdibRg1h3enPQSA4 (version 4).
Verified facts for later rounds: chunk_evenly grains = runs of <= 8 jobs (minibatch_grain_size, common.hpp:315), cut
depends on affinity-id order (model.hpp:209-284, :287-340); listener per chunk registered at src/tron/scheduler/full.cpp:191-193,
given to the last token at full.hpp:2465-2478; chunk size env TRON_PER_USER_PROMPT_CHUNK_LIMIT (h/libtron.hpp:196-204);
the 09-25 page has no "option F" (the alternative is the work-shape class under "The smallest exact change, if wanted");
assertion_signal twin at t/t_compute_attention_unit.cpp:22-34; compile_generated_attention_calls (hetero :163-215) never runs;
decide.py parser lines are :63/:74 (not :167); const fpga_at overload (:345-347) also lacks asserts (W4 detail).
W2 IMPLEMENTED (c612b82a84, 3bda green). W3/W4/W5 still pending jhan's reading.
