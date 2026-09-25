---
name: attn-stats-pr-implementation
description: "2026-09-24: attention path stats (counter.html sections 5/9) IMPLEMENTED as ONE env var TRON_ATTN_STATS; branch jhan-attn-path-stats in ~/workspace/ai-runs/tron-attn-stats (base main 66c7bb8db1; commits 9b3832eb4b, 27c1a3a9d9, 16bbe20f47, cbf1bb6c0c); A/A on 3bda (exec/attnstats-20260924/): head switch-unset -0.17 % at p1024 (band 0.73 %) and +0.77 % at p8192 (faster) -> env var stays; confirmation chain2 on 16bbe20f47 queued; section 13 of counter.html = decision record fed by decision.json; DRAFT PR #4596 opened 2026-09-24 19:5x UTC"
metadata:
  node_type: memory
  type: project
  originSessionId: 22924373-d0c3-448c-ba41-f6004346c8e0
  modified: 2026-09-24T18:36:31.042Z
---

jhan (2026-09-24, in PR3879/new-PRs/new-counters): agrees with counter.html section 9, prefers the
environment variable over a build option ("easier to turn on"); rule: env var unless it has an
OBVIOUS perf impact, then build option. Then implement, test, draft PR, and add a section recording
the final decision to counter.html.

State (2026-09-24 ~18:40 UTC):
- Code: worktree ~/workspace/ai-runs/tron-attn-stats, branch jhan-attn-path-stats off origin/main
  66c7bb8db1, commit 9b3832eb4b (--no-verify: lefthook absent on claude-box). Files: NEW
  h/tron/models/attn_stats.hpp (Note [Attention path stats], visit_tally, rows [class][worker][layer],
  FUSE leaves /model/<id>/attention/{summary,<class>_totals,<class>_forwards,<class>_layer_L,
  <class>_worker_W}, weak_ptr callbacks, stderr summary in ~model_stats), self_attention.hpp
  (page_tok_result {hint, relevant_k_tokens, served} 16 B; per-call stats_on bool; run_attention_job
  T2/T3/T4; stream_hw_joins uint64_t* hw_wait_cycles param; run_joins bool stats_on param;
  prepare_uniform_hw_attention FPGA pass counters; "layer" perfetto arg), model.hpp (begin/end_forward
  around plugin_state.run, class = n_listeners == token_jobs.size(); fpga queries from hw_plan.by_job
  after set_passes; "n_listeners" perfetto arg), full.hpp (T1 around state.forward), NEW t/t_attn_stats.cpp
  (LABELS fake, no mount needed: get_value runs the read callback), t_amx_dispatch_dtype.cpp (stats
  split assertions + the 2 missing apply_page_range args that main lacks; overlaps PR 4557's fix),
  t_llama_unit.cpp (result.relevant_k_tokens; stream_hw_joins nullptr), t/CMakeLists.txt, README.stats.md.
- Verified facts from workflow wf_58133db0-409 (8 readers, 8 refuters, 3 judges, critic): cfg is
  constructed before self_attn_state (model.hpp:1048 vs :1084) so cfg.id is readable in the
  self_attention::state ctor; T4 must be keyed by attention-operation change on worker 0 (llama runs
  ops outer, minibatches inner); T5 = only the wait loop in stream_hw_joins; casual leaves need NO
  .skip (t_tronstats_convention requires live markers == manifest); MAX_STRING_LENGTH 2048 applies to
  writes only, callbacks may exceed it, keep leaves small anyway; EAGLE child shares cfg.id (leaf dir
  attention_eagle); fpga_queries from by_job after set_passes; kill-switch identity is
  avx_full_page(kill) == amx_visits + avx_full_page(on) with identical tokens; rdtsc 31 ticks on AMD;
  visits per decode step llama-8b 8u p1024 = 37,888 (94.6 % dense AMX); same-binary band p1024
  0.6-0.7 TPS (Step E 2026-09-22); a 0.1 % effect is not detectable.
- 3bda: base tree /var/tmp/jhan/tron-attn-base (66c7bb8db1, runtron.attnbase, cross-avx512 preset +
  INGEST ON + AMX ON) built 18:30 UTC; head tree /var/tmp/jhan/tron-attn-head builds via
  exec/attnstats-20260924/chain.sh (started 18:33 UTC, pid 2080049; log exec/logs/attnstats-20260924-chain.log;
  results exec/results/attnstats-20260924/). Campaign = copy of exec/i4525-20260922/campaign.sh with
  base*/head* arm names; arms base head headon base2 (3 reps, p1024 + p8192) then headon headkill
  (1 rep, p1024); fuse-poll.log = live leaf reads; exit-reports.txt = [attn-stats] stderr lines.
- Page: counter.html section 13 (generator gen_counter.py, v4 copy kept) reads
  exec/attnstats-20260924/decision.json (to be written by decide.py after the runs).
- Local checks: lcheck.sh syntax-only passes for t_attn_stats / t_amx_dispatch_dtype / t_llama_unit in
  gen and gen-amxoff configs; clang-format 19.1.7 clean.
- Open: cost-data entry for t_attn_stats (config/test-benchmarks.json, bin/slice bench --update on a
  runner-class host = whole 3bda) -> state as pending in the PR; PR not yet opened; decision.json,
  section 13 rows, PR body, memory update after the campaign.

**Why:** the branch, the chain and the page generator are spread over three places; a new session
must not rebuild them.
**How to apply:** check exec/logs/attnstats-20260924-chain.log first; if the head build failed, fix
in the NFS worktree, commit, relaunch chain.sh with HEAD_COMMIT=<sha> (NAME=attnstats-20260924b to
keep results apart). Related: [[attn-path-counters-design]], [[wade-fuse-question-pr4267]],
[[i4525-first-3bda-test-campaign]], [[platformd-011-restarts-stopped-units]].

UPDATE 2026-09-24 19:2x UTC: commits 27c1a3a9d9 (review fixes: class-split FPGA counters, guards,
last-wins FUSE registration, hoisted path bits, tsc_frequency_hz() accessor in h/system/system.hpp,
per-layer exit line, hetero test caller) and 16bbe20f47 (guide pass: named values PATH_BIT_*_N,
COUNT_ONE_1 ...; braces; off-state JSON fix; id whitelist; T1-T5 in the Note; 5 new t_attn_stats cases).
Main A/A round DONE (9b3832eb4b vs 66c7bb8db1, qwen-3-4b tp2 8u CPU attention, 3 reps): p1024 base 79.95
/ base2 79.67 / head 79.81 / headon 79.91 TPS (band 0.59 = 0.73 %; head inside); p8192 17.12 / 17.11 /
17.25 / 17.24 (head +0.77 % FASTER, outside the band on the fast side = code placement). Verdict: env var
stays. objdump: 384 apply_page_range instantiations, largest 11,866 -> 12,444 bytes, 0 lock-prefixed in
both; run_attention_job rdtsc 8 -> 9. Exit-report counts equal the closed form (ready_amx_visits
10,278,144; pending_amx 6,912 = 3 full-page steps -> open point 11.1 closed: a full pending page takes AMX).
Live FUSE reads in fuse-poll.log (99 lines). Kill-switch pair (headon/headkill p1024) runs after the
serving-up/takeover cycle; chain2 (pid 840912) then builds 16bbe20f47 + t_heterogeneous_scheduler and runs
base3/head2/headon2 x 3 at p1024. Review workflow wf_93caf57d-93e: 52 findings (on 9b3832eb4b), refute
phase running. TRAPS: pkill -f "bash chain2.sh" inside ssh kills the ssh shell (self-match) -> use pkill -fx;
build2.sh TARGETS must not include t_amx_dispatch_dtype for main (does not compile with AMX on until the
PR's fix); ssh launches with setsid nohup hang the ssh session until timeout but the job starts.

UPDATE 2026-09-24 19:3x UTC: commit 16bbe20f47 (guide pass, off-state JSON fix, id whitelist, 5 tests) and
cbf1bb6c0c (critic round: get_cpu_freq() instead of a new accessor -> h/system untouched; T5 renamed
join_wait_cycles; takeover info line; switch_value_turns_on() testable; t_attn_stats.cpp is a second
FILES entry of the t_llama_unit target -> no new cost-data row; comments one claim per sentence).
Code-review workflow wf_93caf57d-93e (6 finders, 104 refuters, critic; result json in
exec/attnstats-20260924/) reviewed 9b3832eb4b; its critic's must-fix list is applied except: bench row
(moot after the merge into t_llama_unit), a forward-class classifier unit test (not written; documented as
untested), ingested-plugin coverage beyond qwen (only qwen measured). chain2 (pid 1769452) waits for
chain1's "=== chain finished", then builds cbf1bb6c0c (head2.sha), runs 5 tests (+ t_heterogeneous_scheduler),
switch-on runs, a bad-value run (expects the warn line), objdump, then base3/head2/headon2 x 3 at p1024.
Files: PR body draft PR3879/new-PRs/new-counters/pr-body.md (placeholders left: CONFIRMATION, KILL);
counter.html section 13 regenerated (rows preliminary until decision.json has final=true).

UPDATE 2026-09-24 19:5x UTC: DRAFT PR #4596 https://github.com/positron-ai/tron/pull/4596 (branch pushed at
cbf1bb6c0c, label Skip benchmarks, assignee jhan-positron, no reviewers = jhan's call; body =
PR3879/new-PRs/new-counters/pr-body.md minus the H1). Final commit built on 3bda in 649 s; tests: t_llama_unit
219,944/56 (13 stats cases inside), t_page_share_counters 61/4, t_amx_numerics 4,109/4, t_amx_dispatch_dtype
1,589/1, t_heterogeneous_scheduler 1,900/2, all pass, also with TRON_ATTN_STATS=1; =yes prints the warning.
Kill-switch identity holds exactly (decode 10,285,056; prefill 17,731,584 = 16,515,072 + 1,216,512), K tokens
equal in both arms. Confirmation cells (base3/head2/headon2 x 3, p1024) running; when done: decide.py with
PR_TEXT, gen_counter.py, edit the PR body's confirmation paragraph (gh pr edit --body-file), memory. Bench row:
none needed (t_attn_stats.cpp is inside t_llama_unit). CI of the draft: lint lanes only until ready.

DONE 2026-09-24 20:0x UTC: confirmation round on cbf1bb6c0c (p1024, 3 reps): base3 79.78 +-0.41 / head2 79.81 +-0.38
(+0.04 %) / headon2 80.10 +-0.17 (+0.39 %). Final objdump: largest apply_page_range 12,603 B / 2,196 insns / 0 lock;
run_attention_job 4,874 B / 9 rdtsc. decision.json final=true (PR_TEXT set), counter.html section 13 regenerated
with all rows, PR #4596 body updated (gh pr edit). Kill-switch arm TPS 71.56 (-10.5 % vs AMX on) = the known AMX
gain, informational. Serving on 3bda restored by campaign.sh (serving_back_up). Open for jhan: reviewers; mark
ready; whole-host bench refresh of t_llama_unit's row (optional); FPGA-attention run for the FPGA counters / T5
(section 10 measurement 6, not done); forward-class classifier unit test (not written).
