---
name: more-testing-round1
description: "DONE 2026-09-05: round-1 campaign running the nightly System CI tests (systems_test: functional, perf, MMLU Pro, soak) against rinzler built from PR3879 head 60d66d9c04; results, how CI works, how to drive it standalone, traps"
metadata: 
  node_type: memory
  type: project
  originSessionId: fffbcfe8-4091-44ec-a261-0731127ed318
  modified: 2026-09-04T17:58:41.445Z
---

Request (jhan 2026-09-04, input-2-ai/more-testing.md): test the AMX change with
the same tests the nightly CI runs (MMLU Pro, soak, CI functional/perf) on 4
models (3 AMX-boosted + gpt-oss regression), CI's models/TP/users; plan +
status md in PR3879/more-testing/ (round-1/ subfolder), status refreshed per
model.

What the nightly CI is (verified from source + the 2026-09-04 run log):
- repo positron-ai/systems_test (clone ~/workspace/ai-runs/systems_test @470aca1),
  workflow system_ci_granite_rapids_72_rinzler_OCI.yaml, cron 03:30Z, ~7h40m,
  client on host system-ci-runner (NOT on 3bda), talks to platformd proxy port
  80 -> 4 tp2 / 2 tp4 engines. Installs tron deb from apt each night.
- phases: functional (pytest functional_tests/, 2 model groups, tp4) 17 min;
  perf (testlib/tps.benchmark_tps, prompt 1024/gen 1536, 10 rounds, 8 users for
  our 4 models) 70 min; MMLU Pro (MMLU_COVERAGE=10 = FIRST 10% of each subject,
  deterministic 1196 questions, 8 parallel, chat, temp 0, max_tokens 4096) 188
  min; soak 3 h (scripts/soak.py, 100 users, trio 3b/8b/70b tp2, ShareGPT-like
  prompt groups, coherency probe every 30 s, DUT monitor over ssh+platformd).
- CI ref numbers extracted by exec/more-testing-r1/ci_reference.py into
  exec/results/more-testing-r1/ci-reference-20260904.json (MMLU: 8b-good 44.82,
  mixtral 43.81, qwen-3-4b-tp4 66.97, gpt-oss-120b-tp4 76.67; perf TPS 139.65 /
  79.59 / 148.3 / 93.93).

Standalone driving (all in exec/more-testing-r1/): talos (CI results DB) is
replaced by a no-op stub on PYTHONPATH (talos_stub/talos.py) so nothing is
written to the CI database; MMLU via scripts/mmlu_cli.py main_chat with
SKIP_PROVISION=1 (same prompts/params as attached runner); perf via st_perf.py
(imports scripts.perf configs + testlib.tps); functional = pytest with the two
proxy auth tests --deselect'ed (no proxy in front of bare rinzler); soak =
python -m scripts.soak with NUM_USERS, MAX_DURATION (minutes), SSH_USER=jhan
SSH_PASS= (key auth; never use the CI account password).

Traps hit:
- fusermount3: do NOT put /opt/positron/bin first on PATH for our rinzler; that
  fusermount3 wants /usr/local/etc/fuse.conf and refuses allow_other -> rinzler
  aborts. /usr/bin/fusermount3 honours /etc/fuse.conf user_allow_other.
- rinzler as an interactive user caps hugepages by memlock ulimit (188 of 256);
  fix: sudo -n prlimit --pid $$ --memlock=unlimited before launching.
- USE_HW_ATTN unset => ingested models (qwen, gpt-oss) use FPGA attention and
  AMX never engages; set USE_HW_ATTN=0 in every arm.
- ci-runner-stop timer at 02:45Z brings production inference up: campaign must
  end by ~02:30Z (deadline logic in exec/more-testing-r1.sh).
- NEVER edit run_cell.sh (or any bash script) while a cell is executing it:
  bash reads the file incrementally from NFS; an in-place edit shifted the
  offsets and the running instance died with "syntax error: unexpected end of
  file" at the very end (qwen mirror cell, 20:03Z; data intact, bookkeeping
  repaired by hand). Edit copies for the next round, or only between campaigns.
- rinzler journal SYSTEM_STATS lines match the "session|token" traffic grep;
  exclude '#EVT#' lines when deciding serving is idle.

RESULTS (round 1, 17:56-01:39Z, all cells done; PR3879/more-testing/round-1/status.md
+ results.html, raw exec/results/more-testing-r1/):
- functional: identical pass/skip in every arm (qwen/llama/mixtral 25/2, gpt-oss 23/4).
- decode TPS at 8 users, 1 engine: llama-8b-good +13.9% canon / +18.9% mirror; qwen
  +4.5/+5.5%; mixtral -0.2/+0.2%; gpt-oss +2.0/+3.6% (noise; sd 1.4-1.9). A/A repeat
  of qwen off differed -2.2% -> <2% not resolved by one run per arm.
- TTFT: canon -4..-9% vs off; MIRROR SLOWER on qwen (+24% vs canon) and llama (+17%),
  every round, TTFT reproduces to 0.2% between identical runs; none on mixtral/gpt-oss.
  Open finding -> round 2 prefill measurement (arena write-through suspected).
- MMLU Pro (first 10% = 1196 fixed questions): deltas vs off qwen +1.51/+1.34, llama
  +0.67, mixtral -0.37, gpt-oss -0.29 points; A/A repeat of qwen off = +1.67 points (runner total 811 vs 791) with
  195/1196 answers changed and only 6.5% byte-identical responses; gpt-oss (no AMX code)
  off-vs-mirror churns 10% of answers -> churn is serving-path nondeterminism (batching
  order), AMX arms indistinguishable from a rerun. Verdict: no detectable accuracy change.
- soak 60 min mirror (llama-8b + qwen tp2, 25 users): 0 failed requests, 109 coherency
  probes 0 failures, but host RAM grew ~40 GiB (0.84-0.92 of the K mirror arena footprint
  in GiB; arena = half of KV bytes, peak 46.5 GB; moves 36-42 GiB once KV is full) -> CI
  soak monitor's 5 GiB growth alert fires; off-arm 20-min soak grew -0.2 GiB. Operational
  property of mirror, not a leak; needs a decision. gpt-oss mirror TPS +3.6% is outside
  the +/-3% band and unresolved (no gpt-oss repeat).
- Report tooling: exec/more-testing-r1/{gen_status.py,gen_results_html.py,resultlib.py,
  mmlu_diff.py,ci_reference.py}; two MMLU scoring rules exist (runner total credits a
  seeded random guess for unextractable letters; mmlu_diff compares extracted letters and
  drops questions one run left unanswered) - always say which one a number uses.

**Why:** these took a full afternoon to establish and are not written in either repo.
**How to apply:** for round 2, reuse exec/more-testing-r1.sh + helpers; compare
against round-1 status.md and ci-reference json. Related:
[[amx-tron-softattn-project]], [[delphi-3bda-hardware]], [[perf-round-20260830]].
