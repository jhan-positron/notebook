# positron-ai/asim PR #244: Add native numerical validation for Qwen3.5 MoE inference
author: positron-jessezhang  created: 2026-09-15  state: closed  merged: 2026-09-17  head: 927d501a8648b53cdaafff22e7a82107c980a337  base: main  url: https://github.com/positron-ai/asim/pull/244
commits: 1
  - feat(validation): qualify Qwen3.5 MoE with native numerical gates
files (52):
  - README.md (+3 -0)
  - docs/ANCHORED_EVIDENCE.md (+1 -0)
  - docs/PRIME_RADIANT.md (+3 -3)
  - docs/QWEN35_MOE_NATIVE_VALIDATION.md (+202 -0)
  - docs/reports/hf_transformer_hardware_fit_matrix.json (+15 -0)
  - docs/reports/hf_transformer_tiny_fixture_coverage.json (+86 -2)
  - docs/reports/hf_transformer_tiny_fixture_coverage.md (+14 -13)
  - docs/reports/hf_transformer_validation_summary.md (+1 -1)
  - src/asim/cli/main.py (+41 -5)
  - src/asim/cli/rtlsim.py (+3 -2)
  - src/asim/sim/attention_kv_runtime.py (+23 -0)
  - src/asim/sim/attention_runtime.py (+7 -1)
  - src/asim/sim/compute/sal_ops.py (+4 -1)
  - src/asim/sim/gdn_backend_runtime.py (+18 -1)
  - src/asim/sim/gdn_recurrence_runtime.py (+20 -13)
  - src/asim/sim/gdn_state_runtime.py (+49 -0)
  - src/asim/sim/generation_checkpoint_runtime.py (+28 -1)
  - src/asim/sim/generation_runtime.py (+2 -0)
  - src/asim/sim/ir_executor.py (+21 -0)
  - src/asim/sim/ir_lowering.py (+24 -1)
  - src/asim/sim/mla_moe_runtime.py (+53 -9)
  - src/asim/sim/weight_loader.py (+24 -1)
  - src/asim/spm/gdn_scratch.py (+36 -10)
  - src/asim/validation/canonical_rtlsim.py (+16 -0)
  - src/asim/validation/hf_fixture_coverage.py (+33 -0)
  - src/asim/validation/native_precision.py (+231 -0)
  - src/asim/validation/native_quantization.py (+119 -0)
  - src/asim/validation/qwen35_gguf_reference.py (+99 -0)
  - src/asim/validation/qwen35_native_reference.py (+404 -0)
  - src/asim/validation/qwen3_5_moe_native_gdn.py (+219 -0)
  - src/asim/validation/qwen3_5_moe_validation.py (+231 -0)
  - src/asim/validation/tiny_hf_models.py (+358 -46)
  - tests/test_canonical_rtlsim.py (+11 -0)
  - tests/test_cli_rtlsim_gguf.py (+16 -0)
  - tests/test_gdn_chunk_intra_batched.py (+151 -7)
  - tests/test_gdn_runtime.py (+24 -6)
  - tests/test_gdn_spm_scratch_map.py (+62 -0)
  - tests/test_generation_state_checkpoints.py (+172 -0)
  - tests/test_hf_fixture_coverage.py (+20 -3)
  - tests/test_import_shadowing_guard.py (+96 -0)
  - tests/test_native_precision_reference.py (+52 -0)
  - tests/test_native_quantization.py (+62 -0)
  - tests/test_qwen35_gguf_qualification.py (+82 -0)
  - tests/test_qwen35_gguf_reference.py (+54 -0)
  - tests/test_qwen35_moe_numerical_gates.py (+180 -0)
  - tests/test_qwen35_native_reference.py (+176 -0)
  - tests/test_qwen3_5_moe_native_gdn.py (+115 -0)
  - tests/test_sal_structural_loads.py (+21 -0)
  - tests/test_tiny_hf_external_oracle_nightly.py (+6 -0)
  - tests/test_tiny_hf_models.py (+124 -0)
  - tests/test_weight_loader.py (+39 -0)
  - tools/prime_radiant/coverage/rtl_asim_candidate_map.json (+7 -7)

## PR body (as it is now; may have been edited after the review)

Add independent numerical checks for standalone Qwen3.5 MoE text inference.

## Problem

Running the full model exposed GDN buffers being overwritten before their final use, incorrect shared-gate tensor layout, and SAL scalar precision mismatches. Generated tokens alone did not establish numerical correctness.

## Solution

Preserve live GDN buffers, correct tensor loading and scalar precision, and add an independent reference with strict checkpoint comparisons for each generation step. Add a 256-expert/top-8 tiny case covering prefill and two decode steps, supported by synthetic GDN regressions and reusable validation artifacts. Mark only the three native-oracle tests whose provenance checks require the RTL checkout. The frozen tiny checkpoint digest is registered in `docs/ANCHORED_EVIDENCE.md` with its provenance in `docs/QWEN35_MOE_NATIVE_VALIDATION.md`. A review pass then consolidated the tolerance rule, margin constants, row-position derivation and comparison-JSON writes into single owners, gated capture-mode recording consistently, restored the conservative scratch reservation for undeclared GDN geometry, and made the reference refuse an undeclared head layout for grouped heads; frozen reference arithmetic and the suite's embedded checkpoint names were left unchanged.

## Testing

- On this head (rebased onto current main, RTL present): nearest and merged test files 753 passed, 0 failed; contract lane 111 passed; light gate all six lanes green (src 801 passed / 7 skipped, 12321 tests collected); tiny canonical passed (prefill plus two decode steps, tokens and all checkpoint gates); `tools.prime_radiant check` and `asim validation hf-survey reports --check` pass; the tiny fixture regenerated before and after the review fixes is byte-identical except the oracle's provenance hashes of the edited reference sources.
- The first full validation of the review pass caught a regression the light gate cannot see: a leftover function-local import in the MoE expert path raised `UnboundLocalError` whenever checkpoint capture was on (tiny canonical and four MoE external-oracle cases failed). Fixed in this head; those five cases pass again. No arithmetic changed.
- Same runtime arithmetic on the pre-rebase head 3e71b6c4: full gate red only on lanes this branch does not own (Gemma strict logits, a C2C ledger check needing Python 3.12.3, Prime Radiant witnesses needing Verilator); tiny canonical passed; two fresh real 35B runs produced ` Paris.\n` through all 40 layers with 0 mismatches against the frozen 3,574-gate suite, and their exact repeat comparison found 0 differences across 4,174 checkpoints.
- A static guard (`tests/test_import_shadowing_guard.py`) now pins that mechanism: a function-scope use of a module-level imported name must not precede a local import of it. Zero hits across `src/asim`, `tests`, `tools`, `scripts`; against the regressed file it reports both crash sites.
- The full validation restarted on the rebased head got through contract, Prime Radiant check, src and the bulk lane (bulk: only the two known non-owned failures, Gemma and the C2C Python-version check) before it was stopped to fold the guard and merge; the 35B acceptance and repeat therefore stand on the earlier head with identical runtime arithmetic (see above), not on this exact head.


## Wade's reviews (summary verdicts)

- review 5215895996 COMMENTED at 2026-09-15T21:22 commit cef64ea5bd7227e813cc022bf3fa19e14d0972cf: (no text)
- review 5240537644 APPROVED at 2026-09-17T19:32 commit 63c5b8a12cecfaf1754e8c01806d76c162b31f24: (no text)

## Wade's inline comments

### inline 4020335622 at 2026-09-15T21:22  tests/test_qwen35_native_reference.py:39 (commit 3e71b6c4d4)
```diff
[... hunk truncated]
+    from asim.validation.qwen35_native_reference import native_rope
+
+    positions = np.asarray([0, 1, 3, 5, 4097, (1 << 24) - 1])
+    values = np.random.default_rng(417).standard_normal((2, len(positions), 128)).astype(np.float32)
+    actual = native_rope(values, positions, theta=1_000_000, rope_dim=32)
+    expected = rope_bf19(values, positions, theta=1_000_000, rope_dim=32)
+    np.testing.assert_array_equal(actual, expected)
+
+
+def test_native_qwen_tiny_reference_propagates_own_cached_frames():
+    from asim.validation.qwen35_native_reference import build_qwen35_native_oracle
+    from asim.validation.tiny_hf_models import tiny_qwen3_5_moe_stress_spec
+
+    oracle = build_qwen35_native_oracle(
+        spec=tiny_qwen3_5_moe_stress_spec({}, profile="chunked_stress"),
+        seed=1234, prompt_tokens=[1, 42, 17, 99], decode_steps=3,
+    )
+    assert oracle["protocol"] == "asim.qwen35-moe-native.v3"
+    assert oracle["source"] == "independent_numpy_native_precision_reference"
+    frames = oracle["reference_frames"]
+    # Frozen from this independent v1 reference before the tie-order correction;
+    # all 282 untied D128 checkpoint arrays must remain byte-identical under v3.
+    digest = hashlib.sha256()
+    for frame in frames:
+        for name, checkpoint in sorted(frame["checkpoints"].items()):
+            digest.update(json.dumps([frame["phase"], frame["generation_step"], frame["positions"],
+                                      name, checkpoint["dtype"], checkpoint["shape"]],
+                                     separators=(",", ":")).encode())
+            digest.update(np.asarray(checkpoint["data"], dtype=checkpoint["dtype"]).tobytes())
+    assert digest.hexdigest() == "14afab7ff0d8cd39d99aa4a1f0b083ce12e2d1b53777d2f348ba7f465980b389"
```
WADE: is this crazy 'magic' digest/sha captured/documented anywhere? Where did it come from? Are these supposed to be listed in the ANCHORED_EVIDENCE doc (I just happened to see that referenced from the AGENTS doc)
  reply by positron-jessezhang (2026-09-16): Good catch: it was not registered. The literal is a SHA256 over every D128 checkpoint array of the tiny `chunked_stress` native reference (frame identity, checkpoint name, dtype, shape, then the bytes, for all three frames), frozen on 2026-09-11 from the first independent NumPy reference (protocol v1). It is a regression lock: the v2 (SVL tie-order) and v3 (128-wide QK merge) corrections only touch tied and D256 paths, so the tiny D128 checkpoints must stay byte-identical, and this assertion is 
