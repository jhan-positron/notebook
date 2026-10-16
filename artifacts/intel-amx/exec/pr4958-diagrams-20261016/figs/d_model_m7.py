"""Change diagram of unit m7 (model.hpp page of PR 4958): the save_k entry
points take a worker index and a worker count.

Head lines 3388-3413: both save_k overloads gain worker_ix = 0 and
n_workers = 1 and forward them to save_k_impl. The callers (generated run(),
generated run_main_help, the handwritten plugin, the tests) come from
ingest/src/TronCpp.hs, llama.hpp and t_llama_unit.cpp of the same head
(b39765ec29).
"""
import sys

from svg_helpers import (C, arrow, cite, figure, line, lines, marker_defs,
                         rect, text, text_width)
from base_model import MAIN_FILL, N_WORKERS_EXAMPLE, THREADS_EXAMPLE

BASE = ("Updates B2. It opens B2's caller boxes and its save_k cell into the "
        "before and after signatures of the two overloads. It adds the worker "
        "arguments each caller passes (0 and n_workers from the generated run(), "
        "worker_ix and n_workers from the generated run_main_help, the defaults 0 "
        "and 1 from the handwritten plugin and the tests) and the three checks "
        "save_k_impl makes on them.")

FID = "model-d7"
W = 720

X1, W1 = 20, 314
X2, W2 = 360, 336
BUS = 346
RBUS = 708


def _fit(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w}", file=sys.stderr)
    return s


def _indented(x, y, s, size, mono, fill=None, weight=None):
    ind = len(s) - len(s.lstrip(" "))
    per = size * (0.60 if mono else 0.55)
    return text(x + ind * per, y, s.lstrip(" "), size, mono=mono, fill=fill,
                weight=weight)


def caller_box(x, y, w, h, ls, ref):
    o = [rect(x, y, w, h, MAIN_FILL, C["line"], 1, 4)]
    for s in ls:
        _fit(s, 9.5, w - 16, False, "caller_box")
    o.append(text(x + 8, y + 15, ls[0], 9.5, weight=600))
    ty = y + 27
    for s in ls[1:]:
        o.append(_indented(x + 8, ty, s, 9.5, False))
        ty += 12
    _fit(ref, 8.5, w - 8, True, "caller_box cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def sig_cell(x, y, w, h, name, desc, sig, ref, tag=None, new_lines=(),
             fill="#fff", stroke=C["ink"]):
    o = [rect(x, y, w, h, fill, stroke, 1.2, 4)]
    _fit(name, 11.5, w - 16, True, "sig_cell name")
    o.append(text(x + 8, y + 16, name, 11.5, mono=True, weight=600))
    ty = y + 31
    for s in desc:
        _fit(s, 9.5, w - 16, False, "sig_cell desc")
        o.append(text(x + 8, ty, s, 9.5))
        ty += 12
    for i, s in enumerate(sig):
        _fit(s, 9, w - 16, True, "sig_cell sig")
        if i in new_lines:
            o.append(_indented(x + 8, ty, s, 9, True, fill=C["new"], weight=700))
        else:
            o.append(_indented(x + 8, ty, s, 9, True))
        ty += 12
    if tag:
        col = C["new"] if tag.startswith("new") else (
            C["gone"] if tag.startswith("removed") else C["muted"])
        o.append(text(x + 8, y + h - 5, tag, 9, fill=col))
    _fit(ref, 8.5, w - 8, True, "sig_cell cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fig():
    fid = FID
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []

    o.append(text(20, 18, "save_k (two overloads): the entry points, before and after",
                  12.5, weight=700))
    o.append(cite(W - 20, 18, "model.hpp:3388-3413"))
    boxes.append(("save_k (two overloads)", "model.hpp:3388-3413 (comment 3388-3393; "
                  "overload 1 at 3394-3403; overload 2 at 3405-3413)"))

    bx, by, bw, bh = 20, 28, 680, 78
    o.append(rect(bx, by, bw, bh, "#fff", C["gone"], 1.4, 5, "6 3"))
    o.append(text(bx + 10, by + 17, "save_k(batch* q_batch, kv_buffer_t& ks)", 10.5,
                  mono=True, weight=700, fill=C["gone"]))
    o.append(text(bx + bw - 10, by + 17, "before (removed)", 9.5, "end", fill=C["gone"],
                  weight=700))
    o.append(text(bx + 10, by + 32, "save_k(batch* q_batch, attention_operation_descriptor "
                  "const& operation, kv_buffer_t& ks)", 10.5, mono=True, weight=700,
                  fill=C["gone"]))
    o.append(text(bx + 10, by + 47, "both called save_k_impl<geometry>(q_batch, operation, "
                  "ks): no worker index, no worker count; the calling thread stored "
                  "every row", 9, fill=C["muted"]))
    o.append(text(bx + 10, by + 60, "the generated run_main_help emitted no save_k call: "
                  "'AttentionStmt _ -> []' (removed line)", 9, fill=C["muted"]))
    o.append(cite(bx + bw - 6, by + bh - 4,
                  "base model.hpp:3131, 3137-3140 (signatures), 3135, 3142 (calls); "
                  "base TronCpp.hs:2924"))
    boxes.append(("save_k(q_batch, ks) / save_k(q_batch, operation, ks) (before, removed)",
                  "replaced at head model.hpp:3394-3413; the removed lines are base "
                  "model.hpp 3131 and 3137-3140 (signatures), 3135 and 3142 (the "
                  "save_k_impl calls)"))
    boxes.append(("'AttentionStmt _ -> []' (before, removed)",
                  "base TronCpp.hs:2924 (runHelperStatement emitted nothing for an "
                  "attention statement); head TronCpp.hs:2924-2942"))

    o.append(text(360, 116, "before -> after: PR 4958", 9, "middle", fill=C["new"],
                  weight=700))

    o.append(text(X1 + W1 / 2, 118, "callers (other files)", 10.5, "middle",
                  weight=700))
    ay, ah = 126, 66
    o.append(caller_box(X1, ay, W1, ah,
                        ["generated run() [main, worker_ix 0]:",
                         "save_k<geometry, operation_ix>(",
                         "    q_batch, ks, 0, n_workers)",
                         "worker 0 as in kernelCall; n_workers in scope in run()"],
                        "TronCpp.hs:2996-3004"))
    boxes.append(("save_k call of the generated run(): save_k(q_batch, ks, 0, n_workers)",
                  "TronCpp.hs:2996-3004 (saveKv: attentionRuntimeCall \"save_k\" with "
                  "IntLit 0 and n_workers)"))
    by2 = ay + ah + 8
    o.append(caller_box(X1, by2, W1, ah,
                        ["generated run_main_help [helper i, worker_ix 1 + i]:",
                         "save_k<geometry, operation_ix>(",
                         "    q_batch, ks, worker_ix, n_workers)",
                         "only for an operation with a KV write (attentionKvWrite)"],
                        "TronCpp.hs:2924-2942; 1430"))
    boxes.append(("save_k call of the generated run_main_help: save_k(q_batch, ks, "
                  "worker_ix, n_workers)",
                  "TronCpp.hs:2924-2942 (runHelperStatement, AttentionStmt), 1430 "
                  "(runHelpParams: q_batches, worker_ix, n_workers)"))
    cy = by2 + ah + 8
    o.append(caller_box(X1, cy, W1, ah,
                        ["handwritten plugin, most tests [the calling thread]:",
                         "save_k<geometry>(q_batch, operation, kouts)",
                         "no worker arguments: the defaults apply,",
                         "worker_ix 0, n_workers 1 (the store is never shared)"],
                        "llama.hpp:1038; t_llama_unit.cpp:4035"))
    boxes.append(("handwritten plugin and tests: save_k with the defaults",
                  "Note [Shared block save] model.hpp:3099-3101 (the handwritten plugins "
                  "and the unit tests except the shared-save case never share); "
                  "t_llama_unit.cpp:2357, 2360, 4035 (calls with the defaults); "
                  "h/tron/plugins/llama.hpp:1038 (overload 2 with the defaults); "
                  "t/heterogeneous_scheduler_compile.cpp:192, 200, 208 (overload 1 with "
                  "the defaults)"))
    dy, dh = cy + ah + 8, 54
    o.append(caller_box(X1, dy, W1, dh,
                        ["test 'three threads' [main + 2 std::thread helpers]:",
                         "save_k<geometry>(q_batch, op, kouts,",
                         "    worker_ix, n_workers): worker_ix 0..2, n_workers 3"],
                        "t_llama_unit.cpp:4040-4061"))
    boxes.append(("save_k calls of the test 'three threads' (worker_ix 0..2, n_workers 3)",
                  "t_llama_unit.cpp:4040-4067 (n_workers = 3 at 4042, helper calls "
                  "4056-4057, main call 4060-4061)"))

    sy, sh = dy + dh + 22, 110
    o.append(text(X1 + W1 / 2, sy - 6, "where the arguments come from", 10.5, "middle",
                  weight=700))
    o.append(rect(X1, sy, W1, sh, "#fff", C["ink"], 1.2, 4))
    o.append(text(X1 + 8, sy + 15, "the run() split [generated run(), main]", 9.5,
                  weight=600))
    split = ["n_main_helpers = outer_state.recommend_n_main_helpers()",
             "n_workers = 1 + n_main_helpers",
             "for (i < n_main_helpers) tp.enqueue_to(i, ...",
             "    run_main_help(q_batches, 1 + i, n_workers))"]
    ty = sy + 29
    for s in split:
        _fit(s, 9, W1 - 16, True, "split")
        o.append(_indented(X1 + 8, ty, s, 9, True))
        ty += 12
    o.append(text(X1 + 8, sy + 83, "1 run() -> 1 main + n_main_helpers helpers", 9,
                  fill=C["ink"], weight=700))
    o.append(text(X1 + 8, sy + 95, "= n_workers workers of every shared window", 9,
                  fill=C["ink"], weight=700))
    o.append(cite(X1 + W1 - 4, sy + sh - 4, "TronCpp.hs:1362-1364, 1385-1392"))
    boxes.append(("n_workers = 1 + n_main_helpers (the run() split, run_main_help launches)",
                  "TronCpp.hs:1385-1392 (workerSplitLines: n_main_helpers, n_workers = "
                  "1 + n_main_helpers), 1362-1364 (run_main_help(q_batches, 1 + i, "
                  "n_workers)); Note [Plugin-owned worker launch] model.hpp:1798"))

    o.append(text(X2 + W2 / 2, 118, "entry points, model.hpp", 10.5, "middle",
                  weight=700))
    o1y, o1h = 126, 140
    o.append(sig_cell(X2, o1y, W2, o1h, "save_k<geometry, operation_ix>",
                      ["Store the K rows of the minibatch. Called by the generated",
                       "plugins: attentionRuntimeCall emits <geometry, operation_ix>."],
                      ["void save_k(batch* q_batch, kv_buffer_t& ks,",
                       "    size_t worker_ix = 0, size_t n_workers = 1) noexcept {",
                       "  operation = generated_attention_operation<geometry,",
                       "      operation_ix>(); static_assert(operation.writes_kv);",
                       "  save_k_impl<geometry>(q_batch, operation, ks,",
                       "      worker_ix, n_workers);"],
                      "model.hpp:3394-3403", tag="changed", new_lines=(1, 5)))
    boxes.append(("save_k<geometry, operation_ix> (overload 1)",
                  "model.hpp:3394-3403 (signature 3394-3398, defaults 3397-3398, "
                  "forward 3402)"))
    o2y, o2h = o1y + o1h + 12, 152
    o.append(sig_cell(X2, o2y, W2, o2h, "save_k<geometry>",
                      ["Store the K rows of the minibatch. Takes the operation as an",
                       "attention_operation_descriptor (handwritten plugin, tests)."],
                      ["void save_k(batch* q_batch,",
                       "    attention_operation_descriptor const& operation,",
                       "    kv_buffer_t& ks,",
                       "    size_t worker_ix = 0, size_t n_workers = 1) noexcept {",
                       "  self_attn_state.validate_operation<geometry>(operation);",
                       "  save_k_impl<geometry>(q_batch, operation, ks,",
                       "      worker_ix, n_workers);"],
                      "model.hpp:3405-3413", tag="changed", new_lines=(3, 6)))
    boxes.append(("save_k<geometry> (overload 2, attention_operation_descriptor)",
                  "model.hpp:3405-3413 (signature 3405-3410, defaults 3409-3410, "
                  "forward 3412)"))
    iy, ih = o2y + o2h + 44, 176
    o.append(sig_cell(X2, iy, W2, ih, "save_k_impl<geometry>",
                      ["Every worker of the store calls this (Note [Shared block",
                       "save]): worker 0 is main, 1 .. n_workers - 1 are helpers."],
                      ["void save_k_impl(batch* q_batch,",
                       "    attention_operation_descriptor const& operation,",
                       "    kv_buffer_t& ks,",
                       "    size_t worker_ix, size_t n_workers) noexcept {",
                       "  TRON_ASSERT(worker_ix < n_workers);  // else: abort",
                       "  const bool is_main = worker_ix == 0;",
                       "  const bool shared = k_store_shared(q_batch, n_workers);",
                       "  if (!is_main && !shared) return; // main's alone",
                       "  ... the window protocol (M5), store_k_block (M4)"],
                      "model.hpp:3295-3315", tag="changed", new_lines=(3, 4, 5, 6, 7)))
    boxes.append(("save_k_impl", "model.hpp:3295-3315 (comment 3295-3299, signature "
                  "3300-3305, TRON_ASSERT 3310-3311, is_main / shared / return 3312-3315)"))
    boxes.append(("worker_ix, n_workers (the new parameters)",
                  "model.hpp:3397-3398 and 3409-3410 (defaults), 3304-3305 (save_k_impl); "
                  "Note [Shared block save] model.hpp:3092-3101"))

    ink = C["ink"]
    a_mid = ay + ah / 2
    b_mid = by2 + ah / 2
    o.append(line(X1 + W1, a_mid, BUS, a_mid, ink, 1.3))
    o.append(line(X1 + W1, b_mid, BUS, b_mid, ink, 1.3))
    o.append(line(BUS, a_mid, BUS, b_mid, ink, 1.3))
    o.append(arrow(fid, "ink", [(BUS, (a_mid + b_mid) / 2), (X2 - 2, (a_mid + b_mid) / 2)],
                   ink, 1.3))
    c_mid = cy + ah / 2
    d_mid = dy + dh / 2
    o.append(line(X1 + W1, c_mid, BUS, c_mid, ink, 1.3))
    o.append(line(X1 + W1, d_mid, BUS, d_mid, ink, 1.3))
    o.append(line(BUS, c_mid, BUS, d_mid, ink, 1.3))
    o.append(arrow(fid, "ink", [(BUS, (c_mid + d_mid) / 2), (X2 - 2, (c_mid + d_mid) / 2)],
                   ink, 1.3))

    mx = X2 + 30
    ry = iy - 22
    o.append(line(X2 + W2, o1y + 60, RBUS, o1y + 60, ink, 1.3))
    o.append(line(RBUS, o1y + 60, RBUS, ry, ink, 1.3))
    o.append(line(RBUS, ry, mx, ry, ink, 1.3))
    o.append(arrow(fid, "ink", [(mx, o2y + o2h), (mx, iy - 2)], ink, 1.3))
    o.append(text(mx + 8, iy - 8, "both: save_k_impl(q_batch, operation, ks, worker_ix, "
                  "n_workers)", 8.5, fill=ink, weight=600))

    ey = iy + ih + 26
    o.append(line(20, ey - 10, W - 20, ey - 10, C["line"]))
    o.append(text(20, ey + 6, f"Worked example: n_workers = {N_WORKERS_EXAMPLE} (main + "
                  f"{N_WORKERS_EXAMPLE - 1} helpers): the three calls of one window, "
                  "and the defaults", 11, weight=700))
    rows = [
        (THREADS_EXAMPLE[0], "save_k(q_batch, ks, 0, 3)",
         "is_main; shared (k_store_shared: yes): opens window W (B3 step 2)"),
        (THREADS_EXAMPLE[1], "save_k(q_batch, ks, 1, 3)",
         "not main; shared: waits for opened >= helper_windows[1] (B3)"),
        (THREADS_EXAMPLE[2], "save_k(q_batch, ks, 2, 3)",
         "not main; shared: waits for opened >= helper_windows[2] (B3)"),
        ("[the calling thread]", "save_k(q_batch, operation, kouts)",
         "worker_ix 0, n_workers 1: k_store_shared: no (n_workers is 1);"),
    ]
    ry0 = ey + 26
    o.append(text(20, ry0 - 2, "thread", 8.5, fill=C["muted"]))
    o.append(text(196, ry0 - 2, "the call", 8.5, fill=C["muted"]))
    o.append(text(372, ry0 - 2, "what save_k_impl does with the two arguments", 8.5,
                  fill=C["muted"]))
    yy = ry0 + 14
    for th, call, what in rows:
        o.append(text(20, yy, th, 10, weight=700))
        o.append(text(196, yy, call, 9.5, mono=True))
        _fit(what, 9, W - 20 - 372, False, "example")
        o.append(text(372, yy, what, 9))
        yy += 16
    o.append(text(372, yy, "store_k_block(items[0, n_items)) on the calling thread alone",
                  9))
    o.append(cite(W - 20, yy + 14, "model.hpp:3312-3315, 3329-3339, 3366-3368; "
                  "t_llama_unit.cpp:4042"))
    boxes.append(("n_workers = 3 (worked example: the three calls of one window)",
                  "t_llama_unit.cpp:4042 (n_workers = 3); model.hpp:3312-3315 (is_main, "
                  "shared), 3329-3339 (open / wait for the window), 3328 (n_helpers = "
                  "n_workers - 1)"))
    boxes.append(("worker_ix = 0, n_workers = 1 (the defaults: the calling thread stores "
                  "every row)",
                  "model.hpp:3392-3393 (comment), 3157-3159 (k_store_shared needs "
                  "n_workers > 1), 3366-3368 (unshared store_k_block over items[0, "
                  "n_items))"))
    H = yy + 34
    o.append(text(20, H - 8, "grey = callers in other files (context); bold = the lines "
                  "this PR adds; red dashed = removed; [...] = the thread that runs it.",
                  8.5, fill=C["muted"]))

    cap = ("Updates B2: the caller boxes and the save_k cell of B2, opened up. "
           "Before (red, dashed) overload 1 took the minibatch and the K buffer (its "
           "operation is the template argument operation_ix), and overload 2 took the "
           "minibatch, the operation descriptor and the K buffer. The calling thread "
           "stored every row. After, both overloads gain worker_ix = 0 and n_workers = 1 "
           "(bold lines) and forward them to save_k_impl, which asserts worker_ix < "
           "n_workers, sets is_main and asks k_store_shared. Look at the caller column. "
           "The generated run() passes 0 and n_workers. The generated run_main_help passes "
           "the helper's own worker_ix and n_workers. The handwritten plugin and most "
           "tests pass nothing, and the defaults then keep the store on the calling "
           "thread. The band at the bottom is the worked example: the three calls of one "
           "window with n_workers = 3, and the defaults row.")
    legend = [
        ("gone", "red dashed box, red text: before (removed), the two save_k signatures "
                 "without worker_ix and n_workers, and the removed 'AttentionStmt _ -> []' "
                 "line of the generated run_main_help"),
        ("ctx", "grey box, thin grey outline: a caller in another file: the generated "
                "run() and run_main_help (TronCpp.hs), the handwritten plugin (llama.hpp), "
                "the tests and the test 'three threads' (t_llama_unit.cpp)"),
        ("box", "white box, ink outline: the two save_k overloads and save_k_impl "
                "(model.hpp), and the run() split that sets n_workers; name in bold "
                "monospace, description in sans-serif under it"),
        ("arrow", "ink arrow: a call; the two caller buses into the overload each caller "
                  "uses, and the merged route of both overloads into save_k_impl"),
        ("font_mono", "monospace = a signature, a call or a body line from the code; bold "
                      "monospace = a line this PR adds (worker_ix, n_workers, the three "
                      "checks of save_k_impl)"),
        ("font_sans", "sans-serif = the function comments, the caller notes, the column "
                      "titles, the bracketed thread names, the worked-example rows and "
                      "the key under the rule; grey sans-serif = a note"),
        ("font_cite", "small grey monospace = the lines that define the box (model.hpp, "
                      "TronCpp.hs, llama.hpp, t_llama_unit.cpp: first-last)"),
        ("font_tag_changed", "grey 'changed' = the cell is changed by this PR (both "
                             "overloads and save_k_impl); red 'before (removed)' = the "
                             "removed signatures and the removed run_main_help line"),
    ]
    return figure(fid, W, H, "save_k entry points: worker index and worker count, "
                  "before and after", "".join(o), cap, boxes=boxes, legend=legend)
