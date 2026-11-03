# Kept findings for PR 4958 (30; each survived 3 refuters)

## structure-4958-1 [block] h/tron/models/model.hpp:3211 (refuter votes against: 0/3; remedy in design: yes)
Hunk: if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) {
        for (size_t t = task_begin; t < task_end; ++t) {
Ben would say: 5047 took the last layout_on out of model.hpp; store_k_block puts two back and carries two store paths (a row-major per-token loop, a VNNI run scan with a scatter-or-block choice) in one 90-line function. Can the cache answer whether a slot stores K in blocks, so the model has one loop and asks?
Evidence: 5047 did: commit ade89a9d9c deleted the `if constexpr (k_vnni::layout_on<geometry.kv.head_size>)` of PR 4956's save_k_impl and left one `pg.template set_k_row<geometry.kv>(slot, kv_head, j, kout)` call (count of layout_on in model.hpp: 1 -> 0). Profile P1, P3, P5; comment 3936986164 (two control-flow paths in one function -> two functions with shared helpers).
Remedy: Add `template <kv_geometry geometry> static constexpr size_t k_block_tokens()` to page (16 for a VNNI slot, 0 = per-row store), branch on `page::k_block_tokens<geometry.kv>() == 0` instead of the layout, and move the run scan into a helper (next_k_run) so store_k_block has one job.

## record-4958-2 [block] h/tron/models/model.hpp:3211 (refuter votes against: 0/3; remedy in design: yes)
Hunk: if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) {
  for (size_t t = task_begin; t < task_end; ++t) {
Ben would say: This function has two bodies: a row-major one, and a VNNI one with its own run scan, two store paths and a conversion buffer. I just moved every layout decision into the cache (set_k_row(expr) converts, score_k picks the reader). Why does model.hpp get to know the layout again, here and in k_store_shared?
Evidence: C3 (3936986164 'two distinct control flow paths ... two distinct functions'), C5 (5270587330), P1 (ade89a9d9c: k_vnni::layout_on uses in model.hpp 1 -> 0; PR 4958 adds two: model.hpp:3154 and 3211). Function is 93 lines (3201-3293) with if constexpr on the layout, rows_are_bf16 (3225) and a 4 KiB conv buffer (3229).
Remedy: The cache answers 'does this slot save K in blocks': page::k_block_tokens<geometry>() = 16 for a VNNI slot, 0 for row-major. The cache converts rows itself: set_k_row(expr) for a run of one, a set_k_block overload that takes the 16 row views plus present. store_k_block keeps one body (scan runs, set_k_row or set_k_block); if constexpr (layout_on) leaves model.hpp.

## abstraction-4958-2 [block] h/tron/models/model.hpp:3211 (refuter votes against: 0/3; remedy in design: partial)
Hunk: if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) { ... pg.template k<geometry.kv>(slot, kv_head, j).set(row_of(ix, kv_head));
Ben would say: 5047 left model.hpp with no idea how K is stored; this brings three k_vnni references back, plus a page::k() that no longer exists. Why does the model pick the page operation per layout? Hand the page the block and let it store it its own way.
Evidence: P1 (ade89a9d9c: layout_on in model.hpp 1 -> 0; grep at Ben's head: 0 `k_vnni::` in model.hpp, PR head: 3 at :3139, :3154, :3211), P2 (page::k removed; :3219 calls it), P4 (the call site asks the cache and takes the answer), P5 ("spaghetti"); pr5047-c2.diff model.hpp hunk (18 layout-aware lines -> one set_k_row(expr) call). kv_cache.hpp:2087 constrains set_k_block to VNNI slots, which is what forces the if constexpr into the model. :3141 k_scatter_run_len is a second layout decision (one-token run = scatter) made by the model.
Remedy: The page answers both questions. (a) `page::k_block_tokens<geometry>()` (16 for a VNNI slot, 0 = per-token store) replaces k_vnni::BLOCK_TOKENS_16 in k_store_shared and in the run cutting. (b) set_k_block exists for every declared geometry: the row-major branch stores the present rows with k_at(i).set(row) inside the page, so store_k_block has one body and model.hpp has zero k_vnni references. (c) Optional: set_k_block chooses store_row itself when one lane is present, and k_scatter_run_len leaves the model. Design 3.PR3' 2a/2b cover (a) and remove layout_on from model.hpp, but keep a row-major branch in store_k_block and keep k_scatter_run_len there.

## interface-4958-1 [block] h/tron/models/model.hpp:3211 (refuter votes against: 0/3; remedy in design: yes)
Hunk: if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) {
  ... pg.template k<geometry.kv>(slot, kv_head, j).set(row_of(ix, kv_head));   // line 3219
Ben would say: My commit took the last k_vnni::layout_on out of model.hpp and removed the page::k() views; this brings both back (here and in k_store_shared at 3154). Why does save_k need to know the layout at all? set_k_row takes the expr for either kind of slot.
Evidence: P1 (model.hpp layout_on 1 -> 0 in ade89a9d9c), P2 (page::k overloads removed, ade89a9d9c), P4; Note [K VNNI storage] item 6 at his head: 'The same operations serve every slot; layout-specific access stays in the cache.'; corpus 5270587330
Remedy: Row-major branch (3212-3221) becomes one call per (token, kv_head): pg.template set_k_row<geometry.kv>(slot, kv_head, j, kout) (his expr overload). k_store_shared asks the cache instead of layout_on: a constexpr page query (design.md's k_block_tokens<geometry>() == 0 means 'no block save, no sharing'). Then model.hpp has zero layout_on again.

## structure-4958-3 [block] h/tron/models/model.hpp:3219 (refuter votes against: 0/3; remedy in design: yes)
Hunk: pg.template k<geometry.kv>(slot, kv_head, j).set(row_of(ix, kv_head));
Ben would say: page::k() does not exist on my branch; kv_block is private there. This line is the raw-view write I removed. set_k_row takes an expr now, so why not use it here too?
Evidence: 5047 did: commit ade89a9d9c replaced PR 4956's `pg.template k<geometry.kv>(slot, kv_head, j).set(kout)` with `pg.template set_k_row<geometry.kv>(slot, kv_head, static_cast<size_t>(j), kout)` and deleted the 8 page::k() overloads ('remove the public raw K views'). Profile P2. Merge conflict: kv_cache 3 and model 1 (design.md section 1).
Remedy: `pg.template set_k_row<geometry.kv>(slot, kv_head, j, row_of(ix, kv_head));` (Ben's expr overload; row_of already returns an expr).

## abstraction-4958-1 [block] h/tron/models/model.hpp:3353 (refuter votes against: 0/3; remedy in design: no)
Hunk: while (w.finished.load(std::memory_order_acquire) < n_helpers) {
          _mm_pause();
Ben would say: Why are we hand-rolling two spin loops and a second watchdog here? The line above your new struct is `latch_ref layer_done`: it already has wait_until_geq, count_down, reset and the TRON_LATCH_WATCHDOG. What does this buy us that the latch does not?
Evidence: C4 (3936968255, 3937239431: use the existing types), C15 (3937077542: he reads memory orders), C2 (3936807517: another timeout knob next to an env-var watchdog), C3 (3936963481). Tree at b39765ec29: h/tron/threading.hpp:110-170 (latch_ref: wait, wait_until_geq, count_down, operator++, reset), :175-215 (TRON_LATCH_WATCHDOG logs latch states), h/tron/models/common.hpp:1038 (layer_done = latches.make_latch), :1087-1091 (wait_for_layer uses hardware::mwaitx::wait_for_event), h/system/mwaitx.hpp:69-120 (wait_for_geq with a wait_ns bound). PR adds: model.hpp:16 <immintrin.h>, :10 <chrono>, :3145-3148 k_join_clock_spins / k_join_timeout_s, :3335-3338 helper wait, :3351-3365 join; common.hpp:1202-1205 the three atomics. Ben's head model.hpp: 0 intrinsics.
Remedy: Make `opened` a count-up latch_ref (main: operator++; helper: wait_until_geq(my_window)) and `finished` a latch_ref (main: reset(n_helpers) before opening; helper: count_down(); main: wait()), both created next to layer_done with latches.make_latch(0, "k_store_opened" / "k_store_finished", ix). count_down is acq_rel and wait acquires, so the release/acquire pairing of the Note stays. Delete <immintrin.h>, <chrono>, _mm_pause, k_join_clock_spins and k_join_timeout_s from model.hpp. If the 120 s abort stays (the PR body's open item), it is one bounded wait: loop on mwaitx::wait_for_geq(&finished, n_helpers, wait_ns) with one clock read per return. next_unit stays a plain atomic (a claim counter, not a latch).

## structure-4958-5 [should] h/tron/models/kv_cache.hpp:2092 (refuter votes against: 0/3; remedy in design: partial)
Hunk: __mmask16 present,
      const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept {
Ben would say: Every other row operation on page takes a typed row (k_source_row, k_destination_row). This one takes 16 bare bf16 pointers and an AVX-512 mask, and a comment to say they are native rows, not packed storage. That comment is the thing the view types exist to replace. Also: this is the only K operation left with a layout requires-clause, which is why the caller has to branch at compile time.
Evidence: Comment 5270587330 ('we really don't want bf16_t* values floating around without any indication of how they are laid out'); issue comment 5765866077 (store_row takes `std::span<const bf16, Dims>`; kernels whose signatures state what they accept). Profile C5, P2 (the 8 k() overloads and k_packed, each with a layout requires-clause, were removed in ade89a9d9c; set_k_block re-adds one). First `__mmask16` on the page API (kv_cache.hpp has no other use).
Remedy: Take the rows as typed row views (the overload of finding 4) instead of `const bf16* const rows[16]`; keep the raw-pointer form, if at all, as the private step that calls store_block. Place the function after Ben's set_k_row(expr) (the conflict hunk). The mask type can stay a nit.

## record-4958-5 [should] h/tron/models/kv_cache.hpp:2093 (refuter votes against: 0/3; remedy in design: yes)
Hunk: __mmask16 present,
  const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept {
Ben would say: set_k_row takes a typed row view; set_k_block takes 16 bare bf16 pointers, some null, and the comment has to say in words that they are 'native source rows, not packed storage'. These are the bf16* values floating around that I asked to get rid of. Can the block take the row views the caller already has?
Evidence: C5 (5270587330 'we really don't want bf16_t* values floating around without any indication of how they are laid out'), C4 (3937239431). PR lines kv_cache.hpp:2089-2093, tensor/k_vnni.hpp:342-345 (store_block, same raw array), model.hpp:3278 (const bf16* rows[16] = {}) and 3282 (rows[run_t[i]] = kout.data strips the typed view to a pointer).
Remedy: set_k_block(slot, kv_head, block, present, std::array<Row, 16>) where Row is the K buffer's row view type (const_k_row_view<head_size, Aligned, Dma>; absent lanes default); store_block takes the same; the page converts non-bf16 rows on its own stack. No .data in model.hpp.

## interface-4958-3 [should] h/tron/models/kv_cache.hpp:2093 (refuter votes against: 0/3; remedy in design: partial)
Hunk: __mmask16 present,
const bf16* const rows[k_vnni::BLOCK_TOKENS_16]) noexcept {
Ben would say: We really don't want bf16* values floating around without an indication of how they are laid out. set_k_row takes a const_k_row_view; why does set_k_block (and store_block at k_vnni.hpp:345) take sixteen raw pointers plus a comment saying 'native source rows in dimension order'? And because the parameter is bf16*, the activation-type conversion (model.hpp:3223-3229, 3281-3286) has moved back out of the cache, which set_k_row(expr) had just put inside.
Evidence: C5 (5270587330 'we really don't want bf16_t* values floating around'), straw-man 5765866077 ('A typed store_block() retains the existing masked 16-token transpose/store path'), P2 ('remove the public raw K views'), set_k_row(expr) in ade89a9d9c; C11 (4134076112) if the raw overload keeps no production caller
Remedy: rows as std::array<const_k_row_view<head_size, Aligned, Dma>, 16> (the type store_row already takes), plus an expr-row overload that converts on the stack inside the page, mirroring set_k_row(expr); store_block keeps its pointer operand internally, as store_row reads src.data. Retire the raw-pointer page overload once model.hpp no longer calls it.

## structure-4958-2 [should] h/tron/models/model.hpp:3154 (refuter votes against: 0/3; remedy in design: yes)
Hunk: if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) {
        return false;
Ben would say: Why does the sharing decision know the storage layout? The thing that matters is whether the slot saves in blocks, and the cache knows that.
Evidence: 5047 did: no equivalent code existed in PR 4956; the commit's rule was that model.hpp holds no layout_on use (ade89a9d9c, 'hide K layout behind row and scoring operations'). Profile P1, P4.
Remedy: `return page::k_block_tokens<geometry.kv>() != 0 && n_workers > 1 && ...` with the constexpr of finding 1; the layout clause disappears from k_store_shared.

## abstraction-4958-3 [should] h/tron/models/model.hpp:3223 (refuter votes against: 0/3; remedy in design: partial)
Hunk: using kv_elem_t = std::remove_cv_t<
            std::remove_pointer_t<decltype(row_of(token_job_id{0}, 0).data)>>;
Ben would say: I took exactly this decltype-and-convert dance out of save_k in 5047 by giving set_k_row an expr overload, and here it is again, twice. And set_k_block takes sixteen bare bf16 pointers: store_row takes a const_k_row_view, why does store_block not?
Evidence: pr5047-c2.diff kv_cache.hpp:2048-2065 (set_k_row(const expr<X, head_size>&): conversion inside the page) and its model.hpp hunk; C5 (5270587330: pointers with no layout hint; 5765866077: views carry their type into kernels); C12 (4134925164 -> PR 4697 row-view alias, the ben-review reference example). PR head: model.hpp:3223-3229 (kv_elem_t, rows_are_bf16, conv[16][128]), :3263-3273 (two set_k_row spellings), :3278-3285 (const bf16* rows[16]; rows[run_t[i]] = kout.data), kv_cache.hpp:2093 and h/tron/tensor/k_vnni.hpp:345 (const bf16* const rows[16]); k_vnni.hpp:209-212 const_k_row_view / k_row_view, :295-297 store_row takes const_k_row_view; h/tron/tensor/view.hpp:57 view::valid().
Remedy: page::set_k_block<geometry>(slot, kv_head, c, present, const std::array<Row, 16>& rows) with Row = the activation row view type (the slice of ks[ix].as_view()), absent lanes default-constructed (valid() false). The page reads bf16 rows in place and converts other types on its own stack, as its set_k_row(expr) does. store_block takes std::array<const_k_row_view<Cols, Aligned, Dma>, 16> like store_row; the pointer is taken inside, next to the intrinsics. store_k_block then loses kv_elem_t, rows_are_bf16, conv and both k_source_row spellings. Design 3.PR3' 2c has the page overload; it does not say what store_block takes.

## structure-4958-4 [should] h/tron/models/model.hpp:3225 (refuter votes against: 0/3; remedy in design: yes)
Hunk: constexpr bool rows_are_bf16 = std::is_same_v<kv_elem_t, bf16>;
        // A bf16 K buffer is read in place. Any other activation type is
Ben would say: I moved this conversion into the cache in 5047. Here it is again, twice (lines 3265-3272 and 3281-3285), with a 16-row stack buffer in the model. The single-token case is already set_k_row(expr). Can set_k_block take the rows as they are and convert inside the page?
Evidence: 5047 did: commit ade89a9d9c removed PR 4956's `kv_elem_t` / `is_same_v<kv_elem_t, bf16>` / `alignas(64) bf16 row[...]` conversion from save_k_impl and added page::set_k_row(const expr<X, head_size>&) ('Convert activation rows to the cache's bf16 representation'). Profile P1; comment 4134925164 (a subtle pattern repeated gets deduplicated).
Remedy: Single-row path: `set_k_row(slot, kv_head, j, kout)` (Ben's overload). Block path: a set_k_block overload taking the 16 activation row views (`std::array<Row, 16>` plus present) that reads bf16 rows in place and converts other types on the stack inside the page. `rows_are_bf16` and `conv` leave model.hpp.

## interface-4958-2 [should] h/tron/models/model.hpp:3239 (refuter votes against: 0/3; remedy in design: partial)
Hunk: const size_t c =
    static_cast<size_t>(pg.offset_in_page(token_jobs[ix0])) / k_store_block;
Ben would say: The block index, the lane bit (3253), the uint8_t lane array (3256) and the 16-token run limit are coordinates of the VNNI panel, and model.hpp computes all of them. Why not hand the cache the run and let it choose scatter or block? set_k_block existing for one layout only (the requires clause at kv_cache.hpp:2087-2088) is what forces this branch.
Evidence: P1, P4, P5 ('a bit spaghetti'); his Note item 3 'Attention code supplies queries and a live-token mask, not a layout' (ade89a9d9c); C5 (5270587330: representation details floating around); C3 (3936986164)
Remedy: One page verb for every slot that takes a run in page coordinates, e.g. set_k_rows<geometry>(slot, kv_head, first_offset, span-of-row-views) or (offset, row) pairs of one page; inside the cache: group by 16-token block, build `present`, call store_block or store_row. store_k_block then only walks consecutive KV items of one page. Work units keep block granularity by asking the cache for its unit size (design.md k_block_tokens), so the unit cut and the stored bytes are unchanged.

## abstraction-4958-6 [should] h/tron/models/model.hpp:3242 (refuter votes against: 1/3; remedy in design: yes)
Hunk: token_job_id run_ix[k_store_block];
          uint8_t run_t[k_store_block];
Ben would say: store_k_block is 95 lines with a scan and two stores interleaved four levels deep. A run is a thing here (page, block, lanes, items): name it and give it a function that finds the next one, so the two stores read as what they do.
Evidence: C3 (3936963481: a function near 200 LoC gets a helper; 3936986164), P3; the ben-review skill (several values describing one concept). PR head: model.hpp:3238-3259 (pg, c, run_ix[16], run_t[16], n, present describe one run), :3260-3290 (two consumers decode the same six values).
Remedy: struct k_run { page* pg; size_t block; block_lanes present; std::array<token_job_id, 16> items; std::array<uint8_t, 16> lanes; size_t n; } and `k_run next_k_run(std::span<const token_job_id> unit, size_t& t)`. store_k_block becomes a loop: run = next_k_run(...), then one store call per kv_head (set_k_row for n == 1 and set_k_block otherwise, or the page decides per finding 2c). Design 3.PR3' 2e names next_k_run; the struct is its return type.

## record-4958-4 [should] h/tron/models/model.hpp:3246 (refuter votes against: 0/3; remedy in design: partial)
Hunk: for (; t < task_end && n < k_store_block; ++t) {
  const token_job_id ix = q_batch->items[t];
Ben would say: k_store_cut_units already cut the items into runs of one page, one block and one KV flag. Then store_k_block scans the same items again with a second definition (skip the non-KV items, stop at a repeated offset). Which one is the definition of a run? Why not cut once and hand both paths a unit list?
Evidence: C12 (4134925164 'a rather subtle pattern that is repeated' -> he opened #4697 himself), C3 (3936963481 move code into a helper). PR lines model.hpp:3165-3191 (k_store_cut_units: boundary at kv/page/block change) and 3242-3259 (second scan: continue on !do_kv, break on page, block, repeated offset).
Remedy: One run cutter, e.g. next_k_run(q_batch, t, end) -> {page, block, present, run_ix[16], n}, used by k_store_cut_units to fill unit_start and by store_k_block to store a unit; the repeated-offset rule lives there once. The unshared path becomes 'cut units, store units 0..n on this thread'.

## structure-4958-6 [should] h/tron/models/model.hpp:3329 (refuter votes against: 0/3; remedy in design: yes)
Hunk: if (is_main) {
          k_store_cut_units(q_batch);
Ben would say: One save_k for both sides is what I asked for, thanks. But inside it, main and the helpers interleave through three is_main checks, and the window protocol (open, enter, claim, finish, join, watchdog) is written on raw atomics here rather than on the window type. Could k_store_window have those operations, so save_k_impl reads like the Note?
Evidence: Profile P3 (commit e17a12ff09: one control flow per function, scoring once after the loop); comment 3936986164 ('essentially two distinct control flow paths ... two distinct functions, possibly with commonalities factored out into helpers'); comment 3936963481 (move code out into a helper); comment 4065141577 (the one-entry-point request, satisfied). 5047 did: nothing at this site (PR 4956 had no sharing); the commit's pattern is the one quoted.
Remedy: Give batch::k_store_window_t the operations open(n_units), enter(worker_ix), claim(), finish(), join(n_helpers) with k_join_clock_spins / k_join_timeout_s as members; save_k_impl becomes about 20 lines; fields stay public for the test; memory orders unchanged.

## record-4958-3 [should] h/tron/models/model.hpp:3329 (refuter votes against: 0/3; remedy in design: partial)
Hunk: if (is_main) {
  k_store_cut_units(q_batch);
Ben would say: I asked for one save_k entry point called from both sides, not one body that branches on is_main at three places (open vs wait, finish-and-return vs join, then the marks). Can the shared part be just the claim loop, with a main function and a helper function around it?
Evidence: C3 (3936986164), C6 (4065141577: one function with worker_ix, which the PR did), P3 (e17a12ff09: one control flow per function). PR lines model.hpp:3312-3314 (is_main, shared, early return), 3329-3339, 3347-3350, 3351-3366; save_k_impl is 88 lines (3301-3388).
Remedy: save_k_impl: if (!is_main) { helper_store(w, ...); return; } main_store(w, ...) = cut + open + claim + join; both call one claim_and_store(w, ...) loop; the marks loop stays in save_k_impl after main_store.

## abstraction-4958-5 [should] h/tron/models/model.hpp:3331 (refuter votes against: 1/3; remedy in design: yes)
Hunk: w.next_unit.store(0, std::memory_order_relaxed);
          w.finished.store(0, std::memory_order_relaxed);
Ben would say: k_store_window_t is a bag of six fields, and save_k_impl spells the protocol in raw atomics braided through is_main branches: two control flows in one function again. Can the window own open, enter, claim, finish and join, so this function reads like the Note?
Evidence: C3 (3936986164: "essentially two distinct control flow paths ... two distinct functions, possibly with commonalities factored out into helpers"; 3936963481: move it into a helper), P3 (e17a12ff09: one control flow per function), C13 (per-worker state lives with its type). PR head: common.hpp:1196-1219 (six fields, no member function), model.hpp:3325-3366 (open = three stores at :3330-3333, enter = :3335-3338, claim = :3342, finish = :3348, join = :3351-3365); save_k_impl grows from about 50 to about 105 lines.
Remedy: Design 3.PR3' 2d: open(n_units), enter(worker_ix), claim(), finish(), join(n_helpers) as members of batch::k_store_window_t (fields stay public for the t_llama_unit case). save_k_impl becomes: if not shared, store all; else a helper enters, claims, finishes, returns; main opens, claims, joins; then the mark loop. The waits inside enter and join are the latch_ref calls of finding 1.

## interface-4958-4 [should] h/tron/models/model.hpp:3335 (refuter votes against: 1/3; remedy in design: partial)
Hunk: const uint32_t my_window = ++w.helper_windows[worker_ix];
while (w.opened.load(std::memory_order_acquire) < my_window) {
Ben would say: save_k_impl now has essentially two control-flow paths, main and helper, interleaved through three is_main branches (3315, 3329, 3347), with open, enter, claim, finish and the join watchdog written inline on public counters of batch. Shouldn't the window be a type with open/enter/claim/finish/join? And should the unit test really assert next_unit == n_units + n_workers (t_llama_unit.cpp:4096) rather than something the type promises?
Evidence: C3 (3936986164 'two distinct control flow paths ... two distinct functions'; 3936963481), P3 (e17a12ff09 one control flow per function), C13 (state with its owner, 3973410716), C12 (4134925164), P2 (tests go through helpers, t/kv_cache_helpers.hpp)
Remedy: batch::k_store_window_t gains open(n_units), enter(worker_ix), claim(), finish(), join(n_helpers) with the watchdog inside join; save_k_impl reads as main: cut, open, drain, join, mark / helper: enter, drain, finish. The test checks through those operations (windows opened, units) or through the stored rows, not through raw counter arithmetic.

## record-4958-1 [should] h/tron/models/model.hpp:3336 (refuter votes against: 0/3; remedy in design: no)
Hunk: while (w.opened.load(std::memory_order_acquire) < my_window) {
  _mm_pause();
Ben would say: Why are we hand-rolling a spin-wait and a watchdog here? batch already joins its main helpers with a latch_ref (next_layer: layer_done.count_down(); layer_done.wait()), latch_ref has wait_until_geq for exactly this 'opened >= W' wait, and TRON_LATCH_WATCHDOG already exists for hangs. Can we not use the latch arena instead of _mm_pause and <immintrin.h> in model.hpp?
Evidence: C4 (3936968255 'Why not use mask_t here?'), C12 (4134925164), C15 (3937077542). Tree at head: h/tron/threading.hpp:110-170 latch_ref::wait_until_geq / count_down / reset / wait, threading.hpp:174-175 TRON_LATCH_WATCHDOG, common.hpp:1076-1083 batch::next_layer joins main helpers with layer_done; PR lines model.hpp:16 (<immintrin.h>), 3142-3148 (k_join_clock_spins, k_join_timeout_s), 3336-3338, 3351-3366.
Remedy: Make opened and finished latch_refs from the batch's latch arena (like layer_done). Helper: opened.wait_until_geq(my_window). Main: finished.reset(n_helpers) before the window is released; helpers finished.count_down(); main finished.wait(). Drop k_join_clock_spins, k_join_timeout_s, the clock loop, _mm_pause and the <immintrin.h>/<chrono> includes. The PR body's open item 'join watchdog, reviewers decide' is then answered by TRON_LATCH_WATCHDOG.

## record-4958-9 [nit] h/tron/models/common.hpp:1199 (refuter votes against: 0/3; remedy in design: no)
Hunk: // This value is the array size of helper_windows below.
static constexpr size_t max_shared_workers = 128;
Ben would say: Where does 128 come from? batch's constructor already asserts app_pool().num_workers() <= per_worker_mask_t::capacity, which is 128. A second 128 here, plus a runtime 'more than 128 workers is not shared' fallback in k_store_shared that the constructor makes unreachable, is one constant too many.
Evidence: C15 (3937013971 'These ... constants deserve a short comment'), C4 (3936968255 use the existing type), C11 (4134076112 code without users). Tree at head: common.hpp:1026 using per_worker_mask_t = mask_t<128>; common.hpp:1052 TRON_ASSERT_LE(app_pool().num_workers(), per_worker_mask_t::capacity). PR lines common.hpp:1199, 1218, model.hpp:3158, Note model.hpp:3105-3106.
Remedy: std::array<uint32_t, per_worker_mask_t::capacity> helper_windows; drop max_shared_workers, the n_workers <= helper_windows.size() clause of k_store_shared and the 'or more than 128 workers' sentence of the Note (or keep one TRON_ASSERT_LE in save_k_impl).

## interface-4958-5 [nit] h/tron/models/common.hpp:1199 (refuter votes against: 0/3; remedy in design: no)
Hunk: static constexpr size_t max_shared_workers = 128;
... std::array<uint32_t, max_shared_workers> helper_windows{};   // line 1218
Ben would say: Why a second 128? batch already has per_worker_mask_t = mask_t<128> (1026) and asserts the worker count against its capacity in the constructor (1052); join_workers (1154) is per-worker state sized by it. And nothing reads max_shared_workers: k_store_shared reads helper_windows.size() (model.hpp:3158).
Evidence: C4 (3936968255 'Why not use mask_t here?'), C15 (3937013971 constants deserve a comment / one source), C11 (4134076112 code without users)
Remedy: std::array<uint32_t, per_worker_mask_t::capacity> helper_windows; drop max_shared_workers (or static_assert it equal to the capacity); k_store_shared asks the window (can_share(n_workers)) instead of reading the array size.

## interface-4958-7 [nit] h/tron/models/kv_cache.hpp:2092 (refuter votes against: 1/3; remedy in design: no)
Hunk: size_t c,
__mmask16 present,
Ben would say: Why __mmask16 at the cache boundary? score_k takes a uint64_t of tokens. The AVX-512 mask-register type belongs inside store_block, not in a page signature or as a public constant of the tensor header (k_vnni.hpp:77 FULL_BLOCK_0XFFFF).
Evidence: C5 (5270587330 representation must not leak), score_k(uint64_t live) in ade89a9d9c; no __mmask type existed in h/tron/models or h/tron/tensor before this PR
Remedy: If the cache computes the lane mask (finding 2) the parameter goes away. If a mask stays on the verb, use the plain-integer convention of `live` (uint64_t of page offsets, or uint16_t) and build the __mmask16 inside store_block.

## record-4958-10 [nit] h/tron/models/model.hpp:3075 (refuter votes against: 1/3; remedy in design: no)
Hunk: // Note [Shared block save]
Ben would say: Shared what? This Note is about the K store under the VNNI layout. The name should say so before the reader opens it, as I asked for Note [VNNI Packed V layout].
Evidence: C8 (4133643149 'Can we rename this to say VNNI'). The Note is referenced from common.hpp, kv_cache.hpp, tensor/k_vnni.hpp, TronCpp.hs, LoopyTronSpec.hs and two tests.
Remedy: Rename to Note [Shared VNNI K store] (or [VNNI K block save]) in all references; run make lint-notes.

## interface-4958-6 [nit] h/tron/models/model.hpp:3139 (refuter votes against: 1/3; remedy in design: partial)
Hunk: static constexpr size_t k_store_block = k_vnni::BLOCK_TOKENS_16;
... static constexpr size_t k_scatter_run_len = 1;   // line 3141
Ben would say: Why are these on state? k_store_block is an alias of a k_vnni constant (the cache owns the block size), k_join_clock_spins and k_join_timeout_s (3145, 3148) belong to the join, and k_scatter_run_len is a named 1 used once (3260). state has no private section, so all four are public API.
Evidence: C7 (4133613638 named constants standing in for a value are a smell), C13 (3973410716 state lives with its owner), P1 (the cache owns the layout, ade89a9d9c); struct state has no access specifier after model.hpp:1113
Remedy: Watchdog constants move into k_store_window_t; k_store_block is replaced by the cache's answer (design.md k_block_tokens<geometry>()); k_scatter_run_len becomes `n == 1` with its one-line reason, or disappears once the cache chooses scatter vs block (finding 2).

## record-4958-6 [nit] h/tron/models/model.hpp:3201 (refuter votes against: 1/3; remedy in design: partial)
Hunk: static constexpr size_t k_store_block = k_vnni::BLOCK_TOKENS_16;   // 3139
void store_k_block(batch* q_batch,                                 // 3201
Ben would say: store_k_block stores anything from one row of a row-major slot to many blocks, and k_store_block three screens above it is a number. Then set_k_block takes a 'c' and the scan keeps a 'run_t'. A newcomer cannot tell these apart. Let's name the function for what it does and the block index for what it is.
Evidence: C1 (5116532748 'nearly impossible for a newcomer to wade into'), C8 (4133643149 names say what they are). PR lines model.hpp:3139, 3141 (k_scatter_run_len), 3201, 3243 (run_t), kv_cache.hpp:2091 (size_t c), tensor/k_vnni.hpp:343.
Remedy: store_k_block -> store_k_units (or store_k_rows); k_store_block -> the page's k_block_tokens<geometry>() (design 2a) so the constant leaves model.hpp; size_t c -> size_t block in set_k_block and store_block; run_t -> lane.

## abstraction-4958-7 [nit] h/tron/models/model.hpp:3204 (refuter votes against: 1/3; remedy in design: no)
Hunk: size_t task_begin,
        size_t task_end) noexcept {
Ben would say: This takes the whole batch plus two indices into one of its vectors, and the callers spell `w.unit_start[u], w.unit_start[u + 1]` and `0, n_items`. Isn't a unit just a span of items?
Evidence: ben-review skill (more than four runtime parameters: q_batch, slot, ks, task_begin, task_end; begin and end are two adjacent size_t describing one concept, a work unit). q_batch is read only as q_batch->items[t] (model.hpp:3213, :3236, :3247). common.hpp:842, :852, :859 already pass `std::span<const token_job_id> items`. Call sites :3344-3345 and :3367. No comment in Ben's record names parameter counts, so this is a nit.
Remedy: store_k_block<geometry>(kv_slot_id slot, kv_buffer_t& ks, std::span<const token_job_id> unit); k_store_window_t::unit(u) returns std::span(items).subspan(unit_start[u], unit_start[u + 1] - unit_start[u]); the unshared call passes std::span(q_batch->items). Three runtime parameters, and the call names the unit.

## record-4958-8 [nit] h/tron/models/model.hpp:3342 (refuter votes against: 0/3; remedy in design: no)
Hunk: const uint32_t u = w.next_unit.fetch_add(1, std::memory_order_acq_rel);
Ben would say: What is acq_rel doing on the claim? Nothing is published through next_unit: unit_start comes through opened and the row stores through finished. If the order is load-bearing, say what it orders; otherwise it should be relaxed.
Evidence: C15 (3937077542 'what is this memory order doing here? AFAIK release on a load has absolutely no use'). PR lines model.hpp:3331-3333 (unit table published by opened release), 3348 and 3353 (stores published by finished release/acquire).
Remedy: std::memory_order_relaxed with a one-line comment ('the claim publishes nothing; the table comes through opened, the stores through finished'), or keep acq_rel with a comment naming what it orders.

## structure-4958-7 [nit] h/tron/tensor/k_vnni.hpp:37 (refuter votes against: 0/3; remedy in design: yes)
Hunk: // page::get_k_row, page::set_k_block, page::k_packed). book::fill_random is the
Ben would say: page::k_packed is gone on my branch; this line (which the PR edits) still lists it. Make it the operations that exist.
Evidence: 5047 did: commit ade89a9d9c changed this same line to '(page::set_k_row, page::get_k_row, page::score_k)'. Profile P2. Merge conflict: tensor/k_vnni 1 (design.md section 1).
Remedy: '(page::set_k_row, page::get_k_row, page::set_k_block, page::score_k)'.

## structure-4958-8 [nit] t/t_llama_unit.cpp:4137 (refuter votes against: 1/3; remedy in design: partial)
Hunk: if constexpr (k_vnni::layout_on<head_size>) {
      check_window(1, finished_0);
Ben would say: The test decides from the storage layout whether a window must have opened. Once the model asks the cache whether the slot stores in blocks, the test should ask the same question, not the layout gate.
Evidence: 5047 did: commit ade89a9d9c removed the `#ifdef TRON_K_VNNI` and `if constexpr (k_vnni::layout_on<geometry.head_size>)` branches from three t_llama_unit.cpp cases and made the page tests uniform through set_k_row / get_k_row and t/kv_cache_helpers.hpp. Profile P1, P2 (tests side). Same branch again at line 4154.
Remedy: `if constexpr (page_t::template k_block_tokens<geometry.kv>() != 0)` at lines 4137 and 4154, once the constexpr of finding 1 exists.
