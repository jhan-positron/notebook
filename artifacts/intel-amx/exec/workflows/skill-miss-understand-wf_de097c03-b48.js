export const meta = {
  name: 'skill-miss-understand',
  description: 'Analyse why five review skills missed the CI-lane test gap of tron PR 5022: skill text, session history, repository facts, reviewer method',
  phases: [
    { title: 'Analyse', detail: 'four skill analysts, two history readers, one repository reader, one reviewer-method reader' },
    { title: 'Verify', detail: 'a skeptic re-opens the cited sources of the history and repository reports' },
  ],
}

const R = '/home/jhan/workspace/ai-runs/skill-replay-20261123'
const A = '/home/jhan/workspace/ai-runs/skill-miss-analysis-20261123'
const WT = R + '/tron-ddf843ad97'
const WT_OLD = '/home/jhan/workspace/ai-runs/pr5022-isaac/tron-head'
const SNAP = R + '/pr5022-snapshot-20261120.md'
const FIND = A + '/finding.md'
const SKILLS = R + '/skills-baseline'
const BACKUP = '/home/jhan/workspace/ai-runs/skills-backup-20261119/claude'
const DRAFT = '/home/jhan/workspace/intel-AMX/muse-glimmer/review-checks-from-isaac-pr5022.draft.md'
const PAGE = A + '/respond-2-Isaac.txt'
const TR = '/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-muse-glimmer'

const COMMON = `
Background. These facts are established. Report anything you find that contradicts them.
- positron-ai/tron PR 5022 (author jhan-positron, branch jhan-amx-kvmul16) lets the AMX attention kernels serve kv_mul 16 (16 query heads per KV head). Final head: ddf843ad97. Commit of the first review: 4c4b7b8864.
- THE FINDING. At the head, t/t_amx_dispatch_dtype.cpp wraps all of its real test code in '#ifdef TRON_AMX_DISPATCH' and has an '#else' arm with one placeholder TEST_CASE that calls SUCCEED. The required CI lane (gcp-nix.yml) builds with that CMake option OFF. So the new 16-head dispatch checks of the PR execute in no required CI lane. The test uses CPU fake kernels and needs no AMX hardware.
- THE FIX that the reviewer offered on 2026-11-24 (PR 5606): register the test with its own compile definition, 'add_catch_test(NAME t_amx_dispatch_dtype DEFINES TRON_AMX_DISPATCH ...)', the way t_page_share_counters does (t/CMakeLists.txt:276 at the head), and delete the #ifdef/#else placeholder. With the option OFF the test then runs 30,747 assertions.
- HISTORY. The reviewer (Isaac, GitHub login ishapira-positron; an agent pipeline writes his reviews) raised the gap on 2026-10-23 with another fix: turn the option ON in the Nix build. claude[bot] raised the gap again on 2026-11-20 with that same fix. Our side declined that fix, because the flag would change what every model test of the required lane exercises. Our side fixed the stale comment and README text and ran the legacy workflow by hand. Nobody on our side proposed the per-target define.
- Our five review skills: ben-review, cpp-coding-guide, folks-code-review (named Wade-code-review until 2026-11-19), positron-code-review, tron-code-review. Three of them were edited on 2026-11-19 with lessons from Isaac's first review.

Files:
- Finding and fix, verbatim: ${FIND}
- PR page as of 2026-11-20 (description, reviews, all threads and replies): ${SNAP}
- Code at the final head: git worktree ${WT}
- Code at the first reviewed commit: git worktree ${WT_OLD}
- The five skills as they stand today (frozen copy): ${SKILLS}/<name>/
- Three skills before the 2026-11-19 edit: ${BACKUP}/ (cpp-coding-guide, tron-code-review, Wade-code-review)
- Draft of checks distilled from Isaac's first review, with a status note on what went into which skill: ${DRAFT}
- Text form of the page on which every reply of review round 2 was drafted and decided (cards I1-I26, T0-T13, B1-B2, D1-D6): ${PAGE}

Rules: read-only. Do not edit, build, run tests, push, post, or use the network (no gh, no curl). Never run 'git worktree prune'. Use 'git -C <path>' and full paths; do not cd. Every claim you return needs a source: a file path with a line number and a short verbatim quote, or a command with its output. Where you find no evidence, say so in the field made for that. Do not fill a gap by inference.
`

const THREE = `
Keep three questions apart for each skill:
- DETECT: does the skill text make a reviewer notice that the new test sections execute in no required CI lane (a compile-time guard on a build option, with a placeholder case that passes)?
- ESCALATE: does it rate that as something to fix before the merge? Or as a wording or claim issue, a question, or nothing?
- REMEDY: does it lead the reviewer to a fix that makes the test run in the required lane without a change to the lane's global build flags? Examples: a compile definition for the one test target, or a search for how a sibling test in the same CMake file solved the same problem.
`

const SKILL_SCHEMA = {
  type: 'object',
  properties: {
    skills: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          skill: { type: 'string' },
          purpose_quote: { type: 'string' },
          in_scope_by_design: { type: 'string', enum: ['yes', 'partly', 'no'] },
          in_scope_reason: { type: 'string' },
          nearest_checks: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                check: { type: 'string' },
                location: { type: 'string' },
                quote: { type: 'string' },
                fires_at_first_reviewed_commit: { type: 'string', enum: ['yes', 'partly', 'no'] },
                fires_at_final_head: { type: 'string', enum: ['yes', 'partly', 'no'] },
                why: { type: 'string' },
                finding_and_remedy_it_prescribes: { type: 'string' },
              },
              required: ['check', 'location', 'quote', 'fires_at_first_reviewed_commit', 'fires_at_final_head', 'why', 'finding_and_remedy_it_prescribes'],
            },
          },
          detect: { type: 'object', properties: { verdict: { type: 'string', enum: ['yes', 'partly', 'no'] }, reason: { type: 'string' } }, required: ['verdict', 'reason'] },
          escalate: { type: 'object', properties: { verdict: { type: 'string', enum: ['yes', 'partly', 'no'] }, reason: { type: 'string' } }, required: ['verdict', 'reason'] },
          remedy: { type: 'object', properties: { verdict: { type: 'string', enum: ['yes', 'partly', 'no'] }, reason: { type: 'string' } }, required: ['verdict', 'reason'] },
          relevant_change_on_20261119: { type: 'string' },
          root_causes: { type: 'array', items: { type: 'object', properties: { cause: { type: 'string' }, evidence: { type: 'string' } }, required: ['cause', 'evidence'] } },
          proposed_edits: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                where: { type: 'string' },
                kind: { type: 'string', enum: ['new check', 'widen trigger', 'remove exclusion', 'new remedy', 'severity', 'procedure step', 'no change'] },
                draft_text: { type: 'string' },
                rationale: { type: 'string' },
                false_positive_risk: { type: 'string' },
              },
              required: ['where', 'kind', 'draft_text', 'rationale', 'false_positive_risk'],
            },
          },
        },
        required: ['skill', 'purpose_quote', 'in_scope_by_design', 'in_scope_reason', 'nearest_checks', 'detect', 'escalate', 'remedy', 'relevant_change_on_20261119', 'root_causes', 'proposed_edits'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['skills'],
}

const CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    answers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          question: { type: 'string' },
          answer: { type: 'string' },
          evidence: {
            type: 'array',
            items: {
              type: 'object',
              properties: { source: { type: 'string' }, locator: { type: 'string' }, quote: { type: 'string' } },
              required: ['source', 'locator', 'quote'],
            },
          },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['question', 'answer', 'evidence', 'confidence'],
      },
    },
    timeline: { type: 'array', items: { type: 'object', properties: { when: { type: 'string' }, what: { type: 'string' }, source: { type: 'string' } }, required: ['when', 'what', 'source'] } },
    not_found: { type: 'array', items: { type: 'string' } },
    lessons: { type: 'array', items: { type: 'string' } },
  },
  required: ['answers', 'not_found'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          question: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'partly', 'refuted', 'unverifiable'] },
          checked: { type: 'string' },
          correction: { type: 'string' },
        },
        required: ['question', 'verdict', 'checked', 'correction'],
      },
    },
    new_facts: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdicts'],
}

const skillTask = (names, extra) => `
Task: analyse why a review skill did not produce the finding and the fix described below, and draft the smallest edit that would make it produce them.
Skill(s) to analyse: ${names.join(', ')}. Return one entry in 'skills' for each.
${COMMON}
${THREE}
What to do:
1. Read each skill completely, from the first line to the last, in ${SKILLS}/<name>/. ${extra}
2. Where a pre-edit version exists in ${BACKUP}/, diff the two versions and report what the 2026-11-19 edit changed that bears on this finding.
3. Read ${FIND}. Read t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp and the registrations of both tests in t/CMakeLists.txt, in both worktrees. Read the three threads of the PR page that concern CI lanes: search ${SNAP} for r4356060700, r4356060885 and r4645384802.
4. State the skill's purpose with a quote, and decide whether this class of finding belongs to that purpose by design.
5. List the checks or rules of the skill that come nearest to the finding. For each one quote its trigger and its exclusions with a line number. Decide whether its trigger fires on the code at the first reviewed commit and at the final head, and why. Write down the exact finding and remedy the check prescribes when it fires.
6. Answer DETECT, ESCALATE and REMEDY for the skill, each with yes, partly or no and the reason.
7. Give the root causes of the miss in the skill text, each tied to a quoted line.
8. Draft edits. An edit must fit the form the skill already uses (its headings, and its pattern of trigger, procedure, exclusions and finding wording). An edit must be general: its trigger must not name the files of PR 5022. Describe a false positive that the edit must not produce. One known case: the kernel cases of t/t_amx_numerics.cpp need real AMX hardware and the kernel source file, so a per-target define cannot make them run. If the finding is outside the purpose of the skill, propose 'no change' and say which skill should own the check.
`

const TRANSCRIPTS = `
Session transcripts are JSON Lines files in ${TR}/ . Each line is one JSON object with 'type' (user, assistant, ...), 'timestamp' (UTC), 'isSidechain', and 'message.content'. The content is a string or a list of blocks: text blocks, tool_use blocks (name, input) and tool_result blocks. Subagent transcripts are in ${TR}/<session-id>/subagents/*.jsonl with a .meta.json beside each. Workflow runs are in ${TR}/<session-id>/workflows/. Large tool outputs are in ${TR}/<session-id>/tool-results/. Files reach 28 MB. Never print a whole file. Write short python3 scripts that scan line by line, parse the JSON, and print the timestamp, the type and a window of text around each match. Quote transcript evidence as: session id, line number, timestamp, and the words.
`

const TASKS = [
  {
    key: 'skill-tron-code-review',
    schema: SKILL_SCHEMA,
    verify: false,
    prompt: skillTask(['tron-code-review'], 'The file is SKILL.md, about 12.7 KB. Section "Tests" holds the mutation checks and the hardware-gate rule that came from Isaac\'s first review.'),
  },
  {
    key: 'skill-folks-code-review',
    schema: SKILL_SCHEMA,
    verify: false,
    prompt: skillTask(['folks-code-review'], 'SKILL.md is about 81 KB and holds 35 checks. references/procedures.md is about 107 KB and holds the step lists. Read SKILL.md whole. In procedures.md read at least the parts for checks 3A, 3B, 33, 34, 6, 7, 8, 12 and 35. Read references/pr4557-misses.md and the section "Replying to Wade" of SKILL.md. Checks that touch gated tests, CI lane claims, bot findings and declined fixes matter most. The pre-edit version is ' + BACKUP + '/Wade-code-review/.'),
  },
  {
    key: 'skill-cpp-coding-guide',
    schema: SKILL_SCHEMA,
    verify: false,
    prompt: skillTask(['cpp-coding-guide'], 'The file is SKILL.md, about 4.8 KB. It is a guide for writing code as well as for review, so also judge whether a rule for the author of a test file belongs in it.'),
  },
  {
    key: 'skill-ben-and-positron',
    schema: SKILL_SCHEMA,
    verify: false,
    prompt: skillTask(['ben-review', 'positron-code-review'], 'ben-review/SKILL.md is about 14.2 KB and positron-code-review/SKILL.md about 3.1 KB. Neither has a pre-edit version in the backup folder. Judge first whether the finding belongs to the stated purpose of each skill.'),
  },
  {
    key: 'history-october',
    schema: CLAIMS_SCHEMA,
    verify: true,
    prompt: `
Task: reconstruct from session transcripts and git history what our review skills did on tron PR 5022 BEFORE the first outside review (2026-10-23), and where the guarded test and the precedent for the fix came from.
${COMMON}
${TRANSCRIPTS}
Sessions of October and early November 2026 in that folder: 2286d13f-0c9b-4afd-a521-f1f97342a0e9 (starts 2026-10-16), 648b68dc-a925-47af-a6eb-b7586de6dc8b, 146c3a6e-a1e1-402b-a412-2cd6ec96fdfc, 198bf255-13d0-4111-94e8-6903ff46f117, ff60e929-f850-4014-9494-90108583a1a0 (all start 2026-10-18), c19a91bd-35ba-4b1c-8db4-368d54a84066 and f6259a56-887c-4ee5-b475-070898361d74 (start 2026-10-30). Other project folders under /home/jhan/.claude/projects/ may hold the sessions that wrote earlier AMX pull requests, for example -home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR0 and -home-jhan-workspace-intel-AMX-PR3879-new-PRs-CI-enable. Use them only for question 5.

Answer these questions, one entry in 'answers' for each:
1. Before 2026-10-23, which review skills were applied to the branch jhan-amx-kvmul16 or to PR 5022? Look for Skill tool calls (tool_use blocks named Skill, with input.skill), for skill names inside prompts given to subagents and workflows, and for the words Wade-code-review, tron-code-review, cpp-coding-guide, ben-review, positron-code-review. For each application give the timestamp, the scope it was given, and the findings it returned.
2. Did any of those applications say anything about (a) the '#ifdef TRON_AMX_DISPATCH' guard around the test files, (b) the '#else' placeholder case that calls SUCCEED, (c) which CI lane builds with the option ON or OFF, (d) the test policy in the repository file AGENTS.md? Quote what was said, or state that nothing was said and how you searched.
3. Which session text or commit wrote the claim that the CMake CI lane configures with TRON_AMX_DISPATCH on (the stale comment in src/tron/CMakeLists.txt and the sentence "so CI covers that code" in README.ci.md)? Use 'git -C ${WT} log -S' and 'git blame'. Was the claim true when it was written, and what change made it stale?
4. Which commit and pull request introduced the '#ifdef TRON_AMX_DISPATCH' guard and the '#else' placeholder case in t/t_amx_dispatch_dtype.cpp and in t/t_amx_numerics.cpp? Who is the author? Was the guard there before PR 5022 (compare ${WT_OLD} with the merge base 3bea58b788 and with older history)? What did PR 5022 add inside the guard?
5. Which commit and pull request added the registration 'add_catch_test(NAME t_page_share_counters DEFINES TRON_PAGE_SHARE_COUNTERS ...)' and the README.ci.md sentence "t_page_share_counters compiles the counter header with its own define in every lane"? Who is the author, and when? If a session transcript shows why that test got its own define, quote the reason.
6. Session c19a91bd, line 191 (2026-10-30T16:31Z) holds tool output with that README.ci.md sentence. What was the assistant doing at that point, and did it comment on the sentence?
Put each dated event in 'timeline'. Put everything you searched for and did not find in 'not_found', with the search you ran.
`,
  },
  {
    key: 'history-november',
    schema: CLAIMS_SCHEMA,
    verify: true,
    prompt: `
Task: reconstruct from session transcripts how our side handled the CI-lane finding in review round 2 of tron PR 5022 (2026-11-19 to 2026-11-21), and why the per-target define was never proposed.
${COMMON}
${TRANSCRIPTS}
Sessions of that period in that folder: 78b9fca8-c24b-4ac2-a02d-0236a437cdd6 (starts 2026-11-19T23:38Z; the session that did round 2; it has subagent transcripts, one of them named agent-aprereview-...), 68a7918d-f12e-464b-b249-eda4aaac93c7 (starts 2026-11-20T00:39Z; it studied Isaac's review and edited the skills), a5b17f22-2551-4a33-9291-7580059b7d40 (starts 2026-11-21T00:07Z). Do not read the two sessions that start on 2026-11-24 (5923dad0 and db5d90b8): they are after the event.

Answer these questions, one entry in 'answers' for each:
1. How was decision D1 ("the build flag stays out of the Nix build in this PR") reached? Quote each option the assistant put before jhan, in order, with timestamps. Quote jhan's answers. Was any option ever listed other than (a) add the flag to the Nix build in this PR, (b) add it in a separate PR, (c) keep it out and document where the tests run?
2. Did any assistant text, any subagent output or any plan ever mention a compile definition for one test target, the DEFINES argument of add_catch_test, or t_page_share_counters as a model for the AMX tests? Known leads: session 78b9fca8 line 1636 (2026-11-20T03:18Z) holds tool output with the README.ci.md sentence "t_page_share_counters compiles the counter header with its own define in every lane", and lines 225, 378, 415, 417, 1544 hold target_compile_definitions output. For each lead, say what the assistant was doing, and what it wrote next. Did it connect the sentence to the AMX test?
3. Review comment I10 (thread r4356060885) asked for a host-testable transpose function, and our side moved the transpose case above the '#ifdef' so that it runs with the option OFF, and removed the placeholder case of t_amx_numerics. Did anyone ask the same question of t_amx_dispatch_dtype: does this test need the build option at all? Quote the reasoning, or state that there is none.
4. The pre-review of 2026-11-19 20:40 to 20:56 PST (2026-11-20 04:40 to 04:56 UTC) by an independent agent used folks-code-review, tron-code-review, cpp-coding-guide and simplify-cpp-comments. Find the prompt given to that agent. Quote its scope sentence. Quote every instruction that tells the agent which decisions are settled or out of scope. List its findings. Did any finding concern the option-OFF lane, the guard, or the placeholder? Which of our five skills were not given to it?
5. How was the claude[bot] finding r4645384802 of 2026-11-20 ("The new kv_mul-16 tests never run on PRs") handled? Quote the analysis and the decision. Was a fix other than the Nix flag considered at that point?
6. In session 68a7918d, how were the lessons of Isaac's first review turned into skill edits? For the CI-lane point (draft sections C1 "CI covers this" and B5 "Code that needs no special hardware must not sit behind a hardware gate"): which text went into which skill, which text was left out, and what did jhan decide (quote)?
7. Quote every statement by jhan between 2026-11-19 and 2026-11-21 about how serious the CI-lane point is, about the test policy, or about keeping the replies simple. Say how each one shaped the outcome.
8. Root cause in your own words, tied to the quotes above: at which step would a different action have produced the per-target define, and what was missing at that step (a check in a skill, a step in the reply procedure, a framing of the options, something else)?
Put each dated event in 'timeline'. Put everything you searched for and did not find in 'not_found', with the search you ran.
`,
  },
  {
    key: 'repo-facts',
    schema: CLAIMS_SCHEMA,
    verify: true,
    prompt: `
Task: establish the repository facts that decide whether the reviewer's fix is sound and how general the problem class is. Work in the worktree at the final head.
${COMMON}
Answer these questions, one entry in 'answers' for each. Cite file:line for every fact.
1. How does add_catch_test in t/CMakeLists.txt apply its DEFINES argument (which CMake command, which scope, which target)? List every registration in t/CMakeLists.txt that passes DEFINES, with its line number and the definition it passes. How many are there?
2. How far apart are the precedent (the t_page_share_counters registration) and the t_amx_dispatch_dtype registration in t/CMakeLists.txt, in lines? Does the diff of PR 5022 ('git -C ${WT} diff 3bea58b788 ddf843ad97 -- t/CMakeLists.txt README.ci.md') touch either file, and how far are its hunks from the precedent lines? In README.ci.md, how many lines separate the sentence "t_page_share_counters compiles the counter header with its own define in every lane" from the TRON_AMX_DISPATCH paragraph that the PR edits?
3. Where is TRON_AMX_DISPATCH read? Run 'git -C ${WT} grep -n TRON_AMX_DISPATCH' and classify every hit: CMake, header code that a test translation unit sees, library source, test source, documentation. Which code changes when one test translation unit defines the macro and the tron library is built without it?
4. Is the per-target define sound for t_amx_dispatch_dtype? The reviewer says: "The option only changes code inside the self_attention<model> template, and no other translation unit in the test binary instantiates that template for the test's models." Check this as far as reading allows. Which entities get a different definition under the macro (templates, inline functions, classes with different members)? Are any of them also compiled into the tron library, the fake library or other objects that link into the test binary without the macro? State the one-definition-rule risk plainly. How do the fake kernels of the test satisfy the kernel symbols when src/tron/kernels/amx_attn.cpp is not compiled?
5. Would the same per-target define work for t_amx_numerics? What does that test need that the define does not give (kernel source file, -mamx compile options, AMX hardware)? What is the right treatment of its kernel cases?
6. How large is the problem class at this head? List every test file under t/ whose test cases sit under a preprocessor guard on a build option or feature macro, and every '#else' arm that holds a placeholder case (SUCCEED, "nothing to test", an empty case, or a WARN). For each give file:line, the macro, whether the lane of gcp-nix.yml defines it (read nix/cmake-tron-test-build.nix and the workflow files under .github/workflows), and whether the guarded code needs hardware or only the macro. How many test files could run in the required lane with a per-target define alone?
7. Quote the section "Test policy" of the root AGENTS.md with line numbers. Quote the rules of t/AGENTS.md that a change like PR 5606 triggers (registry refresh, max_rss). Does any written rule of the repository say how a test must be gated or that a placeholder case is acceptable?
8. Which lanes run on a pull request, and which of them build the tests? Give the workflow file, its triggers and the configure flags (file:line). Confirm or correct: gcp-nix.yml is the required lane and builds with TRON_AMX_DISPATCH OFF, and cmake-single-platform.yml sets it ON and starts only by workflow_dispatch or workflow_call.
9. Read the PR 5606 diff in ${FIND}. Does it do anything beyond the define and the deletion of the placeholder? What does it leave open, by its own words?
Put what you searched for and did not find in 'not_found'. In 'lessons' give the facts a review check must know to propose this fix safely: the precondition list for a per-target define.
`,
  },
  {
    key: 'reviewer-method',
    schema: CLAIMS_SCHEMA,
    verify: false,
    prompt: `
Task: work out which review moves let the outside reviewer produce a fix that our side did not find, and state them as checks that a review skill could hold.
${COMMON}
Read ${FIND} completely. In ${SNAP} read review 5623855297 (the first review body, with its fields "Not verified", "Coverage gaps", "Purpose", "Architecture"), the threads r4356060700, r4356061170, r4356060885, r4356062738 and r4645384802 with our replies, and the body of our reply review 5997064669. Read ${DRAFT}, sections B5, C1 and F.

Answer these questions, one entry in 'answers' for each:
1. How did the reviewer's proposed fix change between 2026-10-23 and 2026-11-24, and what in our replies made the change possible? Quote both fixes and the sentence of our reply that the new fix answers.
2. List each review move visible in the 2026-11-24 comment and in PR 5606. Examples to look for: restating the author's objection as a constraint on the fix; naming a precedent in the same file; a test of the fix with the option OFF; mutations of the production code and of the registration; deletion of the placeholder so that a lost define fails; a list of what the fix makes stale (PR description, registry rows); a statement of what was not tested; an admission of the reviewer's own wrong suggestion. For each move quote the words that show it.
3. For each move, write it as a general check: trigger, procedure, exclusions, wording of the finding. The trigger must not name the files of PR 5022.
4. Which items of ${DRAFT} (B5, C1, F, others) come near these moves? For each, say what it lacks. Quote the item.
5. The first review and the bot both proposed the Nix flag, and neither proposed the per-target define at that time. What does that say about where the fix came from: a check that fires on the code, or a second search made after the first fix was declined? Tie your answer to quotes.
6. What should the AUTHOR's side do when it declines a reviewer's fix for a good reason? Write the shortest procedure that would have produced the per-target define on 2026-11-19. Each step must be an action with an observable result.
In 'lessons' list the generalisable rules in order of expected value, most valuable first.
`,
  },
]

const verifyPrompt = (item, report) => `
Task: adversarial check of an analyst's report. For each answer below, open the cited sources yourself and try to refute the answer. A claim stands only when the source shows it. When the evidence does not show the claim, return 'refuted' or 'unverifiable', not 'confirmed'. Check quotes word for word, line numbers, commit ids, dates and counts. Re-run the commands the analyst names. When an answer is right in substance and wrong in a detail, return 'partly' and give the correction.
${COMMON}
${item.key.startsWith('history') ? TRANSCRIPTS : ''}
The analyst's task was:
${item.prompt}

The analyst's report (JSON):
${JSON.stringify(report, null, 1)}

Return one verdict for each answer, in the same order, with what you checked (command and output, or file and line) and the correction. Use an empty string for the correction when there is none. In 'new_facts' list facts you found that the report missed and that bear on the questions.
`

const results = await pipeline(
  TASKS,
  item => agent(item.prompt, { label: 'analyse:' + item.key, phase: 'Analyse', schema: item.schema }),
  async (report, item) => {
    if (!report) return { key: item.key, report: null, verification: null }
    if (!item.verify) return { key: item.key, report, verification: null }
    const verification = await agent(verifyPrompt(item, report), { label: 'verify:' + item.key, phase: 'Verify', schema: VERIFY_SCHEMA })
    return { key: item.key, report, verification }
  },
)

const out = {}
for (let i = 0; i < TASKS.length; i++) {
  const r = results[i]
  out[TASKS[i].key] = r ? r : { key: TASKS[i].key, report: null, verification: null, failed: true }
}
log('done: ' + Object.keys(out).filter(k => out[k].report).length + ' of ' + TASKS.length + ' reports returned')
return out
