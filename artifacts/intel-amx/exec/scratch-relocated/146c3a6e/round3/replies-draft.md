# Draft replies for the open PR 5015 threads (COMMIT = the round-3 commit sha, filled at post time)

Worktree with the change: /home/jhan/workspace/ai-runs/tron-glimmer-amx (uncommitted diff = round3.patch in this folder).
Line numbers below are from the worktree after the patch and must be re-checked before posting.

## 4308387058 (wade-code-review, t/t_amx_dispatch_dtype.cpp, CI coverage) - jhan left no comment
Wade-code-review: Two of the three asks are in COMMIT; the third is the CI-configuration change that issue #3997 already tracks.

- Skips are reported as skips. The QK and PV cases of `t_amx_numerics` use Catch2 `SKIP(...)` instead of `WARN(...); return;`. On a host without AMX, or under the kill switch, the summary reads `test cases: 4 | 2 passed | 2 skipped` instead of `4 passed`. The exit code stays 0 because the two other cases run (Catch2 returns 4 only when every case is skipped). Verified on delphi-3bda with `TRON_AMX_DISABLE=1`: KILLSWITCH_LINE.
- The build warning is gone. The fakes and the probe of `t_amx_dispatch_dtype` sit inside `#ifdef TRON_AMX_DISPATCH` now, so the build without the option compiles only the SUCCEED fallback case.
- Running the 16-head cases in required CI needs `-DTRON_AMX_DISPATCH=ON` in the cmake_args of `nix/cmake-tron-test-build.nix` (:79-101), the required nix build. That one line adds the kernel translation unit to libtron (`src/tron/CMakeLists.txt:219-223`). On a runner with AMX it then routes the dense full pages of every bf16 attention with head size 128 and kv_mul 4 or 16 through the kernels, in every test of that lane, including the model tests the same cmake_args require (`-DTRON_REQUIRE_ALL_MODEL_TESTS=ON`). Which runner the lane lands on and what its model tests then compare against is the lane owner's call. Issue #3997 (open) records this gap and the CI options for it, and the TODO at `src/tron/CMakeLists.txt:217-218` points at it, so I propose the change in that issue's PR rather than in this kernel PR. For this head the 16-head cases ran on delphi-3bda: DISPATCH_LINE and NUMERICS_LINE (Verification table of the description). The 16-head dispatch section is in that count: removing its second round took the dispatch assertions from 5,756 to 3,694.

## 4308387067 (cpp-coding-guide, lane masks) - jhan: "This is too nit." (resolved)
cpp-coding-guide: Withdrawn, no change.

## 4308443056 (PR review, "2 sections") - jhan left no comment
PR review: Updated the description. The kill-switch row now says 2 test cases (the QK and PV precision checks) skipped with "AMX unavailable on this host". One deviation from the proposal: "4 pass" is not kept. COMMIT replaces the `WARN(...); return;` of both cases with Catch2 `SKIP(...)` (t/t_amx_numerics.cpp:318 and :331; the Wade-code-review thread on t_amx_dispatch_dtype.cpp asked for skips to be reported as skips), so Catch2 counts the two cases as skipped, not passed. The row reads "2 of 4 test cases pass and 2 are skipped, exit code 0". The kill-switch run at COMMIT on delphi-3bda (`TRON_AMX_DISABLE=1`) reported: KILLSWITCH_LINE.

## 4308443061 (PR review, query-fill comment) - jhan left no comment, thread outdated
PR review: a6b93f1f71 had already removed the "permutes or drops heads" claim. COMMIT rewords the sentence that replaced it to what the offset detects: a pack that starts at the wrong head, or steps through the heads with the wrong stride, fails the value check (t/t_amx_dispatch_dtype.cpp:QFILL_LINES).

## 4308443185 (ben-review, view aliases) - jhan: "Accept proposed, and use const_k_row_major_plane_view and const_v_vnni_plane_view"
ben-review: Applied in COMMIT with those two names. They are defined next to the shape constants (h/tron/kernels/amx_attn_iface.hpp:ALIAS_LINES) and used by the two declarations, the two definitions and the four explicit instantiations; the test spellings are unchanged. Object compare at this head (clang 19.1.7, -O3, merge base 6198824246): pack<4> and qk<4> are instruction-identical to main (509 and 204 instructions). pv<4> has the same 121 opcodes in the same order; the operands differ only in how the thread-local scratch is reached (TLS call prefixes and resolved scratch offsets) and in which registers the compiler picked for the tile-load and tile-store addresses.

## 4308443205 (ben-review, n_heads in the REQUIREs) - jhan left no comment
ben-review: Applied in COMMIT: `constexpr size_t group_heads = geometry.kv_mul();` right after the geometry (t/t_amx_dispatch_dtype.cpp:GH_LINE) and the three REQUIREs compare against it (:REQ_LINES). The parameter note now says only that `n_heads` is the query head count. The optional `facts.kv_mul` line outside the diff is unchanged.

## 4308443322 (Wade-code-review, check_qk/check_pv comments) - jhan left no comment
Wade-code-review: Applied in COMMIT, the two comments as proposed (t/t_amx_numerics.cpp:QK_CMT and :PV_CMT); the QK comment names the buffer `s_amx`, the helper's name for the kernel's `s`.

## 4308443327 (Wade-code-review, inline) - jhan: "reject, too niky." (resolved)
Wade-code-review: Withdrawn, no change.

## 4308443331 (Wade-code-review, duplicate 16-head round) - jhan left no comment
Wade-code-review: Applied in COMMIT: the 16-head section runs one round and its name drops the second-call clause (t/t_amx_dispatch_dtype.cpp:SEC_LINES). The description's Verification row is refreshed: DISPATCH_LINE.

## 4308443490 (cpp-coding-guide, query-fill literals) - jhan: "Accept proposed."
cpp-coding-guide: Applied in COMMIT as proposed: QUERY_BASE_1_0, HEAD_OFFSET_STEP_0_0625, VALUE_PERIOD_4 and VALUE_STEP_0_25 (t/t_amx_dispatch_dtype.cpp:QFILL_LINES).

## 4308443563 (positron-code-review, header narration) - jhan: "Issue# should not appear in source code. And this is too nit picking." (resolved)
positron-code-review: Withdrawn, no change. Noted for later reviews: no issue numbers in source code.

## 4308443569 (positron-code-review, reviewer credit) - jhan: "Accept proposed"
positron-code-review: Applied in COMMIT: the two lines are deleted, with no replacement sentence.

## 4308444165 (tron-code-review, KV_MUL_32) - jhan left no comment
tron-code-review: Applied in COMMIT: `KV_MUL_32` refusal row (t/t_amx_numerics.cpp:KV32_LINES) and the comment above it now says that no kernel is instantiated for any group above 16.

## 4308444171 (tron-code-review, "padding stays zero") - jhan left no comment, thread outdated
tron-code-review: No further change. a6b93f1f71 replaced the sentence; the comment now reads "Zero-filled new slots satisfy the packer's padding contract (amx_attn_iface.hpp)" (h/tron/models/self_attention.hpp:PAD_LINES). It names the contract and no longer says the result relies on the padding. The QK result rows 0..kv_mul-1 depend on their own packed columns only; the zero contract stays the tested convention (t/t_amx_numerics.cpp:ZERO_LINE).
