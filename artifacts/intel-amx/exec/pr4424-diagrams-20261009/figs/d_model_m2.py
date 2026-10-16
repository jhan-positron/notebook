"""D2 of the PR 4424 model.hpp page: unit m2, the sharing decision
(k_store_shared), drawn as B3's step 1 ("save_k_impl: the decision") opened
into its four tests: what each test reads (left column), the test itself
(middle), the Note's reason for each "no" (grey column at the right), and
what the one answer makes main and a helper do next (the band at the bottom).

Every label is an identifier or a comment phrase of the code; every box cites
the head line that defines it. Facts: facts/model.json (verified claims
model-function-6, model-data-6, model-data-13, model-data-26, model-data-31,
model-seq-10, model-seq-11, model-seq-17, model-rule-4, model-rule-15,
model-glossary-40, model-glossary-49).
"""
from svg_helpers import (C, arrow, cite, figure, lines, marker_defs, rect,
                         text, text_width)
from base_model import MAIN_FILL, N_ITEMS_EXAMPLE, N_WORKERS_EXAMPLE

BASE = ("Updates B3: step 1 of both lanes (is_main, shared: the decision) is opened into "
        "the four tests of k_store_shared, with the input each test reads, the Note's "
        "reason for every 'no', and what the one answer makes main and a helper do next.")

# the worked example of STYLE.md: a VNNI slot (head_size 128), 3 workers, 40 items
HEAD_SIZE_EXAMPLE = 128    # k_vnni::layout_on<128> is the VNNI layout (tensor/k_vnni.hpp:126)
MAX_SHARED_WORKERS = 128   # k_store_window_t::max_shared_workers (common.hpp:1173)
K_STORE_BLOCK = 16         # k_store_block = k_vnni::BLOCK_TOKENS_16 (model.hpp:3153)

W = 720
IX, IW = 10, 150       # column 1: what k_store_shared reads
TX, TW = 240, 200      # column 2: the four tests
RX, RW = 480, 228      # column 3: the "no" container (shared = false)
TY = [62, 164, 266, 368]   # the four tests' top edges
TH = 82                    # a test box's height
YC = [ty + TH / 2 for ty in TY]   # the tests' centre lines


def _w(s, size, mono=False):
    return text_width(s, size, mono)


# ---- primitives of this figure (built from svg_helpers only) ----------------
def input_box(x, y, w, h, name, sub, ref, tag, cite_up=False):
    """A data box in B1's style: name (mono, bold), description lines, the
    change tag at the lower left, the citation at the lower right (or, with
    cite_up, on its own line above the tag when the two would collide)."""
    o = [rect(x, y, w, h, "#fff", C["ink"], 1.2, 5)]
    o.append(text(x + w / 2, y + 15, name, 10, "middle", True, weight=600))
    o.append(lines(x + w / 2, y + 28, sub, 9, 11, "middle", fill=C["muted"]))
    col = C["new"] if tag.startswith("new") else C["muted"]
    o.append(text(x + 6, y + h - 5, tag, 8.5, fill=col, weight=600))
    o.append(cite(x + w - 4, y + h - (16 if cite_up else 4), ref))
    return "".join(o)


def test_box(x, y, w, h, question, sub, example, ref):
    """One test of k_store_shared in B5's decision_box style (question in
    bold, the code under it), plus the worked example's value in muted text."""
    o = [rect(x, y, w, h, "#fff", C["ink"], 1.6, 10)]
    o.append(text(x + w / 2, y + 16, question, 11, "middle", weight=700))
    o.append(lines(x + w / 2, y + 30, sub, 9, 11, "middle", mono=True))
    o.append(text(x + w / 2, y + h - 15, example, 8.5, "middle", fill=C["muted"],
                  italic=True))
    o.append(cite(x + w - 6, y + h - 4, ref))
    return "".join(o)


def reason_row(x, y, w, h, title, sub, ref, mono_title=False):
    """One reason for a 'no', quoted from Note [Shared block save]."""
    o = [rect(x, y, w, h, "#fff", C["ink"], 1.1, 4)]
    o.append(text(x + 6, y + 14, title, 9.5, mono=mono_title, weight=700))
    o.append(lines(x + 6, y + 27, sub, 9, 11))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def thread_cell(x, y, w, h, thread, title, sub, ref, dash=None):
    """What one thread does next: the bracketed thread name, the step (mono),
    the code lines, the citation. dash = the thread waits."""
    o = [rect(x, y, w, h, "#fff", C["ink"], 1.3 if dash else 1.2, 4, dash)]
    o.append(text(x + 8, y + 13, thread, 9.5, weight=700))
    o.append(text(x + 8, y + 28, title, 10, mono=True, weight=600))
    o.append(lines(x + 8, y + 41, sub, 9, 11))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fig():
    fid = "model-d2"
    ink = C["ink"]
    o = [marker_defs(fid, {"ink": ink})]
    boxes = []

    def lab(x, y, s, size=9, anchor="middle"):
        return text(x, y, s, size, anchor, fill=ink, weight=700)

    # ---- header: the function ----------------------------------------------
    sig = "k_store_shared(q_batch, n_workers) const noexcept"
    o.append(text(IX, 18, sig, 11.5, mono=True, weight=700))
    o.append(text(IX + _w(sig, 11.5, True) * 1.08 + 8, 18, "new", 9.5, fill=C["new"],
                  weight=700))
    o.append(cite(W - 12, 18, "model.hpp:3191-3192"))
    boxes.append(("k_store_shared", "model.hpp:3189-3200 (comment 3189-3190, "
                  "definition 3191-3192)"))
    o.append(text(IX, 33, "Whether the K store of this minibatch is shared with the "
                  "helpers. The answer is the same on the main thread and on every helper.",
                  9, fill=C["muted"]))
    # column captions
    o.append(text(IX + IW / 2, 54, "what it reads", 9.5, "middle", fill=C["muted"],
                  weight=700))
    o.append(text(TX + TW / 2, 54, "the tests, in code order", 9.5, "middle",
                  fill=C["muted"], weight=700))
    o.append(text(RX + RW / 2, 54, "a 'no' and the Note's reason", 9.5, "middle",
                  fill=C["muted"], weight=700))

    # ---- column 2: the four tests --------------------------------------------
    TRUE_Y = TY[3] + TH + 24          # the "shared = true" box
    tests = [
        ("VNNI slot?",
         ["if constexpr (!k_vnni::layout_on<", "geometry.kv.head_size>)", "return false;"],
         f"worked example: head_size {HEAD_SIZE_EXAMPLE} -> yes",
         "model.hpp:3193-3195",
         "VNNI slot? (k_vnni::layout_on)", "model.hpp:3193-3195; tensor/k_vnni.hpp:119-130"),
        ("more than one worker?",
         ["n_workers > 1", "(worker_ix 0 is main,", "1 .. n_workers - 1 are the helpers)"],
         f"worked example: {N_WORKERS_EXAMPLE} > 1 -> yes",
         "model.hpp:3196; 3111-3112",
         "n_workers > 1 (more than one worker?)", "model.hpp:3196; Note at model.hpp:3111-3116"),
        (f"at most {MAX_SHARED_WORKERS} workers?",
         ["n_workers <=", "q_batch->k_store_window", ".helper_windows.size()"],
         f"worked example: {N_WORKERS_EXAMPLE} <= {MAX_SHARED_WORKERS} -> yes",
         "model.hpp:3197",
         "n_workers <= helper_windows.size() (at most 128 workers?)",
         "model.hpp:3197; common.hpp:1171-1173, 1190-1192"),
        (f"more than {K_STORE_BLOCK} items?",
         ["q_batch->items.size()", "> k_store_block"],
         f"worked example: {N_ITEMS_EXAMPLE} > {K_STORE_BLOCK} -> yes",
         "model.hpp:3198",
         "items.size() > k_store_block (more than 16 items?)",
         "model.hpp:3198; model.hpp:3153 (k_store_block = 16)"),
    ]
    for ty, (q, sub, ex, ref, label, reg) in zip(TY, tests):
        o.append(test_box(TX, ty, TW, TH, q, sub, ex, ref))
        boxes.append((label, reg))
    # yes arrows between the tests and to the result
    for y0, y1 in ((TY[0] + TH, TY[1]), (TY[1] + TH, TY[2]), (TY[2] + TH, TY[3]),
                   (TY[3] + TH, TRUE_Y)):
        o.append(arrow(fid, "ink", [(TX + TW / 2, y0), (TX + TW / 2, y1)], ink, 1.3))
        o.append(lab(TX + TW / 2 + 8, (y0 + y1) / 2 + 4, "yes", anchor="start"))
    # the result: shared = true
    o.append(rect(TX, TRUE_Y, TW, 56, "#fff", ink, 1.6, 6))
    o.append(text(TX + TW / 2, TRUE_Y + 16, "shared = true", 11, "middle", True, weight=700))
    o.append(lines(TX + TW / 2, TRUE_Y + 30, ["a window exists only when", "it says yes"],
                   9, 11, "middle", fill=C["muted"]))
    o.append(cite(TX + TW - 6, TRUE_Y + 52, "model.hpp:3364; 3118-3119"))
    boxes.append(("shared = true (a window exists)", "model.hpp:3364 (the local); "
                  "Note at 3118-3119"))

    # ---- column 3: the "no" container, its reason rows and the result --------
    RB = TRUE_Y + 20                  # the container's bottom edge
    o.append(rect(RX, 62, RW, RB - 62, MAIN_FILL, C["line"], 1, 6))
    boxes.append(("shared = false (the grey column)", "model.hpp:3365 (comment); "
                  "the reasons at 3114-3116 and 3120-3121"))
    RRX, RRW, RRH = RX + 7, RW - 14, 56
    reasons = [
        ("if constexpr: return false", True,
         ["every other head size keeps the", "row-major plane: no VNNI layout"],
         "model.hpp:3193; tensor/k_vnni.hpp:120",
         "if constexpr (!k_vnni::layout_on<geometry.kv.head_size>) return false",
         "model.hpp:3193-3195; tensor/k_vnni.hpp:119-130"),
        ("n_workers == 1 never shares", False,
         ["the handwritten plugins, and the unit", "tests except the shared-save case"],
         "model.hpp:3114-3116",
         "n_workers == 1 never shares", "model.hpp:3114-3116"),
        (f"more than {MAX_SHARED_WORKERS} workers is not shared", False,
         [f"max_shared_workers = {MAX_SHARED_WORKERS}: worker counts",
          "above this take the unshared store"],
         "common.hpp:1171-1173; model.hpp:3121",
         "more than 128 workers is not shared", "model.hpp:3120-3121; common.hpp:1171-1173"),
        (f"a pass with at most {K_STORE_BLOCK} items", False,
         ["such as a decode step: not shared;",
          f"a decode step with > {K_STORE_BLOCK} items is shared"],
         "model.hpp:3120-3121; 3198",
         "a pass with at most 16 items (such as a decode step)",
         "model.hpp:3120-3121; the test at 3198"),
    ]
    for yc, (title, mono, sub, ref, label, reg) in zip(YC, reasons):
        ry = yc - RRH / 2
        o.append(reason_row(RRX, ry, RRW, RRH, title, sub, ref, mono_title=mono))
        boxes.append((label, reg))
        # the "no" arrow from the test to its reason
        o.append(arrow(fid, "ink", [(TX + TW, yc), (RRX, yc)], ink, 1.3))
        o.append(lab((TX + TW + RRX) / 2, yc - 5, "no"))
    o.append(text(RX + 8, RB - 29, "shared = false", 10.5, mono=True, weight=700))
    o.append(cite(RX + RW - 6, RB - 29, "model.hpp:3365"))
    o.append(text(RX + 8, RB - 16, "An unshared store is main's alone.", 9, fill=C["muted"]))

    # ---- column 1: what it reads ---------------------------------------------
    ex = IX + IW
    # a: head_size -> test 1
    o.append(input_box(IX, YC[0] - 31, IW, 62, "geometry.kv.head_size",
                       ["attention_geometry template", f"{HEAD_SIZE_EXAMPLE} = the VNNI layout"],
                       "model.hpp:3191", "unchanged"))
    boxes.append(("geometry.kv.head_size", "model.hpp:3191 (template parameter), 3193 "
                  "(the use); kv_cache.hpp:106-108 (attention_geometry)"))
    o.append(arrow(fid, "ink", [(ex, YC[0]), (TX, YC[0])], ink, 1.3))
    o.append(lab(200, YC[0] - 6, "1 value"))
    # b: n_workers -> test 2 and test 3
    o.append(input_box(IX, YC[1] - 37, IW, 80, "n_workers",
                       ["= 1 + n_main_helpers in the", "generated run() (unchanged,",
                        "TronCpp.hs:1388); default 1"],
                       "model.hpp:3192", "new parameter", cite_up=True))
    boxes.append(("n_workers", "model.hpp:3192 (the new parameter of k_store_shared); "
                  "TronCpp.hs:1388 (n_workers = 1 + n_main_helpers: unchanged, where the "
                  "value comes from); model.hpp:3467-3468, 3479-3480 (default 1)"))
    o.append(arrow(fid, "ink", [(ex, YC[1] - 6), (TX, YC[1] - 6)], ink, 1.3))
    o.append(lab(200, YC[1] - 12, "1 value"))
    o.append(arrow(fid, "ink", [(ex, YC[1] + 16), (195, YC[1] + 16), (195, YC[2] - 16),
                                (TX, YC[2] - 16)], ink, 1.3))
    o.append(lab(218, YC[2] - 22, "1 value", 8.5))
    # c: helper_windows -> test 3
    o.append(input_box(IX, YC[2] + 14 - 37, IW, 74, "helper_windows",
                       ["std::array<uint32_t,", "max_shared_workers>;",
                        f".size() = {MAX_SHARED_WORKERS}"],
                       "common.hpp:1190-1192", "new"))
    boxes.append(("helper_windows", "common.hpp:1190-1192; max_shared_workers = 128 at "
                  "common.hpp:1171-1173"))
    o.append(arrow(fid, "ink", [(ex, YC[2] + 14), (TX, YC[2] + 14)], ink, 1.3))
    o.append(lab(200, YC[2] + 8, ".size()"))
    o.append(lab(200, YC[2] + 28, f"= {MAX_SHARED_WORKERS}"))
    # d: items -> test 4
    dy = YC[3] - 8 - 31
    o.append(input_box(IX, dy, IW, 62, "q_batch->items",
                       ["the token jobs of this", "minibatch (n_items of them)"],
                       "common.hpp:1085", "unchanged"))
    boxes.append(("q_batch->items", "common.hpp:1084-1085; n_items at model.hpp:3374"))
    o.append(arrow(fid, "ink", [(ex, YC[3] - 8), (TX, YC[3] - 8)], ink, 1.3))
    o.append(lab(200, YC[3] - 14, ".size()"))
    o.append(lab(200, YC[3] + 6, "= n_items"))
    # e: k_store_block -> test 4
    ey = dy + 62 + 8
    o.append(input_box(IX, ey, IW, 56, "k_store_block",
                       ["= k_vnni::BLOCK_TOKENS_16", f"({K_STORE_BLOCK} tokens per block)"],
                       "model.hpp:3153", "new"))
    boxes.append(("k_store_block", "model.hpp:3153; tensor/k_vnni.hpp:68, 106"))
    eyc = ey + 28
    o.append(arrow(fid, "ink", [(ex, eyc), (228, eyc), (228, YC[3] + 22), (TX, YC[3] + 22)],
                   ink, 1.3))
    o.append(lab(194, eyc - 6, "1 constant"))

    # ---- the band: what each thread does next (B3 step 1 -> step 2) ----------
    BY, BH = TRUE_Y + 56 + 18, 196
    LX, HX2, HW = 10, 365, 345
    o.append(arrow(fid, "ink", [(TX + TW / 2, TRUE_Y + 56), (TX + TW / 2, BY)], ink, 1.3))
    o.append(arrow(fid, "ink", [(RX + RW / 2, RB), (RX + RW / 2, BY)], ink, 1.3))
    for hx, title, note, ref in ((LX, "shared = true",
                                  "-> a window exists (B3 step 2 on both lanes)",
                                  "model.hpp:3118-3119"),
                                 (HX2, "shared = false",
                                  "-> an unshared store is main's alone",
                                  "model.hpp:3365")):
        o.append(rect(hx, BY, HW, BH, MAIN_FILL, C["line"], 1, 6))
        o.append(text(hx + 8, BY + 17, title, 10.5, mono=True, weight=700))
        o.append(text(hx + 8 + _w(title, 10.5, True) * 1.08 + 8, BY + 17, note, 9,
                      fill=C["muted"]))
        o.append(cite(hx + HW - 6, BY + 30, ref))
    boxes.append(("is_main, shared (B3 step 1: save_k_impl's decision, the band)",
                  "model.hpp:3361-3366"))
    CY1, CY2, CH = BY + 38, BY + 116, 70
    CW = HW - 16
    o.append(thread_cell(LX + 8, CY1, CW, CH, "[main, worker_ix 0]",
                         "open the window (B3 step 2)",
                         ["k_store_cut_units; reset next_unit, finished (relaxed);",
                          "opened.fetch_add(1, release): the helpers may enter"],
                         "model.hpp:3380-3384"))
    boxes.append(("k_store_cut_units; opened.fetch_add(1, release) [main, worker_ix 0]: "
                  "open the window (B3 step 2)", "model.hpp:3380-3384"))
    o.append(thread_cell(LX + 8, CY2, CW, CH, "[helper, worker_ix 1 .. n_workers - 1]",
                         "wait for window W (B3 step 2, waits)",
                         ["my_window = ++helper_windows[worker_ix];",
                          "while (opened.load(acquire) < my_window) _mm_pause();"],
                         "model.hpp:3385-3390", dash="5 3"))
    boxes.append(("helper_windows[worker_ix]; opened.load(acquire) [helper, worker_ix 1 .. "
                  "n_workers - 1]: wait for window W (B3 step 2)", "model.hpp:3385-3390"))
    o.append(thread_cell(HX2 + 8, CY1, CW, CH, "[main, worker_ix 0]",
                         "store_k_block(q_batch, slot, ks, 0, n_items)",
                         ["every item on main alone, then B3 steps 6, 7, 8",
                          "(record the rows, mark_k_complete, credit_gof_save, count_down)"],
                         "model.hpp:3417-3419"))
    boxes.append(("store_k_block(q_batch, slot, ks, 0, n_items) [main, worker_ix 0]: the "
                  "unshared store", "model.hpp:3417-3419"))
    o.append(thread_cell(HX2 + 8, CY2, CW, CH, "[helper, worker_ix 1 .. n_workers - 1]",
                         "return",
                         ["if (!is_main && !shared) return;",
                          "no window is opened, so the helper does not wait for one"],
                         "model.hpp:3365-3366; 3118-3120"))
    boxes.append(("if (!is_main && !shared) return; [helper, worker_ix 1 .. n_workers - 1]: "
                  "return at once", "model.hpp:3365-3366; Note at model.hpp:3118-3120"))

    # ---- notes ---------------------------------------------------------------
    ny = BY + BH + 20
    o.append(text(IX, ny, f"Worked example (STYLE.md): head_size {HEAD_SIZE_EXAMPLE} (VNNI), "
                  f"{N_WORKERS_EXAMPLE} workers, {N_ITEMS_EXAMPLE} items. Every test says yes, "
                  "so main opens window W", 9))
    o.append(text(IX, ny + 12, "and both helpers wait for it (the left half). A decode step "
                  f"with at most {K_STORE_BLOCK} items, or n_workers = 1, takes the right half.",
                  9))
    o.append(text(IX, ny + 28, "dashed = a thread waits (spin with _mm_pause); the grey column "
                  "quotes the reasons of a 'no' from Note [Shared block save].", 9,
                  fill=C["muted"]))
    H = ny + 36

    cap = ("Updates B3: step 1 of both lanes (the decision) is drawn in full: "
           "k_store_shared runs four tests in code order, the VNNI layout gate at compile "
           "time, the worker count twice, then the item count. Any 'no' lands in the grey "
           "column, where each row quotes the Note's reason, and the one answer sends main "
           "and a helper to the band at the bottom: on true main opens the window and a "
           "helper waits for it, on false main stores alone and a helper returns. In the "
           f"worked example (head_size {HEAD_SIZE_EXAMPLE}, {N_WORKERS_EXAMPLE} workers, "
           f"{N_ITEMS_EXAMPLE} items) every test says yes.")
    legend = [
        ("box", "white box, ink outline: an input k_store_shared reads "
                "(geometry.kv.head_size, n_workers, helper_windows, q_batch->items, "
                "k_store_block), with rounded corners one of its four tests, the result "
                "shared = true, a reason row of the grey column, and a thread cell of the "
                "two bands (what main and a helper then run)"),
        ("ctx", "grey fill, light grey outline: the column of the Note's reasons for a "
                "'no', and the two bands below the tests (shared = true, shared = false) "
                "that hold one cell per thread"),
        ("idle", "dashed ink outline: the helper waits for window W "
                 "(while (opened.load(acquire) < my_window) _mm_pause();)"),
        ("arrow", "ink arrow: an input into a test (its label says how many), a 'yes' to "
                  "the next test or to shared = true, a 'no' to the Note's reason, and the "
                  "answer down into the band"),
        ("font_mono", "monospace = an identifier or a value from the code: the signature, "
                      "the box names, the tests' code, shared = true / shared = false, the "
                      "step and code lines of a thread cell"),
        ("font_sans", "sans-serif = prose: the questions, the descriptions, the column "
                      "captions, the bracketed thread names, the how-many labels, the notes"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the line or Note that defines the box "
                      "(file:line)"),
        ("font_tag", "bold 'new' = added by this PR (k_store_shared, the n_workers "
                     "parameter, helper_windows, k_store_block); grey 'unchanged' = "
                     "existing code (geometry.kv.head_size, q_batch->items)"),
    ]
    return figure(fid, W, H, "The sharing decision k_store_shared: its inputs, tests, "
                  "reasons for a no, and what each thread does next", "".join(o), cap,
                  boxes=boxes, legend=legend)
