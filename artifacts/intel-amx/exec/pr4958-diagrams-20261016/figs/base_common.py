"""Base diagrams B1-B5 of the PR 4958 page for h/tron/models/common.hpp
(key "common"): the data model of batch::k_store_window_t, who reads and
writes each field, the field values through one window of the worked example,
the three threads over wall-clock time, and the work-unit invariants.

Worked example (STYLE.md, the same on all three pages): one prefill pass,
layer 5, n_workers = 3 (main = worker_ix 0, helpers 1 and 2), 41 items at
page 7 offsets 0..40. unit_start = [0, 16, 32, 41], n_units = 3. Claims drawn:
main unit 0, helper 1 unit 1, helper 2 unit 2.

Every box cites the HEAD line (b39765ec29) that defines it: common.hpp = the
batch, model.hpp = save_k, TronCpp.hs = the code generator, t_llama_unit.cpp
= the three-thread test.

Exports for the change diagrams (from base_common import ...):
  constants: N_WORKERS, N_HELPERS, N_ITEMS, UNIT_START, N_UNITS, UNITS,
             THREADS, WINDOW_FIELDS
  building blocks: fit, tag, field_row, step_box, item_strip, unit_table,
             counters, lanes_grid, cache_lines
"""
import sys

from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, lane, line,
                         lines, marker_defs, rect, text, text_width, work_block)

# ---- the worked example ----------------------------------------------------
N_WORKERS = 3                         # main + 2 helpers (t_llama_unit.cpp:4042)
N_HELPERS = N_WORKERS - 1             # n_helpers = n_workers - 1 (model.hpp:3328)
N_ITEMS = 41                          # items at page 7 offsets 0..40
UNIT_START = [0, 16, 32, 41]          # unit_start[0 .. n_units] (model.hpp:3187-3189)
N_UNITS = 3
UNITS = [
    # u, items [begin, end), page, block c, offsets, n, present mask, the store
    dict(u=0, begin=0, end=16, page=7, block=0, offsets="0..15", n=16,
         present="0xffff", store="set_k_block (16 lines per pair row)"),
    dict(u=1, begin=16, end=32, page=7, block=1, offsets="16..31", n=16,
         present="0xffff", store="set_k_block (16 lines per pair row)"),
    dict(u=2, begin=32, end=41, page=7, block=2, offsets="32..40", n=9,
         present="0x01ff", store="set_k_block (masked lines)"),
]
THREADS = ["[main, worker_ix 0]", "[helper 1, worker_ix 1]", "[helper 2, worker_ix 2]"]
CLAIMS = [(0, 0), (1, 1), (2, 2)]     # (thread, unit): one order; fetch_add fixes none

# The fields of batch::k_store_window_t (common.hpp:1196-1219), in order:
# (name, description lines, citation, colour key).
WINDOW_FIELDS = [
    ("max_shared_workers", ["static constexpr 128: worker counts above it take",
                            "the unshared store; the size of helper_windows"],
     "common.hpp:1197-1199"),
    ("next_unit", ["std::atomic<uint32_t>, alignas(cache_line_size):",
                   "the claim counter, on its own cache line"],
     "common.hpp:1200-1202"),
    ("opened", ["std::atomic<uint32_t>, alignas(cache_line_size):",
                "windows opened so far in this pass"], "common.hpp:1203-1204"),
    ("finished", ["std::atomic<uint32_t>: helpers done with the",
                  "open window"], "common.hpp:1205"),
    ("n_units", ["uint32_t: work units of the open window"], "common.hpp:1206"),
    ("unit_start", ["std::array<uint32_t, max_minibatch_size + 1>:",
                    "unit u = items[unit_start[u], unit_start[u + 1])"],
     "common.hpp:1207-1215"),
    ("helper_windows", ["std::array<uint32_t, max_shared_workers>:",
                        "windows a helper has entered, by worker_ix"],
     "common.hpp:1216-1218"),
]


def fit(s, size, w, mono=False, where=""):
    """Warn on stderr when a string is wider than w px (see the PNG too)."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w}", file=sys.stderr)
    return s


def _w(s, size, mono=False):
    return text_width(s, size, mono)


def tag(x, y, s, col=None, anchor="start", size=9):
    return text(x, y, s, size, anchor, fill=col or C["new"], weight=700)


# ---- building blocks -------------------------------------------------------
def field_row(x, y, w, h, name, desc, ref, tag_=None, fill="#fff", stroke=C["ink"],
              dash=None, name_size=10, desc_size=9):
    """One field of a data box: name (mono, bold) with the citation at the
    right of the same line, then up to two description lines, and an optional
    tag ('new') after the name."""
    o = [rect(x, y, w, h, fill, stroke, 1.1, 3, dash)]
    o.append(text(x + 6, y + 13, name, name_size, mono=True, weight=600))
    o.append(cite(x + w - 4, y + 12, ref))
    ds = desc if isinstance(desc, (list, tuple)) else [desc]
    for s in ds:
        fit(s, desc_size, w - 12, False, f"field_row {name}")
    o.append(lines(x + 6, y + 25, ds, desc_size, 11))
    if tag_:
        o.append(tag(x + 6 + _w(name, name_size, True) * 1.08 + 8, y + 13, tag_))
    return "".join(o)


def step_box(x, y, w, h, title, sub, ref, fill="#fff", stroke=C["ink"], dash=None,
             num=None, title_size=10.5, sub_size=9):
    """A protocol step: an optional step badge, a title (mono, bold), sub
    lines and the citation in the lower-right corner. dash = a waiting step."""
    o = [rect(x, y, w, h, fill, stroke, 1.3 if dash else 1.2, 4, dash)]
    tx = x + 8
    if num is not None:
        o.append(rect(x + 8, y + 5, 36, 14, C["ink"], C["ink"], 1, 3))
        o.append(text(x + 26, y + 15.5, f"step {num}", 8.5, "middle", fill="#fff",
                      weight=700))
        tx = x + 50
    fit(title, title_size, w - (tx - x) - 6, True, f"step_box {title}")
    o.append(text(tx, y + 15, title, title_size, mono=True, weight=600))
    for s in sub:
        fit(s, sub_size, w - 14, False, f"step_box {title}")
    o.append(lines(x + 8, y + 29, sub, sub_size, 11.5))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def item_strip(x, y, cell=15, gap=1, unit_gap=10, h=16, present=True):
    """The 41 items of the worked example as one strip grouped by unit
    (grey-blue = a work unit). Returns (svg, x_end, spans)."""
    o = []
    spans = []
    cx = x
    for u in UNITS:
        x0 = cx
        for i in range(u["begin"], u["end"]):
            o.append(rect(cx, y, cell, h, C["unit_fill"], C["unit"], 0.8, 1))
            cx += cell + gap
        spans.append((x0, cx - gap))
        cx += unit_gap
    return "".join(o), cx - unit_gap, spans


def unit_table(x, y, cell_w=44, h=22, values=UNIT_START):
    """unit_start[0 .. n_units] of the worked example plus an unused tail."""
    o = []
    cx = x
    for i, v in enumerate(values):
        o.append(rect(cx, y, cell_w, h, C["unit_fill"], C["unit"], 1, 2))
        o.append(text(cx + cell_w / 2, y + 15, str(v), 10.5, "middle", True, weight=600))
        o.append(text(cx + cell_w / 2, y - 4, f"[{i}]", 8.5, "middle", True, fill=C["muted"]))
        cx += cell_w + 4
    o.append(rect(cx, y, cell_w, h, C["empty_fill"], C["empty"], 1, 2, "3 2"))
    o.append(text(cx + cell_w / 2, y + 15, "...", 10.5, "middle", True, fill=C["muted"]))
    return "".join(o), cx + cell_w


def counters(x, y, values, w=92, h=32, gap=6):
    """A row of counter boxes: values = [(name, value_text), ...], grey-blue."""
    o = []
    cx = x
    for name, val in values:
        o.append(rect(cx, y, w, h, C["unit_fill"], C["unit"], 1.2, 3))
        o.append(text(cx + w / 2, y + 12, name, 8.5, "middle", True, fill=C["unit"],
                      weight=600))
        o.append(text(cx + w / 2, y + 26, val, 10, "middle", True, weight=600))
        cx += w + gap
    return "".join(o), cx - gap


def lanes_grid(x, y, w, labels, lane_h=58, gap=6):
    """Wall-clock lanes: labels = [(label, sub), ...]. Returns (svg, lane_ys,
    time_x0) where time_x0 is where the time axis starts (140 px gutter)."""
    o = []
    ys = []
    x0 = x + 140
    for i, (lab, sub) in enumerate(labels):
        ly = y + i * (lane_h + gap)
        svg, x0 = lane(x, ly, w, lane_h, lab, sub)
        o.append(svg)
        ys.append(ly)
    return "".join(o), ys, x0


def cache_lines(x, y, w, line_h=26):
    """The memory placement of the window: cache line 0 holds next_unit alone
    (alignas), line 1 starts with opened and carries finished, n_units and the
    start of unit_start; the two arrays follow. Returns (svg, y_end)."""
    o = []
    # line 0: next_unit (4 bytes) then padding to 64 bytes
    o.append(rect(x, y, w, line_h, "#fff", C["line"], 1, 3))
    o.append(text(x - 6, y + line_h / 2 + 4, "cache line 0", 9, "end", fill=C["muted"]))
    o.append(rect(x + 2, y + 3, 92, line_h - 6, C["unit_fill"], C["unit"], 1.1, 2))
    o.append(text(x + 48, y + line_h / 2 + 4, "next_unit", 9.5, "middle", True, weight=600))
    o.append(rect(x + 98, y + 3, w - 102, line_h - 6, C["empty_fill"], C["empty"], 0.9, 2, "3 2"))
    o.append(text(x + 98 + (w - 102) / 2, y + line_h / 2 + 4,
                  "padding to cache_line_size (64 bytes)", 9, "middle", fill=C["muted"]))
    # line 1: opened, finished, n_units, unit_start[0..]
    y1 = y + line_h + 6
    o.append(rect(x, y1, w, line_h, "#fff", C["line"], 1, 3))
    o.append(text(x - 6, y1 + line_h / 2 + 4, "cache line 1", 9, "end", fill=C["muted"]))
    cx = x + 2
    for name, bw in (("opened", 74), ("finished", 78), ("n_units", 74)):
        o.append(rect(cx, y1 + 3, bw, line_h - 6, C["unit_fill"], C["unit"], 1.1, 2))
        o.append(text(cx + bw / 2, y1 + line_h / 2 + 4, name, 9.5, "middle", True, weight=600))
        cx += bw + 4
    o.append(rect(cx, y1 + 3, w - (cx - x) - 4, line_h - 6, C["unit_fill"], C["unit"], 1.1, 2))
    o.append(text(cx + (w - (cx - x) - 4) / 2, y1 + line_h / 2 + 4,
                  "unit_start[0], [1], ... (4 bytes each)", 9.5, "middle", True, weight=600))
    # the arrays continue
    y2 = y1 + line_h + 6
    o.append(rect(x, y2, w, line_h, "#fff", C["line"], 1, 3))
    o.append(text(x - 6, y2 + line_h / 2 + 4, "lines 2 ...", 9, "end", fill=C["muted"]))
    half = (w - 8) / 2
    o.append(rect(x + 2, y2 + 3, half, line_h - 6, C["unit_fill"], C["unit"], 1.1, 2))
    o.append(text(x + 2 + half / 2, y2 + line_h / 2 + 4,
                  "unit_start: max_minibatch_size + 1 entries", 9.5, "middle", True, weight=600))
    o.append(rect(x + 6 + half, y2 + 3, half, line_h - 6, C["unit_fill"], C["unit"], 1.1, 2))
    o.append(text(x + 6 + half + half / 2, y2 + line_h / 2 + 4,
                  "helper_windows: 128 entries = 512 bytes", 9.5, "middle", True, weight=600))
    return "".join(o), y2 + line_h


# ---- B1: data model --------------------------------------------------------
def b1():
    fid = "common-b1"
    W, H = 1000, 744
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"]})]
    boxes = []
    AX, AW = 20, 260      # column A: the batch, the worked example's tables
    BX, BW = 340, 290     # column B: the window type
    CX, CW = 700, 280     # column C: the work unit, the page, the store

    # ---- column A: batch -------------------------------------------------
    o.append(rect(AX, 40, AW, 232, C["soft"], C["ink"], 1.2, 6))
    o.append(text(AX + 8, 56, "batch (one minibatch)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, 56, "common.hpp:1019"))
    boxes.append(("batch", "common.hpp:1019 (struct batch)"))
    rx, rw = AX + 12, AW - 24
    o.append(field_row(rx, 66, rw, 44, "items",
                       ["std::vector<token_job_id>: the token jobs of",
                        "this minibatch, n_items of them, in order"],
                       "common.hpp:1110-1111"))
    boxes.append(("items", "common.hpp:1110-1111"))
    o.append(field_row(rx, 114, rw, 44, "k_store_window",
                       ["k_store_window_t: the K store window of this",
                        "minibatch, one per (layer, pass) (column B)"],
                       "common.hpp:1219", tag_="new"))
    boxes.append(("k_store_window", "common.hpp:1193-1195 (comment), 1219 (member)"))
    o.append(field_row(rx, 162, rw, 44, "layer_done",
                       ["latch_ref: are main and the helper threads",
                        "done with this layer (context)"],
                       "common.hpp:1190-1191"))
    boxes.append(("layer_done", "common.hpp:1190-1191"))
    o.append(field_row(rx, 210, rw, 44, "upstream_kvs_ready",
                       ["latches per slot: counted down by save_k",
                        "after the marks (context)"],
                       "common.hpp:1185-1188"))
    boxes.append(("upstream_kvs_ready", "common.hpp:1185-1188; counted down at model.hpp:3385"))
    o.append(arrow(fid, "unit", [(AX + AW, 136), (BX - 2, 136)], C["unit"]))
    o.append(text((AX + AW + BX) / 2, 130, "1 batch ->", 8.5, "middle", fill=C["unit"], weight=600))
    o.append(text((AX + AW + BX) / 2, 148, "1 window", 8.5, "middle", fill=C["unit"], weight=600))

    # ---- column A: the worked example's tables -----------------------------
    ey = 300
    o.append(text(AX, ey, "worked example: 41 items, 3 units", 10.5, weight=700))
    strip, x_end, spans = item_strip(AX, ey + 8, cell=5.4, gap=0.6, unit_gap=6, h=14)
    o.append(strip)
    for (x0, x1), u in zip(spans, UNITS):
        o.append(text((x0 + x1) / 2, ey + 34, f"unit {u['u']}: {u['begin']}..{u['end'] - 1}",
                      8.5, "middle", True, fill=C["unit"]))
    boxes.append(("unit 0 .. unit 2 (items of the worked example)",
                  "common.hpp:1207-1215; model.hpp:3165-3191 (k_store_cut_units)"))
    o.append(text(AX, ey + 54, "unit_start of the example", 9.5, weight=600))
    tbl, _ = unit_table(AX, ey + 68, cell_w=40, h=20)
    o.append(tbl)
    o.append(cite(AX + AW - 4, ey + 100, "model.hpp:3187-3189"))
    o.append(arrow(fid, "unit", [(BX, 526), (304, 526), (304, ey + 78), (AX + AW + 2, ey + 78)],
                   C["unit"]))
    o.append(text(AX, ey + 118, "1 window -> max_minibatch_size + 1 unit_start", 8.5,
                  fill=C["unit"], weight=600))
    o.append(text(AX, ey + 129, "entries; n_units + 1 = 4 of them used here", 8.5,
                  fill=C["unit"], weight=600))
    # helper_windows of the example
    hy = ey + 150
    o.append(text(AX, hy, "helper_windows of the example (window 1)", 9.5, weight=600))
    cx = AX
    for i, v in enumerate(["0", "1", "1"]):
        fill = C["unit_fill"] if i > 0 else C["empty_fill"]
        stroke = C["unit"] if i > 0 else C["empty"]
        o.append(rect(cx, hy + 14, 40, 20, fill, stroke, 1, 2, None if i > 0 else "3 2"))
        o.append(text(cx + 20, hy + 29, v, 10.5, "middle", True, weight=600))
        o.append(text(cx + 20, hy + 10, f"[{i}]", 8.5, "middle", True, fill=C["muted"]))
        cx += 44
    o.append(rect(cx, hy + 14, 40, 20, C["empty_fill"], C["empty"], 1, 2, "3 2"))
    o.append(text(cx + 20, hy + 29, "...", 10.5, "middle", True, fill=C["muted"]))
    o.append(text(cx + 48, hy + 29, "[127]", 8.5, "start", True, fill=C["muted"]))
    o.append(cite(AX + AW - 4, hy + 46, "model.hpp:3335"))
    o.append(arrow(fid, "unit", [(BX, 604), (312, 604), (312, hy + 24), (AX + AW + 2, hy + 24)],
                   C["unit"]))
    o.append(text(AX, hy + 64, "1 window -> max_shared_workers = 128 entries;", 8.5,
                  fill=C["unit"], weight=600))
    o.append(text(AX, hy + 75, "[1 .. n_workers - 1] used; [0] is main's, unused", 8.5,
                  fill=C["unit"], weight=600))
    boxes.append(("helper_windows of the example", "common.hpp:1216-1218; model.hpp:3335 "
                  "(++w.helper_windows[worker_ix])"))

    # ---- column B: k_store_window_t -------------------------------------
    o.append(rect(BX, 40, BW, 392, "#fff", C["ink"], 1.4, 6))
    o.append(text(BX + 8, 56, "k_store_window_t", 11.5, mono=True, weight=700))
    o.append(tag(BX + 8 + _w("k_store_window_t", 11.5, True) * 1.08 + 8, 56, "new"))
    o.append(cite(BX + BW - 4, 56, "common.hpp:1196-1219"))
    boxes.append(("k_store_window_t", "common.hpp:1196-1219"))
    fy = 66
    for name, desc, ref in WINDOW_FIELDS:
        o.append(field_row(BX + 12, fy, BW - 24, 44, name, desc, ref, fill=C["unit_fill"],
                           stroke=C["unit"]))
        boxes.append((name, ref))
        fy += 48
    # n_units -> the work units of column C
    o.append(arrow(fid, "unit", [(BX + BW, 280), (CX - 2, 280)], C["unit"]))
    o.append(text((BX + BW + CX) / 2, 274, "1 window ->", 8.5, "middle", fill=C["unit"], weight=600))
    o.append(text((BX + BW + CX) / 2, 292, "n_units units", 8.5, "middle", fill=C["unit"], weight=600))

    # threads note under the window
    ty = 444
    o.append(rect(BX, ty, BW, 70, C["soft"], C["line"], 1, 4))
    tl = ["threads of one shared window: [main, worker_ix 0] and",
          "[helpers, worker_ix 1 .. n_workers - 1]; n_workers =",
          "main + the main helpers of the generated plugin;",
          "shared only if 1 < n_workers <= 128 (k_store_shared)"]
    for s in tl:
        fit(s, 9, BW - 16, False, "b1 threads")
    o.append(lines(BX + 8, ty + 13, tl, 9, 11))
    o.append(cite(BX + BW - 4, ty + 66, "model.hpp:3094-3099, 3151-3161"))
    boxes.append(("n_workers, worker_ix (threads of a shared window)",
                  "model.hpp:3094-3099 (Note), 3151-3161 (k_store_shared); TronCpp.hs:1364"))

    # ---- column C: the work unit, the page, the store ----------------------
    uy = 232
    o.append(rect(CX, uy, CW, 96, C["unit_fill"], C["unit"], 1.4, 6))
    o.append(text(CX + 8, uy + 16, "work unit u", 11, mono=True, weight=700))
    o.append(cite(CX + CW - 4, uy + 16, "common.hpp:1207-1214"))
    boxes.append(("work unit u", "common.hpp:1207-1214 (comment of unit_start)"))
    ul = ["= items[unit_start[u], unit_start[u + 1]):",
          "consecutive items in ONE page, ONE 16-token block,",
          "ONE token_jobs_do_kv value (never crosses any of",
          "the three); at most 16 items with KV work"]
    for s in ul:
        fit(s, 9, CW - 16, False, "b1 unit")
    o.append(lines(CX + 8, uy + 31, ul, 9, 11))
    o.append(cite(CX + CW - 4, uy + 92, "model.hpp:3139, 3179-3184"))
    # the page and its blocks
    py = 352
    o.append(rect(CX, py, CW, 120, "#fff", C["ink"], 1.2, 6))
    o.append(text(CX + 8, py + 16, "page, block c", 11, mono=True, weight=700))
    o.append(cite(CX + CW - 4, py + 16, "kv_cache.hpp:2078-2081"))
    boxes.append(("page: 4 blocks of 16 offsets (block c)", "kv_cache.hpp:2078-2081 (set_k_block "
                  "comment: block c holds the page offsets c * 16 .. c * 16 + 15)"))
    bx = CX + 10
    for c in range(4):
        fill = C["vnni_fill"] if c < 3 else C["empty_fill"]
        stroke = C["vnni"] if c < 3 else C["empty"]
        o.append(rect(bx, py + 26, 60, 24, fill, stroke, 1.1, 3, None if c < 3 else "3 2"))
        o.append(text(bx + 30, py + 42, f"block {c}", 9.5, "middle", mono=True))
        bx += 66
    pl = ["1 page -> page_size / BLOCK_TOKENS_16 = 4 blocks;",
          "the example writes blocks 0 and 1 whole, block 2 at",
          "offsets 32..40; block 3 has no row saved"]
    for s in pl:
        fit(s, 8.5, CW - 16, False, "b1 page")
    o.append(lines(CX + 8, py + 66, pl, 8.5, 11, fill=C["muted"]))
    o.append(cite(CX + CW - 4, py + 116, "kv_cache.hpp:2094; k_vnni.hpp:65"))
    o.append(card_arrow(fid, "ink", [(CX + 50, uy + 96), (CX + 50, py - 2)], C["ink"],
                        "1 unit -> rows in 1 block of 1 page", label_dx=8, label_dy=4,
                        anchor="start", size=8.5))
    # the store of a unit
    sy = 486
    o.append(rect(CX, sy, CW, 104, C["soft"], C["line"], 1, 4))
    o.append(text(CX + 8, sy + 15, "what a unit becomes (store_k_block)", 10, weight=700))
    sl = ["n = 1 item with KV work: set_k_row (a scatter),",
          "n = 2 .. 16: set_k_block with the present mask",
          "(bit t = the row of offset c * 16 + t is in the run);",
          "the example: 0xffff, 0xffff, 0x01ff (9 of 16 lanes)"]
    for s in sl:
        fit(s, 9, CW - 16, False, "b1 store")
    o.append(lines(CX + 8, sy + 30, sl, 9, 11))
    o.append(cite(CX + CW - 4, sy + 100, "model.hpp:3193-3199, 3260-3291"))
    boxes.append(("store_k_block (what a unit becomes)",
                  "model.hpp:3193-3201; kv_cache.hpp:2078-2097 (set_k_block)"))
    o.append(arrow(fid, "ink", [(CX + 50, py + 120), (CX + 50, sy - 2)], C["ink"]))

    # ---- the memory placement, bottom ------------------------------------
    my = 622
    o.append(text(20, my - 6, "memory placement of the window (alignas on next_unit and opened)",
                  10.5, weight=700))
    cl, y_end = cache_lines(120, my, 560)
    o.append(cl)
    o.append(cite(680, y_end + 12, "common.hpp:1200-1204; util.hpp:37-39"))
    boxes.append(("cache line 0 / cache line 1 (cache_line_size)",
                  "common.hpp:1200-1204 (alignas(cache_line_size)); util.hpp:37-39 "
                  "(cache_line_size = 64 bytes)"))
    wl = ["why: a claim (next_unit.fetch_add) must not",
          "invalidate the line the waiting threads poll",
          "(the helpers poll opened, main polls finished)"]
    for s in wl:
        fit(s, 9, 300, False, "b1 why")
    o.append(lines(700, my + 10, wl, 9, 11))
    o.append(cite(990, my + 48, "common.hpp:1200-1201"))

    cap = ("The data model. One batch (a minibatch) owns one K store window. The window "
           "holds three counters, a unit count and two tables: unit_start cuts the items "
           "into work units, helper_windows counts the windows each helper entered. A work "
           "unit is a run of consecutive items in one block of one page. The bottom row "
           "shows why next_unit and opened each start a cache line: a claim must not "
           "invalidate the line the waiting threads poll. Worked example: 41 items, 3 units, "
           "the tables at the lower left.")
    legend = [
        ("ctx_ink", "grey fill, ink outline: the batch (context)"),
        ("ctx", "grey box, thin grey outline: the threads note and the store note"),
        ("box", "white box, ink outline: a field of the batch, the window type, the page"),
        ("unit", "grey-blue: the window's fields, the items of a work unit, unit_start, helper_windows, the work unit"),
        ("vnni", "blue: a block of the page that the example writes in the VNNI layout"),
        ("empty", "grey dashed: a block with no row saved, an unused table entry, the padding of a cache line"),
        ("lane", "white box, thin grey outline: one cache line of 64 bytes"),
        ("grey-blue arrow: how many of the next thing one of this thing has", "arrow", C["unit"]),
        ("arrow", "ink arrow: a unit's rows go into one block of one page, through store_k_block"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR"),
    ]
    return figure(fid, W, H, "Data model: batch, k_store_window_t, work units, cache lines",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B2: function model ----------------------------------------------------
def b2():
    fid = "common-b2"
    W, H = 1000, 560
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"], "muted": C["muted"]})]
    boxes = []
    o.append(text(20, 24, "callers (generated plugin, the test)", 10.5, weight=700))
    o.append(text(300, 24, "functions of model.hpp", 10.5, weight=700))
    o.append(text(770, 24, "fields of k_store_window", 10.5, weight=700))
    # callers
    o.append(rect(20, 34, 236, 86, C["soft"], C["line"], 1, 4))
    o.append(text(28, 50, "run() [main]", 10.5, mono=True, weight=700))
    cl = ["save_k(ks, 0, n_workers) at the",
          "statement of the KV write; worker 0",
          "is main; n_workers is in scope in run()"]
    for s in cl:
        fit(s, 9, 220, False, "b2 run")
    o.append(lines(28, 64, cl, 9, 11))
    o.append(cite(252, 116, "TronCpp.hs:2996-3004"))
    boxes.append(("run() [main] -> save_k(..., 0, n_workers)", "TronCpp.hs:2996-3004 (saveKv)"))
    o.append(rect(20, 130, 236, 98, C["soft"], C["line"], 1, 4))
    o.append(text(28, 146, "run_main_help(worker_ix)", 10.5, mono=True, weight=700))
    hl = ["[helper worker_ix]: save_k(ks, worker_ix,",
          "n_workers) at the SAME statement position",
          "(AttentionStmt of runHelperStatement); the",
          "helpers are idle there: their next kernel",
          "waits for the attention output"]
    for s in hl:
        fit(s, 9, 220, False, "b2 help")
    o.append(lines(28, 160, hl, 9, 11))
    o.append(cite(252, 224, "TronCpp.hs:1364, 1420, 2935-2942"))
    boxes.append(("run_main_help(worker_ix) -> save_k(..., worker_ix, n_workers)",
                  "TronCpp.hs:1364 (the call), 1420 (the method), 2935-2942 (the save_k call)"))
    o.append(rect(20, 238, 236, 70, C["soft"], C["line"], 1, 4))
    o.append(text(28, 254, "t_llama_unit.cpp", 10.5, mono=True, weight=700))
    tl = ["the three-thread section: 2 std::thread",
          "helpers, the last one 20 ms late; reads",
          "finished as the main call returns"]
    for s in tl:
        fit(s, 9, 220, False, "b2 test")
    o.append(lines(28, 268, tl, 9, 11))
    o.append(cite(252, 304, "t_llama_unit.cpp:4040-4066"))
    boxes.append(("t_llama_unit.cpp three-thread section", "t_llama_unit.cpp:4040-4066"))

    # functions, one column
    FX, FW = 300, 400
    o.append(fn_cell(FX, 34, FW, 58, "save_k (two entry points)",
                     ["main and the helpers call it with the same operation at the",
                      "same point of the schedule; worker_ix = 0, n_workers = 1 by default"],
                     "model.hpp:3388-3412", "changed"))
    boxes.append(("save_k (two entry points)", "model.hpp:3388-3412"))
    o.append(fn_cell(FX, 104, FW, 110, "save_k_impl(q_batch, operation, ks, worker_ix, n_workers)",
                     ["every worker of the store calls this; main opens the window (resets",
                      "next_unit and finished, bumps opened), stores its share, joins the",
                      "helpers, then marks the tokens; a helper bumps its helper_windows",
                      "slot, waits for opened, stores its share, bumps finished, returns;",
                      "all claim units with next_unit.fetch_add until u >= n_units"],
                     "model.hpp:3295-3368", "changed"))
    boxes.append(("save_k_impl", "model.hpp:3295-3368"))
    o.append(text(FX + 8, 236, "called once by every thread, before the window", 8.5, fill=C["muted"]))
    o.append(fn_cell(FX, 240, FW, 58, "k_store_shared<geometry>(q_batch, n_workers)",
                     ["whether the store is shared: layout on, n_workers > 1, n_workers <=",
                      "helper_windows.size() (128), items.size() > k_store_block (16)"],
                     "model.hpp:3149-3161", "new"))
    boxes.append(("k_store_shared", "model.hpp:3149-3161"))
    o.append(text(FX + 8, 320, "called by main only, before it opens the window", 8.5, fill=C["muted"]))
    o.append(fn_cell(FX, 324, FW, 58, "k_store_cut_units(q_batch)",
                     ["cuts items into the work units; writes unit_start[0 .. n_units]",
                      "and n_units"],
                     "model.hpp:3163-3191", "new"))
    boxes.append(("k_store_cut_units", "model.hpp:3163-3191"))
    o.append(text(FX + 8, 404, "called once per claimed unit, by the thread that claimed it", 8.5,
                  fill=C["muted"]))
    o.append(fn_cell(FX, 408, FW, 58, "store_k_block(q_batch, slot, ks, task_begin, task_end)",
                     ["stores the K rows of items[task_begin, task_end): a run of one",
                      "token -> set_k_row, a run of 2..16 -> set_k_block (present mask)"],
                     "model.hpp:3193-3201", "new"))
    boxes.append(("store_k_block", "model.hpp:3193-3201"))
    # caller arrows into save_k
    o.append(arrow(fid, "ink", [(256, 62), (FX - 2, 62)], C["ink"]))
    o.append(arrow(fid, "ink", [(256, 170), (272, 170), (272, 62)], C["ink"]))
    o.append(arrow(fid, "muted", [(256, 272), (264, 272), (264, 80), (FX - 2, 80)], C["muted"]))
    # save_k -> impl
    o.append(arrow(fid, "ink", [(FX + 40, 92), (FX + 40, 102)], C["ink"]))
    o.append(text(FX + 48, 100, "save_k_impl<geometry>(..., worker_ix, n_workers)", 8.5,
                  fill=C["muted"]))
    # the bus from impl to shared, cut, store
    o.append(line(FX, 190, 288, 190, C["ink"], 1.4))
    o.append(line(288, 190, 288, 437, C["ink"], 1.4))
    o.append(arrow(fid, "ink", [(288, 269), (FX - 2, 269)], C["ink"]))
    o.append(arrow(fid, "ink", [(288, 353), (FX - 2, 353)], C["ink"]))
    o.append(arrow(fid, "ink", [(288, 437), (FX - 2, 437)], C["ink"]))

    # fields with who reads / writes
    RX, RW = 770, 220
    rows = [
        ("next_unit", ["main: store 0 (relaxed); all: fetch_add", "(acq_rel) per claim"],
         "model.hpp:3331, 3342"),
        ("opened", ["main: fetch_add 1 (release); helper:", "load (acquire) in the wait loop"],
         "model.hpp:3333, 3336"),
        ("finished", ["main: store 0 (relaxed), load (acquire)", "in the join; helper: fetch_add 1 (release)"],
         "model.hpp:3332, 3348, 3353"),
        ("n_units", ["main: written by k_store_cut_units;", "all: read once per window"],
         "model.hpp:3190, 3340"),
        ("unit_start", ["main: written by k_store_cut_units; all:", "read [u] and [u + 1] per claimed unit"],
         "model.hpp:3185, 3189, 3345"),
        ("helper_windows", ["helper: ++[worker_ix] (plain, its own", "slot); k_store_shared reads size()"],
         "model.hpp:3335, 3158"),
    ]
    ry = 34
    for name, desc, ref in rows:
        for s in desc:
            fit(s, 8.5, RW - 12, False, f"b2 field {name}")
        o.append(field_row(RX, ry, RW, 46, name, desc, ref, fill=C["unit_fill"], stroke=C["unit"],
                           desc_size=8.5))
        boxes.append((name + " (readers and writers)", ref))
        ry += 52
    # impl -> every counter; cut -> unit_start, n_units; shared -> helper_windows.size()
    o.append(arrow(fid, "unit", [(FX + FW, 160), (RX - 2, 160)], C["unit"]))
    o.append(text((FX + FW + RX) / 2, 154, "1 window", 8.5, "middle", fill=C["unit"], weight=600))
    o.append(text((FX + FW + RX) / 2, 172, "per pass, layer", 8.5, "middle", fill=C["unit"], weight=600))
    o.append(arrow(fid, "unit", [(FX + FW, 353), (735, 353), (735, 260), (RX - 2, 260)], C["unit"]))
    o.append(text(RX - 6, 247, "writes", 8.5, "end", fill=C["unit"], weight=600))
    o.append(arrow(fid, "unit", [(FX + FW, 269), (720, 269), (720, 317), (RX - 2, 317)], C["unit"]))
    o.append(text(RX - 6, 330, "reads size()", 8.5, "end", fill=C["unit"], weight=600))

    # the rule
    ny = 480
    o.append(rect(20, ny, 960, 72, C["soft"], C["line"], 1, 4))
    o.append(text(28, ny + 16, "the rule of the window protocol", 10.5, weight=700))
    nl = ["both sides decide with k_store_shared(): a window exists only when it says yes, so a helper never waits for a window main does not open",
          "(a pass with at most 16 items, such as a decode step, or more than 128 workers is not shared). A helper's W-th call waits for opened >= W, so",
          "window W of a pass is the W-th shared save_k of that pass on both sides. A unit index is assigned once (fetch_add). Main returns only when",
          "finished == n_workers - 1: every unit is stored, no helper is inside a window main has left, every row store happens-before the latch count_down."]
    for s in nl:
        fit(s, 8.5, 944, False, "b2 rule")
    o.append(lines(28, ny + 31, nl, 8.5, 11))
    o.append(cite(976, ny + 68, "model.hpp:3100-3127"))
    boxes.append(("the rule of the window protocol", "model.hpp:3100-3127 (Note [Shared block save])"))

    cap = ("The function model. The generated plugin calls save_k from run() (main, worker "
           "0) and from run_main_help (each helper, its worker_ix) at the same statement "
           "position. One save_k_impl serves both sides. Main alone calls k_store_cut_units. "
           "Every thread calls store_k_block once per claimed unit. The right column says "
           "who reads and writes each field, with the memory order of each access.")
    legend = [
        ("ctx", "grey box, thin grey outline: the callers (generated code, the test) and the rule note"),
        ("box", "white box, ink outline: a function of model.hpp, its one-line description under its name"),
        ("unit", "grey-blue: a field of the window with its readers and writers"),
        ("arrow", "ink arrow: a call (the bus at the left: save_k_impl calls the three functions below it)"),
        ("arrow_muted", "grey arrow: the test's call (context)"),
        ("grey-blue arrow: a function's access to the window's fields", "arrow", C["unit"]),
        ("thin ink line: the call bus from save_k_impl", "line", C["ink"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR; 'changed' = changed by it"),
    ]
    return figure(fid, W, H, "Function model: callers, save_k and its helpers, the fields each one touches",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B3: sequencing model --------------------------------------------------
def b3():
    fid = "common-b3"
    W, H = 1000, 700
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"]})]
    boxes = []
    # columns: step | who | what (mono) | next_unit | opened | finished | n_units | helper_windows[1],[2]
    cols = [("step", 20, 44), ("thread", 64, 112), ("what happens (memory order)", 176, 384),
            ("next_unit", 560, 76), ("opened", 636, 64), ("finished", 700, 68),
            ("n_units", 768, 64), ("helper_windows[1] [2]", 832, 150)]
    hy = 40
    o.append(rect(20, hy - 4, 962, 20, C["soft"], C["line"], 1, 3))
    for name, x, w in cols:
        o.append(text(x + 4, hy + 10, name, 9, weight=700))
    steps = [
        ("0", "-", ["before the window: the counters as the previous window left them",
                    "(opened 0 at the pass start; the test checks opened == 0 after an unshared store)"],
         ["-", "0", "-", "-", "0  0"], "t_llama_unit.cpp:4037"),
        ("1", "[main]", ["k_store_shared: layout on, 1 < 3 <= 128, 41 > 16 -> shared;",
                         "k_store_cut_units: unit_start = [0, 16, 32, 41], n_units = 3"],
         ["-", "0", "-", "3", "0  0"], "model.hpp:3314, 3330"),
        ("2", "[main]", ["next_unit.store(0, relaxed); finished.store(0, relaxed):",
                         "the counters are main's to reset (no helper is inside a window)"],
         ["0", "0", "0", "3", "0  0"], "model.hpp:3331-3332"),
        ("3", "[main]", ["opened.fetch_add(1, release): the window is open; the unit",
                         "table is published with it"],
         ["0", "1", "0", "3", "0  0"], "model.hpp:3333"),
        ("4", "[helpers 1, 2]", ["my_window = ++helper_windows[worker_ix] (= 1); wait while",
                                        "opened.load(acquire) < my_window (_mm_pause); 1 >= 1 -> go"],
         ["0", "1", "0", "3", "1  1"], "model.hpp:3335-3338"),
        ("5", "all three", ["claim: u = next_unit.fetch_add(1, acq_rel): main gets 0, helper 1",
                            "gets 1, helper 2 gets 2 (one possible order); each u < 3"],
         ["3", "1", "0", "3", "1  1"], "model.hpp:3341-3343"),
        ("6", "all three", ["store_k_block(q_batch, slot, ks, unit_start[u], unit_start[u + 1]):",
                            "unit 0 and 1 = set_k_block 0xffff, unit 2 = set_k_block 0x01ff"],
         ["3", "1", "0", "3", "1  1"], "model.hpp:3344-3345"),
        ("7", "all three", ["the next claim returns 3, 4, 5 (>= n_units): each loop ends;",
                            "next_unit ends at n_units + n_workers = 6 (the test checks it)"],
         ["6", "1", "0", "3", "1  1"], "model.hpp:3343; t_llama_unit.cpp:4092"),
        ("8", "[helpers 1, 2]", ["finished.fetch_add(1, release); return: a helper that leaves",
                                        "the claim loop has stored every unit it took"],
         ["6", "1", "2", "3", "1  1"], "model.hpp:3347-3350"),
        ("9", "[main]", ["join: while finished.load(acquire) < n_helpers (2): _mm_pause;",
                         "every 2^20 spins read the clock, abort after 120 s (watchdog)"],
         ["6", "1", "2", "3", "1  1"], "model.hpp:3351-3365"),
        ("10", "[main]", ["after the join: mark_k_complete and the GOF credits per token in",
                          "items order; upstream_kvs_ready[slot].count_down() for downstream"],
         ["6", "1", "2", "3", "1  1"], "model.hpp:3369-3386"),
    ]
    y = hy + 24
    for num, who, what, vals, ref in steps:
        rh = 46
        o.append(rect(20, y, 962, rh, "#fff", C["line"], 1, 3))
        o.append(rect(24, y + 4, 36, 14, C["ink"], C["ink"], 1, 3))
        o.append(text(42, y + 14.5, f"step {num}", 8.5, "middle", fill="#fff", weight=700))
        fit(who, 9, 110, False, "b3 who")
        o.append(text(68, y + 14, who, 9, weight=700))
        for s in what:
            fit(s, 8.5, 380, False, f"b3 step {num}")
        o.append(lines(180, y + 14, what, 8.5, 11))
        o.append(cite(556, y + rh - 4, ref))
        for (name, x, w), v in zip(cols[3:], vals):
            o.append(rect(x + 4, y + 8, w - 10, 26, C["unit_fill"], C["unit"], 1, 2))
            o.append(text(x + 4 + (w - 10) / 2, y + 25, v, 10, "middle", True, weight=600))
        y += rh + 4
    boxes.append(("step 0 .. step 10 (the window protocol)", "model.hpp:3100-3127 (Note); "
                  "model.hpp:3323-3368 (save_k_impl); t_llama_unit.cpp:4037, 4078-4092"))
    boxes.append(("next_unit", "common.hpp:1200-1202"))
    boxes.append(("opened", "common.hpp:1203-1204"))
    boxes.append(("finished", "common.hpp:1205"))
    boxes.append(("n_units", "common.hpp:1206"))
    boxes.append(("helper_windows", "common.hpp:1216-1218"))
    # the happens-before chain
    cy = y + 10
    o.append(rect(20, cy, 962, 60, C["soft"], C["line"], 1, 4))
    o.append(text(28, cy + 16, "the two release / acquire edges", 10.5, weight=700))
    el = ["opened: main's fetch_add (release) at step 3 -> a helper's load (acquire) at step 4: the helper sees unit_start and n_units.",
          "finished: a helper's fetch_add (release) at step 8 -> main's load (acquire) at step 9: main sees every row store of that helper,",
          "so every row store happens-before the latch count_down of step 10. next_unit's fetch_add is acq_rel: a claim is assigned once."]
    for s in el:
        fit(s, 8.5, 944, False, "b3 edges")
    o.append(lines(28, cy + 31, el, 8.5, 11))
    o.append(cite(976, cy + 56, "model.hpp:3113-3124"))
    boxes.append(("the two release / acquire edges", "model.hpp:3113-3124 (Note [Shared block save])"))

    cap = ("The sequencing model: the field values of the worked example's window after each "
           "step (3 workers, 41 items, 3 units). Main cuts, resets and opens; the helpers "
           "count their window and wait for opened; all three claim with fetch_add; the "
           "helpers bump finished; main joins, then marks. The claim order shown is one "
           "possible order: fetch_add fixes none.")
    legend = [
        ("lane", "white row, thin grey outline: one step of the protocol"),
        ("unit", "grey-blue: the value of a window field after the step ('-' = not yet reset by this window)"),
        ("ctx", "grey box, thin grey outline: the column header and the note on the release / acquire edges"),
        ("ink badge with white text: the step number", C["ink"], C["ink"], False, False),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Sequencing model: the window fields through one shared save_k window",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B4: interaction model (wall-clock lanes) ------------------------------
def b4():
    fid = "common-b4"
    W, H = 1000, 440
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"], "q": C["q"]})]
    boxes = []
    o.append(text(20, 24, "one shared save_k window of the worked example (schematic, not to scale)",
                  10.5, weight=700))
    labels = [("[main]", "worker_ix 0"), ("[helper 1]", "worker_ix 1"), ("[helper 2]", "worker_ix 2"),
              ("attention", "workers")]
    grid, ys, x0 = lanes_grid(20, 36, 960, labels, lane_h=64, gap=8)
    o.append(grid)
    boxes.append(("[main], [helper 1], [helper 2] (lanes)", "model.hpp:3094-3099 (worker_ix 0 is "
                  "main, 1 .. n_workers - 1 the helpers); TronCpp.hs:1364"))
    boxes.append(("attention workers (lane)", "model.hpp:3085 ('The attention workers' pending "
                  "sections wait behind it')"))
    X = x0 + 8
    G = 6
    # main lane: (label, width, fill, stroke, idle)
    m = ys[0]
    segs_main = [("k_store_cut_units", 100, C["unit_fill"], C["unit"], False),
                 ("reset, opened += 1", 96, C["unit_fill"], C["unit"], False),
                 ("claim u = 0, store unit 0 (16 rows x n_kv_heads)", 236, C["vnni_fill"], C["vnni"], False),
                 ("join: poll finished", 130, "#fff", C["ink"], True),
                 ("marks loop, credits", 110, "#fff", C["ink"], False)]
    x = X
    main_x = {}
    for label, w, fill, stroke, idle in segs_main:
        o.append(work_block(x, m + 10, w, 30, None, fill, stroke, idle=idle))
        main_x[label] = (x, x + w)
        x += w + G
    for label, w, fill, stroke, idle in segs_main:
        xa, xb = main_x[label]
        fit(label, 8.5, w - 6, False, "b4 main")
        o.append(text((xa + xb) / 2, m + 29, label, 8.5, "middle"))
    o.append(cite(X + 672, m + 56, "common.hpp:1207-1215; model.hpp:3330-3333, 3341-3345, 3351-3386"))
    boxes.append(("k_store_cut_units / reset, opened += 1 / claim and store / join / marks loop (main)",
                  "model.hpp:3330 (cut), 3331-3333 (reset, open), 3341-3345 (claim, store), "
                  "3351-3365 (join), 3369-3386 (marks)"))
    # helper lanes
    store_start = main_x["claim u = 0, store unit 0 (16 rows x n_kv_heads)"][0]
    for hi, ly in enumerate(ys[1:3]):
        wait_w = store_start - X - G
        segs = [("waits for opened (its 1st window)", wait_w, C["unit_fill"], C["ink"], True),
                (f"claim u = {hi + 1}, store unit {hi + 1}", 230 if hi == 0 else 150, C["vnni_fill"], C["vnni"], False),
                ("finished += 1", 70, C["unit_fill"], C["unit"], False),
                ("idle: its next kernel waits for attention", 230 if hi == 0 else 310, "#fff", C["ink"], True)]
        x = X
        xs = []
        for label, w, fill, stroke, idle in segs:
            o.append(work_block(x, ly + 10, w, 30, None, fill, stroke, idle=idle))
            xs.append((x, x + w, label))
            x += w + G
        for xa, xb, label in xs:
            fit(label, 8.5, xb - xa - 6, False, "b4 helper")
            o.append(text((xa + xb) / 2, ly + 29, label, 8.5, "middle"))
        o.append(cite(X + 672, ly + 56, "model.hpp:3335-3338, 3341-3345, 3347-3349, 3092-3094"))
    boxes.append(("waits for opened / claim and store / finished += 1 / idle (a helper)",
                  "model.hpp:3335-3338 (wait), 3341-3345 (claim, store), 3347-3349 (finished), "
                  "3092-3094 (idle helpers)"))
    # attention workers lane
    a = ys[3]
    aw = main_x["marks loop, credits"][1] - X
    o.append(work_block(X, a + 10, aw, 30, None, "#fff", C["q"], idle=True))
    o.append(work_block(X + aw + G, a + 10, 96, 30, None, C["q_fill"], C["q"]))
    o.append(text(X + aw / 2, a + 29, "pending sections wait: the downstream latch is counted down after the marks",
                  8.5, "middle"))
    o.append(text(X + aw + G + 48, a + 29, "pending sections", 8.5, "middle"))
    o.append(cite(X + aw + G + 96, a + 56, "model.hpp:3085, 3385", size=8.5))
    boxes.append(("pending sections (attention workers)", "model.hpp:3085; the latch at 3385"))
    # the critical path frame: main's serial part
    xa = main_x["k_store_cut_units"][0]
    xb = main_x["reset, opened += 1"][1]
    o.append(rect(xa - 2, m + 7, xb - xa + 4, 36, "none", C["crit"], 2.6, 2))
    xa = main_x["join: poll finished"][0]
    xb = main_x["marks loop, credits"][1]
    o.append(rect(xa - 2, m + 7, xb - xa + 4, 36, "none", C["crit"], 2.6, 2))
    ty = ys[3] + 64 + 24
    o.append(text(X, ty, "thick red frame = main's serial part (the cut, the open, the join wait, the marks); "
                  "the three stores run at the same time. Before this PR the whole store was", 8.5, fill=C["crit"]))
    o.append(text(X, ty + 12, "serial on main: 0.86 ms per layer, 105 ns per (token, KV head) row (qwen3-4b, 8 users, "
                  "prompt 1024, 128 tokens of each user per pass, delphi-3bda, 2026-09-14).", 8.5, fill=C["crit"]))
    o.append(cite(980, ty + 26, "model.hpp:3080-3085"))
    boxes.append(("main's serial part (critical path)", "model.hpp:3080-3085 (Note: 'the main thread's "
                  "largest serial piece of work'), 3323-3386"))
    # time axis
    o.append(line(X, ys[3] + 64 + 6, 980, ys[3] + 64 + 6, C["muted"], 1))
    o.append(text(980, ys[3] + 64 + 3, "wall-clock time ->", 8.5, "end", fill=C["muted"]))

    cap = ("The interaction model as wall-clock lanes: one shared window with 3 workers "
           "(worked example). Main cuts the items and opens the window. The helpers were "
           "waiting for opened. All three claim and store a unit at the same time. The "
           "helpers bump finished. Main spins on finished, then marks the tokens, which "
           "lets the attention workers' pending sections start. Durations are schematic, "
           "not measured.")
    legend = [
        ("lane", "white lane, thin grey outline: one thread; the gutter names it"),
        ("unit", "grey-blue block: work on the window's counters and tables (cut, reset, open, finished += 1)"),
        ("vnni", "blue block: the store of one work unit into the VNNI plane (store_k_block)"),
        ("idle", "ink dashed: waiting (a helper spins on opened; main spins on finished; a helper idle after the store)"),
        ("crit", "thick solid red frame: main's serial part, the critical path"),
        ("box", "white box, ink outline: the marks loop and the GOF credits on main"),
        ("q", "violet block: the attention workers' pending sections, which start after the marks"),
        ("violet dashed: the pending sections wait behind save_k", "#fff", C["q"], True, False),
        ("thin grey line: the wall-clock axis", "line", C["muted"]),
        ("red text: the measured cost of the serial per-token store before this PR", "text", C["crit"]),
        "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Interaction model: main, two helpers and the attention workers over wall-clock time",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B5: the work-unit invariants ------------------------------------------
def b5():
    fid = "common-b5"
    W, H = 1000, 480
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"]})]
    boxes = []
    o.append(text(20, 24, "what ends a unit (k_store_cut_units) and why two threads never write the same lanes",
                  10.5, weight=700))
    # three cases, each a strip of 16 lanes of one block
    cases = [
        ("case 1: a run of 16 items fills block 0 of page 7 (unit 0 of the example)",
         [1] * 16, [0] * 16, "one unit, present = 0xffff: each pair row is written with one full-line store",
         "common.hpp:1213-1214; model.hpp:3184-3185"),
        ("case 2: a job without KV work between two items of one block",
         [1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1], [0] * 6 + [2] + [1] * 9,
         "the change of token_jobs_do_kv ends the run: units A (lanes 0..5), B (the one job, no store), C (lanes 7..15); A and C",
         "common.hpp:1209-1212; model.hpp:3179-3184"),
        ("case 3: items of one block that are not consecutive (a partner job moved to the end of a grain)",
         [1] * 16, [0] * 15 + [1],
         "two units of the same block: their writers touch disjoint token lanes (masked stores), so two threads may write one block",
         "common.hpp:1209-1214; model.hpp:3179-3184"),
    ]
    y = 44
    for title, present, unit_of, note, ref in cases:
        o.append(rect(20, y, 960, 108, "#fff", C["line"], 1, 4))
        o.append(text(28, y + 15, title, 10, weight=700))
        # the lanes
        lx = 28
        for t in range(16):
            p = present[t]
            u = unit_of[t]
            if p == 0:
                fill, stroke, dash = C["empty_fill"], C["empty"], "3 2"
            else:
                fill, stroke, dash = C["rows_fill"], C["rows"], None
            o.append(rect(lx, y + 24, 26, 22, fill, stroke, 1, 2, dash))
            o.append(text(lx + 13, y + 39, str(t), 9, "middle", True))
            lx += 28
        # the units as brackets under the lanes
        runs = []
        start = 0
        for t in range(1, 17):
            if t == 16 or unit_of[t] != unit_of[start]:
                runs.append((start, t - 1, unit_of[start]))
                start = t
        for a, b, u in runs:
            xa, xb = 28 + a * 28, 28 + b * 28 + 26
            narrow = xb - xa < 60
            if all(present[t] == 0 for t in range(a, b + 1)):
                o.append(rect(xa, y + 52, xb - xa, 14, C["empty_fill"], C["empty"], 1, 2, "3 2"))
                o.append(text((xa + xb) / 2, y + 77 if narrow else y + 62, "no store", 8.5, "middle",
                              fill=C["muted"]))
            else:
                o.append(rect(xa, y + 52, xb - xa, 14, C["unit_fill"], C["unit"], 1, 2))
                lab = f"unit: lane {a}" if a == b else f"unit: lanes {a}..{b}"
                o.append(text((xa + xb) / 2, y + 77 if narrow else y + 62, lab, 8.5, "middle",
                              fill=C["unit"], weight=600))
        fit(note, 9, 940, False, "b5 note")
        o.append(text(28, y + 93, note, 9))
        o.append(cite(976, y + 104, ref))
        y += 116
    o.append(text(28, y + 8, "lane t of block c = page offset c * 16 + t; green = the row is in the run (its present bit set); grey dashed = not in this run",
                  9, fill=C["muted"]))
    o.append(cite(976, y + 20, "kv_cache.hpp:2080-2081"))
    boxes.append(("case 1 .. case 3: run_kv, run_page, run_block (what ends a unit)", "common.hpp:1207-1214; "
                  "model.hpp:3179-3184 (the if of k_store_cut_units: t == 0 || kv != run_kv || pg != run_page || block != run_block)"))
    boxes.append(("lane t of block c", "kv_cache.hpp:2080-2081 (bit t of present = the row of offset c * 16 + t)"))
    boxes.append(("present", "kv_cache.hpp:2080-2081; k_vnni.hpp:342-345 (store_block: present)"))
    # the three cuts
    ny = y + 30
    o.append(rect(20, ny, 960, 46, C["soft"], C["line"], 1, 4))
    nl = ["a unit never crosses a page (pg != run_page), a 16-token page block (block != run_block) or a change of token_jobs_do_kv (kv != run_kv);",
          "so a unit lies in one page, one block and one KV-write state (the unit invariant the three-thread test checks)."]
    for s in nl:
        fit(s, 8.5, 944, False, "b5 rule")
    o.append(lines(28, ny + 16, nl, 8.5, 11))
    o.append(cite(976, ny + 42, "model.hpp:3184; t_llama_unit.cpp:4097-4101"))
    boxes.append(("the unit invariant: run_kv, run_page, run_block", "model.hpp:3184; t_llama_unit.cpp:4097-4101"))

    cap = ("The work-unit invariants of the unit_start comment, on one 16-token block. A run "
           "ends at a page, a block or a change of token_jobs_do_kv. Two units that fall "
           "into one block hold disjoint lanes, so their masked stores never touch the same "
           "bytes. A run of 16 fills its block with one full-line store per pair row.")
    legend = [
        ("lane", "white box, thin grey outline: one case, one block of 16 lanes"),
        ("present", "green: a lane whose row is in the run (its present bit set)"),
        ("empty", "grey dashed: a lane not in this run (a job without KV work, or an absent token); no store"),
        ("unit", "grey-blue bracket: one work unit and the lanes it writes"),
        ("ctx", "grey box, thin grey outline: the rule of the cut"),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "The work-unit invariants: what ends a unit, disjoint lanes, full-line stores",
                  "".join(o), cap, boxes=boxes, legend=legend)
