## Short version

The review of PR #5022 found three places where the AMX attention path does work it could avoid. None of them changes a result. This issue collects them, so that each one lands with a measurement on a Granite Rapids host.

## Words used here

- AMX = the Intel tile-matrix instructions. The kernels are in `src/tron/kernels/amx_attn.cpp`.
- Q pack = `pack_q_group_128x4`, the copy of one token's query group into the tile layout.
- transposing store = the AVX-512 code in `qk_rowmajor_128x4` that writes the score rows. PR #5022 moves it into `transpose_scores` (`h/tron/kernels/amx_attn_transpose.hpp`).
- dense page = a full 64-token KV page inside the attention window. Only dense pages use AMX.

## Items

1. Baseline first. Time each kernel alone on Granite Rapids: ns per call for `pack_q_group_128x4`, `qk_rowmajor_128x4` and `weights_times_v_128x4`, at 4 and 16 heads, on a dense page. No such number exists today. The review's numbers come from an AMD Zen 4 host: the pack costs 71 ns at 4 heads and 660 ns at 16 heads there.
2. Pack only for dense pages. Today the Q pack runs before the dense-page check. A token whose pages are all partial pays for a pack it never uses ([PR #5022 review thread](https://github.com/positron-ai/tron/pull/5022#discussion_r4356062294)). The [plan on PR #3879](https://github.com/positron-ai/tron/pull/3879#discussion_r3896108314) is to pack only when the page is full, and to open the tile region at the first pack. This item needs one more number: the share of page-range calls that end with zero AMX pages for Muse Glimmer.
3. Vectorise the 16-head pack. It is a scalar loop that compiles to 512 `vpextrw` stores ([review thread](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061055)).
4. Compute stage 3 of the transposing store once per block. The 16-head store emits 48 shuffle instructions where 32 are enough ([review thread](https://github.com/positron-ai/tron/pull/5022#discussion_r4356062057)).

## Out of scope

Adding a group size. Renaming the kernels (#5021).

## Acceptance

- Results unchanged: `t_amx_numerics`, `t_amx_dispatch_dtype` and `t_llama_unit` pass with AMX on and with `TRON_AMX_DISABLE=1`.
- Each item reports its number before and after, from the measurement of item 1.
- The 4-head kernels keep their instruction listing, or the PR explains the difference.
