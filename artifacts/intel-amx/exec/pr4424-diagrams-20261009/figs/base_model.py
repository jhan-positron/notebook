"""Base diagrams B1-B5 of the PR 4424 model.hpp page (key "model").

Worked example (STYLE.md, the same on all three pages): one shared save_k
window with 3 workers (main + 2 helpers) over 40 items. User A's tokens sit at
page 7 offsets 0..31 (two whole 16-token blocks), user B's at page 9 offsets
32..39 (8 tokens). Units [0,16) [16,32) [32,40): two whole-block saves
(set_k_block), one row-by-row run (set_k_row, row-major).

Every fact drawn here comes from facts/model.json (verified claims) or from
the cited head lines of h/tron/models/model.hpp, common.hpp, kv_cache.hpp,
h/tron/tensor/k_vnni.hpp and ingest/src/TronCpp.hs.

Exports for the change diagrams (from base_model import ...):
  constants: N_WORKERS_EXAMPLE, N_HELPERS_EXAMPLE, N_ITEMS_EXAMPLE,
             UNIT_START_EXAMPLE, N_UNITS_EXAMPLE, UNITS_EXAMPLE,
             THREADS_EXAMPLE, CLAIMS_EXAMPLE, WINDOW_FIELDS, STEP_FILL,
             MAIN_FILL, CRIT, CRIT_SW (the critical-path frame: thick ink)
  building blocks: field_row, step_box, item_strip, unit_table,
             window_counters, thread_tags, lanes_grid, block_state_box,
             decision_box, legend_blocks, crit_frame
"""
from svg_helpers import (C, arrow, block_cell, cite, figure, fn_cell, lane,
                         line, lines, marker_defs, rect, text, text_width,
                         work_block)

# ---- the worked example ----------------------------------------------------
N_WORKERS_EXAMPLE = 3                  # main + 2 helpers (t_llama_unit.cpp:3986)
N_HELPERS_EXAMPLE = N_WORKERS_EXAMPLE - 1   # n_helpers = n_workers - 1 (model.hpp:3379)
N_ITEMS_EXAMPLE = 40
UNIT_START_EXAMPLE = [0, 16, 32, 40]   # unit_start[0 .. n_units] (model.hpp:3222, 3228)
N_UNITS_EXAMPLE = 3
UNITS_EXAMPLE = [
    # u, items [begin, end), user, page, block c, page offsets, what store_k_block does
    dict(u=0, begin=0, end=16, user="user A", page=7, block=0, offsets="0..15",
         kind="a run of 16 -> set_k_block", call="set_k_block", state="vnni"),
    dict(u=1, begin=16, end=32, user="user A", page=7, block=1, offsets="16..31",
         kind="a run of 16 -> set_k_block", call="set_k_block", state="vnni"),
    dict(u=2, begin=32, end=40, user="user B", page=9, block=2, offsets="32..39",
         kind="8 rows -> set_k_row x 8", call="set_k_row", state="rm"),
]
THREADS_EXAMPLE = ["[main, worker_ix 0]", "[helper, worker_ix 1]",
                   "[helper, worker_ix 2]"]
# One possible claim order (thread index, unit): fetch_add fixes no order.
CLAIMS_EXAMPLE = [(0, 0), (1, 1), (2, 2)]

# The fields of batch::k_store_window_t (common.hpp:1170-1193), in order:
# (name, description lines, citation). Lines fit a 256 px row at 9 px.
WINDOW_FIELDS = [
    ("max_shared_workers", ["128: worker counts above this take the unshared",
                            "store; the array size of helper_windows"],
     "common.hpp:1171-1173"),
    ("next_unit", ["std::atomic<uint32_t>, own cache line: the claim",
                   "counter; a claim must not touch the polled line"],
     "common.hpp:1174-1176"),
    ("opened", ["std::atomic<uint32_t>, own cache line: windows",
                "opened so far in this pass"], "common.hpp:1177-1178"),
    ("finished", ["std::atomic<uint32_t>: helpers done with the",
                  "open window"], "common.hpp:1179"),
    ("n_units", ["uint32_t: work units of the open window"], "common.hpp:1180"),
    ("unit_start", ["std::array<uint32_t, max_minibatch_size + 1>:",
                    "unit u = items[unit_start[u], unit_start[u + 1])"],
     "common.hpp:1181-1189"),
    ("helper_windows", ["std::array<uint32_t, max_shared_workers>:",
                        "windows a helper has entered, by worker_ix"],
     "common.hpp:1190-1192"),
]

STEP_FILL = "#fff"          # a protocol step (B3)
MAIN_FILL = C["soft"]       # context cells (callers, unchanged code)
# The critical path (main's serial part) is a THICK SOLID RED frame: the
# user's wall-clock-lanes convention (critical path in red, its cost on the
# figure) wins over STYLE.md item 8, which reserved red for removed state.
# Removed / before state stays red too, but THIN and DASHED with the word
# "before"; a waiting critical step keeps its own thin dashed outline under
# the solid thick frame, so the two meanings never share a dash. Shared by
# B3, B4 and the change diagrams (d5, d6).
CRIT = C["crit"]
CRIT_SW = 2.6


def crit_frame(x, y, w, h, dash=None):
    """The critical-path frame drawn over a block: thick solid red, no fill.
    dash is accepted for old callers and ignored (see CRIT)."""
    return rect(x, y, w, h, "none", CRIT, CRIT_SW, 2)


def _w(s, size, mono=False):
    return text_width(s, size, mono)


# ---- building blocks -------------------------------------------------------
def field_row(x, y, w, h, name, desc, ref, tag=None, fill="#fff",
              stroke=C["ink"], dash=None, name_size=10, desc_size=9):
    """One field of a data box: name (mono, bold) with the citation at the
    right of the same line, then up to two description lines. The tag
    ('new', 'changed') follows the name when it fits, else the last line."""
    o = [rect(x, y, w, h, fill, stroke, 1.1, 3, dash)]
    o.append(text(x + 6, y + 13, name, name_size, mono=True, weight=600))
    o.append(cite(x + w - 4, y + 12, ref))
    ds = desc if isinstance(desc, (list, tuple)) else [desc]
    o.append(lines(x + 6, y + 25, ds, desc_size, 11))
    if tag:
        col = C["new"] if tag.startswith("new") else C["muted"]
        name_end = x + 6 + _w(name, name_size, True) * 1.08 + 8
        cite_start = x + w - 4 - _w(ref, 8.5, True)
        if name_end + _w(tag, 8.5) + 6 <= cite_start:
            o.append(text(name_end, y + 13, tag, 8.5, fill=col, weight=600))
        else:
            ly = y + 25 + 11 * (len(ds) - 1)
            lx = x + 6 + _w(ds[-1], desc_size) * 1.04 + 8
            o.append(text(lx, ly, tag, 8.5, fill=col, weight=600))
    return "".join(o)


def step_box(x, y, w, h, title, sub, ref, fill=STEP_FILL, stroke=C["ink"],
             dash=None, num=None, title_size=10.5, sub_size=9, sw=None):
    """A protocol step: optional step number, a title (mono, bold), sub lines,
    and the citation in the lower-right corner. dash = a waiting step;
    sw=CRIT_SW = a step on the critical path (main's serial part): the step
    keeps its own thin (dashed when waiting) outline under a solid thick red
    crit_frame."""
    crit = sw == CRIT_SW
    if sw is None or crit:
        sw = 1.3 if dash else 1.2
    o = [rect(x, y, w, h, fill, stroke, sw, 4, dash)]
    if crit:
        o.append(crit_frame(x, y, w, h))
    tx = x + 8
    if num is not None:
        o.append(rect(x + 8, y + 5, 36, 14, C["ink"], C["ink"], 1, 3))
        o.append(text(x + 26, y + 15.5, f"step {num}", 8.5, "middle",
                      fill="#fff", weight=700))
        tx = x + 50
    o.append(text(tx, y + 15, title, title_size, mono=True, weight=600))
    o.append(lines(x + 8, y + 29, sub, sub_size, 11.5))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def item_strip(x, y, cell=17, gap=1, unit_gap=10, h=16):
    """The 40 items of the worked example as one strip, grouped by unit.
    Returns (svg, x_end, spans) with spans = [(x0, x1), ...] per unit."""
    o = []
    spans = []
    cx = x
    for u in UNITS_EXAMPLE:
        x0 = cx
        for i in range(u["begin"], u["end"]):
            o.append(rect(cx, y, cell, h, C["unit_fill"], C["unit"], 0.8, 1))
            cx += cell + gap
        spans.append((x0, cx - gap))
        cx += unit_gap
    return "".join(o), cx - unit_gap, spans


def unit_table(x, y, cell_w=44, h=22, values=UNIT_START_EXAMPLE):
    """unit_start[0 .. n_units] of the worked example plus an unused tail."""
    o = []
    cx = x
    for i, v in enumerate(values):
        o.append(rect(cx, y, cell_w, h, C["unit_fill"], C["unit"], 1, 2))
        o.append(text(cx + cell_w / 2, y + 15, str(v), 10.5, "middle", True,
                      weight=600))
        o.append(text(cx + cell_w / 2, y - 4, f"[{i}]", 8.5, "middle", True,
                      fill=C["muted"]))
        cx += cell_w + 4
    o.append(rect(cx, y, cell_w, h, C["empty_fill"], C["empty"], 1, 2, "3 2"))
    o.append(text(cx + cell_w / 2, y + 15, "...", 10.5, "middle", True,
                  fill=C["muted"]))
    return "".join(o), cx + cell_w


def window_counters(x, y, values, w=92, h=32, gap=6):
    """A row of counter boxes: values = [(name, value_text, colour), ...]."""
    o = []
    cx = x
    for name, val, col in values:
        o.append(rect(cx, y, w, h, "#fff", col, 1.2, 3))
        o.append(text(cx + w / 2, y + 12, name, 8.5, "middle", True, fill=col,
                      weight=600))
        o.append(text(cx + w / 2, y + 26, val, 10, "middle", True, weight=600))
        cx += w + gap
    return "".join(o), cx - gap


def thread_tags(x, y, size=10.5, gap=18):
    """The bracketed thread names of the worked example in one row."""
    o = []
    cx = x
    for t in THREADS_EXAMPLE:
        o.append(text(cx, y, t, size, weight=700))
        cx += _w(t, size) + gap
    return "".join(o), cx


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


def block_state_box(x, y, w, h, state, title, sub, ref, size=10.5):
    """A 16-token block drawn by its layout state (block_cell colours) with a
    title, sub lines and a citation."""
    o = [block_cell(x, y, w, h, state)]
    o.append(text(x + w / 2, y + 15, title, size, "middle", True, weight=600))
    o.append(lines(x + w / 2, y + 29, sub, 9, 11, "middle"))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def decision_box(x, y, w, h, question, sub, ref):
    """A decision of the store (a question in bold, the test under it)."""
    o = [rect(x, y, w, h, "#fff", C["ink"], 1.6, 10)]
    o.append(text(x + w / 2, y + 16, question, 11, "middle", weight=700))
    o.append(lines(x + w / 2, y + 30, sub, 9, 11, "middle", mono=True))
    o.append(cite(x + w - 6, y + h - 4, ref))
    return "".join(o)


def legend_blocks(x, y):
    """The block colours shared with the kv_cache.hpp page (one row)."""
    items = [("vnni", "VNNI block"), ("rm", "row-major rows"),
             ("pend", "complete, may wait"),
             ("hw", "row-major, no bits (hardware attention)"),
             ("empty", "no row saved")]
    o = []
    cx = x
    for st, lab in items:
        o.append(block_cell(cx, y, 26, 14, st))
        o.append(text(cx + 32, y + 11, lab, 10))
        cx += 32 + _w(lab, 10) + 18
    return "".join(o)


# ---- B1: data model --------------------------------------------------------
def b1():
    fid = "model-b1"
    W, H = 1000, 800
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"], "pend": C["pend"]})]
    boxes = []
    AX, AW = 20, 250      # column A: the batch, the K buffer, the state
    BX, BW = 330, 280     # column B: the window (60 px gap to A for the labels)
    CX, CW = 690, 290     # column C: the page, the work unit
    GA = (AX + AW + BX) / 2   # the centre of the A -> B label gap

    # ---- column A: batch -------------------------------------------------
    o.append(rect(AX, 40, AW, 176, C["soft"], C["ink"], 1.2, 6))
    o.append(text(AX + 8, 56, "batch (one minibatch)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, 56, "common.hpp:993"))
    boxes.append(("batch", "common.hpp:993 (struct batch); Note at common.hpp:958-964"))
    rx, rw = AX + 12, AW - 24
    o.append(field_row(rx, 66, rw, 44, "items",
                       ["std::vector<token_job_id>: n_items jobs in",
                        "items order; n_items <= max_minibatch_size"],
                       "common.hpp:1084-1085"))
    boxes.append(("items", "common.hpp:1084-1085; 1 batch -> n_items items, at most "
                  "max_minibatch_size: model.hpp:3207-3209, common.hpp:1189"))
    o.append(field_row(rx, 114, rw, 44, "k_store_window",
                       ["k_store_window_t: the K store window of",
                        "this minibatch (column B)"],
                       "common.hpp:1193", tag="new"))
    boxes.append(("k_store_window", "common.hpp:1167-1169 (comment), 1193 (member)"))
    o.append(field_row(rx, 162, rw, 44, "downstream_minibatches",
                       ["context: the minibatches whose",
                        "upstream_kvs_ready[slot] save_k counts down"],
                       "common.hpp:1153", name_size=9))
    boxes.append(("downstream_minibatches / upstream_kvs_ready",
                  "common.hpp:1153, 1162; used at model.hpp:3455-3456"))

    # ---- column A: ks --------------------------------------------------
    # The K buffer is the roped K rows (logged 'WK roped'), not query data:
    # plain ink, not the query-side violet.
    ky = 232
    o.append(rect(AX, ky, AW, 124, "#fff", C["ink"], 1.2, 6))
    o.append(text(AX + 8, ky + 16, "ks (kv_buffer_t&)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, ky + 16, "model.hpp:3354, 3358"))
    boxes.append(("ks (kv_buffer_t&)", "model.hpp:3354 (parameter), 3358 (width "
                  "static_assert), 3443 (logged as 'WK roped')"))
    o.append(lines(AX + 8, ky + 30, ["the roped K rows of this minibatch: one row per",
                                     "token job, kv_width() = n_kv_heads x head_size"],
                   9, 11))
    # ks[ix] -> row_of: one K buffer row gives n_kv_heads K rows
    o.append(rect(AX + 10, ky + 50, 70, 20, "#fff", C["ink"], 1, 3))
    o.append(text(AX + 45, ky + 64, "ks[ix]", 10, "middle", True, weight=600))
    o.append(arrow(fid, "ink", [(AX + 45, ky + 71), (AX + 45, ky + 83)], C["ink"]))
    o.append(text(AX + 53, ky + 80, "n_kv_heads rows of head_size values", 8.5, "start",
                  fill=C["ink"], weight=600))
    # the lambda row_of, with what it does (model.hpp:3247-3250)
    o.append(rect(AX + 10, ky + 85, AW - 20, 32, "#fff", C["ink"], 1, 3))
    o.append(text(AX + 16, ky + 98, "row_of", 10, mono=True, weight=600))
    o.append(cite(AX + AW - 14, ky + 98, "model.hpp:3247-3250"))
    o.append(text(AX + 16, ky + 110, "(ix, kv_head) -> the K row: a slice of ks[ix]", 8.5,
                  fill=C["muted"]))
    boxes.append(("row_of", "model.hpp:3247-3250 (lambda in store_k_block: "
                  "slice<head_size>()(ks[ix].as_view(), kv_head * head_size))"))

    # ---- column A: state (model.hpp) ------------------------------------
    sy = 364
    o.append(rect(AX, sy, AW, 222, C["soft"], C["ink"], 1.2, 6))
    o.append(text(AX + 8, sy + 16, "state (model.hpp)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, sy + 16, "model.hpp:1115"))
    boxes.append(("state (model.hpp)", "model.hpp:1115 (struct state); the members "
                  "cited on each row"))
    o.append(field_row(rx, sy + 26, rw, 44, "token_jobs_do_kv",
                       ["with token_jobs: job -> token_id; 1 = the",
                        "job needs KV work this forward, 0 = skipped"],
                       "model.hpp:1159-1160"))
    boxes.append(("token_jobs, token_jobs_do_kv", "model.hpp:1159-1160"))
    o.append(field_row(rx, sy + 74, rw, 44, "k_store_block",
                       ["= k_vnni::BLOCK_TOKENS_16 (16): the block",
                        "one run of store_k_block fills at most"],
                       "model.hpp:3153", tag="new"))
    boxes.append(("k_store_block", "model.hpp:3153; tensor/k_vnni.hpp:68, 106"))
    o.append(field_row(rx, sy + 122, rw, 44, "pending_k_blocks_",
                       ["std::vector<pending_k_block>: the deferred",
                        "conversion list, filled on the main thread"],
                       "model.hpp:3169", tag="new", stroke=C["pend"], dash="5 3",
                       fill=C["pend_fill"]))
    boxes.append(("pending_k_blocks_", "model.hpp:3169; Note [K VNNI storage] "
                  "(model.hpp:3155-3163)"))
    o.append(field_row(rx, sy + 170, rw, 44, "k_join_clock_spins",
                       ["2^20 pause loops between clock reads;",
                        "k_join_timeout_s = 120 s: the watchdog"],
                       "model.hpp:3184-3187", tag="new"))
    boxes.append(("k_join_clock_spins, k_join_timeout_s", "model.hpp:3181-3187"))

    # ---- column B: k_store_window_t -------------------------------------
    o.append(rect(BX, 40, BW, 368, "#fff", C["ink"], 1.4, 6))
    o.append(text(BX + 8, 56, "k_store_window_t", 11.5, mono=True, weight=700))
    o.append(text(BX + 8 + _w("k_store_window_t", 11.5, True) * 1.08 + 8, 56, "new", 9,
                  fill=C["new"], weight=700))
    o.append(cite(BX + BW - 4, 56, "common.hpp:1170-1193"))
    boxes.append(("k_store_window_t", "common.hpp:1170-1193"))
    fy = 66
    for name, desc, ref in WINDOW_FIELDS:
        o.append(field_row(BX + 12, fy, BW - 24, 44, name, desc, ref))
        boxes.append((name, ref))
        fy += 48

    # threads note
    ty = 414
    o.append(rect(BX, ty, BW, 60, C["soft"], C["line"], 1, 4))
    o.append(lines(BX + 8, ty + 13, ["threads of a shared window: [main, worker_ix 0]",
                                     "+ [helpers, worker_ix 1 .. n_workers - 1];",
                                     "n_workers = 1 + n_main_helpers;",
                                     "n_helpers = n_workers - 1"],
                   9, 11))
    o.append(cite(BX + BW - 4, ty + 57, "TronCpp.hs:1388; model.hpp:3379"))
    boxes.append(("n_workers, n_helpers (threads of a shared window)", "TronCpp.hs:1388 (n_workers); "
                  "model.hpp:3379 (n_helpers); model.hpp:3107-3116"))

    # pending_k_block
    py = 482
    o.append(rect(BX, py, BW, 98, C["pend_fill"], C["pend"], 1.4, 6, "5 3"))
    o.append(text(BX + 8, py + 16, "pending_k_block", 11.5, mono=True, weight=700))
    o.append(text(BX + 8 + _w("pending_k_block", 11.5, True) * 1.08 + 8, py + 16, "new", 9,
                  fill=C["new"], weight=700))
    o.append(cite(BX + BW - 4, py + 16, "model.hpp:3164-3168"))
    boxes.append(("pending_k_block", "model.hpp:3164-3168; comment 3155-3163"))
    o.append(lines(BX + 8, py + 31, ["page* pg", "page::k_storage_ref storage  (taken at the save)",
                                     "uint32_t block  (= j / k_store_block)"], 9.5, 12,
                   mono=True))
    o.append(lines(BX + 8, py + 70, ["one block whose 16th row this pass saved through runs",
                                     "shorter than a block; pushed by save_k_impl on main"],
                   9, 11, fill=C["muted"]))

    # ---- column C: page ---------------------------------------------------
    o.append(rect(CX, 40, CW, 262, "#fff", C["ink"], 1.2, 6))
    o.append(text(CX + 8, 56, "page (64 token offsets)", 11.5, mono=True, weight=700))
    o.append(cite(CX + CW - 4, 56, "kv_cache.hpp:1940-1942"))
    boxes.append(("page", "kv_cache.hpp:1940-1942 (64 tokens per page); page_of at "
                  "model.hpp:1773; offset_in_page at kv_cache.hpp:2031"))
    # the page's four blocks: structure only (solid ink outline), not the
    # "no row saved" state (grey dashed) of the block legend
    bx = CX + 10
    for c in range(4):
        o.append(rect(bx, 66, 64, 24, "#fff", C["ink"], 1, 3))
        o.append(text(bx + 32, 82, f"block {c}", 9.5, "middle", mono=True))
        bx += 70
    boxes.append(("block 0 .. block 3", "kv_cache.hpp:2196 (c < page_size / "
                  "BLOCK_TOKENS_16); tensor/k_vnni.hpp:69"))
    o.append(lines(CX + 10, 102, ["1 page -> 4 blocks of 16 offsets",
                                  "(page_size / k_vnni::BLOCK_TOKENS_16)"],
                   9, 11, fill=C["muted"]))
    o.append(cite(CX + CW - 4, 113, "kv_cache.hpp:2196"))
    o.append(field_row(CX + 12, 126, CW - 24, 40, "k_rows_saved_",
                       ["[n_slots + 1] entries: one bit per page offset per",
                        "storage slot (64 bits); VNNI slots only"],
                       "kv_cache.hpp:2608-2617", fill=C["rows_fill"], stroke=C["rows"]))
    boxes.append(("k_rows_saved_", "kv_cache.hpp:2608-2617"))
    o.append(field_row(CX + 12, 170, CW - 24, 40, "k_vnni_blocks_",
                       ["[n_slots + 1] entries: one bit per 16-token block",
                        "per storage slot (4 used); set = the block holds VNNI"],
                       "kv_cache.hpp:2618-2622", fill=C["blk_fill"], stroke=C["blk"]))
    boxes.append(("k_vnni_blocks_", "kv_cache.hpp:2618-2622"))
    o.append(field_row(CX + 12, 214, CW - 24, 40, "k_storage_ref",
                       ["{ offset; state_ix }: k_storage_of(slot)",
                        "resolves it under the current view"],
                       "kv_cache.hpp:2137-2155"))
    boxes.append(("k_storage_ref / k_storage_of", "kv_cache.hpp:2137-2155"))
    o.append(field_row(CX + 12, 258, CW - 24, 40, "kv_block::k",
                       ["one K plane = 64 tokens x 128 bf16 = 16 KiB;",
                        "n_kv_heads planes per (slot, page), one per KV head"],
                       "kv_cache.hpp:2982-2983"))
    boxes.append(("kv_block::k", "kv_cache.hpp:2982-3002; tensor/k_vnni.hpp:24-29"))

    # ---- column C: the slot (what one attention operation writes) ----------
    SLY, SLW, SLH = 352, 200, 96
    o.append(rect(CX, SLY, SLW, SLH, "#fff", C["ink"], 1.2, 6))
    o.append(text(CX + 8, SLY + 15, "slot (binding.kv_slot)", 11, mono=True, weight=700))
    o.append(lines(CX + 8, SLY + 29, ["kv_slot_id: the KV storage that one",
                                      "attention operation writes; k_state_ix",
                                      "(slot) = its entry in the page's bit",
                                      "sets (entry n_slots = EAGLE)"], 9, 11))
    o.append(text(CX + 8, SLY + 76, "1 attention operation -> 1 slot", 8.5, fill=C["ink"],
                  weight=600))
    o.append(cite(CX + SLW - 4, SLY + SLH - 4, "model.hpp:3370; kv_cache.hpp:171"))
    boxes.append(("slot (binding.kv_slot)", "model.hpp:3370 (slot = binding.kv_slot); "
                  "kv_cache.hpp:171 (kv_slot_id selects persistent storage); "
                  "kv_cache.hpp:2502-2504 (k_state_ix)"))
    # slot -> the page's entries and planes (how many)
    o.append(arrow(fid, "ink", [(CX + 70, SLY), (CX + 70, 304)], C["ink"], 1.3))
    o.append(text(CX + 78, 328, "1 slot -> 1 entry of n_slots + 1", 8.5, "start",
                  fill=C["ink"], weight=600))
    o.append(text(CX + 78, 339, "and n_kv_heads kv_block::k planes", 8.5, "start",
                  fill=C["ink"], weight=600))

    # ---- column C: work unit ----------------------------------------------
    uy = 456
    o.append(rect(CX, uy, CW, 72, C["unit_fill"], C["unit"], 1.4, 6))
    o.append(text(CX + 8, uy + 15, "work unit u", 11, mono=True, weight=700))
    o.append(cite(CX + CW - 4, uy + 15, "common.hpp:1181-1188"))
    boxes.append(("work unit u", "common.hpp:1181-1188; model.hpp:3122-3124, 3395-3396"))
    o.append(text(CX + 8, uy + 29, "items[unit_start[u], unit_start[u + 1])", 9.5,
                  mono=True))
    o.append(lines(CX + 8, uy + 42, ["a run of consecutive items in one 16-token block of",
                                     "one page, with the same token_jobs_do_kv value; the",
                                     "open window uses entries 0 .. n_units of unit_start"],
                   9, 11))

    # ---- cardinality arrows ----------------------------------------------
    # items -> page offset (over the top)
    o.append(arrow(fid, "ink", [(AX + AW, 88), (GA, 88), (GA, 26), (835, 26), (835, 38)],
                   C["ink"], 1.3))
    o.append(text(600, 17, "1 item (token_job_id) -> 1 token_id (token_jobs) -> 1 page "
                  "(page_of) + 1 offset j (offset_in_page); block c = j / k_store_block",
                  9, "middle", fill=C["ink"], weight=600))
    # batch.k_store_window -> k_store_window_t: the label lines sit 12 px
    # above and below the arrow, inside the 60 px gap
    o.append(arrow(fid, "ink", [(AX + AW, 136), (BX - 2, 136)], C["ink"], 1.3))
    o.append(text(GA, 124, "1 window", 8.5, "middle", fill=C["ink"], weight=600))
    o.append(text(GA, 152, "per batch", 8.5, "middle", fill=C["ink"], weight=600))
    # unit_start -> work unit; the how-many label sits under the arrow's
    # second leg, clear of its vertical and of the box border
    o.append(arrow(fid, "unit", [(BX + BW, 328), (640, 328), (640, uy + 36), (CX - 2, uy + 36)],
                   C["unit"], 1.4))
    o.append(text(660, uy + 50, "n_units", 9, "middle", fill=C["unit"], weight=700))
    o.append(text(660, uy + 62, "<= n_items", 8.5, "middle", fill=C["unit"], weight=700))
    o.append(text(660, uy + 74, "units", 9, "middle", fill=C["unit"], weight=700))
    # work unit -> page offsets of one block (right of the slot box)
    o.append(arrow(fid, "unit", [(960, uy), (960, 304)], C["unit"], 1.4))
    o.append(text(952, 316, "<= 16 offsets of one block", 8.5, "end", fill=C["unit"],
                  weight=700))
    # pending_k_blocks_ -> pending_k_block (both label lines above the arrow)
    o.append(arrow(fid, "pend", [(AX + AW, 508), (BX - 2, 508)], C["pend"], 1.3))
    o.append(text(GA, 488, "0..1 per", 8.5, "middle", fill=C["pend"], weight=700))
    o.append(text(GA, 499, "KV item", 8.5, "middle", fill=C["pend"], weight=700))
    # pending_k_block -> page (around the bottom right); the last leg is 14 px
    # so that the 7 px marker lands on the page box's right border
    o.append(arrow(fid, "pend", [(BX + BW, 560), (996, 560), (996, 150), (CX + CW + 2, 150)],
                   C["pend"], 1.3))
    o.append(text(800, 554, "1 entry -> 1 pg (page), 1 storage (k_storage_ref), 1 block c",
                  9, "middle", fill=C["pend"], weight=700))
    o.append(text(800, 573, "at most n_items entries per save_k call (a block may be "
                  "queued twice)", 8.5, "middle", fill=C["muted"]))

    # ---- worked example --------------------------------------------------
    o.append(line(20, 590, 980, 590, C["line"]))
    o.append(text(20, 608, "Worked example: one shared save_k window, 3 workers "
                  "(main + 2 helpers), 40 items; units [0,16) [16,32) [32,40)", 11.5,
                  weight=700))
    strip, xe, spans = item_strip(130, 634)
    o.append(strip)
    o.append(text(122, 646, "items", 10, "end", True, fill=C["muted"]))
    for u, (x0, x1) in zip(UNITS_EXAMPLE, spans):
        mx = (x0 + x1) / 2
        o.append(text(mx, 628, f"{u['user']}, page {u['page']}, offsets {u['offsets']} "
                      f"(block {u['block']})", 9, "middle", fill=C["muted"]))
        o.append(text(x0, 662, f"item {u['begin']}", 8.5, "start", fill=C["muted"]))
        o.append(text(x1, 662, f"{u['end'] - 1}", 8.5, "end", fill=C["muted"]))
        col = C["vnni"] if u["state"] == "vnni" else C["rm"]
        o.append(text(mx, 678, f"unit {u['u']}: {u['kind']}", 9.5, "middle", fill=col,
                      weight=700))
    o.append(text(20, 716, "unit_start", 10, "start", True, fill=C["unit"], weight=700))
    tbl, te = unit_table(110, 702)
    o.append(tbl)
    o.append(text(te + 12, 716, "n_units = 3; entries 0 .. 3 used of max_minibatch_size + 1",
                  9.5))
    o.append(cite(980, 716, "model.hpp:3222, 3228-3229"))
    o.append(text(20, 756, "at the open", 10, fill=C["muted"]))
    ctr, ce = window_counters(110, 736, [("next_unit", "0", C["ink"]),
                                         ("finished", "0", C["ink"]),
                                         ("opened", "W - 1 -> W", C["ink"]),
                                         ("helper_windows[1]", "W", C["ink"]),
                                         ("helper_windows[2]", "W", C["ink"])],
                              w=104)
    o.append(ctr)
    o.append(text(ce + 12, 750, "W = the W-th shared save_k of the pass,", 9))
    o.append(text(ce + 12, 762, "the same number on both sides", 9))
    o.append(cite(980, 772, "model.hpp:3382-3386"))
    tags, _ = thread_tags(110, 792)
    o.append(tags)
    o.append(text(20, 792, "threads", 10, fill=C["muted"]))
    o.append(text(560, 792, "n_workers = 3 = 1 + n_main_helpers", 9.5))
    o.append(cite(980, 792, "TronCpp.hs:1388; t_llama_unit.cpp:3986"))

    cap = ("B1, data model. The left column is what save_k reads: the batch (one minibatch) "
           "with its items, the K buffer ks, and the state members of model.hpp. The middle "
           "column is batch::k_store_window_t, the window the PR adds in common.hpp, and the "
           "pending_k_block record of the deferred conversion list. The right column is the "
           "page with its two bit sets and the work unit, a run of consecutive items in one "
           "16-token block, and the slot (the KV storage one attention operation writes). "
           "Every arrow says how many. The band at the bottom is the worked "
           "example: 40 items cut into three units, and the counters at the open of window W. "
           "The slot-5 example of the kv_cache.hpp and k_vnni.hpp pages (page 7, bits 0..40 "
           "set, block 1 complete and waiting) is a different history of page 7: its rows "
           "arrived through short runs, not through this window's two whole-block saves.")
    legend = [
        ("ctx_ink", "grey fill, ink outline: the two groups of what save_k reads, batch "
                    "(one minibatch) and state (model.hpp)"),
        ("ctx", "grey fill, light grey outline: the note under k_store_window_t (the "
                "threads of a shared window and how n_workers and n_helpers relate)"),
        ("box", "white box, ink outline: a data-model entity or a field: the fields of "
                "batch and state, the K buffer ks with ks[ix] and row_of, "
                "k_store_window_t and its seven fields, the page with its four blocks, "
                "k_storage_ref and kv_block::k, the slot, and the five counters at the "
                "open; the name in bold monospace, the description in sans-serif"),
        ("orange dashed box, orange-red text and arrow: the deferred conversion list "
         "pending_k_blocks_ and its record pending_k_block, with their how-many labels "
         "(0..1 pending_k_block per KV item; 1 entry -> 1 page, 1 k_storage_ref, "
         "1 block c)", "multi", ["pend", ("arrow", C["pend"])]),
        ("rows", "green: k_rows_saved_, the page's saved-row bits (one per page offset "
                 "per storage slot)"),
        ("blk", "pink: k_vnni_blocks_, the page's converted-block bits (one per 16-token "
                "block per storage slot)"),
        ("grey-blue (box, text and arrow): the work units: work unit u, the 40 item "
         "cells and the entries 0 .. 3 of unit_start, the unit_start row label, and "
         "the arrows unit_start -> the units (n_units <= n_items), unit -> at most 16 "
         "offsets of one block", "multi", ["unit", ("arrow", C["unit"])]),
        ("empty", "grey dashed: the unused tail of unit_start (the entries after "
                  "n_units = 3) in the worked example"),
        ("blue text: units 0 and 1 of the worked example, a run of 16 -> set_k_block "
         "(the block is stored in the VNNI layout)", "text", C["vnni"]),
        ("orange text: unit 2 of the worked example, 8 rows -> set_k_row x 8 "
         "(row-major rows)", "text", C["rm"]),
        ("arrow", "ink arrow: a containment or a reference with its how-many: item -> "
                  "token_id -> page + offset, batch -> its window, ks[ix] -> n_kv_heads "
                  "K rows, slot -> its entry and its planes of the page"),
        ("font_mono", "monospace = a name or a value from the code: box titles, field "
                      "names, ks[ix], the unit_start entries and the counters at the open"),
        ("font_sans", "sans-serif = the description under a name, the how-many labels, "
                      "the worked example's prose"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the line or Note that defines a box or a "
                      "field (file:line)"),
        ("font_tag", "bold 'new' = a struct, a field or a constant this PR adds: "
                     "k_store_window, k_store_window_t, k_store_block, pending_k_blocks_, "
                     "pending_k_block, k_join_clock_spins"),
    ]
    return figure(fid, W, H, "Data model of save_k: batch, window, pending list, page",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B2: function model ----------------------------------------------------
def b2():
    fid = "model-b2"
    W, H = 1000, 660
    o = [marker_defs(fid, {"ink": C["ink"], "new": C["new"]})]
    boxes = []
    X1, W1 = 20, 180     # callers in other files
    X2, W2 = 225, 225    # entry points in model.hpp
    X3, W3 = 480, 235    # helpers in model.hpp
    X4, W4 = 745, 235    # the page (kv_cache.hpp) and k_vnni.hpp
    CH = 60              # one function cell: name + at most 2 description lines
    heads = [(X1, W1, "callers (other files)"), (X2, W2, "entry points, model.hpp"),
             (X3, W3, "helpers, model.hpp"), (X4, W4, "what they call (other files)")]
    for x, w, h in heads:
        o.append(text(x + w / 2, 26, h, 11.5, "middle", weight=700))

    def caller(x, y, w, h, ls, ref, label, reg=None):
        out = [rect(x, y, w, h, MAIN_FILL, C["line"], 1, 4)]
        out.append(lines(x + 8, y + 15, ls, 9.5, 12))
        out.append(cite(x + w - 4, y + h - 4, ref))
        boxes.append((label, reg or ref))
        return "".join(out)

    def cell(x, y, name, desc, ref, tag, label, reg, fill="#fff", size=11.5, h=CH):
        boxes.append((label, reg))
        return fn_cell(x, y, (W2 if x == X2 else W3 if x == X3 else W4), h, name, desc,
                       ref, tag=tag, fill=fill, size=size)

    # the rows of columns 3 and 4: y = 44 + 68 * i (cell 60 + gap 8)
    R = [44 + 68 * i for i in range(9)]
    mid = [y + CH / 2 for y in R]

    # column 1
    o.append(caller(X1, 44, W1, 64, ["generated run() [main]:", "K channel wait per item,",
                                     "then save_k(ks, 0, n_workers)"],
                    "TronCpp.hs:2951-2958", "saveKv: generated run() calls save_k(..., 0, n_workers)"))
    o.append(caller(X1, 120, W1, 64, ["generated run_main_help", "[main helper i, worker_ix 1 + i]:",
                                      "save_k(ks, worker_ix, n_workers)"],
                    "TronCpp.hs:1358-1360; 2888-2895",
                    "run_main_help (generated): save_k(..., worker_ix, n_workers)"))
    o.append(caller(X1, 196, W1, 64, ["handwritten plugin and tests:", "save_k with the defaults",
                                      "(worker_ix 0, n_workers 1)"],
                    "t_llama_unit.cpp:3931; llama.hpp:1038",
                    "save_k with the defaults (handwritten plugin, tests)"))
    FY = 528             # the forward() / run_forward row
    o.append(caller(X1, FY, W1, 64, ["forward() [main]:", "run_forward(...)"],
                    "model.hpp:1711; 1769", "forward()",
                    reg="model.hpp:1711 (definition); 1769 (the run_forward call)"))

    # column 2
    SY, IY = 100, 200    # save_k, save_k_impl
    o.append(cell(X2, SY, "save_k (two overloads)",
                  ["Store the K rows of the minibatch. The",
                   "defaults keep the store on the caller."],
                  "model.hpp:3465, 3476", "changed", "save_k (two overloads)",
                  "model.hpp:3459-3483", h=64))
    o.append(cell(X2, IY, "save_k_impl",
                  ["Every worker of the store calls this:",
                   "worker 0 is main, the others are helpers."],
                  "model.hpp:3352-3356", "changed", "save_k_impl", "model.hpp:3346-3457",
                  h=64))
    o.append(cell(X2, FY, "run_forward",
                  ["Called by forward() only. One call",
                   "added: convert_pending_k_blocks."],
                  "model.hpp:1782; 1840-1847", "changed", "run_forward",
                  "model.hpp:1782 (definition); 1840-1847 (the calls)", h=64))

    # column 3
    o.append(cell(X3, R[0], "k_store_shared",
                  ["Whether the K store of this minibatch",
                   "is shared with the helpers."],
                  "model.hpp:3191-3192", "new", "k_store_shared", "model.hpp:3189-3200"))
    o.append(cell(X3, R[1], "k_store_cut_units",
                  ["Cut the minibatch's items into the work",
                   "units. Main only, before the open."],
                  "model.hpp:3204", "new", "k_store_cut_units", "model.hpp:3202-3230"))
    o.append(cell(X3, R[2], "store_k_block",
                  ["Store the K rows (every KV head) of",
                   "items[task_begin, task_end) into slot."],
                  "model.hpp:3240-3245", "new", "store_k_block",
                  "model.hpp:3232-3344; row_of at 3247-3250"))
    o.append(cell(X3, R[3], "cached_operation_uses_hw",
                  ["attention_operation_uses_hw[operation.i]",
                   "!= 0: the hardware attention scores it"],
                  "model.hpp:1531-1533", "unchanged", "cached_operation_uses_hw",
                  "model.hpp:1530-1533", fill=MAIN_FILL))
    o.append(cell(X3, R[4], "operation_is_hardware_candidate",
                  ["has_hardware_slot: hardware geometry and this;",
                   "only then the GOF credit (credit_gof_save)"],
                  "model.hpp:1491; 3371-3373", "unchanged",
                  "operation_is_hardware_candidate (has_hardware_slot)",
                  "model.hpp:1491-1492 (definition); 3371-3373 (has_hardware_slot); "
                  "3450-3451 (the credit runs only then)", fill=MAIN_FILL, size=10.5))
    o.append(cell(X3, R[7], "wait_for_coop_gof",
                  ["Forward-end barrier: drains the GOF tail,",
                   "then waits for in-flight submits."],
                  "model.hpp:3583", "unchanged", "wait_for_coop_gof",
                  "model.hpp:3578-3592", fill=MAIN_FILL))
    o.append(cell(X3, R[8], "convert_pending_k_blocks",
                  ["Convert the queued blocks. Main thread,",
                   "after run() returned, staging drained."],
                  "model.hpp:3173", "new", "convert_pending_k_blocks",
                  "model.hpp:3171-3180"))

    # column 4
    o.append(cell(X4, R[0], "k_vnni::layout_on",
                  ["the layout gate: true for 128-dimension",
                   "heads when TRON_K_VNNI is defined"],
                  "tensor/k_vnni.hpp:119-130", "new", "k_vnni::layout_on",
                  "tensor/k_vnni.hpp:119-130"))
    o.append(cell(X4, R[1], "page_of, offset_in_page",
                  ["which page holds the token and its offset",
                   "j in the page; block c = j / k_store_block"],
                  "model.hpp:1773; kv_cache.hpp:2031", "unchanged", "page_of, offset_in_page",
                  "model.hpp:1773; kv_cache.hpp:2031", fill=MAIN_FILL))
    o.append(cell(X4, R[2], "set_k_block, note_k_block_saved",
                  ["16 rows of one block stored at once (VNNI);",
                   "then the 16 row bits and the block bit"],
                  "kv_cache.hpp:2277; 2195", "new", "set_k_block, note_k_block_saved",
                  "kv_cache.hpp:2265-2284; 2192-2200", size=11))
    o.append(cell(X4, R[3], "set_k_row",
                  ["one row into the layout its block holds",
                   "(row-major rows, or the VNNI column)"],
                  "kv_cache.hpp:2247", "new", "set_k_row", "kv_cache.hpp:2238-2262"))
    o.append(cell(X4, R[5], "note_k_row_saved, k_storage_of",
                  ["sets the row's bit; true when the block's 16",
                   "rows are saved and it is not converted yet"],
                  "kv_cache.hpp:2167; 2150", "new", "note_k_row_saved, k_storage_of",
                  "kv_cache.hpp:2157-2167; 2137-2155", size=11))
    o.append(cell(X4, R[6], "mark_k_complete, credit_gof_save",
                  ["log 'WK roped' (3443), mark_k_complete, then",
                   "credit_gof_save and the latch count_down"],
                  "kv_cache.hpp:2450; model.hpp:3550", "unchanged",
                  "mark_k_complete, credit_gof_save, upstream_kvs_ready.count_down "
                  "(and log_intermediate 'WK roped' before them)",
                  "kv_cache.hpp:2444-2450; model.hpp:3550-3552; 3455-3456; "
                  "log_intermediate at model.hpp:3443 (definition 1279)", fill=MAIN_FILL,
                  size=10.5))
    o.append(cell(X4, R[4], "page::k(slot, kv_head, j).set",
                  ["row-major slots only (requires",
                   "!k_vnni::layout_on): one row store"],
                  "kv_cache.hpp:2088-2096", "unchanged", "page::k(slot, kv_head, j).set",
                  "kv_cache.hpp:2088-2096", fill=MAIN_FILL, size=11))
    o.append(cell(X4, R[8], "k_block_to_vnni_at",
                  ["converts block c of every KV head in",
                   "place and sets the block bit (once)"],
                  "kv_cache.hpp:2214", "new", "k_block_to_vnni_at", "kv_cache.hpp:2214-2236"))

    # ---- arrows ----------------------------------------------------------
    ink = C["ink"]
    # callers -> save_k (a bus at x = 212)
    o.append(line(212, 76, 212, 228, ink, 1.3))
    for yy in (76, 152, 228):
        o.append(line(X1 + W1, yy, 212, yy, ink, 1.3))
    o.append(arrow(fid, "ink", [(212, SY + 32), (X2 - 2, SY + 32)], ink, 1.3))
    # save_k -> save_k_impl
    o.append(arrow(fid, "ink", [(337, SY + 64), (337, IY - 2)], ink, 1.3))
    o.append(text(343, SY + 86, "+ worker_ix, n_workers", 8.5, fill=C["muted"]))
    # save_k_impl -> column 3 (a bus at x = 465)
    o.append(line(X2 + W2, IY + 32, 465, IY + 32, ink, 1.3))
    o.append(line(465, mid[0], 465, mid[3], ink, 1.3))
    for yy in mid[:4]:
        o.append(arrow(fid, "ink", [(465, yy), (X3 - 2, yy)], ink, 1.3))
    # save_k_impl -> column 4 (after every store), a bus at x = 400 through
    # the empty rows 4 .. 6 of column 3
    o.append(line(400, IY + 64, 400, mid[6], ink, 1.3))
    o.append(arrow(fid, "ink", [(400, mid[4]), (X3 - 2, mid[4])], ink, 1.3))
    o.append(text(440, mid[4] - 6, "once per call", 9, "middle", fill=C["ink"], weight=600))
    o.append(arrow(fid, "ink", [(400, mid[5]), (X4 - 2, mid[5])], ink, 1.3))
    o.append(arrow(fid, "ink", [(400, mid[6]), (X4 - 2, mid[6])], ink, 1.3))
    o.append(text(572, mid[5] - 6, "[main, after every store] per KV item", 9, "middle",
                  fill=C["ink"], weight=600))
    o.append(text(572, mid[6] - 6, "[main] per token, in items order", 9, "middle",
                  fill=C["ink"], weight=600))
    # column 3 -> column 4 (store_k_block's three callees: a bus at x = 730)
    o.append(arrow(fid, "ink", [(X3 + W3, mid[0]), (X4 - 2, mid[0])], ink, 1.3))
    o.append(arrow(fid, "ink", [(X3 + W3, mid[1]), (X4 - 2, mid[1])], ink, 1.3))
    o.append(line(X3 + W3, mid[2], 730, mid[2], ink, 1.3))
    o.append(line(730, mid[2], 730, mid[4], ink, 1.3))
    for yy in (mid[2], mid[3], mid[4]):
        o.append(arrow(fid, "ink", [(730, yy), (X4 - 2, yy)], ink, 1.3))
    # forward() -> run_forward -> wait_for_coop_gof, convert_pending_k_blocks
    o.append(arrow(fid, "ink", [(X1 + W1, FY + 32), (X2 - 2, FY + 32)], ink, 1.3))
    o.append(line(X2 + W2, FY + 32, 465, FY + 32, ink, 1.3))
    o.append(line(465, mid[7], 465, mid[8], ink, 1.3))
    o.append(arrow(fid, "ink", [(465, mid[7]), (X3 - 2, mid[7])], ink, 1.3))
    o.append(arrow(fid, "ink", [(465, mid[8]), (X3 - 2, mid[8])], ink, 1.3))
    o.append(arrow(fid, "ink", [(X3 + W3, mid[8]), (X4 - 2, mid[8])], ink, 1.3))
    o.append(text(X2 + W2 / 2, FY + 78, "[main, forward end]", 9, "middle",
                  fill=C["ink"], weight=600))
    # legend
    o.append(lines(20, 310, ["tags: new = added by this PR,",
                             "changed = signature or body changed,",
                             "unchanged = context (grey cell)."], 9.5, 13, fill=C["muted"]))
    o.append(text(20, 356, "[...] = the thread that runs it.", 9.5, fill=C["muted"]))
    o.append(lines(20, 376, ["Arrows = calls, in column order:",
                             "caller -> entry point -> helper",
                             "-> page / k_vnni.hpp function."], 9.5, 13, fill=C["muted"]))
    o.append(lines(20, 422, ["Constants of the store (k_store_block,",
                             "k_join_clock_spins, k_join_timeout_s)",
                             "are in B1."], 9.5, 13, fill=C["muted"]))

    cap = ("B2, function model. Each cell is one function with a one-line description "
           "from its comment and the line that defines it. The two save_k overloads take "
           "a worker index and a worker count from the generated run() and run_main_help "
           "and forward them to save_k_impl. save_k_impl decides the sharing "
           "(k_store_shared) and cuts the units (k_store_cut_units, main only). "
           "store_k_block runs on any thread of the window. After every store, main "
           "records the rows and marks the tokens through the page functions at the right. "
           "convert_pending_k_blocks runs once per forward from run_forward, after "
           "wait_for_coop_gof.")
    legend = [
        ("box", "white cell, ink outline: a function this PR adds or changes: the entry "
                "points save_k, save_k_impl, run_forward; the helpers k_store_shared, "
                "k_store_cut_units, store_k_block, convert_pending_k_blocks; the page and "
                "k_vnni.hpp functions k_vnni::layout_on, set_k_block, set_k_row, "
                "note_k_row_saved, k_block_to_vnni_at; the name in bold monospace, the "
                "description in sans-serif"),
        ("ctx_ink", "grey cell, ink outline: an unchanged function the store calls: "
                    "cached_operation_uses_hw, operation_is_hardware_candidate, "
                    "wait_for_coop_gof, page_of / offset_in_page, page::k(...).set, "
                    "mark_k_complete / credit_gof_save"),
        ("ctx", "grey box, light grey outline: a caller in another file (the generated "
                "run() and run_main_help in TronCpp.hs, the handwritten plugin and the "
                "tests, forward()) with its call line and the thread in brackets"),
        ("arrow", "ink arrow: a call, in column order: caller -> entry point -> helper "
                  "-> page / k_vnni.hpp function; its label says how often and on which "
                  "thread"),
        ("font_mono", "monospace = a function name"),
        ("font_sans", "sans-serif = the one-line description of a function, the callers' "
                      "lines, the arrow labels and the key at the left"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the line that defines the function "
                      "(file:line)"),
        ("font_tag", "bold 'new' = a function this PR adds; grey 'changed' = its "
                     "signature or body changed; grey 'unchanged' = context (grey cell)"),
    ]
    return figure(fid, W, H, "Function model of save_k and its helpers", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- B3: sequencing model --------------------------------------------------
def b3():
    fid = "model-b3"
    W, H = 1000, 800
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "unit": C["unit"]})]
    boxes = []
    MX, MW = 20, 310     # main lane
    KX, KW = 380, 220    # the window counters
    HX, HW = 650, 330    # helper lane

    # headers
    o.append(rect(MX, 14, MW, 24, C["soft"], C["line"], 1, 4))
    o.append(text(MX + MW / 2, 30, "[main, worker_ix 0]", 11, "middle", weight=700))
    o.append(rect(KX, 14, KW, 24, C["soft"], C["line"], 1, 4))
    o.append(text(KX + KW / 2, 30, "batch::k_store_window", 11, "middle", True, weight=700))
    o.append(rect(HX, 14, HW, 24, C["soft"], C["line"], 1, 4))
    o.append(text(HX + HW / 2, 30, "[helper, worker_ix 1 .. n_workers - 1]", 11, "middle",
                  weight=700))
    boxes.append(("batch::k_store_window", "common.hpp:1167-1193"))

    # ---- main lane -------------------------------------------------------
    def M(y, h, title, sub, ref, num, label, dash=None, crit=False):
        """A main-lane step; crit = on the critical path (thick frame)."""
        boxes.append((label, ref))
        return step_box(MX, y, MW, h, title, sub, ref, dash=dash, num=num,
                        sw=CRIT_SW if crit else None)

    def Hh(y, h, title, sub, ref, num, label, dash=None):
        boxes.append((label, ref))
        return step_box(HX, y, HW, h, title, sub, ref, dash=dash, num=num)

    o.append(M(46, 58, "run() [generated]", ["K channel wait per item (startOperand),",
                                             "then save_k(ks, 0, n_workers)"],
               "TronCpp.hs:2951-2958", 0, "save_k(ks, 0, n_workers) [step 0 main: generated run()]"))
    o.append(M(114, 82, "is_main, shared",
               ["TRON_ASSERT(worker_ix < n_workers)",
                "is_main = worker_ix == 0; shared = k_store_shared(...)",
                "not shared: store_k_block(items[0, n_items)) on main",
                "alone, then step 6"],
               "model.hpp:3361-3366; 3417-3419", 1,
               "is_main, shared [step 1 main: the decision; unshared store]"))
    o.append(M(206, 70, "open the window",
               ["k_store_cut_units -> unit_start {0, 16, 32, 40}, n_units 3",
                "next_unit.store(0, relaxed); finished.store(0, relaxed)",
                "opened.fetch_add(1, release)"],
               "model.hpp:3380-3384", 2, "k_store_cut_units, opened.fetch_add [step 2 main: open the window]", crit=True))
    o.append(M(302, 94, "claim loop",
               ["u = next_unit.fetch_add(1, acq_rel); u >= n_units: break",
                "store_k_block(items[unit_start[u], unit_start[u + 1]))",
                "example: main takes u = 0 (page 7 block 0: set_k_block);",
                "its next claim returns u >= 3, main leaves the loop"],
               "model.hpp:3391-3397", 3, "next_unit.fetch_add, store_k_block [step 3 main: the claim loop]"))
    o.append(M(410, 94, "join (waits)",
               ["while (finished.load(acquire) < n_helpers (2)) _mm_pause()",
                "watchdog: a clock read every k_join_clock_spins (2^20) loops;",
                "t0 = the first read; TRON_ASSERT(now - t0 < 120 s), message:",
                "finished of n_helpers, claimed of n_units"],
               "model.hpp:3402-3416", 5, "finished.load, k_join_clock_spins [step 5 main: the join and its watchdog]",
               dash="5 3", crit=True))
    # the main lane has no step 4: that number is the helper's
    o.append(text(MX + 50 + _w("join (waits)", 10.5, True) * 1.08 + 10, 425,
                  "(step 4 is on the helper lane)", 8.5, fill=C["muted"]))
    o.append(M(518, 76, "record the rows (VNNI slot)",
               ["if (!cached_operation_uses_hw(binding.operation)):",
                "note_k_row_saved(slot, j) per KV item of q_batch->items;",
                "true -> push {&pg, k_storage_of(slot), j / k_store_block}",
                "example: all false (blocks 0, 1 whole; block 2: 8 of 16 rows)"],
               "model.hpp:3420-3439", 6, "note_k_row_saved loop [step 6 main: the row-recording loop]", crit=True))
    o.append(M(608, 70, "mark_k_complete, credit_gof_save",
               ["the per-token completion marks and GOF credits, in",
                "q_batch->items order: log 'WK roped', mark_k_complete(slot,",
                "j), credit_gof_save (hardware geometry, has_hardware_slot)"],
               "model.hpp:3440-3453", 7, "mark_k_complete, credit_gof_save [step 7 main: "
               "the per-token completion marks and GOF credits]", crit=True))
    o.append(M(692, 56, "ping downstream",
               ["for each downstream minibatch:",
                "upstream_kvs_ready[slot].count_down()"],
               "model.hpp:3454-3456", 8, "upstream_kvs_ready[slot].count_down [step 8 main: the downstream latches]", crit=True))

    # ---- helper lane -----------------------------------------------------
    o.append(Hh(46, 58, "run_main_help [generated]",
                ["save_k(ks, worker_ix, n_workers) at the same",
                 "statement position as main's call"],
                "TronCpp.hs:2888-2895", 0,
                "save_k(ks, worker_ix, n_workers) [step 0 helper: generated run_main_help]"))
    o.append(Hh(114, 82, "is_main, shared",
                ["TRON_ASSERT(worker_ix < n_workers); is_main = false",
                 "shared = k_store_shared (the same answer as main's)",
                 "if (!is_main && !shared) return: an unshared",
                 "store is main's alone"],
                "model.hpp:3361-3366", 1, "is_main, shared [step 1 helper: the decision, early return]"))
    o.append(Hh(206, 70, "wait for the window (waits)",
                ["my_window = ++helper_windows[worker_ix]",
                 "while (opened.load(acquire) < my_window) _mm_pause()",
                 "window W of the pass = the W-th shared save_k on both sides"],
                "model.hpp:3385-3390", 2, "helper_windows, opened.load [step 2 helper: wait for window W]", dash="5 3"))
    o.append(Hh(302, 94, "claim loop (the same loop)",
                ["u = next_unit.fetch_add(1, acq_rel); u >= n_units: break",
                 "store_k_block(items[unit_start[u], unit_start[u + 1]))",
                 "example: helper 1 takes u = 1 (page 7 block 1: set_k_block),",
                 "helper 2 takes u = 2 (page 9 offsets 32..39: set_k_row x 8)"],
                "model.hpp:3391-3397", 3, "next_unit.fetch_add, store_k_block [step 3 helper: the claim loop]"))
    o.append(Hh(410, 46, "finished.fetch_add(1, release); return",
                ["the helper leaves the window"],
                "model.hpp:3398-3401", 4, "finished.fetch_add(1, release) [step 4 helper: "
                "leaves the window and returns]"))
    o.append(Hh(470, 58, "back in run_main_help (idle)",
                ["the helper's next kernel waits for the",
                 "attention output"],
                "model.hpp:3107-3109", None, "helper after step 4: idle until the attention output",
                dash="5 3"))

    # ---- counters --------------------------------------------------------
    def K(y, h, title, sub, ref, label, stroke=C["ink"]):
        boxes.append((label, ref))
        out = [rect(KX, y, KW, h, "#fff", stroke, 1.2, 4)]
        out.append(text(KX + 8, y + 15, title, 10.5, mono=True, weight=600))
        out.append(lines(KX + 8, y + 29, sub, 9, 11.5))
        out.append(cite(KX + KW - 4, y + h - 4, ref))
        return "".join(out)

    o.append(K(150, 60, "helper_windows[1], [2]",
               ["W - 1 -> W: a plain ++ (not atomic),", "the helper's own slot"],
               "common.hpp:1192; model.hpp:3386", "helper_windows[worker_ix]"))
    o.append(K(216, 60, "unit_start, n_units",
               ["{0, 16, 32, 40}, 3: written by main", "before the open (release on opened)"],
               "common.hpp:1180, 1189", "unit_start, n_units (counters column)"))
    o.append(K(282, 46, "opened", ["W - 1 -> W (release); read with acquire"],
               "common.hpp:1178", "opened (counters column)"))
    o.append(K(334, 60, "next_unit", ["0 -> 1 -> 2 -> 3 (one unit per claim),",
                                      "then 3 failing claims -> 6"],
               "common.hpp:1176; model.hpp:3393-3394", "next_unit (counters column)",
               stroke=C["unit"]))
    o.append(K(420, 46, "finished", ["0 -> 1 -> 2 = n_helpers (n_workers - 1)"],
               "common.hpp:1179; model.hpp:3383, 3399, 3404", "finished (counters column)"))
    boxes[-1] = ("finished (counters column)",
                 "common.hpp:1179; model.hpp:3383, 3399, 3404 (n_helpers at 3379)")
    o.append(rect(KX, 580, KW, 72, C["soft"], C["line"], 1, 4))
    o.append(lines(KX + 8, 596, ["after the join: every unit is stored,",
                                 "no helper is inside this window, the",
                                 "counters are main's to reset; every row",
                                 "store happens-before the latch count_down"],
                   9, 11.5))
    boxes.append(("after the join (four things hold)", "model.hpp:3136-3141"))
    o.append(cite(KX + KW - 4, 648, "model.hpp:3136-3141"))

    # ---- arrows with their memory orders --------------------------------
    ink = C["ink"]
    # helper step 2 line 1 -> helper_windows
    o.append(arrow(fid, "ink", [(HX, 232), (KX + KW + 2, 180)], ink, 1.2))
    o.append(text(640, 200, "++", 9, "middle", fill=ink, weight=700))
    # main step 2 line 1 -> unit_start
    o.append(arrow(fid, "ink", [(MX + MW, 234), (KX - 2, 246)], ink, 1.2))
    o.append(text(352, 228, "write", 8.5, "middle", fill=ink, weight=700))
    # main step 2 line 3 -> opened
    o.append(arrow(fid, "ink", [(MX + MW, 262), (KX - 2, 305)], ink, 1.2))
    o.append(text(360, 264, "release", 8.5, "middle", fill=ink, weight=700))
    # opened -> helper step 2 line 2
    o.append(arrow(fid, "ink", [(KX + KW, 305), (HX - 2, 245)], ink, 1.2))
    # the label sits above the arrowhead, in the gap between the '++' line and
    # this line (a label centred on the diagonal collided with it)
    o.append(text(HX - 4, 240, "acquire", 8.5, "end", fill=ink, weight=700))
    # claim loops <-> next_unit
    # the labels are anchored at the next_unit box's edges (2 px off), clear
    # of the step boxes' borders and of the diagonal arrows
    o.append(arrow(fid, "unit", [(MX + MW, 332), (KX - 2, 364)], C["unit"], 1.3))
    o.append(text(KX - 2, 330, "fetch_add", 8.5, "end", fill=C["unit"], weight=700))
    o.append(text(KX - 2, 378, "acq_rel", 8.5, "end", fill=C["unit"], weight=700))
    o.append(arrow(fid, "unit", [(HX, 332), (KX + KW + 2, 364)], C["unit"], 1.3))
    o.append(text(KX + KW + 2, 330, "fetch_add", 8.5, "start", fill=C["unit"], weight=700))
    o.append(text(KX + KW + 2, 378, "acq_rel", 8.5, "start", fill=C["unit"], weight=700))
    # helper step 4 -> finished
    o.append(arrow(fid, "ink", [(HX, 438), (KX + KW + 2, 443)], ink, 1.2))
    o.append(text(625, 430, "release", 8.5, "middle", fill=ink, weight=700))
    # finished -> main step 5
    o.append(arrow(fid, "ink", [(KX, 443), (MX + MW + 2, 440)], ink, 1.2))
    o.append(text(355, 431, "acquire", 8.5, "middle", fill=ink, weight=700))
    # order marks between steps (thin)
    for y0, y1 in ((104, 112), (196, 204), (276, 300), (396, 408), (504, 516), (594, 606),
                   (678, 690)):
        o.append(line(MX + 26, y0, MX + 26, y1, C["muted"], 1))
    for y0, y1 in ((104, 112), (196, 204), (276, 300), (396, 408), (456, 468)):
        o.append(line(HX + 26, y0, HX + 26, y1, C["muted"], 1))
    # legend
    o.append(lines(380, 676, ["thick red frame = main's serial part (the critical path of B4);",
                              "dashed = a thread waits (spin with _mm_pause);",
                              "grey-blue = the claim counter and the units (work units).",
                              "",
                              "The example's claim order (main 0, helper 1 takes 1,",
                              "helper 2 takes 2) is one possible order: fetch_add",
                              "assigns each unit index once, to whichever thread",
                              "claims first (model.hpp:3133-3135)."], 9, 12, fill=C["muted"]))

    cap = ("B3, sequencing model: the steps of one shared save_k window, top to bottom, "
           "for the main thread (left) and one helper (right), with the window counters "
           "between them. Each arrow names its memory order: main publishes the unit table "
           "with a release on opened, a helper reads it with an acquire, every thread claims "
           "units with fetch_add (acq_rel), a helper leaves with a release on finished, and "
           "main's join reads finished with acquire. The worked example (40 items, 3 units, "
           "3 workers) fills in the counters. After this window nothing is queued. Blocks 0 "
           "and 1 of page 7 were saved whole and are VNNI already. Block 2 of page 9 has 8 "
           "of its 16 rows and waits for a later minibatch (of this pass or a later one).")
    legend = [
        ("box", "white box, ink outline: a step that runs without waiting (main steps 0, "
                "1, 2, 3, 6, 7, 8; helper steps 0, 1, 3, 4) and the window counters "
                "helper_windows, unit_start / n_units, opened, finished; the title in "
                "bold monospace, the code lines under it"),
        ("ctx", "grey fill, light grey outline: the three lane headers (main, the window, "
                "the helpers) and the note after the join"),
        ("solid ink badge: the step number ('step 0' .. 'step 8') at the top left of a "
         "step, in white text", C["ink"], C["ink"], False, False),
        ("idle", "dashed ink outline: a step that waits (spin with _mm_pause): main's "
                 "join (step 5), the helper's wait for the window (step 2) and the "
                 "helper idle in run_main_help after step 4"),
        ("crit", "thick solid red frame: main's serial part, the critical path of B4: "
                 "open the window (step 2), join (5), record the rows (6), "
                 "mark_k_complete / credit_gof_save (7), ping downstream (8)"),
        ("white box, grey-blue outline: next_unit, the claim counter of the window; "
         "grey-blue text = fetch_add / acq_rel on its arrows", "#fff", C["unit"], False,
         False),
        ("arrow", "ink arrow: a write or a read of a counter, labelled with its memory "
                  "order: ++ on helper_windows, write unit_start, release on opened, "
                  "acquire of opened, release on finished, acquire of finished"),
        ("grey-blue arrow: the claim, next_unit.fetch_add(1, acq_rel), from both claim "
         "loops", "arrow", C["unit"]),
        ("thin grey line down a lane: the order of the steps on that thread (no data "
         "moves along it)", "line", C["muted"]),
        ("font_mono", "monospace = a step title (the function or the statement), the "
                      "counter names and the header batch::k_store_window"),
        ("font_sans", "sans-serif = the code lines and the example under a title, the "
                      "lane headers, the memory-order labels and the notes"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the lines that define a step or a counter "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Sequencing model of one shared save_k window", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- B4: interaction model (wall-clock lanes) ------------------------------
def b4():
    fid = "model-b4"
    W, H = 1000, 600
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    red = C["crit"]
    soft, lin = C["soft"], C["muted"]
    LANE_H, GAP = 58, 6
    # lane 0: the old layout (before PR 4424), in the before style (red,
    # dashed, the word "before"): the one measured cost sits on its slice
    OY = 60
    o.append(rect(20, OY, 960, LANE_H, "#fff", red, 1, 3, "5 3"))
    o.append(text(28, OY + LANE_H / 2, "[main, before]", 11, weight=700, fill=red))
    o.append(text(28, OY + LANE_H / 2 + 13, "the old layout; helpers idle", 9.5,
                  fill=C["muted"]))
    o.append(cite(28, OY + 54, "base model.hpp:3077-3105", anchor="start"))
    boxes.append(("[main, before] (the old layout: the whole K store on main)",
                  "model.hpp:3087-3094 (the measurement and 'the main thread's largest "
                  "serial piece of work'); base model.hpp:3077-3105 (the store inside the "
                  "marks loop, removed after head 3446)"))
    labels = [("[main]", "worker_ix 0"), ("[main helper 1]", "worker_ix 1"),
              ("[main helper 2]", "worker_ix 2"),
              ("[attention workers]", "the last pool workers")]
    grid, ys, tx0 = lanes_grid(20, OY + LANE_H + GAP, 960, labels, lane_h=LANE_H, gap=GAP)
    o.append(grid)
    boxes.append(("[main]", "model.hpp:3107-3116 (worker_ix 0 is main)"))
    boxes.append(("[main helper 1], [main helper 2]",
                  "model.hpp:3107-3116; TronCpp.hs:1358-1360 (run_main_help(q_batches, 1 + i, "
                  "n_workers))"))
    boxes.append(("[attention workers]", "model.hpp:2338-2345 (Note [Attention workers are "
                  "the last pool workers]); 3093-3094"))
    # one citation per lane, in the gutter under the lane label (C2-N5)
    for i, ref in enumerate(["model.hpp:3380-3456", "model.hpp:3385-3401",
                             "model.hpp:3385-3401", "model.hpp:3093-3094; 2338"]):
        o.append(cite(28, ys[i] + 54, ref, anchor="start"))
    lane_end = ys[3] + LANE_H
    # time axis: the layer part 170..640, the forward end 650..970
    T0, TS, T1 = 170, 645, 970
    o.append(text(T0, 50, "layer L of the pass: around one save_k (one of many layers)", 10,
                  weight=700))
    o.append(cite(T0, 36, "model.hpp:3087-3088; 3144-3148", anchor="start"))
    o.append(line(TS, 30, TS, lane_end + 8, C["muted"], 1, "4 3"))
    o.append(text(TS + 10, 50, "the forward end (after the last layer)", 10, weight=700))
    o.append(cite(TS + 10, 36, "model.hpp:1836-1850", anchor="start"))
    AXY = lane_end + 16
    o.append(arrow(fid, "ink", [(T0, AXY), (T1, AXY)], C["ink"], 1.2))
    o.append(text(T0, AXY + 14, "wall-clock time ->  (durations schematic, not to scale; "
                  "the order and the overlap are the point)", 9, fill=C["muted"]))

    def wb(lane_i, x0, x1, label, fill, stroke, ref, boxname, idle=False, crit=False,
           size=8.5):
        """One block of a lane; idle = a wait (dashed outline); crit = on the
        critical path (thick solid red frame over the block)."""
        y = ys[lane_i] + 6
        h = 36
        svg = work_block(x0, y, x1 - x0, h, label, fill, stroke, idle=idle, size=size)
        if crit:
            svg += crit_frame(x0, y, x1 - x0, h)
        boxes.append((boxname, ref))
        return svg

    # the layer's time marks (schematic): rope 170..230, the K channel wait
    # 230..300, open 300..338, claim + store 338..452, join 452..490,
    # record + marks 490..580, the rest 580..640
    # --- the old layout (before) ---
    oy = OY + 6
    o.append(work_block(170, oy, 60, 36, "rope kernel", soft, lin, size=8.5))
    o.append(work_block(230, oy, 70, 36, "K channel wait", "#fff", C["ink"], idle=True, size=8.5))
    o.append(rect(300, oy, 280, 36, soft, red, 1.2, 2, "5 3"))
    o.append(text(440, oy + 14, "save_k: the whole K store on main alone (before)", 8.5,
                  "middle", fill=red, weight=700))
    o.append(text(440, oy + 27, "0.86 ms per layer (measured 2026-09-14): the critical path",
                  8.5, "middle", fill=red))
    o.append(work_block(580, oy, 60, 36, "save_v, ...", soft, lin))
    o.append(text(650, oy + 22, "run() joins, wait_for_coop_gof, logits (no conversion)", 9,
                  fill=C["muted"]))
    boxes.append(("save_k: the whole K store on main alone (before, removed): 0.86 ms per "
                  "layer", "model.hpp:3087-3094 (the measurement: 0.86 ms per layer, 105 ns "
                  "per (token, KV head) row, 2026-09-14 on delphi-3bda); base "
                  "model.hpp:3098-3105 (the per-token store inside the marks loop)"))
    # --- main lane ---
    o.append(wb(0, 170, 230, "rope kernel", soft, lin, "model.hpp:3146-3148",
                "main: K/Q rope kernel (before the K channel wait)"))
    o.append(wb(0, 230, 300, "K channel wait", "#fff", C["ink"],
                "TronCpp.hs:2951; model.hpp:3144-3146",
                "startOperand [main: the K channel wait per item, before save_k]", idle=True))
    o.append(text(265, ys[0] + 52, "startOperand", 8.5, "middle", fill=C["muted"]))
    o.append(wb(0, 300, 338, "open", "#fff", C["ink"], "model.hpp:3380-3384",
                "k_store_cut_units, opened.fetch_add [main: open (cut units, reset the counters, opened++)]", crit=True))
    o.append(wb(0, 338, 452, "claim + store units", C["unit_fill"], C["unit"],
                "model.hpp:3391-3397", "next_unit.fetch_add, store_k_block [main: claim + store units]"))
    o.append(wb(0, 452, 490, "join", "#fff", C["ink"], "model.hpp:3402-3416",
                "finished.load, k_join_clock_spins [main: join (spin, watchdog)]", idle=True, crit=True))
    o.append(wb(0, 490, 580, "record rows, marks", "#fff", C["ink"],
                "model.hpp:3420-3456", "note_k_row_saved, mark_k_complete, credit_gof_save, count_down [main: after the join]",
                crit=True))
    o.append(wb(0, 580, 640, "save_v, ...", soft, lin,
                "TronCpp.hs:2959-2960", "save_v [main: the rest of the schedule]"))
    # --- helpers ---
    for i in (1, 2):
        o.append(wb(i, 170, 300, "rope kernel", soft, lin,
                    "model.hpp:3146-3148", f"helper {i}: K/Q rope kernel (nothing blocks after it)"))
        o.append(wb(i, 300, 338, "wait", "#fff", C["ink"], "model.hpp:3385-3390",
                    f"helper {i}: wait for opened >= my_window", idle=True))
        o.append(wb(i, 338, 452, "claim + store units", C["unit_fill"], C["unit"],
                    "model.hpp:3391-3397", f"next_unit.fetch_add, store_k_block [helper {i}: claim + store units]"))
        o.append(wb(i, 452, 504, "", C["soft"], C["ink"], "model.hpp:3398-3401",
                    f"finished.fetch_add(1, release) [helper {i}: leaves the window]"))
        o.append(text(478, ys[i] + 20, "finished.", 8.5, "middle", mono=True))
        o.append(text(478, ys[i] + 31, "fetch_add", 8.5, "middle", mono=True))
        o.append(wb(i, 504, 640, "idle until the attention output", "#fff", C["ink"],
                    "model.hpp:3107-3109", f"helper {i}: idle (the next kernel waits for the "
                    "attention output)", idle=True))
    # --- attention workers ---
    o.append(wb(3, 170, 570, "pending section waits behind save_k (latch count_down); idle: "
                "help_drain_gof", "#fff", C["ink"],
                "model.hpp:3093-3094; 3455-3456; self_attention.hpp:761",
                "attention workers: the pending section waits behind save_k; idle workers "
                "help_drain_gof", idle=True))
    o.append(wb(3, 570, 640, "attention plan", C["q_fill"], C["q"],
                "model.hpp:2340-2345", "attention workers: the per-layer attention plan"))
    # --- forward end ---
    o.append(wb(0, 650, 706, "run() joins", "#fff", C["ink"], "model.hpp:1822-1830; 1836",
                "main, forward end: run() joins the helpers and the attention workers",
                idle=True))
    o.append(wb(0, 706, 794, "wait_for_coop_gof", soft, lin, "model.hpp:1840; 3583",
                "wait_for_coop_gof [main, forward end: drains the GOF tail backlog]"))
    o.append(text(750, ys[0] + 52, "drains the GOF tail", 8.5, "middle", fill=C["muted"]))
    o.append(wb(0, 794, 916, "convert_pending_k_blocks", C["pend_fill"], C["pend"],
                "model.hpp:1847; 3173-3180", "convert_pending_k_blocks [main, forward end]",
                crit=True))
    o.append(wb(0, 916, 970, "logits", soft, lin, "model.hpp:1849-1850",
                "Launch logit delivery (comment) [main, forward end]"))
    for i in (1, 2):
        o.append(wb(i, 650, 680, "exit", soft, lin, "TronCpp.hs:1360-1361",
                    f"helper {i}, forward end: exit (workers_done.count_down())"))
    o.append(wb(3, 650, 680, "exit", soft, lin, "model.hpp:3580-3582",
                "attention workers, forward end: exit; the GOF tail backlog is main's, in "
                "wait_for_coop_gof"))
    boxes[-1] = ("attention workers, forward end: exit; the GOF tail backlog is main's, in "
                 "wait_for_coop_gof", "model.hpp:3580-3582; self_attention.hpp:761")

    # critical path annotation (thick red bars under the lanes)
    BY = AXY + 24
    o.append(line(300, BY, 580, BY, CRIT, CRIT_SW))
    o.append(line(794, BY, 916, BY, CRIT, CRIT_SW))
    ty = BY + 16
    o.append(text(170, ty, "critical path (thick red frame): main's serial part of the layer "
                  "(open, join, record rows, marks, credits, latches) and the forward-end "
                  "conversion.", 9.5, fill=CRIT, weight=600))
    o.append(text(170, ty + 15, "Before the two remedies (block save, sharing) the whole K "
                  "store ran on main alone, with the VNNI K layout and the per-row scatter "
                  "store (the red dashed lane):", 9.5))
    o.append(text(170, ty + 28, "0.86 ms per layer, 105 ns per (token, KV head) row (measured "
                  "2026-09-14 on delphi-3bda: qwen3-4b, 8 users, prompt 1024, 128 tokens of each "
                  "user per pass).", 9.5))
    o.append(text(170, ty + 41, "The helpers were idle meanwhile. [model.hpp:3087-3094]", 9.5))
    o.append(text(170, ty + 56, "After the two remedies the store is split into units claimed by "
                  "main and the idle helpers (grey-blue). New split: unmeasured on this page "
                  "(Insufficient data).", 9.5))
    boxes.append(("serial piece of work [critical path, thick red frame]",
                  "model.hpp:3087-3094 (the measurement); 3380-3384, 3402-3456, 1847 (the "
                  "serial pieces)"))
    # legend
    ly = ty + 70
    o.append(rect(20, ly, 960, 62, "#fff", C["line"], 1, 4))
    o.append(work_block(32, ly + 10, 60, 18, "work", C["soft"], C["muted"]))
    o.append(text(98, ly + 23, "= real work (solid)", 9.5))
    o.append(work_block(220, ly + 10, 60, 18, "waits", "#fff", C["ink"], idle=True))
    o.append(text(286, ly + 23, "= waiting, even a spin-wait (dashed)", 9.5))
    o.append(work_block(470, ly + 10, 60, 18, "", C["unit_fill"], C["unit"]))
    o.append(text(536, ly + 23, "= claim + store units (work units of the window)", 9.5))
    o.append(crit_frame(32, ly + 36, 60, 18))
    o.append(text(98, ly + 49, "= critical path (main's serial part)", 9.5))
    o.append(rect(320, ly + 36, 60, 18, "#fff", red, 1, 2, "5 3"))
    o.append(text(386, ly + 49, "= before (removed)", 9.5))
    o.append(work_block(510, ly + 36, 60, 18, "", C["pend_fill"], C["pend"]))
    o.append(text(576, ly + 49, "= the deferred conversion", 9.5))
    o.append(work_block(740, ly + 36, 60, 18, "", C["q_fill"], C["q"]))
    o.append(text(806, ly + 49, "= attention scores (queries)", 9.5))
    H = ly + 76

    cap = ("B4, interaction model: one lane per thread over one layer and then the forward "
           "end, with the old layout (before PR 4424) as the red dashed lane on top. Solid "
           "blocks are work, dashed outlines are waiting. Main waits for the K channel (the "
           "roped K rows of every token, the startOperand wait of the generated run()) "
           "before save_k, and may idle there. The helpers reach their save_k call "
           "with nothing blocking after their rope kernel, wait for main to open the window, "
           "claim and store units beside main, and are idle again until the attention "
           "output. The attention workers' pending sections wait behind save_k. Durations "
           "are schematic. The only measurement quoted (0.86 ms per layer, with the VNNI K "
           "layout and the per-row store, before the two remedies of the Note) comes from "
           "the comment of Note [Shared block save] and sits on the old lane's save_k slice. "
           "The new split's time is unmeasured on this page (Insufficient data).")
    legend = [
        ("lane", "white box, light grey outline: one thread lane ([main], [main helper 1], "
                 "[main helper 2], [attention workers]) with its worker_ix and lines, and "
                 "the key under the caption"),
        ("grey block, grey outline: real work outside the K store: rope kernel, save_v, "
         "wait_for_coop_gof, logits, exit", C["soft"], C["muted"], False, False),
        ("idle", "white block, dashed ink outline: waiting, even a spin-wait: the K "
                 "channel wait, main's join, run() joins, the helpers' wait for the "
                 "window and their idle until the attention output, the attention "
                 "workers' pending section"),
        ("box", "white block, ink outline: main's own work in the window: open, and "
                "record rows, marks"),
        ("unit", "grey-blue: claim + store units, the work units of the window, on main "
                 "and on both helpers"),
        ("ctx_ink", "grey block, ink outline: finished.fetch_add, the helper leaving the "
                    "window"),
        ("pend_solid", "orange-red: convert_pending_k_blocks, the deferred conversion at "
                       "the forward end"),
        ("q", "violet: the attention plan of the attention workers (attention scores, "
              "queries)"),
        ("crit", "thick solid red frame: the critical path, main's serial part (open, "
                 "join, record rows + marks, convert_pending_k_blocks), and the red bars "
                 "under the time axis; red text = its caption"),
        ("gone", "red dashed: [main, before], the lane of the old layout (removed), where "
                 "the whole K store ran on main alone; red text = its name"),
        ("grey block, red dashed outline: save_k before PR 4424 on that lane, the whole "
         "K store on main alone, 0.86 ms per layer; red text = that measurement",
         C["soft"], C["crit"], True, False),
        ("arrow", "ink arrow: the wall-clock time axis (durations schematic)"),
        ("grey dashed vertical line: the boundary between layer L and the forward end "
         "(after the last layer)", "line", C["muted"], True),
        ("font_mono", "monospace = finished.fetch_add, the statement in the helpers' "
                      "block"),
        ("font_sans", "sans-serif = the lane names, the block labels, the headers, the "
                      "caption under the axis and the key"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the lines behind a lane, a block or a "
                      "header (file:line)"),
    ]
    return figure(fid, W, H, "Threads over one layer and the forward end", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- B5: decision model ----------------------------------------------------
def b5():
    fid = "model-b5"
    W, H = 1000, 780
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"],
                           "pend": C["pend"], "hw": C["hw"]})]
    boxes = []
    ink = C["ink"]

    def box(x, y, w, h, title, sub, ref, label, fill="#fff", stroke=ink, dash=None):
        boxes.append((label, ref))
        out = [rect(x, y, w, h, fill, stroke, 1.2, 4, dash)]
        out.append(text(x + w / 2, y + 15, title, 10.5, "middle", True, weight=600))
        out.append(lines(x + w / 2, y + 29, sub, 9, 11, "middle"))
        out.append(cite(x + w - 4, y + h - 4, ref))
        return "".join(out)

    def dec(x, y, w, h, q, sub, ref, label, reg=None):
        boxes.append((label, reg or ref))
        return decision_box(x, y, w, h, q, sub, ref)

    def blk(x, y, w, h, state, title, sub, ref, label, reg=None):
        boxes.append((label, reg or ref))
        return block_state_box(x, y, w, h, state, title, sub, ref)

    def lab(x, y, s, col=ink):
        return text(x, y, s, 9, "middle", fill=col, weight=700)

    # row 1 (y = 50): the run, VNNI slot?, run of 16?, whole-block save
    o.append(box(20, 50, 210, 84, "one run (store_k_block)",
                 ["consecutive KV items of block c of page",
                  "pg; an item without KV work is skipped;",
                  "ends at a page or block change, the same",
                  "offset twice, 16 rows, or task_end"],
                 "model.hpp:3241; 3280-3299", "store_k_block: one run"))
    o.append(dec(270, 50, 190, 60, "VNNI slot?",
                 ["k_vnni::layout_on<", "geometry.kv.head_size>"],
                 "model.hpp:3251", "VNNI slot? (k_vnni::layout_on)",
                 reg="model.hpp:3251; tensor/k_vnni.hpp:119-130"))
    o.append(dec(500, 50, 200, 60, "a run of 16?",
                 ["n == k_store_block; TRON_ASSERT", "(present == FULL_BLOCK_0XFFFF)"],
                 "model.hpp:3300; 3323-3324", "a run of 16? (n == k_store_block)"))
    o.append(box(750, 50, 230, 76, "set_k_block per KV head",
                 ["then note_k_block_saved(slot, c): the 16",
                  "row bits and the block bit, after the last",
                  "KV head [any thread of the window]"],
                 "model.hpp:3325-3340", "set_k_block per KV head, then note_k_block_saved"))
    # row 2: row-major slot path (left), set_k_row (middle), VNNI block (right)
    o.append(box(270, 160, 190, 70, "page::k(...).set",
                 ["one row store per token and KV",
                  "head (the old loop, moved here);",
                  "never shared: [main] alone"],
                 "model.hpp:3252-3261; 3193-3194",
                 "page::k(slot, kv_head, j).set (row-major slots, never shared)"))
    o.append(blk(270, 268, 190, 56, "rm", "row-major slot",
                 ["no bits; the recording loop is", "compiled out (never called)"],
                 "model.hpp:3420; kv_cache.hpp:2157",
                 "row-major slot (no bits; the recording loop is compiled out, so "
                 "note_k_row_saved is never called)",
                 reg="model.hpp:3420 (if constexpr layout_on); kv_cache.hpp:2157-2158"))
    o.append(box(500, 160, 200, 70, "set_k_row per token, KV head",
                 ["a run shorter than 16 (n < 16);", "the block's layout is set_k_row's",
                  "choice [any thread of the window]"],
                 "model.hpp:3304-3320", "set_k_row per token and KV head"))
    o.append(blk(750, 160, 230, 56, "vnni", "one VNNI block (set_k_block)",
                 ["16 row bits + block bit; never queued", "(note_k_row_saved false later)"],
                 "kv_cache.hpp:2265-2266; 2192-2200",
                 "one VNNI block (set_k_block): the whole-block save",
                 reg="model.hpp:3234-3235 ('stored as one VNNI block (set_k_block)'); "
                 "kv_cache.hpp:2265-2266 ('stored at once in the VNNI layout'); "
                 "2192-2200 (the bits); 2163 (never queued)"))
    # row 3: block converted already?
    o.append(dec(500, 268, 200, 56, "k_block_is_vnni?",
                 ["set_k_row reads the block bit"],
                 "model.hpp:3301-3303", "k_block_is_vnni? (set_k_row decides)",
                 reg="kv_cache.hpp:2252-2258; model.hpp:3301-3303"))
    o.append(blk(750, 268, 230, 56, "vnni", "a row saved again",
                 ["written into the VNNI column of", "the converted block (store_row)"],
                 "kv_cache.hpp:2161-2163, 2252-2258", "a row saved again: the VNNI column"))
    # row 4: row-major rows
    o.append(blk(500, 362, 200, 56, "rm", "row-major rows",
                 ["the block's row-major form, 256 bytes", "per token (Note [Row-major tail block])"],
                 "tensor/k_vnni.hpp:437-445", "row-major rows (Note [Row-major tail block])"))
    # row 5: after the join, main only
    o.append(rect(20, 446, 960, 186, C["soft"], C["line"], 1, 6))
    o.append(text(32, 464, "after every row is stored [main only], for every item of the "
                  "minibatch:", 10.5, weight=700))
    o.append(lines(32, 480, ["the rows of the two VNNI boxes above",
                             "arrive here too and answer false"], 9, 11, fill=C["muted"]))
    o.append(cite(976, 464, "model.hpp:3417-3439"))
    boxes.append(("note_k_row_saved loop: after every row is stored [main only]",
                  "model.hpp:3420-3439; 3417-3419 (the unshared store before it); 3142-3143"))
    o.append(dec(500, 476, 200, 60, "hardware-scored?",
                 ["cached_operation_uses_hw(", "binding.operation)"],
                 "model.hpp:3426; 1531-1533", "hardware-scored? (cached_operation_uses_hw)"))
    o.append(blk(250, 476, 210, 64, "hw", "stays row-major",
                 ["no row bit recorded, nothing queued,", "no conversion at the forward end"],
                 "model.hpp:3423-3425", "stays row-major (hardware attention)",
                 reg="model.hpp:3423-3425; kv_cache.hpp:729-734"))
    o.append(box(750, 470, 230, 70, "note_k_row_saved(slot, j)",
                 ["per KV item; true when the block's 16",
                  "rows are now saved and it is not",
                  "converted yet"],
                 "model.hpp:3433; kv_cache.hpp:2157-2163", "note_k_row_saved per row"))
    o.append(blk(500, 566, 200, 58, "rm", "incomplete block",
                 ["fewer than 16 rows: waits for a", "later minibatch (false)"],
                 "model.hpp:3301; kv_cache.hpp:2157-2167",
                 "note_k_row_saved false: an incomplete block (fewer than 16 rows)",
                 reg="kv_cache.hpp:2157-2167; the phrase at model.hpp:3301"))
    o.append(blk(750, 566, 230, 58, "pend", "complete, may wait",
                 ["pending_k_blocks_.push_back({&pg,", "k_storage_of(slot), j / k_store_block})"],
                 "kv_cache.hpp:2159-2161; model.hpp:3433-3436",
                 "pending_k_blocks_.push_back: complete, may wait",
                 reg="kv_cache.hpp:2159-2161 and 2610 (the comments that define the state); "
                 "model.hpp:3433-3436 (the push)"))
    # row 6: forward end
    o.append(box(750, 660, 230, 68, "convert_pending_k_blocks",
                 ["forward end [main]: k_block_to_vnni_at per",
                  "entry -> a VNNI block (blue, legend below);",
                  "a block queued twice converts once"],
                 "model.hpp:1847; 3173-3180", "convert_pending_k_blocks (forward end)",
                 fill=C["pend_fill"], stroke=C["pend"]))
    boxes[-1] = ("convert_pending_k_blocks (forward end)",
                 "model.hpp:1847; 3173-3180; kv_cache.hpp:2214-2236")

    # ---- arrows ----------------------------------------------------------
    o.append(arrow(fid, "ink", [(230, 80), (268, 80)], ink, 1.3))
    o.append(arrow(fid, "ink", [(460, 80), (498, 80)], ink, 1.3))
    o.append(lab(479, 74, "yes"))
    o.append(arrow(fid, "vnni", [(700, 80), (748, 80)], C["vnni"], 1.4))
    o.append(lab(724, 74, "yes", C["vnni"]))
    o.append(arrow(fid, "vnni", [(865, 126), (865, 158)], C["vnni"], 1.4))
    o.append(arrow(fid, "rm", [(365, 110), (365, 158)], C["rm"], 1.4))
    o.append(lab(385, 138, "no", C["rm"]))
    o.append(arrow(fid, "rm", [(365, 230), (365, 266)], C["rm"], 1.4))
    o.append(arrow(fid, "ink", [(600, 110), (600, 158)], ink, 1.3))
    o.append(lab(615, 138, "no"))
    o.append(arrow(fid, "ink", [(600, 230), (600, 266)], ink, 1.3))
    o.append(arrow(fid, "vnni", [(700, 296), (748, 296)], C["vnni"], 1.4))
    o.append(lab(724, 290, "yes", C["vnni"]))
    o.append(arrow(fid, "rm", [(600, 324), (600, 360)], C["rm"], 1.4))
    o.append(lab(615, 346, "no", C["rm"]))
    o.append(arrow(fid, "rm", [(600, 418), (600, 474)], C["rm"], 1.4))
    o.append(text(608, 440, "every stored row", 9, "start", fill=C["rm"], weight=700))
    o.append(arrow(fid, "hw", [(500, 506), (462, 506)], C["hw"], 1.4))
    o.append(lab(481, 500, "yes", C["hw"]))
    o.append(arrow(fid, "ink", [(700, 506), (748, 506)], ink, 1.3))
    o.append(lab(724, 500, "no"))
    o.append(arrow(fid, "rm", [(770, 540), (770, 550), (640, 550), (640, 564)], C["rm"], 1.4))
    o.append(text(705, 546, "false", 9, "middle", fill=C["rm"], weight=700))
    o.append(arrow(fid, "pend", [(880, 540), (880, 564)], C["pend"], 1.4))
    o.append(lab(898, 556, "true", C["pend"]))
    o.append(arrow(fid, "pend", [(865, 624), (865, 658)], C["pend"], 1.4))
    o.append(lab(900, 645, "forward end", C["pend"]))

    # notes
    o.append(rect(20, 160, 210, 70, "#fff", C["line"], 1, 4))
    o.append(lines(28, 175, ["K buffer not bf16: each row is",
                             "converted to bf16 on the stack",
                             "(conv, 16 x head_size, 64-byte",
                             "aligned) before either store."], 9, 11))
    o.append(cite(226, 226, "model.hpp:3263-3269"))
    boxes.append(("conv (bf16 conversion on the stack)", "model.hpp:3263-3269"))
    o.append(rect(20, 268, 210, 162, "#fff", C["line"], 1, 4))
    o.append(text(28, 284, "Worked example", 10, weight=700))
    o.append(lines(28, 298, ["units 0 and 1 (16 tokens each, page 7",
                             "blocks 0 and 1): the top path, VNNI",
                             "blocks at once.",
                             "unit 2 (page 9, offsets 32..39):",
                             "set_k_row x 8, block bit clear ->",
                             "row-major rows. After the join",
                             "note_k_row_saved returns false (8 of",
                             "16 rows), so block 2 of page 9 stays",
                             "incomplete until a later minibatch",
                             "(of this pass or a later one) saves",
                             "offsets 40..47."], 9, 11))
    o.append(cite(226, 426, "STYLE.md worked example"))
    o.append(text(20, 672, "Arrow labels are the answers of the decision they leave. "
                  "Thread names in brackets.", 9.5, fill=C["muted"]))
    o.append(text(20, 686, "The bits (k_rows_saved_, k_vnni_blocks_) belong to the page; "
                  "a row-major slot keeps none.", 9.5, fill=C["muted"]))
    o.append(text(20, 700, "The forward-end conversion (right) runs once per forward from "
                  "run_forward, after wait_for_coop_gof (B2, B4).", 9.5, fill=C["muted"]))
    o.append(text(20, 760, "block colours", 10, fill=C["muted"]))
    o.append(legend_blocks(110, 748))

    cap = ("B5, decision model: what one run of consecutive tokens becomes in the page. "
           "A VNNI slot stores a run of 16 as one block (set_k_block, bits at once, never "
           "queued) and a shorter run row by row (set_k_row, into the row-major form or into "
           "the VNNI column of a block converted already). After every row is stored (the "
           "join of a shared save, or main's own store of an unshared save), main calls "
           "note_k_row_saved for every KV item of the minibatch. The rows of a whole-block "
           "run answer false, because their bits were set at the store. The row that "
           "completes a block through short runs queues it, and the forward end converts it. "
           "Under hardware attention main records no row and queues no block. "
           "The block colours are those of the kv_cache.hpp page. The worked example's "
           "three units are traced in the note at the left.")
    legend = [
        ("box", "white box, ink outline: a step of the store (one run (store_k_block), "
                "set_k_block per KV head, page::k(...).set, set_k_row per token and KV "
                "head, note_k_row_saved(slot, j)) and, with rounded corners, a decision "
                "(VNNI slot?, a run of 16?, k_block_is_vnni?, hardware-scored?)"),
        ("ctx", "grey band, light grey outline: the recording loop after the join; every "
                "box inside it runs on main only, once per item of the minibatch"),
        ("lane", "white box, light grey outline: a note (the bf16 conversion of the K "
                 "buffer rows, and the worked example)"),
        ("blue box and arrow: the VNNI path: a run of 16 -> set_k_block per KV head -> "
         "one VNNI block, and a converted block -> a row saved again; blue text = the "
         "'yes' answers", "multi", ["vnni", ("arrow", C["vnni"])]),
        ("orange box and arrow: the row-major path: not a VNNI slot -> page::k(...).set "
         "-> row-major slot; block bit clear -> row-major rows -> every stored row -> "
         "hardware-scored?; false -> incomplete block; orange text = those answers",
         "multi", ["rm", ("arrow", C["rm"])]),
        ("orange-red dashed box, solid box and arrow: true -> complete, may wait (the "
         "block pending_k_blocks_.push_back queues); forward end -> "
         "convert_pending_k_blocks (the conversion of the queued blocks); orange-red "
         "text = the 'true' answer and 'forward end'",
         "multi", ["pend", "pend_solid", ("arrow", C["pend"])]),
        ("yellow box and arrow: hardware-scored? yes -> stays row-major (no row bit, "
         "nothing queued); yellow text = that 'yes'", "multi", ["hw", ("arrow", C["hw"])]),
        ("empty", "grey dashed: no row saved (a chip of the block colours row only; the "
                  "row repeats the block colours of the companion page "
                  "diagramming-code-changes-kv_cache.hpp.html so the two pages read alike)"),
        ("arrow", "ink arrow: the next step or decision while no layout is decided yet: "
                  "one run -> VNNI slot?, yes -> a run of 16?, no -> set_k_row, "
                  "set_k_row -> k_block_is_vnni?, no -> note_k_row_saved"),
        ("font_mono", "monospace = the title of a step or a block box (a function or a "
                      "block state) and the test under a decision"),
        ("font_sans", "sans-serif = a decision's question (bold), the description under "
                      "a title, the arrow labels (the answers), the notes at the left "
                      "and the block colours row"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the lines that define a box (file:line)"),
    ]
    return figure(fid, W, H, "Decision model of the K store of one run", "".join(o), cap,
                  boxes=boxes, legend=legend)
