# All-core ceiling + heterogeneous frequency — delphi-3bda (2026-07-02)

Machine: Xeon 6962P x2, 144 cores / 288 CPUs. Sibling of CPU N = N+144.
pkg0 = CPUs 0-71 + 144-215, pkg1 = 72-143 + 216-287. Six 24-core power
domains, anchors 0,24,48,72,96,120. RAPL PL1 = 500 W/pkg, PL2 = 600 W/pkg
(sysfs, read live). tjmax 107 C.

All numbers were re-derived from the raw turbostat captures by independent
verification agents; a journalctl audit of every isst write in the window
found zero foreign writes. Load = 25 s pinned shell-spin per listed CPU
(scalar/SSE license class 0); frequencies are mean Bzy_MHz of loaded CPUs
over the window; PkgWatt is turbostat package power over the same window.

## 0. Direct answers

1. **All 144 cores / 288 threads at one speed top out at ~3.25-3.30 GHz and
   502 W/pkg — 3.9 GHz for all 144/288 cores is NOT reachable under this
   load.** The limiter is the 500 W package power limit (PL1), not CLOS, not
   TRL: every configuration tried (TF on/off, core-power on/off, all-CLOS0)
   lands within 3241-3295 MHz at 501-502 W on both packages. Thermal is not
   the limiter (PkgTmp <= 84 C vs tjmax 107). Note this is for a pure-compute
   spin; lighter/memory-bound workloads draw less power per core and will sit
   higher.
2. **Aggregate throughput (GHz x cores): heterogeneous mixes do NOT beat the
   uniform config at full load** — see section 3. Jibin's math is right:
   4x4.4 + 140x2.7 = 395.6 GHz-cores loses badly to uniform. The correct
   uniform baseline at full load is 144 x 3.27 = 470.8 GHz-cores (not
   144 x 3.9 = 561.6, which is beyond the power budget). The best hetero mix
   measured (4x4100 + 140x3251) reaches 471.6 — break-even. At the power
   wall, redistribution is zero-sum; hetero only pays off when specific
   threads are worth more than others (e.g. TRON data plane vs control
   plane — see section 5).
3. **Best flat recipe when NOT power-bound (<= ~20 loaded cores/domain, e.g.
   the 80-CPU CI shape): leave turbo-freq ENABLED and only re-associate:
   4100.0 x80 exact — +200 MHz over the disable-based recipe (3900.0 x80).**
4. **HT siblings always run at core speed**: max sibling-pair delta 0-7 MHz
   across all 144 pairs in every phase.
5. **TRON scenario (control plane 0-23 pinned 2 GHz)**: the app-core ceiling
   is package-asymmetric — pkg0 app cores ~3.64 GHz, pkg1 ~3.26 GHz — and the
   flat config is the aggregate optimum (409.3 GHz-cores); the cheapest
   fast-core mix (8 cores at 4000-4100) costs -0.9 %. See section 5.

## 1. Method / repro template

```
ISST="sudo /opt/intel-speed-select/intel-speed-select"   # NOPASSWD on 3bda
W=/home/jhan/workspace/intel-vs-amd/speed-select/workspace

# measured load: turbostat runs the spin as its child, so the measurement
# window exactly covers the load. <CPUS...> = space-separated CPU list.
sudo /usr/bin/turbostat --quiet --interval 1 \
  --out turbostat.tsv \
  bash $W/debug_3bda/test_allcore_ceiling_3bda.sh __spin 25 <CPUS...>
# summarize:
python3 $W/debug_3bda/summarize_allcore.py turbostat.tsv <tag> <CPUS...>
```

Harnesses that produced the data (each phase applies config, loads, captures
state incl. full 288-CPU assoc sweeps, and auto-reverts on exit):
- RUN1 `debug_3bda/test_allcore_ceiling_3bda.sh` ->
  `debug_3bda/allcore_ceiling_delphi-3bda_20260702_174444/`
- RUN2 `debug_3bda/addendum_tfon_3bda.sh` ->
  `debug_3bda/allcore_tfon_addendum_delphi-3bda_20260702_181035/`
- RUN3 `debug_3bda/tron_scenario_3bda.sh` ->
  `debug_3bda/tron_scenario_delphi-3bda_20260702_*/` (section 5)

**Restore-to-boot-default block** (run between repro experiments; needed
because `core-power enable` and `turbo-freq enable --auto` rewrite CLOS
configs — see section 4):

```
for cpu in 0 24 48 72 96 120; do
  $ISST --cpu $cpu turbo-freq enable
  $ISST --cpu $cpu core-power disable
  $ISST --cpu $cpu core-power config --clos 0 --weight 0 --min 2700 --max 4400
  $ISST --cpu $cpu core-power config --clos 1 --weight 0 --min 0 --max 25500
  $ISST --cpu $cpu core-power config --clos 2 --weight 0 --min 0 --max 25500
  $ISST --cpu $cpu core-power config --clos 3 --weight 0 --min 800 --max 2700
done
$ISST --cpu 0,1,18,19,36,37,54,55,72,73,90,91,108,109,126,127,144,145,162,163,180,181,198,199,216,217,234,235,252,253,270,271 core-power assoc --clos 0
$ISST --cpu 2-17,20-35,38-53,56-71,74-89,92-107,110-125,128-143,146-161,164-179,182-197,200-215,218-233,236-251,254-269,272-287 core-power assoc --clos 3
```

CPU set names used below:

- `ALL288`  = 0-287
- `HALF144` = 0-143 (one thread per core)
- `CHECKER80` = 27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118
  (ranges 27-46,51-70,75-94,99-118; 40 per package; no HT siblings)
- `SEL8` = 30,31,102,103,174,175,246,247 (cores 30,31 pkg0 + 102,103 pkg1,
  both HT threads; arbitrary NON-fused cores)
- boot CLOS0 set (the 16 fused PCT cores + siblings, 32 CPUs) =
  0,1,18,19,36,37,54,55,72,73,90,91,108,109,126,127,
  144,145,162,163,180,181,198,199,216,217,234,235,252,253,270,271

## 2. Results — each phase with exact repro commands

Every block below assumes **boot-default state** (or the restore block above)
as the starting point.

### 2.1 Boot default, full load  (RUN1 baseline_full)

Config: none (boot default: TF enabled, boot CLOS partition).
Load: ALL288.

Result:
```
2700 MHz x256  = every CPU except the boot CLOS0 set
4400 MHz x32   = exactly the boot CLOS0 set (verified set-equal):
                 0,1,18,19,36,37,54,55,72,73,90,91,108,109,126,127,
                 144,145,162,163,180,181,198,199,216,217,234,235,252,253,270,271
sibling max delta 0 MHz
```
PkgWatt: not power-bound (weighted mean 2889 MHz).

### 2.2 Flat (all->CLOS0), TF disabled — the flat_freq_apply state, 3 loads

Config (equivalent to `flat_freq_apply` in `debug_3bda/flat_freq_utils.sh`):
```
for cpu in 0 24 48 72 96 120; do
  $ISST --cpu $cpu core-power disable
  $ISST --cpu $cpu turbo-freq disable
done
$ISST --cpu 0-287 core-power assoc --clos 0
```

| Load | Result | PkgWatt |
|---|---|---|
| ALL288 | 3246-3295 MHz, all 288 CPUs (uniform; ~20 MHz pkg0-vs-pkg1 asymmetry) | 502.0 / 501.9 |
| HALF144 | 3594-3620 MHz, all 144 CPUs | 502.0 / 501.8 |
| CHECKER80 | **3900 MHz exactly, all 80 CPUs** (27-46,51-70,75-94,99-118) | 462.5 / 450.9 |

(RUN1 phases tfoff_allclos0_full / tfon_allclos0_half144 / tfon_allclos0_checker80 —
the latter two ran in this TF-disabled state due to the 17:46:32 flat_freq_apply
collision, journal-verified, PERF_STATUS fingerprint 0x2700.)

### 2.3 Flat (all->CLOS0), TF ENABLED — the better flat recipe  (RUN2)

Config (assoc-only; TF stays at its boot-enabled state):
```
for cpu in 0 24 48 72 96 120; do $ISST --cpu $cpu turbo-freq enable; done  # no-op from boot
$ISST --cpu 0-287 core-power assoc --clos 0
```

| Load | Result | PkgWatt |
|---|---|---|
| ALL288 | 3256-3284 MHz, all 288 CPUs | 502.0 / 501.8 |
| HALF144 | 3597-3622 MHz, all 144 CPUs | 501.8 / 501.9 |
| CHECKER80 | **4100 MHz exactly, all 80 CPUs — +200 MHz vs 2.2 on every CPU** | 498.3 / 495.1 |

C6 is disabled on this host (idle threads sit in C1E; CPU%c6=0 in every
capture) and 4100 was still reached: the TF >=54-HP-core bucket bypasses the
TRL active-core-count bucket, so no BIOS C-state change is needed.
Adding `core-power enable --priority 0` on the anchors changes nothing at
full load (3229-3254 MHz, 501.5/501.3 W) — but it resets CLOS2/CLOS3 configs
(section 4).

### 2.4 Heterogeneous, CLOS-weight split  (RUN1 hetero_clos_full)

Config:
```
for cpu in 0 24 48 72 96 120; do
  $ISST --cpu $cpu turbo-freq enable
  $ISST --cpu $cpu core-power enable --priority 0
  $ISST --cpu $cpu core-power config --clos 0 --weight 15 --min 3900 --max 4400
  $ISST --cpu $cpu core-power config --clos 1 --weight 15 --min 800 --max 3900
done
$ISST --cpu 0-287 core-power assoc --clos 1
$ISST --cpu 30,31,102,103,174,175,246,247 core-power assoc --clos 0
```
Load: ALL288.

Result:
```
fast (SEL8): pkg0 cores 30,31 (CPUs 30,31,174,175)  = 4051-4052 MHz
             pkg1 cores 102,103 (CPUs 102,103,246,247) = 3984 MHz
             (package-asymmetric, power-modulated inside the 3900-4400 window)
rest x280:   3171-3187 MHz
```
PkgWatt: 501.9 / 501.7 (power-bound).

### 2.5 Heterogeneous, per-core SST-TF designation  (RUN1 hetero_tfauto_full)

Config:
```
$ISST --cpu 0-287 core-power assoc --clos 0
for cpu in 0 24 48 72 96 120; do
  $ISST --cpu $cpu turbo-freq enable
  $ISST --cpu $cpu core-power disable
done
$ISST --cpu 30,31,102,103 turbo-freq enable --auto
#  ^ --auto by itself re-partitions EVERYTHING: 30,31,102,103 + HT siblings
#    174,175,246,247 -> CLOS0; the other 280 CPUs -> CLOS3; wipes all four
#    CLOS min/max to 0/MaxTurbo; enables core-power, priority-type ordered.
```
Load: ALL288.

Result:
```
fast x8: CPUs 30,31,102,103,174,175,246,247 = 4400 MHz (each exactly 4400.0)
rest x280: 2700 MHz (stdev 0)
```
PkgWatt: 450.4 / 444.7 (NOT power-bound — commons clipped at 2700 leave budget).
Note: 4400 on ARBITRARY (non-fused) cores — the SST-TF HP clamp acts below
HWP (all 288 CPUs carry identical HWP_CAP/HWP_REQ).

### 2.6 Heterogeneous, TF-auto + commons un-clipped  (RUN1 hetero_tfauto_fixcommons_full)

Config (continues from 2.5):
```
for cpu in 0 24 48 72 96 120; do
  $ISST --cpu $cpu core-power config --clos 0 --weight 15 --min 2700 --max 4400
  $ISST --cpu $cpu core-power config --clos 1 --weight 15 --min 800 --max 3900
done
$ISST --cpu 0-287 core-power assoc --clos 1
$ISST --cpu 30,31,102,103,174,175,246,247 core-power assoc --clos 0
```
Load: ALL288.

Result:
```
fast x8: CPUs 30,31,102,103,174,175,246,247 = 4100 MHz (each exactly 4100.0)
rest x280: 3241-3262 MHz (pkg0 ~3242, pkg1 ~3260)
sibling max delta 3 MHz
```
PkgWatt: 502.1 / 501.9 (power-bound again; the freed budget lifted the
commons, and the fast cores settled from 4400 to 4100).

## 3. Aggregate throughput (GHz-cores = sum of core clock over 144 cores)

| Config | Sum (GHz-cores) | vs uniform |
|---|---|---|
| uniform flat, full load (2.3, ALL288: 144 x 3.269) | 470.8 | baseline |
| hetero 2.6 (4 x 4.100 + 140 x 3.251) | 471.6 | +0.2 % (break-even) |
| hetero 2.4 (4 x 4.018 + 140 x 3.179) | 461.2 | -2.0 % |
| hetero 2.5 (4 x 4.400 + 140 x 2.700) | 395.6 | **-16 %** (Jibin's math confirmed) |
| hypothetical 144 x 3.9 | 561.6 | unreachable at 500 W/pkg |

Conclusion: **at the package power wall, heterogeneous mixes cannot beat the
uniform configuration in aggregate** — the PCU already distributes the whole
budget; making some cores faster only takes clock from the rest (at best
break-even, and clipping commons to 2700 wastes ~50 W/pkg of budget).
Heterogeneous configs are the right tool only when some threads are worth
more than others, or when part of the machine intentionally runs slow and
donates its power budget — which is exactly the TRON scenario below.

## 4. Mechanism notes (verified from state captures + MSRs + journal)

- `turbo-freq enable --auto --cpu <list>` re-partitions the whole socket
  (targets + HT siblings -> CLOS0, everyone else -> CLOS3), wipes ALL FOUR
  CLOS min/max configs to 0/"Max Turbo frequency", enables core-power and
  switches priority-type proportional -> ordered. Full revert needs the
  restore-to-boot block in section 1 (or reboot).
- `core-power enable` (any variant) implicitly RESETS CLOS2/CLOS3 configs to
  weight 15 / min 0 / max MaxTurbo — it silently destroys the boot CLOS3
  clamp (800-2700). Consequence: once CP enable has run in a boot, re-assoc
  of the boot map alone does NOT restore the clipped baseline; CLOS3 must be
  re-configured (see restore block) or the box rebooted.
- The SST-TF HP/LP frequency split is enforced below HWP: HWP_CAP
  (0x05081b2c) and HWP_REQ (0x2c2c, min=max=4400) are identical on all 288
  CPUs even while commons run 2700.
- MSR 0x64f (CORE_PERF_LIMIT_REASONS) reads 0x0 on all CPUs in all phases on
  this SKU — including while demonstrably pinned at PL1. Do not use it for
  limiter attribution here; use PkgWatt vs RAPL sysfs limits.
- PERF_STATUS end-of-window P-state request: 0x2700 (=3900) in every
  TF-disabled phase vs 0x2900 (=4100) in every TF-enabled phase — a quick
  MSR fingerprint for "is TF effectively on".

## 5. TRON scenario — control plane slow, app cores 24-143 optimized (RUN3)

Scenario: cores 0-23 + siblings (CPUs 0-23,144-167, all of pkg0 power domain 0)
are TRON control plane, fixed ~2 GHz. Optimization target: app cores 24-143 +
siblings (CPUs 24-143,168-287; 120 cores / 240 threads).
Runs: `tron_scenario_delphi-3bda_20260702_192615/` and (corrected control pin)
`tron_scenario_b_delphi-3bda_20260702_194020/`. All loads = all 288 CPUs
spinning (control plane spins at its cap) unless noted.

### 5.0 Control-plane pinning — read this first

`--min 800 --max 2000` does NOT hold the control plane at 2 GHz under
contention: with the app cores saturating the power budget, the PCU starved
the CLOS2 cores down to ~800-870 MHz (they only reached 2000 when budget was
free). **To fix the control plane at 2 GHz use `--min 2000 --max 2000`** —
verified: all 48 control CPUs then run exactly 2000 under full contention.
The min=800 phases below are therefore a "control donates maximum budget"
bound; the min=2000 phases are the true scenario.

### 5.1 App-core flat ceiling (the true scenario: control pinned 2000)

Config (from boot default or the restore block; CP stays disabled):
```
for cpu in 0 24 48 72 96 120; do
  $ISST --cpu $cpu turbo-freq enable
  $ISST --cpu $cpu core-power config --clos 0 --weight 0 --min 2700 --max 4400
  $ISST --cpu $cpu core-power config --clos 2 --weight 0 --min 2000 --max 2000
done
$ISST --cpu 24-143 core-power assoc --clos 0
$ISST --cpu 168-287 core-power assoc --clos 0
$ISST --cpu 0-23 core-power assoc --clos 2
$ISST --cpu 144-167 core-power assoc --clos 2
```
Load: ALL288. Result (`app_flat_ctrl_pin2g`):
```
control x48 (CPUs 0-23,144-167):        2000 MHz exact
pkg0 app x96 (cores 24-71 + sibs):      ~3637 MHz  (3600-bucket x96)
pkg1 app x144 (cores 72-143 + sibs):    ~3260 MHz  (3300-bucket x144)
sibling max delta 3 MHz
app aggregate: 409.3 GHz-cores
```
PkgWatt: 502.0 / 501.9.

**The app-core ceiling is package-asymmetric** because the control plane
lives entirely in pkg0: pkg0 splits its 500 W across only 48 app cores
(~3.64 GHz each) while pkg1 splits its 500 W across 72 app cores
(~3.26 GHz each). There is no single "ceiling for all 120 cores" — it is
~3.6 GHz on pkg0 and ~3.3 GHz on pkg1 for this spin load. (With the control
plane left to starve at ~0.8 GHz — min=800 — the same config gives
pkg0 ~3.78 / pkg1 ~3.30, aggregate 418.7; control idle: 420.4.)

### 5.2 Heterogeneous sweep (fast app cores via TF-auto, commons <= 3900)

Config template (fast set F = physical-thread CPU list; from the 5.1 state):
```
$ISST --cpu <F> turbo-freq enable --auto     # re-partitions + wipes configs!
for cpu in 0 24 48 72 96 120; do
  $ISST --cpu $cpu core-power config --clos 0 --weight 0 --min 2700 --max 4400
  $ISST --cpu $cpu core-power config --clos 1 --weight 0 --min 800 --max 3900
  $ISST --cpu $cpu core-power config --clos 2 --weight 0 --min 2000 --max 2000
done
$ISST --cpu 24-143 core-power assoc --clos 1
$ISST --cpu 168-287 core-power assoc --clos 1
$ISST --cpu <F>,<F+144 siblings> core-power assoc --clos 0
$ISST --cpu 0-23 core-power assoc --clos 2
$ISST --cpu 144-167 core-power assoc --clos 2
```
Fast sets used (arbitrary NON-fused app cores, balanced per package):
```
FAST8  = 30,31,58,59       | 82,83,106,107          (4/pkg)
FAST16 = 28-31,58-61       | 82-85,100-103          (8/pkg = TF bucket-0 count)
FAST24 = 26-31,56-61       | 80-85,98-103           (12/pkg)
```

Results (fast / commons / control mean MHz; app aggregate GHz-cores; PkgWatt):

| Phase | fast | commons (pkg0/pkg1) | ctrl | app agg | vs flat | PkgWatt |
|---|---|---|---|---|---|---|
| flat (5.1, pin2g) | — | 3637 / 3260 | 2000 | **409.3** | baseline | 502/502 |
| fast8, ctrl pin2g | pkg0 4100.0x8, pkg1 ~3984x8 | 3642 / 3207 | 2000 | 405.7 | -0.9 % | 500/501 |
| fast8, ctrl min800 | 4100.0 x16 CPUs | ~3700 / ~3200 | 867 | 417.0 | (vs 418.7) -0.4 % | 502/502 |
| fast16, ctrl min800 | 4100x16 + ~3990x16 | ~3700 / ~3100 | 827 | 409.5 | -2.2 % | 502/502 |
| fast24, ctrl min800 | 4100x24 + ~4000x24 | ~3600 / ~3000 | 815 | 408.3 | -2.5 % | 502/502 |
| fast16, commons<=3000 | **4100.0 x32 CPUs exact** | 3000 / 3000 | 2000 | 377.6 | -9.8 % | 488/501 |

(sel values are per-CPU exact; sibling max delta <= 7 MHz everywhere.)

### 5.3 Conclusions for TRON

1. **No combination beats all-app-same-config in aggregate.** The flat config
   IS the aggregate optimum (409.3 GHz-cores with control pinned at 2 GHz);
   every fast-core mix costs 1-10 %. The PCU already spends the entire 500 W
   budget; designating fast cores only moves clock around (and V/f physics
   makes fast cores cost more W per GHz).
2. **If specific threads are worth more, fast8 is nearly free** (-0.9 %):
   4 cores/pkg hold 4000-4100 MHz while commons stay within ~100 MHz of
   their flat values. Per-core gain vs flat neighbors: +~460 MHz on pkg0,
   +~780 MHz on pkg1. Beyond 8 fast cores/pkg the TF bucket drops and the
   aggregate cost grows.
3. **4400 MHz is only grantable when all other cores are at/below the 2700
   LP clip** (sections 2.5/2.6 and every sweep here: fast cores pin at
   exactly 4100 whenever commons run above 2700, even with power headroom —
   H16-low held 4100.0 x32 at 488 W). 4x4.4 + rest@2.7 costs -16 % aggregate.
4. **Package asymmetry is structural**: control plane occupies pkg0 domain 0,
   so pkg0 app cores always run ~350-400 MHz faster than pkg1's at the wall.
   If TRON's data plane wants uniform app-core speed, either accept pkg1's
   number as the SLA (~3.26 GHz), cap pkg0 app cores for symmetry (wastes
   budget), or split the control-plane reservation across both packages
   (topology change).
5. Control-plane power matters: letting control starve (min 800) instead of
   pinning 2000 buys the app cores back ~9 GHz-cores (~+2 %). If TRON's
   control plane tolerates opportunistic throttling under load, use
   min 800 / max 2000 instead of a hard pin.

## 6. End state and recipes

Machine left in the flat_freq_apply state (TF+CP disabled on all 6 domains,
288/288 CPUs in CLOS0) + boot-faithful dormant CLOS2/CLOS3 configs.

- Flat recipe for CI-shaped loads: prefer assoc-only with TF left enabled
  (section 2.3) -> 4100 x80 instead of 3900 x80. Validate against real CI
  (AVX license classes use lower buckets: TF table levels 1-4).
- `flat_freq_apply` sudoers note: its precheck requires NOPASSWD for the
  workspace-path isst binary; only /opt is in sudoers, so it fails from
  non-interactive sessions (interactive use worked via cached sudo).
- Fast-core recipe: section 2.5/2.6 commands; remember --auto's config-wiping
  side effects and the restore block.

## 7. Open items

- Sustained (minutes+) behavior at the hetero operating points (25 s windows
  here; PkgTmp <= 84 C, headroom exists).
- AVX2/AVX512/AMX license classes lower all buckets (only SSE measured).
- P9-style config under 80-CPU-class load (fast cores hot + commons at 3900).
