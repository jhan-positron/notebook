TRON(nodiscard, inline)
std::vector<std::vector<int>> chunk_evenly(size_t n_token_jobs,
    token_batching_affinity_id const* group_ids,
    auto& state) noexcept {
  if (!n_token_jobs) return {};
  constexpr size_t max_minibatch_size =
      std::decay_t<decltype(state)>::max_minibatch_size;
  static_assert(max_minibatch_size >= minibatch_grain_size);

  // Collate tokens into groups.
  size_t n_groups =
      size_t{1} + std::max_element(group_ids, group_ids + n_token_jobs)->i;
  std::vector<std::vector<int>> groups(n_groups);
  for (size_t j = 0; j < n_token_jobs; ++j)
    groups[group_ids[j].i].push_back(j);

  // Split groups in into grains that will never be further split.
  std::vector<std::vector<int>> grains;
  for (auto& group : groups)
    for (size_t i = 0; i < group.size(); i += minibatch_grain_size) {
      size_t size = std::min(minibatch_grain_size, group.size() - i);
      grains.emplace_back(group.begin() + i, group.begin() + i + size);
    }

  // Fix grains not to split even/odd token pairs.  For any given KV page,
  // we have to keep the even and odd token offsets in the same minibatch,
  // because packed V stores them in the same SIMD values (see
  // Note [VNNI Packed V layout] in h/tron/tensor/v_vnni.hpp): `page.set_v` of the
  // odd token merges into the pair its even partner wrote, and so would race
  // with itself if different threads were to try to save the two halves of
  // such a pair separately.
  adjust_grains_for_partners(grains, state, n_token_jobs);

  // Greedily consolidate grains into chunks of roughly equal size.
  size_t target_n_chunks = (n_token_jobs + max_minibatch_size - 1) / max_minibatch_size;
  // Apply max_minibatches constraint if specified
  if (state.cfg.max_minibatches > 0 &&
      target_n_chunks > static_cast<size_t>(state.cfg.max_minibatches))
    target_n_chunks = static_cast<size_t>(state.cfg.max_minibatches);
  if (target_n_chunks == 1 && (n_groups > 1 || n_token_jobs > minibatch_grain_size) &&
      (state.cfg.max_minibatches < 0 || state.cfg.max_minibatches >= 2))
    // Split a large lone chunk in half, to enable FPGA-vs-CPU latency hiding.
    // Only do this if max_minibatches allows it (is negative/unlimited or >= 2)
    target_n_chunks = 2;
  const int target_size = (n_token_jobs + target_n_chunks - 1) / target_n_chunks;
  const int max_size = max_minibatch_size;
  std::vector<std::vector<int>> chunks;
  chunks.emplace_back(std::move(grains[0]));
  for (size_t g = 1; g < grains.size(); ++g) {
    std::vector<int> grain = std::move(grains[g]);
    int old_sz = chunks.back().size();
    int new_sz = old_sz + grain.size();
    bool grain_fits = new_sz <= max_size;
    bool good_here = std::abs(new_sz - target_size) <= std::abs(old_sz - target_size);
    bool hit_chunk_limit = chunks.size() == (uint64_t)state.cfg.max_minibatches;
    if ((grain_fits && good_here) || hit_chunk_limit)
      chunks.back().insert(chunks.back().end(), grain.begin(), grain.end());
    else
      chunks.emplace_back(std::move(grain));
  }

  // Try again to split a large lone chunk, e.g. a lone prompt chunk.
  if (chunks.size() == 1 && n_token_jobs > minibatch_grain_size &&
      (state.cfg.max_minibatches < 0 || state.cfg.max_minibatches >= 2)) {
    // Only do this if max_minibatches allows it (is negative/unlimited or >= 2)
    size_t half = chunks.back().size() / 2;
    chunks.emplace_back(chunks[0].begin() + half, chunks[0].end());
    chunks[0].resize(half);
    // If the final chunk split separated an even/odd token pair, we have to fix it.
    adjust_grains_for_partners(chunks, state, n_token_jobs);
  }

#ifndef NDEBUG
  size_t total_size = 0;
  for (auto& chunk : chunks)
    total_size += chunk.size();
  TRON_ASSERT_EQ(total_size, n_token_jobs);
#endif
  return chunks;
}

void adjust_grains_for_partners(
    std::vector<std::vector<int>>& grains, auto& state, size_t n_token_jobs) {

  if (n_token_jobs == 0 || grains.empty()) return;

  // 1. Build initial job_idx_to_grain_idx_map
  std::vector<int> job_idx_to_grain_idx_map(n_token_jobs, -1);
  for (size_t c_idx = 0; c_idx < grains.size(); ++c_idx) {
    for (int job_idx_val : grains[c_idx]) {
      if (job_idx_val >= 0 && static_cast<size_t>(job_idx_val) < n_token_jobs) {
        job_idx_to_grain_idx_map[job_idx_val] = static_cast<int>(c_idx);
      }
    }
  }

  // 2. Iterate through job indices to find even partners and adjust grains
  for (int k = 0; k < static_cast<int>(n_token_jobs); ++k) {
    token_job_id tj_ix_k(k);
    token_id t_id_k = state.token_jobs[tj_ix_k];
    auto& page_k = state.page_of(t_id_k);
    int offset_k = page_k.offset_in_page(t_id_k);
    if (offset_k % 2 != 0) continue;  // Don't move tokens for odd offsets
    int partner_offset_k = offset_k + 1;
    // Don't move tokens whose partners don't exist
    if ((size_t)partner_offset_k == page_k.count()) continue;
    token_id partner_token_id = page_k.at_offset(partner_offset_k);
    token_job_id candidate_partner_job_ix =
        state.token_job_id_of_token[partner_token_id];
    // Don't try to move partner tokens that don't exist or aren't in the jobs list
    if (candidate_partner_job_ix.i >= n_token_jobs) continue;
    if (state.token_jobs[candidate_partner_job_ix] != partner_token_id) continue;

    int grain_idx_k = job_idx_to_grain_idx_map[k];
    int grain_idx_partner = job_idx_to_grain_idx_map[candidate_partner_job_ix.i];

    if (grain_idx_k != -1 && grain_idx_partner != -1 &&
        grain_idx_k != grain_idx_partner) {
      std::vector<int>& source_grain_vec = grains[grain_idx_partner];
      auto& dest_grain_vec = grains[grain_idx_k];

      auto val_it = std::find(
          source_grain_vec.begin(), source_grain_vec.end(), candidate_partner_job_ix.i);
      if (val_it != source_grain_vec.end()) {
        source_grain_vec.erase(val_it);
        dest_grain_vec.push_back(candidate_partner_job_ix.i);
        job_idx_to_grain_idx_map[candidate_partner_job_ix.i] = grain_idx_k;
      }
    }
  }

  grains.erase(std::remove_if(grains.begin(), grains.end(),
                   [](const std::vector<int>& grain_val) { return grain_val.empty(); }),
      grains.end());
}
