# Handoff: split PR 4424 into a four-PR stack

Written 2026-10-10 02:0x UTC by Claude for the agent that executes the split. Update 1 (the answers to split-handoff-review.md, see split-handoff-update1.md) folded in on 2026-10-10 04:5x UTC. Update 2 (the second review's three findings and two edits) folded in on 2026-10-10 05:4x UTC. Decisions D1, D6, D8 and D11 answered by jhan on 2026-10-10 06:xx UTC (section 0); D8 = (c) with issue #4865. Companion files in this folder: split-plan.md (the analysis, with Update 1 and Update 2), split-plan-codex.md (the review), handoff-material/ (diffs, patches, scripts, logs).

## Short version

PR 4424 (the VNNI K layout for the K cache of 128-dimension heads, a draft, head 0a5334ccb6) becomes four stacked PRs: PR-1 the layout, its AVX-512 reader, the FPGA staging path and the build files; PR-2 the AMX kernel that reads the plane; PR-3 the shared block save; PR-4 the row-major tail block, the hardware-attention policy and the deb preset. The candidate trees of PR-1 and PR-2 exist as commits on scratch branches and pass a syntax check. PR-3 and PR-4 each need one patch applied. Your job: build the four branches, verify each on delphi-3bda, write the bodies, open PR-1 ready for review and PR-2 to PR-4 as drafts, and report.

## Words used here

- PR 4424: positron-ai/tron (tron = the inference program) pull request "VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save". Branch jhan-amx-vnniK, base main, merge base be0d5565b3, head 0a5334ccb6 (29 files, +4054/-198 lines). PR 4774 = the save_k fold PR, PR 4737 = the row-major tail block PR; both were merged into PR 4424 on 2026-10-08. PR = pull request.
- K cache: the stored key vectors of past tokens. Plane: the packed K storage of one KV page and one KV head (16 KiB). KV page: a 64-token block of the K and V caches. kv_mul: the number of query heads that share one KV head. QK: the query-key score product. B operand: the right-hand tile of the AMX multiply. Dotter: the row-major QK score loop. bf16: the 16-bit brain floating-point format.
- AMX: Intel Advanced Matrix Extensions, the tile instruction set. AVX-512: the 512-bit vector instruction set. VNNI layout: the pair-interleaved operand layout the AMX tile multiply reads as its right operand. The option: the CMake switch TRON_K_VNNI. Kill switch: the environment variable TRON_AMX_DISABLE=1, which turns the AMX kernels off at run time.
- FPGA: the attention accelerator card. Hardware attention: attention scores computed on the FPGA. Software attention: scores computed on the CPU. FPGA staging: the gather that copies K rows into the buffers the FPGA reads.
- save_k: the function that stores one pass's K rows into the cache. Shared block save: the K store that writes one whole 16-token block at a time and shares the work with the idle main helper threads. Per-row store: each token's row written on its own (4 AVX-512 scatters).
- Concerns (letters used in the plan and in the patch names): L = layout, storage, views, per-row store; R = AVX-512 reader; G = FPGA staging; A = AMX kernel on the plane; S = shared block save; T = row-major tail block + hardware-attention policy (the PR 4737 content); B = build, CI, preset, README, cost rows.
- CI: continuous integration, the automatic build-and-test runs on GitHub. deb preset: the CMake preset that builds the released Debian package. Cost rows: the per-test run-time rows in config/test-benchmarks.json that the CI's bench check reads. Benchmark-binary mismatch: the legacy CMake workflow benchmarks the runtron of its build job (options on) when the hand-over works and a locally rebuilt runtron (options off) when it does not.
- Stack: a chain of PRs, each based on the previous one. Repo rules (AGENTS.md):
  - only the PR based on main is ready for review (lines 12-13);
  - every descendant stays draft, and after the parent merges only the next PR is promoted (12-13);
  - every PR gets the label "Skip benchmarks" (14-16);
  - the label "Run CI" is never added without jhan's explicit direction (17-18).
- delphi-3bda: the Intel Granite Rapids test machine, shared with the nightly CI and with Bill (a colleague). "Our half" = socket 1 (cpus 72-143 and 216-287). The lease: the file the nightly CI writes to claim the machine. rinzler: the production server; rinzler@N: its systemd units; platformd: the service manager that supervises them. runtron: tron's command-line tool. genoa96 and andoria: the AMD test hosts.
- claude-box: the development container this handoff was written in (host claude-agentsrv). It has no nix today (nix = the package manager that provides tron's build toolchain). So it cannot build tron.
- lcheck: a clang 19 syntax-only compile of one translation unit with the product flags (~/workspace/ai-runs/lcheck/lcheck.sh). gen and gen-amxoff: the two flag sets of lcheck (AMX dispatch on, AMX dispatch off). Syntax matrix: lcheck over 22 cells (gen or gen-amxoff, option off or on, 5 test files, plus amx_attn.cpp in gen).
- Probe branches: jhan-split-probe and jhan-split-probe-pr2 in the worktree ~/workspace/ai-runs/tron-split-probe (repository ~/workspace/tron). Not pushed.
- Reference tree: ~/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K, the worktree of jhan-amx-vnniK at 0a5334ccb6. Read it. Do not change it.
- ingest: tron's Haskell code generator. cabal: the Haskell build tool. fourmolu: the Haskell formatter. lefthook: the git hook runner the repo configures (absent on claude-box). NFS: the network file system that shares ~/workspace between claude-box and delphi-3bda.
- Smoke: a short token-identity run of one user, greedy (temperature 0), compared token by token. A/A: two runs of the same binary. Paired t-test: the test that decides whether two arms differ beyond run-to-run noise. Cell: one model, parallelism, user count, prompt length and attention mode. tp2 / tp4: tensor parallelism over 2 / 4 engines. TPS: decode tokens per second per user. TTFT: time to first token.
- Issue #4444: the token divergence of a VNNI binary against the row-major binary, and the kill-switch rollback contract. Issue #4500: the FPGA-attention decode loss of the per-token 64-line column access under the VNNI layout.
- Codex: OpenAI's code-review agent, the second reviewer of the plan. The classifier: the permission checker of Claude Code's auto mode. It refuses some commands (section 7).

## 0. Decision sheet (fill in before step 1)

jhan decides these. Until an answer is written here, use the default in the right column and say so in your report.

| Id | Question | Default |
|---|---|---|
| D1 | Four PRs (A separate), or three (A folded into PR-1)? | DECIDED (jhan, 2026-10-10): four. |
| D2 | Drop the CMake requirement "TRON_K_VNNI requires TRON_AMX_DISPATCH" in PR-1: the FATAL_ERROR block src/tron/CMakeLists.txt:236-238 (keep the outer `if(TRON_K_VNNI)` at 235 and the definition at 239) and the clause "(requires TRON_AMX_DISPATCH; ...)" in the option help at CMakeLists.txt:47? | drop, keep both compile definitions |
| D3 | PR-1's temporary gate: one clause in apply_page_tok only, or also gate amx_eligible so a VNNI build does not pack Q for nothing? | one clause only |
| D4 | PR-2 (AMX kernel) before PR-3 (shared save)? | yes |
| D5 | Cell sets per PR (section 5.4) | as listed |
| D6 | Who writes the Short version and Background of each PR body? | DECIDED (jhan, 2026-10-10): the executor writes the whole body of each new PR, including the Short version and the Background. The four PRs are new PRs, so the protected-section rule of PR 4424 does not apply to them; it still applies to PR 4424's own body. The executor may reuse sentences of the freshly fetched PR 4424 body (`gh api repos/positron-ai/tron/pulls/4424 --jq .body`, never the snapshot) where they hold for that PR, and must not carry over claims that do not hold (for PR-1: the AMX kernel and the shared block save; for PR-4: the per-token 64-line decode scatter of the old section 4). |
| D7 | Tag the current head and keep PR 4424 open until PR-4 is open? | yes: a local tag pr4424-pre-split-0a5334ccb6 (do not push the tag unless jhan says so), and PR 4424 stays open |
| D8 | Required CI coverage of the option-on paths. The policy (AGENTS.md:20-26) requires, before a test is committed, that a required CI suite executes it; agents may not decide that an exception applies. Options: (a) add `-DTRON_K_VNNI=ON -DTRON_AMX_DISPATCH=ON` to the Nix test build (nix/cmake-tron-test-build.nix): the layout tests and the dispatch fakes then run in the PR suite, but the option-off (row-major 128-dimension K) build then has no required per-PR coverage at all (the coverage preset runs only by manual dispatch, cpp-coverage.yml:3-4; deb-smoke.yml only checks package-repository access with --apt-only and builds nothing), so (a) gives that coverage up and needs that said in the decision; (b) a second Nix test configuration with both flags, next to the current one: both layouts stay covered per PR at the cost of a second C++ build per PR; (c) an explicit exception, approved by jhan in writing, recorded in split-status.md and in each body. In every option one case stays unexecuted: the AMX identity case of t_amx_numerics returns early without AMX hardware (t/t_amx_numerics.cpp:208-211), and the required test jobs of gcp-nix.yml run on runners labeled fpga, test, avx512 (gcp-nix.yml:464, 555, 622), none labeled for AMX. So (a) and (b) also need either a required job on an AMX runner (none exists today; whether one can be added is Insufficient data) or jhan's explicit written exception for that one case. Choosing a compile configuration does not approve that exception by itself. | a prerequisite of step 1.2 (the first test-bearing commit), not of opening PR-1. The executor asks jhan, with this row, and does not commit tests before an answer. The chosen change enters PR-1 as its own commit (step 1.4) and is listed in the allowed final differences (step 4.3). The PR-2 body states where the identity case executes (delphi-3bda by hand; the manual-dispatch CMake lane on an Intel runner) and under which approval. DECIDED (jhan, 2026-10-10): option (c) for now. jhan approves that the tests of the stack run by hand on delphi-3bda and in the legacy CMake lane until the CI change lands; the change itself is tracked in issue #4865 (jhan works it with the CI owner), and the AMX-hardware identity case is part of the same approval. The executor states the gap and cites #4865 in every PR body under Verification, and makes no change to nix/cmake-tron-test-build.nix in the stack (the CI owner's change lands on main on its own). |
| D9 | Add the label "Run CI" to the draft PRs? | no, never without jhan's explicit direction (AGENTS.md:17-18) |
| D10 | PR-3 as the tested shared-save form (with the masked partial-block path PR-4 replaces), or pre-simplified? | tested form |
| D11 | Build host. jhan's instruction to codex (~/.codex/AGENTS.md:26-28) designates sw-dev-01 for tron builds and delphi-3bda for real tests; from this container `ssh sw-dev-01` fails on a changed host key. | DECIDED (jhan, 2026-10-10): delphi-3bda. Build in an isolated worktree under /var/tmp/jhan on our half, with nice, under the lease and the guard (section 5.3), and report the build time (about 10 min per configuration) as machine use. sw-dev-01 is not used for this work. |

### 0.1 D8 in plain words

- The rule. The repository says (AGENTS.md, "Test policy"): a test may be committed only if the CI that every pull request must pass (the required suite) actually runs it. Running the test by hand on delphi-3bda does not count. Only jhan may approve an exception; an agent may not.
- The fact. The CI that every PR must pass (gcp-nix.yml) builds tron with both switches off: TRON_K_VNNI off and TRON_AMX_DISPATCH off. In that build, PR-1's new layout tests are compiled out (they sit under `#ifdef TRON_K_VNNI`), the VNNI branches of t_llama_unit take the row-major path, and the two AMX test files compile to a placeholder that only prints "nothing to test". The only CI that turns the switches on is cmake-single-platform.yml, and it runs only when someone starts it by hand. PR 4424 is in this state today, and PR 3879 was too.
- Why it blocks PR-1. The policy is checked before a test is committed. PR-1's first test-bearing commit (step 1.2) therefore needs the decision first, and the executor cannot make it.
- The options.
  - (a) Change the PR CI's test build (nix/cmake-tron-test-build.nix) to switch both on. The PR CI then runs the layout tests and the AMX dispatch fakes. Cost: the row-major K path for 128-dimension heads is then compiled by no PR CI at all (only the manual coverage lane), so that coverage is given up.
  - (b) Add a second test build to the PR CI with both switches on, next to the current one with both off. Both layouts stay covered. Cost: about twice the C++ build time per PR; the CI owner decides whether that is acceptable.
  - (c) Approve, in writing, that these tests run only in the manual lane and on delphi-3bda. The gap is then written into every PR body under Verification. This is the exception the policy allows only with jhan's explicit approval.
- One case stays open under (a) and (b). The bit-identity case of t_amx_numerics needs real AMX hardware. The CI test machines are labeled avx512 and have no AMX label, so that case returns early ("skipped") in CI whatever the switches say. So (a) or (b) also need either an AMX machine in the required suite (whether one can be added is Insufficient data) or jhan's written exception for that one case. PR 3879's existing AMX cases on main are in the same situation today.
- Recommendation: (b) if the CI owner accepts the extra build time, otherwise (a) with the row-major loss stated in the PR body; in both cases the written exception for the one AMX-hardware case. The executor records the choice in split-status.md and asks the CI owner through jhan.

## 1. Context

- Why: jhan judges PR 4424 too big for manual review (4,054 added lines). Ben (bgamari) reviewed twice on 2026-09-21. He asked for a typed VNNI tensor (done) and for folding save_k_helper (the helper-thread copy of save_k) into save_k with a worker index (done in PR 4774). No reviewer asked for a split.
- The analysis (split-plan.md sections 1-9, Update 1, Update 2):
  - every hunk of the 29 files was labeled by concern;
  - the dependency graph is one-directional: A needs L only, S needs L only, T needs A, S, R and G, and L without R does not compile with the option on;
  - two of the three cuts existed as separate tested PRs (PR 4774 = S fold, PR 4737 = T);
  - the third cut (A out, S out) was built as real trees and is syntax-clean;
  - Codex reviewed the plan and supports the split;
  - three planning agents and one judging agent converged on the same stack.
- The premise "VNNI-K is independent of AMX" holds at the code level. The layout and reader headers have no AMX guard. The reader compiles without AMX flags. It does not hold at the benefit level on AMX hosts: PR-1 alone with the option on is 7 to 11 % slower in decode than main's AMX kernel (the kill-switch run, AMX off and VNNI reader on, stands in for PR-1). So PR-1 ships with the option OFF in every preset. The deb preset line is in PR-4.
- Known gap you inherit: the required PR CI (gcp-nix.yml) builds with neither TRON_K_VNNI nor TRON_AMX_DISPATCH. The workflow that carries the flag (cmake-single-platform.yml) runs by manual dispatch only. Draft PRs get no build or test in CI without the "Run CI" label. See D8 and D9.

## 2. Inputs and where they are

Trees and commits (all in repository ~/workspace/tron; the probe worktree is ~/workspace/ai-runs/tron-split-probe):

| Name | Commit | What it is | Status |
|---|---|---|---|
| base | be0d5565b3 | merge base with main (the PR 4557 merge commit) | on main |
| PR-1 tree | 76a0160b72 | L+R+G+B = ba69cb513e minus A minus S (branch jhan-split-probe) | syntax matrix 22/22 at 0 errors, independently re-checked; never built or run |
| PR-1 + S | 3c56db9a95 | the A-off stage (branch jhan-split-probe) | syntax 22/22; never built |
| PR-2 tree | 4d3a042225 | PR-1 + A (branch jhan-split-probe-pr2, checked out) | syntax 22/22; never built |
| PR-3 content | ba69cb513e | PR-2 + S (= the PR head minus the 4737 merge minus the preset); differs from the 3bda-tested 45e6bb266d by one comment | built and tested on 3bda 2026-10-08 |
| PR-4 content | 9d5c7a389b | + the 4737 merge (T) | built, tested, whole-machine campaign 2026-10-09 |
| head | 0a5334ccb6 | + the deb preset line and README paragraph | PR 4424 head |
| main now | a0056c1ecc (commit date 2026-10-09 22:06 UTC, fetched 23:4x UTC) | 165 commits past base; TronCpp.hs changed by 442 lines, t_llama_unit by 122 added lines | moves daily |

Patches and diffs in handoff-material/ref/ (apply with `git apply --3way`, never by hand-copying):

| File | Range | Use |
|---|---|---|
| PR1-diff-base..76a0.patch | be0d5565b3..76a0160b72 | the PR-1 content as one patch (23 files, +1846/-160 lines) |
| PR2-diff-76a0..4d3a.patch | 76a0160b72..4d3a042225 | the PR-2 content (9 files, +277/-61), already repaired |
| S-diff-76a0..3c56.patch | 76a0160b72..3c56db9a95 | the S content against the PR-1 tree (8 files, +673/-72); on PR-2 expect comment conflicts in 2 to 4 files |
| S-diff-4d3a..ba69.patch | 4d3a042225..ba69cb513e | the S content against the PR-2 tree (9 files, +678/-75): the patch step 3 applies |
| A-diff.patch | 3c56db9a95..ba69cb513e | the raw A diff (for reference; PR2-diff is the repaired form) |
| T-4737-merge.diff | ba69cb513e..9d5c7a389b | the T content (10 files, +1459/-113), byte-identical to the PR 4737 merge diff |
| B-preset.diff | 9d5c7a389b..0a5334ccb6 | the deb preset line + README paragraph (2 files, +7/-2) |
| L-orig-first-commit-0ec355b641.diff, S-orig-striping-0b54..804a.diff, S-4774-fold.diff, P-typed-port-66c2..154d.diff | history | wording references for the per-row save_k, the shared save, the fold, the typed port |

Other material:

- handoff-material/diff/: the per-file diffs of the whole PR (base to head). handoff-material/hunk-classification.json: every hunk labeled by concern.
- handoff-material/probe/: the subtraction edit scripts (A_*.py, S_*.py, edit.py), lcheck-vnni.sh (lcheck.sh plus -DTRON_K_VNNI), matrix.sh (takes W=<worktree>, records the compiler exit status per cell, exits 1 on any failed or missing cell), and the matrix logs (out/baseline, out/A-off-r1, out/S-off-r1). handoff-material/probe-pr2/: repair.py (the two comment repairs of PR-2), matrix.sh, logs. handoff-material/pr1check/: run.sh, a 38-cell matrix (more translation units; takes W=<worktree>, same verdict rule), and its logs on the PR-1 tree, 0 errors. handoff-material/refute1/ and refuter2/: the control matrices (a tree without R fails at the software loop; a tree with the raw A patch fails at page::k).
- handoff-material/pr4424-body-20261009.md: the PR 4424 body as of 2026-10-09, the source of the four new bodies. The live body may have changed since; re-fetch with `gh api repos/positron-ai/tron/pulls/4424 --jq .body`.
- Reusable 3bda scripts under ~/workspace/intel-AMX/exec/:
  - merge4737-20261008/build-test.sh + launch.sh: VNNI build, 6 unit tests, a kill-switch run of t_amx_numerics, the ingest cabal test, clang-format / fourmolu / diff --check, the row-major build;
  - sync4424-20261002/smoke.sh: token identity, arms by binary;
  - sync4424-20261002/campaign.sh: runtron cells, base vs head;
  - i4525-20260922/host-suite.sh: the host test suite;
  - pr4424ci-20261009/: the whole-machine nightly-config campaign;
  - sync4424b-20261007/chain.sh: a full chain with serving down and up, host suite, smokes, cells;
  - lib-guard.sh: the machine guards; bill-share.sh: take and release of Bill's marker.
  Fork these into exec/split-<date>/. Never edit a script that a 3bda process is running.
- Memory of the owner session (for the next Claude session only): ~/.claude/projects/-home-jhan-workspace-intel-AMX/memory/split-4424-plan.md and 3bda-shared-with-bill.md (the marker rule).

## 3. Target: the stack

| PR | Branch (new) | Base | Content | Size (added/removed lines) | Opens as |
|---|---|---|---|---|---|
| PR-1 | jhan-vnnik-1-layout | main | L+R+G+B minus the deb preset line and README deb paragraph; temporary gate in apply_page_tok; D2 | +1846/-160 (tests 965) | ready for review, label Skip benchmarks |
| PR-2 | jhan-vnnik-2-amx | jhan-vnnik-1-layout | A; removes PR-1's temporary gate | +277/-61 | draft, Skip benchmarks |
| PR-3 | jhan-vnnik-3-shared-save | jhan-vnnik-2-amx | S (tested form, D10) | +678/-75 | draft, Skip benchmarks |
| PR-4 | jhan-vnnik-4-tail-block | jhan-vnnik-3-shared-save | T + deb preset line + README deb paragraph | +1466/-115 | draft, Skip benchmarks |

Titles (present tense, no history): PR-1 "VNNI K: the layout, its AVX-512 reader and the FPGA staging path"; PR-2 "VNNI K: the AMX QK kernel reads the plane as its B operand"; PR-3 "VNNI K: shared block save"; PR-4 "VNNI K: keep short K-cache writes row-major, convert at the forward end; deb preset turns the layout on".

Invariants of the stack (check them after every step):

- PR-N's tree compiles and passes its tests with the option off and on. PR-1 also with TRON_AMX_DISPATCH off and the option on (that is what D2 permits).
- No PR references a symbol that only a later PR defines. Grep list per PR in section 5.2.
- PR-4's tree, merged with main, equals the PR 4424 head merged with the same main, except: the D2 lines, the comment wordings PR-1 and PR-2 carry and PR-3 and PR-4 restore, the measured cost rows, and the approved D8 CI change if any. Every other difference must be explained in your report or removed.

## 4. Action plan

### Step 0: preparation (claude-box, about 30 min)

1. Read split-plan.md fully (sections 1-9, Update 1, Update 2) and split-plan-codex.md. Read AGENTS.md of tron. Read ~/workspace/notebook/handoffs/check-CI.md (the lease and guard rules) and the memory file 3bda-shared-with-bill.md (the marker rule). The notebook file share-3bda-with-bill.md holds only the claim-file protocol.
2. `git -C ~/workspace/tron fetch origin main jhan-amx-vnniK`. Confirm origin/jhan-amx-vnniK is still 0a5334ccb6. If not, stop and report: the plan's trees assume that head.
3. Confirm the probe trees: `git -C ~/workspace/ai-runs/tron-split-probe log --oneline -3 jhan-split-probe jhan-split-probe-pr2` shows 4d3a042225, 76a0160b72, 3c56db9a95. `git status --porcelain` is empty.
4. Confirm tooling: `uvx --from ziglang==0.14.0 python -m ziglang clang --version` works (the lcheck compiler). `ls /nix` is empty (no builds here). `ssh -o ConnectTimeout=8 delphi-3bda uptime` works.
5. Tag the head locally (D7): `git -C ~/workspace/tron tag pr4424-pre-split-0a5334ccb6 0a5334ccb6`.
6. Create your exec folder ~/workspace/intel-AMX/exec/split-$(date +%Y%m%d)/ and the status file split-status.md in this folder (section 7).

### Step 1: PR-1

Construction (claude-box; worktree ~/workspace/ai-runs/tron-split-pr1, branch jhan-vnnik-1-layout):

1. `git -C ~/workspace/tron worktree add ~/workspace/ai-runs/tron-split-pr1 -b jhan-vnnik-1-layout be0d5565b3`.
2. Bring in the PR-1 tree as topical commits, not as one commit. Order:
   - (a) "tensor: the K VNNI layout, owner and views" (h/tron/tensor/k_vnni.hpp, kv_cache_fwd.hpp);
   - (b) "kv_cache: store K of 128-dimension heads in the VNNI layout" (kv_cache.hpp integration, model.hpp per-row store, the CMake option and the tron_model_compile_config definition);
   - (c) "kernels: the AVX-512 reader of the VNNI K layout" (kernels/k_vnni.hpp, the self_attention.hpp software loop, the attn_stats.hpp comment, the temporary gate);
   - (d) "gof: the FPGA staging path reads K rows through the layout" (gof.hpp, gof.cpp, full.hpp, the three test lambdas);
   - (e) "tests: t_k_vnni_layout and the t_llama_unit cases" (t/CMakeLists.txt registration, cost rows), with the tolerance change of t_llama_unit's split-vs-unsplit case in this commit or earlier (every later commit must pass);
   - (f) "ci: build and test the CMake lane with TRON_K_VNNI=ON" (workflow flag, README.ci.md).
   The simplest way: `git checkout 76a0160b72 -- <files of commit a>`, commit, and so on. At the end `git diff 76a0160b72` must be empty.
3. One more commit, "VNNI K: the layout needs no AMX dispatch", with these edits (line numbers are those of 76a0160b72; re-find each by its text):
   - D2: delete src/tron/CMakeLists.txt:236-238 (the `if(NOT TRON_AMX_DISPATCH)` / FATAL_ERROR / `endif()` block) and the three justification comment lines 232-234 ("The AMX ... QK kernel ... The option therefore requires TRON_AMX_DISPATCH."). Keep `target_compile_definitions(tron PUBLIC TRON_K_VNNI)` and the tron_model_compile_config INTERFACE definition. In CMakeLists.txt:47 drop "(requires TRON_AMX_DISPATCH; ...)" from the option help.
   - h/tron/kernels/k_vnni.hpp:3-5: "It serves partial pages, hosts without AMX (...) and the AMX kill switch" becomes "Until the VNNI AMX kernel is merged it serves every page of a VNNI slot; after that, partial pages, hosts without AMX and the AMX kill switch".
   - h/tron/kernels/k_vnni.hpp:43-44: "This reader is one of the two layout-specific readers allowed to take the plane address" becomes "This reader is the layout-specific reader allowed to take the plane address".
   - h/tron/tensor/k_vnni.hpp:178-179: drop "and the AMX QK kernel reads the plane in 64-byte tile rows".
   - t/t_llama_unit.cpp:429: drop "and the AMX tile rows".
   - README.ci.md: remove the deb sentences (head lines 593-597) and restore "The option is OFF by default in every other build." (76a0160b72 already has that sentence at line 593; confirm).
   - kv_cache.hpp, the kill-switch paragraph of Note [K VNNI storage]: add "Until the VNNI AMX kernel is merged, TRON_AMX_DISABLE=1 changes no score and no visit path for 128-dimension heads. No AMX visit can occur for a VNNI slot." This is PR-1-only text. Step 2.3 removes it.
   - PR-1-only comment text, all removed or reverted by PR-2: the two sentences above; the "Until the VNNI AMX kernel is merged" wording of h/tron/kernels/k_vnni.hpp:3-5; "the layout-specific reader" at :43-44; the Note [K VNNI storage] consumer items 2 and 3 and the "Why" paragraph in their PR-1 wording. The README sentence "The option is OFF by default in every other build." stays until PR-4.
4. No D8 commit: D8 is decided as (c) with issue #4865 tracking the CI change, which the CI owner lands on main separately. If that change is on main before PR-1 merges, the main merge of step 5 brings it in; nothing in the stack touches nix/cmake-tron-test-build.nix.
5. Merge main: `git merge --no-ff origin/main` (a merge, not a rebase: repo convention). Expect conflicts in t/t_llama_unit.cpp (main added 122 lines there) and possibly kv_cache.hpp. TronCpp.hs is untouched by PR-1. Resolve, keep main's new tests intact, re-run the syntax matrix.
6. Syntax matrix (section 5.1) on the result: 22 cells at 0 errors. The 38-cell variant of handoff-material/pr1check/run.sh covers more translation units.
7. Checks: clang-format 19 on every changed C++ file (`uvx --from clang-format==19.1.7 clang-format --dry-run --Werror <files>`), `git diff --check origin/main HEAD -- ':!lib/**'`, no `<cassert>`, the grep list of section 5.2.
8. 3bda chain (section 5.3): build both layouts, plus AMX dispatch off with the option on (D2); unit tests; kill-switch runs of t_llama_unit and t_amx_numerics; host suite; smokes; cells. Record results in split-status.md.
9. Body (section 6; the executor writes all of it, D6). Open PR-1 against main, ready for review, label "Skip benchmarks", assignee jhan-positron. Do not add "Run CI".

### Step 2: PR-2

1. `git -C ~/workspace/tron worktree add ~/workspace/ai-runs/tron-split-pr2 -b jhan-vnnik-2-amx jhan-vnnik-1-layout`.
2. `git apply --3way handoff-material/ref/PR2-diff-76a0..4d3a.patch`. The patch was made against 76a0160b72. After PR-1's main merge and comment commit, expect small context conflicts in kv_cache.hpp (the consumers list of Note [K VNNI storage]) and amx_attn_iface.hpp. Resolve so the comments name L, R, G and A only. handoff-material/probe-pr2/repair.py shows the two repaired texts.
3. Restore the comments PR-1 reworded: the kill-switch paragraph of Note [K VNNI storage] goes back to the head's wording (0a5334ccb6, kv_cache.hpp, the paragraph starting "The kill switch keeps the layout": with TRON_AMX_DISABLE=1 a TRON_K_VNNI binary runs the AVX-512 reader), h/tron/kernels/k_vnni.hpp:3-5 and :43-44 go back to the head's wording, and the consumer items name the dense AMX path again. Grep the tree for "No AMX visit can occur" and "Until the VNNI AMX kernel": both must be absent.
4. Two commits: "amx: the QK kernel on the VNNI plane" (amx_attn.cpp, amx_attn_iface.hpp, the self_attention.hpp dispatch, the gate removal) and "tests: bit identity and the dispatch fakes for the VNNI kernel" (t_amx_numerics, t_amx_dispatch_dtype, the t_llama_unit probe, the README sentence).
5. Grep: "temporary until" must be absent. qk_vnni_128x4 must be present in the kernel, the interface, the dispatch and the three tests.
6. Syntax matrix 22/22, clang-format, diff --check. 3bda chain with real AMX for t_amx_numerics. Body. Open as draft on jhan-vnnik-1-layout, label Skip benchmarks.

### Step 3: PR-3

1. Worktree ~/workspace/ai-runs/tron-split-pr3, branch jhan-vnnik-3-shared-save from jhan-vnnik-2-amx.
2. `git apply --3way handoff-material/ref/S-diff-4d3a..ba69.patch` (the S content against the PR-2 tree: 9 files, +678/-75, including the Note [QK orientation] restoration in amx_attn_iface.hpp; the older S-diff-76a0..3c56.patch, 8 files against PR-1, stays only as a reference). Expect comment conflicts in kv_cache.hpp (consumer item 1 and the typed-operations list), tensor/k_vnni.hpp (header comment), amx_attn_iface.hpp (Note [QK orientation]: restore the three S sentences the PR-2 repair replaced), possibly t_llama_unit.cpp. The code hunks (model.hpp save_k, common.hpp, the two Haskell files, store_block, set_k_block, the tests) must apply unchanged. Check: `git diff ba69cb513e -- <the 9 files of the patch>` after the apply shows only the main-merge differences and the PR-1 and PR-2 comment wording, nothing else in code.
3. The t_llama_unit save_k case comes back in the S diff in its tested form (the three-thread SECTION with worker_ix and the window checks). Do not rebuild it by hand.
4. Commits: "save_k: 16-token block store for the VNNI K plane" (tensor store_block + transpose, set_k_block, the block path of store_k_block); "save_k: share the K store with the idle main helpers" (window, work units, worker_ix / n_workers, common.hpp, Note [Shared block save], watchdog); "ingest: the helpers call save_k at the attention statement" (TronCpp.hs, LoopyTronSpec.hs); "tests: block save and the shared save case".
5. Haskell: main changed TronCpp.hs by 442 lines since the base. The S hunks there may conflict with the main merge that PR-1 brought. Resolve against the current generator text. The generated call text must be `save_k<...>(q_batch->outer_batch, k, 0, n_workers)` on the main side and `..., worker_ix, n_workers)` on the helper side (LoopyTronSpec.hs checks both). Run the fourmolu check in the nix shell on 3bda.
6. Syntax matrix, clang-format, diff --check. 3bda chain with the ingest cabal test (step A2) and the generated-plugin grep (main-side == helper-side save_k counts, 0 save_k_helper). Cells must include tp4 prompt 1024 (the TTFT claim). Body. Open as draft on jhan-vnnik-2-amx.

### Step 4: PR-4

1. Worktree ~/workspace/ai-runs/tron-split-pr4, branch jhan-vnnik-4-tail-block from jhan-vnnik-3-shared-save.
2. `git apply --3way handoff-material/ref/T-4737-merge.diff`, then `git apply --3way handoff-material/ref/B-preset.diff`. The second patch carries the README deb sentences too (it replaces PR-1's line "The option is OFF by default in every other build."); check that the paragraph appears once and matches the head's README.ci.md lines 591-610. The T diff moves `#include <cstring>` from kernels/k_vnni.hpp to tensor/k_vnni.hpp. Both states compile. Keep exactly one include.
3. Comparison (the stack invariant), run twice: once after step 4.2 and again after the last commit of step 4.5 (the cost-row refresh), on the exact commit that will be pushed. In a scratch worktree, merge origin/main (the same commit you merged into PR-1) into 0a5334ccb6. Then `git diff <that merge> jhan-vnnik-4-tail-block`. Allowed differences: (1) the D2 lines (CMakeLists.txt:47 help text, the FATAL_ERROR block); (2) comment wording only where PR-1 and PR-2 reworded and PR-3 and PR-4 restored (the PR-1-only sentences of step 1.3 must be gone, PR-2 reverts them); (3) the measured cost rows of config/test-benchmarks.json, reported as measurement-record changes with the bench run's date and host, separate from source changes; (4) the approved D8 CI change (nix/cmake-tron-test-build.nix or the added configuration), if D8 is (a) or (b). Nothing else in code. List each difference in the report.
4. Commits: "kv_cache: keep short K-cache writes row-major; convert at the forward end" (bits, note_k_row_saved, pending blocks, conversions, row_major_row, k_row_if_row_major, k_forget_row, copy semantics); "attention: the dense gate and the dotter for row-major tail rows" (self_attention.hpp, amx_attn_iface.hpp, full.hpp, kernels/k_vnni.hpp); "model: no forward-end conversion for hardware-scored operations" (the policy, Note [Row-major blocks under hardware attention]); "tests: tail block, page state, dispatch records rows"; "CMakePresets: the deb preset compiles the VNNI K layout".
5. Syntax matrix, clang-format, diff --check. 3bda: the full chain plus the whole-machine nightly-config campaign (exec/pr4424ci-20261009: 14 configs + the qwen 8k software-attention cell, base = the nightly deb of the day, target = a deb built from PR-4's head). The campaign takes about 8 h and starts after the nightly ends. Bill's marker rules apply. Run `bin/slice route` on delphi-3bda first and obey its verdict (section 5.3). Cost rows: `bin/slice bench --update` for t_k_vnni_layout, t_llama_unit, t_amx_numerics, t_amx_dispatch_dtype on the idle whole machine, committed as "chore(bench): refresh the cost rows". Body. Open as draft on jhan-vnnik-3-shared-save.

### Step 5: after each parent merges

Promote only the next PR (mark it ready for review). Merge origin/main into it. Re-run its syntax matrix, clang-format and the 3bda unit-test chain. Update its body's Verification provenance (commit id + date). Report. Never rebase a reviewed branch.

## 5. Checks: the syntax matrix, the grep lists, the delphi-3bda chain, the claims

### 5.1 Syntax matrix on claude-box (no nix needed)

```
W=<worktree> bash handoff-material/probe/matrix.sh <label>     # 22 cells, about 1 min; summary in handoff-material/probe/out/<label>/summary.txt
```

By hand, one cell: `ERRLIM=0 ~/workspace/ai-runs/lcheck/lcheck.sh <gen|gen-amxoff> <file> <worktree> 2>&1 | grep -c 'error:'` (option off) and the same with handoff-material/probe/lcheck-vnni.sh (option on). Files: t/t_llama_unit.cpp, t/t_k_vnni_layout.cpp, t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp, t/heterogeneous_scheduler_compile.cpp in both trees, plus src/tron/kernels/amx_attn.cpp in gen. A cell passes only when the compiler's exit status is 0 and the log has no 'error:' line. matrix.sh records both (`rc=N errors=M` per cell) and exits 1 unless every expected cell is present with rc=0 and errors=0; check the script's exit status, not only the summary. Prove the counter is live once per tree in both directions: an untracked file with a deliberate syntax error must give errors=1, and a run with the compiler launcher made unavailable (for example PATH without uvx) must give rc!=0 and a MATRIX FAILED verdict (delete the probe file afterwards). Limits: syntax and template instantiation only. No link, no generated model translation units, no runtime, no CMake configure.

### 5.2 Symbols that must be absent, per PR

- PR-1 must not contain: qk_vnni_128x4, pack_q_rows_128x4, Q_ROWS_TILE_4, K_EVEN_PANEL_TILE_5, K_ODD_PANEL_TILE_6 (A); store_block, transpose_16x16_epi32, set_k_block, k_store_window, k_store_cut_units, k_store_shared, k_join_timeout_s, FULL_BLOCK_0XFFFF, LANES_16, "Shared block save", save_k with worker_ix or n_workers (S); note_k_row_saved, note_k_block_saved, k_vnni_blocks, k_rows_saved_, convert_pending_k_blocks, pending_k_blocks_, block_to_vnni, block_to_rows, row_major_row, k_row_if_row_major, k_forget_row, k_layout_dense, BLOCKS_PER_PAGE_MASK_0XF, "Row-major tail block", "Row-major blocks under hardware attention", cached_operation_uses_hw inside save_k (T). "temporary until" must be present in two comments (kv_cache.hpp and t_amx_dispatch_dtype.cpp; grep count 2 at 76a0160b72).
- PR-2 must not contain the S and T lists above. "temporary until" must be absent.
- PR-3 must not contain the T list above.
- PR-4: nothing is forbidden. The comparison of step 4.3 is the check.

The probe found that main itself uses worker_ix in threading.hpp and plugins/llama.hpp, and "main helpers" in several files. Those are not S code.

### 5.3 delphi-3bda rules and the per-PR chain

Rules (notebook check-CI.md "Rules for our own work on delphi-3bda", lines 258-270; memory 3bda-shared-with-bill.md; this project's memory):

- Route: before the hardware chain, run `bin/slice route` from the worktree on delphi-3bda and obey the verdict (AGENTS.md:78-88). For `local-legacy` the chain's direct runtron launches are the normal commands. For `local-shared-dice` the smoke and cell scripts must submit through the shared Dice service; never bypass a blocked or shared route with raw FPGA commands or DICE_DISABLE=1. A free CI lease is not a route decision.
- Work in an isolated worktree under /var/tmp/jhan/<name> on 3bda's local disk (or on sw-dev-01 per D11; the runtime steps stay on 3bda).
  - Never build in an NFS worktree. The ~/workspace tree is shared with claude-box, and the NFS attribute cache can serve stale file content.
  - After a cross-host edit, grep the new text on 3bda before building.
- Source exec/lib-guard.sh.
  - Never launch while `ci_lease_busy 600` says busy.
  - Take `campaign_guard_acquire` before a campaign.
  - Re-check `ci_took_dut` between long runs.
  - Wait with at least 50400 s (14 h) when waiting for the lease.
  - The nightly CI takes the lease by cron at 03:30 UTC (observed launches up to about 03:50) and holds it until about 13:30 UTC, sometimes later. Long campaigns must end before about 02:30 UTC.
- Bill's marker /bill-has-instance-0,2 (memory 3bda-shared-with-bill.md): Bill may use socket 0 (cards 10/13/38/3b). Our half is socket 1: `taskset -c 72-143,216-287`, and `SYSTEM_CONFIG="--instance 1,2"` for fake-device tests.
- Whole-machine work (cells against serving, the host suite with serving down, the deb campaign, bench --update) only through the takeover rules.
  - `exec/bill-share.sh take` and `release` for the marker.
  - `rinzler_takeover_if_idle` after a journalctl traffic check; serving restored afterwards.
  - platformd 0.11 restarts a stopped rinzler@N unit within minutes unless the takeover path is used.
- Build recipe (build host per D11; inside the nix shell, from the worktree): `~/.nix-profile/bin/nix develop --accept-flake-config --command bash -c 'cmake -B gen --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= && ninja -C gen -j 64 runtron t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'`. This is CONF_VNNI and TARGETS_VNNI of exec/merge4737-20261008/build-test.sh. The preset cross-avx512 no longer exists.
  - Row-major build: that script's CONF_RM into a second worktree. It sets -DTRON_K_VNNI=OFF and -DBUILD_INGEST_MODELS=OFF and builds the 5 tests of TESTS_RM (no t_phase1_integration). Use it as is.
  - PR-1 adds a third configure: -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=ON (D2).
  - If nix refuses to evaluate because main added a file under nix/ that the worktree's index does not track, run `git add -A .` first.
- Tests: `env SYSTEM_CONFIG="--instance 1,2" ./gen/t_xxx --skip-benchmarks` from the worktree root, on our cpus with nice.
  - Kill-switch runs: the same with TRON_AMX_DISABLE=1 for t_llama_unit and t_amx_numerics. build-test.sh runs the kill switch on t_amx_numerics only; add t_llama_unit in your fork.
  - Require a fresh binary mtime and a BUILD EXIT line before reading test lines.
  - The forked chain writes `ok` to all.done only when: both builds are ok, every unit test binary passed, both kill-switch runs (t_llama_unit, t_amx_numerics) exited 0, the cabal test rc is 0 (PR-3; for the other PRs the step is skipped and recorded as skipped), the format checks are rc 0, and, for PR-3, the generated-plugin grep found the expected plugin files, equal and positive main-side and helper-side save_k counts, and zero save_k_helper. For PR-1 and PR-2 the grep expects the base save_k call form only and zero helper-side calls. (exec/merge4737-20261008/build-test.sh logs the kill-switch rc and the grep counts without enforcing them.)
- Formatting: clang-format 19 and fourmolu are in the nix shell (fourmolu only when a Haskell file changed), plus `git diff --check`. lefthook is missing on claude-box. So commit there with `-c core.hooksPath=/dev/null --no-verify` and run the checks yourself.

Chain per PR (fork exec/merge4737-20261008/build-test.sh + launch.sh and exec/sync4424b-20261007/chain.sh; results under exec/results/split-<date>-pr<N>/; log every step with an EXIT line and a .done marker):

| Step | PR-1 | PR-2 | PR-3 | PR-4 |
|---|---|---|---|---|
| A: VNNI build + 6 unit tests + kill-switch runs | yes, plus the AMX-off + option-on configure and build | yes (real AMX for t_amx_numerics) | yes | yes |
| A2: ingest cabal test + generated-plugin grep | no (the generator is untouched; recorded as skipped) | no | yes | no |
| B: row-major build + tests | yes | yes | yes | yes |
| F: clang-format, fourmolu, diff --check | yes | yes | yes | yes |
| C: host test suite (i4525-20260922/host-suite.sh) with serving down | yes | yes | yes | yes |
| D: smokes (sync4424-20261002/smoke.sh): A/A, kill switch, vs a main binary built from the merged main; CPU p1024, CPU p8192, FPGA p1024 | yes | yes | yes | yes |
| E: cells (sync4424-20261002/campaign.sh, qwen3-4b tp2 8 users, CPU attention, prompt 1024 and 8192, 3 reps, base = main binary) | yes | yes | yes + tp4 prompt 1024 | yes |
| W: whole-machine nightly-config campaign (pr4424ci-20261009) + bench --update cost rows | no | no | no | yes |

Pass criteria:

- Unit tests: every binary passes in both layouts (and in the AMX-off + option-on build for PR-1).
- Smokes, per cell (arms: new = this PR's head, new2 = its A/A run, newoff = new with TRON_AMX_DISABLE=1, base = the main binary built from the same merged main):
  - every cell: new vs new2 identical (256 of 256 tokens), or the cell is a finding;
  - CPU attention, prompt 1024: PR-1 to PR-3: new vs base first differs at generated token 52 (the #4444 divergence); PR-4: identical; newoff vs new identical for every PR;
  - CPU attention, prompt 8192: identical to base for every PR (measured for the PR-3 and PR-4 states on 2026-10-09; PR-1 and PR-2 are expected to match, a difference is a finding to report);
  - FPGA attention, prompt 1024: new vs base first differs at token 52 for every PR (measured for the PR-3 and PR-4 states; the difference comes from PR-1's reader); newoff vs new identical;
  - any difference not listed is a finding. These are expectations from the 2026-10-09 record, not guarantees for the new revisions; report what is measured.
- Host suite: the known failures are t_proxy_llama31 and t_proxy_lib (missing venv) and, with serving up, 6 heap_setup failures. Anything else is a finding.
- Cells: report TPS and TTFT with the band (the A/A spread) and a paired t-test. No claim without n >= 3.

### 5.4 What each PR can claim, and the cells that back it

- PR-1: option off, no change. Option on with the kill switch or without AMX: decode TPS vs the row-major dotter (expected about +4 to +5 % on qwen3-4b tp2 at CPU attention). Option on with AMX: a loss vs main's AMX kernel until PR-2 (expected -7 to -11 %). Measure the kill-switch arms on 3bda. An AMD-host number is Insufficient data unless jhan asks for a run on genoa96 or andoria.
- PR-2: decode TPS vs main (expected +6 to +10 % at tp2). TTFT at prompt 1024 slightly worse at tp4 (the per-row scatter store) until PR-3.
- PR-3: TTFT at prompt 1024, tp2 and tp4 (expected -40 to -90 ms vs main, -130 to -250 ms vs PR-2). TPS unchanged.
- PR-4: the whole-machine table (expected: llama-8b 32 users at prompt 4096 about +5 % TPS, qwen 8k software attention about +8 %, qwen FPGA attention within noise, llama-3.2-3b about -1.4 % = the kv_mul 3 open item, memory within 0.3 %). Token identity with main in the CPU cells (the 2026-10-09 record: qwen3-4b tp2, 1 user, 256 tokens, CPU attention at prompt 1024 and 8192 identical; FPGA attention at prompt 1024 differs at token 52).

All expectations are from old-base or whole-head data (2026-09-14/15 and 2026-10-09). The bodies carry only the new measurements, final head vs the latest main.

## 6. PR bodies

Rules (jhan's, from the project memory):

- Present tense, written as of the day. No change history, no review-round narration, no "before/after" the fold or the merge.
- Measurements keep provenance only (commit id + date). Only the final head vs the latest main. No previous-head comparator, no attribution subsection.
- A pending measurement is its own subsection: the question, the comparator, the cells, the verdict rule, the status, the table. Never a sentence inside another section.
- No clock times, no paths into the author's workspace, no comparison with another head's assertion counts in the Verification section. Keep dates, commit ids, build settings, pass/skip results, exact test counts.
- Every term defined at first use (a "Words used here" table as in the 4424 body). One claim per sentence. Numbers with units. Plain English, no idioms.
- The Short version and Background of each new PR are the executor's to write (D6, decided). Reuse sentences of the freshly fetched PR 4424 body where they hold for that PR; never copy a claim that does not hold for it (for PR-1 the AMX kernel and the shared block save, for PR-4 the old per-token decode scatter). The protected-section rule applies to PR 4424's own body only. Never reinstate text jhan has deleted from the live body.
- Mapping of the 4424 body's "The changes" bullets to the PRs: split-plan.md section 6. Open items by PR: genoa96 cost row, kv_mul 3/8 reader slowdown, benchmark-binary mismatch, issue #4444 (introduced by PR-1's reader; PR-4 restores identity in the measured CPU cells), widened test tolerance (all PR-1); cost rows refresh (PR-4); the D8 CI-coverage gap (every PR, under Verification).
- Each body ends with the stack map: the four PRs, their order, and the state of each (ready or draft).
- Post with `gh pr create --draft` (PR-2 to PR-4) or without --draft (PR-1), `--label "Skip benchmarks"`, `--assignee jhan-positron`, `--base <parent branch>`. Edit later with `gh api -X PATCH` after re-fetching the live body. jhan edits bodies on GitHub. Never overwrite an edit you have not re-fetched.

## 7. Reporting and checkpoints

Keep split-status.md in this folder up to date after every step: what was done, what was verified with the exact result lines, what is left, the decisions assumed. Checkpoint messages to jhan at: the end of step 0; the PR-1 chain results before opening PR-1; each PR opened; any 3bda step that fails; any classifier refusal. The classifier refuses `systemctl stop rinzler@*`, `pkill` of other people's processes and some ssh launches. Hand jhan the exact command as a `! <command>` line instead of retrying.

Stop and ask (do not guess) when:

- origin/jhan-amx-vnniK has moved past 0a5334ccb6;
- a patch of section 2 does not apply even with --3way and the conflict is in code (not in comments);
- a unit test fails in a way the pass criteria do not list;
- the step 4.3 comparison shows an unexplained code difference;
- a decision of section 0 is needed and no default fits.

## 8. Traps (each cost a session before)

- NFS:
  - never build on 3bda inside ~/workspace (shared with claude-box);
  - never edit a script a 3bda process is running (bash re-reads a running script by byte offset);
  - after a cross-host edit, verify the content on 3bda before building;
  - `git fetch <nfs worktree> <sha>` can fail right after a cross-host ref change; use `git cat-file -e` on the shared store.
- git:
  - version 2.34 on claude-box: no `merge-tree --write-tree`, no `cherry-pick -q`;
  - `git rebase` strips commit-message lines that start with `#`; use merges, and if you must rebase, compare messages and restore with `--cleanup=whitespace`;
  - never `git worktree prune` the shared repository from claude-box;
  - after any amend, check `git branch --show-current`: an amend once went to a detached HEAD and was lost;
  - git rerere is active in ~/workspace/tron (rr-cache) and will auto-resolve a conflict identical to the PR-2 kv_cache.hpp one;
  - lefthook is missing on claude-box: commit with --no-verify and run the checks by hand.
- Build:
  - nix is absent on claude-box today;
  - the lcheck mirror holds generated headers from 2026-09-24; if main changed a generated header, a false error is possible, so compare error sets before and after your change;
  - on 3bda the system g++ lacks __bf16; always use the nix shell;
  - a clean textual merge can still fail to compile when main added a caller of a function whose signature the PR changed; grep main's added lines for save_k, k_head_fn, populate and apply_page_tok.
- Machine:
  - the nightly leaves rinzler@N units running after a failed run, and bill-watch.sh kills our runtron and bench when a unit is active or the lease is busy;
  - the host suite with serving up fails 6 heap_setup tests (environmental);
  - platformd 0.11 restarts stopped units;
  - a campaign and a pre-check must not wait for the same lease event; create the hand-off marker before waiting.
- Tests:
  - never fill bf16 test rows with 0x7f80 or higher patterns (they are NaN);
  - a book with logical_slot_count() == 0 exists in tests; never touch page K state before a token is relevant;
  - main's split-vs-unsplit tolerance in t_llama_unit is marginal and PR-1 widens it; keep that change early in PR-1's history so every later commit passes.
- Bodies:
  - the PR 4424 body is edited by jhan on GitHub;
  - the REST PATCH stores LF line endings; compare after normalizing;
  - never reinstate text jhan deleted.

## 9. Do not

- Do not push to jhan-amx-vnniK. Do not force-push anything. Do not close PR 4424. Do not push the probe branches.
- Do not add "Run CI" (D9). Do not remove "Skip benchmarks". Do not mark PR-2 to PR-4 ready for review.
- Do not post to Slack or GitHub comments in jhan's name. Do not @-mention or name people in bodies (roles and review links only).
- Do not apply the standing "protected-section wording proposal" of PR 4424 anywhere. It is jhan's to apply.
- Do not create files or folders at the top level of ~/workspace. Worktrees and scratch go under ~/workspace/ai-runs/, results under ~/workspace/intel-AMX/exec/results/.
