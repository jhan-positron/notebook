export const meta = {
  name: 'recheck-code-data-list',
  description: 'Second read-only review of the revised list file: every hand-written statement against the sources, earlier findings applied, plain English and format',
  phases: [
    { title: 'Review', detail: 'three reviewers, one lens each, read-only' },
    { title: 'Verify', detail: 'one verifier per reviewer tries to refute each finding' },
  ],
}

const T = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/code-data-list-2026-11-21'
const LIST = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-test-code-data-list.md'

const FINDINGS = {
  type: 'object',
  properties: {
    items_checked: { type: 'integer' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          section: { type: 'string' },
          list_line: { type: 'string' },
          kind: { type: 'string', enum: ['wrong', 'not-applied', 'missing-fact', 'unclear', 'format'] },
          statement: { type: 'string' },
          evidence: { type: 'string' },
          proposed_fix: { type: 'string' },
        },
        required: ['section', 'kind', 'statement', 'evidence', 'proposed_fix'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['items_checked', 'findings'],
}

const VERIFIED = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          index: { type: 'integer' },
          verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partly'] },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['index', 'verdict', 'evidence'],
      },
    },
  },
  required: ['results'],
}

const COMMON = `You review one generated file a second time. A first review found 67 defects, and the file was revised. You must not change any file outside your scratchpad sub-folder. You return findings only.

The file under review: ${LIST}
The script ${T}/make_list.py generated it. The call sequences, function names, line numbers and file introductions come from the overview files ${T}/ann/<key>.overview.json (keys and source paths: ${T}/manifest.json). The other text is typed in make_list.py: Short version, word list, sections 1, 2, 3.1, the tables and bullets at the end of 3.3 and 3.4, the note on three records in 3.6, 4.1, 4.9, 5.1, 6, 7, 8 and the references. The numbers of the two tables of section 6 are computed by the function result_tables of make_list.py.
The findings of the first review, with the verdict of a verifier for each: ${T}/work/list-review.txt

Context: read ${T}/BRIEF.md (sections 1 to 4 and section 7). Hard rules: do not use ssh; do not run go.sh, go2.sh, ra.sh, rx.sh, run_kernels.sh, build12.sh or any benchmark binary; do not send project data to an outside service; do not run make_list.py without --check, companion_tool.py build or data_companions.py. Reading files, grep, small Python scripts and pandoc are allowed. Work in a scratchpad sub-folder named list-recheck-<your lens>.

The request of the user for this file, word for word:
"I like to review involved test code, from top level shell script to kernel C/ASM code. Please: write ./whole-chip-test-code-data-list.md. Use calling sequence as structure to list all the involved source code files and functions, for old and new code. Include path to the files. list the test data generated from the tests, both from new kernel testing and old kernel testing. list the code to analyze test data and generate final aggregation throughput. when listing a code file and data file, no need to give lengthy introduction, a less than 15-word intro is enough."
("Kernel" here means the read inner loop of the benchmark, not the Linux kernel.)

Folder letters: C = /home/jhan/workspace/titan/cache-perf/crb, R = C/results, S = C/tmp/agent-scratch/w120-7200-2026-11-17, K13 = C/tmp/agent-scratch/kernels-2026-11-13, BWX12 = C/tmp/agent-scratch/bwx12-2026-11-15, W15 = C/tmp/agent-scratch/w120-2026-11-15.

Report a finding only when you have evidence: a source line, a file listing, a script result. Give the evidence in one or two sentences that name the file and line or the command. Give a proposed fix as exact text. Do not report matters of taste, and do not report a missing detail that a companion file already gives. Under checked_ok, name in a few entries what you checked and found correct.`

const LENSES = [
  {
    key: 'facts-code',
    text: `Your lens: EVERY TYPED STATEMENT ABOUT CODE, sections "Short version", "Words used here", 1, 2, 3.1, the tables and bullets at the end of 3.3 and 3.4, the note on the three records in 3.6, 5.1, 7 and 8.
Check each sentence against the source: read the named lines of the named file, and decide whether the sentence is true. Check every line number, every function name, every file name and every count with a script or a direct read. For section 3.1 read lines 309, 313, 339, 353, 365 and 377 of the session record named in [Ref3] with a short Python script. For section 7 check each open point: the statement, the named lines, and whether the "Insufficient data" items are really not recorded in the local files (search before you accept that). For section 8 check each bullet: the named files and folders exist, the counts are right, and what each bullet says about their use is true.
For the word list, compare each entry with the word list of S/FACTS.md (lines 38 to 96) where an entry of the same name exists, and with the sources otherwise. A definition that is false for this list is a finding.`,
  },
  {
    key: 'facts-data',
    text: `Your lens: EVERY TYPED STATEMENT ABOUT DATA AND EVERY NUMBER, sections 4.1, 4.2 to 4.8 (introductions), 4.9, 6 and the references.
1. Section 6: recompute every number of the two tables from the raw csv files with your own script (do not import make_list.py): the 12 medians of part A and the 6 percent values, and the 8 rate ranges with their interval counts for the bwx12 parts. Compare the percent ranges with verdicts.q1_parts of S/facts.json and with section 3.4 of S/FACTS.md. Check every bullet of section 6 against S/baselines-and-rules.txt (rules V2 and V3), S/FACTS.md and S/facts_text.py. Decide whether any presented number breaks a rule of S/baselines-and-rules.txt on pooling.
2. Section 4.1: the table and the five bullets below it, against the csv files.
3. Section 4.9: every row (name, folder, description) against S/baselines-and-rules.txt, S/build_facts.py (rx_sets, step_sets, the part A baselines) and the files in R. Check the bullet on positions and kernel counts, the two converted copies and the lines 47 to 53 of S/baselines-and-rules.txt.
4. The introductions of sections 4.2 to 4.8: every count and every named content, by script.
5. The references Ref1 to Ref5: each must hold what the list says, at the named lines.`,
  },
  {
    key: 'applied-english',
    text: `Your lens: EARLIER FINDINGS APPLIED, PLAIN ENGLISH, FORMAT.
1. Go through ${T}/work/list-review.txt. For every finding with the verdict "confirmed" or "partly", decide whether the present list holds the fix (the verifier text, or a text with the same effect). Report a finding of kind "not-applied" for each one that is still open. Three fixes are still pending by plan and must NOT be reported: the names without ".py" in the call sequence of facts_text.py, the two entries mutate and patch in the call sequence of test_make_report.py, and the words "kernel logs" in two notes of the call sequence of make_report.py.
2. Test the typed text against the plain-English rules that your instructions hold (the plain-english skill): one claim per sentence, short sentences, no idioms or metaphors, every code name, abbreviation and metric defined at first use or in the word list, every number with a unit, Short version of at most three sentences, citations as [RefN] after a sentence. List each violation with the exact phrase and a corrected text. Do not report the word-list entries that are copied word for word from S/FACTS.md.
3. Format: convert the file with "pandoc -f gfm -t html" into your scratchpad sub-folder and inspect the HTML: every table became a table with a constant cell count, every list line became a list item at the right depth (compare the counts by script), every <details> block holds a list, every relative link target exists, no text-diagram line is longer than 70 columns, no heading level is skipped.
4. Count the words of every file introduction (the text after "): " of each entry line that holds a link, and the third cell of each row of the table of section 4.9). 15 words or more is a finding.
5. Read the file once from top to bottom as an engineer who has never seen the project. Name up to 5 places where such a reader cannot follow, each with a proposed fix. Do not repeat a place that the first review named and that was fixed.`,
  },
]

const results = await pipeline(
  LENSES,
  l => agent(`${COMMON}\n\n${l.text}`, { label: `recheck:${l.key}`, phase: 'Review', schema: FINDINGS }),
  (rev, l) => {
    if (!rev || !rev.findings.length) return { lens: l.key, review: rev, verified: { results: [] } }
    return agent(`${COMMON}

You are a verifier. Another reviewer (lens "${l.key}") reported the findings below about the file under review. Some of them may be mistaken. For each finding, try to REFUTE it: read the place in the list, read the source or data that the finding names, and run a script where a number or a line reference is in question. Do not trust the evidence text of the finding: check it yourself.
- verdict "confirmed": the finding is true and the list should change. Give the exact corrected text under "fix".
- verdict "partly": part of it is true. Say which part, and give the fix for that part.
- verdict "refuted": the list is right, or the matter is one of taste. Give the evidence.
Use the index of each finding (starting at 0) in your answer. Answer for every finding.

Findings (JSON):
${JSON.stringify(rev.findings.map((f, i) => ({ index: i, ...f })), null, 1)}`, { label: `verify:${l.key}`, phase: 'Verify', schema: VERIFIED })
      .then(v => ({ lens: l.key, review: rev, verified: v }))
  },
)
return { lenses: results }
