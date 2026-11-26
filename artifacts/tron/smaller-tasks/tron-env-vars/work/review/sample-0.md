# Audit sample 0

## `FAKE_TRACED_EXIT_AFTER_CAPTURE_READY`  (from 4. Tests / 4.6 Fixture variables)

| Variable | Set in | Read by | Purpose |
|---|---|---|---|
| `FAKE_TRACED_EXIT_AFTER_CAPTURE_READY` | `perfetto/test_perfetto.py` | Fake `traced` script that the test writes (`perfetto/test_perfetto.py`) | Makes the fake `traced` exit with this status after the fake `perfetto` has reported readiness. |

## `DICE_TEST_HOST_CONFIG_SPAWN_OK`  (from 2. Dice, Slice and the launcher wrappers / 2.4 Dice test overrides)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_TEST_HOST_CONFIG_SPAWN_OK` | `bin/dice` | `bin/dice`, when it starts a detached daemon under pytest. | Only the exact text `1` counts. Any other text behaves like unset. Unset: `DICE_TEST_HOST_CONFIG_PATH` needs a pytest command among the process and its 5 nearest ancestors. | Keeps `DICE_TEST_HOST_CONFIG_PATH` usable in a Dice daemon that was detached from pytest. Such a daemon has no pytest ancestor. It counts only when the command line is `dice daemon run`, the parent process id is `1`, `PYTEST_CURRENT_TEST` is set and `bin/dice` runs from a git checkout. `bin/dice` sets it before it starts a detached daemon, when the test override is active. |

## `TRON_TEST_ENVIRONMENT`  (from 6. CI / 6.4 Step values)

| Variable | Set by | Read by | Effect |
|---|---|---|---|
| `TRON_TEST_ENVIRONMENT` | `bin/ci/tron-build/test_runtime.py`. Its `prepare` command appends the variable to the `GITHUB_ENV` file (the file that sets variables for the later steps of a job). | Steps of jobs `test-host` and `test-fpga` (`.github/workflows/gcp-nix.yml`) and of job `refresh` (`.github/workflows/bench-refresh.yml`) | The steps run `uv`, `python3`, `tron-test-host` and `tron-test-fpga` from `<value>/bin`. Job `refresh` also appends `<value>/bin` to `PATH` for `bench-refresh-ci.sh run-measurement`. |

## `FUSE_STATS_STAMP`  (from 5. Build and packaging / 5.1 `GNUmakefile`)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `FUSE_STATS_STAMP` | `make` (`GNUmakefile`) | Nobody. `GNUmakefile` assigns it. | File path. This is an internal make variable. `GNUmakefile` assigns it and ignores an environment value, except when the only goals are `list-tests` or `list-tests-core`. Unset: `gen/.fuse_stats_stamp`. When the only goals are `list-tests` or `list-tests-core`, the text is empty. | An environment value changes no build result. For the goals `list-tests` and `list-tests-core` alone, `make` puts the value into the prerequisite lists of the CMake configure targets and the package target. `make` does not build those targets for these goals. The file holds the last `ENABLE_FUSE_STATS` value. A changed file makes `make` run CMake configure again. `make FUSE_STATS_STAMP=path` on the command line replaces the path for every goal. |

## `EXPORT_ONLY`  (from 3. Developer tools / 3.4 Ingest tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `EXPORT_ONLY` | `build-all.sh` (`ingest/build-all.sh`) | A developer who runs `ingest/build-all.sh`. | Any non-empty text turns it on. The script does not parse the text. The value `0` also turns it on. Unset: off. The script does not add `--export-only`. | `build-all.sh` (the script that runs ingest for the models listed in `config/models.yaml`) adds `--export-only` to every `build-model.py` call. `build-model.py` then writes the trace (the PyTorch export of the model) and stops. It does not start the ingest program and does not update the model config file. `build-model.py` then does not read `GHC`, `CABAL_INSTALL` or `CABAL_FLAGS`. `DUMP_ALL` has no effect. |

## `DICE_GRANT_ID`  (from 2. Dice, Slice and the launcher wrappers / 2.2 Dice grant)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_GRANT_ID` | `rinzler`, `runtron`, `rinzler_proxy`, the wrappers and `slice` (`src/system/system.cpp`, `bin/rinzler`, `bin/slice` and 2 more files) | The Dice daemon. `bin/slice` passes it to child tests. | Text that is not empty. It is the id of a Dice submission, for example `sub-2026-11-21-003`. The readers do not parse it. Unset: `rinzler` and `runtron` do not read it unless `DICE_DAEMON_CHILD` is `1`. In that case they fail at startup with `Incomplete Dice grant environment`. | Names the grant (the slots that Dice gave to one submission). `rinzler` and `runtron` keep their computed placement while this id and the slot list stay the same. The wrappers and `bin/slice` send it to the daemon with `DICE_GRANT_TOKEN` to confirm the grant. `rinzler` and `runtron` print it in `Dice grant <id>:` error lines. On a shared host the wrappers and `bin/slice` exit with status 2 when `DICE_SLOTS` and `DICE_DAEMON_CHILD` are set but the id is missing. `bin/ci/bench_refresh_quiesce.py` compares it with the id of the running submission. |

## `TRON_HW_SAMPLER_INTERVAL_MS`  (from 1. Variables of the running programs / 1.9 Statistics)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HW_SAMPLER_INTERVAL_MS` | Developers | `rinzler`, `runtron` (`src/pos/hwperf.cpp`) | Integer number of milliseconds, parsed with `atoll`. Only a result above 0 is used. `0`, a negative number and text that is not a number select the default. Unset: 100 ms. | Sets the wait between two samples of the hardware sampler. It has an effect only when `TRON_HW_SAMPLER` turns the hardware sampler on. The sampler thread reads it once, when the thread starts. Text that starts with a number uses that number: `50ms` means 50 ms. No log line shows the value. |

## `REMOTE_MODEL`  (from 5. Build and packaging / 5.2 Remote builds and remote execution)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `REMOTE_MODEL` | `make` (`GNUmakefile`) | A developer, for one `make` test run. | One CPU model name that OpenLava (the LSF scheduler for remote test runs) knows, for example `genoa96`. More than 1 word stops `make`. `make REMOTE_MODEL=name` also works. Unset: `make` requests no CPU model. | `make` adds `--remote-model=<value>` to the `bin/slice run` command of the targets `test`, `test-core`, `test-host`, `test-fpga` and `test-fast`. Slice then requires that CPU model for the remote run. It needs the remote mode `1` (the value of `REMOTE`). With the mode `0`, `make` stops with an error for every goal. With `sku0` or `sku1`, `make` stops with the error `already selects a pool class`. The remote build job does not receive it. |

## `SUDO_USER`  (from 1. Variables of the running programs / 1.1 System, devices and memory pages)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `SUDO_USER` | Developers | The hugepage heap setup that libpos startup calls (`src/system/memory.cpp`), in `rinzler`, `runtron` and the hardware test programs. Nothing in Tron sets it. The program `sudo` sets it. | Any value, including an empty one. The code tests only that the variable exists. Unset: this check does not stop the program. | When a program runs as root and the variable exists, the hugepage heap setup fails with the log line `Please do not run as sudo`. FPGA card startup then logs `INIT: Environment setup failed. Aborting.` and exits with code 1. `rinzler` and `runtron` never reach this check as root. They abort earlier with `fuse_sysfs must not run as root`, with or without the variable. The check stops a hardware test program that runs under `sudo`. A root process without the variable passes the check. |

## `WEIGHTS_ROOT`  (from 3. Developer tools / 3.4 Ingest tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `WEIGHTS_ROOT` | `build-all.sh` (`ingest/build-all.sh`) | A developer, by hand. `config/test_model_definitions.py` sets it in one test. | Path of a directory. It holds one sub-directory of model weights for each Hugging Face model ID. Unset: `/opt/positron/weights/huggingface`. | `ingest/build-all.sh` passes `<WEIGHTS_ROOT>/<model ID>` to `ingest/build-model.py` as the model path (`-m`). A model whose directory does not exist fails with `local weights not found`. A required model without a directory ends the script. An optional one is only reported. `ingest/build-model.py` does not read the variable. It has its own fixed path `/opt/positron/weights/huggingface`. For a model path outside that path, it passes no `--tokenizer` argument to the export step. |
