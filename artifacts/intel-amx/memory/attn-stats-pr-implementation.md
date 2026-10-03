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

UPDATE 2026-09-25 (05:5x UTC): jhan asked for two edits on PR 4596: "the card" -> "the FPGA card" in the
prepare_uniform_hw_attention stats comment (self_attention.hpp:630), and attention-job hooks named
attn_job: note_job_entry_w0 -> note_attn_job_entry_w0, note_job -> note_attn_job (12 occurrences: 2 defs,
2 call sites, 8 tests). Committed LOCALLY as 01c16f0fc7 on jhan-attn-path-stats (NOT pushed; PR head on GitHub
is still cbf1bb6c0c). Checks: clang-format 19.1.7 via uvx clean; ~/workspace/ai-runs/lcheck/lcheck.sh
gen t/t_attn_stats.cpp and t/t_llama_unit.cpp with worktree tron-attn-stats exit 0 (no build tree here:
compile_commands.json at the worktree root is a dangling link). Two sibling comments still say "the card"
(attn_stats.hpp:226-227 layer_fpga_counters, :415-416 note_fpga_pass); not changed, jhan named one line.
Docs need no edit (pr-body.md, README.stats.md, counter.html do not name note_job).

UPDATE 2026-09-25 (06:0x UTC): jhan asked for the two sibling comments too ("the FPGA card" in the
layer_fpga_counters and note_fpga_pass comments) and to push. Commit 04dab92a77 on top of 01c16f0fc7; both
PUSHED to origin jhan-attn-path-stats -> PR #4596 head is now 04dab92a77 (was cbf1bb6c0c). No "the card" left in
the PR's added lines. PR body needs no change (no hook names in it).


UPDATE 2026-09-25 (18:xx UTC, review round 3): jhan's self-review of PR 4596 (13 edit requests + 6 questions + 4 naming
questions) applied as ONE local commit ebadce2adb on jhan-attn-path-stats (NOT pushed; PR head on GitHub still 04dab92a77).
Applied: on->enabled (member; stats_on->stats_enabled, full.hpp attn_stats_enabled; JSON key "on" UNCHANGED), add_relaxed->inc_relaxed,
switch_value_turns_on folded into env_enabled (its 7-check unit case DELETED; the =yes warning is now checked only live),
COUNT_ONE_1/INCLUSIVE_INDEX_TO_COUNT_1/FIRST_INDEX_0/BIT_CLEAR_0/BIT_SET_1 removed (fpga_bits stores PATH_BIT_FPGA_4 itself),
TIMED_WORKER_0->WORKER_0 (no comment, jhan's instruction; the test's own WORKER_0 dropped: using-directive ambiguity), T4 comment
block re-attached, comments on path enum / N_PASSES_2 / T3. NOT applied (jhan's pick pending): path->visit_path (rec) or visit_kind;
decode_like/prompt_or_mixed -> all_jobs_with_listener/some_jobs_without_listener (rec, external leaf names); get->load_relaxed (rec);
hw_wait_cycles/note_hw_wait -> join_wait_cycles/note_join_wait (rec); N_PASSES_2 stays (two run_sections calls per job = fact) or
N_PHASES_2/PHASE_READY_0/PHASE_PENDING_1. Verified facts (wf_08b87b9e-b66): listener = one entry per request edge on its last token,
EVERY prompt chunk gets one (empty buffer when non-final) -> decode_like also = 1-token chunk, cached-prompt re-query (do_kv=0),
spec verify step, edge-split corner; "none" path set impossible in a correct run (own K always in sw or hw mask; model.hpp:746 calls
it silently wrong output), measured 0 in 52/52 forwards lines; tsc_hz = get_cpu_freq() = TSC rate vs CLOCK_MONOTONIC (2.70 GHz), not
the core clock; "pass" is overloaded in the header (software ready/pending pass vs FPGA hw_pass). 3bda: f7da0e64ab built 10 min,
5 test binaries pass (t_llama_unit 219,937/55 = -7 checks/-1 case = the deleted switch test); TRON_ATTN_STATS=yes via
t_heterogeneous_scheduler prints the warning once (the 09-24 "5 warning lines" were the deleted test's values, not the env);
confirmation build of ebadce2adb (comment-only diff) launched via exec/attnstats-20260925-review/build-test.sh. Page: new-counters/
review-round3-response.html = artifact CJfqdoTwggw7SGHhRLZrwk. pr-body.md updated locally (12 cases, stats->enabled); GitHub body
NOT updated (do it with the push). Diff-review workflow wf_e77e93ba-661: 24 findings, 5 should-fix applied. TRAPS: git commit in
this worktree needs --no-verify (lefthook missing); the first commit attempt failed silently and the 3bda build was launched with the
OLD sha (killed with kill -- -<pgid>); clang-format re-aligns trailing comments so a sed on the exact old spacing misses.
CONFIRMED 2026-09-25 18:29 UTC: f7da0e64ab (= ebadce2adb minus one comment line) built on 3bda in 10 min, all 5 test binaries pass
with the same counts, TRON_ATTN_STATS=1 runs pass, =yes prints the warning once (t_heterogeneous_scheduler). Results in
exec/results/attnstats-20260925-review/ (fac3d21d10 run in -review-fac3d21d10/). pr-body.md carries the new test bullet (local).
UPDATE 2026-09-25 20:0x UTC (round 3 picks): jhan picked visit_path (type only), load_relaxed, join_wait_cycles (+ note_join_wait)
-> LOCAL commit 0274131d23 on top of ebadce2adb (NOT pushed). 3bda build ok, 5 test binaries pass with the same counts
(t_llama_unit 219,937/55), =yes warning printed once. N_PASSES_2 family unchanged. Class names (decode_like/prompt_or_mixed) NOT
renamed: jhan asked first whether a global prefill-vs-decode state exists ("position > prompt length = decode?"); research workflow
wf_625fd241-a04 (6 readers x 2 refuters, synthesis, critic) answers it; result to be added to review-round3-response.html.
ANSWER (wf_625fd241-a04, 2026-09-25 20:1x UTC) to "global prefill-vs-decode state?": NO. Prompt length/phase live only above the
scheduler (generation context prompt/prompt_processed/num_tokens_seen context.hpp:74-78; rinzler stream_state.prompt_tokens
rinzler.hpp:601; token stream monitor per handle). sequence_prompt/extend_request are the same call for prompt chunks and generated
tokens (differences: monostate logits for non-final chunks; tokens_reused_out non-null for prompt chunks; num_ephemeral = speculation
only). token_info = {token, kv_ready, eagle_ready, kv_replay_pending}; forward's 13 inputs carry no prompt length / request id (one
active_handle_id per forward). Positions are 0-based tree heights: first generated token AT position == prompt length (>=, not >);
shared prefixes make one position prompt for one user and generated for another. Rule mislabels work shape: cached-prompt re-query
(do_kv=0, decode-shaped), fast-forward tokens and spec verify (prefill-shaped). Smallest exact change = origin bit through
sequence_prompt -> extend_request -> token_info -> per-job byte next to token_jobs_do_kv -> 3 classes; wide surface (public API,
mock/proxy schedulers) -> out of PR 4596. Recommended: keep the listener rule, rename to all_jobs_with_listener/some_jobs_without_listener.
(wf_625fd241-a04 synthesis+critic agree: option A rename = recommended; option B n_empty_listeners one-way prompt signal; option F
work-shape classes from do_kv+has_listener; cached prompt = one do_kv=0 job PER 128-token chunk, one forward each; rinzler restart
and multi-turn clients break any prompt-length rule. Page version 4 carries this. Open: jhan's class-name decision, push.)
UPDATE 2026-09-25 20:4x UTC: jhan decided the class names: enum values STAY decode_like/prompt_or_mixed; the stderr report labels
become "decode_like/all_jobs_with_listener" and "prompt_or_mixed/some_jobs_without_listener" (new CLASS_LABELS array). CLASS_NAMES
(leaf segment) unchanged because a slash in a leaf name would create a subdirectory. LOCAL commit 7f8a4aa4d8 (test + README updated);
our parsers gen_counter.py:410 and decide.py totals_of accept an optional "/rule" suffix. 3bda build of 7f8a4aa4d8 launched
(exec/attnstats-20260925-review/, earlier runs in -fac3d21d10/-f7da0e64ab/-0274131d23). Still NOT pushed; PR body on GitHub stale.
PUSHED 2026-09-25 21:5x UTC (jhan: "after this change, please push"): 7f8a4aa4d8 built on 3bda (21:36-21:46, all 5 test binaries
pass, labels print as decode_like/all_jobs_with_listener). Fast-forward push -> PR #4596 head 7f8a4aa4d8 (was 04dab92a77); PR body
updated via gh pr edit from pr-body.md (H1 stripped): 12 cases, stats->enabled, label note on the captured sample, 3bda bullet for the
three commits. Open for jhan: reviewers / mark ready; optional TRON_ASSERT_LT(set, N_PATH_SETS_8) in end_forward; the switch rule has
no unit test. Page review-round3-response.html = artifact CJfqdoTwggw7SGHhRLZrwk (version 5 = pushed state).
PUSHED 2026-09-25 22:1x UTC: d85edc0e28 (TRON_ASSERT_LT(static_cast<size_t>(set), N_PATH_SETS_8) in end_forward; jhan asked
"push now, report if a problem is found from testing"). 3bda run 21:58-22:08 finished before the push: build ok, all 5 test binaries
pass with the same counts. PR #4596 head d85edc0e28; PR body bullet says four round-3 commits. Page = artifact version 6.
UPDATE 2026-09-26 05:4x UTC (bot finding r4109173415): cursor[bot] on PR 4596 (comment 2026-09-25 22:37Z, at d85edc0e28) is RIGHT:
render_forwards ignored `enabled` and published a zero-filled object while render_totals and README.stats.md:239-242 promise {}
for both leaves; live proof = exec/results/attnstats-20260924/fuse-poll.log line 1 (switch-unset run, decode_like_forwards =
zero object). Fix = LOCAL commit 0a6c0a8582 on jhan-attn-path-stats (NOT pushed; PR head still d85edc0e28): render_forwards
follows render_totals ("{" + body if enabled + "}"), on-state bytes unchanged; t_attn_stats off-state cases now CHECK totals +
forwards of both classes as renderers and as FUSE leaves (renamed case "... only the summary, the class totals and the class
forwards exist, and the last two read {}"). clang-format 19.1.7 clean, lcheck.sh gen syntax exit 0. 3bda: nightly CI holds the
lease (run 36215458085 since 03:39Z) -> queue-after-ci.sh 0a6c0a8582 d85edc0e28 launched on 3bda (pid 2622803, log
exec/logs/attnstats-20260925-review-queue.log): waits wait_for_dut_free, moves results/attnstats-20260925-review ->
-d85edc0e28, runs build-test.sh. Push AFTER the 5 test binaries pass. Verification workflow wf_0f84832e-18b (3 lenses + critic).
No reply posted on the bot thread; PR body untouched (re-fetch before any edit, see [[pr-body-refetch-before-edit]]).
AMENDED 2026-09-26 05:47 UTC: commit is now 1430736b2a (0a6c0a8582 + test-comment split into two sentences after the critic of
wf_0f84832e-18b: no must-fix, on-state bytes proven identical by a standalone fmt run, 4 of the 6 new CHECKs are red on the old
code). 3bda queue relaunched for 1430736b2a (pid 3490270; the 0a6c0a8582 queue was killed before any build). TRAP repeated: pgrep -f
'<script> <sha>' inside an ssh command matches the ssh shell itself and kill -- -pid then kills the ssh (exit 255); use pgrep -fx
with the exact command line. Follow-up outside this fix (not done): README.stats.md:242-246 says the stderr summary prints when the
switch is set; the code also needs at least one counted forward/visit (print_report `if (!any) return;`).
PUSHED 2026-09-26 13:16 UTC: 1430736b2a is the PR #4596 head (was d85edc0e28); PR is no longer a draft (jhan marked it ready).
3bda run 13:02-13:13 UTC after the nightly CI released the lease: build ok, 5 test binaries pass (t_llama_unit 219,949/55 = +12
assertions: 6 new CHECKs + 2 REQUIREs inside each of the 3 leaf_string CHECKs), TRON_ATTN_STATS=1 runs pass, =yes warning printed.
Results exec/results/attnstats-20260925-review/ (the d85edc0e28 run moved to -d85edc0e28/). NOT done (jhan's call): reply on the bot
thread r4109173415; PR body still ends its Verification list at d85edc0e28 and says the switch-unset run showed "empty totals"
(the forwards leaf was zero-filled in that run, now {}); README stderr-summary qualifier follow-up.
UPDATE 2026-09-29 03:5x UTC (review round 4, W1 = Wade's "T5 misses the software join poll"): jhan accepted Option B and asked
for the fix + unit-test gap scoping + tests + a 3bda test after the nightly, coordinated with the i4500 session. LOCAL commit
bfb4cfc4be on jhan-attn-path-stats (NOT pushed; PR head still 1430736b2a): run_joins times the software poll as no-progress
stretches into join_wait_cycles (poll_waiting bool + t_poll; 0 rdtsc off); docs reworded (Note, field, hook, stream_hw_joins
comment, README T5 = both join modes, inside T2); tests: t_heterogeneous_scheduler new SECTION "software-only join times its
wait for the peer sections (T5)" (3 GENERATE arms: late producer on -> >0 and <= wall, sections done -> 0, stats flag off -> 0),
the mixed-attention section installs enabled stats (install_enabled_stats helper) and checks the HW-join T5 > 0 and <= wall;
t_llama_unit stream_hw_joins cases pass a real accumulator and CHECK == 0 (every sweep progresses). lcheck gen/gen-amxoff clean,
clang-format 19 clean. pr-body.md T5 bullet + "Not in this PR" edited locally (GitHub body untouched; re-fetch before edit).
3bda: exec/attnstats-20260929-w1/queue.sh bfb4cfc4be launched 03:5x UTC (pid 2840731): wait_for_dut_free, then holds the
campaign flock (--allow-serving) around build-test.sh (incremental build in /var/tmp/jhan/tron-attn-head, SUFFIX attnhead4,
5 test binaries, switch-on runs, t5-evidence.txt); results exec/results/attnstats-20260929-w1/, log exec/logs/attnstats-20260929-w1*.log.
Agreed with the i4500 session (issue4500-a2): its chain steps A/B may overlap my build (CPU only); its C/D take the same flock
and wait for my release (<= ~25 min); its end marker exec/results/i4500fix-20260928/chain.done. Workflows: wf_77ac48c5-d88
(test-gap audit of the whole PR at 1430736b2a), diff review of bfb4cfc4be (launched after). W2-W5 untouched (jhan still reading).
TRAP 2026-09-29 03:36Z: queue.sh launched at 03:36Z (before the nightly wrote its lease at ~03:38Z) -> wait_for_dut_free
returned at once and build-test.sh started 2 min before the CI; killed by hand (kill -TERM -- -<pgid>, no leftovers, the
lease file did not exist yet). "After CI" needs a NOT_BEFORE gate (13:00Z) plus ci_lease_busy 600, as i4500fix chain.sh does;
queue.sh now has both. Aborted files moved to results/attnstats-20260929-w1-aborted-0336Z and logs/*-aborted-0336Z.log.
UPDATE 2026-09-29 04:5x UTC: bfb4cfc4be AMENDED -> 6e23101744 (W1 fix + start latches in the two timed hetero sections + one-claim
sentence splits, per the diff review wf_1f3fe567-f89: 21 raw / 15 confirmed, record new-counters/w1-diff-review-20260929.md);
second LOCAL commit 1059cc1bc2 = audit-gap tests (t_attn_stats: off-state scratch, note_forward_wall off, FPGA leaf values, report
rule + amx/fpga columns, is_safe_model_id, EAGLE off; t_amx_dispatch_dtype: fake available() flag + kill-switch section;
t_llama_unit: stats follow env_enabled after apply_page_range, FUSE comment fixed). Gap register (wf_77ac48c5-d88, 103 claims):
new-counters/test-gap-register-20260929.md (+ -items.json); 12 gaps wait on W2/W4/W5 (A3,A5,A6,A8-A10,A12,A13,A15,A16,A20,A23,B1-B4,
B7-B9), B5 (empty-path visit with stats on) and B11 (nullptr accumulator arm) deferred, B12/B13 machine-only. NOT pushed; PR head
1430736b2a. 3bda queue relaunched for 1059cc1bc2 (NOT_BEFORE 13:00Z). PR BODY: never gh pr edit from pr-body.md (the live body
has jhan's MoE sentence at :10 and a different structure); patch the live body (scratch copy gh-body-live.md, 117 lines: T5 bullet
:22, tests bullet :32) at push time from a fresh fetch; draft pr-body.md updated with PENDING verification bullets to fill.
counter.html section 5.2 (:633/:662/:791 "T5 = FPGA wait") still to regenerate in the combined docs pass (gen_counter.py).
UPDATE 2026-09-29 13:05Z: the 13:00Z queue run of 1059cc1bc2 FAILED at configure in 16 s: t/model_requirement_audit.cmake (t/CMakeLists.txt:876)
rejects a test source that names a KNOWN RUNTIME MODEL SLUG ("ingested-qwen-3-4b-instruct-2507-tp2" in my is_safe_model_id CHECK) without a
MODEL_REQUIREMENTS declaration -> TRAP: never put a real model slug in a test string; use made-up ids. Fixed by amending the audit-tests
commit -> 37bb2a4055 (branch: 1430736b2a -> 6e23101744 -> 37bb2a4055). Queue relaunched 13:04Z (pid 2435301) for 37bb2a4055; the nightly
lease was already clear at 13:00Z today and the i4500 chain's step A build started 13:00:10Z on the same socket (agreed overlap).
Failed run moved to results/attnstats-20260929-w1-configfail-1059cc1bc2.
DONE 2026-09-29 13:16Z: 37bb2a4055 built on 3bda in 636 s (incremental, alongside the i4500 chain's step A), all 5 test binaries pass:
t_llama_unit 219,991/55 (+42), t_page_share_counters 61/4, t_amx_numerics 4,109/4, t_amx_dispatch_dtype 1,600/1 (+11), t_heterogeneous_scheduler
2,715/2 (+815); switch-on runs same counts; TRON_ATTN_STATS=yes warning printed once on a REAL state (t_heterogeneous_scheduler; the script's
t_llama_unit "[attn_stats]" bad-value step never calls env_enabled -> its "warning lines" count was info lines; build-test.sh corrected).
Measured T5 (Catch2 -s): SW-only late arm 54,179,328 cycles = 20.07 ms; mixed-attention HW join 54.13-54.16 M cycles (4 arms); done/off arms 0.
Results exec/results/attnstats-20260929-w1/. pr-body.md verification bullet filled (draft). NOT pushed: PR head 1430736b2a; branch
1430736b2a -> 6e23101744 -> 37bb2a4055; jhan decides push (then patch the LIVE body from a fresh fetch, see the rule above).
UPDATE 2026-09-29 17:3x UTC (W2 approved by jhan, "option b + unit tests to repro Wade's problems"): LOCAL commit c612b82a84
(on 37bb2a4055): attn_stats.hpp gains #include "common/util.hpp" + struct forward_scope (ctor: class store/begin_forward +
T1 start; dtor after the latch guard: note_forward_wall + end_forward), Note T1/class text reworded; model.hpp forward()
declares attn_stats_scope after the TRACE_EVENT, run_forward loses begin/end_forward + gets a "called by forward() only"
comment; h/tron/scheduler/full.hpp == base 66c7bb8db1 again (file leaves the PR). Tests t_attn_stats.cpp (14 cases now):
"forward_scope: one object owns the per-forward record" and "the hooks alone reproduce the half record forward_scope
prevents" (begin/end without wall -> token_jobs 5 / forwards 0; note_forward_wall on a fresh object -> class 0). NOT written:
a direct model::state::forward test (no fixture builds the 13 inputs; t_trace_passes_host goes through the scheduler and
scheduler_t hides the state) -> the runtron 3bda check (forwards 255/8, token_jobs 2040/8192 vs attnstats-20260924b) is the
end-to-end evidence. lcheck gen/gen-amxoff clean, clang-format clean. pr-body.md hooks bullet + tests bullet updated (draft).
3bda queue relaunched 17:34Z (pid 3984692) for c612b82a84 (results dir of 37bb2a4055 moved to -37bb2a4055). Review workflow
launched. Page section 4 carries an "implemented as c612b82a84" note (regenerated, not yet republished; W3/W4 check pending).
DONE 2026-09-29 17:46Z: c612b82a84 built + tested on 3bda (17:35-17:46Z): t_llama_unit 220,016/57 (+25 assertions, +2 cases),
t_page_share_counters 61/4, t_amx_numerics 4,109/4, t_amx_dispatch_dtype 1,600/1, t_heterogeneous_scheduler 2,715/2; switch-on
runs same counts; =yes warning once (corrected bad-value step). Results exec/results/attnstats-20260929-w1/ (previous run in
-37bb2a4055). Branch: 1430736b2a -> 6e23101744 -> 37bb2a4055 -> c612b82a84, NOT pushed. W3/W4 page sections regenerated with
figures + colored diffs and checked (wf_ffa9db0b-45b, 115 findings, 109 confirmed, all applied; facts learned: chunk_evenly
grain = minibatch_grain_size 8 (common.hpp:315), cut depends on affinity-id order; review-round3 page has no "option F";
assertion_signal has a twin in t_compute_attention_unit.cpp:22-34; compile_generated_attention_calls (:163-215) is never run).
UPDATE 2026-09-29 19:0x UTC: W2 commit review (wf_ac63ef8b-687: 28 raw, 19 confirmed = 10 distinct) applied and c612b82a84
AMENDED -> b6fd226982: forward_scope comment (construction order = stamp then begin_forward; "previous forward's class";
no reviewer name in source; exception-unwinding sentence), Note paragraphs reflowed, run_forward comment ("would file rows
under the previous class, path bits folded into the next forward"), test: stale-class repro now uses the object of defect 1
(prompt class stored) + a fresh-state sub-case; fpga_queries CHECK inside the scope; pr-body T1 bullet names forward_scope.
3bda queue relaunched for b6fd226982 (c612b82a84 results moved to -c612b82a84). Page: section 5 gained the sub-section
"Users, forwards, token jobs and minibatches: what each one is in the code" (table of C++ objects + Figures 5 and 6:
w3_fig_layers.svg, w3_fig_timelines.svg; later figures renumbered to 7-12); not yet republished (waiting for the 3bda result
to put the final sha in). Facts: struct batch = common.hpp:990 (items = vector<token_job_id>), q_batches model.hpp:1159,
construct_minibatches :1815-1826, ids common.hpp:145-200, tree walk full.hpp:2330-2478, max_minibatch_size 128 llama.hpp:184.
UPDATE 2026-09-29 18:1x UTC (W3 approved by jhan: "A + E"): LOCAL commit 736952c66f on b6fd226982: forward_counters gains
listener_jobs / kv_only_jobs; begin_forward(cls, n_token_jobs, n_listeners) with TRON_ASSERT_LE(n_listeners, n_token_jobs)
(safe: ensure_listener pushes one listener_index entry per node, full.hpp:2131-2139, called once per node at :2459/:2468);
forward_scope ctor takes n_listeners (model.hpp passes in_listener_index.size()); render_forwards prints the two keys after
token_jobs; Note + model.hpp comment + README (:246-255) carry the continuous-batching sentence (option A). Tests: LISTENERS_ALL_5 /
LISTENERS_1 constants, 14 calls updated, CHECKs added, exact JSON substring updated, hetero install_enabled_stats passes n_jobs.
lcheck gen/gen-amxoff clean on 4 units, clang-format clean. Branch: 1430736b2a -> 6e23101744 -> 37bb2a4055 -> b6fd226982 -> 736952c66f,
NOT pushed. Page: W3 recommendation label says "implemented as 736952c66f"; "What the two counters look like, with an example"
sub-section (Figure 10 = w3_fig_counts.svg; W4/W5 figures now 11-13) published (version 6). 3bda: b6fd226982 run in flight
(18:01Z); queue 736952c66f after it finishes (same results dir). Reading rule for readers: listener_jobs per forward minus users
in prefill = generated tokens hidden per forward in prompt_or_mixed; runtron prompt 1024 8u -> listener_jobs 64 = chunk ends only.
UPDATE 2026-09-29 18:3x UTC: W3 commit review (wf_11b2ce07-4c8: 13 raw, 11 confirmed) applied; 736952c66f AMENDED -> ae8a6d38d9
(one-claim sentences in Note/model.hpp/README/forward_counters comment with continuous batching, prefill and prompt chunk
defined; caveats: a chunk cut by the per-forward token limit gets its listener in the finishing forward (full.hpp:2452-2455),
speculative verify = one listener per draft token; off-state CHECKs for the two keys; LISTENERS_0 token-limit case; leaf-size
case fills the forwards record). VERIFIED against the critic's wrong claim: non-final prompt chunks DO register a listener (empty
logits buffer -> n_empty_listeners in partition_listeners, model.hpp:1779-1786; context.cpp:48); the full.hpp guard is about
edges cut by the token limit. Branch: ... -> b6fd226982 -> ae8a6d38d9 (NOT pushed). 3bda: 736952c66f run in flight (18:12Z,
validates code minus wording/tests); queue ae8a6d38d9 after it. Page version 7 published with the caveat paragraph.
DONE 2026-09-29 18:34Z: ae8a6d38d9 built (585 s) + tested on 3bda: t_llama_unit 220,037/57 (+18 vs b6fd226982), others unchanged
(61/4, 4,109/4, 1,600/1, 2,715/2); switch-on same counts; =yes warning once; live summary carries listener_jobs/kv_only_jobs.
Results exec/results/attnstats-20260929-w1/ (earlier runs in -37bb2a4055, -c612b82a84, -b6fd226982, -736952c66f).
BRANCH STATE: 1430736b2a (PR head on GitHub) -> 6e23101744 (W1) -> 37bb2a4055 (audit tests) -> b6fd226982 (W2) -> ae8a6d38d9 (W3 A+E),
all LOCAL, all 3bda-green. Open: W4, W5 (jhan still reading), push (jhan's call; patch the LIVE PR body from a fresh fetch),
counter.html sections 5.1/5.2/9/13 regeneration, the CPU-attention runtron run for the first software-join T5 and fresh samples.
UPDATE 2026-09-29 19:0x UTC (W4 approved by jhan: option D): LOCAL commit 32b918b681 on ae8a6d38d9: every range guard -> TRON_ASSERT
(row() const + both fpga_at overloads assert; token_path_span(worker, n_token_jobs) asserts once per call; per-visit compare gone;
end_forward asserts both scratch sizes; note_fpga_query asserts; note_token_path DELETED); fixtures open forward_scope
(t_llama_unit :2204 block + check_page_range_reductions std::optional scope with a stats rebuild after attn.resize(4);
t_amx_dispatch_dtype per round; hetero Q-reuse section); path-sets case writes via token_path_span; negative case
"an out-of-range worker, layer or token job aborts" (fork per hook, SIGABRT) using NEW t/assertion_signal.hpp (namespace tron;
copies removed from t_llama_unit.cpp + t_compute_attention_unit.cpp). build-test.sh now also builds/runs t_compute_attention_unit.
lcheck gen/gen-amxoff clean on 5 units; clang-format clean. 3bda queue launched for 32b918b681; review workflow launched.
pr-body.md has the two W4 bullets. Page: W4 label "implemented as 32b918b681" (regenerated, publish after the run).
Branch: ... -> ae8a6d38d9 (W3) -> 32b918b681 (W4), NOT pushed. Open: W5, push, counter.html regen, CPU-attention run.

UPDATE 2026-09-29 20:1x UTC (W4 + W5 done locally, NOT pushed): branch chain now 1430736b2a -> 6e23101744 (W1) -> 37bb2a4055 (audit tests)
-> b6fd226982 (W2) -> ae8a6d38d9 (W3) -> 15f355acb2 (W4, rewritten from 32b918b681: fixup removed the stdlib/unistd/sys-wait
includes the moved assertion_signal helper needed, message split at semicolons) -> ff37c2a64e (W5 B+C+D). 32b918b681 was green
on 3bda (t_llama_unit 220,066/58; hetero 2,715/2; dispatch 1,600/1; compute 124/4; numerics 4,109/4; results dir
exec/results/attnstats-20260929-w1-32b918b681). ff37c2a64e queued on 3bda 20:06Z (queue pid 2883790, build-test.sh, results in
exec/results/attnstats-20260929-w1/), review workflow wf_c3fe3a20-00e. W5 design as committed: rows/path_bits keyed by pool worker
via model_stats::pool_worker(attn_ix, n_attn_workers) (asserts both), NO_WORKER placeholder in the off path; layer_timers
[class][layer] (T3/T4, 64 B each, worker_layer_row stays 192 B); note_attn_job(worker, layer, busy) + note_attn_job_wall_w0(layer,
wall); note_attn_workers(n) from assemble_attention_plan_impl (once per forward, llama.hpp:596) -> forward_n_attn_workers
(UNKNOWN_SPLIT = fold every row) + n_attn_workers_min/max in the forwards leaf (min printed 0 while max == 0); put_counts(out, s,
with_layer_timers) drops the *_w0 keys from the worker leaf. Tests: t_attn_stats 20 cases (pool_worker, split-moves exposing case,
restricted fold, 5 new abort checks, leaf key presence), t_llama_unit fake-lane case checks the last pool row then a 2-worker split
call (after the numeric loop, so the ratio check is untouched). TRAPS: (1) autosquash without an editor:
GIT_SEQUENCE_EDITOR=script that seds "pick X"->"reword X", GIT_EDITOR=script that cps the message file, -c core.hooksPath=/dev/null;
verify "git diff <pre-rebase-head> HEAD" is empty; (2) a fixup hunk that touches lines a later commit also edits conflicts on
replay: keep such hunks in the later commit; (3) t_attn_stats path-set indices: set index = OR of path_bit() values (1<<path).
Still open: 3bda result of ff37c2a64e, review findings, pr-body verification rows for 15f355acb2/ff37c2a64e, push (jhan's word),
PR replies to Wade (drafts on the page), counter.html regeneration, CPU-attention runtron run for fresh leaf samples.

UPDATE 2026-09-29 20:3x UTC: ff37c2a64e FAILED on 3bda (t_attn_stats :199 expected _forwards string lacked the two new keys; :749/:761
wrong histogram indices: set index = OR of PATH_BIT_* values, NOT 1<<visit_path) -> amended to bff317e0d3 (test-only fix + README/Note
sentence splits + WARN branches for 1-worker pools + braces); queued on 3bda 20:2x UTC (results exec/results/attnstats-20260929-w1/,
failed run archived as -ff37c2a64e-failed). Review wf_c3fe3a20-00e: 12 findings, 9 held, all applied. TRAP: the review predicted the
:749/:761 failures but not :199 (a render-string CHECK in an OLD case breaks whenever render_forwards gains a key) -> grep every
render_*(...).find(" literal in t_attn_stats.cpp when a leaf gains a key.

UPDATE 2026-09-29 20:35 UTC: bff317e0d3 GREEN on 3bda (t_llama_unit 220,146/61; hetero 2,715/2; dispatch 1,600/1; compute 124/4;
numerics 4,109/4; page_share 61/4; switch-on + bad-value runs ok; 55 app-pool workers there, so both fake-lane pool-row checks ran).
ALL FIVE Wade comments implemented locally: chain ... -> ae8a6d38d9 (W3) -> 15f355acb2 (W4) -> bff317e0d3 (W5). NOTHING PUSHED; PR
head on GitHub still 1430736b2a. Remaining for jhan: push order, reply to Wade's five threads (drafts on the page), then patch the LIVE
PR body from a fresh fetch (never from pr-body.md directly), counter.html regeneration, CPU-attention runtron run for fresh samples.

UPDATE 2026-09-29 21:0x UTC: PUSHED. PR #4596 head = bff317e0d3 (fast-forward from 1430736b2a, six commits). LIVE PR BODY TRAP: jhan
rewrote the GitHub body into a SHORT form (117 lines: Short version / Not in this PR (MoE) / Words used here (visit, forward) / Timers /
Doc and tests / Why one env var / A/A / Cross-checks / Leaves / Verification (round 3 only) / Cost data / Refs). The local pr-body.md
(161 lines, long form) is NOT the live body any more; treat it as history. Round-4 body change = a patch on the live text, proposed on
the page (section 11 of respond-Wade-comments.html) and saved as PR3879/new-PRs/new-counters/pr-body-round4.md; apply with gh pr edit
--body-file ONLY after jhan approves, after a fresh fetch and diff. Wade replies: rewritten as done-state drafts on the page (not posted).

UPDATE 2026-09-29 23:4x UTC: CPU-attention runs DONE (exec/results/attnstats-20260929-cpu and -cpu2, wrapper
exec/attnstats-20260929-w1/cpu-cell.sh = campaign.sh + leaf poller): forwards 255/8, token_jobs 2040/8192 (= 09-24), listener 2040/64,
kv_only 0/8128, split 20/20, T5 SW join 2.03 G cycles decode (4.1 us/job, 2.1 % of T2) / 5.37 G prefill (345 us/job, 10.2 %), T1 12.5 ms/step,
worker leaves 0-6 zero, 7-26 attention rows (snapshot cpu2/leaves-latest/, 131 leaves at decode forward 142). FINDING (open, not fixed):
live reads mid-forward show listener_jobs + kv_only_jobs ahead of token_jobs by the in-flight forward (begin_forward adds the two,
end_forward adds token_jobs); fix = add all three in end_forward (store n_listeners in begin_forward). TRAPS: (1) pkill -f '<pattern>'
inside an ssh command line kills the ssh shell itself when the command line contains the pattern (use 'cpu-ce[l]l' style and keep launch
and kill in separate ssh calls); (2) guard takeover rule: rinzler's idle SYSTEM_STATS line is followed by 2 more #EVT# lines, so "last line
idle" never matched -> lib-guard.sh now probes the last 6 lines (bak-20260929); (3) a 35 s runtron run needs a 1 s leaf poller (10 s missed it);
(4) campaign.sh still shows the i4525 header text in rt-results.txt (cosmetic). Proposed PR body pr-body-round4.md now carries the new samples.

UPDATE 2026-09-30 00:0x UTC: job-count fix committed as 04da001cb5 (tested on 3bda as 8670da7f0b, comments-only difference; t_llama_unit
220,158/62, all green), review wf_bbac4876-428 (8 findings, 6 prose ones applied), PUSHED -> PR #4596 head 04da001cb5 (7 commits on top of
1430736b2a). Proposed PR body pr-body-round4.md + page section 11 updated. Still not done: gh pr edit (jhan's word), Wade thread replies,
counter.html regeneration.


UPDATE 2026-09-30 ~23:55 UTC: PR #4596 APPROVED by Wade at 441e81178b; conflicts with main resolved by MERGING main (merge commit 8c95514924 = new PR head, pushed); details and the merge recipe in [[wade-pr4596-round5-response]] and [[git-rebase-traps]] item 6.
