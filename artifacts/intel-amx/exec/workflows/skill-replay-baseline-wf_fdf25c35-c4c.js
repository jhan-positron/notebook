export const meta = {
  name: 'skill-replay-baseline',
  description: 'Blind replay of the five review skills, as they stand, on tron PR 5022 at its final head with the PR page frozen at 2026-11-20',
  phases: [
    { title: 'Replay', detail: 'three trials each of tron-code-review, folks-code-review and cpp-coding-guide; one each of ben-review and positron-code-review; two trials of all five together' },
  ],
}

const R = '/home/jhan/workspace/ai-runs/skill-replay-20261123'
const WT = R + '/tron-ddf843ad97'
const SNAP = R + '/pr5022-snapshot-20261120.md'
const DIR = (args && args.skillsDir) ? args.skillsDir : R + '/skills-baseline'

const REPLAY_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          skill: { type: 'string' },
          check: { type: 'string' },
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['blocker', 'should-fix', 'question', 'nit', 'info'] },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          proposed_change: { type: 'string' },
        },
        required: ['skill', 'check', 'title', 'file', 'severity', 'claim', 'evidence', 'proposed_change'],
      },
    },
    skill_files_read: { type: 'array', items: { type: 'string' } },
    checks_skipped: { type: 'array', items: { type: 'object', properties: { check: { type: 'string' }, reason: { type: 'string' } }, required: ['check', 'reason'] } },
    outside_sources_used: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['findings', 'skill_files_read', 'checks_skipped', 'outside_sources_used', 'summary'],
}

const replayPrompt = (skills) => `
You are a code reviewer. Today is 2026-11-20. Apply ${skills.length === 1 ? 'one review skill' : 'the ' + skills.length + ' review skills named below'} to one pull request and report what ${skills.length === 1 ? 'the skill finds' : 'the skills find'}.

Pull request: positron-ai/tron PR 5022, "AMX attention: serve kv_mul 16 (Muse Glimmer) with a group_heads template parameter", at its final head ddf843ad97. The author has pushed this head and has replied to the first review. Review the whole PR at this head, the way ${skills.length === 1 ? 'the skill asks' : 'each skill asks'}.

${skills.length === 1 ? 'The skill' : 'The skills'}: ${skills.map(s => DIR + '/' + s + '/').join(' , ')}
Read each SKILL.md from the first line to the last. Read every file under the skill folder that SKILL.md tells you to read for a check you apply. Apply each skill as it is written: its triggers, its procedures, its exclusions, its severities and its finding wording. Do not add checks of your own. Do not leave a check out because it is long.

Materials. These are the only sources you may use:
1. Code: the git worktree ${WT}, checked out at ddf843ad97. The merge base with main is 3bea58b788. The PR diff is 'git -C ${WT} diff 3bea58b788 ddf843ad97' (12 files).
2. PR page: ${SNAP}. It holds the title, description, commits, changed files, reviews, inline threads and comments as of today. Where a skill tells you to query GitHub, read this file instead.
3. The skill folder${skills.length === 1 ? '' : 's'} named above.

Rules:
- No network. No gh, no curl, no web tools.
- No other git refs: no '--all', no other branches, no commit later than ddf843ad97. No other worktrees and no other repositories.
- Do not read anything under ~/.claude, ~/.codex, ~/workspace/intel-AMX or ~/workspace/notebook. Under ~/workspace/ai-runs read only the paths named above. This run is a controlled experiment, and an outside source would spoil it.
- Read-only. Do not edit, build or run tests. git diff, git grep, git show, git log on ancestors of ddf843ad97, sed -n and rg are fine. Use 'git -C <path>' and full paths; do not cd.
- Where a skill needs something these rules forbid (a CI log, a run on hardware), record the check in checks_skipped with the reason, and go on.

Return every finding, most severe first. For each finding give: the skill, the check of that skill (its number or section name), a title, the file and line at the head, the severity that the skill assigns (mapped to blocker, should-fix, question, nit or info), the claim, the evidence (a command with its output, or file:line with a quote), and the concrete change you propose (an empty string when the skill prescribes none). Also return the skill files you read, the checks you could not apply, every source you used outside the three materials (this list should be empty), and a summary of at most five sentences.
`

const RUNS = [
  { skills: ['tron-code-review'], trial: 1 },
  { skills: ['tron-code-review'], trial: 2 },
  { skills: ['tron-code-review'], trial: 3 },
  { skills: ['folks-code-review'], trial: 1 },
  { skills: ['folks-code-review'], trial: 2 },
  { skills: ['folks-code-review'], trial: 3 },
  { skills: ['cpp-coding-guide'], trial: 1 },
  { skills: ['cpp-coding-guide'], trial: 2 },
  { skills: ['cpp-coding-guide'], trial: 3 },
  { skills: ['ben-review'], trial: 1 },
  { skills: ['positron-code-review'], trial: 1 },
  { skills: ['ben-review', 'cpp-coding-guide', 'folks-code-review', 'positron-code-review', 'tron-code-review'], trial: 1 },
  { skills: ['ben-review', 'cpp-coding-guide', 'folks-code-review', 'positron-code-review', 'tron-code-review'], trial: 2 },
]

const selected = (args && args.only) ? RUNS.filter(r => args.only.includes(r.skills.length === 1 ? r.skills[0] : 'all-five')) : RUNS

phase('Replay')
const results = await parallel(selected.map(run => () => {
  const name = run.skills.length === 1 ? run.skills[0] : 'all-five'
  return agent(replayPrompt(run.skills), { label: 'replay:' + name + ':t' + run.trial, phase: 'Replay', schema: REPLAY_SCHEMA })
    .then(res => ({ name, trial: run.trial, skillsDir: DIR, result: res }))
}))

const ok = results.filter(Boolean).filter(r => r.result)
log(ok.length + ' of ' + selected.length + ' replays returned')
return { skillsDir: DIR, runs: results.map((r, i) => r ? r : { name: selected[i].skills.length === 1 ? selected[i].skills[0] : 'all-five', trial: selected[i].trial, result: null }) }
