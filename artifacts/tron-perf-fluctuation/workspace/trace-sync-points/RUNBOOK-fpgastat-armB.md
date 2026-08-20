# Runbook: fpgastat arm B — fence-aligned FPGA counters (run after the CI window)

Written 2026-08-17 by the trace-sync-points session; revised 2026-08-17 per
the Codex review (`from-codex/RUNBOOK-fpgastat-armB-review.md`). Owner:
Jibin (jhan). Audience: the agent that executes and analyzes this.
Companion context: `../intra-pass/CONTEXT.md` sections 5e,
`rtl-register-audit.md`, memory note `fpgastat-queued`.

Staged and verified: binary, harness (with automatic smoke barrier), Perfetto
template, analyzer (`tools/fpgastat_fence_dump.py`, dry-tested on arm A
data). No build steps remain.

## 1. Why — the discrepancy this test resolves

Two verified observations appear to contradict each other:

1. Pre-bypass analysis of `fill_logits_buffer()` showed the CPU spending long
   waits inside the [F1→F3] segment — waiting for FPGA wcls results. That
   motivated the hardware bypass, and the bypass confirmed those waits are
   real (pinning them changed the segment's timing exactly as predicted).
2. fpgastat arm A (`fpgastat-20260817T013917Z`) showed the FPGA nearly idle in
   aggregate: matmul engine busy 1.4% of cycles, HBM read duty ~6.7%, zero
   result-path backpressure, activation command queue empty at every 1 s
   snapshot — the chip waiting on the host.

**Hypothesis under test**: the FPGA's work is concentrated in the short
[F1→F3] segments (~0.5 ms of a ~5.5 ms token) and the chip is mostly idle
during the rest of the cycle. Arm A's 1 s windows cannot resolve this.
Recognized alternatives that would also reconcile the two observations:
arm A's regime perturbation (TPS halved to 87–92 — root cause found
2026-08-17: `--tracer-core 5` collided with the TX-38 driver thread pinned
to core 5; NOT driver-detail span volume as first assumed — fence13pf ran
every category at 177 TPS without the tracer), the MM counters not covering
every FPGA engine, and instrumentation/ABI error (arm A also missed the
core tracer counters — wrong category).

Arm B measures the chip **per token, per segment**, aligned with the CPU-side
view, at production speed. The sharp question: **is matmul/HBM activity
concentrated in [F1→F3] versus the rest of the token cycle, and does that
concentration differ between fast and slow draws/tokens?**

## 2. What — instruments and recorded data

Binary `install-fpgause`, sha
`4ceaca1a36e16d983a3c4a508d1ffd97ee0ceec53146e8bd4cff11a54777c662`
(main e8deb5444 + kvwait probes + fpga_use fence-flip; exact source patch
archived per §5). Two mechanisms:

**A. Fence-flip chip counters (kvwait records, per token, per device).** The
scheduler thread flips the chip's metrics window at every fence. Tags
`8000 + dev*100 + seg + field`, t0 = shared flip-loop TSC (see boundary
caveat below), dur = counter value:

| seg | window measured | closing fence |
|---|---|---|
| +20..+26 | [F1→F3] segment of the inter-pass window | Fence 3 (tag 7600) |
| +40..+46 | **rest-of-cycle** [F3→next F1] | Fence 1 (tag 7601) |

**Window semantics — read carefully:**
- The full inter-pass window is `[open→F1→F3→end]`. The `+20` window covers
  only its `[F1→F3]` (logits/streaming) segment, not `[open→F1]` or
  `[F3→end]`.
- The `+40` window is NOT the intra-pass span. It is the complement:
  `F3_i→F1_(i+1) = [F3→end]_i + intra-pass span_(i+1) + [open→F1]_(i+1)`.
  The fence-3 work showed `[open→F1]` alone can carry material jitter, so
  never present `+40` numbers as "the span". This two-flip design cannot
  attribute rest-of-cycle counters specifically to layers 0–35.
- **Token ownership rule**: a `+20` group closed at `F3_i` belongs to
  `[F1_i→F3_i]` of token i; a `+40` group closed at `F1_i` belongs to
  `[F3_(i-1)→F1_i]`, i.e. it STARTED at the previous token. A nearest-fence
  join shifts rest-of-cycle values by one token — use closing-fence order.

field: 0=hbm_timer 1=hbm_read_cycles 2=mm_timer 3=mm_bp 4=mm_in_prog
5=mm_rmem_bp 6=mm_wmem_bp. Clocks: mm counters at 550.0 MHz, hbm at
368.75 MHz (`rtl-register-audit.md`). hbm covers pseudo-channel 0 only.
Fence mode records fields 0–6 only: no `cb_stat.aq_empty` (field 7) and no
`rmem_ctrl` upper-FIFO (field 8) — those exist only in arm A's poller data.

**Boundary precision caveat (do not claim exact fence alignment):**
- The flips are fence-adjacent, not fence-aligned. Tag 7601 and the
  `"fence 1"` instant are emitted inside the generated plugin;
  `wait_for_coop_gof()` and listener enqueue run before
  `fpga_use_fence_flip(1)` executes at the top of `run_logits()`. The
  fence-3 flip runs right after the 7600 stamp / `"fence 3"` instant.
- `metrics.cpp` takes ONE TSC (`t0`) before a serial stop/read/start loop
  over devices 0–3, so each device's window boundary is shifted differently
  and an MMIO gap is excluded at each transition. The shared `t0` is not any
  device's exact flip instant.
- Consequence for analysis: validate per device via the timer residual
  (`mm_timer/550.0e6` and `hbm_timer/368.75e6` vs the fence-measured wall
  time), report the residual distribution per device, and treat differences
  below the residual scale (tens of µs) as unresolved.

**B. Perfetto per draw** (config `~/workspace/common/perfetto.cfg-fpgastat2`):
categories scheduler + driver + model (= the proven fence13pf overhead class)
+ cpufreq at 100 ms; 35 s duration (was 25 s — a 4096-token draw at
150–165 tok/s generates for 24.8–27.3 s plus prefill/startup, so 25 s could
truncate slow draws). This carries: "fence 1"/"fence 3" instants, scheduler
and driver spans, and FPGA tracer counters under `driver` (10 µs chip status
via the mailbox tracer, enabled by `--tracer-core`).

**Tracer core placement (hard requirement)**: the tracer thread spins; it
MUST NOT share a core with a runtron-pinned thread. Observed pins on 3bda
tp4 instance 0: TX 3/4/5/6, work_queue 24, worker 25, RX 147–150. Core 5
collided with TX-38 and halved TPS (arm A, and the first arm B smoke at
80.3 — caught by the smoke barrier 2026-08-17 11:34 UTC, zero campaign
draws burned). Harness default is now `TRACER_CORE=16`; verify after any
launch that the trace shows `16/0-Tracer` alone on its core.

**Tracer caveats:**
- Tracer counters are change-only `TRACE_COUNTER` events, not regular
  samples; the hardware may also drop mailbox samples. A missing track can
  mean constant value, late trace start, or absent instrument — never treat
  absence as zero. Carry the last known value into each analyzed window.
- **`rmem_bp` is QUARANTINED**: tron decodes bit 23 under that name, but the
  RTL audit identifies bit 23 as `rmem_rdy_legacy` (1 = room available) at
  RTL HEAD. The deployed bitfile (01.05.08.00) may have an older ABI, so the
  meaning is uncertain, not merely inverted. Do not interpret this track
  until the ABI is settled. **Settling it is a pre-analysis requirement**:
  read `id_dat` @ 0x000000 to pin the bitfile, and ping the hardware team if
  `act_inprog`/`act_pending`/`compute_phase` (bits 20/21/[29:28]) remain
  absent.
- Tracer `rmem_depth` reports the LOWER 4K FIFO; backpressure is decided on
  the upper 1K CDC FIFO (threshold 870/1024) which the tracer does not carry.
- `inprog_pause` (bit 22) is usable with documented caveats.

Plus the standard kvwait tags (fences 7600/7601, per-request 3000/4000+dev,
per-block 7500+ix) for token bracketing.

**Other instruments the harness retains** (inherited from the lowfreq
lineage; kept deliberately — they are cheap, run outside the model process,
and give the report its standard power/frequency/IOMMU context): per-draw
turbostat (5 s), dmar IOMMU `perf stat` (1 Hz), MSR throttle-log
clear/read (0x19C/0x64F/0x1B1), RAPL snapshots. None of these touch the
FPGA path.

Known perturbation to carry into the report: fence-flip costs ~30–40 µs of
MMIO per fence on the scheduler thread (~1.5%/token). It is measured by the
in-campaign matched control (see §3), NOT by comparison with the wadefix-on
campaign (different binary and capture context; also the [F1→F3] segment
contains the F1-side flip but not the F3-side flip, so cross-campaign
segment comparison cannot isolate the two-flip cost). The FIRST `+40`
group of each run is invalid (no matching start) — the analyzer drops it.

## 3. How — launch and analysis

### Preconditions
- Outside the nightly CI window **02:30–11:30 UTC, every day** (not just
  "after 11:30 today"). The harness does not enforce the clock window —
  the launcher must.
- Machine guard (durable checks, no session-specific state): no `runtron`
  process on 3bda; no campaign root younger than 3 min and no root without
  `finished-epoch.txt` under `/scratch/jhan/perf-fluctuation/{deep-dive,pfgate-3bda}/`;
  the harness additionally takes a host-wide lock
  (`/var/tmp/jhan/3bda-campaign.lock`), which closes the remaining race.
  If another agent session is active on 3bda, coordinate before launching
  (check `ListAgents`; peer sessions have used the name
  `ingested-llama8b-ec`). Fallback contact: the owner (jhan).

### Launch
```sh
D=/scratch/jhan/perf-fluctuation/pfgate-3bda
SHA=4ceaca1a36e16d983a3c4a508d1ffd97ee0ceec53146e8bd4cff11a54777c662
ROOT=$D/fpgastat-armB-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p $ROOT
cp $D/tools/fpgastat-campaign.sh $ROOT/harness.sh
ssh jhan@delphi-3bda "setsid env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 \
  ROUNDS=16 CONTROL_ROUNDS=3 EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
  INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-fpgause \
  PERFETTO_TPL_SRC=/home/jhan/workspace/common/perfetto.cfg-fpgastat2 \
  FPGA_USE_FENCE=1 FPGA_USE_POLL_MS=0 TRACER_CORE=16 \
  bash $ROOT/harness.sh > $ROOT/harness.stdout 2>&1 < /dev/null &"
```
Notes: stdout lives under `$ROOT` (not /tmp); `INSTALL` is passed explicitly;
the harness writes its PID to `$ROOT/harness.pid` and hostname to
`$ROOT/harness.host`. Monitor via NFS tail only (no benchmark keywords in
helper cmdlines).

**Safe stop**: `ssh jhan@delphi-3bda "kill -TERM \$(cat $ROOT/harness.pid)"`.
The TERM trap runs the full restore (engine kill, perfetto daemons down,
rinzler trio restart) before exiting; wait for `$ROOT/RESTORED` or
`$ROOT/RESTORE_FAILED` before touching the machine. Do not SIGKILL the
harness — that skips restore.

### Gates — enforced by the harness, not by operator attention
The harness now runs an automatic **smoke barrier** after the smoke draw and
refuses to start campaign draws unless ALL of:
- smoke TPS ≥ `SMOKE_MIN_TPS` (default **160** — one threshold, no ambiguous
  band; arm A's perturbed regime was 87–92, production ~181);
- smoke `tokens.out` sha256 equals the qwen-tp4 deterministic reference
  `66af1d58…` (same value across wadefix on/off);
- smoke `kvwait.bin` liveness (stdlib-python check, output in
  `smoke/kvwait-liveness.txt`): not truncated, ≥4000 each of tags 7601/7600,
  and in fence mode, for every device and both segments, the seven field
  counts equal each other and the closing-fence count (tolerance 2). The
  expected count derives from the OBSERVED fence count (~4105 = 4096
  generation passes + prefill/preamble), not a hard-coded 4096.
On failure: `SMOKE_BARRIER_FAIL` marker, `smoke-barrier.txt` with values,
exit 1, automatic restore. On completion the harness exits nonzero unless
all 16 campaign draws AND all control draws succeeded and restore passed.

**Matched control**: after the 16 fence-mode draws, the harness runs
`CONTROL_ROUNDS=3` draws named `control_XX` with `FPGA_USE_FENCE=0
FPGA_USE_POLL_MS=0` — same binary, config, harness, host state. This is the
flip-overhead comparison (explicitly setting POLL_MS=0 matters: the
harness default would silently re-enable the 1 s poller).

Per-draw checks already in the harness: bitfile consistency across draws,
instance/device-set checks, trace hard-validation (scheduler category),
effective `TRON_KVWAIT_FILE`/`TRON_FPGA_USE_*` captured in
`runtron-environment.txt` and campaign-level values in `identity.env`.

### Analysis — staged analyzer + pre-registered rules
Analyzer: `tools/fpgastat_fence_dump.py` (this repo; dry-tested on arm A
smoke data). It implements, per draw:
1. count-prefixed `(t0,dur,tag)` parse with truncation rejection;
2. preamble drop (`t0 ≤ 1e12`), freeze rule (drop draws with holes > 50 ms
   in the token stream from the fast4/slow4 sets; report hole counts),
   positional prefill/decode filtering as in `fence3_dump.py`;
3. closing-fence-ordered token join (ownership rule above); first `+40`
   group per device dropped as invalid; per-field completeness required
   (a token missing any of its 7 fields is dropped and counted);
4. counter invariants: `0 ≤ hbm_read ≤ hbm_timer`, nonzero timers, no
   32-bit-saturated timer, `mm_in_prog`/`mm_bp` ≤ `mm_timer`, and the
   documented allowance that the RMEM/WMEM approximate split can slightly
   exceed total backpressure;
5. clock identity per device/window: `hbm_timer/368.75e6` vs
   `mm_timer/550.0e6` vs fence wall time — the per-device residual is the
   flip-alignment error bound;
6. outputs: per-token per-device CSV of absolute cycles AND shares for both
   segments, a validation summary (machine-readable), and per-device +
   cross-device min/max/spread per token (pooled-only summaries can hide a
   single-card straggler).
Aggregation rules: group summaries are **exposure-weighted ratios of sums**
(not unweighted means of per-token ratios) — apply the same when reconciling
with arm A. Trace/tracer joins are restricted to trace-covered tokens
(record first/last covered fence per draw); the primary counter
distributions use the full valid kvwait population.

**Pre-registered decision table** (operating points chosen before seeing
data; report all raw distributions regardless):

| verdict | rule (median over valid tokens, per device) |
|---|---|
| "active in [F1→F3]" | +20 productive share `mm_in_prog/mm_timer` ≥ 25% AND +20 absolute `mm_in_prog` ≥ 50k cycles (~90 µs at 550 MHz) |
| "low-activity in [F1→F3]" | +20 `(mm_in_prog+mm_bp)/mm_timer` ≤ 5% AND +20 hbm duty ≤ 2× (+40 hbm duty) |
| otherwise | indeterminate — report distributions, no verdict |

`(mm_in_prog+mm_bp)/mm_timer` is an active-demand approximation, NOT
whole-chip utilization (MM counters do not cover every engine; hbm is
pchan-0 only — a per-channel byte rate may be ×32-extrapolated only under
the stated symmetry assumption; never multiply a duty percentage by 32).
Report productive and stall shares separately. Beware the denominator
trap: a longer host-paced window mechanically lowers shares — compare
absolute cycles first.
Fast/slow definitions: fast4/slow4 = 4 highest/lowest-TPS freeze-clean
draws; slow/fast tokens = top/bottom decile of F3→F3 period within a draw.
Correlations: Pearson on per-token values with Spearman as robustness
check. Missing-data policy: post-barrier misses should be ~0; any token
with an incomplete field set is dropped and the count reported.

Deliverables: distributions per segment; fast4-vs-slow4 and
slow-token-vs-fast-token comparisons of the chip-side numbers; tracer
(10 µs) view around a handful of slow tokens from the traces (usable
tracks only — `rmem_bp` stays quarantined); flip-overhead accounting from
the matched control (report [F1→F3] cost, rest-of-cycle cost, full F3→F3
cost, and per-device timer residual separately). Report:
`status_report/2026-08-17-01-fpgastat.html` (report 04), combining arm A
(with its trust split) and arm B; artifact via the Artifact tool; archive
extracted CSVs + a checksum manifest to `data/fpgastat-armB.tgz`; update
`../intra-pass/CONTEXT.md` and session memory.

## 4. Next step by outcome (decision tree)

**Outcome A — chip active in [F1→F3], low-activity in the rest of the
cycle** (per the decision table, consistently across devices). The
discrepancy resolves as time-concentration; no contradiction with arm A.
Note this does NOT locate the activity within layers 0–35 vs `[open→F1]` /
`[F3→end]` — the two-flip design cannot separate those. Combined with the
bypass verdict (window jitter = expression), attention shifts to the
rest-of-cycle:
→ Next: the zero-machine-time analysis — mine this campaign's existing
3000/4000 per-request stamps for per-layer chip turnaround vs host
inter-request gaps across the span; follow with per-layer bracketing
(7800+ band) only if the mining is ambiguous.

**Outcome B — matmul/HBM indicators are ALSO low during [F1→F3] while the
CPU waits.** State it exactly that way: the observed indicators are low.
The stronger claim (transport plumbing: result DMA pacing, mcnt mailbox
update latency, descriptor/doorbell round trips) additionally requires
time-aligned tracer evidence and exclusion of listener/scheduler-side work.
**Host issuance stays on the table**: arm A found the activation queue
empty, and fence mode does not record `aq_empty`/`rmem_ctrl` — so first
check tag-3000 dispatch timing and the existing 3000→4000/7500 stamps
before narrowing to DMA/mailbox/doorbell.
→ Next: per-block arrival campaign — tag 7500+block stamps exist on the
consume side; add `rmem_ctrl` upper-FIFO at high rate and `wim/rim`
host-path burst counters from the audit tier list; correlate block arrival
vs consume per token. Re-examine the bypass campaign's drain data
(site 4000−3000) under this lens.

**Outcome C — slow draws/tokens show chip-side deltas** (e.g., wmem stall
share rises in slow draws' windows, or hbm duty sags at equal absolute
read cycles): a chip-side **association** — not yet causation. A delta can
be a response to host command pacing, a ratio-denominator effect, or
unequal work. In particular, lower HBM duty at equal read cycles is
evidence of extra idle time, not an HBM cause. Effect-size bar: the fast4
vs slow4 group delta must exceed 2× the within-group standard deviation.
→ Next: campaign #2 from the audit's physical track — HBM thermal (BAR4
north/south: temperature + refresh band), `activ_mgr_dbg_2` stall-reason
stickies cleared/read per draw, `cmd_cnt` deltas, and `id_dat` (pins the
bitfile and settles the tracer-ABI question). Causality then needs
work-normalized counters, queue state, temporal ordering, or a controlled
intervention. If thermal correlates with slow draws, escalate to the
hardware team with the register evidence.

**Outcome D — smoke barrier fails on TPS (capture too heavy)**: the
fallbacks below are DEVELOPMENT WORK, not staged options — each needs a
config, harness, or source change plus a new smoke:
- new Perfetto template with scheduler+model only (config edit; stage +
  parse-test first);
- kvwait-only arm: the harness has no "no-perfetto" mode — it always
  starts daemons and hard-validates the trace; a `NO_TRACE=1` path must be
  added and tested before this option exists;
- flip at F3 only: NOT a window-only measurement — successive-F3 flips
  measure F3→F3 (whole cycle). A genuine window-only mode (start capture at
  F1, stop/read at F3, off elsewhere) still touches both fences and needs a
  source change, rebuild, and re-verification of gen 7601.

**Cross-cutting, regardless of outcome**: (1) settle the tracer-ABI question
with `id_dat` + a hardware-team ping if act/compute_phase remain absent;
(2) fold the chip-side verdict into the exclusion ledger in
`../intra-pass/CONTEXT.md`; (3) if Outcome A and the earlier ledger hold
together, the standing suspect list reduces to rest-of-cycle host
orchestration + 4-card coordination, and the per-request mining becomes the
critical path.

## 5. Provenance (frozen before launch)

- Binary: `install-fpgause/bin/runtron` sha `4ceaca1a…` (verified). Exact
  source = worktree `~/workspace/tron-fpgause` @ main e8deb5444 + the
  complete probe patch archived at `data/fpgause-probe-patch-4ceaca1a.diff`
  (the binary hash identifies the executable; the patch makes it
  rebuildable). Gen-plugin 7601 hand-edit included in the patch —
  re-verify after any rebuild.
- Harness: `pfgate-3bda/tools/fpgastat-campaign.sh` (per-campaign copy at
  `$ROOT/harness.sh`; sha recorded in `data/fpgastat-armB-manifest.txt`).
- Perfetto template: `~/workspace/common/perfetto.cfg-fpgastat2`
  (35 s, sha in the same manifest).
- Arm A archive: `data/fpgastat-armA.tgz` + checksum manifest (campaign
  `fpgastat-20260817T013917Z`: results.csv, per-draw kvwait-derived CSVs,
  identity, journal).
