"""Change diagram of unit m7 (model.hpp page of PR 4424): the save_k entry
points take a worker index and a worker count.

Head lines 3459-3483: both save_k overloads gain worker_ix = 0 and
n_workers = 1 and forward them to save_k_impl. The callers (generated run(),
generated run_main_help, the handwritten plugin, the tests) come from
ingest/src/TronCpp.hs, llama.hpp and t_llama_unit.cpp of the same PR.

Every label is an identifier or a comment phrase of the code; every box cites
the line that defines it (verified in facts/model.json: model-data-5,
model-data-45, model-function-11, model-function-28).
"""
import sys

from svg_helpers import (C, arrow, cite, figure, line, lines, marker_defs,
                         rect, text, text_width)
from base_model import MAIN_FILL, N_WORKERS_EXAMPLE, THREADS_EXAMPLE

BASE = ("Updates B2. It opens B2's three caller boxes and its save_k cell into the "
        "before and after signatures of the two overloads. It adds the worker "
        "arguments each caller passes (0 and n_workers from the generated run(), "
        "worker_ix and n_workers from the generated run_main_help, the defaults 0 "
        "and 1 from the handwritten plugin and the tests) and the three checks "
        "save_k_impl makes on them.")

FID = "model-d7"
W = 720

# column geometry
X1, W1 = 20, 314        # callers (other files)
X2, W2 = 360, 336       # the entry points and save_k_impl (model.hpp)
BUS = 346               # the x of the caller -> overload bus (in the gap)
RBUS = 708              # the x of the overload 1 -> save_k_impl route


def _fit(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w}", file=sys.stderr)
    return s


def _indented(x, y, s, size, mono, fill=None, weight=None):
    """text() with the leading spaces of s turned into an x offset (SVG
    collapses leading whitespace)."""
    ind = len(s) - len(s.lstrip(" "))
    per = size * (0.60 if mono else 0.55)
    return text(x + ind * per, y, s.lstrip(" "), size, mono=mono, fill=fill,
                weight=weight)


def caller_box(x, y, w, h, ls, ref):
    """A caller in another file (B2 style: grey context cell), text lines at
    9.5 px and the citation in the lower-right corner."""
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
    """A function cell with its signature: name (mono, bold), a description
    from the function's comment (sans 9.5), the signature and body lines
    (mono 9), the lines listed in new_lines in C['new'] (added by the PR),
    a tag at the lower left and the citation at the lower right."""
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
    o = [marker_defs(fid, {"ink": C["ink"], "new": C["new"], "gone": C["gone"]})]
    boxes = []

    # ---- header -----------------------------------------------------------------
    o.append(text(20, 18, "save_k (two overloads): the entry points, before and after",
                  12.5, weight=700))
    o.append(cite(W - 20, 18, "model.hpp:3459-3483"))
    boxes.append(("save_k (two overloads)", "model.hpp:3459-3483 (comment 3459-3463; "
                  "overload 1 at 3464-3473; overload 2 at 3475-3483)"))

    # ---- before: no worker index, no worker count (removed) -----------------------
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
                  "base model.hpp:3119, 3127-3129 (signatures), 3123, 3131 (calls); "
                  "base TronCpp.hs:2877"))
    boxes.append(("save_k(q_batch, ks) / save_k(q_batch, operation, ks) (before, removed)",
                  "replaced at head model.hpp:3464-3483; the removed lines are base "
                  "model.hpp 3119 and 3127-3129 (signatures), 3123 and 3131 (the "
                  "save_k_impl calls), save_k_impl base 3079; diff hunk -3115,20 +3456,30"))
    boxes.append(("'AttentionStmt _ -> []' (before, removed)",
                  "base TronCpp.hs:2877 (runHelperStatement emitted nothing for an "
                  "attention statement); head TronCpp.hs:2878-2895"))

    # ---- before (above) -> after (below) ----------------------------------------
    o.append(text(360, 116, "before -> after: PR 4424", 9, "middle", fill=C["new"],
                  weight=700))

    # ---- column 1: the callers ---------------------------------------------------
    o.append(text(X1 + W1 / 2, 118, "callers (other files)", 10.5, "middle",
                  weight=700))
    ay, ah = 126, 66
    o.append(caller_box(X1, ay, W1, ah,
                        ["generated run() [main, worker_ix 0]:",
                         "save_k<geometry, operation_ix>(",
                         "    q_batch, ks, 0, n_workers)",
                         "worker 0 as in kernelCall; n_workers in scope in run()"],
                        "TronCpp.hs:2949-2958; 2976-2983"))
    boxes.append(("save_k call of the generated run(): save_k(q_batch, ks, 0, n_workers)",
                  "TronCpp.hs:2949-2958 (submitAttentionOperation, saveKv), "
                  "2976-2983 (attentionRuntimeCall emits <geometry, operation_ix>)"))
    by2 = ay + ah + 8
    o.append(caller_box(X1, by2, W1, ah,
                        ["generated run_main_help [helper i, worker_ix 1 + i]:",
                         "save_k<geometry, operation_ix>(",
                         "    q_batch, ks, worker_ix, n_workers)",
                         "only for an operation with a KV write (attentionKvWrite)"],
                        "TronCpp.hs:2878-2895; 1426"))
    boxes.append(("save_k call of the generated run_main_help: save_k(q_batch, ks, "
                  "worker_ix, n_workers)",
                  "TronCpp.hs:2878-2895 (runHelperStatement, AttentionStmt), 1426 "
                  "(runHelpParams: q_batches, worker_ix, n_workers)"))
    cy = by2 + ah + 8
    o.append(caller_box(X1, cy, W1, ah,
                        ["handwritten plugin, most tests [the calling thread]:",
                         "save_k<geometry>(q_batch, operation, kouts)",
                         "no worker arguments: the defaults apply,",
                         "worker_ix 0, n_workers 1 (the store is never shared)"],
                        "llama.hpp:1038-1039; t_llama_unit.cpp:3931"))
    boxes.append(("handwritten plugin and tests: save_k with the defaults",
                  "Note [Shared block save] model.hpp:3114-3116 (the handwritten plugins "
                  "and the unit tests except the shared-save case never share); "
                  "t_llama_unit.cpp:2297, 2300, 3931, 3953, 3973 (calls with the "
                  "defaults); h/tron/plugins/llama.hpp lines 1038-1039 (overload 2 with "
                  "the defaults); t/heterogeneous_scheduler_compile.cpp lines 192, 200, "
                  "208 (overload 1 with the defaults)"))
    dy, dh = cy + ah + 8, 54
    o.append(caller_box(X1, dy, W1, dh,
                        ["test 'three threads' [main + 2 std::thread helpers]:",
                         "save_k<geometry>(q_batch, operation, kouts,",
                         "    worker_ix, n_workers): worker_ix 0..2, n_workers 3"],
                        "t_llama_unit.cpp:3986-3998"))
    boxes.append(("save_k calls of the test 'three threads' (worker_ix 0..2, n_workers 3)",
                  "t_llama_unit.cpp:3982-4007 (n_workers = 3 at 3986, helper calls "
                  "3993-3994, main call 3997-3998)"))

    # the run() split: where n_workers and the helpers' worker_ix come from
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
    o.append(cite(X1 + W1 - 4, sy + sh - 4, "TronCpp.hs:1358-1360, 1379-1388"))
    boxes.append(("n_workers = 1 + n_main_helpers (the run() split, run_main_help launches)",
                  "TronCpp.hs:1379-1388 (workerSplitLines: n_main_helpers, n_workers = "
                  "1 + n_main_helpers), 1358-1360 (run_main_help(q_batches, 1 + i, "
                  "n_workers)); Note [Plugin-owned worker launch] model.hpp:1800-1835"))

    # ---- column 2: the two overloads and save_k_impl ------------------------------
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
                      "model.hpp:3464-3473", tag="changed", new_lines=(1, 5)))
    boxes.append(("save_k<geometry, operation_ix> (overload 1)",
                  "model.hpp:3464-3473 (signature 3464-3468, defaults 3467-3468, "
                  "forward 3472)"))
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
                      "model.hpp:3475-3483", tag="changed", new_lines=(3, 6)))
    boxes.append(("save_k<geometry> (overload 2, attention_operation_descriptor)",
                  "model.hpp:3475-3483 (signature 3475-3480, defaults 3479-3480, "
                  "forward 3482)"))
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
                      "model.hpp:3346-3366", tag="changed", new_lines=(3, 4, 5, 6, 7)))
    boxes.append(("save_k_impl", "model.hpp:3346-3366 (comment 3346-3350, signature "
                  "3351-3356, TRON_ASSERT 3361-3362, is_main / shared / return 3363-3366)"))
    boxes.append(("worker_ix, n_workers (the new parameters)",
                  "model.hpp:3467-3468 and 3479-3480 (defaults), 3355-3356 (save_k_impl); "
                  "Note [Shared block save] model.hpp:3107-3116"))

    # ---- arrows: callers -> overloads --------------------------------------------
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

    # ---- arrows: overloads -> save_k_impl -----------------------------------------
    mx = X2 + 30                      # the merge x of the two routes
    ry = iy - 22                      # the horizontal of overload 1's route
    o.append(line(X2 + W2, o1y + 60, RBUS, o1y + 60, ink, 1.3))
    o.append(line(RBUS, o1y + 60, RBUS, ry, ink, 1.3))
    o.append(line(RBUS, ry, mx, ry, ink, 1.3))
    o.append(arrow(fid, "ink", [(mx, o2y + o2h), (mx, iy - 2)], ink, 1.3))
    o.append(text(mx + 8, iy - 8, "both: save_k_impl(q_batch, operation, ks, worker_ix, "
                  "n_workers)", 8.5, fill=ink, weight=600))

    # ---- worked example: the three calls of one window --------------------------
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
    o.append(cite(W - 20, yy + 14, "model.hpp:3363-3366, 3380-3390, 3417-3418; "
                  "t_llama_unit.cpp:3986"))
    boxes.append(("n_workers = 3 (worked example: the three calls of one window)",
                  "t_llama_unit.cpp:3986 (n_workers = 3); model.hpp:3363-3366 (is_main, "
                  "shared), 3380-3390 (open / wait for the window), 3379 (n_helpers = "
                  "n_workers - 1)"))
    boxes.append(("worker_ix = 0, n_workers = 1 (the defaults: the calling thread stores "
                  "every row)",
                  "model.hpp:3462-3463 (comment), 3196-3198 (k_store_shared needs "
                  "n_workers > 1), 3417-3418 (unshared store_k_block over items[0, "
                  "n_items))"))
    H = yy + 34
    o.append(text(20, H - 8, "grey = callers in other files (context); bold = the lines "
                  "this PR adds; red dashed = removed; [...] = the thread that runs it.",
                  8.5, fill=C["muted"]))

    cap = ("Updates B2: the three caller boxes and the save_k cell of B2, opened up. "
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
                      "the key under the rule"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the lines that define the box (model.hpp, "
                      "TronCpp.hs, llama.hpp, t_llama_unit.cpp: first-last)"),
        ("font_tag_changed", "grey 'changed' = the cell is changed by this PR (both "
                             "overloads and save_k_impl); red 'before (removed)' = the "
                             "removed signatures and the removed run_main_help line"),
    ]
    return figure(fid, W, H, "save_k entry points: worker index and worker count, "
                  "before and after", "".join(o), cap, boxes=boxes, legend=legend)
