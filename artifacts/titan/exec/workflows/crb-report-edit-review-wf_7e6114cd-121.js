export const meta = {
  name: 'crb-report-edit-review',
  description: 'Adversarial review of the edited CRB memory-hierarchy report: request compliance, fact checks against raw data and Arm documents, figure audit, plain-English check, consistency sweep',
  phases: [
    { title: 'Review', detail: '6 independent reviewers, each with one lens, each told to find defects' },
  ],
}

const PRJ = '/home/jhan/workspace/titan/cache-perf'
const REPORT = PRJ + '/crb/crb-memory-hierarchy.html'
const BACKUP = PRJ + '/crb/tmp/crb-memory-hierarchy.before-spec-row.html'
const VDIR = PRJ + '/crb/tmp/agent-scratch/spec-row-2026-11-11'
const KIT = '/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit'
const SP = args.scratch

const REQUEST = `THE AUTHOR'S REQUEST (verbatim from the author's Notion page, 2026-11-11)

Update ./crb-memory-hierarchy.html:

- Section "The hierarchy at a glance", add a row of boxes under the following and align the boxes between rows. The new row lists the potential throughput of each individual h/w if applicable. E.g. The 1st box has the read throughput and write throughput of core, write the calculations like "read: 3 load * 2.8GHz * 16B = 134.4 GB/s", "write: 2 store * 2.8GHz * 16B = 89.6 GB/s". If L1 and L2 have no way to calculate, then say, "measured above". For DRAM box, "640 GB/s theoretical peak". We do not know how to calculate mesh cache because we do not know mesh clock, so just say "unknown" for the mesh cache box at new row, same to pair port box. Discuss with me if you disagree with any of my suggestion.
  [a screenshot of the old one-row figure was attached here]
  Remove "1 core" from L1 and L2 boxes. Remove "640 GB/s theoretical peak" from the current DRAM box since it is added to the new box.
  Add a row caption at the leftmost of row, the current row is "Measured", the new row "Spec".
- Other updates
  Change the following:
    "The 8 reserved cores (120-127) were never used, so whole-chip numbers are for 120 of 128 cores. Per-core numbers do not depend on this."
  to
    "The 8 reserved cores (120-127) were never used - this is a simple operation agreement between Jeremy and me, there is no technical reason - and the whole-chip tests used 120 of 128 cores."
- what does this mean, "it was still rising at the footprint limit" ? Please suggest simpler alternatives
- CRB doc and tools are downloaded to ~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit, can you find out CMN mesh clock frequency at the doc, or find out how to check the system?
- The following is an unrelated calculation, it is not a proof the core's clock is 2.8GHz. Or maybe I do not get it what it is: "Consistent with the measured cycles: 1.43 ns x 2.8 GHz = 4.0."
- Is "mesh cache" the term used in ARM doc? Colleagues commented to use common term, and suggested "SLC". Please investigate and reply
- Change "Measured (fresh chase, the average over all slices). The root run gives the range behind it: 19 to 44 ns by slice." to "Measured (averaged over all slices). Range: 19 to 44 ns by slice"
Section 'What "3 loads + 2 stores of 16 B per cycle" means':
- is that right the pipelines can be configured as 4 read plus 1 write?
- "The compiled read loop reaches 66.8 GB/s,": what are differences between "compiled read loop" and "asm loop"? The "compiled read" is compiled from C code? If so, please change "compiled read loop" to "read loop compiled from C"
- "Hypothesis for the gap: the compiled loop also issues one vector add per load", you can inspect the de-assembled compiled code and save running test, correct?
Please document all your updates to ~/tmp/update-crb-memory-hierarchy.md. [then a review loop with another agent follows]`

const CTX = `You are one of 6 independent reviewers of an edited HTML report. Your job is to FIND DEFECTS, not to praise. Assume the editor made mistakes. Your structured output is raw data for the editor.

FILES
- Edited report: ${REPORT}
- The report before the edit (backup): ${BACKUP}
- Get the exact change set with: diff <(python3 -c "print(open('${BACKUP}').read())") <(python3 -c "print(open('${REPORT}').read())") or with python difflib. Lines are long: print only the changed lines and cut or wrap them.
- Project: ${PRJ} (bench/ = benchmark source, crb/results/ = raw results, crb/refs/ = three Arm PDFs: CMN S3 TRM 107858, CMN-700 TRM, Neoverse V3AE Software Optimization Guide 110075, called SOG).
- Vendor kit: ${KIT} (read-only). The user guide cited is ${KIT}/svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf .
- Helper scripts of the editor, which you may read and run but must not trust blindly: ${VDIR}/check_geometry.py , ${VDIR}/render.py , ${VDIR}/mesh_clock.py . Renders: ${VDIR}/figure-before.png and ${VDIR}/figure-after.png (open them with the Read tool).
- Your scratch directory: ${SP}/review/<your task name>/ (mkdir -p). Write nothing anywhere else.

RULES
- READ-ONLY: do not edit the report, the backup or any project file. Do not contact the measured machine (CRB, 192.168.x.x): no ssh, no ping.
- Tools: python3 with PyMuPDF (import fitz) and pypdf for PDFs; no pdftotext; no browser; cairosvg and PIL are installed.
- One part of the edit is NOT finished and must be ignored: the paragraph that starts "The measured L1 numbers are the pipeline limit." (it still says "The compiled read loop reaches 66.8 GB/s" and holds a hypothesis about vector adds) and the "Words used here" entry "compiled loop, asm loop". They wait for a disassembly result. Do not report them.
- Two texts are the author's own wording and must stay verbatim even if they break style rules: the list item that starts "The 8 reserved cores (120-127) were never used - this is a simple operation agreement" and the table cell "Measured (averaged over all slices). Range: 19 to 44 ns by slice." (the editor added only the final full stop). Report a problem with them only if it is a factual error.
- Every finding needs evidence: file path plus line or page, and a verbatim quote or a computed value. Say how you checked. If you could not check something, list it under not_checked. Do not report style preferences as defects unless your task is the style check.
- Severity: "blocker" = a statement in the edited text is false or the request was not followed without a stated reason; "major" = misleading, unsupported, or a regression (something that worked before is now broken); "minor" = small inaccuracy, citation slip, wording; "note" = observation or suggestion.

${REQUEST}

WHAT THE EDITOR DECIDED (so you can check it, not so you agree with it)
- The mesh clock turned out to be known: the editor says the project's own raw data of 2026-11-02 show 2.0 GHz and that an Arm user guide states 2.0 GHz. The editor still wrote "unknown" in the two Spec boxes (pair port, mesh cache) as the author asked, and put a one-flit-per-cycle calculation (64 GB/s) into the source table and the open items as a labelled hypothesis.
- The editor replaced the sentence "Consistent with the measured cycles: 1.43 ns x 2.8 GHz = 4.0." by a cycle-counter measurement.
- The editor changed "five pipelines" to "four" and added a paragraph on the possible load and store mixes.
- The editor corrected the caveat about the mesh cycle counter (dtc_cycles), added an open item, two "Words used here" entries (mesh clock, flit), a citation of the SVK user guide, and one sentence to the sub-header.
- The editor did NOT rename "mesh cache" (the author asked only to investigate).
`

const SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', description: 'Two or three plain sentences: the overall result of your review' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'] },
          location: { type: 'string', description: 'Report line number (current file) or figure element' },
          problem: { type: 'string' },
          evidence: { type: 'string', description: 'File path plus line or page with a quote, or the computed value and how it was computed' },
          fix: { type: 'string', description: 'The exact corrected wording or markup, ready to paste' },
        },
        required: ['id', 'severity', 'location', 'problem', 'evidence', 'fix'],
      },
    },
    confirmed: { type: 'array', items: { type: 'string' }, description: 'Claims or items you tried to break and could not, one line each with how you checked' },
    not_checked: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'findings', 'confirmed', 'not_checked'],
}

const TASKS = [
  {
    key: 'compliance-diff',
    prompt: `TASK NAME: compliance-diff
Compare the edited report with the backup and with the author's request.
1. List every changed hunk. For each: which request item it serves, or "not requested". For a change that was not requested, judge whether it is a necessary consequence of a requested change, a correction of a factual error tied to one of the author's questions, or scope creep.
2. For every request item that asks for a change to the report: is it done exactly? Check the literal strings (for example that ", 1 core" is gone from the L1 and L2 boxes of the first row and nothing else in those boxes changed; that "640 GB/s theoretical peak" left the first-row DRAM box; that the row captions read "Measured" and "Spec" and sit left of the first box; that the Spec row has six boxes whose texts match the request; that the two verbatim texts match the request character by character apart from the final full stop of the table cell).
3. Regressions: are all element ids, href anchors and the table of contents unchanged? Are the two <script> blocks byte-identical to the backup? Is the changed HTML well formed (every opened tag closed, attribute quotes balanced, entities correct)? Is the <marker id="ar"> still defined exactly once, and is it still referenced by the first figure and by the script that draws the figure with id "ways"?
4. Anything in the first figure, its caption or the source table under it that now contradicts another part of the same section.
5. Typos, doubled words, broken sentences in the changed text.`,
  },
  {
    key: 'refute-mesh-clock',
    prompt: `TASK NAME: refute-mesh-clock
Try to REFUTE every claim about the mesh clock, flits and the pair port that the edit added. They are in: the sub-header (line 49), the source table row "Spec row, pair port and mesh cache: unknown", the note that starts "Caveats. Corrected on 2026-11-11", the first item of "Open items", and the "Words used here" entries "mesh clock, mesh cycle" and "flit". Find the lines with grep.
Check each of these against primary sources, with your own code (do not reuse ${VDIR}/mesh_clock.py; you may compare with it afterwards):
a. "Its 78 raw rows in this run give 1.9995 to 2.0000 GHz, on both meshes, idle and loaded": parse ${PRJ}/crb/results/sudo-20261102T211150Z/writepath.csv yourself. Event names contain commas, so do not split rows on commas blindly. How many dtc_cycles rows, which meshes, which cases, what range? Is the perf "percent running" column 100 for all?
b. "That number was what remained after the analysis script subtracted the idle run from the cycle count [bench/analyze_writepath.py, line 55]": read ${PRJ}/bench/analyze_writepath.py. Is line 55 the subtraction? Reproduce a value near 6,500 per second by hand from the raw rows.
c. "The mesh clock is 2.0 GHz ... so one mesh cycle is 0.5 ns", "It is a different clock from the 2.8 GHz core clock": is the counter really a clock of the mesh? Check the CMN S3 TRM (section 7.2.1 Cycle counter, about page 386) and the Linux driver source (extract drivers/perf/arm-cmn.c from ${KIT}/svk-release/linux/arm-agi-cpu-linux-7.1.3-v0.9.0-source.tar.gz into your scratch directory with tar --wildcards). Could the counter be gated, scaled or multiplexed in a way that makes 2.0 GHz wrong? Does anything in the data suggest the mesh clock changes under load?
d. 'Arm's user guide for CRB firmware 0.9.0 states "Interconnect clocked at 2.0 GHz" [SVK user guide, page 10]': open the PDF, check the exact words, the page, the firmware version the guide is written for, and whether the report says clearly enough that CRB ran firmware 0.7.2 when measured (check ${PRJ}/crb/inspection-record-2026-10-30.md for the firmware version).
e. "a data flit ... holds 32 B [CMN S3 TRM, Table A-2 page 2120]" and "field dat_vc_num_p of por_mxp_p0-5_info_1 [CMN S3 TRM, page 1656]": check both pages and the wording. Is "A data flit holds 32 B, so a 64 B line needs two" right?
f. "One reader on CPU 2 (71 GB/s at 8 MiB) drove its core port at 0.92 data flits per mesh cycle, which is 58.7 GB/s on the port [writepath.csv, case r8M-c2]" and "None of the 30 data-flit counts of that run, on the port and on the four mesh links, exceeded one flit per mesh cycle": recompute. Is "the four mesh links" right (which links were counted)? Is 30 right? Is the event really flits delivered to the core port?
g. The hypothesis "a core port passes at most one data flit per mesh cycle in each direction, which is 64 GB/s": is it worded as a hypothesis everywhere it appears? Is the proposed confirming test sound? Is there data in ${PRJ}/crb/results that already contradicts it (for example a run where one port must have carried more than 64 GB/s)? Look at the pair runs in crb/results/followup-20261030T194205Z (pair.csv, asm.csv) and at the write runs of part 5.
h. Anything else in those added texts that is unsupported or overstated.`,
  },
  {
    key: 'refute-core-pipeline',
    prompt: `TASK NAME: refute-core-pipeline
Try to REFUTE every claim the edit added about the core. They are in: the source table rows "Core, 2.8 GHz fixed", "Spec row, Core: read 134.4 GB/s, write 89.6 GB/s", "Spec row, L1 and L2: measured above", "Spec row, DRAM: 640 GB/s theoretical peak"; the two paragraphs at the start of the section 'What "3 loads + 2 stores of 16 B per cycle" means' (the first starts "The core has four pipelines that start loads and stores", the second starts "It follows that one cycle holds at most"); the changed citation "[SOG, Table 3-13 page 23 and Table 3-14 pages 24 to 25]"; and the Spec-row Core box of the first figure ("read: 3 loads x 2.8 GHz x 16 B = 134.4 GB/s", "write: 2 stores x 2.8 GHz x 16 B = 89.6 GB/s") and DRAM box ("10 channels x 8000 MT/s x 8 B per transfer = 640 GB/s theoretical peak").
Check against the SOG PDF (${PRJ}/crb/refs/arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf), the raw results and the inspection record:
a. Pipeline count and names (Figure 2-1 page 12, Table 2-1 page 13), "each pipeline accepts one operation per cycle" (page 11), the two possible mixes, "It never holds 4 loads + 1 store", "These roles are fixed: the guide describes no setting that changes them", "The guide draws two more memory pipelines, Store data 0 and Store data 1. They carry the data of a store and do not start one". Is any of this wrong or too strong? For example: what carries the data of a vector store according to Table 3-14, and does the new text mislead about that?
b. "The asm copy loop confirms the second mix: it measured 178.4 GB/s, and 2 loads + 2 stores of 16 B per cycle is 179.2 GB/s": check the raw value in ${PRJ}/crb/results/followup-20261030T194205Z/asm.csv and the arithmetic. Does a copy at that rate really prove 2 loads + 2 stores in one cycle?
c. Page numbers of every SOG citation in the changed text.
d. "cpufreq reports 2,800,000 kHz on all 128 cores, with the performance governor and frequency boost off" (${PRJ}/crb/inspection-record-2026-10-30.md) and "in the root run of 2026-11-02 the cycle counter of CPU 2 advanced 2.80000 x 10^9 per second (5,039,939,572 cycles in 1.799979528 s, long run minus short run) [results/sudo-20261102T211150Z/writepath.csv]": recompute from the raw rows yourself (event armv8_pmuv3_0/cycles/, case w8M-c2). Was the counter bound to CPU 2? Does it count all modes? Is "root run of 2026-11-02" the right name for that result folder (the report uses "root run" for results/sudo-20261102T054936Z and "part 5" for sudo-20261102T211150Z: check how the report names them elsewhere and whether the new wording confuses the two)?
e. "Arm's guide states no bandwidth for the L1 or the L2 cache [SOG, searched in full]": search the PDF.
f. The DRAM arithmetic and the phrase "8 B per transfer": is it right for DDR5 (64 data bits per transfer per channel)? Check the DIMM facts in ${PRJ}/crb/results/dmidecode-t17-2026-10-30.txt.
g. "The measured L1 values are 132.7 and 89.5 GB/s": raw values.
h. The old sentence that was removed: "Consistent with the measured cycles: 1.43 ns x 2.8 GHz = 4.0." Is anything lost that the report needs? Is the replacement a real measurement of the clock?`,
  },
  {
    key: 'figure-audit',
    prompt: `TASK NAME: figure-audit
Audit the first figure of the report (the <svg viewBox="0 0 924 234" role="img"> right after the heading "The hierarchy at a glance") against the old figure in the backup and the request.
1. Open ${VDIR}/figure-before.png and ${VDIR}/figure-after.png with the Read tool. Also render the figure yourself from the report with cairosvg into your scratch directory (fonts are in ${VDIR}/fonts; see ${VDIR}/render.py for how the font is set up) and look at your own render. Report anything that looks wrong: overlap, clipping, uneven spacing, misaligned captions, inconsistent text sizes, low contrast, a box that looks empty or unbalanced.
2. Geometry by numbers, with your own code (you may compare with ${VDIR}/check_geometry.py afterwards): for every rect, the text lines inside it, their widths in IBM Plex Sans at the stated size and weight, and the left and right padding. Do the two rows share x and width column by column? Are gaps equal? Do the row captions clear the first box? Does anything leave the viewBox? Are the arrows of the first row still between the boxes and at the vertical centre of the row?
3. Fallback fonts: the page falls back to "Segoe UI", Helvetica, Arial when IBM Plex Sans does not load. Estimate whether the tightest labels still fit with a font that is about 5 % wider. Name the labels at risk.
4. Content: compare every text of the first row with the backup figure. Only two things may differ: ", 1 core" removed from the L1 and L2 boxes, and "640 GB/s theoretical peak" removed from the DRAM box. Check the Spec row texts against the request and against the arithmetic (3 x 2.8e9 x 16 = 134.4e9; 2 x 2.8e9 x 16 = 89.6e9; 10 x 8000e6 x 8 = 640e9).
5. Markup: is the SVG well formed? Does each <text> carry what it needs (no reliance on attributes that an SVG renderer could ignore)? Is the aria-label accurate and not too long? Are font sizes consistent between the two rows, and is the choice of 12 px for the Spec row calculations and 12.5 px elsewhere a visible inconsistency?
6. The page scales the figure to the column width of 880 px, and the viewBox is now 924 wide. What is the effective text size, and how does it compare with the other figures of the report (they use an 880-wide viewBox)? Is that a problem?
7. Does the figure caption (the <figcaption> under it) explain everything a reader needs for the new row, and is every sentence of it true? Check "the next step, 48 threads of 3 MiB each, needs 144 MiB and does not fit in the 128 MiB cache" and "The total was still increasing at 40 threads" against ${PRJ}/crb/results/slc-20261030T194835Z/slc.csv.`,
  },
  {
    key: 'plain-english',
    prompt: `TASK NAME: plain-english
Check every sentence that the edit added or changed (get them from the diff; ignore the unfinished paragraph and respect the two verbatim texts) against the plain-English rules in your instructions (the plain-english skill: no idioms or uncommon words, one claim per sentence, short sentences, numbers with units and meaning, every code name, acronym and metric defined at first use or in the report's "Words used here" list, citations after the sentence).
For each violation give the exact phrase, the rule number, and a corrected sentence that keeps the meaning and every number. Also check:
- Terms used by the new text that the report defines nowhere before their first use or in "Words used here": for example "Spec row", "root run", "part 5", "mesh cycle counter", "dtc_cycles", "data flit", "data channels", "core port", "idle run", "long run minus short run", "SVK user guide", "firmware 0.9.0". Say for each where it is defined, or that it is not.
- Whether the figure caption is too long for a caption, and how to shorten it without losing a fact.
- Whether a reader who has never seen the project can understand the source-table row "Spec row, pair port and mesh cache: unknown" and the first "Open items" bullet on first read. Rewrite them if not. Keep every fact and every citation.
Do not change facts or numbers. Do not flag the report's existing style where the edit did not touch it.`,
  },
  {
    key: 'consistency-sweep',
    prompt: `TASK NAME: consistency-sweep
Read the WHOLE edited report (all prose, tables, captions, and the label strings inside the two <script> blocks) and find statements that the edit has made inconsistent, or that contradict the new facts. New facts stated by the edit: the mesh clock is 2.0 GHz (one mesh cycle is 0.5 ns), measured by the mesh cycle counter; the earlier "about 6,500 per second" was an artifact of idle subtraction in bench/analyze_writepath.py; a data flit holds 32 B; the core has four pipelines that start loads and stores; the first figure has a Measured row and a Spec row; the first-row L1 and L2 boxes no longer say "1 core" and the first-row DRAM box no longer says "640 GB/s theoretical peak".
Look in particular for:
1. Other places that still treat the mesh clock as unknown, or that use the wrong cycle counts: for example the table in the section "Where one writer's 73 GB/s limit sits" (cycles per line, the sentence "the stall counter does not see the wait"), the sentence "That is about 28 B per core cycle", and any "per cycle" value that came from the analysis script. For each, say whether the raw data in ${PRJ}/crb/results/sudo-20261102T211150Z/writepath.csv support the printed value (recompute it) and whether the new facts change the conclusion drawn there.
2. Conclusions that the 2.0 GHz clock puts in doubt: for example "The single-writer limit is inside the core", "neither the port, the mesh nor the memory side caps one core", "For DRAM streams the port is not the limit". Compute from the raw rows how many data flits per mesh cycle the writers sent, and say which sentences need a caveat. Mark these as pre-existing text that the edit did not touch.
3. References to the first figure elsewhere in the report (for example "The 29 to 30 ns mesh cache latency in the hierarchy figure", "Labels marked * are explained in the next three sections", the table of contents, the sentence "The figure mixes three kinds of numbers") that the new figure makes wrong or incomplete.
4. Statements about the number of pipelines, loads and stores elsewhere (the figure with id "pipes" drawn by script, its caption, the takeaways) that disagree with the new paragraphs.
5. The phrases "still rising" and "mesh-served part was still rising": the edit reworded only the first-figure caption. List the other occurrences and say whether the raw data (${PRJ}/crb/results/slc-20261030T194835Z/slc.csv and crb/results/uncore2-20261030T203752Z) support each.
6. Any place where "Words used here" now disagrees with the body.
Classify each finding: "caused by the edit" (the edit created or exposed a contradiction with its own new text: severity major or blocker) or "pre-existing, not touched" (severity note or minor, with the exact corrected wording so the editor can offer it to the author).`,
  },
]

phase('Review')
log('Launching ' + TASKS.length + ' reviewers')
const results = await parallel(TASKS.map(t => () =>
  agent(CTX + '\n' + t.prompt, { label: t.key, phase: 'Review', schema: SCHEMA })
    .then(r => ({ key: t.key, result: r }))
))
const ok = results.filter(Boolean).filter(r => r.result)
const counts = {}
ok.forEach(r => (r.result.findings || []).forEach(f => { counts[f.severity] = (counts[f.severity] || 0) + 1 }))
log(ok.length + ' of ' + TASKS.length + ' reviewers returned; findings by severity: ' + JSON.stringify(counts))
return { returned: ok.map(r => r.key), missing: TASKS.map(t => t.key).filter(k => !ok.some(r => r.key === k)), counts, results: ok }
