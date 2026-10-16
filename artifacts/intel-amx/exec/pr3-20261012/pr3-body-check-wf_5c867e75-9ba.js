export const meta = {
  name: 'pr3-body-check',
  description: 'PR3-handoff.md step 7: check the PR-3 body against the result files, the code, the handoff rules and plain English; two refuters per finding',
  phases: [
    { title: 'Check', detail: 'five lenses over exec/pr3-20261012/pr-body.md' },
    { title: 'Verify', detail: 'two refuters (accuracy, scope) per must-fix/should-fix finding' },
  ],
}
const BODY = '/home/jhan/workspace/intel-AMX/exec/pr3-20261012/pr-body.md'
const W = '/home/jhan/workspace/ai-runs/tron-split-pr3'
const E = '/home/jhan/workspace/intel-AMX/exec'
const HANDOFF = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR3-handoff.md'
const COMMON = `You check the description text (the "body") of PR-3 of the PR 4424 split before it is posted on GitHub. READ-ONLY: never edit or create files; never run git commands that change state; no builds.

The body: ${BODY} (Markdown, about 480 lines). It describes the branch jhan-vnnik-3-shared-save at head 80bce9a08d (worktree ${W}; the diff is \`git -C ${W} diff jhan-vnnik-2-amx HEAD\`, 9 files), which replaces the per-row scatter store of the packed K plane with a block save shared with the idle main helper threads. The base of the stack is main at 72308ec90c, the layout PR is #4868 (82d05e94be), the kernel PR is #4887 (0ee8671d35).

The result files the body's numbers come from:
- cells: ${E}/results/pr3-E-cpu/summary.md (the arm and pair tables; TPS and TTFT means, sample sd, paired deltas with sd, n, t) and rt-results.txt (the arms' binaries, sha256, commit ids, the run headers, "started" date);
- builds and tests: ${E}/results/pr3-20261012/ (build-pr3.log, build-pr3nd.log, build-pr3rm.log with "build rc=0 in N s"; build-pr3.txt; tests-pr3.txt, tests-pr3nd.txt, tests-pr3rm.txt; tests-pr3-t_amx_numerics.out, tests-pr3rm-t_amx_numerics.out, tests-pr3-t_amx_numerics-killswitch.out; mutation1-run.out, mutation1-result.txt, mutation2-run.out, mutation2-result.txt, tests-pr3-t_k_vnni_layout-restored.out, tests-pr3-t_llama_unit-restored.out; ingest-test-pr3.txt; plugin-calls-pr3.txt; format-pr3.txt; lint-notes-pr3.txt; host-suite-pr3.txt and host-suite-pr3.log; smoke/cpu-p1024, smoke/cpu-p8192, smoke/fpga-p1024 with smoke.txt and validate.txt; steps.txt);
- the syntax matrix: ${E}/pr3-20261012/pr3check-out-r2/summary.txt and matrix-r2.log (on the final head);
- the design-evidence traces cited in the Background: ${E}/results/vnnik2-trace-20260915/analysis.md (rows vnni0-tp2, ab-tp2, ab-tp4: Save K us/layer, ns/row, Save V, main helpers counts) and ${E}/results/vnnik-trace-20260914/analysis.md (rows base-tp2, base-tp4), and ${E}/results/vnnik2-20260915/summary.md (ab vs vnni0 TTFT);
- the kernel PR's body, whose numbers and stack table the PR-3 body quotes: ${E}/pr2-20261011/pr-body.md (the live copy).
The rules the body follows: ${HANDOFF} section 6 (sections and their order, present tense, no change history or review narration, measurements with provenance only, comparators = base, the kernel PR's head and its kill-switch run, no PR 4424-era comparator in Measurements but the 2026-09-14 traces allowed in the Background with date and arms, a pending measurement as its own subsection, no clock times, no workspace paths, no comparison with another head's assertion counts in Verification, every term defined at first use with a Words table, one claim per sentence, numbers with units, no idioms, no names of people, the stack table row for PR-3 must agree with the kernel PR body's row) and section 5.5 (what PR-3 can claim). The plain-English rules (the plain-english skill) apply to the whole body.

Findings: file = the body path, line = the line number in the body, severity must-fix (a wrong number, a claim the files or the code do not support, a rule of section 6 broken, a term a newcomer cannot follow), should-fix (an imprecise or misleading sentence, a missing definition, a plain-English violation that hurts reading), nit (wording). Every must-fix or should-fix carries the exact old_text (a substring of one line of the body, verbatim, occurring exactly once in the file) and new_text. Quote the evidence (file and line, or the row of the table) for every finding. Do not invent findings: an empty list is valid.`

const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  file: { type: 'string' }, line: { type: 'integer' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
  category: { type: 'string' }, title: { type: 'string' }, detail: { type: 'string' }, evidence: { type: 'string' },
  old_text: { type: 'string' }, new_text: { type: 'string' } }, required: ['file', 'line', 'severity', 'category', 'title', 'detail', 'evidence'] } },
  summary: { type: 'string' } }, required: ['findings', 'summary'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, better_fix: { type: 'string' } }, required: ['refuted', 'reason'] }

const LENSES = [
  { key: 'numbers', prompt: `${COMMON}

Your lens: every number in the body against the result files. Check each value of the arm table (15 rows: TPS, sd, TTFT, sd per cell and arm), the pair table (15 rows: percentages, TPS and ms deltas, paired t, inside/beyond, the band = max(2 x larger sd, 0.4 TPS or 0.15 s) computed from the arm table), the Short version's numbers, every bullet and sentence of the six Measurements subsections, the build times, the test-count table, the kill-switch counts, the two mutation paragraphs (the FAILED line numbers, the counts, the captured values), the Haskell suite line, the plugin table, the host-suite lines, the token-identity table, the Background's trace numbers (858 us, 105 ns, 80 us, 60 us, 274 us, 281 us, 289 to 316 us, 7 and 8 helpers; the record's exact values may round), the kernel PR's numbers the body quotes (+5.4 %, +9.5 %, +100 ms, -523 ms, -11.0 %, -18.3 %, +674 ms, +64.9 s), the dates, and the commit ids. Recompute every band, every "inside"/"beyond" and every rounded percentage from the files. Report every mismatch as must-fix with the file value.` },
  { key: 'code', prompt: `${COMMON}

Your lens: every mechanism claim of the body against the code at HEAD 80bce9a08d in ${W}: the Short version, the Background (the three store ways, the sharing paragraph, the three unshared cases), every Words row that describes code (store_block, transpose, present mask, set_k_row/set_k_block, run and unit, minibatch, worker index, window and watchdog, generated plugin, k_store_shared's conditions, the completion marks and credits), every bullet of "The changes" (file by file: the constants, the assert, the transpose stages and shuffle count, the window fields and sizes, the memory the window adds, the protocol and memory orders, the deadlock argument, the generator's emission, the spec checks, the two tests: masks, counts of comparisons, sections, what the three-thread section checks, the second window), the Verification's CI coverage sentences (nix/cmake-tron-test-build.nix, .github/workflows/cmake-single-platform.yml, gcp-nix.yml's Test ingest job and draft filtering), and the Open items (the masked path's line count, the watchdog constants, the 128 bound, the cost-data claim about config/test-benchmarks.json rows, the legacy lane's configure line). Report every claim the code does not support as must-fix, and every imprecise one as should-fix, with the code citation.` },
  { key: 'rules', prompt: `${COMMON}

Your lens: the handoff's rules for the body (${HANDOFF} section 6, and section 3 deviation 10, section 5.5) and the consistency with the kernel PR's body (${E}/pr2-20261011/pr-body.md). Check: the nine sections in the prescribed order with the prescribed headings; the Short version is three sentences; present tense, no change history or review narration ("before/after", "previous", "round"); no clock times; no workspace paths; measurements keep provenance (commit id and date); no comparator from the PR 4424 era inside Measurements (the Background may cite the 2026-09-14 traces with date, arms and model: check that it does); no comparison with another head's assertion counts inside Verification (a count may be stated, not compared); every pending measurement, if any, in its own subsection; the stack table's PR-3 row equals the kernel PR body's PR-3 row text; the kernel PR's Open item on the scatter store is answered by this body's measured result; no names of people; the attribution line last; the Words table rows the handoff lists as additions are present (block save, store_block, set_k_block, transpose, present mask, work unit, window, main helpers, worker index, join, watchdog, generated plugin, code generator, LoopyTronSpec, cabal, Sydtest, fourmolu, tp4, head and headoff, mutation check, lint-notes); the Open items the handoff lists are all present (the masked partial-block path, the single-token store, the watchdog and the worker cap, kv_mul other than 4, the kill switch and #4444 with the measured tokens, the cost rows, the benchmark-binary mismatch, the CI gap #4865) plus the control difference; the CI coverage subsection's six claims. Also check that the body does not claim what section 5.5 forbids (no AMD numbers, no kv_mul 3/8 numbers at this head, "TPS unchanged" only as a measured pair). Report each rule broken as must-fix with the sentence.` },
  { key: 'plain', prompt: `${COMMON}

Your lens: load the skill plain-english with the Skill tool (skill name exactly "plain-english") and run it in Check mode over the whole body: every term defined at first use (code names, acronyms, metrics; a term defined in the Words table counts as defined only if the Words table comes before its first use in reading order, or the first use carries an inline gloss; the Short version and the Background come before the Words table, so their terms need inline glosses or must be common words), one claim per sentence (the splitting test: "because", "since", "which means", "so that", semicolons), numbers with units and a plain meaning, citations after a sentence in brackets, no idioms or metaphors, bullets for multi-point paragraphs, short sentences. Tables and code blocks are exempt from rule 2. Severity: must-fix for an undefined term a newcomer cannot follow or a wrong unit; should-fix for a multi-claim sentence or an idiom; nit for the rest. Give the exact phrase and the corrected text for each.` },
  { key: 'newcomer', prompt: `${COMMON}

Your lens: read the body once, top to bottom, as an engineer who has never seen this project, and report every place where you had to guess: a word whose meaning you could not find in the Words table or an earlier sentence, a sentence with two possible readings, a number whose meaning is unclear (what is good, what is bad), a comparison whose direction is ambiguous (which arm is faster), a table whose columns are not explained, a claim you could not connect to its evidence, and any contradiction between two parts of the body (for example a sentence in Measurements against the Short version, or Verification against The changes). Also judge whether the Short version alone tells a reader what the PR does, what changed in the measurements and what state it is in. Report each as should-fix (a real stumble) or nit (a small one) with a concrete fix.` },
]

phase('Check')
const perLens = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  async (res, l) => {
    if (!res) return { key: l.key, findings: [], summary: 'lens returned null' }
    const fs = res.findings.map((f, i) => ({ ...f, lens: l.key, id: `${l.key}-${i + 1}` }))
    log(`${l.key}: ${fs.length} findings (${fs.filter(f => f.severity !== 'nit').length} must/should)`)
    const serious = fs.filter(f => f.severity !== 'nit')
    const verified = await parallel(serious.map(f => () => {
      const claim = `Finding ${f.id} (${f.severity}, lens ${f.lens}) at body line ${f.line}: ${f.title}\nDetail: ${f.detail}\nEvidence: ${f.evidence}\nProposed old_text:\n${f.old_text || '(none)'}\nnew_text:\n${f.new_text || '(none)'}`
      return parallel([
        () => agent(`${COMMON}\n\nYou are a REFUTER (lens: accuracy). Try to refute this finding by reading the body, the result files and the code: is the claimed error real? Quote the actual lines. A finding about a number must be checked by recomputing from the result file. Default to refuted=true when you cannot confirm the error.\n\n${claim}`, { label: `refute:acc:${f.id}`, phase: 'Verify', schema: VERDICT }),
        () => agent(`${COMMON}\n\nYou are a REFUTER (lens: scope and fix). Refute this finding if it asks for something the handoff's body rules forbid or do not ask for, if its severity is overstated, if the proposed new_text is wrong, longer than needed, breaks a rule (adds a semicolon, a clock time, a path, a person's name, a claim without evidence), or if the old_text does not occur exactly once in the body (check with grep -c -F). If the finding is right but the fix is wrong, set refuted=false and give a better_fix. Default to refuted=true only when the finding itself is baseless.\n\n${claim}`, { label: `refute:scope:${f.id}`, phase: 'Verify', schema: VERDICT }),
      ]).then(vs => {
        const votes = vs.filter(Boolean)
        const refutes = votes.filter(v => v.refuted).length
        return { ...f, votes, status: refutes === 0 ? 'kept' : refutes === votes.length ? 'refuted' : 'contested', better_fix: votes.map(v => v.better_fix).filter(Boolean) }
      })
    }))
    return { key: l.key, summary: res.summary, findings: fs, verified: verified.filter(Boolean) }
  },
)
const all = perLens.filter(Boolean)
const kept = all.flatMap(l => l.verified.filter(v => v.status === 'kept'))
const contested = all.flatMap(l => l.verified.filter(v => v.status === 'contested'))
const refuted = all.flatMap(l => l.verified.filter(v => v.status === 'refuted'))
const nits = all.flatMap(l => l.findings.filter(f => f.severity === 'nit'))
log(`done: ${kept.length} kept, ${contested.length} contested, ${refuted.length} refuted, ${nits.length} nits`)
return { summaries: all.map(l => ({ lens: l.key, summary: l.summary })), kept, contested, refuted, nits }