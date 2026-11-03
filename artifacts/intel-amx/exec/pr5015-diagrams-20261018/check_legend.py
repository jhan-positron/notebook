"""Check every figure's declared "Colour and font scheme" against the styles
its SVG really uses.

Usage: python3 check_legend.py <page.html>            (page mode)
       python3 check_legend.py figs/<module>.py        (module mode: the
                                                        module's figures only)
For each figure: the SVG's rect styles (fill, stroke, dashed?, thick?), its
arrow colours (polylines with an arrowhead), and its fonts (monospace, sans,
the citation colour, bold tags) are collected and compared with the
data-style keys of the figure's legend chips.
  MISSING = a style the SVG uses that no legend entry covers
  UNUSED  = a legend entry whose style the SVG never uses
Structural frames (white, soft-grey or no fill with the thin grey line colour)
and the page background are not required; a figure MAY declare one ("ctx",
"lane") and it counts as used when the SVG draws it. Thin lines without an
arrowhead (<line>, a polyline with no marker) are optional in the same way: a
("label", "line", colour[, dashed]) entry counts as used when the SVG draws
one. A ("label", "multi", [...]) entry declares several styles at once. Coloured text (a fill
other than ink, muted, cite) needs an entry with that colour: a box, an arrow,
or a ("label", "text", colour) entry. Exit 1 when any figure has a MISSING or
UNUSED entry.
"""
import html
import importlib.util
import os
import re
import sys

G = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, G)
sys.path.insert(0, os.path.join(G, "figs"))
from svg_helpers import C, style_key, _norm  # noqa: E402

CITE = _norm(C["cite"])
NEUTRAL_TEXT = {_norm(C["ink"]), _norm(C["muted"]), CITE, "#fff", "", "none", "#000", "#000000",
                _norm(C["line"]), _norm(C["cite"])}
STRUCT_STROKES = {_norm(C["line"]), _norm(C["soft"]), "none", ""}


def styles_of(blob):
    used = {}
    struct_used = set()  # structural styles the SVG draws (optional in the legend)
    for m in re.finditer(r"<rect [^>]*>", blob):
        r = m.group(0)
        fill = re.search(r'fill="([^"]+)"', r)
        stroke = re.search(r'stroke="([^"]+)"', r)
        dash = re.search(r'stroke-dasharray="([^"]+)"', r)
        sw = re.search(r'stroke-width="([^"]+)"', r)
        f = _norm(fill.group(1) if fill else "none")
        st = _norm(stroke.group(1) if stroke else "none")
        thick = float(sw.group(1)) >= 2.4 if sw else False
        if st in STRUCT_STROKES and f in ("#fff", "none", _norm(C["soft"]), _norm(C["bg"]) if "bg" in C else "x"):
            struct_used.add(style_key(f, st, bool(dash), thick))
            continue  # a frame, a lane, a grid line, a background
        if st == "none" and f in ("#fff", "none"):
            continue
        key = style_key(f, st, bool(dash), thick)
        used[key] = used.get(key, 0) + 1
    for m in re.finditer(r"<polyline [^>]*marker-end[^>]*>", blob):
        st = re.search(r'stroke="([^"]+)"', m.group(0))
        key = f"arrow:{_norm(st.group(1) if st else 'none')}"
        used[key] = used.get(key, 0) + 1
    line_used = set()  # thin lines without an arrowhead (optional in the legend)
    for m in re.finditer(r"<(?:line|polyline) [^>]*>", blob):
        r = m.group(0)
        if "marker-end" in r:
            continue
        st = re.search(r'stroke="([^"]+)"', r)
        dash = re.search(r'stroke-dasharray="([^"]+)"', r)
        line_used.add(f"line:{_norm(st.group(1) if st else 'none')}:{'d' if dash else 's'}")
    fonts = set()
    coloured_text = set()
    for m in re.finditer(r'<text [^>]*style="([^"]*)"[^>]*>([^<]*)</text>', blob):
        st, txt = m.group(1), html.unescape(m.group(2)).strip()
        mono = "monospace" in st
        fill = re.search(r"fill:([^;]+)", st)
        fill = _norm(fill.group(1)) if fill else ""
        bold = "font-weight:700" in st or "font-weight:600" in st
        if fill == CITE and mono:
            fonts.add("font:cite")
        elif mono:
            fonts.add("font:mono")
        else:
            fonts.add("font:sans")
        # a change tag: the tag word itself, or a bold text that starts with "new "
        # (a question such as "new unit?" is a decision's label, not a tag)
        if txt in ("new", "changed", "removed", "new (kv_cache.hpp)") or \
                (txt.startswith("new ") and bold and not txt.endswith("?")):
            fonts.add("font:tag")
        if fill and fill not in NEUTRAL_TEXT:
            coloured_text.add(fill)
    for f in fonts:
        used[f] = used.get(f, 0) + 1
    return used, coloured_text, struct_used | line_used


def declared_of(fig_html):
    m = re.search(r'<div class="figlegend">(.*?)</div>', fig_html, flags=re.S)
    if not m:
        return None
    # a "multi" entry carries several space-separated styles
    return [k for ds in re.findall(r'data-style="([^"]+)"', m.group(1)) for k in ds.split()]


SHOW = "--show" in sys.argv


def check_figure(fid, blob, fig_html):
    used, coloured_text, struct_used = styles_of(blob)
    decl = declared_of(fig_html)
    problems = []
    if SHOW:
        print(f"--- {fid} uses:")
        for key in sorted(used):
            print(f"      {key}  ({used[key]}x)")
        if coloured_text:
            print(f"      coloured text: {sorted(coloured_text)}")
    if decl is None:
        return [f"{fid}: NO LEGEND (figure(..., legend=[...]) missing)"]
    decl_set = set(decl)
    decl_strokes = {d.split(":")[2] for d in decl if d.startswith("box:")} | \
                   {d.split(":")[1] for d in decl if d.startswith(("arrow:", "text:"))}
    for key in sorted(used):
        if key in decl_set:
            continue
        if key.startswith("font:tag") and "font:tag" in decl_set:
            continue
        problems.append(f"{fid}: MISSING {key} (used {used[key]}x)")
    for d in decl:
        if d in used or (d == "font:tag" and "font:tag" in used):
            continue
        if d in struct_used:
            continue  # a declared frame / context box the SVG draws
        if d.startswith("text:") and d.split(":")[1] in coloured_text:
            continue  # a declared text colour the SVG uses
        problems.append(f"{fid}: UNUSED {d}")
    for c in sorted(coloured_text):
        if c not in decl_strokes:
            problems.append(f"{fid}: MISSING coloured text {c} (no entry with that colour)")
    return problems


def check_html(figs_html):
    allp = []
    for fig_html in figs_html:
        m = re.search(r'(<svg id="([A-Za-z0-9_-]+)".*?</svg>)', fig_html, flags=re.S)
        if not m:
            continue
        allp.extend(check_figure(m.group(2), m.group(1), fig_html))
    return allp


def main(path):
    if path.endswith(".html"):
        src = open(path, encoding="utf-8").read()
        figs = re.findall(r"<figure.*?</figure>", src, flags=re.S)
    else:
        spec = importlib.util.spec_from_file_location("figmod", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        figs = []
        for name in sorted(dir(mod)):
            if re.fullmatch(r"b\d+[a-z]?", name) and callable(getattr(mod, name)):
                figs.append(getattr(mod, name)())
        if hasattr(mod, "figs"):
            figs.extend(mod.figs())
        elif hasattr(mod, "fig"):
            figs.append(mod.fig())
        figs = [f for x in figs for f in re.findall(r"<figure.*?</figure>", x, flags=re.S)]
    problems = check_html(figs)
    print(f"{os.path.basename(path)}: {len(figs)} figures, {len(problems)} legend problems")
    for p in problems:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main([a for a in sys.argv[1:] if not a.startswith("--")][0]))
