## Short version: purpose

`check_accept8.py` checks the output of a trace run of the runner `bwx8` on CRB, as a part of the acceptance of that runner. For every trial of a plan file it applies three rules of `test_runner8.py` and three checks of its own, and it prints one line per trial with the rates of the target windows. Its exit status is 0 only when no check found a problem.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Design**: the file `tackle-8mb.md`, the design of the investigation into the buffer size of 8 MiB. Its Stage 1 lists the acceptance checks that the runner must pass before measurements [Ref1].
- **Decisions note**: the file `DECISIONS-bwx8.md` in the folder of this script. It fixes the plan file, the options and the output rows of `bwx8` [Ref2].
- **Trial mode, trial**: a mode of `bwx8` with one worker thread. A trial is one timed sequence of windows that one line of a plan file describes.
- **Plan file**: a text file that `bwx8` reads. Its first three lines are header lines. Every other line gives one trial in 11 fields that are divided by single spaces: `trial`, `cond`, `rep`, `prev`, `pfx`, `pred`, `tgt`, `nwin`, `win_ms`, `count` and `bins`.
- **Window**: one timed stretch of one kernel inside a trial. It runs whole passes over its range and ends at the first clock read at or after its requested duration.
- **Phase**: the role of a window in a trial: `prev` (previous activity), `prefix`, `pred` (predecessor) or `target`.
- **Target window**: a window of the phase `target`. Only the rates of target windows are printed here.
- **Timed sequence**: all windows of one trial, from the start of the first to the end of the last. No page reading, output or allocation lies inside it.
- **Gap**: the time between the clock read that ends one window and the clock read that starts the next.
- **Bin**: a record inside a target window: at a clock read about every 10 ms the worker stores the time and the bytes so far.
- **Counter mode**: the field `count` of a plan line: `closed`, `open` or `read`. With `read` the worker reads hardware counters at the borders of the target windows.
- **Trace run**: a run of `bwx8` with the option `--trace`. The runner then logs every event of its wrapper code in memory and prints the log as `TR` rows. The rates of a trace run are not used as results [Ref2].
- **`M`, `P`, `W`, `B`, `E`, `X`, `TR` rows**: the row kinds of the trial mode. `M`: one value that describes the process. `P`: the page state before or after a trial. `W`: one window with its bytes and its two times. `B`: one bin. `E`: the summary of a trial. `X`: a failure that the runner reports. `TR`: one event of the trace.
- **Worker thread, controlling thread**: the worker thread runs the kernels on its own CPU. The controlling thread starts it and waits on another CPU.
- **Minor page fault**: an access to a memory page that Linux first has to map, without reading from a disk.
- **Context switch**: Linux takes the CPU from a thread. It is voluntary when the thread waits for something, and involuntary when Linux takes the CPU from a thread that still wants to run.
- **`sink_ok`**: a field of the `E` row. It is 1 when the last old read of the trial left the sum of its range in the variable that takes the result, 0 when not, and `NA` when the trial ran no old read.
- **Docstring**: a text literal at the top of a Python file, class or function that describes it.

## Main flow

1. The script imports the rule functions of `test_runner8.py` ({L6-7}).
2. For each pair of a csv file and a plan file it reads the rows of the csv file by kind, the trials of the plan file, and the `minflt` lines, and it prints one heading ({L10-15}).
3. For each trial it applies the trace rule and the window rule, and the bin rule when the plan asks for bins ({L16-21}).
4. It adds its own checks: the `TR` rows are numbered in order, the timed sequence had 0 minor page faults, and the buffer lies fully on huge pages before and after the trial ({L22-25}).
5. It prints one line for the trial with the rates of the target windows, fields of the `E` row, the `X` rows and the problems ({L26-31}).
6. It prints the total number of problems and sets the exit status ({L32-33}).

## Behavior a reader must know

- The script reads files and measures nothing. The rates that it prints come from the `W` rows: bytes divided by the time between the two clock reads of the window ({L28}).
- The rules themselves are in `test_runner8.py`. This script only applies them to files from CRB. In that test file each rule is also run on changed rows, where it must report a problem [Ref3].
- An `X` row is printed and not counted as a problem ({L26}, {L30}).
- The coverage check expects 8192 kB, so it fits a buffer of 8 MiB only ({L25}).
- A csv file of a run without `--trace` has no `minflt` lines. Every trial of it gets a problem ({L23}).
- Three cases end the script with a Python error and no result line: a file that cannot be read, a trial without an `E` row ({L18}), and a trial that does not have exactly two `P` rows ({L24}).
- Without arguments the script prints 0 problems and ends with exit status 0. A last csv file without a plan file is skipped ({L10}).
- The decisions note records the use of this script on 2026-11-15: the trace runs of two result folders, 18 trials on the CPUs 2 and 41, 0 problems [Ref2].

## References

- [Ref1] The design: the file `tests/2026-11-15-tackle-8mb/report/tackle-8mb.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`, section "Stage 1: establish that the runner can measure the effect", item 1 "Code and accounting" and item 4 "Transition fidelity", and section "One trial".
- [Ref2] The decisions note: the file `code/bwx8-2026-11-14/DECISIONS-bwx8.md` of the same repo. Section "Plan file": the fields of a plan line. Section "bwx8 command line": the option `--trace`, the rules of the timed sequence and the table of the output rows. Section "Changes after the review round": the line `# minflt`. Section "CRB acceptance, 2026-11-15": the trace runs that were checked with this script.
- [Ref3] The file `code/bwx8-2026-11-14/test_runner8.py` of the same repo: its header text, and the functions `rows_of`, `of_trial`, `plan_lines`, `events_of`, `expected_windows`, `window_problems`, `bin_problems` and `trace_problems`.
- [Ref4] The source of the runner: the file `code/bwx8-2026-11-14/bwx8.c` of the same repo. Its function `emit_trial` prints the rows of one trial and the line `# minflt`, with the comment on its meaning. The worker prints the comment lines with the column names of each row kind.
