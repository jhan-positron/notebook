export const meta = {
  name: 'round2-page-v3-confirm',
  description: 'Confirm the third version of the reply page: facts of the changed parts, plain English by reading, and the posted texts',
  phases: [
    { title: 'Confirm', detail: 'three reviewers of the third version; real defects only' },
  ],
}

const PAGE = '/home/jhan/workspace/intel-AMX/muse-glimmer/round2-respond-2-issac.html'
const V2 = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/db5d90b8-2c02-4aa1-b9df-6b564487154c/scratchpad/r3/page-before-patch1.html'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123'
const WT = '/home/jhan/workspace/ai-runs/tron-glimmer-amx'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-muse-glimmer/memory'

const CTX = `
CONTEXT
The page ${PAGE} is a report for the user jhan. It answers a reviewer's follow-up on pull request 5022 of the GitHub repository positron-ai/tron. The reviewer Isaac (GitHub login ishapira-positron) left one conversation comment and opened draft PR 5606 with two commits (c6cba6b0f8, then 90a9110be5) on top of the PR head ddf843ad97. The page reports what was tested, recommends taking both commits, and holds a draft reply to Isaac and draft edits of the PR description. Nothing has been pushed or posted.
This is the THIRD version of the page. Two review rounds (157 and 113 points) are already applied. An older version is at ${V2}; a text diff of the two files shows what changed. Your job is a last confirmation. Report only real defects: a statement that is wrong or not supported, a broken rule, a contradiction, or a sentence a first reader cannot follow. Do not report matters of taste, and do not repeat what the page already handles. If an area is clean, say so in checked_ok.

Material:
- A plain-text export of the page: python3 -B /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/page-tools/html2text.py ${PAGE} <out.txt> (write into your own scratch folder).
- Records of the test runs: ${RES}/ (results.txt is the summary) and their README /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/README.md. Inputs: ${RES}/inputs/ (Isaac's comment, the description of PR 5606, its diff, the live description of PR 5022).
- Source: git worktree ${WT} (branch at ddf843ad97, do not modify, run Python with -B). The commits of PR 5606 and of PR 5572 (882e5322f1) are present, and origin/main is at 0e37695a12.
- Description draft and builder: /home/jhan/workspace/intel-AMX/muse-glimmer/round2-tools/pr5022-body-after-5606.draft.md and apply_body.py.
- Earlier round: /home/jhan/workspace/intel-AMX/muse-glimmer/status/handoff-pr5022-20261120.md, posted replies in /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/md/.
- The user's memory notes: ${MEM}/ (index MEMORY.md).

HARD RULES
- Do not edit the page or any file outside your own scratch folder, which must be a new folder under /tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/db5d90b8-2c02-4aa1-b9df-6b564487154c/scratchpad/. Every shell redirect must use an absolute path inside that folder. Never write into /home/jhan/workspace/intel-AMX/muse-glimmer or the worktree.
- GitHub is read-only: gh may only read. No post, comment, label, push, rerun, dispatch.
- Do not log in to any lab machine. Do not message other agents or spawn agents.
- Quote the exact phrase of the page for each finding (it must occur in the HTML source), and give the exact replacement text.
`

const SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['wrong-fact', 'rule-violation', 'unclear', 'missing', 'style'] },
          phrase: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['id', 'severity', 'phrase', 'problem', 'fix'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'findings'],
}

const LENSES = [
  {
    key: 'facts',
    prompt: `${CTX}
YOUR LENS: fact check of everything that changed since the older version, and of every number the page states about itself.
1. Make a text diff of the old and the new page (html2text on both). Check every new or changed sentence against the records, the inputs, the source at 90a9110be5 and read-only GitHub data. The largest new parts are: the table "Findings that stay open after a go" (5 rows), the list "The registry rows: four routes", the list "The kernel test: two candidates", the eleven steps with the bullets under them, the reply draft, the description edits (7 rows and 10 bullets), section 8, section 5, row 17 of the claims table, and the references R10 to R25.
2. For the registry routes, verify each statement yourself: the one-class practice (run your own count over git log --first-parent --since 2026-10-15 origin/main -- config/test-benchmarks.json and say what you count), the check rule in bin/slice, the remote command and its preconditions in doc/distributed-dice-agent-guide.md, the inputs and the job limit of .github/workflows/bench-refresh.yml, the durations of the last three weekly runs and of the dry run of PR 5278 (gh run view), the commits that wrote the two current rows (git blame on lines 152 and 495 of config/test-benchmarks.json at 90a9110be5), the 16 MB and 10% rule in bin/ci/bench_refresh.py, the state and dates of pull requests 5037, 5038, 4515, 4516, 4672 and 4674, and the count of 35 days.
3. For the kernel test, verify: the assertion counts 2,560 and 6,671 and the difference 4,111 (records), which test cases sit inside the guard of t/t_amx_numerics.cpp, that the eligibility case holds compile-time checks only, what the pack case needs to link (where is the pack function defined, and is that file compiled with the option OFF?), and whether candidate 1 and candidate 2 are described truthfully as hypotheses. Say plainly if a candidate cannot work as described.
4. For section 8, verify the wording of the two clauses against is_dense_amx_page, how apply_page_tok computes begin and end, how the test helper builds the page and the visible range, and the two sketched sections plus the one-line variant.
5. For the reply draft and the description edits: every sentence against a record or a run; the two links; the word counts (1,996 live, 1,998 draft, 1,999 without row 6, 1,996 without the attempt number) by running apply_body.py into your scratch folder and wc -w.
6. Counts the page states about itself: 46 entries in the word list, 17 claims with 14 verdicts, eleven steps, five steps that write to GitHub (are steps 2, 3, 6, 9 and 10 the writing ones?), seven replacements, four routes, two candidates, 25 references, 9 + 6 + 5 agents with 40, 157 and 113 points (the journals are under /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-muse-glimmer/db5d90b8-2c02-4aa1-b9df-6b564487154c/subagents/workflows/: wf_bcf5d3ff-636, wf_04c376be-65d, wf_c467671d-862).
Report only statements that are wrong, unsupported, or stated as fact while only expected.`,
  },
  {
    key: 'plain',
    prompt: `${CTX}
YOUR LENS: plain English, by reading. Load the skill "plain-english-experiment" (Skill tool) and apply it in Check mode to all prose of the page: paragraphs, bullets, the word list, table cells, captions and the reply draft. Its length script (scripts/check_lengths.py in the skill folder) prints nothing for this page; run it once to confirm, and do not count the lengths of paragraphs and bullets again. Check what the script cannot see:
- Rule 1: idioms, metaphors, wordplay, uncommon words.
- Rule 2: two unrelated claims in one sentence, or short simple sentences split without need.
- Rule 3 in table cells and captions (the script skips them): more than 25 words, a semicolon, a clause inside another clause.
- Rule 4: a bullet that starts with an added label, more than three sentences in a table cell, a list that should be prose or the reverse.
- Rule 5: a file and line reference in the body where the line is not the subject, a citation mark that does not follow a sentence.
- Rule 6: a number without a unit, an estimate without "est.", a parenthesis of more than 8 words in a cell.
- Rule 8: a code name, abbreviation, metric or project term that is used before it is defined and is not in the word list (46 entries), or one term with two meanings. New text to read with most care: the table "Findings that stay open after a go", the lists "The registry rows: four routes" and "The kernel test: two candidates", the bullets under the eleven steps, section 8, and the reply draft. The reply draft is posted on GitHub without the word list, so every term in it must be clear to the reviewer by itself.
The quotes (class "quote") and the code blocks are not our prose; skip them. Return each real violation with the rule number, the exact phrase and the exact corrected text. Run your corrected texts through the length script before you return them. Report zero plainly where a rule has no violation. Do not invent violations, and do not report a point that only restates a preference.`,
  },
  {
    key: 'posted',
    prompt: `${CTX}
YOUR LENS: the decision the user must take, and the two texts that will be posted. Read first: ${MEM}/declined-fix-leaves-finding-open.md, ${MEM}/review-replies-keep-simple.md, ${MEM}/changes-need-system-tests.md, ${MEM}/isaac-reviews-are-agent-pipeline.md, and section 4 of the handoff file.
1. The reply draft of section 7. Read it as Isaac's review agents will: they re-run commands and re-read files of the repository. For each sentence: true at posting time, supported by which record or run, and will they contest it? Test every sentence that gives or implies a reason. Is the pair of bullets on the rows of config/test-benchmarks.json the best honest answer under the user's rules (the simplest reply, no promise of later work, no word that grades our own work down, no mention of issue 3997)? Does the sentence about the weekly refresh read as a promise, and is it true (check git blame of lines 152 and 495 of config/test-benchmarks.json at 90a9110be5, and the workflow file)? Give a better version only if it is clearly better, with reasons.
2. The table "Findings that stay open after a go" and the two lists under it. For each row: is the finding stated without the fix, is the smallest fix really the smallest that the repository offers, is the example real, and is the proposal a fair default for a user who wants the simplest change and no untested additions? Does any row still judge the reviewer's named fix instead of the goal? Is any open finding of this pull request missing from the table?
3. The eleven steps and the bullets under them: is every fact that the reply and the description state collected by an earlier step, does every write to GitHub appear as a step, and is the failure branch complete?
4. The first screen (Short version, state table, the box with the question): can the user decide from it plus the two tables of section 6? Is the question clear, and is it clear what one go covers?
5. Consistency of the whole page: the same count and the same name everywhere (eleven steps, seven replacements, four stale places, four routes (a) to (d), two candidates, 46 entries, 17 claims, 25 references), and every "section N", "step N", "row N", "route (x)", "first list below", "second list below" pointing at the right thing.
Report only real defects, with exact replacement texts.`,
  },
]

const results = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `confirm:${l.key}`, phase: 'Confirm', schema: SCHEMA }).then(r => ({ key: l.key, result: r }))
))
const got = results.filter(Boolean)
if (got.length < LENSES.length) log(`${LENSES.length - got.length} reviewer(s) returned nothing`)
return got
