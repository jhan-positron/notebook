---
name: delphi-3b35-no-slice-bench
description: "On delphi-3b35 do not run bin/slice bench (it measures on slot 0 of the other users' half, and tests pin threads by slot); the host clock prints UTC, so watchers must compare epoch seconds"
metadata:
  node_type: memory
  type: reference
  originSessionId: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6
  modified: 2026-11-20T13:58:58.588Z
---

Measured on 2026-11-20 on delphi-3b35 (final head of tron PR 5022, session of the muse-glimmer folder).

- `bin/slice route` answers `local-legacy` there (8 cards, shared Dice not configured).
- `bin/slice bench` (also `--update <test>`) measures each test on the first slot of each NUMA node. With two
  tests, one always runs with SYSTEM_CONFIG `--instance 0,N`, which is the first half of the machine (Brian Hamon,
  John Pruitt). Code: `_cmd_bench` in bin/slice, `parallel_slots` and `instance = slot // s`.
- tron test binaries call the system init and pin their threads by that value, also with the fake device. The
  log line is "INIT: Pinning application cores to ...". `t_amx_dispatch_dtype` starts 55 pool workers.
- So the tool cannot run under jhan's rule "our half only, do not disturb the other half". My interpretation:
  this holds for every `bin/slice bench` and `bin/slice run` of more than one slot on that machine.
- What worked instead: direct runs pinned to CPUs 96-143 with SYSTEM_CONFIG="--instance 1,2"; registry metadata
  (`skip_return_codes` in config/test-benchmarks.json) edited by hand; `bin/slice bench --check` and
  `--check-platform` (both read-only) plus a round trip through the tool's `format_bench_json`; wall times with
  /usr/bin/time. The review reply must say that `times` were not re-measured, and why.
- The host prints UTC (`date`, `uptime -s`). claude-box prints Pacific time. My reboot watcher compared the two
  strings and woke 8 hours late. Compare epoch seconds (`date +%s`, `/proc/uptime`).
- State after the reboot of 2026-11-19 21:19 PST: kernel 6.8.0-138, all 8 FPGA cards visible (0000:3b:00.0 is
  back), the first half runs the disagg deployments dev1 and dev2 (two rinzler servers, 31 busy threads each,
  load average 64). John Pruitt keeps to FPGAs 0-3 (his message of 2026-11-19 23:48 PST).
- Cost of a pass there: an option-ON build of runtron and 3 unit tests takes about 5 minutes on CPUs 96-143
  (-j40, ccache, BUILD_INGEST_MODELS=OFF); the 14 unit-test runs take about 14 s.
  Scripts: `~/workspace/intel-AMX/exec/pr5022-final-20261119/` (build, tests, object compare, registry check).

**How to apply:** when a tron review asks for `bin/slice bench --update` and delphi-3b35 is the only AMX host
available, do not run the tool. Do the hand edit and the read-only checks above, and report the limit plainly.
Related: [[delphi-3b35-default-server]] (in the parent project folder), [[changes-need-system-tests]],
[[review-replies-keep-simple]].
