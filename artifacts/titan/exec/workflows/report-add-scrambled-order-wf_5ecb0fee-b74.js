export const meta = {
  name: 'report-add-scrambled-order',
  description: 'Add the scrambled-order finding (F5) to the report, then review the change and fix',
  phases: [{ title: 'Update' }, { title: 'Review' }, { title: 'Fix' }],
}
const W = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15'
const OUT = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop.html'
const RAW = '/home/jhan/workspace/titan/cache-perf/crb/results/w120-R7-20261115T205946Z'
const CTX = `Report: ${OUT}, built by the generator ${W}/report_w120.py (Python 3, standard library, inline SVG, single LIGHT theme). Source of truth: the facts sheet ${W}/FINDINGS.md, which now has a section "F5. The drop needs a sequential stream" (scrambled-order loops; raw files in ${RAW}: per group two bwx CSV files <group>.m0.csv and <group>.m1.csv with rows "T,round,pos,kernel,tid,cpu,bytes,elapsed_s,..."; thread rate = bytes/elapsed_s; helper ${W}/ang.py prints the sums). The report does not yet contain F5. Style rules of the report (mandatory, as in the rest of the page): plain English, short sentences, one claim per sentence, no idioms or metaphors, every number with a unit, estimates marked "est.", terms defined at first use or in "Words used here", citations as [RefN] after the sentence with the list at the end, light background only, charts with direct value labels, a plain annotation and a one-line takeaway, exact numbers in a compact table next to the chart.`
phase('Update')
const upd = await agent(`${CTX}

Task: extend the generator and rebuild the report so that it covers F5. Recompute the F5 numbers from the raw files first (all 13 groups; sums per mesh and total, per-thread min-max) and use the recomputed values; if they differ from the facts sheet by more than rounding, use the raw values and list the difference. Changes:
1. A new section after the "slow state is not congestion" section: "The drop needs a sequential stream". Content: what the scrambled-order loops are (same loads and padding as the load-only loop, the loop with 96 nop and the loop with 256 nop; the 8192 blocks of each 2 MiB chunk are visited in a scrambled order so that the hardware prefetcher cannot follow), the one-thread rates, the 64+56 results, and the reading (three bullets of F5). New Figure 4: paired bars or a dumbbell with three rows (no padding / 96 nop / 256 nop; window depth 36-40, 20-24, 8-12 lines) comparing the total at 64+56 in sequential order (297.8 in the same run for no padding; 465.5-470.6 for 96 nop from the earlier table; 547.2 in the same run for 256 nop) with scrambled order (489.6, 473.5, 382.5), zero-based axis, value labels, annotation "the order of the two curves is reversed", takeaway line. A compact table with all 13 groups (mesh 0 sum, mesh 1 sum, total).
2. Update the Short version (still at most three sentences), the section "what is established and what is not", and any sentence that says the rule may be "in the core or the mesh": the measured narrowing is that a load-only loop with the same window reads 489.6 GB/s in scrambled order and 297.8 GB/s in sequential order, so the deep window alone does not lower the total and the drop is tied to how the cores handle a sequential stream (hardware prefetch and its request limit); the exact rule inside the core is still NOT established; keep the candidate hypotheses and the measurement that would resolve them. Do not overstate: F5 has one interval of 10 s per cell, one evening.
3. Update the time span (runs until 21:03 UTC), the sample-count table (R7: 13 groups, 24 processes, one 10 s interval each), the word list (scrambled order, hardware prefetcher if not yet defined), and the references (the R7 folder, the bwx13 folder /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx13-2026-11-15).
4. Also correct in FINDINGS.md the three known small errors, so that sheet and report agree: (a) "squeezed read_nop256 7.0-7.7" -> "7.0-7.6"; (b) "the three variants measured at 26-32" -> four variants (read_nop56, read_dadd4, read_nop64, read_sp32); (c) the load sentence in the header: the 1-minute load average at script start was 0.00 to 71.24 and up to 109.60 at process launch, with 1 runnable task and 0 logged-in users at all launches; high values follow the script's own earlier 120-thread processes (hypothesis: decay of the load average; not checked further).
Rebuild, re-run the generator's own checks (well-formed HTML, label overlaps), check that every number in the new parts is in the facts sheet or in your recomputation, and render with headless Chrome if available under ~/.cache/ms-playwright to look at Figure 4 and the Short version. Modify only report_w120.py, the report HTML and FINDINGS.md. Report what changed, the recomputed F5 table, and the check results.`, { label: 'add-F5', phase: 'Update' })
phase('Review')
const rev = await agent(`${CTX}

An editor has just added the F5 content to the report. Editor's report:
${upd}

Task: review, read-only. (1) Recompute the F5 numbers from the raw files with your own script and compare with every F5 number in the report (section text, Figure 4 labels and plotted positions per the generator, table). (2) Read the whole report top to bottom once: check that the Short version (at most three sentences) is consistent with all sections; that no sentence still says the rule may be in the mesh without the F5 narrowing, and none claims the exact core rule is established; that the claim strength matches the evidence (one 10 s interval per F5 cell). (3) Check the new text against the style rules (list violations with the exact phrase and a corrected version). (4) Check that the page has a single light theme and that all [RefN] used exist in the reference list. Return a numbered list of concrete defects with fixes, or "no defects". At most 700 words.`, { label: 'review-F5', phase: 'Review' })
phase('Fix')
const fix = await agent(`${CTX}

The F5 content was added and reviewed. Reviewer's findings:
${rev}

Task: verify each finding, fix the real ones in the generator (and FINDINGS.md if a finding shows it wrong from a raw file), rebuild the report, re-run the checks (well-formed HTML, label overlaps, numbers present in the facts sheet, render check if Chrome is available). Modify only report_w120.py, the report HTML and FINDINGS.md. Report: fixes made, findings rejected with reasons, the final Short version text verbatim, the final file size, and check results.`, { label: 'fix-F5', phase: 'Fix' })
return { upd, rev, fix }
