export const meta = {
  name: 'go-sh-edit-verify-3',
  description: 'Third and last check: hunt for false statements in the final state of the corrections, in the kept tests, in the memory notes and in the final answer text',
  phases: [{ title: 'Verify', detail: '3 agents, read-only' }],
}

const G = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771/scratchpad/goedit'
const E = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory'

const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          quote: { type: 'string', description: 'exact quote, at most 300 characters' },
          input_file: { type: 'string' },
          kind: { type: 'string', enum: ['false', 'unsupported', 'inconsistent', 'missed', 'regression', 'style'] },
          evidence: { type: 'string' },
          proposed: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['file', 'quote', 'kind', 'evidence', 'severity'],
      },
    },
    round2_not_resolved: { type: 'array', items: { type: 'string' } },
    sentences_checked: { type: 'integer' },
    checked_ok: {
      type: 'array',
      items: { type: 'object', properties: { claim: { type: 'string' }, evidence: { type: 'string' } }, required: ['claim', 'evidence'] },
    },
    not_checked: { type: 'string' },
  },
  required: ['findings', 'round2_not_resolved', 'sentences_checked', 'checked_ok', 'not_checked'],
}

const HEAD = 'First read ' + G + '/BRIEF-verify.md, then ' + G + '/BRIEF-verify2.md, then ' + G + '/BRIEF-verify3.md, each in full. Together they define the folders (C, S, T, LIST, G, E, MEM), what happened, the measured facts, the policy for notes, what was left on purpose, what this round reports, the report format and the hard rules. Your label is "@L@" (your scratch folder is ' + G + '/agents4/@L@/). Then do this:\n\n'

const SCOPES = [
  { label: 'final-A', scope:
    'Scope: S/go.sh.md, S/local.sha.md, S/go2.sh.md, S/go2.sha.md, C/tmp/agent-scratch/w120-2026-11-15/rx.sh.md, C/results/go-T72-20261117T221209Z.log.md, LIST, T/BRIEF.md (point 8 of section 7), with their inputs in T/ann and the matching files in G/diffs3.\n' +
    'Take EVERY new or changed sentence (the "+" lines of these diffs), split it into single claims, and try to refute each claim with evidence that you collect yourself: read S/go.sh, the copy E/go.sh.as-run-2026-11-17, S/local.sha, S/go2.sh, S/go2.sha, S/ra.sh, C/tmp/agent-scratch/w120-2026-11-15/rx.sh, the log, the two session records (parse the JSON lines), C/jeremy-plan-constraints-2026-10-30.md, S/build_facts.py, S/facts_text.py, S/facts_text4.py, S/FACTS.md, and the code and the stored outputs of the tests in E. Compute checksums yourself.\n' +
    'Check every [RefN] that a new sentence cites: it exists on the page, its number continues the list, its path exists, and its text holds what the sentence needs. Check that each generated page holds exactly the text of its input. Check the counts in LIST (session records, files outside crb) against its reference list. Check that the text which each page gives for the tests in E fits what the test scripts do (for example: does check_line20.py change the local go.sh?).\n' +
    'Then go through the round-2 findings of these files in G/verify2-findings.json and say which are not resolved.' },
  { label: 'final-B', scope:
    'Scope: S/build_facts.py.md, S/facts_text.py.md, S/facts_text4.py.md, S/FACTS.md.md, S/facts.json.md, C/new-test-kernel/whole-chip-rerun-7200.html.md, with their inputs in T/ann and the matching files in G/diffs3. Also T/make_list.py (the new constants and the function check_two_texts_go) and the folder E (common.py, the three test scripts, their three stored outputs, the copy go.sh.as-run-2026-11-17).\n' +
    '1. Take EVERY new or changed sentence of the six pages (the "+" lines), split it into single claims, and try to refute each claim with evidence that you collect yourself.\n' +
    '2. T/make_list.py: read check_two_texts_go line by line. Is its docstring true (what it tests, what it does not test)? Does each die(...) message say what the test before it tests? Run `python3 ' + G + '/guard_test.py ' + G + '` (it writes only below G/guardtest) and `python3 T/make_list.py --check`, and report the output. Name every sentence of the open point "Two texts of go.sh" in LIST that still has no test, and say whether the docstring admits it.\n' +
    '3. The folder E: do NOT run the tests. Read the code. For each test script: is every sentence of its header true (what it writes, what it runs, where it stops, what it needs)? Does each PASS line of the stored output belong to a check whose condition tests what the text says? Are the stored outputs newer than their scripts and than common.py (file times)? Does any stored output differ from what the present code would print (compare the fixed parts of the lines with the r.line texts in the code)? Is go.sh.as-run-2026-11-17 byte-equal to the backup go.sh (G/backup/tmp/agent-scratch/w120-7200-2026-11-17/go.sh) and to the text of record line 295?\n' +
    '4. Regression in short: the set of files that differ from G/before.json is exactly the 28 of G/changed3.json; `python3 T/companion_tool.py verify-all` gives 33 lines with "left column equals the source"; S/local.sha, S/go2.sha, S/go2.sh, S/FACTS.md, S/facts.json and the HTML report are unchanged in content and file time; E holds exactly 8 files and no work folder and no __pycache__ folder; S, T, C/new-test-kernel hold no *.tmp, *.bak or *.orig file from this work.\n' +
    '5. Go through the round-2 findings of these files (and of the agents kept-tests, delta-B and regression2) in G/verify2-findings.json and say which are not resolved.' },
  { label: 'final-answer', scope:
    'Scope: the final answer to the user, ' + G + '/FINAL-answer.md, and the four memory notes.\n' +
    '1. FINAL-answer.md is the text that the user will read. Split EVERY sentence into single claims and try to refute each one with evidence that you collect yourself. Read C/new-test-kernel/manual-run/run.sh, S/go.sh, S/go2.sh, S/ra.sh, C/tmp/agent-scratch/w120-2026-11-15/rx.sh, S/local.sha, S/build_facts.py, S/facts_text.py, S/facts_text4.py, T/make_list.py, the code and the stored outputs of the tests in E (do NOT run them), G/before.json and G/changed3.json. Recompute every number in the text: 28 files and their split into kinds, 12 inputs, 9 rebuilt explanation files, 3 hand-written explanation files, 7 new and 3 changed lines of the list (diff LIST against its backup), 44 data explanation files, 33 code explanation files, 9, 8 and 12 checks, 27 checks, lines 15, 16 and 26, lines 16 and 25, line 12, lines 7, 13 and 19, line 2, line 4, status 4. Check the sentence "The last round found no false statement" last: it is a claim about THIS round, so judge it by your own result and say so.\n' +
    '2. Say for each claim: true, false, or stated too strongly. Say what the user would be misled about. Say what is MISSING: a consequence of the edit that the user needs for the three decisions at the end and that the text does not give. Say whether one of the three decisions is not a real open choice.\n' +
    '3. The text must follow the plain-English rules that you were given, because this user asks for them: a Short version of at most three sentences that a newcomer can follow, terms defined at first use (check: CRB, marker file, pid line, state line, go-direct.sh, local.sha, facts sheet, check 20, list generator, explanation file, boot-id task, agent briefing), no idioms, numbers with units. Report breaches of these rules for THIS text as style, with a replacement.\n' +
    '4. Read the four memory notes MEM/crb-go-sh-remove-boot-id-todo.md, MEM/crb-whole-chip-rerun-7200-2026-11-17.md, MEM/crb-whole-chip-code-data-list-2026-11-21.md and MEM/MEMORY.md. Try to refute each sentence that speaks about go.sh, go2.sh, local.sha, go2.sha, run.sh, the copy on CRB, build_facts.py, make_list.py, the folder E or the edit of 2026-11-24. Check that the notes do not contradict each other or the answer text, and that every file, function, count and line number they name is right.\n' +
    '5. Go through the round-2 findings of the agent answer2 and of the memory notes in G/verify2-findings.json and say which are not resolved.' },
]

phase('Verify')
const results = await parallel(SCOPES.map(s => () =>
  agent(HEAD.replace(/@L@/g, s.label) + s.scope, { label: 'verify3:' + s.label, phase: 'Verify', schema: SCHEMA })
    .then(r => ({ label: s.label, result: r }))
))
const ok = results.filter(Boolean).filter(r => r.result)
const missing = SCOPES.map(s => s.label).filter(l => !ok.some(r => r.label === l))
log('agents returned: ' + ok.length + ' of ' + SCOPES.length + (missing.length ? ' (missing: ' + missing.join(', ') + ')' : ''))
log('findings: ' + ok.reduce((n, r) => n + r.result.findings.length, 0) + ', sentences checked: ' + ok.reduce((n, r) => n + r.result.sentences_checked, 0) + ', claims checked ok: ' + ok.reduce((n, r) => n + r.result.checked_ok.length, 0))
return { missing, results: ok }
