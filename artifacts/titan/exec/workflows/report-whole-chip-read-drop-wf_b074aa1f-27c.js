export const meta = {
  name: 'report-whole-chip-read-drop',
  description: 'Build the HTML report on the 120-thread read drop from the verified facts sheet, then review numbers and wording and fix',
  phases: [{ title: 'Build' }, { title: 'Review' }, { title: 'Fix' }],
}
const W = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15'
const OUT = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop.html'
const SPEC = `Deliverable: one self-contained HTML report at ${OUT}, produced by a generator script ${W}/report_w120.py (Python 3, standard library only; inline SVG charts; no external scripts, fonts or images) so that it can be rebuilt. Source of truth for every number: the facts sheet ${W}/FINDINGS.md (read it completely; use its numbers exactly; do not add numbers that are not in it or that you did not recompute from the raw files it names). Reader: an engineer who has never seen the project.

Required structure:
1. "Short version" (at most three sentences) - the answer to: "when the new test kernel was used, the whole-chip throughput of read, write and copy all went down - why?"
2. "Words used here" list (CRB, kernel = one timed loop of the benchmark not the Linux kernel, old read / new read / asm read, padded loop, nop, mesh 0 / mesh 1, 64+56, window (out-of-order window) and window depth in lines, line = 64 B cache line, lines in flight, gateway, memory port, home node, busy level, common stop / whole-pass stop, squeezed, GB = 1e9 bytes, est.).
3. The findings in this order, each as a short section with bullets: (a) which of read / write / copy really dropped (with the write timing-rule explanation and a compact table); (b) the read rate against window depth - Figure 1; (c) the padded loop follows the old loop in every thread layout - small table; (d) the share effect with mixed loops - Figure 2; (e) the slow state is not congestion: latency probe and lines in flight - Figure 3, plus a compact table of mesh counters slow vs fast and the memory-port counts; (f) what is established and what is not (the "Insufficient data" items with the measurement that would resolve each); (g) recommendation for the benchmark; (h) how it was measured (machine state, load, scripts, root use, sample counts) ; (i) References section at the end: numbered [Ref1].. list of result folders and scripts; in the body cite as [RefN] after the sentence that carries the claim.
Figures (inline SVG, each with direct value labels, a plain-language annotation on the figure, and a one-line takeaway under it):
 - Figure 1: scatter/dot plot, x = measured window depth in cache lines (use the midpoint of the measured range, draw the range as a thin horizontal bar; x axis from 0 to about 45 lines, and show read_1pl at 156-164 lines with an axis break or a separate small panel), y = total read rate at 64+56 in GB/s from 0 (honest zero-based axis), one dot per loop variant at the middle of its min-max with the min-max as a vertical bar; label the old read loop, the new load-only loop, read_nop72, read_nop256, read_iadd16, read_1pl; shade the band 28-32 lines as "switch"; three colours by what limits the window: padding instructions (nop), vector adds, plain loads (colour-blind-safe palette, also distinguish by marker shape).
 - Figure 2: grouped bars, one group per pair of loops (mesh 0 loop | mesh 1 loop) for the nine mesh-split combinations of F3, two bars per group (mesh 0 sum, mesh 1 sum) with value labels and the total above each group; mark the reference "mesh 0 alone with the load-only loop = 348 GB/s" as a dashed line.
 - Figure 3: dumbbell or paired dot plot of estimated lines in flight per core (est.) for the slow or squeezed meshes (6.5-9.2) against the fast meshes (14.9-25.3), one row per case of F4 (mesh and loop named), with the probe time in ns written next to each row; annotate "a request is not slower in the slow state: 203-211 ns against 238-297 ns".
Style rules (mandatory): LIGHT background only (single light theme, no dark mode, no prefers-color-scheme switch); plain English: short sentences, one claim per sentence, no idioms or metaphors, every number with a unit, estimates marked "est.", every term defined at first use or in the word list, bullets instead of dense paragraphs; neutral technical tone, no preamble or closing remarks; tables compact; exact numbers stay available in tables next to the charts. State plainly the limits: one evening (2026-11-15, 16:56 to 20:50 UTC), one machine, sample counts as in the facts sheet; the internal rule that lowers the lines in flight is NOT established. Do not claim more than the facts sheet does. Do not modify any file other than the two named above.`
phase('Build')
const built = await agent(`${SPEC}

Task: write the generator script and build the report. Run the script, check that the HTML is well-formed (python html.parser pass, every SVG has width/height/viewBox, no text overlaps that you can detect by computing label positions), and that every number in the HTML appears in the facts sheet (write a small check that extracts numbers and compares, and review the leftovers by hand). If a headless Chrome is available under ~/.cache/ms-playwright (find it with ls), render a screenshot to your scratchpad and look at it to catch layout defects; otherwise say that no render check was made. Report: what was built, the checks run and their results, and anything from the spec that was not done.`, { label: 'build-report', phase: 'Build' })
phase('Review')
const lenses = [
  ['numbers', `Check every number, unit, range, sample count and claim in the report against the facts sheet ${W}/FINDINGS.md, and spot-check at least 15 numbers of different kinds against the raw result files that the facts sheet names (bwx CSV: rows "T,round,pos,kernel,tid,cpu,bytes,elapsed_s,..." and "I,...,aggregate_GBps"; perf files "count,unit,event,run_ns,run_percent,," where event names may contain commas). Check the three figures: are the plotted positions consistent with the labelled values (read the generator script ${W}/report_w120.py), are axes zero-based where bars are used, are labels attached to the right marks. Check that no sentence claims more than its evidence: in particular (1) the internal rule that lowers the number of lines in flight is not established; (2) lines in flight are estimates; (3) one evening, one machine; (4) "window depth" values are measured ranges from a one-thread test; (5) the write explanation says "most of", with the 3 to 4 % remainder; (6) busy-level statement includes the in-between cases.`],
  ['wording', `Check the report text against these rules and list every violation with the exact phrase and a corrected version: starts with a "Short version" of at most three sentences that a newcomer can follow; no idioms, metaphors, wordplay or uncommon words (test: would a non-native English speaker with an engineering degree need to guess?); one claim per sentence (split sentences with "because", "since", "which means", "so that", or a semicolon where possible); short sentences; bullets or blank lines to separate points; every number carries a unit and, where the reader cannot judge it alone, a plain meaning; estimates marked "est."; every code name, acronym, metric or project term defined at first use or in the "Words used here" list; citations as [RefN] after a full sentence with the list at the end, never a bare file path in the body; no preamble, no closing pleasantries, no hedging for politeness; light background only (inspect the CSS: no dark theme, no prefers-color-scheme). Also check that the chart annotations are plain language and that the page reads correctly top to bottom for someone who reads only the Short version, the figures and their takeaways.`],
]
const reviews = await parallel(lenses.map(([k, what]) => () => agent(`A report was built to this specification:
${SPEC}

Builder's report:
${built}

Task: review the report ${OUT} and its generator ${W}/report_w120.py, read-only (do not edit them). Lens: ${what}
Return a numbered list of concrete defects (location, what is wrong, the fix). Say "no defects" for a lens item that is clean. At most 900 words.`, { label: `review-${k}`, phase: 'Review' })))
phase('Fix')
const fixed = await agent(`A report was built to this specification:
${SPEC}

Two reviewers reported defects:
--- numbers review ---
${reviews[0]}
--- wording review ---
${reviews[1]}

Task: verify each reported defect against the report and the facts sheet, fix the real ones in the generator ${W}/report_w120.py, rebuild ${OUT}, and re-run the build checks (well-formed HTML, numbers present in the facts sheet, render check if Chrome is available). Do not change numbers away from the facts sheet unless a reviewer showed from a raw file that the facts sheet is wrong; in that case list it clearly. Report: defects fixed, defects rejected with the reason, facts-sheet errors found (if any), final file size, and the checks' results.`, { label: 'fix-report', phase: 'Fix' })
return { built, reviews, fixed }
