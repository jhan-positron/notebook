---
name: talos-rest-api
description: "Talos (the internal test-results service behind the 'View in Talos' links of the nightly Slack reports) answers plain HTTP at http://talos:5000 from agentsrv: session list, one session, per-sample metrics; found 2026-11-25"
metadata:
  node_type: memory
  type: reference
  originSessionId: 8c78edcb-78c6-4643-820a-9f4db3e627b1
  modified: 2026-11-26T05:44:11.649Z
---

Found on 2026-11-25 from agentsrv, no login needed. The web page is `http://talos:5174/sessions/<uuid>`; its data comes from a REST service on port 5000.

- `GET http://talos:5000/sessions`: every session since 2024 as `{"entries": [...]}` (13,329 sessions, 7.5 MB, under 1 second). No filter parameter has an effect. `/sessions/` with a trailing slash is 404.
- `GET /sessions/<uuid>`: one session. `GET /sessions/<uuid>/metrics`: every sample of the session (17 MB for a nightly): per-user `tps` and `ttft` records, `score2` records with `tps_mean`, `min_tps`, `p05_tps`, `prefill_mean`, and soak records. Also `/artifacts`, `/graphs`, `/testruns`, `/logs`.
- A nightly session: `name` "System CI (MM/DD/YYYY)", `runner` "system-ci-runner", `dut` (delphi-3bda or andoria-b1a3), `tron_version` like `v2026.11.25-73ab1891`, `platformd_version`, `bitfile_version`, `started`, `ended`. Reruns by hand have other runners (agentsrv, worker-*).
- While a nightly session runs (found 2026-11-26) its `name` is "Performance Benchmarks (MM/DD/YYYY)", it has no `dut`, `hostname` or soak fields, and its `ended` is the end of the first phase (functional tests), not of the session. The performance fields are filled as the tests finish (all 12 present at 05:40 UTC). The machine is in `GET /sessions/<uuid>/logs`: a line "Connecting to <machine>.positron.internal". The uuid (version 1, made at session start) stays the same when the session gets its final name "System CI". A night that never finishes keeps the name "Performance Benchmarks" (2026-11-01 both machines, 2026-11-08 andoria-b1a3).
- Performance fields are named `<model>_tps @ <users>` and hold one string: `77.25 (std dev 0.90) TTFT 3725ms, prefill 275 tok/s (992 observed prompt tok, 1% cached) prompt=1024 generate=1536 ... users=8 mode=sharegpt`. A failed test holds `FAILED (...)`. Accuracy fields are `mmlu_pro_<model>`.
- The decode rate and TTFT equal the numbers of the Slack report in #ci-cd-notifications (checked for 2026-11-25, both machines). The Slack report adds the thresholds and the slowest user; Talos adds the standard deviation.
- Timing of a delphi-3bda nightly (2026-11-25): start 03:34 UTC, last performance test 05:11 UTC, last accuracy test 08:23 UTC, end 11:26 UTC. andoria-b1a3 starts at 03:06 UTC.

A parser and a per-night store exist in `muse-glimmer/pr5022-nightly-watch/watch.py` ([[pr5022-nightly-watch]]).
