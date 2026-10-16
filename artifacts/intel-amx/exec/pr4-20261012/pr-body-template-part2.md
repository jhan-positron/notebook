
## Measurements

The measurements have three parts. The runtron cells compare decode TPS and TTFT of this PR's binary against the block-save PR's binary and against `main`, under CPU attention and under FPGA attention. The whole-machine campaign compares the released package built from this PR against the package built from `main` for three nightly configurations. The token-identity runs compare the generated tokens of five arms.

### Runtron cells

Configurations:

- `base`: `main` at `72308ec90c`, built as runtron with row-major K and AMX dispatch on.
- `new`: this branch at `{{HEAD_SHORT}}`, with the option and AMX dispatch on.
- `head`: the block-save PR at `{{PR3_SHORT}}`, built the same way as `new`.
- `newoff` and `headoff`: those two binaries with the kill switch.

The experiment ran on {{E_DATE}}:

- Model: qwen3-4b, at tp2 and at tp4.
- Load: 8 users and 256 generated tokens.
- CPU cells: CPU attention, selected by `USE_HW_ATTN=0`; tp2 with prompt lengths 1,024 and 8,192 tokens, and tp4 with prompt length 1,024 tokens; all five arms.
- FPGA cells: FPGA attention, `USE_HW_ATTN` unset as in the released package; tp2 and tp4 with prompt length 1,024 tokens; the arms `base`, `new` and `head`.
- Repetitions: 3, with the binaries run in alternating order.
- Allocation: the whole Granite Rapids test machine with production serving stopped (the tp4 cells need their four FPGA cards and 256 huge pages, the large memory pages reserved for the run's buffers; the FPGA cells need their cards).

The decision band is twice the larger of the two binaries' standard deviations. It is never smaller than 0.4 TPS for throughput or 0.15 s for TTFT. Bands are shown rounded to 0.01 TPS and 0.01 s. A difference beyond that band counts as a change. Paired t uses the 3 repetitions. "Inside" and "beyond" refer to the band.

Each parenthesized value is the sample standard deviation over the 3 repetitions. TPS has units of tokens/s/user. Both TTFT and its standard deviation have units of seconds. The FPGA table's last column is the mean count per run of the "lose HW attention" warning (a shard that got no card memory and was scored on the CPU instead); 0 means every shard ran on the cards.

CPU attention:

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) |
|---|---|---|---|
{{ARM_ROWS_CPU}}

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
{{PAIR_ROWS_CPU}}

FPGA attention:

| Cell | Binary | TPS (tokens/s/user) | TTFT (s) | HW-attention losses per run |
|---|---|---|---|---|
{{ARM_ROWS_FPGA}}

| Cell | Pair | TPS difference (paired t) | TTFT difference (paired t) | Band (TPS / TTFT) |
|---|---|---|---|---|
{{PAIR_ROWS_FPGA}}

### The FPGA-attention decode of qwen3-4b (new vs base, head vs base, new vs head)

This is the claim of issue #4500. Under FPGA attention the layout without the tail block stores and stages 64 lines per generated token where `main` stores and stages 4. The records cited in Background measured that loss at -2.2 % (tp2) and -9.7 % (tp4) with runtron and at -5.0 % and -11.0 % with the nightly's own layout. The expectation here: `head` against `base` shows a loss of that order at both parallelisms. `new` against `base` is inside the band or within a few percent. `new` against `head` is the recovery. The tp4 cell has a large spread in every record of this layout, so a tp4 difference inside the band is not read as a change, and the standard deviations are reported. No earlier record runs this PR's content at 8 users on one engine under FPGA attention: the measured pairs decide.

{{FPGA_PAIRS}}

The claim holds in both cells. `head` loses 1.9 % of decode TPS against `base` at tp2 and 11.0 % at tp4, beyond the bands. `new` is inside the band against `base` in both cells: +0.6 % at tp2 and -0.3 % at tp4. `new` against `head` is the recovery: +2.5 % at tp2 and +12.1 % at tp4, beyond the bands. TTFT is inside the 0.15 s band in every FPGA pair. No run lost hardware attention.

The tp4 loss of `head`, 11.0 %, repeats the 9.7 % of the runtron record and the 11.0 % of the nightly-layout record within 1.3 percentage points. The tp2 loss, 1.9 %, is within 0.3 percentage points of the runtron record's 2.2 %.

### The CPU cells against the block-save PR (new vs head)

A 1,024-token prompt fills whole blocks, so prefill takes the block save as in the block-save PR and no block waits for the forward end. TTFT is expected inside the band. In decode a run of one token now stores 4 whole lines into the row-major tail block instead of 64 scattered dwords. The block whose 16th row a pass saves is converted at the forward end: one 4 KiB copy per block, KV head and layer, once per 16 steps per user, on the main thread. The page being filled takes the software loop (the reader for its converted blocks, the dotters for the tail) instead of the AMX kernel until all its blocks are converted. The expectation is TPS inside the band at tp2. The tp4 cell is reported with its spread.

{{TPS_HEAD}}
{{TTFT_HEAD}}

Decode TPS is inside the band in all three cells. This meets the expectation. The largest difference is -0.7 % at tp2 prompt length 1,024 tokens, paired t -2.4, inside the 0.66 TPS band. TTFT is inside the band in all three cells. At tp2 prompt length 8,192 tokens the difference is +231 ms, inside the 0.30 s band. The prefill of that cell takes about 52 s, and 231 ms is 0.4 % of it.

So the tail block, the forward-end conversion and the software loop on the page being filled cost nothing beyond the bands with AMX on in these cells. The AMX-off pair below measures the same code without the AMX kernel.

### This PR against `main` (new vs base)

The block-save PR measured, against the same `main`, TPS +5.1 %, +9.1 % and +3.4 % and TTFT -57 ms, -827 ms and -75 ms at tp2 prompt length 1,024 tokens, tp2 prompt length 8,192 tokens and tp4 prompt length 1,024 tokens. [PR #4898, Measurements] The expectation is the same within the bands.

{{AGAINST_MAIN}}

`new` is above `main` in decode TPS in all three cells, beyond the bands. TTFT is below `main` in all three cells: inside the 0.15 s band at the two 1,024-token cells, and beyond the 0.30 s band at 8,192 tokens, where the prefill is 697 ms (1.3 %) shorter.

The block-save PR's TPS gains repeat within 0.4 percentage points at tp2: +4.7 % and +9.4 % here against +5.1 % and +9.1 % in its run. The tp4 cell is 1.0 percentage point lower here, +2.4 % against +3.4 %. That cell has the largest spread of the three: `base` sd 0.49 TPS and `new` sd 0.39 TPS. The session control below moves the block-save PR's own binary by 0.5 percentage points in the same cell between the two sessions. The TTFT gains repeat within 130 ms: -56 ms, -697 ms and -73 ms here against -57 ms, -827 ms and -75 ms.

### The kill switch inside this PR (newoff vs new)

The store is the same with or without the switch. The scoring paths differ from the block-save PR's: with the switch, the reader scores the converted blocks and the dotter scores the row-major tail rows. Without it, the AMX kernel reads a page only when all its blocks are converted. The block-save PR measured, for its own binary, TPS -11.1 %, -18.0 % and -7.9 % and TTFT +768 ms, +65.7 s and +268 ms in the three CPU cells. [PR #4898, Measurements] That is a provisional expectation. The measured pair decides.

{{KILL_SWITCH}}

The three cells show the AMX page path's gain, as in the block-save PR. TPS is -13.6 %, -20.6 % and -9.3 % and TTFT is +780 ms, +66.0 s and +275 ms under the switch, beyond the bands. The TTFT values repeat the block-save PR's +768 ms, +65.7 s and +268 ms within 0.3 s. The TPS gaps are 2.5, 2.6 and 1.4 percentage points wider than that PR's -11.1 %, -18.0 % and -7.9 %.

The wider gaps are the AMX-off arm's loss of the next pair, not a gain of the AMX-on arm: `new` is inside the band against `head` above.

### The two AMX-off arms (newoff vs headoff)

Both arms disable AMX. `headoff` scores every relevant token of a packed slot through the reader: the block-save PR has no row-major tail path. `newoff` scores a converted block through the reader and an unconverted block through the dotter. So this pair measures the storage, the conversion and the scoring of unconverted blocks together. It does not isolate the store. The expectation is inside the band for TPS and TTFT. A difference beyond the band needs the Save K span, the `convert_k_blocks` span and the attention spans of a Perfetto trace (tron's timing trace) of the same decode workload for both arms.

{{AMX_OFF}}

TPS is beyond the band in all three cells. `newoff` is 3.4 %, 2.9 % and 2.0 % below `headoff`, with paired t -12.4, -45.2 and -4.4. This does not meet the expectation. TTFT is inside the 0.15 s band at the two 1,024-token cells. At 8,192 tokens TTFT is +453 ms, beyond the 0.21 s band. The prefill of that cell takes about 117 s under the switch, and 453 ms is 0.4 % of it.

The cause is not measured. The Perfetto trace named above was not taken. Hypothesis, labelled: the software loop of `self_attention.hpp` builds the array of `operation_kv_mul` dotters for every page and KV head it visits of a VNNI slot, before it knows whether the slot holds a row-major block. The generic dotter converts its 128-value query row to fp32 at construction. The block-save PR's loop built no dotter for a VNNI slot. With the switch, every page of every layer takes that loop. A second hypothesis, labelled: the per-token tests of the block bit and of the row-major branch inside the loop.

The measurement that would decide: the same three cells with a variant that builds the dotters of a VNNI slot at its first row-major row only, with the switch (against `newoff` and `headoff`) and with AMX on (against `new` and `head`). That variant is prepared and not measured at the time of writing. [Open items]

### The block-save PR against `main` in this session (head vs base)

This pair repeats the block-save PR's claim in the same session as the other pairs: TPS +5.1 %, +9.1 % and +3.4 % and TTFT -57 ms, -827 ms and -75 ms on 2026-10-12. [PR #4898, Measurements] A deviation beyond the bands would say that the machine's speed changed between the two sessions. Such a change would limit what every other pair of this run can show.

{{HEAD_BASE}}

The block-save PR's TPS claim repeats within 0.5 percentage points: +5.4 %, +9.2 % and +2.9 % here against +5.1 %, +9.1 % and +3.4 % in its own run. Its TTFT claim repeats within 101 ms: -65 ms, -928 ms and -78 ms here against -57 ms, -827 ms and -75 ms. Each of those differences is inside the band of its cell. So no machine-speed change between the two sessions limits the other pairs of this run.

### The whole-machine campaign (base deb vs target deb)

The campaign re-runs the nightly's perf code by hand on the whole Granite Rapids test machine, with the packages installed through the machine's package manager and the engines started by platformd, as the nightly does.

- Packages: the base deb (`main` at `72308ec90c`, version `{{W_BASE_VERSION}}`) and the target deb (this branch at `{{HEAD_SHORT}}`, version `{{W_TARGET_VERSION}}`). Both were built on the test machine with the `make deb` recipe of the repository.
- Configurations: three of the nightly's 14, chosen for this PR: llama-3.1-8b at tp2 with 8 users and prompt length 1,024 tokens, llama-3.1-8b at tp2 with 32 users and prompt length 4,096 tokens, and gpt-oss-120b at tp4 with 8 users and prompt length 1,024 tokens. FPGA attention as shipped. The llama-3.1-8b rows test that this PR keeps the decode and prefill gains of PR #4424; the gpt-oss-120b row tests parity.
- Passes: base, target, target, base ({{W_PASSES}}), 10 rounds of one request per user each. TPS is captured over generated tokens 896 to 1024. The paired t pools the rounds of both pass pairs.
- Dates: {{W_DATES}}.
- Memory: VmHWM and VmRSS of every rinzler process, summed over the engines, read after every provisioning and every benchmark.

A cell is resolved when its target differs from its base beyond noise: the paired t is at least 2.26 in magnitude and the difference is at least 1 % (for TTFT also at least 1 ms). TPS has units of tokens/s/user; TTFT is in ms; memory is in MiB.

| Cell | Base TPS (sd over passes) | Target TPS | Delta | Paired t (rounds) | Resolved | Base TTFT | Target TTFT | Delta | TTFT resolved | Base VmHWM | Target VmHWM | Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
{{W_ROWS}}

{{W_TEXT}}

{{W_MEM_TEXT}}

### Token identity

Setup ({{SMOKE_DATE}}):

- runtron with qwen3-4b, tp2, and 1 user.
- Temperature setting 0, `--pay-for-determinism`, random seed identifier 1, and 256 generated tokens.
- CPU attention at prompt lengths 1,024 and 8,192 tokens.
- FPGA attention at prompt length 1,024 tokens.
- Binaries: `new`, `new2` (the A/A repeat), `newoff`, `head`, and `base`.

Acceptance rules:

- Every binary exits with status 0 (success) and produces exactly 256 generated tokens.
- `new2` must match `new` for all 256 generated tokens in each cell.
- CPU attention: `new` must match `base` for all 256 generated tokens. This is the correctness claim of the PR for the measured cells: the dotter scores the blocks a decode step completes until the forward end converts them, a converted block holds the same values, and the generated tokens therefore equal `main`'s. The claim is for the measured cells: a converted block of a partial page is scored by the reader, whose fp32 add order differs from the dotter's.
- FPGA attention: `new` must match `head` for all 256 generated tokens. The tail block changes no FPGA-scored token.
- `newoff` against `new` is expected identical in every cell. The block-save PR and the kernel PR measured a first difference at generated token 247 at CPU prompt length 1,024 tokens for their binaries (an exact tie of the two best tokens, decided by the AMX-versus-reader numerics). With the tail block the scored sequence of that cell changes, so the tie is not expected to recur.

| Cell | new vs new2 | new vs base | new vs head | newoff vs new | head vs base |
|---|---|---|---|---|---|
{{SMOKE_ROWS}}

Outcome of the acceptance rules:

{{IDENTITY_TEXT}}

## Verification

Build provenance:

- Machine and date: Granite Rapids, Intel Xeon 6962P with AMX, {{BUILD_DATE}}.
- Revision: `{{HEAD_SHORT}}`, three commits on the block-save PR at `{{PR3_SHORT}}`. The head of this PR, `{{PUSHED_SHORT}}`, adds one commit to it: the cost rows of `config/test-benchmarks.json` measured below, a measurement record and no source. The measurements and the checks below are at `{{HEAD_SHORT}}`. The block-save PR is based on the kernel PR at `0ee8671d35`, the kernel PR on the layout PR at `82d05e94be`, and the layout PR includes `main` at `72308ec90c`.
- Environment: `nix develop`, the project's pinned build shell.
- Compiler: clang version 19.1.7.
- Preset: `native` (the Ninja build runner, the clang-19 compiler, the ccache compiler cache, the lld linker, build type `RelWithDebInfo`). The AVX-512 flags are explicit in `src/tron/CMakeLists.txt` and do not depend on the preset or on the build host.
- Build type: `RelWithDebInfo`, an optimized build with debug symbols.
- Each of the 3 configurations used a separate worktree.

`BUILD_INGEST_MODELS` controls compilation of the models produced by the ingest pipeline (the project's model conversion step).

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | {{BUILD_PR4}} s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | {{BUILD_PR4ND}} s |
| option off | OFF | ON | OFF | the 6 tests below without `t_phase1_integration` | {{BUILD_PR4RM}} s |

`t_heterogeneous_scheduler` tests scheduling across different attention geometries. `t_k_vnni_layout` tests the packed layout, its row and block operations, the tail-block conversion, the page's layout state and the reader. `t_phase1_integration` tests staging (the copy of K and V into buffers read by the FPGA) and dispatch integration.

The following unit-test binaries passed with a fake device (a simulated FPGA). `--skip-benchmarks` excluded their benchmark sections. Each result gives assertions / test cases.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
{{TEST_ROWS}}

`t_k_vnni_layout` reports 10 test cases in every build: the cases that work on an owner run whatever the option is, and the page-state cases take the row-major branch with the option off (no row is recorded and no block converts). The `save_k` case of `t_llama_unit` runs its four sections in every build; with the option off it runs the row-major store and the block checks are compiled out. The identity case of `t_amx_numerics` (the kernel PR's bit-identity check of the AMX kernel) ran on real AMX in the option-on build and in the option-off build. Neither `t_amx_numerics` run printed an "AMX unavailable" line. The option-on build without AMX dispatch compiles `t_amx_dispatch_dtype` as a placeholder; its two file-scope constants for the dispatch sections are then unused, and the compiler reports two `-Wunused-const-variable` warnings. The build has no `-Werror`, and the constants are kept as they are in the reviewed tree.

Kill-switch results in the option-on build:

{{KILLSWITCH_LINES}}

Two mutation checks ran in the option-on worktree.

- The page state: the completion test of `note_k_row_saved` in `kv_cache.hpp` was inverted (`==` to `!=` in the comparison of the block's 16 row bits). Every row of an incomplete block then reports "complete" and the 16th row reports "not complete", so no block is converted through the row path. The page-state case of `t_k_vnni_layout`, run alone, then fails at its first `REQUIRE`. {{MUTATION1}} With the file restored, `t_k_vnni_layout` passes again with {{RESTORED1}}.
- The hardware-attention policy: the condition `if (!cached_operation_uses_hw(binding.operation))` of `save_k_impl` in `model.hpp` lost its negation. Rows are then recorded only for hardware-scored operations. The `save_k` case of `t_llama_unit`, run alone, then fails in `check_blocks` in each of its four leaf sections: the one-thread section, the other-operation section and the three-thread section expect blocks 0 and 3 converted and find block 3 only, and the hardware-scored section expects block 3 only and finds blocks 0 and 3. {{MUTATION2}} With the file restored, `t_llama_unit` passes again with {{RESTORED2}}.

The two Debian packages of the campaign were built on the test machine with `make deb` (outside nix, uv 0.9.5 and the ghcup toolchain on the path, 48 jobs on one socket):

{{DEB_LINES}}

The Haskell suite is not repeated: this PR changes no file under `ingest/`, so the code generator is untouched. The suite ran on the block-save PR's head on 2026-10-12 (1,363 tests passed, 0 failed). The generated-plugin check of the block-save PR was repeated on this PR's option-on build: for each of the 19 generated plugins, the `save_v` calls, the main-side `save_k` calls and the helper-side `save_k` calls are equal and positive, no `save_k` call has another argument tail, and `save_k_helper` does not occur. The check compares call forms and counts, not bytes. Its verdict line: {{PLUGIN_PASS}}

| Plugin | KV-writing operations | Main-side `save_k` calls | Helper-side `save_k` calls |
|---|---|---|---|
{{PLUGIN_ROWS}}

All of these checks pass at `{{HEAD_SHORT}}`:

- clang-format version 19.1.7, the source formatter, with `--dry-run --Werror` on all 10 changed C++ files.
- `git diff --check`, the whitespace check, against the block-save PR's head.
- A search for the prohibited `<cassert>` header in the diff.
- {{LINT_NOTES}}

Syntax-only compilation used clang version 19 with the product's compile flags. It covered 38 configurations with 0 errors. 36 configurations had 0 warnings; the two AMX-dispatch-off configurations of `t_amx_dispatch_dtype` reported the two unused-constant warnings named above.

- All 4 combinations of AMX dispatch on/off and the option on/off for 9 translation units: `t_llama_unit`, `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `heterogeneous_scheduler_compile` (heterogeneous scheduling compilation), `scheduler/full.cpp` (the full scheduler), `gof.cpp` (staging), `t_gof_dma` (staging DMA, direct memory access transfers), and `t_kv_oom_subcases` (out-of-memory cases).
- `kernels/amx_attn.cpp` (the AMX kernels) with dispatch on and the option on/off.

The compiler flag is `-fsyntax-only`.

Host test suite (`make build-test-host` and `make test-host` with a fake device, in the option-on worktree, on one socket of the test machine with production serving stopped):

{{HOST_LINES}}

The suite permits only the existing Python-environment exceptions: `t_proxy_lib`, a proxy-library test, may skip, and `t_proxy_llama31`, a Llama proxy test, may fail. Both lack the virtual environment `t/proxy/.venv`, the isolated Python dependency directory.

Cost rows: `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics t_amx_dispatch_dtype` ran on the whole test machine with serving stopped, in the option-on worktree, and rewrote the four rows of the `granite_rapids_6962p` block of `config/test-benchmarks.json`. The commit `{{PUSHED_SHORT}}` carries them.

{{BENCH_LINES}}

### CI coverage

The GCP Nix test build enables neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI`. [nix/cmake-tron-test-build.nix]

- In that configuration the tail-block cases that work on an owner still run. The page-state cases take the row-major branch: no row is recorded and no block converts. The `save_k` sections run the row-major store with the block checks compiled out. The dense gate is not compiled.
- The option-on paths run on the Granite Rapids test machine, as reported above, and in the legacy CMake lane, which compiles both options on. [.github/workflows/cmake-single-platform.yml]
- The `deb` preset now compiles the option into the released package. The required CI therefore tests a configuration that the package does not ship. The whole-machine campaign of this PR and the nightly after the merge test the shipped one.
- At review time, this PR is a draft without the `Run CI` label. GCP Nix skips its product test jobs (Build Tron, Test host, Test FPGA and Test ingest) on a draft without that label. Its lint and infrastructure checks (Lint, CI machinery contracts, CI machinery tests, Nix Toolchain Contracts, Fresh Cabal plan) passed in [run 38343432613](https://github.com/positron-ai/tron/actions/runs/38343432613) at `{{PUSHED_SHORT}}`. The separate Debian smoke check (`deb-smoke.yml`, a workflow that checks authenticated access to the Debian package repository and builds no tron binary) passed in [run 38343432617](https://github.com/positron-ai/tron/actions/runs/38343432617). The Slice tooling check (`slice.yml`) ran because the cost-row commit changes `config/test-benchmarks.json`. It tests the tooling with its own fixtures and does not read the row values. It passed in [run 38343432618](https://github.com/positron-ai/tron/actions/runs/38343432618).
- The author explicitly accepts this limitation for this PR. Issue #4865 tracks enabling both options in the required test build.

## Open items

**Decode-completed blocks under software attention for a hardware operation.**

- When the software scores a range although the operation is a hardware one (before the engagement point, a prompt shorter than 128 tokens, a shard without card memory, a raised engagement point), the blocks that decode completed stay row-major and the dotter scores them, where the conversion would have let the AMX kernel score a page of them. Every reader takes its layout from the block bit, and no stored token is missed.
- Both layouts hold the same K values. The fp32 add order of the dotter and of the reader differs, so a score can differ by that add order alone, and so can a generated token. [Note [Row-major blocks under hardware attention], h/tron/models/kv_cache.hpp]

**The forward-end conversion's serial cost.**

- Every block that a pass completes through short runs is converted on the main thread at the forward end: one 4 KiB read and write per block, KV head and layer, once per 16 decode steps per user.
- Not measured here. The measurement that would decide it: the `convert_k_blocks` span of a Perfetto trace of a decode workload.

**The storage-view (EAGLE) state is tested by the unit tests only.**

- The EAGLE case of `t_k_vnni_layout` and the copy semantics of the page are the evidence. No EAGLE model is run here.

**128-dimension heads with kv_mul other than 4 query heads.**

- The kernel serves kv_mul 4 only. Other groups retain the packed layout and use the reader for the converted blocks and the dotter for the tail rows. The store does not depend on kv_mul.
- Decode TPS of those groups under runtron is not measured at `{{HEAD_SHORT}}`. No AMD host is measured at this head either.

**The join watchdog and the worker cap.**

- The shared save of the block-save PR is unchanged here: the main thread aborts the process when a shared store's join has not completed 120 s after its first clock read, and a pass with more than 128 workers stores on the main thread alone.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]**

- With the option on, the kill switch gives an AMX-off run of the same binary: the reader scores the converted blocks and the dotter scores the tail rows. It does not reproduce the tokens of a clean binary, meaning a build with both options off, in general. In the measured cells this PR's tokens equal `main`'s under FPGA attention and at CPU prompt length 8,192 tokens, and equal the block-save PR's under CPU attention at prompt length 1,024 tokens, where both first differ from `main` at generated token 83. [Measurements, Token identity; Open items, Token identity]
- {{NEWOFF_NEW_V}}
- {{DIVERGENCE_V}}
- The rollback contract (the documented promise of what the kill switch restores) promises AMX off with the same AVX dotter and clean-binary numerical results. A packed binary with the switch runs the reader for its converted blocks. [Item 4 of Note [AMX attention dispatch], h/tron/kernels/amx_attn_iface.hpp]
- Issue #4444 records two choices:
  1. Accept the narrower rollback contract. Add "with `TRON_K_VNNI` off" to item 4.
  2. Keep a row-major binary as the deployment rollback artifact. Document that requirement.

**Token identity against `main` and against the block-save PR. Reviewers decide.**

- The expectation before the run: `new` equals `base` in the CPU cells and `head` in the FPGA cell. The measured pattern differs. At CPU prompt length 1,024 tokens `new` equals `head`, and both first differ from `base` at generated token 83 (token id 1499 against 258). At FPGA prompt length 1,024 tokens `new` equals `base`, and `head` first differs from both at token 83. At CPU prompt length 8,192 tokens every pair is identical over 256 tokens. The A/A repeat is identical in every cell. [Measurements, Token identity]
- Hypothesis, labelled: no defect. Dense pages are scored bit-identically in every arm (the identity case of `t_amx_numerics`: the VNNI AMX kernel equals the row-major AMX kernel), so only a partial page can differ. The block-save PR and this PR both score the converted blocks of a partial page with the reader, where `main` uses the dotter, and the two fp32 add orders differ. A near tie of the two best tokens decided by that order hits both PRs alike: the CPU cell. The block-save PR scores the row-major tail with the reader and this PR with the dotter, as `main` does. A tie decided there hits the block-save PR alone: the FPGA cell. Whether such a tie occurs within 256 tokens depends on the token stream of the cell.
- The measurement that would confirm or reject it: the forced-run probe of the kernel PR (every step's logits, with the arms force-fed the same token sequence) at token 83, for `new` against `base` in the CPU cell and for `head` against `new` in the FPGA cell. A near tie of the two best tokens, decided by the add order, confirms it. A large logit gap rejects it. Not run at `ea94e95a4e`. This item is under investigation at the time of posting: the probe is scheduled on the test machine, and this description is updated with its result.
- `newoff` against `new` first differs at generated token 247 in the CPU cell at prompt length 1,024 tokens, with the token ids of the block-save PR's and the kernel PR's records (624 against 13). The expectation that this tie would not recur assumed a changed token stream. The stream equals the block-save PR's in that cell, as the `new` against `head` row shows, so the kernel PR's exact tie recurs. [PR #4887, Measurements]
- The claim this PR makes for the measured cells is the measured statement: under FPGA attention this PR's generated tokens equal `main`'s where the block-save PR's differ. Under CPU attention they equal the block-save PR's at prompt length 1,024 tokens and `main`'s at 8,192 tokens.

**Decode TPS with AMX off, against the block-save PR. Reviewers decide.**

- `newoff` against `headoff` is -3.4 %, -2.9 % and -2.0 % TPS in the three CPU cells, beyond the bands, and +453 ms TTFT at prompt length 8,192 tokens, beyond the 0.21 s band. [Measurements, The two AMX-off arms] With AMX on, `new` against `head` is inside the band in the same cells.
- The hypotheses and the deciding measurement are stated under that pair. The variant that builds the dotters of a VNNI slot at its first row-major row only is prepared and not measured at `ea94e95a4e`. This item is under investigation at the time of posting: the measurement of that variant against `new`, `newoff`, `head` and `headoff` in the three CPU cells is scheduled on the test machine after the whole-machine campaign, and this description is updated with its result. If the variant recovers the difference, the change joins this PR as a further commit, the chain's checks and the three cells are re-run on the new head, and this body says so.
- The AMX-off path is the kill switch's path and the path of a host without AMX. The shipped package runs the AMX kernel on the Granite Rapids hosts.

**Benchmark binary mismatch, inherited from PR #3879. Reviewers decide.**

- The legacy CMake workflow's `build` job compiles runtron with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`. It transfers that binary to its `benchmark` job.
- After a failed transfer, the benchmark job builds runtron through `make`. That build sets neither option. It benchmarks row-major K without AMX kernels.
- PR #3879 introduced the mismatch for AMX dispatch. The layout PR added the layout option to the same configure line. This PR changes neither.
- The GCP Nix benchmark configuration is unchanged. Its binary has neither option enabled.

**CI coverage gap. [Issue #4865]**

- When the GCP Nix product tests run, their configuration runs the owner-level tail-block cases, the page-state cases on the row-major branch and the `save_k` case on the row-major store, and never compiles the dense gate. The `deb` preset ships the option. The build and test evidence of this PR is the Granite Rapids run reported under Verification and the whole-machine campaign under Measurements. [CI coverage above]

**The campaign's base package is built from the stack's `main`, not from the nightly's.**

- The base deb is `main` at `72308ec90c`, the `main` inside the layout PR, so that every comparison of the stack has the same base. The nightly's package of the day carries the commits `main` gained since then. What that package would have measured instead: Insufficient data. The resume form of the campaign with the nightly's package as its base would give it.

**PR #4424 stays open as the reference.**

- The stack is complete with this PR. PR #4424 remains open until its author closes it.

## The stack

PR #4424 uses branch `jhan-amx-vnniK` and adds 4,054 lines. Four dependent PRs replace it. Each is based on the preceding PR. The stack is complete with this PR. PR #4424 remains open as a reference until it is closed.

| Order | PR branch and base | What it adds | State |
|---|---|---|---|
| 1 | PR #4868, `jhan-vnnik-1-layout`, based on `main` | Packed K layout, owner and views, per-row store, reader, FPGA staging gather, the option disabled in presets, and tests | ready for review |
| 2 | PR #4887, `jhan-vnnik-2-amx`, based on PR #4868 | The AMX QK kernel `qk_vnni_128x4` and query packer `pack_q_rows_128x4`. A bit-identity test compares with the row-major kernel. | draft until PR #4868 merges |
| 3 | PR #4898, `jhan-vnnik-3-shared-save`, based on PR #4887 | Shared saves of 16-token blocks, transposed in registers and written as whole cache lines by the main thread and idle helper threads. This provides PR #4424's TTFT improvement. | draft until PR #4887 merges |
| 4 | this PR, `jhan-vnnik-4-tail-block`, based on PR #4898 | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention (FPGA attention) addresses issue #4500. The `deb` package-build preset enables the option in the released package. | draft until PR #4898 merges |

The option is on in the `deb` preset of this PR and off in every other preset. The intermediate states of the stack do not enter production through those presets.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
