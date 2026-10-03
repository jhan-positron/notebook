---
name: attention-stats-claude-page
description: "2026-09-29 new-counters/attention-stats-claude.html = why/what page for the PR 4596 counters (coarse-to-fine figure, stderr line-by-line, closed-form arithmetic on samples A/B/C/D); check script + data lineage + traps"
metadata:
  node_type: memory
  type: project
  originSessionId: 7684287b-c61d-49c7-bd35-07b469748b28
  modified: 2026-09-30T04:46:45.017Z
---

Page: `PR3879/new-PRs/new-counters/attention-stats-claude.html` (about 115 KB, 12k words, pure ASCII, light theme, Wade-page CSS). Check script next to it: `attention-stats-claude-check.py` (72 closed-form checks against the raw files, writes facts.json to stdout). Built 2026-09-29 by workflow wf_032a5012-c97 (4 gather + 1 write + 3 verify/fix rounds), then hand-checked.

Data lineage (all qwen-3-4b tp2, 8 users, prompt 1024, 256 tokens, 3bda our half):
- Sample A (CPU attention, AMX on, head bff317e0d3, 09-29 23:24 UTC): `exec/results/attnstats-20260929-cpu/rt/q3-4b-tp2-8u-p1024__cpu__headon4__rep1.log`
- Sample B (FPGA attention, OLD head cbf1bb6c0c, 09-25 13:24 UTC): `exec/results/attnstats-20260925-fpga/rt/..._fpga__headon2__rep1.log` (labels lack the rule, no listener_jobs/kv_only_jobs/n_attn_workers keys)
- Cross-check C (09-24, head 9b3832eb4b): `attnstats-20260924/rt/...headon__rep1.log` vs `...headkill__rep1.log`
- Snapshot D: `attnstats-20260929-cpu2/leaves-latest/` (131 leaves copied one file at a time over 0.49 s, shell glob = alphabetical order)

Verified facts worth reusing:
- Decode closed forms: ready pages per (user, KV head, layer) = sum over s=1..255 of floor((1023+s)/64) = 4461; full pending page at s = 64/128/192 takes AMX (6912 = 3 x 2304); AVX tail sum 8064; context sum 293760; UHL = 2304.
- Prefill: 7168 ready visits per triple; per chunk per triple 192 visits / 8256 K tokens / 66 full-page AVX visits; chunk's own pages ALWAYS AVX (one-visible-range clause of is_dense_amx_page fails: a fresh page has one range per token, self_attention.hpp comment on the page-level visibility gate).
- FPGA sample: passes = 255 x 8 x 36; card tokens + AVX tail = context sum; prefill fpga_k_tokens x 8 = CPU run's ready_amx_k_tokens; T5 = 63 % of T2 (worker waits on the card).
- T2 (attn_elapsed) EXCLUDES the upstream K/V wait at the head; the Wade page's Figure 1 text says otherwise and is wrong.
- Timers sample A decode: T1 12.51 ms/forward, T4 sum of 35 periods 11.65 ms (93 %), T2 6.96 ms per worker per forward (56 %), T5 4.1 us/job (2.1 % of T2).

Traps:
- A multi-leaf FUSE snapshot is not one consistent read (worker sums > layer sums > forwards leaf; run advanced ~19 forwards during the copy). Take intervals from the same leaf.
- At bff317e0d3 listener_jobs was added at begin_forward: live read showed listener_jobs 8 ahead of token_jobs; fixed by 04da001cb5.
- The branch moved during the workflow (round-5 test-only commits 5eb8fa0419, 492345f04c, 5b6a5deb51, a80a07945e); none touches attn_stats.hpp. Meta line names 7f86648d10 / 04da001cb5.
- Verify lenses churn on ", so" splitting; 3 rounds went 41 -> 22 -> 20 high/medium findings, mostly style. Read the page yourself for the final pass.

Related: [[attn-stats-pr-implementation]], [[wade-pr4596-review-response]], [[attn-path-counters-design]].
