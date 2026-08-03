# Independent review of `simlot-S1-report.md`

**Review date:** 2026-07-30
**Reviewer:** Codex
**Source report reviewed:** `from-claude/simlot-S1-report.md`
**Source report SHA-256:** `C859E348ED62264105D98B365731634CF237D0CEC4EDE51E151BE2C117003A33`
**Runbook:** `from-claude/05-runbook-sim-lottery.md`, with the standing rules in runbook 04 §0
**Raw result set:** `delphi-3bda:/scratch/jhan/simlot/results/`

## Bottom line

I **agree with the narrow, pre-registered one-round primary classification: S1 is `NOT REPRODUCED`**. Independent recomputation from the 24 final `sim.json` files gives population CV **0.515282%**, `(max-min)/mean` **2.236836%**, and median within-draw block CV **0.647857%**. The frozen `CV <= 0.8%` rule therefore fires, regardless of the other two clauses.

I **do not agree that the report as filed is a fully verified or mechanistically conclusive result**. Its final 24-draw data set is clean, but the report omits two preceding aborted attempts; the current preregistration header was written after S1 data had already been seen; the advertised rank-stationarity test was not implemented; the IMC parser is dimensionally wrong; build provenance is incomplete and includes a stale hash sidecar; required adversarial/PAL/lab-log steps are absent; and the CI start timer was left disabled. The report also overstates what can be inferred from one session and from non-comparable memory metrics.

My disposition is:

- **Primary numerical verdict:** accept.
- **Branch-3 routing (`NOT REPRODUCED` -> L1, then L2, then L3 if still warranted):** accept.
- **“Stronger negative,” “different mechanism,” “none of five ingredients is sufficient,” and confirmed causal-exclusion language:** do not accept as written; make these provisional and narrower.
- **Runbook/workflow compliance:** incomplete.

## What I audited

I read the report, runbook 05, runbook 04 §0 and its method rules, the relevant S1 and later entries in `02-investigation-plan.md`, and the PAL log. I also inspected the final and rotated artifacts read-only, including:

- `journal.log`, `drawmap.txt`, all 25 final result directories, and the first attempt preserved in `results.prev.20260730180103`;
- all final `sim.json`, `sim.err`, `shape.txt`, `threads_psr.txt`, topdown, core-PMU, IMC, app-frequency, turbostat, and nuisance artifacts;
- `orchestratorS1.sh`, `stats_s1.py`, and `analysis_s1_stats.json`;
- the simulator worktree, source diff, parked binary, and their hashes;
- the post-run machine-state evidence and CI timer state.

All remote inspection was read-only. Once a new AB59 run was observed live at 21:03 UTC, I stopped using the DUT for this audit and confined remaining computation to the off-DUT host/shared artifacts.

## Agreements

### 1. Authorization, window, and final draw count

The measurement authorization is documented in the lab log. The final session ran 18:06–19:52 UTC, inside the reclaimable daytime window and outside the nightly hands-off interval. The final drawmap contains exactly one smoke plus **24/24 analysis draws**, all marked `OK`; every drawmap `gen` value exactly matches its corresponding JSON. There were no final-round exclusions or reruns.

### 2. The final result set is segregated from the aborted attempts

The earlier accepted smoke/draws are under `results.prev.20260730180103`; they are not referenced by the final drawmap or `stats_s1.py`. The second attempt aborted before producing a drawmap. Thus the final 24-draw statistic is not contaminated by those earlier files.

### 3. Shape and 1 GiB backing were consistently observed

All 25 final `shape.txt` files are byte-identical:

`7275021809522EEA21482929AE6BC14118380BD2099D1039410D4974A1EF3934`

They record Main CPU 24, 55 workers on CPUs 25–71 and 151–158, TX on 3–6, RX on 147–150, and both shared/rings as `hugetlb-1G`. Each archived `threads_psr.txt` has 66 lines (header plus 65 live threads) and shows the required Main, worker, TX, and RX names running on the expected CPUs. This is strong evidence that the intended named topology was live during every launch.

### 4. Capture/artifact liveness is materially better than the report demonstrates

The final set has 25 draw directories and 275 top-level per-draw files. Every launch has non-empty JSON, stderr, shape, topdown CSV, IMC log/data, app-frequency, thread snapshot, turbostat, and nuisance artifacts. The zero-byte `corepmu.log` and `topdown.log` files are empty wrapper streams; their actual CSV outputs are present and non-empty. The only systematic stderr warning is that the helper CPU list is empty.

The topdown raw event files report full running time, and the expected raw counters are present on the app CPU set. This supports the existence of the SEC1 input, although not all of the report's interpretation of it.

### 5. Primary arithmetic and decision

From the raw final JSONs:

| Quantity | Independent result | Filed result | Assessment |
|---|---:|---:|---|
| n | 24 | 24 | exact |
| mean `gen` | 98.800254 | 98.800 | agrees after rounding |
| min / max | 97.791 / 100.001 | 97.791 / 100.001 | exact |
| population CV | **0.515282%** | **0.515%** | exact after rounding |
| sample CV | 0.526364% | not stated | still below 0.8% |
| range / mean | **2.236836%** | **2.24%** | exact after rounding |
| median block CV | **0.647857%** | **0.648%** | exact after rounding |

`stats_s1.py` uses population standard deviation. The runbook did not explicitly say population versus sample CV, so the report should name the convention; the choice does not change the verdict.

A post-hoc 200,000-resample nonparametric bootstrap gives a descriptive 95% percentile interval of **[0.319%, 0.654%]** for population CV. Leave-one-draw-out CV ranges **0.459%–0.526%**. These are not substitutes for a pre-registered CI, but they show that the `0.8%` decision is not driven by one draw.

### 6. The ordered next-test branch is basically correct

The formal primary outcome selects runbook branch 3. The runbook's order—L1 file-backed hugepages, then L2 co-run, with L3 device/VFIO work only after the cheaper discriminators—is the right decision path. I agree with doing L1 next, provided its design and endpoints are frozen before any L1 pilot or analysis data.

### 7. Tail-share caveat

SEC2 is indeed degenerate: the reported fast/slow values are essentially identical around 0.997, and the simulator's “tail” is not anatomically comparable to tron's ~5% tail. The report is right not to use this endpoint as a discriminator.

## Disagreements and required corrections

### 1. The “before any S1 draw” preregistration claim is false

The journal records:

- attempt 1 at 17:41 UTC: smoke plus accepted draws 01 and 02, then a partial draw 03 and signal abort at 17:57;
- attempt 2 at 18:01 UTC: pre-draw abort at 18:02 because `ci-runner.sh stop` brought inference up and the trio did not stop in time;
- final attempt at 18:06 UTC: smoke plus the 24 analyzed draws.

The current `orchestratorS1.sh` says its header was frozen around 17:55 UTC, but the file's mtime is 18:06:17 UTC and its own comments describe defects learned from the first attempt. Therefore it was frozen **before the final 24-draw round**, but not before any S1 data. The report's §§3 and 4 should say this explicitly.

This does not overturn the primary result: its thresholds already existed in runbook 05, and the final round is fresh and separate. It does mean this should be described as a **pilot-informed protocol revision followed by a clean analysis round**, not a pristine preregistration. Any rule or caveat introduced after the first smoke/draws must be labeled as such.

### 2. Two aborted attempts are omitted

The report starts its execution narrative at 18:06, omitting the 17:41 signal abort and the 18:02 restore-safe abort. Both restores completed, and the first attempt's results were rotated cleanly, so this is a reporting-integrity issue rather than final-data contamination. Still, a complete report must list all attempts, explain why each stopped, and identify which artifacts were excluded.

### 3. Build provenance is not sealed by the cited commit

The worktree is at commit `0aa63bf09349d87245fe1f706dd6891de0b0f7ac`, but `src/tronsim.cpp` is modified by an uncommitted 18-line `MAP_HUGE_*` fix. The actual source-of-record hash is:

`70328EA64E9566407F43DDBE63F2E9A2CBBDC13DCB8303712A488E83B0BE9688`

The parked binary and current worktree binary match at:

`0F993D8C653FC252029DB0C380B47913CC657DD42C66B90BD8B1B7E25445B082`

However, `/scratch/jhan/simlot/bin/tronsim.sha256.short` contains the stale value `3295d593307a362b`, which does not prefix the executed binary hash. The report does disclose the hugepage source fix, but presenting the build as merely “worktree @ 0aa63bf09” is insufficient and potentially misleading. Record the dirty-source hash, full binary hash, compiler/build command, and script hash in the report; replace or explicitly retire the stale sidecar.

For reference, the inspected final analysis artifacts hash as follows:

- `orchestratorS1.sh`: `DFF6AD83B50E178AE80248151F21EE242CF227957312E91E6B298839A8F5F479`
- `stats_s1.py`: `7770385945CB8D0DA44090BE9FF86C28122273C5A829D0434B49582CCE6082D4`
- `analysis_s1_stats.json`: `EE07B7E6F285C49645E0A14DF18D795889E0DA6F332DBD4CDC679AE0D6C61136`

### 4. “Exact shape” needs two caveats

The expected named threads are present, but every live snapshot also contains one additional thread named simply `tronsim`, observed on PSR 144 in the inspected draw. That may be benign runtime machinery, but it should be explained before calling the process shape exactly identical.

Also, `threads_psr.txt` is a scheduling snapshot, not an affinity-mask proof. Runbook 05 specifically asked for an independent `taskset -pc <tid>` cross-check. No taskset output is archived. The defensible statement is that the emitted shape and live observed CPUs/names matched; exact affinity masks were not independently preserved.

### 5. Calibration and byte-identical argv are plausible but incompletely archived

The final script hardcodes a single argv and changes only the JSON output path, and all JSONs agree on `steps=110423`, seed, cycles, and backing. I therefore see no evidence of argv drift.

But there is no calibration transcript supporting the filed `96357` versus `110423` measurements, and there is no per-draw `/proc/<pid>/cmdline` or `argv.txt`. The report should distinguish “fixed by script construction” from “independently archived byte-for-byte.” Future runs should save the actual cmdline and its normalized hash per draw.

### 6. The registered rank-stationarity endpoint was not implemented

The runbook and header specify a **rank-stationarity** check using `blocks[]`. `stats_s1.py` instead compares each draw's first-half and second-half mean and counts an unregistered absolute shift greater than 1%. The filed “0 of 24” is therefore not the preregistered endpoint, and “never flip class” does not follow from it.

A direct rank-based audit gives:

- Spearman(first-half mean, second-half mean): **+0.8565**;
- Spearman(full-draw `gen`, first-half mean): **+0.9600**;
- Spearman(full-draw `gen`, second-half mean): **+0.9557**;
- median-split class changes between halves: **4/24** draws.

The data do show substantial rank persistence, which is reassuring. They do **not** support the filed “zero flips” formulation. Replace the stationarity paragraph with a clearly defined rank statistic, and freeze that operational definition before any subsequent round.

### 7. SEC3's parser and unit are wrong

`stats_s1.py::imc_read_bytes` scans both `imc_perf_raw.csv` and `imc_summary.csv`:

- in the raw perf CSV it skips the MiB count (below its `1e6` heuristic), takes the ~40-billion-nanosecond running-time field, and multiplies that by 64;
- in the summary CSV it takes the already-converted `bytes` field and multiplies it by 64 again;
- it then adds those heterogeneous values together.

It divides this aggregate by the JSON's fixed **24,000 full-run cycles**, even though the IMC capture is a 20-second window. The resulting quantity is not IMC read bytes per cycle.

Parsing only `cas_count_read` bytes from `imc_summary.csv` and dividing by the same constant happens, coincidentally, to preserve the draw ordering: the independently recomputed Spearman is still **rho = +0.69913** (20,000-permutation two-sided p approximately **0.00025**). That rescues the rank association, not the filed implementation or units. Recompute SEC3 from a defined capture-overlap denominator—preferably report fixed-window GiB/s, or count simulator cycles inside the IMC window—and regenerate the analysis JSON.

The report's explanation that “more cycles completed per second means more bytes read per second” is also a throughput explanation, not a bytes-per-cycle explanation.

### 8. SEC1's correlation is real in this data, but its interpretation is too strong

I agree that the raw-event computation produces approximately **rho = +0.806** with a permutation p-value at the 20,000-permutation resolution floor. I do not agree that this establishes a “different mechanism” or a scientifically comparable sign flip:

- runbook 05 says SEC1 classifies mechanism **if the lottery is reproduced**; the primary says it was not;
- sim `topdown-mem-bound / slots` and tron's reported “mem-stall share of cycles” have different definitions and denominators;
- a share metric is compositional, and the residual `gen` range here is only about 2.2%;
- no effect-size confidence interval is reported.

Treat SEC1 as an exploratory association within the simulator's small residual variation. Do not use it to classify the tron mechanism.

### 9. “More memory-bound” does not make this a stronger negative

The comparison “92.9–94.5% of slots” versus “24–29% of cycles” is not apples-to-apples. Even if both were valid measures of the same construct, saturating the simulator on one bottleneck could make it **less** sensitive to the launch-selected state rather than more sensitive. The direction of that sensitivity is an empirical question.

Accordingly, the statements that the null is “stronger than anticipated” and that the simulator “exceeds tron on the very axis” should be removed or recast as hypotheses.

### 10. The scope of the causal exclusion is overstated

S1 establishes that **this joint simulator implementation, at this configuration, did not show a tron-sized launch lottery in this session**. It does not separately prove that none of the five ingredients is sufficient, because:

- the memory footprint is about 46 GiB, not tron's roughly 210 GiB store-plus-KV scale;
- anonymous hugepages differ from hugetlbfs slice files;
- the tail occupies ~99.7% rather than ~5% of a cycle;
- yield/poll behavior and device traffic are stand-ins, not identical execution;
- the ingredients were not randomized one at a time and may interact.

Use the null to justify the registered discriminator ladder, not to close each ingredient individually.

### 11. The “tron-scale” and “exact decode anatomy” language conflicts with the fidelity table

The report's own table correctly lists material gaps, but its headline and interpretation repeatedly call the sim tron-scale and anatomically faithful. Given the 46 GiB versus ~210 GiB footprint, nearly whole-cycle “tail,” no hugetlbfs files, no FPGA/VFIO/DMA, and no engine load path, those phrases should be narrowed to **tron-derived thread/core topology and approximately tron-like cycle duration**.

### 12. The report's uncertainty claims are not demonstrated

The point estimate and post-hoc bootstrap support a tight one-round result. But “detects roughly >=1.5% comfortably” has no filed power calculation, and “excludes a tron-sized effect” is stronger than the documented decision rule. Report the observed margin and a stated CI model instead of an unreferenced detection threshold.

The current data make a 3–5% dispersion implausible for this session/configuration; they do not establish a timeless absence across machine epochs.

### 13. Required adversarial verification, PAL, and final lab-log bookkeeping are missing

Runbook 04 method rules require independent recomputation plus at least two hostile reviewers before reporting every result, and a PAL gate at each decision step. Runbook 05 also calls for the standard multi-agent workflow and lab-log/mirror bookkeeping.

At the time of this review:

- `02-investigation-plan.md` records authorization, build, defects, and the initial 17:41 launch, but not the final S1 result;
- `03-pal-consensus-log.md` ends with the AB58 Gate 6.5 material and has no S1 decision gate;
- no S1 eight-agent/two-hostile artifact bundle or synthesis is identified;
- the report does not state that the final result was mirrored.

This Codex review supplies an independent audit, but it is not a substitute for the required full workflow. Until that workflow is completed, mechanistic conclusions should be labeled **PROVISIONAL**.

### 14. Restore was only partially complete with respect to ownership

The S1 journal records the standing SST policy at start/end and a successful restore of three served models at 19:52. A separate 20:02 read-only snapshot corroborated CLOS0=224/CLOS3=64, rinzler@0–3 active, the runner inactive, and no S1 processes. I therefore agree that serving and SST were restored.

However, `ci-runner-start@delphi-3bda.timer` was **disabled/inactive with no next trigger**, contrary to the standing “timer re-arms at 14:00; never disable it” rule. The report's “restore verified” wording is incomplete. The timer condition must be coordinated and repaired after the currently active AB59 work, then verified without disrupting that run. The final S1 kit also did not record post-run free 1 GiB hugepage count or a broad process census.

## Explicit runbook deviations

1. The final protocol was frozen before the final round, but after earlier S1 smoke/analysis data.
2. Two aborted attempts are not disclosed in the report.
3. The committed source identity does not describe the dirty source used to build the parked binary; the short hash sidecar is stale.
4. The independent taskset affinity check was not archived.
5. No per-draw actual argv record was archived.
6. No calibration transcript was archived.
7. The registered rank-stationarity endpoint was replaced by an unregistered >1% half-shift rule.
8. SEC3 was implemented with an invalid parser and denominator.
9. The final S1 result has not been appended to the authoritative lab log, passed through PAL, or documented as completing the required adversarial workflow.
10. The CI start timer was not re-armed.
11. “Nothing else running” is not auditable from the per-draw artifacts; nuisance files contain uptime/memory but no broad process census.

## Limitations of this review

- I did not rebuild the simulator or mutate the worktree; source-to-binary provenance is inferred from the matching current worktree/parked binary plus timestamps and hashes.
- I did not observe the run live. Thread topology is based on its archived `ps` snapshots; affinity masks were not preserved.
- The bootstrap interval and rank-stationarity recomputation are post-hoc audit diagnostics, not preregistered inferential endpoints.
- Current machine state after 21:03 UTC belongs to the live AB59 follow-up and cannot be used as an S1 restore snapshot.
- Authorization is assessed from the written local record; I did not independently reconstruct the originating message thread.

## Recommended next steps

1. **Correct the S1 report before treating it as the record.** Add all three attempts, exact hashes, population-CV convention, the corrected stationarity result, a corrected SEC3 analysis, and the CI timer deviation. Narrow the causal language as described above.
2. **Complete the standing verification workflow.** Run the remaining independent/hostile checks off-DUT, append the result to `02-investigation-plan.md`, add the PAL decision, and mirror the finalized documents.
3. **Restore ownership safely.** After the live AB59 activity completes and the box owner agrees, re-arm/verify the CI start timer and capture the full standard snapshot. Do not change state during the live run.
4. **Replicate S1 hours apart before relying on causal exclusions.** Keep the current label as “one-session, pre-registered-threshold `NOT REPRODUCED`.” A second 24-draw round is cheap insurance and is required before stronger “confirmed” language under method rule 3.
5. **Proceed to L1 only under a newly sealed protocol.** Freeze the exact file-backed footprint, allocation/touch policy, endpoints, exclusions, hashes, and uncertainty analysis before any pilot. If L1 is tight, still execute the registered L2 co-run discriminator before concentrating the residual explanation on FPGA/VFIO.
6. **Harden the next kit's audit trail.** Per draw, save the actual cmdline, PID/start time, `taskset -pc` masks, broad process census, hugepage state before/during/after, capture return codes, and an artifact manifest. Seal source, binary, orchestrator, and analyzer hashes before launch.

## Final assessment

The clean final data answer the narrow S1 question: **this simulator/configuration did not reproduce the tron-sized launch dispersion in the observed 24-draw session**. That is a useful negative and a valid reason to enter branch 3.

The evidence does **not** yet support the report's stronger mechanistic exclusions or “confirmed” tone. After the statistical corrections, provenance repair, adversarial/PAL completion, ownership restoration, and preferably an hours-apart replication, S1 can become a strong discriminator rather than an overextended one-session null.
