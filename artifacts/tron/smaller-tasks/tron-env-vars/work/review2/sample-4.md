# Head audit sample 4

## `PERFETTO_CAPTURE_REQUIRE_INTEGRATION`  (from 4. Tests / 4.4 Tests of Dice, Slice and CI scripts)

| Variable | Read by | Values and default | Effect |
|---|---|---|---|
| `PERFETTO_CAPTURE_REQUIRE_INTEGRATION` | `test-perfetto-capture.sh` (`bin/ci/test-perfetto-capture.sh`) | Exactly `1` turns the requirement on. Any other text leaves it off. Unset: when `PERFETTO_BIN_DIR` is unset or empty, or `traced` or `perfetto` in it is not executable, the script prints a skip message and exits with status 0. | With `1`, the script prints a failure message and exits with status 1 when `PERFETTO_BIN_DIR` does not hold the executable Perfetto programs `traced` and `perfetto`. It does not skip the integration checks. CI sets `1` for the step that runs `bin/ci/run-ci-helper-suites.sh` in `cmake-single-platform.yml` and `gcp-nix.yml`. That script starts `test-perfetto-capture.sh`. The variable changes nothing when `PERFETTO_BIN_DIR` holds both programs. |

## `TRON_HWATTN_COMPOUND_SPLIT`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HWATTN_COMPOUND_SPLIT` | Developers | `rinzler`, `runtron` (`h/tron/models/model.hpp`) | Integer, parsed with `std::atol`. The code does not use the result. Unset: no effect. | No effect on `rinzler` or `runtron`. The code reads the value when it plans hardware attention and discards the result. |

## `TRON_PERFETTO_CONFIG`  (from 3. Developer tools / 3.2 Perfetto tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_PERFETTO_CONFIG` | `tronperf` (`perfetto/tronperf`) | A developer, by hand. | Path of a Perfetto config file in protobuf text format. A path that starts with `/` is used as written. Any other path is relative to the repository root. Unset: `tronperf` uses `perfetto/runtron.cfg` as the base config. | `tronperf` (the Perfetto launcher for `runtron`) uses the file as its base config. `perfetto/generate-config` then changes that config with the command-line options of `tronperf`. The option `--perfetto-config` overrides it. `perfetto/wrapper` does not read it. A file that `generate-config` cannot read or parse stops `tronperf` with exit status 2. |

## `BACKGROUND_CHECK_DIR`  (from 6. CI / 6.5 Script variables)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `BACKGROUND_CHECK_DIR` | `bin/ci/background-check.sh` | `bin/ci/test-background-check.sh`. No workflow sets it. | Path of a directory. The script uses the text unchanged. Unset: the script uses `RUNNER_TEMP`. Without `RUNNER_TEMP` it uses `TMPDIR`. Without `TMPDIR` it uses `/tmp`. An empty value counts as unset. | It sets the root directory for the state of each background check (a slow check that the script runs in the background of a job). The state of one check is in `background-check-<NAME>`. When `GITHUB_RUN_ID` is set, the script first appends `background-checks-<run id>-<attempt>-<job>` to the root. `bin/ci/README.md` asks matrix jobs with a shared temporary directory to set separate roots. |

## `REMOTE_REQUIRE`  (from 5. Build and packaging / 5.2 Remote builds and remote execution)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `REMOTE_REQUIRE` | `make` (`GNUmakefile`) | No one. `GNUmakefile` rejects it. A test checks the error. | Any text that is not blank. The text is not parsed. `make REMOTE_REQUIRE=value` has the same effect. Unset: no effect. | `make` stops for every goal with an error. The error text says that `REMOTE_REQUIRE` and `REMOTE_PREFER` are not supported. It names the supported inputs: `REMOTE=sku0`, `REMOTE=sku1`, `REMOTE_MODEL` and `REMOTE_HOST`. |

## `TRON_SPEEDOMETER_TIMESCALE`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_SPEEDOMETER_TIMESCALE` | Developers | `rinzler`, `runtron` (`h/tron/threading.hpp`) | Number, parsed with `std::atof`. The unit is updates of the speed estimator. It must be above 0. Text that is not a number counts as `0`. Unset: `10` updates. Empty: counts as `0`, and the process aborts. | Sets the time constant of the speed estimator of the shared thread pool. The estimator keeps a speed estimate for each worker. At each update, the estimator multiplies its stored measurements by `exp(-(1+p)/value)`, where `p` is `TRON_SPEEDOMETER_PRIOR_STRENGTH`. A larger value makes the speed estimates change more slowly. The speed estimates split the attention work between the attention workers. A value of 0 or below aborts the process when the shared thread pool is created. The error line in the log names `timescale`. There is one update per forward pass. The estimates are not used with the option `--pay-for-determinism`. |

## `HTTP_PROXY`  (from 7. Variables defined by other software / 7.6 Network proxies)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `HTTP_PROXY` | HTTP client libraries | Reads and sets | No Tron code names it outside tests. Python `urllib` reads it inside `bin/hugepage_exhaustion_repro.py`. The `httpx` library reads it inside `t/proxy/tools/capture.py`. `t/proxy/test_rzproxy.py` sets it. | `bin/hugepage_exhaustion_repro.py` and `t/proxy/tools/capture.py` send their `http` requests through this proxy. That includes requests to `rinzler` on `127.0.0.1`, unless `no_proxy` lists that address. When `http_proxy` is also set, the libraries ignore `HTTP_PROXY`. The replay tests under `t/proxy` ignore it. |

## `REMOTE_HOST`  (from 5. Build and packaging / 5.2 Remote builds and remote execution)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `REMOTE_HOST` | `make` (`GNUmakefile`) | A developer, for one `make` test run. | Name of one worker host (a server that LSF runs remote tests on), for example `andoria-02`. More than 1 word stops `make` with an error. `make REMOTE_HOST=name` also works. Unset: `make` requests no worker host. | `make` adds `--remote-host=<value>` to the `bin/slice run` command of the targets `test`, `test-core`, `test-host`, `test-fpga` and `test-fast`. Slice then requires that worker host for the remote run. It needs the remote mode `1`, `sku0` or `sku1` (the value of `REMOTE`). With the mode `0`, `make` stops with an error for every goal. `TRON_REMOTE_EXECUTION` supplies a mode only for the goals that its row names. The remote build job does not receive it. |

## `TRON_HEAP_PROFILE_PATH`  (from 1. Variables of the running programs / 1.3 Memory)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HEAP_PROFILE_PATH` | Developers | `rinzler`, `runtron` (`src/system/heap_v2.cpp`) | Path of a file. The file is opened in append mode with `std::fopen`. Unset: no profile is written. Empty: counts as a path. The open fails and a warning is logged. | Names the file that receives heap profiles. When an allocation from the hugepage heap fails for lack of memory, the arena allocator appends a histogram of the live allocations to this file. The histogram is grouped by size class and by caller address. Each block starts with a line that holds `OOM` and `n_live=`. A profile is written only when the arena allocator is in use and its shadow map (per-allocation tracking) is on: `TRON_HEAP_SHADOW=1` or `--heap-shadow`. The info log line `pos_heap_setup: using arena allocator (pos_heap_v2)` then ends with `with shadow map`. A failed open logs `heap_v2::dump_profile: could not open`. |

## `DICE_LOCK_PATH`  (from 2. Dice, Slice and the launcher wrappers / 2.4 Dice test overrides)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_LOCK_PATH` | `dice` daemon (`bin/dice`) | The Dice tests. | A file path. The text is used as given. Unset: `dice.lock` in the Dice runtime directory (`DICE_RUNTIME_DIR`). That directory is `/run/dice` on a shared host. | Moves the lock file that the Dice daemon holds while it runs. A second daemon that uses the same lock file does not start. Only tests can use it. On a shared host outside a `DICE_TEST_HOST_CONFIG_PATH` override, a daemon with this variable does not start. It prints `DICE_LOCK_PATH is test-only in shared Dice`. A client ignores the variable there. Without that override, the daemon removes the variable from the environment of programs it starts. On a legacy host no Dice daemon runs. |
