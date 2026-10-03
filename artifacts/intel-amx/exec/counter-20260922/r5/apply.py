#!/usr/bin/env python3
"""Round-5 edits for PR 4596 (Wade W6-W9). Exact string replacement; aborts if any original is missing or ambiguous."""
import sys
from pathlib import Path
WT = Path("/home/jhan/workspace/ai-runs/tron-attn-stats")
EDITS = []
def E(path, old, new): EDITS.append((path, old, new))

# W6: attn_stats.hpp forward_scope comment
E("h/tron/models/attn_stats.hpp",
"""// without this object gets a half record: token jobs without forwards, or a
// wall filed under the previous forward's class (PR 4596 review round 4,
// comment W2). The destructor also runs when forward() unwinds through an
// exception, so such a forward is still counted; tron's asserts abort rather
// than throw.
""",
"""// without this object gets a half record: token jobs without forwards, or a
// wall filed under the previous forward's class. The destructor also runs
// when forward() unwinds through an exception, so such a forward is still
// counted; tron's asserts abort rather than throw.
""")

# W7: t_attn_stats.cpp :306
E("t/t_attn_stats.cpp",
"""  // PR 4596 review round 4, comment W2: the record behind <class>_forwards
  // had two writers, the scheduler (forwards and the wall) and the model
  // (class, token jobs, path sets). forward_scope is the one owner. The class
  // is stored at construction. The wall and the fold are recorded at
  // destruction. So every caller of model::state::forward gets a whole record
  // filed under the class of that forward.
""",
"""  // forward_scope is the one owner of the record behind <class>_forwards. The
  // class is stored at construction. The wall and the fold are recorded at
  // destruction. So every caller of model::state::forward gets a whole record
  // filed under the class of that forward.
""")

# W7: t_attn_stats.cpp :372 (history anchor "seen in a live read on 2026-09-29", "under the old order")
E("t/t_attn_stats.cpp",
"""  // Seen in a live read of a CPU-attention run on 2026-09-29: listener_jobs
  // was one forward ahead of token_jobs. begin_forward added the listener
  // counts and end_forward added the token jobs. A reader of the leaves
  // during a forward must never see listener_jobs + kv_only_jobs above
  // token_jobs. All three are added in end_forward now. Under the old order
  // the mid-forward CHECKs on listener_jobs, kv_only_jobs and the rendered
  // leaf fail, for both classes below.
""",
"""  // A reader of the leaves during a forward must never see listener_jobs +
  // kv_only_jobs above token_jobs. end_forward adds all three together. If
  // begin_forward added the listener counts and end_forward the token jobs,
  // listener_jobs would run one forward ahead of token_jobs. The mid-forward
  // CHECKs on listener_jobs, kv_only_jobs and the rendered leaf below would
  // then fail for both classes.
""")

# W7: t_attn_stats.cpp :408
E("t/t_attn_stats.cpp",
"""  // PR 4596 review round 4, comment W4: in production every index is in range
  // by construction (the worker index is below the pool size that sizes the
  // rows, the layer id below n_layers, the token job below the count that
  // begin_forward sized). A wrong index must therefore fail, not go uncounted.
  // Each call runs in a forked child that must die with SIGABRT.
""",
"""  // In production every index is in range by construction (the worker index
  // is below the pool size that sizes the rows, the layer id below n_layers,
  // the token job below the count that begin_forward sized). A wrong index
  // must therefore fail, not go uncounted. Each call runs in a forked child
  // that must die with SIGABRT.
""")

# W8: delete the pool_worker arithmetic case (:640-658)
E("t/t_attn_stats.cpp",
"""TEST_CASE("attn-stats pool_worker: the last n_attn_workers pool workers run attention",
    "[attn_stats]") {
  // Note [Attention workers are the last pool workers] in model.hpp: attention
  // worker i of a forward with n attention workers is pool worker
  // num_workers - n + i. The rows are keyed by that pool worker.
  constexpr size_t SPLIT_1 = 1;
  constexpr size_t SPLIT_2 = 2;
  auto stats = make_stats(STATS_ON_TRUE);
  CHECK(stats->pool_worker(WORKER_0, N_WORKERS_3) == WORKER_0);
  CHECK(stats->pool_worker(WORKER_2, N_WORKERS_3) == WORKER_2);
  CHECK(stats->pool_worker(WORKER_0, SPLIT_2) == WORKER_1);
  CHECK(stats->pool_worker(WORKER_1, SPLIT_2) == WORKER_2);
  CHECK(stats->pool_worker(WORKER_0, SPLIT_1) == WORKER_2);
  // The off state answers the same: the mapping is arithmetic on the pool
  // size, and a caller may compute it before testing the switch.
  auto off = make_stats(STATS_OFF_FALSE);
  CHECK(off->pool_worker(WORKER_0, SPLIT_1) == WORKER_2);
}

""", "")

# W7: t_attn_stats.cpp :662 (rows keyed by pool worker) + Note reference graft
E("t/t_attn_stats.cpp",
"""  // PR 4596 review round 4, comment W5. The rows are sized by the pool (3
  // here) and were indexed by the attention worker index. The plugin picks
  // the split per forward (recommend_n_main_helpers), so attention worker 0
  // of a 1-worker forward is pool worker 2 and attention worker 0 of a
  // 2-worker forward is pool worker 1: two threads, two cores. The old keying
  // put both under row 0, a row that no thread of either forward owned.
  // This case drives the hooks the way self_attention.hpp calls them after
  // the fix (row = pool_worker(attention index, split)) and checks that the
  // two forwards land in the two rows those threads own. Under the old
  // keying every CHECK on rows 1 and 2 below fails and row 0 carries it all.
""",
"""  // The rows are sized by the pool (3 here) and keyed by the pool worker, not
  // by the attention worker index (Note [Attention workers are the last pool
  // workers] in model.hpp). The plugin picks the split per forward
  // (recommend_n_main_helpers), so attention worker 0 of a 1-worker forward
  // is pool worker 2 and attention worker 0 of a 2-worker forward is pool
  // worker 1: two threads, two cores. Keyed by the attention index, both
  // forwards would land in row 0, a row that no thread of either forward
  // owns. This case drives the hooks the way self_attention.hpp calls them
  // (row = pool_worker(attention index, split)) and checks that the two
  // forwards land in the two rows those threads own.
""")

# W8 graft: keep the "+ attn_ix" term of the formula under a positive check (forward B of the rows case)
E("t/t_attn_stats.cpp",
"""    const size_t row = stats->pool_worker(WORKER_0, SPLIT_2);
    REQUIRE(row == WORKER_1);
""",
"""    const size_t row = stats->pool_worker(WORKER_0, SPLIT_2);
    REQUIRE(row == WORKER_1);
    // The second attention worker of this split is the last pool worker.
    CHECK(stats->pool_worker(WORKER_1, SPLIT_2) == WORKER_2);
""")

# W7: t_llama_unit.cpp :2227
E("t/t_llama_unit.cpp",
"""    // PR 4596 review round 4, comment W5: the row is the pool worker's, not
    // the attention worker's. The call above ran attention worker 0 of a
    // 1-worker split, which is the last pool worker (Note [Attention workers
    // are the last pool workers] in model.hpp). Before the fix the visits
    // went to row 0, which is a main helper whenever the pool has more than
    // one worker.
""",
"""    // The row is the pool worker's, not the attention worker's. The call
    // above ran attention worker 0 of a 1-worker split, which is the last
    // pool worker (Note [Attention workers are the last pool workers] in
    // model.hpp). Keyed by the attention index, the visits would go to row 0,
    // which is a main helper whenever the pool has more than one worker.
""")

# W7: t_llama_unit.cpp :2255
E("t/t_llama_unit.cpp",
"""    // row follows the thread, not the attention index. The old keying put
    // this call in row 0 again, on top of the first call.
""",
"""    // row follows the thread, not the attention index. Keyed by the attention
    // index, this call would land in row 0 again, on top of the first call.
""")

# W9: one helper for the three stats row keys
E("h/tron/models/self_attention.hpp",
"""        stats_ref.note_attn_job(pool_worker_ix, layer.i, attn_elapsed);
""",
"""        stats_ref.note_attn_job(
            stats_ref.pool_worker(worker_ix, n_attn_workers), layer.i, attn_elapsed);
""")

ok = True
for path, old, new in EDITS:
    p = WT / path; text = p.read_text()
    n = text.count(old)
    if n != 1:
        print(f"FAIL {path}: original found {n} times:\n{old[:120]}"); ok = False
if not ok: sys.exit(1)
for path, old, new in EDITS:
    p = WT / path; p.write_text(p.read_text().replace(old, new, 1))
    print(f"applied {path}: -{old.count(chr(10))} +{new.count(chr(10))} lines")
