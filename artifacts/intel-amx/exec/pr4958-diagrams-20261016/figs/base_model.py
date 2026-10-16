"""Base diagrams B1-B5 of the PR 4958 model.hpp page (key "model").

Worked example (STYLE.md, the same on all three pages): one shared save_k
window, layer 5 (storage slot 5), a generated plugin with 3 workers (main +
2 helpers), one user with 41 items at page 7 offsets 0..40. Units [0,16)
[16,32) [32,41): two whole-block saves (set_k_block, present 0xffff) and one
partial-block save (set_k_block, present 0x01ff, 9 tokens). A run of ONE
token (a decode step) takes set_k_row (the per-row scatter).

Every fact drawn here comes from the cited head lines (b39765ec29) of
h/tron/models/model.hpp, common.hpp, kv_cache.hpp, h/tron/tensor/k_vnni.hpp
and ingest/src/TronCpp.hs.

Exports for the change diagrams (from base_model import ...):
  constants: N_WORKERS_EXAMPLE, N_HELPERS_EXAMPLE, N_ITEMS_EXAMPLE,
             UNIT_START_EXAMPLE, N_UNITS_EXAMPLE, UNITS_EXAMPLE,
             THREADS_EXAMPLE, CLAIMS_EXAMPLE, WINDOW_FIELDS, STEP_FILL,
             MAIN_FILL, CRIT, CRIT_SW (the critical-path frame: thick red)
  building blocks: field_row, step_box, item_strip, unit_table,
             window_counters, thread_tags, lanes_grid, run_box,
             decision_box, legend_runs, crit_frame, fit
"""
import sys

from svg_helpers import (C, arrow, cite, figure, fn_cell, lane, line, lines,
                         marker_defs, rect, text, text_width, work_block)

# ---- the worked example ----------------------------------------------------
N_WORKERS_EXAMPLE = 3                  # main + 2 helpers (t_llama_unit.cpp:4042)
N_HELPERS_EXAMPLE = N_WORKERS_EXAMPLE - 1   # n_helpers = n_workers - 1 (model.hpp:3328)
N_ITEMS_EXAMPLE = 41
UNIT_START_EXAMPLE = [0, 16, 32, 41]   # unit_start[0 .. n_units] (model.hpp:3183, 3189)
N_UNITS_EXAMPLE = 3
UNITS_EXAMPLE = [
    # u, items [begin, end), page, block c, page offsets, present, what store_k_block does
    dict(u=0, begin=0, end=16, page=7, block=0, offsets="0..15", present="0xffff",
         kind="16 tokens -> set_k_block, 0xffff", call="set_k_block", state="full"),
    dict(u=1, begin=16, end=32, page=7, block=1, offsets="16..31", present="0xffff",
         kind="16 tokens -> set_k_block, 0xffff", call="set_k_block", state="full"),
    dict(u=2, begin=32, end=41, page=7, block=2, offsets="32..40", present="0x01ff",
         kind="9 tokens -> set_k_block, 0x01ff", call="set_k_block", state="part"),
]
THREADS_EXAMPLE = ["[main, worker_ix 0]", "[helper, worker_ix 1]",
                   "[helper, worker_ix 2]"]
# One possible claim order (thread index, unit): fetch_add fixes no order.
CLAIMS_EXAMPLE = [(0, 0), (1, 1), (2, 2)]

# The fields of batch::k_store_window_t (common.hpp:1196-1219), in order:
# (name, description lines, citation). Lines fit a 256 px row at 9 px.
WINDOW_FIELDS = [
    ("max_shared_workers", ["128: worker counts above this take the unshared",
                            "store; the array size of helper_windows"],
     "common.hpp:1197-1199"),
    ("next_unit", ["std::atomic<uint32_t>, own cache line: the claim",
                   "counter; a claim must not touch the polled line"],
     "common.hpp:1200-1202"),
    ("opened", ["std::atomic<uint32_t>, own cache line: windows",
                "opened so far in this pass"], "common.hpp:1203-1204"),
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

STEP_FILL = "#fff"          # a protocol step (B3)
MAIN_FILL = C["soft"]       # context cells (callers, unchanged code)
# The critical path (main's serial part) is a THICK SOLID RED frame (the
# wall-clock-lanes convention). Removed / before state is red too, but THIN
# and DASHED with the word "before".
CRIT = C["crit"]
CRIT_SW = 2.6


def crit_frame(x, y, w, h):
    """The critical-path frame drawn over a block: thick solid red, no fill."""
    return rect(x, y, w, h, "none", CRIT, CRIT_SW, 2)


def _w(s, size, mono=False):
    return text_width(s, size, mono)


def fit(s, size, w, mono=False, where=""):
    """Warn on stderr when a string is wider than w px (see the PNG too)."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w}", file=sys.stderr)
    return s


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
    """The 41 items of the worked example as one strip, grouped by unit.
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


def run_box(x, y, w, h, state, title, sub, ref, size=10.5):
    """What a run becomes, drawn by its store: 'full' (a whole block, VNNI
    blue), 'part' (a partial block: blue, dashed outline), 'row' (a run of
    one token: the per-row scatter, solid blue outline, white fill), 'rm'
    (a row-major slot, orange), 'empty' (nothing stored, grey dashed)."""
    if state == "full":
        r = rect(x, y, w, h, C["vnni_fill"], C["vnni"], 1.4, 3)
    elif state == "part":
        r = rect(x, y, w, h, C["vnni_fill"], C["vnni"], 1.4, 3, "5 3")
    elif state == "row":
        r = rect(x, y, w, h, "#fff", C["vnni"], 1.4, 3)
    elif state == "rm":
        r = rect(x, y, w, h, C["rm_fill"], C["rm"], 1.4, 3)
    elif state == "empty":
        r = rect(x, y, w, h, C["empty_fill"], C["empty"], 1, 3, "3 2")
    else:
        raise ValueError(state)
    o = [r]
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


def legend_runs(x, y):
    """The run colours of B5 and the change diagrams (one row)."""
    items = [("full", "a whole block (set_k_block, 0xffff)"),
             ("part", "a partial block (masked lanes)"),
             ("row", "one token (set_k_row scatter)"),
             ("rm", "a row-major slot (page::k)")]
    o = []
    cx = x
    for st, lab in items:
        if st == "full":
            o.append(rect(cx, y, 26, 14, C["vnni_fill"], C["vnni"], 1.4, 3))
        elif st == "part":
            o.append(rect(cx, y, 26, 14, C["vnni_fill"], C["vnni"], 1.4, 3, "5 3"))
        elif st == "row":
            o.append(rect(cx, y, 26, 14, "#fff", C["vnni"], 1.4, 3))
        elif st == "rm":
            o.append(rect(cx, y, 26, 14, C["rm_fill"], C["rm"], 1.4, 3))
        o.append(text(cx + 32, y + 11, lab, 10))
        cx += 32 + _w(lab, 10) + 18
    return "".join(o)


# ---- B1: data model --------------------------------------------------------
def b1():
    fid = "model-b1"
    W, H = 1000, 790
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"], "vnni": C["vnni"]})]
    boxes = []
    AX, AW = 20, 250      # column A: the batch, the K buffer, the state
    BX, BW = 330, 280     # column B: the window (60 px gap to A for the labels)
    CX, CW = 690, 290     # column C: the page, the work unit
    GA = (AX + AW + BX) / 2   # the centre of the A -> B label gap

    # ---- column A: batch -------------------------------------------------
    o.append(rect(AX, 40, AW, 176, C["soft"], C["ink"], 1.2, 6))
    o.append(text(AX + 8, 56, "batch (one minibatch)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, 56, "common.hpp:1019"))
    boxes.append(("batch", "common.hpp:1019 (struct batch); Note at common.hpp:992-1010"))
    rx, rw = AX + 12, AW - 24
    o.append(field_row(rx, 66, rw, 44, "items",
                       ["std::vector<token_job_id>: n_items jobs in",
                        "items order; n_items <= max_minibatch_size"],
                       "common.hpp:1110-1111"))
    boxes.append(("items", "common.hpp:1110-1111; 1 batch -> n_items items, at most "
                  "max_minibatch_size: model.hpp:3168-3170, common.hpp:1215"))
    o.append(field_row(rx, 114, rw, 44, "k_store_window",
                       ["k_store_window_t: the K store window of",
                        "this minibatch (column B)"],
                       "common.hpp:1219", tag="new"))
    boxes.append(("k_store_window", "common.hpp:1193-1195 (comment), 1219 (member)"))
    o.append(field_row(rx, 162, rw, 44, "downstream_minibatches",
                       ["context: the minibatches whose",
                        "upstream_kvs_ready[slot] save_k counts down"],
                       "common.hpp:1179", name_size=9))
    boxes.append(("downstream_minibatches / upstream_kvs_ready",
                  "common.hpp:1179, 1188; used at model.hpp:3384-3385"))

    # ---- column A: ks --------------------------------------------------
    # The K buffer is the roped K rows (logged 'WK roped'): one native row
    # per (token, KV head), in dimension order: the row-major orange.
    ky = 232
    o.append(rect(AX, ky, AW, 124, C["rm_fill"], C["rm"], 1.2, 6))
    o.append(text(AX + 8, ky + 16, "ks (kv_buffer_t&)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, ky + 16, "model.hpp:3303, 3307"))
    boxes.append(("ks (kv_buffer_t&)", "model.hpp:3303 (parameter), 3307 (width "
                  "static_assert), 3372 (logged as 'WK roped')"))
    o.append(lines(AX + 8, ky + 30, ["the roped K rows of this minibatch: one row per",
                                     "token job, kv_width() = n_kv_heads x head_size"],
                   9, 11))
    o.append(rect(AX + 10, ky + 50, 70, 20, "#fff", C["ink"], 1, 3))
    o.append(text(AX + 45, ky + 64, "ks[ix]", 10, "middle", True, weight=600))
    o.append(arrow(fid, "ink", [(AX + 45, ky + 71), (AX + 45, ky + 83)], C["ink"]))
    o.append(text(AX + 53, ky + 80, "n_kv_heads rows of head_size values", 8.5, "start",
                  fill=C["ink"], weight=600))
    o.append(rect(AX + 10, ky + 85, AW - 20, 32, "#fff", C["ink"], 1, 3))
    o.append(text(AX + 16, ky + 98, "row_of", 10, mono=True, weight=600))
    o.append(cite(AX + AW - 14, ky + 98, "model.hpp:3207-3210"))
    o.append(text(AX + 16, ky + 110, "(ix, kv_head) -> the K row: a slice of ks[ix]", 8.5,
                  fill=C["muted"]))
    boxes.append(("row_of", "model.hpp:3207-3210 (lambda in store_k_block: "
                  "slice<head_size>()(ks[ix].as_view(), kv_head * head_size))"))

    # ---- column A: state (model.hpp) ------------------------------------
    sy = 364
    o.append(rect(AX, sy, AW, 222, C["soft"], C["ink"], 1.2, 6))
    o.append(text(AX + 8, sy + 16, "state (model.hpp)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, sy + 16, "model.hpp:1113"))
    boxes.append(("state (model.hpp)", "model.hpp:1113 (struct state); the members "
                  "cited on each row"))
    o.append(field_row(rx, sy + 26, rw, 44, "token_jobs_do_kv",
                       ["with token_jobs: job -> token_id; 1 = the",
                        "job needs KV work this forward, 0 = skipped"],
                       "model.hpp:1157-1158"))
    boxes.append(("token_jobs, token_jobs_do_kv", "model.hpp:1157-1158"))
    o.append(field_row(rx, sy + 74, rw, 44, "k_store_block",
                       ["= k_vnni::BLOCK_TOKENS_16 (16): the size of",
                        "one block save and the longest run"],
                       "model.hpp:3138-3139", tag="new"))
    boxes.append(("k_store_block", "model.hpp:3138-3139; tensor/k_vnni.hpp:65"))
    o.append(field_row(rx, sy + 122, rw, 44, "k_scatter_run_len",
                       ["= 1: a run of this length is stored row",
                        "by row (set_k_row), not as a block"],
                       "model.hpp:3140-3141", tag="new"))
    boxes.append(("k_scatter_run_len", "model.hpp:3140-3141"))
    o.append(field_row(rx, sy + 170, rw, 44, "k_join_clock_spins",
                       ["2^20 pause loops between clock reads;",
                        "k_join_timeout_s = 120 s: the watchdog"],
                       "model.hpp:3142-3148", tag="new"))
    boxes.append(("k_join_clock_spins, k_join_timeout_s", "model.hpp:3142-3148"))

    # ---- column B: k_store_window_t -------------------------------------
    o.append(rect(BX, 40, BW, 368, "#fff", C["ink"], 1.4, 6))
    o.append(text(BX + 8, 56, "k_store_window_t", 11.5, mono=True, weight=700))
    o.append(text(BX + 8 + _w("k_store_window_t", 11.5, True) * 1.08 + 8, 56, "new", 9,
                  fill=C["new"], weight=700))
    o.append(cite(BX + BW - 4, 56, "common.hpp:1196-1219"))
    boxes.append(("k_store_window_t", "common.hpp:1196-1219"))
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
    o.append(cite(BX + BW - 4, ty + 57, "TronCpp.hs:1392; model.hpp:3328"))
    boxes.append(("n_workers, n_helpers (threads of a shared window)",
                  "TronCpp.hs:1392 (n_workers); model.hpp:3328 (n_helpers); "
                  "model.hpp:3092-3101"))

    # the present mask (what one block save carries)
    py = 482
    o.append(rect(BX, py, BW, 98, "#fff", C["ink"], 1.2, 6))
    o.append(text(BX + 8, py + 16, "present (__mmask16)", 11.5, mono=True, weight=700))
    o.append(cite(BX + BW - 4, py + 16, "model.hpp:3245"))
    boxes.append(("present (__mmask16)", "model.hpp:3245 (the local of one run); "
                  "kv_cache.hpp:2080-2081 (bit t = rows[t] is the row of offset "
                  "c * 16 + t); tensor/k_vnni.hpp:76-77 (FULL_BLOCK_0XFFFF)"))
    o.append(lines(BX + 8, py + 31, ["one bit per token lane of a block: bit t set =",
                                     "the row of offset c * 16 + t is in the run;",
                                     "0xffff = all 16 lanes (whole-line stores),",
                                     "else masked line stores to the set lanes"],
                   9, 11))
    bx0 = BX + 8
    for t in range(16):
        on = t < 9
        o.append(rect(bx0 + t * 15, py + 76, 13, 12, C["rows_fill"] if on else C["empty_fill"],
                      C["rows"] if on else C["empty"], 0.8, 1, None if on else "2 2"))
    o.append(text(bx0 + 16 * 15 + 6, py + 86, "0x01ff (unit 2)", 8.5, fill=C["rows"],
                  weight=600))

    # ---- column C: page ---------------------------------------------------
    o.append(rect(CX, 40, CW, 262, "#fff", C["ink"], 1.2, 6))
    o.append(text(CX + 8, 56, "page (64 token offsets)", 11.5, mono=True, weight=700))
    o.append(cite(CX + CW - 4, 56, "kv_cache.hpp:1887-1889"))
    boxes.append(("page", "kv_cache.hpp:1887-1889 (struct page, page_size = 64); page_of at "
                  "model.hpp:1771; offset_in_page at kv_cache.hpp:1972"))
    bx = CX + 10
    for c in range(4):
        o.append(rect(bx, 66, 64, 24, "#fff", C["ink"], 1, 3))
        o.append(text(bx + 32, 82, f"block {c}", 9.5, "middle", mono=True))
        bx += 70
    boxes.append(("block 0 .. block 3", "kv_cache.hpp:2095 (c < page_size / "
                  "BLOCK_TOKENS_16); tensor/k_vnni.hpp:66 (TOKEN_BLOCKS_4)"))
    o.append(lines(CX + 10, 102, ["1 page -> 4 blocks of 16 offsets",
                                  "(page_size / k_vnni::BLOCK_TOKENS_16)"],
                   9, 11, fill=C["muted"]))
    o.append(cite(CX + CW - 4, 113, "kv_cache.hpp:2095"))
    o.append(field_row(CX + 12, 126, CW - 24, 40, "kv_block::k",
                       ["one K plane = 64 tokens x 128 bf16 = 16 KiB;",
                        "n_kv_heads planes per (slot, page), one per KV head"],
                       "kv_cache.hpp:2593-2603", fill=C["vnni_fill"], stroke=C["vnni"]))
    boxes.append(("kv_block::k", "kv_cache.hpp:2593-2603 (k_storage: k_vnni_tensor for a "
                  "VNNI slot); tensor/k_vnni.hpp:21-30"))
    o.append(field_row(CX + 12, 170, CW - 24, 40, "set_k_block",
                       ["rows of up to 16 tokens of block c, stored at",
                        "once (store_block); the present mask names them"],
                       "kv_cache.hpp:2078-2096", tag="new"))
    boxes.append(("set_k_block", "kv_cache.hpp:2078-2096"))
    o.append(field_row(CX + 12, 214, CW - 24, 40, "set_k_row",
                       ["one token's K row into the slot's layout",
                        "(store_row: the per-row scatter, PR 4956)"],
                       "kv_cache.hpp:2061-2076"))
    boxes.append(("set_k_row", "kv_cache.hpp:2061-2076"))
    o.append(field_row(CX + 12, 258, CW - 24, 40, "k(slot, kv_head, j).set",
                       ["row-major slots only (requires !layout_on):",
                        "one row store, 4 whole lines"],
                       "kv_cache.hpp:2015-2029", name_size=9.5))
    boxes.append(("k(slot, kv_head, j).set (page::k)", "kv_cache.hpp:2015-2029"))

    # ---- column C: the slot (what one attention operation writes) ----------
    SLY, SLW, SLH = 352, 200, 84
    o.append(rect(CX, SLY, SLW, SLH, "#fff", C["ink"], 1.2, 6))
    o.append(text(CX + 8, SLY + 15, "slot (binding.kv_slot)", 11, mono=True, weight=700))
    o.append(lines(CX + 8, SLY + 29, ["kv_slot_id: the KV storage that one",
                                      "attention operation writes; every",
                                      "KV head's plane of the slot is stored"], 9, 11))
    o.append(text(CX + 8, SLY + 70, "1 attention operation -> 1 slot", 8.5, fill=C["ink"],
                  weight=600))
    o.append(cite(CX + SLW - 4, SLY + SLH - 4, "model.hpp:3319; kv_cache.hpp:186"))
    boxes.append(("slot (binding.kv_slot)", "model.hpp:3319 (slot = binding.kv_slot); "
                  "kv_cache.hpp:186 (kv_slot_id selects persistent storage)"))
    o.append(arrow(fid, "vnni", [(CX + 70, SLY), (CX + 70, 304)], C["vnni"], 1.3))
    o.append(text(CX + 78, 328, "1 slot -> n_kv_heads", 8.5, "start",
                  fill=C["vnni"], weight=600))
    o.append(text(CX + 78, 339, "kv_block::k planes per page", 8.5, "start",
                  fill=C["vnni"], weight=600))

    # ---- column C: work unit ----------------------------------------------
    uy = 456
    o.append(rect(CX, uy, CW, 72, C["unit_fill"], C["unit"], 1.4, 6))
    o.append(text(CX + 8, uy + 15, "work unit u", 11, mono=True, weight=700))
    o.append(cite(CX + CW - 4, uy + 15, "common.hpp:1207-1214"))
    boxes.append(("work unit u", "common.hpp:1207-1214; model.hpp:3107-3109, 3344-3345"))
    o.append(text(CX + 8, uy + 29, "items[unit_start[u], unit_start[u + 1])", 9.5,
                  mono=True))
    o.append(lines(CX + 8, uy + 42, ["a run of consecutive items in one 16-token block of",
                                     "one page, with the same token_jobs_do_kv value; the",
                                     "open window uses entries 0 .. n_units of unit_start"],
                   9, 11))

    # ---- cardinality arrows ----------------------------------------------
    o.append(arrow(fid, "ink", [(AX + AW, 88), (GA, 88), (GA, 26), (835, 26), (835, 38)],
                   C["ink"], 1.3))
    o.append(text(600, 17, "1 item (token_job_id) -> 1 token_id (token_jobs) -> 1 page "
                  "(page_of) + 1 offset j (offset_in_page); block c = j / k_store_block",
                  9, "middle", fill=C["ink"], weight=600))
    o.append(arrow(fid, "ink", [(AX + AW, 136), (BX - 2, 136)], C["ink"], 1.3))
    o.append(text(GA, 124, "1 window", 8.5, "middle", fill=C["ink"], weight=600))
    o.append(text(GA, 152, "per batch", 8.5, "middle", fill=C["ink"], weight=600))
    o.append(arrow(fid, "unit", [(BX + BW, 328), (640, 328), (640, uy + 36), (CX - 2, uy + 36)],
                   C["unit"], 1.4))
    o.append(text(660, uy + 50, "n_units", 9, "middle", fill=C["unit"], weight=700))
    o.append(text(660, uy + 62, "<= n_items", 8.5, "middle", fill=C["unit"], weight=700))
    o.append(text(660, uy + 74, "units", 9, "middle", fill=C["unit"], weight=700))
    o.append(arrow(fid, "unit", [(960, uy), (960, 304)], C["unit"], 1.4))
    o.append(text(952, 316, "<= 16 offsets of one block", 8.5, "end", fill=C["unit"],
                  weight=700))
    # present -> set_k_block (around the bottom right)
    o.append(arrow(fid, "ink", [(BX + BW, 530), (996, 530), (996, 190), (CX + CW + 2, 190)],
                   C["ink"], 1.3))
    o.append(text(800, 546, "1 run of 2 .. 16 tokens -> 1 present mask -> n_kv_heads "
                  "set_k_block calls", 9, "middle", fill=C["ink"], weight=600))
    o.append(text(800, 562, "(a run of 1 token -> n_kv_heads set_k_row calls, no mask)",
                  8.5, "middle", fill=C["muted"]))
    # ks -> the page's store entry points
    o.append(arrow(fid, "ink", [(AX + AW, ky + 101), (300, ky + 101), (300, 598), (985, 598),
                                (985, 296), (CX + CW + 2, 296)], C["ink"], 1.3))
    o.append(text(560, 592, "n x n_kv_heads rows per run of n tokens, into the plane", 8.5,
                  "middle", fill=C["ink"], weight=600))

    # ---- worked example --------------------------------------------------
    o.append(line(20, 606, 980, 606, C["line"]))
    o.append(text(20, 624, "Worked example: one shared save_k window, 3 workers "
                  "(main + 2 helpers), 41 items at page 7; units [0,16) [16,32) [32,41)", 11.5,
                  weight=700))
    strip, xe, spans = item_strip(130, 650)
    o.append(strip)
    o.append(text(122, 662, "items", 10, "end", True, fill=C["muted"]))
    for u, (x0, x1) in zip(UNITS_EXAMPLE, spans):
        mx = (x0 + x1) / 2
        o.append(text(mx, 644, f"page {u['page']}, offsets {u['offsets']} "
                      f"(block {u['block']})", 9, "middle", fill=C["muted"]))
        o.append(text(x0, 678, f"item {u['begin']}", 8.5, "start", fill=C["muted"]))
        o.append(text(x1, 678, f"{u['end'] - 1}", 8.5, "end", fill=C["muted"]))
        o.append(text(mx, 694, f"unit {u['u']}: {u['kind']}", 9.5, "middle", fill=C["vnni"],
                      weight=700))
    o.append(text(20, 732, "unit_start", 10, "start", True, fill=C["unit"], weight=700))
    tbl, te = unit_table(110, 718)
    o.append(tbl)
    o.append(text(te + 12, 732, "n_units = 3; entries 0 .. 3 used of max_minibatch_size + 1",
                  9.5))
    o.append(cite(980, 732, "model.hpp:3183, 3189-3190"))
    o.append(text(20, 772, "at the open", 10, fill=C["muted"]))
    ctr, ce = window_counters(110, 752, [("next_unit", "0", C["ink"]),
                                         ("finished", "0", C["ink"]),
                                         ("opened", "W - 1 -> W", C["ink"]),
                                         ("helper_windows[1]", "W", C["ink"]),
                                         ("helper_windows[2]", "W", C["ink"])],
                              w=104)
    o.append(ctr)
    o.append(text(ce + 12, 766, "W = the W-th shared save_k of the pass,", 9))
    o.append(text(ce + 12, 778, "the same number on both sides", 9))
    o.append(cite(980, 788, "model.hpp:3331-3335"))

    cap = ("B1, data model. The left column is what save_k reads: the batch (one minibatch) "
           "with its items, the K buffer ks (one native row per token and KV head, orange), "
           "and the state members of model.hpp with the new constants. The middle column is "
           "batch::k_store_window_t, the window the PR adds in common.hpp, and the present "
           "mask one block save carries. The right column is the page with its four blocks, "
           "its three store entry points (set_k_block is new), the slot, and the work unit, "
           "a run of consecutive items in one 16-token block. Every arrow says how many. The "
           "band at the bottom is the worked example: 41 items cut into three units, and the "
           "counters at the open of window W.")
    legend = [
        ("ctx_ink", "grey fill, ink outline: the two groups of what save_k reads, batch "
                    "(one minibatch) and state (model.hpp)"),
        ("ctx", "grey fill, light grey outline: the note under k_store_window_t (the "
                "threads of a shared window and how n_workers and n_helpers relate)"),
        ("box", "white box, ink outline: a data-model entity or a field: the fields of "
                "batch and state, ks[ix] and row_of, k_store_window_t and its seven "
                "fields, the present mask, the page with its four blocks, set_k_block, "
                "set_k_row, k(...).set, the slot, and the five counters at the open; the "
                "name in bold monospace, the description in sans-serif"),
        ("rm", "orange: ks, the K buffer of roped K rows, one native row per (token, KV "
               "head) in dimension order"),
        ("blue box, text and arrow: kv_block::k, the VNNI K plane of one (slot, KV head, "
         "page); 1 slot -> n_kv_heads planes; the three units of the worked example, "
         "each a set_k_block store into that plane", "multi",
         ["vnni", ("arrow", C["vnni"])]),
        ("present", "green squares: the set bits of the present mask of unit 2 (0x01ff: "
                    "lanes 0..8 = offsets 32..40)"),
        ("grey-blue (box, text and arrow): the work units: work unit u, the 41 item "
         "cells and the entries 0 .. 3 of unit_start, the unit_start row label, and "
         "the arrows unit_start -> the units (n_units <= n_items), unit -> at most 16 "
         "offsets of one block", "multi", ["unit", ("arrow", C["unit"])]),
        ("empty", "grey dashed: the unused tail of unit_start (the entries after "
                  "n_units = 3) and the clear lanes 9..15 of the present mask"),
        ("arrow", "ink arrow: a containment or a reference with its how-many: item -> "
                  "token_id -> page + offset, batch -> its window, ks[ix] -> n_kv_heads "
                  "K rows, ks -> the page's store entry points, present -> set_k_block"),
        ("font_mono", "monospace = a name or a value from the code: box titles, field "
                      "names, ks[ix], the unit_start entries and the counters at the open"),
        ("font_sans", "sans-serif = the description under a name, the how-many labels, "
                      "the worked example's prose; grey sans-serif = a note or a "
                      "secondary label"),
        ("font_cite", "small grey monospace = the line or Note that defines a box or a "
                      "field (file:line)"),
        ("font_tag", "bold 'new' = a struct, a field or a constant this PR adds: "
                     "k_store_window, k_store_window_t, k_store_block, k_scatter_run_len, "
                     "k_join_clock_spins, set_k_block"),
    ]
    return figure(fid, W, H, "Data model of save_k: batch, window, page, work unit",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B2: function model ----------------------------------------------------
def b2():
    fid = "model-b2"
    W, H = 1000, 600
    o = [marker_defs(fid, {"ink": C["ink"]})]
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

    R = [44 + 68 * i for i in range(8)]
    mid = [y + CH / 2 for y in R]

    # column 1
    o.append(caller(X1, 44, W1, 64, ["generated run() [main]:", "K channel wait per item,",
                                     "then save_k(ks, 0, n_workers)"],
                    "TronCpp.hs:2996-3004", "generated run() calls save_k(..., 0, n_workers)"))
    o.append(caller(X1, 120, W1, 64, ["generated run_main_help", "[main helper i, worker_ix 1 + i]:",
                                      "save_k(ks, worker_ix, n_workers)"],
                    "TronCpp.hs:1364; 2935-2942",
                    "run_main_help (generated): save_k(..., worker_ix, n_workers)"))
    o.append(caller(X1, 196, W1, 64, ["handwritten plugin and tests:", "save_k with the defaults",
                                      "(worker_ix 0, n_workers 1)"],
                    "llama.hpp:1038; t_llama_unit.cpp:4035",
                    "save_k with the defaults (handwritten plugin, tests)",
                    reg="t_llama_unit.cpp:4035 (a call with the defaults); model.hpp:3099-3101; h/tron/plugins/llama.hpp:1038"))
    o.append(caller(X1, 272, W1, 64, ["test 'three threads' [main +", "2 std::thread helpers]:",
                                      "save_k(..., worker_ix, 3)"],
                    "t_llama_unit.cpp:4040-4061",
                    "save_k calls of the test 'three threads' (worker_ix 0..2, n_workers 3)"))

    # column 2
    SY, IY = 100, 220    # save_k, save_k_impl
    o.append(cell(X2, SY, "save_k (two overloads)",
                  ["Store the K rows of the minibatch. The",
                   "defaults keep the store on the caller."],
                  "model.hpp:3395, 3406", "changed", "save_k (two overloads)",
                  "model.hpp:3388-3413", h=64))
    o.append(cell(X2, IY, "save_k_impl",
                  ["Every worker of the store calls this:",
                   "worker 0 is main, the others are helpers."],
                  "model.hpp:3295-3305", "changed", "save_k_impl", "model.hpp:3295-3386",
                  h=64))

    # column 3
    o.append(cell(X3, R[0], "k_store_shared",
                  ["Whether the K store of this minibatch",
                   "is shared with the helpers."],
                  "model.hpp:3150-3153", "new", "k_store_shared", "model.hpp:3150-3161"))
    o.append(cell(X3, R[1], "k_store_cut_units",
                  ["Cut the minibatch's items into the work",
                   "units. Main only, before the open."],
                  "model.hpp:3163-3165", "new", "k_store_cut_units", "model.hpp:3163-3191"))
    o.append(cell(X3, R[2], "store_k_block",
                  ["Store the K rows (every KV head) of",
                   "items[task_begin, task_end) into slot."],
                  "model.hpp:3193-3201", "new (per unit)", "store_k_block",
                  "model.hpp:3193-3293; row_of at 3207-3210"))
    o.append(cell(X3, R[4], "operation_is_hardware_candidate",
                  ["has_hardware_slot: hardware geometry and this;",
                   "only then the GOF credit (credit_gof_save)"],
                  "model.hpp:1489; 3320-3322", "unchanged",
                  "operation_is_hardware_candidate (has_hardware_slot)",
                  "model.hpp:1489 (definition); 3320-3322 (has_hardware_slot); "
                  "3379-3380 (the credit runs only then)", fill=MAIN_FILL, size=10.5))
    o.append(cell(X3, R[5], "mark_k_complete, credit_gof_save",
                  ["[main] after the join: mark per token, then",
                   "credit_gof_save and the latch count_down"],
                  "model.hpp:3369-3385", "unchanged",
                  "mark_k_complete, credit_gof_save, upstream_kvs_ready.count_down "
                  "(and log_intermediate 'WK roped' before them)",
                  "model.hpp:3369-3385 (the marks loop at head); kv_cache.hpp:2236; "
                  "model.hpp:3480 (credit_gof_save)", fill=MAIN_FILL, size=10.5))

    # column 4
    o.append(cell(X4, R[0], "k_vnni::layout_on",
                  ["the layout gate: true for 128-dimension",
                   "heads when TRON_K_VNNI is defined"],
                  "tensor/k_vnni.hpp:94-103", "unchanged", "k_vnni::layout_on",
                  "tensor/k_vnni.hpp:94-103 (PR 4956)", fill=MAIN_FILL))
    o.append(cell(X4, R[1], "page_of, offset_in_page",
                  ["which page holds the token and its offset",
                   "j in the page; block c = j / k_store_block"],
                  "model.hpp:1771; kv_cache.hpp:1972", "unchanged", "page_of, offset_in_page",
                  "model.hpp:1771; kv_cache.hpp:1972", fill=MAIN_FILL))
    o.append(cell(X4, R[2], "set_k_block -> store_block",
                  ["rows of up to 16 tokens of one block, stored",
                   "at once: a register transpose, whole lines"],
                  "kv_cache.hpp:2089", "new (2..16 tokens)",
                  "set_k_block -> store_block",
                  "kv_cache.hpp:2078-2096; tensor/k_vnni.hpp:326-368", size=11))
    o.append(cell(X4, R[3], "set_k_row -> store_row",
                  ["one token's row into the plane: 4 scatters,",
                   "4 bytes into each of its 64 lines (PR 4956)"],
                  "kv_cache.hpp:2065", "unchanged (1 token)",
                  "set_k_row -> store_row",
                  "kv_cache.hpp:2061-2076; tensor/k_vnni.hpp:290-310", fill=MAIN_FILL, size=11))
    o.append(cell(X4, R[4], "page::k(slot, kv_head, j).set",
                  ["row-major slots only (requires",
                   "!k_vnni::layout_on): one row store"],
                  "kv_cache.hpp:2015", "unchanged (row-major)", "page::k(slot, kv_head, j).set",
                  "kv_cache.hpp:2015-2029", fill=MAIN_FILL, size=11))
    o.append(cell(X4, R[5], "upstream_kvs_ready.count_down",
                  ["the downstream minibatches' latch: the",
                   "attention of the next minibatch may start"],
                  "model.hpp:3384-3385", "unchanged",
                  "upstream_kvs_ready[slot].count_down()",
                  "common.hpp:1188; model.hpp:3383-3385; self_attention.hpp:823 (the wait)",
                  fill=MAIN_FILL, size=10.5))

    # ---- arrows ----------------------------------------------------------
    ink = C["ink"]
    o.append(line(212, 76, 212, 304, ink, 1.3))
    for yy in (76, 152, 228, 304):
        o.append(line(X1 + W1, yy, 212, yy, ink, 1.3))
    o.append(arrow(fid, "ink", [(212, SY + 32), (X2 - 2, SY + 32)], ink, 1.3))
    o.append(arrow(fid, "ink", [(337, SY + 64), (337, IY - 2)], ink, 1.3))
    o.append(text(343, SY + 100, "+ worker_ix, n_workers", 8.5, fill=C["muted"]))
    # save_k_impl -> column 3 (a bus at x = 465)
    o.append(line(X2 + W2, IY + 32, 465, IY + 32, ink, 1.3))
    o.append(line(465, mid[0], 465, mid[5], ink, 1.3))
    for yy in (mid[0], mid[1], mid[2], mid[4], mid[5]):
        o.append(arrow(fid, "ink", [(465, yy), (X3 - 2, yy)], ink, 1.3))
    # column 3 -> column 4 (store_k_block's callees: a bus at x = 730)
    o.append(arrow(fid, "ink", [(X3 + W3, mid[0]), (X4 - 2, mid[0])], ink, 1.3))
    o.append(arrow(fid, "ink", [(X3 + W3, mid[1]), (X4 - 2, mid[1])], ink, 1.3))
    o.append(line(X3 + W3, mid[2], 730, mid[2], ink, 1.3))
    o.append(line(730, mid[2], 730, mid[4], ink, 1.3))
    for yy in (mid[2], mid[3], mid[4]):
        o.append(arrow(fid, "ink", [(730, yy), (X4 - 2, yy)], ink, 1.3))
    o.append(arrow(fid, "ink", [(X3 + W3, mid[5]), (X4 - 2, mid[5])], ink, 1.3))
    # legend
    o.append(lines(20, 380, ["tags: new = added by this PR,",
                             "changed = signature or body changed,",
                             "unchanged = context (grey cell)."], 9.5, 13, fill=C["muted"]))
    o.append(text(20, 426, "[...] = the thread that runs it.", 9.5, fill=C["muted"]))
    o.append(lines(20, 446, ["Arrows = calls, in column order:",
                             "caller -> entry point -> helper",
                             "-> page / k_vnni.hpp function."], 9.5, 13, fill=C["muted"]))
    o.append(lines(20, 492, ["Constants of the store (k_store_block,",
                             "k_scatter_run_len, k_join_clock_spins,",
                             "k_join_timeout_s) are in B1."], 9.5, 13, fill=C["muted"]))
    o.append(lines(X2, 420, ["Not in this PR: no row bits, no deferred",
                             "conversion (they land in PR 4959)."], 9.5, 13, fill=C["muted"]))

    cap = ("B2, function model. Each cell is one function with a one-line description "
           "from its comment and the line that defines it. The two save_k overloads take "
           "a worker index and a worker count from the generated run() and run_main_help "
           "and forward them to save_k_impl. save_k_impl decides the sharing "
           "(k_store_shared) and cuts the units (k_store_cut_units, main only). "
           "store_k_block runs on any thread of the window and chooses the page's store "
           "entry point per run: set_k_block for 2 to 16 tokens, set_k_row for one token, "
           "page::k(...).set for a row-major slot. After every store, main marks the "
           "tokens, credits the GOFs and counts the downstream latches down.")
    legend = [
        ("box", "white cell, ink outline: a function this PR adds or changes: the entry "
                "points save_k and save_k_impl; the helpers k_store_shared, "
                "k_store_cut_units, store_k_block; the page function set_k_block and "
                "store_block of k_vnni.hpp; the name in bold monospace, the description "
                "in sans-serif"),
        ("ctx_ink", "grey cell, ink outline: an unchanged function the store calls: "
                    "k_vnni::layout_on, page_of / offset_in_page, set_k_row -> store_row, "
                    "page::k(...).set, operation_is_hardware_candidate, mark_k_complete / "
                    "credit_gof_save, upstream_kvs_ready.count_down"),
        ("ctx", "grey box, light grey outline: a caller in another file (the generated "
                "run() and run_main_help in TronCpp.hs, the handwritten plugin and the "
                "tests, the three-thread test) with its call line and the thread in "
                "brackets"),
        ("arrow", "ink arrow: a call, in column order: caller -> entry point -> helper "
                  "-> page / k_vnni.hpp function; its label says how often and on which "
                  "thread, or which run length takes it"),
        ("font_mono", "monospace = a function name"),
        ("font_sans", "sans-serif = the one-line description of a function, the callers' "
                      "lines, the arrow labels and the key at the left; grey sans-serif = "
                      "a note"),
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
    W, H = 1000, 790
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"]})]
    boxes = []
    MX, MW = 20, 310     # main lane
    KX, KW = 380, 220    # the window counters
    HX, HW = 650, 330    # helper lane

    o.append(rect(MX, 14, MW, 24, C["soft"], C["line"], 1, 4))
    o.append(text(MX + MW / 2, 30, "[main, worker_ix 0]", 11, "middle", weight=700))
    o.append(rect(KX, 14, KW, 24, C["soft"], C["line"], 1, 4))
    o.append(text(KX + KW / 2, 30, "batch::k_store_window", 11, "middle", True, weight=700))
    o.append(rect(HX, 14, HW, 24, C["soft"], C["line"], 1, 4))
    o.append(text(HX + HW / 2, 30, "[helper, worker_ix 1 .. n_workers - 1]", 11, "middle",
                  weight=700))
    boxes.append(("batch::k_store_window", "common.hpp:1193-1219"))

    def M(y, h, title, sub, ref, num, label, dash=None, crit=False):
        boxes.append((label, ref))
        return step_box(MX, y, MW, h, title, sub, ref, dash=dash, num=num,
                        sw=CRIT_SW if crit else None)

    def Hh(y, h, title, sub, ref, num, label, dash=None):
        boxes.append((label, ref))
        return step_box(HX, y, HW, h, title, sub, ref, dash=dash, num=num)

    o.append(M(46, 58, "run() [generated]", ["K channel wait per item (startReadingAll),",
                                             "then save_k(ks, 0, n_workers)"],
               "TronCpp.hs:2996-3004", 0, "save_k(ks, 0, n_workers) [step 0 main: generated run()]"))
    o.append(M(114, 82, "is_main, shared",
               ["TRON_ASSERT(worker_ix < n_workers)",
                "is_main = worker_ix == 0; shared = k_store_shared(...)",
                "not shared: store_k_block(items[0, n_items)) on main",
                "alone, then step 6"],
               "model.hpp:3310-3315; 3366-3368", 1,
               "is_main, shared [step 1 main: the decision; unshared store]"))
    o.append(M(206, 70, "open the window",
               ["k_store_cut_units -> unit_start {0, 16, 32, 41}, n_units 3",
                "next_unit.store(0, relaxed); finished.store(0, relaxed)",
                "opened.fetch_add(1, release)"],
               "model.hpp:3329-3333", 2, "k_store_cut_units, opened.fetch_add [step 2 main: open the window]", crit=True))
    o.append(M(302, 94, "claim loop",
               ["u = next_unit.fetch_add(1, acq_rel); u >= n_units: break",
                "store_k_block(items[unit_start[u], unit_start[u + 1]))",
                "example: main takes u = 0 (page 7 block 0: set_k_block, 0xffff);",
                "its next claim returns u >= 3, main leaves the loop"],
               "model.hpp:3340-3346", 3, "next_unit.fetch_add, store_k_block [step 3 main: the claim loop]"))
    o.append(M(410, 94, "join (waits)",
               ["while (finished.load(acquire) < n_helpers (2)) _mm_pause()",
                "watchdog: a clock read every k_join_clock_spins (2^20) loops;",
                "t0 = the first read; TRON_ASSERT(now - t0 < 120 s), message:",
                "finished of n_helpers, claimed of n_units"],
               "model.hpp:3351-3365", 5, "finished.load, k_join_clock_spins [step 5 main: the join and its watchdog]",
               dash="5 3", crit=True))
    o.append(text(MX + 50 + _w("join (waits)", 10.5, True) * 1.08 + 10, 425,
                  "(step 4 is on the helper lane)", 8.5, fill=C["muted"]))
    o.append(M(518, 82, "mark_k_complete, credit_gof_save",
               ["the per-token completion marks and GOF credits, in",
                "q_batch->items order: log 'WK roped', mark_k_complete(slot,",
                "j), credit_gof_save (hardware geometry, has_hardware_slot);",
                "the per-token K store that sat here before is gone (M6)"],
               "model.hpp:3369-3382", 6, "mark_k_complete, credit_gof_save [step 6 main: "
               "the per-token completion marks and GOF credits]", crit=True))
    o.append(M(614, 56, "ping downstream",
               ["for each downstream minibatch:",
                "upstream_kvs_ready[slot].count_down()"],
               "model.hpp:3383-3385", 7, "upstream_kvs_ready[slot].count_down [step 7 main: the downstream latches]", crit=True))

    o.append(Hh(46, 58, "run_main_help [generated]",
                ["save_k(ks, worker_ix, n_workers) at the same",
                 "statement position as main's call"],
                "TronCpp.hs:2935-2942", 0,
                "save_k(ks, worker_ix, n_workers) [step 0 helper: generated run_main_help]"))
    o.append(Hh(114, 82, "is_main, shared",
                ["TRON_ASSERT(worker_ix < n_workers); is_main = false",
                 "shared = k_store_shared (the same answer as main's)",
                 "if (!is_main && !shared) return: an unshared",
                 "store is main's alone"],
                "model.hpp:3310-3315", 1, "is_main, shared [step 1 helper: the decision, early return]"))
    o.append(Hh(206, 70, "wait for the window (waits)",
                ["my_window = ++helper_windows[worker_ix]",
                 "while (opened.load(acquire) < my_window) _mm_pause()",
                 "window W of the pass = the W-th shared save_k on both sides"],
                "model.hpp:3334-3339", 2, "helper_windows, opened.load [step 2 helper: wait for window W]", dash="5 3"))
    o.append(Hh(302, 94, "claim loop (the same loop)",
                ["u = next_unit.fetch_add(1, acq_rel); u >= n_units: break",
                 "store_k_block(items[unit_start[u], unit_start[u + 1]))",
                 "example: helper 1 takes u = 1 (page 7 block 1: set_k_block, 0xffff),",
                 "helper 2 takes u = 2 (page 7 offsets 32..40: set_k_block, 0x01ff)"],
                "model.hpp:3340-3346", 3, "next_unit.fetch_add, store_k_block [step 3 helper: the claim loop]"))
    o.append(Hh(410, 46, "finished.fetch_add(1, release); return",
                ["the helper leaves the window"],
                "model.hpp:3347-3350", 4, "finished.fetch_add(1, release) [step 4 helper: "
                "leaves the window and returns]"))
    o.append(Hh(470, 58, "back in run_main_help (idle)",
                ["the helper's next kernel waits for the",
                 "attention output"],
                "model.hpp:3092-3094", None, "helper after step 4: idle until the attention output",
                dash="5 3"))

    def K(y, h, title, sub, ref, label, stroke=C["ink"]):
        boxes.append((label, ref))
        out = [rect(KX, y, KW, h, "#fff", stroke, 1.2, 4)]
        out.append(text(KX + 8, y + 15, title, 10.5, mono=True, weight=600))
        out.append(lines(KX + 8, y + 29, sub, 9, 11.5))
        out.append(cite(KX + KW - 4, y + h - 4, ref))
        return "".join(out)

    o.append(K(150, 60, "helper_windows[1], [2]",
               ["W - 1 -> W: a plain ++ (not atomic),", "the helper's own slot"],
               "common.hpp:1218; model.hpp:3335", "helper_windows[worker_ix]"))
    o.append(K(216, 60, "unit_start, n_units",
               ["{0, 16, 32, 41}, 3: written by main", "before the open (release on opened)"],
               "common.hpp:1206, 1215", "unit_start, n_units (counters column)"))
    o.append(K(282, 46, "opened", ["W - 1 -> W (release); read with acquire"],
               "common.hpp:1204", "opened (counters column)"))
    o.append(K(334, 60, "next_unit", ["0 -> 1 -> 2 -> 3 (one unit per claim),",
                                      "then 3 failing claims -> 6"],
               "common.hpp:1202; model.hpp:3342-3343", "next_unit (counters column)",
               stroke=C["unit"]))
    o.append(K(420, 46, "finished", ["0 -> 1 -> 2 = n_helpers (n_workers - 1)"],
               "common.hpp:1205; model.hpp:3328, 3348, 3353", "finished (counters column)"))
    o.append(rect(KX, 580, KW, 72, C["soft"], C["line"], 1, 4))
    o.append(lines(KX + 8, 596, ["after the join: every unit is stored,",
                                 "no helper is inside this window, the",
                                 "counters are main's to reset; every row",
                                 "store happens-before the latch count_down"],
                   9, 11.5))
    boxes.append(("after the join (four things hold)", "model.hpp:3121-3126"))
    o.append(cite(KX + KW - 4, 648, "model.hpp:3121-3126"))

    ink = C["ink"]
    o.append(arrow(fid, "ink", [(HX, 232), (KX + KW + 2, 180)], ink, 1.2))
    o.append(text(640, 200, "++", 9, "middle", fill=ink, weight=700))
    o.append(arrow(fid, "ink", [(MX + MW, 234), (KX - 2, 246)], ink, 1.2))
    o.append(text(352, 228, "write", 8.5, "middle", fill=ink, weight=700))
    o.append(arrow(fid, "ink", [(MX + MW, 262), (KX - 2, 305)], ink, 1.2))
    o.append(text(360, 264, "release", 8.5, "middle", fill=ink, weight=700))
    o.append(arrow(fid, "ink", [(KX + KW, 305), (HX - 2, 245)], ink, 1.2))
    o.append(text(HX - 4, 240, "acquire", 8.5, "end", fill=ink, weight=700))
    o.append(arrow(fid, "unit", [(MX + MW, 332), (KX - 2, 364)], C["unit"], 1.3))
    o.append(text(KX - 2, 330, "fetch_add", 8.5, "end", fill=C["unit"], weight=700))
    o.append(text(KX - 2, 378, "acq_rel", 8.5, "end", fill=C["unit"], weight=700))
    o.append(arrow(fid, "unit", [(HX, 332), (KX + KW + 2, 364)], C["unit"], 1.3))
    o.append(text(KX + KW + 2, 330, "fetch_add", 8.5, "start", fill=C["unit"], weight=700))
    o.append(text(KX + KW + 2, 378, "acq_rel", 8.5, "start", fill=C["unit"], weight=700))
    o.append(arrow(fid, "ink", [(HX, 438), (KX + KW + 2, 443)], ink, 1.2))
    o.append(text(625, 430, "release", 8.5, "middle", fill=ink, weight=700))
    o.append(arrow(fid, "ink", [(KX, 443), (MX + MW + 2, 440)], ink, 1.2))
    o.append(text(355, 431, "acquire", 8.5, "middle", fill=ink, weight=700))
    for y0, y1 in ((104, 112), (196, 204), (276, 300), (396, 408), (504, 516), (600, 612)):
        o.append(line(MX + 26, y0, MX + 26, y1, C["muted"], 1))
    for y0, y1 in ((104, 112), (196, 204), (276, 300), (396, 408), (456, 468)):
        o.append(line(HX + 26, y0, HX + 26, y1, C["muted"], 1))
    o.append(lines(380, 676, ["thick red frame = main's serial part (the critical path of B4);",
                              "dashed = a thread waits (spin with _mm_pause);",
                              "grey-blue = the claim counter and the units (work units).",
                              "",
                              "The example's claim order (main 0, helper 1 takes 1,",
                              "helper 2 takes 2) is one possible order: fetch_add",
                              "assigns each unit index once, to whichever thread",
                              "claims first (model.hpp:3118-3120)."], 9, 12, fill=C["muted"]))

    cap = ("B3, sequencing model: the steps of one shared save_k window, top to bottom, "
           "for the main thread (left) and one helper (right), with the window counters "
           "between them. Each arrow names its memory order: main publishes the unit table "
           "with a release on opened, a helper reads it with an acquire, every thread claims "
           "units with fetch_add (acq_rel), a helper leaves with a release on finished, and "
           "main's join reads finished with acquire. The worked example (41 items, 3 units, "
           "3 workers) fills in the counters: the two whole blocks and the partial block 2 "
           "of page 7 are all stored by set_k_block. After the join main marks the tokens; "
           "no row store sits in that loop any more.")
    legend = [
        ("box", "white box, ink outline: a step that runs without waiting (main steps 0, "
                "1, 2, 3, 6, 7; helper steps 0, 1, 3, 4) and the window counters "
                "helper_windows, unit_start / n_units, opened, finished; the title in "
                "bold monospace, the code lines under it"),
        ("ctx", "grey fill, light grey outline: the three lane headers (main, the window, "
                "the helpers) and the note after the join"),
        ("solid ink badge: the step number ('step 0' .. 'step 7') at the top left of a "
         "step, in white text", C["ink"], C["ink"], False, False),
        ("idle", "dashed ink outline: a step that waits (spin with _mm_pause): main's "
                 "join (step 5), the helper's wait for the window (step 2) and the "
                 "helper idle in run_main_help after step 4"),
        ("crit", "thick solid red frame: main's serial part, the critical path of B4: "
                 "open the window (step 2), join (5), mark_k_complete / credit_gof_save "
                 "(6), ping downstream (7)"),
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
                      "lane headers, the memory-order labels and the notes; grey "
                      "sans-serif = a note"),
        ("font_cite", "small grey monospace = the lines that define a step or a counter "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Sequencing model of one shared save_k window", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- B4: interaction model (wall-clock lanes) ------------------------------
def b4():
    fid = "model-b4"
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    red = C["crit"]
    soft, lin = C["soft"], C["muted"]
    LANE_H, GAP = 58, 6
    W = 1000
    # lane 0: the base (before PR 4958), in the before style (red, dashed,
    # the word "before"): the one measured cost sits on its slice
    OY = 60
    o.append(rect(20, OY, 960, LANE_H, "#fff", red, 1, 3, "5 3"))
    o.append(text(28, OY + LANE_H / 2, "[main, before]", 11, weight=700, fill=red))
    o.append(text(28, OY + LANE_H / 2 + 13, "the base: helpers idle", 9.5,
                  fill=C["muted"]))
    o.append(cite(28, OY + 54, "base model.hpp:3088-3124", anchor="start"))
    boxes.append(("[main, before] (the base: the whole K store on main, one scatter per "
                  "token)", "model.hpp:3077-3086 (the measurement and 'the main thread's "
                  "largest serial piece of work'); base model.hpp:3088-3124 (the store "
                  "inside the marks loop, removed before head 3376)"))
    labels = [("[main]", "worker_ix 0"), ("[main helper 1]", "worker_ix 1"),
              ("[main helper 2]", "worker_ix 2"),
              ("[attention workers]", "the last pool workers")]
    grid, ys, tx0 = lanes_grid(20, OY + LANE_H + GAP, 960, labels, lane_h=LANE_H, gap=GAP)
    o.append(grid)
    boxes.append(("[main]", "model.hpp:3095-3097 (worker_ix 0 is main)"))
    boxes.append(("[main helper 1], [main helper 2]",
                  "model.hpp:3095-3097; TronCpp.hs:1362-1364 (run_main_help(q_batches, 1 + i, "
                  "n_workers))"))
    boxes.append(("[attention workers]", "model.hpp:2329-2336 (Note [Attention workers are "
                  "the last pool workers]); 3085"))
    for i, ref in enumerate(["model.hpp:3329-3385", "model.hpp:3334-3350",
                             "model.hpp:3334-3350", "model.hpp:3085; 2329"]):
        o.append(cite(28, ys[i] + 54, ref, anchor="start"))
    lane_end = ys[3] + LANE_H
    T0, TS, T1 = 170, 645, 970
    o.append(text(T0, 50, "layer L of the pass: around one save_k (one of many layers)", 10,
                  weight=700))
    o.append(cite(T0, 36, "model.hpp:3077-3078; 3129-3133", anchor="start"))
    o.append(line(TS, 30, TS, lane_end + 8, C["muted"], 1, "4 3"))
    o.append(text(TS + 10, 50, "the forward end (after the last layer)", 10, weight=700))
    o.append(cite(TS + 10, 36, "model.hpp:1836-1851", anchor="start"))
    AXY = lane_end + 16
    o.append(arrow(fid, "ink", [(T0, AXY), (T1, AXY)], C["ink"], 1.2))
    o.append(text(T0, AXY + 14, "wall-clock time ->  (durations schematic, not to scale; "
                  "the order and the overlap are the point)", 9, fill=C["muted"]))

    def wb(lane_i, x0, x1, label, fill, stroke, ref, boxname, idle=False, crit=False,
           size=8.5):
        y = ys[lane_i] + 6
        h = 36
        svg = work_block(x0, y, x1 - x0, h, label, fill, stroke, idle=idle, size=size)
        if crit:
            svg += crit_frame(x0, y, x1 - x0, h)
        boxes.append((boxname, ref))
        return svg

    # --- the base (before) ---
    oy = OY + 6
    o.append(work_block(170, oy, 60, 36, "rope kernel", soft, lin, size=8.5))
    o.append(work_block(230, oy, 70, 36, "K channel wait", "#fff", C["ink"], idle=True, size=8.5))
    o.append(rect(300, oy, 280, 36, soft, red, 1.2, 2, "5 3"))
    o.append(text(440, oy + 14, "save_k: one scatter per token, on main alone (before)",
                  8.5, "middle", fill=red, weight=700))
    o.append(text(440, oy + 27, "0.86 ms per layer (measured 2026-09-14): the critical path",
                  8.5, "middle", fill=red))
    o.append(work_block(580, oy, 60, 36, "save_v, ...", soft, lin))
    o.append(text(650, oy + 22, "run() joins, wait_for_coop_gof, logits (unchanged)", 9,
                  fill=C["muted"]))
    boxes.append(("save_k: one set_k_row scatter per token on main alone (before, removed): "
                  "0.86 ms per layer", "model.hpp:3077-3086 (the measurement: 0.86 ms per "
                  "layer, 105 ns per (token, KV head) row, 2026-09-14 on delphi-3bda); base "
                  "model.hpp:3096-3116 (the per-token store inside the marks loop)"))
    # --- main lane ---
    o.append(wb(0, 170, 230, "rope kernel", soft, lin, "model.hpp:3132-3133",
                "main: K/Q rope kernel (before the K channel wait)"))
    o.append(wb(0, 230, 300, "K channel wait", "#fff", C["ink"],
                "TronCpp.hs:2997; model.hpp:3129-3131",
                "startReadingAll [main: the K channel wait per item, before save_k]", idle=True))
    o.append(text(265, ys[0] + 52, "startReadingAll", 8.5, "middle", fill=C["muted"]))
    o.append(wb(0, 300, 338, "open", "#fff", C["ink"], "model.hpp:3329-3333",
                "k_store_cut_units, opened.fetch_add [main: open (cut units, reset the counters, opened++)]", crit=True))
    o.append(wb(0, 338, 452, "claim + store units", C["unit_fill"], C["unit"],
                "model.hpp:3340-3346", "next_unit.fetch_add, store_k_block [main: claim + store units]"))
    o.append(wb(0, 452, 490, "join", "#fff", C["ink"], "model.hpp:3351-3365",
                "finished.load, k_join_clock_spins [main: join (spin, watchdog)]", idle=True, crit=True))
    o.append(wb(0, 490, 580, "marks + latches", "#fff", C["ink"],
                "model.hpp:3369-3385", "mark_k_complete, credit_gof_save, count_down [main: after the join]",
                crit=True))
    o.append(wb(0, 580, 640, "save_v, ...", soft, lin,
                "TronCpp.hs:3005-3009", "save_v [main: the rest of the schedule]"))
    # --- helpers ---
    for i in (1, 2):
        o.append(wb(i, 170, 300, "rope kernel", soft, lin,
                    "model.hpp:3132-3133", f"helper {i}: K/Q rope kernel (nothing blocks after it)"))
        o.append(wb(i, 300, 338, "wait", "#fff", C["ink"], "model.hpp:3334-3339",
                    f"helper {i}: wait for opened >= my_window", idle=True))
        o.append(wb(i, 338, 452, "claim + store units", C["unit_fill"], C["unit"],
                    "model.hpp:3340-3346", f"next_unit.fetch_add, store_k_block [helper {i}: claim + store units]"))
        o.append(wb(i, 452, 504, "", C["soft"], C["ink"], "model.hpp:3347-3350",
                    f"finished.fetch_add(1, release) [helper {i}: leaves the window]"))
        o.append(text(478, ys[i] + 20, "finished.", 8.5, "middle", mono=True))
        o.append(text(478, ys[i] + 31, "fetch_add", 8.5, "middle", mono=True))
        o.append(wb(i, 504, 640, "idle until the attention output", "#fff", C["ink"],
                    "model.hpp:3092-3094", f"helper {i}: idle (the next kernel waits for the "
                    "attention output)", idle=True))
    # --- attention workers ---
    o.append(wb(3, 170, 570, "pending section waits behind save_k (latch count_down); idle: "
                "help_drain_gof", "#fff", C["ink"],
                "model.hpp:3085; 3384-3385; self_attention.hpp:823, 760",
                "attention workers: the pending section waits behind save_k; idle workers "
                "help_drain_gof", idle=True))
    o.append(wb(3, 570, 640, "attention plan", C["q_fill"], C["q"],
                "model.hpp:2329-2336", "attention workers: the per-layer attention plan"))
    # --- forward end ---
    o.append(wb(0, 650, 706, "run() joins", "#fff", C["ink"], "model.hpp:1836-1838",
                "main, forward end: run() joins the helpers and the attention workers",
                idle=True))
    o.append(wb(0, 706, 800, "wait_for_coop_gof", soft, lin, "model.hpp:1838; 3513",
                "wait_for_coop_gof [main, forward end: drains the GOF tail backlog]"))
    o.append(text(753, ys[0] + 52, "drains the GOF tail", 8.5, "middle", fill=C["muted"]))
    o.append(wb(0, 800, 970, "logits (unchanged forward end)", soft, lin, "model.hpp:1840-1851",
                "Launch logit delivery (comment) [main, forward end]"))
    for i in (1, 2):
        o.append(wb(i, 650, 680, "exit", soft, lin, "TronCpp.hs:1364-1365",
                    f"helper {i}, forward end: exit (workers_done.count_down())"))
    o.append(wb(3, 650, 680, "exit", soft, lin, "model.hpp:3513-3520",
                "attention workers, forward end: exit; the GOF tail backlog is main's, in "
                "wait_for_coop_gof"))

    BY = AXY + 24
    o.append(line(300, BY, 580, BY, CRIT, CRIT_SW))
    ty = BY + 16
    o.append(text(170, ty, "critical path (thick red frame): main's serial part of the layer "
                  "(open, join, marks, credits, latches). Nothing changes at the forward end.",
                  9.5, fill=CRIT, weight=600))
    o.append(text(170, ty + 15, "Before the two remedies (block save, sharing) the whole K "
                  "store ran on main alone, with the VNNI K layout and the per-row scatter "
                  "store (the red dashed lane):", 9.5))
    o.append(text(170, ty + 28, "0.86 ms per layer, 105 ns per (token, KV head) row (measured "
                  "2026-09-14 on delphi-3bda: qwen3-4b, 8 users, prompt 1024, 128 tokens of each "
                  "user per pass).", 9.5))
    o.append(text(170, ty + 41, "The helpers were idle meanwhile. [model.hpp:3077-3086]", 9.5))
    o.append(text(170, ty + 56, "After the two remedies the store is split into units claimed by "
                  "main and the idle helpers (grey-blue): 80 us per layer at tp2", 9.5))
    o.append(text(170, ty + 69, "for the block save shared with the helpers, same model and settings, "
                  "2026-09-14 [PR #4958 body, Background]. The lanes are schematic:", 9.5))
    o.append(text(170, ty + 82, "the 0.86 ms and 80 us slices are not drawn to scale.", 9.5))
    boxes.append(("serial piece of work [critical path, thick red frame]",
                  "model.hpp:3077-3086 (the measurement); 3329-3333, 3351-3385 (the "
                  "serial pieces)"))
    boxes.append(("80 us per layer at tp2 (the block save shared with the helpers)",
                  "PR #4958 body, Background (traces of 2026-09-14 on the PR 4424 branch); "
                  "not a line of the code"))
    ly = ty + 97
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
    o.append(work_block(510, ly + 36, 60, 18, "", C["q_fill"], C["q"]))
    o.append(text(576, ly + 49, "= attention scores (queries)", 9.5))
    H = ly + 76

    cap = ("B4, interaction model: one lane per thread over one layer and then the forward "
           "end, with the base (before PR 4958) as the red dashed lane on top. Solid "
           "blocks are work, dashed outlines are waiting. Main waits for the K channel (the "
           "roped K rows of every token, the startReadingAll wait of the generated run()) "
           "before save_k, and may idle there. The helpers reach their save_k call "
           "with nothing blocking after their rope kernel, wait for main to open the window, "
           "claim and store units beside main, and are idle again until the attention "
           "output. The attention workers' pending sections wait behind save_k. The forward "
           "end is unchanged by this PR. Durations are schematic. The measurement quoted on "
           "the old lane (0.86 ms per layer) comes from the comment of Note [Shared block "
           "save]; the 80 us after the two remedies comes from the PR body.")
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
                "marks, credits, latches"),
        ("unit", "grey-blue: claim + store units, the work units of the window, on main "
                 "and on both helpers"),
        ("ctx_ink", "grey block, ink outline: finished.fetch_add, the helper leaving the "
                    "window"),
        ("q", "violet: the attention plan of the attention workers (attention scores, "
              "queries)"),
        ("crit", "thick solid red frame: the critical path, main's serial part (open, "
                 "join, marks + credits + latches), and the red bar under the time axis; "
                 "red text = its caption"),
        ("gone", "red dashed: [main, before], the lane of the base (removed), where "
                 "the whole K store ran on main alone; red text = its name"),
        ("grey block, red dashed outline: save_k before PR 4958 on that lane, one "
         "set_k_row scatter per token on main alone, 0.86 ms per layer; red text = that "
         "measurement", C["soft"], C["crit"], True, False),
        ("arrow", "ink arrow: the wall-clock time axis (durations schematic)"),
        ("grey dashed vertical line: the boundary between layer L and the forward end "
         "(after the last layer)", "line", C["muted"], True),
        ("font_mono", "monospace = finished.fetch_add, the statement in the helpers' "
                      "block"),
        ("font_sans", "sans-serif = the lane names, the block labels, the headers, the "
                      "caption under the axis and the key; grey sans-serif = a note"),
        ("font_cite", "small grey monospace = the lines behind a lane, a block or a "
                      "header (file:line)"),
    ]
    return figure(fid, W, H, "Threads over one layer and the forward end", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- B5: decision model ----------------------------------------------------
def b5():
    fid = "model-b5"
    W, H = 1000, 700
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"],
                           "unit": C["unit"]})]
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

    def rb(x, y, w, h, state, title, sub, ref, label, reg=None):
        boxes.append((label, reg or ref))
        return run_box(x, y, w, h, state, title, sub, ref)

    def lab(x, y, s, col=ink):
        return text(x, y, s, 9, "middle", fill=col, weight=700)

    # row 0 (y = 30): the sharing decision (the band at the top)
    o.append(rect(20, 30, 960, 118, C["soft"], C["line"], 1, 6))
    o.append(text(32, 48, "first, once per save_k call on every thread: is the store shared?",
                  10.5, weight=700))
    o.append(cite(976, 48, "model.hpp:3150-3161; 3312-3315"))
    boxes.append(("is the store shared? (k_store_shared, once per save_k call)",
                  "model.hpp:3150-3161; 3312-3315"))
    o.append(dec(32, 58, 230, 80, "k_store_shared?",
                 ["layout_on && n_workers > 1", "&& n_workers <= 128",
                  "&& items.size() > k_store_block (16)"],
                 "model.hpp:3154-3159", "k_store_shared? (the four tests)"))
    o.append(box(290, 58, 310, 80, "shared: the window",
                 ["[main] cuts the items into units, opens the window;",
                  "every thread claims units (B3); each unit is",
                  "store_k_block(items[unit_start[u], unit_start[u + 1]))"],
                 "model.hpp:3325-3346", "shared: the window (store_k_block per claimed unit)",
                 fill=C["unit_fill"], stroke=C["unit"]))
    o.append(box(630, 58, 350, 80, "not shared: main alone",
                 ["a decode step (at most 16 items), n_workers == 1",
                  "(handwritten plugins, tests), > 128 workers, or a",
                  "row-major slot: store_k_block(items[0, n_items)) on main"],
                 "model.hpp:3366-3368; 3103-3106", "not shared: main alone (store_k_block over "
                 "items[0, n_items))"))
    o.append(arrow(fid, "unit", [(262, 98), (288, 98)], C["unit"], 1.4))
    o.append(lab(275, 92, "yes", C["unit"]))
    o.append(arrow(fid, "ink", [(600, 98), (628, 98)], ink, 1.3))
    o.append(lab(614, 92, "no"))

    # row 1 (y = 180): the run, VNNI slot?, a run of one?, the two stores
    o.append(box(20, 180, 210, 84, "one run (store_k_block)",
                 ["consecutive KV items of block c of page",
                  "pg; an item without KV work is skipped;",
                  "ends at a page or block change, the same",
                  "offset twice, 16 rows, or task_end"],
                 "model.hpp:3240-3259", "store_k_block: one run (consecutive items in block c)"))
    o.append(dec(270, 180, 190, 60, "VNNI slot?",
                 ["k_vnni::layout_on<", "geometry.kv.head_size>"],
                 "model.hpp:3211", "VNNI slot? (k_vnni::layout_on)",
                 reg="model.hpp:3211; tensor/k_vnni.hpp:94-103"))
    o.append(dec(500, 180, 200, 60, "a run of one token?",
                 ["n == k_scatter_run_len (1)"],
                 "model.hpp:3260; 3140-3141", "a run of one token? (n == k_scatter_run_len)"))
    o.append(box(750, 180, 230, 76, "set_k_block per KV head",
                 ["(slot, kv_head, c, present, rows): the 16",
                  "row pointers, absent lanes null; store_block",
                  "[any thread of the window]"],
                 "model.hpp:3277-3288; kv_cache.hpp:2089", "set_k_block per KV head"))
    # row 2: row-major slot path (left), set_k_row (middle), VNNI block (right)
    o.append(box(270, 290, 190, 70, "page::k(...).set",
                 ["one row store per token and KV",
                  "head (the old loop, moved here);",
                  "never shared: [main] alone"],
                 "model.hpp:3212-3221; 3154-3155",
                 "page::k(slot, kv_head, j).set (row-major slots, never shared)"))
    o.append(rb(270, 398, 190, 56, "rm", "row-major slot",
                ["4 whole lines per token, the", "store of the row-major layout"],
                "kv_cache.hpp:2015-2029",
                "row-major slot (page::k(...).set, 4 whole lines per token)"))
    o.append(box(500, 290, 200, 70, "set_k_row per KV head",
                 ["(slot, kv_head, j, k_source_row(row));", "the per-row scatter (store_row)",
                  "[any thread of the window]"],
                 "model.hpp:3261-3275; kv_cache.hpp:2065", "set_k_row per KV head (a run of one token)"))
    o.append(rb(500, 398, 200, 56, "row", "one token: the scatter",
                ["4 scatters write 4 bytes into each", "of the token's 64 lines"],
                "tensor/k_vnni.hpp:290-310",
                "one token: the scatter (store_row: 4 scatters, 4 bytes into each of 64 lines)",
                reg="tensor/k_vnni.hpp:290-310; kv_cache.hpp:715-719 (Note item 1)"))
    o.append(dec(750, 290, 230, 60, "present == 0xffff?",
                 ["FULL_BLOCK_0XFFFF: all 16 lanes"],
                 "tensor/k_vnni.hpp:358", "present == FULL_BLOCK_0XFFFF? (store_block)",
                 reg="tensor/k_vnni.hpp:358; 76-77"))
    o.append(rb(750, 398, 110, 56, "full", "a whole block",
                ["64 full-line stores", "(16 per panel)"],
                "k_vnni.hpp:358-360",
                "a whole block (store_block, 64 full-line stores)"))
    o.append(rb(870, 398, 110, 56, "part", "a partial block",
                ["64 masked line stores", "to the present lanes"],
                "k_vnni.hpp:361-364",
                "a partial block (store_block, 64 masked line stores)",
                reg="tensor/k_vnni.hpp:361-364, 326-331"))
    # row 5: after the stores, main only
    o.append(rect(20, 490, 960, 92, C["soft"], C["line"], 1, 6))
    o.append(text(32, 508, "after every row is stored [main only], for every item of the "
                  "minibatch, in items order:", 10.5, weight=700))
    o.append(cite(976, 508, "model.hpp:3369-3385"))
    boxes.append(("after every row is stored [main only]: the marks loop",
                  "model.hpp:3369-3385, 3127-3128"))
    o.append(box(32, 520, 300, 54, "mark_k_complete(slot, j)",
                 ["log 'WK roped'; the per-token completion mark;",
                  "credit_gof_save when has_hardware_slot"],
                 "model.hpp:3372-3381", "mark_k_complete, credit_gof_save (the marks loop)"))
    o.append(box(360, 520, 300, 54, "upstream_kvs_ready[slot].count_down()",
                 ["for every downstream minibatch: every row",
                  "store happens-before this (the join's acquire)"],
                 "model.hpp:3383-3385; 3125-3126", "upstream_kvs_ready[slot].count_down() "
                 "(every row store happens-before it)"))
    o.append(rect(690, 520, 290, 54, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(835, 535, "before: set_k_row per token sat here", 10, "middle", True,
                  weight=600, fill=C["gone"]))
    o.append(lines(835, 549, ["inside the marks loop, [main] alone;",
                              "removed (M6)"], 9, 11, "middle", fill=C["gone"]))
    o.append(cite(976, 570, "base model.hpp:3096-3116"))
    boxes.append(("before: set_k_row per token sat here (removed)",
                  "base model.hpp:3096-3116 (the 23 lines removed before head 3376)"))
    o.append(arrow(fid, "ink", [(332, 547), (358, 547)], ink, 1.3))

    # ---- arrows ----------------------------------------------------------
    o.append(arrow(fid, "ink", [(230, 210), (268, 210)], ink, 1.3))
    o.append(arrow(fid, "ink", [(460, 210), (498, 210)], ink, 1.3))
    o.append(lab(479, 204, "yes"))
    o.append(arrow(fid, "vnni", [(700, 210), (748, 210)], C["vnni"], 1.4))
    o.append(lab(724, 204, "no: 2..16", C["vnni"]))
    o.append(arrow(fid, "vnni", [(865, 256), (865, 288)], C["vnni"], 1.4))
    o.append(arrow(fid, "rm", [(365, 240), (365, 288)], C["rm"], 1.4))
    o.append(lab(385, 268, "no", C["rm"]))
    o.append(arrow(fid, "rm", [(365, 360), (365, 396)], C["rm"], 1.4))
    o.append(arrow(fid, "vnni", [(600, 240), (600, 288)], C["vnni"], 1.4))
    o.append(lab(615, 268, "yes", C["vnni"]))
    o.append(arrow(fid, "vnni", [(600, 360), (600, 396)], C["vnni"], 1.4))
    o.append(arrow(fid, "vnni", [(805, 350), (805, 396)], C["vnni"], 1.4))
    o.append(lab(790, 376, "yes", C["vnni"]))
    o.append(arrow(fid, "vnni", [(925, 350), (925, 396)], C["vnni"], 1.4))
    o.append(lab(940, 376, "no", C["vnni"]))
    # the run comes from the window or from main alone
    o.append(arrow(fid, "unit", [(445, 138), (445, 160), (125, 160), (125, 178)], C["unit"], 1.4))
    o.append(text(285, 156, "per claimed unit", 8.5, "middle", fill=C["unit"], weight=700))
    o.append(arrow(fid, "ink", [(805, 138), (805, 166), (135, 166), (135, 178)], ink, 1.3))
    o.append(text(470, 174, "items[0, n_items) on main", 8.5, "middle", fill=ink, weight=600))
    # the stores -> the marks loop
    o.append(arrow(fid, "ink", [(600, 454), (600, 488)], ink, 1.3))
    o.append(text(608, 474, "every store done (the join, or main's own store)", 9, "start",
                  fill=ink, weight=700))

    # notes
    o.append(rect(20, 290, 210, 70, "#fff", C["line"], 1, 4))
    o.append(lines(28, 305, ["K buffer not bf16: each row is",
                             "converted to bf16 on the stack",
                             "(conv, 16 x head_size, 64-byte",
                             "aligned) before either store."], 9, 11))
    o.append(cite(226, 356, "model.hpp:3226-3229"))
    boxes.append(("conv (bf16 conversion on the stack)", "model.hpp:3226-3229"))
    o.append(rect(20, 376, 210, 100, "#fff", C["line"], 1, 4))
    o.append(text(28, 392, "Worked example", 10, weight=700))
    o.append(lines(28, 406, ["units 0 and 1 (16 tokens each, page 7",
                             "blocks 0 and 1): set_k_block with",
                             "present 0xffff, a whole block each.",
                             "unit 2 (page 7, offsets 32..40):",
                             "set_k_block with present 0x01ff,",
                             "a partial block (lanes 9..15 untouched)."], 9, 11))
    o.append(cite(226, 472, "STYLE.md worked example"))
    o.append(text(20, 604, "Arrow labels are the answers of the decision they leave. "
                  "Thread names in brackets.", 9.5, fill=C["muted"]))
    o.append(text(20, 618, "A block has no layout state in this PR: set_k_block and set_k_row "
                  "write the same VNNI columns (store_block is bit-identical to store_row per "
                  "present token, kv_cache.hpp:2082-2083).", 9.5, fill=C["muted"]))
    o.append(text(20, 632, "The row bits, the row-major tail block and the deferred conversion "
                  "land in PR 4959, not here.", 9.5, fill=C["muted"]))
    o.append(text(20, 672, "run colours", 10, fill=C["muted"]))
    o.append(legend_runs(110, 660))

    cap = ("B5, decision model: what one run of consecutive tokens becomes in the page. "
           "First the sharing decision (top band): a shared store hands every claimed unit "
           "to store_k_block, an unshared store hands all items to it on main. Then, per "
           "run: a row-major slot stores one row per token and KV head through "
           "page::k(...).set; a VNNI slot stores a run of one token with set_k_row (the "
           "per-row scatter) and a run of 2 to 16 tokens with set_k_block, where store_block "
           "writes whole lines for a full present mask and masked lines otherwise. After "
           "every row is stored, main runs the marks loop, which no longer holds a store. "
           "The worked example's three units are traced in the note at the left.")
    legend = [
        ("box", "white box, ink outline: a step of the store (one run (store_k_block), "
                "set_k_block per KV head, page::k(...).set, set_k_row per KV head, "
                "mark_k_complete, count_down, not shared: main alone) and, with rounded "
                "corners, a decision (k_store_shared?, VNNI slot?, a run of one token?, "
                "present == 0xffff?)"),
        ("ctx", "grey band, light grey outline: the sharing decision at the top and the "
                "marks loop after the stores; every box inside the lower band runs on main "
                "only, once per item of the minibatch"),
        ("lane", "white box, light grey outline: a note (the bf16 conversion of the K "
                 "buffer rows, and the worked example)"),
        ("grey-blue box and arrow: shared: the window; per claimed unit -> one run; "
         "grey-blue text = the 'yes' of k_store_shared", "multi",
         ["unit", ("arrow", C["unit"])]),
        ("blue boxes and arrows: the VNNI paths: a run of 2..16 -> set_k_block per KV "
         "head -> a whole block (solid blue) or a partial block (blue, dashed outline); a "
         "run of one token -> set_k_row -> the scatter (white, blue outline); blue text = "
         "those answers", "multi", ["vnni", ("#fff", C["vnni"], False, False),
                                    (C["vnni_fill"], C["vnni"], True, False),
                                    ("arrow", C["vnni"])]),
        ("orange box and arrow: the row-major path: not a VNNI slot -> page::k(...).set "
         "-> row-major slot; orange text = that 'no'", "multi", ["rm", ("arrow", C["rm"])]),
        ("gone", "red dashed box, red text: before (removed), the set_k_row per token "
                 "inside the marks loop"),
        ("arrow", "ink arrow: the next step or decision while no path is decided yet: "
                  "not shared -> one run, one run -> VNNI slot?, yes -> a run of one "
                  "token?, every store done -> the marks loop, mark -> count_down"),
        ("font_mono", "monospace = the title of a step or a run box (a function or a "
                      "store) and the test under a decision"),
        ("font_sans", "sans-serif = a decision's question (bold), the description under "
                      "a title, the arrow labels (the answers), the notes at the left "
                      "and the run colours row; grey sans-serif = a note"),
        ("font_cite", "small grey monospace = the lines that define a box (file:line)"),
    ]
    return figure(fid, W, H, "Decision model of the K store of one run", "".join(o), cap,
                  boxes=boxes, legend=legend)
