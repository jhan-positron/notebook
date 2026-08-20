# Runbook: decode-TPS fluctuation screen for ingested-llama-3.1-8b (tp2, tp4)

Written 2026-08-14 by the trace-sync-points session. Owner: Jibin (jhan).
Audience: the agent that will execute this. Self-contained; read fully before acting.

## 0. Goal and decision rule

Determine whether **decode TPS fluctuates draw-to-draw** for the ingested
Llama-3.1-8B model at **tp2** and **tp4**. This is a screen, not a drill-down:
**stock latest main, no probes, no perfetto, no extra instrumentation.** The only
measurement is the harness's own per-draw TPS.

Decision metric (owner-set threshold, 2026-08-14): draw-level TPS CV over the
campaign's draws, plus the max−min gap as a companion guard.

| classification | rule (matches the deep-dive screen precedent) |
|---|---|
| FLUCTUATES ("rolls") | CV ≥ ~1.0% or gap ≥ ~3% |
| TIGHT | CV < 1.0% and gap < 3% |

Run **20 draws per config** (screen precedent; at n=20 a CV estimate has ~±16%
relative error at 1σ — mention this next to any borderline verdict).

Why this test: qwen-3-4b tp4 fluctuates (CV 1.3–3.3% across campaigns/hosts/builds);
on qwen, tp1 and tp2 screens were tight and tp4 rolled (deep-dive report
2026-08-11-02). If llama-8b shows the same tp2-tight/tp4-rolls pattern, the
phenomenon follows the parallelism degree; if llama tp4 is tight, it is
model-dependent. Also note the counter-example on record: llama-70b tp4 was TIGHT
on delphi-3af6 (PDJN) — fluctuation is host- and model-dependent, so state host in
every claim.

## 1. Model facts (from config/models.yaml @ latest main)

- Registry entry `ingested_llama_3p1_8b`, support_level *working*, generated C++
  plugin ("tokens verified end-to-end"), trace_dir `traces/ingested-llama-3.1-8b`.
- Variant slug `ingested-llama-3.1-8b`, executors **tp1, tp2, tp4** → runtron
  model names `ingested-llama-3.1-8b-tp2` and `ingested-llama-3.1-8b-tp4`.
- Do NOT use the `-permuted` variant here (different executor class, tag test).

## 2. Build (alpha, claude-box) — stock latest main

```sh
cd /home/jhan/workspace/tron && git fetch origin main
git worktree add ../tron-llama8b origin/main    # record the exact sha in your notes
cd ../tron-llama8b
cp ../tron-kvprobe/config/models.local.yaml config/
```

Then EDIT `config/models.local.yaml`: **delete the two override entries**
`ingested_llama_3p1_8b` and `ingested_llama_3p1_8b_permuted` (they exclude the
model this screen needs; keep all other exclusions — they block gated models the
build cannot fetch). Do NOT copy anything from the probe worktrees' source
patches: this build must be stock.

```sh
PATH=/nix/var/nix/profiles/default/bin:$PATH nix develop -c bash -c \
  "cmake --preset native && ninja -C gen runtron"
```

**Known blocker — plan for it:** the `ingested-llama-3.1-8b` torch-trace export
downloads from the GATED HuggingFace repo `meta-llama/Llama-3.1-8B-Instruct`;
claude-box has no HF token and the export fails with HTTP 401 (observed
2026-08-14). Resolutions, in order of preference:

1. Copy an already-exported trace dir into the worktree as
   `ingest/traces/ingested-llama-3.1-8b/` (must contain `torch-export.stamp`).
   Look for one in other tron checkouts on alpha, on /scratch, or on 3bda
   (`find ~/workspace /scratch -maxdepth 6 -type d -name "ingested-llama-3.1-8b"`).
2. Ask the owner for an HF token with meta-llama access; export
   `HF_TOKEN=<token>` in the nix develop shell for the build.
3. If neither works, STOP and report — do not improvise model substitutes.

**Deploy (RUNPATH gotcha, hit 2026-08-14):** latest main's binary uses
$ORIGIN-relative RUNPATH; a bare `bin/runtron` copy aborts with exit 127
(`libfuse3.so.4 ... No such file`). Stage the install like this and verify:

```sh
D=/scratch/jhan/perf-fluctuation/deep-dive
mkdir -p $D/install-llama8b-stock/bin $D/install-llama8b-stock/lib
cp gen/runtron $D/install-llama8b-stock/bin/
cp gen/src/libversion.so $D/install-llama8b-stock/lib/
cp gen/libfuse3_external-prefix/src/libfuse3_external-build/lib/libfuse3.so.4 $D/install-llama8b-stock/lib/
sha256sum $D/install-llama8b-stock/bin/runtron        # record as EXPECTED_BIN_SHA
ssh jhan@delphi-3bda "env -i LD_LIBRARY_PATH=$D/install-llama8b-stock/lib \
  /usr/bin/ldd $D/install-llama8b-stock/bin/runtron | grep -c 'not found'"   # must print 0
```

Never rebuild this worktree while a campaign that uses the install may be running
(libraries resolve over NFS).

## 3. Campaigns (delphi-3bda ONLY)

Owner directives: delphi-3bda only (Bill's 3c51 is off-limits); the harness
refuses to start inside the nightly CI window **02:30–11:30 UTC** — schedule
around it; the harness itself stops/restores the serving trio behind a traffic
gate, do not do that by hand. One campaign at a time. Monitor from alpha via NFS
tail of `$ROOT/journal.log` / `results.csv`; NEVER run remote helper commands
whose cmdline contains benchmark keywords (e.g. "runtron") while a draw may
start. Prefer one ssh session with a remote loop over repeated one-shot ssh
(login spawns ssh-agents; orphans accumulate).

Two campaigns, standard harness (`deepdive-campaign.sh`, per-campaign copy —
never edit a running script). tp4 first (the config most likely to roll), then tp2:

```sh
D=/scratch/jhan/perf-fluctuation/deep-dive
SHA=<EXPECTED_BIN_SHA from step 2>
# --- campaign A: tp4 (4 cards -> SLICE_OF=2) ---
ROOT=$D/3bda-llama8b-tp4-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p $ROOT && cp $D/tools/deepdive-campaign.sh $ROOT/harness.sh
ssh jhan@delphi-3bda "setsid env MODEL=ingested-llama-3.1-8b-tp4 SLICE_OF=2 \
  ROUNDS=20 CAPTURE=none KVWAIT=0 INSTALL=$D/install-llama8b-stock \
  EXPECTED_BIN_SHA=$SHA CAMPAIGN_ROOT=$ROOT \
  bash $ROOT/harness.sh > /tmp/3bda-llama8b-tp4.stdout 2>&1 < /dev/null &"
# wait for $ROOT/harness-exit-code.txt, verify 'restored' + 20/20 ok, THEN:
# --- campaign B: tp2 (2 cards -> SLICE_OF=4) ---
#   same as above with MODEL=ingested-llama-3.1-8b-tp2, SLICE_OF=4, new ROOT
#   3bda-llama8b-tp2-<ts>
```

Notes:
- `KVWAIT=0` keeps the run instrumentation-free (this is the point of the screen).
- First-ever launch of this model on 3bda downloads/ingests weights into the
  host's cache. If the smoke fails with `model load timeout` (300 s), simply
  relaunch the campaign once the cache is warm; if it fails twice, check disk and
  the weights id before retrying. Budget time for this on campaign A only.
- Gates the harness applies for you: CI window, runner idle, binary sha, traffic
  gate, bitfile consistency per draw, sw-attention banner, device set
  (tp4: expects the first 4 BDFs; tp2 with SLICE_OF=4 uses the first 2 — if the
  'wrong device set' gate trips on tp2, read the harness EXPECTED_DEVS logic and
  report rather than editing gates).
- Determinism check: the harness runs greedy with a fixed seed
  (`--threshold_p 0 --dont-stop -s ...`), so `token_sha256` must be IDENTICAL
  across all draws within a campaign. There is no external reference sha for this
  model — within-campaign identity is the gate; record the sha.
- Verify at the end of each campaign: `status.txt` = restored, harness exit 0,
  20/20 ok in results.csv.

## 4. Analysis and report

All inputs are in `$ROOT/results.csv` (columns include draw, status,
generate_tok_s, token_sha256). Per config compute over ok draws:

- mean, sd (state population vs sample), **CV**, min, max, **gap = (max−min)/mean**;
- per-token time sd in µs (sd of 1e6/tps) — the absolute-units honesty check;
- the classification against section 0's rule, with the n=20 precision caveat.

Deliverable: `status_report/report.md` in THIS project folder — create the
`status_report/` directory if it does not exist. Markdown, per owner conventions:
plain English or exact source terms only, every claim citing its campaign id.
Contents: the per-config numbers table (mean, sd, CV, min, max, gap, per-token
sd in µs, classification); the per-draw TPS values listed per config; a text
dot-strip of per-draw TPS if it fits within 70 columns (horizontal layout,
one row per config), otherwise the sorted per-draw list suffices. Compare
against the qwen-3-4b picture (control 08-14: CV 1.32% on 3c51; wadefix-on:
CV 1.32% on 3bda — context only, different host/model, never merged into the
classification) and state the conclusion in one sentence per config:
fluctuates or tight, on delphi-3bda, at this build.

Archive: copy both results.csv into this folder (`data/`), since /tmp scratchpads
get wiped — anything a report depends on lives in the workspace or /scratch.

## 5. What NOT to do

- No kvwait probes, no perfetto, no gen-file edits, no driver patches — a stock
  binary is the experimental condition here.
- No comparisons across hosts in one table (3bda numbers vs 3c51 numbers may be
  labeled as context, never merged into one classification).
- Do not run anything on Bill's delphi-3c51.
- Do not chase causes in this runbook's scope: if a config fluctuates, the output
  is the classification + the report. Cause-hunting belongs to the
  perf-fluctuation/intra-pass project (see ../intra-pass/CONTEXT.md).

## 6. Context pointers

- Fluctuation state of the art: ../trace-sync-points/status_report/
  2026-08-13-03-wcls-bypass.html (jitter anatomy on qwen-3-4b tp4) and
  ../intra-pass/CONTEXT.md (current project, terminology, ops rules).
- Screen precedent + thresholds: ../deep-dive/status_report/
  2026-08-11-02-deepdive-report.html (tp1/tp2/tp4 bare screens, CV/gap table).
- Harness reference: /scratch/jhan/perf-fluctuation/deep-dive/tools/
  deepdive-campaign.sh (3bda variant; read its env knobs before launching).
