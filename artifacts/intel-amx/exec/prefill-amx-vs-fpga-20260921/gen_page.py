#!/usr/bin/env python3
"""Generate CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html.

Question (jhan, 2026-09-21): for qwen3-4b, is prefill (TTFT) better with AMX
attention on the CPU (canonical build or the VNNI-K build) or with attention on
the FPGA?  Decode TPS is already known to favour the FPGA.

Every number below was extracted from the campaign result files by the
2026-09-21 workflow (14 agents, journal wf_258257df-233) and is carried here
with its per-repetition values so the deltas and t statistics are recomputed
from raw values, not copied.  rows-extracted.json next to this script is the
full extraction (253 rows).

Pure ASCII output (artifact mojibake trap).  Light theme only (jhan rule).
"""
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fpga_section as FS  # noqa: E402  (section 5 from the q4b-fpga-20260921 campaign, when its rows exist)
import rt8u_section as RT  # noqa: E402  (the runtron campaign of 2026-09-22, when its summary exists)
OUT = "/home/jhan/workspace/intel-AMX/CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html"
R = "/home/jhan/workspace/intel-AMX/exec/results"

# ---------------------------------------------------------------- raw values
# Each arm: label, attention ('cpu'|'fpga'), kernel ('avx'|'canon'|'vnnik'),
# per-rep TTFT ms, build, file ref.  All qwen-3-4b, prompt 1024.

def arm(label, attention, kernel, reps, build, ref, note=""):
    reps = [float(x) for x in reps]
    n = len(reps)
    mean = sum(reps) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in reps) / (n - 1)) if n > 1 else None
    return dict(label=label, attention=attention, kernel=kernel, reps=reps, n=n,
                mean=mean, sd=sd, build=build, ref=ref, note=note)

P0 = R + "/p0perf-20260913/summary.md"
WP = R + "/wedperf-20260916/summary.md"  # cited lines hold the cell means; per-rep values are in summary.json (cells[].reps[].ttft_s)
WA = R + "/wedperf-attr-20260916/summary.md"  # same: means at the cited lines, per-rep values in summary.json
V4 = R + "/vnnik4-20260915/summary.md"
V4M = R + "/vnnik4-models-20260915/results.txt"
QS = R + "/q4b-swattn-20260919/summary.txt"
CC = R + "/canon-ci-20260918/canon/summary.txt"
CMB = R + "/ci-mimic-20260918/base-pass1/summary.txt"
CMT = R + "/ci-mimic-20260918/target-pass1/summary.txt"
NS = R + "/nightly_stats.json"
M6 = R + "/issue4500-20260918/m6/summary.md"
I45 = R + "/issue4500-20260918/summary.md"

# CI harness, our half, nightly per-engine load, one binary 544ca05c7a, 2026-09-13
ci_half_tp2 = dict(
    avx=arm("AVX (kill switch)", "cpu", "avx", [913, 906, 907], "544ca05c7a + TRON_AMX_DISABLE=1", P0 + ":15,44-46"),
    canon=arm("canonical AMX", "cpu", "canon", [726, 731, 725], "544ca05c7a", P0 + ":15,47-49"),
    fpga=arm("FPGA attention (CPU share on AVX)", "fpga", "avx", [759, 760, 764], "544ca05c7a + TRON_AMX_DISABLE=1, USE_HW_ATTN unset", P0 + ":15,50-52"),
)
ci_half_tp4 = dict(
    avx=arm("AVX (kill switch)", "cpu", "avx", [954, 955, 947], "544ca05c7a + TRON_AMX_DISABLE=1", P0 + ":17,53-55"),
    canon=arm("canonical AMX", "cpu", "canon", [854, 856, 857], "544ca05c7a", P0 + ":17,56-58"),
    fpga=arm("FPGA attention (CPU share on AVX)", "fpga", "avx", [843, 834, 841], "544ca05c7a + TRON_AMX_DISABLE=1, USE_HW_ATTN unset", P0 + ":17,59-61"),
)
# CI harness, whole 3bda, 4 tp2 engines x 2 users, client claude-agentsrv
ci_whole_tp2 = dict(
    canon_cpu=arm("canonical AMX deb, CPU attention (q4b-swattn, 3 passes, 2026-09-20)", "cpu", "canon", [516, 518, 518], "deb 2026.09.18-0594dc54-jhan-ci-canon, USE_HW_ATTN=0", QS + ":3"),
    canon_fpga=arm("canonical AMX deb, FPGA attention (canon-ci, 1 pass, 2026-09-18 23:48 UTC)", "fpga", "canon", [516], "deb 2026.09.18-0594dc54-jhan-ci-canon, USE_HW_ATTN unset", CC + ":36"),
    avx_cpu=arm("nightly deb, CPU attention (q4b-swattn, 3 passes, 2026-09-20)", "cpu", "avx", [666, 655, 702], "deb 2026.09.18-3faba6d0 (no AMX code), USE_HW_ATTN=0", QS + ":3"),
    avx_fpga_night=arm("nightly deb, FPGA attention (the 2026-09-18 nightly itself, remote client)", "fpga", "avx", [528], "deb 2026.09.18-3faba6d0, USE_HW_ATTN unset", R + "/ci-mimic-20260918/reference/nightly-0918.arm.json:896 (tp2 528 ms; this night is not in the 13-night series of nightly_stats.json)"),
    avx_fpga_mimic=arm("nightly deb, FPGA attention (ci-mimic base, 2026-09-18, client CPU-saturated)", "fpga", "avx", [556], "deb 2026.09.18-3faba6d0, USE_HW_ATTN unset", CMB + ":36"),
    vnnik_fpga=arm("VNNI-K deb, FPGA attention (ci-mimic target, 2026-09-18)", "fpga", "vnnik", [504], "deb 2026.09.18-29a8a547-jhan-ci-mimic-target (main + PR 4424)", CMT + ":36"),
)
NIGHT13_TP2 = (509.5, 7.2, 13)   # 13-night mean, sd, n  [nightly_stats.json]
NIGHT13_TP4 = (635.2, 10.1, 13)
ci_whole_tp4_fpga = dict(
    avx_night=arm("nightly deb, FPGA attention (2026-09-18 nightly)", "fpga", "avx", [636], "deb 2026.09.18-3faba6d0", R + "/ci-mimic-20260918/reference/nightly-0918.arm.json:999"),
    canon=arm("canonical AMX deb, FPGA attention (canon-ci)", "fpga", "canon", [646], "deb 0594dc54", CC + ":37"),
    vnnik=arm("VNNI-K deb, FPGA attention (ci-mimic target)", "fpga", "vnnik", [629], "deb 29a8a547", CMT + ":37"),
)
# CI harness, our half, one rinzler engine, FPGA attention only, CPU build varied (issue 4500 block m6)
m6_tp2 = dict(
    avx=arm("nightly deb (AVX)", "fpga", "avx", [763, 761], "deb 2026.09.18-3faba6d0", M6 + ":5"),
    vnnik=arm("VNNI-K deb (AMX on)", "fpga", "vnnik", [698, 701], "deb 29a8a547", M6 + ":6"),
    vnnik_kill=arm("VNNI-K deb + kill switch", "fpga", "avx", [761, 764], "deb 29a8a547 + TRON_AMX_DISABLE=1", M6 + ":7"),
)
m6_tp4 = dict(
    avx=arm("nightly deb (AVX)", "fpga", "avx", [847, 850], "deb 2026.09.18-3faba6d0", M6 + ":10"),
    vnnik=arm("VNNI-K deb (AMX on)", "fpga", "vnnik", [809, 809], "deb 29a8a547", M6 + ":11"),
    vnnik_kill=arm("VNNI-K deb + kill switch", "fpga", "avx", [815, 814], "deb 29a8a547 + TRON_AMX_DISABLE=1", M6 + ":12"),
)

# runtron, our half, 8 users in one batch, prompt 1024, 256 generated
rt_wed_tp2 = dict(
    avx_cpu=arm("AVX", "cpu", "avx", [3942.4, 3947.8, 3944.2], "eb2de0265a (main before PR 3879)", WP + ":21"),
    avx_fpga=arm("AVX", "fpga", "avx", [3176.7, 3205.3], "eb2de0265a", WP + ":31"),
    vnnik_cpu=arm("VNNI-K", "cpu", "vnnik", [3084.3, 3085.0, 3092.2], "ff680c8020 (PR 4424 head)", WP + ":22"),
    vnnik_fpga=arm("VNNI-K", "fpga", "vnnik", [3140.3, 3159.1], "ff680c8020", WP + ":32"),
)
rt_wed_tp4 = dict(
    avx_cpu=arm("AVX", "cpu", "avx", [2458.6, 2463.5, 2468.6], "eb2de0265a", WP + ":23"),
    avx_fpga=arm("AVX", "fpga", "avx", [2290.0, 2255.6], "eb2de0265a", WP + ":33"),
    vnnik_cpu=arm("VNNI-K", "cpu", "vnnik", [2126.0, 2112.6, 2124.7], "ff680c8020", WP + ":24"),
    vnnik_fpga=arm("VNNI-K", "fpga", "vnnik", [2217.9, 2285.1], "ff680c8020", WP + ":34"),
)
rt_attr_tp2 = dict(
    avx_cpu=arm("AVX", "cpu", "avx", [3945.6, 3940.2], "eb2de0265a", WA + ":13"),
    avx_fpga=arm("AVX", "fpga", "avx", [3202.6, 3238.8, 3179.9, 3218.6, 3205.2, 3240.1], "eb2de0265a", WA + ":25"),
    canon_cpu=arm("canonical AMX", "cpu", "canon", [3158.1, 3154.9], "c7844ca2ce (main after the PR 3879 merge)", WA + ":14"),
    canon_fpga=arm("canonical AMX", "fpga", "canon", [3203.0, 3181.3, 3197.5, 3194.0, 3209.9, 3185.0], "c7844ca2ce", WA + ":26"),
    vnnik_cpu=arm("VNNI-K", "cpu", "vnnik", [3089.0, 3093.7], "ff680c8020", WA + ":15"),
    vnnik_fpga=arm("VNNI-K", "fpga", "vnnik", [3182.1, 3143.8, 3143.2, 3166.7, 3164.6, 3166.0], "ff680c8020", WA + ":27"),
)
rt_attr_tp4_fpga = dict(
    avx=arm("AVX", "fpga", "avx", [2245.0, 2278.7, 2243.6, 2235.1, 2269.0, 2247.4], "eb2de0265a", WA + ":22"),
    canon=arm("canonical AMX", "fpga", "canon", [2281.1, 2279.3, 2290.7, 2316.9, 2271.4, 2290.8], "c7844ca2ce", WA + ":23"),
    vnnik=arm("VNNI-K", "fpga", "vnnik", [2220.8, 2262.5, 2214.1, 2260.0, 2216.3, 2209.5], "ff680c8020", WA + ":24"),
)
rt_v4_tp2 = dict(
    canon_cpu=arm("canonical AMX", "cpu", "canon", [3138.461, 3144.168], "544ca05c7a (runtron.p0perf13)", V4 + ":9"),
    canon_fpga=arm("canonical AMX", "fpga", "canon", [3154.906], "544ca05c7a", V4M + ":58-77 (rt cell=fpga arm=base)"),
    vnnik_cpu=arm("VNNI-K", "cpu", "vnnik", [3089.202, 3075.878], "dc950be5f2 (VNNI K, block+stripe store)", V4 + ":10"),
    vnnik_fpga=arm("VNNI-K", "fpga", "vnnik", [3162.477], "dc950be5f2", V4M + ":78-97 (rt cell=fpga arm=new)"),
)
rt_canon_tp4_cpu = arm("canonical AMX (544ca05c7a, 2026-09-13, 6 reps)", "cpu", "canon",
                       [2201, 2210, 2200, 2198, 2196, 2192], "544ca05c7a", P0 + ":8,38-43")
rt_canon_tp4_fpga_i45 = arm("canonical AMX (c7844ca2ce, issue 4500 block m1, 2026-09-18, 3 reps)", "fpga", "canon",
                            [2333.4] * 3, "c7844ca2ce", I45 + ":15 (mean 2.333 s, sd 9.2 ms; per-rep not carried)")

# prompt-length scaling, runtron tp2 8 users, CPU attention, vnnik-20260914 (cold prompts, 3 reps)
scaling = {
    "AVX (kill switch)": {1024: 3937.8, 2048: 11077.5, 8192: 121679.4},
    "canonical AMX": {1024: 3150.9, 2048: 7271.9, 8192: 53284.3},
    "VNNI-K (2026-09-14 store)": {1024: 3221.4, 2048: 7271.1, 8192: 52343.5},
}
SCALING_REF = R + "/vnnik-20260914/summary.md:9-20"
fpga_1024_points = {  # runtron tp2 8 users FPGA attention at 1024 (the only prompt length measured)
    "AVX": 3191.0, "canonical AMX": 3195.1, "VNNI-K": 3149.7,
}
# CI-harness prompt sweep (q4b-swattn, both arms CPU attention, warm prefix cache above 1024)
sweep_prompts = [1024, 1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192]
sweep_avx = [674.3, 1180.7, 1683.3, 3361.0, 5468.3, 8086.3, 11092.3, 13238.3, 15763.7]
sweep_canon = [517.3, 845.7, 1087.7, 1857.7, 2778.7, 3744.3, 4493.0, 5738.0, 7144.7]
sweep_canon_cold_8192 = 12743.0


# ---------------------------------------------------------------- statistics
def welch_t(a, b):
    """t of (mean a - mean b) with unequal variances; None if either n < 2."""
    if a["n"] < 2 or b["n"] < 2:
        return None
    va = a["sd"] ** 2 / a["n"]
    vb = b["sd"] ** 2 / b["n"]
    if va + vb == 0:
        return None
    return (a["mean"] - b["mean"]) / math.sqrt(va + vb)


def welch_df(a, b):
    """Welch-Satterthwaite degrees of freedom; None if either n < 2."""
    if a["n"] < 2 or b["n"] < 2:
        return None
    va = a["sd"] ** 2 / a["n"]
    vb = b["sd"] ** 2 / b["n"]
    den = (va ** 2 / (a["n"] - 1)) + (vb ** 2 / (b["n"] - 1))
    return None if den == 0 else (va + vb) ** 2 / den


SHORT = {
    "our half, tp2, 2 engines x 2 users, one binary 544ca05c7a, 2026-09-13": "our half, tp2, 2 users/engine, one binary (09-13)",
    "our half, tp4, 1 engine x 4 users, one binary 544ca05c7a, 2026-09-13": "our half, tp4, 4 users/engine, one binary (09-13)",
    "whole 3bda, tp2, 4 engines x 2 users, one deb 0594dc54, 2026-09-18 vs 09-20": "whole 3bda, tp2, nightly layout, one deb (09-18 / 09-20)",
    "whole 3bda, tp2, 4 engines x 2 users, nightly deb 3faba6d0, 2026-09-18 vs 09-20": "whole 3bda, tp2, nightly layout, nightly deb (09-18 / 09-20)",
    "tp2, 2026-09-16 (wedperf)": "tp2, 8 users, 09-16 (wedperf)",
    "tp2, 2026-09-16 (wedperf-attr)": "tp2, 8 users, 09-16 (wedperf-attr)",
    "tp2, 2026-09-15 (vnnik4)": "tp2, 8 users, 09-15 (vnnik4)",
    "tp4, 2026-09-16 (wedperf)": "tp4, 8 users, 09-16 (wedperf)",
    "tp4, canonical: CPU 544ca05c7a (09-13) vs FPGA c7844ca2ce (09-16 attr)": "tp4, 8 users, canonical, two builds (09-13 / 09-16)",
}


def pair(setup, group, kernel, cpu, fpga, note="", solid=True):
    d = fpga["mean"] - cpu["mean"]
    pct = 100.0 * d / cpu["mean"]
    return dict(setup=setup, group=group, kernel=kernel, cpu=cpu, fpga=fpga,
                delta_ms=d, pct=pct, t=welch_t(fpga, cpu), df=welch_df(fpga, cpu), note=note, solid=solid)


PAIRS = [
    # CI harness
    pair("our half, tp2, 2 engines x 2 users, one binary 544ca05c7a, 2026-09-13", "ci", "avx",
         ci_half_tp2["avx"], ci_half_tp2["fpga"]),
    pair("our half, tp2, 2 engines x 2 users, one binary 544ca05c7a, 2026-09-13", "ci", "canon",
         ci_half_tp2["canon"], ci_half_tp2["fpga"],
         "the FPGA arm ran with the kill switch (its CPU share is AVX). Block m6 measured that switch at +62 ms in this layout for the VNNI-K deb, so the canonical-vs-FPGA gap here lies between about -4 % and +4.6 %"),
    pair("our half, tp4, 1 engine x 4 users, one binary 544ca05c7a, 2026-09-13", "ci", "avx",
         ci_half_tp4["avx"], ci_half_tp4["fpga"]),
    pair("our half, tp4, 1 engine x 4 users, one binary 544ca05c7a, 2026-09-13", "ci", "canon",
         ci_half_tp4["canon"], ci_half_tp4["fpga"],
         "the FPGA arm ran with the kill switch, so its CPU share is AVX"),
    pair("whole 3bda, tp2, 4 engines x 2 users, one deb 0594dc54, 2026-09-18 vs 09-20", "ci", "canon",
         ci_whole_tp2["canon_cpu"], ci_whole_tp2["canon_fpga"],
         "FPGA side is one pass (n = 1). The night-to-night sd of this cell is 7.2 ms. Same client host on both sides"),
    pair("whole 3bda, tp2, 4 engines x 2 users, nightly deb 3faba6d0, 2026-09-18 vs 09-20", "ci", "avx",
         ci_whole_tp2["avx_cpu"], ci_whole_tp2["avx_fpga_night"],
         "FPGA side is the 2026-09-18 nightly (remote client). The 13-night mean is 509.5 +/- 7.2 ms. CPU side: base pass 3 (702 ms) had an uneven Caddy spread (22 / 22 / 0 / 20 requests per engine) and 2 Caddy health events. Passes 1 and 2 alone give 660 ms and -20.1 %"),
    # runtron
    pair("tp2, 2026-09-16 (wedperf)", "rt", "avx", rt_wed_tp2["avx_cpu"], rt_wed_tp2["avx_fpga"]),
    pair("tp2, 2026-09-16 (wedperf)", "rt", "vnnik", rt_wed_tp2["vnnik_cpu"], rt_wed_tp2["vnnik_fpga"]),
    pair("tp2, 2026-09-16 (wedperf-attr)", "rt", "avx", rt_attr_tp2["avx_cpu"], rt_attr_tp2["avx_fpga"]),
    pair("tp2, 2026-09-16 (wedperf-attr)", "rt", "canon", rt_attr_tp2["canon_cpu"], rt_attr_tp2["canon_fpga"]),
    pair("tp2, 2026-09-16 (wedperf-attr)", "rt", "vnnik", rt_attr_tp2["vnnik_cpu"], rt_attr_tp2["vnnik_fpga"]),
    pair("tp2, 2026-09-15 (vnnik4)", "rt", "canon", rt_v4_tp2["canon_cpu"], rt_v4_tp2["canon_fpga"],
         "FPGA side n = 1. CPU cells logged at debug level, FPGA cells at info level"),
    pair("tp2, 2026-09-15 (vnnik4)", "rt", "vnnik", rt_v4_tp2["vnnik_cpu"], rt_v4_tp2["vnnik_fpga"],
         "FPGA side n = 1. CPU side forced TRON_K_VNNI_BLOCK=1 and TRON_K_VNNI_STRIPE=1 by env, the FPGA side ran the binary's defaults (not recorded)"),
    pair("tp4, 2026-09-16 (wedperf)", "rt", "avx", rt_wed_tp4["avx_cpu"], rt_wed_tp4["avx_fpga"]),
    pair("tp4, 2026-09-16 (wedperf)", "rt", "vnnik", rt_wed_tp4["vnnik_cpu"], rt_wed_tp4["vnnik_fpga"],
         "the two FPGA repetitions are 67 ms apart (2218 and 2285 ms), so the size of this delta is not resolved (about 1 degree of freedom)"),
    pair("tp4, canonical: CPU 544ca05c7a (09-13) vs FPGA c7844ca2ce (09-16 attr)", "rt", "canon",
         rt_canon_tp4_cpu, rt_attr_tp4_fpga["canon"],
         "different builds and days (no same-binary canonical tp4 pair exists). Hollow marker", solid=False),
]

# ---------------------------------------------------------------- helpers
KCOL = {"avx": "#1baf7a", "canon": "#2a78d6", "vnnik": "#eb6834"}   # dataviz slots 3, 1, 2
KNAME = {"avx": "AVX (no AMX code, or kill switch)", "canon": "canonical AMX (PR 3879)", "vnnik": "AMX + VNNI-K (PR 4424)"}
KSHORT = {"avx": "AVX", "canon": "canonical AMX", "vnnik": "VNNI-K"}
INK, INK2, INK3, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"


def f0(x):
    return f"{x:,.0f}"


def f1(x):
    return f"{x:.1f}"


def pct(x):
    return f"{x:+.1f} %"


def tstr(t):
    return "-" if t is None else f"{t:+.1f}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rel_ref(ref):
    return ref.replace("/home/jhan/workspace/intel-AMX/", "")


# ---------------------------------------------------------------- figure 1: diverging dots
def fig1():
    ci = [p for p in PAIRS if p["group"] == "ci"]
    rt = [p for p in PAIRS if p["group"] == "rt"]
    # group rows by setup, keep order
    def rows_of(pairs):
        rows = []
        for p in pairs:
            if not rows or rows[-1]["setup"] != p["setup"]:
                rows.append(dict(setup=p["setup"], pairs=[]))
            rows[-1]["pairs"].append(p)
        return rows
    rows_ci, rows_rt = rows_of(ci), rows_of(rt)
    W = 1000
    left, right = 430, 960
    xmin, xmax = -26.0, 10.0
    def X(v):
        return left + (v - xmin) / (xmax - xmin) * (right - left)
    row_h = 30
    y = 118
    out = []
    n_rows = len(rows_ci) + len(rows_rt)
    H = y + n_rows * row_h + 2 * 34 + 70
    out.append(f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="TTFT of FPGA attention relative to CPU attention, qwen3-4b, prompt 1024" style="max-width:{W}px;font-family:system-ui,sans-serif">')
    out.append(f'<text x="16" y="24" font-size="15" font-weight="600" fill="{INK}">Prefill with attention on the FPGA, relative to prefill with attention on the CPU (qwen3-4b, prompt 1024)</text>')
    out.append(f'<text x="16" y="44" font-size="12" fill="{INK2}">Each dot: (FPGA-attention TTFT minus CPU-attention TTFT) as a percentage of the CPU-attention TTFT. Left of zero = the FPGA prefill is faster.</text>')
    out.append(f'<text x="16" y="60" font-size="12" fill="{INK2}">The colour is the CPU attention kernel the FPGA arm is compared with. Hollow dot = the two sides are different builds.</text>')
    # legend
    lx = 16
    for k in ("avx", "canon", "vnnik"):
        out.append(f'<circle cx="{lx + 6}" cy="82" r="5" fill="{KCOL[k]}"/>')
        out.append(f'<text x="{lx + 16}" y="86" font-size="11" fill="{INK2}">{esc(KNAME[k])}</text>')
        lx += 300
    # axis grid
    for v in range(-25, 11, 5):
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{y - 8}" x2="{x:.1f}" y2="{H - 60}" stroke="{GRID if v else INK3}" stroke-width="{1 if v else 1.5}"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 44}" font-size="11" fill="{INK3}" text-anchor="middle">{v:+d} %</text>')
    out.append(f'<text x="{(X(xmin) + X(0)) / 2:.1f}" y="{y - 14}" font-size="11" fill="{INK3}" text-anchor="middle">FPGA prefill faster</text>')
    out.append(f'<text x="{(X(0) + X(xmax)) / 2:.1f}" y="{y - 14}" font-size="11" fill="{INK3}" text-anchor="middle">CPU prefill faster</text>')
    out.append(f'<text x="{(left + right) / 2:.1f}" y="{H - 24}" font-size="11" fill="{INK3}" text-anchor="middle">TTFT of the FPGA-attention arm relative to the CPU-attention arm (percent of the CPU arm)</text>')

    def draw_rows(rows, title):
        nonlocal y
        out.append(f'<text x="16" y="{y + 4}" font-size="12" font-weight="600" fill="{INK}">{esc(title)}</text>')
        y += 34
        for r in rows:
            out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="11" fill="{INK}" text-anchor="end">{esc(SHORT.get(r["setup"], r["setup"]))}</text>')
            out.append(f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="{GRID}" stroke-width="1"/>')
            # labels stacked to avoid collisions: sort by pct
            ps = sorted(r["pairs"], key=lambda p: p["pct"])
            for i, p in enumerate(ps):
                x = X(p["pct"])
                fill = KCOL[p["kernel"]] if p["solid"] else SURF
                out.append(f'<circle cx="{x:.1f}" cy="{y}" r="6" fill="{fill}" stroke="{KCOL[p["kernel"]]}" stroke-width="2"><title>{esc(KSHORT[p["kernel"]])}: CPU {f0(p["cpu"]["mean"])} ms (n={p["cpu"]["n"]}) vs FPGA {f0(p["fpga"]["mean"])} ms (n={p["fpga"]["n"]}) = {pct(p["pct"])}, {p["delta_ms"]:+.0f} ms, Welch t {tstr(p["t"])}</title></circle>')
                lbl = f'{pct(p["pct"])}'
                # place label right of the dot if pct<0 and there is no neighbour within 3.5 points to the right
                nxt = ps[i + 1]["pct"] if i + 1 < len(ps) else None
                prv = ps[i - 1]["pct"] if i > 0 else None
                if nxt is not None and nxt - p["pct"] < 4.5:
                    anchor, xx = "end", x - 10
                elif prv is not None and p["pct"] - prv < 4.5:
                    anchor, xx = "start", x + 10
                else:
                    anchor, xx = ("start", x + 10) if p["pct"] < 0 else ("end", x - 10)
                out.append(f'<text x="{xx:.1f}" y="{y + 4}" font-size="11" fill="{INK}" text-anchor="{anchor}">{lbl}</text>')
            y += row_h
    draw_rows(rows_ci, "CI harness (client-side TTFT, 2 or 4 users per engine)")
    draw_rows(rows_rt, "runtron (server-side prefill of 8 prompts in one batch)")
    out.append('</svg>')
    return "\n".join(out)


# ---------------------------------------------------------------- figure 2: whole-machine bars
def fig2():
    bars = [
        ("nightly deb (AVX) + CPU attention", ci_whole_tp2["avx_cpu"], "cpu"),
        ("nightly deb (AVX) + FPGA attention  [2026-09-18 nightly]", ci_whole_tp2["avx_fpga_night"], "fpga"),
        ("canonical AMX deb + CPU attention", ci_whole_tp2["canon_cpu"], "cpu"),
        ("canonical AMX deb + FPGA attention", ci_whole_tp2["canon_fpga"], "fpga"),
        ("VNNI-K deb + FPGA attention  (no CPU-attention run exists)", ci_whole_tp2["vnnik_fpga"], "fpga"),
    ]
    W, left, right = 980, 420, 900
    xmax = 720.0
    def X(v):
        return left + v / xmax * (right - left)
    ACOL = {"cpu": "#2a78d6", "fpga": "#eb6834"}
    y0, bh, gap = 140, 22, 14
    H = y0 + len(bars) * (bh + gap) + 70
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Whole-machine CI layout TTFT at prompt 1024, tp2" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="16" y="24" font-size="15" font-weight="600" fill="{INK}">Whole delphi-3bda in the nightly layout (4 tp2 engines behind Caddy, 2 users each), prompt 1024</text>')
    out.append(f'<text x="16" y="44" font-size="12" fill="{INK2}">Client-side TTFT in ms, mean of 8 users x 10 rounds. CPU-attention bars: q4b-swattn 2026-09-20, mean of 3 passes.</text>')
    out.append(f'<text x="16" y="60" font-size="12" fill="{INK2}">FPGA-attention bars: one pass each (canon-ci 2026-09-19, ci-mimic 2026-09-18, the nightly of 2026-09-18).</text>')
    out.append(f'<text x="16" y="76" font-size="12" fill="{INK2}">Night-to-night spread of the nightly cell: 509.5 +/- 7.2 ms over 13 nights. Each FPGA bar is one pass,</text>')
    out.append(f'<text x="16" y="92" font-size="12" fill="{INK2}">so a difference between two bars under about 20 ms is not resolved.</text>')
    out.append(f'<rect x="16" y="106" width="12" height="12" fill="{ACOL["cpu"]}"/><text x="34" y="116" font-size="11" fill="{INK2}">attention on the CPU (USE_HW_ATTN=0)</text>')
    out.append(f'<rect x="286" y="106" width="12" height="12" fill="{ACOL["fpga"]}"/><text x="304" y="116" font-size="11" fill="{INK2}">attention on the FPGA (USE_HW_ATTN unset, the nightly default)</text>')
    for v in range(0, 701, 100):
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{y0 - 6}" x2="{x:.1f}" y2="{H - 50}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 34}" font-size="11" fill="{INK3}" text-anchor="middle">{v}</text>')
    out.append(f'<text x="{(left + right) / 2:.1f}" y="{H - 16}" font-size="11" fill="{INK3}" text-anchor="middle">TTFT, ms (client side)</text>')
    y = y0
    for label, a, mode in bars:
        out.append(f'<text x="{left - 12}" y="{y + bh / 2 + 4}" font-size="11" fill="{INK}" text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{X(a["mean"]) - left:.1f}" height="{bh}" rx="4" fill="{ACOL[mode]}"><title>{esc(a["label"])}: {f0(a["mean"])} ms, n={a["n"]}</title></rect>')
        out.append(f'<text x="{X(a["mean"]) + 8:.1f}" y="{y + bh / 2 + 4}" font-size="12" fill="{INK}">{f0(a["mean"])} ms</text>')
        y += bh + gap
    out.append('</svg>')
    return "\n".join(out)


# ---------------------------------------------------------------- figure 3: scaling (log y)
def fig3():
    W, H = 980, 480
    left, right, top, bot = 90, 700, 86, 410
    xs = [1024, 2048, 8192]
    def X(p):
        return left + (math.log2(p) - 10) / (13 - 10) * (right - left)
    ymin, ymax = math.log10(2000), math.log10(200000)
    def Y(ms):
        return bot - (math.log10(ms) - ymin) / (ymax - ymin) * (bot - top)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="TTFT against prompt length, CPU attention kernels, with the FPGA gap" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="16" y="24" font-size="15" font-weight="600" fill="{INK}">Prefill time against prompt length: measured for CPU attention, not measured for FPGA attention above 1024</text>')
    out.append(f'<text x="16" y="44" font-size="12" fill="{INK2}">runtron, tp2, 8 users in one batch, our half, 2026-09-14 (3 reps per point, cold prompts). Both axes are logarithmic.</text>')
    out.append(f'<text x="16" y="60" font-size="12" fill="{INK2}">The FPGA-attention point exists only at prompt 1024 (three builds, 2026-09-16, 3.15 to 3.20 s).</text>')
    for ms in (2000, 5000, 10000, 20000, 50000, 100000):
        yy = Y(ms)
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 8}" y="{yy + 4:.1f}" font-size="11" fill="{INK3}" text-anchor="end">{ms / 1000:g} s</text>')
    for p in xs:
        out.append(f'<text x="{X(p):.1f}" y="{bot + 20}" font-size="11" fill="{INK3}" text-anchor="middle">prompt {p}</text>')
    out.append(f'<text x="{(left + right) / 2:.1f}" y="{bot + 44}" font-size="11" fill="{INK3}" text-anchor="middle">prompt length, tokens (log scale)</text>')
    out.append(f'<text x="20" y="{(top + bot) / 2:.1f}" font-size="11" fill="{INK3}" text-anchor="middle" transform="rotate(-90 20 {(top + bot) / 2:.1f})">TTFT of the 8-prompt batch, seconds (log scale)</text>')
    kmap = {"AVX (kill switch)": "avx", "canonical AMX": "canon", "VNNI-K (2026-09-14 store)": "vnnik"}
    for name, series in scaling.items():
        k = kmap[name]
        pts = [(X(p), Y(series[p])) for p in xs]
        out.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="none" stroke="{KCOL[k]}" stroke-width="2"/>')
        for p, (x, yy) in zip(xs, pts):
            out.append(f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="5" fill="{KCOL[k]}" stroke="{SURF}" stroke-width="2"><title>{esc(name)}, prompt {p}: {series[p] / 1000:.2f} s</title></circle>')
        x, yy = pts[-1]
        dy = {"avx": -6, "canon": 4, "vnnik": 16}[k]
        out.append(f'<text x="{x + 12:.1f}" y="{yy + dy:.1f}" font-size="11" fill="{INK}">{esc(KSHORT[k])} {series[8192] / 1000:.1f} s</text>')
    # FPGA point at 1024: one square at the mean of the three builds, drawn to the right of the CPU dots
    x = X(1024) + 22
    fm = sum(fpga_1024_points.values()) / 3.0
    out.append(f'<rect x="{x - 6:.1f}" y="{Y(fm) - 6:.1f}" width="12" height="12" fill="{SURF}" stroke="{INK}" stroke-width="2"><title>FPGA attention, prompt 1024: AVX build {fpga_1024_points["AVX"] / 1000:.2f} s, canonical {fpga_1024_points["canonical AMX"] / 1000:.2f} s, VNNI-K {fpga_1024_points["VNNI-K"] / 1000:.2f} s (2026-09-16)</title></rect>')
    out.append(f'<text x="{x + 12:.1f}" y="{Y(fm) + 22:.1f}" font-size="11" fill="{INK}">square: FPGA attention, 3.15 to 3.20 s (three builds)</text>')
    # gap annotation
    gx1, gx2 = X(2048) - 40, right + 190
    out.append(f'<rect x="{gx1:.1f}" y="{top - 6}" width="{gx2 - gx1:.1f}" height="{bot - top + 6}" fill="none" stroke="{INK3}" stroke-dasharray="6 4"/>')
    out.append(f'<text x="{gx1 + 12:.1f}" y="{top + 14}" font-size="12" font-weight="600" fill="{INK}">FPGA attention: no qwen3-4b TTFT measured at these prompt lengths</text>')
    out.append(f'<text x="{gx1 + 12:.1f}" y="{top + 30}" font-size="11" fill="{INK2}">(Insufficient data; the measurement that closes the gap is in section 6)</text>')
    out.append('</svg>')
    return "\n".join(out)


# ---------------------------------------------------------------- tables
# issue 4500 block m1: runtron, 8 users, FPGA attention, CPU build varied (means, n = 3; per-rep not carried)
M1 = {
    2: dict(canon=3188.9, headoff=3207.1, vnni=3189.2, vnni2=3160.6, kill=3204.8),
    4: dict(canon=2333.4, headoff=2347.1, vnni=2260.3, vnni2=2227.3, kill=2191.7),
}


def dfstr(x):
    return "-" if x is None else f"{x:.1f}"


def pair_table():
    h = ['<div class="tw"><table class="num"><thead><tr><th>harness</th><th>setup</th><th>CPU kernel</th><th>CPU-attention TTFT, ms (n)</th><th>FPGA-attention TTFT, ms (n)</th><th>FPGA minus CPU, ms</th><th>percent of CPU</th><th>Welch t</th><th>Welch df</th><th>note</th></tr></thead><tbody>']
    for p in PAIRS:
        c, f = p["cpu"], p["fpga"]
        csd = f" +/- {f1(c['sd'])}" if c["sd"] is not None else ""
        fsd = f" +/- {f1(f['sd'])}" if f["sd"] is not None else ""
        h.append(f'<tr><td>{"CI harness" if p["group"] == "ci" else "runtron"}</td><td>{esc(p["setup"])}</td><td>{esc(KSHORT[p["kernel"]])}</td>'
                 f'<td>{f0(c["mean"])}{csd} ({c["n"]})</td><td>{f0(f["mean"])}{fsd} ({f["n"]})</td>'
                 f'<td>{p["delta_ms"]:+.0f}</td><td>{pct(p["pct"])}</td><td>{tstr(p["t"])}</td><td>{dfstr(p["df"])}</td><td>{esc(p["note"])}</td></tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)


def fpga_build_table():
    h = ['<div class="tw"><table class="num"><thead><tr><th>layout</th><th>tp</th><th>AVX build (nightly deb 3faba6d0, or runtron eb2de0265a)</th><th>canonical AMX build (deb 0594dc54, or runtron c7844ca2ce)</th><th>VNNI-K build (deb 29a8a547, or runtron ff680c8020)</th><th>VNNI-K build + kill switch</th><th>source</th></tr></thead><tbody>']
    h.append(f'<tr><td>whole 3bda, 4 engines x 2 users, CI harness</td><td>2</td><td>{f0(ci_whole_tp2["avx_fpga_night"]["mean"])} (nightly 09-18, remote client), {f0(ci_whole_tp2["avx_fpga_mimic"]["mean"])} (ci-mimic, saturated client), 13-night mean {NIGHT13_TP2[0]} +/- {NIGHT13_TP2[1]}</td><td>{f0(ci_whole_tp2["canon_fpga"]["mean"])} (canon-ci, client pressure 0 to 5 %)</td><td>{f0(ci_whole_tp2["vnnik_fpga"]["mean"])} (ci-mimic, client pressure 27 to 48 %, so an upper bound)</td><td>-</td><td>canon-ci, ci-mimic, nightly-0918.arm.json, nightly_stats.json</td></tr>')
    h.append(f'<tr><td>whole 3bda, 2 engines x 4 users, CI harness</td><td>4</td><td>{f0(ci_whole_tp4_fpga["avx_night"]["mean"])} (nightly 09-18), 13-night mean {NIGHT13_TP4[0]} +/- {NIGHT13_TP4[1]}</td><td>{f0(ci_whole_tp4_fpga["canon"]["mean"])}</td><td>{f0(ci_whole_tp4_fpga["vnnik"]["mean"])}</td><td>-</td><td>same</td></tr>')
    h.append(f'<tr><td>our half, 1 engine x 2 users, CI harness (issue 4500 block m6, n = 2)</td><td>2</td><td>{f0(m6_tp2["avx"]["mean"])}</td><td>-</td><td>{f0(m6_tp2["vnnik"]["mean"])}</td><td>{f0(m6_tp2["vnnik_kill"]["mean"])}</td><td>issue4500 m6/summary.md:5-8</td></tr>')
    h.append(f'<tr><td>our half, 1 engine x 4 users, CI harness (block m6, n = 2)</td><td>4</td><td>{f0(m6_tp4["avx"]["mean"])}</td><td>-</td><td>{f0(m6_tp4["vnnik"]["mean"])}</td><td>{f0(m6_tp4["vnnik_kill"]["mean"])}</td><td>issue4500 m6/summary.md:10-12</td></tr>')
    h.append(f'<tr><td>runtron, 8 users (wedperf-attr, n = 6)</td><td>2</td><td>{f0(rt_attr_tp2["avx_fpga"]["mean"])}</td><td>{f0(rt_attr_tp2["canon_fpga"]["mean"])}</td><td>{f0(rt_attr_tp2["vnnik_fpga"]["mean"])}</td><td>-</td><td>wedperf-attr summary.md:25-27</td></tr>')
    h.append(f'<tr><td>runtron, 8 users (wedperf-attr, n = 6)</td><td>4</td><td>{f0(rt_attr_tp4_fpga["avx"]["mean"])}</td><td>{f0(rt_attr_tp4_fpga["canon"]["mean"])}</td><td>{f0(rt_attr_tp4_fpga["vnnik"]["mean"])}</td><td>-</td><td>wedperf-attr summary.md:22-24</td></tr>')
    h.append(f'<tr><td>runtron, 8 users (issue 4500 block m1, 2026-09-18/19, n = 3)</td><td>2</td><td>-</td><td>{f0(M1[2]["canon"])} (c7844ca2ce), {f0(M1[2]["headoff"])} (PR 4424 code, layout off)</td><td>{f0(M1[2]["vnni"])} and {f0(M1[2]["vnni2"])} (two identical binaries)</td><td>{f0(M1[2]["kill"])}</td><td>issue4500 summary.md:9-14</td></tr>')
    h.append(f'<tr><td>runtron, 8 users (block m1, n = 3)</td><td>4</td><td>-</td><td>{f0(M1[4]["canon"])} (c7844ca2ce), {f0(M1[4]["headoff"])} (layout off)</td><td>{f0(M1[4]["vnni"])} and {f0(M1[4]["vnni2"])}</td><td>{f0(M1[4]["kill"])}</td><td>issue4500 summary.md:15-20</td></tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)


def sweep_table():
    h = ['<div class="tw"><table class="num"><thead><tr><th>prompt length</th><th>nightly deb, AVX, CPU attention</th><th>canonical AMX deb, CPU attention</th><th>AMX deb relative to AVX deb</th><th>FPGA attention</th></tr></thead><tbody>']
    for p, a, c in zip(sweep_prompts, sweep_avx, sweep_canon):
        fp = f"{f0(ci_whole_tp2['avx_fpga_night']['mean'])} (nightly deb), {f0(ci_whole_tp2['canon_fpga']['mean'])} (canonical AMX deb)" if p == 1024 else "not measured"
        h.append(f'<tr><td>{p}</td><td>{f0(a)}</td><td>{f0(c)}</td><td>{100 * (c - a) / a:+.0f} %</td><td>{fp}</td></tr>')
    h.append(f'<tr><td>8192, cold prefixes (check cell, 1 pass)</td><td>not measured</td><td>{f0(sweep_canon_cold_8192)}</td><td>-</td><td>not measured</td></tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)


def scaling_table():
    h = ['<div class="tw"><table class="num"><thead><tr><th>prompt length</th><th>AVX (kill switch)</th><th>canonical AMX</th><th>VNNI-K (2026-09-14 store)</th><th>canonical AMX relative to AVX</th><th>FPGA attention</th></tr></thead><tbody>']
    for p in (1024, 2048, 8192):
        a, c, v = scaling["AVX (kill switch)"][p], scaling["canonical AMX"][p], scaling["VNNI-K (2026-09-14 store)"][p]
        fp = "3,191 (AVX build), 3,195 (canonical), 3,150 (VNNI-K), 2026-09-16" if p == 1024 else "not measured"
        h.append(f'<tr><td>{p}</td><td>{f0(a)}</td><td>{f0(c)}</td><td>{f0(v)}</td><td>{100 * (c - a) / a:+.0f} %</td><td>{fp}</td></tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)


# ---------------------------------------------------------------- section 5 variants
def section5_gap():
    H = []
    H.append("<h2>5. Longer prompts: measured for CPU attention, not for FPGA attention</h2>")
    H.append(f'<div class="fig">{fig3()}<p class="cap">Figure 3. Lines: runtron, CPU attention, tp2, 8 prompts in one batch, 3 repetitions per point [{rel_ref(SCALING_REF)}]. Square at prompt 1024: the mean of the FPGA-attention runs of 2026-09-16 with the three kinds of build (3.15 to 3.20 s, n = 2 to 6). No FPGA-attention run of qwen3-4b exists at any other prompt length.</p></div>')
    H.append(scaling_table())
    H.append('<p class="cap">runtron TTFT in ms of the 8-prompt batch. Cold prompts (Moby Dick chapters, one per user, not seen before by the engine), so no prefix-cache effect.</p>')
    H.append("<h3>The CI-harness prompt-length series of 2026-09-20 (both arms with CPU attention)</h3>")
    H.append(sweep_table())
    H.append('<p class="cap">Client-side TTFT in ms, whole machine, 4 tp2 engines x 2 users, mean of 3 passes [exec/results/q4b-swattn-20260919/summary.txt:3-11]. Above prompt 1024 the same conversation seeds are reused. So 12 to 50 % of each request\'s prompt tokens are served from rinzler\'s prefix cache (1.2 % at 1024) [exec/results/q4b-swattn-20260919/summary.json, cache_hit_pct per pass]. The TTFT is therefore lower than a cold prefill. The cold check cell at 8192 took 12,743 ms against the warm 7,145 ms [exec/results/q4b-swattn-20260919/RUNBOOK.md:33-39].</p>')
    H.append('<div class="gap"><p><b>Insufficient data.</b> The question "is FPGA-attention prefill better at long prompts" cannot be answered from the local files. Every qwen3-4b run at prompt 1536 to 8192 forced CPU attention. Every run with FPGA attention used prompt 1024. This was checked by a search over all 56 result directories, the logs and the reports: 274 files carry the "HW attention enabled" line for qwen3-4b, all at prompt 1024.</p>')
    H.append('<p>What the code says about the shape of the two curves, without deciding the winner: the CPU AMX path scores one (query, page) pair per kernel call and reuses each page over all queries of the forward, so its cost grows with the square of the prompt length. The FPGA path scores at most 32 queries per pass and re-reads the resident K/V on every pass, so it is also quadratic, plus a host cost linear in the prompt length for staging and DMA. The per-pass device time decides the prompt length at which the two curves cross. It is not in the code (hypothesis to test, section 8).</p></div>')
    return H


def section5_measured(agg):
    rows6 = FS.load()
    S = FS.summary(agg)
    def m(arm, p, key):
        return FS.mean(agg.get(arm, {}).get(p, {}).get(key, []))
    def n(arm, p, key):
        return len(agg.get(arm, {}).get(p, {}).get(key, []))
    def wt(p):
        a = [r["ttft_harness_ms"] for r in rows6 if r["arm"] == "canon" and r["prompt_length"] == p and not r["cold"]]
        b = [r["ttft_harness_ms"] for r in rows6 if r["arm"] == "fpgacanon" and r["prompt_length"] == p and not r["cold"]]
        return FS.welch(a, b)
    wts = {p: wt(p) for p in (1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192)}
    wt_str = ", ".join(f"{p}: {t:+.1f}" for p, t in wts.items() if t is not None)
    wt_res = ", ".join(str(p) for p, t in wts.items() if t is not None and abs(t) > 4.3)
    wt_weak = ", ".join(str(p) for p, t in wts.items() if t is not None and abs(t) <= 4.3)
    def pc(x, y):
        return f"{100 * (x - y) / y:+.0f} %"
    H = []
    H.append("<h2>5. Longer prompts: the measured FPGA curve (campaign q4b-fpga-20260921)</h2>")
    n_fb = len({t for p in agg.get("fpgabase", {}).values() for t in p["warm_tags"] + p["cold_tags"]})
    n_fc = len({t for p in agg.get("fpgacanon", {}).values() for t in p["warm_tags"] + p["cold_tags"]})
    uneven = [r for r in rows6 if r["arm"] in ("fpgabase", "fpgacanon") and r.get("engine_requests") and any(v is None for v in r["engine_requests"].values())]
    uneven_txt = "; ".join(f"{FS.ARM_LABEL[r['arm']]} pass {FS.pass_no(r['tag'])} at prompt {r['prompt_length']} (spread {' / '.join('not recorded' if v is None else str(v) for v in r['engine_requests'].values())}, {r.get('caddy_health_events') or 0} Caddy health events, {r['ttft_harness_ms']:,.0f} ms)" for r in uneven)
    n_fpga_cells = sum(1 for r in rows6 if r["arm"] in ("fpgabase", "fpgacanon") and not r["cold"]) + sum(1 for r in rows6 if r["arm"] in ("fpgabase", "fpgacanon") and r["cold"])
    H.append(f'<p>Measured on the whole of delphi-3bda in the nightly layout (platformd 0.11, 4 tp2 engines behind the test proxy, 2 users per engine, 1536 generated tokens) with the same harness, prompts and cells as the 2026-09-20 CPU-attention series, in two windows: 2026-09-21 22:35 to 2026-09-22 01:17 UTC (pass 1 and the first cold cells) and 2026-09-22 13:29 to 16:25 UTC (passes 2 and 3 and the second cold cells). FPGA-attention driver runs: {n_fb} with the nightly deb, {n_fc} with the canonical AMX deb (three 9-cell passes and four single cold cells each). The CPU-attention arms are the 2026-09-20 series (3 passes each) plus one canonical pass of 2026-09-22 and the cold check cell of 2026-09-19, not re-run further (jhan). Every engine\'s environment was checked after each provisioning: no USE_HW_ATTN=0 in the FPGA arms, exactly one in the CPU arms. {n_fpga_cells - len(uneven)} of the {n_fpga_cells} FPGA-arm cells spread their 80 requests 20 / 20 / 20 / 20 over the four engines. {len(uneven)} did not, because one engine restarted during the cell (its request counters start again from zero and its card is nearly empty afterwards): {uneven_txt}. Those cells stay in the means, and pass 1 is the only pass without such a restart on either arm. The canonical CPU pass of 2026-09-22 has the same kind of exception: engine default-1 restarted before its prompt-3000 cell (spread 22 / not recorded / 20 / 22, 3 Caddy health events, 2,296 ms). That cell stays in the n = 4 mean and is flagged in the table caption. The measurements took three launches: the first ran fpgabase pass 1 and stopped at the switch to the canonical deb (an idle-test bug in dut.sh, see the runbook\'s incident log), the relaunch at 23:37 UTC ran fpgacanon pass 1, the canonical CPU pass and the first four cold cells, and the third launch after the 2026-09-22 nightly ran passes 2 and 3 of both FPGA arms and the second cold cells. The binary check of every run shows the intended deb.</p>')
    H.append(f'<div class="fig">{FS.fig(agg)}<p class="cap">Figure 3. Client-side TTFT against prompt length for the four arms, mean over the passes of each cell. Inside a pass only the prompt-1024 cell meets fresh engines. The later cells reuse the same conversation seeds, and 12 to 54 % of their prompt tokens come from the prefix cache, so the lines above 1024 are warm numbers. The end labels are the 8192 warm means. Squares mark cold cells (single-cell driver runs on fresh engines, mean of two runs for the FPGA arms): the FPGA arms at 4096 and 8192, and the canonical CPU arm at 8192 (the 2026-09-19 check cell, one run).</p></div>')
    # cold 8192
    c_cpu, c_fc, c_fb = m("canon", 8192, "cold"), m("fpgacanon", 8192, "cold"), m("fpgabase", 8192, "cold")
    w_b, w_c, w_fc, w_fb = m("base", 8192, "warm"), m("canon", 8192, "warm"), m("fpgacanon", 8192, "warm"), m("fpgabase", 8192, "warm")
    H.append("<ul>")
    if c_cpu and c_fc:
        H.append(f"<li><b>Cold prefill at prompt 8192 (fresh engines, no prefix cache).</b> AMX kernel on the CPU {c_cpu:,.0f} ms (the 2026-09-19 check cell, n = 1) against FPGA attention {c_fc:,.0f} ms with the AMX build and {c_fb:,.0f} ms with the AVX build (n = {n('fpgacanon', 8192, 'cold')} each, the two cold runs of one arm 17 ms apart for the AMX build and 41 ms for the AVX build). The FPGA prefill is {c_cpu / c_fc:.1f}x faster ({pc(c_fc, c_cpu)}). The CPU build behind the FPGA changes the cold number by {pc(c_fc, c_fb)}. No cold AVX-CPU cell exists at 8192. The CPU cell ran under platformd 0.10.7 on 2026-09-19, the FPGA cells under 0.11.0 on 2026-09-22. At 1024 the 2026-09-22 canonical pass reproduces the 0.10.7 value within 1 % (518 against 516 to 518 ms), so the layout change is not expected to move the 8192 cell either (hypothesis: no same-layout cold CPU cell at 8192 exists).</li>")
    c4_fc, c4_fb = m("fpgacanon", 4096, "cold"), m("fpgabase", 4096, "cold")
    if c4_fc:
        H.append(f"<li><b>Cold prefill at prompt 4096.</b> FPGA attention {c4_fc:,.0f} ms (AMX build) and {c4_fb:,.0f} ms (AVX build), n = {n('fpgacanon', 4096, 'cold')} each. No cold CPU-attention cell exists at 4096 (no single-cell CPU-attention run at 4096 was made). The warm canonical CPU cell is {m('canon', 4096, 'warm'):,.0f} ms with 33 to 38 % prefix-cache hits, so the cold CPU value is higher than that (est.).</li>")
    if w_b and w_c and w_fc:
        H.append(f"<li><b>Warm prefill at prompt 8192 (the passes\' last cell).</b> AVX on the CPU {w_b:,.0f} ms, AMX on the CPU {w_c:,.0f} ms ({w_b / w_c:.1f}x faster than AVX, the 2x jhan recalled), FPGA attention {w_fc:,.0f} ms with the AMX build ({w_c / w_fc:.1f}x faster than AMX on the CPU) and {w_fb:,.0f} ms with the AVX build. From AVX on the CPU to FPGA attention with the AMX build the warm prefill at 8192 shrinks {w_b / w_fc:.1f}x.</li>")
    d = S.get("fpgacanon", {}).get("warm", {})
    if d:
        lo, hi = min(v["pct"] for v in d.values()), max(v["pct"] for v in d.values())
        parts = ", ".join(f"{p}: {v['pct']:+.0f} %" for p, v in sorted(d.items()) if p != 1024)
        H.append(f"<li><b>FPGA against CPU, canonical AMX deb, per prompt length (warm cells, FPGA minus CPU in percent of CPU).</b> {parts}. At 1024 (cold) {m('fpgacanon', 1024, 'cold'):,.0f} against {m('canon', 1024, 'cold'):,.0f} ms ({pc(m('fpgacanon', 1024, 'cold'), m('canon', 1024, 'cold'))}). The FPGA is faster at every prompt length from 2048 up. The gap is largest at the longest prompts ({d[7168]['pct']:+.0f} % at 7168, {d[8192]['pct']:+.0f} % at 8192) and is not steady in between ({d[3000]['pct']:+.0f} % at 3000, {d[4096]['pct']:+.0f} % at 4096, {d[5120]['pct']:+.0f} % at 5120). The warm cells at 4096 to 6144 are hybrids of FPGA and CPU attention in every pass (the card\'s K/V space was exhausted, subsection below), the 7168 cells in 2 of 6 pass-cells, and the 8192 cells from round 6 to 8 of 10 on. So the clean long-prompt comparison is the cold one: {m('fpgacanon', 8192, 'cold'):,.0f} against {m('canon', 8192, 'cold'):,.0f} ms at 8192. With three FPGA passes and four CPU passes per warm cell, the Welch t of FPGA against CPU is {wt_str}: resolved (|t| above 4.3, the two-sided 5 % bound at 2 degrees of freedom) at {wt_res}, weak at {wt_weak}.</li>")
    d = S.get("fpgabase", {}).get("warm", {})
    if d:
        parts = ", ".join(f"{p}: {v['pct']:+.0f} %" for p, v in sorted(d.items()) if p != 1024)
        H.append(f"<li><b>FPGA against CPU, nightly deb (AVX), per prompt length (warm cells).</b> {parts}. At 1024 (cold) {m('fpgabase', 1024, 'cold'):,.0f} against {m('base', 1024, 'cold'):,.0f} ms ({pc(m('fpgabase', 1024, 'cold'), m('base', 1024, 'cold'))}). This is the pair the nightly would see if it switched qwen3-4b from FPGA attention to CPU attention without AMX: prefill would take 1.2x (1024) to 2.6x (7168) longer. The nightly-deb FPGA value at 1024 ({m('fpgabase', 1024, 'cold'):,.0f} ms, mean of three passes that agree within 2 ms, platformd 0.11) is 25 to 45 ms above the same cell\'s history (528 ms on 2026-09-18, 509.5 +/- 7.2 ms over 13 nights). The agreement across passes makes it a systematic offset of this layout and client, not an outlier (hypothesis: the test proxy on port 80 or the client host; not measured). With the history values the 1024 ratio is 1.3x.</li>")
    H.append("</ul>")
    c6 = {(c["prompt"], c["kind"]): c for c in FS.amx_vs_avx_rows(rows6)}
    wl = [c6[(p, "warm")] for p in (4096, 5120, 6144, 7168, 8192)]
    wl_lo, wl_hi = min(c["ttft_pct"] for c in wl), max(c["ttft_pct"] for c in wl)
    wl_all = [v for c in wl for v in c["ttft_pcts"]]
    tk_lo, tk_hi = min(c["tok_pct"] for c in wl), max(c["tok_pct"] for c in wl)
    c2k, c15, c30, c71 = c6[(2048, "warm")], c6[(1536, "warm")], c6[(3000, "warm")], c6[(7168, "warm")]
    cold6 = [c6[k] for k in ((1024, "cold"), (4096, "cold"), (8192, "cold")) if k in c6]
    hb = hbm_load()
    def share_new(p):
        v = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(hb, arm, p, "warm") if c["lose"] and c.get("share_new_pct") is not None]
        return (min(v), max(v)) if v else (None, None)
    s45 = share_new(4096) + share_new(5120); s61 = share_new(6144)
    cpu_gain = {p: 100.0 * (m("canon", p, "warm") - m("base", p, "warm")) / m("base", p, "warm") for p in (4096, 5120, 6144)}
    # pre-cell AMX probe of the canonical FPGA arm: windows grouped by the state of the card (gap warnings before the cell)
    gaps = {(g["tag"], g["before_prompt"]): g["lose"] for g in (hb.get("gaps", []) if hb else [])}
    pr_fresh, pr_clean, pr_full = [], [], []
    for r in rows6:
        if r["arm"] != "fpgacanon" or r.get("amx_busy_cycles") is None:
            continue
        v = r["amx_busy_cycles"] / 1e9
        (pr_fresh if r["cold"] else (pr_clean if gaps.get((r["tag"], r["prompt_length"]), 0) == 0 else pr_full)).append(v)
    H.append(f'<p class="hyp">Why the AMX build helps the warm cells under FPGA attention far more than the cold cells: two candidate mechanisms, neither proven for every cell. The measurements first (means of the per-pass deltas over 3 paired passes per cell, section 6). The AMX build lowers the warm TTFT by {r0(wl_hi)} to {r0(wl_lo)} % from prompt 4096 up, and in every one of the {len(wl_all)} paired passes ({min(wl_all):+.0f} to {max(wl_all):+.0f} %). Per uncached prompt token (the two arms did not see the same prefix-cache share in a paired cell) the same gains are {r0(tk_hi)} to {r0(tk_lo)} %. At 2048 it lowers the TTFT by {r0(c2k["ttft_pct"])} % on average ({", ".join(f"{v:+.1f}" for v in c2k["ttft_pcts"])} % per pass). At 1536 and 3000 the means are {c15["ttft_pct"]:+.1f} and {c30["ttft_pct"]:+.1f} %, with Welch t {c15["t_ttft"]:+.1f} and {c30["t_ttft"]:+.1f}, so not resolved. In the cold cells it lowers TTFT by {r0(max(c["ttft_pct"] for c in cold6))} to {r0(min(c["ttft_pct"] for c in cold6))} % (n = 2 to 3 per cell). Mechanism 1, measured as a co-occurrence (next subsection): in every pass the 4096, 5120 and 6144 cells ran with the card\'s K/V space exhausted from round 1 until 60 to 99 % of the cell. At 4096 and 5120 nearly every new shard placement failed ({r0(min(s45))} to {r0(max(s45))} % of the new placements, est.), at 6144 {r0(s61[0])} to {r0(s61[1])} %. So in those cells both arms scored nearly all new context on the CPU, where the AMX kernel replaces the AVX loop. The AMX gain there ({r0(c6[(4096, "warm")]["ttft_pct"])} % at 4096, {r0(c6[(5120, "warm")]["ttft_pct"])} % at 5120) is then the CPU-attention gain in another guise: the canonical CPU arm beats the AVX CPU arm by {r0(cpu_gain[4096])} % and {r0(cpu_gain[5120])} % in the same warm cells. Mechanism 1 cannot explain the 2048 cells. They had no exhaustion warning in any pass, no earlier cell of any pass had one either, and they still read {c2k["ttft_pct"]:+.0f} % on average. The 7168 cells and the first rounds of the 8192 cells are not counter-examples: a shard that fell back keeps running on the CPU for as long as the prefix cache keeps its tree node, and it warns only once, when it is created [h/tron/shard.hpp:8-31; src/tron/gof.cpp:70-103; h/tron/scheduler/full.hpp:2400-2428, Note "Retrying a degraded shard"]. A request that inherits such a shard through the prefix cache runs part of its attention on the CPU without a new warning. So the absence of new warnings at 7168 ({", ".join(f"{v:+.1f}" for v in c71["ttft_pcts"])} % in the three pairs) and in rounds 1 to 6 at 8192 does not show the absence of CPU attention there. Mechanism 2, a hypothesis: in a warm request the K/V pages (64-token blocks) that come from the prefix cache are scored on the CPU while the card\'s copy lags (the DMA-lag rule of section 4), and the AMX kernel covers that work. Evidence in the same direction, not proof. The pre-cell AMX probe (Words used here) counts AMX-busy cycles in one 20 s window before each cell. More cycles mean more attention work ran through the AMX kernel. On fresh engines it read {min(pr_fresh):.1f} to {max(pr_fresh):.1f} billion ({len(pr_fresh)} windows, canonical FPGA arm, all three passes and the cold cells). In the warm windows without an exhaustion warning it read {min(pr_clean):.1f} to {max(pr_clean):.1f} billion ({len(pr_clean)} windows). In the windows where the card was full it read {min(pr_full):.1f} to {max(pr_full):.1f} billion ({len(pr_full)} windows). The groups overlap at about 21 billion, so the probe separates fresh from warm engines but not a clean warm card from a full one. It measures its own request streams, not the cell. Test that would settle it: a perfetto trace of one warm 2048 request, AMX build against kill switch. The per-card fallback counter, recorded per cell since the third launch, confirms the exhaustion counts but cannot separate the two mechanisms.</p>')
    H.extend(hbm_subsection())
    H.append("<h3>The record: every cell</h3>")
    H.append(FS.table(agg))
    c3000_low = statistics.mean(sorted(agg["canon"][3000]["warm"])[:2])
    H.append(f'<p class="cap">Client-side TTFT in ms, harness mean over 8 users x 10 rounds. "warm mean (passes)" = mean over the passes with the sd and the pass count. "cold" = single-cell driver runs (and the 2026-09-19 check cell for the canonical CPU arm at 8192). The CPU-attention columns come from the 2026-09-20 campaign (3 passes) plus the canonical pass of 2026-09-22. In the canonical 3000 row the two highest values (2,056 ms in the 2026-09-20 pass 1 and 2,296 ms in the 2026-09-22 pass) are cells with an uneven proxy spread (one engine unreported, 2 and 3 Caddy health events). Without them the row reads {c3000_low:,.0f} ms (n = 2) and the FPGA-vs-CPU figure at 3000 is {pc(m("fpgacanon", 3000, "warm"), c3000_low)} instead of {pc(m("fpgacanon", 3000, "warm"), m("canon", 3000, "warm"))}. Source: exec/prefill-amx-vs-fpga-20260921/fpga-campaign-rows.json (ingest_fpga.py over the perf.json files).</p>')
    tps_fc8k = statistics.mean([r["tps_mean"] for r in rows6 if r["arm"] == "fpgacanon" and r["prompt_length"] == 8192 and not r["cold"]])
    H.append(f'<p>Reading. Both the AMX kernel and the FPGA remove the quadratic attention cost that the AVX path pays, and the FPGA removes more of it: at 8192 the AMX kernel halves the AVX prefill and the FPGA halves it again. The CPU build moves the cold FPGA prefill by 2 to 8 % (the AMX build is faster in all seven cold pass-pairs: n = 3 at 1024, n = 2 at 4096 and 8192). So the card sets most of the cold number, not all of it. The warm FPGA numbers at 4096 to 6144 are hybrids of FPGA and CPU attention in every pass (the card\'s K/V space was exhausted, subsection above), the 7168 numbers in 2 of 6 pass-cells, and the 8192 numbers from round 6 to 8 of 10 on. So the cold cells are the ones to quote for long prompts. Decode TPS in the same cells stays in the FPGA\'s favour (at 8192: {tps_fc8k:.0f} TPS with FPGA attention and the AMX build, mean of three passes, against 60 TPS with AMX on the CPU).</p>')
    return H


HBM_JSON = os.path.join(HERE, "hbm-exhaustion-cells.json")


def r0(x):
    """Magnitude rounded half up to a whole number (48.5 -> 49), for ranges quoted in prose."""
    return int(math.floor(abs(x) + 0.5))


def rs(lo, hi, fmt="{:.0f}"):
    """'a to b' or just 'a' when both ends print the same."""
    a, b = fmt.format(lo), fmt.format(hi)
    return a if a == b else f"{a} to {b}"


def hbm_load():
    return json.load(open(HBM_JSON)) if os.path.exists(HBM_JSON) else None


def hbm_group(d, arm, prompt, kind):
    """The cells of one arm at one prompt length, warm (inside a pass) or cold (single-cell runs), sorted by tag."""
    return sorted([c for c in d["cells"] if c["tag"].startswith(arm) and c["prompt"] == prompt and (("cold" in c["tag"]) == (kind == "cold"))], key=lambda c: c["tag"])


def hbm_subsection():
    """The card's K/V space ran out in the warm long-prompt cells: counts per cell from the engine journal (hbm_cells.py), aggregated per arm and prompt over the passes."""
    d = hbm_load()
    if not d:
        return []
    gaps = d.get("gaps", [])
    gap_after = {}
    for g in gaps:
        if g["lose"]:
            gap_after.setdefault(g["after_prompt"], []).append(g["lose"])
    n_gap = sum(g["lose"] for g in gaps)
    n_passes = len({c["tag"] for c in d["cells"] if c["tag"].startswith("fpga") and "pass" in c["tag"]})
    n_cold = len({c["tag"] for c in d["cells"] if c["tag"].startswith("fpga") and "cold" in c["tag"]})
    av = d.get("avail_counts", {})
    MiB = 2 ** 20
    H = []
    H.append("<h3>The card ran out of K/V space in the warm long-prompt cells</h3>")
    H.append(f'<p>The engine journal (the systemd log of the four rinzler engines) of the two campaign windows (2026-09-21 22:30 to 2026-09-22 01:30 UTC and 2026-09-22 13:00 to 16:30 UTC) holds {d["total_lose"]:,} warnings of the form "HBM bypass space exhausted, caller degrades to SW attention" followed by "shard base tok_ix N: 36 of 36 slots lose HW attention" [exec/results/q4b-fpga-20260921/hbm-journal-20260921.txt, hbm-journal-20260922.txt]. HBM is the card\'s memory. A shard is the card-side copy of 1024 tokens of one request\'s K/V, placed on one of the engine\'s two cards. One warning means one new shard could not be placed on its card, and that shard\'s attention ran on the CPU instead. A shard warns once, when it is created. It keeps its CPU-attention state for as long as the prefix cache keeps its tree node, and a later request that inherits it through the prefix cache runs that part of its attention on the CPU without a new warning [h/tron/shard.hpp:8-31; h/tron/scheduler/full.hpp:2400-2428]. So the counts below measure new failures, not the total share of CPU attention in a cell. {d["inside_cells"]:,} warnings fall inside cells (between the harness\'s start and end time of a cell). The other {n_gap:,} fall in the 30 s gaps between cells of the {n_passes} FPGA passes: after the 3000, 4096 and 5120 cells in every pass ({len(gap_after.get(3000, []))}, {len(gap_after.get(4096, []))} and {len(gap_after.get(5120, []))} of {n_passes} passes), after the 6144 cell in {len(gap_after.get(6144, []))} passes, never after 7168. In those gaps our campaign driver (the script that provisions the engines and runs the harness cells) runs the pre-cell AMX probe, which keeps 4 request streams of its own running for 20 s (Words used here). The gap warnings name only shard bases 0 and 1024. So they are the probe\'s own requests, which could not place even their first shard. They show that the card was already full when each 3000 cell ended and stayed full to the start of the 6144 cell. The first warning of the first window is at 22:45:30 UTC, 12 s after the prompt-3000 cell of the first FPGA pass ended and 19 s before the first round of its prompt-4096 cell. None of the warnings fall in the CPU-attention pass or in the {n_cold} cold cells. None appear in any earlier FPGA-attention run at prompt 1024: 0 warnings in every runtron log of the issue-4500, wedperf, wedperf-attr and vnnik4-models campaigns (358 files) and in the engine logs of the p0perf-20260913 CI cells.</p>')
    H.append('<div class="tw"><table class="num"><thead><tr><th>cell</th><th>passes</th><th>warnings per pass</th><th>fallback counter per pass (recorded from the third launch on)</th><th>share of the cell\'s new shard placements (est.)</th><th>first warning (round of 10)</th><th>last warning (% of the cell)</th><th>free space after the cell, lowest card (MiB)</th><th>reading</th></tr></thead><tbody>')
    def fmt_list(xs, f="{}"):
        return ", ".join("-" if x is None else f.format(x) for x in xs)
    for arm in ("fpgabase", "fpgacanon"):
        for kind in ("warm", "cold"):
            for p in (1024, 1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192):
                cs = hbm_group(d, arm, p, kind)
                if not cs:
                    continue
                w = [c["lose"] for c in cs]
                fr = [c["first_round"] for c in cs if c["lose"]]
                lp = [c["last_pct"] for c in cs if c["lose"]]
                if not any(w) and kind == "cold":
                    reading = "clean: fresh engines, every shard on the card"
                elif not any(w) and p <= 3000:
                    reading = "clean: every shard on the card (no earlier exhaustion in the pass)"
                elif not any(w):
                    reading = "no new shard failed; inherited degraded shards not measured"
                elif all(w) and all(x == 1 for x in fr) and min(lp) >= 95:
                    reading = "exhausted through the whole cell in every pass"
                elif all(w) and all(x == 1 for x in fr):
                    reading = f"exhausted from round 1 until {rs(min(lp), max(lp))} % of the cell"
                elif not all(w):
                    reading = f"new shards failed in {sum(1 for x in w if x)} of {len(w)} passes (from round {rs(min(fr), max(fr))}, until {rs(min(lp), max(lp))} % of the cell), on the engine that had restarted earlier in that pass"
                else:
                    reading = f"clean of new failures until round {rs(min(fr) - 1, max(fr) - 1)}, exhausted after"
                sh = [c["share_new_pct"] for c in cs if c["lose"] and c.get("share_new_pct") is not None]
                share = "-" if not sh else f"{rs(min(sh), max(sh))} %"
                H.append(f'<tr><td>{esc(FS.ARM_LABEL.get(arm, arm))}, prompt {p}, {kind}</td><td>{len(cs)}</td><td>{fmt_list(w)}</td><td>{fmt_list([c.get("fallback_counter") for c in cs])}</td><td>{share}</td><td>{fmt_list([c["first_round"] for c in cs])}</td><td>{fmt_list([c["last_pct"] for c in cs])}</td><td>{fmt_list([None if c.get("free_min_after") is None else round(c["free_min_after"] / MiB) for c in cs], "{:,}")}</td><td>{reading}</td></tr>')
    H.append('</tbody></table></div>')
    H.append('<p class="cap">Passes in tag order (pass 1, 2, 3 for warm cells, the two single-cell runs for cold cells). One warning per new shard per engine (a shard sits on one card). Fallback counter = the engines\' sw_fallback_total FUSE stat, summed over the 4 engines x 2 cards, as the difference across the cell. It is recorded from the third launch on (passes 2 and 3 and the second cold cells); a dash = not recorded. Share (est.) = warnings divided by the cell\'s new shard placements, est. per request as ceil((prompt tokens not served from the prefix cache + 1536 generated tokens) / 1024), summed over the 80 requests from the harness\'s usage data. Values above 100 % mean the estimate of new placements is low (the probe\'s own requests between cells are not in it). First warning = the round (of 10) in which the first warning of the cell fell. Last warning = its position as a percentage of the cell\'s wall time. Free space = the allocator\'s free_total after the cell on the card with the least, in MiB (56 MiB = 59,113,472 B = the residue of a full card). Source: exec/prefill-amx-vs-fpga-20260921/hbm-exhaustion-cells.json (hbm_cells.py maps the journal lines and the recorded counters onto the perf.json cell windows).</p>')
    fb = [c["free_before_min"] for c in d["cells"] if c["tag"].startswith("fpga") and c.get("free_before_min") and (c["prompt"] == 1024 or "cold" in c["tag"])]
    fbx = [c["free_before_max"] for c in d["cells"] if c["tag"].startswith("fpga") and c.get("free_before_max") and (c["prompt"] == 1024 or "cold" in c["tag"])]
    fr_lo, fr_hi = min(fb) / 1e9, max(fbx) / 1e9
    cap_gb = 2 ** 35 / 1e9
    # cells whose exhaustion lasted to the end of the cell vs cells where the space came free before the end
    ended_full = [c for c in d["cells"] if c["tag"].startswith("fpga") and c["lose"] and c.get("free_min_after") and c["last_pct"] >= 94]
    ended_free = [c for c in d["cells"] if c["tag"].startswith("fpga") and c["lose"] and c.get("free_min_after") and c["last_pct"] < 94]
    H.append(f'<p>What the card holds (tron source at 30c4ac82cb, read 2026-09-22, and the recorded counters). The card-side K/V allocator (the code that hands out card memory to shards) manages one 1 GiB address range, fixed at compile time. Every allocation occupies that range on each of the card\'s 32 memory channels (the card\'s independent memory ports). So a card offers 32 GiB of K/V space, which is what the engines\' FUSE stats report (FUSE = Filesystem in Userspace, the file-like interface through which an engine exposes its counters; capacity 34,359,738,368 bytes on every device). The FPGA weights share that space. One 1024-token shard of qwen3-4b (36 layers) takes 4.5 MiB per channel, which is 144 MiB per card. If the weights took none of the space, a card would hold 227 shards (1 GiB / 4.5 MiB), about 232,000 tokens (est.). The recorded free space gives the real figure: before the first cell of each third-launch run, on freshly provisioned engines that had served only the harness\'s warm-up requests, the allocator reported {fr_lo:.1f} to {fr_hi:.1f} GB free per card (8 runs x 8 cards) out of {cap_gb:.1f} GB. So the weights and fixed allocations take about {cap_gb - fr_hi:.1f} to {cap_gb - fr_lo:.1f} GB per card, and a card holds about {fr_lo * 1e9 / (144 * MiB):.0f} to {fr_hi * 1e9 / (144 * MiB):.0f} shards, roughly {int(fr_lo * 1e9 / (144 * MiB)) * 1024 // 1000:,},000 to {int(fr_hi * 1e9 / (144 * MiB)) * 1024 // 1000:,},000 tokens (est.: the warm-up requests\' shards are counted as used). A shard is released only when the host prefix cache evicts its tree node (the prefix cache stores prompt prefixes as a tree, one node per stored prefix). A request ending does not release its shard. Every warning names the largest free block at that moment: 0x3000 (12 KiB) on the lower-numbered card of every engine and 0x5800 (22 KiB) on the other ({av.get("0x3000", 0):,} and {av.get("0x5800", 0):,} lines), constant through both windows. In every recorded pass-cell that was still exhausted when it ended (last warning at 94 % of the cell or later: {len(ended_full)} pass-cells at 4096, 5120, 6144 and 8192) the free_total after the cell is 59,113,472 B (56.4 MiB) on the card with the least. 56 MiB free in blocks of at most 22 KiB, against 144 MiB per shard, means the space was full. Fragmentation played no part there. In the {len(ended_free)} recorded pass-cells where the space came free before the cell ended (6144 and 7168 in passes 2 and 3) the reading after the cell is {min(c["free_min_after"] for c in ended_free) / 1e9:.1f} to {max(c["free_min_after"] for c in ended_free) / 1e9:.1f} GB, and the constant largest-free-block value in their warning lines is the only evidence about the state at warning time. No environment variable or config changes the space or the shard size. The fallback counter (sw_fallback_total per device), recorded per cell from the third launch on, equals the journal\'s warning count in every cell [src/pos/driver.cpp:884-894; src/tron/gof.cpp:34-39, 64-103; h/pos/device.hpp:459-479; h/tron/shard.hpp:8-31; src/pos/alloc.cpp:350-387; h/pos/alloc.hpp:87-93; src/rinzler.cpp:4258-4283].</p>')
    def free_after(p):
        v = [c["free_min_after"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, p, "warm") if c.get("free_min_after")]
        return (min(v) / 1e9, max(v) / 1e9) if v else (None, None)
    f10, f15, f20, f30 = free_after(1024), free_after(1536), free_after(2048), free_after(3000)
    c71 = [c for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 7168, "warm")]
    f71_clean = [c["free_min_after"] / 1e9 for c in c71 if c["lose"] == 0 and c.get("free_min_after")]
    n81 = [c for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 8192, "warm") if c["lose"]]
    sh_ex = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120) for c in hbm_group(d, arm, p, "warm") if c.get("share_new_pct") is not None]
    sh61 = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 6144, "warm") if c.get("share_new_pct") is not None]
    lp61 = [c["last_pct"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 6144, "warm") if c["lose"]]
    H.append(f'<p>Reading. Inside a pass the harness reuses the same conversation seeds (the fixed prompt texts each simulated user starts from). The prefix cache therefore keeps the K/V of earlier requests alive. Their shards stay on the card as well. The recorded free space shows the fill (passes 2 and 3, the card with the least): {rs(*f10)} GB after the 1024 cell, {rs(*f15)} GB after 1536, {rs(*f20)} GB after 2048 and {rs(*f30, fmt="{:.1f}")} GB after 3000. By the end of the 3000 cell the card is full: the probe requests in the gap before 4096 could not place their first shard, in every pass. In the 4096 and 5120 cells the space stayed full through the whole cell in every pass (first warning in round 1, last at 97 to 99 % of the cell, {rs(min(sh_ex), max(sh_ex))} % of the cells\' new shard placements failed, est.). In the 6144 cells it was full from round 1 until {rs(min(lp61), max(lp61))} % of the cell ({rs(min(sh61), max(sh61))} % of the new placements failed). In the 7168 cells no new shard failed in {sum(1 for c in c71 if c["lose"] == 0)} of the {len(c71)} pass-cells ({rs(min(f71_clean), max(f71_clean), fmt="{:.1f}")} GB free after the cell in the recorded ones). In the other {sum(1 for c in c71 if c["lose"])} ({", ".join(str(c["lose"]) for c in c71 if c["lose"])} warnings) every warning came from the one engine that had restarted earlier in that pass (fpgabase pass 2 at 2048, fpgacanon pass 3 at 1536), whose card filled later than the others (hypothesis, from the per-engine counters). In the 8192 cells new shards failed again from round {rs(min(c["first_round"] for c in n81), max(c["first_round"] for c in n81))} ({rs(min(c["share_new_pct"] for c in n81), max(c["share_new_pct"] for c in n81))} % of new placements, est.). The release during the 6144 and 7168 cells is not measured (hypothesis: the host prefix cache evicted the oldest seeds\' nodes during the long 6144 cell, which released their shards). So the warm FPGA numbers at 4096 to 6144 are hybrids of FPGA and CPU attention in every pass, with nearly all new context on the CPU at 4096 and 5120. At 7168 and 8192 the new shards were mostly placed, but shards inherited from the exhausted cells through the prefix cache kept their CPU attention without a new warning, so the CPU share there is not measured. The cold cells (fresh engines, no warning) are the clean FPGA-attention numbers at every length. What this does and does not explain about the AMX build\'s warm gains is in the paragraph before this subsection.</p>')
    return H


def section6_amx_vs_aof(rows):
    """jhan, 2026-09-22 01:5x UTC: 'is it a pattern that AMX + AoF perf > AoF alone perf? For both decode TPS and prefill.'"""
    cells = FS.amx_vs_avx_rows(rows)
    warm = [c for c in cells if c["kind"] == "warm"]
    cold = [c for c in cells if c["kind"] == "cold"]
    warm_long = [c for c in warm if c["prompt"] >= 4096]
    def rng(xs, key):
        v = [x[key] for x in xs if x.get(key) is not None]
        return (min(v), max(v)) if v else (None, None)
    def rng_all(xs, key):
        v = [y for x in xs for y in x[key]]
        return (min(v), max(v)) if v else (None, None)
    def by(p, kind):
        return [c for c in cells if c["prompt"] == p and c["kind"] == kind][0]
    def plist(c, key="ttft_pcts"):
        return ", ".join(f"{v:+.1f}" for v in c[key]) + " %"
    def lst(xs, key, fmt):
        return ", ".join(f"{c['prompt']}: {c[key]:{fmt}} %" for c in xs)
    tl_lo, tl_hi = rng(warm_long, "ttft_pct"); tla_lo, tla_hi = rng_all(warm_long, "ttft_pcts")
    tt_lo, tt_hi = rng(warm_long, "t_ttft")
    pl_lo, pl_hi = rng(warm_long, "tps_pct"); pla_lo, pla_hi = rng_all(warm_long, "tps_pcts")
    tc_lo, tc_hi = rng(cold, "ttft_pct"); pc_lo, pc_hi = rng(cold, "tps_pct")
    c1024, c1536, c2048, c3000, c7168 = by(1024, "cold"), by(1536, "warm"), by(2048, "warm"), by(3000, "warm"), by(7168, "warm")
    c4c, c8c = by(4096, "cold"), by(8192, "cold")
    exh = [c for c in warm if c["prompt"] in (4096, 5120, 6144)]
    ex_t_lo, ex_t_hi = rng(exh, "ttft_pct"); ex_p_lo, ex_p_hi = rng(exh, "tps_pct")
    sign_mixed = [c["prompt"] for c in warm_long if min(c["tps_pcts"]) < 0 < max(c["tps_pcts"])]
    n_pairs_long = sum(c["n"] for c in warm_long)
    wc = []
    for w in warm:
        for c in cold:
            if c["prompt"] == w["prompt"]:
                wc += [100.0 * (w["tps_avx"] - c["tps_avx"]) / c["tps_avx"], 100.0 * (w["tps_amx"] - c["tps_amx"]) / c["tps_amx"]]
    wc_lo, wc_hi = (min(wc), max(wc)) if wc else (None, None)
    prior_earlier = [p for i, p in enumerate(FS.PRIOR_1024) if i != 2]   # this campaign's own 1024 pair is already a cell above
    pe_t = [100.0 * (p[4] - p[5]) / p[5] for p in prior_earlier]
    pe_p = [100.0 * (p[6] - p[7]) / p[7] for p in prior_earlier]
    hb = hbm_load()
    def lose_list(arm, p):
        return [c["lose"] for c in hbm_group(hb, arm, p, "warm")] if hb else []
    ex_lose = [c["lose"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120, 6144) for c in (hbm_group(hb, arm, p, "warm") if hb else [])]
    ex_share45 = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120) for c in (hbm_group(hb, arm, p, "warm") if hb else []) if c.get("share_new_pct") is not None]
    ex_share61 = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for c in (hbm_group(hb, arm, 6144, "warm") if hb else []) if c.get("share_new_pct") is not None]
    tk_lo, tk_hi = rng(warm_long, "tok_pct")
    l71 = lose_list("fpgabase", 7168) + lose_list("fpgacanon", 7168)
    H = []
    H.append("<h2>6. Is AMX plus FPGA attention better than FPGA attention alone?</h2>")
    H.append("<p>Question (jhan, 2026-09-22): from the data so far, is it a pattern that the AMX build with attention on the FPGA beats the AVX build with attention on the FPGA, for both prefill and decode? The comparison below holds the attention mode fixed (FPGA) and changes only the CPU build: canonical AMX deb against the nightly deb (no AMX code). The two arms ran as separate passes on the same evening or afternoon, and the comparison pairs pass 1 with pass 1, pass 2 with pass 2, pass 3 with pass 3 (three warm passes per arm, two or three cold runs per arm and length). The VNNI-K deb is listed separately at the end.</p>")
    H.append('<div class="short"><p><b>Answer.</b></p>')
    H.append(f"<p><b>Prefill: yes in warm cells from prompt 4096 up, resolved over three passes. In cold cells the AMX build is faster by 2 to 8 %. At 1536 and 3000 the difference is not resolved.</b> In the warm cells at 4096 to 8192 the AMX build prefilled {r0(tl_hi)} to {r0(tl_lo)} % faster than the AVX build (means of the per-pass deltas, 3 paired passes per cell). It was faster in every one of the {n_pairs_long} paired passes (per-pass range {tla_lo:+.1f} to {tla_hi:+.1f} %). The Welch t over the three pass means per arm is {tt_lo:+.1f} to {tt_hi:+.1f}. At 2048 the mean is {c2048['ttft_pct']:+.1f} % ({plist(c2048)} per pass, t {c2048['t_ttft']:+.1f}): the AMX build faster in all three passes, by a varying margin. At 1536 the mean is {c1536['ttft_pct']:+.1f} % ({plist(c1536)}, t {c1536['t_ttft']:+.1f}) and at 3000 {c3000['ttft_pct']:+.1f} % ({plist(c3000)}, t {c3000['t_ttft']:+.1f}). Neither is resolved. In the cold cells the AMX build is faster in every run: {c1024['ttft_pct']:+.1f} % at 1024 (n = 3, t {c1024['t_ttft']:+.1f}), {c4c['ttft_pct']:+.1f} % at 4096 and {c8c['ttft_pct']:+.1f} % at 8192 (n = 2 each). At prompt 1024 the pairs of the earlier campaigns read {min(pe_t):+.1f} % to {max(pe_t):+.1f} % (n = 1 to 6), and at tp4 the AVX build was faster in both pairs (+1.6 %, resolved in runtron with Welch t +3.7). So at 1024 the sign depends on the campaign and on tp. With 8 or 2 users on one engine and no prefix-cache reuse (runtron, section 7) the two builds prefill within 2 % of each other under FPGA attention (-2.0 to +0.3 %, n = 3 per cell). The AMX build is faster in 5 of the 6 cells there. The paired t is -7.9 to -17 in four cells and -0.7 and +1.8 in the other two. The two arms did not see the same prefix-cache share in a paired warm cell (table below). Per uncached prompt token the warm gains from 4096 up are {r0(tk_hi)} to {r0(tk_lo)} % ({r0(tl_hi)} to {r0(tl_lo)} % raw). The cause of the warm gain is not settled (section 5). At 4096 and 5120 it co-occurs in every pass with the card's K/V space running out. There nearly every new shard placement failed ({r0(min(ex_share45))} to {r0(max(ex_share45))} % of the new placements, est.), so both arms scored nearly all new context on the CPU, where the AMX kernel replaces the AVX loop. At 6144 {r0(min(ex_share61))} to {r0(max(ex_share61))} % of the new placements failed. That is a measured co-occurrence, not a measured cause. The gain also appears at 2048 ({c2048['ttft_pct']:+.1f} %), where no shard had failed in any pass and none could have been inherited. At 7168 ({plist(c7168)} in the three pairs) shards inherited from the exhausted cells may have kept their CPU attention without a new warning (section 5), so that cell settles nothing.</p>")
    H.append(f"<p><b>Decode: no at prompt 1024 and in cold cells. Not resolved in warm long-prompt cells.</b> At prompt 1024 the two builds differ by at most 2 % in every pair ({min(pe_p):+.1f} % to {max(pe_p):+.1f} % in the earlier campaigns, {plist(c1024, 'tps_pcts')} in this campaign's three cold runs). In the cold cells at 4096 and 8192 the difference is {pc_lo:+.1f} to {pc_hi:+.1f} % (n = 2 each). In the warm cells from 4096 up the means favour the AMX build by {pl_lo:+.1f} to {pl_hi:+.1f} % TPS. The per-pass deltas, however, run from {pla_lo:+.1f} to {pla_hi:+.1f} % and change sign inside {len(sign_mixed)} of the 5 cells ({', '.join(str(p) for p in sign_mixed)}). So the warm decode direction is not resolved with three passes. With 8 users on one engine and no prefix-cache reuse (runtron, section 7) the two builds decode within 1.2 % of each other in every cell (n = 3). The warm TPS itself lies {abs(wc_hi):.0f} to {abs(wc_lo):.0f} % below the cold TPS at the same prompt length. The VNNI-K build is the opposite case: it decodes 4 to 13 % slower under FPGA attention (issue 4500, the GitHub issue on the VNNI-K decode loss under FPGA attention).</p></div>")
    H.append(f'<div class="fig">{FS.fig_amx_vs_avx(cells)}<p class="cap">Figure 4. AMX build minus AVX build, both with FPGA attention, as a percentage of the AVX build. Rows above the horizontal line are this campaign\'s cells (fpgacanon = the canonical AMX deb with FPGA attention, against fpgabase = the nightly deb with FPGA attention, paired by pass number: 3 passes for warm cells, 3 runs at 1024 and 2 runs at 4096 and 8192 for cold cells). The dot is the mean of the per-pass deltas, the pale bar their range. Rows below the line are the prompt-1024 pairs of earlier campaigns: the whole-machine CI cells of 2026-09-18 (canon-ci against the same-night nightly) and the runtron cells of 2026-09-16 (n = 6 each). Exact values in the tables below.</p></div>')
    H.append("<ul>")
    H.append(f"<li><b>Prefill, warm cells.</b> {lst(warm, 'ttft_pct', '+.1f')} (means of the per-pass deltas). From 4096 up every one of the {n_pairs_long} paired passes favours the AMX build. At 2048 and 1536 all three passes favour it, by margins from {abs(max(c2048['ttft_pcts'] + c1536['ttft_pcts'])):.0f} to {abs(min(c2048['ttft_pcts'] + c1536['ttft_pcts'])):.0f} %. At 3000 the sign changes between passes ({plist(c3000)}).</li>")
    H.append(f"<li><b>Prefill, cold cells.</b> {lst(cold, 'ttft_pct', '+.1f')} (n = 3 at 1024, n = 2 at 4096 and 8192, the AMX build faster in every run). The AVX-side 1024 value ({c1024['ttft_avx']:,.0f} ms, three runs within 2 ms) is 25 to 45 ms above that cell's history (section 5). Prompt-1024 pairs from the earlier campaigns: {', '.join(f'{v:+.1f} %' for v in pe_t)}.</li>")
    dec_list = ", ".join(f"{c['prompt']} {c['kind']}: {c['tps_pct']:+.1f} %" for c in cells)
    H.append(f"<li><b>Decode, all cells.</b> {dec_list} (means of the per-pass deltas; per-pass values in the table). Prompt-1024 pairs from the earlier campaigns: {', '.join(f'{v:+.1f} %' for v in pe_p)}.</li>")
    H.append(f"<li><b>Reading.</b> The warm cells at 4096 to 6144 ran with the card's K/V space exhausted in every pass (section 5). tron logged {min(ex_lose)} to {max(ex_lose)} \"lose HW attention\" warnings per pass-cell there (one per shard per engine, HW = the FPGA), and the recorded fallback counter agrees with those counts. The affected shards were scored on the CPU for both prefill and decode. On the CPU the AMX kernel replaces the AVX loop. So in those three cells the AMX build's gains ({r0(ex_t_hi)} to {r0(ex_t_lo)} % lower TTFT, {ex_p_lo:+.1f} to {ex_p_hi:+.1f} % TPS on average) include AMX against AVX on the share of attention that moved to the CPU. That share is not a gain of the FPGA path itself. The gain at 2048 ({c2048['ttft_pct']:+.1f} %) is not explained by fallback: no shard had failed before or during any 2048 cell (hypothesis in section 5: cached-prefix pages scored on the CPU). At 7168 ({c7168['ttft_pct']:+.1f} %, no new failure in {sum(1 for x in l71 if x == 0)} of 6 pass-cells) inherited degraded shards may have run CPU attention without a warning, so that cell is not evidence either way. Three FPGA-arm cells had one engine restart during the cell (fpgabase pass 2 at 2048, fpgabase pass 3 at 7168, fpgacanon pass 3 at 1536, section 5), which adds noise to those pairs. At 8192 the two arms also differ in how much fell back ({', '.join(str(x) for x in lose_list('fpgabase', 8192))} warnings per pass in the AVX arm against {', '.join(str(x) for x in lose_list('fpgacanon', 8192))} in the AMX arm). That difference adds noise to the 8192 comparison. In the cold cells (no warning) the card holds every shard. The CPU keeps only the own-chunk triangle (each query's own 128-token chunk, section 4). The CPU build then lowers TTFT by {abs(tc_hi):.0f} to {abs(tc_lo):.0f} % and changes TPS by at most {max(abs(v) for c in cold for v in c['tps_pcts']):.1f} %. Under FPGA attention the warm decode is {abs(wc_hi):.0f} to {abs(wc_lo):.0f} % slower than the cold decode at the same prompt length. Hypothesis: the fallback to CPU attention causes part of that loss. Test: a perfetto trace of one warm 2048 request, AMX build against kill switch.</li>")
    H.append("</ul>")
    H.append("<h3>The record</h3>")
    H.append(FS.table_amx_vs_avx(cells))
    H.append('<p class="cap">Top: this campaign\'s cells (client-side TTFT and decode TPS per user, harness means over 8 users x 10 rounds per pass; mean and sd over the passes per arm; the change columns are the mean of the per-pass deltas and the per-pass deltas themselves; Welch t over the pass means of the two arms; the per-uncached-token column divides each pass\'s TTFT by its prompt tokens not served from the prefix cache before taking the delta, because the two arms saw different prefix-cache shares in the same cell). Middle: canonical-AMX against AVX pairs at prompt 1024 with FPGA attention on both sides (this campaign\'s cold cells included as one row with their three-run means). Bottom: the VNNI-K deb against the AVX deb at prompt 1024, where the decode loss of issue 4500 shows. Sources are in the source column and in section 9 (Data files).</p>')
    return H


# ---------------------------------------------------------------- page
def page():
    p_half2 = [p for p in PAIRS if p["setup"].startswith("our half, tp2")]
    p_half4 = [p for p in PAIRS if p["setup"].startswith("our half, tp4")]
    canon_half2 = [p for p in p_half2 if p["kernel"] == "canon"][0]
    canon_half4 = [p for p in p_half4 if p["kernel"] == "canon"][0]
    avx_half2 = [p for p in p_half2 if p["kernel"] == "avx"][0]
    avx_half4 = [p for p in p_half4 if p["kernel"] == "avx"][0]
    whole_canon = [p for p in PAIRS if p["setup"].startswith("whole 3bda") and p["kernel"] == "canon"][0]
    whole_avx = [p for p in PAIRS if p["setup"].startswith("whole 3bda") and p["kernel"] == "avx"][0]
    rt_pairs = [p for p in PAIRS if p["group"] == "rt"]
    rt_vnnik = [p for p in rt_pairs if p["kernel"] == "vnnik"]
    canon_solid = [p for p in PAIRS if p["kernel"] == "canon" and p["solid"]]
    rt_canon_solid = [p for p in rt_pairs if p["kernel"] == "canon" and p["solid"]]
    avx_all = [p for p in PAIRS if p["kernel"] == "avx"]
    vn_lo, vn_hi = min(p["pct"] for p in rt_vnnik), max(p["pct"] for p in rt_vnnik)
    ca_lo, ca_hi = min(p["pct"] for p in canon_solid), max(p["pct"] for p in canon_solid)
    rca_lo, rca_hi = min(p["pct"] for p in rt_canon_solid), max(p["pct"] for p in rt_canon_solid)
    av_lo, av_hi = min(p["pct"] for p in avx_all), max(p["pct"] for p in avx_all)
    n_vn = len(rt_vnnik)
    n_ca = len(canon_solid)
    n_ca_fpga_faster = sum(1 for p in canon_solid if p["pct"] < 0)
    n_ca_fpga_slower = n_ca - n_ca_fpga_faster
    NUMWORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

    css = """
    body{background:#f9f9f7;color:#0b0b0b;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.5;margin:0;padding-block:24px;padding-inline:16px}
    main{max-width:1040px;margin:0 auto}
    h1{font-size:26px;line-height:1.2;margin:0 0 6px;text-wrap:balance}
    h2{font-size:19px;margin:36px 0 10px;border-bottom:1px solid #e1e0d9;padding-bottom:4px}
    h3{font-size:16px;margin:22px 0 6px}
    p,li{max-width:78ch}
    .sub{color:#52514e;font-size:13px;margin:0 0 18px}
    .short{background:#fcfcfb;border:1px solid #e1e0d9;border-left:4px solid #2a78d6;padding:12px 16px;margin:16px 0}
    .short p{margin:6px 0}
    .fig{background:#fcfcfb;border:1px solid #e1e0d9;padding:12px;margin:14px 0;overflow-x:auto}
    .cap{color:#52514e;font-size:13px;margin:6px 0 0;max-width:none}
    .tw{overflow-x:auto;margin:10px 0}
    table{border-collapse:collapse;font-size:13px;min-width:600px}
    th,td{border-bottom:1px solid #e1e0d9;padding:5px 8px;text-align:left;vertical-align:top}
    th{background:#f0efec;font-weight:600;color:#52514e}
    table.num td:not(:first-child):not(:last-child){font-variant-numeric:tabular-nums;white-space:nowrap}
    dt{font-weight:600;margin-top:10px}
    dd{margin:2px 0 0 0}
    code{font-size:13px;background:#f0efec;padding:1px 4px}
    pre{background:#f0efec;border:1px solid #e1e0d9;padding:10px 12px;font-size:12.5px;line-height:1.35;overflow-x:auto}
    .gap{background:#fcfcfb;border:1px solid #e1e0d9;border-left:4px solid #eda100;padding:10px 14px;margin:10px 0}
    .hyp{color:#52514e}
    """
    H = []
    H.append("<title>qwen3-4b prefill: AMX or FPGA</title>")
    H.append(f"<style>{css}</style>")
    H.append("<main>")
    H.append("<h1>Prefill on qwen3-4b: attention on the CPU with AMX against attention on the FPGA</h1>")
    H.append('<p class="sub">Answer to jhan\'s question of 2026-09-21: "Among the tests performed at qwen3-4b, comparing prefill performance between AMX (canonical, VNNI-K) and Attention-on-FPGA, which is better?" Every number comes from campaign result files under exec/results/ (extraction workflow wf_258257df-233 with 14 agents and verification workflow wf_89cf57ff-912 with 10 agents, both 2026-09-21. Section 5 added 2026-09-22 from the q4b-fpga-20260921 campaign). Generator: exec/prefill-amx-vs-fpga-20260921/gen_page.py.</p>')

    H.append('<div class="short"><p><b>Short version.</b></p>')
    agg0 = FS.aggregate(FS.load())
    rtd = RT.load()
    rt8k = {k: RT.cell(rtd, "q3-4b-tp2-8u-p8192", *a)["ttft_mean"] for k, a in (("cb", ("cpu", "base")), ("cc", ("cpu", "canon")), ("fc", ("fpga", "canon")))} if rtd else None
    if FS.have_fpga(agg0):
        c_cpu, c_fc = FS.mean(agg0.get("canon", {}).get(8192, {}).get("cold", [])), FS.mean(agg0.get("fpgacanon", {}).get(8192, {}).get("cold", []))
        w_b, w_c = FS.mean(agg0.get("base", {}).get(8192, {}).get("warm", [])), FS.mean(agg0.get("canon", {}).get(8192, {}).get("warm", []))
        rowsA = FS.load()
        t5120 = FS.welch([r["ttft_harness_ms"] for r in rowsA if r["arm"] == "canon" and r["prompt_length"] == 5120 and not r["cold"]], [r["ttft_harness_ms"] for r in rowsA if r["arm"] == "fpgacanon" and r["prompt_length"] == 5120 and not r["cold"]])
        c_fb = FS.mean(agg0.get("fpgabase", {}).get(8192, {}).get("cold", []))
        H.append(f'<p>At prompt 1024, prefill takes about the same time with the AMX kernel on the CPU as with attention on the FPGA. '
                 f'From prompt 2048 up the FPGA is faster, up to {c_cpu / c_fc:.1f}x at a cold 8192-token prompt, and the AMX kernel on the CPU is itself {w_b / w_c:.1f}x faster than the old AVX kernel at that length. '
                 f'Under FPGA attention the AMX build lowers the warm TTFT by 33 to 48 % from prompt 4096 up (cause not settled, section 5), but without a warm prefix cache it changes prefill by at most 8 % and decode by at most 2 % (sections 6 and 7).</p></div>')
        H.append('<p class="cap"><b>Key numbers behind the Short version.</b></p><ul>')
        H.append(f'<li>Prompt 1024 (sections 1 to 3): every matched pair of the canonical build is within {ca_lo:+.1f} % to {ca_hi:+.1f} % (FPGA minus CPU).</li>')
        H.append(f'<li>Cold 8192-token prefill, CI harness, 2 users per engine (section 5): {c_fc / 1000:.1f} s on the FPGA with the AMX build, {c_fb / 1000:.1f} s with the AVX build, {c_cpu / 1000:.1f} s with the AMX kernel on the CPU (one run of 2026-09-19). FPGA against CPU AMX: {c_cpu / c_fc:.1f}x.</li>')
        H.append(f'<li>8 prompts of 8192 tokens at once on one engine, runtron (section 7): {rt8k["fc"]:.0f} s on the FPGA, {rt8k["cc"]:.0f} s with the AMX kernel on the CPU, {rt8k["cb"]:.0f} s with the old AVX kernel. FPGA against CPU AMX: {rt8k["cc"] / rt8k["fc"]:.1f}x. AMX against AVX on the CPU: {rt8k["cb"] / rt8k["cc"]:.1f}x.</li>')
        H.append(f'<li>Warm 8192 cells, CI harness (section 5): AVX on the CPU {w_b / 1000:.1f} s, AMX on the CPU {w_c / 1000:.1f} s ({w_b / w_c:.1f}x). The FPGA is faster than the CPU AMX kernel at every warm length from 2048 up; the 5120 pair alone is not resolved (Welch t {t5120:+.1f}).</li>')
        H.append('<li>AMX build against AVX build under FPGA attention (sections 6 and 7): warm cells from 4096 up 33 to 48 % lower TTFT in every one of three passes, cold CI cells 2 to 8 % lower, runtron cells -2.0 to +0.3 %, decode within 2 % everywhere except the warm CI cells, where three passes do not resolve it. The card\'s K/V space ran out in the 4096 to 6144 cells of every pass (section 5), which explains the gain there but not at 2048.</li>')
        H.append('</ul>')
    else:
        H.append(f'<p>At prompt 1024, prefill takes about the same time whether attention runs on the CPU with the AMX kernel or on the FPGA. '
                 f'In every matched pair the FPGA arm is within {ca_lo:+.1f} % to {ca_hi:+.1f} % of the canonical-AMX arm and within {vn_lo:+.1f} % to {vn_hi:+.1f} % of the VNNI-K arm (positive = FPGA slower), and it beats the old AVX kernel by {abs(av_hi):.0f} to {abs(av_lo):.0f} %. '
                 f'Above prompt 1024 no qwen3-4b run with FPGA attention recorded a TTFT, so the long-prompt comparison is Insufficient data.</p></div>')

    # words
    H.append("<h2>Words used here</h2><dl>")
    H.append("<dt>tron, runtron, rinzler, engine, FPGA, tp2 / tp4</dt><dd>tron is the inference program under test. runtron is its command-line tool (one process, no HTTP). rinzler is the production server around tron. One running rinzler is one engine. FPGA (field-programmable gate array) = the accelerator card. tp2 / tp4 = two / four FPGA cards per engine.</dd>")
    H.append("<dt>prefill, TTFT, TPS</dt><dd>prefill = processing the prompt before the first generated token. TTFT = time to first token. TPS = generated tokens per second per user (decode speed). Two different TTFT numbers appear on this page and are never mixed. (a) runtron's server-side \"Parsing the prompt took\" time. For 8 users this is the wall time of the batched prefill of all 8 prompts (the 8 values agree to the millisecond). (b) The CI harness's client-side stopwatch from the HTTP request to the first streamed chunk. It is the mean over all users x 10 rounds (8 users = 80 samples on the whole machine, 4 users = 40 samples in the our-half cells). It also contains the proxy hop, tokenization and the first sampling step.</dd>")
    H.append("<dt>CI, CI harness, the nightly</dt><dd>CI = continuous integration, the automated test run. The nightly = the CI run that starts at 03:30 UTC every night on delphi-3bda and installs that day's tron deb. The CI harness = the nightly's own client program (systems_test), which we also run by hand.</dd>")
    H.append("<dt>attention on the CPU / on the FPGA, K/V, HBM, DMA</dt><dd>tron scores attention either on CPU worker threads (USE_HW_ATTN=0, \"CPU attention\") or on the FPGA card (USE_HW_ATTN unset, the production and nightly default for ingested models such as qwen3-4b, \"FPGA attention\" or \"AoF\"). K/V = the attention keys and values saved per prompt token. HBM = high-bandwidth memory, the card's own memory, which holds a copy of the K/V. DMA = direct memory access, the copy of K/V from host memory to the card. Even with FPGA attention a share of the prompt's attention stays on the CPU (section 4).</dd>")
    H.append("<dt>AVX, canonical AMX, VNNI-K, kill switch, deb</dt><dd>AVX = the CPU attention kernel of tron before PR 3879 (AVX-512 vector instructions). An AMX build also runs it when the kill switch TRON_AMX_DISABLE=1 is set. Canonical AMX = the AMX (Intel Advanced Matrix Extensions) page kernel of PR 3879 on the normal row-major K layout. VNNI-K = PR 4424, which stores K in place in the VNNI (Intel Vector Neural Network Instructions) pair-interleaved layout. deb = a tron Debian package as the nightly installs it. The nightly deb has no AMX code. Its build preset does not set TRON_AMX_DISPATCH.</dd>")
    H.append("<dt>our half, whole 3bda, nightly layout, platformd, Caddy</dt><dd>delphi-3bda is the test machine (Intel Granite Rapids, 8 FPGA cards). \"Our half\" = socket 1 with cards 90/93/b9/bc. \"Whole 3bda, nightly layout\" = 4 tp2 engines (or 2 tp4 engines) started by platformd (the service that starts and places the engines) behind the Caddy reverse proxy, 8 users in total, 2 (tp2) or 4 (tp4) users per engine. This is the nightly's own shape.</dd>")
    H.append("<dt>campaign names, arm names, issue 4500</dt><dd>p0perf, wedperf, wedperf-attr, vnnik4, canon-ci, ci-mimic, q4b-swattn, issue4500, q4b-fpga = the result directories under exec/results/ that hold each measurement run. Section 8 lists their files. Arm names of the q4b-fpga campaign: fpgabase = the nightly deb with FPGA attention, fpgacanon = the canonical AMX deb with FPGA attention, canon = the canonical deb with CPU attention. issue 4500 = the GitHub issue on the VNNI-K decode loss under FPGA attention.</dd>")
    H.append("<dt>prefix cache, tree node, conversation seeds, cold and warm prompts, perfetto</dt><dd>prefix cache = rinzler reuses the K/V of a prompt start it has already processed. It stores the prefixes as a tree, one node per stored prefix. A warm request hits it, a cold one does not. conversation seeds = the fixed prompt texts each simulated user of the CI harness starts from, reused inside a pass. perfetto = the timeline tracing tool tron writes its spans to.</dd>")
    H.append("<dt>pre-cell AMX probe (AMX-busy probe), engine journal, driver, FUSE stats, shard</dt><dd>pre-cell AMX probe = before every cell our campaign driver counts EXE.AMX_BUSY (the CPU\'s count of cycles in which the AMX unit was busy) on the engine processes for 20 s. During that window it keeps 4 request streams of its own running. Each stream repeats a 6,000-character prompt (about 1,100 tokens, est.) with 256 generated tokens. The count is proof that AMX instructions ran. It measures the probe\'s own traffic in the state the engines are in at that moment, not the cell that follows. engine journal = the systemd log of the rinzler engines (journalctl -u rinzler@*). driver = our campaign script that provisions the engines and runs the harness cells (exec/q4b-fpga-20260921/st_ci_perf.py). FUSE stats = the file-like interface through which an engine exposes its counters (FUSE = Filesystem in Userspace). shard = the card-side copy of 1024 tokens of one request\'s K/V, placed on one card.</dd>")
    H.append("<dt>repetition, paired t, runtron.pre3879 / runtron.main0916</dt><dd>repetition = one full round of all cells, arms and attention modes of the runtron campaign (section 7). The campaign ran 3 repetitions, interleaved. A slow change of the machine\'s state during the campaign therefore affects every arm alike. paired t = the mean of the per-repetition differences (repetition k of one arm minus repetition k of the other) divided by their standard error. runtron.pre3879 = runtron built from main before PR 3879 (eb2de0265a, the AVX build). runtron.main0916 = runtron built from main on 2026-09-16 (c7844ca2ce, the canonical AMX build).</dd>")
    H.append("<dt>Welch t, Welch df, n, sd</dt><dd>n = repetitions the mean is over. sd = sample standard deviation over those repetitions. Welch t = (FPGA mean minus CPU mean) divided by the standard error of that difference with unequal variances. Welch df = the degrees of freedom of that test. With n = 2 on one side the df is about 1, and a two-sided p of 0.05 then needs |t| above 12.7 (4.3 at df 2, 2.8 at df 4). So a |t| of 3 means \"three standard errors\", not \"resolved\", in the low-df rows. With n = 1 on one side no t exists.</dd>")
    H.append("</dl>")

    # section 1
    H.append("<h2>1. The comparison at prompt 1024</h2>")
    H.append(f'<div class="fig">{fig1()}<p class="cap">Figure 1. One row per setup. One dot per CPU kernel the FPGA arm is compared with. In the two "our half" CI rows and the "one deb" whole-machine row the CPU and FPGA arms are the same binary. In the runtron rows both arms are the same binary per colour, but the CPU and FPGA cells ran in separate blocks 8 minutes to about 2 hours apart. Exact values, n, t and df are in the table below.</p></div>')
    H.append("<ul>")
    H.append(f"<li><b>Canonical AMX on the CPU against the FPGA.</b> Same binary 544ca05c7a, CI harness, our half, 2026-09-13. At tp2, {f0(canon_half2['cpu']['mean'])} ms against {f0(canon_half2['fpga']['mean'])} ms ({pct(canon_half2['pct'])}, t {tstr(canon_half2['t'])}). At tp4, {f0(canon_half4['cpu']['mean'])} ms against {f0(canon_half4['fpga']['mean'])} ms ({pct(canon_half4['pct'])}, t {tstr(canon_half4['t'])}). The sign flips between tp2 and tp4. The FPGA arm of this campaign also had the kill switch set. Block m6 of issue 4500 measured that switch at +62 ms in the same layout for the VNNI-K deb, so the tp2 gap lies between about -4 % and +4.6 %. Same deb 0594dc54 on the whole machine in the nightly layout: {f0(whole_canon['cpu']['mean'])} ms against {f0(whole_canon['fpga']['mean'])} ms ({pct(whole_canon['pct'])}, one pass on the FPGA side). Runtron, 8 prompts in one batch: {rca_lo:+.1f} % to {rca_hi:+.1f} %. Over all {NUMWORD[n_ca]} canonical pairs the FPGA arm is slower in {NUMWORD[n_ca_fpga_slower]} and faster in {NUMWORD[n_ca_fpga_faster]}. The two pairs nearest zero ({whole_canon['pct']:+.1f} % and {rca_lo:+.1f} %) have n = 1 on the FPGA side and are not resolved.</li>")
    H.append(f"<li><b>VNNI-K on the CPU against the FPGA.</b> Only runtron pairs exist. No CI-harness run of the VNNI-K deb with CPU attention was ever made. The FPGA arm is slower by {vn_lo:+.1f} % to {vn_hi:+.1f} % in all {NUMWORD[n_vn]} pairs (tp2 +2.0 to +2.6 %, tp4 +6.1 %). The tp4 value rests on two FPGA repetitions 67 ms apart (Welch t +3.9 with about 1 degree of freedom), so its size is not resolved. The direction is resolved by the wedperf-attr tp2 pair (n = 6 on the FPGA side, t +10.6) and by the same sign in all {NUMWORD[n_vn]} pairs.</li>")
    H.append(f"<li><b>AVX on the CPU against the FPGA.</b> The FPGA arm is faster by {abs(av_hi):.0f} % to {abs(av_lo):.0f} % in every pair. This is the comparison the nightly would see today. The nightly deb has no AMX code.</li>")
    H.append("</ul>")
    H.append('<p>Reading. The AMX kernel and the FPGA remove about the same amount of prefill time from the AVX baseline at this prompt length. Which one is a few percent faster depends on tp and on the harness. Within one setup the difference is resolved (t +14.0 at tp2, t -5.7 at tp4, against a run-to-run sd of 2 to 5 ms). Its sign changes between setups, so no single winner exists at this prompt length. The differences are of the size of the setup differences between the two sides: the kill switch on the p0perf FPGA arm (62 ms in block m6), separate blocks 8 minutes to 2 hours apart in runtron, and two days on the whole machine. Decode TPS, which was not the question, favours the FPGA by 24 to 57 % in the two cited cell sets (CI harness our half +24 to +37 %, runtron vnnik4 +47 to +57 %) [exec/results/p0perf-20260913/summary.md:14,16; exec/results/vnnik4-models-20260915/results.txt:70,90 with vnnik4-20260915/summary.md:9-10]. In the wedperf runtron cells that gain is +13 % (VNNI-K, tp4) to +75 % (AVX, tp2) [exec/results/wedperf-20260916/summary.md:21-24,31-34].</p>')
    H.append("<h3>The record: every matched pair (the last row pairs two builds)</h3>")
    H.append(pair_table())
    H.append('<p class="cap">The runtron TTFT is the batched prefill of 8 prompts. The CI-harness TTFT is a per-request client-side value with 2 or 4 users per engine. The two are not comparable with each other, only within a row. The 1-user smoke runs of vnnik4 (VNNI-K build, CPU 432 ms with n = 2, FPGA 416 ms with n = 1) are left out: the CPU smoke ran under a machine load of 99 to 121 with no free hugepages. Sources are listed in section 9.</p>')

    # section 2
    H.append("<h2>2. The production-like view</h2>")
    H.append(f'<div class="fig">{fig2()}<p class="cap">Figure 2. The same deb 0594dc54 gives {f0(ci_whole_tp2["canon_cpu"]["mean"])} ms with CPU attention (q4b-swattn, 2026-09-20) and {f0(ci_whole_tp2["canon_fpga"]["mean"])} ms with FPGA attention (canon-ci, 2026-09-18). The nightly deb (AVX) gives {f0(ci_whole_tp2["avx_cpu"]["mean"])} ms with CPU attention (q4b-swattn, 2026-09-20) and {f0(ci_whole_tp2["avx_fpga_night"]["mean"])} ms with FPGA attention in the nightly of 2026-09-18 (remote client). Each FPGA bar is one pass. A difference between two FPGA bars under about 20 ms (two sd of a two-night difference) is not resolved.</p></div>')
    H.append('<p>Three caveats on this figure. The CPU-attention bars (q4b-swattn) and the canonical-AMX FPGA bar (canon-ci) used the same client host (claude-agentsrv). canon-ci measured its client lightly loaded (CPU pressure 0 to 5 %). q4b-swattn did not record its client load. The nightly bar used the remote CI runner, whose load is never recorded. The ci-mimic run of the nightly deb with FPGA attention on 2026-09-18 gave 556 ms, but its client host was CPU-saturated during that arm, so the same-day nightly (528 ms) is the number used here [exec/results/ci-mimic-20260918/caveats.html]. The 674 ms bar includes base pass 3 (702 ms), which had an uneven Caddy spread (22 / 22 / 0 / 20 requests per engine) and 2 Caddy health events [exec/results/q4b-swattn-20260919/summary.txt:13]. Passes 1 and 2 alone give 660 ms.</p>')

    # section 3
    H.append("<h2>3. With FPGA attention, does the CPU build still matter for prefill?</h2>")
    H.append(fpga_build_table())
    H.append('<p>At prompt 1024, once the FPGA scores attention, the CPU build changes prefill by a few percent at most. The sign depends on the build and on tp. At longer prompts with a warm prefix cache the AMX build lowers it by 33 to 48 % from 4096 up (means over three passes, section 6). The cause of that warm gain is not settled (section 5 names two candidate mechanisms).</p>')
    H.append("<ul>")
    H.append("<li><b>VNNI-K build against AVX build.</b> Faster in every cell: -8 % at 2 users per engine on our half (762 to 700 ms, n = 2, Welch t -35), -5 % at 4 users (848 to 809 ms), -4.5 % on the whole machine at tp2 (528 to 504 ms, one pass each, client under pressure on the 504 side), -1.7 % (tp2) and -1.0 % (tp4) in runtron with 8 prompts.</li>")
    H.append("<li><b>Canonical build against AVX build.</b> Not resolved at tp2 (516 against 528 ms on the whole machine, one pass each). Against the 13-night mean of 509.5 ms the canonical deb reads +1.3 %. Slightly slower at tp4 (runtron 2,288 against 2,253 ms, +1.6 %, n = 6 per side, Welch t +3.7, and on the whole machine 646 against 636 ms, one pass each).</li>")
    H.append("<li><b>The kill switch on the VNNI-K deb.</b> At tp2 it gives the AVX number back (762 ms against 762 ms for the nightly deb). At tp4 it does not (814 ms with the switch against 848 ms for the nightly deb, -4.0 %, Welch t -21.5). So at tp4 most of the VNNI-K deb's -4.7 % is a difference between the two debs, not the AMX kernel. In runtron block m1 at tp4 the kill-switch arm (2,192 ms) is the fastest of the five arms.</li>")
    H.append("</ul>")
    H.append('<p class="hyp">Hypothesis (unmeasured): the -8 % at 2 users per engine comes from prompt K/V whose DMA to the card had not finished when the next 128-token forward was scheduled. Those pages were then scored on the CPU as dense pages, where the AMX kernel applies (section 4). Test: a perfetto trace of one prefill with the "Attention Ready / Pending" and "attention: hw wait" spans per forward, AMX build against kill switch, on the same engine.</p>')

    # section 4
    H.append("<h2>4. What runs where during prefill (from the tron source)</h2>")
    H.append('<p>Read from the PR 4424 tree (30c4ac82cb) by three agents and checked by two more. Line numbers are from that tree. The FPGA prefill path and its constants are the same in main of 2026-09-10 (1279137d). The AMX statements exist only in the PR tree, because that main predates the PR 3879 merge. The file:line evidence is in the workflow journals.</p>')
    H.append("<ul>")
    H.append('<li>A prompt is fed to the model 128 tokens per user per forward pass (default of TRON_PER_USER_PROMPT_CHUNK_LIMIT, which no deployment file on delphi-3bda sets). A 1024-token prompt is 8 forwards. With 8 users in one runtron batch, each forward carries 8 x 128 = 1024 prompt tokens. That fits one forward under either reading of the per-forward budget (1024 tokens for the ingested plugin\'s one minibatch, or tron\'s 4096-token mask capacity). That is why all 8 users finish prefill on the same pass [h/libtron.hpp:197-203; src/tron/generation/context.cpp:40-42; ingest/src/TronCpp.hs:262-263; h/tron/scheduler/full.hpp:1692-1699; h/tron/models/ranged_mask.hpp:20].</li>')
    H.append('<li>With FPGA attention, the queries of forward k are scored on the FPGA against the K/V of forwards 1..k-1 that already sit in the card\'s HBM. The first forward (positions 0..127) runs entirely on the CPU: no K/V of the prompt is on the card yet, and the FPGA takes a query only once 128 tokens (positions 0..127, up to the engagement point 127) are DMA-complete in HBM. The engagement point is the default 127. USE_HW_ATTN=N moves it to the next 64-token page boundary minus 1. Every query\'s own 128-token chunk (the causal triangle) is always scored on the CPU. So is any K/V above the first 4-token group whose DMA had not completed when the forward was planned: the FPGA covers a contiguous DMA-complete prefix, and everything above the first gap stays on the CPU [h/libpos.hpp:90; h/pos/config.hpp:98; h/tron/scheduler/full.hpp:1913-1919, 2755-2800; src/tron/models/ranged_mask.cpp:73-86; h/tron/models/model.hpp:2495-2513].</li>')
    H.append('<li>With CPU attention, the AMX page kernel scores the queries of forward k against the full 64-token pages of forwards 1..k-1 (a page is "dense" for a query when it is fully visible). The own-chunk triangle runs the AVX path in every build [h/tron/models/self_attention.hpp:1383-1394, 1546-1556].</li>')
    H.append('<li>Therefore the FPGA and the AMX kernel replace the same part of the work when the DMA keeps up with the forwards: the cross-chunk rectangles, about 87 % (est.) of the 524,800 causal (query, key) pairs of a 1024-token prompt. The remaining 13 % (est., 66,048 pairs) runs on the CPU with the AVX path in both modes. In an FPGA-attention run the AMX dense-page kernel does not touch the prompt\'s own attention unless DMA lags, a KV slot is configured software-only, or a shard lost its HBM allocation. The AMX build still packs each query\'s Q group and holds the tile configuration for every attention call, a small fixed cost that is the only AMX-build effect on the FPGA path when no DMA lags [h/tron/models/self_attention.hpp:1228-1256].</li>')
    H.append('<li>Extra work inside TTFT in the FPGA path: (1) staging each group of 4 tokens into the card\'s layout (gof::populate) and 36 DMA descriptors per group per layer [src/tron/gof.cpp:159-222; h/tron/models/model.hpp:3146-3300]. (2) One FPGA pass per at most 32 queries per layer (MAX_B, which the card\'s activation-slot budget or HWATTN_MAX_B can lower), and each pass re-reads the resident K/V [h/tron/models/model.hpp:2580-2650; src/pos/worker.cpp:969-975]. (3) The unpack and join of each pass\'s result on the attention workers [h/tron/models/self_attention.hpp:843-895, 1024-1050].</li>')
    H.append("</ul>")
    H.append("<pre>")
    H.append("prefill of one 1024-token prompt, FPGA attention on (8 forwards of 128 tokens)\n")
    H.append("forward 1  positions 0..127     CPU only (no K/V on the card yet)\n")
    H.append("forward k  positions (k-1)*128..k*128-1\n")
    H.append("           FPGA : 128 queries x K/V of forwards 1..k-1 already in HBM\n")
    H.append("                  (a contiguous DMA-complete prefix)\n")
    H.append("           CPU  : 128 queries x own chunk (causal triangle), AVX path\n")
    H.append("                  + K/V above the first DMA gap, if any\n")
    H.append("           host : save K/V -> stage 4-token groups -> DMA (async,\n")
    H.append("                  visible to the plan of forward k+1 at the earliest)\n")
    H.append("\n")
    H.append("same prompt, CPU attention (USE_HW_ATTN=0)\n")
    H.append("forward k  AMX page kernel : 128 queries x dense pages of forwards 1..k-1\n")
    H.append("           AVX path        : 128 queries x own chunk (causal triangle)\n")
    H.append("</pre>")
    H.append('<p class="cap">Text diagram. Durations are not to scale. "dense page" = a 64-token KV page fully visible to the query.</p>')
    H.append('<p>Why the two are equal at 1024 (a reading of the data, not a measurement of the parts). In the CI cells on our half, replacing AVX by AMX on the cross-chunk part removed 181 ms (909 to 727) at tp2. Moving that part to the FPGA removed 148 ms (909 to 761). On the whole machine the two removals were 157 ms (674 to 517, one campaign, same client and day) and about 146 ms (est., 674 from q4b-swattn on 2026-09-20 against 528 from the 2026-09-18 nightly on a different client host). The FPGA path carries its staging, launch and join overhead inside TTFT. The AMX path carries the page kernel\'s own time. At this prompt length the two costs are of the same size.</p>')

    # section 5: measured FPGA curve when the q4b-fpga-20260921 rows exist, else the gap statement
    agg = FS.aggregate(FS.load())
    if FS.have_fpga(agg):
        H.extend(section5_measured(agg))
    else:
        H.extend(section5_gap())

    # section 6: AMX build against AVX build under FPGA attention (jhan's question of 2026-09-22 01:5x UTC)
    if FS.have_fpga(agg):
        H.extend(section6_amx_vs_aof(FS.load()))
    H.extend(RT.section())

    # section 7
    H.append("<h2>8. What was measured on 2026-09-21/22, and what remains</h2>")
    H.append("<p>The campaign exec/q4b-fpga-20260921/ is the measurement the first version of this page asked for (FPGA-attention cells at prompts 1536 to 8192 in the nightly layout), run on the platformd 0.11 layout (Rhys upgraded delphi-3bda on 2026-09-21: engines are named entries default-0 to default-3 with their own ingress ports, the harness provisions them through the explicit config and a test proxy on port 80. Our wrappers were updated the same evening).</p>")
    H.append("<ul>")
    H.append("<li>Arms run: fpgabase (nightly deb, FPGA attention), fpgacanon (canonical AMX deb, FPGA attention), canon (canonical deb, CPU attention, one same-day pass). Each pass = the 9 cells of the 2026-09-20 grid. Cold cells = single-cell driver runs at 4096 and 8192 for both FPGA arms, two per arm and length.</li>")
    H.append("<li>Kept from before: the 2026-09-20 CPU-attention series (nightly deb and canonical deb, 3 passes each) and its cold check cell at 8192. The CPU-attention arms were not re-run beyond the one canonical pass (jhan, 2026-09-22).</li>")
    H.append("<li>Done after the 2026-09-22 nightly (13:20 to 16:25 UTC): passes 2 and 3 of the two FPGA arms and a second cold cell per arm at 4096 and 8192, with the card allocator free space and the software-fallback count recorded per cell (they confirm the exhaustion reading, section 5). Done the same afternoon (16:58 to 18:12 UTC): the runtron campaign exec/q4b-rt8u-20260922/ (8 users on one engine on our half, prompts 1024 to 8192, plus 2 users at 4096 and 8192, both attention modes and both builds, 3 repetitions), section 7. Not measured and not planned: a cold CPU-attention cell at 4096, a cold AVX cell at 8192, and the VNNI-K deb under FPGA attention at long prompts (optional arm fpgavnnik).</li>")
    H.append(f"<li>Noise: three passes per FPGA arm. The pass-to-pass sd of the warm TTFT is 16 to 128 ms below 4096 and 118 to 793 ms from 4096 up (the AVX arm is the noisier one from 4096 up, sd 282 to 793 ms against 118 to 411 ms). The two cold runs of one arm at one length are 10 to 41 ms apart (sd 7 to 29 ms). The CPU series' 3-pass sd was 1 to 25 ms at 1024 and 350 to 1230 ms at 8192.</li>")
    H.append("</ul>")

    # section 7
    H.append("<h2>9. Caveats and provenance</h2>")
    H.append("<ul>")
    H.append("<li>The only same-binary, same-day CI-harness pairs (p0perf-20260913) change two things at once: the FPGA arm also set the kill switch. Its CPU share therefore ran AVX. The code reading says the AMX dense-page kernel does not run on the prompt's attention under FPGA attention unless DMA lags. By that reading the kill switch should not matter there. The data are mixed on this (section 3 at prompt 1024, and section 6 shows 33 to 48 % in warm cells from 4096 up, three passes each, with the two candidate causes in section 5). So the +4.6 % / -1.9 % may include a kill-switch effect of unknown sign.</li>")
    H.append("<li>Before 2026-09-22 no campaign interleaved CPU-attention and FPGA-attention repetitions. The runtron campaign of that day (section 7) did, inside each of its 3 repetitions, and reports the attention-mode comparison as ratios of means. Earlier, runtron ran them in blocks 8 minutes to about 2 hours apart (wedperf: CPU 18:34 to 19:37 UTC and FPGA 19:46 to 19:59, wedperf-attr: CPU 21:50 to 22:03 and FPGA 22:11 to 23:54). The whole-machine pair spans two campaigns two days apart. No paired t for attention mode exists in sections 1 to 5. The Welch t values there compare separate blocks.</li>")
    H.append("<li>At prompt 1024 in the earlier campaigns (sections 1 to 3) the FPGA-side n is small: one pass in canon-ci and the nightly, n = 1 in vnnik4-models, n = 2 in wedperf. Only wedperf-attr (n = 6) and p0perf-20260913 (n = 3) have repeats there. The 2026-09-21/22 campaigns of sections 5 to 7 have 3 passes or repetitions per arm. The four wedperf pairs (n = 3 against 2) have about 1 degree of freedom.</li>")
    H.append("<li>Client host load inflates client-side TTFT. The ci-mimic base arm (556 ms) ran on a saturated client and is not used for a delta. The ci-mimic target arm (504 ms) ran at client CPU pressure 27 to 48 %. q4b-swattn recorded no client CPU pressure. The nightly's runner never does.</li>")
    H.append("<li>No canonical-AMX CPU-attention runtron cell at tp4 exists on the same day as an FPGA cell. The tp4 canonical row in figure 1 pairs two different builds (544ca05c7a against c7844ca2ce) and is drawn hollow.</li>")
    H.append("<li>FPGA-attention cells above prompt 1024 (sections 5 and 6) are three passes per arm, run on 2026-09-21 evening and 2026-09-22 afternoon (UTC), with pass-to-pass sd of 16 to 128 ms below 4096 and 118 to 793 ms from 4096 up. Their warm values depend on the prefix-cache share of the cell (12 to 54 %) and, at 4096 to 6144, on the share of attention that fell back to the CPU when the card\'s K/V space ran out (section 5). Hypothesis for the fpgabase line not being monotone: both shares vary from cell to cell, so the TTFT does not track the uncached-token count alone. The cold cells have neither dependence.</li>")
    H.append("<li>At prompt 1024 (sections 1 to 3) the runtron 8-user TTFT is the batched prefill of 8 prompts of 1024 tokens. The CI-harness TTFT is per request with 2 or 4 prompts per engine. Their ratio there (about 4.3x at tp2, 2.6x at tp4) is a layout effect, not an attention-path effect. Section 7 uses the same runtron measure at 2048 to 8192 and never mixes it with CI-harness values.</li>")
    H.append("</ul>")
    H.append("<h3>Data files</h3>")
    H.append('<div class="tw"><table><thead><tr><th>campaign</th><th>what</th><th>file</th></tr></thead><tbody>')
    rows = [
        ("p0perf-20260913", "CI harness, our half, off/on/fpga, one binary 544ca05c7a; runtron off/on", rel_ref(P0) + " lines 12-17 (CI table), 44-61 (CI per-rep), 6-9 and 20-43 (runtron); summary.json"),
        ("wedperf-20260916", "runtron cpu and fpga blocks, base eb2de0265a vs target ff680c8020", rel_ref(WP) + " lines 21-34 (means); summary.json cells[].reps[].ttft_s (per-rep)"),
        ("wedperf-attr-20260916", "runtron attribution: base / mid c7844ca2ce / target, cpu and fpga", rel_ref(WA) + " lines 13-27 (means); summary.json (per-rep)"),
        ("vnnik4-20260915, vnnik4-models-20260915", "runtron cpu (base vs ab) and the fpga cell (base vs new), 2026-09-15", rel_ref(V4) + " lines 9-10; " + rel_ref(V4M) + " lines 58-97"),
        ("q4b-swattn-20260919", "CI harness, whole machine, CPU attention, nightly deb vs canonical deb, 9 prompts", rel_ref(QS) + " lines 3-13; summary.json (cache_hit_pct, engine_requests); RUNBOOK.md lines 33-39 (check cell)"),
        ("q4b-fpga-20260921", "CI harness, whole machine, FPGA attention (nightly deb, canonical deb) + one canonical CPU pass; cold cells at 4096 / 8192; platformd 0.11", "exec/results/q4b-fpga-20260921/<tag>/perf.json (fpgabase-pass1, fpgacanon-pass1, canon-pass1, *-cold-p4096, *-cold-p8192); RUNBOOK.md; exec/prefill-amx-vs-fpga-20260921/fpga-campaign-rows.json"),
        ("q4b-rt8u-20260922", "runtron, our half, one tp2 engine, 8 or 2 users, prompts 1024 to 8192, CPU and FPGA attention, AVX build (eb2de0265a) and AMX build (c7844ca2ce), 3 repetitions (2026-09-22 16:58 to 18:12 UTC)", "exec/results/q4b-rt8u-20260922/summary.md, summary.json, rt-results.txt, rt/<cell>__<attn>__<arm>__rep<k>.log"),
        ("canon-ci-20260918", "CI harness, whole machine, canonical deb, FPGA attention (2026-09-18 23:48 UTC)", rel_ref(CC) + " lines 36-37; canon/driver.log"),
        ("ci-mimic-20260918", "CI harness, whole machine, nightly deb and VNNI-K deb, FPGA attention", rel_ref(CMB) + " and target-pass1/summary.txt lines 36-37; caveats.html"),
        ("nightly 2026-09-18", "the 2026-09-18 nightly perf log (GitHub run 35303980268): qwen3-4b tp2 528 ms, tp4 636 ms", "exec/results/ci-mimic-20260918/reference/nightly-0918.arm.json lines 896, 999; nightly-35303980268.log"),
        ("nightly reference", "13 nights (2026-09-05 to 09-17) of the nightly's qwen3-4b TTFT", rel_ref(NS)),
        ("issue4500-20260918", "runtron FPGA-attention blocks m1-m4; block m6 rinzler + CI client on our half", rel_ref(I45) + " lines 9-20; " + rel_ref(M6) + " lines 5-12"),
        ("vnnik-20260914", "runtron CPU attention at prompts 1024 / 2048 / 8192", rel_ref(SCALING_REF)),
        ("workflows", "extraction rows (253), the three code readings, and the 162 verification findings", "exec/prefill-amx-vs-fpga-20260921/rows-extracted.json, pairs.json; journals wf_258257df-233, wf_89cf57ff-912"),
    ]
    for c, w, f in rows:
        H.append(f"<tr><td>{esc(c)}</td><td>{esc(w)}</td><td><code>{esc(f)}</code></td></tr>")
    H.append("</tbody></table></div>")
    H.append("</main>")
    return "\n".join(H)


def main():
    html = page()
    bad = [c for c in html if ord(c) > 127]
    assert not bad, f"non-ASCII characters in output: {sorted(set(bad))[:10]}"
    with open(OUT, "w") as f:
        f.write(html)
    print(OUT, len(html), "bytes")
    # dump the pairs for the verifier
    with open(os.path.join(HERE, "pairs.json"), "w") as f:
        json.dump([dict(setup=p["setup"], group=p["group"], kernel=p["kernel"],
                        cpu_mean=p["cpu"]["mean"], cpu_n=p["cpu"]["n"], cpu_reps=p["cpu"]["reps"], cpu_ref=p["cpu"]["ref"],
                        fpga_mean=p["fpga"]["mean"], fpga_n=p["fpga"]["n"], fpga_reps=p["fpga"]["reps"], fpga_ref=p["fpga"]["ref"],
                        delta_ms=p["delta_ms"], pct=p["pct"], t=p["t"], df=p["df"], note=p["note"]) for p in PAIRS], f, indent=1)
    for p in PAIRS:
        print(f'{p["group"]:2s} {KSHORT[p["kernel"]]:14s} {p["setup"][:60]:60s} cpu {p["cpu"]["mean"]:8.1f} (n{p["cpu"]["n"]}) fpga {p["fpga"]["mean"]:8.1f} (n{p["fpga"]["n"]}) d {p["delta_ms"]:+7.1f} ms {p["pct"]:+5.1f} % t {tstr(p["t"])}')


if __name__ == "__main__":
    main()
