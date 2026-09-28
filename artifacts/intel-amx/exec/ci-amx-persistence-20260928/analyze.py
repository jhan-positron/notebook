#!/usr/bin/env python3
"""Extract completed CI benchmark rows and retain auditable source excerpts.

Usage: python3 analyze.py --logs /tmp/ci-amx-persistence-20260928
                              --previous /path/to/ci-amx-row-20260923
Outputs are written beside this script. Raw logs stay outside the notebook.
"""

import argparse
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TIMESTAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z")
CONFIG_FIELDS = (
    "n_users", "n_rounds", "stagger_delay", "model", "shared_prompt_length",
    "prompt_length", "generate_length", "start_capture", "end_capture",
    "sample_interval", "continuous_usage", "max_tokens",
)


def parse(path, machine, run_id):
    raw = path.read_bytes()
    lines = ANSI.sub("", raw.decode("utf-8", errors="replace")).splitlines()
    rows = []
    row = None
    package = None
    excerpts = []
    for index, line in enumerate(lines):
        line_number = index + 1
        match = re.search(r"Setting up tron \(([^)]+)\)", line)
        if match:
            package = match[1]
            excerpts.append((line_number, line))
        if re.search(r"\bn_users=\d+,", line):
            config = {}
            config_lines = []
            for offset, config_line in enumerate(lines[index:index + 18]):
                for field in CONFIG_FIELDS:
                    match = re.search(r"\b" + field + r"=('[^']*'|[^,]+),", config_line)
                    if match:
                        value = match[1]
                        if value.startswith("'"):
                            value = value.strip("'")
                        else:
                            value = float(value) if "." in value else int(value)
                        config[field] = value
                        config_lines.append((line_number + offset, config_line))
            if "model" in config and "prompt_length" in config:
                row = {
                    "config": config, "config_line": line_number,
                    "start_time": TIMESTAMP.search(line)[0],
                    "samples_tps": [], "samples_ttft_ms": [],
                    "running_averages": [], "completed": False,
                }
                rows.append(row)
                excerpts.extend(config_lines)
        if row is None:
            continue
        if "eligible conversations" in line:
            row["dataset"] = line.split("Using ")[-1]
            excerpts.append((line_number, line))
        match = re.search(r"Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)", line)
        if match:
            row["samples_ttft_ms"].append(int(match[1]))
            row["samples_tps"].append(float(match[2]))
        match = re.search(r"Running averages: TTFT=(\d+), TPS=([\d.]+)", line)
        if match:
            row["running_averages"].append({
                "line": line_number, "ttft_ms": int(match[1]), "tps": float(match[2])
            })
            row["last_average_line"] = line
        match = re.search(r"Perf test for (.+) completed in", line)
        if match and match[1] == row["config"]["model"]:
            row["completed"] = True
            row["completion_line"] = line_number
            row["end_time"] = TIMESTAMP.search(line)[0]
            if row["running_averages"]:
                excerpts.append((row["running_averages"][-1]["line"], row.pop("last_average_line")))
            excerpts.append((line_number, line))
            row = None

    checks = []
    for row in rows:
        count = len(row["samples_tps"])
        expected = row["config"]["n_users"] * row["config"]["n_rounds"]
        row["n_samples"] = count
        row["expected_samples"] = expected
        row["usable"] = row["completed"] and count == expected
        if not count:
            continue
        row["tps_mean"] = statistics.mean(row["samples_tps"])
        row["tps_sd"] = statistics.pstdev(row["samples_tps"])
        row["ttft_mean_ms"] = statistics.mean(row["samples_ttft_ms"])
        # Match the harness formula: round mean TTFT to milliseconds first.
        row["ttft_rounded_ms"] = round(row["ttft_mean_ms"])
        row["prefill_tps"] = row["config"]["prompt_length"] * 1000 / row["ttft_rounded_ms"]
        if row["usable"]:
            final_average = row["running_averages"][-1]
            tps_gap = abs(row["tps_mean"] - final_average["tps"])
            ttft_gap = abs(row["ttft_mean_ms"] - final_average["ttft_ms"])
            checks.append({
                "model": row["config"]["model"], "users": row["config"]["n_users"],
                "tps_gap": tps_gap, "ttft_gap_ms": ttft_gap,
                "rounds": len(row["running_averages"]), "samples": count,
            })
            assert tps_gap <= 0.011, (path, row["config"], tps_gap)
            assert ttft_gap <= 1.1, (path, row["config"], ttft_gap)
            assert len(row["running_averages"]) == row["config"]["n_rounds"]
    excerpt_path = HERE / "evidence" / f"{machine}-{run_id}.txt"
    excerpt_path.parent.mkdir(exist_ok=True)
    excerpt_path.write_text(
        f"Source: https://github.com/positron-ai/systems_test/actions/runs/{run_id}\n"
        f"Raw log SHA256: {hashlib.sha256(raw).hexdigest()}\n"
        "Numbers before each line refer to the unmodified gh run view --log output.\n\n"
        + "\n".join(f"{number}: {text}" for number, text in sorted(set(excerpts))) + "\n"
    )
    return {
        "machine": machine, "run_id": run_id,
        "url": f"https://github.com/positron-ai/systems_test/actions/runs/{run_id}",
        "date": rows[0]["start_time"][:10] if rows else None,
        "package": package, "raw_log_path": str(path),
        "raw_log_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_log_bytes": len(raw), "evidence": str(excerpt_path.relative_to(HERE)),
        "rows": rows, "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    args = parser.parse_args()
    inputs = [
        (args.previous / "nightly-35683952944.log", "intel", 35683952944),
        (args.previous / "nightly-35815209295.log", "intel", 35815209295),
        (args.previous / "nightly-genoa-35682128668.log", "amd", 35682128668),
        (args.previous / "nightly-genoa-35813240282.log", "amd", 35813240282),
    ]
    for path in sorted(args.logs.glob("*.log")):
        machine, _, run_id = path.stem.split("-")
        inputs.append((path, machine, int(run_id)))
    runs = [parse(*item) for item in inputs]
    runs.sort(key=lambda run: (run["machine"], run["date"]))
    (HERE / "results.json").write_text(json.dumps(runs, indent=2) + "\n")
    columns = [
        "machine", "date", "package", "run_id", "model", "users", "prompt_tokens",
        "generated_tokens", "n_samples", "expected_samples", "usable", "tps_mean",
        "ttft_mean_ms", "ttft_rounded_ms", "prefill_tps", "source_url",
    ]
    with (HERE / "rows.csv").open("w") as output:
        writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for run in runs:
            for row in run["rows"]:
                if not row["n_samples"]:
                    continue
                config = row["config"]
                writer.writerow({
                    **{key: run[key] for key in ("machine", "date", "package", "run_id")},
                    **{key: row[key] for key in (
                        "n_samples", "expected_samples", "usable", "tps_mean",
                        "ttft_mean_ms", "ttft_rounded_ms", "prefill_tps",
                    )},
                    "model": config["model"], "users": config["n_users"],
                    "prompt_tokens": config["prompt_length"],
                    "generated_tokens": config["generate_length"], "source_url": run["url"],
                })
    for run in runs:
        print(run["machine"], run["date"], run["package"],
              f'{sum(row["usable"] for row in run["rows"])}/{len(run["rows"])} complete rows')
        for row in run["rows"]:
            if row["config"]["n_users"] == 32 and row["config"]["prompt_length"] == 4096:
                print("  AMX row:", row["n_samples"], "samples,", round(row["tps_mean"], 3),
                      "decode tok/s,", round(row["prefill_tps"], 2), "prefill tok/s,",
                      row["ttft_rounded_ms"], "ms TTFT")


if __name__ == "__main__":
    main()
