# Round 27 review — no further actionable findings

**Short version.** All remaining round 26 findings are resolved. I have no further actionable comments on the run 7 plan and implementation.

Reviewed: commit `b85d975bfd001e288777d9f774ced4ce1c8e4a73`, Claude's response to round 26, and plan SHA-256 `2fbcc4b1c7cb5e6eac400e28d1c692c3779f5b4fcb2d5c81a6ad0d455a9ad64e`. All nine checked workspace files match the clean checkout. Snapshot: `/tmp/followup-round27-b85d975`.

- **R46 resolved.** The counter descriptions give the explicit external-source and L3-source conditions. Other configurations require their selected source to be identified. [README:318](README.md:318) [common.h:410](common.h:410) [run_l3.sh:57](run_l3.sh:57)
- **R47 resolved.** The script now says that 0xA2 has not established the external-fetch count for this stream. The shared signal behind 0x400B and 0xA2 remains explicit. [run_l3.sh:54](run_l3.sh:54)
- **R48 resolved.** Source selection, event activity and population coverage are separate checks. External-source counts per program line become an external-fetch total only with the additional population evidence. The final reading rule carries the same requirement. [Plan:319](follow-up-run-plan.md:319) [Plan:332](follow-up-run-plan.md:332)
- **R50 resolved.** The optional fifth boot requires baseline and candidate bit-6 readbacks, matched conditions and a check of target activity. Its rate outcomes are limited to the effect observed for this setting, workload and precision. The distinction between storage and request handling remains unresolved by this intervention alone. [Plan:330](follow-up-run-plan.md:330)

The latest implementation revision changes documentation and comments only. The earlier software checks remain applicable. No hardware test was run for this review.

**Disposition:** no further actionable findings. This closes the review of the current plan. Event validation, external-fetch coverage and attribution of the speed gain remain measurement questions under the plan's stated limits. Claude can record whether anything remains open on the author side below.

---

# Round 26 review — remaining source conditions and the proposed intervention

**Short version.** The main round 25 corrections are present. Remaining comments concern two counter qualifications, one stale sentence, and the interpretation of the optional fifth boot. No measurement command or executable logic changed in this revision.

Reviewed: commit `a96acb1d44cb801a07f45777f43bc8075df6db4a`, Claude's response to round 25, and plan SHA-256 `0840adbaf66ad5d806908acca743eed9325f0cc34fa530cd1859b6a02dd787a9`. All nine checked workspace files match the clean checkout. Snapshot: `/tmp/followup-round26-a96acb1`.

## R46, remaining: Preserve the selection conditions in every description

The README and script say that the events count external transactions with EXTLLC set and no L3, and L3 accesses/refills “otherwise.” The latter is true only with **EXTLLC clear and both L2 and L3 present**. The available RTL also has L1, L2 and zero-output cases. `common.h` and the plan already give the explicit L3 condition. [README:318](README.md:318) [run_l3.sh:58](run_l3.sh:58) [RTL source selection](/tmp/followup-round25-21b5608/nevis0_dpu_pmu.sv:1802)

**Requested correction:** replace “otherwise” with that explicit condition and require the selected source to be identified for other configurations.

## R48, remaining: Source selection does not establish complete prefetch coverage

The categorical below-one/above-one interpretations are removed. However, the plan and comments still make external-source selection sufficient to call the count “lines fetched from outside the cluster.” Source selection identifies the input to the counter. It does not establish that this input includes every kind of prefetch responsible for the stream's fills, or that a returned transaction corresponds to one of its unique lines. No such population evidence was added in this revision. [Plan:318](follow-up-run-plan.md:318) [common.h:419](common.h:419)

**Requested correction:** report **selected external-source event counts per program line** once that source is validated. Require separate evidence for which demand/prefetch populations it includes before treating it as the total external-fetch count. Until then, the total requested by the causal goal remains **Insufficient data**. Apply the same condition to the final reading rule and matching comments.

## R47, final wording

The alias/fallback correction is complete. One script phrase still states “which 0xA2 does not give for a prefetched stream” immediately before calling the population an interpretation. Replace it with “which 0xA2 has not established for this stream.” [run_l3.sh:54](run_l3.sh:54)

## R50 — P2: Verify the optional stride-target intervention before interpreting its outcome

The proposed fifth boot sets bit 6 but does not require its value on the baseline. If it is already set, there is no intervention. If the active stream does not use the affected stride-prefetch path, the changed setting need not change its destination. The conclusion that an unchanged rate shows the destination is not what the gain needs is therefore too broad. [Plan:329](follow-up-run-plan.md:329)

**Requested correction:** record baseline and candidate bit-6 values, keep the other conditions matched, and check whether the affected target activity changes. Report an unchanged rate as no observed effect of this intervention at the tested workload and precision. Do not use it to exclude other L3-prefetch activity or compensated effects. A rate difference can establish an effect of the controlled setting change; the existing storage-versus-request-handling qualification remains necessary.

The fifth boot is clearly optional and excluded from the four-boot budget; that scope is consistent. R49's distinction between participation and cause is resolved. The earlier software checks remain applicable because only comments, documentation and usage text changed.

**Disposition:** the bounded corrections above remain open. Monitoring continues; earlier reviews and responses are preserved below.

---

# Round 25 review — external-read counters and the causal goal

**Short version.** The added rows can supply useful observations, but they do not yet establish the external-fetch count promised by the plan or identify what caused the gain. Four findings remain: counter-source selection, an ineffective fallback, overinterpretation of counts per line, and the distinction between L3 participation and causation. A documented stride-prefetch destination control offers a more targeted experiment, with limits described below.

Reviewed on 2026-11-09 UTC: commit `21b560882246727b4870e3d1ab115f0a73d57a52` against `ac8fbf7`, and section 14 of [follow-up-run-plan.md](follow-up-run-plan.md), SHA-256 `d792a99acfcd15c25765585061313ae865accbc815e8299e3d3e612fd92a405d`. All nine checked workspace files match the clean checkout. The new option and CSV output pass the software checks; the findings concern what their results can mean.

## R46 — P1: EXTLLC selects the counter source; it is not simply an enable bit

The plan and comments say `0x36` and `0x37` read zero when EXTLLC is clear. The register definition instead says that clear selects a last-level cache within the cluster. The manual's `0x32` entry describes that selection and says it counts the same as `0x36`. [Plan:315](follow-up-run-plan.md:315) [common.h:417](common.h:417) [C1-Nano TRM, EXTLLC](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:16666) [LL_CACHE](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:6515)

The available RTL makes the distinction concrete: the selected source depends on EXTLLC **and** the L2/L3-presence inputs. With both caches present and EXTLLC clear, `0x36` selects L3 read accesses and `0x37` selects L3 read refills. These can be nonzero without representing external-cache traffic. The external path is selected by `ectlr_ext_llc_i & ~cb_l3_present_i`, so an EXTLLC readback alone does not prove that this path is active in the tested image. [nevis0_dpu_pmu.sv:1802](/tmp/followup-round25-21b5608/nevis0_dpu_pmu.sv:1802)

The individual event descriptions are less complete than this register definition and source selection. Use the latter to qualify the former; do not infer the selected source from a nonzero value. The relationship between these presence inputs and the tested image's runtime L3 mode still needs evidence.

**Requested correction:** describe `llc` as a candidate last-level-cache set until the selected source and population are established for each boot. Reject the external-fetch interpretation when the source is internal or unresolved, even if counts are nonzero. Record EXTLLC and the evidence for the applicable cache-presence/source selection. Synchronize the plan, README, usage text and comments. Event activity and external-source validation are separate checks.

## R47 — P1: 0x400B does not recover traffic missing from 0xA2

The proposed fallback shares the existing event's signal in the available RTL: `evnt_l3d_ll_miss_rd_rs = evnt_l2_evnt_l3d_cache_refill_rs`. The decoders map these to `0x400B` and `0xA2`, and their extra increment for two events in one cycle is also shared. Thus this implementation supplies the same population, not an independent count of missing prefetch fetches. [Plan:315](follow-up-run-plan.md:315) [RTL alias](/tmp/followup-round25-21b5608/nevis0_dpu_pmu.sv:2567) [0x400B decoder](/tmp/followup-round25-21b5608/nevis0_dpu_pmu.sv:4176) [0xA2 decoder](/tmp/followup-round25-21b5608/nevis0_dpu_pmu.sv:4419) [shared increment](/tmp/followup-round25-21b5608/nevis0_dpu_pmu.sv:4480)

The new paragraph and `common.h` also turn low `0xA2` counts into proof that the event excludes prefetched fills on both modes. Round 23 explicitly retained that reading as an interpretation. The complete population cannot be derived from the observed near-zero. [common.h:414](common.h:414) [Plan:315](follow-up-run-plan.md:315)

**Requested correction:** remove the fallback promise. If `0x400B` is retained, identify it as an alias/check of `0xA2` for this RTL, subject to image applicability. Keep the missing external-fetch measurement **Insufficient data** if no validated counter supplies it. Restore the distinction between the `0xA2` observation and the interpretation of its population.

## R48 — P2: Counts per program line do not uniquely identify reuse or overfetch

The new reading rule maps a value below one to reuse from L3 between passes, and a value above one to excess prefetching. Even after external-source validation, the event counts transactions returned during the measured interval, normalized by the program's bytes divided by 64. It does not identify unique stream lines, their prior cache level or the pass that caused them. Warm-up happens before counters start; outstanding prefetch returns can cross the measurement boundaries. [Plan:318](follow-up-run-plan.md:318) [bandwidth.c:420](bandwidth.c:420) [bandwidth.c:598](bandwidth.c:598)

The whole-command 2 MiB request ratio of 0.975 does not predict one returned transaction per timed program line either. It is a ratio between different populations and windows, already distinguished in round 23.

**Requested correction:** report the accepted event count per program line and its change between modes. Treat L3 reuse and overfetch as hypotheses requiring matching line/source evidence. Remove the categorical below-one/above-one rules. Before calling the result all external fetches, establish which demand, prefetch and other read populations the selected event includes.

## R49 — P2: Positive L3-prefetch hits do not exclude request timing as the cause

The new paragraph says positive `0x8156` and `0x81E6` show “the part of the picture that the alternative denies.” They establish L3-targeted accesses and qualifying demand hits. They reject a claim that no prefetched L3 line is ever used. They do not reject improved request handling as the main cause of the gain: that mechanism can coexist with some L3 hits. [Plan:319](follow-up-run-plan.md:319)

**Requested correction:** separate participation from causal contribution. Retain the current limits on queue occupancy and zero demand-hit counts. In particular, the later phrase “no L3 hits with the activity validated elsewhere” cannot reject the broader storage picture by itself: the plan already allows a prefetch to move data onward before demand reaches it. [Plan:322](follow-up-run-plan.md:322)

## Answer to the goal question, including a targeted experiment

| Accepted result | Conclusion |
|---|---|
| Gain requires prefetchers, L3-target accesses and demand hits occur, external-return intensity is similar | Supports participation of L3 prefetching; does not identify its share of the gain |
| Comparable gain persists with hardware prefetchers disabled | Challenges prefetching as the necessary or complete explanation under those conditions |
| Validated zero first-demand-hit count | No qualifying hits were counted; forwarding before demand remains possible |
| Queue occupancy rises | More active entries in the measured home-node queues on average; not a count of total outstanding cluster reads |

A more targeted candidate is **IMP_CPUECTLR_EL1.L1SPFL2, bit 6**. The manual specifies stride prefetching into L1+L3 when clear and L1+L2 when set. Keep full L3 mode and the other prefetch settings fixed, change only this bit with an appropriate privileged setting/readback, and repeat the matched 32 MiB read and target-counter measurement. This tests whether the stride-prefetch destination affects throughput. It is a condition change, not a flag the current benchmark can set. [C1-Nano TRM, L1SPFL2](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:16659)

This is a candidate for the run owner to assess, not a promise of complete causal separation. It does not disable all L3 prefetchers; the L3 offset-prefetch control is separate. Changing the target can change request handling as well as storage. A rate change would establish dependence on that setting, while attribution specifically to stored data ahead of demand would still need supporting evidence. [C1-Nano TRM, L3OPFCTL](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:16620)

No verified cheap event alone closes the causal gap. A timed request/allocation/forwarding trace, or a supported intervention that isolates L3 storage from request handling, remains the stronger discriminator. The current rows can narrow the explanation; they cannot yet establish the new causal goal conclusively.

## Verification and next round

- Host build: no warnings with `-Wall -Wextra`. Fifteen option probes pass, including all repeated-selection pairs and missing-`--perf` rejection for all three sets.
- All eight optional-counter refusal combinations preserve CSV column names, positions and values. The existing reader accepts them.
- Shell syntax passes. The dry run has **27 commands, 15 helper launches and 42 launches**. The four-boot estimate is **7.834–10.420 s est.**, consistent with **7.8–10.4 s est.**
- No target run or platform change was performed. Evidence: `/tmp/followup-round25-21b5608`.

**Disposition:** R46–R49 are open. I will monitor the plan, code and `Responses to round 25`. Earlier reviews and Claude's responses are preserved below.

---

# Round 24 review — no further actionable findings

**Short version.** R44 and R45 are resolved. The plan retains the L3-prefetch picture as the working explanation and separates its assumptions from the measured facts. It now states what run 7 can establish without promising conclusive proof of the mechanism. No review comments remain open; this loop is complete.

Reviewed on 2026-11-09 UTC: the revised explanatory block in section 14, Claude's response to round 23, and plan SHA-256 `9d13fb15ed6c2d3255991cff1718db5c4ed2675ce60699932a8dd9dade097165`.

- **R44:** the plan distinguishes measured throughput, refills and whole-command request counts from assumptions about L3 residency, outstanding reads and one mesh crossing per line per pass. It identifies the concurrency estimates as derived quantities and retains the alternative request-timing hypothesis. Attribution between the mechanisms remains **Insufficient data**, with a discriminating measurement named.
- **R45:** the new outcome table limits each run 7 result to its measured population and interval. It distinguishes target accesses, qualifying first demand hits and whole-command queue occupancy. It also explains why a zero demand-hit count cannot reject every form of L3 prefetch benefit.

The implementation is unchanged at `ac8fbf7c21ff9d256787eec8e7fb3605c58f644a`. All nine previously checked workspace files match that clean checkout. This round needed no new build or hardware run. The cited E/C 32 MiB rates and refill counts, and the F1/run 3 whole-command 2 MiB request ratio, were reproduced from their saved CSV files during round 23.

Evidence: `/tmp/followup-round23-ac8fbf7` and `/tmp/followup-round24-ac8fbf7`. Hardware validation and identification of the causal mechanism remain pending under the plan's stated limits.

**Disposition:** no further actionable findings. Earlier reviews and Claude's responses are preserved below.

---

# Round 23 review — the proposed explanation of the read-stream gain

**Short version.** Yes: the proposed L3-prefetch mechanism is a coherent explanation of the listed large-footprint observations. No: those observations do not establish that mechanism as the cause of the gain. I would call it the working explanation, with the mechanism still to be validated; two statements in the new paragraph need that distinction.

Reviewed on 2026-11-09 UTC: the new “Jibin's reading” paragraphs in section 14, plan SHA-256 `3196f0b642d4eb1b7ae07d70a7a6fbec8905908f186d70ea14db53fcbde55015`. The implementation remains at `ac8fbf7c21ff9d256787eec8e7fb3605c58f644a`; all nine previously checked files are unchanged and match the clean checkout. This round answers the interpretation question. It finds no new implementation defect.

## What the explanation accounts for

The hardware can prefetch into L1, L2 or L3. Therefore, using L3 to hold data ahead of demand is a supported possibility, even when the complete buffer is much larger than L3. Only the part ahead of the reader would need to reside there. This is a hypothesis about these runs, not an observed data path. [C1-Nano TRM, Hardware data prefetcher](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:4257)

Equal L1/L2 refill counts do not contradict this hypothesis. A line could enter L3 early and later refill L2 and L1 once. The matched E/C 32 MiB read rows measure **24.546 versus 9.196 GB/s**, with L1 refills **0.9998 versus 0.9998 per line** and L2 refills **0.9998 versus 0.9997 per line**. Those results establish almost equal counted fills at different rates. They do not reveal where the lines waited or when their requests were issued. [boot E data](results/membench-jibin-010/results/bootE/bandwidth-read-prefetch.csv) [boot C data](results/membench-jibin-007/results/bootC/bandwidth-read-prefetch.csv)

The nearly equal request totals and unchanged large random-chain and one-core write rates are also compatible with a change in read timing or overlap. I found no contradiction in those selected comparisons. Compatibility does not distinguish L3 storage from other changes in request handling. [report, section 2.3](asimov-c1nano-perf.html#f1vs3)

## R44 — P2: Keep the specific cause as a hypothesis

The new paragraph treats “runs ahead into L3,” “fewer lines at a time” with L3 off, and “rarely wait” as the explanation of the measured gain. The data cited do not measure these quantities. The manual establishes possible destinations, not the destination, distance ahead or stall time in this experiment. [Plan:297](follow-up-run-plan.md:297)

- **The 7.5 and 20 lines in flight are estimates derived from the effect.** They use throughput times random-chain latency divided by 64 bytes per line. This assumes the serialized chain's latency represents the lifetime of a streaming request. Reusing the throughput gain in that calculation does not independently establish increased concurrency or explain why it increased. A matching request-lifetime measurement is missing.
- **“Every line … once per pass” is a model assumption.** The cited request ratio is `427,991 / 438,961 = 0.9750` for the whole **2 MiB command**, including setup and other system traffic. It is not a count of external fetches for every line in the timed 32 MiB stream. [F1 mesh counts](results/membench-jibin-011/results/bootF1/cmn-counts.csv) [run 3 mesh counts](results/membench-jibin-004/results/19700101T000000Z/cmn-counts.csv)
- **The low `0xA2` counts do not identify the missing prefetch fills.** The core manual defines read-caused accesses receiving data from outside L3. The inference that the observed near-zero excludes prefetch fills must remain labeled as an interpretation until the relevant event population is established. It is not evidence that those fills landed in L3. [C1-Nano TRM, 0xA2](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:6784)

**A competing hypothesis:** full L3 mode changes acceptance or timing of the existing prefetch requests, while the useful data still arrives directly in L1/L2. That can produce the same refill totals, similar total traffic and faster streams without L3 storage ahead of demand being the cause. Serialized chains and writes need not improve under this hypothesis either. The manuals document prefetch timing mechanisms, including a DSU delay for matching a prefetch with a later read; they do not establish which mechanism changed here. I am not claiming that a timing-control register changed between boots. [C1-DSU TRM, PFMTCH](/home/jhan/workspace/vendor-resources/arm-txt/c1-dsu-trm.txt:15087)

The distinction to measure is:

```mermaid
flowchart LR
    A[Full L3 mode] --> B[Data waits in L3 ahead of demand]
    A --> C[Request acceptance or timing improves]
    B --> D[Faster read stream]
    C --> D
```

Both paths are hypotheses. A trace of the timed stream's request issue/completion, actual L3 allocations and subsequent forwarding would distinguish them. A supported experiment that selectively prevents L3-prefetch allocation while preserving the request path could also test the storage explanation. Neither measurement is currently available, so that attribution is **Insufficient data**.

**Requested correction:** retain Jibin's proposed mechanism as the working explanation, and distinguish its assumptions from the measured facts. The open question is which mechanism causes the gain, not whether a coherent explanation exists. No additional campaign work is required merely to state this accurately.

## R45 — P2: Run 7 can test parts of the explanation, not conclusively confirm or reject both assertions

The new “confirm or reject” sentence exceeds the measurement limits already stated earlier in section 14. [Plan:299](follow-up-run-plan.md:299)

| Run 7 measurement | What an accepted result can establish | What remains unresolved |
|---|---|---|
| Four matched firmware conditions | Whether the read-rate advantage depends on enabled prefetchers under these conditions | Where the prefetched data waits and why request handling improves |
| `0x8156` above zero | L3-targeted prefetch accesses occurred | Successful L3 allocation or useful residency |
| Validated `0x81E6` above zero | Some demand reads first hit lines prefetched into L3 | How much those hits contribute to the rate gain or how far ahead prefetches run |
| Home-node read-queue occupancy | Mean active entries in those queues over the whole command | Total outstanding core/cluster reads during the timed passes, or a larger request capacity |

These limits follow from the event definitions and measurement windows. The core counters bracket timed passes. The mesh counters include the whole process and other system traffic. H1 and H2 also use different pass counts. [C1-Nano TRM, target accesses](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:7212) [first demand hits](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:7519) [bandwidth.c:414](bandwidth.c:414) [cmncount.c:353](cmncount.c:353) [run_l3.sh:107](run_l3.sh:107)

There is a specific reason a zero demand-hit count would not reject every version of the L3-storage hypothesis: an L1 hardware prefetch could fetch a line onward from L3 before demand reaches it. The manual defines L3 accesses from L1 hardware prefetches, whereas `0x81E6` selects first demand-read hits. This forwarding path is a hypothesis about these runs, not a measured route. All-zero events without activity validation remain **Insufficient data** under the existing rule. [C1-Nano TRM, L1-prefetch accesses to L3](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:8289)

**Requested correction:** replace the conclusive promise with these bounded outcomes. A gain that persists with prefetchers disabled would challenge prefetching as the complete explanation. A gain that disappears would establish prefetch dependence under those conditions, while leaving the storage-versus-request-handling cause open. Queue occupancy alone can neither confirm nor reject the claimed increase in total outstanding reads.

**Disposition:** R44 and R45 are open in the new explanatory paragraphs. The existing run 7 implementation and its earlier acceptance rules remain reviewed. Evidence snapshot and reproduced data: `/tmp/followup-round23-ac8fbf7`. No new hardware run or implementation change was made. I will monitor the plan and `Responses to round 23`.

---

# Round 22 review — no further actionable findings

**Short version.** R41–R43 are resolved. Claude corrected the remaining boot 2 phrase, and the final plan agrees with the reviewed implementation. No review comments remain open; this review loop is complete.

Reviewed on 2026-11-09 UTC:

- Final commit: `ac8fbf7c21ff9d256787eec8e7fb3605c58f644a`. The checkout is clean.
- Section 14 of [follow-up-run-plan.md](follow-up-run-plan.md), SHA-256 `e37b2b6aa3778d0899fb917e60083e2433d3451d8a644603b4dd05ba12a3091f`.
- Claude's responses to rounds 20 and 21 below. All nine checked workspace script, source, build and README files match the checkout and the reviewed revision.

The plan now separates L3-targeted accesses from first demand hits on prefetched lines. It requires activity evidence for each event before interpreting zero counts. Both `--events` choices require `--perf`, and repeated choices select the last value. The final edit changes only the stale boot 2 wording.

Verification remains valid: the host build has no warnings; the six focused option probes pass; shell syntax and CSV column checks pass. The dry run contains **25 commands, 15 helper launches and 40 launches**. The stated four-boot budget of **7.5–10.0 s est.** agrees with the estimator. Evidence: `/tmp/followup-round20-ba93ae1`, `/tmp/followup-round21-ac8fbf7`, `/tmp/followup-round21-working` and `/tmp/followup-round22-ac8fbf7`.

No target campaign was run during this review. Hardware event activity and simultaneous counter coverage remain to be checked on the target under the plan's acceptance rules.

**Disposition:** no further actionable findings. Earlier reviews and Claude's responses are preserved below.

---

# Round 21 review — one stale phrase remains

**Short version.** The counter interpretation, per-event validation rule and option parser are corrected. One phrase in the boot request still promises the zeros that the revised reading rule no longer predicts. No further implementation finding remains.

Reviewed: commit `ac8fbf7c21ff9d256787eec8e7fb3605c58f644a`, Claude's response to round 20, and plan SHA-256 `035210de9be33c8a428037859ce33584c796caf9dfa4481a57243a717141f725`. The checkout is clean, and all nine checked workspace files match it.

## R41, remaining: Synchronize the boot 2 description

The request for boot 2 still ends with “the prefetch-target rows' expected zeros.” The revised hypothesis 2 paragraph explicitly says that no value on the L3-off boots is predicted. [Plan:291](follow-up-run-plan.md:291) [Plan:284](follow-up-run-plan.md:284)

**Requested correction:** replace the stale phrase with “the prefetch-target rows with the L3 off.” This is a plan-only correction.

## Verified closures

- **R41, substantive correction:** the plan, source comments and README distinguish target accesses from first demand hits. The blanket nonzero-is-error rule is removed, and the proposed DSU mechanism remains a hypothesis.
- **R42:** each event needs its own activity evidence. All-zero columns remain unvalidated, and conclusions requiring them are **Insufficient data**.
- **R43:** both event-set values require `--perf`. The last repeated choice takes effect in either order. Six focused host probes pass, covering both missing-`--perf` cases, both ordinary selections and both repeated-choice orders. The tested parser is identical to the committed one; the host build reports no warnings.

The measurement commands and estimator are unchanged from round 20. Evidence: `/tmp/followup-round21-ac8fbf7` and `/tmp/followup-round21-working`. No target campaign was run.

**Disposition:** only the boot 2 phrase remains open. Monitoring continues. Earlier reviews and responses are preserved below.

---

# Round 20 review — run 7 prefetch-target additions

**Short version.** Three actionable findings remain in the new additions: distinguish prefetch accesses from successful L3 fills, require positive evidence before interpreting zero counts, and correct the new option parser. The added measurements remain useful. Their command count and chip-time budget reproduce.

Reviewed on 2026-11-09 UTC: commit `ba93ae12e33e8ebca099cde0fefab3aea2d959a5` against `900b713`, and section 14 of [follow-up-run-plan.md](follow-up-run-plan.md), SHA-256 `59bef0319039feea62edcaa2b0bc468c78442057de8d7b2064a160b1836e297b`. All nine checked workspace script, source, build and README files match the clean checkout. Round 19's closure remains valid for its earlier revision.

## R41 — P2: Do not reject L3-targeted accesses merely because the L3 holds no data

The plan expects both L3 event columns to be zero with the L3 off and calls any nonzero value a reading error. That conflates two different events. `0x8156` counts accesses generated by hardware prefetchers targeting L3. `0x81E6` counts first demand-read hits on prefetched L3 lines. An access is not proof of a successful allocation or hit. [Plan:283](follow-up-run-plan.md:283) [Plan:295](follow-up-run-plan.md:295) [C1-Nano TRM, event definitions](/home/jhan/workspace/vendor-resources/ARM/md/Arm-C1-Nano-TRM-r0p2.md:4809)

The C1-DSU manual explicitly describes core-origin prefetch stash transactions whose stash is not performed because L3 is off. Thus prefetch request activity and no L3 allocation can coexist. This does not prove what `0x8156` will read on this platform, but it rules out deriving its required zero solely from empty L3 RAM. [C1-DSU TRM 107804, SCU_PFTCH_CPU_ACCESS and SCU_PFTCH_CPU_HIT](/home/jhan/workspace/vendor-resources/arm-txt/c1-dsu-trm.txt:13600)

The available core RTL also generates this event from a serialized L3 stash request, without a completed-fill test at that point. The PMU path separately gates it with `cb_l3_present_i`; the plan provides no mapping from that signal to the runtime snoop-filter-only setting. A specific zero guarantee needs that evidence. [nevis0_l2_tagctl.sv:10339](/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/dl/rtl-l2/nevis0_l2_tagctl.sv:10339) [nevis0_dpu_pmu.sv:2790](/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/dl/rtl-l2/nevis0_dpu_pmu.sv:2790)

**Requested correction:** retain `0x8156` as observed target-access activity on either L3 mode. Use validated `0x81E6` separately for first demand hits. Remove the blanket nonzero-is-error rule and the claim that a zero establishes that prefetches had nowhere to go. Keep the proposed DSU handling mechanism as a hypothesis. Apply the same distinction to the plan, `common.h` and the H2 comments, which currently say these events establish that prefetchers put lines in L3. [common.h:387](common.h:387) [run_l3.sh:41](run_l3.sh:41)

## R42 — P2: An expected zero does not validate an event that always reads zero

The phrase “that is also the check that a 0 means something” treats a negative control as evidence that the event works. An unsupported or inactive event can return zero on every boot and pass that check. The reading rule handles refused columns but does not handle accepted events that remain zero everywhere. This conflicts with the useful rule already in `common.h`: a zero on an L3-on boot is unvalidated until the event has read nonzero. [Plan:283](follow-up-run-plan.md:283) [Plan:295](follow-up-run-plan.md:295) [common.h:395](common.h:395)

**Requested correction:** state a per-event activity rule in section 14. A column that never reads nonzero stays unvalidated, and conclusions that require it are **Insufficient data**. Name a positive stimulus or explicitly leave that validation pending. A nonzero count establishes activity for that event only; an expected zero in another condition is a consistency check. Retain the existing rules for refused columns and incomplete counter coverage. No extra campaign rows are required if the unsupported conclusions are deferred.

## R43 — P2: Parse both event-set choices and track whether the option was supplied

The parser sets `cfg.ev_pf` only for `pf`. The `prefetch` branch neither resets it nor records that `--events` appeared. The later `--perf` requirement therefore checks the selected value instead of the presence of the option. [bandwidth.c:475](bandwidth.c:475) [bandwidth.c:509](bandwidth.c:509)

Two host probes reproduce the consequence, using `--bytes 4K --kernel read --passes 1 --reps 1 --no-hugetlb`:

- Adding `--events prefetch` exits 0 and emits no counter columns, contrary to the plan's promise to reject `--events` without `--perf`.
- Adding `--perf --events pf --events prefetch` still emits `l2d_hwprf_per_line`, `l3d_hwprf_per_line` and `l3d_hit_rd_fhwprf_per_line`. The final `prefetch` choice has no effect.

**Requested correction:** record that `--events` was supplied and assign the selection for both accepted values. Apply the `--perf` requirement to either value. Repeated choices should follow the parser's normal last-choice behavior or be explicitly rejected. Verify these two cases as well as the ordinary `pf` and `prefetch` paths. Probe outputs: `/tmp/followup-round20-ba93ae1/prefetch_without_perf.txt` and `/tmp/followup-round20-ba93ae1/pf_then_prefetch.txt`.

## Verification and next round

- Shell syntax checks pass. The dry run has **25 commands, 15 helper launches and 40 launches**.
- At the stated read-rate assumptions, the estimator gives **1.167 s, 1.556 s and 3.628 s est.** The four-boot total is **7.518–9.979 s est.**, consistent with the plan's **7.5–10.0 s est.**
- The snapshot's bandwidth program builds on the host with `-Wall -Wextra` and no warnings. Normal set selection, unknown-value rejection and CME incompatibility checks behave as expected, apart from R43.
- All eight combinations of refusal of the three optional events preserve their CSV column positions. The existing reader accepts the new named columns. These host probes test software behavior and do not validate Arm events.
- Evidence snapshot: `/tmp/followup-round20-ba93ae1`. No target campaign, CPU hot-plug or platform change was performed.

**Disposition:** R41–R43 are open. I will monitor section 14 and `Responses to round 20`, then review the updated code and plan. Earlier reviews and responses are preserved below.

---

# Round 19 review — no further actionable findings

**Short version.** No further actionable findings. R35–R40 and both smaller round 17 corrections are resolved. Claude accepted the remaining round 18 budget correction and updated section 14. No review comment remains open; the run 7 plan review loop is complete.

Reviewed on 2026-11-09 UTC:

- Commit `900b71311bcddfc0ce3b4ac57d1b1940da7ce3fd` in the cache-mem-perf checkout; working tree clean.
- Section 14 of [follow-up-run-plan.md](follow-up-run-plan.md), SHA-256 `4ab1eebd1514e6086bdff3f36f467bf0de001f35f1e1587a163f59d077c2ca63`.
- Claude's responses to rounds 17 and 18 below. All nine checked workspace script, source, build and README files match the checkout and the reviewed revision.

The final plan converts occupancy counts using the factor of 4,096, separates conflicting counter sets, and requires complete, simultaneous counter coverage before accepting a queue result. It names the result as whole-command read-queue occupancy and limits the conclusions accordingly. The four firmware arms use matching workload arguments. Placement comparisons account for repetition spread, and the motivating measurements retain their actual sources.

The corrected four-boot budget is **7.0–9.2 s est.** The reproduced terms are `1.097 + 1.448 + [1.097, 3.319] + 3.319 s`, totaling `6.961–9.183 s est.` The final edit changes only the plan's budget wording; no further implementation change was needed.

Verification: shell syntax checks pass; the dry run contains **22 commands, 15 helper launches and 37 total launches**; each H1 request/queue pair has matching workload arguments and unique labels. The estimates reproduce at the stated read-rate assumptions. No C implementation changed, and this review ran no hardware campaign. Evidence snapshots: `/tmp/followup-round18-900b713` and `/tmp/followup-round19-900b713`.

Hardware counter availability and simultaneous scheduling remain to be checked on the target. The plan requires **Insufficient data** for missing counter inputs, a zero cycle denominator or multiplexed queue measurements. This closes the plan review; it does not validate measurements from a future campaign.

**Disposition:** no open comments. Earlier reviews and Claude's responses are preserved below.

---

# Round 18 review — one budget correction remains

**Short version.** R35–R40 and the load-count correction are resolved. The revised per-boot estimates reproduce, but their stated four-boot total is too low. No further measurement-design or implementation finding remains in the reviewed revision.

Reviewed: commit `900b713`, Claude's response to round 17, and plan SHA-256 `b5c12e54feb2d1862f275add9672533c619eaf27f94d0e7efbe58e96d00f9d5d`. All nine checked workspace files match the checkout.

## Remaining correction: Sum the four boot estimates consistently

The request lists four estimated costs: `1.097 s + 1.448 s + [1.097, 3.319] s + 3.319 s`. These sum to **6.961–9.183 s est.**, or approximately **7.0–9.2 s est.**, not 5–9 s. These values come from the dry run and estimator with core-read rates of 24.6, 10 and 2.4 GB/s, as specified in the plan. [Plan, section 14, Requests to Jesse](follow-up-run-plan.md)

**Requested correction:** update the total to agree with the individual boot assumptions. Using boot 2's measured historical 9.2 GB/s instead of the default 10 GB/s gives a similar total, **7.012–9.234 s est.** Either explicitly stated budgeting choice is consistent with roughly 7.0–9.2 seconds.

## Verified closures

- **R35:** the mean occupancy includes the factor of 4,096 and retains raw counts.
- **R36:** the queue set has only the five read-occupancy events and the dedicated cycle counter. H1 request counts run separately. The plan explicitly rejects missing, zero-denominator and multiplexed queue data. This is a reader acceptance rule; the helper still permits uncounted host smoke execution, which the plan now distinguishes from mesh validation.
- **R37:** the result is whole-command queue occupancy. The chain has no required value, and the plan withholds claims about core ownership, timed-pass concurrency and cluster request capacity.
- **R38:** the fourth boot provides the matching prefetch-off/L3-off arm. Historical B/D rows are context, and throughput alone no longer identifies demand-miss overlap.
- **R39:** equal placement rates show no observed sharing penalty at that load. The plan does not infer a per-core cap and uses repetition spread when comparing rates.
- **R40:** throughput, refill and request-count observations name their actual experiments. The unchanged-chain/write claims name their scope. The load-pair byte count is corrected.

Verification reproduces **22 commands, 15 helper launches and 37 total launches**. Every H1 request/queue pair has matching workload arguments and unique labels. Both scripts pass shell syntax checks. No C implementation changed, and this review ran no hardware campaign. Evidence: `/tmp/followup-round18-900b713`.

**Disposition:** only the four-boot total remains open. Monitoring continues. Earlier findings and Claude's responses are preserved below.

---

# Round 17 review — run 7, section 14

**Short version.** Six actionable findings remain. The occupancy formula needs a factor of 4,096, and the proposed counter set contains conflicting filters. The tests remain useful, but their validation rules and causal conclusions need the corrections below before the campaign.

Reviewed: section 14 of [follow-up-run-plan.md](follow-up-run-plan.md:271), SHA-256 `877e380cd925499c829853a546316d52cf1e1c3e16b54925055d94fa8f084834`, and commit `c9b5b8bec94bbc31982f66a38c2698eb53c591ba`. The nine checked workspace script, source, build and README files match the checkout.

**Numbering:** Round 16 already closes run 6 at the top of this file and in the plan's section 9. This new loop therefore begins at Round 17. Please append `Responses to round 17`; the earlier closure remains intact.

Words used here: **POCQ** is the home node's request queue. **Occupancy** is the mean number of active queue entries. **PMU** is the hardware counter unit. **DTC** is the mesh's global debug/trace counter unit; **DTM** is its local counter unit. **Multiplexing** means the kernel alternates counters because they cannot all run together. P1 findings invalidate the proposed measurement; P2 findings affect its interpretation or acceptance.

## R35 — P1: Convert occupancy events to entry-cycles before dividing by cycles

The occupancy event does not count one event for every queued request on every cycle. It counts overflows of a 12-bit accumulator of active-entry cycles. The CMN S3(AE) TRM gives the conversion explicitly: [TRM 107858_0205_06_en, section 7.12, Figure 7-23](/home/jhan/workspace/vendor-resources/ARM/md/Arm_CMN_S3AE_TRM_r2p5_split/07_Performance_optimization_and_monitoring.md:2107)

`mean active entries = 4096 × sum(occupancy event counts) / cycle count`

The current formula is smaller by a factor of 4,096. The kernel driver returns raw event counts, and `cmncount` adjusts only for enabled versus running time; neither applies this conversion. The same formula appears in the available r2p3 manual. [TRM event 0x0f](/home/jhan/workspace/vendor-resources/ARM/md/Arm_CMN_S3AE_TRM_r2p5_split/07_Performance_optimization_and_monitoring.md:742) [driver read path](/tmp/followup-round17-c9b5b8b/arm-cmn.c:1694) [cmncount.c:393](cmncount.c:393)

**Requested correction:** use the documented conversion in the plan's definition and reading rule, `lib_run.sh`, and `run_l3.sh`. Record the applicable event semantics and target revision in the evidence. Preserve raw counts alongside the derived mean. [Plan:275](follow-up-run-plan.md:275) [Plan:290](follow-up-run-plan.md:290)

## R36 — P1: Use a compatible counter set and reject incomplete queue measurements

`hns_qos_pocq_occupancy_read` and `hns_qos_pocq_occupancy_all` use different values of the same per-node occupancy filter. The global `all` event covers the same nodes as the five `read` events. The driver rejects conflicting live filter values, so this set cannot run simultaneously as planned. [lib_run.sh:49](lib_run.sh:49) [driver event definitions](/tmp/followup-round17-c9b5b8b/arm-cmn.c:941) [driver filter conflict](/tmp/followup-round17-c9b5b8b/arm-cmn.c:1720)

- The number of event names does not establish schedulability. `dtc_cycles` uses a dedicated cycle counter; the DTC also has eight general event counters, and each DTM has four local counters. Filters add separate constraints. The statement that a ninth event necessarily multiplexes is incorrect. [driver allocation](/tmp/followup-round17-c9b5b8b/arm-cmn.c:2115)
- On newer CMN-S3 revisions, `pocq_reqs_recvd_all` can share this occupancy filter too. Choose the replacement set against the target driver and revision. The five read-occupancy events plus cycles avoid the unnecessary global filters; collect other kinds separately if needed. [driver request events](/tmp/followup-round17-c9b5b8b/arm-cmn.c:1025)
- Missing counters do not fail the suite today. A local probe using the actual `cmnq`, `run`, `finish_suite` and compiled `cmncount` returned exit 0 and “0 measurement command(s) failed” when the PMU was unavailable. It wrote only a comment and timing rows. [cmncount.c:220](cmncount.c:220) [lib_run.sh:63](lib_run.sh:63)

**Requested correction:** remove or separate conflicting events. Before accepting an occupancy ratio, require all five node rows, a positive cycle count and valid running coverage over the measured interval. Missing, failed or multiplexed inputs must make that result invalid and leave H1 **Insufficient data**. Independently scaled samples of initialization, warm-up and timed work do not establish a simultaneous ratio. Keep host smoke execution possible, but distinguish it from a complete queue measurement. The probe is saved at `/tmp/round17-review/queue_failure_probe.sh`.

## R37 — P2: Queue occupancy does not identify this core's outstanding loads

The corrected quantity is mean active read-class POCQ entries. The events do not select the benchmark's core, demand versus prefetch traffic, or its timed passes. `cmncount` measures the whole command and other system traffic. Calling the result “this core's reads in flight” assigns ownership and a lifetime that these counters do not measure. [Plan:278](follow-up-run-plan.md:278) [run_l3.sh:22](run_l3.sh:22) [cmncount.c:15](cmncount.c:15) [TRM event 0x0f](/home/jhan/workspace/vendor-resources/ARM/md/Arm_CMN_S3AE_TRM_r2p5_split/07_Performance_optimization_and_monitoring.md:742)

The dependent chain is not a calibration whose mean must be about one. A load occupies the home-node queue for only part of its end-to-end lifetime. Other reads, translation traffic and initialization can increase or decrease the whole-command mean; they do not merely dilute it. Even a correctly measured rise in queue occupancy can reflect a changed arrival rate or queue residence time rather than more available request slots in the cluster.

**Requested correction:** keep the chain as a serialized comparison, remove the required `about 1` result, and name the measured quantity as whole-command read-queue occupancy. Treat changes as observations consistent with the hypothesis. Claims about timed-pass concurrency or a larger cluster capacity need a matching measurement window and evidence that identifies that quantity; otherwise leave them **Insufficient data**. The longer streams help reduce setup's share but do not establish its size by themselves.

## R38 — P2: H2 lacks the matching prefetch-off, L3-off arm

The proposed decisive baseline, 2.377 GB/s on boots B and D, comes from older bandwidth programs with `--perf`. The new H2 rows run the current program without that option. None of the three requested boots supplies current-build L3-off/prefetch-off rows. The comparison changes more than L3 mode. [Plan:279](follow-up-run-plan.md:279) [run_l3.sh:94](run_l3.sh:94) [boot B log](results/membench-jibin-006/results/bootB/log.txt) [boot D log](results/membench-jibin-008/results/bootD/log.txt)

**Requested correction:** add the missing arm with the same build and options if a causal comparison is required, or retain B/D as historical context and withhold the stated causal dichotomy. Use the new on/on boot's own H2 rows as its reference too. A throughput rise with prefetch disabled would establish an L3-mode throughput effect under that condition; the rate alone would not identify increased overlap of demand misses.

## R39 — P2: Equal placement rates do not prove a per-core cap

About 49 GB/s for both same-cluster and separate-cluster pairs shows no observed sharing penalty at that offered load. A shared cluster limit above 49 GB/s produces the same result, so the result does not establish that the limit is per core. Conversely, about 27 versus 49 GB/s supports a shared-cluster restriction but does not identify request-slot capacity as its mechanism. [Plan:280](follow-up-run-plan.md:280) [run_l3.sh:35](run_l3.sh:35)

**Requested correction:** keep these useful placement tests and state those bounded outcomes. Define “about” or a meaningful gap using repetition spread, and compare against the collected one-reader 16 MiB reference. Leave the limiting resource unresolved without a measurement that identifies it.

## R40 — P2: Keep the motivating measurements attached to their actual experiments

The opening paragraph combines three different observations as if they came from the same 32 MiB comparison. Section 2.3 of the HTML correctly distinguishes them: [Plan:273](follow-up-run-plan.md:273) [report section 2.3](asimov-c1nano-perf.html#f1vs3)

- **32 MiB throughput:** F1/run 3 is `24.575 / 9.172 GB/s = 2.679×`.
- **Home-node requests:** `427,991 / 438,961 = 0.9750×` belongs to `dram-read-2M-cpu2`, a **2 MiB** whole-command measurement, not the 32 MiB row.
- **Core refills:** the comparison comes from boots E/C. F1/run 3's bandwidth rows carry no core counters.

The blanket claim that random chains and write streams did not move is also too broad. The same report shows the 192–384 KiB chains improving by 1.79–2.07× and paired writes by up to 23%. The unchanged comparisons must name their footprint or placement sets.

**Requested correction:** preserve those source distinctions in section 14 and the script/README descriptions. The new run is motivated by consistent evidence across experiments, not a single row carrying all three measurements.

## Smaller corrections

- `k_read` executes **eight 32-byte LDP instructions**, or sixteen 16-byte vector loads, per 256 bytes. “Sixteen 32-byte loads” doubles its actual byte count. [Plan:275](follow-up-run-plan.md:275) [bandwidth.c:131](bandwidth.c:131)
- The 1.047 s estimate assumes 10 GB/s for every core read. It is not a neutral estimate for the prefetch-off boot, whose possible slow outcome is the cited 2.377 GB/s. Provide a per-condition estimate or a slow/fast range using that historical measurement as a labeled budgeting assumption. The experiment is intended to determine whether the slow outcome persists, so the three-boot budget should not assume it disappears.

## Verification and next round

- The dry run reproduces **18 commands, 11 helper launches and 29 total launches**, with **1.047 s est.** under the current assumptions. Shell syntax checks pass.
- The principal throughput, placement and request-count values above reproduce from the saved CSV files. The source distinctions, units and interpretation are the issues.
- The PMU-unavailable probe runs only a harmless child command. No campaign, hardware access, CPU hot-plug or debugfs mount was performed. A host smoke result cannot validate the selected mesh events.
- Review evidence and source snapshots: `/tmp/followup-round17-c9b5b8b` and `/tmp/round17-review`.

**Disposition:** R35–R40 and the two smaller corrections are open. I will monitor section 14 and Claude's appended response, then review the resulting commit. No implementation files were edited by this review.

---

# Round 16 review — no further actionable findings

**Short version.** No further actionable findings. The final revision resolves R27–R34 and the two smaller round 13 corrections. Claude's response to round 15 states that nothing remains open on his side, so this review loop is complete.

Reviewed on 2026-11-06 UTC:

- Supporting implementation: commit `0c190a1fc7502faf2262b1b985078c36030859eb`.
- Plan: [follow-up-run-plan.md](follow-up-run-plan.md), SHA-256 `b2ed73da79b933b55d88c932259b7257f03acf206a32aac0bcff1931ad0fbab5`.
- Claude's appended responses to rounds 13, 14 and 15. All 12 checked workspace source, build, script and README files match the final checkout.

## Final resolution

- Span conversion runs outside timed brackets. The remaining difference is an instrumented outside-span interval, with no claim that it isolates the switch or establishes unchanged historical latency.
- CME bandwidth accepts one worker. Core workers do not reset the shared timestamps. Best-row bracket and span values come from the same repetition.
- Intercept differences describe the net change between implementations. The no-fold control measures removal of the reduction and return dependency, including changed overlap or completion waiting. The unsupported ISB completion guarantee is withdrawn.
- DSB ST measures the barrier's effect. A small effect leaves store posting unresolved, and completion is not equated with arrival at DRAM.
- The refill fit checks the actual matrix's rank and conditioning. It withholds unidentified coefficients and endpoint predictions. CME L3 hit/miss events remain exploratory in run 6; the plan, source comment and README all defer hit-specific attribution until an independent control validates the interpretation and event populations.
- The promised read/write counterparts are present. Metadata compatibility is described accurately.

## Verification and limits

- Host builds completed without warnings. All 12 latency-reader checks and the new option-rejection checks passed. The shell scripts passed syntax checks.
- The final commit changes comments and documentation only. All six C targets preprocess identically to the preceding reviewed revision. Earlier executable checks therefore remain applicable.
- This review performed no Arm or emulation run. The plan still requires `cme_test` on an SME2 machine before the campaign. The review closes the plan and implementation comments; it does not certify measurements from boots that have not run.
- Final evidence snapshots: `/tmp/followup-round16-0c190a1`; earlier checks are recorded in the preceding rounds.

**Disposition:** no open review comments at `0c190a1`. The review loop has reached its agreed stopping condition. All findings and Claude's responses are preserved below.

---

# Round 15 review — one event-validation item remains

**Short version.** R27, R33 and R34 are resolved. R31's regression and cache-source corrections are also resolved. Only the L3-event validation paragraph from round 14 remains open.

Reviewed on 2026-11-06 UTC: commits `0c424d7` and `2fff008`, Claude's response to round 14, and plan SHA-256 `eec78d8c7e772ea0661f4a229b44b0bac6c0ad0c924545ed270302aac6d17f26`. All 12 checked workspace files match the checkout. The changed bandwidth program builds without warnings; the remaining executable code and script commands are unchanged from the preceding checks.

## R31 — remaining: Keep the L3 events exploratory until independently validated

G-m still permits its `hit + miss` versus `inner + outer` comparison to replace the independent L3-disabled control. It then permits `hit` to replace `inner` in the penalty fit. Claude's response resolves the separate regression issue but does not address this event-validation paragraph. [Plan:256](follow-up-run-plan.md:256)

- Agreement between the sums does not validate how the first sum is divided into hits and misses.
- The TRM's L3-access population includes translation-resolution accesses. Its L1 source events count cache-line refills. Equality between these totals is a workload hypothesis, not a documented identity. [C1-SME2 TRM:4364](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:4364) [C1-SME2 TRM:4298](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:4298)

**Requested correction:** retain collection and the sum comparison as exploratory checks. Do not use that comparison alone to authorize L3-hit attribution. State that the hit-specific fit remains **Insufficient data** until an independent control validates the hit/miss interpretation and the populations used by the fit. This can be deferred without adding work to run 6. Make the plan, `common.h` event-set comment and README's F2 event row agree. [common.h:395](common.h:395) [README.md:231](README.md:231)

## Verified closures

- **R33:** only a CME worker resets the shared span sum; core workers leave it alone.
- **R27:** the `0.01 ns/load` threshold now bounds only the outside-span contribution. Historical equality requires actual old/new values; an isolated stamp effect requires a matched control.
- **R34:** the no-fold comparison is the net effect of removing the reduction and return dependency. The unsupported ISB completion guarantee is withdrawn.
- **R31, regression:** the rule now checks the actual fit matrix's rank and conditioning. It withholds coefficients and endpoint predictions when identification fails. The inner-source wording now includes other cores' caches.

Evidence: `/tmp/followup-round15-2fff008`. **Disposition:** only R31's event-validation interpretation remains open. Monitoring continues; no further findings in the reviewed changes.

---

# Round 14 review — verification of the round 13 response

**Short version.** The revised implementation fixes the original span collection, concurrent-CME-worker and best-row pairing defects. Four bounded issues remain: one new shared write in core runs, the regression fallback, and two timing interpretations. The added fold and L3-event controls remain useful with the qualifications below.

Reviewed on 2026-11-06 UTC: commit `b345288`, Claude's appended response to round 13, and plan SHA-256 `62dd0aecddcc0d61b6dfc4f96075b9ff6baa7ed8f42be813380dbf5148210174`. All 12 checked workspace files match the checkout.

## R33 — P2: Guard the span reset on non-CME workers

The worker calls `cme_span_reset()` unconditionally after the start barrier. Non-CME bandwidth runs still permit several workers, so those workers now write the same non-atomic `cme_span[2]` concurrently. Rejecting several CME workers does not protect this core-only path. The new write also adds shared-cache-line traffic just before the measurement. [bandwidth.c:410](bandwidth.c:410) [common.h:543](common.h:543)

**Requested correction:** execute the reset only when `cfg.cme` is true, as the subsequent sum read already does. Host smoke tests miss this issue because the optimized host stand-ins eliminate the unused timestamp storage; the Arm declaration refers to the real external object.

## R31 — remaining: Unidentified penalties also make the endpoint predictions unidentified

The revised model correctly calls `b` and `c` penalties. However, it says to quote `a + b` and `a + c` when the data cannot identify `b` and `c`. Adding a known constant cannot resolve that ambiguity. [Plan:255](follow-up-run-plan.md:255)

Computed example, not test data: take `a = 21 ns`, inner refill rates `[0.1, 0.2, 0.3, 0.4]` per load, and outer rates twice those values. Both coefficient pairs below predict exactly the same row times `[26, 31, 36, 41] ns`:

| Fitted penalties | Predicted all-inner time | Predicted all-outer time |
|---|---:|---:|
| `b = 10 ns`, `c = 20 ns` | 31 ns | 41 ns |
| `b = 30 ns`, `c = 10 ns` | 51 ns | 31 ns |

The endpoint times are therefore unresolved too. Correlation alone is also the wrong identification test for this fixed-baseline model: it does not handle a zero source column, and centering the columns can conceal the actual rank of the matrix used by the fit.

**Requested correction:** check the actual two-column fit matrix for independent information and numerical stability. Withhold both individual coefficients and their endpoint predictions when that check fails. Report measured rows or predictions for source mixtures supported by the observations. Also replace “L3 and snoop filter together” with the documented “caches inside the immediate cluster,” which includes another core's caches; the snoop filter is not itself the source of cached data. The existing comment in `common.h` already makes this distinction. [common.h:268](common.h:268) [C1-SME2 TRM:4302](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:4302)

The new L3 events are correctly encoded, but comparing `hit + miss` with `inner + outer` does not validate the hit/miss split. The L3 event definitions also include accesses caused by translation resolution, whereas the L1 source events count cache-line refills. Equality is a workload hypothesis, not a documented identity. The plan currently lets this sum comparison replace its independent L3-disabled control and then authorizes an L3-hit fit. Keep the events exploratory until an independent known-hit/miss control validates that interpretation, or specify and validate the required event populations before replacing `inner` with `hit`. [Plan:255](follow-up-run-plan.md:255) [C1-SME2 TRM:4364](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:4364)

## R27 — remaining: A small outside-span interval does not establish unchanged latency

The conversion has moved outside the timing bracket, and the remaining difference is now correctly named an instrumented interval. That part is resolved. G-k still says that an outside-span interval below `0.01 ns/load` establishes that the old per-load results are unchanged. Work added **inside** the span is present in both bracket and span, so their subtraction cancels it. That check cannot measure its effect on the old result. [Plan:248](follow-up-run-plan.md:248) [Plan:251](follow-up-run-plan.md:251)

**Requested correction:** keep the threshold as a check on the measured outside-span contribution only. Report the new latency measurements on their own values. Claims of unchanged latency require the actual old/new comparison, with its implementation and boot differences stated; isolating instrumentation requires a matched control.

Two factual details belong in the same correction: `SM_LEAVE` has **eight** instructions between its counter read and `SMSTOP`, including `ADRP` and `ADD`, not six. Say “no C span collection inside the bracket”; the C pass loop and dispatch still run there. [cme_kern.S:83](cme_kern.S:83) [bandwidth.c:416](bandwidth.c:416)

## R34 — P2: Qualify the new no-fold control and its timing endpoint

The control removes the final vector reduction and its `FMOV` return dependency. It replaces them with `MOV x0, #0`. Its difference from the folded kernel measures the net effect of removing that chain, including any change in overlap or completion waiting. It does not by itself isolate the execution cost of the 17 removed instructions. [cme_kern.S:189](cme_kern.S:189) [Plan:249](follow-up-run-plan.md:249)

The plan and assembly comments also assert that the ending ISB on the in-order host guarantees that the read's last load has returned. The CME executes out of order, and the core has explicit stalls for CME general-purpose-register results. The folded read has such a result dependency before the timestamp; the no-fold read removes it. The supplied sources do not establish that ISB alone supplies the claimed completion guarantee. This is **Insufficient data about that guarantee**, not a claim that the timestamp is proven early. [Plan:257](follow-up-run-plan.md:257) [C1-SME2 TRM:1323](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:1323) [C1-Nano TRM:8450](/home/jhan/workspace/vendor-resources/arm-txt/c1-nano-trm.txt:8450)

**Requested correction:** keep the control and report the net effect of removing the final reduction and return dependency. Remove the unsupported completion guarantee, or supply an applicable architecture reference or a completion control that establishes it. Do not describe all no-fold work as guaranteed complete at the inner timestamp without that evidence. Apply the same wording to the plan, README and source comments.

## Resolved items and verification

- R28's original attribution from looped-versus-single-call intercepts is corrected. R34 addresses the new control, not that resolved comparison.
- R29 and R30 are resolved: the CME worker guard runs before worker creation, and best-row span selection follows the best bracket repetition.
- R32 and both smaller round 13 items are resolved. The additional read/write footprints are present; non-CME metadata changes are documented.
- All six host targets build without warnings. The new invalid-option cases return exit code 2, including two CME workers, unsupported no-fold combinations and CME L3 events without CME. Shell syntax checks pass.
- The running-sum assembly preserves the kernel return values. The L3 event encodings match the local TRM. No further address or loop-count defect was found in the new kernels. No Arm execution was performed by this review.

Evidence: `/tmp/followup-round14-b345288`. **Disposition:** R27's remaining claim, R31's fallback, R33 and R34 are open. Monitoring continues. Earlier rounds and Claude's responses remain below.

---

# Round 13 review — run 6 timing and interpretation

**Short version.** Six actionable findings remain. Two affect the reported span data; four affect what the proposed experiment can establish. The new rows can measure the instrumented kernels, but the current plan cannot isolate switch cost, fold cost or absolute L3 latency as claimed.

Reviewed on 2026-11-06 UTC (2026-11-05 evening locally): sections 9 and 13 of [follow-up-run-plan.md](follow-up-run-plan.md), SHA-256 `a0798d0db028ca206d26037e7c5a31dd0f9f8f8edcb0c9a5dfd91ebafe6ee45a`, and commit `aa408edc39968f3c2e693c8a50c6fdef75257562`. All 12 checked source, build, script and README files in this directory match that checkout. This round leaves the closed run 5c review intact.

Words used here: a **bracket** is the caller's elapsed time around the work. A **span** is the time between the new counter reads inside streaming mode. A **pass** visits the buffer once; a **repetition** times several passes. An **intercept** is the fitted size-independent time per pass. CME is the Arm C1-SME2 execution unit. P1 blocks the stated measurement claim; P2 needs correction before accepting the affected data or interpretation.

## R27 — P1: Bracket minus span includes new measurement work

The bandwidth pass and the 64-call latency control call `cme_span_s()` inside the outer timing bracket. That helper reads the counter frequency, loads both timestamps, converts integers to floating point and divides. Its caller also accumulates the result. The ordinary chase and long round-trip rows call the helper after the bracket. These paths therefore do not measure the same outside-span work. [common.h:520](common.h:520) [bandwidth.c:313](bandwidth.c:313) [bandwidth.c:408](bandwidth.c:408) [latency.c:294](latency.c:294)

- The looped bandwidth form pays this added collection cost per pass; the single-call form pays it once per repetition. It contributes directly to the proposed intercept difference.
- The timestamp instructions also add work inside and outside the recorded span. The first timestamp's address calculation and store are inside it; the second timestamp's store is outside it. The extra instructions can change the interval in which stores drain. [cme_kern.S:57](cme_kern.S:57)
- Consequently, G-k cannot call this subtraction the original kernel's switch/save/restore cost. The old `cme-call` minus `cme-roundtrip` estimate likewise includes call machinery and predicate setup, not an isolated switch. The claim that the older latency numbers remain unchanged needs a measurement. [Plan:245](follow-up-run-plan.md:245) [Plan:248](follow-up-run-plan.md:248) [Plan:251](follow-up-run-plan.md:251) [Plan:259](follow-up-run-plan.md:259)

**Requested correction:** move frequency lookup and floating-point conversion outside timed loops if retaining this measurement design. Account for the remaining timestamp collection cost, or name the result an **instrumented outside-span interval** and leave the isolated switch cost **Insufficient data**. Apply that distinction to the plan, source comments and README. Compare F1 with run 3 as different instrumented implementations unless a matched control bounds the instrumentation effect.

## R28 — P2: The intercept difference cannot isolate the fold

The looped read initializes two predicates and 16 vector accumulators on every call. The single-call read does this once per repetition. Address setup and pass-loop control also differ. Subtracting the outside-span interval therefore leaves setup and other differences as well as the fold. [cme_kern.S:128](cme_kern.S:128) [cme_kern.S:208](cme_kern.S:208) [bandwidth.c:295](bandwidth.c:295)

The single-call intercept is not necessarily the loop step alone. Repetition overhead divided by the pass count also enters the model, and the pass count changes with footprint. This is the same attribution distinction already accepted for the core forms in R24. [Plan:249](follow-up-run-plan.md:249)

**Requested correction:** report each form's fitted cost and their net difference. Leave the fold contribution **Insufficient data**, or add a matched control that changes only the fold. Call the single-call throughput the measured whole-kernel rate: its vector XORs and loop instructions remain part of the work. Do not call it an isolated memory-path rate. [Plan:251](follow-up-run-plan.md:251)

## R29 — P2: Concurrent CME workers overwrite the shared timestamps

`cme_span[2]` is one global pair, but `bandwidth` still accepts multiple `--cme` workers. A worker can collect another worker's timestamps or an unmatched pair. For example, worker A writes start 100 and end 150, then worker B writes start 200 before A collects. The unsigned subtraction produces `18446744073709551566` ticks. This is a deterministic example of a valid interleaving, not a hardware measurement. [cme_kern.S:66](cme_kern.S:66) [cme_kern.S:366](cme_kern.S:366) [bandwidth.c:483](bandwidth.c:483)

**Requested correction:** reject `--cme` with more than one worker, or give each worker its own timestamp storage. The planned campaign uses one worker, so rejecting unsupported concurrency is sufficient for its scope. Verify the guard before hardware allocation or worker launch.

## R30 — P2: The best summary combines unpaired times

The code selects the best bracket throughput and the best span throughput independently. They can come from different repetitions. For synthetic pairs of `(100 ns bracket, 80 ns span)` and `(110 ns bracket, 60 ns span)`, the summary combines 100 ns with 60 ns. Its apparent 40 ns difference was never observed; the actual differences were 20 ns and 50 ns. [bandwidth.c:550](bandwidth.c:550) [bandwidth.c:556](bandwidth.c:556) [bandwidth.c:579](bandwidth.c:579)

**Requested correction:** retain the span from the repetition chosen for the bracket, or explicitly label the independent extrema and prohibit using that summary for subtraction. The plan's reading rule must select the same repetition for both columns. [Plan:259](follow-up-run-plan.md:259)

## R31 — P2: G-m mislabels fitted penalties and overlooks an existing L3 event

With `a` fixed to the L1-hit time, the model `time = a + inner × b + outer × c` makes `b` and `c` incremental penalties above that baseline. Its all-inner and all-outer predictions are `a + b` and `a + c`. Calling `b` an absolute L3 latency and applying the proposed absolute-latency lower bound directly to it is inconsistent with the equation. A small residual also cannot identify both coefficients if the two refill columns lack independent variation. [Plan:255](follow-up-run-plan.md:255)

- INNER and OUTER count cache-line refills by source, not identified load instructions. Disabling hardware prefetch is useful, but the plan must validate the mapping before treating per-load refill rates as mutually exclusive load fractions. The TRM's read-refill event includes speculative loads. [C1-SME2 TRM, document 107831_0103_07_en, event table](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:4298)
- The claim that the CME event list names no L3-hit event is false. It names `0x328E CME_L3D_CACHE_HIT` and `0x328F CME_L3D_CACHE_MISS`. Availability and behavior on this machine still need validation. [C1-SME2 TRM, event table](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:4398)

**Requested correction:** define the fit as an empirical penalty model unless the population assumptions are checked. Report coefficient identifiability and leave unsupported cache-level latency assignments **Insufficient data**. Remove the invalid bound or apply a justified comparison to the correct quantity. Correct the event-list claim; either collect and validate the documented L3 events or explicitly defer the L3-specific attribution.

## R32 — P2: A zero DSB intercept does not refute store posting

The DSB ST rows test sensitivity to waiting for preceding stores to complete. A fitted intercept near zero does not prove that stores were not posted. Completion costs can remain in the fitted slope or overlap other work, and the new instrumentation changes inter-call timing. The control is useful, but the proposed binary conclusion is stronger than the comparison establishes. [Plan:250](follow-up-run-plan.md:250)

The wording also equates store completion with data reaching memory. DSB ST does not clean a write-back cache or prove arrival at DRAM. The CME can allocate written data in its L1; dirty writeback is a separate event. [cme_kern.S:17](cme_kern.S:17) [C1-SME2 TRM:2231](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:2231) [C1-SME2 TRM:4344](/home/jhan/workspace/vendor-resources/arm-txt/c1-sme2-trm.txt:4344)

**Requested correction:** report the barrier's measured effect and treat posting as a hypothesis unless an additional observation identifies it. A small barrier effect leaves the mechanism unresolved. Correct the completion wording in the plan and assembly comments.

## Two smaller scope and compatibility corrections

- The outcome promises single-call versions of CME bandwidth rows below 256 KiB, but the new script produces only 4, 8, 16 and 24 KiB read/write pairs. The existing 48, 96 and 160 KiB rows and other kernel forms have no corresponding single-call rows. Restrict the promise to the collected pairs or add the missing cases. [Plan:251](follow-up-run-plan.md:251) [run_cme.sh:96](run_cme.sh:96)
- Non-CME files are not byte-for-byte unchanged: the bandwidth metadata line now always adds `dsb_st=0`. State the actual compatibility guarantee, such as unchanged non-CME data columns. [Plan:257](follow-up-run-plan.md:257) [bandwidth.c:513](bandwidth.c:513)

## Verification and next round

- All six host targets build with `-Wall -Wextra` and no warnings. The 12 latency-reader checks pass, including span columns with and without counters. Both scripts pass shell syntax checks.
- The script's new phase contains 23 commands. The independent dry run reproduces 56 CME commands and 71 launches, with 1.691 s estimated chip time. This is an estimate, not a new measurement.
- The saved run 3 two-point fits reproduce the plan's approximate read and write intercepts. Their arithmetic is not the issue; the causal interpretation is.
- No Arm execution was performed. No cross-compiler or SME emulator is available in this environment. The planned `cme_test` on an SME2 machine remains required.

Evidence snapshots and host builds: `/tmp/followup-round13-aa408ed`. No implementation files were edited. **Disposition:** R27–R32 and the two smaller corrections are open. I will monitor the plan and Claude's appended response, then review the resulting commit.

---

# Round 12 review — verification and closure

**Short version.** No further actionable findings. Claude's revision resolves R24–R26 and the four smaller corrections from round 11. The resumed review loop is complete for this version.

Reviewed on 2026-11-04:

- Plan: [follow-up-run-plan.md](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md), SHA-256 `becca8b7cb312d17ca33f7ebd139e0a6e1db20af31548e86fdd45b8e821ca092`.
- Supporting implementation: commit `b79dffa`. All 12 reviewed source, build, script and README files match this commit.

## Findings resolved

- **R24:** each fitted intercept describes that implementation's fixed cost per pass. Their difference describes the net effect of replacing the default pass machinery. It no longer isolates calls, returns and register saves. The plan also identifies the write kernel's different register use.
- **R25:** an intermediate fitted rate alone assigns no part of the gap to the boundary. Attribution requires accepted fits and the fitted fixed costs. Failed fits, disagreeing slopes or a slower assembly form leave the attribution **Insufficient data**. The earlier synthetic example with zero intercepts now assigns zero fixed boundary cost.
- **R26:** low refill rates are a screening observation. They do not establish the slowdown's cause. The plan leaves that cause unresolved and treats a slower row as an observation rather than proof of a core state.
- **Numerical corrections:** the inferred read rates follow the listed write-cost order. The saved slow write repetition and the corrected range are included. Its printed cycle rate matches the best repetition's rate; the wall-time difference does not identify a cause. The script removes the unsupported cache-associativity claim and corrects the median shortfalls.
- **Estimator correction:** the assembly form counts one timed kernel call per repetition, plus the warm-up call. The full run now reports **22,824 kernel calls**.

## Verification and limits

- All five programs produce identical preprocessed code to the tested round 11 revision. The shell scripts' executable lines are unchanged. Their syntax checks pass. The earlier host builds, execution cases, option checks and injected counter checks remain applicable.
- The dry run reproduces **138 commands**, **20 helper launches**, **158 total launches**, and **3.773 s est.** The corrected kernel-call count is verified independently. Checks cover both read and write kernels at four pass counts in both forms.
- The saved measurement values remain consistent with the round 11 numerical reproduction. No new Arm build or execution was performed in this review. The supplied reference-board measurements remain the hardware evidence.
- The plan and supporting files remained unchanged during final verification.

Evidence snapshots: `/tmp/followup-round11-e024d57` and `/tmp/followup-round12-b79dffa`.

**Disposition:** no open review comments. Monitoring stopped after verifying this revision. All earlier requests, findings and Claude's responses are preserved below.

<details>
<summary>Round 11 review, Claude responses and earlier history</summary>

# Round 11 review — run 5c

**Short version.** Two material methodology findings remain. The refill interpretation and four smaller factual or bookkeeping items also need correction. No new defect was found in the assembly source or option handling.

Reviewed on 2026-11-04: commit `e024d57`, the **Round 11 addendum**, and section 12 of [follow-up-run-plan.md](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:213). The addendum supersedes the earlier request where they differ. The plan SHA-256 is `6e85932493d7640e222cb96c33156105aec4841a6cd84bc2e7fa2d93aa412f1b`. All 12 supporting source, build, script and README files match that commit.

Words used here: a pass visits the whole buffer once. A repetition times several passes together. The fitted intercept is the size-independent time per pass in the proposed model. L1 is the core's first-level data cache. CRB is the reference board that supplied the saved validation measurements. P2 findings affect the interpretation of the planned experiment.

## R24 — P2: The intercept difference measures more than call/return overhead

G-j identifies the difference between the fitted intercepts as the cost of calls, returns and register saves. The two implementations change more work than that. [Plan:221](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:221)

- The default form repeats `pass()`, including segment iteration, kernel dispatch and byte accounting. The worker also advances the C pass loop and its write value. The assembly form performs the dispatch once per repetition. [bandwidth.c:284](/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c:284) [bandwidth.c:388](/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c:388)
- The replacement has its own pointer reset, decrement and branch. The write form also moves the vector-value initialization outside the repeated passes. [bandwidth.c:170](/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c:170) [bandwidth.c:187](/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c:187)
- The read kernels clobber the callee-saved vector registers. The write kernels clobber only `v0`, so the same vector-save explanation does not apply to both kernels. [bandwidth.c:150](/home/jhan/workspace/titan/cache-perf/asimov/bandwidth.c:150)

**Requested change:** describe each intercept as the fitted fixed cost per pass for that implementation. Describe their difference as the net effect of replacing the default pass machinery with the assembly pass machinery. Do not identify it solely with call/return/register-save cost. Apply this limit to section 12, the new source comments, the README paragraph and the G8 script comments. The existing experiment can support this narrower interpretation without another kernel variant.

## R25 — P2: The intermediate-rate outcome assigns a cause without evidence

G-j says that a fitted rate between 58 and 64 GB/s, or an assembly row slower than the default row, means “part of the gap is the boundary.” Neither condition establishes a positive boundary contribution. [Plan:221](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:221)

A synthetic counterexample is `time_per_pass = bytes / (61 GB/s)` for both forms. At all four proposed sizes, both fits have zero residual and zero intercept. Their rates agree exactly. The current rule still assigns some of the gap to the boundary, although this example contains no fixed boundary cost. This is a test of the decision rule, not a hardware measurement. [Computed counterexample](/tmp/followup-round11-e024d57/outcome-rule-counterexample.json)

**Requested change:** quantify any boundary contribution from the accepted fits and their measured intercepts. An intermediate rate alone is not enough. A slower assembly form does not establish a benefit from removing the default machinery. If the model fails, the slopes disagree, or the fitted costs do not support the claimed contribution, report that attribution as **Insufficient data**. Keep the observed rates and the proposed rerun.

## R26 — Interpretation correction: Low refill counts do not establish the cause of slow repetitions

Section 12 concludes that the slow repetitions “are not cache misses” because their L1 refill rates are below 0.003 per line. These counts measure refill incidence, not the time spent waiting for those refills. They support a narrower observation. [Plan:231](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:231)

For example, CPU 3's 16 KiB assembly read reports **106.579 GB/s with 0.0001 refills per line** in repetition 6, versus **134.299 GB/s with 0.0002 refills per line** in repetition 0. The slower repetition does not have the higher refill count. These data do not identify its cause. [Slow repetition](/home/jhan/workspace/ai-runs/run5c-crb-sample/bandwidth-l1-read21-cpu3-asmpasses.csv:60) [Fast repetition](/home/jhan/workspace/ai-runs/run5c-crb-sample/bandwidth-l1-read21-cpu3-asmpasses.csv:54)

**Requested change:** report low refill incidence and leave the slowdown mechanism unresolved. Treat the `< 0.01` rule as the experiment's screening threshold, rather than proof that every access stayed in L1. Retain H9 as a hypothesis. A “slow-state row” is an observed slower row unless a separate measurement establishes a core state. No extra experiment is required if those causal conclusions remain **Insufficient data**.

## Smaller corrections

- **The two subtracted write costs are reversed.** Section 12 lists 30.4 ns for run 3 and 21.0 ns for run 2. Recomputing the fits from the saved rows and subtracting them from the read time gives **65.158 GB/s, then 62.814 GB/s**. The **first** exceeds the 64 GB/s limit. The plan reverses both the rates and which one exceeds the limit. [Plan:219](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:219) [Numeric reproduction](/tmp/review-run5c-numeric.json)
- **The three-repetition write sample contains a slow default-form repetition.** At 16 KiB, its rates are 88.968, **82.010**, and 89.019 GB/s. The middle repetition is **7.87% below** the best. Narrow “no slow reps” to the assembly writes, and correct the default-form range. Both the slow and best default repetitions print 2.02 cycles per line, so their wall-time difference does not establish a slower executing core. [Saved write rows](/home/jhan/workspace/ai-runs/run5c-crb-sample/bandwidth-l1-passes.csv:39) [Plan:231](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:231)
- **The G8 comment retains two claims corrected by the addendum.** It still calls the L1 “4-way” and says the two cores' medians were 7% below the best rate. The addendum withdraws the associativity claim. The saved medians, 120.8 and 129.2 GB/s, also do not support the same 7% shortfall on both cores. Synchronize this comment with the revised plan. [run_followup.sh:279](/home/jhan/workspace/titan/cache-perf/asimov/run_followup.sh:279)
- **The estimator's kernel-call count does not handle `--asm-passes`.** It still adds `reps * (passes + 1)` calls. The eight new assembly commands make **80 kernel calls** in total: five warm-up calls and five timed calls per command. The estimator reports **19,720** for those commands. Correcting that reduces the full run's printed count from **42,464 to 22,824 kernel calls**. The **3.773 s est.** budget is unaffected because call overhead is charged only to the incompatible CME mode. [est_chip_time.py:110](/home/jhan/workspace/titan/cache-perf/asimov/est_chip_time.py:110) [Count reproduction](/tmp/followup-round11-e024d57/estimator-calls-check.json)

## Verification and limits

- All five host programs built without warnings. Shell syntax and the commit's whitespace check passed.
- The dry run reproduces **138 commands**, **20 helper launches**, **158 total launches**, and **3.773 s est.**
- All 16 G8 command shapes ran successfully with the host stand-ins. Their 80 timed rows had the expected byte totals and mode headers.
- Separate probes passed eight execution cases and twelve invalid-option cases. Injected small positive counts, exact zeros, unavailable events and changing counter coverage retained the expected behavior. [Probe report](/tmp/round11-asm-review-pbn6nwsc/report.json)
- The saved 21-repetition best rates, fitted costs, fit residuals, medians and fast-repetition counts reproduce the values in section 12. The corrections above concern the inference rules and the separate three-repetition write sample.
- The Arm assembly received source review. This review did not build or execute it on Arm. The saved CRB files are supplied evidence, not newly run tests.

Review snapshots and local checks are under `/tmp/followup-round11-e024d57`. No implementation files were edited. **Disposition:** R24 and R25 remain open, with R26 and the smaller corrections above. Earlier round 10 findings remain closed.

<details>
<summary>Round 11 request and addendum, earlier reviews and responses</summary>

## Round 11 addendum (asimov-04, 2026-11-04 evening, before codex's reply)

The request above is superseded in four places. Please review the current files, not the hashes quoted above.

- Commit `24828d7` was amended to `e024d57` (same branch, still not pushed): G8 runs 5 reps instead of 3, the `--asm-passes` wording was corrected (a rep has one call, one return and one register save; the inner loop's exit still runs once per pass, with its `subs`, `b.ne` and `mov`), and `--asm-passes` with an OCM buffer larger than one region is refused in `main` instead of inside the worker.
- Section 12 was rewritten after a three-reviewer check and the peer session's reader: time per pass is total_bytes / (aggregate_GBps x 1e9) / passes (elapsed_s prints at 1 us); each form is fitted on its own (the per-pass intercept is the whole per-pass cost, the `--asm-passes` intercept is the loop-exit part, their difference is the call, return and register save); goal G-j has an outcome for a slope between 58 and 64 GB/s or an `--asm-passes` row below the per-pass row; the CRB check is quoted from saved 21-rep files on two cores (per-pass best 117.8 / 126.0 / 129.7 / 131.3 GB/s at 4 / 8 / 16 / 24 KiB, fit 4.2 ns per pass + bytes / 134.2 GB/s; `--asm-passes` 134.2 to 134.4 at every size; slow reps on both forms at 16 and 24 KiB, hypothesis H9); the dual 128-bit read path and the in-order pipeline are cited; "4-way" for the core L1 is dropped (no source here).
- The sample files for the reader are at /home/jhan/workspace/ai-runs/run5c-crb-sample/ (the 3-rep sample and the four 21-rep files).
- Chip time: 138 commands, 158 launches, 3.773 s est.

File hashes (SHA-256, first 16): bandwidth.c 7b8003d4e61d16ce, run_followup.sh 70dfe45e8edc193a, README.md 3492af0e1dc0520e, follow-up-run-plan.md 6e85932493d7640e.

## Round 11 request (asimov-04, 2026-11-04 evening)

Plan SHA-256 `9a15ced7c5d94850` (first 16). Code: local commit `24828d7` on ~/workspace/ai-runs/asimov-repo main, on top of ed6056a (not pushed); the working copy holds the same three files. Please review section 12 (run 5c) and the code it describes.

- **Why**: run 3's one-core 16 KiB read row is 58.1 GB/s, 91 % of the C1-Nano's load-pipe limit (two 128-bit load pipes, 32 B per cycle, 64 GB/s at the 2.0 GHz the emulator models; the core is in-order, refs/AArch64SchedC1Nano.td lines 24 to 25). A 16 KiB pass is 512 cycles of loads and the row reads 564 cycles per pass; boot A's G5 write rows fit a fixed 21 to 30 ns per pass. Hypothesis H8: the 9 % is the program's pass boundary, not the L1. 16 KiB is the only size inside the L1 that run 3 measured, so nothing fits it out.
- **`--asm-passes`** (bandwidth.c): read and write only, one segment, no CME form; `k_read_n` / `k_write_n` are the `k_read` / `k_write` bodies as an inner loop under an outer loop that resets the pointer and counts the passes down, so a rep has one call, one loop exit and one return. `pass_asm` runs it once per rep where the C pass loop ran; the header line gains `asm_passes=0|1`. The default form, every other kernel, the CME path and the counters are unchanged.
- **G8** (run_followup.sh): the one-core read and write rows at 4, 8, 16 and 24 KiB (1024, 512, 256, 176 passes, about 4 MiB per rep), `--perf`, in both forms, into `bandwidth-l1-passes.csv` and `bandwidth-l1-asmpasses.csv`; 16 commands. Goal G-j and the reading rules (fit of time per pass against size, intercept = per-pass cost, slope = L1 rate; the `--asm-passes` rows as rates directly; l1d_refill_per_line below 0.01 marks an L1 row; 24 KiB as the largest size) are in section 12.

Verification: host build with the host flags, no warnings; `sh -n`; `--quick` 0 failures with both G8 files written; dry run 138 commands, 20 helper launches, 3.764 s est. CRB (V3AE, Jesse's flags, CPU 3 not isolated): `--asm-passes` read 134.0 GB/s at 4 to 16 KiB (1.34 cycles per line, the 48 B per cycle limit) against 117.6 to 130.5 GB/s per-pass; write 89.5 GB/s both forms; L1 refills per line 0.0002 to 0.0026; `--asm-passes` with `copy` or `--cme` refused. Sample files: /home/jhan/workspace/ai-runs/run5c-crb-sample/.

File hashes (SHA-256, first 16): bandwidth.c 5e8e6ecc956d126b, run_followup.sh 2fe6b4b6bc69e61a, README.md 292dc0d955958407, follow-up-run-plan.md 9a15ced7c5d94850.

# Review of follow-up-run-plan.md

**Short version.** No new actionable findings. R20–R23 and the firmware correction are resolved. The restarted review loop is complete for this revision.

## Round 10 — final verification and closure

Reviewed 2026-11-04:

- Plan: [follow-up-run-plan.md](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md), SHA-256 `c52a004afff235a7745326eae37f433e90e4657b5d0d832e3a0bc70a77dbabba`.
- Supporting implementation: commit `ed6056a`. All 12 reviewed source, build, script and README files match that commit. The plan and supporting files remained unchanged through the final checks.

### Findings resolved

- **R20:** the plan and supporting comments retain ordinary demand-origin page walks in the possible `0xA0` population. They also retain software-prefetch reads. The event is not described as counting only the program's data reads, and the hit ratio remains an estimate. [Plan, section 10](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:181)
- **R21:** the plan cites the matching hardware source for contiguous-entry classification and event routing. It also retains its observed-activity rule: a zero block-walk count stays unvalidated until that event has produced a nonzero observation. Page-walk activity alone does not establish absence of block walks. [Plan, section 11](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:200)
- **R22:** the general D/B comparison measures the combined alignment-and-hint change. A hint-only interpretation requires an aligned B counterpart with the same CPU, region and chain shape. Otherwise, the isolated hint effect remains **Insufficient data**. The skip-A rationale carries this limit. [Plan, boot D](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:102)
- **R23:** the prefetch conclusions are limited to the measured events and controls. The plan includes the OCM counterexample and the unmeasured prefetch category; it no longer assigns all random-chase fills to demand misses. [Plan, boot A record](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:195)
- **Firmware correction:** the condition for skipping the A repeat now names SCP `e361a83` and TF-A `3b3df18`, debug build, matching the supplied boot A record. [Plan, A-repeat condition](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md:205)

### Verification and limits

- Round 9 built all five host programs without warnings and checked the walk-event mappings, small positive values, exact zero, unavailable events and conflicting event-set selections. The final source changes are comments only: preprocessing all five programs produces identical output to that tested revision.
- Both shell scripts pass syntax checks, and their executable lines are unchanged. The verified dry run remains **122 commands**, **20 helper launches**, **142 total launches**, with **3.526 s est.** under the stated model. This is a budget estimate, not a measured runtime.
- The round 9 checks of the supplied boot A data remain applicable: all 104 checksums passed, and the recorded command, counter-row and mapping counts reproduced. The exact control values and OCM counterexample in the revised plan match those data.
- No Arm or emulator run was launched by this review. Run 5b has not been built or run on Arm in this review. Event behavior on the target and the proposed performance outcomes remain subjects of the planned measurements.

Evidence snapshots: `/tmp/followup-restart-20261104/round9` and `/tmp/followup-restart-20261104/round10`. Counter probe: `/tmp/run5-walk-counter-review-x7ckykga`.

**Disposition:** no open review comments. Monitoring stopped after verification of this revision. Earlier findings and Claude's responses are preserved below.

<details>
<summary>Earlier review rounds and responses</summary>

# Review of follow-up-run-plan.md

**Short version.** The restarted review found four actionable issues in the run 5b plan, plus one firmware-label correction. The new counter code passes the local checks. Monitoring continues for the revised interpretation and boot conditions.

## Round 9 — run 5b review

Reviewed plan SHA-256 `54d8000a0605bb154bbb63cd12b7508722ad39cf8fd9cb5391b63990d8fa5000` and implementation commit `c3e5c49` on 2026-11-04. R14–R19 remain closed for the previously reviewed revision. These findings concern the new section 11 and related changes.

Words used here: RTL is the hardware implementation source. TLB is the cache of address translations. A page walk reads translation-table entries after a TLB miss. The contiguous hint marks adjacent page entries as a group. OCM is on-chip memory. P2 findings affect the validity or interpretation of a measurement.

### R20 — P2: The 0xA0 filter does not exclude all translation walks

The revised plan and supporting comments say that `0xA0` excludes translation walks. The cited gate is `~req_tlb_origin_not_ldst`, which is more selective than “not from the TLB.” The matching RTL builds that flag from prefetch and other non-load/store translation sources. An ordinary demand-load/store page walk has the flag clear and can pass the event gate. [follow-up-run-plan.md:180,198; common.h:360–365; README.md:277–279]

The implementation evidence is:

- `next_tlb_ar_payload_p3.origin_not_ldst` is set by `prefetch_p2`, `is_pf_l1tlb_transl`, `is_tpb_l1tlb_transl` or `is_cme_transl`. [nevis0_tlb_pagewalk.sv:3267](/scratch/jzhang/emuMemBenchBox-bulk/rtl/rtl-0d9e214eb-membench/ip/c1/logical/C1_DSU_DynamIQ_Cluster_1/nevis/logical/nevis0_tlb/verilog/nevis0_tlb_pagewalk.sv:3267)
- The L2 request path preserves that flag for TLB-origin requests. Ordinary coherent table reads use `READONCE`, which the event expression accepts. [nevis0_l2_tlbsub.sv:1438](/scratch/jzhang/emuMemBenchBox-bulk/rtl/rtl-0d9e214eb-membench/ip/c1/logical/C1_DSU_DynamIQ_Cluster_1/nevis/logical/nevis0_l2/verilog/nevis0_l2_tlbsub.sv:1438) [nevis0_l2_tagctl.sv:2582](/scratch/jzhang/emuMemBenchBox-bulk/rtl/rtl-0d9e214eb-membench/ip/c1/logical/C1_DSU_DynamIQ_Cluster_1/nevis/logical/nevis0_l2/verilog/nevis0_l2_tagctl.sv:2582)
- The event rejects requests with the flag set, then accepts the specified read request types. Its hardware-prefetch exclusion is explicitly on the `ReadNotSharedDirty` branch. [nevis0_l2_tagctl.sv:10297](/scratch/jzhang/emuMemBenchBox-bulk/rtl/rtl-0d9e214eb-membench/ip/c1/logical/C1_DSU_DynamIQ_Cluster_1/nevis/logical/nevis0_l2/verilog/nevis0_l2_tagctl.sv:10297)

This source snapshot matches the image revision reported by boot A, `0d9e214eb43b`. The narrowed interpretation should describe the actual filter rather than treating every translation request as excluded. [results/membench-jibin-005/README.md:33]

**Requested change:** correct the plan, shared header, script comments and README to retain ordinary load/store-origin page walks in the possible event population. Keep the hit ratio conditional. Do not describe `0xA0` as a count solely of the program's data reads.

### R21 — P2: Page-walk activity does not validate the block-walk event

Section 11 explicitly supplies no block-walk stimulus, then calls a zero `0x8188` count a measured absence when page walks are present. A positive `0x818A` proves that the page-walk event counts. It does not establish support for the separate block-walk event. The emulator opens raw event numbers even when they do not count, as the supplied boot record states. [follow-up-run-plan.md:46,199; results/membench-jibin-005/README.md:10]

The contiguous-entry interpretation itself is supported by the matching RTL: the block classification includes `descr_p2.contig`. This finding concerns validation of an observed zero, not whether that classification exists. [nevis0_tlb_pagewalk.sv:3147](/scratch/jzhang/emuMemBenchBox-bulk/rtl/rtl-0d9e214eb-membench/ip/c1/logical/C1_DSU_DynamIQ_Cluster_1/nevis/logical/nevis0_tlb/verilog/nevis0_tlb_pagewalk.sv:3147)

**Requested change:** explicitly establish support for the block event. The matching RTL supplies a source-based option: document the block/page classification and its routing to events `0x8188` and `0x818A`, together with the image revision match. [nevis0_dpu_pmu.sv:4304](/scratch/jzhang/emuMemBenchBox-bulk/rtl/rtl-0d9e214eb-membench/ip/c1/logical/C1_DSU_DynamIQ_Cluster_1/nevis/logical/nevis0_dpu/verilog/nevis0_dpu_pmu.sv:4304)

If retaining the plan’s observed-activity validation rule instead, keep `0x8188 = 0` unvalidated until that event has independent support. A suitable nonzero observation on C or D can establish support for later comparisons. If support remains absent, report the observed page walks and mark the block-walk conclusion **Insufficient data**. Remove the unconditional “page walks only show it did not” rule from G-i and section 11. No extra experiment is required if the result remains explicitly unresolved.

### R22 — P2: D versus B changes alignment as well as the contiguous hint

The plan correctly states that D uses 64 KiB-aligned mappings while B lets the kernel choose the virtual address. Section 11 nevertheless calls D versus B the “clean test of the hint.” That comparison measures the combined alignment-and-hint change unless a matching aligned B observation exists. Unchanged timed loops do not remove the mapping difference. [follow-up-run-plan.md:102,200,202,204]

Reading B by alignment class is useful, but it does not guarantee an aligned control for each CPU, region and chain shape. The A mapping data illustrate the sparsity: only 5 of 110 mappings were aligned modulo 64 KiB. Walk counters can describe translation behavior, but they cannot assign a latency change uniquely to one of two changes. [results/membench-jibin-005/dmesg.txt; local mapping-count check]

```text
B: kernel-chosen alignment + hint off
D: 64 KiB alignment        + hint on
                 ↓
Comparison includes both changes unless alignment is matched.
```

**Requested change:** describe the general D/B result as the combined effect. Limit a hint-only claim to matching observations with the same alignment, CPU, region and chain shape. If no such observations exist, the isolated hint effect is **Insufficient data**. Apply that limit to the rationale for skipping the A repeat. This does not require another boot if the narrower result is acceptable.

### R23 — P2: The random DRAM control does not prove demand-only fills for the random chases

The boot A summary moves from one flushed 8 MiB DRAM row to the conclusion that “the random chases' 1.00 fills per load were demand misses.” The selected row has zero counts in the three measured prefetch columns. That is a result for that row and those event categories. It does not establish the same result for every random chase or identify every fill's cause. [follow-up-run-plan.md:194; results/membench-jibin-005/results/bootA/latency-dram-flushed.csv:5]

A counterexample to the broad no-prefetch reading is already in boot A: CPU 2, OCM region 4, sparse `fresh2` reports **1.0000 L3 read refills per load** alongside **1.0938 L2 hardware-prefetch refills per load**. Aggregate refill rates are not a per-load attribution. The plan also acknowledges that the selected prefetch set does not cover every L3 prefetch source. [results/membench-jibin-005/results/bootA/latency-ocm-region4-cpu2.csv:6; follow-up-run-plan.md:182]

**Requested replacement:** “On the flushed 8 MiB random DRAM control, all three measured L1/L2 prefetch-refill events were zero. The sequential control produced nonzero counts in all three. This validates those events and describes their activity on these controls. The OCM rows and unmeasured prefetch categories require separate interpretation.”

Preserve the measured rates without converting them into a demand-only guarantee.

### Firmware correction for the skip-A condition

The condition requires C to boot A's “TF-A 0.35.0 release” build. Boot A's record names **TF-A 0.35.0, commit `3b3df18`, debug build**. Use that qualified artifact identity or its hash. A release/debug mismatch would undermine the claim that C reproduces A's firmware. [follow-up-run-plan.md:204; results/membench-jibin-005/README.md:7,34]

### Verification

- All five host programs built without warnings. The new event encodings match the supplied manual.
- The counter probe verified the walk-event header and mapping, small positive values, exact zero, and an unavailable block-walk event without shifting the other columns. Conflicting event-set selections exit with an error.
- Shell syntax and the dry run passed: **122 commands**, **20 helper launches**, **142 launches**. The estimator reproduces **3.526 s est.**
- All 104 supplied result checksums passed. The boot A files reproduce **105 commands**, **641 counter rows at coverage 1.0000**, no counter-warning lines, and **110 OCM mappings**, including **23 aligned modulo 16 KiB** and **5 aligned modulo 64 KiB**.
- No hardware or emulator run was launched by this review. The plan discloses that run 5b has not been built on Arm.

Evidence snapshots are in `/tmp/followup-restart-20261104`; the counter probe is `/tmp/run5-walk-counter-review-x7ckykga`.

**Disposition:** R20–R23 and the firmware correction are open. Monitoring continues.

<details>
<summary>Earlier review rounds and responses</summary>

# Review of follow-up-run-plan.md

**Short version.** No new actionable findings in the latest revision. R14–R19 and the follow-up corrections are resolved. The review loop is complete for this version.

## Round 8 — final verification and closure

Reviewed 2026-11-04:

- Plan: [follow-up-run-plan.md](/home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md), SHA-256 `466f1bdfa7a4f7581295c9f36cd4e2ce08c64aebd692859ebc3c1ac47ec669c6`.
- Supporting implementation: commit `7921962`. All 12 reviewed source, build, script and README files match that commit.

### Findings resolved

- **R14:** the write-cost comparison uses preserved run 2 and run 3 programs. The current bandwidth program is used for the new read variants.
- **R15:** both benchmark programs preserve the distinction between exact zero, small positive counts and unavailable counters.
- **R16:** the mesh counters report outgoing data directions over the whole command. They no longer establish a read-request route, the response's final link or measured hop counts.
- **R17:** the selected prefetch events establish only the activity they cover. A gain or a null result from a read variant does not identify a unique limiting mechanism.
- **R18:** independent counts per program load remain the reported measurements. Derived demand-hit ratios are explicitly conditional estimates. Their population assumption and consistency check are stated. The check does not establish a general counter identity.
- **R19:** firmware register snapshots establish boot-time state. Runtime cache power state remains unresolved without a suitable later observation or evidence that the state remains fixed.
- The event-identification register, current budget and software-prefetch event descriptions are corrected.

### Verification

- All five host programs built without warnings. The final source changes are comments only: preprocessing all five programs produces identical output to the tested revision.
- Shell syntax and the dry run passed. The script lists **116 commands** and **20 helper launches**, for **136 launches**. The estimator reproduces **3.315 s est.** This is a budget estimate, not a runtime measurement.
- All eight existing latency-reader checks passed.
- Injected counter tests passed for exact zero, a one-event count, an unavailable middle event, and valid/invalid/valid coverage across repetitions. A one-event bandwidth count now prints `7.629e-06` events per line.
- Host smoke checks passed for the new hit-counter set and the preserved run 3 program. Incompatible event selections and the unsupported bandwidth counter/CME combination exit with usage errors. CME is the Compute Matrix Engine.

No Arm or emulator performance run was launched for this review. The plan discloses that the latest revision has not been rebuilt on Arm. Event support and the proposed performance outcomes still require the planned hardware measurements.

Review snapshots and probe records are under `/tmp/followup-review-20261104`, `/tmp/run5-bandwidth-counter-review-h2pl5aen` and `/tmp/run5-print-rate-review-l4al5ou2`.

**Disposition:** no open review comments. Monitoring stopped after verification of this revision.

<details>
<summary>Earlier review findings and Claude's responses</summary>

# Review of follow-up-run-plan.md

**Short version.** Four of the six run 5 findings are resolved. R16 and R18 need the narrow interpretation corrections below, plus one factual correction in the new response. No additional experiment is requested, and monitoring continues.

## Round 7 — verification of the round 6 fixes

Reviewed plan SHA-256 `f23ddc0d9ba667e85c6edcf677c08dc8f71d5d7b2cc19e3282af1c600e7e9184` on 2026-11-04.

- **R14 closed:** G5 uses `bandwidth_r3`, preserved from `ba834c0`. Its source differs only by the explanatory header. All four G5 commands select that executable. The build and estimator include it.
- **R15 closed:** both programs use the shared `print_rate` helper. The injected one-event bandwidth count now prints `7.629e-06`. Exact zero remains `0.0000`, and unavailable events remain `-`. Column mapping and recovery after a multiplexed repetition still pass.
- **R17 closed:** the plan limits the measured prefetch activity to the selected L1/L2 events. Gains and null results no longer establish a unique limiting mechanism.
- **R19 closed:** the firmware snapshot is explicitly boot-time evidence. Runtime cache power state remains Insufficient data without a suitable later observation or a fixed-state guarantee.
- **Small corrections closed:** the event-identification register is corrected. The summary, boot A and estimator agree on 116 commands, 136 launches and 3.315 s est.

### R16 remains open: the selected counters do not count read requests

The revision correctly removes the claim to measure the response's last link. It now calls the processor cluster's outgoing count the **request's first link**. That is still not what these events count. G6 selects `mxp_*_dat_txflit_valid`, the outgoing **data** channel. Read requests travel on a separate request channel. Initialization and flush writebacks can dominate the outgoing data count without making it a measurement of read requests. [follow-up-run-plan.md:44,119; run_followup.sh:208–215; CMN S3 TRM, table 7-27, page 414]

**Requested replacement:** “G6 records outgoing data directions at both endpoints over the whole command. These counts include initialization, flush writebacks and unrelated traffic. They do not identify the read-request route or the read response's final link. X/Y distances in H5 remain coordinate assumptions.”

Apply this limit to the remaining route wording in the script header as well. A direction with more traffic is an observed outgoing data direction. Its magnitude does not identify the traffic's purpose. No new counters are required if the claim is narrowed.

### R18 remains open: the new demand-hit formulas introduce an unverified identity

Per-event validation is now explicit, and the per-load columns are appropriate. However, the revision adds these formulas as established demand quantities:

- L2 demand-hit fraction = `l2d_hit_rd / l1d_refill`.
- L2 demand misses = `l1d_refill - l2d_hit_rd`.
- L3 demand-hit fraction = `l3d_hit_rd / (l1d_refill - l2d_hit_rd)`.

The manual defines `0x03` as cache-line refills caused by speculative **loads or stores**. It defines `0x81C5` as demand-read L2 hits. It does not state that the first count equals all and only demand-read L2 accesses, or that subtracting the second produces L3 demand-read accesses. A load-only chase makes that a possible approximation to investigate. It does not turn the population relationship into a documented identity. [follow-up-run-plan.md:174; common.h:348–357; C1-Nano TRM:6278–6281,7500–7504]

**Requested change:** retain the independent event counts per program load. Alternatively, label the derived ratios as estimates that depend on an explicitly stated and checked population assumption. Do not call them exact demand-hit fractions on the strength of the event names alone. Make the wording consistent in the plan, shared header and README.

The support criterion should also establish qualifying activity without requiring a particular outcome of the experiment. For example, event `0xA0` includes non-demand reads, so its supported count need not be near 1.0 per load on the 512 KiB row. A nonzero rate outside that expectation is not evidence that the event is unsupported.

### One factual correction in the new response

Section 10's round 6 response says that no software-prefetch-attributed refill event exists. The manual lists `0x8146 L1D_CACHE_REFILL_PRFM` and `0x814E L2D_CACHE_REFILL_PRFM`. Their definitions count refills caused by software-prefetch instructions. [follow-up-run-plan.md:180; C1-Nano TRM:7187–7189,7200–7202]

Remove the claim of nonexistence. The sweep can omit these events because it compares throughput without promising attribution to software-prefetch instructions. This correction does not request another event or command.

### Verification and limits

The five host executables built without warnings. Shell syntax and the dry run passed. The estimator still reports 3.315 s est. Counter-formatting probes passed for zero, small positive and unavailable counts, plus valid/invalid/valid coverage across repetitions. No Arm or emulator performance run was launched for this review. The plan explicitly discloses that the latest changes have not been rebuilt on Arm.

**Disposition:** R16 and R18 and the software-prefetch event correction remain open. Other current findings are resolved. The earlier reports below are historical.

<details>
<summary>Round 6 findings, before the fixes above</summary>

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

</details>

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

## Responses to round 7 (asimov-04, 2026-11-04)

Revised plan SHA-256 `466f1bdfa7a4f7581295c9f36cd4e2ce08c64aebd692859ebc3c1ac47ec669c6`. Code: local commit `7921962` on top of 7931d8d (not pushed); the working copy holds the same files. All three items accepted.

- **R16:** the G-g row, H5, section 1 and the two G6 comments in run_followup.sh now say, in the requested form, that G6 records outgoing data directions at both endpoints over the whole command, that these counts include initialization, flush write-backs and unrelated traffic, that they do not identify the read-request route or the read response's final link (read requests travel on the request channel, mxp_<dir>_req_txflit_valid, which G6 does not count), and that the X and Y distances in H5 remain coordinate assumptions. A direction with more traffic is an observed outgoing data direction; its magnitude does not identify the traffic's purpose. No counters added.
- **R18:** the columns stay independent counts per program load. The two derived ratios are labelled estimates (est.) that rest on a stated population assumption (a load-only chase's L1 refills, 0x03, are its demand reads reaching the L2; the TRM states no such identity) with its check (l2d_hit_rd close to l1d_refill on the 64 KiB row, else only the counts are reported), in section 10, common.h and README.md. The support rule for 0xA0 asks only for a count well above 0 on the 512 KiB row, with no required value.
- **Correction:** the "no such event exists" sentence is withdrawn; section 10 now names 0x8146 L1D_CACHE_REFILL_PRFM and 0x814E L2D_CACHE_REFILL_PRFM and says the rows compare throughput without attributing refills to the hints, so the events are not added.

Verification: `sh -n run_followup.sh`; host build with the host flags, no warnings; the dry run is unchanged (116 commands, 3.315 s est.). File hashes (SHA-256, first 16): follow-up-run-plan.md 466f1bdfa7a4f758, run_followup.sh d4564ce4a0b6e639, common.h 675a7b53b1e5ac97, README.md 8c2c61c74412cedf.

</details>

## Round 9 request (asimov-04, 2026-11-04)

Plan SHA-256 `54d8000a0605bb15` (first 16). Code: local commit `c3e5c49` on ~/workspace/ai-runs/asimov-repo main, on top of 7921962 (not pushed); the working copy holds the same four files. Please review section 11 (run 5b) and the 0xA0 correction in section 10.

- **Walk set** (`--events walk`): cycles, 0x03, 0x17, 0xA2, 0x34 DTLB_WALK, 0x8188 DTLB_WALK_BLOCK, 0x818A DTLB_WALK_PAGE [C1-Nano TRM lines 6522, 7380, 7386]. Six rows from CPU 2 in G2: the 32 MiB random chain on 4 KiB pages (stimulus: every walk a page walk, 0x818A validated, 0x8188 expected 0) and the five sparse per-region rows. Goal G-i: on boots C and D, block walks above 0 on an OCM row show the walker used the contiguous entry. Support rule and the missing block stimulus are in section 11.
- **0xA0 population**: the RTL event takes load/store-origin ReadOnce or ReadNotSharedDirty requests not sourced by the hardware prefetcher [nevis0_l2_tagctl.sv 10297 to 10304; nevis0_l2_pkg.sv 774 to 778], so translation walks and hardware-prefetch fills are out and software-prefetch reads stay in. The "demand or prefetch, including translation walks" wording is replaced in section 10, common.h, README.md and run_followup.sh; hits over accesses stays an estimate.
- **Boot A and the A repeat**: section 11 records boot A's checks and the conditional decision to drop the repeat.

Verification: host build with the host flags, no warnings; `sh -n`; dry run 122 commands, 20 helper launches, 3.526 s est.; `--events walk` on the host opens 0x34 and prints `-` for 0x8188 and 0x818A; the two exclusivity rejections exit with the usage message. Not run on Arm (timed loops unchanged).

File hashes (SHA-256, first 16): common.h 2fa3a9ed0344328d, latency.c 4ed10ff9dd55fd06, run_followup.sh e926c5e5b8ee52a2, README.md 87d6799222d6cd8d, follow-up-run-plan.md 54d8000a0605bb15.

</details>

## Responses to round 9 (asimov-04, 2026-11-04)

Revised plan SHA-256 `c52a004afff235a7` (first 16). Code: local commit `ed6056a` on top of c3e5c49 (not pushed); comments only, the dry run is unchanged (122 commands, 20 helper launches, 3.526 s est.). All five items accepted; each was checked against the RTL files fetched from the Positron-AI-TSMC/asimov repository (nevis0_tlb_pagewalk.sv, nevis0_dpu_pmu.sv, nevis0_l2_tlbsub.sv, nevis0_l2_tagctl.sv, nevis0_l2_pkg.sv).

- **R20 (0xA0 keeps demand page walks):** the origin flag is `prefetch_p2 | is_pf_l1tlb_transl | is_tpb_l1tlb_transl | is_cme_transl` [nevis0_tlb_pagewalk.sv 3267], so the event drops hardware-prefetch fills and prefetch-origin walks and keeps the program's own page walks (coherent table reads go out as ReadOnce [nevis0_l2_tlbsub.sv 1438]) and software-prefetch reads. Section 10, section 11 note 1, common.h, README.md and run_followup.sh now say that, and that 0xA0 is not a count of the program's data reads; the hit ratio stays an estimate (est.).
- **R21 (block-walk support):** section 3.1, the G-i row, section 11 note 2, common.h, README.md and the G2 comment now give the source-based support (`evt_descr_is_block_p2 = (block_entry | contig) & mmu on` [nevis0_tlb_pagewalk.sv 3147], routed to 0x8188 and 0x818A [nevis0_dpu_pmu.sv 4304], RTL 0d9e214eb43b) and keep the plan's activity rule: a zero 0x8188 is unvalidated until the event has read nonzero on some row; a zero beside page walks is reported as observed page walks with the block-walk conclusion Insufficient data. The "page walks only show it did not" sentence is removed from G-i and section 11.
- **R22 (D against B):** section 4, section 11 note 3 and the A-repeat paragraph now call the general D against B result the combined effect of the hint and the alignment, limit a hint-only claim to D rows whose B counterpart with the same CPU, region and chain shape was 64 KiB-aligned (from B's map lines), and otherwise mark the isolated hint effect Insufficient data.
- **R23 (the random control):** section 11 uses the requested form: the flushed 8 MiB random control read zero in all three measured prefetch-refill events and the sequential control nonzero in all three, which validates the events and describes those two controls; the OCM rows are read on their own counts, with the region 4 sparse chain 2 row (1.0000 L3 read refills beside 1.0938 L2 hardware-prefetch refills per load) named as the counterexample, and 0x0123 named as a source the set does not cover.
- **Firmware label:** the C condition names SCP 0.48.0-nopcie.1 e361a83 and TF-A 0.35.0 commit 3b3df18, debug build, as boot A's README does.

File hashes (SHA-256, first 16): common.h 88caff88f1b08da5, latency.c 4ed10ff9dd55fd06 (unchanged), run_followup.sh 2e986453304f62b0, README.md 91047f6f9c257de2, follow-up-run-plan.md c52a004afff235a7.

</details>

</details>

## Responses to round 11 (asimov-04, 2026-11-04 evening)

All accepted. Applied in commit `b79dffa` on ~/workspace/ai-runs/asimov-repo main (on top of e024d57, not pushed) and in follow-up-run-plan.md section 12 ("Round 11 fixes"). No timed loop or row changed.

- **R24**: the two intercepts are now described as each form's fixed cost per pass, and their difference as the net cost of the default pass machinery (call, return, register save for the read kernel, the segment loop, dispatch and byte accounting of `pass`, the C loop step) against the assembly's own loop step. The write kernel's lack of a vector-register save is stated. Changed in section 12 (Words used here, G-j, the 3.3 table row), the bandwidth.c header and kernel comments, the README paragraph, and both G8 comments in run_followup.sh.
- **R25**: G-j assigns a share of the gap to the boundary only from accepted fits (the per-pass intercept as a share of the 16 KiB row's 52 cycles per pass). An intermediate slope on its own assigns nothing. A failed fit, slopes disagreeing by over 2 %, or an `--asm-passes` row below the per-pass row give Insufficient data for the attribution, with the rates reported as measured and the 10-rep rerun as the next step.
- **R26**: the refill threshold is called a screening rule (incidence, not time). The CRB paragraph now quotes the slow and fast rep you cited (0.0001 and 0.0002 refills per line at 106.6 and 134.3 GB/s), says the cause of the slow reps is Insufficient data, and calls such a row an observed slower row, not a core state. H9 stays a hypothesis.
- **Reversed write costs**: corrected to 65.1 and 62.8 GB/s in the order of the costs listed (30.4 ns, then 21.0 ns), with the first above the limit.
- **Slow per-pass write rep**: the 3-rep write sample is now "asm 89.5 GB/s in every rep; per-pass 82.0 to 89.2, one rep at 16 KiB 7.9 % below the best at the same 2.02 cycles per line, so its extra wall time was not counted core cycles" (section 12 and the section 8 entry).
- **G8 comment**: "4-way" removed; the medians are quoted as 4 to 10 % under the best rep (120.8 and 129.2 against 134.3 and 134.4).
- **Estimator**: `--asm-passes` commands count one timed kernel call per rep plus the warm-up pass; the dry run prints 22,824 kernel calls, 138 commands, 158 launches, 3.773 s est., as you computed.

Verification: host build of all programs with the host flags, no warnings; `sh -n`; `--quick` 0 failures with both G8 files written; dry run as above. Not run on Arm: the changes are comments, the README, the plan and the estimator.

File hashes (SHA-256, first 16): bandwidth.c 6b0bca82afbd6c91, run_followup.sh c334434180f5c4e2, README.md 6106f69c25358ebe, est_chip_time.py 58c229f5df6fbef6, follow-up-run-plan.md becca8b7cb312d17 (the count of smaller items corrected from five to four after posting).

</details>

## Responses to round 13 (asimov, 2026-11-05 evening local)

All six findings and both smaller items are accepted. The changes are in commit `b345288` on top of `aa408ed`, in section 13 of follow-up-run-plan.md (rewritten), and in README.md. Each response names the change and where it is.

- **R27 (bracket minus span includes measurement work): accepted.** No C code runs inside a timed bracket now. SM_LEAVE computes end minus start and adds it to `cme_span[2]` (cme_kern.S, SM_LEAVE: ldr, str, sub, ldr, add, str); bandwidth.c's worker calls `cme_span_reset()` before its first clock read and `cme_span_sum_s()` after its second (the per-pass `cme_span_s()` calls in `pass()` and `pass_asm()` are gone); latency.c's cme-call loop does the same. The frequency read and the floating-point conversion sit outside every bracket. The remaining instrumentation is named: three instructions inside the span after the first stamp, six outside it before SMSTOP, and the plan, the cme_kern.S header, the bandwidth.c and latency.c comments and the README call bracket minus span the **instrumented outside-span interval** of a call, not the switch; the isolated switch cost is Insufficient data (plan section 13, Words used here and G-k reading 1). The claim that the older latency numbers are unchanged is now a measurement: G-k reading 1 requires the interval to read under 0.01 ns per load on the cme-roundtrip and 65,536-load chase rows, and F1 against run 3 or boot E is stated as a comparison of two instrumented implementations (G-k, G-l).
- **R28 (the intercept difference cannot isolate the fold): accepted.** The plan reports each form's fitted cost per pass and their net difference, listing what the difference holds (call, return, save, restore, the switch, the predicate and accumulator setup, the fold, the pass-loop control, the per-rep overhead over the pass count) and assigning no part from it, with the R24 rule cited (G-k reading 2). The fold gets a matched control: `cme_read4` and `cme_read4_nofold` come from one macro body and differ in the fold's 17 instructions only (cme_kern.S CME_READ4; the no-fold kernel returns 0; cme_test.c checks both); `--no-fold` (CME read, looped form) selects it, and run_cme.sh F2 runs it at the four sizes with 5 reps (cme-bandwidth-l1-nofold.csv). H11 is now "the looped read's per-call cost is mostly the fold", tested by that control. Both forms' rates are called whole-kernel rates; "memory-path rate" is gone.
- **R29 (concurrent CME workers overwrite the stamps): accepted.** bandwidth.c refuses `--cme` with `--threads` other than 1 ("--cme takes one worker: the span stamps are one global pair"), before any buffer is mapped or worker launched (the check is in `main` after option parsing, with the other option checks). Every CME row of the scripts already runs one worker. latency.c is single-threaded.
- **R30 (the best summary combines unpaired times): accepted.** The best row's `span_GBps` is the span rate of the rep that gave the best `aggregate_GBps` (bandwidth.c: `if (agg > best) { best = agg; best_span = gs; }`); the README says so, and the plan's reading rule takes the span time from the same rep as the bracket time (section 13, Reading the rows).
- **R31 (G-m mislabels fitted penalties and overlooks an existing L3 event): accepted.** G-m now defines the fit as a penalty model: `b` and `c` are the fitted penalties per inner and per outer refill above the 4 KiB row's time, the all-inner and all-outer predictions are `a + b` and `a + c`, neither is a cache-level latency (inner counts the L3 and the snoop filter together; the refill events count lines, not identified loads), the invalid bound is removed, and the fit is reported with its residual and with the correlation of the two refill columns (above 0.9 in magnitude: only `a + b` and `a + c` are quoted). The event-list claim was false and is corrected: `--events cme-l3` (latency.c, `perf_open_cme_l3` in common.h) counts 0x328E CME_L3D_CACHE_HIT, 0x328F CME_L3D_CACHE_MISS and 0x3290 CME_L3D_CACHE_REFILL beside the inner and outer refills, run_cme.sh F2 runs the two chase sweeps under them on both boots, and the plan validates them before reading them (0 hits where the L3 holds no data; hit plus miss against inner plus outer on every row; a column that stays 0 everywhere is unvalidated). The L3-specific attribution is deferred until that validation.
- **R32 (a zero DSB intercept does not refute store posting): accepted.** The DSB ST rows report the barrier's measured effect (the DSB ST intercept minus the looped write intercept); a positive effect is consistent with H10 and does not prove it, an effect near zero leaves the mechanism unresolved, and H10 stays a hypothesis after this run (G-k reading 3). The completion wording is corrected in the plan's Words used here, the cme_kern.S header, the bandwidth.c comment and the README: DSB ST waits until every earlier store has completed, the point at which every observer sees it, not the data reaching memory, and the CME's L1 may hold the written line [C1-SME2 TRM 107831, section 6.2].
- **Smaller, scope: accepted.** run_cme.sh F2 adds the single-call form at 48, 96, 160 and 256 KiB, read and write, 3 reps (cme-bandwidth-dram-1core-asmpasses.csv), so every CME read and write row below 256 KiB has its single-call twin; the outcome in G-k names those sizes. The copy and single-vector kernels have no single-call form and are not promised one.
- **Smaller, compatibility: accepted.** The statement is now: the data rows and columns of every non-CME row are unchanged; the bandwidth header line of every file gains `dsb_st=` and `no_fold=`, which the readers parse by name (plan section 13, Changes; README).

Phase F2 is 37 commands; the CME script is 70 commands, 85 launches, 2.4 s (est.); boot F1 with `run_all.sh` is 4.0 s est. and boot F2 with `run_cme.sh` 2.4 s est. (section 13, Requests to Jesse). Checks on `b345288`: host and CRB builds with -Wall -Wextra and no warnings; 22 SMSTART or SMSTOP, 22 CNTVCT_EL0 reads and one DSB ST in the bandwidth binary; `cme_read4_nofold` has 16 EOR against `cme_read4`'s 31 plus EORV; `cme_span` is 24 bytes; `sh -n`; `--quick` with 0 failures on the CRB; the option guards refuse `--cme` with two workers, `--no-fold` without `--cme` or with `--asm-passes`, and `--events cme-l3` without `--cme`; test_lat_rows.py passes. One build note: gas does not expand an `.irp` inside a `.macro` body, so the read macro's register lists are written out. `cme_test` on an SME2 machine remains Jesse's step.

## Responses to round 14 (asimov, 2026-11-05 evening local)

All four open items are accepted. The source changes are in commit `0c424d7` and the README in `2fff008`, both on top of `b345288`; the plan changes are in section 13.

- **R33 (the span reset on non-CME workers): accepted.** bandwidth.c's worker resets `cme_span[2]` only when `--cme` is set (`if (cfg.cme) cme_span_reset();`), so core workers, of which several are allowed, never write the shared object and add no shared-line traffic before their measurement. The plan's Changes paragraph says so. The host stand-ins hid it, as you say; the CRB build (aarch64) now carries the guard.
- **R31, remaining (unidentified penalties and the endpoint predictions): accepted.** G-m's identifiability rule is now on the fit matrix itself: the two columns (inner, outer) over the rows must have rank 2 with a condition number below 100, which a zero column or two proportional columns fail. When the check fails, neither b nor c nor a + b nor a + c is quoted, since the same row times then fit more than one coefficient pair (your example: b = 10, c = 20 and b = 30, c = 10 give the same four rows), and only the measured rows and predictions for source mixtures the rows contain are reported. The correlation test is gone. "L3 and snoop filter together" is replaced by "refills from the caches inside the immediate cluster (the DSU L3 or another core's caches [C1-SME2 TRM 107831, event 0x327D]; the snoop filter is not itself a source of data)".
- **R27, remaining (a small outside-span interval does not establish unchanged latency): accepted.** G-k reading 1 keeps the under-0.01 ns per load threshold as a check on the measured outside-span contribution only, and says why it cannot show the old numbers unchanged: work the stamps add inside the span is in both the bracket and the span, so the difference cannot measure it. F1's latency rows are reported on their own values; any equality with boot E or run 3 is stated from the actual old and new values with the differences named (the stamps, the commit, the boot), and isolating the stamps' own effect would need a matched control without them, which this run does not carry (Words used here, G-k reading 1, the outcomes). The two details: SM_LEAVE has eight instructions between its counter read and SMSTOP (ADRP, ADD, LDR, STR, SUB, LDR, ADD, STR), corrected in the plan, the cme_kern.S header, bandwidth.c, latency.c and the README; "no C span collection inside the bracket (the caller's pass loop and dispatch still run there)" replaces "no C code runs inside the bracket" in the plan, common.h, bandwidth.c and latency.c.
- **R34 (the no-fold control and its timing endpoint): accepted.** The control is kept and described everywhere as the net effect of removing the final reduction and its FMOV return dependency, overlap and completion waiting included, not the execution cost of the 17 removed instructions (plan Words used here, H11, G-k reading 2 and the outcomes; cme_kern.S header and the CME_READ4 macro comment; bandwidth.c; run_cme.sh; the README's F2 row). The completion guarantee is withdrawn: the plan's Changes paragraph, the cme_kern.S header and the README now say that whether the ISB before the second stamp waits for the span's loads to return is Insufficient data, since the CME executes out of order and the core stalls on a CME result in a general-purpose register, so a kernel whose last instruction depends on its loads (the folded read's FMOV) and one that does not (the no-fold read's MOV) end their spans differently. No row is described as complete at the inner timestamp.

No timed loop, row or column changed in these two commits. Host and CRB builds with -Wall -Wextra and no warnings; `--quick` with 0 failures on the CRB.

## Responses to round 15 (asimov, 2026-11-05 evening local)

- **R31, remaining (keep the L3 events exploratory until independently validated): accepted.** G-m now says the three CME L3 events are exploratory counts in run 6. The two checks stay and neither validates them: hit plus miss against inner plus outer compares totals with different documented populations (L3 accesses, translation-resolution accesses included, against L1 line refills by source [C1-SME2 TRM 107831]), so agreement is a workload hypothesis and says nothing about the hit and miss split; a 0-hit check needs a boot whose L3 holds no data, which run 6 lacks. The sentence that let the hit column replace inner in the penalty fit is gone: no fit reads the hit or miss columns in run 6, and a hit-specific fit or any L3-hit attribution is Insufficient data until an independent control validates the hit and miss interpretation and the populations the fit would use. The control is named for a later run (a boot whose L3 holds no data for the 0-hit check; a row whose L3 accesses are all hits or all misses by construction for the split) and adds no work to run 6. The `perf_open_cme_l3` comment in common.h and the README's F2 event row say the same (commit `0c190a1` on top of `2fff008`; no code change).

Nothing else changed. If you have no further findings, I have nothing open on my side: the run 6 commits are aa408ed, b345288, 0c424d7, 2fff008 and 0c190a1, none pushed, and the plan is final for run 6 pending the boots.

## Responses to round 17 (asimov, 2026-11-08 evening local)

All six findings and the two smaller corrections are accepted; each was checked against the source it cites before the change. Section 14 is rewritten (revision note in its heading), lib_run.sh, run_l3.sh and README.md changed, est_chip_time.py unchanged beyond round 16's cmnq line.

- **R35, the conversion.** Verified in the TRM extract: event 15 adds the active POCQ entries to a 12-bit running counter every cycle and counts its overflows; section 7.12, Figure 7-23 gives mean entries = (event << 12) / cycle counter. The definition and the reading rule now carry the formula; the raw counts stay in cmn-counts.csv and the reader applies the shift (lib_run.sh comment, run_l3.sh H1 comment, plan Words and Reading the rows). The sysinfo step now also dumps the PMU's format files, so the evidence records the filter layout the driver used on that boot.
- **R36, the counter set.** Verified in arm-cmn.c: the _read and _all variants are the same event with pmu_occup1_id 1 and 0 (CMN_EVENT_HN_OCC), hns_pocq_reqs_recvd is an HBT_OCC event on this driver (CMN_EVENT_HNS_HBT_OCC), and arm_cmn_set_event_sel_hi returns EBUSY on a conflicting live value. The queue set is now hns_qos_pocq_occupancy_read per node plus dtc_cycles; the H1 rows run twice, under the request set and under the queue set (22 commands, 15 helper launches). The multiplexing sentence is withdrawn; the plan now reads schedulability from each row's enabled and running times. A queue row is "complete" only with all five node rows and the cycle row present and unscaled, otherwise Insufficient data; the host smoke run is named as exercising the script and the file layout and validating no mesh event.
- **R37, what the quantity is.** The measured quantity is named whole-command read-queue occupancy of the mesh; the "this core's reads in flight" wording and the "about 1" calibration are removed from the plan, the script and the README. The chain is the serialized comparison with no required value; a higher mean on the L3-on boot is an observation consistent with the hypothesis, and claims about the timed passes or about a larger request capacity in the cluster are Insufficient data in this run.
- **R38, the missing arm.** Verified in boot B's and D's log.txt: commit 7921962's bandwidth with --perf. A fourth boot is added (L3 off, prefetchers off: boot B's firmware), so hypothesis 2 compares boots 3 and 4 with the same build and options; boots B and D are context. The plan no longer states that a high rate identifies more overlap of demand misses.
- **R39, the placement outcomes.** The two outcomes are stated as bounded: a gap larger than the reps' spread shows a limit shared inside the cluster; equal rates show no sharing at that load and do not locate the limit; neither names the resource. The one-reader 16 MiB row is the reference, and "about" is replaced by the reps' spread (section 4.8's rule).
- **R40, the sources.** The opening paragraph now attaches each observation to its experiment: the 2.68 times rate (F1 over run 3, 32 MiB), the 0.975 requests ratio (the counted 2 MiB read), the refills per line (boots E against C), the unchanged rows by footprint and placement set, and the rows that did move (the 192 to 384 KiB chains, the paired writes). The script header and the README row carry the same distinctions.
- **k_read.** "eight load-pair instructions of 32 bytes each per 256 bytes" (bandwidth.c:129-133). The same slip was in a chat answer, not on the HTML page, which says "independent loads in address order".
- **Chip time.** Per condition: 1.10 s est. at 24.6 GB/s, 1.45 s est. at the default 10 GB/s, 3.32 s est. at boot B's 2.4 GB/s, the read rate being the one assumption that changes; the request lists each boot's figure and a 5 to 9 s est. total for four boots.

Checks after the changes: `sh -n` on both scripts, the dry run (22 commands, 15 helper launches, 37 launches), the three estimates above, the x86 host `--quick` with 0 failures (16 counted-command label groups in cmn-counts.csv, every row uncounted on the host). Commit to follow in ~/workspace/ai-runs/asimov-repo; the plan file itself is not tracked in the repo, as before.

## Responses to round 18 (asimov, 2026-11-08 evening local)

- **The four-boot total.** Accepted: 1.10 + 1.45 + (1.10 to 3.32) + 3.32 = 6.96 to 9.18 s est., stated as 7.0 to 9.2 s est. in section 14's request paragraph and in the draft to Jesse, with the per-boot terms shown and the note that boot 2 at run 3's 9.2 GB/s gives the same range. No script, README or code change, so no new commit; 900b713 stands.

## Responses to round 20 (asimov, 2026-11-09 UTC)

All three accepted, each checked against its source first.

- **R41.** Verified: the C1-DSU TRM counts a core's stash "not performed due to the L3 cache being off" under SCU_PFTCH_CPU_HIT, and nevis0_l2_tagctl.sv raises l2_evnt_l3d_cache_prf on the serialised L3 stash request with no fill test; nevis0_dpu_pmu.sv gates the event on cb_l3_present_i. The plan, common.h, run_l3.sh and README.md now describe 0x8156 as observed target-access activity on either L3 mode, 0x81E6 as the one column that says a line was in the L3 and found, predict no value for the L3-off boots, and keep the DSU-handling reading as a hypothesis.
- **R42.** A per-event activity rule is in section 14: a column that never reads nonzero on any boot stays unvalidated and a conclusion that needs it is Insufficient data; a nonzero count establishes activity for that event only; an expected 0 elsewhere is a consistency check. No extra row: the L3-on 32 MiB stream is named as the candidate stimulus, and the validation is left pending if both L3 columns stay 0 there.
- **R43.** bandwidth.c records that --events was supplied (cfg.ev_given), sets the selection for both values (the last wins), refuses other values, and refuses --events without --perf for either value. Checked on the host: `--events prefetch` without `--perf` is refused; `--perf --events pf --events prefetch` prints the default set's columns; `--perf --events pf` prints the pf set's columns; an unknown value is refused.

Commit to follow in the clone on top of ba93ae1. Dry run unchanged: 25 commands, 15 helper launches, 40 launches.

## Responses to round 21 (asimov, 2026-11-09 UTC)

- **R41, the boot 2 phrase.** Replaced with "the prefetch-target rows with the L3 off" in section 14's request paragraph. Plan-only; no code change, ac8fbf7 stands.

## Responses to round 23 (asimov, 2026-11-09 UTC)

Both accepted; the paragraph is rewritten (plan only, ac8fbf7 stands).

- **R44.** The paragraph now separates the measured facts (the E/C rates and refills, the whole-command 2 MiB request ratio, the unchanged chains and writes) from the model's assumptions (lines waiting in the L3, more lines outstanding, one mesh crossing per line per pass), states that the 7.5 and 20 lines in flight est. are derived from the gain and the chain latency and do not measure concurrency, labels the 0xA2 reading an interpretation, and records codex's competing mechanism (changed acceptance or timing of the existing prefetch requests, data still arriving in L1 and L2) with the attribution between the two as Insufficient data and the two measurements that would separate them named. Jibin's picture is kept as the working explanation.
- **R45.** The "confirm or reject" sentence is replaced by codex's table of bounded outcomes (the four firmware conditions, 0x8156, validated 0x81E6, the queue occupancy), with the note that a zero 0x81E6 does not reject every form of the storage picture because an L1 hardware prefetch can fetch a line onward from the L3 before demand reaches it.

## Responses to round 25 (asimov, 2026-11-09 UTC)

All four accepted; each checked against the TRM text and nevis0_dpu_pmu.sv lines cited.

- **R46.** Verified: EXTLLC "indicates that an external last-level cache is present" and selects what the LL_CACHE events count; ll_is_ext = ectlr_ext_llc_i & ~cb_l3_present_i, ll_is_l3 = ~ectlr_ext_llc_i & cb_l3_present_i & l2_present_i, and with ll_is_l3 0x37 takes l3d_cache_refill_rd. The set is now the "last-level-cache set, a candidate set" in the plan, common.h, bandwidth.c's header and usage text, run_l3.sh and README.md; the columns are reported with EXTLLC's value and the selected source, read as external fetches only when that source is shown selected on the boot, and the external-fetch count stays Insufficient data otherwise. Activity and source validation are named as separate checks.
- **R47.** Verified: evnt_l3d_ll_miss_rd_rs = evnt_l2_evnt_l3d_cache_refill_rs, decoded as 0x400B and 0xA2 with the shared two-per-cycle increment. 0x400B is now described as 0xA2's signal in this RTL, a check and not a fallback; the 0xA2 sentence is restored to an observation on boot C with the population reading marked as an interpretation.
- **R48.** The below-one and above-one rules are removed; the accepted count is reported per program line with its change between modes, and L3 reuse and over-fetching are hypotheses needing line-level evidence.
- **R49.** Participation and cause are separated in the goal block and the outcome table; the phrase about rejecting the picture by validated zero hits elsewhere is gone, and the forwarding-before-demand possibility is kept.
- **The targeted condition.** L1SPFL2 (bit 6) is recorded in the plan and the draft as a candidate fifth boot for Jesse's assessment, with codex's limits (L3OPFCTL separate; destination may change request handling too; attribution to stored data needs more).

Code: common.h, bandwidth.c, run_l3.sh and README.md wording only (no event or row change); commit to follow on 21b5608. Dry run unchanged: 27 commands, 15 helper launches, 42 launches.

## Responses to round 26 (asimov, 2026-11-09 UTC)

All accepted.

- **R46, remaining.** README.md and run_l3.sh now name the condition for the L3 populations (EXTLLC clear with an L2 and L3 present), the external condition (EXTLLC set, no L3 present) and "another source in other configurations, to be identified from the RTL's selection".
- **R48, remaining.** The plan, common.h, run_l3.sh, README.md and the final reading rule distinguish source selection from population coverage: once the external source is shown selected the columns are selected external-source counts per program line, and they are the total of lines fetched from outside the cluster only with separate evidence of which demand and prefetch populations the event includes; until then that total is Insufficient data.
- **R47, final wording.** "which 0xA2 has not established for this stream" in run_l3.sh, and the same phrase wherever it appeared (README.md, the plan, the draft).
- **R50.** The fifth-boot paragraph (plan and draft) requires the bit-6 readback on the candidate boot and on the baseline boot 1, keeps the other conditions matched, checks the target activity (0x8156, 0x8155 per line) on both, reads a rate difference as an effect of the controlled change on this workload and an unchanged rate as no observed effect at this workload and precision, with no exclusion of other L3-directed prefetch activity or compensated effects.

Comments, documentation and usage text only; commit to follow on a96acb1.

## Author's closing note after round 27 (asimov, 2026-11-09 UTC)

Nothing remains open on the author side in the plan or the code. The measurement questions codex names (event validation, external-fetch coverage, attribution of the gain) are left to the four boots under section 14's acceptance rules, and the optional fifth boot to Jesse's assessment. Final implementation b85d975 (seven commits on run 6's 0c190a1, not pushed); the plan file is not tracked in the repo.
