export const meta = {
  name: 'wade-miss-analysis',
  description: 'Verify each Wade PR4557 point, explain why our reviews missed it, derive an executable detection rule, refute and precision-probe each rule',
  phases: [
    { title: 'Analyze', detail: 'one agent per Wade point + one Wade-pattern agent' },
    { title: 'Refute', detail: 'three lenses per derived rule' },
    { title: 'Precision', detail: 'would the rule fire on things Wade kept?' },
  ],
}
const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade'
const CTX = `Read ${S}/CONTEXT.md first (all paths, the review text, the prior lenses). Worktree is READ ONLY.`

const POINTS = [
  { id: 'W1', where: 't/t_llama_unit.cpp:3575', text: 'Comment 4188336250: the packed-bits case makes "a float NaN stores as +inf" a tested contract; AGENTS.md treats NaN as corruption; the truncation and tie rows pin today\'s rounding with no named consumer. Drop the NaN->inf and rounding rows; keep the bf16 bit-exact round trip and partner-zero checks.' },
  { id: 'W2', where: 't/t_amx_numerics.cpp:227', text: 'Comment 4188336256: the only check of the packed layout against an independent formula sits after the available() early return (line 197), so it silently skips on hosts without AMX (CI). The at() section in t_llama_unit does not cover it: at() and append_v_row share pair_base, so a wrong formula passes both.' },
  { id: 'W3', where: 'h/tron/tensor/kv_cache_fwd.hpp:43', text: 'Comment 4188336267: native_k_view is an alias of the generic row-major view and t_llama_unit asserts it is constructible from const bf16*; so any pointer or row-major 64x128 bf16 view passes the QK kernel; the PR body claim "a bare pointer is a compile error" holds for V only. Say so in the description.' },
  { id: 'W4', where: 't/t_llama_unit.cpp:419', text: 'Comment 4188336302: the kernel probes (bare pointer / other plane view rejected) are the PR\'s real contract; several STATIC_REQUIREs only document structure (test policy): no operator[], no view of a temporary, not default-constructible, sizeof/alignof; three trivial-type checks repeat static_asserts kv_cache.hpp already makes. Keep the probes, drop the rest.' },
  { id: 'W5', where: 't/t_llama_unit.cpp:3298', text: 'Comment 4188336316: this GENERATE and the new "token copies keep bits in all four parity combinations" section (line 3664) both run all four copy_token parities through book::append; the bit-exact one covers more; one parity here already protects the NaN zeroing, so one of these is duplicate coverage.' },
  { id: 'W6', where: 't/t_llama_unit.cpp:3293', text: 'Comment 4188336324: the section is still named "append_v preserves poison" but it now asserts that the poison is zeroed.' },
  { id: 'M1', where: 'h/system/memory.hpp:192', text: 'Comment 4188336279: "As this line says, nothing can catch a regression here, and it adds a global operator new[] overload in a widely included header. It\'s a correct reading of [intro.object], but since it came from 39a68994465f rather than #4698, it\'d be good to get the maintainer\'s explicit sign-off on the approach." (jhan answered: 39a6899 was the comment update Ben asked for in thread 4159939672.) Analyze the REVIEW pattern: blast radius of a change (global overload, widely included header) + provenance (which commit/PR introduced it, did the maintainer see it) + "nothing can catch a regression" as a flag that needs explicit ownership.' },
  { id: 'S2', where: 'src/tron/kernels/amx_attn.cpp (commit ec795fbce8) and t/t_heap_v2.cpp', text: 'Summary item "Unrelated changes": the AMX tile-number constants (commit ec795fbce8) and the t_heap_v2 alignment check are not part of typed tensors; split them out. Verify both hunks in the diff and why each entered the PR (git log of the branch).' },
  { id: 'L3', where: 'git log e5fa372c19..96a6220ab6', text: 'Summary item "Commits: 20, three of them rewording one Note. Please squash." Verify the count and the three Note commits; analyze as a review-hygiene rule (commit history as part of what a reviewer reads).' },
  { id: 'L4a', where: 'PR description, Words row "AMX-on build, AMX-off build"', text: 'Summary item: the description says the required CI builds AMX-off; .github/workflows/cmake-single-platform.yml:355 builds with -DTRON_AMX_DISPATCH=ON. Verify against the yml at e5fa372c19 and git log -S for when the flag entered CI (PR #4505).' },
  { id: 'L4b', where: 'PR description, Verification/Status sections', text: 'Summary item: the unit-test and token-identity results are from c12df586b6 / faf8ee42ca, before the merge of main; re-run or mark pre-merge. Verify which commit ids the description cites per result row and what the head was.' },
  { id: 'L4c', where: 'PR description, Status section', text: 'Summary item: assertion-count arithmetic, UTC build timestamps and log paths can go. Verify the passages in the body as reviewed (line ~158-162).' },
  { id: 'S1', where: 'constants across the diff', text: 'Summary item "Constant names with the value built in" (V_ODD_TOKEN_LANE_MASK_0XFFFF0000, BF16_BITS_16, ACCUMULATOR_TILE_0..3, APPENDED_TOKENS_7, PATTERN_BASE_0X3C00). jhan has DECIDED this is his convention (C++ guide) and answered Wade. Do NOT propose dropping the convention. Instead analyze: which of the named examples are literal-restating names where the guide itself allows a plain literal (e.g. its alignas exception, zero), and whether a skill should pre-empt this reviewer reaction (e.g. by naming the ROLE in the name, like K_ODD_BLOCK_TILE_5, as jhan himself proposed in his reply). Output a rule that is compatible with the guide.' },
]

const ANALYSIS = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    verdict: { type: 'string', enum: ['holds', 'partly', 'refuted'] },
    evidence: { type: 'array', items: { type: 'object', properties: { ref: { type: 'string' }, quote: { type: 'string' }, note: { type: 'string' } }, required: ['ref', 'quote'] } },
    miss_category: { type: 'string', description: 'short slug, e.g. test-pins-incidental-behavior, test-gated-by-hardware, claim-exceeds-code, scope-creep, stale-description, history-hygiene, blast-radius-ownership, duplicate-coverage, name-vs-assertion' },
    why_missed: { type: 'object', properties: {
      prior_lens_closest: { type: 'string', description: 'which prior lens/skill came closest (name + file) and what it actually asked' },
      root_cause: { type: 'string', description: 'the mechanism: e.g. the lens asked whether the test is CORRECT, not whether it SHOULD EXIST; the lens read the diff not the PR body; nobody compared the body claim to the enforcing code; nobody looked at commit history; the finder was told what the test proves and accepted it' },
      author_blind_spot: { type: 'string', description: 'why the author-side agents in particular could not see it (same agent wrote test and judged it, etc.)' },
    }, required: ['prior_lens_closest', 'root_cause'] },
    rule: { type: 'object', properties: {
      name: { type: 'string' },
      trigger: { type: 'string', description: 'what in a diff/PR makes this rule apply' },
      procedure: { type: 'array', items: { type: 'string' }, description: 'numbered executable steps an agent follows (commands, what to read, what to compare)' },
      discriminating_question: { type: 'string', description: 'the one question whose answer separates a defect from a non-defect' },
      false_positive_guard: { type: 'string', description: 'when NOT to flag' },
      finding_template: { type: 'string', description: 'how to word the finding (one or two sentences, Wade register: location, what the code actually does, what to do)' },
    }, required: ['name', 'trigger', 'procedure', 'discriminating_question', 'false_positive_guard', 'finding_template'] },
    generalizes: { type: 'string', description: 'other PRs/places in tron where this rule would have fired (from the memory notes or the Wade corpus), or "unknown"' },
  },
  required: ['id', 'verdict', 'evidence', 'miss_category', 'why_missed', 'rule', 'generalizes'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reason: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
    fix: { type: 'string', description: 'if the rule is wrong or too broad/narrow, the corrected wording' },
  },
  required: ['refuted', 'confidence', 'reason', 'evidence'],
}

const PROBE = {
  type: 'object',
  properties: {
    fires_on_kept: { type: 'array', items: { type: 'object', properties: { what: { type: 'string' }, ref: { type: 'string' }, why_rule_fires: { type: 'string' } }, required: ['what', 'ref', 'why_rule_fires'] }, description: 'things in the SAME PR that Wade explicitly kept or did not flag, on which the rule as written would fire' },
    reproduces_wade: { type: 'boolean', description: 'applying the procedure to 96a6220ab6 blind, does it produce the Wade finding?' },
    reproduction_notes: { type: 'string' },
    tightened_rule: { type: 'string', description: 'reworded trigger/guard that keeps the true positive and drops the false ones' },
  },
  required: ['fires_on_kept', 'reproduces_wade', 'reproduction_notes', 'tightened_rule'],
}

log(`Analyzing ${POINTS.length} Wade points`)
const results = await pipeline(
  POINTS,
  p => agent(`${CTX}

You analyze ONE point of Wade's review of PR 4557: ${p.id} at ${p.where}.
Wade's text: ${p.text}

Do these steps and return the schema:
1. VERIFY the point against the code at 96a6220ab6 (git show 96a6220ab6:<path>), the PR body as reviewed, the CI yml, or git log as applicable. Quote the exact lines. Verdict holds/partly/refuted.
2. WHY MISSED: read ${S}/prior-0922-lenses.txt and ${S}/prior-0922-results.txt (our 2026-09-22 review), the four skills under /home/jhan/.claude/skills (tron-code-review, ben-review, positron-code-review, cpp-coding-guide), and the PR 4596 lens list in CONTEXT.md. Name the closest lens and quote what it actually asked. State the mechanism of the miss (not "nobody looked": what question was asked instead of the one that finds this).
3. RULE: write an executable detection rule in the Wade register. The procedure must be steps an agent can run (which files to open, which command, what to compare with what). Give the discriminating question, the false-positive guard, and a finding template.
4. GENERALIZES: check the memory notes named in CONTEXT.md and ${S}/wade-inline-corpus.jsonl (if non-empty: Wade's inline comments across the repo; grep for related words) for other places the same rule fires.`,
    { label: `analyze:${p.id}`, phase: 'Analyze', schema: ANALYSIS }),
  (a, p) => a && parallel([
    ['fact', 'Try to REFUTE the verdict and evidence: open the cited files at 96a6220ab6 and check every quote and line number. Is the point as stated by the analysis actually true of the code? Default refuted=true if a cited quote is not at the cited place.'],
    ['cause', 'Try to REFUTE the why_missed claim: open the prior lens prompt file and the results file. Did a prior lens actually ask the discriminating question and still miss (then the root cause is wrong), or was the question absent? Is the "closest lens" really the closest? Default refuted=true if the stated mechanism does not match the prompt text.'],
    ['rule', 'Try to REFUTE the rule: is the procedure executable by an agent without human judgment it does not have? Does the discriminating question actually separate this defect from legitimate code? Is the false-positive guard enough? Would the finding template read like Wade (specific location, what the code actually does, one concrete ask)? Propose the fixed wording in "fix".'],
  ].map(([lens, task]) => () => agent(`${CTX}

Point ${p.id} (${p.where}). Wade's text: ${p.text}

An analysis agent produced this JSON:
${JSON.stringify(a, null, 1)}

Your lens: ${lens}. ${task}`, { label: `refute:${p.id}:${lens}`, phase: 'Refute', schema: VERDICT })))
    .then(vs => ({ analysis: a, votes: vs.filter(Boolean), lenses: ['fact', 'cause', 'rule'] })),
  (r, p) => r && agent(`${CTX}

Point ${p.id} (${p.where}). Wade's text: ${p.text}

Derived rule (after refuters; apply their "fix" wording if any):
${JSON.stringify(r.analysis.rule, null, 1)}
Refuter votes: ${JSON.stringify(r.votes.map((v, i) => ({ lens: r.lenses[i], refuted: v.refuted, reason: v.reason, fix: v.fix })), null, 1)}

PRECISION PROBE. Apply the rule's procedure, as literally as an agent would, to the WHOLE PR diff at 96a6220ab6 (${S}/pr4557-at-96a6220ab6.diff) and the reviewed PR body, not only to Wade's line.
(1) List every place it fires. For each, say whether Wade flagged it. Things Wade explicitly KEPT or praised (e.g. the kernel probes, the bf16 bit-exact round trip, the partner-zero checks, the at() section, the bit-exact four-parity section) count as false positives if the rule fires on them.
(2) Does the procedure, run blind, reproduce Wade's finding at ${p.where}? Say what step produces it.
(3) Reword trigger/guard so the true positive survives and the false positives drop. Return the schema.`,
    { label: `probe:${p.id}`, phase: 'Precision', schema: PROBE })
    .then(probe => ({ ...r, probe }))
)

phase('Analyze')
const pattern = await agent(`${CTX}

You extract the reviewer's general PATTERN, not one point. Inputs: Wade's 4557 review (CONTEXT.md + ${S}/wade-inline-4557.md), his earlier comments in the memory notes listed in CONTEXT.md (read those five files), and ${S}/wade-inline-corpus.jsonl (his inline comments across positron-ai/tron, one JSON per line; may be partial). Produce:
- a ranked list of recurring themes with counts (count from the corpus file if non-empty; otherwise from the notes), each with one verbatim quote and the PR number;
- what he does NOT comment on (negative space) with evidence;
- his decision rule (what he treats as "please drop", "please say so in the description", "nit", "needs sign-off");
- the register of his comments (sentence shape, how he cites, how he asks).
Return JSON: {themes:[{theme, count, quotes:[{pr, quote}]}], negative_space:[string], decision_rules:[string], register:[string], corpus_size:number}`,
  { label: 'wade-pattern', phase: 'Analyze', schema: { type: 'object', properties: { themes: { type: 'array', items: { type: 'object', properties: { theme: { type: 'string' }, count: { type: 'number' }, quotes: { type: 'array', items: { type: 'object', properties: { pr: { type: 'string' }, quote: { type: 'string' } }, required: ['pr', 'quote'] } } }, required: ['theme', 'count', 'quotes'] } }, negative_space: { type: 'array', items: { type: 'string' } }, decision_rules: { type: 'array', items: { type: 'string' } }, register: { type: 'array', items: { type: 'string' } }, corpus_size: { type: 'number' } }, required: ['themes', 'negative_space', 'decision_rules', 'register', 'corpus_size'] } })

const done = results.filter(Boolean)
log(`${done.length}/${POINTS.length} points analyzed; dropped: ${POINTS.filter((p, i) => !results[i]).map(p => p.id).join(',') || 'none'}`)
return { points: done, pattern }