export const meta = {
  name: 'prefill-decode-global-state',
  description: 'Find whether tron has a per-forward or per-token-job fact that says prefill vs decode, usable by the attention stats classifier',
  phases: [
    { title: 'Read', detail: '6 readers, one code region each' },
    { title: 'Refute', detail: '2 refuters per reader claim' },
    { title: 'Synthesize', detail: 'one synthesis + one critic' },
  ],
}
const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const CTX = `Repository worktree: ${WT} (tron, branch jhan-attn-path-stats, HEAD ebadce2adb; the working tree may be mid-edit, so read committed content with: git -C ${WT} show HEAD:<path> | cat -n, and grep with git -C ${WT} grep -n <pattern> HEAD -- <paths>).
Background: PR #4596 adds attention path statistics (h/tron/models/attn_stats.hpp). It classifies every model forward into two classes at model.hpp near line 1746: decode_like when n_listeners == token_jobs.size() (every token job has a listener), prompt_or_mixed otherwise. A listener is one scheduler entry per request edge on its last token (h/tron/scheduler/full.hpp ~2141-2148); every prompt chunk gets one (empty logits buffer when the chunk is not the final one).
The PR author asks: is there any global state (per forward, per token job, per request) from which the forward could be classified as PREFILL (prompt tokens) versus DECODE (generated tokens) exactly, for example "token position greater than the prompt length means decode"? The answer must be grounded in code with file:line citations. Do not edit any file. Return raw facts, not prose for a human.`

const READERS = [
  { key: 'forward-inputs', prompt: 'Read model::state::forward and the arrays the scheduler passes into it (h/tron/models/model.hpp: the forward(...) signature near lines 1630-1680, in_tokens, token_positions, token_pages, live_groups, in_listener_index, token_jobs_do_kv, and anything else per token job). List EVERY per-token-job and per-forward input that reaches begin_forward (model.hpp ~1745). For each say what it encodes and whether it distinguishes a prompt token from a generated token. Also read model.hpp near line 100 where a comment mentions "prompt/decode classification" kept "in the executor": quote it and find the executor code it refers to.' },
  { key: 'scheduler-jobs', prompt: 'Read h/tron/scheduler/full.hpp where token jobs are built for a forward (attempt_kv_job ~2121-2139, the listener branch ~2462-2483, the live_token_limit cut ~2342-2347, the forward call ~2085-2105). Does the scheduler know, per token job or per request node, whether the tokens came from a client prompt (sequence_prompt / extend_request) or from a sampled/generated token? Look at the request tree node/edge structures (what fields an edge or node has: origin, is_prompt, generated flag, sampled, prompt length, n_prompt_tokens, position). Cite every field that could tell prompt from generated.' },
  { key: 'generation', prompt: 'Read src/tron/generation/context.cpp (prompt submission ~38-78, decode step ~136-181, ~230), src/tron/scheduler/full.cpp (extend_request ~190-193), src/tron/generation/speculate.cpp (~692-710), and h/libtron.hpp (get_prompt_chunk_size ~193-205). At the generation layer: does a request know its prompt length? Is there a per-request field like prompt_tokens, n_prompt, prompt_len, or a phase flag (prefill/decode)? Does the decode step append tokens through the same path as prompt chunks (so the scheduler cannot tell them apart) or through a different path with a flag? Cite file:line.' },
  { key: 'metrics', prompt: 'Find every existing tron metric, log line, perfetto TRACE_EVENT arg or checkpoint that already distinguishes prompt/prefill from decode/generation: git grep -n -i -E "prefill|decode|prompt_tokens|generated_tokens|n_prompt|is_prompt|ttft|time_to_first|tokens_per_second" HEAD -- h src (skip ingest/ and tests). For each hit that carries such a distinction at runtime, say where the fact comes from (which variable) and whether it is visible inside model::state::forward or only in the scheduler/generation layer.' },
  { key: 'positions', prompt: 'Evaluate the author\'s proposed rule "if the token position (sequence number) is greater than the prompt length, the token is a decode token". Read how token_positions are set (h/tron/models/model.hpp token_positions, h/tron/scheduler/full.hpp where positions are assigned) and whether "prompt length" per request is available anywhere the model or scheduler can read it at forward time. Consider: prefix-cache hits (cached prompt re-query with do_kv=0), speculative verify steps (draft tokens have positions past the prompt but are not sampled decode tokens in the usual sense), constraint fast-forward tokens (>1 token per user per step), branches/trees (a node with several children), and multi-user forwards mixing prefill and decode. For each, state whether the rule gives the right answer and cite file:line.' },
  { key: 'cheap-flag', prompt: 'Design question, grounded in code: if tron wanted an exact per-token-job flag "prompt token vs generated token" available at model::state::forward time, what is the smallest change? Candidates: (a) a per-token-job bit array next to token_jobs_do_kv filled by the scheduler from the request edge origin; (b) a per-request counter of client-supplied tokens compared with the token position; (c) reuse of an existing field. Read h/tron/models/model.hpp forward inputs (~1630-1710), h/tron/scheduler/full.hpp job building (~2100-2180, ~2440-2490) and src/tron/scheduler/full.cpp extend_request (~150-230) and say, with file:line, which fields exist, which would be new, and what the three-class version of the stats (all prompt / all generated / mixed) would need. Do not propose code, list facts and the minimal set of touched functions.' },
]
const FACTS = { type: 'object', properties: {
  key: { type: 'string' },
  facts: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, citation: { type: 'string' } }, required: ['claim', 'citation'] } },
  answer_to_author: { type: 'string', description: 'in 3-6 sentences: what this region says about prefill-vs-decode knowability' },
}, required: ['key', 'facts', 'answer_to_author'] }
const VERDICT = { type: 'object', properties: { refuted_claims: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, why: { type: 'string' }, citation: { type: 'string' } }, required: ['claim', 'why', 'citation'] } }, all_hold: { type: 'boolean' } }, required: ['refuted_claims', 'all_hold'] }

phase('Read')
const read = await pipeline(
  READERS,
  r => agent(`${CTX}\n\nYour region: ${r.key}. ${r.prompt}`, { label: `read:${r.key}`, phase: 'Read', schema: FACTS }),
  async (f, r) => {
    if (!f) return null
    const votes = (await parallel([1, 2].map(k => () =>
      agent(`${CTX}\n\nYou are refuter ${k}. Try to REFUTE each of these facts by reading the code; list only the ones you can contradict with file:line evidence.\n${JSON.stringify(f.facts, null, 1)}`,
        { label: `refute${k}:${r.key}`, phase: 'Refute', schema: VERDICT })))).filter(Boolean)
    return { ...f, refutations: votes }
  },
)
phase('Synthesize')
const SYN = { type: 'object', properties: {
  short_answer: { type: 'string', description: '3 sentences for the PR author' },
  what_exists: { type: 'array', items: { type: 'string' }, description: 'facts with citations: which prompt-vs-decode information exists where' },
  rule_evaluation: { type: 'array', items: { type: 'string' }, description: 'the author\'s position>prompt-length rule: case by case, right or wrong, with citation' },
  options: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, mechanism: { type: 'string' }, exactness: { type: 'string' }, cost: { type: 'string' } }, required: ['name', 'mechanism', 'exactness', 'cost'] } },
  recommendation: { type: 'string' },
}, required: ['short_answer', 'what_exists', 'rule_evaluation', 'options', 'recommendation'] }
const syn = await agent(`${CTX}\n\nSynthesize the readers' verified facts (drop any fact both refuters contradicted) into an answer for the PR author. Facts:\n${JSON.stringify(read.filter(Boolean), null, 1)}`, { label: 'synthesis', phase: 'Synthesize', schema: SYN })
const critic = await agent(`${CTX}\n\nYou are the completeness critic. Here is a synthesis about whether prefill vs decode is knowable per forward/token job. What is missing, unverified, or wrong? Check every citation you doubt in the code. Return a list of corrections with file:line, and an "ok" list of the claims you verified.\n${JSON.stringify(syn, null, 1)}`, { label: 'critic', phase: 'Synthesize', schema: { type: 'object', properties: { corrections: { type: 'array', items: { type: 'string' } }, ok: { type: 'array', items: { type: 'string' } } }, required: ['corrections', 'ok'] } })
return { read: read.filter(Boolean), syn, critic }