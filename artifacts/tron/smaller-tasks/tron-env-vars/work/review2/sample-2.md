# Head audit sample 2

## `DICE_GRANT_TOKEN`  (from 2. Dice, Slice and the launcher wrappers / 2.2 Dice grant)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_GRANT_TOKEN` | `rinzler`, `runtron`, `rinzler_proxy`, the wrappers and `slice` (`src/system/system.cpp`, `bin/rinzler`, `bin/slice` and other files) | The Dice daemon. Inside a grant, `bin/slice` passes it to each test. | Text that is not empty. It is random text that the Dice daemon creates for one grant. The readers do not parse it. Unset: `rinzler` and `runtron` do not read it unless `DICE_DAEMON_CHILD` is `1`. In that case they fail at startup with `Incomplete Dice grant environment`. | Proves the grant to the Dice daemon. The wrappers and `bin/slice` send it with `DICE_GRANT_ID` in a `grant-check` request, and the daemon compares it with the stored token. `rinzler` and `runtron` only test that it is set and not empty. `bin/slice` leaves it out of the command line that it writes to test logs. The daemon accepts the check only from the started program, its process group or its descendants. Without it, the wrappers and `bin/slice` exit with status 2 inside a grant. |

## `TRON_INGEST_PLUGIN_BUNDLE_STAMP_REQUIRED`  (from 5. Build and packaging / 5.5 Ingest build)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_INGEST_PLUGIN_BUNDLE_STAMP_REQUIRED` | `make` (`GNUmakefile`) | `GNUmakefile`. No person sets it. | Only the text `1` turns the stamp update on. Any other text counts as off. Unset: `make` sets `1` when no goal is given, or when a goal is outside its list of goals that do not use the bundle. | With `1`, `make` runs the stamp helper (`bin/ci/update-ingest-plugin-bundle-stamp.sh`) while it reads the makefile. A value of `1` in the environment turns the stamp update on for the goals that skip it, for example `clean`, `lint` and `deb`. It is an internal variable of `GNUmakefile`. When `make` assigns `1`, it ignores an environment value. A command-line assignment replaces the value for every goal. `make` does not read it when the only goals are `list-tests` or `list-tests-core`. |

## `USE_PYTHON_TOKENIZER`  (from 1. Variables of the running programs / 1.7 Tokenizers)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `USE_PYTHON_TOKENIZER` | Developers | `rinzler`, `runtron`, `rinzler_proxy` (`src/rinzler/tokenizers.cpp`) | Any text other than the exact text `false` turns it on. The comparison is case-sensitive. `0`, `False` and an empty value turn it on. Unset: the Rust tokenizer is used when the model directory holds `tokenizer.json`. Otherwise the Python tokenizer is used. Empty: on. | Forces the Python tokenizer in place of the Rust tokenizer. Its helper program runs once to load the vocabulary and once for every encode call. When `VALIDATE_TOKENIZERS` is on, this variable is ignored. `TRON_TOKENIZE_PY` names the helper program. The process stops when the helper program does not exist. `rinzler` ignores it for models whose id contains `gpt-oss`. Check: the warning `Falling back to slow tokenizer script <path>`. |

## `PWD`  (from 7. Variables defined by other software / 7.1 Operating system and shell)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `PWD` | POSIX shell | Reads | The Nix dev shell hook, the Nix apps `tronperf` and `wrapper` (programs that `nix run` starts), CI scripts and a workflow (`flake.nix`, `bin/ci/ci-restore-test-artifact.sh`, `.github/workflows/cmake-single-platform.yml` and other files) | The Nix dev shell hook uses it as the repository root when `git rev-parse --show-toplevel` fails. The Nix apps search upward from it for `perfetto/tronperf` or `perfetto/wrapper`. `bin/ci/ci-restore-test-artifact.sh` extracts the test archive into it. |

## `TRON_AMX_DISABLE`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_AMX_DISABLE` | Developers | `rinzler`, `runtron` through libtron (`src/tron/kernels/amx_attn.cpp`). Only a build with the CMake option `TRON_AMX_DISPATCH` reads it. | Only the exact text `1` has an effect. Every other text is ignored without a message, for example `0`, `true` or an empty value. Unset: software attention uses the AMX kernel when the CPU, the operating system and the process permission allow AMX. | With `1`, software attention does not use the AMX kernel (code that uses Intel AMX, a matrix instruction set of the CPU). It uses the AVX-512 code for every KV page. AVX-512 is a vector instruction set of the CPU. The program reads the value one time, at the first use. `TRON_AMX_DISPATCH` is off by default and on in the `deb` preset (the package build). The AMX kernel serves only models with a head size of 128 dimensions and 4 query heads per KV head. Check: the FUSE stats file `/model/<model id>/attention/summary` shows `amx_available` as `false`. |

## `TRON_ATTN_SECTION_SPLIT`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_ATTN_SECTION_SPLIT` | Developers | `rinzler`, `runtron` (`h/tron/models/model.hpp`) | Whole number `0` or larger, digits only, parsed with `std::from_chars`. A value above `16` is lowered to `16`. Any other text, also empty text, aborts the process. Unset: 8 pieces. Empty: the value is invalid and the process aborts. | Sets the largest number of pieces into which Tron splits the software attention work on one KV cache page (64 tokens). Different attention workers can then run the pieces. `0` or `1` turns splitting off. The attention worker count also limits the pieces. A minibatch of fewer than 32 tokens is not split. An invalid value passes startup. The first forward pass with software attention work then logs `invalid TRON_ATTN_SECTION_SPLIT` and aborts the process. No command-line option sets it. No log line shows the value. |

## `BUILD_ARTIFACT_MAX_AGE_DAYS`  (from 6. CI / 6.5 Script variables)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `BUILD_ARTIFACT_MAX_AGE_DAYS` | `bin/ci/ci-cleanup-build-artifacts.sh` | `bin/ci/test_build_test_stage.py`. No workflow sets it. | Whole number of days, digits only. Other text stops the script with an error and exit status 2. Unset: 3 days. An empty value also gives 3 days. | The script removes build artifact directories whose modification time is at least this many days old. It looks only at directories named with 7 lowercase hexadecimal characters, at most 2 levels below the artifact root. The artifact root is the first argument of the script (default `/scratch/tron-build`). With `0` the script removes directories of any age. Bash reads a value with a leading `0` as octal. `010` means 8 days. `08` stops the script with an arithmetic error. |

## `MFLAGS`  (from 7. Variables defined by other software / 7.3 Compilers and build tools)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `MFLAGS` | GNU Make | Unsets | No reader in Tron. `bin/ci/test-make-environment-guidance.sh` removes it for `make` commands that it starts. | `bin/ci/test-make-environment-guidance.sh` checks when the makefile prints its warning about a run outside the Nix dev shell. It removes this name from the `make` commands of that check. A value from a parent `make` then does not reach them. |

## `TRON_REQUIRE_CLOSURE_AUDIT`  (from 4. Tests / 4.4 Tests of Dice, Slice and CI scripts)

| Variable | Read by | Values and default | Effect |
|---|---|---|---|
| `TRON_REQUIRE_CLOSURE_AUDIT` | `test-nix-lint-toolchain.sh` (`bin/ci/test-nix-lint-toolchain.sh`) | Only the exact text `1` turns the audit on. Any other text behaves like unset. Unset: the test skips the closure audit, the `ghc` and `cabal` check and the `make lint-notes` check. Its tool path and version checks still run. | With `1`, the test runs the closure audit (a check of the Nix store paths that the lint tools depend on). It also fails when `ghc` or `cabal` is on `PATH`, and it runs `make lint-notes` on a sample file. With `1`, the test needs `TRON_LINT_CLOSURE_PATHS`, `TRON_EXPECTED_NIXFMT_PATH` and `TRON_LINT_RUNTIME_CLOSURE_PATHS`. `TRON_SOURCE_STORE_PATH` is optional. The test fails at its start unless `TRON_NIX_LINT_SHELL` is `1`. `flake.nix` sets `1` in the Nix check `lint-toolchain` (a Nix build that runs this test). |

## `DICE_LSF_TERMINAL_OUTPUT`  (from 2. Dice, Slice and the launcher wrappers / 2.3 Distributed Dice)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_LSF_TERMINAL_OUTPUT` | `bin/slice` | `bin/dice-lsf-runner`, for the command it starts. | Only the exact text `1` counts. Any other text behaves like unset. Unset: `bin/slice run` draws its live status block only when stderr is a terminal. | `bin/slice run` draws its live status block with terminal control sequences even when stderr is not a terminal. `bin/dice-lsf-runner` removes an inherited value. It sets `1` when `bin/dice-lsf-submit` runs with `--wait` and its stdout is a terminal. Without the variable and without a terminal, `bin/slice run` under `DICE_LSF_RUNNING=1` prints at most one progress line every 10 seconds. |
