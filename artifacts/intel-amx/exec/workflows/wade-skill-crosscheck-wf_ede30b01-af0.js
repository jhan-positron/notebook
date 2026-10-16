export const meta = {
  name: 'wade-skill-crosscheck',
  description: 'Judge the Claude and codex Wade-code-review skills against the verified PR 4557 analysis; refute each Claude check; plain-English check',
  phases: [{ title: 'Judge' }, { title: 'Refute' }, { title: 'English' }],
}
const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade'
const MINE = '/home/jhan/.claude/skills/Wade-code-review'
const CODEX = '/home/jhan/.codex/skills/wade-code-review'
const CTX = `Read ${S}/CONTEXT.md first (the review, the paths, the earlier lenses). Two skills were written independently today to cover what our reviews missed on PR 4557:
- Claude's: ${MINE}/SKILL.md, ${MINE}/references/pr4557-misses.md, ${MINE}/references/procedures.md
- codex's: ${CODEX}/SKILL.md, ${CODEX}/references/pr4557.md
The verified ground truth is ${S}/analysis.json (13 points: analysis, refuter votes, precision probe) and ${S}/../../tasks/w4c6vh4xh.output is NOT readable; use ${MINE}/references/pr4557-misses.md for the codex-claims verdicts. Worktree READ ONLY: /home/jhan/workspace/ai-runs/tron-issue4525, reviewed head 96a6220ab6 (git show 96a6220ab6:<path>).`

const JUDGE = { type: 'object', properties: {
  coverage: { type: 'array', items: { type: 'object', properties: { point: { type: 'string' }, claude: { type: 'string', enum: ['full', 'partial', 'none'] }, codex: { type: 'string', enum: ['full', 'partial', 'none'] }, note: { type: 'string' } }, required: ['point', 'claude', 'codex', 'note'] } },
  scores: { type: 'object', properties: { claude: { type: 'number' }, codex: { type: 'number' } }, required: ['claude', 'codex'] },
  claude_weaknesses: { type: 'array', items: { type: 'string' } },
  codex_weaknesses: { type: 'array', items: { type: 'string' } },
  codex_strengths_to_graft: { type: 'array', items: { type: 'string' }, description: 'things in codex\'s skill that Claude\'s lacks and should take' },
  factual_errors: { type: 'array', items: { type: 'object', properties: { skill: { type: 'string' }, location: { type: 'string' }, error: { type: 'string' }, evidence: { type: 'string' } }, required: ['skill', 'location', 'error', 'evidence'] } },
}, required: ['coverage', 'scores', 'claude_weaknesses', 'codex_weaknesses', 'codex_strengths_to_graft', 'factual_errors'] }

const LENSES = [
  ['coverage', 'Lens COVERAGE: for each of the 13 Wade points (W1-W6, M1, S1, S2, L3, L4a, L4b, L4c) and the 3 reply-correcting facts (W5 observation guard, L4a gating lane, M1 commit date), does each skill contain a check that would produce that finding when run on PR 4557 at 96a6220ab6 by an agent that has not seen Wade\'s review? Score 0-10 each.'],
  ['executability', 'Lens EXECUTABILITY: pick 4 checks from each skill and try to run them literally as an agent would on the PR at 96a6220ab6 (commands, files). Does the text tell you what to open, what to compare, when to stop? Where does it require judgment it does not define? Score 0-10 each.'],
  ['precision', 'Lens PRECISION: for each skill, find things in PR 4557 that Wade explicitly KEPT (kernel probes, bf16 round trip, partner-zero checks, at() section, bit-exact four-parity section, the suffix naming convention jhan defended) and check whether the skill as written would flag them. Also check whether either skill contradicts the user\'s own decisions (the value-suffix convention is jhan\'s; nothing in a skill may propose dropping it). Score 0-10 each.'],
  ['facts', 'Lens FACTS: every file:line, commit id, PR number, date and quoted code in BOTH skills (SKILL.md and references) must be checked against the worktree (git show 96a6220ab6:...), git log, and the GitHub facts in CONTEXT.md. List every wrong one. Score 0-10 each.'],
  ['form', 'Lens FORM: compare both SKILL.md files with the existing skills ~/.claude/skills/tron-code-review/SKILL.md and ben-review/SKILL.md for frontmatter, length, structure, and whether the description would make an agent load the skill at the right moment. Would a reviewer-agent reading only SKILL.md (no references) know what to do? Score 0-10 each.'],
]

phase('Judge')
const judged = await parallel(LENSES.map(([k, task]) => () => agent(`${CTX}\n\n${task}\n\nReturn the schema. Cite file:line for every factual error.`, { label: `judge:${k}`, phase: 'Judge', schema: JUDGE })))

const CHECKS = ['1 Value-pinning rows need a consumer', '2 Structure-only compile-time checks', '3 A layout-formula check must execute on every CI runner class', '4 Same experiment run twice', '5 A test name states the enforced contract', '6 Guarantee claim versus enforcing declaration', '7 CI claims name the lane, the trigger and the configure line', '8 Result rows cite the reviewed head', '9 PR-body passages a GitHub reader cannot use', '10 Hunk-to-claim trace', '11 Commit history is reviewed content', '12 A shared-header change no test observes needs a named owner\'s acceptance', '13 Role-bearing constant names']
const V = { type: 'object', properties: { check: { type: 'string' }, reproduces_wade: { type: 'boolean' }, false_positives: { type: 'array', items: { type: 'string' } }, defects: { type: 'array', items: { type: 'object', properties: { quote: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['quote', 'problem', 'fix'] } }, verdict: { type: 'string', enum: ['keep', 'fix-wording', 'rewrite'] } }, required: ['check', 'reproduces_wade', 'false_positives', 'defects', 'verdict'] }
phase('Refute')
const refuted = await parallel(CHECKS.map(c => () => agent(`${CTX}\n\nYou REFUTE one check of Claude's skill: "${c}" (section in ${MINE}/SKILL.md; its long procedure in ${MINE}/references/procedures.md). Run it as literally as an agent would on PR 4557 at 96a6220ab6 (diff ${S}/pr4557-at-96a6220ab6.diff, body ${S}/pr4557-body-as-reviewed.md, worktree git show). (1) Does it reproduce the corresponding Wade finding blind? (2) What does it also fire on that Wade kept or did not flag? (3) Which sentences require judgment the text does not define, cite a wrong file:line, or contradict the references? Give the exact replacement wording for each defect. Return the schema.`, { label: `refute:${c.split(' ')[0]}`, phase: 'Refute', schema: V })))

phase('English')
const english = await agent(`Check mode of the plain-english skill (call the Skill tool with skill "plain-english" first). Text to check: ${MINE}/SKILL.md (read it in full). Rules: define every code name, acronym and metric at first use (a term defined once in the document is fine later); one claim per sentence; numbers with units and meaning; citations after a sentence; Short version first; no idioms or metaphors; bullets for multi-point paragraphs; short sentences, no semicolons. Return JSON {violations:[{rule:number, original:string, fix:string}], count:number}. Do not invent violations; a skill file is a reference document, so a heading followed by a list is fine.`, { label: 'english', phase: 'English', schema: { type: 'object', properties: { violations: { type: 'array', items: { type: 'object', properties: { rule: { type: 'number' }, original: { type: 'string' }, fix: { type: 'string' } }, required: ['rule', 'original', 'fix'] } }, count: { type: 'number' } }, required: ['violations', 'count'] } })

return { judged: judged.filter(Boolean), refuted: refuted.filter(Boolean), english }