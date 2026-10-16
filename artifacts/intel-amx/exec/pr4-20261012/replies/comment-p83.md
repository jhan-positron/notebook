The forced-token probe for the open item "Token mismatches" ran on 2026-10-13 from 17:17 to 18:00 UTC. The description's section "Token identity" now holds the table, and the open item is updated.

**Short version.** Each of the three token mismatches of 2026-10-12 is a near-tie, not a divergence. At generated token 83, `base` (CPU attention) and `head` (FPGA attention) sit on an exact tie between tokens 258 and 1499 (margin 0.000) that their tie-break resolves to 258, while `new` scores 1499 ahead by 1 to 2 ulps (a ulp is one bf16 step at the size of the score, 0.0625 near 15). At token 247 the kill-switch arm reverses a 1-ulp margin. At every other step every pair chooses the same top token, and the scores differ only at the ulp level (median top-two margin difference 0.0625, about 80 % of the vocabulary scores change by at least one ulp per step).

| Pair | Attention | Top-token changes over 256 steps | At token 83 | At token 247 |
|---|---|---|---|---|
| new vs base | CPU | 1 | `new` 1499 by 0.125 (2 ulps), `base` tie 258/1499 | same |
| new vs head | CPU | 0 | both 1499 by 0.125 | same |
| newoff vs new | CPU | 1 | same | `new` 13 by 0.125 (1 ulp), `newoff` 624 by 0.125 |
| new vs head | FPGA | 1 | `new` 1499 by 0.0625 (1 ulp), `head` tie 258/1499 | same |
| new vs base | FPGA | 0 | both 1499 by 0.0625 | same |

Setup: qwen3-4b at tp2, 1 user, 1,024 prompt tokens, temperature 0, `--pay-for-determinism`, 256 generated tokens, `new` free-running and every other arm fed `new`'s tokens. A repeat of `new` reproduced every score exactly. Record: `exec/results/p83-20261013/` in jhan's intel-AMX workspace.

The addition-order hypothesis is consistent with every measurement. Which arm's rounding is preferable is not decided here. Reviewers decide whether this closes the item.
