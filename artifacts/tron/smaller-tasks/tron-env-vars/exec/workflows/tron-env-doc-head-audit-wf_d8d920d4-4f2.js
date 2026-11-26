export const meta = {
  name: 'tron-env-doc-head-audit',
  description: 'Independent measurement of the final document: blind audit of 50 random rows and a fact check of the rewritten prose',
  phases: [
    { title: 'Head audit', detail: 'five agents grade 50 random rows of the final file against the code' },
    { title: 'Prose', detail: 'one agent fact-checks every sentence outside the tables; one checks the three staged files as a whole' },
  ],
}

const ROOT = args.root
const WORK = args.work

const BASE = `
Context. README.env-vars.md is a new reference file in the positron-ai/tron repository (Tron: LLM inference on FPGA cards). It lists the environment variables that the source code reads or sets. Support engineers act on section 1. It is about to go into a draft pull request, and this is the last measurement before that.

Checkout: ${ROOT}  (branch jhan-env-vars-doc: main at commit 7eddde7895 plus three staged files: README.env-vars.md, README.md, AGENTS.md). See the change with: git -C ${ROOT} diff --cached
The document: ${ROOT}/README.env-vars.md

Hard rules: do NOT modify any file inside the checkout. Do NOT build, run tests, run repository scripts or start workloads. Only read. Do not use "cd" in shell commands; use absolute paths or "git -C ${ROOT} ...". Write only the one output file named in your task.
`

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          verdict: { type: 'string', enum: ['correct', 'imprecise', 'wrong'] },
          problems: { type: 'array', items: { type: 'string' } },
        },
        required: ['name', 'verdict', 'problems'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['out_file', 'rows', 'notes'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'optional'] },
          where: { type: 'string' },
          problem: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['severity', 'where', 'problem', 'fix'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['out_file', 'findings', 'notes'],
}

function auditPrompt(i) {
  return `${BASE}

YOUR TASK: blind accuracy audit of the 10 rows in ${WORK}/review2/sample-${i}.md. Each row is shown exactly as a reader sees it. The sample was drawn at random from the final file, so your result estimates its error rate. Do not rewrite for style. Grade facts only.

For each row:
1. First derive the facts yourself from the code: find every read and every set of the variable (git grep the name, follow helper functions and constants that hold the name), read the code around them, and work out who reads it, how the text is parsed, what happens when it is unset, empty or invalid, and what the value changes.
2. Then read the row sentence by sentence and grade every statement against the code:
   - "wrong": a statement contradicts the code, or a reader who follows the row gets a result that the row does not predict (wrong default, wrong accepted value, wrong reader, wrong effect, an effect that does not exist, a quoted log text that the source does not hold).
   - "imprecise": nothing contradicts the code, but a statement is vague, misses a condition that changes the outcome, or names a file that is not a main reader.
   - "correct": every statement holds.
   A row gets the worst grade of its statements. A missing detail that does not change what a reader would do is not a problem: rows are limited to 1,000 characters and leave out minor facts on purpose.
3. For every problem give the statement, what the code says, the path:line that proves it, and the corrected cell text (short plain sentences, code names in backticks, no line numbers, no "|" character, the whole row still at most 1,000 characters).

Write JSON to ${WORK}/review2/audit-${i}.json:
{ "rows": [ { "name": "...", "verdict": "correct|imprecise|wrong", "problems": [ { "cell": "...", "statement": "...", "code_says": "...", "site": "path:line", "corrected_cell": "full replacement text for that cell" } ], "checked_sites": ["path:line"] } ], "notes": "..." }
Validate it with python3 -m json.tool. Return the summary: for each row the verdict and one string per problem ("cell: statement -> what the code says (path:line)").`
}

const prosePrompt = `${BASE}

YOUR TASK: fact-check every sentence of the document that is NOT a row of a variable table: "Short version", "How to read this file", "Rules for developers", "Words used here", "How to set a variable" with all its subsections and its table of three places, every section introduction in sections 1 to 7, the two list tables (4.6 Fixture variables and 6.4 Step values: check that the introduction is true for the listed names; a script may sample them), and "How to check this file".
For each factual sentence, find the source that proves it: packaging/systemd/rinzler@.service, packaging/tron-host/, packaging/positron-dice/dice.service, doc/dice.md, doc/slice.md, README.stats.md, README.proxy.md, bin/slice, bin/dice, t/CMakeLists.txt, src/, h/, the workflows, or the rows of the document. Statements about systemd behaviour cite systemd.exec(5); these were checked against the manual text and stand: a required EnvironmentFile that is missing fails the start, a "-" prefix makes a file optional, a file value overrides Environment=, a later file overrides an earlier one, lines that start with "#" or ";" are comments, interior white space of a value is kept. Do not re-check those six.
Check in particular:
- every rule in "Rules for developers" against the layout of the file itself (a script helps): are the tables sorted as rule 2 says, is every row at most 1,000 characters as rule 5 says, does every section-1 row follow rule 3, do sections 4.6 and 6.4 match rule 7;
- every definition in "Words used here" against the code and the repository documentation;
- every Markdown link target and every in-page anchor (GitHub anchor rules);
- the commands in "How to check this file": run them exactly as written from the root of the checkout (they only read; they write two temporary files outside the checkout) and report what they print. The text says they print no name at the baseline commit;
- the statement in section 1's introduction about three groups;
- the statement that Dice removes \`DICE_DISABLE\` and Dice service variables (bin/dice), and the statement about \`--instance\` in \`SYSTEM_CONFIG\`;
- the statement that \`bin/slice\` values win over a declared CTest value.
Report each sentence that is wrong, unsupported, or broader than its source, with the exact replacement sentence. Use "must-fix" only when a reader would be misled or a stated rule is false for the file itself.

Write your findings as JSON to ${WORK}/review2/prose.json:
{ "findings": [ { "severity": "must-fix|should-fix|optional", "where": "heading or file:line", "problem": "...", "evidence": "path:line or quote", "fix": "exact replacement text" } ], "notes": "..." }
Validate it with python3 -m json.tool and return the same findings.`

const wholePrompt = `${BASE}

YOUR TASK: last look at the three staged files together, as the reviewer who must approve the pull request. Read ${ROOT}/AGENTS.md, ${ROOT}/changelog.d/README.md and the staged diff of README.md and AGENTS.md. Read README.env-vars.md from the top through "How to set a variable", then skim every table (a script that prints each row's name, length and first 150 characters helps).
Report only real defects, with evidence:
1. A statement in README.md or AGENTS.md that disagrees with README.env-vars.md (file name, anchor, what the rule requires).
2. Any leftover of an earlier draft: the old file name "README.environment.md" anywhere in the three files; a section number in the text that does not match the headings (for example a reference to "section 2.4" or "4.6" whose content is elsewhere); a table that the text announces and that is missing or empty; a heading without content.
3. Rows that break the file's own rules: run a script over all table rows for: more than 1,000 characters; a table not sorted by name ignoring case; a "For" cell that is not Operators or Developers; a "Values and default" cell without "Unset:"; an empty cell; a "Tron" cell in section 7 that is not one of Reads, Sets, Reads and sets, Unsets; a cell that mentions reviewers, audits, hints or agents; a line number of the form file.ext:123.
4. Words: a British spelling; the word "flag" outside code; "TRON" as a project name outside a variable name; an inline definition that contradicts "Words used here".
5. A name that appears in two places as a variable entry (two rows, or a row and a list in 4.6 or 6.4).
6. Would any CI check or hook that reads these three files fail (bin/ci/lint-agent-guidance.py, lefthook.yml, flake.nix lint checks)? Read their source; do not run repository scripts.
Give the exact fix for each defect.

Write your findings as JSON to ${WORK}/review2/whole.json:
{ "findings": [ { "severity": "must-fix|should-fix|optional", "where": "...", "problem": "...", "evidence": "...", "fix": "..." } ], "notes": "..." }
Validate it with python3 -m json.tool and return the same findings.`

const [audits, prose, whole] = await parallel([
  () => parallel([0, 1, 2, 3, 4].map(i => () =>
    agent(auditPrompt(i), { label: `head-audit:${i}`, phase: 'Head audit', schema: AUDIT_SCHEMA }))),
  () => agent(prosePrompt, { label: 'prose-facts', phase: 'Prose', schema: FINDINGS_SCHEMA }),
  () => agent(wholePrompt, { label: 'whole-change', phase: 'Prose', schema: FINDINGS_SCHEMA }),
])

const rows = (audits || []).filter(Boolean).flatMap(a => a.rows)
const tally = { correct: 0, imprecise: 0, wrong: 0 }
for (const r of rows) tally[r.verdict] = (tally[r.verdict] || 0) + 1
log(`Head audit: ${rows.length} rows graded: ${tally.correct} correct, ${tally.imprecise} imprecise, ${tally.wrong} wrong`)

return {
  audit: { graded: rows.length, tally, notCorrect: rows.filter(r => r.verdict !== 'correct') },
  auditAgentsFailed: 5 - (audits || []).filter(Boolean).length,
  prose: prose ? { findings: prose.findings, notes: prose.notes.slice(0, 1500) } : null,
  whole: whole ? { findings: whole.findings, notes: whole.notes.slice(0, 1500) } : null,
}
