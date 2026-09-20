# Status report: AMX change (PR3879) under the nightly System CI tests, round 1

Generated 2026-09-05 02:13 UTC by `exec/more-testing-r1/gen_status.py`. Test plan: `../test-plan.md`. Raw data: `exec/results/more-testing-r1/`. Chart page with the same data: `results.html`.

## Short version

12 of 12 model-and-arm combinations (cells) and the 60-minute soak finished. Every functional API test passed in every arm, decode throughput rose by 14 to 19% on llama-3.1-8b and 4.5 to 5.5% on qwen-3-4b with AMX on, and MMLU Pro accuracy moved by -0.4 to +1.5 points, which is inside the +1.7 points seen when the off arm was run a second time unchanged, so no accuracy change is detectable. Two findings need follow-up: the mirror arm is 13% slower to first token than off on qwen and llama, and its K mirror arena grows host RAM by about half the KV cache size (about 40 GiB in the soak), which the CI soak monitor reports as an error.

## Words used here

- **tron, rinzler, runtron**: tron is the inference program under test; rinzler is its production HTTP server, which every cell here runs; runtron is tron's command-line tool used by the earlier decode-only rounds.
- **AMX, AVX**: AMX = Intel Advanced Matrix Extensions, CPU matrix instructions the change uses for attention; AVX = the older vector instructions the existing code uses.
- **K, V, KV cache, KV head, head size**: for every served token the server stores the attention keys (K) and values (V); this store is the KV cache, kept in hugepages (2 MB or 1 GB memory pages reserved for it). A KV head is one stored key/value stream shared by several query heads; head size is the vector width of one attention head. The change's kernels (small compute routines) exist only for head size 128 with 4 query heads per KV head (qwen, llama, mixtral); gpt-oss (head size 64, 8 query heads per KV head) never runs them.
- **off, canon, mirror (the arms)**: off = the canonical build (rinzler.canon) started with TRON_AMX_DISABLE=1, the kill switch, so attention runs on the AVX path; canon = the same binary with the switch unset, AMX kernels read the normal K layout; mirror = a second build (rinzler.mirror) that also keeps an AMX-friendly copy of K in ordinary RAM, the K mirror arena. The kill-switch state is recorded by the launcher (rz.sh, meta.json); rinzler itself does not log it.
- **USE_HW_ATTN=0**: environment switch that forces attention onto the CPU for every model; without it the ingested models (qwen, gpt-oss) run attention on the FPGA (the accelerator cards) and AMX never engages. Set in every arm; the server log line 'HW attention disabled' confirms it per cell.
- **tp2, tp4**: tensor parallelism, the number of FPGA cards one model instance spans; CI's choice per model was kept.
- **functional**: the CI pytest suite functional_tests/test_api.py: API shape, streaming, stop tokens, golden-response similarity, concurrency; counts are passed/skipped/failed.
- **perf, TPS, TTFT, sd**: the CI throughput benchmark: 8 users each send 10 rounds of a 1024-token prompt and read 1536 generated tokens. TPS = tokens per second per user during generation (decode); TTFT = time to first token in milliseconds (mostly the prompt processing, prefill, with 8 requests arriving together); sd = standard deviation of the 80 per-user-per-round TPS samples inside one run (round-to-round drift within one server process, not between-run spread).
- **MMLU Pro**: multiple-choice knowledge test; CI's setting is the first 10% of every subject, a fixed set of 1196 questions, answered with chain-of-thought (the model writes its reasoning before the final letter) under greedy decoding (always the highest-scoring token) at temperature 0, 8 questions in flight at a time. Score = percent correct as computed by the CI runner, which scores a response with no extractable letter by a seeded random guess and drops a question whose response was empty.
- **answer changes, A/A control**: per-question comparison of two runs: the final letters actually extracted are compared, so a question one run left unanswered is dropped and a random-guess credit is not counted; the net column can therefore differ from the score difference by a few questions. A/A control = the same binary with the same switches run a second time, which measures the run-to-run spread of the serving path (8 requests are batched in changing order and the floating-point reduction order follows).
- **soak, coherency probe, harness**: sustained mixed traffic from 25 simulated users for a fixed time while the CI monitor records failed requests, host used memory (whole host, hugepages excluded), power, and a coherency probe (a fixed prompt sent every 30 s, its answer compared with known-good answers). Harness = the soak.py driver; its error count includes monitor alerts.
- **CI reference**: the nightly run of 2026-09-04 (GitHub Actions run 33833914529, tron package 2026.09.04-fe8dbdee, main branch). Its client ran on another host through the platformd proxy over 2 to 4 engines; ours ran on the test machine against one engine, so CI throughput and TTFT are not directly comparable and are shown for orientation only.

## Per-model summary

- **qwen-3-4b (tp4)** (AMX-eligible): canon: functional 25 passed / 0 failed, TPS +4.5% vs off, TTFT -8.9% vs off, MMLU Pro 67.64% vs off 66.14% (+1.51 points); mirror: functional 25 passed / 0 failed, TPS +5.5% vs off, TTFT +13.1% vs off, MMLU Pro 67.47% vs off 66.14% (+1.34 points).
- **llama-3.1-8b-good (tp2)** (AMX-eligible): canon: functional 25 passed / 0 failed, TPS +13.9% vs off, TTFT -3.6% vs off; mirror: functional 25 passed / 0 failed, TPS +18.9% vs off, TTFT +13.1% vs off, MMLU Pro 45.07% vs off 44.40% (+0.67 points).
- **mixtral-8x7b (tp2)** (AMX-eligible): canon: functional 25 passed / 0 failed, TPS -0.2% vs off, TTFT +0.2% vs off; mirror: functional 25 passed / 0 failed, TPS +0.2% vs off, TTFT +0.7% vs off, MMLU Pro 41.64% vs off 42.01% (-0.37 points).
- **gpt-oss-120b (tp4)** (not eligible (regression check)): canon: functional 23 passed / 0 failed, TPS +2.0% vs off, TTFT -0.2% vs off; mirror: functional 23 passed / 0 failed, TPS +3.6% vs off, TTFT -0.2% vs off, MMLU Pro 76.60% vs off 76.88% (-0.29 points).

## Build and machine facts

- tron source tree `~/workspace/tron-amx` at `60d66d9c04`, the PR3879 head. rinzler binaries were built 2026-09-04 17:33-17:46 UTC (`exec/logs/more-testing-r1-build.log`): canon sha256 `0b5fe23f...`, mirror sha256 `fc32cabe...`, version 2026.09.04-60d66d9c-jhan-amx-p0.
- Test machine delphi-3bda (2-socket Xeon 6, 8 FPGA cards). Production rinzler serving was stopped 17:33 UTC per the standing policy (idle: zero client connections, zero request lines). One rinzler process per cell on port 13100 with production's per-instance card, core, and hugepage arguments (tp2: 2 cards, 128 hugepages; tp4: 4 cards, 256 hugepages); `USE_HW_ATTN=0` in every arm.
- Client: systems_test `470aca1` (the CI repository) in `/var/tmp/jhan/st-venv` on delphi-3bda itself; its CI reporting library was replaced by a no-op stub so nothing was written to the CI database.
- CI's functional phase ran six models at tp4 in one group (150 passed, 2 skipped) and gpt-oss-120b + qwen-3-4b at tp4 in a second group (48 passed, 4 skipped); it reports group totals only and did not run the llama and mixtral tp2 ids through the functional tests (their tp4 variants were in the first group). The two proxy-authentication tests (`test_auth_reject_no_token`, `test_auth_reject_bad_token`) skip themselves when the Server header starts with `drogon/` (rinzler's own HTTP server); they were skipped in our cells and, by its pytest progress output, in both CI groups as well, so the skip counts match.

## Results per model

### qwen-3-4b (tp4): `ingested-qwen-3-4b-instruct-2507-tp4` (AMX-eligible)

| Arm | Status | Functional passed/skipped/failed | TPS mean (sd) [tok/s per user] | TPS vs off | TTFT [ms] | TTFT vs off | MMLU Pro [%] | MMLU vs off [points] | Phase durations [min]: start / functional / perf / MMLU |
|---|---|---|---|---|---|---|---|---|---|
| CI reference (main, 2-4 engines) | 2026-09-04 | group totals only | 148.30 | n/a | 638 | n/a | 66.97 | n/a | perf 1.96, MMLU 23.83 |
| off | done | 25/2/0 | 77.83 (0.64) | baseline | 1777 | baseline | 66.14 | baseline | 0.9 / 1.1 / 3.7 / 38.4 |
| canon | done | 25/2/0 | 81.37 (0.77) | +4.5% | 1618 | -8.9% | 67.64 | +1.51 | 0.9 / 1.0 / 3.5 / 36.0 |
| mirror | done | 25/2/0 | 82.11 (1.16) | +5.5% | 2009 | +13.1% | 67.47 | +1.34 | 0.9 / 1.1 / 3.5 / 35.3 |
| off (repeat rep2, A/A control) | done | 25/2/0 | 76.12 (0.83) | -2.2% | 1781 | +0.2% | 67.81 | +1.67 | 0.9 / 1.1 / 3.7 / 38.7 |

MMLU Pro question accounting per arm, of the 1196 asked: off: 1196 answered, 0 excluded (empty completion), 3 scored by random guess (no extractable letter); canon: 1196 answered, 0 excluded (empty completion), 5 scored by random guess (no extractable letter); mirror: 1196 answered, 0 excluded (empty completion), 2 scored by random guess (no extractable letter); off (repeat rep2, A/A control): 1196 answered, 0 excluded (empty completion), 4 scored by random guess (no extractable letter).

MMLU Pro answer changes relative to the off arm. Both runs were asked the same 1196 questions; a question one run left unanswered is dropped from the comparison (compared count below), and the letters actually extracted are compared, so the net column can differ from the score difference by a few random-guess credits. A changed answer means the reasoning text diverged and ended on another letter.

| Compared with off | Questions compared | Responses byte-identical | Final answer changed | right -> wrong | wrong -> right | wrong -> other wrong | Net [questions] |
|---|---|---|---|---|---|---|---|
| canon | 1196 | 72 (6.0%) | 186 (15.6%) | 40 | 58 | 88 | +18 |
| mirror | 1196 | 78 (6.5%) | 187 (15.6%) | 46 | 62 | 79 | +16 |
| off (repeat rep2, A/A control) | 1196 | 78 (6.5%) | 195 (16.3%) | 44 | 63 | 88 | +19 |

MMLU Pro per subject, percent correct (question counts asked per subject: biology 71, business 78, chemistry 113, computer science 41, economics 84, engineering 96, health 81, history 38, law 110, math 135, philosophy 49, physics 129, psychology 79, other 92; an excluded question lowers a subject's count by one):

| Arm | overall | biology | business | chemistry | computer science | economics | engineering | health | history | law | math | philosophy | physics | psychology | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CI reference | 66.97 | 83.10 | 71.79 | 74.34 | 85.37 | 67.86 | 54.17 | 61.73 | 50.00 | 40.91 | 91.11 | 53.06 | 77.52 | 65.82 | 46.74 |
| off | 66.14 | 85.92 | 70.51 | 70.80 | 82.93 | 69.05 | 46.88 | 60.49 | 52.63 | 38.18 | 88.89 | 59.18 | 79.07 | 67.09 | 46.74 |
| canon | 67.64 | 83.10 | 75.64 | 72.57 | 82.93 | 70.24 | 57.29 | 64.20 | 47.37 | 38.18 | 90.37 | 59.18 | 77.52 | 70.89 | 45.65 |
| mirror | 67.47 | 84.51 | 71.79 | 75.22 | 80.49 | 67.86 | 55.21 | 62.96 | 52.63 | 40.00 | 88.89 | 59.18 | 78.29 | 68.35 | 47.83 |
| off (repeat rep2, A/A control) | 67.81 | 84.51 | 71.79 | 77.88 | 82.93 | 70.24 | 56.25 | 59.26 | 42.11 | 40.00 | 91.11 | 59.18 | 76.74 | 65.82 | 53.26 |

Server log evidence. Two facts are read from each cell's rinzler.log: 'HW attention disabled' shows attention ran on the CPU in that arm, and a non-zero 'K mirror' size shows the mirror arena was allocated (zero in the off and canon arms, and always zero for gpt-oss). The footprint line is printed at start-up and again as the KV cache grows, so the early copies quoted here are small; the notes quote the end-of-run values.

- off: HW attention disabled for model 'ingested-qwen-3-4b-instruct-2507-tp4': USE_HW_ATTN=0 / KV cache footprint: 1.01 GB DMA + 0.00 GB K mirror in 10 books / KV cache footprint: 2.02 GB DMA + 0.00 GB K mirror in 30 books
- canon: HW attention disabled for model 'ingested-qwen-3-4b-instruct-2507-tp4': USE_HW_ATTN=0 / KV cache footprint: 1.01 GB DMA + 0.00 GB K mirror in 10 books / KV cache footprint: 2.16 GB DMA + 0.00 GB K mirror in 29 books
- mirror: HW attention disabled for model 'ingested-qwen-3-4b-instruct-2507-tp4': USE_HW_ATTN=0 / KV cache footprint: 0.88 GB DMA + 0.44 GB K mirror in 4 books / KV cache footprint: 1.64 GB DMA + 0.82 GB K mirror in 20 books

### llama-3.1-8b-good (tp2): `llama-3.1-8b-instruct-good-tp2` (AMX-eligible)

| Arm | Status | Functional passed/skipped/failed | TPS mean (sd) [tok/s per user] | TPS vs off | TTFT [ms] | TTFT vs off | MMLU Pro [%] | MMLU vs off [points] | Phase durations [min]: start / functional / perf / MMLU |
|---|---|---|---|---|---|---|---|---|---|
| CI reference (main, 2-4 engines) | 2026-09-04 | group totals only | 139.65 | n/a | 671 | n/a | 44.82 | n/a | perf 2.07, MMLU 13.59 |
| off | done | 25/2/0 | 76.07 (0.25) | baseline | 2784 | baseline | 44.40 | baseline | 0.5 / 1.1 / 3.8 / 25.5 |
| canon | done | 25/2/0 | 86.66 (0.23) | +13.9% | 2683 | -3.6% | not planned | n/a | 0.5 / 1.1 / 3.5 / - |
| mirror | done | 25/2/0 | 90.44 (0.21) | +18.9% | 3148 | +13.1% | 45.07 | +0.67 | 0.5 / 1.1 / 3.4 / 20.3 |

MMLU Pro question accounting per arm, of the 1196 asked: off: 1196 answered, 0 excluded (empty completion), 79 scored by random guess (no extractable letter); mirror: 1196 answered, 0 excluded (empty completion), 81 scored by random guess (no extractable letter).

MMLU Pro answer changes relative to the off arm. Both runs were asked the same 1196 questions; a question one run left unanswered is dropped from the comparison (compared count below), and the letters actually extracted are compared, so the net column can differ from the score difference by a few random-guess credits. A changed answer means the reasoning text diverged and ended on another letter.

| Compared with off | Questions compared | Responses byte-identical | Final answer changed | right -> wrong | wrong -> right | wrong -> other wrong | Net [questions] |
|---|---|---|---|---|---|---|---|
| mirror | 1196 | 543 (45.4%) | 223 (18.6%) | 50 | 57 | 116 | +7 |

MMLU Pro per subject, percent correct (question counts asked per subject: biology 71, business 78, chemistry 113, computer science 41, economics 84, engineering 96, health 81, history 38, law 110, math 135, philosophy 49, physics 129, psychology 79, other 92; an excluded question lowers a subject's count by one):

| Arm | overall | biology | business | chemistry | computer science | economics | engineering | health | history | law | math | philosophy | physics | psychology | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CI reference | 44.82 | 59.15 | 47.44 | 38.05 | 41.46 | 46.43 | 38.54 | 48.15 | 34.21 | 32.73 | 56.30 | 55.10 | 38.76 | 56.96 | 38.04 |
| off | 44.40 | 59.15 | 47.44 | 39.82 | 41.46 | 44.05 | 34.38 | 51.85 | 28.95 | 32.73 | 58.52 | 46.94 | 37.98 | 54.43 | 40.22 |
| mirror | 45.07 | 64.79 | 48.72 | 39.82 | 53.66 | 45.24 | 36.46 | 46.91 | 31.58 | 32.73 | 54.81 | 53.06 | 38.76 | 55.70 | 38.04 |

Server log evidence. Two facts are read from each cell's rinzler.log: 'HW attention disabled' shows attention ran on the CPU in that arm, and a non-zero 'K mirror' size shows the mirror arena was allocated (zero in the off and canon arms, and always zero for gpt-oss). The footprint line is printed at start-up and again as the KV cache grows, so the early copies quoted here are small; the notes quote the end-of-run values.

- off: HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': USE_HW_ATTN=0 / KV cache footprint: 1.01 GB DMA + 0.00 GB K mirror in 21 books / KV cache footprint: 2.02 GB DMA + 0.00 GB K mirror in 68 books
- canon: HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': USE_HW_ATTN=0 / KV cache footprint: 1.01 GB DMA + 0.00 GB K mirror in 21 books / KV cache footprint: 2.03 GB DMA + 0.00 GB K mirror in 68 books
- mirror: HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': USE_HW_ATTN=0 / KV cache footprint: 0.72 GB DMA + 0.36 GB K mirror in 8 books / KV cache footprint: 1.41 GB DMA + 0.71 GB K mirror in 37 books

### mixtral-8x7b (tp2): `mixtral-8x7b-instruct-v0.1-tp2` (AMX-eligible)

| Arm | Status | Functional passed/skipped/failed | TPS mean (sd) [tok/s per user] | TPS vs off | TTFT [ms] | TTFT vs off | MMLU Pro [%] | MMLU vs off [points] | Phase durations [min]: start / functional / perf / MMLU |
|---|---|---|---|---|---|---|---|---|---|
| CI reference (main, 2-4 engines) | 2026-09-04 | group totals only | 79.59 | n/a | 1260 | n/a | 43.81 | n/a | perf 3.56, MMLU 9.92 |
| off | done | 25/2/0 | 33.22 (0.17) | baseline | 5478 | baseline | 42.01 | baseline | 0.6 / 2.0 / 8.8 / 21.1 |
| canon | done | 25/2/0 | 33.14 (0.23) | -0.2% | 5491 | +0.2% | not planned | n/a | 0.6 / 2.0 / 8.8 / - |
| mirror | done | 25/2/0 | 33.28 (0.16) | +0.2% | 5514 | +0.7% | 41.64 | -0.37 | 0.6 / 1.9 / 8.8 / 21.2 |

MMLU Pro question accounting per arm, of the 1196 asked: off: 1195 answered, 1 excluded (empty completion), 18 scored by random guess (no extractable letter); mirror: 1196 answered, 0 excluded (empty completion), 26 scored by random guess (no extractable letter).

MMLU Pro answer changes relative to the off arm. Both runs were asked the same 1196 questions; a question one run left unanswered is dropped from the comparison (compared count below), and the letters actually extracted are compared, so the net column can differ from the score difference by a few random-guess credits. A changed answer means the reasoning text diverged and ended on another letter.

| Compared with off | Questions compared | Responses byte-identical | Final answer changed | right -> wrong | wrong -> right | wrong -> other wrong | Net [questions] |
|---|---|---|---|---|---|---|---|
| mirror | 1195 | 312 (26.1%) | 381 (31.9%) | 83 | 79 | 219 | -4 |

MMLU Pro per subject, percent correct (question counts asked per subject: biology 71, business 78, chemistry 113, computer science 41, economics 84, engineering 96, health 81, history 38, law 110, math 135, philosophy 49, physics 129, psychology 79, other 92; an excluded question lowers a subject's count by one):

| Arm | overall | biology | business | chemistry | computer science | economics | engineering | health | history | law | math | philosophy | physics | psychology | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CI reference | 43.81 | 61.97 | 44.87 | 36.28 | 43.90 | 45.24 | 34.38 | 49.38 | 44.74 | 26.36 | 55.56 | 38.78 | 37.21 | 59.49 | 43.48 |
| off | 42.01 | 54.93 | 44.87 | 42.48 | 41.46 | 47.62 | 22.92 | 50.62 | 39.47 | 31.82 | 43.70 | 39.58 | 35.66 | 56.96 | 44.57 |
| mirror | 41.64 | 54.93 | 37.18 | 35.40 | 48.78 | 50.00 | 23.96 | 46.91 | 36.84 | 31.82 | 45.19 | 42.86 | 39.53 | 59.49 | 41.30 |

Server log evidence. Two facts are read from each cell's rinzler.log: 'HW attention disabled' shows attention ran on the CPU in that arm, and a non-zero 'K mirror' size shows the mirror arena was allocated (zero in the off and canon arms, and always zero for gpt-oss). The footprint line is printed at start-up and again as the KV cache grows, so the early copies quoted here are small; the notes quote the end-of-run values.

- off: HW attention disabled for model 'mixtral-8x7b-instruct-v0.1-tp2': USE_HW_ATTN=0 / KV cache footprint: 1.00 GB DMA + 0.00 GB K mirror in 20 books / KV cache footprint: 2.01 GB DMA + 0.00 GB K mirror in 62 books
- canon: HW attention disabled for model 'mixtral-8x7b-instruct-v0.1-tp2': USE_HW_ATTN=0 / KV cache footprint: 1.02 GB DMA + 0.00 GB K mirror in 21 books / KV cache footprint: 2.07 GB DMA + 0.00 GB K mirror in 62 books
- mirror: HW attention disabled for model 'mixtral-8x7b-instruct-v0.1-tp2': USE_HW_ATTN=0 / KV cache footprint: 0.70 GB DMA + 0.35 GB K mirror in 7 books / KV cache footprint: 1.39 GB DMA + 0.70 GB K mirror in 34 books

### gpt-oss-120b (tp4): `ingested-gpt-oss-120b-tp4` (not eligible (regression check))

| Arm | Status | Functional passed/skipped/failed | TPS mean (sd) [tok/s per user] | TPS vs off | TTFT [ms] | TTFT vs off | MMLU Pro [%] | MMLU vs off [points] | Phase durations [min]: start / functional / perf / MMLU |
|---|---|---|---|---|---|---|---|---|---|
| CI reference (main, 2-4 engines) | 2026-09-04 | group totals only | 93.93 | n/a | 1160 | n/a | 76.67 | n/a | perf 3.06, MMLU 15.85 |
| off | done | 23/4/0 | 60.56 (1.41) | baseline | 2379 | baseline | 76.88 | baseline | 1.3 / 2.0 / 4.7 / 23.8 |
| canon | done | 23/4/0 | 61.75 (1.58) | +2.0% | 2375 | -0.2% | not planned | n/a | 1.3 / 1.9 / 4.6 / - |
| mirror | done | 23/4/0 | 62.73 (1.92) | +3.6% | 2375 | -0.2% | 76.60 | -0.29 | 1.3 / 1.8 / 4.5 / 23.2 |

MMLU Pro question accounting per arm, of the 1196 asked: off: 1194 answered, 2 excluded (empty completion), 0 scored by random guess (no extractable letter); mirror: 1188 answered, 8 excluded (empty completion), 1 scored by random guess (no extractable letter).

MMLU Pro answer changes relative to the off arm. Both runs were asked the same 1196 questions; a question one run left unanswered is dropped from the comparison (compared count below), and the letters actually extracted are compared, so the net column can differ from the score difference by a few random-guess credits. A changed answer means the reasoning text diverged and ended on another letter.

| Compared with off | Questions compared | Responses byte-identical | Final answer changed | right -> wrong | wrong -> right | wrong -> other wrong | Net [questions] |
|---|---|---|---|---|---|---|---|
| mirror | 1186 | 129 (10.9%) | 120 (10.1%) | 40 | 35 | 45 | -5 |

MMLU Pro per subject, percent correct (question counts asked per subject: biology 71, business 78, chemistry 113, computer science 41, economics 84, engineering 96, health 81, history 38, law 110, math 135, philosophy 49, physics 129, psychology 79, other 92; an excluded question lowers a subject's count by one):

| Arm | overall | biology | business | chemistry | computer science | economics | engineering | health | history | law | math | philosophy | physics | psychology | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CI reference | 76.67 | 88.73 | 78.21 | 83.19 | 87.80 | 82.14 | 66.67 | 69.14 | 52.63 | 55.45 | 90.37 | 71.43 | 89.15 | 77.22 | 65.22 |
| off | 76.88 | 91.55 | 80.77 | 84.07 | 87.80 | 80.95 | 69.47 | 67.90 | 50.00 | 51.82 | 94.78 | 67.35 | 89.15 | 81.01 | 59.78 |
| mirror | 76.60 | 87.14 | 82.05 | 86.61 | 90.24 | 79.76 | 75.82 | 66.67 | 50.00 | 52.73 | 93.33 | 67.35 | 89.06 | 73.42 | 57.61 |

Server log evidence. Two facts are read from each cell's rinzler.log: 'HW attention disabled' shows attention ran on the CPU in that arm, and a non-zero 'K mirror' size shows the mirror arena was allocated (zero in the off and canon arms, and always zero for gpt-oss). The footprint line is printed at start-up and again as the KV cache grows, so the early copies quoted here are small; the notes quote the end-of-run values.

- off: HW attention disabled for model 'ingested-gpt-oss-120b-tp4': USE_HW_ATTN=0 / KV cache footprint: 1.00 GB DMA + 0.00 GB K mirror in 58 books / KV cache footprint: 2.02 GB DMA + 0.00 GB K mirror in 115 books
- canon: HW attention disabled for model 'ingested-gpt-oss-120b-tp4': USE_HW_ATTN=0 / KV cache footprint: 1.01 GB DMA + 0.00 GB K mirror in 69 books / KV cache footprint: 2.10 GB DMA + 0.00 GB K mirror in 118 books
- mirror: HW attention disabled for model 'ingested-gpt-oss-120b-tp4': USE_HW_ATTN=0 / KV cache footprint: 1.00 GB DMA + 0.00 GB K mirror in 68 books / KV cache footprint: 2.03 GB DMA + 0.00 GB K mirror in 112 books

## Soak

Planned: 60 minutes, 25 users, mirror arm, models llama-3.1-8b-instruct-good-tp2 + ingested-qwen-3-4b-instruct-2507-tp2 on one tp2 engine. Status: done.

- Planned soak: arm mirror, 25 users, duration 60 min 1 s (Max duration (1:00:00) reached). The harness counted 1 error(s): the monitor alert(s) quoted below; request failures are in the table. Host used memory (whole host, hugepages excluded): growth since start 33.2 GiB at the end, peak growth 42.3 GiB; the monitor's per-process 'Rinzler RSS' figure read 0 because it targets the production systemd units, not our process. Coherency probes 109, failures 0.
  - monitor alert (counted): Memory Growth (5.2041015625 GiB) above maximum threshold (5 GiB)
  - post-run log copy warnings (not counted): 5 'Failed to gather ...' lines; the monitor's journalctl calls need sudo when run as jhan, and our rinzler is not a systemd unit.

| Model | Requests sent / completed / failed (a request still running at the cutoff is neither) | Avg TTFT [s] | Total generation [tok/s] | Per-user generation [tok/s] |
|---|---|---|---|---|
| ingested-qwen-3-4b-instruct-2507-tp2 | 137 / 120 / 0 | 2.04 | 296.41 | 11.81 |
| llama-3.1-8b-instruct-good-tp2 | 140 / 133 / 0 | 1.67 | 288.51 | 11.94 |

Extra soak `off20` (status done):

- Extra soak off20: arm off, 25 users, duration 20 min 0 s (Max duration (0:20:00) reached). The harness counted 0 error(s): none; request failures are in the table. Host used memory (whole host, hugepages excluded): growth since start -0.2 GiB at the end, peak growth 0.0 GiB; the monitor's per-process 'Rinzler RSS' figure read 0 because it targets the production systemd units, not our process. Coherency probes 36, failures 0.
  - post-run log copy warnings (not counted): 5 'Failed to gather ...' lines; the monitor's journalctl calls need sudo when run as jhan, and our rinzler is not a systemd unit.

| Model | Requests sent / completed / failed (a request still running at the cutoff is neither) | Avg TTFT [s] | Total generation [tok/s] | Per-user generation [tok/s] |
|---|---|---|---|---|
| ingested-qwen-3-4b-instruct-2507-tp2 | 37 / 27 / 0 | 5.27 | 156.84 | 10.09 |
| llama-3.1-8b-instruct-good-tp2 | 49 / 34 / 0 | 1.59 | 214.97 | 8.61 |

For comparison, CI's own soak of 2026-09-04 (3 h; 100 users over 4 tp2 engines per the test plan, section 2; models llama-3.1-8b-instruct-good-tp2, llama-3.2-3b-instruct-fast-tp2, llama-3.3-70b-instruct-good-tp2) recorded 0 errors and 0.008 GiB memory growth:

| Model | Requests sent / completed / failed | Avg TTFT [s] | Per-user generation [tok/s] |
|---|---|---|---|
| llama-3.1-8b-instruct-good-tp2 | 550 / 509 / 0 | 3.37 | 5.78 |
| llama-3.2-3b-instruct-fast-tp2 | 606 / 579 / 0 | 2.97 | 5.81 |
| llama-3.3-70b-instruct-good-tp2 | 526 / 496 / 0 | 8.22 | 5.49 |

## Notes from the analyst (hand-written, `exec/results/more-testing-r1/notes.md`)

Notes are dated (UTC) and cite the cell directories under `exec/results/more-testing-r1/cells/`. Words used in the notes: sd = standard deviation (spread) of the 80 per-user-per-round throughput samples inside one run; greedy decoding = the model always takes its highest-scoring next token, so any tiny numeric difference early in an answer can change the rest of the text; chain-of-thought = the reasoning text the model writes before its final letter; prefill = processing the prompt (measured by TTFT, time to first token); decode = generating tokens after the prompt (measured by TPS, tokens per second per user); byte-identical = the two runs produced exactly the same response text; K mirror arena = the second, AMX-friendly copy of the attention keys that the mirror arm keeps in ordinary RAM; KV cache = the stored keys and values of served tokens (in hugepages, so not counted in the host "used memory" figure).

- 20:15 qwen-3-4b tp4, all three arms done. Functional: identical outcome in every arm (25 passed, 2 self-skipped auth tests). Perf at 8 users on one engine: off 77.8, canon 81.4 (+4.5%), mirror 82.1 (+5.5%) tok/s per user; spreads (sd over 80 samples) 0.6-1.2 tok/s. Superseded at 01:20: the sd measures round-to-round drift inside one server process only (the 8 users of a round move together); the between-run spread from the repeated off arm is 2.2%, which is the yardstick used from 01:20 on. The gains are smaller than the decode-only runtron measurements of earlier rounds because this benchmark's context is about 1000 prompt tokens plus up to 1536 generated tokens, where attention is a modest share of decode.
- 20:15 qwen-3-4b tp4 TTFT (time to first token, mostly prefill of the ~977-token prompt with 8 requests arriving together): off 1777 ms, canon 1618 ms (-9%), mirror 2009 ms (+13% vs off, +24% vs canon; every TTFT delta in these notes names its baseline). The mirror penalty is present in every one of the 10 rounds (per-round means 1943-2055 ms vs 1580-1659 ms for canon), so it is systematic, not noise. Hypothesis (not tested here): the write-through of K into the mirror arena during prefill (the server log shows the arena in use: "137.93 GB DMA + 68.96 GB K mirror"). Earlier runtron rounds measured mirror prefill within about 2% of canonical at tp2 [exec/QUEUE.md row 13, "Prefill +1.0-2.0% over inc-1b NET of the RX save_k write-through", results/slot1/p2-inc2.txt; exec/results/perf-round-20260830/perf-round.txt]; this is tp4 with 8 concurrent prefills. Needs a dedicated prefill measurement at tp4 (round 2 candidate). The llama, mixtral, and gpt-oss cells will show whether the TTFT penalty recurs; for gpt-oss the arena is not allocated, so mirror TTFT should equal canon there.
- 20:15 qwen-3-4b tp4 MMLU Pro: off 66.14%, canon 67.64% (+1.51 points), mirror 67.47% (+1.34 points); CI reference 66.97% (main branch, FPGA attention). Both AMX arms sit in the plan's "investigate" band (1 to 2 points). Per question, about 15.6% of final answers changed versus off in either AMX arm (canon: 40 right->wrong, 58 wrong->right; mirror: 46 and 62), and only 6% of the chain-of-thought responses are byte-identical. A change of that size in either direction is what greedy decoding does when a near-tie token flips early in a long answer; the score moved by +16 to +18 questions of 1196. Whether the 94% response divergence is caused by the AMX numerics or by ordinary run-to-run variation of one arm (8 requests batched in changing order) is decided by the queued A/A control (off arm repeated). Until then the MMLU deltas are "no evidence of degradation" and not yet "parity confirmed".
- 21:10 llama-3.1-8b-instruct-good tp2, all three arms done. Functional identical (25/2/0). Perf at 8 users: off 76.1, canon 86.7 (+13.9%), mirror 90.4 (+18.9%) tok/s per user, spreads 0.2 tok/s. MMLU Pro: off 44.40%, mirror 45.07% (+0.67 points, inside the plan's parity band); CI reference 44.82% (this model runs CPU attention in CI as well, so CI-vs-off is close to a main-vs-branch comparison with AMX off: 5 questions of 1196). Per question, 223 answers changed between mirror and off (50 right->wrong, 57 wrong->right) while 45% of responses are byte-identical; qwen had only 6% identical, consistent with its much longer chain-of-thought answers (about 1000 generated tokens versus about 500) giving more chances for a near-tie token to flip.
- 21:10 TTFT pattern now seen on two models: mirror is slower to first token than off by 13% on both (llama tp2: 3148 vs 2784 ms; qwen tp4: 2009 vs 1777 ms) and slower than canon by 17% and 24% (canon itself is faster than off by 4% and 9%), in every round. The runtron rounds of August measured mirror prefill at parity with canonical, so this is specific to the rinzler serving path (8 concurrent prefills of about 1000 tokens each, continuous batching, prefix cache) or to these prompt lengths. The mirror arena is confirmed in use in both cells (server log "K mirror" footprint = half the KV bytes). Round-2 measurement to settle it: TTFT versus concurrent users (1, 2, 4, 8) for canon and mirror on one model, plus the per-token prefill rate from the server log, to separate arena write-through cost from batching effects.
- 22:20 Soak (mirror arm, llama-3.1-8b-good tp2 + qwen-3-4b tp2 on one tp2 engine, 25 users, 60 min): 277 requests sent, 253 completed, 0 failed (the rest were in flight at the cutoff); 109 coherency probes, 0 failures; server stayed up. The harness counted 1 error: its DUT monitor's alert "Memory Growth above maximum threshold (5 GiB)". Host used memory grew 16.5 GiB at 10 min, 31.1 at 20 min, 39.6 at 30 min, then moved between 35.7 and 42.3 GiB (peak 42.3 GiB at 34.5 min; 39.3 at 40 min, 36.8 at 50 min) and fell to 33.2 GiB at the end. The server log's KV footprint line (printed in GB, 10^9 bytes; the monitor prints GiB, 2^30 bytes) moves with it: K mirror 20.5 GB at 10 min, 35.4 at 20 min, 43.8 at 30 min, then between 39.3 and 46.5 GB (42.7 at 40 min, 40.7 at 50 min; peak 46.5 GB at 21:51:28 when the DMA KV footprint peaked at 92.9 GB), 36.5 GB at the end; the arena is always half of the DMA KV bytes. In the same unit the host growth is 0.84 to 0.92 of the arena footprint at every mark (16.6 vs 19.7 GiB at 10 min, 31.1 vs 34.7 at 20 min, 39.7 vs 43.1 at 30 min, 33.2 vs 36.5 at the end), so the arena is large enough to account for all of the growth; the remaining 3 to 4 GiB of printed footprint that is not visible as used memory is unexplained (a per-process memory sample would settle it; the monitor's own "Rinzler RSS" figure read 0.00 GiB throughout because it looks at the production systemd units, not at our process). So the growth follows the K mirror arena filling from ordinary RAM as the KV cache fills, it stops rising when the cache is full, and it shrinks when pages are freed; it is not an unbounded leak within the hour. It is, however, a real operational property of the mirror arm: about half the KV cache size in host RAM per engine (here 45 GB), and CI's soak monitor will flag it as an error every night unless the threshold or the accounting changes. The off-arm soak queued at the end of the run (20 min, same models and users) gives the no-arena baseline for the same host (the test client itself runs on the DUT, so a few GiB of growth are expected from it).
- 22:20 Soak log gathering at the end reported "Failed to gather rinzler_0..3 / caddy / platformd" (the monitor's journalctl calls need sudo when run as jhan, and our rinzler is not a systemd unit). Host memory, power and request metrics were unaffected; the per-process "Rinzler RSS" metric read 0.00 GiB for the same reason (it targets the production units), and the post-run log copy is missing.
- 23:25 mixtral-8x7b tp2, all three arms done. Functional identical (25/2/0). Perf at 8 users: off 33.22, canon 33.14 (-0.2%), mirror 33.28 (+0.2%) tok/s per user, spreads 0.2: decode parity, as expected for a mixture-of-experts model at this context (its expert layers, not attention, dominate; the August runtron round saw +2% at prompt 2048 and +9% only at prompt 8192). TTFT: off 5478, canon 5491, mirror 5514 ms, all within 0.7%: the mirror TTFT penalty seen on qwen and llama (+13% vs off on both; +24% and +17% vs canon) is absent here. Two hypotheses, neither tested in this round: (A) the K write into the mirror arena sits on the prefill critical path for qwen and llama but is hidden behind FPGA time on mixtral (mixtral writes the same K bytes per token as llama: both log 32 layers x 8 KV heads x head size 128, so a fixed cost per byte written alone does not explain the difference); (B) a mirror-layout read cost in prefill attention. Round-2 test: single-user prefill time versus prompt length, canon vs mirror, on llama and mixtral. MMLU Pro: off 42.01% (502/1195; one question excluded after an empty completion), mirror 41.64% (-0.37 points, 4 questions), CI reference 43.81%. Answer churn between mirror and off is the largest of the three models: 381 of 1195 final answers changed (83 right->wrong, 79 wrong->right), 26% of responses byte-identical; a plausible amplifier is expert routing, where a near-tie token flip also changes which experts run for the rest of the answer.
- 23:25 Reading the MMLU deltas across models so far: qwen +1.51/+1.34 (canon/mirror), llama +0.67 (mirror), mixtral -0.37 (mirror). Signs differ between models, and the churn (16 to 32% of answers) is far larger than the net movement (4 to 18 questions), so the net movement looks like the random walk of greedy decoding under small numeric perturbations rather than a systematic quality change. The A/A control (queued) is the test of that reading.
- 00:40 gpt-oss-120b tp4 (AMX-ineligible: head size 64, 8 query heads per KV head; the AMX dispatch is compiled out for it and the mirror arena is not allocated, server log "0.00 GB K mirror"), all three arms done. Functional identical (23/4/0; the 4 skips are the two auth self-skips plus the two legacy-completions tests this chat-only model skips, the same count CI records for it). Perf at 8 users: off 60.6, canon 61.7 (+2.0%), mirror 62.7 (+3.6%) tok/s per user, with sample spreads of 1.4 to 1.9 tok/s, three to ten times wider than for the other models (the August perf round also found gpt-oss at 8 users the noisiest cell). The mirror number is outside the plan's pre-registered +/-3% band by 0.6 points. It is not resolved either way: no AMX or arena code runs for this model in either arm (a compile-time predicate), TTFT is identical in all arms (2375 to 2379 ms), and the qwen A/A repeat moved 2.2% with nothing changed, but gpt-oss has about three times qwen's within-run spread and no gpt-oss arm was repeated (Insufficient data; a repeat of the gpt-oss off or mirror arm decides it, round-2 item). MMLU Pro: off 76.88% (918 of 1194 answered; 2 questions returned empty completions and were excluded), mirror 76.60% (910 of 1188; 8 excluded), CI reference 76.67%; on the 1186 questions both arms answered, mirror is 5 questions lower (914 vs 909 correct, -0.42 points).
- 00:40 gpt-oss gives a no-AMX comparison between the two builds for the MMLU answer churn: no AMX kernel and no arena runs for this model in either arm (the binaries do differ: rinzler.canon with the kill switch vs rinzler.mirror), yet only 129 of the 1186 questions answered in both runs (10.9%) have byte-identical responses and 120 final answers (10.1%) changed (40 right->wrong, 35 wrong->right). The only same-binary repeat (a true A/A control) is the qwen off arm at 01:20. So most of the response divergence seen between arms on the other models is intrinsic to the serving path (8 concurrent requests are batched in changing order and the floating-point reduction order follows), not a property of the AMX kernels. The queued same-binary repeat of the qwen off arm will put a number on that for qwen itself.
- 01:20 A/A control done (qwen-3-4b tp4, off arm run a second time with the same binary and switches; cell `ingested-qwen-3-4b-instruct-2507-tp4__off__rep2`). MMLU Pro 67.81% (811/1196, the runner's own total) against 66.14% for the first off run: +1.67 points from a run that changed nothing. Per question: 195 final answers changed (44 lost, 63 gained; the per-question counts use the extracted letters, so their net of +19 differs by one from the score difference of +20 because one response with no extractable letter was scored correct by the runner's seeded random guess), only 78 responses (6.5%) byte-identical, the same picture as canon-vs-off (186 changed, 6.0% identical) and mirror-vs-off (187 changed, 6.5% identical). Canon against the repeated off run differs by -0.17 points (809 vs 811 correct) with 186 answers changed. Reading: on this serving path, one MMLU Pro run of qwen has a run-to-run spread of about 1.7 points and about 16% answer churn with no code change at all; the AMX arms sit inside that spread. The plan's "investigate" band for qwen is therefore closed as noise, and the round-1 MMLU verdict for all four models is "no detectable accuracy change" (a real effect would have to exceed roughly 2 points to be visible with one run per arm; averaging several runs per arm would tighten that, round-2 candidate).
- 01:20 The same repeat also calibrates the perf benchmark: TPS 76.12 (sd 0.83) against 77.83 (sd 0.64) for the first off run, a -2.2% run-to-run difference between identical configurations, while TTFT reproduced to 0.2% (1781 vs 1777 ms). So the decode gains of llama (+13.9/+18.9%) and qwen (+4.5/+5.5%) exceed the run-to-run spread; mixtral (-0.2/+0.2%) and gpt-oss canon (+2.0%) are inside it; gpt-oss mirror (+3.6%) is not resolved (see 00:40); and the mirror TTFT penalty (+13% vs off on qwen and llama) is far outside the TTFT spread.
- 01:45 Off-arm soak baseline (20 minutes, 25 users, same two models, cell `soak__off20`): 0 request failures, 0 monitor alerts other than the log-copy warnings, host used-memory growth -0.2 GiB throughout (flat), with 56 GB of KV cache allocated in hugepages by the end (hugepages are not counted in the monitor's used-memory figure; the mirror arena is, because it lives in ordinary RAM). This confirms the attribution of the mirror soak's +40 GiB to the K mirror arena. The test client running on the same host adds no measurable growth over 20 minutes.
- 01:45 Campaign closed: 12 planned cells, the 60-minute mirror soak, the A/A control and the off-arm soak all completed between 17:56 and 01:39 UTC; no cell was skipped for time. The machine was handed back clean (no rinzler process, 512 of 512 hugepages free, campaign lock released, production units left inactive for the 02:45 UTC timer as the standing policy requires).

## Cells not run or failed

- none

## Timeline (UTC)

- 17:56 - 18:40  ingested-qwen-3-4b-instruct-2507-tp4 / off  (done)
- 18:40 - 19:22  ingested-qwen-3-4b-instruct-2507-tp4 / canon  (done)
- 19:22 - 20:03  ingested-qwen-3-4b-instruct-2507-tp4 / mirror  (done)
- 20:03 - 20:34  llama-3.1-8b-instruct-good-tp2 / off  (done)
- 20:34 - 20:39  llama-3.1-8b-instruct-good-tp2 / canon  (done)
- 20:39 - 21:04  llama-3.1-8b-instruct-good-tp2 / mirror  (done)
- 21:04 - 22:05  soak main (mirror arm, 60 min, 25 users)  (done)
- 22:05 - 22:38  mixtral-8x7b-instruct-v0.1-tp2 / off  (done)
- 22:38 - 22:49  mixtral-8x7b-instruct-v0.1-tp2 / canon  (done)
- 22:49 - 23:22  mixtral-8x7b-instruct-v0.1-tp2 / mirror  (done)
- 23:22 - 23:54  ingested-gpt-oss-120b-tp4 / off  (done)
- 23:54 - 00:01  ingested-gpt-oss-120b-tp4 / canon  (done)
- 00:01 - 00:32  ingested-gpt-oss-120b-tp4 / mirror  (done)
- 00:33 - 01:17  ingested-qwen-3-4b-instruct-2507-tp4 / off (repeat rep2, A/A control)  (done)
- 01:18 - 01:38  soak off20 (off arm, 20 min, 25 users)  (done)

