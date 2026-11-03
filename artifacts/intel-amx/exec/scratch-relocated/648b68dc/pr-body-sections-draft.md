### Token identity

Measured 2026-10-18 on delphi-3bda, our half: one user, temperature 0, `--pay-for-determinism`, seed 1, 256 generated tokens. Two binaries built with one recipe (plain shell, clang 19.1.7, preset `native`, `-DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON`): base = main 6198824246 (this PR's merge base) and head = 5061623a34. head2 = head run a second time (the A/A control). headoff = head with the kill switch. Raw results: smoke/<cell>/<arm>.tokens and identity.txt (result set glimext-20261018).

| Cell | head vs head2 | head vs base | headoff vs base |
|---|---|---|---|
| llama-3.1-8b tp2, CPU attention, prompt 1024 (kv_mul 4) | identical, 256 of 256 | identical, 256 of 256 | first difference at token 12 (AMX vs AVX, see issue #4444) |
| qwen3-4b tp2, FPGA attention, prompt 1024 | identical | identical | identical |
| gpt-oss-120b tp4, FPGA attention, prompt 1024 | identical | identical | identical |
| Glimmer tp2, FPGA attention, prompt 1024 | identical | first difference at token 5 | identical, 256 of 256 |
| Glimmer tp2, CPU attention, prompt 1024 | identical | first difference at token 53 | identical |
| Glimmer tp2, FPGA attention, prompt 2048 | identical | first difference at token 12 | identical |
| Glimmer tp4, FPGA attention, prompt 1024 | identical | first difference at token 30 | identical |

What the table says. The kill switch gives main's tokens on Glimmer in every cell. The kv_mul-4 path is unchanged: head equals base on llama-3.1-8b. The FPGA-attention models are untouched. Where the AMX kernel scores Glimmer's sliding-window layers, head and base diverge at a near tie after 5 to 53 tokens; the measurement of that tie is in issue #4444 (comment of 2026-10-18), not here.

### Other models with and without this PR

Same two binaries, 8 users, 256 generated tokens with `--dont-stop`, 4 repetitions (8 for llama-3.1-8b at prompt 8192, re-measured after the first 4 flagged it), the arm order alternating per repetition, `TRON_ATTN_STATS=1` in both arms. Decision rule: paired head minus base per repetition; band = twice the larger arm sd over the repetitions; a cell holds when the TPS delta is not below minus the band and the prefill delta not above the band. The AMX share is the share of the K tokens of the run that the AMX kernel scored (the exit report), base / head. Raw results: rt-results.txt, rt/<run>.log, results.md (result set glimext-20261018).

| Cell | base TPS/user | head TPS/user | Paired delta (band, t, paired reps) | base prefill s | head prefill s | AMX share base / head | Verdict |
|---|---|---|---|---|---|---|---|
PERF_ROWS

What the table says. llama-3.1-8b (kv_mul 4, the same kernel in both binaries), qwen3-4b and gpt-oss-120b (FPGA attention) decode within 0.4 % of base, and their prefill within 0.2 %. L8B8192_SENTENCE Glimmer gains 4.3 to 15.6 % decode TPS and 0.5 to 8.9 % prefill time against main, the same gains as the kill-switch comparison above. The kernel disassembly of this build pair (same compiler) confirms the kv_mul-4 kernels: pack and QK byte-identical to main's (509 and 204 instructions), PV the same 120 instructions in the same order with the thread-local scratch addressed differently (preservation2.txt).
