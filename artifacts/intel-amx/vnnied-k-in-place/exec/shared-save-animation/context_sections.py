#!/usr/bin/env python3
"""Sections 2 and 3 of status/shared-save-animation.html (added 2026-09-18, revision 5):
where the shared save sits in a prefill layer (run, pass, layer), what it reads and
writes, which functions take part, and how it fits together with the block store.
Imported by gen_page.py. Pure ASCII.

Data: the one-layer lane extracts of lanes.py (exec/vnnik-trace-20260914/lanes.py) for
layer 10 of prefill pass 3 (pass index 2) of every traced configuration
(<trace>.lanes.json next to the traces), the per-run statistics of analyze.py
(analysis.json) for both trace sets, the single-span spread of savek_spans.py
(savek_spans.json, next to this file) and the TTFT cells of the remedies campaign
(exec/results/vnnik2-20260915/summary.json). The remedied traces (vnni0, a, b, ab) were
extracted on 2026-09-18 with the same script and arguments as the report's figure 2.2.

Thread roles are counted per window from the span names (a thread with kernel_* spans in
the window is a main helper, a thread with Attention spans is an attention worker), not
from lanes.py's whole-trace "cls" field: at tp4 a prefill pass has 15 helpers and 40
attention workers, a decode pass 8 and 47 (the report's section 1 quotes the decode split).

Cited code positions: worktree tron-VNNIed-K at 30c4ac82cb. model.hpp, common.hpp,
k_vnni.hpp, self_attention.hpp and TronCpp.hs are byte-identical to 04ffeedccb;
kv_cache.hpp differs in 3 wording lines with the same line count; gof.hpp's page_info
comment (lines 61-77) was rewritten by cac6814322 (git diff --stat 04ffeedccb 30c4ac82cb).
"""
import json
import os
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
RES = "/home/jhan/workspace/intel-AMX/exec/results"
SET1 = "vnnik-trace-20260914"    # binaries: base (row-major, 544ca05c7a) and vnni (5e45ae55ae, VNNI scatter store)
SET2 = "vnnik2-trace-20260915"   # one binary, commit 9928cb2849, configurations vnni0 / a / b / ab
TRACES = [("base-tp2", SET1), ("vnni-tp2", SET1), ("vnni0-tp2", SET2), ("a-tp2", SET2), ("b-tp2", SET2), ("ab-tp2", SET2),
          ("base-tp4", SET1), ("vnni-tp4", SET1), ("vnni0-tp4", SET2), ("a-tp4", SET2), ("b-tp4", SET2), ("ab-tp4", SET2)]
CFG_WORDS = {"base": "row-major K, main alone (the binary before VNNI K)", "vnni": "VNNI K, scatter per token, main alone (2026-09-14 binary)",
             "vnni0": "VNNI K, scatter per token, main alone (both remedies off)", "a": "block store only", "b": "shared save only", "ab": "block store and shared save"}

LANES = {}
for _n, _d in TRACES:
    LANES[_n] = json.load(open(os.path.join(RES, _d, _n + ".perfetto-trace.lanes.json")))["prefill"]
    assert LANES[_n]["layer"] == 10 and LANES[_n]["pass_index"] == 2 and LANES[_n]["n_token_jobs"] == 1024, _n

ANALYSIS = {}
for _d in (SET1, SET2):
    for _e in json.load(open(os.path.join(RES, _d, "analysis.json"))):
        ANALYSIS[_e["trace"].replace(".perfetto-trace", "")] = _e
N_LAYERS = int(ANALYSIS["vnni0-tp2"]["kinds"]["prefill"]["n_layers"])
assert N_LAYERS == 36 and all(int(e["kinds"]["prefill"]["n_layers"]) == 36 for e in ANALYSIS.values())
SPANS = json.load(open(os.path.join(HERE, "savek_spans.json")))   # single Save K spans over the run (savek_spans.py)
assert SPANS["vnni0-tp2"]["n"] == 288 and SPANS["ab-tp2"]["n"] == 288
TTFT_CELLS = {(c["arm"], "tp%d" % c["tp"]): c for c in json.load(open(os.path.join(RES, "vnnik2-20260915", "summary.json")))["cells"] if c["prompt"] == 1024}
assert ("ab", "tp4") in TTFT_CELLS and TTFT_CELLS[("ab", "tp2")]["n"] == 3 and TTFT_CELLS[("ab", "tp4")]["n"] == 2

N_PREFILL_PASSES = 8          # 1024-token prompt in 128-token chunks (report section 2 recipe: --trace-passes 1-16 = 8 prefill + 8 decode)
N_ITEMS = 1024
N_KV_HEADS = 8
ROW_BYTES = 256               # one K row: 128 bf16
ENTRY_BYTES = N_KV_HEADS * ROW_BYTES   # one K buffer entry: the token's 8 K rows
ROWS_PER_SAVE = N_ITEMS * N_KV_HEADS
BYTES_PER_SAVE = ROWS_PER_SAVE * ROW_BYTES
assert BYTES_PER_SAVE == 2 * 1024 * 1024 and ENTRY_BYTES == 2048
WINDOWS_PER_PASS = N_LAYERS
WINDOWS_PER_PREFILL = WINDOWS_PER_PASS * N_PREFILL_PASSES
assert WINDOWS_PER_PREFILL == 288
PAGES_PER_SAVE = 16           # pass 3: pages 4 and 5 of each of 8 users
PLANES_PER_SAVE = PAGES_PER_SAVE * N_KV_HEADS
assert PLANES_PER_SAVE * 16 * 1024 == BYTES_PER_SAVE

P = lambda n: ANALYSIS[n]["kinds"]["prefill"]
D = lambda n: ANALYSIS[n]["kinds"]["decode"]
MEAN = {n: P(n)["save_k_us_per_layer"] for n in ANALYSIS}          # unrounded per-layer means (us)
MEAS_ROUNDED = {n: round(MEAN[n]) for n in ANALYSIS}
assert MEAS_ROUNDED["vnni0-tp2"] == 858 and MEAS_ROUNDED["ab-tp2"] == 80 and MEAS_ROUNDED["b-tp4"] == 110 and MEAS_ROUNDED["ab-tp4"] == 60

L = {
    "save_k": "model.hpp:3065", "save_k_impl": "model.hpp:2992-3059", "trace": "model.hpp:3001", "shared": "model.hpp:2806-2814",
    "cut": "model.hpp:2818-2845", "store_k_block": "model.hpp:2855-2946", "helper": "model.hpp:2953-2990", "marks": "model.hpp:3040-3058",
    "save_v": "model.hpp:3082-3128", "latch_reset": "model.hpp:1866-1889 (finalize_minibatches)", "window": "common.hpp:1045-1068",
    "helpers_rule": "model.hpp:1933-1935 (fixed_main_helper_split = pool workers x 2 / 7), 1950-1960 (the single-minibatch branch of recommend_n_main_helpers), 1976-1982 (the caps); ingest/src/TronCpp.hs:1397-1412 (available_main_parallelism = n_tokens x the largest MoE top-k, 1 without MoE)",
    "early": "model.hpp:91-136 (Note [Early and late hardware attention launch]), 2140 (launch_early_hw_attention)",
    "set_k_row": "kv_cache.hpp:1701", "set_k_block": "kv_cache.hpp:1723", "get_k_row": "kv_cache.hpp:1737", "plane": "kv_cache.hpp:1689",
    "mark": "kv_cache.hpp:1935", "is_kv_complete": "kv_cache.hpp:1949", "copy": "kv_cache.hpp:2093, 2147-2161 (copy_from), 1086-1113 (book::append)", "note_vnni": "kv_cache.hpp:653-718 (Note [K VNNI storage])",
    "slot": "kv_cache.hpp:160-166 (kv_slot_spec), ingest/src/Tron.hs:815-816 (uniformKvSlot)",
    "scatter": "k_vnni.hpp:139", "transpose": "k_vnni.hpp:153", "store_block": "k_vnni.hpp:194", "gather": "k_vnni.hpp:221", "qk_group": "k_vnni.hpp:248",
    "wait": "self_attention.hpp:784", "ready": "self_attention.hpp:777", "pending": "self_attention.hpp:788", "amx": "self_attention.hpp:1437", "sw": "self_attention.hpp:1636",
    "dense": "self_attention.hpp:1375-1391 (is_dense_amx_page), src/tron/models/ranged_mask.cpp:42-49 (a visible range closes above each query token)",
    "emit_main": "ingest/src/TronCpp.hs:2370-2418 (submitAttentionOperation, saveKv)", "emit_help": "ingest/src/TronCpp.hs:2325-2340 (runHelperStatement)",
    "emit_run_help": "ingest/src/TronCpp.hs:1271-1282 (runHelpMethod)", "strategy": "ingest/src/TronCpp.hs:2002-2040 (staticStrategy)",
    "emit_matmul": "ingest/src/TronCpp.hs:2237-2247 (runStatement: the matmul statements, main only), 2298-2300 (runHelperStatement emits nothing for them), 2462-2478 (matmulLaunch)",
    "names": "ingest/src/Name.hs:66-80 (a name's counter 0 has no suffix)",
    "gof": "h/tron/gof.hpp:61-81 (page_info::k_head_fn, kv_complete_fn)", "gof_readers": "h/tron/scheduler/full.hpp:2641-2642, 2745; model.hpp:3205-3209 (fire_gof_rodeo); kv_cache.hpp:2154-2158 (copy_from copies the counters)",
    "btensor": "h/tron/hardware/btensor.hpp:21", "one_minibatch": "ingest/src/TronCpp.hs:1275-1278 (run_main_help asserts one minibatch)",
    "test": "t/t_llama_unit.cpp:2767-2769 (one-thread case), 2772-2807 (three-thread case)",
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def milestones(name):
    """Key times of the traced layer, us from the Save K start (t = 0). Thread roles from the
    span names inside the window."""
    w = LANES[name]
    sp = w["spans"]
    end = lambda s: s["start_us"] + s["dur_us"]
    main = {s["name"]: s for s in sp if s["name"] in ("Save K", "Save V")}
    kern_threads = {s["thread"] for s in sp if s["name"].startswith("kernel_")}
    att_threads = {s["thread"] for s in sp if s["name"].startswith("Attention") or s["name"] == "attention: join"}
    assert not (kern_threads & att_threads), name
    hel = [s for s in sp if s["thread"] in kern_threads]
    att = [s for s in sp if s["thread"] in att_threads]
    rope = [s for s in hel if "rope" in s["name"] and s["start_us"] < 0]
    after = [s for s in hel if s["start_us"] > 0]
    nxt = min(after, key=lambda s: s["start_us"])["name"]
    nxt_end = max(end(s) for s in after if s["name"] == nxt)
    later = [s for s in after if s["start_us"] > nxt_end]
    m = {
        "save_k": main["Save K"]["dur_us"], "save_v_start": main["Save V"]["start_us"], "save_v_end": end(main["Save V"]),
        "rope_name": rope[0]["name"], "rope_start": min(s["start_us"] for s in rope), "rope_end_min": min(end(s) for s in rope), "rope_end_max": max(end(s) for s in rope),
        "next_name": nxt, "next_start": min(s["start_us"] for s in after if s["name"] == nxt), "next_end": nxt_end,
        "next2_start": min(s["start_us"] for s in later) if later else None, "next2_name": min(later, key=lambda s: s["start_us"])["name"] if later else None,
        "ready_first": min(s["start_us"] for s in att if s["name"] == "Attention Ready"), "ready_last_end": max(end(s) for s in att if s["name"] == "Attention Ready"),
        "pending_first": min(s["start_us"] for s in att if s["name"] == "Attention Pending"), "pending_last_end": max(end(s) for s in att if s["name"] == "Attention Pending"),
        "join_first": min(s["start_us"] for s in att if s["name"] == "attention: join"), "join_last_end": max(end(s) for s in att if s["name"] == "attention: join"),
        "n_helpers": len(kern_threads), "n_attn": len(att_threads), "n_rope_threads": len({s["thread"] for s in rope}), "pass_ms": w["pass_ms"],
    }
    assert m["rope_name"] == "kernel_rmsnorm_rope_rmsnorm_rope_10" and m["next_name"] == "kernel_add_rmsnorm_20", (name, m["rope_name"], m["next_name"])
    assert m["n_rope_threads"] == m["n_helpers"], name
    assert -5.0 < m["rope_end_min"] <= m["rope_end_max"] < 1.0, (name, m["rope_end_min"], m["rope_end_max"])
    assert abs(m["pending_first"] - m["save_v_end"]) < 1.0, (name, m["pending_first"], m["save_v_end"])
    return m


M = {n: milestones(n) for n, _ in TRACES}
assert all(M[n]["n_helpers"] == 7 and M[n]["n_attn"] == 20 for n in M if n.endswith("tp2"))
assert all(M[n]["n_helpers"] == 15 and M[n]["n_attn"] == 40 for n in M if n.endswith("tp4"))
HELPERS_PREFILL = {"tp2": 7, "tp4": 15}
POOL_WORKERS = {"tp2": 27, "tp4": 55}   # application-pool threads besides main: 28 and 56 cores (report section 1)
assert all((POOL_WORKERS[tp] * 2) // 7 == HELPERS_PREFILL[tp] for tp in POOL_WORKERS), "fixed_main_helper_split = pool workers x 2 / 7"
HELPERS_DECODE = {"tp2": ANALYSIS["vnni0-tp2"]["threads"]["main_helpers"], "tp4": ANALYSIS["vnni0-tp4"]["threads"]["main_helpers"]}
ATTN_DECODE = {"tp2": ANALYSIS["vnni0-tp2"]["threads"]["attention_workers"], "tp4": ANALYSIS["vnni0-tp4"]["threads"]["attention_workers"]}
assert HELPERS_DECODE == {"tp2": 7, "tp4": 8} and ATTN_DECODE == {"tp2": 20, "tp4": 47}
BEFORE, AFTER = "vnni0-tp2", "ab-tp2"
LAYER_END_SHIFT = M[BEFORE]["join_last_end"] - M[AFTER]["join_last_end"]
SAVE_K_SHIFT = M[BEFORE]["save_k"] - M[AFTER]["save_k"]
PENDING_SHIFT = M[BEFORE]["pending_first"] - M[AFTER]["pending_first"]
ROPE_LO = min(m["rope_end_min"] for m in M.values())
ROPE_HI = max(m["rope_end_max"] for m in M.values())
ROPE_LATE = [n for n, m in M.items() if m["rope_end_max"] > 0]
READY_LO = min(m["ready_first"] for m in M.values())
READY_HI = max(m["ready_first"] for m in M.values())
PEND_GAP_LO = min(m["pending_first"] - m["save_v_end"] for m in M.values())
PEND_GAP_HI = max(m["pending_first"] - m["save_v_end"] for m in M.values())


def f0(x):
    return "%.0f" % x


def f1(x):
    return "%.1f" % x


def f2(x):
    return "%.2f" % x


def wrap_lines(text, width):
    return textwrap.wrap(text, width) or [""]


# ---------------------------------------------------------------- 2.1 the three levels
def levels_tree():
    b, a = M[BEFORE], M[AFTER]
    lines = [
        "run: 8 users, one 1024-token prompt each",
        "+-- prefill pass 1 .. %d: 128 tokens of each user = %d items per pass" % (N_PREFILL_PASSES, N_ITEMS),
        "|     (mean pass length at tp2: %.0f ms with both remedies off, %.0f ms with both on)" % (P(BEFORE)["pass_ms"], P(AFTER)["pass_ms"]),
        "|   +-- layer 1 .. %d (the traces count from 0: their layer 10 is the 11th layer here, window W = 11)" % N_LAYERS,
        "|         +-- FPGA cards: the layer's Q, K and V projection matmuls (no trace span on main)",
        "|         +-- main helpers (%d at tp2, %d at tp4): norm and rope, item by item, into the K buffer ks" % (HELPERS_PREFILL["tp2"], HELPERS_PREFILL["tp4"]),
        "|         +-- main + helpers: save_k = ONE WINDOW: 64 units, %d K rows, 2 MiB" % ROWS_PER_SAVE,
        "|         |     (%s us before the remedies, %s us after: layer 10 of pass 3, tp2)" % (f0(b["save_k"]), f0(a["save_k"])),
        "|         +-- main alone: save_v (%s us)" % f0(b["save_v_end"] - b["save_v_start"]),
        "|         +-- attention workers (%d at tp2, %d at tp4): Ready sections, the latch, Pending sections, joins" % (M["vnni0-tp2"]["n_attn"], M["vnni0-tp4"]["n_attn"]),
        "+-- decode step 1 .. N: 8 items (one per user): no window, main stores alone with scatters",
    ]
    assert all(len(ln) <= 120 for ln in lines), max(len(ln) for ln in lines)
    return '<pre class="mono" style="line-height:1.35">' + esc("\n".join(lines)) + '</pre>'


def levels_table():
    rows = [
        ("prefill passes of the run (8 users x 1024 tokens, 128 tokens of each user per pass)", "%d" % N_PREFILL_PASSES, "report section 2 (recipe), report section 1"),
        ("layers per pass = save_k calls per pass = windows per pass (one KV-writing attention operation per layer)", "%d" % WINDOWS_PER_PASS, "analysis.json n_layers; model.hpp save_k_impl (one Save K span per call)"),
        ("windows per prefill of the 8 prompts", "%d" % WINDOWS_PER_PREFILL, "36 x 8, computed"),
        ("K rows one save stores (1024 items x 8 KV heads, each K row 256 bytes), bytes", "%d K rows = %d K buffer entries of %d bytes, %d bytes (2 MiB)" % (ROWS_PER_SAVE, N_ITEMS, ENTRY_BYTES, BYTES_PER_SAVE), "computed from the model shape"),
        ("planes one save fills in pass 3 (pages 4 and 5 of each user x 8 KV heads), 16 KiB each", "%d" % PLANES_PER_SAVE, "section 4.1 unit table"),
        ("threads in a prefill window: main + helpers = n_workers, tp2 / tp4", "1 + %d = %d / 1 + %d = %d" % (HELPERS_PREFILL["tp2"], HELPERS_PREFILL["tp2"] + 1, HELPERS_PREFILL["tp4"], HELPERS_PREFILL["tp4"] + 1), "threads with kernel spans in the traced window (lanes.json, section 2.2); model.hpp recommend_n_main_helpers"),
        ("Save K per pass, both remedies off (vnni0): tp2 / tp4", "%.1f ms (%.1f%% of a %.0f ms pass) / %.1f ms (%.1f%% of %.0f ms)" % (
            P("vnni0-tp2")["save_k_ms"], 100 * P("vnni0-tp2")["save_k_ms"] / P("vnni0-tp2")["pass_ms"], P("vnni0-tp2")["pass_ms"],
            P("vnni0-tp4")["save_k_ms"], 100 * P("vnni0-tp4")["save_k_ms"] / P("vnni0-tp4")["pass_ms"], P("vnni0-tp4")["pass_ms"]),
         "analysis.json (vnnik2-trace-20260915), mean over the 8 prefill passes"),
        ("Save K per pass, both remedies on (ab): tp2 / tp4", "%.1f ms (%.1f%% of a %.0f ms pass) / %.1f ms (%.1f%% of %.0f ms)" % (
            P("ab-tp2")["save_k_ms"], 100 * P("ab-tp2")["save_k_ms"] / P("ab-tp2")["pass_ms"], P("ab-tp2")["pass_ms"],
            P("ab-tp4")["save_k_ms"], 100 * P("ab-tp4")["save_k_ms"] / P("ab-tp4")["pass_ms"], P("ab-tp4")["pass_ms"]),
         "analysis.json (vnnik2-trace-20260915)"),
        ("Save K per pass, the row-major store of the binary before VNNI K (base): tp2 / tp4", "%.1f ms (%.1f%%) / %.1f ms (%.1f%%)" % (
            P("base-tp2")["save_k_ms"], 100 * P("base-tp2")["save_k_ms"] / P("base-tp2")["pass_ms"],
            P("base-tp4")["save_k_ms"], 100 * P("base-tp4")["save_k_ms"] / P("base-tp4")["pass_ms"]),
         "analysis.json (vnnik-trace-20260914)"),
        ("windows in a decode pass (8 items; k_store_shared, the function that decides whether a save is shared, needs more than 16 items)", "0", "model.hpp k_store_shared"),
    ]
    h = ['<table><tr><th>Quantity</th><th>Value</th><th>Source</th></tr>']
    for a, b, c in rows:
        h.append('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (esc(a), esc(b), esc(c)))
    h.append('</table>')
    return "".join(h)


# ---------------------------------------------------------------- 2.2 the layer, measured lanes
C = {"savek": "#b02a2a", "savev": "#eb6834", "kernel": "#0a6b4f", "ready": "#2a78d6", "pending": "#eb6834", "join": "#8a8987", "idle": "#a9a8a4", "ink": "#0b0b0b", "muted": "#52514e"}


def stage_svg():
    """Two charts, one x axis: layer 10 of prefill pass 3 with both remedies off (vnni0) and on
    (ab), tp2, commit 9928cb2849. Lanes: main (traced spans only), the 7 helpers as one
    envelope lane, the 20 attention workers as three envelope lanes (Ready, Pending, attention join)."""
    X0, X1 = -650.0, 5400.0
    W, LEFT, RIGHT = 960, 178, 30
    px = lambda t: LEFT + (t - X0) / (X1 - X0) * (W - LEFT - RIGHT)
    LANE_H = 26
    charts = [(BEFORE, "before: both remedies off (vnni0), Save K %s us" % f0(M[BEFORE]["save_k"])),
              (AFTER, "after: block store and shared save (ab), Save K %s us" % f0(M[AFTER]["save_k"]))]
    body = []
    y = 48
    dashed = lambda x0, x1, yy, col: '<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="none" stroke="%s" stroke-dasharray="2,3"/>' % (x0, yy + 2, max(0.5, x1 - x0), LANE_H - 4, col)
    for name, title in charts:
        m = M[name]
        body.append('<text x="10" y="%d" font-size="13" font-weight="600" fill="%s">%s</text>' % (y + 12, C["ink"], esc(title)))
        y += 22
        lanes = [("main thread", "main"), ("main helpers (%d), envelope" % m["n_helpers"], "helpers"),
                 ("attention workers (%d): Ready" % m["n_attn"], "ready"), ("attention workers: Pending", "pending"), ("attention join (the workers)", "join")]
        for label, kind in lanes:
            yy = y
            body.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#f7f6f3"/>' % (LEFT, yy, W - LEFT - RIGHT, LANE_H))
            body.append('<text x="%d" y="%.1f" font-size="11" text-anchor="end" fill="%s">%s</text>' % (LEFT - 6, yy + LANE_H * 0.68, C["muted"], esc(label)))
            if kind == "main":
                body.append(dashed(px(X0) + 0.5, px(0) - 1, yy, C["idle"]))
                body.append('<text x="%.1f" y="%.1f" font-size="10" text-anchor="middle" fill="%s">not traced</text>' % ((px(X0) + px(0)) / 2, yy + LANE_H * 0.68, C["muted"]))
                xs, xe = px(0), px(m["save_k"])
                body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"><title>Save K %.1f us</title></rect>' % (xs, yy + 1, max(1.5, xe - xs), LANE_H - 2, C["savek"], m["save_k"]))
                xs2, xe2 = px(m["save_v_start"]), px(m["save_v_end"])
                body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"><title>Save V %.1f us</title></rect>' % (xs2, yy + 1, max(1.5, xe2 - xs2), LANE_H - 2, C["savev"], m["save_v_end"] - m["save_v_start"]))
                body.append(dashed(xe2 + 1, px(X1) - 0.5, yy, C["idle"]))
                body.append('<text x="%.1f" y="%.1f" font-size="10" text-anchor="end" fill="%s">not traced</text>' % (px(X1) - 4, yy + LANE_H * 0.68, C["muted"]))
                body.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="600" fill="%s">Save K %s us, then Save V %s us (serial, main alone)</text>' % (xe2 + 6, yy + LANE_H * 0.68, C["savek"], f0(m["save_k"]), f0(m["save_v_end"] - m["save_v_start"])))
            elif kind == "helpers":
                xs, xe = px(max(m["rope_start"], X0)), px(m["rope_end_max"])
                body.append(dashed(px(X0) + 0.5, xs - 1, yy, C["idle"]))
                body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"><title>%s: %.0f .. %.2f us</title></rect>' % (xs, yy + 1, xe - xs, LANE_H - 2, C["kernel"], esc(m["rope_name"]), m["rope_start"], m["rope_end_max"]))
                body.append('<text x="%.1f" y="%.1f" font-size="10" text-anchor="end" fill="#fff">norm+rope</text>' % (xe - 4, yy + LANE_H * 0.68))
                if name == AFTER:
                    body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="none" stroke="%s" stroke-width="1.5" stroke-dasharray="3,2"/>' % (px(0), yy + 2, max(2.0, px(m["save_k"]) - px(0)), LANE_H - 4, C["savek"]))
                    gap_from = m["save_k"]
                    body.append('<text x="%.1f" y="%.1f" font-size="10" fill="%s">claim units inside Save K (from the code, no trace span)</text>' % (px(m["save_k"]) + 6, yy + 11, C["savek"]))
                else:
                    gap_from = m["rope_end_max"]
                    body.append('<text x="%.1f" y="%.1f" font-size="10" fill="%s">idle: the next kernel needs the attention output</text>' % (px(m["save_k"]) + 6, yy + 11, C["muted"]))
                xa, xb = px(gap_from), px(m["next_start"])
                body.append(dashed(xa + 1, xb - 1, yy, C["idle"]))
                xs3, xe3 = px(m["next_start"]), px(min(m["next_end"], X1))
                body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"><title>%s: %.0f .. %.0f us</title></rect>' % (xs3, yy + 1, xe3 - xs3, LANE_H - 2, C["kernel"], esc(m["next_name"]), m["next_start"], m["next_end"]))
                body.append('<text x="%.1f" y="%.1f" font-size="10" text-anchor="end" fill="%s">residual add + norm, %s to %s us</text>' % (xs3 - 4, yy + 22, C["muted"], f0(m["next_start"]), f0(m["next_end"])))
                nxt2 = m["next2_start"] if m["next2_start"] is not None else X1
                body.append(dashed(xe3 + 1, px(min(nxt2, X1)) - 1, yy, C["idle"]))
                if nxt2 < X1:
                    body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"><title>%s starts at %.0f us</title></rect>' % (px(nxt2), yy + 1, px(X1) - px(nxt2), LANE_H - 2, C["kernel"], esc(m["next2_name"]), nxt2))
            else:
                a, b = {"ready": (m["ready_first"], m["ready_last_end"]), "pending": (m["pending_first"], m["pending_last_end"]), "join": (m["join_first"], m["join_last_end"])}[kind]
                xs, xe = px(a), px(b)
                body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" fill-opacity="0.85"><title>%s: first start %.1f us, last end %.0f us</title></rect>' % (xs, yy + 1, xe - xs, LANE_H - 2, C[kind], kind, a, b))
                if kind == "ready":
                    body.append('<text x="%.1f" y="%.1f" font-size="10" fill="#fff">earlier chunks\' pages, %s to %s us</text>' % (xs + 4, yy + LANE_H * 0.68, f1(a), f0(b)))
                elif kind == "pending":
                    body.append('<text x="%.1f" y="%.1f" font-size="10" fill="#fff">this pass\'s pages; start %s us = Save V end + %s us</text>' % (xs + 4, yy + LANE_H * 0.68, f1(a), f1(a - m["save_v_end"])))
                else:
                    body.append('<text x="%.1f" y="%.1f" font-size="10" fill="%s">layer end (last attention join) %s us</text>' % (xe + 6, yy + LANE_H * 0.68, C["muted"], f0(b)))
                    body.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2"/>' % (xe, yy - 3, xe, yy + LANE_H + 3, C["savek"]))
            y += LANE_H + 3
        y += 10
    out = []
    ax_y = y + 6
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (LEFT, ax_y, W - RIGHT, ax_y, C["muted"]))
    t = -500.0
    while t <= X1:
        x = px(t)
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>' % (x, ax_y, x, ax_y + 5, C["muted"]))
        out.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">%s</text>' % (x, ax_y + 17, C["muted"], ("%.1f" % (t / 1000)).rstrip("0").rstrip(".") if t else "0"))
        out.append('<line x1="%.1f" y1="46" x2="%.1f" y2="%d" stroke="#e6e5e1"/>' % (x, x, ax_y))
        t += 500.0
    out.append('<text x="%d" y="%d" font-size="11" fill="%s">wall-clock time, ms; 0 = the start of this layer\'s Save K; durations to scale; layer 10 of prefill pass 3, tp2, commit 9928cb2849</text>' % (LEFT, ax_y + 33, C["muted"]))
    out.append('<text x="%d" y="%d" font-size="11" font-weight="600" fill="%s">the layer end moved by %s us (%s to %s us); Save K shrank by %s us; the first Pending start moved by %s us</text>' % (
        LEFT, ax_y + 50, C["savek"], f0(LAYER_END_SHIFT), f0(M[BEFORE]["join_last_end"]), f0(M[AFTER]["join_last_end"]), f0(SAVE_K_SHIFT), f0(PENDING_SHIFT)))
    # legend
    lg = [("Save K", C["savek"], None), ("Save V, Pending", C["savev"], None), ("helper kernel", C["kernel"], None), ("Ready", C["ready"], None), ("attention join", C["join"], None),
          ("waiting or not traced", None, C["idle"]), ("helpers' claims (from the code)", None, C["savek"]), ("layer end", "bar", None)]
    x = 10
    for text, fill, stroke in lg:
        if fill == "bar":
            out.append('<line x1="%d" y1="23" x2="%d" y2="36" stroke="%s" stroke-width="2"/>' % (x + 5, x + 5, C["savek"]))
        elif fill:
            out.append('<rect x="%d" y="24" width="11" height="11" fill="%s"/>' % (x, fill))
        else:
            out.append('<rect x="%d" y="24" width="11" height="11" fill="none" stroke="%s" stroke-dasharray="3,2"/>' % (x, stroke))
        out.append('<text x="%d" y="34" font-size="11" fill="%s">%s</text>' % (x + 15, C["muted"], esc(text)))
        x += 15 + int(6.0 * len(text)) + 18
    H = ax_y + 60
    head = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="One prefill layer before and after the two remedies, wall-clock lanes to scale" xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;">' % (W, H, W, H)]
    head.append('<text x="10" y="16" font-size="14" font-weight="600" fill="%s">One prefill layer, before and after: where Save K sits, and what waits for it</text>' % C["ink"])
    return "".join(head + out + body + ['</svg>'])


def stage_table():
    h = ['<table><tr><th>configuration (trace set)</th><th>helpers / attention workers in the window</th><th>the helpers\' rope kernel ends (first .. last helper), us</th><th>Save K, us</th><th>Save V start .. end, us</th>'
         '<th>first Pending start, us</th><th>last attention join ends (layer end), us</th><th>helpers\' next kernel starts, us</th></tr>']
    for n, d in TRACES:
        m = M[n]
        cfg, tp = n.split("-")
        h.append('<tr><td>%s, %s (%s)</td><td class="num">%d / %d</td><td class="num">%s .. %s</td><td class="num">%s</td><td class="num">%s .. %s</td><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>' % (
            esc(CFG_WORDS[cfg]), tp, "set 1" if d == SET1 else "set 2", m["n_helpers"], m["n_attn"], f2(m["rope_end_min"]), f2(m["rope_end_max"]), f1(m["save_k"]), f1(m["save_v_start"]), f1(m["save_v_end"]),
            f1(m["pending_first"]), f0(m["join_last_end"]), f0(m["next_start"])))
    h.append('</table>')
    return "".join(h)


# ---------------------------------------------------------------- 2.3 the statement order
def order_table():
    b, a = M[BEFORE], M[AFTER]
    rows = [
        ("1", "main", "Launches the layer's projection matmuls (Q, K, V) on the FPGA cards: for each one a matmul fill, prepare and launch statement, emitted for main only. The launch starts writing the output channel and finishes it from the completion callback. The rows come back per token. No trace span on main.",
         L["emit_matmul"]),
        ("1b", "main helpers", "Before it ropes item i, a helper waits for item i on the channel of every buffer its kernel reads (start_reading_at(i)). The wait for its first item comes before the kernel's trace span, the later ones inside it. After each item it finishes the item on the channel of every buffer it wrote (finish_writing_at(i)). For the K buffer that is the K channel main waits on in step 3. Whether the K matmul output buffer and ks are one buffer (norm and rope in place) or two is not readable in this worktree: the qwen graph is generated at build time. Insufficient data.",
         L["strategy"]),
        ("2", "main helpers (%d at tp2, %d at tp4 in a prefill pass)" % (HELPERS_PREFILL["tp2"], HELPERS_PREFILL["tp4"]),
         "The fused per-token kernel kernel_rmsnorm_rope_rmsnorm_rope_L (L = the layer's number in the ingest's kernel counter, 10 for the traced layer): the norm and the rope of Q, then of K, item by item on the helper's stripe. It writes each item's 8 K rows into the K buffer ks and finishes the item's K channel. In the traced layer the last helper ends %s us (before the remedies) and %s us (after) before Save K starts. The pass's helper count is the fixed split (pool workers x 2) / 7: %d at tp4 (%d pool workers) and %d at tp2 (%d). It is then capped by the item count and by the min/max helper limits. A prefill pass has 1024 items, so the cap does not act. A decode pass has 8 items, so at tp4 it has %d helpers." % (
             f1(-b["rope_end_max"]), f1(-a["rope_end_max"]), HELPERS_PREFILL["tp4"], POOL_WORKERS["tp4"], HELPERS_PREFILL["tp2"], POOL_WORKERS["tp2"], HELPERS_DECODE["tp4"]),
         "%s; %s; %s; lanes.json of set 2" % (L["strategy"], L["names"], L["helpers_rule"])),
        ("2b", "main", "launch_early_hw_attention(q, q_channel): the first statement of the attention block. The executor picks one FPGA attention launch phase per minibatch by its item count: %d or more items (TRON_HWATTN_EARLY_LAUNCH_MIN_B, default 4) means the early phase, and the launch runs here, before the saves. Fewer items means the late phase (step 8). The traced runs used the CPU attention, so no call dispatched hardware." % 4,
         L["early"] + "; " + L["emit_main"]),
        ("3", "main", "For every item: start_reading_at on the K channel (waits for that item's K rows). Then save_k(q_batch, k, n_workers). n_workers is 1 + the helpers: %d at tp2, %d at tp4 in a prefill pass." % (HELPERS_PREFILL["tp2"] + 1, HELPERS_PREFILL["tp4"] + 1),
         L["emit_main"] + "; " + L["save_k"]),
        ("4", "main, in save_k_impl", "The Save K span. k_store_shared decides whether this save is shared. k_store_cut_units cuts the items into units. next_unit = 0, finished = 0, opened++ (release). Claim loop: store_k_block per unit. Join: spin on finished. Then per token in item order: mark_k_complete, credit_gof_save (hardware attention slot only). Then upstream_kvs_ready[slot].count_down() on every downstream minibatch (one, in these runs: step 7).",
         ", ".join([L["save_k_impl"], L["shared"], L["cut"], L["marks"]])),
        ("4'", "main helpers, at the same statement position", "run_main_help calls save_k_helper(q_batch, k, worker_ix, n_workers): ++helper_windows[worker_ix], spin on opened, claim loop with store_k_block per unit, finished++ (release). Steps 4 and 4' run at the same time.",
         L["emit_help"] + "; " + L["emit_run_help"] + "; " + L["helper"]),
        ("5", "every claimer, per unit", "store_k_block. A run of 2 to 16 items of one block -> page::set_k_block -> k_vnni::store_block, per KV head: 4 dim steps, each with one 64-byte load per present row, one transpose_16x16_epi32 and 16 stores. The stores are full-line stores when the run fills the block and lane-masked stores otherwise. A run of one item -> page::set_k_row -> k_vnni::scatter_row (4 scatters) per KV head. The K buffer values are bf16 (the 16-bit brain floating-point format, 2 bytes per value; the buffer type is hardware::btensor). So store_k_block reads the rows in place, without a conversion copy.",
         ", ".join([L["store_k_block"], L["set_k_block"], L["store_block"], L["transpose"], L["set_k_row"], L["scatter"], L["btensor"]])),
        ("6", "main", "For every item: start_reading_at on the V channel. Then save_v(v): serial, token by token (the V plane pairs two tokens in one 32-bit lane). mark_v_complete, credits, and the second upstream_kvs_ready count_down.",
         L["emit_main"] + "; " + L["save_v"]),
        ("7", "attention workers (%d at tp2, %d at tp4 in a prefill pass)" % (M["vnni0-tp2"]["n_attn"], M["vnni0-tp4"]["n_attn"]),
         "run_attention_job. Ready sections (the pages of the earlier chunks) start %s to %s us after the Save K start in the 12 traced configurations. Then upstream_kvs_ready[slot].wait(). The latch of this layer's KV slot was reset to kvs_needed at the start of the pass. kvs_needed is 2 per upstream minibatch whose pages this minibatch reads: one count for that minibatch's save_k and one for its save_v. The generated plugin has one minibatch per pass, and it is its own upstream. So the latch is 2, and it opens after this layer's save_k and save_v. Then Pending sections over this pass's pages. In these runs those pages fail the dense predicate. Every token of a Pending page is a query token of this pass. A visible range closes above every query token. So the range that holds the page's first token ends inside the page, and the predicate fails. The Pending sections therefore run k_vnni::qk_group, the AVX-512 reader. The AMX kernel qk_vnni_128x4 reads the planes this save wrote in later passes, when the same pages are Ready pages. Then the attention joins. In the traced layers the first Pending starts %s to %s us after Save V ends." % (
             f1(READY_LO), f1(READY_HI), f1(PEND_GAP_LO), f1(PEND_GAP_HI)),
         ", ".join([L["ready"], L["wait"], L["latch_reset"], L["one_minibatch"], L["pending"], L["dense"], L["sw"], L["amx"], L["plane"]])),
        ("8", "main", "prepare_late_hw_attention, launch_late_hw_attention: the late FPGA attention phase, after both saves. With %d or more items (all traced passes) both return at once, because the early phase (step 2b) was chosen. The traced runs used the CPU attention (the attention workers' spans above)." % 4,
         L["emit_main"] + "; " + L["early"]),
        ("9", "main helpers", "kernel_add_rmsnorm_2L (20 for the traced layer 10): the residual add and the norm after attention. The ingest counts each kernel name across the layers. There are two add_rmsnorm kernels per layer. So the layer's second one, number 2L + 1, follows the MLP (the feed-forward block). Layer 0's names carry no number. The kernel starts when the attention output has arrived: %s us after the Save K start before the remedies, %s us after." % (f0(b["next_start"]), f0(a["next_start"])),
         "lanes.json of set 2 (vnni0-tp2, ab-tp2); " + L["names"]),
    ]
    h = ['<table><tr><th>step</th><th>thread</th><th>what happens</th><th>source (line numbers at commit 30c4ac82cb)</th></tr>']
    for a_, b_, c_, d_ in rows:
        h.append('<tr><td class="num">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (esc(a_), esc(b_), esc(c_), esc(d_)))
    h.append('</table>')
    return "".join(h)


# ---------------------------------------------------------------- 2.4 inputs, outputs, functions
def dataflow_svg():
    """Three columns: what one save reads (left), who does the work (middle), what it writes
    and who reads that (right). Every arrow is an explicit edge from the source box's right
    (or bottom) edge to the target box's left (or top) edge. Labels sit inside boxes only."""
    W = 960
    COLS = [(10, 290), (345, 600), (670, 950)]      # x0, x1 of the three columns; 600..615 is the middle column's corridor
    CORR_X = 608
    CB = {"in": "#eef4fb", "in_s": "#0072b2", "mid": "#fbeeee", "mid_s": "#b02a2a", "out": "#eef8f3", "out_s": "#007a59", "arrow": "#6b6a67"}
    FS = 10.5
    LH = 13.5
    CH = 6.05  # px per character at 10.5 px system-ui (est.)

    def box(x0, x1, y, title, lines, fill, stroke):
        width_chars = int((x1 - x0 - 16) / CH)
        tw = wrap_lines(title, int(width_chars / 1.15))
        wrapped = []
        for ln in lines:
            wrapped += wrap_lines(ln, width_chars)
        h = 8 + LH * len(tw) + LH * len(wrapped) + 6
        o = ['<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="%s" stroke="%s"/>' % (x0, y, x1 - x0, h, fill, stroke)]
        for i, ln in enumerate(tw):
            o.append('<text x="%d" y="%d" font-size="%s" font-weight="600" fill="%s">%s</text>' % (x0 + 8, y + 8 + LH * (i + 1) - 3, FS, C["ink"], esc(ln)))
        for i, ln in enumerate(wrapped):
            o.append('<text x="%d" y="%d" font-size="%s" fill="%s">%s</text>' % (x0 + 8, y + 8 + LH * (len(tw) + i + 1) - 3, FS, C["muted"], esc(ln)))
        return "".join(o), h

    def column(col, items, fill, stroke, y0=40):
        out, geo, y = [], [], y0
        for title, lines in items:
            s, h = box(col[0], col[1], y, title, lines, fill, stroke)
            out.append(s)
            geo.append((y, y + h))
            y += h + 10
        return out, geo, y

    ins = [
        ("the item list of the minibatch", ["items[]: 1024 token job ids of the pass in the scheduler's order (unit boundaries follow it).",
                                            "token_jobs_do_kv[ix]: whether the job writes KV (every item of the traced prefill passes does; a job without it is skipped).",
                                            "token_jobs[ix] -> token id -> page_of(), offset_in_page(): the destination page, block c = offset / 16, column offset % 16."]),
        ("ks: the K buffer", ["1024 entries of 2048 bytes (one per item), each the token's 8 K rows of 256 bytes (8 KV heads x 128 bf16), the norm-and-rope output of the helpers' stripes. Read in place."]),
        ("operation.binding: kv_slot, model_layer", ["Which KV slot of the pages receives the rows (slot L for layer L in the generated qwen plugin), and the layer for the marks and the log records."]),
        ("n_workers", ["1 + the main helpers of this pass: %d at tp2, %d at tp4 in prefill. The handwritten plugins pass nothing (default 1)." % (HELPERS_PREFILL["tp2"] + 1, HELPERS_PREFILL["tp4"] + 1)]),
    ]
    mids = [
        ("main: save_k -> save_k_impl", ["Save K span. k_store_shared, k_store_cut_units, reset the counters, opened++, claim loop, join on finished, then marks, credits, latch."]),
        ("batch::k_store_window (4736 bytes)", ["next_unit, opened, finished, n_units, unit_start[1025], helper_windows[128]. Section 5. Main opens it, every claimer takes unit indexes from next_unit."]),
        ("%d or %d helpers: save_k_helper" % (HELPERS_PREFILL["tp2"], HELPERS_PREFILL["tp4"]), ["++helper_windows[worker_ix], spin on opened, claim loop, finished++. Called from the generated run_main_help at the same statement position."]),
        ("every claimer, per claimed unit u", ["store_k_block(items[unit_start[u] .. unit_start[u+1])), called by main and by every helper.", "run of 2..16 items -> page::set_k_block -> k_vnni::store_block (transpose, 16 stores per dim step and KV head: full-line for a full block, lane-masked for a partial one).",
                                                                                                  "run of 1 item -> page::set_k_row -> k_vnni::scatter_row (4 scatters per KV head)."]),
    ]
    outs = [
        ("K planes in the KV cache (DRAM)", ["%d planes of 16 KiB in pass 3: pages 4 and 5 of each user x 8 KV heads = 2 MiB per save. VNNI layout, every byte written once." % PLANES_PER_SAVE]),
        ("readers of the planes", ["This pass's Pending sections: k_vnni::qk_group (AVX-512; these pages are not dense for this pass's queries). Later passes' Ready sections and decode steps: qk_vnni_128x4 (AMX, dense pages) or k_vnni::qk_group (partial pages, kill switch).",
                                   "FPGA attention staging (when hardware attention is used): gof::populate -> page_info::k_head_fn -> page::get_k_row (gather). Defragmentation: book::append -> copy_storage_slot."]),
        ("mark_k_complete(slot, offset)", ["Per token, after the join, in item order: the page's per-token completion count. Consumed only by the FPGA GOF dispatch (page::is_kv_complete via page_info::kv_complete_fn) and by an assertion in fire_gof_rodeo. A page copy (page::copy_from, defragmentation) carries the counts to the new page. The CPU attention does not read it. Its gate is the latch."]),
        ("credit_gof_save (hardware slot only)", ["One save credit per GOF (group of four tokens) that holds the token. Drives the FPGA KV dispatch counter."]),
        ("upstream_kvs_ready[slot].count_down()", ["On every downstream minibatch (one in these runs). Together with save_v's count_down it releases the attention workers' Pending sections."]),
    ]
    o_in, g_in, y_in = column(COLS[0], ins, CB["in"], CB["in_s"])
    o_mid, g_mid, y_mid = column(COLS[1], mids, CB["mid"], CB["mid_s"])
    o_out, g_out, y_out = column(COLS[2], outs, CB["out"], CB["out_s"])
    cy = lambda g: (g[0] + g[1]) / 2
    ar = []
    line = lambda x1, y1, x2, y2: '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2" marker-end="url(#ah)"/>' % (x1, y1, x2, y2, CB["arrow"])
    # inputs -> middle: (input index, middle index)
    for i, j in [(0, 0), (0, 3), (1, 3), (2, 0), (2, 2), (3, 0), (3, 2)]:
        ar.append(line(COLS[0][1] + 2, cy(g_in[i]), COLS[1][0] - 3, cy(g_mid[j])))
    xm = (COLS[1][0] + COLS[1][1]) / 2
    ar.append(line(xm, g_mid[0][1] + 1, xm, g_mid[1][0] - 3))          # main -> window
    ar.append(line(xm, g_mid[2][0] - 1, xm, g_mid[1][1] + 3))          # helpers -> window (upwards)
    ar.append(line(xm, g_mid[2][1] + 1, xm, g_mid[3][0] - 3))          # helpers -> store_k_block
    ar.append('<polyline points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="none" stroke="%s" stroke-width="1.2" marker-end="url(#ah)"/>' % (
        COLS[1][1] + 1, cy(g_mid[0]) + 14, CORR_X, cy(g_mid[0]) + 14, CORR_X, cy(g_mid[3]), COLS[1][1] + 3, cy(g_mid[3]), CB["arrow"]))   # main -> store_k_block via the corridor
    ar.append(line(COLS[1][1] + 2, cy(g_mid[3]) - 10, COLS[2][0] - 3, cy(g_out[0])))     # store_k_block -> K planes
    xo = (COLS[2][0] + COLS[2][1]) / 2
    ar.append(line(xo, g_out[0][1] + 1, xo, g_out[1][0] - 3))          # K planes -> readers
    for j in (2, 3, 4):
        ar.append(line(COLS[1][1] + 2, cy(g_mid[0]) - 8 + 4 * (j - 3), COLS[2][0] - 3, cy(g_out[j])))   # main -> marks, credits, latch
    H = max(y_in, y_mid, y_out) + 20
    head = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Inputs, work and outputs of one shared save" xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;">' % (W, H, W, H),
            '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker></defs>' % CB["arrow"],
            '<text x="%d" y="18" font-size="12" font-weight="600" fill="%s">what one save reads</text>' % (COLS[0][0], CB["in_s"]),
            '<text x="%d" y="18" font-size="12" font-weight="600" fill="%s">who does the work (one layer, one pass)</text>' % (COLS[1][0], CB["mid_s"]),
            '<text x="%d" y="18" font-size="12" font-weight="600" fill="%s">what it writes, and who reads that</text>' % (COLS[2][0], CB["out_s"])]
    return "".join(head + o_in + o_mid + o_out + ar + ['</svg>'])


def functions_table():
    rows = [
        ("emitter (build time)", "runStatement: MatmulFillStmt, MatmulPrepareStmt, MatmulLaunchStmt", "ingest, Haskell", "The layer's projection matmuls on the FPGA cards, emitted for main only. matmulLaunch starts writing the output channel and finishes it from the completion callback, so the rows arrive per token.", L["emit_matmul"]),
        ("emitter (build time)", "submitAttentionOperation, saveKv", "ingest, Haskell", "Emits main's attention block for a KV-writing operation: launch_early_hw_attention, K channel waits, save_k(.., n_workers), V channel waits, save_v, prepare_late_hw_attention, launch_late_hw_attention.", L["emit_main"]),
        ("emitter (build time)", "runHelperStatement, runHelpMethod", "ingest, Haskell", "Emits the helpers' run_main_help. At the attention statement of a KV-writing operation: save_k_helper(.., worker_ix, n_workers). Same statement position as main's save_k.", L["emit_help"] + "; " + L["emit_run_help"]),
        ("emitter (build time)", "staticStrategy, Note [Main Thread Skips Helper Kernels]", "ingest, Haskell", "The helpers' per-token kernels (norm, rope): item = first + actual_worker_ix, step n_actual_workers. start_reading_at per item on the read channels, finish_writing_at per item on the written channels. So the K channel of an item closes when its rows are roped.", L["strategy"]),
        ("run time, per pass", "recommend_n_main_helpers, available_main_parallelism", "model.hpp, generated plugin", "The main-helper count of a pass. With one minibatch it is the fixed split (pool workers x 2) / 7. It is then capped by the plugin's available_main_parallelism(items) = items x the largest MoE top-k (MoE = mixture of experts; qwen3-4b has none, so the factor is 1 and the cap is the item count) and by the min/max limits. Traces: 7 helpers at tp2 in prefill and decode, 15 at tp4 in prefill, 8 at tp4 in decode.", L["helpers_rule"]),
        ("run time, main", "save_k -> save_k_impl", "model.hpp", "Entry (default n_workers = 1) and the body: Save K span, sharing decision, cut, window, claim loop, join, marks, credits, latch.", L["save_k"] + "; " + L["save_k_impl"]),
        ("run time, main and every helper", "k_store_shared", "model.hpp", "layout_on for the head size, 1 < n_workers <= 128, items > 16. The same answer on main and on every helper.", L["shared"]),
        ("run time, main", "k_store_cut_units", "model.hpp", "items -> unit_start[], n_units. A unit ends where the KV flag, the page or the 16-token block changes.", L["cut"]),
        ("run time, helpers", "save_k_helper", "model.hpp", "Window count, spin on opened, claim loop, finished++. Two overloads (generated operation index, descriptor).", L["helper"]),
        ("run time, every claimer", "store_k_block", "model.hpp", "A unit -> runs -> set_k_block or set_k_row per KV head. Converts non-bf16 rows to bf16 on the stack (not needed for qwen3-4b: bf16 buffers).", L["store_k_block"]),
        ("run time, every claimer", "page::set_k_block -> k_vnni::store_block, transpose_16x16_epi32", "kv_cache.hpp, k_vnni.hpp", "The block store, per KV head: 4 dim steps, each with one load per present row, the 16 x 16 transpose of 32-bit lanes, 16 stores (full-line for a full block, lane-masked for a partial one).", ", ".join([L["set_k_block"], L["store_block"], L["transpose"]])),
        ("run time, every claimer", "page::set_k_row -> k_vnni::scatter_row", "kv_cache.hpp, k_vnni.hpp", "The per-token store: 4 scatters of 16 dwords (4-byte values, one dimension pair each), one per dim step. Used for a run of one token.", L["set_k_row"] + "; " + L["scatter"]),
        ("run time, main, after the join", "page::mark_k_complete, credit_gof_save, upstream_kvs_ready.count_down", "kv_cache.hpp, model.hpp", "Completion marks per token, GOF credits (hardware slot), and the latch that releases the Pending sections (together with the V save's count).", L["mark"] + "; " + L["marks"] + "; " + L["latch_reset"]),
        ("run time, FPGA GOF dispatch", "page::is_kv_complete via page_info::kv_complete_fn; fire_gof_rodeo assertion", "kv_cache.hpp, scheduler/full.hpp, model.hpp", "The only consumers of the completion marks: the GOF dispatch and its assertion. page::copy_from copies the counters along with a page. The CPU attention does not read them.", L["is_kv_complete"] + "; " + L["gof_readers"]),
        ("run time, main", "save_v -> save_v_impl", "model.hpp", "The V save, serial on main. Not part of the window (the V plane pairs two tokens in one lane).", L["save_v"]),
        ("run time, attention workers", "run_attention_job: run_sections (ready), upstream_kvs_ready.wait, run_sections (pending)", "self_attention.hpp", "Reads the planes: this pass's Pending sections with k_vnni::qk_group (in these runs the pages are not dense for this pass's queries), later passes' Ready sections with the AMX kernel qk_vnni_128x4 on page::k_vnni_plane for dense pages and k_vnni::qk_group for partial pages and the kill switch.", ", ".join([L["ready"], L["wait"], L["pending"], L["dense"], L["amx"], L["plane"], L["sw"]])),
        ("run time, FPGA attention staging", "gof::populate -> page_info::k_head_fn -> page::get_k_row -> k_vnni::gather_row", "gof.hpp, kv_cache.hpp, k_vnni.hpp", "Rebuilds one row per token from the plane for the FPGA KV staging (not used in the traced CPU-attention runs).", L["gof"] + "; " + L["get_k_row"] + "; " + L["gather"]),
        ("run time, defragmentation", "book::append -> page::copy_from -> copy_storage_slot", "kv_cache.hpp", "Copies a book (the KV cache allocation that holds a run of pages) onto the end of another after tree-shaped speculation (speculative decoding: several candidate continuations are kept as a tree of books, and the accepted branch is compacted afterwards). A whole-page memcpy when the range covers the page, else gather + scatter per token. copy_storage_slot has no other caller.", L["copy"] + "; " + L["note_vnni"]),
    ]
    h = ['<table><tr><th>when, who</th><th>function</th><th>file</th><th>role in the save</th><th>source</th></tr>']
    for a, b, c, d, e in rows:
        h.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (esc(a), esc(b), esc(c), esc(d), esc(e)))
    h.append('</table>')
    return "".join(h)


# ---------------------------------------------------------------- 3 the two remedies together
def remedies_matrix():
    r = MEAS_ROUNDED
    cell = lambda n2, n4, cfg: '%s / %s us (%s)' % (r[n2], r[n4], cfg)
    h = ['<table><tr><th>who writes (shared save) \\ how a block is written (block store)</th><th>64 scatters per block and KV head: 4 bytes into each of 16 lines per scatter, every line written 16 times</th><th>transpose in registers, 64 full-line stores per block and KV head</th></tr>']
    h.append('<tr><td>main alone</td><td class="num">%s</td><td class="num">%s</td></tr>' % (cell("vnni0-tp2", "vnni0-tp4", "vnni0"), cell("a-tp2", "a-tp4", "a")))
    h.append('<tr><td>main + the idle helpers (%d at tp2, %d at tp4)</td><td class="num">%s</td><td class="num">%s</td></tr>' % (HELPERS_PREFILL["tp2"], HELPERS_PREFILL["tp4"], cell("b-tp2", "b-tp4", "b"), cell("ab-tp2", "ab-tp4", "ab")))
    h.append('<tr><td>reference: the row-major store of the binary before VNNI K (main alone, 4 full-line stores per K row)</td><td class="num" colspan="2">%s / %s us (base)</td></tr>' % (r["base-tp2"], r["base-tp4"]))
    h.append('</table>')
    return "".join(h)


def factor(a, b):
    return MEAN[a] / MEAN[b]


FACT = {
    "block_alone": (factor("vnni0-tp2", "a-tp2"), factor("vnni0-tp4", "a-tp4")),
    "shared_alone": (factor("vnni0-tp2", "b-tp2"), factor("vnni0-tp4", "b-tp4")),
    "both": (factor("vnni0-tp2", "ab-tp2"), factor("vnni0-tp4", "ab-tp4")),
    "block_when_shared": (factor("b-tp2", "ab-tp2"), factor("b-tp4", "ab-tp4")),
    "shared_when_block": (factor("a-tp2", "ab-tp2"), factor("a-tp4", "ab-tp4")),
    "ab_vs_base": (factor("base-tp2", "ab-tp2"), factor("base-tp4", "ab-tp4")),
    "vnni0_vs_base": (factor("vnni0-tp2", "base-tp2"), factor("vnni0-tp4", "base-tp4")),
}


def factors_table():
    rows = [
        ("block store alone (vnni0 -> a)", FACT["block_alone"]),
        ("shared save alone (vnni0 -> b)", FACT["shared_alone"]),
        ("both (vnni0 -> ab)", FACT["both"]),
        ("block store, added to the shared save (b -> ab)", FACT["block_when_shared"]),
        ("shared save, added to the block store (a -> ab)", FACT["shared_when_block"]),
        ("both, against the row-major store of before (base -> ab)", FACT["ab_vs_base"]),
    ]
    h = ['<table><tr><th>step (a factor = the Save K span before the step divided by the span after it)</th><th>factor at tp2</th><th>factor at tp4</th></tr>']
    for a, (v2, v4) in rows:
        h.append('<tr><td>%s</td><td class="num">%.2fx</td><td class="num">%.2fx</td></tr>' % (esc(a), v2, v4))
    h.append('</table>')
    return "".join(h)


def remedies_svg():
    """Dot plot: one row per configuration, Save K us per prefill layer on a linear axis, a
    hollow ring for tp4 and a smaller filled dot for tp2 (so coincident values read as a dot
    inside a ring), direct labels, the factor of each remedy step at the right."""
    rows = [("base: row-major, main alone", "base"), ("vnni0: scatter, main alone", "vnni0"), ("a: block store, main alone", "a"), ("b: scatter, main + helpers", "b"), ("ab: block store, main + helpers", "ab")]
    W, LEFT, RIGHT = 960, 250, 300
    X1 = 900.0
    px = lambda v: LEFT + v / X1 * (W - LEFT - RIGHT)
    ROW = 34
    y0 = 44
    BLUE = "#0072b2"
    Hh = y0 + ROW * len(rows) + 60
    out = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Save K per prefill layer for the four configurations and the row-major reference" xmlns="http://www.w3.org/2000/svg" style="font-family:system-ui,sans-serif;">' % (W, Hh, W, Hh)]
    out.append('<text x="10" y="16" font-size="14" font-weight="600" fill="%s">Save K per prefill layer, us (shorter is better); filled dot = tp2, ring = tp4</text>' % C["ink"])
    out.append('<text x="10" y="32" font-size="11" fill="%s">qwen3-4b, 8 users, prompt 1024; traces of commit 9928cb2849 (vnni0, a, b, ab) and of the row-major binary (base); means over 8 prefill passes</text>' % C["muted"])
    ax_y = y0 + ROW * len(rows) + 8
    for v in range(0, 901, 100):
        x = px(v)
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#e6e5e1"/>' % (x, y0 - 6, x, ax_y))
        out.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">%d</text>' % (x, ax_y + 15, C["muted"], v))
    out.append('<line x1="%d" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>' % (LEFT, ax_y, px(X1), ax_y, C["muted"]))
    notes = {"base": ["reference: the store before VNNI K"], "vnni0": ["%.1fx / %.1fx longer than base" % FACT["vnni0_vs_base"]], "a": ["%.2fx / %.2fx shorter than vnni0" % FACT["block_alone"]],
             "b": ["%.2fx / %.2fx shorter than vnni0" % FACT["shared_alone"]], "ab": ["%.1fx / %.1fx shorter than vnni0" % FACT["both"], "%.1fx / %.1fx shorter than base" % FACT["ab_vs_base"]]}
    for i, (label, cfg) in enumerate(rows):
        y = y0 + ROW * i + ROW / 2
        out.append('<rect x="%d" y="%.1f" width="%d" height="%d" fill="%s"/>' % (LEFT, y - ROW / 2 + 2, W - LEFT - RIGHT, ROW - 4, "#f7f6f3" if i % 2 == 0 else "#fcfcfb"))
        out.append('<text x="%d" y="%.1f" font-size="12" text-anchor="end" fill="%s">%s</text>' % (LEFT - 8, y + 4, C["ink"], esc(label)))
        v2, v4 = MEAS_ROUNDED[cfg + "-tp2"], MEAS_ROUNDED[cfg + "-tp4"]
        x2, x4 = px(v2), px(v4)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (min(x2, x4), y, max(x2, x4), y, BLUE))
        out.append('<circle cx="%.1f" cy="%.1f" r="6" fill="#fff" stroke="%s" stroke-width="2"/>' % (x4, y, BLUE))
        out.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s" stroke="#fff" stroke-width="1"/>' % (x2, y, BLUE))
        if max(v2, v4) > 600:
            out.append('<text x="%.1f" y="%.1f" font-size="11" text-anchor="end" fill="%s">%d / %d</text>' % (min(x2, x4) - 10, y + 4, C["ink"], v2, v4))
        else:
            out.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s">%d / %d</text>' % (max(x2, x4) + 10, y + 4, C["ink"], v2, v4))
        for j, ln in enumerate(notes[cfg]):
            dy = (j - (len(notes[cfg]) - 1) / 2) * 12
            out.append('<text x="%d" y="%.1f" font-size="11" fill="%s">%s</text>' % (W - RIGHT + 8, y + 4 + dy, C["savek"] if cfg == "ab" else C["muted"], esc(ln)))
    out.append('<text x="%d" y="%d" font-size="11" fill="%s">Save K, us per prefill layer (tp2 / tp4, rounded means; the factors at the right use the unrounded means)</text>' % (LEFT, ax_y + 32, C["muted"]))
    out.append('</svg>')
    return "".join(out)


def ttft_ms(arm, tp):
    return 1000.0 * TTFT_CELLS[(arm, tp)]["ttft_mean"]


def ttft_sd(arm, tp):
    return 1000.0 * TTFT_CELLS[(arm, tp)]["ttft_sd"]


def ttft_table():
    h = ['<table><tr><th>configuration</th><th>TTFT at tp2, ms (n = %d runs: the mean, with the standard deviation (sd) in parentheses)</th><th>against vnni0, ms</th><th>TTFT at tp4, ms (n = %d runs: mean and sd)</th><th>against vnni0, ms</th></tr>' % (TTFT_CELLS[("vnni0", "tp2")]["n"], TTFT_CELLS[("vnni0", "tp4")]["n"])]
    for arm, word in (("vnni0", "vnni0: both remedies off"), ("a", "a: block store only"), ("b", "b: shared save only"), ("ab", "ab: both")):
        h.append('<tr><td>%s</td><td class="num">%.0f (sd %.0f)</td><td class="num">%+.0f</td><td class="num">%.0f (sd %.0f)</td><td class="num">%+.0f</td></tr>' % (
            esc(word), ttft_ms(arm, "tp2"), ttft_sd(arm, "tp2"), ttft_ms(arm, "tp2") - ttft_ms("vnni0", "tp2"), ttft_ms(arm, "tp4"), ttft_sd(arm, "tp4"), ttft_ms(arm, "tp4") - ttft_ms("vnni0", "tp4")))
    h.append('</table>')
    return "".join(h)


def scope_table():
    dec = lambda n: D(n)["save_k_us_per_layer"]
    dsd = lambda n: D(n)["save_k_us_per_layer_sd"]
    sv = lambda n: P(n)["save_v_us_per_layer"]
    rows = [
        ("prefill pass, a run of 16 tokens that fills one block (the report's runs: all 64 units full)", "yes (transpose, full-line stores)", "yes (64 units, %d or %d threads)" % (HELPERS_PREFILL["tp2"] + 1, HELPERS_PREFILL["tp4"] + 1), "the 2 x 2 above"),
        ("prefill pass, a run of 2 to 15 tokens (a partial block: a pass that starts or ends inside a block, or a job without KV work between the items of one block)", "yes, with a lane mask", "yes (the run is a unit of its own)", "k_vnni.hpp store_block (masked stores); common.hpp k_store_window_t comment; section 4.2 units 0, 2, 3, 5, 7"),
        ("a run of one token inside a prefill pass (an item alone in its block)", "no: scatter_row", "yes (a unit of one item)", "model.hpp store_k_block K_SCATTER_RUN_LEN_1; section 4.2 unit 6"),
        ("decode pass (8 items, one token per user)", "no: every run has one token", "no: items <= 16, no window", "decode Save K per layer the same within the step-to-step spread: vnni0 %.1f / %.1f us, ab %.1f / %.1f us (tp2 / tp4; standard deviation over the 8 decode steps %.1f to %.1f us); a %.1f / %.1f, b %.1f / %.1f" % (
            dec("vnni0-tp2"), dec("vnni0-tp4"), dec("ab-tp2"), dec("ab-tp4"), min(dsd(n) for n in ("vnni0-tp2", "vnni0-tp4", "ab-tp2", "ab-tp4", "a-tp2", "a-tp4", "b-tp2", "b-tp4")), max(dsd(n) for n in ("vnni0-tp2", "vnni0-tp4", "ab-tp2", "ab-tp4", "a-tp2", "a-tp4", "b-tp2", "b-tp4")),
            dec("a-tp2"), dec("a-tp4"), dec("b-tp2"), dec("b-tp4"))),
        ("the V save (save_v)", "no: the V layout is unchanged", "no: two tokens share one 32-bit lane", "model.hpp save_v_impl comment; Save V per layer %.0f / %.0f us (ab), now the longer of the two saves" % (sv("ab-tp2"), sv("ab-tp4"))),
        ("handwritten plugins (llama.hpp): n_workers = 1 (the default argument)", "yes", "no", "model.hpp save_k default argument; k_store_shared"),
        ("unit test t_llama_unit, one-thread case: n_workers = 1", "yes", "no (opened stays 0)", L["test"]),
        ("unit test t_llama_unit, three-thread case: main + 2 helper threads, 48 items, 9 units", "yes", "yes (section 4.2 reproduces its units)", L["test"]),
        ("more than 128 workers", "yes", "no", "common.hpp MAX_SHARED_WORKERS_128"),
        ("row-major K (TRON_K_VNNI off, or a head size other than 128)", "no: the per-token row store of before", "no", "model.hpp store_k_block (the !layout_on branch); k_vnni.hpp layout_on"),
    ]
    h = ['<table><tr><th>case</th><th>block store applies</th><th>shared save applies</th><th>evidence</th></tr>']
    for a, b, c, e in rows:
        h.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (esc(a), esc(b), esc(c), esc(e)))
    h.append('</table>')
    return "".join(h)


# ---------------------------------------------------------------- the HTML of sections 2 and 3
def context_html():
    b, a = M[BEFORE], M[AFTER]
    sb, sa = SPANS[BEFORE], SPANS[AFTER]
    H = []
    H.append('<h2>2. Where the save sits: the stage of prefill, its inputs and its outputs</h2>')
    H.append('<p>This section and the next were added on 2026-09-18. They answer three questions about the shared save before the page goes into the details of the window: at which point of prefill it runs, what data goes in and comes out, and which functions and threads take part. Section 3 then relates it to the block store. Line numbers are those of the worktree at commit 30c4ac82cb (the PR 4424 head). The cited files model.hpp, common.hpp, k_vnni.hpp, self_attention.hpp and TronCpp.hs are byte-identical to commit 04ffeedccb, the commit that revisions 1 to 4 of this page read. kv_cache.hpp differs in three wording lines with the same line count, and the page_info comment of gof.hpp (lines 61-77) was rewritten.</p>')
    H.append('<h3>2.1 Three levels: the run, the pass, the layer</h3>')
    H.append('<p>The run has 8 users. Each user sends a 1024-token prompt. The scheduler prefills the prompts in passes of 128 tokens per user (a chunk). So a prompt takes 8 prefill passes, and every prefill pass holds 1024 items. A pass runs the 36 layers of qwen3-4b in order. Every layer has one attention operation that writes KV. So every layer calls save_k once, and with more than 16 items that call opens one window. The tree below places the window inside the run. The table after it counts the windows of a prefill, the K rows one window stores, the threads in a window, and the Save K time of a pass.</p>')
    H.append('<div class="scroll">' + levels_tree() + '</div>')
    H.append('<div class="scroll">' + levels_table() + '</div>')
    H.append('<p class="take">Reading: a prefill of the 8 prompts runs 288 windows. Each stores 2 MiB of K rows. Before the remedies the 36 saves of a pass took %.1f ms of a %.0f ms pass at tp2 (%.1f%%). With both remedies they take %.1f ms (%.1f%%). At tp4 the share fell from %.1f%% to %.1f%%. In decode there is no window: a decode pass has 8 items.</p>' % (
        P("vnni0-tp2")["save_k_ms"], P("vnni0-tp2")["pass_ms"], 100 * P("vnni0-tp2")["save_k_ms"] / P("vnni0-tp2")["pass_ms"],
        P("ab-tp2")["save_k_ms"], 100 * P("ab-tp2")["save_k_ms"] / P("ab-tp2")["pass_ms"],
        100 * P("vnni0-tp4")["save_k_ms"] / P("vnni0-tp4")["pass_ms"], 100 * P("ab-tp4")["save_k_ms"] / P("ab-tp4")["pass_ms"]))

    H.append('<h3>2.2 One layer: what runs before, during and after the save (measured)</h3>')
    H.append('<p>The figure draws layer 10 of prefill pass 3 (the traces count layers from 0, so this is the 11th layer of the pass, window W = 11 of the glossary) from the report\'s traces, as who-does-what-when lanes to scale, twice: both remedies off (configuration vnni0) and both on (configuration ab), tp2, the same binary (commit 9928cb2849). Time 0 is the start of the layer\'s Save K. The 7 helpers are drawn as one envelope lane (first start to last end over the 7 threads). The 20 attention workers are drawn as three envelope lanes, one per span kind. Solid blocks are recorded spans. Dashed outlines are gaps between a thread\'s spans (waiting), or time in which main has no span. Main\'s work outside its two spans is not traced, and is not idleness. The helpers\' claims in the "after" chart are drawn from the code: save_k_helper has no trace span.</p>')
    H.append('<div class="fig">' + stage_svg() + '</div>')
    H.append('<p class="take">What the two charts show. (1) The helpers\' fused kernel (one kernel into which the ingest merged four per-token steps: the norm and the rope of Q, then of K) ends %s to %s us before Save K starts in the "before" chart, and %s to %s us before it in the "after" chart: main waited for the last K rows. (2) In the "before" chart the helpers are idle from then until the residual-add kernel at %s us. Save K (%s us) lies inside that idle interval of the helpers. That idle time is what the shared save uses. (3) The attention workers start their Ready sections (the pages of the earlier chunks) %s us ("before") and %s us ("after") after Save K starts, and run them during the save. (4) Their Pending sections (this pass\'s pages) start %s us after Save V (the trace span of save_v_impl, the V save that follows Save K on main) ends: the latch needs both saves. (5) The layer end (the end of the last attention join span) moved from %s us to %s us, by %s us. Save K shrank by %s us. The first Pending start moved by %s us. So in this traced layer the whole Save K span was on the critical path of the layer.</p>' % (
        f1(-b["rope_end_min"]), f1(-b["rope_end_max"]), f1(-a["rope_end_min"]), f1(-a["rope_end_max"]), f0(b["next_start"]), f0(b["save_k"]), f1(b["ready_first"]), f1(a["ready_first"]), f1(b["pending_first"] - b["save_v_end"]),
        f0(b["join_last_end"]), f0(a["join_last_end"]), f0(LAYER_END_SHIFT), f0(SAVE_K_SHIFT), f0(PENDING_SHIFT)))
    H.append('<p class="take">This is one traced layer per configuration, not a mean. Single Save K spans spread around the run mean. Over the %d spans of the run (36 layers x 8 prefill passes) the standard deviation is %.0f us for vnni0 (spans from %.0f to %.0f us) and %.0f us for ab (%.0f to %.0f us) at tp2. The pass-to-pass standard deviation of the per-pass mean is smaller: %.1f us (vnni0) and %.1f us (ab). The traced layer\'s %s us and %s us lie inside the single-span spread around the means %s us and %s us that sections 3.2 and 6.6 use.</p>' % (
        sb["n"], sb["sd"], sb["min"], sb["max"], sa["sd"], sa["min"], sa["max"], P(BEFORE)["save_k_us_per_layer_sd"], P(AFTER)["save_k_us_per_layer_sd"], f0(b["save_k"]), f0(a["save_k"]), MEAS_ROUNDED[BEFORE], MEAS_ROUNDED[AFTER]))
    H.append('<p>The same milestones for all 12 traced configurations (layer 10 of prefill pass 3; set 1 = the 2026-09-14 traces of the base and vnni binaries, set 2 = the 2026-09-15 traces of commit 9928cb2849). The helper and attention-worker counts are the threads with kernel spans and with attention spans inside the window:</p>')
    H.append('<div class="scroll">' + stage_table() + '</div>')
    late = ", ".join("%s (%s us after)" % (n, f2(M[n]["rope_end_max"])) for n in ROPE_LATE) if ROPE_LATE else "none"
    H.append('<p class="take">Across the 12 rows the helpers\' rope kernels end between %.1f us before the Save K start and %.2f us after it. Rows with a rope span ending after the start: %s. The first Pending section starts %.1f to %.1f us after Save V ends in every row. At tp2 a window has %d helpers in every pass. At tp4 it has %d helpers in a prefill pass and %d in a decode pass: the helper count of a pass is capped by the item count, among other limits [%s]. The report\'s section 1 gives the decode split for tp4 (1 + 8 + 47). Its section 2.2 figures label the prefill split (15 and 40). Its section 4.3 table and reading also use the decode split for the tp4 prefill rows (the helper column reads \'of 8\', and the reading says \'7.9x with 8 helpers at tp4, the ideal is 9x\'). With the 15 helpers of a prefill window the ideal factor is 16x. No trace of the head protocol (page-block units, one join counter) exists. Section 6.6 says the same about the Save K span.</p>' % (
        -ROPE_LO, ROPE_HI, late, PEND_GAP_LO, PEND_GAP_HI, HELPERS_PREFILL["tp2"], HELPERS_PREFILL["tp4"], HELPERS_DECODE["tp4"], L["helpers_rule"]))

    H.append('<h3>2.3 The statement order around the save, in the generated qwen plugin</h3>')
    H.append('<p>The ingest (the Haskell code generator, ingest/src) emits two methods per model: run() for the main thread and run_main_help() for the helpers. Both walk the same statement list. So the helpers reach the attention statement of a layer at the same position of their list as main does. The steps of one layer around the save:</p>')
    H.append('<div class="scroll">' + order_table() + '</div>')

    H.append('<h3>2.4 What one save reads, what it writes, and who reads that</h3>')
    H.append('<div class="fig">' + dataflow_svg() + '</div>')
    H.append('<p class="take">The save moves data only. It reads 1024 K buffer entries of 2048 bytes (8192 K rows of 256 bytes) and writes the same 2 MiB into the K planes of 16 pages, in the VNNI layout. Nothing is computed on the values: the block store transposes 32-bit lanes, and the scatter moves 4-byte pairs. That is why the report\'s greedy-agreement check (report section 5) must give identical output tokens in every configuration. That check runs each configuration with greedy decoding (temperature 0: tron takes the highest-scoring token at every step) and compares 128 generated tokens. The side effects of the save are the completion marks, the GOF credits and the latch count. The readers of the planes are listed in the right column of the figure above.</p>')
    H.append('<p>The functions, in the order they take part:</p>')
    H.append('<div class="scroll">' + functions_table() + '</div>')

    H.append('<h2>3. How the shared save and the block store fit together</h2>')
    H.append('<h3>3.1 Two remedies, two questions</h3>')
    H.append('<p>The report built two remedies for the slow VNNI K store [report section 3]. They answer different questions.</p>')
    H.append('<ul><li><b>The block store answers "how is one 16-token block written?"</b> Before: 64 scatters per block and KV head. Each scatter writes 4 bytes into each of 16 lines. So every one of the block\'s 64 lines receives 16 partial writes. After: per dim step 16 loads, one 16 x 16 transpose of 32-bit lanes in registers and 16 full-line stores, so 64 loads, 4 transposes and 64 full-line stores per block and KV head [k_vnni.hpp store_block; the companion page block-store-animation.html].</li>'
             '<li><b>The shared save answers "who writes the blocks?"</b> Before: main alone, while the %d (tp2) or %d (tp4) helpers were idle. After: main and the helpers claim units from one counter [model.hpp Note [Shared block save]].</li>'
             '<li><b>They meet in one function.</b> store_k_block is what every thread calls for each unit it claims, and the block store is inside it. A unit of the shared save fits inside one block of the block store: a unit never crosses a 16-token page block [model.hpp k_store_cut_units]. So a claimed full unit is exactly the input of one store_block call per KV head, 8 calls for qwen3-4b. Section 4.1 lists the 64 units of the pass. The companion page plays one of those store_block calls.</li>'
             '<li><b>Both are on at head, without switches.</b> The report measured them apart with the switches TRON_K_VNNI_BLOCK and TRON_K_VNNI_STRIPE of commit 9928cb2849. Commit ec1be6dde4 removed the switches.</li></ul>' % (HELPERS_PREFILL["tp2"], HELPERS_PREFILL["tp4"]))
    H.append('<h3>3.2 Measured: the 2 x 2 of who and how</h3>')
    H.append('<p>Save K per prefill layer, us, tp2 / tp4, from the report\'s traces (report section 4.3; the means over 8 prefill passes, rounded to whole us): the rows are who writes, the columns are how a block is written. The factors below the chart are computed from the unrounded means of analysis.json.</p>')
    H.append('<div class="scroll">' + remedies_matrix() + '</div>')
    H.append('<div class="fig">' + remedies_svg() + '</div>')
    H.append('<div class="scroll">' + factors_table() + '</div>')
    H.append('<p class="take">Reading the factors. Alone, the block store cuts the span %.2fx (tp2) and %.2fx (tp4). Alone, the shared save cuts it %.2fx and %.2fx. Together they cut it %.1fx and %.1fx. The two factors do not multiply in full: %.2f x %.2f = %.1f at tp2 against %.1f measured, and %.2f x %.2f = %.1f at tp4 against %.1f measured. Once the save is shared, the block store adds only %.2fx (tp2) and %.2fx (tp4). A hypothesis, consistent with section 6.6: the parts of the window that the block store does not shorten (the cut, the helpers\' arrival, the join wait and the marks loop) are a larger share of a short window. No per-thread trace of the window exists to confirm it. With both remedies the VNNI Save K is %.1fx (tp2) and %.1fx (tp4) shorter than the row-major store of the binary before VNNI K. Before the remedies it was %.1fx longer.</p>' % (
        FACT["block_alone"] + FACT["shared_alone"] + FACT["both"] + (FACT["block_alone"][0], FACT["shared_alone"][0], round(FACT["block_alone"][0], 2) * round(FACT["shared_alone"][0], 2), FACT["both"][0], FACT["block_alone"][1], FACT["shared_alone"][1], round(FACT["block_alone"][1], 2) * round(FACT["shared_alone"][1], 2), FACT["both"][1]) + FACT["block_when_shared"] + FACT["ab_vs_base"] + (FACT["vnni0_vs_base"][0],)))
    H.append('<p>The same four configurations at the level the report was written for, TTFT (time to first token, here the batched prefill time of the 8 prompts) at prompt 1024 [report sections 4.1 and 4.2, runtron cells of the same campaign]. The differences in the table and in the paragraph below are computed from the unrounded means, so a difference can be 1 ms off the difference of two rounded cells.</p>')
    H.append('<div class="scroll">' + ttft_table() + '</div>')
    d_b_ab = (ttft_ms("b", "tp2") - ttft_ms("ab", "tp2"), ttft_ms("b", "tp4") - ttft_ms("ab", "tp4"))
    d_a_ab = (ttft_ms("a", "tp2") - ttft_ms("ab", "tp2"), ttft_ms("a", "tp4") - ttft_ms("ab", "tp4"))
    sd_max = (max(ttft_sd(x, "tp2") for x in ("a", "b", "ab")), max(ttft_sd(x, "tp4") for x in ("a", "b", "ab")))
    crit = (2 * sd_max[0], 2 * sd_max[1])
    verdict = lambda d, tp_i: "resolved" if abs(d) > crit[tp_i] else "not resolved"
    H.append('<p class="take">At the TTFT level, adding the block store to the shared save lowers TTFT by a further %.0f ms at tp2 and %.0f ms at tp4 (b against ab). Adding the shared save to the block store lowers it by a further %.0f ms at tp2 and %.0f ms at tp4 (a against ab). The run-to-run standard deviations of these cells are at most %.0f ms (tp2) and %.0f ms (tp4). Section 6.6 counts a difference as resolved when it exceeds twice the standard deviation. By that criterion the block store\'s further reduction is %s at tp2 (%.0f against %.0f ms) and %s at tp4 (%.0f against %.0f ms, from %d runs per cell). The shared save\'s further reduction is %s at tp2 (%.0f against %.0f ms) and %s at tp4 (%.0f against %.0f ms). The block store is the only remedy the n_workers = 1 paths get (section 3.3), and the shared save is the larger of the two in a prefill pass.</p>' % (
        d_b_ab[0], d_b_ab[1], d_a_ab[0], d_a_ab[1], sd_max[0], sd_max[1],
        verdict(d_b_ab[0], 0), d_b_ab[0], crit[0], verdict(d_b_ab[1], 1), d_b_ab[1], crit[1], TTFT_CELLS[("ab", "tp4")]["n"],
        verdict(d_a_ab[0], 0), d_a_ab[0], crit[0], verdict(d_a_ab[1], 1), d_a_ab[1], crit[1]))
    H.append('<h3>3.3 Where each remedy applies, and where it does not</h3>')
    H.append('<div class="scroll">' + scope_table() + '</div>')
    H.append('<p class="take">Two consequences. In decode neither remedy acts. So the decode Save K is the same in the four VNNI configurations, within the step-to-step spread. The report\'s section 2.3 shows that in decode this Save K is hidden behind the attention workers\' Ready sections. In prefill, with both remedies on, Save V (%.0f us per layer at tp2) is now longer than Save K (%.0f us). Save V is serial on main and is not part of the window.</p>' % (
        P("ab-tp2")["save_v_us_per_layer"], P("ab-tp2")["save_k_us_per_layer"]))
    return "\n".join(H)


def context_words():
    """Extra rows for the Words used here table (the rows of gen_page.py come first)."""
    return [
        ("Q, K, V, norm, residual add, projection matmul, MLP", "Q, K and V are the query, key and value vectors of a token in one layer. The layer's projection matmuls (matrix multiplications of the layer input with the weight matrices, run on the FPGA cards) produce them. K and V are what the saves store into the KV cache. Q is scored against the stored keys by the attention. norm: the RMS (root mean square) normalisation layer (rmsnorm) applied to a token's vector. In qwen3-4b a norm is applied to Q and to K before rope. residual add: adding a sub-layer's output to its input (the helper kernel add_rmsnorm does the add and the following norm). MLP: the feed-forward block of a layer, after attention."),
        ("K row, K buffer entry", "A K row is one token's K vector for one KV head: 128 bf16 values = 256 bytes (the report's meaning, and the unit set_k_row stores). A K buffer entry is one item's 8 K rows in ks: 2048 bytes for qwen3-4b. One save stores 1024 entries = 8192 K rows = 2 MiB. Where sections 4 to 6 say 'rows of the K buffer' or 'rows roped by', they mean entries."),
        ("KV slot, kv_slot, slot", "The K and V storage of one attention operation inside every page, numbered independently of the operation (kv_slot_id). The generated qwen plugin uses one slot per layer: slot L for layer L (uniformKvSlot). So a page holds 36 slots, and the save of layer L writes slot L of the token's page. The destination of one K row is (page, slot, KV head, offset) [%s]." % L["slot"]),
        ("bf16, dword", "bf16 is the 16-bit brain floating-point format: 2 bytes per value. Every K value is bf16. A dword (double word) is a 4-byte value: one dimension pair of one token in the VNNI plane."),
        ("Save V", "The Perfetto trace span of save_v_impl, the function that stores the V rows of a pass into the KV cache, serial on main, once per layer per pass, right after Save K [%s]." % L["save_v"]),
        ("Ready section, Pending section", "The two halves of an attention worker's work in a layer. A Ready section scores the query tokens against a page written in an earlier pass (the user's earlier chunks). A Pending section scores them against a page written in this pass. The Pending sections wait for the latch that save_k and save_v count down [h/tron/models/self_attention.hpp:777-788]."),
        ("dense page, partial page", "A dense page is a 64-token page of which the query attends to all 64 positions. Three tests decide it (is_dense_amx_page): the whole page is active (all 64 positions hold tokens the pass may read), one visible range (a run of token positions the attention mask lets the query see) covers the page, and the page lies inside the sliding attention window (the model's limit on how far back a query may look). Only dense pages take the AMX kernel. Every other page is partial and takes the AVX-512 reader k_vnni::qk_group (AVX-512 = Advanced Vector Extensions 512, the CPU's 512-bit vector instructions). A page written in a pass is not dense for that pass's queries when it holds more than one query token of the pass: a visible range closes above every query token, and the predicate tests the range that holds the page's first token. In the report's prefill runs every token of a Pending page is a query token of the pass, so no Pending page is dense. A page whose only new token is its last one (a decode step that fills a page) is dense for that query [%s]." % L["dense"]),
        ("kill switch, TRON_AMX_DISABLE", "The run-time environment variable TRON_AMX_DISABLE=1 turns the AMX attention path off in an AMX build. The K layout stays VNNI; every page is then scored with k_vnni::qk_group."),
        ("row-major K, base", "The K plane layout before VNNI K (TRON_K_VNNI off, or a head size other than 128): one contiguous 256-byte K row per token in the plane of each KV head, written with 4 full-line stores per row. base is the traced binary with that layout (commit 544ca05c7a)."),
        ("attention join (span 'attention: join')", "The last part of an attention worker's layer: the workers combine their partial results per KV head and write the attention output. The trace span is named 'attention: join'. It is not the window join of section 6 (main's wait for finished == n_workers - 1). The layer end on this page is the end of the last attention join span."),
        ("fused kernel", "One helper kernel into which the ingest (tron's code generator, the Haskell program in ingest/src that emits the qwen plugin at build time) merged several adjacent per-token steps. The trace name lists the steps: kernel_rmsnorm_rope_rmsnorm_rope_L is the norm and the rope of Q, then of K, for layer L."),
        ("helper count per pass", "The number of main helpers is chosen per pass: with one minibatch it is the fixed split (pool workers x 2) / 7, capped by the item count and by the min/max limits [%s]. The traces show 7 at tp2 in prefill and decode, 15 at tp4 in prefill and 8 at tp4 in decode (the decode pass has 8 items). The attention workers are the rest of the pool: 20 at tp2, 40 (prefill) or 47 (decode) at tp4. n_workers of a window = 1 + the helpers: 8 at tp2, 16 at tp4 in prefill." % L["helpers_rule"]),
        ("TTFT", "Time to first token: for the batched prefill of the 8 prompts, the time from the request to the first generated token, as runtron reports it [report section 1]."),
        ("trace set 1, trace set 2", "set 1: the 2026-09-14 traces of the row-major binary (base) and the first VNNI binary (vnni), exec/results/vnnik-trace-20260914. set 2: the 2026-09-15 traces of commit 9928cb2849 in its four configurations (vnni0, a, b, ab), exec/results/vnnik2-trace-20260915. Each trace holds 8 prefill passes and 8 decode steps of one run."),
        ("envelope lane", "In the lanes figure of section 2.2: one lane that stands for several threads, drawn from the first start to the last end of their spans of one kind. It shows when any of them worked, not how many."),
    ]


def context_sources():
    """Extra rows for the Sources and checks table: (fact, kind, source)."""
    return [
        ("Layer 10 of prefill pass 3 milestones (rope kernel end, Save K, Save V, first Pending start, last attention join end, next helper kernel) for 12 traced configurations", "measured", "exec/results/vnnik-trace-20260914/*.lanes.json (base, vnni) and exec/results/vnnik2-trace-20260915/*.lanes.json (vnni0, a, b, ab; extracted 2026-09-18 with exec/vnnik-trace-20260914/lanes.py TRACE 2 10)"),
        ("Thread roles per window: threads with kernel spans = main helpers (7 at tp2; 15 at tp4 in prefill, 8 in decode), threads with attention spans = attention workers (20; 40 in prefill, 47 in decode)", "measured", "the same lanes.json files (prefill and decode objects); analysis.json threads (whole-trace classification = the decode split)"),
        ("Save K and Save V per layer and per pass, pass length, decode Save K and its step-to-step spread, for every configuration (means over 8 passes)", "measured", "exec/results/vnnik-trace-20260914/analysis.json, exec/results/vnnik2-trace-20260915/analysis.json"),
        ("Single Save K spans over the run: n = 288, standard deviation, min, max (vnni0, a, b, ab at tp2)", "measured", "exec/shared-save-animation/savek_spans.json (savek_spans.py over the set 2 traces, 2026-09-18)"),
        ("The layer end moved by %s us between vnni0 and ab at tp2 while Save K shrank by %s us" % (f0(LAYER_END_SHIFT), f0(SAVE_K_SHIFT)), "measured (one traced layer per configuration)", "lanes.json of vnni0-tp2 and ab-tp2, attention: join last end; this page's context_sections.py"),
        ("TTFT at prompt 1024 per configuration (means and standard deviations over 3 runs at tp2, 2 at tp4)", "measured", "exec/results/vnnik2-20260915/summary.json (cells); report sections 4.1 and 4.2"),
        ("Statement order on main: launch_early_hw_attention, K channel waits, save_k(.., n_workers), V channel waits, save_v, prepare_late_hw_attention, launch_late_hw_attention; save_k_helper at the attention statement of the helpers' list", "code", L["emit_main"] + "; " + L["emit_help"] + "; " + L["emit_run_help"] + "; " + L["early"]),
        ("The latch upstream_kvs_ready is reset to kvs_needed, and kvs_needed grows by 2 per upstream minibatch a minibatch reads from (one count for save_k, one for save_v). The generated plugin has one minibatch, which is its own upstream. The attention workers wait on the latch between the Ready and the Pending sections", "code", L["latch_reset"] + "; " + L["one_minibatch"] + "; " + L["wait"]),
        ("The K buffer element type is bf16 (hardware::btensor = dmatensor<bf16, ...>). So store_k_block reads the rows in place", "code", L["btensor"] + "; " + L["store_k_block"]),
        ("The completion marks are consumed only by the FPGA GOF dispatch and by an assertion. page::copy_from copies them along with a page. The CPU attention's gate is the latch", "code", L["is_kv_complete"] + "; " + L["gof_readers"]),
        ("A page written in a pass is not dense for that pass's queries when it holds more than one query token of the pass (is_dense_amx_page tests the range of the page's first token, and a range closes above each query token). In the prefill runs every Pending page holds 64 query tokens", "code", L["dense"]),
        ("Factors between the configurations (2 x 2 and the reference), from the unrounded per-layer means", "computed", "this page's context_sections.py from analysis.json save_k_us_per_layer"),
        ("The switches TRON_K_VNNI_BLOCK / TRON_K_VNNI_STRIPE existed in commit 9928cb2849 and were removed in commit ec1be6dde4", "git history", "branch jhan-amx-vnniK; report section 3"),
    ]


if __name__ == "__main__":
    html = context_html()
    bad = [(i, c) for i, c in enumerate(html) if ord(c) > 127]
    assert not bad, bad[:5]
    print(len(html), "bytes of HTML; factors", {k: ("%.2f" % v[0], "%.2f" % v[1]) for k, v in FACT.items()})
    print("layer end shift %.1f us, Save K shift %.1f us, pending shift %.1f us; rope ends %.2f .. %.2f (late: %s); ready first %.1f .. %.1f; pending gap %.2f .. %.2f" % (
        LAYER_END_SHIFT, SAVE_K_SHIFT, PENDING_SHIFT, ROPE_LO, ROPE_HI, ROPE_LATE, READY_LO, READY_HI, PEND_GAP_LO, PEND_GAP_HI))
    print({n: (m["n_helpers"], m["n_attn"]) for n, m in M.items()})
