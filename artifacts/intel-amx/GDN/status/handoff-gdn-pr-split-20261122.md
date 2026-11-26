# Handoff: split draft PR 5572 (GDN and AMX for Qwen3.5 4B) into four draft PRs

Written 2026-11-22 18:30 PST (2026-11-23 02:30 UTC) by the Claude session that did the work behind PR 5572.
Updated 2026-11-23 12:30 PST by the same session: section 0 is new. The Short version, "Words used here",
sections 1, 2.2, 2.3, 2.4, 3, 4, 5, 7.1, 7.7, 8.1, 8.4, 9, 11 and 12 and the references changed. The file as
it was before is `handoff-gdn-pr-split-20261122.before-20261123.md` in the same folder.
Nothing of the split is done yet. Times are UTC unless a line says PST.

## Short version

Draft PR #5572 of the repository positron-ai/tron holds four separate code changes for the model Qwen3.5 4B.
jhan, the author, decided to replace it with four smaller draft PRs, so that reviewers can read each change
alone. This file gives the next agent the decisions, the present state, the order of work and the checks,
and its section 0 holds news of 2026-11-23 that adds two questions for jhan.

## Words used here

- tron: the inference program. runtron: its command-line tool.
- GDN (GatedDeltaNet): the recurrent layer type in 24 of the 32 layers of Qwen3.5 4B. The other 8 layers are
  attention layers.
- AMX: Intel's tile-matrix instruction set. AVX-512: Intel's 512-bit vector instruction set.
- bf16: a 16-bit floating-point format. A bf16 step is the smallest change of a bf16 value.
- Attention head: one of the parallel parts of an attention layer. Query heads and KV heads are attention
  heads. Head size: the number of values per attention head. "256 wide" means head size 256.
- kv_mul: the number of query heads per KV head.
- Shape: the head size and the kv_mul of an attention layer, for example 256 wide with kv_mul 4.
- Page: a block of 64 tokens of the key and value cache. The AMX attention kernels take only full pages.
- K tokens: the counter of cached keys that a kernel read. It stands in the `[attn-stats]` lines of a run.
- Counters: the GDN path statistics. They count which kernel advanced a token, and they time the GDN work.
- Token loop: today's GDN code. It calls `step()` once per token.
- Part 0: the GDN chain kernel. It advances a window of 32 prompt tokens with AVX-512. It gives the bytes of
  the token loop.
- Part A: the AMX block kernel for GDN. It takes full windows of 32 tokens. Its results lie inside an error
  band around the token loop. They are not the same bytes. This holds while K and Q are bf16 values (section
  0.2).
- Part B: the AMX attention kernels for the shape 256 wide with kv_mul 4 (namespace `amx_attn_h256g4`).
- The model's branch: `rbjarnason/qwen35-native-4b-registry`, the head branch of PR #3696 [R2]. Qwen3.5 4B is
  registered there. It is not on main.
- Plugin: the code that tron generates and compiles for one model variant. Slug: the name of a plugin, as
  runtron takes it.
- E4B: the model Gemma 4 E4B. It is on main. Its 35 sliding-window attention layers have the shape that Part B
  serves. tp4 and permuted are two of its plugins. Their slugs are `ingested-gemma-4-e4b-it-tp4` and
  `ingested-gemma-4-e4b-it-permuted`.
- `TRON_AMX_DISPATCH`: the CMake option that compiles the AMX kernels. Its default is OFF. "The option" in
  this file means this option.
- Kill switch: the environment variable `TRON_AMX_DISABLE=1`. The same binary then runs no AMX kernel.
- GDN kernel switch: `TRON_AMX_GDN_DISABLE=1`. Only the GDN block kernel is then off.
- Counter switch: `TRON_ATTN_STATS=1`, the existing switch of the attention counters. `TRON_GDN_STATS=1` is
  today's separate switch of the GDN counters. The split removes it.
- TTFT: time to first token, in seconds. Decode speed: generated tokens per second per user.
- Prefill: the processing of the prompt before the first generated token. One prefill pass handles 128 prompt
  tokens.
- Scores: the logits, one score per word of the vocabulary.
- Note: a named comment block of the form `Note [title]` in the tron sources. Other comments refer to it by
  its title.
- Head (of a branch or of a PR): its newest commit. An attention head is always written with "attention",
  "query" or "KV", or as "256-wide heads".
- Arm: one build with one set of switches. Cell: one user count with one prompt length. Campaign: the timed
  runs of all arms over all cells. Campaign start: one unbroken run of the campaign script.
- Build tag: the name of a build tree `/var/tmp/jhan/b35-gdn-<tag>` on delphi-3b35.
- delphi-3b35: jhan's test server, an Intel Xeon 6962P machine with AMX. Other users share it.
- Our half: the second half of its FPGA cards (4 accelerator cards, `SYSTEM_CONFIG="--instance 1,2"`) and the
  CPUs 96-143 and 223-230.
- GCP Nix workflow: `gcp-nix.yml`, the CI workflow of every PR. It builds with the option OFF.
- CMake workflow: `cmake-single-platform.yml`, the only CI workflow that builds with the option ON. It starts
  by hand.
- CI runner: a lab machine that executes CI jobs.
- Go: jhan's explicit word that something may be pushed, posted or closed.
- The GDN owner: the author of PR #3696, of PR #3221, of issue #5433 and of draft PR #5571.
- Rounding call: a place where the GDN code rounds a value to bf16. K and Q: the normalized key and the
  normalized query of one token. Part A reads them.
- Conflict region: one block between a `<<<<<<<` line and a `>>>>>>>` line that git writes into a file it
  could not merge.
- Float64 model: the formula of the GDN recurrence, computed in 64-bit floats by a script. It is not a run of
  the kernel.
- Relative L2 norm of a difference: the length of the difference of two matrices, divided by the length of
  the reference matrix. 3e-3 means 0.3 %.
- Recurrent matrix: the FP32 state of one GDN value head. Executor: the class `gdn_rolling_executor`, which
  calls the GDN kernels.
- The rounding task: a second task of jhan, with its own handoff [R20]. Another agent may do it at the same
  time.

## 0. News of 2026-11-23. Read this first.

### 0.1 What the GDN owner said

A Slack group chat of jhan with the GDN owner, 2026-11-23, 10:53 to 10:59 PST [R18]:

- jhan asked for a rough schedule of Qwen3.5 4B and named PR #3696.
- The GDN owner on the schedule: "My guess is mid-to-late December at the current rate, which is limited by
  review pace."
- The GDN owner's advice: "You don't have to wait for it though. The GDN kernels are already on main
  (h/tron/kernels/gated_delta_net.hpp), so the AMX work can branch from main, and you can run Qwen3.5 4b
  end-to-end from the #3696 branch".
- jhan answered: "Yes, I will use this strategy".
- The GDN owner's warning: "Heads up though that #3221 (not merged) parallelizes GDN across key-head groups,
  which changes how the kernel is driven, and we're measuring whether to drop some of the rounding inside the
  layer (issue #5433, draft PR #5571)".

jhan then told the writing session: "Runar has no plan to merge PR3696 soon and asked us to use its branch".
Runar is the GDN owner. The chat gives an estimate for PR #3696, mid-to-late December. It does not say that no
merge is planned.

- jhan's sentence is shorter than the advice. The advice names two things: main as the base of the AMX work,
  and the branch of PR #3696 for the model runs. jhan's sentence names only the branch of PR #3696 and does
  not say for what.
- In the chat jhan accepted the advice as a whole. So the GDN owner may expect the AMX PRs on main.
- So jhan's sentence does not settle the base of the PRs. This file is written for the branch of PR #3696 as
  the base. Question Q4 asks jhan (section 2.3).

A second chat of the same morning, from jhan to the colleague who asked for the AMX work on GDN, 10:47 PST
[R18]:

- PR #5022 is updated after a review, and jhan merges it when it is approved. So the base of PR 4 can merge
  soon. Default U2 says what to do then.
- jhan named the missing merge of PR #3696 as the present blocker of the GDN work. Six minutes later jhan wrote
  to the GDN owner in the group chat: "It is not blocking me as I need to refine the code and do more
  testing".

### 0.2 Facts found on 2026-11-23

Six read-only agents collected them. [R19] names the three fact files that this file uses. No tron code was
built or run.

**The stack of the model**

- main is `f454423b09`. PR #3696 is unchanged at `72e1191804`.
- 12 open PRs lie between main and PR #3696. In order: #3206, #5345, #3205, #3221, #5023, #5486, #5024, #3689,
  #3690, #3692, #3694, #3695. 11 of the 12 have the review state "changes requested". Only #5486 is approved.
- The GDN owner rewrote the lower 7 of the 12 (#3206 to #5024) onto today's main on 2026-11-23. The upper 5
  (#3689 to #3695) and PR #3696 itself are still the commits of 2026-11-17.
- So the model's branch is old. 7 of its 21 commits are on main: 3 as the same patch and 4 in a changed form.
  It holds an older copy of PR #3221.
- It must be rewritten onto the new lower PRs before it can merge. This is our inference from the stack:
  GitHub reports PR #3689 as conflicting. The GDN owner has not said when.
- Qwen3.5 4B is registered only on the model's branch. No commit holds both today's GDN code and the model.

**What each base can hold**

| Base | Counters, Part 0, Part A | Can Qwen3.5 4B run there |
|---|---|---|
| The model's branch `72e1191804` | All of it, as it is. Our commits were made there. | Yes |
| The head of PR #3221, `127a662083` (main plus 4 commits) | All of it, after a port by hand: at least 12 conflict regions in 5 files for the two GDN commits together. No conflict was resolved, and nothing was compiled. | No. The registration and 8 more PRs are above it. |
| main `f454423b09` | Only the files that hold a kernel or the counter types alone: `gdn_stats.hpp`, `t_gdn_stats.cpp`, the chain kernel in `gated_delta_net.hpp`, `amx_gdn.cpp`, `amx_gdn_iface.hpp`, `t_amx_gdn_numerics.cpp`. | No |

- main has no caller for these kernels. `gdn_execution.hpp` does not exist there, `model.hpp` and
  `TronCpp.hs` hold no GDN code, and the executor has no head groups and no working copy.
- So on main the split of section 1 does not work as written. A stack of kernels without their callers
  would be another split.

**The rounding question (issue #5433, draft PR #5571)**

- On main and at the head of PR #3221 the GDN code rounds values to bf16 at 22 places. The model's branch
  holds 25: it still has three that main dropped. Draft PR #5571 removes 14 of the 22. Issue #5433 measures
  first and then decides on eight of them.
- The issue says that six roundings of the normalization go "whatever the measurement says about the other
  eight". By the reading of [R19], one of the six is the rounding of K and Q.
- Part A needs K and Q as bf16 values. Its AMX kernel packs them by keeping the upper 16 bits of each value.
  Nothing checks this. With unrounded K and Q the kernel would cut each value toward zero by up to 0.78 %.
- An estimate from a float64 model, not from a run: the recurrent matrix of Part A would then differ from
  the chain kernel by about 3e-3 in relative L2 norm. Today's measured difference is 5e-8 to 4e-7.
- On the model's branch at `72e1191804` the rounding is present. So the builds, the tests and the runs of
  PR 3 in this file are valid for that base.
- By the code, Part 0 keeps the bytes of the token loop under the six removals. It calls the same
  normalization. No run has shown it.
- If all 14 go, Part 0 needs changes by hand in three places. Its own copy of the value rounding stays after
  a merge without a conflict marker (`gated_delta_net.hpp`, line 418 of `775bba7661`). `postprocess` in
  `gdn_rolling_executor.hpp` needs a merge by hand that drops three roundings. Two comments then describe a
  rounding that is gone [R19].
- The rounding task [R20] measures all this and compares the ways to adapt Part A.

**delphi-3b35**

- It was rebooted on 2026-11-23 at 08:55 UTC. The writing session read this by ssh at 19:20 UTC. The build
  trees are still there.
- The kernel is 6.8.0-138. The runs of 2026-11-20 to 2026-11-22 used the same version: their load snapshots
  record it.
- After the reboot `/dev/hugepages` held only `slice-0-of-8` to `slice-3-of-8`, the files of the other half.
  Not verified: that the first run on our half starts cleanly. Check that the first run ends with `RUN-OK`.
  If it fails at its start, stop and report.

### 0.3 What this changes in this file

- Two new questions for jhan: Q4 on the base, and Q5 on the time of PR 3 (section 2.3).
- Two new open items: one for the body of PR 3 and one for the body of PR 2 (section 8.4).
- The rounding task may run at the same time on the same machine (sections 3 and 7.1).
- After the reboot, a new timing is not comparable with section 7.7 without a control (section 11).

## 1. What to deliver

| Order | New branch | Base branch | Content | Source |
|---|---|---|---|---|
| PR 1 | `jhan-gdn-1-stats` | `rbjarnason/qwen35-native-4b-registry` | Counters for GDN, under the switch `TRON_ATTN_STATS` | commit `0d69ef3ce8` plus the switch change |
| PR 2 | `jhan-gdn-2-chain` | `jhan-gdn-1-stats` | Part 0 | the Part 0 share of commit `775bba7661` |
| PR 3 | `jhan-gdn-3-amx` | `jhan-gdn-2-chain` | Part A | the Part A share of commit `775bba7661` |
| PR 4 | `jhan-attn-h256` | `jhan-amx-kvmul16` (head branch of PR #5022 [R3]) | Part B | a port of commit `882e5322f1` |

The task is done when all of this holds:

1. PR #5572 carries a note that it is split, and it is closed. Its branch stays.
2. The branches of the PRs that section 2.3 allows are pushed. These PRs are open as drafts with the label
   `Skip benchmarks` and without the label `Run CI`. A PR that Q2 or Q5 holds back stays a local commit with
   its results.
3. Every PR has its result files under `/home/jhan/workspace/intel-AMX/exec/results/gdn-split-<YYYYMMDD>/`:
   builds with the option ON and OFF, unit tests, lint, token checks, and timed runs with the system load.
4. Every body follows the PR-description rules [R13]. Every body holds the stack table and the open item on
   `Run CI`.
5. Every PR has its changelog line.
6. jhan has a report with the links of the opened PRs, each PR held back with its reason, and the reminder
   of section 9.

## 2. Decisions

### 2.1 Decided by jhan on 2026-11-22. Do not reopen them.

| # | Decision | jhan's words |
|---|---|---|
| D1 | Four separate PRs. Not one PR with four commits. | "no, let's do separate PR" |
| D2 | PR 1, PR 2 and PR 3 form a GitHub stack in the order counters, Part 0, Part A. Each body describes the stack. | "we can make the first 3 PR a github PR sequence set, and also describe the sequence in PR body" |
| D3 | Part B is outside the stack. | "yes" |
| D4 | All four PRs are drafts. | "all PR are draft" |
| D5 | The GDN counters reuse `TRON_ATTN_STATS`. `TRON_GDN_STATS` is removed. | "yes, reuse" |
| D6 | PR #5572 gets a note that it will be split. Then it is closed. | "Add a note stating it will be split and close it" |
| D7 | The drafts open without `Run CI`. jhan reviews first. Then jhan asks for `Run CI`. Remind jhan of that. Each body carries it as an action item. | "when first open draft PR, do not run CI. After my review, run CI. Remind me to call it." |
| D8 | The Part 0 head gets timed runs of its own binary. | "I want a run at the Part 0 head" |
| D9 | E4B stays in the scope of Part B. The condition that selects the AMX kernels tests only the shape. No model-specific condition is added. | "`I still recommend keeping E4B in scope`: agree" |
| D10 | Deferred: the approval for AMX test cases that the GCP Nix workflow does not execute. | "let's defer this decison, let me know if this is blocking" |

### 2.2 Defaults set by this file. jhan has not decided them.

Follow them unless jhan says otherwise. Name each one in your report.

| # | Default | Reason, and what jhan heard before |
|---|---|---|
| U1 | The branch names of section 1. | jhan heard the names `jhan-gdn-stats`, `jhan-gdn-chain`, `jhan-gdn-amx`, `jhan-attn-h256`. Two of them are taken: `jhan-gdn-stats` is an old local branch, and `jhan-gdn-amx` is the head branch of PR #5572. |
| U2 | Part B is based on the branch of PR #5022. | jhan proposed "a new branch off 5022 branch" and left the choice to the session ("some branch of your pick"). If PR #5022 is merged when you start, tell jhan before you choose main. |
| U3 | One commit per PR at opening. | main merges by squash, and a body holds no change history. |
| U4 | One `changelog.d` line per PR, pushed after opening (section 8.6). | jhan was told this plan and did not object. The file name needs the PR number [R16]. |
| U5 | `config/test-benchmarks.json` stays unchanged. The missing refresh is an open item in each body. | jhan was told that 2 new test programs need rows, and that delphi-3b35 may write the Intel rows. Both statements are withdrawn. The split adds no new test name. The measuring tool must not run on delphi-3b35 (section 11). The AMD rows need an AMD CI runner, and reserving one needs jhan's OK. |
| U6 | The Qwen3.5 numbers of PR 4 come from a measurement-only build (section 6.5). | Qwen3.5 4B is not registered on the base of PR 4. jhan was told of this build. |
| U7 | The E4B evidence of PR 4 is the list of section 7.6. A model-level E4B test with a longer text is an open item, not part of PR 4. | jhan was told that the Part B work gains "a test that reaches the kernels". Such a test needs data files of 134.2 MB on every CI runner (section 7.6). An agent cannot place them. |
| U8 | No body holds numbers of Part A and Part B together. | That combination is the head of none of the four PRs. |
| U9 | The results page [R9] is not changed in this task. | It describes the commits of PR #5572. It will still name `TRON_GDN_STATS` and the closed PR. Ask jhan in the report whether it is to be updated. |
| U10 | Closing PR #5572 is step 1, before the new branches exist. | jhan was told this order and did not object. |
| U11 | A second comment on PR #5572 lists the new PRs that are opened. | jhan asked only for the note. The second comment lets a reader of the closed PR find the new PRs. |
| U12 | Without an answer to Q5, PR 3 is held back (section 2.3). | The view of the writing session of 2026-11-23. jhan has not decided it. |

### 2.3 Questions for jhan at the start

Ask them in one message before step 1, unless jhan's starting instruction already answers them.

| # | Question | What waits for the answer |
|---|---|---|
| Q1 | The go, if the starting instruction does not clearly give it (section 3). | everything |
| Q2 | The approval of D10. The repository rule says: "A test that does not execute in CI must not be committed, except in extremely rare cases explicitly approved by the user. Agents may not decide that an exception applies." [R16]. PR 3 and PR 4 hold AMX test cases that no required CI suite executes. The list is below. PR #5572 already holds all of them except one new section. | the push and the opening of PR 3 and PR 4 |
| Q3 | May the two measurement-only branches of section 6.5 be pushed without a PR? jhan heard only of a measurement-only build. | only that push. It also waits for the yes to Q2, because both branches hold AMX test cases. |
| Q4 | Which base do PR 1, PR 2 and PR 3 get: the model's branch, as this file is written; main, as the GDN owner advised (section 0.1); or the head of PR #3221 (table of section 0.2)? | everything, also step 1 |
| Q5 | Is PR 3 opened now, or held until the rounding task [R20] reports (section 0.2)? | the push and the opening of PR 3 |

The test cases of Q2:

- PR 3: the 5 cases of `t/t_amx_gdn_numerics.cpp`. The GCP Nix workflow compiles them out. Three more cases
  of `t/t_gated_delta_net.cpp` run there, but only on the chain kernel.
- PR 4: the kernel cases of `t/t_amx_numerics.cpp` for the 256 shape, the 256 sections of
  `t/t_amx_dispatch_dtype.cpp`, and the new section of section 6.4.
- All of them run in the CMake workflow. Their AMX instructions execute only when its test job runs on an
  Intel runner [R7].

The writing session told jhan on 2026-11-22 that the missing approval does not block a draft. jhan did not
answer that. This file reads the rule so: the approval comes before a commit with such a test leaves the
agent's machine. A local commit for the builds and the runs is not yet a commit to the repository. jhan has
not confirmed this reading. Say it in the message that asks Q2. Then:

- With a yes to Q2, open PR 4. Open PR 3 only when Q5 also says "now" (see "About Q5").
- Without an answer, finish and open PR 1 and PR 2. Keep the commits of PR 3 and PR 4 local, for the builds
  and the runs. Do not push them. Report.
- With a no, do steps 2 to 9 for all four PRs as planned. Keep the commits of PR 3 and PR 4 local. Open PR 1
  and PR 2 only. Report, and ask jhan how PR 3 and PR 4 go on.

When PR 3 is not opened, or PR 3 and PR 4 are not opened (Q2 or Q5):

- Step 11 pushes and opens only the other PRs. Steps 12 and 13 handle only those.
- In the stack table, the row of a PR that is not opened gets "not opened yet" in place of a number.
- The second comment on PR #5572 lists the opened PRs. It says which PRs are not opened yet.
- Say in the report that PR #5572 is closed while the parts of those PRs have no open PR.

About Q4:

- With "the model's branch", work as this file says.
- With "main" or "the head of PR #3221", stop. Sections 1, 5, 6 and 7 do not fit that base. Ask jhan to have
  this file revised first. Do not make up the new cut yourself.
- Without an answer, do not start. The first comment on PR #5572 names the base (section 8.1).
- What main offers: a PR there does not wait for PR #3696, and it follows the advice that jhan accepted in
  the chat. What it costs: only kernels and counter types fit there, without a caller and without a model
  run (section 0.2). An answer "main" changes what D1 and D2 can mean. Say so in the question.
- The writing session's view, for jhan: the model's branch keeps the measured code and the reviewed code the
  same, and no other base runs the model. Its cost is a port when that branch is rewritten. [R19] counted at
  least 12 conflict regions in 5 files for such a port onto the head of PR #3221.

About Q5:

- D2 stands: PR 3 belongs to the stack. Q5 asks only when it is opened.
- With "now", open PR 3 with the open item of section 8.4 that names issue #5433.
- With "hold", or without an answer: build, test and time PR 3 as this file says, and keep its commit local.
  Do not push it and do not open PR 3. A held PR 3 is opened later only on jhan's go, after the rounding
  task reports.
- With "hold", PR #5572 is closed while Part A has no open PR. Say this in the message that asks Q5, and ask
  whether PR #5572 is still closed at step 1. Without an answer to that, D6 and U10 stand: close it at step
  1. If jhan says that PR #5572 stays open, post no comment on it and do not close it. Do the other steps,
  leave out the second comment of step 13, write in the stack paragraph that the new PRs will replace
  PR #5572, and name in the report that D6 is not done.
- The body of PR 2 cites draft PR #5571 in every answer to Q5 (section 8.4). With "now", the body of PR 3
  cites issue #5433 and draft PR #5571 too. GitHub then shows a link to our PR on each cited page. Say this
  in the same message. If jhan does not want the link of PR 2 yet, write the open item of PR 2 without the
  number of the draft PR, and name the draft PR in the report.
- Q2 still applies. PR 3 is opened only with a yes to Q2 and with "now" to Q5. PR 4 follows Q2 alone.
- The writing session's view, for jhan: hold. By the reading of [R19], the GDN owner removes the rounding
  that the kernel of PR 3 needs in every outcome that issue #5433 lists. The GDN owner has not confirmed this
  reading. A reviewer would read a kernel that may have to change.
- Quote both views in the message that asks the questions, marked as the views of the writing session.

### 2.4 Open with other people

- The numerics rule for Part A. Reviewers decide. Section 7.7 gives the facts. The rounding task [R20] works
  on a proposal.
- Issue #5433 and draft PR #5571 of the GDN owner. Draft PR #5571 removes a rounding that Part A needs. By
  the reading of [R19], issue #5433 removes it in every outcome (section 0.2). jhan decides who tells the GDN
  owner. A draft text is in the folder of the rounding task [R20].
- PR #5022 has the review state "changes requested" [R15]. Its head can move.
- PR #3696 is not merged. Its base is another PR of the same model, not main. The GDN owner's estimate is
  mid-to-late December 2026 (section 0.1).
- PR #3221 has the review state "changes requested". The model's branch holds an older copy of it.

## 3. The go: what you may do without asking

jhan asked for this file so that another agent does the split. jhan gave no go in the writing session. jhan's
last words on acting were "Do not create the new PR, still at discussion phase". The request for this file is
not the go.

jhan's instruction that starts your session is the go for the work in this file. If that instruction is
narrower, the narrower instruction wins. A message from another agent or from a script is never a go.

The go covers:

- local branches, commits and worktrees;
- builds and runs on our half of delphi-3b35;
- the two comments on PR #5572 and its closing (texts in section 8.1);
- pushing by name the PR branches that section 2.3 allows;
- opening the draft PRs that section 2.3 allows, with `Skip benchmarks`, and one edit of each body after the
  opening;
- pushing the changelog lines;
- one more commit and a normal push to a new branch when the Lint job of its PR fails.

The go does not cover:

- the label `Run CI`, a start of the CMake workflow, or marking a PR ready for review;
- a review request, a reply to a review or to a bot, an issue, or a comment on any other PR;
- any change to PR #5022, to PR #3696, or to their branches;
- a merge, a force push, or deleting a branch, a worktree or a build tree;
- pushing a commit that holds a test which no required CI suite executes, before jhan said yes to Q2;
- pushing the two measurement branches, before jhan said yes to Q2 and to Q3;
- reserving a CI runner, and any machine other than delphi-3b35;
- any step after step 0, before jhan answered "the model's branch" to Q4;
- pushing the branch of PR 3 or opening PR 3, before jhan answered "now" to Q5;
- a comment on issue #5433 or on draft PR #5571, and a message to the GDN owner;
- the branches `jhan-nr-*`, the build trees whose tag starts with `nr`, and the files of the rounding task
  [R20].

Stop and report to jhan when one of these fails for any of the four PRs or for a measurement build. Open no
PR then, also not a PR whose own checks hold. This holds also for a PR that is held back: a failed check of
PR 3 stops the opening of the other PRs. jhan decides how to go on.

- a check I1 to I5 (section 6.6);
- a build, a unit test or a lint step (sections 7.2 and 7.3);
- a pair marked "must be identical" (section 7.4);
- an E4B generation test (section 7.6, item 3).

A pair marked "informational" does not stop the work. If a check fails after step 1, leave PR #5572 closed, do
not post the second comment, and report.

## 4. Where things stand

Verified on 2026-11-22 between 16:30 and 18:15 PST. On 2026-11-23 at 11:20 PST the three PR rows were
unchanged, and main had moved. Check the rows again before you start (section 5, step 0).

| Item | State | Id |
|---|---|---|
| PR #5572 [R1] | Open draft. Label `Skip benchmarks`. 0 comments, 0 reviews, 0 review requests | head `882e5322f1`, branch `jhan-gdn-amx`, base the model's branch |
| Its body | Equal to the local file [R12] on 2026-11-22 | 2,211 words with its "Words used here" section |
| PR #3696 [R2] | Open, not a draft. Base `rbjarnason/qwen35-normalize-conv-weight-storage` | head `72e1191804` |
| PR #5022 [R3] | Open, not a draft. Base main. Review state "changes requested" | head `ddf843ad97`, branch `jhan-amx-kvmul16` |
| main | | `f454423b09` (2026-11-23). It was `7eddde7895` on 2026-11-22. |
| Branch `jhan-gdn-amx` | 3 commits on `72e1191804`, pushed | `0d69ef3ce8` counters, `775bba7661` Part 0 and Part A, `882e5322f1` Part B |
| The 6 new branch names (sections 1 and 6.5) | Free, locally and on GitHub | |

Working trees of the shared repository `/home/jhan/workspace/tron`:

| Path | State | Note |
|---|---|---|
| `/home/jhan/workspace/ai-runs/tron-gdn-amx` | branch `jhan-gdn-amx` at `882e5322f1`, clean | the source of the split. Leave it as it is. |
| `/home/jhan/workspace/ai-runs/tron-glimmer-amx` | branch `jhan-amx-kvmul16` at `ddf843ad97` | PR #5022. Do not change it. |
| `/home/jhan/workspace/ai-runs/tron-qwen35-4b` | detached at `72e1191804` | read-only copy of the model's branch |
| `/home/jhan/workspace/ai-runs/tron-gdn-stats` | old local branch `jhan-gdn-stats` at `4e509c7f9f` | an early form of the counters. Not a source. |
| `/home/jhan/workspace/ai-runs/tron-gdn-partb` | old local branch `jhan-gdn-partb` at `8376a86d8a` | Part B alone on the model's branch, older text. Not a source. |
| `/home/jhan/workspace/ai-runs/tron-gdn-amx-review` | detached at `cbcb771f61` | an old review copy of the three commits. Not a source. |

Other local branches, all old: `jhan-gdn-amx-measured` (`aacdd287c0`, the commits that the old campaign
timed), and `jhan-gdn-amx-wip1`, `-wip2`, `-wip3`, `-wip5`, `-wip6` and `-wip7`. There is no `-wip4`.

Build trees on delphi-3b35, under `/var/tmp/jhan/`:

| Tree | Commit | Note |
|---|---|---|
| `b35-gdn-base` | `72e1191804` | the model's branch, built on 2026-11-20 by `exec/gdn-20261120/build-3b35.sh`. It holds only `runtron` and `t_gated_delta_net`. It serves the arms `orig` and `orig0`. |
| `b35-gdn-ctr`, `-pa`, `-pab` | `0d69ef3ce8`, `775bba7661`, `882e5322f1` | the heads of PR #5572 |
| `b35-gdn-e4b` | `882e5322f1` | Qwen3.5 4B and both E4B plugins |
| `b35-gdn-noamx` | `882e5322f1` | Debug build with the option OFF |
| `b35-gdn-p0`, `-partb`, `-stats` | `a72caf7e40`, `8376a86d8a`, `4e509c7f9f` | old commits. Not a source. `p0` holds an old work-in-progress commit, not Part 0. |
| `b35-pr5022-final` | checked out at `3bea58b788`, with the files of PR #5022 copied over it | Its tree equals the tree of `ddf843ad97`. Built without model plugins. |

`/var/tmp/jhan` had 3,145 GB free on 2026-11-22 at 02:00 UTC. Two more trees were built after that. No old
tree has to be deleted. On 2026-11-23 at 19:20 UTC, after the reboot of section 0.2, all trees of the table
were present and 2.9 TB were free.

## 5. Order of work

Do not start a step before the check of the step before it holds.

0. **Read and verify.** Read this file, the five fact files [R4] to [R8], the five files of [R13], and
   `AGENTS.md` and `t/AGENTS.md` of the repository [R16]. For section 0, read the fact files on the stack and
   on the rounding calls [R19]. Then run the commands below. If a head has moved, section 11 says what to do.

   ```
   git -C /home/jhan/workspace/tron fetch origin
   for r in rbjarnason/qwen35-native-4b-registry jhan-amx-kvmul16 jhan-gdn-amx main; do git -C /home/jhan/workspace/tron rev-parse --short=10 origin/$r; done
   git -C /home/jhan/workspace/tron worktree list | grep -E 'ai-runs/tron-(gdn|glimmer-amx |qwen35-4b)'
   for n in 5572 3696 5022; do gh pr view $n -R positron-ai/tron --json number,state,isDraft,headRefOid,baseRefName,reviewDecision; done
   gh pr view 5572 -R positron-ai/tron --json labels,comments,reviews,reviewRequests --jq '{labels:[.labels[].name],comments:(.comments|length),reviews:(.reviews|length),requests:(.reviewRequests|length)}'
   gh pr view 5572 -R positron-ai/tron --json body --jq .body | diff - /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/pr-body.md
   git -C /home/jhan/workspace/ai-runs/tron-gdn-amx status --short
   git -C /home/jhan/workspace/tron branch -a --list '*jhan-gdn-[123]-*' '*jhan-attn-h256*'
   ssh delphi-3b35 'ls -d /var/tmp/jhan/b35-gdn-* /var/tmp/jhan/b35-pr5022-final; df -h /var/tmp/jhan | tail -1'
   ```

   Check: the first three ids are `72e1191804`, `ddf843ad97` and `882e5322f1`. The body differs from the file
   by one empty line at most. If it differs more, jhan edited it: take the live body as the source. The
   status command and the branch command print nothing. The worktree lines show the six paths of section 4
   with the ids of that table.
1. **Ask the questions of section 2.3**, if they are still open. Wait for the go (Q1) and for the answer "the
   model's branch" to Q4. **Then note and close PR #5572** (section 8.1). Check: `gh pr view 5572` shows the state CLOSED, and the branch `jhan-gdn-amx` still exists
   on GitHub.
2. **Make the branch of PR 1** (section 6.1). Check: I1, I4, and the three lint commands of section 7.3 that
   need no build.
3. **Make the branches of PR 2 and PR 3** (sections 6.2 and 6.3). Check: I2, I3, I4, and the same three lint
   commands.
4. **Make the branch of PR 4** (section 6.4). Check: I5, and the same three lint commands.
5. **Make the two measurement branches** (section 6.5). Check: the diff from `72e1191804` to the first branch
   names the 12 files of PR #5022. The diff from the first branch to the second names the 7 files of PR 4.
6. **Build every tag of section 7.2 on delphi-3b35.** Check: every marker file `build-<tag>.done` holds `ok`.
7. **Run the unit tests and `make lint-notes`** (section 7.3). Check: no failed case, and every skipped case
   has a stated reason.
8. **Run the token checks** (section 7.4). Check: every pair that must be identical is identical.
9. **Run the timed campaign** for Qwen3.5 4B (section 7.5) and the E4B runs (section 7.6).
10. **Write the bodies** of the PRs that will be opened (section 8). For a PR that is held back, write no body
    and put its results into the report. Check: the self-check list of the PR-description skill.
11. **Push and open.** Push by name each PR branch that section 2.3 allows:
    `git -C /home/jhan/workspace/tron push origin <branch>:<branch>`. Push PR 1 first, then PR 2, then PR 3 if section 2.3 allows it:
    a PR needs its base branch on GitHub. Never push with `HEAD:<other name>`. Open the drafts that
    section 2.3 allows (section 8.5). With a yes to Q2 and to Q3, push the two measurement branches here too. Check: `git ls-remote origin <branch>` shows the local id. The ids of
    `rbjarnason/qwen35-native-4b-registry` and `jhan-amx-kvmul16` are unchanged.
12. **Push the changelog lines** (section 8.6). Check: about 10 minutes after each push,
    `gh pr checks <N> -R positron-ai/tron` shows the Lint job as passed and the build and test jobs as
    skipped. If Lint fails, fix it with one more commit and a normal push, and say so in the report.
13. **Edit each body once.** Fill in the PR numbers of the stack table and the final head. Fetch the live body
    first. Then post the second comment on PR #5572.
14. **Report to jhan** (section 9). Then update the memory note `gdn-amx-project.md` [R14] with the four PR
    numbers, the heads and the open items.

## 6. How to make each branch

Make new worktrees under `/home/jhan/workspace/ai-runs/`, one per branch, for example:

```
git -C /home/jhan/workspace/tron worktree add --no-track -b jhan-gdn-1-stats /home/jhan/workspace/ai-runs/tron-gdn-split-1 origin/rbjarnason/qwen35-native-4b-registry
```

- `--no-track` matters. Without it the new branch gets the model's branch as its upstream.
- Commit with `git commit --no-verify`. The commit hook (lefthook) is not installed on the agent's machine.
- For a cherry-pick that you change before the commit, use `git cherry-pick -n`, then
  `git commit --no-verify`. After you resolve conflicts, finish with `git commit --no-verify` too.
  `git cherry-pick --continue` starts the hook.
- End every commit message with the `Co-Authored-By:` line that your session's instructions give.

### 6.1 PR 1: counters with the shared switch

Source: commit `0d69ef3ce8` (8 files, 1,678 added lines). Cherry-pick it, then make the switch change. The
fact file [R5] lists every place with its line. The short form:

1. `h/tron/models/gdn_stats.hpp`: delete the function `gdn_stats::env_enabled()` and its comment. Add
   `using attn_stats::env_enabled;` to the list of using-lines. The header already includes
   `attn_stats.hpp`. Then `model.hpp` and the test need no edit for the call.
2. The same file: change three places so that each names `TRON_ATTN_STATS`. The places are the text of
   `Note [GDN path stats]`, the info log line and the JSON field `"switch"`. Delete the sentence that says
   the switch is separate. Drop `<cstdlib>` and `<cstring>` if nothing else uses them.
3. `t/t_gdn_stats.cpp`: the switch test case sets `TRON_ATTN_STATS`. Change the two expected `"switch"`
   strings (lines 442 and 568) to `TRON_ATTN_STATS=1`.
4. `README.stats.md`, lines 306 to 308: rewrite the bullet on `TRON_GDN_STATS`. It must say that GDN
   collection follows `TRON_ATTN_STATS`. Delete its sentence "It does not depend on `TRON_ATTN_STATS`."
5. The commit message: no `TRON_GDN_STATS` in the subject or in the text.

Facts to keep in mind:

- `attn_stats.hpp` is the same file on main, on the model's branch and on the branch of PR #5022. Do not
  change it.
- A model without GDN layers builds no GDN counter object. So it prints no `[gdn-stats]` line under the
  shared switch. This comes from reading the code [R5]. No run has shown it. State it in the body as read
  from the code.
- The counters commit already defines ten keys that no code writes yet. Five get their writer in PR 2 and five
  in PR 3 [R4]. The stated rule is "a path that a build does not have reads zero". Put this into the body of
  PR 1 as an open item with "Reviewers decide."
- The comment line in `gdn_stats.hpp` that names `gdn_recurrence_chain` comes with Part 0, not with PR 1.

### 6.2 and 6.3 PR 2 (Part 0) and PR 3 (Part A): cut commit `775bba7661`

The fact file [R4] classifies all 15 files and gives the line ranges. In short:

- 11 files belong to one part as a whole. The two comment hunks of `gdn_stats.hpp` are Part 0. The other 10
  are Part A: `amx_gdn_iface.hpp`, `amx_gdn.cpp`, `t_amx_gdn_numerics.cpp`, `model.hpp`,
  `src/tron/CMakeLists.txt`, `t/CMakeLists.txt`, `CMakeLists.txt`, `README.ci.md`, `amx_attn_iface.hpp` and
  `amx_attn.cpp`.
- 4 files need a cut inside the file: `gdn_rolling_executor.hpp`, `gdn_execution.hpp` (one line),
  `t/t_gated_delta_net.cpp` and `gated_delta_net.hpp` (only `normalized_query`, see below).

A method that keeps the final code safe:

1. Branch `jhan-gdn-3-amx` off `jhan-gdn-1-stats`. Cherry-pick `775bba7661` onto it. Call this commit X and
   write down its id. Its tree is the wanted final tree of PR 3.
2. Branch `jhan-gdn-2-chain` off `jhan-gdn-1-stats`. Take the Part 0 files from X. Bring the four mixed files
   into their Part 0 form by hand. Commit as Part 0.
3. In the worktree of `jhan-gdn-3-amx`: `git reset --soft jhan-gdn-2-chain`, then `git commit --no-verify`.
   The index still holds the tree of X, so the new commit has exactly that tree. Check:
   `git diff --quiet X HEAD`.

The Part 0 form of the mixed files:

- `advance()` loses the parameter `gdn_block_kernel`. Its form is `advance(tokens, first_position, rows,
  tally)`. Part A adds the parameter again and changes all four call sites.
- The executor loses the enum `gdn_block_kernel`, both AMX includes, `block_kernel_shape`, the block scratch
  member, `block_kernel_available()`, the tile-region helpers and `advance_window_with_block_kernel()`.
- The executor keeps `static_assert(gdn_window_tokens == gdn_stats::BLOCK_TOKENS_32)`. Part 0 counts
  `chain_full_block_tokens` on that grid.
- No text of Part 0 may refer to `Note [AMX GatedDeltaNet block kernel]`. That Note is defined in a Part A
  file, and `make lint-notes` fails on a reference without a definition.
- The changed checks of the test "GatedDeltaNet replay counts its work items ..." belong to Part 0. The old
  checks fail once `advance()` is in place.
- The test "advance gives full windows to the block kernel and counts them" is the only test of
  `chain_full_block_tokens` above zero. Give Part 0 a chain-only form of it. Part A turns it into the form
  with both kernels.
- Move `gdn_recurrence_window::normalized_query` to Part A: the member (line 366 of `gated_delta_net.hpp`),
  its store (lines 408-409) and the words on it in the Note (lines 339-340). Only Part A code reads it.
- Three names of `t/t_gated_delta_net.cpp` are read only by Part A code: `head_floats`, `no_value_head` and
  `chain_case_result::recurrent_state_bytes`. Move them to Part A. Otherwise Part 0 holds unused names.
- Each commit needs a clang-format pass. Removing the kernel argument changes the wrapping of the calls.
- Split the commit message of `775bba7661`: the chain kernel belongs to Part 0. The AMX block kernel and the
  GDN kernel switch belong to Part A.

Estimated sizes [R4]: Part 0 about 940 added lines (est.), Part A about 1,570 added lines (est.). The move of
`normalized_query` shifts a few lines from Part 0 to Part A.

A later change for PR 3, not for now. On a host without AMX a kernel test case cannot run. The branch of
PR #5022 reports such a case with `SKIP` and the exit code 4. `t_amx_gdn_numerics.cpp` uses `WARN` and
`return`, as the model's branch does today. When PR #5022 is in the base of PR 3, change it to the `SKIP`
form.

### 6.4 PR 4: port Part B onto the branch of PR #5022

Source: commit `882e5322f1` (7 files, 627 added lines). It holds the newest Part B text. Do not port from
`8376a86d8a`. Part B needs nothing from the GDN commits.

A cherry-pick onto `ddf843ad97` conflicts in 5 of the 7 files, in 29 places [R6]. PR #5022 varies the number
of query heads per KV head by a template parameter `group_heads` in one namespace. Part B adds a second
namespace for the 256-wide heads. The port puts the second namespace beside the template.

| File | Hand work |
|---|---|
| `h/tron/tensor/v_vnni.hpp` | none |
| `h/tron/kernels/amx_attn_iface.hpp` | 6 places, all comments. |
| `src/tron/kernels/amx_attn.cpp` | no text conflict. Check the duplicate named below. |
| `h/tron/models/self_attention.hpp` | 6 places. Keep Part B's `if constexpr (amx_serves_256x4<geometry>)` block for the 256 shape. In the `else` block keep the calls of PR #5022 with `<operation_kv_mul>`. Keep PR #5022's `row` view. Keep Part B's grow-only resize of `amx_qpack`. |
| `t/CMakeLists.txt` | 1 place. Keep PR #5022's registration of `t_amx_numerics`. Take Part B's 2-line comment over `t_amx_dispatch_dtype`. Drop the three lines that name `t_amx_gdn_numerics.cpp`. |
| `t/t_amx_dispatch_dtype.cpp` | 9 places. The head size becomes one more template parameter of `exercise_page`. |
| `t/t_amx_numerics.cpp` | 7 places. Two test layouts become one. Use `SKIP`, as PR #5022 does. |

Rules for the port:

- Leave PR #5022's code as it is. That covers:
  - `group_heads_ok`, `GROUP_HEADS_16`, and the condition of the 128 shape;
  - the three kernel templates and their instantiations;
  - `amx_attn_transpose.hpp`;
  - the `SKIP` handling, and the sections for 16 and 32 query heads;
  - `t/t_llama_unit.cpp`, `changelog.d/5022.changed.md` and `config/test-benchmarks.json`.
- Choose names and comments that are correct when a KV head has 16 query heads. Two places need it. On that
  branch the predicate `amx_serves_128x4` of `self_attention.hpp` is also true for 128 wide with 16 query
  heads. And Part B's comment on the resize of `amx_qpack` says "the 4 live columns". List the names you
  chose in the report.
- Part B's `store_query_rows` does the same work as PR #5022's `transpose_scores<GROUP_HEADS_4>`. Use the
  existing function if the result bytes are the same, and show that with `t_amx_numerics`. If not, keep both
  and say why in the body.
- The condition of the 256 shape stays head size 256 with kv_mul 4. Neither side serves 256 wide with 16
  query heads.
- Write a new commit message. The text of `882e5322f1` is wrong on this base in three points. The 128-wide
  path serves 4 or 16 query heads per KV head. Qwen3.5 4B is not registered here, and E4B is the model that
  takes the new kernels. The tests are as the port leaves them.
- New test, covered by Q2: a section of `t_amx_dispatch_dtype.cpp` with the shape of an E4B sliding-window
  layer (8 query heads, 2 KV heads, head size 256, window 512 tokens). It must show two things. A full page
  inside the window goes to the 256 kernels. A partial page, or a page outside the window, goes to the
  AVX-512 loop. First check whether an existing section already does this.

### 6.5 The measurement-only build for the Qwen3.5 numbers of PR 4

Qwen3.5 4B is not registered on the base of PR 4. So PR 4 cannot run it. Two local branches give the numbers:

| Branch | Content | Build tag |
|---|---|---|
| `jhan-attn-h256-on-qwen35-base` | the model's branch plus the net change of PR #5022 | `m0` |
| `jhan-attn-h256-on-qwen35` | the branch above plus the commit of PR 4 | `m1` |

- The net change of PR #5022 is the diff from `3bea58b788` to `ddf843ad97` (12 files). `3bea58b788` is the
  merge base of main and that head. No existing commit holds this net change, and the branch contains a merge
  commit. So make a one-commit form first, in the worktree of the first branch (made from `72e1191804`):

  ```
  N=$(git commit-tree 'ddf843ad97^{tree}' -p 3bea58b788 -m 'net change of PR 5022')
  git cherry-pick -n $N && git commit --no-verify -F <message file>
  ```

  Without `-F`, `git commit` takes the text of `$N`.

  This applies onto `72e1191804` without conflict [R6]. Do not cherry-pick the range, and do not merge the
  branch of PR #5022: a merge also brings 38 commits of main and 9 conflicting files.
- For the second branch: `git cherry-pick -n <head of PR 4>` on top, then commit. Three files differ between
  the two bases (`self_attention.hpp` in one comment hunk, `t/CMakeLists.txt`, `t/t_llama_unit.cpp`) [R6].
  Resolve a conflict only when the fix is mechanical. Otherwise stop and report.
- Both commit messages start with "Measurement only" and end with the `Co-Authored-By:` line. These branches
  never get a PR.
- The body of PR 4 says plainly that its Qwen3.5 numbers come from this build, with both commit ids. If the
  branches are not pushed (Q3), the body says that the two commits are not on GitHub.

### 6.6 Checks on the branches

| # | Check |
|---|---|
| I1 | The diff from `0d69ef3ce8` to the head of PR 1 shows the switch change of section 6.1 and nothing else. |
| I2 | The diff from `775bba7661` to the head of PR 3 shows the same switch change. Any other difference fails the check, unless you made it on purpose. List each such difference, with its reason, in the report. |
| I3 | The head of PR 2 holds no Part A text, and PR 2 changes only the five Part 0 files. |
| I4 | The heads of PR 1, PR 2 and PR 3 do not name `TRON_GDN_STATS`, in no file and in no commit message. |
| I5 | PR 4 changes exactly the 7 files of Part B. |

The commands, each run in the worktree of the branch it checks:

```
# I1 and I2
git diff 0d69ef3ce8 jhan-gdn-1-stats
git diff 775bba7661 jhan-gdn-3-amx
# I3: the grep must print nothing; the diff must name only gated_delta_net.hpp, gdn_stats.hpp,
#     gdn_execution.hpp, gdn_rolling_executor.hpp and t/t_gated_delta_net.cpp
git grep -n -E 'amx_gdn_(iface|k128v128)|amx_gdn\.cpp|block_kernel|TRON_AMX_GDN_DISABLE' jhan-gdn-2-chain -- h src t CMakeLists.txt README.ci.md
git diff --stat jhan-gdn-1-stats jhan-gdn-2-chain
# I3, second grep: must print nothing (it prints nothing at 0d69ef3ce8, and 42 lines at 775bba7661)
git grep -n -i -E 'amx|tile|finally|normalized_query\[' jhan-gdn-2-chain -- h/tron/models/gdn_rolling_executor.hpp h/tron/models/gdn_execution.hpp h/tron/kernels/gated_delta_net.hpp
# I4: the grep must print nothing; the count must be 0
git grep -n TRON_GDN_STATS <head>
git log --format=%B origin/rbjarnason/qwen35-native-4b-registry..<head> | grep -c TRON_GDN_STATS
# I5
git diff --stat ddf843ad97 jhan-attn-h256
```

The pattern of I3 leaves out the field name `amx_gdn_enabled` on purpose. PR 1 holds it on 5 lines, so it
stays in PR 2.

## 7. Checks and measurements on delphi-3b35

### 7.1 Rules of the machine

- Drive it with `ssh delphi-3b35`. No sudo. Use only our half. Keep `SYSTEM_CONFIG="--instance 1,2"`.
- Builds, unit tests and lint run under `nice -n10 taskset -c 96-143`, or on a part of that range.
- Before the first test run, run `bin/slice route` in a build tree, as `AGENTS.md` asks [R16]. On 2026-11-20
  it answered `local-legacy`. That means normal local commands. If the answer differs, stop and report.
- Take a load snapshot before every timed run and every token run [R10]. `run-one.sh` does this. It refuses a
  run when one of our cards is open or when our CPUs are more than 5 % busy.
- Report the load in every result table: socket 0 busy, socket 1 busy, our CPUs busy. On 2026-11-22 socket 0
  was about 42 % busy from other users, and our CPUs were 0.0 to 0.1 % busy.
- During a timed run or a token run, nothing else of ours runs there: no build, no unit test, no lint, no
  score dump. `run-one.sh` checks the load only before a run starts.
- Never touch a process or a file of another user.
- The rounding task [R20] may use jhan's account on this machine at the same time. Its build tags start with
  `nr`. Before every campaign start and every token run, check on delphi-3b35:
  `ssh delphi-3b35 "pgrep -u jhan -fa '[r]untron|[n]inja|[c]make|[b]uild\.sh|[c]ampaign|[r]un-one\.sh|[t]oken-check|[l]ogit-margin|[u]nit-tests|gen/[t]_|[a]mx_gdn_bench'"`.
  The brackets keep the calling shell out of the result. Run the check as a command of its own. A campaign
  has no runtron process between two runs, so the names of the driver scripts are part of the pattern. No
  output means that nothing of these runs. Do not start while a build, a run, a test or a bench of that
  account is active. Do not build while a timed run of the
  other task is active.

### 7.2 Builds

Copy the scripts of the old run folder [R10] into a new folder
`/home/jhan/workspace/intel-AMX/exec/gdn-split-<YYYYMMDD>/`. Results go to
`/home/jhan/workspace/intel-AMX/exec/results/gdn-split-<YYYYMMDD>/`. A new name is needed: four scripts skip
a run whose output file exists (`run-one.sh`, `token-check.sh`, `logit-margin.sh`, `e4b-check.sh`). The fact
file [R8] lists every value that is fixed in the script texts.

| Tag | Commit | Model list | Used for |
|---|---|---|---|
| `base` (exists) | `72e1191804` | Qwen3.5 4B | the model's branch |
| `s1`, `s2`, `s3` | the commits of PR 1, PR 2, PR 3 | Qwen3.5 4B (`exec/gdn-20261120/models.gdn.yaml`) | the stack |
| `b0` | `ddf843ad97` | E4B only (a new file) | today's code under PR 4 |
| `b1` | the commit of PR 4 | E4B only | PR 4 |
| `m0`, `m1` | the two branches of section 6.5 | Qwen3.5 4B | Qwen3.5 numbers of PR 4 |
| `s1off`, `s2off`, `s3off`, `b1off` | the four PR commits | as above | builds with the option OFF |

- `build.sh` takes `TAG`, `SHA`, `REG` (the model list), `TARGETS` and `CONF_FLAGS`. A tag holds lowercase
  letters and digits. A commit needs no push: the build trees are worktrees of the shared repository.
- The E4B-only list is new. Take lines 4 and 5 (`schema_version: 1`, `models:`) and lines 20 to 49 of
  `models.e4b.yaml` [R10]. The Qwen3.5 entry of that file does not exist on main.
- For a build with the option OFF, pass `CONF_FLAGS='-DCMAKE_BUILD_TYPE=Debug'`. The default of `CONF_FLAGS`
  is `-DTRON_AMX_DISPATCH=ON`, and any other value replaces it. `pr-prep.sh` does the same [R10].
- An existing tree keeps its old configure options. Use a new tag for a new configuration.
- Targets of `s1`, `s2`, `s3` and their OFF builds: `runtron t_gated_delta_net t_amx_numerics
  t_amx_dispatch_dtype t_llama_unit t_tronstats_convention`.
- Targets of `b0` and `b1`: `runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit` and the four tests
  `t_generate_ingest_1_gemma_4_e4b_{fpga,tp2_fpga,tp4_fpga,permuted_fpga}`.
- Targets of `b1off`, `m0` and `m1`: `runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit`.
- `runtron` is in every OFF build so that the model code compiles with the option OFF. The GCP Nix workflow
  compiles it that way.
- No build of a commit based on main was made with `build.sh` yet. Its text should work when `REG` names
  models of that commit [R8]. If it fails, read the build log, fix the copy of `build.sh`, and report the
  change. If the E4B export fails at `ddf843ad97`, stop and report: PR 4 then has no E4B evidence.
- Measured build times: 548 to 580 s for a new Qwen3.5 tree, and 749 s for the new tree with Qwen3.5 and both
  E4B plugins. A rebuild in an existing tree took 294 to 311 s. Every planned tag is a new tree. All builds,
  one after the other, take about 80 to 105 minutes (est.).
- Each build and each run belongs to the code commit of its PR. The changelog commit of step 12 comes on top
  and adds one text file. No run is repeated for it.

### 7.3 Unit tests and lint

Run the test programs that each tag holds with a copy of `unit-tests.sh` [R10]. Pass `TAGS`, `TESTS` and
`OUT` per call. Put `nice -n10` before `taskset` in the copy.

| Tag | Extra runs with a switch |
|---|---|
| `s3` | `t_gated_delta_net` and `t_amx_numerics`, each with `TRON_AMX_DISABLE=1` and with `TRON_AMX_GDN_DISABLE=1` |
| `b1` | `t_amx_numerics`, `t_amx_dispatch_dtype` and `t_llama_unit` with `TRON_AMX_DISABLE=1` |

- `t_gdn_stats.cpp` is part of the program `t_gated_delta_net`. `t_amx_gdn_numerics.cpp` is part of the
  program `t_amx_numerics`. So the split adds no new test name [R7].
- `unit-tests.sh` accepts only the output line `All tests passed`. On the tags `b0`, `b1`, `b1off`, `m0` and
  `m1` a case that cannot run uses `SKIP`. The program then prints `test cases: N | M passed | K skipped`
  with exit code 0, and `unit-tests.sh` writes `FAILED rc=0`. Change the rule in the copy: a run passes when
  the exit code is 0 and no case failed. Print the number of skipped cases.
- Count skipped cases. A skip is never a pass. Every skip needs its reason in the table.
- For comparison, at the heads of PR #5572: 19 of 19 runs pass. The build with the option OFF gave 109,130
  assertions in 50 cases for `t_gated_delta_net`.

Lint, at every PR commit, as the CI lint job does [R7]. The first three need no build. Run them at steps 2
to 4.

- `git diff --check <base> <head>`.
- No `#include <cassert>` in `h`, `src` or `t`.
- clang-format 19.1.7: `uvx --from clang-format==19.1.7 clang-format --dry-run -Werror <changed files>`.
- `make lint-notes` in the trees `s1`, `s2`, `s3` and `b1`, on our CPUs:
  `( cd /var/tmp/jhan/b35-gdn-<tag> && PATH=$HOME/.ghcup/bin:$HOME/.cabal/bin:$PATH nice -n10 taskset -c 96-143 timeout 900 make lint-notes )`.

### 7.4 Token checks

Settings: 1 user, temperature 0, `--pay-for-determinism`, `--output-token-file`. `token-check.sh` does this
for Qwen3.5 4B [R10].

Qwen3.5 4B (`ingested-qwen-3.5-4b-tp4`), prompt 1,024 and prompt 4,096, 256 generated tokens:

| Pair | Rule |
|---|---|
| a repeat of the same arm | must be identical |
| `base`, `s1`, `s2`, `m0` | must be identical. Part 0 gives the bytes of the token loop. |
| `s3` with the GDN kernel switch, against `s2` | must be identical |
| `s3` with the kill switch, against `s2` | must be identical. Its `[gdn-stats]` lines must show no token on the amx path. |
| `m1` with the kill switch, against `m0` | must be identical |
| `s3` against `s2` | informational. At the old commits: first difference at generated token 185 of prompt 1,024, and no difference at prompt 4,096. |
| `m1` against `m0` | informational. At the old commits: first difference at generated token 1 of prompt 1,024, and no difference at prompt 4,096. |

E4B (tp4 and permuted), prompt 1,024, 128 generated tokens:

| Pair | Rule |
|---|---|
| a repeat of `b1` | must be identical |
| `b1` with the kill switch, against `b0` | must be identical |
| `b1` against `b0` | informational. At the old commit: tp4 differs from generated token 63 on, and permuted is identical. |

- `e4b-check.sh` [R10] takes one tag per call and compares only inside that tag. Its file names hold no tag,
  and its results folder name is fixed in its text. In the copy, give the arm table a tag field, as
  `token-check.sh` has. Then compare across the tags `b0` and `b1`.
- For every informational difference, measure the scores at the first different token (section 7.6,
  item 2). Say in the body whether the two best scores were equal, or how many bf16 steps apart they were.

### 7.5 Timed campaign for Qwen3.5 4B

Cells: 1 user and 8 users, each with prompt 1,024, prompt 4,096 and prompt 8,192. Every run generates 256
tokens. Model `ingested-qwen-3.5-4b-tp4`. 3 repetitions. The arm order rotates by one position per
repetition, as `campaign.sh` does [R10].

Main campaign start, 7 arms:

| Arm | Tag | Switches | Shows |
|---|---|---|---|
| `st` | `s1` | `TRON_ATTN_STATS=1` | PR 1: today's token loop with the counters on. The base of PR 2. |
| `ch` | `s2` | `TRON_ATTN_STATS=1` | PR 2: Part 0 |
| `bk` | `s3` | `TRON_ATTN_STATS=1` | PR 3: Part A |
| `bkoff` | `s3` | `TRON_ATTN_STATS=1 TRON_AMX_GDN_DISABLE=1` | PR 3 with the GDN kernel switch. Expected: the speed of `ch`. |
| `m0` | `m0` | `TRON_ATTN_STATS=1` | the base of PR 4 on the model's branch |
| `m1` | `m1` | `TRON_ATTN_STATS=1` | PR 4: Part B |
| `m1off` | `m1` | `TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1` | PR 4 with the kill switch. Expected: the speed of `m0`. |

Control campaign start for the cost of the counters in PR 1, 4 arms. It runs on the 3 cells of the old
control: 1 user at prompt 1,024, 8 users at prompt 1,024, and 1 user at prompt 4,096.

| Arm | Tag | Switches | Shows |
|---|---|---|---|
| `orig` | `base` | `TRON_ATTN_STATS=1` | the model's branch, attention counters on |
| `st` | `s1` | `TRON_ATTN_STATS=1` | PR 1, both counter sets on |
| `orig0` | `base` | none | the model's branch, counters off |
| `st0` | `s1` | none | PR 1, counters off |

- `st` against `orig` is the cost of the GDN counters when the switch is on. `st0` against `orig0` is the
  cost of PR 1 when the switch is off.
- The arm `st` is in both campaign starts, on the same three cells. A run is named
  `<cell>__<arm>__rep<N>`, and `run-one.sh` skips a run whose log exists. So give the control start its own
  repetition numbers: `FIRST_REP=21 REPS=23`, as the old control did. Check after both starts:
  `rt-results.txt` holds 126 and 36 blocks with `RUN-OK`.
- Form every ratio from runs of one campaign start. Do not divide a value of one start by a value of another.
- The new arm names differ from the old ones on purpose. The old arms `base`, `p0`, `a`, `a0`, `b`, `ab` and
  the old tags `ctr`, `pa`, `pab`, `p0` belong to the old campaign. The old arm `base` was the counters
  build. It is not the tag `base`.
- `run-one.sh` sets `TRON_ATTN_STATS=1` only when its input `ARMENV` is not set at all. `campaign.sh` always
  sets it from the third field of the arm row. So an empty third field gives a run without counters. Every
  arm with counters must name `TRON_ATTN_STATS=1` in its row. Check the field `armenv=[...]` of each run in
  `rt-results.txt`.
- The old arm `nost` (attention counters on, GDN counters off) cannot exist any more.
- The main start is 126 runs, about 75 minutes (est., from 21.4 minutes per 36 runs in the old campaign). The
  control start is 36 runs, about 17 minutes (est.).
- Read TTFT and the decode speed from the runtron log lines.
- Use the decision rule of the body of PR #5572 in every body [R12]. It gives the mean of the 3 runs. A
  change counts only when it is larger than twice the larger standard deviation of the two arms. Mark every
  other change "inside". Print the standard deviation beside every mean.

### 7.6 E4B evidence for PR 4

E4B is the only model on the base of PR 4 that takes the new kernels. Results exist for the old commit
`882e5322f1` [R11]. Both plugins compile. In 35 of 42 layers the AMX kernels read the K tokens. The four
generation tests pass. The layers 5, 11, 17, 23, 29, 35 and 41 stay on AVX-512. They are the 7 full-attention
layers, and the public configuration of the model gives them 512-wide heads.

1. Token check and kernel per layer, with `b0` and `b1` (section 7.4). Read the layers from the
   `[attn-stats]` lines.
2. Scores at the first different token. Adapt `logit-margin.sh` and `logit_summary.py`. Their arm table and
   file names are fixed to Qwen3.5. The fact file [R8] lists the 8 points to change. Not known yet: whether
   the E4B plugin writes the log lines "Top-k Logits", and which line holds generated token 63.
   For the Qwen3.5 pairs of section 7.4, change the arm table too. Its rows name the old tags `ctr`, `pa` and
   `pab`, and those trees still hold the commits of PR #5572. New rows use the tags `s2`, `s3`, `m0` and
   `m1`. Check the field `tip=` of each run in `rt-results.txt` against the commit of its PR.
3. The four tests `t_generate_ingest_1_gemma_4_e4b_*`, with AMX on and with the kill switch
   (`e4b-tests.sh`, one output folder per tag). They must pass. They do not reach the AMX kernels: their text
   has 24 tokens, so no page is full. Say that in the body. They show only that nothing else breaks.
4. A few timed cells: tp4, 1 user and 8 users, prompt 1,024 and prompt 4,096, 256 generated tokens, 3
   repetitions, arms `b0`, `b1`, and `b1` with the kill switch. If a cell does not start, drop it and say so.
   The old single runs allow no claim.
5. The new section of `t_amx_dispatch_dtype.cpp` (section 6.4).

Open item for the body, with "Author decides.": a model-level E4B test that reaches the kernels. It needs a
text of more than 64 tokens that the test feeds token by token. Then it needs a token file and a file of
stored scores in `/scratch/test/data` on every CI runner. One token position takes 1,048,584 bytes, so 128
positions take 134.2 MB [R7]. An agent cannot place these files.

### 7.7 Values of the old commits, for comparison

No body may cite these values: a body cites its own commit. A new result far from them needs a cause before it
goes into a body.

Source: the second campaign start of 2026-11-22, means of 3 runs [R10], [R12]. Its commits were `d5093e07c2`,
`8351e4ad52` and `aacdd287c0` of the branch `jhan-gdn-amx-measured`. They differ from the commits of PR #5572
in comments, tests and README files only. "Counters build" is the old arm `base`. It matches the new arm `st`.
The new pair `m1` against `m0` has the token loop in both arms, not the chain kernel. So expect its TTFT
fall near the second range of the Part B row.

| Quantity | Against | Old value |
|---|---|---|
| TTFT of the counters build, 1 user, prompt 1,024 / 4,096 / 8,192 | | 0.385 s / 1.90 s / 4.71 s |
| TTFT of the counters build, 8 users, same prompts | | 2.90 s / 14.3 s / 35.7 s |
| Decode speed of the counters build, 1 user | | 273 / 254 / 233 tokens per second |
| Decode speed of the counters build, 8 users | | 121 / 77.9 / 56.4 tokens per second per user |
| TTFT fall of Part 0 | the counters build | 9.0 to 14.1 % over the 6 cells |
| TTFT fall of Part A | the counters build (Part 0 and Part A together) | 15.3 to 24.7 % |
| TTFT fall of Part A | Part 0 (the step that the body of PR 3 shows) | 7.0 to 12.4 % |
| TTFT fall of Part B | the same binary with the kill switch (old arms `b` and `p0`, both on the chain kernel) | 0.7 to 25.3 %. In percent of the TTFT of the counters build: 0.6 to 23.0 %. |
| Decode speed with Part 0, with Part A | the counters build | -0.7 to +0.2 %, -0.3 to +0.5 % |
| Decode speed with Part B | the same binary with the kill switch | +18.0 % and +22.0 % at 8 users with prompt 4,096 and prompt 8,192. Between -1.0 % and +2.9 % in the other cells. |
| GDN time per token of one key head in prefill, 1 user, prompt 1,024 | | 6.08 us with the token loop, 4.01 us with Part 0, 2.56 us with Part A (mean over the GDN threads, medians of 3 runs) |
| Counters build against the model's branch, both with the counters on (control start, medians of 3 runs) | | decode -0.6 to +0.4 %, TTFT -0.1 to +0.2 %, inside the band in all 3 cells |

Findings that belong in the bodies as open items. Their numbers are values of the old commits too. A body
gives each finding with the value measured at its own commit. The scores come from the runs of section 7.4.
The wait per prefill pass comes from `join_wait_cycles` in the `[attn-stats]` lines of the arms `m0` and
`m1`, as `collect.py` computes it. If a value is not measured again, state the finding without a number and
write "Insufficient data".

- Part A: the scores drift during decode from at most 1 bf16 step to up to 10 steps. At generated token 185
  the best score leads by 8 bf16 steps, and Part A still picks another token. This is not a tie. The numerics
  rule is open. Reviewers decide.
- Part A: the AMX kernel reads K and Q as bf16 values. Draft PR #5571 removes the rounding that makes them
  so. By the reading of [R19], issue #5433 removes it in every outcome (section 0.2). The body of PR 3 states
  this need and cites issue #5433 and draft PR #5571.
- Part B, Qwen3.5 4B: at generated token 1 of prompt 1,024 the two best scores are equal (both 16.375, an
  exact tie in bf16). Part B then picks the other of the two tokens.
- Part B, 8 users, prompt 1,024: the time that an attention thread waits for the other attention threads
  rises from 3.3 ms to 10.9 ms per prefill pass. The cause is not measured.
- Part A holds a fix for blocks that run slowly when their values are subnormal (too small for the normal
  float format). It sets two CPU float modes around the kernel: FTZ (flush to zero) and DAZ (denormals are
  zero). Keep it.

## 8. The PR texts

### 8.1 The two comments on PR #5572

First comment, then `gh pr close 5572 -R positron-ai/tron` (never with `--delete-branch`):

> This PR is being split into four smaller draft PRs, so that each change can be reviewed alone:
>
> 1. GDN path statistics (the counters).
> 2. The GatedDeltaNet chain kernel.
> 3. The AMX block kernel for GatedDeltaNet.
> 4. The AMX attention kernels for 256-wide heads.
>
> PRs 1 to 3 form a stack on the branch of #3696. PR 4 is based on the branch of #5022. The links follow in
> a second comment. The branch of this PR stays as it is.

Second comment, at step 13: one line per new PR with its number and its title.

The first comment names the base of PR 1 to PR 3. It is written for the answer "the model's branch" to Q4.
If PR 3 or PR 4 is held back when you post it, add one sentence: "PR 3 is opened later." or "PRs 3 and 4 are
opened later."

### 8.2 The bodies

- Write each body with the PR-description skill and check it with the plain-english skill [R13]. If your tool
  has no skills, read the two skill files.
- Start from the live body of PR #5572 [R12]. Give each of its facts and open items to the PR it belongs to.
- Every number comes from a run at the code commit of that PR, with the commit id and the date. Say that the
  head adds only the changelog line on top of that commit.
- Present tense. No change history. No names of people. Under 2,000 words without the "Words used here"
  section.
- PR 4: name E4B and Qwen3.5 4B as the models that take the new kernels. Say which numbers come from which
  build.
- Each PR of the stack shows only its own step: PR 2 against PR 1, and PR 3 against PR 2.

### 8.3 The stack table

Every body that is written holds the same section "The stack". One paragraph says that the four PRs replace
PR #5572. Then
this table, with the real numbers:

| Order | PR | Branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #N1 | `jhan-gdn-1-stats` on the branch of #3696 | counters for GDN | draft until #3696 and the PRs under it are on main |
| 2 | #N2 | `jhan-gdn-2-chain` on `jhan-gdn-1-stats` | the GDN chain kernel | draft until #N1 merges |
| 3 | #N3 | `jhan-gdn-3-amx` on `jhan-gdn-2-chain` | the AMX block kernel for GDN | draft until #N2 merges |
| beside | #N4 | `jhan-attn-h256` on the branch of #5022 | AMX attention kernels for 256-wide heads | draft until #5022 merges |

The numbers exist only after the opening. For a PR that is not opened, write "not opened yet" in the columns
PR and State. So open the PRs with a placeholder, then edit each body once
(step 13). Fetch the live body again before every `gh pr edit`.

### 8.4 Open items that every body or some bodies need

| Open item | Bodies | Decider |
|---|---|---|
| CI has not run. The draft opens without `Run CI`, so the GCP Nix workflow skips its build and test jobs. The author adds the label after the author's own review. | all four | Author decides. |
| The times in `config/test-benchmarks.json` are not measured again for the changed test programs. | all four | Author decides. |
| The GCP Nix workflow does not execute the AMX test cases. They run in the CMake workflow, and only when its test job runs on an Intel runner. | PR 3, PR 4 | Author decides. |
| Ten counter keys have no writer until PR 2 and PR 3. | PR 1 | Reviewers decide. |
| The numerics rule for the AMX block kernel. | PR 3 | Reviewers decide. |
| The AMX block kernel needs normalized keys and queries that are bf16 values. Draft PR #5571 removes the rounding that makes them so. Issue #5433 says that six normalization roundings are removed whatever its measurement shows. By our reading this rounding is one of the six. The kernel or its caller must change before or with that removal. | PR 3 | Reviewers decide. Cite #5433 and #5571. |
| The chain kernel holds its own copy of the rounding of the value. Draft PR #5571 removes that rounding from the token loop. If #5571 merges with all 14 removals, this line must go too. A merge shows no conflict there. | PR 2 | Author decides. Cite #5571, unless jhan said no to that link (section 2.3). |
| A model-level E4B test that reaches the 256 kernels. | PR 4 | Author decides. |
| The longer wait between attention threads with 8 users. | PR 4 | pending measurement |

The body of PR #5572 lists more open items, for example a missing unit test that sets the GDN kernel switch.
Keep each one that a reviewer or the author must act on before merging.

### 8.5 Titles, labels, commands

Suggested titles:

1. "Add GatedDeltaNet path statistics under TRON_ATTN_STATS"
2. "Advance GatedDeltaNet prompt chains with a chain kernel"
3. "Advance full GatedDeltaNet windows with an AMX block kernel"
4. "AMX attention kernels for 256-wide heads with 4 query heads per KV head"

```
gh pr create -R positron-ai/tron --draft --base <base branch> --head <new branch> \
  --title "<title>" --body-file <body file> --label "Skip benchmarks"
```

End every body with the line that your session's instructions give for PR descriptions.

### 8.6 Changelog lines

- One file per PR: `changelog.d/<PR number>.<section>.md`, with one line `- scope: Entry. (#N)` of at most 80
  characters, in the imperative mood [R16]. Example on the branch of PR #5022:
  `- runtime: Speed up Muse Glimmer 30B attention with AMX on Intel hosts. (#5022)`.
- The stack rule of the repository [R16]: in a stack only the PR that makes the change usable carries the
  line, unless a PR is notable by itself. Default of this file: PR 1 (new counters), PR 2 (shorter TTFT
  without AMX) and PR 3 (shorter TTFT with AMX) are each notable by themselves. Name this in the report, so
  that jhan can reduce it.
- Sections: `added` for PR 1 (scope `stats`), `changed` for PR 2, PR 3 and PR 4 (scope `runtime`).
- The folder `changelog.d` does not exist on the model's branch. That branch is older than the rule. The
  first file of PR 1 creates the folder there.
- Each changelog commit is on its own branch only. Do not rebase PR 2 and PR 3 onto the changelog commit
  of their base. GitHub then shows them as out of date with the base. That is accepted.
- Count the characters of every line before the push.

## 9. After the PRs are open

Report to jhan:

- the links of the opened PRs, the answers to Q1 to Q5, each PR held back with its reason, the code commits
  and heads, and the closed PR #5572;
- the test tables, and the timing results as charts with their tables, each with the load;
- every default of section 2.2 that you used or changed, and the names you chose in the port;
- every open item;
- the review findings, see below.

A push can bring an automated review within about 16 minutes [R14]. About 20 minutes after the last push,
list the reviews of the opened PRs (read-only). Test each finding before you believe it. Report it. Reply to
none.

Remind jhan twice of `Run CI`: in this report, and again when jhan says that the review is done. Add the
label only when jhan then asks for it.

Tell jhan also:

- The AMX cases run only in the CMake workflow. A start by hand is
  `gh workflow run cmake-single-platform.yml -R positron-ai/tron --ref <branch> -F skip_benchmarks=true`.
  It needs jhan's go.
- Two sentences of the old chat that are corrected in section 11.

What can follow, each only on jhan's go:

- When PR #3696 and the PRs under it have reached main, PR 1 is rebased onto main. main merges by squash. So
  the branches of PR 2 and PR 3 need a rebase after every merge below them. A rebase needs a force push.
- Before that, the model's branch must be rewritten (our inference, section 0.2), because PR #3696 and the 5
  PRs under it still sit on the main of 2026-11-16. PR 1 to PR 3 then need a port by hand, not a plain
  rebase. Expect at least the size that [R19] counted for the head of PR #3221: 12 conflict regions in 5
  files. That count is a lower bound.
- A held PR 3 is opened only on jhan's go, after the rounding task reports.
- When PR #5022 merges, PR 4 is rebased onto main. If the head of PR #5022 changes before that, PR 4 is
  ported onto the new head. Both need a force push.

## 10. jhan's rules that stay in force

- Machines: delphi-3b35 only, our half only, no sudo. Not delphi-3bda and no other lab machine unless jhan
  names it. Measure the load before every performance test and report it.
- The agent's own machine allows 8 CPUs per user. Shell commands of the agent are pinned to 6 CPUs. Size
  every worker pool from `nproc`. Do not build tron there.
- Never run `git worktree prune` on `/home/jhan/workspace/tron`. Its worktree list shows the trees on
  delphi-3b35 as "prunable", because that disk is absent on the agent's machine.
- New files and folders go under `/home/jhan/workspace/ai-runs/` or into the project folder. Never directly
  into `/home/jhan/workspace`.
- GitHub text: no names of people and no @-mentions. Roles and links only. Write "PR", never "pull request".
- Source code: no issue number and no PR number in a comment. Follow the C++ coding guide [R13] and the
  conventions of the files you edit.
- Fetch the live body before every `gh pr edit`. Never overwrite an edit that jhan made on GitHub.
- Add `Skip benchmarks` to every PR. Add `Run CI` only on jhan's direction [R16].
- Treat jhan's name, email address and project details as private. Do not send them to outside services.
- Writing: plain English, a "Short version" first, one claim per sentence, terms defined at first use,
  numbers with units, no idioms, short sentences, bullets. Write "prompt 1,024", never "ctx 1024". Do not use
  the words convoy, refund, swept or "in disguise".
- Results for jhan: a chart whose form fits the data, with the exact numbers in a table beside it. Mark
  estimates "est.". Files for jhan are HTML with a light background unless jhan asks for another format.
- Say "Insufficient data" and name the missing measurement when a claim has no run behind it.

## 11. Traps

- **A head has moved.** If the model's branch moved, stop and report first (see the next trap). If jhan then
  says to go on, build the stack on its new head. `build.sh` refuses the
  tag `base`, so build that new head under a new tag, for example `base2`, with the targets
  `runtron t_gated_delta_net`. Use it in place of `base`. Then replace I1 by
  `git range-diff 72e1191804..0d69ef3ce8 <new base>..<head of PR 1>`. For I2, first join PR 2 and PR 3 into
  one commit, because `775bba7661` is one commit:
  `S=$(git commit-tree '<head of PR 3>^{tree}' -p <head of PR 1> -m joined)`, then
  `git range-diff 0d69ef3ce8..775bba7661 <head of PR 1>..$S`. If a cherry-pick conflicts in GDN
  files and the fix is not mechanical, stop and report. If the head of PR #5022 moved, port onto the new head
  and take the new merge base for section 6.5.
- **The model's branch is old.** On 2026-11-23 the lower 7 PRs of the model's stack were rewritten onto
  today's main. The model's branch did not move. When it moves, expect conflicts in GDN files that are not
  mechanical: at the head of PR #3221 the caller of the executor has another signature [R19]. Stop and report
  then.
- **The reboot of 2026-11-23.** delphi-3b35 was rebooted between the old campaign and yours (section 0.2).
  The kernel version is the same. The control start of section 7.5 repeats one old arm, `orig`. Its old TTFT
  medians of 3 runs are 0.384 s (1 user, prompt 1,024), 1.897 s (1 user, prompt 4,096) and 2.91 s (8 users,
  prompt 1,024). They are in `collected-controls.json` in the results folder of [R10]. Only `orig` repeats an
  old arm on the same binary. The arms `orig0` and `st0` have no old value. The arm `st` has only the old arm
  `base` of another commit (section 7.7). If the new `orig` differs from an old median by more than twice the standard
  deviation of your 3 runs, name the reboot as a possible cause and compare only inside the new campaign.
- **Two tasks, one machine.** See the last rule of section 7.1.
- **`bin/slice bench` on delphi-3b35.** Do not run it, also not with `--update`. It measures on the first
  slot of each half, so one test runs on the other users' half [R14]. The read-only forms
  `bin/slice bench --check` and `--check-platform` are safe.
- **Git 2.34.1** on the agent's machine has no `git merge-tree --write-tree`. Simulate a merge in a scratch
  clone that borrows the objects of the shared repository [R6].
- **ssh output.** A remote `cd` prints a directory listing, and ssh prints a terminal-title line. Use full
  paths and `git -C`.
- **NFS.** After you edit a script on the agent's machine, wait until delphi-3b35 sees the new text. Never
  edit a script while a copy of it runs.
- **Clocks.** delphi-3b35 prints UTC. The agent's machine prints Pacific time.
- **Old tags.** `build.sh` moves an existing tree to the new commit and removes the old binary. Use the new
  tags of section 7.2.
- **Analysis scripts.** `collect.py`, `compare.py`, `report_data.py`, `gen_report.py`, `decode_why.py` and
  `gen_pr_body.py` have the old arms, tags and cells fixed in their text [R8]. `gen_pr_body.py` asserts 3
  commits on `72e1191804`. E4B logs 1,025 prompt tokens for prompt 1,024, so the prefill rule of `collect.py`
  does not fit it.
- **Wrong sentences in the old chat** [R17]. (1) "The E4B generation tests take the new kernels": they do
  not. jhan has this correction. (2) "The test limits its context to 64 tokens": the text has 24 tokens, and
  the two `TRON_BOOK_*` variables size the key and value cache. (3) "The 2 new test programs" of the timing
  file: no new test name exists. jhan got (2) and (3) with this handoff. Repeat them in the report.
- **Background waits.** A shell command that waits in the background is stopped after about 10 minutes.
  Start it again, or let the job write a marker file and check for that file.
- **Permission system.** A run of a newly compiled test program on the agent's own machine was denied in an
  earlier session. Run test programs on delphi-3b35.

## 12. Files

| What | Where |
|---|---|
| This file | `/home/jhan/workspace/intel-AMX/GDN/status/handoff-gdn-pr-split-20261122.md` |
| The five fact files behind it | [R4] to [R8] |
| Results page and design page of the old work | [R9] |
| Scripts and results of the old campaign | [R10] |
| E4B results | [R11] |
| Body of PR #5572 as posted | [R12] |
| The agent's memory notes | [R14] |
| State of PR #5022 | [R15] |
| Full record of the writing session | [R17] |
| The Slack chat of 2026-11-23 | [R18] |
| The fact files of 2026-11-23, and the handoff of the rounding task | [R19], [R20] |
| Issue #5433, draft PR #5571, PR #3221 | [R21] |

## References

- [R1] https://github.com/positron-ai/tron/pull/5572
- [R2] https://github.com/positron-ai/tron/pull/3696
- [R3] https://github.com/positron-ai/tron/pull/5022
- [R4] `/home/jhan/workspace/intel-AMX/GDN/status/handoff-material/facts-cut.md`: every file of `775bba7661`
  with its part, the line ranges of the mixed files, the test cases per part, the ten counter keys, and the
  risks of the cut. It classes `gated_delta_net.hpp` as Part 0. Its note N1 holds the `normalized_query`
  question that section 6.2 settles.
- [R5] `handoff-material/facts-switch.md` in the same folder: every place that names `TRON_GDN_STATS`, the two
  readers, what is printed, and the smallest change list.
- [R6] `handoff-material/facts-partb.md`: the simulated cherry-pick, the 14 points where PR #5022 and Part B
  conflict in design, the port plan, and the measurement-only build.
- [R7] `handoff-material/facts-tests.md`: the rules of `AGENTS.md` on stacks, labels, tests and the changelog,
  word for word. Also the test programs, the CI workflows, the timing file, the lint commands, and the E4B
  generation test.
- [R8] `handoff-material/facts-scripts.md`: every script of the old run folder with its inputs, outputs and
  fixed values, and the list of edits for a new campaign.
- [R9] `/home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html`, published as
  https://claude.ai/artifact/T4FxXrJVomTvmX3UWG3jSY, and `gdn-amx-design.html` in the same folder.
- [R10] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/` (`build.sh`, `campaign.sh`, `unit-tests.sh`,
  `token-check.sh`, `logit-margin.sh`, `e4b-check.sh`, `e4b-tests.sh`, `pr-prep.sh`, `models.e4b.yaml`),
  `/home/jhan/workspace/intel-AMX/exec/gdn-20261120/` (`run-one.sh`, `models.gdn.yaml`),
  `/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh`, and the results in
  `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/`.
- [R11] `/home/jhan/workspace/intel-AMX/exec/results/gdn-e4b-20261122/`: `tokens/summary.txt`,
  `tests/summary.txt`, the run logs and the load snapshots.
- [R12] `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/pr-body.md`.
- [R13] `/home/jhan/.claude/skills/PR-description/SKILL.md`, `/home/jhan/.claude/skills/plain-english/SKILL.md`,
  `/home/jhan/.claude/skills/cpp-coding-guide/SKILL.md`, `/home/jhan/.claude/CLAUDE.md` and
  `/home/jhan/workspace/intel-AMX/CLAUDE.md`.
- [R14] `/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/MEMORY.md` is the index. Notes used
  here: `gdn-amx-project.md`, `delphi-3b35-default-server.md`, `pr-body-refetch-before-edit.md`,
  `no-names-in-github-issues.md`, `no-issue-numbers-in-source.md`, `worktree-prune-nfs-trap.md`. From the
  folder `-home-jhan-workspace-intel-AMX-muse-glimmer/memory/`: `delphi-3b35-no-slice-bench.md`,
  `tron-manual-legacy-ci-run.md`, `tron-main-merge-queue-squash.md`, `tron-pr-push-triggers-bot-review.md`.
- [R15] `/home/jhan/workspace/intel-AMX/muse-glimmer/status/handoff-pr5022-20261120.md`: the state of PR #5022.
- [R16] In the tron repository: `AGENTS.md` (stacks and labels at lines 12-18, tests in CI at lines 29-35,
  `bin/slice route` at line 92, all on main), `t/AGENTS.md`, `changelog.d/README.md` (on main), `README.ci.md`
  and `doc/slice.md`.
- [R17] `/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b.jsonl`
- [R18] Slack group chat of jhan with the GDN owner and two colleagues, 2026-11-23:
  https://positronai.slack.com/archives/C0CL3US5HAP/p1795460388146249 . jhan's message of 10:47 PST to one
  of the two colleagues: https://positronai.slack.com/archives/D0AVD4EG675/p1795459646960159
- [R19] `/home/jhan/workspace/smaller-tasks/numeric-rounding/handoff-material/`: `facts-stack.md` (the PR
  stack, the age of the model's branch, the three candidate bases), `facts-port.md` (trial cherry-picks of our
  commits onto main, onto the head of PR #3221 and onto the head of PR #5571), `facts-rounding.md` (the 22
  rounding calls, and what Part 0 and Part A need).
- [R20] `/home/jhan/workspace/smaller-tasks/numeric-rounding/handoff-numeric-rounding-20261123.md`: the handoff
  of the rounding task. Its folder `drafts/` holds a draft comment for issue #5433.
- [R21] https://github.com/positron-ai/tron/issues/5433 , https://github.com/positron-ai/tron/pull/5571 and
  https://github.com/positron-ai/tron/pull/3221
