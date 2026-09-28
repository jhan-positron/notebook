#!/usr/bin/env python3
"""Build the follow-up report from results.json and primary-source metadata.

Run with: uv run --with matplotlib==3.11.2 --with markdown==3.11 python report.py
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "CI-test" / "status"
STEM = "CI-AMX-persistence-20260928"
RUNS = json.loads((HERE / "results.json").read_text())
META = json.loads((HERE / "metadata.json").read_text())
INTEL = [r for r in RUNS if r["machine"] == "intel"]
AMD = [r for r in RUNS if r["machine"] == "amd"]
L8B = ("llama-3.1-8b-instruct-good-tp2", 32)
OTHERS = [
    ("llama-3.3-70b-instruct-good-tp4", 4, "Llama 3.3 70B TP4"),
    ("ingested-qwen-3-4b-instruct-2507-tp4", 8, "Qwen 3 4B TP4"),
    ("ingested-gpt-oss-120b-tp4", 8, "GPT-OSS 120B TP4"),
]


def row(run, model, users):
    found = [r for r in run["rows"] if r["config"]["model"] == model and r["config"]["n_users"] == users]
    assert len(found) == 1 and found[0]["usable"]
    return found[0]


def percent(value, base):
    return 100 * (value / base - 1)


def timestamp(value):
    return datetime.fromisoformat(value[:19] + "+00:00")


def md_table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(map(str, values)) + " |" for values in rows),
    ])


def plot():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    colors = ["#235b9b", "#8856a7", "#00877b", "#bb651e"]
    for (model, users, label), color in zip([(L8B[0], L8B[1], "Llama 3.1 8B AMX row"), *OTHERS], colors):
        values = [row(run, model, users)["tps_mean"] for run in INTEL]
        gains = [percent(value, values[0]) for value in values]
        axes[0].plot(range(7), gains, marker="o", markersize=4, label=label, color=color, linewidth=2)
    for runs, label, color in [(INTEL, "Intel: Llama 8B", colors[0]), (AMD, "AMD: Llama 8B", "#707780")]:
        values = [row(run, *L8B)["prefill_tps"] for run in runs]
        axes[1].plot(range(7), [percent(value, values[0]) for value in values], marker="o", markersize=4, label=label, color=color, linewidth=2)
    axes[0].set_title("Decode speed on Intel", loc="left", fontweight="bold", pad=13)
    axes[1].set_title("TTFT-derived prefill: AMX benchmark row", loc="left", fontweight="bold", pad=13)
    for ax in axes:
        ax.axvspan(1.5, 6.25, color="#758497", alpha=0.07)
        ax.axvline(1.5, color="#9299a0", linestyle=":", linewidth=1.2)
        ax.axhline(0, color="#9299a0", linewidth=0.8)
        ax.set_xticks(range(7), ["Sep 22", "23", "24", "25", "26", "27", "28"])
        ax.set_xlim(-0.18, 6.2)
        ax.set_ylabel("Change from Sep 22 (%)")
        ax.set_xlabel("2026 CI run date (UTC)")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.18)
        ax.legend(frameon=False, fontsize=8.7, loc="upper center",
                  bbox_to_anchor=(0.5, -0.20), ncol=2)
    axes[0].set_ylim(-1, 21)
    axes[1].set_ylim(-5, 76)
    axes[0].text(1.65, 19.3, "Sep 24+: additional runtime changes", color="#5b646c", fontsize=9)
    axes[1].text(1.65, 69, "Sep 24+: additional runtime changes", color="#5b646c", fontsize=9)
    fig.suptitle("The measured gains persisted through six AMX-enabled nightly runs", x=0.06, ha="left", fontweight="bold", fontsize=14)
    fig.tight_layout(rect=(0.015, 0.015, 0.995, 0.96))
    fig.savefig(OUT / f"{STEM}.svg", bbox_inches="tight")
    svg_path = OUT / f"{STEM}.svg"
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n")
    fig.savefig(OUT / f"{STEM}.png", bbox_inches="tight", dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plot()
    base = row(INTEL[0], *L8B)
    nightly = []
    for run in INTEL:
        r = row(run, *L8B)
        nightly.append([
            f'[{run["date"][5:]}]({run["url"]})', f'`{run["package"].split("-")[-1]}`',
            f'{r["tps_mean"]:.2f}', f'{percent(r["tps_mean"], base["tps_mean"]):+.1f}%',
            f'{r["prefill_tps"]:.1f}', f'{percent(r["prefill_tps"], base["prefill_tps"]):+.1f}%',
            f'{r["ttft_rounded_ms"] / 1000:.3f}',
        ])
    other_rows = []
    for model, users, label in OTHERS:
        values = [row(run, model, users) for run in INTEL]
        decode = [v["tps_mean"] for v in values[2:]]
        prefill = [v["prefill_tps"] for v in values[2:]]
        other_rows.append([
            label, f'{values[0]["tps_mean"]:.2f}', f'{values[1]["tps_mean"]:.2f}',
            f'{min(decode):.2f}–{max(decode):.2f}',
            f'{percent(values[-1]["tps_mean"], values[0]["tps_mean"]):+.1f}%',
            f'{values[0]["prefill_tps"]:.1f} → {values[1]["prefill_tps"]:.1f} → {min(prefill):.1f}–{max(prefill):.1f}',
        ])
    amd_rows = []
    for run in AMD:
        r = row(run, *L8B)
        amd_rows.append([
            f'[{run["date"][5:]}]({run["url"]})', f'{r["tps_mean"]:.2f}',
            f'{r["prefill_tps"]:.1f}', str(r["n_samples"]),
        ])
    source_rows = []
    for run in INTEL:
        build = next((b for b in META["build"] if b["headSha"].startswith(run["package"].split("-")[-1])), None)
        build_link = f'[{build["databaseId"]}]({build["url"]})' if build else "Prior package (Sep 18)"
        source_rows.append([
            run["date"], f'`{run["package"]}`',
            f'[{run["run_id"]}]({run["url"]})', build_link,
            f'[Excerpt](../../exec/ci-amx-persistence-20260928/{run["evidence"]})',
        ])
    early = [
        (4522, "Placement cleanup", "Removes unused state. The random seed and placement sequence stay the same."),
        (4458, "Generated routing names", "Fixes identifier resolution. It does not affect the hand-written Llama AMX row."),
        (4526, "Placement lock removal", "Changes serial model loading. It does not change the placement sequence."),
        (4459, "Generated router identity", "Separates logical identity from storage. Separate routing fields are still emitted."),
        (4009, "Prequantized cache format", "Adds format helpers. Production loading is deferred to later changes."),
        (4460, "Routing preparation schedule", "Potential performance change for generated mixture-of-experts models. Preparation timing can change even though shared fields are deferred. No AMX-row effect: its Llama model is hand-written."),
        (4206, "Future module interface", "Adds an unused header. It has no runtime consumer."),
        (4551, "Comment correction", "No executable change."),
        (4536, "Placement helper extraction", "Computes the same device positions as the earlier loops."),
        (4353, "Attention work scheduling", "Definite new optimization in a shared runtime path. Its own measurements report GPT-OSS prefill and decode gains."),
    ]
    early_rows = []
    for number, category, finding in early:
        pr = next(p for p in META["prs"] if p["number"] == number)
        early_rows.append([f'[{number}]({pr["url"]})', pr["mergedAt"].replace("T", " ").replace("Z", ""), category, finding])
    prs = {p["number"]: p for p in META["prs"]}
    slack = json.loads((HERE / "evidence" / "slack-report-timestamps.json").read_text())
    slack.sort(key=lambda record: record["message_ts"])
    first_build = next(build for build in META["build"] if build["headSha"].startswith("5cf65b92"))
    events = [
        ("Baseline AMX-row benchmark begins (28.25 tok/s)", row(INTEL[0], *L8B)["start_time"], INTEL[0]["url"]),
        ("#4505: enable AMX in nightly packages", prs[4505]["mergedAt"], prs[4505]["url"]),
        ("#4534: disable shared wait counters", prs[4534]["mergedAt"], prs[4534]["url"]),
        ("Build first AMX-enabled package, 5cf65b92", first_build["createdAt"], first_build["url"]),
        ("First AMX-enabled benchmark begins (32.49 tok/s)", row(INTEL[1], *L8B)["start_time"], INTEL[1]["url"]),
        ("Slack posts first AMX-enabled nightly report", datetime.fromtimestamp(float(slack[0]["message_ts"]), timezone.utc).isoformat(), slack[0]["url"]),
        ("#4353: attention query-splitting optimization merges", prs[4353]["mergedAt"], prs[4353]["url"]),
        ("First benchmark with #4353 begins", row(INTEL[2], *L8B)["start_time"], INTEL[2]["url"]),
        ("Slack posts first report with #4353", datetime.fromtimestamp(float(slack[1]["message_ts"]), timezone.utc).isoformat(), slack[1]["url"]),
    ]
    timeline_rows = [
        [f"[{name}]({url})", timestamp(time).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%m-%d %H:%M:%S"), timestamp(time).strftime("%m-%d %H:%M:%S")]
        for name, time, url in events
    ]
    selected = [
        (*L8B, "Llama 8B TP2, 32 users (AMX row)"),
        ("llama-3.3-70b-instruct-good-tp4", 4, "Llama 70B TP4, 4 users"),
        ("ingested-qwen-3-4b-instruct-2507-tp2", 8, "Qwen 3 4B TP2, 8 users"),
        ("ingested-qwen-3-4b-instruct-2507-tp4", 8, "Qwen 3 4B TP4, 8 users"),
        ("ingested-gpt-oss-120b-tp4", 8, "GPT-OSS 120B TP4, 8 users"),
    ]
    after_rows = []
    for model, users, label in selected:
        before = row(INTEL[1], model, users)
        after = row(INTEL[2], model, users)
        after_rows.append([
            label, f'{before["tps_mean"]:.2f} → {after["tps_mean"]:.2f}',
            f'{percent(after["tps_mean"], before["tps_mean"]):+.2f}%',
            f'{before["prefill_tps"]:.1f} → {after["prefill_tps"]:.1f}',
            f'{percent(after["prefill_tps"], before["prefill_tps"]):+.2f}%',
        ])
    changes = []
    for machine, runs in [("intel", INTEL), ("amd", AMD)]:
        for before in runs[1]["rows"]:
            after = row(runs[2], before["config"]["model"], before["config"]["n_users"])
            assert before["config"] == after["config"]
            change = {"machine": machine, "model": before["config"]["model"],
                      "users": before["config"]["n_users"], "before_pacific_night": "2026-09-22",
                      "after_pacific_night": "2026-09-23", "before_run": runs[1]["run_id"],
                      "after_run": runs[2]["run_id"]}
            for metric in ("tps_mean", "prefill_tps", "ttft_rounded_ms"):
                change[f"before_{metric}"] = before[metric]
                change[f"after_{metric}"] = after[metric]
                change[f"change_{metric}_pct"] = percent(after[metric], before[metric])
            changes.append(change)
    with (HERE / "after-4353-comparison.csv").open("w") as output:
        writer = csv.DictWriter(output, fieldnames=list(changes[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(changes)
    text = f"""# AMX CI timeline: the first Pacific night was September 22

Written and updated September 28, 2026. The timeline below gives both Pacific daylight time (PDT, UTC−7) and UTC. The daily metric tables and chart retain UTC dates to match the package names, GitHub Actions, and Claude's original report.

**Short version.** AMX was enabled on September 22 Pacific time, and #4353 merged the following morning, September 23. Claude compared the correct packages, leaving one initial AMX-enabled nightly observation before the next attention optimization reached CI. The following nights show small additional prefill gains in some models and retain the large Llama 8B improvement, but the nightly comparisons do not isolate individual pull requests.

**Timestamp recheck: the user's note is correct.** The first AMX-enabled benchmark ran September 22 at 21:08–21:18 PDT. Its Slack report appeared September 23 at 06:05 PDT and prints exactly the remembered 32.5 TPS, approximately 354 prefill tokens/s, and 11,569 milliseconds to first token. The same benchmark is dated September 23 in UTC. #4353 merged September 23 at 08:50 PDT, so it did not merge on the Pacific calendar day when AMX was enabled.

{md_table(["Event", "Pacific date and time (PDT)", "UTC date and time"], timeline_rows)}

**Claude used the right comparison window.** Its baseline is the September 21 Pacific evening run, reported September 22, with package `2026.09.18-3faba6d0`. Its improved result is the September 22 Pacific evening run, reported September 23, with package `2026.09.23-5cf65b92`. Those are the actual 28.25 → 32.49 decode-token/s measurements. The date labels in Claude's document follow UTC/report dates. They do not select the wrong pair of runs.

Source ancestry confirms that #4353 is absent from both packages in Claude's comparison. It first appears in `2026.09.24-2a527a4b`, tested on the September 23 Pacific evening. The [saved membership check](../../exec/ci-amx-persistence-20260928/package-membership.json) also shows that #4505, #4534, and #4258 are present together in the first AMX-enabled package.

**How long before another performance change?** There is one nightly observation before #4353, on September 22 Pacific time. That benchmark finished 11 hours 32 minutes before #4353 merged. The gap between the AMX-enabling merge and #4353's merge is 18 hours 42 minutes. The next nightly, roughly 24 hours later, already contains #4353. There is no two- or three-day interval with the initial package's relevant runtime code unchanged.

Strictly, none of these nightly pairs isolates AMX alone. The wait-counter change #4534 merged 6 minutes 25 seconds after AMX enabling and shipped in the same first package. Claude's strong attribution for Llama 8B comes from the separate September 20 comparison of the same source built with and without AMX. Across the other models, the initial gains can include the wait-counter and accelerator-attention changes.

**What changed after #4353 reached CI?** The table compares September 22 → September 23 Pacific evenings, which are the September 23 → September 24 UTC reports. Both packages have AMX enabled. Decode is in tokens/s/user. Prefill is in tokens/s, calculated from prompt length divided by time to first token.

{md_table(["Intel benchmark", "Decode before → after", "Decode change", "Prefill before → after", "Prefill change"], after_rows)}

- The Llama 8B AMX row has effectively unchanged decode speed and 0.49% higher prefill. This is much smaller than its initial 15.0% decode and 61.2% prefill increases.
- GPT-OSS prefill increases 2.98% on the first updated night. Over all five subsequent nights, it remains 2.39–3.38% above the first AMX-enabled result. Qwen TP4 prefill remains 1.44–3.68% above that result. Thus these are observed, sustained package-level differences.
- The AMD machine's immediate changes are smaller or opposite for those prefill rows: GPT-OSS +0.49%, Qwen TP4 −1.49%, and Qwen TP2 −0.61%. That does not establish which change caused the Intel improvements.
- #4353's own GPT-OSS measurements use one user and roughly 2,000 or 32,000 prompt tokens. The nightly GPT-OSS row uses eight users per machine and 1,024 prompt tokens. Its reported 2.38%/4.28% prompt gains are therefore not predictions for this exact nightly row.
- The new package contains 31 further merges, including #4460's routing preparation changes. A before/after nightly comparison can establish a measured difference, but cannot attribute that difference to #4353 alone. The [full comparison CSV](../../exec/ci-amx-persistence-20260928/after-4353-comparison.csv) covers all 13 rows on both machines.

Later performance-relevant routing changes also arrive during the observed span. [#4461](https://github.com/positron-ai/tron/pull/4461) shares generated routing storage, and [#2750](https://github.com/positron-ai/tron/pull/2750) retains routing-buffer allocations. Both first appear in the September 26 Pacific nightly. Intel GPT-OSS decode rises 1.50% from the preceding night, to 120.70 tokens/s, but an earlier updated package had already reached 120.76 tokens/s. That change is not a distinct new best level. The September 27 Pacific package adds [#4492](https://github.com/positron-ai/tron/pull/4492) and [#4494](https://github.com/positron-ai/tron/pull/4494), changing routing traversal and row representation. GPT-OSS decode then changes −0.08%, and prefill changes +0.58%. These observations also do not isolate the individual changes. The [later PR descriptions and merge metadata](../../exec/ci-amx-persistence-20260928/later-prs.json) are preserved.

The original Llama 8B improvement remains visible on six Pacific nights, September 22–27, corresponding to the six UTC reports September 23–28. That is observed persistence across changing packages, not six days of AMX-only evidence.

**Detailed evidence below uses UTC run dates.** This preserves direct alignment with the earlier investigation and raw CI results.

**The document you remembered.** Claude's September 23 report is [“Did other merges change decode or prefill speed on 09-23?”](CI-merges-20260923.html). Its published copy is [the Claude artifact](https://claude.ai/artifact/XfjSvRGsrojxBN2qyHmc2t). The [session handoff](../../../../handoffs/claude_20260923_amx-benchmark-tps-regression-between-ci-runs.md) records the investigation and source files.

Claude concluded that AMX explained almost all of the Llama 8B benchmark's 15.0% decode gain. A prior comparison of the same source code built with and without AMX measured a 14.0% gain. The report separately identified other performance-relevant changes: [#4258](https://github.com/positron-ai/tron/pull/4258), which changes accelerator attention joins, and [#4534](https://github.com/positron-ai/tron/pull/4534), which disables shared wait counters. It treated #4534 as the likely, unconfirmed explanation for the extra Intel gains in three four-card models. It did **not** attribute every improved model to AMX alone.

**Terms and measurement.** AMX means Intel Advanced Matrix Extensions. CI means continuous integration. Tron is the inference program under test. Decode speed is generated tokens per second per user. TTFT is time to first token. The reported prefill rate is configured prompt length divided by mean TTFT, rounded to milliseconds first. This rate includes waiting behind other users' prompts. It is not aggregate engine throughput. TP2 and TP4 mean a model is split across two or four accelerator cards. A package suffix identifies the Tron source commit actually installed by the nightly job.

**How long, under each interpretation.**

- **Observed persistence: at least six consecutive nightly runs, September 23–28.** Llama 8B decode stayed 14.8–15.5% above September 22. Its TTFT-derived prefill rate stayed 61.2–62.1% above September 22. The series has no observed end to the improvement.
- **Before the next performance-relevant package: one nightly run, September 23.** The September 24 package already contains new attention scheduling and generated routing preparation changes. A two- or three-night window with unchanged relevant code does not exist.
- **AMX as the only meaningful main-branch change across all models: zero nightly runs.** [#4505](https://github.com/positron-ai/tron/pull/4505) enabled AMX in the package preset at September 22, 21:08:26 UTC. #4534 merged at 21:14:51 UTC, just 6 minutes 25 seconds later. Both are in the first AMX-enabled nightly package. This does not negate the independent same-code AMX result for Llama 8B.

![Daily decode and prefill gains, with subsequent runtime changes marked]({STEM}.svg)

**Llama 3.1 8B AMX benchmark: daily Intel results.** The load is unchanged across all seven runs: 32 users per machine, prompt length 4,096 tokens, 1,536 generated tokens, 10 rounds, and 320 completed requests. Each log identifies the same 332 eligible conversations and cycling order. The first row is the pre-AMX baseline. “Change” columns compare with that row.

{md_table(["CI date", "Package commit", "Decode (tok/s/user)", "Decode change", "Prefill (tok/s)", "Prefill change", "TTFT (s)"], nightly)}

The September 24–28 decode values remain within 0.42% of September 23. The prefill values remain within 0.56% of September 23. These observations support persistence of the original improvement. They do not isolate the AMX contribution in each later package.

**Where further performance changes enter.** [#4353](https://github.com/positron-ai/tron/pull/4353) merged on September 23 at 15:50:53 UTC (08:50:53 PDT). It splits software attention work within a page across processor cores by query. It also changes query bounds and bookkeeping in the shared attention path. Its own measurements report GPT-OSS prefill gains of 2.38% at roughly 2,000 prompt tokens and 4.28% at roughly 32,000 prompt tokens, plus a 1.03% decode gain at the longer prompt. Its Llama controls showed less than 1% movement under the tested loads. Those controls did not use this exact 4,096-token AMX benchmark.

The September 24 package is `2026.09.24-2a527a4b`. Its source contains #4353. The September 23 package, `2026.09.23-5cf65b92`, does not. This is a definite cutoff for claiming that later CI changes have no new attention optimization as a possible cause. It is not evidence that AMX stopped working.

There is an earlier possible cause for generated models: [#4460](https://github.com/positron-ai/tron/pull/4460) merged at September 23, 03:51:52 UTC. Its routing assignment is not yet used to share storage, but its preparation schedule is consumed by the code generator. A reusable routing slot can therefore move a channel preparation later. This makes it unsafe to dismiss the entire change as unused analysis. The hand-written Llama 8B AMX row does not use that generator path. #4460 also first reaches these nightly benchmarks in the September 24 package.

The first positive AMX benchmark ran at 04:08–04:18 UTC on September 23. Main had therefore already accepted #4460 when that benchmark ran, but the installed package still used the earlier source snapshot. A merge time does not identify the source snapshot installed by a CI job.

**Audit up to the new attention optimization.** Times in this table are GitHub's `mergedAt` values. They differ from the timestamps stored in some merge commits. No new controlled performance tests were run for these changes.

{md_table(["PR", "Merged at (UTC)", "Change", "Assessment"], early_rows)}

The complete [31-merge list for the successor package](../../exec/ci-amx-persistence-20260928/successor-package-merges.tsv) records the scope after September 23. The source diffs for [attention scheduling](../../exec/ci-amx-persistence-20260928/evidence/attention-split-4353.patch) and [routing preparation](../../exec/ci-amx-persistence-20260928/evidence/routing-preparation-4460.patch) are saved with this report.

**The other three model gains also persist.** All decode columns below use tokens per second per user. The prefill sequence is September 22 → September 23 → the September 24–28 range, in tokens per second. These are observations about the package changes, not AMX-only measurements.

{md_table(["Model", "Sep 22 decode", "Sep 23 decode", "Sep 24–28 decode range", "Sep 28 decode change", "Prefill sequence (tok/s)"], other_rows)}

Qwen and GPT-OSS run accelerator attention in the original investigation. Llama 70B does not have the AMX kernel's supported attention shape. Persistence of their gains is therefore not proof of an AMX effect. The original wait-counter and accelerator-join explanations remain possible causes. The large Llama 8B AMX gain has stronger attribution evidence from the prior same-code comparison.

**AMD control for the same Llama 8B row.** AMD cannot run the Intel AMX kernel. Its decode remains near the September 22 baseline while Intel retains the large gain.

{md_table(["CI date", "Decode (tok/s/user)", "Prefill (tok/s)", "Completed requests"], amd_rows)}

The September 26–28 AMD workflows were cancelled later. Their Llama 8B rows each completed all 320 requests before cancellation. They are included only as completed row measurements. Other AMD rows have large anomalies, especially Llama 70B TP4, so this report does not assume the whole AMD workflow was healthy.

**Verification and limits.**

- Retrieved fresh September 24–28 job logs for both machines. Reused the preserved September 22–23 raw logs. Extracted 182 completed benchmark rows and 20,160 request records across 14 jobs.
- Checked every row against its expected request count and 10 running-average records. Recomputed means agree with the final logged averages within 0.011 decode tokens/s and 1.1 milliseconds of TTFT. The four original Llama 8B row records reproduce Claude's saved values exactly to floating-point precision.
- Verified that the AMX row's logged load settings and prompt dataset description are identical each day. The later test-harness commit changes quality-score threshold policy, not benchmark load or the prefill formula.
- Matched each installed package to its published build. The Debian package preset keeps `TRON_AMX_DISPATCH=ON` in all September 23–28 source snapshots. The AMX kernel source and interface are unchanged over that span.
- The workflow's overall failure or cancellation status is not treated as a missing performance measurement. A row is included only after all requests and rounds complete. Complete measurements can still contain machine effects.
- No new AMX on/off comparison was performed. No causal estimate is assigned to the small differences between later nights. Claude's 0.29 decode-token/s residual is a descriptive comparison with its earlier campaign, not a statistical upper bound on every other change.
- Prefill values come from logged per-request TTFT rounded to whole milliseconds. This matches the original report's method and the harness formula closely. A sub-millisecond rounding boundary can shift another model's reconstructed prefill slightly.

**Primary run and package evidence.**

{md_table(["CI date", "Installed package", "CI run", "Package build", "Saved log evidence"], source_rows)}

The [all-model CSV](../../exec/ci-amx-persistence-20260928/rows.csv) includes both machines. The [structured results](../../exec/ci-amx-persistence-20260928/results.json) retain request samples, row timestamps, settings, source line numbers, and log hashes. The [source metadata](../../exec/ci-amx-persistence-20260928/metadata.json) preserves PR descriptions, merge times, run statuses, build commits, and the main heads read during this investigation.

Reproduce the extraction with [analyze.py](../../exec/ci-amx-persistence-20260928/analyze.py). Download a source log with `gh run view RUN_ID -R positron-ai/systems_test --log`. Generate this report with [report.py](../../exec/ci-amx-persistence-20260928/report.py).
"""
    (OUT / f"{STEM}.md").write_text(text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    svg = (OUT / f"{STEM}.svg").read_text()
    svg = svg[svg.index("<svg"):]
    svg = svg.replace("<svg ", '<svg role="img" aria-label="Daily decode and prefill gains" ', 1)
    body = body.replace(
        f'<img alt="Daily decode and prefill gains, with subsequent runtime changes marked" src="{STEM}.svg" />',
        svg,
    )
    page = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AMX CI timeline: the first Pacific night was September 22</title>
<style>
:root{color-scheme:light}body{margin:0;background:#f4f6f8;color:#1b2935;font:16px/1.65 system-ui,sans-serif}
main{max-width:1200px;margin:32px auto;background:white;padding:38px 44px;border:1px solid #dde3e8;border-radius:12px}
h1{font-size:32px;line-height:1.2;max-width:940px;margin-top:0}p,li{max-width:1080px}a{color:#1d5d99;text-underline-offset:3px}
p:has(>strong:first-child){margin-top:30px}img,svg{max-width:100%;height:auto}table{font-size:13px;line-height:1.45;border-collapse:collapse;width:100%;margin:18px 0;display:block;overflow:auto}
th{background:#e9eff4;text-align:left;position:sticky;top:0}td,th{border:1px solid #dbe2e8;padding:9px 10px;vertical-align:top}tr:nth-child(even) td{background:#f8fafb}code{background:#eff2f5;border-radius:3px;padding:2px 4px;font-size:.88em}li{margin:9px 0}
@media(max-width:700px){main{margin:0;padding:22px 16px;border:0;border-radius:0}h1{font-size:26px}body{font-size:15px}}
</style><main>""" + body + "</main></html>"
    (OUT / f"{STEM}.html").write_text(page)
    print(OUT / f"{STEM}.html")
    print(OUT / f"{STEM}.md")


if __name__ == "__main__":
    main()
