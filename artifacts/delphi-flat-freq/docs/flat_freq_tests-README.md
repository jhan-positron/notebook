# flat_freq_tests — checkerboard benchmark runs on the delphi hosts

Benchmark series comparing inference performance under different CPU
frequency configurations (Intel SST-CP CLOS shapes) on delphi-3bda and
delphi-3af6 (Xeon 6962P, 288 logical CPUs, 8 FPGAs each). Owner: jhan.

---

## Layout and conventions

```
scripts/                          runner scripts (see each header for usage)
<date>_<shape>[-<host>]_<test>/   one folder per run (UTC dates)
```

Per-run folder contents:

```
sweep_console.log       full run-multi-sweep.sh console output
turbostat_per_cpu.tsv   per-CPU freq/power capture during the run
shape_watch.log         periodic CLOS association probes (later runs)
runner_timeline.txt     start/end timestamps (UTC)
SWEEP_EXIT_CODE         0 = success
sweep-results/          checkerboard tree (metrics.json, summary.log,
                        runtron/log.<n>, consolidated results-v2-*.csv)
```

### Frequency-shape glossary

| Shape label | Meaning | Busy-core result (measured) |
|---|---|---|
| `boot-default-clamped` | BIOS PCT partition: 16 cores/machine in CLOS0, everything else CLOS3 ≤ 2700 | most busy cores exactly 2700 |
| `flat-freq` (v1, used by the 24h sweep) | all 288 → CLOS0, turbo-freq DISABLED | ~3900 shape, run mean 3756 |
| universal flat (v2, `flat_freq_apply`) | all 288 → CLOS0, turbo-freq ENABLED | ~4100 grant, run means 4044–4057 |
| `tron80` / select | TRON app cores (+HT sibs) → CLOS0/TF-on, rest CLOS3 | fast ~4000–4100, rest ≤ 2700 |
| `tron88` | tron80 + the 8 FPGA-driver cores in the fast set | same as tron80 |
| `tier3` (`flat_freq_apply_tiers`) | fast CLOS0 / mid CLOS1 ≤ 3900 / low CLOS3 ≤ 2700 | 4032 / 3899 / idle |
| `tron112` (PR #3070 map) | the PR's 112 phys cores (+sibs) → CLOS0, rest CLOS3 | fast ~4045, drivers 2700 |

All shapes are applied with `flat_freq_utils.sh` (canonical:
`workspace debug_3bda/`, mirrored in the notebook repo) and DO NOT survive
a reboot — the BIOS re-deals the PCT partition at every boot.

### Why "universal flat" numbers differ across this file (3.27 vs 3.76 vs ~4.05 GHz)

Three different things, all real:

1. **All-288-thread synthetic spin** (Jul 2 exploration): package-power-bound
   at ~3.27 GHz × 288T / 502 W per package. No shape can beat power.
2. **24h sweep under v1 flat** (TF disabled): busy mean 3756 — the v1 recipe
   tops out at the 3900 TRL shape.
3. **Ladder phases A/B under v2 flat** (TF enabled): busy means 4044/4057 —
   the TF high-priority grant gives 4100-class to CLOS0 members, and
   checkerboard loads ≤ ~112 of 144 cores, far from the power wall.

---

## How to run these tests manually

From a shell on delphi-3bda or delphi-3af6:

```bash
cd /home/jhan/workspace/run_checkerboard/checkerboard
unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL   # jhan-shell landmine!
export CHECKERBOARD_MEMLOCK_KB=197971044          # host limit < 200GB default

# Single gpt-oss test (~2 min warm, ~10 min after reboot):
./run-multi-sweep.sh \
  --models ingested-gpt-oss-120b-tp4 \
  -p 1024 -g 1024 --shared-system-prompt-lengths 256 -s 0 -u 8

# Full sweeps: see the marked "THE BENCHMARK COMMAND" block in each
# scripts/run_*.sh. The three length lists are ZIPPED by position,
# not cross-multiplied.

# Results: sweeps/multi-sweep-<ts>/<model>/<config>/<inst>-<users>/
# Consolidated CSV: ./post-processing/export_to_spreadsheet.py sweeps/multi-sweep-<ts>
```

Before benchmarking after ANY reboot:

1. Frequency shape:
   ```bash
   source ~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
   flat_freq_apply                                   # universal flat, or:
   flat_freq_apply "27-46,51-70,75-94,99-118"        # tron80 select, or:
   flat_freq_apply_tiers "<fast>" "<mid>"            # 3-tier
   ```
2. FPGAs healthy: all 8 of `/sys/bus/pci/devices/0000:{10,13,38,3b,90,93,b9,bc}:00.0/resource`
   must have 3 non-zero BAR lines; validate with `pho test cards dma readback --bdf all`.
3. Machine idle: no runtron/rinzler; stale `/dev/hugepages/*slice*` files owned
   by OTHERS must be checked with `fuser` before removal; your own are reused.

Wrappers with monitoring (recommended) live in `scripts/` — all scrub the
env landmine, capture turbostat, and produce self-contained run folders.

---

## Run log (chronological)

### 2026-06-30 — clamped baseline (Hannah)

`2026-06-30_boot-default-clamped_gpt-oss-single/` — reference run, tron
branch `hrv-intel-speed-select-crosscheck-measure` (66deff22), boot-default
clamp: parse 551.5 tok/s, generate 90.6, TTFT 2.32 s, TTLT 13.61 s;
turbostat ~89% of busy samples at 2.6–2.7 GHz. (Her full 188-config sweep
`multi-sweep-20260630-030357` on 3bda later serves as the clamped baseline
for grid comparisons.) NOTE: the thread-placement capture in this folder
recorded only its own monitor loop — no runtron data.

### 2026-07-02 — two failed attempts + host fault

- `..._attempt1-FAILED/` — both instances inherited
  `SYSTEM_CONFIG="--instance 1,2"` from `~/jibin.bashrc.positron.dev`
  → hugepage lock collision + init crash. Runners now unset
  `SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL`.
- `..._attempt2-FAILED-fpga-bars/` — **host fault**: 3bda booted 05:08 with
  6/8 FPGAs unprogrammed (BittWare bootloader `12ba:0076`, one 256 MB BAR);
  BIOS shrink-wrapped their PCIe stack windows; post-boot flashing could
  never get the real 4M+1G+128G BARs assigned (Linux cannot grow firmware
  decode windows). Every BAR2-touching process segfaulted at offset
  0x200010 — 130 kernel-logged crashes incl. all daytime CI.
- **Fix recipe** (evening, jointly with jhan): `pho bw images use -c
  {0,1,4,5,6,7} archer_agm_01.05.08.00.rbf` (over USB/BMC) → warm reboot
  WITH images resident → BIOS sizes all stack windows → 8/8 full BARs →
  `pho test cards dma readback` PASS 8/8.

### 2026-07-02 — SST frequency-exploration work stream (parallel session)

Artifacts under `W = workspace debug_3bda/`; main report
`W/ALLCORE_CEILING_HETERO_CLAUDE_20260702.md` (repro blocks per phase).

- **All-core ceiling**: full-machine load is RAPL-bound (~3.27 GHz × 288T,
  ~3.6 × 144T, 502 W/pkg) in every config. HT sibling pairs equal ≤ 7 MHz.
- **Key recipe delta**: TF ENABLED + assoc-only → **4100.0 × 80** on the
  checkerboard shape vs 3900 with the disable recipe (+200 MHz).
  `turbo-freq enable --auto` puts arbitrary cores at 4400 but clips all
  else to 2700. Landmine: `core-power enable` silently resets CLOS2/3.
- **E1/E2** (`W/e1e2_beat80_.../`): generator config verbatim → 4100.0×80
  exact; the "4400 requires all others ≤2700" rule survived direct
  falsification with ~50 W/pkg unused → all-80@4100 is the runtime-SST
  aggregate optimum. No 4200 rung exists.
- **TRON scenario**: control-plane pinning needs CLOS min=max (min=800
  starves to 0.8 GHz); app-core ceiling package-asymmetric under full load.
- **Tooling**: `flat_freq_utils.sh` (patched → later v2/v3) and
  `gen_tron_flatfreq.py` (parses tron resource-map.yaml → exact isst
  sequence; `--also-boost dev,rinzler,platform`; `--revert`).

### 2026-07-03 — clean flat-freq single run

`2026-07-03_flat-freq_gpt-oss-single/` (v1 flat shape, busy ~3.9 GHz):

| Metric | Clamped baseline | Flat | Delta |
|---|---|---|---|
| Parse | 551.5 | 644.7 | **+16.9%** |
| Generate | 90.6 | 102.6 | **+13.3%** |
| TTFT | 2.32 s | 1.99 s | −14.5% |
| TTLT | 13.61 s | 11.94 s | −12.2% |

### 2026-07-03 → 05 — "24-hour" multi-model sweep (flat v1, 3bda)

`2026-07-03_flat-freq_24h-sweep/` — 49 h 57 m (11 model×TP configs; the
"24h" name is a misnomer at these lengths). 483 configs with metrics
(56 auto-skipped where users < instances); exactly **1 failure**
(3b-tp1/p1024/8-inst: teardown segfault after a completed iteration — tron
shutdown bug). Shape held: 300/300 CLOS probes, 531k busy samples mean
3756 MHz, 0.00% clamp band. Model substitution: llama-3.1-70b for Hannah's
llama-3.3-70b (absent from tron main).
CSV: `sweep-results/results-v2-multi-model-20260703-005629.csv`.

### 2026-07-05 — flat vs clamped (the headline grid comparison)

151 paired configs vs Hannah's clamped baseline (same host; tron versions
differ). Flat wins nearly every config:

| Model | Parse | Generate | TTFT | TTLT | cfgs |
|---|---|---|---|---|---|
| gpt-oss-120b tp4 | +12.6% | +9.9% | 11.1% fst | 9.4% fst | 20 |
| llama-8b-good tp4 | +12.2% | +8.4% | 11.2% fst | 8.2% fst | 20 |
| llama-8b-good tp2 | +11.4% | +6.7% | 9.9% fst | 6.8% fst | 16 |
| llama-3b-fast tp4 | +13.9% | +7.6% | 11.9% fst | 7.8% fst | 20 |
| llama-3b-fast tp2 | +16.8% | +7.3% | 13.3% fst | 7.7% fst | 16 |
| llama-3b-fast tp1 | +13.0% | +5.9% | 11.7% fst | 6.4% fst | 11 |
| mixtral tp4 | +7.5% | +4.4% | 7.0% fst | 4.8% fst | 20 |
| mixtral tp2 | +6.3% | +3.2% | 6.0% fst | 3.5% fst | 16 |
| mixtral tp1 | +4.3% | +3.4% | 4.1% fst | 3.5% fst | 12 |

Gaps: no clamped baseline for 70B (hers is 3.3, ours 3.1); baseline has
fewer user counts. Older baselines: `multi-sweep-20260603/04`; Talos
MongoDB holds nightly CI history.

### 2026-07-05 — TRON-80 run (3af6) vs universal flat

`2026-07-05_tron80-4100-3af6_gpt-oss-3b-matrix/` — 6 h 35 m, 98 configs,
0 failures; TRON cores 56k busy samples mean 3977, none clamped.

- gpt-oss-tp4 (49 cfg): parse **+2.9%** (46/49), generate +1.0%, TTFT 2.9% fst.
- 3b-fast-tp4 (49 cfg): parse +2.7% but generate **−0.8%** (11/49) — the
  strict-80 shape clips the FPGA-driver cores to 2700; small-model
  generation feels it (the PLAN_E5 "V2 risk", confirmed).

Cross-host caveat (3af6 vs 3bda) later bounded at ~0.5% by the tron88 run.

### 2026-07-05 — TRON-88 baseline round (3bda, 55 min)

`2026-07-05_tron88-4100-3bda_baseline-matrix/` — 56 configs, 0 failures;
shape = tron80 + driver cores (`25-46,49-70,73-94,97-118` +sibs); fast-set
busy mean 4042, none clamped.

| Comparison | Result |
|---|---|
| (a) vs clamped (same host) | gpt-oss +14.6/+10.9 (20/20); 8b-tp4 +13.7/+9.9; 8b-tp2 +12.9/+7.6 |
| (b) vs universal flat (same host) | +0.9 to +1.8% everywhere — first same-host select-beats-flat confirmation |
| (c) vs strict tron80 (3af6) | ~0% ± 0.4 for gpt-oss — driver boost neutral; also pins host variance at ~0.5% |

### 2026-07-06 — 3-tier round (3bda, 55 min)

`2026-07-06_tier3-4100-3900-3bda_baseline-matrix/` — 56 configs, 0
failures. Shape via `flat_freq_apply_tiers` (v3): fast = app cores
(CLOS0/TF-on), mid = TRON-aux `0,24-26,48-50,72-74,96-98`+sibs (CLOS1
≤ 3900), low = rest (≤ 2700). (4.2 GHz tier-1 was requested but is not
grantable: TF gives 4100 when any core > 2700; no 4200 rung.)

Realized: tier1 mean 4032 (68% in 4000–4099); tier2 mean 3899 hard-pinned
3888–3900 (TX/RX driver threads genuinely busy — first shape where they
show up); tier3 zero busy samples.

Results: vs clamped ≈ identical to tron88; **vs tron88: 0.0 ± 0.4%** —
lifting aux cores 2700→3900 buys nothing for these models. The app-worker
4100 tier is the only lever that matters.

### 2026-07-09 — PR #3070 A/B/C ladder (3af6): software vs shape decomposed

tron PR #3070 (https://github.com/positron-ai/tron/pull/3070, head
`66b66350`, branch "gr-6962p-tuning") replaces the core map:
14 phys cores/slice (2 die-A addressed via HT-sibling IDs + 6 die-B +
6 die-C), 112 phys cores total vs 80, main thread deliberately lands on
die B. Testing it requires the PR *binary* (19 files incl. rinzler.cpp) —
built from `pull/3070/head`, published to `/scratch/jhan/tron-pr3070`.
Shape list validated two independent ways — exact invocations (run on
both hosts; outputs shown are what each printed):

```bash
# 1. Generator: parse the PR's resource map (extracted from pull/3070/head)
git -C /tmp/jhan-tron3070 show pr3070:config/resource-map.yaml > /tmp/jhan-rm-pr3070.yaml
python3 /home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/gen_tron_flatfreq.py \
    /tmp/jhan-rm-pr3070.yaml --section granite_rapids_6962p
#  -> boost set: 7-14,24-71,79-86,96-143,151-158,168-215,223-230,240-287 (224 CPUs)
#  -> slow set:  0-6,15-23,72-78,87-95,144-150,159-167,216-222,231-239   (64 CPUs)

# 2. Apply with the MANUALLY derived argument (union of the 8 slice lists,
#    sibling IDs 151-158/223-230 folded to physical cores 7-14/79-86):
source /home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
flat_freq_apply 7-14,24-71,79-86,96-143
#  -> high (CLOS0, 2700-4400): 7-14 24-71 79-86 96-143 151-158 168-215 223-230 240-287
#  -> low  (CLOS3, <=2700):    0-6 15-23 72-78 87-95 144-150 159-167 216-222 231-239
#  -> turbo-freq enabled; configs pinned; assoc: clos0=224 clos3=64
```

VALIDATION RESULT: the apply expansion is byte-identical to the generator's
boost/slow sets in both directions. Phase C's runner
(`scripts/run_pr3070_ladder_BC_3af6.sh`) invokes exactly this
`flat_freq_apply 7-14,24-71,79-86,96-143`; phases A/B invoke
`flat_freq_apply` with no arguments (universal flat).

Phases (each 56 configs, 0 failures, 0 shape deviations; new-map pinning
verified in logs — `App CPU list: 223-224,96-101,...`):

| Phase | runtron | Shape | Busy mean |
|---|---|---|---|
| A `2026-07-09_ladderA-flat4100-main-3af6_baseline-matrix` | main ae82870ae | universal flat | 4044 |
| B `2026-07-09_ladderB-flat4100-pr3070-3af6_baseline-matrix` | PR 66b66350 | universal flat | 4057 |
| C `2026-07-09_ladderC-tron112-pr3070-3af6_baseline-matrix` | PR 66b66350 | tron112 select | fast 4045 / drivers 2695 |

Realized frequency distributions (busy > 50% samples, each phase bounded
to its own snapshot window). IMPORTANT: compare like-for-like — under
universal flat the TX/RX driver and OS threads are also CLOS0 and, being
lightly threaded (one sibling per core), they earn the 4100+ grants; a
naive "all busy" column therefore looks faster than a workers-only column.
Worker cores themselves never sustain 4100: both HT siblings loaded costs
~50 MHz in every shape.

| Band (MHz) | A all busy | B all busy | B workers only | C workers (fast set) | B non-workers |
|---|---|---|---|---|---|
| 3800–3899 | 4.0% | — | — | 1.2% | — |
| 3900–3999 | 22.3% | 18.5% | 21.3% | 28.6% | 0.2% |
| 4000–4099 | 60.2% | 69.4% | 74.7% | 66.1% | 34.3% |
| 4100–4199 | 12.3% | 10.4% | 2.1% | 2.1% | 65.4% |
| 4200+ | 1.2% | 1.6% | 1.9% | 1.9% | — |
| n / mean | 4806 / 4044 | 6910 / 4057 | 6010 / 4052 | 6378 / 4045 | 900 / 4088 |

Workers B vs C: 4052 vs 4045 — identical within noise; the frequency shape
did not change worker-core behavior between flat and select (as intended).
C additionally has the new map's TX/RX driver cores busy in the SLOW set:
n=976, mean 2695 — pinned at their cap, doing real work. The 4200+ samples
everywhere are light-load moments between configs where few busy cores
earn higher grants.

Decomposition (per-config geomeans, win counts):

| Ratio | gpt-oss-120b tp4 | llama-8b tp4 | llama-8b tp2 |
|---|---|---|---|
| **B/A — software effect** (flat both sides) | parse **+9.3%** (19/20), gen +3.4% (14/20), TTLT 4.1% fst | parse +3.6%, gen −0.1% | parse −5.8% (4/16), gen **−18.1%** (1/16), TTLT −19.6% |
| **C/B — shape effect** (PR both sides) | ~0 (+0.3%) | parse −1.8%, gen −0.5% | parse +0.2%, gen −1.3% |
| **C/A — combined** | parse +9.6% (20/20), gen +3.8% | parse +1.8%, gen −0.5% | parse −5.6%, gen −19.2% |

Sanity: A vs tron80-3af6 (gpt-oss, main binary, flat vs old select):
±0.5% — measurement stable across days.

**C vs the 2026-07-06 tier3 round** (new-map select on 3af6 vs old-map
3-tier on 3bda — i.e., "new world vs best old world", cross-host):

| Model | Parse | Generate | TTFT | TTLT |
|---|---|---|---|---|
| gpt-oss-120b tp4 | **+10.0%** (20/20) | +3.9% (16/20) | 8.8% fst | 4.6% fst |
| llama-8b tp4 | +2.6% (11/20) | −2.2% (7/20) | 2.7% fst | −1.8% |
| llama-8b tp2 | −5.6% (5/16) | **−19.6%** (1/16) | −4.5% | −21.3% |

Frequency comparison C vs tier3: fast tiers essentially identical
(4045 vs 4032, both ~66–68% in the 4000–4099 band); the difference is the
aux/driver cores — tier3 ran them at 3899 (CLOS1), C clips them at 2695.
Given C/B ≈ 0, that difference again doesn't move tokens/s for these
models — the perf deltas above are the PR's software/placement change.

**C vs the CLAMPED bootup baseline (directly measured — the full stack:
frequency fix × PR-3070 software):**

| Model | Parse | Generate | TTFT | TTLT |
|---|---|---|---|---|
| gpt-oss-120b tp4 | **+26.0%** (20/20) | **+15.1%** (20/20) | 20.6% fst | 14.4% fst |
| llama-8b tp4 | +16.7% (16/20) | +8.6% (18/20) | 14.5% fst | 8.6% fst |
| llama-8b tp2 | +6.5% (7/16) | **−13.5%** (3/16) | 7.2% fst | −11.9% |

The effects compose multiplicatively: e.g. gpt-oss parse 1.146 (freq fix)
× 1.100 (PR software) = 1.261 ≈ the measured +26.0%. Note the split when
citing these numbers: ~+14.6% ships with the frequency configuration alone
(deployable today, see positron-infrastructure PR #165,
https://github.com/positron-ai/positron-infrastructure/pull/165); the
additional ~+10% requires the PR-3070 tron change to merge. And for
8b-tp2 the PR regression more than cancels the frequency gain — its
generate is NET NEGATIVE vs the untouched bootup config.

**Takeaways for PR #3070 review:**

1. New map is a clear win for gpt-oss-120b-tp4 (+9–10%, prefill/parse most,
   consistent with the die-A prefill design) and mildly good for 8b-tp4.
2. **8b TP2 regresses ~18–20% on generation** — the 4-instance/2-slice
   topology under the new map needs attention before merge.
3. Frequency-shape choice (flat vs select) remains a wash; the software/
   placement change is what matters. Universal flat + new map captures
   nearly the whole win.

Measurement notes: first B/C attempt failed instantly — the PR runtron's
RPATH pointed into the 3bda-local build tree (`libversion.so` not found on
3af6); fixed with `LD_LIBRARY_PATH` into the `/scratch` copy. Lesson:
smoke-test on the TARGET host. Also: runner `kill` cannot reap root
turbostat children → orphan turbostats accumulate (19 on 3af6, needs
`sudo pkill turbostat`; 3bda similar) and per-phase turbostat files get
contaminated by successor phases — all analyses above are bounded to each
phase's own snapshot window.

### 2026-07-11 — Nightly-CI reality check: the @8u TPS metric is frequency-insensitive

Question raised: 3bda's first clean TPS nightly (2026-07-10, under the
deployed strict tron80 shape from positron-infrastructure PR #165,
https://github.com/positron-ai/positron-infrastructure/pull/165) showed
gpt-oss decode 93.28 / prefill ~799 — "no flat-freq improvement".

Evidence gathered from #ci-cd-notifications nightly history:

| Night | Host | Shape | tron | gpt-oss decode/user | prefill~ |
|---|---|---|---|---|---|
| Jul 4 | 17cf | clamped | 07.04 | 99.03 | 804 |
| Jul 6 | 17cf | clamped | 198650bf | 98.09 | 801 |
| Jul 7 | 17cf | clamped | 198650bf | 98.02 | 803 |
| Jul 8 | 17cf | clamped | 198650bf | 97.52 | 801 |
| Jul 10 | 17cf | clamped | ef720667 | 93.39 (host SICK: hugepage bug platformd#413, all models down) | 797 |
| Jul 10 | 3bda | tron80 boosted | ef720667 | 93.28 (all OTHER models healthy) | 799 |

Findings:
1. 3bda had NO earlier TPS nightlies (June reports were MMLU-only; Jul 9
   run crashed via tron#3097) — so there is no same-machine clamped
   baseline; the "no improvement" impression came from comparing to 17cf.
2. Boosted 3bda == clamped-healthy 17cf on EVERY other model within noise
   (3b 191.6 vs 191-193; 8b-tp2 194.4 vs 190-196; 70b rows equal; mixtral
   80.8 vs 80-82; qwen, gemma equal). CONCLUSION: the nightly @8u decode
   metric is FPGA-pipeline-bound and essentially insensitive to CPU
   frequency shape. The flat-freq win lives in CPU-saturated regimes
   (concurrent prefill storms, high user counts — what checkerboard
   measures); this benchmark does not exercise them.
3. Client-side prefill~ (prompt/TTFT at 1k) is ~800 in every era and both
   shapes — the single-stream prefill pipeline ceiling. It is NOT
   comparable to checkerboard's parse metric (which saturates workers with
   4 simultaneous prefills per instance and IS frequency-sensitive:
   551 clamped -> 645+ unclamped).
4. Real anomaly worth flagging: gpt-oss decode dropped ~5% on BOTH DUTs on
   Jul 10 (97.5-99 -> 93.3) coinciding with tron v2026.07.10-ef720667 —
   likely a tron regression, not the frequency shape (identical dip on the
   shape-less 17cf). Watch the next nights: if a healthy 17cf recovers to
   ~98 while 3bda stays ~93 on the same tron, revisit the shape hypothesis
   (strict shape clamps rinzler+driver cores on the production path).

### 2026-07-11 — RCA consensus (Claude + gpt-5.6-sol via PAL): why the nightly shows no uplift

Four-round consensus dialogue (PAL MCP on andoria-11, model gpt-5.6-sol),
with live read-only evidence fetched between rounds. Verdict: consensus
reached.

Decisive live evidence (captured DURING a nightly decode phase on 3bda):
- TX driver threads: 99.9% CPU at exactly 2700 MHz (cores 49/50) —
  saturated AND clamped under the deployed strict-tron80 shape.
- Main rinzler serving thread: 80.3% CPU on clamped core 48.
- The production engine is rinzler itself (cmdline: rinzler --model ...
  --app-cores ... --dev-cores ...); app threads correctly on boosted
  cores (e.g. 3937 MHz @ 99.8% busy); serving/driver threads on the slow
  set. Checkerboard bypasses this path entirely.
- Boot-service shape provenance: applied once at boot Jul 9 15:28:48,
  zero CLOS writes since, readback matches config (shape-inactive
  hypothesis closed).
- Speculation setting: /etc/rinzler/instance-N.env, platformd-owned 600 —
  unread; GATING provenance item before cross-era comparisons are final.

Consensus RCA — two SEPARATE questions (amended 2026-07-11 after user
challenge; supersedes earlier wording that overweighted the serving-path
clamp):

Q1: Why doesn't the nightly @8u decode metric show the worker boost?
  - Leading: the metric is largely CPU-frequency-insensitive at this load
    — per-token latency is dominated by FPGA round-trip + waits, not CPU
    clock. Evidence: 3bda-boosted == 17cf-clamped within noise on every
    other model; prefill~ constant ~800 across all eras and shapes.
  - FALSIFIABLE PREDICTION (2026-07-11, tested by plan item 6b): if the
    leading hypothesis is right, the tron worker cores during a nightly
    gpt-oss phase will NOT be doing full-load work the way they were in
    our checkerboard runs — they will spend a larger share of each token
    interval waiting, because in the nightly the work arrives through the
    rinzler serving path (client -> Caddy -> rinzler engine) at @8u pacing
    instead of checkerboard's direct saturating drive. If 6b instead shows
    workers compute-busy like checkerboard, the leading hypothesis is
    wrong and the build-regression track (Q2) has to carry the whole gap.
    Measurement caveat: "waiting" will NOT reliably show as low Busy% —
    tron's poll/wait infra makes waiting threads read as busy to
    /proc and turbostat (TX: 99.9% CPU with voluntary_ctxt_switches=1).
    The discriminating signals in the 6b capture are the perfetto sched
    trace (real running vs runnable vs sleep per worker thread, per-token
    gaps) and per-engine IPC from perf stat (spin/wait loops burn cycles
    at low instructions-per-cycle vs matmul-feeding work), compared
    against the same signals during a checkerboard run at the same shape.
  - DOWNGRADED (was "RCA(i)"): "clamped serving path caps decode". TX
    threads DO read 99.9% CPU at 2700 and rinzler-main 80% — but that is
    wait-OCCUPANCY, not starved compute: TX shows
    voluntary_ctxt_switches=1 (pure poll loop; tron ships mwaitx wait
    infra), the perfetto thread study found app workers busiest with
    main/TX/RX mostly idle in work terms, and our own checkerboard A/Bs
    (tron88 vs tron80 = 0.0+-0.4%; ladder C/B ~ 0 for gpt-oss) directly
    measured driver-clamping as a non-effect. The one-night aux-boost A/B
    (plan item 6) remains a cheap discriminator but with LOW expected
    effect.
  - Open decomposition: checkerboard decode gained +13% clamped->flat on
    workers, so full CPU-insensitivity cannot be assumed for the nightly
    either. 93.28 = (17cf-era ~98) x (build delta) x (worker-freq delta):
    one equation, two unknowns until the next healthy same-build
    nightlies land on both hosts.

Q2: Why is 3bda's 93.28 below 17cf's 97.5-99 era? Leading: tron build
    ef720667 (both DUTs read ~93.3 on it; older builds on 17cf read ~98;
    the shape cannot explain it — 3bda-tron80 dominates 17cf-clamped on
    every core). Confirm via next healthy same-build nightlies + a
    198650bf..ef720667 diff review.

Closed branches: shape-not-active (boot-service provenance + readback);
host variance as main effect (cross-model equality within noise).

Consensus plan (priority order):
1. Preserve Jul-10 + current nightly artifacts/configs.
2. Same-build cross-host comparison from the next healthy nightlies
   (both DUTs now on ef720667+): healthy 17cf at ~93 confirms the build
   regression independent of shape.
3. Verify harness/model/speculation config equivalence across eras
   (spec setting location known, needs platformd/root read).
4. If reproduced: bisect 198650bf..ef720667 (decode/scheduler/gpt-oss
   paths) and open a tron issue with raw evidence.
5. Measure aux pressure during the gpt-oss phase specifically (tp4).
6. Paired one-night A/B on 3bda: strict tron80 vs tron80+aux
   (dev,rinzler,platform), pre-run isst readback + placement capture,
   identical build/model/spec; phase-specific TPS + TX/rinzler CPU+freq.
   EXPECTED RESULT (post-amendment): little to no change — checkerboard
   driver A/Bs and the TX spin-wait signature predict aux frequency is
   immaterial; run it once as a cheap discriminator, not as the fix.
   2026-07-11 refinement: the RINZLER cores are the interesting part of
   "aux" — see "Rinzler-core frequency facts" below. Each active engine
   instance runs a near-saturated work_queue thread clamped at 2700, no
   checkerboard A/B has ever exercised rinzler-core frequency (checkerboard
   never spawns rinzler), and the boot-default config even had one fast
   rinzler core (72) that the deployed tron80 shape demoted to 2700.
   Read the 6b perfetto/IPC verdict on that thread before spending a
   nightly on this A/B.
6b. Workload-shape profiling during a FULL CI/nightly run on 3bda
   (cannot be done now — needs an approved window + root): run perfetto
   (tron has in-process tracing) and/or perf (perf_event_paranoid=4
   currently blocks unprivileged use) across a complete gpt-oss phase.
   Capture per-thread time breakdown — real work vs wait — for app
   workers, TX/RX drivers, and rinzler-main, plus per-token timeline.
   This answers the open question the frequency A/Bs cannot: whether the
   serving path gates worker throughput in FREQUENCY-INDEPENDENT ways
   (scheduling, token pacing, batching waits), i.e. where per-token time
   actually goes at @8u, and why worker MHz does not reach the client
   metric.
   Success criterion: this directly tests the FALSIFIABLE PREDICTION under
   Q1 above — workers waiting-dominated per token at @8u through rinzler
   (leading hypothesis holds) vs compute-busy like checkerboard (hypothesis
   falsified; build regression must carry the gap). For the comparison
   side, capture the same perfetto/perf signals during a checkerboard run
   at the same shape (allowed on 3af6 any time; on 3bda only in a window).
   TOOLING STAGED 2026-07-10 (capture only needs the window now, ~2 min):
   - installed (no root, user-space): /scratch/jhan/tools/tracebox and
     /scratch/jhan/tools/trace_processor (perfetto v57.2, prebuilts cached);
     perf 6.8.12 + bpftrace were already present.
   - capture script: /scratch/jhan/flat_freq_tests/scripts/ci_workload_profile.sh
     (+ /scratch/jhan/tools/ci_profile_trace.cfg). Observational only —
     refuses to run unless engine processes are already up; gates on the
     gpt-oss phase by default (--model/--any). Running perf as root
     bypasses perf_event_paranoid=4, so NO sysctl change is needed.
   - preflight verified on live 3bda engines: --check --any -> PREFLIGHT OK.
   - window-time procedure: wait for the nightly's gpt-oss phase, then
       sudo -v && /scratch/jhan/flat_freq_tests/scripts/ci_workload_profile.sh
     Output lands in /scratch/jhan/flat_freq_tests/<ts>_ci-workload-profile-3bda/
     (perfetto .pftrace, perf.data, per-engine IPC, before/after thread +
     ctxt-switch snapshots, turbostat, isst shape). Analyze on-host with
     /scratch/jhan/tools/trace_processor or upload the .pftrace to
     https://ui.perfetto.dev.
7. Ansible role change is CONDITIONAL on 6 (sol's amendment): do not
   deploy universal flat "regardless"; verify range semantics first.
8. Add provenance to nightly reports: shape readback, build, model config,
   spec mode, thread-placement summary.
9. Longer term: CPU-saturating nightly test with server-side prefill
   metrics separated from client TTFT.

### 2026-07-11 — Rinzler-core frequency facts (the "boost rinzler cores" idea)

Questions answered here: how fast do the rinzler cores run under (a) last
night's deployed shape and (b) the clamped/boot-default config, and (c)
what occupies the fast cores under the clamped config? All 3bda numbers
verified live 2026-07-11 by isst get-assoc readback + a turbostat sample
while production engines were serving llama-3.3-70b-instruct-good-tp4
(2 rinzler instances).

How many rinzler cores: 4 physical — Linux CPUs 24, 48, 72, 96 — plus HT
siblings 168, 192, 216, 240 = 8 logical CPUs (resource-map
granite_rapids_6962p rinzler_cores). Live placement: each active engine
instance occupies ONE rinzler physical core — rinzler-main on one HT
thread (~14% CPU) and a hot work_queue thread on the other (~87% CPU;
the busiest serving-path thread observed). tp4 models run 2 instances;
today they landed on cores 24 and 96 (NOT sequential 24,48 — assignment
varies), leaving core 72 idle.

(a) Last night on 3bda (deployed strict tron80, PR#165 boot service):
ALL 4 rinzler cores + siblings are CLOS3 -> clipped at 2700 MHz.
Verified: get-assoc reads clos:3 on 24/48/72/96/216; turbostat shows the
busy rinzler CPUs pinned exactly at the clip (CPU 96: 99.8% busy at
2700 MHz; CPU 168: 73% at 2699) while an idle-ish worker CPU floats at
3400+.

(b) Clamped / boot-default config: the fast set is FIXED BY THE BIOS PCT
partition, not by software role — 16 physical cores 0,1,18,19,36,37,54,55
(pkg0) + 72,73,90,91,108,109,126,127 (pkg1), plus HT siblings, in CLOS0
(2700-4400 window, TF on); everything else CLOS3 <=2700. Therefore at
clamped config:
- rinzler cores 24, 48, 96 -> 2700 clip (same as under the deployed shape);
- rinzler core 72 (+ sibling 216) -> FAST, 4400-capable. The 4400-rung
  condition (all other cores <=2700) is exactly satisfied at boot default,
  so it realizes ~4300-4400 when busy.
So the clamped config had ONE fast rinzler core, and deploying tron80
DEMOTED it to 2700. Whether that demotion ever touched an active instance
depends on where the instances land (today 72 was idle at 2 instances);
with 4-instance (tp2) or 8-instance (tp1) models core 72 is always
active. (17cf presumed to have the identical partition — same SKU, same
fused PCT pairs — but we have never read 17cf's registers directly.)

(c) What software runs on the boot-default fast cores (PCT set crossed
with the production role map):
- 0 (+144): platform cores — platformd, unpinned OS/housekeeping.
- 72 (+216): rinzler core — rinzler-main + work_queue when in use.
- 73 (+217): dev core — the TX driver thread of one FPGA (its RX on 217).
- 1, 18, 19, 36, 37, 54, 55, 90, 91, 108, 109, 126, 127 (+siblings): no
  pinned tron threads — OS pool (Caddy, talos, kernel threads), mostly
  idle, bursting toward 4400.
i.e. at clamped config NONE of the 80 workers, 7 of 8 dev cores, and 3 of
4 rinzler cores are fast; the boot fast set mostly hosts near-idle OS
cores, plus one rinzler core and one TX core by coincidence of the PCT
layout.

Why "boost rinzler cores" is genuinely UNTESTED: checkerboard drives
runtron directly and never spawns rinzler, so none of our checkerboard
A/Bs (flat-vs-select, tron88-vs-tron80, the PR-3070 ladder) ever exercised
rinzler-core frequency — those cores sat idle in every run. Only a
production-path (nightly) A/B can test it. It is cheap to configure:
assoc CPUs 24,48,72,96,168,192,216,240 into CLOS0 — e.g.
flat_freq_apply with the worker list + rinzler cores, or
gen_tron_flatfreq.py --also-boost rinzler — and the 4-core addition is
expected to keep the ~4100-class grant (the 88-core tron88 set held
4100). A manual assoc persists until reboot (the PR#165 boot service
re-applies strict tron80 only at boot). This is plan item 6, now with the
rinzler work_queue thread as the primary suspect to watch: it is the one
serving-path thread that is BOTH near-saturated and clamped. Caveat
unchanged: ~87-100% occupancy may be poll-wait rather than starved
compute (the TX lesson — 99.9% CPU, voluntary_ctxt_switches=1, no real
work); the 6b perfetto sched + per-thread IPC capture on this exact
thread decides which, and should be read before spending a nightly on
the A/B.

### 2026-07-12 — 2nd nightly on deployed tron80: build regression confirmed on GNR

Nightly reports (#ci-cd-notifications, all on tron v2026.07.10-ef720667
unless noted). gpt-oss-120b-tp4 @8u decode TPS:

  host / shape                     Jul 07   Jul 08   Jul 10   Jul 11
  17cf clamped, 198650bf            98.02    97.52      -        -
  17cf clamped, ef720667              -        -      93.39    88.24
  3bda tron80-boosted, ef720667       -        -      93.28    94.18
  andoria (Genoa), 198650bf        114.90   115.49      -        -
  andoria (Genoa), ef720667           -        -     115.44   115.52

Findings:
1. BUILD REGRESSION CONFIRMED, GNR-ONLY: 17cf, same host and same clamped
   shape, dropped 97.52 -> 93.39 (-4.2%) exactly when the build moved
   198650bf -> ef720667; Genoa is flat across the same transition
   (115.49 -> 115.44). This substantially answers plan item 2 and
   justifies item 4 (bisect 198650bf..ef720667, GNR-specific paths).
2. 17cf IS ALSO SICK AS A HOST: on Jul 10/11 several tp2 models read far
   below goal (3B @32u: 64% then 32%; mixtral 51% then 71%; gemma 88%)
   while 3bda passes the same models on the same build — so 17cf's 88.24
   (Jul 11) overstates the regression; the clean signal is the Jul 8 ->
   Jul 10 drop. 17cf needs host attention before it is a valid comparator
   (functional also 172/173 both nights).
3. Same-build cross-host: 3bda-boosted beat or matched 17cf-clamped on
   EVERY model both nights (gpt-oss: +0% Jul 10, +6.7% Jul 11 with the
   17cf-health confound). No evidence the boost hurts; still no clean
   evidence it helps at @8u.
4. Decomposition (Q1/Q2): 93.28 ~= 97.8 x 0.955 — the ef720667 build cost
   (~-4.5% from 17cf's clean pair) fully accounts for 3bda sitting at ~93
   instead of the 17cf-era ~98. Both leading hypotheses strengthened:
   Q2 = build regression is real; Q1 = the @8u metric shows ~no worker-
   frequency effect (boost contribution ~= 0 within night-to-night noise).
5. 3bda itself: 93.28 -> 94.18 (+1.0%), functional 172/173 -> 173/173.
   Two consecutive clean nights on the deployed strict tron80 = the
   baseline pair for the planned rinzler-boost nightly A/B (item 6).
6. Context from the Jul-9 report (Rhys): that night's failures on both
   delphi DUTs were rinzler hugepage mmap crash loops -
   https://github.com/positron-ai/tron/issues/3097, fix up at
   https://github.com/positron-ai/tron/pull/3148 - the same file family
   as the leftovers cleaned below.

### 2026-07-11 — daytime window on 3bda: state findings + staged tests

Machine check at 15:16 UTC (post-nightly): nobody logged in, zero
rinzler/runtron processes (engines idle out after CI), platformd active.
Two window-relevant discoveries:

1. LEFTOVER HUGEPAGE FILES BLOCK ANY DUT-SIDE BENCHMARK: last night's
   engines left /dev/hugepages/slice-{0..7}-of-8 (positron-owned,
   verified unmapped via fuser + /proc scan) holding ALL 512 x 1 GiB
   hugepages. With user approval, deleted them one-at-a-time with
   verification (first delete freed exactly 64 pages -> unmapped
   confirmed; final state 512/512 free). Same cleanup precedent:
   2026-07-02 (stale libpos-slice files). Related bug: tron#3097.
2. 3bda IS IN ITS DAYTIME-CI ROLE: per llm-toolbox
   key-resources/ci-runners-cheatsheet.md, 3bda is a split runner —
   ci-runner-start@ timer starts the GitHub Actions runner at 14:00 UTC
   (PR benchmark jobs; one was observed executing at 15:45 UTC), and
   ci-runner-stop@ stops it at 02:45 UTC for the talos nightly. So
   "machine looks idle" mid-day is FALSE availability: a GH job can land
   any moment. Official handover for a manual window:
   sudo /opt/positron/ci/ci-runner.sh stop|start|status.
   CONSEQUENCE: the staged checkerboard window round was NOT launched
   (would race GH jobs, and the frequency shape must stay standard while
   PR benchmarks can run). Scripts staged for a future proper window:
   scripts/run_window_round_3bda.sh (baseline-matched grid under the
   deployed shape, verify-only, instrumented) and
   scripts/yield_monitor_3bda.sh (auto-yield guard: non-jhan login,
   rinzler/talos/foreign-runtron, deadline; TODO add Runner.Worker
   trigger).

### 2026-07-12 — Hannah's 3bd6 validation run: tron112 service deployed, ladder composite reproduced

Hannah's checkerboard run (no rinzler):
/scratch/hvaneenoo/results-v2-multi-model-20260711-220227.csv — System =
delphi-3bd6 (NOT 3af6/3bda; the file merely lives on shared /scratch),
tron main v2026.07.11-29924aa8, 188 configs, 6 models x tp1/2/4, started
22:02 UTC 2026-07-11.

SHAPE VERIFIED — BUT IT IS tron112 (PR-3070 map), NOT tron80:
- intel-speed-select-state.service on 3bd6: active + enabled;
  /etc/default/intel-speed-select-state ("Managed by the intel-speed-select
  Ansible role") has FAST_CORE_RANGES='7-14 24-71 79-86 96-143' — exactly
  the https://github.com/positron-ai/tron/pull/3070 die-aware map (112
  phys cores; matches gen_tron_flatfreq.py output validated 2026-07-08).
  So PR-3070 has presumably merged to main and the Ansible role was
  updated to the new map.
- Live probe (unprivileged cpufreq, spin-pinned): cpu51=4400 MHz,
  cpu25=4348, cpu24=4313 (all inside the fast ranges; ~4400 rung because
  only 3 cores busy) vs cpu2 = 2700 exact clip. cpu27 probe earlier:
  4372. Shape is real and live.

BASELINE VALIDATED: her Jun-30 3bd6 run (multi-sweep-20260630-062732,
build 66deff22) reads +2.2% vs the canonical 3bda clamped baseline at the
gpt-oss p1024/g1024/s256 2-inst 8-users anchor (563.8 vs 551.5 parse) —
a clean same-host clamped baseline. (Units note: the CSV "Users" column
is TOTAL users; our prose "2 inst x 4 users" = Users=8.)

RESULTS — new (tron112 flat, 29924aa8) vs same-host clamped (66deff22),
geomean over all matched configs, via scripts/compare_csv.py:
  gpt-oss-tp4      parse +25.0%  gen +15.9%   (n=20)
  8b-tp2 / tp4     parse +19.5% / +18.3%  gen +16.2% / +8.0%
  3b tp1/tp2/tp4   parse +31.8/+30.4/+22.5%  gen +21.5/+20.1/+10.8%
  70b tp2/tp4      parse +4.4%  gen +5.9-7.7%   (FPGA-bound, as expected)
  mixtral          parse +8-11%  gen +4-7%
Long-context high-user configs gain most (gpt-oss p2048 2x16-32u parse
+42-43%) — the CPU-parse-bound signature.

DECOMPOSITION — the composite reproduces our PR-3070 ladder:
- vs our ladder-A (universal flat 4100, OLD map, main Jul 9, 3af6):
  gpt-oss parse +9.2% / gen +4.2% -> matches our measured PR-3070
  SOFTWARE effect (ladder B/A: +9.3% / +3.4%) almost exactly.
- vs our tron80-4100 run (Jul 5, 3af6): +9.4% / +4.7% — same story.
- Composite vs clamped: hers +25.0%/+15.9% vs our ladder A->C prediction
  +26.0%/+15.1% — agreement within ~1 pt on a different host, different
  build, deployed via the productionized service. The flat-freq +
  PR-3070 stack is CONFIRMED end-to-end.
- The ladder-B 8b-tp2 generate regression (-18%) is ABSENT in her run
  (8b-tp2 gen vs ladder-A: +8.7%) — fixed before merge or specific to
  the pre-merge PR build.
- Note vs Q2: build 29924aa8 (which postdates ef720667) is FASTER than
  Jul-9 main on checkerboard load, while ef720667 REGRESSED the @8u
  nightly serving metric on GNR — further evidence the nightly @8u
  metric and checkerboard throughput measure different regimes.

2026-07-12 3bda OUTAGE (investigated ~04:00-04:45 UTC via 3af6 jump):
- delphi-3bda is HARD-DOWN, not a tailscale glitch: tailscale last saw it
  ~22:05-22:30 UTC 2026-07-11 (tx no rx since), and a full ping +
  host-key sweep of the lab /22 (192.168.0.0/22) found NO host answering
  ssh as 3bda on any LAN IP. Per user, Hannah ran her test at 3bda too —
  it started 22:02 UTC, i.e. the host dropped off the network within ~30
  minutes of that run starting. The successful 220227 CSV analyzed above
  is the 3bd6 run; whatever happened on 3bda (its own sweep dir, crash
  logs) is on its local disk until the host returns.
- NEEDS: BMC/console check (power state, kernel panic?). History of
  host-level faults under FPGA test load on this fleet (2026-07-02 BAR
  wedge + PCU dispatcher timeout on 3bda; IERR marker on 3bd6).
- CONSEQUENCE: tonight's 3bda nightly cannot run (talos cannot reach it).
- When it returns, check in order: (a) FPGA enumeration (boot-
  unprogrammed 12ba:0076 history — may need pho image load + warm
  reboot); (b) whether /etc/default/intel-speed-select-state on 3bda was
  also updated to the tron112 ranges like 3bd6, or still carries tron80
  (determines the deployed shape!); (c) tailscaled up; (d) sync the
  canonical copy of this README (mirror is ahead while 3bda is down).
- Fleet discovery notes: delphi LAN = 192.168.0.0/22, jump via 3af6
  works when tailscale is down (3af6=192.168.0.78, 3bd6=192.168.2.155);
  ssh HOST KEYS ARE NOT UNIQUE — delphi-3c51 (192.168.2.188) presents
  the identical ed25519 key as rebuilt 3bda (same image), so identify
  hosts by `hostname`, never by host key.
- Applier fix needed before any future arming: flat_freq_apply prechecks
  the workspace isst binary which is NOT in sudoers — non-interactive
  runs must set FLAT_FREQ_ISST=/opt/intel-speed-select/intel-speed-select
  (add to apply_tron84_rinzler_AB.sh).

### 2026-07-13 — P4.3: rinzler-core frequency A/B through the REAL serving path (3bda, self-serve)

Context: 3bda returned from the Jul-11 silent freeze (no journal, no SEL
entry — power-cycled Jul 12 20:03, booted Jul 13 16:27); CI disabled by
Hannah -> dedicated experiment machine. Machine standardized on main:
tron package upgraded ef720667 -> 2026.07.13-29924aa8 (PR-3070 merged),
tron112 shape via the Ansible boot service (config already updated fleet-
wide Jul 11 20:54). FPGA dma readback PASS. platformd regenerated
instance envs with NEW-map cores after a config PATCH
(models=[{shape: ingested-gpt-oss-120b}], tp=4, count=2) — rinzler
processes pinned to new rinzler cores (1,145,2,146 / 73,217,74,218),
TRON_USE_SPECULATION=1 (consensus item 3 CLOSED: production runs spec ON).

Design: interleaved 5-min blocks A/B/A/B/A/B (A = deployed tron112,
rinzler cores clos:3 @2700; B = + cores 1,2,73,74 + sibs -> clos:0,
realized ~4000 MHz by turbostat), after a clean stack restart + 5-min
conditioning. Load: scripts /scratch/jhan/p43/loadgen.py from 3af6 over
LAN — closed-loop @8 users, UNIQUE ~1k-token prompts per request
(two instrument traps found and fixed: identical prompts hit the
persistent KV prefix cache, TTFT 1.23s -> 0.092s; and deterministic
per-user seeds made run N+1 replay run N's prompts, which the PERSISTENT
token cache served as prefix hits, TTFT -> 0.135s. Also /v1/completions
does not stream per-token and yields no text for harmony models — use
/v1/chat/completions, one SSE event per token, verified 59 events / 60
tokens). Per-token timestamps -> per-user decode TPS, TTFT, makespan
aggregate. perfetto+perf captured in blocks A2 and B3.

Results (gpt-oss-120b-tp4, 2 instances, @8u, ~660 reqs/block, 0 errors):

  pair   A clamped   B boosted   decode delta   TTFT A->B
  1      103.97      105.29      +1.27%         1.242 -> 1.229 s
  2      104.35      105.63      +1.23%         1.241 -> 1.231 s
  3      104.06      105.27      +1.16%         1.242 -> 1.230 s

  BOOST EFFECT: +1.2% +/- 0.06% decode TPS/user, -0.9% TTFT — small but
  REAL and perfectly reproducible (3/3 pairs; A-blocks stable +/-0.2%).
  Aggregate: +1.1% (552 -> 558 tok/s makespan).

MECHANISM (perfetto sched traces, 60 s windows):
- There is NO "*work_queue*" thread in build 29924aa8 — the scheduler
  coordinator moved to the FAST die-B worker cores by design (the new
  resource map pins Main/coordinator to the lowest tron core per slice,
  ~54ns L3). The ef720667-era hot work_queue-on-rinzler-cores picture is
  obsolete.
- Under @8u load the rinzler cores are ~2.5% occupied (fuse_worker +
  Drogon HTTP/SSE IO). The +1.2% therefore comes from the per-token SSE
  delivery path + per-request chat-template tokenization running ~48%
  faster on the serving-thread cores — a small critical-path component.
- Worker threads read ~95% sched-Running during load (includes their
  poll loops; work-vs-spin split needs the captured perf data — open).

VERDICT: boosting rinzler cores is a real but ~1% effect on the new
stack. It is FREE (cores are ~idle; no grant-rung or power downside
observed) — worth adding 1-2,73-74 to FAST_CORE_RANGES in the Ansible
role if we want the last percent, but it is NOT the missing-uplift
explanation. The @8u serving metric on the new stack is engine-bound,
not serving-path-bound.

PARSE/PREFILL ANALYSIS (added 2026-07-13, from the same blocks — per-
request prefill = prompt_tokens/TTFT, the CI "prefill~=" metric family;
prompt_tokens calibrated via usage: 823 tok per 4000-char prompt):

  pair   A clamped   B boosted   parse delta
  1      663.1       669.9       +1.03%
  2      663.6       668.8       +0.78%
  3      663.0       669.1       +0.92%
  (tok/s per request, mean~=HM; block stability +/-0.1%)

  BOOST EFFECT ON PREFILL: +0.9% +/- 0.1% — same story as decode: real,
  reproducible, ~1%. Consistent with the mechanism (tokenization + SSE
  on rinzler cores touch both phases' critical path a little).

Baseline comparison at CI prompt-length parity (A1k block: baseline
shape, 979-token calibrated prompts, 300 s): TTFT 1.539 s -> prefill
~636 tok/s; decode 102.7 tps/user. Same-family CI-era numbers (ef720667
+ tron80, @8u, ~1k prompts, over network): prefill~=783-799, TTFT
1.28-1.31 s. CAUTION — NOT attributable as a regression: load pattern
(closed-loop zero-think-time vs talos pacing), chat-template inclusion,
output length, and network boundary all differ; the honest comparison
is the next talos-style run on this stack. What IS clean: the A/B
deltas above, measured under identical conditions.
Cross-reference (different regime, per the metrics explainer): checker-
board tron112 in-process parse at p1024 2x8u = 727.9 tok/s (burst load,
ssp prefix effects, no HTTP).

THREADS x CORES x FREQUENCY — the two shapes under test (new PR-3070
map; "workers" = the map's tron_cores, hosting the app worker pool =
attention workers + the Main/coordinator thread + the scheduler loop):

  Shape 1: tron112 (deployed baseline; FAST='7-14 24-71 79-86 96-143'+sibs)
  phys cores        siblings          role / threads                 freq
  0, 72             144, 216          platform: platformd, OS        2700
  1, 2, 73, 74      145,146,217,218   rinzler proc: HTTP/SSE IO,     2700
                                      tokenize, fuse, admission
  3-6, 75-78        147-150,219-222   dev: TX DMA + RX (sibling)     2700
  7-14, 79-86 (dieA) 151-158,223-230  workers: attention (via        ~4000
                                      sibling thread ids)
  24-71, 96-143     168-215,240-287   workers: attention + Main/     ~4000
  (die B/C)                           coordinator (lowest core/slice)
  15-23, 87-95      159-167,231-239   spare (OS strays)              2700

  Shape 2: tron112 + rinzler boost (p43_rinzler_boost.sh apply):
  identical except cores 1,2,73,74 + sibs -> ~4000 (measured 3889).
  112 fast phys -> 116; grant rung unchanged.

CORE BUSINESS BY ARM (turbostat 30-s frames under load, mean Busy% /
Bzy_MHz; frames classified by the toggle core's frequency):

  Rinzler A/B experiment (workers always fast):
  role       A clamped        B boosted        note
  workers    49.1% @ 4020     49.1% @ 4022     unchanged (control OK)
  rinzler    24.5% @ 2640     23.2% @ 3889     same work, ~5% less busy
  dev        99.8% @ 2700     99.8% @ 2700     TX/RX spin loops (always)
  platform    4.7% @ ~2490     4.7% @ ~2495    background
  spare       2.6% @ ~2430     2.7% @ ~2440    background

  Worker W/F experiment (rinzler always clamped):
  role       W workers-2700   F workers-4000   note
  workers    49.1% @ 2728     49.1% @ 3992     IDENTICAL busy% at both
                                               clocks -> C0 time is poll-
                                               wait scaling with wall
                                               clock, not compute (compute-
                                               bound cores would get BUSIER
                                               when clamped). Matches the
                                               IPC 0.02 stall signature.
  rinzler    27.8% @ 2642     25.7% @ 2639     slightly busier when engine
                                               slower (more waiting/token)
  dev        99.8% @ 2700     99.8% @ 2700     spin, both arms

Artifacts: /scratch/jhan/p43/ (loadgen.py, p43_rinzler_boost.sh, blocks/
summaries + per-request jsonl + turbostat), profile captures
/scratch/jhan/flat_freq_tests/20260713-{182616,184618}_ci-workload-
profile-delphi-3bda/ (pftrace + perf.data + IPC + thread snapshots).
Timeline note: a mid-run `posadm restart` contaminated the first Arm-A
attempt (detected, discarded, redesigned to interleaved blocks).

### 2026-07-13 — P4.3b: the WORKER-core toggle through the serving path — Q1 CLOSED

The experiment CI could never run for us: toggle the 112 worker cores
(map tron_cores + sibs) between CLOS3 2700 and CLOS0 ~4000 while the
SAME rinzler serving stack handles the SAME @8u load (rinzler/dev/
platform untouched, verified per block). Interleaved pairs, 5 min each,
scripts/p43_worker_toggle.sh:

  pair  W workers-2700       F workers-4000       decode    parse
  1     100.53 / 1.392s      104.11 / 1.243s      +3.6%     +12.0%
  2     100.32 / 1.386s      104.18 / 1.242s      +3.8%     +11.6%
  3     100.41 / 1.390s      104.28 / 1.244s      +3.9%     +11.7%
  (decode tps/user / TTFT)   WORKER-CLOCK EFFECT: decode +3.7+/-0.15%,
                             parse/prefill +11.8+/-0.2%

FINDINGS (Q1 — why CI never showed the checkerboard boost):
1. Prefill IS fully clock-sensitive through the serving path (+12% for
   +47% clock — same as checkerboard's +12.6%). The CPU-bound phase
   behaves identically in both harnesses.
2. Decode @8u gains only +3.7% from the same clock change — the cores
   are wait-dominated, proven three independent ways: IPC 0.02 (perf,
   both arms), worker Busy% IDENTICAL at 49.1% under 2700 and 4000 MHz
   (turbostat; compute-bound cores would get busier when clamped), and
   the +3.7% behavioral ceiling itself.
3. The CI arithmetic closes by superposition: worker boost gave 3bda
   roughly +3-4% decode @8u; the ef720667 build regression (GNR-only,
   17cf-measured) cost ~-4.5% THE SAME NIGHT the boost went live.
   Net ~= -1% == "CI showed no improvement". Both effects were real;
   they cancelled.
4. OPEN SLIVER: CI's prefill~= stayed ~790 tok/s across ALL eras while
   our toggle moves parse +/-12% — CI's TTFT likely carries a non-prefill
   component (talos pacing/queueing, network, prompt-reuse against the
   persistent prefix cache?). Needs one look at the talos client or a
   like-for-like talos run on the new stack.
5. Tuning priorities implied: (a) the Q2 bisect (+4.5% decode on GNR,
   software); (b) wait-structure attacks — HW attention (USE_HW_ATTN,
   decode >=128 tok, default off), forward-pass cadence tunables
   (TRON_LIVE_TOKEN_LIMIT, 128-tok prefill chunks), speculation depth;
   (c) uncore/mesh frequency (attention is memory-bound; not an isst
   knob); (d) the free ~1% rinzler-core boost; (e) operating point —
   @8u is far below the aggregate-throughput knee.

Machine left in deployed state: workers fast (tron112), rinzler cores
clos:3, gpt-oss serving up. Scripts preserved: p43_worker_toggle.sh,
role_busy.py (turbostat per-role analyzer).

### 2026-07-13 — P4.3c: the prefill-flatness sliver — cache theory REFUTED, scheduler-pinning theory emerges

Question: why did CI's prefill~= stay ~790 tok/s in EVERY era when parse
is +12% worker-clock-sensitive?

Discriminating arms (loadgen --shared-prefix-chars / --think-time, each
under the worker toggle, 180 s blocks):
  arm                                workers-4000   workers-2700   sensitivity
  shared-prefix (784/834 tok cached,  TTFT 0.180 s   0.185 s       +2.8% (FLAT)
    verified via usage.cached_tokens)
  paced 2u unique prompts             TTFT 0.399 s   0.446 s       +11.8% (FULL)
  8u unique closed-loop (P4.3b)       TTFT 1.243 s   1.390 s       +11.8% (FULL)
-> cache-hit prefill is the ONLY mode that reproduces frequency-flatness,
   BUT its TTFT magnitude (0.18 s) is nothing like CI's ~1.3 s.

CI's own records (talos API, verified from systems_test@994badfc source:
closed-loop 8u barrier rounds, fresh client per request, deterministic
ShareGPT corpus, prefill = prompt_length/TTFT, per-request cached_tokens
recorded):
  session                          n   TTFT mean  cached
  3bda Jul-11 BOOSTED ef720667    80   1307 ms    69/1035 tok (7%)
  17cf Jul-11 CLAMPED ef720667    80   1300 ms    69/1035 tok (7%)
  17cf Jul-08 CLAMPED 198650bf    80   1279 ms    69/1035 tok (7%)
-> PROMPT-REUSE/CACHE THEORY REFUTED for CI: only the template+system
   prefix caches (constant 69 tok); prompts genuinely prefill fresh.
-> CI's flatness is REAL: boosted and clamped hosts measured identical
   TTFT on the same build/night, cache-free.

2026-07-14 05:30 UTC status — talos self-run staged, PAUSED for machine
contention: the decisive talos-harness A/B was fully prepared (venv at
3af6:/scratch/jhan/p43/talos/venv with openai/pymongo/rich/transformers/
opensearch-py; harness clone /tmp/jhan-systest @994badfc, PYTHONPATH with
/tmp/jhan-talos; invocation = benchmark_tps(Config()) with env MODEL/
N_USERS=8/N_ROUNDS=10/PROMPT_LENGTH=1024/GENERATE_LENGTH=1536/
TOKENIZER_MODEL=openai/gpt-oss-120b/OPENAI_HOST=http://192.168.1.4/v1,
TALOS_SESSION=fresh uuid; results then queryable via
talos:5000/sessions/<uuid>/metrics). Findings from smoke: (a) harness
workers die as opaque BrokenProcessPool on API errors (debug markers left
in the /tmp/jhan-systest clone; real error surfaced standalone: model
404); (b) at 05:23 UTC a localhost process on 3bda (after a positron-user
session from 100.94.250.110, 23:29-03:13) reprovisioned serving to
qwen-2.5-32b x4 — gpt-oss gone, machine no longer exclusively ours.
Overnight A/B NOT launched (would perturb the other party's work).
Resume checklist (~40 min once ownership confirmed): re-PATCH config to
gpt-oss tp4 x2, verify advertised name via port 80 /v1/models, rerun
smoke (N_USERS=1 N_ROUNDS=1), then arm F run -> worker clamp -> arm W run
-> restore, N_ROUNDS=10 each; compare prefill_mean/ttft vs the ~790
constant. Frequency shape untouched throughout (tron112 deployed).

### 2026-07-14 — P4.3d: THE TALOS HARNESS ITSELF CONFIRMS IT — Q1 fully closed

Ran the actual CI measurement code (systems_test@994badfc, the commit of
the Jul-11 nightly; venv on 3af6; nightly-parity: 8 users, 10 barrier
rounds, prompt 1024 / generate 1536, capture 896-1024, sharegpt corpus,
via Caddy port 80) against 3bda's new stack, toggling ONLY the worker
cores between rounds of runs. Cache-cold verified per arm via the
harness's own cached_tokens (~71 = template prefix, same as CI's
historical 69):

  arm  workers  prefill tok/s  TTFT ms  decode TPS/u  cached  seeds
  F    ~4000    883            1207     95.26         72.8    0-79
  F2   ~4000    867            1224     93.58         71.0    400-479
  W3    2700    736            1441     87.97         71.0    200-279

  WORKER-CLOCK EFFECT VIA THE CI HARNESS: prefill +19% (736 -> 875 avg),
  TTFT -16%, decode +7.3%. F/F2 reproduce within 2% (corpus effects nil).

The prediction lands on both ends:
- New stack, workers fast: prefill 875 BREAKS AWAY from the historical
  ~790 constant (+11%), decode 94.4 ~= the boosted-era nightlies
  (93.3-94.2) almost exactly.
- Workers clamped: prefill falls to 736 — back to (slightly below) the
  historical constant band; the old "~790 forever" regime is the
  clamped-scheduler regime.
Note decode's talos-measured sensitivity (+7.3%) exceeds the loadgen's
(+3.7%) — different load pattern (barrier-synced rounds, 1536-token
generations, capture-window TPS); both small, same direction.

TWO HARNESS GOTCHAS DEMONSTRATED LIVE (worth reporting to the CI team):
1. Deterministic seeds (seed = round*n_users + user, fixed corpus) mean
   ANY back-to-back rerun against a live engine hits the persistent
   prefix cache: our first W arm read "prefill 4745 tok/s" with 647/1035
   tokens cached. CI is protected ONLY by fresh provisioning per nightly.
2. The KV store survives same-model reprovisioning (hugepage-backed
   store files persist): even after an engine bounce, 479 tokens still
   cached. Fresh SEED ranges are the reliable isolation (we patched a
   SEED_OFFSET env into our systems_test clone; one-line, worth
   upstreaming).
3. (From the smoke debugging: harness workers die as opaque
   BrokenProcessPool on any API error — the underlying exception is
   swallowed. Also worth upstreaming a fix.)

PUBLIC CONFIRMATION — THE REAL NIGHTLY (2026-07-14, build de7647f3;
CI re-enabled on 3bda by Rhys/Hannah; ran ~11:00 UTC, before our runs):
  gpt-oss @8u          3bda (tron112 boosted)   17cf (clamped)
  prefill~=            874 tok/s                788 tok/s      (+11%)
  TTFT                 1171 ms                  1299 ms        (-10%)
  decode TPS/user      95.70                    96.05          (~equal)
First nightly ever to show the flat-freq boost — 3bda's 874/1171 matches
our Arm-F prediction (875/1207) almost exactly, and 17cf stays at the
historical ~790 constant (no boost service; on the new map its scheduler
sits on clamped worker cores). 8B tp2 shows the same split: 3bda prefill
1.4k / TTFT 742ms vs 17cf 1k / 1022ms. Decode @8u remains ~insensitive
cross-host, as measured. Timeline of eras, for the record:
  Jul 10-11 nightlies:  OLD build (ef720667) + tron80 — scheduler pinned
                        on clamped rinzler cores on BOTH hosts -> both
                        capped ~790, no visible boost (+ the -4.5% build
                        regression cancelling decode gains).
  Jul 11 checkerboard:  new stack (29924aa8+tron112) -> +25%/+16%
                        (Hannah, 3bd6) — boost fully visible.
  Jul 14 talos toggles: new stack, same host — prefill 736<->875 (+19%).
  Jul 14 real nightly:  new stack fleet-wide -> boost visible in CI
                        (874 vs 788 cross-host).

### 2026-07-16 — Power cost of the flat-freq boost (turbostat PkgWatt, 3bda, load-window means)

  config (same instrument, same host)   workload            Bzy_MHz  PkgWatt  RAMWatt
  CLAMPED boot-default (Jun-30 CI run)  gpt-oss single       2829     469 W    51 W
  FLAT v1 3.9GHz (Jul-3)                same gpt-oss single  3887     610 W    49 W
  tron88 4100-class (Jul-5)             gpt-oss+8B grid      3797     659 W    62 W
  tier3 (Jul-6)                         same grid            3794     658 W    62 W
  (24h sweep whole-window incl. 70B/mixtral phases: 789 W / RAM 128 W)

Matched comparison (identical gpt-oss workload): clamped -> flat =
+141 W package (+30%) for +16.9% parse / +13.3% gen -> CPU-package
perf/W DROPS ~10-13%. BUT the system view flips it: CPU packages are a
minority of an inference appliance's draw (8 FPGAs at ~210-225 W each;
comparable GNR system ~2.3 kW under soak) -> +141 W ~= +6% system power
for +13-17% throughput => SYSTEM-level perf/W IMPROVES (INFERRED — 3bda
wall power not directly measured; FPGA-share assumption from the
andoria soak hardware numbers). Both sockets stayed well inside the
2x500 W TDP budget (max seen 789 W). Data: turbostat_per_cpu*.tsv in
the run folders (clamped file: 2026-06-30.../turbostat_per_cpu_during_ci
.tsv; NOTE the Jul-3 file kept logging through the 24h sweep — window
the first ~120 loaded samples for the single run).

### 2026-07-16 — THE COMPLETED 2x2 (build x shape, talos serving path, 3bda) — final word

Method: laptop-independent orchestrator (11:37-12:09 UTC window after the
nightly): per-arm rinzler BINARY swapped via systemd drop-in (fingerprint-
verified per arm: prz_*-198650bf / prz_*-29924aa8), IDENTICAL platformd-
generated placement args (new-map --app-cores) for both builds — so the
build axis is pure engine-binary, single-variable. Store files cleaned
between builds; fresh SEED_OFFSET per run; nightly-parity params; talos
client on 3af6; perfetto/perf captured in 0bf rep-2 both shapes. Machine
restored (stock 0e50a645 binary, trio, tron112) by 12:09.

  gpt-oss tp4 @8u        workers-clamped(2700)     tron112(~4000)
  0bf (n=3)              prefill 744 / dec 92.4    prefill 877 / dec 97.1
  aa8 (src n=1 + pkg)    prefill 756 / dec 88.0-89.5  prefill 871-875 / dec 94.4-94.6

HEADLINES:
1. COMPOSITE (aa8+tron112 vs 0bf+clamped, the campaign end-to-end by CI
   methodology): prefill +17.7%, decode +2.4%.
2. Frequency effect is build-INDEPENDENT: 0bf toggles +18.0% prefill /
   +5.1% decode; aa8 +16% / +6.5%. The flat-freq win needs only the
   112-worker placement, not the new engine code.
3. PR-3070 BINARY effect through serving at IDENTICAL placement:
   prefill ~0% (877 vs 871-875) — the ladder's +9.3% "software" parse
   gain was THE MAP (worker count/placement), not kernels;
   decode -3% (0bf 97.1/92.4 vs aa8 94.5/88-89.5 at fast/clamp) — the
   aa8 engine is slightly SLOWER serving gpt-oss @8u. PLAUSIBLE
   mechanism (TESTED 2026-07-16 -> NULL at n=13, see ab23 section): aa8's coordinator lives ON a worker core
   (fast but steals worker capacity); 0bf's scheduler sits on dedicated
   rinzler cores. Worth a look by the tron team; small but consistent
   across both shapes. NOTE: best decode cell of the whole 2x2 is
   [0bf + tron112] = 97.1.
4. MECHANISM REVISION (honesty ledger): perfetto shows 0bf's scheduler
   thread ~90% busy at 2700 (CPUAFFINITY-confined, both arms) while
   prefill scaled fully -> a clamped scheduler does NOT cap prefill at
   this workload. The historical ~790-constant is therefore attributed
   to the OLD MAP's worker layout (80 workers/old placement), mechanism
   within it UNRESOLVED (candidates: worker-capacity saturation point,
   old-map die-crossing, scheduler-under-old-map-conditions). The
   scheduler-clock-cap claim is PARTIALLY REFUTED as the specific cause;
   the map-unlock claim (PR-3070's placement made serving frequency-
   responsive, nightly-visible) stands CONFIRMED by this 2x2 + the
   Jul-14 nightly. [0bf/aa8 + OLD-map args] cells would settle the
   residual mechanism if ever needed.
aa8 source-vs-package consistency: verified (94.56/870.9 vs 94.4/875).

### 2026-07-15 — ef720667 investigation CONCLUDED + machine-regime correction

VERDICT (phases 1-2, two independent run sets): the -4.5% gpt-oss decode
regression DOES NOT reproduce in direct-runtron checkerboard conditions.
Pooled clean runs, gen tok/s @2x8u p1024/g1024/s256, same shape, same
day, interleaved: 198650bf n=4 mean 97.8 {100.3, 99.4, 95.5, 95.9};
ef720667 n=6 mean 99.5 {96.6, 100.5, 100.5, 104.0, 98.8, 96.4} — the
suspect build is, if anything, ~+2% FASTER; spread ~±4%. Combined with
the CI-only visibility (17cf 97.5->93.4) => the regression lived in the
SERVING path (where the old build's scheduler was pinned-clamped), which
checkerboard structurally bypasses. Build retired, prod healed
(residual ~-1.5% on de7647f3), phase 3 (manual old-build serving A/B)
judged not worth the effort by this session — but the scheduled task
remains ACTIVE per user (a run was in progress 2026-07-15 19:0x UTC);
final phase-3/retirement decision deferred to the user after that run
reports.
BONUS reproduction: 198650bf (pre-#3148) reliably TRON_ASSERTs on
back-to-back runs when hugepages are not yet released ("Failed to mmap
libpos-slice: Cannot allocate memory") — live confirmation of the
tron#3097 bug class the Jul-9 nightlies died of; ef720667+ tolerates.
Fix for benchmarking old builds: wait for HugePages_Free to recover
between runs (phase2b free-gate: zero failures).

MACHINE-REGIME CORRECTION (from the scheduled session's gate-fail,
2026-07-15 14:12, verified against systemd timers): the split-runner
timers are ACTIVE again — GitHub CI runner owns 3bda from 14:00 UTC to
02:45 UTC (daytime PR benchmarks; ci-runner-start@ fired 14:00, stopped
rinzler@0-3, Runner.Listener accepting jobs); talos nightly ~04:25-11:20
UTC. TRULY FREE windows: ~11:30-13:45 UTC and ~02:45-04:20 UTC only.
The earlier "3bda is ours all daytime (12:00-04:00 UTC)" model was
WRONG/stale. ACTION: reconcile with Hannah — either she re-disables the
GH runner on 3bda (restoring "ours in daytime") or our experiment
windows shrink to the two gaps / require ci-runner.sh handovers.
Also flagged: serving engines left up during GH-runner time (status quo
since Jul-14) potentially perturb PR benchmarks — Hannah's call.
TSX provenance (Bill's question, 2026-07-15): TSX/RTM ENABLED on both
CI DUTs (rtm CPU flag; tsx=on cmdline; runtron logs "INIT: Intel RTM
(TSX) supported" in every run). The kernel's "Unknown parameter tsx=on"
boot warning is cosmetic. tron uses RTM+tpause as its wait/wakeup
primitive (mwaitx.cpp); no-TSX fallback = pause-spin that fights the HT
sibling — fatal to PR-3070's two-threads-per-core placement. TRON_NO_RTM
=1 exists for quantifying the cliff.

### 2026-07-14 — Operating directives + forward action plan (user-set)

DIRECTIVES: (0, 2026-07-16) EVERY test captures power: wrap runs with /scratch/jhan/tools/power_capture.sh start|stop <outdir> (turbostat PkgWatt/RAMWatt; summary auto-written); report watts next to perf. (1) talos/CI harness is the PRIMARY test mechanism from now
on (checkerboard only for targeted comparisons); (2) 3bda is ours in
DAYTIME, nightly CI owns it at night (~07:00-11:00 UTC) — end-of-day
ritual: restore fleet-standard serving config, leave deployed tron112
shape, nothing running into the CI window.

ATTRIBUTION CLARIFICATION (recorded after user challenge): the -4.5%
decode regression that cancelled the boost on Jul 10-11 nightlies was
build ef720667 (Jul 10, PRE-PR-3070, old map; evidence: 17cf same-shape
97.52->93.39 at that build change, Genoa flat; mostly healed by
de7647f3, residual ~-1.5%). PR-3070 never degraded gpt-oss — it
improved it (+9.3%/+3.4% software effect, ladder-measured). ef720667
never appeared in any checkerboard A/B, which is why checkerboard never
saw its regression.

ACTION PLAN:
1. [user] Send the Hannah/team note: nightly-visible boost story; deploy
   boost service to 17cf (788 vs 874 prefill every morning); optional
   +1% rinzler cores (FAST_CORE_RANGES += 1-2 73-74); tie role ranges to
   resource-map.yaml; 3 harness fixes to upstream (SEED_OFFSET,
   surface worker exceptions, KV-store-survives-reprovision note).
2. [ready to run] Long-prompt gpt-oss CI config proposal: checkerboard
   gradient (+12% parse @p256 -> +43% @p2048) says the current
   prompt=1024-only nightly sits at the shallow end for CPU-side
   sensitivity. Pilot in a daytime window: talos harness, prompt=4096
   @8u, fast-vs-clamped; then PR the config into systems_test perf.py
   (check ShareGPT generator behavior >2k tokens first).
3. [mine] Formalize talos_run.sh wrapper (venv + env + SEED_OFFSET +
   session bookkeeping) as the standard runner; upstream SEED_OFFSET so
   the primary mechanism is not a patched clone.
4. [scheduled] ef720667 investigation: daily idle-window task (12:33
   UTC, gated on CI window + machine idleness + HOLD marker) executes
   /scratch/jhan/ef720667-inv/PLAN.md — source-build ef720667 +
   198650bf (apt no longer carries them), checkerboard A/B first,
   manual-serving talos A/B only if needed. CI window measured from
   talos session records: start ~04:30 UTC, end ~11:00-11:20 UTC,
   very stable -> OUR window = 12:00-04:00 UTC daily.
5. [team] 3bda Jul-11 silent freeze (no journal/SEL) — hardware/BMC
   investigation if it recurs.
6. [next frontier, daytime windows] wait-structure experiments: HW
   attention (USE_HW_ATTN, decode >=128 tok), forward-pass cadence
   (TRON_LIVE_TOKEN_LIMIT, 128-tok prefill chunk size), speculation
   depth, uncore/mesh frequency; operating-point/capacity study beyond
   @8u.
7. [housekeeping] handoff-generation pass for recent sessions; remove
   debug patches from /tmp/jhan-systest clone once SEED_OFFSET lands
   upstream.

### 2026-07-14 — Long-prompt pilot (action-plan item 2): talos harness, prompt-length gradient

Method: talos harness, gpt-oss-tp4 @8u, generate=1536, capture 896-1024,
engine bounce before EVERY run (cache verified clean: cached ~69/53 =
template overlap only), fresh SEED_OFFSET per arm, workers toggled
between F (~4000) and W (2700). p4096 arms are n=8 (single round) —
see corpus limitation below. p1024 rows from P4.3d for reference.

  prompt   arm  n   TTFT ms   prefill tok/s   decode TPS/u
  1024     F    80  1207      875             94.4 (avg F/F2)
  1024     W    80  1441      736             88.0
  2048     F    80  3144      653             83.6
  2048     W    80  3688      553             80.1
  4096     F     8  9399      440             74.4
  4096     W     8  11296     366             65.4

  Worker-clock sensitivity by prompt length (F vs W):
  prefill: +19% / +18% / +20%  — UNIFORM ~+19-20% at every length
           (talos's barrier rounds keep all 8 prefills concurrent at
           every p, unlike checkerboard's burst overlap which grew
           with p — hence checkerboard's +12->+43% gradient vs talos's
           flat ~20%).
  decode:  +7.3% / +4.4% / +13.8% — rises at long context (deeper
           attention per token = more CPU work), though p4096 is n=8.
  Absolute rates fall with length (prefill 875->440; decode 94->74):
  attention superlinearity, as expected.

WHY THIS BELONGS IN CI: (a) prefill stays ~20% clock/CPU-sensitive at
every length — long-prompt configs guard the CPU-side path where the
scheduler-placement class of regression hid for weeks; (b) TTFT at
p4096 is 9.4-11.3 s — the user-visible long-context pain point, worth
an SLO-style goal; (c) today NOTHING in the nightly tests >1024-token
prompts while the model advertises 131k context.

HARNESS/CORPUS WORK NEEDED FOR THE systems_test PR (discovered here):
1. prompt.py generate() RAISES for convos shorter than prompt_length —
   the harness cannot run >~2k prompts today. Our clone carries a
   deterministic long-convo selector patch (map seeds onto qualifying
   convos).
2. Corpus: only 13/1000 sharegpt convos are >=4096 tokens (>=80 exist
   for 2048). p4096 needs corpus augmentation (concatenate convos or a
   long-context corpus) for full 80-request rounds.
3. Bonus bug: generate() mutates the cached convo (inserts the system
   message into self.convos permanently) — harmless for fresh-process
   runs, corrupts long-lived processes.
Recommendation for the PR: add prompt=2048 config now (works with
existing corpus, +80 qualifying convos), stage prompt=4096 behind the
corpus fix; also record prefill from OBSERVED prompt_tokens (perf.py
currently divides the CONFIGURED length by TTFT).

UNIFIED EXPLANATION (status: CONFIRMED 2026-07-14 — the operative
prediction verified by the CI harness itself AND by the production
nightly; previously SUPPORTED): on the
OLD build the single scheduler thread (work_queue) was the prefill
bottleneck, and PRODUCTION pins it to clamped rinzler cores (CPUAFFINITY)
— so CI prefill was scheduler-capped at ~790 regardless of worker clocks
— while CHECKERBOARD leaves the same thread unpinned ("N/?-work_queue" =
migratable), letting it ride boosted cores, hence +12% there. The new
build moved the coordinator onto fast worker cores by design, which is
why the serving path NOW shows the full +11.8% in our toggles.
Every piece is independently observed (work_queue at 87-100% on clamped
rinzler cores during the actual Jul-11 nightly; thread unpinned in
runtron; CPUAFFINITY in instance envs; new-build traces have no
work_queue and full sensitivity). DECISIVE TEST: one talos run on the
new stack — prefill~= should break from ~790 and become clock-sensitive.
Ask Hannah.

Planned next (pending explicit user go): arm tonight's nightly as the
rinzler-boost A/B — at 02:55 UTC (after runner-stop, before nightly)
apply "tron84" = tron80 workers + rinzler cores 24,48,72,96 (+HT sibs)
-> CLOS0 ~4100, drivers/others stay <= 2700; baseline = the Jul 10/11
tron80 pair. Script drafted: scripts/apply_tron84_rinzler_AB.sh
(preflight refuses if Runner.Worker alive or pre-shape is not strict
tron80; readback at 02:55 and 06:55 UTC for provenance; revert =
reboot via PR#165 boot service or flat_freq_apply with the worker-only
list). Caveats: a reboot before the nightly silently reverts the A/B
(check readback files before interpreting); a new tron build tonight
would confound build-vs-shape (check the report's version line).

### 2026-07-16 — ab23 coordinator-placement A/B: NULL at n=13 (hypothesis retired)

Tests the 2x2 HEADLINE-3 "plausible mechanism": does aa8's Main/
coordinator thread sharing a fast WORKER core (lowest core per slice:
24/96 for gpt-oss tp4 x2) cost the -3% serving decode vs 0bf's
dedicated-scheduler layout?

Design (kit: /scratch/jhan/ab23/): aa8 build via systemd drop-in;
  stock  = unmodified app-cores (Main on worker cores 24/96);
  dedic  = rz_wrapper.sh rewrites app-cores per instance
           (",24-29,"->",15,25-29,"  ",96-101,"->",87,97-101,") so Main
           lands on spare cores 15/87, boosted clos0 for the session
           (with HT sibs 159/231); worker set otherwise IDENTICAL
           (worker count unchanged; core 24/96 simply idles in dedic).
  Serving path: platformd PATCH -> gpt-oss tp4 x2; client on 3af6 =
  talos benchmark_tps nightly-parity (8u, p1024/g1024, 80 req/cell,
  cache-cold fresh seed ranges per cell, verified cached_tokens ~69).
  Interleaved stock/dedic pairs, full re-provision between cells.

Results — n=3 (completed 20:31 UTC) trended +1.5% decode / +1.7%
prefill (pairs +2.9%/-1.0%/+2.6%). Confirmation reps 4-13 (21:33-23:27
UTC, seeds 6000-7900) erased it. POOLED n=13 pairs:

| metric          | stock  | dedic  | delta          |
|-----------------|--------|--------|----------------|
| decode tok/s/u  | 93.78  | 93.81  | +0.03% (NULL)  |
| prefill tok/s   | 876.7  | 881.1* | +0.5%  (noise) |
| TTFT ms         | 1212   | 1204   | -0.7%  (noise) |

*dedic_r8 excluded from prefill/TTFT means (transient: TTFT 2105 ms,
one bad round); its decode 93.64 is normal and included.

Arm-application VERIFIED from journald (the ps-snapshot placement files
are inconclusive — captured pre-spawn): during dedic cells BOTH gpt-oss
serving instances logged the rewrite and matching engine pinning —
  rz_wrapper: instance=0 app-cores rewritten: 151-152,15,25-29,...
  rz_wrapper: instance=1 app-cores rewritten: 223-224,87,97-101,...
  INIT: Pinning application cores to 151-152,15,25-29,... (rz0/2)
while stock cells pin 151-152,24-29,... / 223-224,96-101,... The clos0
boost path is the same sudo isst used by worker_toggle, which logged
success at window open. Restore verified after ALL_DONE (23:27 UTC):
drop-in removed, trio serving back, tron112 fast shape reasserted,
spares 15/87/159/231 back to clos3.

CONCLUSION: coordinator placement does NOT matter at 8u on this
workload — consistent with the wait-domination picture (decode ~85%
wait-bound; the coordinator's cycles-stolen-from-one-worker are lost in
slack). The -3% aa8 serving-decode cost vs 0bf is UNEXPLAINED again;
remaining candidates are engine-code differences probed by the
wait-structure items (speculation depth, USE_HW_ATTN, chunk cadence).
Do NOT pitch a placement change to the tron team; hand them the -3%
finding without a mechanism claim.

POWER: this run predates directive (0) per-arm capture. Single live
datapoint mid-run (power_capture.sh smoke, 23:05 UTC): 732 W pkg @
3902 MHz busy — flat-freq loaded band + client burst. Any rerun must
wrap cells with power_capture.sh start/stop.

### 2026-07-17 — Eddy's under-stress claim REFUTED (inverted); four decode-gap hypotheses killed in one night; ab25 designed

1) EDDY CLAIM ("CI sends one prompt at 1K; tronperf loops different user
prompts, so tronperf stresses more") — VERDICT: FALSE, direction inverted.
Verified three ways (stock-source trace, Mongo empirical audit of real
nightlies, tool identification; all adversarially re-derived):
- Stock talos CI at p1024/8u/10r sends 80 UNIQUE prompts per run:
  seed = round*n_users + user (stock testlib/tps.py:144), distinct
  sharegpt convo per seed + unique seed-derived "[TIME: hh:mm:ss]"
  system message (prompt.py:60-71). Full HTTP/SSE serving path,
  ignore_eos, generate_length 1536 (perf.py:135-146; n_rounds=10).
- Last 5 recorded 3bda nightlies (Mongo, 400 requests): TTFT median
  1.17-1.33 s, 0% under 300 ms, cached_tokens only {0, 71} (~7% =
  chat-template preamble). Real cold prefill every request, every night.
- "tronperf" is NOT a load generator: it is the perfetto tracing wrapper
  around runtron (tron/perfetto/tronperf; exec's runtron --trace-gen).
  Its recorded invocation (run-tronperf.sh) sends 8 FIXED Moby Dick
  chapter prompts (/scratch/prompts/md_chN.txt, chapter i+1 per user i,
  identical every run), one-shot batch at t=0, no loop. The only loop
  (--iterations, unused) REPLAYS the same prompts as prefix-cache hits
  (tokens_reused) — i.e. it stresses LESS than CI, not more.
- Kernel of truth worth fixing (goes into the systems_test PR):
  (a) the stock 80-prompt set is byte-identical every run/night (no
  RNG, no SEED_OFFSET upstream), so any back-to-back same-model
  same-config rerun is ~100% prefix-cache hit; the nightly escapes only
  because it rebuilds tron and provisions 8 other model configs before
  gpt-oss (hugepage KV evicted). (b) prefill = CONFIGURED
  prompt_length / TTFT, never cache-corrected (tps.py:340, perf.py:325;
  verified empirically: 729.86 = 1024/1.403 exactly) — under cache hits
  it would silently report ~10,000 tok/s. Hardening: date-derived
  SEED_OFFSET upstream + cache-aware prefill (subtract cached_tokens,
  fail-loud when cached_tokens > preamble or TTFT < 0.3 s).
- Our A/B data is unaffected: patched SEED_OFFSET ranges; all 26
  sessions from 07-16 re-verified in Mongo (cached <= 71, 0% TTFT<0.3s).

2) DECODE-GAP LEDGER — four deaths recorded 07-17 (workflow + agents):
- SPECULATION: DEAD. gpt-oss CANNOT speculate on any binary present —
  speculation is EAGLE-draft-based and no eagle-ingested-gpt-oss-120b
  entry/weights exist (model-definitions.i has eagle for llama-8b/70b
  only). platformd sets TRON_USE_SPECULATION=1 (schema default true)
  but find_eagle_model silently clears it (full.cpp:306-356, verified
  in journald: zero EAGLE lines in gpt-oss windows). BOTH harnesses ran
  gpt-oss spec-off. Also: zero spec-on checkerboard artifacts exist on
  any host tree (1012/1012 cells Speculation:0 — never invoked).
  NOTE: the llama trio DOES run EAGLE speculation in production.
- METRIC DEFINITIONS: DEAD (<=2-3pp; both harnesses decode-only,
  TTFT-excluded, linear in uniform speedup; file:line audited twice).
- PHASE OVERLAP (H3): DEAD. runtron prefills are batch-interleaved:
  all 4 users' parses complete within 18 us of each other BEFORE the
  first decode token (microsecond log forensics, multi-sweep-20260701-
  052049 cell); checkerboard's generate window is pure batched decode,
  structurally like talos's 896-1024 capture window. Overlap ~0.0002%.
- 0bf-PARTIAL-CLAMP: DEAD. ab22 serving pinned BOTH builds to the same
  fast-set layout — platformd's RZ_CLI_ARGS --app-cores overrides the
  binary's built-in map (journald-verified: rz0/2 = 24-71+HT151-158,
  rz1/2 = 96-143+HT223-230, 0/56 outside the fast set). 0bf's +5.14%
  is clean like-for-like.
- RINZLER-CLAMPED-CORES (H2): CLOSED as minor, quantified. The serving
  front-end (SSE egress + chat template) is a serial ~4% of the token
  period at fixed 2700; boosting exactly those cores gave +1.2 +- 0.06%
  decode (P4.3, 3/3 pairs). Covers ~1.2pp of the ~8pp gap.
- CLEAN ANCHORS: checkerboard freq response +13.7% gen / +16.4% parse
  (same-build ae82870a pair, clamp and flat turbostat-verified);
  serving freq response +5.1% (0bf) / +5.7% (aa8) at identical
  placement (ab22). Talos samples DEEPER context (~1.9-2.0k) than
  checkerboard's window average (~1.5k), where attention share is
  LARGER — the anomaly direction is real, not definitional.
- REMAINING HYPOTHESES: (a) worker GEOMETRY — checkerboard instances =
  40 phys cores, no HT (legacy layout); serving instances = 48 phys +
  8 HT in die-aware slices; (b) serving-process residual (rinzler
  engine loop vs runtron in-process). Discriminator = ab25.

3) ab25 DESIGN (kit staged; install blocked by session permissions,
pending user go): serving path, deployed binary, 2x2x3 =
  {GEOM old = legacy layout via drop-in wrapper rewriting --app-cores/
   --dev-cores (inst0 27-36,37-46,51-60,61-70 dev 25,26,49,50; inst1
   75-84,85-94,99-108,109-118 dev 95,119,120,121) | GEOM new = native}
  x {clamp-all = ALL 288 cpus clos3 (2700) | fast-all = ALL clos0
   (~3.9GHz at this load)} x 3 interleaved reps.
  Nightly-parity client on 3af6 (u8 p1024 g1536 capture 896-1024,
  fresh SEED_OFFSET 9000+), per-cell power_capture.sh (directive 0),
  journald pinning verification with abort-on-mismatch, window gate
  11:28-13:45 UTC, full restore (trio + tron112 shape) at end/abort.
  PREDICTION: old-geom freq response ~+13% => geometry explains the
  gap (serving path exonerated; CI decode numbers are honest for the
  production placement — the checkerboard layout is simply more
  clock-sensitive per worker). ~+6-7% => the serving process itself
  is the diluter => next step perfetto attach-the-waits on the engine
  loop under serving. Caveat: clamp-all is slightly harsher than the
  boot-default clamp (which left the 16 PCT boot cores fast — 10% of
  busy samples in the Jun-30 turbostat); noted for interpretation.

### 2026-07-17 — ab25 RESULT: geometry does NOT explain the decode gap; residual isolated to serving-process-or-build

Ran 11:44-12:28 UTC in the post-nightly window (kit /scratch/jhan/ab26/../ab25/,
journal + per-cell power + journald pinning evidence in results/).
Serving path, deployed binary (0e50a645), gpt-oss tp4 x2, talos
nightly-parity client (u8 p1024 g1536 capture 896-1024, fresh
SEED_OFFSET per cell, cached 69-71 verified all 12 cells). 2x2x3:

| arm                    | decode (n=3) | prefill | TTFT ms | PkgWatt @ Bzy_MHz |
|------------------------|--------------|---------|---------|-------------------|
| legacy geom, clamp-all | 86.48        | 645.5   | 1626    | 551 @ 2694        |
| legacy geom, fast-all  | 93.69        | 817.3   | 1304    | 708 @ 4024        |
| native geom, clamp-all | 89.70        | 735.0   | 1436    | 579 @ 2698        |
| native geom, fast-all  | 96.05        | 896.7   | 1187    | 796 @ 4028        |

- Decode frequency-response THROUGH SERVING: legacy geometry +8.3%,
  native +7.1% — nowhere near runtron's +13.7% anchor. GEOMETRY
  (40-phys legacy vs 48+8HT die-aware slices) moves response only ~1pp.
  Prefill response: +26.6% legacy / +22.0% native (prefill is MORE
  clock-responsive through serving than runtron's parse +16.4%; the
  anomaly is decode-only).
- CONSISTENCY CHECKS PASSED: all-core toggle (+7.1% native) beats
  ab22's 112-set-only toggle (+5.7%) by ~1.3pp ~= the directly measured
  +1.2% rinzler-core effect. Pinning verified per provisioning from
  journald (legacy arms: 27-36,37-46,51-60,61-70 / 75-84,85-94,99-108,
  109-118 with rewritten dev-cores; native arms: slice layout).
- MAP VALUE CONFIRMED through serving: native beats legacy geometry
  absolutely at both clocks (+3.7% decode / +13.9% prefill at clamp;
  +2.5% / +9.7% at fast) — PR-3070's extra workers + slice structure
  are real wins.
- POWER (directive 0): fast-all = 796 W pkg (native) — +136 W over the
  deployed tron112 shape (~660 W) for only ~+1.3% decode vs the
  112-set toggle. tron112 remains the right production shape; fast-all
  is a diagnostic arm only. clamp 551-579 W. RAMWatt flat 51-53 W.
- REMAINING UNKNOWN, now sharply bounded: runtron +13.7% (build
  ae82870a) vs serving +8.3% (deployed 0e50a645) at MATCHED geometry
  and toggle scope = ~5.4pp attributable to (a) the serving process
  execution structure, or (b) the newer build lineage having lost
  decode clock-sensitivity. Discriminator = ab26 (runtron freq A/B on
  0bf and aa8 lineages, flat-all vs clamp-all, 3 singles each,
  checkerboard harness with RUNTRON_BIN override — env wins per
  config/checkerboard.defaults.env:12). Predictions: both lineages
  ~+13% => serving process is the diluter -> perfetto attach-the-waits
  on the engine loop under serving next. aa8 ~+8% with 0bf ~+13% =>
  the PR-3070-lineage ENGINE lost clock response -> diff engine
  changes; serving exonerated. Both ~+8% => condition-of-day confound,
  re-examine (bitfile, corpus, prompts).

### 2026-07-17 evening — BREAKTHROUGH CANDIDATE: the +13.7% anchor era ran with TSX/RTM DISABLED (wait-regime confound)

Found by the tron diff-triage workflow (153 commits ae82870a..0e50a645,
GitHub-only, 8 agents, adversarially verified) + a targeted check it
prescribed. Evidence chain (all verifiable without 3bda):
1. mwaitx.cpp at ae82870a ALREADY contains the startup line
   "INIT: Intel RTM (TSX) supported" (src/system/mwaitx.cpp:47 —
   byte-identical logging code at 198650bf).
2. The FULL archived runtron logs of the anchor runs contain ZERO
   rtm/tsx mentions (grep -c -i rtm = 0 on every instance log):
   2026-06-30_boot-default-clamped_gpt-oss-single/.../runtron/log.{0,1}
   and 2026-07-03_flat-freq_gpt-oss-single/sweep-results/.../log.{0,1}
   (read via andoria-15 NFS mount during the 3bda maintenance window).
3. Jul-14/15 checkerboard logs (build 198650bf, same lazy logging code)
   DO show the line (sweep-inventory + comparability audits, 07-17 am).
=> RTM/TSX was NOT active on 3bda before the 2026-07-13 16:27 reboot.
   The ENTIRE pre-reboot era — Jun-30 clamped baseline, Jul-3 flat
   (+13.3% gen), the 24h sweep, tron88, tier3 — ran tron's no-TSX
   fallback: SPIN+PAUSE waits. Everything since Jul-13 (Jul-14/15
   checkerboard, P4.3, ab22/ab23/ab25, all talos serving data) runs
   RTM+TPAUSE parked waits.

MECHANISM (tron's own t/t_mwaitx_cliff.cpp, added Jul-7 in PR-3137):
spin+pause bystander waiters hammer the shared wait-stats cache line
(~10 MHz/waiter vs ~1.3 MHz parked); measured on delphi-3c51: decode
13-30% SLOWER under spin+pause until RTM was enabled. Spinning is
clock-proportional work -> under spin+pause the whole decode loop is
clock-COUPLED (inflated frequency response, the +13.7%); parked tpause
waits are clock-insensitive -> the RTM-era true response is the +7-8%
we keep measuring. IF CONFIRMED, the decode-gap question INVERTS:
nothing was ever missing from CI — the checkerboard-era +13-15% decode
expectation was an artifact of a misconfigured host (RTM off), and
enabling RTM at the Jul-13 reboot itself delivered a large absolute
decode gain (to be quantified by ab26 cell A vs the Jul-3 102.6).

SHA CORRECTION (same workflow): the PR-3070 merge is 48e7740918 and
touches ONLY config/resource-map.yaml (+26/-5) — the "relocated
scheduler" is pure yaml pinning (Main -> die-B HT-sibling slot), not a
code change. 29924aa860 is an unrelated CI-workflow merge nearby on
main. Our "aa8" source build (checkout at 29924aa8) CONTAINS PR-3070,
so no measurement conclusions change — only the anchor label. Diff
also yields the candidate list for the small aa8-vs-0bf -3% serving
decode delta: the 56c map's internal structure (attention-via-HT-
sibling; active even at matched app-cores pins since each build loads
its own yaml), arena-allocator default flip 6590b12915 (testable:
TRON_USE_ARENA_ALLOCATOR=0, gate was +-2%), client-disconnect cancel
(serving-only, inert without disconnect churn). Everything else in the
range: verified no-op for gpt-oss decode (incl. all speculation-gated
code — inert; runtron metric semantics unchanged by 4a7af2c7e8, only
the "[Concurrency]" -> "[Load]" log prefix, a scraper hazard).

ab26 REVISED (v2 staged at /scratch/jhan/ab26/orchestrator26.sh via
andoria): arms A/B = {0bf, aa8} x {clamp-all, fast-all} x 3 reps under
today's RTM regime; arm D = 0bf + TRON_NO_RTM=1 x {clamp-all,
fast-all} x 2 reps = POSITIVE CONTROL recreating the June regime on
today's host. Per-cell power capture + per-cell wait-regime provenance
(grep engine banner into cellmap.txt). PREDICTIONS: A,B ~+7-8%
response, fast-all absolute ABOVE 102.6; D ~+13% response, absolute
LOWER. That outcome closes the decode-gap investigation with the
mechanism demonstrated live.

### 2026-07-18/19 — ab26 v2-v5 + ab27: the decode-gap investigation CLOSED

THE ARC (each step evidence-verified; kits/results under /scratch/jhan/
ab26/ [results_v2run, results_v3run, results_v4run, results=v5] and
/scratch/jhan/ab27/):

1) ab26 v2-v4 all lost one runtron instance per launch (48/48). Root
   cause (debug agent, file:line): the DOCUMENTED SYSTEM_CONFIG
   landmine — ~/.bashrc exports SYSTEM_CONFIG="--instance 1,2" and the
   engine applies env OVER argv (driver.cpp:166-172), so BOTH
   instances configured as instance 1,2 and flock-raced on
   libpos-slice-4 (huge.cpp:335, 8 tries x 50ms*2^n = 6.35s = the
   observed death gap). Jul-14/15 worked only because a long-lived
   shell had `unset SYSTEM_CONFIG`; the Jul-18 01:38 maintenance
   reboot revived the landmine (0/84 pre-reboot logs carry the env
   override line; 84/84 post-reboot do). "Active" hugepage files are
   flock-only — no stale-flag mechanism exists; the v3/v4 hugepage-
   hygiene and warm-store theories were wrong. FIX: unset in every
   orchestrator (v5+); durable fix = unset in delphi-3bda-setup.sh
   (user decision; also rotate the plaintext API keys exported by the
   same world-readable NFS dotfile).
   SIDE-BUG for the team: ci-runner.sh clear_hugepage_residue globs
   only libpos*/rinzler-* and misses the new slice-K-of-8 naming.

2) ab26 v5 (clean, 20/20 launches failed=0, 2 instances, warm store,
   per-cell regime provenance; runtron path, all-core clamp/fast
   toggle, 3 reps):
   | arm            | gen clamp | gen fast | gen resp | parse resp |
   |----------------|-----------|----------|----------|------------|
   | 0bf RTM        | 95.80     | 103.18   | +7.7%    | +17.7%     |
   | aa8 RTM        | 97.81     | 103.08   | +5.4%    | +15.6%     |
   | aa8 TRON_NO_RTM| 97.76     | 105.51   | +7.9%    | +16.3%     |
   THE RTM/WAIT-REGIME HYPOTHESIS IS REFUTED at real topology: the
   no-RTM control (banner-verified in both instances) shows NO clamp
   penalty and NO response inflation. The dramatic regime effect seen
   in v3/v4 was specific to the SYSTEM_CONFIG-broken single-instance
   topology (worth a note to the tron team, not our answer). The RTM
   log-absence discovery stands as FACT (June ran RTM-off) but is not
   the June-anomaly mechanism. Session power: 595 W pkg @ 3367 MHz
   (mixed arms), RAM 52 W.

3) PRECISE LOCALIZATION: across eras the FAST arms agree (June 102.6;
   v5 103.1-103.2; ab27 101.0-102.4) — the entire June-vs-now delta is
   the CLAMPED arm: June 90.3-90.6 vs today 95.0-97.8, i.e. clamped
   decode got ~5-7% FASTER despite today's clamp-all being harsher
   than June's boot-default clamp.

4) ab27 (allocator A/B; GitHub-verified differential: June builds
   compiled TRON_ARENA_ALLOCATOR_DEFAULT_ON=OFF, 198650bf+=ON;
   runtime-reverted via TRON_USE_ARENA_ALLOCATOR=0; 14/14 clean,
   provenance from the pos_heap_setup log line):
   | 0bf arm     | gen clamp | gen fast | resp  | parse resp |
   |-------------|-----------|----------|-------|------------|
   | legacy heap | 95.02     | 100.96   | +6.2% | +18.0%     |
   | arena       | 96.64     | 102.37   | +5.9% | +18.2%     |
   ALLOCATOR HYPOTHESIS REFUTED: legacy heap does NOT recreate June's
   slow clamp arm. (Arena is worth ~+1.5% absolute — nice, small.)

5) FINAL ATTRIBUTION: with software fully controlled (build, map,
   geometry, allocator, wait regime, spec, metrics, cache-coldness,
   path) and the bitfile unchanged (01.05.08.00 all eras), the June
   +13.3-13.7% decode response is an ERA-SPECIFIC HOST STATE in the
   clamped arm that did not survive the Jul-17/18 maintenance
   (candidates: BIOS/uncore/memory config, microcode; June-era
   turbostat has no uncore column so it is not reconstructable).
   Every recreation attempt on today's host converges to +5-8%.

== BOTTOM LINE (the original question, finally) ==
The flat-frequency fix's TRUE, REPRODUCIBLE effect on the current
stack (gpt-oss-120b tp4, 8 users) is:
  PREFILL/PARSE : +16-18%  (every harness, every era — rock solid)
  DECODE        : +5-8%    (serving AND runtron, all controls agree)
CI (talos) was always honest. The +13-15% decode expectation came from
June-era checkerboard runs whose CLAMPED baseline was anomalously slow
(era-specific host state + unlucky timing of the never-explained
config); it should be RETIRED as a target. Deployed tron112 remains
the right shape (ab25: fast-all costs +136 W for ~+1.3%).

### 2026-07-20 — ab28: prompt-length sweep on the CLEAN host — length-dependence CONFIRMED

The June-era observation "longer prompts => bigger boost" survives every
control. aa8 build, RTM on, SYSTEM_CONFIG scrubbed, warm store, 18/18
launches failed=0 (both instances), checkerboard 2x4=8u, all-core
clamp-all/fast-all toggle, 2 reps, per-cell power. Kit+results:
/scratch/jhan/ab28/. Ran 02:42-03:16 UTC, restored before the nightly.

| p=g len | gen clamp | gen fast | GEN boost | PARSE boost | PkgWatt clamp->fast |
|---------|-----------|----------|-----------|-------------|---------------------|
| 256     | 110.2     | 111.2    | +0.9% (noise) | +10.0%  | 530 -> 749 W        |
| 1024    | 96.1      | 102.8    | +7.0%     | +14.8%      | (~same band)        |
| 2048    | 81.7      | 89.9     | +10.1%    | +20.4%      |                     |
| 4096    | 59.1      | 67.0     | +13.4%    | +26.6%      | 601 -> 840 W        |

READINGS:
- The SLOPE of the June curve was real; only its LEVEL was inflated by
  the era host state (June p1024 +10.4% -> clean +7.0%; June p2048
  +15.1% -> clean +10.1%).
- Mechanism consistent with the wait-structure picture: decode attention
  is CPU work proportional to context, so the clock-sensitive fraction
  grows with length. Parse boost grows with length too (+10% at p256 ->
  +26.6% at p4096).
- HEADLINE QUALIFIER for all prior "+5-8% decode" statements: that is
  the p1024 figure. At p4096 the flat-freq fix is worth +13.4% decode /
  +26.6% parse — long-context workloads benefit substantially more.
- RAMWatt rises with length (50-51 W at p256 -> 65-66 W at p4096) —
  KV/attention memory traffic visible in the power channel.
- p256 gen absolutes are noisy (short cells); its +0.9% is within noise.

### 2026-07-20 — per-token decode model VALIDATED (from ab28; predictive for tuning)

time/token(ms) = FLOOR + SLOPE * avg_ctx(k), avg_ctx ~= prompt + gen/2.
Fits (aa8, RTM on, runtron path, 8u, all 16 ab28 cells):
  fast  : 8.27 ms + 1.052 us/ctx-token
  clamp : 8.36 ms + 1.370 us/ctx-token
VALIDATION: floor CLOCK-INVARIANT (8.27 vs 8.36, 1% apart across a 48%
clock change = the FPGA+wait component, exactly as the wait-domination
picture requires); slope scales x1.30 for x1.48 clock (attention partly
memory-BW-bound; RAMWatt 50->66 W corroborates); in-range predictions
+-3.6%; leave-one-out endpoints +-10%; model-derived boost curve matches
measured within ~1.5pp at every length; June 24h sweep confirms the
affine form holds to p8192 (~12k ctx, era-specific constants).
TUNING PREDICTIONS the model makes: clock/worker levers only touch the
slope term (+7% @1k -> +13-19% @4-8k); -1ms floor = +11% @1k / +7% @4k;
halving attention = +9% @1k / +28% @4k (the long-context lever); p8192
predicted ~47 fast / ~40 clamp (+19%) — testable when a long-context
config lands. Re-fit constants after engine changes (one 30-min sweep).
Full write-up + how-to-use: artifacts/delphi-flat-freq/docs/
flat_freq_explained.html section "A model that predicts generation
performance" (rendered-view link at top of file).

### 2026-07-20 — DIRECTIVE (user): repro insurance — never lose an era's host state again

Lesson: the July-3 clamped-decode anomaly is PERMANENTLY unexplainable
because no record of that era's host configuration exists. Three-layer
insurance now in force:

(1) STATE CAPTURE — /scratch/jhan/tools/sysconfig_snapshot.sh (read-only,
    ~520 diff-friendly lines): kernel cmdline (tsx/hugepages), BIOS ver +
    microcode, isst feature state + ALL 288 CLOS assocs, uncore min/max,
    governor + cpuidle states, RAPL limits, DIMM speeds, numa/hugepage/THP
    state, boot freq-service config, tron/platformd versions +
    resource-map md5, platformd config, instance envs (md5 + key lines),
    FPGA PCIe LnkSta (degraded link = silent perf loss), login-shell env
    landmines (SYSTEM_CONFIG etc.) + memlock, live engine provenance
    banners (RTM/allocator/pinning).
    WHEN: at the start of every experiment orchestrator (ab30+ MUST call
    it into results/); after every reboot; BEFORE and AFTER any announced
    maintenance; snapshots accumulate in /scratch/jhan/sysconfig_snapshots/
    and get archived to the notebook repo
    (artifacts/delphi-flat-freq/sysconfig-snapshots/).
    DIAGNOSIS = diff two snapshots.
    Baseline of record: delphi-3bda_20260720_045931.txt (tsx=on, uncore
    800MHz-2.5GHz, tron112 assocs, RTM on, arena on, memlock OK).

(2) PERFORMANCE FINGERPRINT (canary) — the July-3 anomaly lived in the
    CLAMPED arm, which nothing routinely measures (nightly only runs the
    production fast shape; its pass goals are far too loose to catch
    drift: Friday ran at 178% of goal). Ritual: after any reboot or
    maintenance, run ONE clamp-all + ONE fast-all p1024 cell (either
    harness, ~10-15 min incl. restore) and compare BOTH absolutes and
    the ratio against the trailing reference (currently: runtron
    ~96/103 clamp/fast, serving ~90/96; alarm at >3% drift on any of
    the four numbers). This catches a July-3-style baseline shift the
    same day it happens, with the snapshot diff ready to explain it.
    TEAM ASK (for the note + systems_test PR): add a clamped-arm canary
    + trailing-median regression bands (+-5%) to the nightly, replacing
    the static goals that a 6% drift would never trip.

(3) PER-RUN PROVENANCE (already standard since ab26 v5): every cell
    records failed_count, surviving instances, wait-regime banner,
    allocator banner, cached_tokens, per-cell power; SYSTEM_CONFIG/
    TRON_* scrubbed in every orchestrator. A result without provenance
    doesn't enter the record.

### 2026-07-20 — ab30 perfetto: the "serving coupling" mechanism NAMED — it's the work_queue engine orchestrator on clamped cores (mechanism D)

Setup: two 60s full-system sched traces under identical steady 8u decode
load (loadgen 3af6 -> instance ports 13000/13001, mongo-independent),
front-end cpus {1,2,73,74,+HT} clamped(2.7) vs boosted(3.9); perf
record/stat per arm; idle-baseline traces for contrast; power +
sysconfig snapshot per directive. Kits/results: /scratch/jhan/ab30/
(results_noload = quarantined first attempt: loadgen endpoint-format
bug; stale DONE-marker bug in orchestrator noted — clean REQ_*/DONE_*
at start in future kits). Traces:
/scratch/jhan/flat_freq_tests/20260720-1431*_ci-workload-profile-* and
20260720-1436*; IDLE-BASELINE dirs from the no-load attempt.

FINDINGS (analysis + independent adversarial re-derivation, exact match):
1. HTTP/SSE is NOT the coupling: DrogonIoLoop totals 46 us/token
   (~0.8 bursts/token, mean slice 57 us) and NO engine thread is ever
   woken by a front-end thread: 0 events in 47,472 tokens (clamped) and
   0 in 36,450 (boosted). Mechanisms A (sync handoff) and B
   (backpressure) REFUTED as instrumented; pure interference (C) also
   refuted (workers run 3.93 GHz with unchanged spin duty in both arms).
2. THE MECHANISM (D): each rinzler instance's `work_queue` thread — the
   forward-pass ORCHESTRATOR (perf callchain: work_queue::do_work ->
   full_scheduler::forward -> hw_prepare / prepare_hardware_matmul_job /
   write_tx/rx_descriptors / enqueue_hardware_matmul_job / moe_routing /
   save_k/save_v, between mwaitx waits on FPGA completions) — is
   confined by the process CPUAFFINITY taskset to front-end cores 1 and
   73, ~99% busy, spawned on first request (absent in idle traces).
   ~2.9 ms of every ~9.88 ms decode iteration's orchestration executes
   at the clamp: ~2.05 ms/iter MMIO/latency-bound (CLOCK-INVARIANT) +
   ~0.84 ms/iter genuinely clock-bound. Boost recovers ~0.25 ms/iter of
   busy time; the client-visible +1.2% (0.117 ms/iter) = the serial-path
   half; back-solving the serial 2.7GHz-equivalent gives ~0.38-0.4 ms =
   exactly the P4.3 Amdahl number. All three measurements (P4.3 toggle,
   ab28 model, ab30 traces) now close through one picture.
   mwaitx/tpause handoffs are invisible to sched — hence zero wakeups;
   trace analyses on this stack must not rely on block/wake signatures.
3. HISTORICAL echo: this is the same work_queue thread as the old-map
   prefill saga. PR-3070's map relocated the per-slice coordinators,
   but the work_queue EXECUTOR still inherits the front-end taskset on
   the deployed stack (0e50a645).
CAVEAT: the ms decomposition (2.9/0.84/0.25) rests on the root-only
perf profile; the sched+turbostat evidence is independently consistent
(duty 29.2%@2.7 vs 26.7%@3.9 solves to the same split).

RECOMMENDATION (tron team, concrete): pin/affine the per-instance
work_queue threads to fast-CLOS cores (or add cores 1,73+siblings to
the fast set — 2 physical cores, negligible power) => capture at least
the +1.2% decode with no other change. Bigger follow-on target: the
~2.05 ms/iter clock-invariant MMIO/descriptor path (~21% of the
iteration) — clock won't help it; batching/overlap might.

### 2026-07-20 evening — ab31/ab31b: the serial-share question ANSWERED (and the "2.05ms overlap prize" honestly retired)

Three probes under steady 8u serving decode (loadgen, mongo-independent):

(1) UNCORE PROBE, two context points (ab31 long ~1.5k ctx, ab31b short
~0.4k ctx): pinning mesh/uncore 2.5 -> 1.6 GHz costs decode -6.2% (long)
and -7.3% (short). Context-INDEPENDENT => the mesh-latency-sensitive
serial component sits in the FIXED token path (orchestrator descriptor/
doorbell traffic), NOT attention. ~0.6ms/token spill from a 56% mesh
slowdown => the pipeline overlap has limited slack.
OPS GUARDRAIL (new): uncore must run its full 0.8-2.5GHz range — a
BIOS/power-management uncore cap silently costs 6-7% decode. Uncore
state is in sysconfig_snapshot; treat any uncore change as a canary
alarm. (Caveat: short block = high request churn, not a pure low-ctx
decode measure; the 4x attention swing producing NO delta reduction is
still decisive.)

(2) PHASE PROFILE (ab31b phase.perf.data: 20s, 397,537 samples, 5
threads — capture landed on instance-0 only; ~4.1kHz/thread since -F is
shared): work_queue real-work duty 26.9% (~2.8ms/iter, matches ab30's
2.9). THE KEY RESULT: the folded-iteration profile is FLAT (<=4pp
modulation) and wq work is ANTI-phased with worker attention
(corr -0.32; only ~12% of wq work overlaps attention; quiet/FPGA zone
~55% of the period) => the orchestrator's work is SPREAD ACROSS THE
ITERATION, INTERLEAVED WITH FPGA COMPUTE — the engine ALREADY pipelines
job-prep under FPGA execution. The genuinely-serial head is small:
~0.4-0.5 ms/iter — i.e. the clock-bound serial path we already knew.
=> REVISION of the earlier "up to 2.05ms (~21%) overlap opportunity":
MEASURED, that work is already ~88% overlapped. The remaining serial
head ceiling is ~4-5% of the token, of which the pin fix captures the
clock-scalable ~1.2%; the residue (~0.2-0.3ms latency-bound head) is
the true remaining engine opportunity — real but modest.
Caveats: single-instance capture; period jitter +-1ms limits head
resolution below ~0.4ms; perf windows adjacent to (not inside) the
perfetto-traced windows.

(3) SURPRISES: (a) worker load GRADIENT within an instance — sampled
workers' duty 29.1/19.9/17.5/16.6% (core 25/0 carries ~1.5x) — work not
evenly shared; possibly interesting to the tron team. (b) THE COMM
MYSTERY SOLVED: thread comm = "<cpu>/?-work_queue", and TASK_COMM_LEN=16
truncates 3-digit-CPU names to "NNN/?-work_queu" (no trailing 'e') —
which is why global `grep -- "-work_queue"` found nothing while per-pid
enumeration worked. RULE: never grep engine thread names with full
suffixes; enumerate per-pid and match loosely ("work_queu").

ab31 v1 (aborted perf) + kits: /scratch/jhan/ab31{,b}/; analysis
intermediates /tmp/jhan_phase.txt etc. on 3bda.

### 2026-07-20 late — ab32: the pin fix TESTED AS IT WOULD SHIP — and it LOSES. Recommendation revised.

Question: does moving the two work_queue threads to idle FAST cores
(taskset to 7 / 79, tron112 clamp untouched) deliver P4.3's +1.2%?
Setup: 2x gpt-oss tp4, 8u loadgen (p~1k/g1024), 3 interleaved
stock/pinned pairs of 240s, placement verified per block (affinity
readback at set + psr under load mid-block and at block end), power
captured per block, zero request errors.

| rep | stock t/s/u (ttft) | pinned t/s/u (ttft) | pair delta |
|-----|--------------------|---------------------|------------|
| r1  | 97.48 (1.161s)     | 95.58 (1.264s)      | -1.9%      |
| r2  | 95.32 (1.028s)     | 94.45 (1.211s)      | -0.9%      |
| r3  | 96.87 (1.179s)     | 94.73 (1.262s)      | -2.2%      |
| mean| 96.56 (1.123s)     | 94.92 (1.246s)      | **-1.7%**  |

VERDICT: the migration form of the pin fix is a REGRESSION: decode
-1.7%, TTFT +11%, direction consistent 3/3. Prediction (x1.012)
REFUTED. Power/clock identical across arms (~732-739W, ~3650-3670MHz).

INTERPRETATION (fits everything we've measured): the work_queue
thread's stock placement on the front-end cores is LOCALITY-optimal —
it shares HT siblings and L2/mesh neighborhood with the Drogon/SSE
front-end threads it exchanges tokens with, and sits by the dev-cores.
Migrating it to a fast core buys +48% clock on ~0.84ms of clock-bound
work (~+1.2%) but pays MORE in handoff/mesh latency on the
latency-bound ~2ms (ab31: this path is mesh-sensitive; -6..-7% under
uncore cap). Clock gain < locality loss => net -1.7%.

REVISED TEAM RECOMMENDATION: the ONLY safe form of the work_queue fix
is the FREQUENCY form — exempt the front-end cores from the CLOS3
clamp (what P4.3 measured: +1.2%) or fold them into FAST_CORE_RANGES.
Do NOT migrate the thread off the front-end cores; thread affinity to
"better" cores makes it worse. (Config-level change, no code needed.)

BONUS FINDING — the provisioning lottery: tonight's two gpt-oss
provisionings, IDENTICAL host state by sysconfig-snapshot diff (same
boot, uncore healthy, same shapes), measured stock decode 102.29
(prov A, 20:12) vs 96.56 mean (prov B, 21:17): a -5.6% provisioning-
level shift. Prime suspect: platformd's instance<->unit/FPGA-pair
assignment shuffle (documented shuffle observed 19:48 and in the
snapshot env diff). n=2, but it brackets nightly-CI run-to-run
variance: each nightly rides one provisioning draw. Next kit should
capture rinzler cmdlines (devices/dev-cores/numa) during runs to pin
the mechanism.

KIT LESSONS (v3->v7, each root-caused live):
- `ps -p <tid>` cannot select a non-leader thread; use `ps -Lo` on the
  owning pid.
- An IDLE thread's psr never updates on sched_setaffinity — verify
  placement by `taskset -pc` AFFINITY READBACK; check psr only under
  load.
- Engine threads keep generic comm "rinzler" until they RENAME under
  real streaming load ("<cpu>/<instance>-<role>"); one idle completion
  does not trigger it => name-based discovery must run DURING a load
  block.
- /v1/models-ready != first-inference-ready: a cold 120B instance
  serves the model list minutes before its first token. PRE-WARM each
  instance port with a direct /v1/completions before timing anything.
- platformd shuffles instance<->unit mapping per provisioning: never
  hardcode front-end core numbers; classify work_queue threads by
  SOCKET and record stock affinity via readback.
- `ssh host 'setsid nohup x &'` never returns (wrapper waits in
  do_wait on the background child) and silently stalls multi-command
  launch sequences; use `ssh host 'setsid --fork x'`. And a pgrep
  guard self-matches if its own cmdline contains the plain script
  name — separate check-ssh from launch-ssh.
- Orchestrator waits must FAIL LOUD: v4 logged "warmup done" on a
  silent 400s timeout and ran an empty measurement block.

Artifacts: /scratch/jhan/ab32/results/ (loadgen_*.json = per-request
records; summaries in journal.log; placement.txt; per-block power;
sysconfig snapshot), aborted attempts archived as
journal_v*abort.log + results_v*_aborted/.
