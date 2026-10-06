"""Compare matching nightly workloads and retain sources for each measurement."""

import csv
import json
import re
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
EARLIER = ROOT / "earlier-context"
AMX = "llama-3.1-8b-instruct-good-tp2 @32u (AMX benchmark)"


def normalized(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def flatten(value, prefix=""):
    for key, item in value.items():
        name = f"{prefix}{key}"
        if isinstance(item, dict):
            yield from flatten(item, name + ".")
        else:
            yield name, item


def read_search(path):
    saved = json.loads(path.read_text())
    assert "No more pages" in saved["pagination_info"], path
    for segment in re.split(r"### Result \d+ of \d+\n", saved["results"])[1:]:
        header, body = segment.split("Text: \n", 1)
        date = re.search(r"Nightly Report \((\d{4}-\d{2}-\d{2})\)", body)
        if not date:
            continue
        machine = re.search(r"DUT: (delphi-3bda|andoria-b1a3)", body)[1].split("-")[0]
        report = {
            "machine": machine,
            "date": date[1],
            "timestamp": re.search(r"Message_ts: (\S+)", header)[1],
            "url": re.search(r"Permalink: \[link\]\((.*?)\)", header)[1],
            "version": re.search(r"Tron.*", body)[0],
            "source_file": path.name,
            "body": body,
            "performance": [],
        }
        session = re.search(r"http://talos:5174/sessions/([\w-]+)", body)
        report["talos_url"] = session[0] if session else ""
        for line in body.splitlines():
            match = re.match(r"\s+:([^:]+): ([\w.\-]+) @(\d+)u per machine(?: \(([^)]+)\))?: (.*)", line)
            if not match:
                continue
            status, model, users, label, metrics = match.groups()
            tps = re.match(r"\*?([\d.]+)\*? TPS", metrics)
            if not tps:
                tps = re.search(r"of decode goal \(([\d.]+) /", metrics)
            assert tps, (path, report["date"], line)
            ttft = re.search(r"TTFT (\d+)ms", line)
            slowest = re.search(r"slowest user @ ([\d.]+)", line)
            prefill = re.search(r"prefill≈([\d.]+)(k?) tok/s", line)
            key = f"{model} @{users}u" + (f" ({label})" if label else "")
            report["performance"].append({
                "key": key, "model": model, "users": int(users), "label": label or "",
                "status": status, "tps": float(tps[1]), "tps_decimals": len(tps[1].split(".")[1]),
                "ttft_ms": int(ttft[1]) if ttft else None,
                "slowest_tps": float(slowest[1]) if slowest else None,
                "prefill_est_tokens_s": float(prefill[1]) * (1000 if prefill[2] else 1) if prefill else None,
                "raw_line": line, "value_source": report["url"],
            })
        assert len(report["performance"]) == body.count("u per machine:" ) + body.count("u per machine (AMX benchmark):"), report
        yield report


def enrich(report):
    source = ROOT / "talos" / (report["talos_url"].rsplit("/", 1)[-1] + ".json")
    if not source.exists():
        source = EARLIER / f"{report['machine']}-talos-{report['date']}.json"
    if not source.exists():
        return
    raw = json.loads(source.read_text())
    if "dut" in raw:
        assert raw["dut"].startswith(report["machine"]), source
    assert raw["tron_version"] in report["version"], source
    stored = {normalized(k): v for k, v in flatten(raw) if "_tps @ " in k}
    report["talos_url"] = f"http://talos:5174/sessions/{raw['uuid']}"
    for row in report["performance"]:
        storage_key = normalized(row["model"] + f"tps{row['users']}")
        if storage_key not in stored:
            assert row["tps"] == 0 and row["status"] == "x", (source, row)
            row["measurement_missing"] = True
            continue
        value = stored[storage_key]
        match = re.match(r"([\d.]+) \(std dev ([\d.]+)\) TTFT (\d+)ms, prefill (\d+) tok/s", value)
        assert match, value
        tps, deviation, ttft, prefill = match.groups()
        assert abs(float(tps) - row["tps"]) <= 0.051, (source, row, tps)
        assert row["ttft_ms"] in (None, int(ttft)), (source, row, ttft)
        row.update(tps=float(tps), tps_decimals=2, ttft_ms=int(ttft), prefill_est_tokens_s=int(prefill),
                   sample_tps_stddev=float(deviation), talos_line=value, value_source=report["talos_url"])
        if row["key"] == AMX:
            assert "prompt=4096 generate=1536 shared_prefix=0 capture=896-1024 users=32 mode=sharegpt" in value, (source, value)


reports = []
for filename in ["first-week-delphi.json", "first-week-andoria.json", "recent-search.json"]:
    reports.extend(read_search(ROOT / filename))
for report in reports:
    enrich(report)

# Earlier reports provide context for leads that predate the new AMX workload.
for report in json.loads((EARLIER / "reports.json").read_text()):
    if report["date"] >= "2026-09-22":
        continue
    for row in report["performance"]:
        row["tps_decimals"] = 2
        row["value_source"] = report.get("talos_url", report["url"])
        row["prefill_est_tokens_s"] = row.pop("prefill_display_tokens_s", None)
    reports.append(report)

reports.sort(key=lambda r: (r["date"], r["machine"], float(r["timestamp"])))
nightlies = {}
reruns = []
for report in reports:
    pair = report["date"], report["machine"]
    if pair in nightlies:
        reruns.append(report)
    else:
        nightlies[pair] = report

assert len([r for r in nightlies.values() if r["date"] >= "2026-09-22"]) == 30
pairs = []
for date in sorted({r["date"] for r in reports}):
    delphi = nightlies.get((date, "delphi"))
    andoria = nightlies.get((date, "andoria"))
    if not delphi or not andoria:
        continue
    other = {p["key"]: p for p in andoria["performance"]}
    for p in delphi["performance"]:
        q = other.get(p["key"])
        if not q:
            continue
        valid = p["tps"] > 0 and q["tps"] > 0
        row = {"date": date, "key": p["key"], "delphi_tps": p["tps"], "andoria_tps": q["tps"],
               "delphi_tps_decimals": p["tps_decimals"], "andoria_tps_decimals": q["tps_decimals"],
               "valid": valid, "delphi_lead_pct": (p["tps"] / q["tps"] - 1) * 100 if valid else None,
               "delphi_url": delphi["url"], "andoria_url": andoria["url"],
               "delphi_value_source": p["value_source"], "andoria_value_source": q["value_source"]}
        for machine, measurement in [("delphi", p), ("andoria", q)]:
            for metric in ["ttft_ms", "slowest_tps", "prefill_est_tokens_s", "status"]:
                row[f"{machine}_{metric}"] = measurement.get(metric)
        pairs.append(row)

summaries = []
for key in dict.fromkeys(p["key"] for p in pairs):
    summary = {"key": key}
    for name, start, end in [("pre", "2026-09-15", "2026-09-22"), ("post", "2026-09-23", "2026-10-06")]:
        observations = [p for p in pairs if p["key"] == key and start <= p["date"] <= end and p["valid"]]
        wins = [p for p in observations if p["delphi_lead_pct"] > 0]
        summary[name] = {"n": len(observations), "wins": len(wins), "win_dates": [p["date"] for p in wins]}
        if observations:
            summary[name].update(median_lead_pct=median(p["delphi_lead_pct"] for p in observations),
                                 min_lead_pct=min(p["delphi_lead_pct"] for p in observations),
                                 max_lead_pct=max(p["delphi_lead_pct"] for p in observations),
                                 delphi_median_tps=median(p["delphi_tps"] for p in observations),
                                 andoria_median_tps=median(p["andoria_tps"] for p in observations))
    summaries.append(summary)

baseline_pairs = {p["key"]: p for p in pairs if p["date"] == "2026-09-22" and p["valid"]}
new_sustained_leads = [
    s["key"] for s in summaries
    if s["post"]["n"] == 14 and s["post"]["wins"] == 14
    and s["key"] in baseline_pairs and baseline_pairs[s["key"]]["delphi_lead_pct"] < 0
]
assert new_sustained_leads == [AMX], new_sustained_leads

for name, data in [("reports.json", reports), ("paired-results.json", pairs), ("summary.json", summaries), ("reruns.json", reruns)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n")
with (ROOT / "paired-results.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(pairs[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(pairs)

print("AMX DAILY PAIRS")
print("ONLY NEW SUSTAINED LEAD", new_sustained_leads)
for p in pairs:
    if p["key"] == AMX:
        print(p["date"], p["delphi_tps"], p["andoria_tps"], f"{p['delphi_lead_pct']:+.3f}%")
print("ALL WORKLOADS")
for s in summaries:
    print(s["key"], json.dumps({k: v for k, v in s.items() if k != "key"}))
print("RERUNS", [(r["date"], r["machine"], r["timestamp"]) for r in reruns])
print("INVALID PAIRS", [(r["date"], r["key"], r["delphi_tps"], r["andoria_tps"]) for r in pairs if not r["valid"]])
