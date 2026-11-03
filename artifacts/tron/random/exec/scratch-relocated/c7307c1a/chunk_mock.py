# Mirror of chunk_evenly (h/tron/models/model.hpp:209-275 at e6c53ba7), without
# adjust_grains_for_partners (assumes no even/odd KV-page pair straddles a cut).
import math
GRAIN = 8
def chunk_evenly(group_sizes, max_mb_size, max_minibatches):
    n = sum(group_sizes)
    if n == 0: return []
    grains = []
    for gs in group_sizes:
        i = 0
        while i < gs:
            grains.append(min(GRAIN, gs - i)); i += GRAIN
    target_n = (n + max_mb_size - 1) // max_mb_size
    if max_minibatches > 0 and target_n > max_minibatches:
        target_n = max_minibatches
    if target_n == 1 and (len(group_sizes) > 1 or n > GRAIN) and (max_minibatches < 0 or max_minibatches >= 2):
        target_n = 2
    target_size = (n + target_n - 1) // target_n
    chunks = [grains[0]]
    for g in grains[1:]:
        old = chunks[-1]; new = old + g
        fits = new <= max_mb_size
        good = abs(new - target_size) <= abs(old - target_size)
        hit_limit = len(chunks) == max_minibatches
        if (fits and good) or hit_limit: chunks[-1] = new
        else: chunks.append(g)
    if len(chunks) == 1 and n > GRAIN and (max_minibatches < 0 or max_minibatches >= 2):
        half = chunks[0] // 2
        chunks = [half, chunks[0] - half]
    return chunks, target_n, target_size
cases = [
 ("4 decode users, 1 token each (llama)", [1,1,1,1], 128, -1),
 ("6 decode users, 1 token each (llama)", [1]*6, 128, -1),
 ("1 decode user, 1 token (llama)", [1], 128, -1),
 ("200 decode users (llama)", [1]*200, 128, -1),
 ("300 decode users (llama)", [1]*300, 128, -1),
 ("1 prompt of 20 tokens (llama)", [20], 128, -1),
 ("1 prompt of 300 tokens (llama)", [300], 128, -1),
 ("1 prompt of 20 tokens + 3 decode users (llama)", [20,1,1,1], 128, -1),
 ("4 decode users (generated plugin: 1 minibatch, cap 1024)", [1,1,1,1], 1024, 1),
 ("1 prompt of 300 tokens (generated plugin)", [300], 1024, 1),
]
for name, groups, cap, mx in cases:
    ch, tn, ts = chunk_evenly(groups, cap, mx)
    print(f"{name:58s} target_n={tn} target_size={ts:3d} -> chunks {ch}")
