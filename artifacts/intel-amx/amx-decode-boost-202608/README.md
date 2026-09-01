# AMX decode-boost measurement raw data (delphi-3bda, 2026-08-31 .. 2026-09-01)

Analysis page: intel-AMX/PR3879/make-sense-amx-vs-avx.html (artifact db6b18c8-0696-417a-ad22-21efa86544b7).
Campaign scripts: intel-AMX/exec/fence-20260831/, exec/perfstat-20260831/, exec/ctxfill-20260901/.
Model: ingested-qwen-3-4b-instruct-2507-tp2. Host: delphi-3bda (2x Xeon 6962P).

- fence-20260831/: kvwait record files (gzipped; format: 8-byte count then 24-byte records
  t0_tsc,dur,tag; tags 7600 F3, 7601 F1, 7602 extend-enqueued, 7603/7604 attention pipeline),
  arms mirror vs same-binary kill switch, ctx {256,2048,8192} x 3 reps. Binary 6b1fead791.
- fence2-20260901/: same grid, 2 reps, plus tag 7605 (payload = per-pass pure attention wall,
  TSC cycles). Binary 376db1c9af.
- perfstat2-20260831/: perf-stat round 2 text output (three arms, 12s windows; paranoid
  set/restore lines included). Binaries 662f820d (canon) / 235b516d (mirror).
- ctxfill-20260901/: the deployable boost-vs-context grid (clean vs mirror, commit-pinned
  60d66d9c04, 8 reps, Latin-square order) + curve.json medians.
- extract.py: per-token window extractor for the kvwait files (decode windows require
  exactly one 7602; TSC at 2.7 GHz).

TSC base clock 2.7 GHz. Fence definitions: tron-perf-fluctuation project, stall-map section 3.6.
