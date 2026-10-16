The deferred-dotter measurement for the open item "AMX-disabled slowdown" ran on 2026-10-13 from 15:58 to 17:13 UTC. The description's section "CPU attention" now holds the table, and the open item is updated.

**Short version.** A probe build that constructs the dotters of a page only at its first row-major row (commit `ca6456b7dc` on `ea94e95a4e`, a 26-line change in `h/tron/models/self_attention.hpp`, not in this PR) recovers part of the loss with AMX disabled: +2.3 % TPS (tokens per second per user) in the tp2 1,024-token cell, +1.6 % in the tp2 8,192-token cell, +0.2 % in the tp4 cell. With AMX enabled it costs nothing measurable (inside the band in all three cells). Against the parent with AMX disabled, 1.5 %, 1.5 %, and 1.0 % remain, the first beyond its band.

| Cell | lazyoff vs newoff | lazyoff vs headoff | newoff vs headoff (this run) | lazy vs new |
|---|---|---|---|---|
| tp2, 1,024 tokens | +2.3 % (t +8.5), beyond | -1.5 % (t -3.8), beyond | -3.7 % (t -16.5), beyond | -0.1 %, inside |
| tp2, 8,192 tokens | +1.6 % (t +19.2), inside the 0.40 TPS floor | -1.5 % (t -19.5), inside | -3.1 % (t -45.2), beyond | +0.1 %, inside |
| tp4, 1,024 tokens | +0.2 % (t +1.5), inside | -1.0 % (t -2.8), inside | -1.2 % (t -4.2), beyond | +0.3 %, inside |

`lazy` is the probe build, `lazyoff` is that build with `TRON_AMX_DISABLE=1`. The other arms and the band rule are those of the description's CPU-attention section: qwen3-4b, 8 users, 256 generated tokens, 3 repetitions, software attention, the band is twice the larger sample standard deviation with a 0.40 TPS floor.

So the dotter construction explains part of the slowdown in the tp2 cells. The remaining 1.0 % to 1.5 % has no measured cause. The open choice for reviewers: the deferred-dotter change can join this PR as a further commit (with the step-4 checks and the CPU cells re-run), or follow in a later PR.
