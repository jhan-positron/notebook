export const meta = {
  name: 'pr4424-desc-proposal',
  description: 'Find PR 4424 description statements made stale by the save_k fold, verify them, draft a <=100-word change proposal, check it',
  phases: [
    { title: 'Find', detail: 'four lenses over the live body vs the merged code' },
    { title: 'Verify', detail: 'three refuters per finding' },
    { title: 'Draft', detail: 'three drafts, three judges, one synthesis' },
    { title: 'Check', detail: 'plain-English check, fact check, word count' },
  ],
}

const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-merge-4774-2-4424/d4ac9706-06c9-4ef8-94c0-0ee3dd53e686/scratchpad'
const COMMON = `Read ${S}/facts.md FIRST (the task, the merged change, the measured facts, the file list, the rules). The live PR description is ${S}/pr4424-live-body.md (CRLF; use \`tr -d '\\r' < file | cat -n\` for line numbers). The code at the new head ba69cb513e is the worktree /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K (read only; never run git commands that change it; \`git -C <wt> show\`, \`git -C <wt> grep\` and reading files are fine). The fold diff is ${S}/fold.diff. Cite file:line evidence for every claim. Return raw data only.`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          line: { type: 'integer', description: '1-based line in the live body (tr -d \\r numbering)' },
          section: { type: 'string' },
          quote: { type: 'string', description: 'the exact stale phrase or sentence' },
          why_stale: { type: 'string', description: 'what the merged code or the measured facts make false or incomplete' },
          evidence: { type: 'string', description: 'file:line or result-file citations' },
          protected: { type: 'boolean', description: 'true when the line is inside body lines 1-27' },
          proposed_text: { type: 'string', description: 'present-tense replacement sentence(s), plain English, minimum change' },
        },
        required: ['line', 'section', 'quote', 'why_stale', 'evidence', 'protected', 'proposed_text'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    must_change: { type: 'boolean', description: 'true when leaving the text unchanged would state something false about the head ba69cb513e' },
    correction: { type: 'string', description: 'if the finding is right but its proposed text is wrong or breaks a rule, the corrected proposed text; else empty' },
  },
  required: ['refuted', 'reason', 'must_change', 'correction'],
}

const DRAFT = {
  type: 'object',
  properties: {
    edits: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          line: { type: 'integer' },
          old_text: { type: 'string', description: 'the exact text to replace (may be a phrase inside the line)' },
          new_text: { type: 'string', description: 'the replacement text; empty string for a pure deletion' },
        },
        required: ['line', 'old_text', 'new_text'],
      },
    },
    inserted_word_count: { type: 'integer', description: 'wc -w over the concatenation of all new_text values, computed by running wc' },
    notes: { type: 'string' },
  },
  required: ['edits', 'inserted_word_count', 'notes'],
}

const SCORE = {
  type: 'object',
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          draft: { type: 'integer' },
          accuracy: { type: 'integer', description: '0-10: every edit true of the head and the measured facts' },
          plain_english: { type: 'integer', description: '0-10: rule violations found, 10 = none' },
          coverage: { type: 'integer', description: '0-10: every confirmed must_change finding addressed' },
          minimality: { type: 'integer', description: '0-10: the author\'s sentences kept wherever still true' },
          word_count_ok: { type: 'boolean', description: 'recomputed with wc -w, <= 100' },
          recounted_words: { type: 'integer' },
          problems: { type: 'string' },
        },
        required: ['draft', 'accuracy', 'plain_english', 'coverage', 'minimality', 'word_count_ok', 'recounted_words', 'problems'],
      },
    },
    best: { type: 'integer' },
    grafts: { type: 'string', description: 'specific edits from the other drafts that the best draft should take' },
  },
  required: ['scores', 'best', 'grafts'],
}

const CHECK = {
  type: 'object',
  properties: {
    violations: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string' }, original: { type: 'string' }, fix: { type: 'string' } }, required: ['rule', 'original', 'fix'] } },
    false_statements: { type: 'array', items: { type: 'object', properties: { statement: { type: 'string' }, why_false: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['statement', 'why_false', 'evidence', 'fix'] } },
    word_count: { type: 'integer', description: 'wc -w over all new_text values, computed by running wc' },
    corrected_edits: { type: 'array', items: { type: 'object', properties: { line: { type: 'integer' }, old_text: { type: 'string' }, new_text: { type: 'string' } }, required: ['line', 'old_text', 'new_text'] } },
  },
  required: ['violations', 'false_statements', 'word_count', 'corrected_edits'],
}

// ---------- Find ----------
const LENSES = [
  { key: 'changes', prompt: `${COMMON}\nLens: the "## The changes" section (body lines 56-97). For every sentence that names save_k, save_k_helper, worker, helper, n_workers, TronCpp.hs, LoopyTronSpec.hs, t_llama_unit, the window or the join, check it against model.hpp, ingest/src/TronCpp.hs, ingest/test/LoopyTronSpec.hs and t/t_llama_unit.cpp at ba69cb513e. Report every statement the merged code makes false, incomplete or misleading, with a minimum-change present-tense replacement. Report nothing that is still true.` },
  { key: 'verification', prompt: `${COMMON}\nLens: the "## Verification" section (body lines 119-179). Compare every provenance sentence, build-setup claim and test-count row with the measured facts in facts.md (the result files under /home/jhan/workspace/intel-AMX/exec/results/savek2-20261008/ are the primary source: read steps.txt, tests-savek2.txt, tests-savek2rm.txt). Which sentences are false at the head ba69cb513e (for example claims that the head compiles to the same code as the tested commit, or assertion counts that changed)? Which rows were not re-measured at the fold and need a provenance note under jhan's rule that measurements keep commit + date provenance? Propose minimum present-tense replacements. Do not propose re-measurement text as a sentence inside a paragraph; if a pending measurement is needed, say so as a finding with proposed_text describing a subsection heading only.` },
  { key: 'rest', prompt: `${COMMON}\nLens: "## Words used here" (lines 29-55), "## Measurements" (98-118) and "## Open items" (180-190). Which statements does the merged fold make false or stale (for example the stacked-PRs item that lists PR #4774 as a PR still based on this branch, Words rows that describe the helper call, n_workers, or save_k)? Propose minimum present-tense replacements. Report nothing that is still true.` },
  { key: 'sweep', prompt: `${COMMON}\nLens: whole-body sweep, lines 1-190, with grep for every token of the fold: save_k, save_k_helper, helper, worker_ix, n_workers, worker, window, join, 4774, 4812, 4737, 6b939d25d2, 37064d72b2, 251563, 251478. For each hit decide whether the merged head makes the sentence false, incomplete or stale. Lines 1-27 are protected: report hits there with protected=true and no proposed_text beyond "protected, informational". Also look for statements elsewhere that the merge changes indirectly (counts of files, test-case descriptions, open items that are now done).` },
]

phase('Find')
log('Find: 4 lenses over the live body')
const found = (await parallel(LENSES.map(l => () => agent(l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS })))).filter(Boolean).flatMap(r => r.findings)
log(`Find: ${found.length} raw findings`)

// dedup by line: merge quotes/evidence, keep the first proposed_text and collect alternates
const byLine = new Map()
for (const f of found) {
  const k = f.line
  if (!byLine.has(k)) byLine.set(k, { ...f, alternates: [] })
  else byLine.get(k).alternates.push({ why_stale: f.why_stale, evidence: f.evidence, proposed_text: f.proposed_text })
}
const unique = [...byLine.values()].sort((a, b) => a.line - b.line)
log(`Find: ${unique.length} unique lines; protected hits: ${unique.filter(f => f.protected).length}`)

// ---------- Verify ----------
const REFUTE_LENSES = [
  'code truth: is the quoted text really false, incomplete or stale at ba69cb513e? Read the code. Default to refuted=true if you cannot show a concrete contradiction.',
  'rules: does jhan\'s rule set (facts.md "Task" and "Wording rules", the memory notes it lists) forbid this edit (protected section, change narration, trivial fact promoted, people named, clock times, workspace paths, earlier-head count comparisons)? If the edit is forbidden or unnecessary under those rules, refute it. Also check the proposed_text for plain-English violations and give a corrected text.',
  'reader necessity: would a reviewer who reads the description at head ba69cb513e be misled by the unchanged text? If the text is still true, or the staleness is a presentation detail that jhan would call noise, refute. Default to refuted=true if uncertain.',
]
phase('Verify')
const verified = await pipeline(unique.filter(f => !f.protected),
  f => parallel(REFUTE_LENSES.map((lens, i) => () => agent(
    `${COMMON}\nTry to REFUTE this finding about the live PR description. Finding: line ${f.line} (${f.section}). Quote: "${f.quote}". Claimed reason it is stale: ${f.why_stale}. Evidence given: ${f.evidence}. Proposed replacement: "${f.proposed_text}". Alternates from other finders: ${JSON.stringify(f.alternates)}.\nYour lens: ${lens}`,
    { label: `verify:L${f.line}:${i}`, phase: 'Verify', schema: VERDICT }))).then(vs => {
      const votes = vs.filter(Boolean)
      const keep = votes.filter(v => !v.refuted).length >= 2
      const must = votes.filter(v => v.must_change).length >= 2
      const corrections = votes.map(v => v.correction).filter(c => c && c.trim())
      return { ...f, keep, must, votes, corrections }
    }))
const confirmed = verified.filter(Boolean).filter(v => v.keep)
log(`Verify: ${confirmed.length} of ${verified.filter(Boolean).length} findings survive; must-change: ${confirmed.filter(c => c.must).length}`)
const expected = [77, 88, 95, 121, 132, 143, 187]
const missing = expected.filter(l => !confirmed.some(c => c.line === l))
log(`Verify: main agent's candidate lines not among the confirmed: ${missing.length ? missing.join(', ') : 'none'}`)
const protectedHits = unique.filter(f => f.protected)

// ---------- Draft ----------
phase('Draft')
const confirmedText = JSON.stringify(confirmed.map(c => ({ line: c.line, section: c.section, quote: c.quote, why_stale: c.why_stale, evidence: c.evidence, must: c.must, proposed_text: c.proposed_text, corrections: c.corrections })), null, 1)
const ANGLES = [
  'minimum words: change the fewest words that make every must-change statement true; prefer replacing one phrase inside the author\'s sentence over rewriting the sentence',
  'reader first: a newcomer reads each edited sentence on its own; every term it uses is defined in the body\'s Words table or inline; one claim per sentence',
  'completeness: address every confirmed finding (must and optional) as far as the 100-word budget allows, giving the Verification provenance the exact commit ids and counts',
]
const drafts = (await parallel(ANGLES.map((angle, i) => () => agent(
  `${COMMON}\nWrite the proposal of changes to the PR #4424 description that the merged fold requires. Confirmed findings (line, quote, why, proposed text, corrections from the verifiers):\n${confirmedText}\n\nHard constraints: (1) the inserted words over ALL edits total at most 100 (run \`wc -w\` on the concatenated new_text values through Bash and report the number; identifiers in backticks count as one word); (2) plain-English rules; (3) present tense, no change narration, no "now/was/previously/replaced/removed"; (4) never touch lines 1-27; (5) keep the author's sentences wherever the head keeps them true; (6) each edit = exact old_text to replace and its new_text, so that jhan can apply it by hand. Your angle: ${angle}.`,
  { label: `draft:${i}`, phase: 'Draft', schema: DRAFT })))).map((d, i) => ({ ...d, id: i })).filter(d => d && d.edits)
log(`Draft: ${drafts.length} drafts, inserted words ${drafts.map(d => d.inserted_word_count).join(' / ')}`)

const draftsText = JSON.stringify(drafts.map(d => ({ draft: d.id, edits: d.edits, inserted_word_count: d.inserted_word_count, notes: d.notes })), null, 1)
const judges = (await parallel([0, 1, 2].map(i => () => agent(
  `${COMMON}\nJudge these ${drafts.length} drafts of the proposal (each a list of edits: line, old_text, new_text):\n${draftsText}\n\nConfirmed findings they must address:\n${confirmedText}\n\nScore each draft on accuracy (check every new_text against the code at ba69cb513e and the measured facts), plain_english (apply the plain-English rules: terms defined, one claim per sentence, units, no idioms, short sentences; the no-history rule), coverage, minimality, and recount the inserted words with wc -w through Bash. Pick the best and name the grafts it should take from the others. Judge ${i}: ${['weigh accuracy highest', 'weigh plain-English compliance highest', 'weigh minimality and the author\'s voice highest'][i]}.`,
  { label: `judge:${i}`, phase: 'Draft', schema: SCORE })))).filter(Boolean)
const tally = {}
for (const j of judges) for (const s of j.scores) { tally[s.draft] = (tally[s.draft] || 0) + s.accuracy * 3 + s.plain_english * 2 + s.coverage + s.minimality + (s.word_count_ok ? 5 : -20) }
const bestId = Object.entries(tally).sort((a, b) => b[1] - a[1])[0][0]
log(`Draft: judge tallies ${JSON.stringify(tally)}; best = draft ${bestId}`)

let proposal = await agent(
  `${COMMON}\nSynthesize the final proposal. Winner: draft ${bestId}. All drafts:\n${draftsText}\n\nJudge verdicts (scores, problems, grafts):\n${JSON.stringify(judges, null, 1)}\n\nConfirmed findings:\n${confirmedText}\n\nProduce the final edit list: start from the winner, apply the grafts and fix every problem the judges name. Hard constraints unchanged: inserted words <= 100 (run wc -w through Bash and report), plain English, present tense, no change narration, lines 1-27 untouched, exact old_text per edit.`,
  { label: 'synthesize', phase: 'Draft', schema: DRAFT })

// ---------- Check ----------
phase('Check')
let rounds = 0
let lastCheck = null
while (rounds < 2) {
  rounds++
  const propText = JSON.stringify(proposal.edits, null, 1)
  const checks = (await parallel([
    () => agent(`${COMMON}\nCheck mode of the plain-English skill: list every rule violation in the new_text values of these edits (rule number, exact phrase, fix) and give the corrected edits. Also apply jhan's no-history rule (present tense, no change narration) and the wording rules in facts.md. Edits:\n${propText}\nCompute word_count = wc -w over all new_text values through Bash. false_statements: leave empty (another agent checks facts).`, { label: `check:english:${rounds}`, phase: 'Check', schema: CHECK }),
    () => agent(`${COMMON}\nFact check: try to find any statement in the new_text values of these edits that is false, unverifiable or misleading about the head ba69cb513e or the measured facts (read the code and the result files; check every commit id, count, file name and function name). Also check that each old_text exists verbatim in the live body at that line. Edits:\n${propText}\nReport false_statements with evidence and a fix; violations: leave empty (another agent checks English). Compute word_count = wc -w over all new_text values through Bash. corrected_edits = the edits with your fixes applied (or unchanged).`, { label: `check:facts:${rounds}`, phase: 'Check', schema: CHECK }),
  ])).filter(Boolean)
  lastCheck = checks
  const nViol = checks.reduce((n, c) => n + c.violations.length, 0)
  const nFalse = checks.reduce((n, c) => n + c.false_statements.length, 0)
  const counts = checks.map(c => c.word_count)
  log(`Check round ${rounds}: ${nViol} English violations, ${nFalse} false statements, word counts ${counts.join('/')}`)
  if (nViol === 0 && nFalse === 0 && counts.every(c => c <= 100)) break
  proposal = await agent(
    `${COMMON}\nRevise the proposal. Current edits:\n${propText}\nChecker results (violations, false statements, corrected edits, word counts):\n${JSON.stringify(checks, null, 1)}\nApply every fix, keep inserted words <= 100 (run wc -w through Bash and report), plain English, present tense, no change narration, lines 1-27 untouched, exact old_text per edit.`,
    { label: `revise:${rounds}`, phase: 'Check', schema: DRAFT })
}

return {
  proposal,
  checks: lastCheck,
  confirmed: confirmed.map(c => ({ line: c.line, section: c.section, quote: c.quote, why_stale: c.why_stale, evidence: c.evidence, must: c.must })),
  refuted: verified.filter(Boolean).filter(v => !v.keep).map(v => ({ line: v.line, quote: v.quote, reasons: v.votes.filter(x => x.refuted).map(x => x.reason) })),
  protectedHits: protectedHits.map(p => ({ line: p.line, quote: p.quote, why_stale: p.why_stale })),
  missingCandidates: missing,
  tally,
}