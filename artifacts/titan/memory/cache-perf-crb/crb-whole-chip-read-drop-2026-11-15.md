---
name: crb-whole-chip-read-drop-2026-11-15
description: Where the 120-thread read-drop investigation of 2026-11-15 lives (report, facts sheet, runners, root-counter scripts) and how its runs were driven on CRB
metadata:
  type: reference
---

Investigation of the question "why did the whole-chip rate fall with the new read kernel" (asked 2026-11-15).

- Report: `crb/new-test-kernel/whole-chip-read-drop.html`, built by `crb/tmp/agent-scratch/w120-2026-11-15/report_w120.py` from `FINDINGS.md` in the same folder. Edit the generator, not the HTML.
- Runners: `bwx12` (window-depth kernels) and `bwx13` (scrambled-order kernels) under `crb/tmp/agent-scratch/bwx1{2,3}-2026-11-15/`, on CRB under `~/cache-perf/bwx1{2,3}-20261115/`.
- Run scripts in `w120-2026-11-15/`: `rx.sh` (plain), `rg.sh` (simultaneous processes, mixed kernels, latency probe), `rc.sh` / `rc2.sh` / `rgc.sh` (mesh counters with `sudo -n perf stat -a`), analysis `an.py`, `anc*.py`, `ang.py`. Window-size test: `robsize/`.
- Result folders: `crb/results/w120-*`.
- Root on CRB: on 2026-11-15 the user approved `sudo perf stat` for mesh counters (and temporary settings changes; none was made) for that investigation. That approval does not carry to a later task: ask again.
- CMN watchpoints work for CBusy and SrcID on DAT/RSP flits to core ports (`watchpoint_down`, `wp_chn_sel`, `wp_val`, `wp_mask`; mask bit 1 = ignore); event sets are in `sets4.txt` to `sets6.txt`.
- The `cd` hook of this shell prints a directory listing; use `cd X >/dev/null`.

Related: [[crb-scaled-perf-counts]], [[review-loop-claim-defect-classes]].
