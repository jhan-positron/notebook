#!/usr/bin/env python3
import json
import math
import os
import sys
from pathlib import Path


def load_benchmark_lib():
    repo = Path("/home/jhan/workspace/tron")
    sys.path.insert(0, str(repo / "bin" / "ci"))
    import benchmark_lib as b  # type: ignore

    return b


def load_experiments(output_dir: Path) -> list[dict]:
    experiments: list[dict] = []
    for rep_dir in sorted(output_dir.glob("repeat_*")):
        for meta_path in sorted(rep_dir.glob("inst*_meta.json")):
            idx = meta_path.stem.removeprefix("inst").removesuffix("_meta")
            stdout_path = rep_dir / f"inst{idx}_stdout.log"
            stderr_path = rep_dir / f"inst{idx}_stderr.log"
            with meta_path.open() as f:
                meta = json.load(f)
            meta["stdout"] = stdout_path.read_text() if stdout_path.exists() else ""
            meta["stderr"] = stderr_path.read_text() if stderr_path.exists() else ""
            experiments.append(meta)
    return experiments


def pct_change(a: float, b: float) -> str:
    if not a or math.isnan(a) or math.isnan(b):
        return "nan"
    return f"{(b / a - 1.0) * 100.0:+.2f}%"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: summarize_ci32u_run.py OUTPUT_DIR SUMMARY_JSON", file=sys.stderr)
        return 2
    output_dir = Path(sys.argv[1])
    summary_json = Path(sys.argv[2])
    b = load_benchmark_lib()
    experiments = load_experiments(output_dir)
    if not experiments:
        raise SystemExit(f"no experiment logs found under {output_dir}")

    evals = b.eval_experiments(experiments)
    if not evals:
        raise SystemExit("benchmark_lib.eval_experiments returned no evaluations")
    evaluation = evals[0]

    result = {
        "output_dir": str(output_dir),
        "experiment_count": len(experiments),
        "returncodes": [e.get("returncode") for e in experiments],
        "durations_sec": [e.get("duration") for e in experiments],
        "evaluation": evaluation,
        "primary_metric": {
            "name": "direct_ci_style_gen_rate_per_machine",
            "value": evaluation["gen_rate_per_machine"],
            "unit": "tok/s",
            "method": "benchmark_lib.eval_experiments over four concurrent runtron instance logs",
        },
        "secondary_metrics": {
            "parse_rate_per_machine": evaluation["parse_rate_per_machine"],
            "gen_rate_per_user": evaluation["gen_rate_per_user"],
            "parse_rate_per_user": evaluation["parse_rate_per_user"],
            "n_samples": evaluation["n_samples"],
            "error_rate": evaluation["error_rate"],
            "sample_runs": evaluation["sample_runs"],
            "sample_instances": evaluation["sample_instances"],
        },
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(result, indent=2, default=str) + "\n")

    print(f"output_dir={output_dir}")
    print(f"experiments={len(experiments)} returncodes={result['returncodes']}")
    print(f"gen_rate_per_machine_tok_s={evaluation['gen_rate_per_machine']:.6f}")
    print(f"parse_rate_per_machine_tok_s={evaluation['parse_rate_per_machine']:.6f}")
    print(f"gen_rate_per_user_tok_s={evaluation['gen_rate_per_user']:.6f}")
    print(f"parse_rate_per_user_tok_s={evaluation['parse_rate_per_user']:.6f}")
    print(f"n_samples={evaluation['n_samples']} error_rate={evaluation['error_rate']:.6f}")
    if any(code != 0 for code in result["returncodes"]):
        print(f"ERROR: one or more runtron instances failed: {result['returncodes']}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
