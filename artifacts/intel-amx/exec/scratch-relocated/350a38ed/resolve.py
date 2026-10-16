import re, sys
root = sys.argv[1]
pat = re.compile(r"<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> f52d634c32\n", re.S)
plan = {
 "h/tron/models/model.hpp": [
  "    // reach its save_k call without main's help. Nothing blocks between its\n"
  "    // K/Q rope kernel and this statement. So main's join cannot deadlock. A\n"
  "    // join that does not complete within about two minutes\n"
  "    // (k_join_timeout_s after the first clock read) aborts with the\n",
  "                \"finished, {} of {} units claimed); the helpers' save_k calls do not \"\n"
  "                \"match this one\",\n"
  "                k_join_timeout_s, w.finished.load(), n_helpers,\n",
 ],
 "ingest/src/TronCpp.hs": [
  "  -- of consecutive tokens inside one 16-token page block).\n"
  "  -- Both sides call save_k, main with worker index 0 (submitAttentionOperation)\n"
  "  -- and the helpers with their own worker_ix, at the same position of the\n"
  "  -- statement list. So the N-th window a helper enters in a pass is the N-th\n"
  "  -- window main opens in that pass.\n",
 ],
 "t/t_llama_unit.cpp": [
  "    REQUIRE(stored == kv_jobs * n_kv_heads);\n"
  "    REQUIRE(kept == (num_kv_tokens - kv_jobs) * n_kv_heads);\n"
  "    // The marks: save_k marks K of every job with KV work exactly once. The\n"
  "    // helpers leave before the mark loop. K alone does not complete a token.\n"
  "    // The second mark completes it (mark_k_complete returns true only when\n"
  "    // the count was 1). A job without KV work has no mark (count 0).\n"
  "    for (size_t job = 0; job < n_items; ++job) {\n"
  "      page_t* page = token_pages[job_tokens[job].i];\n"
  "      const size_t offset = static_cast<size_t>(page->offset_in_page(job_tokens[job]));\n"
  "      REQUIRE_FALSE(page->is_kv_complete(slot, offset));\n"
  "      REQUIRE(page->mark_k_complete(slot, offset) == (do_kv[job] != 0));\n"
  "    }\n",
  "    constexpr size_t n_workers = 3;\n"
  "    constexpr size_t main_worker_ix = 0;\n"
  "    // Every worker calls the same save_k with its own index (Note [Shared\n"
  "    // block save] in model.hpp).\n",
  "        state.template save_k<geometry>(\n"
  "            &q_batch, operation, state.plugin_state.kouts, worker_ix, n_workers);\n"
  "      });\n"
  "    }\n"
  "    state.template save_k<geometry>(\n"
  "        &q_batch, operation, state.plugin_state.kouts, main_worker_ix, n_workers);\n",
 ],
}
for f, reps in plan.items():
    p = f"{root}/{f}"
    s = open(p).read()
    blocks = pat.findall(s)
    assert len(blocks) == len(reps), (f, len(blocks), len(reps))
    it = iter(reps)
    s2 = pat.sub(lambda m: next(it), s)
    assert "<<<<<<<" not in s2 and ">>>>>>>" not in s2 and "\n=======\n" not in s2, f
    open(p, "w").write(s2)
    print(f, "resolved", len(reps), "hunks")
