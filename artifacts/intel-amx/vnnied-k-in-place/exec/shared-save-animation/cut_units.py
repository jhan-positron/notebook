#!/usr/bin/env python3
"""Reproduce k_store_cut_units (model.hpp) and store_k_block's run rule in Python and
check them against the unit test t_llama_unit.cpp ("save_k stores every token's K row
once ..."), whose expected unit_start is [0,3,4,11,16,32,40,41,47,48]."""
import json, sys
PAGE = 64; BLOCK = 16

def cut_units(items):
    """items: list of (user, token_position, do_kv). Returns unit_start (n_units + 1 entries).
    A page is identified by (user, position // 64), as the code compares page objects."""
    starts = []
    run = None
    for t, (user, tok, kv) in enumerate(items):
        page = (user, tok // PAGE) if kv else None
        block = (tok % PAGE) // BLOCK if kv else 0
        key = (kv, page, block)
        if t == 0 or key != run:
            starts.append(t); run = key
    starts.append(len(items))
    return starts

def runs_in_unit(items, a, b):
    """store_k_block inside one unit: runs of consecutive KV items in one block with
    distinct offsets, at most 16; a run of 1 takes the scatter path."""
    runs = []; t = a
    while t < b:
        user, tok, kv = items[t]
        if not kv: t += 1; continue
        page, c = (user, tok // PAGE), (tok % PAGE) // BLOCK
        present = set(); n = 0; start = t
        while t < b and n < 16:
            user2, tok2, kv2 = items[t]
            if not kv2: t += 1; continue
            if (user2, tok2 // PAGE) != page or (tok2 % PAGE) // BLOCK != c: break
            off = tok2 % BLOCK
            if off in present: break
            present.add(off); n += 1; t += 1
        runs.append({"items": [start, t], "page": page[1], "block": c, "n": n, "path": "scatter" if n == 1 else "block store", "columns": sorted(present)})
    return runs

# --- the unit test's pass (t/t_llama_unit.cpp:2640-2665)
test_items = [(0, tok, tok != 8) for tok in range(5, 21)] + [(0, tok, True) for tok in range(48, 64)] + \
             [(0, tok, True) for tok in range(64, 72)] + [(0, 100, True)] + [(0, tok, True) for tok in range(130, 136)] + [(0, 21, False)]
assert len(test_items) == 48
starts = cut_units(test_items)
expected = [0, 3, 4, 11, 16, 32, 40, 41, 47, 48]
print("unit test pass: unit_start =", starts, "matches expected:", starts == expected)
assert starts == expected
test_units = []
for u in range(len(starts) - 1):
    a, b = starts[u], starts[u + 1]
    toks = [test_items[i][1] for i in range(a, b)]
    kv = test_items[a][2]
    test_units.append({"u": u, "items": [a, b], "tokens": [toks[0], toks[-1]], "n_items": b - a, "kv": kv,
                       "page": toks[0] // PAGE if kv else None, "block": (toks[0] % PAGE) // BLOCK if kv else None,
                       "runs": runs_in_unit(test_items, a, b) if kv else []})

# --- the mock prefill pass: 8 users x 128 tokens (pass 3: positions 256..383), user-major item order
mock_items = []
for user in range(8):
    for k in range(128):
        mock_items.append((user, 256 + k, True))
mstarts = cut_units(mock_items)
assert mstarts == [16 * u for u in range(65)], mstarts[:5]
mock_units = []
for u in range(64):
    a = 16 * u; user = u // 8; pos0 = 256 + 16 * (u % 8)
    mock_units.append({"u": u, "items": [a, a + 16], "user": user + 1, "positions": [pos0, pos0 + 15],
                       "page": pos0 // PAGE, "block": (pos0 % PAGE) // BLOCK, "columns": [0, 15]})
json.dump({"test_pass": {"items": test_items, "unit_start": starts, "units": test_units},
           "mock_pass": {"unit_start": mstarts, "units": mock_units}}, open(sys.argv[1] if len(sys.argv) > 1 else "units.json", "w"), indent=0)
print("mock pass: %d units, unit_start[0..4] = %s ... unit_start[64] = %d" % (len(mstarts) - 1, mstarts[:5], mstarts[64]))
for x in test_units: print("  test unit", x["u"], "items", x["items"], "tokens", x["tokens"], "kv", x["kv"], "page", x["page"], "block", x["block"], [(r["n"], r["path"]) for r in x["runs"]])
