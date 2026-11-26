export const meta = {
  name: 'check-fixes-and-record',
  description: 'Check the fixes that followed the first check of the CRB report step, and the new section 11 of the update record; then try to refute every finding',
  phases: [
    { title: 'Check', detail: 'two checkers: the second-pass edits of report and brief, and section 11 of the record' },
    { title: 'Refute', detail: 'one second checker per first checker tries to refute each finding' },
  ],
}

const CRB = '/home/jhan/workspace/titan/cache-perf/crb'
const REPORT = `${CRB}/crb-memory-hierarchy.html`
const EVID = `${CRB}/tmp/agent-scratch/apply-p1-p3-2026-11-12`
const RECORD = '/home/jhan/tmp/update-crb-memory-hierarchy.md'
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/apply_p/agents4'

const COMMON = `
You are a read-only checker. Do NOT edit any file under /home/jhan/workspace or /home/jhan/tmp. Do not log in to any other machine and do not use the network. Write scratch files only under ${SCRATCH}/<your label>/ (create it). Never run python with py_compile inside ${CRB}.

Context. ${REPORT} is an HTML report (978 physical lines, many of them several thousand characters long) about memory-hierarchy measurements on a server called CRB. Today the author asked for three changes: (1) "flit" in "Words used here", (2) the Spec box of the pair port in the first figure says "estimated 64 GB/s", with an explanation in the section "Where each number in the figure comes from" (report line 121), (3) three older statements were replaced by the approved texts P1, P2 and P3 (now at report lines 380, 214 and 289). The work was done in two passes. Three states of the report exist, all with the same 978 line numbers:
 - ${EVID}/report.before.html : before this step;
 - ${EVID}/report.check3-state.html : after the first pass (34 edits on 28 lines). A first check ("check3": four checkers and four second checkers) read this state. Its findings and verdicts are in ${EVID}/check3_results.json;
 - ${REPORT} : now, after the second pass (37 edits on 15 lines, script ${EVID}/apply_report_p_fixes.py, each edit names the finding that it answers).
The two-page brief ${CRB}/crb-memory-hierarchy-brief.html is built by ${CRB}/make-brief.py. Its states: ${EVID}/brief.before.html and make-brief.before.py, ${EVID}/brief.check3-state.html and make-brief.check3-state.py, and the files now (second pass: ${EVID}/apply_brief_p_fixes.py).
The update record is ${RECORD} (900 lines). Its new section 11 (lines 677 to 859) describes this step. ${EVID}/record.before.md is the record before this step. The approved texts P1, P2, P3 are in ${EVID}/record.before.md lines 624 to 650.

How to read. The Read tool may cut long lines. Print full lines with:
python3 -B -c "import sys;L=open(sys.argv[1],encoding='utf-8').read().split('\\n');a,b=int(sys.argv[2]),int(sys.argv[3]);[print('L%d: %s'%(n,L[n-1])) for n in range(a,b+1)]" ${REPORT} 289 289
List the lines that differ between two states with: python3 -B -c "import sys;A=open(sys.argv[1],encoding='utf-8').read().split('\\n');B=open(sys.argv[2],encoding='utf-8').read().split('\\n');print([i+1 for i,(a,b) in enumerate(zip(A,B)) if a!=b])" <file1> <file2>

Raw data: ${CRB}/results/ . Loop rates of 2026-10-30: results/followup-20261030T194205Z/pair.csv and asm.csv, results/20261030T193108Z/bandwidth.csv (helper: python3 -B ${EVID}/rates.py <csv> [filter]). Counter runs of 2026-11-02: results/sudo-20261102T211150Z/writepath.csv (part 5; helper: python3 -B ${CRB}/tmp/agent-scratch/spec-row-2026-11-11/port_counts.py; each case has nine runs of 0.2 s and nine runs of 2 s, and a count is the 2 s run minus the 0.2 s run), results/sudo-20261102T054936Z/writebw.csv and results/sudo-20261102T040631Z/writebw.csv. Arm's manual: ${CRB}/refs/arm-cmn-s3-r2p3-trm-107858.pdf (PyMuPDF: python3 -B -c "import fitz; ..."). Arm's CHI specification: /home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf.

The author's writing rules (plain English) apply to every new sentence: short sentences, one claim per sentence, no semicolons, no idioms, every number with a unit, estimates marked "est.", every code name or abbreviation defined at first use or in a word list, and a claim must be tied to test data or a source, or be a labelled hypothesis with the test that would confirm it.

Known and left on purpose (do not report): the label "per 2 cores" in the Measured box of the pair port (report line 85); "67 GB/s from the SLC" in the Short version; the shares 81 % and 19 % at report lines 266, 330 and 959; "a few percent" at line 408; the heading at line 269; the row at line 333; the caption at line 367; the long third sentence of the Short version (line 52), which waits for the author's decision; other files that repeat the old statements.

Report only real defects. Do not invent findings. Give every finding: an id (your label plus a number), file, line, the exact quote (copied, not paraphrased), the problem, the severity ("major" = a wrong number, a wrong source, a claim that the data do not support, a contradiction, or a statement of the record that does not match the files; "minor" = imprecise or incomplete; "note" = optional), a proposed replacement text, and your evidence (file and line of the raw data, or the lines of the files that you compared).
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
  { label: 'fixes', prompt: `Your task: the second pass. Compare ${EVID}/report.check3-state.html with ${REPORT} (15 lines differ: 49, 52, 110, 118, 121, 179, 206, 213, 266, 278, 289, 380, 437, 451, 462), and the brief and generator of the check3 state with the files now (generator lines 166, 180, 181; brief lines 25, 39, 40). For every changed sentence: (a) find the finding of check3_results.json that it answers, and judge whether the new text answers it and is itself correct; list every confirmed or partly confirmed finding of check3_results.json that the second pass did NOT answer (the two that are known as not applied: "language-render-5", the Short version as a list, and the second half of "numbers-writes-6", a new item in the list "Open" of the brief); (b) recompute every number of the new or changed sentences from the raw files, for example: "62.4 to 67.1 GB/s (seven runs)" and "37.8 to 40.3 GB/s (five runs)" at line 213 (per-thread columns of the best repetition); at line 289: "73.2 GB/s (best of three repetitions of 0.5 s)", "70.4 to 71.3 GB/s in the nine runs of 2 s", "68.9 to 70.7 GB/s", "81.4 to 82.1 GB/s", "82.3 GB/s", "228 to 230 GB/s", "between 60 and 61 GB/s", "57 GB/s on average (55 to 59 GB/s by writer)", "1.7 × 10^6" and "2.0 × 10^7" data stalls per second, "7 × 10^5" credit-stall cycles per second, "0.005 data stalls per line written", "0.000 refills for writes per line and at most 0.001 write-backs per line", "44.8 GB/s"; at line 278 the values in brackets for 1 GiB; at line 121: "81.4 to 82.1 GB/s", "82.3 GB/s", "75.6 GB/s", "63.2 GB/s", "80.9 GB/s", "72.5 GB/s", "77.5 GB/s" and "64.1 GB/s at the port (est.)"; at line 206 "all 120 CPUs"; in the brief "about 0.001 % of the cycles of the mesh clock (2.0 GHz)"; (c) check that a range belongs to exactly the runs that its sentence names, and that loop, CPUs and date are as stated; (d) look for a new contradiction between the changed text and text that was left unchanged (search the whole report); (e) plain-English rules for every new sentence, and that every new term is defined ("streaming writes", "back-pressure", "credit stall", "data stall", "write in flight", "partner cores"); (f) structure: 978 lines, tags balanced (python3 -B ${EVID}/structure_check.py ${REPORT}), figure geometry (python3 -B ${CRB}/tmp/agent-scratch/spec-row-2026-11-11/check_geometry.py ${REPORT} 6); (g) render the changed blocks with the local headless browser, offline (read /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/headless-chrome-offline-render.md for the command and the font setup, use your own --user-data-dir): the section "Where each number in the figure comes from" with line 121, the paragraphs of line 213, the list of line 266, the list of line 289, and "Words used here". Look at each screenshot at window widths 1000 px and 600 px. Report overlaps, a table that leaves the page at 1000 px, and whether the word list is wider than before at 600 px (compare with ${EVID}/report.before.html). Print the brief to PDF and confirm 2 pages, with page 2 starting at "DRAM write bandwidth against writer placement".` },
  { label: 'record', prompt: `Your task: section 11 of the record (${RECORD} lines 677 to 859) and the status edits that this step made in older sections of the record (compare with ${EVID}/record.before.md: the third sentence of the Short version, the word-list entry "Checker", the report row of the file table in section 1, the sentence on other project files, row R4, the status sentences in D1 and D2, the intro and eleven row ids of section 6, the heading and first paragraph of section 10.6, one item of the list "Not done" of section 10, the end of [Ref5], and the new [Ref38]). Check every statement of the record against the files: (a) the change list against the real difference. List the report lines that differ between ${EVID}/report.before.html and ${REPORT} and confirm that section 11 describes each of them, and that each change that section 11 describes exists in the report. A quotation in the record must be findable word for word in the state that it names ("Before" texts in report.before.html, "Now" texts in the report now). Do the same for the brief and the generator. (b) every count: 978 lines; 28 lines; "34 edits on 28 lines" and "37 edits on 15 of these lines" (run the two scripts ${EVID}/apply_report_p.py and ${EVID}/apply_report_p_fixes.py on scratch copies of the right start states to count, each prints its number of edits; apply_report_p.py needs ${EVID}/texts_p.py beside it, and it was changed after the first pass only if its output differs from report.check3-state.html: say so if it does); the 72 findings at 43 places of the search (${EVID}/sweep_results.json: 29 report lines, 2 generator lines, 12 places in four other files); the 39 findings, 6 major, 16 minor, 17 notes, 32 confirmed, 6 confirmed in part, 1 rejected, and 15 extra findings with 9 minor and 6 notes (${EVID}/check3_results.json); "81 sentences", "47 word for word" (python3 -B ${EVID}/sentences_p.py ${EVID}/record.before.md ${REPORT}); the numbers of elements that section 11.3 gives for lines 214, 289 and 380 (rows of tables, items of lists); the sha256 values of the report and the brief; the points of the brief print (705 of 842, before 642); (c) every number that section 11 states about the measurements, recomputed from the raw files (for example 3,116,815 data stalls in 1.8000 s, 35,180,359 data stalls in 1.8001 s, 1,252,463 credit-stall cycles, 37,976 credit-stall cycles in 3,599,908,867 mesh cycles, 60.15 to 61.34 GB/s, 55.49 to 58.80 GB/s, 63.19 minus 44.78 GB/s, 64.06 to 64.92 GB/s); (d) that every file and script that section 11 and [Ref38] name exists in ${EVID} (one file is expected to be missing because it is written after your check: check4_results.json); that every [RefN] used in section 11 is defined; (e) that the rows of section 6 that are marked "applied" are really applied in the report, and that no other row of section 6 was applied without a mark (compare the proposed texts of rows F1 to F35 with the report now); (f) plain-English rules for section 11: short sentences, one claim per sentence, no semicolons, numbers with units, terms defined in the word list of the record (lines 15 to 62) or at first use; (g) statements that say more than was done, for example about what was rendered and viewed, or about what the checkers confirmed.` },
]

phase('Check')
const results = await pipeline(
  TASKS,
  t => agent(COMMON + '\n' + t.prompt + `\nYour label: ${t.label}.`, { label: `check:${t.label}`, phase: 'Check', schema: FIND }),
  (found, t) => {
    if (!found) return { label: t.label, found: null, verdicts: null }
    return agent(COMMON + `\nYou are the SECOND checker. A first checker with the task below returned the findings that follow. Try to REFUTE each finding: open the files yourself and recompute. Give "rejected" when the finding is wrong or when you cannot reproduce it, "confirmed_in_part" when only a part holds or when the proposed text is itself wrong (then give a corrected text), "confirmed" only when you reproduced it. Then look for defects that the first checker missed in the same task, and return at most 8 of them as extra_findings (same rules, ids "${t.label}-X1" and so on).\n\nThe first checker's task: ${t.prompt}\n\nThe first checker's findings (JSON):\n${JSON.stringify(found.findings, null, 1)}\n\nWhat the first checker says it checked: ${found.checked}\nYour label: refute-${t.label}.`,
      { label: `refute:${t.label}`, phase: 'Refute', schema: VERDICT })
      .then(v => ({ label: t.label, found, verdicts: v }))
  }
)
return results.filter(Boolean)
