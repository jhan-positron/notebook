export const meta = {
  name: 'skill-edit-final-check',
  description: 'Check that version 2 of the skill edits applied the required changes of the three skeptic reviews and added no new defect',
  phases: [
    { title: 'Final check', detail: 'one checker per skill reads the edited text against the required changes' },
  ],
}

const R = '/home/jhan/workspace/ai-runs/skill-replay-20261123'
const A = '/home/jhan/workspace/ai-runs/skill-miss-analysis-20261123'
const WT = R + '/tron-ddf843ad97'

const SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['install as is', 'install after the listed fixes', 'rework'] },
    required_changes_checked: { type: 'integer' },
    not_applied: {
      type: 'array',
      items: {
        type: 'object',
        properties: { source: { type: 'string' }, what_was_asked: { type: 'string' }, state_in_v2: { type: 'string' }, matters: { type: 'string', enum: ['yes', 'no'] }, why: { type: 'string' } },
        required: ['source', 'what_was_asked', 'state_in_v2', 'matters', 'why'],
      },
    },
    new_defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: { file: { type: 'string' }, quoted_text: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' }, replacement_text: { type: 'string' } },
        required: ['file', 'quoted_text', 'problem', 'evidence', 'replacement_text'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['verdict', 'required_changes_checked', 'not_applied', 'new_defects'],
}

const prompt = (skill, files) => `
Task: final check of one edited review skill before it is proposed for installation.

Context. Version 1 of the edits to three review skills was reviewed by three skeptics. They returned required changes. Version 2 was written to apply them. Check version 2 of the skill named below.

Skill to check: ${skill}. Edited files: ${files}.

Files:
- Unedited skills: ${R}/skills-baseline/
- Version 1 of the edits: ${R}/skills-candidate/
- Version 2 of the edits: ${R}/skills-candidate-v2/ . See the edits with: diff ${R}/skills-baseline/<file> ${R}/skills-candidate-v2/<file>
- The script that made version 2 (old text and new text): ${A}/tools/apply_candidate_v2.py
- The three skeptic reviews (JSON, each with required_changes that quote version 1 text): ${A}/out/skeptic_false-positives.json, ${A}/out/skeptic_technical-correctness.json, ${A}/out/skeptic_form-and-consistency.json
- tron at the head of PR 5022: git worktree ${WT} (read-only)
- The finding and the fix that the edits answer: ${A}/finding.md
- The author's writing rules: /home/jhan/.claude/skills/plain-english/SKILL.md

Do these steps.
1. From the three reviews, list every required change that concerns this skill. Count them.
2. For each one, read version 2 and decide: applied, applied in another wording, or not applied. Where two reviewers asked for conflicting things, say which one version 2 followed. Report only the ones that are not applied, and say whether that matters. A change does not matter when version 2 removes the defect in another way.
3. Read the whole edited text of version 2 once more as a reviewer who has to follow it. Report new defects only: a contradiction inside the skill, a wrong statement about the repository (check it in the worktree), a command that does not run or returns something else than the text says (run it), a rule that would prescribe a per-target compile definition where it is unsafe, a rule that would hide the PR 5022 finding itself, or a clear break of the writing rules (an idiom, an undefined term, two claims in one sentence). Give paste-ready replacement text for each.
4. Known cases that the text must handle. t/t_amx_dispatch_dtype.cpp at the head: finding, per-target define, delete the placeholder, before the merge. The gate case at t/t_amx_numerics.cpp:148: move above the guard. The packer, QK and PV cases of t/t_amx_numerics.cpp: no per-target define. A new case under '#ifdef HBM_ALLOC_SHADOW' in t/t_hwalloc.cpp: gap reported, no per-target define, no production refactor demanded before the merge. A hand-started workflow that sets the option: does not count as a required lane.

Rules: read-only. Do not edit any file, build, or use the network. Use 'git -C <path>' and full paths; do not cd. Do not ask for a change because of taste. Do not repeat a required change that version 2 already applies.
`

const ITEMS = [
  { skill: 'tron-code-review', files: 'tron-code-review/SKILL.md' },
  { skill: 'folks-code-review', files: 'folks-code-review/SKILL.md and folks-code-review/references/procedures.md' },
  { skill: 'cpp-coding-guide', files: 'cpp-coding-guide/SKILL.md' },
]

const results = await parallel(ITEMS.map(it => () =>
  agent(prompt(it.skill, it.files), { label: 'final-check:' + it.skill, phase: 'Final check', schema: SCHEMA }).then(r => ({ skill: it.skill, check: r }))))
return { checks: results.map((r, i) => r ? r : { skill: ITEMS[i].skill, check: null }) }
