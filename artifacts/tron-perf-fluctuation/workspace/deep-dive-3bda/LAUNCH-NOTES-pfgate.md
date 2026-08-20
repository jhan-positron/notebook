# pfgate campaign — 12:00 UTC launch sequence (prepared 06:50 UTC)

Everything below runs only after the Monitor fires at 2026-08-12 12:00 UTC.
Binary sha256: 0200e8181bd081678900b9d1ee0666231e51e8e4cbdb13a32308a7decc6b9148
tokens.out reference: 66af1d583183f4b09a47a253e4eb909235b8cfdd19da9bf2c631720934f193c4

## 1. Preconditions (§3), in order

    ssh jhan@delphi-3bda 'date -u; uname -r; systemctl is-active actions.runner.positron-ai.delphi-3bda-0.service'
    # kernel was 6.8.0-124-generic at 06:01 UTC; record if changed (reboot -> -136)
    ssh jhan@delphi-3bda 'sha256sum /scratch/jhan/perf-fluctuation/deep-dive/install-pfgate/bin/runtron'   # NFS identity check
    ssh jhan@delphi-3bda '/scratch/jhan/perf-fluctuation/deep-dive/install-pfgate/bin/runtron --help | head -2'
    ssh jhan@delphi-3bda 'touch /scratch/jhan/perf-fluctuation/pfgate-3bda/.write-test && rm /scratch/jhan/perf-fluctuation/pfgate-3bda/.write-test && echo WRITABLE'
    ssh jhan@delphi-3bda 'bash /scratch/jhan/pdjn/gate_count.sh'   # x6 manually over 60 s, <3 nonzero
    # leftover perfetto daemons check (pitfall §7):
    ssh jhan@delphi-3bda 'pgrep -f tracebox; ls -la /tmp/perfetto-* 2>/dev/null; echo done'

## 2. Launch (per-campaign copy, background on DUT)

    TS=$(date -u +%Y%m%dT%H%M%SZ)
    ROOT=/scratch/jhan/perf-fluctuation/pfgate-3bda/pfgate-tp4-$TS
    ssh jhan@delphi-3bda "mkdir -p $ROOT && cp /scratch/jhan/pdjn/tools-pfgate/perfetto-5cat-campaign-v4.sh /scratch/jhan/pdjn/tools-pfgate/perfetto-5cat-report-v3.py $ROOT/ && cd $ROOT && MODEL=ingested-qwen-3-4b-instruct-2507-tp4 CAMPAIGN_ROOT=$ROOT ROUNDS=20 setsid nohup bash $ROOT/perfetto-5cat-campaign-v4.sh > $ROOT/launch.log 2>&1 < /dev/null & echo LAUNCHED"

Monitor from alpha over NFS (no DUT load): tail $ROOT/journal.log, status.txt,
results.csv. Smoke trace: $ROOT/smoke/trace.pftrace.

## 3. Smoke acceptance (§4.1) — from alpha via NFS

- grep "HW attention" $ROOT/smoke/runtron.log (harness gates the banner itself)
- sha256sum $ROOT/smoke/tokens.out == 66af1d58…93c4 (STOP if different — §7 pitfall)
- smoke generate_tok_s in 170–190; STOP if >2% below 176 (i.e. <172.5)
- trace file size: single-digit MB (>100 MB = gate leak, check CLOSE sites)
- gate test with /scratch/jhan/tools/trace_processor on alpha:
    slice count 1e5–1e6; min/max ts spans benchmark;
    windows contain fill_logits_buffer/notify_listener/"data ready";
    n_rope_spans ~1 per window (36x = leak); no mid-layer Save K/V floods
- "data ready" present (check slice dur=0 and legacy instant table)
- analysis/pfgate_windows.py smoke trace: n_windows ≈ 4096 (25 s capture may
  clip decode tail on slow draws — up to ~10% shortfall is capture clipping,
  not gate failure; distinguish via trace_span_s ≈ 25 vs << 25)

## 4. Campaign watch

- ~2 min/draw, 20 draws ≈ 45 min. results.csv grows one line per draw.
- 19/20 usable is OK ("no log directory" transient race, §7).
- After ALL_DRAWS_SCHEDULED + RESTORED: curl check is inside harness restore;
  verify $ROOT/RESTORED exists and status.txt == restored.
- Record: uname -r, bitfile line (results/*/bitfile.txt; reference
  Release Code 01.05.08.00 / 06-16-2026).

## 5. Analysis (§5) — on alpha

- pfgate_windows.py per draw (out under deep-dive-3bda/analysis/out/<draw>);
  fastest/slowest by generate_tok_s; fast4/slow4 aggregate; Pearson corr of
  per-draw span totals vs TPS (20 draws); cross-validate vs kvprobe7 table
  (A1 497k→680k −0.61 / A2 30k→42k / B 925k→1238k −0.79 / C.cb 43k→70k /
  C.rest 422k→526k −0.69 cyc; 1M cyc ≈ 370 µs at TSC 2.7 GHz).
- §5.4 key question: slow-window time between wcls dispatch and "data ready"/
  fill completion — in named spans (which thread?) or unattributed gaps?

## 6. Deliverable (§6)

2026-08-12-07-3bda-pfgate-step0.html in deep-dive-3bda/. Light single theme;
wall-clock lanes fast vs slow window (per-thread lanes, µs to scale, dashed
idle, red critical path annotated); per-span fast4/slow4 + corr table (define
corr on page); two-level attribution reconciled vs TPS-derived total with
residuals ("inter-fwd-pass", "share of level 1"); yellow next-target boxes;
plain English, no invented shorthand; every number traceable to a draw.
Then append 3bda-pfgate entry to deepdive-project-state.md (deep-dive project
memory) per §8.
