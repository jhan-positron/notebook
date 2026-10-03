#!/usr/bin/env python3
"""Round-5 edits after the diff review (wf_48d45328-3c3): E1, E2, E3, E4b, E5, E6, E7. E4a (two full-split CHECKs) is NOT applied: Wade asked to drop that arithmetic."""
import sys
from pathlib import Path
WT = Path("/home/jhan/workspace/ai-runs/tron-attn-stats")
EDITS = []
def E(path, old, new): EDITS.append((path, old, new))
E("t/t_attn_stats.cpp",
"""  // forward_scope is the one owner of the record behind <class>_forwards. The
  // class is stored at construction. The wall and the fold are recorded at
  // destruction. So every caller of model::state::forward gets a whole record
  // filed under the class of that forward.
""",
"""  // forward_scope is the one owner of the record behind <class>_forwards. The
  // class is stored at construction. The wall and the fold are recorded at
  // destruction. With the forwards count and the wall written at one site and
  // the class and job counts at another, a wall could be filed under the class
  // of the previous forward. So every caller of model::state::forward gets a
  // whole record filed under the class of that forward.
""")
E("t/t_attn_stats.cpp",
"""  // listener_jobs would run one forward ahead of token_jobs. The mid-forward
  // CHECKs on listener_jobs, kv_only_jobs and the rendered leaf below would
  // then fail for both classes.
""",
"""  // listener_jobs would already include the current forward while token_jobs
  // would not. The mid-forward CHECKs below would then fail: listener_jobs,
  // kv_only_jobs and the rendered leaf for the prompt class, listener_jobs
  // for the decode class.
""")
E("t/t_attn_stats.cpp",
"""  // (recommend_n_main_helpers), so attention worker 0 of a 1-worker forward
  // is pool worker 2 and attention worker 0 of a 2-worker forward is pool
  // worker 1: two threads, two cores. Keyed by the attention index, both
""",
"""  // (recommend_n_main_helpers). So attention worker 0 of a 1-worker forward is
  // pool worker 2. Attention worker 0 of a 2-worker forward is pool worker 1.
  // Those are two threads on two cores. Keyed by the attention index, both
""")
E("t/t_attn_stats.cpp",
"""    // The second attention worker of this split is the last pool worker.
    CHECK(stats->pool_worker(WORKER_1, SPLIT_2) == WORKER_2);
""",
"""    // Pins the "+ attn_ix" term of the row formula: the second attention
    // worker of this split is the last pool worker.
    CHECK(stats->pool_worker(WORKER_1, SPLIT_2) == WORKER_2);
""")
E("t/t_llama_unit.cpp",
"""    // model.hpp). Keyed by the attention index, the visits would go to row 0,
    // which is a main helper whenever the pool has more than one worker.
""",
"""    // model.hpp). Keyed by the attention index, the visits would go to row 0.
    // Row 0 is a main helper whenever the pool has more than one worker.
""")
E("t/t_llama_unit.cpp",
"""    // index, this call would land in row 0 again, on top of the first call.
""",
"""    // index, this call would land in row 0 again, added to the first call.
""")
E("h/tron/models/attn_stats.hpp",
"""// counted; tron's asserts abort rather than throw.
""",
"""// counted. tron's asserts abort rather than throw.
""")
ok = True
for path, old, new in EDITS:
    n = (WT / path).read_text().count(old)
    if n != 1: print(f"FAIL {path}: found {n}:\n{old[:100]}"); ok = False
if not ok: sys.exit(1)
for path, old, new in EDITS:
    p = WT / path; p.write_text(p.read_text().replace(old, new, 1)); print("applied", path)
