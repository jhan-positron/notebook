export const meta = {
  name: 'tron-env-doc-review',
  description: 'Review README.environment.md: blind accuracy audit of 60 sampled rows, prose fact check, reader lenses, plain-English check, repo conventions, glossary',
  phases: [
    { title: 'Audit', detail: 'six agents re-derive 60 sampled rows from the code and grade each cell' },
    { title: 'Review', detail: 'prose facts, support reader, developer reader, plain English, repo conventions, glossary' },
  ],
}

const ROOT = args.root
const WORK = args.work
const DOC = `${ROOT}/README.environment.md`

const BASE = `
Context. README.environment.md is a new reference file in the positron-ai/tron repository (Tron: LLM inference on FPGA cards). It lists every environment variable that the source code reads or sets: 529 rows in 7 sections. Support engineers act on section 1. All developers will consult the file and add rows to it later. It is about to go into a draft pull request.

Checkout: ${ROOT}  (branch jhan-env-vars-doc; main at commit 7eddde7895 plus three staged files: README.environment.md, README.md, AGENTS.md). See the change with: git -C ${ROOT} diff --cached
The document: ${DOC}

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

YOUR TASK: blind accuracy audit of the 10 rows in ${WORK}/review/sample-${i}.md. Each row is shown exactly as a reader sees it. The sample was drawn at random, so your result estimates the error rate of the whole file.

For each row:
1. First derive the facts yourself from the code: find every read and every set of the variable in the checkout (git grep the name, follow helpers and constants), read the code around them, and work out how the text is parsed, what happens when the variable is unset, empty or invalid, and what the value changes.
2. Then read the row, sentence by sentence. Grade every statement against the code:
   - "wrong": a statement contradicts the code, or a reader who follows the row would get a result the row does not predict (wrong default, wrong accepted value, wrong reader, wrong effect, an effect that does not exist).
   - "imprecise": nothing contradicts the code, but a statement is vague, misses a condition that changes the outcome, or names a file that is not the main reader.
   - "correct": every statement holds.
   A row gets the worst grade of its statements. Do not grade style here.
3. For every problem, give: the statement, what the code says, and the path:line that proves it. Give the corrected cell text in the style of the row (short plain sentences, code names in backticks, no line numbers, no "|" character).

Be strict but fair: a missing detail that does not change what a reader would do is not a problem. Do not accept a statement because it sounds reasonable; open the code.

Write JSON to ${WORK}/review/audit-${i}.json:
{ "rows": [ { "name": "...", "verdict": "correct|imprecise|wrong", "problems": [ { "cell": "Read by|Values and default|Effect|...", "statement": "...", "code_says": "...", "site": "path:line", "corrected_cell": "full replacement text for that cell" } ], "checked_sites": ["path:line", "..."] } ], "notes": "..." }
Validate it with python3 -m json.tool. Return the summary: for each row the verdict and one string per problem ("cell: statement -> what the code says (path:line)").`
}

const REVIEWS = [
  {
    key: 'prose-facts',
    prompt: `YOUR TASK: fact-check every sentence of the document that is NOT inside a variable table. That is: "Short version", "How to read this file", "Rules for developers", "Words used here", "How to set a variable" with its four subsections and its table of three places, every section introduction in sections 1 to 7, and "How this file was built and how to check it".
For each factual sentence, find the source that proves it: the unit file packaging/systemd/rinzler@.service, packaging/tron-host/, doc/dice.md, doc/slice.md, README.stats.md, README.proxy.md, bin/slice, bin/dice, t/CMakeLists.txt, the workflows, or the rows of the document itself. For statements about systemd behaviour, read the local manual pages if they exist (man systemd.exec, man systemd.service); if they do not exist on this machine, say so and mark the statement "not checked here".
Also run the four git grep commands of the last section against the checkout and confirm that each runs without error and prints matches.
Also check every glossary definition in "Words used here" against the repository documentation and code.
Also check that every Markdown link target exists, and that every in-page anchor link (#...) matches a heading of the file under GitHub's anchor rules (lower case, spaces to hyphens, punctuation removed, backticks removed).
Report each sentence that is wrong, unsupported, or broader than its source. Give the exact replacement sentence.`,
  },
  {
    key: 'support-reader',
    prompt: `YOUR TASK: read the document as a support engineer. You run Tron on customer servers through the packaged systemd service. You are not a Tron developer. You can read a log and edit an environment file.
Read the top of the file through "How to set a variable", then all of section 1.
Report:
1. Every place where you cannot tell what to do, or where you would likely do the wrong thing. Quote the text.
2. Every term that the row uses without a definition, when it is not in "Words used here" and not defined in the same cell. List each term once, with the rows that use it.
3. The "For" column. For each of these, open the code and its comments before you report: (a) variables marked "Operators" that look unsafe or pointless to set on a customer system (experiments, test hooks, variables with no effect, variables whose wrong value aborts the server with no message); (b) variables marked "Developers" that a support engineer needs in the field (logging, diagnostics that engineering asks for). Give your reason and the path:line. The definition in the file is: Operators = a support engineer or an operator may set it on a deployed system; Developers = it exists for debugging, experiments or tests, and nobody should set it on a customer system without advice from engineering.
4. Rows of section 1 where the "Effect" cell is so long or so detailed that the main point is hard to find. Give a shorter cell that keeps every fact a support engineer needs: the effect, the interaction with flags and other variables, and how to see the value in effect.
5. Anything a support engineer needs from this file and does not find.`,
  },
  {
    key: 'developer-reader',
    prompt: `YOUR TASK: read the document as a Tron developer who must keep it up to date.
1. Follow "Rules for developers" for three imagined changes: (a) you add std::getenv("TRON_FOO_LIMIT") in h/tron/scheduler; (b) you add \${BENCH_RETRIES:-3} to a script under bin/ci that a workflow calls; (c) a test starts setting FAKE_GH_RATE_LIMIT for its fake gh program. For each, say where the row goes and what you would write. Report every point where the rules are ambiguous, contradict the layout of the file, or leave a decision open.
2. Section placement. Read the names and "Read by" cells of all tables (a script that prints name, section and Read by helps). Report variables that sit in the wrong section or sub-table under the file's own rules, for example a variable that a running program reads but that sits in section 3 to 7, or a CI-only variable in section 3. Open the code before you report one.
3. Consistency. Find families of related variables (same prefix) whose rows describe the same mechanism in conflicting ways, and rows whose "Set by" cell conflicts with another row. Report each with both texts.
4. Sorting: confirm with a script that each table is sorted by name, case-insensitive. Report tables that are not.
5. The two small edits: the pointer added to README.md and the rule added to AGENTS.md (git -C ${ROOT} diff --cached -- README.md AGENTS.md). Are they in the right place, in the style of the surrounding text, and consistent with the rules inside README.environment.md?`,
  },
  {
    key: 'plain-english',
    prompt: `YOUR TASK: check the writing against these plain-English rules. Readers include engineers who are not native English speakers.
Rules: (1) no idioms, metaphors, wordplay or uncommon words; (2) one claim per sentence; (3) short sentences, no semicolons, at most one subordinate clause; (4) separate points use bullets or blank lines; (6) every number carries a unit and, where a reader cannot judge it alone, a plain meaning; (8) every project term, abbreviation and metric is defined at first use or in "Words used here". Also: present tense, no vague words such as "typically", "should", "probably", and no sentence that mentions how the file was produced by tools or agents.
Scope: (a) every sentence outside the tables; (b) every cell of sections 1 and 2; (c) the first 12 rows of every table in sections 3 to 7.
Use a script to list sentences longer than 30 words, sentences with a semicolon, and cells longer than 110 words, then read them. Then read the scope in full for idioms, undefined terms and numbers without units.
Report each violation: the row or heading, the rule number, the exact original phrase, and the corrected text. For a table cell give the full corrected cell. Do not change facts. Do not report a term that the same cell defines or that "Words used here" defines.`,
  },
  {
    key: 'repo-conventions',
    prompt: `YOUR TASK: review the staged change as the repository's own reviewers would, before they see it. Read ${ROOT}/AGENTS.md, ${ROOT}/.github/AGENTS.md, ${ROOT}/changelog.d/README.md and ${ROOT}/README.ci.md (the parts about lint and required checks) first. Look at how the other root documents are written: README.stats.md, README.proxy.md, README.ci.md.
Check:
1. Claims wider than the code. Sentences in the prose of README.environment.md, in README.md and in AGENTS.md that promise more than the change delivers. For example: "every environment variable", "exactly one row", the rule that every pull request updates the file. Is each one true at this commit, and is it worded so that it stays true or fails visibly?
2. Text that goes stale. Counts, commit ids, dates, file lists, "at the time of writing" statements, references to pull requests. Say which ones are acceptable history and which ones will be wrong after the next unrelated merge.
3. Scope. Does the change touch only what it needs? Is the AGENTS.md rule in the right section and in the style of that file? Does the README.md pointer sit in a sensible place? Would CODEOWNERS (.github/CODEOWNERS) route this change to sensible reviewers?
4. CI. Which CI checks and lefthook hooks read these three files (flake.nix lint checks, lefthook.yml, bin/ci/lint-agent-guidance.py, lint-notes, any Markdown or link check)? Would any fail? Name the check and the reason. Do not run repository scripts, except that reading their source is expected.
5. Changelog. Does this change need a changelog.d fragment under changelog.d/README.md? If yes, give the exact file name pattern, section and line text (the pull request number is not known yet; write <PR>).
6. File name and location. Is README.environment.md consistent with the names and roles of the other root README.*.md files and the doc/ directory? If another name or place fits the conventions better, say which and why.
7. Size. The file is about 317 KB with table rows up to about 1300 characters. Check how the repository's other large Markdown files compare (wc -c). Report any concrete problem that this size causes (for example a documented GitHub rendering limit that you can cite), not a general worry.
8. Wording that a reviewer would reject: cells that quote log text or source comments in a way that will break on the next code change, statements about source comments, statements such as "A source comment says ...". Count them with a script and judge whether they belong in a reference file.`,
  },
  {
    key: 'glossary',
    prompt: `YOUR TASK: improve "Words used here". The row writers proposed many term definitions; they are in the "new_terms" arrays of ${WORK}/chunks/*.final.json. Many cells define a term in a clause inside the cell.
1. With a script, collect every proposed term with its definitions and the number of rows of README.environment.md that use the term (case-insensitive whole-phrase match). Also find recurring inline definitions of the form "X (a ...)" / "X, the ..." in the cells.
2. Choose the terms that deserve a place in "Words used here": a project term (not a general computing term) that at least 4 rows use, or that a support engineer must know to read section 1. Aim for at most 20 additions. Do not repeat terms the list already has.
3. For each chosen term, write one definition of at most 30 words in plain short sentences, and verify it against the code or the repository documentation. Give the path:line that supports it.
4. Report terms that different rows define in CONFLICTING ways (give both texts and say which is right).
5. Report terms in the existing "Words used here" list that no row uses.
Write the additions as ready-to-paste Markdown bullets in the style of the existing list: "- **Term**: definition."`,
  },
]

function reviewPrompt(r) {
  return `${BASE}

${r.prompt}

Write your full findings as JSON to ${WORK}/review/${r.key}.json:
{ "findings": [ { "severity": "must-fix|should-fix|optional", "where": "row name, heading, or file:line", "problem": "...", "evidence": "path:line or quote", "fix": "exact replacement text or exact action" } ], "notes": "..." }
"must-fix" means a reader would be misled or a required check would fail. "should-fix" means a clear improvement with low risk. "optional" is a matter of taste.
Validate the file with python3 -m json.tool. Return the same findings in the summary, with "fix" holding the exact replacement text where one applies.`
}

const [audits, reviews] = await parallel([
  () => parallel([0, 1, 2, 3, 4, 5].map(i => () =>
    agent(auditPrompt(i), { label: `audit:${i}`, phase: 'Audit', schema: AUDIT_SCHEMA }))),
  () => parallel(REVIEWS.map(r => () =>
    agent(reviewPrompt(r), { label: `review:${r.key}`, phase: 'Review', schema: FINDINGS_SCHEMA })
      .then(x => x ? { key: r.key, ...x } : null))),
])

const rows = (audits || []).filter(Boolean).flatMap(a => a.rows)
const tally = { correct: 0, imprecise: 0, wrong: 0 }
for (const r of rows) tally[r.verdict] = (tally[r.verdict] || 0) + 1
log(`Audit: ${rows.length} rows graded: ${tally.correct} correct, ${tally.imprecise} imprecise, ${tally.wrong} wrong`)

return {
  audit: { graded: rows.length, tally, notCorrect: rows.filter(r => r.verdict !== 'correct') },
  auditFailed: 6 - (audits || []).filter(Boolean).length,
  reviews: (reviews || []).filter(Boolean).map(r => ({
    key: r.key,
    counts: r.findings.reduce((a, f) => { a[f.severity] = (a[f.severity] || 0) + 1; return a }, {}),
    mustFix: r.findings.filter(f => f.severity === 'must-fix'),
    shouldFix: r.findings.filter(f => f.severity === 'should-fix').map(f => ({ where: f.where, problem: f.problem.slice(0, 300) })),
    notes: r.notes.slice(0, 1200),
    out_file: r.out_file,
  })),
  reviewsFailed: REVIEWS.length - (reviews || []).filter(Boolean).length,
}
