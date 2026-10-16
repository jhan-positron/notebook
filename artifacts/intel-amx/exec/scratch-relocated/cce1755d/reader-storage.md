# Reader report: the storage side of the T patch (PR-4)

Paths written as `h/...` or `t/...` are relative to the probe worktree ~/workspace/ai-runs/tron-split-probe-pr4 (the PR-3 head 80bce9a08d with the T and B patches applied, staged, not committed). Paths written as `ref/...` are relative to ~/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material/. Line numbers of the T patch are lines of ref/T-4737-merge.diff. Nothing was modified; no git command that changes state was run; delphi-3bda was not used.

## Short version

The T patch makes a 16-token block of the packed K plane hold plain token rows (row-major) until all 16 of its rows are saved, and converts the block to the VNNI layout in place at the end of the forward pass. The page records two bit sets per storage slot for that: the saved rows (k_rows_saved_, 64 bits) and the converted blocks (k_vnni_blocks_, 4 bits), and every reader and writer of a row takes the block's layout from the converted-block bit. Under hardware attention (the FPGA scores the operation) save_k records no row bits and queues no conversion, so those blocks stay row-major.

## Words used here

The vocabulary of PR3-handoff.md "Words used here" applies (page, plane, panel, token block, slot, VNNI layout, store_row, store_block, save_k, main helpers, window, kill switch, FPGA, hardware attention). New terms of this report:

- Row-major block (also "row-major tail block"): a 16-token block whose rows are stored as 16 contiguous 256-byte rows inside the block's own 4 panels, not as VNNI columns [h/tron/tensor/k_vnni.hpp:445-456].
- Converted block (also "VNNI block"): a block whose 4 KiB hold the VNNI layout; its bit in k_vnni_blocks_ is set [h/tron/models/kv_cache.hpp:2620-2624].
- Saved-row bit: bit `offset` of k_rows_saved_, set when the K row of that page offset has been stored for the slot [h/tron/models/kv_cache.hpp:2609-2619].
- Storage slot: one physical K/V storage region of a page. Logical slot: the slot a caller names (kv_slot_id). The two differ only under the EAGLE view.
- EAGLE: the draft-model speculation feature; a book that supports it carries one extra physical storage slot (the EAGLE storage, at index logical_slot_count()) [h/tron/models/kv_cache.hpp:1092-1095]. Storage view: the book setting that makes logical slot 0 address the EAGLE storage (set_storage_view / reset_storage_view) [h/tron/models/kv_cache.hpp:1071-1090].
- Forward end: the point in model::forward after the plugin's run() returned and wait_for_coop_gof() returned [h/tron/models/model.hpp:1836-1847].
- GOF: a group of four consecutive tokens whose K/V rows the staging (gof::populate) copies into a DMA buffer for the FPGA [h/tron/models/kv_cache.hpp:736-740]. Cooperative GOF drain: idle attention workers run queued GOF staging tasks (help_drain_gof) and main runs the rest at the forward end (wait_for_coop_gof) [h/tron/models/model.hpp:3563-3595, h/tron/models/self_attention.hpp:761].
- Engagement point: the sequence position (hw_attn_engagement_point, 127 by default) from which the FPGA holds the K/V of every DMA-complete GOF [h/tron/models/kv_cache.hpp:735-737].
- Dotter: the row-major per-token dot-product loop of self_attention.hpp (tron::dotter).
- Minibatch: one group of a pass's items; `q_batch->items` lists its token jobs.
- Catch2 terms (REQUIRE, SECTION, CAPTURE): as in PR3-handoff.md.

## 1. h/tron/tensor/k_vnni.hpp (the layout operations; T adds +115/-4 lines, the probe's staged diff is +115/-5)

What the file gains, in plain words:

- Four constants and helpers in namespace k_vnni. PANEL_ROWS_4 = 4: a row-major block keeps 4 token rows of 256 bytes in each of its 4 panels (one panel is 1 KiB) [h/tron/tensor/k_vnni.hpp:91-93]. BLOCKS_PER_PAGE_MASK_0XF = 0xf: the mask with every one of a page's 4 block bits set [:94-96]. block_bit(c) = 1 << c, the bit of token block c in a block mask [:97-100]. offset_bit(offset) = 1 << offset, the bit of one page offset in a 64-bit row mask [:101-105]. Two static_asserts tie the names to the values [:107-113].
- Note [Row-major tail block] (title at [:445], tildes at [:446], text to [:465]). It states: a block holds the VNNI layout only once all 16 of its K rows are saved; until then token t of block c owns 256 contiguous bytes at row_major_row(); those bytes are the block's own 4 panels, panel (t / 4, c) holding the rows of tokens 4 (t / 4) .. 4 (t / 4) + 3; so both layouts occupy the same 4 KiB and touch no other block. It gives the why: in decode every step saves one token per user; the VNNI scatter of one row writes 4 bytes into each of 64 lines, the row-major store writes 4 whole lines, and the readers of an incomplete block (the dotter and the FPGA staging gather) read 4 lines per token instead of 64. It names when the conversion runs (the forward end of the pass that saved the 16th row, or at once for a whole-block save) and says the layout of a block is recorded by the page, not by the plane [:456-465].
- row_major_row(plane, token): returns a typed row view (k_row_view or const_k_row_view, by the plane's constness) of the token's 128 contiguous bf16 values at `plane + ((t / 4) * 4 + c) * 512 + (t % 4) * Cols` elements, where c = token / 16 and t = token % 16 [:467-480]. The view does not say whether the block is row-major; the caller knows that from the page's state [:467-470].
- store_row_major(dst, token, src): one memcpy of Cols * 2 bytes (256 bytes for 128 dimensions) into row_major_row(dst, token) [:482-490]. load_row_major(src, token, dst): the inverse memcpy [:492-500].
- block_to_vnni(plane, c): copies the block's 16 row-major rows to a 64-byte-aligned stack array with load_row_major, then calls store_block(plane, c, FULL_BLOCK_0XFFFF, row_ptrs) [:502-517]. The stack copy is needed because store_block writes panel (s, c) while the rows of tokens 4 s .. 4 s + 3 still live there [:502-504]. Bit identity with store_row: store_block with a full mask is already bit-identical to store_row per token (the PR-3 block-save case), so block_to_vnni is bit-identical to 16 store_row calls; the tail-block test checks that directly against store_row [t/t_k_vnni_layout.cpp:308-319].
- block_to_rows(plane, c): the inverse; load_row of each of the 16 tokens into the stack array (the VNNI gather), then store_row_major of each [:519-532].
- store_block itself is unchanged by T. It keeps its `__mmask16 present` parameter and its masked-store branch [:401-428]. Its callers in the probe are page::set_k_block with FULL_BLOCK_0XFFFF [h/tron/models/kv_cache.hpp:2284-2285], block_to_vnni with FULL_BLOCK_0XFFFF [h/tron/tensor/k_vnni.hpp:516] and the block-save test with arbitrary masks [t/t_k_vnni_layout.cpp:261]. So the masked branch of store_block is reachable from the test only. The T patch does not remove it.
- The file header comment names the conversion operations and keeps the PR-2 sentence about the AMX QK kernel (section 9) [:1-12].

## 2. h/tron/models/kv_cache.hpp (the page state and the accessors; T adds +493/-52, the probe's staged diff is +496/-56)

### 2.1 The two bit sets

- k_rows_saved_: `std::array<std::atomic<uint64_t>, n_slots + 1>`, one bit per page offset (64) per storage slot; entry n_slots is the EAGLE storage [h/tron/models/kv_cache.hpp:2609-2619]. k_vnni_blocks_: `std::array<std::atomic<uint8_t>, n_slots + 1>`, one bit per 16-token block (4) per storage slot [:2620-2624]. EAGLE_STORAGE_SLOTS_1 = 1 is the extra entry [:2493-2494].
- Invariant stated in the comments: a set block bit implies the block's 16 row bits; a block with 16 row bits set and no block bit is complete and waits for its conversion [:2611-2613, :2622]. The bits exist for every slot; only a VNNI slot's readers and writers take their layout from them [:2486-2491].
- k_state_ix(slot): the state entry of a logical slot: n_slots when the EAGLE view is active and slot.i == 0, else slot.i [:2501-2507]. It uses book::eagle_view_active(), a new book method that reads storage_view_offset_.i != 0 [:1084-1089].
- k_block_bits(c): the 16 row bits of block c, `FULL_BLOCK_0XFFFF << (c * 16)`; a static_assert ties page_size to 64 [:2509-2513]. k_block_is_vnni(state_ix, offset): whether the block of that offset has its bit set (acquire load) [:2515-2520].
- The page move constructor copies both bit sets with the other counters (std::atomic is not movable) [:1970-1975].

### 2.2 note_k_row_saved (return value, callers)

- Signature: `template <kv_geometry geometry> bool note_k_row_saved(kv_slot_id slot, size_t offset)` [:2167-2169], plus an overload without the template argument for uniform-geometry books that forwards the primary geometry [:2187-2192].
- For a row-major geometry it returns BLOCK_COMPLETED_FALSE (= false) and keeps no bit [:2171-2174, :2495-2496].
- For a VNNI geometry: it sets the row's bit with fetch_or (skipped when a relaxed load shows the bit already set) and returns true exactly when the row's block now has all 16 row bits set AND the block's converted bit is clear [:2175-2184].
- Meaning of the return: "the caller must queue this block for conversion". A row saved again into a complete, not yet converted block returns true again (the conversion is idempotent); a row of a converted block returns false, because set_k_row wrote it into the VNNI column [:2159-2166].
- Callers: save_k_impl on the main thread after the join, for every KV-writing item of the minibatch, only when the operation is not hardware-scored [h/tron/models/model.hpp:3425-3436]; the tests: t/t_k_vnni_layout.cpp:635 (the save_row_state helper), t/t_llama_unit.cpp:2544 and :4045, t/t_amx_dispatch_dtype.cpp:135. No helper thread calls it.

### 2.3 note_k_block_saved

- `void note_k_block_saved(kv_slot_id slot, size_t c)`: sets the block's 16 row bits (fetch_or, acq_rel) and then the block bit (fetch_or, release) [:2194-2202]. It records that block c was stored whole in the VNNI layout by set_k_block.
- Caller: store_k_block, once per block after the set_k_block of the last KV head [h/tron/models/model.hpp:3326-3339]. Any thread of a shared window may run it (every row of the block belongs to that one run) [h/tron/models/kv_cache.hpp:705-711]. The order "every head first, then the bits" matters because the bits are per slot, not per KV head: a reader must not see the block bit before every head holds the layout [:707-709].

### 2.4 k_storage_ref, k_storage_of and the storage view

- `struct k_storage_ref { kv_storage_offset offset; size_t state_ix; }`: a physical storage slot and the index of its K layout state entry, passed as one argument [:2139-2150].
- k_storage_of(slot): resolves a logical slot under the current view: the pair (eagle_storage_offset(), n_slots) when k_state_ix says the EAGLE entry, else (kv_storage_offset(slot.i), slot.i) [:2151-2157].
- What a storage view change is: book::set_storage_view(offset) sets storage_view_offset_ so that logical slot 0 addresses the EAGLE physical slot; reset_storage_view() restores offset 0 [:1071-1082]. The comment says why the pair is taken at the save: the deferred conversion list of save_k keeps the resolved pair, so that a view change between the save and the forward end cannot redirect the conversion [:2142-2146]. copy_from builds the pair from the physical slot, because a page copy moves every physical slot [:2141-2142].
- The EAGLE view test: rows recorded under the view go to the extra state entry and must not appear in the primary slot's state [t/t_k_vnni_layout.cpp:796-870].

### 2.5 k_block_to_vnni and k_block_to_vnni_at

- k_block_to_vnni(slot, c) forwards to k_block_to_vnni_at(k_storage_of(slot), c) [:2203-2213].
- k_block_to_vnni_at(storage, c): returns CONVERTED_FALSE when the block's 16 row bits are not all set or its block bit is already set; otherwise it calls block_to_vnni on every KV head's plane of that storage slot (through k_with_storage_geometry, which runs the lambda with the slot's declared geometry or the primary geometry for the EAGLE storage [:2522-2535]), then sets the block bit (release) and returns CONVERTED_TRUE [:2214-2238]. A row-major geometry never converts (the `if constexpr` leaves `converted` false) [:2228-2234].
- Rule stated in the comment: main thread only, at a point where no reader of the block runs (the forward end) [:2207-2209].
- Callers: convert_pending_k_blocks for the `_at` form [h/tron/models/model.hpp:3180]; the tests for the slot form [t/t_k_vnni_layout.cpp:636, t/t_llama_unit.cpp:2545, t/t_amx_dispatch_dtype.cpp:136].

### 2.6 set_k_row, get_k_row, set_k_block

- set_k_row: for a VNNI geometry it now branches on k_block_is_vnni(k_state_ix(slot), i_page): store_row into the VNNI column when the block is converted, store_row_major otherwise [:2249-2262]. The row's saved bit is the caller's job (note_k_row_saved) [:2244-2245].
- get_k_row: the same branch with load_row / load_row_major [:2293-2306].
- set_k_block: the `__mmask16 present` parameter is removed. The signature is now (slot, kv_head, c, rows) and the body calls store_block with k_vnni::FULL_BLOCK_0XFFFF [:2276-2290]. The comment now says "K rows of the 16 tokens of one 16-token block, stored at once in the VNNI layout" and "the caller records the block with note_k_block_saved after the last KV head" [:2266-2274]. In the T patch this is the hunk at ref/T-4737-merge.diff:443-454.
- k_packed's comment now says that only the blocks named by k_vnni_blocks hold the VNNI layout and that the others hold row-major rows read through row_major_row [:2115-2117].
- k_vnni_blocks(slot): the public read of the converted-block byte for the slot (acquire) [:2129-2137]. Readers: the dense AMX gate k_layout_dense in self_attention.hpp [h/tron/models/self_attention.hpp:1924-1931] and the software loop's per-token layout choice [:2021-2024]; the tests.

### 2.7 k_row_if_row_major (the FPGA staging reader)

- `k_row_view<head_size> k_row_if_row_major(slot, kv_head, i_page)`: returns an invalid view (data == nullptr) when the block is converted, else row_major_row of the plane, in place, with TRON(this_lifetimebound) [:2333-2351]. valid() is `data != nullptr` [h/tron/tensor/view.hpp:56-59].
- The only production caller is full.hpp's k_head_fn (section 4). The rule in the comment: the view is valid as long as no writer touches the block, the same rule as get_k_row's read [:2333-2337].

### 2.8 k_forget_row and clear_kv_complete_at

- clear_kv_complete_at(offset) (a new token takes a page offset) resets the kv_saves_ counters of that offset and now calls k_forget_row(offset) [:2472-2479].
- k_forget_row(offset): for every storage slot (logical slots, and the EAGLE entry only when the book has EAGLE storage) it drops the saved-row bits of the offset and of every offset above it, and the converted-block bits of the offset's block and every block above it [:2544-2588]. Before dropping the bits, when the offset's block keeps rows below the offset (offset % 16 != 0), the block was converted, and the storage is readable (k_storage_readable: no private KV restore in flight and the slot's arena allocated [:2537-2543]), it converts that block back to row-major with block_to_rows on every KV head, so the kept rows stay readable [:2572-2583]. Blocks above hold no live row: their bits are dropped and their bytes are left alone [:2548-2551]. A fast path skips a slot whose bits at or above the offset are all clear (the common decode append: two loads instead of two locked read-modify-writes) [:2566-2571].
- The rule stated: called with the token tree locked, between forward passes; no reader runs meanwhile [:2551-2553]. The Note adds: when the book's storage is not readable only the bits change, because the bytes are not valid anyway [:716-718].
- Tests: the page-state case forgets offsets 3, 18, 16 and 3 again and checks rows, bits and the bytes of an untouched block above [t/t_k_vnni_layout.cpp:716-794]; the two-slot case checks that only the slot whose block was converted converts back [:872-908].

### 2.9 Copy semantics (how the layout state travels with the rows)

- copy_storage_slot now takes a k_storage_ref (offset + state index) instead of a bare storage offset [:2690-2697]. copy_from builds the pair for every active logical slot (kv_storage_offset(slot), slot) and for the EAGLE storage (eagle_storage_offset(), n_slots) [:2789-2805]. book::append (defrag of tree-shaped speculation) is the caller of copy_from [:1362-1391].
- Whole-page copy (src_begin == 0, dst_begin == 0, count == page_size): one owner assignment of the plane (dst_block.k = src_block.k) and the destination's block bits become the source's [:2733-2735]. The saved-row bits of the whole range are replaced by the source's (the general formula with range = all ones) [:2714-2721].
- Every other range (token append): the bits are computed once per slot before the head loop: new_saved = destination bits outside the range plus the source bits shifted into it [:2714-2721]. Per KV head: every destination block the range touches that is converted is turned row-major first (block_to_rows) and its block bit cleared [:2738-2747]; each token is copied row-major: load_row from a converted source block into the destination's row-major row, or a store_row_major from the source's row-major row [:2748-2757]; then every touched destination block whose 16 row bits are set in new_saved is converted (block_to_vnni) and its bit set [:2758-2763]. After the last KV head both bit sets are stored with release [:2780-2783].
- The test covers the three forms: token append into a partly filled page (5 old rows, 40 new rows; blocks 0 and 1 end converted), append into a converted destination block (the block goes back to row-major for the copy and returns to VNNI), and the whole-page copy [t/t_k_vnni_layout.cpp:910-1031].

### 2.10 Private helpers and constants

k_with_storage_geometry [:2522-2535], k_storage_readable [:2537-2543], BLOCK_COMPLETED_FALSE [:2496], CONVERTED_FALSE / CONVERTED_TRUE [:2497-2499], EAGLE_STORAGE_SLOTS_1 [:2494]. These are private to page.

## 3. h/tron/models/model.hpp (the save_k side; +79/-12 in both the T patch and the probe)

### 3.1 The pending-block queue

- `struct pending_k_block { page* pg; typename page::k_storage_ref storage; uint32_t block; }` and `std::vector<pending_k_block> pending_k_blocks_` are members of model state [h/tron/models/model.hpp:3158-3172].
- convert_pending_k_blocks(): returns at once when the vector is empty; otherwise opens a trace event "convert_k_blocks" with the count, calls `b.pg->k_block_to_vnni_at(b.storage, b.block)` for each entry, and clears the vector [:3174-3183].
- Who fills it: save_k_impl on main, after the join of the shared window (or after the unshared store), for each KV-writing item whose note_k_row_saved returned true, with the storage reference resolved at that moment (pg.k_storage_of(slot)) [:3419-3437].
- Where it runs: in forward(), right after wait_for_coop_gof() and before the logit delivery is launched [:1838-1847]. plugin_state.run(q_batches) at [:1836] has joined the plugin's workers by then.
- Why there and not in save_k (the Note's reasoning [h/tron/models/kv_cache.hpp:687-705]): a block may be split across two minibatches of one pass (grains of 8 tokens); the cooperative GOF staging gather of the earlier minibatch's tokens (help_drain_gof on the attention workers, wait_for_coop_gof on main) reads the block's rows row-major while the later minibatch saves the block's last rows. The attention workers themselves are not that reader: a pending page is read only after every minibatch that writes it counted its latch down. The forward end, after wait_for_coop_gof, is the first point where no reader of this pass is left. The second reason, in the comment of pending_k_blocks_: the storage reference is taken at the save, so a storage view change cannot redirect the conversion [h/tron/models/model.hpp:3158-3166].

### 3.2 store_k_block's new branch rule

- The run loop is unchanged: consecutive KV-writing items of one page and one block, no offset twice, at most 16 [:3283-3302]. `present` is still built as a __mmask16 for the run [:3288-3298].
- New rule: `if (n < k_store_block)` (any run shorter than 16) stores row by row with set_k_row, which itself picks store_row_major or the VNNI column [:3303-3321]. The else branch (n == 16) asserts `present == FULL_BLOCK_0XFFFF` ("a run of 16 tokens must cover its block"), calls set_k_block per KV head with the 4-argument signature, then note_k_block_saved(slot, c) once [:3322-3339].
- Removed: `k_scatter_run_len` (0 occurrences in model.hpp and kv_cache.hpp at the probe) and the `n == k_scatter_run_len` branch (T patch hunk ref/T-4737-merge.diff:852-862 and :885-895); the `present` argument of set_k_block [:874-883]. The masked partial-block store of PR-3 (a run of 2 to 15 tokens through store_block's masked branch) is therefore no longer reachable from save_k.
- The store_k_block comment: "consecutive items that fill one whole 16-token block of one page are stored as one VNNI block (set_k_block). A shorter run is stored row by row (set_k_row) into the block's row-major form. ... Marks, saved-row bits of partial runs and credits are not touched here. save_k_impl does them after every store is done." [:3236-3242].
- Note [Shared block save] item 1 is reworded to the same effect: a run that fills one whole block is transposed; a shorter run is stored row by row into the block's row-major form, also whole lines; a block completed that way is queued after the join and converted at the forward end unless the hardware attention scores the operation's K [:3097-3108].

### 3.3 The hardware-attention policy

- In save_k_impl, after the store and before the mark loop: `if (!cached_operation_uses_hw(binding.operation))` guards the whole row-recording loop [:3419-3437]. cached_operation_uses_hw(operation) reads attention_operation_uses_hw[operation.i] != 0, decided once per model at configure time [:1530-1533].
- Effect: for a hardware-scored operation no row bit is set and no block is queued; a block that decode completes there stays row-major forever (a page copy does not convert it either, since the bits are clear) [h/tron/models/kv_cache.hpp:731-736]. Whole-block saves (prefill) still write VNNI and set their bits through note_k_block_saved, which the policy does not guard [h/tron/models/model.hpp:3339; h/tron/models/kv_cache.hpp:750-753].
- Tests: the save_k case of t_llama_unit has two sections for the policy: "hardware attention scores the operation: the completed block stays row-major, the whole-block save is still VNNI" (sets attention_operation_uses_hw for the saving operation; expects block 3 of page 0 VNNI and block 0 not converted, also after convert_pending_k_blocks) and "hardware attention scores another operation: this one still converts" [t/t_llama_unit.cpp:4077-4116, check_blocks at :4049-4060].

## 4. h/tron/scheduler/full.hpp (+8/-2)

- In the page_info builder of the FPGA staging, the k_head_fn callback for a VNNI geometry first calls `pg_ptr->template k_row_if_row_major<hw_kv>(slot, kv_head, off)`; when the view is valid it returns `row.data` (the row in place, no copy); otherwise it gathers the row with get_k_row into the caller's 64-byte-aligned scratch (dest, 256 bytes per head) and returns dest [h/tron/scheduler/full.hpp:2747-2771]. The row-major geometry branch is unchanged (page::k) [:2768-2771]. The V callback always unpacks into the scratch [:2773-2782].
- The comment says the row-major block is "the usual case under hardware attention" and cites Note [Row-major blocks under hardware attention] [:2755-2760].

## 5. The three Notes (titles exactly as written)

- `Note [Row-major tail block]`: defined in h/tron/tensor/k_vnni.hpp:445 (tildes at :446). Content: section 1 above. Referenced from kv_cache.hpp (:679, :2116, :2205), model.hpp (:3102, :3304), kernels/k_vnni.hpp (:44), the test headers [t/t_k_vnni_layout.cpp:5-6, :270].
- `Note [Row-major blocks under hardware attention]`: defined in h/tron/models/kv_cache.hpp:729 (tildes at :730), text to :764. What it says: when the hardware attention scores an operation's K (cached_operation_uses_hw, decided once per model), save_k records no row bits for the rows a short run stores and queues no block; such a block stays row-major and a page copy does not convert it either [:731-736]. Why: past the engagement point the FPGA holds the K/V of every DMA-complete GOF and the CPU scores only the tail above them; a page the hardware covers takes the software loop with no K bytes read, and a tail token in a row-major block is scored row by row, so the AMX kernel never reads a block that decode completes there [:737-746]. What the conversion would cost: a serial main-thread copy of every completed block of every layer and KV head at the forward end (8 KiB of plane traffic plus an 8 KiB stack round trip per block and KV head, every 16th step for every user) and a 64-line gather per row whenever the staging copies a converted block [:746-750]. Whole-block saves still store VNNI at once, which is the only way a page the hardware does not cover yet becomes dense for the AMX kernel [:750-753]. The cost accepted: a range the software scores although the operation is a hardware one (before the engagement point, a prompt shorter than 128 tokens, a shard without HBM, USE_HW_ATTN=N raising the engagement point) scores decode-completed blocks with the dotter instead of the AMX kernel; both layouts hold the same K values; the fp32 add order of the dotter and of qk_group differs, so a score and a generated token can differ by that add order alone [:754-764]. Referenced from model.hpp (:1845-1846, :3107, :3160-3161, :3423-3424), kv_cache.hpp (:797-798, :2334-2335, :2615), full.hpp (:2757), self_attention.hpp (:1920-1921), t/t_llama_unit.cpp (:4077).
- `Note [K VNNI storage]` (defined at h/tron/models/kv_cache.hpp:651, unchanged title): T inserts the state paragraph (a block holds the VNNI layout only once complete and converted; the two bit sets; who sets, queues, converts, drops and copies them; why the transition is at 16 rows) between the existing layout paragraphs and the consumer list [:677-727], inserts the hardware-attention Note after it [:729-764], and changes the consumer items: item 1 (the whole-block save and the row-by-row store of any shorter run, store_row_major, 4 whole lines per token) [:767-778]; item 2 (the dense AMX path runs only when k_vnni_blocks says every block is converted; three cases take the software loop) [:779-784]; item 3 (the VNNI reader reads the VNNI blocks; the tail block's tokens are scored with the dotter through row_major_row, 4 lines per token) [:785-794]; item 4 (the staging returns the row pointer from k_row_if_row_major for a row-major block, no copy; gathers with get_k_row for a converted block) [:795-804]; item 5 (whole-page copies carry the bits; token copies go through row-major rows with block_to_rows first and block_to_vnni after) [:805-812]; item 6 (set_k_row / get_k_row follow the block's recorded layout) [:813-816]. Items 1 to 6 are on lines 767-816 of the probe; the kill-switch paragraph follows at :817-821.
- lint-notes (bin/lint-notes, a Haskell checker run by `make lint-notes` [GNUmakefile:686-692]) requires every "Note [...]" reference to name a defined Note with the closing bracket on the same line as "Note [" [bin/lint-notes:16-25]. Every reference above names one of the three defined Notes or Note [Shared block save] / Note [AMX attention dispatch] / Note [QK orientation], which exist already.

## 6. New identifiers with their probe definition line (the "must be present" list)

h/tron/tensor/k_vnni.hpp:
- k_vnni::PANEL_ROWS_4 [:93]; k_vnni::BLOCKS_PER_PAGE_MASK_0XF [:96]; k_vnni::block_bit [:98]; k_vnni::offset_bit [:103]; the static_asserts [:107-113].
- Note [Row-major tail block] [:445].
- tron::row_major_row [:472]; tron::store_row_major [:486]; tron::load_row_major [:496]; tron::block_to_vnni [:507]; tron::block_to_rows [:522].
- `#include <cstring>` [:46].

h/tron/models/kv_cache.hpp:
- book::eagle_view_active [:1087].
- page::k_vnni_blocks [:2135]; page::k_storage_ref [:2147]; page::k_storage_of [:2152]; page::note_k_row_saved (template) [:2169] and (uniform overload) [:2188]; page::note_k_block_saved [:2197]; page::k_block_to_vnni [:2211]; page::k_block_to_vnni_at [:2216]; page::k_row_if_row_major [:2343].
- set_k_block with 4 parameters [:2279-2283]; set_k_row's layout branch [:2256-2260]; get_k_row's layout branch [:2300-2304]; clear_kv_complete_at's k_forget_row call [:2478].
- private: EAGLE_STORAGE_SLOTS_1 [:2494]; BLOCK_COMPLETED_FALSE [:2496]; CONVERTED_FALSE [:2498]; CONVERTED_TRUE [:2499]; k_state_ix [:2504]; k_block_bits [:2510]; k_block_is_vnni [:2516]; k_with_storage_geometry [:2526]; k_storage_readable [:2541]; k_forget_row [:2554]; k_rows_saved_ [:2618-2619]; k_vnni_blocks_ [:2623-2624]; copy_storage_slot(k_storage_ref, ...) [:2693]; copy_from's two k_storage_ref constructions [:2794, :2803-2804]; the move constructor's bit copy [:1970-1975].
- Note [Row-major blocks under hardware attention] [:729]; the state paragraph of Note [K VNNI storage] [:677-727].

h/tron/models/model.hpp:
- pending_k_block [:3167]; pending_k_blocks_ [:3172]; convert_pending_k_blocks [:3176]; the forward-end call [:1847]; the `n < k_store_block` branch [:3303]; the TRON_ASSERT on `present` [:3324-3325]; the note_k_block_saved call [:3339]; the policy block with cached_operation_uses_hw inside save_k_impl [:3425]; the note_k_row_saved call [:3432]; the push_back [:3433-3434]. Absent: k_scatter_run_len (0 hits).

h/tron/scheduler/full.hpp: the k_row_if_row_major call [:2762-2764].

Outside the four files, for the absent-list of PR3-handoff.md 5.2 that PR-4 inverts: k_layout_dense [h/tron/models/self_attention.hpp:1924]; the test helpers save_row_state [t/t_k_vnni_layout.cpp:633] and vnni_blocks [:642].

## 7. The `#include <cstring>` question

- The T patch removes the line from h/tron/kernels/k_vnni.hpp [ref/T-4737-merge.diff:29-35] and adds it to h/tron/tensor/k_vnni.hpp [:1088-1095]. The probe keeps both: kernels/k_vnni.hpp:18 and tensor/k_vnni.hpp:46. The probe's staged diff of kernels/k_vnni.hpp contains no cstring line (grep found none), so the removal hunk was dropped as split-plan.md U2.2 says [split-plan.md:438-440].
- Which functions call a <cstring> function. kernels/k_vnni.hpp: qk_group calls std::memcpy once, to read one dimension pair of the bf16 query as a 32-bit word [h/tron/kernels/k_vnni.hpp:108, inside qk_group defined at :63-65]. That is the header's only <cstring> use. tensor/k_vnni.hpp: store_row_major [:489] and load_row_major [:499] each call std::memcpy; no other function of that header uses <cstring> (grep for memcpy, memset, memcmp, std::mem found only those two lines). kernels/k_vnni.hpp includes tensor/k_vnni.hpp [:25], so it would also reach <cstring> through that include; keeping its own include line makes the dependency explicit.

## 8. Proposed mutation checks on the storage code

Both run in the option-on worktree, as PR-3's M1 and M2 did. Before each mutation, `--list-tests '<name>'` must list exactly that one case; a mutant run that prints "No tests ran" is a failed check. Restore with `git checkout -- <file>`, rebuild, and run the whole binary again. Record what Catch2 prints; do not predict the assertion counts.

### M3: row_major_row places a block's rows in its own panels

- File and text (occurs once; `grep -c '(t / k_vnni::PANEL_ROWS_4) \* k_vnni::TOKEN_BLOCKS_4 + c) \*' h/tron/tensor/k_vnni.hpp` = 1 at the probe): line 477 `               ((t / k_vnni::PANEL_ROWS_4) * k_vnni::TOKEN_BLOCKS_4 + c) *`. Replacement: `((t / k_vnni::PANEL_ROWS_4) * k_vnni::TOKEN_BLOCKS_4 + (c ^ 1)) *` (block c's row-major rows land in block c ^ 1's panels; the same style as PR-3's M1).
- Binary: t_k_vnni_layout (`cmake --build gen --target t_k_vnni_layout`; the header is included by libtron sources, so the rebuild is longer than a test-only change; PR-3's M2 note applies, about 5 min est.).
- Command: `./gen/t_k_vnni_layout --skip-benchmarks 'row-major tail block converts to the VNNI layout and back\, bit for bit'` (one comma, escaped) [t/t_k_vnni_layout.cpp:268-269].
- Expected first failure: in the first section "row_major_row rows are distinct, 64-byte aligned, and inside the block's panels", at tok = 0: the mutated address is plane + 512 elements = 1024 bytes, so `REQUIRE(off % 64 == 0)` [:296] passes, panel = 1 and `REQUIRE(panel % TOKEN_BLOCKS_4 == c)` [:299] fails with CAPTURE tok = 0, off = 1024. Expected FAILED line: `t/t_k_vnni_layout.cpp:299`.
- The second section (Catch2 re-enters the case for the remaining section after a failed section; confirm in the run): at c = 0, store_row_major writes the 16 rows into block 1's panels, block_to_vnni reads them back from the same mutated place and writes block 0 correctly, so blk's block 1 holds rows where ref's holds poison, and `REQUIRE(std::memcmp(&blk->plane, &ref->plane, ...) == 0)` [:319] fails with CAPTURE c = 0. Expected summary: a test-cases line ending in "1 failed".
- The rest of the binary under the mutant (by reading, not measured): the page-state case [:654] is expected to fail at check_rows after token 16 is saved (its row-major row overwrites panel (0, 0) of the converted block 0, so get_k_row of token 0 returns changed bits at `REQUIRE(same_bits(got, row))` [:684]); the append case [:910] is expected to fail the same way through its source page. The index-map, typed-operations, block-save, reader and page-accessor cases [:109, :128, :212, :466, :525] are expected to pass: they never convert a block, or they write and read through the same mutated address. t_llama_unit and t_amx_dispatch_dtype also include the header but the chain does not run them under the mutant.

### M4: note_k_row_saved reports a block complete at its 16th row only

- File and text (occurs once; `grep -c 'return (after & k_block_bits(c)) == k_block_bits(c) &&' h/tron/models/kv_cache.hpp` = 1 at the probe): line 2182 `    return (after & k_block_bits(c)) == k_block_bits(c) &&`. Replacement: `!=` for `==` (one token). Under the mutant every row of an incomplete block reports "complete", and the 16th row reports "not complete", so no block is ever converted through the row path; whole-block saves (note_k_block_saved) are unaffected.
- Binary: t_k_vnni_layout, same rebuild remark (kv_cache.hpp is included by libtron).
- Command: `./gen/t_k_vnni_layout --skip-benchmarks 'page K blocks turn VNNI at the 16th saved row and back when a row is forgotten'` (no comma; the name is split over two string literals in the source [t/t_k_vnni_layout.cpp:654-655]).
- Expected first failure: the first REQUIRE of the case, `REQUIRE(save_row_state(page, SLOT_0, tok) == (vnni_build && tok == LAST_OF_BLOCK_0_15))` [:691-692] at tok = 0: note_k_row_saved returns true (after = bit 0, `(after & 0xffff) != 0xffff` holds, block 0 not converted), save_row_state's k_block_to_vnni call refuses (16 row bits not set, CONVERTED_FALSE [h/tron/models/kv_cache.hpp:2221-2225]) and returns true, the expected value is false. Expected FAILED line: `t/t_k_vnni_layout.cpp:691` with CAPTURE tok = 0. Expected summary: `test cases: 1 | 1 failed`, `assertions: 1 | 1 failed` (no passed column, the Catch2 3.7.1 column rule of PR3-handoff.md step 6 M1).
- The rest of the binary under the mutant (by reading): the EAGLE case fails at `REQUIRE(vnni_blocks(page, SLOT_0) == ... BLOCK_0_ONLY_0X1 ...)` [:824] (the primary block never converts); the two-slot case at [:892]; the append case at `REQUIRE_FALSE(save_row_state(...))` [:934] at tok = 0. The tail-block, index-map, typed-operations, block-save, reader and page-accessor cases pass (they do not call note_k_row_saved). t_llama_unit's save_k case would fail at `REQUIRE_FALSE(pages[0]->note_k_row_saved(slot, tok))` [t/t_llama_unit.cpp:4045] if it were run.

Either check alone proves the new cases can fail; M3 covers the layout operations (tensor/k_vnni.hpp), M4 the page state (kv_cache.hpp). PR-3's M1 and M2 still apply unchanged at the probe (their texts: store_block's panel line [h/tron/tensor/k_vnni.hpp:415] and k_store_cut_units' cut condition [h/tron/models/model.hpp:3225]).

## 9. Where the probe differs from the T patch in these files

The staged diff of the probe was compared with the T patch line by line (added and removed lines only). model.hpp and full.hpp are identical. Differences:

- kv_cache.hpp, Note [K VNNI storage] item 3: the T patch rewrites the PR 4424 wording "the software path for partial pages, the kill switch (TRON_AMX_DISABLE=1) and hosts without AMX ..." [ref/T-4737-merge.diff:191-204]. The probe's base (PR-2's pre-review rewording, kept by PR-3) reads "every other visit of a VNNI slot uses k_vnni::qk_group with the same view: partial or partly visible pages, the kill switch, hosts without AMX, builds without TRON_AMX_DISPATCH, and the shapes and query types outside the AMX gate (Note [AMX attention dispatch])". The probe's resolution keeps that list and adds T's new sentences ("reads the VNNI blocks with k_vnni::qk_group"; "The tokens of the row-major tail block are scored with the row-major dotter ... 4 lines per token") [h/tron/models/kv_cache.hpp:785-794]. This is why the probe's numstat is +496/-56 against the patch's +493/-52.
- tensor/k_vnni.hpp header: the probe keeps PR-2's sentence "and the AMX QK kernel in h/tron/kernels/amx_attn_iface.hpp" after "The AVX-512 score reader of this layout is in h/tron/kernels/k_vnni.hpp" [:9-10]; the T patch's version of the sentence has no AMX kernel mention [ref/T-4737-merge.diff:1081-1083].
- kernels/k_vnni.hpp: the include hunk is dropped (section 7); the qk_group comment keeps PR-2's "one of the two layout-specific score kernels allowed to take the plane address (the other is amx_attn_h128g4::qk_vnni_128x4)" where the T patch says "one of the two layout-specific readers allowed to take the plane address" [h/tron/kernels/k_vnni.hpp:44-52; ref/T-4737-merge.diff:37-64].

For the stack-invariant comparison of split-handoff.md step 4.3 these three are comment-wording differences against the PR 4424 head; the handoff should list them as expected differences or decide to restore the 4424 wording.

## 10. Callers of the new functions, in one place

- note_k_row_saved: model.hpp:3432 (main, save_k_impl, after the join); t/t_k_vnni_layout.cpp:635; t/t_llama_unit.cpp:2544, :4045; t/t_amx_dispatch_dtype.cpp:135.
- note_k_block_saved: model.hpp:3339 only (store_k_block, any worker of a shared window).
- k_vnni_blocks: self_attention.hpp:1926 (k_layout_dense, the dense AMX gate), :2021 (the software loop's per-token layout choice); the tests.
- k_storage_of: model.hpp:3433; kv_cache.hpp:2212. k_block_to_vnni_at: model.hpp:3180. k_block_to_vnni: tests only.
- k_row_if_row_major: full.hpp:2762 only.
- row_major_row: self_attention.hpp:2029 (the dotter's row); kv_cache.hpp:2350, :2753, :2756; tensor/k_vnni.hpp:489, :499; the tests.
- block_to_vnni / block_to_rows: kv_cache.hpp:2230, :2578, :2745, :2761; the tail-block test.
- convert_pending_k_blocks: model.hpp:1847 (forward end); t/t_llama_unit.cpp:4071, :4093, :4113, :4207, :4229.
- help_drain_gof (existing, named by the Note's reasoning): self_attention.hpp:761 (begin_attention_job, budget 4). wait_for_coop_gof: model.hpp:1840.

--- concerns ---
- The probe resolves three comment hunks by keeping PR-2's wording instead of the T patch's (Note [K VNNI storage] item 3 in kv_cache.hpp:785-794, the tensor/k_vnni.hpp header lines 9-10, the qk_group comment in kernels/k_vnni.hpp:44-52). The handoff must say whether PR-4 keeps those wordings (then the stack-invariant comparison of split-handoff.md step 4.3 lists them as allowed differences) or restores the PR 4424 text.
- store_block in h/tron/tensor/k_vnni.hpp keeps its __mmask16 present parameter and its masked-store branch (lines 401-428); after T the only non-test caller passes FULL_BLOCK_0XFFFF (kv_cache.hpp:2284-2285 and tensor/k_vnni.hpp:516). The masked branch is reachable from the block-save test only. The PR-4 body should say so, or the author should decide whether PR-4 removes it (the T patch does not).
- The expected Catch2 behaviour of M3 (the second section runs after the first section failed, giving two FAILED lines in one case) is from reading Catch2's section semantics, not from a run; the chain should require rc != 0, a FAILED line at t/t_k_vnni_layout.cpp:299 and a test-cases line ending in '1 failed', and record the assertion counts rather than predict them.
- Rebuild time for M3 and M4: both headers are included by libtron sources, so `cmake --build gen --target t_k_vnni_layout` rebuilds libtron objects. The about-5-min figure is PR-3's M2 estimate for model.hpp; for kv_cache.hpp and tensor/k_vnni.hpp it is Insufficient data until measured.
- The statements in section 8 about which other cases pass or fail under each mutant come from reading the code and the tests, not from a run. The chain treats only the named case's result as the check.
- Insufficient data on the T patch's effect on t_amx_dispatch_dtype under mutant M4: that test's REQUIREs after the record_rows loop (t/t_amx_dispatch_dtype.cpp:135-136) were not read.
