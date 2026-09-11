# Handoff: finish the PR 3879 split (written Saturday 2026-09-05, 22:10 PDT)

## Short version

The code work of the split is done and reviewed; it sits in local branches that nobody has
pushed. What remains is machine verification on delphi-3bda (build, tests, clang-format, the
cost-data entries CI demands), then pushing PR 0 as a draft, pushing PR 0b, and asking jhan for
the go before force-pushing PR 1 onto #3879. delphi-3bda is on hold until jhan says it may be
used again (jhan is syncing with Bill Saturday night). Use PAL to work with gpt-6-astra on every
substantive judgment during the execution: reading build failures, any code change, the final
PR texts. Everything you need is listed below with exact commands.

## Words used here

- **tron / rinzler / runtron**: tron is the inference program; rinzler is its production
  server, built from tron; runtron is its command-line tool.
- **PR 3879**: the original pull request "AMX software attention (default-off): QK/PV tile
  kernels + K-mirror arena", branch `jhan-amx-p0`, old head 60d66d9c04 (local tag
  `pr3879-pre-split`). It is being split into PR 0 (page-share counters), PR 1 (the canonical
  AMX path, reusing #3879) and PR 2 (the K mirror, a reference draft), plus PR 0b (a one-line
  fix). The plan is `PR3879/breakup-PR3879.html`; jhan's decisions are in its section 8.
- **AMX / AVX-512**: AMX (Intel Advanced Matrix Extensions) is the tile-matrix instruction
  set the new kernels use; AVX-512 is the vector instruction set the existing attention loop
  (the "dotter") uses.
- **canonical / row-major K**: the attention keys K kept in today's single storage and read
  as stored (PR 1). **K mirror**: a second copy of K in the VNNI layout, kept in ordinary RAM
  and written through on every K store (PR 2, opt-in `TRON_AMX_K_MIRROR`).
- **R**: the whole PR 3879 tree rebased (squash-merged) onto main a80b102c18, commit
  e449b11452, branch `split-base-R`. PR 0 + PR 1 + PR 2 reproduce R minus one parked tool.
- **stage 1 / stage 2**: stage 1 = the pure subtraction of R into the three PRs (no text
  changes, byte-checked); stage 2 = the edits on top (renames, prose, Ben's review items,
  the kill-switch document, CMake option placement, CI flag).
- **the guard**: `exec/lib-guard.sh` on delphi-3bda; `campaign_guard_acquire` refuses when
  the nightly CI holds the lease, when another person is actively using the machine
  (`other_user_active`, Bill), or during a blackout window (`blackout_active`, file
  `/var/tmp/jhan/3bda-blackout`).
- **PAL / gpt-6-astra**: PAL is the MCP bridge to external models (`~/bin/pal_mcp_client.py`);
  gpt-6-astra is the OpenAI model jhan wants used for this work.
- **the chain**: `exec/split-verify2.sh` runs one build-and-test step of one commit on
  delphi-3bda; `exec/split-relaunch.sh` queues the eight steps in order.

## Ground rules (from jhan, in force)

1. **delphi-3bda is on hold.** jhan (Saturday 2026-09-05, late evening PDT): "please hold
   using the machine. I will sync with Bill tomorrow night." Do not launch anything there,
   not even a compile, until jhan says the machine may be used. Read-only ssh to look at a log
   is acceptable; nothing that runs work is. The blackout file on 3bda enforces this until
   Monday 00:00 PDT (07:00 UTC 2026-09-07); when jhan gives the go, remove or shorten it (step
   0 below). Bill shares the machine Saturday to Monday; the guard's `other_user_active`
   check stays on.
2. **Use PAL with gpt-6-astra for the execution.** Every substantive step goes through
   gpt-6-astra: interpreting a build or test failure, any code change on any branch, the
   final wording of PR descriptions and the thread map, and the go/no-go summary for jhan.
   Recipe in section 7. You remain responsible for the result; treat the model's output as
   input to verify, not as a decision.
3. **What may be pushed without asking**: PR 0's branch and a **draft** PR for it; PR 0b's
   branch and its PR (open it as a draft too, and let jhan decide whether to mark it ready).
   **PR 1 (force-push of `jhan-amx-p0`, retitle of #3879) only after jhan's explicit go**,
   given in this conversation or in writing. PR 2 is pushed and opened as a draft only after
   PR 1 is pushed (it is stacked on PR 1).
4. **No messages to Ben, Bill or Jeremy** from this work (jhan communicates directly). The
   only posts the plan allows are the review thread map as a comment on #3879 after the
   force-push, and a correction comment on issue #3997; both drafts exist; post them only
   after jhan's go for PR 1.
5. Labels: `Skip benchmarks` on every PR; never `Run CI`. Stack policy (tron AGENTS.md): only
   a PR based on main may be ready for review; PR 2 stays a draft.
6. Never edit a bash script while a queued step is executing it (bash reads scripts
   incrementally from NFS; a live edit corrupts the running instance). Copy to a new file
   instead.
7. Write in plain English (define terms at first use, one claim per sentence, numbers with
   units); keep the status pages current (section 6, step 8).

## Where everything is

Worktree: `~/workspace/ai-runs/tron-split` (a worktree of the shared repo whose main checkout
is `~/workspace/tron-amx`, branch `jhan-amx-p0`; the repo is NFS-shared with delphi-3bda).
Working tree is clean; check with `git -C ~/workspace/ai-runs/tron-split status`.

| Branch | Tip | What it is |
|---|---|---|
| `split-base-R` | e449b11452 | R: whole PR on main a80b102c18 (Day 1 rebase, 5 conflict blocks resolved) |
| `pr0-pure`, `pr1-pure`, `pr2-pure` | fc05957a32, b7ecdbe7ef, 4670f7233b | stage-1 pure subtraction, kept for reference |
| `jhan-page-share-counters` | b5714afd54 | **PR 0**, 2 commits (header + 5 hooks; top-level CMake option + host test `t_page_share_counters`) |
| `jhan-kv-footprint-memorder` | e2f22c7a09 | **PR 0b**, 1 commit (relaxed load in `log_kv_footprint`) |
| `jhan-amx-p0-v2` | 2746d408b9 | **PR 1**, 4 topical commits (21c81721b5 kernel + interface + `doc/amx_software_attention.md`; then dispatch + V accessors; then option + CI flag + README.ci.md; then tests). Becomes `jhan-amx-p0` only after jhan's go |
| `jhan-amx-k-mirror` | d8189f19ce | **PR 2**, 1 commit on PR 1 (reference draft) |
| `pr1-stage2` | 360f4f8791 | PR 1 as a linear WIP history (same tree as `jhan-amx-p0-v2`); edit here, then regenerate the topical commits |
| `jhan-amx-p0` | 60d66d9c04 | the live #3879 head; untouched. Tag `pr3879-pre-split` marks it |

Files in this folder (`PR3879/new-PRs/`):

- `PR0/`, `PR0b/`, `PR1/`, `PR2/`: `status.html` (generated), `pr-body.md` (PR description
  draft), `PR1/thread-map.md` (Ben's and Jeremy's comment ids mapped to the new code; line
  numbers still to fill), `PR1/issue-3997-comment.md` (draft correction for issue #3997).
- `reviews/`: gpt-6-astra prompts and replies (`gpt-6-astra-prompt-1-plan.md`,
  `gpt-6-astra-reply-1-subtraction-prose-ben-items.md`, `gpt-6-astra-prompt-2-review.md`,
  `gpt-6-astra-reply-2-pr1-review.md`), the two agent review results
  (`agent-verify-pure-subtraction.json`, `agent-review-pr1-four-lenses.json`) and the PR 1
  diff those reviews looked at (`pr1-stage2b-diff-reviewed.diff`; the branch has since gained
  the correction commits, so re-diff before quoting).

Tools (all in `~/workspace/intel-AMX/exec/`):

- `split-verify2.sh <label> <commit> <DISPATCH> <K_MIRROR> <PAGE_SHARE> <tests...>`: builds
  the commit in an isolated worktree on 3bda's local disk (`/var/tmp/jhan/tron-split-<label>`),
  waits for the guard, runs the tests, writes `exec/logs/split-<label>.{log,txt,done}`.
  `FORMAT=1` runs clang-format-19 on the changed C++ files first and saves the diff as
  `exec/logs/split-<label>-format.patch` (the formatted tree is what gets built).
  `BENCH="<tests>"` runs `bin/slice bench --update <tests>` after the tests pass and saves the
  resulting `config/test-benchmarks.json` as `exec/logs/split-<label>-test-benchmarks.json`.
- `split-relaunch.sh`: queues the eight steps (PR0-on with format + bench, PR0-off, PR0b,
  PR1-on with format + bench, PR1-off, PR2-on with format, R-mirror, R-canon) on 3bda in one
  detached process. Edit the SHAs at the top if a branch moves.
- `split-tools/make_topical.sh <stage2-tip> <new-branch>`: rebuilds PR 1 as the four topical
  commits from a linear tip (run inside the worktree); prints "tree identical to tip: yes".
- `split-tools/make_trees.py`, `subtract.py`, `concern-map-hunks.csv`: the stage-1 tooling and
  the verified concern map (PR-head line ranges by concern). Not needed again unless the
  split has to be redone from R.
- `split-status/gen_status.py` + `state.json`: the status pages. Edit `state.json`, run the
  script, it rewrites the four `status.html` files.
- `lib-guard.sh`: the guard (`blackout_active` was added on 2026-09-05; backup
  `lib-guard.sh.bak-20260905b`).
- `sunday-killer-20260906.sh`: no longer running; ignore.

Logs: `exec/logs/split-*.log` (full build log), `split-*.txt` (one summary line per test),
`split-*.done` (marker: `ok`, `build-failed`, `guard-never-free`, `dut-never-free`). Only
`split-PR0-on.log` exists so far, with a single "queued" line; the chain never built.

Memory notes for the next session (in `~/.claude/projects/-home-jhan-workspace-intel-AMX/memory/`):
`pr3879-split-progress.md` (state and traps), `3bda-shared-with-bill.md` (the hold),
`breakup-pr3879-plan.md` (plan and decisions), `pal-bridge.md` (PAL recipe).

## What is verified and what is not

| Claim | Status | Evidence |
|---|---|---|
| Stage 1 partition is exact: PR 0 + PR 1 + PR 2 = R minus the parked tool `t_amx_logit_ab` | verified | added-line multiset checks in this session; independent agent pass (`reviews/agent-verify-pure-subtraction.json`); its two findings (a lost closing brace in t_llama_unit.cpp, two mirror fakes in the dtype test) were fixed in stage 2 |
| PR 1 contains no mirror symbol, macro, option or test | verified | grep over the tree; agent review |
| PR 1 compiles | **not verified**: no compiler on this host (no nix); two read-only reviews found no compile error (`reviews/gpt-6-astra-reply-2-pr1-review.md` section 1; `agent-review-pr1-four-lenses.json`, lens "compile") | the 3bda chain is the test |
| PR 1's AVX path equals main's and its AMX path equals R's, statement for statement | verified by reading (both reviews) | same files |
| All added lines are within 88 columns (`.clang-format` limit) | verified by a line-length scan; clang-format-19 may still re-break a line | the chain's `FORMAT=1` step reports any residual patch |
| CI cost-data entries for `t_page_share_counters`, `t_amx_numerics`, `t_amx_dispatch_dtype` | **missing**; CI's `bin/slice bench --check` fails without them | the chain's `BENCH=` steps produce them |
| Real-AMX execution of the kernel tests on the PR 1 tip | **missing** | the chain's PR1-on step on 3bda (Granite Rapids) |
| Round-1 numbers quoted in the PR bodies | measured before the split (PR3879/more-testing/round-1/status.md) | the plan asks to re-run the qwen 8-user / prompt-8192 canonical cell on the PR 1 tip before quoting it as PR evidence; not done |

## Execution steps

### Step 0: wait for jhan's go, then lift the hold

Do nothing on 3bda until jhan says the machine may be used. Then:

```sh
ssh delphi-3bda 'cat /var/tmp/jhan/3bda-blackout; rm -f /var/tmp/jhan/3bda-blackout;
  source ~/workspace/intel-AMX/exec/lib-guard.sh; ci_lease_busy && echo CI-busy || echo CI-free;
  other_user_active && echo OTHER-USER-ACTIVE || echo no-other-user; uptime'
```

If Bill is active (`OTHER-USER-ACTIVE`) or the CI lease is busy, the chain will wait on its
own (`wait_for_dut_free`, polling every 5 minutes, up to 12 hours per step); that is fine.
The nightly CI holds the machine from about 03:30 UTC to about 09:30 UTC.

### Step 1: run the chain and watch it

```sh
~/workspace/intel-AMX/exec/split-relaunch.sh          # prints the number of chain processes (expect 2 or 3)
ls -la ~/workspace/intel-AMX/exec/logs/split-*.done  # appears per finished step
cat ~/workspace/intel-AMX/exec/logs/split-PR1-on.txt # one line per test
```

Watch by polling the `.done` markers (the log directory is on NFS, visible from this host);
do not poll 3bda itself more than needed. A step passes when its `.done` says `ok` and every
test line in `.txt` reads `All tests passed` (Catch2's summary). Expected per step, in order:

| Step | Commit | Configuration | Tests that must pass | Extras |
|---|---|---|---|---|
| PR0-on | b5714afd54 | counters option ON | t_page_share_counters, t_llama_unit | format patch; bench for t_page_share_counters |
| PR0-off | b5714afd54 | default | same two | |
| PR0b | e2f22c7a09 | default | t_llama_unit | |
| PR1-on | 2746d408b9 | TRON_AMX_DISPATCH ON | t_amx_numerics (must NOT print "AMX unavailable"), t_amx_dispatch_dtype, t_llama_unit | format patch; bench for t_amx_numerics t_amx_dispatch_dtype |
| PR1-off | 2746d408b9 | default | the three (the AMX tests are skip stubs) | |
| PR2-on | d8189f19ce | DISPATCH + K_MIRROR ON | t_amx_mirror, t_amx_arena_leak, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit | format patch |
| R-mirror, R-canon | e449b11452 | both / DISPATCH only | the five / the three | Day-1 gate of the plan (the rebase itself is sound) |

`bin/slice bench --update` may refuse on a busy machine (it needs the box idle for its
timing). If the `.txt` says `bench rc=` non-zero, re-run it by hand later in a fresh worktree
when the machine is idle, or ask gpt-6-astra how to satisfy `bin/slice bench --check`
otherwise (`doc/slice-benchmark-lifecycle.md` in the tron tree explains the file).

### Step 2: if a step fails

Read `exec/logs/split-<label>.log` (compile errors are grepped into it) and give the error,
the file at that revision (`git -C ~/workspace/ai-runs/tron-split show <tip>:<path>`) and
the reviews to gpt-6-astra (section 7). Fix on the right branch:

- PR 0: edit on `jhan-page-share-counters`, `git commit --amend` into the right one of its
  two commits (or add a third if it is a distinct concern).
- PR 1: edit on `pr1-stage2`, commit, then regenerate the topical branch:
  `bash ~/workspace/intel-AMX/exec/split-tools/make_topical.sh pr1-stage2 jhan-amx-p0-v2`
  (inside the worktree; it prints "tree identical to tip: yes"). Then re-stack PR 2:
  `git rebase --onto jhan-amx-p0-v2 <old PR 1 tip> jhan-amx-k-mirror` and resolve any
  conflict (PR 2 touches the same helpers; keep PR 1's text and add PR 2's `#ifdef
  TRON_AMX_K_MIRROR` blocks).
- PR 2: edit on `jhan-amx-k-mirror`, `git commit --amend`.

Re-run only the failed steps: copy the matching line out of `split-relaunch.sh`, change the
SHA, and launch it with the same `ssh ... setsid nohup bash -c "..."` wrapper. Update the
SHAs in `split-relaunch.sh` and in `split-status/state.json`.

### Step 3: apply the clang-format patches

For each non-empty `exec/logs/split-<label>-format.patch`: apply it to the branch's linear
tip (`git apply` on `pr1-stage2`, on `jhan-page-share-counters`, on `jhan-amx-k-mirror`),
commit or amend, regenerate the topical commits for PR 1 (make_topical.sh) and re-stack PR 2
as in step 2. A patch that only re-breaks lines needs no new build for correctness; still
prefer to rebuild the changed tip so the tested SHA is the pushed SHA (queue just the
PR1-on / PR0-on / PR2-on steps again).

### Step 4: commit the cost-data entries

`exec/logs/split-PR0-on-test-benchmarks.json` and `split-PR1-on-test-benchmarks.json` are
the tron `config/test-benchmarks.json` with the new entries (platform block
`granite_rapids_6962p`). Diff each against main's file and keep only the added entries:

- PR 0: copy into the worktree on `jhan-page-share-counters`, commit as a third commit
  "config: cost data for t_page_share_counters (granite_rapids_6962p)".
- PR 1: copy into the worktree on `pr1-stage2`, commit, regenerate the topical commits (the
  script folds the file into the tests commit), re-stack PR 2.
- PR 2's own tests (`t_amx_mirror`, `t_amx_arena_leak`) have no entries either; CI on the
  draft would fail its cost-data check. Optional: run `BENCH="t_amx_mirror t_amx_arena_leak"`
  with the PR2-on step and commit the result on `jhan-amx-k-mirror`.

Other runner classes (genoa96, genoa32, granite_rapids_6960p) get their entries from the
weekly `bench-refresh` workflow; CI only requires one platform.

### Step 5: push PR 0 (draft) and PR 0b

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

Before pushing, have gpt-6-astra read the final `pr-body.md` files against the tree (section
7) and update the "Verification" paragraph of PR 0's body with the actual 3bda results. After
pushing, watch the CI runs (`gh pr checks <number>`); record the run ids in `state.json`.

### Step 6: PR 1, only after jhan's go

Report to jhan first: the build and test lines of PR1-on and PR1-off, the R gate results,
whether the format patch was empty, that the cost data is committed, and the open decisions
(section 8). Then wait. On jhan's go:

```sh
cd ~/workspace/tron-amx && git status --short          # must be clean; it is the checkout of jhan-amx-p0
git tag -f pr3879-pre-split 60d66d9c04
git push origin pr3879-pre-split:refs/heads/jhan-amx-p0-pre-split   # backup of the old head as a branch
git reset --hard jhan-amx-p0-v2                          # jhan-amx-p0 now points at the four topical commits
git push --force-with-lease=jhan-amx-p0:60d66d9c04 origin jhan-amx-p0
gh pr edit 3879 --repo positron-ai/tron \
  --title "AMX software attention, canonical path: kernel + dispatch, default-off" \
  --body-file ~/workspace/intel-AMX/PR3879/new-PRs/PR1/pr-body.md --add-label "Skip benchmarks"
```

Then fill the "New location" line numbers in `PR1/thread-map.md` from the pushed commits and
post it as a comment on #3879 (`gh pr comment 3879 --body-file ...`). Post the #3997
correction (`PR1/issue-3997-comment.md`) with `gh issue comment 3997 --body-file ...` if jhan
agrees. Note `~/workspace/tron-amx/gen` (the build directory) belongs to the old head; a
rebuild there needs a fresh configure.

### Step 7: PR 2 as a stacked draft

```sh
cd ~/workspace/ai-runs/tron-split && git push -u origin jhan-amx-k-mirror
gh pr create --repo positron-ai/tron --draft --base jhan-amx-p0 --head jhan-amx-k-mirror \
  --title "K mirror arena for the AMX attention kernels (reference draft; not for review)" \
  --body-file ~/workspace/intel-AMX/PR3879/new-PRs/PR2/pr-body.md --label "Skip benchmarks"
```

### Step 8: keep the record current

After each step: edit `exec/split-status/state.json` (step states: done / progress /
waiting / blocked / todo; notes with the evidence), run `python3
exec/split-status/gen_status.py`, and update the memory note `pr3879-split-progress.md`.

## How to work with gpt-6-astra through PAL

Bridge: `~/bin/pal_mcp_client.py`. gpt-6-astra is not in PAL's bundled registry, so every
call needs `OPENAI_MODELS_CONFIG_PATH=$HOME/bin/pal_openai_models.json`. Each call spawns a
fresh server: there is no continuation, so every prompt must be self-contained and attach
every file it needs (the model answers `files_required_to_continue` when one is missing;
then relaunch with the file added). Attached files are limited to about 269K tokens in total.
Calls take 3 to 8 minutes at `thinking_mode: max`; run them in the background:

```sh
cd <scratch dir>; mkdir -p pal-in pal-out
python3 - <<'EOF' > pal-in/req.json
import json,os
SP=os.getcwd()
files=["pal-in/prompt.md", ...]   # absolute paths of the files to attach (not the prompt)
args={"prompt":open("pal-in/prompt.md").read(),"model":"gpt-6-astra","thinking_mode":"max",
      "temperature":0.2,"working_directory_absolute_path":SP,
      "absolute_file_paths":[f"{SP}/{f}" for f in files[1:]]}
print(json.dumps(args))
EOF
OPENAI_MODELS_CONFIG_PATH=$HOME/bin/pal_openai_models.json PAL_TIMEOUT=1500 \
  python3 ~/bin/pal_mcp_client.py chat - < pal-in/req.json > pal-out/reply.raw
python3 -c "import json;print(json.load(open('pal-out/reply.raw'))['content'])" > pal-out/reply.md
```

What to attach for the typical questions of this handoff:

- A build failure: the error lines from `split-<label>.log`, the failing file at the built
  revision (`git show <tip>:<path>`), the interface header
  `h/tron/kernels/amx_attn_iface.hpp`, and `reviews/gpt-6-astra-reply-2-pr1-review.md`
  (so the model knows what was already reviewed). Ask for the minimal fix and for the
  reason the reviews missed it.
- A test failure: the same plus the test source and the Catch2 output.
- PR texts and the thread map: the final diff (`git diff origin/main <tip>`), the drafts,
  `reviews/pr3879-review-threads.md` (Ben's and Jeremy's threads as fetched from GitHub on
  2026-09-05 04:00 UTC; re-fetch with `gh api graphql` if newer comments may exist), and the
  plan page's sections 6 and 8.

Ask for exact replacement text and exact fixes, mark the writing rules (define terms, one
claim per sentence, numbers with units, no idioms), and tell the model to flag anything it is
unsure of. Its earlier replies over-fragmented prose into one-clause sentences; keep the
sense, not the style. Two of its claims in the planning phase were wrong and retracted (see
`breakup-pr3879-plan.md`), so verify quoted line numbers against the tree.

## Open decisions for jhan (surface them in the report, do not decide)

1. The kernel cases of `t_amx_numerics` execute AMX only when the CI test job lands on a
   Granite Rapids runner (issue #3997 option 1); tron's AGENTS.md test policy calls that an
   exception only the user can grant. Stated in PR 1's body; jhan confirms or changes it.
2. PR 0 does not touch the CI workflow (the test carries its own define); the plan had the
   CMake lane switch the option on. jhan's call.
3. `t_llama_unit`'s AMX eligibility case overlaps the first test of `t_amx_numerics`; kept
   because it was in the original PR and checks the model-level alias. jhan may drop it.
4. Whether to post the issue #3997 correction and whether PR 0b opens as ready.
5. The plan's Day 4 and 5 measurements (G1 store cost, G2 GOF cost) and the re-run of the
   qwen 8-user / prompt-8192 canonical cell on the PR 1 tip are not part of this handoff;
   they need machine time jhan has to allot.

## Traps already hit (do not repeat)

- `bin/slice bench --check` in CI fails for a test without a cost-data entry on any platform.
- `campaign_guard_acquire` returns immediately (refuses) when another session holds the
  flock; `split-verify2.sh` retries, the older `split-verify.sh` does not.
- Editing a running bash script corrupts it; `pkill -f <pattern>` inside an ssh command kills
  the ssh shell itself when the pattern appears in its command line (use `pkill -f 'patter[n]'`).
- NFS: a file edited on this host and built on 3bda within seconds can compile stale content;
  check the content on 3bda before building, or commit and build the commit (the chain does).
- This host (claude-agentsrv) has no nix and no compiler; do not try to build here.
- The plan page's weekday labels are off by one (2026-09-04 was a Friday).
- `mask_t<N>` exists only for N in 8..128, 512 and 4096; plugins declare
  `max_minibatch_size` 128 (llama) and 1024 (mock, every ingested plugin).

## Definition of done for this handoff

- Every chain step's `.done` says `ok` and every test line says `All tests passed`;
  `t_amx_numerics` in PR1-on and PR2-on printed no "AMX unavailable" warning.
- Format patches applied (or empty) and cost-data entries committed on PR 0 and PR 1.
- PR 0 pushed and open as a draft with `Skip benchmarks`; PR 0b pushed and open; CI green
  on both (or the failure understood and reported).
- jhan has the PR 1 report (results, evidence, open decisions) and has answered; on a go,
  #3879 force-pushed, retitled, described, thread map posted; PR 2 open as a draft on it.
- Status pages and the memory note reflect the end state.
