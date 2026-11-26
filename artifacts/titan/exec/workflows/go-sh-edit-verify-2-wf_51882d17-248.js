export const meta = {
  name: 'go-sh-edit-verify-2',
  description: 'Second adversarial check after the round-1 corrections: new sentences against evidence, the kept tests, the stricter guard, regression, plain English, and the second draft of the answer',
  phases: [{ title: 'Verify', detail: '6 agents, read-only except their own scratch folders and the sandbox tests' }],
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
    round1_not_resolved: { type: 'array', items: { type: 'string' }, description: 'round-1 findings of your scope that are still open and not in the left-on-purpose list (one short line each)' },
    checked_ok: {
      type: 'array',
      items: { type: 'object', properties: { claim: { type: 'string' }, evidence: { type: 'string' } }, required: ['claim', 'evidence'] },
    },
    not_checked: { type: 'string' },
  },
  required: ['findings', 'round1_not_resolved', 'checked_ok', 'not_checked'],
}

const HEAD = 'First read ' + G + '/BRIEF-verify.md in full, then ' + G + '/BRIEF-verify2.md in full. Together they define the folders (C, S, T, LIST, G, E, MEM), what happened, the measured facts, the policy for notes, what was left on purpose, the report format and the hard rules. Your label is "@L@" (your scratch folder is ' + G + '/agents3/@L@/). Then do this:\n\n'

const SCOPES = [
  { label: 'delta-A', scope:
    'Scope: S/go.sh.md, S/local.sha.md, S/go2.sh.md, S/go2.sha.md, C/tmp/agent-scratch/w120-2026-11-15/rx.sh.md, C/results/go-T72-20261117T221209Z.log.md, their inputs in T/ann (go.overview, go.c01, local_sha.overview, local_sha.c01, go2.overview, go2_sha.overview, rx.overview, go_log.overview), and the matching files in G/diffs2.\n' +
    'Take EVERY sentence that is new or changed (the "+" lines of the diffs), split it into single claims, and try to refute each claim with evidence that you collect yourself (read the scripts, the log, S/local.sha, the two session records, the notes file about Jeremy, S/build_facts.py, S/facts_text.py, S/facts_text4.py, the files in E and their stored outputs; compute checksums yourself).\n' +
    'Check every [RefN] that a new sentence cites: it exists on the page, its number continues the list, its path exists, and its text holds what the sentence needs. Check the line numbers and times that the new text names. Check that the generated page holds exactly the text of its input (search each new input sentence in the page). Check the format rules of T/BRIEF.md section 5 for the changed fields (purpose one or two sentences, a segment text up to 6 bullets, role at most 14 words).\n' +
    'Then go through the round-1 findings of these files in G/verify-findings.json and say which are not resolved.' },
  { label: 'delta-B', scope:
    'Scope: S/build_facts.py.md, S/facts_text.py.md, S/facts_text4.py.md (inputs T/ann/build_facts.overview.json, T/ann/build_facts.c02.json, T/ann/facts_text.overview.json, T/ann/facts_text4.overview.json), the hand-written S/FACTS.md.md, S/facts.json.md and C/new-test-kernel/whole-chip-rerun-7200.html.md, LIST, T/BRIEF.md (point 8 of section 7), T/make_list.py, and the matching files in G/diffs2.\n' +
    '1. Take EVERY new or changed sentence (the "+" lines), split it into single claims, and try to refute each claim with evidence that you collect yourself. Do not run the tests in E (another agent does): read their stored outputs E/*.out and their code instead.\n' +
    '2. LIST: check the 8 changed places. Check that the counts in the text fit the reference list (session records, files outside crb), that [Ref3], [Ref7], [Ref8], [Ref9] hold what the new text needs, that the paths of [Ref8] and [Ref9] exist relative to C, and that no other sentence of LIST counts references or files in a way that the new entries made false (search for "two", "three", "six", "6 references", "outside").\n' +
    '3. T/make_list.py: review the new constants and the function check_two_texts_go line by line. For each sentence of the open point "Two texts of go.sh" in LIST say which test of the function guards it, and which sentences have no guard. Run `python3 ' + G + '/guard_test.py ' + G + '` and `python3 T/make_list.py --check` and report the output. Try to find a state of the input files in which the guard passes although a sentence of the open point is false (reason about it, and test it on copies in your scratch folder when you can).\n' +
    '4. The hand-written files: the changed table rows are still valid rows, the new reference entries [Ref10] (FACTS.md.md) and [Ref21] (facts.json.md) continue their lists and are cited, the new bullet of FACTS.md.md stands after the bullet that defines `S`, and the Short version of FACTS.md.md still has at most three sentences.\n' +
    '5. Go through the round-1 findings of these files in G/verify-findings.json and say which are not resolved.' },
  { label: 'kept-tests', scope:
    'Scope: the folder E (' + E + ').\n' +
    'You are the ONE agent that may run the three tests: `python3 ' + E + '/check_line20.py`, `python3 ' + E + '/check_facts_build.py` (about one minute), `python3 ' + E + '/check_start_command.py`. Run them one after the other, never two at a time. Before you run them, read common.py and the three scripts in full and confirm for each one: it writes only below E/work-..., it removes that folder at the end, it cannot write into S, C/results, C/new-test-kernel or any other real folder, it runs no ssh, and the only script text of the test that it executes is a copy that stops before a benchmark can start (say at which line and why).\n' +
    'Then check: (1) each run prints ALL PASS and its output equals the stored file E/<name>.out except for values that change from run to run (times, process ids, boot id, load); list every other difference. (2) After the runs: no work folder and no __pycache__ folder is left in E, and S/FACTS.md, S/facts.json, S/go.sh, S/local.sha have the sha256 values and file times of before your runs. (3) Does each PASS line test what its text says? Read the condition behind every r.line(...) call and report each one that can pass while its text is false (for example a comparison that is vacuous). (4) check_start_command.py tests the text of C/new-test-kernel/manual-run/run.sh: confirm that it reads that file, and that the three states (asrun, newonly, newboth) are built as its header says. (5) E/go.sh.as-run-2026-11-17 has the sha256 that S/local.sha lists for go.sh, and differs from S/go.sh in line 20 only. (6) The headers and comments of the four Python files: are they true, and are they plain English (short sentences, one claim per sentence, no idioms)?\n' +
    'Also say whether a reader who has only the folder E and the project folder can repeat the three claims that the companions cite from it: "with the old line 20 put back, go.sh has the sha256 that local.sha lists", "with the edited go.sh the build ends with status 1 and writes no file", "with the old line 20 it passes".' },
  { label: 'regression2', scope:
    'Scope: nothing changed that should not have changed, in the final state.\n' +
    '1. Recompute the sha256 of all 268 files of G/before.json. The set of changed files must be exactly the 28 files of G/changed2.json. Report every other difference.\n' +
    '2. Read all 28 diffs in G/diffs2 in full. For each hunk decide whether it is an intended correction for the edit of go.sh line 20, the mechanical effect of a rebuild (byte count, sha256 of the source, the left cell of row 20), or neither. Report every hunk that is neither. Confirm for each changed annotation input that the JSON loads, that only the intended fields changed (compare the parsed objects of the backup and of the present file key by key, and list every changed key path), and that the generated companion was built after the last change of its input (file times).\n' +
    '3. Run `python3 T/companion_tool.py verify-all` (wanted: 33 lines with "left column equals the source", status 0), check-overview on the 9 changed overview files, check-ann on the 3 changed chunk files, and `python3 T/make_list.py --check`.\n' +
    '4. Evidence files: S/local.sha, S/go2.sha, S/go2.sh, S/ra.sh, the three spec files, S/FACTS.md, S/facts.json, C/new-test-kernel/whole-chip-rerun-7200.html and C/new-test-kernel/manual-run/run.sh have the content of before (where G/before.json or the backup holds them; for run.sh compare with ' + G + '/../startcmd/direct/cmd.txt) and their old file times. `diff` of the backup go.sh against S/go.sh shows exactly one changed line.\n' +
    '5. Links: every relative link of LIST resolves to an existing file. Every reference path that the NEW text names exists (the folder E and its 8 files, C/jeremy-plan-constraints-2026-10-30.md, the two session records).\n' +
    '6. The 44 data companions are byte-equal to the backup.\n' +
    '7. Leftovers: files named *.tmp, *.bak, *.orig, __pycache__ folders, work-* folders, or files newer than 2026-11-24 12:00 local time in S, T, E, C/new-test-kernel and C/results that are neither in G/changed2.json nor one of the 8 files of E nor a companion that was written again with equal content. Report each one.\n' +
    '8. Go through the round-1 findings of the agent "regression" in G/verify-findings.json and say which are not resolved.' },
  { label: 'english2', scope:
    'Scope: language and format of the NEW text only: the "+" lines of all files in G/diffs2 (skip the diff of go.sh itself and the mechanical lines with byte counts and checksums), and the memory notes MEM/crb-go-sh-remove-boot-id-todo.md (whole file, it was rewritten), MEM/crb-whole-chip-rerun-7200-2026-11-17.md (lines 15, 19 and 22), MEM/crb-whole-chip-code-data-list-2026-11-21.md (lines 17, 19 and the bullet on go.sh), MEM/MEMORY.md (the line on go.sh).\n' +
    'Check every new sentence against the plain-English rules that you were given: no idioms or metaphors; one claim per sentence (a sentence with "because", "since", "which means", "so that", a colon that joins two full claims, or a semicolon is a candidate); short sentences; a term is defined at first use on its page or stands in the word list of the page (check "Jeremy", "block", "sha256", "facts sheet", "check 20", "sha-local", "build_facts.py", "facts_text4.py", "stored sheet", "launch", "the text that ran", "transcript"); numbers carry units; a citation follows a sentence. No pronoun for a person whose pronouns are not stated (search for he, his, him, she, her).\n' +
    'Check consistency of wording across the pages. For each of these facts collect every wording that the new text uses and report real differences in meaning: the date of the edit; what was edited; the old and the new message (exact strings); the name of the older text ("the text that ran"); the stored facts sheet ("the stored sheet", "the stored file", "the stored build"); the test folder and its scripts; who asked for the edit; what happens in a new build ("fails check 20", "stops", "writes no file").\n' +
    'Then go through the round-1 findings of kind "style" and of the agent "english" in G/verify-findings.json and say which are not resolved. Weigh the severity honestly: report as medium only what makes a reader misunderstand a fact. Give a proposed replacement sentence for every finding.' },
  { label: 'answer2', scope:
    'Scope: the second draft of the answer to the user and the memory notes.\n' +
    '1. Read ' + G + '/DRAFT-answer2.md. It holds 14 claims, D1 to D14. Try to refute EACH claim with evidence that you collect yourself. Do not run the tests in E (another agent does): read the code of the tests and their stored outputs E/*.out, and repeat small pieces of logic on copies in your scratch folder when you need to (never run a copy of go.sh outside a fake HOME that lacks rx.sh). For D4 to D6 read C/new-test-kernel/manual-run/run.sh, S/go.sh, S/ra.sh and C/tmp/agent-scratch/w120-2026-11-15/rx.sh line by line. For D12 recompute the counts (28 changed files by content against G/before.json; the companions written again with equal content by file time; the files in E). For D14 read the memory note and S/go.sh.\n' +
    '2. For each claim say: true, false, or stated too strongly, and what the user would be misled about. Then say what is MISSING: a consequence of the edit that the user must know to decide the next step and that no claim covers. Look again at the three points that the first check found missing (do not rewrite local.sha; the two generators need opposite states of go.sh; what a stop during a run prints) and say whether the draft now covers them.\n' +
    '3. Read the four memory notes MEM/crb-go-sh-remove-boot-id-todo.md, MEM/crb-whole-chip-rerun-7200-2026-11-17.md, MEM/crb-whole-chip-code-data-list-2026-11-21.md and MEM/MEMORY.md. Try to refute each sentence that speaks about go.sh, local.sha, go2.sha, run.sh, the copy on CRB, build_facts.py, make_list.py, the folder E or the edit of 2026-11-24. Check that the notes do not contradict each other or the draft, and that every file, function and line number they name exists.\n' +
    '4. Go through the round-1 findings of the agent "answer" in G/verify-findings.json and say which are not resolved.' },
]

phase('Verify')
const results = await parallel(SCOPES.map(s => () =>
  agent(HEAD.replace(/@L@/g, s.label) + s.scope, { label: 'verify2:' + s.label, phase: 'Verify', schema: SCHEMA })
    .then(r => ({ label: s.label, result: r }))
))
const ok = results.filter(Boolean).filter(r => r.result)
const missing = SCOPES.map(s => s.label).filter(l => !ok.some(r => r.label === l))
log('agents returned: ' + ok.length + ' of ' + SCOPES.length + (missing.length ? ' (missing: ' + missing.join(', ') + ')' : ''))
log('findings: ' + ok.reduce((n, r) => n + r.result.findings.length, 0) + ', round-1 not resolved: ' + ok.reduce((n, r) => n + r.result.round1_not_resolved.length, 0) + ', claims checked ok: ' + ok.reduce((n, r) => n + r.result.checked_ok.length, 0))
return { missing, results: ok }
