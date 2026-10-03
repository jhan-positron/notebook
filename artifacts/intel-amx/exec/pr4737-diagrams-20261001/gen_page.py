"""Assemble diagramming-code-changes.html for PR 4737 (kv_cache.hpp).

Run:  python3 gen_page.py [OUT_HTML]
Code excerpts come from `git diff 30c4ac82cb bb32a80774 -- h/tron/models/kv_cache.hpp`
in the tron-i4500 worktree (difflib_units.py); diagrams are inline SVG.
"""
import html
import sys

sys.path.insert(0, "/home/jhan/workspace/intel-AMX/exec/pr4737-diagrams-20261001")
from difflib_units import (BASE, HEAD, FILE, unit_rows, render_rows, counts,
                           blame_commits, git)
from svg_helpers import C
import diagrams_base as B
import diagrams_changes as D
from diagrams_base_b5 import b5 as _b5
B.b5 = _b5

OUT = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4500/diagramming-code-changes.html"

PROMPT = """generate diagramming-code-changes.html:
- at the top, include this prompt literally
- have Table of Content at top
- use diagrams to explain code changes of PR4737
- each code change has at least 1 diagrams
- definition of "1 code change": a logical unit of code change. E.g.:
--- 5 lines of code update one data model which is used by other code, these 5 lines are 1 unit and there should be a diagram illustrating the change
--- 10 lines of code checks one data model based on another model
- trivial code changes do not need diagrams, but need to be listed
- code comments which explain the code need to keep with code
- code change and its corresponding diagram are best side to side
- use consistent font/color schemes for same concepts or data models across whole file
- at start, use some base diagrams to illustrate overall data models, function models, sequencing models, interaction models, etc.
--- individual diagrams beside code changes, if use base diagrams as context, or better yet, update base diagrams, would be great.
- target file: kv_cache.hpp"""

COMMITS = {}
for ln in git("log", "--format=%h %s", f"{BASE}..{HEAD}").split("\n"):
    if ln:
        h, s = ln.split(" ", 1)
        COMMITS[h] = s

# ---------------------------------------------------------------------------
# The logical units. ranges = inclusive head line numbers shown (in this order).
# ---------------------------------------------------------------------------
UNITS = [
    dict(id="c0", title="The design note: Note [K VNNI storage] and the new "
         "Note [Row-major blocks under hardware attention]",
         kind="comment only", ranges=[(653, 808)], fig=D.d0,
         base="B1 to B5 are this note drawn. D0 maps its paragraphs to them.",
         lead=[
             "This hunk is comment text. It is the design record that the code below "
             "follows, so it is listed first and shown in full.",
             "The first note gains the description of the two bit sets, the deferred "
             "conversion at the forward end, and the reason the conversion cannot run "
             "inside save_k (the staging gather of an earlier minibatch reads the block "
             "while a later minibatch saves its last rows).",
             "The second note states the policy for operations whose attention runs on "
             "the FPGA: no row bit is recorded and no block is queued, so such blocks "
             "stay row-major.",
             "The six consumer items are reworded for the new behaviour."]),
    dict(id="c1", title="The K layout state: two bit arrays per page",
         kind="new data model", ranges=[(2347, 2361), (2221, 2235), (2245, 2256),
                                        (1808, 1817), (1645, 1659)], fig=D.d1,
         base="Updates B1: the two new fields of the page struct and the block "
              "colours of the K plane.",
         lead=[
             "The page gains two arrays of atomics, one entry per storage slot plus one "
             "entry for the EAGLE storage.",
             "k_rows_saved_ holds one bit per page offset (64 bits): the K row of that "
             "offset is saved. k_vnni_blocks_ holds one bit per 16-token block (4 bits): "
             "the block holds the VNNI layout.",
             "Three constants name the extra entry and the boolean return values. "
             "k_block_bits(c) is the 16-bit mask of block c. k_block_is_vnni reads the "
             "block bit for an offset. The public k_vnni_blocks(slot) returns the whole "
             "byte for the dense gate and the software loop in self_attention.hpp.",
             "The move constructor copies both arrays, as it already did for kv_saves_.",
             "Invariant: a set block bit implies the 16 row bits of its block."]),
    dict(id="c2", title="Which state entry and which storage slot a call means",
         kind="new helpers", ranges=[(1070, 1076), (2237, 2243), (1819, 1837),
                                     (2258, 2270)], fig=D.d2,
         base="Updates B1: the EAGLE entry E and the slot row of the book.",
         lead=[
             "The EAGLE view maps logical slot 0 onto the extra physical slot "
             "(book::set_storage_view). book::eagle_view_active is new and says whether "
             "that view is selected.",
             "k_state_ix picks the state entry of a logical slot under that rule: entry "
             "n_slots for slot 0 while the view is active, the slot's own index otherwise.",
             "k_storage_ref pairs a physical storage offset with its state entry. "
             "k_storage_of builds it from a logical slot under the current view. "
             "copy_from builds it from the physical slot instead (change C8).",
             "k_with_storage_geometry calls a template lambda with the geometry of a "
             "storage slot: the slot's declared geometry, or the primary geometry for the "
             "EAGLE storage. The conversion (C4) and the clear path (C7) need it to reach "
             "the planes."]),
    dict(id="c3", title="Recording saved rows and whole-block saves",
         kind="new writers of the state", ranges=[(1839, 1882)], fig=D.d3,
         base="Updates B4: the arrows into 'complete, waits' and into 'converted'.",
         lead=[
             "note_k_row_saved sets the row's bit and returns true when the block's 16 "
             "bits are now set and the block bit is clear. save_k's row-recording loop "
             "(the loop in model.hpp that runs on the main thread after the K stores "
             "and calls note_k_row_saved for every stored token) then queues the "
             "block for the forward end.",
             "The bit is set with a relaxed load first and fetch_or only when it was "
             "clear. A row saved again into a complete block therefore costs no locked "
             "read-modify-write, and it still returns true (the conversion is idempotent).",
             "A row-major slot keeps no bits and returns false. The uniform-geometry "
             "overload forwards to the primary geometry.",
             "note_k_block_saved publishes the 16 row bits and the block bit at once. "
             "The caller runs it after the last KV head of a whole-block save."]),
    dict(id="c4", title="The in-place conversion of one block",
         kind="new", ranges=[(1884, 1920)], fig=D.d4,
         base="Updates B4 ('complete, waits' to 'converted') and B2 (the arrow between "
              "the two forms).",
         lead=[
             "k_block_to_vnni_at checks the two bit sets, converts block c of every KV "
             "head's plane with k_vnni::block_to_vnni, and sets the block bit with "
             "release order after the last head.",
             "It returns false when there is nothing to do, so a repeated call is "
             "harmless. k_block_to_vnni resolves a logical slot first (C2).",
             "Callers: convert_pending_k_blocks in model.hpp (main thread, forward end, "
             "see B5) and tests."]),
    dict(id="c5", title="Row accessors follow the block's layout",
         kind="changed + new", ranges=[(1921, 1944), (1965, 1986), (2004, 2019)],
         fig=D.d5,
         base="Updates B3 rows 1 and 6, and B2 (which form a row is read from).",
         lead=[
             "set_k_row and get_k_row branch on the block bit: scatter or gather into "
             "the VNNI column when the block is converted, a 256-byte memcpy at "
             "k_vnni::row_ptr otherwise.",
             "k_row_if_row_major is new: a pointer into a row-major block, or nullptr "
             "for a converted block. The staging callback in full.hpp uses it and copies "
             "nothing for a row-major row.",
             "None of the three touches the bits. The saved-row bit is the caller's "
             "(C3)."]),
    dict(id="c6", title="set_k_block: whole blocks only",
         kind="changed signature", ranges=[(1945, 1964)], fig=D.d6,
         base="Updates B3 row 2.",
         lead=[
             "set_k_block loses its `present` mask. It stores a whole 16-token block "
             "with FULL_BLOCK_0XFFFF.",
             "The caller, store_k_block in model.hpp, uses it only for runs of 16 tokens "
             "and records the block with note_k_block_saved after the last KV head. "
             "Shorter runs go through set_k_row (C5)."]),
    dict(id="c7", title="Forgetting rows when a new token takes an offset",
         kind="changed + new", ranges=[(2208, 2215), (2272, 2280), (2282, 2326)],
         fig=D.d7,
         base="Updates B4: the 'converted' to 'partial' arrow and the drop note.",
         lead=[
             "clear_kv_complete_at now also calls k_forget_row.",
             "For each state entry, k_forget_row drops the row bits at and above the "
             "offset and the block bits of those blocks.",
             "When the offset's block is converted and keeps rows below the offset, and "
             "the storage is readable (k_storage_readable: no KV restore in flight, slot "
             "allocated), the block is converted back to row-major first, so those rows "
             "stay readable.",
             "A decode append with nothing at or above the offset costs two loads and no "
             "locked read-modify-write."]),
    dict(id="c8", title="Page copies carry the bits with the rows",
         kind="changed", ranges=[(2468, 2541), (2565, 2572), (2574, 2591)], fig=D.d8,
         base="Updates B4 (the page-copy note) and B2 (every row crosses the row-major "
              "form).",
         lead=[
             "copy_storage_slot takes a k_storage_ref (C2) and computes the new bits once "
             "per slot. A whole-page copy stays one memcpy and copies the block bits.",
             "Any other range runs in three steps. First, the destination blocks the range "
             "touches are converted back to row-major. Second, each row is gathered from a "
             "converted source block, or copied from a row-major one, into row_ptr of the "
             "destination. Third, destination blocks whose 16 row bits are now set are converted "
             "to VNNI.",
             "The bits are stored after the last KV head. copy_from builds the refs for "
             "every active slot and for the EAGLE storage."]),
]

TRIVIAL = [
    dict(ranges=[(1793, 1806)], what="Comment of k_vnni_plane: says that only the blocks "
         "named by k_vnni_blocks hold the VNNI layout. Two lines. The function body is "
         "unchanged."),
]

GLOSSARY = [
    ("tron", "the inference program this file belongs to. PR 4737 is a pull request "
             "against it (positron-ai/tron)."),
    ("kv_cache.hpp", "the header that holds the KV cache: the book, page and kv_block "
                     "types used by every model. Path h/tron/models/kv_cache.hpp."),
    ("K, V, KV cache", "the attention keys (K) and values (V) stored per token so that "
                       "later tokens can attend to earlier ones."),
    ("book", "the unit of KV memory allocation (Note [KV Memory Layout] in kv_cache.hpp): "
             "the K and V of one run of consecutive tokens, up to n_pages pages of 64 tokens, "
             "for all layers. The scheduler's token tree owns many books, and a branch "
             "starts a new one."),
    ("storage slot, logical slot", "the K/V storage of one layer (n_slots == n_layers). "
     "A logical slot is what callers name. A physical storage offset is where the bytes "
     "are. They differ only under the EAGLE view."),
    ("EAGLE", "a speculative-decoding draft model. Its KV storage is an extra physical "
              "slot of the book. The EAGLE view maps logical slot 0 onto it."),
    ("page, offset", "64 consecutive token positions of a sequence. An offset is a "
                     "position 0..63 inside the page."),
    ("KV head", "one attention head of the K/V side. A slot has n_kv_heads of them."),
    ("K plane", "the K storage of one (slot, KV head, page): 64 tokens x 128 dims of "
                "bf16 = 16 KiB."),
    ("block", "16 consecutive offsets of a page (page offsets 16 c .. 16 c + 15). A page "
              "has 4 blocks, c = 0..3."),
    ("panel", "1 KiB of the K plane. In the VNNI form it is one AMX tile (16 pair rows of 64 "
              "bytes). In the row-major form it holds four 256-byte token rows."),
    ("row-major", "a token's 128 values are contiguous (256 bytes)."),
    ("VNNI layout", "Vector Neural Network Instructions layout: the two values of a "
                    "dimension pair sit next to each other, and one 64-byte row holds "
                    "that pair for 16 tokens. It is the B-operand layout of the AMX tile "
                    "multiply."),
    ("AMX, AVX-512", "Advanced Matrix Extensions (tile instructions) and Advanced Vector "
                     "Extensions (512-bit vectors) of the Intel CPU."),
    ("bf16, fp32", "bf16 is the 16-bit brain floating-point format. fp32 is the 32-bit IEEE float."),
    ("dotter", "the per-token dot-product loop of self_attention.hpp (row-major reader)."),
    ("qk_group", "the AVX-512 reader of the VNNI blocks in k_vnni.hpp (one token per lane)."),
    ("dense AMX path, k_layout_dense", "the AMX kernel that scores a whole page at once. "
     "Its third gate (self_attention.hpp) requires all 4 block bits set."),
    ("hardware attention, FPGA", "attention computed on the field-programmable gate array "
     "card instead of the CPU. The operation flag is cached_operation_uses_hw in "
     "model.hpp."),
    ("GOF, staging, DMA", "a group of four consecutive tokens. gof::populate copies their "
     "K/V rows into a buffer (staging) that direct memory access moves to the card."),
    ("forward pass, minibatch", "one model execution over the tokens of a step. A pass "
     "may hold several minibatches (grains of 8 tokens)."),
    ("main thread, main helpers, attention workers, scheduler thread", "in order: the thread that "
     "runs the plugin's forward. The helpers it shares a block save with (Note [Shared "
     "block save] in model.hpp). The threads that run attention sections. The thread that "
     "assigns tokens and copies pages between passes under the token tree lock."),
    ("latch", "the counter the attention workers wait on until every writer minibatch "
              "of a page has stored its K and V."),
    ("TRON_K_VNNI", "the build option that turns the VNNI K layout on (128-dimension "
                    "heads only: k_vnni::layout_on)."),
    ("TRON_AMX_DISABLE (kill switch)", "runtime switch: the VNNI binary runs the AVX-512 "
     "reader instead of the AMX kernel. The layout stays."),
    ("acquire, release, fetch_or, fetch_and", "C++ atomic memory orders and locked "
     "read-modify-write (RMW) operations on the bit words. An atomic is a variable that "
     "several threads may read and write without a lock."),
    ("row-recording loop of save_k", "the loop in save_k (model.hpp) that runs on "
     "the main thread after the K stores and the helper join: for every stored token "
     "it calls note_k_row_saved, and when that returns true it pushes the token's "
     "block onto pending_k_blocks_ for the forward-end conversion. Skipped for "
     "operations the hardware attention scores. A name used on this page only."),
    ("hunk", "one contiguous changed region of a diff. This file's diff has 15."),
    ("idempotent", "a repeated call changes nothing more than the first one did."),
    ("C0..C8, T1, B1..B5, D0..D8", "the ids used on this page: logical changes, the "
     "trivial change, base diagrams, per-change diagrams."),
]

CSS = f"""
:root{{--bg:#fbfbf9;--fg:#1f2937;--muted:#6b7280;--line:#d6d9de;--soft:#f3f5f8;
--rm:{C['rm']};--rm-fill:{C['rm_fill']};--vnni:{C['vnni']};--vnni-fill:{C['vnni_fill']};
--pend:{C['pend']};--rows:{C['rows']};--rows-fill:{C['rows_fill']};--blk:{C['blk']};
--blk-fill:{C['blk_fill']};--hw:{C['hw']};--hw-fill:{C['hw_fill']};--eagle:{C['eagle']};
--eagle-fill:{C['eagle_fill']};--new:{C['new']};color-scheme:light}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.5;margin:0;padding:24px 16px}}
main{{max-width:1480px;margin:0 auto}}
h1{{font-size:26px;line-height:1.25;margin:0 0 8px}}
h2{{font-size:21px;margin:40px 0 10px;padding-top:8px;border-top:2px solid var(--line)}}
h3{{font-size:17px;margin:28px 0 6px}}
h4{{font-size:14px;margin:14px 0 4px;color:var(--muted)}}
p{{max-width:90ch}}
code,pre,.mono{{font-family:ui-monospace,Menlo,Consolas,"DejaVu Sans Mono",monospace}}
code{{font-size:.92em;background:var(--soft);padding:0 3px;border-radius:3px}}
.meta{{color:var(--muted);font-size:13px;max-width:none}}
.short{{background:#eef6ff;border-left:4px solid #2a78d6;padding:10px 14px;max-width:100ch}}
.note{{background:#fff8e6;border-left:4px solid #e0a800;padding:8px 12px;max-width:100ch}}
pre{{background:var(--soft);padding:10px;overflow-x:auto;font-size:12.5px;line-height:1.4;white-space:pre}}
pre.prompt{{white-space:pre-wrap;border-left:4px solid var(--muted);max-width:none}}
pre.diff{{padding:6px 0;font-size:11.6px;line-height:1.38;white-space:pre;background:#fff;border:1px solid var(--line)}}
.row{{display:block;padding:0 8px 0 0;white-space:pre}}
.row.add{{background:#e6ffec}}
.row.del{{background:#ffebe9}}
.row .ln{{display:inline-block;width:3.6em;text-align:right;padding-right:.6em;color:var(--muted);user-select:none}}
.row .sg{{display:inline-block;width:1.1em;color:var(--muted);user-select:none}}
.gap{{display:inline-block;color:var(--muted);padding-left:.4em}}
.row.gaprow{{background:var(--soft)}}
pre.diff .ln:first-child{{border-right:1px solid var(--line)}}
.side{{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:18px;align-items:start}}
@media (max-width:980px){{.side{{grid-template-columns:1fr}}}}
.fig{{position:sticky;top:12px}}
figure{{margin:0 0 10px;max-width:100%}}
figure svg{{width:100%;height:auto;display:block;background:#fff;border:1px solid var(--line);border-radius:6px}}
figcaption{{font-size:13px;color:var(--muted);max-width:none;margin-top:6px}}
.unit{{margin:26px 0 40px;padding-top:4px}}
.unit header{{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline}}
.tag{{display:inline-block;font-size:11.5px;padding:1px 8px;border-radius:10px;background:var(--soft);border:1px solid var(--line);color:var(--muted)}}
.tag.new{{color:var(--new);border-color:var(--new)}}
.base{{font-size:13px;color:var(--muted);margin:4px 0 10px}}
table{{border-collapse:collapse;font-size:13px}}
th,td{{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}}
th{{background:var(--soft)}}
.tbl{{overflow-x:auto;max-width:100%}}
dl.words{{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:14px;max-width:110ch}}
dl.words dt{{font-weight:600}}dl.words dd{{margin:0}}
@media (max-width:700px){{dl.words{{grid-template-columns:1fr}}}}
nav.toc ol{{columns:2;column-gap:32px;max-width:110ch;font-size:14px}}
@media (max-width:760px){{nav.toc ol{{columns:1}}}}
nav.toc li{{break-inside:avoid}}
.chips{{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:13px;align-items:center}}
.chip{{display:inline-block;width:26px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:6px;border:1.4px solid}}
.top{{font-size:12px;color:var(--muted);text-decoration:none;margin-left:8px}}
.lead li{{max-width:90ch;margin-bottom:4px}}
"""


def chip(fill, stroke, dashed=False):
    d = "border-style:dashed;" if dashed else ""
    return f'<span class="chip" style="background:{fill};border-color:{stroke};{d}"></span>'


def unit_html(u, n):
    rows = unit_rows(u["ranges"])
    add, dele = counts(rows)
    commits = blame_commits(u["ranges"])
    rng = ", ".join(f"{a}-{b}" for a, b in u["ranges"])
    lead = "".join(f"<li>{html.escape(s)}</li>" for s in u["lead"])
    com = " ".join(f'<code title="{html.escape(COMMITS.get(c, ""))}">{c}</code>' for c in commits)
    tag_cls = "tag new" if u["kind"].startswith("new") else "tag"
    return f"""
<article class="unit" id="{u['id']}">
<header><h3>{u['id'].upper()}. {html.escape(u['title'])}<a class="top" href="#toc">top</a></h3>
<span class="{tag_cls}">{html.escape(u['kind'])}</span>
<span class="tag">head lines {rng}</span>
<span class="tag">+{add} / -{dele} lines</span></header>
<p class="meta">Commits that last touched these lines (hover for the subject): {com}</p>
<ul class="lead">{lead}</ul>
<p class="base"><b>Base diagram updated:</b> {html.escape(u['base'])}</p>
<div class="side">
<div class="code"><pre class="diff">{render_rows(rows)}</pre></div>
<div class="fig">{u['fig']()}</div>
</div>
</article>"""


def build():
    toc_units = "".join(
        f'<li><a href="#{u["id"]}">{u["id"].upper()}. {html.escape(u["title"])}</a></li>'
        for u in UNITS)
    words = "".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(d)}</dd>" for t, d in GLOSSARY)
    units = "".join(unit_html(u, i) for i, u in enumerate(UNITS))
    triv_rows = ""
    for t in TRIVIAL:
        rows = unit_rows(t["ranges"])
        a, d = counts(rows)
        rng = ", ".join(f"{x}-{y}" for x, y in t["ranges"])
        triv_rows += (f'<article class="unit" id="t1"><header><h3>T1. Comment of k_vnni_plane'
                      f'<a class="top" href="#toc">top</a></h3><span class="tag">comment only</span>'
                      f'<span class="tag">head lines {rng}</span><span class="tag">+{a} / -{d} lines'
                      f'</span></header><p>{html.escape(t["what"])}</p>'
                      f'<pre class="diff">{render_rows(rows)}</pre></article>')
    xref = ""
    for u in UNITS:
        rows = unit_rows(u["ranges"])
        a, d = counts(rows)
        rng = "<br>".join(f"{x}-{y}" for x, y in u["ranges"])
        com = "<br>".join(f"<code>{c}</code> {html.escape(COMMITS.get(c, ''))}"
                          for c in blame_commits(u["ranges"]))
        xref += (f'<tr><td><a href="#{u["id"]}">{u["id"].upper()}</a></td>'
                 f'<td>{html.escape(u["title"])}</td><td class="mono">{rng}</td>'
                 f'<td>+{a} / -{d}</td><td>{com}</td><td>{html.escape(u["base"])}</td></tr>')
    commits_list = "".join(f"<li><code>{h}</code> {html.escape(s)}</li>" for h, s in COMMITS.items())

    legend = f"""
<div class="chips">
<span>{chip(C['vnni_fill'], C['vnni'])}converted block: VNNI layout (block bit set)</span>
<span>{chip(C['pend_fill'], C['pend'], True)}complete block, not converted (16 row bits, block bit clear)</span>
<span>{chip(C['rm_fill'], C['rm'])}row-major rows (some row bits)</span>
<span>{chip(C['empty_fill'], C['empty'], True)}no row saved</span>
<span>{chip(C['hw_fill'], C['hw'])}row-major, no bits: hardware-scored operation</span>
<span>{chip(C['rows_fill'], C['rows'])}k_rows_saved_ bit set</span>
<span>{chip(C['blk_fill'], C['blk'])}k_vnni_blocks_ bit set</span>
<span>{chip(C['eagle_fill'], C['eagle'])}EAGLE storage / entry E</span>
<span><span class="chip" style="background:#e6ffec;border-color:#9fd3ad"></span>added line (head)</span>
<span><span class="chip" style="background:#ffebe9;border-color:#e0a6a0"></span>removed line (base)</span>
</div>
<p class="meta">Identifiers are set in monospace in prose, code and diagrams. Every diagram
uses the same block colours and bit colours. A dashed outline means "waiting" or "no bytes
saved". Thread names appear in brackets on arrows. The worked example of B1 (page 7, slot 5,
offsets 0..40 saved) is reused by D1, D3, D7 and D8.</p>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PR 4737 kv_cache.hpp diagrams</title>
<meta name="description" content="Diagrams of every logical code change PR 4737 makes to kv_cache.hpp">
<style>{CSS}</style></head>
<body><main>
<h1>PR 4737 in kv_cache.hpp: every code change, diagrammed</h1>
<p class="meta">tron PR <a href="https://github.com/positron-ai/tron/pull/4737">#4737</a>
"Keep short K-cache writes row-major to avoid VNNI decode overhead" &middot; base branch
<code>jhan-amx-vnniK</code> at <code>{BASE}</code> &middot; head <code>jhan-amx-vnniK-i4500</code>
at <code>{HEAD}</code> &middot; file <code>{FILE}</code>: 2720 lines at the base, 3149 at the head, 484 lines added, 55 removed, in 15 hunks &middot; page generated 2026-10-01 by
<code>exec/pr4737-diagrams-20261001/gen_page.py</code>.</p>

<section id="prompt"><h2>The request (verbatim)</h2>
<pre class="prompt">{html.escape(PROMPT)}</pre></section>

<nav class="toc" id="toc"><h2>Table of contents</h2><ol>
<li><a href="#short">Short version</a></li>
<li><a href="#words">Words used here</a></li>
<li><a href="#legend">Colour and font scheme</a></li>
<li><a href="#base">1. Base diagrams</a>
<ol><li><a href="#b1">B1 data model</a></li><li><a href="#b2">B2 one block, two layouts</a></li>
<li><a href="#b3">B3 function model</a></li><li><a href="#b4">B4 sequencing model</a></li>
<li><a href="#b5">B5 interaction model</a></li></ol></li>
<li><a href="#changes">2. Code changes, each beside its diagram</a><ol>{toc_units}</ol></li>
<li><a href="#trivial">3. Trivial changes (listed, no diagram)</a></li>
<li><a href="#xref">4. Cross-reference: change, lines, commits, base diagram</a></li>
<li><a href="#method">5. How this page was made and checked</a></li>
</ol></nav>

<section id="short"><h2>Short version</h2>
<p class="short">PR 4737 changes kv_cache.hpp so that a 16-token K block stays row-major
until all 16 of its rows are saved, and is transposed to the VNNI layout in place afterwards
(or never, for operations the FPGA scores). The page gains two bit sets per storage slot that
record saved rows and converted blocks, and every K reader and writer in the file now follows
those bits. This page draws the data model, the call graph and the timing once (section 1),
then shows each of the nine logical changes of the file next to the diagram it alters
(section 2).</p></section>

<section id="words"><h2>Words used here</h2>
<dl class="words">{words}</dl></section>

<section id="legend"><h2>Colour and font scheme</h2>{legend}</section>

<section id="base"><h2>1. Base diagrams</h2>
<p>Five diagrams carry the context that every change below refers to. B1 is the data model,
B2 the two byte layouts of one block, B3 the function model (who calls what), B4 the sequencing
model (the life of one block) and B5 the interaction model (which thread touches the state
when). The per-change diagrams D0 to D8 in section 2 reuse their shapes and colours and say
which base diagram they update.</p>
<h3 id="b1">B1. Data model: book, page, kv_block, and the new per-page state</h3>
<p>The two arrays this PR adds live in the page struct and have one entry per storage slot
plus one for the EAGLE storage. They describe the K plane of every KV head of that slot in
that page. B1 also fixes the worked example that the later diagrams reuse.</p>
{B.b1()}
<h3 id="b2">B2. One block, two layouts in the same bytes</h3>
<p>The K plane of one (slot, KV head, page) is 16 panels of 1 KiB. A block owns four of them,
4 KiB apart. The PR lets those four panels hold either 16 row-major token rows or the VNNI
form, and converts between the two in place (k_vnni.hpp, outside this file). The page's block
bit says which form a block holds.</p>
{B.b2()}
<h3 id="b3">B3. Function model: callers, page API, kernels</h3>
<p>Each row is one call path through kv_cache.hpp. The tags mark what the PR adds or changes.
The private helpers at the bottom are shared by the rows above them.</p>
{B.b3()}
<h3 id="b4">B4. Sequencing model: the life of one 16-token block</h3>
<p>A block of one storage slot moves through four states. The upper path is the decode case
(one row per step). The arc over the top is the prefill case (a whole block at once). The
lower path is the hardware-attention policy, under which a block never converts.</p>
{B.b4()}
<h3 id="b5">B5. Interaction model: threads over one forward pass</h3>
<p>The diagram shows why the conversion waits for the forward end. Durations are not to
scale. The order is what matters.</p>
{B.b5()}
</section>

<section id="changes"><h2>2. Code changes, each beside its diagram</h2>
<p>A unit is one logical change: a data model and its helpers, one function's new behaviour,
one call path. Each unit shows the head code with its comments (added lines green, removed
base lines red, head line numbers in the second column, base line numbers in the first) and,
beside it, the diagram that updates a base diagram. Units are ordered by dependency: the state
(C1), how it is addressed (C2), who writes it (C3), the conversion (C4), the readers and writers
of rows (C5, C6), the clear path (C7) and page copies (C8). The design note (C0) comes first
because the code follows it.</p>
{units}
</section>

<section id="trivial"><h2>3. Trivial changes (listed, no diagram)</h2>
<p>Changes that alter no behaviour and need no picture. The named constants of C1 and the
argument-type changes of copy_from (C8) are listed inside their units.</p>
{triv_rows}
<ul>
<li>Blank separator lines between the new functions: 9 of the 484 added lines (head lines 1818,
1838, 1883, 2236, 2244, 2257, 2271, 2281, 2362).</li>
<li>The <code>(void)slot;</code> and the <code>requires(layout_t::uniform_geometry)</code> overload
inside note_k_row_saved (C3): compiler-silencing and a forwarding overload.</li>
<li>Comment-only edits inside other units: the set_k_row and get_k_row comments (C5), the
set_k_block comment (C6), the copy_storage_slot comments (C8) and the consumer list of the
note (C0).</li>
</ul></section>

<section id="xref"><h2>4. Cross-reference</h2>
<div class="tbl"><table><thead><tr><th>id</th><th>change</th><th>head lines</th><th>+ / -</th>
<th>commits that last touched the added lines</th><th>base diagram updated</th></tr></thead>
<tbody>{xref}</tbody></table></div>
<h4>The 14 commits of the PR (newest first); 8 touch kv_cache.hpp</h4>
<ul>{commits_list}</ul></section>

<section id="method"><h2>5. How this page was made and checked</h2>
<ul>
<li>Source of every code excerpt: <code>git diff {BASE} {HEAD} -- {FILE}</code> in the
worktree VNNIed-K-in-place/tron-i4500, parsed by <code>difflib_units.py</code>. Context lines
come from the head file, so a unit can show a whole function. The parser's totals (484 added,
55 removed) match <code>git diff --stat</code> (539 changed lines).</li>
<li>Thread and ordering facts in the diagrams come from the comments in the diff itself
(Note [K VNNI storage] lines 672-721, Note [Row-major blocks under hardware attention] lines
723-759, and the function comments) and from the callers' diffs in model.hpp,
self_attention.hpp and full.hpp of the same PR.</li>
<li>The worked example (page 7, slot 5, offsets 0..40 saved) is an illustration, not a
measurement. No performance number appears on this page. Those live in
issue4500/policy-4500.html and round2-4500.html.</li>
<li>Every SVG was rendered to PNG with cairosvg and inspected for clipped or overlapping
labels before delivery (<code>render_check.py</code>).</li>
</ul></section>
</main></body></html>
"""


if __name__ == "__main__":
    page = build()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    non_ascii = sum(1 for ch in page if ord(ch) > 127)
    print(OUT, len(page), "bytes;", "non-ascii chars:", non_ascii)
