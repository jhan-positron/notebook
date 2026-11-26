# Audit sample 4

## `RZ_SAVE_TOKENS_PROMPT_ONLY`  (from 1. Variables of the running programs / 1.6 Server behaviour)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `RZ_SAVE_TOKENS_PROMPT_ONLY` | Operators | `rinzler`, `rinzler_proxy` (`src/rinzler.cpp`, `h/rinzler/rinzler-config.hpp`) | Exactly `0` or `1`. Any other text, including an empty value, stops rinzler at startup with exit code 1. Unset: off. A request with `save_tokens` runs a normal generation. Empty: rinzler exits at startup with code 1. | With `1`, rinzler answers a request that has `save_tokens` set to `true` and generates nothing for it. `save_tokens` is a request field that returns the rendered prompt and its token ids. The response holds only the `save_tokens` object, and its `output_tokens` list is empty. Other requests generate as before. `1` together with `RZ_ENABLE_SAVE_TOKENS=0` also stops startup. The error log starts with `RZ_SAVE_TOKENS_PROMPT_ONLY validation failed`. With `1`, startup logs `save_tokens requests answer before generation (RZ_SAVE_TOKENS_PROMPT_ONLY=1)`. A value in `/opt/positron/user/config.env` reaches every instance that the packaged systemd unit starts. |

## `DICE_TEST_HOST_CONFIG_PATH`  (from 2. Dice, Slice and the launcher wrappers / 2.4 Dice test overrides)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_TEST_HOST_CONFIG_PATH` | `bin/dice`, `bin/slice`, `bin/rinzler`, `bin/runtron` | The Dice and Slice tests. | Path of a file with `key: value` lines. `bin/dice` reads the keys `mode` (`legacy` or `shared`) and `socket` (an absolute path). Unset: the programs read `/etc/positron/dice.yaml`. A missing file means `mode: legacy`. | The Dice programs take the host mode and the socket path from this file and not from `/etc/positron/dice.yaml`. While the override is active, `bin/dice` accepts path overrides such as `DICE_RUNTIME_DIR` with `mode: shared`. It also starts the daemon itself and not through `dice.service`. The override needs `DICE_ALLOW_TEST_HOST_CONFIG=1`, a `PYTEST_CURRENT_TEST` that is not empty, `bin/dice` inside a git checkout, and a pytest command among the process and its 5 nearest ancestors. Otherwise a set value stops `bin/dice` with an error. With `mode: shared` in `/etc/positron/dice.yaml`, it also needs `DICE_ALLOW_TEST_HOST_CONFIG_SHADOW_SHARED=1`. |

## `TRON_USE_SPECULATION`  (from 1. Variables of the running programs / 1.5 Generation and scheduling)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_USE_SPECULATION` | Operators | `rinzler`, `runtron` (`src/tron/scheduler/legacy_dispatch.cpp`) | Integer, parsed with `atoi`. Any result other than `0` turns it on. Text that is not a number counts as `0`. `true` leaves it off. Unset: off. | For each loaded model, the scheduler looks for a built-in EAGLE draft model (a small model that proposes tokens for the main model to check). The name is `eagle-<model id>`, also tried without `-good`, `-fast`, `-nice` and `-best`. If one exists, it is loaded and rinzler generates with speculative decoding. With a draft model, rinzler answers HTTP 400 to requests for logprobs (non-gemma models), structured output, tool calling or `reasoning_budget_tokens`. Missing draft weights stop the process. runtron uses the draft model only with `--draft-model`. Check: the log line `Found EAGLE model for <model>: <eagle model>`. |

## `POS_PREQUANT_CACHE`  (from 1. Variables of the running programs / 1.2 Model files and caches)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `POS_PREQUANT_CACHE` | Developers | `t_prequant_cache`, a test program (`h/tron/hardware/prequant_cache.hpp`). `rinzler` and `runtron` do not read it. | Path to a directory. The text is used as given. An empty value counts as unset. Unset: the root is `<POS_WEIGHTS_CACHE>/prequant` when `POS_WEIGHTS_CACHE` is set and not empty. Otherwise the root is `/opt/positron/weights_cache/prequant`. | Sets the root directory of the prequant cache (a disk cache of quantized model weights). Only the test program `t_prequant_cache` uses this cache. The variable has no effect on `rinzler` or `runtron`. Overrides `POS_WEIGHTS_CACHE`. The same header has a disable check that reads `TRON_NO_PREQUANT_CACHE`. Only the test calls that check. `bin/ci/tron-build/test_runtime.py` writes this variable for the CI test jobs. A cache entry is stored at `<root>/<first 2 characters of the key>/<key>`. |

## `TRON_SPEEDOMETER_PRIOR_STRENGTH`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_SPEEDOMETER_PRIOR_STRENGTH` | Developers | `rinzler`, `runtron` (`h/tron/threading.hpp`) | Number without a unit, parsed with `std::atof`. It must be 0 or above. Text that is not a number counts as `0`. Unset: `0.1`. Empty: counts as `0`. | Sets how strongly each update moves the speed estimate of each worker of the shared thread pool (the worker threads for model work on the CPU) toward the mean of all workers. `0` removes this effect. The estimates split the attention work between the workers that run attention. At each update the mean of all workers gets the weight `1-exp(-value/timescale)`. The timescale is `TRON_SPEEDOMETER_TIMESCALE` or its default of 10 updates. A negative value aborts the process with `Expected prior_strength >= 0.0f`. The estimates are not used when the model config sets `pay_for_determinism`. |

## `PYTHONUTF8`  (from 7. Variables defined by other software / 7.4 Python tools)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `PYTHONUTF8` | Python | Sets | Nothing in Tron. `perfetto/test_perfetto.py` sets it for a child process. | One test runs `perfetto/generate-config` (the script that generates a Perfetto trace configuration) with `LC_ALL=C`, `PYTHONCOERCECLOCALE=0` and `PYTHONUTF8=0`. The base configuration file of that test holds non-ASCII text. The test requires exit status `0`. |

## `FAKE_PR_BASE_SHA`  (from 4. Tests / 4.6 Fixture variables)

| Variable | Set in | Read by | Purpose |
|---|---|---|---|
| `FAKE_PR_BASE_SHA` | `bin/slice-tests/test_bench_refresh_workflow.py` | Fake `gh` script that the test writes (`bin/slice-tests/test_bench_refresh_workflow.py`) | Gives the base commit id that the fake `gh` prints in its `pr view` answer. |

## `REMOTE_BUILD_QUEUE`  (from 5. Build and packaging / 5.2 Remote builds and remote execution)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `REMOTE_BUILD_QUEUE` | `bin/bsub-build` (`bin/bsub-build`) | Developers, before a build on an LSF worker. | Name of an LSF queue. The script passes the text to `bsub -q` without a check. Unset: the queue `sw-build`. | Selects the LSF queue that receives the build job. `make` runs `bin/bsub-build` only when `REMOTE` is `1`, `sku0` or `sku1`. |

## `TRON_HEAP_PROFILE_PATH`  (from 1. Variables of the running programs / 1.3 Memory)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HEAP_PROFILE_PATH` | Developers | `rinzler`, `runtron` (`src/system/heap_v2.cpp`) | Path of a file. The file is opened in append mode with `std::fopen`. Unset: no profile is written. Empty: counts as a path. The open fails and a warning is logged. | When an allocation from the hugepage heap fails for lack of memory, the arena allocator (`pos_heap_v2`, the build-default allocator of that heap) appends a histogram of the live allocations to this file. The histogram is grouped by size class and by caller address. Each block starts with `=== OOM n_live=`. A profile is written only when the arena allocator is in use and its shadow map (per-allocation tracking) is on: `TRON_HEAP_SHADOW=1` or `--heap-shadow`. The info log line `pos_heap_setup: using arena allocator (pos_heap_v2) with shadow map` confirms both. A failed open logs `heap_v2::dump_profile: could not open`. |

## `CCACHE_DISABLE`  (from 7. Variables defined by other software / 7.3 Compilers and build tools)

| Variable | Defined by | Tron | Where | What Tron does with it |
|---|---|---|---|---|
| `CCACHE_DISABLE` | ccache | Reads and sets | `bsub-build`, `time_rebuild` (`bin/bsub-build`, `bin/time_rebuild`) | `bin/bsub-build` exports a non-empty value in the LSF build job. `bin/time_rebuild` exports `CCACHE_DISABLE=1` before its second, timed `make`. That build then runs without ccache (the compiler cache). |
