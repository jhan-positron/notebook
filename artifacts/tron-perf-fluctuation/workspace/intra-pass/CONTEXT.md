# intra-pass: project context

Written 2026-08-14 by the trace-sync-points session (owner: Jibin, jhan@positron.ai).
Audience: agents working in this project. Read this before proposing plans.

## 1. Goal in one paragraph

Localize and explain the per-token jitter inside the **intra-pass span** — layers
0–35 of a decode token's computation on TRON (Positron FPGA inference). Two prior
projects (deep-dive, trace-sync-points) localized where jitter *shows up*; a bypass
experiment on 2026-08-14 proved the previously-suspected inter-pass window is an
*expression* of a run-wide condition, not the source, and relocated the open
question here: the intra-pass span carries 57–79% of within-run per-token variance
and, once the window is pinned, the cross-draw draw-speed differences as well. The
span is FPGA layer matmuls + software attention + per-layer host kernels + driver
work, interleaved — **not yet separated**. Separating them is this project's job.

## 2. Terminology (use these words exactly; no metaphors, no new shorthand)

| Term | Definition |
|---|---|
| token cycle | One generated token's full period, measured F3→F3 (equivalently F1→F1 or open→open; they agree to three digits). ~5.9 ms at ~170 tok/s on qwen-3-4b tp4. |
| intra-pass span | Layers 0–35: from the layer-0 Q-wait entry (kvwait tag 0) to the layer-35 attention-barrier end (tag 2035 end). ~4.99 ms mean. THIS PROJECT'S SUBJECT. (Older pages call it "forward pass" or "forward segment" — same thing.) |
| inter-pass window (or span) | [open → F1 → F3 → end]: transfer phase + logits stage + construction, one contiguous span between two consecutive intra-pass spans. ~0.9 ms mean. |
| Fence 1 (F1) | All pool workers joined after layer 35 (`workers_done.wait()` end, tag 7601). A definitive sync point. |
| Fence 3 (F3) | Logits delivered to all listeners (`listeners_notified.wait()` end, tag 7600). The token cycle's other definitive sync point. |
| definitive sync point | An instant every operation on every thread is definitively before or after. |
| draw / campaign | One benchmark run (4096 generated tokens); a campaign = smoke + 16 draws on one host/config. |
| fast4 / slow4 | The 4 highest-TPS / 4 lowest-TPS clean draws of a campaign. |
| wcls | The classifier-head matmul producing logits (vocab 151,936, 4 device tiles at tp4). |
| within-run jitter vs cross-draw difference | Two distinct pools of variation; see section 4. Never conflate them. |

Convention: always write "intra-pass" and "inter-pass" in full — they are easy to
misread for each other.

## 3. How we got here (evidence chain, all claims cite campaigns)

1. **Weeks of window investigation** (deep-dive 08-11..12, trace-sync-points 08-13):
   the inter-pass window carried 64–75% of the fast4→slow4 cross-draw difference at
   only ~15.5% of the runtime (report 01 Level-1: 74.7% campaign 1, 64.4% campaign 2),
   with corr(window, TPS) ≈ −0.85 replicated by three independent methods. That was
   correct measurement — of the cross-draw dimension.
2. **The wcls bypass experiment** (2026-08-14, delphi-3c51, campaigns
   `3c51-wclsbyp-ctl-tp4-20260814T045710Z` and `3c51-wclsbyp-on-tp4-20260814T051813Z`,
   both smoke+16/16): the driver was modified (env `TRON_WCLS_BYPASS_NS`) to stop
   waiting for real FPGA logits — constant 2.5 ms hold, zeroed buffers, background
   drain. Result: token-cycle within-run spread stayed at 99% of control
   (p90−p10 1559→1538 µs); overall sd fell only 4.5% (640→612 µs); the pinned logits
   stage decorrelated from TPS (−0.86 → −0.06) while the intra-pass span (−0.86) and
   transfer phase (−0.81) now carry the cross-draw variation. Verdict: the wcls
   production-to-consumption pipeline is an expression, not the source.
3. **The two-pools reconciliation** (same data): within-run token noise
   (~404k µs² variance) is ~65× larger than the between-run persistent-offset pool
   (~6.2k µs²). The intra-pass span dominates the big pool (57–79% of variance in
   every campaign, pre- and post-bypass); the window dominated the small pool until
   the bypass severed its data dependency — after which the small pool did not
   shrink much either (fast4→slow4 total −17%), it re-expressed in the intra-pass
   span (+67 → +108 µs/token). A run-wide per-launch condition is acting on
   whichever stages are data-dependent.

Full record with charts, tables, and the pre-run scoping:
`../trace-sync-points/status_report/2026-08-13-03-wcls-bypass.html`
(artifact https://claude.ai/code/artifact/88d53503-f6d7-406a-995c-105c9c5af6c4).

## 4. What is known about the intra-pass span (the starting facts)

Numbers from control 08-14 (3c51) and fence13 08-13 (3c51), 65.5k tokens/arm,
cycles→µs at 2.700 GHz; extraction via `fence3_dump.py`:

| metric | fence13 08-13 | control 08-14 |
|---|---|---|
| runtime mean | 4,956.9 µs (84.3% of cycle) | 4,988.4 µs (84.5%) |
| within-run sd | 524.1 µs | 529.3 µs |
| within-run CV | 10.6% | 10.6% |
| p99 / p50 | 1.22× | 1.21× |
| max / p50 | 2.1× | 2.3× |
| share of within-run token variance | 57.2% | 68.3% |
| share of fast4→slow4 difference | 35.9% (pre-bypass) | 33.9% (pre-bypass); 65.6% under bypass |

Structural facts:

- Span boundaries in probe data: tag-0 instant (layer-0 Q-wait entry) → tag-2035 end
  (layer-35 attention barrier). The bracketing/hygiene recipe (positional decode
  filter, preamble drop, 50 ms freeze filter) is implemented in
  `fence3_dump.py` / `fence3_split.py`.
- Composition (not yet separated): per layer — FPGA legacy matmuls (QKV, W_O, MLP;
  hardware attention is DISABLED in all campaigns, `USE_HW_ATTN=0`), software
  attention and host kernels (rmsnorm/rope/swishmul) on pool workers, TX/RX driver
  work per device, KV-cache writes.
- The span's jitter is broad, not tail-only: CV 10.6% with p99 only 1.22× the median
  — contrast the window (CV 38–44%, p99 = 2.6–3.1× median). Small relative wobble on
  a long base = the largest absolute jitter contributor.
- Known discrete events that land in or straddle the span: (a) a deterministic
  once-per-run >5 ms window event at a fixed position (all 16 draws of the traced
  fence13pf campaign, exactly 2,715 windows before capture end; also present
  untraced — cause unknown, labeled hypothesis: periodic host/system event);
  (b) whole-system stalls hitting all 4 devices at the same token (32 of 262k drains
  in the bypass arm, 1–6 ms).
- **Unmined data that may answer the first question without any new run**: kvwait
  tags 3000+dev (tx dispatch instant) and 4000+dev (rx completion instant) stamp
  EVERY matmul in every existing kvwait campaign. Per-request chip turnaround vs
  host inter-request gaps across the span is computable from existing
  `kvwait.bin` files. Nobody has done this yet.

## 5. Wade's wcmd-deferral A/B (executed 2026-08-14 evening, delphi-3bda)

Wade Miller's PR #3785 (merged 17:58 UTC) defers wcls weight commands until launch
admission — a correctness fix for an FPGA W-Mem corruption defect that also removes
wcls WCMD traffic from the device command FIFO during the FINAL LAYERS of the
intra-pass span. Single-variable A/B, one binary (`install-wadefix` = main
e8deb5444 + kvwait probes), same host, back-to-back: `3bda-wadefix-on-tp4-
20260814T195201Z` (deferral ON, default) vs `3bda-wadefix-off-tp4-20260814T201252Z`
(`TRON_DEFER_WCLS_WCMD_UNTIL_LAUNCH=0`), smoke+16/16 each, token shas identical in
both arms AND identical to the old-main reference (`66af1d58…`) — no numerics
change. Dumps archived at `../trace-sync-points/data/wadefix-dumps.tgz`.
Full report with charts: `../trace-sync-points/status_report/2026-08-14-01-wadefix-ab.html`
(artifact https://claude.ai/code/artifact/6c9c10da-6527-4df5-b993-288ae85ab8bc).

Results (freeze-clean draws, 14 per arm; polluted draws excluded per the standing
freeze-filter rule — see below):

| metric | deferral ON | deferral OFF |
|---|---|---|
| TPS CV across draws | 1.32% | 2.11% |
| fast4→slow4 difference | 171.0 µs/token | 280.9 µs/token |
| …carried by window / span | +151 / +22 | +209 / +72 |
| window within-run sd | 410.4 µs | 447.5 µs (−8.3% with fix) |
| intra-pass span within-run sd | 461.8 µs | 454.4 µs (unchanged) |
| token-cycle within-run sd | 619.1 µs | 647.6 µs |

Reading (direction consistent across three views; n=14 draws/arm, so magnitudes
are indicative): Wade's fix reduces the cross-draw spread ~35–40% and window
within-run jitter ~8%, and leaves intra-pass-span jitter unchanged. The window
level-shift mode (draw-mean window ~700–1000 µs vs ~550 baseline) still occurs in
BOTH arms — reduced, not eliminated. Separately, the OFF arm had two draws with
CLUSTERED whole-system freezes (10 and 14 holes of ~170–210 ms each, hiding
+382/+708 µs/token from the segment view), vs two single-freeze draws in the ON
arm — suggestive of an old-ordering pathology but unattributable at n=16; treat as
an open question. 3bda/new-main baseline note for this project: window variance
share is higher here (44–48%) and span share lower (49–56%) than the 3c51/old-main
campaigns (29% / 68%) — the two-pool structure holds, the split shifts with
host+base; never mix hosts in one comparison.

## 5b. Frequency/power excluded as the fluctuation cause (2026-08-15)

Campaign `lowfreq-20260815T122602Z` (3bda, install-wadefix, 16/16, perfetto
linux.sys_stats cpufreq 100 ms + scheduler-only track_event, turbostat, RAPL,
throttle MSRs around every draw; draw lottery expressed strongly: TPS
176.4–189.4, CV 1.92%): **CPU frequency lowering is excluded.** Zero throttle
reasons (0x64F = 0 everywhere; sticky thermal/power-limit log bits clear);
busy frequency flat 3737–3770 MHz across draws (0.9% spread vs 7.1% TPS
spread) and stable within draws (≤33 MHz); correlations run OPPOSITE
(corr(TPS, busy MHz) = −0.84, corr(TPS, pkg-0 W) = −0.87 — slow draws burn
more power at higher clocks, a consequence of extra spin-wait time). Report:
`../trace-sync-points/status_report/2026-08-15-01-lowered_freq.html` (artifact f861edf4). Same-day
same-host context from the ingested-llama8b project: llama-8b tp4 CV 1.44%
(fluctuates) / tp2 CV 0.67% (tight) — the tp4 fluctuation reproduces across
models. Ops: rdmsr/wrmsr are NOT installed on 3bda — use /dev/cpu/N/msr; and
two campaigns launched within the ~60 s preflight window kill each other
(guard: no runtron process AND no campaign root younger than 3 min before
launching).

## 5c. Cross-model screens: the fluctuation is tp4-specific, not model- or ingestion-specific (2026-08-15, ingested-llama8b project)

Screens on the same host (3bda), 20 draws each, stock binaries, data in
`../ingested-llama8b/data/`:

| model / build | tp4 | tp2 |
|---|---|---|
| qwen-3-4b ingested (reference) | CV 1.3–1.9% rolls | (tp2 tight per 08-11 screens) |
| llama-3.1-8b ingested | CV 1.44% rolls | CV 0.67% tight |
| mixtral-8x7b hand-authored | **CV 2.43% rolls (hardest)** | — |
| mixtral-8x7b ingested | CV 1.11% rolls | CV 0.14% extremely tight |

The ingestion confound is broken (a hand-authored model rolls, and harder than
its ingested sibling). Combined with 5 (wcls pipeline ruled out) and 5b
(frequency/power excluded), the cause space narrows to **something specific to
4-card operation**: candidates are the [open→F1] transfer phase (cross-draw
corr −0.81 under bypass), 4-device interleaving inside the intra-pass span
(per-layer driver work, device queue coordination), and 4-card join behavior.
Campaigns: 3bda-mixtral-tp4-20260815T152808Z,
3bda-ingmixtral-tp4-20260815T155824Z, 3bda-ingmixtral-tp2-20260815T163100Z.

## 5d. Host DRAM bandwidth ceiling excluded (2026-08-16)

Campaign `3bda-drambw-tp4-20260816T195258Z` (16/16, install-wadefix, KVWAIT=1)
with an in-campaign ceiling calibration (28x membw saturating both sockets;
achievable ~220 GB/s reads per socket ground truth; IMC counters under-scale
x2.01 — DDR5 sub-channel CAS — so all ratios are IMC/IMC, scale-free) and
per-second per-socket `uncore_imc/cas_count_read,write` through every draw:
**decode uses 11.5–14.4% of the DRAM ceiling at the mean, 28–30% at the
busiest single second of any draw; corr(TPS, bandwidth) = +0.57 and
corr(TPS, peak util) = +0.74 — fast draws move MORE data.** Demand-limited,
not supply-limited: the DRAM-throughput-constraint hypothesis is disproved.
Report: `../trace-sync-points/status_report/2026-08-16-01-dram-ceiling.html` (artifact f687c32a);
data `../trace-sync-points/data/drambw.tgz`; harness
`deep-dive/tools/deepdive-campaign-drambw.sh` (reusable: per-draw IMC capture
+ ceiling calibration). NOT excluded by this test: memory-LATENCY effects
(NUMA-remote cost, per-channel imbalance) and FPGA-side HBM behavior.
FPGA-side HBM measurement is SCOPED (report 03 section 3b): the chip counts
hbm_read_cycles/hbm_timer (HBM read duty) and mm_wmem_bp_cycles (matmul
stalled on weight memory) with a ready driver API
(fpga_use_metrics_start/stop/readout, driver.cpp:1881-1903) that NOTHING
currently calls — a kvwait-style env-gated 1 s-window poller patch enables
it (32-bit counters wrap in ~10-17 s; whole-draw windows impossible).
Existing directional evidence against HBM-bandwidth causation: tp2 doubles
per-card weight bytes/token yet is tight on every model.

## 5e. FPGA observability plan (owner-approved 2026-08-17; instruments built, campaign queued)

Goal: poll FPGA status so fast vs slow draws can be compared on what the chip
was doing (the bypass showed long CPU-side waits; this measures the card side
of them). THREE instruments, first two require no RTL changes:

1. **FPGA tracer -> perfetto (10 us chip status; ZERO code change).** The chip
   already DMA-pushes a 32-bit status word into a host mailbox every 10 us
   (tracer_period=10, pos/config.hpp:63; chip-side pacing in 2.5 ns units,
   device.cpp:289-299). A stock reader thread (`fpga_state_tracer`,
   metrics.cpp) decodes it into perfetto TRACE_COUNTERs under the
   `driver-detail` category: rmem_depth, rmem_bp, inprog_pause, wmem_loaded,
   activation_pending/inprog, fetcher16/0 read_done, mm_results_accum. It is
   OFF unless runtron gets `--tracer-core <core>` (system.cpp:1616; default
   -1). Enable = add the flag + capture driver-detail. Field decode reference:
   Notion page "Tracer" (linked in metrics.cpp:decode_tracer).
2. **fpga_use windowed counters (HBM duty + weight-stall; small poller patch,
   IMPLEMENTED 2026-08-17).** Worktree tron-fpgause (main e8deb5444 + kvprobe
   patch + poller): env `TRON_FPGA_USE_POLL_MS` spawns one poller thread per
   device (pinned to platform core 5) doing start->window->stop->readout of
   the chip metrics FSM, recording all 7 counters as kvwait records with tags
   `8000 + dev*100 + field` (field 0..6 = hbm_timer, hbm_read_cycles,
   mm_timer, mm_bp, mm_in_prog, mm_rmem_bp, mm_wmem_bp). Key metrics:
   hbm_read_cycles/hbm_timer = HBM read duty; mm_wmem_bp/mm_timer =
   weight-fetch stall share. 32-bit counters -> 1 s windows (wrap ~10-17 s).
3. **RTL register audit: DONE (2026-08-17), full findings in
   `../trace-sync-points/rtl-register-audit.md`.** Load-bearing facts: mm counters tick at
   550 MHz, hbm at 368.75 MHz, 32-bit SATURATING (windows <= ~5 s);
   `hbm_metrics` observes pseudo-channel 0 ONLY (x32 extrapolation is an
   assumption; card fabric ceiling 755 GB/s payload, 23.6 GB/s per pchan);
   the tracer word carries compute_phase[29:28] (idle/matmul/attn-K/attn-V)
   which tron's decoder dropped (added in tron-fpgause, emitted as a
   perfetto counter); tracer rmem_depth is the LOWER 4K FIFO while
   backpressure is decided on the UPPER 1K FIFO (read `rmem_ctrl` 0x700400);
   `cb_stat` 0x700280 aq_empty is the cleanest "FPGA slow vs host not
   feeding it" discriminator (both now stamped per poller window, kvwait
   tags base+7/base+8); top unmeasured PHYSICAL suspect = HBM stack
   temperature / refresh band (BAR4, per stack) — campaign #2 candidate
   along with activ_mgr_dbg_2 stall-reason stickies, cmd_cnt deltas, and
   wim/rim host-traffic counters.

ARM A RESULT (fpgastat-20260817T013917Z, 16/16; caveat: TPS halved to
87-92 — regime perturbed, internally consistent. Root cause found
2026-08-17 from arm B's first smoke: `--tracer-core 5` collided with the
TX-38 driver thread pinned to core 5 (trace shows both "5/0-TX-38" and
"5/0-Tracer"); NOT driver-detail span volume as first assumed — fence13pf
captured every category at 177 TPS without the tracer. Fixed:
TRACER_CORE=16):
the FPGA is nearly idle and host-starved. HBM read duty 6.5-6.9% (pchan 0;
~13% at production speed — matches the paper demand math), matmul engine
busy 1.4% of cycles, stalls ~1.1% of cycles (virtually all weight-fetch;
result-path backpressure ZERO; upper FIFO ~empty), and the activation
command queue was EMPTY at essentially every snapshot (aq_empty = 1.000)
— the chip waits on the host, not the reverse. All counters correlate with
TPS in the demand-following direction (+0.96). Tracer counter gaps found:
the core trio (rmem_depth/rmem_bp/inprog_pause) is emitted under the
"driver" category (arm A captured driver-detail instead), and
act_inprog/act_pending/compute_phase never appeared — suspected tracer-ABI
mismatch with the deployed bitfile (01.05.08.00 of 2026-06-16 vs RTL HEAD);
verify via id_dat in campaign #2. ARM B queued at production speed — full why/what/how, launch recipe, gates,
and the outcome-based decision tree live in **`../trace-sync-points/RUNBOOK-fpgastat-armB.md`**
(fence-flip per-token chip counters; config perfetto.cfg-fpgastat2 =
scheduler + driver + model + cpufreq; binary sha 4ceaca1a…).

ARM A HISTORY (superseded — do not execute): arm A ran with the 1 s poller
(`TRON_FPGA_USE_POLL_MS=1000`) and config `perfetto.cfg-fpgastat`
(scheduler + driver-detail + cpufreq); that capture halved TPS and missed
the core tracer counters — its results are the paragraph above. The ACTIVE
plan is arm B per the runbook (fence-flip per-token mode, config
`perfetto.cfg-fpgastat2` at 35 s, harness with automatic smoke barrier +
3 matched control draws, staged analyzer
`../trace-sync-points/tools/fpgastat_fence_dump.py`), revised 2026-08-17
per the Codex review at
`../trace-sync-points/from-codex/RUNBOOK-fpgastat-armB-review.md`. Key
review corrections that also apply when reading arm B data: the +40 window
is REST-OF-CYCLE (not the intra-pass span), the flips are fence-adjacent
(shared TSC, serial per-device stagger — use timer residuals), and the
tracer `rmem_bp` track is quarantined pending the bitfile-ABI check
(`id_dat`): RTL HEAD says bit 23 is `rmem_rdy_legacy` (1 = room), the
opposite polarity of the name tron uses.

ARM B EXECUTED 2026-08-17 11:44-12:11 UTC (fpgastat-armB-20260817T114401Z,
16 fence draws + 3 matched controls, 19/19 ok, restored). VERDICT: **FPGA
chip work is exactly constant per token** — window [F1→F3]: 47,520 HBM read
cycles (128.9 us) + 11,880 matmul cycles (21.6 us); rest-of-cycle: 253,440 +
63,360; single-valued across all 65,504 token x device samples, all 16 draws
(TPS 157.4-171.8, CV 2.43%); weight-fetch stall varies only ±0.8 us
(uncorrelated), result-path backpressure zero. Slow-decile tokens carry
identical chip work to fast-decile. Only WALL time varies: rest-of-cycle
wall corr(TPS) = -0.98. FPGA compute + HBM EXCLUDED as fluctuation source.
Window job = fixed lm-head weight stream (~97 MB/dev est., matches fp8
lm-head slice to 0.2%), chip ~80% idle even in window -> CPU window waits
are host-side delivery/expression (consistent with bypass). Arm A closes
numerically (13.5% exposure-weighted duty vs arm A's ~13%). Flip capture
cost 4.1% (controls 172.5 vs fence 165.5). First launch aborted by the new
smoke barrier at 80.3 TPS: tracer-core-5 collision with TX-38 (fixed:
TRACER_CORE=16). Report 04:
`../trace-sync-points/status_report/2026-08-17-01-fpgastat.html` (artifact
03347dd8); data `../trace-sync-points/data/fpgastat-armB.tgz`; analyzer
`../trace-sync-points/tools/fpgastat_fence_dump.py`.

EXCLUSION LEDGER as of 2026-08-17: wcls production-to-consumption pipeline
(08-14 bypass) · CPU frequency/power/throttling (08-15 lowered_freq) ·
ingestion path (08-15 Mixtral A/B) · host DRAM bandwidth ceiling (08-16;
BURST-RESOLVED 08-19: decode 10 ms windows peak 28-30% of ceiling, RPQ
queue residency flat fast-vs-slow, one non-decode end-of-run burst noted) ·
FPGA chip compute + FPGA HBM (08-17 fpgastat arm B: per-token work exactly
constant across draws; BURST-RESOLVED 08-19 at 278 us windows: duty p99
identical 45.9% every draw, max 55%, no multi-window bursts — report 06
`../trace-sync-points/status_report/DDR_HBM_peak_throughput.html`).
Also 08-19: id_dat register read pins bitfile 01.05.08.00/2026-06-16 —
tracer-ABI question settled (ABI lag, not instrumentation bugs); CPU
mem-bound share is higher in slow draws (25.9->30.2%, corr -0.78) but
confounded with waiting — the placement/wakeup campaign should break the
tie with per-core breakdown.
MINING EXECUTED 2026-08-17 (report 05, no machine time,
`../trace-sync-points/status_report/2026-08-17-02-window-waits.html`,
artifact e341f5b8): the draw-level fluctuation is localized to HOST
THREAD-HANDOFF WAITS in the inter-pass window, moving together as a
PER-DRAW LEVEL SHIFT. Fast4→slow4 budget of the +360 us/token period
delta: [open→F1] +112 (31%, contains workers_done join wait +70,
corr -0.79) · [F1→listeners-notified] +159 (44%; fill_logits_buffer
+147 — entirely the wcls block-ARRIVAL tail 489→897 us while
post-arrival processing is constant ~30 us; listeners_notified wait
+110) · [notify→end] +23 (7%) · span +65 (18%, = host inter-dispatch
gap growth). Chip turnaround (3000→4000 ordinal) median 20 us with
slow-fast delta +0.0 us. The three waits do NOT co-move per token
(corr <= 0.14) -> a per-bring-up state slows every scheduler-thread
handoff by a near-constant amount ("window level-shift mode" now has a
mechanism). Token-noise pool separately confirmed: 77% of within-draw
period variance is the span.
Standing suspects (all host-side, per-draw state): thread placement
drift of unpinned worker/RX/listener threads · futex/cv wakeup path
cost (cpuidle depth, IPI, sibling load) · NUMA placement of run
allocations.
Next step (cheap, next campaign): per-draw `ps -T -o tid,psr,comm`
snapshot + numa_maps in the harness, and one campaign with perfetto
linux.ftrace sched_wakeup/sched_switch to measure wakeup-to-run latency
of scheduler/RX/listener threads fast vs slow draws.

## 6. Tooling and data inventory

- **Probe infrastructure**: `kvwait_probe.hpp` (env `TRON_KVWAIT_FILE`, lock-free
  (t0,dur,tag) records, TSC cycles). Tag map: 0xx layer-0 Q-wait · 1xxx KV latch ·
  2xxx attention barrier (2035 = layer 35) · 3000+dev tx dispatch · 4000+dev rx
  completion · 7000 fill · 7100 alloc wait · 7200 prepare · 7400 callback ·
  7500+block per-block consume · 7600 Fence 3 · 7601 Fence 1 · 7700+dev bypass hold ·
  7900+dev HBM audit. Free band for new stamps: 7800+ (mind the 7500-family reach at
  tp1; all campaigns are tp4).
- **Analyzers** (durable at `/scratch/jhan/perf-fluctuation/deep-dive/tools/`):
  `fence3_dump.py` (per-token segments), `fence3_split.py` (per-draw split),
  `wcls7700.py`, `ab_verdict.py`, `fence_windows.py` (perfetto traces),
  campaign harnesses `deepdive-campaign.sh` (3bda) / variants with env passthrough.
- **Worktrees on alpha** (build host, claude-box): `~/workspace/tron-kvprobe`
  (12804a812 + probes, built), `~/workspace/tron-wclsbypass` (+ bypass, built),
  `~/workspace/tron-wadefix` (main e8deb5444 + probes, built),
  `~/workspace/tron-wclsbypass-pr` (clean bypass PR branch).
- **Binaries on /scratch** (shared filer, readable from alpha and 3bda):
  `install-kvprobe10` (old main + probes), `install-wclsbypass`, `install-wadefix`.
- **Data archives**: `../trace-sync-points/data/` (wclsbypass-ab-verdict.json,
  wclsbypass-dumps.tgz, fencepf-windows.tgz); raw campaigns under
  `/scratch/jhan/perf-fluctuation/deep-dive/<campaign>/results/draw_NN/kvwait.bin`.
- **Reports**: `../trace-sync-points/status_report/2026-08-13-0{1,2,3}-*.html`,
  `../deep-dive/status_report/*.html`, `../deep-dive-3bda/*.html`.
- **Draft PR** #3788 (bypass code, for Mike/Wade validity review) — now needs a
  rebase over Wade's #3785 (same tx_launch region).

## 7. Operational rules (owner directives; do not violate)

1. **Machines**: delphi-3bda ONLY for tests (Bill's 3c51 is off-limits as of
   2026-08-14). 3bda nightly CI window 02:30–11:30 UTC: light-load work only —
   the harness refuses to start campaigns inside it.
2. Build on alpha (claude-box) with
   `nix develop -c bash -c "cmake --preset native && ninja -C gen runtron"`.
   Gotchas: copy `config/models.local.yaml` from an existing worktree (gitignored;
   excludes gated-HF models, build fails without it); after every build re-apply and
   verify the tag-7601 hand-edit in the GENERATED
   `gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp` (grep for 7601); new
   main's RUNPATH is $ORIGIN-relative, so install dirs need `lib/` with
   `libversion.so` + `libfuse3.so.4` staged next to `bin/runtron`.
3. Never rebuild a worktree while a campaign that resolves libraries from it might
   run (NFS). One campaign at a time per host; per-campaign harness COPY, never edit
   a running script; monitor via NFS tail from alpha, and never run remote helper
   commands whose cmdline contains benchmark keywords (e.g. "runtron") while a draw
   may start.
4. One ssh session with a remote loop instead of repeated one-shot ssh (the shell
   profile spawns an ssh-agent per login; orphans accumulate).
5. Anything a durable artifact depends on (scripts, extracted CSVs) lives in the
   workspace or /scratch — never only in a /tmp scratchpad (they get wiped).
6. Statistics: cycles→µs at 2.700 GHz TSC (validated); state population-vs-sample
   sd; variance is immune to constant offsets, CV is not (rescale to a common mean
   when arms differ by a designed constant); the fast4→slow4 decomposition and the
   within-run variance decomposition answer different questions — report which one
   you are using.
7. Reporting style: exact source terms or plain English; label estimates "est.";
   every claim cites its campaign/draw; light-background HTML reports with charts.

## 8. Candidate directions (for the planning discussion — not commitments)

Ordered by evidence-per-effort as of today:

1. **Mine existing 3000/4000 stamps** (zero machine time): per-matmul chip
   turnaround vs host inter-request gaps across the span, per layer position, per
   device; correlate with slow tokens and slow draws. Splits "FPGA compute jitter"
   from "host orchestration jitter" observationally.
2. **Ingest tonight's wadefix A/B**: does deferring wcls WCMDs out of the final
   layers change span jitter? (If yes: command-FIFO interference inside the span is
   real and steerable.)
3. **Per-layer bracketing**: new stamps in the 7800+ band at layer boundaries
   (pattern proven by the 7600/7601 work) — locates which layers carry the
   within-run wobble and whether it is uniform (frequency/thermal-like) or
   structured (specific layers/resources).
4. **Bypass-style intervention inside the span** (heavier; scoping exists in report
   03 section on "bypass all matmuls"): only after 1–3 say where to cut.
5. **The run-wide condition** (the per-launch draw lottery) is still unexplained:
   arm A/B designs that decouple elapsed time from token count (idle-pause or rate
   intervention) remain unbuilt; the deterministic once-per-run event is a separate
   thread worth one dedicated look (correlate its fixed position against system
   logs).
