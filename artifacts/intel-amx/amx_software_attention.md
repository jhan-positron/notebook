# AMX software attention

> Copied from tron PR #3879: `doc/amx_software_attention.md` as of commit 4290402491
> (2026-09-11). The file was removed from the PR in 47f6f2dceb at Ben's request: TRON
> environment variables are to be described in one document (tron issue #4338), and the
> PR's code comments now point at Note [AMX attention dispatch] in
> `h/tron/kernels/amx_attn_iface.hpp` instead. File paths and line numbers below refer to
> the PR tree at that commit. Body verbatim. The addendum at the end (added 2026-09-15)
> records what tron PR #4424 adds: the build option `TRON_K_VNNI`, and a changed meaning
> of `TRON_AMX_DISABLE=1` on a binary built with that option.

## What it is

`TRON_AMX_DISPATCH` adds an optional AMX fast path to software attention.
It applies to one attention shape: head size 128 with kv_mul 4, on executors
that store activations as bf16 (`tp*`, `perm_tp*`, `host_bf16`). It applies
to one condition per (query, page) pair: a full 64-token page that is visible to
the query in one range and inside the query's sliding window. Such a page is
called dense. For a dense page the dispatch calls the QK kernel once (all 64
scores of the 4 query heads, in tile multiplies) and the PV kernel once. Every
other page, and every other model shape or activation type, runs the existing
AVX-512 dotter loop unchanged.

K stays in its existing row-major storage and V in its existing
pair-interleaved storage. The change adds no persistent copy of either tensor.
The kernels read K as stored (see Note [QK orientation] in
`h/tron/kernels/amx_attn_iface.hpp`).

## Build configuration

`TRON_AMX_DISPATCH` is a CMake option declared in the top-level
`CMakeLists.txt`. Its default is `OFF`; a default build contains none of the
AMX code. Enable it with `-DTRON_AMX_DISPATCH=ON`. The option requires
`TRON_CHUNK_SIZE == 16` (the pair-interleaved V layout the PV kernel reads);
other chunk sizes fail at compile time on purpose. Only
`src/tron/kernels/amx_attn.cpp` receives the AMX compiler flags; every other
file includes only the intrinsics-free interface header.

## Runtime disable contract

The environment variable `TRON_AMX_DISABLE=1`, set before the process starts,
makes `amx_attn_h128g4::available()` return false, so every software-attention
page runs the AVX dotter (hardware attention on FPGA hosts is not affected by
this variable). Only the exact string `1` disables. The availability check
runs once per process and its result is cached, so changing the variable while
the process runs has no effect.

When the variable is set, an AMX-enabled binary stores K and V in the
same layout as a binary built without the option, runs the same AVX dotter
code on every page, and produces the numerics of that clean binary. The
nightly system-test measurements quoted below are same-binary A/B comparisons:
the same binary run twice, once with and once without `TRON_AMX_DISABLE=1`
(the runtron figure quoted first compares two builds). Any change that breaks
this contract must update this document.

AMX-on and AMX-off results are not bit-identical. Both paths multiply bf16
inputs and accumulate in fp32, but they add the products in a different order,
and the AMX PV kernel rounds the softmax weights to bf16 with round to nearest
even where the AVX path truncates. `t/t_amx_numerics.cpp` pins both effects to
an error band computed from the inputs.

## Continuous integration

The CMake CI workflow (`.github/workflows/cmake-single-platform.yml`)
configures with `-DTRON_AMX_DISPATCH=ON`, so the kernels and the dispatch
compile whenever that lane's build step runs (a cached build artifact can skip
it). The kernel tests execute AMX only when the test job
lands on one of the runners with AMX (the Granite Rapids hosts `delphi-17cf`,
`delphi-3bd6` and `delphi-3bda`); on other runners they skip with a warning.
`t/t_amx_dispatch_dtype.cpp` uses CPU fakes for the kernels and runs
everywhere, but it does not execute tile instructions. A green run is
therefore not by itself evidence that AMX executed: record which runner ran
the tests, and require one real-AMX execution per candidate tip. Run the
enabled binary once on a host without AMX as well, to check the fallback.

## How to verify on an AMX host

Configure, build and run the two tests:

```sh
cmake -B gen --preset native -DTRON_AMX_DISPATCH=ON
cmake --build gen --target t_amx_numerics t_amx_dispatch_dtype
./gen/t_amx_numerics      # must NOT print "AMX unavailable on this host"
./gen/t_amx_dispatch_dtype
TRON_AMX_DISABLE=1 ./gen/t_amx_numerics   # now prints the skip warnings
```

For an end-to-end A/B, run the same inference command twice, once with
`TRON_AMX_DISABLE=1`. On hosts with FPGA attention, set `USE_HW_ATTN=0` so
the attention runs in software at all; ingested models default to hardware
attention. Measured before this document was written (all with
`USE_HW_ATTN=0`, on delphi-3bda, a Xeon 6962P host): decode throughput at 8
users and a 8192-token prompt on qwen-3-4b (tp2) was 17.5% higher with AMX
than with a binary built without the option (14.5 tokens/s per user without
the option, 17.0 with AMX); the nightly system tests at a 1024-token prompt,
one binary with and without the switch, showed +13.9% on llama-3.1-8b (tp2)
and +4.5% on qwen-3-4b (tp4). MMLU Pro accuracy on qwen (tp4) moved by +1.5
points, less than the 1.7 points between two unchanged runs of the AMX-off
arm. Those binaries predate the split of the original pull request;
re-measure on the current tip before quoting them for it.

## Addendum (2026-09-15): tron PR #4424, K stored in the VNNI layout

> Added 2026-09-15 from tron PR #4424 (branch `jhan-amx-vnniK`, base `jhan-amx-p0`, the
> PR #3879 branch). The body above is still the verbatim PR #3879 document. This addendum
> records what PR #4424 adds to the build configuration and what it changes in the runtime
> disable contract. File paths refer to the PR #4424 tree.

### What it adds

PR #4424 stores the K cache (the attention keys) of 128-dimension heads in the VNNI layout
at the moment it is written. VNNI (Vector Neural Network Instructions) names the
pair-interleaved layout of the B operand (the right-hand matrix) of the AMX tile multiply:
the two values of one dimension pair sit next to each other, and one 64-byte row holds that
dimension pair for 16 tokens. The AMX QK kernel then reads K without a transpose. V is
unchanged. So the sentence "K stays in its existing row-major storage" in the body holds
only for a binary built without the option below.

### Build flag: `TRON_K_VNNI`

- `TRON_K_VNNI` is a CMake option in the top-level `CMakeLists.txt`. Its default is `OFF`.
  A default build stores K row-major, as before.
- It requires `TRON_AMX_DISPATCH=ON`. Otherwise configure stops with the message
  "TRON_K_VNNI requires TRON_AMX_DISPATCH=ON" (`src/tron/CMakeLists.txt`).
- With the option on, the tron library gets the compile definition `TRON_K_VNNI` as
  PUBLIC. Every translation unit that touches a KV page (a fixed-size 64-token block of the
  key/value cache) must agree on the layout.
- The layout gate is decided at compile time, per model: `k_vnni::layout_on<head_size>`
  is true for head size 128 when `TRON_K_VNNI` is defined, and false otherwise
  (`h/tron/kernels/k_vnni.hpp`). Models with 64-dimension heads (gpt-oss-120b) keep
  row-major K inside a VNNI binary. Models with 128-dimension heads and a kv_mul (query
  heads per KV head) other than 4, such as qwen-3-30b-a3b with kv_mul 8, get the layout
  but not the AMX kernel, so they read it with the AVX-512 reader described below. That
  combination is an open item of the PR (one run showed -5.4% decode throughput).
- The PR adds no environment variable. Two measurement switches, `TRON_K_VNNI_BLOCK` and
  `TRON_K_VNNI_STRIPE`, existed in one development commit (9928cb2849) and were removed
  again (ec1be6dde4). They are not in the PR.

### Runtime disable contract, amended

`TRON_AMX_DISABLE=1` behaves as described in the body: `available()` returns false, and
the AMX kernels do not run. The layout, however, is decided at build time. So on a
`TRON_K_VNNI` binary the kill switch keeps the VNNI layout. The software path then runs
the AVX-512 reader of that layout (`k_vnni::qk_group`, one token per vector lane). The
row-major dotter loop is compiled only for row-major slots (a slot is one layer's K or V
storage) and does not run.

Consequences:

- An AMX-off run of a VNNI binary is an AMX-off run of the same layout. It is not a
  rollback to the row-major binary's numerics. The fp32 add order of the VNNI reader
  differs from the row-major dotter (Note [K VNNI storage] in
  `h/tron/models/kv_cache.hpp`). The "clean-binary numerics" clause of the contract above
  therefore holds only for binaries built without `TRON_K_VNNI`.
- A same-binary A/B (one binary, with and without `TRON_AMX_DISABLE=1`) still isolates
  the AMX kernels. A layout A/B needs two builds, `TRON_K_VNNI=OFF` against `ON`.
- The K stores are not affected by the variable. `save_k` uses the same VNNI store paths
  with and without it.
- Rollback to row-major K is a rebuild with the option off. Nothing at runtime does it.
- Hardware attention on FPGA hosts is not affected by either variable. The FPGA staging
  path (`gof::populate`) materializes one K row per token through `page::get_k_row`. The
  staging bytes and the FPGA memory layout are unchanged. The PR's FPGA-attention smoke run
  produced tokens identical to the base binary (128 of 128).

### Numerics

- The AMX QK kernel reading the VNNI plane is bit-identical to the AMX QK kernel reading
  row-major K. `t/t_amx_numerics.cpp` pins this in the case "AMX QK from the VNNI K plane
  is bit-identical to AMX QK from row-major K" (needs real AMX). So on dense pages a VNNI
  binary with AMX on scores exactly like the PR #3879 binary with AMX on.
- The AVX-512 VNNI reader and the row-major dotter add the same products in a different
  order. `t/t_k_vnni_layout.cpp` ("VNNI K reader does not digress from the row-major
  dotter") bounds the difference to 1e-4 of the absolute-product mass plus 1e-6, for bf16
  and fp32 queries, and checks that the reader never loads a dead token (their storage
  holds NaN poison). In greedy runs this add order shows as a token divergence from the
  base binary on models that use the reader: llama-3.1-8b first differed at token 46,
  qwen-3-30b-a3b at token 5. Both outputs were fluent continuations. This is the same
  numerics contract as the body's AMX-on versus AMX-off paragraph, not a defect.

### Continuous integration

- The CMake CI workflow (`.github/workflows/cmake-single-platform.yml`) configures with
  `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`. The whole test suite of that lane runs on the
  VNNI layout. The weekly `coverage` preset sets neither option and keeps the row-major
  layout covered (`README.ci.md`, section "CMake Flags").
- The `gen/runtron` that the build job bundles as the benchmark artifact is therefore a
  VNNI binary. When the benchmark job falls back to a local rebuild (`make gen/config/test`
  sets neither option) it measures row-major K. The PR lists this mix as a reviewer
  decision.
- Tests added or extended: `t_k_vnni_layout` (new: index-map anchors, store and load
  exactness, block save equals the per-token scatter bit for bit, reader against dotter,
  page copy and append); the bit-identity case of `t_amx_numerics` (executes AMX only on a
  Granite Rapids runner, skips elsewhere); fakes in `t_amx_dispatch_dtype`; the `save_k`
  case of `t_llama_unit` (alone and with two helper threads); emitter checks in
  `ingest/test/LoopyTronSpec.hs` (one `save_k_helper` call per KV-writing operation).
  Cost rows for the three C++ tests are in `config/test-benchmarks.json`
  (granite_rapids_6962p block).

### How to verify on an AMX host

```sh
cmake -B gen --preset native -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON
cmake --build gen --target t_k_vnni_layout t_amx_numerics t_amx_dispatch_dtype t_llama_unit
./gen/t_k_vnni_layout
./gen/t_amx_numerics      # the VNNI bit-identity case must NOT skip
./gen/t_amx_dispatch_dtype
./gen/t_llama_unit
TRON_AMX_DISABLE=1 ./gen/t_amx_numerics   # AMX cases skip; K stays in the VNNI layout
```

Measured for the PR on 2026-09-15 (delphi-3bda, one socket and four FPGA cards, qwen3-4b,
8 users, software attention with AMX in both binaries, `USE_HW_ATTN=0`), VNNI binary
against the PR #3879 binary. TTFT is the time to first token; TPS is generated tokens per
second per user in decode.

| prompt | tp2 TTFT | tp4 TTFT | tp2 decode TPS/user | tp4 decode TPS/user |
|---|---|---|---|---|
| 1024 | -56 ms (3.150 s to 3.095 s) | -77 ms (2.194 s to 2.117 s) | +5.3% (79.7 to 83.9) | +0.2% (103.6 to 103.9; inside the 1 to 3 TPS run-to-run spread) |
| 8192 | -1.37 s (-2.6%) | -0.52 s (-1.7%) | +10.1% | +8.0% |

Save K (the store of one prefill layer's K rows) went from 274 us per layer in the base
binary to 60 to 80 us in the PR, measured with in-process Perfetto traces (the trace
recorder built into tron). The TTFT gain comes from that store. The decode gain comes from
the transpose-free AMX read, and it grows with the prompt length. Re-measure on the merged
tip before quoting these numbers for it.
