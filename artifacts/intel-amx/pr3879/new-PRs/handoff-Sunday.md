# Handoff: finish the PR 3879 split (written Sunday 2026-09-06, 15:00 PDT)

**Superseded by `Monday-handoff.md` (2026-09-07 19:45 UTC), which holds the current state; this file keeps the history.**

Supersedes `handoff-Saturday.md` (same folder). Read this file first; the Saturday file is kept for its
longer explanations of the tools and the plan.

## Update 2026-09-06 22:55 UTC (read this before the rest)

jhan stated the new machine-sharing scheme in `~/workspace/notebook/handoffs/delphi-3bda-guard.md`: the machine is
split by halves, not by time. Bill has the first four FPGA cards (10:00.0, 13:00.0, 38:00.0, 3b:00.0) and CPU
socket 0; jhan has the second four cards and socket 1, which `SYSTEM_CONFIG="--instance 1,2"` selects. Whole-machine
measurements are allowed only when Bill is not using the machine. Rule 1 (stay out of the CI window; never launch
while a `rinzler@N` unit is active) is unchanged. Done under this scheme:

- The guard doc's fix 2 was applied: `export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"` appended to
  `~/delphi-3bda-setup.sh` on delphi-3bda (backup `.bak-20260906`); every ssh shell, interactive or not, sources it.
  Fix 1 (30 campaign scripts in `exec/` that pass `--instance 0,4 --devices 10:00.0,13:00.0`, Bill's cards) is NOT
  done; none of the chain scripts pass `--instance` or `--devices`.
- New chain tools, all copies (the v2 files are untouched): `exec/split-verify3.sh` (build and tests pinned to the
  socket-1 cores 72-143,216-287; tests run WITH `SYSTEM_CONFIG="--instance 1,2"`, which for these `fake`-labelled
  host tests only selects the core set, since pos_fake's `pos_startup()` never opens a hugepage file; no
  `--allow-serving`; a pre-CI hold that starts no step between 01:40 and 03:45 UTC; a 40-minute `timeout` per test;
  `KEEP_WT=1` keeps the worktree), `exec/split-bench3.sh` (the cost-data measurement, separated because
  `bin/slice bench --update` launches the test under `--instance i,n` for every slot of the box, i.e. on both
  sockets; it waits until Bill has no engine or tron process and the default guard passes) and
  `exec/split-relaunch3.sh` (eight build steps, then the two bench steps; the redirection covers the whole
  backgrounded group so the ssh returns at once). `exec/split-tools/chain_results.sh` also prints the bench marker.
- The chain was launched at 22:50:51 UTC on 2026-09-06 with the tips of the table below. Read the results with
  `bash exec/split-tools/chain_results.sh`. Per-test full output: `exec/logs/split-<label>-<test>.out`.
- Where the text below says `split-verify2.sh`, `split-relaunch.sh` or `BENCH=`, read `split-verify3.sh`,
  `split-relaunch3.sh` and `split-bench3.sh <label> <tests>` (Step 2: copy the matching line out of
  `split-relaunch3.sh`, keep `KEEP_WT=1` on the steps whose bench is still wanted, and queue the bench line after it;
  Step 4's optional PR 2 bench: run PR2-on with `KEEP_WT=1`, then `split-bench3.sh PR2-on t_amx_mirror t_amx_arena_leak`).
- Bill's real hugepage or card use could not be read from jhan's account (his `/proc/<pid>/maps` are not readable);
  the half split is followed on the evidence of his engines' command lines (`--cards 10:00.0`, `13:00.0`) and CPU
  affinities (all inside socket 0).

**Pass 1 (22:51-23:12 UTC) and pass 2 (from 23:20 UTC).** Each step took about 2.5 minutes. Pass 1: PR0-on, PR0-off,
PR0b, PR1-on, PR1-off and R-canon passed every test; `t_amx_numerics` executed AMX (4,109 assertions, no
"AMX unavailable" line). PR2-on and R-mirror failed to compile: `t/t_llama_unit.cpp:924` and `:928`
("no matching constructor for initialization of 'attention_operation_config'"), in the test case that only the
mirror build compiles; main a80b102c18 gives that struct only a three-argument constructor and the Day-1 rebase
missed these two sites. gpt-6-astra confirmed the diagnosis and found no other incompatibility
(`reviews/gpt-6-astra-reply-10-pr2-build-fix.md`); the fix passes
`attention_operation_config{std::nullopt, std::nullopt, 0x1.6a09e6p-4f}` (1/sqrt(128); the predicates the case
checks never read the scale). R stays unpatched (frozen reference; its mirror-ON failure is recorded, and the
amended PR 2 tree differs from R by these two initializers). The clang-format patches were folded in: PR 0's test
file (8+/5-), PR 1's `amx_attn.cpp` (2+/3-, via `pr1-stage2` 2c3c56a37e and `make_topical.sh`), PR 2's
`self_attention.hpp`, `rinzler.cpp` and `t_llama_unit.cpp`. **Final tips: PR 0 f6794a7c15, PR 0b e2f22c7a09
(unchanged), PR 1 32a4d1664f, PR 2 47a2bf140e** (8a878984e7 until 23:47 UTC; a comment-only amend after the
claim check; rebuilt as step PR2-on at 23:47-23:52 UTC with identical test lines and an empty format patch) (the table below still shows the pass-1 tips). Pass 2
(`exec/split-relaunch3b.sh`) rebuilds and retests these tips and then runs the three bench steps; pass-1 logs are
archived in `exec/logs/pass1-20260906/`.

**Cost data.** gpt-6-astra (`reviews/gpt-6-astra-reply-9-bench-halfbox.md`) confirms that `bin/slice bench` has
no half-machine mode (every width places runs on both sockets) and that hand-written entries would pass the check
but misrepresent measurements, which we will not do. CI's check is the step "Check slice cost data"
(`bin/slice bench --check`) of the `build` job in `.github/workflows/cmake-single-platform.yml`; it fails while a
discovered test has no entry on any platform. The bench steps therefore wait until Bill has no engine running.
Whether to push PR 0 before the entry exists (with the failure disclosed in the body) is jhan's decision.

**Pass 2 result (23:20-23:29 UTC): every step ok, every clang-format patch empty.** PR0-on/PR0-off (f6794a7c15), PR1-on/PR1-off
(32a4d1664f) repeat the pass-1 lines; PR2-on (8a878984e7, both options ON) builds and passes `t_amx_mirror` (24,576
assertions), `t_amx_arena_leak` (12 assertions, 3 cases), `t_amx_numerics` (6,413 assertions, 5 cases, no
"AMX unavailable"), `t_amx_dispatch_dtype` (1,559) and `t_llama_unit` (144,915 assertions, 31 cases). The three
`VERIFICATION-PLACEHOLDER`s are filled (previous texts kept as `*.v2-20260906-prefill.md`); PR 0's and PR 1's
paragraphs state the cost-data entries as present, which becomes true only after the bench steps run (alternate
sentences for a push without the entries: scratch file noted in the memory note). **PR 0 was pushed and opened as draft #4267 on 2026-09-07 03:18 UTC on jhan's decision, without the cost-data entry (its body says the entry is not yet measured; the thread map's PR0-TIP is filled with f6794a7c15). PR 0b was pushed and opened as
draft #4265** (label `Skip benchmarks`) at 23:33 UTC; the H1 line of `PR0b/pr-body.md` was left out of the posted
body because it repeats the title. The bench steps for PR 0, PR 1 and PR 2 wait in the chain until Bill's engines
stop (their worktrees are kept at `/var/tmp/jhan/tron-split-PR{0,1,2}-on`).

## Update 2026-09-07 04:xx UTC: jhan's decisions and the resulting tips

- Decision 1: PR 0 pushed as draft #4267 without the cost-data entry (03:18 UTC). Decision 2 (option B): the CMake CI lane
  configures with `-DTRON_PAGE_SHARE_COUNTERS=ON`; PR 0 third commit 8a867e03a3 (workflow line + README.ci.md paragraph;
  no built code changes). Decision 3: the `t_llama_unit` AMX eligibility case is dropped from PR 1 (it duplicates the first
  case of `t_amx_numerics`); PR 1 regenerated from `pr1-stage2` 4ec6a2b819 -> `jhan-amx-p0-v2` 9723d56f62 (the doc's
  "How to verify" names the two AMX tests; commit-4 message in `make_topical.sh` updated). PR 2 rebased -> dfa6a5f71b: its
  three `amx_mirror_eligible` assertions, which extended the dropped case, are now the mirror-only case "K mirror eligibility
  follows the executor's activation scalar". Decision 4a: PR 0b stays a draft. Still open: posting the #3997 correction
  (4b), PR 1's go, patching R.
- **Tips now: PR 0 8a867e03a3 (built code = f6794a7c15), PR 0b e2f22c7a09, PR 1 9723d56f62, PR 2 dfa6a5f71b.** PR 1 and PR 2
  must be rebuilt (steps PR1-on, PR1-off, PR2-on) before their Verification paragraphs are filled again (placeholders
  `VERIFICATION-RERUN-PENDING`); the rebuild waits for the nightly CI (lease from about 03:37 UTC).
- PR 0 + PR 1 + PR 2 no longer reproduce R exactly: R keeps the dropped case (canonical assertions) and the two `{}` configs.
- **Decision 5 (jhan, 2026-09-07 06:1x UTC): PR 2's priority is lowered below the single-K series** (the SK-A/B/C
  PRs behind the 2026-09-16 gate, `PR3879/breakup-PR3879.html` section 5; PR 2 is that series' A/B comparison arm).
  Consequences applied: PR 2 stays a verified local branch (its two-minute rebuild PR2-on stays in pass 3, launcher
  `exec/split-relaunch3d.sh`); its cost-data step was removed from the queue (a draft needs no cost data; the step
  used the whole machine); **Step 7 below (open PR 2 as a stacked draft) is deferred until jhan asks**, even after
  PR 1 is pushed; its Verification paragraph keeps the `VERIFICATION-RERUN-PENDING` placeholder until the rebuild,
  and its cost-data sentence stays "no entry yet". Machine time when Bill is idle goes to PR 0's and PR 1's cost data
  and then to the gate measurements G1 (VNNI store cost) and G2 (FPGA staging cost), which this handoff does not
  cover. Pass 3 now: PR1-on, PR1-off (9723d56f62), PR2-on (dfa6a5f71b), bench PR0-on, bench PR1-on.
- **Whole-machine window plan (jhan, 2026-09-07 06:3x UTC).** When the whole machine is ours for a few hours, in this
  order: (1) the queued cost-data steps for PR 0 and PR 1 (automatic); (2) the qwen-3-4b tp2, 8-user, prompt-8192 decode
  re-run on the PR 1 tip against a clean build (`exec/p2-8u8k.sh` is the script; PR 1's text says this check is not
  included yet); (3) gate measurement G1, time to first token at 1, 2, 4 and 8 users, mirror arm against canonical arm,
  with the round-1 recipe; G2 (FPGA staging cost) needs a prototype first. Build the binaries beforehand on our half.
  Guard rule for (2) and (3): they use the whole machine, so run them with the guard's DEFAULT exclusion list
  (`GUARD_EXCLUDE_USERS="jhan nobody positron packer"`, i.e. Bill's activity blocks again) plus a check that no process
  of Bill's exists (`pgrep -u bill -f 'eoe_engine|runtron|rinzler|gen/'`), because the login environment now excludes
  Bill (fix 2) and the guard's 10-second CPU sample calls idle engines "idle" while they still hold his cards.
- **Plan for the morning of 2026-09-07 after the CI window (jhan, 06:4x UTC; defaults confirmed).** If Bill uses the
  machine, keep the half split and hold every whole-machine test. If he has no process on it, run (a) the cost data for
  PR 0 and PR 1 (queued in `split-relaunch3d.sh`) and (b) the qwen 8-user / prompt-8192 re-run on the PR 1 tip
  (`exec/qwen8u8k-pr1.sh`, August placement, three arms: clean build, AMX build with the kill switch, AMX build; two
  repetitions). A side monitor, `exec/bill-watch.sh`, polls every ~30 s; "Bill uses the machine" = any process of his
  that is not login plumbing, or more than 0.2 core over 10 s; a bare login is logged only. On detection (or when the CI
  lease appears) it kills only our whole-machine processes (jhan's runtron, rinzler, `bin/slice bench`), writes
  `/var/tmp/jhan/bill-active.flag`, and clears the flag after two clean polls; the queue then waits until he is gone.
  Half-machine work continues. `exec/qwen8u8k-prep.sh` builds the two runtron binaries (PR 1 tip, option ON and OFF,
  ingested qwen model) on our half beforehand into `/var/tmp/jhan/bin/`. G1 is not in scope for that morning.
  Logs: `exec/logs/bill-watch.log`, `qwen8u8k-prep.log`, `qwen8u8k-pr1.log`; result `exec/results/qwen8u8k-pr1-<date>.txt`.
  Details after two review rounds (2026-09-07 07:xx UTC): `split-bench3.sh` (not yet executing) was patched so that a
  cost-data step starts only when the monitor's state file `/var/tmp/jhan/bill-watch.state` is fresh (under 2 minutes)
  and says CLEAR and no flag exists, and so that a bench killed by the monitor keeps its worktree and is retried up to
  three times. **Consequence: if `bill-watch.sh` is not running, the cost-data steps and the qwen wrapper wait
  forever; start it with `exec/morning-launch-20260907.sh` (idempotent) after any reboot or kill.** The two runtron
  binaries stay inside their worktrees' `gen/` (runtron's run path is `$ORIGIN`-relative:
  `/var/tmp/jhan/tron-qwen-pr1-amx/gen/runtron.pr1amx`, `/var/tmp/jhan/tron-qwen-pr1-clean/gen/runtron.pr1clean`,
  listed in `exec/logs/qwen8u8k-prep.bins`); their names have no hyphen so the guard's and the monitor's runtron
  patterns match them. The wrapper marks a run the monitor killed as `RUN-STOPPED` and repeats that arm once the
  monitor says CLEAR; it gives up 24 hours after it was queued (`gave-up` marker).
- **18:4x UTC, jhan: "since Bill is using the machine, let's use our half".** Started `exec/qwen8u8k-prep.sh` on our half
  (18:40 UTC; the earlier start attempt had matched its own ssh shell in the running-check and did nothing; the launcher
  now uses `pgrep -fx "bash exec/<script>"`). New `exec/qwen8u8k-pr1-half.sh`: the qwen re-run on OUR half, same flags as
  August except the placement (`--instance 2,4 --devices 90:00.0,93:00.0`, app cores 223-224,96-101,120-125,225-226,
  102-107,126-131, dev cores 75,76, `--numa 1`; every August core + 72), no monitor gating, guard ignores Bill, still
  waits for the lease, serving, the pre-CI hold and the pre-build; result `exec/results/qwen8u8k-pr1-half-<date>.txt`.
  Both arms share the placement, so the AMX/clean ratio is comparable with August; the absolute tokens/s may differ from
  the socket-0 run. `bill-watch.sh` now exempts our-half runtron runs from its kill list (command line names none of
  Bill's cards and no `--instance 0,`). The August-placement run (`qwen8u8k-pr1.sh`) stays queued for when Bill is gone.
  Still blocked by Bill (by design): the cost data (whole-machine bench).
- **19:1x UTC, second review round applied.** `split-bench3.sh` (replaced by rename, so the polling PR0-on step kept the
  old file): a bench stopped a third time now gives up with marker `bench-stopped` and keeps its worktree; a finished
  bench is never discarded because the flag appeared in its last seconds; retries respect the pre-CI hold; Bill's
  processes are looked up by uid 1062305141. Both qwen wrappers: only exit codes 143/137 (killed) count as a stop, at
  most 4 attempts per arm, any other failure is `RUN-FAILED` and the script moves on; the pre-CI hold is checked
  before every run; the campaign flock is released while waiting and taken again per run. `bill-watch.sh`: uid instead of
  the name, zombies ignored, a third person's CPU is labelled as such. New `exec/split-relaunch3e.sh`: the two cost-data
  steps with a 24-hour wait each (the pass-3 chain's bench step had a 12-hour deadline ending 23:57 UTC); it replaces the
  chain's remaining bench steps. Start order: `morning-launch-20260907.sh` (monitor, pre-build, both wrappers), then
  `split-relaunch3e.sh`.
- **18:56 UTC: pre-build done.** `/var/tmp/jhan/tron-qwen-pr1-amx/gen/runtron.pr1amx` (option ON, 459 s) and
  `/var/tmp/jhan/tron-qwen-pr1-clean/gen/runtron.pr1clean` (option OFF, 476 s), both from 9723d56f62 with the ingested
  qwen model present; paths in `exec/logs/qwen8u8k-prep.bins`, marker `qwen8u8k-prep.done` = ok.
- **Trap found by the delta review (19:3x UTC): `SYSTEM_CONFIG` overrides a command-line placement.** The login
  environment exports `SYSTEM_CONFIG="--instance 1,2"` into every detached process. runtron applies the command line
  first and then, in `pos_startup_host` -> `system_parse_env`, applies `SYSTEM_CONFIG` again with no "already
  configured" check, so `--instance 1,2` REPLACES the command line's `--devices`, `--app-cores`, `--dev-cores` and
  `--numa` (four cards and 24 cores instead of two cards and twelve). The sharing doc's sentence "a command-line
  `--instance` wins over it" is wrong for placement (`early_parse_instance` only picks the FUSE mount path). Every
  script that passes its own `--instance`/`--devices` must run tron under `env -u SYSTEM_CONFIG` (both qwen wrappers
  now do; `split-bench3.sh` already did); the 30 campaign scripts that pin cards on the command line have the same
  exposure since fix 2 exported the variable. The wrappers also keep the "Configured instance" and "App CPU list"
  lines of the run in the result file as proof of the placement. Other delta-review fixes: the monitor's exemption
  regex covers every instance form on Bill's slices (`--instance 0,N; 1,4; 1,8 2,8 3,8`), and a CI-lease or serving
  stop kills every runtron of ours, our-half ones included; the result files carry a time stamp.
- **19:05-19:20 UTC: the qwen re-run on our half is done** (`exec/results/qwen8u8k-pr1-half-20260907T1904.txt`; the
  file keeps the "Configured instance 2,4" and "App CPU list" lines as placement proof). Two rounds, decode tokens/s per
  user: clean 14.621 and 14.687; kill switch 14.743 and 14.758; AMX 17.247 and 17.247. AMX over clean **+17.7%** (August,
  socket 0, pre-split binaries: 14.497 to 17.038, +17.5%); kill switch over clean +0.7%. Prefill of the 8 x 8192-token
  prompts: 122 s clean and kill switch, 53.6 s AMX (+128%; August +90%, 65.4 to 124.5 tokens/s; the larger prefill gain on
  the split tip is measured, not explained: Insufficient data). Monitor said STOP (Bill) throughout and killed nothing;
  the run was exempt as our-half work. 19:04:56 launch: monitor, half wrapper, whole-machine wrapper (waits for the cost
  data and CLEAR); 19:08:44: bench chain 3e (24-hour wait) queued after two failed starts (the renamed-in
  `split-bench3.sh` had lost its executable bit; fixed with chmod).
- PR 1's Evidence table gained the new row and its closing paragraph now states the result with the placement caveat
  (previous text kept as `PR1/pr-body.v4-20260907-before-qwen.md`); gpt-6-astra confirmed every number and its four wording
  refinements are applied (`reviews/gpt-6-astra-reply-13-pr1-qwen-measurement.md`). PAL helpers now live in the repository under
  `exec/pal/`; keep the prompt and its attachments under the session scratchpad path (`/tmp/claude-0/.../scratchpad/pal/in/`):
  attachments under `/var/tmp` came back as "NO FILES FOUND".

## Update 2026-09-07 18:3x UTC: pass 3 done; the morning window was missed

- Pass 3 ran after the nightly (11:3x UTC): PR1-on/PR1-off at 9723d56f62 and PR2-on at dfa6a5f71b all passed with empty
  clang-format patches (`t_llama_unit` 120054 assertions / 27 cases in both PR 1 builds; 144911 / 31 in PR 2). Both
  Verification paragraphs are filled again; the cost-data sentences still say "not measured".
- The cost-data steps did not run: the patched `split-bench3.sh` waits for the side monitor, and the Claude session that
  was to start the monitor (after the second review round) ended overnight before doing so. The bench PR0-on step has
  been polling since 11:3x UTC ("monitor not CLEAR ..."). Bill's four `eoe_engine` processes are back at 100% CPU since
  about 15:16 UTC, so under the plan the whole-machine tests are on hold until he leaves again. Whether the machine was
  free of Bill between the end of the nightly and 15:16 UTC is not recorded (no monitor ran): Insufficient data.
- Next: finish the second review round of `bill-watch.sh`, `qwen8u8k-prep.sh`, `qwen8u8k-pr1.sh`, `split-bench3.sh`,
  then run `exec/morning-launch-20260907.sh` (monitor, pre-build on our half, qwen wrapper). The bench and the qwen run
  then start by themselves the next time the monitor says CLEAR (Bill gone, no lease, no serving) and stop again if he
  returns. **Final tips unchanged: PR 0 8a867e03a3 (#4267), PR 0b e2f22c7a09 (#4265), PR 1 9723d56f62, PR 2 dfa6a5f71b.**

## Short version

The code of the split is done, reviewed twice more today, and sits in local branches that nobody has
pushed. The build-and-test chain on delphi-3bda never ran: Bill used the machine all Sunday. jhan is
replacing the Saturday machine-sharing procedure with a new scheme; until jhan states it in this
conversation or in writing, launch nothing on delphi-3bda. Everything else is ready: the branch tips
below are final, the chain launcher points at them, the six GitHub texts are written with placeholders
for the build results, and the PAL recipe for gpt-6-astra is in section 7.

## Words used here

- **tron / rinzler / runtron**: tron is the inference program; rinzler is its production server, built
  from tron; runtron is its command-line tool.
- **PR 3879**: the original pull request "AMX software attention (default-off): QK/PV tile kernels +
  K-mirror arena", branch `jhan-amx-p0`, head 60d66d9c04 (local tag `pr3879-pre-split`). It is being
  split into PR 0 (page-share counters), PR 1 (the canonical AMX path, reusing #3879), PR 2 (the K
  mirror, a reference draft) and PR 0b (a one-line fix). Plan: `PR3879/breakup-PR3879.html`, jhan's
  decisions in its section 8.
- **AMX / AVX-512**: AMX (Intel Advanced Matrix Extensions) is the tile-matrix instruction set the new
  kernels use; AVX-512 is the vector instruction set of the existing attention loop (the "dotter").
- **canonical / K mirror**: canonical = the AMX path that reads the attention keys K as stored (PR 1);
  the K mirror = a second copy of K in the VNNI layout, kept in ordinary RAM (PR 2, option
  `TRON_AMX_K_MIRROR`).
- **R**: the whole PR 3879 tree rebased onto main a80b102c18 as one commit (e449b11452, branch
  `split-base-R`). PR 0 + PR 1 + PR 2 reproduce R minus the parked tool `t_amx_logit_ab`.
- **the chain**: `exec/split-verify2.sh` builds and tests one commit on delphi-3bda in an isolated
  worktree; `exec/split-relaunch.sh` queues the eight steps in order.
- **the guard**: `exec/lib-guard.sh`; `campaign_guard_acquire` refuses while the nightly CI holds the
  lease, while another person is actively using the machine (`other_user_active`), or during a
  blackout window (`blackout_active`, file `/var/tmp/jhan/3bda-blackout`).
- **people-check**: `exec/people-check.sh`, the Saturday procedure for sharing the machine with Bill
  (described in `~/workspace/notebook/handoffs/share-3bda-with-bill.md`). Superseded; see rule 1.
- **PAL / gpt-6-astra**: PAL is the MCP bridge to external models (`~/bin/pal_mcp_client.py`);
  gpt-6-astra is the OpenAI model jhan wants used for every substantive judgment.
- **cost data**: `config/test-benchmarks.json` in the tron tree; CI's `bin/slice bench --check` fails
  the build when a registered test has no entry. The new tests have none yet.

## Ground rules (from jhan, in force)

1. **Machine access follows a new scheme jhan will state.** The Saturday people-check procedure
   (30-minute polling, claim files, the same-time rule) is no longer the rule. Until jhan describes
   the new scheme, do not launch anything on delphi-3bda, not even a compile; read-only ssh to look at
   the state is acceptable. The blackout file was removed on 2026-09-06 at 17:22 UTC (a copy is at
   `/var/tmp/jhan/3bda-blackout.lifted-20260906`), so the guard now checks only the CI lease and
   other people's activity. If the new scheme needs a hold, recreate the file with one line
   `<start_epoch> <end_epoch> <note>`.
2. **Use PAL with gpt-6-astra for every substantive step**: interpreting a build or test failure, any
   code change on any branch, the final wording of the PR texts, and the go/no-go summary for jhan.
   Recipe in section 7. Treat the model's output as input to verify, not as a decision.
3. **What may be pushed without asking**: PR 0's branch and a **draft** PR for it; PR 0b's branch and a
   draft PR for it. **PR 1 (force-push of `jhan-amx-p0`, retitle of #3879) only after jhan's explicit
   go.** PR 2 is pushed and opened as a draft only after PR 1 is pushed (it is stacked on PR 1).
4. **No messages to Ben, Bill or Jeremy** from this work. The only GitHub posts the plan allows are the
   thread map as a comment on #3879 after the force-push and the correction comment on issue #3997;
   both drafts exist; post them only after jhan's go for PR 1.
5. Labels: `Skip benchmarks` on every PR; never `Run CI`. Only a PR based on main may be ready for
   review; PR 2 stays a draft.
6. Never edit a bash script while a queued step is executing it (bash reads scripts incrementally
   from NFS). Copy to a new file instead.
7. Plain English (define terms at first use, one claim per sentence, numbers with units); keep the
   status pages current (section 6, step 8).
8. New today: the Claude Code auto-mode classifier blocks compound git commands that rewrite history
   (amend + cherry-pick + branch -f in one line, or with `-c user.name=...`). Run each as its own plain
   command; `git commit --amend --no-edit -a -q` alone passes. The message "Can't find lefthook in
   PATH" on every commit is harmless (the repo's hook runner is not installed on this host).

## Where everything is

Worktree: `~/workspace/ai-runs/tron-split` (a worktree of the shared repo whose main checkout is
`~/workspace/tron-amx`, branch `jhan-amx-p0`; the repo is NFS-shared with delphi-3bda). Checked out:
`jhan-page-share-counters`, clean.

| Branch | Tip | What it is |
|---|---|---|
| `split-base-R` | e449b11452 | R: whole PR on main a80b102c18 |
| `pr0-pure`, `pr1-pure`, `pr2-pure` | fc05957a32, b7ecdbe7ef, 4670f7233b | stage-1 pure subtraction, reference only |
| `jhan-page-share-counters` | **4f4c4d4f4c** | **PR 0**, 2 commits: c3e405b2b5 (header + 5 hooks), 4f4c4d4f4c (top-level CMake option + host test `t_page_share_counters`) |
| `jhan-kv-footprint-memorder` | **e2f22c7a09** | **PR 0b**, 1 commit (relaxed load in `log_kv_footprint`); unchanged since Saturday |
| `jhan-amx-p0-v2` | **a92245304d** | **PR 1**, 4 topical commits: eaf8b2c660 kernels + interface + `doc/amx_software_attention.md`; f1f13e3c32 dispatch + V accessors; 77c46a3f90 option + CI flag + README.ci.md; a92245304d tests. Becomes `jhan-amx-p0` only after jhan's go |
| `pr1-stage2` | c9759264dc | PR 1 as a linear WIP history (same tree as `jhan-amx-p0-v2`); edit here, then regenerate the topical commits |
| `jhan-amx-k-mirror` | **cca2960f5f** | **PR 2**, 1 commit on PR 1 a92245304d |
| `jhan-amx-p0` | 60d66d9c04 | the live #3879 head; untouched. Tag `pr3879-pre-split` marks it (local only) |

Base of PR 0, PR 0b and PR 1 is main a80b102c18. origin/main has moved past it (37 files as of
2026-09-06, including `src/tron/CMakeLists.txt`, which PR 1 also touches); the PRs are pushed on
their own base and rebased later if the reviewers ask.

Files in this folder (`PR3879/new-PRs/`):

- `PR0/pr-body.md`, `PR0b/pr-body.md`, `PR1/pr-body.md`, `PR2/pr-body.md`: the PR descriptions, final
  except for placeholders. `PR1/thread-map.md`: Ben's and Jeremy's comments mapped to the new code,
  line numbers filled at the current tips. `PR1/issue-3997-comment.md`: the correction for issue
  #3997 (pure posted text; the posting note is in `issue-3997-comment.NOTE.md`, which is NOT posted).
  `*.v1-20260905.md`: the Saturday drafts, for comparison. `*/status.html`: generated status pages.
- Placeholders to fill before posting: `VERIFICATION-PLACEHOLDER` (PR0, PR1, PR2 bodies: the build and
  test results); `LINE-NUMBER-TIP` and `PR0-TIP` (thread map header: the pushed PR 1 and PR 0 tips);
  `PR2-NUMBER-PLACEHOLDER` (issue comment: PR 2's number once opened).
- `reviews/`: eight gpt-6-astra prompt/reply pairs (`gpt-6-astra-prompt-N-*.md`,
  `gpt-6-astra-reply-N-*.md`; 1 plan, 2 PR 1 review, 3 PR 0 and PR 0b texts, 4 PR 1 and PR 2 texts,
  5 the PR 0 date and PR 2 fake fixes, 6 the PR 1 doc fix and PR 2 test header, 7 the six rewritten
  texts, 8 the PR 0 header sentence), two independent agent claim checks of the texts
  (`agent-verify-six-texts-20260906*.json` and `-v2-*`, each with a `-digest.md`), the Saturday
  agent reviews, the reviewed PR 1 diff of Saturday (stale; re-diff before quoting) and
  `pr3879-review-threads.md` (Ben's and Jeremy's threads as fetched 2026-09-05 04:00 UTC; no new
  comments as of 2026-09-06).

Tools (all in `~/workspace/intel-AMX/exec/`):

- `split-verify2.sh <label> <commit> <DISPATCH> <K_MIRROR> <PAGE_SHARE> <tests...>`: builds the
  commit in `/var/tmp/jhan/tron-split-<label>` on delphi-3bda, waits for the guard, runs the tests,
  writes `exec/logs/split-<label>.{log,txt,done}`. `FORMAT=1` runs clang-format-19 on the C++ files
  the commit changes against its merge base with origin/main (fixed today; it diffed against the
  moving origin/main before) and saves the patch as `exec/logs/split-<label>-format.patch`; the
  formatted tree is what gets built. `BENCH="<tests>"` runs `bin/slice bench --update <tests>` after
  the tests and saves `config/test-benchmarks.json` as `exec/logs/split-<label>-test-benchmarks.json`.
- `split-relaunch.sh`: queues the eight steps (PR0-on with format + bench, PR0-off, PR0b, PR1-on with
  format + bench, PR1-off, PR2-on with format, R-mirror, R-canon) on delphi-3bda in one detached
  process. Its SHAs are the tips above (updated 2026-09-06 20:20 UTC). Edit them if a branch moves.
- `split-tools/make_topical.sh <stage2-tip> <new-branch>`: rebuilds PR 1 as the four topical commits
  from a linear tip, on the tip's merge base with origin/main (fixed today: it used the moving
  origin/main before, which would have dropped main's later change to `src/tron/CMakeLists.txt`).
  Run inside the worktree; it prints "tree identical to tip: yes".
- `split-tools/threadmap_lines.sh <PR1 tip> <PR0 tip> <PR0b tip>`: prints the file:line anchors the
  thread map's "New location" column uses (run inside the worktree; re-run after any commit change).
- `split-tools/chain_results.sh [labels]`: one summary per chain step (marker, test lines, format
  patch size, cost-data entries, errors in the log).
- `split-tools/make_trees.py`, `subtract.py`, `concern-map-hunks.csv`: stage-1 tooling; not needed
  unless the split is redone from R.
- `split-status/gen_status.py` + `state.json`: the status pages. Edit `state.json`, run
  `python3 exec/split-status/gen_status.py` from `~/workspace/intel-AMX`.
- `lib-guard.sh`: the guard (backups `lib-guard.sh.bak-20260905*`). `people-check.sh`: the superseded
  Saturday procedure. `sunday-killer-20260906.sh`: not running; ignore.

Logs: `exec/logs/split-PR0-on.log` and `split-R-mirror.log` each hold one "queued" line from Saturday;
the chain never built anything. No `.done`, `.txt`, format patch or bench json exists yet.

Memory notes (`~/.claude/projects/-home-jhan-workspace-intel-AMX/memory/`): `pr3879-split-progress.md`
(state, tips and traps, updated through 2026-09-06), `3bda-shared-with-bill.md` (the Saturday sharing
rules; superseded by jhan's new scheme), `breakup-pr3879-plan.md` (plan and decisions),
`pal-bridge.md` (PAL recipe).

## What changed since the Saturday handoff (all on 2026-09-06)

Code, each change reviewed by gpt-6-astra (reviews 5, 6 and 8) and covered by the agent claim checks:

- PR 0 (both commits amended): the measurement date in the header comment and the test comment is
  2026-08-18 (the log's own timestamp `# P1 sharing counters, 2026-08-18T19:12:55Z`), not 2026-08-19.
  The header's dump sentence now says "at normal process exit to stderr, if any visit was counted",
  "Low hot-loop cost" instead of "Zero", and the widths "show where several query tokens share a page
  load and where they do not" instead of "are the reason the AMX attention kernels batch queries per
  page" (the PR 1 kernel serves one query token's four heads per page load; it batches no tokens).
- PR 1 (`doc/amx_software_attention.md`, regenerated into commit eaf8b2c660): the +17.5% decode gain
  (qwen-3-4b tp2, 8 users, prompt 8192 tokens) was measured against a separately built binary without
  the option (14.5 to 17.0 tokens/s per user, `tmp/amx-raw-data/chart-check.csv`), not against the
  kill switch; the contract paragraph now says only the nightly rows are same-binary comparisons; the
  CI paragraph says the code compiles "whenever that lane's build step runs"; the MMLU Pro sentence
  states the +1.5 points against the 1.7 points between two unchanged runs. The commit-1 message says
  AMX belongs to "Sapphire Rapids and later Xeons" (the test hosts are Granite Rapids).
- PR 2 (`t/t_amx_dispatch_dtype.cpp`): the test defines every kernel entry point as a CPU fake so the
  linker never pulls `amx_attn.cpp`'s object; PR 2's dispatch calls two more entry points
  (`pack_q_rows_128x4`, `qk_mirror_128x4`) under `TRON_AMX_K_MIRROR`, and the test had no fakes for
  them, so the mirror build would have failed to link the test (the two unresolved symbols pull the
  object, which duplicates the other fakes). Fakes added under the same guard; the header comment was
  reworded per gpt-6-astra (reviews 5 and 6). Not yet built: the PR2-on chain step is the test.

Texts: all six GitHub texts were rewritten against the diffs at the new tips and the evidence files.
About 260 claims were checked in the first agent pass and about 300 in the second; 28 defects were
fixed in the first round and the second round's precision items applied. The largest corrections:
the +17.5% baseline; the arena figures in PR 2 (the server's footprint line labels its values GB but
divides by 2^30 bytes, so they are GiB: 43.8 at 30 minutes, 39.3 to 46.5 for the rest of the hour,
36.5 at the end, not "43.8 to 44.6 GB at peak"); -8.9% not -9% for the qwen TTFT; AMX as a Sapphire
Rapids feature; the constant is spelled `xfeature_xtiledata`; the issue #3997 comment now corrects
only the runner-inventory statement (README.ci.md listed the Granite Rapids runners since 2026-06-02
and 2026-07-07, before the issue was filed on 2026-08-26) and says PR 1 implements only the
`TRON_AMX_DISPATCH` half of option 1. gpt-6-astra's remaining suggestions for the in-tree document
(expanding FPGA, CI and CPU; splitting every sentence into one clause) were not adopted; jhan may want
them.

Machine timeline: the nightly CI held the lease from 03:37 to 11:27 UTC (run 34009467357, success).
The blackout file was removed at 17:22 UTC on jhan's conditional go. Bill was actively using the
machine from about 15:56 UTC (eight `eoe_engine` processes at about 98% CPU each, all 512 hugepages,
later four processes) through at least 21:25 UTC, with fresh logins at 17:20, 18:49 and 20:52 UTC,
so every people-check said WAIT or YIELD and the chain was never launched. At about 21:30 UTC jhan
stopped the monitoring and announced a new sharing scheme.

## What is verified and what is not

| Claim | Status | Evidence |
|---|---|---|
| Stage 1 partition is exact: PR 0 + PR 1 + PR 2 = R minus `t_amx_logit_ab` | verified (Saturday) | `reviews/agent-verify-pure-subtraction.json`; today's changes are comment lines, one doc paragraph and one test's fakes |
| PR 1 contains no mirror symbol, macro, option or test | verified | grep over the tree; agent reviews |
| PR 1 compiles | **not verified**: no compiler on this host | the PR1-on / PR1-off chain steps are the test |
| PR 2's test links in the mirror build after today's fix | **not verified** | the PR2-on chain step is the test; gpt-6-astra (review 6) agrees the fakes are complete and the counts hold |
| All added lines within 88 columns | verified by scan | the chain's `FORMAT=1` steps report any residual clang-format patch |
| Cost-data entries for `t_page_share_counters`, `t_amx_numerics`, `t_amx_dispatch_dtype` | **missing**; CI's `bin/slice bench --check` fails without them | the chain's `BENCH=` steps produce them |
| Real-AMX execution of the kernel tests on the PR 1 tip | **missing** | the PR1-on step on delphi-3bda (Granite Rapids) |
| The six GitHub texts state only supported facts | verified by gpt-6-astra (reviews 3, 4, 7) and two agent passes, except the placeholders | `reviews/` |
| Round-1 numbers in the PR bodies | measured before the split (`PR3879/more-testing/round-1/status.md`) | the qwen 8-user / prompt-8192 re-run on the PR 1 tip is not part of this handoff |

## Execution steps

### Step 0: get the machine under jhan's new scheme

Do nothing on delphi-3bda until jhan states the new scheme. When it is stated, follow it literally.
The chain's own guards still apply on top: each step calls `wait_for_dut_free` (CI lease, other
person active, blackout window; polls every 5 minutes, up to 12 hours) and `campaign_guard_acquire`.
If the new scheme conflicts with `other_user_active` (for example, jhan and Bill agree to share the
cores while Bill's processes run), the guard must be changed in a copy of `lib-guard.sh` and
`split-verify2.sh` must be pointed at that copy; ask jhan before weakening a guard. Read-only state
check that is always allowed:

```sh
ssh delphi-3bda 'source ~/workspace/intel-AMX/exec/lib-guard.sh; ci_lease_busy && echo CI-busy || echo CI-free;
  GUARD_OTHER_USERS=bill other_user_active && echo BILL-ACTIVE || echo bill-idle; who -u; uptime;
  grep -E "HugePages_(Total|Free)" /proc/meminfo'
```

### Step 1: run the chain and watch it

```sh
~/workspace/intel-AMX/exec/split-relaunch.sh          # prints the number of chain processes (expect 2 or 3)
bash ~/workspace/intel-AMX/exec/split-tools/chain_results.sh   # summary of every step so far
```

Expected per step, in order (a step passes when its `.done` says `ok` and every test line in `.txt`
reads `All tests passed`):

| Step | Commit | Configuration | Tests that must pass | Extras |
|---|---|---|---|---|
| PR0-on | 4f4c4d4f4c | counters option ON | t_page_share_counters, t_llama_unit | format patch; bench for t_page_share_counters |
| PR0-off | 4f4c4d4f4c | default | same two | |
| PR0b | e2f22c7a09 | default | t_llama_unit | |
| PR1-on | a92245304d | TRON_AMX_DISPATCH ON | t_amx_numerics (must NOT print "AMX unavailable"), t_amx_dispatch_dtype, t_llama_unit | format patch; bench for t_amx_numerics t_amx_dispatch_dtype |
| PR1-off | a92245304d | default | the three (the AMX tests are skip stubs) | |
| PR2-on | cca2960f5f | DISPATCH + K_MIRROR ON | t_amx_mirror, t_amx_arena_leak, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit | format patch |
| R-mirror, R-canon | e449b11452 | both / DISPATCH only | the five / the three | Day-1 gate of the plan |

`bin/slice bench --update` may refuse on a busy machine (it wants the box idle). If the `.txt` says
`bench rc=` non-zero, re-run it by hand later in a fresh worktree when the machine is idle, or ask
gpt-6-astra how to satisfy `bin/slice bench --check` otherwise (`doc/slice-benchmark-lifecycle.md` in
the tron tree).

### Step 2: if a step fails

Read `exec/logs/split-<label>.log` and give the error, the file at that revision
(`git -C ~/workspace/ai-runs/tron-split show <tip>:<path>`) and the relevant reviews to gpt-6-astra
(section 7). Fix on the right branch:

- PR 0: edit on `jhan-page-share-counters`. To amend the first commit: `git checkout --detach c3e405b2b5`,
  edit, `git commit --amend --no-edit -a -q`, `git cherry-pick 4f4c4d4f4c`, `git branch -f
  jhan-page-share-counters HEAD`, `git checkout jhan-page-share-counters` (one command each, rule 8).
- PR 1: edit on `pr1-stage2`, commit, then `bash ~/workspace/intel-AMX/exec/split-tools/make_topical.sh
  pr1-stage2 jhan-amx-p0-v2` (inside the worktree). Then re-stack PR 2: `git rebase --onto
  jhan-amx-p0-v2 <old PR 1 tip> jhan-amx-k-mirror`; PR 2 touches none of the files PR 1's doc fix
  touched, so the rebase has been conflict-free today.
- PR 2: edit on `jhan-amx-k-mirror`, `git commit --amend --no-edit -a -q`.

Re-run only the failed steps: copy the matching line out of `split-relaunch.sh`, change the SHA, and
launch it with the same `ssh ... setsid nohup bash -c "..."` wrapper. Update the SHAs in
`split-relaunch.sh` and in `split-status/state.json`.

### Step 3: apply the clang-format patches

For each non-empty `exec/logs/split-<label>-format.patch`: apply it to the branch's linear tip
(`git apply` on `pr1-stage2`, on `jhan-page-share-counters`, on `jhan-amx-k-mirror`), commit or amend,
regenerate PR 1's topical commits and re-stack PR 2 as in step 2. Rebuild the changed tips (queue the
PR1-on / PR0-on / PR2-on steps again) so the tested SHA is the pushed SHA.

### Step 4: commit the cost-data entries

`exec/logs/split-PR0-on-test-benchmarks.json` and `split-PR1-on-test-benchmarks.json` are the tron
`config/test-benchmarks.json` with the new entries (platform block `granite_rapids_6962p`). Diff each
against main's file and keep only the added entries:

- PR 0: copy into the worktree on `jhan-page-share-counters`, commit as a third commit
  "config: cost data for t_page_share_counters (granite_rapids_6962p)". PR 0's body already says the
  file gains this entry.
- PR 1: copy into the worktree on `pr1-stage2`, commit, regenerate the topical commits (the script
  folds the file into the tests commit), re-stack PR 2. PR 1's body already lists the file under
  commit 4.
- PR 2's own tests (`t_amx_mirror`, `t_amx_arena_leak`) have no entries either. Optional: run
  `BENCH="t_amx_mirror t_amx_arena_leak"` with the PR2-on step and commit the result on
  `jhan-amx-k-mirror`.

### Step 5: push PR 0 (draft) and PR 0b (draft)

Fill `VERIFICATION-PLACEHOLDER` in `PR0/pr-body.md` with the actual results (commit, option ON and
OFF, CPU Xeon 6962P, both tests' Catch2 summary lines). Have gpt-6-astra read the final body against
the tree (section 7). Then:

```sh
cd ~/workspace/ai-runs/tron-split
git push -u origin jhan-page-share-counters
gh pr create --repo positron-ai/tron --draft --base main --head jhan-page-share-counters \
  --title "page_share_counters: count query tokens per KV page visit (instrumentation, default off)" \
  --body-file ~/workspace/intel-AMX/PR3879/new-PRs/PR0/pr-body.md --label "Skip benchmarks"
git push -u origin jhan-kv-footprint-memorder
gh pr create --repo positron-ai/tron --draft --base main --head jhan-kv-footprint-memorder \
  --title "kv_cache: load last_print_bytes with a valid memory order" \
  --body-file ~/workspace/intel-AMX/PR3879/new-PRs/PR0b/pr-body.md --label "Skip benchmarks"
```

Watch the CI runs (`gh pr checks <number>`); record the PR numbers and run ids in `state.json`.

### Step 6: PR 1, only after jhan's go

Report to jhan first: the build and test lines of PR1-on and PR1-off, the R gate results, whether the
format patch was empty, that the cost data is committed, and the open decisions (section 8). On
jhan's go:

```sh
cd ~/workspace/tron-amx && git status --short          # must be clean; it is the checkout of jhan-amx-p0
git tag -f pr3879-pre-split 60d66d9c04
git push origin pr3879-pre-split:refs/heads/jhan-amx-p0-pre-split   # the body says this branch exists
git reset --hard jhan-amx-p0-v2
git push --force-with-lease=jhan-amx-p0:60d66d9c04 origin jhan-amx-p0
gh pr edit 3879 --repo positron-ai/tron \
  --title "AMX software attention, canonical path: kernel + dispatch, default-off" \
  --body-file ~/workspace/intel-AMX/PR3879/new-PRs/PR1/pr-body.md --add-label "Skip benchmarks"
```

Before the `gh pr edit`, fill `VERIFICATION-PLACEHOLDER` in `PR1/pr-body.md`. Then fill
`LINE-NUMBER-TIP` (the pushed PR 1 tip) and `PR0-TIP` (the pushed PR 0 tip) in
`PR1/thread-map.md`, check its anchors with `threadmap_lines.sh <PR1 tip> <PR0 tip> e2f22c7a09`, and
post it: `gh pr comment 3879 --body-file .../PR1/thread-map.md`. Post the #3997 correction only if
jhan agrees (fill `PR2-NUMBER-PLACEHOLDER` after step 7): `gh issue comment 3997 --body-file
.../PR1/issue-3997-comment.md`. Note `~/workspace/tron-amx/gen` (the build directory) belongs to the
old head; a rebuild there needs a fresh configure.

### Step 7: PR 2 as a stacked draft

**Deferred (decision 5, 2026-09-07): do not run this step until jhan asks; PR 2 ranks below the single-K series.**

Fill `VERIFICATION-PLACEHOLDER` in `PR2/pr-body.md` from the PR2-on results, then:

```sh
cd ~/workspace/ai-runs/tron-split && git push -u origin jhan-amx-k-mirror
gh pr create --repo positron-ai/tron --draft --base jhan-amx-p0 --head jhan-amx-k-mirror \
  --title "K mirror arena for the AMX attention kernels (reference draft; not for review)" \
  --body-file ~/workspace/intel-AMX/PR3879/new-PRs/PR2/pr-body.md --label "Skip benchmarks"
```

### Step 8: keep the record current

After each step: edit `exec/split-status/state.json`, run `python3 exec/split-status/gen_status.py`
from `~/workspace/intel-AMX`, and update the memory note `pr3879-split-progress.md`.

## How to work with gpt-6-astra through PAL

Bridge: `~/bin/pal_mcp_client.py`. gpt-6-astra is not in PAL's bundled registry, so every call needs
`OPENAI_MODELS_CONFIG_PATH=$HOME/bin/pal_openai_models.json`. Each call spawns a fresh server: there
is no continuation, so every prompt must be self-contained and attach every file it needs. When the
model answers with `"status": "files_required_to_continue"`, relaunch with the listed files attached
(it did so once today when given only a header excerpt). Attached files are limited to about 269K
tokens in total. Calls take 3 to 8 minutes at `thinking_mode: max`; run them detached and watch the
output file. Build the request with a small Python script (inner heredoc markers must differ from the
outer shell's, or use a script file):

```sh
cd <scratch dir>; mkdir -p pal-in pal-out
python3 - <<'PY' > pal-in/req.json
import json,os
SP=os.getcwd()
files=["pal-in/a.diff", "pal-in/b.md"]   # paths relative to the scratch dir, attached as absolute paths
args={"prompt":open("pal-in/prompt.md").read(),"model":"gpt-6-astra","thinking_mode":"max",
      "temperature":0.2,"working_directory_absolute_path":SP,
      "absolute_file_paths":[f"{SP}/{f}" for f in files]}
print(json.dumps(args))
PY
OPENAI_MODELS_CONFIG_PATH=$HOME/bin/pal_openai_models.json PAL_TIMEOUT=1500 setsid nohup \
  python3 ~/bin/pal_mcp_client.py chat - < pal-in/req.json > pal-out/reply.raw 2> pal-out/reply.err &
# later:
python3 -c "import json;print(json.load(open('pal-out/reply.raw'))['content'])" > pal-out/reply.md
```

The eight prompts in `reviews/gpt-6-astra-prompt-*.md` are working examples (what to attach for a
build failure, for a code change, for PR texts). Ask for exact replacement text and exact fixes; mark
the writing rules; tell the model to flag what it is unsure of. Its replies over-fragment prose into
one-clause sentences and expand every acronym; keep the sense, not the style. Verify every quoted
line number against the tree (it quotes diff-file lines, not source lines, unless told otherwise).

## Open decisions for jhan (surface them in the report, do not decide)

1. The kernel cases of `t_amx_numerics` execute AMX only when the CI test job lands on a Granite
   Rapids runner (issue #3997 option 1); tron's AGENTS.md test policy calls that an exception only
   the user can grant. Stated in PR 1's body; jhan confirms or changes it.
2. PR 0 does not touch the CI workflow (the test carries its own define); the plan had the CMake lane
   switch the option on. jhan's call.
3. `t_llama_unit`'s AMX eligibility case overlaps the first test of `t_amx_numerics`; kept because it
   was in the original PR. jhan may drop it.
4. Whether to post the issue #3997 correction, and whether PR 0b opens as ready instead of draft.
5. The plan's Day 4 and 5 measurements and the re-run of the qwen 8-user / prompt-8192 cell on the
   PR 1 tip are not part of this handoff; they need machine time jhan has to allot.
6. New: PR 2 rewrites the `kv_cache.hpp` line that PR 0b fixes (the release-order load, with the
   mirror term added), so the two conflict if both land; and PR 2's version keeps the release order.
7. New: whether to adopt gpt-6-astra's style suggestions for `doc/amx_software_attention.md`
   (acronym expansions, one clause per sentence), which were not applied.

## Traps already hit (do not repeat)

- `bin/slice bench --check` in CI fails for a test without a cost-data entry on any platform.
- `campaign_guard_acquire` returns immediately (refuses) when another session holds the flock;
  `split-verify2.sh` retries, the older `split-verify.sh` does not.
- Editing a running bash script corrupts it; `pkill -f <pattern>` inside an ssh command kills the ssh
  shell itself when the pattern appears in its command line (use `pkill -f 'patter[n]'`).
- NFS: a file edited on this host and built on delphi-3bda within seconds can compile stale content;
  the chain builds committed SHAs in a local-disk worktree, which avoids this.
- This host (claude-agentsrv) has no nix and no compiler; do not try to build here.
- The classifier blocks compound history-rewrite git commands (rule 8).
- `make_topical.sh` must base on the PR's merge base, not origin/main (fixed today; keep it so).
- The server's KV footprint log line labels its values GB but divides by 2^30; treat them as GiB.
- A shell heredoc that contains another heredoc with the same marker ends early and runs the rest as
  commands (happened while writing this file; use distinct markers or the Write tool).
- The plan page's weekday labels are off by one (2026-09-04 was a Friday).
- `mask_t<N>` exists only for N in 8..128, 512 and 4096; plugins declare `max_minibatch_size` 128
  (llama) and 1024 (mock, every ingested plugin).

## Definition of done for this handoff

- Every chain step's `.done` says `ok` and every test line says `All tests passed`;
  `t_amx_numerics` in PR1-on and PR2-on printed no "AMX unavailable" warning.
- Format patches applied (or empty) and cost-data entries committed on PR 0 and PR 1.
- PR 0 pushed and open as a draft with `Skip benchmarks`; PR 0b pushed and open as a draft; CI green
  on both (or the failure understood and reported).
- jhan has the PR 1 report (results, evidence, open decisions) and has answered; on a go, #3879
  force-pushed, retitled, described, thread map posted; PR 2 open as a draft on it.
- Status pages and the memory note reflect the end state.
