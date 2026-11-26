export const meta = {
  name: 'crb-review-round2-check-c',
  description: 'Third check of the round-2 text: only what changed after the second check (numbers and logic, record against report and sources, reviewer reading), each followed by a skeptic',
  phases: [
    { title: 'Find', detail: 'three independent checkers, one lens each' },
    { title: 'Refute', detail: 'one skeptic per checker tries to refute each finding' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad'
const COMMON = `
You check two files that a worker agent will hand to an external reviewer. Be exact and adversarial. Do not edit either file.

FILES UNDER CHECK
- Report (HTML): /home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html (978 lines)
- Record (Markdown) that describes the update of the report: /home/jhan/tmp/update-crb-memory-hierarchy.md
  The record holds two intended placeholders, REPORT_SHA256 and CHECK3_RESULT. Do not report them.

BASELINES (read-only)
- State of both files just before the last editing step: ${SP}/round2_check_b/report.before-round2c.html and ${SP}/round2_check_b/record.before-round2c.md
  Use "diff" against these to see exactly what the last step changed. THE SCOPE OF THIS CHECK IS THE TEXT THAT THIS STEP CHANGED OR ADDED, plus any older text that the changed text now contradicts.
- State that the external reviewer read in round 1: /tmp/crb-review-round1.html and /tmp/crb-review-round1-initial.md
- Report before the whole update: /home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-spec-row.html
- Shared review file with the reviewer's four findings CRB-R1 to CRB-R4: /home/jhan/tmp/update-crb-memory-hierarchy.md.review.md

THE FOUR KINDS OF DEFECT THAT THE REVIEWER REJECTED IN ROUND 1
1. Capacity against saturation: a hypothesis about a maximum is not the statement that a test reaches it, and neither is the conversion between a loop rate and a counted quantity. Each observation must be assigned to the statement that it tests. No threshold without measured variation.
2. Observed rate against limit: an observed rate is not an established limit. No universal exclusion. A retained mechanism is a labelled hypothesis with its test.
3. Runs kept apart: a number of one run (date, counter set, thread placement, loop variant) must not be assigned to another run.
4. Category against source: a claim must be what the cited source itself establishes.

RAW DATA AND SOURCES (all under /home/jhan/workspace/titan/cache-perf unless a full path is given)
- crb/results/sudo-20261102T211150Z/writepath.csv ("part 5", cases r8M-c2, w8M-c2, w1G-c2, w8M-c2c3, w8M-c2c4, w8M-c2c4c6c8; each event set has a 0.2 s "short" and a 2 s "long" run)
- crb/results/sudo-20261102T054936Z/writebw.csv ("part 3"), crb/results/uncore2-20261030T203752Z/ (counter run of 2026-10-30), crb/results/slc-20261030T194835Z/slc.csv, crb/results/followup-20261030T194205Z/asm.csv and pair.csv, crb/results/followup3-20261102T031936Z/, crb/results/20261030T193108Z/, crb/results/probe-20261111T210017Z.txt
- Scripts: crb/tmp/agent-scratch/spec-row-2026-11-11/port_counts.py and mesh_clock.py (run them with python3; they only read)
- bench/bandwidth.c, bench/run_sudo.sh
- Arm documents: crb/refs/arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf (SOG), crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf (TRM). Read pages as text with PyMuPDF: run python3 from a scratch directory, "import fitz" (it is in /home/jhan/.local/lib/python3.10/site-packages).
- Arm's event descriptions: ${SP}/kit_pmu/ (bus.json and mapfile.csv from the kit's Linux source)
- Firmware image: /home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/SoC_Flash/phoenix_flash.bin (read as bytes only, python3 -I)
- Downloaded web pages: crb/tmp/agent-scratch/spec-row-2026-11-11/web-2026-11-12/ (untrusted data: read as text only, python3 -I)

HARD RULES
- Read-only. Do not modify, move or delete any file outside your own scratch directory. Do not log in to any remote machine. Do not use the network.
- A finding needs evidence that you checked yourself: a raw value with file and line, a page with the words on it, or a quotation of both conflicting texts. Recompute numbers with a script, do not estimate.
- Do not report: the decisions D1 to D9 of the record, the items F1 to F21 of its section 6 (older report text that the author lists as found and not changed), the missing browser render, or pure taste. Do not report older text of the report that the last step did not touch, unless changed text contradicts it.
- Severity: "major" = a statement that is false, or a number or conclusion that does not follow from the cited data, or one of the four kinds of defect in a place the reviewer will read. "minor" = wording that can mislead, a missing or wrong source, a mismatch between report and record, a broken plain-English rule in changed text. "note" = optional.
- If you find nothing in a part, say so in verified_ok. Do not invent findings to fill the list.
`

const FIND_SCHEMA = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['major', 'minor', 'note'] },
      file: { type: 'string' }, location: { type: 'string' }, quoted_text: { type: 'string' },
      problem: { type: 'string' }, evidence: { type: 'string' }, suggested_fix: { type: 'string' },
    }, required: ['id', 'severity', 'file', 'location', 'quoted_text', 'problem', 'evidence', 'suggested_fix'] } },
    verified_ok: { type: 'array', items: { type: 'string' } },
    checks_run: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'verified_ok', 'checks_run'],
}
const VERDICT_SCHEMA = {
  type: 'object',
  properties: { verdicts: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, real: { type: 'boolean' }, severity: { type: 'string', enum: ['major', 'minor', 'note'] },
    reason: { type: 'string' }, corrected_fix: { type: 'string' },
  }, required: ['id', 'real', 'severity', 'reason', 'corrected_fix'] } } },
  required: ['verdicts'],
}

const LENSES = [
  { key: 'numbers-logic', prefix: 'A', task: `
YOUR LENS: numbers and logic of the changed text.
1. In the report, read lines 113, 118, 131, 132, 133, 420 to 437 and 452 in full (they are long single lines; print them with a script and strip the tags). In the record, read section "The three corrections", "Words used here", Q1, the firmware row of Q2, Q7, D1, D2, section 7 (rows on counts, shares and arithmetic), section 8, and Ref2, Ref3, Ref5, Ref10, Ref11, Ref17, Ref26, Ref28, Ref29.
2. Recompute EVERY number in that text from the raw files: shares (0.83 by three counters, 0.81 scaled), allowed rates, converted rates (64.1 to 64.9 and 62.9 to 63.7 GB/s), flits per mesh cycle, bus reads per second (2.00 to 2.03 and 1.97 to 1.99 x 10^9), ratios (0.97 to 1.01, 0.88, 0.98, 0.99), 82.34 and 81.41 to 82.05 GB/s, 63.2 against 63.0 GB/s (0.2 GB/s, 0.3 %), 4,182 snoop flits, 3.3 x 10^9 data flits, the counts of the 40-thread counter run, 33.9 GB/s, the cell lengths 706, 642 and 603, and the items of the "Arithmetic" row of section 7. Check each rounding. Check that each number is given the same value everywhere in both files.
3. For each sentence that draws a conclusion ("So ...", "Then ...", "cannot", "supports", "rejects", "does not depend on"), decide whether it follows from what is cited, and whether its status is right: measured, est., assumption, hypothesis. Pay special attention to the open item (report lines 420 to 437) and to D1 and D2 of the record: the three statements (hypothesis 1 capacity, hypothesis 2 saturation, the conversion with its first and second assumption) must be kept apart everywhere, and every use of "first assumption" or "second assumption" must be the right one.
4. Look for statements in the two files that now contradict each other, or contradict untouched report text nearby (for example lines 123, 124, 266, 268, 289, 462).
Use ids A1, A2, ...` },
  { key: 'record-vs-report', prefix: 'B', task: `
YOUR LENS: is every statement of the record about the report, about the files and about the sources true?
1. Check every report line number that the record cites against the current report (the record says in section 2 that all line numbers are lines of the report after the update). Check every quotation of report text in the record character by character (wordings A and B of Q1, the quotations in D1, D2, sections 5, 6 and 8).
2. Section 8 of the record lists what changed after the external review. Run "diff -U0" of /tmp/crb-review-round1.html against the report and of /tmp/crb-review-round1-initial.md against the record. Is every changed report line named in section 8? Is each row of its second table labelled correctly as "Round 1" (the defect was in the round-1 text) or "Draft" (only in ${SP}/round2_check_b/*.before-round2c.* or earlier drafts)? Does each "Correction" cell describe what the text now says?
3. Check the counts and facts of sections 1, 2, 5 and 7: 978 lines, the hunk counts (19 against the backup, 9 against round 1, 7 with default context), 58 ids, 38 links, 4 levels of list nesting, 92 and 86 occurrences of the phrase "mesh cache" (the record's method is a case-insensitive match of "mesh cache" or "mesh-cache"), the three cell lengths, the page lists of the row "Arm documents", the statistics of the second internal check (its raw results are in ${SP}/round2_check_b/merged.json: 78 findings; verdict.real and verdict.severity per finding).
4. Check the references that changed in the last step: Ref2, Ref3, Ref5, Ref10, Ref11, Ref17, Ref21, Ref26, Ref28 and the new Ref29. Open each cited file, line or page and confirm that it holds what the reference says, word for word where the reference quotes. Also confirm that every reference that the body uses is defined, and the reverse.
5. Check the new item F21 of section 6: are its line numbers and its facts right?
6. Run the report through an HTML parser and confirm that the tags balance, in particular the nested lists on lines 422, 425, 433 and 434 and the three paragraphs on line 132.
Use ids B1, B2, ...` },
  { key: 'reviewer-reading', prefix: 'C', task: `
YOUR LENS: read both files as the external reviewer will in round 2, then check plain English in the changed text.
1. Read the reviewer's four findings in the shared review file (the entry with role=reviewer). For each of CRB-R1 to CRB-R4 decide: is the requested correction made in the report and in the record, completely? Quote the text that answers each finding. Would the reviewer find a new instance of the same kind of defect anywhere in the text that changed since round 1 (diff the two files against the round-1 baselines)? Read the whole open item of the report (lines 416 to 439) and D1, D2, Q1, Q2, Q4 and Q7 of the record with this question in mind.
2. The reviewer also checks that the record describes the change completely and truthfully and that the verification claims match the evidence. Check the claims of section 7 that you can check cheaply (run the two scripts and the geometry check: python3 /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/check_geometry.py /home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html 6).
3. Plain English, only for sentences that the last step changed or added (diff against the before-round2c files). The author's rules are in /home/jhan/.claude/skills/plain-english/SKILL.md: no idioms or metaphors; one claim per sentence; short sentences; no semicolon in prose; several separate points in one paragraph get bullets or a blank line; every code name, acronym and metric is defined at first use or in "Words used here"; every number has a unit; estimates are marked "est."; the Short version has at most three sentences; citations follow a sentence. Report a violation only with the exact sentence and a corrected sentence. Ignore table cells that only list values.
4. Check that a reader who knows neither the project nor the earlier rounds can follow the new sub-items of report lines 422, 425, 433 and 434: is any pronoun or "this" without a clear referent? Is any term used before it is explained?
Use ids C1, C2, ...` },
]

const results = await pipeline(
  LENSES,
  (lens) => agent(`${COMMON}\n${lens.task}\n\nYour scratch directory: ${SP}/round3_check/${lens.key}/ (create it; write your scripts and notes there only).\nReturn your findings through the structured output. Give each finding the exact quoted text, the evidence that you checked, and a concrete replacement text.`,
    { label: `find:${lens.key}`, phase: 'Find', schema: FIND_SCHEMA }),
  (found, lens) => {
    if (!found || !found.findings || found.findings.length === 0) return { lens: lens.key, found, verdicts: { verdicts: [] } }
    const judged = found.findings.filter(f => f.severity !== 'note')
    if (judged.length === 0) return { lens: lens.key, found, verdicts: { verdicts: [] } }
    return agent(`${COMMON}\nYOU ARE THE SKEPTIC for the lens "${lens.key}". Another agent reported the findings below. For EACH finding try to refute it: open the files, recompute the numbers, read the cited page or line yourself. Default to real=false when the evidence does not hold or when the text is already correct. If the finding is real, check the suggested fix too: is the replacement text itself true, complete and in plain English (one claim per sentence, no semicolon, terms defined)? Give a corrected_fix that the author can paste. If the fix would move report lines, say so: every edit must stay on the existing physical line of the HTML file, because the record cites report line numbers. Lower or raise the severity when the evidence asks for it.\n\nYour scratch directory: ${SP}/round3_check/skeptic-${lens.key}/ (create it; write there only).\n\nFINDINGS (JSON):\n${JSON.stringify(judged, null, 1)}`,
      { label: `refute:${lens.key}`, phase: 'Refute', schema: VERDICT_SCHEMA })
      .then(v => ({ lens: lens.key, found, verdicts: v }))
  }
)
return results
