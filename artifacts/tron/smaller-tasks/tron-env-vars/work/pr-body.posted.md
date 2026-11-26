## Short version

This PR adds `README.env-vars.md`, one file that lists the 529 environment variables that the Tron source code reads or sets. Support engineers get a part on how to set a variable for a service instance of `rinzler` (the Tron server program), and a section on the 70 variables that the running programs read. `AGENTS.md` gains a rule: a PR that changes a variable also updates the file.

Closes #4338.

## Background

Tron code reads environment variables in C++, Rust, Python, shell, Make, CMake, Nix and workflow YAML. No file lists them. The largest list on `main` is a table of 8 names in `README.proxy.md`. Issue #4338 asks for one central document.

Two groups need the list:

- Support engineers need to know which variables exist, which text each one accepts, and what happens when a variable is unset.
- Developers need one place to record a variable when they add or change one. Issue #1971 proposes one configuration scheme for variables and command-line options. The list shows which variables exist today.

## Words used here

| Term | Meaning |
|---|---|
| Row | One table line of `README.env-vars.md`. It describes one variable. |
| Running programs | `rinzler`, `runtron` (the Tron command-line program) and the libraries that they link. Section 1 of the file holds their variables. |
| Operators, Developers | The two labels of the "For" column in section 1. Operators marks a variable that a support engineer may need to set or check on a deployed system. Developers marks every other variable of section 1. |
| Baseline | Commit `7eddde7895` of `main` (2026-11-21). The rows describe the code of this commit. |
| Blind audit | A check in which the checker first derives the facts of a variable from the code, and only then grades the row. |

## How to review this PR

**Are the rows of the code that you own right?**

- `README.env-vars.md`, section 1: each of the 70 rows says how the text is parsed, what happens when the variable is unset, and what the value changes. Read the rows of the code that you own.
- Every row comes from reading the code at the baseline. No row was confirmed by a run on hardware.
- Verification: the blind audit in [Verification].

**Is each Operators label right? Reviewers decide.**

- `README.env-vars.md`, column "For" of section 1: 19 rows say Operators and 51 say Developers.
- The first labels follow one rule. A row says Operators only when a packaging file uses the variable, or another Tron document describes the variable for deployed systems. The code cannot show that a person may set a variable on a customer system. So the file says that the team that owns the reading code decides the label.
- Rows that the checkers doubted, in both directions: `RZ_CHAT_TEMPLATE_KWARGS`, `TIKTOKEN_ENCODINGS_BASE`, `TRON_TOKENIZE_PY`, `TZ`, `SPDLOG_LEVEL`, `TRON_ATTN_STATS` and `POS_HUGEPAGE_PATH` say Developers. `TRON_LOG_LEVEL` and `USE_HW_ATTN` say Operators, and only changelog entries describe them outside this file.
- Verification: Open. The owners of the reading code decide.

**Do the "Rules for developers" give one answer for a new variable?**

- `README.env-vars.md`, "Rules for developers": the rules say which changes need an update, which section a row goes in, and what each cell holds.
- `AGENTS.md`, "Environment variables": the rule that sends a developer or an agent to those rules.
- Try three cases: a new `std::getenv` under `h/tron/scheduler`, a new `${NAME:-default}` in a script under `bin/ci`, and a variable that a test sets for its fake program.
- Verification: Open. Reviewers decide whether every PR can follow the rules.

## Verification

Every result below comes from reading the checkout at head `6d2c76796d`, with base `main` at `7eddde7895`, on 2026-11-22. The PR changes four files and no code. No build, test run, token comparison or performance measurement applies.

**Checks on the files**

| Check | Result |
|---|---|
| Pre-commit hooks of lefthook (the Git hook runner of the repository) that match the changed files: `whitespace`, `lock-freshness`, `agent-guidance` | pass |
| `bin/ci/lint-agent-guidance.py` and its self-test (20 cases) | pass |
| Markdown parse with markdown-it-py 3.0.0, the version that CI pins | 52 tables, 0 table lines outside a table |
| In-page links of the file | 11, 0 broken |
| Rows longer than 1,000 characters (GitHub code search cuts a line at 1,024) | 0 |
| Tables not sorted by name | 0 of 52 |

**Completeness**

| Check | Result |
|---|---|
| Names that a regular-expression scan finds in all tracked files | 344. 339 are in the file. 5 are not environment variables, and each has a recorded reason. |
| Names in the file | 529. 405 have a row. 124 are in the lists of sections 4.6 and 6.4. |
| Names of those two lists that occur in the file that their list line names | 124 of 124 |
| Names in the file that no other tracked file holds | 3: `LNAME` and `USERNAME` (Python `getpass.getuser()` reads them), `OMP_NUM_THREADS` (`nproc` reads it) |
| The check commands in the last section of the file | find 291 names and print none as missing |

What the tables say:

- The scan finds no variable that the file lacks.
- 185 names of the file are not in the scan. They reach the read through a helper function, a constant, or a form that the scan does not match, such as a workflow `env:` block.
- The check commands cover C, C++, Rust, Python and shell. The file lists the cases that they miss.

**Accuracy**

| Check | Result |
|---|---|
| Blind audit of 50 rows drawn at random from the file (fixed seed, 20 of them from section 1) | 49 correct, 1 imprecise, 0 wrong |

What the table says:

- The imprecise row is `TZ`. It did not say that the time of day in log lines also follows the variable. The head holds the corrected row.
- Before this sample, each of the 405 rows was derived again from the code by a checker that did not write it.
- 53 statements about failure cases come from reading the code and need a run to confirm. [Open items] lists the ones that touch Operators rows.

## Open items

**Operators labels. Reviewers decide.** See the second question of [How to review this PR].

**Test-only and step-only names. Reviewers decide.** 89 variables that a test sets for its own helper program, and 35 values that a workflow step sets for itself, have no row. Sections 4.6 and 6.4 list them by file. Decide whether these lists stay. Without them the file is smaller, and a test change needs no edit here.

**File size. Reviewers decide.** The file has 309,455 bytes. GitHub code search leaves out a file over 350 KiB (358,400 bytes). The room left is 48,945 bytes, est. 70 rows at the present mean row length. The other choice is two files, for example sections 1 to 5 and sections 6 to 7. A split after the merge breaks links to the headings.

**Review routing. Reviewers decide.** `.github/CODEOWNERS` has no entry for the file, so the catch-all owner reviews every later edit. The rows describe code of several teams.

**No CI check compares the file with the code.** The last section of the file holds commands that print names without a row. A CI job could run them. This PR adds no such job.

**Other documents that disagree with the code.** The rows follow the code. Where another document says something else, this PR does not change that document. Example: `README.tokenizers.md` names `USE_RUST_TOKENIZER`, and the code reads `USE_PYTHON_TOKENIZER`. No issue tracks these places yet.

**Pending measurements.** Each needs one start on a test host:

- Does an instance fail to start when `CPUAFFINITY` is unset? The row says yes, from systemd.service(5) and the `taskset` parser.
- Does `POS_NR_HUGEPAGES=0` or `POS_1GB_PER_NUMA=0` stop the process at startup? The rows say yes, from the code path.
- Does `rinzler` abort when the mount of its statistics files under `RZ_FUSE_MOUNT_PATH` fails? The row says yes, from the code path.
- Where does a production instance write `alderaan.log`? The packaged unit does not set `TRON_LOG_DIR`. platformd (the Positron service that starts the instances) decides this, and it is not in this repository.
- Does a program outside this repository read the run file under `RZ_RUNFILE_DIR`? The repository holds only test readers.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
