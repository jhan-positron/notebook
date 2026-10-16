---
name: attn-worker-lane-facts
description: "2026-09-02 code-verified per-layer sequence of one tron CPU attention worker (12 steps), the three real barriers, the serial join fold, the pending-page AVX fact, and the handwritten-llama.hpp vs ingested-plugin trap; distilled-page figures are edited in exec/gen_distilled.py, not in rampup/"
metadata: 
  node_type: memory
  type: project
  originSessionId: ac6b80f3-ca07-4e95-a5e1-e8e90e3e8320
  modified: 2026-09-02T19:38:12.994Z
---

Verified 2026-09-02 in ~/workspace/tron-amx @ 60d66d9c04 (16-agent read/refute
workflow + my own spot checks) for the "One decode step" lanes figure in
tron-amx-distilled.html, section "Decode architecture".

Per (layer, minibatch), every attention worker runs (self_attention.hpp:801-894
run_attention_job; llama.hpp:718-732 run_pre_attn):
1 free_scratchpads_barrier (worker n-1 resets scratchpads; all wait) ->
2 qs_roped_channel.start_writing = wait for main's next_layer phase (this is the long
between-layer idle for one minibatch) -> 3 per-token wait for the WQ FPGA row (DMA latch)
-> 4 rope Q on the worker's striped tokens only -> 5 roped-Q fallback latch = all
workers arrived -> 6 run_sections(ready): per page QK -> scale -> max/exp/corr -> PV ->
m*,s*,v* update in attn[worker] -> 7 upstream_kvs_ready[layer].wait() -> 8
run_sections(pending): the one partial page per user, AVX path because the AMX
predicate needs end == page_size (self_attention.hpp:1553-1572) -> 9 run_joins poll:
bare spin on atomic sections_left[kv_head] for the worker's own KV heads (the real
"wait for the slowest worker") -> 10 serial fold of workers 1..n-1 into worker 0's
scratchpad per (kv_head, token) by rank striping, then finish = v*/s* -> vo (the
balanced tree is only a TODO note, 1196-1222) -> 11 vo latch count_down (releases
main's Wo launch) -> 12 attn_done_barrier.arrive_and_wait (after vo, so not on main's
path). Loop order: layer outer, minibatch inner (A then B of the same layer).
Latch waits are monitored spins (mwaitx.cpp monitor_and_wait: TSX xbegin + tpause on
3bda), never OS sleeps. The partial (m*,s*,v*) is never copied; sections_left-- per
SECTION is the only cross-worker signal.

**Trap:** this is the handwritten llama.hpp schedule. Ingested (generated) plugins,
i.e. the qwen-3-4b runs, have no run_pre_attn on the attention workers (rope Q is a
main-stream kernel), main advances the scratchpad phase via prepare_attention_job
(self_attention.hpp:780-796, model.hpp:2119-2160), and one minibatch is asserted.
Steps 6-12 (run_attention_job from run_sections on) are the same code.

**How to apply:** when a figure or prose in this project attributes work to the
attention workers, say which plugin path it describes; do not draw the join as a
tree or as an all-worker barrier. Edits to figures transplanted into
tron-amx-distilled.html go into exec/gen_distilled.py as asserted `_replace_once`
string replacements on the fragment (precedent: 2026-09-01 zoom-figure labels,
2026-09-02 attention lane + zoom strip); rampup/02 keeps its original figure; the
generator reproduced the page byte-for-byte before the edit, check that first.
Related: [[amx-tron-softattn-project]], [[single-attention-measurement]],
[[svg-render-check]] (cairosvg's fallback font is ~15% wider than system-ui and lacks
circled digits 11+; use plain numbers).
