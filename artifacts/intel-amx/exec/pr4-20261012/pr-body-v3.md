## Short version

This PR keeps an incomplete 16-token block of K rows (saved key vectors) row-major inside the block's own bytes, and converts it to the VNNI layout at the end of the pass that saves its 16th row. Under hardware attention the blocks that decode completes stay row-major, which recovers the decode throughput loss of issue #4500 in the measured FPGA cells [Performance]. The `deb` preset turns the layout option on in the released package, and this is the last of four PRs [The stack].

## Background

The VNNI-packed layout of the earlier PRs writes one generated token's K row across 64 cache lines, and the FPGA staging gathers it from those lines per generated token. Issue #4500 records the resulting FPGA-attention decode loss for qwen3-4b: 2.2 % at tp2 and 9.7 % at tp4 (runtron, 2026-09-16).

Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp` and Notes [K VNNI storage] and [Row-major blocks under hardware attention] in `h/tron/models/kv_cache.hpp` explain the mechanism.

## Words used here

| Term | Meaning |
|---|---|
| tron, runtron, AMX, AVX-512, FPGA, fp32, Note | tron is the inference program under test and runtron its command-line tool. A Note is a named comment block in the code, and `make lint-notes` checks that every Note reference resolves. AMX (Intel Advanced Matrix Extensions, the tile matrix-multiplication instruction set) and AVX-512 (the CPU's 512-bit vector instruction set) are CPU instruction sets. fp32 is the 32-bit float format. An FPGA (field-programmable gate array) is the accelerator card that runs hardware attention. |
| VNNI layout, VNNI-packed, row-major, plane | The VNNI layout is the right-operand format of AMX tile multiplication: two consecutive dimensions of one token are adjacent in memory, and one 64-byte line holds that dimension pair for 16 consecutive tokens. VNNI-packed means stored this way. Row-major K, the layout `main` uses, is one contiguous row of values per token, 256 bytes (4 cache lines) for a 128-dimension head. A plane is the K storage of one page for one KV head. |
| KV page, block, KV head, storage slot, EAGLE storage view | A KV page is a 64-token unit of the key/value cache, and a block is 16 consecutive tokens of it. A KV head is one key/value head. A storage slot is the physical storage of one persistent K/V storage region. The EAGLE storage view is the separate K/V storage view of EAGLE speculative decoding (a draft-model technique), with its own layout state. |
| the conversion, the forward end, staging | The conversion, `block_to_vnni`, rewrites a complete block in place into the VNNI layout. The staging (`gof::populate`) copies the K and V rows of a GOF (group of four consecutive tokens) into a buffer that DMA (direct memory access) moves to the FPGA card. Cooperative staging is that work done by the pass's worker threads next to the compute. The forward end is the point of a pass after the plugin's `run()` joined its workers and the cooperative staging drained, where `convert_pending_k_blocks` converts the blocks the pass completed. |
| hardware attention, software attention | Hardware attention (FPGA attention) scores the tokens from the engagement point (`hw_attn_engagement_point`, 127 by default, the first position the FPGA scores) on with the FPGA cards, and the CPU scores the positions below it and the tail above the last complete GOF. Software attention scores every token on the CPU. The environment variable `USE_HW_ATTN=0` selects software attention. |
| the option, AMX dispatch, the kill switch, the `deb` preset | `TRON_K_VNNI` (the option, a CMake option) selects VNNI-packed K storage for every 128-dimension head. `TRON_AMX_DISPATCH` (AMX dispatch) compiles the AMX kernels. `TRON_AMX_DISABLE=1` (the kill switch) stops their use at run time. A preset is a named CMake build configuration, and the `deb` preset builds the released Debian package, which the nightly (the nightly test job that installs the newest package on the test machine and runs its benchmark phases) installs and production serving runs. |
| the kernel, the reader, the dotter | The kernel is `qk_vnni_128x4` (PR #4887), the AMX routine that scores one dense page (a full 64-token page the query sees whole) from the VNNI-packed plane. The reader is `k_vnni::qk_group` (PR #4868), the AVX-512 routine that scores a query group (the query heads sharing one KV head) against the converted blocks of a page. The dotter is `main`'s per-token dot product over a row-major row, which also scores the rows of a row-major block through its typed row `row_major_row`. |
| base, new, new2, head, newoff, headoff | runtron builds: `base` from `main` at `72308ec90c` with row-major K and AMX dispatch on, `new` from this branch at `ea94e95a4e` with both options on, `head` from the parent PR #4898 at `dfafd13dce` built like `new`. `new2` repeats `new` (the A/A control). `newoff` and `headoff` run `new` and `head` with the kill switch. |
| TPS, TTFT, tp2, tp4, pass | A pass is one forward computation of the model over its current input. TPS is decode throughput (decode generates one output token per user per pass) in tokens per second per user. TTFT is the time to first token in seconds, the maximum over the users. `tp2` and `tp4` split the model across 2 or 4 devices. |
| mutation check | A deliberate code change that a test must catch. The test's failure proves that the test can fail. |
| qwen3-4b, llama-3.1-8b, gpt-oss-120b | The models of the measurements: Qwen3 with 4 billion parameters, Llama 3.1 with 8 billion, gpt-oss with 120 billion. |
| `t_k_vnni_layout`, `t_llama_unit`, `t_heterogeneous_scheduler`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `t_phase1_integration` | The layout test, the model and cache tests, the scheduler test, the dispatch-per-activation-type test, the AMX numerical-accuracy test, and the staging and dispatch integration test. |

## How to review this PR

The best case against merging is that the PR adds per-slot layout state that every reader and writer of a K block must follow, and turns the option on in the released package while the AMX-off path is slower than the parent's [Performance].

**Where this could be wrong**

**Can a reader see a block in the wrong layout?** Read `h/tron/models/kv_cache.hpp`: every reader and writer of a row takes the layout from the block's converted bit, kept per storage slot next to the saved-row bits, and `note_k_row_saved` is true only when the row's block has all 16 rows saved and is not converted yet. Read `convert_pending_k_blocks` in `h/tron/models/model.hpp`: it runs at the forward end, after the cooperative staging gather (the last reader that can hold a block's rows row-major) has finished. Verification: the `t_k_vnni_layout` cases "page K blocks turn VNNI at the 16th saved row and back when a row is forgotten" and "the EAGLE storage view keeps its own K layout state", and the forward-path case of `t_heterogeneous_scheduler` with its mutation check [Builds and tests]. The ordering after the staging drain is Open [Open items].

**Do page reuse and page copies keep the state consistent with the bytes?** Read `k_forget_row` in `h/tron/models/kv_cache.hpp`: when a new token takes a page offset, a converted block with live rows below it is converted back first when its storage is readable, then the bits from that offset up are dropped in every storage slot. Page copies (`copy_storage_slot`) carry the bits with the rows and convert partial destination blocks back and forth as needed. Verification: the `t_k_vnni_layout` cases "row-major tail block converts to the VNNI layout and back, bit for bit", "forgetting a row acts on every slot's own block" and "page append carries the K layout state with the rows".

**Which path scores a page, and can the hardware-attention policy leave a token unscored?** Read `k_layout_dense` in `h/tron/models/self_attention.hpp`: the kernel runs only when every block of the page is converted. Otherwise the reader scores the converted blocks and the dotter scores the row-major rows. Read the policy in `save_k` (`h/tron/models/model.hpp`): when hardware attention scores the operation's K (`cached_operation_uses_hw`), the pass records no row bits for the rows of a run shorter than a block and queues no conversion. Whole-block saves still write and record the VNNI layout. Verification: the two hardware-attention sections of the `save_k` case of `t_llama_unit`, the hardware-policy mutation check, and the token-identity and FPGA-attention cells [Verification].

**What you might decide differently**

**Should blocks completed under hardware attention stay row-major?** Choice: never convert them. The conversion would cost a serial main-thread copy per completed block and KV head for blocks the kernel never reads. Cost accepted: when software scores such an operation, the dotter scores those blocks, and a score can differ by fp32 add order alone. Alternative: convert anyway. Check: the FPGA-attention cells [Performance]. The fallback cost is Open. Reviewers decide.

**Should the deferred-dotter change join this PR?** Choice: not in this PR. The probe build of [Open items] recovers part of the AMX-off loss. Alternative: a further commit with the CPU cells run again. Open. Reviewers decide.

**Should the released package turn the option on now?** Choice: the `deb` preset sets `TRON_K_VNNI` on next to `TRON_AMX_DISPATCH`. Every other preset stays off, and the layout does not depend on AMX. Alternative: release the package with the option off and enable it after a nightly cycle. Check: the package campaign [Performance] and the CI gap [Builds and tests]. Open. Reviewers decide.

## Verification

Implementation `ea94e95a4e`, measured on 2026-10-12 and 2026-10-13. The head `175b1837b9` adds four benchmark-record rows (`e7d06a1267`) and the forward-path test case. Granite Rapids machine (Intel Xeon 6962P, 8 FPGA cards), `nix develop` (the project's build shell), clang 19.1.7, the `native` preset, `RelWithDebInfo`. Binaries: `base`, `new`, `new2`, `head`, `newoff`, `headoff` [Words used here].

### Builds and tests

Unit tests with a fake device (a simulated FPGA) in three configurations: the option on with AMX dispatch, on without it, and off.

- Pass in all three: `t_k_vnni_layout` (10 cases), `t_llama_unit` (66 cases) and `t_heterogeneous_scheduler` (3 cases, 4 at the head). At the head its forward-path case passes with the option on and off. The option-on build also passes `t_llama_unit` under the kill switch.
- Pass with dispatch on: `t_amx_dispatch_dtype` (1 case) and `t_amx_numerics` (5 cases). Without dispatch both are `SUCCEED` placeholders. Under the kill switch three AMX checks of `t_amx_numerics` report AMX unavailable and skip.
- `t_phase1_integration` (64 cases) passes in both option-on configurations (the option-off build targets the other five tests only).

Mutation checks: reversing the completion comparison fails 1 assertion of `t_k_vnni_layout`. Reversing the hardware-policy condition fails 4 of 5115 assertions in the `save_k` case of `t_llama_unit`. Removing `convert_pending_k_blocks()` from the forward fails the forward-path case.

Clean at the head: clang-format on the 11 changed C++ files, `git diff --check`, and a syntax-only compile in 38 configurations with 0 errors (two no-dispatch configurations warn about unused constants). At `ea94e95a4e`: no prohibited `<cassert>` header, `make lint-notes`, and `make test-host` (option-on build) passing 93 tests, with `t_proxy_lib` skipped and `t_proxy_llama31` failed, both for the missing `t/proxy/.venv`. Four cost rows (test timing records) in `config/test-benchmarks.json` are refreshed.

The default CI workflow (GCP Nix) builds with both options off [nix/cmake-tron-test-build.nix], so the option-on paths run only in the manual legacy CMake lane and here (issue #4865).

### Token identity

qwen3-4b, tp2, 1 user, temperature 0, `--pay-for-determinism` (sums in a fixed order), 256 generated tokens, 2026-10-12. Identical: all 256 tokens match. Only `new2` must match `new`, and it does in every cell. `head` can differ where the dotter scores blocks the parent's reader scored. `newoff` and `base` are informational [issue #4444].

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
- With the kill switch on both binaries (`newoff` against `headoff`) this PR is 3.4 %, 2.9 % and 2.0 % slower in TPS than the parent, beyond the band, and its TTFT at prompt 8,192 tokens is 453 ms higher, beyond the 0.21 s band. That comparison changes storage, conversion and the scoring of unconverted blocks together [Open items].

Whole-machine package campaign, 2026-10-13 (record `pr4ci-20261012`): the `deb` package of `72308ec90c` against that of `ea94e95a4e` through the nightly's benchmark harness under FPGA attention, four runs (base, target, target, base) of 10 rounds. A cell is resolved at a paired t (a paired-difference statistic) of at least 2.26 in magnitude over the 20 round pairs and a difference of at least 1 % (TTFT also at least 1 ms). llama-3.1-8b at tp2 with 32 users and prompt 4,096 tokens keeps the gain that PR #4424's campaign of 2026-10-09 resolved: +5.2 % TPS (paired t +53.81) against +4.8 % then. llama-3.1-8b at tp2 and gpt-oss-120b at tp4 (8 users, prompt 1,024 tokens), TTFT and peak memory show no resolved change.

## Open items

**AMX-disabled slowdown.** This path also serves hosts without AMX. A probe build that constructs a page's dotters at its first row-major row (`ca6456b7dc` on `ea94e95a4e`, 2026-10-13) recovers +2.3 % TPS (beyond the band), +1.6 % and +0.2 % (inside it) with the kill switch in the three CPU cells. It costs nothing measurable with AMX on. It leaves 1.5 % (beyond the band), 1.5 % and 1.0 % (inside it) of TPS against the parent unexplained. Settled by: a Perfetto trace (a timing trace) of the attention spans.

**The conversion.** No mutation checks its ordering after the staging drain (settled by a fixture with cooperative staging). Its serial main-thread cost, 4 KiB of plane data (plane: one page's K storage per KV head) per block and KV head, is not measured (settled by a trace of the `convert_k_blocks` span).

**Token differences and the rollback contract. Reviewers decide. [Issue #4444]** This head's results and its probe are under Token identity. The status after the stack, which rounding is preferable at the near ties, and the two rollback-contract choices are tracked in issue #4444.

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
