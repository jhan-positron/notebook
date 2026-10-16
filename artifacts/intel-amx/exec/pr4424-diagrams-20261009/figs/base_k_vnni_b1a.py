"""B1a of the k_vnni page: the hierarchy travel from the K of one KV page down
to one dimension pair, with the token block and the dimension step marked
where they cut the grid. Added 2026-10-09 on jhan's request (kept separate
from base_k_vnni.py so that the two can be edited independently)."""
from svg_helpers import (C, arrow, card_arrow, cite, figure, line, lines,
                         marker_defs, rect, text)

HI = C["hi_fill"]


def b1a():
    fid = "k_vnni-b1a"
    W, H = 1000, 1010
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    boxes = []

    # ---- level 1: the K of one KV page for one slot = n_kv_heads planes ----
    o.append(text(20, 24, "1. the K of one KV page, one storage slot:", 12.5, weight=700))
    o.append(text(20, 40, "n_kv_heads kv_blocks, one K plane each", 12.5, weight=700))
    sx, sy = 30, 56
    for k in (3, 2, 1):
        o.append(rect(sx + 7 * k, sy + 7 * k, 150, 98, "#fff", C["line"], 1, 4))
    o.append(rect(sx, sy, 150, 98, C["vnni_fill"], C["vnni"], 1.4, 4))
    o.append(text(sx + 75, sy + 20, "kv_block(slot 5,", 10.5, "middle", True, weight=600))
    o.append(text(sx + 75, sy + 34, "kv_head 0, page 7).k", 10.5, "middle", True, weight=600))
    o.append(text(sx + 75, sy + 52, "the K plane: 64 tokens", 9.5, "middle"))
    o.append(text(sx + 75, sy + 65, "x 128 dimensions of bf16", 9.5, "middle"))
    o.append(text(sx + 75, sy + 78, "= 16 KiB", 9.5, "middle"))
    o.append(cite(sx + 146, sy + 94, "k_vnni.hpp:24-28"))
    o.append(text(sx + 90, sy + 130, "behind it: kv_head 1 .. n_kv_heads - 1", 9.5, "middle", fill=C["muted"]))
    o.append(text(sx + 90, sy + 143, "(one plane per KV head, same page)", 9.5, "middle", fill=C["muted"]))
    o.append(cite(sx + 90, sy + 158, "kv_cache.hpp:2630-2634, 1811-1817", "middle"))
    boxes.append(("kv_block(slot 5, kv_head 0, page 7).k", "kv_cache.hpp:2630-2634 (page::kv_block per slot and KV head); 2982-2983"))
    o.append(card_arrow(fid, "vnni", [(sx + 165, sy + 45), (sx + 245, sy + 45)], C["vnni"],
                        "1 plane", 0, -6, 1.6))
    o.append(text(sx + 205, sy + 60, "= the grid", 9.5, "middle", fill=C["vnni"]))

    # ---- level 2: the plane as the 64 x 128 grid -----------------------------
    gx, gy, gw, gh = 330, 62, 448, 224     # 128 dims -> 448 px (3.5 px/dim), 64 tokens -> 224 px
    o.append(text(gx, 22, "2. one plane = the [64 x 128] grid: 64 token rows x 128 dimensions",
                  11.5, weight=700))
    o.append(rect(gx, gy, gw, gh, "#fff", C["ink"], 1.2, 2))
    for s in range(4):
        x0 = gx + s * gw / 4
        if s:
            o.append(line(x0, gy, x0, gy + gh, C["vnni"], 1.2, "4 3"))
        o.append(text(x0 + gw / 8, gy - 4, f"s = {s}: dims {32*s}..{32*s+31}", 8.5, "middle", fill=C["vnni"], weight=600))
    for c in range(4):
        y0 = gy + c * gh / 4
        if c:
            o.append(line(gx, y0, gx + gw, y0, C["rm"], 1.2, "4 3"))
        o.append(text(gx + gw + 6, y0 + gh / 8 + 4, f"c = {c}: tokens {16*c}..{16*c+15}", 8.5, fill=C["rm"], weight=600))
    o.append(text(gx + gw / 2, gy - 18, "dimension step s = dim / 32 (4 bands of 32 columns)", 8.5, "middle", fill=C["vnni"]))
    o.append(text(gx + gw + 6, gy + gh + 12, "token block c = token / 16", 8.5, fill=C["rm"]))
    o.append(text(gx + gw + 6, gy + gh + 23, "(4 bands of 16 rows)", 8.5, fill=C["rm"]))
    for s in range(4):
        for c in range(4):
            x0, y0 = gx + s * gw / 4, gy + c * gh / 4
            hi = (s == 2 and c == 2)
            if hi:
                o.append(rect(x0 + 1, y0 + 1, gw / 4 - 2, gh / 4 - 2, HI, C["ink"], 1.8, 2))
            o.append(text(x0 + gw / 8 + (12 if s == 2 else 0), y0 + gh / 8 + 4, f"panel ({s},{c}) #{4*s+c}",
                          8.5, "middle", True, weight=700 if hi else None, fill=C["ink"] if hi else C["muted"]))
    ty = gy + 37 * gh / 64 + gh / 128
    dx = gx + 70 * gw / 128 + gw / 256
    o.append(line(gx, ty, gx + gw, ty, C["rm"], 0.8))
    o.append(line(dx, gy, dx, gy + gh, C["vnni"], 0.8))
    o.append(rect(dx - 2, ty - 2, 4, 4, C["ink"], C["ink"], 0.5, 0))
    o.append(text(gx - 6, ty + 3, "token 37", 8.5, "end", fill=C["rm"]))
    o.append(text(dx, gy + gh + 11, "dim 70", 8.5, "middle", fill=C["vnni"]))
    o.append(lines(gx, gy + gh + 36, [
        "the two cuts: a dimension step s = dim / 32 cuts the columns into 4 bands (blue dashed);",
        "a token block c = token / 16 cuts the rows into 4 bands (orange dashed). The 4 x 4 cells are",
        "the 16 panels: panel (s, c) = block c's 16 tokens x step s's 32 dimensions, index 4 s + c."],
        9.5, 12))
    o.append(cite(gx + gw, gy + gh + 74, "k_vnni.hpp:24-32, 68-74, 78-82"))
    boxes.append(("one plane = the [64 x 128] grid", "k_vnni.hpp:24-28 (64 tokens x 128 dimensions of bf16 = 16 KiB)"))
    boxes.append(("dimension step s", "k_vnni.hpp:70-74 (STEP_DIMS_32, DIM_STEPS_4: s = dim / 32)"))
    boxes.append(("token block c", "k_vnni.hpp:68-69 (BLOCK_TOKENS_16, TOKEN_BLOCKS_4: c = token / 16); 30-32"))
    boxes.append(("panel (s,c) #4s+c", "k_vnni.hpp:29-30, 78-82 (one (s, c) is one 1 KiB panel, index s * 4 + c)"))

    # ---- level 3: zoom into panel (2,2): 16 tokens x 32 dims = 16 pairs ------
    ax = gx + 1.5 * gw / 4
    o.append(card_arrow(fid, "ink", [(ax, gy + gh + 84), (ax, gy + gh + 104)], C["ink"],
                        "1 plane -> 4 x 4 = 16 panels; zoom into panel (2,2) #10", 0, -8))
    zy = 410
    o.append(text(20, zy, "3. one panel = 16 tokens x 32 dims = 512 bf16 = 1 KiB; 16 pairs per token row",
                  12, weight=700))
    px, py, pw, ph = 120, zy + 32, 384, 192          # 16 pairs -> 384 px (24 px), 16 tokens -> 192 px (12 px)
    o.append(rect(px, py, pw, ph, HI, C["ink"], 1.4, 2))
    for dp in range(16):
        x0 = px + dp * 24
        if dp:
            o.append(line(x0, py, x0, py + ph, C["vnni"], 0.9 if dp % 2 == 0 else 0.4, None if dp % 2 == 0 else "2 2"))
        if dp in (0, 3, 15):
            o.append(text(x0 + 12, py - 4, f"dp {dp}", 8.5, "middle", fill=C["vnni"], weight=700 if dp == 3 else None))
    for t in range(16):
        y0 = py + t * 12
        if t:
            o.append(line(px, y0, px + pw, y0, C["rm"], 0.4, "2 2"))
        if t in (0, 5, 15):
            o.append(text(px - 5, y0 + 9, f"t = {t}" + (" (token 37)" if t == 5 else ""), 8.5, "end",
                          fill=C["rm"], weight=700 if t == 5 else None))
    o.append(rect(px + 3 * 24, py + 5 * 12, 24, 12, C["vnni"], C["ink"], 1.2, 0))
    o.append(text(px + 3 * 24 + 12, py + 5 * 12 + 9, "70|71", 7.5, "middle", True, fill="#fff", weight=700))
    o.append(line(px + 3 * 24, py - 14, px + 3 * 24, py + ph + 4, C["ink"], 1.2))
    o.append(line(px + 4 * 24, py - 14, px + 4 * 24, py + ph + 4, C["ink"], 1.2))
    o.append(text(px + 3 * 24 + 12, py + ph + 16, "pair dp = 3 = dims 70, 71", 8.5, "middle", fill=C["ink"], weight=600))
    o.append(lines(30, py + ph + 34, [
        "columns: the step's 32 dimensions 64..95 in 16 pairs dp = (dim % 32) / 2;",
        "a pair = dims 2 dp, 2 dp + 1. rows: the block's 16 tokens t = token % 16",
        "(tokens 32..47). One cell = one pair of one token = 2 bf16 = 4 bytes."],
        9.5, 12))
    o.append(cite(px + pw, py + ph + 72, "k_vnni.hpp:63-65, 73, 134-137"))
    boxes.append(("pair dp", "k_vnni.hpp:63-64 (PAIR_2: the two values of one dimension pair share one 32-bit lane); 73 (STEP_PAIRS_16)"))

    # ---- level 4: the VNNI form of the panel: 16 pair rows x 16 dwords --------
    vx, vy, vw, vh = 600, py, 336, 192   # 16 dwords -> 336 px (21 px), 16 pair rows -> 192 px (12 px)
    o.append(arrow(fid, "vnni", [(px + pw + 14, py + ph / 2), (vx - 16, py + ph / 2)], C["vnni"], 1.6))
    o.append(text((px + pw + vx) / 2, py + ph / 2 - 24, "VNNI form:", 9, "middle", fill=C["vnni"], weight=600))
    o.append(text((px + pw + vx) / 2, py + ph / 2 - 12, "the cell grid", 8.5, "middle", fill=C["vnni"]))
    o.append(text((px + pw + vx) / 2, py + ph / 2 + 14, "turned so that", 8.5, "middle", fill=C["vnni"]))
    o.append(text((px + pw + vx) / 2, py + ph / 2 + 25, "a pair is a row", 8.5, "middle", fill=C["vnni"]))
    o.append(text(vx, zy + 2, "4. the same panel in the VNNI form: 16 pair rows", 11, weight=700, fill=C["vnni"]))
    o.append(text(vx, zy + 15, "1 panel -> 16 pair rows (STEP_PAIRS_16)", 9, fill=C["vnni"], weight=600))
    o.append(rect(vx, vy, vw, vh, C["vnni_fill"], C["vnni"], 1.4, 2))
    for dp in range(16):
        y0 = vy + dp * 12
        if dp:
            o.append(line(vx, y0, vx + vw, y0, C["vnni"], 0.9))
        if dp in (0, 3, 15):
            o.append(text(vx + vw + 5, y0 + 9, f"dp {dp}", 8.5, fill=C["vnni"], weight=700 if dp == 3 else None))
    o.append(text(vx + vw + 5, vy - 4, "pair row", 8.5, fill=C["vnni"]))
    for t in range(16):
        x0 = vx + t * 21
        if t:
            o.append(line(x0, vy, x0, vy + vh, C["vnni"], 0.4, "2 2"))
        if t in (0, 5, 15):
            o.append(text(x0 + 10, vy - 4, f"t = {t}", 8.5, "middle", fill=C["rm"], weight=700 if t == 5 else None))
    o.append(rect(vx, vy + 3 * 12, vw, 12, "none", C["ink"], 2.6, 0))
    o.append(rect(vx + 5 * 21, vy + 3 * 12, 21, 12, C["vnni"], C["ink"], 1.2, 0))
    o.append(text(vx + 5 * 21 + 10, vy + 3 * 12 + 9, "70|71", 7, "middle", True, fill="#fff", weight=700))
    o.append(lines(vx, vy + vh + 16, [
        "one pair row = one dimension pair dp of the block's 16 tokens",
        "= 16 dwords = 64 bytes: one cache line, one AMX B tile row.",
        "thick frame: pair row 3 (dims 70, 71); dark cell: dword t = 5,",
        "token 37. Rows are 64 B apart (pair_row_offsets)."],
        9.5, 12))
    o.append(cite(vx + vw + 60, vy + vh + 72, "k_vnni.hpp:66-67, 75-77, 303-310"))
    boxes.append(("pair row dp (VNNI form)", "k_vnni.hpp:66-67 (one 64-byte line holds one dimension pair of 16 consecutive tokens); 75-77; 29-30"))
    boxes.append(("dword t (one token's pair)", "k_vnni.hpp:30-31 (token i owns column i % 16 in every panel); 65 (DWORD_BYTES_4)"))

    # ---- level 5: one dword = one pair --------------------------------------
    ey = 748
    axx = vx + 5 * 21 + 10
    o.append(arrow(fid, "ink", [(axx, vy + vh + 78), (axx, ey - 22)], C["ink"], 1.4))
    o.append(text(axx - 8, (vy + vh + 78 + ey - 22) / 2 + 4, "1 pair row -> 16 dwords, 1 per token; 1 dword -> 2 bf16",
                  9.5, "end", fill=C["ink"], weight=600))
    o.append(text(20, ey, "5. one dword = one pair: the two bf16 of dimensions 70 and 71 of token 37 = 4 bytes, one 32-bit lane",
                  12.5, weight=700))
    bx, by = 30, ey + 14
    o.append(rect(bx, by, 150, 36, C["vnni"], C["ink"], 1.2, 2))
    o.append(text(bx + 75, by + 15, "low half j = 0", 9.5, "middle", fill="#fff", weight=600))
    o.append(text(bx + 75, by + 29, "K[37][70] (bf16)", 9.5, "middle", True, fill="#fff"))
    o.append(rect(bx + 150, by, 150, 36, C["vnni"], C["ink"], 1.2, 2))
    o.append(text(bx + 225, by + 15, "high half j = 1", 9.5, "middle", fill="#fff", weight=600))
    o.append(text(bx + 225, by + 29, "K[37][71] (bf16)", 9.5, "middle", True, fill="#fff"))
    o.append(text(bx + 310, by + 23, "= dword 5 of pair row 3 of panel #10 (j = dim % 2)", 10))
    o.append(cite(bx + 300, by + 50, "k_vnni.hpp:63-65, 87-90"))
    boxes.append(("low half j = 0 / high half j = 1", "k_vnni.hpp:63-65, 87-90 (PAIR_2, DWORD_BYTES_4; the even value in the low half of the dword, the odd value in the high half)"))

    # ---- the formula as the travel ------------------------------------------
    fy = ey + 70
    o.append(rect(20, fy, 960, 92, C["soft"], C["ink"], 1.2, 4))
    o.append(text(32, fy + 18, "the travel as the index formula: index(token 37, dim 70)", 11, weight=700, mono=True))
    o.append(lines(32, fy + 35, [
        "step s = 70 / 32 = 2   block c = 37 / 16 = 2   -> panel 4 s + c = 10        (level 2: which panel)",
        "pair dp = (70 % 32) / 2 = 3                     -> pair row 3 of that panel   (levels 3 and 4: which row)",
        "token t = 37 % 16 = 5   j = 70 % 2 = 0          -> dword 5, low half          (levels 4 and 5: which dword, which half)",
        "index = (((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j = (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2 + 0 = 5226 (bf16) = byte 10452"],
        9.5, 13, mono=True))
    o.append(cite(976, fy + 88, "k_vnni.hpp:27-28, 132-141"))
    boxes.append(("the travel as the index formula", "k_vnni.hpp:27-28 (the formula in the header comment), 132-141 (k_vnni::index)"))

    # ---- the other carving: the row-major form of a block --------------------
    ry = fy + 104
    o.append(rect(20, ry, 960, 60, "#fff", C["rm"], 1.4, 4))
    o.append(text(32, ry + 17, "the other carving of the same 4 KiB: the row-major form of a block (Note [Row-major tail block])",
                  10.5, weight=700, fill=C["rm"]))
    o.append(lines(32, ry + 33, [
        "Until block c has all 16 rows saved, its 4 panels (s, c) hold token rows instead: panel (t / 4, c) holds the",
        "256-byte rows of tokens 4 (t / 4) .. 4 (t / 4) + 3 of the block. Then a panel is not a 16 x 32 cell of the grid (B4, K8)."],
        9.5, 12))
    o.append(cite(976, ry + 56, "k_vnni.hpp:437-445, 462-472"))
    boxes.append(("the row-major form of a block", "Note [Row-major tail block] (k_vnni.hpp:437-456); row_major_row 462-472"))

    cap = ("B1a, the hierarchy travel. Level 1: the K of one KV page for one storage slot is one plane per KV head. "
           "Level 2: a plane is the 64 x 128 grid of one KV head; a dimension step s cuts its columns into 4 bands of "
           "32 dimensions, a token block c cuts its rows into 4 bands of 16 tokens, and a panel is one of the 16 cells. "
           "Level 3: inside a panel the 32 dimensions are 16 pairs. Level 4: the VNNI form stores the panel as 16 pair "
           "rows of 64 bytes, one per pair, 16 tokens across. Level 5: one dword of a pair row is one pair of one token. "
           "The worked example (token 37, dimension 70) is followed through every level and through the index formula.")
    legend = [
        ("vnni", "blue: the K plane (level 1), a dimension step cut (blue dashed line), the VNNI form of the panel (level 4)"),
        ("solid blue cell with ink outline: the worked example's pair (dims 70, 71 of token 37) and its two bf16 halves", C["vnni"], C["ink"], False, False),
        ("the worked example's panel (2,2) #10 (levels 2 and 3)", HI, C["ink"], False, False),
        ("white grid with ink frame: the plane as the 64 x 128 grid of panels; thin lines: the token-37 row (orange) and the dim-70 column (blue)", "#fff", C["ink"], False, False),
        ("black dot: where the token-37 row meets the dim-70 column", C["ink"], C["ink"], False, False),
        ("thick ink outline: pair row 3, the row of the worked example's pair", "none", C["ink"], False, True),
        ("orange: a token block cut (orange dashed line), token labels, and the row-major form of a block", "#fff", C["rm"], False, False),
        ("ctx_ink", "grey box: the index formula written out for the worked example"),
        ("lane", "the planes of the other KV heads behind the first (thin grey outline)"),
        ("blue arrow: one plane is the grid; the VNNI form of the panel", "arrow", C["vnni"]),
        "arrow", "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "The hierarchy from the K of one page down to one dimension pair",
                  "".join(o), cap, boxes=boxes, legend=legend)
