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

- fence3-20260901/: THREE stamped arms (canonical-config 0148c218 / mirror-config 376db1c9 /
  kill switch on the mirror binary), ctx {256,2048,8192} x 2 reps, tags 7600-7605.
- perfstat3-20260901/: perf-stat round 3, phase-locked (fresh workload per measurement, window at
  decode token 400 read from the stamp records), brace groups <=3 GP; cache ladder + DRAM locality
  + dTLB + core + msr + uncore + turbostat; 4 of 54 windows flagged RUN-ENDED-DURING (excluded).
  Raw perf text + parsed.json.

- ctxfill2-20260901/: curve extension - commit-pinned clean vs mirror at ctx {2048, 8192, 32768},
  8 reps, Latin-square order; same builds as ctxfill-20260901 (/var/tmp worktrees). curve2.json
  medians. Result: +5.0 / +18.0 / +27.6%.

- thp-20260901/: THP experiment on the K mirror arena - same stamped mirror binary, arms base vs
  TRON_AMX_MIRROR_THP=1 (2 MiB-aligned + madvise(MADV_HUGEPAGE)); Part A fence grid ctx {2048,8192}
  x 3 reps (kvwait gz), Part B phase-locked counters (thp.txt). Result: 4K walks -98%, wall time
  unchanged (<0.4%). Note: the AnonHugePages lines in thp.txt read the timeout wrapper's process
  (script bug), not runtron - disregard them; the walk counters are the proof.

- fallback-20260901/: per-cause AMX dense-path fallback counters (TRON_AMX_FALLBACK_COUNTERS build
  of the fence branch at 3cd2670df1), mirror arm, ctx {256,2048,8192} x 2 runs. Decode fallback =
  partial tail page only (72,576 = 252 tokens x 36 layers x 8 KV heads at every ctx); prefill
  fallback = causal-mask range cut only. Whole-run coverage 92.19% at 2K / 97.77% at 8K matches the
  08-31 counter-summary (92.2% / 97.8%) exactly.
- single-attn-20260901/: the single-attention phase probe (page section 7.2.1). kvwait files
  (gzipped) with tags 7600-7605 plus 7606-7627 = worker-0 per-token phase counters (tag table in
  scripts/extract-sa.py: unit counts AMX/dotter/empty, cycles for QK / softmax / PV / state on both
  paths, Q pack, tile region, page-range wall, run_sections, upstream wait, joins, barrier). Three
  arms (canon / mirror / disable = kill switch) x ctx {256,2048,8192} x 2 reps, 1u; branch
  jhan-amx-fence commit 8fd1e7798d (probe gated on TRON_ATTN_PHASE=1). phases-*.json = per-cell
  medians, summary.json = per-unit split + speedups. Binaries built in tron-fence-amx/gen as
  runtron.samirror / runtron.sacanon (sha256 in single-attn.txt).

## Canonical paths for refresh (resolved 2026-09-04)

`WS` below is `claude-agentsrv:/home/jhan/workspace/intel-AMX`, on the shared
home filesystem used by the delphi-3bda campaigns. These roots were resolved
from the campaign scripts and checked against the existing copies:

- Result directories in this registry map to `WS/exec/results/<directory>/`.
- `extract.py` maps to `WS/exec/fence-20260831/extract.py`.
- `single-attn-20260901/scripts/` maps to `WS/exec/single-attn-20260901/`, except
  `patch-gen-stamps.py`, which maps to `WS/exec/fence-20260831/patch-gen-stamps.py`.
- The `.bin.gz` files are compressed archival copies of corresponding `.bin`
  records; compare decompressed content when an uncompressed source exists.

**Canonical-missing alert, 2026-09-04:** 63 capture files are absent from the
shared canonical result directories: 19 in `fence-20260831`, 13 in
`fence2-20260901`, 19 in `fence3-20260901`, and 12 in `thp-20260901`.
The repo archives were retained and may be the only remaining copies. The
complete per-file paths are in `logs/codex-handoff-20260904-review.md`.
No new raw capture files were added by this refresh.
