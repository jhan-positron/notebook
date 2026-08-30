# P1A pre-registration — router option (c), host-router prototype

Written 2026-08-24, BEFORE any P1a measurement, under jhan's endorsement of the G0
deviation (scope: 20b, spike-first order; explicitly not a P1b/AMX authorization).
Plan: `router/02-option-c-plan.md` sec 4 P1a. Predecessor: `G0-preregistration.md`
(including its deviation record). Deviations from this document must be reported
as deviations.

## Order of work (Sol: spike-first)

- **Phase S — type-feasibility spike.** Hand-edit the GENERATED
  `ingested_gpt_oss_20b.hpp` in the `tron-router-p0` build tree (no emitter
  change, no ingest-owner dependency): make the router gate weight a host fp32
  tensor, compute logits synchronously on the driving thread at the launch site,
  publish through the existing channel/latch contract. Outcome is categorical,
  not a gate: either "compiles + runs + tokens sane" plus the list of
  specializations that were required, or the concrete blocker. A runtime
  `TRON_CPU_ROUTER` env check keeps both paths in one binary (spike-grade switch;
  the production two-control design stays as planned for the emitter change).
  Spike coverage checklist (plan sec 4 P1a; type SELECTION is legitimately
  deferred to the emitter change, everything else must be exercised for real):
  weight visitation/LOADING of the host-typed router weight through the normal
  loader path (real checkpoint weights, not synthetic fills), launcher
  selection, latch/channel behavior under decode, and mixed `is_host`
  assumptions. Contamination guard: the hand-edited header is a spike
  artifact — it carries a loud marker comment block at the top, lives only in
  `tron-router-p0`, and must never serve as a baseline (in particular not for
  the future generator golden test, whose baseline is pristine emitter output).
- **Phase M — integrated same-binary A/B** (only if S succeeds). The integrated
  measurement SUPERSEDES the G0 residual model R.

## CPU-world boundaries (Sol requirement: directly marked, not inferred)

New slices in the spike build: `cpu router compute` (kernel start→end on the
driving thread) and `cpu router publish` (channel finish_writing side).
Existing slices reused: helper first-wait (helper entry), kernel_add_topk_softmax
(top-k execution; its per-task finish_writing_at is the output publish, bounded
by the kernel slice end), `start_reading topk_snd_channel` (worker-0 read
return). Every boundary in Sol's list maps to a direct slice; none is inferred
from gaps.

## Phase M design (pre-registered)

- Configs: decode (1u,2K), (1u,8K), (8u,2K), (8u,8K), ingested-gpt-oss-20b-tp2,
  production attention mode, `-l 256`.
- Arms: `TRON_CPU_ROUTER=off` (FPGA baseline) vs `on` (host router, fp32 host
  weight, best CPU arm from P0b at that M: AVX-512 bf16 at M=1, serialized
  single-thread first — the parallel variant is a separate later increment).
- Run order ABBA per config; ≥3 reps per arm per config; add reps until the
  per-arm CI half-width < 0.3% of mean tok/s or 6 reps reached.
- Primary metric: steady-state decode tok/s (runtron per-request line;
  aggregate = per-user × users). Success (plan G-B): CPU-router arm ≥ +1%
  vs baseline with 95% CI (t-interval on rep means) excluding zero.
- Secondary gates: prefill tok/s regression > 1% fails; kill-switch arm
  (`off`) within noise of a clean-binary baseline run.
- Numerics (spike-level; full pin remains P2): identical prompt, greedy
  decoding — token sequences must match between arms, or the first divergence
  step is recorded and investigated before any tok/s claim.
- Trace attribution (one traced rep per config per arm): stall_topk_read
  (primary estimand), cpu-compute slice, helper entry, per Sol's boundary list.
  Predicted-vs-measured gain reported side by side with the G0 corrected
  estimate.

## Residual/attribution treatment (prospective adoptions from the G0 round)

- Per-layer residual clamping (not per-config means) wherever a residual model
  is still used for attribution commentary.
- Layer records missing `helper_entry_off` (first-wait slice absent in the
  window): excluded from E estimation, included in A sums; count reported per
  config.
- Primary corrected estimand remains `stall_topk_read` alone; adjacent
  logits-read / wait-indices slices are reported but not presumed removable —
  Phase M shows directly whether they disappear.

## Stop conditions for P1a

- Phase S blocker that requires emitter or launcher specialization beyond a
  hand-editable scope: stop, report the scope honestly (the plan's "count it as
  P1a integration work" clause), and return to jhan + ingest owners.
- Phase M: CPU-router arm upper 95% CI < +1% in all four configs, or numerics
  divergence without an identified benign cause: report and stop — the G0
  corrected estimate is then rejected by the integrated measurement, and that
  outcome is written into the record with the same prominence as the estimate.

Machine discipline unchanged: lib-guard flow, lease checks, never-restart policy,
results to `exec/results/router/`, narrative to `exec/QUEUE.md`.

## OUTCOME (2026-08-24, recorded after Phase M completed)

Phase S: all checklist items green (mixed-type compile+run, real-loader host
weight, latch/channel contract, is_host survey). Phase M, avx_bf16 arm, n=6/arm:
1u/2K +0.81% [-0.22, +1.85]; 1u/8K -0.03%; 8u/2K -2.30%; 8u/8K -1.77%
[CI excludes zero]. G-B NOT MET in any config -> the pre-registered stop applies:
the corrected G0 estimate is rejected by the integrated measurement (root cause:
tracing inflated the P0 stall ~2.5x; plus the serialized placement adds the
rmsnorm arrival wait to the driving thread). Numerics: the attempted seeded OFF-vs-OFF control diverged under the command
used. This does not establish that token comparison is instrument-invalid: the
pre-registered greedy/deterministic setup must be checked against the prior
runtron recipe (--temperature 0 -s 42 --pay-for-determinism) and retried on
gpt-oss. Token comparison remains unresolved; if a correctly configured
OFF-vs-OFF control still diverges, the P2 logits/expert-set pin is the
authoritative instrument. (Command audit 2026-08-24: the flags WERE absent -
only --seed 42.) RESOLVED by the flagged retry (r0-p1a-numerics2.sh,
2026-08-24, token-span re-verdict): control CLEAN (instrument valid; gpt-oss
deterministic under the full recipe, MoE ties do not break it); OFF-vs-ON
genuinely diverges at token ~16/34 under deterministic greedy decoding -
recorded per the pre-registered rule; investigation = P2 logits/expert-set
pin with cutoff margins (near-tie flip is the labeled hypothesis).
Deviations of this phase are listed in router/p1a-spike.html sec 5 (placeholder
first arm corrected mid-phase and both generations preserved; extension to all
four configs; compute-slice includes the arrival wait; 8K cells untraced).
Full record: router/p1a-spike.html.
