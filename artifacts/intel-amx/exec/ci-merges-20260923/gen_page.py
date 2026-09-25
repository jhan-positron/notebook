#!/usr/bin/env python3
"""Generate the CI merge audit page (2026-09-23).

Reads numbers.json (from calc_numbers.py) and writes
~/workspace/intel-AMX/CI-test/status/CI-merges-20260923.html.
Every number on the page comes from numbers.json or from the merge
list below (git log / gh pr view, read 2026-09-23).
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "CI-test", "status",
                   "CI-merges-20260923.html")
N = json.load(open(os.path.join(HERE, "numbers.json")))
H = N["headline"]

esc = html.escape


def pct(v, nd=1):
    s = f"{v:+.{nd}f}"
    return s.replace("-", "−") + " %"


def num(v, nd=2):
    s = f"{v:,.{nd}f}"
    return s.replace("-", "−")


# --------------------------------------------------------------------------
# Row metadata (model facts: config/models.yaml, rinzler journal 2026-09-23)
# --------------------------------------------------------------------------
ROWS = [
    # key (model, users, prompt), short label, tags, group
    (("llama-3.2-3b-instruct-fast-tp2", 32, 200), "llama-3.2-3b tp2", "32 users · prompt 200", "hw2"),
    (("llama-3.1-8b-instruct-good-tp2", 8, 1024), "llama-3.1-8b tp2", "8 users · AMX shape", "hw2"),
    (("llama-3.3-70b-instruct-good-tp2", 8, 1024), "llama-3.3-70b tp2", "8 users", "hw2"),
    (("llama-3.3-70b-instruct-good-tp2", 4, 1024), "llama-3.3-70b tp2", "4 users", "hw2"),
    (("mixtral-8x7b-instruct-v0.1-tp2", 8, 1024), "mixtral-8x7b tp2", "AMX shape · MoE", "hw2"),
    (("qwen-2.5-32b-it-fast-tp2", 8, 1024), "qwen-2.5-32b tp2", "8 users", "hw2"),
    (("gemma-2-9b-it-fast-tp2", 8, 1024), "gemma-2-9b tp2", "sliding window", "hw2"),
    (("llama-3.3-70b-instruct-good-tp4", 4, 1024), "llama-3.3-70b tp4", "4 users", "hw4"),
    (("ingested-qwen-3-4b-instruct-2507-tp2", 8, 1024), "qwen-3-4b tp2", "FPGA attn · AMX shape", "gen_fpga"),
    (("ingested-qwen-3-4b-instruct-2507-tp4", 8, 1024), "qwen-3-4b tp4", "FPGA attn · AMX shape", "gen_fpga"),
    (("ingested-gpt-oss-120b-tp4", 8, 1024), "gpt-oss-120b tp4", "FPGA attn · sliding · MoE", "gen_fpga"),
    (("ingested-gemma-4-31b-it-tp2", 8, 1024), "gemma-4-31b tp2", "sliding window", "gen_sw"),
    (("llama-3.1-8b-instruct-good-tp2", 32, 4096), "llama-3.1-8b tp2", "32 users · prompt 4096", "amx"),
]
GROUPS = {
    "hw2": "Hand-written models, tp2",
    "hw4": "Hand-written model, tp4",
    "gen_fpga": "Generated models, FPGA attention on",
    "gen_sw": "Generated model, software attention",
    "amx": "The AMX benchmark row (1 prior night)",
}


def find(mach, key):
    for r in N[mach]:
        if (r["model"], r["users"], r["prompt"]) == key:
            return r
    raise KeyError(key)


# --------------------------------------------------------------------------
# Merge list: 32 first-parent merges 3faba6d0..5cf65b92, grouped by reach.
# (pr, title, mergedAt UTC, what changes, reaches AMX row, other rows, evidence)
# --------------------------------------------------------------------------
META = {}
for line in open(os.path.join(HERE, "prmeta.txt")):
    pr, merged, author, title = line.rstrip("\n").split("|", 3)
    META[int(pr)] = dict(merged=merged, author=author, title=title.strip())
SHA = {}
for line in open(os.path.join(HERE, "merges.txt")):
    sha, pr, files, ins, dels = line.rstrip("\n").split("|")
    SHA[int(pr)] = dict(sha=sha, files=int(files), ins=int(ins or 0), dels=int(dels or 0))

BUCKETS = [
    ("A", "The AMX switch",
     "Turns the AMX kernels on in the nightly package.", [
         (4505, "The <code>deb</code> build preset now sets <code>TRON_AMX_DISPATCH=ON</code>, so the package carries the AMX kernels.",
          "Yes. This is the intended change.",
          "Rows with head size 128 and 4 query heads per KV head: both llama-3.1-8b rows, mixtral-8x7b, and the software part of qwen-3-4b (positions below 127).",
          "CMakePresets.json diff. Build log of publish-deb run 35806901506 shows <code>TRON_AMX_DISPATCH=\"ON\"</code>. The installed rinzler holds the kill-switch text once (the old package: 0 times)."),
     ]),
    ("B", "Change code that the AMX row runs",
     "These can change the AMX row itself. Together they have at most +0.29 TPS to explain.", [
         (4534, "Removes two process-wide atomic counter updates from every timed wait. The counters are now behind <code>TRON_MWAIT_STATS</code>, default OFF.",
          "Yes. Every worker thread of every engine uses timed waits.",
          "All rows. The effect is likely largest on Intel tp4 engines (see section 4).",
          "src/system/mwaitx.cpp:18-19, 198-200 at 3faba6d0. PR text: “Those updates add contention during inference.” PR diagnostic: +6.9 % to +11.3 % decode per user on 4-card gpt-oss-20b."),
         (4205, "Compiles model code in one object file per model family, instead of numbered group files inside the tron library. The compile options are copied.",
          "Yes. The llama-3.1-8b code is rebuilt in a new object file.",
          "All rows.",
          "src/tron/CMakeLists.txt:268-349 at 5cf65b92. The copied option list matches the tron library's list. PR invariant: “compile flags, LTO … remain unchanged.” Effect not measured."),
         (4203, "Adds a model-family filter to the model-definition generator (config/model_definitions.py). #4205 uses it.",
          "Only through #4205.",
          "All rows, through #4205.",
          "PR invariant: without a filter, selection and ordering keep current behavior."),
         (4456, "Releases old sliding-window KV chunks under memory pressure. For every model, it also records one token position per pin.",
          "Yes, but tiny: a few vector operations and one pressure check per request step.",
          "gemma-2-9b, gemma-4-31b, gpt-oss-120b (sliding-window layers).",
          "src/tron/scheduler/full.cpp:80, 193 and 201, token_cache.cpp:159-161. Note [Sliding-window KV reclamation]: “No reclamation tree walk is needed when pressure is absent.”"),
     ]),
    ("C", "Change code that only other rows run",
     "These cannot change the AMX row. Some of them explain the other rows that moved.", [
         (4258, "Merges FPGA attention results as each card finishes, instead of in launch order.",
          "No. llama-3.1-8b runs software attention, and the software-only branch does the same merge as before.",
          "qwen-3-4b tp2 and tp4, gpt-oss-120b tp4 (FPGA attention on in CI).",
          "self_attention.hpp:1193, 1234-1252. rinzler log 09-23 04:05:52: “HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2'”. PR: 8-user llama-3.1-8b with FPGA attention off “equivalent”. PR: 8-user gpt-oss-120b at 2K prompt, TTFT −2.07 %."),
         (4455, "Stores sliding-window KV in separate chunks of at most 256 MiB. Sliding layers need one chunk lookup per page.",
          "No. Full-history models keep direct K/V indexing, and the new checks return early.",
          "gemma-2-9b, gemma-4-31b, gpt-oss-120b.",
          "kv_cache.hpp:578-580: “Uniform full-history views preselect their base pointer when the view changes, so inner K/V access performs direct indexing.”"),
         (4531, "Changes which card gets each non-expert tensor tile when experts are placed by measured load.",
          "No. llama-3.1-8b is not a mixture-of-experts model.",
          "gpt-oss-120b tp4 only. Mixtral has no load profile, so it keeps the default placement.",
          "placer.cpp, ExpertsByPlan. rinzler log 09-23 05:19:19: “Using ExpertsByPlan placement strategy with device_count=4”. Log 04:57:13: “No expert-load profile at … Mixtral … using defaults”."),
         (4159, "Ingest compiler: moves the parameter tensor fields into one record type.",
          "No. llama-3.1-8b is hand-written (config/models.yaml: source hand_authored).",
          "Generated models: qwen-3-4b, gpt-oss-120b, gemma-4-31b.",
          "PR: a refactor that keeps behavior. Generated code not diffed."),
         (4302, "Ingest compiler: moves the RoPE inverse-frequency fields into one record type.",
          "No (hand-written model).",
          "Generated models.",
          "PR: “Keep all geometry, validation and numerical behavior.”"),
         (4449, "Ingest compiler: separates routing names from numeric bounds in size types.",
          "No (hand-written model).",
          "Generated models.",
          "PR: “Lowering and C++ generation remain unchanged.”"),
         (4450, "Ingest compiler: makes channel iteration spaces traversable.",
          "No (hand-written model).",
          "Generated models.",
          "PR: “generated C++ retain their existing behavior.”"),
         (4451, "Ingest compiler: resolves named loop bounds to the config field or loop variable.",
          "No (hand-written model).",
          "Generated models.",
          "PR: fixes bounds that named a C++ variable that does not exist. Code that already compiled keeps its loops."),
         (4475, "Ingest compiler: removes unused MoE kernel metadata.",
          "No (hand-written model).",
          "Generated MoE models (gpt-oss-120b).",
          "PR: “leaves generated kernel signatures and execution unchanged.”"),
         (4476, "Ingest compiler: removes expert-view initialization statements that never ran.",
          "No (hand-written model).",
          "Generated MoE models (gpt-oss-120b).",
          "PR: “Generated C++ execution is unchanged.”"),
         (4479, "Ingest compiler: prints empty generated blocks as <code>{}</code>.",
          "No (hand-written model).",
          "Generated models (text only).",
          "PR: “generated behavior is unchanged.”"),
     ]),
    ("D", "Run at model load or for tracing only",
     "These run once per model load, or only when tracing or placement logging is on.", [
         (4519, "Replaces an empty placement strategy with an explicit all-devices strategy.",
          "Load time only. The placement stays the same.",
          "—",
          "placer.cpp: the old empty strategy also placed every tensor on all devices."),
         (4520, "Prints the tensor placement report once per load.",
          "Load time only, and only with <code>TRON_LOG_PLACEMENT</code>.",
          "—",
          "placer.cpp."),
         (4529, "Renames <code>start_placing</code> to <code>begin_tensor</code>.",
          "No. Rename only.",
          "—",
          "placer.hpp, placer.cpp."),
         (4299, "Closes the generation trace slice after the schedulers stop.",
          "No. Tracing only.",
          "—",
          "h/runtron/stream_generate.hpp."),
     ]),
    ("E", "No effect on the shipped program",
     "CI, build tooling, tests, data files, and a header move.", [
         (4510, "Adds the job permissions that the nightly package build needs.",
          "No. It is why the package could be built again.",
          "—",
          "publish-deb.yml. The build had failed to start on 09-19, 09-20, 09-21 and 09-22."),
         (4516, "Refreshes CI unit-test run times for this CPU model. CI uses them to pack test jobs onto machine slices.",
          "No. “Slice” here is a CI test shard, not a runtime setting.",
          "—",
          "config/test-benchmarks.json only. This corrects this morning's page, which named it as a candidate."),
         (4008, "Moves the quantized weight layout definitions to their own header, with the same values.",
          "No.",
          "—",
          "tensor.hpp, weight_format.hpp: same GROUPS_PER_STRIP, strip layout (576 bytes), COLUMNS_PER_FETCHER, SYSTOLIC_COLUMNS."),
         (4447, "Narrows the CI and lint toolchains.",
          "No.",
          "—",
          "Workflows, flake.nix, and the lint-notes target of GNUmakefile."),
         (4452, "Runs Nix cleanup after failed CI builds.",
          "No.", "—", "CI workflow and scripts."),
         (4501, "Keeps Git metadata out of Nix build inputs.",
          "No.", "—", "nix/, CI tests."),
         (4496, "Evaluates the Nix build recipe before the lab build.",
          "No.", "—", "CI workflow, nix/."),
         (4503, "Tolerates cleanup races between CI jobs.",
          "No.", "—", "CI scripts."),
         (4524, "Sends remote developer builds to the sw-build queue.",
          "No.", "—", "bin/bsub-build, README."),
         (4537, "Downloads the pinned Ministral model files in CI.",
          "No.", "—", "bin/ci/prime_hf_models.py."),
         (4502, "Removes two speculation tests.",
          "No.", "—", "t/ and test timing data."),
         (4431, "Fixes a NaN marker test.",
          "No.", "—", "t/t_threading.cpp."),
     ]),
]
assert sum(len(b[3]) for b in BUCKETS) == 32, "expected 32 merges"
assert {m[0] for b in BUCKETS for m in b[3]} == set(META), "merge set mismatch"


def merged_short(pr):
    m = META[pr]["merged"]  # 2026-09-22T21:14:51Z
    return m[5:10] + " " + m[11:16]


# --------------------------------------------------------------------------
# Figure 1: dumbbell, TPS and prefill rate, shared row labels
# --------------------------------------------------------------------------
def fig_dumbbell():
    rows = [
        dict(label="Nightly CI, delphi-3bda (Intel)", sub="09-22 old package → 09-23 new package",
             tps=(H["ci22_tps"], H["ci23_tps"]), pre=(H["ci22_prefill"], H["ci23_prefill"])),
        dict(label="Our test, delphi-3bda, 2026-09-20", sub="code 3faba6d0 without → with AMX kernels",
             tps=(H["base_tps"], H["canon_tps"]), pre=(H["base_prefill"], H["canon_prefill"])),
        dict(label="Nightly CI, andoria-b1a3 (AMD)", sub="same two packages, no AMX unit",
             tps=(H["amd22_tps"], H["amd23_tps"]), pre=(H["amd22_prefill"], H["amd23_prefill"])),
    ]
    LW = 300          # label column
    PW = 300          # panel width
    GAP = 44
    TOP = 52
    RH = 70
    W = LW + PW + GAP + PW + 24
    Hh = TOP + RH * len(rows) + 46
    p1 = (LW, LW + PW)
    p2 = (LW + PW + GAP, LW + PW + GAP + PW)
    s1 = (27.0, 34.0)
    s2 = (200.0, 380.0)

    def X(v, p, s):
        return p[0] + (v - s[0]) / (s[1] - s[0]) * (p[1] - p[0])

    o = [f'<svg class="fig" viewBox="0 0 {W} {Hh}" role="img" aria-labelledby="f1t f1d">',
         '<title id="f1t">Decode speed and prefill rate of the 32-user llama-3.1-8b row</title>',
         '<desc id="f1d">Dumbbell chart. Intel CI 28.25 to 32.49 TPS, our same-code test 28.25 to 32.21 TPS, AMD CI 29.00 to 28.91 TPS. Prefill rate: 219.7 to 354.0, 215.2 to 356.8, 308.8 to 307.4 tokens per second.</desc>']
    # panel titles
    o.append(f'<text class="ptitle" x="{p1[0]}" y="18">Decode speed, TPS per user</text>')
    o.append(f'<text class="ptitle" x="{p2[0]}" y="18">Prefill rate, tok/s (4096 / mean TTFT)</text>')
    # grids + axis ticks
    for p, s, ticks, fmt in ((p1, s1, [27, 28, 29, 30, 31, 32, 33, 34], "{:.0f}"),
                             (p2, s2, [200, 240, 280, 320, 360], "{:.0f}")):
        for t in ticks:
            x = X(t, p, s)
            o.append(f'<line class="grid" x1="{x:.1f}" y1="{TOP - 10}" x2="{x:.1f}" y2="{TOP + RH * len(rows) - 14}"/>')
            o.append(f'<text class="tick" x="{x:.1f}" y="{TOP + RH * len(rows) + 4}" text-anchor="middle">{fmt.format(t)}</text>')
    for i, r in enumerate(rows):
        y0 = TOP + RH * i
        yt = y0 + 30
        o.append(f'<text class="rlabel" x="0" y="{y0 + 22}">{esc(r["label"])}</text>')
        o.append(f'<text class="rsub" x="0" y="{y0 + 40}">{esc(r["sub"])}</text>')
        for key, p, s, fmtv, unit in (("tps", p1, s1, "{:.2f}", "TPS"), ("pre", p2, s2, "{:.1f}", "tok/s")):
            a, b = r[key]
            xa, xb = X(a, p, s), X(b, p, s)
            o.append(f'<line class="track" x1="{min(xa, xb):.1f}" y1="{yt}" x2="{max(xa, xb):.1f}" y2="{yt}"/>')
            d = 100 * (b / a - 1)
            # value labels: avoid collision when the two dots are close
            if abs(xb - xa) < 64:
                left, right = (xa, a, "old"), (xb, b, "new")
                if xb < xa:
                    left, right = (xb, b, "new"), (xa, a, "old")
                o.append(f'<text class="vlab" x="{left[0] - 9:.1f}" y="{yt + 4}" text-anchor="end">{fmtv.format(left[1])}</text>')
                o.append(f'<text class="vlab" x="{right[0] + 9:.1f}" y="{yt + 4}">{fmtv.format(right[1])}</text>')
                o.append(f'<text class="dlab" x="{right[0] + 9:.1f}" y="{yt + 20}">{pct(d)}</text>')
            else:
                o.append(f'<text class="vlab" x="{xa:.1f}" y="{yt - 11}" text-anchor="middle">{fmtv.format(a)}</text>')
                o.append(f'<text class="vlab" x="{xb:.1f}" y="{yt - 11}" text-anchor="middle">{fmtv.format(b)}</text>')
                o.append(f'<text class="dlab" x="{(xa + xb) / 2:.1f}" y="{yt + 20}" text-anchor="middle">{pct(d)}</text>')
            tip_a = f'{r["label"]} | package without AMX kernels | {fmtv.format(a)} {unit}'
            tip_b = f'{r["label"]} | package with AMX kernels | {fmtv.format(b)} {unit}'
            for x, cls, tip in ((xa, "old", tip_a), (xb, "new", tip_b)):
                o.append(f'<circle class="dot {cls}" cx="{x:.1f}" cy="{yt}" r="6"/>')
                o.append(f'<circle class="hit" cx="{x:.1f}" cy="{yt}" r="13" tabindex="0" data-tip="{esc(tip)}"/>')
    # residual guide: a vertical line at the CI 09-23 value, dropped from row 1's
    # orange dot to just above row 2's value labels (row 2's orange dot is our canon).
    xg = X(H["ci23_tps"], p1, s1)
    y1 = TOP + 30
    y2 = TOP + RH + 30
    o.append(f'<line class="guide" x1="{xg:.1f}" y1="{y1 + 8}" x2="{xg:.1f}" y2="{y2 - 25}"/>')
    o.append(f'<text class="glab" x="{xg + 6:.1f}" y="{y1 + 38}">+{H["resid_tps"]:.2f} TPS above our canon</text>')
    o.append(f'<text class="tick" x="{p1[1]:.1f}" y="{TOP + RH * len(rows) + 22}" text-anchor="end">TPS</text>')
    o.append(f'<text class="tick" x="{p2[1]:.1f}" y="{TOP + RH * len(rows) + 22}" text-anchor="end">tok/s</text>')
    o.append('</svg>')
    return "\n".join(o)


# --------------------------------------------------------------------------
# Figure 2: the 32 merges as units, grouped by reach (HTML)
# --------------------------------------------------------------------------
def fig_units():
    o = ['<div class="units" role="img" aria-label="32 merges grouped by how far their code reaches">']
    for code, name, blurb, items in BUCKETS:
        o.append(f'<div class="urow"><div class="uname"><span class="ucount">{len(items)}</span> {esc(name)}</div><div class="ucells">')
        for m in items:
            pr = m[0]
            o.append(f'<a class="u u{code}" href="#pr{pr}" title="#{pr} {esc(META[pr]["title"])}">{pr}</a>')
        o.append('</div></div>')
    o.append('</div>')
    return "\n".join(o)


# --------------------------------------------------------------------------
# Figure 3: wall-clock lanes of one 10 us timed wait (est.)
# --------------------------------------------------------------------------
def fig_lanes():
    W, LW = 1000, 180
    x0, x1 = LW, W - 30
    T = 11.0  # microseconds shown
    def X(t):
        return x0 + t / T * (x1 - x0)
    budget = H["rtm_budget_ns_est"] / 1000.0   # us per RTM pass
    passes = int(-(-10.0 // budget))            # ceil(10 / budget)
    o = [f'<svg class="fig" viewBox="0 0 {W} 230" role="img" aria-labelledby="f3t f3d">',
         '<title id="f3t">Counter updates during one 10 microsecond timed wait</title>',
         f'<desc id="f3d">AMD MWAITX path: one sleep and 2 counter updates. Intel RTM path: {passes} passes of about {budget:.2f} microseconds and {passes + 1} counter updates. Estimated from code constants.</desc>']
    for t in range(0, 12):
        x = X(t)
        o.append(f'<line class="grid" x1="{x:.1f}" y1="30" x2="{x:.1f}" y2="186"/>')
        o.append(f'<text class="tick" x="{x:.1f}" y="204" text-anchor="middle">{t}</text>')
    o.append(f'<text class="tick" x="{x1:.1f}" y="222" text-anchor="end">microseconds since the wait began (to scale, est.)</text>')
    # deadline marker
    xd = X(10.0)
    o.append(f'<line class="deadline" x1="{xd:.1f}" y1="24" x2="{xd:.1f}" y2="190"/>')
    o.append(f'<text class="tick" x="{xd - 4:.1f}" y="20" text-anchor="end">10 µs timeout</text>')
    # AMD lane
    ya = 54
    o.append(f'<text class="rlabel" x="0" y="{ya + 6}">AMD · MWAITX</text>')
    o.append(f'<text class="rsub" x="0" y="{ya + 24}">1 pass · 2 updates</text>')
    o.append(f'<rect class="wait" x="{X(0):.1f}" y="{ya - 14}" width="{X(10) - X(0):.1f}" height="28" rx="3"/>')
    o.append(f'<text class="inlab" x="{X(5):.1f}" y="{ya + 5}" text-anchor="middle">sleeps until the watched line changes or the timeout ends</text>')
    o.append(f'<line class="upd" x1="{X(0) + 1:.1f}" y1="{ya - 20}" x2="{X(0) + 1:.1f}" y2="{ya + 20}"/>')
    o.append(f'<line class="upd" x1="{X(0) + 5:.1f}" y1="{ya - 20}" x2="{X(0) + 5:.1f}" y2="{ya + 20}"/>')
    # Intel lane
    yi = 138
    o.append(f'<text class="rlabel" x="0" y="{yi + 6}">Intel · RTM</text>')
    o.append(f'<text class="rsub" x="0" y="{yi + 24}">{passes} passes · {passes + 1} updates</text>')
    for k in range(passes):
        a = k * budget
        b = a + budget
        o.append(f'<rect class="wait" x="{X(a) + 1.5:.1f}" y="{yi - 14}" width="{X(b) - X(a) - 3:.1f}" height="28" rx="3"/>')
        o.append(f'<line class="upd" x1="{X(a) + 1:.1f}" y1="{yi - 20}" x2="{X(a) + 1:.1f}" y2="{yi + 20}"/>')
    o.append(f'<line class="upd" x1="{X(0) + 5:.1f}" y1="{yi - 20}" x2="{X(0) + 5:.1f}" y2="{yi + 20}"/>')
    o.append(f'<text class="inlab" x="{X(budget / 2):.1f}" y="{yi - 22}" text-anchor="middle">one pass ≈ {budget * 1000:.0f} ns</text>')
    o.append('</svg>')
    return "\n".join(o), passes


# --------------------------------------------------------------------------
# Figures 4 and 5: 09-23 change vs same-package range, Intel | AMD
# --------------------------------------------------------------------------
def fig_dots(metric, xmin, xmax, ticks, include_amx, fid, title, desc):
    LW, PW, GAP = 330, 330, 64
    W = LW + PW + GAP + PW + 20
    TOP = 50
    RH = 30
    GH = 26
    rows = [r for r in ROWS if include_amx or r[3] != "amx"]
    # layout rows with group headers
    y = TOP
    lay = []
    last_g = None
    for key, lab, tag, g in rows:
        if g != last_g:
            lay.append(("group", g, y))
            y += GH
            last_g = g
        lay.append(("row", (key, lab, tag, g), y))
        y += RH
    Hh = y + 40
    panels = (("intel", "delphi-3bda (Intel)", LW), ("amd", "andoria-b1a3 (AMD)", LW + PW + GAP))

    def X(v, px):
        v = max(xmin, min(xmax, v))
        return px + (v - xmin) / (xmax - xmin) * PW

    o = [f'<svg class="fig" viewBox="0 0 {W} {Hh}" role="img" aria-labelledby="{fid}t {fid}d">',
         f'<title id="{fid}t">{esc(title)}</title>', f'<desc id="{fid}d">{esc(desc)}</desc>']
    for mach, ptitle, px in panels:
        o.append(f'<text class="ptitle" x="{px}" y="18">{esc(ptitle)}</text>')
        for t in ticks:
            x = X(t, px)
            o.append(f'<line class="{"zero" if t == 0 else "grid"}" x1="{x:.1f}" y1="{TOP - 8}" x2="{x:.1f}" y2="{Hh - 36}"/>')
            o.append(f'<text class="tick" x="{x:.1f}" y="{Hh - 20}" text-anchor="middle">{pct(t, 0) if t else "0"}</text>')
    for kind, item, yy in lay:
        if kind == "group":
            o.append(f'<text class="ghead" x="0" y="{yy + 17}">{esc(GROUPS[item])}</text>')
            continue
        key, lab, tag, g = item
        yc = yy + RH / 2
        o.append(f'<text class="rlabel2" x="0" y="{yc + 4:.1f}">{esc(lab)}</text>')
        o.append(f'<text class="rtag" x="134" y="{yc + 4:.1f}">{esc(tag)}</text>')
        for mach, ptitle, px in panels:
            r = find(mach, key)
            m = r[metric]
            unit = "TPS" if metric == "tps" else "ms"
            nd = 2 if metric == "tps" else 0
            if r["n_base"] > 1:
                xa, xb = X(m["lo_pct"], px), X(m["hi_pct"], px)
                o.append(f'<rect class="band" x="{xa - 3:.1f}" y="{yc - 5:.1f}" width="{xb - xa + 6:.1f}" height="10" rx="5"/>')
            else:
                x = X(0, px)
                o.append(f'<line class="prior" x1="{x:.1f}" y1="{yc - 7:.1f}" x2="{x:.1f}" y2="{yc + 7:.1f}"/>')
            xv = X(m["pct"], px)
            clipped = m["pct"] < xmin or m["pct"] > xmax
            o.append(f'<circle class="dot new" cx="{xv:.1f}" cy="{yc:.1f}" r="5"/>')
            moved = m.get("clearly_moved") or (r["n_base"] == 1 and abs(m["pct"]) >= 1.0)
            if moved or clipped:
                txt = pct(m["pct"]) + (" (off scale)" if clipped else "")
                # Put the label on the side away from the range band, and never
                # past the panel's right edge.
                left_side = (r["n_base"] > 1 and m["pct"] < m["lo_pct"]) or xv > px + PW - 70
                if left_side:
                    o.append(f'<text class="vlab" x="{xv - 9:.1f}" y="{yc + 4:.1f}" text-anchor="end">{txt}</text>')
                else:
                    o.append(f'<text class="vlab" x="{xv + 9:.1f}" y="{yc + 4:.1f}">{txt}</text>')
            nights = f'{r["n_base"]} old-package night' + ("s" if r["n_base"] > 1 else "")
            tip = (f'{lab} ({tag}) | {ptitle} | 09-23: {num(m["new"], nd)} {unit} | '
                   f'{pct(m["pct"])} vs mean of {nights} ({num(m["mean"], nd)} {unit}) | '
                   f'range {num(m["min"], nd)} to {num(m["max"], nd)} {unit}')
            o.append(f'<circle class="hit" cx="{xv:.1f}" cy="{yc:.1f}" r="12" tabindex="0" data-tip="{esc(tip)}"/>')
    o.append('</svg>')
    return "\n".join(o)


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def table_headline():
    rows = [
        ("Nightly CI, delphi-3bda, 09-22", "2026.09.18-3faba6d0 (no AMX kernels)", H["ci22_tps"], H["ci22_ttft"], H["ci22_prefill"], "320 samples"),
        ("Nightly CI, delphi-3bda, 09-23", "2026.09.23-5cf65b92 (AMX kernels in)", H["ci23_tps"], H["ci23_ttft"], H["ci23_prefill"], "320 samples"),
        ("Our test, base arm, 09-20", "2026.09.18-3faba6d0 (no AMX kernels)", H["base_tps"], H["base_ttft"], H["base_prefill"], "3 passes × 320"),
        ("Our test, canon arm, 09-20", "3faba6d0 + AMX build option", H["canon_tps"], H["canon_ttft"], H["canon_prefill"], "3 passes × 320"),
        ("Nightly CI, andoria-b1a3, 09-22", "2026.09.18-3faba6d0", H["amd22_tps"], H["amd22_ttft"], H["amd22_prefill"], "320 samples"),
        ("Nightly CI, andoria-b1a3, 09-23", "2026.09.23-5cf65b92 (kernels present, unused)", H["amd23_tps"], H["amd23_ttft"], H["amd23_prefill"], "320 samples"),
    ]
    o = ['<div class="tscroll"><table class="data"><thead><tr><th>Run</th><th>Package</th><th class="n">TPS mean</th><th class="n">TTFT, ms</th><th class="n">Prefill, tok/s</th><th>Samples</th></tr></thead><tbody>']
    for run, pkg, tps, ttft, pre, samp in rows:
        o.append(f'<tr><td>{esc(run)}</td><td><code>{esc(pkg)}</code></td><td class="n">{tps:.3f}</td><td class="n">{ttft:,.0f}</td><td class="n">{pre:.1f}</td><td>{samp}</td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


def table_merges():
    o = ['<div class="tscroll"><table class="merges"><thead><tr><th>PR</th><th>Title and merge time (UTC)</th><th>What it changes</th><th>Can it change the AMX row?</th><th>Other rows it can reach</th><th>Evidence</th></tr></thead>']
    for code, name, blurb, items in BUCKETS:
        o.append(f'<tbody><tr class="bhead"><td colspan="6"><span class="chip c{code}">{esc(name)}</span> {len(items)} merge{"s" if len(items) > 1 else ""}. {esc(blurb)}</td></tr>')
        for pr, what, reach, other, evid in items:
            m = META[pr]
            s = SHA[pr]
            o.append(
                f'<tr id="pr{pr}"><td class="prn"><a href="https://github.com/positron-ai/tron/pull/{pr}">#{pr}</a>'
                f'<div class="sha">{s["sha"]}</div><div class="sha">{s["files"]} files, +{s["ins"]} −{s["dels"]}</div></td>'
                f'<td><div class="ptitle2">{esc(m["title"])}</div><div class="when">{merged_short(pr)}</div></td>'
                f'<td>{what}</td><td>{reach}</td><td>{other}</td><td class="ev">{evid}</td></tr>')
        o.append('</tbody>')
    o.append('</table></div>')
    return "\n".join(o)


def table_rows():
    o = ['<div class="tscroll"><table class="data rows"><thead><tr><th rowspan="2">Row</th><th colspan="4" class="grp">delphi-3bda (Intel)</th><th colspan="4" class="grp">andoria-b1a3 (AMD)</th></tr>'
         '<tr><th class="n">TPS 09-23</th><th class="n">vs mean</th><th class="n">TTFT 09-23, ms</th><th class="n">vs mean</th>'
         '<th class="n">TPS 09-23</th><th class="n">vs mean</th><th class="n">TTFT 09-23, ms</th><th class="n">vs mean</th></tr></thead><tbody>']
    last = None
    for key, lab, tag, g in ROWS:
        if g != last:
            o.append(f'<tr class="bhead"><td colspan="9">{esc(GROUPS[g])}</td></tr>')
            last = g
        cells = []
        for mach in ("intel", "amd"):
            r = find(mach, key)
            for metric, nd in (("tps", 2), ("ttft", 0)):
                m = r[metric]
                moved = m.get("clearly_moved") or (r["n_base"] == 1 and abs(m["pct"]) >= 1.0)
                rng = f'range {num(m["min"], nd)}–{num(m["max"], nd)}' if r["n_base"] > 1 else "1 prior night"
                cls = "n moved" if moved else "n"
                note = '<div class="rng">clearly moved</div>' if moved else ""
                cells.append(f'<td class="n">{num(m["new"], nd)}<div class="rng">{rng}</div></td>')
                cells.append(f'<td class="{cls}">{pct(m["pct"])}{note}</td>')
        o.append(f'<tr><td>{esc(lab)}<div class="rng">{esc(tag)}</div></td>{"".join(cells)}</tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
lanes_svg, passes = fig_lanes()
i70 = find("intel", ROWS[7][0])["tps"]
a70 = find("amd", ROWS[7][0])["tps"]
iq4 = find("intel", ROWS[9][0])
aq4 = find("amd", ROWS[9][0])
igo = find("intel", ROWS[10][0])
ago = find("amd", ROWS[10][0])
ig4 = find("intel", ROWS[11][0])
ag4 = find("amd", ROWS[11][0])
imx = find("intel", ROWS[4][0])
amx_ = find("amd", ROWS[4][0])
i3b = find("intel", ROWS[0][0])
iq2 = find("intel", ROWS[8][0])
aq2 = find("amd", ROWS[8][0])
steps_ratio = i3b["tps"]["new"] / H["ci23_tps"]

CSS = """
:root{
  --ground:#f3f5f7; --surface:#ffffff; --ink:#161a20; --ink-2:#465061; --muted:#687283;
  --hair:#dfe3e9; --band:#cdd4de; --old:#2a78d6; --new:#eb6834; --link:#1c5cab;
  --uA:#eb6834; --uB:#1f2833; --uC:#7d8898; --uD:#c3cad4; --uE:#e6eaef; --upd:#d03b3b;
  --mono:"IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  --sans:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
body{background:var(--ground); color:var(--ink); font-family:var(--sans); font-size:15.5px; line-height:1.55;}
.wrap{max-width:1080px; margin:0 auto; padding-inline:20px; padding-block:28px 64px;}
header.top{padding-block:8px 18px; border-bottom:1px solid var(--hair); margin-bottom:22px;}
.eyebrow{font-family:var(--mono); font-size:12px; letter-spacing:.04em; color:var(--muted); text-transform:uppercase;}
h1{font-size:30px; line-height:1.2; margin:.3em 0 .35em; font-weight:600; text-wrap:balance; max-width:30ch;}
.meta{color:var(--ink-2); font-size:14px; max-width:80ch;}
h2{font-size:21px; font-weight:600; margin:2.1em 0 .5em; text-wrap:balance;}
h3{font-size:16.5px; font-weight:600; margin:1.6em 0 .4em;}
p, li{max-width:72ch;}
ul{padding-left:1.2em;} li{margin:.25em 0;}
a{color:var(--link);} a:focus-visible, .hit:focus-visible, .u:focus-visible{outline:2px solid var(--link); outline-offset:2px;}
code{font-family:var(--mono); font-size:.88em; background:#eaeef3; padding:.05em .3em; border-radius:3px;}
.cite{color:var(--muted); font-size:.9em;}
.short{background:var(--surface); border:1px solid var(--hair); border-radius:6px; padding:16px 20px; margin:6px 0 10px;}
.short h2{margin:0 0 .4em; font-size:17px;}
.short ul{margin:0;}
.words{columns:2 340px; column-gap:36px; font-size:14px; color:var(--ink-2); margin:0; padding:0;}
.words div{break-inside:avoid; margin:0 0 .55em;}
.words b{color:var(--ink); font-weight:600;}
figure{margin:18px 0 8px; background:var(--surface); border:1px solid var(--hair); border-radius:6px; padding:14px 14px 10px;}
figcaption{font-size:13.5px; color:var(--ink-2); margin-top:6px; max-width:none;}
figcaption b{color:var(--ink);}
.take{font-weight:600; color:var(--ink); margin:.2em 0 0; max-width:none;}
.figscroll{overflow-x:auto;}
svg.fig{display:block; width:100%; height:auto; min-width:820px; font-family:var(--sans);}
svg .ptitle{font-size:14px; font-weight:600; fill:var(--ink);}
svg .grid{stroke:var(--hair); stroke-width:1;}
svg .zero{stroke:#aeb7c3; stroke-width:1;}
svg .tick{font-size:12px; fill:var(--muted); font-variant-numeric:tabular-nums;}
svg .rlabel{font-size:14px; font-weight:600; fill:var(--ink);}
svg .rlabel2{font-size:13.5px; fill:var(--ink);}
svg .rsub{font-size:12.5px; fill:var(--ink-2);}
svg .rtag{font-size:12px; fill:var(--muted);}
svg .ghead{font-size:12px; font-weight:600; fill:var(--ink-2); letter-spacing:.03em; text-transform:uppercase;}
svg .track{stroke:#b9c1cc; stroke-width:2; stroke-linecap:round;}
svg .dot{stroke:var(--surface); stroke-width:2;}
svg .dot.old{fill:var(--old);} svg .dot.new{fill:var(--new);}
svg .hit{fill:transparent; cursor:default;}
svg .vlab{font-size:12.5px; fill:var(--ink); font-variant-numeric:tabular-nums;}
svg .dlab{font-size:12px; font-weight:600; fill:var(--ink-2);}
svg .guide{stroke:var(--new); stroke-width:1.5; opacity:.8;}
svg .glab{font-size:12px; fill:var(--ink); font-weight:600;}
svg .band{fill:var(--band);}
svg .prior{stroke:var(--ink-2); stroke-width:2;}
svg .wait{fill:none; stroke:#8e98a6; stroke-width:1.5; stroke-dasharray:5 4;}
svg .upd{stroke:var(--upd); stroke-width:3;}
svg .deadline{stroke:var(--ink-2); stroke-width:1;}
svg .inlab{font-size:12.5px; fill:var(--ink-2);}
.legend{display:flex; flex-wrap:wrap; gap:6px 20px; font-size:13px; color:var(--ink-2); margin:2px 0 8px;}
.legend span{display:inline-flex; align-items:center; gap:7px;}
.key{width:12px; height:12px; border-radius:50%; display:inline-block;}
.key.old{background:var(--old);} .key.new{background:var(--new);}
.key.band{width:26px; height:9px; border-radius:5px; background:var(--band);}
.key.upd{width:3px; height:14px; border-radius:0; background:var(--upd);}
.key.wait{width:24px; height:12px; border-radius:3px; border:1.5px dashed #8e98a6; background:none;}
.units{display:grid; gap:10px;}
.urow{display:grid; grid-template-columns:minmax(210px, 300px) 1fr; gap:12px; align-items:center;}
.uname{font-size:14px; color:var(--ink);}
.ucount{display:inline-block; min-width:1.8em; font-weight:600; font-variant-numeric:tabular-nums;}
.ucells{display:flex; flex-wrap:wrap; gap:4px;}
.u{display:inline-flex; align-items:center; justify-content:center; width:52px; height:30px; border-radius:4px; font-family:var(--mono); font-size:12.5px; text-decoration:none;}
.uA{background:var(--uA); color:#1a0d06;} .uB{background:var(--uB); color:#fff;} .uC{background:var(--uC); color:#fff;}
.uD{background:var(--uD); color:var(--ink);} .uE{background:var(--uE); color:var(--ink-2);}
@media (max-width:620px){ .urow{grid-template-columns:1fr; gap:4px;} h1{font-size:25px;} }
.tscroll{overflow-x:auto; margin:10px 0 6px; background:var(--surface); border:1px solid var(--hair); border-radius:6px;}
table{border-collapse:collapse; width:100%; font-size:13.5px;}
th, td{text-align:left; vertical-align:top; padding:8px 10px; border-bottom:1px solid var(--hair);}
th{font-weight:600; color:var(--ink-2); font-size:12.5px; background:#f8f9fb;}
th.grp{text-align:center;}
td.n, th.n{text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap;}
td.moved{font-weight:600;}
.rng{font-size:11.5px; color:var(--muted); font-weight:400;}
table.merges{min-width:1060px;}
table.merges td{font-size:13px;}
table.merges td.prn{white-space:nowrap; font-family:var(--mono); font-size:12.5px;}
.sha{font-family:var(--mono); font-size:11px; color:var(--muted);}
.ptitle2{font-weight:500;}
.when{font-family:var(--mono); font-size:11.5px; color:var(--muted); margin-top:2px;}
td.ev{color:var(--ink-2); font-size:12.5px;}
tr.bhead td{background:#f5f7fa; font-size:13px; color:var(--ink-2); padding-top:12px;}
table.rows{min-width:880px;}
.chip{display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px; font-weight:600; margin-right:6px;}
.cA{background:var(--uA); color:#1a0d06;} .cB{background:var(--uB); color:#fff;} .cC{background:var(--uC); color:#fff;}
.cD{background:var(--uD); color:var(--ink);} .cE{background:var(--uE); color:var(--ink-2); border:1px solid var(--hair);}
.callout{border-left:3px solid var(--new); padding:4px 0 4px 14px; margin:14px 0;}
.hyp{border-left:3px solid #9aa4b2; padding:4px 0 4px 14px; margin:12px 0;}
#tip{position:fixed; z-index:10; pointer-events:none; background:#161a20; color:#fff; font-size:12.5px; line-height:1.45; padding:7px 10px; border-radius:5px; max-width:340px; box-shadow:0 2px 8px rgba(0,0,0,.18);}
#tip b{font-weight:600;}
.src li{font-size:13.5px; color:var(--ink-2);}
@media (prefers-reduced-motion:reduce){ *{scroll-behavior:auto;} }
"""

JS = """
(function(){
  var tip = document.getElementById('tip');
  function show(el, x, y){
    var parts = (el.getAttribute('data-tip') || '').split(' | ');
    tip.textContent = '';
    parts.forEach(function(p, i){
      var line = document.createElement('div');
      if (i === 2) { var b = document.createElement('b'); b.textContent = p; line.appendChild(b); }
      else { line.textContent = p; }
      tip.appendChild(line);
    });
    tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var px = Math.min(window.innerWidth - w - 8, x + 14), py = y - h - 12;
    if (py < 8) py = y + 16;
    tip.style.left = px + 'px'; tip.style.top = py + 'px';
  }
  function hide(){ tip.hidden = true; }
  document.querySelectorAll('.hit').forEach(function(el){
    el.addEventListener('pointermove', function(e){ show(el, e.clientX, e.clientY); });
    el.addEventListener('pointerleave', hide);
    el.addEventListener('focus', function(){ var r = el.getBoundingClientRect(); show(el, r.left + r.width/2, r.top); });
    el.addEventListener('blur', hide);
  });
})();
"""

page = f"""<title>AMX Jump Merge Audit</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header class="top">
  <div class="eyebrow">delphi-3bda nightly CI · merge audit · written 2026-09-23</div>
  <h1>Did other merges change decode or prefill speed on 09-23?</h1>
  <div class="meta">Two nightly runs: 09-22 (tron 2026.09.18-3faba6d0, systems_test run 35683952944) and 09-23 (tron 2026.09.23-5cf65b92, run 35815209295). Between the two packages, 32 pull requests were merged into tron main. Each one was read and checked against the rows of both CI machines.</div>
</header>

<section class="short" aria-label="Short version">
  <h2>Short version</h2>
  <ul>
    <li>The AMX kernels explain almost all of the {pct(H['ci_gain_pct'])} decode gain of the 32-user llama-3.1-8b row: our own test of the old code with and without the kernels measured {pct(H['ab_gain_pct'])}.</li>
    <li>Only 4 of the other 31 merges can change code that this row runs, and together with setup differences they have at most +{H['resid_tps']:.2f} TPS ({pct(H['resid_pct_of_canon'])}) left to explain.</li>
    <li>Other merges did move other rows: #4258 made the FPGA-attention models faster on both CI machines, and #4534 is the likely cause of the Intel-only gains of the three tp4 rows.</li>
  </ul>
</section>

<h2 id="words">Words used here</h2>
<div class="words">
  <div><b>TPS</b>: decode speed, generated tokens per second for one user. The CI measures it between generated tokens 896 and 1024 of each request and averages all samples.</div>
  <div><b>TTFT</b>: time to first token, in milliseconds (ms). With 8 users per engine it includes the wait behind other users' prompts.</div>
  <div><b>Prefill rate</b>: prompt length divided by mean TTFT, in tokens per second (tok/s). The CI computes it on the client.</div>
  <div><b>AMX</b>: Advanced Matrix Extensions, the matrix unit of Intel Xeon CPUs such as the Xeon 6962P in delphi-3bda.</div>
  <div><b>AMX kernels</b>: tron's attention code that uses AMX. The build option <code>TRON_AMX_DISPATCH</code> compiles it in. It serves only models with head size 128 and 4 query heads per KV head ("AMX shape").</div>
  <div><b>Old / new package</b>: tron 2026.09.18-3faba6d0 (no AMX kernels, ran 09-18 to 09-22) and tron 2026.09.23-5cf65b92 (AMX kernels in, ran 09-23).</div>
  <div><b>Merge, #NNNN</b>: one pull request merged into tron main, named by its number.</div>
  <div><b>delphi-3bda, andoria-b1a3</b>: the two CI machines. delphi-3bda has an Intel Xeon 6962P (has AMX). andoria-b1a3 has an AMD Genoa CPU (no AMX unit). Both ran the same two packages.</div>
  <div><b>Engine</b>: one rinzler server process. rinzler is the server program in the tron package.</div>
  <div><b>tp2, tp4</b>: the model is split over 2 or 4 accelerator cards (tensor parallel). A tp2 row runs 4 engines of 2 cards. A tp4 row runs 2 engines of 4 cards.</div>
  <div><b>Hand-written, generated model</b>: C++ model code written by hand (<code>hand_authored</code> in config/models.yaml), or produced by the ingest compiler (<code>generated</code>, and CI names start with "ingested-").</div>
  <div><b>FPGA attention</b>: attention computed on the accelerator cards ("hardware attention", <code>USE_HW_ATTN</code>). In the CI it is on for qwen-3-4b and gpt-oss-120b only.</div>
  <div><b>Sliding-window attention</b>: layers that look back only a fixed number of tokens (gemma-2, gemma-4, gpt-oss).</div>
  <div><b>MoE, expert placement</b>: mixture-of-experts models (mixtral, gpt-oss), and the rule that decides which card holds each expert's weights.</div>
  <div><b>Timed wait</b>: tron's wait loop with a timeout (src/system/mwaitx.cpp). Worker threads use it between layers and for card events.</div>
  <div><b>RTM, MWAITX</b>: the CPU instructions that the timed wait uses to sleep until memory changes: Intel's transactional memory (RTM, part of TSX) and AMD's monitor-wait (MWAITX).</div>
  <div><b>Same-package range</b>: lowest to highest value of a row over the nights with the old package: delphi-3bda 09-18 to 09-22 (5 nights), andoria-b1a3 09-19 to 09-22 (4 nights, without its cancelled 09-18 run).</div>
  <div><b>Clearly moved</b>: the 09-23 value lies outside the same-package range by more than the range's own width, and differs from the mean by at least 1 % (and by at least 3 ms for TTFT). A value just outside the range proves little: with 5 nights it happens by chance in about 1 of 3 cases.</div>
  <div><b>Base, canon</b>: the two builds of our 2026-09-20 test on delphi-3bda. Base is the old package. Canon is the same code (3faba6d0) built with the AMX option.</div>
</div>

<h2 id="changed">1. What changed between the two nights</h2>
<p>Four things could differ between the two runs: the tron package, the test harness, the machine, and the benchmark itself. Only the tron package changed in a way that can affect speed.</p>
<ul>
  <li><b>tron package.</b> The CI replaced the old package with the new one. The new package holds 32 more merges (102 commits) <span class="cite">[git log --first-parent 3faba6d0..5cf65b92]</span>. Both packages were built with Clang 19.1.7. Their CMake settings differ only in <code>TRON_AMX_DISPATCH="ON"</code> <span class="cite">[configure output of publish-deb runs 35295875031 and 35806901506]</span>.</li>
  <li><b>Why 32 merges at once.</b> The nightly package build failed to start on 09-19, 09-20, 09-21 and 09-22 <span class="cite">[publish-deb runs 35413074014, 35481888971, 35551712750, 35676322727: startup_failure]</span>. #4510 fixed its permissions. The build at 2026-09-23 01:35 UTC took main at 5cf65b92.</li>
  <li><b>Test harness.</b> systems_test moved from 7327184 to 5b2250b9 (12 files). The logged benchmark settings are identical: 32 users, 10 rounds, prompt 4096 tokens, 1536 generated tokens, and the same 320 prompts in the same order <span class="cite">[run logs: "Using 332 eligible conversations for 320 requests at prompt length 4096; cycling in dataset order"]</span>. The changes are Slack formatting (#227), thresholds (#229), failure recovery (#223), telemetry parsing (#226), the exit code (#225) and one expected reply text (#218).</li>
  <li><b>Machine.</b> delphi-3bda was not rebooted between the runs (up since 2026-09-15 23:54 UTC). It kept kernel 6.8.0-138-generic and platformd 0.11.0 on both nights <span class="cite">[last -x, uname -r, /var/log/dpkg.log]</span>. platformd went from 0.10.7 to 0.11.0 on 09-21 at 19:58 UTC, before both runs. On 09-23 apt also upgraded libssh2, linux-libc-dev and linux-tools-common. None of them is part of the running server.</li>
  <li><b>The AMX kernels are in the new package.</b> The installed rinzler contains the kill-switch text <code>TRON_AMX_DISABLE</code> once. The old package contains it 0 times <span class="cite">[strings /opt/positron/bin/rinzler on delphi-3bda, 2026-09-23 17:24 UTC]</span>. This morning's page counted 86 AMX tile instructions in the same binary <span class="cite">[CI-AMX-row-20260923.html, section 3]</span>.</li>
</ul>

<h2 id="amxrow">2. The AMX row: how much is left for other merges</h2>
<p>Figure 1 compares three pairs of runs of the same benchmark (llama-3.1-8b tp2, 32 users, prompt 4096 tokens). Our 2026-09-20 test built the old code twice: without and with the AMX kernels. So its gap is the AMX effect alone. The AMD machine cannot run AMX. So its gap is the effect of everything else in the new package.</p>
<div class="legend"><span><i class="key old"></i>package without AMX kernels</span><span><i class="key new"></i>package with AMX kernels</span></div>
<figure>
  <div class="figscroll">{fig_dumbbell()}</div>
  <figcaption><p class="take">Only the Intel rows moved, and the CI moved 1 point more than AMX alone did in our test.</p>
  Figure 1. The vertical orange line marks the CI value with kernels ({H['ci23_tps']:.2f} TPS). It sits +{H['resid_tps']:.2f} TPS to the right of our canon value ({H['canon_tps']:.2f} TPS). Axes do not start at zero. Hover a dot for its value.</figcaption>
</figure>
{table_headline()}
<p class="cite">Sources: CI values are the means of the 320 "Done" samples in the run logs [exec/ci-amx-row-20260923/amx_row.json]. Our values are the means of 3 interleaved passes per build [exec/results/l8b-8u4k-20260920/summary.json]. Prefill rate = 4096 tokens / mean TTFT.</p>
<ul>
  <li>The CI row rose by +{H['ci_gain_tps']:.2f} TPS ({pct(H['ci_gain_pct'])}).</li>
  <li>Our test measured +{H['ab_gain_tps']:.2f} TPS ({pct(H['ab_gain_pct'])}) for AMX alone <span class="cite">[3 pass pairs, paired t = {H['campaign_t']:.0f}]</span>.</li>
  <li>The two values without kernels agree to +{H['base_agree_tps']:.3f} TPS ({pct(H['base_agree_pct'], 2)}). So the harness, the prompt set and platformd 0.11 do not shift this row.</li>
  <li>The CI value with kernels is +{H['resid_tps']:.2f} TPS ({pct(H['resid_pct_of_canon'])}) above ours. This is the most that the 31 other merges, plus any setup difference, can add to this row.</li>
  <li>On the AMD machine the same package change moved this row by {num(H['amd23_tps'] - H['amd22_tps'])} TPS ({pct(H['amd_tps_pct'])}). There, the new package differs from the old one only by the other merges, because its AMX code stays idle. So the other merges did not speed up this row on AMD.</li>
  <li>Prefill: the CI prefill rate rose {pct(H['ci_prefill_pct'])}, and ours rose {pct(H['ab_prefill_pct'])}. The CI TTFT with kernels is {pct(H['ttft_vs_canon_pct'])} slower than ours ({H['ci23_ttft']:,.0f} against {H['canon_ttft']:,.0f} ms). So no other merge added prefill speed to this row either.</li>
</ul>

<h2 id="merges">3. All 32 merges, one verdict each</h2>
<p>I read the diff of every merge and the description of every pull request. The chart sorts the merges into five groups by which rows their code can affect. Each square links to its row in the table.</p>
<figure>
  {fig_units()}
  <figcaption><p class="take">4 of the 31 non-AMX merges can change code that the AMX row runs. The other 27 cannot change it.</p>
  Figure 2. The dark squares are the 4 merges that section 4 examines. Numbers are tron pull request numbers.</figcaption>
</figure>
{table_merges()}
<p class="cite">Merge times are GitHub "mergedAt" values [gh pr view]. Commit SHAs are the first-parent merge commits in tron main [git log --first-parent 3faba6d0..5cf65b92]. Model facts come from config/models.yaml and from the rinzler log on delphi-3bda for the 09-23 run [journalctl -u rinzler@0].</p>

<h2 id="four">4. The four merges that touch the AMX row's code</h2>

<h3>#4534: timed waits no longer update shared counters</h3>
<ul>
  <li>Before #4534, every pass through the timed-wait loop added 1 to a process-wide atomic counter, and every call added 1 to a second one <span class="cite">[src/system/mwaitx.cpp:18-19, 198-200 at 3faba6d0]</span>.</li>
  <li>All waiting threads of an engine write the same two counters. Only diagnostic tests read them.</li>
  <li>The pull request describes the cost: "Those updates add contention during inference."</li>
  <li>Its first diagnostic removed only the counter updates on 4-card gpt-oss-20b. Decode per user rose +11.25 % with 1 user and +6.94 % with 4 users <span class="cite">[PR #4534 description]</span>.</li>
  <li>A later full comparison "no longer shows the earlier large four-card slowdown" <span class="cite">[same]</span>. The machine type of the diagnostic is not stated: Insufficient data.</li>
</ul>
<div class="hyp"><b>Hypothesis: the counters cost more on Intel.</b> Figure 3 shows one 10 µs timed wait, the timeout that <code>wait_for_layer</code> uses between layers <span class="cite">[h/tron/models/common.hpp:949-954 at 3faba6d0]</span>. On AMD, MWAITX sleeps until the watched memory changes or the timeout ends. So the wait makes 1 pass and 2 counter updates (est.). On Intel, each RTM pass ends after at most 2048 TSC cycles, about {H['rtm_budget_ns_est']:.0f} ns at the 2.7 GHz named in the code comment <span class="cite">[src/system/mwaitx.cpp:124]</span>. So the same wait makes {passes} passes and {passes + 1} counter updates (est.), about {((passes + 1) / 2):.1f} times as many. The delphi-3bda engines use the RTM path <span class="cite">[rinzler log 09-23 04:05:34: "INIT: Intel RTM (TSX) supported"]</span>. Measurement that decides it: rebuild the new package with <code>-DTRON_MWAIT_STATS=ON</code> (counters back) and run the 70b tp4 row in alternating passes against the default build.</div>
<div class="legend"><span><i class="key wait"></i>waiting (sleep or RTM pass)</span><span><i class="key upd"></i>one locked add to a counter shared by all waiting threads</span></div>
<figure>
  <div class="figscroll">{lanes_svg}</div>
  <figcaption><p class="take">For the same 10 µs wait, the Intel loop updates the shared counters {passes + 1} times, against 2 times on AMD (est.).</p>
  Figure 3. Durations to scale. Wait lengths come from code constants, not from measurement. The cost of each update was not measured. A write to the watched line ends either wait early. The figure shows a wait that runs to its timeout.</figcaption>
</figure>
<ul>
  <li>Effect on the AMX row: small. On delphi-3bda, the hand-written tp2 rows without the AMX shape moved between −0.3 % and +0.3 % <span class="cite">[table in section 5]</span>.</li>
  <li>One of them, llama-3.2-3b, makes about {steps_ratio:.0f} times as many decode steps per second as the AMX row ({i3b['tps']['new']:.0f} against {H['ci23_tps']:.1f} TPS). It moved only {pct(i3b['tps']['pct'])}, inside its range.</li>
  <li>So at tp2 the effect of #4534 fits inside the +{H['resid_tps']:.2f} TPS residual of the AMX row.</li>
</ul>

<h3>#4205 with #4203: model code compiled in new object files</h3>
<ul>
  <li>Before #4205, the model code was compiled inside the tron library, in numbered group files (<code>models_0.cpp</code> and so on).</li>
  <li>Now each model family (llama, mixtral, qwen, …) is compiled as its own object file with a copied set of compile options <span class="cite">[src/tron/CMakeLists.txt:300-349 at 5cf65b92]</span>. #4203 adds the generator filter that picks one family per file.</li>
  <li>I compared the copied option list with the tron library's own list. They match: the same instruction-set flags (<code>-mavx2</code>, <code>-mfma</code>, the AVX-512 set), <code>-O3</code>, <code>TRON_AMX_DISPATCH</code> and the other definitions, and LTO (link-time optimization) on each object <span class="cite">[same file, lines 268-298 against 314-331 and 349]</span>.</li>
  <li>The pull request states the same: "Model selection, compile flags, LTO, generated-plugin dependencies, and public runtime behavior remain unchanged."</li>
  <li>The compiler can still inline and lay out the hot loops differently in a new object file. The size of that effect was not measured: Insufficient data. It is a candidate for part of the +{H['resid_tps']:.2f} TPS.</li>
</ul>

<h3>#4456: one position record per pin</h3>
<ul>
  <li>For every model, each request step now records the token position of each pin and removes it when the pin is released <span class="cite">[src/tron/scheduler/full.cpp:193 and 201, h/tron/scheduler/full.hpp:463]</span>. A pin is the scheduler's reference that keeps needed KV history.</li>
  <li>Each step also calls one memory-pressure check. It returns at once unless the process is in arena mode and over its memory target <span class="cite">[src/tron/scheduler/full.cpp:80, token_cache.cpp:123-124 and 159-161]</span>.</li>
  <li>The reclamation itself works only on sliding-window layers. llama-3.1-8b has none.</li>
  <li>Expected effect: a few vector operations per step, against a decode step of about {1000 / H['ci23_tps']:.0f} ms (1 / {H['ci23_tps']:.1f} TPS). Negligible (est.).</li>
</ul>

<h3>Two merges that edit files this row compiles, but not code it runs</h3>
<ul>
  <li><b>#4258</b> rewrote the attention join in <code>self_attention.hpp</code>. llama-3.1-8b runs software attention only <span class="cite">[rinzler log 09-23 04:05:52: "HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': default off for this model"]</span>. For software-only layers, the new code merges the worker scratchpads in the same order as before (<code>join_software</code>, then <code>finish_job</code>) <span class="cite">[self_attention.hpp:1193, 1234-1252 at 5cf65b92]</span>. The pull request's own control measured 8-user llama-3.1-8b with FPGA attention off as "equivalent" (under 1 %).</li>
  <li><b>#4455</b> changed KV storage for sliding-window layers. Models without them keep direct K/V indexing <span class="cite">[h/tron/models/kv_cache.hpp:578-580: "Uniform full-history views preselect their base pointer"]</span>. Its new book checks return early when a book has no sliding-window storage.</li>
</ul>

<h2 id="others">5. Other rows that moved, and which merges can explain them</h2>
<p>The other rows of the same two nights show what the other merges did. Figures 4 and 5 place each row's 09-23 value against its same-package range, on both machines. Labels mark only the values that clearly moved.</p>
<div class="legend"><span><i class="key band"></i>same-package range (old package), as % of its mean</span><span><i class="key new"></i>09-23 value (new package)</span></div>
<figure>
  <div class="figscroll">{fig_dots("tps", -6, 20, [-5, 0, 5, 10, 15, 20], True, "f4", "Decode speed on 09-23 against the same-package range", "Dot plot per row and machine of the 09-23 TPS change against the old-package range.")}</div>
  <figcaption><p class="take">Hand-written tp2 rows stayed flat on both machines. The tp4 rows rose on Intel only.</p>
  Figure 4. Decode speed (TPS), 09-23 change against the mean of the old-package nights. The AMX row has only one prior night, marked by a short line.</figcaption>
</figure>
<figure>
  <div class="figscroll">{fig_dots("ttft", -18, 14, [-15, -10, -5, 0, 5, 10], False, "f5", "TTFT on 09-23 against the same-package range", "Dot plot per row and machine of the 09-23 TTFT change against the old-package range.")}</div>
  <figcaption><p class="take">On AMD only the generated models moved, and all of them got faster. On Intel, qwen-3-4b tp4 got faster and mixtral got slower.</p>
  Figure 5. TTFT, 09-23 change against the old-package mean. Lower is faster. The AMX row is left out here: its TTFT fell {pct(H['ci_ttft_pct'])} on Intel and rose {pct(H['amd_ttft_pct'])} on AMD (Figure 1).</figcaption>
</figure>

<h3>Generated models with FPGA attention: faster on both machines</h3>
<ul>
  <li>On AMD, qwen-3-4b tp4 decode rose {pct(aq4['tps']['pct'])} and gpt-oss-120b rose {pct(ago['tps']['pct'])}. Their TTFT fell {pct(aq4['ttft']['pct'])} and {pct(ago['ttft']['pct'])}. qwen-3-4b tp2 TTFT fell {pct(aq2['ttft']['pct'])}.</li>
  <li>No hand-written row clearly moved on AMD.</li>
  <li>FPGA attention is on for exactly these three rows <span class="cite">[rinzler log 09-23: "HW attention enabled for model 'ingested-qwen-3-4b-instruct-2507-tp2'", "…-tp4", "'ingested-gpt-oss-120b-tp4'"]</span>. It is off or not available for every other row.</li>
  <li>#4258 is the merge that changes FPGA attention. Its pull request measured, on a Genoa machine with 4 cards: TTFT −2.07 % for 8-user gpt-oss-120b at a 2K prompt, and larger gains at longer contexts (TTFT −7.57 % and decode +15.9 % at 32K, 1 user).</li>
  <li>So #4258 is the likely cause of these gains. On Intel the tp4 rows gained more, as the next part shows.</li>
</ul>

<h3>tp4 rows: faster on Intel only</h3>
<ul>
  <li>llama-3.3-70b tp4 rose {pct(i70['pct'])} on Intel ({i70['new']:.2f} TPS against {i70['min']:.2f} to {i70['max']:.2f}), and {pct(a70['pct'])} on AMD.</li>
  <li>qwen-3-4b tp4 rose {pct(iq4['tps']['pct'])} on Intel and {pct(aq4['tps']['pct'])} on AMD. gpt-oss-120b tp4 rose {pct(igo['tps']['pct'])} on Intel and {pct(ago['tps']['pct'])} on AMD.</li>
  <li>llama-3.3-70b tp4 is the clearest test. It is hand-written, runs software attention, has 8 query heads per KV head (no AMX shape), and has no sliding window and no experts. Of the 32 merges, only #4534, #4205 and #4456 can change its code.</li>
  <li>A tp4 engine drives 4 cards instead of 2 <span class="cite">[run log: tp4 models provisioned on engines default-0 and default-1, tp2 models on default-0 to default-3]</span>. So one engine process has more waiting threads writing the shared counters. Their number per engine was not read: Insufficient data.</li>
  <li>This makes #4534 the likely cause (see the hypothesis in section 4). The measurement named there decides it.</li>
  <li>For gpt-oss-120b, #4531 also changes which card holds each non-expert tensor tile, because this model places its experts by measured load <span class="cite">[rinzler log 09-23 05:19:19: "Using ExpertsByPlan placement strategy with device_count=4, n_moe_routers=36"]</span>. Its effect on speed is unknown: Insufficient data.</li>
</ul>

<h3>mixtral-8x7b: slower prefill on Intel only</h3>
<ul>
  <li>mixtral TTFT rose {pct(imx['ttft']['pct'])} on Intel ({imx['ttft']['new']:,.0f} ms against {imx['ttft']['min']:,.0f} to {imx['ttft']['max']:,.0f} ms) and {pct(amx_['ttft']['pct'])} on AMD. Its decode did not move on either machine.</li>
  <li>Mixtral has the AMX shape, so on Intel its attention now runs partly on AMX.</li>
  <li>No other merge reaches mixtral alone. It has no expert-load profile, so #4531 does not apply <span class="cite">[rinzler log 09-23 04:57:13: "No expert-load profile at …/Mixtral-8x7B-Instruct-v0.1/expert_load.json; using defaults"]</span>.</li>
  <li>Hypothesis: a side effect of the AMX path at 1024-token prompts. Measurement that decides it: run the mixtral row with the new package, with and without <code>TRON_AMX_DISABLE=1</code>.</li>
</ul>

<h3>gemma-4-31b: moved in opposite directions</h3>
<ul>
  <li>gemma-4-31b decode fell {pct(ig4['tps']['pct'])} on Intel and rose {pct(ag4['tps']['pct'])} on AMD.</li>
  <li>It has no FPGA attention <span class="cite">[rinzler log 09-23 05:22:53: "HW-attention not available for this model. Will use SW-only path."]</span> and no AMX shape (head size 256).</li>
  <li>The merges that can change its code are the sliding-window pair (#4455, #4456), the 8 ingest-compiler refactors and the generic ones. None of them explains opposite signs on the two machines: Insufficient data. More nights of the new package would show whether the change persists.</li>
</ul>

<h3>All rows, both machines</h3>
{table_rows()}
<p class="cite">Old-package nights: delphi-3bda runs 35303980268, 35419103383, 35487126137, 35558398011, 35683952944 (09-18 to 09-22). andoria-b1a3 runs 35417734329, 35485839673, 35556631420, 35682128668 (09-19 to 09-22). New package: runs 35815209295 and 35813240282. Values are the harness's final running averages [scripts/perf.py "Running averages"].</p>

<h2 id="measure">6. Measurements that would settle the open points</h2>
<ul>
  <li><b>#4534 on Intel tp4.</b> Build the new package with <code>-DTRON_MWAIT_STATS=ON</code>. Run the llama-3.3-70b tp4 row in alternating passes against the default build on delphi-3bda. If #4534 is the cause, the counters-on build returns to about {i70['mean']:.2f} TPS.</li>
  <li><b>The +{H['resid_tps']:.2f} TPS residual of the AMX row.</b> Run the new package and our canon package in alternating passes with our harness. Add the counters-on build to separate #4534 from #4205.</li>
  <li><b>mixtral prefill.</b> Run the mixtral row with the new package, with and without <code>TRON_AMX_DISABLE=1</code>.</li>
  <li><b>gpt-oss-120b placement.</b> Load it with <code>TRON_LOG_PLACEMENT=1</code> on both packages and compare the tensor device counts.</li>
</ul>

<h2 id="sources">Sources</h2>
<ul class="src">
  <li>tron repository: <code>git log --first-parent 3faba6d0..5cf65b92</code> and the diff of each merge, and <code>gh pr view</code> for all 32 pull requests (read 2026-09-23).</li>
  <li>tron publish-deb runs 35295875031 (09-18, 3faba6d0) and 35806901506 (09-23, 5cf65b9241): CMake configure output, compiler identification.</li>
  <li>systems_test runs, delphi-3bda: 35303980268, 35419103383, 35487126137, 35558398011, 35683952944, 35815209295. andoria-b1a3: 35417734329, 35485839673, 35556631420, 35682128668, 35813240282. systems_test diff 7327184..5b2250b9.</li>
  <li>delphi-3bda, read-only, 2026-09-23 17:24 UTC: /var/log/dpkg.log, <code>last -x</code>, <code>uname -r</code>, <code>strings /opt/positron/bin/rinzler</code>, <code>journalctl -u rinzler@0</code> for the 09-23 run.</li>
  <li>Our 2026-09-20 test: exec/results/l8b-8u4k-20260920/summary.json. This morning's page: CI-test/status/CI-AMX-row-20260923.html.</li>
  <li>Scripts for this page: exec/ci-merges-20260923/ (parse_perf.sh, calc_numbers.py, gen_page.py, numbers.json).</li>
</ul>
</div>
<div id="tip" hidden></div>
<script>{JS}</script>
"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write(page)
print(OUT, len(page), "bytes")
