export const meta = {
  name: 'wade-skill-draft-verify',
  description: 'Draft each new or widened Wade check in skill form, refute with three lenses, tighten, probe for false positives, and draft the style section',
  phases: [
    { title: 'Draft', detail: 'one drafter per check: trigger, procedure, question, do-not-fire, finding shape, commands, verbatim quotes' },
    { title: 'Refute', detail: 'three lenses per draft: precision on silent PRs, verbatim and code facts, executability on the originating PR' },
    { title: 'Tighten', detail: 'fold the refuters into a final text per check' },
    { title: 'Style', detail: 'wording, verdict and negative-space section from counts and verbatim quotes' },
    { title: 'Critic', detail: 'codex pick-up coverage and cross-check overlap' },
  ],
}
const ROOT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/wade-20261006'
const SKILL = '/home/jhan/.claude/skills/Wade-code-review'
const items = args.items

const DRAFT_SCHEMA = {
  type: 'object',
  properties: {
    label: { type: 'string' },
    disposition: { type: 'string' },
    skill_entry: { type: 'object', properties: {
      name: { type: 'string' }, trigger: { type: 'string' }, procedure: { type: 'string' }, question: { type: 'string' },
      do_not_fire: { type: 'string' }, finding_shape: { type: 'string' }, severity_wade_uses: { type: 'string' }, evidence_scope: { type: 'string' } },
      required: ['name', 'trigger', 'procedure', 'question', 'do_not_fire', 'finding_shape', 'severity_wade_uses', 'evidence_scope'] },
    procedure_commands: { type: 'string' },
    widen_delta: { type: 'string' },
    quotes: { type: 'array', items: { type: 'object', properties: { id: { type: 'number' }, pr: { type: 'string' }, quote: { type: 'string' }, what_it_shows: { type: 'string' } }, required: ['id', 'pr', 'quote', 'what_it_shows'] } },
    code_facts: { type: 'array', items: { type: 'string' } },
    codex_folded: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['label', 'disposition', 'skill_entry', 'procedure_commands', 'widen_delta', 'quotes', 'code_facts', 'codex_folded', 'open_questions'],
}
const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' }, verdict: { type: 'string', enum: ['ok', 'fix', 'refuted'] },
    problems: { type: 'array', items: { type: 'string' } },
    fixes: { type: 'array', items: { type: 'string' } },
    probe_log: { type: 'string' },
    false_positives: { type: 'array', items: { type: 'string' } },
    reproduced_wade: { type: 'string' },
  },
  required: ['lens', 'verdict', 'problems', 'fixes', 'probe_log', 'false_positives', 'reproduced_wade'],
}
const FINAL_SCHEMA = {
  type: 'object',
  properties: {
    label: { type: 'string' }, disposition: { type: 'string' }, keep: { type: 'boolean' }, drop_reason: { type: 'string' },
    skill_entry: DRAFT_SCHEMA.properties.skill_entry,
    procedure_commands: { type: 'string' }, widen_delta: { type: 'string' },
    quotes: DRAFT_SCHEMA.properties.quotes,
    precedent_note: { type: 'string' },
    changes_made: { type: 'array', items: { type: 'string' } },
    residual_risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['label', 'disposition', 'keep', 'drop_reason', 'skill_entry', 'procedure_commands', 'widen_delta', 'quotes', 'precedent_note', 'changes_made', 'residual_risks'],
}

const common = `Read ${ROOT}/CONTEXT.md fully, then ${SKILL}/SKILL.md fully and skim ${SKILL}/references/procedures.md for the house form (trigger / procedure / question / do-not-fire / finding shape, and numbered commands with BASE, HEAD, WT, N placeholders). Plain English: define a code name or acronym at first use, one claim per sentence, no idioms. The tron worktree /home/jhan/workspace/ai-runs/tron-issue4525 is READ ONLY (git show / log / grep only; never checkout, reset, fetch, pull, prune, worktree). gh pr diff N --repo positron-ai/tron and gh api are allowed for reading.`

const LENSES = [
  { key: 'precision', prompt: (d, it) => `Lens: PRECISION. Would this check fire where Wade stayed silent? Run the draft's trigger and procedure, as literally as written, on at least four of the diffs of PRs Wade approved with no comment at all: the files in ${ROOT}/corpus/silent-diffs/ (pick the four largest you can read in full, plus any that touch the check's file areas). Report every hit as a false positive with file:line and the reason the check would have fired. Then check overlap: does any of the 13 existing checks in ${SKILL}/SKILL.md, or another merged check in ${ROOT}/merged-taxonomy.json, already own this trigger? If the draft would fire on more than one silent PR, verdict = fix with a narrowed trigger or do-not-fire clause; if it cannot be narrowed without losing Wade's cases, verdict = refuted.` },
  { key: 'facts', prompt: (d, it) => `Lens: FACTS. For every quote in the draft, confirm the id exists in ${ROOT}/corpus/corpus.json and the quote is a verbatim substring of that comment's body (normalize CRLF). For every code fact in the draft, verify it with git -C /home/jhan/workspace/ai-runs/tron-issue4525 show <commit>:<path> at the commit the comment names (corpus.json inline.commit) or gh pr diff. Also check that the draft does not contradict Wade's later replies in the same thread (digests show replies) and that the severity matches his words. Verdict fix with corrected text for any error; refuted only if the central mechanism is not what Wade said.` },
  { key: 'executability', prompt: (d, it) => `Lens: EXECUTABILITY. Take ONE originating PR of this check (member ids in the item file; prefer the representative with the most code context) and run the draft's procedure_commands on it, substituting BASE, HEAD, WT, N (HEAD = the commit named next to Wade's comment, or the PR head from corpus.json; BASE = git merge-base against the PR's base_ref branch, which may be hwattention_sync, not main; if a ref is missing in the worktree, use gh pr diff N and gh api). Record each command and its output size. Did the procedure reach Wade's finding without the agent already knowing it? Which step is ambiguous, unbounded (hundreds of hits) or impossible without network or hardware? Verdict fix with the rewritten steps; refuted if no executable path exists.` },
]

phase('Draft')
const results = await pipeline(items,
  (it) => agent(`${common}

Item file: ${ROOT}/items/${it.label}.json (read fully: the merged check, its member Wade comments with concern, quote, detection sketch, and matching codex bullets). Read the full digests of at least three member PRs in ${ROOT}/corpus/pr/ for the hunks and replies, and read the code at the comment's commit for at least two members (git show <commit>:<path>) so that the procedure names real file patterns and greps.

Disposition ${it.disposition}${it.existing_check ? `, existing check ${it.existing_check}` : ''}. ${it.disposition === 'add_new' ? 'Write a NEW check in the house form.' : `Write the DELTA to existing check ${it.existing_check}: widen_delta = the exact sentences to add or replace (quote the existing sentence being replaced), and still fill skill_entry with the widened text of that check.`}
Requirements:
- trigger: what in the diff fires it, mechanical enough that an agent can grep for it. procedure: numbered steps naming what to read or run (git grep patterns, which files, which neighbours). question: the one question whose answer decides the finding, in Wade's terms. do_not_fire: the cases Wade accepted or never commented on (read the author replies and the negative-space section of ${ROOT}/merged-taxonomy.json). finding_shape: one sentence template in Wade's register for this check (his hand-written comments are short questions, lowercase, often one reason; see quotes). severity_wade_uses: nit / minor / normal with his own words. evidence_scope: hunk only / full file / callers / other files / PR body / commits / CI / runtime.
- procedure_commands: the numbered shell commands for references/procedures.md, with an "On PR <n>:" line that records the run on one member PR with real file:line values.
- quotes: 2 to 5 verbatim excerpts (copy exactly from the digest, max 240 chars, CRLF removed), with id and pr and what each shows.
- codex_folded: the codex bullets (by C-id from the item file) whose wording or step you adopted, and which you rejected and why.
- code_facts: each fact you verified in the code, with commit:path:line.
Return raw data only.`, { label: `draft:${it.label}`, phase: 'Draft', schema: DRAFT_SCHEMA }),
  (draft, it) => parallel(LENSES.map(l => () => agent(`${common}

Item file: ${ROOT}/items/${it.label}.json. The DRAFT under test (JSON):
${JSON.stringify(draft)}

${l.prompt(draft, it)}
Return raw data only: lens, verdict, problems, fixes (each a replacement sentence or step), probe_log (commands run and hit counts), false_positives, reproduced_wade (yes/no/partly with the step that reached it).`, { label: `refute:${l.key}:${it.label}`, phase: 'Refute', schema: VERDICT_SCHEMA }))).then(v => ({ draft, verdicts: v.filter(Boolean) })),
  (r, it) => agent(`${common}

Item file: ${ROOT}/items/${it.label}.json. Draft (JSON):
${JSON.stringify(r.draft)}
Refuter verdicts (JSON):
${JSON.stringify(r.verdicts)}

Fold every fix in. Where refuters disagree, re-read the comment or the code and decide; say which. keep=false only if the precision lens showed the check fires on more than one silent PR and no narrowing keeps Wade's cases, or the facts lens refuted the mechanism. Write precedent_note: "n = <count> comments over <prs> PRs, <date range>" plus whether any member is pasted assistant text. Keep the skill_entry compact (trigger, procedure, question, do_not_fire, finding_shape each at most 120 words). Keep the quotes verbatim. Return raw data only.`, { label: `tighten:${it.label}`, phase: 'Tighten', schema: FINAL_SCHEMA, effort: 'high' })
)

phase('Style')
const STYLE_SCHEMA = { type: 'object', properties: { how_wade_words_a_finding: { type: 'string' }, verdict_calibration: { type: 'string' }, assisted_text: { type: 'string' }, negative_space: { type: 'string' }, when_replying_to_wade: { type: 'string' }, quotes_used: { type: 'array', items: { type: 'object', properties: { id: { type: 'number' }, quote: { type: 'string' } }, required: ['id', 'quote'] } } }, required: ['how_wade_words_a_finding', 'verdict_calibration', 'assisted_text', 'negative_space', 'when_replying_to_wade', 'quotes_used'] }
const style = await agent(`${common}

Inputs: ${ROOT}/style-stats.json (counts computed with code), the style_observations and negative_space arrays in ${ROOT}/merged-taxonomy.json, ${ROOT}/codex-factcheck.md (claims 1, 6, 7), and the corpus digests for verbatim quotes.
Write five Markdown sections for the skill, replacing the current "How Wade words a finding" (SKILL.md) which was derived from PR 4557 alone:
1. how_wade_words_a_finding: two registers by date (hand-written 2025-09 to 2026-08: short lowercase questions, 'right?', '... intentional?', suggestion blocks for one-line fixes, 'same here'; 2026-09 onward and in assisted reviews: fact, 'So' consequence, ask with two repairs, file:line). Every count from style-stats.json with its denominator. 6 to 10 verbatim quotes with ids.
2. verdict_calibration: review states (100 APPROVED / 234 COMMENTED / 0 CHANGES_REQUESTED of 334), final verdict by comment count, how a must-change is signalled ('before merging', 'needs', 'Please <verb>', withheld approval), conditional approvals, 48 silent PRs and what they look like (size numbers), median time to first review.
3. assisted_text: the nine disclosed pastes with ids and dates, how to treat them, and that PR 4557's style matches the disclosed-assisted PR 4128 with no disclosure (Insufficient data).
4. negative_space: what he does not comment on, each item with its count or source (file types, formatting, kernel arithmetic, benchmark numbers, commit messages, CI YAML, missing tests on small PRs), and the two exceptions the fact-check found (3778051701 Markdown line length; 4607543703 before/after trace request).
5. when_replying_to_wade: how he reacts to pushback (concedes in writing: 'yeah, doh!', 'Nevermind ;p'), defers to owners, accepts 'next iteration', about one in six asks declined and let stand; what an agent should do when drafting a reply.
Plain English rules apply. Return raw data only.`, { label: 'style-section', phase: 'Style', schema: STYLE_SCHEMA, effort: 'high' })

phase('Critic')
const finals = results.filter(Boolean)
const CRITIC_SCHEMA = { type: 'object', properties: { codex_gaps: { type: 'array', items: { type: 'string' } }, overlaps_between_new_checks: { type: 'array', items: { type: 'string' } }, overlaps_with_existing_13: { type: 'array', items: { type: 'string' } }, ordering_suggestion: { type: 'array', items: { type: 'string' } }, contradictions: { type: 'array', items: { type: 'string' } } }, required: ['codex_gaps', 'overlaps_between_new_checks', 'overlaps_with_existing_13', 'ordering_suggestion', 'contradictions'] }
const critic = await agent(`${common}

Final drafted checks (JSON, ${finals.length} items):
${JSON.stringify(finals.map(f => ({ label: f.label, keep: f.keep, disposition: f.disposition, existing_check: f.skill_entry && f.skill_entry.name, trigger: f.skill_entry.trigger, do_not_fire: f.skill_entry.do_not_fire, question: f.skill_entry.question })))}

Tasks:
1. codex_gaps: read ${ROOT}/codex-map.json. For every bullet with pick_up = yes, name the final check (label) or style section that now carries it, or write "gap: <bullet id> <first clause>" with the Wade evidence ids that justify adding it. Also list pick_up = yes bullets whose only evidence is assistant paste (derived_from) so the skill can mark them as attributed.
2. overlaps_between_new_checks: pairs of final checks whose triggers fire on the same hunk; say which should own it and the sentence to add to the other's do_not_fire.
3. overlaps_with_existing_13: the same against the 13 checks in ${SKILL}/SKILL.md.
4. ordering_suggestion: group the final checks into sections for SKILL.md (code: lifetime and concurrency / code: hygiene / tests / claims and body / history and scope), ordered by Wade's comment count (item files have count).
5. contradictions: any final check sentence that contradicts ${ROOT}/codex-factcheck.md or a Wade reply.
Return raw data only.`, { label: 'critic', phase: 'Critic', schema: CRITIC_SCHEMA, effort: 'high' })

return { finals, style, critic }