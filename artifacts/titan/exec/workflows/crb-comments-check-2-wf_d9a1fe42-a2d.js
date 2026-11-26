export const meta = {
  name: 'crb-comments-check-2',
  description: 'Check the edits of 2026-11-12 after the rename check (five author comments, rewrite of the compiled-loop passage, 14 fixes) and the new record section; each finding goes to a skeptic',
  phases: [
    { title: 'Find', detail: 'two checkers: report edits, record section 10' },
    { title: 'Verify', detail: 'one skeptic per checker tries to refute each finding' },
  ],
}

const S = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc'

const COMMON = `
CONTEXT
Project folder C = /home/jhan/workspace/titan/cache-perf/crb . It holds a report (C/crb-memory-hierarchy.html, 978 lines) and the raw data of memory measurements on an Arm server called CRB. B = /home/jhan/workspace/titan/cache-perf/bench holds the benchmark source. The record of all changes is /home/jhan/tmp/update-crb-memory-hierarchy.md (672 lines).
Three states of the report exist, all with 978 lines, so "diff" pairs them line by line:
- REVIEWED = C/tmp/crb-memory-hierarchy.before-slc-rename.html (the state that an external reviewer accepted).
- RENAMED = ${S}/report.after-rename.before-fixes.html (after the rename of "mesh cache" to "SLC" and a first buffer-size edit; that step was already checked by an earlier run, do not re-check it).
- NOW = C/crb-memory-hierarchy.html . 26 lines differ from RENAMED: 35, 49, 52, 58, 60, 82, 105, 107, 112, 113, 116, 118, 122, 124, 131, 132, 133, 139, 179, 182, 297, 421, 425, 429, 454, 457.
The 26 changed lines come from two scripts: ${S}/apply_report_fixes.py (14 fixes that the earlier check confirmed) and ${S}/apply_report_comments.py (the author's five comments of 2026-11-12).
The author's five comments, word for word:
1. \`The cycle number is derived: ns × 2.8 GHz.\` in table \`Where each number in the figure comes from\` change to \`Cycles derived\`
2. \`30 ns (85 cycles)\` in table \`Where each number in the figure comes from\` change to \`SLC latency avg: 30 ns (85 cycles)\`
3. \`≥0.62 TB/s whole chip\` in table \`Where each number in the figure comes from\` change to \`SLC throughput ≥0.62 TB/s whole chip\`
4. \`So the label "3 loads + 2 stores" gives two separate limits. It does not mean five operations in one cycle.\` : this is great clarification, please change all \`3 loads + 2 stores\` to \`3 loads / 2 stores\`
5. The long paragraph starting \`The read loop compiled from C reaches 66.8 GB/s, which is 1.5 loads of 16 B per cycle. This loop is the C function k_read in bench/bandwidth.c.\` can rewrite with better format. And please list the relevent C code
For comment 5 the three source lines 131 to 133 were rewritten: a new sub-heading (h3), three code listings inside "pre" elements (line breaks are written as the character reference &#10; so that the line count of the file stays the same), a table of limits, a list of two hypotheses and a table for the missing test. The intent: every statement and number of the old text is kept, only the form changes.

SOURCES
- B/bandwidth.c (the listings must equal lines 138 to 148 and 173 to 195).
- C/results/probe-20261111T210017Z.txt (disassembly read on CRB; the machine-code listing must equal lines 44 to 59, white space apart).
- Arm's guide for the core ("SOG"): C/refs/arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf (pages 11, 13, 23 to 26, 55). The mesh manual ("CMN S3 TRM"): C/refs/arm-cmn-s3-r2p3-trm-107858.pdf . "import fitz" reads PDFs.
- Raw result files under C/results (for example followup-20261030T194205Z/asm.csv and pair.csv, 20261030T193108Z/bandwidth.csv, sudo-20261102T211150Z/writepath.csv, sudo-20261102T054936Z/writebw.csv, sudo-20261102T040631Z/writebw.csv). In "perf stat -x," rows column 5 is the share of the run in which the counter ran; below 100 the count is scaled and is an estimate.
- The results of the earlier check: ${S}/check1_results.json and the readable files ${S}/check1_report-rename.txt (not present; use the json), ${S}/check1_brief-language.txt, ${S}/check1_answer-facts.txt, ${S}/check1_replacement-statements.txt .

A HEADLESS BROWSER EXISTS (offline use only). To render a file, make your own folder A = ${S}/agents2/<your label>/ and run:
  mkdir -p $A/home $A/profile $A/tmp
  env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=${S}/render/fontconfig/fonts.conf timeout 120 /home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=1000,6400 --screenshot=$A/out.png "file:///path/to/file.html"
Use --dump-dom instead of --screenshot to get the page after its scripts ran, and --no-pdf-header-footer --print-to-pdf=$A/out.pdf to print. Keep the option --host-resolver-rules exactly as given: it blocks the network. The page's monospace font is not installed here, so listings show in DejaVu Sans Mono. View images with your Read tool (crop tall images with PIL first).

RULES
- Read only. Do not change, create or delete any file under /home/jhan/workspace or /home/jhan/tmp. Do not run C/make-brief.py . Do not log in to any machine. Do not use the network.
- Scratch files go into ${S}/agents2/<your label>/ only.
- Report only what you verified in the files yourself. Give the line number and the exact text for every finding.
- The author's rules for prose (apply them to NEW text only): no idioms or metaphors; one claim per sentence; short sentences; no semicolons; every acronym and code name defined at first use in the document; numbers with units; estimates labelled "est."; a claim about a test result must name its data or source, or be labelled as a hypothesis with its test.
- Do not report as findings: the element ids and link targets that contain "mesh-cache"; the six history notes that name the old term at report lines 49, 60, 179, 182, 183, 454; defects in report text that today's edits did not write (the record lists known ones as F1 to F34 in its section 6). If you find a NEW defect in old text, report it with severity "note".
- Severity: "major" = a wrong statement, a wrong number, a broken page, a lost statement, or a place where the reader is misled; "minor" = wording, grammar, format, an inconsistent label; "note" = an observation with no required change.
`

const FIND_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['major', 'minor', 'note'] },
          where: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          proposed_fix: { type: 'string' },
        },
        required: ['id', 'severity', 'where', 'problem', 'evidence', 'proposed_fix'],
      },
    },
    checked: { type: 'array', items: { type: 'string' } },
    not_checked: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked', 'not_checked'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'partly', 'refuted'] },
          reason: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['id', 'verdict', 'reason', 'fix'],
      },
    },
    extra_findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['major', 'minor', 'note'] },
          where: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          proposed_fix: { type: 'string' },
        },
        required: ['id', 'severity', 'where', 'problem', 'evidence', 'proposed_fix'],
      },
    },
  },
  required: ['verdicts', 'extra_findings'],
}

const FINDERS = [
  {
    key: 'report-edits',
    prompt: `${COMMON}
YOUR TASK (label: report-edits). Check the 26 changed lines of NOW against RENAMED. Use id prefix "RE".
1. Comments 1 to 4. Is each done exactly as the author asked, in every place? Search NOW for any "3 loads + 2 stores" that is left, in body text, figure text, table cells, link texts and the strings of the two script blocks. The mixes "3 loads + 1 store" and "2 loads + 2 stores" were kept on purpose (they name the operations of one cycle); say if you disagree. Does any other text of the report now contradict the new labels (for example a sentence that quotes the old row label of the source table)?
2. Comment 5, fidelity. Take the text of lines 131 to 133 in RENAMED and in NOW (strip the tags). For every sentence, number and citation of the old text, find where it is in the new text. List anything that is lost, changed in meaning, or attached to another subject. Check every cell of the new table of limits against the old sentences and against Arm's guide (SOG pages 11, 13, 23, 26 and 55): the limits 3, 2, 10, 6, "2 and 2", 20 and "4, 4 and 2", and the values of the loop 1.5, 1.5, 3.0, 1.5, 1.5, 3.7 and 0.75. Check the new sentences (the lead paragraph under the new heading, the two sentences that introduce k_asmread, "How the loop is counted:", "The table below compares ...") for truth against the report itself and the sources. Example: the lead says "The asm read loop measured 132.7 GB/s, which is 99 % of 3 loads per cycle" - check it against line 130.
3. Comment 5, listings. Confirm with a script that the three listings equal their sources (decode &#10; and the HTML entities first). Is the description of each listing right (number of instructions, bytes per pass, which function)? Is the citation of the line ranges right?
4. Comment 5, form. Does the new h3 fit the heading structure of the report (the contents list at lines 55 to 72 must list it, with the same text)? Is the HTML valid (balanced tags, a "pre" is not inside a "p", lists and tables closed)? Render the page with the headless browser: (a) --dump-dom of NOW and confirm that no script error occurs and that the figures drawn by script still have content; (b) a screenshot of the part from the heading 'What "3 loads / 2 stores of 16 B per cycle" means' to the end of the new sub-section (you may build a scratch page from lines 1 to 47 plus lines 122 to 133 of NOW; without the scripts the figure with id "pipes" stays empty, which is expected). Look at the screenshot: do the listings, the lists and the two tables read well? Is anything cut off, overlapping or wider than the column?
5. The 14 fixes of ${S}/apply_report_fixes.py . For each one: is the new text right? Check the facts behind lines 118, 421, 425, 429 and 457 in the raw files and sources: the share 0.82 of case asmread-8M-4 in the two writebw.csv files (lines 601, 605, 610, 614) and the loop rates of that case; the rates 75.6 and 44.8 GB/s in C/results/20261030T193108Z/bandwidth.csv (lines 154, 160, 218); B/bandwidth.c lines 4 to 6 and 301 to 306; B/run_crb.sh lines 83 to 89; the sizes 3 MiB and 256 MiB of the whole-chip tests; CMN S3 TRM pages 31 to 32 for the way counts cited at line 139.
6. Consistency inside the report after today's edits. Line 421 now limits two of the four kinds of run of "hypothesis 2" to the asm loop: do lines 422 to 437 still agree with that? Line 425 says "0.82 accesses to the SLC per line" for four busy cores: does any other line contradict it? Line 457 defines "at 8 MiB": does it agree with the captions at lines 265 and 296?
Return the structured result. For each problem give the exact replacement text in proposed_fix.`,
  },
  {
    key: 'record-section-10',
    prompt: `${COMMON}
YOUR TASK (label: record-section-10). Check the NEW and CHANGED text of the record /home/jhan/tmp/update-crb-memory-hierarchy.md . Use id prefix "RC". The record before today's change is ${S}/record.before-section10.md ; diff the two to see what is new: the third sentence of the Short version, two places in section 1, one sentence in Q4, one in D6, the intro and several rows of section 6 (F1, F8, F10, F14, F15 reworded, F22 to F34 new), the whole section 10 (10.1 to 10.7) and the references Ref30 to Ref36. The text "REPORT_SHA256" stands in two places on purpose; it is filled in at the end.
1. Every statement of section 10 about the report, the brief and the generator: check it in the files. Counts: "101 replacements on 77 lines" (scripts ${S}/apply_report.py and the diff REVIEWED against RENAMED minus the 3 lines of the buffer-size edit), "93 lines differ from the reviewed state" (diff REVIEWED against NOW), "10 lines" and "11 lines" for the generator and the brief (their "before" copies are C/tmp/make-brief.before-slc-rename.py and C/tmp/crb-memory-hierarchy-brief.before-slc-rename.html), the six history notes, the places with "SLC (L3)", the line numbers given for every change, the six places of "3 loads / 2 stores", "59 ids" and "39 link targets", "14 text strings and 2 comments" in the script blocks. Sentences count of the passage: "Of the 60 sentences of the old text, 47 are in the new text word for word. The other 13 became list items, table cells or table rows" (old text = lines 131 to 133 of RENAMED; recount with your own method and say how you split sentences).
2. Section 10.4: are the three corrections described as they are in the report, and is the evidence right?
3. Section 10.5 (answers): check the quotations of the CHI specification (/home/jhan/workspace/vendor-resources/ARM/pdf/IHI0050H_amba_chi_architecture_spec.pdf pages 32, 455, 518), the pages of the CMN S3 TRM that are cited (12, 17, 51, 250, 621, 2120), and every number: 71 and 58.7 GB/s, 0.83, 77.5 to 78.5, 64.1 to 64.9, 63.2, 44.8, 63, 78, 82, "62.0 to 64.9 GB/s (est.)" and "0.97 to 1.01". The script C/tmp/agent-scratch/spec-row-2026-11-11/port_counts.py recomputes the counts of part 5 (it only reads). Is the logic stated without overclaim (a hypothesis about a maximum is not shown by a rate; numbers of one run are not assigned to another run; every estimate is marked)?
4. Section 10.6 (P1, P2, P3 and the two texts for the brief): an earlier run already checked drafts of these texts (see ${S}/check1_replacement-statements.txt). Check only that the final texts in the record equal the corrected texts of that run or differ for a stated good reason, and spot-check ten numbers of your choice in the raw files.
5. Section 10.7 (checks): each row must describe a check that the files in ${S} can support. Check the counts of the first run in ${S}/check1_results.json : "73 findings: 12 major, 36 minor and 25 notes", "confirmed 60, confirmed 13 in part and rejected none", "22 findings of their own". The folder ${S}/render holds the renders (brief.pdf, part-section.png, sub.1.png to sub.3.png, report.dom.html).
6. Section 6: rows F22 to F34. For each row check the line numbers, the quotations and the numbers against the report, the brief, the generator and the raw files. Rows F23, F24, F27 and F29 say which parts were not recomputed by the author; recompute those parts yourself and report the result. The reworded rows F1, F8, F10, F14 and F15 must quote the report as it is NOW.
7. References Ref30 to Ref36: every file, line number, page and number.
8. The author's prose rules on the new text of the record. The record is a document of its own: a term that section 10 uses must be defined in the record's list "Words used here" (lines 15 to 49) or at first use. List the terms that section 10 uses with no definition anywhere in the record.
Return the structured result. For each problem give the exact replacement text in proposed_fix.`,
  },
]

const results = await pipeline(
  FINDERS,
  f => agent(f.prompt, { label: `find:${f.key}`, phase: 'Find', schema: FIND_SCHEMA }),
  (found, f) => {
    if (!found) return { key: f.key, found: null, verdicts: null }
    return agent(`${COMMON}
YOUR TASK (label: skeptic-${f.key}). Another checker returned the findings below for the area "${f.key}". Try to REFUTE each finding. For each one, open the files yourself and check the evidence line by line. A finding is "confirmed" only if you verified it yourself in the files. It is "refuted" if the evidence is wrong, if the place is one of the things that the rules say not to report, or if the proposed fix would make the text wrong. It is "partly" if the problem is real but the proposed fix is wrong or too wide; then give the right fix. Default to "refuted" when you cannot confirm the evidence.
For a confirmed or partly confirmed finding, give in "fix" the exact final change (file, line, old text -> new text), short and ready to apply. The old text must occur exactly once in that line. For a finding that needs no change, write "no change".
Then use the rest of your effort on what the first checker may have missed in the same area: read its "checked" and "not_checked" lists, pick the two or three most important unchecked or weakly checked items, and check them yourself. Put any new problem into "extra_findings" (id prefix "X-"), with line numbers and exact text.

The checker's task was:
----
${f.prompt.replace(COMMON, '')}
----
The checker's result (JSON):
${JSON.stringify(found, null, 1)}
`, { label: `verify:${f.key}`, phase: 'Verify', schema: VERDICT_SCHEMA })
      .then(v => ({ key: f.key, found, verdicts: v }))
  }
)

return results
