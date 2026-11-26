export const meta = {
  name: 'gdn-split-handoff-check',
  description: 'Independent read-only checks of the GDN PR split handoff: facts, decisions, executability, plain English',
  phases: [{ title: 'Check', detail: 'six independent checkers, one lens each' }],
}

const FILE = '/home/jhan/workspace/intel-AMX/GDN/status/handoff-gdn-pr-split-20261122.md'
const MAT = '/home/jhan/workspace/intel-AMX/GDN/status/handoff-material'

const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          section: { type: 'string', description: 'section number or heading of the handoff' },
          quote: { type: 'string', description: 'the exact text of the handoff that is wrong, unclear or missing context (short)' },
          problem: { type: 'string' },
          evidence: { type: 'string', description: 'the command you ran and what it printed, or the file:line you read' },
          fix: { type: 'string', description: 'the corrected text or the concrete addition' },
          severity: { type: 'string', enum: ['wrong', 'gap', 'unclear', 'style'] },
        },
        required: ['section', 'quote', 'problem', 'evidence', 'fix', 'severity'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' }, description: 'short list of the claims you verified and found correct' },
    not_checked: { type: 'array', items: { type: 'string' }, description: 'claims in your scope that you could not check, with the reason' },
  },
  required: ['findings', 'checked_ok', 'not_checked'],
}

const COMMON = `
You check a handoff document. Another agent will use it to split one draft PR of the repository positron-ai/tron into four draft PRs. The document is ${FILE}. Five fact files that it cites are in ${MAT}/ (facts-cut.md, facts-switch.md, facts-partb.md, facts-tests.md, facts-scripts.md).

HARD RULES
- Read-only. Do not edit the handoff or any other file outside your scratchpad. Do not check out, commit, push or change any branch or working tree. Never run "git worktree prune". No ssh. No builds. No test runs. GitHub: read-only "gh pr view" / "gh api" GET only. Post nothing.
- Git: "git -C /home/jhan/workspace/ai-runs/tron-gdn-amx ..." with "git show <sha>:<path>", "git diff", "git log", "git grep <pattern> <sha> -- <path>". A plain "cd" prints a directory listing, so avoid it. The host git is 2.34.1.
- Report a finding only when you have evidence: a command output or a file:line. Do not report taste. Do not report that the document is long.
- Stay inside your lens. Other checkers cover the other lenses.
- Be exact in "quote": copy the words from the handoff, so that the author can find the place.
`

const LENSES = [
  {
    key: 'facts-repo',
    prompt: `${COMMON}
YOUR LENS: repository and GitHub facts in sections 1, 4, 5 (step 0), 6 and 8 of the handoff.
Check each stated fact against the repository and GitHub: commit ids and what they hold, branch names and whether they exist (local and on origin), base branches, PR states, labels, counts of files and added lines, file names of each part, function and symbol names (for example gdn_stats::env_enabled, attn_stats::env_enabled, gdn_block_kernel, advance(), normalized_query, amx_serves_128x4, store_query_rows, transpose_scores, group_heads_ok, exercise_page), the diff range "3bea58b788 to ddf843ad97 (12 files)", the statement that the folder changelog.d does not exist on the model's branch, the example changelog line, the statement that the live body of PR 5572 equals exec/gdn-impl-20261121/pr-body.md except one empty line, worktree paths (git -C /home/jhan/workspace/tron worktree list), and the checks I1 to I5 (would each command do what the text says; for example does the grep pattern of I3 really find nothing in a correct Part 0, given that the counters commit 0d69ef3ce8 itself may contain matching text such as "amx_gdn" or "block_kernel" in h, src or t?). For I3 and I4 run the grep on 0d69ef3ce8 and report what already matches there.
Also check the commands in step 0 of section 5 and in section 6 for syntax and for the ids they are said to print.`,
  },
  {
    key: 'facts-numbers',
    prompt: `${COMMON}
YOUR LENS: numbers and measurement facts in sections 4 (build trees), 7 and 11 of the handoff.
Sources of truth: /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/ (collected.json, comparison.json, collected-controls.json, comparison-controls.json, unit-tests.txt, unit-tests-noamx.txt, build-*.txt, tokens/, rt-results.txt), /home/jhan/workspace/intel-AMX/exec/logs/gdn-impl-20261121-*.log, /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/ (collected.json), /home/jhan/workspace/intel-AMX/exec/results/gdn-e4b-20261122/ (tokens/summary.txt, tests/summary.txt), the scripts in /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/ and /home/jhan/workspace/intel-AMX/exec/gdn-20261120/, the generated PR body /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/pr-body.md, and the page /home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html (large: grep it, do not read it whole).
Check every number of section 7.7 (TTFT and decode speed of the model's branch per cell, the TTFT fall ranges of Part 0, Part A and Part B alone, the decode changes, the GDN time 6.08 / 4.01 / 2.56 us and its unit and meaning, the cost of the counters, the score drift, the token numbers 185, 1 and 63, the join wait 3.3 ms to 10.9 ms), the token-check expectations of section 7.4 (which arm pairs were identical at the old commits, at prompt 1,024 and at prompt 4,096), the E4B facts of section 7.6 (35 of 42 layers, the layer list, 24 tokens, 1,048,584 bytes, 134.2 MB), the build times and the run-time estimates of sections 7.2 and 7.5 (126 runs, 27 runs, 21.4 minutes per 36 runs), "19 of 19 runs pass" and "109,130 assertions in 50 cases", the free disk space, and the descriptions of what build.sh, run-one.sh, campaign.sh, unit-tests.sh, token-check.sh, e4b-check.sh, e4b-tests.sh and pr-prep.sh do (inputs such as TAG, SHA, REG, TARGETS, CONF_FLAGS, ARMENV; the refusal rules; the rotation rule). Check that the proposed tags (s1, s2, s3, b0, b1, m0, m1, s1off, s2off, s3off, b1off) pass the tag rule of build.sh, and that an arm "without a counter switch" is possible with run-one.sh as the handoff describes.
Compute, do not estimate. Give the file and the key or line for every number.`,
  },
  {
    key: 'decisions',
    prompt: `${COMMON}
YOUR LENS: section 2 (decisions) and section 3 (the go) of the handoff, against what the user (jhan) really said.
Source of truth: the session record /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b.jsonl (JSON lines, large: do not read it whole). Write a small python script that prints, in order, every message with role "user" whose text is typed by the human (skip tool results, system reminders, task notifications and summaries; note that some human text is wrapped as "The user sent a new message while you were working: ..."), and the assistant text messages that hold the words "split", "four PRs", "open points", "Part B", "E4B", "branch names" or "go". Read at least everything from the first mention of splitting the PR ("break GDN PR to multi PR") to the end.
Check:
1. Each of D1 to D10: did jhan say it? Quote jhan's words. Is anything stated as decided that jhan did not decide, or decided differently?
2. Did jhan decide or ask for anything about the split that the handoff does not carry (for example reminders, the PR body content, the order of steps, what to do with PR 5572, which branch Part B sits on, E4B)?
3. Each of U1 to U8: is it honestly presented as NOT decided by jhan? Did the assistant earlier tell jhan something different from the default now written (for example about branch names, the timing file, the changelog lines, a test that reaches the kernels in E4B)? List each difference.
4. Section 3: jhan said at different times "Do not break PR yet, let's discuss first", "Do not create the new PR, still at discussion phase", and finally asked for this handoff file "that instructs another agent to implement the new PRs as we discussed". Does section 3 authorize any action that goes beyond what jhan decided? Name each one and say why.
5. The rules of /home/jhan/.claude/CLAUDE.md, /home/jhan/workspace/intel-AMX/CLAUDE.md and the repository file AGENTS.md (git -C /home/jhan/workspace/ai-runs/tron-gdn-amx show origin/main:AGENTS.md): does any instruction of the handoff break one of them?`,
  },
  {
    key: 'cold-git',
    prompt: `${COMMON}
YOUR LENS: you are the agent who must EXECUTE the handoff tomorrow, with no other context. Read the handoff and the fact files facts-cut.md, facts-switch.md, facts-partb.md and facts-tests.md. Judge sections 1, 3, 4, 5, 6, 8, 9 and 11 for the git and GitHub work (steps 0 to 5 and 10 to 13).
Walk through every step as if you did it (do not do it). For each step ask: do I know exactly what to do; which command; on which branch and worktree; what the check is; what to do when it fails? Use the repository read-only to test your reading (for example: does "git cherry-pick 775bba7661" onto a branch that holds the switch change of PR 1 conflict? Look at the lines both touch. Does the three-step method of section 6.2 give a Part 0 commit that can compile, given the facts in facts-cut.md? Does "git checkout X -- ." also remove files that Part 0 has and X lacks? Does the order of step 11 work, given that a PR needs its base branch on GitHub first? Can "gh pr create --base jhan-gdn-1-stats" work before that branch is pushed? Does closing PR 5572 first leave anything broken? Is the measurement branch recipe of section 6.5 executable as written, and does the "net change of PR 4" apply on top of it, given the three files that differ per facts-partb.md?).
Report: contradictions between sections, between the handoff and the fact files; missing inputs; steps in the wrong order; instructions that would lose code or tests; checks that cannot fail or cannot pass; anything a careful agent would have to guess.`,
  },
  {
    key: 'cold-measure',
    prompt: `${COMMON}
YOUR LENS: you are the agent who must EXECUTE the measurement part of the handoff tomorrow, with no other context. Read the handoff, the fact files facts-scripts.md, facts-tests.md and facts-switch.md, and the scripts in /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/ and /home/jhan/workspace/intel-AMX/exec/gdn-20261120/ (run-one.sh, models.gdn.yaml). Judge sections 7 and 10 and steps 6 to 9 of section 5.
Walk through every build, test run, token check and timed run as if you did it (do not do it; no ssh). For each ask: which script, which inputs, which tag, which model list, which output folder; is the arm possible with that build (for example: does the switch TRON_AMX_GDN_DISABLE exist in the build of that tag; is the model slug registered in that build; does the build tag hold the test programs named; is the baseline of each comparison the right one for the PR it supports; does each PR of the stack get a comparison against the head below it; is the arm "orig" at tag base comparable with tag s1, given that tag base was built by another script and at another time)?
Also check the logic of the evidence: does the plan give every claim that the four PR bodies will need (identity of Part 0, the GDN switch, the kill switch, E4B, cost of the counters with one shared switch) a run, and is any run without a use? Is anything required by section 1 ("builds with the option ON and OFF, unit tests, lint, token checks, timed runs with the system load" for every head) missing in section 7 for one of the heads? Are the time estimates consistent with each other? Is the rule "never a build and a timed run at the same time" compatible with the plan?
Report gaps, contradictions, wrong baselines, steps a careful agent would have to guess, and risks to the other users of the shared machine.`,
  },
  {
    key: 'plain-english',
    prompt: `${COMMON}
YOUR LENS: the writing rules. Read /home/jhan/.claude/skills/plain-english/SKILL.md and the term list in /home/jhan/workspace/intel-AMX/CLAUDE.md. Run the skill's Check mode on the handoff, but report through the findings list (do not output a corrected full text).
Rules to apply: no idioms, metaphors or uncommon words (also never the words convoy, refund, swept, "in disguise"); one claim per sentence; short sentences (flag sentences over 25 words or with more than one subordinate clause); bullets for multi-point paragraphs; every number with a unit and, where needed, a meaning; a "Short version" of at most three sentences that a newcomer can follow; every project term, code name, abbreviation and metric defined at first use or in "Words used here" (check each term that the text uses: is it in the list or defined inline? examples to test: slug, plugin, FPGA, lefthook, FTZ, DAZ, join wait, prefill, K tokens, bf16 tie, dispatch test, lint, squash, cherry-pick are general git words and need none); citations as an index in brackets after a sentence that carries the claim, with the list at the end (check that every [Rn] used exists in the list and every list entry is used); "prompt N", never "ctx N"; names of people (the handoff may name jhan; flag any other person named).
Also flag: a term used in two different meanings; a sentence a non-native engineer would have to guess at; a table cell that is a long paragraph.
Give at most 40 findings, the most harmful first. severity = style for pure wording, unclear when a reader could misread an instruction.`,
  },
]

phase('Check')
const results = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: SCHEMA })
    .then(r => ({ key: l.key, ...r }))))
const done = results.filter(Boolean)
const missing = LENSES.map(l => l.key).filter(k => !done.find(d => d.key === k))
if (missing.length) log(`checkers without a result: ${missing.join(', ')}`)
return {
  missing,
  counts: Object.fromEntries(done.map(d => [d.key, d.findings.length])),
  results: done,
}
