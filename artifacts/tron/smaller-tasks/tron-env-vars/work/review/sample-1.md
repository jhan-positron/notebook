# Audit sample 1

## `RZ_RUNFILE_DIR`  (from 1. Variables of the running programs / 1.6 Server behaviour)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `RZ_RUNFILE_DIR` | Operators | `rinzler`, `rinzler_proxy` (`h/rinzler/rinzler-config.hpp`, `src/rinzler.cpp`). The test launcher `t/proxy/rzproxy/launch.py` reads it too. | Path of an existing directory that rinzler can write. The text is used as given. An empty value counts as unset. rinzler does not create the directory. Unset: `/var/log/positron`. | Sets the directory of the run file `rinzler-<pid>.run`. rinzler writes this JSON file after all models have loaded and removes it on a clean shutdown. The file holds the process id, the model names and the instance. No command-line flag exists. When the directory is not writable, rinzler prints `Error: runfile directory is not writable` and exits with code 1 before it loads a model. Log after the write: `Rinzler ready. Wrote PID file: <path>`. |

## `DICE_LOG_PATH`  (from 2. Dice, Slice and the launcher wrappers / 2.4 Dice test overrides)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_LOG_PATH` | `dice` daemon (`bin/dice`) | The Dice test fixtures. | A file path. The text is used as given. Unset: `dice.log` in the Dice runtime directory. That directory is `/run/dice` on a shared host. | Moves the log file of the Dice daemon. Only tests can use it. On a shared host outside a `DICE_TEST_HOST_CONFIG_PATH` override, a daemon with this variable does not start. It prints `DICE_LOG_PATH is test-only in shared Dice`. A client ignores the variable there. On a legacy host no Dice daemon runs. |

## `DICE_LSF_TERMINAL_OUTPUT`  (from 2. Dice, Slice and the launcher wrappers / 2.3 Distributed Dice)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_LSF_TERMINAL_OUTPUT` | `bin/slice` | `bin/dice-lsf-runner`, for the command it starts. | Only the exact text `1` counts. Any other text behaves like unset. Unset: `bin/slice run` draws its live status block only when stderr is a terminal. | `bin/slice run` draws its live status block with terminal control sequences even when stderr is not a terminal. `bin/dice-lsf-runner` removes an inherited value. It sets `1` when `bin/dice-lsf-submit` runs with `--wait` and its stdout is a terminal. Without the variable and without a terminal, `bin/slice run` under `DICE_LSF_RUNNING=1` prints at most one progress line every 10 seconds. |

## `TRON_HWATTN_COMPOUND_SPLIT`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HWATTN_COMPOUND_SPLIT` | Developers | `rinzler`, `runtron` (`h/tron/models/model.hpp`) | Integer, parsed with `std::atol`. The code does not use the result. Unset: no effect. | No effect. The code reads the variable, computes a flag and discards the flag. A source comment says that the variable is intentionally ignored. The read happens only when hardware attention is active for the model. |

## `GIT_SHA7`  (from 6. CI / 6.4 Step values)

| Variable | Set by | Read by | Effect |
|---|---|---|---|
| `GIT_SHA7` | `.github/workflows/gcp-nix.yml` | The step `Run exact prebuilt benchmark` of the job `benchmark` (`.github/workflows/gcp-nix.yml`). | The step passes the value to `bin/ci/tron-build/run_benchmark.sh`. That script uses it in the name of the benchmark result file: `<results directory>/<value>.<host>.json`. The results directory is `/scratch/tron-benchmark` unless `TRON_BENCHMARK_RESULTS_ROOT` is set. |

## `TRON_TOKENIZE_PY`  (from 1. Variables of the running programs / 1.7 Tokenizers)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_TOKENIZE_PY` | Operators | `rinzler`, `runtron`, `rinzler_proxy` (`src/rinzler/tokenizers.cpp`). Also the `make` rule for `gen/tokenize_py` (`GNUmakefile`). | Path of an executable tokenizer program. The text is used as given. If the path does not exist, the program aborts with `Python tokenizer script <path> not found`. Unset: the programs run `bin/tokenize_py`, relative to their working directory. In a Nix dev shell, `make gen/tokenize_py` stops with an error. | Names the program that the Python fallback tokenizer runs as a child process to read the vocabulary and to encode text. In a Nix dev shell, `make gen/tokenize_py` copies this file to `gen/tokenize_py`. The fallback is used when the model directory has no `tokenizer.json`, when the Rust tokenizer fails to load, or when `USE_PYTHON_TOKENIZER` or `VALIDATE_TOKENIZERS` is enabled. The warning `Falling back to slow tokenizer script <path>` shows the path in effect. The Nix dev shell sets it. |

## `REMOTE_BUILD_MEM`  (from 5. Build and packaging / 5.2 Remote builds and remote execution)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `REMOTE_BUILD_MEM` | `bin/bsub-build` (`bin/bsub-build`) | Developers, before a build on an LSF worker. | A number of MB (megabytes). The script does not check the text. It passes the text to `bsub` in `rusage[mem=<value>]`. Unset: 8192 MB for each core of `REMOTE_BUILD_CORES`. That is 131072 MB for the default of 16 cores. | Sets the memory that the LSF build job reserves. The script comment says `8 GB per core` for the default, and the log line adds the suffix `M`. The repository holds no LSF configuration that confirms the unit of `rusage[mem=]`. `make` runs `bin/bsub-build` only when `REMOTE` is `1`, `sku0` or `sku1`. |

## `TRON_HEAP_SHADOW`  (from 1. Variables of the running programs / 1.3 Memory)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HEAP_SHADOW` | Developers | `rinzler`, `runtron` (`src/system/memory.cpp`) | Exactly `1` turns the shadow map on. The code compares the text with `strcmp`. Any other text, such as `true`, is off. No message is logged. Unset: the shadow map is off, unless the option `--heap-shadow` is given. | Turns on the shadow map of the arena allocator (`pos_heap_v2`, the default allocator for hugepage memory). The shadow map holds one record for each live allocation, with the requested size and 2 caller addresses. Each free checks the pointer and size against the record, and a mismatch aborts the process. `--heap-shadow` does the same, on the command line or in `SYSTEM_CONFIG`. No effect when `TRON_USE_ARENA_ALLOCATOR` selects the legacy heap. The `TRON_HEAP_PROFILE_PATH` profile of the arena allocator needs the shadow map. Check: the log line `pos_heap_setup: using arena allocator (pos_heap_v2) with shadow map`. |

## `TRON_INGEST_LIBSTDCXX_PATH`  (from 3. Developer tools / 3.4 Ingest tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_INGEST_LIBSTDCXX_PATH` | `build-model.py` (`ingest/build-model.py`) | The Nix dev shell and the derivation in `nix/model-traces.nix`. | Path of the directory that holds `libstdc++`. The script does not check the text. Unset: `build-model.py` does not change `LD_LIBRARY_PATH` of the export subprocess. | `ingest/build-model.py` puts the directory at the front of `LD_LIBRARY_PATH` for its export subprocess (the ingest step that exports the PyTorch model trace). Later subprocesses of the script do not get the change. The script reads it only when the export step runs. The option `--skip-export` skips that step. Nix sets it to the `libstdc++` directory of the Nix compiler on Linux, and to an empty string on other systems. |

## `GITHUB_RUN_ATTEMPT`  (from 7. Variables defined by other software / 7.2 GitHub Actions)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `GITHUB_RUN_ATTEMPT` | GitHub Actions | Reads | `background-check.sh`, `publish_regional.py`, `prepare_handoff.py`, `prime_hf_models.py` (`bin/ci/background-check.sh`, `bin/ci/nix-cache/publish_regional.py`, `bin/ci/tron-build/prepare_handoff.py` and 1 more file) | For an attempt above 1, `prepare_handoff.py` writes `tests_required=true` even when a pass marker exists. It is the second part of the `nonce` text of `publish_regional.py` and of the state directory name of `background-check.sh`. |
