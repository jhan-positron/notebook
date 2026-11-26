---
name: review-loop-claim-defect-classes
description: Seventeen kinds of claim defect to sweep for before READY in the inter-agent review loop, before a final report, and before I propose a replacement text for approval (found in the CRB report update of 2026-11-12 by the reviewer agent and by five rounds of checkers)
metadata:
  node_type: memory
  type: feedback
  originSessionId: 6eb09a16-5942-4cc5-8ed0-249c7d5ab696
  modified: 2026-11-13T03:37:57.054Z
---

Before a report or record goes to the reviewer of the inter-agent-review-loop skill, sweep all new text for the kinds of defect below. The reviewer agent wrote one finding of each of the first four kinds on 2026-11-12 (session 20261111T222457Z-33f3e5, files `crb/crb-memory-hierarchy.html` and `~/tmp/update-crb-memory-hierarchy.md`), and an internal sweep then found about 40 more places of the same kinds in text that I had already called finished.

1. **Capacity against saturation.** A hypothesis about a maximum (for example "one flit per mesh cycle") is separate from the statement that a test reaches that maximum, and from the conversion between a loop rate and the counted quantity. A low observed rate cannot reject a capacity. A counter mismatch tests the conversion, not the capacity. Say which observation tests which statement, and set no numeric threshold without measured variation.
2. **Observed rate against limit.** "The loop ran 1.0 passes per cycle" is an observation, not "its limit is one pass per cycle". No universal exclusion ("no other limit in the guide is reached"): name exactly the limits that were compared. A retained mechanism is a labelled hypothesis with the test and the result that would reject it.
3. **Runs kept apart.** Do not assign a number of one run (date, counter set, thread placement, loop variant) to another run. Say when a total and its split come from different runs, and label the link as an interpretation.
4. **Category against source.** A table category or a phrase such as "CMN-based" or "next to the PLL name" must be what the cited source itself establishes. "Medium confidence" is not evidence.

Two more kinds that my own second sweep found on 2026-11-12 in text that had already passed one sweep:

5. **Status of a number.** A count, a count that the tool scaled, a derived value and an assumed value are four different things. Say which one each number is (see [[crb-scaled-perf-counts]]). If a conversion is named as an assumption in one place, every other use of it must name it too.
6. **The change list against the reviewer's baseline.** The section that lists the changes of a round must match a `diff` against the files that the reviewer read. A quotation in that list must be findable in the reviewer's version, or be labelled as draft text.

One more, from the reviewer agent's round-2 finding CRB-R5 (2026-11-12):

7. **A deferred defect in a line that my change revised.** When I find a defect class in older text and list it as "found and not changed", I must still correct every instance in a line that my own diff touches. Only untouched lines can be deferred. The reviewer rejected a caption and a table cell that I had revised and then listed as "outside this change".

Two more, from the second check of my own record on 2026-11-12 (section 10 of `~/tmp/update-crb-memory-hierarchy.md`). Both are my reading of checker findings, not user feedback:

8. **A check that the record claims must name its file and the state it ran on.** "A script compared the sentences" had no script behind it any more, and its counts (60 and 47) could not be repeated (57 and 44). "The figure was rendered and viewed" named a render that was older than the last label change. Keep the script, name it in the record, and re-run renders and counts after the last edit. The session scratch folder does not last, so copy the evidence to `crb/tmp/agent-scratch/<topic>-<date>/` and cite that path.
9. **A range belongs to exactly the runs that the sentence names.** I wrote "in those runs each pair read 62.9 to 63.7 GB/s" for the runs that gave a count. The range was from all ten runs of the case, and the two counted runs gave 63.0 to 63.1 GB/s. Half of a four-thread total is an average for a pair, not "each pair": say "on average" when the file has no row per thread.

Three more, from the check of the texts P1 to P3 after the user had me apply them on 2026-11-12 (section 11 of the same record). They are my reading of checker findings, not user feedback. The checkers found them inside text that the user had already approved:

10. **The loop and the run behind every rate.** A rate needs its loop (asm or compiled from C), its CPUs, its date and its kind of run (the 2 s runs or the 0.2 s runs of a counter case) whenever another loop or run gives another value. "One writer alone already reaches the rate of the pair" was true for the asm loop only. A conversion must not apply a count of one loop to a rate of the other loop: a table row converted a pair rate "from one run with each write loop" with a bus count that exists for the asm loop only.
11. **The sample of a test.** "Cores 2k and 2k+1 together read 78 GB/s" speaks for every pair, and the pair test ran on three pairs. Name the sample (three pairs, CPUs 0 to 5) and say which test covers all (the latency fit). The same holds for "each writer falls from 71 GB/s" when only one of the writers was measured alone.
12. **A universal "no run counted".** "No run counted both cores of a pair" was false, because home-node and link counters did run with both cores busy. Say exactly which counter of which cores no run holds ("the bus accesses of both cores"), and check the sentence against every counter set of the result files.

Two more, from the last check of the same step on 2026-11-12 (third pass, section 11.7 of the record). They are my reading of checker findings, not user feedback:

13. **A list that the sentence announces as complete.** "Other runs were not converted. They are the write runs ... and the copy runs" announced all such runs, and the result files held two more kinds. "All rates in this list are from the asm write loop" stood over a list with three rates of the other loop. Before writing "they are", "all" or "no run ... alone", scan every result file for runs of the same kind, and scope the sentence ("at 8 MiB or 1 GiB", "except where a sentence names the loop", "writing alone"). When two places of the report hold the same list, change both.
14. **The evidence of the final state, and the place of a statement.** The record named a folder of renders that held screenshots of the pass before, and the final renders were made after the record's last write. Order after the last edit: render, view every piece, copy to the evidence folder, then write the row that names the folder. Copy the final state of each changed file there too: on 2026-11-12 a second session of the user wrote the report 20 minutes after my last write, and after that no file on disk had the sha256 that my record names, except my copy. The record also cited "section 10.5" for a recommendation that I had given only in a chat answer: cite the place where a statement really stands, and say when it is not in the record.

Three more, from the reviewer agent's round-1 findings on 2026-11-13 (session 20261113T0635Z-k7c2, file `~/tmp/k_cread.md` and its linked page `crb/results/cread-20261113T060510Z/cread-result.html`). They are my reading of reviewer findings, not user feedback:

15. **A rounded value used as a strict bound.** "At most 0.6 %" was false for 0.618 %. Write "less than 0.7 %" or "about 0.6 %", and write "nearly equal", not "the same", when the values differ.
16. **A value converted with an assumed constant is an estimate.** Loads per cycle computed from GB/s at an assumed 2.8 GHz need "est., assuming 2.8 GHz" in the table header, in the chart label and in each sentence, and not the verb "reach".
17. **The linked page gets the same strictness as the handoff.** A check by hand whose output was not saved must say so on the page too, and must not carry file references. A definition of a general term (Linux load average) and a schedule from an older record (the weekday block window) are claims as well: check them against the source and against later exceptions.

**Why:** the user's rule "Interpret test results with proof" already demands this, and the reviewer enforces it finding by finding. Each round costs hours.

**How to apply:** run the sweep (one checker per kind plus a skeptic) on the whole diff and on the whole record before the first READY, not after the reviewer's comments. Run it also on a replacement text before I offer it to the user for approval: the user approves the wording that I show, so its defects become approved defects, and each later fix is a visible deviation from the approved text. Proposed replacement texts in a "found and not changed" list are claims too and get the same check. My interpretation: the reviewer treats the record with the same strictness as the report.

Related: [[svg-render-check-without-browser]], [[aarch64-disassembly-source]].

Kinds 18 to 21 (from the review of the plan `~/tmp/investigate-new-c-mysteries.md`, 2026-11-13; they apply to test plans):

18. A rejection rule stronger than the intervention: a test that changes one factor "rejects" a hypothesis that has two parts, or "not seen in a finite run" is written as "rejected". Split the hypothesis, state a bounded prediction, and use "not observed" / "not resolved".
19. A control that removes the suspected cause before the difference is reproduced (aligning all loops when alignment is a hypothesis; replacing the timing method when the timing method is a hypothesis). Keep a reproduction condition with the original setting.
20. A screening step (existing binaries, no controls) that the decision section lets close a hypothesis. Mark it as screening and name its exceptions to the rules.
21. A decision rule that cannot fire for a negative difference (median compared with a non-negative spread without an absolute value), and a remaining effect assigned to "the hardware" when only some software causes were excluded.

Kinds 22 and 23 (from the reviewer agent's findings on 2026-11-14, session 20261114T0717Z-b8f8, file `crb/new-test-kernel/results.md`; my reading of reviewer findings, not user feedback):

22. A result handoff that never answers the original question. The file gave one word per hypothesis and a reproduced difference, and did not say whether the two original questions were resolved. Lead with a direct verdict per original question, and keep apart "measured", "not established" and "missing evidence". Complete runs are not a complete causal investigation. A change of labels or limits can change a result word and cannot add an observation, so do not write "no new measurement is needed" or "only item N needs a new run" for a question whose evidence is missing.
23. A sentence added inside a correction is a new claim. Two of my correction rounds each added one unsupported universal ("they are not planned", "the others have no test protocol yet") and each cost a round. Check every added sentence against the plan before READY, and add no sentence that the finding did not ask for.
