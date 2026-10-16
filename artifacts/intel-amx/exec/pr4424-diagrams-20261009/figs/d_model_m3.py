"""Change diagram of unit m3 (model.hpp): k_store_cut_units, the cut of the
minibatch's items into the work units of the K store window.

Updates B1: B1 shows the unit table of the worked example as a result
(unit_start {0, 16, 32, 40}, n_units 3, the "work unit u" box); this figure
opens the function that computes it: the (kv, pg, block) key of every item,
the test that starts a unit, the sentinel and n_units written last, the
assert on the table size, and the release on opened that publishes the
table to the helpers.

Every label is an identifier or a comment phrase of model.hpp (head line
numbers) or of common.hpp / kv_cache.hpp of the same PR. Facts come from
facts/model.json (model-function-7, model-data-11/12/15/16, model-data-28/
30/32/33/35, model-seq-12, model-rule-5) and the cited head lines.
"""
from svg_helpers import (C, arrow, cite, figure, label_box, line, lines,
                         marker_defs, rect, text, text_width)
from base_model import (N_ITEMS_EXAMPLE, N_UNITS_EXAMPLE, UNIT_START_EXAMPLE,
                        UNITS_EXAMPLE, decision_box, item_strip, step_box)

BASE = ("Updates B1. It opens the unit_start table of B1's worked example into the "
        "walk that k_store_cut_units makes over the items: the (kv, pg, block) key "
        "of each item, the test that starts a unit, the end sentinel and n_units "
        "written last. It adds the TRON_ASSERT on the table size and the release on "
        "opened that publishes the table to the helpers.")

FID = "model-d3"
W, H = 700, 792

ink = C["ink"]


def _w(s, size, mono=False):
    return text_width(s, size, mono)


def badge(x, y, label):
    """The step badge of step_box, drawn alone (for a panel header)."""
    bw = max(36, _w(label, 8.5) + 10)
    return (rect(x, y, bw, 14, ink, ink, 1, 3) +
            text(x + bw / 2, y + 10.5, label, 8.5, "middle", fill="#fff", weight=700))


def unit_cell(x, y, i, v, w=44, h=22):
    """One unit_start entry in the style of base_model.unit_table."""
    o = [rect(x, y, w, h, C["unit_fill"], C["unit"], 1, 2)]
    o.append(text(x + w / 2, y + 15, str(v), 10.5, "middle", True, weight=600))
    o.append(text(x + w / 2, y - 5, f"[{i}]", 8.5, "middle", True, fill=C["muted"]))
    return "".join(o)


def mini(x, y, w, h, name, sub, ref, fill="#fff", stroke=ink, size=9.5):
    """A small cell: a mono name, one small sub line, the citation."""
    o = [rect(x, y, w, h, fill, stroke, 1.2, 3)]
    o.append(text(x + 6, y + 13, name, size, mono=True, weight=600))
    if sub:
        o.append(text(x + 6, y + 25, sub, 8.5, fill=C["muted"]))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fig():
    assert UNIT_START_EXAMPLE == [0, 16, 32, 40] and N_UNITS_EXAMPLE == 3
    assert N_ITEMS_EXAMPLE == 40
    o = [marker_defs(FID, {"ink": ink, "unit": C["unit"], "muted": C["muted"]})]
    boxes = []

    # ---- title ---------------------------------------------------------------
    o.append(text(12, 16, "k_store_cut_units: one walk over q_batch->items; a new unit at "
                  "every change of (kv, pg, block)", 11.5, weight=600))
    o.append(text(12, 31, "[main, worker_ix 0] only, before it opens the window; writes "
                  "k_store_window.unit_start and n_units", 9.5, fill=C["muted"]))
    o.append(cite(688, 31, "model.hpp:3202-3204"))
    boxes.append(("k_store_cut_units [main, worker_ix 0]",
                  "model.hpp:3202-3204 (comment and signature); 3381 (the one caller)"))

    # ---- step 1: the assert --------------------------------------------------
    o.append(step_box(12, 42, 676, 58, "TRON_ASSERT(n_items + 1 <= w.unit_start.size(), ...)",
                      ["n_items = q_batch->items.size(); unit_start.size() = "
                       "max_minibatch_size + 1 entries [common.hpp:1189]",
                       "when false the process aborts: \"save_k: {} items exceed the K store "
                       "window's unit table\""],
                      "model.hpp:3207-3209", num=1))
    boxes.append(("TRON_ASSERT(n_items + 1 <= w.unit_start.size(), ...)",
                  "model.hpp:3207-3209; common.hpp:1189 (unit_start has max_minibatch_size "
                  "+ 1 entries)"))

    # ---- step 2: the loop ----------------------------------------------------
    P0, P1 = 110, 358
    o.append(rect(12, P0, 676, P1 - P0, C["soft"], C["line"], 1, 4))
    o.append(badge(20, P0 + 5, "step 2"))
    o.append(text(62, P0 + 15, "for (size_t t = 0; t < n_items; ++t)", 10.5, mono=True,
                  weight=600))
    o.append(text(300, P0 + 15, "one walk over the items, no new unit -> the next t", 9.5,
                  fill=C["muted"]))
    o.append(cite(684, P0 + 15, "model.hpp:3214-3227"))
    boxes.append(("for (size_t t = 0; t < n_items; ++t)", "model.hpp:3214-3227"))

    # column A: the item
    AY = P0 + 54
    o.append(label_box(24, AY, 110, 56, "items[t]", ["ix (token_job_id)"], "#fff", ink,
                       11.5, ref="model.hpp:3215"))
    boxes.append(("items[t] -> ix", "model.hpp:3215; common.hpp:1084-1085 (items)"))
    o.append(text(79, AY + 70, "1 item -> 1 ix", 9, "middle", fill=ink, weight=600))
    o.append(text(79, AY + 82, "-> 1 kv, 1 pg, 1 block", 9, "middle", fill=ink, weight=600))
    o.append(cite(132, AY + 94, "model.hpp:3215-3220"))

    # column B: the three parts of the key
    BX, BW = 160, 216
    BY = [P0 + 28, P0 + 80, P0 + 132]
    bh = 46
    o.append(label_box(BX, BY[0], BW, bh, "token_jobs_do_kv[ix] != 0",
                       ["kv (bool): 1 = the job needs KV work"], "#fff", ink, 11,
                       ref="model.hpp:3216; 1160"))
    boxes.append(("token_jobs_do_kv[ix] != 0 -> kv", "model.hpp:3216; 1160 (member); 1700"))
    o.append(label_box(BX, BY[1], BW, bh, "page_of(token_jobs[ix])",
                       ["pg (const page*): the token's page"], "#fff", ink, 11,
                       ref="model.hpp:3217; 1773"))
    boxes.append(("page_of(token_jobs[ix]) -> pg", "model.hpp:3217; 1773 (page_of)"))
    o.append(label_box(BX, BY[2], BW, bh, "offset_in_page / k_store_block",
                       ["block (size_t): c = j / 16, 0 .. 3"], "#fff", ink, 11,
                       ref="model.hpp:3218-3220; kv_cache.hpp:2031"))
    boxes.append(("offset_in_page / k_store_block -> block",
                  "model.hpp:3218-3220; kv_cache.hpp:2031 (offset_in_page); model.hpp:3153 "
                  "(k_store_block = 16)"))
    # the bus from items[t] to the three boxes
    ay = AY + 28
    o.append(line(134, ay, 148, ay, ink, 1.3))
    o.append(line(148, BY[0] + bh / 2, 148, BY[2] + bh / 2, ink, 1.3))
    for y in BY:
        o.append(arrow(FID, "ink", [(148, y + bh / 2), (BX - 2, y + bh / 2)], ink, 1.3))

    # the kv == false case (items without KV work)
    KY = P0 + 190
    o.append(rect(BX, KY, BW, 58, C["empty_fill"], C["empty"], 1.2, 4, "4 3"))
    o.append(text(BX + 8, KY + 14, "kv false: pg = nullptr, block = 0", 10, mono=True,
                  weight=600))
    o.append(lines(BX + 8, KY + 27, ["a unit of its own; store_k_block skips",
                                     "every item of it [3254, 3273-3276]"], 9, 11,
                   fill=C["muted"]))
    o.append(cite(BX + BW - 4, KY + 54, "model.hpp:3217-3220"))
    boxes.append(("kv false: pg = nullptr, block = 0 (a unit of its own)",
                  "model.hpp:3217-3220; store_k_block skips those items at 3254, 3273-3276"))

    # column C: the test
    DX, DW = 436, 252
    DY = P0 + 28
    o.append(decision_box(DX, DY, DW, 136, "new unit?",
                          ["t == 0", "|| kv != run_kv", "|| pg != run_page",
                           "|| block != run_block"], "model.hpp:3221"))
    boxes.append(("run_kv, run_page, run_block: new unit? (t == 0 || kv != run_kv || pg != run_page || block != run_block)",
                  "model.hpp:3221; run_kv, run_page, run_block declared at 3211-3213"))
    for y, lab in zip(BY, ["kv", "pg", "block"]):
        cy = y + bh / 2
        o.append(arrow(FID, "ink", [(BX + BW, cy), (DX - 2, cy)], ink, 1.3))
        o.append(text((BX + BW + DX) / 2, cy - 5, lab, 9, "middle", True, fill=ink,
                      weight=700))
        o.append(text((BX + BW + DX) / 2, cy + 13, "1 per item", 8.5, "middle",
                      fill=C["muted"]))
    # yes -> write the unit start and remember the key
    RY = P0 + 190
    o.append(arrow(FID, "ink", [(DX + DW / 2, DY + 136), (DX + DW / 2, RY - 2)], ink, 1.3))
    o.append(text(DX + DW / 2 + 8, RY - 12, "yes", 9, fill=ink, weight=700))
    o.append(label_box(DX, RY, DW, 50, "unit_start[n_units++] = t",
                       ["run_kv, run_page, run_block = kv, pg, block"], C["unit_fill"],
                       C["unit"], 11, ref="model.hpp:3222-3225"))
    boxes.append(("unit_start[n_units++] = t; run_kv, run_page, run_block = kv, pg, block",
                  "model.hpp:3222-3225"))

    # ---- step 3: the sentinel and n_units ------------------------------------
    S3 = P1 + 10
    o.append(step_box(12, S3, 676, 46, "w.unit_start[n_units] = n_items;   w.n_units = n_units;",
                      ["after the loop: entry n_units holds n_items as the end sentinel; "
                       "n_units is written last"],
                      "model.hpp:3228-3229", num=3))
    boxes.append(("w.unit_start[n_units] = n_items; w.n_units = n_units", "model.hpp:3228-3229"))

    # ---- worked example ------------------------------------------------------
    E0 = S3 + 56
    EH = 198
    o.append(rect(12, E0, 676, EH, "#fff", C["line"], 1, 4))
    o.append(text(20, E0 + 16, "Worked example: 40 items; user A at page 7 offsets 0..31, "
                  "user B at page 9 offsets 32..39", 10.5, weight=700))
    o.append(cite(684, E0 + 16, "STYLE.md worked example"))
    boxes.append(("unit_start (worked example: the items strip)",
                  "STYLE.md worked example; model.hpp:3222 (the three starts), 3228 (the "
                  "sentinel)"))
    SY = E0 + 42
    strip, xe, spans = item_strip(120, SY, cell=12, gap=1, unit_gap=8, h=16)
    o.append(strip)
    o.append(text(112, SY + 12, "items", 10, "end", True, fill=C["muted"]))
    keys = ["(kv true, page 7, block 0)", "(kv true, page 7, block 1)",
            "(kv true, page 9, block 2)"]
    for u, (x0, x1), k in zip(UNITS_EXAMPLE, spans, keys):
        o.append(text((x0 + x1) / 2, SY - 6, k, 9, "middle", fill=C["muted"]))
    # the three unit starts: one arrow per fired test, into unit_start
    TY = SY + 74           # the unit_start cells
    tests = [["t == 0"], ["block != run_block", "(0 -> 1)"], ["pg != run_page", "(page 7 -> 9)"]]
    for u, (x0, x1), tl in zip(UNITS_EXAMPLE, spans, tests):
        cx = x0 + 22
        o.append(arrow(FID, "unit", [(cx, SY + 18), (cx, TY - 16)], C["unit"], 1.4))
        o.append(unit_cell(x0, TY, u["u"], u["begin"]))
        if u["u"] == 2:
            # the label sits left of its arrow (the sentinel's arrow is at the
            # right): a short tick from the label to the arrow attaches it
            lx, anc = cx - 8, "end"
            o.append(line(cx - 7, SY + 46, cx - 1, SY + 46, C["unit"], 1.4))
        else:
            lx, anc = cx + 6, "start"
        o.append(text(cx + 6, SY + 30, f"t = {u['begin']}", 8.5, "start", fill=C["muted"]))
        o.append(lines(lx, SY + 44, tl, 9, 11, anc, fill=C["unit"], weight=700))
        o.append(text(x1, SY + 30, str(u["end"] - 1), 8.5, "end", fill=C["muted"]))
    # the sentinel
    sx = xe - 44
    o.append(unit_cell(sx, TY, N_UNITS_EXAMPLE, N_ITEMS_EXAMPLE))
    o.append(arrow(FID, "muted", [(sx + 22, SY + 18), (sx + 22, TY - 16)], C["muted"], 1.2,
                   dash="4 3"))
    o.append(text(sx + 28, SY + 44, "n_items", 9, fill=C["muted"], weight=700))
    o.append(text(sx + 28, SY + 55, "(step 3)", 9, fill=C["muted"], weight=700))
    o.append(text(112, TY + 15, "unit_start", 10, "end", True, fill=C["unit"], weight=700))
    o.append(lines(20, TY + 42, ["unit_start[0 .. 2] = the t where the test fired (step 2); "
                                 "unit_start[3] = n_items = 40, the end sentinel; n_units = 3 "
                                 "(step 3)",
                                 "n_units + 1 = 4 entries used of max_minibatch_size + 1 "
                                 "[common.hpp:1189]; n_units (3) <= n_items (40): the three "
                                 "units of B1"], 9, 12))
    o.append(cite(684, E0 + EH - 4, "model.hpp:3222, 3228-3229"))

    # ---- then, in save_k_impl: the publish -----------------------------------
    F0 = E0 + EH + 10
    o.append(rect(12, F0, 676, 144, C["soft"], C["line"], 1, 4))
    o.append(badge(20, F0 + 5, "then, in save_k_impl"))
    o.append(text(156, F0 + 15, "the release on opened publishes the table to the helpers "
                  "(unit M5)", 10, weight=700))
    o.append(cite(684, F0 + 15, "model.hpp:3380-3396"))
    MY, HY = F0 + 28, F0 + 98
    o.append(text(20, MY + 24, "[main, worker_ix 0]", 10, weight=700))
    o.append(text(20, HY + 18, "[helper, worker_ix", 10, weight=700))
    o.append(text(20, HY + 30, "1 .. n_workers - 1]", 10, weight=700))
    o.append(mini(150, MY, 150, 40, "k_store_cut_units", "cuts the items into the units",
                  "model.hpp:3381"))
    o.append(mini(312, MY, 190, 40, "next_unit = 0, finished = 0", "relaxed stores",
                  "model.hpp:3382-3383"))
    o.append(mini(514, MY, 174, 40, "opened.fetch_add(1, ...)", "release",
                  "model.hpp:3384"))
    boxes.append(("[main, worker_ix 0]: k_store_cut_units; next_unit = 0, finished = 0 "
                  "(relaxed); opened.fetch_add(1, release)", "model.hpp:3380-3384"))
    o.append(mini(150, HY, 214, 40, "opened.load(acquire) >= my_window", "the helper's wait",
                  "model.hpp:3386-3389"))
    o.append(mini(376, HY, 312, 40, "n_units = w.n_units; unit_start[u], unit_start[u + 1]",
                  "read without a lock, one unit per claim", "model.hpp:3391-3396"))
    boxes.append(("[helper, worker_ix 1 .. n_workers - 1]: opened.load(acquire) >= my_window; "
                  "n_units, unit_start[u], unit_start[u + 1]", "model.hpp:3386-3396"))
    o.append(arrow(FID, "ink", [(300, MY + 20), (310, MY + 20)], ink, 1.3))
    o.append(arrow(FID, "ink", [(502, MY + 20), (512, MY + 20)], ink, 1.3))
    o.append(arrow(FID, "ink", [(364, HY + 20), (374, HY + 20)], ink, 1.3))
    # release -> acquire
    o.append(arrow(FID, "ink", [(601, MY + 40), (601, MY + 56), (257, MY + 56), (257, HY - 2)],
                   ink, 1.3))
    o.append(text(429, MY + 51, "release -> acquire: publishes the table and the zeroed "
                  "counters", 9, "middle", fill=ink, weight=600))

    cap = ("Updates B1: B1 shows the unit table of the worked example as a result "
           "(unit_start {0, 16, 32, 40}, n_units 3); this figure shows how "
           "k_store_cut_units computes it, step by step: the assert on the table size "
           "(step 1), the (kv, pg, block) key of every item and the test that starts a "
           "unit (step 2), the end sentinel and n_units written last (step 3). Look at "
           "the three grey-blue arrows from the item strip into unit_start: each names the "
           "test that fired (t == 0, a block change, a page change), and the dashed "
           "arrow is the sentinel. The bottom panel is context from save_k_impl: only "
           "main runs the cut, and the release on opened publishes the table to the "
           "helpers' acquire. This figure marks nothing as new, changed or removed. "
           "'new unit?' is the question of the decision box.")
    legend = [
        ("solid ink badge: the number of a step (step 1, step 2, step 3) and the "
         "header of the bottom panel (then, in save_k_impl); white bold text",
         C["ink"], C["ink"], False, False),
        ("box", "white box, ink outline: step 1 (the TRON_ASSERT), step 3 (the "
                "sentinel and n_units), items[t], the three parts of its key "
                "(token_jobs_do_kv[ix], page_of(token_jobs[ix]), offset_in_page / "
                "k_store_block), the test 'new unit?', and the five save_k_impl "
                "cells of the bottom panel; name in bold monospace, description in "
                "grey sans-serif"),
        ("ctx", "grey band, light grey outline: the body of the step 2 loop (one item "
                "per pass) and the bottom panel 'then, in save_k_impl'"),
        ("lane", "white box, light grey outline: the worked example (40 items, three "
                 "units)"),
        ("unit", "grey-blue: a work unit of the shared block save: the write "
                 "unit_start[n_units++] = t (step 2), the 40 items of the strip "
                 "grouped by unit, and the unit_start cells [0] .. [3]; grey-blue "
                 "labels name the test that fired and the unit_start row"),
        ("empty", "grey dashed: the kv false case (pg = nullptr, block = 0), a unit "
                  "of its own whose items store_k_block skips"),
        ("arrow", "ink arrow: a step of the walk: items[t] -> the three parts of "
                  "its key, kv / pg / block -> the test (1 per item), yes -> the "
                  "write; in the bottom panel main's three steps and the release -> "
                  "acquire edge to the helper"),
        ("grey-blue arrow: a fired test that starts a unit, from the first item of "
         "the unit into its unit_start entry (t == 0, block != run_block, "
         "pg != run_page)", "arrow", C["unit"]),
        ("arrow_muted", "grey dashed arrow: the end sentinel unit_start[3] = "
                        "n_items = 40, written after the loop (step 3)"),
        ("font_mono", "monospace = an identifier or a value from the code: the box "
                      "names, the loop header, the tests, the unit_start values, "
                      "the save_k_impl cells"),
        ("font_sans", "sans-serif = prose: the descriptions, the how-many labels, "
                      "the item keys over the strip, the thread names [main, "
                      "worker_ix 0] / [helper, worker_ix 1 .. n_workers - 1], the "
                      "notes"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        ("font_cite", "small grey monospace = the line that defines the box "
                      "(file:line)"),
    ]
    return figure(FID, W, H, "k_store_cut_units: the walk over the items that fills "
                  "unit_start and n_units", "".join(o), cap, boxes=boxes, legend=legend)
