"""Change diagram of unit k9 of the k_vnni.hpp page: the in-place conversion
of one block (block_to_vnni, block_to_rows; head lines 494-526).

Two figures: k_vnni-d9a (the two conversions through the 4 KiB stack copy) and
k_vnni-d9b (the three callers: thread, when, guard, what it does, the bit it
publishes).

Every label, count and citation comes from facts/k_vnni.json (claims
k_vnni-function-23/24, k_vnni-data-26/42/46/50, k_vnni-sequencing-1/4/5/8/
21/25/34/35/36) or from the head code of k_vnni.hpp, kv_cache.hpp and
model.hpp. Line numbers are head line numbers of h/tron/tensor/k_vnni.hpp
unless another file is named.
"""
from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, lane, line,
                         lines, marker_defs, rect, text, text_width)
from base_k_vnni import (BLOCK_2, KV_HEAD_0, PAGE_7, SLOT_5, lane_block,
                         panel_lines, rm_forms)

BASE = ("Updates B4: steps 2 and 5 (block_to_vnni, block_to_rows) are opened up "
        "to show the 4 KiB stack copy between the read of block 2 and its "
        "in-place rewrite. The copy is needed because panel (0,2) holds tokens "
        "32..35 row-major and dimension step 0 of all 16 tokens VNNI. The second "
        "figure (d9b) updates B5: the three callers as lanes, with the thread rule "
        "and the bit each publishes.")

W = 700
LX, RX, CW = 12, 364, 324          # the two columns
PW, PH, PG = 70, 64, 10            # one panel: 16 lines of 64 B


def _panels4(x, y, forms4, hi_panel=None, **kw):
    """The 4 panels (s, 2) of block 2 side by side, short labels above.
    hi_panel = s: a thick C['pend'] frame round panel (s, 2), the panel whose
    row-major rows (tokens 4 s .. 4 s + 3) still live there when store_block
    writes it (k_vnni.hpp:495-496)."""
    o = []
    for s in range(4):
        px = x + s * (PW + PG)
        o.append(text(px + PW / 2, y - 9, f"({s},{BLOCK_2}) #{4 * s + BLOCK_2}", 9,
                      "middle", True, fill=C["muted"]))
        o.append(panel_lines(px, y, PW, PH, forms4[s], **kw))
    if hi_panel is not None:
        px = x + hi_panel * (PW + PG)
        o.append(rect(px - 5, y - 5, PW + 10, PH + 10, "none", C["pend"], 2, 2))
    return "".join(o)


def _chip(x, y, kind, label):
    """A legend chip: kind = 'rm' | 'vnni' | 'read' | 'overlap' (the thick frame)."""
    if kind == "read":
        r = rect(x, y, 22, 12, "#fff", C["ink"], 1.2, 1, "4 3")
    elif kind == "overlap":
        r = rect(x, y, 22, 12, "#fff", C["pend"], 2, 1)
    else:
        r = rect(x, y, 22, 12, C[kind + "_fill"], C[kind], 1, 1)
    return r + text(x + 28, y + 10, label, 9.5), x + 28 + text_width(label, 9.5) + 16


def _varrow(o, fid, name, color, x, y0, y1, lines_, ref):
    """A vertical how-many arrow at x, its label lines to the right."""
    o.append(arrow(fid, name, [(x, y0), (x, y1)], color, 1.6))
    o.append(lines(x + 10, y0 + 12, lines_, 9, 10.5, fill=color, weight=600))
    o.append(text(x + 10, y0 + 12 + len(lines_) * 10.5, f"[{ref}]", 8.5, mono=True,
                  fill=C["cite"]))


def _fig_a():
    fid = "k_vnni-d9a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "pend": C["pend"]})]
    # ---- title and legend ------------------------------------------------------
    o.append(text(LX, 16, f"worked example: block {BLOCK_2} (tokens 32..47) of the plane "
                  f"of slot {SLOT_5}, KV head {KV_HEAD_0}, page {PAGE_7}", 11, weight=700))
    o.append(text(LX, 30, "left: block_to_vnni; right: its inverse block_to_rows; the "
                  "same 4 KiB is read once and written once, in place", 9.5,
                  fill=C["muted"]))
    x = LX
    for kind, lab in [("rm", "row-major token rows (4 lines each)"),
                      ("vnni", "VNNI pair rows")]:
        svg, x = _chip(x, 40, kind, lab)
        o.append(svg)
    x = LX
    for kind, lab in [("read", "dashed outline: the 4 KiB is read"),
                      ("overlap", "thick outline: panel (0,2): tokens 4 s .. 4 s + 3 "
                                  "still live there")]:
        svg, x = _chip(x, 57, kind, lab)
        o.append(svg)
    # ---- the two function cells -------------------------------------------------
    fy, fh = 80, 62          # two description lines: 62 px clears the tag and cite
    o.append(fn_cell(LX, fy, CW, fh, "block_to_vnni(plane, c)",
                     ["Convert block c from row-major (Note [Row-major",
                      "tail block]) to the VNNI layout, in place"],
                     "k_vnni.hpp:497-509; 494-496", "new"))
    boxes.append(("block_to_vnni(plane, c)", "k_vnni.hpp:497-509; 494-496"))
    o.append(fn_cell(RX, fy, CW, fh, "block_to_rows(plane, c)",
                     ["The inverse: block c from the VNNI layout",
                      "back to row-major, in place"],
                     "k_vnni.hpp:512-524; 511", "new"))
    boxes.append(("block_to_rows(plane, c)", "k_vnni.hpp:512-524; 511"))
    # ---- the byte flow of each column -----------------------------------------
    py1, py2 = 178, 452                    # the two panel rows
    sy, sh = 304, 64                       # the stack box (2 sub-lines + cite)
    rm16 = rm_forms(range(32, 48))         # all 16 token rows saved, row-major
    vnni16 = [["vnni"] * 16 for _ in range(4)]
    cols = [
        dict(x=LX, top=rm16, bot=vnni16, hi=0,
             top_lab="1. read: row-major, 16 row bits set, block bit clear",
             top_ref="k_vnni.hpp:441-445", read_name="rm",
             read=["16 x load_row_major -> rows[t]:",
                   "16 rows x 256 B = 4 KiB read through",
                   "source (the read-only view of plane)"],
             read_ref="k_vnni.hpp:502-506",
             stack_sub=["alignas(LINE_BYTES_64) bf16: 16 x 128 = 4 KiB on the stack",
                        "row_ptrs[t] = rows[t]: the 16 pointers store_block takes"],
             stack_ref="k_vnni.hpp:500-501", write_name="vnni",
             write=["store_block(plane, c, FULL_BLOCK_0XFFFF, row_ptrs):",
                    "4 steps x 16 pair rows = 64 whole-line stores",
                    "= 4 KiB, transposed in registers per step"],
             write_ref="k_vnni.hpp:508; 401-419",
             bot_lab="2. write: VNNI, in place; the caller then sets block bit 2",
             bot_ref="k_vnni.hpp:29-32, 443-445",
             note=["why the stack copy: panel (0,2) #2 holds the rows of tokens",
                   "32..35 in the row-major form and step 0 of tokens 32..47 in",
                   "the VNNI form. store_block writes panel (s,2) while the rows",
                   "of tokens 4 s .. 4 s + 3 still live there [k_vnni.hpp:495-496]"]),
        dict(x=RX, top=vnni16, bot=rm16, hi=None,
             top_lab="1. read: VNNI, block bit 2 set",
             top_ref="k_vnni.hpp:29-32, 443-445", read_name="vnni",
             read=["16 x load_row -> rows[t]:",
                   "16 x 4 gathers of 16 dwords = 4 KiB read",
                   "through source (the read-only view of plane)"],
             read_ref="k_vnni.hpp:516-519",
             stack_sub=["alignas(LINE_BYTES_64) bf16: 16 x 128 = 4 KiB on the stack",
                        "the same array, no row_ptrs"],
             stack_ref="k_vnni.hpp:515", write_name="rm",
             write=["16 x store_row_major(plane, 32 + t, rows[t]):",
                    "16 memcpy of 256 B = 64 whole lines = 4 KiB",
                    "into row_major_row(plane, 32 + t)"],
             write_ref="k_vnni.hpp:520-523; 476-482",
             bot_lab="2. write: row-major in place; caller clears block bit 2",
             bot_ref="k_vnni.hpp:441-445",
             note=["block_to_rows loads all 16 rows before its first",
                   "store_row_major: load_row gathers from the same 4 KiB",
                   "that store_row_major rewrites [k_vnni.hpp:517-523, 444-445].",
                   "a converted block that will receive or lose rows goes back",
                   "to row-major so set_k_row and its readers find the rows",
                   "[kv_cache.hpp:715-716, 806-808]"]),
    ]
    for cdef in cols:
        x = cdef["x"]
        px = x + 7
        # 1. the block as it is: read (dashed)
        o.append(text(x, py1 - 22, cdef["top_lab"], 9.5, weight=600))
        o.append(_panels4(px, py1, cdef["top"], cdef["hi"], read_all=True))
        o.append(cite(px + 4 * PW + 3 * PG, py1 + PH + 12, cdef["top_ref"]))
        boxes.append((f"block 2 panels (s,2), read ({cdef['top_lab'][9:]})",
                      cdef["top_ref"]))
        # read arrow -> stack
        _varrow(o, fid, cdef["read_name"], C[cdef["read_name"]], x + 18, py1 + PH + 8,
                sy - 4, cdef["read"], cdef["read_ref"])
        # the stack array
        o.append(label_box(x, sy, CW, sh, "rows[BLOCK_TOKENS_16][Cols]", cdef["stack_sub"],
                           C["rm_fill"], C["rm"], 10.5, ref=cdef["stack_ref"]))
        boxes.append((f"rows[BLOCK_TOKENS_16][Cols] (stack, {cdef['stack_ref']})",
                      cdef["stack_ref"]))
        # write arrow -> the block in the other form
        _varrow(o, fid, cdef["write_name"], C[cdef["write_name"]], x + 18, sy + sh + 4,
                py2 - 36, cdef["write"], cdef["write_ref"])
        # 2. the block rewritten in place
        o.append(text(x, py2 - 22, cdef["bot_lab"], 9.5, weight=600))
        o.append(_panels4(px, py2, cdef["bot"], cdef["hi"]))
        o.append(cite(px + 4 * PW + 3 * PG, py2 + PH + 12, cdef["bot_ref"]))
        boxes.append((f"block 2 panels (s,2), written ({cdef['bot_lab'][10:]})",
                      cdef["bot_ref"]))
        # the note under the panels
        o.append(lines(x, py2 + PH + 28, cdef["note"], 9, 11, fill=C["ink"]))
    H = py2 + PH + 28 + 6 * 11 + 6
    cap = ("Updates B4: steps 2 and 5 of the worked example are opened up: each column "
           "reads the 4 KiB of block 2 into the stack array rows[16][128], then "
           "rewrites the same 4 KiB in place in the other form. Look at panel (0,2): "
           "it holds the rows of tokens 32..35 in the row-major form and dimension "
           "step 0 of all 16 tokens in the VNNI form, so the rows go to the stack "
           "before store_block writes. The next figure names the three callers.")
    legend = [
        ("rm", "orange: the row-major form of block 2 (one token row = 4 lines of a "
               "panel) and the stack array rows[BLOCK_TOKENS_16][Cols] that holds the "
               "16 rows between the read and the write"),
        ("vnni", "blue: the VNNI form of block 2 (one pair row = 1 line of a panel): "
                 "written by store_block (left), read by load_row (right)"),
        ("thin ink outline: the frame of one panel (s,2) of block 2, 16 lines of 64 B",
         "none", C["ink"], False, False),
        ("dashed ink outline round the four panels: the 4 KiB of block 2 is read "
         "(step 1 of each column)", "none", C["ink"], True, False),
        ("white chip, dashed ink outline: the figure's own key chip for 'the 4 KiB "
         "is read'", "#fff", C["ink"], True, False),
        ("thick orange-red outline: panel (0,2) #2 of the left column, whose row-major "
         "rows (tokens 32..35) still live there when store_block writes it",
         "none", C["pend"], False, False),
        ("white chip, orange-red outline: the figure's own key chip for that panel",
         "#fff", C["pend"], False, False),
        ("box", "white box, ink outline: the two function cells block_to_vnni(plane, c) "
                "and block_to_rows(plane, c); name in bold monospace, description in "
                "sans-serif"),
        ("orange arrow and its orange label: the row-major side of the copy, 16 x "
         "load_row_major reads the rows (left), 16 x store_row_major writes them "
         "(right); the label says how many bytes", "arrow", C["rm"]),
        ("blue arrow and its blue label: the VNNI side of the copy, store_block writes "
         "the pair rows (left), 16 x load_row reads them (right); the label says how "
         "many bytes", "arrow", C["vnni"]),
        ("font_mono", "monospace = a name from the code: the function cells, "
                      "rows[BLOCK_TOKENS_16][Cols], the panel labels (s,2) #n"),
        ("font_sans", "sans-serif = the figure title and subtitle, the figure's own key, "
                      "the step titles, the arrow labels and the notes under the panels"),
        ("font_cite", "small grey monospace = the head lines (file:line) of k_vnni.hpp "
                      "that define the cell, the panel state or the arrow's count"),
        ("font_tag", "bold 'new' = block_to_vnni and block_to_rows are added by this PR"),
    ]
    return figure(fid, W, H, "The in-place conversion of one block: block_to_vnni and "
                  "block_to_rows through the 4 KiB stack copy",
                  "".join(o), cap, boxes=boxes, legend=legend)


def _fig_b():
    fid = "k_vnni-d9b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(LX, 16, "the callers of block_to_vnni and block_to_rows as a cut of B5: "
                  "one lane per thread, one column per phase", 10.5, weight=700))
    # the two phase columns of B5 that hold the callers
    cols = [(152, 412, "forward end", "model.hpp:1836-1847"),
            (420, 690, "between passes (tree lock)", "kv_cache.hpp:701-704")]
    for x0, x1, name, ref in cols:
        o.append(rect(x0, 26, x1 - x0, 26, C["soft"], C["line"], 1, 3))
        o.append(text((x0 + x1) / 2, 38, name, 9.5, "middle", weight=600))
        o.append(text((x0 + x1) / 2, 49, ref, 8.5, "middle", True, fill=C["cite"]))
    # (lines, fill, stroke, drawn cite, register entry); a lane_block needs
    # 10 n + 17 px for n lines at lh 10
    main = (["page::k_block_to_vnni_at(storage, c)",
             "when: after run() returned and wait_for_coop_gof",
             "drained; called by convert_pending_k_blocks",
             "guard: 16 row bits set, block bit clear (acquire",
             "loads); else CONVERTED_FALSE; no reader runs",
             "does: block_to_vnni x n_kv_heads planes (every",
             "KV head of the slot)",
             "publishes: k_vnni_blocks_ fetch_or block_bit(c)",
             "(release); returns CONVERTED_TRUE"],
            C["pend_fill"], C["pend"], "kv_cache.hpp:2214-2236; model.hpp:3173-3177",
            ("page::k_block_to_vnni_at [main thread]", "kv_cache.hpp:2214-2236; 2202-2211"))
    sched = [
        (["page::k_forget_row(offset)",
          "when: clear_kv_complete_at gives offset to a new",
          "token",
          "guard: block c = offset / 16 converted, keeps rows",
          "below offset (offset % 16 != 0), k_storage_readable",
          "does: block_to_rows x n_kv_heads planes (worked",
          "example: offset 37 -> block 2 keeps rows 32..36)",
          "publishes: fetch_and drops the block bits >= c and",
          "the row bits >= offset (release)"],
         C["rm_fill"], C["rm"], "kv_cache.hpp:2552-2586; 2472-2477",
         ("page::k_forget_row [scheduler thread, tree lock]", "kv_cache.hpp:2552-2586")),
        (["page::copy_storage_slot (not the whole page)",
          "when: copy_from of count tokens between pages",
          "does: 1. block_to_rows on each converted destination",
          "block the range touches (bit cleared in new_blocks)",
          "2. count tokens through row_major_row: load_row or",
          "store_row_major (2747-2756)",
          "3. block_to_vnni on each touched block whose 16 bits",
          "are set in new_saved (bit set in new_blocks)",
          "publishes: k_rows_saved_ = new_saved,",
          "k_vnni_blocks_ = new_blocks (release)"],
         "#fff", C["ink"], "kv_cache.hpp:2691, 2735-2763, 2780-2783",
         ("page::copy_storage_slot (not the whole page) [scheduler thread, tree lock]",
          "kv_cache.hpp:2691, 2735-2763")),
    ]
    # main thread lane: the conversion at the forward end, idle between passes
    ly = 60
    mh = 10 * len(main[0]) + 17
    svg, _ = lane(LX, ly, W - 2 * LX, mh + 12, "main thread", "worker_ix 0")
    o.append(svg)
    o.append(lane_block(420, ly + 6, 270, 47, [
        "no forward pass reads the book while the",
        "tree lock is held: the in-place transposes",
        "of the scheduler rely on it"], "#fff", C["ink"], "kv_cache.hpp:701-704",
        idle=True, size=9, lh=10))
    boxes.append(("clear_kv_complete_at and copy_from rely on the tree lock: no forward pass "
                  "reads the book (main thread lane, between passes)", "kv_cache.hpp:701-704"))
    o.append(lane_block(152, ly + 6, 260, mh, main[0], main[1], main[2], main[3], size=9,
                        lh=10))
    boxes.append(main[4])
    # scheduler thread lane: the way back and the page copy, between passes
    ly2 = ly + mh + 12 + 6
    hs = [10 * len(c[0]) + 17 for c in sched]
    sh_ = 6 + hs[0] + 8 + hs[1] + 6
    svg, _ = lane(LX, ly2, W - 2 * LX, sh_, "scheduler thread", "tree work")
    o.append(svg)
    o.append(lane_block(152, ly2 + 6, 260, 47, [
        "tree work (clear_kv_complete_at, copy_from)",
        "runs between forward passes only, with",
        "the tree lock held"], "#fff", C["ink"], "kv_cache.hpp:701-704, 2550-2551",
        idle=True, size=9, lh=10))
    boxes.append(("copy_from and clear_kv_complete_at run between forward passes (scheduler "
                  "thread lane, forward end)", "kv_cache.hpp:701-704, 2550-2551"))
    yy = ly2 + 6
    for (ls, fill, stroke, ref, reg), h in zip(sched, hs):
        o.append(lane_block(420, yy, 270, h, ls, fill, stroke, ref, size=9, lh=10))
        boxes.append(reg)
        yy += h + 8
    H = int(ly2 + sh_ + 8)
    cap = ("Updates B5: the three callers of the conversions as a cut of B5, one lane per "
           "thread and one column per phase. The boxes are in the colour the page uses "
           "for their action (vermillion: the conversion of a complete block, as in B4 "
           "step 2 and B5; orange: the way back to row-major, as in B4 step 5; white: "
           "the page copy, which does both). Each box says when the call happens, its "
           "guard, what it does and the bit it publishes.")
    legend = [
        ("ctx", "grey box, thin grey outline: a phase header of the top row, with the "
                "lines that bound the phase"),
        ("lane", "white frame, thin grey outline: one thread lane; its name at the left "
                 "in bold, its role under it in grey"),
        ("pend_solid", "orange box, orange-red outline: page::k_block_to_vnni_at, the "
                       "conversion of a complete block (block_to_vnni x n_kv_heads "
                       "planes); main thread, forward end"),
        ("rm", "orange: page::k_forget_row, the inverse conversion to row-major "
               "(block_to_rows x n_kv_heads planes); scheduler thread, between passes"),
        ("box", "white box, ink outline: page::copy_storage_slot, the page copy that "
                "does both (block_to_rows, then block_to_vnni); scheduler thread, "
                "between passes"),
        ("idle", "dashed outline: the thread does not touch the book in this phase: the "
                 "main thread between passes (no forward pass reads the book while the "
                 "tree lock is held), the scheduler thread at the forward end (tree "
                 "work runs between passes only)"),
        ("font_sans", "sans-serif = all text of the lane blocks, the thread labels and "
                      "the phase headers"),
        ("font_cite", "small grey monospace = the head lines (file:line) of kv_cache.hpp "
                      "and model.hpp that define the box or the phase column"),
    ]
    return figure(fid, W, H, "The callers of block_to_vnni and block_to_rows as B5 lanes: "
                  "when, guard, action, published bit", "".join(o), cap, boxes=boxes,
                  legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
