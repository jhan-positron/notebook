export const meta = {
  name: 'wade-corpus-classify',
  description: 'Classify every Wade review comment against the existing 13-check skill, then build a merged taxonomy of what he reviews for',
  phases: [
    { title: 'Classify', detail: 'one agent per PR batch: every Wade comment -> concern, existing check fit, candidate label, detection sketch, evidence needed, form' },
    { title: 'Taxonomy', detail: 'three independent taxonomists over all classifications, then one judge merges with counts' },
  ],
}
const ROOT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/wade-20261006'
const batches = args.batches

const CLASSIFY_SCHEMA = {
  type: 'object',
  properties: {
    prs: { type: 'array', items: { type: 'object', properties: {
      pr: { type: 'string' }, verdict_pattern: { type: 'string' }, pr_level_notes: { type: 'string' } }, required: ['pr', 'verdict_pattern', 'pr_level_notes'] } },
    comments: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'number' }, pr: { type: 'string' }, kind: { type: 'string', enum: ['inline', 'review', 'issue'] },
      path: { type: ['string', 'null'] }, is_reply: { type: 'boolean' },
      concern: { type: 'string' },
      existing_check: { type: ['number', 'null'] }, existing_check_fit: { type: 'string', enum: ['full', 'partial', 'none'] },
      candidate_label: { type: 'string' },
      detection: { type: 'object', properties: { trigger: { type: 'string' }, procedure: { type: 'string' }, question: { type: 'string' } }, required: ['trigger', 'procedure', 'question'] },
      evidence_read: { type: 'array', items: { type: 'string', enum: ['hunk', 'full_file', 'other_file', 'callers', 'pr_body', 'commits', 'ci_config', 'runtime_behavior', 'perf_knowledge', 'hardware_knowledge', 'docs', 'test_run', 'prior_pr'] } },
      form: { type: 'string', enum: ['question', 'statement', 'ask', 'suggestion_block', 'praise', 'self_note', 'meta', 'answer'] },
      severity: { type: 'string', enum: ['nit', 'minor', 'normal', 'blocking', 'none'] },
      author_outcome: { type: 'string', enum: ['accepted', 'changed', 'pushed_back', 'discussed', 'unknown'] },
      quote: { type: 'string' }, reviewable_by_agent: { type: 'string', enum: ['yes', 'needs_runtime', 'needs_domain', 'no'] }, note: { type: 'string' } },
      required: ['id', 'pr', 'kind', 'path', 'is_reply', 'concern', 'existing_check', 'existing_check_fit', 'candidate_label', 'detection', 'evidence_read', 'form', 'severity', 'author_outcome', 'quote', 'reviewable_by_agent', 'note'] } },
  },
  required: ['prs', 'comments'],
}

phase('Classify')
const classified = await parallel(batches.map((b, i) => () => agent(`Read ${ROOT}/CONTEXT.md fully, then /home/jhan/.claude/skills/Wade-code-review/SKILL.md fully (the 13 checks).
Then read these PR digests fully: ${b.map(k => `${ROOT}/corpus/pr/${k}.md`).join(' ')}.

Task: classify EVERY Wade comment in these digests (every "### inline", every review with text, every "### issue-comment"). Do not skip replies, praise, or self-notes; classify them with form=answer/praise/self_note and candidate_label "none".
For each comment:
- concern: one sentence, what Wade is checking or asking for, in plain English (define code names at first use).
- existing_check: the number 1-13 of the skill check that would have produced this comment, or null. existing_check_fit: full (the check's trigger and procedure as written would fire here), partial (same theme, but the trigger or procedure as written would not fire), none.
- candidate_label: a short kebab-case slug for the review pattern this comment is an instance of (reuse the same slug for the same pattern across comments; prefer mechanism-level labels such as "buffer-freed-while-dma-in-flight", "lock-held-across-blocking-call", "magic-number-needs-name", "ask-for-unit-test", "perf-extra-copy-on-hot-path", "comment-stale-vs-code", "ask-to-run-tests-before-merge"). Not "misc".
- detection: how an agent with the diff and the repository could reproduce this comment: trigger (what in the diff fires it), procedure (what to read or run; name files, greps, callers), question (the one question whose answer decides the finding). Be concrete to the mechanism, not to this PR.
- evidence_read: what Wade had to have read or known to write it (enum).
- form, severity (nit if he says nit/minor/trivial; blocking only if he says it blocks approval; none for praise/answers), author_outcome from the replies in the digest.
- quote: verbatim excerpt of Wade's words, at most 240 characters, copied exactly from the digest (no paraphrase).
- reviewable_by_agent: yes if an agent with code access can produce it; needs_runtime if it needs a run or measurement; needs_domain if it needs knowledge not in the repo (hardware, team plans); no if it is social.
- note: anything else, e.g. the exact code fact Wade relied on (read the hunk; if useful, read the file at the comment's commit with git -C /home/jhan/workspace/ai-runs/tron-issue4525 show <commit>:<path>, read only).
Per PR also give verdict_pattern (what he did: approve silently, comment then approve, questions only, asked to run tests, asked for follow-up PR...) and pr_level_notes (what the PR is, which areas, whether he reviewed code or process).
Return raw data only.`, { label: `classify:${b.join('+')}`, phase: 'Classify', schema: CLASSIFY_SCHEMA })))
const all = classified.filter(Boolean)
const comments = all.flatMap(r => r.comments)
const prs = all.flatMap(r => r.prs)
log(`classified ${comments.length} comments over ${prs.length} PRs (${batches.length - all.length} batches failed)`)

phase('Taxonomy')
const TAX_SCHEMA = {
  type: 'object',
  properties: {
    checks: { type: 'array', items: { type: 'object', properties: {
      label: { type: 'string' }, name: { type: 'string' }, description: { type: 'string' },
      member_ids: { type: 'array', items: { type: 'number' } }, count: { type: 'number' },
      existing_check: { type: ['number', 'null'] }, overlap: { type: 'string', enum: ['subsumed', 'extends', 'new'] },
      evidence_needed: { type: 'array', items: { type: 'string' } },
      representative_ids: { type: 'array', items: { type: 'number' } },
      agent_feasibility: { type: 'string' }, prs_spanned: { type: 'number' } },
      required: ['label', 'name', 'description', 'member_ids', 'count', 'existing_check', 'overlap', 'evidence_needed', 'representative_ids', 'agent_feasibility', 'prs_spanned'] } },
    style_observations: { type: 'array', items: { type: 'string' } },
    negative_space: { type: 'array', items: { type: 'string' } },
    uncategorized_ids: { type: 'array', items: { type: 'number' } },
  },
  required: ['checks', 'style_observations', 'negative_space', 'uncategorized_ids'],
}
const compact = comments.map(c => ({ id: c.id, pr: c.pr, path: c.path, reply: c.is_reply, concern: c.concern, ex: c.existing_check, fit: c.existing_check_fit, label: c.candidate_label, trig: c.detection.trigger, q: c.detection.question, ev: c.evidence_read, form: c.form, sev: c.severity, out: c.author_outcome, agent: c.reviewable_by_agent, quote: c.quote }))
const LENSES = [
  { key: 'mechanism', hint: 'Group by the code mechanism at fault (what breaks: lifetime, ordering, aliasing, perf, naming, docs...). Each check must be executable by an agent with the diff and the repo.' },
  { key: 'evidence', hint: 'Group by what a reviewer must READ to produce the comment (the hunk alone; the whole file; callers; another file; PR body; commits; runtime). Then split each group by concern. Each check must name its evidence source.' },
  { key: 'skill-delta', hint: 'Start from the 13 existing checks. First assign every comment that an existing check covers (full or partial) and say per check whether its trigger must widen. Then group the remainder into NEW checks, largest first.' },
]
const taxonomies = await parallel(LENSES.map(l => () => agent(`Read ${ROOT}/CONTEXT.md fully and /home/jhan/.claude/skills/Wade-code-review/SKILL.md fully.
Below is the classification of every Wade comment (${compact.length} rows, JSON). Build a taxonomy of review checks from it. Lens: ${l.hint}

Rules: every check lists ALL member comment ids (a comment belongs to exactly one check; put answers, praise and self-notes into one check labelled "non-review" so nothing is lost); count = member_ids length; prs_spanned = distinct PRs among the members; existing_check = the skill check it maps to or null; overlap = subsumed (the existing check as written covers it), extends (existing check needs a wider trigger or an extra step), new. representative_ids = up to 4 ids whose quotes best show the pattern. Order checks by count descending. Also return style_observations (how he words things, verdict habits, with counts you can derive from the rows) and negative_space (what he does not comment on; use the 48 silent PRs in ${ROOT}/corpus/silent.json and corpus.json file lists if useful). uncategorized_ids must be empty; if you cannot place a comment, put it in the closest check and say so in its description.
Return raw data only.

ROWS:
${JSON.stringify(compact)}`, { label: `taxonomy:${l.key}`, phase: 'Taxonomy', schema: TAX_SCHEMA })))
const tax = taxonomies.filter(Boolean)
log(`${tax.length} taxonomies: ${tax.map(t => t.checks.length + ' checks').join(', ')}`)

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    checks: { type: 'array', items: { type: 'object', properties: {
      label: { type: 'string' }, name: { type: 'string' }, description: { type: 'string' },
      member_ids: { type: 'array', items: { type: 'number' } }, count: { type: 'number' }, prs_spanned: { type: 'number' },
      existing_check: { type: ['number', 'null'] }, disposition: { type: 'string', enum: ['add_new', 'widen_existing', 'retune_existing', 'keep_existing', 'style_only', 'drop'] },
      disposition_reason: { type: 'string' },
      evidence_needed: { type: 'array', items: { type: 'string' } }, representative_ids: { type: 'array', items: { type: 'number' } },
      agent_feasibility: { type: 'string' }, taxonomies_agreeing: { type: 'number' } },
      required: ['label', 'name', 'description', 'member_ids', 'count', 'prs_spanned', 'existing_check', 'disposition', 'disposition_reason', 'evidence_needed', 'representative_ids', 'agent_feasibility', 'taxonomies_agreeing'] } },
    style_observations: { type: 'array', items: { type: 'string' } },
    negative_space: { type: 'array', items: { type: 'string' } },
    disagreements: { type: 'array', items: { type: 'string' } },
  },
  required: ['checks', 'style_observations', 'negative_space', 'disagreements'],
}
const merged = await agent(`Read ${ROOT}/CONTEXT.md fully and /home/jhan/.claude/skills/Wade-code-review/SKILL.md fully.
Three independent taxonomies of Wade's ${compact.length} review comments follow (JSON), built with different lenses (mechanism / evidence / skill-delta), plus the underlying rows. Merge them into ONE taxonomy:
- Every comment id appears in exactly one merged check. Resolve conflicts by the mechanism the comment names (read the quote and concern), not by vote.
- Merge checks that two taxonomies split the same way; split a check only when its members need different procedures.
- disposition per merged check: add_new (no existing check covers it; count >= 3 or spans >= 2 PRs), widen_existing (existing check N covers the theme, the trigger must widen), retune_existing (procedure wrong or incomplete), keep_existing, style_only (wording or verdict habit, goes into the "How Wade words a finding" section), drop (non-review: answers, praise, self-notes; or singletons that are not agent-reviewable). Give the reason.
- taxonomies_agreeing: how many of the 3 taxonomies had a check with the same mechanism.
- Order by count descending. Keep every representative id verifiable: it must be a member id.
- style_observations and negative_space: union of the three, deduplicated, each with its count or source.
- disagreements: where the taxonomies conflicted and how you decided.
Return raw data only.

TAXONOMIES:
${JSON.stringify(tax)}

ROWS:
${JSON.stringify(compact)}`, { label: 'merge-taxonomy', phase: 'Taxonomy', schema: MERGE_SCHEMA, effort: 'high' })

return { classified: all, taxonomies: tax, merged }