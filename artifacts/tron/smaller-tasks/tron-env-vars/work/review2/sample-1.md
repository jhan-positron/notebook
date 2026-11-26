# Head audit sample 1

## `VALIDATE_TOKENIZERS`  (from 1. Variables of the running programs / 1.7 Tokenizers)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `VALIDATE_TOKENIZERS` | Developers | `rinzler`, `runtron`, `rinzler_proxy` (`src/rinzler/tokenizers.cpp`) | Any text other than the exact text `false` turns it on. The comparison is case-sensitive. `0`, `False` and an empty value turn it on. Unset: no validation. One tokenizer is created. Empty: on. | Creates the Rust tokenizer and the Python tokenizer for each model directory. Each encode and decode call runs both, logs any mismatch as an error and returns the Python result. Encode can add begin-of-sequence or end-of-sequence tokens. For these tokens it uses ids that this mode picks itself. It does not apply `add_bos_token`. Overrides `USE_PYTHON_TOKENIZER`. Needs the Python helper program (`TRON_TOKENIZE_PY`). The process stops when the Python tokenizer cannot be created. Every encode call starts a Python child process. `rinzler` ignores it for `gpt-oss` models. Check: the log line `Using validation tokenizer to compare Rust and Python implementations`. |

## `POS_PREQUANT_CACHE`  (from 1. Variables of the running programs / 1.2 Model files and caches)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `POS_PREQUANT_CACHE` | Developers | `t_prequant_cache`, a test program (`h/tron/hardware/prequant_cache.hpp`). `rinzler` and `runtron` do not read it. | Path to a directory. The text is used as given. An empty value counts as unset. Unset: the root is `<POS_WEIGHTS_CACHE>/prequant` when `POS_WEIGHTS_CACHE` is set and not empty. Otherwise the root is `/opt/positron/weights_cache/prequant`. | No effect on `rinzler` or `runtron`. Sets the root directory of the prequant cache (a disk cache of quantized model weights). Only the test program `t_prequant_cache` uses this cache. Overrides `POS_WEIGHTS_CACHE`. The same header has a disable check that reads `TRON_NO_PREQUANT_CACHE`. Only the test calls that check. `bin/ci/tron-build/test_runtime.py` writes this variable for the CI test jobs. A cache entry is stored at `<root>/<first 2 characters of the key>/<key>`. |

## `SLICE_STATE_DIR`  (from 2. Dice, Slice and the launcher wrappers / 2.5 Slice)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `SLICE_STATE_DIR` | `bin/slice` | Slice test fixtures. A person can set it by hand. | Path of a directory. Unset: `/tmp`. | Changes where `bin/slice` keeps one state file for each `bin/slice run` process. The files are `<value>/slice-state-<user id>/slice-state-pid<PID>.json`. `bin/slice view` and `bin/slice queue` read them. `bin/slice run` also reads them to end test processes whose `bin/slice run` process has ended. `bin/slice` creates the per-user directory with mode `0700`. If that directory belongs to another user or keeps another mode, `bin/slice` writes no state file and prints no error. `bin/slice` also reads older files named `slice-state-pid*.json` in `<value>` itself. |

## `TRON_LINT_RUNTIME_CLOSURE_PATHS`  (from 4. Tests / 4.4 Tests of Dice, Slice and CI scripts)

| Variable | Read by | Values and default | Effect |
|---|---|---|---|
| `TRON_LINT_RUNTIME_CLOSURE_PATHS` | `test-nix-lint-toolchain.sh` (`bin/ci/test-nix-lint-toolchain.sh`) | Path of a text file with one Nix store path (a path below `/nix/store`) on each line. Unset: the test fails and reports a missing runtime closure list when `TRON_REQUIRE_CLOSURE_AUDIT` is `1`. Otherwise the test does not read it. | The test searches this file for a line with a path part that contains `-ghc-` or `-cabal-install-` followed by a digit. On a match the test fails and reports that the lint tools depend on GHC or Cabal. When the file is missing, the search finds no match and this check passes. `flake.nix` sets it to the `store-paths` file of `lintRuntimeClosureInfo` in the Nix check `lint-toolchain` (a Nix build that runs this test). |

## `MODEL_TRACE_STORE_PATH`  (from 6. CI / 6.3 Workflow and job `env:` values)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `MODEL_TRACE_STORE_PATH` | Steps of the job `generate-plugins` (`.github/workflows/gcp-nix.yml`). | `.github/workflows/gcp-nix.yml` | Nix store path of the model traces (the files that the job `build-model-traces` exports for the test models). It is the output `store_path` of that job. Unset: does not occur. The job always defines it. | The job fetches this store path from the Nix binary cache at `REGIONAL_NIX_CACHE` with `bin/ci/nix-cache/acquire.py`. The plugin build (`nix/model-plugins-entry.nix`) gets the value as the Nix argument `modelTraces`. `bin/ci/nix-cache/acquire.py` rejects text that is not a Nix store path of the form `/nix/store/<hash>-<name>`. |

## `UV_VERSION`  (from 6. CI / 6.3 Workflow and job `env:` values)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `UV_VERSION` | Steps of the workflows that set it (`.github/workflows/cmake-single-platform.yml`, `.github/workflows/gcp-nix.yml`, `.github/workflows/publish-deb.yml` and other files) | `cmake-single-platform.yml`, `gcp-nix.yml`, `publish-deb.yml` and other workflow files | Version text of `uv` (the Python dependency manager). Every workflow that sets it writes the same value. `README.dependencies.md` records the pinned value. Unset: no default exists. The paths then lack the version directory, for example `/tools/uv//uv`. | The steps build the program path `/tools/uv/<UV_VERSION>/uv` or the directory `/tools/uv/<UV_VERSION>` from it. They store the program path in `UV`, or they add the directory to `PATH`. The workflows use the program that the runner has under `/tools/uv/<UV_VERSION>`. `bin/ci/lint-ci-pins.sh` fails when the files under `.github` give different values. `positron-dice-deb.yml` sets the variable at job level. The other workflows set it at workflow level. |

## `IN_NIX_SHELL`  (from 7. Variables defined by other software / 7.3 Compilers and build tools)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `IN_NIX_SHELL` | Nix | Reads and sets | `make` (`GNUmakefile`), `cmake` (`cmake/model_selection.cmake`, `ingest/CMakeLists.txt`) and other files. `flake.nix` sets it in its Nix builds, in its checks and in its wrapper for `lefthook` (the Git hook runner). | It marks a run inside the Nix dev shell. When it is set, CMake takes `python3` from `PATH`. When it is not empty, `rust/run-cargo` uses the Rust toolchain of `TRON_NIX_RUST_TOOLCHAIN`, and `make deb` and `make deb-host` stop with an error. |

## `TRON_MIN_MAIN_HELPERS`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_MIN_MAIN_HELPERS` | Developers | `rinzler`, `runtron` (`h/tron/models/model.hpp`) | Integer of 0 or more, parsed with `atol`. The unit is worker threads. Text that is not a number counts as `0`. A negative number converts to an unsigned 64-bit number. `-1` becomes 2^64 - 1 threads. Unset: 1 helper when the shared thread pool has 16 or more workers. Otherwise 0 helpers. Empty: counts as `0`. | Sets the smallest number of main helpers in a forward pass. A value above `TRON_MAX_MAIN_HELPERS` or its default aborts the process at model load. The error line in the log names `min_main_helpers` and `max_main_helpers`. A pass with few tokens can use fewer helpers. The value is not checked against the size of the shared thread pool. A pass that leaves no attention worker aborts the process. |

## `API_KEY`  (from 3. Developer tools / 3.1 Load and request generators)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `API_KEY` | `burst-test.sh` (`perfetto/tools/burst-test.sh`) | The person who runs `burst-test.sh`. | Any text. The script does not check it. Unset: the script sends the text `YOUR_API_KEY`. | `burst-test.sh` (the script that sends a burst of chat completion requests to a server) puts the value in the header `Authorization: Bearer <value>` of every request. The option `-k` or `--key` overrides the variable. |

## `REMOTE`  (from 5. Build and packaging / 5.2 Remote builds and remote execution)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `REMOTE` | `make` (`GNUmakefile`) | Developers. `bin/bsub-build` sets `0` inside the LSF job. | Exactly one of `0`, `1`, `sku0`, `sku1`. Spaces around the value are removed. Any other text stops `make` with an error. `make REMOTE=1` also works. Unset: the value of `TRON_REMOTE_EXECUTION` (default `0`) for build goals and test goals, and `0` for other goals. Empty: `make` stops with an error. | `0` runs everything on the local host. `1`, `sku0` and `sku1` send the goals `all`, `build`, `core`, `build-core`, `build-prod`, `build-test`, `build-ingest`, `build-test-host` and `build-test-fpga` to an LSF worker through `bin/bsub-build`. They also add `--remote` to `bin/slice run` for `test`, `test-core`, `test-host`, `test-fpga` and `test-fast`. They stop `make` with an error for goals that run tests directly, for example `run`, `t_<name>` and `test-proxy`. `sku0` and `sku1` also add `--remote-sku=<value>` (a server class of the test pool). Other goals run on the local host. |
