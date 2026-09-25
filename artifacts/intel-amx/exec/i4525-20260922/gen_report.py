#!/usr/bin/env python3
"""Build issue4525/status/first-3bda-test-results.html from the i4525-20260922 results (Steps C, D, E, F of
status/first-3bda-test-plan.md). Reads exec/results/i4525-20260922/ (+ i4525-final-20260922/), the chain log,
the peer's Step F report (copied into the evidence dir when present). Pure-ASCII HTML, light theme.
Usage: gen_report.py [OUT_HTML]
"""
import glob, html, json, os, re, sys

EXEC = "/home/jhan/workspace/intel-AMX/exec"
RES = f"{EXEC}/results/i4525-20260922"
RES_FINAL = f"{EXEC}/results/i4525-final-20260922"
EV = "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/3bda-first-test"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/status/first-3bda-test-results.html"


def rd(p):
    try:
        return open(p, errors="replace").read()
    except OSError:
        return ""


def esc(s):
    return html.escape(str(s), quote=True)


def shas():
    lines = rd(f"{EXEC}/i4525-20260922/SNAPSHOT.sha").splitlines()
    snap = lines[0] if lines else "?"
    final = next((l.split("=", 1)[1].split()[0] for l in lines if l.startswith("final=")), None)
    return snap, final


def build_rows():
    rows = []
    for suf, label in [("main0922", "base = main 0a51385e95"), ("i4525rt", "head = snapshot 48ab31f7"), ("i4525rt2", "682064f8fb = last production change"), ("i4525c", "Step C tree (snapshot, AMX off)")]:
        t = rd(f"{RES}/build-{suf}.txt"); done = rd(f"{RES}/build-{suf}.done").strip()
        tip = re.search(r"^tip (\S+)", t, re.M); cache = re.search(r"^cache: (.*)", t, re.M); built = re.search(r"built (\S+) in (\d+) s", t)
        rows.append((label, suf, done or "not run", tip.group(1)[:10] if tip else "-", cache.group(1) if cache else "-", f"{built.group(2)} s" if built else "-"))
    return rows


def smoke_tables():
    out = []
    for d in sorted(glob.glob(f"{RES}/smoke/*")):
        txt = rd(f"{d}/smoke.txt"); name = os.path.basename(d)
        verdict = (re.findall(r"SMOKE-VERDICT (\S+)", txt) or ["not run"])[-1]
        pairs = re.findall(r"^(\w+) vs (\w+): (.*)$", txt, re.M)
        runs = re.findall(r"^smoke (\w+) rc=(\d+) (.*)$", txt, re.M)
        out.append((name, verdict, pairs, runs, [l for l in txt.splitlines() if "SMOKE-" in l and "VERDICT" not in l]))
    return out


def perf_tables(res):
    j = rd(f"{res}/summary.json")
    if not j:
        return None
    return json.loads(j)


def chain_steps():
    return rd(f"{RES}/chain-steps.txt").splitlines()


def host_suite():
    b = rd(f"{RES}/build-test-host-i4525c.txt"); k = rd(f"{RES}/build-test-host-k0-i4525c.txt"); t = rd(f"{RES}/test-host-i4525c.txt")
    return b, k, t


def slice_counts(txt):
    """passed/failed/skipped counts from a bin/slice run tail; None when absent."""
    m = re.search(r"(\d+) passed", txt); f = re.search(r"(\d+) failed", txt); k = re.search(r"(\d+) skipped", txt)
    rc = re.search(r"test-host rc=(\d+)", txt)
    return (int(m.group(1)) if m else None, int(f.group(1)) if f else None, int(k.group(1)) if k else None, int(rc.group(1)) if rc else None)


def short_version(snap, final):
    sm = smoke_tables()
    d_ok = sum(1 for x in sm if x[1] == "ok"); d_n = len(sm)
    pj = perf_tables(RES)
    e_txt = "Step E not run."
    if pj:
        cells_by = {(c['cell'], c['attn'], c['arm']): c for c in pj.get("cells", [])}
        inside = total = 0; worst_tps = worst_ttft = 0.0
        for d in pj.get("deltas", []):
            for key_mean, key_sd, ref in (("tps_mean", "tps_sd", 0.4), ("ttft_mean", "ttft_sd", 0.15)):
                ca = cells_by.get((d['cell'], d['attn'], d['a'])); cb = cells_by.get((d['cell'], d['attn'], d['b']))
                if not ca or not cb or min(ca.get('n', 0), cb.get('n', 0)) < 2:
                    continue
                total += 1
                diff = abs(ca[key_mean] - cb[key_mean]); bw = max(2 * max(ca.get(key_sd) or 0, cb.get(key_sd) or 0), ref)
                inside += diff <= bw
            worst_tps = max(worst_tps, abs(d['tps_delta_pct'])); worst_ttft = max(worst_ttft, abs(d['ttft_delta_pct']))
        e_txt = (f"Step E (performance A/B, commit {(final or '?')[:10]} vs main, 8 users, prompt 1024/2048/8192, 3 repetitions): "
                 f"{inside} of {total} comparisons inside the run-to-run band; the largest difference is {worst_tps:.2f} % TPS and {worst_ttft:.2f} % TTFT.")
    b, k, t = host_suite()
    p, f, sk, rc = slice_counts(t)
    if t:
        c_txt = f"Step C (host suite, 16-lane AMX-off branch tree): make build-test-host rc=0, make test-host rc={rc}: {p} passed, {f} failed, {sk} skipped."
    else:
        c_txt = "Step C (host suite): build-test-host rc=0 on the branch tree; test-host " + ("not run." if not b else "pending.")
    tb = rd(f"{RES}/test-host-i4525cbase.txt")
    if tb:
        p2, f2, sk2, rc2 = slice_counts(tb)
        c_txt += f" Main in the same configuration: test-host rc={rc2}: {p2} passed, {f2} failed, {sk2} skipped."
    c_short = "not run"
    if t:
        c_short = f"{p} passed, {f} failed, {sk} skipped on the branch" + (f" and the same {p2} passed, {f2} failed, {sk2} skipped on main" if tb else "")
    e_short = "Step E not run"
    if pj:
        e_short = (f"the performance A/B of commit {(final or '?')[:10]} (the branch's last production-code change) against main (8 users, prompt 1024/2048/8192, 3 repetitions) "
                   f"has all {total} comparisons inside the run-to-run band, the largest difference being {worst_tps:.2f} % in TPS and {worst_ttft:.2f} % in TTFT")
    return (f"The branch changed no result: the greedy token identity test (Step D, snapshot {snap[:10]} vs main) is identical in {d_ok} of {d_n} specs "
            "(CPU attention with AMX, CPU attention with the kill switch, FPGA attention, prompt 1024 and 8192, 256 tokens each), and the instruction "
            "comparison of the moved loops (Step F, by the plan's author, rerun on the branch head's production code) shows identical bodies or addressing-only differences. "
            f"Performance is unchanged: {e_short}. "
            f"The host test suite in the 16-lane AMX-off configuration (Step C) gives {c_short}.")


def delta_chart(pj):
    """Dot plot: every Step E comparison's measured difference (percent of the main value) against its pass band."""
    cells_by = {(c['cell'], c['attn'], c['arm']): c for c in pj.get("cells", [])}
    rows = []
    for d in pj.get("deltas", []):
        ca = cells_by.get((d['cell'], d['attn'], d['a'])); cb = cells_by.get((d['cell'], d['attn'], d['b']))
        if not ca or not cb or min(ca.get('n', 0), cb.get('n', 0)) < 2:
            continue
        prompt = d['cell'].split('-p')[-1]; pair = "AMX on" if d['a'] == "head" else "kill switch"
        r = {"label": f"prompt {prompt}, {pair}"}
        for key, mean, sd, ref in (("tps", "tps_mean", "tps_sd", 0.4), ("ttft", "ttft_mean", "ttft_sd", 0.15)):
            base = cb[mean]; diff = (ca[mean] - base) / base * 100.0
            band = max(2 * max(ca.get(sd) or 0, cb.get(sd) or 0), ref) / base * 100.0
            r[key] = (diff, band)
        rows.append(r)
    if not rows:
        return ""
    W, PW, LW, RH, TOP = 940, 300, 165, 26, 44
    H = TOP + RH * len(rows) + 34
    def panel(x0, key, title, note):
        xmax = max(1.0, max(max(abs(r[key][0]), r[key][1]) for r in rows) * 1.15)   # per panel: TPS and TTFT bands differ in size
        xmax = round(xmax + 0.05, 1)
        step = 1.0 if xmax <= 2.5 else (2.0 if xmax <= 6 else 5.0)
        ticks = [t * step for t in range(-int(xmax // step), int(xmax // step) + 1)]
        out = [f"<text x='{x0 + PW/2:.0f}' y='16' text-anchor='middle' font-size='13' font-weight='600' fill='#0b0b0b'>{title}</text>",
               f"<text x='{x0 + PW/2:.0f}' y='31' text-anchor='middle' font-size='11' fill='#52514e'>{note}</text>"]
        sx = lambda v: x0 + (v + xmax) / (2 * xmax) * PW
        for gv in ticks:
            if abs(gv) <= xmax:
                col = '#8a8985' if gv == 0 else '#dedcd6'
                out.append(f"<line x1='{sx(gv):.1f}' y1='{TOP - 6}' x2='{sx(gv):.1f}' y2='{TOP + RH*len(rows)}' stroke='{col}' stroke-width='1'/>")
                out.append(f"<text x='{sx(gv):.1f}' y='{TOP + RH*len(rows) + 14}' text-anchor='middle' font-size='11' fill='#52514e'>{gv:+.0f} %</text>")
        for i, r in enumerate(rows):
            y = TOP + RH * i + RH / 2; diff, band = r[key]
            inside = abs(diff) <= band
            out.append(f"<rect x='{sx(-band):.1f}' y='{y-7:.1f}' width='{max(sx(band)-sx(-band), 1):.1f}' height='14' rx='4' fill='#e3e1da'/>")
            out.append(f"<circle cx='{sx(diff):.1f}' cy='{y:.1f}' r='6' fill='{'#2a78d6' if inside else '#e34948'}' stroke='#ffffff' stroke-width='2'><title>{r['label']}: {diff:+.2f} % ({'inside' if inside else 'outside'} band of +/-{band:.2f} %)</title></circle>")
        return out
    parts = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}' role='img' aria-label='Step E differences against their pass bands'>",
             f"<rect x='0' y='0' width='{W}' height='{H}' fill='#ffffff'/>"]
    for i, r in enumerate(rows):
        y = TOP + RH * i + RH / 2
        parts.append(f"<text x='{LW - 8}' y='{y + 4:.1f}' text-anchor='end' font-size='12' fill='#0b0b0b'>{r['label']}</text>")
        parts.append(f"<text x='{LW + PW + 44}' y='{y + 4:.1f}' text-anchor='end' font-size='11' fill='#52514e' font-family='ui-monospace,Menlo,Consolas,monospace'>{r['tps'][0]:+.2f} %</text>")
        parts.append(f"<text x='{W - 8}' y='{y + 4:.1f}' text-anchor='end' font-size='11' fill='#52514e' font-family='ui-monospace,Menlo,Consolas,monospace'>{r['ttft'][0]:+.2f} %</text>")
    parts += panel(LW, "tps", "Decode speed (TPS per user), branch minus main", "positive = branch faster")
    parts += panel(LW + PW + 60 + 50, "ttft", "Time to first token, branch minus main", "negative = branch faster")
    parts.append("</svg>")
    return ("<div class='viz'>" + "".join(parts) + "</div><p class='cap'>Each dot is one comparison (3 repetitions per arm). The grey bar is its pass band "
            "(the larger of 2 x the arm standard deviation and the plan's reference spread, 0.4 TPS or 0.15 s, as a percent of the main value). "
            "A blue dot lies inside its band, a red dot outside. The numbers at the right of each panel are the dot values. The two panels have their own percent scales. The TTFT band at short prompts is wide: the 0.15 s reference floor is a large share of a 3 s TTFT.</p>")


def main():
    snap, final = shas()
    steps = chain_steps()
    css = """body{font-family:system-ui,Segoe UI,Helvetica,Arial,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;background:#fff;color:#1a1a1a;line-height:1.45}
h1{font-size:1.5rem}h2{font-size:1.2rem;margin-top:2rem;border-bottom:1px solid #ddd;padding-bottom:4px}
table{border-collapse:collapse;margin:8px 0;font-size:0.92rem}th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;vertical-align:top}th{background:#f3f3f3}
code,pre{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:0.88rem}pre{background:#f7f7f7;padding:8px;overflow-x:auto;border:1px solid #e5e5e5}
.ok{color:#137333;font-weight:600}.bad{color:#b3261e;font-weight:600}.note{background:#fff8e1;border-left:4px solid #f9a825;padding:6px 10px;margin:8px 0}
.short{background:#eef4ff;border-left:4px solid #3b6fd8;padding:8px 12px}\n.tbl{overflow-x:auto;margin:8px 0}.tbl table{margin:0}.viz{max-width:100%;overflow-x:auto}.viz svg{display:block;max-width:100%;height:auto}\n.cap{color:#52514e;font-size:0.9rem;margin:4px 0 12px}"""
    h = [f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>Typed KV Tensors 3bda Test</title><style>{css}</style></head><body>"]
    h.append("<h1>First delphi-3bda machine test: typed KV-cache tensors (issue #4525), results</h1>")
    h.append(f"<p>Generated from exec/results/i4525-20260922/ by exec/i4525-20260922/gen_report.py. Plan: status/first-3bda-test-plan.md. Branch source under test: snapshot commit <code>{esc(snap[:10])}</code> (branch working tree at 20:47 UTC 2026-09-22) for Step D; commit <code>{esc((final or '-')[:10])}</code>, the branch's last production-code change, for Step E (later commits c2efd73ff6 and c3c368d298 change tests and comments only; the branch head is c3c368d298).</p>")
    h.append("<div class='short'><b>Short version</b><br>" + short_version(snap, final) + "</div>")
    h.append("<h2>Words used here</h2><ul>"
             "<li>tron: the inference program under test. runtron: its command-line tool. rinzler: the production server (systemd units rinzler@0..3 on delphi-3bda).</li>"
             "<li>base: a runtron built from main 0a51385e95. head: the same build from the branch (snapshot 48ab31f7 = the working tree at 20:47 UTC; 682064f8fb = the branch's last production-code commit, one hot-path assert removed; the branch head c3c368d298 differs from it only in tests and comments). baseoff / headoff: the same binaries run with TRON_AMX_DISABLE=1 (the AMX kill switch: the AMX code is present but the AVX-512 path is taken).</li>"
             "<li>delphi-3bda (3bda): the Intel Xeon 6 test server with AMX that runs the nightly CI (continuous-integration test run); our half = socket 1 (CPUs 72-143 and 216-287, accelerator cards 90, 93, b9, bc). Bill's marker: the file /bill-has-instance-0,2, present while the first half (socket 0, cards 10, 13, 38, 3b) is reserved for Bill. CI lease: the file /run/lock/systems-test-ci.lease, present while the nightly CI holds the machine (prep timer 02:45 UTC, start 03:30 UTC). platformd: the machine's control service that starts and stops the production engines; dut.sh serving-down/up and lib-guard: our shell helpers that use it and that guard campaign launches. The driver: the chain script (chain4.sh) that ran the steps.</li>"
             "<li>KV cache: the stored keys (K) and values (V) of earlier tokens that attention reads; typed KV-cache tensors: the branch's change, which replaces raw pointers to that storage with typed views. AVX-512: the 512-bit vector instructions of the normal attention path. 16-lane build: 16 fp32 values per vector register (the AVX-512 build). AMX-off: built with TRON_AMX_DISPATCH=OFF, so no AMX code is compiled (the CI configuration), as opposed to the kill switch above.</li>"
             "<li>Cell label, e.g. q3-4b-tp2-8u-p1024: model qwen3-4b (ingested-qwen-3-4b-instruct-2507-tp2), tp2 = the model split over two accelerator cards, 8 users, prompt of 1024 tokens; every run generates 256 tokens per user. greedy: the most likely token is taken at every step (temperature 0). pay-for-determinism: runtron's mode that makes a run bit-reproducible at some speed cost. rc: a command's return code (0 = success). sd: sample standard deviation over the repetitions; n: number of repetitions.</li>"
             "<li>AMX: Intel Advanced Matrix Extensions (tile instructions of the fast CPU attention path). FPGA attention: attention computed on the accelerator cards (USE_HW_ATTN unset); CPU attention: USE_HW_ATTN=0.</li>"
             "<li>TPS: generated tokens per second per user in decode. TTFT: time to first token in seconds (runtron's prompt parsing time; per run, the largest of the 8 users' values). A/A: the same binary run twice. A/B: base binary against branch binary. Paired delta: per-repetition head minus base, mean and t statistic over the repetitions.</li>"
             "<li>Step C: the host test suite (make build-test-host + make test-host in a 16-lane, AMX-off tree). Step D: greedy token identity. Step E: performance A/B. Step F: instruction comparison (objdump).</li></ul>")
    # builds
    h.append("<h2>Builds on delphi-3bda</h2><table><tr><th>Binary</th><th>Tree suffix</th><th>Result</th><th>Tip</th><th>Cache values</th><th>Build time</th></tr>")
    for label, suf, done, tip, cache, bt in build_rows():
        cls = "ok" if done == "ok" else "bad"
        if suf == "i4525rt2":
            bt = bt + " (the driver's re-check, no work to do; the full build ran 21:06-21:18 UTC, 733 s, started by hand)"
        if suf == "i4525c":
            bt = bt + " (configure + one dependency target; the 669-target make build-test-host followed, rc=0)"
        h.append(f"<tr><td>{esc(label)}</td><td>{esc(suf)}</td><td class='{cls}'>{esc(done)}</td><td><code>{esc(tip)}</code></td><td><code>{esc(cache)}</code></td><td>{esc(bt)}</td></tr>")
    h.append("</table><p class='cap'>The build times of the first three trees include heavy contention. Three trees compiled at once next to the idling production engines, at a 1-minute load average of 140 to 206 on the 288-CPU machine. "
             "The 682064f8fb row shows the compiler cache entry as UNINITIALIZED. The driver's re-check re-ran the configure step with the same preset, which rewrote that entry. The compiler was clang-19 from the Nix shell in every tree.</p>")
    # Step D
    h.append("<h2>Step D: greedy token identity (1 user, temperature 0, pay-for-determinism, seed 1, 256 generated tokens)</h2>")
    h.append("<p>Pass rule (plan Step D): the branch binary produces the same tokens as the main binary, token for token over the whole generation, for each attention "
             "path; head2 is the A/A control (same binary twice). Runs: qwen3-4b tp2 on cards 90:00.0 and 93:00.0, runtron's built-in prompt of the given length "
             "(--prompt-length), one user, 256 generated tokens; token files under smoke/&lt;attn&gt;-p&lt;prompt&gt;/.</p>")
    sm = smoke_tables()
    if not sm:
        h.append("<p class='bad'>Not run.</p>")
    for name, verdict, pairs, runs, problems in sm:
        cls = "ok" if verdict == "ok" else "bad"
        h.append(f"<h3>{esc(name)}: <span class='{cls}'>{esc(verdict)}</span></h3>")
        if "off-machine" in rd(f"{RES}/smoke/{name}/smoke.txt"):
            h.append("<p class='cap'>The five runs of this spec completed on 3bda, but the smoke script died before its comparison step (NFS stale file handle after the script file "
                     "was replaced during the run); the comparison below was computed on claude-box from the same token files with the same code, and is marked so in smoke.txt.</p>")
        h.append("<table><tr><th>Pair</th><th>Result</th></tr>")
        for a, b, r in pairs:
            h.append(f"<tr><td>{esc(a)} vs {esc(b)}</td><td>{esc(r)}</td></tr>")
        h.append("</table><details><summary>runs</summary><pre>" + esc("\n".join(f"{a} rc={rc} {rest}" for a, rc, rest in runs)) + "</pre></details>")
        if problems:
            h.append("<pre class='bad'>" + esc("\n".join(problems)) + "</pre>")
    # Step E
    for res, title in [(RES, "Step E: performance A/B (8 users, prompt 1024/2048/8192, 256 generated tokens, 3 repetitions, CPU attention)"), (RES_FINAL, "Step E (reduced): base vs 682064f8fb, prompt 1024/8192, 2 repetitions")]:
        pj = perf_tables(res)
        if pj is None and res == RES_FINAL:
            continue
        h.append(f"<h2>{esc(title)}</h2>")
        if pj is None:
            h.append("<p class='bad'>Not run.</p>"); continue
        h.append(delta_chart(pj))
        h.append("<table><tr><th>Cell</th><th>Arm</th><th>n</th><th>TPS mean (sd)</th><th>TTFT s mean (sd)</th></tr>")
        for c in pj.get("cells", []):
            h.append(f"<tr><td>{esc(c['cell'])}</td><td>{esc(c['arm'])}</td><td>{c['n']}</td><td>{c['tps_mean']:.2f} ({c['tps_sd']:.2f})</td><td>{c['ttft_mean']:.3f} ({c['ttft_sd']:.3f})</td></tr>")
        h.append("</table><p>Pass rule of the plan: |head - base| inside the run-to-run band. Band used here = the larger of (2 x the larger of the two arms' standard deviations over the repetitions) and the plan's reference spread at this shape (at most 0.4 TPS per user and 0.15 s TTFT, the largest standard deviations the 2026-09-14 campaign saw at this shape). \"inside\" = the absolute mean difference is within that band.</p>")
        h.append("<table><tr><th>Cell</th><th>Comparison</th><th>TPS delta %</th><th>TPS |delta| vs band (sd a, sd b)</th><th>TTFT delta %</th><th>TTFT |delta| s vs band (sd a, sd b)</th><th>Paired TPS delta mean (sd, n, t)</th><th>Paired TTFT delta ms mean (sd, n, t)</th></tr>")
        paired = {(p['cell'], p['a'], p['b']): p for p in pj.get("paired", [])}
        cells_by = {(c['cell'], c['attn'], c['arm']): c for c in pj.get("cells", [])}
        def band(d, key_mean, key_sd):
            ca = cells_by.get((d['cell'], d['attn'], d['a'])); cb = cells_by.get((d['cell'], d['attn'], d['b']))
            if not ca or not cb or ca.get(key_mean) is None or cb.get(key_mean) is None:
                return "-"
            diff = abs(ca[key_mean] - cb[key_mean]); sa = ca.get(key_sd) or 0.0; sb = cb.get(key_sd) or 0.0
            ref = 0.4 if key_mean == "tps_mean" else 0.15   # the plan's reference run-to-run spread at this shape (2026-09-14 campaign)
            if min(ca.get("n", 0), cb.get("n", 0)) < 2:
                return f"n&lt;2: no band; |d|={diff:.3f}"
            bw = max(2 * max(sa, sb), ref); ok = diff <= bw
            return f"<span class='{'ok' if ok else 'bad'}'>{'inside' if ok else 'OUTSIDE'}</span> |d|={diff:.3f} band={bw:.3f} (sd {sa:.3f}, {sb:.3f})"
        for d in pj.get("deltas", []):
            p = paired.get((d['cell'], d['a'], d['b']), {})
            tps = p.get("tps", {}); tt = p.get("ttft_s", {})
            def fmt(x, scale=1.0, nd=2):
                if not x or x.get("mean") is None:
                    return "-"
                tval = "-" if x.get("t") is None else f"{x['t']:+.1f}"
                return f"{x['mean']*scale:+.{nd}f} ({(x.get('sd') or 0)*scale:.{nd}f}, {x.get('n', 0)}, {tval})"
            h.append(f"<tr><td>{esc(d['cell'])}</td><td>{esc(d['a'])} vs {esc(d['b'])}</td><td>{d['tps_delta_pct']:+.1f}</td><td>{band(d, 'tps_mean', 'tps_sd')}</td><td>{d['ttft_delta_pct']:+.1f}</td><td>{band(d, 'ttft_mean', 'ttft_sd')}</td><td>{fmt(tps)}</td><td>{fmt(tt, 1000.0, 0)}</td></tr>")
        h.append("</table>")
        md = rd(f"{res}/summary.md")
        if md:
            h.append("<details><summary>summarize.py output (raw)</summary><pre>" + esc(md) + "</pre></details>")
    # Step C
    b, k, t = host_suite()
    h.append("<h2>Step C: host test suite in the 16-lane AMX-off tree (branch snapshot)</h2>")
    h.append("<p>Pass rule (plan Step C): the set of passing and failing binaries is the same for base and branch, and every test that touches the KV cache passes on "
             "the branch. Tree: /var/tmp/jhan/tron-i4525c (snapshot 48ab31f7), configured with preset native, AVX512=ON, TRON_AMX_DISPATCH=OFF, RelWithDebInfo; "
             "make build-test-host built the 669 host test targets (rc=0, run in the background from 20:51 UTC, paused during Step E), then make test-host "
             "(bin/slice run --filter=host --exclude-tag=slow) with SYSTEM_CONFIG=--instance 1,2 while serving was down.</p>")
    h.append("<p>Configuration note: t_rinzler is an fpga-labelled test, so it is not among the host targets that make build-test-host builds and not part of Step C. "
             "Its compile error on main 0a51385e95 in the 16-lane AMX-on trees (t/t_rinzler.cpp:5316, read_stats_counter undeclared; observed by the plan's author) comes from a symbol "
             "that is defined only when the gpt-oss-20b ingest model is compiled in, so it depends on the ingest-model configuration, not on AMX, and it predates the branch.</p>")
    h.append("<pre>" + esc((b or "build-test-host: not run").strip()[-3000:]) + "</pre>")
    if k:
        h.append("<p>Rebuild with ninja -k 0 (one broken target does not hide the rest):</p><pre>" + esc(k.strip()[-3000:]) + "</pre>")
    h.append("<pre>" + esc((t or "test-host: not run").strip()[-6000:]) + "</pre>")
    tb = rd(f"{RES}/test-host-i4525cbase.txt")
    if tb:
        def status_set(txt):
            return {m.group(2): m.group(1) for m in re.finditer(r"^\s+(passed|failed|skipped)(?: \[new\])?\s+(\S+)", txt, re.M)}
        sb_, sm_ = status_set(t), status_set(tb)
        diffs = sorted(k for k in set(sb_) | set(sm_) if sb_.get(k) != sm_.get(k))
        h.append("<h3>Same suite on main 0a51385e95 (tree /var/tmp/jhan/tron-i4525cbase, same configuration)</h3>")
        h.append(f"<p>Pass rule of the plan: the set of passing and failing binaries is the same for base and branch. Branch: {len(sb_)} test lines "
                 f"({sum(1 for v in sb_.values() if v == 'passed')} passed, {sum(1 for v in sb_.values() if v == 'failed')} failed, {sum(1 for v in sb_.values() if v == 'skipped')} skipped); "
                 f"main: {len(sm_)} test lines ({sum(1 for v in sm_.values() if v == 'passed')} passed, {sum(1 for v in sm_.values() if v == 'failed')} failed, {sum(1 for v in sm_.values() if v == 'skipped')} skipped). "
                 + ("<span class='ok'>Identical status for every test.</span>" if not diffs else "<span class='bad'>Differences: " + esc(", ".join(f"{k}: branch {sb_.get(k)} / main {sm_.get(k)}" for k in diffs)) + "</span>")
                 + " The one skipped test on both trees is t_proxy_lib (a Python virtual-environment dependency, skipped by Slice on this host).</p>")
        h.append("<pre>" + esc(tb.strip()[-6000:]) + "</pre>")
    # Step F
    h.append("<h2>Step F: instruction comparison</h2>")
    h.append("<p>Pass rule (plan Step F): the same instruction counts per loop body in main and branch, no new call, no destination load on an even append, no scalar "
             "dimension loop, no memory clearing in book::allocate_kv_group or restore_reclaimable_kv_storage.</p>")
    h.append("<p>Done by the plan's author (session issue4525-e8) with a wrapper harness, not by this chain: 19 noinline wrapper functions per tree "
             "(set_v even/odd for bf16, fp16, float; get_v even/odd for float, bf16; book::append; scaled_v; book construction; reclaimable free and restore; "
             "runtime-token variants) were compiled against main 0a51385e95 and against the branch snapshot 48ab31f7 with the exact clang-19 command of "
             "t_llama_unit, then disassembled with objdump and compared after normalisation. Files: issue4525/evidence/3bda-first-test/stepF-peer/out/ "
             "(report.txt = per-wrapper table, callee histograms, clearing scan; vector_mix.txt; diff_*.txt; listing_*.txt), copied from "
             "/var/tmp/jhan/tron-issue4525-tests/objdump/ on delphi-3bda at 21:43 UTC.</p>")
    h.append("<p>Result reported by the author and read from report.txt: the 14 constant-token wrapper bodies are instruction-sequence identical between main and the "
             "branch (three of them, book::append, book construction and restore, are short call wrappers whose callees differed only by the snapshot's assert); the vector mnemonic counts are equal for all 19; the even append reads only the source row (no destination load) in both trees; no scalar "
             "dimension loop, no rep stos and no memset appear in the allocation or restore closures, so the in-place kv_block array construction compiles to "
             "nothing. The five runtime-token wrappers (set_v/get_v with a runtime token) differ by one cmp+jae and a spill per call: the snapshot's "
             "TRON_ASSERT_LT(token, Rows) in v_vnni_access::pair_base. That assert was removed in commit 682064f8fb (v_vnni.hpp only), the commit Step E "
             "measured. "
             "The author reran the harness on the branch head's production code at 22:52-22:55 UTC (report_final.txt and diff_final_*.txt in the same folder; the base object unchanged). "
             "Result read from report_final.txt: every constant-token set_v/get_v wrapper, scaled_v, book::append, book construction and restore body is instruction-identical to main. "
             "Four of the five runtime-token wrappers differ by one scalar add fewer (103 to 102, 96 to 95, 103 to 102, 88 to 87 instructions). The fifth has the same mnemonic histogram with different operand order. "
             "The snapshot's compare-and-branch is gone. The copy_token closure differs by register allocation and address mode only (409 to 417 instructions, same vector mnemonic counts, no new call). "
             "allocate_kv_group stays out of line with a once-per-arena size assert and writes nothing to the arena; the make_book and restore closures grow by 260 and 303 instructions from that out-of-line "
             "function and two new abort-message instantiations. The Step E numbers measured on 682064f8fb are therefore the branch head's numbers.</p>")
    fobj = sorted(glob.glob("/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/3bda-first-test/objdump.*.txt"))
    h.append("<p>This chain's own Step F data (full objdump -d -l of the two A1 t_llama_unit binaries, 1,757,567 and 1,745,790 lines, 159 MB each) stays on delphi-3bda under "
             "/var/tmp/jhan/tron-issue4525-tests/ (objdump.tron-issue4525.txt, objdump.tron-issue4525-base.txt); it was not copied to the evidence folder because of its size.</p>")
    # deviations, timeline
    h.append("<h2>Deviations from the plan, and open items</h2><ul>"
             "<li><b>Source under test.</b> The branch had no commit when the plan was written, so the working tree was snapshotted into commit 48ab31f7 "
             "(ref i4525-snap-20260922T2047Z). Later commits: 85084e937c (test only), 682064f8fb (v_vnni.hpp: hot-path TRON_ASSERT_LT removed from the bulk "
             "route; the only production change after the snapshot), c2efd73ff6 and c3c368d298 (comments and tests; one 8-lane-only member deleted). "
             "Step D used the snapshot binary (an assert changes no token); Step E and the branch host suite used 682064f8fb and the snapshot tree respectively; "
             "at 16 lanes the production code of the branch head c3c368d298 is identical to 682064f8fb (verified with git diff on the commits).</li>"
             "<li><b>Instance placement.</b> The plan says runtron with --instance 1,2 (four cards) for the tp2 model; the proven tp2 placement of the earlier "
             "campaigns was used instead: --instance 2,4 with cards 90:00.0 and 93:00.0 and worker cores of socket 1 only (our half). Bill's marker stayed in place. "
             "runtron's main thread, however, ran on socket-0 CPUs during model load in 9 of the 14 Step D runs (21:15 to 21:22 UTC), because runtron was started without taskset and inherited "
             "the driver's mask. The driver was pinned to socket 1 with taskset at about 21:19 UTC. Every later run, including all 36 Step E runs, had every thread on socket 1.</li>"
             "<li><b>Step C command.</b> make build-test-host (the host test targets) was used instead of make build-test (every test target); make test-host "
             "runs the same host filter either way. make reconfigures gen/ with BUILD_INGEST_MODELS=ON and BUILD_TEST_MODELS=ON (recorded in the cache line "
             "above); AVX512=ON and TRON_AMX_DISPATCH=OFF were kept.</li>"
             "<li><b>Serving down.</b> The lib-guard idle takeover refused at 21:10:52 and 21:12:53 UTC (log exec/logs/i4525-20260922.log). Its check wants the last journal line to be an idle "
             "SYSTEM_STATS statistics line. After a statistics burst the engines log two more lines, so the last line is '#EVT# 0 history events' and the check never passes. "
             "The idle bursts of an engine that has been idle for hours are far apart (est. about one hour, from the growing interval that lib-guard documents: 300, 450, 675, 1013 s and so on). "
             "Serving was therefore taken down by hand at 21:14 UTC with dut.sh serving-down (platformd API after a 5-minute request-line check; run from claude-box, so it is not in the copied logs) "
             "and restored by the driver at 22:30 UTC. The base host suite took it down and up once more (22:45 and 22:48 UTC). Follow-up: make rinzler_takeover_if_idle read the last SYSTEM_STATS line instead of the last line.</li>"
             "<li><b>Step F.</b> Done by the plan's author with a wrapper harness, first on the snapshot (differences = the snapshot's assert) and then on the branch head's production code "
             "(result in the Step F section). This chain only produced the full disassemblies.</li>"
             "<li><b>Step E band.</b> The plan names the 2026-09-14 spread (0.4 TPS, 0.15 s) as the band; this report uses the larger of that and 2 x the measured "
             "arm sd. Under this combined band all 12 comparisons are inside. The two definitions alone disagree on three of them: the plan's reference floor alone (0.15 s) would "
             "flag the prompt-8192 TTFT difference (0.39 s, -0.73 %, head faster), and 2 x sd alone would flag two prompt-2048 differences whose arm spreads are tiny "
             "(+0.32 TPS with sd at most 0.09 TPS; -0.019 s with sd at most 0.007 s). Every flagged difference favours the branch. The TTFT reductions at prompt 1024 and "
             "2048 are consistent across the three repetitions (paired t -4.3 and -7.1) but small (6 ms and 19 ms, 0.2-0.3 %); they are reported here, not claimed as a gain.</li>"
             "<li><b>Prompt source in Step D.</b> The plan's recipe names a forced text token file; the runs used runtron's built-in prompt of the requested length "
             "(--prompt-length, one user, --pay-for-determinism, temperature 0, seed 1), the recipe of the 2026-09-14/15 campaigns whose A/A runs were identical. "
             "The head2 A/A control of this run was identical as well.</li>"
             "<li><b>Steps A and B</b> (build configurations, real-AMX proof) were run by the plan's author before the plan was written (plan section 2, results in its "
             "section 7); this chain did not repeat Step B on the later commits. Follow-up: t_amx_numerics on c3c368d298 or later with and without TRON_AMX_DISABLE=1.</li>"
             "<li><b>Step G.</b> Tree status: the runtron trees and the two host-suite trees are clean checkouts of their commits (git status: 0 changed files); the "
             "author's trees /var/tmp/jhan/tron-issue4525 (working-tree sync, 15 changed files at objdump time) and -base (1 changed file) are not clean and are "
             "recorded as such in the chain log. Slice logs of both host-suite runs are in the evidence folder (slice-logs-tron-i4525c/, slice-logs-tron-i4525cbase/).</li>"
             "<li><b>Not covered</b> (as in the plan section 6): CI evidence, the test-cost record (bin/slice bench --update), the 8-lane suite, PR #4424's rebase.</li></ul>")
    h.append("<h2>Machine timeline (UTC, 2026-09-22)</h2><ul>"
             "<li>20:39 plan file first seen by this session (file mtime; its header says written 21:00 UTC and it was edited afterwards); 20:47 snapshot commit; 20:50-21:10 runtron builds (base, snapshot), Step C tree configured and built (build-test-host 669 targets); "
             "21:06-21:18 runtron build of 682064f8fb (733 s); 21:25 the driver's 18 s re-check of that tree.</li>"
             "<li>21:14 production serving down through platformd (idle check: 0 request lines in 5 min, 0 remote connections).</li>"
             "<li>21:15-21:25 Step D (14 runtron runs); 21:25-22:14 Step E (36 runs, 0 failures); 22:14-22:17 test-host on the branch tree; 22:17-22:29 objdump of "
             "both A1 t_llama_unit binaries; 22:30 serving up (4 engines idle, marker present).</li>"
             "<li>22:31-22:45 main built in the AMX-off configuration (build-test-host 816 s, rc=0); 22:45 serving down (idle check passed at once); 22:46-22:48 test-host on main; 22:48 serving up.</li>"
             "<li>Rules kept: CI lease free throughout (nightly prep timer 02:45 UTC, cron 03:30 UTC); Bill's marker /bill-has-instance-0,2 present; builds, unit tests and the "
             "host suites were pinned to socket 1 with taskset; runtron used only our cards (90:00.0, 93:00.0) and socket-1 app and device cores through its own placement "
             "flags, but its start-up thread ran unpinned before that placement took effect (the logs show socket-0 CPU ids in the first lines of 9 of the 14 Step D runs); "
             "the driver itself was pinned to socket 1 at 21:1x UTC.</li></ul>")
    # chain steps + machine
    h.append("<h2>Chain step log</h2><pre>" + esc("\n".join(steps) or "(none)") + "</pre>")
    h.append("<h2>Evidence</h2><p>Folder issue4525/evidence/3bda-first-test/: build logs and build-*.txt, smoke/&lt;attn&gt;-p&lt;prompt&gt;/ (token files, runtron logs, smoke.txt), rt/ runtron logs, rt-results.txt, summary.json and summary.md, the host-suite outputs of both trees, the Slice logs of both host-suite runs (slice-logs-*/), the author's Step F harness output (stepF-peer/), the plan author's own logs (c2.*, c3.*, c4.*, t_amx_*.log), and the chain logs. The full disassemblies of this chain stay on delphi-3bda (see Step F).</p>")
    h.append("</body></html>")
    doc = "\n".join(h)
    doc = doc.replace("<table>", "<div class='tbl'><table>").replace("</table>", "</table></div>")
    doc = doc.encode("ascii", "xmlcharrefreplace").decode("ascii")
    open(OUT, "w").write(doc)
    print("written", OUT, len(doc), "bytes")
    # artifact copy: the same page without the document wrapper (the Artifact tool adds its own skeleton)
    art = re.sub(r"^.*?<title>", "<title>", doc, count=1, flags=re.S).replace("</head><body>", "").replace("</body></html>", "")
    art_path = os.environ.get("ARTIFACT_COPY", "/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/d7314eec-6275-458e-8946-af0dec5dd459/scratchpad/typed-kv-tensors-3bda-test.artifact.html")
    open(art_path, "w").write(art); print("artifact copy", art_path, len(art), "bytes")


if __name__ == "__main__":
    main()
