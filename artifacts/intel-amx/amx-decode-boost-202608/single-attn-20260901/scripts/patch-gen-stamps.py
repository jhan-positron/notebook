#!/usr/bin/env python3
"""Apply kvwait stamps 7601/7603/7604/7605 and the attention phase counters
(7606-7627, via self_attn_state.probe_reset/probe_take) to the generated qwen
plugin header. Each site is checked and applied on its own, so the script is
idempotent and also upgrades a header that already carries 7601-7605.
Run after every cmake configure of the fence worktree, before ninja."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/jhan/workspace/tron-fence-amx/gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp"
s = open(P).read()
done = []

def replace_once(old, new, site):
    global s
    n = s.count(old)
    assert n == 1, f"{site}: anchor count {n}"
    s = s.replace(old, new)
    done.append(site)

# --- 7601: bracket workers_done.wait() at the end of run() ---
if "site 7601" not in s:
    replace_once("""      // All the workers we spawned must be done before run() returns.
      // See Note [Plugin-owned worker launch] in model.hpp.
      workers_done.wait();
""", """      // All the workers we spawned must be done before run() returns.
      // See Note [Plugin-owned worker launch] in model.hpp.
      if (kvwait_probe::state().enabled) {
        const uint64_t f1_t0 = kvwait_probe::state_t::now();
        workers_done.wait();
        kvwait_probe::state().add(f1_t0,
            kvwait_probe::state_t::now() - f1_t0, 7601);  // site 7601: Fence 1
      } else {
        workers_done.wait();
      }
""", "7601")

# --- 7603: after the op-0 prepare_attention_job (attention released) ---
if "site 7603" not in s:
    anchor = "prepare_attention_job<tron::attention_geometry{32, tron::kv_geometry{8, 128}}, 0>(q_batch->outer_batch, rope);"
    assert s.count(anchor) == 1, f"7603 anchor count {s.count(anchor)}"
    i = s.index(anchor) + len(anchor)
    s = s[:i] + """
        if (kvwait_probe::state().enabled)
          kvwait_probe::state().add(kvwait_probe::state_t::now(),
              q_batch->items.size(), 7603);  // site 7603: attention released (op 0)""" + s[i:]
    done.append("7603")

# --- 7604 + 7605: the worker-0 block after op 35 (byte-identical to the
# header as stamped on 2026-08-31/09-01) ---
BLOCK_7605 = """      if (worker_ix == 0) {
        kvwait_probe::state_t& kvp = kvwait_probe::state();
        if (kvp.enabled) {
          kvp.add(kvwait_probe::state_t::now(),
              q_batch->outer_batch->items.size(), 7604);  // site 7604: attention joined (op 35)
          kvp.add(kvwait_probe::state_t::now(),
              static_cast<uint64_t>(attn_elapsed), 7605);  // site 7605: payload = worker-0 attention wall (TSC cycles), summed over the 36 ops
        }
        outer_state.record_attention_time((attn_elapsed * n_attn_workers));
      }"""
if "site 7604" not in s:
    replace_once("""      if (worker_ix == 0) {
        outer_state.record_attention_time((attn_elapsed * n_attn_workers));
      }""", BLOCK_7605, "7604/7605")
assert s.count(BLOCK_7605) == 1 or "sites 7606" in s, "7604/7605 block text differs from the expected stamped form"

# --- 7606-7627: phase counters exported after 7605, reset at worker start ---
# Only when the worktree's self_attention.hpp carries the probe (commit
# "attention phase probe"); otherwise the header must not reference it, so a
# build of the branch without the probe keeps working (shared patcher, 2026-09-01).
import os
SA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(P)))))))),
    "h", "tron", "models", "self_attention.hpp")
HAS_PROBE = os.path.exists(SA) and "namespace attn_phase" in open(SA).read()
if not HAS_PROBE:
    print("note: self_attention.hpp has no attn_phase probe; 7606-7627 sites skipped")
if HAS_PROBE and "sites 7606" not in s:
    replace_once("""          kvp.add(kvwait_probe::state_t::now(),
              static_cast<uint64_t>(attn_elapsed), 7605);  // site 7605: payload = worker-0 attention wall (TSC cycles), summed over the 36 ops
        }
""", """          kvp.add(kvwait_probe::state_t::now(),
              static_cast<uint64_t>(attn_elapsed), 7605);  // site 7605: payload = worker-0 attention wall (TSC cycles), summed over the 36 ops
          {
            const tron::attn_phase::counters pcs = outer_state.self_attn_state.probe_take();
            for (size_t i = 0; i < tron::attn_phase::n_counters; ++i)
              kvp.add(kvwait_probe::state_t::now(), pcs.v[i],
                  7606 + i);  // sites 7606-7627: worker-0 attention phase counters for this token (see attn_phase::idx)
          }
        }
""", "7606-7627")
if HAS_PROBE and "probe_reset" not in s:
    replace_once("""      plugin_batch* q_batch = &(q_batches[0]->plugin_batch);
      uint64_t attn_elapsed = 0;
      outer_state.wait_attention_job(q_batch->outer_batch, worker_ix);
""", """      plugin_batch* q_batch = &(q_batches[0]->plugin_batch);
      uint64_t attn_elapsed = 0;
      outer_state.self_attn_state.probe_reset();  // attention phase counters (sites 7606-7627)
      outer_state.wait_attention_job(q_batch->outer_batch, worker_ix);
""", "probe_reset")

if not done:
    print("already stamped"); sys.exit(0)
open(P, "w").write(s)
print("stamped " + ", ".join(done))
