import json
U = {
 "file": "h/tron/models/model.hpp",
 "short": [
  "PR 4958 (tron pull request 4958, the third of four PRs that split PR 4424) changes save_k in model.hpp, the function that stores the K rows (the keys of one attention layer) of one minibatch into the KV cache.",
  "With the VNNI K layout of PR 4956 (the pair-interleaved layout the AMX tile multiply reads), a run of 2 to 16 consecutive tokens of one 16-token page block is now stored as one block (set_k_block: a register transpose, then whole 64-byte lines), a run of one token keeps the per-row scatter (set_k_row), and the store of a minibatch with more than 16 items is shared with the idle main helper threads through a window of work units (Note [Shared block save]).",
  "This page draws the data model, the call graph, the window protocol, the threads over one layer and the store decision once (section 1), then each of the eight logical changes of the file beside its diagram (section 2)."
 ],
 "base_intro": "Five diagrams carry the context that every change below refers to. B1 is the data model (the minibatch, the window batch::k_store_window_t, the page and the work unit), B2 the function model, B3 the sequencing model (one window, step by step), B4 the interaction model (threads over one layer, wall-clock lanes) and B5 the store decision (what one run of tokens becomes). The per-change diagrams in section 2 reuse their shapes and colours and say which base diagram they update.",
 "changes_intro": "A unit is one logical change: a data model and its constants, one function's new behaviour, one call path. Each unit shows the head code with its comments (added lines green, removed base lines red, head line numbers in the second column, base line numbers in the first) and, beside it, the diagram that updates a base diagram. Units are ordered by dependency: the design note (M0), the constants (M1), the sharing decision (M2), the unit cut (M3), the run store (M4), the window protocol with its watchdog (M5), the marks loop that lost the per-token store (M6) and the entry points (M7).",
 "trivial_intro": "Changes that alter no behaviour and need no picture.",
 "trivial_bullets": [
  "Blank separator lines between the new functions (head lines 3137, 3149, 3162, 3192, 3294: added blank lines) belong to no unit."
 ],
 "method": [
  "Facts in the diagrams come from the comments in the diff itself (Note [Shared block save], head lines 3075-3136, and the function comments), from batch::k_store_window_t in common.hpp (head lines 1193-1219), from page::set_k_block in kv_cache.hpp and store_block in h/tron/tensor/k_vnni.hpp, and from the generated-code change in ingest/src/TronCpp.hs of the same PR. Every line number was read from the head file b39765ec29. Facts about the next PR of the split (the row-major tail block, the saved-row bits, the deferred conversion) are named as future work and never drawn as present.",
  "The worked example (one shared window of 41 items with 3 workers, units [0,16) [16,32) [32,41), token 37 and dimension 70) is an illustration, not a measurement. The one measurement on this page (0.86 ms per layer, 105 ns per (token, KV head) row, with the VNNI K layout and the per-row store on main alone) is quoted from the comment of Note [Shared block save], which names its date and machine. The 80 us figure of B4 is quoted from the PR body of #4958 (Background) with that label."
 ],
 "base": [
  {"id": "model-b1", "short": "data model",
   "title": "Data model: the minibatch, the K store window, the page and the work unit",
   "intro": "A batch holds the items of one minibatch (token jobs), each at one page offset. The PR adds batch::k_store_window_t in common.hpp (the claim counter next_unit, the counters opened and finished, the unit table unit_start and the helpers' window counters helper_windows) and the constants of the store in model.hpp. Every arrow says how many. The worked example is one shared window of 41 items with 3 workers (main and 2 main helpers): units [0,16) [16,32) [32,41)."},
  {"id": "model-b2", "short": "function model",
   "title": "Function model: save_k, its helpers, and what they call in the page",
   "intro": "save_k (two overloads) calls save_k_impl. save_k_impl decides the sharing (k_store_shared), cuts the units (k_store_cut_units), stores the runs (store_k_block) and marks the tokens. store_k_block calls page::set_k_block (a run of 2 to 16 tokens), page::set_k_row (a run of one token) or page::k(...).set (a row-major slot). The generated plugins call save_k from run() (worker 0) and run_main_help (the helpers). Every cell says in one line what the function does."},
  {"id": "model-b3", "short": "sequencing model",
   "title": "Sequencing model: one shared save_k window, step by step",
   "intro": "The ordered steps of one window, each citing the line that does it. Main cuts the units, resets the counters and opens the window (release on opened). Each helper waits for its window number (acquire on opened). Every thread claims units with fetch_add on next_unit and stores them. Each helper increments finished (release). Main joins (acquire on finished) under a watchdog. Main marks the tokens, credits the GOFs and counts the downstream latches down."},
  {"id": "model-b4", "short": "interaction model",
   "title": "Interaction model: threads over one layer and the forward end (wall-clock lanes)",
   "intro": "One lane per thread: main, the two main helpers of the worked example, the attention workers, and the forward end. Solid blocks are work, dashed outlines are waiting. The critical path (main's serial part) is marked with a thick red frame. Durations are schematic. The order and the overlap are what the diagram shows. The two numbers quoted (0.86 ms per layer before, 80 us after) come from the comment of Note [Shared block save] and from the PR body."},
  {"id": "model-b5", "short": "store decision",
   "title": "Decision model: what one run of tokens becomes in the page",
   "intro": "For each run of consecutive items in one 16-token block of one page, three cases. A row-major slot stores one row per token and KV head through page::k(...).set. A VNNI slot stores a run of one token with set_k_row (the per-row scatter: 4 bytes into each of the token's 64 lines) and a run of 2 to 16 tokens with set_k_block (one block, the present mask naming the lanes: whole-line stores when the mask is full, masked line stores otherwise). The sharing of the store is a separate decision (k_store_shared), drawn at the top."}
 ],
 "units": [
  {"id": "m0", "title": "Note [Shared block save]: the design record of the K store window",
   "kind": "comment only", "ranges": [[3075, 3136]],
   "lead": [
    "Comment text only. It is the design record the code below follows, so it is listed first and shown in full.",
    "The problem (3077-3086): with the VNNI K layout and one set_k_row scatter per token on the main thread alone, the K store is the main thread's largest serial piece of work in a prefill layer. The measurement of 2026-09-14 on the test server delphi-3bda (qwen3-4b, 8 users, prompt 1024, 128 tokens of each user per pass) gave 0.86 ms per layer, 105 ns per (token, KV head) row. The attention workers' pending sections wait behind it.",
    "The two remedies (3087-3101): the block save (store_block, page::set_k_block: a run that fills part or all of one 16-token block is transposed in registers and written as whole 64-byte lines, chosen per run in store_k_block), and the sharing with the main helpers (the generated run_main_help calls save_k at the same statement position with the helper's worker_ix; every thread claims work units until none is left; n_workers == 1 never shares).",
    "The window protocol (3102-3128): both sides decide with k_store_shared; main cuts the items into units, zeroes next_unit and finished and increments opened (release); a helper's W-th call waits for opened >= W (acquire); every thread claims units with fetch_add on next_unit; a helper increments finished (release) when its claim loop ends; main returns only when finished == n_workers - 1 (acquire); the per-token completion marks and GOF credits stay on main after the join.",
    "Why the join cannot deadlock (3129-3136): main waited for every token's K channel before save_k, the channel phase cannot advance while main is inside save_k, and nothing blocks a helper between its K/Q rope kernel and its save_k call. A join that does not complete within about two minutes (k_join_timeout_s after the first clock read) aborts with the counters in the message."
   ],
   "base": "(set by the figure module)"},
  {"id": "m1", "title": "The constants of the store: the block size, the scatter run length and the join watchdog",
   "kind": "new", "ranges": [[3138, 3148]],
   "lead": [
    "k_store_block = k_vnni::BLOCK_TOKENS_16 (16 tokens): the size of one block save and the longest run. k_store_shared, k_store_cut_units and store_k_block share it.",
    "k_scatter_run_len = 1: a run of this length is stored row by row (set_k_row, the per-row scatter), not as a block. A run of 2 to 16 tokens takes set_k_block.",
    "k_join_clock_spins = 1048576 (2^20) and k_join_timeout_s = 120: the join watchdog of Note [Shared block save]. Main reads the clock once every k_join_clock_spins pause loops and aborts k_join_timeout_s seconds after the first clock read. A static_assert pins the spin count to a power of two, because the check masks with it."
   ],
   "base": "(set by the figure module)"},
  {"id": "m2", "title": "The sharing decision: k_store_shared",
   "kind": "new", "ranges": [[3150, 3161]],
   "lead": [
    "The answer is the same on main and on every helper. Four tests must all pass: a VNNI slot (k_vnni::layout_on on the head size, a compile-time test), more than one worker, at most helper_windows.size() = 128 workers, and more than k_store_block = 16 items in the minibatch.",
    "A decode step (one token per user, 8 items with 8 users) is not shared. The handwritten plugins and the unit tests (except the three-thread section of t_llama_unit) pass n_workers = 1 and never share."
   ],
   "base": "(set by the figure module)"},
  {"id": "m3", "title": "Cutting the minibatch into work units: k_store_cut_units",
   "kind": "new", "ranges": [[3163, 3191]],
   "lead": [
    "A unit is a run of consecutive items in one 16-token block of one page with the same token_jobs_do_kv value. A new unit starts at t == 0, at a change of kv, of pg (page_of) or of block (offset_in_page / k_store_block).",
    "Unit u is items[unit_start[u], unit_start[u + 1]) (the end is exclusive). The array unit_start has max_minibatch_size + 1 entries. The open window uses entries 0 .. n_units of it, and w.n_units is written last.",
    "Items without KV work (token_jobs_do_kv == 0) form units of their own (pg nullptr, block 0). A thread claims such a unit and store_k_block skips every item of it.",
    "TRON_ASSERT: n_items + 1 must fit the unit table (max_minibatch_size + 1 entries). Otherwise the process aborts.",
    "Only main calls this, before it opens the window (the release increment of opened publishes the table to the helpers)."
   ],
   "base": "(set by the figure module)"},
  {"id": "m4", "title": "store_k_block: a run of 2 to 16 tokens as one block, a run of one token as a scatter",
   "kind": "new", "ranges": [[3193, 3293]],
   "lead": [
    "Contract: stores the K rows (every KV head) of items[task_begin, task_end) into slot. Marks and credits are not touched here. save_k_impl does them after every store is done.",
    "Row-major slots (layout_on false): one row store per token and KV head through page::k(slot, kv_head, j).set, the old per-token loop moved here from the marks loop.",
    "VNNI slots: a run collects consecutive KV items of one block c of one page. An item without KV work is skipped and does not end the run. A page change, a block change or the same offset twice ends the run. The item that ended it starts the next run. A run also ends at 16 rows or at task_end.",
    "A run of one token (n == k_scatter_run_len) goes through page::set_k_row per KV head: the per-row scatter store_row, 4 bytes into each of the token's 64 lines.",
    "A run of 2 to 16 tokens goes through page::set_k_block per KV head with the present mask (bit t = the row of offset c * 16 + t is in the run): store_block transposes the rows in registers and writes whole 64-byte lines, masked to the present lanes when the block is partial. Any thread of a shared window may do this.",
    "A non-bf16 K buffer is converted to bf16 on the stack first (conv: 16 rows of head_size values, 4 KiB, 64-byte aligned). A bf16 buffer is read in place through k_source_row (per row) or through its row pointer (per block)."
   ],
   "base": "(set by the figure module)"},
  {"id": "m5", "title": "save_k_impl: the window protocol (open, claim, join) and its watchdog",
   "kind": "changed + new", "ranges": [[3295, 3315], [3323, 3368]],
   "lead": [
    "save_k_impl gains worker_ix and n_workers. TRON_ASSERT worker_ix < n_workers. Worker 0 is main. An unshared store is main's alone. A helper therefore returns at once when k_store_shared says no. n_items (head 3323) is a new local, used by the unshared store at 3367.",
    "Shared, main: k_store_cut_units fills unit_start and n_units, next_unit and finished are reset with relaxed stores, then opened.fetch_add(1, release) publishes them.",
    "Shared, helper: my_window = ++w.helper_windows[worker_ix] (the helper's own plain counter, one per worker_ix), then spin with _mm_pause until opened.load(acquire) >= my_window. So window W of a pass is the W-th shared save_k on both sides.",
    "Every thread: u = next_unit.fetch_add(1, acq_rel); stop when u >= n_units; else store_k_block(items[unit_start[u], unit_start[u + 1])).",
    "Helper end: finished.fetch_add(1, release) and return. Main end: spin until finished.load(acquire) >= n_helpers (= n_workers - 1).",
    "Watchdog: every k_join_clock_spins (2^20 = 1048576) pause loops main reads std::chrono::steady_clock. The first read sets t0. TRON_ASSERT checks now - t0 < k_join_timeout_s (120 s). The abort message carries finished of n_helpers and claimed of n_units.",
    "Unshared: main calls store_k_block over items[0, n_items) itself."
   ],
   "base": "(set by the figure module)"},
  {"id": "m6", "title": "The marks loop loses the per-token K store",
   "kind": "removed + context", "ranges": [[3369, 3385]],
   "lead": [
    "The 23 removed base lines (base 3095-3117) were the per-token K store inside the marks loop: for every KV item, for every KV head, set_k_row for a VNNI slot (with a bf16 conversion on the stack for other activation types) or page::k(...).set for a row-major slot, before the token's mark.",
    "At the head every K row of the minibatch is stored first (store_k_block, by any thread of the window, then main's join). The marks loop keeps mark_k_complete and the GOF credits (credit_gof_save) on main, in q_batch->items order, one token at a time. Then upstream_kvs_ready[slot].count_down() runs for every downstream minibatch.",
    "The base comment 'Update the page first so HW sees the latest K values.' moved to head 3324, reworded ('Update the pages first. That way HW sees the latest K values.')."
   ],
   "base": "(set by the figure module)"},
  {"id": "m7", "title": "The save_k entry points take a worker index and a worker count",
   "kind": "changed signature", "ranges": [[3388, 3413]],
   "lead": [
    "Both save_k overloads gain worker_ix = 0 and n_workers = 1 and pass them to save_k_impl. The defaults store every row on the calling thread (handwritten plugins, tests).",
    "The generated plugins pass worker 0 and n_workers from run() and the helper's worker_ix and n_workers from run_main_help (TronCpp.hs, the same statement position on both sides)."
   ],
   "base": "(set by the figure module)"}
 ],
 "trivial": [
  {"id": "t1", "title": "Includes for the join watchdog and _mm_pause", "ranges": [[10, 10], [15, 16]],
   "what": "The chrono and immintrin.h includes (the join watchdog reads std::chrono::steady_clock; the spin loops call _mm_pause), and one comment alignment change on the functional include."}
 ],
 "glossary": [
  ["_mm_pause", "A spin-wait hint (an instruction that slows a polling loop and saves power). k_join_clock_spins counts these loops between clock reads. [model.hpp:16, 3337, 3354]"],
  ["acquire / release / fetch_add", "In the window: opened is incremented with release by main and loaded with acquire by helpers. next_unit.fetch_add uses acq_rel. finished is incremented with release by a helper and loaded with acquire by main. See 'memory orders'. [model.hpp:3331-3336, 3342, 3348, 3353]"],
  ["AMX", "Intel Advanced Matrix Extensions, the tile instruction set of the CPU. The AMX kernel qk_vnni_128x4 of PR 4957 reads the VNNI plane as its B operand. [tensor/k_vnni.hpp:11-14]"],
  ["attention workers", "Pool workers that run the per-layer attention plan. Their pending sections wait behind save_k. When idle, they drain GOF staging work (help_drain_gof). [model.hpp:2329-2336; 3085]"],
  ["AVX-512", "The 512-bit vector instruction set of the CPU. store_block's register transpose and masked line stores use it, and so do the scatters of store_row. [tensor/k_vnni.hpp:14-15]"],
  ["bf16", "16-bit brain floating-point, the storage type of K rows. A non-bf16 K buffer is converted to bf16 on the stack before the store. [the conversion at model.hpp:3226-3229]"],
  ["block / 16-token block / k_store_block / BLOCK_TOKENS_16", "The unit of the VNNI layout and of the shared store: 16 consecutive page offsets. A 64-byte line holds one dimension pair of 16 tokens. [model.hpp:3139; tensor/k_vnni.hpp:65]"],
  ["cache_line_size / cache line", "The unit of memory the CPU caches move (64 bytes). The window keeps the claim counter and the polled counter on separate lines. [common.hpp:1200-1204]"],
  ["channel / K channel", "A phase-tracked buffer whose readiness latches keep producers and consumers in step. Main waits for every token's K channel before save_k, and the channel phase cannot advance while main is inside save_k. [model.hpp:3129-3131]"],
  ["conv", "The stack buffer of store_k_block: 16 rows of head_size bf16 values (4 KiB, 64-byte aligned) that hold the converted rows of a non-bf16 K buffer. [model.hpp:3226-3229]"],
  ["critical path", "The serial work on the main thread that no other thread shortens (the thick red frame of B3, B4, M5 and M6)."],
  ["dotter", "The AVX software reader for row-major K: one dot product per (query head, token) through a typed row view. Not changed by this PR. [kv_cache.hpp:727-736]"],
  ["forward pass / pass / forward end", "One forward() call that runs every layer for this step's tokens. The forward end is the part of run_forward after the plugin's run() returned: wait_for_coop_gof, logits. [model.hpp:1709, 1780, 1836-1851]"],
  ["FPGA", "Field-programmable gate array, the accelerator card that scores hardware attention and receives the GOFs by DMA (direct memory access). [kv_cache.hpp:737-741]"],
  ["generated plugin / handwritten plugin", "Generated plugins (the output of ingest/src/TronCpp.hs) call save_k from run() with worker 0 and from run_main_help with the helper's worker_ix. Handwritten plugins and the unit tests (except the three-thread section of t_llama_unit) use the defaults worker_ix = 0, n_workers = 1. [model.hpp:3092-3101]"],
  ["GOF", "A group of 4 contiguous tokens whose K/V are shipped to the FPGA together. credit_gof_save credits one K or V save against the token's GOF. [model.hpp:3480-3486]"],
  ["grain", "A group of at most 8 tokens (minibatch_grain_size), the unit the batcher merges into minibatches. A partner job moved to the end of a grain can make a block's items non-consecutive. [common.hpp:317; 1207-1211]"],
  ["hardware attention / has_hardware_slot", "Hardware attention = attention scored on the FPGA. has_hardware_slot is a local of save_k_impl: true when the geometry is the hardware geometry and the operation is a hardware candidate. Only then does the marks loop credit the GOF (credit_gof_save). [model.hpp:3320-3322, 3379-3381]"],
  ["helper_windows", "std::array<uint32_t, max_shared_workers>: the windows a helper has entered, by worker_ix (the helper's own slot). Its size (128) bounds the worker count of a shared store. [common.hpp:1216-1218]"],
  ["k_source_row / const_k_row_view", "k_source_row builds the read-only typed row view (const_k_row_view) that page::set_k_row takes. A row that is a bf16 K buffer row keeps the buffer's alignment and DMA flags; a plain bf16 pointer (the conv stack row) gets the default flags. [tensor/k_vnni.hpp:205-225]"],
  ["kill switch / TRON_AMX_DISABLE", "Runtime switch that disables the AMX kernels. It leaves both store paths untouched. [kv_cache.hpp:722-724]"],
  ["KV head", "One key/value head. A token has geometry.kv.n_kv_heads of them, and each K row holds geometry.kv.head_size bf16 values (128 for the VNNI layout). [the loops at model.hpp:3218, 3263, 3277]"],
  ["latch / upstream_kvs_ready / downstream_minibatches", "latch_ref wraps an atomic counter with wait() and count_down(). downstream_minibatches is the producer side (whom to tick). upstream_kvs_ready is the consumer latch (how many producers are still pending). [common.hpp:1179, 1188; Note at common.hpp:992]"],
  ["main helpers / worker_ix / n_workers / run_main_help", "Helper threads of the main thread. worker_ix 0 is main, 1 .. n_workers - 1 are helpers. run_main_help(q_batches, worker_ix, n_workers) is the generated method the helpers run. run() launches it once per main helper with worker index 1 + i, and n_workers = 1 + n_main_helpers. [TronCpp.hs:1362-1364, 1392; model.hpp:3095-3097]"],
  ["mark_k_complete / credit_gof_save", "The per-token completion marks and GOF credits that stay on main after the join, in q_batch->items order. mark_k_complete counts the (offset, slot) save and returns true when K and V are both in. [kv_cache.hpp:2236-2240; model.hpp:3480]"],
  ["max_minibatch_size / max_shared_workers", "Table sizes of k_store_window_t: unit_start[max_minibatch_size + 1], helper_windows[128]. A pass with more than 128 workers is not shared. [common.hpp:1197-1199, 1215, 1218]"],
  ["memory orders (relaxed, acquire, release, acq_rel)", "The C++ std::memory_order values. A release write publishes every earlier write of its thread to a thread whose acquire read sees it. acq_rel does both. relaxed orders nothing beyond the atomic itself. fetch_add is an atomic read-modify-write that takes one of these orders."],
  ["minibatch / batch / q_batch / items", "struct batch is one minibatch. q_batch->items is its token jobs (token_job_id) in order. save_k's loops and the unit table index items by position. [common.hpp:1019, 1111]"],
  ["Note [name]", "A named comment block in the tron source. Other comments refer to it by this name."],
  ["page / page_of / offset_in_page", "A page holds 64 tokens of K and V per slot and KV head. page_of(tok) returns the live token's page. offset_in_page(tok) returns the token's offset in the page (0 .. 63). [model.hpp:1771-1773; kv_cache.hpp:1972]"],
  ["plane / panel / pair row", "Plane = the K of one KV head of one page (16 KiB). Panel = the 16 pair rows of one 32-dimension step for one 16-token block (1 KiB, one AMX B tile). Pair row = one 64-byte line = one dimension pair of 16 tokens. The block save writes each pair row with one line store. [tensor/k_vnni.hpp:21-33, 72-75]"],
  ["prefill / decode", "Prefill = prompt processing (many tokens per user per pass, 128 in the Note's measurement). Decode = one generated token per user per step. Sharing depends on the minibatch's item count (more than 16), the worker count and the layout, not on the pass kind. [model.hpp:3103-3106]"],
  ["present / __mmask16 / FULL_BLOCK_0XFFFF", "The 16-bit mask of store_block and set_k_block: bit t set = the row of offset c * 16 + t is in the run (lane t of every pair row is written). FULL_BLOCK_0XFFFF = every lane present: whole-line stores. [tensor/k_vnni.hpp:76-77, 326-332; kv_cache.hpp:2078-2084]"],
  ["qk_group / qk_vnni_128x4", "The AVX-512 score reader of the VNNI plane (PR 4956) and the AMX kernel for a dense VNNI page (PR 4957). Readers of the plane, not changed by this PR. [kv_cache.hpp:725-736]"],
  ["rope / roped / WK roped", "rope = rotary position embedding, the per-position rotation applied to the Q and K rows before the store (the K/Q rope kernel of the Note). 'WK roped' is tron's record label for the K rows after rope (log_intermediate). [model.hpp:3133; 3372]"],
  ["row_of", "The lambda of store_k_block that gives the K row of (token job ix, KV head): a slice of ks[ix] of head_size values. [model.hpp:3207-3210]"],
  ["save_k (two overloads)", "Overload 1 takes the operation as the template argument operation_ix (the generated plugins); overload 2 takes a runtime attention_operation_descriptor (handwritten plugins, tests). Both forward worker_ix and n_workers to save_k_impl. [model.hpp:3394-3413]"],
  ["sentinel", "The extra entry unit_start[n_units] = n_items that ends the last unit. [model.hpp:3189]"],
  ["set_k_block / set_k_row / store_block / store_row", "The two K store entry points of the page used by store_k_block. set_k_block takes 16 native row pointers and the present mask and calls store_block (the register transpose and whole-line stores). set_k_row takes one const_k_row_view and calls store_row (4 scatters, 4 bytes into each of the token's 64 lines). [kv_cache.hpp:2061-2096; tensor/k_vnni.hpp:290-368]"],
  ["slot / kv_slot_id", "A kv_slot_id selects persistent KV storage. One attention operation writes one slot (binding.kv_slot). [kv_cache.hpp:186; model.hpp:3319]"],
  ["spin-wait", "A loop that re-reads a variable until it changes, instead of sleeping."],
  ["std::chrono::steady_clock", "The monotonic C++ clock the join watchdog reads once every k_join_clock_spins pause loops. [model.hpp:3352, 3356]"],
  ["token lane", "Token t of a block owns lane t (column t % 16) of every pair row of its block's four panels. The present mask selects which lanes a store writes. [tensor/k_vnni.hpp:326-332]"],
  ["token_id / token_job_id / token_jobs", "token_id = the token's global tree position. token_job_id = its position in this forward's job list. token_jobs[ix] gives the job's token_id. [common.hpp:147, 178; model.hpp:1157]"],
  ["token_jobs_do_kv", "indexed_span<token_job_id, const uint8_t>: 1 when the job needs KV computation this forward (its K and V are saved), 0 otherwise. [model.hpp:1158, 1752]"],
  ["TRACE_EVENT", "A named time span recorded in the run's perfetto trace (perfetto = the tracing library). save_k_impl records 'Save K'. [model.hpp:3317]"],
  ["transpose_16x16_epi32", "The in-place transpose of 16 registers of 16 32-bit lanes that store_block runs per dimension step (4 stages of shuffles). [tensor/k_vnni.hpp:257-287]"],
  ["tron", "The inference program under test (the positron-ai/tron repository). Its C++ code lives in namespace tron. runtron is its command-line tool and rinzler the production server."],
  ["TRON_ASSERT", "Abort-on-false assertion macro with a fmt message. It is not disabled in release builds."],
  ["TRON_K_VNNI / k_vnni::layout_on", "Build-time gate of the VNNI K layout. It is a property of the storage geometry (true for 128-dimension heads with the option on), not of the query type or AMX availability. [tensor/k_vnni.hpp:94-103]"],
  ["VNNI", "The pair-interleaved K layout: the two values of a dimension pair of one token are adjacent, and one 64-byte row holds one dimension pair for 16 consecutive tokens. It is the AMX tile-multiply B-operand layout. [tensor/k_vnni.hpp:15-19]"],
  ["wait_for_coop_gof / help_drain_gof", "The cooperative GOF dispatch: idle attention workers stage and submit complete GOFs (help_drain_gof); main drains the rest at the forward end (wait_for_coop_gof). Not changed by this PR. [model.hpp:3500, 3513]"],
  ["window / k_store_window / opened / finished", "The per-minibatch protocol state of the shared K store. opened counts windows opened in the pass. finished counts helpers done with the open window. Window W of a pass is the W-th shared save_k on both sides. [common.hpp:1193-1219; model.hpp:3113-3117]"],
  ["work unit / unit_start / n_units / next_unit", "The claimable piece of a shared K store. Unit u = items[unit_start[u], unit_start[u + 1]). unit_start has max_minibatch_size + 1 entries. n_units counts the units of the open window. next_unit is the claim counter on its own cache line. [common.hpp:1200-1215]"]
 ]
}
json.dump(U, open("/home/jhan/workspace/intel-AMX/exec/pr4958-diagrams-20261016/units_model.json", "w"), indent=1)
print("ok", len(U["units"]), len(U["glossary"]))
