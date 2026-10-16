"""Change diagrams of unit c0 (kv_cache.hpp page of PR 4959): the design Notes.

Comment-only unit (head lines 711-850: the layout state paragraph of Note
[K VNNI storage], Note [Row-major blocks under hardware attention], and the
consumer list rewritten; 132 added comment lines, 30 removed).
Two figures:
  d0a: the two design decisions the Notes record, drawn on the B4 state strip:
       the transition at 16 saved rows (a per-token cost strip, 754-761) and
       the hardware-attention branch (765-769, 784-787).
  d0b: the map from every paragraph and numbered item of the Notes to the base
       diagrams B1-B5 that draw it, with the head lines each paragraph covers.
Every label is an identifier or a comment phrase of the code; every box cites
the head line that holds it.
"""
from svg_helpers import (C, arrow, block_cell, cite, figure, line, lines,
                         marker_defs, rect, text, text_width)
from base_kv_cache import fit, state_box

BASE = ("Updates B4: the two design decisions of the Notes are drawn on the B4 "
        "state strip: the transition at 16 saved rows (a per-token cost strip: 4 "
        "whole lines for a row-major tail block against 64 lines for the VNNI "
        "column) and the hardware-attention branch (no row bit from a short run, "
        "while a whole-block save still sets its bits). The second figure is an "
        "index of every paragraph of the Notes against the base diagram that draws it.")

W = 700


# ---- d0a: the two decisions ------------------------------------------------------
def token_row_lines(o, x, y, w):
    """One token row of a row-major tail block: 4 whole 64-byte lines."""
    for r in range(4):
        o.append(rect(x, y + r * 13, w, 10, C["rm_fill"], C["rm"], 1, 2))
        o.append(text(x + w / 2, y + r * 13 + 8, f"line {r}: 64 B (32 dimensions)", 8.5,
                      "middle"))


def vnni_column_lines(o, x, y, cw, ch, hi_col):
    """The 64 lines of a block's four panels (16 pair rows each) with one
    token's 4-byte slot marked in every line."""
    for s in range(4):
        px = x + s * (16 * cw + 8)
        for r in range(16):
            ry = y + r * (ch + 0.6)
            for c in range(16):
                f = C["vnni"] if c == hi_col else "#fff"
                o.append(rect(px + c * cw, ry, cw, ch, f, C["vnni"], 0.35, 0))
        o.append(text(px + 8 * cw, y + 16 * (ch + 0.6) + 9, f"panel (s = {s}, c)", 8.5,
                      "middle", True, fill=C["muted"]))


def fig_a():
    fid = "kv_cache-d0a"
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "pend": C["pend"],
                           "vnni": C["vnni"], "hw": C["hw"]})]
    boxes = []
    o.append(text(12, 16, "The two design decisions of the Notes, drawn on the B4 state strip",
                  12, weight=700))

    # ---- A: why the transition is at 16 saved rows -------------------------------
    ay = 36
    o.append(text(12, ay, "A. Why the transition is at 16 saved rows", 11, weight=700))
    o.append(cite(688, ay, "kv_cache.hpp:754-761"))
    o.append(text(12, ay + 14, "in decode every step saves one token per user, and the "
                  "tail block of every user is read again on every step [754-755]", 9,
                  fill=C["muted"]))
    # left: the row-major tail block, per token
    lx, ly, lw, lh = 12, ay + 24, 300, 132
    o.append(rect(lx, ly, lw, lh, "#fff", C["rm"], 1.2, 4))
    o.append(text(lx + 8, ly + 14, "row-major tail block: one token row", 10, weight=700,
                  fill=C["rm"]))
    token_row_lines(o, lx + 8, ly + 22, 150)
    o.append(lines(lx + 166, ly + 34, ["4 whole lines per token", "to store, to score", "and to stage for the FPGA"],
                   9, 11))
    o.append(text(lx + 8, ly + 100, "store_row_major, the dotter, k_row_if_row_major", 8.5,
                  fill=C["muted"]))
    o.append(cite(lx + lw - 4, ly + lh - 4, "kv_cache.hpp:756-757"))
    boxes.append(("row-major tail block costs 4 whole lines per token to store, to score "
                  "and to stage", "kv_cache.hpp:756-757"))
    # right: the VNNI column, per token
    rx, rw = 328, 360
    o.append(rect(rx, ly, rw, lh, "#fff", C["vnni"], 1.2, 4))
    o.append(text(rx + 8, ly + 14, "VNNI column: the same token in a converted block", 10,
                  weight=700, fill=C["vnni"]))
    vnni_column_lines(o, rx + 8, ly + 22, 4.6, 2.6, 5)
    o.append(text(rx + 8, ly + 100, "64 lines, 4 bytes in each: a VNNI column costs 64 "
                  "lines each (issue #4500)", 8.5, fill=C["muted"]))
    o.append(text(rx + 8, ly + 111, "store_row (4 scatters), load_row (4 gathers) per token",
                  8.5, fill=C["muted"]))
    o.append(cite(rx + rw - 4, ly + lh - 4, "kv_cache.hpp:757; tensor/k_vnni.hpp:311-345"))
    boxes.append(("a VNNI column costs 64 lines each (issue #4500)",
                  "kv_cache.hpp:757; store_row / load_row tensor/k_vnni.hpp:311-345"))
    # the B4 strip with the transition (the sentence above it sits 16 px under
    # the two boxes of part A, so that it reads as the strip's introduction)
    sy = ly + lh + 52
    sw, sh = 150, 64
    sx = [12, 186, 360, 534]
    states = [("empty", "empty", "no row saved", "kv_cache.hpp:2639-2648"),
              ("rm", "incomplete, row-major", "1..15 row bits, bit clear",
               "kv_cache.hpp:711-720"),
              ("pend", "complete, may wait", "for its conversion", "kv_cache.hpp:718-719"),
              ("vnni", "converted: VNNI", "16 row bits, block bit set", "kv_cache.hpp:2649-2653")]
    for x, (st, t1, t2, ref) in zip(sx, states):
        o.append(state_box(x, sy, sw, sh, st, t1, t2, ref))
    boxes += [("k_rows_saved_ bits all clear: the empty state", "kv_cache.hpp:2639-2648"),
              ("incomplete block: row-major rows (row-major tail block)",
               "kv_cache.hpp:711-720; model.hpp:3298; Note [Row-major tail block] "
               "(tensor/k_vnni.hpp:403-421)"),
              ("complete, may wait for its conversion", "kv_cache.hpp:718-719"),
              ("k_vnni_blocks_ bit set: the converted (VNNI) state", "kv_cache.hpp:2649-2653")]
    am = sy + 26
    labels = [("rm", C["rm"], ["rows 1..15: 4 lines", "each, no transpose"]),
              ("pend", C["pend"], ["16th row: queued", "(note_k_row_saved)"]),
              ("vnni", C["vnni"], ["forward end: block_to_vnni", "once, 4 KiB [758-761]"])]
    for i, (name, col, lab) in enumerate(labels):
        o.append(arrow(fid, name, [(sx[i] + sw + 2, am), (sx[i + 1] - 2, am)], col, 1.6))
        o.append(lines((sx[i] + sw + sx[i + 1]) / 2, sy - 16, lab, 8.5, 10, "middle",
                       fill=col, weight=700))
    o.append(text(sx[0] + sw + 4, sy - 36, "the transition: a block is transposed once, after "
                  "its 16th row, not on every row", 9, weight=600))
    ny = sy + sh + 16
    nA = ["A page is dense for the AMX kernel only when all its 64 rows are saved: it is VNNI "
          "from the forward end of the pass",
          "that completed its last block (at once when that block was a whole-block save), "
          "and takes the software loop until then."]
    for s in nA:
        fit(s, 9, 676, False, "nA")
    o.append(lines(12, ny, nA, 9, 11))
    o.append(cite(688, ny + 22, "kv_cache.hpp:758-761"))
    boxes.append(("A page is dense for that kernel only when all its 64 rows are saved",
                  "kv_cache.hpp:758-761"))

    # ---- B: row-major blocks under hardware attention ---------------------------
    by = ny + 48
    o.append(line(12, by - 14, 688, by - 14, C["line"]))
    o.append(text(12, by, "B. Row-major blocks under hardware attention", 11, weight=700))
    o.append(cite(688, by, "kv_cache.hpp:763-798"))
    ty = by + 64
    o.append(state_box(12, ty, sw, sh, "empty", "empty", "no row saved", "kv_cache.hpp:2639-2648"))
    hx, hw = 290, 250
    o.append(state_box(hx, ty, hw, sh, "hw", "records no row bits: stays row-major",
                       "no row bit from a short run, no queued block", "kv_cache.hpp:765-769"))
    boxes.append(("records no row bits: stays row-major (hardware attention)",
                  "Note [Row-major blocks under hardware attention] (kv_cache.hpp:765-769)"))
    o.append(arrow(fid, "hw", [(12 + sw + 2, ty + 26), (hx - 2, ty + 26)], C["hw"], 1.6))
    gm = (12 + sw + hx) / 2
    o.append(lines(gm, ty + 42, ["short run: set_k_row", "stores row-major; the",
                                 "note_k_row_saved loop", "is skipped: no bit"], 8.5, 10,
                   "middle", fill=C["hw"], weight=700))
    o.append(cite(gm, ty + 84, "model.hpp:3419", "middle"))
    boxes.append(("cached_operation_uses_hw (the note_k_row_saved loop is skipped)",
                  "model.hpp:3414-3419 (the skip and its comment); cached_operation_uses_hw "
                  "defined at model.hpp:1529"))
    o.append(state_box(548, ty, sw, sh, "vnni", "converted: VNNI", "16 row bits, block bit set",
                       "kv_cache.hpp:2649-2653"))
    # the arc: whole-block saves still store VNNI
    o.append(arrow(fid, "vnni", [(60, ty - 2), (60, ty - 30), (618, ty - 30), (618, ty - 2)],
                   C["vnni"], 1.6))
    o.append(text(380, ty - 46, "Whole-block saves (prefill) still store the VNNI layout at "
                  "once: set_k_block, then note_k_block_saved", 9, "middle", fill=C["vnni"],
                  weight=700))
    o.append(cite(380, ty - 35, "kv_cache.hpp:784-787; model.hpp:3331-3333", "middle"))
    boxes.append(("Whole-block saves (prefill) still store the VNNI layout at once",
                  "kv_cache.hpp:784-787; model.hpp:3331-3333"))
    # why, and the cost accepted
    wy = ty + sh + 44
    o.append(rect(12, wy, 332, 96, C["soft"], C["line"], 1, 4))
    o.append(text(20, wy + 14, "Why", 10, weight=700))
    why = ["past the engagement point the FPGA holds the K/V",
           "of every DMA-complete GOF; the CPU scores only",
           "the tail above them, row by row in a row-major",
           "block. What the conversion would cost: a serial",
           "main-thread copy per completed block at the forward",
           "end, and a 64-line gather per staged converted row"]
    for s in why:
        fit(s, 9, 316, False, "why")
    o.append(lines(20, wy + 28, why, 9, 11))
    o.append(cite(340, wy + 92, "kv_cache.hpp:770-783"))
    boxes.append(("the CPU scores only the tail above them; What the conversion would cost",
                  "kv_cache.hpp:770-783"))
    o.append(rect(356, wy, 332, 96, C["soft"], C["line"], 1, 4))
    o.append(text(364, wy + 14, "The cost accepted", 10, weight=700))
    cost = ["a range the software scores although the operation",
            "is a hardware one scores the blocks decode",
            "completed with the row-major dotter, where the",
            "conversion would have let the AMX kernel score a",
            "page of them; the fp32 add order of the dotter and",
            "of k_vnni::qk_group differs"]
    for s in cost:
        fit(s, 9, 316, False, "cost")
    o.append(lines(364, wy + 28, cost, 9, 11))
    o.append(cite(684, wy + 92, "kv_cache.hpp:788-798"))
    boxes.append(("The cost accepted: the row-major dotter scores the blocks decode completed",
                  "kv_cache.hpp:788-798"))
    H = wy + 96 + 12
    cap = ("Updates B4: the two design decisions the Notes record, drawn on the B4 state "
           "strip. Part A is why a block is transposed once, after its 16th row: a "
           "row-major tail block costs 4 whole 64-byte lines per token to store, to score "
           "and to stage, where the VNNI column costs 64 lines per token. Part B is the "
           "hardware-attention branch: a short run under a hardware-scored operation "
           "records no row bit, so such a block stays row-major, while a whole-block "
           "save still stores the VNNI layout and sets its bits [kv_cache.hpp:754-761, "
           "765-769, 784-787; model.hpp:3333, 3419].")
    legend = [
        ("rm", "orange: the four 64-byte lines of one token row of the row-major tail "
               "block (part A, left), and the state incomplete, row-major (1..15 row "
               "bits, bit clear)"),
        ("white box, orange outline: the frame of the row-major tail block (part A, "
         "left); its title in bold orange", "#fff", C["rm"], False, False),
        ("vnni_solid", "solid blue: the same token's 4-byte slot in each of the 64 lines "
                       "of a converted block (part A, right)"),
        ("white box, blue outline: the frame of the VNNI column, and the 4-byte slots "
         "of the other tokens in every panel (s, c); its title in bold blue",
         "#fff", C["vnni"], False, False),
        ("empty", "grey dashed: the state empty (no row saved), the first state of the "
                  "strip in parts A and B"),
        ("pend", "orange-red dashed: the state complete, may wait for its conversion "
                 "(16 row bits, block bit clear)"),
        ("vnni", "blue: the state converted: VNNI (16 row bits, block bit set), the last "
                 "state of the strip in parts A and B"),
        ("hw", "yellow: the state under hardware attention, records no row bits: stays "
               "row-major (part B)"),
        ("orange arrow and label: empty -> incomplete, row-major (rows 1..15: 4 lines "
         "each, no transpose)", "arrow", C["rm"]),
        ("orange-red arrow and label: incomplete -> complete, may wait (16th row: "
         "queued, note_k_row_saved)", "arrow", C["pend"]),
        ("blue arrow and label: complete -> converted (forward end: block_to_vnni "
         "once), and in part B the arc of whole-block saves (set_k_block, then "
         "note_k_block_saved)", "arrow", C["vnni"]),
        ("yellow arrow and label: empty -> records no row bits (short run: set_k_row "
         "stores row-major, the note_k_row_saved loop is skipped)", "arrow", C["hw"]),
        ("ctx", "grey box, thin grey outline: the two notes of part B, Why and The cost "
                "accepted (kv_cache.hpp:770-798)"),
        ("font_mono", "monospace = the panel names panel (s, c) of the VNNI column"),
        ("font_sans", "sans-serif = the state names, the arrow labels and the prose "
                      "of parts A and B"),
        ("font_cite", "small grey monospace = the head lines each box cites "
                      "(kv_cache.hpp:754-761, model.hpp:3419, ...)"),
    ]
    return figure(fid, W, H, "The two design decisions of the Notes on the B4 state strip",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- d0b: the paragraph map -------------------------------------------------------
FID = "kv_cache-d0b"
# the paragraph column and the label band of the five base diagrams
PX, PW, PH = 12, 448, 32
CHIP_X0, CHIP_PITCH, CHIP_W, CHIP_H = 502, 38, 30, 18

B_NAMES = [("B1", "data model"), ("B2", "one block, two layouts"),
           ("B3", "function model"), ("B4", "sequencing model"),
           ("B5", "interaction model")]

# One row per paragraph or numbered item: (title = the comment's opening
# phrase, one-line description, head lines, base diagrams that draw it).
NOTE1 = ("Note [K VNNI storage]: the new paragraph", "kv_cache.hpp:711-761", [
    ("A block holds the VNNI layout only once it is complete and converted",
     "page records k_rows_saved_ and k_vnni_blocks_ per storage slot",
     (711, 720), "B1 B2 B4"),
    ("- save_k sets a row's bit after the row is stored, on the main thread",
     "queued and converted at the forward end; why not in save_k",
     (721, 738), "B3 B4 B5"),
    ("- a full-block save (page::set_k_block) writes the VNNI layout directly",
     "no bit; note_k_block_saved after every head [any window thread]",
     (739, 745), "B3 B4 B5"),
    ("- clear_kv_complete_at (a new token takes a page offset) drops the row bits",
     "bits at and above; a converted block goes back to rows first",
     (746, 752), "B3 B4 B5"),
    ("- page copies (copy_from) carry both bit sets with the rows",
     "(one sentence; the mechanics are consumer item 5 below)",
     (753, 753), "B3 B4"),
    ("Why the transition is at 16 saved rows",
     "tail block: 4 lines per token where the VNNI column costs 64",
     (754, 761), "B2 B4"),
])
NOTE2 = ("Note [Row-major blocks under hardware attention]", "kv_cache.hpp:763-798", [
    ("When the hardware attention scores an operation's K: no row bits",
     "no row bit from a short run, no queued block; stays row-major",
     (765, 769), "B3 B4"),
    ("Why: past the engagement point the FPGA holds the K/V of every GOF",
     "the CPU scores only the tail; what the conversion would cost",
     (770, 783), "B4"),
    ("Whole-block saves (prefill) still store the VNNI layout at once",
     "a page the hardware does not cover yet is dense through them",
     (784, 787), "B4"),
    ("The cost accepted: the row-major dotter scores blocks decode completed",
     "the fp32 add order of the dotter and of k_vnni::qk_group differs",
     (788, 798), "B3 B4"),
])
ITEMS = ("Consumers of a VNNI slot (rewritten)", "kv_cache.hpp:800-850", [
    ("1. save_k: set_k_block for a whole 16-token block, set_k_row row by row",
     "store_block or store_row_major; the idle main helpers may share",
     (801, 812), "B3 B5"),
    ("2. the dense AMX page path passes page::k_packed to qk_vnni_128x4",
     "when page::k_vnni_blocks says every block is converted",
     (813, 818), "B3 B5"),
    ("3. every other visit reads the VNNI blocks with k_vnni::qk_group",
     "tail block tokens: the dotter through row_major_row, 4 lines",
     (819, 828), "B2 B3"),
    ("4. the FPGA staging path: k_row_if_row_major in place, else get_k_row",
     "row in place when row-major; get_k_row gathers into scratch",
     (829, 838), "B3 B5"),
    ("5. page copies: a whole page as one owner assignment, bits included",
     "any other range: block_to_rows, row copy, block_to_vnni",
     (839, 846), "B2 B3 B4"),
    ("6. the row view page::k() does not exist for VNNI slots",
     "set_k_row / get_k_row follow the block's recorded layout",
     (847, 850), "B1 B3"),
])


def chip_x(k):
    """Left x of the label of base diagram B<k+1>."""
    return CHIP_X0 + k * CHIP_PITCH


def chip(x, y, name):
    return (rect(x, y, CHIP_W, CHIP_H, "#fff", C["ink"], 1.1, 3) +
            text(x + CHIP_W / 2, y + 13, name, 9.5, "middle", True, weight=700))


def para_row(y, title, desc, rng, drawn_in):
    """One paragraph: its box (title, one-line description, head lines), an
    arrow that ends at the first base-diagram label that draws it, and a grey
    connector from that label to the last one."""
    a, b = rng
    ref = f"kv_cache.hpp:{a}" if a == b else f"kv_cache.hpp:{a}-{b}"
    o = [rect(PX, y, PW, PH, C["soft"], C["line"], 1, 4)]
    # bold DejaVu Sans is about 0.61 em per char, not the 0.55 of text_width
    fit(title, 9.5, (PW - 12) * 0.55 / 0.61, False, "d0 title")
    fit(desc, 9, PW - 16 - text_width(ref, 8.5, True) - 12, False, "d0 desc")
    o.append(text(PX + 8, y + 12, title, 9.5, weight=600))
    o.append(text(PX + 8, y + 24, desc, 9, fill=C["muted"]))
    o.append(cite(PX + PW - 4, y + PH - 4, ref))
    ym = y + PH / 2
    ks = sorted(int(n[1]) - 1 for n in drawn_in.split())
    if len(ks) > 1:
        o.append(line(chip_x(ks[0]), ym, chip_x(ks[-1]), ym, C["line"], 1))
    o.append(arrow(FID, "ink", [(PX + PW + 3, ym), (chip_x(ks[0]) - 2, ym)], C["ink"], 1.3))
    for k in ks:
        o.append(chip(chip_x(k), ym - CHIP_H / 2, B_NAMES[k][0]))
    return "".join(o), ref


def section(y, title, ref, tag=None):
    o = [text(PX, y, title, 11.5, weight=700)]
    o.append(cite(PX + PW - 4, y, ref))
    if tag:
        o.append(text(chip_x(4) + CHIP_W, y, tag, 9.5, "end", fill=C["new"],
                      weight=700))
    return "".join(o)


def fig_b():
    o = [marker_defs(FID, {"ink": C["ink"]})]
    boxes = []
    # header: column titles and the B1..B5 column labels over the label band
    o.append(text(PX, 14, "paragraph or numbered item of the Notes (head lines)",
                  11, weight=700))
    band_mid = (chip_x(0) + chip_x(4) + CHIP_W) / 2
    o.append(text(band_mid, 14, "drawn in base diagram", 10, "middle", weight=700))
    for k, (nm, _) in enumerate(B_NAMES):
        o.append(text(chip_x(k) + CHIP_W / 2, 32, nm, 10, "middle", True,
                      fill=C["muted"], weight=700))
    y = 50
    for i, (stitle, sref, rows) in enumerate([NOTE1, NOTE2, ITEMS]):
        o.append(section(y, stitle, sref,
                         "new comment text: 132 lines" if i == 0 else None))
        y += 6
        for title, desc, rng, drawn in rows:
            s, ref = para_row(y, title, desc, rng, drawn)
            o.append(s)
            note = "Note [K VNNI storage]" if i == 0 else (
                "Note [Row-major blocks under hardware attention]" if i == 1
                else "Note [K VNNI storage], consumer items")
            boxes.append((title, f"{ref} ({note})"))
            y += PH + 3
        y += 15
    # key: the five base diagrams with their figure ids
    y += 3
    o.append(line(PX, y, chip_x(4) + CHIP_W, y, C["line"]))
    y += 15
    key1 = "   |   ".join(f"{nm} {desc}" for nm, desc in B_NAMES[:3])
    key2 = "   |   ".join(f"{nm} {desc}" for nm, desc in B_NAMES[3:])
    o.append(text(PX, y, key1, 9.5))
    o.append(text(PX, y + 13, key2 + "   (figures kv_cache-b1 to kv_cache-b5 in section 1)",
                  9.5))
    o.append(text(PX, y + 27, "a label B1..B5 = that base diagram draws the paragraph; the "
                  "row's arrow ends at the first of them", 9, fill=C["muted"]))
    H = y + 36
    cap = ("Index of the Notes against B1-B5: the unit is comment text only, the design "
           "record that the five base diagrams draw. Each row is one paragraph or "
           "numbered item of the Notes with its head lines, and its arrow points at the "
           "base diagrams that draw it (the labels B1 to B5). Read down the label "
           "columns: the data and state paragraphs land on B1, B2 and B4, the writers "
           "and consumers on B3 and B5. The kill-switch paragraph (851-855) is unchanged "
           "and not listed.")
    legend = [
        ("ctx", "grey box, thin grey outline: one paragraph or numbered item of the Notes: "
                "its opening phrase in bold, its one-line description in grey, its head "
                "lines at the right"),
        ("box", "white box, ink outline: a base-diagram label B1 to B5 (bold monospace), "
                "one on the row of every paragraph that diagram draws"),
        ("thin grey line between two labels of a row: the paragraph is drawn in both "
         "base diagrams; the arrow ends at the first of them", "line", C["line"]),
        ("arrow", "ink arrow: from a paragraph row to the first base diagram that "
                  "draws it"),
        ("font_mono", "monospace = the base-diagram names B1 to B5 (column heads and "
                      "labels)"),
        ("font_sans", "sans-serif = the opening phrase of each paragraph (bold), its "
                      "one-line description (grey), the section titles and the key"),
        ("font_cite", "small grey monospace = the head lines of each paragraph and "
                      "section (kv_cache.hpp:711-720, ...)"),
        ("font_tag", "bold 'new comment text: 132 lines' = the tag on the first "
                     "section: the unit's 132 comment lines are added by this PR (30 "
                     "lines of the consumer list are removed)"),
    ]
    return figure(FID, W, H, "Map from the paragraphs of the two Notes to the base "
                  "diagrams that draw them", "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
