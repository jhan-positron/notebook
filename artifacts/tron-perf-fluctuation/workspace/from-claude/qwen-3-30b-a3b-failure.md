# qwen-3-30b-a3b failure report — NaN logits at token 0

Date: 2026-08-09
Machine: delphi-3bda
Binary: `/scratch/jhan/tron-perfetto-install-20260809/bin/runtron`
(tron main `12804a81216632d38c204c61d0b6fc076702a7eb`, built 2026-08-09 on
alpha, cross-avx512 preset; sha256 `17da8295…d6255f`)

## Summary

Every inference run of `ingested-qwen-3-30b-a3b-instruct-2507` (tp4 and tp2)
aborts with a NaN logit at the first generated token. The 20-draw Perfetto
campaign for this model produced **no valid data**. The other two campaign
models (qwen-3-4b dense, gpt-oss-20b MoE) work on the same binary, harness,
and machine, so the failure is specific to the qwen-3-30b MoE model plugin
or its interaction with these weights.

## Symptom

```
[error] TRON_ASSERT(!std::isnan(elt)): Encountered NaN logit at token 0.
```

runtron then aborts (SIGABRT, exit 134).

- Reference (tp4): all 21 runs (1 smoke + 20 draws) of campaign
  `/scratch/jhan/perf-fluctuation/tron-perfetto-5cat-qwen3-30b-a3b-20260809T1710Z`,
  e.g. `results/draw_01/runtron.log` line at 17:14:50.
- Reference (tp2): both runs of the 1-round diagnostic
  `/scratch/jhan/perf-fluctuation/tron-perfetto-diag-qwen3-30b-tp2-20260809T1857Z`
  (`smoke/runtron.log`, `results/draw_01/runtron.log`).

Caution when reading the campaign data: the harness marked all crashed draws
`ok` (exit 0). The only journal-visible symptom is `generate=None tok/s` in
`journal.log`, and `run-benchmark.log` shows
`✗ Instance 0 exited with status 134`. results.csv `status=ok` for this
campaign does NOT mean the draw succeeded.

## What was ruled out (each claim with its reference)

| Ruled out | Evidence |
|---|---|
| Infrastructure / binary / harness | qwen-3-4b: 20/20 draws OK, mean 102.6 tok/s (campaign `…-qwen3-4b-20260809T1626Z/results.csv`). gpt-oss-20b (also MoE + GPTQ): 19/20 OK, mean 107.3 tok/s (`…-gptoss20b-20260809T1752Z/results.csv`). Same binary, harness, machine. |
| tp4-specific bug | Same assert at tp2 (diagnostic run above). |
| Missing/unreadable weights | `runtron.log` shows tokenizer and all layers loading from `/opt/positron/weights_cache/cached/positron-ai/Qwen--Qwen3-30B-A3B-Instruct-2507-ingest-best-gptq-v1` (draw_01 log, 17:14:01–17:14:02). |
| Plugin/weights config mismatch | HF snapshot config used for plugin generation (alpha HF cache, snapshot `0d7cf239…`) matches the GPTQ weights `config.json` on all architecture fields; only cosmetic diffs (`torch_dtype` key rename, `transformers_version`). |
| Missing expert-load profile | gpt-oss-20b also has no `expert_load.json` (only gpt-oss-120b has one in the weights cache) and runs fine with the "using defaults" path. |
| Immature model | Registry lists `support_level: working` ("valid tokens in and out"); promoted to production in tron PR #3409 (`d32b922`). |

## Where the NaN appears (symbolized stack)

Symbolized with addr2line against the unstripped binary on alpha:

```
tron_abort                                   h/common/assert.hpp:61
top_k_accum_t::insert<tron::bf16>            h/common/top_k_accum.hpp:57
stream_result_t::try_consume                 h/libpos.hpp:228
  (launch_matmul consumer, qwen_3_30b_moe_impl / tp4_min512_tensor)
fill_logits_buffer, sparse_logits_t lambda   h/tron/models/model.hpp:3182
```

The assert fires while top-k consumes logits streamed from the final matmul —
the forward-pass output is already NaN before sampling. The assert is the
detector, not the cause.

## Hypothesis (labeled, unconfirmed)

The 30b GPTQ weights' `quantization_config.dynamic` rules exclude the MoE
router from quantization (`-:^model\.layers\.[^.]+\.mlp\.gate$` — present in
the 30b config, absent in the working 4b config). The router therefore ships
as bf16 while everything else is GPTQ int4. If the loader or the generated
plugin mishandles this unquantized gate tensor, routing weights become
garbage and the MoE output NaNs.

This is a hypothesis: no measurement yet ties the NaN to the gate tensor.
Measurements that would confirm or reject it:

1. Run the **official deb-built runtron** on the same weights on
   delphi-3bda. Crash → weights/plugin problem; success → this build
   (nix/cross-avx512 path) is at fault.
2. Dump the router (`mlp.gate`) weights after load and compare against the
   safetensors values.
3. Bisect tron main between the PR #3409 validation point and `12804a8`.

`Insufficient data` on where the model was last validated: delphi-3bda's
production rinzler serves only llama models (`/etc/rinzler/instance-*.env`),
so no on-machine known-good run exists to compare against.

## Impact

- Campaign 2 of 3 (qwen-3-30b-a3b) has no valid throughput or trace data;
  its campaign directory should not be used for gap/fluctuation analysis.
- Campaigns 1 and 3 are unaffected and complete:
  - `…/tron-perfetto-5cat-qwen3-4b-20260809T1626Z/report.html` (20/20)
  - `…/tron-perfetto-5cat-gptoss20b-20260809T1752Z/report.html` (19/20;
    draw_05 failed at metrics extraction, reason `no metrics` in
    results.csv, not an inference failure)
