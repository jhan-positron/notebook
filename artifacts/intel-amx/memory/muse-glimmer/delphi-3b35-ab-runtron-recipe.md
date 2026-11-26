---
name: delphi-3b35-ab-runtron-recipe
description: "Working recipe and measured costs for an A/B runtron test of a tron source change on delphi-3b35 (two builds, unit tests, token identity, throughput): folder exec/pr5022-optb-20261124, 31 minutes in total on 2026-11-25"
metadata:
  node_type: memory
  type: reference
  originSessionId: e6131298-3716-420b-b25d-23483ce37d5a
  modified: 2026-11-25T01:09:03.267Z
---

Used on 2026-11-25 (UTC) for tron PR 5022, when jhan asked for "a A/B test on 3b35: with and without the change ... Use Muse Glimmer model and an unrelated model".

Folder: `~/workspace/intel-AMX/exec/pr5022-optb-20261124/` (README.md there). Results: `exec/results/pr5022-optb-20261124/`. Report page: `muse-glimmer/pr5022-optb-ab.html`.

What works on delphi-3b35 without root:
- `chain.sh` runs detached (`setsid nohup`): two builds in parallel with `-j22` each on CPUs 96-143, then unit tests, identity runs and throughput runs.
- A registry file with only the models under test (`-DDEV_MODEL_CONFIG=`) keeps the build at 751 to 764 s for runtron with the Glimmer and llama plugins.
- The Glimmer trace is copied from `/var/tmp/jhan/seed-traces/b47f`. Model weights are in `/opt/positron/weights/huggingface/_promoted/`.
- Slugs that worked with `SYSTEM_CONFIG="--instance 1,2"`: `ingested-meta-models--Muse-Glimmer-30B-tp4` and `llama-3.1-8b-instruct-good-tp4` (with `USE_HW_ATTN=0` for CPU attention).
- `run-one.sh` (copy of `exec/gdn-20261120/run-one.sh`) takes the load snapshot, refuses a run when our cards are open or our CPUs are over 5% busy, and removes its huge page files.
- One run takes 13 to 87 s. The whole chain took 31 minutes (4 repetitions per arm, 2 models).
- `collect.py` applies the band rule of `exec/glimext-20261018/gen_report.py` (band = twice the larger standard deviation of the two arms).

Traps met:
- An ssh command that prints the environment or the setup script was denied by the permission classifier. Do not read env variables or `~/delphi-3b35-setup.sh` over ssh.
- `pgrep -f <pattern>` inside an ssh command matches the ssh shell itself. Use a bracket in the pattern (`chain[.]sh`) or `pgrep -x runtron`.
- The agent machine has no `node`, no browser and no PyYAML: the dataviz palette validator and a page preview cannot run there.
- Each build tree holds 13 GB under `/var/tmp/jhan/b35-optb-{a,b}`. They were left in place.

Related: [[delphi-3b35-no-slice-bench]], [[delphi-3bda-lost-no-comparable-reruns]], [[changes-need-system-tests]].
