export const meta = {
  name: 'no-haskell-savek-exploration',
  description: 'Search for a way to satisfy the PR 4424 reviewer suggestion on save_k without changing the Haskell generator; refute weak proposals',
  phases: [{ title: 'Design', detail: 'four independent angles' }, { title: 'Refute', detail: 'two refuters per proposal' }, { title: 'Critic', detail: 'completeness check' }],
}
const CTX = `
READ-ONLY task: never edit files, never run state-changing git commands (no checkout/commit/reset/stash/clean). Scratch copies via "git show <rev>:<path>" or "git worktree" are NOT allowed either; read with git show / sed / grep only.
Repository worktree: /home/jhan/workspace/ai-runs/tron-vnnik-savek2 (positron-ai/tron) at HEAD 45e6bb266d = merge of PR 4774 (f52d634c32) onto the jhan-amx-vnniK head 6b939d25d2. origin/main is fetched (main has NO VNNI K code).

Background (verified facts):
- PR 4424 ("VNNI K", branch jhan-amx-vnniK) stores K in the AMX VNNI layout and added a "shared block save": the main thread's save_k cuts the pass into work units and the idle main helpers claim units (Note [Shared block save] in h/tron/models/model.hpp). PR 4424's generator change (ingest/src/TronCpp.hs vs main merge-base c7844ca2ce) is: in runHelperStatement the case "AttentionStmt _ -> []" became a case that emits "save_k_helper<geometry,op>(q_batch->outer_batch, k, worker_ix, n_workers)" for KV-writing operations, and the main-side submitAttentionOperation call became "save_k(..., k, n_workers)".
- Reviewer Ben's comment r4065141577 (2026-09-21) is anchored on exactly that Haskell hunk (the helper-side save_k_helper emission): "Why do we need to introduce a new function for this? Why not simply extend save_k itself with a worker_ix argument and call it consistently from both the main thread and the helpers?"
- PR 4774 (now merged as 45e6bb266d) implements that literally: save_k(q_batch, ks, worker_ix = 0, n_workers = 1); the helper side emits save_k(..., worker_ix, n_workers), the main side save_k(..., 0, n_workers); save_k_helper removed. Its Haskell diff vs 6b939d25d2: two emitted call lines + comments in TronCpp.hs and the expected texts in ingest/test/LoopyTronSpec.hs. See: git diff 6b939d25d2 45e6bb266d -- ingest/
- jhan (the author) now asks: "my impression was, his suggestion was not to modify haskell code at all ... see if there is solution without changing haskell (revert the haskell changes first)". "The Haskell changes" = PR 4774's changes to ingest/ (relative to 6b939d25d2). With those reverted, the generator emits save_k_helper(k, worker_ix, n_workers) on the helper side and save_k(k, n_workers) on the main side.
- At main, the helpers execute NOTHING at the attention statement; in the generated run_main_help the statements around it are (qwen3-4b): kernel_rmsnorm_rope_rmsnorm_rope(q_batch, worker_ix, n_workers); <finish_writing/finish_reading of the rope/linear channels>; [the helper-side save_k call]; q_batch->mul_19_channel.start_writing(worker_ix); q_batch->linear_channel_2.start_reading(worker_ix) [= consumer_barrier.wait(worker_ix) + latch wait, h/tron/models/common.hpp:593]; kernel_add_rmsnorm(...). The main helpers run run_main_help as one long thread-pool task (TronCpp.hs ~1359), the attention workers run run_attention_worker likewise; batch::reset_channels(n_attn_workers, n_main_workers) tells the batch the worker counts (common.hpp:1045).
- Measured on delphi-3bda 2026-09-15 (Perfetto traces, qwen3-4b, 8 users x 128 tokens per prefill pass, us of Save K per layer, tp2/tp4): row-major base 274/281; VNNI scatter 858/863; block save alone 346/353; sharing alone 175/110; block save + sharing 80/60. Save K sits on the prefill critical path (the attention workers' pending sections wait behind it).

Question to answer: is there a design that satisfies the reviewer's intent ("one save_k, no second entry point") WITHOUT any change to ingest/ relative to 6b939d25d2 (i.e. with the generator still emitting save_k_helper on the helper side), or alternatively WITHOUT any change to ingest/ relative to main (helpers emit nothing at the attention statement), while keeping the measured sharing gain? Be concrete: name the C++ functions/lines you would change, and state which constraint each design violates, if any.
`
const PROPOSAL = { type: 'object', properties: {
  angle: { type: 'string' }, feasible: { type: 'boolean' },
  design: { type: 'string' }, changes: { type: 'string' }, keeps_sharing_gain: { type: 'boolean' },
  haskell_diff_vs_6b939d25d2: { type: 'string', enum: ['none', 'smaller than PR 4774', 'same as PR 4774', 'larger'] },
  satisfies_reviewer_intent: { type: 'boolean' }, risks: { type: 'string' }, evidence: { type: 'string' } },
  required: ['angle', 'feasible', 'design', 'changes', 'keeps_sharing_gain', 'haskell_diff_vs_6b939d25d2', 'satisfies_reviewer_intent', 'risks', 'evidence'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const ANGLES = [
  { key: 'generator-unchanged-vs-4424', prompt: `Angle A: keep ingest/ exactly as at 6b939d25d2 (helper side emits save_k_helper(k, worker_ix, n_workers), main side save_k(k, n_workers)). Is there ANY C++ shape (aliases, using-declarations, a single template with a tag, overload tricks, macros) under which the reviewer's objection ("a new function") is honestly answered? Read model.hpp around save_k/save_k_impl. Decide and justify.` },
  { key: 'cpp-only-sharing', prompt: `Angle B: keep ingest/ exactly as at main (helpers emit nothing at the attention statement). Design the helpers' participation in C++ only: e.g. a hook in the channel wait the helpers enter right after the statement (common.hpp channel::start_reading / consumer_barrier.wait / latch wait), or in kernel entry. Read common.hpp (channel, consumer_barrier, latch) and model.hpp (save_k_impl, k_store_window in common.hpp ~1170) and say exactly where the hook would go, how main finds out all units are stored, how a helper that never reaches the wait is handled, what happens on the handwritten plugins and in the unit tests, and how many shared primitives change. Is it simpler or more complex than the two emitted lines PR 4774 changes?` },
  { key: 'other-threads', prompt: `Angle C: keep ingest/ as at main. Could threads other than the generated main helpers store K (attention workers, the thread pool via app_pool().enqueue, a dedicated store thread)? Read how run() launches workers (TronCpp.hs ~1340-1400 in the merged tree), what the attention workers do while main runs save_k (Note [Shared block save] and the attention worker lane code in model.hpp), and the thread pool API (h/tron/ or src/ thread pool). Decide feasibility and cost.` },
  { key: 'reread-reviewer', prompt: `Angle D: re-read the reviewer's sentence in its anchor context (git diff c7844ca2ce 30c4ac82cb -- ingest/src/TronCpp.hs, the hunk at runHelperStatement) and the generator's existing patterns (kernelCall with worker_ix on helpers and IntLit 0 on main, TronCpp.hs ~2798 and ~2850). Is there a reading under which "call it consistently from both the main thread and the helpers" can be met with NO change to the generator relative to 6b939d25d2? Is there a reading under which the Haskell change could be SMALLER than PR 4774's (e.g. one shared emission function for both sides)? Also judge: is PR 4774's current Haskell diff the minimal change implied by the suggestion?` },
]
phase('Design')
const results = await pipeline(ANGLES,
  a => agent(CTX + '\n' + a.prompt + '\nReturn one proposal (the best you found for this angle), with evidence as file:line citations.', { label: `design:${a.key}`, phase: 'Design', schema: PROPOSAL }),
  (p, a) => {
    if (!p) return null
    log(`angle ${a.key}: feasible=${p.feasible} haskell=${p.haskell_diff_vs_6b939d25d2} sharing=${p.keeps_sharing_gain} intent=${p.satisfies_reviewer_intent}`)
    return parallel([1, 2].map(i => () => agent(
      CTX + `\nRefuter ${i} of 2. A designer (angle ${a.key}) proposes:\n` + JSON.stringify(p, null, 2) +
      `\nTry to REFUTE its feasibility / its claims (feasible, keeps_sharing_gain, haskell diff size, satisfies the reviewer's intent) by reading the code. Refuted = at least one stated claim is wrong or the design cannot work as described. Default refuted=true if uncertain. Cite file:line.`,
      { label: `refute:${a.key}:${i}`, phase: 'Refute', schema: VERDICT })))
      .then(vs => ({ angle: a.key, proposal: p, refutations: vs.filter(Boolean) }))
  })
const all = results.filter(Boolean)
phase('Critic')
const critic = await agent(CTX + `\nCompleteness critic. Here are four proposals with refutations:\n` + JSON.stringify(all, null, 2) +
  `\nWhat design angle is missing? Is there a zero-Haskell design nobody considered? State the single best honest answer to jhan's question in at most 8 sentences, plain English, with the decisive evidence (file:line or measured numbers).`,
  { label: 'critic', phase: 'Critic' })
return { proposals: all, critic }