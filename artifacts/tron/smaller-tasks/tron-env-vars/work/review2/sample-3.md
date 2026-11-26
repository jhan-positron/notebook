# Head audit sample 3

## `TRON_LOG_PLACEMENT`  (from 1. Variables of the running programs / 1.8 Logging)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_LOG_PLACEMENT` | Developers | `rinzler`, `runtron` (`src/tron/hardware/placer.cpp`) | Any value turns it on. The text is not parsed. The values `0` and `false` also turn it on. Unset: off. No placement count is kept. Empty: on. | While a model loads, the program counts the tiles (blocks of a weight tensor) that it places, per tensor name and per FPGA card. At the end of the placement it writes one info log entry that starts with `Tensor device counts:`. The counts follow as JSON. A `TRON_LOG_LEVEL` of `warn` or higher hides the entry. The entry has several lines. The JSON names each card by its index in the process. With the variable set, the code also needs a tensor name before it places a tile. Without that name, the code aborts. |

## `TRON_TEST_CHILD_LIBRARY_PATH`  (from 2. Dice, Slice and the launcher wrappers / 2.5 Slice)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_TEST_CHILD_LIBRARY_PATH` | `bin/slice` | CI, through `bin/ci/tron-build/test_runtime.py`. | A library search path: directories separated by colons. Unset: `bin/slice` adds nothing to the `LD_LIBRARY_PATH` of the tests it starts. | `bin/slice` puts the value in front of `LD_LIBRARY_PATH` for each test that it starts. `bin/slice` itself keeps its own `LD_LIBRARY_PATH`. The variable is not passed to the test. `bin/slice` ignores a CTest `ENVIRONMENT` entry with this name. The test log shows the resulting `LD_LIBRARY_PATH` in its `# cmd:` line. In CI, `bin/ci/tron-build/test_runtime.py` writes the variable to the GitHub environment file. |

## `TRON_HW_SAMPLER_ALL_SENSORS`  (from 1. Variables of the running programs / 1.10 Tracing)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_HW_SAMPLER_ALL_SENSORS` | Developers | `rinzler`, `runtron` (`src/pos/hwperf.cpp`) | Exactly `1` or `true` turns it on. The comparison is case-sensitive. Any other text is off. No message is logged. Unset: off. For each CPU socket the trace gets the package temperature and the minimum, average and maximum of the other temperature sensors. | Adds one temperature counter for every CPU temperature sensor to the trace, in addition to the summary counters of each socket. The counter name is `<driver> socket<N> <label> (C)`. It has an effect only when `TRON_HW_SAMPLER` turns on the hardware sampler (the thread that writes CPU temperature, frequency and power counters to a trace). The sampler thread reads it once, at its first sample. |

## `TRON_MAX_MAIN_HELPERS`  (from 1. Variables of the running programs / 1.4 Attention)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_MAX_MAIN_HELPERS` | Developers | `rinzler`, `runtron` (`h/tron/models/model.hpp`) | Integer of 0 or more, parsed with `atol`. The unit is worker threads. Text that is not a number counts as `0`. A negative number converts to an unsigned 64-bit number. `-1` becomes 2^64 - 1 threads. That value sets no upper limit. Unset: half of the workers of the shared thread pool, rounded down. Empty: counts as `0`. | Sets the largest number of main helpers in a forward pass, and `0` turns main helpers off. A value below `TRON_MIN_MAIN_HELPERS` or its default aborts the process at model load. The error line in the log names `min_main_helpers` and `max_main_helpers`. With 16 or more workers in the shared thread pool, `0` also needs `TRON_MIN_MAIN_HELPERS=0`. The value is not checked against the size of the shared thread pool. A forward pass that leaves no attention worker aborts the process. |

## `TRON_TOKENIZE_PY`  (from 1. Variables of the running programs / 1.7 Tokenizers)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_TOKENIZE_PY` | Developers | `rinzler`, `runtron`, `rinzler_proxy` (`src/rinzler/tokenizers.cpp`). Also the `make` rule for `gen/tokenize_py` (`GNUmakefile`). | Path of an executable tokenizer program. The text is used as given. A path that does not exist aborts the process when the Python tokenizer starts, with `Python tokenizer script <path> not found`. Unset: `bin/tokenize_py`, relative to the working directory, with the same check. In a Nix dev shell, `make gen/tokenize_py` stops with an error. | Names the program that the Python tokenizer runs. The Python tokenizer is used when the model directory has no `tokenizer.json`, or when `USE_PYTHON_TOKENIZER` or `VALIDATE_TOKENIZERS` is on. In a Nix dev shell, `make gen/tokenize_py` copies this file to `gen/tokenize_py`. The Nix dev shell sets the variable. The LSF runner (`bin/dice-lsf-runner`) sets it for a job submitted from a Nix dev shell. Check: the warning `Falling back to slow tokenizer script <path>`. |

## `TZ`  (from 1. Variables of the running programs / 1.6 Server behavior)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TZ` | Developers | The C library, through `localtime_r` and `mktime` calls in `rinzler` and `rinzler_proxy` (`src/rinzler/harmony.cpp`, `rust/minijinja/src/lib.rs`). Tron code does not call `getenv` for it. | A time zone setting that the C library parses. Tron code does not parse it. Unset: the C library chooses the time zone. Tron code has no rule for this case. | Sets the time zone of the local date and time that `rinzler` writes into prompts. This affects `conversation_start_date` in the system message of `gpt-oss` models, the output of `strftime_now` in chat templates, and the `rendered_at` field of a `save_tokens` capture. `RZ_SYSTEM_START_DATE` pins the date. The current time is then not used, and the pinned date is taken as local noon. Check: the `rendered_at` field of a chat `save_tokens` response shows the date in effect. |

## `DICE_ETA`  (from 2. Dice, Slice and the launcher wrappers / 2.6 Launcher wrappers)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `DICE_ETA` | The wrappers (`bin/rinzler`, `bin/runtron`) | A person, by hand. | Seconds as a number of 0 or more, or `inf`, `infinity`, `infty`, or `?` for no estimate. A negative number or other text makes `slice submit` exit with status 2. Unset: `inf`. Dice then expects no end time for the submission. | Sets the predicted run time that the wrapper passes as `--eta` to `bin/slice submit` when it queues `rinzler` or `runtron` through Dice. The Dice scheduler uses the value to decide whether a later submission can start before an earlier one. The wrapper reads it only on a shared host outside a grant. Dice does not stop a submission that runs longer. `bin/dice-lsf-runner` removes every `DICE_` variable from remote work. A value from the submitting shell does not reach a `--remote` run. |

## `MODEL`  (from 3. Developer tools / 3.1 Load and request generators)

| Variable | Read by | Set by | Values and default | Effect |
|---|---|---|---|---|
| `MODEL` | `burst-test.sh` (`perfetto/tools/burst-test.sh`) | The person who runs `burst-test.sh`. | A model name as text. The script does not check it. Unset: `llama-3.2-3b-instruct-fast-tp2`. | `burst-test.sh` (the script that sends a burst of chat completion requests to a server) puts the value in the `model` field of every request. The option `-m` or `--model` overrides the variable. |

## `TRON_BOOK_INITIAL_TOKENS`  (from 1. Variables of the running programs / 1.3 Memory)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `TRON_BOOK_INITIAL_TOKENS` | Developers | `rinzler`, `runtron` (`h/tron/scheduler/full.hpp`) | Integer number of tokens, parsed with `std::atoi`. A result below `1` counts as `1`. Text that is not a number counts as `1`. Unset: 1600 tokens (25 pages of 64 tokens). Empty: 1 token, which is rounded up to 1 page. | Sets the preferred size of a new KV book. It applies to tokens added at the root of the token tree or one node below it. Sizes round up to whole pages. `TRON_BOOK_MAX_TOKENS` caps this size. A value above that cap acts like the cap. A book is still made large enough for the tokens being added. Other new books start at 1 page or grow by `TRON_BOOK_GROWTH_FACTOR`. No command-line option sets it. No log line shows the value. |

## `RZ_CHAT_TEMPLATE_KWARGS`  (from 1. Variables of the running programs / 1.6 Server behavior)

| Variable | For | Read by | Values and default | Effect |
|---|---|---|---|---|
| `RZ_CHAT_TEMPLATE_KWARGS` | Developers | `rinzler`, `rinzler_proxy` (`src/rinzler.cpp`, `h/rinzler/rinzler-config.hpp`) | JSON object, at most 512 bytes. Member values must not be objects or arrays. `reasoning_effort` must be `none`, `low`, `medium`, `high` or `xhigh`. `enable_thinking` must be a boolean. Reserved keys such as `tools` are invalid (list: `h/rinzler/chat-template-reserved-keys.hpp`). Unset: no server defaults. Empty: invalid. An invalid value makes `rinzler` log an error and exit with code 1. | Sets default `chat_template_kwargs` (extra variables for the template that renders chat messages into prompt text) for every chat completion request. `chat_template_kwargs` in a request override the defaults one key at a time. A top-level `reasoning_effort` in a request overrides that key. Harmony models answer HTTP 400 to a default `reasoning_effort` of `none` or `xhigh`, unless the request overrides it. Check: the log line `Loaded RZ_CHAT_TEMPLATE_KWARGS: <JSON>`. |
