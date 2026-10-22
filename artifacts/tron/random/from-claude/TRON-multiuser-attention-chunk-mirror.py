#!/usr/bin/env python3
"""Mirror of TRON's chunk_evenly (h/tron/models/model.hpp:209-276 at commit e6c53ba7).

It computes the worked-example table in section 4 of
TRON-multiuser-attention-claude.html. The values are computed from the same
rules as the C++ function, not observed in a TRON run.

Left out on purpose: adjust_grains_for_partners (model.hpp:232-237, 274-275),
the fix that keeps the even and odd token offsets of one KV page in the same
minibatch. It changes nothing in the cases below when a prompt starts at an
even page offset and a decode token's partner is an already cached token.

Run: python3 -I TRON-multiuser-attention-chunk-mirror.py
"""
GRAIN = 8  # minibatch_grain_size, h/tron/models/common.hpp:315


def chunk_evenly(group_sizes, max_mb_size, max_minibatches):
    """group_sizes: tokens per affinity label, in label order.
    max_mb_size: the plugin cap (llama 128, generated plugins 1024).
    max_minibatches: cfg.max_minibatches (-1 = no limit; generated plugins 1).
    Returns (chunk sizes, target count, target size)."""
    n = sum(group_sizes)
    if n == 0:
        return [], 0, 0
    # model.hpp:224-230: cut each group into grains of at most GRAIN tokens.
    grains = []
    for gs in group_sizes:
        i = 0
        while i < gs:
            grains.append(min(GRAIN, gs - i))
            i += GRAIN
    # model.hpp:240-249: target count.
    target_n = (n + max_mb_size - 1) // max_mb_size
    if max_minibatches > 0 and target_n > max_minibatches:
        target_n = max_minibatches
    if target_n == 1 and (len(group_sizes) > 1 or n > GRAIN) and (
            max_minibatches < 0 or max_minibatches >= 2):
        target_n = 2
    target_size = (n + target_n - 1) // target_n
    # model.hpp:250-265: greedy merge.
    chunks = [grains[0]]
    for g in grains[1:]:
        old = chunks[-1]
        new = old + g
        fits = new <= max_mb_size
        good = abs(new - target_size) <= abs(old - target_size)
        hit_limit = len(chunks) == max_minibatches
        if (fits and good) or hit_limit:
            chunks[-1] = new
        else:
            chunks.append(g)
    # model.hpp:267-276: split a lone chunk of more than GRAIN tokens in half.
    if len(chunks) == 1 and n > GRAIN and (max_minibatches < 0 or max_minibatches >= 2):
        half = chunks[0] // 2
        chunks = [half, chunks[0] - half]
    return chunks, target_n, target_size


CASES = [
    ("4 decode users, 1 token each (llama)", [1, 1, 1, 1], 128, -1),
    ("6 decode users, 1 token each (llama)", [1] * 6, 128, -1),
    ("1 decode user, 1 token (llama)", [1], 128, -1),
    ("200 decode users (llama)", [1] * 200, 128, -1),
    ("300 decode users (llama)", [1] * 300, 128, -1),
    ("1 prompt of 20 tokens (llama)", [20], 128, -1),
    ("1 prompt of 300 tokens (llama)", [300], 128, -1),
    ("1 prompt of 20 tokens + 3 decode users (llama)", [20, 1, 1, 1], 128, -1),
    ("4 decode users (generated plugin: 1 minibatch, cap 1024)", [1, 1, 1, 1], 1024, 1),
    ("1 prompt of 300 tokens (generated plugin)", [300], 1024, 1),
]

if __name__ == "__main__":
    for name, groups, cap, mx in CASES:
        ch, tn, ts = chunk_evenly(groups, cap, mx)
        print(f"{name:58s} target_n={tn} target_size={ts:3d} -> chunks {ch}")
