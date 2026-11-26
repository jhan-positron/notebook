# Audit sample 3

## `BASE_SHA`  (from 6. CI / 6.4 Step values)

| Variable | Set by | Read by | Effect |
|---|---|---|---|
| `BASE_SHA` | `.github/workflows/cmake-single-platform.yml`, `.github/workflows/gcp-nix.yml` | Step `Generate unified benchmark report` of job `benchmark-report` (`.github/workflows/cmake-single-platform.yml`, `.github/workflows/gcp-nix.yml`) | The step passes it to `bin/ci/generate_benchmark_report.sh` as the third argument, the reference commit. The report adds a comparison with that commit when a file `/scratch/tron-benchmark/<7-character commit id>.*.json` exists. |

## `SLICE_STATE_DIR`  (from 2. Dice, Slice and the launcher wrappers / 2.5 Slice)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `SLICE_STATE_DIR` | `bin/slice` | Slice test fixtures. A person can set it by hand. | Path of a directory. Unset: `/tmp`. | Changes where `bin/slice` keeps one state file for each `bin/slice` process that runs tests. The files are `<value>/slice-state-<user id>/slice-state-pid<PID>.json`. `bin/slice view`, `bin/slice queue` and the cleanup of stale test processes read them. `bin/slice` creates the per-user directory with mode `0700`. If that directory belongs to another user or keeps another mode, `bin/slice` writes no state file and prints no error. `bin/slice` also reads older files named `slice-state-pid*.json` in `<value>` itself. |

## `RZ_FUSE_MOUNT_PRESCOPED`  (from 1. Variables of the running programs / 1.9 Statistics)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `RZ_FUSE_MOUNT_PRESCOPED` | Operators | `rinzler`, `runtron` (`src/system/fuse_helpers.cpp`). `rinzler_proxy` never mounts and does not read it. | Only the exact text `1` has an effect. Every other text is ignored without a message, for example `true`, `yes`, `0` or an empty value. Unset: when the instance count is above 1, the program appends `/instance-<id>` to the FUSE stats mount path. | With `1`, the program mounts the FUSE stats at the base path and adds no `/instance-<id>` suffix. The base path comes from `RZ_FUSE_MOUNT_PATH` or from the built-in default. No effect with `--fuse-mount`, with an instance count of 1, or with no instance set. The packaged systemd unit sets `1`. A value in `/etc/rinzler/instance-<N>.env` replaces it. With the suffix on, the log holds `FUSE mount point scoped for instance`. |

## `HWATTN_MAX_B`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `HWATTN_MAX_B` | Developers | `rinzler`, `runtron` through libpos (`src/pos/driver.cpp`) | Integer number of queries, parsed with `atoi`. Only a value above `0` is used. Unset: the limit is the value computed for the FPGA card. It is at most 32 queries. | Lowers the largest number of queries (batch entries) in one hardware attention pass on an FPGA card. The result is the smaller of the value and the limit computed for the card. The variable cannot raise the limit. `0`, a negative number, text that is not a number and an empty value count as unset. There is no error and no log line for the value. The value is read once per process. `rinzler_proxy` does not read it. |

## `POS_WEIGHTS_DIR`  (from 1. Variables of the running programs / 1.2 Model files and caches)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `POS_WEIGHTS_DIR` | Operators | `rinzler`, `runtron`, `rinzler_proxy` through libtron (`src/tron/models/load.cpp`) | Path to a directory: the root of the model weights tree. The text is used as given. An empty value counts as unset. Unset: the root is `/opt/positron/weights/huggingface`. | Sets the root directory under which the built-in weights name of a model, such as `<org>/<model>`, is looked up. It applies when a model is loaded with no explicit weights path. The path found is made canonical, and the programs read the model files from it. `--model-path` does not use it. A relative `--model-path` is joined to the fixed root `/opt/positron/weights/huggingface/`. A missing directory logs `Weights not found at the source path: <path>`, and the program stops. In `rinzler`, `GET /v1/info` returns the weights path of each model. |

## `TRON_BOOK_MAX_TOKENS`  (from 1. Variables of the running programs / 1.3 Memory)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_BOOK_MAX_TOKENS` | Operators | `rinzler`, `runtron` (`h/tron/scheduler/full.hpp`) | Integer number of tokens, parsed with `std::atoi`. A result below `1` counts as `1`. Text that is not a number counts as `1`. Unset: 1600 tokens (25 pages of 64 tokens). Empty: 1 token, which is rounded up to 1 page. | Caps the size that the scheduler prefers for a new KV book (a block of KV cache memory for a run of tokens). The cap is rounded up to whole pages of 64 tokens. The request is raised above the cap when the added tokens need more pages. It caps `TRON_BOOK_INITIAL_TOKENS` and the result of `TRON_BOOK_GROWTH_FACTOR`. The value is read once per process. A wrong value logs no message. No flag exists. No log line shows the value. |

## `POS_HUGEPAGE_PATH`  (from 1. Variables of the running programs / 1.1 System, devices and memory pages)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `POS_HUGEPAGE_PATH` | Operators | `rinzler`, `runtron` (`src/pos/driver.cpp`, `src/system/system.cpp`) | Path of a file on a hugetlbfs mount (a file system that provides hugepages). The text is used as given. Unset: the `--hugepage_file` value, or `/dev/hugepages/libpos`. Empty: the path becomes empty. It is not treated as unset. | Sets the base path of the hugepage files. Without `--instance`, the process maps this one file. With `--instance`, only the directory of the path is used, and the files are named `slice-<k>-of-8`, one for each physical slice (one FPGA card with its CPU cores) of the instance. Overrides `--hugepage_file`. Startup fails when the directory of the path cannot be read. When Dice starts the process (`DICE_DAEMON_CHILD` is `1`), the path must resolve to `/dev/hugepages/libpos`, or startup fails. The debug log shows `INIT: Allocating <count> hugepages from <path>*`. |

## `FAKE_ISSUE_BODY`  (from 4. Tests / 4.6 Fixture variables)

| Variable | Set in | Read by | Purpose |
|---|---|---|---|
| `FAKE_ISSUE_BODY` | `bin/slice-tests/test_bench_refresh_workflow.py` | Fake `gh` that the test generates (`bin/slice-tests/test_bench_refresh_workflow.py`) | The fake `gh` copies the file named by its last argument to this path. |

## `TRON_DRAFT_TREE_MAX_DEPTH`  (from 1. Variables of the running programs / 1.5 Generation and scheduling)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_DRAFT_TREE_MAX_DEPTH` | Operators | `rinzler`, `runtron` (`src/tron/generation/speculate.cpp`) | Integer number of tree levels, parsed with `std::atoi`. The root counts as level 1. Text that is not a number counts as `0`. `0` and `1` draft no token. Unset: 2 levels. Empty: counts as `0`. No token is drafted then. | Sets the largest depth of the draft tree. In speculative decoding, a draft model proposes this tree of candidate tokens, and the main model then verifies them. A draft step adds one level only while the tree is shallower than this value. It has an effect only when speculative decoding is active (see `TRON_USE_SPECULATION`). With the default `TRON_DRAFT_TREE_MAX_SIZE` of 2 nodes, a depth above 2 levels adds no verified token. A negative number becomes a very large limit. No flag exists. No log line shows the value. |

## `UV_VERSION`  (from 6. CI / 6.3 Workflow and job `env:` values)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `UV_VERSION` | Steps of the 7 workflows that set it (`.github/workflows/cmake-single-platform.yml`, `.github/workflows/gcp-nix.yml`, `.github/workflows/publish-deb.yml` and 4 more files) | `.github/workflows/cmake-single-platform.yml`, `.github/workflows/gcp-nix.yml`, `.github/workflows/publish-deb.yml` and 4 more | Version text of `uv` (the Python dependency manager). Every workflow that sets it writes `0.9.5`. Unset: no default exists. The paths then lack the version directory, for example `/tools/uv//uv`. | The steps build the program path `/tools/uv/<UV_VERSION>/uv` or the directory `/tools/uv/<UV_VERSION>` from it. They store the program path in `UV`, or they add the directory to `PATH`. The workflows do not install `uv`. They use the program that the runner has under `/tools/uv/<UV_VERSION>`. `bin/ci/lint-ci-pins.sh` fails when the YAML files under `.github` give different values. `.github/workflows/positron-dice-deb.yml` sets the variable at job level. The other 6 workflows set it at workflow level. |
