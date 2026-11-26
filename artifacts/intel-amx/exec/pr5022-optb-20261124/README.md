# pr5022-optb-20261124: A/B machine test of "option B" for tron PR 5022 on delphi-3b35

## Short version

Option B changes one declaration of `s_pages` in `h/tron/models/self_attention.hpp`. Two builds of the rebased
PR head `187da02163`, one without and one with the change, gave the same tokens on Muse Glimmer 30B and on
llama-3.1-8b, and all unit tests pass in both. Throughput differs by 0.16% at most, inside the run-to-run spread.

Run on 2026-11-25, 00:33 to 01:04 UTC (31 minutes). Report page: `muse-glimmer/pr5022-optb-ab.html`.

## Words used here

- tron: the inference program under test. runtron: its command-line tool.
- AMX: Intel's tile-matrix instruction set. kv_mul: query heads per KV head (Glimmer 16, llama-3.1-8b 4).
- Arm a: the commit unchanged. Arm b: the commit with the option B declaration (3 changed lines).
- Option B: `auto s_pages = make_array_of<tensor<page::page_size>, operation_kv_mul>(uninitialized);` in place of
  `tensor<operation_kv_mul, page::page_size> s_pages{uninitialized};`.
- Band: twice the larger standard deviation of the two arms (the rule of `exec/glimext-20261018/gen_report.py`).
- delphi-3b35: the shared AMX test machine. Our half: CPUs 96-143 and 223-230, FPGA cards 90/93/b9/bc,
  `SYSTEM_CONFIG="--instance 1,2"`.

## Files

| File | Runs on | What it does |
|---|---|---|
| chain.sh | delphi-3b35, detached | Steps B (both builds in parallel), T (unit tests), I (token identity), P (throughput, 4 repetitions per arm, arm order alternating). |
| build-3b35.sh | delphi-3b35 | `TAG=a` or `TAG=b`: worktree `/var/tmp/jhan/b35-optb-$TAG` at `187da02163`, the option B edit for b, build of runtron and three unit tests with the two model plugins. |
| run-one.sh | delphi-3b35 | One runtron run with a load snapshot first. It refuses to start when our cards are open or our CPUs are more than 5% busy. |
| models.optb.yaml | - | Registry with the two models, so that the build compiles only their plugins. |
| collect.py | anywhere | Reads the run logs into `summary.json` and prints a text table. |
| gen_report.py, report-template.html | anywhere | Write the report page from `summary.json`. The script stops when a number in the page text differs from the data. |

run-one.sh is a copy of `exec/gdn-20261120/run-one.sh` with four settings changed: the tree prefix
(`b35-optb-`), the results folder name, and `MODEL` and `TAG` are required inputs.

## How to run

```
ssh delphi-3b35 'setsid nohup bash ~/workspace/intel-AMX/exec/pr5022-optb-20261124/chain.sh >/dev/null 2>&1 </dev/null &'
python3 exec/pr5022-optb-20261124/collect.py
python3 exec/pr5022-optb-20261124/gen_report.py
```

Optional variables of chain.sh: `STEPS="B T I P"`, `REPS=4`, `CELLS="glm-tp4 l8b-tp4-cpu"`. Done runs are skipped.
Marker: `exec/results/pr5022-optb-20261124/chain.done`. Log: `exec/logs/pr5022-optb-20261124-chain.log`.

## Measured costs

- Both builds in parallel with `-j22` each: 751 s and 764 s. The Glimmer trace was copied from
  `/var/tmp/jhan/seed-traces/b47f`.
- One run takes 13 to 87 s of wall time (22 runs, none failed or refused), plus about 12 s for the load snapshot.
- Each build tree holds 13 GB. Both trees stay on delphi-3b35 after the test.

## Results

See `exec/results/pr5022-optb-20261124/`: `build-*.txt`, `build-b.diff`, `tests.txt`, `identity.txt`, `tokens/`,
`rt-results.txt`, `rt/`, `load/`, `summary.json`.

Not covered: option A (the default-constructed `s_pages` with its zero fill) was not an arm, so the cost of the
fill is not measured here. One prompt length (1024 tokens) ran.
