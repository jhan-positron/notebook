# perf-model-20260903: AMX decode boost from a data-wait model (raw data)

Campaign of 2026-09-03 on delphi-3bda (Xeon 6962P), qwen-3-4b-tp2, one user, prompt 8192.
Tron ran only in its AVX form (kill switch); the AMX unit was measured with a copy of Tron's
AMX kernel run outside Tron (tools/src/unit_bench.cpp).

- pages/index.html: the report (estimate +14.4% vs measured +17.3%; verdict per the plan's
  gate: calibration failed, "close" if the gate is waived). pages/action-plan.html: the plan.
- results/: campaign.log, book-sens.log, m0..m8 raw files, m3-*.json (unit benchmark),
  m7-kvwait-*.bin.gz (Tron probe records, sparse, gzipped), m8-avx-1u-8192.perfetto-trace.gz
  (traced Tron AVX run, 19 MiB), medians.json (parse.py), model.json (model.py), m8-spans.json,
  narrative.json.
- tools/: run-perf-model.sh, run-book-sens.sh, launch.sh, parse.py, model.py, spans.py,
  gen_report.py and the C/C++ sources (unit_bench.cpp, memrate.c, latency.c, insn_loops.cpp).
