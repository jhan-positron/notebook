export const meta = {
  name: 'round2-page-final-check',
  description: 'Final check of the revised reply page: facts, the declined-fix lesson, plain English by reading, the reply text, and consistency',
  phases: [
    { title: 'Final check', detail: 'five independent reviewers of the revised page' },
  ],
}

const PAGE = '/home/jhan/workspace/intel-AMX/muse-glimmer/round2-respond-2-issac.html'
const RES = '/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123'
const WT = '/home/jhan/workspace/ai-runs/tron-glimmer-amx'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-muse-glimmer/memory'

const CTX = `
CONTEXT
The page ${PAGE} is a report for the user jhan. It answers a reviewer's follow-up on pull request 5022 of the GitHub repository positron-ai/tron. The reviewer Isaac (GitHub login ishapira-positron) left one conversation comment and opened draft PR 5606 with two commits (c6cba6b0f8, then 90a9110be5) on top of the PR head ddf843ad97. The page reports what was tested, recommends taking both commits, and holds a draft reply to Isaac and draft edits of the PR description. Nothing has been pushed or posted. This is the SECOND version of the page: a first review round of six agents reported 157 points, and the page was rewritten and then patched. Your job is the final check of this version.

Material:
- The page itself. A plain-text export: python3 -B /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/page-tools/html2text.py ${PAGE} <out.txt> (write into your own scratch folder).
- Records of the test runs: ${RES}/ (results.txt is the summary; tests-*.txt, mutations*.txt, symbols-*.txt, bincmp-off-on-S2.txt, compile-commands-*.txt, wall-times-off.txt, load-snapshot-*.txt, registry-check.txt). README of the run: /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/README.md.
- Inputs: ${RES}/inputs/ (comment-7118448228.md is Isaac's comment, pr5606-body.md the description of PR 5606, pr5606.diff its diff, pr5022-body-live.md the live description of PR 5022).
- Source: git worktree ${WT} (branch at ddf843ad97). The commits of PR 5606 are fetched, so \`git -C ${WT} show 90a9110be5:<path>\` works. origin/main is fetched at 0e37695a12.
- Description draft and its builder: /home/jhan/workspace/intel-AMX/muse-glimmer/round2-tools/pr5022-body-after-5606.draft.md and apply_body.py in the same folder.
- Earlier round: /home/jhan/workspace/intel-AMX/muse-glimmer/status/handoff-pr5022-20261120.md and the posted replies in /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/md/.
- The user's memory notes: ${MEM}/ (index MEMORY.md).
- Journals of the earlier agent runs: /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-muse-glimmer/db5d90b8-2c02-4aa1-b9df-6b564487154c/subagents/workflows/wf_bcf5d3ff-636/journal.jsonl (9 agents: build, readers, skeptics) and wf_04c376be-65d/journal.jsonl (6 reviewers of the first version).

HARD RULES
- Do not edit the page or any file outside your own scratch folder (a folder under /tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/db5d90b8-2c02-4aa1-b9df-6b564487154c/scratchpad/). Never write into /home/jhan/workspace/intel-AMX/muse-glimmer or the worktree. When a shell command redirects output, use an absolute path in your scratch folder. You return findings. Another agent applies them.
- GitHub is read-only: \`gh\` may only read. No post, comment, label, push, rerun, dispatch.
- Do not modify the worktree ${WT}. Run Python with -B there. Do not log in to any lab machine. Do not message other agents or spawn agents.
- Report only real problems. Quote the exact phrase of the page for each finding, so it can be found with a text search. Give the exact replacement text. If you find nothing in an area, say so. Do not repeat points that the page already handles.
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
    key: 'facts',
    prompt: `${CTX}
YOUR LENS: fact check of the whole page, with most care for text that is new in this version. Check every number, name, date, time, commit id, PR number, line number, quoted text and every statement about what a file or tool does, against the records, the inputs, the source at 90a9110be5 and read-only GitHub data. Recompute what can be recomputed.
New or changed in this version, so check each of these fully:
- The status table (state on 2026-11-24, 08:50 PST) and the box under it (ten steps, what one go covers).
- The word list (44 entries): is each definition correct for this project? Check the new entries against the code: Query head and KV head, Kernel and pack, KV page and dense page, Eligible and available(), Sliding window, v_star and s_star, Real cases, Registration line, Granite Rapids, Git tree, Trial merge, Loaded section, Model type and symbol, Machine class, MiB and MB (how does bin/slice fill max_rss_mb?), Earlier round, Agent.
- Section 1: the four quotes from the PR 5606 description and the sentence that says which three come from its list "Heads-up" (is that true of the saved description?).
- Section 3: the paragraph on the preset, the one-definition paragraphs, the sentence "With the option ON the two commits change no compiled line", the cost table (registry times per class) and the load bullets.
- Section 4: the intro sentence with "13 of the 16 claims", and rows 3, 7, 8, 9, 12, 13, 14.
- Section 5: the bullets on the model flags, on the hardening flags and the standard library, and on draft PR 5572 (does it change the same test file under the same guard?).
- Section 6: the bullet on the Lint job, the ten steps, the two tables, the list of four routes for the registry rows (is each statement about bin/slice bench --remote, about bench-refresh.yml, about its dry run, its 120 minute limit, the 10% rule and pull requests 5037 and 5038 true?), and the hypothesis about PR 5606 being shown as merged.
- Section 7: every sentence of the reply draft; the link in it (does the thread discussion_r4356061343 hold our reply of 2026-11-20 about bin/slice bench?); the table of seven description edits against apply_body.py and the draft file (before texts, after texts, word changes, total 1,997 by wc -w); the eight bullets under the table.
- Section 8: the two clauses (read is_dense_amx_page and how apply_page_tok computes begin and end, and how the test builds its page and its visible range), the two commit ids, the statement about the 16-head partial-page section, and the sketch of a fix (is each of the two proposed sections a state the test helper could build? say so if not).
- Section 9 and section 10 (the counts 9 agents, 48 minutes, 40 findings as 27, 10, 2 and 1, 25 notes, 6 reviewers, 157 points).
- References R1 to R23: every path exists, every cited line range holds what the page says at the stated commit.
Flag any statement that the records do not support, any number without a unit, any estimate without "est.", and any place where the page states as fact something that is only expected.`,
  },
  {
    key: 'lesson',
    prompt: `${CTX}
YOUR LENS: the lesson "a declined fix leaves the finding open". Read ${MEM}/declined-fix-leaves-finding-open.md first, and ${MEM}/review-replies-keep-simple.md, ${MEM}/changes-need-system-tests.md and section 4 of the handoff file. The lesson was written on 2026-11-23 after this same pull request: a gap was reported five times, each time we judged the fix that the reviewer named and not the goal, and a narrower fix with a sibling example in the same file was missed.
Apply the lesson to the page as a checklist:
1. List every point on the page where we decline, postpone or leave something: the registry rows, the define that the test file does not name, the comment in amx_attn_iface.hpp, fault m04, the real-AMX run in required CI, the run of the required lane before the push, the merge of main, the Debug presets, the third machine class, and any other you find. For each: does the page state the finding without the fix, say whether the proposal closes it, give the reason as a condition on any fix, and name the narrowest fix that meets the condition?
2. For each declined point, search the repository yourself for a narrower fix and for a sibling example (the same problem solved elsewhere in the same file or folder). Use grep on the tree at 90a9110be5, for example on t/CMakeLists.txt, t/*.cpp, config/test-benchmarks.json history (git log -p --follow on the two rows, and how rows of other tests were refreshed: by whom, by which kind of commit), bin/slice bench options (is there a way to measure one test on the current host half only, an option such as --slots, --instance or --no-calibration?), .github/workflows. Report every narrower fix or example that the page does not have. Say plainly when you find none.
3. Test every sentence of the page and of the reply draft that has the form "X needs Y", "X cannot", "only if", "must", "no ... can", or that gives a reason for not doing something. Is the sentence true? Is the reason a fact or a habit? Example of the failure to look for: "running the cases in required CI needs the Nix flag" was false.
4. Does the page pass any point on as settled, in words such as "do not reopen", "decided", "as you decided", in a way that could hide an open finding from the user? The mention of issue 3997 is one such place: check whether the page still shows the finding itself.
5. The reply draft: does its last bullet state the open finding honestly? Would Isaac's review agents, which read t/AGENTS.md and the repository documents, find a documented route that the reply ignores? Give the best version of that bullet under the user's rules (simplest, no promise, no word that grades our work down).
6. Draft PR 5572 of the same author has the same kind of gap (see the memory note). Does the page say enough about it for the user to act?
Return findings with exact replacement texts.`,
  },
  {
    key: 'plain',
    prompt: `${CTX}
YOUR LENS: plain English, by reading. Load the skill "plain-english-experiment" (Skill tool) and apply it in Check mode to all prose of the page: the paragraphs, the bullets, the word list, the table cells, the figure captions and the reply draft. Its length script (scripts/check_lengths.py in the skill folder) prints nothing for this page, so do not count the sentence lengths of paragraphs and bullets again. Check what the script cannot see:
- Rule 1: idioms, metaphors, wordplay, uncommon words. Would a non-native English speaker with an engineering degree have to guess?
- Rule 2: a sentence that carries two unrelated claims, or a test with its observation and its meaning. Also short simple sentences that were split without need.
- Rule 3 inside table cells and captions, which the script skips: a sentence of more than 25 words, a semicolon, a clause inside another clause.
- Rule 4: a bullet that starts with an added label. A list that should be prose or the reverse. More than three sentences in one table cell.
- Rule 5: a file and line reference in the body where the line is not the subject. A citation mark that does not follow a sentence.
- Rule 6: a number without a unit. An estimate without "est.". A parenthesis of more than 8 words in a table cell.
- Rule 8: walk the page from top to bottom. List every code name, abbreviation, metric or project term that is used before it is defined and that is not in the word list (44 entries). Check that each term has one name everywhere. Check the term list of /home/jhan/workspace/intel-AMX/CLAUDE.md for definitions that must be reused.
The quotes (class "quote") and the code blocks are not our prose; skip them. The reply draft (class "reply") is our prose and will be posted on GitHub, where the word list is not present: every term in it must be clear to the reviewer without the page.
Return each violation with the rule number, the exact phrase and the exact corrected text. Report zero plainly where a rule has no violation. Do not invent violations.`,
  },
  {
    key: 'reply',
    prompt: `${CTX}
YOUR LENS: the two texts that will be posted, as their reader will see them. Read ${MEM}/review-replies-keep-simple.md, ${MEM}/isaac-reviews-are-agent-pipeline.md, ${MEM}/tron-pr-post-replies-as-one-review.md and section 4 of the handoff file first.
1. The reply draft of section 7. Turn it into GitHub markdown the way /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/to_markdown.py does (read that script; one paragraph per line, code in backticks, links as markdown). Save your markdown in your scratch folder and put its full text into one finding's fix field with the id REPLY-MD. Then judge it as Isaac's review agents will read it: they will re-run commands and re-read files. For each sentence: is it true at the time it is posted (after the push and after both CI runs), and which record or run supports it? Which sentence will they contest? Is any sentence not needed? Is any sentence missing for them to accept the change and clear "changes requested"? Check the user's rules: the simplest reply, no promise of later work, no word that grades our own work down ("only", "just", "merely", "I accept"), no mention of issue 3997. Check the placeholders: each name, where its value comes from, and whether the page's steps collect that value.
2. The seven description edits. Apply them yourself to a copy of ${RES}/inputs/pr5022-body-live.md and compare with the draft file. Read the whole draft description as a reviewer who has only that text: after the edits, is every sentence of its Verification section and its Open items true for the head 90a9110be5, and does any other sentence of the description become false or stale that the seven edits do not touch? Count the words with wc -w. Check that the placeholders in the draft are single words, and say what the count becomes if "attempt ATTEMPT_N" is dropped.
3. The order of the steps in section 6 against what the two texts need: is every fact that the texts state collected by a step before the text is posted? Is anything posted before its evidence exists?
Return findings with exact replacement texts.`,
  },
  {
    key: 'consistency',
    prompt: `${CTX}
YOUR LENS: a careful first reader, and a consistency check of this second version. Read the page from top to bottom once, as an engineer who has never seen this project, before you open any other file. Write down every place where you had to guess, re-read, or scroll to follow the text. Then check:
1. Counts and names that appear in more than one place: 20 test runs, 4 builds, 15 fault runs, 10 faults with 9 caught, 44 terms, ten steps, seven replacements, four stale places, two tables in section 6, four routes named (a) to (d), 23 references. Do all places agree? Does every "step N", "row N", "route (x)", "section N" and "the table below" point at the right thing after the rewrite?
2. Contradictions between sections: the Short version, the box under it, section 5, the two tables of section 6, the list of routes, the reply draft, the description edits, section 8 and section 9 must tell one story. Example to test: what the reply says about the registry rows against what the routes list and the description edit 7 say.
3. The first screen: is the recommendation clear, is it clear what one go covers and what it does not cover, and can the user decide from the first screen plus the two tables of section 6?
4. Anything important for the user's decision that is still missing: a risk, a cost, an alternative, a step, a failure branch.
5. The two figures and the bar chart: read the SVG and HTML source. Do labels overlap or leave the viewBox (average glyph width 0.55 times the font size)? Do the captions and takeaways read correctly on their own? Is the bar chart's label column wide enough for its longest label at 13px (the column is 340px)?
6. The page as HTML: links that go nowhere, an id used twice, a reference that is cited but does not support the sentence that cites it. The structure check /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/page-tools/check_html.py may be run (it only reads).
Return findings with the exact phrase and the exact replacement text.`,
  },
]

const results = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `final:${l.key}`, phase: 'Final check', schema: SCHEMA }).then(r => ({ key: l.key, result: r }))
))
const got = results.filter(Boolean)
if (got.length < LENSES.length) log(`${LENSES.length - got.length} reviewer(s) returned nothing`)
return got
