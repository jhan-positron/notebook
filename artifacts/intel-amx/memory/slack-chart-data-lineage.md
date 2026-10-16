---
name: slack-chart-data-lineage
description: Where the qwen-3-4b-tp2 decode/prefill charts posted to #intel-amx (2026-08-21) get their numbers; prefill mirror column uses the inc2 binary, not arena
metadata:
  type: project
---

The two bar charts jhan posted to Slack #intel-amx (C0BRZQDAYMS) on 2026-08-21 are the
`tron-amx-distilled.html` charts (exec/gen_distilled.py DECODE / PREFILL dicts).
Verified 2026-08-25 by recomputing from raw logs (tmp/amx-raw-data/chart-check.csv):
- decode canonical: exec/results/t4/t4-suite.txt arm canonical-amx vs clean
- decode arena-mirror: exec/results/t4/p2-inc3-arena.txt TRON_AMX_DISABLE=0 vs t4-suite clean
- prefill canonical: t4-suite canonical-amx
- prefill "arena-mirror": t4-suite arm mirror-amx = increment-2 (3-plane) binary, NOT the arena binary.
  Arena's own prefill gains are ~2 pp lower at 1u/2K, 8u/2K, 8u/8K (+44.3/+105.5/+41.7/+97.8).

Raw-data package for Jeremy: tmp/amx-raw-data/ (CSV + raw logs + README). Not yet posted to Slack.

**Why:** Jeremy asked for the raw numbers; any follow-up must cite the right file per series.
**How to apply:** when quoting mirror prefill gains, say which binary; prefer arena numbers for the opt-in config. See [[amx-tron-softattn-project]].
