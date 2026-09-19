#!/usr/bin/env python3
"""Generate status/VNNI-K-FPGA-ATTN.html (pure ASCII, light theme). Run: python3 exec/gen_fpga_page.py"""
import os, sys

OUT = "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/VNNI-K-FPGA-ATTN.html"
SCRATCH = os.environ.get("FIG_DIR", "/tmp")  # standalone SVG copies for render checks

INK, INK2, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BASE_C, VNNI_C, CHANGED_C, SAME_C = "#8a8987", "#eb6834", "#fbe3d8", "#f3f2ef"

# ---------------------------------------------------------------- figure 1
def fig1():
    W, H = 1040, 400
    bw, bh, gap, x0, y0 = 176, 96, 30, 20, 40
    boxes = [
        ("save_k (CPU)", ["computes K per token", "and stores it into", "the KV page"], False),
        ("KV page, K plane", ["VNNI layout for", "128-dimension heads", "(TRON_K_VNNI)"], True),
        ("gof::populate", ["k_head_fn gathers one", "token's row into", "scratch (get_k_row)"], True),
        ("shuffle_k_entry", ["packs the row into", "the hwcacheblock", "(HBM word order)"], False),
        ("DMA to HBM", ["xfer of the staging", "block; the FPGA", "reads HBM only"], False),
    ]
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="The path of one K row from the CPU to the FPGA memory; the two changed steps are shaded" '
         f'xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, Segoe UI, sans-serif">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}"/>')
    s.append('<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
             f'<path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker></defs>')
    s.append(f'<text x="{x0}" y="22" font-size="13" fill="{INK2}">Figure 1. Where one K row travels in a run with FPGA attention (USE_HW_ATTN unset). Shaded = changed by PR 4424.</text>')
    for i, (title, lines, changed) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        fill = CHANGED_C if changed else SAME_C
        stroke = VNNI_C if changed else AXIS
        s.append(f'<rect x="{x}" y="{y0}" width="{bw}" height="{bh}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{2 if changed else 1}"/>')
        s.append(f'<text x="{x + bw/2:.0f}" y="{y0 + 24}" font-size="14" font-weight="600" text-anchor="middle" fill="{INK}">{title}</text>')
        for j, ln in enumerate(lines):
            s.append(f'<text x="{x + bw/2:.0f}" y="{y0 + 46 + j*17}" font-size="12.5" text-anchor="middle" fill="{INK2}">{ln}</text>')
        if changed:
            s.append(f'<text x="{x + bw/2:.0f}" y="{y0 + bh + 18}" font-size="12" font-weight="600" text-anchor="middle" fill="{VNNI_C}">changed</text>')
        else:
            s.append(f'<text x="{x + bw/2:.0f}" y="{y0 + bh + 18}" font-size="12" text-anchor="middle" fill="{INK2}">unchanged</text>')
        if i < len(boxes) - 1:
            ax0, ax1, ay = x + bw + 3, x + bw + gap - 3, y0 + bh/2
            s.append(f'<line x1="{ax0}" y1="{ay:.0f}" x2="{ax1}" y2="{ay:.0f}" stroke="{INK2}" stroke-width="2" marker-end="url(#ah)"/>')
    # branch: CPU-scored share of the same run
    kx = x0 + 1 * (bw + gap) + bw/2
    by = y0 + bh + 40
    s.append(f'<line x1="{kx:.0f}" y1="{y0 + bh + 26}" x2="{kx:.0f}" y2="{by + 58}" stroke="{INK2}" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#ah)"/>')
    bx, bw2, bh2 = x0 + 2 * (bw + gap), 2 * bw + gap, 96
    byy = by + 62
    s.append(f'<rect x="{bx}" y="{byy}" width="{bw2}" height="{bh2}" rx="6" fill="{CHANGED_C}" stroke="{VNNI_C}" stroke-width="2"/>')
    s.append(f'<text x="{bx + 14}" y="{byy + 24}" font-size="14" font-weight="600" fill="{INK}">CPU software attention in the same run</text>')
    s.append(f'<text x="{bx + 14}" y="{byy + 46}" font-size="12.5" fill="{INK2}">scores positions 0 to 126 and the tail tokens not yet in HBM.</text>')
    s.append(f'<text x="{bx + 14}" y="{byy + 63}" font-size="12.5" fill="{INK2}">Reader = qk_group or the VNNI AMX kernel, never the row-major dotter.</text>')
    s.append(f'<text x="{bx + 14}" y="{byy + 80}" font-size="12.5" fill="{INK2}">fp32 add order differs from main on partial pages (issue 4444).</text>')
    s.append(f'<text x="{kx + 10:.0f}" y="{by + 30}" font-size="12" fill="{INK2}">the same pages are also read by</text>')
    s.append(f'<text x="{x0}" y="{H - 12}" font-size="12" fill="{INK2}">Boxes are steps, not time. Only one function reads K from host pages for the FPGA: gof::populate [src/tron/gof.cpp:213].</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- figure 2
ROWS = [
    # label, sublabel, unit, base, vnni, better
    ("smoke TTFT", "1 user, greedy, 128 tokens", "s", 0.4270, 0.4160, "lower is better"),
    ("smoke decode", "1 user, greedy, 128 tokens", "tok/s", 223.70, 222.78, "higher is better"),
    ("cell TTFT", "8 users, 256 tokens", "s", 3.1549, 3.1625, "lower is better"),
    ("cell decode per user", "8 users, 256 tokens", "tok/s", 125.389, 123.647, "higher is better"),
]

def fmt_abs(v, unit):
    if unit == "s":
        return f"{v:.4f} s" if v < 1 else f"{v:.3f} s"
    return f"{v:.2f} {unit}" if v < 200 else f"{v:.1f} {unit}"

def fmt_delta(b, v, unit):
    d = v - b
    pct = 100.0 * d / b
    if unit == "s":
        ad = f"{d*1000:+.1f} ms"
    else:
        ad = f"{d:+.2f} {unit}"
    return f"{ad} ({pct:+.2f}%)", pct

def fig2():
    W = 1040
    left, right, top = 280, 830, 78
    rowh = 74
    H = top + rowh * len(ROWS) + 70
    xmin, xmax = -3.0, 3.0
    def X(p):
        return left + (p - xmin) / (xmax - xmin) * (right - left)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="Dumbbell chart: change of four metrics from the row-major base to the VNNI binary under FPGA attention, one run each" '
         f'xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, Segoe UI, sans-serif">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}"/>')
    s.append(f'<text x="20" y="22" font-size="13" fill="{INK2}">Figure 2. FPGA attention, qwen-3-4b tp2, prompt 1024: VNNI binary against the row-major base. One run per arm.</text>')
    # legend
    s.append(f'<circle cx="28" cy="46" r="6" fill="{BASE_C}"/><text x="40" y="50" font-size="12.5" fill="{INK}">base = 544ca05c7a, row-major K (anchored at 0)</text>')
    s.append(f'<circle cx="388" cy="46" r="6" fill="{VNNI_C}"/><text x="400" y="50" font-size="12.5" fill="{INK}">VNNI = dc950be5f2, TRON_K_VNNI=ON (staging code identical to head ff680c8020)</text>')
    # grid + axis
    for p in range(-3, 4):
        x = X(p)
        s.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{top + rowh*len(ROWS)}" stroke="{GRID if p else AXIS}" stroke-width="{1 if p else 1.5}"/>')
        s.append(f'<text x="{x:.1f}" y="{top + rowh*len(ROWS) + 18}" font-size="12" text-anchor="middle" fill="{INK2}">{p:+d}%</text>' if p else
                 f'<text x="{x:.1f}" y="{top + rowh*len(ROWS) + 18}" font-size="12" text-anchor="middle" fill="{INK2}">0 = base</text>')
    s.append(f'<text x="{(left+right)/2:.0f}" y="{top + rowh*len(ROWS) + 40}" font-size="12.5" fill="{INK2}" text-anchor="middle">VNNI minus base, in percent of base</text>')
    for i, (lab, sub, unit, b, v, better) in enumerate(ROWS):
        cy = top + rowh * i + rowh / 2
        dtxt, pct = fmt_delta(b, v, unit)
        xb, xv = X(0), X(pct)
        s.append(f'<text x="{left - 14}" y="{cy - 10}" font-size="13.5" font-weight="600" text-anchor="end" fill="{INK}">{lab}</text>')
        s.append(f'<text x="{left - 14}" y="{cy + 6}" font-size="11.5" text-anchor="end" fill="{INK2}">{sub}</text>')
        s.append(f'<text x="{left - 14}" y="{cy + 21}" font-size="11.5" text-anchor="end" fill="{INK2}">{better}</text>')
        s.append(f'<line x1="{min(xb,xv):.1f}" y1="{cy:.1f}" x2="{max(xb,xv):.1f}" y2="{cy:.1f}" stroke="{VNNI_C}" stroke-width="2"/>')
        s.append(f'<circle cx="{xb:.1f}" cy="{cy:.1f}" r="7" fill="{BASE_C}" stroke="{SURF}" stroke-width="2"><title>base: {fmt_abs(b, unit)}</title></circle>')
        s.append(f'<circle cx="{xv:.1f}" cy="{cy:.1f}" r="7" fill="{VNNI_C}" stroke="{SURF}" stroke-width="2"><title>VNNI: {fmt_abs(v, unit)}</title></circle>')
        # direct labels: base below, vnni above (or swapped if too close)
        s.append(f'<text x="{xb:.1f}" y="{cy + 24}" font-size="12" text-anchor="middle" fill="{INK2}">{fmt_abs(b, unit)}</text>')
        s.append(f'<text x="{xv:.1f}" y="{cy - 14}" font-size="12" text-anchor="middle" fill="{INK}">{fmt_abs(v, unit)}</text>')
        s.append(f'<text x="{right + 16}" y="{cy + 4}" font-size="12.5" fill="{INK}">{dtxt}</text>')
    s.append(f'<text x="20" y="{H - 10}" font-size="12" fill="{INK2}">Smoke tokens: 128 of 128 identical between the two binaries. No spread is available (n = 1 per arm), so none of the four deltas can be separated from run-to-run noise.</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- page
CSS = f"""
:root {{ color-scheme: light; --ink: {INK}; --ink2: {INK2}; --grid: #e6e5e1; --bg: #ffffff; --accent: #2a78d6; }}
body {{ margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--ink); font: 15px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; max-width: 1100px; margin-left: auto; margin-right: auto; }}
h1 {{ font-size: 24px; margin: 0 0 6px; }} h2 {{ font-size: 19px; margin: 36px 0 8px; border-bottom: 1px solid var(--grid); padding-bottom: 4px; }} h3 {{ font-size: 16px; margin: 22px 0 6px; }}
p, li {{ max-width: 900px; }} .meta {{ color: var(--ink2); font-size: 13px; }}
.short {{ background: #f3f2ef; border-left: 4px solid var(--accent); padding: 10px 14px; margin: 12px 0; max-width: 900px; }}
table {{ border-collapse: collapse; margin: 10px 0 16px; font-size: 13px; }} th, td {{ border: 1px solid var(--grid); padding: 4px 8px; text-align: left; vertical-align: top; }} th {{ background: #f4f3f0; }}
td.num {{ font-variant-numeric: tabular-nums; text-align: right; }}
pre {{ background: #f6f5f2; border: 1px solid var(--grid); padding: 8px 10px; font-size: 12.5px; overflow-x: auto; max-width: 900px; }}
code {{ font-size: 13px; background: #f6f5f2; padding: 0 3px; }}
.chart {{ max-width: 100%; height: auto; display: block; margin: 8px 0 4px; border: 1px solid var(--grid); }}
.cap {{ color: var(--ink2); font-size: 13px; margin: 2px 0 14px; max-width: 900px; }}
.small {{ font-size: 13px; color: var(--ink2); }}
.tag {{ display: inline-block; font-size: 12px; padding: 1px 6px; border-radius: 3px; margin-right: 6px; }}
.fact {{ background: #e8f1fb; color: #1c4f8a; }} .risk {{ background: #fbe3d8; color: #8a3a12; }} .gap {{ background: #fff4e5; color: #7a3b00; }}
"""

def page():
    f1, f2 = fig1(), fig2()
    open(os.path.join(SCRATCH, "fig1.svg"), "w").write(f1.replace('class="chart" ', ''))
    open(os.path.join(SCRATCH, "fig2.svg"), "w").write(f2.replace('class="chart" ', ''))
    d_cell_ttft, _ = fmt_delta(3.1549, 3.1625, "s")
    d_cell_tps, _ = fmt_delta(125.389, 123.647, "tok/s")
    d_smoke_ttft, _ = fmt_delta(0.4270, 0.4160, "s")
    d_smoke_tps, _ = fmt_delta(223.70, 222.78, "tok/s")
    H = []
    a = H.append
    a('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">')
    a('<title>VNNI K and FPGA attention</title>')
    a(f'<style>{CSS}</style></head><body>')
    a('<h1>VNNI K layout and the FPGA attention path</h1>')
    a('<p class="meta">Written 2026-09-16 for PR positron-ai/tron #4424 (head ff680c8020, merge base c7844ca2ce). Code read in the worktree VNNIed-K-in-place/tron-VNNIed-K at the head. Measurement from exec/results/vnnik4-models-20260915. Method: six independent readers and three adversarial verifiers per finding (appendix B). Terms are defined in section 1.</p>')
    a('<div class="short"><b>Short version.</b> The FPGA reads K from host memory through one function, gof::populate. PR 4424 changed that function&#39;s callback so it rebuilds each token&#39;s K row from the VNNI layout before the copy, and one FPGA run gave tokens identical to the row-major build. Two things are open: the cost of the rebuild is unmeasured, and no CI run has executed the VNNI build on an FPGA.</div>')

    a('<h2>1. Words used here</h2>')
    a('<table><thead><tr><th>term</th><th>meaning</th></tr></thead><tbody>')
    terms = [
        ("tron, runtron", "tron = the inference program under test. runtron = its command-line tool that runs one model with synthetic users."),
        ("PR 4424, TRON_K_VNNI", "the pull request under review. TRON_K_VNNI is its CMake build option (default OFF). With it on, the K cache of every 128-dimension head is stored in the VNNI layout."),
        ("VNNI layout, K plane", "VNNI = Vector Neural Network Instructions. The layout is the pair-interleaved operand order of the AMX tile multiply: one 64-byte row holds one pair of dimensions for 16 consecutive tokens. The K plane is the K half of one KV page (64 tokens of one KV head)."),
        ("AMX", "Intel Advanced Matrix Extensions, the tile-multiply unit used by the software attention of PR 3879 and PR 4424."),
        ("FPGA attention, USE_HW_ATTN", "attention computed on the FPGA cards. The environment variable USE_HW_ATTN unset turns it on for ingested models. USE_HW_ATTN=0 keeps attention on the CPU."),
        ("GOF", "group of four consecutive tokens, the unit in which K and V are staged and copied to the FPGA."),
        ("gof::populate, k_head_fn", "gof::populate copies a GOF&#39;s K and V rows into a host staging block. k_head_fn is the callback that hands it one token&#39;s K row for one KV head."),
        ("shuffle_k_entry, hwcacheblock", "shuffle_k_entry rearranges a K row into the word order the FPGA expects. The hwcacheblock is the 8 KiB host staging block for one GOF that the DMA then copies."),
        ("HBM", "High Bandwidth Memory, the FPGA card&#39;s memory that holds the K and V cache the FPGA reads."),
        ("engagement point", "the first sequence position the FPGA scores, 127 by default. The CPU scores the positions below it, and the tail tokens that are not yet in HBM."),
        ("dotter, qk_group", "dotter = the per-token AVX-512 dot-product loop of the software attention before PR 4424 (row-major K). qk_group = the new AVX-512 reader that scores 64 tokens at once from the VNNI plane."),
        ("kill switch", "the environment variable TRON_AMX_DISABLE=1. It turns the AMX kernels off at run time."),
        ("kv_mul", "query heads per KV head (grouped-query attention). The AMX kernel serves kv_mul 4 only; the layout gate does not look at kv_mul."),
        ("save_k, shared block save", "save_k stores the pass&#39;s K rows into the KV pages. The shared block save is the PR&#39;s way of splitting that store over the idle helper threads in 16-token blocks."),
        ("TTFT, TPS", "TTFT = time to first token, here runtron&#39;s &#39;Parsing the prompt took&#39; time in seconds. TPS = generated tokens per second per user."),
        ("base, VNNI binary", "base = runtron built from 544ca05c7a (PR 3879 head, row-major K, TRON_AMX_DISPATCH=ON). VNNI = runtron built from dc950be5f2 (the branch before its rebase onto main) with TRON_K_VNNI=ON."),
    ]
    for t, m in terms:
        a(f'<tr><td>{t}</td><td>{m}</td></tr>')
    a('</tbody></table>')

    a('<h2>2. The question and the answer</h2>')
    a('<p>Question (2026-09-16): PR 4424 changes the K layout to VNNI. Does that affect the FPGA attention path?</p>')
    a('<p>Answer: no functional effect was found. The FPGA never reads a KV page directly. It reads HBM, and HBM is filled from a staging block that one function builds row by row. The PR made that one function layout-aware. The bytes that reach HBM are the same by construction, and the one FPGA run that exists produced the same tokens as the row-major binary. What the PR does change in an FPGA run is the CPU-scored share of attention (section 4) and the cost of building the staging block (section 6), and neither has been measured with repetitions.</p>')
    a(f1)
    a('<p class="cap">Figure 1. Boxes are steps, not time. The two shaded steps are the PR&#39;s changes on this path. The dashed branch shows that the same pages also feed the CPU software attention of an FPGA run.</p>')

    a('<h2>3. What was verified in the code</h2>')
    a('<p>Every item below was read at head ff680c8020 and survived three adversarial checks (appendix B).</p>')
    a('<ul>')
    a('<li><span class="tag fact">fact</span><b>One consumer.</b> gof::populate is the only production code that reads K bytes from host KV pages to build the FPGA staging block [src/tron/gof.cpp:213]. shuffle_k_entry then indexes the row it gets as a contiguous 128-element array [h/pos/hwattention.hpp:778-781]. The DMA reads the hwcacheblock only, never a page.</li>')
    a('<li><span class="tag fact">fact</span><b>The rewiring.</b> When the layout gate is on, the k_head_fn lambda calls page::get_k_row into a 64-byte-aligned scratch buffer that populate owns, and returns the scratch. Otherwise it returns the old in-page pointer [h/tron/scheduler/full.hpp:2644-2660; src/tron/gof.cpp:203]. get_k_row on a VNNI slot is k_vnni::gather_row, four AVX-512 gathers of 16 dwords [h/tron/models/kv_cache.hpp:1737-1748; h/tron/kernels/k_vnni.hpp:222-229].</li>')
    a('<li><span class="tag fact">fact</span><b>Bit-exact rebuild.</b> gather_row is tested as the exact inverse of the store for all 64 tokens of a page, and the page-level round trip is tested through set_k_row and get_k_row [t/t_k_vnni_layout.cpp:126, :394]. The save_k case of t_llama_unit reads every stored row back with get_k_row and compares it to the source bits.</li>')
    a('<li><span class="tag fact">fact</span><b>HBM format unchanged.</b> The diff between c7844ca2ce and ff680c8020 is empty under h/pos, h/libpos.hpp, lib, fpga-reg and h/tron/hardware. shuffle_k_entry, k_hwcacheblock::set_position and the HBM word order are as on main.</li>')
    a('<li><span class="tag fact">fact</span><b>The gate cannot disagree between store and staging.</b> A KV slot becomes a hardware slot only when its geometry equals hardware_attention_geometry.kv exactly [h/tron/models/kv_cache.hpp:404-416]. The store gates on the same head size. The accessors reject a wrong geometry at compile time in a uniform cache and by an always-on TRON_ASSERT in a heterogeneous cache [h/tron/models/kv_cache.hpp:1416-1421]. The row view page::k() does not compile for a VNNI slot [h/tron/models/kv_cache.hpp:1662-1664].</li>')
    a('<li><span class="tag fact">fact</span><b>Head size decides, not kv_mul.</b> The gate is head_size == 128 under the define and false otherwise [h/tron/kernels/k_vnni.hpp:90-97]. So gpt-oss (64-dimension heads) keeps the row-major path on both sides. A kv_mul 8 model such as qwen-3-30b-a3b takes the VNNI layout and therefore the gather in staging too.</li>')
    a('<li><span class="tag fact">fact</span><b>Completion and ordering unchanged.</b> populate&#39;s callers still require all four tokens of a GOF complete before reading (kv_complete_fn, save_count). The PR did not touch kv_saves_, mark_k_complete or is_kv_complete. In the shared block save, the main thread marks tokens complete only after every helper has left the window [h/tron/models/model.hpp, Note Shared block save].</li>')
    a('<li><span class="tag fact">fact</span><b>No store writes another token&#39;s lane.</b> The per-token scatter writes only the token&#39;s 64 dwords. The block store uses an unmasked full-line store only when all 16 lanes belong to the current run, and masked stores otherwise [h/tron/kernels/k_vnni.hpp store_block]. So a gather of token C and a store of tokens A to B in the same block touch disjoint bytes.</li>')
    a('<li><span class="tag fact">fact</span><b>Page copies and relocation.</b> A whole-page copy is one memcpy. Any other range moves token by token with gather_row and scatter_row, because a token&#39;s column depends on its offset in the page [h/tron/models/kv_cache.hpp:2099-2117]. Page relocation rebuilds page_info through the same factory, so the gathering lambda is used after relocation too [h/tron/scheduler/full.hpp:1408-1426].</li>')
    a('</ul>')

    a('<h2>4. What does change in an FPGA run</h2>')
    a('<p>The FPGA scores positions from the engagement point on. The CPU still scores two classes of pairs: every query at a position below 127, and the tail tokens that are not yet in HBM. Under TRON_K_VNNI those pairs never use the row-major dotter. A dense 64-token page with AMX available takes the VNNI AMX kernel qk_vnni_128x4. Every other pair takes qk_group [h/tron/models/self_attention.hpp:1574-1640]. The dense kernel is bit-identical to the row-major AMX kernel by test. qk_group has a different fp32 add order from the dotter.</p>')
    a('<p>The kill switch does not bring the dotter back. TRON_AMX_DISABLE=1 only makes the AMX probe report unavailable, and the pair then falls to qk_group. So under TRON_K_VNNI an FPGA run with the kill switch is an AMX-off run of the same layout, not a rollback to the numerics of a row-major binary. Issue #4444 records this contract change, and item 4 of Note [AMX attention dispatch] is stale on this point [h/tron/kernels/amx_attn_iface.hpp:47-51].</p>')
    a('<p>Consequence: the FPGA arm is not numerically identical to main by construction. A near-tie token flip is possible in the CPU-scored share, exactly as in the CPU-attention runs of issue #4444. The one FPGA run gave identical tokens.</p>')

    a('<h2>5. The one measurement</h2>')
    a('<p>Campaign vnnik4-models-20260915, cell fpga: model ingested-qwen-3-4b-instruct-2507-tp2 (8 KV heads, head size 128, kv_mul 4), prompt 1024 tokens, USE_HW_ATTN unset, both binaries logged hardware attention enabled with engagement 127. The VNNI binary is the pre-rebase commit dc950be5f2. Its k_head_fn, gof.cpp, get_k_row and gather_row are identical to the head ff680c8020.</p>')
    a(f2)
    a('<p class="cap">Figure 2. Each row is one metric. The gray dot is the base value, anchored at 0. The orange dot is the VNNI value as a percent change from base, with both absolute values written on the dots. One run per arm.</p>')
    a('<table><thead><tr><th>run</th><th>metric</th><th>base 544ca05c7a</th><th>VNNI dc950be5f2</th><th>VNNI minus base</th></tr></thead><tbody>')
    a('<tr><td>smoke: 1 user, greedy, 128 generated tokens</td><td>generated tokens</td><td colspan="2" class="num">128 of 128 identical</td><td>-</td></tr>')
    a(f'<tr><td>smoke</td><td>TTFT</td><td class="num">0.4270 s</td><td class="num">0.4160 s</td><td class="num">{d_smoke_ttft}</td></tr>')
    a(f'<tr><td>smoke</td><td>decode</td><td class="num">223.70 tok/s</td><td class="num">222.78 tok/s</td><td class="num">{d_smoke_tps}</td></tr>')
    a(f'<tr><td>cell: 8 users, 256 generated tokens</td><td>TTFT (mean of 8 users)</td><td class="num">3.1549 s</td><td class="num">3.1625 s</td><td class="num">{d_cell_ttft}</td></tr>')
    a(f'<tr><td>cell</td><td>decode per user (mean of 8)</td><td class="num">125.39 tok/s</td><td class="num">123.65 tok/s</td><td class="num">{d_cell_tps}</td></tr>')
    a('</tbody></table>')
    a('<p>One run per arm. No spread is available, so none of the four deltas can be separated from run-to-run noise. The token identity is the strongest of the five results: the FPGA scored every position from 127 on from the staged bytes, and 128 greedy steps agreed. The results folder without &quot;-models&quot; in its name (exec/results/vnnik4-20260915) holds no FPGA cell. Every later campaign (vnnik5, vnnik6) ran CPU attention only.</p>')

    a('<h2>6. Cost that is unmeasured</h2>')
    a('<ul>')
    a('<li><span class="tag risk">risk</span><b>Cache lines per staged row.</b> The gather reads 64 distinct 64-byte lines per token and KV head (one dword from each pair row), then writes 256 bytes of scratch that the shuffle re-reads. The old path read 4 lines straight from the page. The useful bytes are the same, 256 bytes per token and head.</li>')
    a('<li><span class="tag risk">risk</span><b>Where it runs.</b> populate is called from the GOF rodeo. Attention workers drain up to 4 GOFs each at the start of every attention job. The forward thread drains the rest in wait_for_coop_gof, after the plugin run and before logits [h/tron/models/model.hpp:3179-3188]. That tail is inside the measured TTFT. It also fires again after every staging eviction.</li>')
    a('<li><span class="tag gap">gap</span><b>Size, estimated only.</b> The design page&#39;s figure is est. 1 us per GOF and layer. For a 1024-token prompt over 36 layers that is 9216 GOFs and est. 9 ms per prompt. The measured cell TTFT delta was +7.6 ms with n = 1, which is the same order but proves nothing on its own. The perfetto spans gof_populate and wait_coop_gof exist in the code and would settle it.</li>')
    a('<li><span class="tag risk">risk</span><b>Decode tail cost.</b> In FPGA decode the CPU scores only the tail tokens of each step. The VNNI reader prices a 16-token block with one live token at the full block cost. The cell&#39;s -1.4% decode delta could be this effect or noise, and one run cannot tell.</li>')
    a('</ul>')

    a('<h2>7. Coverage gaps and CI status</h2>')
    a('<ul>')
    a('<li><span class="tag gap">gap</span><b>No unit test asserts the staged bytes through the real lambda.</b> The GOF tests build page_info from synthetic row buffers and ignore the scratch argument [t/t_gof_dma.cpp:347; t/t_gof_staging_leaks.cpp:137; t/t_phase1_integration.cpp:890]. They pass for any k_head_fn semantics. The gather itself is tested at page level only.</li>')
    a('<li><span class="tag gap">gap</span><b>No FPGA run at the head.</b> The one FPGA run used dc950be5f2 against the PR 3879 binary, not ff680c8020 against main (c7844ca2ce). The staging code is identical between the two commits, so the residual risk is a build-level regression, not a logic difference.</li>')
    a('<li><span class="tag gap">gap</span><b>The PR&#39;s CI lane cannot test the VNNI layout on an FPGA.</b> The default lane gcp-nix.yml builds the test runtime without TRON_K_VNNI and without TRON_AMX_DISPATCH [nix/cmake-tron-test-build.nix:80-102]. So its Test FPGA job runs the row-major layout. The legacy lane cmake-single-platform.yml carries -DTRON_K_VNNI=ON [.github/workflows/cmake-single-platform.yml:330-335] but has only manual and workflow_call triggers.</li>')
    a('<li><span class="tag gap">gap</span><b>The head&#39;s CI run skipped the build and test jobs.</b> PR 4424 is a draft with the label &quot;Skip benchmarks&quot; and without &quot;Run CI&quot;. GCP Nix run 35046296975 at ff680c8020 (2026-09-16 02:00 UTC) ran the lint and machinery checks and skipped Build Tron, Test host, Test FPGA and Benchmark (checked with gh on 2026-09-16).</li>')
    a('<li><span class="tag gap">gap</span><b>Relocation under VNNI is untested.</b> No test or run covered page relocation with a VNNI slot while GOF staging is rebuilt.</li>')
    a('<li><span class="tag fact">fact</span><b>No reviewer has raised the FPGA question.</b> PR 4424 has zero reviews and zero comments as of 2026-09-16.</li>')
    a('</ul>')

    a('<h2>8. What would close the question</h2>')
    a('<ol>')
    a('<li>FPGA cells (USE_HW_ATTN unset) base = main c7844ca2ce against head ff680c8020, qwen-3-4b tp2 and llama-3.1-8b tp2, prompt 1024, at least 3 paired repetitions, greedy token comparison, TTFT and TPS. Decision rule written before the run.</li>')
    a('<li>A perfetto trace of the same cells with the categories hwattention and hwattention-detail, comparing the gof_populate and wait_coop_gof span totals between the two binaries. This isolates the gather cost from the rest of the PR.</li>')
    a('<li>A Catch2 test that builds a page_info from a real VNNI page through the scheduler&#39;s factory, runs gof::populate, and compares the hwcacheblock bytes to those produced from a row-major page with the same rows.</li>')
    a('<li>For CI: either add TRON_K_VNNI to the Nix test build, or run the legacy CMake lane by hand on the branch with Run CI set, so that Test FPGA executes the VNNI build once before merge.</li>')
    a('</ol>')

    a('<h2>Appendix A. Which reader runs where</h2>')
    a('<p>The build options and the kill switch decide which K reader runs on the CPU. In an FPGA run the CPU-scored share follows the same tree. Corrections to a first draft of this tree are marked.</p>')
    a('<pre>' + TREE + '</pre>')

    a('<h2>Appendix B. Method</h2>')
    a('<p>Six independent readers traced one question each at head ff680c8020 with read-only tools: every consumer of K bytes on the FPGA path, gate consistency, concurrency and completion, tests and measurements, cost, and the written claims in the PR body, the issue and the design pages. They returned 98 findings with file and line evidence. Each finding was then attacked by three verifiers with distinct lenses (code, data, edge cases) that were told to refute it with concrete counter-evidence. 83 findings survived all three. The 15 that fell were corrected, not dropped, and the corrections are in this page. Examples: the claim that the CI lane runs FPGA tests on the VNNI build fell because that lane has no automatic trigger. The claim that the GOF tests are the only end-to-end coverage fell because the fpga-labelled ingest tests do drive the real lambda, but only in a lane that did not run. The claim that FPGA staging waits for position 127 fell because staging runs for every complete GOF once a shard exists. 300 agents, 34 million tokens, 2 hours 11 minutes.</p>')
    a('<p class="small">Palette: the reference categorical slot 2 orange for the VNNI arm and the de-emphasis gray for the base arm, as in the other status pages of this folder. The palette validator (node) was not available on this host, so the pair was not re-validated here. Colors never carry meaning alone: every value is written next to its dot.</p>')
    a('</body></html>')
    html = "\n".join(H)
    # ASCII assertion
    bad = [(i, c) for i, c in enumerate(html) if ord(c) > 127]
    if bad:
        print("NON-ASCII at", bad[:5]); sys.exit(1)
    open(OUT, "w").write(html)
    print("wrote", OUT, len(html), "chars")

TREE = """if TRON_AMX_DISPATCH == ON:
   if TRON_K_VNNI == ON:
      AMX code and VNNI-K code are compiled to binary
      K of 128-dim heads is VNNI layout (every leaf below); other head sizes stay row-major
      FPGA staging: k_head_fn gathers each token's row into scratch (get_k_row); HBM bytes unchanged
      if TRON_AMX_DISABLE == 1:
         AMX kernels never dispatched (available() returns false, amx_q_packed stays null)
         Reader = k_vnni::qk_group on every page          &lt;- corrected: NOT the pre-PR3879 dotter
                  (the row-major dotter is not compiled for VNNI slots; fp32 add order differs)
         Heads != 128 (gpt-oss, 64-dim): row-major K, row-major dotter, as before PR3879
      else:
         AMX runs only where all of these hold:
            head 128, kv_mul 4, bf16 activation executor, AMX hardware + OS permission,
            page dense (all 64 tokens present and visible)
            -&gt; qk_vnni_128x4 reads the VNNI plane directly, no transposing store
         Every other pair: k_vnni::qk_group (partial pages; kv_mul 8 models such as
            qwen-3-30b-a3b take qk_group on every page; hosts without AMX too)
         Heads != 128: row-major K, row-major dotter, no AMX
   else:
      AMX code is compiled to binary
      VNNI-K code is not compiled to binary (layout_on == false for every head size)
      K is row-major (all heads); FPGA staging returns a pointer into the page, as before
      if TRON_AMX_DISABLE == 1:
         AMX kernels never dispatched
         Reader = row-major dotter on every page = pre-PR3879 AVX attention, same layout, same numerics
         (the only true rollback to pre-PR3879 numerics inside an AMX binary)
      else:
         PR3879 as merged: AMX on dense eligible pages (qk_rowmajor_128x4 + transposing store),
         row-major dotter on every other pair
else:
   if TRON_K_VNNI == ON:
      cmake configure fails: FATAL_ERROR "TRON_K_VNNI requires TRON_AMX_DISPATCH=ON"
      (configure time, not compile time; no binary is produced)
   else:
      Neither AMX code nor VNNI-K code is compiled to binary
      K is row-major; AVX (pre-PR3879 version) runs; TRON_AMX_DISABLE has no effect

USE_HW_ATTN is an orthogonal axis. Unset, the FPGA scores query positions 127 and up,
and positions 0 to 126 of every sequence follow the same tree on the CPU."""

if __name__ == "__main__":
    page()
