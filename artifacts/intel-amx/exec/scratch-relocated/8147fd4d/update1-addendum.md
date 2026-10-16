
## Update 1 addendum (planner round 2, 2026-10-10 00:4x UTC)

Short version: Update 1 was re-checked against the source, the probe worktree and the measurement records, and every checked fact holds. This addendum adds four facts that change section 5 and the PR bodies (the PR-2 tree residue check, the "Run CI" label for draft PRs, the precedent for the AMX-only numerics case, the token-identity cells) and corrects one host name. The recommendation and the merge order do not change.

### U1A.1 The PR-2 tree, re-checked (U1.3)

- The probe worktree is on the branch jhan-split-probe-pr2 at 4d3a042225 (parent 76a0160b72, the PR-1 tree). `git diff --numstat 76a0160b72 4d3a042225` gives 9 files, +277/-61 lines. The matrix summary lists 22 cells, each with 0 errors [scratchpad probe-pr2/out/pr2-r1/summary.txt].
- No temporary gate remains. A grep for "temporary until" and for `!k_vnni::layout_on<operation_head_size>` in self_attention.hpp, and for `layout_on<head_size>` in t_amx_dispatch_dtype.cpp, returns nothing.
- No S or T symbol remains. A grep over h/, src/, t/ and ingest/ for store_block, set_k_block, k_store_window, note_k_row_saved, note_k_block_saved, k_vnni_blocks, k_layout_dense, block_to_vnni, row_major_row, k_row_if_row_major, convert_pending_k_blocks, FULL_BLOCK_0XFFFF, LANES_16 and transpose_16x16 finds only main's own worker_ix uses in threading.hpp and plugins/llama.hpp, which are not S code.
- PR-2 against the tested tree ba69cb513e differs by 9 files, +75/-678 lines: the S code, plus the comment wordings of amx_attn_iface.hpp (8 lines), kv_cache.hpp, tensor/k_vnni.hpp and t_llama_unit.cpp.
- The comment-only differences between PR-1 and PR-2 are in four files, not two: tensor/k_vnni.hpp (two hunks, lines 29-37 and 117-121, "the two layout-specific score kernels"), kv_cache.hpp (the Why paragraph of Note [K VNNI storage], consumer items 2 and 3, the page::k_packed comment), amx_attn_iface.hpp (the Note [QK orientation] paragraph, 3 lines in the first-commit wording), and README.ci.md (the t_amx_numerics sentence restored). None of them is code.

### U1A.2 Draft PRs and the Nix suite (adds to section 5.1 and to the decisions)

- gcp-nix.yml is the pull-request workflow (triggers: pull_request opened / synchronize / reopened / ready_for_review, merge_group, push to main). Its Note [Draft PR Filtering and Label Override] says that draft PRs run lint, machinery and fresh-plan checks only, and that the label "Run CI" enables the product pipeline. The build and test jobs carry that condition [.github/workflows/gcp-nix.yml:5, 189-191, 315-317, 403-405].
- AGENTS.md keeps PR-2, PR-3 and PR-4 as drafts until their parent merges. So each descendant needs the label "Run CI", or its build and tests do not run in CI at all. PR 4424 is in that state today: its recorded check runs list Build Tron, Test host and Test as skipped (the A-off refutation, from the check-runs API).
- New decision D9: label every draft PR of the stack "Run CI" when it is opened. Recommended: yes. It costs runner time on each push to a draft; without it only PR-1 is tested by CI before its merge.
- Which checks branch protection requires today is Insufficient data. The 2026-09-11 reading (build, lint, test, test-fpga, test-host, ci-machinery-tests) predates the cutover to gcp-nix.yml. `gh api repos/positron-ai/tron/branches/main/protection` would resolve it.

### U1A.3 The AMX-only numerics case of PR-2 (codex point 2, second half)

- The new case of t_amx_numerics warns and returns when amx_attn_h128g4::available() is false [t/t_amx_numerics.cpp:208-211]. That is the pattern of the file's existing QK and PV cases. Main merged those cases with PR 3879 [memory amx-ci-coverage-facts: t_amx_numerics.cpp:145-148 and 189-192 at that time].
- The PR-2 body therefore says two things. The fake-dispatch cases (t_amx_dispatch_dtype) run on every runner. The identity case executes AMX only on an Intel runner (Granite Rapids) and on delphi-3bda, and warns elsewhere.
- Whether that is an approved exception to the test policy or a gap carried over from PR 3879 is jhan's call. It is part of D8.

### U1A.4 Token-identity records, for the PR bodies (U1.5)

The record is exec/results/merge4737-precheck/smoke (ingested-qwen-3-4b-instruct-2507-tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens). The arms: base = main be0d5565b3; head = 45e6bb266d, the PR-3 state (it differs from ba69cb513e by comment lines only); new = 9d5c7a389b, the PR-4 state; newoff = new with TRON_AMX_DISABLE=1.

- CPU attention, prompt 1024: head vs base differ at generated token 52 of 256. new vs base: identical for 256 of 256 tokens. newoff vs new: identical for 256 of 256.
- CPU attention, prompt 8192: head, new and base are all identical, 256 of 256.
- FPGA attention, prompt 1024: head vs base differ at token 52. new vs base differ at token 52. new vs head: identical.

Meaning for the bodies: the divergence at token 52 under CPU attention at prompt 1024 (#4444) is present in the PR-1 to PR-3 state and absent in the PR-4 state, in that cell. The kill switch of the PR-4 state changed no token in that cell. T changes no FPGA-attention token (new vs head identical), so the FPGA-attention divergence against main at token 52 comes from PR-1's reader. These are the three measured cells. The bodies make no wider claim.

### U1A.5 Host-name correction (U1.6 and the supplement of U1.8)

- This session's container runs on the host claude-agentsrv, not on sw-dev-01. The notebook records the container's moves: alpha, then sw-dev-01, then agentsrv on 2026-08-27 [notebook artifacts/dev-machines/README.md:4].
- In this container /nix is an empty directory and ~/.nix-profile/bin/nix does not exist (checked 2026-10-10 00:4x UTC). So no tron build runs here. The memory note of 2026-09-30 ("nix is back on claude-box") does not hold for this container today.
- Whether sw-dev-01 itself has nix today is Insufficient data: ssh from this container to sw-dev-01 is refused (the host key changed).
- The conclusion of U1.6 stands: builds and tests stay on delphi-3bda, in an isolated worktree under /var/tmp/jhan, under the guard. The definition in U1.8 should read: "claude-box: the development container this session runs in, on the host claude-agentsrv; sw-dev-01: its previous host".

### U1A.6 What does not change

The recommendation (the four-PR stack, merged PR-1, PR-2, PR-3, PR-4), the construction method with the PR-2 hand repairs of U1.3, section 5 with the new 5.1, and decisions D1 to D8 stand as Update 1 states them. D9 is added above.
