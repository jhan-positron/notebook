# Adversarial review of the W1 commit (bfb4cfc4be, before amend) of PR 4596 (workflow wf_1f3fe567-f89, 2026-09-29 04:2x UTC)

6 finder lenses, 2 refuters per finding, 1 critic. 21 raw findings, 15 confirmed by both refuters.

## Critic

Short version: two must-fix items, both in the PR body draft (the draft would overwrite jhan's live GitHub edits, and the tests bullet does not name the W1 tests). One code change is worth landing before the machine run: a start latch in the two timed test sections, so the T5 > 0 checks stop depending on thread start latency. The review missed a multi-head software-join test, the objdump count for the new build, and the fact that the queued 3bda run points at bfb4cfc4be, so a new commit needs a repoint before 13:00Z.

Words used here: T5 = `join_wait_cycles`, the cycles a join worker spends waiting with no join progress. run_joins / stream_hw_joins = the join functions in h/tron/models/self_attention.hpp. hetero test = t/heterogeneous_scheduler_compile.cpp (binary t_heterogeneous_scheduler). pr-body.md = /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/pr-body.md, the local draft of the PR 4596 body. counter.html = the design page in the same folder. W1 = Wade's review comment "T5 misses the software join poll".

## Must-fix

1. pr-body.md is not a safe source for `gh pr edit` (pr-body.md:141-143; finding "Draft body diverges"). The live body has jhan's "Not in this PR" MoE sentence and a shorter structure. The draft has neither.
   Change: never run `gh pr edit --body-file pr-body.md`. Fetch the live body (`gh pr view 4596 --json body -q .body > gh-body.md`), then apply three edits to that file: replace live line 22 (old T5 text) with draft line 36; append to live line 10 (the MoE paragraph) the sentence "A fresh CPU-attention run for the software-join T5 is pending; the sample under \"What the leaves look like\" predates that fix and reads join_wait_cycles 0."; replace the live tests bullet (line 32) with the text in item 2. Then `gh pr edit 4596 --body-file gh-body.md`. Also add the MoE sentence verbatim to draft line 143 so the draft stops diverging: "MoE models are not specifically scoped, it is likely MoE stats are not covered. Will add when AMX feature extends to MoE."

2. Tests bullet says the two files only "follow the new parameters" (pr-body.md:56). It must name the W1 tests.
   Change, replace line 56 with two bullets:
   "- `t/heterogeneous_scheduler_compile.cpp`: a helper installs an enabled stats object in place of the state's own (the binary mounts no FUSE tree, so no leaf callback holds the old object). The mixed-attention section runs `run_joins` with stats on and checks the hardware join's T5: greater than 0 and at most the join's wall time. A new section runs `run_joins` with no hardware plan against a producer that finishes 20 ms late, in three arms: late producer with stats on (T5 greater than 0 and at most the wall time), sections already done (T5 = 0), late producer with the call's stats flag off (T5 = 0). The join result is checked in every arm."
   "- `t/t_llama_unit.cpp`: the two direct `stream_hw_joins` cases pass a real accumulator and check 0, because every sweep there makes progress and that function's wait loop is never entered."

## Should-fix

Code (do this one before the 3bda run, because that run is the first execution of these sections):

1. T5 > 0 checks depend on the async thread starting within 20 ms (hetero test :453 and :533; three findings, two refuters each say should-fix). The file already uses `std::latch` for this in the Q-reuse section (:641-650), and `<latch>` is included (:9).
   Change in the software-only section (around :515-527):
   ```cpp
   std::latch joining(1);
   auto worker = std::async(std::launch::async, [&] {
     joining.count_down();  // the 20 ms wait below starts at worker entry
     state->self_attn_state.run_joins<geometry>(
         &q_batch, operation, output, 0, 2, /*uses_hw=*/false, stats_enabled);
   });
   if (late) {
     joining.wait();
     // The worker must still be polling after 20 ms; then release it.
     CHECK(worker.wait_for(std::chrono::milliseconds(20)) ==
           std::future_status::timeout);
     produce_software();
   }
   ```
   Same shape in the mixed section (around :424-440): declare `std::latch joining(1);` before `std::async`, `joining.count_down();` as the lambda's first line, and `joining.wait();` right after the `std::async` call, before the `if (hardware_first)` spin. Add one comment line: "The latch narrows the window to a preemption between lambda entry and the first poll; it does not close it."

Docs and PR body:

2. Off-state sentence (self_attention.hpp:1263). Replace "Off state: no rdtsc, one test of a stack bool per poll." with "Off state: no rdtsc; one test of stats_enabled per failed poll and one test of poll_waiting per kv head joined (also in the hardware join, where the poll is skipped)."

3. One claim per sentence (attn_stats.hpp:37-42, :220-222; README.stats.md:260-266). Replace the Note sentence with: "T5 = time a worker waits in the join with no join progress. It is measured in both join modes. In a hardware join it is the wait loop of stream_hw_joins, which ends when an FPGA pass or the peer workers' software partials become ready. In a software-only join it is the stretches of failed polls on the peer workers' sections in run_joins. T5 is inside T2 in both modes. T2 minus T5 is compute plus fold." Same split in the README, with the semicolon removed. Field comment: "T5: cycles this worker spent waiting in the join with no join progress. Hardware join: the wait loop. Software-only join: the failed polls."

4. t_llama_unit.cpp:2824. Replace "T5 (join_wait_cycles) counts only the wait loop, which a sweep that made progress never enters" with "Inside stream_hw_joins, T5 counts only its wait loop, which a sweep that made progress never enters".

5. Literal classes (pr-body.md:58; self_attention.hpp:1270/:1277; hetero test :300-301, :514, :519, :523). Cheapest correct fix: extend the sentence at :58 with ", state-flag assignments (`= true` / `= false` on a bool declared with a name, the `poll_waiting` stretch flag), and test fixture values in the two scheduler sections and `t_attn_stats.cpp` (head counts, batch sizes, section counts, partial values, expected outputs, the 20 ms grace, and the positional `worker_ix`, `n_attn_workers`, `uses_hw` arguments of `run_joins`)". If naming is preferred instead, add `constexpr bool USES_HW_FALSE = false;` beside `STATS_ENABLED_TRUE` and use it at :519.

6. Hooks bullet (pr-body.md:43). Replace with: "- `stream_hw_joins` gets a `uint64_t*` accumulator (nullptr when off) and times only its wait loop (hardware join). `run_joins` owns the accumulator: with no hardware plan it times the poll on `sections_left` as stretches (rdtsc at the first failed poll after the last join progress, rdtsc at the next successful poll) into the same local, then records the sum per job with `note_join_wait`. Off state: no rdtsc, one bool test per poll."

7. Verification list (pr-body.md:134). Add two bullets after :134: "- delphi-3bda build and tests of 1430736b2a (2026-09-26, incremental): `t_llama_unit` 219,949 assertions in 55 cases (+12: the bot-fix checks), the other four binaries unchanged. All pass, also with `TRON_ATTN_STATS=1`." and "- delphi-3bda build and tests of the T5 software-join fix: pending (after CI). The new section adds assertions to `t_heterogeneous_scheduler` (still 2 cases) and two assertions to `t_llama_unit`; the counts above stop at 1430736b2a." Do not carry 1,900 / 219,937 forward.

8. "Final commit" wording (pr-body.md:83, :88, :89, :91, :112, :127, :133). Replace "the final commit cbf1bb6c0c" with "the 2026-09-24 commit cbf1bb6c0c (the last before the review-round fixes)". Append to :91 and :95: "The T5 fix adds two rdtsc reads to `run_joins`, both behind the stats bool; `run_joins` is compiled out of line, so the `run_attention_job` count is unchanged. The objdump check on that build is pending." (The out-of-line fact comes from nm on two local builds, cited in the refuter's verdict; the pending objdump run confirms it.)

9. Sample note (pr-body.md:112). Append after "The `prompt_or_mixed` class is the 8 prefill forwards.": "The run predates the T5 fix, so `join_wait_cycles` reads 0: the software-only poll was not timed then (review round 4, W1)." Move the pending-run sentence from :143 into the Verification list as the pending bullet of item 7, and append to the FPGA sentence at :143 "(the hardware join's T5 now has a unit check in t_heterogeneous_scheduler)".

10. counter.html. Add to the section-13 bullet at :853 a dated note: "Review round 4 (2026-09-29, W1): run_joins now also times the software-only poll on sections_left as stretches into the same accumulator; T5 covers both join modes." Add round 4 to the review-rounds bullet at :857. Add one "Superseded 2026-09-29: T5 covers both join modes" note under the 5.2 row at :662 and at :791; leave the figure label at :633 with the same note in its caption.

## What is missing from the review

1. No test drives a software-only join with two kv heads on one worker. The commit message's claim "folding head B while head A is pending is work, so stretches never overlap and the sum stays below wall" has no test. Proposed section: `kv_heads_to_join[0] = {0, 1}`, `sections_left = {0, 1}` at start, release head 1 after 20 ms; check T5 > 0, T5 <= wall, and both heads' outputs. Precondition to check first: whether the test geometry and `plan.n_sections` allow two kv heads; if not, state the gap in the PR body.

2. No test writes T5 for a worker other than worker 0. `note_join_wait` indexes the row by `worker_ix` [attn_stats.hpp:426]; the test passes `worker_ix = 0` in every arm. A one-arm variant with `worker_ix = 1` (and `kv_heads_to_join[1]`) would cover the row index.

3. The stats-off arm tests a state production cannot reach. `run_attention_job` copies `stats_ref.enabled` once [self_attention.hpp:804] and passes it to `run_joins` [:842-843], so the call flag and the object flag always agree in production. The arm is still useful (it proves the flag gates the rdtsc), but the PR body should say the object-disabled off state is covered by the switch-unset 3bda runs, not by this arm.

4. The objdump off-state check counts rdtsc only inside `run_attention_job` symbols (exec/attnstats-20260924/objdump-check.sh). `run_joins` is out of line, so the two new reads land in `run_joins` symbols and the script would report "unchanged". Extend the script to also count rdtsc in `run_joins` symbols (expected: 2 before the fix from the inlined `stream_hw_joins`, 4 after), and record both numbers.

5. The queued 3bda chain (exec/attnstats-20260929-w1/queue.sh, NOT_BEFORE 13:00Z, per project memory) builds bfb4cfc4be. If the latch fix in should-fix 1 lands as a new commit, repoint queue.sh to the new head before 13:00Z, or the machine tests the old commit. The other session's chain (i4500fix) takes the same flock after ours; a repoint does not change that agreement.

6. The review did not examine the hetero binary's run with `TRON_ATTN_STATS=1` (the PR body says that arm is run). `install_enabled_stats` then replaces an enabled env object; the refuters showed it prints nothing because it counted no forwards or visits. That is a reasoned claim, not a measurement. The pending 3bda run should grep the switch-on log of t_heterogeneous_scheduler for `[attn-stats]` lines and record the count (expected 0).

7. The refuted "T2 minus T5 hides the output-channel wait" findings agree the `start_writing` barrier inside T2 is a non-wait only because llama.hpp prepares the channel before the KV jobs. No comment records that ordering dependency. One clause in the Note would do: "(the output channel's start_writing sits inside T2; it is a non-wait because the channel is prepared before the KV jobs the K/V wait depends on)". Optional.

## Confirmed findings

### Late-producer T5 > 0 checks depend on thread start latency under 20 ms (nit -> nit) heterogeneous_scheduler_compile.cpp:533

CHECK(sums.join_wait_cycles > 0) in the late_producer_stats_on arm (and the same check for the hardware join at :453) passes only if the std::async worker thread reaches its first failed poll before the test thread's 20 ms wait_for expires and produce_software() stores sections_left = 0. If thread creation on a loaded CI host is delayed past 20 ms, the worker's first poll succeeds, no stretch opens, T5 = 0, and the CHECK fails while the 20 ms timeout CHECK at :523 still passes (the worker has not finished).

Evidence: t/heterogeneous_scheduler_compile.cpp:520-533: worker launched with std::async at :520, produce_software() at :525 after a 20 ms wait_for at :523; h/tron/models/self_attention.hpp:1268-1272 opens a stretch only on a failed poll. Thread start latency is normally well under 1 ms, so the risk is low; it is the same timing assumption the pre-existing mixed-attention section already makes with hardware_progressed / waiting_for_other (:440-448). Not compiled or run in this review.

Fix: Optional: make the late arm robust by having the worker signal (atomic flag or latch) that run_joins has been entered before the test thread starts its 20 ms wait, or accept the existing assumption and document it in the section comment.

### T5 > 0 checks depend on the async worker starting within the main thread's 20 ms wait (should-fix -> should-fix) heterogeneous_scheduler_compile.cpp:533

Under heavy load the std::async worker can start more than 20 ms after launch. Then the main thread runs produce_software (or produce_hardware in the mixed section with hardware_first=false) before the worker's first poll. The worker's first poll succeeds, no stretch is opened, join_wait_cycles stays 0 and CHECK(sums.join_wait_cycles > 0) fails. The existing 20 ms timeout CHECK cannot fail this way (the worker cannot finish before the producer), so this is a new load-sensitive assumption.

Evidence: t/heterogeneous_scheduler_compile.cpp:517-527 launches the worker, waits 20 ms, then calls produce_software; :533 requires join_wait_cycles > 0. The stretch opens only on a failed poll: h/tron/models/self_attention.hpp:1268-1272 (`if (!join_hw && plan_state.sections_left[kv_head]) { if (stats_enabled && !poll_waiting) { ... t_poll = rdtsc(); } continue; }`). The same pattern in the mixed section: :425-445 (wait_for 20 ms, then the second producer) and :453 (`CHECK(sums.join_wait_cycles > 0)`), exposed for hardware_first=false because only the hardware_first=true arm first waits for unpack_state == 2 (:432-437).

Fix: Have the async lambda signal it has entered (std::latch or std::atomic_flag set just before run_joins) and make the main thread wait on that signal before its 20 ms wait_for. The exposure then shrinks from thread-creation latency to the few microseconds between lambda entry and the first poll.

### T5 > 0 CHECK depends on the async worker starting within 20 ms (should-fix -> should-fix) heterogeneous_scheduler_compile.cpp:453

In the mixed section with hardware_first=false, and in the software-only late arms (line 533), the new CHECK(join_wait_cycles > 0) fails if the std::async thread has not reached its first sweep/poll before the 20 ms wait_for expires; the pre-existing timeout CHECK passes in that case, so this is a new flake vector on a loaded CI host.

Evidence: The producer runs right after worker.wait_for(20 ms) times out [lines 440-444 and 523-526]. If the worker thread starts late, its first sweep already sees both producers ready: stream_hw_joins finishes every job in sweep 1 and never enters the wait loop (self_attention.hpp:1062-1123), and run_joins' first poll succeeds so no stretch opens (self_attention.hpp:1268-1272). T5 is then 0. Only hardware_first=true is protected by the 2 s spin on hw_attn[1].unpack_state[1] == 2 [lines 431-438].

Fix: Set a std::atomic<bool> started inside each async lambda before calling run_joins, spin on it in the main thread, then do the 20 ms wait_for; this makes the 20 ms window start at worker entry instead of at std::async.

### Design page and PR-body draft still define T5 as the FPGA wait only (should-fix -> should-fix) counter.html:662

After this commit the code comments say T5 covers both join modes, but the design page counter.html and one line of the pr-body.md draft still say T5 is the FPGA pass wait, timed only in stream_hw_joins and only under FPGA attention. A reader who checks the code against the design page finds a contradiction.

Evidence: counter.html:633 figure label "T5 hw_join_wait (CPU waits for the card)"; :662 (table 5.2) "CPU time an attention worker spends waiting for FPGA pass completion; splits T2 into compute and waiting on the card"; :791 "two rdtsc per job; only under FPGA attention"; :853 "stream_hw_joins times only its wait loop into an accumulator run_joins passes ... for T5". pr-body.md:43 still reads "stream_hw_joins ... times only its wait loop. run_joins passes it and records the sum per job", while pr-body.md:36 was updated to the both-modes definition.

Fix: Add a dated note to counter.html section 5.2 and the :853 bullet ("review round 4, W1: T5 now also times the software-only poll in run_joins"), and update pr-body.md:43 to "run_joins also times its own poll on sections_left (software-only join)". Patch the live GitHub body from a fresh fetch, not from the draft.

### New literals outside the PR body's listed C++-guide exception classes (should-fix -> should-fix) self_attention.hpp:1270

The repo C++ guide (cpp-coding-guide skill: named constexpr values, true/false/0/1 included, list every exception) is applied by exception list in pr-body.md:58. The added lines carry literals that fall in none of the listed classes (loop starts, zero-initializers, return true/false in predicates, emptiness tests). The declarations `bool poll_waiting = false;` and `t_poll = attn_stats::UNSET_CYCLES_0` themselves are fine: they match `bool any_ready = false;` (:1134), `bool software_ready = false;` (:1063) and `t_wait` (:1133), and zero-initializers are a listed exception.

Evidence: self_attention.hpp:1270 `poll_waiting = true;` and :1277 `poll_waiting = false;` are state assignments, not initializers (the file's own `progressed = true` at :1078 is pre-existing, not on added lines). t/heterogeneous_scheduler_compile.cpp:300-301 `facts.n_kv_heads = 1; facts.kv_mul = 1;` (ones, not zero-initializers); :514 `plan.sections_left[0] = 1;`; :519 `/*uses_hw=*/false` while the sibling section on :427 uses the named `STATS_ENABLED_TRUE` beside a bare `true` on the same line the commit rewrote; :523 `std::chrono::milliseconds(20)` (the 20 ms grace, also at :440, :649, :652 pre-existing).

Fix: Either name them (`constexpr bool USES_HW_FALSE = false;`, `constexpr size_t ONE_SECTION_LEFT_1 = 1;`, `constexpr auto POLL_GRACE_20MS = std::chrono::milliseconds(20);`, `constexpr size_t KV_HEADS_1 = 1;`) or extend the exception list in the PR body with "state-flag assignments (= true / = false on a bool that was declared with a name) and test fixture values (= 1, the 20 ms wait)".

### Reworded T5 sentences carry several claims each and use a semicolon (nit -> nit) attn_stats.hpp:37

The plain-English rules (one claim per sentence, no semicolon) apply in full to code comments and to README prose. The new T5 definition is one sentence with four claims in the Note and one sentence with a semicolon in the README.

Evidence: attn_stats.hpp:37-42: "T5 = time a worker spends waiting in the join with no join progress, in both join modes: in a hardware join the wait loop of stream_hw_joins (it ends when ...), in a software-only join the stretches of failed polls on the peer workers' sections in run_joins." README.stats.md:260-265: "... in both join modes: in a hardware join, the wait loop that ends when an FPGA pass or the other workers' software partials become ready; in a software-only join (CPU attention), the stretches of failed polls ...". The field comment (:220-222) has the same shape.

Fix: Split: "T5 = time a worker waits in the join with no join progress. It is measured in both join modes. In a hardware join it is the wait loop of stream_hw_joins, which ends when an FPGA pass or the peer workers' software partials become ready. In a software-only join it is the stretches of failed polls on the peer workers' sections in run_joins. T5 is inside T2 in both modes." Same split in README.stats.md.

### t_llama_unit comment says T5 "counts only the wait loop", which the Note no longer says (nit -> nit) t_llama_unit.cpp:2824

The comment reads as a definition of T5 ("T5 (join_wait_cycles) counts only the wait loop"). After this commit T5 also counts the software-only poll in run_joins, so the sentence contradicts the Note when read alone.

Evidence: t/t_llama_unit.cpp:2824-2825 vs attn_stats.hpp:37-42 and self_attention.hpp:1257-1263. The call at :2828 is stream_hw_joins, so the intended scope is that function's loop.

Fix: Scope the sentence: "Inside stream_hw_joins, T5 counts only its wait loop, which a sweep that made progress never enters ...".

### Off-state cost sentence names the wrong bool and misses the per-head test (nit -> nit) self_attention.hpp:1263

The comment says "Off state: no rdtsc, one test of a stack bool per poll." On a failed poll the test is of `stats_enabled` (a function parameter), and on every successful poll, also in the hardware join where the poll itself is skipped, `if (poll_waiting)` runs once per kv head. Reviewers of this PR asked for exact off-state costs (Note: "Off-state contract" at attn_stats.hpp:14-17), so the sentence should match the code.

Evidence: self_attention.hpp:1269 `if (stats_enabled && !poll_waiting)` on the failed-poll path; :1275 `if (poll_waiting)` on the path taken by every successful poll, including when join_hw is true (the `!join_hw &&` at :1268 skips only the poll, not :1275).

Fix: "Off state: no rdtsc; one test of stats_enabled per failed poll and one test of poll_waiting per kv head joined."

### Draft body diverges from the live GitHub body; pushing the draft overwrites jhan's edits (must-fix -> must-fix) pr-body.md:141

The live body of PR 4596 (fetched today with gh pr view) was restructured by jhan and no longer matches the draft: its 'Not in this PR' section is one sentence about MoE models, it has no 'What changes'/'Hooks' lists, no C++ guide paragraph, and its Verification list holds only the round-3 bullet. The draft's 'Not in this PR' paragraph at :141-143 does not contain the MoE sentence, so a `gh pr edit --body-file pr-body.md` would delete it (the 2026-09-25 trap in memory pr-body-refetch-before-edit).

Evidence: Live body lines 1-10 (scratchpad gh-body.md): '## Short version ... Perf impacts are neglectable. ## Not in this PR MoE models are not specifically scoped, it is likely MoE stats are not covered. Will add when AMX feature extends to MoE.' Live :22 still has the old T5 text 'the time a worker spends in the join's wait loop'. Draft :141-143 has no MoE sentence.

Fix: Patch the live body, not the draft: replace live :22 with the draft's :36 T5 bullet; replace live :32 (tests bullet) with the new tests text (finding on :56); append to the live 'Not in this PR' paragraph (:10) the sentence 'A fresh CPU-attention run for the software-join T5 is pending; the sample under "What the leaves look like" predates that fix and reads join_wait_cycles 0.' If the draft stays the source, add jhan's MoE sentence to draft :143 verbatim: 'MoE models are not specifically scoped, it is likely MoE stats are not covered. Will add when AMX feature extends to MoE.'

### Hooks bullet still says only stream_hw_joins times the join; contradicts the T5 bullet (must-fix -> should-fix) pr-body.md:43

Line 43 describes the T5 hook as 'stream_hw_joins ... times only its wait loop. run_joins passes it and records the sum per job.' After bfb4cfc4be run_joins also times the software-only poll, so :43 says less than :36 and a reader sees two different mechanisms.

Evidence: h/tron/models/self_attention.hpp:1262-1279 (worktree): `bool poll_waiting = false; uint64_t t_poll = ...; if (!join_hw && plan_state.sections_left[kv_head]) { if (stats_enabled && !poll_waiting) { poll_waiting = true; t_poll = rdtsc(); } continue; } if (poll_waiting) { join_wait_cycles += rdtsc() - t_poll; ... }`; :1323-1326 passes `stats_enabled ? &join_wait_cycles : nullptr` to stream_hw_joins; :1335 `note_join_wait(worker_ix, layer.i, join_wait_cycles)`.

Fix: Replace :43 with: '- `stream_hw_joins` gets a `uint64_t*` accumulator (nullptr when off) and times only its wait loop (hardware join). `run_joins` owns the accumulator: with no hardware plan it times the poll on `sections_left` as stretches (rdtsc at the first failed poll after the last join progress, rdtsc at the next successful poll) into the same local, then records the sum per job with `note_join_wait`. Off state: no rdtsc, one test of a stack bool per poll.'

### Tests bullet for heterogeneous_scheduler_compile.cpp and t_llama_unit.cpp omits the T5 tests added for W1 (must-fix -> must-fix/should-fix) pr-body.md:56

Line 56 says the two files only 'follow the new run_joins and stream_hw_joins parameters'. bfb4cfc4be adds a new section with three GENERATE arms, a T5 check in the mixed-attention section, an install_enabled_stats helper, and two CHECK(join_wait_cycles == 0) in t_llama_unit. These are the unit tests that close the W1 gap and the body does not mention them.

Evidence: t/heterogeneous_scheduler_compile.cpp:293-312 (install_enabled_stats), :419-455 (mixed-attention section: CHECK(sums.join_wait_cycles > 0); CHECK(sums.join_wait_cycles <= join_wall)), :463-543 (SECTION 'software-only join times its wait for the peer sections (T5)', GENERATE of late_producer_stats_on / sections_done_stats_on / late_producer_stats_off at :507). t/t_llama_unit.cpp ~:2826-2832 and ~:2880-2886 (real accumulator, CHECK(join_wait_cycles == 0)).

Fix: Replace :56 with: '- `t/heterogeneous_scheduler_compile.cpp`: a helper installs an enabled stats object in place of the state's own (the binary mounts no FUSE tree, so no leaf callback holds the old object). The mixed-attention section runs `run_joins` with stats on and checks the hardware join's T5: greater than 0 and at most the join's wall time. A new section runs `run_joins` with no hardware plan against a producer that finishes 20 ms late, in three arms: late producer with stats on (T5 greater than 0 and at most the wall time), sections already done (T5 = 0), late producer with the call's stats flag off (T5 = 0). The join result is checked in every arm.\n- `t/t_llama_unit.cpp`: the two direct `stream_hw_joins` cases pass a real accumulator and check 0, because every sweep there makes progress and T5 counts only the wait loop.'

### Verification list has no entry for bfb4cfc4be and its test counts predate the new section (must-fix -> should-fix) pr-body.md:134

The last Verification bullet (:134) ends at d85edc0e28 and reports `t_heterogeneous_scheduler` 1,900 assertions in 2 cases and `t_llama_unit` 219,937 in 55. bfb4cfc4be adds assertions to both binaries (three GENERATE arms x (2 x 128 output checks + T5 checks + one wait_for check) in the hetero binary, two CHECKs in t_llama_unit), so those counts no longer describe the head. The case count of the hetero binary stays 2 (the addition is a SECTION, not a TEST_CASE). The 3bda run has not happened, so no new numbers exist.

Evidence: pr-body.md:134 'same counts at every build: ... t_heterogeneous_scheduler 1,900 in 2'; t/heterogeneous_scheduler_compile.cpp:463 SECTION (not TEST_CASE), :507 GENERATE with three arms, :537-541 per-arm output loop over query_width(); t/t_llama_unit.cpp CHECK(join_wait_cycles == 0) twice. Also 1430736b2a (the bot fix, PR head) has no Verification bullet either.

Fix: Add after :134, with the counts left blank until the run: '- delphi-3bda build and tests of 1430736b2a and bfb4cfc4be (T5 software-join fix): pending. The counts above stop at d85edc0e28; the new section adds assertions to `t_heterogeneous_scheduler` (still 2 cases) and two assertions to `t_llama_unit`. To be filled from the run after CI.' Do not carry the 1,900 / 219,937 numbers forward as the head's counts.

### 'Final commit' / 'final binary' wording and the rdtsc count of run_attention_job now point at a superseded commit (should-fix -> nit/should-fix) pr-body.md:91

Lines 83, 91, 112 and 127 call cbf1bb6c0c 'the final commit' and :91 'the final binary'. After bfb4cfc4be that is no longer the final commit. :91 and :95 report 9 rdtsc reads in the largest `run_attention_job` instantiation; run_joins is a template member called from run_attention_job and now holds two more rdtsc reads, so that count needs a re-measure on the new build (an inlined run_joins changes it). No new number exists yet.

Evidence: pr-body.md:83 'Confirmation round on the final commit cbf1bb6c0c'; :91 'The final binary's instruction counts ... run_attention_job ... 9 rdtsc reads'; :95 'from 8 to 9 rdtsc reads. The added read runs only with the switch on.' self_attention.hpp:842 run_joins call inside run_attention_job; :1271 and :1276 new rdtsc reads.

Fix: :83 'Confirmation round on cbf1bb6c0c (the last commit before the round-3 and round-4 fixes), ...'. :91 'The instruction counts of the cbf1bb6c0c binary: ...' and append 'bfb4cfc4be adds two rdtsc reads to `run_joins`, both behind the stats bool; the objdump check on that build is pending.' :95 append the same pending sentence after 'The added read runs only with the switch on.' :112 and :127 keep 'The final commit' only if replaced by 'The current code' (both statements still hold at head).

### Sample shows join_wait_cycles 0 with no note at the sample; the explanation sits under 'Not in this PR' (should-fix -> should-fix) pr-body.md:119

The stderr sample at :115-125 shows `"join_wait_cycles":0` for a CPU-attention run. The only explanation is at :143, 24 lines later, inside the scope section 'Not in this PR'. A pending re-run is a verification status, not a scope exclusion, and the user plans that run after CI.

Evidence: pr-body.md:119 '"join_wait_cycles":0'; :143 'A fresh CPU-attention run for the software-join T5, which the sample above predates (its join_wait_cycles 0 is the untimed software poll of review round 4, W1).'

Fix: Add one sentence to :112 after 'The prompt_or_mixed class is the 8 prefill forwards.': 'The run predates bfb4cfc4be, so `join_wait_cycles` reads 0: the software-only poll was not timed then (review round 4, W1).' Move the sentence 'A fresh CPU-attention run for the software-join T5 ...' from :143 into the Verification list as a pending bullet: '- CPU-attention run of bfb4cfc4be with `TRON_ATTN_STATS=1` to show a non-zero `join_wait_cycles` on the software-only join: pending.' Keep 'Runtime evidence for the FPGA counters and for T5 in the hardware join' at :143 and append '(the hardware join's T5 now has a unit check in t_heterogeneous_scheduler)'.

### C++ guide paragraph does not list the literal classes the new tests add (should-fix -> should-fix) pr-body.md:58

Line 58 claims to list every class of literal left unfixed on the added lines (loop starts, zero-initializers, return true/false, emptiness tests). bfb4cfc4be adds test-fixture values (`= 1`, `resize(2)`, `values{0, 2}`, `worker < 2`) and commented literal arguments (`/*uses_hw=*/false`, positional `0, 2, true` in the run_joins call) that fall in none of the four listed classes. The memory rule for this reviewer set: pass the guide verbatim and list every class left unfixed.

Evidence: t/heterogeneous_scheduler_compile.cpp:471-472 `output.resize(2); state->resize(2);`, :480 `plan.n_sections = {0};`, :490 `constexpr std::array<float, 2> values{0, 2};`, :498 `partial[0].s_star = 1;`, :512 `plan.sections_left[0] = 1;`, :517 `&q_batch, operation, output, 0, 2, /*uses_hw=*/false, stats_enabled)`, :426-428 `&q_batch, operation, output, 0, 2, true, STATS_ENABLED_TRUE)`.

Fix: Append to :58: ', test fixtures in the two scheduler test sections (batch sizes, section counts, partial values, and the positional `worker_ix`, `n_attn_workers`, `uses_hw` arguments of `run_joins`, some with `/*name=*/` comments, the file's existing idiom).'

