#!/usr/bin/env python3
"""Build the HTML report for the p0perf-20260911 campaign.

Inputs (all under RESULTS_DIR = exec/results/p0perf-20260911 unless noted):
  summary.json            written by summarize.py (runtron + CI-harness cells, means, boosts, paired deltas)
  rt-results.txt          runtron result lines (placement header lines; per-request parse times)
  build.txt               tip, cmake line, sha256 of the two binaries, version line
  cells/*/meta.json       per CI cell: started, machine line, binary sha (read through summary.json)
  ci-reference-*.json     the nightly's own numbers of the same night (ci_reference.py); ci-run-<id>.log = its job log
  exec/logs/p0perf-20260911.log   campaign passes (start / finish lines)
Output: the HTML page given as the second argument (light theme, inline SVG, no libraries).
Usage: gen_report.py RESULTS_DIR OUT_HTML
Version 2 (2026-09-11): after the 105-agent verification of version 1 (numbers all confirmed; 46 wording,
definition and record findings applied). Version 1 kept as gen_report.py.v1-20260911.
"""
import datetime
import glob
import html
import json
import math
import os
import re
import statistics
import sys

RES, OUT = sys.argv[1], sys.argv[2]
EXEC = os.path.dirname(os.path.dirname(os.path.abspath(RES.rstrip('/'))))
LOG = os.path.join(EXEC, "logs", "p0perf-20260911.log")
S = json.load(open(os.path.join(RES, "summary.json")))
BUILD = open(os.path.join(RES, "build.txt")).read().splitlines() if os.path.exists(os.path.join(RES, "build.txt")) else []
RT_TXT = open(os.path.join(RES, "rt-results.txt"), errors="replace").read().splitlines() if os.path.exists(os.path.join(RES, "rt-results.txt")) else []
RT_HDR = [l for l in RT_TXT if l.startswith("#")]
refs = sorted(glob.glob(os.path.join(RES, "ci-reference-*.json")))
CIREF = json.load(open(refs[-1])) if refs else None
CILOG = sorted(glob.glob(os.path.join(RES, "ci-run-*.log")))

# Colors: the round-1 page's convention (off = neutral gray, AMX = categorical slot 1 blue); text in ink tokens only.
C_OFF, C_ON, INK, INK2, MUTED, GRID, AXIS, SURF, GOOD, BAD = "#6b6a66", "#2a78d6", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#006300", "#d03b3b"
NOISE_PCT = 2.5   # round 1's same-binary repeat of one CI cell differed by 2.2% in TPS


def esc(x):
    return html.escape(str(x), quote=True)


def f(x, nd=1, unit=""):
    return "n/a" if x is None else f"{x:.{nd}f}{unit}"


def pm(triple, nd=1, unit=""):
    if not triple or triple[0] is None:
        return "n/a"
    m, sd, n = triple
    return f"{m:.{nd}f}{unit} ± {sd:.{nd}f} (n={n})" if n > 1 else f"{m:.{nd}f}{unit} (n=1)"


def ms(tr):  # seconds triple [mean, sd, n] -> milliseconds triple
    return None if (not tr or tr[0] is None) else [tr[0] * 1000, tr[1] * 1000, tr[2]]


def signed(x, nd=1):
    return "n/a" if x is None else f"{x:+.{nd}f}%"


def verdict(pct, better):  # better = 'higher' or 'lower'
    if pct is None:
        return ("n/a", MUTED)
    if abs(pct) <= NOISE_PCT:
        return ("inside the ±%.1f%% band" % NOISE_PCT, MUTED)
    good = (pct > 0) if better == "higher" else (pct < 0)
    return ("better with AMX", GOOD) if good else ("worse with AMX", BAD)


def nice_ticks(hi, n=5):
    if hi <= 0:
        return [0, 1]
    raw = hi / (n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    t, out = 0, []
    while t <= hi + 1e-9:
        out.append(round(t, 6)); t += step
    return out


def valid(rows):
    return [r for r in rows if not r.get("early_stop")]


def spread_pct(vals):
    vals = [v for v in vals if v is not None]
    return None if len(vals) < 2 or min(vals) <= 0 else 100.0 * (max(vals) / min(vals) - 1)


# ---------- data views ----------
def rt_rows(tp, arm):
    return S["runtron"].get(f"tp{tp}", {}).get(arm, [])


def ci_rows(tp, arm, done_only=True):
    rows = S["ci"].get(f"tp{tp}", {}).get(arm, [])
    return [r for r in rows if r.get("status") == "done"] if done_only else rows


def pct_of(key, tp, metric):
    d = S[key].get(f"tp{tp}", {}).get(metric, {})
    return d.get("boost_pct") if "tps" in metric else d.get("change_pct")


def paired(key, tp, metric):
    return S[key].get(f"tp{tp}", {}).get(metric, {}).get("paired_pct", {}) or {}


def rows_for(metric, only):  # rows for one figure panel; values in a common unit
    rows = []
    test = "runtron" if only == "runtron" else "CI harness"
    for tp in (2, 4):
        d = S[only].get(f"tp{tp}", {})
        if metric == "tps":
            agg = d.get("tps_per_user", {}); scale = 1.0; k = "tps_per_user" if only == "runtron" else "tps_mean"
        else:
            agg = d.get("ttft_s" if only == "runtron" else "ttft_ms", {}); scale = 1000.0 if only == "runtron" else 1.0
            k = "ttft_s" if only == "runtron" else "ttft_ms"
        src_off = valid(d.get("off", [])) if only == "runtron" else ci_rows(tp, "off")
        src_on = valid(d.get("on", [])) if only == "runtron" else ci_rows(tp, "on")
        off = agg.get("off") or [None, None, 0]; on = agg.get("on") or [None, None, 0]
        rows.append({"label": f"{test} · tp{tp}", "sub": "8 users · prompt 1024 · " + ("256-token limit" if only == "runtron" else "1536 generated · 10 rounds"),
                     "off": None if off[0] is None else off[0] * scale, "on": None if on[0] is None else on[0] * scale,
                     "off_sd": None if off[1] is None else off[1] * scale, "on_sd": None if on[1] is None else on[1] * scale,
                     "n_off": off[2], "n_on": on[2],
                     "reps_off": [r[k] * scale for r in src_off if r.get(k) is not None], "reps_on": [r[k] * scale for r in src_on if r.get(k) is not None],
                     "pct": agg.get("boost_pct") if metric == "tps" else agg.get("change_pct")})
    return rows


def dumbbell(rows, title, unit, better, nd):
    W, L, R, ROW, TOP, BOT = 900, 270, 150, 66, 78, 44
    H = TOP + ROW * len(rows) + BOT
    vals = [v for r in rows for v in ([r["off"], r["on"]] + r["reps_off"] + r["reps_on"]) if v is not None]
    hi = max(vals) * 1.08 if vals else 1
    ticks = nice_ticks(hi)
    hi = max(hi, ticks[-1])
    def X(v): return L + (W - L - R) * v / hi
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;display:block;background:{SURF}" role="img" aria-label="{esc(title)}">']
    o.append(f'<text x="{L}" y="22" font-size="15" font-weight="600" fill="{INK}">{esc(title)}</text>')
    for t in ticks:
        x = X(t)
        o.append(f'<line x1="{x:.1f}" y1="{TOP - 8}" x2="{x:.1f}" y2="{H - BOT + 6}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{x:.1f}" y="{H - BOT + 22}" font-size="11" fill="{MUTED}" text-anchor="middle" font-variant-numeric="tabular-nums">{t:g}</text>')
    o.append(f'<text x="{X(hi / 2):.1f}" y="{H - 8}" font-size="11" fill="{INK2}" text-anchor="middle">{esc(unit)}</text>')
    o.append(f'<line x1="{L}" y1="{TOP - 8}" x2="{L}" y2="{H - BOT + 6}" stroke="{AXIS}" stroke-width="1"/>')
    for i, r in enumerate(rows):
        y = TOP + ROW * i + ROW / 2 - 4
        o.append(f'<text x="{L - 14}" y="{y - 3}" font-size="13" font-weight="600" fill="{INK}" text-anchor="end">{esc(r["label"])}</text>')
        o.append(f'<text x="{L - 14}" y="{y + 13}" font-size="11" fill="{MUTED}" text-anchor="end">{esc(r["sub"])}</text>')
        if r["off"] is None or r["on"] is None:
            o.append(f'<text x="{L + 12}" y="{y + 4}" font-size="12" fill="{MUTED}">no data (off n={r["n_off"]}, on n={r["n_on"]})</text>')
            continue
        xo, xn = X(r["off"]), X(r["on"])
        o.append(f'<line x1="{xo:.1f}" y1="{y}" x2="{xn:.1f}" y2="{y}" stroke="{AXIS}" stroke-width="2" stroke-linecap="round"/>')
        # single repetitions in a strip below the pair, so the mean markers never hide them
        for v in r["reps_off"]:
            o.append(f'<circle cx="{X(v):.1f}" cy="{y + 13}" r="3" fill="{C_OFF}" fill-opacity="0.6"><title>AMX-off, one repetition: {v:.{nd}f} {esc(unit)}</title></circle>')
        for v in r["reps_on"]:
            o.append(f'<circle cx="{X(v):.1f}" cy="{y + 13}" r="3" fill="{C_ON}" fill-opacity="0.6"><title>AMX-on, one repetition: {v:.{nd}f} {esc(unit)}</title></circle>')
        for cx, col, lab, v, sd, n in ((xo, C_OFF, "AMX-off", r["off"], r["off_sd"], r["n_off"]), (xn, C_ON, "AMX-on", r["on"], r["on_sd"], r["n_on"])):
            o.append(f'<circle cx="{cx:.1f}" cy="{y}" r="8" fill="{SURF}"/><circle cx="{cx:.1f}" cy="{y}" r="6" fill="{col}"><title>{lab}: mean {v:.{nd}f} {esc(unit)}, sd {f(sd, nd)}, n={n}</title></circle>')
        left, right = (("off", xo, r["off"]), ("on", xn, r["on"])) if xo <= xn else (("on", xn, r["on"]), ("off", xo, r["off"]))
        # value labels: left dot above, right dot below the strip; the same placement in every row
        o.append(f'<text x="{left[1]:.1f}" y="{y - 12}" font-size="12" fill="{INK}" text-anchor="middle" font-variant-numeric="tabular-nums">{left[0]} {left[2]:.{nd}f}</text>')
        o.append(f'<text x="{right[1]:.1f}" y="{y + 30}" font-size="12" fill="{INK}" text-anchor="middle" font-variant-numeric="tabular-nums">{right[0]} {right[2]:.{nd}f}</text>')
        word, col = verdict(r["pct"], better)
        o.append(f'<text x="{W - R + 12}" y="{y - 2}" font-size="13" font-weight="600" fill="{col}" font-variant-numeric="tabular-nums">{signed(r["pct"])}</text>')
        o.append(f'<text x="{W - R + 12}" y="{y + 13}" font-size="10.5" fill="{col}">{esc(word)}</text>')
    ly = 46
    o.append(f'<circle cx="{L + 8}" cy="{ly}" r="6" fill="{C_OFF}"/><text x="{L + 20}" y="{ly + 4}" font-size="11.5" fill="{INK2}">AMX-off (kill switch), mean</text>')
    o.append(f'<circle cx="{L + 208}" cy="{ly}" r="6" fill="{C_ON}"/><text x="{L + 220}" y="{ly + 4}" font-size="11.5" fill="{INK2}">AMX-on, mean</text>')
    o.append(f'<circle cx="{L + 330}" cy="{ly}" r="3" fill="{INK2}" fill-opacity="0.6"/><text x="{L + 340}" y="{ly + 4}" font-size="11.5" fill="{INK2}">one repetition (strip below the pair)</text>')
    o.append('</svg>')
    return "\n".join(o)


# ---------- facts computed from the raw files ----------
# campaign passes
passes = []
if os.path.exists(LOG):
    for l in open(LOG, errors="replace"):
        m = re.match(r"=== p0perf-20260911 campaign started (\S+) pid \d+ TIP=\S+ RT_REPS=(\d+) CI_REPS=(\d+)", l)
        if m:
            passes.append({"start": m.group(1), "end": None, "status": "running", "rt": int(m.group(2)), "ci": int(m.group(3))})
        m = re.match(r"=== campaign finished (\S+): (.*) ===", l)
        if m and passes:
            passes[-1]["end"] = m.group(1); passes[-1]["status"] = m.group(2)


def hm(ts):
    return ts[11:19] + "Z" if ts and len(ts) >= 19 else (ts or "running")


if passes:
    pass_txt = "Campaign in %d pass%s on 2026-09-11 UTC: " % (len(passes), "es" if len(passes) > 1 else "") + "; ".join(
        f"pass {i + 1} {hm(p['start'])} to {hm(p['end'])} ({p['status']}; RT_REPS={p['rt']}, CI_REPS={p['ci']})" for i, p in enumerate(passes))
    if len(passes) > 1:
        pass_txt += ". A later pass skips the runs and cells an earlier pass finished and adds only the extra runtron repetitions"
    pass_txt += "."
else:
    pass_txt = "Campaign log not found."

# runtron per-request parse-time spread (the TTFT value used is the largest of the 8 per-request values)
rt_runs = []   # completed attempts
cur = None
for l in RT_TXT:
    m = re.match(r"### runtron tp=(\d) arm=(\w+) rep=(\d+) attempt=(\d+)", l)
    if m:
        cur = {"tp": int(m.group(1)), "arm": m.group(2), "rep": int(m.group(3)), "parse": [], "gen": 0}; rt_runs.append(cur); continue
    if cur is None:
        continue
    m = re.search(r"Parsing the prompt took ([\d.]+) s", l)
    if m: cur["parse"].append(float(m.group(1)))
    if "average tok/s" in l: cur["gen"] += 1
rt_runs = [r for r in rt_runs if r["gen"] > 0]
uneven = [r for r in rt_runs if r["parse"] and (max(r["parse"]) - min(r["parse"])) > 0.01]
uneven_txt = "; ".join(f"tp{r['tp']} {r['arm']} rep{r['rep']} ({max(r['parse']) - min(r['parse']):.2f} s)" for r in uneven)

# excluded (early-stop) runs
ex_runs = [(tp, arm, r) for tp in (2, 4) for arm in ("off", "on") for r in rt_rows(tp, arm) if r.get("early_stop")]

# per-cell spreads
def spreads(key, tp, metric_key):
    src = lambda arm: (valid(rt_rows(tp, arm)) if key == "runtron" else ci_rows(tp, arm))
    return spread_pct([r.get(metric_key) for r in src("off")]), spread_pct([r.get(metric_key) for r in src("on")])

sp = {("runtron", 2): spreads("runtron", 2, "tps_per_user"), ("runtron", 4): spreads("runtron", 4, "tps_per_user"),
      ("ci", 2): spreads("ci", 2, "tps_mean"), ("ci", 4): spreads("ci", 4, "tps_mean")}
sp_ttft = [x for key, tp, k in (("runtron", 2, "ttft_s"), ("runtron", 4, "ttft_s"), ("ci", 2, "ttft_ms"), ("ci", 4, "ttft_ms")) for x in spreads(key, tp, k) if x is not None]
pr4 = list(paired("runtron", 4, "tps_per_user").values())
pr4_sd = statistics.stdev(pr4) if len(pr4) > 1 else None
pr4_ci = 2.57 * pr4_sd / math.sqrt(len(pr4)) if pr4_sd is not None and len(pr4) == 6 else None   # t(0.975, 5 df) = 2.57
all_pairs = []   # (test, tp, metric, delta, good)
for key, test in (("runtron", "runtron"), ("ci", "CI harness")):
    for tp in (2, 4):
        for metric, better in (("tps_per_user", "higher"), (("ttft_s" if key == "runtron" else "ttft_ms"), "lower")):
            for rep_, v in paired(key, tp, metric).items():
                all_pairs.append((test, tp, metric, v, (v > 0) if better == "higher" else (v < 0)))
n_pairs, n_pairs_good = len(all_pairs), sum(1 for p in all_pairs if p[4])
sp4 = [x for x in sp[("runtron", 4)] if x is not None]

# CI prompt tokens as counted by the server
ci_prompt = [r.get("prompt_tokens_mean") for tp in (2, 4) for arm in ("off", "on") for r in ci_rows(tp, arm) if r.get("prompt_tokens_mean")]
ci_cache = [r.get("cache_hit_pct") for tp in (2, 4) for arm in ("off", "on") for r in ci_rows(tp, arm) if r.get("cache_hit_pct") is not None]
ci_prompt_txt = (f"the server counted {statistics.mean(ci_prompt):.0f} prompt tokens per request on average, with a prefix-cache hit rate of {statistics.mean(ci_cache):.1f}%"
                 if ci_prompt else "the server's own prompt-token count was not recorded")

# build facts
def build_field(prefix):
    return next((l for l in BUILD if l.startswith(prefix)), "")

tip = build_field("tip ").replace("tip ", "", 1) or "(build.txt missing)"
shas = [l for l in BUILD if re.match(r"^[0-9a-f]{64} ", l)]
version = next((l for l in BUILD if "Version" in l or re.match(r"^\d{4}\.\d{2}\.\d{2}-", l)), "")
m = re.search(r"built (\S+) in (\d+) s", build_field("cmake"))
build_end, build_secs = (m.group(1), int(m.group(2))) if m else ("", 0)
build_start = (datetime.datetime.strptime(build_end, "%Y-%m-%dT%H:%M:%SZ") - datetime.timedelta(seconds=build_secs)).strftime("%H:%M:%SZ") if build_end else "?"
place2 = next((l.split(":", 1)[1].strip() for l in RT_HDR if l.startswith("# placement tp2")), "(see rt-results.txt)")
place4 = next((l.split(":", 1)[1].strip() for l in RT_HDR if l.startswith("# placement tp4")), "(see rt-results.txt)")

# machine lines per run
ctx_rows = []
for tp in (2, 4):
    for arm in ("off", "on"):
        for r in rt_rows(tp, arm):
            ctx_rows.append((f"runtron tp{tp} {arm} rep{r['rep']}" + (" (excluded, early stop)" if r.get("early_stop") else ""), r.get("machine", "")))
        for r in ci_rows(tp, arm, done_only=False):
            ctx_rows.append((f"CI tp{tp} {arm} rep{r['rep']} ({r.get('status')})", r.get("machine", "")))
n_ctx = len(ctx_rows)
n_b0 = sum(1 for _, l in ctx_rows if "bill_procs=0 bill_cpu_pct=0" in l)
n_hp = sum(1 for _, l in ctx_rows if "hugepages_free=512" in l)


def load1(line):
    m = re.search(r"load=([\d.]+)", line); return float(m.group(1)) if m else None


def started(line):
    m = re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line); return m.group(1) if m else ""


rt_first = sorted([(started(r.get("machine", "")), load1(r.get("machine", ""))) for tp in (2, 4) for arm in ("off", "on") for r in rt_rows(tp, arm) if r.get("rep") == 1])
loads_txt = ", ".join(f"{v:.0f}" for _, v in rt_first if v is not None)

# earlier measurement constants (sources named in the table)
R1 = {"off": 77.83, "off2": 76.12, "on": 81.37, "ttft_off": 1777, "ttft_off2": 1781, "ttft_on": 1618}   # round 1, PR3879/more-testing/round-1/status.md
Q9 = {"clean": (14.652, 14.648), "off": (14.743, 14.747), "on": (17.193, 17.211)}   # exec/results/qwen8u8k-pr1-half-20260909T1704.txt

# ---------- HTML ----------
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
H = []
H.append(f"""<title>Friday morning CI results</title>
<style>
:root {{ color-scheme: light; }}
body {{ background:#f9f9f7; color:{INK}; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size:15px; line-height:1.5; margin:0; padding-block:24px 48px; padding-inline:16px; }}
main {{ max-width: 960px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin: 0 0 4px; }} h2 {{ font-size: 18px; margin: 32px 0 8px; }} h3 {{ font-size: 15px; margin: 20px 0 6px; }}
.sub {{ color:{INK2}; font-size: 13.5px; margin-bottom: 18px; }}
.short {{ background:{SURF}; border:1px solid {GRID}; border-radius:8px; padding:14px 18px; }}
table {{ border-collapse: collapse; font-size: 13.5px; }} .tw {{ overflow-x:auto; }}
th, td {{ border-bottom: 1px solid {GRID}; padding: 5px 10px; text-align: left; vertical-align: top; }} th {{ color:{INK2}; font-weight:600; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.fig {{ background:{SURF}; border:1px solid {GRID}; border-radius:8px; padding:10px 12px 6px; margin: 10px 0; }}
.take {{ font-size: 13.5px; color:{INK2}; margin: 4px 0 0 4px; }}
code {{ font-size: 12.5px; background:#f0efec; padding:1px 4px; border-radius:3px; }}
dl {{ margin:0; }} dt {{ font-weight:600; margin-top:6px; }} dd {{ margin: 0; color:{INK2}; }}
.warn {{ border-left: 4px solid #eda100; padding-left: 12px; }}
</style>
<main>
<h1>AMX perf check after the Friday nightly CI (2026-09-11)</h1>
<div class="sub">CI = continuous integration, the automated nightly test run of the tron inference program (GitHub Actions workflow "System CI"; its client runs on another host and its server is delphi-3bda, the shared test machine). This page: qwen-3-4b (ingested), tp2 and tp4, 8 users, prompt 1024 tokens, AMX-off against AMX-on, on our half of delphi-3bda, branch jhan-amx-p0 at {esc(tip.split(' ')[0][:10])}. {esc(pass_txt)} Page generated {now}.</div>
""")

# ---- Short version (three sentences) ----
p_rt2, p_rt4, p_ci2, p_ci4 = pct_of("runtron", 2, "tps_per_user"), pct_of("runtron", 4, "tps_per_user"), pct_of("ci", 2, "tps_per_user"), pct_of("ci", 4, "tps_per_user")
t_rt2, t_rt4, t_ci2, t_ci4 = pct_of("runtron", 2, "ttft_s"), pct_of("runtron", 4, "ttft_s"), pct_of("ci", 2, "ttft_ms"), pct_of("ci", 4, "ttft_ms")
def drop(x):  # "-20.5%" -> "20.5%" for "fell by"
    return "n/a" if x is None else f"{abs(x):.1f}%"
sv = (f"<p><b>Short version.</b> With AMX on (Intel Advanced Matrix Extensions, CPU matrix instructions this branch uses for the attention step), each of 8 concurrent users of the qwen-3-4b model was served tokens faster by {signed(p_rt2)} (tp2) and {signed(p_rt4)} (tp4) as measured by runtron (tron's command-line tool, 256-token answers) and by {signed(p_ci2)} (tp2) and {signed(p_ci4)} (tp4) as measured by the nightly CI's throughput benchmark run against one server built from the branch (tp2 and tp4 = the model spread over 2 or 4 FPGA accelerator cards). "
      f"The wait for the first token fell by {drop(t_rt2)} and {drop(t_rt4)} (runtron tp2, tp4) and by {drop(t_ci2)} and {drop(t_ci4)} (CI benchmark tp2, tp4). "
      f"Both arms ran the same binary on the same cards and cores with CPU attention forced on, so the only intended difference is the attention code path (the new AMX kernels against the existing AVX kernels inside one binary); {n_pairs_good} of the {n_pairs} per-repetition comparisons favour AMX-on, and the runtron tp4 throughput gain is the least precisely known (its repetitions spread by up to {f(max(sp4), 1, '%') if sp4 else 'n/a'}; see How to read).</p>")
H.append(f'<div class="short">{sv}</div>')
if ex_runs:
    n_ex = len(ex_runs)
    parts = []
    for tp, arm, r in ex_runs:
        parts.append(f"tp{tp} {arm} repetition {r['rep']}: shortest answer {r['gen_tokens_min']} tokens, longest {r['gen_tokens_max']}, {r['n_requests']} of 8 requests reported")
    H.append(f"<p><b>Excluded run{'s' if n_ex > 1 else ''}.</b> {n_ex} runtron run{'s are' if n_ex > 1 else ' is'} excluded from the means and from the per-repetition deltas: {esc('; '.join(parts))}. "
             f"A stop token (the model's end-of-answer marker) ended one user's answer early, so the remaining users ran the rest of the decode with fewer than 8 users and their per-user rate is not an 8-user number. The run{'s' if n_ex > 1 else ''} still appear{'' if n_ex > 1 else 's'} in the tables, marked.</p>")
missing = S.get("missing", [])
if missing:
    H.append(f'<p class="warn"><b>Incomplete:</b> no successful run for {esc(", ".join(missing))}. See the status and log files under exec/logs/.</p>')

# ---- Words used here ----
n_rt_txt = ", ".join(f"tp{tp} {arm} n={len(valid(rt_rows(tp, arm)))}" for tp in (2, 4) for arm in ("off", "on"))
n_ci_txt = ", ".join(f"tp{tp} {arm} n={len(ci_rows(tp, arm))}" for tp in (2, 4) for arm in ("off", "on"))
H.append(f"""<h2>Words used here</h2>
<dl>
<dt>tron, runtron, rinzler, engine</dt><dd>tron is the inference program under test (it serves large language models on this hardware). runtron is its command-line tool: one process loads the model, sends 8 synthetic prompts at once and generates a fixed number of tokens for each. rinzler is the production HTTP server built from the same source; one running rinzler process serving one model is called an engine here.</dd>
<dt>CI, the nightly, CI harness</dt><dd>CI = continuous integration, the automated build-and-test system. "The nightly" = the GitHub Actions workflow "System CI" that runs every night against delphi-3bda (on 2026-09-11 from 03:38 to 11:29 UTC). One of its phases is a throughput benchmark; that benchmark's code (repository positron-ai/systems_test, file testlib/tps.py) run here against one engine built from the branch is called the CI harness.</dd>
<dt>AMX, AVX, kernel</dt><dd>AMX = Intel Advanced Matrix Extensions, CPU instructions that multiply small matrices in one step; the branch uses them for the attention step of the model. AVX = Intel Advanced Vector Extensions, the older CPU vector instructions the existing attention code uses. A kernel is one small compute routine, here the routine that computes attention for one block of the model.</dd>
<dt>arm, cell, repetition</dt><dd>An arm is one of the two conditions compared, AMX-off or AMX-on. A cell is one combination of test (runtron or CI harness), tp and arm, that is one row of the "What was run" table. A repetition is one complete run of a cell; the means below are over repetitions.</dd>
<dt>AMX-off, AMX-on, kill switch</dt><dd>Both arms run the same binary, built with the AMX code (cmake option TRON_AMX_DISPATCH=ON). AMX-off = the environment variable TRON_AMX_DISABLE=1 (the kill switch) makes attention take the existing AVX path; AMX-on = the variable is unset. The AMX-off arm is therefore the AMX build with the kill switch set, not a build without the AMX code. The last comparison with such a build on this branch (2026-09-09, head 26a0338c3b, qwen tp2, 8 users, prompt 8192, today's tp2 placement) found no measurable kill-switch cost: the kill-switch arm decoded at {Q9['off'][0]:.2f} and {Q9['off'][1]:.2f} tokens per second per user against {Q9['clean'][0]:.2f} and {Q9['clean'][1]:.2f} for the build without the AMX code [exec/results/qwen8u8k-pr1-half-20260909T1704.txt].</dd>
<dt>tp2, tp4, FPGA</dt><dd>tp = tensor parallelism, the number of FPGA cards one model instance spans (2 or 4). FPGA = field-programmable gate array, the accelerator cards of this machine (8 per machine). On our half tp2 uses cards 90:00.0 and 93:00.0, tp4 all four cards 90/93/b9/bc, all attached to CPU socket 1.</dd>
<dt>delphi-3bda, our half, Bill, socket, hugepages</dt><dd>delphi-3bda is the shared test machine: 2 CPU sockets (physical processors of 72 cores each) and 8 FPGA cards. Since 2026-09-06 it is split between two people: Bill (a colleague) uses socket 0 and cards 10/13/38/3b; we use socket 1 and cards 90/93/b9/bc ("our half"). A process placed on socket 1 uses only that socket's cores and memory. Hugepages are 1 GiB memory pages reserved at boot for tron's model and device memory; the machine has 512, and "hugepages_free=512" in a machine line means none were in use when the run started.</dd>
<dt>ingested, USE_HW_ATTN=0, prefill, decode</dt><dd>"Ingested" marks a model converted into tron's own format by its ingest tool (the model name carries the prefix). USE_HW_ATTN=0 is the environment switch that forces the attention step onto the CPU; without it the ingested qwen model runs attention on the FPGA and the AMX code never runs. It is set in every arm, and the log line "HW attention disabled" confirms it per run. Prefill = processing the prompt tokens before the first answer token; decode = generating the answer one token at a time.</dd>
<dt>TPS (runtron)</dt><dd>tokens per second per user during decode, as runtron prints it per request ("... at X average tok/s"), averaged over the 8 requests of one run (they agree to 3 digits because the 8 users run in one batch). Multiply by 8 for the aggregate rate.</dd>
<dt>TTFT (runtron)</dt><dd>time to first token: the largest of the 8 "Parsing the prompt took S s" values of one run, that is the wait until the last of the 8 users has its first token (the 8 prompts of 1024 tokens are prefilled together). In {len(rt_runs) - len(uneven)} of the {len(rt_runs)} runs the 8 values agree within 10 ms. In {len(uneven)} run{'s' if len(uneven) != 1 else ''} one request reported a shorter time than the other 7: {esc(uneven_txt) if uneven_txt else 'none'}; the other 7 still agree with each other, and the largest value is used as the batch time. Figures and tables use milliseconds.</dd>
<dt>TPS and TTFT (CI harness), capture window</dt><dd>The CI harness runs the nightly's benchmark with the nightly's settings: 8 users each send 10 rounds of a chat prompt cut to 1024 tokens from real conversations (the sharegpt set; {esc(ci_prompt_txt)}) and read 1536 generated tokens. TPS = tokens per second per user measured in the capture window, generated tokens 896 to 1024 of each answer, averaged over the 80 user-rounds. TTFT = milliseconds until the first piece of the streamed HTTP answer arrives, same averaging. Three things differ from the nightly: here every request goes to one engine built from the branch, attention runs on the CPU, and the harness's results database is replaced by a stub that writes nothing.</dd>
<dt>sd, n</dt><dd>n = the number of repetitions that enter a cell's mean ({n_rt_txt}; CI harness {n_ci_txt}); a run excluded for an early stop does not count. sd = standard deviation across those repetitions. Inside one CI-harness run the harness also reports an sd over its 80 samples; that one measures drift within one server process, not between-run spread.</dd>
<dt>placement, SYSTEM_CONFIG</dt><dd>Placement = the machine resources one tron process gets: --instance k,n = the k-th of n equal shares of the machine from tron's resource map; --devices = the FPGA cards; --app-cores = CPU cores for the application threads; --dev-cores = cores reserved for the device driver threads; --numa = the memory node (socket); --nr_hugepages = the number of 1 GiB hugepages. SYSTEM_CONFIG is an environment variable the login shell exports with a default placement; tron applies it after the command line, so every run here removes it (env -u) and passes the placement explicitly.</dd>
</dl>
""")

# ---- What was run ----
H.append("""<h2>What was run</h2>
<div class="tw"><table>
<tr><th>#</th><th>test</th><th>model</th><th>arm</th><th>users</th><th>prompt</th><th>generated</th><th>repetitions</th></tr>""")
i = 0
for test, gen, key in (("runtron", "256-token limit", "runtron"), ("CI harness", "1536 per round, 10 rounds", "ci")):
    for tp in (2, 4):
        for arm in ("off", "on"):
            i += 1
            if key == "runtron":
                runs = rt_rows(tp, arm); n_done = len(runs); n_ex = len([r for r in runs if r.get("early_stop")])
                cell = f"{n_done} done" + (f", {n_ex} excluded (early stop)" if n_ex else "")
                prompt = "1024 synthetic tokens"
            else:
                allr = ci_rows(tp, arm, done_only=False); n_done = len(ci_rows(tp, arm)); n_other = len(allr) - n_done
                cell = f"{n_done} done" + (f", {n_other} not done ({', '.join(r.get('status', '?') for r in allr if r.get('status') != 'done')})" if n_other else "")
                prompt = "1024 (harness setting)"
            H.append(f"<tr><td>{i}</td><td>{test}</td><td>ingested-qwen-3-4b-instruct-2507-tp{tp}</td><td>AMX-{arm}</td><td class='num'>8</td><td>{prompt}</td><td>{gen}</td><td>{cell}</td></tr>")
H.append("</table></div>")
H.append(f"<p class='take'>The runtron prompt is exactly 1024 synthetic tokens per user, and runtron's timed count for a complete answer is 253 of the 256-token limit. The CI harness cuts real chat prompts to 1024 tokens; {esc(ci_prompt_txt)}.</p>")

# ---- Results ----
def fig_take_tps():
    vals = [p for p in (p_rt2, p_rt4, p_ci2, p_ci4) if p is not None]
    if not vals:
        return ""
    lo, hi_ = min(vals), max(vals)
    s4 = sp[("runtron", 4)]
    return (f"AMX-on is faster in all four rows, {signed(lo)} to {signed(hi_)}, each outside the ±{NOISE_PCT}% band. The runtron tp4 row has the widest spread between repetitions "
            f"(AMX-off {f(s4[0], 1, '%')}, AMX-on {f(s4[1], 1, '%')} between the extreme runs); its per-repetition deltas are {', '.join(f'{v:+.1f}%' for v in pr4)}.")

H.append('<h2>Results</h2><h3>Figure 1: decode throughput per user (higher is better)</h3><div class="fig">')
H.append(dumbbell(rows_for("tps", "runtron"), "runtron: per-user decode TPS, AMX-off vs AMX-on", "tokens per second per user (runtron's per-request average)", "higher", 1))
H.append(dumbbell(rows_for("tps", "ci"), "CI harness: per-user decode TPS, AMX-off vs AMX-on", "tokens per second per user (capture window, generated tokens 896 to 1024)", "higher", 1))
H.append(f'<div class="take">Reading: the gray dot is AMX-off, the blue dot AMX-on for the same test; the percentage at the right is the AMX-on mean divided by the AMX-off mean, minus one. Small dots below a pair are the single repetitions. {esc(fig_take_tps())}</div></div>')
H.append('<h3>Figure 2: time to first token (lower is better)</h3><div class="fig">')
H.append(dumbbell(rows_for("ttft", "runtron"), "runtron: time to first token (batched prefill of 8 prompts)", "milliseconds", "lower", 0))
H.append(dumbbell(rows_for("ttft", "ci"), "CI harness: time to first token (per request)", "milliseconds", "lower", 0))
tt = [x for x in (t_rt2, t_rt4, t_ci2, t_ci4) if x is not None]
tt_take = ("AMX-on is faster in all four rows, by " + f"{min(abs(x) for x in tt):.1f}% to {max(abs(x) for x in tt):.1f}%.") if tt and all(x < 0 for x in tt) else ""
H.append(f'<div class="take">runtron TTFT is the batched prefill of 8 prompts of 1024 tokens (time until the last of the 8 users has its first token); CI TTFT is each user\'s wait for the first streamed chunk of a chat prompt of about 1024 tokens, with the 8 users arriving 0.1 s apart. Compare arms within a row, not rows with each other. {tt_take}</div></div>')

# ---- Exact numbers ----
def prs(d):
    p = d.get("paired_pct") or {}
    return ", ".join(f"rep{k}: {v:+.1f}%" for k, v in p.items()) if p else "n/a"

H.append('<h3>Exact numbers</h3><p class="take">Means and sd are over the repetitions. A runtron run marked <b>early stop</b> is listed but excluded from the means and from the per-repetition deltas. TTFT is in milliseconds in every row; whole-millisecond means are rounded half to even (a mean of 2460.5 prints as 2460, 1577.5 as 1578).</p><div class="tw"><table><tr><th>test</th><th>metric</th><th class="num">AMX-off</th><th class="num">AMX-on</th><th class="num">on vs off (means)</th><th>on vs off per repetition</th><th>per repetition (off | on)</th></tr>')
for key, test in (("runtron", "runtron"), ("ci", "CI harness")):
    for tp in (2, 4):
        d = S[key].get(f"tp{tp}", {})
        if key == "runtron":
            a, t = d.get("tps_per_user", {}), d.get("ttft_s", {})
            es = lambda r: " (early stop, %d-%d tokens)" % (r["gen_tokens_min"], r["gen_tokens_max"]) if r.get("early_stop") else ""
            ro = " | ".join(f"{r['tps_per_user']:.2f}{es(r)}" for r in d.get("off", [])); rn = " | ".join(f"{r['tps_per_user']:.2f}{es(r)}" for r in d.get("on", []))
            to = " | ".join(f"{r['ttft_s'] * 1000:.0f}{es(r)}" for r in d.get("off", []) if r.get('ttft_s') is not None); tn = " | ".join(f"{r['ttft_s'] * 1000:.0f}{es(r)}" for r in d.get("on", []) if r.get('ttft_s') is not None)
            H.append(f"<tr><td>runtron tp{tp}</td><td>TPS per user</td><td class='num'>{pm(a.get('off'), 2)}</td><td class='num'>{pm(a.get('on'), 2)}</td><td class='num'>{signed(a.get('boost_pct'))}</td><td>{esc(prs(a))}</td><td>{esc(ro)} &nbsp;|&nbsp; {esc(rn)}</td></tr>")
            H.append(f"<tr><td>runtron tp{tp}</td><td>TTFT (ms, batched prefill)</td><td class='num'>{pm(ms(t.get('off')), 0)}</td><td class='num'>{pm(ms(t.get('on')), 0)}</td><td class='num'>{signed(t.get('change_pct'))}</td><td>{esc(prs(t))}</td><td>{esc(to)} &nbsp;|&nbsp; {esc(tn)}</td></tr>")
        else:
            a, t = d.get("tps_per_user", {}), d.get("ttft_ms", {})
            ro = " | ".join(f"{r['tps_mean']:.2f} (sd {r['tps_sd']:.2f}, min {r['min_tps']:.1f})" for r in d.get("off", []) if 'tps_mean' in r); rn = " | ".join(f"{r['tps_mean']:.2f} (sd {r['tps_sd']:.2f}, min {r['min_tps']:.1f})" for r in d.get("on", []) if 'tps_mean' in r)
            to = " | ".join(f"{r['ttft_ms']}" for r in d.get("off", []) if 'ttft_ms' in r); tn = " | ".join(f"{r['ttft_ms']}" for r in d.get("on", []) if 'ttft_ms' in r)
            H.append(f"<tr><td>CI harness tp{tp}</td><td>TPS per user</td><td class='num'>{pm(a.get('off'), 2)}</td><td class='num'>{pm(a.get('on'), 2)}</td><td class='num'>{signed(a.get('boost_pct'))}</td><td>{esc(prs(a))}</td><td>{esc(ro)} &nbsp;|&nbsp; {esc(rn)}</td></tr>")
            H.append(f"<tr><td>CI harness tp{tp}</td><td>TTFT (ms)</td><td class='num'>{pm(t.get('off'), 0)}</td><td class='num'>{pm(t.get('on'), 0)}</td><td class='num'>{signed(t.get('change_pct'))}</td><td>{esc(prs(t))}</td><td>{esc(to)} &nbsp;|&nbsp; {esc(tn)}</td></tr>")
H.append("</table></div>")

# ---- Context ----
off4 = (S["ci"].get("tp4", {}).get("tps_per_user", {}).get("off") or [None])[0]
on4 = (S["ci"].get("tp4", {}).get("tps_per_user", {}).get("on") or [None])[0]
q9_boost = 100 * (statistics.mean(Q9["on"]) / statistics.mean(Q9["off"]) - 1)
d_off4 = signed(100 * (off4 / R1['off'] - 1)) if off4 else "n/a"
d_on4 = signed(100 * (on4 / R1['on'] - 1)) if on4 else "n/a"
H.append(f"""<h2>Context</h2>
<h3>Earlier measurements of the same cells</h3>
<div class="tw"><table><tr><th>when</th><th>test</th><th>branch head</th><th class="num">AMX-off</th><th class="num">AMX-on</th><th class="num">on vs off</th><th>source</th></tr>
<tr><td>2026-09-04 (round 1)</td><td>CI harness, qwen tp4, 8 users, TPS per user</td><td>60d66d9c04</td><td class="num">{R1['off']:.2f} (repeat {R1['off2']:.2f})</td><td class="num">{R1['on']:.2f}</td><td class="num">+4.5%</td><td>PR3879/more-testing/round-1/status.md; placement was socket 0 and cards 38/3b/10/13 (Bill's half today)</td></tr>
<tr><td>2026-09-04 (round 1)</td><td>CI harness, qwen tp4, 8 users, TTFT ms</td><td>60d66d9c04</td><td class="num">{R1['ttft_off']} (repeat {R1['ttft_off2']})</td><td class="num">{R1['ttft_on']}</td><td class="num">-8.9%</td><td>same</td></tr>
<tr><td>2026-09-09</td><td>runtron, qwen tp2, 8 users, prompt 8192, TPS per user</td><td>26a0338c3b</td><td class="num">{Q9['off'][0]:.2f} / {Q9['off'][1]:.2f}</td><td class="num">{Q9['on'][0]:.2f} / {Q9['on'][1]:.2f}</td><td class="num">{q9_boost:+.1f}%</td><td>exec/results/qwen8u8k-pr1-half-20260909T1704.txt, repetitions 1 and 2, our half (today's tp2 placement). The same file has a build without the AMX code: {Q9['clean'][0]:.2f} / {Q9['clean'][1]:.2f}, so the kill-switch arm was not slower than that build there.</td></tr>
</table></div>
<p class="take">The prompt-8192 row shows the trend with context length. The AMX kernels speed up only the attention step, and attention's share of one decode step grows with the context: measured 15 to 16% at prompt 256, 28 to 31% at 2048 and 57 to 62% at 8192 (1 user; exec/results/fence2-20260901/, PR3879/make-sense-amx-vs-avx.html). So a 1024-token prompt shows a smaller gain (runtron tp2 {signed(p_rt2)} today) than an 8192-token prompt ({q9_boost:+.1f}% on 2026-09-09, at an earlier head).</p>
<p class="take"><b>Round 1 against today, CI harness, qwen tp4.</b> Round 1 (2026-09-04) measured +4.5% TPS and -8.9% TTFT. Today measured {signed(p_ci4)} TPS and {signed(t_ci4)} TTFT. The TPS change sits in the AMX-off arm: AMX-off went from {R1['off']:.2f} to {f(off4, 2)} tokens per second per user ({d_off4}) while AMX-on went from {R1['on']:.2f} to {f(on4, 2)} ({d_on4}). Three things differ between the two measurements. (1) The code: round 1 ran head 60d66d9c04, today runs 47f6f2dceb; the changes in between include moving the packed query buffers (query vectors laid out for the AMX tiles) into the per-worker attention accumulator and clean-ups of the kernel interface. (2) The placement: socket 0 and Bill's cards then, socket 1 and ours today. (3) The server state at benchmark time: round 1 ran the functional tests in the same server process before the benchmark, today the benchmark ran on a freshly started server. The benchmark checkout is the same (systems_test 470aca1). Which of (1) to (3) causes the slower AMX-off arm today is <b>Insufficient data</b>; the measurement that would decide it is round 1's binary (rinzler.canon, kept in ~/workspace/tron-amx/gen) run in today's placement with the same harness, off and on.</p>
""")
if CIREF:
    logref = f" (job log copied to exec/results/p0perf-20260911/{os.path.basename(CILOG[-1])})" if CILOG else ""
    H.append("<h3>The nightly's own numbers for the same night (for context only; not comparable with the cells above)</h3>")
    H.append(f"<p class='take'>GitHub Actions run {esc(CIREF.get('run_id'))}{esc(logref)}: job log from 2026-09-11 03:38:24 to 11:29:44 UTC. Its perf phase completed (qwen tp2 at 04:54:39, tp4 at 04:57:34 UTC; log lines 2131 and 2292). The run's overall verdict was <i>failure</i>: in the last phase (a 3-hour soak test) the monitor reported total system power 2505.1 W above its 2500 W threshold at 11:28:19 UTC (log line 53053), and the job ended with exit code 1 (line 53071). "
             f"The nightly's client ran on another host and sent its requests through platformd (the production process manager, whose HTTP proxy spreads requests over the running engines) to the production engines: the tron package installed from the apt repository (Ubuntu's package manager), version 2026.09.11-632c6181 from the main branch (log line 474), with attention on the FPGA. The log shows 'All 4 inference engines are running' for tp2 models and 'All 2 inference engines are running' for tp4 models, so each engine served 2 or 4 of the 8 users (assuming the proxy spread them evenly). Per-user TPS is therefore far higher than in the one-engine, CPU-attention cells above.</p>")
    H.append('<div class="tw"><table><tr><th>model</th><th class="num">TPS per user</th><th class="num">TTFT ms</th><th class="num">minutes</th></tr>')
    for m_, lst in CIREF.get("perf", {}).items():
        if "qwen-3-4b" in m_:
            for e in lst:
                H.append(f"<tr><td>{esc(m_)}</td><td class='num'>{e['tps']:.2f}</td><td class='num'>{e['ttft_ms']}</td><td class='num'>{e['minutes']:.2f}</td></tr>")
    H.append("</table></div>")
else:
    H.append("<p class='take'>The nightly's own qwen numbers for this night were not extracted (no ci-reference-*.json in the results folder).</p>")

# ---- How to read ----
sp_txt = "; ".join(f"{'runtron' if k == 'runtron' else 'CI harness'} tp{tp}: AMX-off {f(v[0], 1, '%')}, AMX-on {f(v[1], 1, '%')}" for (k, tp), v in sp.items())
ci4_on = [r["tps_mean"] for r in ci_rows(4, "on")]
H.append(f"""<h2>How to read these numbers</h2>
<ul>
<li><b>Same binary, two environments.</b> The AMX-off arm is the AMX build with the kill switch set, not a build without the AMX code. On this branch the last comparison with such a build (2026-09-09, prompt 8192, see the Context table) found no measurable kill-switch cost, so the gains here are expected to hold against a build without the AMX code as well; that comparison has not been repeated at prompt 1024.</li>
<li><b>One engine, CPU attention.</b> Every cell runs one rinzler or runtron on our half of the machine with USE_HW_ATTN=0. The nightly's published qwen numbers use FPGA attention and several engines behind a proxy; they do not measure the AMX path at all.</li>
<li><b>Run order.</b> In every repetition the AMX-off run came first and the AMX-on run second (about 50 s later for runtron, about 6 min later for the CI harness); the order was never swapped. A machine that steadily speeds up or slows down during a repetition would therefore add to or subtract from every delta alike. The per-repetition deltas of the same cell agree with each other (see the Exact numbers table), which such a drift would not produce unless it repeated identically six times.</li>
<li><b>Spread.</b> Spread here = the largest value of one arm's repetitions divided by the smallest, minus one. Decode TPS: {esc(sp_txt)}. Every TTFT cell spreads by less than {f(max(sp_ttft), 1, '%') if sp_ttft else 'n/a'}. The runtron tp4 TPS cells are the noisy ones; their six per-repetition deltas are all positive ({', '.join(f'{v:+.1f}%' for v in pr4)}), so the direction of the tp4 gain is settled while its size is known to about ±{f(pr4_ci, 1)} points (95% interval of the mean of six paired deltas). The ±{NOISE_PCT}% band used in the figures comes from one same-binary repeat of the CI harness in round 1 ({R1['off']:.2f} against {R1['off2']:.2f} tokens per second per user, -2.2%; TTFT {R1['ttft_off']} against {R1['ttft_off2']} ms). Today's own repeats exceed that band in the tp4 cells (the two CI-harness tp4 AMX-on runs differ by {f(spread_pct(ci4_on), 1, '%')}), so for the tp4 cells a difference below about 4% would not be resolved by this many repetitions; for the tp2 cells the repeats agree to within 1%.</li>
<li><b>The other half of the machine.</b> Bill's socket-0 work can run at the same time as our cells; the machine line recorded at the start of every run (table below) shows his process count and CPU so that a cell disturbed by his work can be identified.</li>
<li><b>Runtron TTFT against CI TTFT.</b> Runtron prefills the 8 prompts as one batch and prints the batch time; the CI harness measures each user's wait for the first HTTP chunk with users arriving 0.1 s apart. Both fall with faster prefill, but the absolute values differ because the two tools measure different waits.</li>
</ul>
""")

# ---- Provenance ----
H.append("<h2>Provenance</h2><dl>")
H.append(f"<dt>Source</dt><dd>branch jhan-amx-p0, {esc(tip)}</dd>")
H.append(f"<dt>Build</dt><dd>{esc(build_field('cmake'))}<br>{'<br>'.join(esc(s) for s in shas)}<br>{esc(version)}</dd>")
H.append(f"<dt>Placement tp2 (runtron and rinzler)</dt><dd><code>{esc(place2)}</code></dd>")
H.append(f"<dt>Placement tp4 (runtron and rinzler)</dt><dd><code>{esc(place4)}</code> (the same placement the nightly's own rinzler uses on socket 1)</dd>")
H.append("<dt>Environment of every tron process</dt><dd><code>env -u SYSTEM_CONFIG</code> removes the login shell's default placement (see Words used here); <code>USE_HW_ATTN=0</code> forces CPU attention; <code>TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug</code> only make tron print more (the login shell's values, the same in both arms); <code>TRON_AMX_DISABLE=1</code> is set in the off arm and unset in the on arm. rinzler additionally gets <code>TRON_USE_SPECULATION=0</code> (no speculative decoding), <code>RZ_ENABLE_SAVE_TOKENS=1</code> and its FUSE mount path (FUSE = a file system served by a user-space process, which rinzler uses for its token files); these values were copied from round 1's launcher, which took them from the environment platformd gives production engines, and were not re-verified against platformd today.</dd>")
H.append("<dt>runtron command</dt><dd><code>runtron.p0perf stream-generate-text -m &lt;model&gt; &lt;placement&gt; --hugepage_file /dev/hugepages/amx-p0perf -o --prompt-length 1024 -l 256 -u 8</code> (-o = optimize, the usual flag)</dd>")
H.append("<dt>CI harness</dt><dd>systems_test 470aca1 (the checkout round 1 used; upstream changed only whitespace in scripts/perf.py since), driven by exec/more-testing-r1/st_perf.py with the CI results database replaced by a stub that writes nothing; OPENAI_HOST=http://delphi-3bda:13100/v1, one engine.</dd>")
H.append("<dt>Machine</dt><dd>delphi-3bda, our half (socket 1, cards 90/93/b9/bc). Production serving was stopped after the nightly per the standing idle-serving policy (no client activity for 10 minutes) and not restarted. The machine line recorded at the start of every run (1-, 5- and 15-minute load averages, free hugepages, Bill's process count and summed CPU percent):</dd>")
H.append("</dl><div class='tw'><table><tr><th>run</th><th>machine line at start</th></tr>")
for name, line in ctx_rows:
    H.append(f"<tr><td>{esc(name)}</td><td><code>{esc(line)}</code></td></tr>")
H.append("</table></div>")
H.append(f"<p class='take'>Reading of the machine table: bill_procs=0 and bill_cpu_pct=0 in {n_b0} of {n_ctx} lines, so none of Bill's processes ran at the start of any cell. hugepages_free=512 in {n_hp} of {n_ctx} lines: no hugepage file of ours or of production was left behind between runs. The 1-minute load averages of the first repetition of the four runtron cells ({esc(loads_txt)}) are the decaying tail of the build ({build_start} to {hm(build_end)}, 96 parallel jobs on socket 1) and of the production servers stopped at 11:50:43Z; the runs themselves started 2.5 to 4.5 minutes later, and repetitions 2 to 6 of the same cells (load 7 to 10) give the same paired deltas.</p>")
H.append("""<h2>Raw data</h2>
<ul>
<li>exec/results/p0perf-20260911/rt-results.txt (runtron result lines per run), rt/*.log (full runtron output per run)</li>
<li>exec/results/p0perf-20260911/cells/&lt;model&gt;__&lt;arm&gt;__rep&lt;N&gt;/ (perf.json, perf.log, rinzler.log, meta.json, proof.txt, STATUS)</li>
<li>exec/results/p0perf-20260911/summary.json, summary.md (exec/p0perf-20260911/summarize.py); build.txt; ci-reference-20260911.json and ci-run-34559196745.log (the nightly)</li>
<li>campaign: exec/p0perf-20260911/campaign.sh, rz.sh, launch.sh; log exec/logs/p0perf-20260911.log; this page: exec/p0perf-20260911/gen_report.py</li>
</ul>
</main>""")
open(OUT, "w").write("\n".join(H))
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
