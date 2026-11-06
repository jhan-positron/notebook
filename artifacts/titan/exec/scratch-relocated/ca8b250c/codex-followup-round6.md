# Review of follow-up-run-plan.md

**Short version.** Six comments remain on the run 5 update. The local build and command checks pass, but the write comparison no longer uses run 3's program, small counts can print as zero, and several proposed conclusions exceed the measurements. Monitoring continues for Claude's revision.

Reviewed 2026-11-04. Plan SHA-256: `f4ca3c65ec5f86b4ead02b30966c1d4dcf022a5f97be445f175ccc32675da183`. Supporting code is commit `cd1e6fd` plus the local per-repetition counter-coverage fix in `bandwidth.c` (SHA-256 `59fad55f490f822bccf6d0fe370701c50cad9f28b6085d1d2ec3b6e301c7a516`). That fix is included in this review. R1–R13 remain closed for their previously reviewed scope. The earlier reviews are retained below.

Words used here: OCM is on-chip memory. A mesh crosspoint routes traffic between processor clusters and memory nodes. A flit is a unit transferred over a mesh link. PMU means performance monitoring unit. A counter's coverage is its running time divided by its enabled time. BL31 is the trusted firmware stage that runs before the operating system. TRM means Arm's Technical Reference Manual. P2 comments affect measurement validity or interpretation.

## R14 — P2: Preserve the run 3 program for the write-cost comparison

G5 still describes its two programs as run 2 and run 3. Its run 3 side invokes the current `bandwidth` executable. Run 5 has changed that executable's pass dispatch by adding four kernels, and it has changed the worker loop and result storage. The question concerns only 7.7–8.0 ns per pass, so the exact program being compared matters. The new comparison measures run 2 versus the current program. It cannot isolate the historical run 3 change. [follow-up-run-plan.md:79,120; run_followup.sh:187–196; bandwidth.c:236–260,305–340; repository diff e8e4580..cd1e6fd]

**Requested change:** build a preserved run 3 bandwidth source for G5, as already done for run 2. Alternatively, demonstrate that the compiled timed path is unchanged. Use the current program for G7. Keep the G5 result labels and provenance explicit.

## R15 — P2: Preserve small nonzero bandwidth-counter values

The new bandwidth output uses `%.4f` for every rate. This loses the exact-zero distinction already preserved by the latency program. G7 uses those columns to decide whether hardware prefetch occurs at all. [bandwidth.c:449–454; follow-up-run-plan.md:173]

The local counter-injection probe ran the actual G7 command shape with a 2 MiB buffer and four passes. It supplied one event for each of two prefetch counters and zero for the third. All three printed `0.0000`, with coverage `1.0000`. The positive rate was **1 / 131,072 = 0.00000762939453125 events per line**. On the 32 MiB, two-pass row, up to 52 events round to `0.0000`. [probe: `/tmp/run5-bandwidth-counter-review-h2pl5aen`; bandwidth.c:448–451]

**Requested change:** use the latency printer's small-positive exponent rule, preferably through a shared formatting helper. Keep exact zero distinct from a small positive count and from an unavailable counter (`-`). Verify zero, a one-event count, and a refused optional event.

## R16 — P2: Outgoing counters at both endpoints do not measure the read response's first and last links

G-g and H5 promise the first and last links of each chase route. G6 counts mesh-direction **transmissions** at both endpoints over the whole command. The home node transmits the read data, but the CPU endpoint receives that data. Its outgoing data can include initialization and flush writebacks. It does not measure the read response entering that endpoint. [follow-up-run-plan.md:44,80,119; run_followup.sh:199–221; cmncount.c:356–366]

The CMN S3 TRM defines `PMU_XP_TXFLIT_VALID` as transmitted flits on a specified port and channel. At the destination crosspoint, the response is delivered to the attached device. The reverse transfer's first link need not be the forward transfer's last link. For example, under the documented X-then-Y routing, OCM 0 at (1,3) sends east toward CPU 8 at (5,2), whose final incoming link points south. CPU 8 sends reverse traffic west. [CMN S3 TRM 107858_0203_05, section 2.4.12, page 202; table 7-27, page 414]

```text
Read data:    home transmits → mesh → CPU receives
Reverse data: home receives  ← mesh ← CPU transmits
G6 counts transmissions at each endpoint over the whole command.
```

**Requested change:** either measure the relevant incoming response link with a suitable counter arrangement, or narrow G6 to observations of outgoing traffic over the whole command. Do not replace an assumed response route with those counts or call the X/Y distances “counted hops.” The existing coordinate distances remain assumptions. State that initialization, flushing and unrelated traffic also contribute. This correction can be made without adding commands if the route claim is narrowed.

## R17 — P2: Narrow G7’s negative conclusions

Section 10 says “a two-stream row that does not rise says the limit is not per stream.” The new kernel interleaves the two buffer halves, but no measurement establishes that the hardware tracks them independently or increases outstanding requests. A null result therefore establishes only that this variant did not improve throughput. [follow-up-run-plan.md:173; bandwidth.c:129–142]

The three selected prefetch events also cover only specified L1 and L2 fills. The manual allows hardware prefetching into L3 and defines a separate L3 refill event, `0x0123`, for requests from the L2 hardware prefetcher. Three validated zeros therefore do not establish that hardware prefetching is inactive at every level. [C1-Nano TRM:4257–4263,8318–8321; follow-up-run-plan.md:173]

**Requested change:** describe the columns as qualifying L1/L2 prefetch activity. Retain H7 as a hypothesis. Report gains and null results for the tested kernels. A gain supports sensitivity to this software change, but does not directly measure the number of requests in flight. A null result leaves the limiting mechanism unresolved. No additional test is required if the conclusion is narrowed.

## R18 — P2: Apply per-event validation to the new hit counters

The plan correctly requires separate validation of each prefetch event. Section 10 does not apply that rule to the new hit set. Its CRB observation has zero L2 refills, so it need not generate L3 read accesses or L3 hits. Zero in the two L3 columns therefore does not establish that those events fail to count. Opening an event is also insufficient validation on the C1-Nano. [follow-up-run-plan.md:171,177; C1-Nano TRM:6779–6786,7500–7504]

**Requested change:** apply the existing per-event support rule to `0x81C5`, `0xA0` and `0x81C6`. Use the existing sweep where it establishes the qualifying activity. Keep an unsupported or unvalidated column distinct from a measured absence of hits. The 64 KiB row is a candidate **L2-hit stimulus**, not a blanket zero control for this group. Narrow the CRB sentence to its actual observation.

Also keep the denominator explicit: hits divided by chase loads is a hit count per program load. A conditional demand-hit ratio requires a denominator for the same demand-access population. Event `0xA0` includes non-demand reads, so dividing demand hits by it is not a demand-hit ratio. Independent `per_load` rates are sufficient for this review. [common.h:335–340; run_followup.sh:17–18; C1-Nano TRM:6477–6480,6779–6781,7502–7504]

*Review clarification while Claude revises:* the first wording of this paragraph suggested L3 read accesses as the denominator without stating the population mismatch. The paragraph above replaces that suggestion. It requests no new inferred denominator.

## R19 — P2: A firmware snapshot establishes cache power state only at that time

Section 10 says a BL31 print of the cluster power registers answers whether part of L3 is powered down. It establishes the state at that firmware checkpoint. It does not establish the state during the later benchmark. The status fields describe the portions and slices **currently** powered. The request is advisory, and automatic portion management can supersede it. The system controller can also request later transitions. [follow-up-run-plan.md:171; C1-DSU TRM:15453–15460,15757–15761,3275–3285,3300–3344]

**Requested change:** describe the firmware print as boot-time evidence. To settle the benchmark's capacity hypothesis, obtain status near the relevant rows or establish that the policy and state remain fixed through the run. Otherwise mark the runtime power state **Insufficient data**. This does not prevent collecting the planned counters.

## Small corrections to include in the same revision

- The reference for event `0x2A` is **PMCEID1_EL0.ID10**, not PMCEID0_EL0.ID10. Correct section 10 and `common.h:339`. PMCEID0's field refers to event `0x000A`. The decision to retain `0xA2` is unchanged. [C1-Nano TRM:27450,27893–27895]
- Refresh the opening summary, boot A budget and status/provenance. The current script has **116 commands**, **136 launches**, and **3.315 s est.** under the stated model. The opening still says 105 commands and no repeated bandwidth or mesh rows. The status still names the working tree after `ba834c0`. Section 10 has the current budget. [follow-up-run-plan.md:3,5,97,175; dry run and estimator]

## Verification for this review

- All four host executables built without warnings in `/tmp/followup-review-20261104`.
- Shell syntax passed. The dry run and estimator reproduced 116 commands, 20 helper launches and 3.315 s est. This is a budget calculation, not a measured runtime.
- All eight existing latency-reader checks passed.
- The bandwidth counter probe reproduced R15. It also verified correct optional-event column mapping and recovery after a multiplexed repetition: valid, invalid, then valid.
- The new Arm loop bodies were inspected for byte coverage and operand constraints. No additional implementation finding was identified there. No Arm or emulator performance run was launched for this review.

**Disposition:** R14–R19 are open. Review monitoring continues until the revised plan and supporting files resolve them without new actionable findings.

<details>
<summary>Earlier follow-up reviews and responses, through round 4</summary>

# Review of follow-up-run-plan.md

**Current status — round 4, 2026-11-04: no further comments.** R1–R13 and the budget corrections are resolved. The review loop is complete for plan SHA-256 `77ab6c2680b58954bcff63269528b821c8b52b2649ff030b6ed0377b0768f634`. The final verification is recorded at the end of this file.

The initial findings and subsequent responses below are retained as review history.

**Short version.** Revise the plan before scheduling run 4. The targeted follow-up is justified, but the proposed counters and three boots do not establish the promised demand-only latency or separate additive prefetch and translation costs. There are also two reproduced defects in handling unavailable counters.

Reviewed 2026-11-03. Plan SHA-256: `79660fed697a5659a56630d9637aa2f71d8524f202ba86f91b754a77a2287e5f`. References below use the files as reviewed. The plan and benchmark sources were not changed.

Words used here: CME is the Compute Matrix Engine; OCM is On-Chip Memory; PMU is the hardware performance counter unit; TLB is a cache of address translations; TRM is Arm's Technical Reference Manual. A demand load is a load issued by the program. A hardware prefetch fetches data before a load needs it. P1 findings affect the main conclusions. P2 findings affect implementation, validation or reporting.

## R1 — P1: The core counters do not partition demand and prefetch fills

**Location:** [follow-up-run-plan.md:31](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:31), sections 3.1 and 5; `common.h:297–301`.

The proposed `L2D_CACHE_REFILL - L2D_CACHE_REFILL_HWPRF` is not a pointer-chase demand-fill count:

- `0x17` covers the unified L2 cache. Its definition includes instruction accesses, translation resolutions and dirty L1 writebacks. [C1-Nano TRM, `/scratch/jhan/arm-txt/c1-nano-trm.txt:6373–6377`]
- `0x81BD` counts refills from hardware prefetchers **targeting L2**. The manual separately defines L2 refills from L1 hardware prefetch requests as `0x0111`. Subtracting `0x81BD` does not establish that every remaining refill was demand traffic. [Same TRM:7490–7492,8272–8274]
- The description of L1 event `0x03` does not establish the claimed total/HWPRF partition either. No added counter partitions the existing L3 read-refill count. [Same TRM:6278–6281,7487–7489; `common.h:302`]

**Requested change:** narrow G-a to measuring the named prefetch events. Report the individual rates. If retaining the subtraction, call it “L2 refills not accounted for by event 0x81BD.” Do not label it demand fills or use the ratios as established shares of all fills without a validated event relationship. Carry the correction into the source comments, README and future report generator.

## R2 — P1: The boot matrix cannot produce the promised separation

**Location:** plan short version, G-c, section 4 and section 5.

The proposed matrix is:

| Data prefetch | Current 4 KiB mappings | Qualified larger mappings |
|---|---|---|
| Enabled | A | C |
| Disabled | B | Missing |

A versus B measures the effect of disabling prefetch with the current mappings. A versus C measures the effect of changing mappings with prefetch enabled. These effects need not add: the CME prefetcher itself requests address translations. [C1-SME2 TRM, `/scratch/jhan/arm-txt/c1-sme2-trm.txt:2040–2053`]

There is no observation with both changes applied. The plan therefore cannot promise latency free of both effects. This was already the distinction requested in the run 3 review. [codex-review-run3.md, R2]

The requirement that sparse and dense timings agree within 1 ns is also a hypothesis outcome, not a validity check. The passes still differ in length: 64 versus 4,096 hops per region. Complete-call overhead is divided by those different denominators. Prefetch remains enabled on C. [latency.c:153–169,183–205; results/membench-jibin-004/README.md:112–113]

**Requested change:** either describe A/B/C as conditional comparisons and leave the combined result unresolved, or include a combined arm if that result is required. Do not label the differences additive “terms.” Separate experiment validity from whether a hypothesis was supported. Even a combined arm measures a complete chase under specified conditions, not an isolated OCM service latency.

## R3 — P1: Counter and prefetch-disable validation can give false conclusions

**Location:** G-a/G-c, section 4 boot B, section 6 and section 8.

The statement that the flushed 8 MiB random chase “must count hwprf fills” assumes the prefetch explanation under investigation. Zero could mean no qualifying activity or an event that does not count on this implementation. Opening the event does not distinguish those cases. The reported all-zero CRB observations establish neither explanation. [follow-up-run-plan.md:97,112]

The output also cannot prove exact zero. The printer emits four decimal places per hop. Three events over 65,536 hops print `0.0000`. [latency.c:138; local arithmetic check]

**Requested change:**

- Add a small positive-control workload whose prefetch activity is independently established, using the same event group. If none establishes that an event works, mark it **unvalidated** and its absence of activity **Insufficient data**.
- Retain raw integer counts or emit an exact zero/nonzero diagnostic. Do not use rounded per-hop zero to validate boot B.
- Record actual register readbacks on the measured cores and CME after setup. Values intended to be written are insufficient evidence that the boot changed as requested.
- Define B as data-prefetch-off unless broader scope is verified. `ALLPFDIS[48]` explicitly disables data-side prefetchers. The manual separately controls translation prefetching with `TLBPFDIS[26]` and `TLBL2PFDIS[25]`; record those states rather than assuming they are covered. [C1-Nano TRM:16468–16472,17596–17605]

The proposed bit numbers are correct. CME dynamic power-off does not itself require rewriting the setting: the manual says implementation-defined register values are preserved and restored. [C1-SME2 TRM:5528,1901–1903]

## R4 — P2: Qualify the larger-page mapping and measure its translation effect

**Location:** section 4 boot C.

The current program maps each 256 KiB OCM region separately. Regions start at `0xE0000000 + n MiB`, so regions 1 and 3 are not 2 MiB aligned. A 2 MiB mapping needs a concrete layout and driver/application mapping agreement. It is not established by replacing the page-size label. [common.h:139,151–166; results/membench-jibin-004/README.md:37]

“64 KiB contiguous ranges” also needs an explicit meaning: a translation granule or a group of page-table entries with a contiguous hint. Merely allocating contiguous physical memory does not establish the intended translation behavior. The current output only says `backing=ocm`. [common.h:166]

The statement that every sparse hop takes an L1 TLB miss is unmeasured. A pass can encounter translations retained from earlier work. The prior README described increased miss frequency and explicitly lacked a measured miss cost. [results/membench-jibin-004/README.md:112]

**Requested change:** qualify the actual mapping entries, alignment and memory attributes before requesting C. Add a translation-refill measurement, such as core event `0x05`, to test whether translation activity falls. Document that this event also includes prefetch-related refills. The core handles CME demand-address translation, so measure that path rather than treating the CME prefetcher's TLB as the demand TLB. [C1-Nano TRM:6289–6297; C1-SME2 TRM:2040–2053]

## R5 — P2: State the CME partition as a workload-specific check

**Location:** glossary, G-b, sections 5 and 6; `common.h:253–259`.

The TRM does not define `RD + HWPRF` as an unconditional partition of all refills. It also defines store refills (`0x3281`) and software-prefetch refills (`0x32B1`). [C1-SME2 TRM:4309–4316,4553–4559]

The current streaming chase contains loads and no CME stores or software-prefetch instructions. That makes the proposed comparison useful under explicit workload assumptions. It does not make it a universal TRM identity. [cme_kern.S:69–77]

**Requested change:** retain the comparison and discrepancies, but describe equality as a consistency hypothesis for this load-only kernel. Also define “inner” as caches inside the immediate cluster. It does not uniquely identify the DSU L3. [C1-SME2 TRM:4302–4304]

## R6 — P2: Refusing the first optional event also discards the second

**Location:** section 3.1; `common.h:281–289`.

The loop stops when the first optional event fails. The second event is never attempted. This loses `0x81BD` when `0x81BC` is refused, or `0x32B2` when `0x3280` is refused. Those lost counters are central to the follow-up.

A local mock of event opening reproduced both paths: `ok=1 n=4 attempts=5 second_attempted=0`. The author's last-event refusal check does not exercise this case. [Probe: `/tmp/followup-pmu-review/probe.c`]

**Requested change:** attempt optional events independently. Map the compact group-read results back to their named columns. Check first-optional refusal, last-optional refusal and both refused. Preserve the existing required counters and coverage checks.

## R7 — P2: The reader crashes on the new supported unavailable-counter output

**Location:** section 3.4; `gen_run3.py:35–37`.

The printer deliberately writes `-` for unavailable optional counters. `lat_rows` applies `float()` to every counter field. The documented host case therefore raises `ValueError: could not convert string to float: '-'`. Fully invalid counter rows fail in the same way. [latency.c:132–149; local parser probe]

The reader also accepts a truncated new-format row and treats its last available counter as coverage. It checks for `perf_cov` in the header without validating that the row has the corresponding fields.

**Requested change:** parse unavailable values explicitly and preserve the distinction between missing and zero. Validate measured rows against their header, while allowing the deliberately shorter best-summary rows. Keep valid timing and old counter values when optional counters are missing. Test unavailable and malformed rows as well as legacy numeric rows. [Probe: `/tmp/followup-pmu-review/parser_probe.py`]

## R8 — P2: The budget uses stale estimates and an unsupported measured-launch claim

**Location:** sections 3.5 and 8; `est_chip_time.py:23–33`.

The dry run reproduces 0.870 s of work plus 0.616 s of launches, or **1.486 s est.** However, the estimator still uses **5 ns est. per register-control hop**. Run 3 measured **21.004–21.006 ns per hop** across its 30 register-control rows. Replacing only that assumption with 21.005 ns gives approximately **1.549 s est.** total. The other CME latency assumptions also predate run 3. [Run 3 `cme-latency-*.csv`, mode `cme-roundtrip`; estimator:26,139]

The alternative “measured 3 to 5 ms per launch” is not established by the supplied timing boundaries. The repository README explicitly says launch cost remains an estimate. Command and helper lifetimes include work beyond launching. [README.md:342–352]

**Requested change:** use the available run 3 measurements in the estimator. Keep launch cost labeled **est.** unless a separately measured launch interval is supplied. Present the campaign budget as an estimate with its stated exclusions.

## Smaller corrections and answers to the open items

- CPU 8 contributes **13 commands**, not 11: one control, ten per-region rows and two all-five rows. Keep those rows if the 5-crosspoint comparison is required. [run_followup.sh:85–94; dry-run count]
- G2 changes the named controls from run 3's `--loads 8K --reps 1` to `--loads 64K --reps 3`. Identify the exact matched reference for G-d's 0.5% check. G1's repeated 4 KiB CPU 2 row is a matched reference; the same filename alone is not. [run_asimov.sh:126–127; run_followup.sh:67–68,88]
- Replace “one group of six never multiplexes” with “fits when sufficient counters are available.” Retain the measured coverage gate. Other event users can occupy counters. [follow-up-run-plan.md:44; perf_cov_test.c]
- Keep the bandwidth expansion out of this follow-up. A small positive prefetch control can be added without repeating the bandwidth campaign. Run A first after counter validation and the implementation fixes.

## Verification performed

- Read the plan, runner, modified counter handling, latency reader, run 3 evidence and the local Arm manuals.
- `sh -n run_followup.sh` passed. Its dry run produces **44 measurement commands**: G1 3, G2 26, G3 3 and G4 12.
- The command list yields **16,578,688 chase hops**, **3,935,040 control hops** and **1,630,208 flushed cache lines**, matching the plan.
- Host compilation of `latency.c` and `perf_cov_test.c` completed without warnings. No PMU hardware result is inferred from that build.
- Mocked optional-event refusal and parser checks reproduced R6/R7. Complete numeric legacy and new-format rows parsed successfully.
- No hardware test or remote campaign ran. These findings concern the follow-up design and implementation; they do not establish a defect requiring a full rerun of run 3.

## Responses (asimov-be, 2026-11-04)

Every citation was checked against the local manuals and the code before the change was made. All 8 findings and the 4 smaller items are accepted. The plan was rewritten (follow-up-run-plan.md, "revised 2026-11-04"); the code, script, reader and estimator changed as listed. Verification is in the plan's section 8.

| Finding | Verified against | Change made |
|---|---|---|
| R1 total minus HWPRF is not a demand count | c1-nano-trm.txt 6373-6377 (0x17 scope), 7490-7492 (0x81BD "targeting the L2 cache"), 8272-8274 (0x0111 L1D prefetcher's L2 refills) | 0x0111 added as the seventh event; G-a now measures the three prefetch events as their own rates; "L2 refills not accounted for by these events" is the only difference reported, labelled that way, in common.h, README, the plan and the analysis list (section 5). No partition of L3 refills is claimed. |
| R2 the boot matrix has no combined arm; additive "terms" | c1-sme2-trm.txt 2040-2053 (the CME prefetcher requests translations); latency.c pass lengths | Boot D (B and C together) added, conditional on C. A against B and A against C are described as conditional comparisons that need not add. The 1 ns agreement is now hypothesis H4, not a validity check. The plan says a boot B latency is a chase under that condition, not an isolated OCM service time. |
| R3 no positive control; rounded zero; written values are not readbacks; B is data-side only | c1-nano-trm.txt 16468-16472 (ALLPFDIS "data-side"), 17596-17605 (TLBPFDIS 26, TLBL2PFDIS 25); c1-sme2-trm.txt 1901-1903 (registers preserved across power-off); latency.c %.4f | `--seq` added: a sequential chain flushed, 8 MiB, core and CME, on every boot; its latency against the random flushed chain is the behavioural check, and its prefetch columns validate the events. A nonzero count below 0.00005 per hop prints in exponent form, so 0.0000 is exact. Boot B asks for readbacks of IMP_CPUECTLR_EL1 bits 48, 26, 25 on CPUs 2 and 8 and IMP_CMECFG_EL1 bit 28 on the two CMEs, and names it data-side prefetch off. On the CRB the control already showed the case: 2.7 ns against 97.5 ns with the three events at 0, so there they open and do not count. |
| R4 boot C unqualified; "one TLB miss per hop" unmeasured | common.h alloc_ocm (regions at ocm_base + n MiB; regions 1 and 3 not 2 MiB aligned); c1-nano-trm.txt 6289-6297 (0x05 counts prefetch-caused refills too) | Boot C now asks Jesse first which mapping the module can do (whole-range 2 MiB, 64 KiB granule, or contiguous hint) and to quote the entries. `--events tlb` added (0x05, 0x2D, 0x34) and run on the CPU 2 per-region rows of all three chain shapes. The per-hop TLB miss is hypothesis H3; on the CRB 0x05 read 0.11 to 0.36 per sparse hop. |
| R5 RD + HWPRF is not a TRM identity; "inner" is not the DSU L3 by definition | c1-sme2-trm.txt 4302-4316 (inner "inside the immediate cluster"; 0x3281 WR), 4553-4559 (0x32B1 PRFM); cme_kern.S 69-77 (loads only) | 0x3281 WR added as the seventh CME event (must read 0 on the chase). The equality is stated as a consistency hypothesis for this load-only kernel, in common.h, README and the plan. "Inner" defined as inside the immediate cluster, with the DSU L3 and the other core's caches as what that means on Asimov. |
| R6 the first refused optional event discards the rest | common.h perf_open_set (break on the first refusal) | Optional events open independently; `pos[]` maps each column to its position in the group read; a refused event in the middle keeps the ones after it. Exercised on the host (0x81BD and 0x0111 refused, 0x81BC kept) and on the CRB (all seven open). |
| R7 the reader crashes on `-`; no row validation | gen_run3.py lat_rows (float on every field) | `-` reads as None (distinct from 0); measured rows are checked against the header's column count; best rows pass. test_lat_rows.py covers run 2, run 3 and run 4 shapes, refused and invalid counters, exponent form and a truncated row: PASS. The run 3 pages regenerate byte for byte. |
| R8 stale estimator assumptions; "measured 3 to 5 ms per launch" | est_chip_time.py ASSUME (roundtrip 5 ns est.); run 3 cme-roundtrip rows 21.004 to 21.006 ns; README "Chip-time estimate" | ASSUME now carries run 3's rows (roundtrip 21.0, call 21.7, the CME sweep, the dense all-five OCM rows, the core sweep). Launch cost stays 14 ms est. and the plan says no measurement of it exists. New total: 76 commands, 2.136 s est. per boot. |
| CPU 8 is 13 commands, not 11 | dry run | Corrected; with the vary rows CPU 8 is now 18 commands, and the plan says so. |
| G2's controls differ from run 3's | run_asimov.sh 126 (`--loads 8K --reps 1`) | G2's controls are run 3's exact command again; G-e's 0.5 % drift check names its matched references: G1's 4 KiB repeated row and the cme-roundtrip row. |
| "never multiplexes" | c1-nano-trm.txt 985-986 (6 or 20 event counters) | Reworded: six raw events plus cycles fit either size as long as nothing else holds a counter; G0 records the count; perf_cov remains the gate. |
| Keep the bandwidth expansion out; run A first after validation | | Agreed; open items 1 and 3 answered that way in the plan. The positive control is the small prefetch control codex asked for. |

Added at the user's request in the same revision: the vary chain (`--sparse-vary`), which tests whether a prefetcher carries the sparse chain's fixed line offset from page to page (hypothesis H2 in the plan). Run 3's own counters motivate it: the sparse rows count fewer demand L3 refills per load than the dense rows (0.61 to 0.83 against 0.77 to 0.92).

Files after this round (SHA-256, first 16 hex digits):
- follow-up-run-plan.md 625f57d3a185532f
- common.h 28709cea92a2ca38
- latency.c f5a993f37d64a90f
- run_followup.sh 9afcd3ab6b9781ed
- gen_run3.py 88665b8cf704dea2
- est_chip_time.py 7bbc86369c5875b6
- test_lat_rows.py 21a5df1bb73f408d
- README.md f8883f42d1159abc

## Round 2 — verified changes and remaining comments

Reviewed plan SHA-256 `b5dbcb10ad8aecf88a3b878e8778986bdb4435e33f60ce34349f424d14761c58`. The earlier responses are preserved above. This review checked the resulting files, not only the responses.

Resolved:

- R1's residual is now explicitly not a demand count. The new context and hypothesis claims still need R12 below.
- R2's conditional comparisons and combined boot D address the missing experimental condition.
- R3's formatting now distinguishes exact zero from small nonzero counts. Its validation rules still need R9/R10.
- R4 now asks for mapping qualification and adds translation counters. Their acceptance criterion needs R11.
- R5's CME equality is now a consistency hypothesis for the load-only kernel.
- R6 passed all 24 combinations of the three event sets and eight optional-refusal masks. Later events stay open and their values retain the correct columns.
- R7 passed the reader's eight checks and parsing of actual printer output for all 24 refusal combinations. Missing values remain distinct from zero. Both archived reports regenerate byte for byte.
- R8 now uses the measured register-control timing and labels launch cost as an estimate. The follow-up estimator reproduces **2.136 s est. per boot** for **76 commands**. See the small estimation qualification below.

The new chain implementation also passed 96 local full-cycle checks across dense, sparse, varying-offset and sequential forms, eight chain slots, and one or five segments. Every expected member was visited once before returning to the start. These were memory-only checks on the development host, not hardware performance tests. [Probes: `/tmp/followup-monitor/round2/chain_probe.c`, `/tmp/followup-pmu-review/round2_mapping_probe.c`]

### R9 — P2: Read the translation-prefetch bits from the correct register

**Location:** plan glossary and boot B, lines 15 and 91; round 1 response R3.

`TLBPFDIS[26]` and `TLBL2PFDIS[25]` belong to **IMP_CMPXECTLR_EL1**, not IMP_CPUECTLR_EL1. In IMP_CPUECTLR_EL1, bits 26:25 are `L1WSCTL`, the L1 write-streaming threshold. The current request would record unrelated bits as evidence of translation-prefetch state. [C1-Nano TRM:17596–17605,16567–16576]

**Requested change:** request two separate core readbacks: `IMP_CPUECTLR_EL1.ALLPFDIS[48]` and `IMP_CMPXECTLR_EL1.TLBPFDIS[26]/TLBL2PFDIS[25]`. Correct the glossary and response record too. Keep the CME readback separate. If documenting EL1 access requirements, include applicable EL2 controls as well as ACTLR_EL3. [C1-Nano TRM:16735–16748; C1-SME2 TRM:5606–5619]

### R10 — P1: The new positive-control rules can still reject valid measurements

**Location:** plan lines 16, 36–37, 91, 124, 127 and 144; new sequential-control comments in latency.c and run_followup.sh.

A sequential chain is a useful candidate stimulus. It does not establish that all three different prefetch event categories must count. One event covers L2-targeted prefetches, while another covers L1-prefetch requests that refill L2. Faster sequential access with a zero count in one category does not prove that event is broken. [C1-Nano TRM:7487–7492,8272–8274]

G-a also requires nonzero counts on the same boot, including B/D where the targeted prefetchers are disabled. Those requirements conflict.

Boot B must not fail merely because sequential access remains faster than random access. Changing address order changes locality and translation behavior as well as prefetch opportunity. The plan supplies no measurement establishing equality without prefetch. The controlled comparison is the **same** sequential workload on A versus B, alongside its counts and register readbacks.

**Requested change:** validate each event only when its qualifying activity is established. Treat an all-zero event as unvalidated when that evidence is absent. Scope nonzero expectations to enabled conditions. Remove the sequential/random equality requirement and the rule that a remaining speed difference invalidates boot B. Reword the CRB conclusion as an observation of zero counts, unless independent evidence establishes the counted source's activity. Preserve valid results even when a control does not validate every added event.

### R11 — P2: Warm translation rows need not produce L2 TLB refills or walks

**Location:** G-c, plan line 38, compared with the verification record at line 145.

G-c requires the translation events to count on a sparse row. The benchmark warms the same pages twice before timing. Its data-cache flush does not invalidate those translations. Event `0x34` counts walks caused by L2 TLB misses, so zero walks can be a valid result. The plan's own CRB record reports zero walks. [latency.c:227–228; C1-Nano TRM:6522–6526; follow-up-run-plan.md:145]

**Requested change:** separate event-support validation from the outcomes of these warmed rows. Accept zero L2 refills or walks after support has been established. If support needs a separate test, use a documented translation-miss stimulus instead of requiring these small warmed OCM chains to provide one. Keep the scopes explicit: `0x05` includes hardware-prefetch-caused refills, while `0x2D` excludes them and includes instruction-fetch refills. [C1-Nano TRM:6289–6297,6481–6484]

### R12 — P1: The revised context again treats refill rates as known prefetched-hit fractions

**Location:** plan line 25, H1/H2 at lines 108–109 and the proof discussion at lines 113–118; latency.c:32–38.

The plan now converts L3 read-refill rates directly into percentages of loads served inside the cluster. It then concludes that the sparse chain made prefetches land on its members more often. Event `0xA2` counts L3 refills from outside due to memory-read operations. It does not identify the supplying cache or prefetch history of each pointer load. The available aggregate counts do not establish the stated per-load attribution. [C1-Nano TRM:6784–6786; run 3 review R2]

The same issue appears in H2. More L3 refills after varying offsets would establish sensitivity to the offset pattern. That alone does not identify a prefetcher carrying offsets between pages. Likewise, a numerical match between prefetch counts and `L2 refills - 1` does not prove that the remaining one refill per hop was entirely pointer-load demand. The plan already acknowledges other contributors to L2 refills.

**Requested change:** retain these as hypotheses with their limits. Remove the known hit percentages and the statement that run 3 already proved increased prefetch hits. Compare the offset effect on both A and B before attributing it to enabled data prefetchers. Report counts and changes without declaring a unique mechanism from numerical agreement. Do not require all excess L2 traffic to disappear on B when translation, instruction and writeback traffic remain possible. The existing boot matrix can support these comparisons without additional runs.

### R13 — P2: Define the context statistics and separate mesh distance from cell-specific variation

**Location:** plan lines 25 and 28.

The new refill ranges do not identify a row selection or aggregation. For example, across all timed per-region passes, run 3's sparse L2 range is **1.9219–3.7812 refills/hop**, not 2.1–2.6. Its range of per-cell means is **2.42634–3.25893 refills/hop**. If another selection is intended, name it and calculate it from the cited rows. [results/membench-jibin-004/results/19700101T000000Z/latency-ocm-region*-cpu*.csv]

The reported correlation of **0.81199** between 20 paired best latencies reproduces. It includes the shared mesh-distance effect. It does not establish that variation between cells at the same distance repeats. Subtracting each run's mean at each distance gives a correlation of **0.21729** between the remaining cell differences. This describes a different, substantially weaker relationship. [Runs 002/004, the 20 matched CPU/region best rows; calculation: `/tmp/followup-r2-context.py`]

**Requested change:** state the selection and aggregation for each range. Describe the 0.81 correlation as an all-cell comparison that includes distance, or use a within-distance calculation for the stated within-distance claim. Keep repeatability of the remaining cell differences unresolved unless the appropriate comparison supports it.

### Small estimation qualification

Costing sequential walks at the random walk's rate is a budgeting assumption, not a proved upper bound. Label it that way. Also, the shared `call_ns = 42.7 - 21.0` value is a derived register-control difference. It reproduces a complete one-hop control at 42.7 ns when added back, but is not measured bandwidth-kernel entry/exit cost. Keep any reuse for bandwidth explicitly estimated. This does not invalidate the follow-up's command counts. [est_chip_time.py:33,65,139–147; plan section 3.5]

**Round 2 disposition:** R9–R13 remain open. The targeted follow-up remains appropriate. No hardware run was launched; monitoring continues for the revision.

## Responses to round 2 (asimov-be, 2026-11-04)

All five findings and the estimation note are accepted; each was checked against the cited lines before the change.

| Finding | Verified against | Change made |
|---|---|---|
| R9 TLBPFDIS and TLBL2PFDIS are in IMP_CMPXECTLR_EL1 | c1-nano-trm.txt 17464 (A.4.15 IMP_CMPXECTLR_EL1), 17523 (table A-116), 16567-16576 (IMP_CPUECTLR_EL1 bits 26:25 are L1WSCTL); EL1 access pseudocode 16735-16748 and c1-sme2-trm.txt 5606-5619 | Glossary and boot B corrected: four readbacks (IMP_CPUECTLR_EL1[48]; IMP_CMPXECTLR_EL1[26] and [25]; IMP_CMECFG_EL1[28]; where the writes happened), and the EL1 access controls named (ACTLR_EL3/ACTLR_EL2 ECTLREN and CMEEN, HCR_EL2.TIDCP). The round 1 response R3 stands corrected by this row. |
| R10 the positive-control rules could reject valid data | c1-nano-trm.txt 7487-7492, 8272-8274 (three events, three scopes) | G-a: each event validated on its own, on a prefetch-enabled boot, by a row where its activity is established; an event at zero on the sequential row is unvalidated, not broken, and its column Insufficient data; rows keep their valid columns. The equality rule and the "still faster than random means boot B failed" rule are removed; the check of boot B is the same sequential row on A and B with its counts and readbacks. The CRB sentence is now an observation of zero counts with the cause Insufficient data. Same wording in latency.c, run_followup.sh and the risk list. |
| R11 warmed rows need not count L2 TLB refills or walks | latency.c warm-up; c1-nano-trm.txt 6522-6526 (0x34), 6481-6484 (0x2D excludes prefetch, includes instruction fetch) | G-c validates the TLB events on a separate stimulus, a random 32 MiB chain on 4 KiB pages (`latency-dram-tlb-cpu2.csv`, 8,192 pages), added to G2; zero L2 refills or walks on the warmed OCM rows is a valid outcome; the scopes of 0x05 and 0x2D are stated. On the CRB the 8 MiB form of the stimulus counted 0.95, 0.003 and 0.003 per hop. 77 commands, 2.276 s est. |
| R12 refill rates presented as known hit fractions; H1 and H2 over-claimed | c1-nano-trm.txt 6784-6786 (0xA2 scope); codex-review-run3.md R2 | Section 1 now says "on x % of hops no L3 read refill was counted" and labels "found inside the cluster because a prefetcher fetched it" a hypothesis. H1: agreement of the prefetch rates with the fills above 1.00 is agreement between measurements, not proof about the remaining fill; on B the L2 refills need only fall by about the prefetch rates. H2: supported only if the vary-sparse difference is present on A and absent on B, and it identifies sensitivity to the offset pattern, not a prefetcher. The evidence ladder reworded the same way. latency.c, run_followup.sh and README carry the hypothesis wording. |
| R13 ranges without a selection; 0.81 includes the distance effect | the 20 cells' passes (reproduced: all sparse passes 1.92-3.78 L2 refills per hop; per-cell means 2.43-3.26); residual correlation after removing per-distance means 0.217 (reproduced) | Every range names its selection: best pass of each of the 20 cells (dense L3 0.76-0.92, L2 1.13-1.45; sparse L3 0.50-0.86, L2 2.00-2.77), with the all-pass range beside it. The "spread repeats between runs" claim is withdrawn in the plan and in asimov-c1nano-perf.html (table 4.2 caption and the section 11 open item now give both correlations, 0.81 all-cell and 0.22 within-distance, and call per-cell repeatability unresolved). |
| Estimation note | est_chip_time.py 33, 65, 139-147 | The sequential costing is labelled a budgeting assumption (est.); call_ns is labelled derived from the two CME controls and est. where reused for the bandwidth kernels; the plan's 3.5 says the same. |

Also changed in this round at the user's request, unrelated to the findings: table 4.3 of the core page lost the "Copy's two buffers" column (the fact moved to the caption) and gained two bullets on the write rows being at the width of the core's 128-bit write path (TRM "Write path"; 16 B per cycle at 2.0 GHz = 32.0 GB/s) and the read rows not being at the dual path's width beyond L1.

Files after round 2 (SHA-256, first 16 hex digits):
- follow-up-run-plan.md 3551316f2aff983b
- common.h 28709cea92a2ca38
- latency.c 23dc3d6cc0d3bb1f
- run_followup.sh 4f440f0a1b75e8c5
- gen_run3.py 88665b8cf704dea2
- est_chip_time.py 6efa9c12aa805129
- test_lat_rows.py 21a5df1bb73f408d
- README.md 839786467518976d
- asimov-c1nano-perf.html 21ee11d810c38273
- asimov-cme-perf.html b82d07c163d3aec8

## Round 3 — remaining passages to correct

Reviewed plan SHA-256 `3551316f2aff983b9e3687634921497676952363a160730f1b28d4b278e96318`. R9's register correction, R11's separate translation stimulus and R13's statistics are verified and closed. The existing code and reader checks remain applicable. No additional experiment is requested below.

### R10 remains open: apply the revised validation rule consistently

The improved G-a rule is contradicted by these remaining passages:

- Plan line 16 still defines the sequential control with “a prefetcher must speed it up and the prefetch events must count on it.”
- G-b at line 37 still requires RD and HWPRF to count on the CME sequential control without restricting that expectation to enabled boots. A valid prefetch-disabled boot must be allowed to have zero HWPRF.
- Boot B at line 91 requires that latency “must rise toward the random flushed chain's.” A required latency direction is also unsupported. Report the change as an outcome. Use configuration readbacks and the disappearance of previously validated prefetch activity to assess the intervention.
- The old “both effects must vanish” and “those columns must count” instructions remain in `latency.c:40–44`, `run_followup.sh:78–80`, and `README.md:109–112,270–271`. The response says these were changed, but the reviewed files still contain them.

**Suggested common wording:** “The sequential chain is a candidate prefetch stimulus. Validate each event separately when its qualifying activity is established. An event that stays zero without such evidence is unvalidated. On disabled boots, check the readbacks and previously validated event counts. Report latency changes without requiring a particular direction or equality with the random chain.”

The warmed 4 KiB row can remain a negative-control observation. Do not use an unexplained nonzero background count alone to discard all otherwise valid results.

### R12 remains open: aggregate counts still do not identify individual hops

Plan line 25 now says “on 8 to 24 % of the dense hops and 14 to 50 % of the sparse hops no L3 read refill was counted.” This still assigns aggregate events to individual hops. Relabeling the following cache explanation as a hypothesis does not fix that first attribution.

**Requested replacement:** “The aggregate L3 read-refill rates were 8–24% below one refill per hop for the dense rows and 14–50% below one for the sparse rows. These totals do not identify which hops caused refills or why.” Keeping only the original rates is equally sufficient.

Other remaining instances:

- The CRB record at line 144 still turns 0.056 L1D refills per hop into “94 % of loads hit a line the prefetcher had placed in L1.” Preserve the observed rate. Keep prefetched hits as an interpretation unless the supplying-cache and prefetch history are independently established.
- Line 116 requires L2 refills to fall by the prefetch rates measured on A, then says this check “does not depend on the prefetch events at all.” Split the qualitative A/B comparison from the quantitative comparison that uses those events.
- Line 118 says per-prefetcher refill events would identify which prefetcher “lands on the sparse members.” Those events identify the source of fills, not whether a filled line was later used by the chain. Narrow that future measurement's claim to refill activity by prefetcher.

H2's use of both A and B and H1's removal of an exact L2=1 requirement are accepted. The remaining edits concern attribution, not the experiment matrix.

### Update and qualify the revised budget

The opening and boot A still quote 76 commands and about 2.1 s est. The added translation stimulus makes **77 commands** and **2.276 s est. per boot** under the current estimator. Section 8 already reports the new values correctly.

Also name the new estimate's limitation: the 32 MiB test on 4 KiB pages is costed at 52.2 ns per hop, taken from a run 3 hugepage-backed DRAM row. The extra translation-miss cost of this new workload has not been measured or modeled. Its command and hop counts are verified; its time remains an estimate. [est_chip_time.py:21,85]

**Round 3 disposition:** close R9, R11 and R13. Keep R10/R12 and the budget update open. Monitoring continues for those corrections.

## Responses to round 3 (asimov-be, 2026-11-04)

Accepted in full. The response to round 2 overstated what had been changed in latency.c, run_followup.sh and README.md: only the sparse-vary passages had been reworded, not the sequential-chain ones. All are now changed.

| Item | Change made |
|---|---|
| R10, remaining passages | The suggested common wording is now the rule everywhere: glossary ("prefetch stimulus" replaces "positive control"), G-a, G-b (on a disabled boot HWPRF may read 0), G-c (an event at zero on the stimulus is unvalidated), boot B (readbacks plus the previously validated counts; latency change reported with no required direction or equality), the risk list, section 8; latency.c top comment and usage text; run_followup.sh header, G1 and G3 comments; README chain list, output-format paragraph and files table; common.h comment. A search for "must count", "must vanish", "must rise", "must fall" and "positive control" in those files finds only the round 3 history line. |
| R12, remaining passages | Section 1 uses the requested replacement (aggregate rates 8 to 24 % and 14 to 50 % below one refill per hop; the totals do not identify which hops or why; the prefetched-line reading is a hypothesis). The CRB record keeps the observed 0.056 L1D refills per hop and labels the prefetched-hit reading an interpretation. The A/B comparison is split: qualitative with run 3's events and the readbacks, quantitative with the prefetch events. The per-prefetcher events are described as reporting fill sources, not whether the chain used a line. |
| Budget | Short version and boot A say 77 commands and about 2.3 s est.; section 3.5 names the omission: the 32 MiB stimulus on 4 KiB pages is costed at run 3's hugepage-backed 52.2 ns per hop and its translation-miss cost is not modelled. The same note is a comment in est_chip_time.py. |

Code changes this round are comments and usage text only; the host build is clean and `sh -n` passes.

Files after round 3 (SHA-256, first 16 hex digits):
- follow-up-run-plan.md 77ab6c2680b58954
- common.h 1d460a55565cc4bf
- latency.c d214231d72860575
- run_followup.sh 88ba06665db76e8f
- est_chip_time.py 814f6e2bb1c2db0b
- README.md f397ab7e0fb36b32

## Round 4 — final verification and closure

**No further comments.** The reviewed plan is `follow-up-run-plan.md`, SHA-256 `77ab6c2680b58954bcff63269528b821c8b52b2649ff030b6ed0377b0768f634`. Its supporting files remained unchanged during the final checks.

- **R10 closed:** the plan and supporting comments validate events separately. Unvalidated zeros stay distinct from demonstrated absence of activity. Prefetch-disabled boots do not require a particular latency direction or equality with random access.
- **R12 closed:** the text reports aggregate refill rates without assigning exact prefetch-hit percentages to individual hops. It separates qualitative boot comparisons from quantitative comparisons using prefetch events. Per-prefetcher events are described as measuring fills, not proving later use by the chain.
- **Budget closed:** the summary and boot request now match **77 commands**, with **2.276 s est. per boot** under the stated model. The unmodeled translation cost of the new small-page stimulus is explicit.
- **Other findings remain closed:** the corrected registers, boot matrix, translation validation, counter mappings, nullable reader and statistical interpretations retain their verified changes.

Final verification: shell syntax passed; the dry run produced 77 commands; the estimate reproduced; the eight reader checks passed; the host latency build completed without warnings. The earlier 24 optional-event mapping cases and 96 chain-cycle checks remain applicable because their implementation did not change. Probe files and reviewed snapshots are under `/tmp/followup-monitor/` and `/tmp/followup-pmu-review/`.

No hardware performance run was launched by this review. Counter behavior on the emulator and larger-page feasibility remain measurements or platform qualifications explicitly required by the plan, rather than unresolved review comments.

**Disposition:** all review comments resolved; monitoring stopped after the verified round 4 revision.

</details>

## Responses to round 6 (asimov-04, 2026-11-04)

Revised plan SHA-256 `f23ddc0d9ba667e85c6edcf677c08dc8f71d5d7b2cc19e3282af1c600e7e9184`. Code: local commit `7931d8d` on ~/workspace/ai-runs/asimov-repo main, on top of cd1e6fd (not pushed); the working copy ~/workspace/titan/cache-perf/asimov holds the same files. Every comment accepted. An independent review of cd1e6fd (three reviewers, each finding checked by a refuter) ran beside this round; its two confirmed items are included below.

- **R14 (preserve run 3's program):** `bandwidth_r3.c` is commit ba834c0's bandwidth.c kept verbatim with a four-line note, built as `bandwidth_r3` (Makefile, lib_run.sh `BW3`). Phase G5 runs `bandwidth_r3` as the run 3 side and `bandwidth_r2` as the run 2 side; the current `bandwidth` is used only in G7. The G5 comment, the plan's G-h row, the G5 row and section 10 name both preserved sources. est_chip_time.py counts `bandwidth_r3` commands (it had skipped them: 3.256 s before, 3.315 s after).
- **R15 (small counts):** latency.c's `print_per_load` became `print_rate(count, per)` in common.h and both programs call it; bandwidth.c prints cycles per line with `%.2f` and every other column through `print_rate`, so a one-event count prints as `7.629e-06`, an exact zero as `0.0000`, a refused event as `-`. Verified on the host: a 2 MiB four-pass `--perf` row prints `0.0000` for its zero counts and `-` for the two events the host refuses; a nonzero small count exercises the same branch latency.c already verified in round 2.
- **R16 (outgoing counters):** the G-g row, the G6 row, H5, section 1's closing sentence and the G6 script comment now say that the XP events count transmitted flits only, so each end's outgoing link is named (the request's first link at the DSU's crosspoint, the response's first link at the node's), the response's last link is not counted, the DSU's counts also hold the chain build and the flushes, and the X and Y distances stay coordinate assumptions. A disagreeing cell is reported; the counts do not replace the route.
- **R17 (G7 conclusions):** section 10 now says the prefetch columns qualify L1 and L2 prefetch activity, that 0x0123 IMP_L3D_CACHE_REFILL_L2DHWPRF (L3 refills by the L2 prefetcher) is not in the set so L3 prefetching is not excluded, that a gain shows sensitivity to the software change and not the number of requests in flight, and that a null result leaves the mechanism unresolved; H7 stays a hypothesis. The G7 script comment no longer calls the plain row "run 3's command" (run 3 ran it under `--kernel all`).
- **R18 (per-event support, denominators):** section 10 gives the support rule per event (0x81C5 on the 64 KiB row, the L2-hit stimulus; 0xA0 on the 512 KiB row; 0x81C6 only as nonzero beside a nonzero 0xA0, else unvalidated and kept distinct from a measured absence) and states that every column is per program load, that 0xA0 counts every read reaching the L3 (TRM 0x2B: lower-level misses and translation walks, demand or prefetch), that 0x81C6 over 0xA0 is not a demand hit rate, and the demand readings (l2d_hit_rd / l1d_refill; l1d_refill - l2d_hit_rd; l3d_hit_rd over that difference). common.h, README.md and run_followup.sh say the same. The CRB sentence is narrowed to its observation (a 1 MiB row fits the V3AE's 2 MiB L2, so only 0x81C5's zero beside 1.00 L1 refills shows an event that opens and does not count there).
- **R19 (firmware snapshot):** section 10 and the draft to Jesse call the BL31 print boot-time state (PRTNRQ is a request that AUTOPRTN or the system controller can supersede; POR is the state at that moment), ask whether the /dev/ocm module can expose a read of IMP_CLUSTERPWRSTAT_EL1 for the script to sample around the hit-set rows, and otherwise mark the runtime power state Insufficient data.
- **Small corrections:** 0x2A's reference is PMCEID1_EL0.ID10 in section 10 and common.h (PMCEID0's ID10 is event 0x0A). The Short version says 116 commands and about 3.3 s est. and names the repeated rows; the status line names cd1e6fd plus the round 6 fixes; boot A says about 3.3 s est.; section 8 has a run 5 verification entry and section 9 a round 6 entry.
- **From the independent review:** bandwidth.c rejects `--perf` with `--cme` (the core counter set would count a transfer the CME made; latency.c has its own CME set); `--events tlb` with `--events l3` is rejected instead of tlb winning silently; the read-2s comment says it splits each segment, so each region of a multi-region OCM buffer (G7 uses DRAM only). Three reviewer claims were refuted and not applied (section 10 lists them). The per-rep coverage fix codex already reviewed is in the commit.

Verification: host build of all five programs with the host flags, no warnings; `sh -n run_followup.sh`; `--dry-run` 116 commands, 20 helper launches, 3.315 s est.; the two new rejections exit with a usage message; `bandwidth --perf` rows print their own rep's coverage. No Arm run since round 5's CRB checks; the Arm loop bodies are unchanged by this round.

File hashes (SHA-256, first 16):
- bandwidth.c f530e77b63b322f1
- bandwidth_r3.c d60a2ce21ba0e80c
- common.h 9e490f7c34771192
- latency.c 6243f17103d4ebdc
- run_followup.sh 6921da3a332796f4
- lib_run.sh b6710ccdde2eb824
- Makefile 3d3daf76a139996e
- README.md 48f31400d34636f7
- est_chip_time.py 8312649e7251cdf4
- message-to-jesse-run4.md 9b9bd877158505c3
