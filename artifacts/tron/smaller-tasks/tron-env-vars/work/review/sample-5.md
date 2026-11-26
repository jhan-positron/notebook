# Audit sample 5

## `TRON_BENCHMARK_DIR`  (from 3. Developer tools / 3.2 Benchmark tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_BENCHMARK_DIR` | `benchmark_save.py` (`bin/ci/benchmark_save.py`). The function `golden_trace_dir` in `bin/ci/benchmark_lib.py` also reads it, and no code calls that function. | `bin/ci/tron-build/run_benchmark.sh` and the workflow `benchmark-golden.yml`. | Path of an existing directory. `benchmark_save.py` does not create the directory and does not check the path. Unset: `/scratch/tron-benchmark`. Empty: `benchmark_save.py` uses the empty text, and the result file path starts at the root directory `/`. | `bin/ci/benchmark_save.py` (the script that runs benchmarks and saves the samples) reads and writes its result file in this directory. The file name is `<commit>.<host name>.json`, with the first 7 characters of the commit. The script loads an existing file and skips configurations that already have enough samples. `bin/ci/tron-build/run_benchmark.sh` overwrites it with the value of `TRON_BENCHMARK_RESULTS_ROOT`, or with `/scratch/tron-benchmark` when that variable is unset. `benchmark-golden.yml` sets `/scratch/tron-benchmark-golden`. `ci-run-benchmark.sh`, `benchmark_info.py` and `generate_benchmark_report.sh` use fixed paths under `/scratch`. They do not read the variable. A missing directory makes the first save fail. |

## `DICE_STATE_PATH`  (from 2. Dice, Slice and the launcher wrappers / 2.4 Dice test overrides)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_STATE_PATH` | `bin/dice`. `bin/slice` loads `bin/dice` as a module and reads it there. | The Dice tests. | Path of a file. The text is used as given. Unset: `dice.state.json` in the Dice runtime directory (`DICE_RUNTIME_DIR`). | Moves the file in which the Dice daemon records its running, queued and finished work. `bin/slice` reads the same file. With `mode: shared` in `/etc/positron/dice.yaml`, `bin/dice` stops with `DICE_STATE_PATH is test-only in shared Dice`, unless the test override `DICE_TEST_HOST_CONFIG_PATH` is active. The Dice daemon runs only with `mode: shared`. Without that override, the daemon removes the variable from the environment of programs it starts. |

## `NPROC_BUILD`  (from 5. Build and packaging / 5.1 `GNUmakefile`)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `NPROC_BUILD` | `make`, the Nix build `tron-cmake-test-build`, CI workflows (`GNUmakefile`, `bin/ci/ci-select-tron-build-jobs.sh`, `nix/cmake-tron-test-build.nix` and 2 more files) | CI workflows, the Nix build and `bin/bsub-build`. | Positive integer, a number of parallel jobs. `GNUmakefile` passes the text to `-j` without a check. `bin/ci/ci-select-tron-build-jobs.sh` accepts only digits with no leading `0`. `make NPROC_BUILD=4` also works. Unset: `GNUmakefile` uses the smaller of 16 jobs and the `nproc` output. `bin/ci/ci-select-tron-build-jobs.sh` stops with the error `NPROC_BUILD is required`. | `GNUmakefile` adds `-j <value>` to the flags of `make` and to its `cmake --build` commands, except the one that builds IWYU (the include-what-you-use tool). In the Nix build `tron-cmake-test-build`, the job count is the smaller of `NIX_BUILD_CORES` and this value. For a build on an LSF worker (`REMOTE`), the local value does not reach the worker. `bin/bsub-build` sets the variable there to the value of `REMOTE_BUILD_CORES`. Two CI workflows and `nix/cmake-tron-test-build.nix` set 16 jobs. |

## `TRON_HWATTN_HEAD_TILING`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HWATTN_HEAD_TILING` | Developers | `rinzler`, `runtron` (`src/pos/device.cpp`) | Integer, parsed with `atoi`. A result above 0 forces head tiling on. Any other set value forces it off: `0`, a negative number, or text that is not a number. Unset: each FPGA card decides from its bitfile. Head tiling is on for project 01 or 03 at version 05.09 or later. Empty: forced off. | Forces head tiling on or off for every FPGA card and skips the bitfile check. Head tiling applies when one hardware attention pass covers more KV cache tokens than a card handles for all heads. The card then gets one command that handles fewer heads per pass, not several commands. When set, the log shows once `HW attention: TRON_HWATTN_HEAD_TILING=<value> forces the feature ON` or `OFF`. Words such as `true` force it off. A value above 0 turns head tiling on also for a bitfile that fails the check. No command-line flag sets it. |

## `SLICE_BOX_CAPACITY`  (from 2. Dice, Slice and the launcher wrappers / 2.5 Slice)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `SLICE_BOX_CAPACITY` | `bin/slice`, the Dice daemon (`bin/dice`) | A person, by hand. Slice test fixtures also set it. | Slot count of the server. Integer greater than 0, parsed with `int`. Other text or a count below 1 slot ends the program with an error. Unset: the programs get the slot count from `config/resource-map.yaml` through `config/resource-parser.sh`. | Sets the number of slots of the server for `bin/slice` and the Dice daemon. It has the same meaning as `DICE_BOX_SLOTS`. `DICE_BOX_SLOTS` is used when both are set. `bin/slice` ignores both when a live Dice daemon reports its slot count. The Dice daemon reads its own environment once at startup. Its option `--box` replaces both. `bin/dice-lsf-runner` removes the variable for the command it starts. |

## `RZ_FUSE_MOUNT_PATH`  (from 1. Variables of the running programs / 1.9 Statistics)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `RZ_FUSE_MOUNT_PATH` | Operators | `rinzler`, `runtron`, the packaged systemd unit `rinzler@.service`, `bin/fuse_cleanup.py` (`src/system/fuse_helpers.cpp`, `packaging/systemd/rinzler@.service`, `bin/fuse_cleanup.py` and 7 more files) | Directory path, used as given. An empty value counts as unset. The program creates a missing directory. A failed creation only logs the warning `Could not create FUSE mount point`. Unset: `/opt/positron/stats`. A program whose file path contains `/gen/` uses `<repository root>/stats`, and `REPO_ROOT_OVERRIDE` replaces the repository root. | Sets the base directory where the program mounts the FUSE stats. When the instance count is above 1, the program appends `/instance-<id>` to the path. `RZ_FUSE_MOUNT_PRESCOPED=1` turns this suffix off. `--fuse-mount` overrides it and is used as given. `rinzler_proxy` never mounts and ignores it. The packaged systemd unit sets `/var/run/rinzler/<N>`. It rejects a relative path, `/`, and a path directly under `/`. Logs: `FUSE mount point from RZ_FUSE_MOUNT_PATH: <path>`, then `Stats/config mounted at <path>`. |

## `SPDLOG_LEVEL`  (from 1. Variables of the running programs / 1.8 Logging)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `SPDLOG_LEVEL` | Operators | `rinzler`, `runtron`, `rinzler_proxy`, through the spdlog logging library (`src/system/spdlog.cpp`) | A level name: `trace`, `debug`, `info`, `warn`, `error`, `critical` or `off`. Case is ignored. The spdlog library parses the text and ignores an unknown name without a message. Unset: the logger keeps the level from `TRON_LOG_LEVEL`. That level is `debug` when `TRON_LOG_LEVEL` is unset. | Changes the level of the Tron logger after `TRON_LOG_LEVEL` is applied. The stderr output and the log file keep the level from `TRON_LOG_LEVEL`. So the variable can hide messages, and it cannot show more messages. Example: `warn` hides `info` and `debug` lines. `off` stops all log output. Use `TRON_LOG_LEVEL` to get more detail. The form `NAME=LEVEL` sets one logger, and Tron has one logger, `default_logger`. No log line reports the level. The format comes from spdlog v1.17.0. |

## `PLUGIN_STORE_PATH`  (from 6. CI / 6.3 Workflow and job `env:` values)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `PLUGIN_STORE_PATH` | Steps of the job `prepare-tron-build-inputs` (`.github/workflows/gcp-nix.yml`). | `.github/workflows/gcp-nix.yml` | Nix store path of the model plugins (the model code that ingest generates). It is the output `store_path` of the job `generate-plugins`. Unset: does not occur. The job always defines it. | The job fetches this store path from the Nix binary cache at `REGIONAL_NIX_CACHE` with `bin/ci/nix-cache/acquire.py`. The build recipe (`nix/tron-build.nix`) gets the value as the Nix argument `pluginBundle`. `bin/ci/nix-cache/acquire.py` rejects text that is not a Nix store path of the form `/nix/store/<hash>-<name>`. |

## `PERFETTO_HOME`  (from 3. Developer tools / 3.3 Perfetto tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `PERFETTO_HOME` | `tronperf`, `wrapper` (`perfetto/launcher-common`) | A developer who uses a custom Perfetto build. | Path of a directory. The scripts use its sub-directory `out/linux`. That sub-directory must hold executable files `perfetto`, `traced` and `traced_probes`. Unset: no effect. When `PERFETTO_BIN_DIR` is also unset or empty, `tronperf` and `wrapper` print an error and exit with status 2. | `tronperf` and `wrapper` (the Perfetto capture scripts in `perfetto/`) start `perfetto`, `traced` and `traced_probes` from `$PERFETTO_HOME/out/linux`. The scripts use `PERFETTO_HOME` only when `PERFETTO_BIN_DIR` is unset or empty. `nix run .#tronperf` and `nix run .#wrapper` always export a non-empty `PERFETTO_BIN_DIR`. `PERFETTO_HOME` then has no effect. A missing program stops the script with exit status 2. `bin/ci/perfetto_capture.py` does not read `PERFETTO_HOME`. |

## `TRACE_FILE`  (from 1. Variables of the running programs / 1.10 Tracing)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRACE_FILE` | Developers | `rinzler`, `runtron`, through libpos startup (`src/pos/driver.cpp`). The script `perfetto/tools/rinzler-capture.sh` checks the value of a running rinzler. Two test programs read it too (`t/t_gof_staging_leaks.cpp`, `t/t_pos_lifecycle_fake.cpp`). | The exact text `traced`, or a file path. The text is not checked at startup. Unset: the destination is `traced`, the Perfetto system daemon. An outside Perfetto client owns the output file. Empty: the first `SIGUSR1` capture aborts the program. | With a file path, a `SIGUSR1` capture is recorded inside the process and written to that file. A `SIGUSR1` capture is a Perfetto trace of 10 seconds that starts when the program receives the signal `SIGUSR1`. Each capture truncates the file. The Perfetto daemon then receives nothing. Startup logs `INIT: perfetto trace destination: <text>`. A path that cannot be opened aborts the program at the first `SIGUSR1`. With `traced` or unset, a non-empty `TRON_TRACE_CATEGORIES` aborts the program at `SIGUSR1`. `runtron --trace FILE` records a run to a file without this variable. |
