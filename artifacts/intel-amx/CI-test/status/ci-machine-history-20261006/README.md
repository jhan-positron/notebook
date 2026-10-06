# Delphi versus Andoria after the AMX rollout

**Short version:** Llama 3.1 8B at 32 users is the only tested workload with a new, sustained Delphi lead after AMX was enabled. The reversal first appears in the September 23, 2026 nightly report and holds on all 14 paired nights through October 6. Mixtral 8x7B, Gemma 2 9B, and Gemma 4 31B already led on Delphi before the rollout.

- [Rendered report](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/CI-test/status/ci-machine-history-20261006/report.html)
- [Backup rendered report](https://raw.githack.com/jhan-positron/notebook/main/artifacts/intel-amx/CI-test/status/ci-machine-history-20261006/report.html)
- [Report source](report.html), [paired measurements](paired-results.csv), and [all-model summary](summary.json)

Delphi means delphi-3bda, the Intel Granite Rapids machine. Andoria means andoria-b1a3, the AMD Genoa machine. AMX means Intel Advanced Matrix Extensions. The comparison measures mean generated tokens per second per user. TP2 splits the model across two accelerator cards. CI means continuous integration, the automated nightly test suite.

## Historical conclusion

The Llama 3.1 8B workload uses TP2, 32 users per machine, a 4,096-token prompt, and 1,536 generated tokens. The September 22 report is the baseline without AMX. The package change enabling AMX merged later on September 22. [Baseline explanation](https://positronai.slack.com/archives/C06S8PNDBQA/p1790095827478439), [package change](https://github.com/positron-ai/tron/pull/4505).

| Workload | September 22 Delphi lead | Wins, September 23-October 6 | Classification |
| --- | ---: | ---: | --- |
| Llama 3.1 8B, TP2, 32 users | -2.6% | 14/14 nights | Only new sustained lead after rollout |
| Mixtral 8x7B, TP2, 8 users | +1.6% | 14/14 nights | Lead predates rollout |
| Gemma 2 9B, TP2, 8 users | +4.7% | 14/14 nights | Lead predates rollout |
| Gemma 4 31B, TP2, 8 users | +8.2% | 14/14 nights | Lead predates rollout |

The baseline values come from the [September 22 Delphi session](http://talos:5174/sessions/4d0034b1-b637-11f1-87f0-bc2411bdb3f2) and [September 22 Andoria session](http://talos:5174/sessions/1e9c1199-b633-11f1-9378-bc2411bdb3f2). The win counts are computed from [every paired nightly measurement](paired-results.csv).

- Llama 3.1 8B changes from **28.25 versus 29.00 tokens/s** on September 22 to **32.49 versus 28.91 tokens/s** on September 23. Its lead is **12.4%-14.1%** on the 14 nights after rollout. The median daily lead is **13.5%**. [Daily source table](report.html).
- The same model at **8 users** remains faster on Andoria on all 14 nights. The conclusion is specific to the 32-user workload. [All-model summary](summary.json).
- Llama 70B and GPT-OSS have temporary Delphi wins during Andoria slowdowns. Those do not form another sustained reversal after rollout. [September 29 discussion](https://positronai.slack.com/archives/C06S8PNDBQA/p1790699156777329), [October 2 incident](https://positronai.slack.com/archives/C06S8PNDBQA/p1790948618221139).

This is a historical conclusion about which machine leads. Other models can improve without gaining a sustained Delphi lead. The nightly sequence establishes the timing but does not isolate each change in the package.

## Reproduce the report

Run from this directory with Python 3, NumPy, and Matplotlib installed:

```sh
python3 analyze.py
python3 build_report.py
```

The analysis asserts that Llama 3.1 8B at 32 users is the sole workload that was behind on September 22 and then won all 14 subsequent nightly pairs. All required inputs are preserved here. The scripts read saved data and do not run machine benchmarks.

- `first-week-*.json` and `recent-search.json`: saved Slack reports for September 22-October 6.
- `talos/`: 31 stored session summaries, including the October 2 Andoria rerun. Talos is the internal test-results service.
- `earlier-context/reports.json`: 15 saved report records for September 15-21, including one rerun and one report without performance results.
- `paired-results.csv`, `paired-results.json`, and `summary.json`: calculated results with source links.
- `reports.json` and `reruns.json`: parsed reports and separately retained reruns.
- `report.html`: standalone light-background report with embedded charts and an interactive source table.
- `*.png` and `*.svg`: chart exports. `report.html.lineage.md` records preservation details.

## Preservation

Canonical directory: `/home/jhan/workspace/random/ci-machine-history-2026-10-06/`.

Notebook mirror: `artifacts/intel-amx/CI-test/status/ci-machine-history-20261006/`.

Edit the canonical sources first, regenerate the report, and refresh the notebook mirror. Local browser screenshots and a redundant September 29 session download are omitted from the mirror. The corresponding measurements are preserved in `talos/`.
