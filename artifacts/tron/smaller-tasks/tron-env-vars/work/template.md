# Environment variables

## Short version

This file lists the environment variables that the Tron source code reads or
sets. Support engineers need two parts: [How to set a variable](#how-to-set-a-variable)
and section 1, [Variables of the running programs](#1-variables-of-the-running-programs).
A PR that adds, renames or removes a variable, or changes how a variable
behaves, also updates this file.

## How to read this file

Each variable has one row, or one entry in the lists of sections 4.6 and 6.4.
Other rows can mention the name. Search the file for the name.

A variable that the code reads and that this file lacks is a defect of this
file. Add the row, or report it.

The rows are grouped by the code that reads the variable:

| Section | Holds | Main readers of the section |
|---|---|---|
| [1. Variables of the running programs](#1-variables-of-the-running-programs) | Variables that `rinzler`, `runtron` and their libraries read | Support engineers, all developers |
| [2. Dice, Slice and the launcher wrappers](#2-dice-slice-and-the-launcher-wrappers) | Variables of the tools that share one server between users and tests | Developers, lab administrators |
| [3. Developer tools](#3-developer-tools) | Variables of the tools that a developer runs by hand: load generators and trace, ingest, coverage, lint and hardware tools | Developers |
| [4. Tests](#4-tests) | Variables that only test code reads | Developers |
| [5. Build and packaging](#5-build-and-packaging) | Variables read when the code is configured, built or packaged | Developers |
| [6. CI](#6-ci) | Variables that the workflows and the scripts that CI runs read | Developers who change workflows |
| [7. Variables defined by other software](#7-variables-defined-by-other-software) | Names that the operating system, GitHub Actions, build tools and libraries define, and that Tron reads or sets | Developers |

The columns mean:

- **Variable**: the exact name. Names are case-sensitive.
- **For** (section 1 only):
  - *Operators*: a support engineer or an operator may need to set or check
    the variable on a deployed system. The team that owns the code that reads
    the variable decides this label.
  - *Developers*: every other variable of section 1. It exists for debugging,
    experiments, tuning or tests. Do not set it on a customer system without
    advice from engineering. Engineering may ask you to set one for a
    diagnosis. Then take the exact value from the row, and remove the variable
    when the diagnosis ends.
- **Read by**: the programs that read the variable, and the main source files.
  Search the source for the name to find every read.
- **Set by** (sections 2, 3, 5 and 6): the person, program or file that sets
  the variable.
- **Values and default**: the accepted values and how the program parses the
  text. The text after "Unset:" says what happens when the variable is not
  set. The text after "Empty:" says what an empty value does, when that
  differs.
- **Effect**: what changes when the variable is set, and what else interacts
  with it. In section 1, the text after "Check:" names the log line, the file,
  the command or the response field that shows the value in effect.
- **Defined by** (section 7): the software that gives the name its meaning.
- **Tron** (section 7): one of *Reads*, *Sets*, *Reads and sets* or *Unsets*.
  *Reads*: Tron code reads the name. *Sets*: Tron code sets it, for itself or
  for a child process. *Unsets*: Tron code only removes it from the
  environment of a child process.
- **Where** (section 7): the Tron files that read, set or unset the name.
- **What Tron does with it** (section 7): how Tron code uses the name.

This file leaves out names that are not environment variables:

- CMake options such as `BUILD_EXPERIMENTAL_MODELS` and `TRON_AMX_DISPATCH`.
- Make variables that only the `make` command line can set, such as
  `BUILD_TYPE`.
- Command-line options of the programs.

This file describes the code of the commit that holds it. An installed package
can be older. `/opt/positron/bin/rinzler --version` prints the installed
version. A program ignores a variable that it does not know, and it prints no
message about it.

## Rules for developers

Update this file in the same PR when the PR does one of these things:

- It adds a read of a new environment variable. This applies to every language
  in the repository, for example C++, Rust, Python, shell, Make, CMake, Nix,
  Haskell and workflow YAML.
- It renames or removes a variable.
- It changes the accepted values, the parsing, the default or the effect of a
  variable.
- It adds or removes a reader of an existing variable, or changes who sets a
  variable.
- It makes Tron set a variable for a child process or a library, or remove one
  from the environment of a child process.
- It changes a log line that a row of this file quotes.
- It moves or renames a file that a row names.

How to write a row:

1. Choose the section by the code that reads the variable. Use the first case
   that fits:
   - C++ and Rust source under `src/`, `h/` and `rust/` counts as the running
     programs, also when only a test program uses the code today. A variable
     that this source reads goes in section 1, even when a test or a script
     also reads it. There are two exceptions. Dice sets the Dice grant
     variables of section 2.2, and a person does not. A variable that only a
     unit test inside this source reads, for example in a Rust `#[cfg(test)]`
     module, goes in section 4.
   - A name that other software defines goes in section 7. The exception is a
     name that a library inside `rinzler` or `runtron` reads, such as `TZ`.
     That name goes in section 1. A name that only a child process reads, such
     as `PATH`, stays in section 7.
   - When code of two sections reads one name, use the section with the lower
     number.
   - Inside a section, choose the table by the subject of the variable.
     Section 6 is different: its tables are ordered by where the value comes
     from, and a variable goes in the first table that fits.
2. Keep the rows of each table sorted by name. Compare the names in lower
   case, character by character. An underscore then sorts before a letter:
   `PY_COLORS` comes before `PYTEST_ADDOPTS`.
3. Fill every cell from the code, not from the name of the variable:
   - **Values and default**: say how the text is parsed. "Exactly `1` enables
     it" and "any non-empty value enables it" are different rules. Start the
     default with "Unset:". Add "Empty:" when an empty value does not behave
     like an unset one.
   - **Effect**: short sentences with one fact in each. The first sentence
     says what the variable changes. Then say what overrides it or interacts
     with it, and what a wrong value does. In section 1, end with "Check:" and
     the log line, the file, the command or the response field that shows the
     value in effect, when one exists.
     Give every number a unit.
4. Do not write line numbers, or counts of files, tests, jobs or workflows.
   They become wrong when the code changes.
5. Keep each row at or under 1,000 characters. GitHub code search does not
   index the part of a line after 1,024 characters. Keep the whole file under
   350 KiB (358,400 bytes). GitHub code search leaves out a larger file.
6. In section 1, a new row gets *Developers*. The team that owns the code that
   reads the variable decides when a row gets *Operators*.
7. A variable that a test sets only for its own helper program needs no row.
   Add its name to the line of that test file in
   [4.6 Fixture variables](#46-fixture-variables). A variable that a workflow
   step sets only for itself, or for later steps of its job, also needs no
   row. Add its name to the line of that workflow or script in
   [6.4 Step values](#64-step-values).

## Words used here

Programs and libraries:

- **`rinzler`**: the Tron server program. It serves an OpenAI-compatible HTTP
  API.
- **`runtron`**: the Tron command-line program. It runs a model without the
  server.
- **`rinzler_proxy`**: a test build of `rinzler`. It replays recorded tokens
  and needs no FPGA card.
- **`rinzler_host`**: a build of `rinzler` that runs models on the CPU and
  needs no FPGA card. The `tron-host` package installs it on test and
  development hosts.
- **`libtron`, `libpos`**: the Tron core library and the FPGA driver library
  that the programs link.
- **platformd**: the Positron service that manages `rinzler` instances on
  production systems. It writes `/etc/rinzler/instance-N.env` and starts the
  instances through the unit `rinzler@.service`. It is not part of this
  repository.

Hardware and memory:

- **FPGA card**: the accelerator card that runs the matrix operations of the
  model.
- **Bitfile**: the FPGA image that is loaded into a card.
- **Instance**: one `rinzler` or `runtron` process that owns a fixed share of
  the server (FPGA cards, CPU cores, memory). The option `--instance id,count`
  selects the share. The packaged service runs one such process for each unit
  `rinzler@N`.
- **Physical slice**: one FPGA card with its CPU cores and its memory. An
  instance owns one or more physical slices. It is not the tool Slice.
- **Hugepage**: a memory page of 1 GiB. The programs take their FPGA buffers
  and the KV cache from a pool of hugepages.
- **NUMA node**: a group of CPU cores with its own memory.
- **Resource map**: the YAML file `resource-map.yaml`. For each server type it
  lists the FPGA cards, the CPU cores and the NUMA nodes. The repository copy
  is `config/resource-map.yaml`.
- **Arena allocator, legacy allocator**: the two allocators for hugepage
  memory. The arena allocator (`pos_heap_v2`) is the build default. The legacy
  allocator is `pos_heap`. `TRON_USE_ARENA_ALLOCATOR` selects one.

Model execution:

- **Forward pass, minibatch**: a forward pass is one run of the model over a
  group of tokens. A minibatch is a part of that group that the model computes
  together.
- **Scheduler**: in section 1, the part of `rinzler` and `runtron` that keeps
  the token tree and chooses the tokens of each forward pass. Dice and LSF
  have their own schedulers.
- **Token tree**: the tree in which the scheduler stores all token sequences.
  Sequences that start with the same tokens share nodes.
- **KV cache**: the stored attention keys and values of tokens that were
  already processed.
- **KV book**: one allocation of KV cache memory. A book holds a whole number
  of pages. One page holds the keys and values of 64 tokens.
- **Hardware attention, software attention**: attention computed on the FPGA
  cards, or on the CPU.
- **Shared thread pool**: the worker threads of one process for model work on
  the CPU. In a forward pass, some workers are main helpers for non-attention
  work. The other workers are attention workers.
- **Speculative decoding**: a generation mode in which a small draft model
  proposes a tree of candidate tokens, the draft tree. The main model then
  verifies the tree. See `TRON_USE_SPECULATION`.
- **Python tokenizer, Rust tokenizer**: the two tokenizer implementations. The
  Rust tokenizer is the Hugging Face library inside the process. The Python
  tokenizer is a slower fallback that runs a Python child process.
- **Harmony**: the prompt format of the gpt-oss models.
- **`save_tokens`**: a request parameter of `rinzler`. When it is `true`, the
  response also holds the rendered prompt, the prompt token ids and the output
  token ids.

Logs, statistics and traces:

- **Log levels**: the levels, from most detail to least, are `trace`, `debug`,
  `info`, `warn`, `error` and `critical`. A "debug log line" is a log line of
  level `debug`. A line appears when `TRON_LOG_LEVEL` is at its level or at a
  level with more detail. The default level is `debug`.
- **FUSE stats**: run-time statistics that `rinzler` and `runtron` publish as
  files through a FUSE mount. See [README.stats.md](README.stats.md).
- **Perfetto**: the tracing system that Tron uses to record timing events. See
  [README.perfetto.md](README.perfetto.md).
- **`traced`, `traced_probes`**: the two Perfetto daemons. `traced` is the
  tracing service. Programs send it trace events over a socket.
  `traced_probes` collects kernel events.

Tools:

- **Dice**: the daemon and client that queue work and grant FPGA slots on a
  shared server. See [doc/dice.md](doc/dice.md).
- **Slot**: one FPGA card with its share of the CPU cores and the memory. Dice
  grants slots. Some rows call the same unit a physical slice.
- **Shared host, legacy host**: a shared host is a server whose
  `/etc/positron/dice.yaml` sets `mode: shared`. One Dice daemon there queues
  the FPGA work of all users. Other servers are legacy hosts without a Dice
  daemon.
- **Submission, grant**: a submission is one command that a client asks the
  Dice daemon to run. The grant is the slots that the daemon gives to the
  submission while it runs.
- **Slice**: the test launcher `bin/slice`. It spreads tests over instances.
  See [doc/slice.md](doc/slice.md).
- **Launcher wrappers**: the scripts `bin/rinzler` and `bin/runtron`. They
  start the built `rinzler` and `runtron`, through Dice on a shared host.
- **LSF**: the batch scheduler that Distributed Dice and remote builds submit
  jobs to. The lab installation is OpenLava, which accepts the LSF commands.
- **Distributed Dice**: the part of Dice that runs work on another FPGA server
  through LSF. `bin/dice-lsf-submit` submits the LSF job. The LSF runner
  (`bin/dice-lsf-runner`) starts the work on that server.
- **Remote build, LSF worker**: a remote build is a build that `make` sends to
  an LSF worker through `bin/bsub-build`. An LSF worker is a server that runs
  LSF jobs.
- **Slice cost-data refresh**: the CI workflow `bench-refresh.yml`. It
  measures the run time and peak memory of each test again. It updates the
  Slice cost data in `config/test-benchmarks.json` through a PR.
- **Fake, stub**: a short program that a test writes. The code under test runs
  it in place of a real program, for example a fake `mv`.
- **Ingest**: the pipeline that converts a PyTorch model into Tron model code.
- **`gen/`**: the build output directory of the repository.
- **Nix dev shell**: the development environment that `nix develop` starts.
- **CI**: the GitHub Actions workflows under `.github/workflows`.

Words in the "Values and default" cells:

- **`atoi`, `atol`, `atoll`, `atof`, `stof`, `stoi`, `stoul`, `stoull`,
  `stoll`, `from_chars`, `strcmp`**: C and C++ library functions that read a number
  from text or compare two texts. Each row says what happens with wrong text.
  "Throws" means that the function reports an error. The process ends when no
  code handles the error.

## How to set a variable

A process gets its environment when it starts. A change to a file or to a
shell does not reach a process that is already running. Restart the program
after a change.

### A `rinzler` service instance

The Tron package installs the systemd unit `rinzler@.service`
([packaging/systemd/rinzler@.service](packaging/systemd/rinzler@.service)).
Instance `N` runs as `rinzler@N`. The unit takes variables from three places:

| Place | Applies to | Written by |
|---|---|---|
| `Environment=` lines in the unit | Every instance | The package. The unit sets `RZ_FUSE_MOUNT_PATH`, `RZ_FUSE_MOUNT_PRESCOPED` and `RZ_ENABLE_SAVE_TOKENS`. |
| `/etc/rinzler/instance-N.env` | Instance `N` | platformd. The instance does not start without this file. This repository does not say when platformd writes the file again, so an edit by hand can be lost. |
| `/opt/positron/user/config.env` | Every instance on the host | A person. The file is optional. |

Which value wins (systemd.exec(5), `EnvironmentFile=`):

- A value from one of the two files replaces the value of the same name from
  an `Environment=` line.
- The unit lists `/etc/rinzler/instance-N.env` first and
  `/opt/positron/user/config.env` second. systemd reads the files in the
  listed order, and the later file wins when both set one name.
- So a value in `/opt/positron/user/config.env` reaches every instance and
  wins over the instance file. Do not put a value there that must differ
  between instances, for example `CPUAFFINITY`, `RZ_CLI_ARGS` or
  `RZ_FUSE_MOUNT_PATH`.
- Do not set `RZ_FUSE_MOUNT_PRESCOPED` in either file. The unit already sets
  `1`. With any other value, an instance that runs with `--instance id,count`
  and a count above 1 adds a second instance directory to the FUSE stats mount
  path, for example `/var/run/rinzler/0/instance-0`.

Both files hold one `NAME=value` assignment on each line (systemd.exec(5),
`EnvironmentFile=`):

- A line that starts with `#` or `;` is a comment.
- White space inside a value is kept. `SYSTEM_CONFIG=--instance 1,2` needs no
  quotes.

A line `NAME=` sets the variable to an empty value. It does not unset the
variable. Many rows have an "Empty:" case for this.

The unit itself expands two variables to build the command line of `rinzler`:
`CPUAFFINITY` and `RZ_CLI_ARGS`. Both have a row in section 1.

To apply a change to `/etc/rinzler/instance-N.env`, restart that instance:
`sudo systemctl restart rinzler@N`. To apply a change to
`/opt/positron/user/config.env`, restart every instance. A restart ends the
requests in progress, and the instance loads its models again.

To check a change:

- The log. For a service instance, the output on stderr goes to the systemd
  journal: `journalctl -u rinzler@N`. The program also writes the log file
  `alderaan.log`. See the `TRON_LOG_DIR` row for its directory.
- The environment of the running process:
  `sudo cat /proc/<pid>/environ | tr '\0' '\n'`.
- The FUSE stats of instance `N` are mounted at `/var/run/rinzler/N`. See
  [README.stats.md](README.stats.md).

Test and development hosts that use the `tron-host` package can have one more
place. The package ships the example drop-in
[packaging/tron-host/90-rinzler-host.conf](packaging/tron-host/90-rinzler-host.conf).
After a person copies it to `/etc/systemd/system/rinzler@.service.d/` and runs
`sudo systemctl daemon-reload`, it sets `TRON_LOG_DIR` and `RZ_KV_CACHE_GB`
for every instance. The drop-in uses `Environment=` lines, so a value of the
same name in one of the two files still wins. See
[packaging/tron-host/README](packaging/tron-host/README).

### A program that a person starts

- For one command: `NAME=value bin/runtron ...`. `bin/runtron` and
  `bin/rinzler` are the launcher wrappers of section 2. On a shared host they
  queue the work through Dice. Do not start the programs under `gen/` directly
  on a shared host.
- For every later command in the shell: `export NAME=value`.

On a shared host, Dice starts the program with the environment of the person
who submitted the work. Dice changes that environment in these ways:

- It adds the grant variables of section 2.2.
- It sets `DICE_LABEL` when the submission has a label.
- It sets `PATH`, `USER`, `LOGNAME` and `HOME` when the submitted environment
  lacks them.
- It removes `DICE_DISABLE` and these variables of section 2.4:
  `DICE_ALLOW_TEST_HOST_CONFIG`, `DICE_LOCK_PATH`, `DICE_LOG_DIR`,
  `DICE_LOG_PATH`, `DICE_RUNTIME_DIR`, `DICE_SOCKET_PATH`, `DICE_STATE_PATH`
  and `DICE_TEST_HOST_CONFIG_PATH`.
- When the grant has the form of an `--instance` share, it takes the
  `--instance` choice in `SYSTEM_CONFIG` from the grant, not from the
  submitted value.

See [doc/dice.md](doc/dice.md).

### The Dice daemon

On a shared host the Dice daemon runs as the systemd service `dice.service`
([packaging/positron-dice/dice.service](packaging/positron-dice/dice.service)).
The unit sets no variable and reads no environment file. The rows of sections
2.1 and 2.4 say which variables the daemon reads from its environment. The
daemon also reads `SLICE_BOX_CAPACITY` of section 2.5.

### A test

- `bin/slice run` sets `TRON_LOG_DIR`, `SYSTEM_CONFIG` and
  `RZ_FUSE_MOUNT_PATH` for each test that it starts. `bin/slice bench` sets
  only `SYSTEM_CONFIG`. See [doc/slice.md](doc/slice.md).
- A test can declare more variables in its `ENVIRONMENT` property in
  `t/CMakeLists.txt`. CTest sets them, and `bin/slice` sets them too. A value
  that `bin/slice` sets wins over a declared value of the same name.

### A CI job

A workflow sets variables in its `env:` blocks. A step can also set a variable
for the later steps of its job: it appends a `NAME=value` line to the file
that `GITHUB_ENV` names. Repository variables and secrets are set in the
GitHub settings of the repository. Section 6 says where each CI variable comes
from.

## 1. Variables of the running programs

`rinzler`, `runtron`, `rinzler_proxy` and the libraries that they link read
these variables. Four groups are different:

- systemd reads `CPUAFFINITY` and `RZ_CLI_ARGS` when it starts the unit
  `rinzler@.service`. No Tron program reads them.
- Only the test program `t_prequant_cache` reads `POS_PREQUANT_CACHE`,
  `POS_WEIGHTS_CACHE` and `TRON_NO_PREQUANT_CACHE`. The read is in a library
  header under `h/`, so the rows are here.
- Only hardware test programs reach the read of `SUDO_USER`. `rinzler` and
  `runtron` hold the same code and never reach it.
- `rinzler` and `runtron` also read the four Dice grant variables. Their rows
  are in section 2.2.

### 1.1 System, devices and memory pages

{{table:runtime.system}}

### 1.2 Model files and caches

{{table:runtime.weights}}

### 1.3 Memory

{{table:runtime.memory}}

### 1.4 Attention

{{table:runtime.attention}}

### 1.5 Generation and scheduling

{{table:runtime.generation}}

### 1.6 Server behavior

{{table:runtime.server}}

### 1.7 Tokenizers

{{table:runtime.tokenizer}}

### 1.8 Logging

{{table:runtime.logging}}

### 1.9 Statistics

{{table:runtime.stats}}

### 1.10 Tracing

To record a trace on an installed system, run `/opt/positron/bin/fuse-capture`.
It needs no environment variable. See
[perfetto/README.fuse-captures.md](perfetto/README.fuse-captures.md).

{{table:runtime.tracing}}

## 2. Dice, Slice and the launcher wrappers

### 2.1 Dice daemon and client

{{table:dispatch.dice}}

### 2.2 Dice grant

Dice sets these variables for the program that it starts. They describe the
grant. A person does not set them.

{{table:dispatch.dice-grant}}

### 2.3 Distributed Dice

{{table:dispatch.dice-lsf}}

### 2.4 Dice test overrides

The Dice and Slice tests set these variables. One is different: `bin/dice`
itself sets `DICE_TEST_HOST_CONFIG_SPAWN_OK` when it starts a detached daemon
under pytest. The variables move the files of the Dice daemon, replace the
Dice host configuration, or let a test replace the LSF runner script.

{{table:dispatch.dice-test-hooks}}

### 2.5 Slice

{{table:dispatch.slice}}

### 2.6 Launcher wrappers

{{table:dispatch.wrappers}}

## 3. Developer tools

### 3.1 Load and request generators

{{table:tools.load-test}}

### 3.2 Perfetto tools

{{table:tools.perfetto}}

### 3.3 Ingest tools

{{table:tools.ingest}}

### 3.4 Coverage tools

{{table:tools.coverage}}

### 3.5 Lint helpers

{{table:tools.lint}}

### 3.6 Hardware tools

{{table:tools.hardware-tools}}

### 3.7 Other tools

{{table:tools.other}}

## 4. Tests

Sections 4.1 to 4.5 hold the variables that a person, a CI job or CTest sets
to control tests. Section 4.6 holds the variables that a test sets for its own
helper program.

### 4.1 Model and tokenizer files

{{table:tests.models}}

### 4.2 Hardware tests

{{table:tests.hardware}}

### 4.3 `rinzler_proxy` tests

{{table:tests.proxy}}

### 4.4 Tests of Dice, Slice and CI scripts

{{table:tests.tool-tests}}

### 4.5 Other tests

{{table:tests.other}}

### 4.6 Fixture variables

A test sets each of these variables for a helper program that the same test
starts. The helper is a fake program or a stub. Two lines differ:
`bin/ci/test/test-positron-dice-resource-map.sh` passes its variables to the
real `yq` program, and `bin/scratch-dir.sh` is a build script whose self-test
sets the variable. A few variables are only markers that the test looks for
later. Nobody sets them by hand, so they have no row of their own. The test
file explains each one.

{{table:tests.fixture}}

## 5. Build and packaging

### 5.1 `GNUmakefile` and the scripts that it runs

{{table:build.make}}

### 5.2 Remote builds and remote execution

{{table:build.remote-build}}

### 5.3 CMake

{{table:build.cmake}}

### 5.4 Nix

{{table:build.nix}}

### 5.5 Ingest build

{{table:build.ingest-build}}

### 5.6 Packaging

{{table:build.packaging}}

## 6. CI

The tables are ordered by where the value comes from. A variable goes in the
first table that fits.

### 6.1 GitHub repository variables

{{table:ci.repository-variable}}

### 6.2 GitHub secrets

{{table:ci.repository-secret}}

### 6.3 Workflow and job `env:` values

{{table:ci.workflow-env}}

### 6.4 Step values

A workflow step sets each of these variables for itself, or for the later
steps of its job through the `GITHUB_ENV` file. The value comes from a
workflow expression, from the output of an earlier step, or from a script.
The last two lines name scripts that write the `GITHUB_ENV` file for a step.
A name that several workflows set is listed one time, in the line of one of
them. These variables have no row of their own. The workflow file, or the
script that reads the variable, explains each one.

{{table:ci.step-env}}

### 6.5 Script variables

These are variables of scripts that CI runs. Each has a default that the
caller can replace. No workflow sets them, with one exception: a step of
`benchmark-golden.yml` sets `TRON_BENCHMARK_DIR`.

{{table:ci.script}}

## 7. Variables defined by other software

Other software defines these names. Tron code reads them, sets them for a
child process, or removes them from the environment of a child process. The
last column says only what Tron does. The documentation of the software that
defines a name explains its full meaning.

### 7.1 Operating system and shell

{{table:external.os}}

### 7.2 GitHub Actions

{{table:external.github-actions}}

### 7.3 Compilers and build tools

{{table:external.build-tools}}

### 7.4 Python tools

{{table:external.python}}

### 7.5 Machine learning libraries

{{table:external.ml-libraries}}

### 7.6 Network proxies

{{table:external.network}}

### 7.7 Sanitizers and coverage run times

{{table:external.sanitizers}}

### 7.8 LSF

{{table:external.lsf}}

### 7.9 Tracing

{{table:external.tracing}}

### 7.10 Other

{{table:external.other}}

## How to check this file

The baseline of this file is commit `7eddde7895` of `main` (2026-11-21). At
that commit, each variable of the file was traced to the code that reads or
sets it.

These commands print the names that the code reads and that this file lacks.
They cover C, C++, Rust, Python and shell. Run them in the root of the
repository. No output means that the commands found no missing name.

```bash
export LC_ALL=C
names=$(mktemp)
known=$(mktemp)
grep -oE '`[A-Za-z_][A-Za-z0-9_]*`' README.env-vars.md | tr -d '`' | sort -u > "$known"
{
  # C and C++
  git grep -IhoE '(secure_)?getenv *\( *"[A-Za-z_][A-Za-z0-9_]*"' -- '*.cpp' '*.hpp' '*.c' '*.h'
  # Rust
  git grep -IhoE '(env::var(_os)?|env!)\( *"[A-Za-z_][A-Za-z0-9_]*"' -- '*.rs'
  # Python, including scripts without a file extension
  git grep -IhoE '(os\.environ(\.get|\.pop|\.setdefault)?[[(]|os\.getenv\() *"[A-Za-z_][A-Za-z0-9_]*"' -- '*.py' bin perfetto
} | grep -oE '"[^"]+"' | tr -d '"' > "$names"
# Shell text, also in Make recipes and workflow steps: variables with a
# default or a required value
git grep -IhoE '\$\{[A-Z_][A-Z0-9_]*:?[-=?+]' -- '*.sh' bin perfetto rust packaging GNUmakefile .github \
  | grep -oE '[A-Z_][A-Z0-9_]*' >> "$names"
sort -u "$names" | comm -23 - "$known"
rm -f "$names" "$known"
```

The check treats every name in backticks in this file as known. One known
name is not an environment variable: `SELF_DIR` is a shell variable.
`perfetto/tronperf` and `perfetto/wrapper` assign it before they load
`perfetto/launcher-common`. It is named here so that the commands do not print
it. At the baseline commit the commands print no name.

The commands do not find every read. They miss these cases:

- A name that reaches the read through a helper function, a constant or a
  table. Some Python scripts hold the name in a constant such as
  `DICE_GRANT_ID_ENV`. For those, search for the constant.
- A shell read without a default or a required value, such as `$NAME`.
- A Python read that writes the name in single quotes, such as
  `os.environ['NAME']`, or on the line after the opening bracket.
- A Make variable (`NAME ?= value`), a CMake read (`$ENV{NAME}`), a Nix
  attribute and a workflow `env:` block.
- A variable that Tron only sets for a child process.
