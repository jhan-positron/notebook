#!/usr/bin/env python3
"""Generate status/shared-save-animation.html: the shared block save (the K store
window that the main thread and the idle main helpers work through together,
report section 3.2 (b)) played claim by claim, with the unit list, the counter
values, the cache lines of the window, the data each claimed unit moves, and a
wall-clock lanes chart. Ground truth: layout.json (window_layout.cpp, the struct
replica compiled with g++) and units.json (cut_units.py, checked against
t_llama_unit.cpp). Pure ASCII.
Revision 2 (2026-09-17): 61 round-1 review findings applied. Revision 3: 28 round-2
findings applied. Revision 4: 19 round-3 findings applied (REV below). Revision 5
(2026-09-18): sections 2 and 3 (context_sections.py: the stage of prefill, the data and
the functions of one save, the relation to the block store) inserted; the former
sections 2-6 became 4-8. Revision 5 also corrects the tp4 thread split: a prefill window has
15 main helpers (16 claimers), not 8; the 8 of revisions 1-4 is the decode split (context_sections.py).
"""
import datetime
import json
import os
import sys

import context_sections as ctx

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "status", "shared-save-animation.html")
HEAD = "30c4ac82cb"
REV = 5
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
LAYOUT = json.load(open(os.path.join(HERE, "layout.json")))
UNITS = json.load(open(os.path.join(HERE, "units.json")))
assert LAYOUT["next_unit"] == 0 and LAYOUT["opened"] == 64 and LAYOUT["finished"] == 68 and LAYOUT["n_units"] == 72 and LAYOUT["unit_start"] == 76
assert len(UNITS["mock_pass"]["units"]) == 64 and len(UNITS["test_pass"]["units"]) == 9

# measured Save K spans per prefill layer, us (report section 4.3, prompt 1024, 8 users, qwen3-4b, commit 9928cb2849)
MEAS = {"vnni0": {"tp2": 858, "tp4": 863}, "a": {"tp2": 346, "tp4": 353}, "b": {"tp2": 175, "tp4": 110}, "ab": {"tp2": 80, "tp4": 60}}
HELPERS = {"tp2": 7, "tp4": 15}  # main helpers of a PREFILL window, counted from the trace spans (context_sections.py); a decode pass has 8 at tp4
N_UNITS = 64
# simulation parameters (mock, see section 6.6 of the page)
CUT_US = 1.0          # main cuts the units: mock duration
ARRIVE_STEP_US = 0.1  # helper h arrives 0.1 h us after main entered save_k (mock; all before the open)
MARK_US = 2.0         # marks + credits + latch: mock duration
W_EXAMPLE = 11        # the example window number (the 11th save_k of the pass)
SERIAL_OF = {"ab": "a", "b": "vnni0"}  # the serial configuration whose span gives the unit cost
UNIT_COST = {(cfg, tp): round(MEAS[SERIAL_OF[cfg]][tp] / N_UNITS, 1) for cfg in ("ab", "b") for tp in ("tp2", "tp4")}
assert UNIT_COST == {("ab", "tp2"): 5.4, ("ab", "tp4"): 5.5, ("b", "tp2"): 13.4, ("b", "tp4"): 13.5}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def simulate(n_helpers, cost):
    """The same event model as the page's JavaScript (kept identical by hand):
    returns (window_length_us, units_per_thread, t_join)."""
    H = n_helpers
    free = {0: CUT_US}
    for h in range(1, H + 1):
        free[h] = max(ARRIVE_STEP_US * h, CUT_US)
    next_unit = 0
    left = set()
    per_thread = {x: 0 for x in range(H + 1)}
    last_finished = 0.0
    main_wait_from = 0.0
    while len(left) < H + 1:
        x = min((t for t in range(H + 1) if t not in left), key=lambda t: (free[t], t))
        t = free[x]
        u = next_unit
        next_unit += 1
        if u < N_UNITS:
            per_thread[x] += 1
            free[x] = t + cost
        else:
            left.add(x)
            if x == 0:
                main_wait_from = t
            else:
                last_finished = max(last_finished, t)
    t_join = max(last_finished, main_wait_from)
    return t_join + MARK_US, per_thread, t_join


# trace statistics behind the report's rounded spans: mean and pass-to-pass standard deviation over the
# 8 prefill passes of each traced run (exec/results/vnnik2-trace-20260915/analysis.json, kinds.prefill)
TRACE_JSON = "/home/jhan/workspace/intel-AMX/exec/results/vnnik2-trace-20260915/analysis.json"
TRACE = {}
for _e in json.load(open(TRACE_JSON)):
    _name = _e["trace"].replace(".perfetto-trace", "")
    _cfg, _tp = _name.split("-")
    TRACE[(_cfg, _tp)] = (_e["kinds"]["prefill"]["save_k_us_per_layer"], _e["kinds"]["prefill"]["save_k_us_per_layer_sd"])
for _k, _v in MEAS.items():
    for _tp in ("tp2", "tp4"):
        assert round(TRACE[(_k, _tp)][0]) == _v[_tp], (_k, _tp, TRACE[(_k, _tp)], _v[_tp])

SIM = {}
for cfg in ("ab", "b"):
    for tp in ("tp2", "tp4"):
        length, per_thread, t_join = simulate(HELPERS[tp], UNIT_COST[(cfg, tp)])
        SIM[(cfg, tp)] = {"length": length, "per_thread": per_thread, "t_join": t_join, "measured": MEAS[cfg][tp], "trace_mean": TRACE[(cfg, tp)][0], "trace_sd": TRACE[(cfg, tp)][1], "serial": MEAS[SERIAL_OF[cfg]][tp], "cost": UNIT_COST[(cfg, tp)]}

TINT = ["#f3c4c4", "#cce3f0", "#ccece3", "#faeccc", "#e3d5f5", "#f5e4ed", "#d0ecec", "#e6e5e1", "#f0d9c0", "#dbe4ff", "#d3f9d8", "#ffdeeb", "#ffe8cc", "#c5f6fa", "#f3d9fa", "#e5dbff"]
DARK = ["#d03b3b", "#0072b2", "#007a59", "#b87a00", "#7a3fbf", "#a05080", "#0ca3a3", "#6b6a67", "#b8651a", "#3b5bdb", "#2b8a3e", "#c2255c", "#e8590c", "#0b7285", "#862e9c", "#5f3dc4"]
assert len(TINT) == len(DARK) == 1 + max(HELPERS.values())


def legend_swatches():
    return "".join('<span><span class="sw" style="background:%s"></span>%s</span>' % (DARK[i], "main" if i == 0 else "helper %d%s" % (i, " (tp4 only)" if i > HELPERS["tp2"] else "")) for i in range(1 + max(HELPERS.values())))

CSS = """
:root { --ink:#0b0b0b; --muted:#52514e; --line:#e6e5e1; --bg:#fcfcfb; --panel:#f3f2ef; --accent:#2a78d6; --warn:#d03b3b; }
html { color-scheme: light; }
* { box-sizing: border-box; }
body { margin:0; padding-block:24px 48px; padding-inline:16px; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:1000px; margin:0 auto; }
h1 { font-size:26px; margin:0 0 6px; text-wrap:balance; } h2 { font-size:20px; margin:30px 0 8px; border-bottom:1px solid var(--line); padding-bottom:4px; } h3 { font-size:16px; margin:18px 0 6px; } h4 { font-size:14px; margin:14px 0 4px; color:var(--muted); }
p { max-width:72ch; }
.sub { color:var(--muted); margin-bottom:16px; }
.short { background:var(--panel); border-left:4px solid var(--accent); padding:10px 14px; margin:14px 0; } .short p { max-width:none; }
table { border-collapse:collapse; margin:10px 0 14px; font-size:14px; } th, td { border:1px solid var(--line); padding:5px 8px; vertical-align:top; text-align:left; } th { background:var(--panel); }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; }
code, pre, .mono { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; }
.fig { margin:6px 0 4px; border:1px solid var(--line); background:#fff; padding:8px; overflow-x:auto; }
.take { font-size:14px; color:var(--muted); margin:2px 0 12px; max-width:none; }
.answer { border:1px solid var(--line); border-left:4px solid #0072b2; background:#fff; padding:8px 12px; margin:10px 0; } .answer p { max-width:none; }
ul { margin:6px 0 10px 22px; } li { margin:3px 0; }
details { margin:8px 0; } summary { cursor:pointer; color:var(--accent); }
.scroll { overflow-x:auto; }
.controls { display:flex; flex-wrap:wrap; gap:8px 12px; align-items:center; position:sticky; top:env(safe-area-inset-top, 0px); background:var(--bg); padding:8px 0; border-bottom:1px solid var(--line); z-index:5; }
.controls button { font:14px system-ui,sans-serif; padding:5px 10px; border:1px solid #b8b6b0; background:#fff; border-radius:4px; cursor:pointer; }
.controls button:hover { background:var(--panel); } .controls button:focus-visible { outline:2px solid var(--accent); outline-offset:1px; }
.controls label { font-size:14px; } .controls select { font:14px system-ui,sans-serif; }
.status { background:var(--panel); border:1px solid var(--line); padding:8px 12px; margin:10px 0; min-height:48px; font-size:14px; }
.counters { display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; color:var(--muted); margin:4px 0 10px; } .counters span b { color:var(--ink); font-variant-numeric:tabular-nums; }
.stage { margin:16px 0; } .stage h3 { margin-bottom:4px; }
.stagehint { font-size:13px; color:var(--muted); margin:0 0 6px; max-width:none; } ul.stagehint { margin:0 0 8px 22px; } ul.stagehint li { margin:2px 0; }
.legend { display:flex; flex-wrap:wrap; gap:10px 16px; font-size:12.5px; color:var(--muted); margin:8px 0; }
.legend .sw { display:inline-block; width:14px; height:12px; border:1px solid var(--line); vertical-align:-2px; margin-right:4px; background:#fff; }
/* unit strip: two rows of 32 units */
.ustrip { display:grid; grid-template-columns:repeat(32, 1fr); gap:1px; min-width:900px; }
.ucell { border:1px solid var(--line); min-height:38px; font-size:9px; line-height:1.2; text-align:center; padding:2px 0; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; background:#fff; color:var(--muted); overflow:hidden; }
.ucell.cur { box-shadow:0 0 0 2px var(--accent); }
.ulbl { display:grid; grid-template-columns:repeat(4, 1fr); min-width:900px; font-size:11px; color:var(--muted); text-align:center; margin:2px 0 6px; }
/* counters table and threads */
.grid { border-collapse:collapse; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; line-height:1.25; }
.grid th, .grid td { border:1px solid var(--line); padding:2px 6px; text-align:left; white-space:nowrap; }
.grid th { background:var(--panel); font-weight:600; }
.grid td.num { text-align:right; }
.grid tr.currow td { box-shadow:inset 0 0 0 2px var(--accent); }
/* cache lines of the window */
.wlines { display:grid; grid-template-columns:130px 1fr; gap:6px; align-items:stretch; min-width:700px; }
.wl { border:1px solid var(--line); border-radius:2px; padding:4px 8px; font-size:11.5px; line-height:1.3; background:#fff; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
.wl .own { font-weight:700; }
.wl.cur { box-shadow:0 0 0 2px var(--accent); }
.wlbl { font-size:11px; color:var(--muted); align-self:center; }
/* data of the claimed unit */
.data { display:grid; grid-template-columns:150px 1fr; gap:6px; min-width:700px; }
.dl { font-size:11px; color:var(--muted); align-self:center; }
.db { border:1px solid var(--line); border-radius:2px; padding:4px 8px; font-size:11.5px; line-height:1.3; background:#fff; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
.heads { display:grid; grid-template-columns:repeat(8, 1fr); gap:3px; margin-top:4px; }
.hd { border:1px solid var(--line); border-radius:2px; padding:3px 4px; font-size:10px; line-height:1.25; text-align:center; background:#fff; }
svg.lanes { display:block; max-width:100%; height:auto; }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
"""


def words_table():
    rows = [
        ("tron, runtron", "tron is the inference program under test. runtron is its command-line tool."),
        ("qwen3-4b", "The model under test: Qwen/Qwen3-4B-Instruct-2507, with 8 KV heads, head size 128, 32 query heads and 36 layers (its Hugging Face config file)."),
        ("KV head", "A token has 8 key/value vector sets per layer in qwen3-4b. Each set is one KV head. The store writes every KV head of a token."),
        ("pass, token item, prefill, decode, chunk", "A pass is one forward step of tron over the tokens it holds at that moment, layer by layer. A token item (item) is one token of the pass. Prefill is the passes over the prompt tokens. In the report's runs each user's prompt is 1024 tokens, and the scheduler processes it in 8 prefill passes of 128 tokens per user (a chunk). One prefill pass therefore holds 128 tokens of each of the 8 users, 1024 items. Decode is a pass that adds one generated token per user (8 items)."),
        ("minibatch, downstream minibatch", "The scheduler's unit of work: one struct batch holding the items of a pass (a pass may be split into several minibatches). The window is a field of the minibatch. A downstream minibatch is one whose attention reads the K and V this minibatch stores."),
        ("tp2, tp4", "The model split over two or four FPGA cards (FPGA = field-programmable gate array, the accelerator card tron runs the model on). tp stands for tensor parallelism, the split of one model over several cards. The K store runs on the CPU: main plus 7 main helpers at tp2 in every pass. At tp4 it is main plus 15 in a prefill pass and main plus 8 in a decode pass. All three counts come from the trace spans (section 2.2). The report's section 1 quotes the decode split."),
        ("main thread, main helpers, attention workers, worker, worker_ix, n_workers", "The generated qwen plugin runs the forward pass on one main thread. The main helpers of the pass run the per-token kernels (norms, the normalisation layers, and rope) beside it. Their number is chosen per pass (see the row helper count per pass). The other threads of the pool are the attention workers (20 at tp2; at tp4 40 in a prefill pass and 47 in a decode pass). They run the CPU attention and take no part in the store. A worker on this page is main or a main helper. worker_ix is its number: 0 for main, 1 .. n_workers - 1 for the helpers. n_workers = 1 + the number of main helpers. Every pool thread pins itself to one core of the application CPU set. So each worker runs on its own core [h/tron/threading.hpp:819-822, 859-862]."),
        ("stripe (round-robin)", "How the helpers share a per-token kernel: helper worker_ix handles the items worker_ix - 1, worker_ix - 1 + (n_workers - 1), ... of the pass. Consecutive items therefore go to consecutive helpers, and main takes none [ingest/src/TronCpp.hs staticStrategy, Note [Main Thread Skips Helper Kernels]]."),
        ("rope", "Rotary position embedding: the position-dependent rotation applied to each K row (and Q row) before the store. The main helpers run it, each on its own stripe of the items. So the K buffer entries of one 16-item unit were written by 7 (tp2) or 15 (tp4) different cores just before the store reads them."),
        ("K channel", "The per-item completion signal of the K rows. Main waits for every item's K channel before it calls save_k. So every helper has finished its rope stripe when the window opens."),
        ("Save K", "The Perfetto trace span (Perfetto is the trace recorder built into tron) of save_k_impl, the function that stores the K rows of a pass into the KV cache, once per layer per pass. Its length is the number this page compares against."),
        ("KV cache, page, block, plane", "The KV cache keeps the K and V vectors of past tokens, per layer, in DRAM. A page holds 64 token positions in 4 blocks of 16 (c0 .. c3). The K storage of one KV head for one page is one plane of 16 KiB. The companion page block-store-animation.html shows how one block of one plane is written."),
        ("K buffer (ks)", "The pass's K vectors after rope: one 2048-byte entry per token item, holding the token's 8 K rows (8 KV heads x 128 bf16 = 8 x 256 bytes for qwen3-4b). The store reads from it. A K row is one token's vector for one KV head, 256 bytes (see also the row K row, K buffer entry)."),
        ("dim step, lane, masked store", "A dim is one of the 128 positions of a K vector. A dim step is 32 consecutive dims = 64 bytes of a K row (a row has 4). A 64-byte line of the K plane holds 16 lanes of 4 bytes, one per token of a block. A masked store writes only the lanes whose mask bit is set and leaves the other bytes unchanged (companion page)."),
        ("panel", "The storage of one dim step of one 16-token block in a plane: 16 lines x 16 lanes x 4 bytes = 1 KiB. Panel (s, c) is dim step s of block c and starts at plane byte (4s + c) x 1024. So a block has 4 panels (s0 .. s3), one per dim step, 4 KiB apart (companion page)."),
        ("work unit, unit", "A run of consecutive items of the pass that have KV work and fall into one 16-token block of one page. Items without KV work form their own units. A unit ends where the page, the block or the KV flag changes. Unit u is items[unit_start[u], unit_start[u+1]) [model.hpp k_store_cut_units]."),
        ("run", "Inside a unit, the items store_k_block writes with one block store: consecutive items with KV work in one block, each in a different column, at most 16. A second run starts only where a column repeats. A run of one item takes the scatter path."),
        ("block store, scatter", "The two ways a run is written (companion page): a run of 2 to 16 items of one block is transposed in registers and written as 64 full 64-byte lines per KV head (block store). A run of one item is written with 4 scatters of 16 x 4 bytes per KV head. In the report's configuration b the block store was switched off. Every item was then written with scatters. Either way a unit of 16 items touches 64 lines per KV head, 512 lines (32 KiB) for 8 KV heads."),
        ("window, W", "One shared save: main opens it, every worker claims units from it, main closes it after the join. Windows are counted per pass on both sides: the W-th window main opens is the W-th window a helper enters. There is one window per layer. So W runs 1 .. 36 in a qwen3-4b pass. This page plays W = %d as its example. The traced layer of sections 2.2 and 4.1 is layer 10 in the traces' count, which starts at 0: it is the 11th layer of the pass, so it is window W = 11 there too." % W_EXAMPLE),
        ("claim, empty claim, fetch_add, atomic counter", "A claim is one fetch_add on next_unit: the instruction adds 1 to the counter and returns the old value, atomically (no two threads can get the same value). A returned value below n_units is the unit the thread now owns. A returned value of n_units or more is an empty claim: the window has no unit left, and the thread leaves. Every thread ends with exactly one empty claim. So a window has 64 unit claims plus one empty claim per thread: 72 fetch_adds at tp2 (8 threads), 80 at tp4 (16 threads in a prefill pass)."),
        ("opened, finished, next_unit, n_units, unit_start[], helper_windows[]", "The fields of batch::k_store_window. opened counts the windows main has opened in this pass. finished counts the helpers that have left the open window. next_unit is the claim counter. n_units and unit_start[] describe the units. helper_windows[worker_ix] counts the windows helper worker_ix has entered [common.hpp k_store_window_t]."),
        ("release, acquire", "Memory-order labels on the atomic operations. A release store publishes every earlier write of its thread. An acquire load that reads that value sees them. So a helper that sees opened >= W also sees the unit table main wrote before opening, and main that sees finished == n_workers - 1 (the number of helpers) sees every row the helpers stored."),
        ("spin-wait, _mm_pause", "A loop that re-reads a counter until it has the wanted value, with a pause instruction in each turn to slow the loop down. Helpers spin on opened. Main spins on finished."),
        ("join", "The moment main has seen finished == n_workers - 1: every helper has left the window and every unit is stored. Main's spin on finished is the join wait. When the helpers left before main's own empty claim, the spin ends at its first read."),
        ("marks, GOF credit, hardware attention slot, latch", "After the join, main marks every stored token's K as complete (mark_k_complete). When the layer has a hardware attention slot (the KV geometry is the hardware geometry and the layer's attention operation is an FPGA attention candidate, has_hardware_slot in save_k_impl), main also credits the GOF dispatch counter. A GOF (group of four) is 4 tokens of K and V data packed as one 8 KB K block plus one 8 KB V block for the FPGA KV cache [h/tron/gof.hpp:3-7]. credit_gof_save adds one save credit for the token to every GOF that holds it. Then main counts the latch (a countdown counter, upstream_kvs_ready, on which the downstream minibatches' attention workers wait) down once. The latch needs two counts per upstream minibatch. The attention workers' Pending sections (their work over the pages written in this pass) start after save_v has given the second count (section 2.2)."),
        ("watchdog", "Main reads the clock once every 2^20 spins of the join loop. It aborts tron when 120 s (K_JOIN_TIMEOUT_S_120) have passed since its first clock read, with the counter values in the message [model.hpp:2795-2801, 3024-3037]."),
        ("VNNI layout, TRON_K_VNNI, layout_on", "VNNI (Vector Neural Network Instructions) is the name of the CPU instructions that read this K layout. In the VNNI layout the two values of a dimension pair of one token sit next to each other (4 bytes), and one 64-byte line holds that pair for the 16 tokens of a block. It is the right-operand layout of the AMX tile multiply (AMX = Advanced Matrix Extensions, the Intel CPU instructions that multiply small matrices held in tile registers) [h/tron/kernels/k_vnni.hpp:14-21]. TRON_K_VNNI is the build option that stores K this way for 128-dimension heads. layout_on is the compile-time flag derived from it (in h/tron/kernels/k_vnni.hpp). The shared save exists only when it is on."),
        ("configuration vnni0, a, b, ab", "The report's four settings of one binary (commit 9928cb2849): both remedies off (vnni0), block store only (a), shared save only (b), both (ab). At head %s both are always on. The switches no longer exist." % HEAD),
        ("L1D, L2, L3, DRAM, cache line, cold, dirty, evicted", "The core's first-level data cache (48 KiB), its second-level cache (2 MiB), the socket's shared third-level cache (432 MiB) and main memory, all with 64-byte lines. These are the sizes of delphi-3bda, the Intel Xeon 6 6962P test server on which the report's runs were traced (getconf on delphi-3bda, 2026-09-17). A line is held in one core's cache in a writable state, or in several cores' caches read-only. A write by another core moves it (a line transfer) and invalidates the other copies. A cold line is in no cache. The first access then fetches it from DRAM. A dirty line is one a core has modified in its cache and not yet written back to DRAM. A line is evicted when the cache needs its place for another line. A dirty line is then written back to the next level."),
        ("critical path", "The chain of steps whose lengths add up to the window's length: the last thread to finish its units, then main's join, marks and release. The lanes chart frames the first step of that chain, the last unit to finish, with a black dashed border. Main's join wait (red dashed) and the marks block (solid red) follow it on main's lane."),
        ("mock, est., model, hypothesis", "mock = a made-up value chosen so that the animation can be traced (arrival times, the cut and marks durations, the claim order). est. = a value derived from a measurement by arithmetic, not measured itself (the unit cost). model = a statement about cache behaviour that follows from the code and the cache rules, not from a measurement. hypothesis = an explanation a source gives without a measurement."),
    ] + ctx.context_words()
    return "<table><tr><th>Term</th><th>Meaning</th></tr>" + "".join("<tr><td>%s</td><td>%s</td></tr>" % (esc(t), esc(m)) for t, m in rows) + "</table>"


def own_rows(a, b, H, x):
    """How many items of [a, b) helper x roped under the round-robin stripe (main: 0)."""
    if x == 0:
        return 0
    return sum(1 for i in range(a, b) if (i % H) + 1 == x)


def units_table():
    us = UNITS["mock_pass"]["units"]
    h = ['<table><tr><th class="num">unit u</th><th class="num">unit_start[u]</th><th>items</th><th>user</th><th>token positions in the prompt</th><th class="num">page of that user</th><th>block</th><th>rows roped by (tp2, item i by helper (i mod 7) + 1, mod = the remainder of the division)</th><th class="num">bytes written (8 KV heads)</th></tr>']
    for x in us:
        a, b = x["items"]
        h.append('<tr><td class="num">%d</td><td class="num">%d</td><td class="mono">%d .. %d</td><td>user %d</td><td class="mono">%d .. %d</td><td class="num">%d</td><td>c%d</td><td>helpers %s, ... : %s</td><td class="num">%d</td></tr>' % (
            x["u"], a, a, b - 1, x["user"], x["positions"][0], x["positions"][1], x["page"], x["block"],
            ", ".join(str((i % 7) + 1) for i in range(a, a + 7)),
            ", ".join("h%d: %d" % (hh, own_rows(a, b, 7, hh)) for hh in range(1, 8)), 8 * 4096))
    h.append('</table>')
    return "".join(h)


def test_units_table():
    tu = UNITS["test_pass"]["units"]
    h = ['<table><tr><th class="num">unit u</th><th class="num">unit_start[u]</th><th>items</th><th>token position (index into the test\'s KV cache of 3 pages x 64 tokens)</th><th>KV work</th><th>page</th><th>block</th><th>what store_k_block does with it</th></tr>']
    for x in tu:
        a, b = x["items"]
        what = "skipped (no KV work)" if not x["kv"] else ", ".join("%d item%s: %s" % (r["n"], "" if r["n"] == 1 else "s", r["path"]) for r in x["runs"])
        h.append('<tr><td class="num">%d</td><td class="num">%d</td><td class="mono">%d .. %d</td><td class="mono">%d .. %d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            x["u"], a, a, b - 1, x["tokens"][0], x["tokens"][1], "yes" if x["kv"] else "no",
            "-" if x["page"] is None else str(x["page"]), "-" if x["block"] is None else "c%d" % x["block"], what))
    h.append('<tr><td class="num">9</td><td class="num">48</td><td colspan="6">end marker: unit_start[n_units] = number of items</td></tr></table>')
    return "".join(h)


def layout_table():
    L = LAYOUT
    rows = [
        ("next_unit (atomic uint32, the claim counter)", L["next_unit"], L["next_unit"] + 3, "0", "reset to 0 by main before the window opens (store, relaxed). Then written by every fetch_add: 64 unit claims plus one empty claim per thread. Alone on its line by alignas(cache_line_size). So the claims never disturb the line the waiting threads poll"),
        ("padding", 4, 63, "0", "unused"),
        ("opened (atomic uint32)", L["opened"], L["opened"] + 3, "1", "written once per window by main (fetch_add, release). Polled by every waiting helper"),
        ("finished (atomic uint32)", L["finished"], L["finished"] + 3, "1", "reset to 0 by main before the window opens (store, relaxed). Then written once per window by each helper (fetch_add, release). Polled by main during the join"),
        ("n_units (uint32)", L["n_units"], L["n_units"] + 3, "1", "written by main during the cut. Read by every helper once"),
        ("unit_start[0 .. 12]", L["unit_start"], 127, "1", "the first 13 unit boundaries, written by main during the cut, share the polled line"),
        ("unit_start[13 .. 1024]", 128, L["unit_start_end"] - 1, "2 .. 65", "1012 entries of 4 bytes. The whole array holds 1025 entries (max_minibatch_size 1024 + 1), the first 13 on line 1. A thread reads unit_start[u] and [u+1] for each claimed unit"),
        ("helper_windows[0 .. 127]", L["helper_windows"], L["helper_windows_end"] - 1, "65 .. 73", "one per worker_ix. Only its own helper writes entry worker_ix (no atomic needed)"),
        ("padding to the struct end", L["helper_windows_end"], L["sizeof"] - 1, "73", "struct size %d bytes = %d lines" % (L["sizeof"], L["lines"])),
    ]
    return "<table><tr><th>field</th><th class=\"num\">bytes</th><th>cache line</th><th>who writes, who reads</th></tr>" + "".join(
        '<tr><td class="mono">%s</td><td class="num">%d-%d</td><td class="mono">%s</td><td>%s</td></tr>' % (esc(f), a, b, ln, esc(w)) for f, a, b, ln, w in rows) + "</table>"


def sim_table():
    h = ['<table><tr><th>configuration, threads</th><th class="num">unit cost used (us, est. upper bound)</th><th class="num">units per thread (simulation)</th><th class="num">window length, simulation (us)</th><th class="num">Save K measured (us, report 4.3, rounded)</th><th class="num">trace mean and pass-to-pass standard deviation (sd) over the 8 prefill passes (us)</th><th class="num">serial Save K the cost is derived from (us)</th><th class="num">gap, trace mean minus simulation (us)</th></tr>']
    for (cfg, tp), r in SIM.items():
        pt = r["per_thread"]
        h.append('<tr><td>%s, %s (main + %d helpers)</td><td class="num">%s</td><td class="num">%d .. %d</td><td class="num">%.1f</td><td class="num">%d</td><td class="num">%.1f, sd %.1f</td><td class="num">%d</td><td class="num">%+.1f</td></tr>' % (
            cfg, tp, HELPERS[tp], r["cost"], min(pt.values()), max(pt.values()), r["length"], r["measured"], r["trace_mean"], r["trace_sd"], r["serial"], r["trace_mean"] - r["length"]))
    h.append('</table>')
    return "".join(h)


JS = r"""
(function () {
  'use strict';
  var MOCK_UNITS = __MOCK_UNITS__;
  var N_UNITS = 64, CUT_US = __CUT__, ARRIVE_STEP_US = __ARR__, MARK_US = __MARK__, W = __W__;
  var COST = __COST__;
  var MEAS = __MEAS__;
  var TINT = __TINT__, DARK = __DARK__;
  function f1(x) { return x.toFixed(1); }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function tname(x) { return x === 0 ? 'main' : 'helper ' + x; }
  function ownRows(a, b, H, x) { if (x === 0) return 0; var n = 0, i; for (i = a; i < b; i++) if ((i % H) + 1 === x) n++; return n; }
  function ordinal(n) { return n + (n === 1 ? 'st' : (n === 2 ? 'nd' : (n === 3 ? 'rd' : 'th'))); }

  // ---- the event model (identical to gen_page.py simulate())
  function simulate(H, cost) {
    var ev = [], x, t, u, h;
    var free = {}, left = {}, nLeft = 0, nextUnit = 0, lastFinished = 0, mainWaitFrom = 0;
    ev.push({ type: 'enter', t: 0, x: 0 });
    for (h = 1; h <= H; h++) {
      ev.push({ type: 'arrive', t: ARRIVE_STEP_US * h, x: h });
      if (ARRIVE_STEP_US * h < CUT_US) ev.push({ type: 'waitopen', t: ARRIVE_STEP_US * h, x: h });
    }
    ev.push({ type: 'cut', t: 0, x: 0, tEnd: CUT_US });
    ev.push({ type: 'open', t: CUT_US, x: 0 });
    free[0] = CUT_US;
    for (h = 1; h <= H; h++) free[h] = Math.max(ARRIVE_STEP_US * h, CUT_US);
    while (nLeft < H + 1) {
      x = -1;
      for (h = 0; h <= H; h++) { if (left[h]) continue; if (x < 0 || free[h] < free[x]) x = h; }
      t = free[x]; u = nextUnit; nextUnit++;
      if (u < N_UNITS) {
        ev.push({ type: 'claim', t: t, x: x, u: u, counter: u + 1 });
        ev.push({ type: 'done', t: t + cost, x: x, u: u });
        free[x] = t + cost;
      } else {
        left[x] = true; nLeft++;
        if (x === 0) { mainWaitFrom = t; ev.push({ type: 'mainleave', t: t, x: 0, counter: u + 1 }); }
        else { lastFinished = Math.max(lastFinished, t); ev.push({ type: 'finished', t: t, x: x, counter: u + 1 }); }
      }
    }
    var tJoin = Math.max(lastFinished, mainWaitFrom);
    ev.push({ type: 'join', t: tJoin, x: 0 });
    ev.push({ type: 'marks', t: tJoin, x: 0, tEnd: tJoin + MARK_US });
    ev.push({ type: 'release', t: tJoin + MARK_US, x: 0 });
    // same-time events: a thread's done before its next claim; claim-like events in fetch_add order (counter)
    var prio = { enter: 0, arrive: 1, waitopen: 2, cut: 3, open: 4, done: 5, claim: 6, finished: 6, mainleave: 6, join: 7, marks: 8, release: 9 };
    ev.sort(function (a, b) { return a.t - b.t || prio[a.type] - prio[b.type] || (a.counter || 0) - (b.counter || 0) || a.x - b.x || (a.u || 0) - (b.u || 0); });
    return { events: ev, tEnd: tJoin + MARK_US, tJoin: tJoin };
  }

  // ---- state after k events
  function derive(H, sim, k) {
    var st = { time: 0, opened: W - 1, nextUnit: 0, finished: 0, nUnits: 0, hw: {}, thr: {}, units: [], claims: 0, fetchAdds: 0, line0Owner: 'main', line0Moves: 0, line1Sharers: [], line1Invalidations: 0, last: null, phase: 'before', lastClaim: null, linesWritten: 0 };
    var h, i, e, u;
    for (h = 0; h <= H; h++) st.thr[h] = { state: h === 0 ? 'in save_k' : 'rope kernel', unit: -1, units: [], done: 0 };
    for (h = 1; h <= H; h++) st.hw[h] = W - 1;
    for (u = 0; u < N_UNITS; u++) st.units.push({ owner: -1, claimNo: 0, done: false });
    for (i = 0; i < k; i++) {
      e = sim.events[i]; st.last = e; st.time = e.t;
      if (e.type === 'enter') { st.thr[0].state = 'waited for the K channels, enters save_k'; }
      else if (e.type === 'arrive') { st.hw[e.x] = W; st.thr[e.x].state = 'arrived at save_k_helper: helper_windows[' + e.x + '] = ' + W; }
      else if (e.type === 'waitopen') { st.thr[e.x].state = 'spins on opened (' + st.opened + ' < ' + W + ')'; st.line1Sharers.push(e.x); }
      else if (e.type === 'cut') { st.nUnits = N_UNITS; st.thr[0].state = 'cuts the items into ' + N_UNITS + ' units, resets next_unit and finished'; st.phase = 'cut'; }
      else if (e.type === 'open') { st.opened = W; st.line1Invalidations = st.line1Sharers.length; st.line1Sharers = []; st.thr[0].state = 'opened window ' + W + ' (opened = ' + W + ', release)'; st.phase = 'open'; }
      else if (e.type === 'claim') { st.nextUnit = e.counter; st.claims++; st.fetchAdds++; st.units[e.u].owner = e.x; st.units[e.u].claimNo = st.claims; st.thr[e.x].state = 'stores unit ' + e.u; st.thr[e.x].unit = e.u; st.thr[e.x].units.push(e.u); st.lastClaim = e; if (st.line0Owner !== tname(e.x)) { st.line0Moves++; st.line0Owner = tname(e.x); } }
      else if (e.type === 'done') { st.units[e.u].done = true; st.thr[e.x].unit = -1; st.thr[e.x].done++; st.linesWritten += 512; st.thr[e.x].state = 'finished unit ' + e.u + ', claims again'; }
      else if (e.type === 'finished') { st.nextUnit = e.counter; st.fetchAdds++; st.finished++; st.thr[e.x].state = 'left the window: finished = ' + st.finished + ' (release). Idle until the attention output'; if (st.line0Owner !== tname(e.x)) { st.line0Moves++; st.line0Owner = tname(e.x); } }
      else if (e.type === 'mainleave') { st.nextUnit = e.counter; st.fetchAdds++; st.thr[0].state = (st.finished >= H) ? ('no unit left: reads finished = ' + H + ' at once, no wait') : ('no unit left: spins on finished (' + st.finished + ' < ' + H + ')'); if (st.line0Owner !== 'main') { st.line0Moves++; st.line0Owner = 'main'; } }
      else if (e.type === 'join') { st.thr[0].state = 'join: finished == ' + H + ' (acquire), every unit is stored'; st.phase = 'join'; }
      else if (e.type === 'marks') { st.thr[0].state = 'marks 1024 tokens K-complete, credits, counts the latch down'; st.phase = 'marks'; }
      else if (e.type === 'release') { st.thr[0].state = 'Save K span ends: the latch has one of its two counts. The Pending sections start after Save V'; st.phase = 'done'; }
    }
    return st;
  }

  // ---- renderers
  function renderCounters(H, st) {
    var h = ['<div class="scroll"><table class="grid"><tr><th>counter</th><th>value now</th><th>meaning</th></tr>'];
    h.push('<tr><td>opened</td><td class="num">' + st.opened + '</td><td>windows opened in this pass (W = ' + W + ' is this one)</td></tr>');
    h.push('<tr><td>next_unit</td><td class="num">' + st.nextUnit + '</td><td>fetch_adds so far (the next one returns this value). Values 64 and above are empty claims. Final value 64 + ' + (H + 1) + ' = ' + (64 + H + 1) + '</td></tr>');
    h.push('<tr><td>finished</td><td class="num">' + st.finished + '</td><td>helpers that have left the window (main waits for ' + H + ')</td></tr>');
    h.push('<tr><td>n_units</td><td class="num">' + st.nUnits + '</td><td>units of the open window</td></tr>');
    var hw = []; for (var x = 1; x <= H; x++) hw.push(st.hw[x]);
    h.push('<tr><td>helper_windows[1..' + H + ']</td><td class="num">' + hw.join(' ') + '</td><td>windows each helper has entered (its own W)</td></tr>');
    h.push('</table></div>');
    h.push('<div class="scroll"><table class="grid"><tr><th>thread</th><th>state at t = ' + f1(st.time) + ' us</th><th>units claimed so far (... = in progress)</th></tr>');
    for (x = 0; x <= H; x++) {
      var cur = st.last && st.last.x === x;
      var list = st.thr[x].units.map(function (u) { return u === st.thr[x].unit ? u + ' ...' : String(u); }).join(', ');
      h.push('<tr' + (cur ? ' class="currow"' : '') + '><td style="color:' + DARK[x] + ';font-weight:700">' + tname(x) + '</td><td>' + esc(st.thr[x].state) + '</td><td class="num">' + (list || '-') + '</td></tr>');
    }
    h.push('</table></div>');
    document.getElementById('stage-counters').innerHTML = h.join('');
  }

  function renderUnits(st) {
    var h = [], u, m, un, cur, row;
    for (row = 0; row < 2; row++) {
      h.push('<div class="scroll"><div class="ustrip">');
      for (u = 32 * row; u < 32 * row + 32; u++) {
        m = MOCK_UNITS[u]; un = st.units[u];
        cur = st.last && (st.last.type === 'claim' || st.last.type === 'done') && st.last.u === u;
        var style = un.owner >= 0 ? 'background:' + TINT[un.owner] + ';color:#0b0b0b;border-color:' + DARK[un.owner] : '';
        var txt = un.owner >= 0 ? ('u' + u + '<br>#' + un.claimNo + '<br>' + (un.owner === 0 ? 'main' : 'h' + un.owner) + (un.done ? '' : ' ...')) : ('u' + u + '<br>-<br>-');
        h.push('<div class="ucell' + (cur ? ' cur' : '') + '" style="' + style + '" title="unit ' + u + ': items ' + m.items[0] + '..' + (m.items[1] - 1) + ', user ' + m.user + ', positions ' + m.positions[0] + '..' + m.positions[1] + ', page ' + m.page + ' block c' + m.block + '. ' + (un.owner >= 0 ? 'Claim #' + un.claimNo + ' by ' + tname(un.owner) + (un.done ? ', stored' : ', in progress') : 'Not claimed yet') + '">' + txt + '</div>');
      }
      h.push('</div><div class="ulbl">');
      for (u = 4 * row; u < 4 * row + 4; u++) h.push('<div>user ' + (u + 1) + ': units ' + (8 * u) + '-' + (8 * u + 7) + '</div>');
      h.push('</div></div>');
    }
    document.getElementById('stage-units').innerHTML = h.join('');
  }

  function renderLines(H, st) {
    var h = ['<div class="scroll"><div class="wlines">'];
    var l0cur = st.last && (st.last.type === 'claim' || st.last.type === 'finished' || st.last.type === 'mainleave' || st.last.type === 'cut');
    var l1cur = st.last && (st.last.type === 'open' || st.last.type === 'waitopen' || st.last.type === 'finished' || st.last.type === 'join' || st.last.type === 'cut');
    h.push('<div class="wlbl">line 0, bytes 0-63<br>next_unit</div><div class="wl' + (l0cur ? ' cur' : '') + '">value ' + st.nextUnit + '. Held writable by <span class="own">' + esc(st.line0Owner) + '</span>' + (st.fetchAdds === 0 && st.phase !== 'before' ? ' (main wrote the reset)' : '') + '. Line transfers so far (model): ' + st.line0Moves + ' (one per fetch_add by a different thread than the previous writer).</div>');
    var sharers = st.line1Sharers.length ? st.line1Sharers.map(function (x) { return 'helper ' + x; }).join(', ') : 'none';
    var l1 = 'opened ' + st.opened + ', finished ' + st.finished + ', n_units ' + st.nUnits + ', unit_start[0..12]. ';
    if (st.phase === 'before') l1 += 'Helpers spinning on opened hold a read-only copy: ' + sharers + '.';
    else if (st.phase === 'cut') l1 += 'Main writes unit_start[0..12] and n_units on this line during the cut. After the cut it writes finished = 0. Each write invalidates the copies of the spinning helpers (' + sharers + '). Each spinning helper then re-reads the line (model, up to 15 invalidations before the open).';
    else if (st.phase === 'open') l1 += 'Main\'s opened++ invalidated the ' + st.line1Invalidations + ' polling cop' + (st.line1Invalidations === 1 ? 'y' : 'ies') + ' (model). Each spinning helper re-read the line once and saw ' + W + '. Now every thread reads unit_start[u], unit_start[u+1] from it for each claim (read-only copies).';
    else if (st.phase === 'join') l1 += 'Each finished++ moved the line to that helper (model): ' + H + ' transfers in this window. Only the transfers after main started polling invalidated a copy of main.';
    else l1 += 'Idle until the next window.';
    h.push('<div class="wlbl">line 1, bytes 64-127<br>opened, finished, n_units, unit_start[0..12]</div><div class="wl' + (l1cur ? ' cur' : '') + '">' + esc(l1) + '</div>');
    h.push('<div class="wlbl">lines 2-65<br>unit_start[13..1024]</div><div class="wl">Written by main during the cut (' + (st.nUnits ? '65 entries used, unit_start[64] = 1024' : 'not yet written') + '). Read-only copies in every claiming thread afterwards.</div>');
    h.push('<div class="wlbl">lines 65-73<br>helper_windows[0..127]</div><div class="wl">Each helper writes only its own entry, once per window' + (st.last && st.last.type === 'arrive' ? ' (helper ' + st.last.x + ' just did)' : '') + '. No other thread reads it.</div>');
    h.push('</div></div>');
    document.getElementById('stage-lines').innerHTML = h.join('');
  }

  function renderData(H, st, cfg) {
    var h = ['<div class="scroll"><div class="data">'], e = st.lastClaim, m, own, k, planeOff;
    if (!e) {
      h.push('<div class="dl">no unit claimed yet</div><div class="db">The first claim shows the source rows and the destination lines of that unit here.</div>');
    } else {
      m = MOCK_UNITS[e.u]; own = ownRows(m.items[0], m.items[1], H, e.x);
      h.push('<div class="dl"><b>source</b>: K buffer rows of unit ' + e.u + '</div><div class="db">items ' + m.items[0] + '..' + (m.items[1] - 1) + ' of ks: 16 rows x 2048 bytes = 32 KiB (8 KV heads x 256 bytes each). Row i was roped by helper (i mod ' + H + ') + 1. ' + tname(e.x) + ' roped ' + own + ' of the 16 rows itself and reads the other ' + (16 - own) + ' from other cores\' caches (model: the level, L2 or L3, is not measured).</div>');
      h.push('<div class="dl"><b>destination</b>: KV cache, page ' + m.page + ' of user ' + m.user + ', block c' + m.block + '</div><div class="db">8 planes (one per KV head), each 16 KiB in DRAM. This unit writes 4 panels x 16 lines = 64 lines per plane, 512 lines = 32 KiB in all' + (cfg === 'ab' ? ', each line with one full-line store' : ', each line with 16 partial writes of 4 bytes (scatter, block store off)') + '. The lines are assumed cold before the store (model). After it they are dirty in ' + tname(e.x) + '\'s L1D, or already evicted to its L2 (model). The unit moves 32 KiB of source rows and 32 KiB of destination lines through a 48 KiB L1D. Not all of it fits. Write-back to DRAM later.<div class="heads">');
      for (k = 0; k < 8; k++) {
        planeOff = m.block * 1024;
        h.push('<div class="hd">KV head ' + k + '<br>panels (s0..s3, c' + m.block + ')<br>plane bytes ' + planeOff + ', +4096, +8192, +12288<br>64 lines</div>');
      }
      h.push('</div></div>');
    }
    h.push('<div class="dl"><b>totals</b> in this window</div><div class="db">units stored ' + st.units.filter(function (u) { return u.done; }).length + ' of 64, lines written ' + st.linesWritten + ' of 32768 (' + (st.linesWritten * 64 / 1048576).toFixed(2) + ' MiB of 2 MiB: 1024 tokens x 8 KV heads x 256 bytes).</div>');
    h.push('</div></div>');
    document.getElementById('stage-data').innerHTML = h.join('');
  }

  function renderLanes(H, sim, k, st, cost, cfg, tp) {
    var W_ = 960, LEFT = 90, RIGHT = 20, TOP = 40, LH = 22, GAP = 6;
    var meas = MEAS[cfg][tp];
    var tMax = Math.max(sim.tEnd, meas) * 1.02;
    var x = function (t) { return LEFT + (W_ - LEFT - RIGHT) * t / tMax; };
    var laneY = function (i) { return TOP + i * (LH + GAP); };
    var Hh = laneY(H + 1) + 72;
    var s = ['<svg class="lanes" viewBox="0 0 ' + W_ + ' ' + Hh + '" role="img" aria-label="Who does what when: one lane per thread, wall-clock time in microseconds to scale, solid = storing a unit, thin grey dashed outline = a helper waiting, thin red dashed outline = main waiting, thick black dashed frame = the last unit to finish (the critical path)">'];
    var i, e, y, hh;
    for (i = 0; i <= H; i++) {
      y = laneY(i);
      s.push('<rect x="' + LEFT + '" y="' + y + '" width="' + (W_ - LEFT - RIGHT) + '" height="' + LH + '" fill="#f7f6f3"/>');
      s.push('<text x="' + (LEFT - 6) + '" y="' + (y + LH * 0.72) + '" font-size="11" text-anchor="end" fill="' + DARK[i] + '" font-weight="600">' + tname(i) + '</text>');
    }
    var busy = {}, waitFrom = {}, done = [];
    for (i = 0; i <= H; i++) busy[i] = null;
    for (i = 0; i < k; i++) {
      e = sim.events[i];
      if (e.type === 'cut') s.push('<rect x="' + x(0) + '" y="' + (laneY(0) + 3) + '" width="' + (x(e.tEnd) - x(0)) + '" height="' + (LH - 6) + '" fill="#8a8987"><title>cut units 0..' + e.tEnd + ' us (mock)</title></rect>');
      else if (e.type === 'arrive') s.push('<line x1="' + x(e.t) + '" y1="' + (laneY(e.x) + 1) + '" x2="' + x(e.t) + '" y2="' + (laneY(e.x) + LH - 1) + '" stroke="' + DARK[e.x] + '" stroke-width="1.5"><title>helper ' + e.x + ' arrives (mock ' + f1(e.t) + ' us)</title></line>');
      else if (e.type === 'waitopen') waitFrom[e.x] = e.t;
      else if (e.type === 'open') { for (hh = 1; hh <= H; hh++) if (waitFrom[hh] !== undefined) { s.push('<rect x="' + x(waitFrom[hh]) + '" y="' + (laneY(hh) + 3) + '" width="' + Math.max(1, x(e.t) - x(waitFrom[hh])) + '" height="' + (LH - 6) + '" fill="none" stroke="#a9a8a4" stroke-dasharray="3,3"><title>helper ' + hh + ' spins on opened ' + f1(waitFrom[hh]) + '-' + f1(e.t) + ' us</title></rect>'); delete waitFrom[hh]; } }
      else if (e.type === 'claim') busy[e.x] = e;
      else if (e.type === 'done') { s.push('<rect x="' + x(e.t - cost) + '" y="' + (laneY(e.x) + 3) + '" width="' + (x(e.t) - x(e.t - cost)) + '" height="' + (LH - 6) + '" fill="' + DARK[e.x] + '" opacity="0.85"><title>' + tname(e.x) + ' stores unit ' + e.u + ': ' + f1(e.t - cost) + '-' + f1(e.t) + ' us</title></rect><text x="' + ((x(e.t - cost) + x(e.t)) / 2) + '" y="' + (laneY(e.x) + LH * 0.72) + '" font-size="9" text-anchor="middle" fill="#fff">' + e.u + '</text>'); busy[e.x] = null; done.push(e); }
      else if (e.type === 'mainleave') waitFrom[0] = e.t;
      else if (e.type === 'join') { if (waitFrom[0] !== undefined) { if (e.t > waitFrom[0]) s.push('<rect x="' + x(waitFrom[0]) + '" y="' + (laneY(0) + 3) + '" width="' + (x(e.t) - x(waitFrom[0])) + '" height="' + (LH - 6) + '" fill="none" stroke="#d03b3b" stroke-dasharray="3,3"><title>main spins on finished ' + f1(waitFrom[0]) + '-' + f1(e.t) + ' us</title></rect>'); delete waitFrom[0]; } }
      else if (e.type === 'marks') s.push('<rect x="' + x(e.t) + '" y="' + (laneY(0) + 3) + '" width="' + (x(e.tEnd) - x(e.t)) + '" height="' + (LH - 6) + '" fill="#d03b3b"><title>marks, credits, latch (mock ' + MARK_US + ' us)</title></rect>');
    }
    // waits still in progress at the current time
    for (hh = 0; hh <= H; hh++) if (waitFrom[hh] !== undefined && st.time > waitFrom[hh]) s.push('<rect x="' + x(waitFrom[hh]) + '" y="' + (laneY(hh) + 3) + '" width="' + Math.max(1, x(st.time) - x(waitFrom[hh])) + '" height="' + (LH - 6) + '" fill="none" stroke="' + (hh === 0 ? '#d03b3b' : '#a9a8a4') + '" stroke-dasharray="3,3"><title>' + (hh === 0 ? 'main spins on finished (in progress)' : 'helper ' + hh + ' spins on opened (in progress)') + '</title></rect>');
    // units in progress at the current time
    for (i = 0; i <= H; i++) if (busy[i]) { e = busy[i]; s.push('<rect x="' + x(e.t) + '" y="' + (laneY(i) + 3) + '" width="' + Math.max(1, x(st.time) - x(e.t)) + '" height="' + (LH - 6) + '" fill="' + DARK[i] + '" opacity="0.4"><title>' + tname(i) + ' storing unit ' + e.u + ' (in progress)</title></rect>'); }
    // critical path at the end: the last unit to finish
    if (k >= sim.events.length) {
      var lastDone = null; for (i = 0; i < done.length; i++) if (!lastDone || done[i].t > lastDone.t) lastDone = done[i];
      if (lastDone) s.push('<rect x="' + (x(lastDone.t - cost) - 1) + '" y="' + (laneY(lastDone.x) + 0.5) + '" width="' + (x(lastDone.t) - x(lastDone.t - cost) + 2) + '" height="' + (LH - 1) + '" fill="none" stroke="#0b0b0b" stroke-width="2" stroke-dasharray="5,2"><title>critical path: the last unit to finish</title></rect>');
    }
    // measured marker (own header line) and time cursor
    var lx = x(meas), anchor = 'middle';
    if (lx > W_ - RIGHT - 65) { lx = W_ - RIGHT; anchor = 'end'; }
    s.push('<line x1="' + x(meas) + '" y1="' + (TOP - 4) + '" x2="' + x(meas) + '" y2="' + laneY(H + 1) + '" stroke="#8a8987" stroke-dasharray="4,3"/><text x="' + lx + '" y="' + (TOP - 22) + '" font-size="10" text-anchor="' + anchor + '" fill="#8a8987">measured Save K ' + meas + ' us</text>');
    s.push('<line x1="' + x(st.time) + '" y1="' + (TOP - 4) + '" x2="' + x(st.time) + '" y2="' + laneY(H + 1) + '" stroke="#2a78d6" stroke-width="1.5"/>');
    s.push('<text x="' + x(st.time) + '" y="' + (TOP - 8) + '" font-size="10" text-anchor="middle" fill="#2a78d6">t = ' + f1(st.time) + ' us</text>');
    var ay = laneY(H + 1) + 6;
    s.push('<line x1="' + LEFT + '" y1="' + ay + '" x2="' + (W_ - RIGHT) + '" y2="' + ay + '" stroke="#52514e"/>');
    var step = tMax > 120 ? 25 : (tMax > 60 ? 10 : 5);
    for (var tt = 0; tt <= tMax; tt += step) { s.push('<line x1="' + x(tt) + '" y1="' + ay + '" x2="' + x(tt) + '" y2="' + (ay + 4) + '" stroke="#52514e"/><text x="' + x(tt) + '" y="' + (ay + 15) + '" font-size="10" text-anchor="middle" fill="#52514e">' + tt + '</text>'); }
    s.push('<text x="' + LEFT + '" y="' + (ay + 30) + '" font-size="10.5" fill="#52514e">wall-clock time, us, to scale. Unit cost ' + cost + ' us (est.). Arrivals, the cut and the marks are mock durations.</text>');
    s.push('<text x="' + LEFT + '" y="' + (ay + 42) + '" font-size="10.5" fill="#52514e">The grey dashed line is the measured Save K span of configuration ' + cfg + ' at ' + tp + '.</text>');
    s.push('</svg>');
    document.getElementById('stage-lanes').innerHTML = s.join('');
  }

  function describe(H, sim, k, st, cost, cfg) {
    var e = st.last;
    if (!e) return '<b>Start.</b> Prefill pass, one layer, window ' + W + ' of the pass: 1024 items, 64 units, main plus ' + H + ' helpers. Time 0 is the start of the Save K span. Press Play or Step.';
    var head = '<b>Step ' + k + ' of ' + sim.events.length + ', t = ' + f1(e.t) + ' us.</b> ';
    var m, own;
    switch (e.type) {
      case 'enter': return head + 'Main has waited for every item\'s K channel (all helper rope stripes are done) and enters save_k. k_store_shared returns true: the VNNI K layout is on, ' + (H + 1) + ' workers, and 1024 items > 16.';
      case 'arrive': return head + 'Helper ' + e.x + ' reaches save_k_helper at the same statement position of its schedule (its rope stripe ended, mock arrival ' + f1(e.t) + ' us). It increments helper_windows[' + e.x + '] to ' + W + '. That is the window it must enter.';
      case 'waitopen': return head + 'Helper ' + e.x + ' spins: opened is ' + st.opened + ', it needs ' + W + '. Each turn re-reads its own copy of the opened line and pauses.';
      case 'cut': return head + 'Main cuts the item list: 64 units, unit_start[u] = 16u, unit_start[64] = 1024 (a unit ends where the page, the block or the KV flag changes). After the cut it resets next_unit = 0 (line 0) and finished = 0 (line 1). The mock shows both inside the cut step. Duration ' + CUT_US + ' us (mock).';
      case 'open': return head + 'Main does opened.fetch_add(1) with release: opened = ' + W + '. Every spinning helper now reads ' + W + ' >= ' + W + ' and enters the claim loop (acquire: it sees the unit table). Main enters the same claim loop.';
      case 'claim':
        m = MOCK_UNITS[e.u]; own = ownRows(m.items[0], m.items[1], H, e.x);
        return head + tname(e.x) + ' claims: next_unit.fetch_add(1) returns ' + e.u + ' (next_unit is now ' + e.counter + '). Unit ' + e.u + ' = items ' + m.items[0] + '..' + (m.items[1] - 1) + ' = user ' + m.user + ', positions ' + m.positions[0] + '..' + m.positions[1] + ', page ' + m.page + ' of that user, block c' + m.block + '. ' +
          (cfg === 'ab' ? 'It stores 8 KV heads x 64 full-line stores = 512 lines (32 KiB), estimated ' + cost + ' us. ' : 'Block store off: it writes the 16 rows one by one, 4 scatters of 16 x 4 bytes per row per KV head = 512 scatters. They touch the same 512 lines (32 KiB), each line 16 times. Estimated ' + cost + ' us. ') +
          'The 16 rows were roped by all ' + H + ' helper cores (round-robin). ' + tname(e.x) + ' roped ' + own + ' of them and reads the other ' + (16 - own) + ' from other cores\' caches (model, cache level not measured).';
      case 'done': return head + tname(e.x) + ' has stored unit ' + e.u + ' (its ' + ordinal(st.thr[e.x].done) + ' unit). It claims again.';
      case 'finished': return head + 'Helper ' + e.x + ' claimed ' + (e.counter - 1) + ' >= 64: an empty claim, no unit left. It does finished.fetch_add(1) with release: finished = ' + st.finished + '. It leaves the window and idles until the attention output, as before the change.';
      case 'mainleave': return head + 'Main claimed ' + (e.counter - 1) + ' >= 64: an empty claim, no unit left. ' + (st.finished >= H ? 'Every helper has already left (finished = ' + H + ' of ' + H + '). The join loop exits at its first read. The loop body never runs. Main therefore never reaches the 120 s watchdog check.' : 'It spins on finished (' + st.finished + ' of ' + H + ') with a 120 s watchdog.' + (sim.tJoin === e.t ? ' In this simulation every helper reaches its empty claim at the same simulated time as main. The join wait therefore has zero length (mock). The chart draws no wait box.' : ''));
      case 'join': return head + 'Join: finished == ' + H + ' (acquire). Every helper has left the window. Every unit is therefore stored and visible to main. Units per thread: ' + Object.keys(st.thr).map(function (x) { return tname(+x) + ' ' + st.thr[x].units.length; }).join(', ') + '.';
      case 'marks': return head + 'Main alone: mark_k_complete for each of the 1024 tokens, GOF credits when the layer has a hardware attention slot, then upstream_kvs_ready.count_down for the downstream minibatches (duration ' + MARK_US + ' us, mock).';
      case 'release': return head + '<b>Save K ends at ' + f1(e.t) + ' us in this simulation</b> (measured: the grey marker). Main has counted the latch down once. Save V follows on main alone, and the attention workers\' Pending sections start when it ends (section 2.2).';
    }
    return head;
  }

  // ---- controller
  var cfg = 'ab', tp = 'tp2', H = 7, cost = COST[cfg][tp], sim = simulate(H, cost), k = 0, timer = null;
  var speedSel, cfgSel, tpSel;
  function render() {
    var st = derive(H, sim, k);
    document.getElementById('status').innerHTML = describe(H, sim, k, st, cost, cfg);
    document.getElementById('counters').innerHTML =
      '<span>event <b>' + k + '</b> / ' + sim.events.length + '</span><span>simulated time <b>' + f1(st.time) + '</b> us</span>' +
      '<span>units claimed <b>' + st.claims + '</b> / 64</span><span>fetch_adds on next_unit <b>' + st.fetchAdds + '</b> / ' + (64 + H + 1) + ' (64 units + one empty claim per thread)</span><span>units stored <b>' + st.units.filter(function (u) { return u.done; }).length + '</b> / 64</span>' +
      '<span>helpers finished <b>' + st.finished + '</b> / ' + H + '</span><span>next_unit line transfers (model) <b>' + st.line0Moves + '</b></span>' +
      '<span>simulated window length <b>' + f1(sim.tEnd) + '</b> us, measured Save K <b>' + MEAS[cfg][tp] + '</b> us</span>';
    renderLanes(H, sim, k, st, cost, cfg, tp);
    renderCounters(H, st);
    renderUnits(st);
    renderLines(H, st);
    renderData(H, st, cfg);
    document.getElementById('btn-play').textContent = timer ? 'Pause' : 'Play';
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function setK(v) { k = Math.max(0, Math.min(sim.events.length, v)); render(); }
  function tick() { if (k >= sim.events.length) { stop(); render(); return; } setK(k + 1); }
  function play() { if (timer) { stop(); render(); return; } if (k >= sim.events.length) k = 0; var sps = parseFloat(speedSel.value) || 4; timer = setInterval(tick, 1000 / sps); render(); }
  function nextPhase() {
    var i; for (i = k; i < sim.events.length; i++) { var t = sim.events[i].type; if (t === 'open' || t === 'join' || t === 'release' || t === 'finished') { setK(i + 1); return; } }
    setK(sim.events.length);
  }
  function reconfigure() { stop(); cfg = cfgSel.value; tp = tpSel.value; H = (tp === 'tp2') ? 7 : 15; cost = COST[cfg][tp]; sim = simulate(H, cost); k = 0; render(); }
  function selfCheck() {
    var want = __SIM_LENGTHS__, got = [], ok = true, key, parts, r, i, prev, cnt;
    for (key in want) {
      parts = key.split('|'); r = simulate(parts[1] === 'tp2' ? 7 : 15, COST[parts[0]][parts[1]]);
      got.push(key.replace('|', ' at ') + ' = ' + r.tEnd.toFixed(1) + ' us');
      if (Math.abs(r.tEnd - want[key]) > 0.05) ok = false;
      // the displayed order of fetch_adds must be monotone
      prev = 0;
      for (i = 0; i < r.events.length; i++) { cnt = r.events[i].counter; if (cnt !== undefined) { if (cnt !== prev + 1) ok = false; prev = cnt; } }
    }
    var el = document.getElementById('selfcheck');
    if (el) el.textContent = 'Self-check in this browser: simulated window lengths ' + got.join(', ') + (ok ? '. They match the values the generator computed for the static tables, and every event list shows the fetch_adds in counter order.' : '. MISMATCH with the generator or a non-monotone fetch_add order. Do not trust the simulation numbers.');
  }
  document.addEventListener('DOMContentLoaded', function () {
    speedSel = document.getElementById('speed'); cfgSel = document.getElementById('cfg'); tpSel = document.getElementById('tp');
    document.getElementById('btn-play').addEventListener('click', play);
    document.getElementById('btn-back').addEventListener('click', function () { stop(); setK(k - 1); });
    document.getElementById('btn-fwd').addEventListener('click', function () { stop(); setK(k + 1); });
    document.getElementById('btn-phase').addEventListener('click', function () { stop(); nextPhase(); });
    document.getElementById('btn-end').addEventListener('click', function () { stop(); setK(sim.events.length); });
    document.getElementById('btn-reset').addEventListener('click', function () { stop(); setK(0); });
    cfgSel.addEventListener('change', reconfigure); tpSel.addEventListener('change', reconfigure);
    speedSel.addEventListener('change', function () { if (timer) { stop(); play(); } });
    document.addEventListener('keydown', function (e) {
      var tag = e.target && e.target.tagName;
      if (tag === 'SELECT' || tag === 'INPUT') return;
      if (tag === 'BUTTON' && e.key === ' ') return;
      if (e.key === 'ArrowRight') { stop(); setK(k + 1); e.preventDefault(); }
      else if (e.key === 'ArrowLeft') { stop(); setK(k - 1); e.preventDefault(); }
      else if (e.key === ' ') { play(); e.preventDefault(); }
    });
    selfCheck();
    render();
  });
})();
"""


def build():
    cost_js = json.dumps({cfg: {tp: UNIT_COST[(cfg, tp)] for tp in ("tp2", "tp4")} for cfg in ("ab", "b")})
    js = (JS.replace("__MOCK_UNITS__", json.dumps(UNITS["mock_pass"]["units"], separators=(",", ":")))
          .replace("__CUT__", str(CUT_US)).replace("__ARR__", str(ARRIVE_STEP_US)).replace("__MARK__", str(MARK_US)).replace("__W__", str(W_EXAMPLE))
          .replace("__COST__", cost_js).replace("__MEAS__", json.dumps({"ab": MEAS["ab"], "b": MEAS["b"]}))
          .replace("__TINT__", json.dumps(TINT)).replace("__DARK__", json.dumps(DARK))
          .replace("__SIM_LENGTHS__", json.dumps({"%s|%s" % k: round(v["length"], 3) for k, v in SIM.items()})))
    s_ab2, s_b2 = SIM[("ab", "tp2")], SIM[("b", "tp2")]
    gaps = sorted(((v["measured"] - v["length"]), "%s at %s" % k) for k, v in SIM.items())
    H = []
    H.append('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">')
    H.append('<title>Shared block save, claim by claim</title>')
    H.append('<style>' + CSS + '</style></head><body><main>')
    H.append('<h1>Shared block save, claim by claim</h1>')
    H.append('<p class="sub">A companion to section 3.2 (b) of <a href="store-remedies-report.html">the store-remedies report</a> (status/store-remedies-report.html). The report calls the remedy striping. The code at head calls it the shared block save. '
             'Code read at commit %s of branch jhan-amx-vnniK (the PR 4424 head). Revisions 1 to 4 read commit 04ffeedccb. Between the two commits the cited files are byte-identical, except three wording lines of kv_cache.hpp and the page_info comment of gof.hpp (lines 61-77). Generated %s by exec/shared-save-animation/gen_page.py and context_sections.py (revision %d). The block store of one unit is the subject of the companion page <a href="block-store-animation.html">block-store-animation.html</a>.</p>' % (HEAD, NOW, REV))
    H.append('<div class="short"><p><b>Short version.</b> In a prefill layer the main thread used to store all 8192 K rows (1024 items x 8 KV heads) alone while the 7 (tp2) or 15 (tp4) main helpers were idle. '
             'Now main cuts the pass\'s item list into 64 work units (one per 16-token page block). Main opens a window (one counter increment). Then main and the helpers each claim the next unit from a second counter until none is left. '
             'After the last helper has left the window, main marks the tokens complete and counts the latch down once (the V save gives the second count). The attention workers have been running their Ready sections (the pages of earlier passes) since the Save K start. Their Pending sections (this pass\'s pages) start once Save V has counted the latch down too.</p>'
             '<p>Measured per prefill layer (report section 4.3): the shared save alone cuts Save K from 858 us to 175 us at tp2 and from 863 us to 110 us at tp4. With the block store as well: 80 us and 60 us. <b>What this page adds:</b></p><ul>'
             '<li><b>Context</b> (sections 2 and 3, added 2026-09-18). Section 2 places the save in prefill (run, pass, layer) and shows measured lanes of one layer before and after the remedies. It lists what one save reads and writes, and which functions and threads take part. Section 3 relates the shared save to the block store in the 2 x 2 table of section 3.2 (rows = who writes the blocks, columns = how one block is written, cells = the measured Save K per prefill layer) and gives the factors between the cells. A factor is the span before a remedy divided by the span after it.</li>'
             '<li><b>Animation</b> (section 6): every arrival, cut, open, claim, unit completion, empty claim and the join as one event each, with the counter values and a wall-clock lanes chart to scale.</li>'
             '<li><b>Real numbers</b>: the 64 units of the pass with their items, users, token positions, pages and blocks (section 4.1). The unit test\'s irregular 48-item pass with its 9 units, reproduced (section 4.2). The fields of the window and the cache line that holds each one, with byte offsets (section 5).</li>'
             '<li><b>Sequencing</b>: the protocol fixes the order of the phases (cut, open, claims, empty claims, join, marks, release). The claim order inside the window is the order of the fetch_add calls. That order depends on which thread is free first. It is not deterministic in the real run. The page shows one mock order as claim numbers on the units.</li>'
             '<li><b>Cache lines and DRAM</b>: which thread holds the claim-counter line, why next_unit has a cache line of its own, what main\'s writes during the cut and its opened++ do to the copies of the spinning helpers, where a claimed unit\'s 16 source entries come from (one K buffer entry per item, 8 K rows each; a helper that claims reads 2 or 3 entries from its own core and 13 or 14 from the 6 other helper cores at tp2, and main reads all 16 from the 7 helper cores), and which 512 lines of which planes in DRAM the unit writes (section 6.5). All of it is a model, not a measurement.</li>'
             '<li><b>The gap</b>: the simulation with an estimated unit cost gives %.0f us for ab at tp2 against 80 us measured, and %.0f us for b against 175 us. The difference is not attributed: no per-thread trace of the window exists (section 6.6).</li></ul></div>' % (s_ab2["length"], s_b2["length"]))

    H.append('<h2>1. Words used here</h2>')
    H.append('<div class="scroll">' + words_table() + '</div>')
    H.append(ctx.context_html())

    H.append('<h2>4. The work units</h2>')
    H.append('<h3>4.1 The mock pass: prefill pass 3 of the 8-user prompt-1024 run, one layer</h3>')
    H.append('<p>The traced layer of report section 2.2 (the layer of section 2.2 of this page) is in prefill pass 3. That pass holds each user\'s third chunk (a 128-token slice of the 1024-token prompt), positions 256 to 383. Those positions are pages 4 and 5 of that user (pages count from 0), all four blocks of each. The page assumes the item list holds user 1\'s 128 items first, then user 2\'s, and so on (the report\'s Figure 3.2 draws the same order, and the scheduler decides the real order). Every item has KV work in prefill. k_store_cut_units then gives 64 units of 16 items: unit_start[u] = 16u, unit_start[64] = 1024 [model.hpp k_store_cut_units, exec/shared-save-animation/cut_units.py]. Every unit fills all 16 columns (token slots 0 .. 15) of its block.</p>')
    H.append('<div class="scroll">' + units_table() + '</div>')
    H.append('<p class="take">The rope stripe rule (last column): item i of the pass was roped by helper (i mod 7) + 1 at tp2. So the 16 rows of any unit were written by all 7 helper cores, 3 rows by two of them and 2 rows by five. A helper that claims the unit roped 2 or 3 of its 16 rows itself and reads the other 13 or 14 from other cores\' caches. At tp4 (15 helpers in a prefill pass) one helper roped 2 of the unit\'s 16 entries and each of the other 14 helpers roped 1. So a claiming helper reads 14 or 15 of the 16 entries from other cores\' caches. Main roped no row and reads all 16 from other cores\' caches (a model statement, the cache level is not measured).</p>')
    H.append('<h3>4.2 An irregular pass: the unit test\'s 48 items, 9 units</h3>')
    H.append('<p>The unit test t_llama_unit.cpp builds a pass with runs that start mid-block, an item without KV work in the middle, a page crossing, a lone token and a trailing item without KV work, and runs the shared save with three threads [t/t_llama_unit.cpp:2572-2815]. The Python copy of the cut rule in exec/shared-save-animation/cut_units.py reproduces the test\'s expected unit_start = [0, 3, 4, 11, 16, 32, 40, 41, 47, 48] exactly. The copy identifies a page by the pair (user, position divided by 64 and rounded down). The code identifies a page by the page object. For these two passes both rules cut at the same places.</p>')
    H.append('<div class="scroll">' + test_units_table() + '</div>')
    H.append('<p class="take">Two facts to read off the table. An item without KV work is a unit of its own (units 1 and 8): a thread claims it and store_k_block skips it. An item without KV work between two items of one block splits them into three units. The cut rule starts a new unit at every change of the KV flag [model.hpp k_store_cut_units]. Units 0 and 2 show it: both are block c0 of page 0, split by unit 1. A unit holds a second run only when a column repeats inside it (store_k_block ends the run at the repeated column and starts the next run there) [model.hpp store_k_block]. That case does not occur in this test.</p>')

    H.append('<h2>5. The window in memory: batch::k_store_window</h2>')
    H.append('<p>The window is one struct per minibatch. Its layout puts the claim counter on a cache line of its own. So the 72 (tp2) or 80 (tp4, prefill) fetch_adds on next_unit per window (64 unit claims plus one empty claim per thread, each a write) never invalidate the line the waiting helpers poll (model). The offsets below come from a replica of the struct compiled with g++ (exec/shared-save-animation/window_layout.cpp, max_minibatch_size = 1024 as in the generated plugins [ingest/src/TronCpp.hs:263], cache_line_size = 64 [common/util.hpp]).</p>')
    H.append('<div class="scroll">' + layout_table() + '</div>')
    H.append('<div class="answer"><p><b>Why two lines (model).</b> While a helper waits, it spins on opened: its core keeps a read-only copy of line 1 in L1D, and the spin loop reads that copy without any traffic. Before the open, main writes unit_start[0..12] and then n_units on that same line 1 during the cut, and then finished = 0 after the cut returns [model.hpp k_store_cut_units, save_k_impl]. That is 15 writes on line 1. Each of them, and then the single opened++, invalidates the copies of the helpers that are already spinning: up to 15 invalidations per window, plus one (model). Each helper then re-reads the line. If next_unit shared that line, the 72 or 80 fetch_adds by 8 or 16 different threads would invalidate the polling copies again and again. The struct isolates only next_unit, and its comment says why: a claim must not invalidate the line the waiting threads poll [common.hpp k_store_window_t].</p></div>')

    H.append('<h2>6. The animation</h2>')
    H.append('<p>The animation plays one window: main plus 7 helpers (tp2) or 15 helpers (tp4, the prefill split; section 2.2), 64 units. Each event is one step: a helper\'s arrival, the cut, the open, a claim, a unit completion, an empty claim, the join, the marks and the release. The lanes chart draws the events on a wall-clock axis to scale. Keys: right and left arrows step, space plays.</p>')
    H.append('<div class="controls"><label>Unit cost <select id="cfg"><option value="ab">block store units (configuration ab: %s us at tp2, %s us at tp4)</option><option value="b">scatter units (configuration b: %s us at tp2, %s us at tp4)</option></select></label>'
             '<label>Threads <select id="tp"><option value="tp2">tp2: main + 7 helpers</option><option value="tp4">tp4: main + 15 helpers (a prefill pass)</option></select></label>'
             '<button id="btn-play">Play</button><button id="btn-back">Step back</button><button id="btn-fwd">Step</button><button id="btn-phase">Next phase</button><button id="btn-end">To the end</button><button id="btn-reset">Reset</button>'
             '<label>Speed <select id="speed"><option value="1">1 event/s</option><option value="4" selected>4 events/s</option><option value="10">10 events/s</option><option value="25">25 events/s</option></select></label></div>' % (UNIT_COST[("ab", "tp2")], UNIT_COST[("ab", "tp4")], UNIT_COST[("b", "tp2")], UNIT_COST[("b", "tp4")]))
    H.append('<div class="status" id="status">The animation needs JavaScript. Sections 4, 5 and 6.6 carry the same facts as static tables.</div>')
    H.append('<div class="counters" id="counters"></div>')
    H.append('<div class="legend">' + legend_swatches() +
             '<span><span class="sw" style="border-style:dashed"></span>waiting (spin)</span><span><span class="sw" style="border:2px dashed #0b0b0b"></span>critical path (the last unit to finish)</span><span><span class="sw" style="box-shadow:0 0 0 2px #2a78d6"></span>touched by the current event</span></div>')
    H.append('<h4>6.1 Who does what when (wall-clock lanes, to scale)</h4><p class="stagehint">Solid blocks are units being stored (the number is the unit). Grey or red thin dashed outlines are spin-waits (red for main). The black dashed frame is the last unit to finish (the critical path). The grey block at the start of main\'s lane is the cut, and the red block at its end is the marks. A short vertical tick is a helper\'s arrival. The blue line is the simulated time of the current event. The grey dashed line is the measured Save K span of this configuration for comparison.</p><div class="fig" id="stage-lanes"></div>')
    H.append('<h4>6.2 The counters and the threads</h4><div id="stage-counters"></div>')
    H.append('<h4>6.3 The 64 units: who claimed which, in which order</h4><p class="stagehint">Two rows of 32 units (users 1-4 above, users 5-8 below). Each cell is one unit: its number, its claim number (#) and its owner (main, or h1 .. h' + str(HELPERS["tp2"]) + ' at tp2 and h1 .. h' + str(HELPERS["tp4"]) + ' at tp4). Hover for items, user, positions, page and block.</p><div id="stage-units"></div>')
    H.append('<h4>6.4 The cache lines of the window (model)</h4>'
             '<p class="stagehint"><b>Model used here (schematic).</b></p><ul class="stagehint">'
             '<li>A line that one core writes moves to that core (a line transfer). Other cores\' copies are invalidated.</li>'
             '<li>A core that spins on a value re-reads its own copy of the line. It causes no traffic until the copy is invalidated.</li>'
             '<li>A fetch_add is a write. So every fetch_add by a different thread than the previous writer moves the next_unit line once. The animation counts these transfers.</li>'
             '<li>Not measured: the time a transfer costs, the cache level a unit\'s source rows come from, and whether the destination lines are fetched before a full-line store (see the companion page).</li></ul>'
             '<div id="stage-lines"></div>')
    H.append('<h4>6.5 The data of the claimed unit: source rows and destination lines (model)</h4>'
             '<p class="stagehint">Updated at every claim. The source is 16 rows of the K buffer, written by the helpers\' rope stripes. The destination is 64 lines in each of the 8 planes of the unit\'s page, in the KV cache in DRAM. The companion page shows one plane\'s 64 lines store by store.</p><div id="stage-data"></div>')
    H.append('<h3>6.6 Simulation against measurement</h3>')
    H.append('<p>The simulation uses a constant unit cost: the serial Save K of the matching configuration and thread count divided by 64 units (346 / 64 = %s us and 353 / 64 = %s us for block-store units, 858 / 64 = %s us and 863 / 64 = %s us for scatter units). That unit cost is an upper bound (est.). The serial span also contains the marks loop and the latch. Those two parts are not measured apart. Arrivals, the cut and the marks are mock durations (%s us per helper, %s us, %s us). Claims cost nothing in the simulation.</p>' % (UNIT_COST[("ab", "tp2")], UNIT_COST[("ab", "tp4")], UNIT_COST[("b", "tp2")], UNIT_COST[("b", "tp4")], ARRIVE_STEP_US, CUT_US, MARK_US))
    H.append('<p>The measured spans come from commit 9928cb2849. Its window handed out 16-item blocks of the item list and joined on two counters. This page animates the head protocol: page-block units and one join counter (commit 10fc7c724c and later). For the report\'s pass both cut rules give the same 64 units. So the unit count and the unit cost of commit 9928cb2849 also apply to the head protocol. The join cost may differ. No Save K span of the head protocol is measured for qwen3-4b (report section 4.4 gives TTFT (time to first token) and TPS (generated tokens per second, per user) cells for commit 10fc7c724c, not a Save K trace span).</p>')
    H.append('<div class="scroll">' + sim_table() + '</div>')
    within = [(k, v) for k, v in SIM.items() if abs(v["trace_mean"] - v["length"]) <= 2 * v["trace_sd"]]
    outside = sorted(((v["trace_mean"] - v["length"]), "%s at %s" % k) for k, v in SIM.items() if abs(v["trace_mean"] - v["length"]) > 2 * v["trace_sd"])
    take = ('In all four cases' if len(outside) == len(SIM) else 'In %d of the four cases' % len(outside)) + ' the measured Save K (trace mean) is longer than the simulation, by %.1f us (%s) to %.1f us (%s). Those gaps are more than twice the pass-to-pass standard deviation of the measurement (%.1f to %.1f us).' % (
        outside[0][0], outside[0][1], outside[-1][0], outside[-1][1], min(v["trace_sd"] for v in SIM.values()), max(v["trace_sd"] for v in SIM.values()))
    if within:
        take += ' In the remaining case%s (%s) the gap is within twice the spread: %s.' % ('s' if len(within) > 1 else '', ', '.join('%s at %s' % k for k, v in within), ', '.join('%+.1f us against a standard deviation of %.1f us' % (v["trace_mean"] - v["length"], v["trace_sd"]) for k, v in within))
    else:
        l8 = simulate(8, UNIT_COST[("b", "tp4")])[0]
        take += ' No case agrees with the simulation within twice the spread. Revisions 1 to 4 of this page simulated tp4 with 8 helpers (the decode split). In that simulation the b case at tp4 was within twice the spread (%.1f us simulated against a trace mean of %.1f us). With the 15 helpers of a prefill window the simulated window is shorter (%.1f us). The agreement no longer holds.' % (l8, SIM[("b", "tp4")]["trace_mean"], SIM[("b", "tp4")]["length"])
    H.append('<p class="take">' + take + '</p>')
    H.append('<p class="take">The report names the join and the helpers\' arrival as the cause of the gap to the ideal speed-up [store-remedies-report.html sections 3.2 (figure caption) and 4.3]. The report\'s ideal at tp4 (9x) counts main plus the 8 helpers of the decode split. A tp4 prefill window has main plus 15 helpers (section 2.2), so its ideal is 16x. The measured factor of the shared save alone at tp4 is %.2fx (section 3.2), about half of that ideal. So the unattributed part at tp4 is larger than the report states. Its open items add the block loop as a third candidate and say the three are not separated [store-remedies-report.html section 6]. This page cannot split the gap further: save_k_helper has no trace span. So no per-thread timing of the window exists. <b>Insufficient data</b>: a TRACE_EVENT in save_k_helper (one span per claimed unit) would give the per-unit cost, the arrival times and the join wait directly.</p>' % ctx.FACT["shared_alone"][1])
    H.append('<p class="mono" id="selfcheck">Self-check: JavaScript did not run.</p>')

    H.append('<h2>7. Rules of the window, and the cases it does not cover</h2>')
    H.append('<ul><li><b>Who shares:</b> only the generated plugins pass n_workers > 1 to save_k. The handwritten llama plugin uses the default n_workers = 1. So it never shares [ingest/src/TronCpp.hs saveKv, model.hpp save_k default]. Sharing then needs three things: the VNNI K layout is on for the head size (TRON_K_VNNI and head size 128), the pass has more than 16 items, and n_workers is 2 to 128 [model.hpp k_store_shared, h/tron/kernels/k_vnni.hpp layout_on]. A decode pass (8 items) opens no window: main stores alone with the scatter, and the helpers\' save_k_helper call returns at once. k_store_shared returns false on their side too.</li>'
             '<li><b>Why the counts agree:</b> the emitter places save_k_helper at the same statement position in the helpers\' schedule as save_k in main\'s, for every KV-writing attention operation. So the W-th window main opens in a pass is the W-th window every helper enters [ingest/src/TronCpp.hs runHelperStatement].</li>'
             '<li><b>Why a helper never waits for a window main does not open:</b> both sides decide with the same k_store_shared, on the same batch and worker count.</li>'
             '<li><b>Why main cannot deadlock:</b> main waited for every K channel before save_k. So every helper has finished its rope stripe. Nothing blocks a helper between its rope kernel and save_k_helper. The watchdog aborts tron about 120 s into the join wait (counted from its first clock read, which follows the first 2^20 spins) if finished has still not reached n_workers - 1 [model.hpp:3024-3037].</li>'
             '<li><b>Two units in one block:</b> items of one block that are not consecutive in the item list (an item without KV work between them, or an item the scheduler moved to the end of its group) fall into two units. Two threads may then write the same 64-byte lines with masked stores on disjoint lanes. That is correct (no byte is written twice). In the cache model the two cores own those lines alternately.</li>'
             '<li><b>Why K and not V:</b> in the VNNI K plane a token owns 4 bytes of each line it touches. In the V plane two tokens share one 32-bit lane. Two threads storing the two tokens of a pair would write the same 4 bytes. save_v stays on main alone [report section 3.2].</li>'
             '<li><b>The unit tests</b>: the one-thread case checks the grouping (opened stays 0). The three-thread case runs two helper threads and main through one window and checks that every K row was written exactly once, that untouched rows kept their bytes, and the exact 9-unit table of section 4.2 [t/t_llama_unit.cpp:2765-2810]. The emitter test counts one save_k_helper call per KV-writing operation [ingest/test/LoopyTronSpec.hs].</li></ul>')

    H.append('<h2>8. Sources and checks</h2>')
    rows = [
        ("Window protocol: cut, reset, opened++ (release), claim loop on main, spin on finished (acquire), marks, credits, latch", "code", "h/tron/models/model.hpp:2992-3060 (save_k_impl), Note [Shared block save] :2732-2790 (head %s)" % HEAD),
        ("Helper side: ++helper_windows[worker_ix], spin on opened, claim loop, finished++ (release)", "code", "model.hpp:2948-2989 (save_k_helper)"),
        ("Unit cut rule: a unit ends where the KV flag, the page or the block changes. unit_start[n_units] = n_items", "code", "model.hpp:2816-2845 (k_store_cut_units)"),
        ("Run rule inside a unit: consecutive KV items of one block with distinct columns, at most 16. A run of one item takes the scatter path", "code", "model.hpp:2855-2945 (store_k_block), K_SCATTER_RUN_LEN_1 :2794"),
        ("Sharing condition: layout_on (TRON_K_VNNI build, head size 128), n_workers > 1, n_workers <= 128, items > 16. Handwritten plugins pass no n_workers (default 1)", "code", "model.hpp:2806-2814 (k_store_shared), h/tron/kernels/k_vnni.hpp:91-97 (layout_on), model.hpp:3062-3065 (save_k default)"),
        ("Watchdog: clock read every 2^20 spins, abort 120 s after the first clock read", "code", "model.hpp:2795-2801, 3024-3037"),
        ("Struct fields, the two alignas(cache_line_size) lines, and the struct comment on why", "code", "h/tron/models/common.hpp:1042-1068 (k_store_window_t)"),
        ("Struct byte offsets (0, 64, 68, 72, 76, 4176), size 4736 bytes = 74 lines", "run", "exec/shared-save-animation/window_layout.cpp (replica compiled with g++ 11), layout.json"),
        ("max_minibatch_size = 1024 in generated plugins. cache_line_size = hardware_destructive_interference_size or 64", "code", "ingest/src/TronCpp.hs:263, h/common/util.hpp:36-40"),
        ("Helper statement placement and the n_workers argument of save_k", "code", "ingest/src/TronCpp.hs:2325-2340 (runHelperStatement), :2400-2408 (saveKv)"),
        ("Rope stripe rule: item = init + actual_worker_ix, step n_actual_workers. Main skips helper kernels", "code", "ingest/src/TronCpp.hs:1977-1991 (Note [Main Thread Skips Helper Kernels]), :2002-2040 (staticStrategy)"),
        ("Every pool thread pins itself to one core of the application CPU set (one worker per core)", "code", "h/tron/threading.hpp:819-822, 859-862"),
        ("The unit test's 48-item pass and its 9 expected units", "test", "t/t_llama_unit.cpp:2572-2815, reproduced by exec/shared-save-animation/cut_units.py"),
        ("Save K per prefill layer: vnni0 858 / 863 us, a 346 / 353, b 175 / 110, ab 80 / 60 (tp2 / tp4). Conditions: qwen3-4b, 8 users, prompt 1024, binary of commit 9928cb2849 (16-item window blocks, two join counters)", "measured", "store-remedies-report.html section 4.3"),
        ("Trace means and pass-to-pass standard deviations of the same spans (for example b at tp4: 109.7 us, standard deviation 2.3 us over 8 prefill passes)", "measured", "exec/results/vnnik2-trace-20260915/analysis.json (kinds.prefill.save_k_us_per_layer, _sd)"),
        ("Thread placement: main + 7 helpers + 20 attention workers on 28 cores (tp2, every pass); at tp4 main + 15 + 40 in a prefill pass and main + 8 + 47 in a decode pass, on 56 cores. The report's section 1 words table gives the decode split for tp4, and so do its section 4.3 table (of 8) and reading (7.9x with 8 helpers, ideal 9x). Its section 2.2 figures label the prefill split", "measured (trace spans per window, section 2.2)", "lanes.json prefill and decode objects; store-remedies-report.html sections 1 and 2.2"),
        ("Helpers idle during Save K before the change. Their rope kernel ends at the start of Save K", "measured", "store-remedies-report.html section 2.2 (lanes of layer 10, prefill pass 3)"),
        ("Unit cost 5.4 / 5.5 / 13.4 / 13.5 us (est., upper bounds). The arrival, cut and marks durations and the claim order (mock)", "est. / mock", "this page's simulation (gen_page.py simulate(), mirrored in the script), not measured"),
        ("Where a unit's rows and lines are in the cache hierarchy at each step (sections 4.1, 5, 6.4, 6.5)", "model", "follows from the code and the cache rules stated in 6.4, not measured"),
        ("The gap between simulation and measurement is the join and the helpers' arrival (the block loop is a third candidate the report does not rule out)", "hypothesis (the report's explanation)", "store-remedies-report.html sections 3.2, 4.3 (assertion) and 6 (listed as not separated)"),
        ("No per-thread timing of the window exists", "code", "grep TRACE_EVENT model.hpp: only Save K (:3001) and Save V (:3090), none in save_k_helper or store_k_block"),
    ] + ctx.context_sources()
    H.append('<div class="scroll"><table><tr><th>Fact used on this page</th><th>Kind</th><th>Source</th></tr>' + "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(a), esc(b), esc(c)) for a, b, c in rows) + '</table></div>')
    H.append('<p class="take">Line numbers refer to the worktree at commit %s. The report\'s Figure 3.2 stays valid. This page adds the unit table, the counter values, the struct layout, the event order, the data each unit moves and the simulation against the measurement. Sections 2 and 3 (revision 5) add the stage of prefill, the data and the functions of one save, and the relation to the block store.</p>' % HEAD)
    H.append('</main><script>' + js + '</script></body></html>')
    page = "\n".join(H)
    bad = [(i, c) for i, c in enumerate(page) if ord(c) > 127]
    assert not bad, "non-ASCII at %r" % bad[:5]
    with open(OUT, "w") as f:
        f.write(page)
    print("wrote %s (%d bytes)" % (OUT, len(page)))
    for k, v in SIM.items():
        print("  sim %s %s: cost %s, length %.1f us, per thread %s, measured %d, gap %+.1f" % (k[0], k[1], v["cost"], v["length"], sorted(v["per_thread"].values()), v["measured"], v["measured"] - v["length"]))


if __name__ == "__main__":
    build()
