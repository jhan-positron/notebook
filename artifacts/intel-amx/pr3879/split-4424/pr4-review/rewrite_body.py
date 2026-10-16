import json
import re
from pathlib import Path

p = Path(__file__).parent
old = (p / 'body-latest.md').read_text()
tables = re.findall(r'(?:^\|.*\n)+', old, re.M)
assert len(tables) == 10
glossary = json.loads((p / 'comments.json').read_text())[0]['body']
glossary = glossary[glossary.index('| Term |'):].strip()
# Keep the published vocabulary, with limits that the implementation requires.
glossary = glossary.replace('until all 16 rows are saved.',
    'until conversion after all 16 rows are saved. Short writes for hardware-scored operations remain row-major.')
glossary = glossary.replace('A cell that is not resolved is read as noise.',
    'An unresolved cell does not establish a difference under this rule.')
glossary = glossary.replace('the two-sided 5 % threshold for 9 degrees of freedom',
    'the campaign\'s stated threshold')
glossary = glossary.replace('the layout PR\'s merge base, the `main` commit it is based on',
    'the `main` commit included in the layout PR')

body = '''## Short version

This pull request keeps short writes to the attention-key cache in contiguous rows until a complete block can be packed for faster reading.
The measured accelerator-assisted throughput is within the comparison band of the main branch.
Token mismatches, slower throughput with matrix acceleration disabled, and a pending package campaign remain open.

## Words used here

'''+glossary+'''

### Background

The previous packed layout writes one generated token's K row across 64 cache lines.
FPGA staging then gathers that row from those lines.
This PR stores a short run as contiguous rows inside the same block storage.
Each row occupies 4 cache lines, or 256 bytes.

Issue #4500 records the earlier FPGA-attention throughput loss for qwen3-4b, the Qwen3 model with 4 billion parameters.
The 2026-09-16 runtron comparison reported losses of 2.2 % at tp2 and 9.7 % at tp4.
The 2026-09-18 nightly-layout comparison reported losses of 5.0 % and 11.0 %, respectively.
Those historical runs are background evidence. The tables below use this PR's own binaries.

## The changes

- **Storage and conversion.** `h/tron/tensor/k_vnni.hpp` adds contiguous rows inside each 16-token block. `block_to_vnni` converts a complete block through a 64-byte-aligned temporary array. `block_to_rows` reverses the conversion. The conversion tests compare the complete plane with the existing per-token store.
- **Page state.** `h/tron/models/kv_cache.hpp` tracks saved rows and converted blocks separately for every storage slot. The EAGLE storage has its own entry. Row access follows the converted-block bit. A whole-block save publishes its bits after every KV head is written.
- **Page reuse and copies.** Forgetting an offset clears saved-row state at and above that offset. A converted block with retained rows is first returned to row-major form when its storage is readable. Page copies carry the state with the rows. Partial copies convert the destination blocks as needed.
- **Stable storage references.** `k_storage_ref` pairs physical storage with its state entry. The pending-conversion list captures that pair during the save. A later storage-view change cannot redirect the conversion.
- **Save and forward completion.** `h/tron/models/model.hpp` stores a full 16-token run directly in VNNI form. Shorter runs use row stores. For software-scored operations, a short run that completes a block queues its conversion. The forward path converts queued blocks after the plugin joins its workers and `wait_for_coop_gof` drains staging. Logit delivery follows the conversion.
- **Hardware-attention policy.** Short writes for an operation selected for hardware attention do not record saved-row bits or queue conversion. Those blocks stay row-major. Whole-block saves still write VNNI form. CPU fallback for a hardware operation follows the recorded layout.
- **Scoring.** `h/tron/models/self_attention.hpp` permits the dense AMX path only when every block of the page is VNNI. Otherwise, the reader scores converted blocks and the dotter scores row-major rows. The kernel comments describe this split.
- **Staging.** `h/tron/scheduler/full.hpp` returns row-major K rows directly to staging. Converted rows are gathered into caller-owned scratch. Staging copies either representation into the existing transfer buffers.
- **Packaging.** `CMakePresets.json` enables `TRON_K_VNNI` in the `deb` preset alongside `TRON_AMX_DISPATCH`. Other presets retain the default OFF setting. `README.ci.md` documents the choice.
- **Tests and timing records.** Existing test binaries cover conversion, page state, EAGLE storage, page append, mixed-layout scoring, the hardware-operation policy, and dense-path selection. `config/test-benchmarks.json` contains refreshed durations and memory records for four tests.

The partial-block masked save is removed from `save_k`.
`store_block` retains its mask parameter for the existing block-store test.
Its production callers pass the full mask.

## Measurements

### Revisions and setup

The runtron measurements were collected on 2026-10-12 on the Granite Rapids test machine.
The measured implementation is `ea94e95a4e`.
The published head, `e7d06a1267`, differs only in four benchmark-record rows.

- `base`: `main` at `72308ec90c`, with row-major K and AMX dispatch enabled.
- `new`: this PR at `ea94e95a4e`, with VNNI K and AMX dispatch enabled.
- `head`: the parent PR #4898 at `dfafd13dce`, with both options enabled.
- `newoff` and `headoff`: the corresponding binaries with `TRON_AMX_DISABLE=1`.

The throughput experiment uses qwen3-4b, 8 users, and 256 generated tokens.
Each cell has 3 repetitions in alternating binary order.
CPU attention uses `USE_HW_ATTN=0`. FPGA attention leaves that variable unset.
Production serving was stopped during these whole-machine runs.

The band is twice the larger sample standard deviation of the compared arms.
It has a minimum of 0.4 tokens/s/user for TPS and 0.15 s for TTFT.
A difference beyond the band counts as a change under this experiment's rule.
An inside-band result does not prove equivalence.
Parentheses in the arm tables give sample standard deviations.
TTFT is the maximum over the 8 users.

### CPU attention

'''+tables[0]+'\n'+tables[1]+'''
The cells are ordered as tp2 with 1,024 prompt tokens, tp2 with 8,192 prompt tokens, and tp4 with 1,024 prompt tokens.

- **This PR versus its parent, AMX enabled:** TPS and TTFT are inside their bands in all three cells. The largest TPS difference is -0.7 %. The 8,192-token TTFT difference is +231 ms, within its 0.30 s band.
- **This PR versus main:** TPS increases by 4.7 %, 9.4 %, and 2.4 %. Each increase is beyond its band. TTFT decreases by 56 ms, 697 ms, and 73 ms. Only the 8,192-token TTFT decrease is beyond its band.
- **AMX disabled versus enabled in this PR:** TPS changes by -13.6 %, -20.6 %, and -9.3 %. TTFT increases by 780 ms, 66.0 s, and 275 ms. These differences are beyond their bands.
- **Both binaries with AMX disabled:** This PR is 3.4 %, 2.9 %, and 2.0 % slower than its parent in TPS. Each difference is beyond its band. TTFT increases by 453 ms at 8,192 prompt tokens, beyond its 0.21 s band. The shorter-prompt TTFT differences are inside their bands.
- **Parent versus main in this session:** TPS gains are 5.4 %, 9.2 %, and 2.9 %. TTFT decreases by 65 ms, 928 ms, and 78 ms. These results are consistent with the parent's earlier report within the stated bands. They do not exclude every possible change in machine performance.

The AMX-disabled comparison changes storage, conversion, and scoring together.
It does not isolate the cost of any one operation.
The cause of the slowdown is unmeasured.
The relevant Perfetto spans are `Save K`, `convert_k_blocks`, and the attention spans.

One hypothesis is unnecessary dotter construction for fully converted pages.
The changed software loop constructs dotters before it knows whether any row needs them.
For the measured `bf16`, 128-value path, the specialized dotter loads four vectors.
It does not convert the query to fp32 at construction. [h/tron/kernels/dotter.hpp:174–208]
Another hypothesis is the added per-token layout branching.
Neither hypothesis establishes the measured cause.
The planned comparison uses a variant that constructs dotters only at the first row-major row.
That comparison is pending.

### FPGA attention

'''+tables[2]+'\n'+tables[3]+'''
This PR differs from main by +0.6 % TPS at tp2 and -0.3 % at tp4.
Both results are inside their bands.
The parent loses 1.9 % and 11.0 % against main, beyond the bands.
This PR improves on the parent by 2.5 % and 12.1 %, beyond the bands.
These cells support recovery of the issue #4500 loss under the measured conditions.
Every FPGA-attention TTFT comparison is inside the 0.15 s band.
No run reported a loss of hardware attention.

### Whole-machine package campaign — pending

The campaign compares the base and target Debian packages through the nightly's performance harness.
The packages are installed through the package manager.
The service manager starts the serving engines.

- **Question:** Does the target retain the earlier package gains for Llama and maintain parity for GPT-OSS?
- **Comparator:** Base package `2026.10.12-72308ec9-jhan-pr4ci-base` against target package `2026.10.12-ea94e95a-jhan-pr4ci-target`.
- **Cells:** llama-3.1-8b at tp2 with 8 users and 1,024 prompt tokens, llama-3.1-8b at tp2 with 32 users and 4,096 prompt tokens, and gpt-oss-120b at tp4 with 8 users and 1,024 prompt tokens. All use FPGA attention.
- **Order:** Base, target, target, base. Each pass contains 10 rounds. TPS is sampled over generated tokens 896 through 1024.
- **Decision rule:** The absolute paired t must be at least 2.26 and the absolute difference at least 1 %. A TTFT difference must also reach 1 ms. The campaign pools both pass pairs under its stated rule.
- **Memory:** Record VmHWM and VmRSS after provisioning and after each benchmark. Sum the serving processes across engines.
- **Status:** Scheduled after the nightly CI of 2026-10-13, no earlier than 13:00 UTC. Results are not available in this description.

The base package uses the main commit included in this stack.
It does not use the latest nightly package.
Insufficient data: comparison with that nightly requires a separate campaign using it as the base.

### Token identity

The token comparison uses qwen3-4b at tp2 with 1 user.
Each run uses temperature 0, `--pay-for-determinism`, seed identifier 1, and 256 generated tokens.
`new2` repeats `new` as a control.
The run date is 2026-10-12.

'''+tables[4]+'''
Every binary exited successfully and produced 256 tokens in each cell.
The repeated `new` runs matched in all cells.

Three pre-run expectations did not hold:

- **CPU, 1,024 prompt tokens:** `new` and `head` match each other. Both first differ from `base` at generated token 83. Their token identifier is 1499, versus 258 for `base`.
- **FPGA, 1,024 prompt tokens:** `new` matches `base`. `head` first differs from both at generated token 83. The token identifier is 258 for `head`, versus 1499 for `new` and `base`.
- **Kill switch, CPU, 1,024 prompt tokens:** `newoff` first differs from `new` at generated token 247. The token identifiers are 624 and 13, respectively.

The 8,192-token CPU cell matches across all reported pairs.
These results do not establish general token identity with main or with the parent.

Different floating-point addition orders are a possible explanation for the mismatches.
Insufficient data: the current head needs a forced-token comparison of logits at token 83 and, for the kill switch, token 247.
That experiment feeds the same token sequence to both binaries and records their output scores.
The earlier parent-PR probe found an exact tie at token 247.
Matching token identifiers here do not prove that the same tie occurred in this binary.
The current investigation remains pending.

## Verification

### Builds and focused tests

The implementation was built at `ea94e95a4e` on the Granite Rapids machine on 2026-10-12.
The environment was the pinned Nix development shell with clang 19.1.7.
The `native` preset used `RelWithDebInfo`, an optimized build with debug information.
Each configuration had a separate checkout.
`BUILD_INGEST_MODELS` controls compilation of generated model plugins.

'''+tables[5]+'''
The test binaries use a fake device, a simulated FPGA.
The `--skip-benchmarks` argument excludes benchmark sections.
Each cell below gives the assertion count followed by the test-case count.

'''+tables[6]+'''
The owner-level conversion case runs with the layout option either enabled or disabled.
The page-state cases use the row-major branch when the option is disabled.
The saved-block assertions in `t_llama_unit` are compiled out in that configuration.
The no-dispatch builds of the AMX-specific tests contain placeholder cases.
They do not exercise AMX dispatch or arithmetic.

The AMX-enabled numerical runs reported no unavailable-hardware skip.
With `TRON_AMX_DISABLE=1`:

- `t_llama_unit` passed 277775 assertions in 66 cases.
- `t_amx_numerics` passed 4108 assertions in 5 cases. Its QK precision, QK identity, and PV precision checks reported AMX unavailable and skipped those checks.

### Mutation checks

- **Saved-row completion:** Reversing the completion comparison caused 1 assertion to fail in 1 case of `t_k_vnni_layout`. The captured token offset was 0. Restoring the source returned the full binary to 1041241 passing assertions in 10 cases.
- **Hardware-operation policy:** Reversing the hardware-policy condition caused 4 of 5115 assertions to fail in the `save_k` case of `t_llama_unit`. Each leaf section detected the wrong converted-block set. Restoring the source returned the full binary to 277775 passing assertions in 66 cases.

These mutations test the completion predicate and operation policy.
They do not test deletion or reordering of the production forward-end conversion call.

### Debian packages

Both packages were built with `make deb` outside Nix on one socket, using 48 build jobs.
The build environment included uv 0.9.5 and the ghcup Haskell toolchain manager.

- **Base:** `2026.10.12-72308ec9-jhan-pr4ci-base`, from `72308ec90c`, built in 915 s. AMX dispatch was enabled. The preset did not set the VNNI K option. Binary inspection found the kill-switch string once and 86 AMX tile instructions.
- **Target:** `2026.10.12-ea94e95a-jhan-pr4ci-target`, from `ea94e95a4e`, built in 953 s. Both options were enabled. Binary inspection found the kill-switch string once and 126 AMX tile instructions.

These build and inspection results do not replace the pending package campaign.

### Generated plugins

This PR changes no file under `ingest/`, the code-generator directory.
The Haskell suite was not repeated for this PR.
It passed 1,363 tests with 0 failures on the parent revision on 2026-10-12.

The generated-plugin check was repeated on this PR's option-on build.
All 19 plugins had equal, positive counts of KV-writing operations, main-side K saves, and helper-side K saves.
No unexpected K-save argument form or `save_k_helper` call was found.
This check compares call forms and counts. It does not establish byte-identical generated files.

'''+tables[7]+'''
### Source checks and host suite

- clang-format 19.1.7 passed with `--dry-run --Werror` on all 10 changed C++ files.
- `git diff --check` passed against the parent revision.
- The diff contained no prohibited `<cassert>` include.
- `make lint-notes` passed. Both new named comments and their references resolved.
- Syntax-only compilation covered 38 configurations with 0 errors. The two no-dispatch configurations of `t_amx_dispatch_dtype` each reported two unused-constant warnings. The remaining 36 configurations had no warnings.

The syntax checks covered all four combinations of the layout and dispatch options for nine translation units.
Those units were the four layout/AMX/model test files, heterogeneous scheduling, the full scheduler, staging, staging-transfer tests, and cache out-of-memory tests.
The AMX kernel source was also checked with dispatch enabled and the layout option both enabled and disabled.

The host suite built every test target with the layout option enabled.
Its result was **93 tests passed, 1 skipped, and 1 failed** in 111.8 s.
The failed test was `t_proxy_llama31`, which reported a missing `t/proxy/.venv` Python environment.
The retained suite summary does not identify the skipped test.
Insufficient data: the individual skip record is needed to confirm whether it was the permitted `t_proxy_lib` exception.
The suite's exit status was a failure. It is not reported as a clean pass.

### Benchmark records

The timing refresh ran on 2026-10-13 at implementation revision `ea94e95a4e`.
The command was `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics t_amx_dispatch_dtype`.
Serving was stopped on the whole test machine.
Commit `e7d06a1267` records the four updated rows for `granite_rapids_6962p`.

'''+tables[8]+'''
The shorter `t_llama_unit` duration is a measurement difference from the earlier record.
Its cause has not been established here.

### CI coverage

The GCP Nix workflow's C++ test configuration enables neither layout nor AMX dispatch.
Its product tests therefore do not cover the shipped combination of these options. [nix/cmake-tron-test-build.nix]
The legacy **CMake and CTest** workflow configures both options ON. [.github/workflows/cmake-single-platform.yml:355–356]
It runs by manual dispatch or through the package-publishing workflow's tag/feature-branch gate. [.github/workflows/publish-deb.yml:55–70]
Issue #4865 tracks the missing default-workflow coverage.
The author accepts this documented limitation for the stack.

This draft has no `Run CI` label.
The GCP Nix product build, host tests, FPGA tests, ingest tests, and benchmarks were skipped.
The following checks passed at `e7d06a1267`:

- Lint, CI machinery contracts, CI machinery tests, Nix Toolchain Contracts, and Fresh Cabal plan. [GCP Nix run 38343432613](https://github.com/positron-ai/tron/actions/runs/38343432613)
- The Debian-repository smoke check. It checks repository access and builds no tron binary. [Run 38343432617](https://github.com/positron-ai/tron/actions/runs/38343432617)
- Slice tooling tests. The benchmark-record change triggered this workflow. The tests use their own fixtures rather than validating these measured row values. [Run 38343432618](https://github.com/positron-ai/tron/actions/runs/38343432618)

GitHub reported no required checks for this PR's current target branch when queried during review.
The passing draft checks are not evidence that the changed product paths ran in CI.

## Open items

- **Token mismatches:** The exact observations and pending forced-token probe are in Token identity. A numerical explanation remains a hypothesis.
- **AMX-disabled slowdown:** The three measured CPU cells lose 2.0 % to 3.4 % TPS against the parent. The deferred-dotter variant and timing trace remain pending. This path also serves hosts without AMX.
- **Package campaign:** The three selected nightly configurations remain pending. The package build alone does not establish serving performance.
- **Hardware-operation fallback:** Before hardware engagement, after card-memory exhaustion, or under a raised engagement threshold, software may score rows from a hardware-designated operation. Blocks completed by short writes remain row-major in those cases. Their scores can differ from packed-reader scores through addition order.
- **Conversion cost:** The main thread converts completed blocks after each pass. Each conversion reads and writes 4 KiB of plane data per block and KV head, with temporary-stack traffic as well. Insufficient data: a `convert_k_blocks` trace is needed to measure its serial cost.
- **EAGLE:** Unit tests cover its storage-view state. No EAGLE model run is reported here.
- **Other shapes and hosts:** There is no throughput measurement at this revision for 128-dimension heads with a query-head ratio other than 4, or for an AMD host.
- **Shared-save limits:** The inherited helper join has a 120 s watchdog. A pass with more than 128 workers stores on the main thread alone.
- **Rollback contract, issue #4444:** The kill switch disables AMX but keeps packed storage and its reader. It does not generally reproduce a build with both options disabled. The open choices are to narrow the documented numerical promise or retain a row-major binary as the deployment rollback artifact.
- **Inherited benchmark fallback:** The legacy workflow initially builds with both options enabled. If transfer to the benchmark job fails, its `make` fallback enables neither option. This PR does not change that fallback.
- **Default CI and nightly comparator:** Issue #4865 tracks option-on coverage. The pending package campaign uses the stack's main revision rather than the latest nightly package.
- **Reference PR:** PR #4424 remains open until its author closes it.

## The stack

This is the fourth and final dependent PR replacing PR #4424.
Each PR targets its predecessor.
Only the first PR is ready for review.

'''+tables[9]+'''
Only this PR's `deb` preset enables VNNI K storage.
The intermediate stack presets keep it disabled.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
'''

# Preserve every numerical table exactly. Whitespace outside tables may change.
new_tables = re.findall(r'(?:^\|.*\n)+', body, re.M)
for table in tables:
    assert table in new_tables, table.splitlines()[0]
assert len(body) < 65536, len(body)
(p / 'body-proposed.md').write_text(body)
print(f'Body: {len(old)} -> {len(body)} characters; all {len(tables)} original tables retained.')
