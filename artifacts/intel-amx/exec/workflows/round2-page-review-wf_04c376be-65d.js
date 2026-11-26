export const meta = {
  name: 'round2-page-review',
  description: 'Review the reply page: fact check against the records, plain-English check by reading, the user rules for replies, and a newcomer read',
  phases: [
    { title: 'Review', detail: 'six independent reviewers, each with one lens' },
  ],
}

const PAGE = '/home/jhan/workspace/intel-AMX/muse-glimmer/round2-respond-2-issac.html'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123'
const WT = '/home/jhan/workspace/ai-runs/tron-glimmer-amx'

const CTX = `
CONTEXT
The page ${PAGE} is a report for the user jhan. It answers a reviewer's follow-up on pull request 5022 of the GitHub repository positron-ai/tron. The reviewer Isaac (GitHub login ishapira-positron) left one conversation comment and opened draft PR 5606 with two commits (c6cba6b0f8, then 90a9110be5) on top of the PR head ddf843ad97. The page reports what was tested, recommends taking both commits, and holds a draft reply to Isaac and draft edits of the PR description. Nothing has been pushed or posted.

Material:
- The page itself. A plain-text export can be made with: python3 -B /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/page-tools/html2text.py ${PAGE} <out.txt> (write the output into your own scratch folder).
- Records of the test runs: ${RES}/ (results.txt is the summary; tests-*.txt, mutations*.txt, symbols-*.txt, bincmp-off-on-S2.txt, compile-commands-*.txt, wall-times-off.txt, load-snapshot-*.txt, registry-check.txt). README of the run: /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/README.md.
- Inputs: ${RES}/inputs/ (comment-7118448228.md is Isaac's comment, pr5606-body.md the description of PR 5606, pr5606.diff its diff, pr5022-body-live.md the live description of PR 5022).
- Source: git worktree ${WT} (branch at ddf843ad97). The commits of PR 5606 are fetched, so \`git -C ${WT} show 90a9110be5:<path>\` works.
- Description draft and its builder: /home/jhan/workspace/intel-AMX/muse-glimmer/round2-tools/pr5022-body-after-5606.draft.md and apply_body.py in the same folder.
- Earlier round: /home/jhan/workspace/intel-AMX/muse-glimmer/status/handoff-pr5022-20261120.md and the posted replies in /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/md/.

HARD RULES
- Do not edit the page or any file outside your own scratch folder. You return findings. Another agent applies them.
- GitHub is read-only: \`gh\` may only read. No post, comment, label, push, rerun.
- Do not modify the worktree ${WT}. Do not log in to any lab machine. Do not message other agents or spawn agents.
- Report only real problems. Quote the exact phrase of the page for each finding, so it can be found with a text search. Give the exact replacement text. If you find nothing in an area, say so.
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
          phrase: { type: 'string', description: 'the exact phrase on the page (copy it), or the section name when something is missing' },
          problem: { type: 'string' },
          evidence: { type: 'string', description: 'file:line, record line or command output that shows the problem' },
          fix: { type: 'string', description: 'the exact replacement text' },
        },
        required: ['id', 'severity', 'phrase', 'problem', 'fix'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' }, description: 'areas or statements you checked and found correct' },
  },
  required: ['summary', 'findings'],
}

const LENSES = [
  {
    key: 'facts-tests',
    prompt: `${CTX}
YOUR LENS: fact check of the page sections "Short version", the status table under it, "1. What arrived", "2. The fix as a diff" and "3. What the tests show" (including both figures, every table, the bars and every bullet).
Check every number, name, date, time, commit id, line number and quoted text against the records, the inputs and the source. Examples of what to verify: the quotes of Isaac are word for word from his comment and from the PR 5606 description; the diff blocks equal \`git diff ddf843ad97 c6cba6b0f8\` and \`git diff c6cba6b0f8 90a9110be5\` with the right old and new line numbers; the counts of runs, builds and fault runs; every assertion count and exit code; the positions in the dumbbell chart (the scale is 460 SVG units for 32,000 assertions, starting at x=250); the fault table against mutations.txt (line numbers, what each fault does, exit codes, sections that fail, first failed check); the compile-command counts; the binary compare; the symbol counts; wall time and memory; the load figures; the sentence about the three library files; the statement that 14 commits separate main from the head. Recompute what can be recomputed. Flag any statement that the records do not support, any number without a unit, and any estimate that is not marked "est.".`,
  },
  {
    key: 'facts-plan',
    prompt: `${CTX}
YOUR LENS: fact check of the page sections "4. Isaac's claims, one by one", "5. What is still open", "6. My proposal" (the steps and the table of choices), "7. Reply draft and description edits", "8. Found on the way", "9. Not covered", "10. How this was checked" and "References".
Check every statement against the records, the inputs, the source at 90a9110be5 and read-only GitHub data. Examples: each row of the claims table (is the claim quoted fairly from Isaac's comment or the PR 5606 description, and is the verdict supported); the reference list (does every path exist, does every cited line range hold what the page says, at the stated commit); the durations in the steps (33 minutes, 41 minutes, 16 minutes: find their source in the handoff file); the table of choices (is each "reason" true; is the route \`bin/slice bench --remote --update\` real; does a manual start of gcp-nix.yml on a branch exist); every sentence of the reply draft (true, and supported by a record); the seven description replacements (apply_body.py and the draft file: are the "before" texts exact, are the word deltas right, is 1,998 the result of \`wc -w\`); section 8 (the two clauses, the commit b431585224, whether the predicate and the partial-page section are on main); the counts in section 10 (9 agents, 48 minutes, 40 findings, 25 notes: the journal is /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-muse-glimmer/db5d90b8-2c02-4aa1-b9df-6b564487154c/subagents/workflows/wf_bcf5d3ff-636/journal.jsonl). Flag any statement that is not supported, any promise of future work in the reply draft, and any place where the page states as fact something that is only expected.`,
  },
  {
    key: 'plain-words',
    prompt: `${CTX}
YOUR LENS: plain English, by reading. Load the skill "plain-english-experiment" (Skill tool) and apply it in Check mode to the prose of the page. Its length script (scripts/check_lengths.py in the skill folder) already prints nothing for this page, so do not count sentence lengths again. Concentrate on what a script cannot see:
- Rule 1: idioms, metaphors, wordplay, uncommon words. Test each doubtful word: would a non-native English speaker with an engineering degree have to guess?
- Rule 8: every code name, abbreviation, metric and project term is defined at first use or in the "Words used here" list. Walk the page top to bottom and list every term a newcomer meets that is not defined (examples to test: Nix, CMake, lint, sha256, link line, object file, translation unit, preset, RelWithDebInfo, Granite Rapids, Xeon 6962P, QK, PV, pack, KV head, registry class names, model type, class template, symbol, build ID, GCP, conversation comment, review thread, draft PR, trial merge, tree hash, Muse Glimmer, kv_mul 8, #5511). Say for each whether an inline clause of at most 8 words or a new entry in the word list is the better fix, and give the text. Also check the word list itself: is each definition correct and no longer than three sentences, and does it reuse the term list of /home/jhan/workspace/intel-AMX/CLAUDE.md where a term is in that list?
- A clause that sits inside another clause.
- A bullet that starts with an added label.
The quotes of Isaac (class "quote") and the code blocks are not our prose; skip them. The reply draft (class "reply") is our prose and will be posted on GitHub: check it with the same care.
Return each violation with the rule number in the problem text.`,
  },
  {
    key: 'plain-structure',
    prompt: `${CTX}
YOUR LENS: plain English, by reading, second half. Load the skill "plain-english-experiment" (Skill tool) and apply it in Check mode to the prose of the page. Its length script already prints nothing for this page, so do not count sentence lengths again. Concentrate on:
- Rule 2: one claim per sentence. Find sentences that carry a test, an observation and a meaning together, or two unrelated claims. Also find the opposite defect that the skill names: short, simple sentences about one subject that were split without need, so that the text reads choppy.
- Rule 4: three or more sentences in a row that each cover a different aspect of one thing and should be a list; a list that should be prose; a numbered list where order does not matter, or bullets where it does.
- Rule 5: every citation index follows a sentence that carries the claim; none stands alone; file and line references are in the reference section and not in the body (the tables may name a line number where the line is the subject).
- Rule 6: every number has a unit and, where the reader cannot judge it, a plain meaning of at most 8 words. Estimates carry "est.". Look at the tables and the figure texts too.
- Rule 7: the "Short version" has at most three sentences, and a newcomer can follow each without the rest of the page.
- Table cells: the length script skips them. Read every cell and flag a cell whose sentence has more than 25 words, a semicolon, or a parenthesis of more than 8 words.
- Consistency of wording: the same thing must have the same name everywhere (for example "required lane", "the define", "guarded blocks", "dispatch test", "source state").
The quotes of Isaac (class "quote") and the code blocks are not our prose; skip them. The reply draft (class "reply") is our prose and will be posted on GitHub: check it with the same care.
Return each violation with the rule number in the problem text.`,
  },
  {
    key: 'user-rules',
    prompt: `${CTX}
YOUR LENS: the user's own rules for review replies and for reports. Read these files first; they hold the rules in the user's words:
- /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-muse-glimmer/memory/review-replies-keep-simple.md
- .../memory/changes-need-system-tests.md
- .../memory/review-reply-edits-as-diffs.md
- .../memory/no-issue-numbers-in-source.md
- .../memory/isaac-reviews-are-agent-pipeline.md
- .../memory/tron-pr-push-triggers-bot-review.md
- .../memory/tron-pr-post-replies-as-one-review.md
- .../memory/delphi-3b35-no-slice-bench.md
- /home/jhan/workspace/intel-AMX/muse-glimmer/status/handoff-pr5022-20261120.md (section 4, "jhan's rules that stay in force", and the list of settled decisions)
- /home/jhan/.claude/CLAUDE.md and /home/jhan/workspace/intel-AMX/CLAUDE.md
Then judge the page, and above all the reply draft, the description edits, the proposal and its steps:
1. Is the reply the simplest reply that answers Isaac? Name every sentence that could go without loss, and every sentence that is missing for him to accept the change. Give a shorter version if one exists.
2. Does the reply use words that grade our own work down ("only", "I accept", "merely", "just"), promise later work, or mention issue 3997?
3. Does anything in the proposal reopen a settled decision, widen the scope of the PR, or skip a step the handoff requires (tests on delphi-3b35 before the go, the go before any commit, push or post, the CMake workflow by hand, the re-read of reviews after a push, the description under 2,000 words)?
4. Does the page ask the user for a decision that the user already made, or fail to ask for one that is the user's to make? Is the one question clear?
5. Does the page follow the user's report rules: a light background, a "Short version" first, a chart for the quantitative results with direct labels and a one-line takeaway, exact numbers in a table, estimates labelled "est.", system load reported with the timing figures, "Insufficient data" where a measurement is missing, and "prompt N" never "ctx N"?
6. Is any private detail of the user on the page that would be a problem if the reply text is posted (the reply text only)?
Return findings; for the reply, put your full proposed text into the fix field of one finding.`,
  },
  {
    key: 'newcomer',
    prompt: `${CTX}
YOUR LENS: a careful first reader, and a completeness critic. Read the page from top to bottom once, as an engineer who has never seen this project, before you open any other file. Write down every place where you had to guess, re-read, or scroll to another section to follow the text. Then open Isaac's comment (${RES}/inputs/comment-7118448228.md) and the description of PR 5606 (${RES}/inputs/pr5606-body.md) and check completeness:
1. Is every point of his comment and every bullet of the PR 5606 description answered somewhere on the page? List each point and where the page answers it, and flag the ones that are not answered.
2. Does the page contradict itself anywhere (for example counts that differ between sections, "four places" against "seven replacements", section numbers in cross references, the date of the tests)?
3. Does every cross reference ("section 6", "section 7", "section 8", "the table below") point at the right place?
4. Is the recommendation clear in the first screen, and is it clear what happens after the user says go and what does not happen?
5. Is anything important for the user's decision missing: a risk, a cost, an alternative, a step?
6. Do the two figures read correctly on their own (title or caption, axis, labels, takeaway)? Render check by reading the SVG source: do any text elements overlap or leave the viewBox (compute from the x, y and text-anchor values and an average glyph width of 0.55 times the font size)?
Return findings with the exact phrase and the exact replacement text.`,
  },
]

const results = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `review:${l.key}`, phase: 'Review', schema: SCHEMA }).then(r => ({ key: l.key, result: r }))
))
const got = results.filter(Boolean)
if (got.length < LENSES.length) log(`${LENSES.length - got.length} reviewer(s) returned nothing`)
return got
