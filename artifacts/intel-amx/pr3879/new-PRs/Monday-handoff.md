# Handoff: PR 3879 split, state at the end of Monday 2026-09-07 (19:45 UTC)

Supersedes `handoff-Sunday.md` (same folder), which is kept for the full history of 2026-09-06 and 2026-09-07 (its
"Update" sections at the top run in chronological order). Read this file first.

## Update 2026-09-08 03:3x UTC: PR 0 out of draft, PR 1 landed on #3879

jhan's decisions: cost data in, PR 0 off draft (he asks Ben for review himself), PR 1 go, post the #3997 correction, PR 2 stays parked.
Done: PR 0 cost-data commit **6c735e63ae** pushed (entry 0.698/0.700/0.696 s, 8 MB), one sentence appended to the PR description
(addition only; jhan owns the text), `gh pr ready 4267`. PR 1: cost data committed on `pr1-stage2` (124b87d800), `make_topical.sh` rebuilt
`jhan-amx-p0-v2` = **fcc78573b0** ("tree identical to tip: yes"; differs from the tested 9723d56f62 only in `config/test-benchmarks.json`,
so no rebuild was run: delphi-3bda was serving rinzler@0-2 and the verify script would have waited); old head 60d66d9c04 pushed as branch
`jhan-amx-p0-pre-split`; the force-push itself was run by jhan by hand because the auto-mode classifier blocks `git push
--force-with-lease` (ask him to run it with `!` next time); #3879 retitled, body set from `PR1/pr-body.md` (Evidence row 3 = the
whole-machine repeat in August's placement: 14.67 / 14.78 / 17.29 tokens/s per user, +17.8%), label `Skip benchmarks`; thread map posted
(issuecomment-5578693039; row 2 rewritten because PR 0's inline-variables comment is gone); #3997 correction posted
(issuecomment-5578693167). PR 2 re-stacked locally on fcc78573b0 = c64b0ca102, not pushed. CI: PR 0 run 34182621147 and #3879 run
34183469443 were in progress at 03:30 UTC; both branches' "Slice tests" passed. gpt-6-astra fact check of the three texts:
`reviews/gpt-6-astra-reply-16-pr1-go-texts.md` (corrections applied). Bill question (Slack 14:32 PDT): our whole-machine jobs ran
21:10-21:31 UTC inside a gap in his work, nothing killed; he probably saw our processes on his half and waited (bill-watch.log).

## Update 2026-09-08 20:2x UTC: both PRs out of draft; CI queued behind other runs; clock labels corrected

jhan marked #4265 (PR 0b) ready for review at 19:35 UTC himself, after rewriting its description (no longer "One line"; 377 words),
so `PR0b/pr-body.md` is only our draft. #4267 (PR 0) has been ready since 03:10 UTC with reviewers Wado-posi, mcherba, Ben,
sthorup-positron. CI at 20:15 UTC: #4267 run 34267638537 (ef13273ba9): lint, ci-machinery-tests, test-slice, Bugbot, Graphite pass;
`build` started 20:06 UTC after about 50 min in the runner queue (four other CMake runs queued). #4265 run 34269850486 (7a7699b338):
lint and ci-machinery-tests pass, `build` pending; benchmark skipped by label. Clock correction: the section headers written today by
this session used host local time (PDT) as UTC in two places; corrected to 18:5x UTC (assessment) and 19:1x UTC (option A applied).
The guard-A landing time (11:5x UTC) was right (commits dc5d496d06 05:11 UTC, 7a7699b338 11:53 UTC).
CI GREEN on #4267 ef13273ba9 (run 34267638537, about 21:1x UTC): build, test-host, test-fpga and the `test` gate passed;
benchmark and benchmark-report skipped by the label. CI GREEN on #4265 7a7699b338 as well (run 34269850486, its first
non-draft run, about 21:5x UTC): build with the cost-data check, test-host (t_kv_footprint_memorder green), test-fpga, `test`.

## Update 2026-09-08 19:1x UTC: option A APPLIED to PR 0 (#4267 head ef13273ba9), GitHub body untouched

On jhan's go ("Apply option A and README.ci.md. Do not update PR body"): commit **ef13273ba9** in `~/workspace/tron` (his checkout,
branch `jhan-page-share-counters`), pushed 19:12 UTC; #4267 (not a draft, label `Skip benchmarks`) now ends 6c735e63ae -> ef13273ba9. Change:
workflow :367 back to `-DTRON_REQUIRE_ALL_MODEL_TESTS=ON` (no counters flag); `CMakePresets.json` coverage preset gains
`"TRON_PAGE_SHARE_COUNTERS": "ON"`; README.ci.md "CMake Flags" paragraph rewritten (build job leaves the option OFF, coverage preset
sets it ON, cpp-coverage.yml compiles and t_llama_unit exercises the hooks). Validated: JSON parses, workflow YAML parses,
`git diff --check` clean; lefthook is not installed here, so the commit hook did not run (CI lint does). CI on ef13273ba9 was
pending at push time (lint, ci-machinery-tests, test-slice; build/test follow because the PR is off draft). The GitHub body was
NOT edited; jhan got the suggested addition in chat (the body has no sentence about the CI lane any more, so it needs one new
sentence, not a correction). Local `PR0/pr-body.md` is stale relative to jhan's GitHub text and was left alone.

## Update 2026-09-08 18:5x UTC: codex comment on #4267 (benchmark artifact) assessed; agree with corrections; applied in the 19:1x section above

jhan asked whether a codex review comment on PR 0 is right: the `build` job's `-DTRON_PAGE_SHARE_COUNTERS=ON` (PR 0's third
commit, workflow :367) instruments `gen/runtron`, which `bin/ci/ci-bundle-artifact.sh` bundles as the benchmark artifact and the
`benchmark` job runs with `--prebuilt`. Verified (five agents, report `PR0/codex-benchmark-artifact-verification.json`; page
`PR0/codex-benchmark-artifact.html`): the chain holds; the clean-build fallback is a rare corner (3-day artifact expiry + forced
rerun, or bundle/NFS/ldd failure), not a coin flip; the stronger reason is the nightly golden baseline, which is always a clean
build, so after merge every report's golden section compares instrumented vs clean permanently. Overhead unmeasured (A/B of the
grid needed). Recommended fix: drop the flag from workflow :367 and add `"TRON_PAGE_SHARE_COUNTERS": "ON"` to the `coverage`
preset (CMakePresets.json:113-118; weekly lane compiles every TU and runs t_llama_unit), rewrite README.ci.md:505-520 and the PR
body's Test paragraph. This reverses decision 2 (option B) with a new fact; jhan's call. `~/workspace/tron` untouched.

## Update 2026-09-08 12:0x UTC: guard A LANDED on PR 0b (pushed; #4265 head 7a7699b338)

The chain of the 05:1x section ran after the CI lease cleared (about 11:45 UTC): fixed tip dc5d496d06 built (rc 0, 131 s) and
`t_kv_footprint_memorder` passed ("All tests passed (2 assertions in 1 test case)"); main + test ee4caa88e0 built (rc 0, 129 s)
and the test FAILED as intended ("assertions: 2 | 1 passed | 1 failed", child SIGABRT, exit code 42); the bench ran at 11:51 UTC
(whole machine, nobody else active): 0.7 s at 1/2/4 slices, 8 MB RSS. Pushed `jhan-kv-footprint-memorder` twice: dc5d496d06
(test) and 7a7699b338 (cost data, third commit). #4265 stays a draft with the three commits; its GitHub description still says
"One line" (jhan edits it; draft text `PR0b/pr-body.md`, now describing all three commits). Temp branch
`tmp-pr0b-test-on-main` deleted. Worktree `~/workspace/ai-runs/tron-pr0b` kept on the branch (clean). Logs archived in
`PR0b/ub-guard/` (split-PR0b-test*.txt/.out, the bench json); page `PR0b/ub-guard.html` has a "Landed" table. The G1 campaign
of the other session was waiting for `split-PR0b-test.bench-done`, which now says ok. Scratch `/var/tmp/jhan/memorder/` on
delphi-3bda is removable.

## Update 2026-09-08 05:1x UTC: guard A added to PR 0b (superseded by the 12:0x section above)

jhan asked to add guard A (the Catch2 test with a per-target `_GLIBCXX_ASSERTIONS`) to PR 0b. Done locally in the new
worktree `~/workspace/ai-runs/tron-pr0b` (branch `jhan-kv-footprint-memorder`): commit **dc5d496d06** on top of e2f22c7a09
adds `t/t_kv_footprint_memorder.cpp` and its `add_catch_test(... DEFINES _GLIBCXX_ASSERTIONS PROPERTIES LABELS fake)` line
in `t/CMakeLists.txt` (clang-format-19 dry-run clean, `git diff --check` clean, no `<cassert>`). A temporary local branch
`tmp-pr0b-test-on-main` = **ee4caa88e0** (main a80b102c18 + the test, WITHOUT the fix) exists only for the "fails without
the fix" proof; delete it afterwards (`git branch -D tmp-pr0b-test-on-main` in the tron-pr0b worktree), never push it.
Queued on delphi-3bda at 05:12 UTC (wrapper pid 3862416, waits for the CI lease): `split-verify3.sh PR0b-test dc5d496d06`
(KEEP_WT=1; expect "All tests passed (2 assertions in 1 test case)"), then `split-verify3.sh PR0b-test-on-main ee4caa88e0`
(expect the test to FAIL: `REQUIRE(sig == 0)` with 6 = SIGABRT), then `split-bench3.sh PR0b-test t_kv_footprint_memorder`
(cost data; whole-machine, Bill-gated). Markers: `exec/logs/split-PR0b-test.done`, `split-PR0b-test-on-main.done`,
`split-PR0b-test.bench-done`. Next: when both verify markers say ok and the .txt lines match the expectations, push
`jhan-kv-footprint-memorder` (rule 3 allows it); then, when the bench lands, commit the added `config/test-benchmarks.json`
entries as a second commit and push again. PR body draft updated: `PR0b/pr-body.md` (previous text
`pr-body.v2-20260906-one-line.md`); the GitHub body of #4265 was not edited (jhan edits PR descriptions himself).
Queued BEHIND this chain by jhan's other session (new-prs-f9, message 05:2x UTC): the whole-machine G1 store-cost campaign
`exec/g1-20260908/g1-campaign.sh` (waiter polls the CI lease; starts only after `split-PR0b-test.bench-done` exists or the
PR0b wrapper has exited; then holds the campaign flock about 3.5 h; kills only its own rinzler.canon/.mirror/.g1, runtron and
st_perf.py processes). Status `exec/logs/g1-20260908.status`, log `exec/logs/g1-20260908.log`, plan `Tuesday-plan.html`.
If the PR0b bench waits long for Bill, that campaign waits too; that is intended (jhan's rule for the campaign: after the
PR 0b test, and only if Bill is absent). The campaign's idle-serving takeover (stop rinzler@0-3 after 10 quiet minutes,
round 1's recipe) runs right after the CI lease clears, which also clears the PR0b bench's "no serving" wait.

## Update 2026-09-08 04:5x UTC: can a test guard the PR 0b bug? (answered, nothing committed)

jhan asked whether a unit test can guard the undefined behaviour PR 0b fixes. Answer and evidence: `PR0b/ub-guard.html`
(+ `PR0b/ub-guard/`). Verified with tron's nix clang 19 + libstdc++ 14.3 on delphi-3bda (single-file compiles under `nice`
while CI held the lease): the wrong and the fixed line compile to identical instructions; no warning, clang-tidy, TSan or
UBSan reacts; only `-D_GLIBCXX_ASSERTIONS` (libstdc++ precondition checks) aborts at the load. A draft Catch2 test
(`PR0b/ub-guard/t_kv_footprint_memorder.cpp`, registered with `add_catch_test ... DEFINES _GLIBCXX_ASSERTIONS`) fails on
main and passes with e2f22c7a09; a lefthook grep rule is the second guard (must land with or after PR 0b). Not done: no
branch changed, no cost-data run (a new test binary needs `config/test-benchmarks.json` entries), the tree-wide effect of the
define is unmeasured. Scratch on delphi-3bda: `/var/tmp/jhan/memorder/` (removable).

## Update 2026-09-08 02:4x UTC: PR 0 review round 2

jhan edited the header and the test himself in `~/workspace/tron` (shorter comments, braces) and asked for two more changes,
applied on his go: the literal 7 became the constant `HISTOGRAM_SLOTS_7` (his name; ALL_CAPS with the value in the name is
unusual in tron, 27 such constants vs 260 lower-case, concern raised and overruled) used by the header and the test with a
`static_assert` tying it to the report format string; the report labels became "query-token/page-visit pairs" and "% of pairs"
(the term "work units" had lost its definition). Checked on copies first (compile, Catch2 stand-in, delphi-3bda ON+OFF builds,
clang-format) because jhan's rule for `~/workspace/tron` is "do not change anything before confirming with me". Committed as
jhan in his checkout and pushed on his request: **834d8346d5** is the new head of `jhan-page-share-counters` and of draft
#4267. jhan edits the PR description himself; its Verification paragraph is still the 2026-09-06 text and must be replaced.

## Update 2026-09-07 21:0x UTC: PR 0 review round 1

jhan reviewed #4267 (12 comments: the word "width", the macro guard, three comment deletions, the histogram comment, three
terse comments, the n_visible name, `!x` on integers, the report's `v`/`t`, the exit-time dump, `local`, `shared_v`/`shared_t`).
Answers: `PR0/Monday-report.html`. Code revision: ONE commit on the side branch `jhan-page-share-counters-rev1` (worktree
`~/workspace/ai-runs/tron-pr0-rev1`; id in `PR0/review1.commit`; diff `PR0/review1.diff`), not pushed; jhan's own checkout
`~/workspace/tron` is on `jhan-page-share-counters` and must not be touched. Built and tested on our half with
`exec/split-verify3.sh` (labels split-PR0-rev1*, ON and OFF), reviewed by gpt-6-astra (reviews/*-14-pr0-review1.md, no blocker).
PR body draft `PR0/pr-body.md` updated (previous text `pr-body.v4-20260907-before-review1.md`); its Verification paragraph still
needs the rev1 rows. Decided by jhan the same evening: names as in the branch (per-call members + `total_`-prefixed atomics, no totals struct), keep the
exit-time reporter, keep the guard. Pushed: 1deb17fc4d is the new head of `jhan-page-share-counters` and of draft #4267 (22:3x UTC).
The PR body on GitHub was NOT edited (jhan edits it himself; `PR0/pr-body.md` is only a draft). PR 0's tip in the table of
section 2 is therefore 1deb17fc4d (built code = that commit, ON and OFF verified, split-PR0-rev1d-*). The cost-data step for
PR 0 (bench chain, worktree tron-split-PR0-on at f6794a7c15) measures the same test binary and stays valid.

## Short version

All four pieces of the split are built and tested at their final commits; PR 0b (#4265) and PR 0 (#4267) are open as
drafts; PR 1 is complete locally and waits only for jhan's go and its cost-data entries; PR 2 is a verified local branch
whose priority jhan lowered below the single-K series. Two whole-machine jobs are queued on delphi-3bda behind a monitor
that waits for Bill to leave: the cost data for PR 0 and PR 1, and a repeat of the qwen measurement in the August
placement. The qwen measurement itself was already done today on our half and is in PR 1's text: AMX +17.7% decode over
the clean build (August: +17.5%).

## Words used here

- **tron / rinzler / runtron**: tron is the inference program under test; rinzler is its production server; runtron
  is its command-line tool.
- **PR 0, PR 0b, PR 1, PR 2**: the pieces of the old pull request #3879. PR 0 = page-share counters (instrumentation
  that counts how many query tokens visit each page of the attention key/value cache; default off; draft #4267). PR 0b =
  a one-line fix of a memory-order argument (draft #4265). PR 1 = the canonical AMX attention path (reads the keys as
  stored; reuses #3879 after a force-push). PR 2 = the K-mirror reference draft (a second copy of the keys in the layout
  the AMX tile multiply consumes; not for review). **R** = the whole old PR rebased onto main a80b102c18 as one commit
  (e449b11452); reference only, not pushed.
- **AMX**: Intel Advanced Matrix Extensions, the tile instruction set the kernels use. **Granite Rapids**: the Xeon 6
  generation with AMX; delphi-3bda is a Xeon 6962P.
- **half split**: jhan's sharing rule for delphi-3bda (`~/workspace/notebook/handoffs/delphi-3bda-guard.md`): Bill has
  cards 10:00.0, 13:00.0, 38:00.0, 3b:00.0 and CPU socket 0 (slices 0-3); we have cards 90:00.0, 93:00.0, b9:00.0,
  bc:00.0 and socket 1 (slices 4-7, `--instance 1,2`). Whole-machine work only when Bill has no process on the machine.
- **the guard**: `exec/lib-guard.sh`; `campaign_guard_acquire` refuses while the nightly CI holds its lease
  (`/run/lock/systems-test-ci.lease`), while a rinzler@N unit is active, or while another person is active
  (`other_user_active`, 10-second CPU sample; the exclusion list `GUARD_EXCLUDE_USERS` decides who counts). The login
  environment on delphi-3bda now exports the list WITH `bill`, so scripts ignore Bill unless they override it.
- **the monitor**: `exec/bill-watch.sh`; see "What is running".
- **cost data**: `config/test-benchmarks.json` in the tron tree, produced by `bin/slice bench --update <tests>`; the CI
  step "Check slice cost data" (`bin/slice bench --check`, job `build` of `cmake-single-platform.yml`) fails while a
  registered test has no entry. That job is skipped on draft PRs (no `Run CI` label), so a draft shows no failure.
- **PAL / gpt-6-astra**: the MCP bridge to external models (`~/bin/pal_mcp_client.py`) and the OpenAI model jhan wants
  used for every substantive judgment. Helpers: `exec/pal/ask.sh`, `exec/pal/collect.sh` (see section 8).
- **Catch2 summary line**: the last line a test prints, "All tests passed (N assertions in M test cases)".

## 1. Ground rules (from jhan, in force)

1. Machine: half split. Builds and host tests run on socket 1 with `SYSTEM_CONFIG="--instance 1,2"`; whole-machine work
   (the cost-data bench, runs on Bill's cards) only when Bill has no process, and stops within about 30 s if he returns
   (the monitor does that). No message to Bill.
2. Use gpt-6-astra through PAL for every substantive step (a build or test failure, any code change on any branch, the
   final wording of PR texts, the go/no-go summary). Treat its output as input to verify. In addition, this work used
   Claude workflows (parallel reviewer/refuter agents) before every launch; keep doing that for scripts that run
   unattended.
3. Pushes allowed without asking: PR 0 and PR 0b branches and their draft PRs (both done). PR 1 (force-push of
   `jhan-amx-p0`, retitle of #3879) only after jhan's explicit go. PR 2 is not opened as a PR until jhan asks (decision
   5). No `Run CI` label ever; `Skip benchmarks` on every PR.
4. GitHub posts allowed only after jhan's go: the thread map as a comment on #3879 after the force-push, and the
   correction comment on issue #3997 (decision still open). No messages to Ben, Bill or Jeremy.
5. Never edit a bash script while a queued step is executing it (bash reads scripts incrementally from NFS). Write a
   new file and rename it over the old one, then `chmod +x` (a Python write + rename drops the executable bit; this
   killed a chain twice today).
6. Plain English everywhere: define terms at first use, one claim per sentence, numbers with units and meaning.

## 2. The branches (final tips)

| PR | Branch | Tip | On GitHub | Tested |
|---|---|---|---|---|
| PR 0 | `jhan-page-share-counters` | 8a867e03a3 (3 commits: c3e405b2b5 header + hooks; f6794a7c15 option + test; 8a867e03a3 CI-lane flag + README.ci.md) | draft #4267, label `Skip benchmarks` | built code = f6794a7c15: option ON and OFF, `t_page_share_counters` 61 assertions / 4 cases, `t_llama_unit` 120054 / 27 |
| PR 0b | `jhan-kv-footprint-memorder` | e2f22c7a09 | draft #4265 (stays a draft, decision 4a) | default build, `t_llama_unit` 120054 / 27 |
| PR 1 | `jhan-amx-p0-v2` (linear source `pr1-stage2` 4ec6a2b819) | 9723d56f62 (4 topical commits: 0a1e62a0fe kernels + interface + doc; 7d033ee78c dispatch; option + CI flag + README.ci.md; 9723d56f62 tests) | not pushed; `jhan-amx-p0` still at 60d66d9c04 | DISPATCH ON: `t_amx_numerics` 4109 / 4 (no "AMX unavailable", so AMX executed), `t_amx_dispatch_dtype` 1559 / 1, `t_llama_unit` 120054 / 27; OFF: stubs 1 / 1, `t_llama_unit` 120054 / 27 |
| PR 2 | `jhan-amx-k-mirror` | dfa6a5f71b (1 commit on 9723d56f62) | not pushed; deferred (decision 5) | DISPATCH + K_MIRROR ON: `t_amx_mirror` 24576 / 1, `t_amx_arena_leak` 12 / 3, `t_amx_numerics` 6413 / 5, `t_amx_dispatch_dtype` 1559 / 1, `t_llama_unit` 144911 / 31 |
| R | `split-base-R` | e449b11452 | not pushed | DISPATCH ON passed; both options ON **fails to build** (the two `{}` configs; recorded, not patched) |

Base of PR 0, PR 0b and PR 1 is main a80b102c18; origin/main has moved on (PR 0's and PR 1's third commits edit the same
workflow line, a one-token conflict for whichever lands second). All clang-format patches are empty at these tips.
PR 0 + PR 1 + PR 2 no longer reproduce R exactly: R keeps the dropped eligibility case and the two empty configs.

Worktree of the shared repo: `~/workspace/ai-runs/tron-split` (currently on `jhan-amx-k-mirror`); the repo's main
checkout `~/workspace/tron-amx` is `jhan-amx-p0` and must stay clean for the PR 1 force-push recipe.

## 3. What is running on delphi-3bda right now (19:45 UTC)

| Piece | Process | State | What it does next |
|---|---|---|---|
| Monitor `exec/bill-watch.sh` | `bash exec/bill-watch.sh` (pid file `/var/tmp/jhan/bill-watch.pid`) | STOP: Bill's four `eoe_engine` processes at 100% CPU since about 15:16 UTC; flag `/var/tmp/jhan/bill-active.flag` set; killed nothing | Polls every ~30 s (10 s CPU sample + 20 s sleep). CLEAR when Bill has no work process and under 0.2 core, no CI lease, no rinzler serving (a bare login of his does not count). On STOP it kills OUR whole-machine processes only (jhan's runtron that names Bill's cards or slices, rinzler, `bin/slice bench` and its children); on a CI-lease or serving STOP it kills every runtron of ours. State line rewritten every poll in `/var/tmp/jhan/bill-watch.state`; log `exec/logs/bill-watch.log`. |
| Cost-data chain (`exec/split-relaunch3e.sh`) | `bash -c "BENCH_WAIT_SEC=86400 exec/split-bench3.sh PR0-on ...; ... PR1-on ..."` | step PR0-on polling since 19:08:44 UTC ("monitor not CLEAR ... waits") | Starts `bin/slice bench --update` in the kept worktree when the monitor is CLEAR and fresh; retries up to 3 times if stopped; gives up after 24 h (`bench-stopped`, worktree kept). Then the PR 1 step. Outputs: `exec/logs/split-PR{0,1}-on.bench-done` (ok / bench-failed / bench-stopped / ...), `split-PR{0,1}-on-test-benchmarks.json`, lines appended to `split-PR{0,1}-on.txt`. |
| Whole-machine qwen repeat `exec/qwen8u8k-pr1.sh` | `bash exec/qwen8u8k-pr1.sh` | waiting for `split-PR1-on.bench-done` | Then waits for the monitor's CLEAR and runs the August placement (cards 10/13, socket 0) for comparability; result `exec/results/qwen8u8k-pr1-<stamp>.txt`, marker `exec/logs/qwen8u8k-pr1.done`. Gives up 24 h after 19:04 UTC. |
| Nothing else of ours | | | The our-half qwen run finished 19:20 UTC. |

Kept worktrees on local disk: `/var/tmp/jhan/tron-split-PR0-on` (f6794a7c15, built ON), `tron-split-PR1-on`
(9723d56f62, ON), `tron-split-PR2-on` (dfa6a5f71b), `tron-qwen-pr1-amx` and `tron-qwen-pr1-clean` (the two runtron
binaries `gen/runtron.pr1amx`, `gen/runtron.pr1clean`; they must stay in their `gen/`, runtron's library path is
`$ORIGIN`-relative). Remove them with `git -C ~/workspace/tron-amx worktree remove --force <path>` when no longer needed.

If the monitor is not running, the cost-data steps and the whole-machine wrapper wait forever. Restart everything with
`exec/morning-launch-20260907.sh` (idempotent: it skips pieces already running and the finished pre-build) and, if the
bench chain is gone, `exec/split-relaunch3e.sh` (check first with `pgrep -f '^bash -c BENCH_WAIT_SEC=86400'`; a plain
`pgrep -f split-bench3` matches your own ssh shell).

Read-only state check that is always allowed:

```sh
ssh delphi-3bda 'cat /var/tmp/jhan/bill-watch.state; ps -u 1062305141 -o pid=,pcpu=,comm= | grep -c eoe_engine;
  cat /run/lock/systems-test-ci.lease 2>/dev/null | head -c 120; echo; for m in split-PR0-on.bench-done split-PR1-on.bench-done qwen8u8k-pr1.done; do printf "%s=%s " $m "$(cat ~/workspace/intel-AMX/exec/logs/$m 2>/dev/null || echo none)"; done'
```

## 4. Today's measurement (already in PR 1's text)

`exec/results/qwen8u8k-pr1-half-20260907T1904.txt`: qwen-3-4b tp2, 8 users, prompt 8192 tokens, 256 generated, PR 1 tip
9723d56f62, run on our half (cards 90:00.0 and 93:00.0, `--instance 2,4`, socket-1 cores = the August cores + 72,
`--numa 1`), two rounds, three arms. Decode tokens/s per user: clean build 14.621 and 14.687; AMX build with
`TRON_AMX_DISABLE=1` 14.743 and 14.758; AMX 17.247 and 17.247. AMX over clean **+17.7%** (August, socket 0, pre-split
binaries: 14.497 to 17.038, +17.5%). Kill-switch mean within 0.7% of clean. Prefill per request 122 s without AMX and
53.6 s with it (throughput +128%; August +90.5%; not separable from placement and shared-host effects). The result file
keeps the "Configured instance 2,4" and "App CPU list" lines as placement proof. gpt-6-astra checked the numbers and the
wording (`reviews/gpt-6-astra-reply-13-pr1-qwen-measurement.md`); PR 1's Evidence table has the row and the paragraph.

## 5. Decisions taken (jhan) and still open

Taken on 2026-09-07: (1) PR 0 pushed as a draft without the cost-data entry; (2) option B, the CMake CI lane configures
with `-DTRON_PAGE_SHARE_COUNTERS=ON` (PR 0's third commit); (3) the `t_llama_unit` AMX eligibility case dropped from PR 1
(it duplicates the first case of `t_amx_numerics`; PR 2 keeps its three mirror assertions in an own mirror-only case);
(4a) PR 0b stays a draft; (5) PR 2 ranks below the single-K series: kept as a verified local branch, its cost-data step
removed, its opening deferred until jhan asks; whole-machine window plan: cost data first, then the qwen re-run;
Bill present means half split, whole-machine tests on hold.

Open: (a) **PR 1's go** (force-push, retitle, thread map; its two cost-data entries are not measured yet, harmless while
the PR stays a draft); (b) whether to post the #3997 correction (`PR1/issue-3997-comment.md`, dates corrected today, PR 2
named as a branch; posting note beside it); (c) whether to patch R's mirror-only test the same way; (d) the handoff's old
items: AMX executes only on Granite Rapids runners (AGENTS.md exception, stated in PR 1); the SK gate measurements G1
(VNNI store cost, time to first token at 1/2/4/8 users mirror against canonical) and G2 (FPGA staging cost) for
2026-09-16, not in scope so far; PR 2 rewrites the line PR 0b fixes; gpt-6-astra's style suggestions for
`doc/amx_software_attention.md` (`reviews/doc-style-suggestions-for-amx_software_attention.md`); (e) noted, not
changed: `t_amx_numerics` and `t_amx_dispatch_dtype` are not in `TEST_INSTALL_TARGETS` (pre-existing; CI unaffected).

## 6. Next steps

1. **When the cost data lands** (markers `split-PR0-on.bench-done` and `split-PR1-on.bench-done` say ok): diff each
   `exec/logs/split-<label>-test-benchmarks.json` against main's `config/test-benchmarks.json` and keep only the added
   entries (platform block `granite_rapids_6962p`). PR 0: commit as a fourth commit on `jhan-page-share-counters`
   ("config: cost data for t_page_share_counters (granite_rapids_6962p)"), then switch PR 0's Test and Verification
   sentences to the "committed" wording (kept in `handoff-Sunday.md` and in the scratch note; the sentences now say
   "not yet measured"), push, `gh pr edit 4267 --body-file <body without its first heading line>`. PR 1: commit the
   entries on `pr1-stage2`, run `bash exec/split-tools/make_topical.sh pr1-stage2 jhan-amx-p0-v2` inside the worktree
   (the script folds `config/test-benchmarks.json` into the tests commit; it must print "tree identical to tip: yes"),
   then `git rebase --onto jhan-amx-p0-v2 <old PR 1 tip> jhan-amx-k-mirror`, switch PR 1's cost-data sentences (item 4
   and Verification). Rebuild the changed ON steps once (`split-verify3.sh`, two minutes each) so the tested commit is
   the pushed commit. If a marker says bench-stopped or dut-never-free, re-run by hand: `exec/split-bench3.sh <label>
   <tests>` (the worktree is kept).
2. **Report to jhan for the PR 1 go**: the results of section 2 and 4, the empty format patches, the cost-data state, the
   open decisions. On the go, follow `handoff-Sunday.md` Step 6 exactly (tag `pr3879-pre-split` = 60d66d9c04, push it as
   `jhan-amx-p0-pre-split`, `git reset --hard jhan-amx-p0-v2` in `~/workspace/tron-amx`, `git push
   --force-with-lease=jhan-amx-p0:60d66d9c04 origin jhan-amx-p0`, `gh pr edit 3879` with title "AMX software attention,
   canonical path: kernel + dispatch, default-off" and `PR1/pr-body.md` without its first heading line, label `Skip
   benchmarks`). Then fill `LINE-NUMBER-TIP` in `PR1/thread-map.md` with the pushed tip (the anchors were verified
   unchanged with `split-tools/threadmap_lines.sh <PR1 tip> 8a867e03a3 e2f22c7a09`; `PR0-TIP` is already f6794a7c15,
   the commit the anchors point at) and post it with `gh pr comment 3879 --body-file`. Post the #3997 comment only if jhan
   says so.
3. **Whole-machine qwen repeat**: runs by itself after the cost data when Bill is gone; if it produces numbers, add one
   line to PR 1's Evidence paragraph (August placement, same tip); it is optional evidence.
4. **PR 2**: nothing until jhan asks; keep it rebased if PR 1 changes (the rebase has been conflict-free except the
   known whitespace hunk in `amx_attn.cpp`, resolved by taking PR 2's side).
5. **Keep the record**: `exec/split-status/state.json` + `python3 exec/split-status/gen_status.py` (status pages),
   `python3 exec/split-status/gen_report_20260906.py` (the report page `PR3879/new-PRs/report-20260906.html`), the
   memory note `pr3879-split-progress.md`.

## 7. Traps found today (do not repeat)

- **`SYSTEM_CONFIG` overrides command-line placement.** The login environment exports `SYSTEM_CONFIG="--instance 1,2"`
  into every detached process; runtron applies the command line first and then `SYSTEM_CONFIG` again
  (`pos_startup_host` -> `system_parse_env`, no "already configured" check), so `--instance 1,2` replaces the command
  line's `--devices`, `--app-cores`, `--dev-cores`, `--numa`. The sharing doc's sentence "a command-line `--instance`
  wins over it" is wrong for placement. Any script that pins cards or cores on the command line must run tron under
  `env -u SYSTEM_CONFIG` (the two qwen wrappers and `split-bench3.sh` do). The 30 older campaign scripts that pin
  Bill's cards have the same exposure.
- A Python write followed by `os.replace()` over a script drops its executable bit; `chmod +x` afterwards.
- `pgrep -f <pattern>` inside an ssh command matches the ssh shell itself (its command line contains the pattern). Use
  `pgrep -fx "bash exec/<script>"` or a pattern anchored at the start of the `-c` string; kill by pid after checking the
  command line.
- A Python loop editing two files with a nested function using `global s` edited only the second file; always
  grep-verify edits.
- PAL: attachments must live under the session scratchpad path (`/tmp/claude-0/.../scratchpad/pal/in/`); files under
  `/var/tmp` came back as "NO FILES FOUND". `exec/pal/ask.sh` sets the working directory to the attachments' common
  parent. The scratchpad does not survive a container restart: copy prompts and replies into `reviews/` at once.
- The container was killed once (about 07:40 UTC) with background waiters and a review workflow running; nothing on
  delphi-3bda was affected (the chain and the monitor are detached there), but anything only in the session's memory
  was lost. Record state in this folder and in the memory note after every step.
- Older traps still valid: `bin/slice bench --check` needs an entry per test; `campaign_guard_acquire` does not wait for
  the flock (the v3 scripts retry); NFS attribute cache (compare `md5sum` on both hosts before launching an edited
  script); the classifier blocks compound history-rewriting git commands (one command per line); `make_topical.sh`
  bases on the merge base, not on the moving origin/main; the server's footprint log labels GiB as GB.

## 8. Tools and files

- Chain: `exec/split-verify3.sh` (build + test one commit on our half; `FORMAT=1`, `KEEP_WT=1`), `exec/split-bench3.sh`
  (cost data; monitor-gated; retries), `exec/split-relaunch3d.sh` (the pass that ran), `exec/split-relaunch3e.sh`
  (bench-only, 24 h wait), `exec/split-tools/chain_results.sh` (summary), `split-tools/make_topical.sh`,
  `split-tools/threadmap_lines.sh`.
- Morning plan: `exec/bill-watch.sh`, `exec/qwen8u8k-prep.sh` (done), `exec/qwen8u8k-pr1-half.sh` (done),
  `exec/qwen8u8k-pr1.sh` (queued), `exec/morning-launch-20260907.sh`.
- PAL: `exec/pal/ask.sh <name> <prompt.md> [files]` (detached; reply in `$PAL_OUT/<name>.raw`, default
  `/var/tmp/jhan/pal-out`; put the prompt and files under the scratchpad), `exec/pal/collect.sh <name>`.
- Texts: `PR0/pr-body.md`, `PR0b/pr-body.md`, `PR1/pr-body.md`, `PR2/pr-body.md`, `PR1/thread-map.md`
  (`LINE-NUMBER-TIP` open), `PR1/issue-3997-comment.md` + `.NOTE.md`; older versions `*.v1..v4-*.md`. Posted bodies
  omit the first heading line (it repeats the title).
- Reviews: `reviews/gpt-6-astra-{prompt,reply}-1..13-*.md`, `reviews/agent-*-2026090{6,7}*.json` with `-digest.md`,
  `reviews/doc-style-suggestions-for-amx_software_attention.md`.
- Logs: `exec/logs/split-<label>.{txt,done,log}` (`.log` files append across passes), `pass1-20260906/`,
  `pass2-20260906/`, `pass2b-20260906/` (archived passes), `split-<label>-<test>.out`, `bill-watch.log`,
  `qwen8u8k-*.log`; results `exec/results/qwen8u8k-pr1-half-20260907T1904.txt`.
- Status: `PR3879/new-PRs/PR*/status.html` (from `exec/split-status/state.json`), `report-20260906.html` (+ `.md`,
  generator `exec/split-status/gen_report_20260906.py`).
- Memory notes: `pr3879-split-progress.md` (chronological log of this work), `3bda-shared-with-bill.md` (half split and
  the SYSTEM_CONFIG correction), `pal-bridge.md`, `breakup-pr3879-plan.md`.

## 9. Definition of done

- Cost-data entries committed on PR 0 and PR 1 (or their absence explained to jhan), both drafts updated.
- jhan has the PR 1 report and has answered; on a go, #3879 force-pushed, retitled, described, thread map posted;
  #3997 comment posted only on jhan's word.
- Status pages, report page, this handoff and the memory note reflect the end state; the kept worktrees and the monitor
  removed when the machine work is over (`pkill -fx "bash exec/bill-watch.sh"`; remove `/var/tmp/jhan/bill-active.flag`
  and `bill-watch.state` afterwards).
