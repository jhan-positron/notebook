"""Change diagrams of unit k4 of the PR 4959 page for h/tron/tensor/k_vnni.hpp:
block_to_vnni and block_to_rows (head lines 461-491).

Two figures: k_vnni-d4a (the two conversions through the 4 KiB stack copy)
and k_vnni-d4b (the three callers: thread, when, guard, what it does, the bit
it publishes). Adapted from exec/pr4424-diagrams-20261009/figs/d_k_vnni_k9.py;
line numbers re-derived from the PR 4959 head (6b081187e1)."""
from svg_helpers import C, arrow, cite, figure, fn_cell, label_box, lines, marker_defs, rect, text, text_width
from base_k_vnni import BLOCK_2, KV_HEAD_0, PAGE_7, SLOT_5, _w, panel_lines, rm_forms

BASE = ("Updates B4: steps 4 and 5 (block_to_vnni, block_to_rows) are opened up to show "
        "the 4 KiB stack copy between the read of block 2 and its in-place rewrite. The "
        "second figure (d4b) updates B5: the three callers with the thread, the moment, "
        "the guard and the bit each one publishes.")

W = 700
LX, RX, CW = 12, 364, 324
PW, PH, PG = 70, 64, 10


def _panels4(x, y, forms4, hi_panel=None, **kw):
    """The 4 panels (s, 2) of block 2 side by side. hi_panel = s: a thick
    C['pend'] frame round panel (s, 2), the panel whose row-major rows (tokens
    4 s .. 4 s + 3) still live there when store_block writes it (461-463)."""
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
    if kind == "read":
        r = rect(x, y, 22, 12, "#fff", C["ink"], 1.2, 1, "4 3")
    elif kind == "overlap":
        r = rect(x, y, 22, 12, "#fff", C["pend"], 2, 1)
    else:
        r = rect(x, y, 22, 12, C[kind + "_fill"], C[kind], 1, 1)
    return r + text(x + 28, y + 10, label, 9.5), x + 28 + text_width(label, 9.5) + 16


def _varrow(o, fid, name, color, x, y0, y1, lines_, ref):
    o.append(arrow(fid, name, [(x, y0), (x, y1)], color, 1.6))
    o.append(lines(x + 10, y0 + 12, lines_, 9, 10.5, fill=color, weight=600))
    o.append(text(x + 10, y0 + 12 + len(lines_) * 10.5, f"[{ref}]", 8.5, mono=True,
                  fill=C["cite"]))


def _fig_a():
    fid = "k_vnni-d4a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "pend": C["pend"]})]
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
                      ("overlap", "thick outline: panel (0,2): tokens 32..35 still live there")]:
        svg, x = _chip(x, 57, kind, lab)
        o.append(svg)
    fy, fh = 80, 62
    o.append(fn_cell(LX, fy, CW, fh, "block_to_vnni(plane, c)",
                     ["Convert block c from row-major (Note [Row-major",
                      "tail block]) to the VNNI layout, in place"],
                     "k_vnni.hpp:461-476", "new"))
    boxes.append(("block_to_vnni(plane, c)", "k_vnni.hpp:461-476"))
    o.append(fn_cell(RX, fy, CW, fh, "block_to_rows(plane, c)",
                     ["The inverse: block c from the VNNI layout",
                      "back to row-major, in place"],
                     "k_vnni.hpp:478-491", "new"))
    boxes.append(("block_to_rows(plane, c)", "k_vnni.hpp:478-491"))
    py1, py2 = 178, 452
    sy, sh = 304, 64
    rm16 = rm_forms(range(32, 48))
    vnni16 = [["vnni"] * 16 for _ in range(4)]
    cols = [
        dict(x=LX, top=rm16, bot=vnni16, hi=0,
             top_lab="1. read: row-major, 16 row bits set, block bit clear",
             top_ref="k_vnni.hpp:405-411", read_name="rm",
             read=["16 x load_row_major -> rows[t]:",
                   "16 rows x 256 B = 4 KiB read through",
                   "source (the read-only view of plane)"],
             read_ref="k_vnni.hpp:469-474",
             stack_sub=["alignas(LINE_BYTES_64) bf16: 16 x 128 = 4 KiB on the stack",
                        "row_ptrs[t] = rows[t]: the 16 pointers store_block takes"],
             stack_ref="k_vnni.hpp:467-468", write_name="vnni",
             write=["store_block(plane, c, FULL_BLOCK_0XFFFF, row_ptrs):",
                    "4 steps x 16 pair rows = 64 whole-line stores",
                    "= 4 KiB, transposed in registers per step"],
             write_ref="k_vnni.hpp:475; 347-388",
             bot_lab="2. write: VNNI, in place; the caller then sets block bit 2",
             bot_ref="k_vnni.hpp:24-32, 416-418",
             note=["why the stack copy: panel (0,2) #2 holds the rows of tokens",
                   "32..35 in the row-major form and step 0 of tokens 32..47 in",
                   "the VNNI form. store_block writes panel (s,2) while the rows",
                   "of tokens 4 s .. 4 s + 3 still live there [k_vnni.hpp:461-463]"]),
        dict(x=RX, top=vnni16, bot=rm16, hi=None,
             top_lab="1. read: VNNI, block bit 2 set",
             top_ref="k_vnni.hpp:24-32, 416-418", read_name="vnni",
             read=["16 x load_row -> rows[t]:",
                   "16 x 4 gathers of 16 dwords = 4 KiB read",
                   "through source (the read-only view of plane)"],
             read_ref="k_vnni.hpp:483-486",
             stack_sub=["alignas(LINE_BYTES_64) bf16: 16 x 128 = 4 KiB on the stack",
                        "the same array, no row_ptrs"],
             stack_ref="k_vnni.hpp:482", write_name="rm",
             write=["16 x store_row_major(plane, 32 + t, rows[t]):",
                    "16 memcpy of 256 B = 64 whole lines = 4 KiB",
                    "into row_major_row(plane, 32 + t)"],
             write_ref="k_vnni.hpp:487-490; 441-449",
             bot_lab="2. write: row-major in place; caller clears block bit 2",
             bot_ref="k_vnni.hpp:405-411",
             note=["block_to_rows loads all 16 rows before its first",
                   "store_row_major: load_row gathers from the same 4 KiB",
                   "that store_row_major rewrites [k_vnni.hpp:484-490, 410-411].",
                   "a converted block that will receive or lose rows goes back",
                   "to row-major so set_k_row and its readers find the rows",
                   "[kv_cache.hpp:744-751, 866-873]"]),
    ]
    for cdef in cols:
        x = cdef["x"]
        px = x + 7
        o.append(text(x, py1 - 22, cdef["top_lab"], 9.5, weight=600))
        o.append(_panels4(px, py1, cdef["top"], cdef["hi"], read_all=True))
        o.append(cite(px + 4 * PW + 3 * PG, py1 + PH + 12, cdef["top_ref"]))
        boxes.append((f"block 2 panels (s,2), read ({cdef['top_lab'][9:]})", cdef["top_ref"]))
        _varrow(o, fid, cdef["read_name"], C[cdef["read_name"]], x + 18, py1 + PH + 8,
                sy - 4, cdef["read"], cdef["read_ref"])
        o.append(label_box(x, sy, CW, sh, "rows[BLOCK_TOKENS_16][Cols]", cdef["stack_sub"],
                           C["rm_fill"], C["rm"], 10.5, ref=cdef["stack_ref"]))
        boxes.append((f"rows[BLOCK_TOKENS_16][Cols] (stack, {cdef['stack_ref']})",
                      cdef["stack_ref"]))
        _varrow(o, fid, cdef["write_name"], C[cdef["write_name"]], x + 18, sy + sh + 4,
                py2 - 36, cdef["write"], cdef["write_ref"])
        o.append(text(x, py2 - 22, cdef["bot_lab"], 9.5, weight=600))
        o.append(_panels4(px, py2, cdef["bot"], cdef["hi"]))
        o.append(cite(px + 4 * PW + 3 * PG, py2 + PH + 12, cdef["bot_ref"]))
        boxes.append((f"block 2 panels (s,2), written ({cdef['bot_lab'][10:]})", cdef["bot_ref"]))
        for s in cdef["note"]:
            _w(s, 9, CW, where="k4 note")
        o.append(lines(x, py2 + PH + 28, cdef["note"], 9, 11, fill=C["ink"]))
    H = py2 + PH + 28 + 6 * 11 + 6
    cap = ("Updates B4: steps 4 and 5 of the worked example are opened up: each column "
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
    fid = "k_vnni-d4b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(LX, 16, "the three callers of block_to_vnni and block_to_rows (a cut of B5): "
                  "thread, moment, guard, action, published bit", 10.5, weight=700))
    callers = [
        ("page::k_block_to_vnni_at(storage, c)",
         ["[main thread, forward end]",
          "when: after run() returned and",
          "wait_for_coop_gof drained; called by",
          "convert_pending_k_blocks per entry",
          "guard: the 16 row bits set and the",
          "block bit clear (acquire loads), else",
          "returns false; no reader runs",
          "does: block_to_vnni x n_kv_heads",
          "(every KV head of the slot)",
          "publishes: k_vnni_blocks_ fetch_or",
          "block_bit(c) (release); returns true"],
         C["pend_fill"], C["pend"], "kv_cache.hpp:2261-2283",
         ("page::k_block_to_vnni_at [main thread, forward end]",
          "kv_cache.hpp:2261-2283; model.hpp:3170-3177, 1838-1842")),
        ("page::k_forget_row(offset)",
         ["[scheduler thread, tree lock]",
          "when: clear_kv_complete_at gives the",
          "offset to a new token, between passes",
          "guard: block c = offset / 16 converted,",
          "keeps rows below offset (offset % 16",
          "!= 0), k_storage_readable",
          "does: block_to_rows x n_kv_heads",
          "(worked example: offset 37 -> block 2",
          "keeps rows 32..36)",
          "publishes: fetch_and drops the block",
          "bits >= c and the row bits >= offset"],
         C["rm_fill"], C["rm"], "kv_cache.hpp:2583-2617",
         ("page::k_forget_row [scheduler thread, tree lock]", "kv_cache.hpp:2583-2617; 2509-2514")),
        ("page::copy_storage_slot (partial)",
         ["[scheduler thread, tree lock]",
          "when: copy_from of count tokens",
          "between pages, not a whole page",
          "does: 1. block_to_rows on each conver-",
          "ted destination block the range touches",
          "2. count rows through row_major_row:",
          "load_row or store_row_major",
          "3. block_to_vnni on each touched block",
          "whose 16 bits are set in new_saved",
          "publishes: k_rows_saved_ = new_saved,",
          "k_vnni_blocks_ = new_blocks (release)"],
         "#fff", C["ink"], "kv_cache.hpp:2722-2811",
         ("page::copy_storage_slot (partial range) [scheduler thread, tree lock]",
          "kv_cache.hpp:2722-2811; 2815")),
    ]
    cw, gap = 220, 9
    y0 = 30
    for i, (name, ls, fill, stroke, ref, reg) in enumerate(callers):
        x = LX + i * (cw + gap)
        h = 22 + 10.5 * len(ls) + 16
        _w(name, 9.5, cw - 8, True, f"k4b name {name}")
        for s in ls:
            _w(s, 8.5, cw - 8, where=f"k4b {name}")
        o.append(rect(x, y0, cw, h, fill, stroke, 1.2, 4))
        o.append(text(x + 5, y0 + 14, name, 9.5, mono=True, weight=700))
        o.append(lines(x + 5, y0 + 28, ls, 8.5, 10.5))
        o.append(cite(x + cw - 4, y0 + h - 4, ref))
        boxes.append(reg)
    H = int(y0 + 22 + 10.5 * 11 + 16 + 30)
    o.append(text(LX, H - 12, "no forward pass reads the book while the tree lock is held: "
                  "the in-place transposes of the scheduler rely on it [kv_cache.hpp:733-736]",
                  9, fill=C["muted"]))
    boxes.append(("the tree-lock rule of the scheduler's transposes", "kv_cache.hpp:733-736"))
    cap = ("Updates B5: the three callers of the conversions. The boxes are in the colour "
           "the page uses for their action (orange-red outline: the conversion of a "
           "complete block, as in B4 step 4; orange: the way back to row-major, as in B4 "
           "step 5; white: the page copy, which does both). Each box says the thread, "
           "when the call happens, its guard, what it does and the bit it publishes.")
    legend = [
        ("pend_solid", "orange box, orange-red outline: page::k_block_to_vnni_at, the "
                       "conversion of a complete block (block_to_vnni x n_kv_heads); main "
                       "thread, forward end"),
        ("rm", "orange: page::k_forget_row, the inverse conversion to row-major "
               "(block_to_rows x n_kv_heads); scheduler thread, between passes"),
        ("box", "white box, ink outline: page::copy_storage_slot, the page copy that "
                "does both (block_to_rows, then block_to_vnni); scheduler thread, "
                "between passes"),
        ("font_mono", "monospace = the caller names"),
        ("font_sans", "sans-serif = the title, the thread in brackets, and the when / guard "
                      "/ does / publishes lines"),
        ("font_cite", "small grey monospace = the head lines (file:line) of kv_cache.hpp "
                      "that define each caller"),
    ]
    return figure(fid, W, H, "The callers of block_to_vnni and block_to_rows: thread, "
                  "moment, guard, action, published bit", "".join(o), cap, boxes=boxes,
                  legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
