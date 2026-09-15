# AMX software attention

> Copied from tron PR #3879: `doc/amx_software_attention.md` as of commit 4290402491
> (2026-09-11). The file was removed from the PR in 47f6f2dceb at Ben's request: TRON
> environment variables are to be described in one document (tron issue #4338), and the
> PR's code comments now point at Note [AMX attention dispatch] in
> `h/tron/kernels/amx_attn_iface.hpp` instead. File paths and line numbers in the body refer to
> the PR tree at that commit. Body verbatim. The addendum at the end (added 2026-09-15)
> records what tron PR #4424 adds: the build option `TRON_K_VNNI`, and the part of the
> `TRON_AMX_DISABLE=1` contract (same dotter code, clean-binary numerics) that no longer
> holds on a binary built with that option.

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

> Added 2026-09-15 from tron PR #4424. tron is the inference program this document is
> about. The PR branch is `jhan-amx-vnniK`. Its base is `jhan-amx-p0`, the PR #3879 branch.
> The body above is still the verbatim PR #3879 document. This addendum records what
> PR #4424 adds to the build configuration and which part of the runtime disable contract
> no longer holds. File paths in the addendum refer to the PR #4424 tree.

**Short version.** PR #4424 adds the CMake option `TRON_K_VNNI` (default OFF). With the
option on, the K cache of 128-dimension heads is stored in the AMX VNNI layout, and
`TRON_AMX_DISABLE=1` no longer restores the row-major binary's reader or numerics. On
qwen3-4b the PR measured a decode gain of +5.3% (tp2, prompt 1024) and +10.1% (tp2,
prompt 8192) with a lower time to first token.

### Words used here

- K, V: the attention keys and values kept in the KV cache. A KV page is a fixed-size
  64-token block of that cache. A slot is one persistent K and V storage region of the
  cache, one per layer or shared between layers.
- 128-dimension heads: attention heads whose key vector has 128 values. Row-major K: one
  row of 128 values per token, the layout of PR #3879 and of `main`.
- AMX: Intel Advanced Matrix Extensions, the CPU's tile-multiply instruction set.
  AVX-512: the CPU's 512-bit vector instruction set.
- VNNI (Vector Neural Network Instructions): the pair-interleaved layout of the B operand
  (the right-hand matrix) of the AMX tile multiply. The two values of one dimension pair
  sit next to each other, and one 64-byte row holds that dimension pair for 16 tokens.
  The VNNI plane is the 16 KiB K storage of one page in that layout.
- QK: the query-key score product. The dotter is the per-token AVX-512 dot-product loop
  of the software attention path. A dense page is a full 64-token page entirely visible
  to the query, the only case the AMX kernel handles.
- kv_mul: query heads per KV head. `TRON_AMX_DISPATCH`: the CMake option of PR #3879,
  described in the body, that compiles the AMX kernels. The kill switch:
  `TRON_AMX_DISABLE=1`.
- bf16: 16-bit brain floating point, the storage format of K and V. fp32: 32-bit float,
  the accumulator format.
- `save_k`: the function in `h/tron/models/model.hpp` that writes one pass's K rows into
  the KV cache. Save K is its span in the trace. Prefill is the phase that processes the
  prompt. Decode is the token-generation phase after it.
- base binary: the PR #3879 binary (row-major K). runtron: tron's command-line inference
  tool. delphi-3bda: the shared Intel Granite Rapids (the CPU generation with AMX) test
  machine, a Xeon 6962P host. tp2, tp4: the model split over 2 or 4 FPGA
  (field-programmable gate array) cards.
- TTFT: time to first token. TPS: generated tokens per second per user in decode. A smoke
  run is 1 user, greedy (temperature 0, always the top-scoring token, deterministic
  reductions), 128 generated tokens.

### What it adds

PR #4424 stores the K cache of 128-dimension heads in the VNNI layout at the moment it is
written. The AMX QK kernel then reads K without a transpose. V is unchanged. So the
sentence "K stays in its existing row-major storage" in the body holds only for a binary
built without the option below.

### Build flag: `TRON_K_VNNI`

- `TRON_K_VNNI` is a CMake option in the top-level `CMakeLists.txt`. Its default is `OFF`.
  A default build stores K row-major, as before.
- It requires `TRON_AMX_DISPATCH=ON`. Otherwise configure stops with the message
  "TRON_K_VNNI requires TRON_AMX_DISPATCH=ON" (`src/tron/CMakeLists.txt`).
- With the option on, the tron library gets the compile definition `TRON_K_VNNI` as
  PUBLIC (every target that links the library inherits it). Every translation unit that
  touches a KV page must agree on the layout.
- The layout gate is decided at compile time, per model. `k_vnni::layout_on<head_size>`
  is true for head size 128 when `TRON_K_VNNI` is defined, and false otherwise
  (`h/tron/kernels/k_vnni.hpp`). Models with 64-dimension heads (gpt-oss-120b) keep
  row-major K inside a VNNI binary. Models with 128-dimension heads and a kv_mul other
  than 4, such as qwen-3-30b-a3b with kv_mul 8, get the layout but not the AMX kernel.
  They read the layout with the AVX-512 reader described below. That combination is an
  open item of the PR (one run showed -5.4% decode TPS).
- The PR adds no environment variable. Two measurement switches, `TRON_K_VNNI_BLOCK` and
  `TRON_K_VNNI_STRIPE`, were added in one development commit (9928cb2849) and removed two
  commits later (ec1be6dde4). They are not in the PR's head tree.

### Runtime disable contract, amended

`TRON_AMX_DISABLE=1` behaves as described in the body: `available()` returns false, and
the AMX kernels do not run. The layout, however, is decided at build time. So on a
`TRON_K_VNNI` binary the kill switch keeps the VNNI layout. The software path then runs
the AVX-512 reader of that layout (`k_vnni::qk_group`, one token per vector lane). The
row-major dotter loop is compiled only for row-major slots and does not run.

Consequences:

- The body's contract has three clauses: the same layout as a binary built without
  `TRON_AMX_DISPATCH`, the same AVX dotter code on every page, and the numerics of that
  clean binary. On a `TRON_K_VNNI` binary the second and third clauses no longer hold. The
  kill switch keeps the VNNI layout, runs `k_vnni::qk_group` instead of the dotter, and
  produces the VNNI reader's numerics. The fp32 add order of that reader differs from the
  row-major dotter (Note [K VNNI storage] in `h/tron/models/kv_cache.hpp`). An AMX-off run
  of a VNNI binary is therefore an AMX-off run of the same layout, not a rollback to the
  row-major binary's numerics.
- A same-binary A/B (one binary, with and without `TRON_AMX_DISABLE=1`) still isolates
  the AMX kernels. A layout A/B needs two builds, `TRON_K_VNNI=OFF` against `ON`.
- The K stores are not affected by the variable. `save_k` uses the same VNNI store paths
  with and without it.
- Rollback to row-major K is a rebuild with the option off. Nothing at runtime does it.
- Hardware attention on FPGA hosts is not affected by the build option or by the variable.
  The FPGA staging path (the code that copies K and V rows into the buffers the FPGA reads,
  `gof::populate`) materializes one K row per token through `page::get_k_row`. The staging
  bytes and the FPGA memory layout are unchanged. The PR's FPGA-attention smoke run
  produced the same 128 of 128 tokens as the base binary.

### Numerics

- The AMX QK kernel reading the VNNI plane is bit-identical to the AMX QK kernel reading
  row-major K. `t/t_amx_numerics.cpp` pins this in the case "AMX QK from the VNNI K plane
  is bit-identical to AMX QK from row-major K". The case executes on any host with AMX
  and skips elsewhere. So on dense pages a VNNI binary with AMX on scores exactly like the
  base binary with AMX on.
- The AVX-512 VNNI reader and the row-major dotter add the same products in a different
  order. `t/t_k_vnni_layout.cpp` ("VNNI K reader does not digress from the row-major
  dotter") bounds the difference to 1e-4 of the absolute-product mass (the sum of the
  absolute values of the 128 products) plus 1e-6. It runs the check for bf16 and fp32
  queries. It also checks that the reader never loads a dead token (a token outside the
  live mask). The storage of dead tokens holds NaN poison (a not-a-number fill that a
  stray load would spread into the scores).
- In greedy runs this add order shows as a token divergence from the base binary on models
  that use the reader: llama-3.1-8b first differed at token 46, qwen-3-30b-a3b at token 5.
  Both outputs were fluent continuations. This is the same numerics contract as the
  body's AMX-on versus AMX-off paragraph, not a defect.

### Continuous integration

- The CMake CI workflow (`.github/workflows/cmake-single-platform.yml`) configures with
  `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON`. The whole test suite of that lane runs on the
  VNNI layout. The weekly `coverage` preset sets neither option and keeps the row-major
  layout covered (`README.ci.md`, section "CMake Flags").
- The `gen/runtron` that the build job bundles as the benchmark artifact is therefore a
  VNNI binary. When the benchmark job falls back to a local rebuild (`make gen/config/test`
  sets neither option) it measures row-major K. The PR lists this mix as a reviewer
  decision.
- Tests added or extended:
  - `t_k_vnni_layout` (new): index-map anchors, store and load exactness, block save
    equals the per-token scatter bit for bit, reader against dotter, page copy and append.
  - `t_amx_numerics`: the bit-identity case above.
  - `t_amx_dispatch_dtype`: fakes (stand-in kernels used only by the test) for the VNNI
    kernel entry points.
  - `t_llama_unit`: the `save_k` case, alone and with two helper threads.
  - `ingest/test/LoopyTronSpec.hs`: checks on the code generator's output, one
    `save_k_helper` call per KV-writing operation.
- Cost rows (the timing rows the CI slice check requires for every registered test) are
  in `config/test-benchmarks.json`, granite_rapids_6962p block: a new row for
  `t_k_vnni_layout` and refreshed rows for `t_llama_unit` and `t_amx_numerics`. The
  `t_amx_dispatch_dtype` row is unchanged.

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

### Measurements

The table was measured for the PR on 2026-09-14 and 2026-09-15 (UTC) on half of
delphi-3bda (one CPU socket and four of the eight FPGA cards; a tp2 cell uses two of the
cards, a tp4 cell all four). Model qwen3-4b, 8 users, software attention with AMX in both
binaries (the campaign scripts set `USE_HW_ATTN=0`; the PR body says "sw attention with
AMX"). It compares the VNNI binary against the base binary. Deltas come from the
unrounded means.

| prompt | tp2 TTFT | tp4 TTFT | tp2 decode TPS/user | tp4 decode TPS/user |
|---|---|---|---|---|
| 1024 | -56 ms (3.150 s to 3.095 s) | -77 ms (2.194 s to 2.117 s) | +5.3% (79.7 to 83.9) | +0.2% (103.6 to 103.9, inside the 1 to 3 TPS run-to-run spread) |
| 8192 | -1.37 s (-2.6% of 53.369 s) | -0.52 s (-1.7% of 30.487 s) | +10.1% | +8.0% |

Save K went from 274 us per prefill layer in the base binary to 60 to 80 us in the PR,
measured with in-process Perfetto traces (the trace recorder built into tron). The TTFT
gain comes from that store. The decode gain grows with the prompt length. The PR
attributes it to the transpose-free AMX read. No measurement in the PR isolates that
read. Re-measure on the merged tip before quoting these numbers for it.
