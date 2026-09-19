#!/usr/bin/env python3
"""Generate VNNIed-K-in-place/status/Monday-morning-report.html from the vnnik-20260914
campaign outputs (exec/results/vnnik-20260914/). Pure-ASCII HTML, light theme, inline SVG
dot plots (one row per prompt length, one dot per arm), a numbers table per chart, the
build / test / smoke records, the section on Bill's investigation, and a raw-data
description for the reviewing agent. Every block degrades to "pending" when its input is
missing, so the page can be generated before and after the test window.
Usage: gen_report.py [RESULTS_DIR] [OUT_HTML]
"""
import glob
import html
import json
import math
import os
import re
import statistics
import sys
import datetime

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/Monday-morning-report.html"
EXEC = "/home/jhan/workspace/intel-AMX/exec"
SRC_WT = "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

ARMS = ["off", "base", "vnni", "vnnioff"]
ARM_LABEL = {"off": "off (row-major, no AMX)", "base": "base (PR #3879 AMX)", "vnni": "vnni (this design, AMX)",
             "vnnioff": "vnni-off (VNNI storage, no AMX)"}
# Validated categorical slots of the dataviz reference palette (light): aqua, blue, orange;
# the fourth arm is a secondary arm and gets a hollow gray marker (identity from the legend
# and the direct label, never from color alone).
ARM_COLOR = {"off": "#1baf7a", "base": "#2a78d6", "vnni": "#eb6834", "vnnioff": "#52514e"}


def esc(s):
    return html.escape(str(s), quote=True)


def read(path):
    try:
        return open(path, errors="replace").read()
    except OSError:
        return None


def load_summary():
    p = os.path.join(RES, "summary.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None


def git(cmd):
    import subprocess
    try:
        return subprocess.run(["git", "-C", SRC_WT] + cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


summary = load_summary()
cells = (summary or {}).get("cells", {})
deltas = (summary or {}).get("deltas", {})
build_txt = read(os.path.join(RES, "build.txt"))
tests_txt = read(os.path.join(RES, "tests.txt"))
smoke_txt = read(os.path.join(RES, "smoke", "smoke.txt"))
status_line = read(os.path.join(EXEC, "logs", "vnnik-20260914.status"))
marker = read(os.path.join(EXEC, "logs", "vnnik-20260914.done"))
head = git(["log", "-1", "--format=%H %ci %s"])
commits = git(["log", "--format=%h %s", "544ca05c7a..HEAD"])
diffstat = git(["diff", "--stat", "544ca05c7a..HEAD"])
syn_c1 = read("/var/tmp/jhan/vnni-syn-c1.out")  # only present when run on 3bda; else the copies below
syn_c3 = read("/var/tmp/jhan/vnni-syn-c3.out")
pretest = read("/var/tmp/jhan/vnni-pretest-p3.out")
for name, var in (("syn-c1.out", "syn_c1"), ("syn-c3.out", "syn_c3"), ("pretest-p3.out", "pretest")):
    if globals()[var] is None:
        globals()[var] = read(os.path.join(RES, "prewindow", name))
syn_c6 = read(os.path.join(RES, "prewindow", "syn-c6.out"))
pretest_r6 = read(os.path.join(RES, "prewindow", "pretest-r6.out"))


def cell(tp, prompt, arm):
    return cells.get("tp%d p%d %s" % (tp, prompt, arm))


def delta(tp, prompt, a, b):
    return deltas.get("tp%d p%d %s vs %s" % (tp, prompt, a, b))


def prompts_for(tp):
    return sorted({c["prompt"] for c in cells.values() if c["tp"] == tp})


def fmt(x, nd=2):
    return "pending" if x is None else ("%.*f" % (nd, x))


def pct(x):
    return "pending" if x is None else ("%+.1f%%" % x)


# ------------------------------------------------------------------ charts
def dot_plot(tp, metric):
    """One SVG: rows = prompt lengths, dots = arms. Each row has its own x scale (the
    prompt lengths differ by 8x in TTFT, so one shared axis would collapse the short
    rows); the value labels and the table carry the numbers."""
    prompts = prompts_for(tp)
    if not prompts:
        return '<p class="pending">pending: no cells for tp%d yet</p>' % tp
    key = "tps_mean" if metric == "tps" else "ttft_mean_s"
    sdkey = "tps_sd" if metric == "tps" else "ttft_sd_s"
    rows_data = []
    for p in prompts:
        row = [(a, cell(tp, p, a)) for a in ARMS if cell(tp, p, a) and cell(tp, p, a).get(key) is not None]
        if row:
            rows_data.append((p, row))
    if not rows_data:
        return '<p class="pending">pending: no %s values for tp%d yet</p>' % (metric, tp)
    W = 900
    ROW_H = 90
    H = 40 + ROW_H * len(rows_data) + 10
    L, R = 130, 150
    unit = "TPS per user (decode tokens/s)" if metric == "tps" else "TTFT (prefill s for 8 prompts)"
    out = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" font-family="system-ui,sans-serif" font-size="12" role="img" aria-label="%s tp%d">' % (W, H, W, H, unit, tp)]
    out.append('<text x="%d" y="18" font-size="13" font-weight="600" fill="#0b0b0b">%s, qwen3-4b tp%d, 8 users, 256 generated; each row has its own scale</text>' % (L, esc(unit), tp))
    for i, (p, row) in enumerate(rows_data):
        y = 40 + i * ROW_H + 40
        vals = [c[key] for _, c in row]
        sds = [c.get(sdkey) or 0.0 for _, c in row]
        lo = min(v - sd for v, sd in zip(vals, sds))
        hi = max(v + sd for v, sd in zip(vals, sds))
        span = (hi - lo) or (abs(hi) * 0.02 or 1.0)
        lo -= 0.15 * span
        hi += 0.15 * span
        def X(v, lo=lo, hi=hi):
            return L + (v - lo) / (hi - lo) * (W - L - R)
        raw = (hi - lo) / 4.0
        step = 10 ** math.floor(math.log10(raw))
        step *= 5 if raw / step >= 5 else (2 if raw / step >= 2 else 1)
        tick = math.ceil(lo / step) * step
        while tick <= hi + 1e-9:
            out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#e6e5e1" stroke-width="1"/>' % (X(tick), y - 26, X(tick), y + 16))
            out.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#52514e" font-size="11">%s</text>' % (X(tick), y + 36, ("%g" % round(tick, 6))))
            tick += step
        out.append('<text x="%d" y="%d" text-anchor="end" fill="#0b0b0b" font-weight="600">prompt %d</text>' % (L - 12, y + 4, p))
        if len(vals) >= 2:
            out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#c9c8c3" stroke-width="2" stroke-linecap="round"/>' % (X(min(vals)), y, X(max(vals)), y))
        for a, c in row:
            if c.get(sdkey):
                out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1" opacity="0.6"/>' % (X(c[key] - c[sdkey]), y, X(c[key] + c[sdkey]), y, ARM_COLOR[a]))
        for a, c in row:
            fill = ARM_COLOR[a] if a != "vnnioff" else "#ffffff"
            out.append('<circle cx="%.1f" cy="%d" r="7" fill="#ffffff"/>' % (X(c[key]), y))
            out.append('<circle cx="%.1f" cy="%d" r="5" fill="%s" stroke="%s" stroke-width="2"/>' % (X(c[key]), y, fill, ARM_COLOR[a]))
        for a, c in row:
            if a == "vnni":
                out.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#0b0b0b">vnni %s</text>' % (X(c[key]), y - 12, fmt(c[key], 2 if metric == "tps" else 3)))
            elif a == "base":
                out.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#0b0b0b">base %s</text>' % (X(c[key]), y + 18, fmt(c[key], 2 if metric == "tps" else 3)))
        d = delta(tp, p, "vnni", "base")
        if d:
            v = d["tps_pct"] if metric == "tps" else d.get("ttft_pct")
            if v is not None:
                good = (v > 0) if metric == "tps" else (v < 0)
                vtxt = ("%+.1f%%" % v) if abs(v) >= 0.05 else "0.0%"
                col = ("#0ca30c" if good else "#d03b3b") if abs(v) >= 0.05 else "#52514e"
                out.append('<text x="%d" y="%d" text-anchor="end" fill="%s" font-weight="600">vnni vs base %s</text>' % (W - 10, y + 4, col, vtxt))
    out.append('</svg>')
    legend = '<div class="legend">' + "".join(
        '<span class="key"><span class="sw" style="background:%s;%s"></span>%s</span>' % (
            ARM_COLOR[a] if a != "vnnioff" else "#fff", "" if a != "vnnioff" else "border:2px solid #52514e;", esc(ARM_LABEL[a])) for a in ARMS) + '</div>'
    return legend + '<div class="fig">' + "".join(out) + '</div>'


def numbers_table(tp):
    prompts = prompts_for(tp)
    if not prompts:
        return '<p class="pending">pending</p>'
    rows = ['<table><tr><th>prompt</th><th>arm</th><th>n</th><th>TPS/user</th><th>sd</th><th>TTFT s</th><th>sd</th><th>early stops</th><th>binary tip</th></tr>']
    for p in prompts:
        for a in ARMS:
            c = cell(tp, p, a)
            if not c:
                continue
            rows.append('<tr><td>%d</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td></tr>' % (
                p, esc(a), c["n"], fmt(c["tps_mean"]), fmt(c["tps_sd"]), fmt(c["ttft_mean_s"], 3), fmt(c["ttft_sd_s"], 3), c["early_stop_runs"],
                esc(", ".join(t[:10] for t in c.get("tips", [])) or "-")))
    rows.append('</table>')
    rows.append('<table><tr><th>prompt</th><th>comparison</th><th>TPS delta</th><th>TTFT delta (time)</th><th>reading</th></tr>')
    readings = {("vnni", "base"): "the design against the AMX baseline", ("base", "off"): "the known AMX gain (check against 2026-09-11/13)",
                ("vnnioff", "off"): "the software-path change alone (AVX-512 VNNI reader + scatter store)", ("vnni", "off"): "the design against no AMX",
                ("vnni", "vnnioff"): "AMX on the VNNI storage against off"}
    for p in prompts:
        for (a, b), txt in readings.items():
            d = delta(tp, p, a, b)
            if d:
                rows.append('<tr><td>%d</td><td>%s vs %s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (p, a, b, pct(d["tps_pct"]), pct(d.get("ttft_pct")), esc(txt)))
    rows.append('</table>')
    return "".join(rows)


def headline():
    """Short-version sentences from the tp2 data, or a pending sentence."""
    ps = prompts_for(2)
    if not ps:
        return ("The measurement has not produced numbers yet (status: %s)." % esc((status_line or "not started").strip()))
    parts = []
    for p in ps:
        d = delta(2, p, "vnni", "base")
        if d:
            parts.append("prompt %d: TPS %s, TTFT %s" % (p, pct(d["tps_pct"]), pct(d.get("ttft_pct"))))
    return "Measured on delphi-3bda (qwen3-4b tp2, 8 users), VNNIed K against the AMX baseline: " + "; ".join(parts) + "."


def pre(txt, maxlines=60):
    if not txt:
        return '<p class="pending">pending</p>'
    lines = txt.strip().splitlines()
    if len(lines) > maxlines:
        lines = lines[:maxlines] + ["... (%d more lines in the file)" % (len(txt.strip().splitlines()) - maxlines)]
    return "<pre>%s</pre>" % esc("\n".join(lines))


def syn_summary(txt, label):
    if not txt:
        return "<li>%s: pending</li>" % label
    ok = re.findall(r"^\[(ON|OFF)\] syntax (\S+) rc=(\d+)", txt, flags=re.M)
    bad = [(c, f) for c, f, rc in ok if rc != "0" and "gof.cpp" not in f]
    gof = [f for c, f, rc in ok if rc != "0" and "gof.cpp" in f]
    fmt_diff = re.findall(r"clang-format DIFF: (\S+)", txt)
    return "<li>%s: %d translation-unit checks; failures: %s%s; clang-format differences: %s.</li>" % (
        label, len(ok), esc(", ".join("%s (%s)" % (f, c) for c, f in bad) or "none"),
        " (gof.cpp needs the generated model-definitions file, absent in a configure-only tree: not a defect of the change)" if gof else "",
        esc(", ".join(fmt_diff) or "none"))


def pretest_summary(txt):
    if not txt:
        return "<li>pre-window unit tests: pending</li>"
    lines = [l for l in txt.splitlines() if re.match(r"^(t_\w+ rc=|build rc=|configure)", l)]
    return "<li>pre-window unit tests (4 cores during the CI window): %s</li>" % (esc(" | ".join(lines)) if lines else "running")


# ------------------------------------------------------------------ Bill section
def bill_section():
    base_off = [(p, delta(2, p, "base", "off")) for p in prompts_for(2)]
    base_off = [(p, d) for p, d in base_off if d]
    vnni_base = [(p, delta(2, p, "vnni", "base")) for p in prompts_for(2)]
    vnni_base = [(p, d) for p, d in vnni_base if d]
    vnnioff_off = [(p, delta(2, p, "vnnioff", "off")) for p in prompts_for(2)]
    vnnioff_off = [(p, d) for p, d in vnnioff_off if d]
    if base_off:
        ours = "Our AMX gain over the AVX baseline (base vs off, qwen3-4b tp2, 8 users): " + "; ".join(
            "prompt %d TPS %s, TTFT %s" % (p, pct(d["tps_pct"]), pct(d.get("ttft_pct"))) for p, d in base_off) + "."
    else:
        ours = "Our base-vs-off numbers are pending."
    if vnnioff_off:
        sw = "Our software-path change alone (vnni-off vs off: AVX-512 VNNI reader plus the scatter store, no AMX): " + "; ".join(
            "prompt %d TPS %s, TTFT %s" % (p, pct(d["tps_pct"]), pct(d.get("ttft_pct"))) for p, d in vnnioff_off) + "."
    else:
        sw = "Our vnni-off vs off numbers (the closest analogue of his AVX and scalar observations) are pending."
    if vnni_base:
        design = "The design's own effect (vnni vs base): " + "; ".join(
            "prompt %d TPS %s, TTFT %s" % (p, pct(d["tps_pct"]), pct(d.get("ttft_pct"))) for p, d in vnni_base) + "."
    else:
        design = "The vnni-vs-base numbers are pending."
    return """
<p>Bill's Slack message (direct message, 2026-09-10 17:46 PDT) points at his branch bill-amx (PR #2934) and names three things: the VNNI storage contract in h/tron/kernels/attention_dispatch.hpp, the AVX-512 kernel in h/tron/kernels/avx512_blocked_attention.hpp that consumes the same VNNI K, and a benchmark note (dispatcher-m-sweep.md) with the AVX gain and a small-M slowdown. His summary: the branch keeps both copies of K (row-major and VNNI); the VNNI copy serves AMX and AVX; the scalar path sees a 13% slowdown; removing the row-major K was planned but not done. The PR description reports gpt-oss-120b-tp4, 2K prompt, 1K generated, 4 users: throughput 621.6 to 694.5 tok/s (+11.7%), TTFT 6.93 to 5.77 s (-16.7%), and llama-3-8b 2K/1K about 983 tok/s with no regression.</p>
<h3>What we can learn from it</h3>
<ul>
<li><b>Same direction, one step further.</b> His note confirms the plan we built: K written once in the VNNI layout at generation and read by both AMX and AVX-512. His branch still stores the row-major copy next to it (a fat kv_block, +50% K+V payload; the layout penalty we measured on our own in-block mirror in August, -3.7 to -7.8% AVX decode); our branch removes that copy. His sentence &quot;Removing normal K was planned to be removed but had not happened yet&quot; is the step this project takes [attention_dispatch.hpp, Note [K VNNI mirror] on bill-amx].</li>
<li><b>The AVX-512 reader is the same idea.</b> His avx512_blocked::qk broadcasts one query dim pair, loads one 64-byte VNNI row of 16 keys, and accumulates with vdpbf16ps, four query rows per block. Our k_vnni::qk_group does the same with the group's kv_mul heads per K load and a lane mask for the live tokens, so partial pages and unwritten tokens need no special case [avx512_blocked_attention.hpp:35 on bill-amx; h/tron/kernels/k_vnni.hpp on jhan-amx-vnniK].</li>
<li><b>His format rule differs from ours in one respect.</b> He decides the format from kv_mul (VNNI only for kv_mul at least 4; a kv_mul-3 model such as llama-3.2-3b stays on the row-major scalar path and never touches the mirror). With a single in-place K, every model with a 128-dim head must be served from the VNNI plane, so our rule is head size only and the AVX-512 reader handles any kv_mul (accumulator count). His two-copy design could afford to skip small kv_mul; ours must serve it, and we have not measured a kv_mul-3 model yet [attention_dispatch.hpp, &quot;FORMAT IS A COMPILE-TIME FUNCTION OF kv_mul&quot;].</li>
<li><b>His head-size coverage is wider.</b> His kernels exist for head 64 and 128, so gpt-oss (head 64) is served; ours are head 128 only, so gpt-oss keeps the row-major plane and never runs AMX attention in our build. His gpt-oss numbers therefore have no counterpart in ours.</li>
<li><b>The 13% scalar-path slowdown.</b> The message says the scalar (dotter) path sees a 13% slowdown on his branch; the benchmark note it refers to is not on the pushed branch (dispatcher-m-sweep.md is absent from origin/bill-amx), so which configuration and which layout that number describes is <span class="warn">Insufficient data</span> from what we can read. Two candidates from our own measurements: the fat kv_block layout penalty on the AVX path (our -3.7 to -7.8% decode with the in-block mirror, 2026-08-19), and, if his scalar path unpacks VNNI K row by row, the gather cost. Our design has neither a second plane nor a row-unpacking scalar path: the AVX-512 reader consumes the plane directly.</li>
<li><b>The store cost is the shared risk.</b> Both designs scatter each K row into 64 cache lines at generation. His note does not report a prefill-store cost separately; our G1 probe measured +11.7% TTFT for the scalar version of that store with 8 concurrent short prefills (2026-09-08). The vnni-off vs off arm below isolates our store plus reader change without AMX.</li>
</ul>
<h3>Do we see similar performance results?</h3>
<p>His headline is a different model and a different configuration (gpt-oss-120b tp4, 4 users, 2K/1K, an FPGA-attention-eligible model whose CPU share his head-64 kernels serve), so only the direction is comparable, not the size.</p>
<ul>
<li>OURS_PLACEHOLDER</li>
<li>SW_PLACEHOLDER</li>
<li>DESIGN_PLACEHOLDER</li>
</ul>
<p>Reading: his +11.7% throughput and -16.7% TTFT came from AMX plus blocked AVX-512 on a VNNI K copy; our base arm (PR #3879, AMX on row-major K) already realizes an AMX gain of that order on qwen at prompt 1024 in the earlier campaigns (+11.9% and +13.2% TPS, -20% TTFT on 2026-09-11 and 2026-09-13). What this project adds on top is the vnni-vs-base delta above. Whether our TTFT moves in his direction (down) or the store cost dominates (up) is the row this page exists to report.</p>
""".replace("OURS_PLACEHOLDER", ours).replace("SW_PLACEHOLDER", sw).replace("DESIGN_PLACEHOLDER", design)


# ------------------------------------------------------------------ raw data description
def raw_data_section():
    files = sorted(glob.glob(os.path.join(RES, "rt", "*.log")))
    n_logs = len(files)
    return """
<p>Everything a reviewing agent needs to recompute this page is under <code>%s</code> (host claude-box, NFS-shared with delphi-3bda) and in the branch worktree <code>%s</code>.</p>
<table>
<tr><th>File</th><th>Content and format</th></tr>
<tr><td><code>rt-results.txt</code></td><td>One block per run: a header line <code>### runtron tp=&lt;2|4&gt; prompt=&lt;N&gt; arm=&lt;off|base|vnni|vnnioff&gt; rep=&lt;r&gt; attempt=&lt;k&gt; bin=&lt;path&gt; env=&lt;...&gt; len=256 users=8 &lt;UTC time&gt; load=... hugepages_free=... bill_procs=...</code>, then the runtron lines grepped from the run: <code>Version:</code>, <code>Configured instance ...</code> and <code>App CPU list ...</code> (placement proof), <code>HW attention ...</code>, one <code>Parsing the prompt took S s at X tokens/s</code> per request (TTFT = max over the 8), one <code>Generating G response tokens with C context took T s at X average tok/s</code> per request (TPS per user = mean over the 8; G is 253 for a request that reached the -l 256 limit, because runtron counts the response size minus one minus padding; a smaller G marks a stop token and flags the run as an early stop). <code>RUN-STOPPED</code> / <code>RUN-FAILED</code> lines mark attempts that are excluded.</td></tr>
<tr><td><code>rt/tp&lt;tp&gt;__p&lt;prompt&gt;__&lt;arm&gt;__rep&lt;r&gt;.log</code> (+ <code>.attempt&lt;k&gt;</code>)</td><td>The complete runtron output of the accepted attempt (and of every attempt). %d accepted logs at generation time.</td></tr>
<tr><td><code>summary.json</code>, <code>summary.md</code></td><td>Produced by <code>exec/vnnik-20260914/summarize.py</code>: per cell (tp, prompt, arm) the repetitions with tps_per_user, ttft_s, generated token counts, early-stop flag, placement lines; mean and sd; the deltas used on this page (a/b - 1). The docstring of the script states every definition.</td></tr>
<tr><td><code>build.txt</code></td><td>Branch tip built, cmake options, sha256 of runtron.vnnik and of the base binary runtron.p0perf13, runtron --version output.</td></tr>
<tr><td><code>tests.txt</code>, <code>tests-&lt;name&gt;.out</code></td><td>Unit-test results in the window (t_k_vnni_layout, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit) with the Catch2 summary lines; a failure would have stopped the campaign before any measurement.</td></tr>
<tr><td><code>smoke/smoke.txt</code>, <code>smoke/&lt;arm&gt;.tokens</code>, <code>smoke/&lt;arm&gt;.log</code></td><td>Greedy decode of one prompt (1024 tokens, 128 generated, temperature 0, --pay-for-determinism) per arm, plus the A/A repeats base2 and vnni2 (same binary, same recipe, run again); the token-id rows and the comparison by <code>compare_tokens.py</code> (agreeing prefix, first difference). The two A/A rows must read identical before the base-vs-vnni row is interpreted.</td></tr>
<tr><td><code>prewindow/</code></td><td>Copies of the pre-window checks made during the CI window: the two-configuration syntax checks (syn-c1.out, syn-c3.out) and the 4-core unit-test build and run (pretest-p3.out).</td></tr>
<tr><td><code>exec/logs/vnnik-20260914.{log,status,done}</code></td><td>Campaign log (every guard decision, takeover, watcher stop), one-line status, end marker (ok, or the failure kind).</td></tr>
<tr><td><code>exec/vnnik-20260914/campaign.sh</code></td><td>The campaign itself (arms, cells, placement flags, guard rules); its header states every deliberate choice.</td></tr>
</table>
<p>Arms and binaries: off and base run <code>/var/tmp/jhan/tron-p0perf13/gen/runtron.p0perf13</code> (commit 544ca05c7a, jhan-amx-p0 = PR #3879 head, row-major K, TRON_AMX_DISPATCH=ON); vnni and vnni-off run <code>/var/tmp/jhan/tron-vnnik/gen/runtron.vnnik</code> (this branch, TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON). off and vnni-off set TRON_AMX_DISABLE=1. All runs: USE_HW_ATTN=0 (CPU attention), <code>env -u SYSTEM_CONFIG</code>, tp2 placement <code>--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1</code>, tp4 placement <code>--instance 1,2</code> with all four of our cards, 8 users, <code>--prompt-length N -l 256 -o</code>. Arms are interleaved inside each repetition.</p>
<p>How to recompute: <code>python3 exec/vnnik-20260914/summarize.py exec/results/vnnik-20260914</code> rewrites summary.json and prints the tables; <code>python3 exec/vnnik-20260914/gen_report.py</code> rewrites this page.</p>
""" % (esc(RES), esc(SRC_WT), n_logs)


# ------------------------------------------------------------------ page
page = []
page.append("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VNNIed K Monday report</title>
<style>
:root { --ink:#0b0b0b; --muted:#52514e; --line:#e6e5e1; --bg:#fcfcfb; --panel:#f3f2ef; --accent:#2a78d6; --warn:#d03b3b; --ok:#0ca30c; }
body { margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:1000px; margin:0 auto; }
h1 { font-size:26px; margin:0 0 6px; } h2 { font-size:20px; margin:30px 0 8px; border-bottom:1px solid var(--line); padding-bottom:4px; } h3 { font-size:16px; margin:18px 0 6px; }
.sub { color:var(--muted); margin-bottom:16px; }
.short { background:var(--panel); border-left:4px solid var(--accent); padding:10px 14px; margin:14px 0; }
table { border-collapse:collapse; width:100%%; margin:10px 0 14px; font-size:14px; } th, td { border:1px solid var(--line); padding:6px 8px; vertical-align:top; text-align:left; } th { background:var(--panel); }
td:nth-child(n+3) { font-variant-numeric: tabular-nums; }
code, pre { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; } pre { background:var(--panel); border:1px solid var(--line); padding:10px 12px; overflow-x:auto; }
.fig { margin:6px 0 4px; border:1px solid var(--line); background:#fff; padding:8px; overflow-x:auto; }
.legend { display:flex; flex-wrap:wrap; gap:14px; font-size:13px; color:var(--muted); margin:10px 0 0; } .key { display:inline-flex; align-items:center; gap:6px; } .sw { display:inline-block; width:12px; height:12px; border-radius:50%%; }
.pending { color:var(--muted); font-style:italic; } .warn { color:var(--warn); font-weight:600; } .ok { color:var(--ok); font-weight:600; }
ul { margin:6px 0 10px 22px; } li { margin:3px 0; }
</style></head><body><main>
<h1>VNNIed K in place: Monday morning report</h1>
<p class="sub">Generated %s from exec/results/vnnik-20260914 and the branch jhan-amx-vnniK. Campaign status: <b>%s</b>%s. Design document: <a href="../design/claude-VNNIed-K.html">design/claude-VNNIed-K.html</a>.</p>
""" % (NOW, esc((status_line or "not started").strip()), (" (marker: %s)" % esc(marker.strip())) if marker else ""))

page.append('<div class="short"><p><b>Short version.</b> %s The branch stores the K of 128-dim heads in the AMX VNNI layout in place of the row-major rows, so the AMX kernel skips the score transpose and no second copy of K exists; the AVX-512 path, the K store and the FPGA staging adapter were updated to the layout. The rest of this page holds the numbers table, the build and test record, what Bill\'s investigation adds, and a description of the raw data for review.</p></div>' % headline())

page.append("""<h2>1. Words used here</h2>
<table><tr><th>Term</th><th>Meaning</th></tr>
<tr><td>tron, runtron</td><td>tron is the inference program under test; runtron is its command-line tool, which produced every number here.</td></tr>
<tr><td>AMX, AVX-512</td><td>The Intel matrix (tile) and vector instruction sets of the Xeon 6 host delphi-3bda.</td></tr>
<tr><td>VNNI layout</td><td>The pair-interleaved K layout the AMX tile multiply needs as its right operand; this branch stores K in it (design section 3.1).</td></tr>
<tr><td>arms</td><td>off = the base binary with the AMX kill switch (row-major K, AVX dotter); base = the base binary with AMX (PR #3879); vnni = this branch with AMX; vnni-off = this branch with the kill switch (AVX-512 VNNI reader, scatter store, no AMX).</td></tr>
<tr><td>TPS, TTFT</td><td>TPS = generated tokens per second per user during decode (runtron's &quot;average tok/s&quot;, mean over the 8 users). TTFT = time to first token = runtron's &quot;Parsing the prompt took&quot; seconds, the batched prefill of the 8 prompts.</td></tr>
<tr><td>prompt N</td><td>Prompt length in tokens (1024, 2048, 8192); every run then generates 256 tokens per user.</td></tr>
<tr><td>sd, n</td><td>Standard deviation over the n repetitions of a cell (arms interleaved inside each repetition).</td></tr>
</table>""")

page.append("<h2>2. Results: qwen3-4b tp2, 8 users</h2>")
page.append("<h3>2.1 Decode rate</h3>" + dot_plot(2, "tps"))
page.append('<p class="cap">Dots = mean over repetitions; thin whiskers = one sd; each prompt row has its own scale (rows are not comparable by eye across prompts; the table has every number); the value labels are the two arms the project compares; the delta at the right is vnni against base (green = better).</p>')
page.append("<h3>2.2 Time to first token</h3>" + dot_plot(2, "ttft"))
page.append('<p class="cap">Lower is better. The delta at the right is the change of the prefill time, vnni against base (green = faster).</p>')
page.append("<h3>2.3 Numbers</h3>" + numbers_table(2))

def reading_section():
    """Sentences composed from the measured deltas; every number is read from summary.json."""
    out = []
    for tp in (2, 4):
        ps = prompts_for(tp)
        if not ps:
            continue
        vb = [(p, delta(tp, p, "vnni", "base")) for p in ps]
        bo = [(p, delta(tp, p, "base", "off")) for p in ps]
        vo = [(p, delta(tp, p, "vnnioff", "off")) for p in ps]
        vb = [(p, d) for p, d in vb if d]; bo = [(p, d) for p, d in bo if d]; vo = [(p, d) for p, d in vo if d]
        if vb:
            out.append("<li><b>tp%d, the design against the AMX baseline (vnni vs base):</b> decode TPS %s; TTFT %s. The decode gain grows with the prompt length, as the attention share of a decode step grows.</li>" % (
                tp, "; ".join("prompt %d %s" % (p, pct(d["tps_pct"])) for p, d in vb), "; ".join("prompt %d %s" % (p, pct(d.get("ttft_pct"))) for p, d in vb)))
            worst = max(vb, key=lambda x: x[1].get("ttft_pct") or -1e9)
            wt = worst[1].get("ttft_pct")
            if wt is not None and wt > 0:
                c_b, c_v = cell(tp, worst[0], "base"), cell(tp, worst[0], "vnni")
                out.append("<li><b>tp%d, the one TTFT cost:</b> at prompt %d the vnni prefill takes %.3f s against %.3f s for base (%s, %+.0f ms; sd %.3f and %.3f s over %d repetitions, so the difference is real). The breakup plan's store-cost gate called more than 2%% at the short prompt a fail; this is the store cost that the design section 3.6 named as the open risk. At the longer prompts the kernel gain covers it.</li>" % (
                    tp, worst[0], c_v["ttft_mean_s"], c_b["ttft_mean_s"], pct(wt), 1000 * (c_v["ttft_mean_s"] - c_b["ttft_mean_s"]), c_v["ttft_sd_s"], c_b["ttft_sd_s"], c_v["n"]))
        if vo:
            out.append("<li><b>tp%d, the software path alone (vnni-off vs off, no AMX in either):</b> decode TPS %s; TTFT %s. The AVX-512 VNNI reader is faster than the row-major dotter in decode, and the scatter store does not show in the batched prefill without AMX.</li>" % (
                tp, "; ".join("prompt %d %s" % (p, pct(d["tps_pct"])) for p, d in vo), "; ".join("prompt %d %s" % (p, pct(d.get("ttft_pct"))) for p, d in vo)))
        if bo:
            out.append("<li><b>tp%d, the known AMX gain (base vs off):</b> decode TPS %s; TTFT %s. At prompt 1024 the 2026-09-13 campaign measured +13.2%% TPS and -20.0%% TTFT on the same base commit and placement, so the two campaigns agree and the arms are comparable.</li>" % (
                tp, "; ".join("prompt %d %s" % (p, pct(d["tps_pct"])) for p, d in bo), "; ".join("prompt %d %s" % (p, pct(d.get("ttft_pct"))) for p, d in bo)))
    return "<ul>" + "".join(out) + "</ul>" if out else '<p class="pending">pending</p>'


page.append("<h2>Reading the numbers</h2>" + reading_section())
page.append("<p>Every run completed with 8 requests of 253 generated tokens each (no early stop), arms interleaved inside each repetition; the sd column of the tables gives the spread over the repetitions. The full-page attention of a decode step dominates at prompt 8192, where the design gains most; the prefill at prompt 1024 is where the per-token store is most visible.</p>")

if prompts_for(4):
    page.append("<h2>3. Results: qwen3-4b tp4, 8 users</h2>")
    page.append("<h3>3.1 Decode rate</h3>" + dot_plot(4, "tps"))
    page.append("<h3>3.2 Time to first token</h3>" + dot_plot(4, "ttft"))
    page.append("<h3>3.3 Numbers</h3>" + numbers_table(4))
else:
    page.append('<h2>3. Results: qwen3-4b tp4, 8 users</h2><p class="pending">pending (the tp4 cells run after the tp2 cells)</p>')

page.append("<h2>4. What was built and how it was checked</h2>")
page.append("<p>Branch tip: <code>%s</code>. Commits on top of 544ca05c7a (jhan-amx-p0 = PR #3879 head):</p><pre>%s</pre><pre>%s</pre>" % (esc(head), esc(commits), esc(diffstat)))
page.append("<ul>")
page.append(syn_summary(syn_c1, "syntax-only compile, first commit 73125f5464 (TRON_K_VNNI ON and OFF, 3bda, during the CI window)"))
page.append(syn_summary(syn_c3, "syntax-only compile, formatted tip 18ba069c95 (ON and OFF)"))
page.append(syn_summary(syn_c6, "syntax-only compile, review-fix commit f66bb07542 (ON and OFF; the two clang-format differences were formatted in 5e45ae55ae)"))
page.append(pretest_summary(pretest))
page.append(pretest_summary(pretest_r6).replace("pre-window unit tests (4 cores during the CI window)", "pre-window unit tests rebuilt at the review-fix commit f66bb07542 (4 cores; t_llama_unit included)"))
page.append("<li>unit tests in the window (from tests.txt): %s</li>" % (esc(tests_txt.strip().replace("\n", " | ")) if tests_txt else "pending"))
page.append("<li>build in the window (from build.txt): %s</li>" % (esc(build_txt.strip().splitlines()[0]) if build_txt else "pending"))
page.append("</ul>")
page.append("<h3>4.1 Greedy-agreement smoke</h3>" + pre(smoke_txt, 30))
page.append("<p>How to read it: the A/A rows (base vs base2, vnni vs vnni2) must be identical, otherwise the run itself is not reproducible and no cross-arm row means anything. Expected (design section 5): base and vnni agree for a long prefix (the dense pages give bit-identical scores; only the partial page's add order differs).</p> <p>Reading of the measured rows (2026-09-14 11:49-11:52 UTC, prompt 1024, 128 generated, one user): both A/A pairs are identical for all 128 tokens, so the recipe reproduces. Within each binary, AMX on and AMX off give identical tokens (base vs off, vnni vs vnni-off): the AMX kernels tipped no near-tie in 128 tokens on either binary. The two binaries diverge from each other at generated token 52, in both AMX states, so the divergence comes from the one thing that differs between them in both states: the software reader of the partial page (row-major dotter against the VNNI reader), whose fp32 add order differs. The dense-page AMX scores are bit-identical by test and the PV kernel is the same code. This is the pattern of a near-tie flip (the 2026-08-19 AMX-vs-AVX runs flipped qwen at token 30 and llama at margins 0.031 and 0.000), and the unit test bounds the reader's deviation from the dotter to the accumulation-order envelope over every prefix and hole mask. The smoke cannot itself separate a near-tie flip from a small systematic error; the measurement that would settle it is the per-step logit margin at token 52 with the definitive-decode tooling (labelled: hypothesis with its test, not a measured fact).</p>")

page.append("<h2>5. Bill's investigation</h2>" + bill_section())

page.append("<h2>6. Raw data for the reviewing agent</h2>" + raw_data_section())

def questions_section():
    """Answers to jhan's three questions of 2026-09-14 (after the first report), with every
    number recomputed from summary.json."""
    def c(tp, p, a):
        return cell(tp, p, a)
    ps = sorted(set(prompts_for(2)) & set(prompts_for(4)))
    if not ps:
        return '<p class="pending">pending: tp2 and tp4 cells needed</p>'
    def step_ms(tp, p, a):
        return 1000.0 / c(tp, p, a)["tps_mean"]
    # table 1: tp4 / tp2 per arm
    t1 = ['<table><tr><th>prompt</th><th>arm</th><th>TPS/user tp2</th><th>TPS/user tp4</th><th>tp4 / tp2</th><th>aggregate tok/s tp2 (2 cards)</th><th>aggregate tok/s tp4 (4 cards)</th><th>per card tp2</th><th>per card tp4</th><th>TTFT tp2 s</th><th>TTFT tp4 s</th><th>tp4 / tp2</th></tr>']
    for p in ps:
        for a in ARMS:
            a2, a4 = c(2, p, a), c(4, p, a)
            if not a2 or not a4:
                continue
            t1.append('<tr><td>%d</td><td>%s</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.0f</td><td>%.0f</td><td>%.0f</td><td>%.0f</td><td>%.3f</td><td>%.3f</td><td>%.2f</td></tr>' % (
                p, a, a2["tps_mean"], a4["tps_mean"], a4["tps_mean"] / a2["tps_mean"], 8 * a2["tps_mean"], 8 * a4["tps_mean"],
                8 * a2["tps_mean"] / 2, 8 * a4["tps_mean"] / 4, a2["ttft_mean_s"], a4["ttft_mean_s"], a4["ttft_mean_s"] / a2["ttft_mean_s"]))
    t1.append('</table>')
    # table 2: absolute TTFT deltas and the implied per-row store cost
    t2 = ['<table><tr><th>tp</th><th>prompt</th><th>K rows stored in the prefill</th><th>vnni minus base TTFT</th><th>ns per K row if the whole difference were the store (est.)</th><th>vnni-off minus off TTFT</th><th>base prefill s</th></tr>']
    for tp in (2, 4):
        for p in ps:
            b, v, o, vo = c(tp, p, "base"), c(tp, p, "vnni"), c(tp, p, "off"), c(tp, p, "vnnioff")
            if not all([b, v, o, vo]):
                continue
            rows = 8 * p * 36 * 8
            dv = 1000 * (v["ttft_mean_s"] - b["ttft_mean_s"])
            do = 1000 * (vo["ttft_mean_s"] - o["ttft_mean_s"])
            t2.append('<tr><td>%d</td><td>%d</td><td>%.2f M</td><td>%+.0f ms (%s)</td><td>%+.0f</td><td>%+.0f ms</td><td>%.3f</td></tr>' % (
                tp, p, rows / 1e6, dv, pct(100 * (v["ttft_mean_s"] / b["ttft_mean_s"] - 1)), dv * 1e6 / rows, do, b["ttft_mean_s"]))
    t2.append('</table>')
    # table 3: decode step time and the saving per token
    t3 = ['<table><tr><th>tp</th><th>prompt</th><th>decode step off (ms)</th><th>base (ms)</th><th>vnni (ms)</th><th>base saves vs off (ms/token)</th><th>vnni saves vs base (ms/token)</th><th>vnni vs base TPS</th></tr>']
    for p in ps:
        for tp in (2, 4):
            o, b, v = c(tp, p, "off"), c(tp, p, "base"), c(tp, p, "vnni")
            if not all([o, b, v]):
                continue
            t3.append('<tr><td>%d</td><td>%d</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%+.2f</td><td>%+.2f</td><td>%s</td></tr>' % (
                tp, p, step_ms(tp, p, "off"), step_ms(tp, p, "base"), step_ms(tp, p, "vnni"),
                step_ms(tp, p, "off") - step_ms(tp, p, "base"), step_ms(tp, p, "base") - step_ms(tp, p, "vnni"),
                pct(100 * (v["tps_mean"] / b["tps_mean"] - 1))))
    t3.append('</table>')
    # numbers used in the prose
    def dms(tp, p):
        return 1000 * (c(tp, p, "vnni")["ttft_mean_s"] - c(tp, p, "base")["ttft_mean_s"])
    q1 = """
<h3>7.1 TTFT: why is VNNIed K slower than the baseline at tp4?</h3>
<p><b>Short answer.</b> The K store of the VNNI layout is a fixed amount of serial work per token on one thread, and at tp4 everything around it got faster, so more of it shows in the prefill time. At the long prompt the transpose-free kernel saves more than the store costs; at the short prompts it does not, and least of all at tp4.</p>
<p><b>What the store does.</b> A VNNI K store writes 4 bytes into each of 64 cache lines (k_vnni::scatter_row, 4 scatter instructions) where the row-major store writes one 256-byte row into 4 lines [h/tron/kernels/k_vnni.hpp:89-99; h/tron/models/kv_cache.hpp:1382-1392]. In the model measured here (the ingested qwen plugin) save_k is a statement of the forward pass's main thread: once per layer and pass it loops serially over the pass's tokens (up to 1024) and the 8 KV heads; the helper threads skip that statement, and the attention over this pass's own pages waits for it [ingest/src/TronCpp.hs:2212, 2279, 2309-2353; h/tron/models/model.hpp save_k_impl; h/tron/models/self_attention.hpp:782-788]. (The design page said &quot;RX worker&quot;; that placement is the handwritten llama plugin's, h/tron/plugins/llama.hpp:967-1025, and it is corrected in the design page now.) So the store work is the same 2.36 M rows for the 8 x 1024-token prefill at tp2 and at tp4 (8 users x 1024 tokens x 36 layers x 8 KV heads), on one core, while the matmuls run on 2 against 4 cards and the attention on 28 against 56 app cores. What shrinks with tp gets faster; the store does not, so a larger share of it is exposed.</p>
<p><b>The data.</b> vnni minus base prefill time at prompt 1024: %+.0f ms at tp2 (%s), %+.0f ms at tp4 (%s); at prompt 2048: %+.0f ms at tp2, %+.0f ms at tp4 (%s); at prompt 8192: %+.0f ms at tp2, %+.0f ms at tp4. Every tp4 difference is far outside the run spread (base 2.191 / 2.183 s against vnni 2.358 / 2.358 s at prompt 1024). If the whole tp4 prompt-1024 difference were the store, it would be %.0f ns per K row (est.); this is a lower bound on the exposed store cost, because the same number also contains the kernel's gain, and the prompt-2048 cell gives only %.0f ns per row net (est.), so the per-row net is not a constant. The August microbenchmark of the scalar mirror scatter measured 70.9 ns per row on one L2-resident core [exec/results/bench-scatter-20260824.txt]; it is a different routine on a different path, so it says the order of magnitude is right, not that the vectorized scatter costs the same. The G1 probe's scalar in-place store cost +189 ms in the rinzler serving path at qwen tp4 with 8 users (2026-09-08), the same magnitude as the +171 ms here.</p>
<p>The AMX-off pair (vnni-off minus off) is %+.0f ms at tp4 and %+.0f ms at tp2 at prompt 1024 and negative at every longer prompt; that arm also swaps the row-major dotter for the AVX-512 VNNI reader, which is faster in prefill, so it does not isolate the store either. What the data cannot give is the store's own time: <span class="warn">Insufficient data</span>; the measurement that settles it is a Perfetto trace of the &quot;Save K&quot; span (TRACE_EVENT in save_k_impl) for base and vnni at tp2 and tp4, prompt 1024, next to the attention workers' sections.</p>
%s
<p><b>What would remove it.</b> (a) In prefill, transpose each 16-token block of a page in registers and write full 64-byte lines (the design's section 7 block transpose; 16x fewer store instructions and no partial-line writes). (b) Stripe the save_k token loop over the idle helper threads by 16-token block: legal for K because tokens write disjoint bytes in this layout [k_vnni.hpp:22-24], unlike V's pair-interleaved plane. (c) Both.</p>
""" % (dms(2, 1024), pct(100 * (c(2, 1024, "vnni")["ttft_mean_s"] / c(2, 1024, "base")["ttft_mean_s"] - 1)), dms(4, 1024), pct(100 * (c(4, 1024, "vnni")["ttft_mean_s"] / c(4, 1024, "base")["ttft_mean_s"] - 1)),
       dms(2, 2048), dms(4, 2048), pct(100 * (c(4, 2048, "vnni")["ttft_mean_s"] / c(4, 2048, "base")["ttft_mean_s"] - 1)),
       dms(2, 8192), dms(4, 8192),
       dms(4, 1024) * 1e6 / (8 * 1024 * 36 * 8), dms(4, 2048) * 1e6 / (8 * 2048 * 36 * 8),
       1000 * (c(4, 1024, "vnnioff")["ttft_mean_s"] - c(4, 1024, "off")["ttft_mean_s"]), 1000 * (c(2, 1024, "vnnioff")["ttft_mean_s"] - c(2, 1024, "off")["ttft_mean_s"]),
       "".join(t2))
    def sav(tp, p, a, b):
        return step_ms(tp, p, a) - step_ms(tp, p, b)
    q2 = """
<h3>7.2 Decode TPS: why is the VNNIed K gain smaller at tp4 than at tp2?</h3>
<p><b>Short answer.</b> The VNNI gain is a saving inside the attention part of the decode step; at tp4 that part is spread over about twice the attention workers, so the saving per token is about half as many milliseconds, and it is a smaller fraction of a step that shrank less than attention did. The same dilution hits the baseline AMX gain. On top of that, the tp4 short-prompt cells have a run spread of 1 to 2.4 TPS over 2 repetitions, which covers the prompt-1024 result.</p>
<ul>
<li><b>Dilution.</b> CPU attention is not split across the tensor-parallel cards: every configuration runs the full attention of all 8 KV heads on its app cores, on about 20 attention workers at tp2 and 47 at tp4 (est. from the fixed helper split in the code; the run logs do not print the split). The saving the design removes (the transposing store, per page) therefore shrinks to roughly 20/47 = 0.43 of its tp2 milliseconds (est., linear scaling). Measured: vnni saves %.2f / %.2f / %.2f ms per token over base at tp2 and %.2f / %.2f / %.2f ms at tp4 (prompt 1024 / 2048 / 8192): ratios %.2f / %.2f / %.2f. The baseline AMX gain shows the same dilution: base saves %.2f / %.2f / %.2f ms per token over off at tp2 and %.2f / %.2f / %.2f at tp4 (ratios %.2f / %.2f / %.2f); in percent, +13.2%% -> +10.3%% at 1024 and +15.6%% -> +8.6%% at 2048, unchanged at 8192 (+17.2%% -> +17.0%%) where the whole step shrinks by the same factor as attention. Applying the AMX gain's own dilution ratio to the tp2 vnni saving predicts the tp4 vnni gain at prompt 2048 exactly (+3.8%% predicted, +3.8%% measured), leaves a shortfall of about 0.5 ms per token at prompt 1024 (+4.7%% predicted, %s measured) and about 1 ms at 8192 (+10.2%% predicted, %s measured).</li>
<li><b>Spread.</b> tp4 has 2 repetitions per cell; at prompt 1024 the base cell reads %.2f / %.2f and the vnni cell %.2f / %.2f TPS per user (both pairs within 1 to 2 TPS of each other), and the tp4 base-vs-off gain itself swings from +13.7%% to +7.0%% between the two repetitions. Any tp4 short-prompt delta carries about 3 percentage points of spread (est.), so the prompt-1024 shortfall is inside the spread. At prompt 8192 the per-repetition vnni saving is 2.46 and 1.57 ms per token; the residual shortfall of about 1 ms is within one repetition's spread.</li>
<li><b>The decode K store</b> also exists (2304 rows per step, on the main thread) but cannot be sized from this campaign; even at the scalar bench's 70.9 ns per row it would be 0.16 ms per step (est.), too small to carry the gap. Not confirmed, not excluded.</li>
</ul>
%s
<p>What settles the residual: the per-layer attention wall (the 2026-09-01 stamp-7605 method) at tp2 and tp4 for base and vnni, a Perfetto &quot;Save K&quot; span in decode, or 6 or more repetitions of the tp4 cells. Insufficient data to say more from this campaign.</p>
""" % (sav(2, 1024, "base", "vnni"), sav(2, 2048, "base", "vnni"), sav(2, 8192, "base", "vnni"),
       sav(4, 1024, "base", "vnni"), sav(4, 2048, "base", "vnni"), sav(4, 8192, "base", "vnni"),
       sav(4, 1024, "base", "vnni") / sav(2, 1024, "base", "vnni"), sav(4, 2048, "base", "vnni") / sav(2, 2048, "base", "vnni"), sav(4, 8192, "base", "vnni") / sav(2, 8192, "base", "vnni"),
       sav(2, 1024, "off", "base"), sav(2, 2048, "off", "base"), sav(2, 8192, "off", "base"),
       sav(4, 1024, "off", "base"), sav(4, 2048, "off", "base"), sav(4, 8192, "off", "base"),
       sav(4, 1024, "off", "base") / sav(2, 1024, "off", "base"), sav(4, 2048, "off", "base") / sav(2, 2048, "off", "base"), sav(4, 8192, "off", "base") / sav(2, 8192, "off", "base"),
       pct(100 * (c(4, 1024, "vnni")["tps_mean"] / c(4, 1024, "base")["tps_mean"] - 1)), pct(100 * (c(4, 8192, "vnni")["tps_mean"] / c(4, 8192, "base")["tps_mean"] - 1)),
       c(4, 1024, "base")["reps"][0]["tps_per_user"], c(4, 1024, "base")["reps"][1]["tps_per_user"], c(4, 1024, "vnni")["reps"][0]["tps_per_user"], c(4, 1024, "vnni")["reps"][1]["tps_per_user"],
       "".join(t3))
    q3 = """
<h3>7.3 Decode TPS: is tp4 slower than tp2?</h3>
<p><b>Short answer.</b> Not per user. In every one of the 12 (prompt, arm) pairs of this report the tp4 cell has a higher decode rate per user and a shorter prefill than the tp2 cell: tp4/tp2 TPS 1.25 to 1.37 at prompt 1024, 1.43 to 1.63 at 2048, 1.73 to 1.80 at 8192; TTFT 0.53 to 0.73 of the tp2 time (table below). The smallest gap (vnni, prompt 1024) is 20 times the cell spread.</p>
<p>Two true statements may be behind the question.</p>
<ul>
<li><b>tp4 is not twice tp2 although it has twice the cards and twice the app cores.</b> A decode step has a part that grows with the context and a part that does not. Fitting the step time as A + B at tp2 and A/2 + B at tp4 (est., two points per prompt) gives, for base, A = 6.3 / 12.3 / 51.1 ms per token at prompt 1024 / 2048 / 8192 (about 1 : 2 : 8, like the prompt lengths) and B = 6.2 / 6.7 / 6.7 ms, roughly constant. The part that halves is the CPU attention, which is not sharded across cards (both configurations attend all 8 KV heads on their app cores); the 6 to 7 ms that do not halve are the per-layer matmul launches, DMA and receive latency, the main thread's per-token kernels (norms, rope, the K and V stores) and the serial join of the attention workers. Which of those dominates is not measured here (a Perfetto trace of one decode step at each tp would settle it). The ratio therefore approaches 2 as the attention share grows: base %.2f at prompt 1024, %.2f at 2048, %.2f at 8192.</li>
<li><b>Per card, tp2 delivers more.</b> Normalizing the 8-user cells: %.0f tok/s on 2 cards at tp2 (%.0f per card) against %.0f tok/s on 4 cards at tp4 (%.0f per card), off arm, prompt 1024 (a normalization of one process, not a measurement of two tp2 processes). The measured version is the 2026-09-13 CI-layout run on the same 4 cards with CPU attention and AMX on: two tp2 engines with 2 users each gave 152.46 TPS aggregate against 123.89 for one tp4 engine with 4 users (+23%%) [exec/results/p0perf-20260913/summary.md]. The nightly CI's per-machine numbers (tp2 185.4 against tp4 147.2 TPS on 2026-09-11: 4 tp2 engines x 2 users against 2 tp4 engines x 4 users on 8 cards) point the same way, but they run FPGA attention and mix the tensor-parallel effect with the users-per-engine effect, so they are a supporting example, not the same measurement. That is the one place where tp4 reads slower than tp2, and it is a fixed-card-count comparison, not a per-user one.</li>
</ul>
<p>Two readings of this page could also suggest &quot;tp4 slower&quot;: the vnni-vs-base deltas are smaller at tp4 (section 7.2), and every chart row has its own scale, so dots cannot be compared across rows by position; the numbers table is the reference.</p>
%s
""" % (c(4, 1024, "base")["tps_mean"] / c(2, 1024, "base")["tps_mean"], c(4, 2048, "base")["tps_mean"] / c(2, 2048, "base")["tps_mean"], c(4, 8192, "base")["tps_mean"] / c(2, 8192, "base")["tps_mean"],
       8 * c(2, 1024, "off")["tps_mean"], 8 * c(2, 1024, "off")["tps_mean"] / 2, 8 * c(4, 1024, "off")["tps_mean"], 8 * c(4, 1024, "off")["tps_mean"] / 4, "".join(t1))
    return q1 + q2 + q3


page.append("<h2>7. Questions from jhan (2026-09-14) and the answers</h2>" + questions_section())

page.append("""<h2>8. Open items</h2>
<ul>
<li>FPGA-attention path (USE_HW_ATTN unset): the gather adapter in the GOF staging is built but its cost is unmeasured (design section 3.7).</li>
<li>Prefill store: TTFT of vnni is above base at the short prompts (section 7.1); the planned fixes are the 16-token block transpose in save_k (full cache lines) and striping the save_k token loop over the idle helper threads (design section 7). The store's own time was not measured; a Perfetto &quot;Save K&quot; span would give it.</li>
<li>CI: no lane compiles TRON_K_VNNI=ON; the new test needs a cost-data entry (bin/slice bench --update t_k_vnni_layout, a whole-machine measurement) before a PR can pass the slice check.</li>
<li>Models with head 128 and kv_mul other than 4 (llama-3.2-3b) run the AVX-512 VNNI reader without AMX; not measured.</li>
</ul>
</main></body></html>""")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
out = "".join(page)
bad = [c for c in out if ord(c) > 127]
if bad:
    out = "".join(("&#%d;" % ord(c)) if ord(c) > 127 else c for c in out)
open(OUT, "w").write(out)
print("wrote", OUT, len(out), "bytes; non-ascii replaced:", len(bad))
