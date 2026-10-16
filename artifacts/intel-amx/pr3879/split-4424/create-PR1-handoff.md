# Handoff: create and test PR-1 of the PR 4424 split

Written 2026-10-10 06:5x UTC by Claude for the agent that creates PR-1. This file is the PR-1 part of split-handoff.md (same folder), with every decision resolved. Read split-handoff.md only for the picture of the whole stack; this file is complete for PR-1. Companion material: handoff-material/ (patches, scripts, logs), split-plan.md (the analysis), new-PRs.html (what the four PRs are).

## Short version

PR-1 is the first of four stacked PRs that replace PR 4424. It adds the VNNI K layout for the K cache of 128-dimension heads, the typed owner and views, the per-row store, the AVX-512 reader, the FPGA staging gather, the CMake option (off in every preset) and the tests. Its tree already exists as commit 76a0160b72 on the scratch branch jhan-split-probe and passes a syntax check. Your job: rebuild that tree as topical commits on a new branch from main, add one commit of PR-1-only edits, merge main, verify on delphi-3bda, write the body, and open the PR ready for review.

## Words used here

- PR 4424: positron-ai/tron (tron = the inference program) pull request "VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save". Draft, branch jhan-amx-vnniK, head 0a5334ccb6, merge base with main be0d5565b3. It stays open until the last PR of the stack is open. PR = pull request.
- K cache: the stored key vectors of past tokens. KV page: a 64-token block of the K and V caches. Plane: the packed K storage of one page and one KV head (16 KiB). kv_mul: the number of query heads that share one KV head. Dotter: the row-major QK (query-key score) loop that scores K today. bf16: the 16-bit brain floating-point format.
- AMX: Intel Advanced Matrix Extensions, the tile instruction set. AVX-512: the 512-bit vector instruction set. VNNI layout: the pair-interleaved operand layout the AMX tile multiply reads as its right operand. The option: the CMake switch TRON_K_VNNI. AMX dispatch: the CMake switch TRON_AMX_DISPATCH that compiles the AMX attention kernels (on main since PR 3879). Kill switch: the environment variable TRON_AMX_DISABLE=1, which turns the AMX kernels off at run time.
- The reader: PR-1's AVX-512 loop (k_vnni::qk_group) that scores K stored in the VNNI layout. Per-row store: each token's K row written on its own into the layout (4 AVX-512 scatters).
- FPGA: the attention accelerator card. FPGA staging: the gather that copies K rows into the buffers the FPGA reads. Hardware attention: scores computed on the FPGA. Software attention: scores computed on the CPU.
- Concern letters of the plan: L = layout, storage, views, per-row store; R = the reader; G = FPGA staging; B = build and CI files. PR-1 = L+R+G+B. A (AMX kernel on the plane), S (shared block save) and T (row-major tail block + hardware-attention policy) are the later PRs.
- CI: continuous integration, the automatic build-and-test runs on GitHub. Required CI: the workflow every PR must pass (gcp-nix.yml). Legacy CMake lane: .github/workflows/cmake-single-platform.yml, run by hand.
- delphi-3bda: the Intel Granite Rapids test machine, shared with the nightly CI and with Bill (a colleague). "Our half" = socket 1 (cpus 72-143 and 216-287). The lease: the file the nightly CI writes to claim the machine. rinzler: the production server; rinzler@N: its systemd units; platformd: the service manager that supervises them. runtron: tron's command-line tool.
- claude-box: the development container this handoff was written in (host claude-agentsrv). It has no nix (the package manager that provides tron's build toolchain), so it cannot build tron. It can run the syntax check.
- lcheck: a clang 19 syntax-only compile of one translation unit with the product flags (~/workspace/ai-runs/lcheck/lcheck.sh). gen / gen-amxoff: its two flag sets (AMX dispatch on / off). Syntax matrix: lcheck over 22 cells (gen or gen-amxoff, option off or on, 5 test files, plus amx_attn.cpp in gen).
- Reference tree: ~/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K, the worktree of jhan-amx-vnniK at 0a5334ccb6. Read it. Do not change it.
- lefthook: the git hook runner the repo configures (absent on claude-box). NFS: the network file system that shares ~/workspace between claude-box and delphi-3bda.
- Smoke: a short token-identity run of one user, greedy (temperature 0), compared token by token. A/A: two runs of the same binary. Paired t-test: the test that decides whether two arms differ beyond run-to-run noise. Cell: one model, parallelism, user count, prompt length and attention mode. tp2: tensor parallelism over 2 engines. TPS: decode tokens per second per user. TTFT: time to first token.
- Issue #4444: the token divergence of a VNNI binary against the row-major binary, and the kill-switch rollback contract. Issue #4865: the CI change that will make the required CI compile both switches (tracked by jhan with the CI owner). The classifier: the permission checker of Claude Code's auto mode; it refuses some commands (section 7).

## 0. Decisions (all resolved by jhan on 2026-10-10)

| Id | Decision |
|---|---|
| D1 | Four PRs. PR-1 does not contain the AMX kernel on the plane. |
| D2 | PR-1 drops the CMake requirement "TRON_K_VNNI requires TRON_AMX_DISPATCH": the FATAL_ERROR block src/tron/CMakeLists.txt:236-238 goes (keep the outer `if(TRON_K_VNNI)` at 235 and the definition at 239), and the clause "(requires TRON_AMX_DISPATCH; ...)" leaves the option help in CMakeLists.txt:47. Both compile definitions stay (the tron target and tron_model_compile_config). |
| D3 | The temporary gate is one clause in apply_page_tok only (already in the tree). |
| D5 | The cells of section 5.5. |
| D6 | You write the whole PR-1 body, including the Short version and the Background. The four PRs are new PRs; the protected-section rule applies to PR 4424's own body only. You may reuse sentences of the freshly fetched PR 4424 body (`gh api repos/positron-ai/tron/pulls/4424 --jq .body`, never a snapshot) where they hold for PR-1, and must not carry over claims that do not hold for it (the AMX kernel on the plane, the shared block save, the tail block). |
| D7 | Tag the current head locally before anything else: `git -C ~/workspace/tron tag pr4424-pre-split-0a5334ccb6 0a5334ccb6`. Do not push the tag. PR 4424 stays open. |
| D8 | Option (c): jhan approves that PR-1's tests run by hand on delphi-3bda and in the legacy CMake lane until the CI change of issue #4865 lands. You state that gap and cite #4865 in the body under Verification. You do not touch nix/cmake-tron-test-build.nix. The AMX-hardware identity case of t_amx_numerics is not part of PR-1 (it comes with the AMX kernel PR). |
| D9 | No "Run CI" label on any PR. PR-1 opens ready for review, so the required CI runs on it without a label. |
| D11 | Build and test on delphi-3bda, in an isolated worktree under /var/tmp/jhan on our half, under the lease and the guard (section 5.3). Report the build time (about 10 min per configuration) as machine use. sw-dev-01 is not used. |

## 1. Context

- Why a split: jhan judges PR 4424 too big for manual review (4,054 added lines). The analysis (split-plan.md) labeled every hunk by concern and found four features with one-directional dependencies; codex and a planning panel agreed. PR-1 is the base of the stack: everything else needs the layout, the typed views and the reader.
- What PR-1 is on its own: a storage layout with its software reader and the FPGA gather, and no AMX instruction. With the option off (every preset) nothing changes. With the option on, every page of a VNNI slot takes the reader, even on an AMX host, because the dense AMX path is gated off for VNNI slots until the AMX kernel PR lands. On an AMX host that is a decode loss of about 7 to 11 % against main's AMX kernel (the kill-switch run on 2026-09-14 is the proxy); on a host without AMX it is a gain of about 4 to 5 % over the row-major dotter. The body says this plainly.
- What the next PR does: PR-2 (the AMX QK kernel that reads the plane as its B operand, about 280 lines) removes PR-1's temporary gate and the PR-1-only comment sentences. You do not build PR-2; you only keep PR-1's temporary text identifiable (section 4, step 3).
- The CI gap you inherit: the required CI builds with both switches off, so PR-1's layout tests under `#ifdef TRON_K_VNNI` are compiled out there and the VNNI branches of t_llama_unit take the row-major path. The legacy CMake lane compiles the option on but runs by hand. D8 covers it; issue #4865 tracks the fix.

## 2. Inputs and where they are

| Name | Commit | What it is | Status |
|---|---|---|---|
| base | be0d5565b3 | the merge base of PR 4424 with main (the PR 4557 merge commit) | on main |
| PR-1 tree | 76a0160b72 | branch jhan-split-probe in ~/workspace/ai-runs/tron-split-probe (repository ~/workspace/tron); = the tested commit ba69cb513e minus the AMX kernel minus the shared block save | 22-cell syntax matrix at 0 errors, verified twice; never built or run |
| head of PR 4424 | 0a5334ccb6 | for comparison and for the fetched body | on origin/jhan-amx-vnniK |
| main | origin/main (a0056c1ecc on 2026-10-09; moves daily) | 165 commits past base at that time; t/t_llama_unit.cpp gained 122 lines there | fetch before you start |

Material in handoff-material/:

- ref/PR1-diff-base..76a0.patch: the PR-1 content as one patch (23 files, +1846/-160 lines). You build the branch from the tree of 76a0160b72, not from this patch; the patch is the reference and the review aid.
- probe/matrix.sh (`W=<worktree> bash matrix.sh <label>`): the 22-cell syntax matrix; records the compiler exit status per cell and exits 1 on any failed or missing cell. probe/lcheck-vnni.sh: lcheck with -DTRON_K_VNNI. pr1check/run.sh (`W=<worktree> bash run.sh`): a 38-cell variant with more translation units. Logs of the earlier runs are next to them.
- probe/A_*.py and S_*.py: the edit scripts that produced 76a0160b72 (reference only).
- pr4424-body-20261009.md: the PR 4424 body as of 2026-10-09, for orientation only; the body you reuse sentences from is the fetched one.
- Reusable delphi-3bda scripts under ~/workspace/intel-AMX/exec/ (fork them into exec/pr1-<date>/; never edit a script a 3bda process is running):
  - merge4737-20261008/build-test.sh + launch.sh: VNNI build, the unit tests, a kill-switch run of t_amx_numerics, format checks, the row-major build;
  - sync4424-20261002/smoke.sh: token identity, arms by binary;
  - sync4424-20261002/campaign.sh: runtron cells, base vs head;
  - i4525-20260922/host-suite.sh: the host test suite;
  - sync4424b-20261007/chain.sh: a full chain with serving down and up, host suite, smokes, cells;
  - lib-guard.sh: the machine guards; bill-share.sh: take and release of Bill's marker.
- Rules of the machine: ~/workspace/notebook/handoffs/check-CI.md ("Rules for our own work on delphi-3bda", lines 258-270) and the memory file ~/.claude/projects/-home-jhan-workspace-intel-AMX/memory/3bda-shared-with-bill.md (the marker rule).

## 3. Target

- Branch: jhan-vnnik-1-layout, from main. Worktree: ~/workspace/ai-runs/tron-split-pr1.
- Title: "VNNI K: the layout, its AVX-512 reader and the FPGA staging path".
- Content: the tree of 76a0160b72, plus the PR-1-only commit of step 3, merged with origin/main. 23 files; +1846/-160 lines by git numstat before the main merge, of which tests +965/-90 (t_k_vnni_layout +474, t_llama_unit +469/-78, t_amx_dispatch_dtype +16/-7, three gof test lambdas +5/-5, t/CMakeLists.txt +1) and code +881/-70 (h/tron/tensor/k_vnni.hpp +335, h/tron/models/kv_cache.hpp +235/-38, h/tron/kernels/k_vnni.hpp +128, h/tron/models/self_attention.hpp +53/-9, gof.hpp + gof.cpp + full.hpp +39/-12, model.hpp +23/-1, kv_cache_fwd.hpp +16/-3, attn_stats.hpp +4/-3, amx_attn_iface.hpp +1, CMake option + CI flag + README + cost rows +47/-5).
- Opens as: ready for review, base main, label "Skip benchmarks", assignee jhan-positron, no "Run CI" label.
- Invariants (check after every step):
  - the tree compiles and its tests pass with the option off, with the option on, and with the option on and AMX dispatch off (D2);
  - no symbol of the later PRs is present (section 5.2);
  - "temporary until" is present in exactly two comments (kv_cache.hpp and t_amx_dispatch_dtype.cpp);
  - every PR-1-only sentence of step 3 is listed in split-status.md so PR-2 can revert it.

## 4. Steps

### Step 0: preparation (claude-box, about 30 min)

1. Read this file, then split-plan.md sections 1-3 and 7 (why the stack, what PR-1 is), AGENTS.md of tron (the PR CI policy and the test policy), check-CI.md's rules, and the marker rule.
2. `git -C ~/workspace/tron fetch origin main jhan-amx-vnniK`. Confirm origin/jhan-amx-vnniK is 0a5334ccb6. If not, stop and report (the PR-1 tree assumes that head).
3. Confirm the PR-1 tree: `git -C ~/workspace/ai-runs/tron-split-probe log --oneline -1 jhan-split-probe` shows 76a0160b72 and `git -C ~/workspace/ai-runs/tron-split-probe status --porcelain` is empty. (That worktree is checked out on jhan-split-probe-pr2 at 4d3a042225; leave it.)
4. Confirm tooling: `uvx --from ziglang==0.14.0 python -m ziglang clang --version` prints clang 19.1.7; `ssh -o ConnectTimeout=8 delphi-3bda uptime` works; `ls /nix` is empty (no builds here).
5. D7: `git -C ~/workspace/tron tag pr4424-pre-split-0a5334ccb6 0a5334ccb6`.
6. Create ~/workspace/intel-AMX/exec/pr1-$(date +%Y%m%d)/ for your scripts and split-status.md in this folder (section 7).

### Step 1: the branch and the topical commits (claude-box)

1. `git -C ~/workspace/tron worktree add ~/workspace/ai-runs/tron-split-pr1 -b jhan-vnnik-1-layout be0d5565b3`.
2. Bring in the tree of 76a0160b72 as six topical commits, by `git checkout 76a0160b72 -- <files>` then commit, in this order:
   - (a) "tensor: the K VNNI layout, owner and views": h/tron/tensor/k_vnni.hpp, h/tron/tensor/kv_cache_fwd.hpp;
   - (b) "kv_cache: store K of 128-dimension heads in the VNNI layout": h/tron/models/kv_cache.hpp, h/tron/models/model.hpp (the per-row store), CMakeLists.txt (the option), src/tron/CMakeLists.txt (the two compile definitions);
   - (c) "kernels: the AVX-512 reader of the VNNI K layout": h/tron/kernels/k_vnni.hpp, h/tron/models/self_attention.hpp (the software loop and the temporary gate), h/tron/models/attn_stats.hpp, h/tron/kernels/amx_attn_iface.hpp (one diagram line);
   - (d) "gof: the FPGA staging path reads K rows through the layout": h/tron/gof.hpp, src/tron/gof.cpp, h/tron/scheduler/full.hpp, t/t_gof_dma.cpp, t/t_gof_staging_leaks.cpp, t/t_phase1_integration.cpp;
   - (e) "tests: t_k_vnni_layout and the t_llama_unit cases": t/t_k_vnni_layout.cpp, t/t_llama_unit.cpp, t/t_amx_dispatch_dtype.cpp, t/CMakeLists.txt, config/test-benchmarks.json. The widened split-vs-unsplit tolerance of t_llama_unit is in this commit; it must be in place before any commit that a VNNI build would run against it;
   - (f) "ci: build and test the CMake lane with TRON_K_VNNI=ON": .github/workflows/cmake-single-platform.yml, README.ci.md.
   Commit with `git -c core.hooksPath=/dev/null commit --no-verify` (lefthook is absent here). Each commit message: a subject in the present tense and a short body saying what the commit adds; no history narration.
3. At the end: `git diff 76a0160b72` must be empty. Record the six commit ids in split-status.md.

### Step 2 (step 3 of the stack plan): the PR-1-only commit

One commit, "VNNI K: the layout needs no AMX dispatch", with these edits (line numbers are those of 76a0160b72; re-find each by its text):

- D2: delete src/tron/CMakeLists.txt:236-238 (the `if(NOT TRON_AMX_DISPATCH)` / FATAL_ERROR / `endif()` block) and the three justification comment lines 232-234 ("The AMX ... QK kernel ... The option therefore requires TRON_AMX_DISPATCH."). Keep `target_compile_definitions(tron PUBLIC TRON_K_VNNI)` and the tron_model_compile_config INTERFACE definition. In CMakeLists.txt:47 drop "(requires TRON_AMX_DISPATCH; ...)" from the option help.
- h/tron/kernels/k_vnni.hpp:3-5: "It serves partial pages, hosts without AMX (...) and the AMX kill switch" becomes "Until the VNNI AMX kernel is merged it serves every page of a VNNI slot; after that, partial pages, hosts without AMX and the AMX kill switch".
- h/tron/kernels/k_vnni.hpp:43-44: "This reader is one of the two layout-specific readers allowed to take the plane address" becomes "This reader is the layout-specific reader allowed to take the plane address".
- h/tron/tensor/k_vnni.hpp:178-179: drop "and the AMX QK kernel reads the plane in 64-byte tile rows".
- t/t_llama_unit.cpp:429: drop "and the AMX tile rows".
- README.ci.md: the paragraph on TRON_K_VNNI must say "The option is OFF by default in every other build." and must not mention the deb preset (76a0160b72 already has that sentence at line 593; confirm).
- h/tron/models/kv_cache.hpp, the kill-switch paragraph of Note [K VNNI storage]: add "Until the VNNI AMX kernel is merged, TRON_AMX_DISABLE=1 changes no score and no visit path for 128-dimension heads. No AMX visit can occur for a VNNI slot."
- Record in split-status.md the list of PR-1-only text that PR-2 will revert: the two sentences just added; the "Until the VNNI AMX kernel is merged" wording of h/tron/kernels/k_vnni.hpp:3-5; "the layout-specific reader" at :43-44; the consumer items 2 and 3 and the "Why" paragraph of Note [K VNNI storage] in their PR-1 wording; the temporary gate in apply_page_tok and the `!k_vnni::layout_on<head_size>` clause in t_amx_dispatch_dtype.cpp.

### Step 3: merge main

`git merge --no-ff origin/main` (a merge, not a rebase: the repo convention for reviewed branches). Expect conflicts in t/t_llama_unit.cpp (main added 122 lines) and possibly h/tron/models/kv_cache.hpp. Keep main's new tests intact. After the merge, grep main's added lines for callers of functions whose signature PR-1 changes (page_info::k_head_fn gained a scratch argument; page::k() is constrained to row-major slots): `git diff be0d5565b3 origin/main | grep '^+' | grep -E 'k_head_fn|template k<|\.k\('`. A clean textual merge can still fail to compile for that reason.

### Step 4: checks on claude-box

1. Syntax matrix: `W=~/workspace/ai-runs/tron-split-pr1 bash handoff-material/probe/matrix.sh pr1` must end with "MATRIX OK: 22 cells". Check the script's exit status. Prove the counter once in both directions: an untracked file with a deliberate syntax error gives errors=1; a run with the compiler launcher unavailable (PATH without uvx) gives rc!=0 and MATRIX FAILED. Delete the probe file afterwards. Then the 38-cell variant: `W=... bash handoff-material/pr1check/run.sh`.
2. clang-format 19 on every changed C++ file: `uvx --from clang-format==19.1.7 clang-format --dry-run --Werror <files>`; `git diff --check origin/main HEAD -- ':!lib/**'`; no `<cassert>` in the diff.
3. Grep list (section 5.2): no symbol of the later PRs; "temporary until" exactly twice.

### Step 5: build and test on delphi-3bda

Section 5.3 has the rules and the recipe. The chain, forked from exec/merge4737-20261008/build-test.sh + launch.sh and exec/sync4424b-20261007/chain.sh, with results under exec/results/pr1-<date>/ and an EXIT line plus a .done marker per step:

| Step | What | Where |
|---|---|---|
| A | VNNI build (option on, AMX dispatch on) + the 6 unit tests + kill-switch runs of t_llama_unit and t_amx_numerics | our half, next to serving |
| A3 | the D2 configuration: option on, AMX dispatch off; build the same targets and run the 5 tests that exist without dispatch (t_amx_numerics and t_amx_dispatch_dtype are placeholders there; record them as such) | our half |
| B | row-major build (option off) + its 5 tests | our half |
| F | clang-format and `git diff --check` in the nix shell (no Haskell file changes in PR-1, fourmolu not needed) | our half |
| A0 | a main binary built from the merged main (the same commit you merged), runtron.main-<date> | our half |
| C | the host test suite with serving down (i4525-20260922/host-suite.sh) | whole machine, takeover rules |
| D | smokes (sync4424-20261002/smoke.sh): arms base (main binary), new (PR-1, option on), new2 (A/A), newoff (new with TRON_AMX_DISABLE=1); cells CPU prompt 1024, CPU prompt 8192, FPGA prompt 1024; qwen3-4b tp2, 1 user, 256 tokens | whole machine |
| E | cells (sync4424-20261002/campaign.sh): qwen3-4b tp2 8 users, CPU attention, prompt 1024 and 8192, 3 reps, arms base / new / newoff | whole machine |

The chain writes `ok` to all.done only when: the three builds are ok, every unit test binary passed, both kill-switch runs exited 0, the format checks are rc 0. The reference script logs the kill-switch rc without enforcing it and runs the kill switch on t_amx_numerics only; your fork enforces both runs.

### Step 6: the body and the PR

Write the body (section 6). Open with `gh pr create --base main --title "VNNI K: the layout, its AVX-512 reader and the FPGA staging path" --body-file <file> --label "Skip benchmarks" --assignee jhan-positron` (no --draft). Push the branch first with a plain `git push -u origin jhan-vnnik-1-layout`. Do not add "Run CI". Record the PR number and head in split-status.md and tell jhan.

### Step 7: after opening

Watch the required CI on the PR (it runs because the PR is ready for review). Reply to review comments only when jhan asks. When jhan says main moved and the PR should take it: `git merge --no-ff origin/main`, re-run steps 4 and 5 A/B, update the body's Verification provenance (commit id + date), push.

## 5. Checks in detail

### 5.1 Syntax matrix (claude-box)

Cells: trees gen (AMX dispatch on) and gen-amxoff (off), option off and on, files t/t_llama_unit.cpp, t/t_k_vnni_layout.cpp, t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp, t/heterogeneous_scheduler_compile.cpp, plus src/tron/kernels/amx_attn.cpp in gen. A cell passes only when the compiler's exit status is 0 and the log has no "error:" line. Limits: syntax and template instantiation only; no link, no generated model translation units, no runtime, no CMake configure. The lcheck mirror holds generated headers from 2026-09-24; if main changed a generated header, a false error is possible, so compare error sets before and after your change.

### 5.2 Symbols that must be absent from PR-1

- AMX kernel (A): qk_vnni_128x4, pack_q_rows_128x4, Q_ROWS_TILE_4, K_EVEN_PANEL_TILE_5, K_ODD_PANEL_TILE_6.
- Shared block save (S): store_block, transpose_16x16_epi32, set_k_block, k_store_window, k_store_cut_units, k_store_shared, k_join_timeout_s, FULL_BLOCK_0XFFFF, LANES_16, "Shared block save", save_k with worker_ix or n_workers.
- Tail block (T): note_k_row_saved, note_k_block_saved, k_vnni_blocks, k_rows_saved_, convert_pending_k_blocks, pending_k_blocks_, block_to_vnni, block_to_rows, row_major_row, k_row_if_row_major, k_forget_row, k_layout_dense, BLOCKS_PER_PAGE_MASK_0XF, "Row-major tail block", "Row-major blocks under hardware attention", cached_operation_uses_hw inside save_k.
- Present: "temporary until" in exactly two comments. main itself uses worker_ix in threading.hpp and plugins/llama.hpp and "main helpers" in several files; those are not S code.

### 5.3 delphi-3bda rules and the build recipe

- Route: before the hardware steps, run `bin/slice route` from the worktree on delphi-3bda and obey the verdict (AGENTS.md:78-88). For `local-legacy` the direct runtron launches of the scripts are the normal commands. For `local-shared-dice` the smoke and cell scripts must submit through the shared Dice service; never bypass a blocked or shared route with raw FPGA commands or DICE_DISABLE=1. A free CI lease is not a route decision.
- Work in an isolated worktree under /var/tmp/jhan/<name> on 3bda's local disk. Never build inside ~/workspace on 3bda (NFS, shared with claude-box; the attribute cache can serve stale content). After a cross-host edit, grep the new text on 3bda before building. `git fetch <nfs worktree> <sha>` can fail right after a cross-host ref change; use `git cat-file -e` on the shared store.
- Source exec/lib-guard.sh. Never launch while `ci_lease_busy 600` says busy. Take `campaign_guard_acquire` before a campaign. Re-check `ci_took_dut` between long runs. Wait with at least 50400 s (14 h) when waiting for the lease. The nightly CI takes the lease by cron at 03:30 UTC (launches observed up to about 03:50) and holds it until about 13:30 UTC, sometimes later. Long work must end before about 02:30 UTC.
- Bill's marker /bill-has-instance-0,2: Bill may use socket 0 (cards 10/13/38/3b). Our half is socket 1: `taskset -c 72-143,216-287`, and `SYSTEM_CONFIG="--instance 1,2"` for the fake-device tests. Whole-machine steps (C, D, E) only through the takeover rules: `exec/bill-share.sh take` and `release` for the marker; `rinzler_takeover_if_idle` after a journalctl traffic check; serving restored afterwards. platformd 0.11 restarts a stopped rinzler@N unit within minutes unless the takeover path is used.
- Build recipe (inside the nix shell, from the worktree): `~/.nix-profile/bin/nix develop --accept-flake-config --command bash -c 'cmake -B gen --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS= && ninja -C gen -j 64 runtron t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'` (CONF_VNNI and TARGETS_VNNI of exec/merge4737-20261008/build-test.sh; the preset cross-avx512 no longer exists). Row-major build: that script's CONF_RM into a second worktree (option off, BUILD_INGEST_MODELS off, 5 tests). The D2 configuration: a third worktree with -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=ON. If nix refuses to evaluate because main added a file under nix/ that the worktree's index does not track, run `git add -A .` first. The system g++ on 3bda lacks __bf16; always use the nix shell.
- Tests: `env SYSTEM_CONFIG="--instance 1,2" ./gen/t_xxx --skip-benchmarks` from the worktree root, on our cpus with nice. Kill-switch runs: the same with TRON_AMX_DISABLE=1 for t_llama_unit and t_amx_numerics. Require a fresh binary mtime and a BUILD EXIT line before reading test lines.
- Formatting on 3bda: clang-format 19 in the nix shell, `git diff --check`.

### 5.4 Pass criteria

- Unit tests: every binary passes in the VNNI build, the row-major build and the D2 build (where t_amx_numerics and t_amx_dispatch_dtype are placeholders, recorded as such).
- Smokes, per cell (arms: new = PR-1 with the option on, new2 = its A/A run, newoff = new with TRON_AMX_DISABLE=1, base = the main binary from the same merged main):
  - every cell: new vs new2 identical (256 of 256 tokens), or the cell is a finding;
  - newoff vs new identical in every cell (in PR-1 the kill switch changes no score for 128-dimension heads, because no AMX visit can occur for a VNNI slot);
  - CPU attention, prompt 1024: new vs base is expected to first differ at generated token 52 (the #4444 divergence, measured for the later states of this branch on 2026-10-09); report the measured token;
  - CPU attention, prompt 8192: identical to base was measured for the later states; a difference is a finding to report;
  - FPGA attention, prompt 1024: new vs base is expected to differ at token 52; report the measured token;
  - any difference not listed is a finding. These are expectations from records of other states of the branch, not guarantees; report what is measured.
- Host suite: the known failures are t_proxy_llama31 and t_proxy_lib (missing venv) and, with serving up, 6 heap_setup failures. Anything else is a finding.
- Cells: report TPS and TTFT with the band (the A/A spread) and a paired t-test. No claim without n >= 3.

### 5.5 What PR-1 can claim, and the cells that back it

- Option off (every preset): no behaviour change. Back it with the row-major build's tests and with base vs new under the option off if you build that arm (optional).
- Option on, AMX host, AMX on (arm new): a loss against main's AMX kernel is expected (about -7 to -11 % decode TPS at prompt 1024 to 8192, from the 2026-09-14 kill-switch proxy). The body states the measured number and says that PR-2 removes it.
- Option on, kill switch (arm newoff vs base with TRON_AMX_DISABLE=1 on both, add that arm if the machine time allows): the reader against the row-major dotter, expected about +4 to +5 % decode TPS. An AMD-host number is Insufficient data unless jhan asks for a run on genoa96 or andoria.
- TTFT at prompt 1024 and 8192: report; no claim.

## 6. The body of PR-1

Rules (jhan's):

- Present tense, written as of the day. No change history, no review-round narration, no "before/after".
- Measurements keep provenance only (commit id + date). Only the final head against the latest main (the main you merged). No previous-head comparator, no attribution subsection.
- A pending measurement is its own subsection: the question, the comparator, the cells, the verdict rule, the status, the table. Never a sentence inside another section.
- No clock times, no paths into the author's workspace, no comparison with another head's assertion counts in the Verification section. Keep dates, commit ids, build settings, pass/skip results, exact test counts.
- Every term defined at first use (a "Words used here" table as in the 4424 body). One claim per sentence. Numbers with units. Plain English, no idioms. No names of people (roles and links only).

Sections, in this order:

1. "## Short version": three sentences. What PR-1 stores (the K cache of 128-dimension heads in the VNNI layout, typed owner and views, no raw pointer leaves the cache), who reads it in this PR (the AVX-512 reader on the CPU, the FPGA staging gather), and the state of the option (off in every preset; the AMX kernel on the plane, the shared block save and the row-major tail block follow in the next three PRs of the stack).
2. "### Background": why the layout exists (the AMX tile multiply takes a row-major matrix only as its left operand; storing K pair-interleaved lets the kernel of the next PR compute S = Q K^T without the register transpose). Reuse the fetched 4424 Background sentences where they hold.
3. "## Words used here": the table.
4. "## The changes": by file, mechanism level (the reader must see job -> what is measured). Take the PR-1 items of the fetched 4424 body's "The changes" (the tensor header without store_block and the tail-block operations; the kernels header; kv_cache_fwd.hpp; the kv_cache.hpp items on Note [K VNNI storage], kv_block::k, page::k(), page::k_packed, set_k_row / get_k_row, the whole-page copy, fill_random; model.hpp: the per-row store; self_attention.hpp: the software loop with qk_group and the temporary gate; the FPGA staging bullet; CMake option, CI flag, README; the tests), reworded to PR-1's truth. State the temporary gate and the PR-1-only comments plainly, as "until the AMX kernel PR".
5. "## Measurements": the cells of step 5 E, final head vs the merged main, with the band and the paired t. Then one subsection for the loss on AMX hosts with the option on, and one for the reader against the dotter (kill switch), each with its provenance. If a run is still pending when you post, it is its own subsection in the pending form.
6. "## Verification": the three builds and their test counts; the kill-switch runs; the host suite; the token-identity table (the three smoke cells); the syntax matrix; then the subsection "### CI coverage": the required CI builds with both switches off, so the cases under `#ifdef TRON_K_VNNI` and the VNNI branches of t_llama_unit do not execute there; they run in the legacy CMake lane (by hand) and on the Granite Rapids test machine; jhan approved proceeding on that basis; the CI change is tracked in #4865.
7. "## Open items": the kv_mul 3 and 8 reader slowdown (llama-3.2-3b -1.4 % and qwen-3-30b-a3b in the 4424 measurements; the AMX kernel of the next PR applies to kv_mul 4 only); issue #4444 (the reader's add order differs from the dotter's, a token can flip at a near tie; the measured first difference; the kill-switch rollback contract: a row-major build is the rollback artifact); the widened split-vs-unsplit tolerance of t_llama_unit (the mechanism and the numbers, for the test's author to review); the genoa96 cost row (missing; the CI check passes without it); the benchmark-binary mismatch of the legacy workflow (inherited from PR 3879); the performance of PR-1 alone on AMX hosts with the option on (removed by the next PR).
8. "## The stack": the four PRs, their order, what each adds, and the state of each (PR-1 ready for review; PR-2 to PR-4 to follow as drafts, each based on the previous one). Say that PR 4424 stays open as the reference until the last PR is open.
9. The attribution line: "🤖 Generated with [Claude Code](https://claude.com/claude-code)".

Post with `gh pr create` and the file. Edit later only after re-fetching the live body (jhan edits bodies on GitHub; the REST PATCH stores LF line endings, so compare after normalizing). Never reinstate text jhan deleted.

## 7. Reporting and checkpoints

Keep split-status.md in this folder up to date after every step: what was done, what was verified with the exact result lines, what is left, the decisions assumed. Checkpoints to jhan: after step 0; after step 4 (the matrix and the checks pass); after step 5 with the chain results, before opening the PR; when the PR is open (number and head); on any 3bda step that fails; on any classifier refusal (the classifier refuses `systemctl stop rinzler@*`, `pkill` of other people's processes and some ssh launches: hand jhan the exact command as a `! <command>` line instead of retrying).

Stop and ask (do not guess) when:

- origin/jhan-amx-vnniK has moved past 0a5334ccb6;
- the main merge conflicts in code (not in comments or tests) and the resolution is not obvious from main's new callers;
- a unit test fails in a way the pass criteria do not list;
- the syntax matrix or the build fails after the main merge for a reason you cannot fix in a few lines;
- `bin/slice route` returns a verdict the scripts cannot follow.

## 8. Traps (each cost a session before)

- git on claude-box is 2.34 (no `merge-tree --write-tree`, no `cherry-pick -q`). `git rebase` strips commit-message lines that start with `#`; use merges. Never `git worktree prune` the shared repository from claude-box. After any amend, check `git branch --show-current` (an amend once went to a detached HEAD and was lost). git rerere is active in ~/workspace/tron and auto-resolves conflicts it has seen. lefthook is missing on claude-box: commit with --no-verify and run the checks yourself.
- NFS: never edit a script a 3bda process is running (bash re-reads a running script by byte offset); verify cross-host edits on 3bda before building.
- Machine: the nightly leaves rinzler@N units running after a failed run, and bill-watch.sh kills our runtron and bench when a unit is active or the lease is busy; the host suite with serving up fails 6 heap_setup tests (environmental); a campaign and a pre-check must not wait for the same lease event (create the hand-off marker before waiting).
- Tests: never fill bf16 test rows with 0x7f80 or higher patterns (NaN); a book with logical_slot_count() == 0 exists in tests (never touch page K state before a token is relevant); the widened tolerance must precede any VNNI run of t_llama_unit in the history.
- Smoke results: the campaign summary's TPS is decode-only; the runtron log's "average tok/s" is a different metric.

## 9. Do not

- Do not push to jhan-amx-vnniK. Do not force-push anything. Do not close PR 4424. Do not push the probe branches or the tag.
- Do not add "Run CI". Do not remove "Skip benchmarks".
- Do not change nix/cmake-tron-test-build.nix (D8 is option c; #4865 tracks the CI change).
- Do not post to Slack or GitHub comments in jhan's name. Do not name people in the body.
- Do not create files or folders at the top level of ~/workspace. Worktrees go under ~/workspace/ai-runs/, results under ~/workspace/intel-AMX/exec/results/.
- Do not start PR-2. Its construction is in split-handoff.md step 2; it begins only after jhan has seen PR-1 open.
