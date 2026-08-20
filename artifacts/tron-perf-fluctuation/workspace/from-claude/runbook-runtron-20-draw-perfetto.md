# Runbook: 20-draw runtron Perfetto campaign on delphi-3bda

Repeats the 2026-08-06 campaign (`/scratch/jhan/tron-perfetto-5cat-20260806T2145Z`, 20/20 OK, ~65 min total).

# machine

delphi-3bda, as user `jhan` (needs passwordless sudo).

# binary

`/scratch/jhan/tron-perfetto-vanilla-install-20260806/bin/runtron`

SHA-256: `6f5cb54f6cd22536d7ce7a9fdb0c7573d95e3a9ad5784384f68dcf3af26d6fbb`
(the harness verifies this hash in preflight and refuses to run on mismatch)

# harness

`/scratch/jhan/tron-perfetto-5cat-tools-v3-20260806/perfetto-5cat-campaign-v3.sh`

One unattended script that does everything: preflight, machine mutation
(stops CI runner + rinzler, clears hugepages, ISST pinning), Perfetto
daemons, per-draw turbostat capture, 1 smoke draw + 20 real draws,
fast/slow analysis, HTML report, and machine restore. Report generator
sits next to it (`perfetto-5cat-report-v3.py`).

The per-draw Perfetto config is generated at launch from
`/home/jhan/workspace/common/perfetto.cfg-template` — edit the template,
not the harness, to change the capture.

# run

```bash
ssh jhan@delphi-3bda
export MODEL=ingested-gpt-oss-120b-tp4
export CAMPAIGN_ROOT=/scratch/jhan/perf-fluctuation/tron-perfetto-5cat-$(date -u +%Y%m%dT%H%MZ)
mkdir -p "$CAMPAIGN_ROOT"

HARNESS=/scratch/jhan/tron-perfetto-5cat-tools-v3-20260806/perfetto-5cat-campaign-v3.sh

# optional dry run (no machine mutation):
PREFLIGHT_ONLY=1 "$HARNESS"

nohup "$HARNESS" > "$CAMPAIGN_ROOT/campaign.stdout" 2>&1 &
```

If `CAMPAIGN_ROOT` is not set, the harness defaults it to a timestamped
directory under `/scratch/jhan/perf-fluctuation/` (echoed at startup).

Preflight aborts if the CI runner (`actions.runner.positron-ai.delphi-3bda-0`)
is active or a runtron/run-benchmark process exists — check before launch.

# monitor

- `cat $CAMPAIGN_ROOT/status.txt` — preparing → mutating_machine → smoke → campaign → analyzing → reporting → awaiting_restore → restored
- `tail -f $CAMPAIGN_ROOT/journal.log` — one `draw_NN OK generate=… tok/s` line per draw, ~2m50s each
- Done when `FINAL_REPORT_DONE` and `RESTORED` markers exist and `harness-exit-code.txt` reads 0

Gotcha: runtron renames its main thread, so `pgrep -x runtron` never
matches a live engine — check with `pgrep -u jhan -f "^/scratch/jhan/tron-perfetto-vanilla-install-20260806/bin/runtron "`.
The v3 harness already handles this; don't reuse the older expanded-tools script.

# outputs

- `$CAMPAIGN_ROOT/results.csv` — all 20 scheduled outcomes incl. failures
- `$CAMPAIGN_ROOT/results/draw_NN/` — per draw: untouched `trace.pftrace` + `metrics.json`, exact `perfetto.cfg`, `perfetto.log`/`.rc`, turbostat `power.tsv`, benchmark + placement logs, cmdline/env/timestamps
- `$CAMPAIGN_ROOT/analysis/` — fast vs slow draw phase/category/top-slice queries
- `$CAMPAIGN_ROOT/report.html` — command line, ranked draws, fast-vs-slow timing deltas vs throughput delta, per-draw core frequency and package power with a fast-vs-slow power comparison

# restore

Automatic on exit (even on failure): stops Perfetto daemons, restarts
rinzler@0-3, restores the serving trio, verifies ≥3 models on
`http://localhost/v1/models`. Confirm `status.txt` reads `restored`;
if `RESTORE_FAILED` exists, the machine needs manual attention.
