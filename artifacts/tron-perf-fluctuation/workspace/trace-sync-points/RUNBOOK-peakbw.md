# Runbook: peakbw — burst/peak measurement of host DDR and FPGA HBM

Written 2026-08-18 by the trace-sync-points session. Owner: Jibin (jhan).
Audience: the agent that prepares, executes, and analyzes this.
Status: **EXECUTED 2026-08-19** (campaign peakbw-20260819T221215Z, 19/19,
report status_report/DDR_HBM_peak_throughput.html). Verdicts: H1 no (decode
p99 28-30%; one non-decode end-of-run burst), H2 no (+0.3% vs 1.6% bar;
decode is latency-class at 2.15x saturation residency), H0 fires-confounded
(mem-bound share 25.9->30.2%, consistent with waiting, not a memory cause),
H3 no (HBM p99 identical 45.9% every draw). P1 notes: no RPQ_INSERTS
encoding on GNR (0x10 dead, 0x20 = write queue); occupancy 0x80/0x81 works.
Kept below for the record. Companion context:
`../intra-pass/CONTEXT.md` §5d/5e, `rtl-register-audit.md`,
`RUNBOOK-fpgastat-armB.md` (harness pattern this reuses), reports
03 (dram-ceiling), 04 (fpgastat), 05 (window-waits).

## 1. Why

Jeremy's point: both memory systems measured "barely 30% of bandwidth", but
those numbers are averages (host DDR: 1 s perf intervals; HBM: per-fence
windows of ~0.3/5.8 ms). Bursty traffic can saturate briefly while averaging
low. This campaign measures burst behavior directly and tests whether burst
pressure differs between fast and slow draws.

Standing context that bounds expectations (do not un-learn it):
- FPGA side, the victim cost of any burst is already measured: `mm_wmem_bp`
  (matmul engine stall on weight fetch) is constant ±0.8 µs/token across all
  draws (report 04). Bursts exist but their cost does not vary.
- The draw-level TPS fluctuation is localized to host thread handoffs
  (report 05). This campaign can *add* a memory-latency mechanism behind
  those handoffs, or close it.

## 2. Hypotheses and pre-registered decision criteria

| id | hypothesis | measurement | pre-registered criterion |
|---|---|---|---|
| H1 | Host DDR bursts approach the ceiling at fine timescales even though 1 s averages are ~12% | per-socket CAS bandwidth at 10 ms intervals, whole draws | characterization: report the peak-window distribution. "Burst-saturating" = any 10 ms window ≥ 70% of the same-counter calibrated ceiling |
| H2 | Memory-controller queue pressure differs between fast and slow draws (latency mechanism for the handoff level shift) | IMC read-pending-queue: occupancy ÷ inserts (Little's law → average queue latency), per 100 ms interval, plus the same counters during saturation calibration as the "what full pressure looks like" reference | suspect-confirming = slow4 vs fast4 RPQ-latency delta > 2× within-group sd AND slow-draw latency shifted toward the saturation reference; else H2 closed |
| H3 | HBM read bursts differ between fast and slow draws at sub-ms windows | fine-window fpga_use duty on ONE device (tier 2, needs rebuild) and/or sticky stall-reason flags (tier 1) | expected NO (stall cost already constant). Suspect-confirming = burst-window duty distribution differs fast4 vs slow4 beyond 2× within-group sd |
| H0 | CPU cores actually stall on memory more in slow draws | core-PMU memory-stall share on tron cores per draw | suspect-confirming = slow4 stall share > fast4 by > 2× within-group sd |

Denominator-trap rule from report 04 applies: compare absolute counts first,
shares second; slow draws have longer denominators by construction.

## 3. PREP checklist (all on delphi-3bda unless noted; light work OK during CI window)

**P1 — verify PMU event names (GNR names differ across kernels):**
```sh
perf list 2>/dev/null | grep -i -E 'unc_m_(rpq|cas)' | head
perf list 2>/dev/null | grep -i -E 'stalls_mem|memory_bound|topdown' | head
```
Needed: `unc_m_cas_count.rd/.wr` (or the `uncore_imc/cas_count_*` aliases
used by the drambw harness), `unc_m_rpq_occupancy_pch0/pch1`,
`unc_m_rpq_inserts.pch0/.pch1`, and a core memory-stall event
(`cycle_activity.stalls_mem_any` or the topdown memory-bound group).
Record the exact names in the harness copy. If RPQ events are absent, H2
falls back to latency inference from 10 ms burst shape only — say so in the
report rather than substituting a guess.

**P2 — counter budget check:** one IMC box has 4 general counters. Plan:
ONE perf instance, `-I 10`, events = cas rd + cas wr; a SECOND perf
instance, `-I 100`, events = rpq occupancy + rpq inserts (per pchan if the
counter budget allows, else summed). Verify no multiplexing is reported
(`perf stat` prints multiplexing percentages — require 100% running time).
Core-PMU stall events run in a third instance pinned to the tron core list
(24/25/48/151 + TX/RX cores 3-6,147-150), `-I 1000`.

**P3 — calibration extension:** reuse the drambw in-campaign ceiling
calibration (28× `tools/membw`, machine quiesced) but record BOTH counter
sets during the plateau: the CAS ceiling AND the RPQ occupancy/latency at
known saturation. This is the reference signature for H2. (The ×2.01 DDR5
sub-channel scale gotcha applies to CAS bytes; all comparisons same-counter,
scale-free.)

**P4 — harness:** copy `pfgate-3bda/tools/fpgastat-campaign.sh` →
`peakbw-campaign.sh`. Keep: smoke barrier (TPS ≥ 160, token sha, kvwait
liveness), host lock, TRACER_CORE=16, restore trap, CONTROL_ROUNDS.
Change: add the three perf instances per draw (start after model-load
marker as in the drambw harness, stop at draw end; files
`ddr-cas-10ms.csv`, `ddr-rpq-100ms.csv`, `cpu-memstall.csv`); add the P3
calibration step; drop `FPGA_USE_FENCE` (use poller or tier-2 mode per P6).
`bash -n` clean before launch.

**P5 — HBM tier 1 (no rebuild) scoping:** find a userspace read path for
the audit's tier-list registers — `activ_mgr_dbg_2` (sticky stall reasons),
`cmd_cnt`, and `id_dat` @ 0x000000 (this read also settles the standing
tracer-ABI question; see report 04 quarantine). Candidates: the `fpga-reg`
tooling in the tron repo, or a small addition to the fpgause probe. If no
path exists without a rebuild, fold these reads into the tier-2 build (P6).
Protocol per draw: clear/read stickies before, read after — "did any stall
reason ever fire during this draw" is burst evidence with no sampling-rate
limit.

**P6 — HBM tier 2 (rebuild, optional but preferred):** add
`TRON_FPGA_USE_WINDOW_US=<n>` to the fpgause probe: a poller thread
(pinned core 16-adjacent spare, NOT 3-6/24/25/147-150) flipping the
fpga_use window on ONE device at ~200-500 µs cadence, kvwait tags in the
8xxx band (new seg offset, e.g. +60). Each flip costs ~30-40 µs MMIO, so
200 µs cadence ≈ 15-20% of one spare core and zero scheduler-thread cost —
but verify perturbation via the smoke barrier and 3 control draws as
always. Rebuild = new sha; re-verify gen-plugin 7601 hand-edit; update
`EXPECTED_BIN_SHA`; freeze the patch in `data/` (provenance rule).

## 4. Launch (after PREP; outside the CI window 02:30–11:30 UTC daily)

Machine guard as in RUNBOOK-fpgastat-armB §3 (no runtron, no young/
unfinished roots, host lock, coordinate with any active peer session).
```sh
D=/scratch/jhan/perf-fluctuation/pfgate-3bda
ROOT=$D/peakbw-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p $ROOT && cp $D/tools/peakbw-campaign.sh $ROOT/harness.sh
ssh jhan@delphi-3bda "setsid env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 \
  ROUNDS=16 CONTROL_ROUNDS=3 EXPECTED_BIN_SHA=<sha per P6, or current 4ceaca1a…> \
  CAMPAIGN_ROOT=$ROOT INSTALL=<install per P6> \
  PERFETTO_TPL_SRC=/home/jhan/workspace/common/perfetto.cfg-fpgastat2 \
  TRACER_CORE=16 <FPGA_USE knobs per P5/P6> \
  bash $ROOT/harness.sh > $ROOT/harness.stdout 2>&1 < /dev/null &"
```
Safe stop: `kill -TERM $(cat $ROOT/harness.pid)`; wait for RESTORED.

## 5. Analysis (alpha-side; extend tools/, keep everything durable)

- **DDR bursts (H1)**: per draw, distribution of 10 ms-window bandwidth ÷
  calibrated ceiling; report p50/p99/max windows; overlay fast4 vs slow4.
  Same chart form as the dram-ceiling report §1 (dots vs red ceiling line),
  one dot per draw at its max 10 ms window.
- **RPQ latency (H2)**: occupancy ÷ inserts per interval → per-draw
  distribution; compare against the saturation-calibration reference and
  fast4 vs slow4 (criterion above). Exposure-weighted ratios of sums.
- **CPU memory stalls (H0)**: stall share per tron core per draw vs TPS.
- **HBM (H3)**: tier 1 — sticky flags fired per draw (binary table, fast vs
  slow); tier 2 — fine-window duty distribution per draw: p99/max window
  duty, burst-length estimate (consecutive high-duty windows), fast4 vs
  slow4. Cross-check total read cycles against the known constants
  (47,520 + 253,440 per token) — the fine windows must sum to the same
  totals, or the mode is broken.
- Freeze/preamble hygiene and per-device reporting as pre-registered in
  RUNBOOK-fpgastat-armB §3.

Report: `status_report/<date>-01-peakbw.html` (pure-ASCII rule, entities
only), artifact via the Artifact tool; archive CSVs + manifest to
`data/peakbw.tgz`; update `../intra-pass/CONTEXT.md` and session memory.

## 6. Outcomes

- **A (expected): all quiet** — DDR 10 ms peaks well under 70%, RPQ latency
  flat vs the saturation reference and equal fast/slow, stickies equal,
  HBM fine-window bursts identical fast/slow. Then: burst/peak saturation
  is excluded at both memories; the exclusion ledger line for DRAM/HBM gets
  strengthened from "average utilization low" to "burst-resolved, victim
  cost constant"; the host-handoff investigation (report 05 §6: thread
  placement, wakeup path, NUMA snapshots) stays the critical path.
- **B: H2 or H0 fires** (queue latency or CPU memory stalls higher in slow
  draws) — memory latency becomes the mechanism candidate BEHIND the
  handoff level shift; next: NUMA/placement per-draw snapshots correlated
  with the same draws (already designed in report 05 §6), since placement
  is the natural per-bring-up cause of latency differences.
- **C: H1 fires alone** (deep bursts but equal fast/slow) — a
  characterization fact for capacity planning, not a fluctuation cause;
  record it and stop.
- **D: H3 fires** (HBM burst structure differs fast/slow) — contradicts the
  constant stall counter; before believing it, re-verify the tier-2 mode
  against the known per-token totals and re-check the denominator trap.
  If it survives, reopen the chip-side track (campaign #2 register set).

## 7. Cost and priority note

Machine cost: one campaign (~35 min) + possibly one rebuild. Priority:
report 05's placement/wakeup instrumentation answers the SAME "what sets
the per-draw level shift" question more directly; if machine time is
scarce, run that first and fold this campaign's perf instances into it —
the two instrument sets do not conflict (different PMU boxes) and P4 can
host both.
