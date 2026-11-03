export const meta = {
  name: 'f2-dense-mask-review',
  description: 'Adversarially verify the dense-page live-mask fast path for issue 5097 (mask equality with the per-token loop in every case)',
  phases: [
    { title: 'Attack', detail: 'independent attackers look for a case where the fast path and the loop disagree' },
    { title: 'Verify', detail: 'refute each claimed counterexample against the code' },
    { title: 'Synthesize', detail: 'verdict, required changes, test proposal' },
  ],
}

const CTX = `
Patch under review: the single uncommitted-or-last commit in worktree /home/jhan/workspace/ai-runs/tron-ben-pr1-f2 (branch jhan-vnnik-1-5047-fixes-f2, base db76973fdd = PR 5098 head on PR 5047's branch). Show it with: git -C /home/jhan/workspace/ai-runs/tron-ben-pr1-f2 diff db76973fdd -- h/tron/models/self_attention.hpp (if that diff is empty, use git show HEAD). It is in apply_page_tok (around lines 1894-1930). The fast path: when end > begin && query_visible && page.at_offset(end - 1) < range_hint->tok_hi && (int)q_position - (int)(k_position + begin) < sliding_window_size, the live mask is one run of ones over [begin, end) and the per-token loop is skipped. relevant_k_tokens becomes std::popcount(live) in both paths.
Claim to attack: for every input state, the fast path produces exactly the live mask, the relevant_k_tokens value, the range_hint pointer and the query_visible value that the per-token loop would have produced. Equivalent outputs mean identical scores and identical generated tokens.
Context: the same dense test exists in is_dense_amx_page (self_attention.hpp around line 1710) for full pages only. Read the whole of apply_page_tok and apply_page_range (lines ~1480-1700 and 1800-2010), the page accessors at_offset / offset_for / count in h/tron/models/kv_cache.hpp, the query_mask / token_range / find_range / visible / sw_required code (grep for 'struct token_range' and 'find_range' under h/tron/), the EAGLE begin = 1 case (Note [EAGLE first token exception]), sliding-window models (gemma / Glimmer, sliding_window_size and illegal_sliding_window), hardware-attention mixing (run_visible_in_software false -> sw_required), and pages with count() < page_size (the last page of a prompt, pages under forgets or reclaim).
HARD RULES: read-only on every worktree (git diff/show/log are fine, never checkout or edit). Never ssh anywhere. Files you create go under /tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/f2review/. Plain English, one claim per sentence, no semicolons.
`

const A_SCHEMA = { type: 'object', properties: { counterexamples: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, state: { type: 'string' }, loop_result: { type: 'string' }, fast_result: { type: 'string' }, code_refs: { type: 'string' }, severity: { type: 'string' } }, required: ['id', 'state', 'loop_result', 'fast_result', 'code_refs', 'severity'] } }, notes: { type: 'string' } }, required: ['counterexamples', 'notes'] }

phase('Attack')
const LENSES = [
  'token ordering: is page.at_offset(i) strictly increasing in i for every i in [begin, end), on every page kind (fresh, after forget, after reclaim, EAGLE, speculative branches, "stale entries from other branches" that count() skips)? If at_offset is not monotone, the loop may advance the hint at an inner token while the fast path tests only end - 1.',
  'the range hint: can range_hint at entry point to a range whose tok_lo is above page.at_offset(begin), or to a range that does not contain the page at all, so that the loop advance (kv_idx >= tok_hi) fires or does not fire differently from the fast test? Read find_range and how page_begin_hint / range_hint are threaded between pages in apply_page_range.',
  'sliding window: positions. The loop uses k_position + i with k_position = token_positions[page.at_offset(0)]. Are positions contiguous within a page for every model (EAGLE, speculative decoding, batched prompts, Glimmer / gemma sliding windows)? Does illegal_sliding_window (no window) make the test trivially true? Is the integer arithmetic the same in both paths?',
  'partial pages and begin: end = page.count() < page_size, begin = 1 for EAGLE. Check the mask arithmetic for n in {1, 63, 64}, begin in {0, 1}, and that bits above count() stay 0 (page::score_k and the softmax epilogue must not see bits for tokens that are not on the page). Also end == begin and end == 0.',
  'hardware-attention mixing: run_visible_in_software false uses sw_required(job_ix). Can query_visible be true at entry yet the loop skip tokens, or false at entry yet the loop select tokens, in a way the fast test misses? Also the AMX path above: can the fast path change which visits reach apply_dense_amx_page (it must not).',
  'relevant_k_tokens and returned values: the loop counted only selected tokens, so popcount is equal. But check every reader of relevant_k_tokens and page_tok_result (visit path stats, the early return when 0, attn_stats) and the returned range_hint. Is there any reader that depended on the loop having advanced the hint even for a dense page?',
]
const attacks = await parallel(LENSES.map((lens, k) => () => agent(`You are trying to BREAK a patch. Find a concrete input state where the fast path and the per-token loop give different results.\n${CTX}\nYour lens: ${lens}\nFor every counterexample give the exact state (page contents, begin, end, hint range, positions, window, flags), what the loop computes, what the fast path computes, and the code lines that prove each step. Default to reporting a counterexample only when you can trace both results in the code. Also report in notes what you verified holds (with line references), so the synthesis can cite it. Write your full notes to f2review/attack-${k}.md.`,
  { label: `attack:${k}`, phase: 'Attack', schema: A_SCHEMA })))

const all = attacks.filter(Boolean).flatMap((a, k) => a.counterexamples.map(c => ({ ...c, lens: k })))
log(`${all.length} counterexamples claimed`)

phase('Verify')
const V_SCHEMA = { type: 'object', properties: { refuted: { type: 'boolean' }, confidence: { type: 'string' }, reason: { type: 'string' }, required_change: { type: 'string' } }, required: ['refuted', 'confidence', 'reason'] }
const verified = await parallel(all.map(c => () => parallel([0, 1].map(v => () =>
  agent(`Adversarially verify a claimed counterexample against the code. Default to refuted=true unless you can reproduce the trace yourself from the code.\n${CTX}\nClaim ${c.id} (lens ${c.lens}): state: ${c.state}\nLoop result: ${c.loop_result}\nFast-path result: ${c.fast_result}\nCode refs: ${c.code_refs}\nTrace both paths yourself. Can this state occur at run time (who constructs it)? If the claim holds, say what change to the fast-path condition fixes it.`,
  { label: `verify:${c.id}:${v}`, phase: 'Verify', schema: V_SCHEMA }))).then(vs => ({ ...c, votes: vs.filter(Boolean) }))))
const real = verified.filter(c => c.votes.length && c.votes.filter(v => !v.refuted).length >= 1)
log(`${real.length} counterexamples survive at least one verifier`)

phase('Synthesize')
const S_SCHEMA = { type: 'object', properties: { verdict: { type: 'string' }, required_changes: { type: 'array', items: { type: 'string' } }, verified_invariants: { type: 'array', items: { type: 'string' } }, test_proposal: { type: 'string' }, report_path: { type: 'string' } }, required: ['verdict', 'required_changes', 'verified_invariants', 'test_proposal', 'report_path'] }
const synth = await agent(`Write the review record for the dense-page mask fast path.\n${CTX}\nAttack notes: f2review/attack-*.md. Surviving counterexamples with verifier votes:\n${JSON.stringify(real, null, 1)}\nRefuted claims (one line each with the reason):\n${JSON.stringify(verified.filter(c => !real.includes(c)).map(c => ({ id: c.id, state: c.state, reasons: c.votes.map(v => v.reason) })), null, 1)}\nWrite f2review/review.md: Short version (verdict: safe as written / needs the listed change), the invariants that were verified with line references (at_offset monotone, hint threading, positions, mask arithmetic, readers of relevant_k_tokens), the required changes if any (exact condition text), and a test proposal: the smallest unit test (which existing test file and harness in t/ can drive apply_page_tok or apply_page_range with a crafted query mask and page count, or a mutation check: which existing case fails if the fast path sets one wrong bit). Return the structured verdict.`,
  { label: 'synthesize', phase: 'Synthesize', schema: S_SCHEMA })
return { claimed: all.length, surviving: real.length, synth }