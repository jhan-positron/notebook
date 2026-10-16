## Short version

This PR keeps an incomplete 16-token block of K rows (saved key vectors) row-major inside the block's own bytes, and converts it to the VNNI layout at the end of the pass that saves its 16th row. Under hardware attention the blocks that decode completes stay row-major, which recovers the decode throughput loss of issue #4500 in the measured FPGA cells. The `deb` preset turns the layout option on in the released package, and this is the last of four PRs.

## Background

The VNNI-packed layout of the earlier PRs writes one generated token's K row across 64 cache lines, and the FPGA staging gathers it from those lines per generated token. Issue #4500 records the resulting FPGA-attention decode loss for qwen3-4b: 2.2 % at tp2 and 9.7 % at tp4 (runtron, 2026-09-16).

Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp` and Notes [K VNNI storage] and [Row-major blocks under hardware attention] in `h/tron/models/kv_cache.hpp` explain the mechanism.

## Words used here

| Term | Meaning |
|---|---|
| KV page, block, KV head, storage slot, EAGLE storage view | A KV page is a 64-token unit of the key/value cache, and a block is 16 consecutive tokens of it. A KV head is one key/value head. A storage slot is the physical storage of one persistent K/V storage region. The EAGLE storage view is the separate K/V storage view of EAGLE speculative decoding (a draft-model technique), with its own layout state. |
| the conversion, the forward end, staging | The conversion, `block_to_vnni`, rewrites a complete block in place into the VNNI layout. The staging (`gof::populate`) copies the K and V rows of a GOF (group of four consecutive tokens) into a buffer that DMA (direct memory access) moves to the FPGA card. Cooperative staging is that work done by the pass's worker threads next to the compute. The forward end is the point of a pass after the plugin's `run()` joined its workers and the cooperative staging drained, where `convert_pending_k_blocks` converts the blocks the pass completed. |
| the option, AMX dispatch, the kill switch, the `deb` preset | `TRON_K_VNNI` (the option, a CMake option) selects VNNI-packed K storage for every 128-dimension head. `TRON_AMX_DISPATCH` (AMX dispatch) compiles the AMX kernels. `TRON_AMX_DISABLE=1` (the kill switch) stops their use at run time. A preset is a named CMake build configuration, and the `deb` preset builds the released Debian package, which the nightly (the nightly test job that installs the newest package on the test machine and runs its benchmark phases) installs and production serving runs. |
| the kernel, the reader, the dotter | The kernel is `qk_vnni_128x4` (PR #4887), the AMX routine that scores one dense page (a full 64-token page the query sees whole) from the VNNI-packed plane. The reader is `k_vnni::qk_group` (PR #4868), the AVX-512 routine that scores a query group (the query heads sharing one KV head) against the converted blocks of a page. The dotter is `main`'s per-token dot product over a row-major row, which also scores the rows of a row-major block through its typed row `row_major_row`. |
| base, new, new2, head, newoff, headoff, baseoff | runtron builds: `base` from `main` at `72308ec90c` with row-major K and AMX dispatch on, `new` from this branch at `ea94e95a4e` with both options on, `head` from the parent PR #4898 at `dfafd13dce` built like `new`. `new2` repeats `new` (the A/A control). `newoff`, `headoff` and `baseoff` run `new`, `head` and `base` with the kill switch. |

## How to review this PR

**Can a reader see a block in the wrong layout?**
- Read `h/tron/models/kv_cache.hpp`: every reader and writer of a row takes the layout from the block's converted bit, kept per storage slot next to the saved-row bits, and `note_k_row_saved` is true only when the row's block has all 16 rows saved and is not converted yet.
- Read `convert_pending_k_blocks` in `h/tron/models/model.hpp`: it runs at the forward end, after the cooperative staging gather (the last reader that can hold a block's rows row-major) has finished.
- Verification: the `t_k_vnni_layout` cases "page K blocks turn VNNI at the 16th saved row and back when a row is forgotten" and "the EAGLE storage view keeps its own K layout state", and the forward-path case of `t_heterogeneous_scheduler` with its mutation check [Builds and tests].
- Open: the ordering after the staging drain, settled by a fixture with cooperative staging [Open items].

**Do page reuse and page copies keep the state consistent with the bytes?**
- Read `k_forget_row` in `h/tron/models/kv_cache.hpp`: when a new token takes a page offset, a converted block with live rows below it is converted back first when its storage is readable, then the bits from that offset up are dropped in every storage slot.
- Page copies (`copy_storage_slot`) carry the bits with the rows and convert partial destination blocks back and forth as needed.
- Verification: the `t_k_vnni_layout` cases "row-major tail block converts to the VNNI layout and back, bit for bit", "forgetting a row acts on every slot's own block" and "page append carries the K layout state with the rows".

**Which path scores a page, and can the hardware-attention policy leave a token unscored?**
- Read `k_layout_dense` in `h/tron/models/self_attention.hpp`: the kernel runs only when every block of the page is converted. Otherwise the reader scores the converted blocks and the dotter scores the row-major rows.
- Read the policy in `save_k` (`h/tron/models/model.hpp`): when hardware attention scores the operation's K (`cached_operation_uses_hw`), the pass records no row bits for the rows of a run shorter than a block and queues no conversion. Whole-block saves still write and record the VNNI layout.
- Verification: the two hardware-attention sections of the `save_k` case of `t_llama_unit`, the hardware-policy mutation check, and the token-identity and FPGA-attention cells [Verification].

## Verification

Implementation `ea94e95a4e`, measured on 2026-10-12, 2026-10-13 and 2026-10-14. The head `4d64013dff` adds four benchmark-record rows (`e7d06a1267`), the forward-path test case (`175b1837b9`) and three commits of comment and style edits with no behaviour change (`8ad54a13b1`, `d0e6f816dd`, `4d64013dff`).

### Builds and tests

Unit tests with a fake device (a simulated FPGA) in three configurations: the option on with AMX dispatch, on without it, and off.

- Pass in all three: `t_k_vnni_layout` (10 cases), `t_llama_unit` (66 cases) and `t_heterogeneous_scheduler` (3 cases, 4 from `175b1837b9`). At `175b1837b9` its forward-path case passes with the option on and off. The option-on build also passes `t_llama_unit` under the kill switch.
- Pass with dispatch on: `t_amx_dispatch_dtype` (1 case) and `t_amx_numerics` (5 cases). Without dispatch both are `SUCCEED` placeholders. Under the kill switch three AMX checks of `t_amx_numerics` report AMX unavailable and skip.
- `t_phase1_integration` (64 cases) passes in both option-on configurations (the option-off build targets the other five tests only).

Mutation checks: reversing the completion comparison fails 1 assertion of `t_k_vnni_layout`. Reversing the hardware-policy condition fails 4 of 5115 assertions in the `save_k` case of `t_llama_unit`. Removing `convert_pending_k_blocks()` from the forward fails the forward-path case.

Clean at the head: clang-format on the 11 changed C++ files, `git diff --check`, and a syntax-only compile in 38 configurations with 0 errors and 0 warnings. At `ea94e95a4e`: no prohibited `<cassert>` header, `make lint-notes`, and `make test-host` (option-on build) passing 93 tests, with `t_proxy_lib` skipped and `t_proxy_llama31` failed, both for the missing `t/proxy/.venv`. Four cost rows (test timing records) in `config/test-benchmarks.json` are refreshed.

The default CI workflow (GCP Nix) builds with both options off [nix/cmake-tron-test-build.nix], so the option-on paths run only in the manual legacy CMake lane and here (issue #4865).

### Token identity

qwen3-4b, tp2, 1 user, temperature 0, `--pay-for-determinism`, 256 generated tokens. Only `new2` must match `new`, and it does. Issue #4444 tracks every difference.

| Cell | new vs base | new vs head | newoff vs new |
|---|---|---|---|
| CPU attention, prompt 1,024 tokens | first difference at generated token 83 | identical | first difference at generated token 247 |
| CPU attention, prompt 8,192 tokens | identical | identical | identical |
| FPGA attention, prompt 1,024 tokens | identical | first difference at generated token 83 | identical |

A forced-token probe on 2026-10-13 (record `p83-20261013`) shows each difference as a near tie. At generated token 83, `base` (CPU) and `head` (FPGA) have an exact tie between vocabulary tokens 258 and 1499, which `new` scores 1 to 2 ulps apart (a ulp is one bf16 step at the score's size). At generated token 247 the kill switch reverses a 1-ulp margin.

### Performance

qwen3-4b, 8 users, 256 generated tokens, 3 repetitions in alternating order, 2026-10-12 (per-binary values: record `pr4-20261012`). The band is twice the larger of the two binaries' sample standard deviations over the 3 repetitions, never smaller than 0.4 TPS or 0.15 s, and a difference beyond it counts as a change.

| Pair, decode TPS | CPU tp2, prompt 1,024 | CPU tp2, prompt 8,192 | CPU tp4, prompt 1,024 | FPGA tp2, prompt 1,024 | FPGA tp4, prompt 1,024 |
|---|---|---|---|---|---|
| new vs base | +4.7 %, beyond | +9.4 %, beyond | +2.4 %, beyond | +0.6 %, inside | -0.3 %, inside |
| new vs head | -0.7 %, inside | +0.2 %, inside | -0.5 %, inside | +2.5 %, beyond | +12.1 %, beyond |

With AMX on, TTFT is inside its band against the parent in all three CPU cells, and every FPGA-attention TTFT comparison is inside its 0.15 s band. No FPGA run lost hardware attention.

- Under FPGA attention this PR is inside the band against `main`, where the parent loses 1.9 % and 11.0 %.
- With the kill switch on both binaries, this PR against `main` (`newoff` against `baseoff`, 2026-10-14, record `pr4off-20261014`) is inside the band in TPS in all three CPU cells: +0.7 %, +2.7 % (0.39 TPS, under the 0.40 TPS floor) and -0.5 %. Its TTFT at prompt 8,192 tokens is 4.98 s lower, beyond the 0.44 s band, and inside the band in the other two cells.
- With the kill switch on both binaries, this PR against the parent (`newoff` against `headoff`) is slower in TPS: 3.4 %, 2.9 % and 2.0 % on 2026-10-12, and 3.3 %, 2.7 % and 0.5 % on 2026-10-14, all beyond the band except the last. Its TTFT at prompt 8,192 tokens is 453 ms and 587 ms higher, beyond the band (0.21 s and 0.20 s). That comparison changes storage, conversion and the scoring of unconverted blocks together (issue #4934).

Whole-machine package campaign, 2026-10-13 (record `pr4ci-20261012`): the `deb` package of `72308ec90c` against that of `ea94e95a4e` through the nightly's benchmark harness under FPGA attention, four runs (base, target, target, base) of 10 rounds. A cell is resolved at a paired t (a paired-difference statistic) of at least 2.26 in magnitude over the 20 round pairs and a difference of at least 1 % (TTFT also at least 1 ms). llama-3.1-8b at tp2 with 32 users and prompt 4,096 tokens keeps the gain that PR #4424's campaign of 2026-10-09 resolved: +5.2 % TPS (paired t +53.81) against +4.8 % then. llama-3.1-8b at tp2 and gpt-oss-120b at tp4 (8 users, prompt 1,024 tokens), TTFT and peak memory show no resolved change.

## Open items

Issue #4934 is tracking the decode slowdown against the parent with the kill switch.

**Hardware-attention fallback cost. Reviewers decide.** Blocks that decode completes under hardware attention are never converted. That saves a serial main-thread copy per completed block and KV head for blocks the kernel never reads. When software scores such an operation, the dotter scores those blocks, and a score can differ by fp32 add order alone. The alternative is to convert anyway. Check: the FPGA-attention cells [Performance].

**The option on in the released package. Reviewers decide.** The `deb` preset sets `TRON_K_VNNI` on next to `TRON_AMX_DISPATCH`. Every other preset stays off, and the layout does not depend on AMX. The alternative is to release the package with the option off and enable it after a nightly cycle. Check: the package campaign [Performance] and the CI gap [Builds and tests].

**The conversion.** No mutation checks its ordering after the staging drain (settled by a fixture with cooperative staging). Its serial main-thread cost, 4 KiB of plane data (plane: one page's K storage per KV head) per block and KV head, is not measured (settled by a trace of the `convert_k_blocks` span).

Issue #4444 is tracking the token identity issue.

**Not measured at this head.** An EAGLE model run, kv_mul (query heads per KV head) other than 4, an AMD host, and the latest nightly package as the campaign's base.

## The stack

These four PRs, each based on the preceding one, replace PR #4424, which stays open as a reference.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #4868 | `jhan-vnnik-1-layout` on `main` | VNNI-packed K layout, owner and views, row store, reader, FPGA gather, tests | ready for review |
| 2 | #4887 | `jhan-vnnik-2-amx` on PR #4868 | AMX QK (query-key score) kernel `qk_vnni_128x4`, query packer `pack_q_rows_128x4` | draft until PR #4868 merges |
| 3 | #4898 | `jhan-vnnik-3-shared-save` on PR #4887 | Shared 16-token block saves by the main thread and idle helper threads | draft until PR #4887 merges |
| 4 | #4901 | this PR, `jhan-vnnik-4-tail-block` on PR #4898 | Row-major tail block, row-major policy under hardware attention (issue #4500), option on in the `deb` preset | draft until PR #4898 merges |

The option stays off in every preset until this PR's `deb` preset.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


