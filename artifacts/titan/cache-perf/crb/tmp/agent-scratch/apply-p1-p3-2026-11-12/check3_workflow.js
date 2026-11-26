export const meta = {
  name: 'check-spec-box-and-p1-p3',
  description: 'Check the applied Spec-box change and the applied texts P1 to P3 in the CRB report and brief, then try to refute every finding',
  phases: [
    { title: 'Check', detail: 'four checkers: numbers (reads), numbers (writes and brief), claims, language and render' },
    { title: 'Refute', detail: 'one second checker per first checker tries to refute each finding' },
  ],
}

const CRB = '/home/jhan/workspace/titan/cache-perf/crb'
const REPORT = `${CRB}/crb-memory-hierarchy.html`
const BEFORE = `${CRB}/tmp/agent-scratch/apply-p1-p3-2026-11-12/report.before.html`
const EVID = `${CRB}/tmp/agent-scratch/apply-p1-p3-2026-11-12`
const RECORD_BEFORE = `${EVID}/record.before.md`
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/apply_p/agents3'
const CHANGED = (args && args.changed_lines) || 'see the diff'

const COMMON = `
You are a read-only checker. Do NOT edit any file under /home/jhan/workspace or /home/jhan/tmp. Do not log in to any other machine and do not use the network. Write scratch files only under ${SCRATCH}/<your label>/ (create it). Never run python with py_compile inside ${CRB}.

Context. ${REPORT} is an HTML report (978 physical lines, many of them several thousand characters long) about memory-hierarchy measurements on a server called CRB. Today the author asked for three changes, and they are now applied:
 (1) the entry "flit" in "Words used here" (report line 451) says what the word stands for; entries for "credit stall, data stall, back-pressure" and "write in flight" were added on the same line; the entry "pair port" (line 462) was rewritten and now names "partner cores";
 (2) the Spec box of the pair port in the first figure says "estimated 64 GB/s" (it said "unknown"), and the section "Where each number in the figure comes from" explains it (lines 77, 92, 97, 101, 110, 118, 121, 416);
 (3) three older statements were replaced by the texts P1, P2 and P3 that the author approved. The approved texts are in ${RECORD_BEFORE}, section 10.6 (lines 624 to 650). In the report they are now structured as tables and lists: P2 at line 214, P3 at line 289, P1 at line 380. Line 437 (an open item) was rewritten.
 (4) a sweep found other sentences that still stated one of the replaced statements or that the new texts contradict. These were changed too: the Short version (line 52), lines 179, 206 and 213, the sentence on the limit at line 266, three cells of the table of part 5 (lines 275, 276, 278), lines 343, 377 and 379, the open item at line 425 (a fifth run), and the data of the pair chart in the script (line 587, two more rows).
 The two-page brief ${CRB}/crb-memory-hierarchy-brief.html changed in its lines 39 and 40 (its generator ${CRB}/make-brief.py, lines 180 and 181). The brief texts differ from the texts that section 10.6 proposed in two points, on purpose: line 39 ends with "What limits a pair was not measured.", and line 40 gives "about 0.001 % of the mesh cycles" in place of the counts of credit-stall cycles and data flits, because the brief has no word list.
 Known and left unchanged on purpose (do not report these): the label "per 2 cores" in the Measured box of the pair port (line 85); "67 GB/s from the SLC" in the Short version (line 52); the shares 81 % and 19 % at lines 266, 330 and 959; "a few percent" at line 408; the heading at line 269; the row at line 333; the caption at line 367; and other files that repeat the old statements.
The state before these changes is ${BEFORE} (same line numbers: every edit stayed on its physical line). The changed report lines are: ${CHANGED}.

How to read. The Read tool may cut long lines. Print full lines with:
python3 -B -c "import sys;L=open(sys.argv[1],encoding='utf-8').read().split('\\n');a,b=int(sys.argv[2]),int(sys.argv[3]);[print('L%d: %s'%(n,L[n-1])) for n in range(a,b+1)]" ${REPORT} 214 214
List the changed lines with: python3 -B -c "import sys;A=open(sys.argv[1],encoding='utf-8').read().split('\\n');B=open(sys.argv[2],encoding='utf-8').read().split('\\n');print([i+1 for i,(a,b) in enumerate(zip(A,B)) if a!=b])" ${BEFORE} ${REPORT}

Raw data: ${CRB}/results/ . The loop rates of 2026-10-30 are in results/followup-20261030T194205Z/pair.csv and asm.csv and in results/20261030T193108Z/bandwidth.csv (helper: python3 -B ${EVID}/rates.py <csv> [filter], it prints the best rate of every case with its file line). The counter runs of 2026-11-02 are in results/sudo-20261102T211150Z/writepath.csv (part 5; helper: python3 -B ${CRB}/tmp/agent-scratch/spec-row-2026-11-11/port_counts.py) and results/sudo-20261102T054936Z/writebw.csv and results/sudo-20261102T040631Z/writebw.csv (part 3). Arm's manual: ${CRB}/refs/arm-cmn-s3-r2p3-trm-107858.pdf (read pages with PyMuPDF: python3 -B -c "import fitz; ..."; the printed page number is in the page footer and can differ from the PDF index). Arm's CHI specification: /home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf. The edit scripts are in ${EVID} (texts_p.py, apply_report_p.py, apply_brief_p.py and any later apply_*.py).

The author's writing rules (plain English) apply to every new sentence: short sentences, one claim per sentence, no semicolons, no idioms, every number with a unit, estimates marked "est.", every code name or abbreviation defined at first use or in "Words used here", and a claim must be tied to test data or a source, or be a labelled hypothesis with the test that would confirm it.

Report only real defects in text that this change wrote or revised, or contradictions between the new text and text that was left unchanged. Do not report older defects of untouched text unless the new text contradicts them. Do not invent findings. Give every finding: an id (your label plus a number), file, line, the exact quote (copied, not paraphrased), the problem, the severity ("major" = a wrong number, a wrong source, a claim that the data do not support, or a contradiction; "minor" = imprecise or incomplete; "note" = optional), a proposed replacement text, and your evidence (file and line of the raw data, or the page of the manual).
`

const FIND = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' }, quote: { type: 'string' },
          problem: { type: 'string' }, severity: { type: 'string', enum: ['major', 'minor', 'note'] },
          proposed_text: { type: 'string' }, evidence: { type: 'string' },
        },
        required: ['id', 'file', 'line', 'quote', 'problem', 'severity', 'proposed_text', 'evidence'],
      },
    },
    checked: { type: 'string', description: 'what was checked and found correct, in a few sentences with counts' },
  },
  required: ['findings', 'checked'],
}

const VERDICT = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'confirmed_in_part', 'rejected'] },
          reason: { type: 'string' }, corrected_text: { type: 'string' },
        },
        required: ['id', 'verdict', 'reason'],
      },
    },
    extra_findings: FIND.properties.findings,
    notes: { type: 'string' },
  },
  required: ['verdicts', 'extra_findings'],
}

const TASKS = [
  { label: 'numbers-reads', prompt: `Your task: numbers and sources of the Spec-box change and of the read statements. Lines: 49, 52, 77, 92, 97, 101, 110, 118, 121, 179, 206, 213, 214, 266, 343, 377, 379, 416, 425, 451, 462 and the chart data at script line 587. Recompute EVERY number of the new text from the raw files: each rate and range, each count of runs ("five runs", "three runs: two with the asm loop, one with the read loop compiled from C", "two runs"), each ratio (1.6 to 1.7 times, 0.82 to 0.83, 1.15 to 1.17, 1.9 to 2.0, \"differ by 8 %\"), each converted rate (64.1 to 64.9 GB/s, about 13.5 GB/s, 62.9 to 63.7 GB/s, 62.0 to 62.7 GB/s, and 71 GB/s at the loop against 58.7 GB/s on the port for one reader) and each share (83 %, 17 %, 81 %, 1.00 to 1.01, 0.97 to 0.98, 0.99). Check that a range belongs to exactly the runs that its sentence names, and that the loop (asm or compiled from C), the CPUs and the date of each run are as stated. Check every citation: the TRM pages (Table A-2 page 2120, Figure 2-25 page 89, pages 1679 and 391), the two quotations from the CHI specification (pages 32 and 518) and the file names in brackets. Check that each of the nine rows of the pair chart (script line 587) equals its run in pair.csv, that the caption at line 379 fits the chart (which CPUs are on which mesh: results/sudo-20261102T054936Z/core-positions.json), and that the rates of the new sentences at line 266 equal the chart data at script line 513 and the raw files.` },
  { label: 'numbers-writes', prompt: `Your task: numbers and sources of the write statements, of the statements at 1 GiB, and of the brief. Report lines 275, 276, 278, 289, 380, 437, brief lines 39 and 40 and generator lines 180 and 181. Recompute EVERY number from the raw files: 70.4 to 73.2 GB/s, 2 x 10^4 credit-stall cycles per second, 1.85 x 10^9 data flits per second, 1 x 10^4 data stalls per second, 1.68 x 10^9 and 1.96 x 10^9 bus writes per second, 81.4 to 82.3 GB/s, 228 to 230 GB/s, 1.52 bus writes per line, "about 62 to 63 GB/s at the port", the per-writer rates with two and four busy ports (\"between 60 and 61 GB/s\", \"57 GB/s on average (55 to 59 GB/s by writer)\"), the cells of lines 275 and 276 (2.00 and 1.52 bus writes per line, 0.000 stall cycles per line), 63.0, 62.9 and 63.2 GB/s, 0.98 bus writes per mesh cycle, 98 %, every cell of the table at line 380 (rates, differences, percentages), 54.9 GB/s, 2.3 GB/s (4 %), 113 GB/s, 50 GB/s, and the numbers of the brief (70 to 73, 82, 229, 63.0, 63.2, 78, 125 to 134, and \"about 0.001 % of the mesh cycles\": credit-stall cycles of the four links of CPU 2's crosspoint divided by the mesh cycles of the same runs). Check the loop, the CPUs and the date of each run, and that each range belongs to the runs that its sentence names. Check that the brief text and the report text agree.` },
  { label: 'claims', prompt: `Your task: the claims, not the arithmetic. Read all changed lines and the unchanged "Open items" (report lines 414 to 439). For each new or revised sentence ask: (a) does it state a maximum or a limit where the data show only an observed rate? (b) does it say or imply that a run reaches a capacity? (c) does it assign a number of one run (date, loop, CPUs, counter set) to another run? (d) is a derived or scaled value given without "est."? (e) is a hypothesis stated as a fact, or a fact as a hypothesis? (f) does the new text contradict a sentence that was left unchanged anywhere in the report (search the whole report for "pair", "port", "limit", "78", "80 GB/s", "64 GB/s", "inside the core", "outside the core", "unknown")? (g) content against the approved texts: compare line 214 with P2, line 289 with P3 and line 380 with P1 in ${RECORD_BEFORE} lines 624 to 650, sentence by sentence. List every sentence of P1, P2 or P3 whose content is missing in the report, and every statement of the report lines that is not in the approved text and is not a plain restatement (the table at line 380 has one new row, "Write, loop compiled from C ... 18.4 GB/s (41 %)", and line 289 gives per-writer rates in more detail: judge both). (h) is the figure consistent with its caption and table: Spec box "estimated 64 GB/s", Measured box "~80 GB/s per 2 cores", lines 97, 110, 118 and 121? Would a reader who sees 80 above 64 find the explanation, and is the explanation correct?` },
  { label: 'language-render', prompt: `Your task has two parts. Part 1, language: check every new or revised sentence of the changed report lines and of brief lines 39 and 40 against the plain-English rules above. Report a sentence with two claims, a semicolon, an idiom, a number without a unit, an estimate without "est.", or a term that is used before it is defined and is not in "Words used here" (report lines 446 to 468). Table heads are printed in capitals by the style sheet, so a unit in a table head is a defect. Part 2, structure and render: (a) the report still has 978 lines, its tags are balanced, no id occurs twice, every href="#..." has a target; (b) render the report with the local headless browser, offline. Read /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md for the exact command and the font setup, use your own --user-data-dir under your scratch folder, and take screenshots at window widths 1000 px and 390 px of: the first figure with its caption, the section "Where each number in the figure comes from", the section "Is the pair port how the SLC is reached?", the section "Where one writer's 73 GB/s limit sits", the section "The pair finding", "Open items" and "Words used here". Look at every screenshot. Report text that overlaps, a table or a line that leaves the page at 1000 px, a box of the figure whose text touches its border, and script errors (the page draws 19 figures by script: check with --dump-dom that each svg with an id holds elements). At 390 px the page already scrolled sideways by 80 px before this change (long file paths): report only if the new text makes it worse, with the measured widths before and after. (c) print the brief to PDF and confirm that it has exactly 2 pages and that page 2 starts with the heading "DRAM write bandwidth against writer placement". (d) run python3 -B ${CRB}/tmp/agent-scratch/spec-row-2026-11-11/check_geometry.py ${REPORT} 6 and report its result line.` },
]

phase('Check')
const results = await pipeline(
  TASKS,
  t => agent(COMMON + '\n' + t.prompt + `\nYour label: ${t.label}.`, { label: `check:${t.label}`, phase: 'Check', schema: FIND }),
  (found, t) => {
    if (!found) return { label: t.label, found: null, verdicts: null }
    return agent(COMMON + `\nYou are the SECOND checker. A first checker with the task below returned the findings that follow. Try to REFUTE each finding: open the raw file, the manual or the report line yourself and recompute. Give "rejected" when the finding is wrong or when you cannot reproduce it, "confirmed_in_part" when only a part holds or when the proposed text is itself wrong (then give a corrected text), "confirmed" only when you reproduced it. Then look for defects that the first checker missed in the same task, and return at most 8 of them as extra_findings (same rules, ids "${t.label}-X1" and so on).\n\nThe first checker's task: ${t.prompt}\n\nThe first checker's findings (JSON):\n${JSON.stringify(found.findings, null, 1)}\n\nWhat the first checker says it checked: ${found.checked}\nYour label: refute-${t.label}.`,
      { label: `refute:${t.label}`, phase: 'Refute', schema: VERDICT })
      .then(v => ({ label: t.label, found, verdicts: v }))
  }
)
return results.filter(Boolean)
