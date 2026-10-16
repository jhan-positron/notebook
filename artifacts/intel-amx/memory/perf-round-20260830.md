---
name: perf-round-20260830
description: "Perf regression round DONE 2026-08-30: PR3879 head 1d158249e matches Aug-25 refs (decode ±2.1%, prefill ±1.5%); gpt-oss-120b parity + 0 GB arena verified; summary posted as PR3879 comment 5471901175"
metadata: 
  node_type: memory
  type: project
  originSessionId: dee6ed75-0159-4faa-b91d-f5d79f0dbdba
  modified: 2026-08-30T23:23:28.218Z
---

Goal (jhan 2026-08-30): verify the 25 commits bbb55ae5f..1d158249e2 on jhan-amx-p0 (PR3879)
did not regress perf; post a summary comment to positron-ai/tron#3879.

Design: exec/p2-perf-round-20260830.sh on delphi-3bda (launched 20:47Z, PID 56777, guard held).
- AMX-boosted: qwen-3-4b / llama-3.1-8b / mixtral-8x7b, same 8 cells + arms (canon, mirror)
  as the Aug-25 round -> reference = exec/results/perf-round-20260825/perf-round.txt.
- gpt-oss-120b-tp2 (ineligible, 64Q/8KV/head64): 4 cells x arms canon/mirror/disable
  (disable = canon binary + TRON_AMX_DISABLE=1); baseline = within-round disable arm
  (router r0 captures are NOT comparable: traced + FPGA attention + different tree).
- 3 reps, rep-major, USE_HW_ATTN=0, -l 256. Script was 3-lens adversarially reviewed;
  13 confirmed findings applied (pipefail builds + cmp identical-binary check, PIPESTATUS
  RUN-FAILED, env -u TRON_AMX_DISABLE, OUT rotation, epoch clock lookahead vs 03:30Z CI prep,
  lease check before rinzler stage, trap pkills runtron; lib-guard.sh pgrep now matches
  runtron.canon/mirror).

DONE same night (main 20:47-22:14Z marker ok 0 fails; ext 22:20-23:17Z marker ok).
VERDICT: no regression. Boosted decode vs Aug-25 within -2.1..+1.8% (the ±2% cells are
mixtral, historically noisiest), prefill within ±1.5%; mirror-over-canonical gains intact
(qwen +1.6/+3.6/+6.5/+9.8, llama +3.2/+6.2, mixtral -1.9/+9.6%). Numbers verified by 2
independent recomputations (44/44 cells exact). gpt-oss-120b: prefill parity ±0.1%; 1u decode
parity ±0.5%; 8u cells VERY noisy (disable arm 34% ptp at 2K) - the 3-rep "-8.3% mirror" scare
dissolved at 9 matched reps (per-rep matched deltas: 2K canon +0.0/mirror -1.0%; 8K canon
-3.2/mirror -0.4%; canon==disable binary + constexpr amx_eligible self_attention.hpp:1359
compiled out for head-64 -> no code mechanism, mirror parity contradicts AMX cost).
ARENA GATING VERIFIED LIVE: mirror binary logs "KV cache footprint: 1.10 GB DMA + 0.00 GB
K mirror in 10 books" for gpt-oss vs 0.11 GB mirror per 0.22 GB book for qwen (kv_bytes/2).
Footprint log prints only on >=1 GiB change (TRON_LOG_KV_GRANULARITY overrides; qwen 1u/2K
is silent without it - trap). Summary posted: PR3879 comment #issuecomment-5471901175.
Artifacts: exec/results/perf-round-20260830/{perf-round.txt,perf-round-ext.txt,perf-round.html,
pr-summary.md,diag-*.txt}; scripts exec/p2-perf-round-20260830{,-ext}.sh; report generator
exec/perf-round-20260830-report.py. lib-guard.sh pgrep now matches runtron.canon/mirror
(campaign scripts' renamed binaries were invisible to the no-runtron launch check before).
Reusable protocol notes: evening launches need the epoch-based clock lookahead (hhmm>=310
fires instantly at 20:xx); build() needs pipefail or a mirror-only compile failure silently
measures canon-vs-canon (cmp -s catches it); PIPESTATUS capture must precede any || list.

**Why:** the round is the PR3879 perf baseline for future regression checks; the traps above
bit or nearly bit this campaign.
**How to apply:** for the next perf round, copy p2-perf-round-20260830.sh (it has all review
fixes) and compare against THIS round's txt as the new reference.
Related: [[amx-tron-softattn-project]], [[delphi-3bda-hardware]].
