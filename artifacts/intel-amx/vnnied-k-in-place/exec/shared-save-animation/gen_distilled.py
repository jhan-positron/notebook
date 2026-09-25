#!/usr/bin/env python3
"""Generate status/shared-save-animation-distilled.html: the distilled version of
status/shared-save-animation.html (revision 5). Same animation script, same
measured charts (section 2.2 lanes, section 3.2 dumbbell), same data files;
the visible text is limited to 3000 words (asserted below, SVG labels included,
the text the animation script renders excluded). Pure ASCII.
jhan, 2026-09-20: "Generate a distilled version of status/shared-save-animation.html,
limit text at viewable page up to 3000 words."
Revision 2 (2026-09-21): 42 review findings applied (workflow wf_aa7e148a-e78: numbers,
code claims, faithfulness, plain English, completeness, script; three skeptics each).
"""
import datetime
import html as htmlmod
import json
import os
import re
import sys

import context_sections as ctx
import gen_page as full

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "status", "shared-save-animation-distilled.html")
WORD_LIMIT = 3000
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
esc = full.esc
UC = full.UNIT_COST
SIM = full.SIM
L = full.LAYOUT
M = ctx.M
P = ctx.P
R = ctx.MEAS_ROUNDED
F = ctx.FACT


def f0(x):
    return "%.0f" % x


def words_table():
    rows = [
        ("tron, qwen3-4b", "tron: the inference program under test. qwen3-4b: the model, 8 KV (key/value) heads of 128 values, 36 layers."),
        ("pass, item, prefill, decode", "One forward step over the tokens tron holds. An item is one of them. A prefill pass here holds 1024 items (128 prompt tokens of each of 8 users), a decode pass 8."),
        ("tp2, tp4", "The model split over 2 or 4 FPGA (field-programmable gate array) accelerator cards. The K store runs on the CPU: main plus 7 helpers at tp2, main plus 15 in tp4 prefill (8 in decode, capped by the item count)."),
        ("main, main helpers, attention workers", "Main runs the pass, the helpers the per-token kernels (norm = normalisation, rope = the position-dependent rotation of K), the attention workers (20 at tp2, 40 at tp4 prefill, 47 in decode) the CPU attention. One core each."),
        ("Q, K, V, K buffer, entry, K row", "Q, K, V: a token's query, key and value vectors in a layer. The KV cache keeps K and V. K buffer: the roped K of the pass, one 2048-byte entry per item, the item's 8 K rows of 256 bytes (one per KV head)."),
        ("page, block, plane, VNNI layout", "A KV cache page holds 64 tokens in 4 blocks of 16. One KV head's K of one page is one 16 KiB plane in DRAM, stored in the VNNI layout (Vector Neural Network Instructions): one 64-byte line holds one dimension pair of a block's 16 tokens. The AMX (Intel matrix instructions) attention kernel reads it."),
        ("block store, scatter", "2 to 16 tokens transposed in registers and written as 64 lines per KV head, or one token written with 4 scatters of 16 x 4 bytes."),
        ("unit, window, claim", "unit: a run of consecutive items inside one block. window: one shared save. claim: one fetch_add (atomic add-and-return) on next_unit. A value of n_units (64 here) or more is an empty claim."),
        ("opened, finished, latch", "opened: windows main has opened in the pass. finished: helpers that left the open window. latch: the counter that releases the Pending sections after a count from Save K and one from Save V."),
        ("Save K, Save V, Ready, Pending", "Save K and Save V: the trace spans of the K and V stores, once per layer per pass. Ready and Pending: an attention worker's work over earlier passes' pages, and over this pass's pages."),
        ("vnni0, a, b, ab, base", "One binary (commit 9928cb2849): both remedies off, block store only, shared save only, both. base is the row-major K binary before VNNI K. At head both are always on."),
        ("factor, est., mock, model", "factor: span before divided by span after, both measured. est.: derived from a measurement by arithmetic. mock: invented for the animation. model: follows from code and cache rules, not measured."),
    ]
    return '<table><tr><th>Term</th><th>Meaning</th></tr>' + "".join('<tr><td>%s</td><td>%s</td></tr>' % (esc(a), esc(b)) for a, b in rows) + '</table>'


def functions_table():
    rows = [
        ("main", "save_k_impl", "The Save K span: cut, reset, opened++, claim loop, join on finished, marks, GOF credits, first latch count.", "model.hpp:2992-3059"),
        ("helpers", "save_k_helper", "++helper_windows[worker_ix] (its thread number), spin on opened, claim loop, finished++. Same statement position as save_k.", "model.hpp:2953-2989; TronCpp.hs:2325-2340"),
        ("every claimer", "store_k_block", "One unit: 2 to 16 items -> k_vnni::store_block, one item -> k_vnni::scatter_row.", "model.hpp:2855-2946"),
        ("main", "save_v_impl", "The V save, serial, right after Save K. Second latch count.", "model.hpp:3082-3128"),
        ("attention workers", "run_attention_job", "Ready sections from the Save K start, latch wait, Pending sections over the new planes with the AVX-512 (CPU vector instructions) reader (a page holding more than one of this pass's queries is not dense), join.", "self_attention.hpp:777-788, 1375-1391"),
    ]
    return '<table><tr><th>who</th><th>function</th><th>role</th><th>source</th></tr>' + "".join('<tr><td>%s</td><td class="mono">%s</td><td>%s</td><td class="mono">%s</td></tr>' % tuple(esc(x) for x in r) for r in rows) + '</table>'


def scope_table():
    rows = [
        ("prefill, full 16-token block (the traced pass)", "yes", "yes"),
        ("prefill, run of 2 to 15 tokens", "yes, lane-masked", "yes"),
        ("run of one token", "no: scatter", "yes"),
        ("decode pass (8 items)", "no", "no: needs more than 16 items"),
    ]
    return '<table><tr><th>case</th><th>block store</th><th>shared save</th></tr>' + "".join('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % tuple(esc(x) for x in r) for r in rows) + '</table>'


def layout_table():
    rows = [
        ("next_unit (claim counter)", "%d-%d" % (L["next_unit"], L["next_unit"] + 3), "0", "written by every fetch_add (72 at tp2, 80 at tp4). Alone on its line."),
        ("opened", "%d-%d" % (L["opened"], L["opened"] + 3), "1", "written once per window by main. Polled by the waiting helpers."),
        ("finished", "%d-%d" % (L["finished"], L["finished"] + 3), "1", "reset by main, one write per helper. Polled by main in the join."),
        ("n_units, unit_start[0 .. 12]", "%d-127" % L["n_units"], "1", "written by main during the cut, on the polled line."),
        ("unit_start[13 .. 1024]", "128-%d" % (L["unit_start_end"] - 1), "2 .. 65", "read per claimed unit: [u] and [u+1]."),
        ("helper_windows[0 .. 127]", "%d-%d" % (L["helper_windows"], L["helper_windows_end"] - 1), "65 .. 73", "each written only by its own helper."),
    ]
    return '<table><tr><th>field</th><th class="num">bytes</th><th>line</th><th>who writes, who reads</th></tr>' + "".join('<tr><td class="mono">%s</td><td class="num">%s</td><td class="mono">%s</td><td>%s</td></tr>' % tuple(esc(x) for x in r) for r in rows) + '</table>'


def sim_table():
    h = ['<table><tr><th>configuration</th><th class="num">unit cost (us, est.)</th><th class="num">units per thread</th><th class="num">simulated window (us)</th><th class="num">trace mean, sd (us)</th><th class="num">gap (us)</th></tr>']
    for (cfg, tp), r in SIM.items():
        pt = r["per_thread"]
        h.append('<tr><td>%s %s (%d threads)</td><td class="num">%s</td><td class="num">%d</td><td class="num">%.1f</td><td class="num">%.1f, sd %.1f</td><td class="num">%+.1f</td></tr>' % (
            cfg, tp, 1 + full.HELPERS[tp], r["cost"], max(pt.values()), r["length"], r["trace_mean"], r["trace_sd"], r["trace_mean"] - r["length"]))
    h.append('</table>')
    return "".join(h)


def visible_words(page):
    t = re.sub(r'<script.*?</script>', ' ', page, flags=re.S)
    t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = htmlmod.unescape(t)
    return len(t.split())


def build():
    b, a = M[ctx.BEFORE], M[ctx.AFTER]
    cost_js = json.dumps({cfg: {tp: UC[(cfg, tp)] for tp in ("tp2", "tp4")} for cfg in ("ab", "b")})
    js = (full.JS.replace("__MOCK_UNITS__", json.dumps(full.UNITS["mock_pass"]["units"], separators=(",", ":")))
          .replace("__CUT__", str(full.CUT_US)).replace("__ARR__", str(full.ARRIVE_STEP_US)).replace("__MARK__", str(full.MARK_US)).replace("__W__", str(full.W_EXAMPLE))
          .replace("__COST__", cost_js).replace("__MEAS__", json.dumps({"ab": full.MEAS["ab"], "b": full.MEAS["b"]}))
          .replace("__TINT__", json.dumps(full.TINT)).replace("__DARK__", json.dumps(full.DARK))
          .replace("__SIM_LENGTHS__", json.dumps({"%s|%s" % k: round(v["length"], 3) for k, v in SIM.items()})))
    gaps = [v["trace_mean"] - v["length"] for v in SIM.values()]
    sds = [v["trace_sd"] for v in SIM.values()]
    pv = P("vnni0-tp2")
    pa = P("ab-tp2")
    tt = ctx.ttft_ms
    ttft_cut = tuple(100.0 * (tt("vnni0", tp) - tt("ab", tp)) / tt("vnni0", tp) for tp in ("tp2", "tp4"))
    ttft_sdmax = tuple(max(ctx.ttft_sd(x, tp) for x in ("a", "b", "ab")) for tp in ("tp2", "tp4"))
    H = []
    H.append('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">')
    H.append('<title>Shared block save, distilled</title>')
    H.append('<style>' + full.CSS + '</style></head><body><main>')
    H.append('<h1>Shared block save, distilled</h1>')
    H.append('<p class="sub">The short form of <a href="shared-save-animation.html">shared-save-animation.html</a> (revision 5, about 16,600 words): the same animation and charts, under %d words of text, section numbers kept. '
             'Only on the full page: the 64-unit table, the 12-configuration milestones, the TTFT (time to first token) table, the full source table. Code read at commit %s (the PR 4424 head). Generated %s by exec/shared-save-animation/gen_distilled.py. Companion: <a href="block-store-animation.html">block-store-animation.html</a>.</p>' % (WORD_LIMIT, full.HEAD, NOW))
    H.append('<div class="short"><p><b>Short version.</b> In a prefill layer the main thread used to store all 8192 K rows of the pass alone while the 7 (tp2) or 15 (tp4) main helpers were idle. '
             'Now main cuts the pass into 64 units of 16 tokens and opens a window, and main and the helpers claim units from one counter until none is left. '
             'Measured per prefill layer, the shared save alone cuts Save K from %d to %d us at tp2 and from %d to %d us at tp4, and with the block store as well to %d and %d us.</p></div>' % (
                 R["vnni0-tp2"], R["b-tp2"], R["vnni0-tp4"], R["b-tp4"], R["ab-tp2"], R["ab-tp4"]))

    H.append('<h2>1. Words used here</h2>')
    H.append('<div class="scroll">' + words_table() + '</div>')

    H.append('<h2>2. Where the save sits</h2>')
    H.append('<p>Every layer of a prefill pass calls save_k once and opens one window: 36 per pass, 288 per prefill of the 8 prompts. One window stores 8192 K rows, 2 MiB. Before it, the FPGA cards compute the Q, K and V projections and the helpers norm and rope. After it, main runs save_v alone, and the attention workers run Ready sections, wait on the latch, then Pending sections. '
             'Before the remedies the 36 saves took %.1f ms of a %.0f ms pass at tp2 (%.1f%%). With both remedies they take %.1f ms (%.1f%%).</p>' % (
        pv["save_k_ms"], pv["pass_ms"], 100 * pv["save_k_ms"] / pv["pass_ms"], pa["save_k_ms"], 100 * pa["save_k_ms"] / pa["pass_ms"]))
    H.append('<h3>2.2 One layer, before and after (measured)</h3>')
    H.append('<p>Layer 10 of prefill pass 3 (the 11th layer, window W = 11) at tp2, traces of commit 9928cb2849, both remedies off and both on. Time 0 is the start of Save K. Solid: traced. Dashed: not traced.</p>')
    H.append('<div class="fig">' + ctx.stage_svg() + '</div>')
    H.append('<p class="take">The helpers\' rope kernel ends at most %.1f us before Save K starts. Before the change they are then idle until %s us, and the %s us Save K lies inside that idle time. '
             'The Pending sections start %.1f us after Save V ends. The latch needs both saves. '
             'The layer end moved %s us earlier. Save K shrank by %s us. So the whole Save K span was on the critical path. '
             'Single spans, not means: over the 288 spans of a run the standard deviation (sd) is %.0f us (vnni0) and %.0f us (ab).</p>' % (
                 -b["rope_end_min"], f0(b["next_start"]), f0(b["save_k"]), b["pending_first"] - b["save_v_end"], f0(ctx.LAYER_END_SHIFT), f0(ctx.SAVE_K_SHIFT),
                 ctx.SPANS[ctx.BEFORE]["sd"], ctx.SPANS[ctx.AFTER]["sd"]))
    H.append('<h3>2.3 and 2.4 Around the save: statements, data, functions</h3>')
    H.append('<p>The ingest (tron\'s code generator) emits run() for main and run_main_help() for the helpers from one statement list. The helpers rope their stripes of items into the K buffer (item i by helper (i mod 7) + 1 at tp2). Main waits for every item\'s K channel (its roped-K done signal) and calls save_k with n_workers = 1 + the helpers.</p>')
    H.append('<p>One save moves data only: 1024 entries of 2048 bytes in, the same 2 MiB out into the K planes of 16 pages. Nothing is computed. So vnni0, a, b and ab give identical output tokens [report section 5]. Side effects: the completion marks (read only by the FPGA GOF dispatch), the GOF credits (GOF: a group of four tokens packed for the FPGA KV cache), the latch count.</p>')
    H.append('<div class="scroll">' + functions_table() + '</div>')

    H.append('<h2>3. Shared save and block store together</h2>')
    H.append('<p>The block store answers "how is one block written?": 64 scatters per block and KV head became 4 transposes and 64 full-line stores. '
             'The shared save answers "who writes the blocks?": main alone became main and the idle helpers. They meet in store_k_block, called per claimed unit. A full unit is one store_block call per KV head.</p>')
    H.append('<p>Save K per prefill layer, tp2 / tp4, means over 8 prefill passes [report section 4.3]:</p>')
    H.append('<div class="fig">' + ctx.remedies_svg() + '</div>')
    H.append('<p class="take">Alone, the block store cuts the span %.2fx (tp2) and %.2fx (tp4), the shared save %.2fx and %.2fx. Together %.1fx and %.1fx, less than the product. Once the save is shared, the block store adds only %.2fx and %.2fx. '
             'Both together cut TTFT by %.1f%% at tp2 (%.0f to %.0f ms) and %.1f%% at tp4 (%.0f to %.0f ms). The shared save on top of the block store saves a further %.0f ms at tp2 and %.0f ms at tp4, over twice the largest run-to-run sd (%.0f and %.0f ms). The block store on top of the shared save saves %.0f and %.0f ms, within it [full page 3.2].</p>' % (
                 F["block_alone"] + F["shared_alone"] + F["both"] + F["block_when_shared"] + (
                     ttft_cut[0], tt("vnni0", "tp2"), tt("ab", "tp2"), ttft_cut[1], tt("vnni0", "tp4"), tt("ab", "tp4"),
                     tt("a", "tp2") - tt("ab", "tp2"), tt("a", "tp4") - tt("ab", "tp4"), ttft_sdmax[0], ttft_sdmax[1],
                     tt("b", "tp2") - tt("ab", "tp2"), tt("b", "tp4") - tt("ab", "tp4"))))
    H.append('<div class="scroll">' + scope_table() + '</div>')
    H.append('<p class="take">In decode neither remedy acts. In prefill with both, Save V (%.0f us per layer at tp2, serial on main) is now longer than Save K (%.0f us).</p>' % (pa["save_v_us_per_layer"], pa["save_k_us_per_layer"]))

    H.append('<h2>4. The work units</h2>')
    H.append('<p>Prefill pass 3 holds each user\'s third 128-token chunk, positions 256 to 383: pages 4 and 5 of that user, all four blocks. With the users\' items in order, the cut gives 64 units of 16 items, unit_start[u] = 16u, each filling one block.</p>'
             '<p>The 16 entries of a unit were roped by all 7 helper cores at tp2. So a claiming helper reads 13 or 14 of them from other cores\' caches, and main all 16 (model).</p>'
             '<p>The unit test\'s irregular pass (48 items, 9 units, unit_start = [0, 3, 4, 11, 16, 32, 40, 41, 47, 48]) is reproduced by cut_units.py: an item without KV work is its own unit and is skipped, a page or block change ends a unit, a lone token takes the scatter path [t/t_llama_unit.cpp:2572-2810].</p>')

    H.append('<h2>5. The window in memory</h2>')
    H.append('<p>batch::k_store_window is one struct per minibatch (the batch of a pass\'s items), %d bytes = %d cache lines (window_layout.cpp replica). The claim counter has a line of its own. '
             'The helpers spin on opened (line 1) from their own cache copies. Main\'s cut writes and its opened++ invalidate those copies up to 16 times per window. The 72 or 80 fetch_adds would repeat that if next_unit shared the line (model) [common.hpp k_store_window_t].</p>' % (L["sizeof"], L["lines"]))
    H.append('<div class="scroll">' + layout_table() + '</div>')

    H.append('<h2>6. The animation</h2>')
    H.append('<p>One window of 64 units. One event per step: arrival, cut, open, claim, unit completion, empty claim, join, marks, release. The claim order is mock. The real order depends on which thread is free first. Keys: arrows step, space plays.</p>')
    H.append('<div class="controls"><label>Unit cost <select id="cfg"><option value="ab">block store units (ab: %s / %s us, tp2 / tp4)</option><option value="b">scatter units (b: %s / %s us)</option></select></label>'
             '<label>Threads <select id="tp"><option value="tp2">tp2: main + 7 helpers</option><option value="tp4">tp4: main + 15 helpers (prefill)</option></select></label>'
             '<button id="btn-play">Play</button><button id="btn-back">Step back</button><button id="btn-fwd">Step</button><button id="btn-phase">Next phase</button><button id="btn-end">To the end</button><button id="btn-reset">Reset</button>'
             '<label>Speed <select id="speed"><option value="1">1 event/s</option><option value="4" selected>4 events/s</option><option value="10">10 events/s</option><option value="25">25 events/s</option></select></label></div>' % (UC[("ab", "tp2")], UC[("ab", "tp4")], UC[("b", "tp2")], UC[("b", "tp4")]))
    H.append('<div class="status" id="status">The animation needs JavaScript. Sections 5 and 6.6 carry the facts as tables.</div>')
    H.append('<div class="counters" id="counters"></div>')
    legend = "".join('<span><span class="sw" style="background:%s"></span>%s</span>' % (full.DARK[i], "main" if i == 0 else "h%d" % i) for i in range(1 + full.HELPERS["tp4"])) + '<span>(h8 .. h15 at tp4 only)</span>'
    H.append('<div class="legend">' + legend +
             '<span><span class="sw" style="border-style:dashed"></span>waiting (spin)</span><span><span class="sw" style="border:2px dashed #0b0b0b"></span>critical path (the last unit to finish)</span><span><span class="sw" style="box-shadow:0 0 0 2px #2a78d6"></span>touched by the current event</span></div>')
    H.append('<h4>6.1 Who does what when (wall-clock lanes, to scale)</h4><p class="stagehint">Solid blocks: units being stored. Dashed outlines: spin-waits (red for main). Black dashed frame: the last unit to finish. Main\'s lane: the cut (grey) first, the marks (red) last. Ticks: arrivals. Blue line: the current event. Grey dashed line: the measured Save K span.</p><div class="fig" id="stage-lanes"></div>')
    H.append('<h4>6.2 The counters and the threads</h4><div id="stage-counters"></div>')
    H.append('<h4>6.3 The 64 units: who claimed which, in which order</h4><p class="stagehint">Users 1-4 above, 5-8 below: unit number, claim number (#), owner. Hover for details.</p><div id="stage-units"></div>')
    H.append('<h4>6.4 The cache lines of the window (model)</h4>'
             '<p class="stagehint">A written line moves to the writing core, and other copies are invalidated. A spinning core re-reads its own copy without traffic until then. Each change of claiming thread moves the next_unit line once. The animation counts these transfers (cost not measured).</p>'
             '<div id="stage-lines"></div>')
    H.append('<h4>6.5 The data of the claimed unit (model)</h4>'
             '<p class="stagehint">At every claim: the 16 source entries, by the helper that roped them, and the 64 destination lines in each of the unit\'s 8 planes.</p><div id="stage-data"></div>')
    H.append('<h3>6.6 Simulation against measurement</h3>')
    H.append('<p>The unit cost is the serial Save K (a or vnni0, section 3) divided by 64 (%s / %s us for block-store units, %s / %s us for scatter units, tp2 / tp4), an upper bound (est.). The serial span also holds the marks loop and the latch. Arrivals (%s us per helper), the cut (%s us), the marks (%s us) and claims (0 us) are mock.</p>' % (
        UC[("ab", "tp2")], UC[("ab", "tp4")], UC[("b", "tp2")], UC[("b", "tp4")], full.ARRIVE_STEP_US, full.CUT_US, full.MARK_US))
    H.append('<div class="scroll">' + sim_table() + '</div>')
    H.append('<p class="take">In all four cases the trace mean exceeds the simulation by %.1f to %.1f us, more than twice the pass-to-pass sd (%.1f to %.1f us). '
             'The spans were measured on commit 9928cb2849 (16-item blocks, two join counters). The animated head protocol (page-block units, one join counter) gives the same 64 units here, with no measured span. '
             'The report names the join and the helpers\' arrival as the cause, with the block loop as a third candidate. At tp4 the shared save alone measures %.2fx against an ideal of 16x (the report\'s 9x counts the decode split\'s 8 helpers). '
             '<b>Insufficient data</b>: save_k_helper has no trace span. A TRACE_EVENT per claimed unit would give the unit cost, the arrival times and the join wait.</p>' % (min(gaps), max(gaps), min(sds), max(sds), F["shared_alone"][1]))
    H.append('<p class="mono" id="selfcheck">Self-check: JavaScript did not run.</p>')

    H.append('<h2>7. Rules of the window</h2>')
    H.append('<ul><li><b>Who shares:</b> only the generated plugins pass n_workers > 1. Sharing also needs the VNNI K layout, more than 16 items, and n_workers up to 128 [model.hpp k_store_shared].</li>'
             '<li><b>Why the counts agree:</b> save_k_helper sits at the same statement position as save_k. So the W-th window main opens is the W-th every helper enters. Both sides decide with the same k_store_shared.</li>'
             '<li><b>Why main cannot deadlock:</b> every helper finished its rope stripe (main waited for every K channel). Nothing blocks a helper between its rope kernel and save_k_helper. The join\'s watchdog aborts tron after about 120 s [model.hpp:3024-3037].</li>'
             '<li><b>Two units in one block:</b> two threads may write the same lines with masked stores on disjoint lanes. No byte is written twice.</li>'
             '<li><b>Why K and not V:</b> in the V plane two tokens share one 4-byte lane. save_v stays on main.</li>'
             '<li><b>Tests:</b> one thread: opened stays 0. Three threads: every K row written exactly once, and the 9 units [t/t_llama_unit.cpp:2765-2810].</li></ul>')

    H.append('<h2>8. Sources</h2>')
    H.append('<ul><li>Code (commit %s): model.hpp save_k_impl :2992-3059, save_k_helper :2948-2989, k_store_cut_units :2816-2845, store_k_block :2855-2946, k_store_shared :2806-2814; common.hpp k_store_window_t :1042-1068; ingest/src/TronCpp.hs saveKv :2400-2408.</li>'
             '<li>Measured: store-remedies-report.html section 4.3; exec/results/vnnik2-trace-20260915 (analysis.json, lanes.json), exec/results/vnnik-trace-20260914; exec/results/vnnik2-20260915/summary.json (TTFT).</li>'
             '<li>Run: window_layout.cpp (struct offsets), cut_units.py (unit cut), savek_spans.json (288 single spans).</li>'
             '</ul>' % full.HEAD)
    H.append('</main><script>' + js + '</script></body></html>')
    page = "\n".join(H)
    bad = [(i, c) for i, c in enumerate(page) if ord(c) > 127]
    assert not bad, "non-ASCII at %r" % bad[:5]
    n = visible_words(page)
    assert n <= WORD_LIMIT, "visible words %d > %d" % (n, WORD_LIMIT)
    with open(OUT, "w") as f:
        f.write(page)
    print("wrote %s (%d bytes, %d visible words incl. SVG labels)" % (OUT, len(page), n))


if __name__ == "__main__":
    build()
