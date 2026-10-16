"""Change diagram of unit m5 of the PR 4958 model.hpp page: save_k_impl's window
protocol (open, claim, join) and its join watchdog (head lines 3295-3315
and 3323-3368 of h/tron/models/model.hpp).

Every label is an identifier or a comment phrase of the head file; every
line number is a head line number of b39765ec29. The worked example is the
page's (3 workers = main + 2 helpers, 41 items cut into 3 units).

Layout: the before/after signature at the top, the decision with its three
paths, then the window band (B3's two lanes and the counters column, with
the memory orders on the arrows), the watchdog band under main's join, and
the worked example's counters.
"""
import sys

from svg_helpers import (C, arrow, cite, figure, line, lines, marker_defs,
                         rect, text, text_width)
from base_model import (CRIT, CRIT_SW, MAIN_FILL, N_HELPERS_EXAMPLE,
                        N_UNITS_EXAMPLE, N_WORKERS_EXAMPLE, decision_box,
                        step_box, window_counters)

BASE = ("Updates B3. The two lanes of B3 are redrawn as the three paths one "
        "save_k_impl call can take after the new worker_ix / n_workers "
        "signature: a helper's early return, main's unshared store, the "
        "shared window. B3's one-line join step is expanded into the watchdog "
        "loop with its abort message.")

FID = "model-d5"
W, H = 700, 852

MX, MW = 15, 225
KX, KW = 290, 120
HX, HW = 460, 225

assert N_WORKERS_EXAMPLE == 3 and N_HELPERS_EXAMPLE == 2 and N_UNITS_EXAMPLE == 3
NEXT_UNIT_END = N_UNITS_EXAMPLE + N_WORKERS_EXAMPLE


def _fit(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w:.0f}",
              file=sys.stderr)


def kbox(x, y, w, h, title, sub, ref, stroke=C["ink"]):
    o = [rect(x, y, w, h, "#fff", stroke, 1.2, 4)]
    _fit(title, 9.5, w - 12, True, "kbox title")
    o.append(text(x + 6, y + 13, title, 9.5, mono=True, weight=600))
    for s in sub:
        _fit(s, 8.5, w - 12, False, "kbox sub")
    o.append(lines(x + 6, y + 25, sub, 8.5, 11))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def cbox(x, y, w, h, title, sub, ref, fill="#fff", stroke=C["ink"]):
    o = [rect(x, y, w, h, fill, stroke, 1.2, 4)]
    _fit(title, 9.5, w - 12, True, "cbox title")
    o.append(text(x + 6, y + 13, title, 9.5, mono=True, weight=600))
    for s in sub:
        _fit(s, 8.5, w - 12, False, "cbox sub")
    o.append(lines(x + 6, y + 25, sub, 8.5, 11))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def sbox(x, y, w, h, title, sub, ref, num=None, dash=None, stroke=C["ink"],
         fill="#fff", crit=False):
    _fit(title, 10.5, w - (58 if num is not None else 16), True, "step title")
    for s in sub:
        _fit(s, 9, w - 16, False, "step sub")
    return step_box(x, y, w, h, title, sub, ref, fill=fill, stroke=stroke,
                    dash=dash, num=num, sw=CRIT_SW if crit else None)


def lab(x, y, s, col=C["ink"], anchor="middle"):
    return text(x, y, s, 8.5, anchor, fill=col, weight=700)


def fig():
    ink, red, new, unit = C["ink"], C["gone"], C["new"], C["unit"]
    o = [marker_defs(FID, {"ink": ink, "unit": unit})]
    boxes = []

    o.append(text(15, 16, "save_k_impl: the three paths of one call, the window "
                  "protocol and the join watchdog", 11.5, weight=700))

    by, bh = 26, 68
    bx, bw = 15, 320
    o.append(rect(bx, by, bw, bh, "#fff", red, 1.4, 5, "6 3"))
    o.append(text(bx + 8, by + 15, "save_k_impl(q_batch, operation, ks)", 10,
                  mono=True, weight=700, fill=red))
    o.append(lines(bx + 8, by + 29, ["one thread: the caller stored every row inside",
                                     "the marks loop (set_k_row per token and KV",
                                     "head, the scatter), then marked the tokens"],
                   9, 11, fill=C["muted"]))
    o.append(text(bx + 8, by + bh - 6, "before (removed)", 9, fill=red, weight=700))
    o.append(cite(bx + bw - 4, by + bh - 4, "base model.hpp:3073-3076; 3096-3116"))
    boxes.append(("save_k_impl (before: q_batch, operation, ks; the K store inside "
                  "the marks loop)",
                  "model.hpp:3300-3305 (the head signature; the base one had no "
                  "worker_ix, n_workers: base model.hpp:3073-3076); the removed per-token "
                  "store sat before head line 3376 (base model.hpp:3096-3116)"))
    ax, aw = 365, 320
    o.append(arrow(FID, "ink", [(bx + bw + 2, by + bh / 2), (ax - 2, by + bh / 2)],
                   ink, 1.4))
    o.append(rect(ax, by, aw, bh, "#fff", new, 1.4, 5))
    o.append(text(ax + 8, by + 15, "save_k_impl(..., worker_ix, n_workers)", 10,
                  mono=True, weight=700))
    o.append(lines(ax + 8, by + 29, ["TRON_ASSERT(worker_ix < n_workers)",
                                     "worker 0 = main; 1 .. n_workers - 1 = main helpers",
                                     "every worker of the store calls this"],
                   9, 11))
    o.append(text(ax + 8, by + bh - 6, "new", 9, fill=new, weight=700))
    o.append(cite(ax + aw - 4, by + bh - 4, "model.hpp:3300-3311"))
    boxes.append(("save_k_impl(..., worker_ix, n_workers)", "model.hpp:3295-3311"))

    dy, dh = 110, 64
    dx, dw = 200, 300
    o.append(decision_box(dx, dy, dw, dh, "is_main? shared?",
                          ["is_main = worker_ix == 0",
                           "shared = k_store_shared(q_batch, n_workers)"],
                          "model.hpp:3312-3313"))
    boxes.append(("is_main, shared (the decision)", "model.hpp:3312-3313"))
    boxes.append(("k_store_shared(q_batch, n_workers)", "model.hpp:3152-3153; 3313"))
    rx, rw, ry, rh = 15, 125, 114, 68
    o.append(rect(rx, ry, rw, rh, "#fff", ink, 1.2, 4))
    o.append(text(rx + 8, ry + 15, "return", 10, mono=True, weight=700))
    o.append(lines(rx + 8, ry + 28, ["[helper] an unshared", "store is main's alone"],
                   9, 11))
    o.append(cite(rx + rw - 4, ry + rh - 4, "model.hpp:3314-3315"))
    boxes.append(("return (a helper of an unshared store)", "model.hpp:3314-3315"))
    o.append(arrow(FID, "ink", [(dx - 2, 150), (rx + rw + 2, 150)], ink, 1.4))
    o.append(lab(170, 128, "!is_main"))
    o.append(lab(170, 139, "&& !shared"))
    ux, uw = 560, 125
    o.append(rect(ux, ry, uw, rh, "#fff", ink, 1.2, 4))
    o.append(text(ux + 8, ry + 15, "store_k_block", 10, mono=True, weight=700))
    o.append(lines(ux + 8, ry + 28, ["stores the K rows of", "items[0, n_items);",
                                     "[main] alone, one call"], 9, 11))
    o.append(cite(ux + uw - 4, ry + rh - 4, "model.hpp:3366-3368"))
    boxes.append(("store_k_block(q_batch, slot, ks, 0, n_items) (unshared: main alone)",
                  "model.hpp:3366-3368"))
    o.append(arrow(FID, "ink", [(dx + dw + 2, 150), (ux - 2, 150)], ink, 1.4))
    o.append(lab(530, 128, "is_main"))
    o.append(lab(530, 139, "&& !shared"))
    o.append(arrow(FID, "ink", [(350, dy + dh + 1), (350, 196)], ink, 1.4))
    o.append(lab(358, 190, "shared: both sides enter the window", anchor="start"))

    hy = 198
    for x, w, s, mono in ((MX, MW, "[main, worker_ix 0]", False),
                          (KX, KW, "k_store_window", True),
                          (HX, HW, "[helper, worker_ix 1 .. n_workers - 1]", False)):
        o.append(rect(x, hy, w, 24, C["soft"], C["line"], 1, 4))
        _fit(s, 10, w - 8, mono, "header")
        o.append(text(x + w / 2, hy + 16, s, 10, "middle", mono, weight=700))
    boxes.append(("[main, worker_ix 0]", "model.hpp:3295-3297, 3312"))
    boxes.append(("[helper, worker_ix 1 .. n_workers - 1]", "model.hpp:3298-3299"))
    boxes.append(("k_store_window (batch::k_store_window_t)",
                  "common.hpp:1193-1219; model.hpp:3327"))

    y1 = 232
    o.append(sbox(MX, y1, MW, 82, "open the window",
                  ["k_store_cut_units(q_batch)",
                   "next_unit.store(0, relaxed)",
                   "finished.store(0, relaxed)",
                   "opened.fetch_add(1, release)"],
                  "model.hpp:3329-3333", num=2, crit=True))
    boxes.append(("open the window: k_store_cut_units, the two relaxed resets, "
                  "opened.fetch_add(1, release) (step 2, main)", "model.hpp:3329-3333"))
    o.append(sbox(HX, y1, HW, 82, "wait for the window",
                  ["my_window = ++helper_windows[worker_ix]",
                   "while (opened.load(acquire) < my_window)",
                   "    _mm_pause()",
                   "the W-th call waits for the W-th window"],
                  "model.hpp:3334-3339", num=2, dash="5 3"))
    boxes.append(("my_window = ++helper_windows[worker_ix]; wait until opened >= "
                  "my_window (step 2, helper)", "model.hpp:3334-3339"))
    o.append(kbox(KX, y1, KW, 40, "helper_windows", ["W - 1 -> W, plain ++"],
                  "common.hpp:1218"))
    boxes.append(("helper_windows[worker_ix]", "common.hpp:1216-1218; model.hpp:3335"))
    o.append(kbox(KX, y1 + 46, KW, 40, "opened", ["W - 1 -> W"], "common.hpp:1204"))
    boxes.append(("opened", "common.hpp:1203-1204; model.hpp:3333, 3336"))
    o.append(arrow(FID, "ink", [(HX - 2, y1 + 20), (KX + KW + 2, y1 + 20)], ink, 1.3))
    o.append(lab(435, y1 + 15, "++"))
    o.append(arrow(FID, "ink", [(MX + MW + 2, y1 + 66), (KX - 2, y1 + 66)], ink, 1.3))
    o.append(lab(265, y1 + 60, "release"))
    o.append(arrow(FID, "ink", [(KX + KW + 2, y1 + 66), (HX - 2, y1 + 66)], ink, 1.3))
    o.append(lab(435, y1 + 60, "acquire"))

    y2 = 328
    claim = ["u = next_unit.fetch_add(1, acq_rel)",
             "if (u >= n_units) break",
             "store_k_block(q_batch, slot, ks,",
             "    unit_start[u], unit_start[u + 1])"]
    o.append(sbox(MX, y2, MW, 82, "claim loop", claim, "model.hpp:3340-3346", num=3))
    o.append(sbox(HX, y2, HW, 82, "claim loop (the same)", claim,
                  "model.hpp:3340-3346", num=3))
    boxes.append(("next_unit.fetch_add(1, acq_rel), then store_k_block per claimed "
                  "unit (the claim loop, step 3, every thread)", "model.hpp:3340-3346"))
    o.append(kbox(KX, y2 + 15, KW, 52, "next_unit",
                  [f"0 -> 1 -> 2 -> {N_UNITS_EXAMPLE},", f"then 3 failing -> {NEXT_UNIT_END}"],
                  "common.hpp:1202", stroke=unit))
    boxes.append(("next_unit", "common.hpp:1200-1202; model.hpp:3331, 3342"))
    o.append(arrow(FID, "unit", [(MX + MW + 2, y2 + 41), (KX - 2, y2 + 41)], unit, 1.3))
    o.append(lab(265, y2 + 35, "fetch_add", unit))
    o.append(lab(265, y2 + 54, "acq_rel", unit))
    o.append(arrow(FID, "unit", [(HX - 2, y2 + 41), (KX + KW + 2, y2 + 41)], unit, 1.3))
    o.append(lab(435, y2 + 35, "fetch_add", unit))
    o.append(lab(435, y2 + 54, "acq_rel", unit))

    y3 = 424
    o.append(sbox(HX, y3, HW, 46, "finished.fetch_add",
                  ["finished.fetch_add(1, release); return"],
                  "model.hpp:3347-3350", num=4))
    boxes.append(("finished.fetch_add(1, release); return (step 4, helper)",
                  "model.hpp:3347-3350"))
    o.append(sbox(MX, y3, MW, 66, "join (waits)",
                  ["while (finished.load(acquire)",
                   "       < n_helpers) _mm_pause()",
                   "n_helpers = n_workers - 1"],
                  "model.hpp:3351-3365", num=5, dash="5 3", crit=True))
    boxes.append(("finished.load(acquire) < n_helpers: the join loop (step 5, main)",
                  "model.hpp:3351-3365"))
    boxes.append(("n_helpers = n_workers - 1", "model.hpp:3328"))
    o.append(kbox(KX, y3 + 8, KW, 52, "finished",
                  [f"0 -> 1 -> {N_HELPERS_EXAMPLE}", f"= n_helpers ({N_HELPERS_EXAMPLE})"],
                  "common.hpp:1205"))
    boxes.append(("finished", "common.hpp:1205; model.hpp:3332, 3348, 3353"))
    o.append(arrow(FID, "ink", [(HX - 2, y3 + 23), (KX + KW + 2, y3 + 23)], ink, 1.3))
    o.append(lab(435, y3 + 17, "release"))
    o.append(arrow(FID, "ink", [(KX - 2, y3 + 34), (MX + MW + 2, y3 + 34)], ink, 1.3))
    o.append(lab(265, y3 + 28, "acquire"))
    sy = y3 + 56
    o.append(line(HX + 26, y3 + 46, HX + 26, sy, C["muted"], 1))
    o.append(rect(HX, sy, HW, 48, "#fff", ink, 1.2, 4, "5 3"))
    o.append(text(HX + 8, sy + 15, "run_main_help (idle)", 10, mono=True, weight=600))
    o.append(text(HX + 8, sy + 29, "its next kernel waits for the attention output", 9))
    o.append(cite(HX + HW - 4, sy + 44, "model.hpp:3092-3094"))
    boxes.append(("run_main_help (idle after the return)", "model.hpp:3092-3094"))

    wy, wh = 532, 132
    o.append(arrow(FID, "ink", [(70, y3 + 66 + 1), (70, wy - 2)], ink, 1.4, "5 3"))
    o.append(text(78, 506, "++spins on every", 8.5, fill=ink, weight=700))
    o.append(text(78, 517, "_mm_pause() of the join", 8.5, fill=ink, weight=700))
    o.append(rect(15, wy, 670, wh, "#fff", ink, 1.3, 5))
    o.append(text(23, wy + 15, "the join watchdog [main]: one clock read every "
                  "k_join_clock_spins pause loops", 10, weight=700))
    o.append(text(685 - 8, wy + 15, "new", 9, "end", fill=new, weight=700))
    o.append(cite(685 - 4, wy + wh - 4, "model.hpp:3351-3365"))
    boxes.append(("k_join_clock_spins, k_join_timeout_s", "model.hpp:3142-3148"))
    cy, ch = wy + 24, 52
    o.append(cbox(25, cy, 200, ch, "++spins",
                  ["(spins & (k_join_clock_spins - 1))",
                   "== 0: once every 2^20 pause loops"], "model.hpp:3355"))
    boxes.append(("spins, (++spins & (k_join_clock_spins - 1)) == 0",
                  "model.hpp:3351, 3355"))
    o.append(cbox(255, cy, 200, ch, "now = steady_clock::now()",
                  ["if (t0 == time_point{}) t0 = now",
                   "t0 = the first clock read"], "model.hpp:3356-3357"))
    boxes.append(("now = steady_clock::now(); t0 = the first clock read",
                  "model.hpp:3356-3357"))
    o.append(cbox(485, cy, 190, ch, "TRON_ASSERT",
                  ["now - t0 < seconds(k_join_timeout_s)",
                   "false after 120 s: abort, message:"], "model.hpp:3358-3363",
                  fill=C["soft"]))
    boxes.append(("TRON_ASSERT(now - t0 < seconds(k_join_timeout_s)) and its message",
                  "model.hpp:3358-3363"))
    o.append(arrow(FID, "ink", [(225, cy + 26), (253, cy + 26)], ink, 1.3))
    o.append(lab(239, cy + 20, "== 0"))
    o.append(arrow(FID, "ink", [(455, cy + 26), (483, cy + 26)], ink, 1.3))
    o.append(lab(469, cy + 20, "then"))
    my = cy + ch + 14
    msg = ['"save_k: the K store window did not close in {120} s ({finished} of '
           '{n_helpers} helpers finished,',
           '{min(next_unit, n_units)} of {n_units} units claimed). The helpers\' '
           'save_k calls do not match this one"']
    for s in msg:
        _fit(s, 8.5, 670 - 16, False, "message")
    o.append(lines(23, my, msg, 8.5, 11, fill=C["muted"]))
    consts = ("k_join_clock_spins = 1048576 (2^20, a power of two: the check masks "
              "with it); k_join_timeout_s = 120 (seconds)")
    _fit(consts, 8.5, 670 - 16 - 100, False, "constants")
    o.append(text(23, my + 26, consts, 8.5))
    o.append(cite(685 - 4, my + 26, "model.hpp:3142-3148"))

    ey = wy + wh + 18
    o.append(arrow(FID, "ink", [(70, wy + wh + 1), (70, ey - 2)], ink, 1.4))
    o.append(text(78, ey - 5, "finished >= n_helpers: the join returns", 8.5, fill=ink,
                  weight=700))
    o.append(rect(MX, ey, 300, 40, MAIN_FILL, CRIT, CRIT_SW, 4))
    o.append(lines(MX + 8, ey + 15, ["the marks, the credits and the latches (M6):",
                                     "B3 steps 6-7, main only; no row store here"],
                   9, 11))
    o.append(cite(MX + 300 - 4, ey + 36, "model.hpp:3369-3385"))
    boxes.append(("the marks, the credits and the latches (after the join, main only; "
                  "B3 steps 6-7)", "model.hpp:3369-3385, 3127-3128"))

    xy = ey + 58
    o.append(text(15, xy, f"worked example: {N_WORKERS_EXAMPLE} workers (main + "
                  f"{N_HELPERS_EXAMPLE} helpers), 41 items, n_units = {N_UNITS_EXAMPLE}; "
                  "the counters after main's join returned", 10, weight=700))
    ctr, ce = window_counters(15, xy + 10, [
        ("next_unit", f"0 -> {N_UNITS_EXAMPLE} -> {NEXT_UNIT_END}", unit),
        ("finished", f"0 -> {N_HELPERS_EXAMPLE}", ink),
        ("opened", "W - 1 -> W", ink),
        ("n_helpers", str(N_HELPERS_EXAMPLE), ink),
        ("n_units", str(N_UNITS_EXAMPLE), ink)], w=100)
    o.append(ctr)
    o.append(text(ce + 10, xy + 22, f"{NEXT_UNIT_END} = {N_UNITS_EXAMPLE} claims +", 8.5))
    o.append(text(ce + 10, xy + 33, f"{N_WORKERS_EXAMPLE} failing claims", 8.5))
    o.append(cite(685, xy + 52, "model.hpp:3328, 3340-3343"))
    boxes.append((f"n_units = {N_UNITS_EXAMPLE}, next_unit 0 -> {N_UNITS_EXAMPLE} -> "
                  f"{NEXT_UNIT_END}, finished 0 -> {N_HELPERS_EXAMPLE} (worked example)",
                  "model.hpp:3340-3343; 3328"))

    ly = xy + 68
    o.append(lines(15, ly, ["red dashed box = before (removed); bold new = added; dashed "
                            "step = a thread waits (spin with _mm_pause);",
                            "thick red frame = main's serial part (the critical path of B4); "
                            "[...] = the thread; arrow labels = memory orders."],
                   9, 12, fill=C["muted"]))

    cap = ("Updates B3: the three paths one save_k_impl call can take after the new "
           "worker_ix / n_workers signature, and the join watchdog that B3 names in one "
           "line. The top row contrasts the old three-argument signature (before, "
           "removed: one thread stored every row inside the marks loop) with the new "
           "one and its TRON_ASSERT. The decision is_main / shared sends a helper of an "
           "unshared store back at once, sends main of an unshared store to one "
           "store_k_block call over items[0, n_items), and sends both sides of a shared "
           "store into the window band, which is B3's two lanes with their memory "
           "orders (release / acquire on opened, fetch_add acq_rel on next_unit, "
           "release / acquire on finished). The watchdog band shows what main does "
           "inside its join loop: a clock read once every 2^20 pause loops, t0 at the "
           "first read, and the abort after 120 s with the finished and claimed "
           "counters in the message. The strip at the bottom is the worked example "
           "(3 workers, 3 units): next_unit ends at 6, finished at 2 = n_helpers.")
    legend = [
        ("gone", "red dashed box: before (removed): the base signature "
                 "save_k_impl(q_batch, operation, ks); one thread stored every row "
                 "inside the marks loop"),
        ("box", "white box, ink outline: the new signature save_k_impl(..., worker_ix, "
                "n_workers), the decision is_main? shared?, the two unshared paths "
                "(return, store_k_block), the steps open the window / claim loop / "
                "finished.fetch_add, the counters helper_windows, opened and finished "
                "of k_store_window, the watchdog band with ++spins and now = "
                "steady_clock::now(), the worked example's counters; the name in bold "
                "monospace, the lines under it in sans-serif"),
        ("ctx", "grey fill, light grey outline: the three lane headers (main, the window, "
                "the helpers)"),
        ("solid ink badge: the B3 step number of a protocol step (step 2 to step 5)",
         C["ink"], C["ink"], False, False),
        ("idle", "dashed ink outline: a thread waits or is idle: the helper's wait for "
                 "the window and main's join (both spin with _mm_pause), run_main_help "
                 "after the helper's return"),
        ("crit", "thick solid red frame: main's serial part, the critical path of B4: "
                 "open the window (step 2) and join (step 5)"),
        ("grey fill, thick red frame: main's serial part after the join: the marks, "
         "the credits and the latches (B3 steps 6-7, main only)",
         C["soft"], C["crit"], False, True),
        ("ctx_ink", "grey fill, ink outline: TRON_ASSERT, the abort of the watchdog "
                    "after k_join_timeout_s"),
        ("white box, grey-blue outline: next_unit, the claim counter of "
         "batch::k_store_window_t, in the window band and in the worked example; "
         "grey-blue text = its name there and fetch_add / acq_rel on its arrows",
         "#fff", C["unit"], False, False),
        ("arrow", "ink arrow: the before -> after signature, the three paths out of the "
                  "decision, the counter updates with their memory orders (++, release, "
                  "acquire), the watchdog chain (== 0, then), main's way from the join "
                  "into the watchdog (dashed) and out of it"),
        ("grey-blue arrow: next_unit.fetch_add(1, acq_rel), the claim of a unit from "
         "either lane", "arrow", C["unit"]),
        ("thin grey line: the helper's return from step 4 into run_main_help (idle)",
         "line", C["muted"]),
        ("font_mono", "monospace = an identifier or a value from the code: the two "
                      "signatures, the box names, the decision's tests, the code lines "
                      "of the steps, the counter names and values, k_store_window"),
        ("font_sans", "sans-serif = prose: the descriptions under the names, the path "
                      "conditions and memory orders on the arrows (bold), the lane "
                      "headers, the watchdog message and constants, the key under the "
                      "figure; grey sans-serif = a note"),
        ("font_cite", "small grey monospace = the line that defines the box "
                      "(model.hpp:line, common.hpp:line; base model.hpp:line for the "
                      "removed signature)"),
        ("font_tag", "bold 'new' = added by this PR (the signature, the join watchdog); "
                     "red 'before (removed)' = the base signature"),
    ]
    return figure(FID, W, H, "save_k_impl: the three paths, the window protocol and "
                  "the join watchdog", "".join(o), cap, boxes=boxes, legend=legend)
