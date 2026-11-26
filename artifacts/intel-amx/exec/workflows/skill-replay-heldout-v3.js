export const meta = {
  name: 'skill-replay-heldout-v3',
  description: 'Version 3 of the edited review skills on the held-out tron PR 5572 (one run per skill) and on the negative control',
  phases: [
    { title: 'Held-out PR 5572', detail: 'edited tron-code-review and folks-code-review, one run each' },
    { title: 'Negative control', detail: 'edited skills on a synthetic change under a guard whose macro changes library code' },
  ],
}

const R = '/home/jhan/workspace/ai-runs/skill-replay-20261123'
const BASE = R + '/skills-baseline'
const CAND = R + '/skills-candidate-v3-blind'

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

const RULES = (allowed) => `
Rules:
- No network. No gh, no curl, no web tools.
- No other git refs: no '--all', no other branches, no later commit. No other worktrees and no other repositories.
- Do not read anything under ~/.claude, ~/.codex, ~/workspace/intel-AMX or ~/workspace/notebook. Under ~/workspace/ai-runs read only the paths named above. This run is a controlled experiment, and an outside source would spoil it.
- Read-only. Do not edit, build or run tests. git diff, git grep, git show, git log on ancestors of the reviewed commit, sed -n and rg are fine. Use 'git -C <path>' and full paths; do not cd.
- Where a skill needs something these rules forbid (a CI log, a run on hardware), record the check in checks_skipped with the reason, and go on.

Return every finding, most severe first. For each finding give: the skill, the check of that skill (its number or section name), a title, the file and line at the reviewed revision, the severity that the skill assigns (mapped to blocker, should-fix, question, nit or info), the claim, the evidence (a command with its output, or file:line with a quote), and the concrete change you propose (an empty string when the skill prescribes none). Also return the skill files you read, the checks you could not apply, every source you used outside the ${allowed} materials (this list should be empty), and a summary of at most five sentences.
`

const pr5572Prompt = (dir, skill) => `
You are a code reviewer. Today is 2026-11-23. Apply one review skill to one pull request and report what the skill finds.

Pull request: positron-ai/tron PR 5572, a draft, at its head 882e5322f1. Review the whole PR at this head, the way the skill asks.

The skill: ${dir}/${skill}/
Read SKILL.md from the first line to the last. Read every file under the skill folder that SKILL.md tells you to read for a check you apply. Apply the skill as it is written: its triggers, its procedures, its exclusions, its severities and its finding wording. Do not add checks of your own. Do not leave a check out because it is long.

Materials. These are the only sources you may use:
1. Code: the git worktree ${R}/tron-pr5572-882e5322f1, checked out at 882e5322f1. The PR targets the branch rbjarnason/qwen35-native-4b-registry, and the merge base is 72e1191804. The PR diff is 'git -C ${R}/tron-pr5572-882e5322f1 diff 72e1191804 882e5322f1' (22 files, 4,767 lines added).
2. PR page: ${R}/pr5572-snapshot-20261123.md. It holds the title, description, commits and changed files as of today. The PR has no review and no comment yet. Where a skill tells you to query GitHub, read this file instead.
3. The skill folder named above.
${RULES('three')}`

const controlPrompt = (dir, skill) => `
You are a code reviewer. Today is 2026-11-23. Apply one review skill to one local change and report what the skill finds.

The change: an uncommitted working-tree diff in the git worktree ${R}/tron-synthetic-control, on top of commit ddf843ad97 of positron-ai/tron. See it with 'git -C ${R}/tron-synthetic-control diff'. The author's description of the change is in ${R}/synthetic-control-task.md. No pull request exists yet. Review the change the way the skill asks.

The skill: ${dir}/${skill}/
Read SKILL.md from the first line to the last. Read every file under the skill folder that SKILL.md tells you to read for a check you apply. Apply the skill as it is written: its triggers, its procedures, its exclusions, its severities and its finding wording. Do not add checks of your own. Do not leave a check out because it is long.

Materials. These are the only sources you may use:
1. Code: the git worktree ${R}/tron-synthetic-control (HEAD ddf843ad97 plus the working-tree diff).
2. The author's description: ${R}/synthetic-control-task.md. Where a skill tells you to query GitHub for the PR body, read this file instead. No review and no comment exists.
3. The skill folder named above.
${RULES('three')}`

const ALL_RUNS = [
  { group: 'pr5572', variant: 'baseline', dir: BASE, skill: 'tron-code-review', trial: 1 },
  { group: 'pr5572', variant: 'baseline', dir: BASE, skill: 'tron-code-review', trial: 2 },
  { group: 'pr5572', variant: 'baseline', dir: BASE, skill: 'folks-code-review', trial: 1 },
  { group: 'pr5572', variant: 'baseline', dir: BASE, skill: 'folks-code-review', trial: 2 },
  { group: 'pr5572', variant: 'candidate', dir: CAND, skill: 'tron-code-review', trial: 1 },
  { group: 'pr5572', variant: 'candidate', dir: CAND, skill: 'tron-code-review', trial: 2 },
  { group: 'pr5572', variant: 'candidate', dir: CAND, skill: 'folks-code-review', trial: 1 },
  { group: 'pr5572', variant: 'candidate', dir: CAND, skill: 'folks-code-review', trial: 2 },
  { group: 'pr5572', variant: 'candidate', dir: CAND, skill: 'cpp-coding-guide', trial: 1 },
  { group: 'control', variant: 'candidate', dir: CAND, skill: 'tron-code-review', trial: 1 },
  { group: 'control', variant: 'candidate', dir: CAND, skill: 'folks-code-review', trial: 1 },
  { group: 'control', variant: 'candidate', dir: CAND, skill: 'cpp-coding-guide', trial: 1 },
]

const RUNS = ALL_RUNS.filter(r => r.variant === 'candidate' && (r.group === 'control' || (r.trial === 1 && r.skill !== 'cpp-coding-guide')))

const results = await parallel(RUNS.map(run => () => {
  const prompt = run.group === 'pr5572' ? pr5572Prompt(run.dir, run.skill) : controlPrompt(run.dir, run.skill)
  const label = run.group + ':' + run.variant + ':' + run.skill + ':t' + run.trial
  return agent(prompt, { label, phase: run.group === 'pr5572' ? 'Held-out PR 5572' : 'Negative control', schema: REPLAY_SCHEMA })
    .then(res => ({ label, group: run.group, variant: run.variant, skill: run.skill, trial: run.trial, result: res }))
}))

const ok = results.filter(Boolean).filter(r => r.result)
log(ok.length + ' of ' + RUNS.length + ' runs returned')
return { runs: results.map((r, i) => r ? r : { label: RUNS[i].group + ':' + RUNS[i].variant + ':' + RUNS[i].skill + ':t' + RUNS[i].trial, result: null }) }
