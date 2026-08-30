# Review of `RUNBOOK-fpgastat-armB.md`

Reviewed 2026-08-17 against the staged harness, binary, Perfetto template,
`rtl-register-audit.md`, `../intra-pass/CONTEXT.md`, the existing fence
analyzers, and the probe implementation in `tron-fpgause`.

## Verdict

The experiment asks a useful question and the principal assets are staged, but
the runbook is **not ready for an unattended 16-draw run as written**. The main
blockers are:

1. one counter window is mislabeled as the intra-pass span;
2. the harness does not enforce the runbook's smoke-TPS, record-liveness,
   numerics, or 16/16 gates;
3. the tag-8xxx analyzer and its token-pairing rules are not staged; and
4. the implementation's flip boundaries are offset from the recorded fences
   and staggered across devices.

Those issues do not defeat the core inside-versus-outside-[F1→F3] comparison,
but they can produce an incorrect "intra-pass" conclusion or allow an invalid
campaign to run to completion.

## Blocking findings

### 1. `[F3→next F1]` is not the intra-pass span

Runbook lines 40–47 label the `+40..+46` window `[F3→next F1] intra-pass
span`, and lines 111 and 123–130 use it as the span-side comparator. The
project's canonical definitions in `../intra-pass/CONTEXT.md` lines 20–26 say:

- intra-pass span = layer-0 tag 0 through layer-35 tag-2035 end;
- inter-pass window = `[open→F1→F3→end]`.

Therefore:

```text
F3_i → F1_(i+1)
  = F3_i → end_i
  + exact layer-0→35 span_(i+1)
  + open_(i+1) → F1_(i+1)
```

The `+40` records are the complementary **rest-of-cycle** window, not a pure
intra-pass measurement. Rename it throughout and revise Outcome A to conclude
"busy in [F1→F3], mostly idle outside it." The current two-flip design cannot
attribute the rest-of-cycle counters specifically to layers 0–35. Doing that
would require additional boundaries or a carefully justified subtraction.
Likewise, call `+20` the `[F1→F3] logits/streaming segment`, not the complete
inter-pass window, which also contains `[open→F1]` and `[F3→end]`.

The runbook must also state the ownership convention: a `+20` group closed at
`F3_i` belongs to `[F1_i→F3_i]`, whereas a `+40` group closed at `F1_i`
started at `F3_(i-1)`. Without that rule, a nearest-fence join can shift the
rest-of-cycle values by one token.

### 2. The detached harness does not enforce the stated gates

Runbook lines 96–103 require a production-speed smoke, 16/16 success, and
tag-8xxx liveness. The staged harness does none of those before proceeding:

- `fpgastat-campaign.sh` lines 752–768 runs the smoke and immediately enters
  all 16 draws; it never compares smoke TPS with 150 or 165;
- the range `150 <= TPS < 165` is not assigned a pass/fail decision in the
  runbook;
- the harness records `successful-count.txt` but does not fail when
  `successful != scheduled`;
- it does not count or validate tag-8xxx groups;
- it writes `tokens.out` but does not compare the token hash with the known
  qwen-tp4 reference; and
- its hard trace validation checks only the `scheduler` slice category, not
  model fences or FPGA tracer counters.

Because the launch is detached, an operator may discover a slow smoke only
after campaign draws have already begun. This is not hypothetical: arm A's
journal records `smoke OK generate=90.135`, `STATUS campaign`, and
`draw_01 begin` at the same second, after which the harness ran all 16 draws.
Make smoke validation an automatic barrier in the harness, or split the
documented launch into a smoke-only run
followed by a separately authorized 16-draw run. The barrier should check, at
minimum, token hash, an unambiguous TPS threshold, complete tag groups and
counter invariants, F1/F3 presence, and tracer liveness. The final harness exit
must be nonzero unless all scheduled draws succeeded and restoration passed.

### 3. The analysis is a specification, not a runnable staged workflow

Runbook line 4 says everything is staged, but lines 105–119 refer only to a
"scripts pattern in scratchpad + tools/". The durable tools directory contains
`/scratch/jhan/perf-fluctuation/deep-dive/tools/fence3_dump.py` for CPU fence
segments, but no analyzer for the new `+20/+40` tag families and no command
sequence that produces the requested CSVs or report inputs.

Before spending the 16 draws, stage an analyzer that explicitly:

1. parses the count-prefixed `(t0,dur,tag)` format and rejects truncation;
2. derives expected record counts from observed F1/F3 groups rather than the
   approximate hard-coded `4096 * 2 * 7 * 4`;
3. requires seven fields for every device/window and reports duplicates;
4. drops only the first invalid `+40` group per device (the code records that
   group; it is invalid rather than necessarily absent);
5. documents the cross-token `+40` association described above;
6. applies the standing preamble, positional-decode, and freeze-pollution
   filters;
7. checks nonzero/non-saturated timers, ratios in range, and the HBM/MM clock
   identity per device;
8. emits absolute counter cycles as well as ratios, and defines whether group
   summaries are ratios of sums or means of per-token ratios;
9. restricts only Perfetto/tracer joins to trace-covered tokens while retaining
   the full valid kvwait population for the primary counter distributions; and
10. writes the durable CSVs and a machine-readable validation summary.

This is also where fast4/slow4 eligibility, slow-token/fast-token quantiles,
correlation definition, and missing-data policy should be fixed in advance.
Keep per-device results and report each token's cross-device min/max/spread;
pooled-only summaries can hide the four-card straggler under investigation.

### 4. The implementation is fence-adjacent, not exactly fence-aligned

Runbook lines 38–42 and 107–108 describe exact fence windows and say `t0` is
the flip instant. The implementation is less exact:

- tag 7601 and the `"fence 1"` instant are emitted inside the generated
  plugin before `plugin_state.run()` returns (`model.hpp` lines 1787–1798 and
  generated plugin lines 6690–6702);
- `model.hpp` then executes `wait_for_coop_gof()` and enqueues listener jobs
  before `run_logits()` calls `fpga_use_fence_flip(1)`;
- tag 7600 and the `"fence 3"` instant are emitted before
  `fpga_use_fence_flip(3)` (`model.hpp` lines 3100–3113); and
- `metrics.cpp` takes one common TSC before a loop that performs
  stop/read/start serially for devices 0–3. That TSC is neither every device's
  actual stop nor its restart instant (`metrics.cpp` lines 169–193).

Thus every device has a differently shifted window, with an excluded MMIO gap
at each transition. The likely bias may be small enough for the coarse
inside/outside question, but it is on the same tens-of-microseconds scale that
the runbook intends to account for.

Correct the wording and analyze the MM-timer residual separately by device.
Make the dimensional comparison executable: fence/flip TSC deltas use the
validated 2.700 GHz TSC, while MM and HBM timers use 550.0 and 368.75 MHz.
Compare both consecutive shared flip-`t0` deltas and the recorded
`7601.end→7600.end` interval; they test different boundary errors.
For exact claims, record per-device stop/start TSCs or restructure the probe so
the boundary error is explicitly bounded. In particular, do not present the
shared tag `t0` as an exact per-device flip instant.

### 5. "Busy" and "idle" do not yet have a valid decision rule

Lines 107–111 define FPGA busy as `mm_in_prog/mm_timer`, while Outcomes A and
B use qualitative terms such as "high fraction," "mostly idle," and "also
idle." This is insufficient for a reproducible verdict:

- `mm_in_prog` counts productive matmul cycles, not cycles stalled with an
  activation in flight;
- `mm_bp` and its approximate RMEM/WMEM split must be considered before a
  low `mm_in_prog` value can be called idle;
- the MM counters do not cover every FPGA engine;
- HBM observes pseudo-channel 0 only; and
- a whole-window average cannot by itself prove that the host and chip were
  idle **simultaneously**.

Define thresholds or an expected per-token work budget before seeing the
results. Compare absolute productive/stall/read cycles first, then normalized
shares. Report productive and total-stall shares separately; if their source
semantics confirm they are disjoint, `(mm_in_prog + mm_bp) / mm_timer` is a
useful active-demand approximation, not a whole-chip utilization metric.
Outcome B should initially say that the observed matmul/HBM indicators
are low; the stronger transport conclusion requires time-aligned tracer
evidence and exclusion of listener/scheduler-side work. This also prevents a
longer host-paced denominator from making identical FPGA work look like an
FPGA-side slowdown.

Outcome B should retain **host issuance** as an alternative to transport. Arm A
found the activation queue empty, while fence mode records only fields 0–6 and
does not snapshot `cb_stat.aq_empty` or the upper `rmem_ctrl` FIFO. Use first
tag-3000 dispatch timing and the existing 3000→4000/7500 stamps before narrowing
the result to DMA/mailbox/doorbell plumbing.

### 6. The tracer's `rmem_bp` name conflicts with the audited RTL ABI

The runbook treats `rmem_bp` as one of the trusted core tracer signals (lines
53–58). In `tron-fpgause/src/pos/metrics.cpp`, bit 23 is copied directly into a
counter named `rmem_bp`. The local RTL audit, however, identifies bit 23 as
`rmem_rdy_legacy`, where 1 means **room is available**, not backpressure
(`rtl-register-audit.md` lines 50–59).

The deployed bitfile may have an older ABI, which makes the meaning uncertain
rather than proving a simple inversion. Move `id_dat`/bitfile-specific ABI
verification from "when convenient" to a pre-analysis requirement, and do not
interpret this track as backpressure until it is settled. `rmem_depth` and
`inprog_pause` can still be used with their documented caveats. In particular,
tracer `rmem_depth` is the lower 4K FIFO, not the upper 1K FIFO that actually
drives backpressure.

There is a second liveness problem: these are change-only `TRACE_COUNTER`
events. A missing track can mean "constant zero/one," "trace began after the
last transition," or "instrument absent." Requesting the `driver` category is
not proof of capture. Add an initial sample or heartbeat, or define a smoke
query that proves usable per-device tracer state without treating absence as
zero.

## Important corrections

### 7. Outcome C overstates causality

Lines 145–152 call any slow-draw chip-side delta a "genuine FPGA-side
contribution." A correlation can instead be a response to host command pacing,
a ratio-denominator effect, or unequal work. Call it a chip-side association
unless absolute work-normalized counters, queue state, temporal ordering, or a
controlled intervention support causality. In particular, lower HBM duty with
equal read cycles is evidence of extra idle time, not an HBM cause.

### 8. The proposed overhead comparison is not a matched control

Lines 63–65 and 158–160 propose comparison with the wadefix-on campaign. That
campaign differs in binary/capture context, and F1→F3 includes the F1-side flip
but ends before the F3-side flip. It cannot isolate total two-flip cost cleanly.

Use the same binary, model, Perfetto config, harness, and host state with
both `FPGA_USE_FENCE=0` and `FPGA_USE_POLL_MS=0` for one or more matched
control draws. Otherwise disabling fence mode activates the harness's default
1 s poller. Report F1→F3 cost, rest-of-cycle cost, full F3→F3 cost, and
per-device timer residual separately.

### 9. Outcome D is not a runnable or technically correct fallback

Lines 154–160 promise scheduler+model, kvwait-only, and F3-only fallbacks, but
the staged harness always starts Perfetto and requires a valid trace. It has no
kvwait-only mode. The fence implementation also has no mode that flips only at
F3, so that option requires a source change and a new binary.

More importantly, resetting/reading only at successive F3 instants measures
`F3→F3`, a whole token cycle, not `[F1→F3]`. A genuine lower-overhead
window-only implementation would start capture at F1, stop/read at F3, and
leave capture off outside that window. It still touches both fences and must be
staged and validated. Label all three branches as future development until the
corresponding config/harness/binary exists.

### 10. Trace coverage and hygiene need explicit handling

The Perfetto template lasts 25 s. Generating 4096 tokens takes about 24.8 s at
165 tok/s and 27.3 s at 150 tok/s, while capture begins after the start signal
and setup delay. Full-draw trace coverage is therefore not guaranteed,
especially for slow draws. Record first/last covered fences and restrict all
trace/kvwait joins to their overlap. Continue using the full valid kvwait
population for the primary fence-counter analysis.

The tracer tracks are change-only step functions, not guaranteed regular 10 us
samples; the hardware may also drop mailbox samples. Carry the last known value
into each analyzed window, do not equate missing events with zero, and define
how kvwait TSC is mapped to Perfetto time. An ordinal F1/F3 join or an affine
clock mapping should include a residual/coverage check.

The analysis section also omits the standing freeze rule (holes over 50 ms),
the `t0 <= 1e12` preamble drop, and positional prefill/decode filtering used by
the existing fence tools. Without these, freeze-polluted draws can enter the
slow4 set and dominate the result.

### 11. Operational prerequisites are not durable or fully accurate

- "After 11:30 UTC" should be the explicit safe daily interval outside the
  02:30–11:30 UTC CI window; otherwise 01:00 the next day also satisfies the
  wording. The staged harness checks whether the runner is active but has no
  clock-window refusal, despite `CONTEXT.md` saying it does.
- Session/task/peer identifiers in lines 76–79 are ephemeral. Give concrete
  state-file/process/root checks and an owner/contact fallback.
- The harness still starts turbostat and a multi-event IOMMU `perf stat`,
  clears/reads MSRs, and runs a legacy report generator. These activities are
  not listed in the runbook's instrument set. Either document and justify them
  or remove them from this production-speed arm.
- Line 103 suggests inspecting `runtron-environment.txt`, but the harness's
  capture filter omits `TRON_KVWAIT_FILE` and both `TRON_FPGA_USE_*` variables.
  Record the effective values in both per-draw identity and campaign metadata.
- The runbook gives no safe stop procedure for the detached harness even
  though Outcome D requires stopping immediately after smoke.
- The launch writes only a fixed `/tmp/3bda-fpgastat-armB.stdout`, saves no
  remote harness PID, and relies on a hidden default for `INSTALL`. Put stdout
  and the PID under `$ROOT`, pass `INSTALL` explicitly, and document a TERM
  path that allows the restore trap to complete.
- The per-root `flock` cannot serialize two differently named campaign roots;
  use a shared host/campaign lock to close the preflight race.
- Campaign provenance currently says `USERS=4` even though the harness launches
  checkerboard with `-u 1`. Correct that metadata before it is copied into a
  report.

### 12. Tighten record and counter validation

The liveness expression on lines 101–103 is useful as a rough order-of-magnitude
check, not a completeness gate. The corresponding arm A workload recorded
4,105 F1 and F3 calls per draw (4,096 generation calls plus preamble), so the
likely raw arm B total is about `4105 * 2 * 7 * 4 = 229,880`, not 229,376.
The invalid first `+40` set is still present in that raw count. Use the actual
observed number of fence closures, account for prefill passes, and require
equal per-field counts. Also check:

- `0 <= hbm_read_cycles <= hbm_timer`;
- nonzero MM/HBM timers for every retained group;
- no timer at the 32-bit saturation ceiling;
- `hbm_timer/368.75e6` versus `mm_timer/550e6` per device/window;
- `mm_in_prog` and total-backpressure bounds; and
- the documented fact that RMEM/WMEM approximate split values can slightly
  exceed total backpressure.

For each device and field, `+20` raw count should equal the observed tag-7600
count and `+40` raw count should equal tag-7601 count before the initial `+40`
analysis drop; any mismatch should fail the draw.

When estimating aggregate HBM throughput, multiply a per-channel byte rate by
32 only with the symmetry assumption; never multiply the pchan-0 duty
percentage itself by 32.

Finally, lines 21–30 should call concentration the hypothesis under test rather
than the only way to reconcile arm A with the CPU waits. Regime perturbation,
limited counter coverage, and instrumentation/ABI error are already-recognized
alternatives.

### 13. Companion inputs and provenance are not yet durable or consistent

The requested combined Arm A/Arm B report depends on material that is not
archived under this repository's `data/`: Arm A currently lives as a raw
scratch campaign plus prose in `CONTEXT.md`. Preserve its campaign identity,
results table, derived per-draw counters, analysis code, trust annotations, and
a raw-file checksum manifest before relying on it. Reconcile Arm A's aggregate
ratios with Arm B using exposure-weighted sums, not an unweighted mean of token
ratios.

The companion `CONTEXT.md` is internally stale: lines 263–266 describe the new
fence/config-2 arm, while lines 268–274 immediately revert to the old 1 s
poller, `perfetto.cfg-fpgastat`, and `driver-detail` plan. Mark the latter as
Arm A history or replace it so the runbook's context pointer cannot route an
executor to the wrong experiment.

Finally, the exact source is not reconstructible from `main e8deb5444 + kvwait
probes + fpga_use fence-flip`. The `tron-fpgause` worktree currently contains
staged, unstaged, and untracked probe changes. The binary hash is sufficient to
identify this executable but not to rebuild it. Preserve a commit or complete
patch and record hashes for the copied harness and Perfetto template. Replace
the report-name ellipsis and "artifact per convention" with exact report,
archive, manifest, and analyzer paths.

## What was verified

- The staged `install-fpgause/bin/runtron` SHA-256 exactly matches
  `4ceaca1a36e16d983a3c4a508d1ffd97ee0ceec53146e8bd4cff11a54777c662`.
- The staged harness passes `bash -n`.
- The launch's `FPGA_USE_FENCE=1` and `FPGA_USE_POLL_MS=0` are correctly mapped
  by the harness to `TRON_FPGA_USE_FENCE` and `TRON_FPGA_USE_POLL_MS`; the
  periodic poller is suppressed in fence mode.
- `perfetto.cfg-fpgastat2` requests scheduler, driver, and model categories plus
  100 ms cpufreq sampling.
- The seven field numbers and 550.0/368.75 MHz clocks in the runbook agree with
  the implementation and RTL audit.
- The counter windows are far below the documented saturation durations.

## Minimum revision before launch

1. Rename `+40` to rest-of-cycle and correct every span/outcome claim.
2. Add an automatic smoke barrier and a final 16/16 failure condition.
3. Stage and smoke-test the tag-8xxx analyzer with explicit token ownership and
   hygiene rules.
4. Correct or bound fence/device alignment and stop calling the shared `t0` an
   exact flip instant.
5. Pre-register a busy/idle decision table using absolute counters, stalls,
   ratios, and tracer evidence.
6. Resolve the tracer ABI or quarantine the ambiguous `rmem_bp` track.
7. Add a matched fence-off control for perturbation accounting.
8. Either stage the Outcome D modes or clearly mark them as unimplemented
   development work.
9. Archive Arm A and freeze the exact Arm B source/config/harness/analyzer
   provenance before raw scratch state can disappear.

After those changes, the campaign should answer the narrower and defensible
question: **is matmul/HBM activity concentrated in [F1→F3] versus the rest of
the token cycle, and does that concentration differ between fast and slow
draws/tokens?**
