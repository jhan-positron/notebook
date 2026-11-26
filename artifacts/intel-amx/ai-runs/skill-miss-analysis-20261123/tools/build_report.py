#!/usr/bin/env python3
"""Build the HTML report from the run records.

Usage: build_report.py <output.html>
Numbers come from the journals under out/ through metrics.py. Text is in report_template.html.
"""
import html, json, pathlib, re, subprocess, sys

A = pathlib.Path("/home/jhan/workspace/ai-runs/skill-miss-analysis-20261123")
R = pathlib.Path("/home/jhan/workspace/ai-runs/skill-replay-20261123")
sys.path.insert(0, str(A / "tools"))
import metrics  # noqa: E402

OUT = pathlib.Path(sys.argv[1])
esc = html.escape

# ------------------------------------------------------------------ data
JOURNALS = {
    "base_5022": A / "out/replay-baseline-journal.jsonl",
    "v1_5022": A / "out/replay-v1-pr5022-journal.jsonl",
    "v1_held": A / "out/replay-v1-heldout-journal.jsonl",
    "v2_5022": A / "out/replay-v2-pr5022-journal.jsonl",
    "v2_held": A / "out/replay-v2-heldout-journal.jsonl",
    "v3_5022": A / "out/replay-v3-pr5022-journal.jsonl",
    "v3_held": A / "out/replay-v3-heldout-journal.jsonl",
}
VERSIONS = ["v1", "v2", "v3"]


def rows_of(key):
    p = JOURNALS[key]
    if not p.exists():
        return []
    out = []
    for lab, res in metrics.load(p):
        subject = "control" if lab.startswith("control") else "dispatch"
        out.append(metrics.score(lab, res, subject))
    return out


def skill_of(label):
    parts = label.split(":")
    return parts[1] if parts[0] == "replay" else parts[2]


def group(rows, pred):
    g = {}
    for r in rows:
        if not pred(r["label"]):
            continue
        k = skill_of(r["label"])
        d = g.setdefault(k, {"runs": 0, "gap": 0, "define": 0, "wrong": 0, "sev": []})
        d["runs"] += 1
        d["gap"] += r["gap"]
        d["define"] += r["define"]
        d["wrong"] += r["wrong"]
        if r["sev"]:
            d["sev"].append(r["sev"])
    return g


def pool(groups):
    out = {}
    for g in groups:
        for k, d in g.items():
            o = out.setdefault(k, {"runs": 0, "gap": 0, "define": 0, "wrong": 0, "sev": []})
            for f in ("runs", "gap", "define", "wrong"):
                o[f] += d[f]
            o["sev"] += d["sev"]
    return out


base = group(rows_of("base_5022"), lambda l: True)
ed = {v: group(rows_of(f"{v}_5022"), lambda l: True) for v in VERSIONS}
held_base = group(rows_of("v1_held"), lambda l: l.startswith("pr5572:baseline"))
held = {v: group(rows_of(f"{v}_held"), lambda l: l.startswith("pr5572:candidate")) for v in VERSIONS}
ctrl = {v: group(rows_of(f"{v}_held"), lambda l: l.startswith("control")) for v in VERSIONS}
MISSING = [k for k, p in JOURNALS.items() if not p.exists()]

ed_all = pool(ed.values())
held_all = pool(held.values())
ctrl_all = pool(ctrl.values())


def tot(g, field):
    return sum(d[field] for d in g.values())


def frac(g, skill, field="define"):
    d = g.get(skill)
    return (d[field], d["runs"]) if d else None


def kn(pair):
    return "not run" if pair is None else f"{pair[0]} of {pair[1]}"


SEV_WORD = {"blocker": "must fix before the merge", "should-fix": "should fix", "question": "question",
            "nit": "small remark", "info": "information only"}


def sev_text(g, skill):
    d = g.get(skill)
    if not d or not d["sev"]:
        return "none"
    uniq = sorted(set(d["sev"]), key=metrics.SEV_ORDER.index, reverse=True)
    return ", ".join(f"{SEV_WORD[s]} ({d['sev'].count(s)})" for s in uniq)


SKILLS_5022 = ["tron-code-review", "folks-code-review", "cpp-coding-guide", "ben-review", "positron-code-review", "all-five"]
NAME = {"all-five": "all five together"}

n_base, k_base_gap, k_base_def = tot(base, "runs"), tot(base, "gap"), tot(base, "define")
n_ed, k_ed_def, k_ed_gap = tot(ed_all, "runs"), tot(ed_all, "define"), tot(ed_all, "gap")
n_hb, k_hb_def = tot(held_base, "runs"), tot(held_base, "define")
n_he, k_he_def = tot(held_all, "runs"), tot(held_all, "define")
n_ctrl, k_ctrl_def, k_ctrl_gap = tot(ctrl_all, "runs"), tot(ctrl_all, "define"), tot(ctrl_all, "gap")
k_wrong = tot(ed_all, "wrong") + tot(held_all, "wrong")

# ------------------------------------------------------------------ chart (dumbbell)
C_BEFORE = "#86b6ef"
C_AFTER = "#184f95"


def dumbbell(rows, title_id):
    """rows: (label, before (k, n) or None, after (k, n) or None)."""
    left, right, top, rh = 190, 150, 16, 46
    w = 760
    plot = w - left - right
    h = top + rh * len(rows) + 30
    x = lambda p: left + plot * p
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="{title_id}" class="chart">']
    o.append(f'<title id="{title_id}">Share of replay runs that propose the per-target define, before and with the edits</title>')
    for p, lab in ((0, "0%"), (0.5, "50%"), (1, "100%")):
        o.append(f'<line x1="{x(p):.1f}" y1="{top - 8}" x2="{x(p):.1f}" y2="{h - 26}" class="grid"/>')
        o.append(f'<text x="{x(p):.1f}" y="{h - 8}" class="tick" text-anchor="middle">{lab}</text>')
    for i, (label, b, a) in enumerate(rows):
        y = top + rh * i + rh / 2
        o.append(f'<text x="{left - 14}" y="{y + 4:.1f}" class="rowlab" text-anchor="end">{esc(label)}</text>')
        pb = (b[0] / b[1]) if b else None
        pa = (a[0] / a[1]) if a else None
        if pb is not None and pa is not None and pa != pb:
            o.append(f'<line x1="{x(pb):.1f}" y1="{y:.1f}" x2="{x(pa):.1f}" y2="{y:.1f}" class="link"/>')
        if pb is not None:
            o.append(f'<circle cx="{x(pb):.1f}" cy="{y:.1f}" r="7" fill="{C_BEFORE}" class="dot"><title>{esc(label)}, before the edits: {b[0]} of {b[1]} runs</title></circle>')
            anchor, dx = ("start", 11) if (pa is None or pb <= pa) else ("end", -11)
            if pb >= 0.85 and (pa is None or pb <= pa):
                anchor, dx = "end", -11
            o.append(f'<text x="{x(pb) + dx:.1f}" y="{y - 11:.1f}" class="val" text-anchor="{anchor}">{b[0]} of {b[1]}</text>')
        if pa is not None:
            o.append(f'<circle cx="{x(pa):.1f}" cy="{y:.1f}" r="7" fill="{C_AFTER}" class="dot"><title>{esc(label)}, with the edits: {a[0]} of {a[1]} runs</title></circle>')
            anchor, dx = ("start", 13) if (pb is None or pa >= pb) else ("end", -13)
            o.append(f'<text x="{x(pa) + dx:.1f}" y="{y + 4:.1f}" class="val strong" text-anchor="{anchor}">{a[0]} of {a[1]}</text>')
    o.append("</svg>")
    return "\n".join(o)


chart_rows_5022 = [(NAME.get(s, s), frac(base, s), frac(ed_all, s)) for s in ["tron-code-review", "folks-code-review", "cpp-coding-guide", "all-five"]]
chart_rows_held = [(s, frac(held_base, s), frac(held_all, s)) for s in ["tron-code-review", "folks-code-review", "cpp-coding-guide"]]

# ------------------------------------------------------------------ tables


def table_5022():
    o = ['<div class="scroll"><table><thead><tr><th>Skill</th><th>Runs before</th><th>Reported the gap, before</th><th>Rating given, before</th>'
         '<th>Proposed the per-target define, before</th><th>Proposed it, version 1</th><th>version 2</th><th>version 3</th>'
         '<th>Rating given, with the edits</th></tr></thead><tbody>']
    for s in SKILLS_5022:
        b = base.get(s)
        if not b:
            continue
        o.append("<tr>"
                 f"<td>{esc(NAME.get(s, s))}</td><td class='num'>{b['runs']}</td>"
                 f"<td class='num'>{b['gap']} of {b['runs']}</td><td>{esc(sev_text(base, s))}</td>"
                 f"<td class='num'>{b['define']} of {b['runs']}</td>"
                 + "".join(f"<td class='num'>{kn(frac(ed[v], s))}</td>" for v in VERSIONS)
                 + f"<td>{esc(sev_text(ed_all, s)) if s in ed_all else 'not run (skill unchanged)'}</td></tr>")
    o.append("<tr class='total'>"
             f"<td>Total</td><td class='num'>{n_base}</td><td class='num'>{k_base_gap} of {n_base}</td><td></td>"
             f"<td class='num'>{k_base_def} of {n_base}</td>"
             + "".join(f"<td class='num'>{tot(ed[v], 'define')} of {tot(ed[v], 'runs')}</td>" for v in VERSIONS)
             + "<td></td></tr>")
    o.append("</tbody></table></div>")
    return "\n".join(o)


def table_held():
    o = ['<div class="scroll"><table><thead><tr><th>Skill</th><th>Reported the gap, before</th><th>Proposed the per-target define, before</th>'
         '<th>Proposed it, version 1</th><th>version 2</th><th>version 3</th></tr></thead><tbody>']
    for s in ["tron-code-review", "folks-code-review", "cpp-coding-guide"]:
        o.append("<tr>"
                 f"<td>{s}</td><td class='num'>{kn(frac(held_base, s, 'gap'))}</td><td class='num'>{kn(frac(held_base, s))}</td>"
                 + "".join(f"<td class='num'>{kn(frac(held[v], s))}</td>" for v in VERSIONS) + "</tr>")
    o.append("</tbody></table></div>")
    return "\n".join(o)


# Hand-read results for the control: the script cannot tell "do not add DEFINES" or a
# proposal for a separate new test program from a define for the test under review.
CTRL_READ = json.loads((A / "out/control-read.json").read_text()) if (A / "out/control-read.json").exists() else {}


def table_ctrl():
    o = ['<div class="scroll"><table><thead><tr><th>Skill</th><th>Version of the edits</th><th>Reported that the new case runs in no CI lane</th>'
         '<th>Rating given</th><th>Told the author to add the define to the test under review (wrong here)</th><th>What it proposed</th></tr></thead><tbody>']
    for i, v in enumerate(VERSIONS, 1):
        for s in ["tron-code-review", "folks-code-review", "cpp-coding-guide"]:
            d = ctrl[v].get(s)
            if not d:
                continue
            read = CTRL_READ.get(f"{v}:{s}", {})
            wrong = read.get("wrong", d["define"])
            o.append(f"<tr><td>{s}</td><td class='num'>{i}</td><td class='num'>{d['gap']} of {d['runs']}</td>"
                     f"<td>{esc(sev_text(ctrl[v], s))}</td><td class='num'>{wrong} of {d['runs']}</td><td>{esc(read.get('proposed', ''))}</td></tr>")
    o.append("</tbody></table></div>")
    return "\n".join(o)


k_ctrl_wrong = sum(CTRL_READ.get(f"{v}:{s}", {}).get("wrong", ctrl[v][s]["define"]) for v in VERSIONS for s in ctrl[v])


# ------------------------------------------------------------------ diffs of the proposed edits (version 3)
V3 = R / "skills-candidate-v3"
BASE = R / "skills-baseline"
FILES = ["tron-code-review/SKILL.md", "cpp-coding-guide/SKILL.md", "folks-code-review/SKILL.md", "folks-code-review/references/procedures.md"]


def diff_html(rel):
    p = subprocess.run(["diff", "-U1", str(BASE / rel), str(V3 / rel)], capture_output=True, text=True)
    out = []
    for line in p.stdout.splitlines()[2:]:
        if line.startswith("@@"):
            out.append(f'<div class="dh">{esc(line)}</div>')
        elif line.startswith("+"):
            out.append(f'<div class="da">{esc(line[1:]) or "&nbsp;"}</div>')
        elif line.startswith("-"):
            out.append(f'<div class="dd">{esc(line[1:]) or "&nbsp;"}</div>')
        else:
            t = line[1:]
            out.append(f'<div class="dc">{esc(t[:220] + (" [...]" if len(t) > 220 else "")) or "&nbsp;"}</div>')
    return "\n".join(out)


def diff_size(rel):
    p = subprocess.run(["diff", str(BASE / rel), str(V3 / rel)], capture_output=True, text=True)
    add = sum(1 for l in p.stdout.splitlines() if l.startswith(">"))
    rem = sum(1 for l in p.stdout.splitlines() if l.startswith("<"))
    return add, rem, (BASE / rel).stat().st_size, (V3 / rel).stat().st_size


# ------------------------------------------------------------------ final check of version 2
FINAL = {}
for s in ["tron-code-review", "folks-code-review", "cpp-coding-guide"]:
    p = A / f"out/final-check_{s}.json"
    if p.exists():
        FINAL[s] = json.loads(p.read_text())


def final_table():
    if not FINAL:
        return "<p>Insufficient data: the final check of version 2 had not returned when this page was built.</p>"
    o = ['<div class="scroll"><table><thead><tr><th>Skill</th><th>Verdict of the final check on version 2</th><th>Required changes checked</th>'
         '<th>Not applied, and it matters</th><th>New defects found</th></tr></thead><tbody>']
    for s, d in FINAL.items():
        na = sum(1 for x in d.get("not_applied", []) if x.get("matters") == "yes")
        o.append(f"<tr><td>{s}</td><td>{esc(d['verdict'])}</td><td class='num'>{d.get('required_changes_checked', '')}</td>"
                 f"<td class='num'>{na}</td><td class='num'>{len(d.get('new_defects', []))}</td></tr>")
    o.append("</tbody></table></div>")
    return "\n".join(o)


def opt(name, default):
    p = A / "out" / name
    return p.read_text() if p.exists() else default


# ------------------------------------------------------------------ page
TEMPLATE = (A / "tools/report_template.html").read_text()

subs = {
    "@@N_BASE@@": str(n_base), "@@K_BASE_GAP@@": str(k_base_gap), "@@K_BASE_DEF@@": str(k_base_def),
    "@@N_ED@@": str(n_ed), "@@K_ED_DEF@@": str(k_ed_def),
    "@@N_HB@@": str(n_hb), "@@K_HB_DEF@@": str(k_hb_def),
    "@@N_HE@@": str(n_he), "@@K_HE_DEF@@": str(k_he_def),
    "@@N_ALL_ED@@": str(n_ed + n_he), "@@K_ALL_ED_DEF@@": str(k_ed_def + k_he_def),
    "@@N_ALL_BASE@@": str(n_base + n_hb), "@@K_ALL_BASE_DEF@@": str(k_base_def + k_hb_def),
    "@@N_CTRL@@": str(n_ctrl), "@@K_CTRL_DEF@@": str(k_ctrl_def), "@@K_CTRL_GAP@@": str(k_ctrl_gap), "@@K_CTRL_WRONG@@": str(k_ctrl_wrong),
    "@@K_WRONG@@": str(k_wrong),
    "@@CHART_5022@@": dumbbell(chart_rows_5022, "ch1"),
    "@@CHART_HELD@@": dumbbell(chart_rows_held, "ch2"),
    "@@TABLE_5022@@": table_5022(), "@@TABLE_HELD@@": table_held(), "@@TABLE_CTRL@@": table_ctrl(),
    "@@FINAL_TABLE@@": final_table(),
    "@@FINAL_NOTE@@": opt("final-check-note.html", ""),
    "@@CTRL_NOTES@@": opt("control-notes.html", "<li>Insufficient data: the control runs were not read yet when this page was built.</li>"),
    "@@HELD_NOTES@@": opt("heldout-notes.html", ""),
    "@@C_BEFORE@@": C_BEFORE, "@@C_AFTER@@": C_AFTER,
}
for v in VERSIONS:
    n = tot(ed[v], "runs") + tot(held[v], "runs")
    k = tot(ed[v], "define") + tot(held[v], "define")
    subs[f"@@N_{v.upper()}@@"] = str(n)
    subs[f"@@K_{v.upper()}_DEF@@"] = str(k)
for i, f in enumerate(FILES):
    add, rem, b0, b1 = diff_size(f)
    subs[f"@@DIFF{i}@@"] = diff_html(f)
    subs[f"@@SIZE{i}@@"] = f"{add} lines added, {rem} lines replaced, {b0:,} to {b1:,} bytes"

page = TEMPLATE
for k, v in subs.items():
    page = page.replace(k, v)
left = sorted(set(re.findall(r"@@[A-Z0-9_]+@@", page)))
assert not left, f"unfilled placeholders: {left}"
OUT.write_text(page)
print(f"wrote {OUT} ({len(page):,} bytes); missing journals: {MISSING}")
print(f"PR 5022 before: gap {k_base_gap}/{n_base}, define {k_base_def}/{n_base}; edited (all versions): gap {k_ed_gap}/{n_ed}, define {k_ed_def}/{n_ed}")
print("  per version:", {v: f"{tot(ed[v], 'define')}/{tot(ed[v], 'runs')}" for v in VERSIONS})
print(f"PR 5572 before: define {k_hb_def}/{n_hb}; edited: {k_he_def}/{n_he}", {v: f"{tot(held[v], 'define')}/{tot(held[v], 'runs')}" for v in VERSIONS})
print(f"control: define {k_ctrl_def}/{n_ctrl}, gap {k_ctrl_gap}/{n_ctrl}; wrong-target sentences in edited runs: {k_wrong}")
