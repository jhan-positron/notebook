# Test plan: AMX change (PR3879) under the nightly System CI tests

Written 2026-09-04 (round 1). Author: Claude, for jhan. Source request:
`input-2-ai/more-testing.md`.

## Short version

The nightly CI for delphi-3bda is the `systems_test` repository's `system_ci`
driver: it runs functional API tests, a throughput benchmark, MMLU Pro (an
accuracy test), and a 3-hour soak (sustained-traffic stability test) against
the production server rinzler. Round 1 runs those same four tests against
rinzler built from the PR3879 branch on four models (qwen-3-4b, llama-3.1-8b,
mixtral-8x7b, gpt-oss-120b) in three arms: AMX off, AMX canonical, AMX mirror.
Results land in `PR3879/more-testing/round-1/status.md` and are refreshed after
every model.

## Words used here

- **tron**: the inference engine under test. **rinzler**: tron's production
  HTTP server (OpenAI-compatible API). **runtron**: tron's command-line tool
  (used by our earlier campaigns; not used in this round).
- **PR3879 / jhan-amx-p0**: the branch with the AMX change, head `60d66d9c04`.
- **AMX**: Intel Advanced Matrix Extensions, the CPU tile-matrix instructions
  the change uses for software attention. **AVX**: the older vector
  instructions the existing code uses.
- **Arms** (the builds and switches compared):
  - **off**: canonical build run with `TRON_AMX_DISABLE=1` (the kill switch);
    attention runs on the AVX path. This is the within-round baseline.
  - **canon** (canonical): `TRON_AMX_DISPATCH=ON`, `TRON_AMX_K_MIRROR=OFF`.
    AMX kernels read the normal K layout.
  - **mirror**: `TRON_AMX_DISPATCH=ON`, `TRON_AMX_K_MIRROR=ON`. AMX kernels
    read a second, AMX-friendly copy of K kept in ordinary RAM (the "mirror
    arena"). Naming per the project convention: "mirror" is our
    implementation of the formulation from Bill's PR.
- **USE_HW_ATTN=0**: environment switch that forces attention onto the CPU
  ("software attention") for every model. Without it, ingested models
  (qwen, gpt-oss) run attention on the FPGA and AMX never engages
  (`h/tron/models/hw_attn_config.hpp`, `ingest/src/TronCpp.hs:233`).
- **tp2 / tp4**: tensor parallelism, the number of FPGA cards one model
  instance spans.
- **systems_test**: repository `positron-ai/systems_test` (checkout
  `470aca1`, 2026-08-28). Its `system_ci` driver is what the nightly runs.
- **MMLU Pro**: multiple-choice knowledge test (dataset `TIGER-Lab/MMLU-Pro`,
  12032 questions in 14 subjects). The model answers with chain-of-thought
  and must end with "the answer is (X)". Score = percent correct.
  **MMLU_COVERAGE=10** means the first 10% of each subject's questions, a
  fixed set of 1196 questions (not a random sample; verified in
  `scripts/mmlu_pro.py:378` and `scripts/mmlu_cli.py`).
- **Soak**: `scripts/soak.py`, N simulated users send chat requests from the
  ShareGPT prompt set for a fixed duration while a monitor records errors,
  host memory growth, power, and a "coherency" probe (embedding similarity of
  a fixed prompt's answer to known-good answers).
- **Perf**: `testlib/tps.py benchmark_tps`, N users each send 10 rounds of a
  1024-token ShareGPT prompt and read 1536 generated tokens; reports **TPS**
  (per-user decode tokens per second, averaged over rounds) and **TTFT**
  (time to first token, milliseconds).
- **Functional**: `functional_tests/test_api.py` under pytest: API shape,
  streaming, stop tokens, golden-response similarity, concurrency, for every
  model the server advertises.
- **CI reference**: the nightly run of 2026-09-04 (GitHub Actions run
  33833914529, tron package 2026.09.04-fe8dbdee, main branch). Its numbers
  are extracted by `exec/more-testing-r1/ci_reference.py` into
  `exec/results/more-testing-r1/ci-reference-20260904.json`.

## 1. What the nightly CI does (measured from the 2026-09-04 run)

| Phase | What runs | Models on delphi-3bda | Users | Duration |
|---|---|---|---|---|
| Functional | pytest `functional_tests/` | set 1: llama-3.2-3b-fast, llama-3.1-8b-good, llama-3.3-70b-good, mixtral-8x7b, gemma-2-9b, qwen-2.5-32b (all tp4); set 2: gpt-oss-120b-tp4, qwen-3-4b-tp4 | n/a | 16.7 min (150+48 passed, 2+4 skipped) |
| Perf | `benchmark_tps`, prompt 1024, generate 1536, 10 rounds | 3b-tp2 (32 users, prompt 200 + 800 shared), 8b-good-tp2, 70b-tp2, 70b-tp4, mixtral-tp2, qwen-2.5-32b-tp2, qwen-3-4b-tp2, qwen-3-4b-tp4, gemma-tp2, gpt-oss-120b-tp4 | 8 (4 for 70b) | 70.5 min |
| MMLU Pro | coverage 10% = 1196 questions, 8 parallel requests, max_tokens 4096, temperature 0 | 3b-tp2, 8b-good-tp2, 70b-tp2, 70b-tp4, mixtral-tp2, qwen-2.5-32b-tp2, qwen-3-4b-tp4, gemma-tp2, gpt-oss-120b-tp4 | 8 | 188 min |
| Soak | `soak.py`, ShareGPT traffic | llama-3.1-8b-good-tp2 + llama-3.2-3b-fast-tp2 + llama-3.3-70b-good-tp2 served together | 100 | 3 h, 0 errors |

The CI runs its client on a separate machine (`system-ci-runner`) and talks
to the DUT through platformd's proxy on port 80, which spreads requests over
4 engines (tp2) or 2 engines (tp4). Attention for ingested models
(qwen-3-4b, gpt-oss-120b) runs on the FPGA in CI; the hand-written llama and
mixtral models run software attention.

## 2. Round-1 selection

**Models and tensor parallelism (CI's choices):**

| Model id (as served) | Why | AMX eligible? | CI phases with this id |
|---|---|---|---|
| ingested-qwen-3-4b-instruct-2507-tp4 | AMX-boosted model 1 | yes (head 128, 4 query heads per KV head) | functional, perf, MMLU |
| llama-3.1-8b-instruct-good-tp2 | AMX-boosted model 2 (CI's GPTQ variant; same geometry as the ingested llama used before) | yes | perf, MMLU, soak |
| mixtral-8x7b-instruct-v0.1-tp2 | AMX-boosted model 3 | yes | perf, MMLU |
| ingested-gpt-oss-120b-tp4 | regression check (AMX never runs: head 64, 8 query heads per KV head) | no | functional, perf, MMLU |

**Users:** perf at 8 users (CI's `nominal_users` for all four); MMLU at 8
parallel requests (CI's value); soak at 25 users (CI uses 100 across 4
engines; we run 1 engine).

**Arms per model:** off, canon, mirror. All arms run with `USE_HW_ATTN=0`
so the attention engine is the same in every arm and AMX can engage.

**Tests per cell (model x arm):** functional -> perf -> MMLU Pro, on one
rinzler process started for that cell. MMLU (the long test) runs on: all
three arms for qwen (the primary model); off and mirror for llama, mixtral,
gpt-oss (canon and mirror share the same AMX kernels for QK/PV; for gpt-oss
neither arm runs AMX, so mirror alone covers the regression question).

**Soak:** one 60-minute run on the mirror arm serving
llama-3.1-8b-instruct-good-tp2 and ingested-qwen-3-4b-instruct-2507-tp2
together (two AMX-eligible models on one engine, like CI's multi-model
engine), 25 users, ShareGPT prompts, coherency probe on.

**Order and time budget** (machine free from 17:33Z; must end by 02:30Z
because the `ci-runner-stop` timer brings production inference back at
02:45Z and CI prep starts 03:30Z):

1. qwen-3-4b-tp4: off, canon, mirror (each with MMLU) - about 2 h 15 min
2. llama-3.1-8b-tp2: off (MMLU), canon, mirror (MMLU) - about 1 h 20 min
3. soak 60 min (mirror) - about 1 h 15 min
4. mixtral-8x7b-tp2: off (MMLU), canon, mirror (MMLU) - about 1 h 10 min
5. gpt-oss-120b-tp4: off (MMLU), canon, mirror (MMLU) - about 1 h 20 min

Estimated end about 01:30Z. The campaign script refuses to start a cell whose
estimate would cross 02:30Z and records it as skipped; the status file says
which cells did not run.

**Added during the run (19:40Z):** the first canon-vs-off MMLU comparison
showed that 94% of the chain-of-thought responses differ between the two arms
even though the score moved only 1.5 points. To tell AMX-induced divergence
from run-to-run noise of one arm (8 parallel requests are batched in varying
order), an A/A control is queued after the planned cells: the qwen-3-4b off
arm repeated with the same binary and switches (`exec/more-testing-r1-extra.sh`,
runs only if the deadline allows). The per-question comparison tool is
`exec/more-testing-r1/mmlu_diff.py`; its output is in the status report.

**Added during the run (22:20Z):** the mirror-arm soak tripped the CI
monitor's host-memory-growth alert (5 GiB threshold) because the K mirror
arena fills from ordinary RAM as the KV cache fills (about 40 GiB here, then
flat). A 20-minute off-arm soak with the same models and users is queued after
the A/A control (`exec/more-testing-r1-extra2.sh`) as the no-arena memory
baseline; it also runs only if the deadline allows.

## 3. How the tests are driven (and where this differs from CI)

- rinzler is `gen/rinzler.canon` / `gen/rinzler.mirror` built from
  `~/workspace/tron-amx` at `60d66d9c04` (build log
  `exec/logs/more-testing-r1-build.log`). It is started with the same
  system arguments platformd gives production engines on this machine
  (tp2: `--instance 0,4`, cards 10:00.0+13:00.0, 128 hugepages; tp4:
  `--instance 0,2`, cards 38:00.0+3b:00.0+10:00.0+13:00.0, 256 hugepages;
  same core lists), on port 13100, without platformd.
- The systems_test client runs on delphi-3bda itself (venv
  `/var/tmp/jhan/st-venv`, Python 3.12, `uv sync` of the lock file).
  Difference from CI: no network hop and no platformd proxy; one engine
  instead of 2 or 4. Perf numbers are therefore not directly comparable to
  CI's; the within-round arm-to-arm comparison is the controlled one.
- MMLU uses the repository's detached runner (`scripts/mmlu_cli.py`,
  `main_chat` with `SKIP_PROVISION=1`), which sends the same prompts and
  sampling settings as the attached runner CI uses, without platformd.
- Perf and soak use the repository code (`testlib/tps.py`, `scripts/soak.py`)
  with the talos reporting library replaced by a no-op stub, so nothing is
  written to the CI results database or Slack.
- The soak monitor logs into the DUT as jhan (key auth) instead of the CI
  service account.
- The two functional tests that check the proxy's token rejection
  (`test_auth_reject_no_token`, `test_auth_reject_bad_token`) are deselected:
  they test platformd's proxy, which is not in front of our rinzler. CI itself
  deselects them for every model group after the first.
- Perf tokenizers are loaded from the DUT's local copies of the same
  Hugging Face repositories (identical files) instead of the hub.
- Production serving was stopped per the standing rinzler policy (nightly
  finished 11:18Z, zero client connections and zero request lines in the
  journal); nothing restarts it (the 02:45Z timer does).

## 4. Pass criteria (decided before running)

- **Functional:** every arm passes the same tests CI passes for that model
  (0 failures; skips must match CI's skip reasons).
- **MMLU Pro:** overall score difference between an AMX arm and the off arm
  within 1.0 point = parity (one question is 0.084 points of 1196; both arms
  answer the identical question set). 1.0 to 2.0 points = investigate
  (re-run the subjects that moved). More than 2.0 points = fail.
  Difference to the CI reference is reported but is not a pass/fail signal
  (different binary, attention engine for ingested models, and engine count).
- **Perf:** AMX arms must not be slower than the off arm by more than 2% TPS
  (measurement spread seen in earlier rounds); gains are expected to be
  small at this prompt length (1024 + up to 1536 generated tokens) because
  attention is a modest share of decode there. gpt-oss-120b must be within
  +/-3% of off.
- **Soak:** 0 failed requests (excluding the tolerated harmony parse errors
  for gpt-oss, which is not in the soak set), used-memory growth under
  1 GiB over the hour, no coherency-probe failures, no rinzler crash.

## 5. Outputs

- `PR3879/more-testing/round-1/status.md`: status report, regenerated by
  `exec/more-testing-r1/gen_status.py` after every cell.
- `exec/results/more-testing-r1/cells/<model>__<arm>/`: raw outputs per cell
  (`functional.xml`, `functional.log`, `perf.json`, `perf.log`,
  `mmlu.log`, `eval_results/`, `rinzler.log`, `meta.json`).
- `exec/results/more-testing-r1/soak/`: soak log and monitor data.
- `exec/results/more-testing-r1/ci-reference-20260904.json`: CI reference.
- Scripts: `exec/more-testing-r1-build.sh` (stage 1), `exec/more-testing-r1.sh`
  (campaign), helpers in `exec/more-testing-r1/`.

## 6. Left for later rounds

- Multi-engine serving behind a proxy (4 x tp2 / 2 x tp4) so perf and soak
  match CI's load distribution.
- Full 3-hour soak and 100 users.
- The AMX arms with the FPGA attention default (USE_HW_ATTN unset), to show
  the change is inert when attention is not on the CPU.
- llama-3.1-8b-instruct-good at tp4 (CI's functional-test shape).
