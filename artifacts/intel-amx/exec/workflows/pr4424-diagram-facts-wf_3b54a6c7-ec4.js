export const meta = {
  name: 'pr4424-diagram-facts',
  description: 'Extract and adversarially verify the data/function/sequence facts and the unit partition for the three PR 4424 diagram pages',
  phases: [
    { title: 'Extract', detail: '4 lenses per file (data model, functions, sequences/threads, unit partition review)' },
    { title: 'Refute', detail: '2 refuters per claim set, then a judge for disputed claims' },
    { title: 'Write', detail: 'one writer per file saves the verified facts JSON' },
  ],
}

const G = '/home/jhan/workspace/intel-AMX/exec/pr4424-diagrams-20261009'
const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-merge-4737-2-4424/daed4d8b-e695-45e4-a9c9-1635c10014f7/scratchpad/diffs'
const WT = '/home/jhan/workspace/ai-runs/tron-vnnik-i4500m'

const FILES = [
  { key: 'kv_cache', file: 'h/tron/models/kv_cache.hpp', diff: `${S}/kv_cache.hpp.diff`, head: `${S}/kv_cache.hpp.head`,
    related: [`${S}/tensor_k_vnni.hpp.head`, `${S}/model.hpp.diff`, `${S}/self_attention.hpp.diff`, `${S}/full.hpp.diff`, `${S}/gof.hpp.diff`, `${S}/kv_cache_fwd.hpp.diff`] },
  { key: 'k_vnni', file: 'h/tron/tensor/k_vnni.hpp', diff: `${S}/tensor_k_vnni.hpp.diff`, head: `${S}/tensor_k_vnni.hpp.head`,
    related: [`${S}/kernels_k_vnni.hpp.head`, `${S}/kv_cache.hpp.diff`, `${S}/model.hpp.diff`, `${S}/self_attention.hpp.diff`, `${S}/amx_attn.cpp.diff`, `${S}/amx_attn_iface.hpp.diff`, `${S}/kv_cache_fwd.hpp.diff`] },
  { key: 'model', file: 'h/tron/models/model.hpp', diff: `${S}/model.hpp.diff`, head: `${S}/model.hpp.head`,
    related: [`${S}/common.hpp.diff`, `${S}/kv_cache.hpp.diff`, `${S}/tensor_k_vnni.hpp.head`, `${S}/TronCpp.hs.diff`, `${S}/self_attention.hpp.diff`, `${S}/full.hpp.diff`] },
]

const COMMON = (f) => `You are extracting VERIFIED facts for a diagram page about what tron PR 4424 (branch jhan-amx-vnniK, head 9d5c7a389b, base main be0d5565b3) changes in ${f.file}.
Sources (read them; do not guess):
- the file's diff vs main: ${f.diff}  (unified diff, -U3; '+' lines are the PR's additions; head line numbers = the file at the head)
- the file at the head: ${f.head}  (line numbers in this file are the "head line numbers" every citation must use)
- related files of the same PR (callers/callees): ${f.related.join(', ')}
- the full worktree at the head for anything else: ${WT} (read-only; use grep/sed there; never modify it)
- the draft unit partition the page will use: ${G}/units_draft.json (key "${f.file}")
Citation rule: every claim carries a cite of the form "<basename>:<line>" or "<basename>:<a>-<b>" (head line numbers) or "Note [name] (<basename>:<a>-<b>)". Prefer the comment or declaration that DEFINES the thing. No invented names: every identifier in a claim must appear verbatim in the code. Do not paraphrase identifiers (write k_rows_saved_, not "rows-saved bits", when naming the box).
Return ONLY the structured output. Keep each claim's text to one or two plain-English sentences. Ids: "${f.key}-<lens>-<n>".`

const CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    claims: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      kind: { type: 'string', enum: ['data_box', 'cardinality', 'function', 'sequence_step', 'thread_rule', 'unit_issue', 'glossary'] },
      text: { type: 'string' },
      cite: { type: 'string' },
      fields: { type: 'object' },
    }, required: ['id', 'kind', 'text', 'cite'] } },
    notes: { type: 'string' },
  },
  required: ['claims'],
}

const LENSES = {
  data: (f) => `${COMMON(f)}
LENS = DATA MODEL. List every data-model box a diagram of this file's changes needs, and every arrow between boxes WITH ITS CARDINALITY.
kind "data_box": one per type/struct/member/array/constant/bit set that the PR adds or changes in this file, plus the pre-existing containers they live in (book, page, kv_block, batch, ...). fields: {name, container, type_or_shape, new_or_changed: "new"|"changed"|"unchanged context", one_line}. one_line = what it holds, from the code comment.
kind "cardinality": one per containment/reference arrow, text like "one page has layout_t::n_slots + EAGLE_STORAGE_SLOTS_1 entries of k_rows_saved_". fields: {from, to, how_many, proof}. how_many must be an expression from the code (n_slots + 1, n_kv_heads, 16, 4, page_size / BLOCK_TOKENS_16, n_units + 1, max_shared_workers ...), proof = the line that shows the count (an array size, a loop bound, a static_assert).
Aim for completeness: 20-45 claims. Include the worked-example numbers the comments give (64 tokens, 16 KiB plane, 1 KiB panel, 256-byte row, 4 KiB block).`,
  fn: (f) => `${COMMON(f)}
LENS = FUNCTION MODEL. One claim of kind "function" per function/method/lambda/constexpr helper that the PR adds or changes in this file (every one, including private helpers, overloads counted once with a note, deleted functions tagged "removed"). fields: {name, one_line, defined_at, tag: "new"|"changed"|"removed"|"comment only", callers: [ "<file>:<line> <function>" ...], callees: [names], thread: "who calls it (main thread / main helpers / attention workers / scheduler thread / tests / any)", returns_or_effect}.
one_line = what the function does, in plain words, taken from its comment (quote or compress the comment; do not invent). callers/callees come from the diffs of the related files and from grep in the worktree (cite file:line). thread comes from a comment that says so; write "not stated" otherwise.
Aim for completeness: every function in the file's diff. 15-40 claims.`,
  seq: (f) => `${COMMON(f)}
LENS = SEQUENCING AND INTERACTION. Extract the ORDERED steps of every process this file's changes take part in, and every rule about which thread may do what, when.
kind "sequence_step": fields {process, step_no, actor (thread or function), action, happens_before: "what must be done before", why}. Processes to cover where the file is involved: the life of one 16-token block (empty -> row-major rows -> complete waits -> converted VNNI, and back on clear/copy); one save_k call of a shared window (cut units, open, helpers wait, claim loop, finished, join, marks, row-recording, queue); the forward end (run() joined, wait_for_coop_gof, convert_pending_k_blocks, logits); a page copy (copy_from -> copy_storage_slot); the scoring of one page (dense gate k_layout_dense, software loop live mask, qk_group, row-major tail dotter); the FPGA staging read (k_head_fn, k_row_if_row_major, get_k_row). Only those this file touches, but cite the other files' lines for the steps that live there.
kind "thread_rule": one per rule like "k_block_to_vnni_at: main thread only, at the forward end, no reader runs", "clear_kv_complete_at runs with the token tree locked between forward passes", "helpers never wait for a window main does not open". fields {rule, who, when, guard, why}.
Every step and rule cites the comment or line that states it. 20-45 claims.`,
  units: (f) => `${COMMON(f)}
LENS = UNIT PARTITION REVIEW. The draft partition in ${G}/units_draft.json (key "${f.file}") splits the diff into logical units ("1 code change" = a logical unit: e.g. 5 lines that update one data model used by other code; 10 lines that check one data model against another) and trivial changes. Review it against the diff:
1. kind "unit_issue" per problem: a unit that mixes two logical changes (say where to split), two units that are one change (say which to merge), a unit whose title or lead bullet states something the code does not do (quote the line that contradicts it), a trivial entry that is in fact a behaviour change, a missing lead bullet for a notable behaviour in the unit's lines (e.g. memory orders, return values, asserts), or a wrong range. fields {unit_id, severity: "must"|"should"|"nit", problem, proposed_fix, proposed_lead_bullets: [..] (full replacement list when you propose one)}. If a unit is correct, still emit one claim with severity "nit" and problem "none" so coverage is explicit.
2. kind "glossary": every term a newcomer engineer would need defined on this page (code names, acronyms, metrics, project words: tron, book, page, slot, EAGLE, KV head, plane, panel, pair row, VNNI, AMX, AVX-512, bf16, GOF, staging, DMA, minibatch, grain, main helpers, attention workers, scheduler thread, tree lock, latch, acquire/release, fetch_or, kill switch, TRON_K_VNNI, TRON_AMX_DISABLE, dotter, qk_group, qk_vnni_128x4, dense AMX path, hardware attention, engagement point, work unit, window, ...). fields {term, definition (one or two sentences, plain English, from the code comments), source}. Only terms that appear in this file's diff or its direct callers.
30-70 claims.`,
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      verdict: { type: 'string', enum: ['confirmed', 'corrected', 'refuted'] },
      note: { type: 'string' },
      corrected_text: { type: 'string' },
      corrected_cite: { type: 'string' },
      corrected_fields: { type: 'object' },
    }, required: ['id', 'verdict', 'note'] } },
  },
  required: ['verdicts'],
}

const refutePrompt = (f, lens, claims, angle) => `You are an adversarial checker. Another agent extracted the claims below about what tron PR 4424 changes in ${f.file}. Your job is to REFUTE them: for every claim, open the cited lines (head line numbers in ${f.head}; the diff is ${f.diff}; related files ${f.related.join(', ')}; full worktree ${WT}, read-only) and decide.
Angle: ${angle}
Verdicts: "confirmed" = the text is true and the cite points at the line/comment that defines or states it. "corrected" = true in substance but the cite, a number, a name or a detail is wrong: give corrected_text / corrected_cite / corrected_fields (only the keys that change). "refuted" = the claim is false, invented, or names an identifier that does not exist in the code: say why. Default to "corrected" or "refuted" when uncertain; never confirm without reading the cited lines. Check EVERY identifier appears verbatim in the code. Check every count (how_many) against an array size, loop bound or static_assert. Return a verdict for every claim id.
CLAIMS (JSON):
${JSON.stringify(claims)}`

const judgePrompt = (f, disputed) => `You are the judge. For each claim below, two checkers disagreed or at least one corrected/refuted it. Read the cited code yourself (head file ${f.head}, diff ${f.diff}, related ${f.related.join(', ')}, worktree ${WT} read-only) and return the FINAL version: verdict "confirmed" (keep the original text/cite), "corrected" (give the final corrected_text/corrected_cite/corrected_fields, merging the right parts of the checkers' corrections), or "refuted" (drop). Be exact: the final text and cite go onto a diagram page as-is.
ITEMS (each = claim + the two checkers' verdicts):
${JSON.stringify(disputed)}`

const writerPrompt = (f, facts) => `Write the verified facts JSON for ${f.file} to ${G}/facts/${f.key}.json (create the directory if needed; overwrite). Content = exactly the JSON object below, pretty-printed with indent 1, UTF-8, nothing else. Then run: python3 -c "import json; d=json.load(open('${G}/facts/${f.key}.json')); print(len(d['claims']))" and return the printed count and a 5-line summary of what the file holds (how many claims per kind, how many unit issues of severity must/should). Do not edit any other file.
JSON:
${JSON.stringify(facts)}`

phase('Extract')
const results = await pipeline(
  FILES.flatMap(f => Object.keys(LENSES).map(lens => ({ f, lens }))),
  ({ f, lens }) => agent(LENSES[lens](f), { label: `extract:${f.key}:${lens}`, phase: 'Extract', schema: CLAIMS_SCHEMA }),
  async (res, { f, lens }) => {
    if (!res || !res.claims || !res.claims.length) { log(`extract ${f.key}:${lens} returned nothing`); return { f, lens, claims: [] } }
    const claims = res.claims
    const angles = [
      'correctness of the statement against the code (does the code do exactly this? are the numbers right?)',
      'exactness of citations and names (does the cite point at the defining line/comment? does every identifier exist verbatim? is every how_many proven by an array size, loop bound or static_assert?)',
    ]
    const votes = await parallel(angles.map((a, i) => () =>
      agent(refutePrompt(f, lens, claims, a), { label: `refute${i + 1}:${f.key}:${lens}`, phase: 'Refute', schema: VERDICT_SCHEMA })))
    const byId = {}
    for (const v of votes.filter(Boolean)) for (const x of v.verdicts) (byId[x.id] = byId[x.id] || []).push(x)
    const kept = [], disputed = []
    for (const c of claims) {
      const vs = byId[c.id] || []
      if (vs.length === 2 && vs.every(v => v.verdict === 'confirmed')) kept.push(c)
      else disputed.push({ claim: c, checkers: vs })
    }
    log(`${f.key}:${lens}: ${claims.length} claims, ${kept.length} confirmed by both, ${disputed.length} disputed`)
    let judged = []
    if (disputed.length) {
      const j = await agent(judgePrompt(f, disputed), { label: `judge:${f.key}:${lens}`, phase: 'Refute', schema: VERDICT_SCHEMA })
      const jv = {}
      for (const x of (j ? j.verdicts : [])) jv[x.id] = x
      for (const d of disputed) {
        const v = jv[d.claim.id]
        if (!v) { judged.push({ ...d.claim, status: 'unjudged' }); continue }
        if (v.verdict === 'refuted') { judged.push({ ...d.claim, status: 'refuted', note: v.note }); continue }
        if (v.verdict === 'corrected') judged.push({ ...d.claim, text: v.corrected_text || d.claim.text, cite: v.corrected_cite || d.claim.cite, fields: Object.assign({}, d.claim.fields || {}, v.corrected_fields || {}), status: 'corrected', note: v.note })
        else judged.push({ ...d.claim, status: 'confirmed' })
      }
    }
    const final = kept.map(c => ({ ...c, status: 'confirmed' })).concat(judged)
    return { f, lens, claims: final }
  }
)

phase('Write')
const perFile = {}
for (const r of results.filter(Boolean)) {
  const k = r.f.key
  perFile[k] = perFile[k] || { file: r.f.file, claims: [] }
  perFile[k].claims.push(...r.claims)
}
const summaries = await parallel(FILES.map(f => () => {
  const facts = perFile[f.key] || { file: f.file, claims: [] }
  const live = facts.claims.filter(c => c.status !== 'refuted')
  const dropped = facts.claims.filter(c => c.status === 'refuted')
  return agent(writerPrompt(f, { file: f.file, claims: live, refuted: dropped }), { label: `write:${f.key}`, phase: 'Write', effort: 'low' })
}))
return { summaries, counts: Object.fromEntries(Object.entries(perFile).map(([k, v]) => [k, { total: v.claims.length, refuted: v.claims.filter(c => c.status === 'refuted').length, corrected: v.claims.filter(c => c.status === 'corrected').length, unjudged: v.claims.filter(c => c.status === 'unjudged').length }])) }
