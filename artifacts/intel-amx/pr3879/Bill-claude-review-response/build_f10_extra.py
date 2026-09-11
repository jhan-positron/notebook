#!/usr/bin/env python3
"""Builds f10_extra.html: the 'code at the latest head' sub-section of finding 10.
Reads h/tron/models/self_attention.hpp from git at HEAD_SHA (read-only) so every excerpt is the real text."""
import html, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.expanduser("~/workspace/tron-amx")
HEAD_SHA = "47f6f2dceb"
FILE = "h/tron/models/self_attention.hpp"
src = subprocess.run(["git", "-C", TREE, "show", f"{HEAD_SHA}:{FILE}"], check=True, capture_output=True, text=True).stdout.splitlines()
E = html.escape

def lines(a, b, drop_comments=False, keep=None):
    """Numbered excerpt a..b (1-based, inclusive). drop_comments removes full-line // comments; keep = set of line numbers to force-keep."""
    out = []; dropped = 0
    for n in range(a, b + 1):
        t = src[n - 1]
        if drop_comments and t.strip().startswith("//") and not (keep and n in keep):
            dropped += 1
            continue
        if dropped:
            out.append(f"{'':>5}  ... {dropped} comment line{'s' if dropped > 1 else ''} omitted"); dropped = 0
        out.append(f"{n:>5}  {t.rstrip()}")
    if dropped:
        out.append(f"{'':>5}  ... {dropped} comment line{'s' if dropped > 1 else ''} omitted")
    return "<pre>" + E("\n".join(out)) + "</pre>"

# ---- block table
blocks = [
    (0, "29-35", "#if/#error guard", "Refuses the AMX option when TRON_CHUNK_SIZE is not 16 (the pair-interleaved V layout the PV kernel reads exists only then). A build-configuration check, not dispatch; it is counted separately."),
    (1, "277-285", "Type: amx_qpack_slot", "The 4096-byte, 64-byte-aligned buffer that holds one token's packed query group. A declaration."),
    (2, "299-308", "Member: attn_accum::amx_qpack", "One slot per token of the minibatch, inside the per-worker scratchpad struct. A declaration; an unconditional member would put a 24-byte std::vector with a non-trivial destructor into every attn_accum of the OFF build."),
    (3, "1320-1355", "Prologue of apply_page_range", "The compile-time gate (eligible), the run-time gate (available()), the scratchpad alias, the packed bitset, resize plus begin_region(), and the tron::finally guard that releases the tile configuration on every exit."),
    (4, "1390-1397", "In-loop pack", "Inside the page loop and the token loop: on a token's first page, copy its 4 query heads into the tile layout. Nest: #ifdef, then if constexpr, then if."),
    (5, "1421-1551", "Three helper definitions", "packed_amx_query (:1428), is_dense_amx_page (:1451) and apply_dense_amx_page (:1475): the whole dense-page path in one function. 131 lines; the only block that calls the kernel entry points."),
    (6, "1598-1621", "Gate and call in apply_page_tok", "If this executor's scalar and shape are eligible (compile time) and this (query, page) pair has a packed Q and a dense page (run time), run apply_dense_amx_page and return; otherwise fall through to the dotter loop. Nest: #ifdef, then if constexpr, then if."),
]
def span(r):
    a, b = r.split("-"); return int(b) - int(a) + 1
total_lines = sum(span(r) for _, r, _, _ in blocks)

rows = "".join(f'<tr><td>{"guard" if i == 0 else i}</td><td><span class="cite">{E(FILE)}:{r}</span> ({span(r)} lines)</td><td>{E(what)}</td><td>{E(why)}</td></tr>' for i, r, what, why in blocks)
table = ('<div class="tablewrap"><table><thead><tr><th>#</th><th>Where (47f6f2dceb)</th><th>What it holds</th><th>What it does and why it is behind the option</th></tr></thead><tbody>'
         + rows + "</tbody></table></div>")

# ---- code map SVG: three columns (struct, apply_page_range, apply_page_tok) plus the helper box; AMX blocks filled blue, generic code grey outline
def svg_map():
    W, H = 1000, 420
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="f10map" xmlns="http://www.w3.org/2000/svg">',
         '<title id="f10map">Where the six AMX blocks sit in self_attention.hpp</title>',
         '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:12px;fill:#1f2933}.h{font-weight:600;font-size:13px}.mu{fill:#52606d;font-size:11px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:10.5px;fill:#52606d}</style>',
         '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52606d"/></marker></defs>']
    def box(x, y, w, h, label, sub, amx):
        fill = "#dbe7f7" if amx else "#ffffff"; stroke = "#2b6cb0" if amx else "#9aa5b1"
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="{1.5 if amx else 1}"/>')
        s.append(f'<text x="{x+8}" y="{y+16}" class="{"h" if amx else ""}">{E(label)}</text>')
        if sub: s.append(f'<text x="{x+8}" y="{y+30}" class="mono">{E(sub)}</text>')
    def col(x, y, title, sub):
        s.append(f'<text x="{x}" y="{y}" class="h">{E(title)}</text>'); s.append(f'<text x="{x}" y="{y+14}" class="mono">{E(sub)}</text>')
    # column 1: file top + struct
    col(20, 24, "File top and attn_accum", ":29-35, :277-308")
    box(20, 44, 220, 36, "guard: #error (chunk != 16)", ":29-35", True)
    box(20, 92, 220, 36, "1  type amx_qpack_slot", ":277-285", True)
    box(20, 140, 220, 36, "2  member amx_qpack", ":299-308", True)
    box(20, 200, 220, 36, "other attn_accum members", "v_star, s_star, m_star ...", False)
    # column 2: apply_page_range
    col(260, 24, "apply_page_range", ":1284-1419")
    box(260, 44, 240, 36, "3  prologue: gates, slots, region", ":1320-1355", True)
    box(260, 92, 240, 36, "for each page", ":1356", False)
    box(280, 140, 220, 36, "for each token", ":1363", False)
    box(300, 188, 200, 36, "4  pack Q (first page)", ":1390-1397", True)
    box(300, 236, 200, 36, "call apply_page_tok", ":1398-1400", False)
    box(260, 296, 240, 36, "end of loops; guard releases tiles", "", False)
    # column 3: apply_page_tok
    col(540, 24, "apply_page_tok", ":1559-1701")
    box(540, 44, 230, 36, "prologue shared by both paths", "", False)
    box(540, 92, 230, 36, "6  gate: packed Q and dense?", ":1598-1621", True)
    box(540, 140, 230, 36, "dotter loop (AVX-512), unchanged", ":1622-1700", False)
    box(540, 188, 230, 36, "softmax step + v*/s*/m* update", "", False)
    # column 4: helpers
    col(800, 24, "helpers (one #ifdef block)", ":1421-1551")
    box(800, 44, 190, 36, "5a packed_amx_query", ":1428", True)
    box(800, 92, 190, 36, "5b is_dense_amx_page", ":1451", True)
    box(800, 140, 190, 76, "5c apply_dense_amx_page", ":1475-1550", True)
    s.append('<text x="808" y="192" class="mu">QK kernel, softmax step,</text>')
    s.append('<text x="808" y="206" class="mu">PV kernel, accumulator update</text>')
    # arrows
    def arrow(x1, y1, x2, y2):
        s.append(f'<path d="M {x1} {y1} L {x2} {y2}" stroke="#52606d" stroke-width="1.2" fill="none" marker-end="url(#arr)"/>')
    arrow(500, 254, 540, 112)          # call apply_page_tok -> gate
    arrow(500, 206, 800, 62)           # pack -> packed_amx_query
    arrow(770, 108, 800, 108)          # gate -> is_dense
    arrow(770, 116, 800, 164)          # gate -> apply_dense
    arrow(655, 128, 655, 140)          # gate falls through -> dotter
    # legend
    s.append('<rect x="20" y="360" width="14" height="14" fill="#dbe7f7" stroke="#2b6cb0" stroke-width="1.5"/>')
    s.append('<text x="40" y="371">compiled only with TRON_AMX_DISPATCH (the six blocks and the guard)</text>')
    s.append('<rect x="20" y="384" width="14" height="14" fill="#ffffff" stroke="#9aa5b1"/>')
    s.append('<text x="40" y="395">generic code, compiled in every build</text>')
    s.append(f'<text x="{W-16}" y="{H-8}" text-anchor="end" class="mu">h/tron/models/self_attention.hpp at 47f6f2dceb; line numbers are those of that commit</text>')
    s.append("</svg>")
    return "\n".join(s)

parts = []
parts.append('<h3>The code at the latest head, block by block</h3>')
parts.append(f'<p>This sub-section uses the latest head, <span class="cite">47f6f2dceb</span>; h/tron/models/self_attention.hpp is byte-identical there to 4290402491. "Woven" means this: the AMX path is not one module that the attention loop calls once. Pieces of it sit at six places in the file behind <code>#ifdef TRON_AMX_DISPATCH</code>, plus one <code>#error</code> guard, and two of the six sit inside the per-page, per-token loop. Together they are {total_lines} lines of a {len(src)}-line file. The map shows where they are; the table and the excerpts follow.</p>')
parts.append('<figure>' + svg_map() + '<figcaption>Blue: the six blocks and the guard, compiled only when the CMake option is on. White: the generic attention code, compiled in every build. Arrows: the call chain from the loop to the helpers. Blocks 1, 2 and 3 are declarations or set-up; blocks 4 and 6 are the two decision points inside the hot path; block 5 holds the whole dense-page computation.</figcaption></figure>')
parts.append(table)

parts.append('<h3>The excerpts</h3>')
parts.append('<p>Full-line comments are removed where marked, nothing else is changed.</p>')
parts.append('<p><strong>Guard, :29-35.</strong> A build with the AMX option and an 8-wide chunk would compile and pair the wrong V tokens, so the header refuses it at include time.</p>' + lines(29, 35, drop_comments=True))
parts.append('<p><strong>Block 1, :277-285, and block 2, :299-308.</strong> The packed-query storage: a 4096-byte slot type and one slot per token inside the worker\'s scratchpad struct. Both are declarations.</p>' + lines(277, 285, drop_comments=True) + lines(299, 308, drop_comments=True))
parts.append('<p><strong>Block 3, :1320-1355.</strong> The set-up at the top of apply_page_range: <code>amx_eligible</code> is decided at compile time from the executor\'s activation type and the attention shape; <code>amx_on</code> adds the run-time probe (CPU flags, OS permission, the TRON_AMX_DISABLE switch); then the slot vector is sized, the tile configuration is loaded, and the scope guard promises to release it.</p>' + lines(1320, 1355, drop_comments=True))
parts.append('<p><strong>Block 4, :1390-1397.</strong> Inside both loops. For each token, on the first page that passes the outer checks, the 4 query heads are copied into the tile layout; later pages reuse the copy. Three nested conditions: the preprocessor, the compile-time <code>if constexpr</code>, the run-time <code>if (amx_on)</code>.</p>' + lines(1386, 1400))
parts.append('<p><strong>Block 5, :1421-1551.</strong> One block holding three member functions: the pack helper, the dense-page predicate and the dense-page path itself. Only the heads are shown; the bodies are the 131 lines that call the kernel entry points (<code>pack_q_group_128x4</code>, <code>qk_rowmajor_128x4</code>, <code>weights_times_v_128x4</code>).</p>' + lines(1421, 1432, drop_comments=True) + lines(1449, 1456, drop_comments=True) + lines(1473, 1478) + lines(1547, 1551))
parts.append('<p><strong>Block 6, :1598-1621.</strong> In apply_page_tok, after the prologue both paths share: if the compile-time gate holds and this (query, page) pair has a packed Q and a dense page, the dense function does the whole page and the function returns; every other pair falls through to the dotter loop that starts at :1622.</p>' + lines(1598, 1622, drop_comments=True))

parts.append('<h3>What the problem is, in plain words</h3>')
parts.append('<ul>'
 '<li><strong>One file, two shapes.</strong> A default build (the option OFF, which is what a developer builds locally) compiles apply_page_range, apply_page_tok and attn_accum without these blocks; the CI lane and the AMX hosts compile them with the blocks. A rename or a signature change made while working in the OFF shape can break the ON shape without the author noticing until the CI lane runs. Finding 1 closed that gap for CI; it is still open for local builds.</li>'
 '<li><strong>Reading the hot loop means holding three conditions in mind.</strong> At blocks 4 and 6 a reader must combine the preprocessor condition, the per-geometry compile-time condition and the per-process run-time condition to know whether a line executes, and the set-up those lines rely on is 70 lines earlier (block 3) while the guard is 1,300 lines earlier.</li>'
 '<li><strong>The nesting is three deep.</strong> At the head Bill reviewed it was four to five deep, because the K-mirror choice added a further <code>#ifdef</code> inside the dispatch blocks; that layer left with the mirror.</li>'
 '</ul>')
parts.append('<p><strong>What is done.</strong> The dense-page computation is one function (block 5c), called from one place (block 6); the pack is one helper (block 5a); the region bracket is a scope guard (block 3), which removed the seventh block that used to close the region after the loop. Bill\'s "single call" half is met.</p>')
parts.append('<p><strong>What remains, and why it is not a mechanical edit.</strong> Bill\'s fix asks for "one call and no preprocessor". The statements can lose their <code>#ifdef</code>: blocks 3, 4 and 6 sit inside member function templates, so an <code>if constexpr</code> on a constexpr flag exported by the interface header (true only when the kernel translation unit is compiled) would discard the AMX branch in OFF builds without instantiating it, and the OFF build would then not reference any kernel symbol; the one trap is <code>amx_on = amx_eligible &amp;&amp; available()</code>, which must sit inside the discarded branch rather than behind <code>&amp;&amp;</code>, or an unoptimised OFF build would still need the missing available(). Block 5 could also lose its guard, because member functions of a class template are compiled only when something calls them (not verified by a build). Blocks 1 and 2 cannot: <code>if constexpr</code> is a statement, and a type and a data member are declarations. Either every attn_accum in the OFF build carries an unused 24-byte vector with a destructor, or the slot type has to depend on the build (a conditional alias, or a backend type that provides an empty slot type when the option is off). That last option is Bill\'s backend seam, which is why the page treats the preprocessor removal and the seam as one decision.</p>')
parts.append('<p><strong>What should stay.</strong> The <code>#error</code> guard, until finding 13\'s static_assert on the V byte layout replaces it: it fires at include time with a readable message, before any template is instantiated.</p>')

open(os.path.join(HERE, "f10_extra.html"), "w", encoding="utf-8").write("\n".join(parts))
print("f10_extra.html written;", total_lines, "AMX lines of", len(src))
