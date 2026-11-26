export const meta = {
  name: 'numeric-rounding-recheck',
  description: 'Two independent checkers verify that the corrections were applied and look for new contradictions',
  phases: [{ title: 'Recheck', detail: 'two read-only checkers' }],
}

const ROOT = '/home/jhan/workspace/smaller-tasks/numeric-rounding'
const NEW = `${ROOT}/handoff-numeric-rounding-20261123.md`
const SPLIT = '/home/jhan/workspace/intel-AMX/GDN/status/handoff-gdn-pr-split-20261122.md'
const SPLIT_BEFORE = '/home/jhan/workspace/intel-AMX/GDN/status/handoff-gdn-pr-split-20261122.before-20261123.md'
const ROUND1 = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/verify-20261123.json'

const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string' },
    round1_not_resolved: {
      type: 'array',
      items: { type: 'object', properties: { key: { type: 'string' }, index: { type: 'integer' }, why: { type: 'string' }, fix: { type: 'string' } }, required: ['key', 'index', 'why', 'fix'] },
      description: 'round-1 findings of severity wrong, contradiction, missing or unsupported that the present text still does not resolve; leave out findings that the writer may have rejected for a stated good reason',
    },
    new_findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['wrong', 'unsupported', 'contradiction', 'missing', 'unclear'] },
          file: { type: 'string' },
          location: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string', description: 'exact replacement text' },
        },
        required: ['severity', 'file', 'location', 'problem', 'evidence', 'fix'],
      },
    },
  },
  required: ['verdict', 'round1_not_resolved', 'new_findings'],
}

const COMMON = `
You are an independent checker in a second round. A first round of five checkers found 98 points in texts that a Claude session wrote today (2026-11-23) for an engineer, jhan. The writer applied corrections. Your job: find what is STILL wrong, and what the corrections broke. Do not defend the text. Report only what you checked. Do not report pure style points.

## Setting
- The round-1 results are in ${ROUND1}: a JSON list of five objects {key, result:{verdict, findings:[{severity,file,location,problem,evidence,fix}], confirmed}}. Read it with python3 (json.load). The index of a finding is its position in its list, starting at 0.
- The writer made one decision against the first plan: the comment for issue #4444 is NOT posted. Reason: jhan's condition was "update our issue if you believe it is tightly related", and the facts say the two issues are related through one item only. The text is now a draft (${ROOT}/drafts/comment-4444-draft.md). So round-1 findings of the form "the handoff says the comment is posted" are resolved when the handoff now says "not posted".
- Files: the NEW handoff ${NEW}; its fact files ${ROOT}/handoff-material/facts-*.md; the drafts ${ROOT}/drafts/comment-4444-draft.md and comment-5433-draft.md (neither is posted); the SPLIT handoff ${SPLIT} and its version before today ${SPLIT_BEFORE}.
- Repository positron-ai/tron, shared local clone /home/jhan/workspace/tron: READ ONLY ("git -C /home/jhan/workspace/tron ..." with read-only commands; no fetch, checkout, commit; never "git worktree prune"). Our code: worktree /home/jhan/workspace/ai-runs/tron-gdn-amx at 882e5322f1 (read only). Commit ids: main f454423b09; model's branch (PR #3696) 72e1191804; PR #3221 head 127a662083; PR #5571 head 69cc70fae0; our commits 0d69ef3ce8, 775bba7661, 882e5322f1; measured commits 8351e4ad52 (arms a and a0) and aacdd287c0 (arm p0).
- GitHub: "gh ... --repo positron-ai/tron" for READING only. Never write to GitHub. No ssh. No builds. Do not change any file.
- Result files for numbers: /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/collected.json (runs is a dict; fields arm, cell, ttft_max, tip, rep) and collected-controls.json.
`

const TASKS = [
  {
    key: 'recheck-new',
    prompt: `
## Your part: the NEW handoff and the two drafts
1. For every round-1 finding of the lists "new-facts", "new-fresh-agent", "comments" and "completeness" that concerns ${NEW} or one of the two drafts and has the severity wrong, contradiction, missing or unsupported: is it resolved in the present text? Quote nothing for resolved ones. List the unresolved ones.
2. Read ${NEW} in full once more as the receiving agent. Look for errors that the corrections introduced: a table whose numbers do not match its new caption (recompute the TTFT table of section 3.4 from collected.json: arms a0 and a, medians of ttft_max over the 3 repetitions per cell, and the fall in percent from unrounded medians; check the commit of both arms), section numbers or question labels that no longer exist (S1 to S4, N1 to N7, X1 to X10, stage 1 to 3, tree A to F, [C1], [D1], [D2]), steps of section 5.2 whose numbering or cross-references broke, the command lines of section 5.1 (is the quoting of the pgrep line right inside a Markdown code block: the file should show a single backslash before each dot; say what the file holds), sentences that now contradict each other.
3. Check the statements that the corrections added and that round 1 did not see: "Qwen3.5 4B has 16 key heads and 32 value heads per layer" (find it in the code or config of 72e1191804, for example the generated geometry or the tests; if you cannot find it, say unsupported); "It is jhan's only issue on numerics, and it was opened during the first AMX PRs" (gh issue list --repo positron-ai/tron --author jhan-positron --state all --limit 60); "That commit differs from 775bba7661 in comments and tests only" (git diff --stat 8351e4ad52 775bba7661, and git diff 8351e4ad52 775bba7661 -- h src | grep '^[+-]' | grep -v '^[+-] *//' | head -40); the normalization cases "at lines 405, 434 and 462 of t/t_gated_delta_net.cpp at 775bba7661"; "our chain and block cases, from line 2840 on"; the scripts advice of section 6.3 against the script texts in /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121 and ../gdn-20261120.
4. The two drafts: are the round-1 points on them resolved? Does the #5433 draft table match collected.json (same arms as above)? Is anything in the drafts now inconsistent with the handoff?
`,
  },
  {
    key: 'recheck-split',
    prompt: `
## Your part: the SPLIT handoff
1. For every round-1 finding of the lists "split-update" and "completeness" that concerns ${SPLIT} and has the severity wrong, contradiction, missing or unsupported: is it resolved in the present text? List the unresolved ones.
2. Run "diff ${SPLIT_BEFORE} ${SPLIT}" and read every changed passage in its surroundings. Then walk the question flow again and write down, for each combination, the instruction the file gives: Q4 = the model's branch / main / head of PR #3221 / no answer; then, for Q4 = the model's branch: Q2 = yes / no / no answer, times Q5 = now / hold / no answer. Report every combination with no instruction, with two different instructions, or with an instruction that another section contradicts (sections 1, 2.2, 2.3, 3, 5, 8.1, 8.3, 8.4, 9, 11). Check also Q3 (the measurement branches) against Q2 and Q5.
3. Check the facts that the corrections added: "11 of the 12 have the review state changes requested. Only #5486 is approved" (gh pr view each of 3206 5345 3205 3221 5023 5486 5024 3689 3690 3692 3694 3695 --json reviewDecision); "GitHub reports PR #3689 as conflicting" (gh pr view 3689 --json mergeable,mergeStateStatus); the old TTFT medians of the arm orig in the reboot trap (0.384 s, 1.897 s, 2.91 s: recompute from collected-controls.json, medians of ttft_max per cell for arm orig; name the three cells); "The arms orig0, st and st0 have no old value" against section 7.5 of the file (which arms does its control start run, and does the trap describe them correctly); the pgrep line of section 7.1 (what the file holds; is the quoting right); the second Slack reference in [R18].
4. Read sections 0 to 3 once more as the agent that must do the split. Is anything you must do first unclear? Is jhan's decision list D1 to D10 untouched (compare with the version before)? Does any new sentence state a reading or a view of the writing session as jhan's decision or as a fact?
`,
  },
]

phase('Recheck')
const results = await parallel(TASKS.map(t => () =>
  agent(COMMON + t.prompt, { label: t.key, phase: 'Recheck', schema: FINDINGS })
    .then(r => ({ key: t.key, result: r }))
))
return results.filter(Boolean)
