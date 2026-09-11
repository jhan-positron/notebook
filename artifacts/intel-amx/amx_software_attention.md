# AMX software attention

> Copied from tron PR #3879: `doc/amx_software_attention.md` as of commit 4290402491
> (2026-09-11). The file was removed from the PR in 47f6f2dceb at Ben's request: TRON
> environment variables are to be described in one document (tron issue #4338), and the
> PR's code comments now point at Note [AMX attention dispatch] in
> `h/tron/kernels/amx_attn_iface.hpp` instead. File paths and line numbers below refer to
> the PR tree at that commit. Body verbatim.

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
