#!/usr/bin/env python3
"""Friday-morning-CI-run-report.html generator for the ci-mimic campaign (2026-09-18).

Inputs (all JSON unless noted):
  --base     exec/results/ci-mimic-20260918/base-pass1/perf.json     (st_ci_perf.py record)
  --target   exec/results/ci-mimic-20260918/target-pass1/perf.json   (st_ci_perf.py record)
  --nightly  reference/nightly-0918.arm.json                          (nightly_to_arm.py record of the same-day nightly)
  --stats    reference/nightly_stats.json                             (13-night Slack series per config)
  --preflight exec/results/ci-mimic-20260918/preflight.txt            (text; carries the target manifest)
  --out      status/Friday-morning-CI-run-report.html
Every number in the page is computed here from those files; nothing is typed in by hand.
Pre-registered rules: a base-vs-nightly difference counts only if |z| > 3 against the 13-night band AND
|delta| >= 1 %; target-vs-base effects are judged by a paired-by-round t over the 10 round means (|t| >= 2.26
= p < 0.05 at 9 degrees of freedom) AND |delta| >= 1 %.
"""
import argparse
import json
import math
import re
import statistics
import time

# ---- the 12 nightly configs in perf.py order, with short names for charts ----
ORDER = [
    ("llama-3.2-3b-instruct-fast-tp2", 32, "llama-3.2-3b fast tp2 @32u", "CPU attention; VNNI-K layout in target (kv_mul 3, no AMX kernel)"),
    ("llama-3.1-8b-instruct-good-tp2", 8, "llama-3.1-8b good tp2 @8u", "CPU attention; AMX kernel + VNNI-K in target"),
    ("llama-3.3-70b-instruct-good-tp2", 8, "llama-3.3-70b good tp2 @8u", "CPU attention; VNNI-K layout in target (kv_mul 8)"),
    ("llama-3.3-70b-instruct-good-tp2", 4, "llama-3.3-70b good tp2 @4u", "same engines as the @8u cell (no re-provisioning)"),
    ("llama-3.3-70b-instruct-good-tp4", 4, "llama-3.3-70b good tp4 @4u", "CPU attention; VNNI-K layout in target"),
    ("mixtral-8x7b-instruct-v0.1-tp2", 8, "mixtral-8x7b tp2 @8u", "CPU attention; AMX kernel + VNNI-K in target"),
    ("qwen-2.5-32b-it-fast-tp2", 8, "qwen-2.5-32b fast tp2 @8u", "CPU attention; VNNI-K layout in target (kv_mul 5)"),
    ("ingested-qwen-3-4b-instruct-2507-tp2", 8, "qwen-3-4b tp2 @8u", "FPGA attention (nightly default); AMX only in the CPU share"),
    ("ingested-qwen-3-4b-instruct-2507-tp4", 8, "qwen-3-4b tp4 @8u", "FPGA attention; night-to-night noisy (sd 5 TPS)"),
    ("gemma-2-9b-it-fast-tp2", 8, "gemma-2-9b fast tp2 @8u", "head 256: neither AMX nor VNNI-K applies"),
    ("ingested-gpt-oss-120b-tp4", 8, "gpt-oss-120b tp4 @8u", "FPGA attention; head 64: no AMX kernel; noisy (sd 3 TPS)"),
    ("ingested-gemma-4-31b-it-tp2", 8, "gemma-4-31b tp2 @8u", "head 256: neither applies; 3 nights of reference only"),
]
# CURRENT static goals for granite_rapids_72_rinzler (systems_test scripts/system_ci.py get_goal): mean TPS / slowest user TPS
GOALS = {
    ("llama-3.2-3b-instruct-fast-tp2", 32): (191.0, 150.0), ("llama-3.1-8b-instruct-good-tp2", 8): (144.0, 140.0),
    ("llama-3.3-70b-instruct-good-tp2", 4): (27.0, 27.0), ("llama-3.3-70b-instruct-good-tp2", 8): (27.0, 18.0),
    ("llama-3.3-70b-instruct-good-tp4", 4): (27.0, 27.0), ("mixtral-8x7b-instruct-v0.1-tp2", 8): (71.0, 71.0),
    ("qwen-2.5-32b-it-fast-tp2", 8): (35.0, 35.0), ("ingested-qwen-3-4b-instruct-2507-tp2", 8): (175.0, 145.0),
    ("ingested-qwen-3-4b-instruct-2507-tp4", 8): (135.0, 115.0), ("gemma-2-9b-it-fast-tp2", 8): (90.0, 90.0),
    ("ingested-gpt-oss-120b-tp4", 8): (52.0, 40.0), ("ingested-gemma-4-31b-it-tp2", 8): (None, None),
}
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201,
        12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042}
PCT_FLOOR = 1.0
Z_FLAG = 3.0
T_FLAG = 2.262

# palette (dataviz reference instance, light surface): entity colors, never re-assigned
C_BASE, C_TARGET, C_NIGHTLY, C_BAND = "#2a78d6", "#eb6834", "#898781", "#e1e0d9"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"


def t975(df):
    if df <= 0:
        return float("nan")
    if df in T975:
        return T975[df]
    keys = sorted(T975)
    for k in keys:
        if df < k:
            return T975[k]
    return 1.96


def load(path):
    return json.load(open(path)) if path else None


def key_of(res):
    c = res["context"]
    return (c["model"], int(c["nominal_users"]))


def rounds_of(raw, n_users):
    """Per-round TPS and TTFT lists. Driver records are flat in round order (each round completes before the
    next starts); nightly records carry explicit rounds."""
    if raw is None:
        return [], []
    if raw.get("rounds"):
        return [r["tps"] for r in raw["rounds"]], [r["ttft_ms"] for r in raw["rounds"]]
    tps, ttft = raw.get("tpss") or [], raw.get("ttfts_ms") or []
    if n_users and len(tps) % n_users == 0 and len(tps) > 0:
        return ([tps[i:i + n_users] for i in range(0, len(tps), n_users)],
                [ttft[i:i + n_users] for i in range(0, len(ttft), n_users)] if len(ttft) == len(tps) else [])
    return [tps] if tps else [], [ttft] if ttft else []


def arm_table(rec):
    """key -> dict(tps_mean, tps_sd, p05, min, ttft_mean, n, round_tps[], round_ttft[], minutes, engines, prov_s)"""
    out = {}
    if not rec:
        return out
    raws = {}
    for r in rec.get("raw") or []:
        raws.setdefault((r["model"], int(r["n_users"])), r)
    for res in rec.get("results") or []:
        k = key_of(res)
        tps = res.get("tps_results") or []
        rt, rf = rounds_of(raws.get(k), k[1])
        if not tps and rt:
            tps = [x for r in rt for x in r]
        ttft_all = [x for r in rf for x in r] if rf else []
        s = sorted(tps)
        p05 = None
        if s:
            pos = (len(s) - 1) * 0.05
            lo = int(pos); hi = min(lo + 1, len(s) - 1); p05 = s[lo] + (s[hi] - s[lo]) * (pos - lo)
        out[k] = {
            "tps_mean": statistics.mean(tps) if tps else None, "tps_sd": statistics.pstdev(tps) if len(tps) > 1 else 0.0,
            "p05": p05, "min": min(tps) if tps else None, "n": len(tps),
            "ttft_mean": (statistics.mean(ttft_all) if ttft_all else res.get("ttft_mean")),
            "ttft_sd": statistics.pstdev(ttft_all) if len(ttft_all) > 1 else None,
            "round_tps": [statistics.mean(r) for r in rt if r], "round_ttft": [statistics.mean(r) for r in rf if r],
            "minutes": res.get("minutes"), "engines": res.get("engines"), "prov_s": res.get("provision_seconds"),
            "failed": not tps,
        }
    return out


def paired(a, b):
    """paired difference b - a over rounds: mean, sd, t, n, ci95 (absolute units)."""
    n = min(len(a), len(b))
    if n < 2:
        return None
    d = [b[i] - a[i] for i in range(n)]
    m = statistics.mean(d); sd = statistics.stdev(d) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t = (m / se) if se and se > 0 else (float("inf") if m != 0 else 0.0)
    ci = t975(n - 1) * se if se == se else float("nan")
    return {"mean": m, "sd": sd, "t": t, "n": n, "ci": ci}


def pct(x, ref):
    return (x - ref) / ref * 100.0 if (x is not None and ref) else None


def fmt(x, nd=2, unit=""):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:,.{nd}f}{unit}"


def signed(x, nd=1, unit="%"):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:+.{nd}f}{unit}"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def band13(stats, k):
    """13-night Slack series for a config key -> dict(mean, sd, n, ttft_mean, ttft_sd, slowest_mean, slowest_sd, series)"""
    if not stats:
        return None
    name = f"{k[0]} @{k[1]}u"
    s = stats.get(name)
    if not s or not s.get("series"):
        return None
    tps = [r["tps"] for r in s["series"] if r.get("tps") is not None]
    ttft = [r["ttft_ms"] for r in s["series"] if r.get("ttft_ms") is not None]
    slow = [r["slowest"] for r in s["series"] if r.get("slowest") is not None]
    return {"n": len(tps), "mean": statistics.mean(tps), "sd": statistics.stdev(tps) if len(tps) > 1 else 0.0,
            "min": min(tps), "max": max(tps),
            "ttft_mean": statistics.mean(ttft) if ttft else None, "ttft_sd": statistics.stdev(ttft) if len(ttft) > 1 else None,
            "slow_mean": statistics.mean(slow) if slow else None, "slow_sd": statistics.stdev(slow) if len(slow) > 1 else None,
            "series": s["series"]}


def snapshot_facts(rec):
    """Pull the evidence lines out of the driver's snapshots."""
    if not rec:
        return {}
    f = {"engine_counts": [], "deleted": 0, "unit_count": None, "env_vars": None, "sst": None, "rinzler_sha": None, "tron": None}
    for s in rec.get("snapshots") or []:
        t = s.get("text") or ""
        if any(re.match(r"^\d+ /\S+ \(deleted\)", l) for l in t.splitlines()):  # pid lines only; the header names the word
            f["deleted"] += 1
        m = re.search(r"=== engines\n(\[.*\])\s*\n", t)
        if m and s["tag"].startswith("after-provision"):
            try:
                eng = json.loads(m.group(1))
                f["engine_counts"].append((s["tag"].split(":", 1)[1], sum(1 for e in eng if e[1] == "running"), len(eng)))
            except Exception:
                pass
        m = re.search(r"=== unit\n(\d+)", t)
        if m:
            f["unit_count"] = int(m.group(1))
        m = re.search(r"=== rinzler\n([0-9a-f]{64})", t)
        if m:
            f["rinzler_sha"] = m.group(1)
        m = re.search(r"\nii\s+tron\s+(\S+)", t)
        if m:
            f["tron"] = m.group(1)
        m = re.search(r"Intel Speed Select[^\n]*", t)
        if m:
            f["sst"] = m.group(0)
        m = re.search(r"AMX/HW_ATTN vars \(must be 0\)\n([^\n]*)", t)
        if m:
            f["env_vars"] = m.group(1).strip()
    return f


# ---------------- charts (inline SVG, light surface) ----------------
def chart_pct(rows, title, subtitle, xlabel, color, band_key=None, ci_key="ci_pct", val_key="pct", note=None, clip=None):
    """Horizontal dot chart of percent differences, one row per config. rows: list of dicts with
    label, pct, ci_pct (half-width, may be None), band_pct (half-width of the reference band, may be None), flag(bool).
    clip = largest |percent| the axis shows; a value or whisker beyond it is drawn at the edge and its label says so."""
    sub_lines = wrap(subtitle)
    W, left, right, rowh = 960, 250, 150, 30
    top = 52 + 16 * len(sub_lines)
    n = len(rows)
    H = top + n * rowh + 60 + (16 if note else 0)
    vals = []
    for r in rows:
        if r.get(val_key) is not None:
            vals += [r[val_key] - (r.get(ci_key) or 0), r[val_key] + (r.get(ci_key) or 0)]
        if band_key and r.get(band_key) is not None:
            c = r.get("band_center") or 0.0
            vals += [c - r[band_key], c + r[band_key]]
    lim = max(5.0, max(abs(v) for v in vals) * 1.15) if vals else 5.0
    if clip is not None:
        lim = min(lim, clip)
    lim = math.ceil(lim)
    if clip is not None and any(abs(v) > lim for v in vals):
        right = 230  # room for the "(CI +/-N %, off scale)" label of a clipped row
        pw = W - left - right
    pw = W - left - right
    x0 = left + pw / 2

    def X(v):
        return x0 + (v / lim) * (pw / 2)

    step = 1 if lim <= 6 else (2 if lim <= 14 else (5 if lim <= 40 else 10))
    ticks = [v for v in range(-lim, lim + 1) if v % step == 0]
    out = svg_header(W, H, title, sub_lines)
    for v in ticks:
        out.append(f'<line x1="{X(v):.1f}" y1="{top - 6}" x2="{X(v):.1f}" y2="{top + n * rowh}" stroke="{GRID if v else MUTED}" stroke-width="1"/>')
        out.append(f'<text x="{X(v):.1f}" y="{top + n * rowh + 18}" font-size="11" fill="{MUTED}" text-anchor="middle">{v:+d}%</text>')
    out.append(f'<text x="{x0:.1f}" y="{top + n * rowh + 40}" font-size="12" fill="{INK2}" text-anchor="middle">{esc(xlabel)}</text>')
    for i, r in enumerate(rows):
        cy = top + i * rowh + rowh / 2
        out.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="12" fill="{INK2}" text-anchor="end">{esc(r["label"])}</text>')
        if band_key and r.get(band_key) is not None:
            c = r.get("band_center") or 0.0
            lo_b, hi_b = max(-lim, c - r[band_key]), min(lim, c + r[band_key])
            out.append(f'<rect x="{X(lo_b):.1f}" y="{cy - 9:.1f}" width="{max(2.0, X(hi_b) - X(lo_b)):.1f}" height="18" fill="{C_BAND}" rx="2"><title>{esc(r.get("band_title", ""))}</title></rect>')
        v = r.get(val_key)
        if v is None:
            out.append(f'<text x="{x0 + 8:.1f}" y="{cy + 4:.1f}" font-size="11" fill="{MUTED}">no data</text>')
            continue
        v_c = max(-lim, min(lim, v))
        ci = r.get(ci_key)
        clipped = abs(v) > lim or (ci is not None and ci == ci and (v + ci > lim or v - ci < -lim))
        if ci is not None and ci == ci:
            out.append(f'<line x1="{X(max(-lim, v - ci)):.1f}" y1="{cy:.1f}" x2="{X(min(lim, v + ci)):.1f}" y2="{cy:.1f}" stroke="{color}" stroke-width="2" stroke-linecap="round"/>')
        out.append(f'<circle cx="{X(v_c):.1f}" cy="{cy:.1f}" r="7" fill="{SURF}"/>')
        out.append(f'<circle cx="{X(v_c):.1f}" cy="{cy:.1f}" r="5" fill="{color}"><title>{esc(r.get("tip", ""))}</title></circle>')
        lx = X(min(lim, v_c + (ci or 0))) + 10
        weight = "600" if r.get("flag") else "400"
        extra = (f" (CI &#177;{ci:.0f} %, off scale)" if (clipped and ci is not None and ci == ci) else (" (off scale)" if clipped else ""))
        out.append(f'<text x="{lx:.1f}" y="{cy + 4:.1f}" font-size="12" font-weight="{weight}" fill="{INK}">{signed(v)}{" *" if r.get("flag") else ""}{extra}</text>')
    if note:
        for j, l in enumerate(wrap(note, 130)):
            out.append(f'<text x="16" y="{H - 8 - 14 * (len(wrap(note, 130)) - 1 - j)}" font-size="11" fill="{MUTED}">{esc(l)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_abs(rows, title, subtitle):
    """Small multiples: one row per config with its own axis; dots for nightly, base, target; 13-night min-max as a band."""
    sub_lines = wrap(subtitle)
    note = "Each row has its own scale (units differ 12x between configs). Gray band = 13-night min to max of the nightly. Gray dot = the 2026-09-18 nightly, blue = base, orange = target."
    note_lines = wrap(note, 130)
    W, left, right, rowh = 960, 250, 40, 36
    top = 52 + 16 * len(sub_lines)
    n = len(rows)
    H = top + n * rowh + 24 + 14 * len(note_lines)
    pw = W - left - right
    out = svg_header(W, H, title, sub_lines)
    for i, r in enumerate(rows):
        cy = top + i * rowh + rowh / 2
        pts = [(k, v) for k, v in (("nightly", r.get("nightly")), ("base", r.get("base")), ("target", r.get("target"))) if v is not None]
        vals = [v for _, v in pts] + ([r["band"][0], r["band"][1]] if r.get("band") else [])
        out.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="12" fill="{INK2}" text-anchor="end">{esc(r["label"])}</text>')
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or (abs(hi) * 0.05 or 1.0)
        lo -= span * 0.35; hi += span * 0.35

        def X(v):
            return left + (v - lo) / (hi - lo) * pw
        out.append(f'<line x1="{left}" y1="{cy:.1f}" x2="{left + pw}" y2="{cy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        if r.get("band"):
            out.append(f'<rect x="{X(r["band"][0]):.1f}" y="{cy - 8:.1f}" width="{max(2.0, X(r["band"][1]) - X(r["band"][0])):.1f}" height="16" fill="{C_BAND}" rx="2"><title>13-night range {fmt(r["band"][0])} to {fmt(r["band"][1])}</title></rect>')
        # connector between base and target (the dumbbell)
        if r.get("base") is not None and r.get("target") is not None:
            out.append(f'<line x1="{X(r["base"]):.1f}" y1="{cy:.1f}" x2="{X(r["target"]):.1f}" y2="{cy:.1f}" stroke="{INK2}" stroke-width="2" stroke-linecap="round"/>')
        colors = {"nightly": C_NIGHTLY, "base": C_BASE, "target": C_TARGET}
        # labels: place each value label above (nightly), below-left (base) or below-right (target) to avoid collisions
        for k, v in pts:
            out.append(f'<circle cx="{X(v):.1f}" cy="{cy:.1f}" r="7" fill="{SURF}"/>')
            out.append(f'<circle cx="{X(v):.1f}" cy="{cy:.1f}" r="5" fill="{colors[k]}"><title>{k}: {fmt(v)} {esc(r.get("unit", ""))}</title></circle>')
        lab = place_labels([(X(v), k) for k, v in pts])
        for k, v in pts:
            dy, anchor, dx = lab[k]
            out.append(f'<text x="{X(v) + dx:.1f}" y="{cy + dy:.1f}" font-size="10.5" fill="{INK2}" text-anchor="{anchor}">{fmt(v, 1 if v >= 100 else 2)}</text>')
    for j, l in enumerate(note_lines):
        out.append(f'<text x="16" y="{H - 8 - 14 * (len(note_lines) - 1 - j)}" font-size="11" fill="{MUTED}">{esc(l)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def wrap(text, width=108):
    """Split a subtitle into lines of at most `width` characters at word boundaries."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def svg_header(W, H, title, subtitle_lines):
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif;background:{SURF}" role="img" aria-label="{esc(title)}">',
           f'<text x="16" y="24" font-size="16" font-weight="600" fill="{INK}">{esc(title)}</text>']
    for i, l in enumerate(subtitle_lines):
        out.append(f'<text x="16" y="{44 + 16 * i}" font-size="12" fill="{INK2}">{esc(l)}</text>')
    return out


def place_labels(points, min_dx=64):
    """points: list of (x, key). Returns {key: (dy, anchor, dx)} choosing below/above so that labels in the same
    lane are at least min_dx apart; a third neighbour is pushed sideways."""
    lanes = {15: [], -10: []}
    out = {}
    for x, k in sorted(points):
        placed = False
        for dy in (15, -10):
            if all(abs(x - px) >= min_dx for px in lanes[dy]):
                lanes[dy].append(x); out[k] = (dy, "middle", 0); placed = True; break
        if not placed:
            # sideways: to the right of the rightmost neighbour in the lower lane
            out[k] = (15, "start", 14); lanes[15].append(x + 40)
    return out


def legend(items):
    return '<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{esc(t)}</span>' for c, t in items) + "</div>"


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--target"); ap.add_argument("--nightly"); ap.add_argument("--stats")
    ap.add_argument("--preflight"); ap.add_argument("--out", required=True); ap.add_argument("--nightly-run-id", default="")
    ap.add_argument("--caveats", help="HTML fragment (a <ul>) inserted as the caveats section")
    ap.add_argument("--short3", help="third sentence of the Short version (replaces the default n=1 sentence)")
    ap.add_argument("--notes3", help="HTML fragment inserted after the effect table (interpretation of the flagged rows)")
    ap.add_argument("--thr-note", help="HTML paragraph inserted under the threshold table")
    ap.add_argument("--title", default="Friday morning CI run: the nightly perf phase by hand, base vs AMX + VNNI-K target")
    a = ap.parse_args()
    base_rec, tgt_rec, ngt_rec, stats = load(a.base), load(a.target), load(a.nightly), load(a.stats)
    pre = open(a.preflight).read() if a.preflight else ""
    manifest = None
    m = re.search(r"\{[^{}]*\"deb_sha256\".*?\n\}", pre, re.S)
    if m:
        try:
            manifest = json.loads(m.group(0))
        except Exception:
            manifest = None
    B, T, N = arm_table(base_rec), arm_table(tgt_rec), arm_table(ngt_rec)
    fb, ft = snapshot_facts(base_rec), snapshot_facts(tgt_rec)

    rows = []
    for model, users, short, note in ORDER:
        k = (model, users)
        b, t, ng, bd = B.get(k), T.get(k), N.get(k), band13(stats, k)
        r = {"key": k, "short": short, "note": note, "b": b, "t": t, "n": ng, "band": bd}
        # fidelity: base vs same-day nightly and vs the 13-night band
        if b and ng and b["tps_mean"] and ng["tps_mean"]:
            r["fid_pct"] = pct(b["tps_mean"], ng["tps_mean"])
            r["fid_ttft_pct"] = pct(b["ttft_mean"], ng["ttft_mean"]) if b["ttft_mean"] and ng["ttft_mean"] else None
            r["fid_paired"] = paired(ng["round_tps"], b["round_tps"])
        if b and bd and b["tps_mean"]:
            r["z"] = (b["tps_mean"] - bd["mean"]) / bd["sd"] if bd["sd"] > 0 else float("inf")
            r["vs13_pct"] = pct(b["tps_mean"], bd["mean"])
            r["band_pct"] = 2 * bd["sd"] / bd["mean"] * 100
            r["z_ttft"] = ((b["ttft_mean"] - bd["ttft_mean"]) / bd["ttft_sd"]) if (bd.get("ttft_sd") and b["ttft_mean"]) else None
            # flag only if base is off BOTH references: the 13-night band (z) and the same-day nightly (>= 1 %).
            # (llama-70b tp2 @4u sits at z +5 on 09-18 for base AND for the nightly itself: a day effect, not a fidelity miss)
            same_day_off = r.get("fid_pct") is None or abs(r["fid_pct"]) >= PCT_FLOOR
            r["fid_flag"] = (abs(r["z"]) > Z_FLAG) and (abs(r["vs13_pct"]) >= PCT_FLOOR) and same_day_off
        # effect: target vs base
        if b and t and b["tps_mean"] and t["tps_mean"]:
            r["eff_pct"] = pct(t["tps_mean"], b["tps_mean"])
            pr = paired(b["round_tps"], t["round_tps"])
            r["eff_paired"] = pr
            r["eff_ci_pct"] = (pr["ci"] / b["tps_mean"] * 100) if pr and pr["ci"] == pr["ci"] else None
            # resolved = paired t significant AND at least 1 % AND larger than two normal nights differ
            # (2 sd of the 13-night band, in percent). Calibration: nightlies 09-16 vs 09-17 differ by +4.7 %
            # on qwen-3-4b tp4 with a paired t above 2.26, so the t alone over-calls noisy configs.
            night_band = (2 * bd["sd"] / bd["mean"] * 100) if bd and bd["mean"] else 0.0
            r["eff_band_pct"] = night_band
            r["eff_flag"] = bool(pr and abs(pr["t"]) >= T_FLAG and abs(r["eff_pct"]) >= max(PCT_FLOOR, night_band))
            if b["ttft_mean"] and t["ttft_mean"]:
                r["eff_ttft_pct"] = pct(t["ttft_mean"], b["ttft_mean"])
                prf = paired(b["round_ttft"], t["round_ttft"]) if b["round_ttft"] and t["round_ttft"] else None
                r["eff_ttft_paired"] = prf
                r["eff_ttft_ci_pct"] = (prf["ci"] / b["ttft_mean"] * 100) if prf and prf["ci"] == prf["ci"] else None
                ttft_band = (2 * bd["ttft_sd"] / bd["ttft_mean"] * 100) if bd and bd.get("ttft_sd") and bd.get("ttft_mean") else 0.0
                # the Slack TTFT reference is an integer (ms), so a 1 ms band floor stands in for rounding
                ttft_floor = max(PCT_FLOOR, ttft_band, (1.0 / b["ttft_mean"] * 100) if b["ttft_mean"] else 0.0)
                r["eff_ttft_band_pct"] = ttft_band
                r["eff_ttft_flag"] = bool(prf and abs(prf["t"]) >= T_FLAG and abs(r["eff_ttft_pct"]) >= ttft_floor)
        rows.append(r)

    # ---- short version numbers
    fid_rows = [r for r in rows if r.get("fid_pct") is not None]
    fid_ok = [r for r in fid_rows if not r.get("fid_flag")]
    fid_abs = [abs(r["fid_pct"]) for r in fid_rows]
    eff_rows = [r for r in rows if r.get("eff_pct") is not None]
    eff_sig = sorted([r for r in eff_rows if r.get("eff_flag")], key=lambda r: -abs(r["eff_pct"]))
    base_ver = fb.get("tron") or ((base_rec or {}).get("versions") or {}).get("Tron (package)") or (base_rec or {}).get("tron_version") or "?"
    tgt_ver = ft.get("tron") or ((tgt_rec or {}).get("versions") or {}).get("Tron (package)") or (tgt_rec or {}).get("tron_version") or "?"
    ngt_ver = (ngt_rec or {}).get("tron_version", "?")
    sv = []
    n_fail = len(fid_rows) - len(fid_ok)
    if fid_rows:
        sv.append(f"The base run, on the nightly's own package ({esc(base_ver)}) and through the nightly's client path, gave TPS (decode tokens per second per user) within {max(fid_abs):.1f} % of the same-day nightly on all {len(fid_rows)} configs, and "
                  + ("no config fails the fidelity rule of section 2." if n_fail == 0 else f"{n_fail} of {len(fid_rows)} configs fail the fidelity rule of section 2."))
    else:
        sv.append("The base run has no same-day nightly to compare with yet.")
    if eff_rows:
        l8b = next((r for r in rows if r["key"][0] == "llama-3.1-8b-instruct-good-tp2" and r.get("eff_pct") is not None), None)
        l8b_probe = next((p.get("amx_busy_cycles") for p in (tgt_rec or {}).get("amx_probes") or [] if p.get("model", "").startswith("llama-3.1-8b")), None)
        l8b_txt = (f", while llama-3.1-8b, where the AMX kernel ran ({l8b_probe / 1e9:.1f} billion AMX-busy cycles against 0 on base), changes only {signed(l8b['eff_pct'])}"
                   if l8b and l8b_probe else "")
        if eff_sig:
            parts = []
            for r in eff_sig:
                p = f"{r['short']} {signed(r['eff_pct'])}"
                if r["key"][0].startswith("llama-3.2-3b"):
                    p += " (not trusted, see the caveats)"
                parts.append(p)
            sv.append(f"The target package (PR #4424, which stores the K cache in the layout the AMX instructions read, built with AMX turned on) changes TPS by a resolved amount (larger than the night-to-night noise, section 3) on {len(eff_sig)} of {len(eff_rows)} configs: {', '.join(parts)}{l8b_txt}.")
        else:
            sv.append(f"The target package (PR #4424 plus AMX on in the deb build preset) shows no resolved TPS change on any of the {len(eff_rows)} configs{l8b_txt}.")
    else:
        sv.append("The target arm has not produced results yet.")
    sv.append(esc(a.short3) if a.short3 else "Every number here is one run per arm (10 rounds per config, as in the nightly), so differences smaller than the 13-night band are not resolved.")
    caveats_html = open(a.caveats).read() if a.caveats else ""

    # ---- tables
    def tr(cells, cls=""):
        return f'<tr class="{cls}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    fid_table = ['<table><thead><tr><th>config</th><th>nightly 09-18 TPS</th><th>base TPS</th><th>base vs nightly</th><th>paired t (10 rounds)</th><th>13-night mean &#177; sd</th><th>z</th><th>nightly TTFT ms</th><th>base TTFT ms</th><th>TTFT delta</th></tr></thead><tbody>']
    for r in rows:
        b, ng, bd = r["b"], r["n"], r["band"]
        pr = r.get("fid_paired")
        fid_table.append(tr([
            esc(r["short"]), fmt(ng["tps_mean"]) if ng else "n/a", fmt(b["tps_mean"]) if b and b["tps_mean"] else ("failed" if b else "n/a"),
            signed(r.get("fid_pct")), (f"{pr['t']:+.1f}" if pr else "n/a"),
            (f"{fmt(bd['mean'])} &#177; {fmt(bd['sd'])} (n={bd['n']})" if bd else "n/a"),
            (f"{r['z']:+.1f}" + (" *" if r.get("fid_flag") else "")) if r.get("z") is not None and r["z"] == r["z"] and not math.isinf(r["z"]) else ("inf" if r.get("z") is not None else "n/a"),
            fmt(ng["ttft_mean"], 0) if ng and ng["ttft_mean"] else "n/a", fmt(b["ttft_mean"], 0) if b and b["ttft_mean"] else "n/a",
            signed(r.get("fid_ttft_pct"))], "flag" if r.get("fid_flag") else ""))
    fid_table.append("</tbody></table>")

    eff_table = ['<table><thead><tr><th>config</th><th>base TPS</th><th>target TPS</th><th>target vs base</th><th>95 % interval (paired rounds)</th><th>paired t</th><th>13-night TPS band (2 sd)</th><th>base TTFT ms</th><th>target TTFT ms</th><th>TTFT delta</th><th>TTFT paired t</th></tr></thead><tbody>']
    for r in rows:
        b, t = r["b"], r["t"]
        pr, prf = r.get("eff_paired"), r.get("eff_ttft_paired")
        eff_table.append(tr([
            esc(r["short"]), fmt(b["tps_mean"]) if b and b["tps_mean"] else "n/a", fmt(t["tps_mean"]) if t and t["tps_mean"] else ("failed" if t else "n/a"),
            signed(r.get("eff_pct")) + (" *" if r.get("eff_flag") else ""),
            (f"&#177;{r['eff_ci_pct']:.1f} %" if r.get("eff_ci_pct") is not None else "n/a"), (f"{pr['t']:+.1f}" if pr else "n/a"),
            (f"&#177;{r['eff_band_pct']:.1f} %" if r.get("eff_band_pct") is not None else "n/a"),
            fmt(b["ttft_mean"], 0) if b and b["ttft_mean"] else "n/a", fmt(t["ttft_mean"], 0) if t and t["ttft_mean"] else "n/a",
            signed(r.get("eff_ttft_pct")) + (" *" if r.get("eff_ttft_flag") else ""), (f"{prf['t']:+.1f}" if prf else "n/a")],
            "flag" if r.get("eff_flag") else ""))
    eff_table.append("</tbody></table>")

    def verdict(arm, k):
        g = GOALS.get(k, (None, None))
        if not arm or arm.get("tps_mean") is None:
            return "n/a"
        if g[0] is None:
            return "no threshold"
        ok = arm["tps_mean"] >= g[0] and arm["min"] >= g[1]
        why = []
        if arm["tps_mean"] < g[0]:
            why.append(f"mean {fmt(arm['tps_mean'])} &lt; {g[0]:.0f}")
        if arm["min"] < g[1]:
            why.append(f"slowest {fmt(arm['min'])} &lt; {g[1]:.0f}")
        return ("PASS" if ok else "FAIL: " + "; ".join(why))

    thr_table = ['<table><thead><tr><th>config</th><th>goal mean / slowest TPS</th><th>nightly 09-18</th><th>base</th><th>target</th></tr></thead><tbody>']
    for r in rows:
        g = GOALS.get(r["key"], (None, None))
        thr_table.append(tr([esc(r["short"]), (f"{g[0]:.0f} / {g[1]:.0f}" if g[0] else "placeholder (1.00)"),
                             verdict(r["n"], r["key"]), verdict(r["b"], r["key"]), verdict(r["t"], r["key"])]))
    thr_table.append("</tbody></table>")

    # ---- charts
    c1_rows = [{"label": r["short"], "pct": r.get("fid_pct"), "ci_pct": None,
                # the band is centred where the 13-night mean sits relative to the same-day nightly, so dot-inside-band = within 2 sd of the 13 nights;
                # its half-width is 2 sd in percent of the NIGHTLY (the axis unit), so the band edges in TPS are exactly mean13 +/- 2 sd
                "band_center": (pct(r["band"]["mean"], r["n"]["tps_mean"]) if r.get("band") and r.get("n") and r["n"]["tps_mean"] else None),
                "band_pct": ((2 * r["band"]["sd"] / r["n"]["tps_mean"] * 100) if r.get("band") and r.get("n") and r["n"]["tps_mean"] else r.get("band_pct")),
                "band_title": (f"13-night mean {fmt(r['band']['mean'])} TPS +/- 2 sd ({fmt(2 * r['band']['sd'])} TPS); the same-day nightly is at 0" if r.get("band") else ""),
                "flag": r.get("fid_flag"),
                "tip": (f"nightly {fmt(r['n']['tps_mean'])} TPS, base {fmt(r['b']['tps_mean'])} TPS, z {r['z']:+.1f}" if r.get("n") and r.get("b") and r["b"]["tps_mean"] and r.get("z") is not None else "")} for r in rows]
    chart1 = chart_pct(c1_rows, "Fidelity: base TPS relative to the same-day nightly", "Dot = base against the 2026-09-18 nightly, in percent. Gray band = the 13-night mean +/- 2 standard deviations, drawn where it sits relative to that nightly (a band off centre means the 09-18 nightly itself was off its usual value). A dot inside the band is within 2 sd of the 13 nights. * = fails the fidelity rule of the text below.",
                       "base minus nightly, percent of the nightly", C_BASE, band_key="band_pct")
    c2_rows = [{"label": r["short"], "pct": r.get("eff_pct"), "ci_pct": r.get("eff_ci_pct"), "flag": r.get("eff_flag"),
                "tip": (f"base {fmt(r['b']['tps_mean'])} TPS, target {fmt(r['t']['tps_mean'])} TPS, paired t {r['eff_paired']['t']:+.1f}" if r.get("eff_paired") else "")} for r in rows]
    chart2 = chart_pct(c2_rows, "Effect: target TPS relative to base", "Dot = target vs base (percent); whisker = 95 % confidence interval from the 10 paired round means. * = resolved: |t| >= 2.26, |delta| >= 1 %, and |delta| larger than the config's 13-night band (2 sd), because two consecutive nightlies already differ by up to 4.7 % on the noisy configs. llama-3b's * is not trusted (client-affected config, see the text).",
                       "target minus base, percent of base", C_TARGET)
    c3_rows = [{"label": r["short"], "pct": r.get("eff_ttft_pct"), "ci_pct": r.get("eff_ttft_ci_pct"), "flag": r.get("eff_ttft_flag"),
                "tip": (f"base {fmt(r['b']['ttft_mean'], 0)} ms, target {fmt(r['t']['ttft_mean'], 0)} ms" if r.get("b") and r.get("t") and r["b"].get("ttft_mean") and r["t"].get("ttft_mean") else "")} for r in rows]
    chart3 = chart_pct(c3_rows, "Effect: target TTFT relative to base", "Time to first token, mean over users and rounds; negative = faster. Whisker = 95 % CI over paired rounds. The axis stops at 25 %: llama-3b's value is client-side noise and llama-70b tp2 @4u's TTFT falls into two groups (0.3 s and 5.3 s) whose mix varies per run. From mixtral downward the base ran under client load and the target on an idle client, so those rows compare unlike conditions.",
                       "target minus base, percent of base", C_TARGET, clip=25)
    c4_rows = [{"label": r["short"], "nightly": r["n"]["tps_mean"] if r.get("n") else None, "base": r["b"]["tps_mean"] if r.get("b") else None,
                "target": r["t"]["tps_mean"] if r.get("t") else None, "band": (r["band"]["min"], r["band"]["max"]) if r.get("band") else None, "unit": "TPS"} for r in rows]
    chart4 = chart_abs(c4_rows, "Absolute TPS per config: nightly, base, target", "Tokens per second per user, mean over users and rounds. The base-to-target connector is the change the target package makes.")

    # ---- evidence
    def probes(rec):
        return [(p["model"], p.get("amx_busy_cycles")) for p in (rec or {}).get("amx_probes") or []]
    ev = ['<table><thead><tr><th>check</th><th>base</th><th>target</th></tr></thead><tbody>']
    ev.append(tr(["tron package serving", esc(base_ver), esc(tgt_ver)]))
    ev.append(tr(["rinzler sha256 on disk", esc((fb.get("rinzler_sha") or "?")[:16]) + "&#8230;", esc((ft.get("rinzler_sha") or "?")[:16]) + "&#8230;"]))
    short_of = {m: s.split(" @")[0] for m, u, s, n in ORDER}
    ev.append(tr(["engines running after each provisioning (running/planned)", esc("; ".join(f"{short_of.get(m, m)} {a}/{b}" for m, a, b in fb.get("engine_counts", [])) or "n/a"),
                  esc("; ".join(f"{short_of.get(m, m)} {a}/{b}" for m, a, b in ft.get("engine_counts", [])) or "n/a")]))
    ev.append(tr(["snapshots showing an engine on a deleted (replaced on disk) binary", str(fb.get("deleted", "n/a")), str(ft.get("deleted", "n/a"))]))
    ev.append(tr(["AMX-busy cycles in a 20 s probe (EXE.AMX_BUSY, all engine pids)", esc("; ".join(f"{m.split('-instruct')[0]}: {c:,}" if c is not None else f"{m}: n/a" for m, c in probes(base_rec)) or "no probe"),
                  esc("; ".join(f"{m.split('-instruct')[0]}: {c:,}" if c is not None else f"{m}: n/a" for m, c in probes(tgt_rec)) or "no probe")]))
    ev.append(tr(["hand edit in rinzler@.service (--num-expert-replicas count)", str(fb.get("unit_count", "n/a")), str(ft.get("unit_count", "n/a"))]))
    ev.append(tr(["USE_HW_ATTN / TRON_AMX_* / TRON_K_VNNI in engine env files", esc(fb.get("env_vars") or "n/a"), esc(ft.get("env_vars") or "n/a")]))
    ev.append(tr(["Intel Speed Select policy", esc(fb.get("sst") or "n/a"), esc(ft.get("sst") or "n/a")]))
    cpt_b, cpt_t = (base_rec or {}).get("client_path_timing") or {}, (tgt_rec or {}).get("client_path_timing") or {}
    ev.append(tr(["client to proxy: DNS / connect / full GET, median ms", esc(f"{cpt_b.get('namelookup_ms_median', 'n/a')} / {cpt_b.get('connect_ms_median', 'n/a')} / {cpt_b.get('total_ms_median', 'n/a')}"),
                  esc(f"{cpt_t.get('namelookup_ms_median', 'n/a')} / {cpt_t.get('connect_ms_median', 'n/a')} / {cpt_t.get('total_ms_median', 'n/a')}")]))
    ev.append(tr(["perf phase wall time, minutes (nightly 09-16/17: 79.1 / 78.4)", fmt((base_rec or {}).get("perf_minutes"), 1), fmt((tgt_rec or {}).get("perf_minutes"), 1)]))
    ev.append(tr(["client host / started (UTC)", esc(f"{(base_rec or {}).get('client_host', '?')} / {(base_rec or {}).get('started', '?')}"), esc(f"{(tgt_rec or {}).get('client_host', '?')} / {(tgt_rec or {}).get('started', '?')}")]))
    ev.append("</tbody></table>")

    man_rows = ""
    if manifest:
        man_rows = "".join(f"<tr><td>{esc(k)}</td><td><code>{esc(v if not isinstance(v, dict) else json.dumps(v))}</code></td></tr>" for k, v in manifest.items())

    per_config_notes = "".join(f"<li><b>{esc(r['short'])}</b>: {esc(r['note'])}</li>" for r in rows)

    deviations = (base_rec or {}).get("deviations") or []
    dev_html = "".join(f"<li>{esc(d)}</li>" for d in deviations)

    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Friday morning CI run</title>
<style>
:root{{color-scheme:light;--ink:{INK};--ink2:{INK2};--muted:{MUTED};--grid:{GRID};--surf:{SURF};--page:#f9f9f7;--base:{C_BASE};--target:{C_TARGET};--nightly:{C_NIGHTLY}}}
html,body{{background:var(--page);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:18px;margin:36px 0 8px;border-bottom:1px solid var(--grid);padding-bottom:4px}} h3{{font-size:15px;margin:20px 0 6px}}
p,li{{line-height:1.45;font-size:14px}} .sub{{color:var(--ink2);font-size:13px}}
.short{{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:12px 16px;margin:16px 0}}
.short p{{margin:6px 0}}
table{{border-collapse:collapse;font-size:12.5px;margin:8px 0 16px;background:var(--surf)}} th,td{{border:1px solid var(--grid);padding:4px 8px;text-align:left;vertical-align:top}} th{{color:var(--ink2);font-weight:600}}
td:nth-child(n+2){{font-variant-numeric:tabular-nums}} tr.flag td{{background:#fff4ee}}
.fig{{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:8px;margin:12px 0}}
.legend{{font-size:12px;color:var(--ink2);margin:4px 0 8px}} .legend span{{margin-right:16px}} .legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.take{{font-size:13px;color:var(--ink2);margin:4px 0 0 8px}}
code{{font-size:12px;background:#f1f0ec;padding:1px 4px;border-radius:3px}}
.gloss dt{{font-weight:600;font-size:13px;margin-top:6px}} .gloss dd{{margin:0 0 0 16px;font-size:13px;color:var(--ink2)}}
</style></head><body><main>
<h1>{esc(a.title)}</h1>
<p class="sub">delphi-3bda, whole machine, 2026-09-18 after the nightly. Generated {now} by exec/ci-mimic-20260918/gen_report.py from the run records.</p>

<div class="short"><h2 style="margin-top:0;border:0">Short version</h2>
{"".join(f"<p>{s}</p>" for s in sv)}
</div>

<h2>Words used here</h2>
<dl class="gloss">
<dt>nightly, CI, systems_test, CI runner</dt><dd>CI = continuous integration, the automated nightly test job. The nightly is the systems_test job "System CI (Rinzler 72-core Intel system OCI version)" that runs on delphi-3bda (the 72-core Intel Granite Rapids test machine) every night at 03:30 UTC. systems_test is the repository that holds the system tests. The CI runner is the machine that runs the nightly's client code. This page repeats the nightly's perf phase by hand.</dd>
<dt>arm, config</dt><dd>An arm is one of the two packages under test, base or target, run once through all configs. A config is one row of the nightly's perf list: a model, its tensor-parallel width and a user count, for example llama-3.1-8b good tp2 @8u.</dd>
<dt>harness</dt><dd>The nightly's client code (systems_test scripts/perf.py and testlib/tps.py). It provisions each model, starts the users' requests, and computes TPS and TTFT. The same code produced every number here.</dd>
<dt>platformd, rinzler@N, engine, Caddy</dt><dd>platformd is the daemon on the machine that writes one env file per engine and starts the rinzler@N systemd units. rinzler is the production tron server, and one running rinzler is one engine. Caddy is the port-80 proxy in front of the engines. It sends each new user to the engine with the fewest connections.</dd>
<dt>deb, preset, PR</dt><dd>The deb is the tron apt package the nightly installs. The preset is the CMake build recipe ("deb") that builds it. PR = pull request. PR #4424 is the VNNI-K change (branch jhan-amx-vnniK).</dd>
<dt>base</dt><dd>The package the nightly installed on 2026-09-18 ({esc(base_ver)}). It contains no AMX code. The deb preset never turned the AMX option on.</dd>
<dt>target</dt><dd>Our package {esc(tgt_ver)}. It is PR #4424 merged into the same main commit as the nightly's package, built with the deb preset carrying TRON_AMX_DISPATCH=ON and TRON_K_VNNI=ON.</dd>
<dt>AMX, VNNI-K, K cache, KV head, kv_mul, head size</dt><dd>AMX = Intel Advanced Matrix Extensions, the tile matrix instructions of Granite Rapids CPUs. The AMX kernel accelerates software attention for models with a head size of 128 elements and 4 query heads per KV head (kv_mul = 4). A KV head is one key/value head of attention that several query heads share. The K cache is the stored keys of all earlier tokens. VNNI-K = storing the K cache in the pair-interleaved layout the AMX instructions read (two consecutive tokens side by side), the change of PR #4424.</dd>
<dt>FPGA attention, CPU attention, ingested, USE_HW_ATTN</dt><dd>Ingested models (models converted by tron's ingest compiler) run attention on the FPGA cards (Positron's accelerator cards) by default; here that is qwen-3-4b and gpt-oss. gemma-4-31b is ingested but has no FPGA attention (head size 256). It therefore runs attention on the CPU. Hand-written models (models coded by hand in tron) run attention on the CPU, where AMX and VNNI-K act. USE_HW_ATTN is the environment variable that would force one or the other. It was unset, as in the nightly.</dd>
<dt>tp2, tp4, @Nu, round</dt><dd>tp2 and tp4 = tensor-parallel width, the number of FPGA cards one engine uses (2 or 4). The machine's 8 cards therefore give 4 or 2 engines. @Nu = N concurrent users. A round is one pass in which every user sends one request. Every config runs 10 rounds with fixed prompts.</dd>
<dt>TPS, TTFT, slowest user, prefill</dt><dd>TPS = decode tokens per second per user, measured between generated token 896 and 1024 (2 and 333 for llama-3b), mean over users and rounds. TTFT = time to first token in ms, measured on the client. Slowest user = the minimum TPS sample of a config. Prefill = processing the prompt before the first token.</dd>
<dt>paired t, 95 % interval, z, sd, 13-night band, Slack reports</dt><dd>Paired t = the mean of the 10 per-round differences divided by its standard error. The prompts are fixed. Round r of one run therefore pairs with round r of the other. The 95 % interval is the confidence interval of that mean. sd = standard deviation. The Slack reports are the summary messages the nightly posts to a Slack channel. The 13 reports of 2026-09-05 to 09-17 give each config a mean and sd. z = (base minus the 13-night mean) / the 13-night sd. The band drawn is the 13-night mean +/- 2 sd.</dd>
<dt>thresholds, granite_rapids_72_rinzler</dt><dd>The static goals are the mean-TPS and slowest-user limits the Slack report applies (from systems_test scripts/system_ci.py for the machine profile named granite_rapids_72_rinzler). The ratchet thresholds are a second set in YAML files that tightens over time and is not shown in Slack.</dd>
<dt>EXE.AMX_BUSY probe</dt><dd>A 20 s read of the CPU counter EXE.AMX_BUSY, which counts cycles in which the AMX unit was busy, summed over all engine processes while 4 short requests run. It runs before the benchmark of the probed config. It therefore does not touch the measured rounds.</dd>
<dt>PSI, DUT, sha256, runtron, MoE, talos</dt><dd>PSI = Pressure Stall Information. Its "some" value is the share of time at least one task waited for a CPU. DUT = device under test, delphi-3bda. sha256 = a hash that identifies a file's content. runtron = tron's command-line tool, used in earlier campaigns instead of the server. MoE = mixture of experts. talos = the CI's metrics recorder, replaced here by a local stub.</dd>
</dl>

<h2>1. What ran</h2>
<ul>
<li><b>Machine and layout:</b> the whole of delphi-3bda. The marker file that reserves half the machine for Bill was removed at 01:10 UTC (and again before each relaunch, after the failed attempts had re-created it) and re-created for good at 17:58 UTC after the run. Engines were created by platformd for every config exactly as in the nightly: 4 engines for tp2, 2 for tp4, users spread by Caddy.</li>
<li><b>Client:</b> the harness's own <code>test_performance</code> loop, run by <code>st_ci_perf.py</code> from {esc((base_rec or {}).get('client_host', 'the client host'))} (a container on the same network as the CI runner) with the same Python dependency lock file (uv.lock) as the CI runner, through <code>http://delphi-3bda.positron.internal/v1</code>. Speculative decoding (draft-token prediction) was off (SYSTEM_CI_SPECULATION=0), as in the nightly. Each config ran 10 rounds with a 1024-token prompt and 1536 generated tokens (llama-3b: 800 shared prompt tokens + 200 own prompt tokens, 845 generated tokens).</li>
<li><b>Arms:</b> base = nightly package {esc(base_ver)}; target = {esc(tgt_ver)}. The swap used the nightly's own sequence (apt-get remove, apt-get install), and the nightly's package was reinstalled at the end.</li>
<li><b>Reference:</b> the 2026-09-18 nightly run {esc(a.nightly_run_id) or ''} (package {esc(ngt_ver)}) and the 13 Slack reports 2026-09-05 to 09-17.</li>
</ul>
<h3>Deviations from the real nightly (recorded by the driver)</h3>
<ul>{dev_html}
<li>The nightly runs 25 min of functional tests first, then perf, then MMLU Pro (an accuracy benchmark) and a 3 h soak (a long steady-load test). Here the perf phase followed the nightly's soak (base) or the package swap (target).</li>
<li>One run per arm, one nightly for the same-day comparison. Effects below a config's 13-night band are therefore not resolved (section 3).</li>
</ul>
{("<h3>Caveats and incidents (read before the numbers)</h3>" + caveats_html) if caveats_html else ""}

<h2>2. Fidelity: does base reproduce the nightly?</h2>
<p>Test: the same package, the same harness and the same engine layout, about 10 hours after the nightly's perf phase (04:05 to 05:24 UTC against 13:43 to 15:27 UTC). Observation: the chart and table below. Meaning: a dot inside the gray band is within 2 standard deviations of the last 13 nightlies.</p>
{legend([(C_BASE, "base vs the 2026-09-18 nightly"), (C_BAND, "13-night mean +/- 2 sd, placed relative to the 09-18 nightly")])}
<div class="fig">{chart1}</div>
{"".join(fid_table)}
<h3>Reading rule and reference limits</h3>
<ul>
<li>A row is marked * only if all three hold: |z| &gt; 3 against the 13 nights, base at least 1 % from the 13-night mean, and base at least 1 % from the same-day nightly. The third condition was added after seeing the data, for the case below. The rule was therefore not fixed before the data.</li>
<li>llama-70b tp2 @4u has z +5.1 (base 27.98 TPS against a 13-night mean of 27.64 +/- 0.07 TPS) but is not marked. The same-day nightly was also high, at 27.93 TPS (z +4.3), and base differs from it by +0.2 %. Both runs of that day were high by the same amount. That is not a fidelity miss.</li>
<li>llama-3b (z -2.8) and llama-70b tp2 @8u (z -2.2) are outside 2 sd but inside 3 sd. The llama-3b gap is the client stall described in the caveats.</li>
<li>llama-70b tp2 @8u has a 13-night sd of 0.01 TPS (Slack prints 2 decimals), and llama-3b's reference TTFT is an integer (56 or 57 ms). Tiny z values there carry no information.</li>
<li>qwen-3-4b tp4 and gpt-oss tp4 vary 3 to 5 TPS night to night on their own, and gemma-4-31b has only 3 reference nights.</li>
</ul>

<h2>3. Effect: target (AMX + VNNI-K) vs base</h2>
<p>Test: swap only the package, keep everything else. Observation: the two charts and the table. Meaning: see the rules below.</p>
<ul>
<li>A resolved TPS change (marked *) meets three conditions: its 95 % interval over the 10 paired rounds excludes zero, its size is at least 1 %, and its size is larger than the config's 13-night TPS band (2 sd).</li>
<li>The band condition is needed. The nightlies of 2026-09-16 and 09-17, two consecutive packages without AMX, differ by +4.7 % on qwen-3-4b tp4 with a paired t of 4.2. The t test alone would flag too many changes on the noisy configs.</li>
<li>The TTFT * uses the same three conditions with the config's 13-night TTFT band and a floor of 1 ms.</li>
<li>TTFT differences for the configs from mixtral onward compare unlike client conditions (base under load, target lightly loaded, see the caveats). Their TTFT marks cannot be attributed to the package with this data.</li>
</ul>
{legend([(C_TARGET, "target vs base")])}
<div class="fig">{chart2}</div>
<div class="fig">{chart3}</div>
{"".join(eff_table)}
{("<h3>Reading the effects</h3>" + open(a.notes3).read()) if a.notes3 else ""}
<h3>Which configs can react, and why</h3>
<ul>{per_config_notes}</ul>

<h2>4. Absolute numbers side by side</h2>
{legend([(C_NIGHTLY, "nightly 2026-09-18"), (C_BASE, "base"), (C_TARGET, "target"), (C_BAND, "13-night min to max")])}
<div class="fig">{chart4}</div>

<h2>5. Threshold verdicts (CURRENT static goals, as the Slack report applies them)</h2>
<p>PASS needs mean TPS at or above the goal AND the slowest user at or above the slowest-user goal. These are the thresholds from systems_test scripts/system_ci.py for granite_rapids_72_rinzler; the ratchet YAML thresholds are a separate, unpublished set.</p>
{"".join(thr_table)}
{a.thr_note or ""}

<h2>6. Evidence that the right binary served, and that AMX ran</h2>
{"".join(ev)}
<ul class="take">
<li>Expected on base: 0 AMX-busy cycles. The package has no AMX code.</li>
<li>Expected on target: a large count for llama-3.1-8b (CPU attention) and a smaller one for qwen-3-4b tp2, where FPGA attention leaves only the first 127 positions of each query and the most recent tokens not yet copied to HBM (the high-bandwidth memory on the FPGA card) on the CPU.</li>
<li>A "deleted binary" snapshot means an engine kept running an executable whose file was replaced on disk after it started. The target arm shows this in its "before" snapshot and its first config. In both, the running executable's sha256 matched the target package (details in the caveats). So no config served the wrong package.</li>
</ul>
{("<h3>Target package manifest</h3><table><tbody>" + man_rows + "</tbody></table>") if man_rows else ""}

<h2>7. Files</h2>
<ul>
<li>Run records: <code>exec/results/ci-mimic-20260918/base-pass1/perf.json</code>, <code>target-pass1/perf.json</code> (per-request TPS and TTFT, snapshots, probes), <code>preflight.txt</code>, <code>base-identity.txt</code>.</li>
<li>Reference: <code>exec/results/ci-mimic-20260918/reference/</code> (nightly logs parsed by <code>nightly_to_arm.py</code>, 13-night Slack statistics <code>nightly_stats.json</code>).</li>
<li>Scripts: <code>exec/ci-mimic-20260918/</code> (driver <code>st_ci_perf.py</code>, <code>campaign.sh</code>, <code>dut.sh</code>, target build <code>build-target.sh</code>, this generator).</li>
</ul>
</main></body></html>
"""
    data = html.encode("ascii", "xmlcharrefreplace")
    open(a.out, "wb").write(data)
    print(f"wrote {a.out} ({len(data):,} bytes, ASCII only)")
    for s in sv:
        print(" -", re.sub(r"<[^>]+>", "", s))


if __name__ == "__main__":
    main()
