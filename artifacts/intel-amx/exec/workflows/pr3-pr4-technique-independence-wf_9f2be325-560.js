export const meta = {
  name: 'pr3-pr4-technique-independence',
  description: 'Check whether the PR 3 helper-sharing and PR 4 tail-block techniques work without the VNNI K layout, then attack the conclusions',
  phases: [
    { title: 'Read', detail: 'four readers over main, the PR 3 diff, the PR 4 diff and the decode trace' },
    { title: 'Refute', detail: 'three skeptics per claim' },
  ],
}

const COMMON = `
Context (facts already established, do not re-derive; verify only what your task names):
- Repo: positron-ai/tron. Worktrees on this machine: main at 26b6df7d82 = ~/workspace/ai-runs/tron-main-ro (read-only use). PR 3 "shared block save" tree = ~/workspace/ai-runs/tron-split-pr3 (head b39765ec29, parent PR 2 head 26b86a279a). PR 4 "row-major tail block" tree = ~/workspace/ai-runs/tron-split-pr4 (head 6b081187e1, parent b39765ec29). Lazy-dotter probe = ~/workspace/ai-runs/tron-split-probe-pr4lazy (ca6456b7dc).
- Do NOT modify any worktree. Use git diff / sed / grep only. Do not run builds. Do not touch delphi-3bda.
- The stack: PR 1 = VNNI K layout + AVX-512 reader (PR #4956), PR 2 = AMX QK kernel on the plane (#4957), PR 3 = 16-token block save shared between the main thread and the idle main helpers (#4958), PR 4 = row-major tail block, forward-end conversion, row-major policy under hardware attention, deb preset (#4959).
- Live PR bodies: ~/workspace/intel-AMX/PR3879/new-PRs/split-4424/exec/newprs-20261015/new/4958-v2.md and 4959-v2.md. Note [Shared block save] is at tron-split-pr3 h/tron/models/model.hpp:3075-3160.
- Trace data of main (row-major K, "base") vs the VNNI branch, qwen3-4b, 8 users, prompt 1024, CPU attention, 2026-09-14: ~/workspace/intel-AMX/exec/results/vnnik-trace-20260914/analysis.md and the *.lanes.json files there (spans of one prefill layer and one decode step on every thread; cls = main / helper / attention). Main's Save K = 274 us and Save V = 295 us per prefill layer at tp2 (2.5 % + 2.7 % of a 393 ms prefill pass), 281 + 295 us at tp4 (3.7 % + 3.9 %); helpers busy 0.00 during both spans; decode Save K+V = 8 to 11 us per layer, hidden behind the attention workers' Ready sections.
- Generated plugins: main thread runs run(), helpers run run_main_help() (TronCpp.hs emits both; see tron-main-ro ingest/src/TronCpp.hs lines 1340-1430 and runHelperStatement at ~2820). recommend_n_main_helpers() picks the helper count.
Return raw findings with file:line citations. Plain English, no idioms. Mark anything you could not verify as "unverified".`

const READ_SCHEMA = { type: 'object', properties: {
  findings: { type: 'string', description: 'the answers, each with file:line citations' },
  unverified: { type: 'array', items: { type: 'string' } },
}, required: ['findings', 'unverified'] }

const readers = [
  { key: 'main-helpers', prompt: `${COMMON}
Task: in main (tron-main-ro), establish what the main thread and the helpers do around the attention statement of a generated plugin.
(a) In ingest/src/TronCpp.hs: what does run() emit at an AttentionStmt (save_k, save_v, submit of the attention operation, waits) and what does run_main_help emit at the same statement (runHelperStatement)? Quote the emitted C++ call text for save_k and save_v.
(b) In h/tron/models/model.hpp: find save_k_impl and save_v_impl (or whatever main names them). Are they executed on the main thread alone, in one loop over the minibatch's items? What else do they do besides the row copy (completion marks, GOF credits, token_jobs_do_kv checks)? Is the row-major K store one whole-line copy per row (page::set_k_row or similar) and is save_v the same shape?
(c) Where is recommend_n_main_helpers defined, what inputs does it use, and is the helper / attention-worker split decided per pass? Can a helper thread run attention sections, or are the two roles disjoint within a pass?
(d) Compare with PR 3's save_k_impl (tron-split-pr3 model.hpp 3075-3420, common.hpp k_store_window_t, TronCpp.hs hunks of git diff 26b86a279a b39765ec29): list concretely what a port of PR 3's sharing to main's row-major save_k AND save_v would need (functions, generator hunks, tests), and what it would NOT need (anything about transposes, present masks, set_k_block). Name any obstacle you see (ordering of the completion marks, GOF credits, token_jobs_do_kv, the handwritten plugins with n_workers 1, the deadlock argument for save_v).` },
  { key: 'pr3-classify', prompt: `${COMMON}
Task: classify every hunk of PR 3 (cd ~/workspace/ai-runs/tron-split-pr3 && git diff 26b86a279a b39765ec29) into one of three classes and count added lines per class per file:
  L = layout-specific: exists only because K is VNNI-packed (store_block, transpose_16x16_epi32, page::set_k_block, present masks, masked lane stores, anything in h/tron/tensor/k_vnni.hpp, tests of bit identity against store_row).
  G = generic sharing: would be needed to share ANY per-token store between the main thread and the idle helpers (k_store_window_t, k_store_shared, k_store_cut_units, the claim loop on next_unit, opened / finished counters, the join and the watchdog, worker_ix / n_workers plumbing, the TronCpp.hs helper-side emission, LoopyTronSpec, the three-thread test section, Note [Shared block save] text about the protocol).
  M = mixed or comments.
Report a table: file, L lines, G lines, M lines, with the decisive hunk names. Then state in one paragraph: if the G class were landed on main first (for main's row-major save_k and save_v), what of PR 3 would remain (the L class only?).` },
  { key: 'pr4-classify', prompt: `${COMMON}
Task: decide whether PR 4 contains any mechanism that would change behaviour or performance in a tron WITHOUT the VNNI K layout (i.e. main, where every K row is row-major and the FPGA staging gathers 4 whole lines per row).
Read cd ~/workspace/ai-runs/tron-split-pr4 && git diff b39765ec29 6b081187e1 (skip tests after a glance), the body 4959-v2.md, and the Notes [Row-major tail block] (h/tron/tensor/k_vnni.hpp) and [Row-major blocks under hardware attention] (h/tron/models/kv_cache.hpp).
Enumerate every mechanism: saved-row bits and converted bits, note_k_row_saved / note_k_block_saved, pending_k_blocks + convert_pending_k_blocks at the forward end (after wait_for_coop_gof), block_to_vnni / block_to_rows, row_major_row / k_row_if_row_major, k_forget_row, copy_storage_slot bit carry, the dense gate k_layout_dense, the dotter scoring of tail rows, the hardware-attention policy in save_k (cached_operation_uses_hw), the deb preset, and anything else. For each: (1) what it does, (2) what state main is already in with respect to it, (3) whether porting it alone to main could change any measured number (decode TPS, TTFT, FPGA-attention decode). Also look at the lazy-dotter probe (cd ~/workspace/ai-runs/tron-split-probe-pr4lazy && git diff 6b081187e1..ca6456b7dc or git log -3 and git show --stat; also the page ~/workspace/intel-AMX/PR3879/new-PRs/split-4424/pr4-lazy-dotter-20261013.html, grep its Short version): what construction does it defer, does that construction exist on main's row-major path too, and what did it recover (numbers with units from the page or issue body ~/workspace/intel-AMX/PR3879/new-PRs/split-4424/issue-pr4off-decode/body-20261014.md).
Conclude: list of PR 4 mechanisms with a use outside the VNNI layout (may be empty), with evidence.` },
  { key: 'decode-trace', prompt: `${COMMON}
Task: from main's trace data only (base-tp2 and base-tp4 lanes json and analysis.md in ~/workspace/intel-AMX/exec/results/vnnik-trace-20260914; python3 -I for scripts, write scripts under /tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/851b8402-d93e-4edb-b919-4c0fd806a57a/scratchpad/decode-trace/), describe one decode layer (window from Save K start of the layer to the next layer's Save K start) and one prefill layer as a wall-clock timeline:
- for each thread class (main, helpers, attention workers): busy fraction over the layer window, and the sequence and duration of its spans (Save K, Save V, Free scratchpads, kernel_* on helpers, Attention Ready / Pending / join on workers).
- the serial segments of the layer where the main thread works and the helpers are idle, with their length in us and share of the layer.
- the segments where NO thread class has a span (the FPGA-bound time, when the CPU waits for the linear layers), length and share.
- when the attention workers are busy, how many of them are busy (count over time), and whether the helpers run anything at the same time.
Give the numbers in a compact table per (tp2/tp4, prefill/decode). Then answer: in decode, is there any main-thread serial segment that helpers could take, and how long is it per layer and per step (36 layers)? In decode, what fraction of the step is attention on the workers, and are the helpers idle during that time? State what the trace cannot tell (e.g. why a worker is idle).` },
]

phase('Read')
const reads = await parallel(readers.map(r => () => agent(r.prompt, { label: `read:${r.key}`, phase: 'Read', schema: READ_SCHEMA })))
const readMap = {}
readers.forEach((r, i) => { readMap[r.key] = reads[i] })
log(`readers done: ${reads.filter(Boolean).length}/4`)

const CLAIMS = [
  { key: 'pr3-generic', claim: `PR 3 contains two separable techniques. The 16-token block save with the register transpose is layout-specific and has no counterpart on main (main's row-major store already writes whole lines). The sharing of the store with the idle main helpers (window protocol, work units, helper-side emission in the code generator) is generic and could be applied to main's row-major save_k and save_v in an independent PR. Expected TTFT gain on qwen3-4b 8 users prompt 1024: upper bound = Save K + Save V share of a prefill pass = 5.2 % at tp2 and 7.6 % at tp4 (trace 2026-09-14); realistic est. 4 % at tp2 and 6.5 % at tp4, scaled from PR 3's striping-only arm (858 us -> 175 us at tp2 with 8 threads, -> 110 us at tp4 with 9 threads; TTFT -125 ms at tp2 and -232 ms at tp4 for that arm, record exec/results/vnnik2-20260915).` },
  { key: 'pr4-none', claim: `PR 4 contains no technique that would help a tron without the VNNI K layout. Every mechanism (row bits, forward-end conversion, hardware-attention row-major policy, dotter over the tail rows, k_forget_row, bit carry on copies, deb preset) restores on the VNNI layout a state main already has. Its measured gains against its parent (FPGA-attention decode +2.5 % at tp2 and +12.1 % at tp4) are recoveries of the loss issue #4500 recorded, and on CPU attention PR 4 against its parent is inside the band. Porting any of it to main would change nothing measurable.` },
  { key: 'no-decode-gain', claim: `Sharing save_k / save_v with the helpers gives no decode gain on main. In a decode step main's Save K + Save V take 8 to 11 us per layer (1.2 to 4.3 % of the step), the attention workers run Ready sections during them, and the Pending sections wait on other work for about 110 us after Save V (trace 2026-09-14, analysis.md "gap after Save V"); PR 3's own sharing excludes passes of at most 16 items. The decode gains of the stack (+4.7 to +9.4 % TPS on CPU attention against main) come from PR 2's transpose-free AMX kernel, which needs the layout by construction.` },
]

const VERDICT = { type: 'object', properties: {
  refuted: { type: 'boolean' },
  confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  reasoning: { type: 'string', description: 'the strongest counter-evidence found, with file:line or record citations, or why none was found' },
  corrections: { type: 'array', items: { type: 'string' }, description: 'specific wording or number corrections to the claim, each with its source' },
}, required: ['refuted', 'confidence', 'reasoning', 'corrections'] }

const LENSES = [
  'code lens: find code in main or the PR trees that contradicts the claim',
  'data lens: find a measurement record under ~/workspace/intel-AMX/exec/results or the PR bodies that contradicts the claim or its numbers (check every number and unit)',
  'reasoning lens: find a flaw in the inference (e.g. an upper bound that is not on the critical path, a scaling that does not transfer, an excluded case)',
]

phase('Refute')
const refuted = await parallel(CLAIMS.map(c => () =>
  parallel(LENSES.map((lens, i) => () => agent(`${COMMON}
Reader findings so far (data, may contain errors):
--- main-helpers ---
${readMap['main-helpers'] ? readMap['main-helpers'].findings : 'n/a'}
--- pr3-classify ---
${readMap['pr3-classify'] ? readMap['pr3-classify'].findings : 'n/a'}
--- pr4-classify ---
${readMap['pr4-classify'] ? readMap['pr4-classify'].findings : 'n/a'}
--- decode-trace ---
${readMap['decode-trace'] ? readMap['decode-trace'].findings : 'n/a'}
---
Your task: try to REFUTE this claim through the ${lens}.
CLAIM: ${c.claim}
Default to refuted=true only if you found concrete counter-evidence; if you only find wording or number corrections, set refuted=false and list them in corrections. Cite file:line or record paths.`, { label: `refute:${c.key}:${i}`, phase: 'Refute', schema: VERDICT })))
    .then(vs => ({ key: c.key, claim: c.claim, votes: vs.filter(Boolean) }))
))

return { reads: readMap, refuted }