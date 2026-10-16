#!/usr/bin/env python3
"""resolve.py <worktree>: resolve the five conflict blocks of `git apply --3way ref/T-4737-merge.diff`
on the PR-3 head dfafd13dce (PR4-handoff.md step 1), by exact text. Each conflict block must be present
exactly once with exactly the expected "ours" and "theirs" sides; otherwise the script fails and changes
nothing in that file. After the blocks, two exact-text additions put the patch's block checks after each of
PR-3's two shared saves. Written 2026-10-12 from the probe apply (handoff-material/probe-pr4/conflicts.txt).

"ours" = the PR-3 head text (dfafd13dce: PR-1's review fixes, PR-2's and PR-3's comment wording, PR-3's
step-5 test rewrite and its review-fix commit dfafd13dce). "theirs" = the patch's text (9d5c7a389b, the
PR 4737 merge). The resolution keeps the patch's content and the stack's wording where the patch did not
know it."""
import pathlib
import sys

W = pathlib.Path(sys.argv[1])

CONFLICTS = [
    (
        "h/tron/kernels/amx_attn_iface.hpp",
        # ours: PR-3's resolution of Note [QK orientation] (PR-2's panel definition, the two store paths).
        "// of the page (a panel is 16 dimension-pair rows x 16 tokens, one B tile;\n"
        "// h/tron/tensor/k_vnni.hpp) are the B operand. The tiles come out as\n"
        "// S[query][token]. No transpose is needed. The extra work moves to two places.\n"
        "// The K store scatters 64 dimension pairs per token when the token's run has\n"
        "// one token (save_k, page::set_k_row). A run of two or more consecutive tokens\n"
        "// of one block uses the block save (page::set_k_block). The software reader for\n"
        "// partial pages runs k_vnni::qk_group instead of the row-major dotter.\n",
        # theirs: the patch's text (no panel definition; the tail block).
        "// of the page are the B operand. The tiles come out as S[query][token]. No\n"
        "// transpose is needed. The cost moves to the K save. A run of 16 consecutive\n"
        "// tokens that fills one 16-token block uses the block save (page::set_k_block,\n"
        "// a register transpose and whole-line stores). A shorter run (decode: one\n"
        "// token per user per step) is stored row-major into the block's own bytes,\n"
        "// and the block is transposed in place at the end of the forward pass that\n"
        "// saved its 16th row (Note [Row-major tail block] in h/tron/tensor/k_vnni.hpp). The\n"
        "// software reader for the VNNI blocks of partial pages runs k_vnni::qk_group; the\n"
        "// row-major tail block keeps the row-major dotter.\n",
        # resolution: PR-2's panel definition and "extra work" wording, with the patch's store paths.
        "// of the page (a panel is 16 dimension-pair rows x 16 tokens, one B tile;\n"
        "// h/tron/tensor/k_vnni.hpp) are the B operand. The tiles come out as\n"
        "// S[query][token]. No transpose is needed. The extra work moves to the K save.\n"
        "// A run of 16 consecutive tokens that fills one 16-token block uses the block\n"
        "// save (page::set_k_block, a register transpose and whole-line stores). A\n"
        "// shorter run (decode: one token per user per step) is stored row-major into\n"
        "// the block's own bytes, and the block is transposed in place at the end of the\n"
        "// forward pass that saved its 16th row (Note [Row-major tail block] in\n"
        "// h/tron/tensor/k_vnni.hpp). The software reader for the VNNI blocks of partial\n"
        "// pages runs k_vnni::qk_group; the row-major tail block keeps the row-major\n"
        "// dotter.\n",
    ),
    (
        "h/tron/kernels/k_vnni.hpp",
        # ours: PR-2's reader comment (names the kernel as the other plane reader).
        "// change the result. Token lanes: one 64-byte load supplies one dimension pair\n"
        "// of 16 tokens. The query's dimension pair is broadcast. VDPBF16PS accumulates 16\n"
        "// scores at once. So there is no horizontal reduction and no per-token gather.\n"
        "// k_page is the page's packed K plane as its typed view (page::k_packed). This\n"
        "// reader is one of the two layout-specific score kernels allowed to take the\n"
        "// plane address (the other is amx_attn_h128g4::qk_vnni_128x4). q points at\n"
        "// kv_mul rows of 128 values (the group's heads, row stride 128). kv_mul is\n"
        "// any group size: a group of more than 16 heads is\n"
        "// scored 16 heads at a time. Every head's scores are its own accumulation.\n"
        "// So the split changes no head's add order.\n",
        # theirs: the patch's text (the live-bit rule of the tail block).
        "// change the result. Every token block with a live bit must hold the VNNI\n"
        "// layout (Note [Row-major tail block] in h/tron/tensor/k_vnni.hpp): the\n"
        "// caller scores the tokens of a row-major block with the row-major dotter\n"
        "// and keeps their bits clear here. Token lanes: one 64-byte load supplies\n"
        "// one dimension pair of 16 tokens. The query's dimension pair is broadcast.\n"
        "// VDPBF16PS accumulates 16 scores at once. So there is no horizontal\n"
        "// reduction and no per-token gather. k_page is the page's packed K plane as\n"
        "// its typed view (page::k_packed). This reader is one of the two\n"
        "// layout-specific readers allowed to take the plane address. q points at\n"
        "// kv_mul rows of 128 values (the group's heads, row stride 128). kv_mul is\n"
        "// any group size: a group of more than 16 heads is scored 16 heads at a\n"
        "// time. Every head's scores are its own accumulation. So the split changes\n"
        "// no head's add order.\n",
        # resolution: the patch's text with PR-2's naming of the other plane reader.
        "// change the result. Every token block with a live bit must hold the VNNI\n"
        "// layout (Note [Row-major tail block] in h/tron/tensor/k_vnni.hpp): the\n"
        "// caller scores the tokens of a row-major block with the row-major dotter\n"
        "// and keeps their bits clear here. Token lanes: one 64-byte load supplies\n"
        "// one dimension pair of 16 tokens. The query's dimension pair is broadcast.\n"
        "// VDPBF16PS accumulates 16 scores at once. So there is no horizontal\n"
        "// reduction and no per-token gather. k_page is the page's packed K plane as\n"
        "// its typed view (page::k_packed). This reader is one of the two\n"
        "// layout-specific score kernels allowed to take the plane address (the other\n"
        "// is amx_attn_h128g4::qk_vnni_128x4). q points at kv_mul rows of 128 values\n"
        "// (the group's heads, row stride 128). kv_mul is any group size: a group of\n"
        "// more than 16 heads is scored 16 heads at a time. Every head's scores are\n"
        "// its own accumulation. So the split changes no head's add order.\n",
    ),
    (
        "h/tron/models/kv_cache.hpp",
        # ours: PR-2's items 2 (tail) and 3 of Note [K VNNI storage].
        "//      read-only view of the plane, to qk_vnni_128x4.\n"
        "//   3. every other visit of a VNNI slot uses k_vnni::qk_group with the same\n"
        "//      view: partial or partly visible pages, the kill switch\n"
        "//      (TRON_AMX_DISABLE=1), hosts without AMX, builds without\n"
        "//      TRON_AMX_DISPATCH, and the shapes and query types outside the AMX\n"
        "//      gate (Note [AMX attention dispatch]). That reader is AVX-512 code\n"
        "//      with one token per vector lane. It needs no per-token gather and no\n"
        "//      horizontal reduction. The\n"
        "//      row-major dotter loop (the per-token dot-product loop of\n"
        "//      self_attention.hpp) is\n"
        "//      compiled only for row-major slots.\n",
        # theirs: the patch's items 2 (tail) and 3.
        "//      read-only view of the plane, to qk_vnni_128x4 when page::k_vnni_blocks\n"
        "//      says every block of the page is converted. A page whose last block\n"
        "//      waits for the forward end, a page with a block that stays row-major\n"
        "//      under hardware attention, or a page filled by another writer than\n"
        "//      save_k, takes the software loop.\n"
        "//   3. the software path for partial pages, the kill switch\n"
        "//      (TRON_AMX_DISABLE=1) and hosts without AMX read the VNNI blocks with\n"
        "//      k_vnni::qk_group, with the same view. That reader is AVX-512 code with\n"
        "//      one token per vector lane. It needs no per-token gather and no\n"
        "//      horizontal reduction. The tokens of the row-major tail block are\n"
        "//      scored with the row-major dotter (the per-token dot-product loop of\n"
        "//      self_attention.hpp) through their typed row (row_major_row), 4 lines\n"
        "//      per token.\n",
        # resolution: the patch's item 2, and item 3 with PR-2's list of the software visits.
        "//      read-only view of the plane, to qk_vnni_128x4 when page::k_vnni_blocks\n"
        "//      says every block of the page is converted. A page whose last block\n"
        "//      waits for the forward end, a page with a block that stays row-major\n"
        "//      under hardware attention, or a page filled by another writer than\n"
        "//      save_k, takes the software loop.\n"
        "//   3. every other visit of a VNNI slot reads the VNNI blocks with\n"
        "//      k_vnni::qk_group, with the same view: partial or partly visible\n"
        "//      pages, the kill switch (TRON_AMX_DISABLE=1), hosts without AMX,\n"
        "//      builds without TRON_AMX_DISPATCH, and the shapes and query types\n"
        "//      outside the AMX gate (Note [AMX attention dispatch]). That reader is\n"
        "//      AVX-512 code with one token per vector lane. It needs no per-token\n"
        "//      gather and no horizontal reduction. The tokens of the row-major tail\n"
        "//      block are scored with the row-major dotter (the per-token dot-product\n"
        "//      loop of self_attention.hpp) through their typed row (row_major_row),\n"
        "//      4 lines per token.\n",
    ),
    (
        "h/tron/tensor/k_vnni.hpp",
        # ours: PR-3's resolution of the file header (store_block; the reader and the kernel named).
        "// rows in and out (store_row, load_row, store_block, copy_token). The AVX-512\n"
        "// score reader of this layout is in h/tron/kernels/k_vnni.hpp and the AMX QK\n"
        "// kernel in h/tron/kernels/amx_attn_iface.hpp. Who writes and\n"
        "// reads the layout is described in Note [K VNNI storage] (kv_cache.hpp).\n",
        # theirs: the patch's header (the in-place conversion; the reader named only).
        "// rows in and out (store_row, load_row, store_block, copy_token), and the\n"
        "// in-place conversion of one 16-token block between its row-major and its VNNI\n"
        "// form (block_to_vnni, block_to_rows, Note [Row-major tail block] below). The\n"
        "// AVX-512 score reader of this layout is in h/tron/kernels/k_vnni.hpp. Who\n"
        "// writes and reads the layout is described in Note [K VNNI storage]\n"
        "// (kv_cache.hpp).\n",
        # resolution: both.
        "// rows in and out (store_row, load_row, store_block, copy_token), and the\n"
        "// in-place conversion of one 16-token block between its row-major and its VNNI\n"
        "// form (block_to_vnni, block_to_rows, Note [Row-major tail block] below). The\n"
        "// AVX-512 score reader of this layout is in h/tron/kernels/k_vnni.hpp and the\n"
        "// AMX QK kernel in h/tron/kernels/amx_attn_iface.hpp. Who writes and reads the\n"
        "// layout is described in Note [K VNNI storage] (kv_cache.hpp).\n",
    ),
    (
        "t/t_llama_unit.cpp",
        # ours: PR-3's three-thread section at dfafd13dce, from its header to the first lines of
        # check_window (the late helper, the finished count read at return, the two-argument
        # check_window).
        "  SECTION(\"three threads: the helpers share the window and every row is stored once\") {\n"
        "    bk.fill_random(gen);\n"
        "    constexpr size_t n_workers = 3;\n"
        "    constexpr size_t main_worker_ix = 0;\n"
        "    // Every worker calls the same save_k with its own index (Note [Shared\n"
        "    // block save] in model.hpp). The last helper starts late, so the main\n"
        "    // thread's join has to wait for it. The finished count is read as the main\n"
        "    // call returns, before this test joins its threads: the production join,\n"
        "    // not the test's joins, must have seen every helper finish.\n"
        "    constexpr std::chrono::milliseconds late_helper_delay{20};\n"
        "    auto shared_save = [&](attention_operation_descriptor const& op) {\n"
        "      std::vector<std::thread> helpers;\n"
        "      for (size_t worker_ix = 1; worker_ix < n_workers; ++worker_ix) {\n"
        "        helpers.emplace_back([&, worker_ix] {\n"
        "          if (worker_ix == n_workers - 1)\n"
        "            std::this_thread::sleep_for(late_helper_delay);\n"
        "          state.template save_k<geometry>(\n"
        "              &q_batch, op, state.plugin_state.kouts, worker_ix, n_workers);\n"
        "        });\n"
        "      }\n"
        "      state.template save_k<geometry>(\n"
        "          &q_batch, op, state.plugin_state.kouts, main_worker_ix, n_workers);\n"
        "      const uint32_t finished_at_return = q_batch.k_store_window.finished.load();\n"
        "      for (auto& h : helpers) {\n"
        "        h.join();\n"
        "      }\n"
        "      return finished_at_return;\n"
        "    };\n"
        "    // The job's token position, its KV flag, its page and its 16-token block.\n"
        "    auto token_of = [&](size_t item) { return job_tokens[q_batch.items[item].i].i; };\n"
        "    auto kv_of = [&](size_t item) { return do_kv[q_batch.items[item].i] != 0; };\n"
        "    auto block_of = [&](size_t tok) {\n"
        "      return (tok % page_t::page_size) / k_vnni::BLOCK_TOKENS_16;\n"
        "    };\n"
        "    // The window state after the n_windows-th shared save on this batch.\n"
        "    // finished_at_return is the finished count when the main call returned.\n"
        "    [[maybe_unused]] auto check_window = [&](uint32_t n_windows,\n"
        "                                             uint32_t finished_at_return) {\n",
        # theirs: the patch's two hardware-attention sections, then its own three-thread section
        # (inline helper threads, the checks after the join, the start of its window checks).
        "  // Note [Row-major blocks under hardware attention] in kv_cache.hpp: the rows\n"
        "  // land the same way; only the row bits and the forward-end conversion of the\n"
        "  // hardware-scored operation are skipped. Catch2 builds a fresh state for\n"
        "  // every SECTION, so the flag needs no reset.\n"
        "  constexpr uint8_t operation_uses_hw = 1;\n"
        "  SECTION(\"hardware attention scores the operation: the completed block stays \"\n"
        "          \"row-major, the whole-block save is still VNNI\") {\n"
        "    bk.fill_random(gen);\n"
        "    pre_save();\n"
        "    state.attention_operation_uses_hw[operation.binding.operation.i] =\n"
        "        operation_uses_hw;\n"
        "    const auto before = snapshot();\n"
        "    state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts);\n"
        "    check(before);\n"
        "    check_marks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    state.convert_pending_k_blocks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    check(before);\n"
        "  }\n"
        "\n"
        "  SECTION(\"hardware attention scores another operation: this one still converts\") {\n"
        "    // The flag is read for the saving operation, not for another id space\n"
        "    // (operation 0 is also layer 0 and KV slot 0; operation 1 is not).\n"
        "    bk.fill_random(gen);\n"
        "    pre_save();\n"
        "    constexpr size_t other_operation = 1;\n"
        "    const attention_op_id other =\n"
        "        state.active_attention_operations[other_operation].binding.operation;\n"
        "    REQUIRE(other != operation.binding.operation);\n"
        "    state.attention_operation_uses_hw[other.i] = operation_uses_hw;\n"
        "    const auto before = snapshot();\n"
        "    state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts);\n"
        "    check(before);\n"
        "    check_marks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    state.convert_pending_k_blocks();\n"
        "    check_blocks(/*converted=*/true);\n"
        "    check(before);\n"
        "  }\n"
        "\n"
        "  SECTION(\"three threads: the helpers share the window and every row lands once\") {\n"
        "    bk.fill_random(gen);\n"
        "    pre_save();\n"
        "    const auto before = snapshot();\n"
        "    constexpr size_t n_workers = 3;\n"
        "    constexpr size_t main_worker_ix = 0;\n"
        "    // Every worker calls the same save_k with its own index (Note [Shared\n"
        "    // block save] in model.hpp).\n"
        "    std::vector<std::thread> helpers;\n"
        "    for (size_t worker_ix = 1; worker_ix < n_workers; ++worker_ix) {\n"
        "      helpers.emplace_back([&, worker_ix] {\n"
        "        state.template save_k<geometry>(\n"
        "            &q_batch, operation, state.plugin_state.kouts, worker_ix, n_workers);\n"
        "      });\n"
        "    }\n"
        "    state.template save_k<geometry>(\n"
        "        &q_batch, operation, state.plugin_state.kouts, main_worker_ix, n_workers);\n"
        "    for (auto& h : helpers) {\n"
        "      h.join();\n"
        "    }\n"
        "    check(before);\n"
        "    check_marks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    state.convert_pending_k_blocks();\n"
        "    check_blocks(/*converted=*/true);\n"
        "    check(before);\n"
        "    if constexpr (k_vnni::layout_on<head_size>) {\n",
        # resolution: the patch's two sections verbatim, then PR-3's section header with pre_save()
        # and PR-3's lambdas unchanged. The patch's checks after the join are added after each of
        # PR-3's two shared saves by the EDITS below (outside this block).
        "  // Note [Row-major blocks under hardware attention] in kv_cache.hpp: the rows\n"
        "  // land the same way; only the row bits and the forward-end conversion of the\n"
        "  // hardware-scored operation are skipped. Catch2 builds a fresh state for\n"
        "  // every SECTION, so the flag needs no reset.\n"
        "  constexpr uint8_t operation_uses_hw = 1;\n"
        "  SECTION(\"hardware attention scores the operation: the completed block stays \"\n"
        "          \"row-major, the whole-block save is still VNNI\") {\n"
        "    bk.fill_random(gen);\n"
        "    pre_save();\n"
        "    state.attention_operation_uses_hw[operation.binding.operation.i] =\n"
        "        operation_uses_hw;\n"
        "    const auto before = snapshot();\n"
        "    state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts);\n"
        "    check(before);\n"
        "    check_marks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    state.convert_pending_k_blocks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    check(before);\n"
        "  }\n"
        "\n"
        "  SECTION(\"hardware attention scores another operation: this one still converts\") {\n"
        "    // The flag is read for the saving operation, not for another id space\n"
        "    // (operation 0 is also layer 0 and KV slot 0; operation 1 is not).\n"
        "    bk.fill_random(gen);\n"
        "    pre_save();\n"
        "    constexpr size_t other_operation = 1;\n"
        "    const attention_op_id other =\n"
        "        state.active_attention_operations[other_operation].binding.operation;\n"
        "    REQUIRE(other != operation.binding.operation);\n"
        "    state.attention_operation_uses_hw[other.i] = operation_uses_hw;\n"
        "    const auto before = snapshot();\n"
        "    state.template save_k<geometry>(&q_batch, operation, state.plugin_state.kouts);\n"
        "    check(before);\n"
        "    check_marks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    state.convert_pending_k_blocks();\n"
        "    check_blocks(/*converted=*/true);\n"
        "    check(before);\n"
        "  }\n"
        "\n"
        "  SECTION(\"three threads: the helpers share the window and every row is stored once\") {\n"
        "    bk.fill_random(gen);\n"
        "    pre_save();\n"
        "    constexpr size_t n_workers = 3;\n"
        "    constexpr size_t main_worker_ix = 0;\n"
        "    // Every worker calls the same save_k with its own index (Note [Shared\n"
        "    // block save] in model.hpp). The last helper starts late, so the main\n"
        "    // thread's join has to wait for it. The finished count is read as the main\n"
        "    // call returns, before this test joins its threads: the production join,\n"
        "    // not the test's joins, must have seen every helper finish.\n"
        "    constexpr std::chrono::milliseconds late_helper_delay{20};\n"
        "    auto shared_save = [&](attention_operation_descriptor const& op) {\n"
        "      std::vector<std::thread> helpers;\n"
        "      for (size_t worker_ix = 1; worker_ix < n_workers; ++worker_ix) {\n"
        "        helpers.emplace_back([&, worker_ix] {\n"
        "          if (worker_ix == n_workers - 1)\n"
        "            std::this_thread::sleep_for(late_helper_delay);\n"
        "          state.template save_k<geometry>(\n"
        "              &q_batch, op, state.plugin_state.kouts, worker_ix, n_workers);\n"
        "        });\n"
        "      }\n"
        "      state.template save_k<geometry>(\n"
        "          &q_batch, op, state.plugin_state.kouts, main_worker_ix, n_workers);\n"
        "      const uint32_t finished_at_return = q_batch.k_store_window.finished.load();\n"
        "      for (auto& h : helpers) {\n"
        "        h.join();\n"
        "      }\n"
        "      return finished_at_return;\n"
        "    };\n"
        "    // The job's token position, its KV flag, its page and its 16-token block.\n"
        "    auto token_of = [&](size_t item) { return job_tokens[q_batch.items[item].i].i; };\n"
        "    auto kv_of = [&](size_t item) { return do_kv[q_batch.items[item].i] != 0; };\n"
        "    auto block_of = [&](size_t tok) {\n"
        "      return (tok % page_t::page_size) / k_vnni::BLOCK_TOKENS_16;\n"
        "    };\n"
        "    // The window state after the n_windows-th shared save on this batch.\n"
        "    // finished_at_return is the finished count when the main call returned.\n"
        "    [[maybe_unused]] auto check_window = [&](uint32_t n_windows,\n"
        "                                             uint32_t finished_at_return) {\n",
    ),
]

# The patch's checks after the join, re-applied on PR-3's two shared saves (outside the conflict
# block; each old text occurs exactly once at the resolved tree).
EDITS = [
    (
        "t/t_llama_unit.cpp",
        "    const auto before = snapshot();\n"
        "    const uint32_t finished_0 = shared_save(operation);\n"
        "    check(before);\n"
        "    if constexpr (k_vnni::layout_on<head_size>) {\n"
        "      check_window(1, finished_0);\n",
        "    const auto before = snapshot();\n"
        "    const uint32_t finished_0 = shared_save(operation);\n"
        "    check(before);\n"
        "    check_marks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    state.convert_pending_k_blocks();\n"
        "    check_blocks(/*converted=*/true);\n"
        "    check(before);\n"
        "    if constexpr (k_vnni::layout_on<head_size>) {\n"
        "      check_window(1, finished_0);\n",
    ),
    (
        "t/t_llama_unit.cpp",
        "    slot = operation_1.binding.kv_slot;\n"
        "    const auto before_1 = snapshot();\n"
        "    const uint32_t finished_1 = shared_save(operation_1);\n"
        "    check(before_1);\n"
        "    if constexpr (k_vnni::layout_on<head_size>) {\n"
        "      check_window(2, finished_1);\n",
        "    slot = operation_1.binding.kv_slot;\n"
        "    pre_save();\n"
        "    const auto before_1 = snapshot();\n"
        "    const uint32_t finished_1 = shared_save(operation_1);\n"
        "    check(before_1);\n"
        "    check_marks();\n"
        "    check_blocks(/*converted=*/false);\n"
        "    state.convert_pending_k_blocks();\n"
        "    check_blocks(/*converted=*/true);\n"
        "    check(before_1);\n"
        "    if constexpr (k_vnni::layout_on<head_size>) {\n"
        "      check_window(2, finished_1);\n",
    ),
]

rc = 0
for f, ours, theirs, res in CONFLICTS:
    p = W / f
    s = p.read_text()
    block = "<<<<<<< ours\n" + ours + "=======\n" + theirs + ">>>>>>> theirs\n"
    n = s.count(block)
    if n != 1:
        print(f"FAIL {f}: expected conflict block found {n} times")
        rc = 1
        continue
    s = s.replace(block, res)
    p.write_text(s)
    width = max((len(l) for l in res.splitlines()), default=0)
    print(f"ok   {f}: resolved ({len(res.splitlines())} lines, widest {width} columns)")
for f in sorted({c[0] for c in CONFLICTS}):
    left = [l for l in (W / f).read_text().splitlines() if l.startswith(("<<<<<<<", "=======", ">>>>>>>"))]
    if left:
        print(f"FAIL {f}: {len(left)} conflict marker lines left")
        rc = 1
if rc == 0:
    for f, old, new in EDITS:
        p = W / f
        s = p.read_text()
        n = s.count(old)
        if n != 1:
            print(f"FAIL {f}: edit text found {n} times")
            rc = 1
            continue
        p.write_text(s.replace(old, new))
        print(f"ok   {f}: edit applied ({len(new.splitlines()) - len(old.splitlines())} lines added)")
sys.exit(rc)
