## Update 1 (2026-10-10, after the codex review in split-plan-codex.md)

Short version: codex supports the four-PR stack and the merge order, and raises five corrections and three smaller ones. Four of the five are accepted after verification against the source and change the text of sections 2, 3, 4 and 5. The fifth (the dependency wording) is accepted as a rewording. Of the smaller ones, the size and CMake-option points are accepted and the build-location point is refused with a reason. The recommendation (section 3) stands.

### U1.1 Point 1, the PR-4 invariant: accepted, text corrected

Codex: "block VNNI iff its 16 bits are set" is false. Verified at the head: a page keeps two bit sets per storage slot, the saved-row bits (k_rows_saved_, one per page offset) and the converted-block bits (k_vnni_blocks_, one per 16-token block) [h/tron/models/kv_cache.hpp:683-686, 2484-2485]. note_k_row_saved returns true when the block's 16 rows are saved and the block is not converted yet; the main thread then queues the block, and the conversion runs at the forward end after the cooperative staging drained [kv_cache.hpp:2157-2183, model.hpp:1847]. So a complete block may stay row-major until the forward end.

Replacement for the "what a reviewer checks" line of PR-4 in section 3.1: the converted-block bit selects the layout; a converted block has all 16 rows saved; a complete block may remain row-major while its conversion is pending; the three writers of the bits (save_k, clear, copy) and the readers (dense gate, software loop, staging) all read the converted-block bit. The existing t_llama_unit case that checks the state before and after the conversion stays with PR-4.

### U1.2 Point 2, required CI coverage: accepted, new section 5.1

Codex: the cited workflow does not run on pull requests, so the enabled paths have no required CI coverage. Verified:

- The PR CI is gcp-nix.yml (triggers: push to main, pull_request). Its test build (nix/cmake-tron-test-build.nix:80-93) passes neither TRON_K_VNNI nor TRON_AMX_DISPATCH.
- cmake-single-platform.yml, the workflow that carries `-DTRON_K_VNNI=ON`, runs on workflow_dispatch only, and as the test gate of publish-deb.yml (workflow_call).
- AGENTS.md "Test policy": every committed test must run in a required CI suite; local execution is not sufficient.
- With the option off, t_k_vnni_layout's owner-level cases (index map, store_row / load_row, the reader on an owner) run, and its book-level cases are compiled out (#ifdef TRON_K_VNNI); t_llama_unit's VNNI branches take the row-major path; the VNNI case of t_amx_numerics returns early without AMX hardware [t/t_amx_numerics.cpp:208-211].

This gap is inherited: PR 4424 has it today, and PR 3879 had it for TRON_AMX_DISPATCH (memory: the legacy lane is the only one that compiles the option). The split does not create it, but each PR of the stack commits tests that the required CI does not execute with the option on. Section 5 gains the following subsection.

5.1 CI coverage of the enabled paths (new). Before PR-1 opens, one of these must be chosen (decision D8):

- (a) Add `-DTRON_K_VNNI=ON` to the Nix test build (nix/cmake-tron-test-build.nix). The whole PR suite then runs on the VNNI layout; the row-major layout keeps the coverage preset and the deb-smoke lane. The AMX kernel case of t_amx_numerics still runs only on an AMX runner (it returns early elsewhere).
- (b) Add a second Nix test configuration with the option on, next to the default one. Doubles the PR build time of the C++ suite.
- (c) Accept the gap as PR 3879 did, and state it in each PR body under Verification, with the manual-dispatch lane as the way to run the enabled suite. This needs the explicit approval the test policy requires.

Recommended: (a), asked of the CI owner before PR-1 opens, because the deb preset of PR-4 ships the layout on every host and the released configuration should be the tested one. For PR-2 the body must separate the fake-dispatch tests (run everywhere) from the numerical identity case (runs only on an AMX runner, t_amx_numerics returns early otherwise).

### U1.3 Point 3, the PR-2 tree: accepted, probe extended

Codex: the recommended order needs "PR-1 + A without S", which the probe did not build; `git apply --check` of the A diff on the PR-1 tree fails at h/tron/models/kv_cache.hpp:666 and h/tron/tensor/k_vnni.hpp:29. Verified: the same two failures reproduce here (comment context that S changed). The sentence "No hunk-level reconstruction by hand is needed" in section 4 was too strong; the repair is small but it is a hand edit.

The PR-2 tree now exists: commit 4d3a042225 on the scratch branch jhan-split-probe-pr2 (parent 76a0160b72, the PR-1 tree). Facts:

- Construction: `git apply --3way` of the A diff applied 8 of 9 files cleanly. One real conflict remained, the "Consumers of a VNNI slot" list of Note [K VNNI storage] in kv_cache.hpp. The second file of the plain `--check` failure, h/tron/tensor/k_vnni.hpp, merged by itself without S words.
- Hand repairs, both comment-only: (1) that consumers list (PR-1's item 1 on the per-row store kept, A's items 2 and 3 on qk_vnni_128x4 and qk_group taken); (2) the three S sentences of Note [QK orientation] in amx_attn_iface.hpp replaced by one sentence: "The price moves to the K store (a scatter of 64 dimension pairs per token, in save_k) and to the software reader k_vnni::qk_group for partial pages."
- The A diff's clean hunks already remove PR-1's temporary gate, the dispatch-test clause, the diagram line and the README sentence. Grep: 0 hits for "temporary until", store_block, set_k_block, Shared block save, work unit, Row-major tail block, k_vnni_blocks, note_k_row_saved; qk_vnni_128x4 present in 8 files, pack_q_rows_128x4 in 5.
- Size: PR-2 = 9 files, +277/-61 (added/removed lines by git numstat) against the PR-1 tree. What still separates PR-2 from the tested tree ba69cb513e is S plus the two comment wordings: 9 files, +678/-75.
- Syntax matrix on 4d3a042225: 22 of 22 cells at 0 errors (46 s wall). A deliberate syntax error in an untracked file gave 1 error through both checker variants, so the counter is live.
- Side effect to know: git rerere is active in the shared repo ~/workspace/tron and recorded the kv_cache.hpp resolution. An identical conflict in any worktree of that repo would auto-resolve to this text. Harmless for the probe.

The four candidate trees of the stack are therefore all real commits: PR-1 = 76a0160b72, PR-2 = 4d3a042225, PR-1 + S = 3c56db9a95 (the PR-3 content on PR-1, to be re-based on PR-2), PR-4 = the 4737 merge diff on top. Three of them (PR-1, PR-2, PR-1 + S) pass the syntax matrix; ba69cb513e and 9d5c7a389b were built and tested on delphi-3bda.

Section 4, step 2, becomes: apply the A diff with `git apply --3way`, repair the two comment hunks (Note [K VNNI storage] consumer list in kv_cache.hpp, the header comment of tensor/k_vnni.hpp) and the Note [QK orientation] paragraph of amx_attn_iface.hpp so they name only L, R, G and A, remove PR-1's temporary gate, run the syntax matrix, commit.

Section 4, step 4, the final comparison: compare the PR-4 tree against the original head 0a5334ccb6 merged with the same main, and list the allowed differences explicitly: (1) the CMake decoupling of D2 (src/tron/CMakeLists.txt FATAL_ERROR block and the option text in CMakeLists.txt:47), (2) the comment rewrites that PR-1 and PR-2 carry and PR-3 / PR-4 restore in their own wording, (3) nothing else. Every other difference must be explained or removed.

Codex also notes that the syntax-only probe does not validate the CMake configuration after the FATAL_ERROR is dropped. Correct; that is the configure step of section 5 (build with the option on and AMX dispatch off, PR-1 column).

### U1.4 Point 4, dependencies versus extraction order: accepted as a rewording

Codex: T needs the block-store primitive (store_block), consistent readers and writers, and the conversion timing, not helper-thread sharing; and the dense gate adapts the AMX path rather than being a prerequisite. Verified: block_to_vnni calls store_block [h/tron/tensor/k_vnni.hpp:508]; the unshared save branch stores through the same store_k_block and the row-bit loop follows it [h/tron/models/model.hpp:3418-3439]; without A, PR-1 already keeps VNNI pages out of the AMX dispatch (the temporary gate).

Section 1's graph keeps "T after A and S" as the order of this extraction (the T diff is the 4737 merge diff, and it lands on the tree that has S and A). The intrinsic dependency of T is on store_block (76 lines of S) and on R and G. A T-before-S order would need those 76 lines moved into T and the row-bit hook relocated into the per-row save_k (about 34 lines, per the seam check). No extra PR is proposed for this.

### U1.5 Point 5, token identity and performance claims: accepted, text limited to the measured cells

Codex: PR-4 does not establish general token identity with main under CPU attention, because converted blocks of a partial page are still scored by the packed reader (k_vnni::qk_group), whose fp32 add order differs from the row-major dotter. Verified at the head: in the software loop, a token of a converted block sets its bit in `live` and is scored by qk_group after the loop; only the rows of a row-major tail block go through the dotter [h/tron/models/self_attention.hpp:2025-2047]; the reader documents the different add order [h/tron/kernels/k_vnni.hpp:51-54].

The measured identity (exec/results/merge4737-precheck/smoke, 2026-10-09): ingested-qwen-3-4b-instruct-2507-tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens; CPU attention at prompt 1024 and prompt 8192: identical to main for 256 of 256 tokens; FPGA attention at prompt 1024: first difference at generated token 52 (as before PR 4737). Sections 3.1 and 3.2 now say "identical to main in those two cells", not "identical under CPU attention".

Codex also notes that the kill-switch arm on an AMX host does not establish a gain on hosts without AMX. Accepted: the table in section 2.3 is kill-switch data on delphi-3bda (Granite Rapids); the numbers for an AMD host are Insufficient data (a run of the PR-1 head against main on andoria or genoa96 would resolve it).

### U1.6 Smaller points

- Sizes: accepted. By `git diff --numstat be0d5565b3 76a0160b72`, the test sources of PR-1 are +965/-90, which is 52 % of the 1,846 added lines (section 3.1 said 57 % and mixed added with changed lines). t_llama_unit.cpp is +469/-78 (not "+547"), t_k_vnni_layout.cpp +474/-0. The code share of PR-1 is therefore about 880 added lines, not 790. The stack sum of 4,264 added lines stands.
- CMake option text: accepted. D2 also covers CMakeLists.txt:47, whose help text says "requires TRON_AMX_DISPATCH", and keeps both compile definitions (the tron target and tron_model_compile_config, src/tron/CMakeLists.txt:235-240 and 342-348).
- Build location: refused in part. Builds cannot run on claude-box (sw-dev-01) today: /nix is an empty directory and ~/.nix-profile/bin/nix does not exist (checked 2026-10-10 00:5x UTC), so no tron build is possible there, and the syntax matrix is the most claude-box can do. Builds therefore stay on delphi-3bda, on our half next to serving, under the CI lease and the campaign guard, as every chain of this project has done. The scheduling wording is accepted: section 5 now says "under the live CI lease, the campaign guard (campaign_guard_acquire) and the between-run checks (ci_took_dut)", not "after a nightly".

### U1.7 Changes to the decisions list

- D2 is extended to the option help text.
- New D8: the CI coverage choice of U1.2 (a / b / c). Recommended (a).

### U1.8 Corrections to the original text (from the plain-English and number check)

A check of the original text found 5 number errors and 78 style violations (41 undefined terms, 26 sentences with two claims or a semicolon, 4 numbers without a unit or meaning, 6 idioms, 1 Short version sentence with five claims). The number errors are corrected in place, on the same lines, so codex's line references still hold. The in-place edits:

- Short version: "57 % tests" is now "52 % tests".
- Section 3.1, PR-1: the per-file numbers were changed-line counts (added plus removed) labeled as added lines. They are now added/removed pairs by git numstat: tests +965/-90 (t_k_vnni_layout +474, t_llama_unit +469/-78, t_amx_dispatch_dtype +16/-7, three gof test lambdas +5/-5, t/CMakeLists.txt +1); code +881/-70 (tensor/k_vnni.hpp +335, kv_cache.hpp +235/-38, kernels/k_vnni.hpp +128, self_attention.hpp +53/-9, gof.hpp + gof.cpp + full.hpp +39/-12, model.hpp +23/-1, kv_cache_fwd.hpp +16/-3, attn_stats.hpp +4/-3, amx_attn_iface.hpp +1, CMake option + CI flag + README + cost rows +47/-5).
- Section 3.1, PR-3 and PR-4: the per-file numbers are now numstat pairs (PR-3: tensor +85/-6, kv_cache +35/-7, model +298/-36, common +29, TronCpp.hs +24/-3, LoopyTronSpec.hs +24/-2, t_k_vnni_layout +90, t_llama_unit +88/-18; PR-4 tests: t_k_vnni_layout +500/-2, t_llama_unit +140/-4, t_amx_dispatch_dtype +35/-5).
- Section 2.3 and table 3.2: the "est." labels are gone. Both columns are measured ratios of two kill-switch arms on delphi-3bda; the second column is a proxy for PR-1, and the table now says so. The PR-1 row of table 3.2 reads "-7 to -11 %", as section 3.1 does.
- Section 7: "1,050 of them tests" is now "965 of them tests".

Corrected stack sizes (added/removed lines by git numstat, actual trees):

| PR | Tree | Files | Added | Removed | Of which tests (added) |
|---|---|---|---|---|---|
| PR-1 L+R+G+B | 76a0160b72 vs be0d5565b3 | 23 | 1846 | 160 | 965 (52 %) |
| PR-2 A | 4d3a042225 vs 76a0160b72 | 9 | 277 | 61 | 98 (35 %) |
| PR-3 S | 3c56db9a95 vs 76a0160b72 | 8 | 673 | 72 | 178 (26 %) |
| PR-4 T | 9d5c7a389b vs ba69cb513e | 10 | 1459 | 113 | 675 (46 %) |
| deb preset | 0a5334ccb6 vs 9d5c7a389b | 2 | 7 | 2 | 0 |

The style violations of the original text are not edited in place (that would move codex's line references). The terms the check found undefined are defined here, so the document as a whole meets the first-use rule:

Words used here (supplement to the original list):

- Codex: the second, automated reviewer of this plan. tron: the inference program under test. runtron: its command-line tool. delphi-3bda: the Intel Granite Rapids test machine; "our half" is the half of it not reserved for Bill. genoa96: the AMD benchmark runner of the CI. sw-dev-01 / claude-box: the AMD development host this session runs on.
- FPGA: the accelerator card that runs attention for the pages it processes. Hardware attention: attention computed on the FPGA. FPGA staging: the gather that copies K rows into the buffers the FPGA reads; gof is the module that does it. Software attention: attention computed on the CPU.
- Prefill: the processing of the prompt. Decode: the token-by-token generation that follows. tp2 / tp4: tensor-parallel degree 2 / 4 (the number of FPGA cards one engine spans).
- The option: the CMake switch TRON_K_VNNI. Kill switch: TRON_AMX_DISABLE=1, the runtime switch that turns AMX off. Arm: one binary under test in a measurement; "vnnioff" is the VNNI binary with the kill switch, "off" the row-major binary with the kill switch, "base" the row-major binary with AMX.
- Dense page: a full 64-token page that the AMX path scores in one kernel call. VNNI plane: the VNNI-ordered K storage of one page and one KV head (16 KiB). B operand: the right-hand matrix of the AMX tile multiply. Dotter: the row-major dot-product reader of K. Intrinsics: compiler built-in functions that emit single AVX-512 or AMX instructions. VDPBF16PS: the AVX-512 bf16 dot-product instruction.
- Per-row store: each token's K row written on its own into the VNNI layout (4 AVX-512 scatters per row); "scatter store" names the same thing. Shared block save: the K store that writes one whole 16-token block at a time (a register transpose and whole-line stores) and shares the work with the idle main helpers (the helper threads of the main loop, idle during the K store). Join watchdog: the main thread's wait for the helpers aborts with an error after 120 s. Row-major tail block: the last, partly filled 16-token block of a page, kept in plain row order until its 16th row is saved. Converted block: a block whose rows have been transposed into the VNNI layout.
- save_k_helper form: the shared save as a separate helper function (the first version). Worker fold: the same save folded into save_k with a worker index (Ben's thread r4065141577, PR 4774).
- Note [...]: a named long comment block in a header. Row-major geometry: a head-size and kv_mul pair that keeps the row layout (every head size other than 128).
- TronCpp.hs: the Haskell code generator that emits each model's plugin, including the save_k calls. LoopyTronSpec.hs: its test suite. Ingest: the code-generator package. cabal: the Haskell build tool. fourmolu: the Haskell formatter.
- Cell (measurement): one model, parallelism, user count, prompt length and attention mode. Cell (syntax matrix): one compile configuration (tree x option x file). Smoke test: a short end-to-end run of one user, greedy (temperature 0, the top token at every step), compared token by token. A/A: two runs of the same binary, to measure run-to-run noise.
- Cost rows: the per-test timing rows of config/test-benchmarks.json that the CI's bench check reads. Benchmark-binary mismatch: the legacy CMake workflow benchmarks the runtron of its build job (options on) when the hand-over works, and a locally rebuilt runtron (options off) when it does not.
- Classifier / seam / refuter agents: sub-tasks of this analysis; classifiers labeled each hunk by concern, seam agents checked each boundary between two concerns, refuters tried to disprove each seam verdict.
- Issue #4500: the FPGA-attention decode loss caused by the per-token 64-line column access of the VNNI layout. Issue #4444: the token divergence against the row-major binary and the kill-switch rollback contract. p95: the 95th percentile.
- "Built tonight" / "checked tonight" in the original text means 2026-10-09 evening PDT (2026-10-10 00:xx UTC).

A clean second version of the whole plan, with the style fixes applied in the text, is a separate step once the decisions D1 to D8 are made.
