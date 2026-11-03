export const meta = {
  name: 'respond-to-isaac-pr5022',
  description: 'Verify each of Isaac\'s PR 5022 comments against the code at head, draft jhan\'s replies, adversarially check them',
  phases: [
    { title: 'Draft', detail: 'verify claim, classify, draft reply (one agent per item)' },
    { title: 'Refute', detail: 'skeptic re-checks every factual claim in the draft' },
    { title: 'Revise', detail: 'rewrite drafts the skeptic refuted' },
    { title: 'Critique', detail: 'classification and completeness check over all items' },
  ],
}

const S = args.scratch
const CTX = `
CONTEXT (read carefully; it is the only context you have)
- Pull request: positron-ai/tron #5022 "AMX attention: serve kv_mul 16 (Muse Glimmer) with a group_heads template parameter". Branch jhan-amx-kvmul16. Head 4c4b7b886485de971b968de579af170d50d73e04 (short 4c4b7b8864). Merge base 61988242460342b26f153ae5e05ec0b294174904 (short 6198824246). Author: jhan (the person you work for; GitHub login jhan-positron). Reviewer: Isaac (GitHub login ishapira-positron). Isaac submitted CHANGES_REQUESTED on 2026-10-23 with one review body and 26 inline comments.
- Branch commits (oldest first): 393dbc1759 (serve kv_mul 16), 5061623a34 (update comments), a6b93f1f71 (Simplify AMX attention comments), 7e7f52d761 (Apply accepted AMX review changes), 4c4b7b8864 (name the page views, derive the test group size, report skips).
- Read-only git worktree checked out at the PR head: /home/jhan/workspace/ai-runs/pr5022-isaac/tron-head  (use this for all file:line citations; line numbers in Isaac's comments refer to this head). DO NOT modify it. A full clone with build artifacts and compile_commands.json is at /home/jhan/workspace/tron (also do not modify; you may read its compile_commands.json to get compile flags).
- Scratch files (read freely): ${S}/pr.diff (full diff merge base..head), ${S}/pr_body.md (PR description), ${S}/isaac_review_body.md (Isaac's top-level review), ${S}/inline_sorted.json (all 26 inline comments with hunks), ${S}/items.json (all items), ${S}/issue5021.md (follow-up issue #5021: rename + make new shapes a minimal change), ${S}/pr5015_comments.json (112 inline annotations jhan wrote on the predecessor PR #5015 explaining the design; search it for rationale, e.g. grep for "kv_mul 8", "pack", "band", "minimal").
- Earlier campaign reports by jhan (HTML, may contain rationale and measurements): /home/jhan/workspace/intel-AMX/muse-glimmer/muse-glimmer-amx.html and /home/jhan/workspace/intel-AMX/muse-glimmer/muse-glimmer-amx-results.html, /home/jhan/workspace/intel-AMX/muse-glimmer/diagramming-code-changes-PR5015-amx_attn.cpp.html.
- You may write temporary files ONLY under ${S}/work/<your-item-key>/ (create it). You may run read-only gh commands (gh api GET, gh run view, gh pr view). You may run local syntax-only compiles (clang++ -fsyntax-only with flags copied from compile_commands.json, adjusting -I paths to the worktree) and small local probes. This host has no AMX and that is fine.
- HARD RULES: do not post anything to GitHub; do not run anything on delphi-3bda or any remote machine; do not modify the worktree or the main clone; never invent a measurement. If a reply would need a number that does not exist yet, say so and name the measurement that would produce it.
- Naming rule from the project: write "prompt 1024", never "ctx 1024".
`

const DRAFT_SCHEMA = {
  type: 'object',
  properties: {
    key: { type: 'string' },
    isaac_point: { type: 'string', description: 'Isaac\'s point in one plain sentence' },
    claim_status: { type: 'string', enum: ['confirmed', 'partly-confirmed', 'refuted', 'not-verifiable-here'] },
    evidence: { type: 'array', items: { type: 'string' }, description: 'each: what you checked and what you saw, with file:line in the worktree or command -> output' },
    classification: { type: 'string', enum: ['request-for-change', 'request-for-response', 'informational'] },
    recommended_action: { type: 'string', enum: ['accept', 'accept-modified', 'decline', 'defer-to-5021', 'provide-evidence', 'answer-only', 'none'] },
    action_detail: { type: 'string', description: 'concrete to-do for jhan: exact code/comment/doc change, or exact evidence to produce; empty if none' },
    needs_hardware: { type: 'boolean', description: 'true if the action or reply needs a run on delphi-3bda (Granite Rapids with AMX)' },
    hardware_detail: { type: 'string' },
    reply_draft: { type: 'string', description: 'the reply jhan would paste on GitHub, markdown, first person' },
    open_question_for_jhan: { type: 'string', description: 'a decision only jhan can make, or empty' },
  },
  required: ['key', 'isaac_point', 'claim_status', 'evidence', 'classification', 'recommended_action', 'action_detail', 'needs_hardware', 'hardware_detail', 'reply_draft', 'open_question_for_jhan'],
}

const REFUTE_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    problems: { type: 'array', items: { type: 'string' } },
    verified_facts: { type: 'array', items: { type: 'string' } },
    better_action: { type: 'string' },
  },
  required: ['refuted', 'problems', 'verified_facts', 'better_action'],
}

function itemText(it) {
  if (it.kind === 'inline') {
    return `ITEM ${it.key} (inline comment by Isaac)\nFile: ${it.path} line ${it.line} at head\nURL: ${it.url}\nDiff hunk (tail):\n${it.diff_hunk}\n\nIsaac's comment:\n${it.body}`
  }
  return `ITEM ${it.key} (from Isaac's top-level review body)\nTitle: ${it.title}\nText / context:\n${it.body}\n\nRead the whole review body in ${S}/isaac_review_body.md to see where this sits.`
}

const REPLY_RULES = `
HOW TO WRITE THE REPLY (reply_draft):
- Voice: jhan, the PR author, first person, replying to Isaac on GitHub. Direct and technical. Acknowledge plainly when Isaac is right ("You are right." / "Agreed."). No thanks-padding, no apologies unless for an actual error.
- Plain English rules: one claim per sentence; short sentences; define a project term at first use in that reply when a newcomer would not know it (e.g. "the kill switch (TRON_AMX_DISABLE=1)"); every number has a unit; no idioms or metaphors; citations in brackets AFTER a sentence, as file:line at the head commit.
- State the decision in the first sentence or two: what jhan will change (and roughly how), or why not, or the answer to the question, or what evidence will be produced. Nothing has been committed yet, so write "Will do: ..." / "I will ..." rather than "Done in <sha>". Where the change is a one-line comment or code edit, include the proposed text in a fenced block.
- If the item is informational (no change and no question asked), reply_draft may be a one-line acknowledgement or empty.
- If Isaac's claim is wrong or partly wrong, say exactly what the code does, with file:line, and no hedging.
- If the answer depends on a decision only jhan can make (product/plan knowledge), write the reply for the most likely decision and put the alternative in open_question_for_jhan.
- Length: usually 40-150 words; longer only when the point needs it.
- Isaac's stated classification labels "follow-up" and "accepted" (in the Architecture section) are his own labels: "follow-up" = he wants it tracked for a later PR, "accepted" = no change needed.
CLASSIFICATION of the item: request-for-change = Isaac asks for a code, comment, test, doc, CI or PR-body change (even phrased as "Could we ...?"); request-for-response = he asks a question, asks for evidence, or asks for a decision; informational = a statement that needs no change and no answer.
`

phase('Draft')
const results = await pipeline(
  args.items,
  it => agent(`${CTX}\n${itemText(it)}\n\nYOUR TASK (item ${it.key}):\n1. Verify Isaac's claim yourself against the worktree at head. Re-run his "Checked by" commands where present (against the worktree) and extend them: read the surrounding code, the callers, the tests, the CI workflow files (.github/workflows/*.yml, nix/cmake-tron-test-build.nix), README.ci.md, t/CMakeLists.txt, config/test-benchmarks.json, bin/slice, as relevant. For claims about Catch2 behaviour, check the Catch2 source if available under /home/jhan/workspace/tron (find it: find /home/jhan/workspace/tron -name catch_session.cpp 2>/dev/null | head -1) or state what you could not verify. For claims about compile output, instruction counts or nanosecond timings measured by Isaac on his Zen 4 machine, you cannot reproduce them; mark them not-verifiable-here and do not dispute them unless the code contradicts them.\n2. Look for jhan's existing rationale: grep ${S}/pr5015_comments.json and ${S}/pr_body.md and the HTML reports for the topic. If a rationale exists, the reply should use it.\n3. Decide the recommended action and classification.\n4. Write the reply draft.\n${REPLY_RULES}\nReturn the structured result.`,
    { label: `draft:${it.key}`, phase: 'Draft', schema: DRAFT_SCHEMA }),
  (draft, it) => draft && agent(`${CTX}\n${itemText(it)}\n\nA colleague drafted this verification and reply for jhan:\n${JSON.stringify(draft, null, 2)}\n\nYOUR TASK: be the skeptic. Independently re-check EVERY factual claim in the draft (claim_status, each evidence line, every file:line cited in reply_draft, every statement about what the code, tests, CI workflows, Catch2 or the PR body do) against the worktree at head and the scratch files. Also check: (a) does the reply answer what Isaac actually asked, (b) does it promise something that is not possible or not verified, (c) does it contradict the PR body or jhan's own earlier rationale in ${S}/pr5015_comments.json, (d) is the classification right (request-for-change vs request-for-response vs informational), (e) does it invent any number. Set refuted=true if any material fact in the draft is wrong, any cited file:line does not show what the draft says, or the recommended action is clearly worse than an alternative you can justify; list each problem concretely with the correct fact. Set refuted=false if the draft survives. Fill verified_facts with the checks that passed (with file:line). Fill better_action if you recommend a different action (else empty string).`,
    { label: `refute:${it.key}`, phase: 'Refute', schema: REFUTE_SCHEMA }).then(v => ({ draft, verdict: v })),
  (r, it) => {
    if (!r) return null
    if (!r.verdict || !r.verdict.refuted) return { ...r, revised: null }
    return agent(`${CTX}\n${itemText(it)}\n\nA first draft of jhan's reply was written and then a skeptic found problems. First draft:\n${JSON.stringify(r.draft, null, 2)}\n\nSkeptic's verdict:\n${JSON.stringify(r.verdict, null, 2)}\n\nYOUR TASK: produce a corrected version of the structured draft. Re-verify the disputed facts yourself in the worktree (do not simply trust either side), fix every confirmed problem, keep everything that survived. ${REPLY_RULES}\nReturn the corrected structured result.`,
      { label: `revise:${it.key}`, phase: 'Revise', schema: DRAFT_SCHEMA }).then(rev => ({ ...r, revised: rev }))
  },
)

const finals = results.filter(Boolean).map(r => ({ key: (r.revised || r.draft).key, final: r.revised || r.draft, verdict: r.verdict, was_revised: !!r.revised }))
log(`${finals.length}/${args.items.length} items drafted; ${finals.filter(f => f.was_revised).length} revised after refutation`)

phase('Critique')
const compact = finals.map(f => ({ key: f.key, isaac_point: f.final.isaac_point, classification: f.final.classification, recommended_action: f.final.recommended_action, action_detail: f.final.action_detail, needs_hardware: f.final.needs_hardware, claim_status: f.final.claim_status }))
const CRIT_SCHEMA = {
  type: 'object',
  properties: {
    uncovered_points: { type: 'array', items: { type: 'string' }, description: 'sentences or asks in Isaac\'s review body or inline comments that no item covers' },
    classification_corrections: { type: 'array', items: { type: 'object', properties: { key: { type: 'string' }, should_be: { type: 'string' }, why: { type: 'string' } }, required: ['key', 'should_be', 'why'] } },
    conflicts: { type: 'array', items: { type: 'string' }, description: 'pairs of items whose recommended actions contradict each other (e.g. one accepts instantiating 8, another declines)' },
    duplicates: { type: 'array', items: { type: 'string' }, description: 'top-level items that are the same ask as an inline item, as "top-xx = inline-yy"' },
    notes: { type: 'string' },
  },
  required: ['uncovered_points', 'classification_corrections', 'conflicts', 'duplicates', 'notes'],
}
const critique = await agent(`${CTX}\nRead ${S}/isaac_review_body.md and ${S}/inline_sorted.json in full. Here is the per-item summary a team produced:\n${JSON.stringify(compact, null, 2)}\n\nYOUR TASK: (1) list every ask or claim in Isaac's review body and inline comments that is NOT covered by any item; (2) check each item's classification (request-for-change = asks for a code/comment/test/doc/CI/PR-body change, request-for-response = asks a question, evidence or a decision, informational = neither) and list corrections; (3) list contradictions between items' recommended actions (e.g. the kv_mul 8 question appears in top-09, top-11, inline-14, inline-23: the answers must agree); (4) list which top-level items duplicate inline items. Be exhaustive.`,
  { label: 'critique:all', phase: 'Critique', schema: CRIT_SCHEMA })

return { finals, critique }