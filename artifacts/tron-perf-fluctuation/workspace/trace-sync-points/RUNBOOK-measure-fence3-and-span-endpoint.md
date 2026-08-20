# Runbook: measure Fence 3 and the span end point

Written 2026-08-13 by the deep-dive session. Audience: the session that will
build the probe and run the campaign. Owner: Jibin (jhan).

## 0 · Goal in one paragraph

The inter-fwd-pass span currently has NO timestamp at its **definitive sync
point** (project term: an instant every operation on every thread is
definitively before or after — nothing concurrent with it). That point is
**Fence 3**: the scheduler's `listeners_notified.wait()` returning. Today the
TSC segment C.rest lumps together everything from the token-callback return to
the span end point (next pass's layer-0 Q-wait), so we cannot split:

- **[callback-end → Fence 3]** — listener count-downs + the scheduler's futex
  wake latency at the definitive sync point (an unmeasured suspect of the same
  class as the codex F4 doorbell finding), from
- **[Fence 3 → end point]** — the scheduler's single-threaded next-step
  construction (`extend_request`, `compute_forward_args`,
  `construct_minibatches`, attention plan, layer-0 enqueue), which is known to
  stretch with the lottery (C.rest 421k→526k cycles fast4→slow4, corr −0.69).

This runbook adds ONE probe stamp (tag 7600) at Fence 3 and defines the
analysis that produces the split, per token.

## 1 · Tag check (do not skip)

Tag **7600 is unassigned** in the current kvwait tag map:
0xx = P1 Q-wait · 1xxx = K/V latch · 2xxx = barrier · 3xxx = tx dispatch ·
4xxx = rx completion · 7000 fill · 7100 alloc wait · 7200 prepare ·
7300 dead · 7400 callback · 7500+(block_ix&255) per-block consume ·
7900+dev HBM audit.

One caveat: the 7500+ per-block family can reach 7500+117 = **7617 at tp1**
(118 blocks in a single tile). At tp2 (max ≈7558) and tp4 (max ≈7530) there is
no overlap. All campaigns in this series are tp4, so 7600 is safe; if anyone
ever runs the probe at tp1, the analyzer must exclude 7600 records whose
`dur == 0` (per-block stamps are instants; the Fence-3 stamp always has a
nonzero wait duration) or move the stamp to 7800.

## 2 · The code change (one site, ~6 lines)

Worktree: `/home/jhan/workspace/tron-kvprobe` @ `12804a812` on alpha (already
contains all v1–v9 probes). File: `h/tron/models/model.hpp`. Find the
scheduler-side wait (grep-verified at lines 3082–3083, directly after the
per-chunk loop that contains the `waiting_for_logits` TRACE_EVENT):

```cpp
      // This is the main thread waiting for all of the callbacks to be done.
      listeners_notified.wait();
```

Replace with:

```cpp
      // This is the main thread waiting for all of the callbacks to be done.
      if (kvwait_probe::state().enabled) {
        const uint64_t f3_t0 = kvwait_probe::state_t::now();
        listeners_notified.wait();
        kvwait_probe::state().add(f3_t0,
            kvwait_probe::state_t::now() - f3_t0, 7600);  // site 7600: Fence 3
      } else {
        listeners_notified.wait();
      }
```

Record semantics: `t0 + dur` of a 7600 record = **Fence 3, scheduler side**
(the definitive sync point's timestamp). `t0` = when the scheduler began
waiting for listener acknowledgements (i.e., just after the logits_done wait).
This runs on the `24/?-work_queue` thread; the existing probe is lock-free and
multi-thread safe, nothing else is needed. **Nothing else changes** — the span
end point is already stamped (P1 layer-0, tag 0) and the callback end is
tag 7400.

## 2b · RECOMMENDED second stamp: Fence 1 (tag 7601) — a FULL definitive sync point near the span start (corrected 2026-08-13)

CORRECTION (2026-08-13, source-verified in run_forward): `launch_wcls` runs
strictly AFTER `plugin_state.run()` returns, and run() joins all pool workers
internally — so at the Fence-1 instant the hardware pipeline is EMPTY (layer
35's W_O/MLP results already consumed by the helpers; wcls not yet launched;
listener tasks not yet enqueued). Under the same convention that qualifies
Fence 3 (idle/poll loops and &#181;s-scale trailing rx cleanup exempted),
**Fence 1 is a FULL definitive sync point**, not merely scoped. The token
cycle therefore has TWO definitive sync points: F1 and F3. The irreducible
no-definitive-point gap is exactly [F1 → F3] — the streaming region, where
card delivery and host consumption are concurrent by design. Stamping BOTH
7601 (F1) and 7600 (F3) brackets the entire varying region between two
definitive sync points; treat 7601 as recommended, not optional. F1 lands
tens of &#181;s after the span start, inside A1&#8242;.

If taken: bracket the scheduler-side join wait in the generated plugin&#8217;s
`run()` (the `workers_done` wait; codex cites generated
`qwen_3_4b_instruct_2507.hpp:1742-1754` and `:6690-6692` — pin the exact wait
call by grep before patching, same bracket pattern, tag **7601**; 7601 has the
same tp1-only 7500-family caveat as 7600). Payoff: per-token measurement of
the pool join tail [open &#8594; F1] — codex finding F1&#8217;s &#8220;P-wide join
convoy&#8221; — plus a complete scheduler-thread skeleton per token:
F1 &#8594; waiting_for_logits &#8594; F2 &#8594; F3 &#8594; construction &#8594; dispatch.
This stamp is optional; the primary deliverable remains the 7600 split. If
skipped, note it in the report as an open follow-up.

## 3 · Build (alpha)

Follow the recipe in `/home/jhan/workspace/perf-fluctuation/deep-dive/status_report/handoff-2-Bill-delphi.precheck.md`
(nix build in the worktree). Install name: `install-kvprobe10`. Record the
runtron sha256. Share the nix store path to delphi-3c51 as with v7–v9
(`/scratch/jhan/perf-fluctuation/deep-dive/install-kvprobe10`).

## 4 · Campaign (delphi-3c51 — no CI window on this host)

Standard harness pattern (per-campaign copy, never edit a running script):

```sh
D=/scratch/jhan/perf-fluctuation/deep-dive
SHA=$(sha256sum $D/install-kvprobe10/bin/runtron | cut -d' ' -f1)
ROOT=$D/3c51-fence3-tp4-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p $ROOT
cp $D/tools/deepdive-campaign-3c51.sh $ROOT/harness.sh
setsid env MODEL=ingested-qwen-3-4b-instruct-2507-tp4 SLICE_OF=2 ROUNDS=16 \
  CAPTURE=none KVWAIT=1 \
  INSTALL=$D/install-kvprobe10 EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
  bash $ROOT/harness.sh > /tmp/3c51-fence3.stdout 2>&1 < /dev/null &
```

Gates (standing rules):
- Smoke draw first (harness does it): token sha must equal the qwen-tp4
  reference `66af1d58…93c4` — the stamp must not perturb numerics.
- 7600 record count per draw ≈ one per forward pass (~4104 including prefill
  chunks; decode-only filtering is positional, same as all other tags).
- "HW attention disabled" banner gate, bitfile check, restore verification —
  all built into the harness.
- Machine-state caveat: 3c51 tron cores currently run CLOS3-capped at
  2700 MHz (see tron issue #3751). Do NOT change it; within-campaign
  comparisons are unaffected.
- Hygiene: apply the freeze filter (holes > 50 ms between consecutive kvwait
  records, after dropping the v9-style preamble records with t0 <= 1e12 if
  present) and report polluted draws separately.
- Do not run heavy analysis (trace_processor etc.) on the DUT while the
  campaign runs.

## 5 · Analysis (per draw, then fast4/slow4 + corr)

Per token (bracket by consecutive tag-0 layer-0 records, positional decode
filter as in boundary_v7.py):

| segment | definition |
|---|---|
| F3.wait | 7600.dur (scheduler waiting for listener acks; starts at fence-2 return) |
| cb→F3 | 7600.end − 7400.end (listener count-downs + scheduler wake at the definitive sync point) |
| F3→end | next layer-0 tag-0 `t0` − 7600.end (single-threaded next-step construction = clean phase 2) |

Sanity: cb→F3 + F3→end ≈ old C.rest (reconcile with residual, per the
two-level-attribution rule). Then:

- fast4 vs slow4 means and Pearson corr vs decode TPS for each new segment
  (define corr wherever used).
- Bonus, free from the same data: consecutive 7600 record ends give the
  **Fence-3-to-Fence-3 per-token period**. IMPORTANT: this is NOT the
  inter-fwd-pass span — it is one complete token cycle (it decomposes as:
  phase 2 of window i + forward pass i+1 + phase 1 of window i+1). Its role is
  the per-token TOTAL/denominator: because Fence 3 is the token cycle's only
  definitive sync point, this period is exactly measured per token, replacing
  the campaign-mean-derived "whole step = 1e6/TPS" row in level-1 attribution
  and enabling token-by-token reconciliation (window growth vs period growth)
  and exact freeze detection. The inter-fwd-pass window remains the suspect
  region under investigation.
- The question this answers: **does the C.rest stretch live in the wake at the
  definitive sync point, or in the next-step construction?** Either answer is
  a real narrowing: wake-side → scheduler wake latency joins the codex-F4
  class as a live suspect; construction-side → the single-threaded segment
  (tree_lock work, args/minibatch build) is the target.

## 6 · Reporting

- New status-report HTML in `/home/jhan/workspace/perf-fluctuation/deep-dive/status_report/` (light background, terminology:
  "inter-fwd-pass", "definitive sync point", "share of level 1", corr defined;
  regenerate-from-scratch policy; no invented shorthand).
- Update `/home/jhan/workspace/perf-fluctuation/deep-dive/status_report/2026-08-12-07-stall-map.html` §3.5: replace "approximated by the
  tag-7400 end" with the measured Fence-3 numbers.
- Update project memory (`~/.claude/projects/-home-jhan-workspace-perf-fluctuation-deep-dive/memory/deepdive-project-state.md`).

## 7 · Context pointers

- Fence chain + diagram: `/home/jhan/workspace/perf-fluctuation/deep-dive/status_report/2026-08-12-07-stall-map.html` §3.5.
- End point definition + three cuts: step-5 appendix
  (`/home/jhan/workspace/perf-fluctuation/deep-dive/status_report/2026-08-12-06-3c51-step5.html`), P1 entry.
- Codex synchronization inventory (S4/S10/S14, F1–F9):
  `/home/jhan/workspace/perf-fluctuation/deep-dive/from-codex/decode-sync-source-review.md`.
- All prior probe patches for style: `h/tron/models/model.hpp` sites 7000/7100/7400.
