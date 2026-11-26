export const meta = {
  name: 'crb-report-fix-check',
  description: 'Second adversarial pass: verify the fixes made after the first review, the disassembly-based text, the pair-port open item, and the update record',
  phases: [
    { title: 'Check', detail: '4 independent checkers, each told to find defects' },
  ],
}

const PRJ = '/home/jhan/workspace/titan/cache-perf'
const REPORT = PRJ + '/crb/crb-memory-hierarchy.html'
const BACKUP = PRJ + '/crb/tmp/crb-memory-hierarchy.before-spec-row.html'
const VDIR = PRJ + '/crb/tmp/agent-scratch/spec-row-2026-11-11'
const KIT = '/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit'
const MD = '/home/jhan/tmp/update-crb-memory-hierarchy.md'
const PROBE = PRJ + '/crb/results/probe-20261111T210017Z.txt'
const SP = args.scratch
const R1 = SP + '/review_out'

const CTX = `You are one of 4 independent checkers of an edited HTML report and of the record that documents the edit. Your job is to FIND DEFECTS. Assume the editor made mistakes. Your structured output is raw data for the editor.

FILES
- Edited report (current state): ${REPORT}
- The report before the edit: ${BACKUP}
- The update record written by the editor: ${MD}
- New raw file from the measured machine (one read-only login on 2026-11-11): ${PROBE} . It holds versions, mesh event names and the disassembly of four functions.
- Project: ${PRJ} (bench/ = benchmark source, crb/results/ = raw results, crb/refs/ = Arm PDFs: CMN S3 TRM 107858 = "TRM", Neoverse V3AE Software Optimization Guide 110075 = "SOG").
- Vendor kit: ${KIT} (read-only). The SVK user guide is ${KIT}/svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf . The Linux driver source is inside ${KIT}/svk-release/linux/arm-agi-cpu-linux-7.1.3-v0.9.0-source.tar.gz (extract drivers/perf/arm-cmn.c into your scratch directory with tar --wildcards if you need it).
- Findings of a first review round, one text file per reviewer: ${R1}/compliance-diff.txt, refute-mesh-clock.txt, refute-core-pipeline.txt, figure-audit.txt, plain-english.txt, consistency-sweep.txt . The editor changed the report after that round.
- Editor's helper scripts (read them before you trust them): ${VDIR}/check_geometry.py , render.py , mesh_clock.py .
- Your scratch directory: ${SP}/check2/<your task name>/ (mkdir -p). Write nothing anywhere else.

RULES
- READ-ONLY for the report, the backup, the record and every project file. Do not contact the measured machine (CRB, 192.168.x.x).
- Tools: python3 with PyMuPDF (import fitz) for PDFs; no pdftotext; no browser. Lines of the report are long: print only what you need and wrap it.
- Two texts in the report are the author's own wording and stay verbatim: the list item "The 8 reserved cores (120-127) were never used - this is a simple operation agreement ..." and the table cell "Measured (averaged over all slices). Range: 19 to 44 ns by slice."
- The author asked for the word "unknown" in the Spec boxes of the pair port and the mesh cache, and asked only for an investigation of the term "mesh cache". Do not report these two decisions as defects.
- Every finding needs evidence: file path plus line or page with a verbatim quote, or a computed value and how you computed it. If you could not check something, list it under not_checked.
- Severity: "blocker" = a statement is false, or the record says something was done that was not done; "major" = misleading, unsupported, or a regression; "minor" = small inaccuracy, wrong line number, citation slip, unclear wording; "note" = observation.
`

const SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', description: 'Two or three plain sentences' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'] },
          location: { type: 'string', description: 'File and line of the current file' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string', description: 'Exact corrected wording, ready to paste' },
        },
        required: ['id', 'severity', 'location', 'problem', 'evidence', 'fix'],
      },
    },
    confirmed: { type: 'array', items: { type: 'string' } },
    not_checked: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'findings', 'confirmed', 'not_checked'],
}

const TASKS = [
  {
    key: 'fix-verification',
    prompt: `TASK NAME: fix-verification
1. Read the six first-round files. For every finding of severity blocker, major or minor that concerns text the edit added or changed (not the findings marked as pre-existing text that the edit did not touch): is it resolved in the current report? Answer per finding id: resolved, partly resolved (say what is left), not resolved, or deliberately left (the editor's record ${MD} sections 4 and 6 say why). Report only the ones that are not fully resolved and are not covered by the record.
2. Regressions from the fixes. Diff the backup against the current report. Check again: tag balance of the whole file with html.parser; both <script> blocks and the <style> block byte-identical to the backup; all id and href values unchanged; <marker id="ar"> defined once and still referenced; nested lists in the "Open items" section well formed (the first item now holds a nested <ul> with a second nested <ul>); the two <p class="note"> blocks under the part 5 table well formed.
3. New contradictions inside the edited text: read the first figure's caption (line 97), the paragraph at line 101, the source table (lines 103 to 121), the section 'What "3 loads + 2 stores of 16 B per cycle" means' (lines 122 to 132), the part 5 table and its two notes (lines 268 to 291), the first "Open items" item (lines 415 to 429), the "Words used here" entries "cycle", "mesh clock, mesh cycle", "flit, data flit, data channel", "compiled loop, asm loop", "Arm documents cited", and the first paragraph of "When the runs happened". Do any two of these places disagree on a number, a name of a run, a page, or a claim? Does any of them now disagree with an unchanged part of the report in a way that the record does not list (the record lists known ones in its sections 4 and 6)?
4. Re-run ${VDIR}/check_geometry.py on the report and render the figure with ${VDIR}/render.py into your scratch directory; open the PNG with the Read tool and say whether it still matches the description: two rows of six aligned boxes, captions "Measured" and "Spec" at the left.`,
  },
  {
    key: 'disassembly-claims',
    prompt: `TASK NAME: disassembly-claims
Try to REFUTE what the report and the record say about the compiled loops. Report text: the three paragraphs at lines 130 to 132 (they start "The measured L1 numbers are the pipeline limit.", "The read loop compiled from C reaches 66.8 GB/s", "The vector adds explain only part of the gap.") and the "Words used here" entry "compiled loop, asm loop". Record text: sections "Q6" and "Q7" of ${MD}.
Check against ${PROBE} (disassembly of k_read, k_write, k_copy, k_asmread), ${PRJ}/bench/bandwidth.c, the SOG PDF, and the raw results ${PRJ}/crb/results/20261030T193108Z/bandwidth.csv and ${PRJ}/crb/results/followup-20261030T194205Z/asm.csv.
a. Find the hot loop of k_read in the disassembly (the backward branch). Count per pass: loads and their width (ldp of q registers = two 16 B loads), vector adds, integer adds, compares, branches, bytes read per pass. Are the 8 vector accumulators separate registers kept in registers across passes (no load or store of the sums inside the loop)? Is "one vector add per 16 B load" right? Is "2 integer adds and one compare-and-branch" right?
b. Arithmetic: 66.8 GB/s at 2.8 GHz in B per cycle; cycles per pass of 128 B; "1.5 loads of 16 B per cycle"; "2.98 vector results per cycle"; "25 % below" 89.6 GB/s; the two predictions for a loop with loads and adds in a 3:2 ratio (80.6 GB/s under a limit of 3 vector results per cycle; 134.4 GB/s if only the two vector pipelines limit). Use the raw value 66.76 GB/s.
c. SOG: vector ADD throughput and latency (Table 3-15, page 26); LDP of q registers (Table 3-13); the number of FP/ASIMD pipelines (Table 2-1, page 13); dispatch constraints (section 4.1, page 55). Does any documented limit explain 3 vector results per cycle, or contradict the new hypothesis "loads and adds that write vector registers share a limit of 3 per cycle"? Is there another explanation that the text should name (for example a front-end or rename limit, the loop-carried add latency of 2 cycles with 8 chains, or load-to-use latency)? Compute the bound that each gives.
d. Provenance: the report says the binary that was read is the build of 2026-11-02 from the current source file, and that the 66.8 GB/s was measured on 2026-10-30 with an earlier build of which no copy was kept. Check the dates and sha256 values in the probe file against ${PRJ}/bench/bandwidth.c (sha256sum) and the result folders. Is there any evidence about whether k_read changed between 2026-10-30 and 2026-11-02 (look at ${PRJ}/bench/README.md, file dates, result logs)?
e. The record's by-product claim: the compiled write and copy loops are SVE loops that move one 16 B vector per pass, and their measured rates are 0.98 to 1.00 loop passes per cycle (44.0 to 44.8 GB/s write, 88.0 to 88.8 GB/s copy). Check against the disassembly of k_write and k_copy, the SVE vector length in the probe file, and bandwidth.csv.
f. The asm read loop: confirm from the disassembly of k_asmread that it is 8 ldp of q registers per 256 B and nothing else but add, cmp, branch.
g. Citations in line 130: "[bench/bandwidth.c:179 to 186 and 204 to 211]".`,
  },
  {
    key: 'pair-port-item',
    prompt: `TASK NAME: pair-port-item
Try to REFUTE the new statements about the pair port and the mesh cache. Report text: the source-table rows "Spec row, pair port: unknown" and "Spec row, mesh cache: unknown" (lines 118 and 119), the first "Open items" item with its nested list (lines 415 to 429), the "Words used here" entries "mesh clock, mesh cycle" and "flit, data flit, data channel" (lines 440 and 441), and the note that starts "Corrected on 2026-11-11" (line 289). Record text: sections "Q2", "D1" and "D2" of ${MD}.
Recompute every number from the raw files with your own code:
a. ${PRJ}/crb/results/sudo-20261102T211150Z/writepath.csv (event names contain commas; use long run minus short run; no idle subtraction for cycle counters): the mesh clock range over the dtc_cycles rows; data flits per line and per mesh cycle at the port for case r8M-c2 ("1.653 data flits per line", "0.83 of its lines cross the port", "0.92 data flits per mesh cycle", "58.7 GB/s", "71 GB/s"); bus writes per line for case w8M-c2 ("1.52 bus writes of 32 B per line") and per mesh cycle for case w1G-c2 ("0.98 bus writes of 32 B per mesh cycle"). Which perf event is the bus write count, and is one bus write really one 32 B data flit (compare bus reads and port flits in case r8M-c2)?
b. ${PRJ}/crb/results/followup-20261030T194205Z/pair.csv and asm.csv: "Measured: 77.5 to 78.5 GB/s" for two partner readers; "Measured: 82 GB/s" for two partner writers at 8 MiB; "One writer reaches 63.0 GB/s. Two partner writers together reach 63.2 GB/s" at 1 GiB. Which CPUs ran in each row (read the context lines and bench/bandwidth.c for how threads map to the CPU list)? Are CPUs 0 and 1 partners in the report's sense?
c. The predictions: 64 GB/s on the port allows 77 GB/s for two partner readers and 84 GB/s for two partner writers at 8 MiB. Check the arithmetic and whether the conversion is sound. Is there any measured pair value in crb/results that the hypothesis cannot explain (look for rows where two partner cores exceed what 64 GB/s on the port allows, including DRAM reads: asm read with 2 threads at 1 GiB gives 56.66 GB/s; how many data flits per mesh cycle is that if every line crosses the port, and does the report's claim about eviction traffic in the other direction matter)?
d. The probe-based claim: "The Linux mesh driver on CRB lists events for a second response channel (rsp2) and none for a second data channel (dat2)", and "The driver hides the dat2 events when the mesh reports fewer than two data channels". Check ${PROBE} and the driver source (function arm_cmn_event_attr_is_visible and where dat_vc_num is read). Does it follow that "CRB's mesh has one data channel in each direction"? Does the conclusion also hold for the device port of the cores, or only for mesh links? What does the TRM say about the meaning of the register field (pages 820 to 823 and 1656)?
e. TRM citations: Table A-2 page 2120 (flit data width), page 280 (data array timing: "2 or 3 mesh cycles for one access, and one access at a time"), page 1016 (field data_ram_latency of cmn_hns_unit_info), section 7.2.1 page 386 (what clocks the cycle counter). Is "That would bound one slice at 64 or 42.7 GB/s (est., if one access moves one 64 B line)" arithmetic right?
f. SVK user guide citations: page 10 (same value for the interconnect clock, twelve memory interfaces) and page 7 (frequency scaling for the mesh). The report must not quote the guide's sentences (the guide is marked Confidential); check that it only paraphrases.
g. Wording: is the 64 GB/s statement marked as a hypothesis everywhere in the report? Does the sentence "One flit per cycle on one channel is the rule of Arm's CHI link protocol. The CMN manual does not state it in one sentence." claim more than can be supported from local files? Is the "If it holds" list item fair to the two older statements it names (find them in the report and quote them)?`,
  },
  {
    key: 'record-audit',
    prompt: `TASK NAME: record-audit
Audit the update record ${MD} against the report, the backup and the author's request. The request (verbatim, from the author's Notion page) is:

"Update ./crb-memory-hierarchy.html:
- Section 'The hierarchy at a glance', add a row of boxes under the following and align the boxes between rows. The new row lists the potential throughput of each individual h/w if applicable. E.g. The 1st box has the read throughput and write throughput of core, write the calculations like 'read: 3 load * 2.8GHz * 16B = 134.4 GB/s', 'write: 2 store * 2.8GHz * 16B = 89.6 GB/s'. If L1 and L2 have no way to calculate, then say, 'measured above'. For DRAM box, '640 GB/s theoretical peak'. We do not know how to calculate mesh cache because we do not know mesh clock, so just say 'unknown' for the mesh cache box at new row, same to pair port box. Discuss with me if you disagree with any of my suggestion.
  Remove '1 core' from L1 and L2 boxes. Remove '640 GB/s theoretical peak' from the current DRAM box since it is added to the new box.
  Add a row caption at the leftmost of row, the current row is 'Measured', the new row 'Spec'.
- Other updates: change 'The 8 reserved cores (120-127) were never used, so whole-chip numbers are for 120 of 128 cores. Per-core numbers do not depend on this.' to 'The 8 reserved cores (120-127) were never used - this is a simple operation agreement between Jeremy and me, there is no technical reason - and the whole-chip tests used 120 of 128 cores.'
- what does this mean, 'it was still rising at the footprint limit' ? Please suggest simpler alternatives
- CRB doc and tools are downloaded to ~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit, can you find out CMN mesh clock frequency at the doc, or find out how to check the system?
- The following is an unrelated calculation, it is not a proof the core's clock is 2.8GHz. Or maybe I do not get it what it is: 'Consistent with the measured cycles: 1.43 ns x 2.8 GHz = 4.0.'
- Is 'mesh cache' the term used in ARM doc? Colleagues commented to use common term, and suggested 'SLC'. Please investigate and reply
- Change 'Measured (fresh chase, the average over all slices). The root run gives the range behind it: 19 to 44 ns by slice.' to 'Measured (averaged over all slices). Range: 19 to 44 ns by slice'
Section 'What 3 loads + 2 stores of 16 B per cycle means':
- is that right the pipelines can be configured as 4 read plus 1 write?
- 'The compiled read loop reaches 66.8 GB/s,': what are differences between 'compiled read loop' and 'asm loop'? The 'compiled read' is compiled from C code? If so, please change 'compiled read loop' to 'read loop compiled from C'
- 'Hypothesis for the gap: the compiled loop also issues one vector add per load', you can inspect the de-assembled compiled code and save running test, correct?
Please document all your updates to ~/tmp/update-crb-memory-hierarchy.md."

Check:
1. Completeness: compute the diff of the backup and the report (python difflib over lines). Is every changed hunk covered by a row of section 2 or section 5 of the record? Is any change described that is not in the diff? Is every item of the request answered or done (the record must say where)?
2. Line numbers: every line number the record gives for the report (sections 2, 3, 4, 5 and 6) must point at the text it names in the current report. List every wrong one with the right value.
3. Numbers: every number in the record must equal the report, the raw files or the cited document. Spot-check at least: the two sha256 values and line counts in section 1 (sha256sum the files); the box widths in section 2; 899 and 1,349 GB/s; 1.9995 to 2.0000 GHz; 2.7998 to 2.8001; 2,797,265 kHz; the term counts in Q4 (count "SLC" as a whole word and "mesh cache" in the CMN S3 TRM with PyMuPDF); 86 occurrences of "mesh cache" in the backup (count "mesh cache" and "mesh-cache", case-insensitive); the ASCT table in D7 against ${KIT}/tools/asct/reports/asct_run_output_a0_numa2_ddr_7200.txt; "19 hunks"; the verification table.
4. The references [Ref1] to [Ref20]: does each cited file exist, and does each cited line or page hold what the record says? Are any reference numbers used in the text and missing in the list, or the reverse?
5. Plain English (the rules in your instructions): the "Short version" must have at most three sentences that a newcomer can follow; terms defined at first use or in "Words used here"; one claim per sentence; numbers with units; no idioms. List violations with a corrected sentence. Do not ask for the removal of facts.
6. Honesty: does the record claim any check that the files do not support? Does it state plainly what was not done? Is anything important missing that the author must know before sharing the report (for example changes of meaning in the report that the record plays down)?`,
  },
]

phase('Check')
const results = await parallel(TASKS.map(t => () =>
  agent(CTX + '\n' + t.prompt, { label: t.key, phase: 'Check', schema: SCHEMA })
    .then(r => ({ key: t.key, result: r }))
))
const ok = results.filter(Boolean).filter(r => r.result)
const counts = {}
ok.forEach(r => (r.result.findings || []).forEach(f => { counts[f.severity] = (counts[f.severity] || 0) + 1 }))
log(ok.length + ' of ' + TASKS.length + ' checkers returned; findings by severity: ' + JSON.stringify(counts))
return { returned: ok.map(r => r.key), missing: TASKS.map(t => t.key).filter(k => !ok.some(r => r.key === k)), counts, results: ok }
