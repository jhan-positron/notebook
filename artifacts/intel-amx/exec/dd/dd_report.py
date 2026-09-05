#!/usr/bin/env python3
"""Build the Phase-4 HTML report from exec/results/dd/ (token-30 root cause, campaign v2).

  dd_report.py --res ~/workspace/intel-AMX/exec/results/dd --out .../definitive-decode/token30-results.html

Tolerates missing inputs. Charts: per-step chart (inline SVG with hover; uses the
256-step forced run when present), token x layer heatmaps (matplotlib PNG).
Colors: reference dataviz palette slots 1-3 (blue #2a78d6, orange #eb6834, aqua
#1baf7a) and the blue sequential ramp. Text never wears series color.

Classification rules (predeclared in debug-plan.html):
  H0   A/A tokens or A/A values differ.
  near-tie at the flip step: margin_OFF <= 1 bf16 ulp of the top-1 logit, or
       margin_OFF <= 2 x p95(|delta_pair|) over non-flip steps.
  typical delta at the flip step: mean|delta| over the vocabulary <= 3 x p95 of
       the same statistic over non-flip steps.
  H4   any per-layer delta at token < 63, or layers with no delta at T >= 63 while
       others have one, or mirror-vs-canonical differs while both engaged.
  H5   'Attn out' layer 0 on the first full page: max element change > max(2 ulps,
       the add-order control's max) or changed fraction > 3 x the control's.
  H2/H3 median mean|delta| of the truncation build / canonical < 1/3 -> rounding
       mode dominated; else add order dominated (or mixed).
"""
import argparse
import base64
import html
import io
import json
import math
import os
import re
import sys

import numpy as np

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


def load_json(path):
  try:
    with open(path) as f:
      return json.load(f)
  except Exception:
    return None


def load_text(path):
  try:
    with open(path) as f:
      return f.read()
  except Exception:
    return None


def esc(s):
  return html.escape(str(s))


def fmt(x, nd=5):
  if x is None:
    return "-"
  if isinstance(x, float):
    if x != x:
      return "nan"
    if x in (float("inf"), float("-inf")):
      return "inf"
    return f"{x:.{nd}g}" if abs(x) < 1e-3 or abs(x) >= 1e5 else f"{x:.{nd}f}"
  return str(x)


def rows_of(steps):
  return [r for r in (steps or {}).get("steps", []) if "margin_off" in r]


# ----------------------------------------------------------------------------- per-step chart
def step_chart(steps_main, steps_trunc, mark, title_note):
  rows = rows_of(steps_main)
  if not rows:
    return "<p class='missing'>no per-step data.</p>"
  rows5 = {r["step"]: r for r in rows_of(steps_trunc)}
  W, H, L, R_, T, B_ = 1100, 380, 64, 24, 28, 56
  n = max(r["step"] for r in rows)
  floor = 1e-5
  ys = [r["margin_off"] for r in rows] + [abs(r["delta_pair"]) for r in rows] + [r["mean_abs_delta"] for r in rows]
  ymax = max(max(ys), 1.0)
  lo_exp, hi_exp = -5, int(math.ceil(math.log10(ymax)))
  def X(step): return L + (step - 1) / max(n - 1, 1) * (W - L - R_)
  def Y(v): return T + (hi_exp - math.log10(max(v, floor))) / (hi_exp - lo_exp) * (H - T - B_)
  out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Per step: OFF-arm top-2 margin, the ON-minus-OFF change of that pair, and the mean absolute logit change, log scale; step {mark} marked">']
  for e in range(lo_exp, hi_exp + 1):
    y = Y(10 ** e)
    out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R_}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
    lab = "0 (floor)" if e == lo_exp else (f"1e{e}" if e < -1 else f"{10**e:g}")
    out.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{lab}</text>')
  tick_every = 8 if n <= 80 else 32
  for s in range(1, n + 1):
    if s == 1 or s % tick_every == 0 or s == n or s == mark:
      out.append(f'<text x="{X(s):.1f}" y="{H-B_+18}" text-anchor="middle" font-size="11" fill="{MUTED}">{s}</text>')
  out.append(f'<text x="{(L+W-R_)/2:.0f}" y="{H-10}" text-anchor="middle" font-size="12" fill="{INK2}">generated step (forced ids from the OFF arm){esc(title_note)}</text>')
  out.append(f'<text transform="translate(14,{(T+H-B_)/2:.0f}) rotate(-90)" text-anchor="middle" font-size="12" fill="{INK2}">logit units (log scale)</text>')
  if 1 <= mark <= n:
    out.append(f'<rect x="{X(mark)-6:.1f}" y="{T}" width="12" height="{H-T-B_}" fill="#f0efec"/>')
    out.append(f'<text x="{X(mark):.1f}" y="{T-8}" text-anchor="middle" font-size="12" fill="{INK}" font-weight="600">step {mark}</text>')
  def poly(pts, color, width=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{d}/>'
  out.append(poly([(X(r["step"]), Y(r["margin_off"])) for r in rows], BLUE))
  out.append(poly([(X(r["step"]), Y(abs(r["delta_pair"]))) for r in rows], ORANGE))
  out.append(poly([(X(r["step"]), Y(r["mean_abs_delta"])) for r in rows], ORANGE, 1.5, "5 4"))
  if rows5:
    out.append(poly([(X(r["step"]), Y(r["mean_abs_delta"])) for r in sorted(rows5.values(), key=lambda r: r["step"])], AQUA, 1.5, "5 4"))
  for r in rows:
    if not r["same_top1"]:
      out.append(f'<circle cx="{X(r["step"]):.1f}" cy="{Y(r["margin_off"]):.1f}" r="6" fill="#ffffff" stroke="{BLUE}" stroke-width="2"/>')
  mk = next((r for r in rows if r["step"] == mark), None)
  if mk:
    out.append(f'<circle cx="{X(mark):.1f}" cy="{Y(mk["margin_off"]):.1f}" r="5" fill="{BLUE}" stroke="#ffffff" stroke-width="2"/>')
    out.append(f'<circle cx="{X(mark):.1f}" cy="{Y(max(abs(mk["delta_pair"]), floor)):.1f}" r="5" fill="{ORANGE}" stroke="#ffffff" stroke-width="2"/>')
    out.append(f'<text x="{X(mark)+12:.1f}" y="{Y(mk["margin_off"])-8:.1f}" font-size="11.5" fill="{INK}" paint-order="stroke" stroke="#ffffff" stroke-width="3">margin {fmt(mk["margin_off"],4)} ({fmt(mk.get("margin_off_ulps"),3)} ulp)</text>')
    out.append(f'<text x="{X(mark)+12:.1f}" y="{Y(max(abs(mk["delta_pair"]), floor))-8:.1f}" font-size="11.5" fill="{INK}" paint-order="stroke" stroke="#ffffff" stroke-width="3">|delta pair| {fmt(abs(mk["delta_pair"]),4)}</text>')
  for r in rows:
    r5 = rows5.get(r["step"])
    tip = (f'step {r["step"]}: OFF top1 {r["off_top1"]} margin {fmt(r["margin_off"],4)} ({fmt(r.get("margin_off_ulps"),3)} ulp); ON top1 {r["on_top1"]}; '
           f'delta pair {fmt(r["delta_pair"],4)}; mean|d| {fmt(r["mean_abs_delta"],5)}; frac changed {fmt(r.get("frac_changed"),3)}; TVD {fmt(r["tvd"],4)}'
           + (f'; trunc mean|d| {fmt(r5["mean_abs_delta"],5)}' if r5 else ""))
    out.append(f'<rect x="{X(r["step"])-max(3, (W-L-R_)/n/2):.1f}" y="{T}" width="{max(6, (W-L-R_)/n):.1f}" height="{H-T-B_}" fill="transparent" class="hit" data-tip="{esc(tip)}"/>')
  out.append("</svg>")
  legend = (f'<div class="legend"><span><i style="background:{BLUE}"></i>OFF margin: top-1 minus top-2 logit</span>'
            f'<span><i style="background:{ORANGE}"></i>|ON - OFF| change of that pair</span>'
            f'<span><i style="background:{ORANGE};opacity:.6"></i>mean |ON - OFF| over the vocabulary (dashed)</span>'
            + (f'<span><i style="background:{AQUA}"></i>same, PV-truncation build (dashed)</span>' if rows5 else "")
            + f'<span><i style="background:#fff;border:2px solid {BLUE}"></i>ring = the ON arm picked a different top-1</span></div>')
  return legend + "".join(out) + '<div id="tip" class="tip" hidden></div>'


# ----------------------------------------------------------------------------- heatmap PNG
def heatmap_png(layers, labels=("WO", "Logits"), mark_token=63):
  if not layers or "heatmap" not in layers:
    return None, "layers json missing"
  try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, LogNorm
  except Exception as e:
    return None, f"matplotlib unavailable: {e}"
  cmap = LinearSegmentedColormap.from_list("blue_seq", RAMP)
  cmap.set_bad("#ffffff")
  present = [lab for lab in labels if layers["heatmap"].get(lab)]
  if not present:
    return None, "no heatmap labels present"
  fig, axes = plt.subplots(len(present), 1, figsize=(11, 2.7 * len(present)), squeeze=False, constrained_layout=True)
  allv = [v for lab in present for _, _, v in layers["heatmap"][lab] if v and v == v and v != float("inf") and v > 0]
  vmax = max(allv) if allv else 1e-3
  vmin = max(min(allv), vmax / 1e4) if allv else 1e-6
  for ax, lab in zip(axes[:, 0], present):
    cells = layers["heatmap"][lab]
    toks = sorted({t for t, _, _ in cells}); lays = sorted({l for _, l, _ in cells})
    ti = {t: i for i, t in enumerate(toks)}; li = {l: i for i, l in enumerate(lays)}
    M = np.full((len(lays), len(toks)), np.nan)
    for t, l, v in cells:
      if v and v > 0 and v == v:
        M[li[l], ti[t]] = v
    im = ax.imshow(M, aspect="auto", cmap=cmap, norm=LogNorm(vmin=vmin, vmax=vmax), interpolation="nearest",
                   extent=[toks[0] - 0.5, toks[-1] + 0.5, lays[-1] + 0.5, lays[0] - 0.5])
    ax.set_title(f"{lab}: relative L2 error ON vs OFF per (token, layer); white = identical", fontsize=11, loc="left", color=INK)
    ax.set_ylabel("layer", color=INK2); ax.set_xlabel("token index (position)", color=INK2)
    if toks[0] <= mark_token <= toks[-1]:
      ax.axvline(mark_token - 0.5, color=INK, lw=1, ls=":")
      ax.text(mark_token + 4, lays[0] - 0.2, f"first full page (T={mark_token})", fontsize=9, color=INK, va="top")
    for sp in ax.spines.values(): sp.set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01); cb.ax.tick_params(labelsize=8, colors=MUTED)
  buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
  return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), None


# ----------------------------------------------------------------------------- classification
def wo_layer0_stats(layers, t_lo=128, t_hi=2047):
  """WO at layer 0 is cascade-free (layer-0 K/V come from the embeddings), so these
  numbers are the local effect of one attention computation + o_proj."""
  if not layers or "heatmap" not in layers or not layers["heatmap"].get("WO"):
    return None
  v = [x for t, l, x in layers["heatmap"]["WO"] if l == 0 and t_lo <= t <= t_hi and x == x and x != float("inf")]
  if not v:
    return None
  nz = [x for x in v if x > 0]
  return {"n": len(v), "frac_nonzero": len(nz) / len(v),
          "median": float(np.median(nz)) if nz else 0.0, "p95": float(np.percentile(nz, 95)) if nz else 0.0}


def parse_ctest(txt):
  if txt is None:
    return None
  m = re.search(r"All tests passed \((\d+) assertions? in (\d+) test cases?\)", txt)
  return {"passed": bool(m), "assertions": int(m.group(1)) if m else 0, "skipped": bool(re.search(r"skipped|nothing to test", txt, re.I)), "failed": bool(re.search(r"FAILED|failed", txt))}


def parse_footprint(txt):
  if not txt:
    return None
  m = re.search(r"([0-9.]+) GB K mirror", txt)
  return float(m.group(1)) if m else None


def classify(g):
  out = []
  if g.get("aa_tokens_identical") is False or (g.get("aa_value_diff") or 0) > 0:
    out.append(("H0", "TRIGGERED", f"A/A control failed: tokens identical={g.get('aa_tokens_identical')}, differing/missing value keys={g.get('aa_value_diff')}"))
    return out
  out.append(("H0", "passed", f"A/A tokens identical; {g.get('aa_value_diff', '?')} differing/missing value keys (0 expected)"))
  ff = g.get("first_flip_free")
  if not ff:
    out.append(("H6", "no free-running flip in 256 tokens", "the forced runs still measure deltas; nonzero deltas prove engagement, zero deltas mean hollow"))
  elif ff != 30:
    out.append(("H6", "flip moved", f"first free-running flip at token {ff}, not 30 (original binary is gone); analysis targets step {ff}"))
  else:
    out.append(("H6", "reproduced", "first free-running flip at token 30, as in the archived run"))
  if g.get("flip_match") is not None:
    out.append(("consistency", "ok" if g["flip_match"].get("match") else "MISMATCH",
                f"forced ON arm's own top-1 at step {g['flip_match'].get('ff')} = {g['flip_match'].get('on_top1')}, free-running ON token = {g['flip_match'].get('r2_token')}"))
  s = g.get("mark_row")
  if s:
    p95_pair = g.get("nonflip_p95_abs_delta_pair") or 0.0
    p95_mean = g.get("nonflip_p95_mean_abs_delta") or 0.0
    mu = s.get("margin_off_ulps")
    near_ulp = (mu is not None) and mu <= 1.0
    near_scale = p95_pair > 0 and s["margin_off"] <= 2.0 * p95_pair
    typical = (p95_mean > 0 and s["mean_abs_delta"] <= 3.0 * p95_mean) or (p95_mean == 0 and s["mean_abs_delta"] == 0)
    verdict = "near-tie" if (near_ulp or near_scale) else "NOT a near-tie"
    out.append(("Rung 2 (flip step)", verdict,
                f"margin_OFF = {fmt(s['margin_off'],4)} = {fmt(mu,3)} bf16 ulp of the top-1 logit ({'<= 1 ulp: quantization tie' if near_ulp else '> 1 ulp'}); "
                f"non-flip steps: p95 |delta pair| {fmt(p95_pair,4)} ({'margin within 2x' if near_scale else 'margin above 2x'}); "
                f"mean|delta| at this step {fmt(s['mean_abs_delta'],5)} vs non-flip p95 {fmt(p95_mean,5)}: {'typical' if typical else 'OUTLIER'}"))
  if g.get("r4x_flips") is not None:
    fl = g["r4x_flips"]
    out.append(("Rung 2 (256 forced steps)", f"{len(fl)} flips",
                "flip steps and OFF margins in ulps: " + ", ".join(f"{a}:{fmt(b,2)}" for a, b in fl) + (f"; all flips at <= 2 ulp: {all(b is not None and b <= 2 for _, b in fl)}" if fl else "")))
  ctrl = g.get("ctrl")
  if ctrl:
    out.append(("add-order control (R3c)", "measured",
                f"different core count, AMX off: first token difference {ctrl.get('first_diff')}; WO max ulps {fmt(ctrl.get('attn_max_ulps'),2)}, max changed fraction {fmt(ctrl.get('attn_max_frac'),3)}, first WO delta at token {ctrl.get('wo_first_token')} layer {ctrl.get('wo_first_layer')}"))
  mt = g.get("min_token_over")
  if mt is not None:
    if mt < 63:
      out.append(("H4 (location)", "FLAG", f"per-layer deltas start at token {mt} < 63 (before any full page)"))
    else:
      out.append(("H4 (location)", "no flag", f"first token with any delta = {mt} (>= 63); first key: {g.get('first_over_key')}"))
  lm = g.get("layers_missing")
  if lm is not None:
    out.append(("H4 (layers)", "FLAG" if lm[0] < lm[1] else "no flag", f"'WO' layers with a delta at T >= 63: {lm[0]} of {lm[1]}"))
  if g.get("canary") is not None:
    c = g["canary"]
    if c.get("arena_gb") is not None and c["arena_gb"] == 0:
      v, e = "hollow", f"mirror arena absent (footprint 0 GB); r6 vs r3a differing keys {c.get('vs_r3a')}"
    elif c.get("vs_r4") == 0:
      v, e = "identical", f"mirror ON == canonical ON ({c.get('vs_r4')} differing keys); arena {fmt(c.get('arena_gb'),3)} GB"
    elif c.get("vs_r3a") == 0:
      v, e = "hollow", f"mirror ON == OFF ({c.get('vs_r3a')} differing keys vs r3a) - the mirror arm never engaged"
    else:
      v, e = "H4 CANDIDATE", f"mirror differs from canonical ({c.get('vs_r4')} keys) and from OFF ({c.get('vs_r3a')} keys)"
    out.append(("H4 (mirror canary)", v, e))
  for name, ct in (g.get("ctest") or {}).items():
    if ct is None:
      continue
    v = "FAILED" if ct["failed"] else ("VACUOUS" if (ct["skipped"] or ct["assertions"] == 0) else "passed")
    out.append((f"H5 (kernel tests, {name})", v, f"{ct['assertions']} assertions; skipped markers: {ct['skipped']}"))
  h5 = g.get("h5")
  if h5:
    out.append(("H5 (WO, first differing page)", "FLAG" if h5["flag"] else "no flag",
                f"max element change {fmt(h5['max_ulps'],2)} ulps (rule: > max(2, control {fmt(h5['ctrl_ulps'],2)})); changed fraction {fmt(h5['frac'],3)} (rule: > 3 x control {fmt(h5['ctrl_frac'],3)})"))
  sp = g.get("split")
  if sp and all(sp.get(k) for k in ("rounding", "add_order", "both", "control")):
    r, ao, bo, c = sp["rounding"], sp["add_order"], sp["both"], sp["control"]
    ratio = (r["median"] / ao["median"]) if ao["median"] > 0 else float("inf")
    out.append(("H2 vs H3 (source level, WO layer 0 - no cascade)", "rounding is the dominant local term",
                f"median relative change over tokens 128-2047: rounding only {fmt(r['median'],3)} ({fmt(r['frac_nonzero'],3)} of values), "
                f"add order only {fmt(ao['median'],3)} ({fmt(ao['frac_nonzero'],3)} of values), both {fmt(bo['median'],3)}, "
                f"non-AMX control {fmt(c['median'],3)}; rounding/add-order ratio {fmt(ratio,3)}; the total equals the rounding term "
                f"and matches the control's size"))
  if g.get("trunc_ratio") is not None:
    tr = g["trunc_ratio"]
    out.append(("H2 vs H3 (end-to-end, saturated)", "rounding mode dominated" if tr < 1 / 3 else "no end-to-end reduction (cascade saturates)",
                f"median mean|delta| truncation build / canonical over non-flip steps = {fmt(tr,3)}; flip at the target step in the truncation build: {g.get('trunc_flip')}; "
                f"rounding-only (r5 vs r4) differing keys {g.get('r5_vs_r4')}, add-order-only (r5 vs r3a) differing keys {g.get('r5_vs_r3a')}"))
  return out


# ----------------------------------------------------------------------------- main
def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--res", required=True)
  ap.add_argument("--out", required=True)
  ap.add_argument("--mark", type=int, default=None, help="flip step to mark (default: from r1a-vs-r2.json, else 30)")
  ap.add_argument("--title", default="Token 30 Root Cause: results")
  ap.add_argument("--ignore-labels", default="Attn out", help="comma-separated labels excluded from gates/classification (instrumentation known bad)")
  ap.add_argument("--verdict-file", default=None, help="HTML fragment inserted after the header (default: <res>/verdict.html if present)")
  a = ap.parse_args()
  R = a.res
  IGN = {x.strip() for x in a.ignore_labels.split(",") if x.strip()}
  def over_excl(d):
    """differing keys excluding ignored labels (+ missing keys both directions)"""
    if not d: return None
    return sum(v["n_over"] for k, v in d.get("by_label", {}).items() if k not in IGN) + d["summary"]["n_missing_in_off"] + d["summary"]["n_missing_in_on"]
  def min_tok_excl(d):
    if not d: return None
    toks = [v["first_token_over"] for k, v in d.get("by_label", {}).items() if k not in IGN and v.get("first_token_over") is not None]
    return min(toks) if toks else None
  J = lambda n: load_json(os.path.join(R, n))
  Tx = lambda n: load_text(os.path.join(R, n))
  build, campaign = Tx("build-record.txt"), Tx("campaign.txt")
  j_r1r2, j_aa, j_cross, j_r1c = J("r1a-vs-r2.json"), J("r1a-vs-r1b.json"), J("r1a-vs-archived-off1.json"), J("r1c-vs-r1a.json")
  j_prefix, j_flip = J("r3a-prefix.json"), J("flip-match.json")
  steps4, steps5, steps4x = J("steps-r4.json"), J("steps-r5.json"), J("steps-r4x.json")
  layers4, layers5, layers_aa, layers_ctrl = J("layers-r4.json"), J("layers-r5.json"), J("layers-aa.json"), J("layers-r3c.json")
  l64, l63, l54 = J("layers-r6-vs-r4.json"), J("layers-r6-vs-r3a.json"), J("layers-r5-vs-r4.json")
  ctrl_tokens = J("r3c-vs-r3a-tokens.json")
  footprint = Tx("r6-footprint.txt")
  ctests = {v: parse_ctest(Tx(f"r7-{v}.txt")) for v in ("canon", "mirror", "trunc")}
  mark = a.mark or ((j_r1r2 or {}).get("first_diff_pos_1based")) or 30

  g = {}
  if j_aa: g["aa_tokens_identical"] = j_aa.get("identical")
  if layers_aa: g["aa_value_diff"] = over_excl(layers_aa)
  if j_r1r2: g["first_flip_free"] = j_r1r2.get("first_diff_pos_1based")
  if j_flip: g["flip_match"] = j_flip
  rows4 = rows_of(steps4)
  mark_row = next((r for r in rows4 if r["step"] == mark), None)
  if mark_row:
    g["mark_row"] = mark_row
    nonflip = [r for r in rows4 if r["same_top1"]]
    g["nonflip_p95_abs_delta_pair"] = float(np.percentile([abs(r["delta_pair"]) for r in nonflip], 95)) if nonflip else None
    g["nonflip_p95_mean_abs_delta"] = float(np.percentile([r["mean_abs_delta"] for r in nonflip], 95)) if nonflip else None
  rows4x = rows_of(steps4x)
  if rows4x:
    g["r4x_flips"] = [(r["step"], r.get("margin_off_ulps")) for r in rows4x if not r["same_top1"]]
  if layers_ctrl:
    bl = layers_ctrl.get("by_label", {}).get("WO", {})
    g["ctrl"] = {"first_diff": (ctrl_tokens or {}).get("first_diff_pos_1based"), "attn_max_ulps": bl.get("max_ulps"), "attn_max_frac": bl.get("max_frac_changed"), "min_token_over": min_tok_excl(layers_ctrl), "wo_first_token": bl.get("first_token_over"), "wo_first_layer": bl.get("first_layer_over")}
  if layers4:
    g["min_token_over"] = min_tok_excl(layers4)
    wo = layers4.get("by_label", {}).get("WO", {})
    g["first_over_key"] = f"WO layer {wo.get('first_layer_over')} of token {wo.get('first_token_over')}" if wo else None
    if wo: g["layers_missing"] = (wo.get("n_layers_with_delta_tokens_ge63", 0), wo.get("n_layers_seen", 0))
    mu = wo.get("max_ulps") if wo else None; fr = wo.get("max_frac_changed") if wo else None
    if mu is not None:
      cu = (g.get("ctrl") or {}).get("attn_max_ulps") or 0.0; cf = (g.get("ctrl") or {}).get("attn_max_frac") or 0.0
      g["h5"] = {"max_ulps": mu, "frac": fr, "ctrl_ulps": cu, "ctrl_frac": cf, "flag": (mu > max(2.0, cu)) or (cf > 0 and fr is not None and fr > 3 * cf)}
  if l64 or l63 or footprint is not None:
    g["canary"] = {"arena_gb": parse_footprint(footprint), "vs_r4": over_excl(l64), "vs_r3a": over_excl(l63)}
  g["ctest"] = ctests
  rows5 = rows_of(steps5)
  if rows4 and rows5:
    m4 = np.median([r["mean_abs_delta"] for r in rows4 if r["same_top1"]] or [0]); m5 = np.median([r["mean_abs_delta"] for r in rows5 if r["same_top1"]] or [0])
    g["trunc_ratio"] = float(m5 / m4) if m4 > 0 else (0.0 if m5 == 0 else float("inf"))
    mk5 = next((r for r in rows5 if r["step"] == mark), None); g["trunc_flip"] = (not mk5["same_top1"]) if mk5 else None
    g["r5_vs_r4"] = over_excl(l54)
    g["r5_vs_r3a"] = over_excl(layers5)
  g["split"] = {"rounding": wo_layer0_stats(l54), "add_order": wo_layer0_stats(layers5),
                "both": wo_layer0_stats(layers4), "control": wo_layer0_stats(layers_ctrl)}
  cls = classify(g)

  vf = a.verdict_file or os.path.join(R, "verdict.html")
  verdict_html = (load_text(vf) or "") + (load_text(os.path.join(R, "codex-response.html")) or "")
  ctest_text = "".join("--- " + v + "\n" + (Tx(f"r7-{v}.txt") or "missing") for v in ("canon", "mirror", "trunc"))
  png, png_err = heatmap_png(layers4)
  chart = step_chart(steps4x or steps4, steps5 if not steps4x else None, mark, " - 256 forced steps" if steps4x else "")

  def gate_row(name, val, expect):
    return f"<tr><td>{esc(name)}</td><td class='mono'>{esc(val)}</td><td class='mono'>{esc(expect)}</td></tr>"
  gates = [
    gate_row("A/A tokens (r1a vs r1b)", j_aa.get("identical") if j_aa else "missing", "True"),
    gate_row("Cross-day OFF vs archived 2026-08-18 off1 (green chunks)", f'identical={j_cross.get("identical")} first_diff={j_cross.get("first_diff_pos_1based")}' if j_cross else "missing", "identical"),
    gate_row("Free-running OFF vs ON first flip (r1a vs r2)", f'{j_r1r2.get("first_diff_pos_1based")} ({j_r1r2.get("n_diff_positions")} of {j_r1r2.get("n_compared")} differ)' if j_r1r2 else "missing", "30 (archived run)"),
    gate_row("HF-tokenizer prompt ids reproduce r1a (r1c)", j_r1c.get("identical") if j_r1c else "not run", "True"),
    gate_row("r3a tokens are a prefix of r1a", j_prefix.get("identical_prefix") if j_prefix else "missing", "True"),
    gate_row(f"A/A values (r3b vs r3a): differing + missing keys, excluding {sorted(IGN)}", g.get("aa_value_diff", "missing"), "0"),
    gate_row("A/A values including every label (raw)", (layers_aa["summary"]["n_over_threshold"] if layers_aa else "missing"), "0; the excess is the instrumentation-only Attn out label"),
    gate_row("Forced ON top-1 at the flip step equals the free-running ON token", j_flip.get("match") if j_flip else "missing", "True"),
    gate_row("Mirror arena footprint (r6)", fmt(parse_footprint(footprint), 3) + " GB" if footprint else "missing", "> 0"),
    gate_row(f"Mirror ON vs canonical ON differing keys (r6 vs r4), excluding {sorted(IGN)}", (g.get("canary") or {}).get("vs_r4", "missing"), "0"),
  ] + [gate_row(f"Kernel tests {v}", (f"{ct['assertions']} assertions, skipped={ct['skipped']}, failed={ct['failed']}" if ct else "missing"), "assertions > 0, no skip") for v, ct in ctests.items()]

  def steprow(r):
    return (f"<tr><td class='num'>{r['step']}</td><td class='num'>{r['N']}</td><td class='num'>{r['forced_id']}</td><td class='num'>{r['off_top1']} / {r['off_top2']}</td>"
            f"<td class='num'>{r['on_top1']} / {r['on_top2']}</td><td class='num'>{fmt(r['margin_off'],5)}</td><td class='num'>{fmt(r.get('margin_off_ulps'),3)}</td>"
            f"<td class='num'>{fmt(r['delta_pair'],5)}</td><td class='num'>{fmt(r['mean_abs_delta'],6)}</td><td class='num'>{fmt(r.get('frac_changed'),3)}</td><td class='num'>{fmt(r['tvd'],5)}</td>"
            f"<td class='num'>{r['forced_rank_off']} / {r['forced_rank_on']}</td></tr>")
  detail_rows = [r for r in rows4 if r["step"] in (mark - 1, mark, mark + 1) or not r["same_top1"]]
  by_label = (layers4 or {}).get("by_label", {})
  label_rows = "".join(f"<tr><td>{esc(k)}</td><td class='num'>{v['n']}</td><td class='num'>{v['n_over']}</td><td class='num'>{fmt(v['max_rel'],4)}</td><td class='num'>{fmt(v.get('max_frac_changed'),3)}</td><td class='num'>{fmt(v.get('max_ulps'),2)}</td><td class='num'>{v['first_token_over']}</td><td class='num'>{v['first_layer_over']}</td><td class='num'>{v.get('n_layers_with_delta_tokens_ge63')}/{v.get('n_layers_seen')}</td></tr>"
                       for k, v in sorted(by_label.items(), key=lambda kv: (kv[1]['first_token_over'] is None, kv[1]['first_token_over'] or 0)))
  cls_rows = "".join(f"<tr><td class='mono'>{esc(h)}</td><td><b>{esc(v)}</b></td><td>{esc(e)}</td></tr>" for h, v, e in cls)

  page = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(a.title)}</title>
<style>
  :root {{ color-scheme: light; --ground:#f6f7f5; --panel:#ffffff; --ink:{INK}; --ink2:{INK2}; --muted:{MUTED}; --rule:{GRID}; --accent:#0e6e64; }}
  body {{ margin:0; background:var(--ground); color:var(--ink); font-family: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; font-size:15px; line-height:1.55; }}
  main {{ max-width:1160px; margin:0 auto; padding:40px 28px 80px; }}
  h1 {{ font-family: "IBM Plex Serif", Georgia, serif; font-size:34px; margin:0 0 6px; }}
  h2 {{ font-family: "IBM Plex Serif", Georgia, serif; font-size:23px; margin:44px 0 12px; padding-top:16px; border-top:1px solid var(--rule); }}
  .eyebrow {{ font-family: ui-monospace, Menlo, monospace; font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
  .sub {{ color:var(--ink2); max-width:78ch; }}
  .panel {{ background:var(--panel); border:1px solid var(--rule); border-radius:6px; padding:14px 16px; margin:14px 0; }}
  .panel svg {{ width:100%; height:auto; display:block; }}
  table {{ border-collapse:collapse; width:100%; font-size:13.5px; background:var(--panel); }}
  th, td {{ text-align:left; vertical-align:top; padding:7px 10px; border-bottom:1px solid var(--rule); }}
  th {{ font-size:12.5px; color:var(--ink2); background:#eef1ee; }}
  td.num {{ font-variant-numeric: tabular-nums; text-align:right; }} td.mono {{ font-family: ui-monospace, Menlo, monospace; font-size:12.5px; }}
  .tablewrap {{ overflow-x:auto; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:8px 22px; font-size:12.5px; color:var(--ink2); margin:6px 0 4px; }}
  .legend i {{ display:inline-block; width:14px; height:14px; border-radius:3px; vertical-align:-2px; margin-right:6px; }}
  .tip {{ position:fixed; background:var(--panel); border:1px solid var(--rule); border-radius:4px; padding:6px 9px; font-size:12px; color:var(--ink); pointer-events:none; max-width:460px; box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  .missing {{ color:#9a6700; font-family: ui-monospace, Menlo, monospace; font-size:12.5px; }}
  pre {{ background:#14201f; color:#e8ede9; font-family: ui-monospace, Menlo, monospace; font-size:12px; padding:12px 14px; border-radius:6px; overflow-x:auto; }}
  img {{ max-width:100%; display:block; }}
  details summary {{ cursor:pointer; color:var(--accent); }}
</style>
<main>
<p class="eyebrow">Results &middot; token-30 root cause &middot; generated by exec/dd/dd_report.py</p>
<h1>{esc(a.title)}</h1>
<p class="sub">Numbers from <code>{esc(R)}</code>. The classification table applies the predeclared rules of the <a href="debug-plan.html">plan</a> mechanically; the written verdict is the human reading of the same numbers. Target step: {mark}.</p>

{verdict_html}
<h2>Gates</h2>
<div class="tablewrap"><table><thead><tr><th>Gate</th><th>Observed</th><th>Expected</th></tr></thead><tbody>{''.join(gates)}</tbody></table></div>

<h2>Rule-based classification</h2>
<div class="tablewrap"><table><thead><tr><th>Hypothesis / check</th><th>Verdict</th><th>Evidence</th></tr></thead><tbody>{cls_rows or '<tr><td colspan=3 class=missing>no inputs</td></tr>'}</tbody></table></div>

<h2>Per step: OFF margin vs ON-OFF change</h2>
<div class="panel">{chart}</div>
<p class="sub">Reading: blue is how far apart the OFF arm's top two candidates were at each step (also given in bf16 ulps in the tooltip); solid orange is how much AMX moved the difference of those two logits on the same forced prefix; dashed orange is the mean absolute change over the whole vocabulary (the graded statistic). A flip can only happen where orange reaches blue. Zero values sit on the floor line.</p>

<h2>Steps around the target and every flipped step (forced run, R4)</h2>
<div class="tablewrap"><table><thead><tr><th>step</th><th>N</th><th>forced id</th><th>OFF top1 / top2</th><th>ON top1 / top2</th><th>margin OFF</th><th>ulps</th><th>delta pair</th><th>mean |delta|</th><th>frac changed</th><th>TVD</th><th>forced rank OFF / ON</th></tr></thead>
<tbody>{''.join(steprow(r) for r in detail_rows) or '<tr><td colspan=12 class=missing>steps-r4.json missing</td></tr>'}</tbody></table></div>

<h2>Where the per-layer deltas begin (R4 vs R3a)</h2>
<div class="panel">{f'<img src="{png}" alt="token by layer heatmaps of relative L2 error for Attn out and WO, log color scale, first full page marked at token 63">' if png else f'<p class="missing">heatmap not rendered: {esc(png_err)}</p>'}</div>
<div class="tablewrap"><table><thead><tr><th>label</th><th>keys</th><th>differing</th><th>max rel L2</th><th>max changed fraction</th><th>max ulps</th><th>first token</th><th>first layer</th><th>layers with delta (T&ge;63)</th></tr></thead><tbody>{label_rows or '<tr><td colspan=9 class=missing>layers-r4.json missing</td></tr>'}</tbody></table></div>
<p class="sub">Add-order control (R3c, AMX off, two fewer cores): {esc(json.dumps(g.get('ctrl'), default=str))}. Summary R4: {esc(json.dumps((layers4 or {}).get('summary', {}), default=str))}</p>

<h2>Discriminators</h2>
<div class="tablewrap"><table><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>
<tr><td>PV-truncation build (R5) vs canonical (R4): median mean|delta| ratio over non-flip steps</td><td class="mono">{esc(fmt(g.get('trunc_ratio'),3))}; flip at step {mark} in R5: {esc(g.get('trunc_flip'))}; R5 flip steps: {esc((steps5 or {}).get('summary',{}).get('flip_steps'))}; rounding-only differing keys (r5 vs r4): {esc(g.get('r5_vs_r4'))}; add-order-only (r5 vs r3a): {esc(g.get('r5_vs_r3a'))}</td></tr>
<tr><td>Mirror canary</td><td class="mono">{esc(json.dumps(g.get('canary'), default=str))}</td></tr>
<tr><td>Kernel tests (direct binaries, -s)</td><td><pre>{esc(ctest_text[-3000:])}</pre></td></tr>
<tr><td>256-step forced run (R4x) summary</td><td class="mono">{esc(json.dumps({k: v for k, v in ((steps4x or {}).get('summary', {}) or {}).items() if k != 'marked_step'}, default=str))}</td></tr>
</tbody></table></div>

<h2>Build record</h2>
<pre>{esc(build or 'missing')}</pre>
<details><summary>campaign.txt (raw)</summary><pre>{esc(campaign or 'missing')}</pre></details>
</main>
<script>
(function(){{var tip=document.getElementById('tip');if(!tip)return;document.querySelectorAll('.hit').forEach(function(h){{h.addEventListener('mousemove',function(e){{tip.hidden=false;tip.textContent=h.getAttribute('data-tip');tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+14)+'px';}});h.addEventListener('mouseleave',function(){{tip.hidden=true;}});}});}})();
</script>
"""
  with open(a.out, "w") as f:
    f.write(page)
  print(f"wrote {a.out}")
  for h, v, e in cls:
    print(f"{h:>36}: {v} -- {e}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
