import pathlib, sys

ROOT = pathlib.Path("/home/jhan/workspace/ai-runs/tron-vnnik-sync")

def edit(path, pairs):
    p = ROOT / path
    s = p.read_text()
    for old, new, count in pairs:
        n = s.count(old)
        assert n == count, f"{path}: expected {count} of {old!r}, found {n}"
        s = s.replace(old, new)
    p.write_text(s)
    print("edited", path, len(pairs), "replacements")

# ---------------- model.hpp ----------------
edit("h/tron/models/model.hpp", [
    ("    // (K_JOIN_TIMEOUT_S_120 after the first clock read) aborts with the\n",
     "    // (k_join_timeout_s after the first clock read) aborts with the\n", 1),
    ("    static constexpr size_t K_STORE_BLOCK_16 = k_vnni::BLOCK_TOKENS_16;\n"
     "    static_assert(K_STORE_BLOCK_16 == 16, \"the constant's name states its value\");\n",
     "    static constexpr size_t k_store_block = k_vnni::BLOCK_TOKENS_16;\n", 1),
    ("    static constexpr size_t K_SCATTER_RUN_LEN_1 = 1;\n",
     "    static constexpr size_t k_scatter_run_len = 1;\n", 1),
    ("    // every K_JOIN_CLOCK_SPINS_1048576 pause loops. It aborts\n"
     "    // K_JOIN_TIMEOUT_S_120 seconds after the first clock read.\n"
     "    static constexpr uint64_t K_JOIN_CLOCK_SPINS_1048576 = 1048576;  // 2^20\n"
     "    static_assert((K_JOIN_CLOCK_SPINS_1048576 & (K_JOIN_CLOCK_SPINS_1048576 - 1)) == 0,\n",
     "    // every k_join_clock_spins pause loops. It aborts k_join_timeout_s seconds\n"
     "    // after the first clock read.\n"
     "    static constexpr uint64_t k_join_clock_spins = 1048576;  // 2^20\n"
     "    static_assert((k_join_clock_spins & (k_join_clock_spins - 1)) == 0,\n", 1),
    ("    static constexpr int K_JOIN_TIMEOUT_S_120 = 120;\n",
     "    static constexpr int k_join_timeout_s = 120;\n", 1),
    ("K_STORE_BLOCK_16", "k_store_block", 12),
    ("K_SCATTER_RUN_LEN_1", "k_scatter_run_len", 1),
    ("K_JOIN_CLOCK_SPINS_1048576", "k_join_clock_spins", 1),
    ("K_JOIN_TIMEOUT_S_120", "k_join_timeout_s", 2),
])

# ---------------- t_llama_unit.cpp ----------------
edit("t/t_llama_unit.cpp", [
    # typed-slots test: the two-slot K row block
    ("    using k_vnni::HEAD_SIZE_128;  // the head size of book_t\n"
     "    alignas(64) std::array<bf16, HEAD_SIZE_128> ones, twos, got;\n"
     "    ones.fill(static_cast<bf16>(1.0f));\n"
     "    twos.fill(static_cast<bf16>(2.0f));\n"
     "    page->set_k_row(slot_0, 0, 0, k_source_row<HEAD_SIZE_128>(ones.data()));\n"
     "    page->set_k_row(slot_1, 0, 0, k_source_row<HEAD_SIZE_128>(twos.data()));\n"
     "    page->get_k_row(slot_0, 0, 0, k_destination_row<HEAD_SIZE_128>(got.data()));\n"
     "    REQUIRE(got == ones);\n"
     "    page->get_k_row(slot_1, 0, 0, k_destination_row<HEAD_SIZE_128>(got.data()));\n",
     "    constexpr size_t head_size = 128;  // the head size of book_t\n"
     "    alignas(64) std::array<bf16, head_size> ones, twos, got;\n"
     "    ones.fill(static_cast<bf16>(1.0f));\n"
     "    twos.fill(static_cast<bf16>(2.0f));\n"
     "    page->set_k_row(slot_0, 0, 0, k_source_row<head_size>(ones.data()));\n"
     "    page->set_k_row(slot_1, 0, 0, k_source_row<head_size>(twos.data()));\n"
     "    page->get_k_row(slot_0, 0, 0, k_destination_row<head_size>(got.data()));\n"
     "    REQUIRE(got == ones);\n"
     "    page->get_k_row(slot_1, 0, 0, k_destination_row<head_size>(got.data()));\n", 1),
    # EAGLE test
    ("  using k_vnni::HEAD_SIZE_128;  // the head size of book_t\n"
     "  alignas(64) std::array<bf16, HEAD_SIZE_128> k_row{}, got{};\n"
     "  k_row[0] = static_cast<bf16>(1.0f);\n"
     "  page->set_k_row(slot, 0, 0, k_source_row<HEAD_SIZE_128>(k_row.data()));\n",
     "  constexpr size_t head_size = 128;  // the head size of book_t\n"
     "  alignas(64) std::array<bf16, head_size> k_row{}, got{};\n"
     "  k_row[0] = static_cast<bf16>(1.0f);\n"
     "  page->set_k_row(slot, 0, 0, k_source_row<head_size>(k_row.data()));\n", 1),
    ("  k_row[0] = static_cast<bf16>(2.0f);\n"
     "  page->set_k_row(slot, 0, 0, k_source_row<HEAD_SIZE_128>(k_row.data()));\n"
     "\n"
     "  cache.reset_storage_view();\n"
     "  page->get_k_row(slot, 0, 0, k_destination_row<HEAD_SIZE_128>(got.data()));\n"
     "  REQUIRE(float(got[0]) == 1.0f);\n"
     "  REQUIRE(page->is_kv_complete(slot, 0));\n"
     "\n"
     "  cache.set_storage_view(cache.eagle_storage_offset());\n"
     "  page->get_k_row(slot, 0, 0, k_destination_row<HEAD_SIZE_128>(got.data()));\n",
     "  k_row[0] = static_cast<bf16>(2.0f);\n"
     "  page->set_k_row(slot, 0, 0, k_source_row<head_size>(k_row.data()));\n"
     "\n"
     "  cache.reset_storage_view();\n"
     "  page->get_k_row(slot, 0, 0, k_destination_row<head_size>(got.data()));\n"
     "  REQUIRE(float(got[0]) == 1.0f);\n"
     "  REQUIRE(page->is_kv_complete(slot, 0));\n"
     "\n"
     "  cache.set_storage_view(cache.eagle_storage_offset());\n"
     "  page->get_k_row(slot, 0, 0, k_destination_row<head_size>(got.data()));\n", 1),

    # ---- 32-head case ----
    ("  using k_vnni::HEAD_SIZE_128;\n"
     "  constexpr size_t N_HEADS_32 = 32;\n"
     "  constexpr size_t N_KV_HEADS_1 = 1;\n"
     "  constexpr size_t DIM_4096 = N_HEADS_32 * HEAD_SIZE_128;\n"
     "  constexpr size_t HIDDEN_DIM_1024 = 1024;\n"
     "  constexpr size_t N_LAYERS_1 = 1;\n"
     "  constexpr size_t VOCAB_SIZE_32000 = 32000;\n"
     "  constexpr size_t N_EXPERTS_1 = 1;\n"
     "  constexpr size_t N_SHARED_EXPERTS_1 = 1;\n"
     "  // The attention scale 1 / sqrt(128), as a hex float.\n"
     "  constexpr float ATTENTION_SCALE_0X1_6A09E6P_MINUS_4F = 0x1.6a09e6p-4f;\n"
     "  static_assert(DIM_4096 == 4096, \"the constant's name states its value\");\n"
     "  constexpr attention_geometry geometry{\n"
     "      N_HEADS_32, kv_geometry{N_KV_HEADS_1, HEAD_SIZE_128}};\n"
     "  static_assert(geometry.kv_mul() == N_HEADS_32, \"32 query heads share the K/V head\");\n"
     "  constexpr llm_configuration llm_config{.type = model_type::llama,\n"
     "      .dim = DIM_4096,\n"
     "      .hidden_dim = HIDDEN_DIM_1024,\n"
     "      .n_layers = N_LAYERS_1,\n"
     "      .n_heads = N_HEADS_32,\n"
     "      .n_kv_heads = N_KV_HEADS_1,\n"
     "      .vocab_size = VOCAB_SIZE_32000,\n"
     "      .head_size = HEAD_SIZE_128,\n"
     "      .attention_scale = ATTENTION_SCALE_0X1_6A09E6P_MINUS_4F,\n"
     "      .n_experts = N_EXPERTS_1,\n"
     "      .n_shared_experts = N_SHARED_EXPERTS_1,\n",
     "  constexpr size_t head_size = 128;\n"
     "  constexpr size_t n_heads = 32;\n"
     "  constexpr size_t n_kv_heads = 1;\n"
     "  constexpr float attention_scale = 0x1.6a09e6p-4f;  // 1 / sqrt(128)\n"
     "  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};\n"
     "  static_assert(geometry.kv_mul() == n_heads, \"32 query heads share the K/V head\");\n"
     "  constexpr llm_configuration llm_config{.type = model_type::llama,\n"
     "      .dim = n_heads * head_size,\n"
     "      .hidden_dim = 1024,\n"
     "      .n_layers = 1,\n"
     "      .n_heads = n_heads,\n"
     "      .n_kv_heads = n_kv_heads,\n"
     "      .vocab_size = 32000,\n"
     "      .head_size = head_size,\n"
     "      .attention_scale = attention_scale,\n"
     "      .n_experts = 1,\n"
     "      .n_shared_experts = 1,\n", 1),
    ("  state_t state(*model, model_config{.max_layers = N_LAYERS_1});\n"
     "  constexpr size_t N_Q_TOKENS_1 = 1;\n"
     "  state.resize(N_Q_TOKENS_1);\n"
     "  constexpr size_t N_PAGES_1 = 1;\n"
     "  book_t cache(N_PAGES_1, N_LAYERS_1);\n",
     "  state_t state(*model, model_config{.max_layers = 1});\n"
     "  state.resize(1);  // one query token\n"
     "  book_t cache(1, 1);\n", 1),
    ("  std::array<page_t*, N_PAGES_1> pages{page};\n",
     "  std::array<page_t*, 1> pages{page};\n", 1),
    ("  constexpr bool WRITES_KV_TRUE = true;\n"
     "  const attention_operation_descriptor operation{\n"
     "      {attention_op_id(0), model_layer_id(0), kv_slot_id(0)}, attention_kernel_id(0),\n"
     "      attention_hardware_capability::software_only, WRITES_KV_TRUE,\n"
     "      attention_operation_config{\n"
     "          std::nullopt, std::nullopt, ATTENTION_SCALE_0X1_6A09E6P_MINUS_4F}};\n",
     "  const attention_operation_descriptor operation{\n"
     "      {attention_op_id(0), model_layer_id(0), kv_slot_id(0)}, attention_kernel_id(0),\n"
     "      attention_hardware_capability::software_only, true,\n"
     "      attention_operation_config{std::nullopt, std::nullopt, attention_scale}};\n", 1),
    ("  constexpr int SLIDING_WINDOW_1024 = 1024;\n"
     "  constexpr bool WAS_VALID_FALSE = false;\n"
     "  constexpr bool RUN_VISIBLE_IN_SOFTWARE_FALSE = false;\n"
     "  auto const result =\n"
     "      state.self_attn_state.apply_page_tok<geometry>(WAS_VALID_FALSE, *page, operation,\n"
     "          ATTENTION_SCALE_0X1_6A09E6P_MINUS_4F, 0, q, token_id(page_t::page_size),\n"
     "          scratch, token_job_id(0), &mask.find_range(token_id(0)), SLIDING_WINDOW_1024,\n"
     "          RUN_VISIBLE_IN_SOFTWARE_FALSE, nullptr);\n",
     "  // Arguments as in check_page_range_reductions: not was_valid, sliding\n"
     "  // window 1024, not run_visible_in_software.\n"
     "  auto const result = state.self_attn_state.apply_page_tok<geometry>(false, *page,\n"
     "      operation, attention_scale, 0, q, token_id(page_t::page_size), scratch,\n"
     "      token_job_id(0), &mask.find_range(token_id(0)), 1024, false, nullptr);\n", 1),

    # ---- save_k case ----
    ("  using k_vnni::HEAD_SIZE_128;\n"
     "  constexpr size_t N_HEADS_16 = 16;\n"
     "  constexpr size_t DIM_2048 = HEAD_SIZE_128 * N_HEADS_16;\n"
     "  constexpr size_t HIDDEN_DIM_1024 = 1024;\n"
     "  constexpr size_t N_LAYERS_2 = 2;\n"
     "  constexpr size_t N_KV_HEADS_8 = 8;\n"
     "  constexpr size_t VOCAB_SIZE_32000 = 32000;\n"
     "  // The attention scale 1 / sqrt(128), as a hex float.\n"
     "  constexpr float ATTENTION_SCALE_0X1_6A09E6P_MINUS_4F = 0x1.6a09e6p-4f;\n"
     "  static_assert(DIM_2048 == 2048, \"the constant's name states its value\");\n"
     "  constexpr attention_geometry geometry{\n"
     "      N_HEADS_16, kv_geometry{N_KV_HEADS_8, HEAD_SIZE_128}};\n"
     "  constexpr llm_configuration llm_config{.type = model_type::llama,\n"
     "      .dim = DIM_2048,\n"
     "      .hidden_dim = HIDDEN_DIM_1024,\n"
     "      .n_layers = N_LAYERS_2,\n"
     "      .n_heads = N_HEADS_16,\n"
     "      .n_kv_heads = N_KV_HEADS_8,\n"
     "      .vocab_size = VOCAB_SIZE_32000,\n"
     "      .head_size = HEAD_SIZE_128,\n"
     "      .attention_scale = ATTENTION_SCALE_0X1_6A09E6P_MINUS_4F,\n",
     "  constexpr size_t head_size = 128;\n"
     "  constexpr size_t n_heads = 16;\n"
     "  constexpr size_t n_layers = 2;\n"
     "  constexpr size_t n_kv_heads = 8;\n"
     "  constexpr attention_geometry geometry{n_heads, kv_geometry{n_kv_heads, head_size}};\n"
     "  constexpr llm_configuration llm_config{.type = model_type::llama,\n"
     "      .dim = head_size * n_heads,\n"
     "      .hidden_dim = 1024,\n"
     "      .n_layers = n_layers,\n"
     "      .n_heads = n_heads,\n"
     "      .n_kv_heads = n_kv_heads,\n"
     "      .vocab_size = 32000,\n"
     "      .head_size = head_size,\n"
     "      .attention_scale = 0x1.6a09e6p-4f,  // 1 / sqrt(128)\n", 1),
    ("  constexpr size_t NUM_PAGES_3 = 3;\n"
     "  constexpr size_t NUM_KV_TOKENS_192 = NUM_PAGES_3 * page_t::page_size;\n"
     "  static_assert(NUM_KV_TOKENS_192 == 192, \"the constant's name states its value\");\n"
     "  constexpr uint32_t SEED_23 = 23;\n"
     "  std::mt19937 gen(SEED_23);\n"
     "  book_t bk(NUM_PAGES_3, N_LAYERS_2);\n"
     "  std::vector<page_t*> pages;\n"
     "  std::vector<page_t*> token_pages(NUM_KV_TOKENS_192);\n"
     "  for (size_t i = 0; i < NUM_PAGES_3; ++i) {\n",
     "  constexpr size_t num_pages = 3;\n"
     "  constexpr size_t num_kv_tokens = num_pages * page_t::page_size;\n"
     "  std::mt19937 gen(23);\n"
     "  book_t bk(num_pages, n_layers);\n"
     "  std::vector<page_t*> pages;\n"
     "  std::vector<page_t*> token_pages(num_kv_tokens);\n"
     "  for (size_t i = 0; i < num_pages; ++i) {\n", 1),
    ("  for (size_t tok = 0; tok < NUM_KV_TOKENS_192; ++tok) {\n"
     "    token_pages[tok] = bk.page_of(tok);\n",
     "  for (size_t tok = 0; tok < num_kv_tokens; ++tok) {\n"
     "    token_pages[tok] = bk.page_of(tok);\n", 1),
    ("  // The token runs of the pass (a page holds 64 tokens, a block 16 tokens).\n"
     "  constexpr size_t FIRST_RUN_BEGIN_5 = 5;\n"
     "  constexpr size_t FIRST_RUN_END_21 = 21;\n"
     "  constexpr size_t NO_KV_TOKEN_8 = 8;\n"
     "  constexpr size_t WHOLE_BLOCK_BEGIN_48 = 48;\n"
     "  constexpr size_t WHOLE_BLOCK_END_64 = 64;\n"
     "  constexpr size_t PAGE_1_RUN_BEGIN_64 = 64;\n"
     "  constexpr size_t PAGE_1_RUN_END_72 = 72;\n"
     "  constexpr size_t LONE_TOKEN_100 = 100;\n"
     "  constexpr size_t PAGE_2_RUN_BEGIN_130 = 130;\n"
     "  constexpr size_t PAGE_2_RUN_END_136 = 136;\n"
     "  constexpr size_t TRAILING_NO_KV_TOKEN_21 = 21;\n"
     "  constexpr size_t KV_JOBS_46 = 46;  // 48 jobs minus the two without KV work\n"
     "  // Starts mid-block. Crosses blocks 0/1 of page 0. The job of token 8 has no\n"
     "  // KV work.\n"
     "  for (size_t tok = FIRST_RUN_BEGIN_5; tok < FIRST_RUN_END_21; ++tok) {\n"
     "    add(tok, tok != NO_KV_TOKEN_8);\n"
     "  }\n"
     "  // One whole block (block 3 of page 0).\n"
     "  for (size_t tok = WHOLE_BLOCK_BEGIN_48; tok < WHOLE_BLOCK_END_64; ++tok) {\n"
     "    add(tok, true);\n"
     "  }\n"
     "  // Page crossing 63 -> 64. Partial block 0 of page 1.\n"
     "  for (size_t tok = PAGE_1_RUN_BEGIN_64; tok < PAGE_1_RUN_END_72; ++tok) {\n"
     "    add(tok, true);\n"
     "  }\n"
     "  // Alone in block 2 of page 1. This case takes the per-token scatter path.\n"
     "  add(LONE_TOKEN_100, true);\n"
     "  // Page 2.\n"
     "  for (size_t tok = PAGE_2_RUN_BEGIN_130; tok < PAGE_2_RUN_END_136; ++tok) {\n"
     "    add(tok, true);\n"
     "  }\n"
     "  add(TRAILING_NO_KV_TOKEN_21, false);  // a trailing job without KV work\n"
     "  const size_t n_items = job_tokens.size();\n"
     "  REQUIRE(n_items == 48);  // more than 16. So the window can open.\n",
     "  // The token runs of the pass (a page holds 64 tokens, a block 16 tokens).\n"
     "  constexpr size_t kv_jobs = 46;  // 48 jobs minus the two without KV work\n"
     "  // Tokens 5..20: starts mid-block, crosses blocks 0/1 of page 0. The job of\n"
     "  // token 8 has no KV work.\n"
     "  for (size_t tok = 5; tok < 21; ++tok) {\n"
     "    add(tok, tok != 8);\n"
     "  }\n"
     "  // Tokens 48..63: one whole block (block 3 of page 0).\n"
     "  for (size_t tok = 48; tok < 64; ++tok) {\n"
     "    add(tok, true);\n"
     "  }\n"
     "  // Tokens 64..71: page crossing 63 -> 64, partial block 0 of page 1.\n"
     "  for (size_t tok = 64; tok < 72; ++tok) {\n"
     "    add(tok, true);\n"
     "  }\n"
     "  // Token 100: alone in block 2 of page 1. This case takes the per-token\n"
     "  // scatter path.\n"
     "  add(100, true);\n"
     "  // Tokens 130..135: page 2.\n"
     "  for (size_t tok = 130; tok < 136; ++tok) {\n"
     "    add(tok, true);\n"
     "  }\n"
     "  add(21, false);  // a trailing job without KV work\n"
     "  const size_t n_items = job_tokens.size();\n"
     "  REQUIRE(n_items == 48);  // more than 16. So the window can open.\n", 1),
    ("  state_t state(*model, model_config{.max_layers = N_LAYERS_2});\n",
     "  state_t state(*model, model_config{.max_layers = n_layers});\n", 1),
    ("  // Finite bf16 patterns per (job, element). No two rows share a pattern. A row\n"
     "  // stored at the wrong token position or in the wrong slot is then detected.\n"
     "  constexpr size_t KV_WIDTH_1024 = N_KV_HEADS_8 * HEAD_SIZE_128;\n"
     "  static_assert(KV_WIDTH_1024 == 1024, \"the constant's name states its value\");\n"
     "  constexpr uint32_t PATTERN_BASE_0X3800 = 0x3800u;\n"
     "  constexpr uint32_t PATTERN_SPAN_0X0800 = 0x0800u;\n"
     "  constexpr uint32_t JOB_STRIDE_4099 = 4099u;\n"
     "  constexpr uint32_t ELT_STRIDE_17 = 17u;\n"
     "  auto source_bits = [](size_t job, size_t elt) {\n"
     "    const size_t mix = job * JOB_STRIDE_4099 + elt * ELT_STRIDE_17;\n"
     "    return static_cast<uint16_t>(PATTERN_BASE_0X3800 + mix % PATTERN_SPAN_0X0800);\n"
     "  };\n"
     "  for (size_t job = 0; job < n_items; ++job) {\n"
     "    for (size_t elt = 0; elt < KV_WIDTH_1024; ++elt) {\n",
     "  // Finite bf16 patterns per (job, element). No two rows share a pattern. A row\n"
     "  // stored at the wrong token position or in the wrong slot is then detected.\n"
     "  // The bits are 0x3800 + (0..0x07ff): exponent field 0x70..0x7f, never 0xff.\n"
     "  // The strides 4099 and 17 spread the (job, element) pairs over that span.\n"
     "  auto source_bits = [](size_t job, size_t elt) {\n"
     "    const size_t mix = job * 4099 + elt * 17;\n"
     "    return static_cast<uint16_t>(0x3800u + mix % 0x0800u);\n"
     "  };\n"
     "  for (size_t job = 0; job < n_items; ++job) {\n"
     "    for (size_t elt = 0; elt < n_kv_heads * head_size; ++elt) {\n", 1),
    ("    std::vector<std::array<uint16_t, HEAD_SIZE_128>> rows(\n"
     "        NUM_KV_TOKENS_192 * N_KV_HEADS_8);\n"
     "    alignas(64) std::array<bf16, HEAD_SIZE_128> row;\n"
     "    for (size_t tok = 0; tok < NUM_KV_TOKENS_192; ++tok) {\n"
     "      page_t* page = bk.page_of(tok);\n"
     "      const int offset = page->offset_in_page(token_id(tok));\n"
     "      for (size_t kv_head = 0; kv_head < N_KV_HEADS_8; ++kv_head) {\n"
     "        page->get_k_row(\n"
     "            slot, kv_head, offset, k_destination_row<HEAD_SIZE_128>(row.data()));\n"
     "        for (size_t d = 0; d < HEAD_SIZE_128; ++d) {\n"
     "          rows[tok * N_KV_HEADS_8 + kv_head][d] = row[d].to_bits();\n",
     "    std::vector<std::array<uint16_t, head_size>> rows(num_kv_tokens * n_kv_heads);\n"
     "    alignas(64) std::array<bf16, head_size> row;\n"
     "    for (size_t tok = 0; tok < num_kv_tokens; ++tok) {\n"
     "      page_t* page = bk.page_of(tok);\n"
     "      const int offset = page->offset_in_page(token_id(tok));\n"
     "      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {\n"
     "        page->get_k_row(\n"
     "            slot, kv_head, offset, k_destination_row<head_size>(row.data()));\n"
     "        for (size_t d = 0; d < head_size; ++d) {\n"
     "          rows[tok * n_kv_heads + kv_head][d] = row[d].to_bits();\n", 1),
    ("  auto check = [&](std::vector<std::array<uint16_t, HEAD_SIZE_128>> const& before) {\n"
     "    constexpr int NO_JOB_MINUS_1 = -1;\n"
     "    std::vector<int> job_of_token(NUM_KV_TOKENS_192, NO_JOB_MINUS_1);\n",
     "  auto check = [&](std::vector<std::array<uint16_t, head_size>> const& before) {\n"
     "    std::vector<int> job_of_token(num_kv_tokens, -1);  // -1: no job stores it\n", 1),
    ("    for (size_t tok = 0; tok < NUM_KV_TOKENS_192; ++tok) {\n"
     "      for (size_t kv_head = 0; kv_head < N_KV_HEADS_8; ++kv_head) {\n"
     "        auto const& got = after[tok * N_KV_HEADS_8 + kv_head];\n"
     "        if (job_of_token[tok] < 0) {\n"
     "          REQUIRE(got == before[tok * N_KV_HEADS_8 + kv_head]);\n",
     "    for (size_t tok = 0; tok < num_kv_tokens; ++tok) {\n"
     "      for (size_t kv_head = 0; kv_head < n_kv_heads; ++kv_head) {\n"
     "        auto const& got = after[tok * n_kv_heads + kv_head];\n"
     "        if (job_of_token[tok] < 0) {\n"
     "          REQUIRE(got == before[tok * n_kv_heads + kv_head]);\n", 1),
    ("        for (size_t d = 0; d < HEAD_SIZE_128; ++d) {\n"
     "          const uint16_t want = source_bits(job, kv_head * HEAD_SIZE_128 + d);\n",
     "        for (size_t d = 0; d < head_size; ++d) {\n"
     "          const uint16_t want = source_bits(job, kv_head * head_size + d);\n", 1),
    ("    REQUIRE(stored == KV_JOBS_46 * N_KV_HEADS_8);\n"
     "    REQUIRE(kept == (NUM_KV_TOKENS_192 - KV_JOBS_46) * N_KV_HEADS_8);\n",
     "    REQUIRE(stored == kv_jobs * n_kv_heads);\n"
     "    REQUIRE(kept == (num_kv_tokens - kv_jobs) * n_kv_heads);\n", 1),
    ("    constexpr size_t N_WORKERS_3 = 3;\n"
     "    std::vector<std::thread> helpers;\n"
     "    for (size_t worker_ix = 1; worker_ix < N_WORKERS_3; ++worker_ix) {\n"
     "      helpers.emplace_back([&, worker_ix] {\n"
     "        state.template save_k_helper<geometry>(\n"
     "            &q_batch, operation, state.plugin_state.kouts, worker_ix, N_WORKERS_3);\n"
     "      });\n"
     "    }\n"
     "    state.template save_k<geometry>(\n"
     "        &q_batch, operation, state.plugin_state.kouts, N_WORKERS_3);\n",
     "    constexpr size_t n_workers = 3;\n"
     "    std::vector<std::thread> helpers;\n"
     "    for (size_t worker_ix = 1; worker_ix < n_workers; ++worker_ix) {\n"
     "      helpers.emplace_back([&, worker_ix] {\n"
     "        state.template save_k_helper<geometry>(\n"
     "            &q_batch, operation, state.plugin_state.kouts, worker_ix, n_workers);\n"
     "      });\n"
     "    }\n"
     "    state.template save_k<geometry>(\n"
     "        &q_batch, operation, state.plugin_state.kouts, n_workers);\n", 1),
    ("    if constexpr (k_vnni::layout_on<HEAD_SIZE_128>) {\n",
     "    if constexpr (k_vnni::layout_on<head_size>) {\n", 1),
    ("      REQUIRE(w.finished.load() == N_WORKERS_3 - 1);\n",
     "      REQUIRE(w.finished.load() == n_workers - 1);\n", 1),
])

# Final sanity: no NAME_<value> constants defined in the branch's additions remain.
s = (ROOT / "t/t_llama_unit.cpp").read_text()
import re
leftovers = sorted(set(re.findall(r"\b(?:N_[A-Z_]+_\d+|[A-Z_]+_(?:0X[0-9A-F_]+|\d+)(?:F)?)\b", s)))
print("ALLCAPS_value tokens left in t_llama_unit.cpp:", leftovers)
