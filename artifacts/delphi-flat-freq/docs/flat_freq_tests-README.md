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

Consensus RCA:
(i) Strict tron80 leaves the production per-token path clamped (TX 100%
    @2700, rinzler-main 80% @2700) -> nightly @8u decode cannot benefit
    from worker-only boost. [evidenced] This does NOT explain the
    3bda-vs-17cf cross-era gap (17cf's aux cores equally clamped+saturated
    under boot default; 3bda-tron80 dominates 17cf-clamped per-core).
(ii) The cross-era gap (93.3 vs 97.5-99) is most likely tron build
    ef720667. [leading hypothesis, to confirm]
(iii) Closed branches: shape-not-active (refuted), host variance as main
    effect (other models match across hosts within noise).

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
   Prediction if (i) holds: aux boost lifts nightly decode on BOTH hosts.
7. Ansible role change is CONDITIONAL on 6 (sol's amendment): do not
   deploy universal flat "regardless"; verify range semantics first.
8. Add provenance to nightly reports: shape readback, build, model config,
   spec mode, thread-placement summary.
9. Longer term: CPU-saturating nightly test with server-side prefill
   metrics separated from client TTFT.
