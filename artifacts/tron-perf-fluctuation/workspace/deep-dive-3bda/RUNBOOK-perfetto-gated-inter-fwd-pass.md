# Runbook: perfetto capture of the inter-fwd-pass window on delphi-3bda

Written 2026-08-12 ~05:45 UTC by the deep-dive session. Audience: a fresh session
executing this runbook. Owner: Jibin (jhan). Work dir for ALL outputs of this
runbook: /home/jhan/workspace/perf-fluctuation/deep-dive-3bda (this folder).
Build host: alpha (claude-box). Test host: delphi-3bda ONLY.

## 0 · Why this exists (context in one paragraph)

The decode-TPS launch lottery is localized: the per-launch loss sits in the
inter-fwd-pass — the once-per-token end-of-step path (layer-35 attention ends →
lm-head matmul → streamed logits consume → token pick → next step's first
dispatch). TSC probes quantified the segments (largest: waiting for + consuming
streamed logits, corr −0.79..−0.88 vs TPS) but they are single-thread stamps.
Perfetto gives named spans on ALL threads — the full picture of who does what
inside the window — and was previously banned only because full-run tracing
perturbs the workload. The fix, decided by the owner: GATE every tron trace
event so only the inter-fwd-pass window during decode is emitted. Tiny volume,
negligible perturbation, full-detail lanes exactly where the mystery lives.
Prior evidence and terminology: deep-dive/status_report/ (report 02 §7–8,
2026-08-12-05-drilldown-step3.html, concurrency map).

## 1 · Instrument tron (build on alpha)

### 1.1 Worktree

    cd /home/jhan/workspace/tron
    git worktree add /home/jhan/workspace/tron-pfgate 12804a812

12804a812 = the revision of every tested binary in this investigation (do not
use current main; line anchors below are for this revision). Enable the qwen
plugin: copy `config/models.local.yaml` from
/home/jhan/workspace/tron-kvprobe/config/models.local.yaml (it is the DUT
overlay with the qwen_3_4b disable-entry already removed).

### 1.2 The gate — one hook, all 167 call sites

tron wraps perfetto in ONE header: `h/common/perfetto.hpp`
(PERFETTO_DEFINE_CATEGORIES_IN_NAMESPACE(tron, …) at ~line 92, with tron's own
TRACE_EVENT macro plumbing above it — read lines 20–92 first). Because every
TRACE_EVENT/TRACE_EVENT_INSTANT in the codebase (167 sites) goes through this
layer, inject the gate THERE, not at call sites:

1. Add a tiny header `h/common/trace_gate.hpp`:

       #pragma once
       #include <atomic>
       namespace tron {
       inline std::atomic<bool> g_trace_gate{false};
       inline bool trace_gate_open() noexcept {
         return g_trace_gate.load(std::memory_order_relaxed);
       }
       }  // namespace tron

2. In `h/common/perfetto.hpp`, route the emission through the gate. The clean
   mechanism with the perfetto SDK is a dynamic category that resolves to a
   never-enabled name when the gate is closed:

       // inside the macro layer, replacing the direct category use:
       ::perfetto::DynamicCategory{ tron::trace_gate_open() ? (category) : "gated_off" }

   Events with category "gated_off" are dropped at the source because the
   session config never enables that category. IMPORTANT: verify against the
   actual macro text in this file — if the existing macros pass compile-time
   category tokens, adapt minimally (a small `#define` indirection at the top
   of the file is acceptable). Whatever the mechanics, the acceptance test in
   §4.1 is what counts: a trace whose slices exist ONLY inside the gate window.
   Budget real time here; this is the one design-sensitive edit.

3. Gate open/close sites (the owner's condition: LAST LAYER && DECODING &&
   POST-ATTENTION):
   - OPEN: end of the layer-35 attention op = right after
     `outer_batch->attn_done_barrier.arrive_and_wait(n_attn_workers)` in
     `run_attention_job`, `h/tron/models/self_attention.hpp` ~line 928 at this
     revision (unpatched tree; ~line 861 region holds the K/V wait). Open only
     when BOTH: `layer.i == 35` (or better: `layer.i + 1 == n_layers` — do not
     hardcode 36 if a constant is in scope) AND decoding:
     `outer_batch->items.size() <= 8` (the decode/parse discriminator used
     throughout this investigation; u1 decode has items.size()==1).
   - CLOSE: entry of the NEXT step's first attention op = top of
     `run_attention_job` when `layer.i == 0` (the `query_channel.start_reading`
     area, same file ~line 882), same items.size()<=8 condition. Also close
     defensively at the latch-reset site (`h/tron/models/model.hpp:1959`) so
     parse phases never leave the gate stuck open.
   - Worker-race note: many attention workers run these lines; setting an
     atomic bool redundantly from several threads is harmless. Do NOT try to
     make it exact-once.

### 1.3 Mike's "data ready" marker

The exact hunk lives in the PDJN worktree's uncommitted diff on the DUT:

    ssh jhan@delphi-3bda 'git -C /scratch/jhan/pdjn-wt diff src/pos/worker.cpp' > pdjn-worker.diff

Port the `TRACE_EVENT_INSTANT("driver", "data ready", "B", workreq->B, "label",
…)` hunk (it sits in the tx_launch path; take the marker hunk only, not the
whole txlat aggregation machinery). It rides the same gated macro layer, so it
is automatically window-filtered like everything else.

### 1.4 Build and deploy

    cd /home/jhan/workspace/tron-pfgate
    PATH=/nix/var/nix/profiles/default/bin:$PATH nix develop -c bash -c \
      "cmake --preset native && ninja -C gen runtron"
    sha256sum gen/runtron   # record; needed by the harness
    ssh jhan@delphi-3bda 'mkdir -p /scratch/jhan/perf-fluctuation/deep-dive/install-pfgate/bin'
    scp gen/runtron jhan@delphi-3bda:/scratch/jhan/perf-fluctuation/deep-dive/install-pfgate/bin/
    ssh jhan@delphi-3bda '/scratch/jhan/perf-fluctuation/deep-dive/install-pfgate/bin/runtron --help | head -2'

(nix store paths for the binary's deps already exist on 3bda — same pinned
flake; verified for the sibling kvprobe builds.)

## 2 · Harness: 20-round perfetto campaign

Reuse the proven perfetto campaign harness — do NOT rebuild capture plumbing:
`/scratch/jhan/pdjn/tools-u1/perfetto-5cat-campaign-v4.sh` (it already handles
tracebox/traced daemons, per-draw config from the shared template, capture,
trace validation, machine restore). The perfetto config comes from
`~/workspace/common/perfetto.cfg-template` (the harness sed-fills the binary
path; RING_BUFFER policy). Copy it to a NEW tools dir
(/scratch/jhan/pdjn/tools-pfgate/) and make EXACTLY these edits:

1. `INSTALL=/scratch/jhan/perf-fluctuation/deep-dive/install-pfgate` and
   `EXPECTED_BIN_SHA=<sha from §1.4>`.
2. The runtron launch line: add `--pay-for-determinism` and
   `--output-token-file $out/tokens.out` to EXTRA_RUNTRON_ARGS (the tools-u1
   copy has the seed and --dont-stop already; it predates the token file).
3. `-m` model: campaign is driven by `MODEL=ingested-qwen-3-4b-instruct-2507-tp4`
   env; keep the script's `-u 1 -i 1 --slice-of 2 --slice-start 0` line as is.
4. Keep USE_HW_ATTN=0 (present), the traffic gate (present), the bitfile check
   (present). ROUNDS=20.
5. validate_trace(): the 5cat validation requires scheduler+model categories
   present — a gated trace still has both (one window per token × ~4096), so no
   change expected; if a category legitimately empties, relax with
   hard_categories=0 rather than deleting validation.
6. Do NOT touch /scratch/jhan/perf-fluctuation/deep-dive/tools/ — that harness
   family is in use by the 3c51 session.
7. DATA LOCATION (owner instruction): all captures go under a NEW folder in
   /scratch/jhan/perf-fluctuation/ — create it first:
       ssh jhan@delphi-3bda 'mkdir -p /scratch/jhan/perf-fluctuation/pfgate-3bda'
   and set CAMPAIGN_ROOT=/scratch/jhan/perf-fluctuation/pfgate-3bda/<name>-<UTC ts>
   for every campaign (smoke included). Nothing from this runbook writes into
   deep-dive/ or pdjn/ campaign roots.

## 3 · Schedule (owner's instruction)

- Start: 2026-08-12 05:00 PDT = 12:00 UTC, i.e. AFTER tonight's nightly CI.
- Preconditions, in order, non-negotiable:
  1. Clock past 12:00 UTC (nightly usually done ~11:30 UTC; later on bad
     nights).
  2. Traffic gate passes: `bash /scratch/jhan/pdjn/gate_count.sh` — 6 samples
     over 60 s, proceed only if <3 samples show non-self :80 connections. The
     harness re-checks this itself; run it manually first anyway.
  3. `systemctl is-active actions.runner.positron-ai.delphi-3bda-0.service`
     inactive, no runtron/rinzler-stopping surprises (harness preflights this).
- Also check `uname -r` on 3bda: it was on 6.8.0-124 one-shot; if the nightly
  or anyone rebooted, it will be 6.8.0-136 — record whichever it is; the
  lottery reproduces on both, but note it with the results.
- The machine must be restored (serving trio) by the harness after the
  campaign; verify RESTORED and `curl -s localhost/v1/models` shows 3 ids.

## 4 · Smoke acceptance, then the campaign

### 4.1 Smoke acceptance (one draw, before the 20 rounds)

The harness runs a smoke draw first. On it, verify ALL of:
- "HW attention disabled" banner present (harness gates this).
- tokens.out sha256 == 66af1d58… (the qwen-tp4 sequence; every binary built at
  12804a812 has reproduced it bit-for-bit, including on delphi-3c51).
- Decode TPS within the known bare band (~170–190). If it is >2% below the
  bare campaign means (176–184), the gate is not filtering enough — stop and
  fix before burning 20 rounds.
- THE GATE TEST: open the smoke trace with trace_processor
  (/usr/local/bin/trace_processor on 3bda):
      SELECT count(*) FROM slice;                      -- expect ~4096 windows × (a few dozen spans) ≈ 1e5–1e6, NOT 1e7+
      SELECT min(ts), max(ts) FROM slice;              -- spans the benchmark
  Then spot-check: pick one window (slices between consecutive gaps in ts) and
  confirm it contains fill_logits_buffer / notify_listener / "data ready" and
  NOTHING from mid-layer attention (no run_sections-adjacent spans from layers
  0–34). Trace file size sanity: single-digit MB, not hundreds.
- Confirm Mike's marker: `SELECT count(*) FROM slice WHERE name = 'data ready'`
  (instants land in slice or in the instant table depending on TP version —
  check both).

### 4.2 Campaign

20 rounds. Expect ~2 min/draw ≈ 45 min. Record results.csv TPS; the campaign
population should roll (3bda reference: CV 1.3–1.9%, gap 5–8%).

## 5 · Analysis: fastest vs slowest draw

1. Pick best/worst by generate_tok_s from results.csv.
2. For each, with trace_processor against the draw's trace.pftrace:
   - Reconstruct per-window lanes: every slice with its track/thread, ts, dur,
     inside each inter-fwd-pass window; plus "data ready" instants.
   - Aggregate per window: total window duration; per-span-name total/mean;
     count of windows (expect ≈ 4096; a shortfall means the gate misses steps).
   - Distribution: median vs p90 per span name (the TSC probes showed heavy
     tails — most windows fast, a fraction stalled; check whether specific
     SPANS carry the tail or dead space between spans does).
3. Cross-validate against the kvprobe7 segments (deep-dive/status_report/
   2026-08-12-05-drilldown-step3.html): A1 ≈ barrier→listener spans, B ≈
   fill_logits_buffer span (+ preceding stream wait), C.rest ≈ post-callback
   scheduling spans. Report agreements AND disagreements — the perfetto view
   covers all threads, so new dead-space between spans is the interesting part.
4. Key question this capture can answer that TSC stamps could not: in slow
   windows, WHERE does the wall time between the wcls dispatch and "data ready"
   / fill completion sit — in a named span on some thread (which?), or in
   unattributed gaps (pointing below the host again)?

## 6 · Deliverable: HTML with a measured lane diagram

Write to THIS folder (deep-dive-3bda/), name with "3bda", e.g.
`2026-08-12-07-3bda-pfgate-step0.html`. Requirements (owner's standing rules):

- LIGHT background, single-theme.
- A wall-clock lanes diagram of ONE representative fast window and ONE slow
  window, side by side or stacked: one lane per thread that appears (coordinator,
  pool workers that ran logits jobs, TX, RX per card as applicable), X = time
  TO SCALE (µs; TSC 2.7 GHz), solid blocks = named spans, dashed = gaps/idle,
  "data ready" instants as markers, the critical path / biggest slow-window
  delta highlighted in red with its cost annotated on the figure. Tiny spans
  drawn tiny. Caption any simplification.
- Tables: per-span fast4/slow4 aggregate with corr vs TPS (define corr on the
  page: Pearson correlation of per-draw span totals vs decode TPS across the
  20 draws; −1 = longer exactly when slower).
- Two-level attribution reconciled against the TPS-derived total, with
  residuals ("inter-fwd-pass" naming; "share of level 1"; see
  drilldown-step3.html for the exact table shape).
- Plain English throughout; no invented shorthand; every number traceable to a
  draw (command+environment+bitfile captured by the harness per draw).
- End the page with: measured answers to §5.4, and the next collection targets
  laid out as yellow boxes (the drill-down convention).

## 7 · Pitfalls (learned this week — do not rediscover)

- Never edit a harness script a running campaign executes (bash reads
  incrementally; a mid-run sync corrupted a campaign once). Per-campaign copy.
- perfetto daemons: the 5cat harness starts/stops tracebox traced +
  traced_probes and refuses if sockets pre-exist — if a previous run died, run
  its stop_daemons cleanup (pkill tracebox, rm /tmp/perfetto-*) before retrying.
- The sw-attention banner lands 15–55 ms AFTER the load-complete log line
  (harness polls; keep it).
- All perf/ptrace collectors need sudo on 3bda (perf_event_paranoid=4) — not
  relevant to perfetto, listed so you don't add a broken perf sidecar.
- The gate must not change numerics: tokens.out hash is the proof. If the hash
  differs from 66af1d58…, something in the build differs — stop.
- Trace volume: if a draw's trace balloons (>100 MB), the gate leaks (likely
  the CLOSE site misses; check the defensive close at the latch reset).
- Draw failures "no log directory" are a transient sweeps-log race; 19/20 is
  usable.

## 8 · Coordination

- delphi-3c51 (Bill's machine) is running the TSC-probe replication under a
  separate session — different host, different campaign roots, shared /scratch
  READ-ONLY overlap. Do not modify deep-dive/tools/*; use tools-pfgate/.
- Status/memory: the project memory (deepdive-project-state.md in the
  deep-dive project's memory dir) holds the current verdict state; append your
  results there under a 3bda-pfgate entry when done.
- If the nightly overran or the machine looks wrong (kernel changed, bitfile
  changed — the harness records it per draw), note it in the report; bitfile
  reference so far: Release Code 01.05.08.00 / 06-16-2026.
