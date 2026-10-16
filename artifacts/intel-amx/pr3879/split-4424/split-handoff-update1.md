# split-handoff.md, Update 1: response to split-handoff-review.md

Written 2026-10-10 04:3x UTC by Claude. split-handoff.md itself is not edited here, because it is open in an editor (vim, since 04:02 UTC). This file holds the verdict on each of codex's ten points, the replacement text for the handoff, and the script fixes already applied in handoff-material/. Fold the replacement blocks into split-handoff.md once the editor is closed, or ask me to.

## Short version

All ten points were checked against the sources. Nine are accepted (two of them with a narrower scope than codex stated). One, the build host, is a real instruction of jhan's that the handoff did not know about, and it needs a decision because the host is not reachable from this container today. Two scripts in handoff-material/ are fixed. The stack, the order and the construction recipe do not change.

## 1. Verdict per point

| # | Codex's point | Verdict | Evidence |
|---|---|---|---|
| 1 | [P1] Resolve D8 before the test-bearing commits; option (a) must enable both flags; the AMX identity test still skips without AMX hardware | accepted | AGENTS.md:20-26: "Before committing it, verify that a required CI suite collects and executes it ... Agents may not decide that an exception applies." With TRON_AMX_DISPATCH off, both AMX test files compile a placeholder case that only calls SUCCEED (t_amx_dispatch_dtype.cpp:303-306, t_amx_numerics.cpp:342-346). The Nix test build passes neither flag (nix/cmake-tron-test-build.nix:80-93). t_amx_numerics returns early without AMX hardware (:208-211). |
| 2 | [P1] The matrix accepts a cell on "0 lines matching error:" and ignores the compiler's exit status | accepted, fixed | handoff-material/probe/matrix.sh ran `$S $T $F $W > log 2>&1` and never read `$?`. A failed launch (no uvx, no mirror, timeout) printed no "error:" line and counted as clean. Fixed in both matrix scripts and in pr1check/run.sh (section 3). |
| 3 | [P2] The forked chain script must enforce the kill-switch and generated-code checks | accepted | exec/merge4737-20261008/build-test.sh:42-43 logs the kill-switch rc into tests-m4737.txt but the all.done condition at :74-75 reads only the two build markers, the cabal rc and the format rc. The plugin grep (:44-56) prints counts and checks nothing. |
| 4 | [P2] Separate the CPU and FPGA smoke expectations | accepted | exec/results/merge4737-precheck/smoke/fpga-p1024/smoke.txt: new (PR-4 state) vs base differs at generated token 52 under FPGA attention; the handoff's pass criteria (5.3) said "identity is expected for PR-4" without the cell qualifier that 5.4 gives. |
| 5 | [P2] The kill-switch sentence PR-1 adds is never removed, and the PR-3 patch lacks the ninth file | accepted | Step 1.3 adds "No AMX visit can occur for a VNNI slot" to Note [K VNNI storage]; the PR-2 patch (made from probe trees that never had the sentence) leaves it; after PR-2 the dense AMX path is open for VNNI slots, so the sentence is false. `git diff --stat 4d3a042225 ba69cb513e` = 9 files; the shipped S patch (76a0160b72..3c56db9a95) = 8 files, without amx_attn_iface.hpp. A patch against the PR-2 tree is now shipped (section 3). |
| 6 | [P2] Compare the final tree after the cost-row commit | accepted | Step 4.3 compared before step 4.5's `bin/slice bench --update` commit changed config/test-benchmarks.json. |
| 7 | [P2] pr1check/run.sh hard-codes the old scratchpad | accepted, fixed | run.sh:4-5 set S=<scratchpad> and W=$S/pr1tree; W from the environment could not override it. Fixed (section 3). |
| 8 | [P2] Build on sw-dev-01, not on delphi-3bda | accepted as jhan's instruction; needs a decision (D11) | ~/.codex/AGENTS.md:26-28 (jhan's instructions to codex): "Use general Linux server sw-dev-01 if you need to build tron." The Claude instructions name only delphi-3bda ("for real tests"). From this container `ssh sw-dev-01` stops with "REMOTE HOST IDENTIFICATION HAS CHANGED" (a host-key change; not bypassed). The notebook (claude_20260827-20260828 migration handoff) records nix and tron-main on sw-dev-01 under /var/tmp/jhan/persist and not on agentsrv. Every chain of this project since 2026-09 built on delphi-3bda in /var/tmp/jhan worktrees on our half; whether sw-dev-01 still has nix today is Insufficient data. |
| 9 | [P2] Run `bin/slice route` before the hardware chain | accepted | AGENTS.md:78-88: "Before substantial tests or serving work, run `bin/slice route` and obey its verdict ... Never bypass a blocked/shared Dice route with raw FPGA commands". The smoke script launches runtron directly (exec/sync4424-20261002/smoke.sh:42). `bin/slice route` exists in the tree (only `-h` as an option). |
| 10 | [P2] One rule for the protected sections | accepted | D6 said "placeholders"; section 6 said "copy the snapshot verbatim and do not rewrite". The snapshot's Short version claims the AMX kernel and the shared block save, which PR-1 does not contain. |

Scope notes on two acceptances:

- Point 1: the gap is inherited (PR 3879 shipped the same placeholders and the same skip; PR 4424 has them today). The policy still binds every new commit, so the handoff's "write the gap into the body" is not enough. The executor needs jhan's D8 answer before step 1.2, not before PR-1 opens.
- Point 8: jhan's instruction stands. The obstacles are practical (host key, nix state, moving build output to 3bda), not a reason to ignore it. D11 below.

## 2. Replacement text for split-handoff.md

Apply each block to the named place.

### 2.1 Decision sheet

Replace the D6 row with:

| D6 | Who writes the Short version and Background of each PR body? | jhan. The executor leaves the two sections as placeholders (`<!-- protected: jhan writes this section -->`) and writes everything from "Words used here" on. The executor also writes, in split-status.md, a draft of each protected section from the freshly fetched PR 4424 body (`gh api repos/positron-ai/tron/pulls/4424 --jq .body`, never the snapshot), with the sentences that no longer hold for that PR struck through and the reason. Nothing from the snapshot goes into a body. |

Replace the D8 row with:

| D8 | Required CI coverage of the option-on paths. The policy (AGENTS.md:20-26) requires, before a test is committed, that a required CI suite executes it; agents may not decide that an exception applies. Options: (a) add `-DTRON_K_VNNI=ON -DTRON_AMX_DISPATCH=ON` to the Nix test build (nix/cmake-tron-test-build.nix): the dispatch fakes and the layout tests then run in the PR suite, the row-major layout keeps its coverage in the coverage preset and the deb-smoke lane, and the AMX identity case still returns early on runners without AMX; (b) a second Nix test configuration with both flags; (c) an explicit exception, approved by jhan in writing, recorded in split-status.md and in each body | a prerequisite of step 1.2 (the first test-bearing commit), not of opening PR-1. The executor asks jhan, with this table, and does not commit tests before an answer. The executor also records where the real AMX identity case executes (delphi-3bda by hand; the manual-dispatch CMake lane on an Intel runner), and says so in the PR-2 body. |

Add a row:

| D11 | Build host. jhan's instruction to codex (~/.codex/AGENTS.md:26-28) designates sw-dev-01 for tron builds and delphi-3bda for real tests. Today: `ssh sw-dev-01` from this container fails on a changed host key; nix on sw-dev-01 is Insufficient data (it was there on 2026-08-28 under /var/tmp/jhan/persist); every chain of this project since September built on delphi-3bda in /var/tmp/jhan on our half. | ask jhan. If sw-dev-01: jhan confirms the host-key change and the executor builds there in a worktree under /var/tmp/jhan, then copies the test binaries, runtron and the ingest plugin bundle it needs to /var/tmp/jhan/<name> on delphi-3bda with rsync, recording the source commit and the configure line in split-status.md; the runtime steps stay on 3bda under the guards. If delphi-3bda: as section 5.3 says, our half, nice, under the lease and guard, and the build time (about 10 min per configuration) is reported as machine use. |

### 2.2 Step 1.3, the kill-switch sentence

Replace the last bullet of step 1.3 with: "kv_cache.hpp, the kill-switch paragraph of Note [K VNNI storage]: add 'Until the VNNI AMX kernel is merged, TRON_AMX_DISABLE=1 changes no score and no visit path for 128-dimension heads. No AMX visit can occur for a VNNI slot.' This is PR-1-only text. Step 2.3 removes it."

Add to step 1.3 a closing line: "List of PR-1-only comment text, all removed or reverted by PR-2: the two sentences above; the 'Until the VNNI AMX kernel is merged' wording of h/tron/kernels/k_vnni.hpp:3-5; 'the layout-specific reader' at :43-44; the Note [K VNNI storage] consumer items 2 and 3 and the 'Why' paragraph in their PR-1 wording; the README sentence 'The option is OFF by default in every other build.' stays until PR-4."

### 2.3 Step 2

Add as step 2.3 (renumber the rest): "Restore the comments PR-1 reworded: the kill-switch paragraph of Note [K VNNI storage] goes back to the head's wording (0a5334ccb6, kv_cache.hpp around line 707: the kill switch keeps the layout; with TRON_AMX_DISABLE=1 a TRON_K_VNNI binary runs the AVX-512 reader), h/tron/kernels/k_vnni.hpp:3-5 and :43-44 go back to the head's wording, and the consumer items name the dense AMX path again. Grep the tree for 'No AMX visit can occur' and 'Until the VNNI AMX kernel': both must be absent."

### 2.4 Step 3

Replace step 3.2's first sentence with: "`git apply --3way handoff-material/ref/S-diff-4d3a..ba69.patch` (the S content against the PR-2 tree: 9 files, +678/-75, including the Note [QK orientation] restoration in amx_attn_iface.hpp). The older S-diff-76a0..3c56.patch (8 files, against PR-1) stays only as a reference." Replace "`git diff ba69cb513e -- <the 8 S files>`" with "`git diff ba69cb513e -- <the 9 files of the patch>`".

### 2.5 Step 4

Replace step 4.3's first sentence with: "Comparison (the stack invariant), run twice: once after step 4.2 and again after the last commit of step 4.5 (the cost-row refresh), on the exact commit that will be pushed." Add to the allowed differences: "(3) the measured cost rows of config/test-benchmarks.json, reported as measurement-record changes with the bench run's date and host, separate from source changes." Remove "the kill-switch sentences of step 1.3" from the allowed differences (PR-2 reverts them, so the final tree must not carry them).

Add to step 4.5, before the bench command: "Run `bin/slice route` on delphi-3bda first and obey its verdict (section 5.3)."

### 2.6 Section 5.1

Replace the sentence "Every cell must print 0." with: "A cell passes only when the compiler's exit status is 0 and the log has no 'error:' line. matrix.sh now records both (`rc=N errors=M` per cell) and exits 1 unless every expected cell is present with rc=0 and errors=0. Check the script's exit status, not only the summary. Prove the counter is live once per tree in both directions: an untracked file with a deliberate syntax error must give errors=1, and a run with the compiler launcher made unavailable (for example PATH without uvx) must give rc!=0 and a MATRIX FAILED verdict."

### 2.7 Section 5.3

Add as the first rule: "Route: before the hardware chain, run `bin/slice route` from the worktree on delphi-3bda and obey the verdict (AGENTS.md:78-88). For `local-legacy` the chain's direct runtron launches are the normal commands. For `local-shared-dice` the smoke and cell scripts must submit through the shared Dice service; never bypass a blocked or shared route with raw FPGA commands or DICE_DISABLE=1. A free CI lease is not a route decision."

Replace the build-recipe bullet's first sentence with: "Build host per D11. The recipe below is the configure and build line in either case."

Add under "Tests": "The forked chain writes `ok` to all.done only when: both builds are ok, every unit test binary passed, both kill-switch runs (t_llama_unit, t_amx_numerics) exited 0, the cabal test rc is 0 (PR-3; for the other PRs the step is skipped and recorded as skipped), the format checks are rc 0, and, for PR-3, the generated-plugin grep found the expected plugin files, equal and positive main-side and helper-side save_k counts, and zero save_k_helper. For PR-1 and PR-2 the grep expects one save_k call form (the base form) and zero helper-side calls."

Replace the "Smokes" pass criterion with:

- Smokes, per cell (the arms: new = this PR's head, new2 = its A/A run, newoff = new with TRON_AMX_DISABLE=1, base = the main binary built from the same merged main):
  - every cell: new vs new2 identical (256 of 256 tokens), or the cell is a finding;
  - CPU attention, prompt 1024: PR-1 to PR-3: new vs base first differs at generated token 52 (the #4444 divergence); PR-4: identical; newoff vs new identical for every PR;
  - CPU attention, prompt 8192: identical to base for every PR (measured for the PR-3 and PR-4 states on 2026-10-09; PR-1 and PR-2 are expected to match, a difference is a finding to report, not a failure);
  - FPGA attention, prompt 1024: new vs base first differs at token 52 for every PR (measured for the PR-3 and PR-4 states; the difference comes from PR-1's reader); newoff vs new identical;
  - any difference not listed is a finding. These are expectations from the 2026-10-09 record, not guarantees for the new revisions; report what is measured.

### 2.8 Section 6

Replace the "Protected sections (D6)" bullet with: "Protected sections (D6): '## Short version', '### Background' and, for PR-2, '### Remove the Score transpose by saving VNNI layout and transposed K', for PR-3, '### Use shared block in saving K' are placeholders in the body: `<!-- protected: jhan writes this section -->`. The executor's draft of each, from the freshly fetched PR 4424 body with the sentences that no longer hold struck through and explained, goes into split-status.md for jhan, never into the body. Never reinstate text jhan has deleted from the live body."

## 3. Script fixes applied in handoff-material/ (2026-10-10 04:2x UTC)

- probe/matrix.sh and probe-pr2/matrix.sh: each cell records the compiler's exit status (`rc=N`) and the error count; a 900 s timeout per cell; the script sorts the summary and exits 0 only when all expected cells (EXPECTED, default 22) are present with rc=0 and errors=0, else prints MATRIX FAILED and exits 1. The verdict logic was dry-tested on a fake summary with one rc=42 line (flagged).
- pr1check/run.sh: takes W=<worktree> (required) and O=<output dir> (default out/ next to the script), finds lcheck-vnni.sh at ../probe/, writes commit.txt with the checked commit, and ends with the same verdict rule (EXPECTED default 38).
- ref/S-diff-4d3a..ba69.patch: new, the S content against the PR-2 tree (9 files, +678/-75). ref/S-diff-76a0..3c56.patch stays as the reference against PR-1.

## 4. For jhan

- D8: answer before the executor's first test-bearing commit (option a, b, or an explicit written exception).
- D11: build host (sw-dev-01 with the host-key confirmation, or delphi-3bda as practised).
- D6: confirm the placeholder rule of 2.1.
- Known: split-handoff.md is open in vim; the blocks above are not folded in yet.

## Update 2 (2026-10-10 05:4x UTC): response to the second review in split-handoff-review.md

Short version: the second review's three findings and two consistency edits all hold on the sources and are folded into split-handoff.md. The first review's ten points are closed by its own disposition table.

| # | Finding | Verdict | Evidence |
|---|---|---|---|
| 1 | [P1] D8 (a) and (b) leave the AMX identity case unexecuted in any required suite | accepted | The required test jobs of gcp-nix.yml run on runners labeled fpga, test, avx512 (lines 464, 555, 622); no AMX label exists; t_amx_numerics returns early without AMX (:208-211). The D8 row now says that (a) and (b) also need a required job on an AMX runner (Insufficient data whether one can be added) or jhan's explicit written exception for that one case, and that choosing a compile configuration does not approve it. |
| 2 | [P2] deb-smoke does not cover the option-off layout; cpp-coverage is not per PR | accepted | deb-smoke.yml:41 runs the package script with --apt-only, which does apt-get update and exits (bin/ci/test/deb-package-jammy-runtime.sh:42-46); cpp-coverage.yml triggers on workflow_dispatch only. The D8 row now says option (a) gives up required per-PR coverage of the option-off build, and (b) keeps both layouts at the cost of a second build. |
| 3 | [P2] The D8 change has no place in the construction steps or the allowed differences | accepted | New step 1.4 (the D8 commit, after the empty-diff check of step 1.2); the allowed final differences and the section 3 invariant gain item (4), the approved CI change. |
| edit 1 | A2 row of the chain table contradicted the completion rule | accepted | The row now says PR-1: no, recorded as skipped (the generator is untouched); PR-3 only. |
| edit 2 | Step 4.2 restored a README paragraph that B-preset.diff already carries | accepted | handoff-material/ref/B-preset.diff lines 14-32 replace "The option is OFF by default in every other build." with the deb sentences; step 4.2 now checks the paragraph appears once. |

Also noted from the review's verification: the three repaired matrix scripts returned exit 0 on success controls and exit 1 on failed-launch and compiler-error controls; the nine-file PR-3 patch applied on 4d3a042225 reproduces the tree of ba69cb513e exactly.
