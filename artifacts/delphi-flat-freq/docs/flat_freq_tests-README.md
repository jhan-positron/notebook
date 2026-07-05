# flat_freq_tests — checkerboard benchmark runs on delphi-3bda

Benchmark series comparing inference performance under different CPU frequency
configurations (SST-CP CLOS state) on delphi-3bda. Owner: jhan.

## Layout

    scripts/                  runner scripts (see headers for usage)
    <date>_<machine-state>_<test>/   one folder per run (UTC dates)

Machine-state labels:
  boot-default-clamped  BIOS PCT partition active: non-PCT cores in CLOS3,
                        capped at 2700 MHz under load (the "flat freq" bug).
  flat-freq             flat_freq_apply() run beforehand: all 288 CPUs in
                        CLOS0, turbo-freq disabled -> no 2700 MHz clamp.
                        (state resets on reboot; see workspace debug_3bda/)

## Runs

  2026-06-30_boot-default-clamped_gpt-oss-single/
      Reference run (Hannah, tron branch hrv-intel-speed-select-crosscheck-
      measure 66deff22): parse 551.5 tok/s, generate 90.6 tok/s, TTFT 2.32 s,
      TTLT 13.61 s. turbostat: ~89% of busy-core samples at 2.6-2.7 GHz.
      NOTE: thread_cpu_placement file captured only its own monitor loop
      (self-matching pgrep) - contains no runtron data.

  2026-07-02_flat-freq_gpt-oss-single_attempt1-FAILED/
      First flat-freq attempt (tron main ae82870ae). FAILED: both runtron
      instances inherited SYSTEM_CONFIG="--instance 1,2" from
      ~/jibin.bashrc.positron.dev, so both configured as instance 1 ->
      hugepage lock collision (inst 0) + segfault in device init (inst 1).
      Runner now unsets SYSTEM_CONFIG/TRON_LOG_LEVEL/SPDLOG_LEVEL.

  2026-07-02_flat-freq_gpt-oss-single/
      Rerun with env scrubbed. See its folder for results.

## Per-run contents

    sweep_console.log      full run-multi-sweep.sh console output
    turbostat_per_cpu.tsv  5s-interval per-CPU freq/power capture during run
    runner_timeline.txt    start/end timestamps (UTC)
    SWEEP_EXIT_CODE        0 = success
    sweep-results/         checkerboard output tree (metrics.json,
                           summary.log, runtron/log.<n>, alderaan.log)

## HOST FAULT — 2026-07-02 (blocks all benchmarks)

delphi-3bda rebooted 05:08 UTC with 6 of 8 FPGAs unprogrammed: they
enumerated as [12ba:0076] with a single 256M BAR (bootloader state); only
b9:00.0 / bc:00.0 enumerated as the real Positron device [8200:0011] with
BAR0 4M + BAR2 1G + BAR4 128G. The six were flashed after boot (config
space now shows 8200:0011 everywhere) but the kernel never re-assigned
their BAR2/BAR4 (sysfs resource table zeroed). Result: every process that
maps BAR2 on those devices segfaults at offset 0x200010 (NULL + mailbox
offset) — 130 kernel-logged tron crashes since 11:16 UTC incl. daytime CI
and both flat-freq benchmark attempts here.

Evidence: journalctl -k -b (boot enumeration + trap storm),
/sys/bus/pci/devices/0000:{10,b9}:00.0/resource, runtron logs in
2026-07-02_flat-freq_gpt-oss-single/sweep-results.

Fix: warm reboot while images are resident (BARs get assigned at boot
enumeration), or platform bring-up by infra. After ANY reboot re-run
flat_freq_apply (CLOS state resets) before benchmarking.

## 2026-07-03: host fault RESOLVED + flat-freq result

Fix sequence (evening 2026-07-02 UTC): pho bw images use -c {0,1,4,5,6,7}
archer_agm_01.05.08.00.rbf (cards had lost fabric config) -> PCI bridge
remove+rescan -> warm reboot with cards configured -> BIOS sized all four
stack MMIO windows correctly -> 8/8 cards full BARs -> pho test cards dma
readback PASS 8/8. Root cause of the day-long breakage: cards entered POST
unconfigured, BIOS shrink-wrapped stack decode windows to 512M, post-boot
activation could then never get BARs assigned (Linux cannot grow the
firmware decode windows at runtime).

  2026-07-03_flat-freq_gpt-oss-single/   <- THE clean flat-freq run
      exit 0, 0 failed, 8 samples. vs 2026-06-30 clamped baseline:
        parse    644.7 tok/s  (551.5 -> +16.9%)
        generate 102.6 tok/s  ( 90.6 -> +13.3%)
        TTFT     1.985 s      (2.321 -> -14.5%)
        TTLT     11.94 s      (13.61 -> -12.2%)
      turbostat: busy cores flat at 3.9 GHz (mean 3897, min 3711 MHz;
      99% of busy samples in 3800-3999 bin). No 2700 clamp. Peak pkg
      power ~600 W total. Per-instance iteration throughput 722/691
      new tok/s (baseline 616/623).
      Note: ~9 min wall time due to cold weight load after reboot;
      inference itself ~12 s/iteration.

## 2026-07-03: 24-hour multi-model sweep (flat-freq) — RUNNING

Output: 2026-07-03_flat-freq_24h-sweep/   Started 00:56 UTC 2026-07-03.
Expected duration ~24-30 h (539 runs: 11 model configs x 7 zipped length
configs x 7 user counts, speculation off).

MODEL SUBSTITUTION vs Hannah's reference command: tron main (ae82870ae) has
no llama-3.3-70b-instruct-good; replaced with llama-3.1-70b-instruct-good
(tp4, tp2) — same-size dense 70B, equivalent for frequency comparisons.
First attempt (multi-sweep-20260703-004933 in /var/tmp sweeps) was aborted
after every llama-3.3 config failed with "Unsupported model".

## How to run these tests manually

From a shell on delphi-3bda:

    cd /home/jhan/workspace/run_checkerboard/checkerboard
    unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL   # jhan-shell landmine!
    export CHECKERBOARD_MEMLOCK_KB=197971044          # host limit < 200GB default

    # Single gpt-oss test (~2 min warm, ~10 min after reboot):
    ./run-multi-sweep.sh \
      --models ingested-gpt-oss-120b-tp4 \
      -p 1024 -g 1024 --shared-system-prompt-lengths 256 -s 0 -u 8

    # 24-hour sweep: see the "THE BENCHMARK COMMAND" block in
    # scripts/run_24h_sweep.sh (same invocation, 11 models, 7 lengths,
    # 7 user counts). The three length lists are ZIPPED by position,
    # not cross-multiplied.

    # Results: sweeps/multi-sweep-<ts>/<model>/<config>/<inst>-<users>/
    #   metrics.json (harmonic means), summary.log, runtron/log.<n>
    # Consolidated CSV: ./post-processing/export_to_spreadsheet.py sweeps/multi-sweep-<ts>

Before benchmarking after ANY reboot:
  1. flat freq:  source ~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
                 FLAT_FREQ_ISST=/opt/intel-speed-select/intel-speed-select
                 flat_freq_apply
  2. FPGAs: all 8 of /sys/bus/pci/devices/0000:{10,13,38,3b,90,93,b9,bc}:00.0/resource
     must have 3 non-zero BAR lines; validate with: pho test cards dma readback --bdf all
  3. Machine idle: no runtron/rinzler; stale /dev/hugepages/libpos* owned by
     OTHERS must be investigated (fuser) before removal; your own are reused.

Wrappers with monitoring (recommended): scripts/run_gpt_oss_single.sh [outdir],
scripts/run_24h_sweep.sh [outdir]. Both scrub the env landmine, capture
turbostat, and copy results into a self-contained run folder.

## 2026-07-02: SST frequency-exploration work stream (parallel to the
## benchmark runs above; Claude session, ~17:40-22:06 UTC)

All artifacts under the NFS workspace, herein W =
/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/
Machine was left in the flat-freq state (+ boot-faithful CLOS2/3 configs)
after every run. Main report: W/ALLCORE_CEILING_HETERO_CLAUDE_20260702.md
(repro command blocks + exact core lists for every phase).

  All-core ceiling + heterogeneous (RUN1/RUN2):
      W/allcore_ceiling_delphi-3bda_20260702_174444/SUMMARY.md
      W/allcore_tfon_addendum_delphi-3bda_20260702_181035/
      Full-machine load is RAPL-bound: ~3.27 GHz x 288T (~3.6 GHz x 144T)
      at 502 W/pkg in EVERY config; 3.9 GHz all-core is not reachable.
      HT sibling pairs equal within <=7 MHz (first sibling-loaded test).
      KEY RECIPE DELTA: turbo-freq ENABLED + assoc-only -> 4100.0 x80 on
      the checkerboard shape vs 3900 x80 from flat_freq_apply's disables
      (+200 MHz; no BIOS change needed). turbo-freq enable --auto puts
      arbitrary cores at 4400 but clips everything else to 2700.
      Landmine found: core-power enable silently resets CLOS2/CLOS3
      configs (destroys the boot 2700 clamp config).

  TRON scenario (control plane 0-23+sibs pinned 2 GHz):
      W/tron_scenario_delphi-3bda_20260702_192615/ and _b_..._194020/
      Pinning requires CLOS min=max=2000 (min=800 starves to ~0.8 GHz).
      App-core (24-143) ceiling is package-asymmetric: pkg0 ~3.64 GHz /
      pkg1 ~3.26 GHz; flat is the aggregate optimum; hetero mixes lose
      0.9-10%. Report section 5.

  Tooling:
      W/flat_freq_utils.sh PATCHED (backup .bak-20260702): apply pins
      CLOS0; revert restores all boot CLOS configs incl. the CLOS3
      2700 clamp + verifies; FLAT_FREQ_ISST env-overridable (/opt copy
      works NOPASSWD non-interactively). Tested apply->revert->apply.
      W/gen_tron_flatfreq.py: parses tron config/resource-map.yaml
      (granite_rapids_6962p) and emits the exact isst commands to boost
      tron_cores+peer_cores(+HT siblings) to CLOS0 with the rest clipped;
      --also-boost dev,rinzler,platform; --revert; --emit. Validated
      end-to-end (= E1 below). NOTE: default clips dev/rinzler to 2700.

  Can any 80-core freq combination beat all-80-same-freq? (E1+E2):
      W/PLAN_BEAT_80CORE_AGGREGATE_20260702.md (plan + results appendix)
      W/e1e2_beat80_delphi-3bda_20260702_220207/
      E1: generator config verbatim -> 4100.0 x80 exact = 328.0 GHz-cores
      (peer-HT-loaded 160T shape: ~4047). E2: "4400 requires all other
      cores <=2700" rule SURVIVED direct falsification with ~50 W/pkg
      unused headroom -> all-80@4100 is the runtime-SST aggregate
      optimum; BIOS C6 revert (E4) can at best tie -> SKIP.

  Next (pending review): W/PLAN_E5_TRON_TOKPS_20260702.md — tokens/s A/B
      of flat_freq_apply(3900) vs generator 4100 variants using the
      single gpt-oss recipe above. The 2026-07-03 clean run in this
      README is the V1 data point (+16.9% parse / +13.3% gen vs clamped);
      open question is whether 4100 variants add more.

## 2026-07-05: 24h sweep COMPLETE + TRON-80 comparison run started on 3af6

24h flat-freq sweep (2026-07-03_flat-freq_24h-sweep/) finished 02:53 UTC
2026-07-05 after 49h57m (11 models; "24h" is a misnomer at these lengths).
- 483 configs produced metrics (56 configs auto-skipped where user count <
  instance count); exit code 1 solely because of the single known failure.
- Failures: exactly 1 of 483 — llama-3.2-3b-instruct-fast-tp1 /
  spec-off-p1024-g1024-s256 / 8-8, instance 4 segfaulted in TEARDOWN after
  its iteration completed (tron shutdown bug, data for that config lost).
- Flat shape held for the whole run: flat_freq_watch.log 300/300 samples
  clos:0; turbostat 531,188 busy-core samples, mean 3756 MHz, 0.00% in the
  2600-2799 clamp band, 100% >= 3600 MHz.
- Consolidated CSV: sweep-results/results-v2-multi-model-20260703-005629.csv

New run: 2026-07-05_tron80-4100-3af6_gpt-oss-3b-matrix/ on delphi-3af6 —
strict TRON-80 shape (cores 27-46,51-70,75-94,99-118 + HT sibs in
CLOS0/TF-on, verified 4100-4400 MHz; all others CLOS3 <= 2700, verified
2700) applied via flat_freq_apply v2 select mode. Subset: gpt-oss-120b-tp4
+ llama-3.2-3b-fast-tp4, full 7x7 matrices — same matrices as the 24h run
for direct flat-vs-TRON80 comparison (expect TRON-80 faster: busy cores
4100 vs ~3900). Runner: scripts/run_tron80_subset_3af6.sh.

## 2026-07-05: TRON-80 run COMPLETE — comparison vs universal flat

2026-07-05_tron80-4100-3af6_gpt-oss-3b-matrix/ finished 09:31 UTC (6h35m,
rc=0, 98 configs, 0 failures). Shape held the whole run (shape_watch 40/40
cpu30=clos:0 and cpu2=clos:3; turbostat TRON cores: 56,039 busy samples,
mean 3977 MHz, 99.9% >= 3900, none in 2600-2799). Consolidated CSV:
sweep-results/results-v2-multi-model-20260705-025559.csv

Per-config geomean ratios, TRON-80@4100 (3af6) vs universal-flat@3900
(3bda 24h run), 49/49 overlapping configs per model:

  ingested-gpt-oss-120b-tp4:  parse +2.9% (better in 46/49),
    generate +1.0% (38/49), TTFT 2.9% faster (46/49), TTLT 1.3% faster.
    -> TRON-80 wins on all four metrics, as expected.

  llama-3.2-3b-instruct-fast-tp4: parse +2.7%, TTFT 2.6% faster (38/49),
    but generate -0.8% (better in only 11/49) and TTLT -0.4%.
    -> Mixed. Parse (CPU-bound) gains; small-model generation regresses
    slightly — consistent with the strict-80 shape clipping the FPGA
    DRIVER cores (25,26,49,50,73,74,97,98) to 2700 (they ran ~3900 in the
    flat run). This is the exact V2-risk noted in PLAN_E5; the
    --also-boost dev variant (88-core shape) is the candidate fix.

Caveat: cross-host comparison (3af6 vs 3bda, same 6962P/8-FPGA spec, same
NFS runtron build ae82870ae); magnitudes are 1-3%, so host variance is not
fully excluded, but the per-config pairing and consistent directionality
support the frequency-shape explanation.

State left on 3af6: TRON-80 shape still applied (does not survive reboot);
jhan-owned libpos hugepage slice files remain (reused by future runs).

## 2026-07-05: 24h flat run vs CLAMPED baseline (Hannah, Jun 30)

Baseline found: delphi-3bda:/var/tmp/hvaneenoo/checkerboard/sweeps/
multi-sweep-20260630-030357/results-v2-multi-model-20260630-030357.csv —
188 configs, same host (3bda), Hannah tron branch hrv-intel-speed-select,
boot-default CLAMPED state (verified: its gpt-oss p1024 2-8 row matches
her instrumented single run within ~2%, whose turbostat showed the
2.6-2.7 GHz clamp).

151 configs pair with the 24h flat run. Flat-freq uplift vs clamped
(per-config geomeans; flat wins nearly every individual config):

  model                  parse    generate  TTFT       TTLT
  gpt-oss-120b tp4      +12.6%    +9.9%    11.1% fst   9.4% fst  (20 cfg)
  llama-8b-good tp4     +12.2%    +8.4%    11.2% fst   8.2% fst  (20)
  llama-8b-good tp2     +11.4%    +6.7%     9.9% fst   6.8% fst  (16)
  llama-3b-fast tp4     +13.9%    +7.6%    11.9% fst   7.8% fst  (20)
  llama-3b-fast tp2     +16.8%    +7.3%    13.3% fst   7.7% fst  (16)
  llama-3b-fast tp1     +13.0%    +5.9%    11.7% fst   6.4% fst  (11)
  mixtral tp4            +7.5%    +4.4%     7.0% fst   4.8% fst  (20)
  mixtral tp2            +6.3%    +3.2%     6.0% fst   3.5% fst  (16)
  mixtral tp1            +4.3%    +3.4%     4.1% fst   3.5% fst  (12)

Gaps/caveats: 70B has NO clamped baseline (hers is llama-3.3, ours 3.1 —
no pairing); baseline covers fewer user counts than our 482-config run;
tron versions differ (hers 66deff22-era branch vs our main ae82870ae).
Same-host comparison though — stronger than the cross-host tron80 one.
Older baselines also exist (multi-sweep-20260603/04) and Talos MongoDB
holds nightly CI history (see llm-toolbox talos-database-access.md).

## 2026-07-05: TRON-88 baseline round COMPLETE (3bda, 55 min)

2026-07-05_tron88-4100-3bda_baseline-matrix/: 56 configs (gpt-oss-tp4 +
8b-good tp4/tp2, lengths 256-2048 x users 2-32 = Hannah's baseline grid),
0 failures, rc=0, 14:19-15:14 UTC. Shape (cores 25-46,49-70,73-94,97-118
+ sibs @ CLOS0/TF-on) held 6/6 watch samples; fast-set busy mean 4042 MHz,
none in clamp band. CSV: sweep-results/results-v2-multi-model-20260705-141935.csv

(a) tron88 vs CLAMPED baseline (same host, exact config pairing):
    gpt-oss-tp4: parse +14.6, gen +10.9, TTFT 12.6 fst, TTLT 10.3 fst (20/20 all)
    8b-tp4:      parse +13.7, gen  +9.9, TTFT 12.2 fst, TTLT  9.4 fst (20/20)
    8b-tp2:      parse +12.9, gen  +7.6, TTFT 11.1 fst, TTLT  7.7 fst
(b) tron88 vs universal FLAT (same host): +0.9 to +1.8% everywhere —
    first same-host confirmation that the TRON shape beats flat.
(c) tron88 vs strict TRON-80 (3af6): ~0% (+-0.4) for gpt-oss — the
    driver-core boost is neutral for gpt-oss (the earlier 3B generation
    dip remains the only known driver-clip symptom; 3B not in this round).
    Also validates cross-host comparability at the ~0.5% level.
