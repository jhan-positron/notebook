#!/usr/bin/env python3
"""HTML report for the five-category Perfetto campaign.

Beyond the per-draw outcome table it ranks the successful draws by generation
throughput and weighs the trace-level timing deltas of the fastest and slowest
draw against the throughput delta between them. v3 also summarises each draw's
turbostat capture (results/<draw>/power.tsv) into core-frequency and
package-power statistics and compares the fastest and slowest draws on both.
"""
import csv
import html
import math
import statistics
import sys
from pathlib import Path

CATEGORIES = ("scheduler", "model", "matmul", "driver", "gen")
POWER_FIELDS = ("Avg_MHz", "Busy%", "Bzy_MHz", "PkgWatt", "RAMWatt")


def read_power_tsv(path):
    """Parse turbostat -o output into means over its per-interval summary rows.

    turbostat repeats the header before each interval and marks the interval's
    system-summary row with '-' in the topology columns; on that row the
    frequency columns are all-CPU means and the watt columns whole-system sums.
    Per-CPU rows are skipped — package-scope counters appear only on selected
    rows there, so the summary rows are the only uniformly parseable ones.
    """
    if not path.exists():
        return None
    samples = []
    idx = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            fields = line.split()
        if len(fields) < 2:
            continue
        if "Avg_MHz" in fields:
            idx = {name: fields.index(name) for name in ("Package", *POWER_FIELDS) if name in fields}
            continue
        if not idx or fields[idx.get("Package", 0)] != "-":
            continue
        row = {}
        for name in POWER_FIELDS:
            try:
                row[name] = float(fields[idx[name]])
            except (KeyError, IndexError, ValueError):
                row[name] = None
        if row.get("Bzy_MHz") is not None or row.get("PkgWatt") is not None:
            samples.append(row)
    if not samples:
        return None
    out = {"samples": len(samples)}
    for name in POWER_FIELDS:
        vals = [s[name] for s in samples if s[name] is not None]
        out[name] = statistics.fmean(vals) if vals else None
    return out


def fmt1(value):
    return f"{value:.1f}" if value is not None else "—"


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def esc(value):
    return html.escape(str(value), quote=True)


def read_metric_csv(path):
    """Parse a trace_processor query result into {metric: {samples, mean_ns, total_ns}}."""
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            key = (row.get("metric") or "").strip()
            if not key:
                continue

            def num(field):
                try:
                    return int(float(row.get(field) or 0))
                except (ValueError, TypeError):
                    return 0

            out[key] = {"samples": num("samples"), "mean_ns": num("mean_ns"), "total_ns": num("total_ns")}
    return out


def pct_delta(fast, slow):
    """Percent change going from the slow draw to the fast draw."""
    if not slow:
        return None
    return (fast - slow) / slow * 100.0


def fmt_ms(ns):
    return f"{ns / 1e6:.3f}" if ns else "—"


def fmt_pct(value):
    return f"{value:+.2f}%" if value is not None else "—"


def delta_table(fast_rows, slow_rows, label):
    keys = sorted(set(fast_rows) | set(slow_rows))
    if not keys:
        return f"<p class='muted'>No {esc(label)} data was produced.</p>"
    body = []
    for key in keys:
        f = fast_rows.get(key, {"samples": 0, "mean_ns": 0, "total_ns": 0})
        s = slow_rows.get(key, {"samples": 0, "mean_ns": 0, "total_ns": 0})
        body.append(
            "<tr>"
            f"<td>{esc(key)}</td>"
            f"<td>{f['samples']}</td><td>{s['samples']}</td>"
            f"<td>{fmt_ms(f['mean_ns'])}</td><td>{fmt_ms(s['mean_ns'])}</td>"
            f"<td>{esc(fmt_pct(pct_delta(f['mean_ns'], s['mean_ns'])))}</td>"
            f"<td>{fmt_ms(f['total_ns'])}</td><td>{fmt_ms(s['total_ns'])}</td>"
            f"<td>{esc(fmt_pct(pct_delta(f['total_ns'], s['total_ns'])))}</td>"
            "</tr>"
        )
    return (
        "<div class='scroll'><table><thead><tr>"
        "<th>Metric</th><th>Fast n</th><th>Slow n</th>"
        "<th>Fast mean (ms)</th><th>Slow mean (ms)</th><th>Δ mean</th>"
        "<th>Fast total (ms)</th><th>Slow total (ms)</th><th>Δ total</th>"
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
    )


def main():
    root = Path(sys.argv[1]).resolve()
    identity = read_env(root / "identity.env")
    with (root / "results.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    measured = []
    for row in rows:
        if row.get("status") != "ok":
            continue
        try:
            measured.append((row["draw"], float(row["generate_tok_s"])))
        except (ValueError, TypeError):
            pass
    mean = statistics.fmean(v for _, v in measured) if measured else math.nan
    stdev = statistics.pstdev([v for _, v in measured]) if len(measured) > 1 else 0.0
    slow = min(measured, key=lambda item: item[1]) if measured else ("n/a", math.nan)
    fast = max(measured, key=lambda item: item[1]) if measured else ("n/a", math.nan)
    lo = min((v for _, v in measured), default=0.0)
    hi = max((v for _, v in measured), default=1.0)
    span = hi - lo or 1.0
    failures = [r for r in rows if r.get("status") != "ok"]
    restored = (root / "RESTORED").exists()
    restore_failed = (root / "RESTORE_FAILED").exists()
    restoration_status = "Verified" if restored else "Failed" if restore_failed else "Pending"
    restoration_elapsed = None
    try:
        restoration_elapsed = int((root / "restored-epoch.txt").read_text()) - int((root / "mutation-start-epoch.txt").read_text())
    except (FileNotFoundError, ValueError):
        pass

    command = "Not captured"
    environment = "Not captured"
    for candidate in [*(root / "results" / f"draw_{i:02d}" for i in range(1, 21)), root / "smoke"]:
        cmd = candidate / "runtron-command.txt"
        env = candidate / "runtron-environment.txt"
        if cmd.exists():
            command = cmd.read_text(encoding="utf-8", errors="replace").strip()
            environment = env.read_text(encoding="utf-8", errors="replace").strip() if env.exists() else environment
            break

    observations = []
    category_notes = []
    health_notes = []
    for candidate in [root / "smoke", *(root / "results" / f"draw_{i:02d}" for i in range(1, 21))]:
        soft = candidate / "soft-observations.txt"
        cats = candidate / "category-observations.txt"
        if soft.exists():
            for item in soft.read_text(encoding="utf-8").splitlines():
                if item:
                    observations.append((candidate.name, item))
        if cats.exists():
            for item in cats.read_text(encoding="utf-8").splitlines():
                if item:
                    category_notes.append((candidate.name, item))
        health = candidate / "trace-processor.log"
        if health.exists():
            health_text = health.read_text(encoding="utf-8", errors="replace")
            if "Trace health issues:" in health_text:
                labels = [l for l in ("Data losses", "Tokenizer errors", "Packet sequence errors") if l in health_text]
                detail = ", ".join(labels) if labels else "trace processor reported a health issue"
                if "config_write_into_file_discard" in health_text:
                    detail += "; write_into_file + DISCARD warning"
                health_notes.append((candidate.name, detail))
        elif (candidate / "trace.pftrace").exists():
            health_notes.append((candidate.name, "trace-processor health log missing"))

    # ---- fast vs slow trace comparison -------------------------------------
    analysis = root / "analysis"
    sel = read_env(analysis / "selection.env") if (analysis / "selection.env").exists() else {}
    fast_draw = sel.get("fast", fast[0])
    slow_draw = sel.get("slow", slow[0])
    throughput_delta = pct_delta(fast[1], slow[1]) if measured else None

    phase_f = read_metric_csv(analysis / "fast-phase.csv")
    phase_s = read_metric_csv(analysis / "slow-phase.csv")
    cat_f = read_metric_csv(analysis / "fast-category.csv")
    cat_s = read_metric_csv(analysis / "slow-category.csv")
    top_f = read_metric_csv(analysis / "fast-topslices.csv")
    top_s = read_metric_csv(analysis / "slow-topslices.csv")

    gen_f = phase_f.get("generation_forward", {}).get("mean_ns", 0)
    gen_s = phase_s.get("generation_forward", {}).get("mean_ns", 0)
    gen_delta = pct_delta(gen_f, gen_s)

    if throughput_delta is None or gen_delta is None or not gen_f or not gen_s:
        verdict = (
            "<p>The per-token timing comparison could not be completed — one of the two traces "
            "did not yield generation-phase <code>forward</code> slices.</p>"
        )
    else:
        # Throughput is the reciprocal of per-token latency, so a faster draw should
        # show a mean generation-forward duration shorter by roughly the same
        # proportion that its throughput is higher.
        implied = -throughput_delta / (1 + throughput_delta / 100.0)
        residual = gen_delta - implied
        agreement = (
            "consistent with" if abs(residual) < 1.0
            else "broadly consistent with" if abs(residual) < 3.0
            else "not fully explained by"
        )
        verdict = (
            f"<p>Draw <code>{esc(fast_draw)}</code> generated <strong>{fmt_pct(throughput_delta)}</strong> more "
            f"tokens per second than <code>{esc(slow_draw)}</code>. Its mean generation-phase "
            f"<code>forward</code> slice was <strong>{fmt_ms(gen_f)} ms</strong> against "
            f"<strong>{fmt_ms(gen_s)} ms</strong>, a change of <strong>{fmt_pct(gen_delta)}</strong>.</p>"
            f"<p>A throughput gain of {fmt_pct(throughput_delta)} implies a per-token latency change of "
            f"{fmt_pct(implied)} if the whole difference sat in the forward pass. The observed "
            f"{fmt_pct(gen_delta)} leaves a residual of <strong>{residual:+.2f} percentage points</strong>, "
            f"so the measured throughput delta is {agreement} the traced per-token timing.</p>"
        )

    dots = []
    for index, (name, value) in enumerate(measured):
        x = 80 + 820 * (value - lo) / span
        y = 45 + index * 28
        color = "#d55e00" if name == slow[0] else "#0072b2" if name == fast[0] else "#6b7280"
        dots.append(
            f'<text x="65" y="{y+4}" text-anchor="end">{esc(name)}</text>'
            f'<line x1="80" y1="{y}" x2="900" y2="{y}" stroke="#e5e7eb"/>'
            f'<circle cx="{x:.1f}" cy="{y}" r="6" fill="{color}"/>'
            f'<text x="{x+11:.1f}" y="{y+4}" font-weight="700">{value:.3f}</text>'
        )
    svg_height = max(100, 75 + len(measured) * 28)

    ranked = sorted(measured, key=lambda item: item[1], reverse=True)

    # ---- turbostat core frequency and package power -------------------------
    power = {name: read_power_tsv(root / "results" / name / "power.tsv") for name, _ in measured}
    power_rows = []
    for name, value in ranked:
        p = power.get(name)
        if p:
            power_rows.append(
                f"<tr><td><code>{esc(name)}</code></td><td>{value:.3f}</td><td>{p['samples']}</td>"
                f"<td>{fmt1(p['Bzy_MHz'])}</td><td>{fmt1(p['Avg_MHz'])}</td><td>{fmt1(p['Busy%'])}</td>"
                f"<td>{fmt1(p['PkgWatt'])}</td><td>{fmt1(p['RAMWatt'])}</td></tr>"
            )
        else:
            power_rows.append(
                f"<tr><td><code>{esc(name)}</code></td><td>{value:.3f}</td>"
                "<td colspan='6' class='muted'>no power.tsv captured</td></tr>"
            )
    power_f = power.get(fast_draw)
    power_s = power.get(slow_draw)
    if power_f and power_s:
        freq_delta = pct_delta(power_f["Bzy_MHz"], power_s["Bzy_MHz"]) if power_f["Bzy_MHz"] and power_s["Bzy_MHz"] else None
        watt_delta = pct_delta(power_f["PkgWatt"], power_s["PkgWatt"]) if power_f["PkgWatt"] and power_s["PkgWatt"] else None
        power_verdict = (
            f"<p>Fast draw <code>{esc(fast_draw)}</code> ran its busy cores at <strong>{fmt1(power_f['Bzy_MHz'])} MHz</strong> "
            f"drawing <strong>{fmt1(power_f['PkgWatt'])} W</strong> package power, against "
            f"<strong>{fmt1(power_s['Bzy_MHz'])} MHz</strong> and <strong>{fmt1(power_s['PkgWatt'])} W</strong> for slow draw "
            f"<code>{esc(slow_draw)}</code> — a busy-frequency delta of <strong>{fmt_pct(freq_delta)}</strong> and a "
            f"package-power delta of <strong>{fmt_pct(watt_delta)}</strong> against the throughput delta of "
            f"<strong>{fmt_pct(throughput_delta)}</strong>.</p>"
        )
    elif any(power.values()):
        power_verdict = ("<p class='muted'>Power capture is missing for the fastest or slowest draw, "
                         "so no fast-versus-slow power comparison is possible.</p>")
    else:
        power_verdict = ("<p class='muted'>No turbostat capture (power.tsv) was found for any draw — "
                         "this campaign predates the power capture, or turbostat produced no output.</p>")

    rank_rows = "".join(
        f"<tr><td>{i}</td><td><code>{esc(name)}</code></td><td>{value:.3f}</td>"
        f"<td>{esc(fmt_pct(pct_delta(value, slow[1])))}</td></tr>"
        for i, (name, value) in enumerate(ranked, start=1)
    ) or "<tr><td colspan='4'>No successful draws.</td></tr>"

    table_rows = []
    for row in rows:
        draw_dir = root / "results" / row["draw"]
        soft = (draw_dir / "soft-observations.txt").read_text(encoding="utf-8").strip() if (draw_dir / "soft-observations.txt").exists() else ""
        draw_health = "; ".join(item for draw, item in health_notes if draw == row["draw"]) or "none reported"
        artifact_root = str(Path(row["perfetto_capture"]).parent) if row["perfetto_capture"] else str(draw_dir)
        table_rows.append(
            "<tr>"
            f"<td>{esc(row['draw'])}</td><td>{esc(row['status'])}</td>"
            f"<td>{esc(row['generate_tok_s'] or '—')}</td><td>{esc(soft or 'none')}</td><td>{esc(draw_health)}</td>"
            f"<td class='path'>{esc(row['archived_placement_log'])}</td>"
            f"<td class='path'>{esc(row['source_placement_log'])}</td>"
            f"<td class='path'>{esc(row['perfetto_capture'])}</td>"
            f"<td class='path'><details><summary>{esc(artifact_root)}</summary>"
            f"<div>{esc(artifact_root + '/metrics.json')}</div><div>{esc(artifact_root + '/perfetto.cfg')}</div>"
            f"<div>{esc(artifact_root + '/perfetto.log')}</div><div>{esc(artifact_root + '/perfetto.rc')}</div>"
            f"<div>{esc(artifact_root + '/trace-validation.csv')}</div>"
            f"<div>{esc(artifact_root + '/trace-processor.log')}</div><div>{esc(artifact_root + '/runtron-command.txt')}</div>"
            f"<div>{esc(artifact_root + '/run-benchmark.log')}</div>"
            f"<div>{esc(artifact_root + '/capture-timestamp.txt')}</div>"
            f"<div>{esc(artifact_root + '/runtron-environment.txt')}</div></details></td>"
            f"<td>{esc(row['reason'] or '')}</td></tr>"
        )

    soft_rows = "".join(f"<li><code>{esc(draw)}</code>: {esc(item)}</li>" for draw, item in observations) or "<li>None recorded.</li>"
    category_rows = "".join(f"<li><code>{esc(draw)}</code>: {esc(item)}</li>" for draw, item in category_notes) or "<li>All requested categories observed.</li>"
    health_rows = "".join(f"<li><code>{esc(draw)}</code>: {esc(item)}</li>" for draw, item in health_notes) or "<li>No trace-processor health issues were reported.</li>"

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Perfetto campaign — {esc(identity.get('MODEL', 'unknown'))}</title>
<style>
:root{{--paper:#f7f8fa;--card:#fff;--ink:#17202a;--muted:#5f6b76;--line:#d9dee5;--blue:#0072b2;--orange:#d55e00}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}}
main{{max-width:1180px;margin:auto;padding:34px 24px 60px}} header,section{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:16px}}
h1{{margin:0 0 8px;font-size:30px}} h2{{margin-top:0}} .muted{{color:var(--muted)}} .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.kpi{{padding:15px;border:1px solid var(--line);border-radius:9px}} .kpi b{{display:block;font-size:24px}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f3f5;padding:14px;border-radius:8px}}
table{{border-collapse:collapse;min-width:760px;width:100%}} th,td{{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}} th{{background:#eef1f5}}
.scroll{{overflow:auto}} .path{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;overflow-wrap:anywhere}} svg text{{font:12px system-ui,Segoe UI,sans-serif;fill:var(--ink)}}
@media(max-width:760px){{.kpis{{grid-template-columns:1fr 1fr}}main{{padding:20px 12px}}}}
</style></head><body><main>
<header><h1>Perfetto campaign</h1><p><strong>{esc(identity.get('MODEL','unknown'))}</strong> · {esc(identity.get('ROUNDS','20'))} scheduled draws · 25-second trace window</p>
<p class="muted">Categories: {esc(identity.get('PERFETTO_CATEGORIES',''))}</p></header>

<section><h2>Exact resolved runtron command</h2><pre>{esc(command)}</pre><h3>Inherited environment</h3><pre>{esc(environment)}</pre>
<p class="muted">Seed literal: {esc(identity.get('SEED_LITERAL',''))}; effective seed after float parsing: {esc(identity.get('SEED_EFFECTIVE',''))}. Greedy sampling: threshold_p={esc(identity.get('THRESHOLD_P',''))}.</p></section>

<section class="kpis">
<div class="kpi"><span>Scheduled</span><b>{len(rows)}</b></div><div class="kpi"><span>Successful</span><b>{len(measured)}</b></div>
<div class="kpi"><span>Mean tok/s</span><b>{mean:.3f}</b></div><div class="kpi"><span>Spread tok/s</span><b>{lo:.3f}–{hi:.3f}</b></div>
</section>

<section><h2>Fast versus slow: timing deltas against the throughput delta</h2>
{verdict}
<h3>Generation and parse phases</h3>{delta_table(phase_f, phase_s, 'phase')}
<h3>Per-category slice time</h3>{delta_table(cat_f, cat_s, 'category')}
<h3>Heaviest slice names</h3>{delta_table(top_f, top_s, 'slice')}
<p class="muted">Fast draw <code>{esc(fast_draw)}</code>, slow draw <code>{esc(slow_draw)}</code>. The slice table measures one shared set of names — the union of each trace's twenty heaviest — in both traces, so a name never reads as absent merely because it fell outside one trace's top twenty. Totals cover the 25-second capture window, so total-time deltas also move with how much of the run each window caught; the mean columns are the like-for-like comparison.</p></section>

<section><h2>Successful draws ranked by generation throughput</h2>
<div class="scroll"><table><thead><tr><th>Rank</th><th>Draw</th><th>tok/s</th><th>vs slowest</th></tr></thead><tbody>{rank_rows}</tbody></table></div>
<p><strong>Fastest:</strong> {esc(fast[0])} — {fast[1]:.3f} tok/s. <strong>Slowest:</strong> {esc(slow[0])} — {slow[1]:.3f} tok/s. Population standard deviation {stdev:.3f} tok/s.</p></section>

<section><h2>Throughput by draw</h2><svg viewBox="0 0 980 {svg_height}" role="img" aria-label="Generation throughput by draw">{''.join(dots)}</svg></section>

<section><h2>Core frequency and package power (turbostat)</h2>
{power_verdict}
<div class="scroll"><table><thead><tr><th>Draw</th><th>tok/s</th><th>Samples</th><th>Bzy_MHz</th><th>Avg_MHz</th><th>Busy%</th><th>PkgWatt</th><th>RAMWatt</th></tr></thead><tbody>{''.join(power_rows)}</tbody></table></div>
<p class="muted">Draws are listed fastest first. Values are means of turbostat's per-interval system-summary rows ({esc(identity.get('TURBOSTAT_INTERVAL_S','5'))} s intervals), captured from the end of model load until the benchmark exited. The frequency columns average all CPUs — idle rest-set cores pull Avg_MHz down, while Bzy_MHz is the clock while unhalted. PkgWatt sums every package; RAMWatt is DRAM power where the platform reports it.</p></section>

<section><h2>Production restoration</h2><p><strong>{esc(restoration_status)}</strong>{f' — {restoration_elapsed} s from mutation start through verified restoration' if restoration_elapsed is not None else ''}.</p>
<p class="muted">The CI runner is intentionally left stopped, matching the prior campaign's behaviour.</p></section>

<section><h2>Trace observations</h2><p>Soft content observations do not change campaign status.</p><ul>{soft_rows}</ul>
<h3>Category observations</h3><ul>{category_rows}</ul><h3>Trace-processor health</h3><ul>{health_rows}</ul></section>

<section><h2>Scheduled outcomes and artifact paths</h2>
<p>{len(rows)} scheduled, {len(measured)} successful, {len(failures)} failed.</p>
<div class="scroll"><table><thead><tr><th>Draw</th><th>Status</th><th>tok/s</th><th>Soft observations</th><th>Trace health</th><th>Archived placement log</th><th>Source placement log</th><th>Perfetto capture</th><th>Other artifacts</th><th>Reason</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div></section>

<section><h2>Capture identity</h2><pre>{esc((root/'identity.env').read_text(encoding='utf-8'))}</pre>
<p class="muted">Buffer fill policy: {esc(identity.get('TRACE_FILL_POLICY','unknown'))}. Trace-processor health output is archived per draw.</p></section>
</main></body></html>"""
    (root / "report.html").write_text(doc, encoding="utf-8", newline="\n")
    print(root / "report.html")


if __name__ == "__main__":
    main()
