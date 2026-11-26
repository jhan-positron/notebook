# Head audit sample 0

## `ImageOS`  (from 7. Variables defined by other software / 7.2 GitHub Actions)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `ImageOS` | GitHub Actions runner images | Sets | No reader in Tron. `.github/workflows/cmake-single-platform.yml` sets it for every job of that workflow. | The workflow sets `ubuntu22` in its workflow-level `env` block. Every step of the workflow inherits it. |

## `TRON_MODEL_CACHE_LEASE_FDS`  (from 3. Developer tools / 3.3 Ingest tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_MODEL_CACHE_LEASE_FDS` | `build-model.py` (`ingest/build-model.py`) | `bin/ci/ingest/prepare_tests.py` | File descriptor numbers separated by white space. Each item is parsed with `int`. An item that is not an integer raises `ValueError` and ends the script. Unset: `build-model.py` passes no extra file descriptor to the export process. | `build-model.py` passes the listed file descriptors to the process that exports the model trace (the PyTorch export of the model). Each descriptor is a lease (an open file that holds a shared lock in the CI model weights cache). `prepare_tests.py` sets the variable only when it runs a command after `--`. It passes the same descriptors to that command. A process that did not inherit these descriptors cannot use the numbers. `build-model.py` does not read the variable when the option `--skip-export` is given. |

## `DICE_DAEMON_CHILD`  (from 2. Dice, Slice and the launcher wrappers / 2.2 Dice grant)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_DAEMON_CHILD` | `rinzler`, `runtron`, `rinzler_proxy`, the wrappers and `slice` (`src/system/system.cpp`, `bin/rinzler`, `bin/slice` and other files) | The Dice daemon. Inside a grant, `bin/slice` sets it for each test. | Exactly `1` means that the Dice daemon started the process. Any other text counts as unset. Unset: the process is not under a Dice grant. `rinzler` and `runtron` parse placement options without grant checks. | With `1`, `rinzler` and `runtron` check placement options such as `--instance`, `--devices` and `--numa` against the granted slots. Startup then fails unless `DICE_SLOTS`, `DICE_GRANT_ID`, `DICE_GRANT_TOKEN` and `--instance` in `SYSTEM_CONFIG` are all set. Under a grant, `--no-opt` does not stop the pinning of application threads to the granted cores. With `DICE_SLOTS` on a shared host, the wrappers, `slice run` and `slice bench` start the work without a new submission. On a legacy host the wrappers remove it before they start the program. |

## `TRON_LOG_LEVEL`  (from 1. Variables of the running programs / 1.8 Logging)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_LOG_LEVEL` | Operators | `rinzler`, `runtron`, `rinzler_proxy`, `libpos` (`src/system/spdlog.cpp`). Some test programs read the name themselves, with `info` as default. | One of `trace`, `debug`, `info`, `warn`, `warning`, `err`, `error`, `critical`, `off`, in lower case. Any other text, for example `INFO`, counts as `off`. Unset: `debug`. Empty: counts as `off`. The program then writes no log messages. | Sets the lowest message level that the program writes. The level applies to the log file and to the output on stderr. With `off`, the program writes no log messages, error messages included. No log line prints the level in effect. `SPDLOG_LEVEL` is applied after it. `SPDLOG_LEVEL` can hide more messages. It cannot show messages below this level. `rinzler` keeps its HTTP library at level `warn`. |

## `PROMPT_MODE`  (from 3. Developer tools / 3.1 Load and request generators)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `PROMPT_MODE` | `burst-test.sh` (`perfetto/tools/burst-test.sh`) | A developer who runs `burst-test.sh`. | `long` or `short`, as exact text. Any other text stops the script with exit status 1. Unset: `long`. | `long` makes `burst-test.sh` (the script that sends a burst of chat completion requests to a server) send an English passage and ask the model to repeat it. The passage size is drawn at random between `PROMPT_TOKENS_MIN` and `PROMPT_TOKENS_MAX`. `short` sends one of 16 short questions. The option `-s` or `--short-prompts` sets `short` and overrides the variable. |

## `RZ_CLI_ARGS`  (from 1. Variables of the running programs / 1.6 Server behavior)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `RZ_CLI_ARGS` | Operators | No reader in Tron. systemd expands it in the `ExecStart` line of the unit `rinzler@.service` (`packaging/systemd/rinzler@.service`, `packaging/tron-host/90-rinzler-host.conf`). | Command-line arguments of `rinzler`. The unit uses the form `$RZ_CLI_ARGS` without braces. systemd splits that form at white space into separate arguments (`systemd.service(5)`). Unset: no arguments. `rinzler` then uses its built-in defaults, for example the model `llama-3.1-8b-instruct-best`. | Holds all command-line arguments of `rinzler` for one instance. The value belongs in `/etc/rinzler/instance-<N>.env`, the file that platformd writes. A value in `/opt/positron/user/config.env` replaces the value of every instance. It does not add to it. The `tron-host` drop-in `90-rinzler-host.conf` (a systemd file that replaces the `ExecStart` line) starts `rinzler_host` with the same arguments and adds `--host 127.0.0.1`. Check: `ps -o args= -p <pid>` prints the command line. |

## `LSB_HOSTS`  (from 7. Variables defined by other software / 7.8 LSF)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `LSB_HOSTS` | LSF | Reads and sets | `dice-lsf-runner` (`bin/dice-lsf-runner`). The test `bin/slice-tests/test_dice_lsf.py` sets it. | The LSF runner (`bin/dice-lsf-runner`) treats these names, and then the system host name, as the names of its server. It checks the requested host and the Dice resource totals against them. A failed check stops the job. |

## `TRON_HW_SAMPLER`  (from 1. Variables of the running programs / 1.10 Tracing)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HW_SAMPLER` | Developers | `rinzler`, `runtron`, `perfetto/grant-rapl-read` (`src/pos/hwperf.cpp`, `perfetto/grant-rapl-read`) | Exactly `1` or `true` turns the sampler on. The comparison is case-sensitive. Any other text is off. No message is logged. Unset: off. No sampler thread is created. A trace holds no counters of the category `hw`. | Turns on the hardware sampler. When a trace session starts, the process creates one sampler thread. While the trace records the category `hw`, the thread reads CPU temperature, CPU frequency and package power from `/sys` and writes them to the Perfetto trace as counters. The script `perfetto/grant-rapl-read` accepts the same 2 values. It then uses `sudo` to give all local users read access to the RAPL files (CPU energy counters) under `/sys/class/powercap`. Package power needs that access. Check: the log line `hw telemetry: cpu frequency sampled from` at the first trace start, on a host with CPU frequency files. |

## `TRON_NO_RTM`  (from 1. Variables of the running programs / 1.1 System, devices and memory pages)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_NO_RTM` | Developers | `rinzler`, `runtron`, `rinzler_proxy` (`src/system/mwaitx.cpp`) | Exactly `1` turns Intel RTM off. Every other text leaves RTM on. Unset: the wait code uses Intel RTM when the CPU is an Intel CPU that reports RTM. | On an Intel CPU with RTM (the TSX transactional memory instructions), the wait code stops using RTM. Each wait step is then a `pause` instruction. The startup log states that decode (token generation) is 13 to 30 percent slower. It also states that the setting is for benchmarking only, never for production. It has no effect on AMD CPUs or on Intel CPUs without RTM. The test `t_mwaitx_cliff` reads it too. Check: when it takes effect, the error log line `Intel RTM (TSX) DISABLED by TRON_NO_RTM=1`. With RTM in use, the log line `INIT: Intel RTM (TSX) supported`. |

## `SLICE_PLATFORM`  (from 2. Dice, Slice and the launcher wrappers / 2.5 Slice)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `SLICE_PLATFORM` | `bin/slice` | A person, by hand. Test fixtures set `test`. | Any text that is not empty. `bin/slice` uses it as the platform name, for example `genoa96`. Unset: `bin/slice` asks `config/resource-parser.sh` for the server type in `config/resource-map.yaml`. If that fails, the name is `_unknown`. | Selects the platform block of `config/test-benchmarks.json` that `bin/slice` reads and writes. A platform block holds the benchmark data of one server type. `bin/slice run` exits with an error when the file has no complete block for the name. `bin/ci/bench_refresh_platform.py` ignores the variable and prints the detected server type. |
