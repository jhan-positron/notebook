"""Shared page skeleton of the three PR 4959 diagram pages (copied from exec/pr4424-diagrams-20261009 and adapted).

A page spec (spec_<file>.py) names the file, the logical units (head line
ranges, titles, lead bullets, which base diagram each one updates), the
trivial changes, the glossary, the base diagrams and the per-change diagram
functions. build(spec) returns the HTML. The code excerpts come from
difflib_units.DiffFile (never hand-transcribed).
"""
import html
import sys

sys.path.insert(0, "/home/jhan/workspace/intel-AMX/exec/pr4959-diagrams-20261016")
from difflib_units import DiffFile, render_rows, counts, git, BASE, HEAD, WT  # noqa: E402
from svg_helpers import C  # noqa: E402

PR_URL = "https://github.com/positron-ai/tron/pull/4959"
PR_TITLE = "Keep short K writes row-major; enable VNNI K in the deb preset"

PROMPT = """generate diagramming-code-changes.html:
- at the top, include this prompt literally
- have Table of Content at top
- use diagrams to explain the given code changes. Prompt user if no PR or branch is given
- each code change has at least 1 diagrams
- definition of "1 code change": a logical unit of code change. For example,
    - 5 lines of code update one data model which is used by other code, these 5 lines are 1 unit and there should be a diagram illustrating the change
    - 10 lines of code checks one data model based on another model
- trivial code changes do not need diagrams, but need to be listed
- code comments which explain the code need to keep with code
- code change and its corresponding diagram are best side to side
- use consistent font/color schemes for same concepts or data models across whole file; have a color and font scheme table before detailed sections
    - At each section or its diagrams, repeat `Colour and font scheme` but only include the color/font used in the section/diagrams
- at start, use some base diagrams to illustrate overall data models, function models, sequencing models, interaction models, etc.
    - individual diagrams beside code changes, if use base diagrams as context, or better yet, update base diagrams, would be great.
- no invented shorthand; take names from the code, and cite the comment or line that defines each box.
- Every function cell carries a one-line description of what the function does
- Label every arrow between data-model boxes with how many: for example, one page has n_slots entries, one entry covers n_kv_heads kv_blocks
- target files: pick the most important 3 files from code change set, each file has its own diagramming-code-changes.html with PR# and file name, e.g. diagramming-code-changes-PR123-file1.html
    - Use the given files if provided"""

PAGES = [  # the three pages, in the order the file picker ranked them
    ("h/tron/models/kv_cache.hpp", "diagramming-code-changes-PR4959-kv_cache.hpp.html",
     "the K layout state per page (saved-row bits, converted-block bits), the conversion, row accessors that follow the layout, forgetting rows, page copies"),
    ("h/tron/tensor/k_vnni.hpp", "diagramming-code-changes-PR4959-tensor-k_vnni.hpp.html",
     "Note [Row-major tail block]: the row-major form of a block and the in-place conversion block_to_vnni / block_to_rows"),
    ("h/tron/models/model.hpp", "diagramming-code-changes-PR4959-model.hpp.html",
     "the deferred conversion list, the whole-block-only block save, the row-recording loop and the hardware-attention policy"),
]

CSS = f"""
:root{{--bg:#fbfbf9;--fg:#1f2937;--muted:#6b7280;--line:#d6d9de;--soft:#f3f5f8;
--rm:{C['rm']};--rm-fill:{C['rm_fill']};--vnni:{C['vnni']};--vnni-fill:{C['vnni_fill']};
--pend:{C['pend']};--rows:{C['rows']};--rows-fill:{C['rows_fill']};--blk:{C['blk']};
--blk-fill:{C['blk_fill']};--hw:{C['hw']};--hw-fill:{C['hw_fill']};--eagle:{C['eagle']};
--eagle-fill:{C['eagle_fill']};--q:{C['q']};--q-fill:{C['q_fill']};--unit:{C['unit']};
--unit-fill:{C['unit_fill']};--new:{C['new']};color-scheme:light}}
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
.figlegend{{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--fg);margin:6px 0 2px;padding:6px 8px;background:var(--soft);border-radius:6px;align-items:center}}
.figlegend .lt{{font-weight:600;color:var(--muted);margin-right:4px}}
.figlegend .chip{{width:22px;height:12px;margin-right:5px}}
.figlegend .lchip{{display:inline-block;margin-right:5px;vertical-align:-2px}}
.figlegend .lf{{font-size:11.5px}}
details.boxes{{font-size:12px;color:var(--muted);margin-top:4px}}
details.boxes summary{{cursor:pointer}}
details.boxes ul{{margin:4px 0 0;padding-left:18px;columns:2;column-gap:24px}}
details.boxes li{{break-inside:avoid;margin-bottom:2px}}
.unit{{margin:26px 0 40px;padding-top:4px}}
.unit header{{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline}}
.tag{{display:inline-block;font-size:11.5px;padding:1px 8px;border-radius:10px;background:var(--soft);border:1px solid var(--line);color:var(--muted)}}
.tag.new{{color:var(--fg);border-color:var(--fg);font-weight:600}}
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
ul.stack{{max-width:100ch;font-size:14px}}ul.stack li{{margin-bottom:4px}}ul.stack li.this{{background:#eef6ff;padding:2px 6px;border-radius:4px}}
.pages{{font-size:13px}}
"""


def chip(fill, stroke, dashed=False):
    d = "border-style:dashed;" if dashed else ""
    return f'<span class="chip" style="background:{fill};border-color:{stroke};{d}"></span>'


LEGEND = f"""
<p class="meta">ink = the near-black of the body text ({C['ink']}), used for box outlines, arrows and the
step badges; orange-red = {C['pend']} (a complete block that waits for its conversion, and the conversion itself), green =
{C['rows']} (k_rows_saved_ bits), pink = {C['blk']} (k_vnni_blocks_ bits). The palette is Okabe-Ito (colour-blind safe);
fills are light tints of the outline colours.</p>
<div class="chips">
<span>{chip(C['vnni_fill'], C['vnni'])}VNNI layout: a converted block (its k_vnni_blocks_ bit set), a whole-block save, the packed plane k_vnni_tensor / k_vnni_view</span>
<span>{chip(C['vnni'], C['vnni'])}solid blue: a VNNI pair row (one 64-byte line of a panel) or a token's column, as bytes</span>
<span>{chip(C['rm_fill'], C['rm'])}row-major rows: the row-major tail block of a VNNI slot (row_major_row, store_row_major, load_row_major), a row-major slot, or one token's row in dimension order</span>
<span>{chip(C['rm'], C['rm'])}solid orange: a row-major token row, as bytes (4 whole 64-byte lines)</span>
<span>{chip(C['pend_fill'], C['pend'], True)}complete, may wait: a block whose 16 row bits are set and whose block bit is clear; the deferred conversion list pending_k_blocks_</span>
<span>{chip(C['pend_fill'], C['pend'])}drawn solid: the conversion of such a block (block_to_vnni, k_block_to_vnni_at, convert_pending_k_blocks) and the way back (block_to_rows)</span>
<span>{chip(C['rows_fill'], C['rows'])}k_rows_saved_: a saved-row bit that is set (one square per page offset)</span>
<span>{chip(C['blk_fill'], C['blk'])}k_vnni_blocks_: a converted-block bit that is set (one square per 16-token block)</span>
<span>{chip(C['empty_fill'], C['empty'], True)}grey dashed: no row saved (bytes undefined), a bit that is clear</span>
<span>{chip(C['hw_fill'], C['hw'])}hardware attention: an operation the FPGA scores (cached_operation_uses_hw: no row bit, no conversion, the block stays row-major) and the FPGA staging path (gof::populate, page_info::k_head_fn, k_row_if_row_major)</span>
<span>{chip(C['eagle_fill'], C['eagle'])}EAGLE storage: the extra physical slot and its state entry layout_t::n_slots (k_state_ix, eagle_view_active)</span>
<span>{chip(C['q_fill'], C['q'])}query side: Q rows, the dotters dot_q, the live mask of k_vnni::qk_group, the scores s_pages, the AMX gate k_layout_dense</span>
<span>{chip(C['unit_fill'], C['unit'])}work unit of the shared K store window of PR 4958 (context only)</span>
<span>{chip(C['hi_fill'], C['ink'])}the worked example's cell (page 7, storage slot 5, KV head 0; token 37, dimension 70; block 2)</span>
<span><span class="chip" style="background:#fff;border-color:{C['muted']};border-style:dashed"></span>with the word "deleted" or "does not exist": a function or route the code does not provide (page::k for a VNNI slot, a partial set_k_block)</span>
<span><span class="chip" style="background:#fff;border-color:{C['gone']};border-style:dashed"></span>red dashed: before / removed (the base code: the partial block save with a present mask, the scatter of a single-token run)</span>
<span><span class="chip" style="background:{C['soft']};border-color:{C['line']}"></span>grey fill, thin grey outline: context (a caller in another file, a test, a note)</span>
<span><span class="chip" style="background:#e6ffec;border-color:#9fd3ad"></span>added line (head)</span>
<span><span class="chip" style="background:#ffebe9;border-color:#e0a6a0"></span>removed line (base)</span>
</div>
<p class="meta">Identifiers are set in monospace in prose, code and diagrams. The same concept has
the same colour on all three pages. A dashed outline means "waiting", "not read" or "no bytes saved". Threads
are lanes or bracketed names, never colours. The words "new" and "changed" are markers in bold
ink, not a colour. Every box cites the line or Note that defines it
(small grey text in the box, and the "Boxes and their sources" list under each figure). Every
arrow between data-model boxes says how many.</p>"""


STACK = [  # the four PRs of the split, one line each (jhan's pattern, 2026-10-16)
    ("4956", "changes how one K row is stored (scattered into the VNNI plane instead of written as a row) "
             "and how the CPU reads it (the AVX-512 reader instead of the row-major dotter)."),
    ("4957", "changes who scores a full page (the AMX tile kernel reads the VNNI plane as its B operand) "
             "and how the queries are packed for it."),
    ("4958", "changes how a run of tokens is written (a 16-token block at once, transposed in registers) "
             "and which threads write it (the idle helpers share the store)."),
    ("4959", "changes what a run shorter than a block saves (row-major rows) and when that block turns VNNI "
             "(at the end of the pass that completes it, or never under hardware attention). "
             "It also turns the option on in the deb package."),
]


def stack_html(this_pr):
    items = "".join(
        f'<li{" class=this" if pr == this_pr else ""}><b>PR {pr}</b> {html.escape(what)}'
        f'{" (this PR)" if pr == this_pr else ""}</li>' for pr, what in STACK)
    return (f'<h4 id="stack">The four PRs of the split, one line each (a run = the consecutive tokens '
            f'of one pass that land in the same 16-token block of a page)</h4><ul class="stack">{items}</ul>')


def code_legend(row_lists, new_pill, new_file):
    """The colour and font scheme of one section's code excerpts, with only
    the row kinds, number columns and pills that section really shows.
    row_lists = one unit_rows() list per excerpt; new_pill = the section's
    headers carry the bold 'new' pill; new_file = the file has no base."""
    kinds = {r[0] for rows in row_lists for r in rows}
    if not kinds:
        return ""
    ents = []
    if "add" in kinds:
        ents.append('<span><span class="chip" style="background:#e6ffec;border:1.5px solid #9fd3ad">'
                    '</span>green row = a line this PR adds (head)</span>')
    if "del" in kinds:
        ents.append('<span><span class="chip" style="background:#ffebe9;border:1.5px solid #e0a6a0">'
                    '</span>red row = a line this PR removes (base)</span>')
    if "ctx" in kinds:
        ents.append('<span><span class="chip" style="background:#fff;border:1.5px solid #d6d9de">'
                    '</span>white row = unchanged context from the head file</span>')
    # the base column holds a number for removed lines only (difflib_units.render_rows)
    if "del" in kinds:
        num = ("grey numbers = base line (first column, removed lines only), head line "
               "(second column)")
    elif "ctx" in kinds:
        num = ("grey number = the head line of the row (no line is removed here, so the "
               "base column is empty)")
    else:
        num = ("grey number = the head line of the row (every excerpt line is an added line"
               + (" of a new file" if new_file else "") + ", so the base column is empty)")
    if "gap" in kinds:
        num += ('; <span class="chip" style="background:#f3f5f8;border:1.5px solid #d6d9de">'
                '</span>a grey row with a vertical dots mark = lines left out')
    ents.append(f'<span><code class="lf" style="color:#6b7280">1234</code> {num}</span>')
    pill = ('<span><span class="tag">head lines</span> grey pill in a unit header = a fact of '
            'the unit (head lines, +added / -removed lines, the kind of change)')
    if new_pill:
        pill += ('; <span class="tag new">new</span> bold ink-outlined pill \'new\' = the unit '
                 'is added by this PR')
    ents.append(pill + "</span>")
    ents.append('<span><code class="lf">monospace</code> = the code and its comments, exactly '
                'as in the file</span>')
    what = "the code excerpt" if len(row_lists) == 1 else "the code excerpts"
    return (f'<div class="figlegend"><span class="lt">Colour and font scheme used in {what} of '
            f'this section:</span>\n' + "\n".join(ents) + "</div>")


XREF_LEGEND = """<div class="figlegend"><span class="lt">Colour and font scheme used in this section:</span>
<span><code class="lf">name_of_it</code> monospace = a line range (the head lines column) or a commit hash</span>
<span><span class="lf">prose</span> sans-serif = the change titles, the commit subjects and the base-diagram column; a unit id is a link to its section</span></div>"""

METHOD_LEGEND = """<div class="figlegend"><span class="lt">Colour and font scheme used in this section:</span>
<span><code class="lf">name_of_it</code> monospace = the git command, the worktree path and the script names</span>
<span><span class="lf">prose</span> sans-serif = the description of each step</span></div>"""


def commits_map():
    m = {}
    for ln in git("log", "--format=%h %s", f"{BASE}..{HEAD}").split("\n"):
        if ln:
            h, s = ln.split(" ", 1)
            m[h] = s
    return m


def unit_html(d, u, commits):
    rows = d.unit_rows(u["ranges"])
    add, dele = counts(rows)
    cs = d.blame_commits(u["ranges"])
    rng = ", ".join(f"{a}-{b}" for a, b in u["ranges"])
    lead = "".join(f"<li>{html.escape(s)}</li>" for s in u["lead"])
    com = " ".join(f'<code title="{html.escape(commits.get(c, ""))}">{c}</code>' for c in cs)
    tag_cls = "tag new" if u["kind"].startswith("new") else "tag"
    figs = u["fig"] if isinstance(u["fig"], (list, tuple)) else [u["fig"]]
    fig_html = "".join(f() for f in figs)
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
<div class="fig">{fig_html}</div>
</div>
</article>"""


def build(spec):
    d = DiffFile(spec["file"])
    commits = commits_map()
    units, trivial = spec["units"], spec.get("trivial", [])
    short_name = spec["file"].rsplit("/", 1)[-1]
    # coverage check: every added line and deletion anchor is in a unit or a
    # trivial entry (fail loud)
    all_ranges = [r for u in units for r in u["ranges"]] + \
                 [r for t in trivial for r in t["ranges"]]
    miss_add, miss_del = d.coverage(all_ranges)
    assert not miss_add and not miss_del, (
        f"uncovered added lines {miss_add[:20]} / deletion anchors {miss_del[:20]}")

    toc_units = "".join(
        f'<li><a href="#{u["id"]}">{u["id"].upper()}. {html.escape(u["title"])}</a></li>'
        for u in units)
    toc_base = "".join(
        f'<li><a href="#{b["id"]}">{b["id"].upper()} {html.escape(b["short"])}</a></li>'
        for b in spec["base"])
    words = "".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(x)}</dd>"
                    for t, x in spec["glossary"])
    units_html = "".join(unit_html(d, u, commits) for u in units)
    base_html = ""
    for b in spec["base"]:
        base_html += (f'<h3 id="{b["id"]}">{b["id"].upper()}. {html.escape(b["title"])}</h3>'
                      f'<p>{html.escape(b["intro"])}</p>{b["fig"]()}')
    triv_html = ""
    for t in trivial:
        rows = d.unit_rows(t["ranges"])
        a, x = counts(rows)
        rng = ", ".join(f"{p}-{q}" for p, q in t["ranges"])
        triv_html += (f'<article class="unit" id="{t["id"]}"><header><h3>{t["id"].upper()}. '
                      f'{html.escape(t["title"])}<a class="top" href="#toc">top</a></h3>'
                      f'<span class="tag">{html.escape(t.get("kind", "trivial"))}</span>'
                      f'<span class="tag">head lines {rng}</span><span class="tag">+{a} / -{x} lines'
                      f'</span></header><p>{html.escape(t["what"])}</p>'
                      f'<pre class="diff">{render_rows(rows)}</pre></article>')
    extra_triv = "".join(f"<li>{html.escape(s)}</li>" for s in spec.get("trivial_bullets", []))
    xref = ""
    for u in units:
        rows = d.unit_rows(u["ranges"])
        a, x = counts(rows)
        rng = "<br>".join(f"{p}-{q}" for p, q in u["ranges"])
        com = "<br>".join(f"<code>{c}</code> {html.escape(commits.get(c, ''))}"
                          for c in d.blame_commits(u["ranges"]))
        xref += (f'<tr><td><a href="#{u["id"]}">{u["id"].upper()}</a></td>'
                 f'<td>{html.escape(u["title"])}</td><td class="mono">{rng}</td>'
                 f'<td>+{a} / -{x}</td><td>{com}</td><td>{html.escape(u["base"])}</td></tr>')
    file_commits = [h for h in commits if h in {c for u in units for c in d.blame_commits(u["ranges"])}]
    commits_list = "".join(f"<li><code>{h}</code> {html.escape(s)}</li>" for h, s in commits.items())
    pages = "".join(
        f'<li><a href="{out}">{out}</a>: <code>{f}</code>, {html.escape(what)}'
        f'{" (this page)" if f == spec["file"] else ""}</li>' for f, out, what in PAGES)
    short = " ".join(spec["short"])
    method = "".join(f"<li>{s}</li>" for s in spec.get("method", []))
    n_hunks = git("diff", "-U0", BASE, HEAD, "--", spec["file"]).count("\n@@")
    n_hunks3 = git("diff", "-U3", BASE, HEAD, "--", spec["file"]).count("\n@@")
    hunks = (f"in {n_hunks} hunk{'s' if n_hunks != 1 else ''} at zero context (git diff -U0"
             + (f"; {n_hunks3} with the default 3-line context)" if n_hunks3 != n_hunks else ")"))
    n_toc_tr = len(trivial)
    # the code-excerpt scheme of sections 2 and 3: only what each section shows
    new_file = not d.base_lines
    legend2 = code_legend([d.unit_rows(u["ranges"]) for u in units],
                          any(u["kind"].startswith("new") for u in units), new_file)
    legend3 = code_legend([d.unit_rows(t["ranges"]) for t in trivial], False, new_file)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PR 4959 {html.escape(spec.get("page_name", short_name))} diagrams</title>
<meta name="description" content="Diagrams of every logical code change PR 4959 makes to {html.escape(spec['file'])}">
<style>{CSS}</style></head>
<body><main>
<h1>PR 4959 in {html.escape(spec["file"])}: every code change, diagrammed</h1>
<p class="meta">tron PR <a href="{PR_URL}">#4959</a> "{html.escape(PR_TITLE)}" &middot; base
<code>jhan-vnnik-3-shared-save</code> (the head of PR #4958) at <code>{BASE}</code> &middot; head <code>jhan-vnnik-4-tail-block</code> at <code>{HEAD}</code>
&middot; file <code>{html.escape(spec["file"])}</code>: {len(d.base_lines)} lines at the base,
{len(d.head_lines)} at the head, {d.n_added} lines added, {d.n_deleted} removed, {hunks}
&middot; page generated 2026-10-16 by <code>exec/pr4959-diagrams-20261016/{spec["gen"]}</code>.</p>
<p class="pages">The three pages of this set (one per file):</p><ul class="pages">{pages}</ul>

<section id="prompt"><h2>The request (verbatim)</h2>
<pre class="prompt">{html.escape(PROMPT)}</pre></section>

<nav class="toc" id="toc"><h2>Table of contents</h2><ol>
<li><a href="#short">Short version</a> and <a href="#stack">the four PRs, one line each</a></li>
<li><a href="#words">Words used here</a></li>
<li><a href="#legend">Colour and font scheme</a></li>
<li><a href="#base">1. Base diagrams</a><ol>{toc_base}</ol></li>
<li><a href="#changes">2. Code changes, each beside its diagram</a><ol>{toc_units}</ol></li>
<li><a href="#trivial">3. Trivial changes (listed, no diagram)</a></li>
<li><a href="#xref">4. Cross-reference: change, lines, commits, base diagram</a></li>
<li><a href="#method">5. How this page was made and checked</a></li>
</ol></nav>

<section id="short"><h2>Short version</h2>
<p class="short">{short}</p>{stack_html("4959")}</section>

<section id="words"><h2>Words used here</h2>
<dl class="words">{words}</dl></section>

<section id="legend"><h2>Colour and font scheme</h2>{LEGEND}</section>

<section id="base"><h2>1. Base diagrams</h2>
<p>{html.escape(spec["base_intro"])}</p>
<p class="meta">Each base diagram repeats the colour and font scheme with only the styles it uses (the row under the figure).</p>
{base_html}
</section>

<section id="changes"><h2>2. Code changes, each beside its diagram</h2>
<p>{html.escape(spec["changes_intro"])}</p>
{legend2}
<p class="meta">Each diagram below repeats the colour and font scheme with only the styles it uses (the row under the figure).</p>
{units_html}
</section>

<section id="trivial"><h2>3. Trivial changes (listed, no diagram)</h2>
<p>{html.escape(spec.get("trivial_intro", "Changes that alter no behaviour and need no picture."))}</p>
{legend3}
{triv_html}
{("<ul>" + extra_triv + "</ul>") if extra_triv else ""}</section>

<section id="xref"><h2>4. Cross-reference</h2>
{XREF_LEGEND}
<div class="tbl"><table><thead><tr><th>id</th><th>change</th><th>head lines</th><th>+ / -</th>
<th>commits that last touched the added lines</th><th>base diagram updated</th></tr></thead>
<tbody>{xref}</tbody></table></div>
<h4>The {len(commits)} commits of the PR (newest first, first-parent and merged lines)</h4>
<ul>{commits_list}</ul></section>

<section id="method"><h2>5. How this page was made and checked</h2>
{METHOD_LEGEND}
<ul>
<li>Source of every code excerpt: <code>git diff {BASE} {HEAD} -- {html.escape(spec["file"])}</code>
in the worktree <code>{WT}</code>, parsed by <code>difflib_units.py</code>. Context lines come from
the head file, so a unit can show a whole function. The parser's totals ({d.n_added} added,
{d.n_deleted} removed) match <code>git diff --stat</code> ({d.n_added + d.n_deleted} changed lines),
and the build asserts that every non-blank added line and every deletion sits in exactly one unit or
trivial entry (blank separator lines are listed in section 3).</li>
{method}
<li>Every SVG was rendered to PNG with cairosvg and inspected for clipped or overlapping labels
before delivery (<code>render_check.py</code>).</li>
</ul></section>
</main></body></html>
"""


def write(spec, out):
    page = build(spec)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    non_ascii = sum(1 for ch in page if ord(ch) > 127)
    print(out, len(page), "bytes;", "non-ascii chars:", non_ascii)
    return page
