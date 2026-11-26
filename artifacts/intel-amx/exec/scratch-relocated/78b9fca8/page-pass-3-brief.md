# Page pass 3 brief (respond-2-Isaac.html), written 2026-11-19 19:30 PST

Apply on top of the page as it stands after apply_patch2.py (205,248 bytes). Same rules as pass 2:
one idempotent patch script (apply_patch3.py), assert every anchor, keep every id, plain English,
light theme, structure check, stale-phrase grep, headless render of the changed parts.

## A. jhan's second-round answers (2026-11-19, about 19:27 PST). Replace the content of box `#open2`.

Quote them:
1. Nix-flag promise (T1, I7): "I kind of think Issac and we are treating this too serious than what it
   deserves. We did the manual testing at CI machine delphi-3bda when we had the access, so all the tests
   were CI equivalent, but not run from CI process. I leave the decision to you, if you can think of a
   simpler change and explaination and without mentioning issue 3997 at all, that would be great; if you
   think what you current have is the best to move forward, please do."
   My decision: the simpler form. Short comment and README fix, short reply, no flag in this PR,
   no mention of #3997 in any reply, no promise of another PR.
2. Merge main first: "yes, merge". Done in the working tree (PR head 4c4b7b8864 merged with main 3bea58b788,
   no conflict; 3 files merged by git: self_attention.hpp, src/tron/CMakeLists.txt, t/t_llama_unit.cpp).
3. README.ci.md and the issue-number rule: "it is not source code, rule does not cover it".
4. Commit, push and post: "sounds good" (to: I ask once, when the tests at the final head are in).
   Nothing is committed, pushed or posted.

## B. New points that need jhan's word (new box `#open3`, placed after `#open2`)

1. Changelog fragment. Main has a new rule since 2026-11-18 (tron PR 5179; announced in Slack #software on
   2026-11-17 16:48 PST by Weishan Yang): a PR with a change users would notice adds one file in
   `changelog.d/`. "Performance" is on the list of notable changes (changelog.d/README.md). Proposed file
   `changelog.d/5022.changed.md` with one line (79 characters; the limit is 80):
   `- runtime: Speed up Muse Glimmer 30B attention with AMX on Intel hosts. (#5022)`
   It is in the working tree. jhan to confirm the wording, or say that the PR needs none.
2. The repository test policy (AGENTS.md, section "Test policy", in the file since 2026-09-01):
   "Every committed test must run in CI. ... A test that does not execute in CI must not be committed,
   except in extremely rare cases explicitly approved by the user. Agents may not decide that an exception
   applies." This is the written rule behind Isaac's blocker. Of this round's new tests, the transpose case
   runs in the required lane. The new sections of t_amx_dispatch_dtype (16 heads partial page, 16 heads
   kill switch, 32 heads / 2 KV heads) and the new checks of t_amx_numerics PV exist only in a build with
   the option ON, so they run in the legacy CMake workflow and by hand, not in the required lane. jhan's D1
   decision is the approval the policy asks for; the page should say so in one sentence and ask jhan to say
   if they see it differently.

## C. D1 replies, rewritten short. No "#3997" in T1, I7, I8, T4, the combined reply, or Part C.

I7 "Action": accept, modified (comment and README fixed here; no Nix flag in this PR).

I7 reply:

You are right. The comment went stale when CI moved to GCP Nix: that build leaves the option OFF
[nix/cmake-tron-test-build.nix:79-101], and the legacy CMake workflow no longer runs on pull requests.
Fixed here and in README.ci.md:

```
# fast-path call sites. The default CI build (GCP Nix) leaves the option OFF;
# the deb preset and the legacy CMake workflow (cmake-single-platform.yml) set
# it ON. In that workflow the kernel tests execute only on a Granite Rapids
# runner; on other runners they are reported as skipped, and ctest and Slice
# still report a pass.
```

I am not adding the flag to the Nix build in this PR. With it ON, every eligible model test of the
required lane would run the AMX kernels on an Intel runner and the AVX path on an AMD runner. That
changes CI for every pull request, and it is not part of serving kv_mul 16.

What covers this PR:

- The AMX tests ran with the option ON on Granite Rapids hardware: on delphi-3bda, the machine of the
  nightly systems test, at the commit you reviewed (2026-10-18, `round3.log`), and on delphi-3b35 at the
  final head. The records are in the Verification section.
- A run of the legacy CMake workflow at the final head, which builds and tests with the option ON:
  run <id>, test-host on <runner>. [filled in after the run]
- The new transpose test needs no AMX, so it runs in the required lane.

(The earlier paragraphs of the I7 reply about the publish-deb detail, Catch2 exit codes, the "own one-line
PR under #3997" and the rebase promise are removed.)

I8 reply:

You are right. Fixed in this PR: the paragraph no longer says "so CI covers that code" or "skip with a
warning".

```
`TRON_AMX_DISPATCH=ON` compiles the AMX software-attention kernels and their
dispatch (see Note [AMX attention dispatch] in
`h/tron/kernels/amx_attn_iface.hpp`). Of the CI workflows, only the legacy
`cmake-single-platform.yml` passes it; the default `gcp-nix.yml` build leaves
it OFF. The `deb` preset also sets the option ON, so the released package
carries the kernels and selects them at run time only on hosts with AMX. The
`deb-host` preset inherits the setting from `deb`. Every other preset leaves
it at its default OFF. The kernel cases of `t_amx_numerics` execute AMX only
when the test job lands on a Granite Rapids runner; elsewhere Catch2 reports
them as skipped, and ctest and Slice still report a pass.
```

The flags block above it gets one caption line: "The legacy CMake build (`cmake-single-platform.yml`)
configures with the `native` preset and, among others, these flags:". (The `deb-host` sentence is from
main; the paragraph is main's text with two phrases fixed and one sentence added.)

T1 reply:

You are right on the facts: the required GCP Nix build leaves `TRON_AMX_DISPATCH` OFF, so in that lane
both AMX test binaries ran their placeholder case. The stale sentence in the CMake comment and in
README.ci.md is fixed in this PR. I am not adding the flag to the Nix build here: it would change what
every eligible model test of the required lane exercises on Intel runners, and that is a CI change for
all pull requests, not part of serving kv_mul 16. Evidence for this PR: the option-ON test records from
Granite Rapids hosts (delphi-3bda at the reviewed commit, delphi-3b35 at the final head), a run of the
legacy CMake workflow at the final head, and the new transpose test, which runs in the required lane.

T4 reply: drop the last sentence ("The required-lane change stays on #3997, ..."). In its command list the
PV 4-head section is now named "4 heads: rows 0..3 in the envelope, rows 4..15 zero".

Combined reply, first bullet ("CI lane"): "The stale sentence in the CMake comment and in README.ci.md is
fixed. The Nix flag stays out of this PR: it changes what the model tests of the required lane exercise on
Intel runners. Evidence for this PR: option-ON test records from Granite Rapids hosts, a run of the legacy
CMake workflow at the final head, and the transpose test in the required lane."

Part C: delete the bullet "One-line PR: -DTRON_AMX_DISPATCH=ON ... under #3997" and the
`nix/cmake-tron-test-build.nix` bullet's "one-line PR under #3997" wording (say: not changed in this PR).
D1 card: its decision line now reads that the flag stays out of this PR and that the replies do not cite
#3997 (jhan, second round). The card's Q&A may still name #3997 as a fact for jhan; only reply drafts
must not.

## D. Reply texts that changed because of the implementation

- I10: the function is `transpose_scores<group_heads>` with `requires(group_heads_ok(group_heads))` in the
  new header `h/tron/kernels/amx_attn_transpose.hpp`; the helper `store_transposed_rows`, the lane
  constants and `TILE_FP32S` moved with it; plain `inline` was enough (no always_inline). The test case
  "AMX QK transpose writes the group_heads score rows" has sections "4 heads: rows 0..3 written, rows
  4..15 untouched" and "16 heads: all 16 rows written"; it uses a row stride of 80 floats, so each row has
  16 guard columns past token 63 that must keep the sentinel; 1,280 assertions per section. The sentinel
  constant moved above `#ifdef TRON_AMX_DISPATCH`. Local object compare (clang 19.1.7, the lcheck flag
  set, 2026-11-19): all 10 functions of amx_attn.o identical before and after the move, and identical
  between 4c4b7b8864 and the final tree; `qk_rowmajor_128x4<4>` 204 instructions, `<16>` 207. The compare
  with the product flags on delphi-3b35 is pending.
- I14: both asserts sit in `transpose_scores` (already noted in pass 2).
- I17: section name "host_bf16, 32 heads / 2 KV heads, KV head 1, full page: the pack reads the second
  group of 16 heads"; template parameters `<host_bf16, QUERY_HEADS_32, KV_HEADS_2>`, argument `KV_HEAD_1`.
- I20: clang-format puts the two fake signatures on two lines each:
  `void qk_rowmajor_128x4(` / `    const_k_row_major_plane_view, const bf16*, float* output, size_t stride) noexcept {`
  and `void weights_times_v_128x4(` / `    const_v_vnni_plane_view, const float*, size_t, float* output) noexcept {`.
- I7/I8 texts: section C above replaces the pass-2 wording.

## E. Part C status

Code and comment edits: DONE in the working tree `/home/jhan/workspace/ai-runs/pr5022-final/tron`
(uncommitted: PR head 4c4b7b8864 merged with main 3bea58b788, plus the review edits; 9 files changed
against the merge, 1 new header, 1 changelog fragment). Local checks on 2026-11-19: syntax check with
clang 19.1.7 of t_amx_numerics.cpp (option ON and OFF), t_amx_dispatch_dtype.cpp and t_llama_unit.cpp:
0 errors, 0 warnings; clang-format 19.1.7 clean on the 6 C++ files; kernel object compare as in D.
Not done locally: a standalone run of the transpose function (blocked by the permission system); the
test binary on delphi-3b35 covers it.
Pending: build, tests, object compare with product flags and the registry refresh on delphi-3b35 after
the reboot; `config/test-benchmarks.json` not edited yet.

## F. Corrections to earlier statements

- USE_HW_ATTN setters outside the C++ sources: one test registration (t/CMakeLists.txt:598) and one repro
  script, not "two tests".
- Line numbers on main moved: `make deb` is at publish-deb.yml:118, `cmake --preset deb` at
  GNUmakefile:580 (were :113 and :510 at 4c4b7b8864).

## G. RESULTS (appended later by the main session)


## D2. Later changes to quoted texts (19:39 PST; these override section D where they differ)

The git tree hash of the prepared tree is now bbe06f7ed06cf6e265c2a017614b75ee555be3b7 (prep.txt is updated).
The C++ coding guide and the simplify-cpp-comments skill were applied to the new code. Quoted texts that changed:

- T11, the `group_heads_ok` comment is now 5 lines:
```
// The group sizes the kernels are compiled for: 4 and 16, the sizes validated
// on AMX hardware (unit sections, token identity, throughput). The code could
// serve any multiple of 4 up to 16; kv_mul 8 has no AMX run yet and is left
// out. A new size also needs its explicit instantiations at the end of
// amx_attn.cpp and its t_amx_numerics sections.
```
- I24, the fill of `exp_rows` names the sentinel weight:
```
  // Rows group_heads..15 hold a nonzero value the kernel must never read.
  constexpr float UNREAD_WEIGHT_1 = 1.f;
  alignas(64) float exp_rows[TILE_ROWS_16][PAGE_TOKENS_64];
  for (size_t qi = 0; qi < TILE_ROWS_16; ++qi) {
    for (auto& x : exp_rows[qi]) {
      x = qi < group_heads ? std::exp(ue(gen)) : UNREAD_WEIGHT_1;
    }
  }
```
- I17: `n_kv_heads` defaults to a named constant `KV_HEADS_1`; the new section passes `SECOND_KV_HEAD_1`
  (`exercise_page<host_bf16, QUERY_HEADS_32, KV_HEADS_2>(page_size, /*repeat=*/false, /*amx_available=*/true, SECOND_KV_HEAD_1);`).
- I20: the comment above the `qk_rowmajor_128x4` call in t_amx_numerics.cpp is removed, not shortened: the alias
  name says what the comment said.
- I10: the header's two new comments are short: the file comment (3 lines: the transposing store of the QK
  kernel; AVX-512 only, so a host without AMX can run it) and the function comment
  (`s[head][token] = s_transposed[token][head] for head < group_heads`; other rows of `s` are not written).
  The Note [QK orientation] gets one sentence: "The transpose is transpose_scores in amx_attn_transpose.hpp."
  In the test, the stride constant is `ROW_STRIDE_80` and the first value is `FIRST_SCORE_1`.
