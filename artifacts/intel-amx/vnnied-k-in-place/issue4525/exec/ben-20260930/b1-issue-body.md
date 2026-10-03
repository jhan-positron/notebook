## Short version

`view` and `const_view` take their two flags as `bool` template parameters, and call sites can swap the two flags without a compile error (82 lines in 20 files pass bare `true, false`). This issue replaces the two `bool` parameters with two enum types, so that swapped or bare arguments fail to compile. PR #4557 added two named constants as a temporary measure, and this follow-up removes them.

## Words used here

- `view` / `const_view`: tron's fixed-shape tensor view types (h/tron/tensor/view.hpp).
- `aligned` flag: `true` means the data pointer is aligned for whole-register loads, so chunked SIMD (single instruction, multiple data: one instruction on a whole register) reads are allowed.
- `dma` flag: `true` means the memory is DMA-safe (direct memory access: usable by the accelerator cards). The flag takes part in type identity only. No code branches on it.
- `enum class`: a C++ scoped enumeration. Its values do not convert to `bool` or `int` by themselves.

## Why

`view` and `const_view` take two boolean template parameters, `aligned` and `dma` [h/tron/tensor/view.hpp:17-18, views.hpp:23-24, h/tron/kernels/expr.hpp:18-21]. Call sites spell them as bare `true, false` (82 lines in 20 files at PR #4557 head c73e7fb2f9, for example h/tron/models/kv_cache.hpp:1960 `view<bf16, true, false, seq<head_size>>`). Two flags of the same type can be swapped without a compile error.

PR #4557 added the named constants `VIEW_ALIGNED_TRUE` and `VIEW_DMA_FALSE` [h/tron/tensor/kv_cache_fwd.hpp:24-25] on its own 31 lines. The coding guide applied in that PR counts `true` and `false` as literals that must live in named declarations (commit 5051264d80). The maintainer review of PR #4557 asked for enum types instead [https://github.com/positron-ai/tron/pull/4557#discussion_r4133613638]. The same thread marks the change as a follow-up, not a blocker [https://github.com/positron-ai/tron/pull/4557#discussion_r4134933234].

## What

Make the two flags enum types, so that swapped arguments and bare literals fail to compile:

```cpp
// h/tron/tensor/views.hpp (next to the existing dma comment)
enum class view_alignment : uint8_t { unaligned, aligned };
enum class view_memory : uint8_t { host, dma };

template <typename T,
    view_alignment alignment,
    view_memory memory,
    typename Dim,
    typename Stride = row_major<Dim>>
struct view;
```

A call site then reads `view<bf16, view_alignment::aligned, view_memory::host, seq<head_size>, sseq<1>>{dest}` (today: h/tron/scheduler/full.hpp:2762).

The repo already uses enum class template parameters: `rope_scaling` / `rope_layout` [h/tron/kernels/rope.hpp:95, :275] and `moe_scale_mode` [h/tron/models/mixture_of_experts.hpp:275].

## Scope (counts at c73e7fb2f9)

- Parameter declarations that must change type:
  - view.hpp 17 lines, views.hpp 15, slice.hpp 6, expr.hpp 2.
  - tensor.hpp 7 parameter lines (`dma1` / `dma2` at :358-359, :375, :492-493, :517, :522).
  - dotter.hpp 29 (its `template <typename U, bool dma>` members deduce from view types).
- Static members that hold the flag: tensor.hpp:35, :254, itensor.hpp:26 (`= false`), dmatensor.hpp:38, :173 (`= true`).
  - Readers: tensor.hpp:415-416 (`Activation::dma`, `Result::dma`) and model.hpp:2831 (`v_buffer_t::dma`).
  - Computed flags: `constexpr bool is_dma` in mixture_of_experts.hpp:535 and feed_forward.hpp:489.
- Consumers that branch on `aligned`: view.hpp:157-158 forwards it to `chunky<T, aligned>` and `readable_in_chunks<T, aligned>`. slice.hpp:56, :93 and simd/aligned.hpp:14-66 use `if constexpr (aligned)`.
  - Decide in the PR: convert at the view boundary (`alignment == view_alignment::aligned`) and leave the SIMD-level `bool aligned` in wide.hpp (46 lines), chunky.hpp, clamp.hpp and simd/aligned.hpp as is, or convert those too.
- Call sites: 82 lines passing bare `true` / `false` in 20 files, plus the 31 lines in 9 files that use `VIEW_ALIGNED_TRUE` / `VIEW_DMA_FALSE` (delete the two constants), plus the aliases PR #4697 adds (`bool Dma = VIEW_DMA_FALSE`).
- `gptq_view<bool permuted, ...>` in safetensors.hpp is a different flag. Leave it.

## Ordering

Land after #4557 and #4697. #4424 adds 5 bare-flag view lines on its branch. Coordinate with it.

## Acceptance

- No `bool aligned` / `bool dma` parameter remains on `view`, `const_view`, `views`, `const_views`, `lambda_views`, `id_views`, `array_views`, `slice`, `dotter`, `t_launch_matmul`.
- Add a concept `view_args_ok<T, a, m> = requires { typename view<T, a, m, ...>; }` next to the h/tron/tensor/array_like.hpp:24-30 static_asserts, and `static_assert(!view_args_ok<bf16, true, false, ...>)` plus the swapped form. A static_assert on a type alone cannot check that a spelling fails to compile.
- Existing tests pass (t_fp32, t_attention, t_llama_unit, t_heterogeneous_scheduler, t_amx_numerics, t_amx_dispatch_dtype).
- Check that the generated code changes only in symbol names. Compare the defined-symbol counts of t_llama_unit and t_amx_numerics before and after, as commit 5051264d80 did.
