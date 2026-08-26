# Intel AMX in tron

Design of AMX-leveraged features. The first feature is AMX software attention
(PR #3879); subsequent PRs that leverage AMX (other attention geometries, MoE
router, prefill-shaped work) extend this document. Design decisions are
anchored in source with the Notes convention: grep the bracketed note names
cited below.

All measurements: delphi-3bda (Xeon 6 6962P, 2 sockets).

## AMX introduction

### What it is

A per-physical-core matrix-multiply unit (TMUL) with eight 1 KB tile
registers. One `TDPBF16PS` computes `C[16x16] (fp32) += A[16x32] x B[32x16]`
(bf16 inputs, fp32 accumulation): 512 MAC/cycle/core, 8x the two AVX-512
BF16 FMA ports. The TMUL is a separate unit; in Intel's documented model it
is fed via the port-5 issue slot, so AVX-512 loses one of its two FMA ports
only while TDP\* execute.

### Instruction set

The instructions relevant to this work in one table (Intel 64 and IA-32
Architectures Optimization Reference Manual ch. 20, "opt manual" below;
measured = 6962P,
back-to-back cycles/op):

| instruction | function | spec lat/thr (cycles) | measured |
|---|---|---|---|
| `LDTILECFG` | load 64 B config for all 8 tiles | 204 / - | 182-216 |
| `TILERELEASE` | reset tiles + config to INIT | 13 / - | ~15 |
| `TILELOADD` | load one tile (<= 1 KB) | 45 / 8 | 8.4 (L1) |
| `TILESTORED` | store one tile to L1 | - / 16 | 16.1 |
| `TILEZERO` | zero one tile | 16 / 0 | 0.5 |
| `TDPBF16PS` | the matmul | 52 / 16 | 16.2-16.4 |

One `LDTILECFG`/`TILERELEASE` pair per work region, where a work region is one
`apply_page_range` call (per attention worker, kv_head and page-range section,
and again for the pending pass); the pair itself costs ~229 cycles measured
(`begin_region()`/`end_region()`). 6962P also has AMX-INT8 and AMX-FP16; tron's
KV cache is bf16, so only `TDPBF16PS` is used.

### Throughput reality
- A full TDP has ~16-cycle reciprocal throughput; a same-C accumulation
  chain sustains that rate (accumulation adds no stall).
- The recurring system cost is the frequency license, not stalls: ~8%
  core clock on the busy core in the quiet-slot run, ~4% at 8-user service
  scale with package
  power flat - energy per token measured 15-22% LOWER with AMX on.
- Setup cost is small and amortized: `arch_prctl` ~0.9 us once per process, XFD
  first-use trap 4-9 us once per thread, ~229 cycles per work region.

### VNNI B-operand layout

The dot-product instructions never multiply single numbers: per step, each
fp32 accumulator lane consumes one 32-bit element (= two adjacent bf16) from
A and one 32-bit element (= two adjacent bf16) from B. A's pairs come free
(its reduction axis runs along the row). B's reduction axis runs down a
column, so B must be stored with conceptual rows 2k and 2k+1 zipped: stored
row k holds the pair `(B[2k][n], B[2k+1][n])` for every output column n.
Feeding a plain row-major B produces wrong results by construction, not a
slowdown. tron's V storage is already pair-interleaved over adjacent tokens
(the PV reduction axis) at `TRON_CHUNK_SIZE == 16` - the AMX PV kernel
consumes it as-is, zero repack. K is canonical row-major; the mirror feature
below derives the VNNI form of K.

### Precision

Both engines are bf16-in / fp32-accumulate end to end (AVX: `VDPBF16PS`;
AMX: `TDPBF16PS`). For finite, non-subnormal inputs the admissible A/B
deltas are exactly two: fp32 accumulation order, and the PV weight rounding
mode (the AVX path truncates fp32->bf16 weights; AMX converts with
round-to-nearest-even - a deliberate choice, recorded with its fallback in
`Note [AMX attention dispatch]`). Guardrails in-tree:
`t/t_amx_numerics.cpp` pins the kernels to the AVX path inside that envelope
(QK vs the real dotter; PV vs exact references; mirror QK bit-identical to
canonical AMX). System-level: over 956 forced-generation steps, AMX-vs-AVX
max per-step TVD 0.054 (repo golden-test criterion: <= 0.05 with outlier cap
0.30 at <= 10%; 1/956 outlier), and both arms sit at identical distance from
HF fp32 references.

### What AMX requires from the system

- CPU flags (CPUID 7.0 EDX bits 22/24) + OS enabling (XCR0[18:17]); Linux
  >= 5.16. Feature bits, not vendor strings: non-AMX hosts, including AMD,
  take the AVX path.
- One `arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)` once per process,
  from whichever thread first calls available()
- 8 KB XTILEDATA per thread in the XSAVE area once used; `TILERELEASE` when
  leaving a region re-enables the XSAVE init optimization.
- One AMX thread per physical core (Intel guidance). tron pins one attention
  worker per logical CPU from an explicit core list, so this holds only when the
  configured list contains no two SMT siblings of one physical core; tron does
  not check that.
- Toolchain: `-mamx-tile -mamx-bf16` confined to one translation unit
  (`src/tron/kernels/amx_attn.cpp`); the interface header is intrinsics-free.

## AMX software attention (PR #3879)

### Target

Software attention - the `apply_page_tok` QK and PV inner loops. The main
target is forced software attention (`USE_HW_ATTN=0`), where attention
compute is the decode wall at long context (a linear fit of the pre-AMX decode
step time against context length - 3.43 ms + 0.734 us x tokens, qwen-3-4b tp2
on delphi-3bda, 2026-08-18 - attributes 6.0 of 9.4 ms per step at ctx 8192 to
the context-proportional term, i.e. ~64%).
The FPGA-attention flow benefits too, with no additional code: the dispatch
sits inside the software page loop, which hardware mode still uses for its
software-required subset (positions below 127, sliding-window and software-only
layers, hw-ineligible configurations). The dispatch has no `uses_hw` check.
See `Note [AMX attention dispatch]`.

Safety chain: compile-time opt-in (`TRON_AMX_DISPATCH`, default OFF;
`src/tron/CMakeLists.txt`, which also enforces that `TRON_AMX_K_MIRROR`
requires it) ->
runtime detection (`amx_attn::available()`) -> env kill switch
(`TRON_AMX_DISABLE=1`, measured at clean-binary speed) -> per-page dense
predicate. Everything that fails any gate runs the unchanged AVX path.

### Model

Primary: `ingested-qwen-3-4b-instruct-2507-tp2`. All comparisons are
same-binary kill-switch A/Bs against the true clean binary. The measured
numbers (qwen decode/prefill/energy, and the llama-3.1-8b, mixtral-8x7b and
gpt-oss generalization runs, gpt-oss being the ineligible-geometry control)
are in the PR #3879 description.

### Mirror layout

Two QK formulations ship (`Note [Mirror orientation]`):

- **canonical-K** (default): `S^T = K . Q^T`, K consumed exactly as stored;
  the score tile round-trips through memory and is transposed: 1250 ns/page
  against 686 ns for the mirror at width 4 (one L2-resident page, 6962P,
  2026-08-19); the gap includes transpose work and score traffic, was not
  component-isolated, and is NOT a raw tile-store-to-vector-load forwarding
  stall (measured directly).
- **mirror** (opt-in, `TRON_AMX_K_MIRROR`): `S = Q . K^T` with no
  transposing store; needs K in the VNNI B-operand layout - a second,
  derived copy of K (`k_vnni`).

The mirror copy lives in a book-owned PARALLEL ARENA, not inside `kv_block`
(`Note [K mirror parallel arena]`): an in-block third plane measurably broke
prefetch streams (LLC miss 51%->85%, AVX fallback -4..-8%, ~9% tax on the
canonical path) and cost 33% KV page capacity. The arena is ordinary RAM
(`kv_bytes/2`), allocated only for a model with an AMX-eligible attention shape
(`amx_mirror_eligible` over the plugin's attention kernels - the same
`amx_attn::shape_ok` gate as the dispatch) on a host where AMX is available at
runtime, fail-soft to null; page capacity is identical with and without it.
Coherence (`Note [K mirror coherence]`): the mirror is a pure derived view with
exactly two production write sites - the `save_k` write-through on the RX
worker, and the `copy_storage_slot` rebuild - the one function every page move
(defrag, append) goes through. Byte-equivalence is tested at both levels.

**Why keep two copies of K instead of storing K transposed once?**
(`Note [Why not replace canonical K]`.) Because canonical K is a shared
interface and the VNNI form is one kernel's private view: the FPGA DMAs the
K page bytes exactly as stored; the AVX fallback consumes contiguous
128-value K rows (the VNNI layout would turn every narrow/partial/
kill-switch case into strided or gather loads plus rearrangement); and the
kill-switch rollback requires the unchanged layout to exist. Replacing
would save only the arena RAM and its plumbing - not the write, since the
~70 ns/token-row scatter would become the primary store. V is the precedent
for when replacing IS right: every V consumer (AVX, AMX, the card) reads
the same pair-interleaved layout natively, so V needs no second copy.
Reopen only if a card consumes VNNI K natively or an FPGA-free build ships.

### Geometry

The fast path engages only for one attention shape. The gate is one function,
`amx_attn::shape_ok` (`h/tron/kernels/amx_attn_iface.hpp`), evaluated at
compile time wherever the shape matters - the dispatch and both fast-path
blocks in `h/tron/models/self_attention.hpp`, the `save_k` write-through in
`h/tron/models/model.hpp`, and (through `amx_mirror_eligible`) the mirror-arena
allocation - plus the runtime check:

```c++
constexpr bool amx_shape_ok =
    amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
const bool amx_on = amx_shape_ok && amx_attn::available();
```

Each head must be 128 wide, with exactly 4 query heads sharing each K/V head.
Why this shape: one query group of 4 x 128 = 512 bf16 = 1,024 bytes packs as
exactly one full AMX tile operand, no padding waste. The kernel names carry
it: `qk_canonical_128x4`, `weights_times_v_128x4`, `qk_mirror_128x4`.

The following models match the gate: qwen-3-4b-2507, llama-3-8b, llama-3.1-8b,
mistral-7b, ministral-8b, mixtral-8x7b. Three are measured (qwen,
llama-3.1-8b, mixtral). Every other family runs the unchanged AVX path. In
the canonical build no AMX code is compiled into its instantiation; in the
mirror build the same shape gate (`amx_attn::shape_ok`, shared by the
dispatch, the `save_k` write-through, and the mirror-arena allocation)
compiles out the write-through and skips the arena, so an ineligible model on
an AMX host pays nothing for the mirror either. That includes the near miss
llama-3.2-1b (ratio 4, but 64-wide heads fail the head-size half of the
gate) and gpt-oss (64Q/8KV/head 64, fails both halves). Supporting another
shape means writing new kernels for that tile shape, and making the code
that finishes each page after the tile products (scaling, exponentiation,
and the running-softmax update of v*/s*/m*) work for the model's actual
number of query heads per KV head (today it assumes 4,
`geometry.kv_mul()`), with the kernel chosen by that real group width. The
shape check itself must stay strict: loosening it so that an unsupported
shape reaches the existing 128x4 kernels would produce wrong results, because
those kernels read exactly 4 heads of 128 dims.
