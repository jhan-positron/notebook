Campaign W, the whole-machine package campaign of the description's section "Whole-machine package campaign", finished on 2026-10-13 at 15:24 UTC. The description now holds its result, and the "Package campaign" open item is removed.

**Short version.** The target package keeps the parent PR's resolved gain in the 32-user Llama cell: +5.2 % TPS (generated tokens per second, as the harness reports them), paired t +53.8, against +4.8 % in PR #4424's campaign of 2026-10-09. The two other cells are inside the threshold: llama-3.1-8b with 8 users −0.4 % TPS, gpt-oss-120b −0.3 % TPS, neither resolved. TTFT (time to first token) and peak memory show no resolved change in any cell.

| Cell | Base TPS | Target TPS | TPS difference | Paired t | Resolved | TTFT difference |
|---|---|---|---|---|---|---|
| llama-3.1-8b, tp2, 8 users, prompt 1,024 | 150.78 | 150.15 | −0.4 % | −1.05 | no | +14 ms, t = +2.08, not resolved |
| llama-3.1-8b, tp2, 32 users, prompt 4,096 | 32.73 | 34.42 | +5.2 % | +53.81 | yes | −17 ms, not resolved |
| gpt-oss-120b, tp4, 8 users, prompt 1,024 | 123.49 | 123.11 | −0.3 % | −0.59 | no | +4 ms, not resolved |

**Setup.** The base is the Debian package of `main` at `72308ec90c`. The target is the package of this branch at `ea94e95a4e`. The published head `e7d06a1267` adds only four benchmark-record rows. The four passes ran in the order base, target, target, base, with 10 rounds each and FPGA attention as shipped, through the nightly's performance harness on the Granite Rapids test machine. The decision rule is an absolute paired t of at least 2.26 and an absolute difference of at least 1 % (TTFT also at least 1 ms). The t pools the two pass pairs, 20 round pairs per cell.

The open items with scheduled measurements (token identity, AMX-disabled throughput, forward-path coverage) run on the test machine tonight. Their results follow in this thread and in the description.
