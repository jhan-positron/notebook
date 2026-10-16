"""Change diagrams of unit c1 (common.hpp page of PR 4958): the new data model
batch::k_store_window_t and its member k_store_window (head lines 1193-1219).

Two figures: (a) the fields over one forward pass: which ones count across the
pass's windows and which ones are reset per window; (b) the cut of the worked
example's items into unit_start, with the present mask of each unit.
"""
from svg_helpers import C, arrow, card_arrow, cite, figure, label_box, lines, marker_defs, rect, text
from base_common import N_ITEMS, UNITS, UNIT_START, fit, tag, item_strip, unit_table, counters

BASE = ("Updates B1 and B3: the window type is drawn over a whole forward pass (one window per "
        "layer: opened and helper_windows count up, the other fields are reset per window), and "
        "B5's cut is applied to the worked example's 41 items (unit_start and the present masks).")

W = 700


def fig_a():
    fid = "common-d1a"
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"]})]
    boxes = []
    o.append(text(20, 18, "k_store_window over one forward pass: 36 layers -> 36 shared windows", 12,
                  weight=700))
    o.append(text(20, 32, "(qwen3-4b has 36 layers; one save_k window per (layer, pass) in a prefill pass of 41 items)",
                  9, fill=C["muted"]))
    # the pass axis: three windows drawn, dots, the last
    ax, ay = 150, 60
    cols = [("window 1", "layer 0"), ("window 2", "layer 1"), ("...", ""), ("window 36", "layer 35")]
    cw = 120
    for i, (w, l) in enumerate(cols):
        x = ax + i * (cw + 8)
        o.append(rect(x, ay, cw, 30, C["soft"] if w != "..." else "#fff", C["line"], 1, 3))
        o.append(text(x + cw / 2, ay + 13, w, 10, "middle", weight=700))
        if l:
            o.append(text(x + cw / 2, ay + 25, l + ", save_k on 3 threads", 8.5, "middle",
                          fill=C["muted"]))
    o.append(cite(ax + 4 * (cw + 8) - 12, ay + 42, "model.hpp:3077-3078, 3112-3116"))
    boxes.append(("window 1 .. window 36 (one per layer and pass)",
                  "common.hpp:1193-1194 ('one per (layer, pass)'); model.hpp:3112-3116 ('window W of a "
                  "pass is the W-th shared save_k of that pass on both sides')"))
    # rows: fields that count across windows
    rows = [
        ("opened", ["1", "2", "...", "36"], "counts up: main's fetch_add per window; {0} at the batch's start",
         "common.hpp:1203-1204; model.hpp:3333", True),
        ("helper_windows[1]", ["1", "2", "...", "36"], "counts up: the helper's own slot, ++ per call",
         "common.hpp:1216-1218; model.hpp:3335", True),
        ("helper_windows[2]", ["1", "2", "...", "36"], "the same for helper 2 ([0] stays 0: main's slot, unused)",
         "common.hpp:1216-1218; model.hpp:3335", True),
        ("next_unit", ["0 -> 6", "0 -> 6", "...", "0 -> 6"], "reset to 0 by main, then n_units + n_workers claims",
         "common.hpp:1200-1202; model.hpp:3331, 3342", False),
        ("finished", ["0 -> 2", "0 -> 2", "...", "0 -> 2"], "reset to 0 by main, then one fetch_add per helper",
         "common.hpp:1205; model.hpp:3332, 3348", False),
        ("n_units", ["3", "3", "...", "3"], "rewritten by k_store_cut_units: the same items, the same cut",
         "common.hpp:1206; model.hpp:3190", False),
        ("unit_start[0..3]", ["0 16 32 41", "0 16 32 41", "...", "0 16 32 41"],
         "rewritten by k_store_cut_units before each open", "common.hpp:1207-1215; model.hpp:3185-3189", False),
    ]
    y = ay + 54
    for name, vals, desc, ref, mono_up in rows:
        o.append(rect(20, y, 124, 40, C["unit_fill"], C["unit"], 1.1, 3))
        fit(name, 9.5, 116, True, "d1a name")
        o.append(text(26, y + 15, name, 9.5, mono=True, weight=600))
        o.append(text(26, y + 29, "counts up" if mono_up else "per window", 8.5, fill=C["unit"],
                      weight=600))
        for i, v in enumerate(vals):
            x = ax + i * (cw + 8)
            if v == "...":
                o.append(text(x + cw / 2, y + 25, "...", 10, "middle", True, fill=C["muted"]))
                continue
            o.append(rect(x, y + 4, cw, 32, "#fff", C["unit"], 1, 2))
            o.append(text(x + cw / 2, y + 24, v, 10, "middle", True, weight=600))
        fit(desc, 8.5, 440, False, "d1a desc")
        o.append(text(20, y + 52, desc, 8.5, fill=C["muted"]))
        o.append(cite(ax + 4 * (cw + 8) - 12, y + 52, ref))
        boxes.append((name, ref))
        y += 60
    # the two groups
    o.append(text(20, y + 10, "the upper three fields pair a helper's W-th call with main's W-th window; the lower four", 9))
    o.append(text(20, y + 22, "belong to the open window only and are main's to reset after the join (Note [Shared block save])", 9))
    o.append(cite(680, y + 34, "model.hpp:3112-3116, 3120-3121"))
    H = y + 44
    cap = ("Updates B1 and B3: the same window across a whole pass. opened and each helper's "
           "helper_windows slot count the windows of the pass, so a helper's W-th call pairs "
           "with main's W-th window. next_unit, finished, n_units and unit_start describe the "
           "open window only and are rewritten before every open. Worked example: 3 workers, "
           "41 items, 36 layers.")
    legend = [
        ("unit", "grey-blue: a field of the window; white box with grey-blue outline = its value in one window"),
        ("ctx", "grey box, thin grey outline: one window (one layer of the pass)"),
        ("lane", "white box, thin grey outline: the windows left out"),
        ("white box, grey-blue outline: the field's value in one window", "#fff", C["unit"], False, False),
        ("grey-blue text: whether the field counts up across windows or is reset per window", "text", C["unit"]),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "k_store_window over one forward pass: which fields count up, which are reset",
                  "".join(o), cap, boxes=boxes, legend=legend)


def fig_b():
    fid = "common-d1b"
    o = [marker_defs(fid, {"ink": C["ink"], "unit": C["unit"]})]
    boxes = []
    o.append(text(20, 18, "the cut of the worked example: 41 items -> unit_start = [0, 16, 32, 41]", 12,
                  weight=700))
    # items strip with page offsets
    o.append(text(20, 40, "q_batch->items (41 token jobs, page 7 offsets 0..40, all with KV work)", 9.5,
                  weight=600))
    strip, x_end, spans = item_strip(20, 48, cell=14.6, gap=0.6, unit_gap=8, h=18)
    o.append(strip)
    for (x0, x1), u in zip(spans, UNITS):
        o.append(text(x0 + 3, 61, str(u["begin"]), 8.5, "start", True))
        o.append(text(x1 - 3, 61, str(u["end"] - 1), 8.5, "end", True))
        o.append(text((x0 + x1) / 2, 80, f"block {u['block']}: offsets {u['offsets']}", 8.5, "middle",
                      fill=C["unit"], weight=600))
    o.append(cite(680, 92, "common.hpp:1110-1111"))
    boxes.append(("q_batch->items", "common.hpp:1110-1111"))
    # the loop
    ly = 102
    o.append(rect(20, ly, 660, 96, "#fff", C["ink"], 1.2, 5))
    o.append(text(28, ly + 16, "k_store_cut_units: one pass over the items", 10.5, mono=True, weight=700))
    o.append(tag(28 + 270, ly + 16, "new"))
    o.append(cite(676, ly + 16, "model.hpp:3163-3191"))
    boxes.append(("k_store_cut_units", "model.hpp:3163-3191"))
    ll = ["for t in 0 .. n_items - 1: kv = token_jobs_do_kv[items[t]]; pg = kv ? &page_of(token) : nullptr;",
          "block = kv ? offset_in_page(token) / k_store_block : 0;",
          "if (t == 0 || kv != run_kv || pg != run_page || block != run_block): unit_start[n_units++] = t",
          "after the loop: unit_start[n_units] = n_items; w.n_units = n_units",
          "here: t = 0 starts unit 0; t = 16 changes block (0 -> 1); t = 32 changes block (1 -> 2); end = 41"]
    for s in ll:
        fit(s, 8.5, 644, True, "d1b loop")
    o.append(lines(28, ly + 31, ll, 8.5, 12, mono=True))
    o.append(arrow(fid, "ink", [(140, 92), (140, ly - 2)], C["ink"]))
    # unit_start table
    ty = ly + 120
    o.append(text(20, ty + 46, "unit_start: the first n_units + 1 = 4 entries used (the array has max_minibatch_size + 1)",
                  9.5, weight=600))
    tbl, tx = unit_table(20, ty + 8, cell_w=48, h=22)
    o.append(tbl)
    o.append(cite(680, ty + 58, "common.hpp:1207-1215; model.hpp:3187-3190"))
    boxes.append(("unit_start", "common.hpp:1207-1215"))
    o.append(arrow(fid, "ink", [(70, ly + 96), (70, ty + 4)], C["ink"]))
    cnt, _ = counters(330, ty + 2, [("n_units", "3")], w=80, h=30)
    o.append(cnt)
    boxes.append(("n_units", "common.hpp:1206"))
    # the three units and what each one becomes
    uy = ty + 80
    o.append(text(20, uy - 2, "the units and the present mask of each (bit t = offset c * 16 + t is in the run)",
                  9.5, weight=600))
    for i, u in enumerate(UNITS):
        y = uy + 6 + i * 50
        o.append(rect(20, y, 660, 44, C["unit_fill"], C["unit"], 1.1, 4))
        o.append(text(28, y + 15, f"unit {u['u']} = items[{u['begin']}, {u['end']})", 9.5, mono=True,
                      weight=600))
        o.append(text(28, y + 30, f"page {u['page']}, block {u['block']}, offsets {u['offsets']}, n = {u['n']}",
                      8.5, fill=C["muted"]))
        # the mask as 16 lanes
        lx = 250
        for t in range(16):
            on = t < u["n"]
            o.append(rect(lx + t * 14, y + 8, 12, 12, C["rows_fill"] if on else C["empty_fill"],
                          C["rows"] if on else C["empty"], 0.8, 1, None if on else "2 2"))
        o.append(text(lx, y + 34, f"present = {u['present']}; {u['store']}", 8.5, mono=True))
        o.append(cite(676, y + 12, "model.hpp:3260-3291; kv_cache.hpp:2078-2097"))
    boxes.append(("unit 0 .. unit 2, present", "model.hpp:3260-3291 (store_k_block: the run and present); "
                  "kv_cache.hpp:2078-2097 (set_k_block)"))
    H = uy + 6 + 3 * 50 + 10
    cap = ("Updates B5 with the worked example: the one pass of k_store_cut_units over the 41 "
           "items starts a unit at t = 0 and at each block change (t = 16, t = 32), closes the "
           "table with n_items = 41 and sets n_units = 3. Units 0 and 1 are whole blocks "
           "(present 0xffff); unit 2 holds 9 lanes (present 0x01ff). Every unit lies in one "
           "page, one block and one KV-write state.")
    legend = [
        ("unit", "grey-blue: the items of a unit, the unit_start table, n_units, the three units"),
        ("box", "white box, ink outline: the loop of k_store_cut_units"),
        ("present", "green: a lane whose bit is set in the present mask of the unit's set_k_block"),
        ("empty", "grey dashed: a lane not in the run (absent token), an unused unit_start entry"),
        ("arrow", "ink arrow: the items go through the loop into unit_start"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR"),
    ]
    return figure(fid, W, H, "The cut of the worked example's items into unit_start and the present masks",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
