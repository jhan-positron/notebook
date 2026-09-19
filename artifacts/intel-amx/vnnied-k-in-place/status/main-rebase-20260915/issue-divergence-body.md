## Short version

Binaries built with the AMX attention kernels (PR #3879) or with the VNNI K layout (PR #4424) generate different tokens than the row-major binary after some steps, on the same prompt with greedy decoding. The code's numerics contract explains such differences (a different fp32 add order can flip a token at a near tie), but the explanation has not been confirmed by a measurement, and PR #4424 changes what the AMX kill switch gives back. This issue tracks the measurement and the kill-switch decision.

## Words used here

| Term | Meaning |
|---|---|
| row-major binary, clean binary | A build with `TRON_AMX_DISPATCH` and `TRON_K_VNNI` both OFF (the default). K is stored as one row of 128 values per token, and every token is scored by the AVX-512 dotter. |
| dotter | The existing per-token AVX-512 dot-product loop of software attention (`h/tron/kernels/dotter.hpp`). |
| AMX kernels | The tile kernels of PR #3879 that score one full 64-token page at a time (`TRON_AMX_DISPATCH=ON`). |
| VNNI layout, VNNI reader | PR #4424 stores the K cache of 128-dimension heads in the AMX pair-interleaved layout (`TRON_K_VNNI=ON`). The VNNI reader is that PR's AVX-512 routine that scores tokens from the new layout (`k_vnni::qk_group`); it serves partial pages, hosts without AMX and the kill switch. |
| kill switch | The environment variable `TRON_AMX_DISABLE=1`. It turns the AMX kernels off at run time inside the same binary. |
| greedy run | Temperature 0 with deterministic reductions: the same binary produces the same tokens twice. |
| near tie | A generation step where the two best candidate tokens have almost the same score, so a tiny change in the score picks the other one. |
| Top-k Logits record | The per-step record of the best candidate tokens and their scores that a forced run can write out. |
| forced run | Teacher forcing: the binary is fed a fixed token sequence (`--force-feed-text-token-file`) and its scores are recorded at every step, so two binaries can be compared step by step. |

## What was observed

- PR #4424, one greedy run each, tp2, prompt 1024 tokens, 128 generated tokens, base = PR #3879 binary: llama-3.1-8b first different token at step 46; qwen-3-30b-a3b (kv_mul 8, where every page goes through the VNNI reader) first different token at step 5. Both outputs were fluent continuations of the same text. The FPGA-attention run and gpt-oss-120b (64-dimension heads, layout off) were identical, 128 of 128 tokens.
- PR #4424 September campaign, qwen3-4b, tp2, prompt 1024: base and VNNI binaries diverged at step 52, in both AMX states of the VNNI binary (kill switch on and off).
- PR #3879 review: the AMX binary with the kill switch on and off diverged on qwen3-4b. The investigation found an exact bf16 tie flipped by admissible numerics, and an add-order control without AMX reproduced the flip.

No attention scores were recorded in the #4424 runs. So the cause of those divergences is inferred from the contract below, not measured.

## Why the code expects this

- Note [AMX attention dispatch] (a named comment block in `h/tron/kernels/amx_attn_iface.hpp`) states that both paths multiply bf16 inputs and add the products in fp32, and that for finite, non-subnormal inputs the outputs differ for exactly two reasons: the bf16 rounding of the PV weights, and the order in which the fp32 products are added ([amx_attn_iface.hpp lines 74-85 at ff680c8020](https://github.com/positron-ai/tron/blob/ff680c8020/h/tron/kernels/amx_attn_iface.hpp#L74-L85)).
- The VNNI reader states the same contract against the dotter: same instruction (VDPBF16PS), only the order of the fp32 adds differs ([k_vnni.hpp lines 240-242](https://github.com/positron-ai/tron/blob/ff680c8020/h/tron/kernels/k_vnni.hpp#L240-L242)).
- Tests enforce it: `t_k_vnni_layout` checks the reader against the dotter inside an envelope of 1e-4 of the absolute-product mass plus 1e-6, over 91 live-token masks ([t_k_vnni_layout.cpp lines 237-340](https://github.com/positron-ai/tron/blob/ff680c8020/t/t_k_vnni_layout.cpp#L237-L340)). `t_amx_numerics` requires the AMX kernel reading the VNNI plane to be bit-identical to the AMX kernel reading row-major K ([t_amx_numerics.cpp lines 188-244](https://github.com/positron-ai/tron/blob/ff680c8020/t/t_amx_numerics.cpp#L188-L244)).

A score can therefore move by at most the envelope. A token can flip only at a near tie. That last step is the unmeasured part.

## To do

1. **Confirm the near-tie explanation with a measurement.** Run the row-major binary and the PR #4424 binary as forced runs on the same prompt (one of the divergent cases above). Compare the Top-k Logits record at the first divergent step. Expected if the explanation holds: the gap between the two best candidates at that step is within the add-order envelope, and every earlier step has the same top candidate. Anything larger needs its own investigation. The PR #3879 review used this recipe.
2. **Decide the kill-switch contract (reviewers of PR #4424).** Item 4 of Note [AMX attention dispatch] promises for `TRON_AMX_DISABLE=1`: "AMX off, same layout, same AVX dotter, clean-binary numerics; it exists for same-binary A/B tests and for rollback" ([amx_attn_iface.hpp lines 47-51](https://github.com/positron-ai/tron/blob/ff680c8020/h/tron/kernels/amx_attn_iface.hpp#L47-L51)). With `TRON_K_VNNI` on, the kill switch runs the VNNI reader instead of the dotter for 128-dimension heads, so it still gives an AMX-off run of the same binary but no longer the tokens of a clean binary ([kv_cache.hpp lines 706-710](https://github.com/positron-ai/tron/blob/ff680c8020/h/tron/models/kv_cache.hpp#L706-L710)). The layout is a build-time property, so a run-time switch back to row-major K is not possible. Options: (a) accept the weaker rollback and add the condition "with `TRON_K_VNNI` off" to item 4 of the AMX Note; (b) keep a row-major build as the rollback artifact in deployment and document that.
3. **Optional: a model-level bound.** A test that compares the logits of the clean binary and the VNNI binary on a fixed prompt (for example total variation distance per step) would turn the contract into a checked bound at model level, instead of the per-kernel envelope only.

## Related

- PR #3879 (AMX software attention, merged 2026-09-15) and PR #4424 (VNNI K layout, open).
- #4347 (enable AMX attention in nightly CI) and #3997 (no CI configuration compiles the AMX code): the same binaries, different question.
