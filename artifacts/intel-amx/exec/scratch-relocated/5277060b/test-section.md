Head f52d634c32. The delphi-3bda chain below ran at 19ae84d95a; f52d634c32 adds the K-mark checks to the `t_llama_unit` test and rewords one generator comment, so the measured runtron code is the same. The final commit's `t_llama_unit` (both K layouts) and the ingest tests were rerun at f52d634c32 (last bullet).

On delphi-3bda (our half, socket 1; chain `exec/savek-20261006/chain.sh` in jhan's intel-AMX workspace, 2026-10-06 17:54 to 18:44 UTC, rerun of one cell 18:55 to 19:13 UTC; results under `exec/results/savek-20261006/`, `savek-E-cpu/`, `savek-E-fpga/`, `savek-E-cpu8k/`):

- VNNI build (cross-avx512 preset, AMX dispatch on, ingest models on, 610 s): `t_k_vnni_layout` 63426 assertions / 5 cases, `t_amx_dispatch_dtype` 1559 / 1, `t_amx_numerics` 4621 / 5 on real AMX (no "AMX unavailable" line), `t_llama_unit` 128261 / 42, `t_heterogeneous_scheduler` 782 / 1, `t_phase1_integration` 2124 / 64, all pass. Kill-switch control (`TRON_AMX_DISABLE=1`): `t_amx_numerics` 2060 assertions with the three "AMX unavailable" warnings.
- The generated plugins carry one main-side call (`..., 0, n_workers)`) and one helper-side call (`..., worker_ix, n_workers)`) per KV-writing operation and no `save_k_helper`: qwen3-4b 36 and 36, qwen3-30b-moe 48 and 48, gpt-oss-120b 36 and 36.
- Ingest Haskell tests (`bin/ingest-cabal test`): 1 of 1 test suites passed.
- Row-major build (`TRON_K_VNNI=OFF`): the five layout-independent tests pass.
- Whole host suite (`make build-test-host`, `make test-host`, VNNI build): 89 passed, 1 skipped (`t_proxy_lib`), 0 failed, makespan 107 s. The PR #4424 reference is 89 / 1 / 0.
- Token identity (runtron, qwen3-4b tp2, 1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens): the new binary produced the same 256 tokens as the PR #4424 binary (30c4ac82cb) in every cell: CPU attention prompt 1024 (also the A/A repeat and the kill-switch pair), FPGA attention prompt 1024, CPU attention prompt 8192.
- Performance (8 users, 256 tokens, arms interleaved; band = max(2 x max sd, 0.4 TPS / 0.15 s)). TPS = decode tokens per second per user, TTFT = prefill time in seconds (max over the users).

| attention | prompt | n | head TPS | new TPS | TPS delta | head TTFT s | new TTFT s | TTFT delta |
|---|---|---|---|---|---|---|---|---|
| CPU | 1024 | 3 | 83.39 | 83.83 | +0.5 % | 3.139 | 3.136 | -3 ms |
| CPU | 8192 | 3 | 18.90 | 18.80 | -0.5 % | 52.74 | 55.94 | +3.2 s (one repetition at 61.5 s, the other two at 53.1 and 53.2 s) |
| CPU | 8192, rerun, new first | 5 | 18.91 | 18.79 | -0.7 % | 52.82 | 52.99 | +0.17 s (+0.3 %) |
| FPGA | 1024 | 3 | 125.18 | 124.98 | -0.2 % | 3.181 | 3.187 | +6 ms |

  The prompt-8192 cell was run again with five repetitions and the arm order reversed because of the 61.5-s repetition. In the rerun no repetition is above 53.2 s. The decode TPS of that cell is 0.5 to 0.7 % below head in both runs; this is inside the band. A decode step has at most 16 items, so the store is not shared there and both binaries take the same early return in the helpers.
- Final commit f52d634c32: @@FINAL@@
