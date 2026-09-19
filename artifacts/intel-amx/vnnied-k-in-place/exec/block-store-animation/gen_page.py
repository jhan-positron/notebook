#!/usr/bin/env python3
"""Generate status/block-store-animation.html: the VNNI K block store played
step by step for one token block, with mock values, byte offsets, cache and
DRAM. The cell positions come from the compiled ground truth (gt.cpp, run by
build-gt.sh against the real h/tron/kernels/k_vnni.hpp). Pure ASCII output.
Revision 2 (2026-09-17): 48 review findings applied. Revision 3: 26 round-2
findings applied. Revision 4: 21 round-3 findings applied. The numbers and
offsets are unchanged from revision 1 in every revision (REV below).
"""
REV = 4
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "..", "..", "status", "block-store-animation.html")
HEAD = "04ffeedccb"  # jhan-amx-vnniK worktree head the code was read at
MONDAY_TIP = "5e45ae55ae"  # the VNNI binary measured on 2026-09-14 (per-token scatter)
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

GT21 = json.load(open(os.path.join(HERE, "token21.json")))
GTB = json.load(open(os.path.join(HERE, "block.json")))
assert len(GT21) == 128 and len(GTB["stores"]) == 64 and len(GTB["tokens"]) == 16

FOCUS_T = 21
C = 1          # token block of token 21
T_COL = 5      # its column inside the block
N_KV_HEADS = 8  # qwen3-4b (HF config num_key_value_heads)
HEAD_ROW_BYTES = 256
KV_ROW_BYTES = N_KV_HEADS * HEAD_ROW_BYTES  # 2048


def val(T, d):
    """Mock value of token T, dim d: token axis steps by 1.00, dim axis by 0.01."""
    return ((T - FOCUS_T) * 100 + 11 + d) / 100.0


def fv(x):
    return "%.2f" % x


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def panel_byte(s, c):
    return (s * 4 + c) * 1024


def line_byte(s, c, dp):
    return panel_byte(s, c) + dp * 64


# ---- consistency of the local formulas with the compiled ground truth
for rec in GT21:
    d = rec["d"]
    s, dp, j = d // 32, (d % 32) // 2, d % 2
    assert rec["s"] == s and rec["dp"] == dp and rec["j"] == j and rec["c"] == C and rec["t"] == T_COL
    assert rec["byte"] == line_byte(s, C, dp) + T_COL * 4 + j * 2, (rec, line_byte(s, C, dp))
    assert rec["line"] == rec["byte"] // 64
for st in GTB["stores"]:
    assert st["n"] == st["s"] * 16 + st["dp"] + 1
    assert st["byte"] == line_byte(st["s"], C, st["dp"]) and st["line"] == st["byte"] // 64

TINT = {0: "#cce3f0", 1: "#faeccc", 2: "#ccece3", 3: "#f5e4ed"}
DARK = {0: "#0072b2", 1: "#b87a00", 2: "#007a59", 3: "#a05080"}

CSS = """
:root { --ink:#0b0b0b; --muted:#52514e; --line:#e6e5e1; --bg:#fcfcfb; --panel:#f3f2ef; --accent:#2a78d6; --warn:#d03b3b;
  --s0:#cce3f0; --s1:#faeccc; --s2:#ccece3; --s3:#f5e4ed; --s0d:#0072b2; --s1d:#b87a00; --s2d:#007a59; --s3d:#a05080;
  --fetched:#e9e8e4; --cold:#ffffff; }
html { color-scheme: light; }
* { box-sizing: border-box; }
body { margin:0; padding-block:24px 48px; padding-inline:16px; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:1000px; margin:0 auto; }
h1 { font-size:26px; margin:0 0 6px; text-wrap:balance; } h2 { font-size:20px; margin:30px 0 8px; border-bottom:1px solid var(--line); padding-bottom:4px; } h3 { font-size:16px; margin:18px 0 6px; } h4 { font-size:14px; margin:14px 0 4px; color:var(--muted); }
p { max-width:72ch; }
.sub { color:var(--muted); margin-bottom:16px; }
.short { background:var(--panel); border-left:4px solid var(--accent); padding:10px 14px; margin:14px 0; }
.short p { max-width:none; }
table { border-collapse:collapse; margin:10px 0 14px; font-size:14px; } th, td { border:1px solid var(--line); padding:5px 8px; vertical-align:top; text-align:left; } th { background:var(--panel); }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; }
code, pre, .mono { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; } pre { background:var(--panel); border:1px solid var(--line); padding:10px 12px; overflow-x:auto; }
.fig { margin:6px 0 4px; border:1px solid var(--line); background:#fff; padding:8px; overflow-x:auto; }
.take { font-size:14px; color:var(--muted); margin:2px 0 12px; max-width:none; }
.answer { border:1px solid var(--line); border-left:4px solid var(--s0d); background:#fff; padding:8px 12px; margin:10px 0; }
.answer p { max-width:none; }
ul { margin:6px 0 10px 22px; } li { margin:3px 0; }
details { margin:8px 0; } summary { cursor:pointer; color:var(--accent); }
.scroll { overflow-x:auto; }
/* the 256-byte row: overview strip (fluid, fits the page above about 950 px) and detailed strip (scrolls) */
.ovstrip { display:flex; gap:6px; width:100%; min-width:900px; margin:0 0 10px; }
.ovstep { flex:1 1 0; min-width:0; display:flex; gap:1px; border:2px solid; border-radius:3px; padding:3px; }
.ovcell { flex:1 1 0; min-width:0; width:auto; height:26px; border:1px solid var(--line); background:#fff; font-size:8.5px; line-height:24px; text-align:center; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color:var(--muted); }
.ovcell.focuscell { outline:2px solid var(--ink); outline-offset:-2px; color:var(--ink); font-weight:700; }
.ovlbl { font-size:11px; color:var(--muted); margin:0 0 4px; }
.rowstrip { display:flex; gap:10px; width:max-content; }
.step { border:2px solid; border-radius:3px; padding:4px; }
.step .steplabel { font-size:12px; font-weight:600; margin:0 0 4px 2px; }
.pairs { display:flex; gap:2px; }
.pair { width:62px; border:1px solid var(--line); background:#fff; font-size:10.5px; line-height:1.25; text-align:center; padding:2px 0; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
.pair .dims { color:var(--muted); } .pair .vals { font-weight:600; font-size:11.5px; } .pair .bytes { color:var(--muted); }
.pair.focuscell { outline:2px solid var(--ink); outline-offset:-2px; }
/* animation grids */
.grid { border-collapse:collapse; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10.5px; line-height:1.2; }
.grid th, .grid td { border:1px solid var(--line); padding:1px 2px; text-align:center; min-width:46px; height:28px; }
.grid th { background:var(--panel); font-weight:600; font-size:10.5px; }
.grid td.lbl, .grid th.lbl { text-align:left; min-width:120px; background:var(--panel); font-size:10.5px; white-space:nowrap; }
.grid td.empty { color:#c8c7c2; }
.grid td.focus { outline:2px solid var(--ink); outline-offset:-2px; font-weight:700; }
.grid td.cur { box-shadow:inset 0 0 0 2px var(--accent); }
.grid td.tagged { font-size:9.5px; color:var(--muted); }
.grid tr.storedrow td { opacity:0.65; }
.grid tr.currow td { box-shadow:inset 0 0 0 2px var(--accent); }
/* cache strip */
.cache { display:grid; grid-template-columns:110px repeat(16, 1fr); gap:3px; align-items:stretch; min-width:900px; }
.cache .clbl { font-size:11px; color:var(--muted); align-self:center; white-space:nowrap; }
.cl { border:1px solid var(--line); border-radius:2px; min-height:34px; font-size:9.5px; line-height:1.15; text-align:center; padding:2px 1px; position:relative; background:var(--cold); font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
.cl.cold { border-style:dashed; color:var(--muted); }
.cl.fetched { background:var(--fetched); }
.cl.partial .bar { position:absolute; left:0; bottom:0; height:4px; background:var(--ink); }
.cl.cur { box-shadow:0 0 0 2px var(--accent); }
.cl .n { font-weight:700; }
/* DRAM plane summary */
.plane { display:grid; grid-template-columns:120px repeat(4, 1fr); gap:4px; min-width:640px; }
.plane .ph { font-size:11px; color:var(--muted); align-self:center; }
.pn { border:1px solid var(--line); border-radius:2px; padding:4px 6px; font-size:11px; line-height:1.3; background:#fff; min-height:46px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
.pn.other { color:#9a9891; background:#fafaf8; }
.pn.cur { box-shadow:0 0 0 2px var(--accent); }
/* controls */
.controls { display:flex; flex-wrap:wrap; gap:8px 12px; align-items:center; position:sticky; top:env(safe-area-inset-top, 0px); background:var(--bg); padding:8px 0; border-bottom:1px solid var(--line); z-index:5; }
.controls button { font:14px system-ui,sans-serif; padding:5px 10px; border:1px solid #b8b6b0; background:#fff; border-radius:4px; cursor:pointer; }
.controls button:hover { background:var(--panel); } .controls button:focus-visible { outline:2px solid var(--accent); outline-offset:1px; }
.controls label { font-size:14px; } .controls select { font:14px system-ui,sans-serif; }
.status { background:var(--panel); border:1px solid var(--line); padding:8px 12px; margin:10px 0; min-height:48px; font-size:14px; }
.status b { font-weight:700; }
.counters { display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; color:var(--muted); margin:4px 0 10px; }
.counters span b { color:var(--ink); font-variant-numeric:tabular-nums; }
.stage { margin:16px 0; }
.stage h3 { margin-bottom:4px; }
.stagehint { font-size:13px; color:var(--muted); margin:0 0 6px; max-width:none; }
ul.stagehint { margin:0 0 8px 22px; } ul.stagehint li { margin:2px 0; }
.legend { display:flex; flex-wrap:wrap; gap:10px 16px; font-size:12.5px; color:var(--muted); margin:8px 0; }
.legend .sw { display:inline-block; width:14px; height:12px; border:1px solid var(--line); vertical-align:-2px; margin-right:4px; background:#fff; }
.src { display:grid; grid-template-columns:150px repeat(4, 1fr); gap:3px; min-width:760px; }
.src .srclbl { font-size:11px; white-space:nowrap; align-self:center; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
.seg { border:1px solid var(--line); border-radius:2px; font-size:10px; line-height:1.2; text-align:center; padding:2px; background:#fff; color:var(--muted); font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
.seg.loaded { color:var(--ink); }
.seg.cur { box-shadow:0 0 0 2px var(--accent); color:var(--ink); }
.seg.focusrow { border-color:var(--ink); }
.orderfig { border-collapse:collapse; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10px; }
.orderfig td { border:1px solid var(--line); min-width:40px; height:30px; text-align:center; padding:1px; line-height:1.15; }
.orderfig td.lbl { text-align:left; min-width:250px; padding-left:6px; background:var(--panel); white-space:nowrap; font-size:10.5px; }
.orderfig td.other { color:#b5b3ad; background:#fafaf8; }
.orderfig td .t21 { display:block; font-size:9px; color:var(--muted); }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
"""


def words_table():
    rows = [
        ("tron, runtron", "tron is the inference program under test. runtron is its command-line tool."),
        ("qwen3-4b", "The model under test: Qwen/Qwen3-4B-Instruct-2507, with 8 KV heads, head size 128, 32 query heads and 36 layers (its Hugging Face config file)."),
        ("KV head, query head", "A token has 8 key/value vector sets per layer in qwen3-4b. Each set is one KV head. The 32 query heads share them, 4 query heads per KV head (grouped-query attention, GQA). The page follows KV head 0 of one layer."),
        ("pass, token item, prefill, decode", "A pass is one forward step of tron over the tokens it holds at that moment, layer by layer. A token item is one token of the pass. Prefill is the pass over the prompt tokens (in the report's runs 128 tokens of each of 8 users: 1024 items per pass). Decode is a pass that adds one generated token per user (8 items)."),
        ("tp2, tp4", "The model split over two or four FPGA cards (FPGA = field-programmable gate array, the accelerator card tron runs the model on). tp stands for tensor parallelism, the split of one model over several cards. The CPU attention and the K store run on one socket's application cores (28 at tp2, 56 at tp4). The prefill Save K numbers quoted here (858 and 346 us per layer, configurations without helper sharing) are the main thread's serial work. So they are nearly equal at tp2 and tp4: 858 against 863 us for the scatter (0.6% apart) and 346 against 353 us for the block store (2% apart) (report section 4.3). Report section 2.1 gives the same reading for the 2026-09-14 binary: 859 against 862 us. The decode numbers differ more: 444 ns per K row at tp2 and 540 ns at tp4, 22% apart (report section 2.3)."),
        ("main thread, main helpers, worker", "The generated qwen plugin runs the forward pass on one main thread. A fixed set of main helpers runs the per-token kernels (norms, the normalisation layers, and rope) in stripes: each helper handles its own subset of the pass's token rows. The rows of one pass are therefore written by several cores. A worker here means one of these threads, main included. The other threads of the pool are attention workers and take no part in the store."),
        ("rope", "Rotary position embedding: the position-dependent rotation tron applies to each K row (and Q row) before the store. The main helpers run it, each on its own subset of the token rows (the stripes defined above). So the K rows reach the K buffer from several cores just before the store reads them. The store runs on the main thread alone, or on main and the helpers when the save is shared (section 5)."),
        ("Save K", "The Perfetto trace span (Perfetto is the trace recorder built into tron) of save_k_impl, the function that stores the K rows of a pass into the KV cache, once per layer per pass."),
        ("KV cache, page, plane", "The KV cache keeps the K and V vectors of past tokens, per layer. A page holds 64 tokens. The K storage of one KV head for one page is one plane of 16 KiB (64 tokens x 128 values x 2 bytes)."),
        ("K buffer (ks)", "The pass's K rows after rope, one row per token item, read by the store. A row holds every KV head of the token: 8 heads x 128 bf16 = 2048 bytes for qwen3-4b. KV head h is bytes 256h .. 256h+255 of the row."),
        ("bf16", "The 16-bit brain floating-point format: 8 bits of precision (about 2.4 decimal digits). Every K value is 2 bytes."),
        ("dim, dim pair, dword", "A dim is one of the 128 positions of a K vector. A dim pair is dims 2k and 2k+1, 4 bytes together, one dword (double word, a 4-byte unit). The AMX multiply consumes K in pairs. So the pair is the unit that moves. A K row has 64 dim pairs."),
        ("cell", "One dim pair of one token as drawn in the figures: 4 bytes. In section 2 a cell is 4 bytes of the K row. In sections 3 and 4 it is one token's 4 bytes inside one 64-byte line, at line bytes 4t to 4t+3 for column t (bytes 20-23 for token 21, column t = 5)."),
        ("K row", "One token's K vector for one KV head: 128 bf16 = 256 bytes, contiguous in the K buffer."),
        ("dim step", "16 consecutive dim pairs = 32 dims = 64 bytes of a K row. A row has 4 dim steps, s0 .. s3, at row bytes 0-63, 64-127, 128-191, 192-255."),
        ("token block", "16 consecutive positions of a page: blocks c0 .. c3. Token i of the page is column t = i mod 16 of block c = i div 16. Token 21 is column 5 of block c1."),
        ("panel", "The storage of one dim step of one token block: 16 lines (one per dim pair) x 16 columns (one per token) x 4 bytes = 1 KiB. Panel (s, c) starts at plane byte (4s + c) x 1024 and has the panel number p = 4s + c. A panel is exactly one AMX tile (see the AMX row below)."),
        ("line, panel line dp, plane line L", "A line is one 64-byte cache line. Inside a panel, panel line dp (0-15) is the row that holds dim pair dp of the block's 16 tokens. Inside the plane, plane line L (0-255) is plane bytes 64L .. 64L+63, with L = 16p + dp for panel p. The cache strip of section 4 labels plane lines L16 .. L223."),
        ("full-line store, partial-line write", "A store that writes all 64 bytes of a line at once, against a write of 4 bytes into a line."),
        ("register, lane", "An AVX-512 register holds 64 bytes = 16 lanes of 4 bytes = 16 dim pairs. r_t is the register loaded from token 16+t. q_dp is the register that holds dim pair dp of all 16 tokens after the transpose."),
        ("transpose", "The in-register 16 x 16 transpose of 32-bit lanes: 64 shuffle instructions in 4 stages, over the 16 loaded registers and 16 temporaries. Afterwards lane t of q_dp is lane dp of r_t."),
        ("scatter", "One AVX-512 instruction that writes the 16 lanes of a register to 16 separate addresses, 4 bytes each. The per-token store uses 4 scatters per K row."),
        ("the 2026-09-14 binary", "The VNNI-K build at commit %s, measured on Monday 2026-09-14 (the binary the report labels vnni, see status/Monday-morning-report.html). It stored every K row with the per-token scatter. The report calls it Monday's binary. Decode still uses that store today." % MONDAY_TIP),
        ("block store", "k_vnni::store_block: for a run of 2 to 16 consecutive items of the pass whose tokens fall into one 16-token block, each in a different column of that block (a different token position in the page, the code's offset_in_page). In a prefill pass these are usually consecutive tokens of one user. Items without KV work inside the run are skipped, and a gap in the block stays unwritten. Per dim step: one load per present token, one transpose, 16 full-line stores (masked to the present tokens when the block is partial)."),
        ("L1D, L2, L3, DRAM", "The core's first-level data cache (48 KiB, 12-way: each memory address can be held in one of 12 places in the cache), its second-level cache (2 MiB), the socket's shared third-level cache (432 MiB) and main memory, on delphi-3bda (Xeon 6 6962P). All have 64-byte lines."),
        ("line fetch, write-back, eviction, cold line", "A line fetch brings a 64-byte line from a farther level into the core's cache. A dirty line (written in cache) returns to memory by write-back when the cache evicts it. A cold line is one the core does not hold in L1D or L2. In this page's cache model a cold line sits only in DRAM (section 4.3)."),
        ("read for ownership", "The read of a line's old 64 bytes that a core performs before it can modify a line it does not hold. Whether the core skips it for a full-line store is not measured here."),
        ("AMX, AVX-512, VNNI layout", "AMX is the Intel matrix (tile) instruction set. A tile is one AMX register of 16 rows x 64 bytes = 1 KiB. AVX-512 is the 512-bit vector set. The VNNI layout is the pair-interleaved K layout the AMX tile multiply reads as its right operand. The plane holds it."),
        ("poison", "A marker bit pattern (0xA5A5 per bf16 value) pre-filled into storage that no store may change. The tests check that it survives wherever nothing should be written."),
        ("mock values", "The values in this page are made up so that the reader can trace them: token T, dim d holds (T - 21) + 0.11 + 0.01 d. So token 21 holds 0.11, 0.12, ... 1.38. Along a line (one dim pair, 16 tokens) the value steps by 1.00 per token."),
    ]
    return "<table><tr><th>Term</th><th>Meaning</th></tr>" + "".join(
        "<tr><td>%s</td><td>%s</td></tr>" % (esc(t), esc(m)) for t, m in rows) + "</table>"


def overview_strip():
    """Section 2.1, top: the whole 256-byte row in one fluid strip of 64 cells."""
    h = ['<p class="ovlbl">The whole 256-byte row in one strip: 64 dim pairs, 4 dim steps side by side. Each cell shows its pair number (0-63). Hover a cell for its dims and values. The outlined cell is pair 0.</p><div class="scroll"><div class="ovstrip">']
    for s in range(4):
        h.append('<div class="ovstep" style="border-color:%s;background:%s">' % (DARK[s], TINT[s]))
        for dp in range(16):
            d0 = 32 * s + 2 * dp
            k = 16 * s + dp
            h.append('<div class="ovcell%s" title="pair %d: dims %d,%d = (%s, %s), row bytes %d-%d">%d</div>' % (
                " focuscell" if k == 0 else "", k, d0, d0 + 1, fv(val(FOCUS_T, d0)), fv(val(FOCUS_T, d0 + 1)), 4 * k, 4 * k + 3, k))
        h.append('</div>')
    h.append('</div></div>')
    return "".join(h)


def row_strip():
    """Section 2.1, bottom: token 21's 256-byte K row as ONE row of 64 pair cells with values."""
    h = ['<div class="scroll"><div class="rowstrip">']
    for s in range(4):
        h.append('<div class="step" style="border-color:%s;background:%s">' % (DARK[s], TINT[s]))
        h.append('<div class="steplabel">dim step s%d = row bytes %d-%d (dims %d-%d)</div><div class="pairs">' % (s, 64 * s, 64 * s + 63, 32 * s, 32 * s + 31))
        for dp in range(16):
            d0 = 32 * s + 2 * dp
            b0 = 64 * s + 4 * dp
            cls = "pair" + (" focuscell" if d0 == 0 else "")
            h.append('<div class="%s" title="token 21, dims %d,%d, row bytes %d-%d, written to plane bytes %d-%d"><div class="dims">d%d d%d</div><div class="vals">%s<br>%s</div><div class="bytes">B %d-%d</div></div>' % (
                cls, d0, d0 + 1, b0, b0 + 3, line_byte(s, C, dp) + T_COL * 4, line_byte(s, C, dp) + T_COL * 4 + 3,
                d0, d0 + 1, fv(val(FOCUS_T, d0)), fv(val(FOCUS_T, d0 + 1)), b0, b0 + 3))
        h.append('</div></div>')
    h.append('</div></div>')
    return "".join(h)


def pair0_bytes_table():
    r0, r1 = GT21[0], GT21[1]
    def bytes_le(hexs):
        v = int(hexs, 16)
        return "%02X %02X" % (v & 0xFF, v >> 8)
    return ('<table><tr><th>dim</th><th>mock value</th><th>stored bf16 (bits)</th><th>stored value</th><th>bytes in memory (low address first)</th><th>row bytes (K buffer)</th><th>plane bytes (KV cache)</th></tr>'
            '<tr><td>0</td><td class="num">0.11</td><td class="num">%s</td><td class="num">%.6f</td><td class="num">%s</td><td class="num">0-1</td><td class="num">%d-%d</td></tr>'
            '<tr><td>1</td><td class="num">0.12</td><td class="num">%s</td><td class="num">%.6f</td><td class="num">%s</td><td class="num">2-3</td><td class="num">%d-%d</td></tr></table>'
            % (r0["hex"], r0["val"], bytes_le(r0["hex"]), r0["byte"], r0["byte"] + 1,
               r1["hex"], r1["val"], bytes_le(r1["hex"]), r1["byte"], r1["byte"] + 1))


def tokens_table():
    h = ['<table><tr><th>token of the page</th><th>block, column</th><th class="num">dim 0</th><th class="num">dim 1</th><th class="num">...</th><th class="num">dim 126</th><th class="num">dim 127</th><th>K buffer row (2048 bytes), KV head 0 = row bytes</th></tr>']
    for T in range(16, 32):
        style = ' style="font-weight:700"' if T == FOCUS_T else ""
        h.append('<tr%s><td>token %d</td><td>c1, t = %d</td><td class="num">%s</td><td class="num">%s</td><td class="num">...</td><td class="num">%s</td><td class="num">%s</td><td>row of token %d, bytes 0-255</td></tr>' % (
            style, T, T - 16, fv(val(T, 0)), fv(val(T, 1)), fv(val(T, 126)), fv(val(T, 127)), T))
    h.append("</table>")
    return "".join(h)


def plane_grid_static():
    """Section 3.1: the 16 panels with byte offsets."""
    h = ['<div class="scroll"><div class="plane">']
    h.append('<div class="ph"></div>')
    for c in range(4):
        h.append('<div class="ph"><b>block c%d</b><br>tokens %d-%d</div>' % (c, 16 * c, 16 * c + 15))
    for s in range(4):
        h.append('<div class="ph"><b>dim step s%d</b><br>dims %d-%d</div>' % (s, 32 * s, 32 * s + 31))
        for c in range(4):
            b = panel_byte(s, c)
            cls = "pn" if c == C else "pn other"
            extra = "<br>token 21: column 5 = +20..+23 in every line" if c == C else ""
            h.append('<div class="%s" style="%s">panel (s%d, c%d), p = %d<br>bytes %d-%d<br>plane lines %d-%d%s</div>' % (
                cls, ("background:%s" % TINT[s]) if c == C else "", s, c, s * 4 + c, b, b + 1023, b // 64, b // 64 + 15, extra))
    h.append('</div></div>')
    return "".join(h)


def order_fig():
    """Section 3.2: all 256 lines of the plane in address order, with the 64 stores numbered."""
    h = ['<div class="scroll"><table class="orderfig">']
    h.append('<tr><td class="lbl">panel p = 4s + c (address order)</td>' + "".join('<td class="lbl" style="min-width:40px;text-align:center">dp %d</td>' % dp for dp in range(16)) + '</tr>')
    for p in range(16):
        s, c = p // 4, p % 4
        b = p * 1024
        h.append('<tr><td class="lbl">p=%d: panel (s%d, c%d), bytes %d-%d, plane lines %d-%d</td>' % (p, s, c, b, b + 1023, 16 * p, 16 * p + 15))
        for dp in range(16):
            if c == C:
                n = s * 16 + dp + 1
                d0 = 32 * s + 2 * dp
                h.append('<td style="background:%s" title="store %d: plane line %d, plane bytes %d-%d, dims %d,%d of tokens 16-31"><b>#%d</b><span class="t21">t21 %s</span></td>' % (
                    TINT[s], n, 16 * p + dp, b + 64 * dp, b + 64 * dp + 63, d0, d0 + 1, n, fv(val(FOCUS_T, d0))))
            else:
                h.append('<td class="other">-</td>')
        h.append('</tr>')
    h.append('</table></div>')
    return "".join(h)


def token21_table():
    h = ['<table><tr><th class="num">store #</th><th>panel</th><th class="num">panel line dp</th><th class="num">plane line L</th><th class="num">line bytes (64)</th><th class="num">token 21 cell bytes (4)</th><th class="num">dims</th><th class="num">values</th><th class="num">bf16 bits</th></tr>']
    for s in range(4):
        for dp in range(16):
            d0 = 32 * s + 2 * dp
            r0, r1 = GT21[d0], GT21[d0 + 1]
            lb = line_byte(s, C, dp)
            h.append('<tr><td class="num">%d</td><td>(s%d, c1)</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d-%d</td><td class="num">%d-%d</td><td class="num">%d, %d</td><td class="num">%s, %s</td><td class="num">%s %s</td></tr>' % (
                s * 16 + dp + 1, s, dp, lb // 64, lb, lb + 63, r0["byte"], r0["byte"] + 3, d0, d0 + 1, fv(val(FOCUS_T, d0)), fv(val(FOCUS_T, d0 + 1)), r0["hex"], r1["hex"]))
    h.append('</table>')
    return "".join(h)


def sources_table():
    rows = [
        ("Plane index: plane[(((4s + c) * 16 + dp) * 16 + t) * 2 + j] = K[16c + t][32s + 2dp + j]. Panel (s, c) = 1 KiB, one AMX tile", "code", "h/tron/kernels/k_vnni.hpp:22-30 and index() at :101-107 (head %s)" % HEAD),
        ("Block store order: for s = 0..3: one load per present token (t = 0..15, 64 bytes at row + 64s, an absent token's register set to zero without a load), one transpose, 16 stores (dp = 0..15) to panel (s, c) panel line dp. A partial block uses masked stores", "code", "k_vnni.hpp:194-216 (store_block)"),
        ("Transpose: 4 stages of 2-register shuffles, 64 shuffles, lane t of output dp = lane dp of input t", "code", "k_vnni.hpp:149-179 (transpose_16x16_epi32)"),
        ("Per-token scatter: 4 scatters of 16 dwords, one per dim step, into the token's column", "code", "k_vnni.hpp:135-146 (scatter_row), pair_row_offsets :126-132"),
        ("Which path: store_k_block goes through its range of the pass's item list, one item at a time in order, and collects a run: consecutive items in the same 16-token block of the same page, each in a different column of the block. Items without KV work are skipped and do not end the run. A run ends at an item on another page, in another block, in a column already taken (the code comment says the same offset twice), after 16 items, or at the end of the range. A run of one item uses set_k_row (the page-level wrapper of scatter_row). A run of 2 to 16 items uses set_k_block (the page-level wrapper that calls k_vnni::store_block, kv_cache.hpp:1723-1729)", "code", "h/tron/models/model.hpp:2855-2945 (store_k_block), K_SCATTER_RUN_LEN_1 at :2794"),
        ("Source rows: the K buffer row of the token item, KV head h at element offset 128h (256h bytes)", "code", "model.hpp:2861-2864 (row_of)"),
        ("Sharing of the store with the main helpers is on when the pass has more than 16 items and the plugin runs with 2 to 128 workers. One worker (the handwritten plugins, the unit tests except one shared-save case) never shares", "code", "model.hpp:2806-2814 (k_store_shared), Note [Shared block save] at :2732-2790, common.hpp MAX_SHARED_WORKERS_128"),
        ("Block store and scatter leave the plane bit-identical. Absent tokens keep their poison marker", "test", "t/t_k_vnni_layout.cpp:150-206 (38 masks x 4 blocks)"),
        ("This page's cell positions: the real store_block run on the mock rows of block c1 matched index() for all 16 x 128 values and matched scatter_row byte for byte (memcmp, the C byte-compare function, returned 0)", "run", "exec/block-store-animation/gt.cpp via build-gt.sh, outputs token21.json and block.json (2026-09-17)"),
        ("The store order #1 .. #64 is the program order of the two loops in store_block (dim step s outer, panel line dp inner). A final-state check cannot observe order", "code", "k_vnni.hpp:198-215"),
        ("Cache geometry: L1D 49152 bytes 12-way, L2 2097152 bytes, L3 452984832 bytes, 64-byte lines", "measured", "getconf (the POSIX system-configuration query) on delphi-3bda, 2026-09-17 01:05 UTC"),
        ("qwen3-4b: 8 KV heads, head size 128, 32 query heads, 36 layers", "config", "Hugging Face config.json of Qwen/Qwen3-4B-Instruct-2507 (num_key_value_heads, head_dim), cached on delphi-3bda"),
        ("Save K per prefill layer at tp2: 858 us with the per-token scatter (the report's configuration vnni0: the commit-9928cb2849 binary with both remedy switches off) -> 346 us with the block store alone (configuration a: TRON_K_VNNI_BLOCK on, TRON_K_VNNI_STRIPE off), 353 us at tp4. Conditions: qwen3-4b, 8 users, prompt 1024 (1024 items per pass), Perfetto trace on delphi-3bda, one binary of commit 9928cb2849 for both configurations", "measured", "store-remedies-report.html section 4.3"),
        ("L1-resident microbenchmark: 681 -> 169 cycles per 16 tokens (16 scatters against one block store), instruction cost only", "measured", "store-remedies-report.html section 3.1.1 (Checks)"),
        ("Decode store: 444 ns per K row at tp2 and 540 ns at tp4, against 105 ns in prefill", "measured", "store-remedies-report.html section 2.3"),
        ("Decode store cost: the 64 lines of a token's column are cold in decode. Every 4-byte write then waits for a line fetch", "hypothesis (the report's explanation, no cache-miss counter was recorded)", "store-remedies-report.html section 2.3"),
        ("The runtime switches TRON_K_VNNI_BLOCK and TRON_K_VNNI_STRIPE of the report's commit 9928cb2849 no longer exist. The block store is the only path for runs of 2 or more items", "code", "commit ab94854999 on jhan-amx-vnniK"),
    ]
    return "<table><tr><th>Fact used on this page</th><th>Kind</th><th>Source</th></tr>" + "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(a), esc(b), esc(c)) for a, b, c in rows) + "</table>"


# ---- the animation script (plain JavaScript, no library)
JS = r"""
(function () {
  'use strict';
  var GT21 = __GT21__;
  var STORES = __STORES__;
  var FOCUS_T = 21, C = 1, T_COL = 5;
  var TINT = ['#cce3f0', '#faeccc', '#ccece3', '#f5e4ed'];
  var DARK = ['#0072b2', '#b87a00', '#007a59', '#a05080'];

  function val(T, d) { return ((T - FOCUS_T) * 100 + 11 + d) / 100; }
  function fv(x) { return x.toFixed(2); }
  function panelByte(s, c) { return (s * 4 + c) * 1024; }
  function lineByte(s, c, dp) { return panelByte(s, c) + dp * 64; }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  // ---- self-check of the page's formulas against the compiled ground truth
  function selfCheck() {
    var okCells = 0, okStores = 0, i, r, d, s, dp, j, st;
    for (i = 0; i < GT21.length; i++) {
      r = GT21[i]; d = r.d; s = Math.floor(d / 32); dp = Math.floor((d % 32) / 2); j = d % 2;
      if (r.byte === lineByte(s, C, dp) + T_COL * 4 + j * 2 && r.line === Math.floor(r.byte / 64)) okCells++;
    }
    for (i = 0; i < STORES.length; i++) {
      st = STORES[i];
      if (st.byte === lineByte(st.s, C, st.dp) && st.n === st.s * 16 + st.dp + 1) okStores++;
    }
    var el = document.getElementById('selfcheck');
    if (el) {
      el.textContent = 'Self-check in this browser: ' + okCells + ' of ' + GT21.length + ' token-21 cells match the compiled ground truth, and ' + okStores + ' of ' + STORES.length +
        ' store offsets match the source-loop order written in block.json' + ((okCells === GT21.length && okStores === STORES.length) ? '.' : ' -- MISMATCH, do not trust the drawn offsets.');
    }
  }

  // ---- step lists
  function blockSteps() {
    var steps = [], s, t, dp;
    for (s = 0; s < 4; s++) {
      for (t = 0; t < 16; t++) steps.push({ type: 'load', s: s, t: t });
      steps.push({ type: 'transpose', s: s });
      for (dp = 0; dp < 16; dp++) steps.push({ type: 'store', s: s, dp: dp, n: s * 16 + dp + 1 });
    }
    return steps;
  }
  function scatterSteps() {
    var steps = [], t, s;
    for (t = 0; t < 16; t++) {
      for (s = 0; s < 4; s++) {
        steps.push({ type: 'sload', s: s, t: t });
        steps.push({ type: 'scatter', s: s, t: t, n: t * 4 + s + 1 });
      }
    }
    return steps;
  }

  // ---- state after k steps
  function derive(mode, steps, k) {
    var st = {
      loaded: [], lines: [], regS: -1, regLoaded: 0, transposed: false, storedDp: 0, sreg: null,
      loads: 0, transposes: 0, fullStores: 0, partialWrites: 0, fetches: 0, last: null, curPanelS: 0
    };
    var s, dp, i, step, ln;
    for (s = 0; s < 4; s++) {
      st.loaded.push([]); st.lines.push([]);
      for (i = 0; i < 16; i++) { st.loaded[s].push(false); st.lines[s].push({ full: false, cells: 0, storeNo: 0, fetched: false, writes: 0 }); }
    }
    for (i = 0; i < k; i++) {
      step = steps[i]; st.last = step;
      if (step.type === 'load') {
        if (st.regS !== step.s) { st.regS = step.s; st.regLoaded = 0; st.transposed = false; st.storedDp = 0; }
        st.loaded[step.s][step.t] = true; st.regLoaded = step.t + 1; st.loads++; st.curPanelS = step.s;
      } else if (step.type === 'transpose') {
        st.transposed = true; st.transposes++;
      } else if (step.type === 'store') {
        ln = st.lines[step.s][step.dp];
        ln.full = true; ln.cells = 16; ln.storeNo = step.n; ln.writes = 1;
        if (!ln.fetched) { ln.fetched = true; st.fetches++; }
        st.fullStores++; st.storedDp = step.dp + 1; st.curPanelS = step.s;
      } else if (step.type === 'sload') {
        st.loaded[step.s][step.t] = true; st.loads++; st.sreg = { s: step.s, t: step.t, scattered: false }; st.curPanelS = step.s;
      } else if (step.type === 'scatter') {
        for (dp = 0; dp < 16; dp++) {
          ln = st.lines[step.s][dp];
          ln.cells |= (1 << step.t); ln.writes++;
          if (!ln.fetched) { ln.fetched = true; st.fetches++; }
        }
        st.partialWrites += 16; st.sreg = { s: step.s, t: step.t, scattered: true }; st.curPanelS = step.s;
      }
    }
    return st;
  }

  // ---- renderers
  function renderSource(mode, st, step) {
    var h = ['<div class="scroll"><div class="src">'];
    var t, s, T, cls, cur;
    h.push('<div class="srclbl"><b>token (block c1 column)</b></div>');
    for (s = 0; s < 4; s++) h.push('<div class="srclbl" style="text-align:center;color:' + DARK[s] + '">dim step s' + s + '<br>row bytes ' + (64 * s) + '-' + (64 * s + 63) + '</div>');
    for (t = 0; t < 16; t++) {
      T = 16 + t;
      h.push('<div class="srclbl"' + (T === FOCUS_T ? ' style="font-weight:700"' : '') + '>token ' + T + ' (t = ' + t + ')' + (T === FOCUS_T ? ' &lt;- the mock token' : '') + '</div>');
      for (s = 0; s < 4; s++) {
        cur = step && (step.type === 'load' || step.type === 'sload') && step.s === s && step.t === t;
        cls = 'seg' + (st.loaded[s][t] ? ' loaded' : '') + (cur ? ' cur' : '') + (T === FOCUS_T ? ' focusrow' : '');
        h.push('<div class="' + cls + '" style="' + (st.loaded[s][t] ? 'background:' + TINT[s] : '') + '" title="token ' + T + ', dims ' + (32 * s) + '-' + (32 * s + 31) + ', values ' + fv(val(T, 32 * s)) + ' .. ' + fv(val(T, 32 * s + 31)) + '">' +
          fv(val(T, 32 * s)) + ' .. ' + fv(val(T, 32 * s + 31)) + '<br>' + (st.loaded[s][t] ? (mode === 'block' ? '-> r' + t : '-> reg') : 'not read yet') + '</div>');
      }
    }
    h.push('</div></div>');
    document.getElementById('stage-src').innerHTML = h.join('');
  }

  function cellHtml(T, d0, classes, title) {
    return '<td class="' + classes + '" title="' + esc(title) + '">' + fv(val(T, d0)) + '<br>' + fv(val(T, d0 + 1)) + '</td>';
  }

  function renderRegs(mode, st, step) {
    var h = [], s, t, dp, T, d0, cls, rowCls, hint;
    if (mode === 'block') {
      s = st.regS < 0 ? 0 : st.regS;
      if (st.regS < 0) {
        hint = 'Nothing loaded yet. The first dim step (s0) starts with token 16.';
      } else if (!st.transposed) {
        hint = 'Dim step s' + s + ': ' + st.regLoaded + ' of 16 registers loaded. Register r_t = token 16 + t. Its lanes are the token\'s 16 dim pairs of this step (dims ' + (32 * s) + '-' + (32 * s + 31) + '). Token 21 is register r5.';
      } else {
        hint = 'Dim step s' + s + ' after the transpose: register q_dp = dim pair dp (dims ' + (32 * s) + '+2dp, +1) of tokens 16-31. Lane t = token 16 + t. Token 21 is lane 5 of every register. ' + st.storedDp + ' of 16 registers stored.';
      }
      h.push('<p class="stagehint">' + esc(hint) + '</p><div class="scroll"><table class="grid"><tr><th class="lbl">' + (st.transposed ? 'q_dp (dims)' : 'r_t (token)') + '</th>');
      for (t = 0; t < 16; t++) h.push('<th>lane ' + t + (st.transposed ? '<br>tok ' + (16 + t) : '<br>dp ' + t) + '</th>');
      h.push('<th class="lbl">state</th></tr>');
      for (var r = 0; r < 16; r++) {
        if (!st.transposed) {
          T = 16 + r;
          rowCls = (step && step.type === 'load' && step.t === r && st.regS >= 0) ? ' class="currow"' : '';
          h.push('<tr' + rowCls + '><td class="lbl">r' + r + ' = token ' + T + (T === FOCUS_T ? ' (mock)' : '') + '</td>');
          for (dp = 0; dp < 16; dp++) {
            d0 = 32 * s + 2 * dp;
            if (r < st.regLoaded) {
              cls = (T === FOCUS_T ? 'focus' : '');
              h.push(cellHtml(T, d0, cls, 'r' + r + ' lane ' + dp + ': token ' + T + ' dims ' + d0 + ',' + (d0 + 1) + ' (row bytes ' + (64 * s + 4 * dp) + '-' + (64 * s + 4 * dp + 3) + ')'));
            } else h.push('<td class="empty">-</td>');
          }
          h.push('<td class="lbl">' + (r < st.regLoaded ? 'loaded (64 B)' : 'empty') + '</td></tr>');
        } else {
          dp = r; d0 = 32 * s + 2 * dp;
          var stored = dp < st.storedDp;
          var isCur = step && step.type === 'store' && step.dp === dp;
          rowCls = ' class="' + (isCur ? 'currow' : (stored ? 'storedrow' : '')) + '"';
          h.push('<tr' + rowCls + '><td class="lbl">q' + dp + ' = dims ' + d0 + ',' + (d0 + 1) + '</td>');
          for (t = 0; t < 16; t++) {
            T = 16 + t;
            h.push(cellHtml(T, d0, (T === FOCUS_T ? 'focus' : ''), 'q' + dp + ' lane ' + t + ': token ' + T + ' dims ' + d0 + ',' + (d0 + 1) + ' -> plane bytes ' + (lineByte(s, C, dp) + 4 * t) + '-' + (lineByte(s, C, dp) + 4 * t + 3)));
          }
          h.push('<td class="lbl">' + (stored ? 'stored #' + (s * 16 + dp + 1) + ' -> plane line L' + (lineByte(s, C, dp) / 64) : 'waiting') + '</td></tr>');
        }
      }
      h.push('</table></div>');
    } else {
      if (!st.sreg) {
        hint = 'Nothing loaded yet. The per-token path handles token 16 first: its 4 dim steps, one register at a time.';
        h.push('<p class="stagehint">' + esc(hint) + '</p>');
      } else {
        s = st.sreg.s; t = st.sreg.t; T = 16 + t;
        hint = 'One register: token ' + T + ', dim step s' + s + ' (dims ' + (32 * s) + '-' + (32 * s + 31) + '), 16 lanes = 16 dim pairs. ' + (st.sreg.scattered ? 'Scattered: lane dp went to panel (s' + s + ', c1) panel line dp, column ' + t + ' (4 bytes each).' : 'Loaded, not yet scattered.');
        h.push('<p class="stagehint">' + esc(hint) + '</p><div class="scroll"><table class="grid"><tr><th class="lbl">register</th>');
        for (dp = 0; dp < 16; dp++) h.push('<th>lane ' + dp + '<br>dp ' + dp + '</th>');
        h.push('</tr><tr><td class="lbl">token ' + T + ', s' + s + '</td>');
        for (dp = 0; dp < 16; dp++) {
          d0 = 32 * s + 2 * dp;
          h.push(cellHtml(T, d0, (T === FOCUS_T ? 'focus' : ''), 'token ' + T + ' dims ' + d0 + ',' + (d0 + 1) + ' -> plane bytes ' + (lineByte(s, C, dp) + 4 * t) + '-' + (lineByte(s, C, dp) + 4 * t + 3)));
        }
        h.push('</tr><tr><td class="lbl">goes to</td>');
        for (dp = 0; dp < 16; dp++) h.push('<td class="tagged">L' + (lineByte(s, C, dp) / 64) + '<br>+' + (4 * t) + '..' + (4 * t + 3) + '</td>');
        h.push('</tr></table></div>');
      }
    }
    document.getElementById('stage-regs').innerHTML = h.join('');
  }

  function popcount16(x) { var n = 0; while (x) { n += x & 1; x >>= 1; } return n; }

  function renderCache(mode, st, step) {
    var h = ['<div class="scroll"><div class="cache">'], s, dp, ln, cls, inner, cur, lb;
    h.push('<div class="clbl"><b>L1D, 64 lines of block c1</b></div>');
    for (dp = 0; dp < 16; dp++) h.push('<div class="clbl" style="text-align:center">dp ' + dp + '</div>');
    for (s = 0; s < 4; s++) {
      h.push('<div class="clbl" style="color:' + DARK[s] + '">panel (s' + s + ', c1)<br>L' + (panelByte(s, C) / 64) + '-L' + (panelByte(s, C) / 64 + 15) + '</div>');
      for (dp = 0; dp < 16; dp++) {
        ln = st.lines[s][dp]; lb = lineByte(s, C, dp);
        cur = step && ((step.type === 'store' && step.s === s && step.dp === dp) || (step.type === 'scatter' && step.s === s));
        if (!ln.fetched) { cls = 'cl cold'; inner = 'L' + (lb / 64) + '<br>cold<br>(DRAM)'; }
        else if (ln.full) { cls = 'cl full'; inner = 'L' + (lb / 64) + '<br><span class="n">#' + ln.storeNo + '</span> whole<br>dirty'; }
        else { var nc = popcount16(ln.cells); cls = 'cl partial'; inner = 'L' + (lb / 64) + '<br>' + nc + '/16 cells<br>' + ln.writes + ' writes<div class="bar" style="width:' + (nc * 100 / 16) + '%"></div>'; }
        h.push('<div class="' + cls + (cur ? ' cur' : '') + '" style="' + (ln.fetched && ln.full ? 'background:' + TINT[s] : (ln.fetched ? 'background:' + TINT[s] + '80' : '')) + '" title="plane line L' + (lb / 64) + ' = plane bytes ' + lb + '-' + (lb + 63) + '. Token 21 cell at ' + (lb + 20) + '-' + (lb + 23) + '">' + inner + '</div>');
      }
    }
    h.push('</div></div>');
    document.getElementById('stage-cache').innerHTML = h.join('');
  }

  function renderPanelDetail(mode, st, step) {
    var s = st.curPanelS, h = [], dp, t, T, d0, ln, lb, cls, written;
    h.push('<p class="stagehint">Panel (s' + s + ', c1), p = ' + (4 * s + C) + ', as it fills: plane bytes ' + panelByte(s, C) + '-' + (panelByte(s, C) + 1023) + ', plane lines L' + (panelByte(s, C) / 64) + '-L' + (panelByte(s, C) / 64 + 15) + '. A cell shows its two values once written. Column t = 5 (outlined) is token 21.</p>');
    h.push('<div class="scroll"><table class="grid"><tr><th class="lbl">panel line dp (dims) / plane line L / bytes</th>');
    for (t = 0; t < 16; t++) h.push('<th>t=' + t + '<br>tok ' + (16 + t) + '</th>');
    h.push('<th class="lbl">written by</th></tr>');
    for (dp = 0; dp < 16; dp++) {
      ln = st.lines[s][dp]; lb = lineByte(s, C, dp); d0 = 32 * s + 2 * dp;
      var isCur = step && ((step.type === 'store' && step.s === s && step.dp === dp) || (step.type === 'scatter' && step.s === s));
      h.push('<tr' + (isCur ? ' class="currow"' : '') + '><td class="lbl">dp ' + dp + ' (dims ' + d0 + ',' + (d0 + 1) + ') / L' + (lb / 64) + ' / ' + lb + '-' + (lb + 63) + '</td>');
      for (t = 0; t < 16; t++) {
        T = 16 + t;
        written = ln.full || ((ln.cells >> t) & 1);
        cls = (T === FOCUS_T ? 'focus' : '');
        if (written) h.push(cellHtml(T, d0, cls, 'plane bytes ' + (lb + 4 * t) + '-' + (lb + 4 * t + 3) + ': token ' + T + ' dims ' + d0 + ',' + (d0 + 1)));
        else h.push('<td class="empty ' + cls + '" title="plane bytes ' + (lb + 4 * t) + '-' + (lb + 4 * t + 3) + ': not written yet">-</td>');
      }
      var by = ln.full ? ('store #' + ln.storeNo + ' (64 B at once)') : (ln.writes ? (ln.writes + ' x 4-byte writes') : 'nothing yet');
      h.push('<td class="lbl">' + by + '</td></tr>');
    }
    h.push('</table></div>');
    document.getElementById('stage-panel').innerHTML = h.join('');
  }

  function renderDram(mode, st, step) {
    var h = ['<div class="scroll"><div class="plane">'], s, c, b, n, dp, cls;
    h.push('<div class="ph"><b>DRAM: the plane</b><br>16 KiB, 256 lines</div>');
    for (c = 0; c < 4; c++) h.push('<div class="ph" style="text-align:center"><b>block c' + c + '</b><br>tokens ' + (16 * c) + '-' + (16 * c + 15) + '</div>');
    for (s = 0; s < 4; s++) {
      h.push('<div class="ph" style="color:' + DARK[s] + '"><b>dim step s' + s + '</b></div>');
      for (c = 0; c < 4; c++) {
        b = panelByte(s, c);
        if (c !== C) { h.push('<div class="pn other">panel (s' + s + ', c' + c + ')<br>bytes ' + b + '-' + (b + 1023) + '<br>not this block</div>'); continue; }
        n = 0; var w = 0;
        for (dp = 0; dp < 16; dp++) { if (st.lines[s][dp].fetched) n++; w += st.lines[s][dp].writes; }
        cls = 'pn' + (step && step.s === s && (step.type === 'store' || step.type === 'scatter') ? ' cur' : '');
        h.push('<div class="' + cls + '" style="background:' + TINT[s] + '">panel (s' + s + ', c1)<br>bytes ' + b + '-' + (b + 1023) + '<br>' + (n === 0 ? 'all 16 lines still cold in DRAM' : (n + ' of 16 lines now dirty in L1D, ' + (16 - n) + ' cold. ' + w + ' write op' + (w === 1 ? '' : 's') + '. Write-back later.')) + '</div>');
      }
    }
    h.push('</div></div>');
    document.getElementById('stage-dram').innerHTML = h.join('');
  }

  function describe(mode, steps, k, st) {
    var step = k > 0 ? steps[k - 1] : null, s, t, T, dp, d0, lb, n;
    if (!step) {
      return '<b>Start.</b> ' + (mode === 'block' ?
        'Block store of token block c1 (tokens 16-31) for KV head 0: 4 dim steps x (16 loads + 1 transpose + 16 full-line stores) = 132 steps, 64 stores. Press Play or Step.' :
        'Per-token scatter of the same 16 tokens: 16 tokens x 4 dim steps x (1 load + 1 scatter of 16 x 4 bytes) = 128 steps, 1024 four-byte writes. Press Play or Step.');
    }
    s = step.s;
    if (step.type === 'load') {
      t = step.t; T = 16 + t;
      return '<b>Step ' + k + ': load ' + (t + 1) + ' of 16 for dim step s' + s + '.</b> 64 bytes from the K buffer row of token ' + T + ' (KV head 0, row bytes ' + (64 * s) + '-' + (64 * s + 63) + ' = dims ' + (32 * s) + '-' + (32 * s + 31) + ', values ' + fv(val(T, 32 * s)) + ' .. ' + fv(val(T, 32 * s + 31)) + ') go into register r' + t + '. ' + (T === FOCUS_T ? 'This is the mock token: r5 now holds its dim pairs ' + (16 * s) + '-' + (16 * s + 15) + '. ' : '') + 'Which cache level holds the row at this moment (L2 of the core that ran rope, or L3) is not measured.';
    }
    if (step.type === 'transpose') {
      return '<b>Step ' + k + ': transpose in registers, dim step s' + s + '.</b> 64 shuffles in 4 stages, no memory access. Before: r_t = token 16+t, lanes = its 16 dim pairs. After: q_dp = dim pair dp (dims ' + (32 * s) + '+2dp, +1) of all 16 tokens, lanes = tokens 16-31. Token 21 moved from register r5 to lane 5 of every register q_dp. Each q_dp is now exactly one 64-byte line of the panel.';
    }
    if (step.type === 'store') {
      dp = step.dp; d0 = 32 * s + 2 * dp; lb = lineByte(s, C, dp); n = step.n;
      return '<b>Step ' + k + ': store #' + n + ' of 64.</b> Register q' + dp + ' -> panel (s' + s + ', c1) panel line ' + dp + ' = plane line L' + (lb / 64) + ' = plane bytes ' + lb + '-' + (lb + 63) + ', one 64-byte full-line store. The 64 bytes are written together. There is no order inside a line. The line carries dims ' + d0 + ',' + (d0 + 1) + ' of tokens 16-31. Token 21\'s 4 bytes are plane bytes ' + (lb + 20) + '-' + (lb + 23) + ' = (' + fv(val(FOCUS_T, d0)) + ', ' + fv(val(FOCUS_T, d0 + 1)) + '). In the cache model the line was cold (dashed in the L1D strip) and is now present and dirty in L1D (solid, tinted). Whether the core first read the line\'s old bytes (a read for ownership) is not measured. The fetch counter therefore shows a model value.' + (n === 64 ? ' <b>Done: 64 stores, 4 KiB, 64 lines each written once.</b>' : (dp === 15 ? ' Panel (s' + s + ', c1) is complete. Next come the 16 loads of dim step s' + (s + 1) + '.' : ''));
    }
    if (step.type === 'sload') {
      t = step.t; T = 16 + t;
      return '<b>Step ' + k + ': load, token ' + T + ', dim step s' + s + '.</b> 64 bytes from the K buffer row of token ' + T + ' (row bytes ' + (64 * s) + '-' + (64 * s + 63) + ', dims ' + (32 * s) + '-' + (32 * s + 31) + ') into one register.';
    }
    if (step.type === 'scatter') {
      t = step.t; T = 16 + t; lb = panelByte(s, C);
      var fresh = (t === 0) ? 16 : 0;
      return '<b>Step ' + k + ': scatter #' + step.n + ' of 64, token ' + T + ', dim step s' + s + '.</b> One instruction writes the 16 lanes to 16 different lines: lane dp -> panel (s' + s + ', c1) panel line dp, column ' + t + ' = plane bytes ' + (lb + 4 * t) + '-' + (lb + 4 * t + 3) + ', ' + (lb + 64 + 4 * t) + '-' + (lb + 64 + 4 * t + 3) + ', ... ' + (lb + 15 * 64 + 4 * t) + '-' + (lb + 15 * 64 + 4 * t + 3) + ' (stride 64). That is 16 partial-line writes of 4 bytes. ' + (fresh ? 'All 16 lines were cold. In the cache model that is 16 line fetches. ' : 'The 16 lines are already in L1D from token 16. No new fetch is needed, but each line receives partial write ' + (t + 1) + ' of 16. ') + (T === FOCUS_T ? 'Token 21\'s values ' + fv(val(FOCUS_T, 32 * s)) + ' .. ' + fv(val(FOCUS_T, 32 * s + 31)) + ' are written to bytes +20..+23 of each line. ' : '') + (step.n === 64 ? '<b>Done: 64 scatters = 1024 four-byte writes. Every line was written 16 times.</b>' : '');
    }
    return '';
  }

  // ---- controller
  var mode = 'block', steps = blockSteps(), k = 0, timer = null;
  var speedSel, modeSel;

  function render() {
    var st = derive(mode, steps, k);
    var step = k > 0 ? steps[k - 1] : null;
    document.getElementById('status').innerHTML = describe(mode, steps, k, st);
    var fetchText = (mode === 'block')
      ? 'line fetches from DRAM (model): 0 to <b>' + st.fetches + '</b>. Whether a full-line store first reads the old 64 bytes is not measured.'
      : 'line fetches from DRAM (model, not measured): <b>' + st.fetches + '</b>';
    document.getElementById('counters').innerHTML =
      '<span>step <b>' + k + '</b> / ' + steps.length + '</span>' +
      '<span>64-byte loads <b>' + st.loads + '</b></span>' +
      '<span>transposes <b>' + st.transposes + '</b></span>' +
      '<span>64-byte full-line stores <b>' + st.fullStores + '</b></span>' +
      '<span>4-byte partial writes <b>' + st.partialWrites + '</b></span>' +
      '<span>' + fetchText + '</span>' +
      '<span>lines of this block in L1D <b>' + st.fetches + '</b> of 64 (' + (st.fetches * 64 / 1024).toFixed(1) + ' KiB of 48 KiB)</span>';
    renderSource(mode, st, step);
    renderRegs(mode, st, step);
    renderCache(mode, st, step);
    renderPanelDetail(mode, st, step);
    renderDram(mode, st, step);
    document.getElementById('btn-play').textContent = timer ? 'Pause' : 'Play';
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function setK(v) { k = Math.max(0, Math.min(steps.length, v)); render(); }
  function tick() { if (k >= steps.length) { stop(); render(); return; } setK(k + 1); }
  function play() {
    if (timer) { stop(); render(); return; }
    if (k >= steps.length) k = 0;
    var sps = parseFloat(speedSel.value) || 4;
    timer = setInterval(tick, 1000 / sps); render();
  }
  function nextGroup() {
    // block: jump to the end of the current dim step's stores; scatter: to the end of the current token
    var i;
    for (i = k; i < steps.length; i++) {
      var sp = steps[i];
      if (mode === 'block' && sp.type === 'store' && sp.dp === 15) { setK(i + 1); return; }
      if (mode === 'scatter' && sp.type === 'scatter' && sp.s === 3) { setK(i + 1); return; }
    }
    setK(steps.length);
  }
  function setMode(m) { stop(); mode = m; steps = (m === 'block') ? blockSteps() : scatterSteps(); k = 0; render(); }

  document.addEventListener('DOMContentLoaded', function () {
    speedSel = document.getElementById('speed'); modeSel = document.getElementById('mode');
    document.getElementById('btn-play').addEventListener('click', play);
    document.getElementById('btn-back').addEventListener('click', function () { stop(); setK(k - 1); });
    document.getElementById('btn-fwd').addEventListener('click', function () { stop(); setK(k + 1); });
    document.getElementById('btn-group').addEventListener('click', function () { stop(); nextGroup(); });
    document.getElementById('btn-reset').addEventListener('click', function () { stop(); setK(0); });
    document.getElementById('btn-end').addEventListener('click', function () { stop(); setK(steps.length); });
    modeSel.addEventListener('change', function () { setMode(modeSel.value); });
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
    gt21_js = json.dumps([{"d": r["d"], "byte": r["byte"], "line": r["line"]} for r in GT21], separators=(",", ":"))
    stores_js = json.dumps(GTB["stores"], separators=(",", ":"))
    js = JS.replace("__GT21__", gt21_js).replace("__STORES__", stores_js)

    H = []
    H.append('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">')
    H.append('<title>Block store, byte by byte</title>')
    H.append('<style>' + CSS + '</style></head><body>')
    H.append('<main>')
    H.append('<h1>Block store, byte by byte</h1>')
    H.append('<p class="sub">A companion to section 3.1 (a) of <a href="store-remedies-report.html">the store-remedies report</a> (status/store-remedies-report.html). '
             'Code read at commit %s of branch jhan-amx-vnniK (worktree VNNIed-K-in-place/tron-VNNIed-K). Generated %s by exec/block-store-animation/gen_page.py (revision %d).</p>' % (HEAD, NOW, REV))
    H.append('<div class="short"><p><b>Short version.</b> The block store takes the K rows of the 16 tokens of one token block, for one KV head, transposes them in registers, and writes them into the KV cache as 64 whole 64-byte lines in a fixed order: dim step s0 first (stores 1-16), then s1, s2 and s3. '
             'One token\'s 128 values are one contiguous 256-byte row in the source buffer. '
             'They end as 64 four-byte cells, one in each of those 64 lines, always at the same offset inside the line.</p>'
             '<p>Section 4 plays this step by step with mock values, byte offsets and a cache and DRAM strip. A second mode plays the per-token scatter for comparison. <b>Direct answers to the five requests:</b></p><ul>'
             '<li><b>Animation:</b> section 4 (Play, Step, one dim step or one token at a time, two modes).</li>'
             '<li><b>Real values instead of colours:</b> every cell in sections 2 to 4 shows its two values, its dims, its token and its byte offsets (hover a cell for the full text). The mock data set of token 21 is in section 2.1 (all 64 pairs: dims, values, row bytes) and, with the plane line and the stored bf16 bits of every pair, in the 64-row table of section 3.3.</li>'
             '<li><b>Are the 4 dim steps one row or four rows?</b> One row. Token 21\'s K row for one KV head is 256 contiguous bytes. Dim step s is bytes 64s to 64s+63 of that row. Figure 3.1a of the store-remedies report stacked the four pieces only to fit the page width. Section 2.1 draws them in one row.</li>'
             '<li><b>CPU cache and DRAM:</b> the animation has an L1D strip (the 64 destination lines: cold, fetched or dirty), a DRAM view of the plane, and a stated cache model (section 4.3) that keeps measured facts apart from schematic ones.</li>'
             '<li><b>Which 64 bytes are saved first, second, third:</b> store #1 = plane bytes 1024-1087 (dims 0,1 of tokens 16-31), #2 = 1088-1151 (dims 2,3), ... #16 = 1984-2047 (dims 30,31), #17 = 5120-5183 (dims 32,33), ... #64 = 14272-14335 (dims 126,127). Section 3.2 numbers all 64 on the plane. Section 3.3 lists them.</li>'
             '</ul></div>')

    H.append('<h2>1. Words used here</h2>')
    H.append('<div class="scroll">' + words_table() + '</div>')

    H.append('<h2>2. The mock data set: token 21, KV head 0</h2>')
    H.append('<p>The animation follows the K row of one token, token 21 of the page (block c1, column t = 5), for KV head 0 of one layer. Its 128 mock values are 0.11, 0.12, 0.13, ... 1.38: value = 0.11 + 0.01 x dim. The other 15 tokens of the block (16-20 and 22-31) use the same rule shifted by 1.00 per token (section 2.3). Along any line the values step by 1.00 per token. Along any row they step by 0.01 per dim.</p>')
    H.append('<h3>2.1 One row, 256 bytes: the 4 dim steps are pieces of one row</h3>')
    H.append('<p>In the K buffer the row is contiguous. The four dim steps sit side by side, exactly as in memory: s0 is row bytes 0-63, s1 is 64-127, s2 is 128-191, s3 is 192-255. The first strip shows the whole 256-byte row without scrolling (on a screen at least about 950 px wide). The second strip shows every cell in detail: one dim pair (4 bytes) per cell, dims on top, the two values in the middle, the row bytes at the bottom (hover for the plane bytes the pair is written to). The detailed strip is about 4.3 screens wide at this page width (4166 px against about 980 px visible). Scroll it sideways to follow the row. The outlined cell is pair 0, the (0.11, 0.12) of the request.</p>')
    H.append('<div class="fig">' + overview_strip() + row_strip() + '</div>')
    H.append('<div class="answer"><p><b>Answer to the question about the report\'s Figure 3.1a.</b> The four dim steps are one row, not four rows. The figure drew them one under the other to fit 64 cells on the page. The block store reads this one row in four 64-byte loads, one per dim step. The loads happen at four different times: steps 6, 39, 72 and 105 of the 132-step animation. The reason is the loop order: the store handles one dim step of all 16 tokens before it moves to the next dim step.</p></div>')
    H.append('<h3>2.2 The bytes of the first pair</h3>')
    H.append('<p>A dim pair is two bf16 values, 4 bytes, the even dim at the lower address. The page displays the mock decimals. Memory holds the nearest bf16 value. For 0.11 that is 0x3DE1 = 0.109863. The table shows pair 0 of token 21 as bytes, in the K buffer row and at its destination in the plane.</p>')
    H.append('<div class="scroll">' + pair0_bytes_table() + '</div>')
    H.append('<h3>2.3 The 16 tokens of block c1</h3>')
    H.append('<p>Token T, dim d holds (T - 21) + 0.11 + 0.01 d. The first and last pair of every token:</p>')
    H.append('<div class="scroll">' + tokens_table() + '</div>')
    H.append('<p class="take">bf16 keeps 8 bits of precision (about 2.4 decimal digits). So in memory neighbouring mock values of the larger tokens round to the same bf16 value (for example -4.89 and -4.88 both become -4.875). The page shows the intended decimals. The positions are exact.</p>')
    H.append('<h3>2.4 Where the row sits in the K buffer</h3>')
    H.append('<p>The store reads from the pass\'s K buffer: one row per token item, all KV heads of the token in one row (qwen3-4b: 8 heads x 256 bytes = 2048 bytes). KV head h is row bytes 256h to 256h+255. The animation shows head 0: bytes 0-255 of each token\'s row. The same loads, transpose and stores repeat for heads 1 to 7 into 7 other planes [model.hpp row_of, store_k_block].</p>')

    H.append('<h2>3. The destination: one KV head\'s plane of one page</h2>')
    H.append('<h3>3.1 The 16 panels and their byte offsets</h3>')
    H.append('<p>The plane is 16 KiB = 256 lines of 64 bytes. Panel (s, c) starts at byte (4s + c) x 1024 and holds dim step s of token block c: 16 lines, one per dim pair, each line = that pair of the block\'s 16 tokens. Token 21 is column 5 of block c1. So its bytes are at +20 to +23 in every line of the four panels (s0, c1) ... (s3, c1) [k_vnni.hpp:22-30].</p>')
    H.append('<div class="fig">' + plane_grid_static() + '</div>')
    H.append('<h3>3.2 Save order: the 64 stores on the plane, in address order</h3>')
    H.append('<p>Each box is one 64-byte line of the plane (256 boxes, one figure row per panel, panels in address order, one figure column per panel line dp). The number is the store\'s position in the block store\'s sequence. The small text is token 21\'s even value in that line. The stores fill panel (s0, c1) top to bottom. Then the next 16 stores start 4 KiB farther, at panel (s1, c1) (bytes 5120-6143), and so on. Lines of the other blocks are not touched [k_vnni.hpp:198-215].</p>')
    H.append('<div class="fig">' + order_fig() + '</div>')
    H.append('<p class="take">Read across one panel (one figure row): 16 consecutive stores, 1 KiB, contiguous. Read down the c1 panels: the four panels of the block are 4096 bytes apart. So the 4 KiB of one block and one KV head is written as 4 contiguous pieces of 1024 bytes, spread over a 13 KiB span of the plane.</p>')
    H.append('<h3>3.3 Token 21\'s 64 cells, one per store</h3>')
    H.append('<details open><summary>The 64 rows (store number, plane line, line bytes, token 21\'s 4 bytes, dims, values, bf16 bits). Click to fold.</summary><div class="scroll">' + token21_table() + '</div></details>')

    H.append('<h2>4. The animation</h2>')
    H.append('<p>Mode <b>block store</b> plays k_vnni::store_block for block c1 of KV head 0: 4 dim steps x (16 loads, 1 transpose, 16 full-line stores) = 132 steps. Mode <b>per-token scatter</b> plays the store of the same 16 tokens as the 2026-09-14 binary (commit %s) did it, and as decode does it today: 16 tokens x 4 dim steps x (1 load, 1 scatter of 16 x 4 bytes) = 128 steps. Steps are instruction-level events. Their durations are not to scale. Keys: right and left arrows step, space plays.</p>' % MONDAY_TIP)
    H.append('<div class="controls"><label>Mode <select id="mode"><option value="block">block store (2 to 16 tokens in a block)</option><option value="scatter">per-token scatter (the 2026-09-14 binary, and decode today)</option></select></label>'
             '<button id="btn-play">Play</button><button id="btn-back">Step back</button><button id="btn-fwd">Step</button><button id="btn-group">Next dim step / token</button><button id="btn-end">To the end</button><button id="btn-reset">Reset</button>'
             '<label>Speed <select id="speed"><option value="1">1 step/s</option><option value="4" selected>4 steps/s</option><option value="10">10 steps/s</option><option value="25">25 steps/s</option></select></label></div>')
    H.append('<div class="status" id="status">The animation needs JavaScript. Sections 2 and 3 above carry the same positions as static tables.</div>')
    H.append('<div class="counters" id="counters"></div>')
    H.append('<div class="legend"><span><span class="sw" style="background:#cce3f0"></span>s0 dims 0-31</span><span><span class="sw" style="background:#faeccc"></span>s1 dims 32-63</span><span><span class="sw" style="background:#ccece3"></span>s2 dims 64-95</span><span><span class="sw" style="background:#f5e4ed"></span>s3 dims 96-127</span>'
             '<span><span class="sw" style="outline:2px solid #0b0b0b;outline-offset:-2px"></span>token 21 (the mock token)</span><span><span class="sw" style="box-shadow:0 0 0 2px #2a78d6"></span>touched by the current step</span>'
             '<span><span class="sw" style="border-style:dashed"></span>line cold (only in DRAM)</span><span><span class="sw"></span>line present and dirty in L1D (filled with its dim step\'s colour)</span><span><span class="sw" style="border-bottom:4px solid #0b0b0b"></span>line partly written (half-strength colour, bar = cells written)</span></div>')
    H.append('<p class="take">Cells show the mock decimals of section 2.3. The bf16 in memory is the nearest representable value (section 2.2). For tokens whose values are 2 or more in magnitude, neighbouring dims round to one stored value (section 2.3). The positions and byte offsets are exact.</p>')

    H.append('<div class="stage"><h3>4.1 Source: the K buffer rows of the 16 tokens (written by the rope kernel just before, cache level at load time not measured)</h3><p class="stagehint">Each row is one token\'s 256 bytes for KV head 0, drawn as its four 64-byte dim steps side by side. A piece turns coloured when it has been loaded into a register. The values shown are its first and last dim.</p><div id="stage-src"></div></div>')
    H.append('<div class="stage"><h3>4.2 Core: 16 AVX-512 registers, then the transpose</h3><div id="stage-regs"></div></div>')
    H.append('<div class="stage"><h3>4.3 Destination: L1D lines, the panel that fills, and DRAM</h3>'
             '<p class="stagehint"><b>Cache model used here (schematic).</b></p><ul class="stagehint">'
             '<li>A store leaves its bytes in the core. They merge into the 64-byte line in L1D once the line is present and writable.</li>'
             '<li>A line that is not present is fetched from the level that holds it. For a cold KV page that level is DRAM.</li>'
             '<li>In scatter mode the first write to each of the 64 lines fetches it. The 15 later writes of the other tokens find the line already in L1D.</li>'
             '<li>In block mode each line is written once and whole. Whether the core still reads a line\'s old bytes before a full-line store (a read for ownership) is not measured. The counter labels every fetch as model, not measurement.</li>'
             '<li>The dirty lines return to DRAM later, when the cache evicts them. The animation does not time that.</li>'
             '<li>Measured: the cache sizes and the 64-byte line (getconf, the POSIX system-configuration query, on delphi-3bda). Not measured: which level holds a source row at load time, and whether a full-line store fetches.</li></ul>'
             '<h4>L1D: the 64 destination lines of block c1 (4 KiB of the 48 KiB L1D)</h4><div id="stage-cache"></div>'
             '<h4>The panel that is being written</h4><div id="stage-panel"></div>'
             '<h4>DRAM: the whole plane of KV head 0 for this page</h4><div id="stage-dram"></div></div>')

    H.append('<h2>5. The two other cases, and what changed since the report</h2>')
    H.append('<ul><li><b>Partial block</b> (a run of 2 to 15 items of one block): one load per present token per dim step (an absent token\'s register is set to zero by a register instruction, no load is issued), the same transpose, and the same 16 stores per panel, each masked to the present tokens\' lanes. The absent columns keep their bytes. So the store count is the same as for a full block. Only fewer bytes change [k_vnni.hpp:200-203 for the loads, 206-214 for the stores].</li>'
             '<li><b>Lone token</b> (a run of 1, the decode case): the code stores it with set_k_row, the scatter path of the animation\'s second mode: 4 scatters, 64 lines, 4 bytes each [model.hpp K_SCATTER_RUN_LEN_1, store_k_block].<ul>'
             '<li>The code states the rule, not the reason.</li>'
             '<li>The report gives the reason as a design argument, not a measurement: 16 masked stores per panel would each write 4 bytes into one line, the same 64 partial-line writes as the 4 scatters [report section 3.1 (a), Figure 3.1c]. The report\'s caption compares only the stores.</li>'
             '<li>From the code, such a store would also cost one load and one transpose per dim step. Only the present token\'s register is loaded. The other 15 registers are zeroed without a load [k_vnni.hpp:200-204].</li>'
             '<li>The report measures 444 ns per K row in decode at tp2 and 540 ns at tp4, against 105 ns in prefill [report section 2.3].</li>'
             '<li>The report\'s explanation has two parts. In decode the 64 lines of a token\'s column are cold. Every 4-byte write then waits for a line fetch. That explanation is a hypothesis: no cache-miss counter was recorded. A per-level miss count around Save K in decode would confirm or reject it.</li></ul></li>'
             '<li><b>Since the report:</b> the runtime switches TRON_K_VNNI_BLOCK and TRON_K_VNNI_STRIPE that the report\'s commit 9928cb2849 added were removed (commit ab94854999). At head %s the block store is the only path for runs of 2 or more items. The sharing of the store with the main helpers (report section 3.2) is unchanged: it is on in generated plugins when a pass has more than 16 items and the plugin runs with 2 to 128 workers. A single worker (the handwritten plugins, and the unit tests except one shared-save case in t_llama_unit, the llama unit-test program t/t_llama_unit.cpp) never shares [model.hpp k_store_shared, Note [Shared block save]].</li></ul>' % HEAD)

    H.append('<h2>6. Sources and checks</h2>')
    H.append('<p>Every cell position on this page comes from running the real store_block on the mock rows (exec/block-store-animation/gt.cpp). gt.cpp is built by build-gt.sh against the worktree\'s k_vnni.hpp. g++ 11 has no __bf16 type. The build therefore uses a shim: two small replacement header files for tron\'s bf16 and fp16 types, in exec/block-store-animation/shim/, with the same member functions as tron\'s. The kernel only moves bf16 bytes and takes sizeof(bf16) [k_vnni.hpp:51-63]. So the replacement does not change what store_block writes. The run reported 0 mismatches against the index formula, 0 poison slots written outside the block, and byte-identical output to scatter_row per token (memcmp, the C byte-compare function, returned 0). The store order (#1 to #64) is not observed by that run. A final-state check cannot see order. The order is the program order of the two loops in store_block: dim step s outer, panel line dp inner [k_vnni.hpp:198-215]. gt.cpp writes that order into block.json from the same loop nest. The tables of sections 2.2 and 3.3 read the run\'s output (token21.json) for the byte offsets and the bf16 bits. The other figures of sections 2 and 3, and the values column of 3.3, are computed from the same index formula and the mock-value rule of the page. gen_page.py stops if that formula disagrees with the run\'s output for any of the 128 dims of token 21 or the 64 stores. The animation recomputes the same offsets with the formula and compares them at load time:</p>')
    H.append('<p class="mono" id="selfcheck">Self-check: JavaScript did not run.</p>')
    H.append('<div class="scroll">' + sources_table() + '</div>')
    H.append('<p class="take">Line numbers refer to the worktree at commit %s. The report\'s figures 3.1a-c stay valid. This page adds the values, the byte offsets, the order and the cache view.</p>' % HEAD)
    H.append('</main>')
    H.append('<script>' + js + '</script></body></html>')
    page = "\n".join(H)
    bad = [(i, c) for i, c in enumerate(page) if ord(c) > 127]
    assert not bad, "non-ASCII characters at %r" % bad[:5]
    with open(OUT, "w") as f:
        f.write(page)
    print("wrote %s (%d bytes)" % (OUT, len(page)))


if __name__ == "__main__":
    build()
