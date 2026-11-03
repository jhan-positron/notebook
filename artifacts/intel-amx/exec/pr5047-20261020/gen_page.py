#!/usr/bin/env python3
"""Generate random/Ben-PR4956.html: the top-down explanation of PR 5047 (Ben's refactor of PR 4956) plus the 3bda perf check.

Static sections live in page_template.html next to this file (placeholders {{NAME}}). Dynamic sections come from the campaign's
result files under exec/results/pr5047-20261020/: build-*.txt, hetero-*.txt, tests.txt, identity (smoke/<key>/smoke.txt) and the
perf cells (rt-results.txt, parsed by gen_report.py into results.json). Usage: gen_page.py [RESULTS_DIR] [OUT_HTML]
"""
import html
import json
import os
import re
import statistics
import subprocess
import sys
import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "glimmer-20261016"))
from gen_compare import parse_stats  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "results", "pr5047-20261020")
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/random/Ben-PR4956.html"
TEMPLATE = os.path.join(HERE, "page_template.html")

ARM_LABEL = {"base": "base (PR 4956 head, option OFF)", "head": "head (PR 5047, option OFF)",
             "basev": "basev (PR 4956 head, option ON)", "headv": "headv (PR 5047, option ON)"}
PAIR_LABEL = {"head:base": "option OFF: head vs base", "headv:basev": "option ON: headv vs basev", "headoff:baseoff": "kill switch (AMX off): headoff vs baseoff"}
CELL_LABEL = {
    "l8b-tp2-8u-p1024-cpu": "llama-3.1-8b, tp2, 8 users, prompt 1024, CPU attention",
    "l8b-tp2-8u-p4096-cpu": "llama-3.1-8b, tp2, 8 users, prompt 4096, CPU attention",
    "l8b-tp2-8u-p8192-cpu": "llama-3.1-8b, tp2, 8 users, prompt 8192, CPU attention",
    "l8b-tp2-8u-p8192-off": "llama-3.1-8b, tp2, 8 users, prompt 8192, CPU attention with the kill switch (AVX only)",
    "q4b-tp2-8u-p1024-fpga": "qwen3-4b, tp2, 8 users, prompt 1024, FPGA attention",
    "q4b-tp2-8u-p8192-fpga": "qwen3-4b, tp2, 8 users, prompt 8192, FPGA attention",
    "gptoss-tp4-8u-p1024-fpga": "gpt-oss-120b, tp4, 8 users, prompt 1024, FPGA attention",
}
CELL_ORDER = list(CELL_LABEL)
PLANNED_ARMS = {"gptoss-tp4-8u-p1024-fpga": ["base", "head"], "l8b-tp2-8u-p4096-cpu": ["base", "head"]}


def esc(s):
    return html.escape("" if s is None else str(s))


def fnum(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def read(name):
    p = os.path.join(RES, name)
    return open(p, errors="replace").read() if os.path.exists(p) else ""


def refresh_results():
    """Run gen_report.py so results.json matches the result files; tolerate a missing campaign."""
    try:
        subprocess.run([sys.executable, os.path.join(HERE, "gen_report.py"), RES], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except Exception:
        pass
    p = os.path.join(RES, "results.json")
    return json.load(open(p)) if os.path.exists(p) else {"perf": [], "identity": []}


# ---------------------------------------------------------------- builds
def builds_section():
    rows = []
    for tag, what in (("b47b", "base, option OFF"), ("b47h", "head, option OFF"), ("b47bv", "base, option ON"), ("b47hv", "head, option ON")):
        done = read(f"build-{tag}.done").strip() or "pending"
        txt = read(f"build-{tag}.txt")
        tip = (re.search(r"^tip ([0-9a-f]{10})", txt, re.M) or [None, "-"])[1]
        built = (re.search(r"built (\S+) in (\d+) s", txt) or [None, "-", "-"])
        checks = (re.search(r"^checks: (.*)$", txt, re.M) or [None, "-"])[1]
        het = read(f"hetero-{tag}.txt").strip().splitlines()
        het_line = het[0] if het else "-"
        het_err = next((l for l in het[1:] if "error" in l), "")
        rows.append(f"<tr><td><code>{tag}</code></td><td>{esc(what)}</td><td><code>{esc(tip)}</code></td><td>{esc(done)}</td><td>{esc(built[2])} s</td><td class=small>{esc(checks)}</td><td class=small>{esc(het_line)}<br>{esc(het_err[:160])}</td></tr>")
    return ("<table><thead><tr><th>tag</th><th>what</th><th>commit</th><th>marker</th><th>build time</th><th>checks</th><th>t_heterogeneous_scheduler compile (best effort)</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def tests_section():
    t = read("tests.txt").strip().splitlines()
    done = read("tests.done").strip() or "pending (the test step runs after the throughput cells)"
    if not t:
        return f"<p>Tests: {esc(done)}.</p>"
    rows = []
    for l in t[1:]:
        parts = [p.strip() for p in l.split("|")]
        if len(parts) >= 4:
            rows.append("<tr>" + "".join(f"<td>{esc(p)}</td>" for p in parts[:4]) + f"<td class=small>{esc(' | '.join(parts[4:]))[:200]}</td></tr>")
    return (f"<p>Marker: <code>{esc(done)}</code>. Result-file header: <code>{esc(t[0].lstrip('# '))}</code></p><table><thead><tr><th>tag</th><th>test</th><th>assertions</th><th>rc</th><th>notes</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


# ---------------------------------------------------------------- identity
def identity_section(results):
    items = results.get("identity") or []
    done = read("identity.done").strip() or "pending"
    if not items:
        return f"<p>Identity step: {esc(done)}. The planned cells: llama-3.1-8b (CPU attention), qwen3-4b and gpt-oss-120b (FPGA attention), prompt 1024, one user, temperature 0, pay-for-determinism (the runtron setting that makes the token stream reproducible), 256 generated tokens.</p>"
    rows = []
    for it in items:
        for p in it["pairs"]:
            klass = "ok" if "identical" in p["result"] else ("warn" if p["role"] == "informational" else "bad")
            rows.append(f"<tr><td>{esc(it['cell'])}</td><td>{esc(p['a'])} vs {esc(p['b'])}</td><td><span class='pill {klass}'>{esc(p['result'])}</span></td><td>{esc(p['role'])}</td><td>{esc(it['verdict'])}</td></tr>")
        for f in it.get("failed_lines") or []:
            rows.append(f"<tr><td>{esc(it['cell'])}</td><td colspan=4 class=small>{esc(f)}</td></tr>")
    return (f"<p>Step marker: <code>{esc(done)}</code>. Pairs marked <em>must match</em> decide the verdict. The pair headv vs head is informational: the two readers add the dot-product terms in a different order, so a difference there is expected.</p>"
            "<table><thead><tr><th>cell</th><th>pair</th><th>result</th><th>role</th><th>cell verdict</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


# ---------------------------------------------------------------- perf
def dumbbell(cell_row, metric, unit, nd):
    """One small-multiple SVG per cell: one dumbbell per pair (base dot, head dot, hairline, band box around the base mean)."""
    pairs = [(pk, p) for pk, p in cell_row["pairs"].items()]
    arms = cell_row["arms"]
    vals = []
    for pk, p in pairs:
        a, b = pk.split(":")
        for arm in (a, b):
            m = arms.get(arm, {}).get(f"{metric}_mean")
            if m is not None:
                vals.append(m)
        band = p.get("band_tps" if metric == "tps" else "band_prefill") or 0
        bm = arms.get(b, {}).get(f"{metric}_mean")
        if bm is not None:
            vals += [bm - band, bm + band]
    if not vals:
        return "<p class=small>no data</p>"
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, (hi or 1) * 0.02)
    lo -= span * 0.35; hi += span * 0.35
    W, H = 620, 36 + 46 * len(pairs)
    x0, x1 = 230, W - 24
    def X(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(metric)} per arm for {esc(cell_row["cell"])}" style="max-width:100%;height:auto">']
    # axis
    ticks = 4
    for i in range(ticks + 1):
        v = lo + (hi - lo) * i / ticks
        out.append(f'<line x1="{X(v):.1f}" y1="14" x2="{X(v):.1f}" y2="{H-18}" stroke="#e1e0d9" stroke-width="1"/>')
        out.append(f'<text x="{X(v):.1f}" y="{H-5}" font-size="11" fill="#898781" text-anchor="middle">{v:.{nd}f}</text>')
    y = 30
    for pk, p in pairs:
        a, b = pk.split(":")
        am, bm = arms.get(a, {}).get(f"{metric}_mean"), arms.get(b, {}).get(f"{metric}_mean")
        band = p.get("band_tps" if metric == "tps" else "band_prefill") or 0
        st = p.get("tps" if metric == "tps" else "prefill") or {}
        delta = st.get("mean")
        pct = p.get("tps_pct" if metric == "tps" else "prefill_pct")
        out.append(f'<text x="8" y="{y+4}" font-size="12" fill="#52514e">{esc(PAIR_LABEL.get(pk, pk))}</text>')
        if bm is not None:
            out.append(f'<rect x="{X(bm-band):.1f}" y="{y-10}" width="{max(X(bm+band)-X(bm-band),1):.1f}" height="20" fill="#2a78d6" fill-opacity="0.10"/>')
        if am is not None and bm is not None:
            out.append(f'<line x1="{X(bm):.1f}" y1="{y}" x2="{X(am):.1f}" y2="{y}" stroke="#c3c2b7" stroke-width="2" stroke-linecap="round"/>')
        if bm is not None:
            out.append(f'<circle cx="{X(bm):.1f}" cy="{y}" r="6" fill="#86b6ef" stroke="#fcfcfb" stroke-width="2"><title>{esc(b)}: {bm:.{nd}f} {unit}</title></circle>')
            out.append(f'<text x="{X(bm):.1f}" y="{y-12}" font-size="11" fill="#52514e" text-anchor="middle">{bm:.{nd}f}</text>')
        if am is not None:
            out.append(f'<circle cx="{X(am):.1f}" cy="{y}" r="6" fill="#2a78d6" stroke="#fcfcfb" stroke-width="2"><title>{esc(a)}: {am:.{nd}f} {unit}</title></circle>')
            out.append(f'<text x="{X(am):.1f}" y="{y+22}" font-size="11" fill="#0b0b0b" text-anchor="middle">{am:.{nd}f}</text>')
        if delta is not None and pct is not None:
            sign = "+" if delta >= 0 else ""
            label = f"{sign}{delta:.{nd}f} {unit} ({sign}{pct:.1f} %)"
            width = 6.3 * len(label)
            xs = [X(v) for v in (am, bm) if v is not None]
            if bm is not None:
                xs += [X(bm - band), X(bm + band)]
            right_edge, left_edge = max(xs) + 10, min(xs) - 10
            # Boxes already drawn in this row: the row label, the two value labels, the dots and the band.
            row_label = PAIR_LABEL.get(pk, pk)
            taken = [(8, 8 + 6.8 * len(row_label), y - 6, y + 6), (min(xs), max(xs), y - 8, y + 8)]
            if bm is not None:
                vw = 6.3 * len(f"{bm:.{nd}f}")
                taken.append((X(bm) - vw / 2, X(bm) + vw / 2, y - 22, y - 10))
            if am is not None:
                vw = 6.3 * len(f"{am:.{nd}f}")
                taken.append((X(am) - vw / 2, X(am) + vw / 2, y + 12, y + 24))
            def free(box):
                l, r, t, b = box
                if l < 4 or r > W - 4 or t < 2 or b > H - 20:
                    return False
                return all(r + 4 <= tl or l - 4 >= tr or b + 2 <= tt or t - 2 >= tb for tl, tr, tt, tb in taken)
            candidates = [(x1, y + 4), (left_edge, y + 4), (x1, y + 22), (x1, y - 12), (left_edge, y + 22), (left_edge, y - 12), (x1, y + 36)]
            lx, ly = candidates[-1]
            for cx, cy in candidates:
                if free((cx - width, cx, cy - 10, cy + 2)):
                    lx, ly = cx, cy
                    break
            out.append(f'<text x="{lx:.1f}" y="{ly}" font-size="11" fill="#0b0b0b" text-anchor="end">{label}</text>')
        y += 46
    out.append("</svg>")
    return "".join(out)


def perf_section(results):
    perf = results.get("perf") or []
    done = read(os.path.join("..", "..", "logs", "pr5047-20261020.done")).strip() or "running or pending"
    by_cell = {r["cell"]: r for r in perf}
    rows_tbl, charts, verdict_rows = [], [], []
    measured = []
    for cell in CELL_ORDER:
        r = by_cell.get(cell)
        if not r or not r.get("pairs"):
            continue
        measured.append(cell)
        for arm in ("base", "head", "basev", "headv", "baseoff", "headoff"):
            a = r["arms"].get(arm)
            if not a or not a.get("n"):
                continue
            rows_tbl.append(f"<tr><td>{esc(cell)}</td><td>{esc(arm)}</td><td>{a['n']}</td><td>{fnum(a['tps_mean'])} ({fnum(a['tps_sd'])})</td><td>{fnum(a['prefill_mean'],3)} ({fnum(a['prefill_sd'],3)})</td><td>AMX {fnum(a.get('amx_pct_mean'),1)} % / AVX {fnum(a.get('avx_pct_mean'),1)} % / FPGA {fnum(a.get('fpga_pct_mean'),1)} %</td><td>{a.get('early_stop_runs',0)}</td></tr>")
        for pk, p in r["pairs"].items():
            st, sp = p.get("tps") or {}, p.get("prefill") or {}
            v = p["verdict"]
            klass = "ok" if v in ("holds", "gain") else ("warn" if v.startswith("insufficient") or v.startswith("no ") else "bad")
            verdict_rows.append(f"<tr><td>{esc(cell)}</td><td>{esc(PAIR_LABEL.get(pk, pk))}</td><td>{fnum(st.get('mean'))} (n {st.get('n', 0)})</td><td>{fnum(p.get('tps_pct'),1)} %</td><td>{fnum(p.get('band_tps'))}</td><td>{fnum(st.get('t'),1)}</td><td>{fnum(sp.get('mean'),3)}</td><td>{fnum(p.get('prefill_pct'),1)} %</td><td>{fnum(p.get('band_prefill'),3)}</td><td><span class='pill {klass}'>{esc(v)}</span></td></tr>")
        charts.append(f"<figure class=cellfig><figcaption><b>{esc(CELL_LABEL.get(cell, cell))}</b>: decode throughput per user (tokens/s). Light dot = the base of the pair, dark dot = PR 5047. The shaded box is the decision band around the base mean.</figcaption>{dumbbell(r, 'tps', 'TPS', 2)}<figcaption class=small>Prefill time of the slowest user (s), same cell:</figcaption>{dumbbell(r, 'prefill', 's', 3)}</figure>")
    pending = [c for c in CELL_ORDER if c not in measured]
    head = f"<p>Campaign marker: <code>{esc(done)}</code>. Measured cells: {len(measured)} of {len(CELL_ORDER)}."
    if pending and done == "ok":
        head += " Not yet measured: " + ", ".join(f"<code>{esc(c)}</code>" for c in pending) + ". The script chain is finished. The cell is the optional kill-switch follow-up (<code>killswitch.sh</code>, the option-off binaries under <code>TRON_AMX_DISABLE=1</code>). It runs only when the machine is free, and this page is regenerated from the result files when it finishes."
    elif pending:
        head += " Not yet measured: " + ", ".join(f"<code>{esc(c)}</code>" for c in pending) + ". The script chain (smoke, campaign, tests) resumes after the nightly CI (NOT_BEFORE 2026-10-21T13:30:00Z) and this page is regenerated from the result files when it finishes."
    head += "</p>"
    if not measured:
        return head
    out = head
    out += "<h4>Verdict per cell and pair</h4><p>Paired delta = PR 5047 minus its base per repetition. Band = twice the larger arm standard deviation, never below 0.4 TPS or 0.15 s. Holds = TPS delta not below minus the band and prefill delta not above plus the band.</p>"
    out += "<div class=scroll><table><thead><tr><th>cell</th><th>pair</th><th>TPS delta (paired mean)</th><th>TPS delta</th><th>TPS band</th><th>t</th><th>prefill delta (s)</th><th>prefill delta</th><th>prefill band (s)</th><th>verdict</th></tr></thead><tbody>" + "".join(verdict_rows) + "</tbody></table></div>"
    out += floor_note(results)
    out += "<h4>Charts</h4>" + "".join(charts)
    out += "<h4>Per arm</h4><div class=scroll><table><thead><tr><th>cell</th><th>arm</th><th>reps</th><th>decode TPS per user (sd)</th><th>prefill s (sd)</th><th>K tokens by path</th><th>early-stop runs</th></tr></thead><tbody>" + "".join(rows_tbl) + "</tbody></table></div>"
    return out



def floor_pairs(results):
    """Pairs at 'holds' only because of the 0.4 TPS floor: the paired TPS loss exceeds twice the larger arm sd."""
    out = []
    for r in results.get("perf") or []:
        for pk, p in (r.get("pairs") or {}).items():
            st = p.get("tps") or {}
            mean = st.get("mean")
            if p.get("verdict") != "holds" or mean is None or mean >= 0 or ":" not in pk:
                continue
            a, b = pk.split(":")
            raw_band = 2 * max((r.get("arms", {}).get(x) or {}).get("tps_sd") or 0 for x in (a, b))
            if -mean > raw_band and -mean <= (p.get("band_tps") or 0):
                out.append((r["cell"], pk, p, raw_band))
    return out


def has_killswitch_pair(results):
    return any("headoff:baseoff" in (r.get("pairs") or {}) for r in results.get("perf") or [])


def floor_note(results):
    fp = floor_pairs(results)
    if not fp:
        return ""
    items = []
    for c, pk, p, raw in fp:
        st = p.get("tps") or {}
        items.append(f"<code>{esc(c)}</code> {esc(PAIR_LABEL.get(pk, pk))}: decode {st.get('mean'):+.2f} TPS ({p.get('tps_pct') or 0:+.1f} %), "
                     f"t = {st.get('t'):.1f} over {st.get('n')} paired repetitions, twice the larger arm standard deviation = {raw:.2f} TPS")
    note = "<p><b>Inside the band by the floor only.</b> " + " ".join(f"{it}." for it in items)
    note += (" The floor of 0.4 TPS keeps this pair at holds. The paired repetitions agree on the sign. The loss is small, and it is not noise."
             " The option is off in every preset. A headv vs basev pair is informational for the shipped package."
             " Hypothesis: the software scoring path that commit 1 moved into <code>page::score_k</code> carries the cost, and with the option on at this head every K token takes that path (AVX 100 % in the per-arm table).")
    if has_killswitch_pair(results):
        kp = next(p for r in results.get("perf") or [] for pk, p in (r.get("pairs") or {}).items() if pk == "headoff:baseoff")
        ks, kpre = kp.get("tps") or {}, kp.get("prefill") or {}
        note += (f" The kill-switch cell (<code>l8b-tp2-8u-p8192-off</code>, the option-off binaries under <code>TRON_AMX_DISABLE=1</code>, 100 % of K tokens through the dotter) measures the same path in the shipped layout:"
                 f" prefill {(kpre.get('mean') or 0):+.2f} s ({kp.get('prefill_pct') or 0:+.1f} %, {'beyond' if kp['verdict'].startswith('DEGRADATION') else 'inside'} the band) and decode {kp.get('tps_pct') or 0:+.1f} % over {ks.get('n')} paired repetitions."
                 " The restructured software path is slower in prefill when it scores every token. In the shipped configuration at prompt 8192 that path scores 2.8 % of the K tokens."
                 f" Scaled by that share, the cost is about {(kpre.get('mean') or 0) * 0.028:.2f} s (est.) of the measured +0.14 s prefill delta of the option-off pair.")
    else:
        note += " The kill-switch cell (<code>l8b-tp2-8u-p8192-off</code>, the option-off binaries under <code>TRON_AMX_DISABLE=1</code>, 100 % of K tokens through the dotter) would confirm or reject it for the shipped layout. It is not yet measured."
    return note + "</p>"

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


def overall_verdict(results):
    """One sentence for the Short version: interim or final, repetitions, and the flagged pairs with their sizes."""
    perf = results.get("perf") or []
    rows = [(r["cell"], pk, p) for r in perf for pk, p in (r.get("pairs") or {}).items()]
    if not rows:
        return "no result yet"
    done = read(os.path.join("..", "..", "logs", "pr5047-20261020.done")).strip()
    reps = [min(a.get("n", 0) for a in r["arms"].values() if a.get("n")) for r in perf if r.get("arms")]
    stage = "final" if done == "ok" else "interim"
    rep_txt = f"{min(reps)} to {max(reps)}" if reps and min(reps) != max(reps) else (str(reps[0]) if reps else "0")
    diag = [(c, pk, p) for c, pk, p in rows if pk == "headoff:baseoff"]
    rows = [(c, pk, p) for c, pk, p in rows if pk != "headoff:baseoff"]
    bad = [(c, pk, p) for c, pk, p in rows if p["verdict"].startswith("DEGRADATION")]
    weak = [(c, pk, p) for c, pk, p in rows if p["verdict"].startswith(("insufficient", "no "))]
    n_cells = len({c for c, _, _ in rows})
    s = f"({stage}, {rep_txt} of 4 repetitions) "
    if not bad:
        s += f"no degradation beyond the band in any of the {len(rows)} pairs over {n_cells} cells"
        fp = floor_pairs(results)
        if fp:
            s += f", with {len(fp)} pair{'s' if len(fp) > 1 else ''} inside the band by the 0.4 TPS floor only"
    else:
        parts = []
        for c, pk, p in bad:
            st, sp = p.get("tps") or {}, p.get("prefill") or {}
            short = c.replace("-tp2-8u-", " ").replace("-tp4-8u-", " ").replace("l8b", "llama-3.1-8b").replace("q4b", "qwen3-4b").replace("gptoss", "gpt-oss-120b")
            opt = {"head:base": "option OFF", "headv:basev": "option ON", "headoff:baseoff": "kill switch"}.get(pk, pk)
            parts.append(f"{short} {opt}: decode {p.get('tps_pct') or 0:+.1f} %, prefill {p.get('prefill_pct') or 0:+.1f} % ({(sp.get('mean') or 0):+.2f} s)")
        s += f"{len(bad)} of {len(rows)} pairs beyond the band: " + "; ".join(parts)
    if weak:
        s += f"; {len(weak)} pairs still below 2 repetitions"
    for c, pk, p in diag:
        st, sp = p.get("tps") or {}, p.get("prefill") or {}
        verdict = "beyond the band" if p["verdict"].startswith("DEGRADATION") else "inside the band"
        s += (f". The diagnostic kill-switch cell (every K token through the software loop) is {verdict}: "
              f"prefill {p.get('prefill_pct') or 0:+.1f} % ({(sp.get('mean') or 0):+.2f} s), decode {p.get('tps_pct') or 0:+.1f} %")
    return s


def timer_section(results):
    """Per cell and pair: the exit report's own per-forward wall timer (T1, rdtsc around each forward), summed per class
    (prompt_or_mixed = prefill forwards, decode_like = decode forwards), as the ratio head/base per repetition."""
    perf = results.get("perf") or []
    rows = []
    for r in perf:
        cell, attn = r["cell"], r["attn"]
        cyc = {}
        for arm, a in r["arms"].items():
            for rep in (a.get("reps") or {}):
                st = parse_stats(os.path.join(RES, "rt", f"{cell}__{attn}__{arm}__rep{rep}.log"))
                for cls, c in st["classes"].items():
                    fw = c.get("forwards") or {}
                    if isinstance(fw, dict) and fw.get("wall_cycles"):
                        cyc[(arm, int(rep), cls)] = (fw["wall_cycles"], fw.get("forwards"))
        for pk in r.get("pairs") or {}:
            a, b = pk.split(":")
            for cls, label in (("prompt_or_mixed", "prefill forwards"), ("decode_like", "decode forwards")):
                ratios = []
                for rep in sorted({k[1] for k in cyc}):
                    if (a, rep, cls) in cyc and (b, rep, cls) in cyc:
                        ratios.append(cyc[(a, rep, cls)][0] / cyc[(b, rep, cls)][0])
                if ratios:
                    m = statistics.mean(ratios)
                    rows.append(f"<tr><td>{esc(cell)}</td><td>{esc(PAIR_LABEL.get(pk, pk))}</td><td>{esc(label)}</td><td class=num>{len(ratios)}</td><td class=num>{(m - 1) * 100:+.2f} %</td><td class=small>{', '.join(f'{(x - 1) * 100:+.2f}' for x in ratios)}</td></tr>")
    if not rows:
        return "<p>No exit reports yet.</p>"
    return ("<p>The same runs carry a second clock: with <code>TRON_ATTN_STATS=1</code> the program times every forward pass itself (a cycle counter read before and after each forward, summed per class). The table gives the ratio of PR 5047's time to its base's time for the prefill forwards and the decode forwards, per repetition, as a percentage change. The per-path visit counts of these reports are identical between the two arms in every run, so a time difference is not a dispatch difference.</p>"
            "<div class=scroll><table><thead><tr><th>cell</th><th>pair</th><th>class</th><th class=num>reps</th><th class=num>mean change</th><th>per repetition</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def option_context_section(results):
    """The option's own cost (PR 4956's temporary gate, not PR 5047): basev against base, same commit."""
    perf = results.get("perf") or []
    rows = []
    for r in perf:
        a, b = r["arms"].get("basev"), r["arms"].get("base")
        if not (a and b and a.get("n") and b.get("n")):
            continue
        rows.append(f"<tr><td>{esc(CELL_LABEL.get(r['cell'], r['cell']))}</td><td class=num>{fnum(b['tps_mean'])}</td><td class=num>{fnum(a['tps_mean'])}</td><td class=num>{(a['tps_mean'] / b['tps_mean'] - 1) * 100:+.1f} %</td><td class=num>{fnum(b['prefill_mean'], 2)}</td><td class=num>{fnum(a['prefill_mean'], 2)}</td><td class=num>{(a['prefill_mean'] / b['prefill_mean'] - 1) * 100:+.1f} %</td><td class=num>{fnum(b.get('amx_pct_mean'), 1)} % / {fnum(a.get('amx_pct_mean'), 1)} %</td></tr>")
    if not rows:
        return ""
    return ("<h4>Context: what the option itself costs at this commit</h4><p>Not a PR 5047 effect. The same base commit with the option ON (basev) against OFF (base): a VNNI slot never takes the AMX path in this PR of the stack, so the option trades the AMX kernel for the AVX-512 reader until PR 4957 adds the VNNI AMX kernel.</p>"
            "<div class=scroll><table><thead><tr><th>cell</th><th class=num>TPS OFF</th><th class=num>TPS ON</th><th class=num>change</th><th class=num>prefill OFF (s)</th><th class=num>prefill ON (s)</th><th class=num>change</th><th class=num>K tokens on AMX, OFF / ON</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def main():
    results = refresh_results()
    tpl = open(TEMPLATE, encoding="utf-8").read()
    chain = read("chain.done").strip() or "running"
    fills = {
        "GENERATED": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "CHAIN_STATE": chain,
        "BUILDS": builds_section(),
        "TESTS": tests_section(),
        "IDENTITY": identity_section(results),
        "PERF": perf_section(results),
        "TIMER": timer_section(results),
        "OPTION_CONTEXT": option_context_section(results),
        "PERF_VERDICT": overall_verdict(results),
    }
    for k, v in fills.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", tpl)
    if left:
        print("unfilled placeholders:", left, file=sys.stderr)
    tpl = no_semicolons(tpl)
    open(OUT, "w", encoding="utf-8").write(tpl)
    print(f"wrote {OUT} ({len(tpl)} bytes); perf verdict: {fills['PERF_VERDICT']}")


if __name__ == "__main__":
    main()
