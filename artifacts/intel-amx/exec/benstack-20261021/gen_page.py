#!/usr/bin/env python3
"""Generate random/Ben-stack-PR4957-4959.html: what Ben would dislike in PRs 4957/4958/4959 (verified predictions
from his PR 5047 commits and his review record) and the three draft PRs that re-express the stack on his structure.

Inputs:
  SCRATCH/stack/wfA-result.json      kept/dropped predictions (prediction workflow wf_e4c2f652-7e0)
  status.json (this folder)          new heads, draft PR urls, audit facts per branch (filled by hand / by the session)
  git show <sha>:<path>              layout-identifier counts per head (computed here, code lines only)
  exec/results/benstack-20261021/    build-*.txt, tests.txt (3bda gate), when present
Usage: python3 gen_page.py   -> writes the page and prints its size; SVGs are rendered to out/*.png for the eye check.
"""
import collections
import datetime
import html
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = "/tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad"
OUT = "/home/jhan/workspace/intel-AMX/random/Ben-stack-PR4957-4959.html"
REPO = "/home/jhan/workspace/ai-runs/tron-ben-pr2"  # any worktree of the shared repo: git show reads every sha
RESULTS = "/home/jhan/workspace/intel-AMX/exec/results/benstack-20261021"

HEADS = collections.OrderedDict([
    ("base", ("a5697f86d3", "PR 4956 head (base of everything)")),
    ("ben", ("ade89a9d9c", "Ben's PR 5047 head")),
    ("4957", ("26b86a279a", "PR 4957 head")),
    ("4958", ("b39765ec29", "PR 4958 head")),
    ("4959", ("6b081187e1", "PR 4959 head")),
])
FILES = collections.OrderedDict([
    ("self_attention.hpp", "h/tron/models/self_attention.hpp"),
    ("model.hpp", "h/tron/models/model.hpp"),
    ("full.hpp", "h/tron/scheduler/full.hpp"),
    ("kv_cache.hpp", "h/tron/models/kv_cache.hpp"),
])
# Layout-specific identifiers: a code line that names one of these knows how K is stored.
IDENTS = ["k_vnni::layout_on", "k_packed", "template k<", "kv_block(", "k_vnni_blocks", "block_bit", "offset_bit",
          "row_major_row", "__mmask16", "BLOCKS_PER_PAGE_MASK", "BLOCK_TOKENS_16", "k_storage_of"]
# k_source_row / k_destination_row are the typed row views (layout-agnostic by design) and are not counted.



def no_semicolons(page):
    """Plain-English pass: replace '; ' by '. ' in text nodes outside style, script, svg, pre and code blocks.
    HTML entities (which end in ';') are protected. The word after the new period is capitalized when it is a
    plain lowercase English word (letters only) and not a lowercase project name or an arm name."""
    import re as _re
    keep = {"tron", "runtron", "rinzler", "jhan", "ben", "ccache", "cmake", "clang", "ninja", "nix", "gh", "git", "ssh",
            "platformd", "dut", "gof", "dotter", "head", "base", "headv", "basev", "baseoff", "headoff", "head2",
            "main", "cpu", "fpga", "amx", "avx", "vnni", "ok", "est", "lefthook", "zig", "ctest", "catch2"}
    parts = _re.split(r'(<(?:style|script|svg|pre|code)\b[^>]*>.*?</(?:style|script|svg|pre|code)>)', page, flags=_re.S | _re.I)
    out = []
    def cap(m):
        w = m.group(1)
        if w.isalpha() and w.islower() and w not in keep:
            w = w[0].upper() + w[1:]
        return '. ' + w
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
            continue
        def fix_text(m):
            s = m.group(0)
            s = _re.sub(r'&(#[xX][0-9a-fA-F]+|#\d+|\w+);', lambda e: '\x00' + e.group(1) + '\x01', s)
            s = _re.sub(r'; ([\w:.\-]+)', cap, s)
            s = s.replace('; ', '. ')
            return s.replace('\x00', '&').replace('\x01', ';')
        out.append(_re.sub(r'(?<=>)[^<]+(?=<)', fix_text, part))
    return ''.join(out)


def esc(s):
    return html.escape(str(s), quote=True)


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def git_show(sha, path):
    try:
        return subprocess.run(["git", "-C", REPO, "show", f"{sha}:{path}"], capture_output=True, text=True,
                              check=True).stdout
    except subprocess.CalledProcessError:
        return None


def strip_comments(src):
    """Drop // comments and /* */ blocks; keep line structure (a crude but adequate C++ comment stripper)."""
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return "\n".join(line.split("//", 1)[0] for line in src.split("\n"))


def layout_counts(sha):
    out = collections.OrderedDict()
    for short, path in FILES.items():
        src = git_show(sha, path)
        if src is None:
            out[short] = None
            continue
        code = strip_comments(src)
        counts = collections.OrderedDict()
        for ident in IDENTS:
            counts[ident] = sum(1 for line in code.split("\n") if ident in line and "k_block_tokens" not in line.replace(ident, ""))
        # model.hpp may reference page::k_block_tokens (a plain size): do not count the BLOCK_TOKENS_16 alias line twice
        out[short] = counts
    return out


def total(counts):
    return sum(counts.values()) if counts else 0


# ----------------------------------------------------------------------------------------------------------------
# SVG helpers (hand-drawn boxes and arrows; theme colors fixed: the page is light-only)
C_INK = "#1f2933"
C_MUTED = "#52606d"
C_GRID = "#d9dee3"
C_PR = "#d9480f"      # PR head (orange)
C_NEW = "#1c7ed6"     # new branch (blue)
C_BEN = "#495057"     # Ben's head (grey)
C_BOX = "#f5f7fa"
C_BOX_LINE = "#9aa5b1"
C_CACHE = "#e7f5ff"
C_CACHE_LINE = "#1c7ed6"
C_BAD = "#fff4e6"
C_BAD_LINE = "#d9480f"


def svg_open(w, h, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}" '
            f'style="font-family:Inter,system-ui,sans-serif;font-size:12px">'
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{C_MUTED}"/></marker></defs>')


def box(x, y, lines, fill=C_BOX, stroke=C_BOX_LINE, bold_first=True, size=12, w=None):
    """A rounded box whose width fits its longest line (about 6.6 px per character at 12 px)."""
    lh = size + 4
    w = w or int(max(len(l) for l in lines) * (size * 0.6) + 24)
    h = lh * len(lines) + 14
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'
    ty = y + 7 + size
    for i, line in enumerate(lines):
        weight = "600" if (i == 0 and bold_first) else "400"
        s += (f'<text x="{x + w / 2}" y="{ty + i * lh:.1f}" text-anchor="middle" fill="{C_INK}" '
              f'font-weight="{weight}" font-size="{size}">{esc(line)}</text>')
    return s, w, h


def arrow(x1, y1, x2, y2, dashed=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C_MUTED}" stroke-width="1.4" marker-end="url(#arr)"{dash}/>'


def text(x, y, t, size=12, weight="400", fill=C_INK, anchor="start"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-size="{size}" font-weight="{weight}">{esc(t)}</text>'


def figure(svg, caption):
    return f'<figure>{svg}<figcaption>{caption}</figcaption></figure>'


def panel_pair(label, left_boxes, right_boxes, h):
    """Two panels (PR as opened | new branch). A panel is {"boxes": {id: (col, y, lines, style)}, "arrows": [(a, b)]}.
    Column x positions are computed from the widest box of the previous column, so nothing overlaps or clips."""
    size = 12
    def measure(lines):
        return int(max(len(l) for l in lines) * (size * 0.6) + 24)
    panels = []
    x_cursor = 10
    for panel in (left_boxes, right_boxes):
        cols = collections.defaultdict(list)
        for bid, (col, y, lines, style) in panel["boxes"].items():
            cols[col].append(bid)
        col_x = {}
        x = x_cursor
        for col in sorted(cols):
            col_x[col] = x
            x += max(measure(panel["boxes"][b][2]) for b in cols[col]) + 48
        panels.append((panel, col_x, x_cursor))
        x_cursor = x + 12
    w = x_cursor
    s = svg_open(w, h, label)
    geoms = {}
    for pi, (panel, col_x, px) in enumerate(panels):
        s += text(px, 18, "PR as opened" if pi == 0 else "new branch (on Ben's structure)", 13, "600", C_PR if pi == 0 else C_NEW)
        if pi == 1:
            s += f'<line x1="{px - 30}" y1="8" x2="{px - 30}" y2="{h - 8}" stroke="{C_GRID}" stroke-width="1"/>'
        for bid, (col, y, lines, style) in panel["boxes"].items():
            fill, stroke = {"bad": (C_BAD, C_BAD_LINE), "cache": (C_CACHE, C_CACHE_LINE), "plain": (C_BOX, C_BOX_LINE)}[style]
            bs, bw, bh = box(col_x[col], y, lines, fill, stroke)
            s += bs
            geoms[(pi, bid)] = (col_x[col], y, bw, bh)
        for a, b in panel["arrows"]:
            ax, ay, aw, ah = geoms[(pi, a)]
            bx, by, bw, bh = geoms[(pi, b)]
            s += arrow(ax + aw, ay + ah / 2, bx - 2, by + bh / 2)
    s += "</svg>"
    return s


def mech_pr2():
    left = {"boxes": {
        "pack": (0, 40, ["self_attention.hpp: packed_amx_query", "if layout_on: pack_q_rows_128x4", "else pack_q_group_128x4"], "bad"),
        "dense": (0, 150, ["self_attention.hpp: apply_dense_amx_page", "if layout_on: qk_vnni_128x4 on page::k_packed()", "else qk_rowmajor_128x4 on page::k()"], "bad"),
        "page": (1, 95, ["kv_cache.hpp: page", "k_packed(), k() x 8:", "public raw K views"], "plain")},
        "arrows": [("dense", "page")]}
    right = {"boxes": {
        "pack": (0, 40, ["self_attention.hpp: packed_amx_query", "page::pack_q_amx(group, slot)"], "plain"),
        "dense": (0, 150, ["self_attention.hpp: apply_dense_amx_page", "page::try_score_k_amx(...) or software"], "plain"),
        "page": (1, 70, ["kv_cache.hpp: page", "pack_q_amx: VNNI -> rows pack,", "  row-major -> group pack", "try_score_k_amx: VNNI ->", "  qk_vnni_128x4 on its own plane,", "  row-major -> qk_rowmajor_128x4", "kv_block stays private"], "cache")},
        "arrows": [("pack", "page"), ("dense", "page")]}
    return panel_pair("PR 4957 versus PR2': the kernel and the packer choice move into the cache", left, right, 260)


def mech_pr3():
    left = {"boxes": {
        "store": (0, 36, ["model.hpp: store_k_block (95 lines)", "if !layout_on: per-token page::k().set", "else: run scan with a present mask,", "  n == 1 -> set_k_row (scatter),", "  else set_k_block(16 bf16*, mask);", "  fp32 rows converted here"], "bad"),
        "page": (1, 60, ["kv_cache.hpp: page", "set_k_block(rows[16], __mmask16)", "VNNI slots only"], "plain"),
        "win": (0, 190, ["save_k_impl: hand-written window", "opened / finished / helper_windows[128],", "next_unit fetch_add loop, _mm_pause spin,", "2^20 clock spins, abort after 120 s,", "is_main branches x 3"], "bad"),
        "batch": (1, 215, ["common.hpp: batch", "k_store_window_t: 6 fields,", "128-worker cap"], "plain")},
        "arrows": [("store", "page"), ("win", "batch")]}
    right = {"boxes": {
        "store": (0, 36, ["model.hpp: store_k_block", "for run in next_k_run(...):", " for kv_head: rows[16] (row views;", "  an absent lane is an invalid view)", " page::set_k_block(slot, head, c, rows)"], "plain"),
        "page": (1, 36, ["kv_cache.hpp: page", "set_k_block for EVERY slot:", "VNNI: 1 lane -> store_row,", "  else store_block (lanes from", "  valid()); converts inside", "row-major: k_at(i).set per lane"], "cache"),
        "win": (0, 190, ["save_k_impl", "main: cut units; next_phase(reset claim)", "  claim loop; done(0); wait_for_all", "helper: wait(ix); claim loop; done(ix)", "claim loop = greedy_range(next_unit)"], "plain"),
        "batch": (1, 200, ["common.hpp: batch", "barrier k_store_barrier (reset with", "  n_main_workers in reset_channels)", "k_store_units: next_unit, n_units,", "  unit_start[]"], "cache")},
        "arrows": [("store", "page"), ("win", "batch")]}
    return panel_pair("PR 4958 versus PR3': one store flow through the page, and the window is a tron::barrier phase", left, right, 320)


def mech_pr4():
    left = {"boxes": {
        "loop": (0, 36, ["self_attention.hpp: apply_page_tok", "k_layout_dense: block mask == 0xF", "loop: live bit, in-loop dotter for", "  row-major blocks (row_major_row on", "  the page::k_packed() plane),", "reader after the loop"], "bad"),
        "save": (0, 180, ["model.hpp: save_k", "if constexpr layout_on: a 2nd loop", "note_k_row_saved -> push", "  {page, k_storage_of(slot), j / 16}"], "bad"),
        "stage": (0, 290, ["full.hpp: k_head_fn", "k_row_if_row_major -> valid?", "  pointer into the page,", "  else get_k_row gather"], "bad"),
        "page": (1, 150, ["kv_cache.hpp: page", "k_vnni_blocks, block_bit,", "k_packed plane view,", "k_row_if_row_major"], "plain")},
        "arrows": [("loop", "page"), ("save", "page"), ("stage", "page")]}
    right = {"boxes": {
        "loop": (0, 36, ["self_attention.hpp: apply_page_tok", "unchanged from Ben: the loop", "selects tokens into `live`;", "page::score_k(live) after it"], "plain"),
        "save": (0, 160, ["model.hpp: save_k mark loop", "pending = note_k_row_saved(slot, j)", "if pending: push {page, *pending}", "(no layout test, no block arithmetic)"], "plain"),
        "stage": (0, 280, ["full.hpp: k_head_fn", "get_k_row always (Ben's copy;", "FPGA cells inside the band)"], "plain"),
        "page": (1, 60, ["kv_cache.hpp: page", "try_score_k_amx: declines unless", "  every block is converted", "score_k: converted blocks -> reader,", "  row-major blocks -> score_rows", "  (one local lambda, lazy dotters)", "note_k_row_saved -> optional", "  k_pending_block {storage, block}", "get_k_row follows the block bit", "copy / forget split into helpers"], "cache")},
        "arrows": [("loop", "page"), ("save", "page"), ("stage", "page")]}
    return panel_pair("PR 4959 versus PR4': the dense gate and the tail-block scoring move into the page, and the staging keeps Ben's copy", left, right, 380)


def layout_chart(counts_by_head, new_heads):
    """Dumbbell small multiples: per PR (columns) and per file outside the cache (rows): PR head vs new branch,
    with Ben's head as the reference tick."""
    prs = ["4957", "4958", "4959"]
    files = ["self_attention.hpp", "model.hpp", "full.hpp"]
    col_w, row_h, left, top = 290, 46, 150, 54
    w = left + col_w * len(prs) + 20
    h = top + row_h * len(files) + 60
    vmax = 1
    for pr in prs:
        for f in files:
            for key in (pr, f"new{pr}"):
                c = counts_by_head.get(key, {}).get(f)
                vmax = max(vmax, total(c))
    s = svg_open(w, h, "Layout-specific identifiers outside the cache: PR head versus the new branch, per file")
    for ci, pr in enumerate(prs):
        x0 = left + ci * col_w
        s += text(x0 + col_w / 2, 20, f"PR {pr} -> PR{int(pr) - 4955}'", 13, "600", C_INK, "middle")
        nh = new_heads.get(pr[-1])
        s += text(x0 + col_w / 2, 36, f"new branch head {nh[:10] if nh else 'pending'}", 11, "400", C_MUTED, "middle")
        ax0, ax1 = x0 + 24, x0 + col_w - 50
        for ri, f in enumerate(files):
            y = top + ri * row_h + row_h / 2
            s += f'<line x1="{ax0}" y1="{y}" x2="{ax1}" y2="{y}" stroke="{C_GRID}" stroke-width="1"/>'
            def X(v):
                return ax0 + (ax1 - ax0) * v / vmax
            c_pr = total(counts_by_head.get(pr, {}).get(f))
            c_new_counts = counts_by_head.get(f"new{pr}", {}).get(f)
            c_ben = total(counts_by_head.get("ben", {}).get(f))
            s += f'<line x1="{X(c_ben)}" y1="{y - 12}" x2="{X(c_ben)}" y2="{y + 12}" stroke="{C_BEN}" stroke-width="2"/>'
            if c_new_counts is not None:
                c_new = total(c_new_counts)
                s += f'<line x1="{X(c_new)}" y1="{y}" x2="{X(c_pr)}" y2="{y}" stroke="{C_GRID}" stroke-width="4"/>'
                s += f'<circle cx="{X(c_new)}" cy="{y}" r="6" fill="{C_NEW}" stroke="#fff" stroke-width="1.5"/>'
                s += text(X(c_new), y - 10, str(c_new), 11, "600", C_NEW, "middle")
            s += f'<circle cx="{X(c_pr)}" cy="{y}" r="6" fill="{C_PR}" stroke="#fff" stroke-width="1.5"/>'
            s += text(X(c_pr), y + 20, str(c_pr), 11, "600", C_PR, "middle")
            if ci == 0:
                s += text(left - 10, y + 4, f, 12, "500", C_INK, "end")
    ly = h - 22
    s += f'<circle cx="{left + 6}" cy="{ly}" r="6" fill="{C_PR}"/>' + text(left + 18, ly + 4, "PR head (as opened)", 11, "400", C_MUTED)
    s += f'<circle cx="{left + 176}" cy="{ly}" r="6" fill="{C_NEW}"/>' + text(left + 188, ly + 4, "new branch (on Ben's structure)", 11, "400", C_MUTED)
    s += f'<line x1="{left + 420}" y1="{ly - 8}" x2="{left + 420}" y2="{ly + 8}" stroke="{C_BEN}" stroke-width="2"/>' + text(left + 430, ly + 4, "Ben's head (PR 5047) = 0 in every file", 11, "400", C_MUTED)
    s += "</svg>"
    return s


# ----------------------------------------------------------------------------------------------------------------
SEV_ORDER = {"block": 0, "should": 1, "nit": 2}


def sev_badge(sev):
    cls = {"block": "sev-block", "should": "sev-should", "nit": "sev-nit"}.get(sev, "sev-nit")
    label = {"block": "would block", "should": "should fix", "nit": "nit"}.get(sev, sev)
    return f'<span class="badge {cls}">{esc(label)}</span>'


def ids_in(evidence):
    ids = sorted(set(re.findall(r"\b(?:P[1-5]|C1[0-6]|C[1-9])\b", evidence or "")), key=lambda t: (t[0], int(t[1:])))
    return ", ".join(ids)


def findings_section(result, status):
    kept = result.get("kept", [])
    dropped = result.get("dropped", [])
    bypr = collections.defaultdict(list)
    for f in kept:
        bypr[str(f["pr"])].append(f)
    parts = []
    totals = {sev: sum(1 for f in kept if f.get("severity") == sev) for sev in SEV_ORDER}
    parts.append(f"<p>The prediction workflow produced {len(kept) + len(dropped)} candidate objections from four lenses "
                 f"(structure, his review record, missing abstractions, interfaces). Three independent refuters tried to "
                 f"refute each one; {len(kept)} survived (would block: {totals['block']}, should fix: {totals['should']}, "
                 f"nit: {totals['nit']}) and {len(dropped)} were refuted. Each kept row below cites the evidence items of "
                 f"his profile (P1-P5 from PR 5047's commits, C1-C16 from his review comments) and says what the new branch "
                 f"does about it.</p>")
    for pr in ("4957", "4958", "4959"):
        fs = sorted(bypr[pr], key=lambda f: (SEV_ORDER.get(f.get("severity"), 9), f["file"], f.get("line") or 0))
        br = status.get("branches", {}).get(pr[-1], {})
        removed = {k.split(":")[0].strip(): k for k in br.get("objections_removed", [])}
        counts = collections.Counter(f.get("severity") for f in fs)
        parts.append(f'<h3 id="pr{pr}">PR {pr}: {len(fs)} objections (would block {counts["block"]}, should fix '
                     f'{counts["should"]}, nit {counts["nit"]})</h3>')
        rows = []
        for f in fs:
            fid = f["id"]
            status_txt = removed.get(fid)
            if status_txt:
                st = esc(status_txt.split(":", 1)[1].strip()) if ":" in status_txt else "removed"
            else:
                st = {"yes": "planned in the new branch", "partial": "partly planned", "no": "not in the plan"}.get(
                    f.get("remedy_in_design"), "pending")
            rows.append(
                f'<tr><td>{sev_badge(f.get("severity"))}<div class="fid">{esc(fid)}</div></td>'
                f'<td class="mono">{esc(os.path.basename(f["file"]))}:{esc(f.get("line"))}</td>'
                f'<td class="quote">{esc(f["ben_would_say"])}</td>'
                f'<td class="mono small">{esc(ids_in(f.get("evidence", "")))}</td>'
                f'<td class="small">{st}</td></tr>')
        head = ('<table class="findings"><thead><tr><th>severity, id</th><th>where (PR head)</th>'
                '<th>what Ben would write</th><th>evidence</th><th>in the new branch</th></tr></thead><tbody>')
        nits_start = next((i for i, f in enumerate(fs) if f.get("severity") == "nit"), len(fs))
        parts.append(head + "".join(rows[:nits_start]) + "</tbody></table>")
        if nits_start < len(fs):
            parts.append(f'<details><summary>{len(fs) - nits_start} nits for PR {pr}</summary>' + head +
                         "".join(rows[nits_start:]) + "</tbody></table></details>")
    if dropped:
        items = "".join(f'<li><span class="mono">{esc(d["id"])}</span> {esc(d["file"].split("/")[-1])}:{esc(d.get("line"))}: '
                        f'{esc(d["ben_would_say"][:220])} <span class="muted">(refuted: '
                        f'{esc(next((v["reason"][:200] for v in d.get("votes", []) if v.get("refuted")), ""))})</span></li>'
                        for d in dropped)
        parts.append(f'<details><summary>{len(dropped)} refuted predictions (kept for the record)</summary><ul>{items}</ul></details>')
    return "\n".join(parts)


def bda_section(status):
    """3bda gate: build records and test rows, when present."""
    rows = []
    for tag in ("bp2", "bp2v", "bp3", "bp3v", "bp4", "bp4v"):
        done = None
        try:
            done = open(os.path.join(RESULTS, f"build-{tag}.done")).read().strip()
        except OSError:
            pass
        tip = ""
        try:
            for line in open(os.path.join(RESULTS, f"build-{tag}.txt")):
                if line.startswith("tip "):
                    tip = line.split()[1][:10]
                if line.startswith("targets:"):
                    m = re.search(r"in (\d+) s", line)
                    tip += f" ({int(m.group(1)) // 60} min)" if m else ""
        except OSError:
            pass
        rows.append((tag, done or "not run", tip))
    tests = []
    try:
        for line in open(os.path.join(RESULTS, "tests.txt")):
            if line.startswith("#") or not line.strip():
                continue
            tests.append([c.strip() for c in line.split("|")])
    except OSError:
        pass
    s = ['<table><thead><tr><th>tag</th><th>meaning</th><th>build</th><th>head (duration)</th></tr></thead><tbody>']
    meaning = {"bp2": "PR2' option OFF", "bp2v": "PR2' option ON", "bp3": "PR3' option OFF", "bp3v": "PR3' option ON",
               "bp4": "PR4' option OFF", "bp4v": "PR4' option ON"}
    for tag, done, tip in rows:
        s.append(f'<tr><td class="mono">{tag}</td><td>{meaning[tag]}</td><td>{esc(done)}</td><td class="mono">{esc(tip)}</td></tr>')
    s.append("</tbody></table>")
    if tests:
        s.append('<table><thead><tr><th>tag</th><th>test</th><th>assertions</th><th>exit code</th><th>notes</th></tr></thead><tbody>')
        for t in tests:
            if len(t) < 4:
                continue
            ok = t[3] == "0"
            s.append(f'<tr><td class="mono">{esc(t[0])}</td><td class="mono">{esc(t[1])}</td><td>{esc(t[2])}</td>'
                     f'<td class="{"ok" if ok else "bad"}">{esc(t[3])}</td><td class="small">{esc(" | ".join(t[4:])[:160])}</td></tr>')
        s.append("</tbody></table>")
    else:
        s.append('<p class="muted">Unit-test rows: pending (the 3bda gate has not reported yet).</p>')
    return "\n".join(s)


def branch_cards(status, counts_by_head):
    cards = []
    meta = {
        "2": ("PR2'", "jhan-vnnik-2-amx-5047", "4957", "jhan-vnnik-2-amx", "the VNNI AMX kernel behind the cache"),
        "3": ("PR3'", "jhan-vnnik-3-shared-save-5047", "4958", "jhan-vnnik-3-shared-save", "shared block save through the cache"),
        "4": ("PR4'", "jhan-vnnik-4-tail-block-5047", "4959", "jhan-vnnik-4-tail-block", "the row-major tail block inside the cache"),
    }
    for n, (name, branch, pr, base, title) in meta.items():
        b = status.get("branches", {}).get(n, {})
        url = b.get("pr_url")
        link = f'<a href="{esc(url)}">{esc(url)}</a>' if url else '<span class="muted">draft PR: pending</span>'
        head = b.get("head", "pending")
        commits = b.get("commits", [])
        clist = "".join(f'<li><span class="mono">{esc(c.get("sha", "")[:10])}</span> {esc(c.get("subject", ""))}</li>' for c in commits)
        facts = "".join(f"<li>{esc(x)}</li>" for x in b.get("pr_body_facts", []))
        risks = "".join(f"<li>{esc(x)}</li>" for x in b.get("residual_risks", []))
        ver = b.get("matrix", "pending")
        new_counts = counts_by_head.get(f"new{pr}")
        outside = ""
        if new_counts:
            outside = ", ".join(f"{f} {total(new_counts.get(f))}" for f in ("self_attention.hpp", "model.hpp", "full.hpp"))
            outside = f" Layout identifiers outside the cache at the new head: {outside} (PR head: " + \
                      ", ".join(f"{total(counts_by_head.get(pr, {}).get(f))}" for f in ("self_attention.hpp", "model.hpp", "full.hpp")) + ")."
        cards.append(f"""
<div class="card">
<h3>{esc(name)}: {esc(title)}</h3>
<p><span class="mono">{esc(branch)}</span> at <span class="mono">{esc(head[:10] if head != 'pending' else head)}</span>, draft PR against <span class="mono">{esc(base)}</span> (PR {pr}'s branch). {link}</p>
<p>{esc(b.get('summary', 'Summary pending: the implementation workflow has not finished.'))}{outside}</p>
{('<details><summary>' + str(len(commits)) + ' commits after the PR head</summary><ol>' + clist + '</ol></details>') if commits else ''}
{('<p><b>Facts for the PR body.</b></p><ul>' + facts + '</ul>') if facts else ''}
<p><b>Verification.</b> Syntax matrix on claude-box: {esc(ver)}. 3bda: {esc(b.get('bda', 'pending'))}.</p>
{('<p><b>What the syntax matrix cannot prove.</b></p><ul>' + risks + '</ul>') if risks else ''}
</div>""")
    return "\n".join(cards)


def main():
    result = read_json(os.path.join(SCRATCH, "stack", "wfA-result.json"), {"kept": [], "dropped": [], "critics": []})
    status = read_json(os.path.join(HERE, "status.json"), {}) or {}
    new_heads = {n: b.get("head") for n, b in status.get("branches", {}).items() if b.get("head")}
    counts_by_head = collections.OrderedDict()
    for key, (sha, _) in HEADS.items():
        counts_by_head[key] = layout_counts(sha)
    for n, sha in new_heads.items():
        counts_by_head[f"new495{int(n) + 5}"] = layout_counts(sha)
    kept = result.get("kept", [])
    n_block = sum(1 for f in kept if f.get("severity") == "block")
    n_pr = {pr: sum(1 for f in kept if str(f["pr"]) == pr) for pr in ("4957", "4958", "4959")}
    opened = sum(1 for b in status.get("branches", {}).values() if b.get("pr_url") and b.get("pr_url") != "pending")
    bda = status.get("bda_summary") or "pending"

    # layout identifier counts table
    heads_for_table = list(HEADS.keys()) + [k for k in counts_by_head if k.startswith("new")]
    label = {"base": "4956 (base)", "ben": "5047 (Ben)", "4957": "4957", "4958": "4958", "4959": "4959",
             "new4957": "PR2'", "new4958": "PR3'", "new4959": "PR4'"}
    tbl = ['<table><thead><tr><th>file</th>' + "".join(f"<th>{esc(label.get(k, k))}</th>" for k in heads_for_table) + "</tr></thead><tbody>"]
    for f in FILES:
        tbl.append(f'<tr><td class="mono">{esc(f)}</td>' + "".join(
            f'<td class="num">{total(counts_by_head[k].get(f)) if counts_by_head.get(k) and counts_by_head[k].get(f) is not None else "?"}</td>'
            for k in heads_for_table) + "</tr>")
    tbl.append("</tbody></table>")
    ident_list = ", ".join(IDENTS)

    short = (f"PR 5047 (Ben's) makes the cache file h/tron/models/kv_cache.hpp the only place that knows whether a K row is "
             f"stored row-major or in the VNNI layout: the attention, model and scheduler code call page operations such as "
             f"score_k and set_k_row and never test the layout themselves. PRs 4957, 4958 and 4959 were written before PR 5047 "
             f"and still test the layout in those three files, and a mock review of them (written by agents from the rules his two "
             f"commits show, then checked line by line against the code, not a review Ben wrote) lists {len(kept)} objections "
             f"({n_block} of them blocking) that he would raise. Three new draft PRs re-express the three PRs on his structure "
             f"({opened} of 3 open), each gated by the 22-cell syntax matrix and by the 3bda builds and unit tests ({bda}).")

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ben and the VNNI Stack</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root {{ color-scheme: light; --bg:#ffffff; --fg:{C_INK}; --muted:{C_MUTED}; --line:{C_GRID}; --pr:{C_PR}; --new:{C_NEW}; --cache:{C_CACHE}; --soft:#f5f7fa; }}
html {{ background: var(--bg); }}
body {{ margin:0; background:var(--bg); color:var(--fg); font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif; font-size:15px; line-height:1.5;
  padding-block: 24px 60px; padding-left:max(16px, env(safe-area-inset-left,0px)); padding-right:max(16px, env(safe-area-inset-right,0px)); }}
main {{ max-width: 1100px; margin: 0 auto; }}
h1 {{ font-size: 30px; line-height:1.2; margin: 0 0 6px; text-wrap: balance; }}
h2 {{ font-size: 22px; margin: 40px 0 10px; padding-top: 10px; border-top: 2px solid var(--line); text-wrap: balance; }}
h3 {{ font-size: 17px; margin: 24px 0 8px; }}
p, li {{ max-width: 80ch; }}
.lede {{ color: var(--muted); margin: 0 0 18px; }}
.short {{ background: var(--cache); border-left: 4px solid var(--new); padding: 12px 16px; border-radius: 6px; }}
.short p {{ margin: 6px 0; max-width: none; }}
.mono {{ font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; }}
.small {{ font-size: 13px; }}
.muted {{ color: var(--muted); }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0 18px; font-size: 14px; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 7px 8px; vertical-align: top; text-align: left; }}
th {{ background: var(--soft); font-weight: 600; font-size: 13px; letter-spacing: .02em; }}
.tablewrap {{ overflow-x: auto; }}
table.findings td.quote {{ max-width: 46ch; }}
.badge {{ display:inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap; }}
.sev-block {{ background:#ffe3e3; color:#c92a2a; }} .sev-should {{ background:#fff3bf; color:#8a6d00; }} .sev-nit {{ background:#e9ecef; color:#495057; }}
.fid {{ font-family:"JetBrains Mono", monospace; font-size: 11.5px; color: var(--muted); margin-top: 4px; }}
.ok {{ color:#2b8a3e; font-weight:600; }} .bad {{ color:#c92a2a; font-weight:600; }}
figure {{ margin: 16px 0 22px; }} figure svg {{ max-width: 100%; height: auto; display: block; }} figcaption {{ font-size: 13px; color: var(--muted); margin-top: 6px; max-width: 90ch; }}
.card {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px 16px; margin: 12px 0; background: #fff; }}
.cards {{ display: grid; grid-template-columns: 1fr; gap: 12px; }}
dl.words {{ display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; }} dl.words dt {{ font-weight: 600; }} dl.words dd {{ margin: 0; }}
details {{ margin: 8px 0 14px; }} summary {{ cursor: pointer; color: var(--new); font-weight: 500; }}
.lesson {{ display:grid; grid-template-columns: 2.2em 1fr; gap: 8px; margin: 8px 0; }} .lesson b {{ color: var(--new); }}
@media (max-width: 700px) {{ dl.words {{ grid-template-columns: 1fr; }} h1 {{ font-size: 24px; }} }}
</style>
</head>
<body>
<main>
<h1>What Ben would dislike in PRs 4957, 4958 and 4959, and the branches that answer him</h1>
<p class="lede">Predictions from his PR 5047 commits and his 28 review comments on jhan's PRs. Three new branches re-express the stack on his structure. Generated {now} by exec/benstack-20261021/gen_page.py.</p>

<div class="short"><p><b>Short version.</b> {esc(short)}</p></div>

<h2 id="words">Words used here</h2>
<dl class="words">
<dt>tron</dt><dd>the inference program. runtron is its command-line tool.</dd>
<dt>the cache</dt><dd>h/tron/models/kv_cache.hpp: <span class="mono">struct page</span> (one 64-token KV page) and <span class="mono">struct book</span> (the pages of one model instance).</dd>
<dt>the option</dt><dd>the CMake option TRON_K_VNNI. When it is on, the K cache of 128-dimension heads is stored in the AMX VNNI layout (pairs of tokens interleaved per dimension, the layout the AMX tile multiply reads directly).</dd>
<dt>a VNNI slot</dt><dd>one K storage slot that uses that layout. A row-major slot stores one token's row after another.</dd>
<dt>AMX, AVX-512</dt><dd>Intel tile-matrix instructions (the fast QK path) and 512-bit vector instructions (the software path).</dd>
<dt>the kernel, the reader, the dotter</dt><dd>qk_vnni_128x4 (AMX QK scores over a VNNI page), k_vnni::qk_group (AVX-512 scores over the VNNI plane), and the per-token AVX-512 dot product over a row-major row.</dd>
<dt>a block, a lane, a run</dt><dd>16 consecutive tokens of a page, one of the 16 positions of a block, and consecutive minibatch tokens inside one block of one page.</dd>
<dt>the window</dt><dd>the shared K store of one (layer, pass) in which the idle main helper threads take part (PR 4958).</dd>
<dt>layout identifier</dt><dd>a name that a code line can only use when it knows how K is stored: {esc(ident_list)}. The counts below exclude comments.</dd>
<dt>P1-P5, C1-C16</dt><dd>Ben's taste profile: P = what his PR 5047 commits show, C = what his review comments show (ids in the evidence column).</dd>
<dt>PR2', PR3', PR4'</dt><dd>the new branches jhan-vnnik-2-amx-5047, -3-shared-save-5047, -4-tail-block-5047: each PR branch plus a merge of the previous new branch (PR2' merges Ben's head) plus the re-expression.</dd>
<dt>the syntax matrix</dt><dd>22 compiler runs on claude-box (two generated trees x option off/on x five test files, plus the AMX kernel file) that parse and instantiate the templates but do not link or run; nix is not available there, so it is the only local compile check.</dd>
<dt>3bda</dt><dd>delphi-3bda, the Intel server where real builds and unit tests run.</dd>
</dl>

<h2 id="lessons">1. The five lessons of PR 5047</h2>
<p>PR 5047 is Ben's rewrite of PR 4956 (the VNNI K layout and its readers). Its two commits show what he wants from the rest of the stack.</p>
<div class="lesson"><b>P1</b><div>One owner of the K layout: the cache. His second commit moved the scoring (page::score_k), the AMX attempt (page::try_score_k_amx) and the activation-row conversion (set_k_row with an expression) into the page. The count of the layout flag k_vnni::layout_on went from 2/1/1 to 0/0/0 in self_attention.hpp, model.hpp and full.hpp.</div></div>
<div class="lesson"><b>P2</b><div>No public raw K views: the eight page::k() overloads and page::k_packed are gone, page::kv_block is private, and tests go through t/kv_cache_helpers.hpp.</div></div>
<div class="lesson"><b>P3</b><div>One control flow per function: his first commit made the token-selection loop only select tokens into a 64-bit mask. Scoring happens once after the loop. The placeholder lambdas for the other layout are gone.</div></div>
<div class="lesson"><b>P4</b><div>A call site asks the cache and takes the answer: apply_dense_amx_page returns false when the cache declines at run time, instead of a compile-time layout clause at the call site.</div></div>
<div class="lesson"><b>P5</b><div>His own words in the PR body: "The previously-proposed implementation was a bit spaghetti for my liking."</div></div>

{figure(layout_chart(counts_by_head, {k: v for k, v in new_heads.items()}), "Layout identifiers (code lines) outside the cache, per file: the orange dot is the PR as opened, the blue dot the new branch, the grey tick Ben's head (0 everywhere). The branches bring every row to 0.")}
<div class="tablewrap">{''.join(tbl)}</div>

<h2 id="objections">2. What he would dislike, per PR</h2>
{findings_section(result, status)}

<h2 id="branches">3. The new branches and their draft PRs</h2>
<p>Each new branch is the PR's own branch plus a merge of the previous new branch (PR2' merges Ben's head directly) plus topical commits that re-express the PR on his structure. Stored bytes, scores and test expectations are preserved. The named exceptions are in each PR body. The draft PRs target the PR branches, so the diff a reviewer sees is exactly the re-expression.</p>
<div class="cards">
{branch_cards(status, counts_by_head)}
</div>

<h3>What changes, mechanism by mechanism</h3>
{figure(mech_pr2(), "PR 4957 chose the query packer and the QK kernel from the layout flag in two functions of attention code and read the plane through a public view. PR2' asks the page for both: page::pack_q_amx and page::try_score_k_amx.")}
{figure(mech_pr3(), "PR 4958 kept two store bodies in model.hpp and a hand-written window protocol. PR3' has one store flow through page::set_k_block (which serves every slot) and runs the window as a phase of tron::barrier with greedy_range claims.")}
{figure(mech_pr4(), "PR 4959 scored tail-block tokens inside the selection loop and gated AMX on a block mask in attention code. PR4' keeps Ben's loop. The page declines or splits the scoring by block layout, and the FPGA staging keeps Ben's row copy.")}

<h2 id="bda">4. 3bda gate: builds and unit tests</h2>
<p>Two builds per branch (option OFF and ON, AMX dispatch ON) and five unit tests per build with the fake device, plus two kill-switch runs (TRON_AMX_DISABLE=1). Scripts: exec/benstack-20261021/{{build.sh, tests.sh, run-one.sh}}.</p>
{bda_section(status)}
{('<p>' + esc(' '.join(status['bda_notes']) if isinstance(status.get('bda_notes'), list) else status.get('bda_notes', '')) + '</p>') if status.get('bda_notes') else ''}

<h2 id="open">5. Open items for jhan</h2>
<ul>
{''.join('<li>' + esc(x) + '</li>' for x in status.get('open_items', ['pending']))}
</ul>

<h2 id="method">6. Method and provenance</h2>
<ul>
<li>Evidence: Ben's two PR 5047 commits (e17a12ff09, ade89a9d9c) and his 28 review comments on jhan's PRs (ben-corpus.md, comment ids in the profile), the three PR diffs at their heads (26b86a279a, b39765ec29, 6b081187e1), and simulated merges of his head into each PR (git merge-tree: 6, 9 and 13 conflict hunks).</li>
<li>Prediction workflow wf_e4c2f652-7e0: 12 finders (four lenses x three PRs), three refuters per candidate, four critics of the design brief; 277 agents. Kept = at least two of three refuters could not refute.</li>
<li>Design brief v2 (exec/benstack-20261021/design.md) records the critics' corrections: tron::barrier and greedy_range instead of hand-written counters, one set_k_block for every slot, no k_staging_row, the recording loop folded into the mark loop, and the fact that the +0.19 s llama prefill delta of PR 5047 is a CPU-attention cell and not the staging copy.</li>
<li>Implementation workflows (one per branch): implementer, four reviewer lenses (Ben persona, merge and behaviour audit, Wade checks, prose), three refuters per finding, fixer, final audit. Ids in status.json.</li>
<li>Not verified here: run-time behaviour beyond the 3bda unit tests (performance at the new heads is pending measurement, and every PR body says so). Ben's record has no comment on CI lanes, PR bodies or the deb preset, so those are reported as decisions, not objections.</li>
</ul>
</main>
</body>
</html>
"""
    page = no_semicolons(page)
    with open(OUT, "w") as f:
        f.write(page)
    # render the SVGs for the eye check
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    try:
        import cairosvg  # noqa
        for name, svg in (("layout", layout_chart(counts_by_head, new_heads)), ("pr2", mech_pr2()), ("pr3", mech_pr3()), ("pr4", mech_pr4())):
            cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(HERE, "out", f"{name}.png"), output_width=1400)
    except Exception as e:  # noqa
        print("render skipped:", e)
    print(OUT, os.path.getsize(OUT), "bytes; placeholders:", page.count("pending"))


if __name__ == "__main__":
    main()
