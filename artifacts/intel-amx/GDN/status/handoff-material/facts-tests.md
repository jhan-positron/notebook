# Tests, CI lanes and housekeeping facts for the four-PR split

Read from `/home/jhan/workspace/ai-runs/tron-gdn-amx` (git 2.34.1). Nothing was changed. GitHub facts were read on 2026-11-22 with `gh` (GET only).

## Short version
- The branch adds no new CTest name. `t_gdn_stats.cpp` is compiled into `t_gated_delta_net`, and `t_amx_gdn_numerics.cpp` into `t_amx_numerics`. So no new row in `config/test-benchmarks.json` is required.
- The default PR lane (GCP Nix) builds without `TRON_AMX_DISPATCH`, and it skips build and tests on a draft PR without the `Run CI` label. Every AMX-guarded case is compiled out there.
- Only the legacy workflow `cmake-single-platform.yml` builds tests with `TRON_AMX_DISPATCH=ON`. It starts by manual dispatch or from `publish-deb.yml`, and it is not a required check on `main`.

## Commits and PR state
| Item | Fact | Evidence |
|---|---|---|
| Order on branch | 72e1191804 -> 0d69ef3ce8 (counters) -> 775bba7661 (Part 0 + Part A) -> 882e5322f1 (Part B) | `git log --oneline -4 882e5322f1` |
| origin/main | 7eddde7895 (2026-11-21) | `git rev-parse` |
| Model branch vs main | 21 commits ahead, 48 behind; merge-base 54476c6581 (2026-11-16) | `git rev-list --count` |
| PR 5022 branch vs main | 7 ahead, 10 behind; merge-base 3bea58b788 (2026-11-19) | same |
| PR #5572 | draft, base `rbjarnason/qwen35-native-4b-registry`, head 882e5322f1, label `Skip benchmarks` | `gh pr view 5572` |
| PR #3696 | not draft, base `rbjarnason/qwen35-normalize-conv-weight-storage` (not `main`), labels `Continuous integration`, `Skip benchmarks` | `gh pr view 3696` |
| PR #5022 | not draft, base `main`, head ddf843ad97, label `Skip benchmarks`, merge state BLOCKED | `gh pr view 5022` |
| Model branch protection | none (`protected: false`) | `gh api .../branches/rbjarnason%2Fqwen35-native-4b-registry` |

## 1. AGENTS.md rules
`AGENTS.md` at ddf843ad97 equals origin/main (same blob). At 882e5322f1 it equals 72e1191804.

PR stacks, drafts, labels (identical text at 72e1191804:12-18 and origin/main:12-18):
> - In a PR stack, only the PR based on `main` may be ready for review. Keep every
>   descendant draft; after the parent merges, promote only the next PR.
> - Add `Skip benchmarks` to every PR unless the user explicitly directs
>   otherwise. Adding it requires no approval; removing it requires explicit user
>   approval.
> - Do not add `Run CI` unless the user explicitly directs it. Do not use it to
>   wake draft stack members unless the user explicitly directs that action.

Tests that must run in CI (72e1191804:22-28; origin/main:29-35, same text):
> - Every committed test must run in CI. Before committing it, verify that a
>   required CI suite collects and executes it; local execution and the test
>   file's presence are not sufficient. A test that does not execute in CI must
>   not be committed, except in extremely rare cases explicitly approved by the
>   user. Agents may not decide that an exception applies. Integrate tests into
>   the smallest appropriate existing suite; do not create a dedicated CI job
>   when an existing suite can carry them.

Changelog (origin/main:20-25 only; the section does not exist at 72e1191804):
> A PR with a notable change adds one
> [`changelog.d/` fragment](changelog.d/README.md) for the whole PR instead of
> editing `CHANGELOG.md`; purely internal changes need none. Whoever cuts a
> release folds the fragments into `CHANGELOG.md`.

`config/test-benchmarks.json`: no rule in root `AGENTS.md`. The rule is in `t/AGENTS.md`:23-26 (same blob b1a5a10e6f at 72e1191804, ddf843ad97, origin/main):
> - After adding or materially changing a test, refresh
>   `config/test-benchmarks.json` with `bin/slice bench --new` or targeted
>   `bin/slice bench --update <name>`. From a distributed route, use the public
>   `--remote` wrapper and leave the checkout unchanged until it finishes.

Also `t/AGENTS.md`:17-20: "Express hardware needs with `min_slices_N` labels and shared skip behavior with matching `SKIP_RETURN_CODE N` and `skip_return_code_N` labels."

Commit and PR text: no rule at either commit. A grep for commit-message, PR title and PR body rules over `AGENTS.md`, `t/AGENTS.md`, `.github/AGENTS.md`, `README.ci.md`, `lefthook.yml` returned nothing. The only related line is `changelog.d/README.md`:25 at origin/main: "Write the entry in the imperative mood, like a commit subject."

Differences 72e1191804 -> origin/main: only the 7-line `## Changelog` section in `AGENTS.md`, and 3 lines in `.github/AGENTS.md`:18-20 (CI changes need a fragment only when they change what users install).

## 2. Test programs (lines at 882e5322f1)
`git grep TRON_AMX_DISPATCH` on `t/CMakeLists.txt` finds nothing at any of the commits. So every test binary is built in every lane. The AMX cases are guarded inside the sources. The define reaches tests through `target_compile_definitions(tron PUBLIC TRON_AMX_DISPATCH)` (`src/tron/CMakeLists.txt`:220-225).

| Source | Registration | Added by | Guard | Host without AMX |
|---|---|---|---|---|
| `t_gdn_stats.cpp` | part of binary `t_gated_delta_net`, `t/CMakeLists.txt`:266-272, `LABELS fake` | 0d69ef3ce8 (blob unchanged later) | none | No AMX dependence. The test passes its own facts (`make_stats`, line 76-79); the expected `"amx_compiled":false` (line 564) does not read the build flag. |
| `t_gated_delta_net.cpp` | same binary, 266-272; in `TEST_INSTALL_TARGETS` line 1043 | 0d69ef3ce8 adds case at 2294; 775bba7661 adds 6 cases at 2840, 2851, 2863, 2912, 2955, 2993 and edits the counters case (12 lines removed) | only `block_kernel_expected()` 2829-2835 | All cases run and pass. Without the kernel, `advance()` takes the chain kernel; the checks expect `amx_blocks == 0` (2955-2991). No skip is reported. |
| `t_amx_gdn_numerics.cpp` | part of binary `t_amx_numerics`, 690-695, `LABELS fake` | 775bba7661 | whole file inside `#ifdef TRON_AMX_DISPATCH` (21-535), no `#else` | 5 cases (181, 288, 357, 396, 437) do `WARN(...)` then `return`. Catch2 counts them as passed. |
| `t_amx_numerics.cpp` | 692-695 | changed by 882e5322f1 | `#ifdef` 24-350; `#else` placeholder case with `SUCCEED` 352-354 | Gate case (130) and packer case (173) run on every host. QK (209) and PV (259) do `WARN` + `return` (214, 264), counted as passed. |
| `t_amx_dispatch_dtype.cpp` | line 698, `LABELS fake` | changed by 882e5322f1 | `#ifdef` 313-345; `#else` placeholder 347-349 | Runs fully on any host: it defines every AMX entry point as a CPU fake (header 1-8). |

- No `[slow]` tag in any of the five sources.
- Part 0 cases at 2840, 2851, 2993 call `advance(..., gdn_block_kernel::off, ...)`. Cases at 2863, 2912, 2955 use `gdn_block_kernel::when_available`. The file includes `tron/kernels/amx_gdn_iface.hpp`, a Part A file.
- The counters commit already carries AMX-named fields (`amx_blocks`, `amx_fallback_blocks`, `amx_compiled`); `t_gdn_stats.cpp` at 0d69ef3ce8 lines 89-97, 564.

Different convention on the PR #5022 branch (ddf843ad97):
- `t_amx_numerics.cpp`:379-394 uses `SKIP(...)`, not `WARN` + `return`. No placeholder case. A transpose case (72-80) sits outside the guard and runs in every build.
- `t/CMakeLists.txt`:620-625 registers it with `SKIP_RETURN_CODE 4` and label `skip_return_code_4`.
- Both of its cost rows carry `"skip_return_codes":[4]`.
- Simulated apply of 882e5322f1 onto ddf843ad97 (`git merge-tree 775bba7661 ddf843ad97 882e5322f1`; the `--write-tree` form does not exist in git 2.34.1): conflict hunks: `t/t_amx_dispatch_dtype.cpp` 9, `t/t_amx_numerics.cpp` 7, `t/CMakeLists.txt` 1, `h/tron/kernels/amx_attn_iface.hpp` 6, `h/tron/models/self_attention.hpp` 6, `src/tron/kernels/amx_attn.cpp` 0. A real cherry-pick may count differently.
- Part B's own change to `t/CMakeLists.txt` is one 2-line comment (diff 775bba7661..882e5322f1).

## 3. CI lanes
`.github/workflows` is identical at origin/main, 72e1191804 and ddf843ad97.

Default lane: `gcp-nix.yml` ("GCP Nix").
- Trigger, lines 13-14: `pull_request: types: [opened, synchronize, reopened, ready_for_review]`. No `branches` filter, so a PR with any base starts it.
- Draft rule, line 5: "# Draft PRs run lint, machinery, and fresh-plan checks; Run CI enables the product pipeline."
- Gate, lines 188-191 (`build-ingest`), repeated at 314-317 and 402-405:
  ```
  if: >-
    github.event_name != 'pull_request' ||
    !github.event.pull_request.draft ||
    contains(github.event.pull_request.labels.*.name, 'Run CI')
  ```
  `Build Tron`, `Test host`, `Test FPGA` depend on those jobs.
- It does not set `TRON_AMX_DISPATCH`. The configure list is `nix/cmake-tron-test-build.nix`:79-101 at origin/main (no such flag). The option defaults OFF (`CMakeLists.txt`:46).
- Tests run on `runs-on: [self-hosted, fpga, test, avx512]` (lines 555, 622) with `bin/slice run --filter=host` and `--filter=fpga --min-slices=2` (`nix/tron-test-environment.nix`:34, 39). Tests labelled `fake` go to the host list (`doc/slice.md`:236-237).
- Measured on PR #5572 (draft): Lint, CI machinery, Fresh Cabal plan, deb-smoke SUCCESS; Build Tron, Test host, Test FPGA, Test SKIPPED.
- Measured on PR #5022: all GCP Nix jobs SUCCESS.

Lane with `TRON_AMX_DISPATCH=ON`: `cmake-single-platform.yml` ("CMake and CTest").
- Triggers, lines 5-16: `workflow_dispatch` and `workflow_call` only.
- Configure, lines 353-355: `cmake -B .../gen --preset native -DBUILD_TEST_MODELS=ON -DBUILD_INGEST_MODELS=ON -DTRON_REQUIRE_ALL_MODEL_TESTS=ON -DTRON_AMX_DISPATCH=ON`.
- Tests: `bin/slice run --filter=host` (line 473) and `--filter=fpga --min-slices=2` (591), on `[self-hosted, fpga, test, avx512]`.
- Manual start (`README.ci.md`:104-106 at origin/main): `gh workflow run cmake-single-platform.yml --ref YOUR_BRANCH -F skip_benchmarks=true`.
- Called by `publish-deb.yml`:56-70 only for a tag ref or `feature_branch == '1'`.
- The same draft gate text is at lines 146-149, but the event is never `pull_request` now.
- Runner pool (`README.ci.md`:449-457): 4 AMD Genoa hosts and 3 Intel Granite Rapids hosts share the labels. `README.ci.md`:591-593: "The kernel cases of `t_amx_numerics` execute AMX only when the test job lands on a Granite Rapids runner".
- Run 44777748892 (manual, ddf843ad97, 2026-11-20, success): `test-host` on delphi-3bd6-0, `build` on andoria-ee10-0, `test-fpga` on andoria-02-0.
- No run of this workflow exists for branch `jhan-gdn-amx`.
- Required checks on `main` (branch protection API): Build Tron, Build ingest, Build model traces, Generate model plugins, Fresh Cabal plan, Test, Test FPGA, Test host, Test ingest, CI machinery tests, Lint, deb-smoke-tests. The legacy job names are not in the list.

Other presets: `deb` sets `TRON_AMX_DISPATCH` ON with `ENABLE_TESTS` OFF (`CMakePresets.json`:57-69). `coverage` does not set it (109-121).

`README.ci.md` text differs per branch: 775bba7661 edits lines 586-590 (adds the GDN kernel); ddf843ad97 rewrites the same paragraph at 588-597 ("only the legacy `cmake-single-platform.yml` passes it").

## 4. Slice cost data
The branch does not change `config/test-benchmarks.json` (blob aa95294a8b at 72e1191804 and 882e5322f1). Platform blocks: genoa96, genoa32, granite_rapids_6960p, granite_rapids_6962p.

| Test name | 72e1191804 | ddf843ad97 |
|---|---|---|
| `t_gdn_stats` | no entry (not a CTest name) | no entry |
| `t_amx_gdn_numerics` | no entry (not a CTest name) | no entry |
| `t_gated_delta_net` | genoa96 only (0.339 s, 8 MB) | genoa96 only (same row) |
| `t_amx_numerics` | genoa96, granite_rapids_6962p | same two, plus `skip_return_codes [4]` |
| `t_amx_dispatch_dtype` | genoa96, granite_rapids_6962p | same two |

- origin/main changed the `t_gated_delta_net` row to 3.339 s and 322 MB in e1b4b8421f (#5461).
- `t/t_gated_delta_net.cpp` differs between 72e1191804 and origin/main (978 changed lines).

`doc/slice.md` (same blob at all three commits):
- Test without an entry, lines 147-149: "slice runs it in the **unbenched phase** at 2 slices (tagged `[new]`) before the packer's schedule kicks in".
- `bin/slice bench --check`, line 204: "Check live variants; global gaps and duplicate test names fail, local gaps warn." Code: a name missing from every platform prints "error: bench entries missing from every platform" and exits 1 (`bin/slice`:2119-2125 at origin/main); missing from the current platform only prints a warning (2127-2133). GCP Nix runs it in `Build Tron` (`gcp-nix.yml`:502-505).
- `--check-platform`, line 205: "Without a CTest build, require a complete benchmark block with unique test names for the detected platform." (`bin/slice`:2064-2093; `gcp-nix.yml`:487-488).
- Which platform key each CI runner detects: not verified.

## 5. changelog.d
- 72e1191804 and 882e5322f1: folder does not exist. Its first commit 3609c3b4f8 (#5179) is not an ancestor of 72e1191804.
- ddf843ad97: `5022.changed.md`, `5429.added.md`, `5482.fixed.md`, `README.md`.
- `changelog.d/5022.changed.md` at ddf843ad97, whole file: `- runtime: Speed up Muse Glimmer 30B attention with AMX on Intel hosts. (#5022)`
- Stack rule, `changelog.d/README.md`:26-29 at origin/main (same text at ddf843ad97):
  > - In a stack of pull requests, the one that makes the change usable carries
  >   the fragment, and the others add none. A release cut while the stack is
  >   half merged then says nothing about a change that doesn't work yet. A pull
  >   request in the stack that is notable by itself adds its own fragment.
- Naming, lines 10-16: `<PR>.<section>.md`, PR number, never an issue number. Entry, lines 23-25: one `- scope: Entry. (#N)` line, at most 80 characters.

## 6. Lint that CI runs
The `Lint` job (`gcp-nix.yml`:43-55) runs `bash bin/ci/run-lint-checks.sh`, which builds `.#checks.x86_64-linux.lint-toolchain` (`bin/ci/run-lint-checks.sh`:7, 18). It also runs on draft PRs. Commands in `flake.nix` at origin/main (72e1191804 has the same commands at 2311, 2323, 2343, 2453):

| Check | Command | Where |
|---|---|---|
| Whitespace | `git --no-pager diff --check --cached "$empty_tree" -- ':!lib/**'` (whole tree, not only the diff) | 2303-2309 |
| Forbidden include | `grep -l '#include <cassert>'` over `h src t` | 2311-2323 |
| C++ format | `clang-format-19 --dry-run -Werror` over `h` (`.hpp .h .i`), `src t` (`.cpp`), `t` (`.hpp`) | 2325-2336; tool from `pkgs.llvmPackages_19` (620, 643-644). Patch version: not verified. |
| CI pins | `bin/ci/lint-ci-pins.sh` | 2439 |
| Agent guides | `python3 bin/ci/lint-agent-guidance.py` | 2441-2442 |
| Lock files | `bin/ci/check-lock-freshness.sh` | 2444 |
| Notes | `make lint-notes` | 2446 |

- `make lint-notes` (`GNUmakefile`:818-822) reads `h`, `t` and `src` sources, `doc/*.md`, ingest `.hs`, and the list at 71-85. `README.ci.md` and `src/tron/CMakeLists.txt` are not in that list. It exits with failure on "Reference to undefined" Notes (`bin/lint-notes`:268-287).
- Note definitions at 882e5322f1: `Note [GDN path stats]` `h/tron/models/gdn_stats.hpp`:7 (from 0d69ef3ce8); `Note [GatedDeltaNet chain recurrence]` `h/tron/kernels/gated_delta_net.hpp`:309; `Note [AMX GatedDeltaNet block kernel]` `h/tron/kernels/amx_gdn_iface.hpp`:17.
- `h/tron/models/gdn_rolling_executor.hpp`:132 and 339 reference `Note [AMX GatedDeltaNet block kernel]`, whose definition is in a Part A file.
- Local pre-commit equivalents: `lefthook.yml`:15-28, 30-42, 44-62, 284-309 (same blob at all three commits).
- No commit-message check and no changelog-length check: grep over `lefthook.yml`, `flake.nix`, `bin/ci`, `.github`, `GNUmakefile` at origin/main found none.

## 7. Gemma 4 E4B generation test (ddf843ad97)
`t/gemma_4_e4b_generation.hpp` has the same blob at 72e1191804, ddf843ad97 and origin/main.
- What bounds the context: the token file. Line 40-41 loads hash `09e57df5...2d03` from `/scratch/test/data` (`SCRATCH_DIR`, `CMakeLists.txt`:60). The file holds 24 tokens (measured: header count 24, 104 bytes).
- `force_generate` splits it: `gen_steps = min(text.size() / 2, 30)` = 12, prompt = 12 tokens (`t/force_generate.cpp`:363-368). Options: `.max_layers = 42, .max_minibatches = 1` (line 46).
- Lines 43-44 set `TRON_BOOK_INITIAL_TOKENS=64` and `TRON_BOOK_MAX_TOKENS=64`. They size the KV book, not the context: defaults are 1600 (`h/tron/scheduler/full.hpp`:55-70), the page is 64 tokens (`h/tron/models/kv_cache.hpp`:1835), and 993-1000 says "The configured maximum clamps the growth preference, not the capacity required by a caller's token chunk."
- Golden scores: hash `4105f341...acd2` (line 48-49), file `/scratch/test/data/<hash>`, 25,166,016 bytes, 24 rows of 262,144 floats (measured), dated 2026-07-10. So they cover 24 token positions.
- Check: TVD tolerance 0.05, outlier cap 0.20, 20 % outliers, first 3 positions skipped, top-5 overlap at least 3 (lines 50-55).
- How the file was produced: not verified (commit b31fe87d45 has an empty message body). Two writers of this format exist: `ingest/export/reference_logits.py` (HuggingFace forward on CPU; `--max-tokens` default 40, `--save-tokens`, `--max-layers`, `--scratch-dir` default `/scratch/test/data`; lines 1-8, 48-65, 219-264), and the test itself, which saves its own logits and fails when the golden file is missing (`t/testutil.cpp`:339-347).
- `t/model_test_selection.cmake`:19-37 maps test name to runtime slug, for example `"gemma_4_e4b_fpga|ingested-gemma-4-e4b-it"` (line 30). `t/CMakeLists.txt`:359-375 builds one binary per model with `RESOURCE_LOCK fpga`, labels `fpga`, `ingest`, `skip_return_code_4`, and `SKIP_RETURN_CODE 4`. These tests run in the FPGA job.
- Cost rows for the four E4B tests exist in genoa96 and granite_rapids_6962p only.

Facts that bear on a variant with several 64-token pages:
- A token file with that many tokens under `/scratch/test/data`, named by its sha256; `load_tokens_by_hash` returns an empty vector when the file is missing (`t/testutil.cpp`:59).
- A golden file with one row per token of the text: the row counts must match (`t/testutil.cpp`:256). One row is 1,048,584 bytes, so 128 positions take 134.2 MB and 256 positions take 268.4 MB (computed).
- With the default `gen_steps`, at most 30 tokens are forced; the rest is prompt, processed in chunks of `get_prompt_chunk_size()` (`t/force_generate.hpp`:69-74).
- A new CTest name needs a row in at least one platform block, or `bench --check` fails.
- The AMX dense path needs a full 64-token page; a 63-token page goes to the AVX dotter (`t/t_amx_dispatch_dtype.cpp`:11-14 at 882e5322f1). With 24 tokens no page is full.
- Not verified: whether this FPGA-labelled test computes attention on the CPU, and the head size and query-heads-per-KV-head of Gemma 4 E4B.

## Final table
"Default PR lane" means the GCP Nix `Test host` job. It runs only when the PR is not a draft or carries `Run CI`. PRs 1 to 3 have the model branch as base, and PR 4 would have the PR #5022 branch as base.

| Test program | PR | Runs in the default PR lane? | AMX cases run where? |
|---|---|---|---|
| `t_gdn_stats.cpp` (in binary `t_gated_delta_net`) | 1 counters | Yes, all cases | No AMX cases |
| `t_gated_delta_net.cpp`: case at 2294 | 1 counters (edited again by Part 0 + Part A) | Yes | No AMX cases |
| `t_gated_delta_net.cpp`: cases at 2840, 2851, 2993 | 2 Part 0 | Yes | No AMX cases (block kernel off) |
| `t_gated_delta_net.cpp`: cases at 2863, 2912, 2955 | 3 Part A | Yes, but on the chain kernel only | Legacy lane, and only when `test-host` lands on a Granite Rapids runner |
| `t_amx_gdn_numerics.cpp` (in binary `t_amx_numerics`) | 3 Part A | Binary runs; its 5 cases are compiled out | Legacy lane on a Granite Rapids runner; elsewhere `WARN` + return, counted as passed |
| `t_amx_numerics.cpp` | 4 Part B (registration line also changed by Part A) | Binary runs; at 882e5322f1 only the placeholder case | Legacy lane: gate and packer cases on any runner; QK and PV cases on a Granite Rapids runner only |
| `t_amx_dispatch_dtype.cpp` | 4 Part B | Binary runs; only the placeholder case | Legacy lane, any runner (CPU fakes, no AMX instruction) |

Scratch copies used for line numbers: `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/wf/gcp-nix.yml`, `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/wf/cmake-single-platform.yml`, `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/mt-partB.txt`.
