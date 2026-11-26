# Audit sample 2

## `REAL_CHMOD`  (from 4. Tests / 4.6 Fixture variables)

| Variable | Set in | Read by | Purpose |
|---|---|---|---|
| `REAL_CHMOD` | `bin/ci/test-shared-nfs.sh` | Fake `chmod` scripts that the tests write (`bin/ci/test/darwin-file-commands.sh`, `bin/ci/test-shared-nfs.sh`) | Path of the real `chmod` program that the fake `chmod` scripts run. |

## `TRON_NO_RTM`  (from 1. Variables of the running programs / 1.1 System, devices and memory pages)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_NO_RTM` | Developers | `rinzler`, `runtron`, `rinzler_proxy` (`src/system/mwaitx.cpp`) | Exactly `1` turns Intel RTM off. Every other text leaves RTM on. Unset: the wait code uses Intel RTM when the CPU is an Intel CPU that reports RTM. | On an Intel CPU with RTM (the TSX transactional memory instructions), the wait code stops using RTM. Each wait step is then a `pause` instruction. The startup log states that decode is 13 to 30 percent slower and that the setting is for benchmarking only, never for production. It has no effect on AMD CPUs or on Intel CPUs without RTM. When it takes effect, startup logs the error text `Intel RTM (TSX) DISABLED by TRON_NO_RTM=1`. With RTM in use, startup logs `INIT: Intel RTM (TSX) supported`. The test `t_mwaitx_cliff` reads it too. |

## `TRON_BOOK_GROWTH_FACTOR`  (from 1. Variables of the running programs / 1.3 Memory)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_BOOK_GROWTH_FACTOR` | Operators | `rinzler`, `runtron` (`h/tron/scheduler/full.hpp`) | Decimal number, parsed with `std::stof`. Text after the number is ignored. A value below `1.0` counts as `1.0`. Text with no leading number ends the process at first use. Unset: a factor of `2.0`. Empty: `std::stof` throws, and the process ends at first use. | When a sequence outgrows its KV book (a block of KV cache memory for a run of tokens), the scheduler requests a new book. The requested size is the page capacity of the old book times this factor, rounded up to whole pages of 64 tokens. `TRON_BOOK_MAX_TOKENS` caps the result. At the root of the token tree (the scheduler's tree of all token sequences) and one node below it, `TRON_BOOK_INITIAL_TOKENS` sets the size instead. First use is the first book growth, not startup. No flag exists. No log line shows it. |

## `OMP_THREAD_LIMIT`  (from 7. Variables defined by other software / 7.5 Machine learning libraries)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `OMP_THREAD_LIMIT` | OpenMP | Reads | `make` through the command `nproc` (`GNUmakefile`) | It lowers the default of `NPROC_BUILD` (the number of parallel build jobs). The makefile takes that default from the output of `nproc` and caps it at 16 jobs. |

## `COVERAGE_TIX_DIR`  (from 3. Developer tools / 3.5 Coverage tools)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `COVERAGE_TIX_DIR` | `build-all.sh` (`ingest/build-all.sh`) | `make build-all-coverage` in `ingest/`. | Path of a directory. A relative path starts at the working directory of the script. Unset: `dist-newstyle/coverage/build-all-tix` under the working directory. | In coverage mode `build-all.sh` (the script that runs ingest for the models listed in `config/models.yaml`) creates the directory. It sets `HPCTIXFILE` to `<directory>/<model>.tix` for each model. At the end it combines all `.tix` files (Haskell coverage counts) of the directory into `build-all-combined.tix`. Used only when `COVERAGE` is not empty. `.tix` files of an earlier run are combined too. `make build-all-coverage` sets the default directory itself and deletes the `.tix` files there first. `make coverage-combine` reads only `dist-newstyle/coverage/build-all-tix/build-all-combined.tix`. The working directory of the script must be `ingest/`. |

## `TRON_TRACE_CATEGORIES`  (from 1. Variables of the running programs / 1.10 Tracing)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_TRACE_CATEGORIES` | Developers | `rinzler`, `runtron` (`src/pos/perf.cpp`, `h/common/perfetto.hpp`) | Comma-separated entries with no spaces. Each entry is `+name` (record) or `-name` (do not record). `name` is a trace category, or the start of one followed by `*`. Unset: no selection. Perfetto records every category except those tagged `slow` or `debug` (`driver-detail` and `memory`). An empty value counts as unset. | Selects the trace categories (named groups of Perfetto events) that an in-process trace records. The process writes an in-process trace to a file itself. That covers `runtron --trace FILE`, `runtron --trace-gen FILE`, a SIGUSR1 capture when `TRACE_FILE` names a file, and a FUSE capture that names no categories. A bad entry fails the trace start. Any non-empty value fails a trace that goes to `traced` (the Perfetto daemon). A SIGUSR1 capture goes there when `TRACE_FILE` is unset. A failed start ends the process. A FUSE capture is the exception: it reports the error. |

## `TRON_AMX_DISABLE`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_AMX_DISABLE` | Operators | libtron, inside `rinzler` and `runtron` (`src/tron/kernels/amx_attn.cpp`). Only a build with the CMake option `TRON_AMX_DISPATCH` reads it. | Only the exact text `1` has an effect. Every other text is ignored without a message, for example `0`, `true` or an empty value. Unset: software attention uses the AMX kernel when the CPU, the operating system and the process permission allow AMX. | With `1`, software attention does not use the AMX kernel (code that uses Intel AMX, a matrix instruction set of the CPU). It uses the AVX-512 code for every KV page. The program reads the value one time, at the first use. `TRON_AMX_DISPATCH` is off by default and on in the `deb` preset (the package build). The AMX kernel serves only models with a head size of 128 dimensions and 4 query heads per KV head. The FUSE stats file `/model/<model id>/attention/summary` shows `amx_available`. |

## `CMAKE_C_COMPILER`  (from 5. Build and packaging / 5.4 Nix)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `CMAKE_C_COMPILER` | Nothing in Tron. `flake.nix` exports it in the Nix dev shell. | `flake.nix`, for the Nix dev shell. | Path of the `clang-19` wrapper program in the Nix store. Unset: nothing changes. No file in the repository reads the environment variable. | Nothing changes in Tron. No file in the repository reads the environment variable. `CMakePresets.json` sets the CMake cache variable of the same name to `clang-19`, and that is a separate setting. The Nix dev shell also sets `CC` to the same path. |

## `TRON_NIX_LEFTHOOK`  (from 4. Tests / 4.4 Tests of Dice, Slice and CI scripts)

| Variable | Read by | Values and default | Effect |
|---|---|---|---|
| `TRON_NIX_LEFTHOOK` | `test_install_nix_hooks.py` (`bin/ci/test_install_nix_hooks.py`) | Absolute path of an existing file. The test expects the wrapper script of Lefthook (the program that runs the Git pre-commit checks). Unset: the test class stops in `setUpClass` with `KeyError`. None of its tests runs. | Names the Lefthook wrapper under test. The test passes the path to `bin/install-nix-hooks.py --lefthook`. One test case also runs `<path> install`. A relative path or a missing file raises `RuntimeError`. The test class also reads `shellHook` without a default. `flake.nix` sets `TRON_NIX_LEFTHOOK` in the lint dev shell that `nix develop .#lint` starts. `bin/ci/test-lint-check-regressions.sh` starts this test. |

## `TRON_SPEEDOMETER_TIMESCALE`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_SPEEDOMETER_TIMESCALE` | Developers | `rinzler`, `runtron` (`h/tron/threading.hpp`) | Number, parsed with `std::atof`. The unit is updates of the speed estimator. It must be above 0. Text that is not a number counts as `0`. Unset: `10` updates. Empty: counts as `0`, and the process aborts. | Sets the time constant of the speed estimator of the shared thread pool (the worker threads for model work on the CPU). At each update, the estimator multiplies its stored measurements by `exp(-(1+p)/value)`, where `p` is `TRON_SPEEDOMETER_PRIOR_STRENGTH`. A larger value makes the speed estimates change more slowly. The speed estimates split the attention work between workers. A value of 0 or below aborts the process with `Expected timescale > 0.0f`. `TRON_SPEEDOMETER_PRIOR_STRENGTH` is divided by this value. There is one update per forward pass. A model config with `pay_for_determinism` ignores the estimates. |
