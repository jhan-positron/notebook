export const meta = {
  name: 'verify-handoff',
  description: 'Read-only check of the issue 4934 handoff file: facts against records, plain-English rules',
  phases: [{ title: 'Verify', detail: 'facts checker + plain-English checker in parallel' }],
}
const H = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4934/handoff.md'
const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      quote: { type: 'string', description: 'the exact phrase in handoff.md' },
      problem: { type: 'string' },
      evidence: { type: 'string', description: 'file:line or command output that shows it' },
      fix: { type: 'string', description: 'the corrected phrase' },
      severity: { type: 'string', enum: ['wrong', 'unverifiable', 'style'] },
    }, required: ['quote', 'problem', 'evidence', 'fix', 'severity'] } },
    checked: { type: 'string', description: 'one paragraph: what was checked and found correct' },
  },
  required: ['findings', 'checked'],
}
phase('Verify')
const common = `READ-ONLY task. Do not modify any file, do not ssh to any machine, do not run runtron, builds or tests. All paths are under /home/jhan/workspace/intel-AMX/ unless absolute. The file under review is ${H} (a handoff for resuming the issue #4934 work on branch jhan-vnnik-5-i4934). Return findings only for things you could show to be wrong or unverifiable; do not pad.`
const [facts, english] = await parallel([
  () => agent(`${common}
Check every factual claim of the handoff against its source:
- Every path and file it names exists (use ls / test -e). For 3bda-only paths under /var/tmp/jhan, check the records instead: exec/results/i4934-r2/build-fix.txt, steps.txt.
- Every number (assertion counts, cases, percentages, durations, times, pids, sha prefixes) matches its record: exec/results/i4934-r2/tests-fix.txt, tests-fixks.txt, build-fix.txt, steps.txt; exec/results/i4934-E-cpu/summary.md; exec/results/i4934-E-fpga/summary.md; exec/results/i4934-abl-cpu/summary.md; exec/results/i4934-trace2/attn-*.txt and spans-*.txt; exec/logs/i4934-r2-probe.log; exec/logs/i4934-chain2.log; exec/results/i4934-E2-cpu/rt/ (list it); the status file VNNIed-K-in-place/issue4934/status.md.
- Every command it gives matches the script's real usage: read exec/i4934-20261015/launch-chain2.sh, chain-r2.sh (head of file), probe-r2.sh (the SKIP_OURHALF variable and how campaign-rot.sh decides to skip a cell: grep 'average tok/s'), pr_tables.py (its argparse options), gen_report.py (its usage docstring), trace_spans.py, attn_forward.py, spans_compare.py (their usage docstrings), exec/sync4424-20261002/summarize.py (WEDPERF_ARMS / WEDPERF_PAIRS).
- The git facts: git -C /home/jhan/workspace/ai-runs/tron-i4934 log --oneline 175b1837b9..HEAD (7 commits, head 9b30b2074d), git status, and whether the branch exists on origin (git -C /home/jhan/workspace/ai-runs/tron-i4934 ls-remote --heads origin jhan-vnnik-5-i4934; network allowed for this one read).
Report each mismatch with the exact quote, the evidence and the corrected phrase.`, { label: 'facts', schema: FINDINGS }),
  () => agent(`${common}
Run the plain-English Check mode of the user's rules on the handoff (the rules are in your CLAUDE.md context: define a term at first use or in the Words used here table, one claim per sentence, numbers with units and meaning, citations after the sentence, no idioms or metaphors, bullets for several points, short sentences without semicolons). Also the memory rule 'English banned words' (never use: convoy, refund, "in disguise", swept). Report only real violations with the exact phrase and a corrected phrase; a term defined in the Words used here table or inline at first use is not a violation. Do not report violations inside fenced code blocks or file paths.`, { label: 'english', schema: FINDINGS }),
])
return { facts, english }