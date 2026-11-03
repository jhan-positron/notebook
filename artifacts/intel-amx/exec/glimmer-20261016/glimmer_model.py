#!/usr/bin/env python3
"""Page-visit model of the Glimmer runs (8 users, 128-token prompt chunks, 256 decode steps).

Model facts (see the answer for file:line):
- BOS (position 0) is one shared edge; it lives in USER 1's first book, page [0,63].
  User 1's first book maps position p -> entry p (pages [64j, 64j+63]).
  Users 2..8 branch at the BOS and get their own book: position p -> entry p-1
  (pages [64k+1, 64k+64]).
- First book = 25 pages = 1600 tokens. At prompt 2049 the chunk 1536..1663 does not fit
  (1536+128 > 1600 for user 1; entry 1535+128 > 1600 for users 2..8), so every user gets a
  new child edge + new book at position 1536 (pages [1536+64m, 1599+64m]). The old edge
  ends at 1535: user 1's last old page [1472,1535] is full, users 2..8's [1473,1535] has 63.
- FPGA boundary B per forward: prompt forward c>=2: B = 128(c-1)-1, except prompt-2049
  forward 13 where the partial shard (base 1024) moved to the new edge and is not pushed
  (dma_last_abs 1535 < edge base 1536) -> B = 1023 (shard 0). Decode: B = 4*floor(q/4)-1.
- Range boundaries inside a user's token run: 1 (BOS edge | user edge), B+1 (shard event),
  q'+1 for each query q' of this user in this forward, 1536 (new edge, prompt 2049 only).
- Dense (AMX) page: 64 present tokens, not written this forward, first token visible
  (full layer: >= B+1), last token below the range end, q - first < window.
"""
import sys

WINDOW = 2048
HEADS = 2


def run(P):
    newbook = 1536 if P == 2049 else None
    decode_q0 = P - 1  # last prompt token = first decode-like query

    def pages_for(u, maxpos):
        """Pages of user u's own books holding positions <= maxpos: list of (a, b)."""
        out = []
        lim1 = min(maxpos, newbook - 1) if newbook else maxpos
        if u == 1:
            a = 0
            while a <= lim1:
                out.append((a, min(a + 63, lim1)))
                a += 64
        else:
            a = 1
            while a <= lim1:
                out.append((a, min(a + 63, lim1)))
                a += 64
        if newbook and maxpos >= newbook:
            a = newbook
            while a <= maxpos:
                out.append((a, min(a + 63, maxpos)))
                a += 64
        return out

    def forwards():
        # prompt forwards
        nchunks = (P - 2) // 128 + 1  # chunk 1 = 1..127, chunk c = 128(c-1)..128c-1
        for c in range(1, nchunks + 1):
            lo = 1 if c == 1 else 128 * (c - 1)
            hi = 128 * c - 1
            if c == 1:
                B = None
            elif newbook and lo == newbook:
                B = 1023
            else:
                B = lo - 1
            yield ("prompt", c, lo, hi, B, True)
        for f in range(1, 257):
            q = decode_q0 + f - 1
            yield ("decode", f, q, q, 4 * (q // 4) - 1, False)

    stats = {}

    def S(cls, L):
        return stats.setdefault((cls, L), dict(amx=0, avx=0, fpga=0, ready_avx=0, ready_avx_visits=0,
                                               ready_avx_full=0, pending_avx=0, pending_avx_visits=0,
                                               amx_visits=0, empty=0))

    for cls, c, lo, hi, B, is_prompt in forwards():
        written = set(range(lo, hi + 1)) | ({0} if (is_prompt and c == 1) else set())
        maxpos = hi
        for L in ("full", "sliding"):
            st = S(cls, L)
            for u in range(1, 9):
                queries = range(lo, hi + 1)
                bounds = {1, hi + 1}
                if B is not None:
                    bounds.add(B + 1)
                if newbook:
                    bounds.add(newbook)
                bounds |= {q + 1 for q in queries}
                pages = pages_for(u, maxpos)
                if u != 1:
                    pages = [(0, 63 if maxpos >= 63 else maxpos)] + pages  # BOS page (user 1's book)
                for q in queries:
                    if B is not None and L == "full" and q >= 127:
                        st["fpga"] += B + 1
                    for (a, b) in pages:
                        n = b - a + 1
                        if a > q:
                            continue
                        if L == "sliding" and q - (a + n) >= WINDOW:
                            continue  # whole page outside the window
                        if L == "full" and b <= B if B is not None else False:
                            continue  # workless range (all on the card)
                        if L == "full" and B is None:
                            pass
                        pending = any(a <= w <= b for w in written) if n <= 64 else True
                        # tokens visible to this user's query on this page
                        def vis(k):
                            if k > q:
                                return False
                            if k == 0:
                                own = True
                            elif a == 0 and u != 1:
                                own = False  # user 1's tokens on the BOS page
                            else:
                                own = True
                            if not own:
                                return False
                            if L == "sliding" and q - k >= WINDOW:
                                return False
                            if L == "full" and B is not None and k <= B:
                                return False
                            return True
                        first_visible = (a == 0 or (a != 0)) and (
                            (L == "full" and (B is None or a >= B + 1)) or L == "sliding")
                        one_range = not any(a < x <= b for x in bounds)
                        dense = (n == 64 and not pending and first_visible and one_range
                                 and (L == "full" or q - a < WINDOW) and a <= q)
                        if dense:
                            st["amx"] += 64 * HEADS
                            st["amx_visits"] += HEADS
                            continue
                        rel = sum(1 for k in range(a, b + 1) if vis(k))
                        if rel == 0:
                            st["empty"] += HEADS
                            continue
                        st["avx"] += rel * HEADS
                        if pending:
                            st["pending_avx"] += rel * HEADS
                            st["pending_avx_visits"] += HEADS
                        else:
                            st["ready_avx"] += rel * HEADS
                            st["ready_avx_visits"] += HEADS
                            if rel == 64:
                                st["ready_avx_full"] += HEADS
            # BOS job itself in forward 1 (position 0 scores itself) for both layer types
            if is_prompt and c == 1:
                st["avx"] += 1 * HEADS
                st["pending_avx"] += 1 * HEADS
                st["pending_avx_visits"] += HEADS
    return stats


OBS = {
    1025: {
        ("prompt", "full"): dict(amx=0, avx=1056754, fpga=3670016),
        ("prompt", "sliding"): dict(amx=6422528, avx=1974258, fpga=0),
        ("decode", "full"): dict(amx=0, avx=10240, fpga=2355200),
        ("decode", "sliding"): dict(amx=4540416, avx=180224, fpga=0),
        "totals": dict(prompt=dict(ready_avx=4962048, ready_avx_full=69888, pending_avx=85771816,
                                   ready_avx_visits=559104, pending_avx_visits=2011048, amx_visits=3913728),
                       decode=dict(ready_avx=1839240, ready_avx_full=26520, pending_avx=5322616,
                                   ready_avx_visits=168480, pending_avx_visits=212992, amx_visits=2766816)),
    },
    2049: {
        ("prompt", "full"): dict(amx=933888, avx=2228210, fpga=15204352),
        ("prompt", "sliding"): dict(amx=29376512, avx=4194290, fpga=0),
        ("decode", "full"): dict(amx=0, avx=10240, fpga=4452352),
        ("decode", "sliding"): dict(amx=7900672, avx=487936, fpga=0),
        "totals": dict(prompt=dict(ready_avx=34208512, ready_avx_full=219648, pending_avx=158335528,
                                   ready_avx_visits=1594112, pending_avx_visits=3655912, amx_visits=18091008),
                       decode=dict(ready_avx=13837824, ready_avx_full=0, pending_avx=5324800,
                                   ready_avx_visits=297024, pending_avx_visits=212992, amx_visits=4814472)),
    },
}

for P in (1025, 2049):
    st = run(P)
    print(f"=== prompt {P} tokens (prompt_or_mixed = prompt forwards, decode_like = 256 steps)")
    for cls in ("prompt", "decode"):
        for L in ("full", "sliding"):
            m = st[(cls, L)]
            o = OBS[P][(cls, L)]
            ok = all(m[k] == o[k] for k in ("amx", "avx", "fpga"))
            print(f"  {cls:6s} {L:7s} model amx/avx/fpga = {m['amx']}/{m['avx']}/{m['fpga']}  observed {o['amx']}/{o['avx']}/{o['fpga']}  {'MATCH' if ok else 'DIFF'}")
        # totals over 52 layers: 13 full + 39 sliding
        for key in ("ready_avx", "ready_avx_full", "pending_avx", "ready_avx_visits", "pending_avx_visits", "amx_visits"):
            tot = 13 * st[(cls, "full")][key] + 39 * st[(cls, "sliding")][key]
            o = OBS[P]["totals"][cls][key]
            print(f"  {cls:6s} total {key:20s} model {tot:12d} observed {o:12d}  {'MATCH' if tot == o else 'DIFF'}")
        emp = 13 * st[(cls, "full")]["empty"] + 39 * st[(cls, "sliding")]["empty"]
        print(f"  {cls:6s} total empty visits        model {emp:12d} observed            0")
