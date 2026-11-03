# Codex review of CME-plan.md

**Short version.** Re-review complete through section 13.1. All comments, R1 through R14, are resolved. I have no further comments on this version.

**Final reviewed plan:** SHA-256 `53ad8177da55e043078420dbc6ac5d983c7f5d33e12f308180ce79c7aaa9705e`, including section 13.1. The earlier signoff covered SHA-256 `39fedcde1c1147eb9dae3974fe1085f7559dfeb7b5d0adcc353b07168234c8d4`, through section 10.1. The final disposition at the end supersedes all earlier open statuses.

Reviewed the 325-line draft with SHA-256 `679c8fce9a4729d74be8760d139ea00846fc04cc40829dfa2fc4fcc66894878d` and the corresponding local source files. Line references below refer to that draft. Please append responses to `CME-plan.md`, as its introduction requests. I will review the revised text and any supporting changes, then update each comment's status here.

Words used here follow the plan: CME is the Compute Matrix Engine, DSU is the two-core cluster, and PMU is the hardware performance counter unit. A fold combines loaded values with exclusive-or (`EOR`). A counter is multiplexed when it measures only part of the requested interval.

## Round 1 — original comments (current status is in round 2 below)

### R1 — P1: The read comparison also changes the fold's dependency cost

**Plan:** lines 89, 118–122, 258–260. **Status:** open.

The statement that the fold does not slow the stream is unsupported. An instruction's issue rate does not remove dependencies between successive updates of the same accumulator. The local Arm LLVM scheduling model gives streaming `EOR` a latency of 4 cycles. The four-vector reader has four accumulator chains, while the single-vector reader has only two. [refs/AArch64SchedC1Nano.td:430,1927–1932; cme_kern.S:110–125,204–211]

The model therefore implies these recurrence limits, before other costs:

| Reader | Loaded bytes per loop | EOR instructions per loop | Independent accumulator chains | Recurrence cost (est.) |
|---|---:|---:|---:|---:|
| Four vectors per load | 1,024 B | 16 | 4 | 16 cycles/KiB |
| One vector per load | 512 B | 8 | 2 | 32 cycles/KiB |

These are model estimates, not Asimov measurements. They show why a bandwidth difference cannot be assigned solely to load width. The core reader has no equivalent fold. Jacob's four-vector stream does have the same four fold chains, so that narrower comparison remains useful. [bandwidth.c:79–96; /scratch/jgeldbach/agent-builds/cme-perf/wt3/presilicon-perf/cme-perf/bench/stream.S:43–58]

**Requested change:** remove the no-cost assertion. Either define a load-only or matched-fold control for the width question, or describe the results as throughput of these complete kernels and leave the cause unresolved. Do not call an unvalidated folded stream the CME's load bandwidth ceiling.

### R2 — P2: The round-trip difference does not isolate memory latency

**Plan:** lines 27–29, 85, 113–117, 250–253, 293–296. **Status:** open.

The chase executes `LD1D` then `LASTB`. The control replaces `LD1D` with `DUP`. It does not remove a separately measured component of the chase. The instructions use different execution resources, and no supplied calibration establishes equal non-memory costs. Labeling the subtraction an estimate does not establish that model. [cme_kern.S:65–90; refs/AArch64SchedC1Nano.td:1857–1860,2382–2388]

**Requested change:** retain both raw timings. Name any subtraction “chase minus DUP/LASTB control.” Remove the guaranteed “floor” and “memory part” claims unless a source or calibration supports them. Treat the expected approximately 20 ns offset at other cache levels as a hypothesis, with the measured paired rows as its test.

### R3 — P1: The chosen counters cannot identify all advertised cache levels

**Plan:** lines 92–95, 137–139, 254–255, 302–305. **Status:** open.

`CME_L1D_CACHE_REFILL_RD` counts demand-load refills per cache line. `CME_BUS_REQ_RD` includes read transactions and snoop requests/responses. Neither identifies whether the cluster cache or the mesh supplied a line. A latency step alone does not prove that distinction. The reference manual provides `CME_L1D_CACHE_REFILL_INNER` (0x327D) and `..._OUTER` (0x327E) for refills from inside and outside the cluster. [Arm C1-SME2 TRM 107831_0103_07, chapter 12; /scratch/jhan/arm-txt/c1-sme2-trm.txt:4219–4221,4302–4312]

**Requested change:** either plan a suitable source counter/control, or limit attribution to observed L1 demand refills and label lower-level assignments as hypotheses. Specify the evidence required to accept the flushed CME rows as outside-cluster accesses. A successful flush instruction and an expected-looking latency are not that evidence by themselves. Preserve the existing distinction between OCM retaining its data and DRAM-backed lines being invalidated from the mesh cache.

### R4 — P1: Define acceptance rules for counter failures and partial measurements

**Plan:** lines 261–263, 287–289, 297–301. **Status:** open.

The present sanity checks can accept unusable counts. The counter reader substitutes zeros after a failed read while leaving the group marked open. Reset/enable/disable errors are unchecked. The group does not request enabled/running times, so the output cannot establish whether it measured the whole interval. Similar CME and CPU cycle counts do not detect a shared reduction in counting time. [common.h:235–240,290–314]

**Requested change:** define the run acceptance checks and any required implementation work: event availability, successful counter operations/read, expected event count, and full counting coverage or explicit scaling. Treat missing or invalid counters as **Insufficient data for cache attribution**, while retaining independently valid timing. Use the warm L1, round-trip, and flushed large-buffer rows as event sanity controls. Describe `CME_CYCLES` as CME clock cycles, and qualify its comparison with CPU cycles by their clock rates and measurement windows. [Arm TRM text:4060–4062]

### R5 — P2: Recompute the run budget from the actual command list

**Plan:** lines 267–273, 312–314. **Status:** open.

The stated components already sum to `0.10 + 0.25 + 0.05 + 0.03 + 40 × 0.014 = 0.99 s` (est.), before omitted work. They cannot support a total of 0.5 s (est.). Expanding phase F with OCM present gives the following exact work counts. [run_asimov.sh:228–264; latency.c:124–166; bandwidth.c:206,262–270]

| Item | Computed count |
|---|---:|
| Benchmark commands | 30 commands |
| Additional mesh-counter helper launches | 13 launches |
| Benchmark and helper launches combined | 43 launches |
| Timed bandwidth traffic, including OCM and both copy directions | 1,889,009,664 B |
| Untimed bandwidth warm-up traffic | 673,284,096 B |
| Register-control hops, including warm-ups across nine latency commands | 2,359,296 hops |

The plan currently says approximately 1 GB of bandwidth traffic. It also documents the round-trip rows only for the small DRAM file, although `main()` runs them for every `--cme` latency invocation. [latency.c:main; plan section 4.1]

**Requested change:** compute counts from the script and apply explicitly labeled timing assumptions. Include warm-ups, repeated round-trip controls, initialization/chain building, flushing, and counter helpers, or identify their costs as unmeasured. Update the total and wall-time conversion consistently. A 14 ms assumed cost over 43 launches is already 0.602 s (est.). Do not present that assumption as a measured launch cost.

### R6 — P2: Copy has twice the working set of read or write

**Plan:** lines 88, 125–128, 258–260. **Status:** open.

The size argument is per buffer. Copy allocates a source and a destination. Therefore a 48 KiB copy uses 96 KiB of data, beyond the 64 KiB CME L1. A 160 KiB copy uses 320 KiB, beyond the 256 KiB DSU L3. The table currently assigns these sizes to cache levels as if every kernel touched one buffer. [bandwidth.c:206,209–221]

**Requested change:** state per-buffer size and combined active bytes for each kernel. Use the combined working set when discussing cache capacity. Describe the levels as intended regimes until counters or measurements support them.

### R7 — P2: Small bandwidth rows include streaming entry/exit on every pass

**Plan:** lines 108–112, 258–260, 315–317. **Status:** open.

The timed C loop invokes a kernel once per pass and once per OCM segment. Each invocation saves registers, enters streaming mode, leaves it, and restores registers. A 16 KiB row with 256 passes therefore pays 256 entry/exit pairs per timed repetition. The warm-up absorbs the first-use trap, not these recurring costs. [bandwidth.c:177–195,262–273; cme_kern.S:37–57; run_asimov.sh:249–256]

```text
Timer start -> [enter -> stream -> leave] x passes -> Timer stop
```

**Requested change:** define the reported bandwidth as complete-call throughput. Before attributing a small-buffer result to instruction width or the store issue anomaly, require a control that measures transition cost or keeps several passes within one streaming span. Alternatively, leave those causes unresolved. Increasing the number of existing C-level passes does not amortize the per-pass transitions.

### R8 — P2: Correct the comparison scope and streaming-state description

**Plan:** lines 9, 69–75, 101–107, 256–257. **Status:** open.

- “Every CSV row has a C1-Nano twin” excludes the round-trip control, the added 160 KiB and 1 MiB sizes, and the single-vector rows. The plan's own table lists those exceptions. Define the exact matched subset.
- Use the current run's phase B rows for the primary OCM comparison. Run 1's 18.8–23.2 ns rows had measured prefetch contamination and a different fresh-chain policy. Keep them as historical context. [results/membench-jibin-001/README.md, “Reading the numbers”]
- The historical CME numbers are reference points, not an expected equality across images. The source package records RTL `a10181848`, SCP `scp-v0.40.0`, and Linux 6.18.36. Run 1 used a different firmware/image. Record these differences beside cross-run comparisons. [/scratch/jgeldbach/cme-perf-for-jibin/03-code-and-how-to-run.md, “Recipe used so far”; results/membench-jibin-001/README.md]
- A system call clears streaming mode. A signal handler starts outside streaming mode, but normal signal return restores the saved streaming state. Signals still contaminate elapsed time. Correct “either drops the state,” and distinguish an intended uninterrupted span from a guarantee that the code cannot receive a signal. [Linux documentation: https://docs.kernel.org/arch/arm64/sme.html#system-call-behaviour and https://docs.kernel.org/arch/arm64/sve.html#signal-return]

**Requested change:** update these claims throughout the plan. No additional hardware run is needed.

## Review scope and verification

- Read the plan, kernels, functional self-test, timing/counter code, and phase F command block.
- Checked the local Arm manual extracts, Arm LLVM scheduling model, Jacob's source package, and the Linux streaming-state documentation.
- Expanded phase F with stub commands to count its work. No benchmark or hardware access occurred during this check.
- The previously reported QEMU and CRB test passes were not independently rerun in this review. They remain author-reported functional checks, not performance validation.
- Waiting for the author's response in `CME-plan.md`. This review is not complete while any comment remains open.

## Round 2 — review of the author's section 8 response

Reviewed the 430-line revised plan, SHA-256 `8e4d94a9b9eea3dfdbab5e16201c01268790ade8a70eb801ebd040051b68bff6`, and supporting source changes. References in this section use that revision's line numbers. The revised dry-run was executed locally. The updated functional-test passes remain author-reported.

| Comment | Status | Result |
|---|---|---|
| R1 | Closed | The read kernels now have one accumulator per load register. The plan reports whole-kernel throughput and names the remaining differences. |
| R2 | Closed | The control and derived difference are named correctly. One residual causal sentence is listed under R8's consistency corrections. |
| R3 | Open | The new events help, but the mesh-count acceptance rule uses the wrong measurement interval. |
| R4 | Open | Failure checks are improved, but coverage is cumulative rather than per row. |
| R5 | Open | The budget is substantially corrected. Segment calls and the meaning of helper timing still need correction. |
| R6 | Open | The doubled copy working set is documented. The 2 MiB copy row still exceeds the available mesh cache. |
| R7 | Open | The added control bounds cost but cannot be subtracted as an exact overhead. |
| R8 | Open | Several original claims remain in the revised text and supporting documentation. |
| R9 | Open, new | The CME translation-cache claim conflicts with the supplied Arm manual. |

### R3 follow-up — whole-process mesh counts cannot validate one miss per timed load

The revised acceptance rule still requires `hns_cache_miss_all` to rise by approximately one per timed load. However, `cmncount` enables the mesh counters before starting the child and disables them after it exits. Its total includes buffer initialization, construction of three chains, two warm-up walks, both timed walks, flushing, and process traffic. The 8 MiB row has 131,072 loads per timed walk, but there is no mesh sample for either individual walk. [CME-plan.md:104–110,325–328; cmncount.c:356–366; latency.c:143–159]

```text
Mesh counting: [setup -> warm-ups -> timed walks -> teardown]
Chase timing:                       [walk] [walk]
```

**Requested change:** remove this per-load mesh acceptance rule unless the mesh interval is narrowed or a justified aggregate/control method is specified. The simpler resolution is to use `REFILL_OUTER` for outside-cluster evidence and retain **Insufficient data** for precise SLC-versus-DRAM attribution. Whole-process mesh counts can remain corroborating traffic evidence. Do not reject the whole CME event set merely because this unsupported mesh ratio fails.

Also describe INNER/OUTER as refill-source events. The manual does not define them as demand-load-only counts. INNER identifies a cache inside the cluster, not uniquely the DSU L3. Qualify cache-hit assignments accordingly, including possible prefetch contributions. [Arm TRM text:4302–4312]

### R4 follow-up — reset does not reset the coverage times

The new checks compare lifetime enabled/running times after resetting only the event counts. Linux retains those times across `PERF_EVENT_IOC_RESET`. For example, a row with 100 ns enabled and 50 ns running is correctly rejected. A following fully counted 100 ns row produces totals of 200 ns enabled and 150 ns running, and is incorrectly described as partially counted. [common.h:299–320; Linux 6.18.36 source, /scratch/jgeldbach/agent-builds/dpa-d137/linux-6.18.36/kernel/events/core.c:5978–5985,6168–6173]

**Requested change:** compare interval deltas and refresh the baseline after rejected rows too. Verify a partially counted row followed by a fully counted row. Alternatively, explicitly choose conservative invalidation of the whole group's later output and stop describing the coverage as per-row. The former preserves useful later measurements.

### R5 follow-up — count OCM segments and separate helper lifetime from launch cost

I reproduced the updated 32 commands, 14 helpers, byte totals, and 1.258 s estimate with the dry-run. Two details remain:

- The estimator counts one kernel call per bandwidth pass. `pass()` invokes a kernel for each OCM segment. The all-five read contributes 24 more calls than counted, and the all-five write contributes 108 more. The current command list therefore has **31,173 bandwidth kernel calls**, not 31,041. This changes little time, but the table labels the count exact. [est_chip_time.py:bandwidth_cmd; bandwidth.c:177–195]
- `helper_elapsed_ns` measures the helper from entry to `main` through its work, including the child. It excludes the helper's own executable loading and does not isolate process startup. The original script already explains this limitation. Remove the claim that it will measure the per-launch assumption. State separately which setup/counter costs remain unmeasured or are covered by a deliberately broad allowance. [CME-plan.md:350–353; cmncount.c:241; run_asimov.sh:41–49]

**Requested change:** correct the segmented-call count and the timing claim. Keep the existing explicit estimate labels.

### R6 follow-up — the 2 MiB copy working set exceeds unlocked SLC capacity

The revised table puts the 2 MiB copy row in the SLC regime. That row touches 4 MiB across its two buffers. With five 256 KiB OCM regions locked out of a 5 MiB SLC, the available cache is 3.75 MiB. Thus even the capacity model does not fit that working set. [CME-plan.md:145–152; README.md, OCM definition; RUN2-PLAN.md and README.md, SLC capacity discussion]

**Requested change:** mark this copy row as beyond the nominal unlocked SLC capacity, with actual service unresolved. Bandwidth rows have no per-kernel refill counters, so the chase counters cannot directly establish their service source. No extra test row is required.

### R7 follow-up — use the 1 KiB control as a bound

The plan now says the control may be “subtracted” before assigning a result to width or the store path. The control contains 1 KiB of data movement plus folding and loop work. Its cost is not an exact measurement of entry/exit overhead. [CME-plan.md:168–173]

**Requested change:** keep the control as an upper-bound/sensitivity check. If it is negligible relative to a 16 KiB call, state that limited conclusion. Otherwise leave the overhead unresolved unless a matched calibration is added. Subtracting it does not establish the cause of a bandwidth difference.

### R8 follow-up — remove remaining contradictory claims

These are consistency corrections to the accepted scope and wording, not requests for more experiments:

| Location | Remaining claim | Correction |
|---|---|---|
| CME-plan.md:77–79 | A signal drops streaming state | Use the restored-on-signal-return wording already accepted in section 8. |
| CME-plan.md:114–122 | CSV and counter plumbing are unchanged; only the engine differs; historical rates directly compare | State the added coverage column, new counter set, and kernel/control differences. Keep the image-qualified historical comparison. |
| CME-plan.md:128–130 | The comparison with the core proves most of the CME hop is not the cache | Remove this causal conclusion. The control has not separated those costs. |
| CME-plan.md:369–371 | Unverified events are 0x3280 and 0x3268 | Name the implemented 0x327D and 0x327E events. |
| README.md:8,323; run_asimov.sh:41–54 | Old 0.5 s phase-F / 2–2.5 s suite budgets | Update to the new estimate and its uncertainty. |
| run_asimov.sh:232–236 | Every row has a twin; old CME event set | Use the matched subset and current refill-source events. |

### R9 — P2: Distinguish demand-load translation from prefetch translation

The plan says the CME has its own translation lookaside buffer (TLB, a cache of address translations) and suggests its miss cost affects demand chase loads. The supplied manual says load/store addresses arrive already translated by the host core. The CME's own TLB belongs to its prefetcher. [CME-plan.md:389–392; Arm C1-SME2 TRM chapter 5, /scratch/jhan/arm-txt/c1-sme2-trm.txt:2040–2053]

**Requested change:** keep the valid 4 KiB-versus-2 MiB page-size caveat. Explain the host-core demand translation separately from the CME prefetcher's translation requests. Remove the unsupported inference about a distinct CME demand-TLB miss cost.

Waiting for the next response in `CME-plan.md`. R1 and R2 need no further work beyond the explicit consistency cleanup above.

### Round 2 addendum — the new R4 regression test needs initialized state

The interval-delta implementation now passes an independent host probe with controlled counter records: partial coverage, full coverage, control-operation failure, then full coverage. Each valid later interval is accepted. This probe performs no hardware counting.

Before claiming `perf_cov_test.c` as verification, initialize its `struct perfgrp g` and `extra` groups, or initialize all coverage state in `perf_open_set`. The new baseline fields are otherwise indeterminate for these stack objects. Production `latency.c` uses a static, zero-initialized group. [perf_cov_test.c:26–30; common.h:256–280,313–316]

The crowded-row assertion should require actual partial coverage and the `multiplexed` reason. It currently accepts unrelated errors as success and can pass without enough groups to exercise multiplexing. An unavailable setup should be an explicit skip, not PASS. The recorded crowded/quiet output should establish which path was tested.

## Round 3 — review of the author's section 9 response

Reviewed the 490-line plan, SHA-256 `35d2e8b7f9fd3a970961dd958f7604d438af9b7490bdc20c83b97292780572e1`. R7 and R9 are now closed. R1 and R2 remain closed. The main parts of R3 through R6 are fixed, with these final follow-ups:

- **R3 — remove the unsupported demand-only interpretation (plan lines 107–112).** The whole-process mesh-count correction is accepted. However, the replacement paragraph still says the refill-source events are read as demand refills because the chain is random. Repeated random chains can be learned, as the suite's own run 1 evidence explains. Keep these as **refill-source counts**, with demand-only behavior a hypothesis if discussed. Delete the assumption that randomness proves it. No new events or experiment are required. [README.md, fresh-chain definition; latency.c:repeated-walk path]
- **R4 — finish the regression-test correction in the round 2 addendum.** The production interval calculation passes my controlled-record test. `perf_cov_test.c` still uses uninitialized stack groups and does not require the crowded failure to be `multiplexed`. The new section 5 PASS claim cannot replace those corrections. Initialize state, check the intended failure, and record the corrected test outcome or mark it unverified.
- **R5 — distinguish the helper's loading from the child's loading (plan lines 386–389).** The corrected 31,173 kernel-call total is verified. `helper_elapsed_ns` excludes loading the helper before its own `main`. It **includes the child's loading**, because `run_child()` times from before `fork()` through `execvp()` to exit. Remove “or of the child before main.” Neither lifetime isolates launch cost, so keep that remaining caveat. [cmncount.c:174–196,200–209]
- **R6 — remove the chase-to-bandwidth attribution exception (plan lines 163–165).** The capacity correction is accepted. Delete “unless a chase row at the same footprint says otherwise.” A random dependent chase and a sequential read/write/copy stream have different access and prefetch behavior. Their shared footprint does not make the chase counters a measurement of the bandwidth kernel's service source. Keep the capacity-based labels as hypotheses.
- **R8 / R3 — finish the repeated wording.** README lines 58–59 still say a signal drops streaming state, contradicting the corrected later paragraph. README's CME chase row (line 173) still promises identification of all cache levels. Plan lines 171–173 still assert that flushed CME rows establish DRAM service. Use the already accepted wording: signals restore state on return, refill counts identify sources inside/outside the cluster, and the flushed row is an intended DRAM reference whose exact outside-cluster source remains unproven. This final consistency check leaves R8 open until its remaining glossary sentence is corrected.

Verification in this pass: the dry-run reproduces 32 phase-F commands, 14 helper launches, and 31,173 bandwidth kernel calls. `sh -n run_asimov.sh` succeeds. The controlled-record coverage probe accepts full intervals after both partial coverage and a control-operation failure. No hardware benchmark was run by this review.

Waiting for the next response in `CME-plan.md`.

### Section 10 response checked — only the R3/R8 consistency bullet remains

The updated counter test initializes its state, requires the intended failure, and reports unavailable setups as skips. R4 is closed. The helper/child timing description and bandwidth attribution exception are corrected. R5 and R6 are closed. The revised demand-refill paragraph is accepted.

The final R3/R8 bullet was added while section 10 was being written. It still applies to these three locations:

1. README's streaming-mode definition still says a signal drops the state.
2. README's CME chase row still says its counters establish which of all four cache/memory levels served the load.
3. The plan's “Flush rules carry over” paragraph still presents DRAM service as established, instead of the intended reference with the stated evidence limit.

Use the corrected wording already present elsewhere. No further implementation or testing is requested.

## Disposition through section 10.1 — no further comments on that version

Checked section 10.1 and the actual plan/README edits. The remaining signal-state and cache-attribution statements now match the agreed limitations. R3 and R8 are closed. All nine comments are resolved.

The final review verified the command/count calculation, shell syntax, counter interval recovery with controlled records, and the supporting source changes. The latest controlled-record probe passed: partial coverage was rejected, the next full interval was accepted, a control-operation failure was rejected, and the following full interval was accepted.

The author's QEMU and CRB results are recorded in the plan. They were not independently rerun here. CME performance, hardware event behavior, and OCM behavior remain unverified on the target emulator, as the plan explicitly states. This completes the requested plan review, not target performance validation.

## Round 4 — section 11 and the sparse-chain change

Reviewed the 582-line plan and its supporting implementation on 2026-11-02. The new counts reproduce: 100 commands and 166 launches for the suite. The estimator reports 4.111 s (est.) under its existing assumptions. The following comments concern the new sparse experiment.

### R10 — P1: Dense refill counts do not establish that sparse prefetching is absent

**Status:** open. **Locations:** plan lines 535–543, 565–576; README phase B/F rows; `latency.c` sparse description.

The claim that four prefetched lines per page would add 0.06 refills per dense hop is not established. The dense chain eventually reads every line. A prefetch can replace a later demand refill instead of increasing the total. Those same prefetched lines could be wasted by a sparse chain. Dense counts near one refill per hop therefore do not rule out the first-touch behavior discussed in the CRB caveat. [plan lines 572–575; `latency.c:build_cycle`]

The proposed CME check also counts refill sources, including prefetch fills. One outer refill per hop does not prove that every demand waited for an outside-cluster refill. The README's “without prefetched members” claim exceeds what the selected events can establish. This repeats the evidence limit accepted under R3. [plan lines 107–112, 565–567; README lines 174, 185]

**Requested change:** describe sparse chains as an experimental mitigation for reuse of adjacent lines. Remove the exclusion of Nano first-touch prefetching and the guarantee that no member was prefetched. Keep the paired rows and counters as consistency checks. Label the specific prefetch explanation for run 2 as a hypothesis unless direct evidence distinguishes it. If demand-only latency remains an acceptance claim, name the additional demand/prefetch measurement that would establish it. Otherwise state **Insufficient data for demand-only OCM latency** when that distinction matters. No additional event is required merely to narrow the claim.

### R11 — P2: Account for short-call costs and define a usable acceptance tolerance

**Status:** open. **Locations:** plan lines 549–553, 565–567; `latency.c:timed_walk`, `print_bracket_overhead`; `cme_kern.S:SM_ENTER`, `SM_LEAVE`.

The empty bracket measures the interval between two clock reads. A timed CME chase also saves registers, enters streaming mode, initializes its predicate, exits streaming mode, and restores registers. The new 64-hop pass amortizes those costs over only 64 loads. The existing 65,536-hop register control does not measure their contribution to a 64-hop call. The timer-only percentage cannot bound the complete overhead. [latency.c lines 140–159, 205–248; cme_kern.S lines 39–77]

The dense all-five row's two-pass spread is also unsuitable as the acceptance tolerance for seven sparse passes. In run 2 that spread is 0.007 ns/hop on CPUs 2 and 8, 0.025 ns/hop on CPU 6, and 0.057 ns/hop on CPU 4. Even a 1 ns timestamp step contributes 0.015625 ns/hop to a 64-hop row. One counter event contributes 0.015625 refills/hop. These short rows need an explicit treatment of timing uncertainty and counter granularity. [run 2 `latency-ocm-all5-cpu{2,4,6,8}.csv`; 1/64 calculation]

**Requested change:** bound the fixed whole-call cost, or label each sparse timing as complete-call elapsed time divided by its hop count and leave the pure per-hop cost unresolved. Do not subtract the long register control as if it isolated that overhead. Replace “within the dense all-five row's spread” and “near 1.00 ... with no pass below” with a stated tolerance justified by the short measurement window, or make these diagnostic comparisons without a hard acceptance claim. Keep within-sparse repeatability separate from agreement between sparse and dense means.

### R12 — P2: Accepted sparse sizes can execute more loads than reported

**Status:** open. **Locations:** `latency.c` lines 100–109, 164–171; plan line 550; CLI help.

Sparse mode accepts sizes in multiples of 8 KiB. An 8, 16, or 24 KiB buffer therefore has 2, 4, or 6 members. The core chase always executes groups of eight loads, but the timing and counter denominators use the requested member count. This also walks these short chains more than once. The CME path executes the requested count, so the two paths differ. The planned 256 KiB and 1.25 MiB campaign rows are unaffected. [latency.c lines 94–110, 164–171]

An independent host probe with an eight-node cycle confirmed that requests for 2, 4, and 6 loads each returned to node 0, as eight loads would. Their expected endpoints were nodes 2, 4, and 6. A request for 8 loads behaved correctly. [local probe `/tmp/cme-review-snapshots/sparse_load_probe.c`]

**Requested change:** either require sparse sizes to be multiples of 32 KiB or handle the core loop's remainder. Update the size contract and verify the smallest accepted size. Keep the shared loop's reported denominator equal to its actual load count.

### R13 — P2: Reconcile the new section with the operative tables and source data

**Status:** open. **Locations:** plan sections 2.1, 4.1, 4.4, 11; README; `run_asimov.sh` header.

The main plan still specifies dense `--fresh 3` OCM rows and the old phase-F budget. The script header still says phase F adds 32 commands and 46 launches. Section 11 and the script now use sparse rows plus dense controls, with 33 phase-F commands and 48 launches. Update the operative row/file tables and budget, or clearly mark the earlier sections as superseded. Keep the review-response history unchanged. [plan lines 98, 318, 376–394, 555–563; run_asimov.sh lines 53–57]

The new measured ranges also need correction. Across the 40 timed per-region passes, the CSVs give **1.1143–1.4468 L2 refills/load** and **0.7627–0.9500 L3 refills/load**. Across the eight all-five passes, they give **1.0003–1.0006** and **1.0007–1.0011 refills/load**, respectively. The 19-of-20 faster-pass correlation is correct. State whether a range covers individual passes or command summaries, and correct the repeated ranges in the README and source comments. [results/membench-jibin-002/results/19700101T000000Z/latency-ocm-region*-cpu*.csv and latency-ocm-all5-cpu*.csv]

Verification in this review: independent CSV aggregation, a controlled host probe of load counts, shell syntax, and the script's dry-run/estimator. No hardware or emulator benchmark was run. Waiting for the next response in `CME-plan.md`.

### Section 12 response checked — R10 and R12 closed

The revised prefetch interpretation is accepted. The core loop now handles the remaining loads correctly. My independent eight-node probe returns the expected nodes for 2, 4, 6, and 8 loads. A separate host build also produces seven sparse passes at each of 8 KiB, 16 KiB, 24 KiB, 256 KiB, and 1.25 MiB, with the correct reported hop counts. Shell syntax passes.

The new complete-call timing label and diagnostic comparisons address the main R11 concern. The new `cme-call` loop correctly times 64 one-hop calls and reports time per call. Only these follow-ups remain:

- **R11 — finish the control wording.** Plan line 567 says the empty bracket alone bounds the core call's overhead. It contains no `chase()` call, dispatch, loop setup, or return. Say it measures the timer interval only and leaves the core-call cost unresolved. Describe `cme-call` as a complete one-hop control containing the shared streaming entry/exit sequence. Its value also includes one register hop and the surrounding C loop. Remove “minus one hop” from `latency.c` and the exact-component wording in plan line 564 and README line 245. No further calibration is required with these limits stated.
- **R11 — remove the remaining hard acceptance rule.** README line 181 still says sparse rows “must match” dense counters and latency before per-region rows can be trusted. Use section 11's diagnostic comparison and preserve discrepant rows.
- **R13 — account for the new control calls.** `est_chip_time.py:latency_cmd` still counts only `(1 + reps) * loads` control hops. The new code adds 64 one-hop calls per repetition: **1,920 calls/hops across the ten phase-F latency commands**, for **2,623,360 total control hops**. The plan table includes those hops, but the claimed reproducible estimator does not. Update its count and state how the added call/bracket costs are estimated or left unmeasured. This does not require changing the rounded budget unless the calculation warrants it.
- **R13 — correct the DRAM sentence.** Plan line 543 says the two flushed 8 MiB passes have “1.0001 and 1.0002 of each.” The CSV has **1.0001 L2 refills/load in both passes**, and **1.0002 then 1.0001 L3 refills/load**. The per-region and all-five ranges are now correct. [results/membench-jibin-002/results/19700101T000000Z/latency-dram-flushed.csv]

Waiting for the follow-up in `CME-plan.md`. R10 and R12 need no further work.

### Section 12.1 checked — sparse measurement comments resolved

The control descriptions and diagnostic comparison now state the intended limits. R11 is closed. The corrected estimator reproduces 2,623,360 control hops, including 1,920 one-hop calls. The extra call allowance is labeled as an estimate, and uncounted bracket/timer work is explicit. The DRAM sentence is corrected. Those R13 follow-ups are closed.

Section 13 adds a runner split during this review. I checked the new scripts: their combined dry-run contains exactly the previous 100 measurement commands, with phase F moved after the cache suite. The whole suite still has 166 launches, and phase F still has 33 commands and 48 launches. Shell syntax passes for all four scripts. Two packaging issues remain below.

### R14 — P2: The combined runner can report success after failed measurements

**Status:** open. **Locations:** `lib_run.sh:run`; both runner endings; `run_all.sh` exit handling; plan section 13.

`run()` logs a failed benchmark, then returns the status of its final `rm` command. Each suite ends with a successful `say`. Thus `run_all.sh` can print two zero exit codes and return success even when measurements failed. The copied helper inherited this behavior, but the new top-level status does not establish a successful measurement run.

An isolated test of the exact helper used a stub measurement that exits 7. It printed `(exit 7)`, wrote the stub output, and returned 0. The test used only a temporary directory and did not touch CPU state or hardware.

**Requested change:** retain a failure count or status in the shared helper and return nonzero from each suite after cleanup when any measurement command failed. Continuing to collect the other rows is fine. Restore CPU state before returning. Verify the combined runner with an injected failing stub and a succeeding stub. This can be tested without running benchmarks or touching hardware.

### R13 packaging follow-up — use the new runner in the operative plan

Section 4.4 still gives `sh run_asimov.sh --dry-run | python3 est_chip_time.py --phase F` as the source of the phase-F counts. That command now produces **zero commands and zero launches**, which I reproduced. Use `run_cme.sh --dry-run` for phase F and `run_all.sh --dry-run` for the whole suite.

The main plan also still places phase F between D and E with CPU 3 already offline (section 2.2 item 9, section 3.6's runner description, section 6 item 6, and the reviewer path in section 7). Update these operative references for the split, or explicitly mark them as superseded by section 13. No change to the measurement row set is requested.

Waiting for the response to the packaging findings. No target performance validation or publishing was performed by this review.

## Final disposition through section 13.1 — no further comments

Checked the section 13.1 response and the actual script changes. The shared helper records failed measurements, and each suite returns failure after restoring CPU state. The main plan now points to the correct scripts and execution order. R13 and R14 are closed. All fourteen comments are resolved.

Independent isolated runner checks passed:

| Stub measurement result | Cache suite exit | CME suite exit | Combined exit |
|---|---:|---:|---:|
| Cache measurement fails | 1 | 0 | 1 |
| CME measurement fails | 0 | 1 | 1 |
| Both succeed | 0 | 0 | 0 |

These tests used temporary script copies and stub binaries. The CPU helper only logged actions, and the sysinfo block was omitted. The production measurement helper, result handling, and top-level wrapper were unchanged in those copies. All cases retained output, continued through the remaining commands, removed the temporary output file, and logged CPU restoration before the suite result. Dry-run executed no measurements or CPU actions and created no output directory. Shell syntax passed for all four scripts.

The review also verified sparse load counts with a host probe, the smallest supported sparse sizes, measured CSV ranges, unchanged measurement commands after the runner split, and the corrected estimator counts. The reviewed files were checked for further changes before this disposition was written.

Target CME timing, hardware counter behavior, and the effectiveness of the sparse mitigation remain unverified by this review. The plan now states those measurement limits. No further plan-review work is outstanding on the version identified above.
