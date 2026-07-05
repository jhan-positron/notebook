# PLAN E5 (draft for review): pick the SST frequency policy by TRON tokens/s

Goal: choose the production frequency configuration for delphi-class 6962P
hosts by measuring what TRON actually delivers (tokens/s), not GHz. Follows
PLAN_BEAT_80CORE_AGGREGATE_20260702.md (E1/E2 executed separately).

## Benchmark vehicle

Single gpt-oss checkerboard run, exactly the known-good recipe:
```
cd /home/jhan/workspace/run_checkerboard/checkerboard
./run-multi-sweep.sh --models ingested-gpt-oss-120b-tp4 -p 1024 -g 1024 \
    --shared-system-prompt-lengths 256 -s 0 -u 8
```
Wrapper: `/scratch/jhan/flat_freq_tests/scripts/run_gpt_oss_single.sh` (already
scrubs the SYSTEM_CONFIG env landmine and captures a 288-CPU turbostat trace).
Metrics: `metrics.json` harmonic means — parse tok/s, generate tok/s, TTFT,
TTLT, failed_count. Reference point (2026-06-30, boot-clamped 2700): parse
551.5 / gen 90.6 tok/s, TTFT 2.32 s (2 inst x 4 users; tron branch
hrv-intel-speed-select-crosscheck-measure).

## Variants (state applied before each run; verified by assoc sweep + TF/CLOS
readback; each is one command block from existing tooling)

| V | Config | Loaded-core freqs (from our SST data) |
|---|---|---|
| V1 | `flat_freq_apply` (TF off, all->CLOS0) — current candidate | tron/dev/rinzler all 3900 |
| V2 | `gen_tron_flatfreq.py` default | tron+peer 4100; dev/rinzler/platform CLIPPED 2700 |
| V3 | `gen_tron_flatfreq.py --also-boost dev,rinzler,platform` | tron+peer+dev+rinzler 4100 |
| V4 | assoc-only (all 288 -> CLOS0, TF on) — simplest ops | everything 4100 |
| V0 | boot default (optional re-baseline on current tron build) | tron 2700 (+8 PCT cores 4400) |

Priority if time is short: V1 vs V3 vs V4 (V2 risks slowing rinzler/dev data
movers below even the boot behavior for a workload that uses them — include V2
only to quantify that risk). V5 (4400 rinzler cores) is DROPPED unless E2
falsified the "4400 requires rest<=2700" rule.

## Design

- 2 runs per variant, interleaved (V1,V3,V4,V4,V3,V1 ...) to cancel drift;
  report mean +/- spread. Success = variant beats V1 on generate tok/s by more
  than the run-to-run spread.
- Pre-flight per run: FPGA BAR2 check (`/sys/bus/pci/devices/0000:10:00.0/resource`
  line 3 non-zero — 2026-07-02 fault mode), SST state verify, GitHub runner
  idle. Post: revert to V1 state (flat_freq_apply).
- Attribution: from each run's turbostat trace, per-role Bzy_MHz (tron/dev/
  rinzler/platform) to confirm the intended freqs actually held during the run.

## Prerequisites / open questions for Jibin

1. Scheduling: delphi-3bda is a split runner — inference window is 02:45-14:00
   UTC (runner stopped), or stop it via `sudo /opt/positron/ci/ci-runner.sh
   stop` (is that sudo available to jhan non-interactively? my NOPASSWD set
   doesn't include it). Which window do you want?
2. `sudo systemctl stop 'rinzler@*'` pre-flight from the cheatsheet — same
   sudo question.
3. Which tron build: `/home/jhan/workspace/run_checkerboard/tron` main
   (ae82870ae) or Hannah's reference branch (66deff22) for comparability with
   the 2026-06-30 number?
4. Instances/users shape: single-instance `-u 8` (the cheatsheet single test)
   or 2 inst x 4 users (the June reference shape)?
5. Acceptance bar: how big a generate-tok/s win justifies changing the
   production recipe from V1 to a TF-on variant?

## Estimated cost

~10-20 min per run x 6-8 runs = 1.5-3 h inside one inference window, machine
left in flat state. Analysis + verified report: same session.
