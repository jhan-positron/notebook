# Issue #4934 candidate design v1 (2026-10-15 01:1x UTC)

Short version: three changes on top of PR #4901 (branch `jhan-vnnik-4-tail-block`, head 175b1837b9), on the new branch `jhan-vnnik-5-i4934` (worktree `~/workspace/ai-runs/tron-i4934`). (1) The software loop goes back to PR #4898's per-token body and scores the row-major rows after the loop, so no dotter is built and no layout test runs on the common path. (2) The page's block mask is read once per page per `apply_page_range` call and passed into `apply_page_tok`, which also serves the dense AMX gate. (3) The forward-end conversion runs on the app pool in parallel instead of serially on the main thread. An optional fourth change skips `save_k`'s per-item recording loop when the minibatch stored no row through `set_k_row`.

## Words used here

- the loop: the software scoring loop in `apply_page_tok` (`h/tron/models/self_attention.hpp`, lines 1946-2051 at the head).
- the reader: `k_vnni::qk_group` (`h/tron/kernels/k_vnni.hpp`), the AVX-512 routine that scores a query group against the VNNI blocks of a page through a 64-bit live mask.
- the dotter: `dotter<bf16, 128>` (`h/tron/kernels/dotter.hpp`), the per-token dot product over one row-major K row: four 512-bit loads of q at construction, per row four VDPBF16PS into two accumulators, one lane add, one horizontal reduce.
- block mask: `page::k_vnni_blocks(slot)`, one uint8_t per (page, storage slot), bit c set = 16-token block c holds the VNNI layout.
- live mask: the 64-bit mask of the relevant tokens of the page that the loop builds (`live |= offset_bit(i)`).
- the conversion: `convert_pending_k_blocks` (`h/tron/models/model.hpp`), main thread, forward end, one `k_block_to_vnni_at` per queued (page, storage, block), 8 KV heads each, serial.
- H1..H4: the measured or estimated costs: H1 per-token layout tests in the loop, H2 dotters built per page visit, H3 the serial conversion, H4 the per-item recording loop in `save_k`.

## Verified facts the design rests on (from the understanding pass, `understand-digest.txt`)

- Under the kill switch every (query, page) visit runs the loop; the dense AMX gate returns before the loop with AMX on. Prefill and decode use the same per-(query, page) call; an 8-user 8192-token prefill makes 1.2e9 visits and 7.7e10 per-token iterations.
- PR #4901's loop adds per visit: 4 dotter constructions (16 zmm loads, a 1 KiB array), an empty std::optional plane, a uint8_t; per token: an optional-engaged test and a block-bit test; at the first relevant token: one block-mask acquire load and the k_packed call. PR #4898's body was `live |= uint64_t{1} << i` and one qk_group call after the loop.
- The lazy-dotter probe removed H2 only: +2.0 to +2.3 % TPS at tp2 prompt 1024, no TTFT change. So the TTFT loss (453 to 587 ms at prompt 8192) must come from H1 (the only term whose growth matches) and H4 (est. 19 to 35 ms).
- Block bits cannot change while a pass scores: they are set in `save_k` (note_k_block_saved) before the pending sections start, and in the conversion after `run()` joined every worker. Ready sections read pages no minibatch of this pass writes.
- The conversion at the forward end runs while every app-pool worker is idle; the pool is reused for logit delivery right after. `thread_pool::parallel_for(start, end, f)` enqueues one task per worker and joins on a latch.
- The queue can hold the same block twice (a row re-saved into a complete, unconverted block); `k_block_to_vnni_at` returns false for an already converted block but has no claim step, so two concurrent conversions of one block would race.
- Under software attention no staging gather exists; the forward-end deferral protects nothing there. Under FPGA attention, hardware-scored operations queue nothing. (The design keeps the forward-end placement anyway: it is correct and the tests pin it.)
- Tests: no test needs bit-exact scores of row-major rows; the only mixed-page score test uses float queries (`host` executor). Mutation checks M1 (completion comparison), M2 (hardware policy) and M3 (removing the forward's conversion call) must keep failing their cases.

## Change 1: the loop (self_attention.hpp)

Before the token loop, on a VNNI slot: no dotters, no optional, no block-mask read. The per-token body for a VNNI slot is `live |= k_vnni::offset_bit(i)` and nothing else (as PR #4898). The row-major slot path keeps its dotters (built per visit, as before) and its row view.

After the loop, VNNI slot only:

```
if (live != 0) {
  const auto plane = page.template k_packed<geometry.kv>(slot, kv_head);
  const uint64_t vnni_tokens = k_vnni::block_token_mask(k_blocks);   // 4 block bits -> 64 token bits
  if (const uint64_t in_vnni = live & vnni_tokens; in_vnni != 0) {
    k_vnni::qk_group<operation_kv_mul>(plane, q.data + kv_head * operation_kv_mul * operation_head_size, in_vnni, &s_pages[0][0], page::page_size);
  }
  if (uint64_t rows = live & ~vnni_tokens; rows != 0) {
    // The rows of the page's row-major blocks (Note [Row-major tail block]):
    // the row-major dotters, built only here.
    const auto dot_q = make_dot_q();   // the existing pack expansion over kv_mul heads
    for (; rows != 0; rows &= rows - 1) {
      const size_t i = size_t(std::countr_zero(rows));
      const auto k = row_major_row(plane, i);
      for (size_t offset = 0; offset < operation_kv_mul; ++offset) s_pages[offset][i] = dot_q[offset](k);
    }
  }
}
```

`k_vnni::block_token_mask(uint8_t blocks)` is a constexpr function in `h/tron/tensor/k_vnni.hpp` next to `block_bit` and `offset_bit`: a 16-entry table (or 4 conditional ors) mapping block bit c to the 16 token bits 16c..16c+15, with a static_assert on two entries. The dotter arithmetic for row-major rows is unchanged (the same dotter objects), so a row's score is bit-identical to PR #4901's.

`plane` is fetched only when `live != 0`, as PR #4898 fetched it when `relevant_k_tokens > 0`: a page nothing is relevant for is never asked for its plane.

## Change 2: the block mask once per page (self_attention.hpp)

`apply_page_range` reads `k_blocks = page.k_vnni_blocks<geometry.kv>(slot)` once per page before its query loop (VNNI slots only; `BLOCKS_PER_PAGE_MASK_0XF` for a row-major slot, where no state exists) and passes it to `apply_page_tok` as a new argument. The dense AMX gate becomes `k_blocks == k_vnni::BLOCKS_PER_PAGE_MASK_0XF` (no per-visit atomic load; the lambda `k_layout_dense` goes away). Question for the panel: is reading `k_vnni_blocks` for a page before knowing that any token is relevant safe (the state lives in the page struct, arrays sized n_slots + 1; the old comment says "a page nothing is relevant for is never asked for its state (a book may have no active KV slot)")? If not, read it lazily at the first visit of the page inside the query loop.

## Change 3: the conversion on the pool (model.hpp)

```
void convert_pending_k_blocks() noexcept {
  if (pending_k_blocks_.empty()) return;
  TRACE_EVENT("model", "convert_k_blocks", "blocks", pending_k_blocks_.size());
  // One block may be queued twice (a row re-saved into a complete, unconverted
  // block). Two workers must not convert one block at once: drop the duplicates.
  sort + unique on (pg, storage.offset, storage.state_ix, block)
  thread_pool& tp = app_pool();
  if (pending_k_blocks_.size() < k_convert_parallel_min || tp.num_workers() == 0) {
    serial loop (as now)
  } else {
    tp.parallel_for(size_t{0}, pending_k_blocks_.size(), [&](size_t i) { b = pending_k_blocks_[i]; b.pg->k_block_to_vnni_at(b.storage, b.block); });
  }
  pending_k_blocks_.clear();
}
```

`k_convert_parallel_min` is a named constant (8 est.). The call stays at the forward end (after `wait_for_coop_gof`, before logit delivery), so Note [K VNNI storage]'s ordering and the three mutation checks stay as they are. The unit tests that call `convert_pending_k_blocks()` from the test thread queue few blocks and take the serial branch.

## Change 4 (optional): skip the recording loop when no row went through set_k_row (model.hpp)

`store_k_block` counts the rows it stored row by row (short runs) and returns the count; the unshared path uses it directly; the shared path adds it into a new `std::atomic<uint32_t> short_rows` of the K store window (reset by main when it opens the window, added by a worker only when its count is non-zero, read by main after the join). When the count is zero the per-item `note_k_row_saved` loop is skipped. In a whole-block prefill (1024 items per minibatch) the loop never runs; in decode it runs over the 8 items as now.

## What the design does not change

- The storage policy: short runs row-major, whole blocks VNNI, conversion at the forward end, no conversion under hardware-scored operations (issue #4500 gains kept).
- The AMX kernel, the reader, the FPGA staging, the page copies, k_forget_row, the EAGLE view.
- Numerics: VNNI blocks through the reader, row-major rows through the dotter, as PR #4901.

## Measurement plan

Cells: qwen-3-4b, 8 users, 256 generated tokens, CPU attention tp2 prompt 1024, tp2 prompt 8192, tp4 prompt 1024; arms head/headoff (PR #4898), new/newoff (PR #4901), fix/fixoff (this branch), 3 repetitions; FPGA attention tp2 and tp4 prompt 1024 with head/new/fix. Pass rule: fixoff vs headoff inside the band in TPS and TTFT in every cell; fix vs new inside the band or better; fix vs head inside the band or better under FPGA.

## Open questions for the panel

1. Is change 2's early read safe for a page without an active slot? (See above.)
2. Does `parallel_for`'s one-task-per-worker shape cost more than it saves for 36 entries (one user completing)? Alternative: enqueue ceil(n / 8) tasks to the first workers with a latch.
3. Should the conversion overlap logit delivery (enqueue first, join before `q_batches.clear()`) instead of a synchronous join?
4. Is the dedupe needed, or can `k_block_to_vnni_at` claim a block atomically (a CAS on the block bit before the transpose would set the bit before the bytes are VNNI: wrong for readers; a separate claim bit would be new state)?
5. Which tests to add: a bit-exact check that the new post-loop row scoring equals the dotter for bf16 and float queries on a mixed page; a case that queues more than `k_convert_parallel_min` blocks so the parallel branch runs under the fake device.
