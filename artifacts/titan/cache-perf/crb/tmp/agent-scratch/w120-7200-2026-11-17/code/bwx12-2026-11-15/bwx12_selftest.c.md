# `bwx12_selftest.c` explained

- Source file: `bwx12-2026-11-15/bwx12_selftest.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 711 lines, 29959 bytes).
- sha256 of the source when this page was built: `d27ca7aa8e706ec1e79c10258539e8c48fb8249159c38a15069af755fed8b72e`.
- Role in the whole-chip test: Self-test of the runner bwx12. Runs at build time, never in a timed run.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

This file is the self-test of bwx12 (the runner program of the whole-chip test): it checks what each of the 55 kernels does to memory, and the records and output rows of the trial mode. It runs only when bwx12 is started with `--selftest`, which the build script build12.sh does once after the build.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Whole-chip test**: the run of 2026-11-17 on the whole chip. Of bwx12 it timed six kernels: `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **bwx8, bwx10**: two more older versions of the runner. The file comment of bwx12.c gives the order: bwx10 is bwx8 plus round 3, bwx11 is bwx10 plus round 4, bwx12 is bwx11 plus round 5.
- **Round 3, round 4, round 5**: three sets of additions to the runner, all dated 2026-11-15 in bwx12.c. In this file "round" never means a repeat of a kernel sequence.
- **Kernel, kind**: a kernel is one of the 55 loop functions of bwx12 in the table `kernels[]`: a read loop, a write loop or a copy loop. Its kind is its type in that table: `T_READ` (a read loop that returns nothing), `T_OLDREAD` (a read loop that returns a sum), `T_WRITE` or `T_COPY`. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the inner loop of the benchmark that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **Self-test**: the checks of this file. The command `bwx12 --selftest` runs them. It measures no rate.
- **Timed run**: a start of bwx12 that measures rates, in the interval mode or in the trial mode.
- **Interval**: one timed measurement inside a process.
- **Interval mode**: the mode of bwx12 that the whole-chip test uses (option `--seq`). Each thread runs a sequence of kernels, and the function `worker` of bwx12.c times each kernel.
- **Warm-up**: one call of the kernel on its whole range that `worker` of bwx12.c makes before each interval. It is not timed.
- **First touch**: the first write to the pages of a new mapping. Linux gives a page its physical memory at that moment. In the interval mode each thread writes its whole buffer once with `k_write` before any read. In the whole-chip test the thread is pinned to its CPU before this write [Ref1] [Ref6].
- **`--stop common`, common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s). With this rule, and a range of 2 MiB or more, `worker` of bwx12.c calls the kernel on one chunk of 2 MiB at a time and reads the clock after each chunk.
- **Trial mode**: the other mode of bwx12 (option `--trial`). One pinned worker thread runs the trials of a plan file. The whole-chip test does not use it.
- **Plan**: the list of trials that the trial mode reads from a file. One line of the plan is one `struct trial`. The tests of this file write such a structure directly, without a file.
- **Worker record**: the `struct tw` of bwx12.c. It holds the state of the thread that runs the trials: the buffer, the counter group and the trace. In the self-test the main thread runs the trials.
- **Trial, window, target window**: a trial is a list of timed windows that run one directly after the other: 1 window of previous activity, 4 prefix windows, 1 predecessor window, then the target windows. One window runs one kernel on one range for a requested time.
- **Window record**: the `struct win` of one window. Its plan fields (kernel, range size, passes between two clock reads, duration, bin storage) are set before the trial. Its result fields (bytes, start time, end time, number of bins) are written by the timed sequence.
- **Bin**: a record inside a target window: one clock read and the bytes since the start of the window. The requested width of a bin is 10 ms.
- **`timed_sequence`, `timed_sequence_hot`**: the two functions of bwx12.c that run the windows of a trial. With the option `--hot-copy` the second one runs. It copies the plan fields of a window record to local variables before the start clock read of the window.
- **Sink, sink check**: the sink is the variable that receives the sum that an old read kernel returns. After a trial, the sink check compares it with the expected sum: 1 = equal, 0 = not equal, -1 = the trial ran no old read.
- **Evict step**: option `--evict-mb N` of the trial mode. Before the first trial the worker writes N MiB of other memory twice. The stated purpose is that the lines of the benchmark buffer leave the caches.
- **Trace, `EV_KERNEL_FIRST`**: the trial mode can keep a list of the events of a trial (option `--trace`). `EV_KERNEL_FIRST` is the event of the first kernel call of a window.
- **Counter group, multiplexed**: the counter group holds the hardware event counters that the runner opens for a thread. Linux reports how long the group was enabled and how long it ran. "Multiplexed" means here: in a target window the running time is below the enabled time.
- **Counter state**: what a trial does with the counter group. The plan sets it in the field `count`, and the last field of the E row prints it. `closed`: no counter group is open. `open`: the group is open, and the timed sequence does not read it. `read`: the timed sequence reads the group at the borders of the target windows. `fail`: the plan asked for `open` or `read`, and an event did not open.
- **Rows of the trial mode**: `emit_trial` of bwx12.c prints them. The first field is the kind of the row. P is a page snapshot before (`pre`) or after (`post`) the trial. W is one window. B is one bin. C holds the counter differences of one target window. E holds the totals of the trial. X is a defect that the runner found. They are not the I, T, P and C rows of the whole-chip csv files.
- **csv file**: a text file whose rows hold fields separated by commas. Here: the output file of one bwx12 process [Ref6].
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Page snapshot**: the page state of the buffer that the trial mode reads before and after a trial: the size in kB and the kB in huge pages from `/proc/self/smaps`, and four counters from `/proc/vmstat`. A value that is not available is -1 and is printed as `NA`.
- **Word**: 8 bytes, one `uint64_t`.
- **MiB**: 2^20 bytes (1,048,576 bytes).
- **Page, `page_bytes`**: the unit of memory protection. `page_bytes` holds its size in bytes. It was 4096 B in the self-test of the CRB build [Ref3].
- **PROT_NONE page**: a page that the process may neither read nor write. A load from it or a store to it is a fault.
- **Fault, SIGSEGV**: a fault is a forbidden memory access. Linux answers it with the signal SIGSEGV. Without a handler the signal ends the process.
- **Guarded buffer**: a test buffer with one PROT_NONE page directly before it and one directly after it.
- **Stand-in kernels**: on a machine that is not AArch64 (the 64-bit Arm instruction set), plain C loops take the place of the NEON and asm kernels. The header line of the self-test output says which build ran.
- **Objdump listing**: the disassembly text of every kernel of the binary. build12.sh writes it to the file listing.txt, and the script check_listing12.py checks it.
- **nop, vector add, prefetch**: a nop is an instruction that does nothing. A vector add adds two vector registers. A prefetch (`prfm`) asks for a cache line: it reads no data and never faults. None of the three changes memory.
- **d8-d15**: the low halves of the Arm vector registers v8 to v15. The Arm calling convention (AAPCS64) requires that a function gives them back unchanged.
- **build12.sh**: the build script of bwx12. It compiles bwx12.c, runs `bwx12 --selftest`, and writes the objdump listing.
- **taskset**: a Linux tool that starts a program limited to a list of CPUs.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **go.sh, go2.sh, rx.sh, spec file**: scripts of the whole-chip test. go.sh and go2.sh are the drivers. They call rx.sh, which starts one bwx12 process per line of a spec file [Ref5] [Ref6]. A spec file is a text file with one line per bwx12 process: a tag, the character `|`, and the arguments of the process.

</details>

## Main flow

1. bwx12.c includes this file directly before its `main`. `main` reads the page size into `page_bytes`, removes the CPUs above 119 from the allowed set of the process, and calls `selftest` when an argument is `--selftest` [Ref1]. In every other case no function of this file runs (line 676).
2. `selftest` makes the output line-buffered, prints the header line, and stops with the value 2 if the page size is not a multiple of 256 B (lines 678-684).
3. It sets the three buffer sizes (1 page, 3 pages, 1 MiB) and the two block offsets (first and last 256 B of a page) (lines 685-688).
4. `test_round5` checks the table `kernels[]`: the 26 names of round 5, their kinds, and 55 entries in total (line 690).
5. For each of the 55 kernels: `test_size` on the three sizes, `test_block` at the two offsets, and for a read kernel `test_touch` (lines 692-699).
6. Five checks of the trial mode follow: `test_trial`, `test_trial_hot`, `test_hot_touch`, `test_evict`, `test_emit` (lines 700-708).
7. `selftest` prints `# failures=N` and returns 1 if a check failed, else 0. `main` returns this value as the exit status (lines 709-710).
8. build12.sh stores the output in the file selftest-bwx12.txt. It stops the build with status 4 when the exit status is not 0 [Ref2].

## Behavior a reader must know

- The self-test runs only with `bwx12 --selftest`. build12.sh starts it once after the build [Ref2]. The whole-chip test starts bwx12 with `--seq` and never with `--selftest` [Ref6]. So no function of this file runs between two clock reads of a timed run.
- The self-test computes no rate. Only the checks of the trial mode read the clock.
- Result for the bwx12 binary of the whole-chip test: the self-test output of the CRB build has 852 lines, 457 `pass` lines, no `FAIL` line, and the last line `# failures=0`. Its header line says `page_bytes=4096 kernels=55 (aarch64)` [Ref3]. build.txt of the same build records exit status 0 and the sha256 of the binary [Ref4]. go.sh and go2.sh require that sha256 [Ref5]. The binary bwx12 is not in the local folders. Its sha256 is known only from records such as build.txt, go.sh and go2.sh.
- What the kernel checks prove for the six kernels of the whole-chip test (`oldread`, `read`, `asmread`, `read_nop96`, `read_nop256`, `read_1pl`): the buffer is unchanged, no byte within one page outside the test buffer is loaded or stored, and at least one byte of each page of a 3-page range is accessed. For `oldread` in addition: the returned sum equals the sum of all words, for 4096 B, 12288 B and 1 MiB [Ref3].
- The sizes differ from the whole-chip test. With the page size of CRB (4096 B) the kernel checks call a kernel on 256 B, 4096 B, 12288 B and 1 MiB. The trial checks call a kernel on 65536 B and 1 MiB. The whole-chip test (`--bytes 256M`, `--stop common`) calls a kernel on the whole buffer of 256 MiB for the warm-up, and on chunks of 2 MiB between the two clock reads of an interval [Ref1] [Ref6]. No check of this file uses one of these two sizes.
- The whole-chip test runs one more kernel function of this binary, outside every timed interval. `worker` of bwx12.c calls `k_write` (the kernel `write`) once on the whole new buffer of each thread, as the first touch [Ref1]. The self-test checks `write` as a write kernel: after one call on 4096 B, 12288 B and 1 MiB, every word of the buffer holds the value that `call` passed to the kernel [Ref3].
- What the kernel checks cannot prove. They see three things only: the content of memory after the call, a fault, and the sum that an old read kernel returns. They cannot see which bytes inside a page a read kernel without return value loads, a nop, a vector add, the order of loads and stores, the speed, or the saving of the registers d8-d15. The objdump listing is the evidence for the instructions [Ref7].
- No check runs the interval mode. The function `worker` of bwx12.c timed the kernels in the whole-chip test. Its byte count, its clock reads and its stop rule are not tested by this file.
- The five trial checks (`test_trial`, `test_trial_hot`, `test_hot_touch`, `test_evict`, `test_emit`) cover code of the trial mode. The whole-chip test does not use the trial mode, `--hot-copy` or `--evict-mb` [Ref6].
- In `test_size` and `test_block` no SIGSEGV handler is installed. A kernel that loads from or stores to a PROT_NONE page there ends the process. No result line follows, and the last `call` line of the output names the kernel.
- A failed check does not stop the self-test. It adds 1 to `failures`, and the exit status becomes 1.
- The self-test runs in the main thread. `test_hot_touch` adds one helper thread. No thread is pinned to one CPU. The test buffers come from `guarded`: plain `mmap` memory, with no request for huge pages.
- On a machine that is not AArch64 the self-test checks the stand-in kernels, not the real ones. The header line of the output says which kernels ran.

## Call sequence in the whole-chip test

- `build12.sh`: on CRB, 2026-11-15: builds bwx12, then starts `bwx12 --selftest` once
  - `bwx12.c:main`: sets `page_bytes`, calls `selftest` for the argument `--selftest`
    - `selftest` (line 676): prints the header, runs every check, returns 0 or 1
      - `test_round5` (line 559): 26 names and kinds in `kernels[]`, 55 entries
        - `trial_check` (line 266): prints a result line that starts with `trial`
      - `test_size` (line 147): per kernel, 3 sizes: memory after one call on a whole buffer
        - `guarded` (line 108): buffer between two PROT_NONE pages
        - `pattern` (line 124): test value of each word
        - `calling` (line 129): prints the `call` line before the kernel runs
        - `bwx12.c:call`: chooses the argument list by the kind of the kernel
          - `bwx12.c:k_<name>`: the kernel under test, for example `k_oldread`, `k_read`, `k_asmread`
        - `is_read` (line 141): selects the checks of a read kernel
        - `check` (line 134): prints `pass` or `FAIL`, counts a failure
        - `unguard` (line 119): releases the buffer
      - `test_block` (line 192): per kernel, 2 offsets: 256 B at a page start and a page end
        - `bwx12.c:call`: runs the kernel on the 256 B
      - `test_touch` (line 235): read kernels only: one of 3 pages is PROT_NONE
        - `bwx12.c:call`: runs the kernel on the 3 pages, it must fault
          - `on_fault` (line 224): on SIGSEGV: stores the fault address, jumps back to `test_touch`
      - `test_trial` (line 286): trial mode: window records, bins, sink check
        - `kernel_named` (line 273): indexes of `oldread`, `read`, `asmread`
        - `bwx12.c:trial_windows`: number of windows of the plan (9)
        - `bwx12.c:window_bins`: bins per target window (3)
        - `bwx12.c:set_windows`: fills the plan fields of the window records
        - `bwx12.c:run_trial`: one trial, four times with changed plans
          - `bwx12.c:timed_sequence`: runs the windows: kernel calls and clock reads
            - `bwx12.c:call`: one pass of `asmread`, `oldread` or `read`
        - `bwx12.c:first_multiplexed`: checked on three readings written in the test
      - `test_trial_hot` (line 360): the same window checks with `plan.hot_copy = 1`
        - `bwx12.c:run_trial`: one trial, two times
          - `bwx12.c:timed_sequence_hot`: runs the windows on local copies of the plan fields
      - `test_hot_touch` (line 516): compares the faults of the two timed functions
        - `hot_touch_run` (line 466): called twice: `hot` = 0, then `hot` = 1
          - `toucher` (line 441): second thread: makes the record page PROT_NONE for 20 ms
          - `bwx12.c:run_trial`: one 200 ms window of `asmread` on 1 MiB
            - `on_touch` (line 423): on SIGSEGV in the record page: counts, makes the page usable
      - `test_evict` (line 541): the evict step with 4 MiB
        - `map_lines` (line 528): mapping count before and after the step
        - `bwx12.c:evict_step`: maps 4 MiB, writes it twice, unmaps it
      - `test_emit` (line 628): output rows of a hand-written trial record
        - `emitted` (line 605): called twice: with three defects, then without
          - `bwx12.c:emit_trial`: prints the P, W, C, X and E rows into memory
        - `has_line` (line 594): looks for an expected row in the printed text

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `guarded` | 108-117 | Maps `n` words between two PROT_NONE pages and returns the address of the words. | - | no |
| `unguard` | 119-122 | Unmaps a guarded buffer together with its two PROT_NONE pages. | - | no |
| `pattern` | 124-127 | Returns the test value of word `i`: a different value for every `i`, changed by `salt`. | - | no |
| `calling` | 129-132 | Prints `call,<kernel>,<bytes>` before a kernel runs. A kernel that ends the process is named by this line. | - | no |
| `check` | 134-139 | Prints one result line of a kernel check (`pass` or `FAIL`) and counts a failure. | - | no |
| `is_read` | 141-144 | True for the kinds `T_READ` and `T_OLDREAD`. | - | no |
| `test_size` | 147-188 | One kernel on a whole guarded buffer. Read: buffer unchanged. Old read: right sum. Write and copy: every word stored. | `guarded`, `pattern`, `calling`, `bwx12.c:call`, `is_read`, `check`, `unguard` | no |
| `test_block` | 192-222 | One kernel on 256 B at a page start or end: no store outside the block, no load in the PROT_NONE page beside it. | `guarded`, `pattern`, `calling`, `bwx12.c:call`, `is_read`, `check`, `unguard` | no |
| `on_fault` | 224-230 | SIGSEGV handler of `test_touch`: stores the fault address and jumps back to `sigsetjmp`. | - | no |
| `test_touch` | 235-264 | Read kernel on 3 pages with one page PROT_NONE: it must fault in that page, for each of the 3 pages. | `guarded`, `calling`, `bwx12.c:call`, `check`, `unguard` | no |
| `trial_check` | 266-271 | Prints one result line that starts with `trial` and counts a failure. | - | no |
| `kernel_named` | 273-283 | Returns the index of a kernel name in `kernels[]`, or ends the process with status 2. | - | no |
| `test_trial` | 286-355 | Runs four trials through `run_trial`. Checks the window records, the bins, the sink check and `first_multiplexed`. | `kernel_named`, `guarded`, `bwx12.c:trial_windows`, `bwx12.c:window_bins`, `trial_check`, `bwx12.c:set_windows`, `bwx12.c:run_trial`, `bwx12.c:first_multiplexed`, `unguard` | no |
| `test_trial_hot` | 360-416 | The window checks of `test_trial` with `plan.hot_copy = 1`, so `timed_sequence_hot` runs. Also: the plan fields stay unchanged. | `kernel_named`, `guarded`, `bwx12.c:trial_windows`, `bwx12.c:set_windows`, `bwx12.c:run_trial`, `trial_check`, `unguard` | no |
| `on_touch` | 423-433 | SIGSEGV handler of `test_hot_touch`: counts a fault in the page of the window record and makes the page usable. | - | no |
| `toucher` | 441-460 | Second thread: waits for the first kernel call of the window, then makes the record page PROT_NONE for 20 ms. | `bwx12.c:now_ns` | no |
| `hot_touch_run` | 466-514 | One 200 ms window of `asmread`. The window record lies in its own page, and a second thread makes this page PROT_NONE. | `kernel_named`, `guarded`, `bwx12.c:set_windows`, `toucher`, `bwx12.c:run_trial`, `unguard` | no |
| `test_hot_touch` | 516-524 | Runs `hot_touch_run` with both timed functions: `timed_sequence` must fault in the record page, `timed_sequence_hot` must not. | `hot_touch_run`, `trial_check` | no |
| `map_lines` | 528-539 | Counts the lines of `/proc/self/maps`: the number of memory mappings of the process. | - | no |
| `test_evict` | 541-553 | Runs `evict_step` with 4 MiB: no error, clock reads in order, the same number of mappings afterwards. | `map_lines`, `bwx12.c:evict_step`, `trial_check` | no |
| `test_round5` | 559-591 | Each of the 26 kernel names of round 5 must stand once in `kernels[]` with its kind. The table must have 55 entries. | `trial_check` | no |
| `has_line` | 594-601 | True when a text holds the given string as a complete line. | - | no |
| `emitted` | 605-624 | Returns the text that `emit_trial` prints for a given plan and record. A memory stream takes the place of `stdout`. | `bwx12.c:emit_trial` | no |
| `test_emit` | 628-674 | Compares the C, P, E and X rows that `emit_trial` prints for a hand-written record, with and without three defects. | `kernel_named`, `emitted`, `has_line`, `trial_check` | no |
| `selftest` | 676-711 | Entry point of `bwx12 --selftest`: runs all checks, prints `# failures=N`, returns 0, 1 or 2. | `test_round5`, `test_size`, `test_block`, `is_read`, `test_touch`, `test_trial`, `test_trial_hot`, `test_hot_touch`, `test_evict`, `test_emit` | no |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `bwx12-2026-11-15/bwx12_selftest.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (711 lines, 29959 bytes, sha256 `d27ca7aa8e706ec1e79c10258539e8c48fb8249159c38a15069af755fed8b72e`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### File comment: checks added for bwx12 (round 5) (lines 1 to 23)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/* bwx12+ */` | Comment: the marker `bwx12+`. It starts a block of text that was added for bwx12. The next line with `bwx12-` ends the block (line 23). |
| 2 | `/*` | Opens the comment that describes the additions of bwx12. |
| 3 | ` * bwx12_selftest.c - bwx11_selftest.c plus the checks of round 5. Every` | Comment: `bwx12_selftest.c` is `bwx11_selftest.c` plus the checks of round 5. Round 5 is the set of additions that made bwx12 out of bwx11, the runner version before: 26 new kernels. A kernel is one inner loop of the benchmark that reads, writes or copies memory. |
| 4 | ` * addition stands between a line "bwx12+" and a line "bwx12-". Without these` | Comment: every addition stands between a line `bwx12+` and a line `bwx12-`. |
| 5 | ` * blocks this file is bwx11_selftest.c byte for byte.` | Comment: without the `bwx12` blocks the text is `bwx11_selftest.c` byte for byte. |
| 6 | ` *` | Comment: an empty line of the comment. |
| 7 | ` * The loop over kernels[] gives each of the 26 new kernels the checks of its` | Comment: the loop over the table `kernels[]` in the function `selftest` gives each of the 26 new kernels the checks of its kind. The kind is the type of the kernel in that table: read, write or copy. The spec files of the whole-chip test (`like.spec`, `cfwd.spec` and `crev.spec`) name six kernels. Of these six, only `read_nop256` belongs to the 26. |
| 8 | ` * kind. The 20 read kernels: buffer unchanged, no guard page touched, a fault` | Comment: the checks of the 20 new read kernels: the buffer is unchanged, no guard page is touched, and the kernel faults ... A guard page is a page next to the test buffer that the process may neither read nor write. |
| 9 | ` * in each page of a 3-page range. The 4 write kernels: every word equals v,` | Comment: ... in each page of a 3-page range. The checks of the 4 new write kernels: every word equals `v`, the value that the kernel must store, ... |
| 10 | ` * and only the 256 B of a block are written. The 2 copy kernels: destination` | Comment: ... and only the 256 B of a block are written. The checks of the 2 new copy kernels: the destination ... |
| 11 | ` * equals source, source unchanged, and only the 256 B of a block are copied.` | Comment: ... equals the source, the source is unchanged, and only the 256 B of a block are copied. |
| 12 | ` * The kind comes from kernels[]. test_round5: every new kernel is in` | Comment: the kind comes from `kernels[]`. The function `test_round5` checks that every new kernel stands in ... |
| 13 | ` * kernels[] once, with the kind that its name says, and kernels[] has 55` | Comment: ... `kernels[]` exactly once, with the kind that its name says, and that `kernels[]` has 55 ... |
| 14 | ` * entries. A write kernel entered as a read kernel would pass the read` | Comment: ... entries. The reason for this check: a write kernel that was entered as a read kernel would pass the read ... |
| 15 | ` * checks only by accident, so this check stands before them.` | Comment: ... checks only by accident. So this check runs before them. |
| 16 | ` *` | Comment: an empty line of the comment. |
| 17 | ` * Limits, in addition to the limits below. The test cannot see the vector` | Comment: the limits of the new checks, in addition to the limits that the oldest part of the comment names. The test cannot see the vector ... |
| 18 | ` * adds of read_dadd2 to read_iadd16 or any nop: they change no memory. The` | Comment: ... adds of the kernels `read_dadd2` to `read_iadd16`, or any nop. A vector add adds two vector registers, and a nop is an instruction that does nothing. They change no memory. The ... |
| 19 | ` * objdump listing is the evidence (check_listing12.py). It does not check` | Comment: ... objdump listing is the evidence for them. It is the machine code of every kernel as text, and the script `check_listing12.py` checks it. The self-test also does not check ... |
| 20 | ` * that these kernels preserve d8-d15: check_listing12.py checks the stores` | Comment: ... that these kernels preserve the registers d8 to d15. They are the low halves of the Arm vector registers v8 to v15. The Arm calling convention requires that a function gives them back unchanged. `check_listing12.py` checks the stores ... |
| 21 | ` * and loads of the listing.` | Comment: ... and the loads of these registers in the listing. |
| 22 | ` */` | Ends the comment. |
| 23 | `/* bwx12- */` | Comment: the marker `bwx12-`. It ends the block that the line with `bwx12+` started. |

### File comment: checks added for bwx11 (round 4) (lines 24 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 24 | `/* bwx11+ */` | Comment: the marker `bwx11+`. It starts a block of text that was added for bwx11. The next line with `bwx11-` ends the block. |
| 25 | `/*` | Opens the comment that describes the additions of bwx11. |
| 26 | ` * bwx11_selftest.c - bwx10_selftest.c plus the checks of round 4. Every` | Comment: `bwx11_selftest.c` is `bwx10_selftest.c` plus the checks of round 4. Round 4 is the set of additions that made bwx11 out of bwx10. |
| 27 | ` * addition stands between a line "bwx11+" and a line "bwx11-". Without these` | Comment: every addition stands between a line `bwx11+` and a line `bwx11-`. |
| 28 | ` * blocks this file is bwx10_selftest.c byte for byte.` | Comment: without the `bwx11` blocks the text is `bwx10_selftest.c` byte for byte. |
| 29 | ` *` | Comment: an empty line of the comment. |
| 30 | ` * The three new kernels (read_nop64, read_nop96, read_nop128) are read` | Comment: the three new kernels of round 4 are `read_nop64`, `read_nop96` and `read_nop128`. They are read ... One of the three, `read_nop96`, runs in part L of the whole-chip test. The spec file `like.spec` of that test names it in its kernel sequence. |
| 31 | ` * kernels, so the loop over kernels[] gives them the checks of every read` | Comment: ... kernels. So the loop over `kernels[]` gives them the checks of every read ... |
| 32 | ` * kernel.` | Comment: ... kernel. |
| 33 | ` * test_evict: evict_step() with 4 MiB returns no error, its two clock reads` | Comment: the new function `test_evict` checks three things. First: `evict_step` with 4 MiB returns no error. `evict_step` is the function behind the option `--evict-mb`. It stands in the runner source, the C file of the runner, which includes this file. Second: its two clock reads ... |
| 34 | ` * are in order, and the range is unmapped again (the mapping count of the` | Comment: ... are in order. Third: the range is unmapped again. For this the test compares the count of memory mappings of the ... |
| 35 | ` * process in /proc/self/maps is the same before and after).` | Comment: ... process in the file `/proc/self/maps` before and after the step. |
| 36 | ` */` | Ends the comment. |
| 37 | `/* bwx11- */` | Comment: the marker `bwx11-`. It ends the block that the line with `bwx11+` started. |

### File comment: checks added for bwx10 (round 3) (lines 38 to 59)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `/* bwx10+ */` | Comment: the marker `bwx10+`. It starts a block of text that was added for bwx10. The next line with `bwx10-` ends the block. |
| 39 | `/*` | Opens the comment that describes the additions of bwx10. |
| 40 | ` * bwx10_selftest.c - bwx8_selftest.c plus the checks of round 3. Every` | Comment: `bwx10_selftest.c` is `bwx8_selftest.c` plus the checks of round 3. Round 3 is the set of additions that made bwx10 out of bwx8. |
| 41 | ` * addition stands between a line "bwx10+" and a line "bwx10-". Without these` | Comment: every addition stands between a line `bwx10+` and a line `bwx10-`. |
| 42 | ` * blocks this file is bwx8_selftest.c byte for byte.` | Comment: without the `bwx10` blocks the text is `bwx8_selftest.c` byte for byte. |
| 43 | ` *` | Comment: an empty line of the comment. |
| 44 | ` * The five new kernels are read kernels, so the loop over kernels[] gives` | Comment: the five new kernels of round 3 are read kernels. So the loop over `kernels[]` gives ... One of the five, `read_1pl`, runs in part L of the whole-chip test. The spec file `like.spec` of that test names it in its kernel sequence. |
| 45 | ` * them the checks of every read kernel. A read_pf kernel prefetches past the` | Comment: ... them the checks of every read kernel. A `read_pf` kernel prefetches past the ... A prefetch asks for a cache line. It reads no data and never faults. |
| 46 | ` * end of its range, into the PROT_NONE page after the buffer: the test shows` | Comment: ... end of its range, into the page after the buffer. That page is `PROT_NONE`: the process may neither read nor write it. The test shows ... |
| 47 | ` * that this does not fault. read_1pl reads 16 B of every 64 B line: the test` | Comment: ... that this prefetch does not fault. The kernel `read_1pl` reads 16 B of every 64 B line. The test ... |
| 48 | ` * shows that it touches every page.` | Comment: ... shows that it touches every page. |
| 49 | ` *` | Comment: an empty line of the comment. |
| 50 | ` * test_trial_hot: the window checks of test_trial() with --hot-copy, so they` | Comment: the new function `test_trial_hot` repeats the window checks of `test_trial` with the option `--hot-copy`. So they ... |
| 51 | ` * run through timed_sequence_hot().` | Comment: ... run through `timed_sequence_hot`, the function of the runner source that runs the windows of a trial when `--hot-copy` is given. |
| 52 | ` * test_hot_touch: the window record of a 200 ms window stands in a page of` | Comment: the new function `test_hot_touch`. The window record of a 200 ms window stands in a page of ... A window record is the `struct win` that holds the plan and the result of one timed window. |
| 53 | ` * its own. A second thread waits for the first kernel call of the window,` | Comment: ... its own. A second thread waits for the first kernel call of the window, ... |
| 54 | ` * makes the page PROT_NONE for 20 ms, and makes it usable again. A fault in` | Comment: ... makes the page `PROT_NONE` for 20 ms, and makes it usable again. A fault in ... |
| 55 | ` * that page is counted, and the handler makes the page usable. timed_sequence()` | Comment: ... that page is counted, and the signal handler makes the page usable. The function `timed_sequence` ... |
| 56 | ` * must fault (it reads the record after every pass), so the check can see a` | Comment: ... must fault: it reads the record after every pass. So the check can see a ... |
| 57 | ` * touch. timed_sequence_hot() must not fault.` | Comment: ... touch. The function `timed_sequence_hot` must not fault. |
| 58 | ` */` | Ends the comment. |
| 59 | `/* bwx10- */` | Comment: the marker `bwx10-`. It ends the block that the line with `bwx10+` started. |

### File comment: the base self-test (text written for bwx8) (lines 60 to 101)

| Line | Source | Explanation |
|---:|---|---|
| 60 | `/*` | Opens the oldest part of the file comment. It names bwx8. It holds for bwx12 in the same way: `bwx12.c` includes this file [Ref1]. |
| 61 | ` * bwx8_selftest.c - "bwx8 --selftest": checks what every kernel of bwx8.c` | Comment: the purpose. The option `--selftest` of the runner checks what every kernel of the runner source ... |
| 62 | ` * does to memory, and the accounting of the trial mode. bwx8.c includes this` | Comment: ... does to memory, and the accounting of the trial mode (the mode of the runner with the option `--trial`). The runner source includes this ... |
| 63 | ` * file, so the test runs the machine code of the binary that is timed,` | Comment: ... file. So the test runs the machine code of the binary that is timed, ... |
| 64 | ` * through the same call() as the benchmark. The kernel checks are the text of` | Comment: ... through the same function `call` as the benchmark. So the self-test and a timed run are one binary, and both reach a kernel through `call` and the table `kernels[]`. The kernel checks are the text of ... |
| 65 | ` * bwx_selftest.c. test_trial() at the end is new.` | Comment: ... `bwx_selftest.c`, the self-test of the first runner version. The function `test_trial` at the end was new in bwx8. |
| 66 | ` *` | Comment: an empty line of the comment. |
| 67 | ` * Every buffer ends at a page that cannot be read or written (PROT_NONE) and` | Comment: every test buffer ends at a page that cannot be read or written (`PROT_NONE`) and ... |
| 68 | ` * starts after one. A kernel that touches a byte within one page before the` | Comment: ... starts after one. A kernel that touches a byte within one page before the ... So a load or a store up to one page outside the buffer is a fault. The fault ends the process, except in `test_touch` (line 235), which installs a handler. |
| 69 | ` * buffer or within one page after it dies with SIGSEGV. The line "call,..."` | Comment: ... buffer or within one page after it ends with `SIGSEGV`. Linux sends this signal for a forbidden memory access. The line `call,...` ... |
| 70 | ` * printed before each kernel call names the kernel that died.` | Comment: ... that is printed before each kernel call (line 131) names the kernel that ended the process. |
| 71 | ` * Exit status 0 means every check passed.` | Comment: exit status 0 means that every check passed. |
| 72 | ` *` | Comment: an empty line of the comment. |
| 73 | ` * Checks for every kernel that stores (write and copy kinds): every word is` | Comment: the checks for every kernel that stores (the write kind and the copy kind): every word is ... |
| 74 | ` * compared, on whole buffers and on one 256 B block at a page start and at a` | Comment: ... compared, on whole buffers (line 147) and on one 256 B block at a page start and at a ... |
| 75 | ` * page end.` | Comment: ... page end (line 192). |
| 76 | ` * Checks for every read kernel: the buffer is unchanged and no guard page is` | Comment: the checks for every read kernel: the buffer is unchanged and no guard page is ... |
| 77 | ` * touched. The kernel must fault when one page inside its range is made` | Comment: ... touched. The kernel must fault when one page inside its range is made ... |
| 78 | ` * PROT_NONE, for each page of a 3-page range. oldread and oldread2 return a` | Comment: ... `PROT_NONE`, for each page of a 3-page range (line 235). The kernels `oldread` and `oldread2` return a ... |
| 79 | ` * sum: it must equal the sum of all words.` | Comment: ... sum. The test compares it with the sum of all words (line 170). |
| 80 | ` *` | Comment: an empty line of the comment. |
| 81 | ` * Limits. For the read kernels that return nothing, the test proves that` | Comment: the limits. The new read kernel `read` and `asmread` return nothing. For such read kernels the test proves that ... |
| 82 | ` * every page of the range is touched, not every byte: the objdump listing is` | Comment: ... every page of the range is touched. It does not prove that every byte is loaded. For the bytes that such a kernel loads, the objdump listing is ... |
| 83 | ` * the evidence for the bytes. It cannot see in which order a copy kernel` | Comment: ... the evidence [Ref7]. The test also cannot see in which order a copy kernel ... |
| 84 | ` * loads and stores. It does not check that a kernel preserves the` | Comment: ... loads and stores. And it does not check that a kernel preserves the ... |
| 85 | ` * callee-saved registers d8-d15.` | Comment: ... registers d8 to d15, which the called function must save (callee-saved). |
| 86 | ` *` | Comment: an empty line of the comment. |
| 87 | ` * Checks of the trial mode (test_trial): one trial with all phases and bins` | Comment: the checks of the trial mode in `test_trial` (line 286). One trial with all phases and with bins ... The whole-chip test does not use the trial mode [Ref6]. So these checks do not cover the function `worker` of `bwx12.c`, which timed the kernels in the whole-chip test. |
| 88 | ` * runs through run_trial(), the function that the trial mode uses. Every` | Comment: ... runs through `run_trial`, the function that the trial mode uses. Every ... |
| 89 | ` * window must hold whole passes and whole groups of passes between clock` | Comment: ... window must hold whole passes and whole groups of passes between clock ... |
| 90 | ` * reads, must last at least its duration, and must not start before the` | Comment: ... reads, must last at least its duration, and must not start before the ... |
| 91 | ` * window before it ended. The last bin of a window must hold the bytes of` | Comment: ... window before it ended. The last bin of a window must hold the bytes of ... A bin is a record inside a target window: one clock read and the bytes counted from the start of the window to that clock read. |
| 92 | ` * the window. The sink check must pass on a clean buffer and must fail after` | Comment: ... the window. The sink check must pass on a clean buffer and must fail after ... The sink is the variable that receives the sum that an old read kernel returns. The sink check compares it with the expected sum. |
| 93 | ` * one word of the buffer is changed.` | Comment: ... one word of the buffer is changed. |
| 94 | ` *` | Comment: an empty line of the comment. |
| 95 | ` * Checks of the rows (test_emit): emit_trial(), the function that prints the` | Comment: the checks of the output rows in `test_emit` (line 628). `emit_trial`, the function that prints the ... |
| 96 | ` * rows of a trial, runs on a record with known values. The printed text is` | Comment: ... rows of a trial, runs on a record with known values. The printed text is ... |
| 97 | ` * compared: the C rows hold differences of two readings, the post P row holds` | Comment: ... compared. The C rows hold differences of two counter readings. The P row with the word `post` holds ... |
| 98 | ` * the second snapshot, the E row holds CPU time and the two context-switch` | Comment: ... the second page snapshot. The E row holds the CPU time and the two context-switch ... |
| 99 | ` * counts in their own fields, and the X rows coverage_na, count_multiplexed` | Comment: ... counts, each in its own field. And the X rows with the codes `coverage_na`, `count_multiplexed` ... |
| 100 | ` * and sink are printed.` | Comment: ... and `sink` are printed. An X row reports a defect that the runner found in a trial. |
| 101 | ` */` | Ends the comment. |

### Global variables (lines 102 to 104)

| Line | Source | Explanation |
|---:|---|---|
| 102 | `static int failures;` | `failures`: the count of failed checks. `check` (line 138) and `trial_check` (line 270) add to it, and `selftest` prints it at the end (line 709). |
| 103 | `static sigjmp_buf fault_jmp;` | `fault_jmp`: the saved place at which `test_touch` continues after a fault (line 252). `sigjmp_buf` is the type of the C library for such a saved place. |
| 104 | `static volatile uintptr_t fault_addr;` | `fault_addr`: the address of the last fault. The handler `on_fault` writes it (line 228). `volatile` tells the compiler to read and write the variable in memory at every use. A variable that a signal handler changes needs this. |

### Functions `guarded` and `unguard`: a buffer between two `PROT_NONE` pages (lines 105 to 122)

| Line | Source | Explanation |
|---:|---|---|
| 106 | `/* n words whose first byte follows a PROT_NONE page and whose last byte` | Comment: `guarded` gives `n` words (8 bytes each) whose first byte follows a `PROT_NONE` page and whose last byte ... |
| 107 | ` * precedes one. n * 8 must be a multiple of the page size. */` | Comment: ... stands directly before one. For this, `n * 8` must be a multiple of the page size. The function does not test it. With the page size of the CRB build, 4096 B, every caller passes a multiple of the page size. So the last word ends directly before the `PROT_NONE` page [Ref3]. |
| 108 | `static uint64_t *guarded(size_t n)` | Starts the function `guarded`. It returns the address of `n` words of new memory that lie between two `PROT_NONE` pages. The checks of this file take their test buffers from it. The memory comes from a plain `mmap`, with no request for huge pages. |
| 109 | `{` | Opens the body of `guarded`. |
| 110 | `    size_t len = n * 8;` | `len`: the size of the buffer in bytes. |
| 111 | `    uint8_t *raw = mmap(NULL, len + 2 * (size_t)page_bytes, PROT_NONE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | `mmap` asks Linux for `len` bytes plus two pages of new memory. `page_bytes` is the page size in bytes. `main` of the runner source sets it before it calls the self-test. `PROT_NONE`: at first the process may neither read nor write any byte of the range. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. |
| 112 | `    if (raw == MAP_FAILED \|\| mprotect(raw + page_bytes, len, PROT_READ \| PROT_WRITE) != 0) {` | Tests whether `mmap` failed. If it did not fail, `mprotect` makes the `len` bytes after the first page readable and writable. The first page and the last page stay `PROT_NONE`. A return value other than 0 means that `mprotect` failed. |
| 113 | `        perror("guarded");` | On an error: `perror` prints the word `guarded` and the reason that Linux gave. |
| 114 | `        exit(2);` | On an error: the process ends with exit status 2. |
| 115 | `    }` | Ends the `if` of line 112. |
| 116 | `    return (uint64_t *)(raw + page_bytes);` | Returns the address of the first usable byte, one page after the start of the mapping. |
| 117 | `}` | Ends the function `guarded`. |
| 119 | `static void unguard(uint64_t *p, size_t n)` | Starts the function `unguard`. It releases a buffer of `n` words that `guarded` returned. |
| 120 | `{` | Opens the body of `unguard`. |
| 121 | `    munmap((uint8_t *)p - page_bytes, n * 8 + 2 * (size_t)page_bytes);` | `munmap` gives the whole mapping back to Linux: the buffer and its two `PROT_NONE` pages. The mapping starts one page before `p`. |
| 122 | `}` | Ends the function `unguard`. |

### Functions `pattern`, `calling`, `check` and `is_read` (lines 123 to 144)

| Line | Source | Explanation |
|---:|---|---|
| 124 | `static uint64_t pattern(size_t i, uint64_t salt)` | Starts the function `pattern`. It returns the test value of the word with the number `i`. |
| 125 | `{` | Opens the body of `pattern`. |
| 126 | `    return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;` | Returns `(i + 1)` times an odd 64-bit constant, then XOR `salt`. The product is computed first. Two different word numbers `i` always give two different values. Two different `salt` values give two different patterns for the same `i`. |
| 127 | `}` | Ends the function `pattern`. |
| 129 | `static void calling(const struct kdef *kd, size_t n)` | Starts the function `calling`. It names a kernel in the output before the kernel runs. `kd` points to the entry of the kernel in `kernels[]`. `n` is the size of the range in words. |
| 130 | `{` | Opens the body of `calling`. |
| 131 | `    printf("call,%s,%zu\n", kd->name, n * 8);` | Prints the line `call,<kernel>,<bytes>`: the word `call`, the kernel name, and the size of the range in bytes (`n * 8`). The output is line-buffered (line 678), so this line is written before the kernel starts. If the kernel ends the process, this line names it. |
| 132 | `}` | Ends the function `calling`. |
| 134 | `static void check(int ok, const struct kdef *kd, const char *what, size_t n)` | Starts the function `check`. It prints the result line of one kernel check. `ok` is not 0 when the check passed. |
| 135 | `{` | Opens the body of `check`. |
| 136 | `    printf("%s,%s,%zu,%s\n", kd->name, what, n * 8, ok ? "pass" : "FAIL");` | Prints one row with four fields: the kernel name, the name of the check (`what`), the size in bytes (`n * 8`), and `pass` or `FAIL`. |
| 137 | `    if (!ok)` | When the check failed ... |
| 138 | `        failures++;` | ... adds 1 to `failures`. The self-test continues after a failed check. |
| 139 | `}` | Ends the function `check`. |
| 141 | `static int is_read(const struct kdef *kd)` | Starts the function `is_read`. It tells whether a kernel is a read kernel. |
| 142 | `{` | Opens the body of `is_read`. |
| 143 | `    return kd->type == T_READ \|\| kd->type == T_OLDREAD;` | True for the two read kinds. `T_OLDREAD` is `oldread` and `oldread2`: they return a sum. `oldread2` is a second copy of `oldread`: the same source under another name [Ref1]. `T_READ` is every other read kernel, for example `read` and `asmread`: they return nothing. |
| 144 | `}` | Ends the function `is_read`. |

### Function `test_size`: one kernel on a whole guarded buffer (lines 145 to 188)

| Line | Source | Explanation |
|---:|---|---|
| 146 | `/* The kernel on a whole guarded buffer of n words. */` | Comment: `test_size` runs the kernel on a whole guarded buffer of `n` words. A guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. |
| 147 | `static void test_size(const struct kdef *kd, size_t n)` | Starts the function `test_size`. It runs the kernel once on a whole guarded buffer and reads no clock. `selftest` passes three sizes: 1 page, 3 pages and 1 MiB (line 686). What it proves for every kernel: no load and no store within one page outside its buffers. Such an access ends the process. A prefetch raises no fault, so the check does not see one. Read kernel: the buffer is unchanged after the call. Old read kernel: the returned sum equals the sum of all words. Write and copy kernel: every word of the range holds the right value after the call. What it cannot prove: that `read` or `asmread` load anything. A read kernel without a return value that loads nothing passes here. `test_touch` (line 235) checks a part of this. |
| 148 | `{` | Opens the body of `test_size`. |
| 149 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record in the form that `call` needs (`struct thread` of the runner source). Its buffers `a` and `b` are two guarded buffers of `n` words each. Every other field is 0. |
| 150 | `    uint64_t *a = t.a, *b = t.b, sum = 0;` | `a` and `b`: short names for the two buffers. `sum`: the sum of all words of `a`, built in line 160. |
| 151 | `    uint64_t v = 0xA5A5F00D12345678ULL + n;` | `v`: the value that a write kernel must store in every word. It depends on `n`, so each buffer size gets another value. |
| 152 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum that an old read kernel returns. |
| 153 | `    int ok = 1;` | `ok`: the result of the check that runs now. 1 means passed. |
| 155 | `    /* Every word of the source is different, so a store of the wrong vector` | Comment: every word of the source buffer gets a different value. So a store of the wrong vector ... |
| 156 | `     * or to the wrong offset is seen. */` | Comment: ... or a store to the wrong offset is seen. |
| 157 | `    for (size_t i = 0; i < n; i++) {` | Loop over all `n` words. |
| 158 | `        a[i] = pattern(i, 1);` | Gives every word of `a` its own value: `pattern` with the salt 1. |
| 159 | `        b[i] = 0;` | Sets every word of `b` to 0. |
| 160 | `        sum += a[i];` | `sum` becomes the sum of all words of `a` in 64-bit arithmetic (an overflow wraps). |
| 161 | `    }` | Ends the loop of line 157. |
| 162 | `    calling(kd, n);` | Prints the `call` line (line 131). |
| 163 | `    call(kd, &t, 0, n * 8, v, &sink);` | Runs the kernel on the whole buffer (offset 0, `n * 8` bytes) through `call` of the runner source. `call` chooses the arguments by the kind. A read kernel gets `a`. A write kernel gets `a` and the value `v`, which it stores in every word. A copy kernel reads `a` and writes `b`. The sum that an old read kernel returns goes to `sink`. No `SIGSEGV` handler is installed here. A kernel that loads from or stores to a `PROT_NONE` page ends the process. No result line follows then, and the last `call` line of the output names the kernel. |
| 164 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 165 | `        /* read: must leave every word as it was (and must not fault) */` | Comment: a read kernel must leave every word as it was, and it must not fault. |
| 166 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 167 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must still hold its pattern value. One changed word sets `ok` to 0. |
| 168 | `        check(ok, kd, "buffer unchanged", n);` | Prints the result row with the check name `buffer unchanged`. |
| 169 | `        if (kd->type == T_OLDREAD)` | For the kind `T_OLDREAD` in addition ... |
| 170 | `            check(sink == sum, kd, "returned sum equals the sum of all words", n);` | ... the sum in `sink` must equal `sum`. A kernel that skips one word, or adds one word twice, returns another sum. The check name is `returned sum equals the sum of all words`. |
| 171 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 172 | `        /* write: every word must hold v afterwards; no word may keep the old pattern */` | Comment: after a write kernel every word must hold `v`. No word may keep the old pattern. |
| 173 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 174 | `            ok &= a[i] == v;` | Every word of `a` must hold `v`. A word that the kernel did not store keeps its pattern value, and no pattern value equals `v`. So a missing store fails the check. |
| 175 | `        check(ok, kd, "every word equals v", n);` | Prints the result row with the check name `every word equals v`. |
| 176 | `    } else {` | Branch for a copy kernel. |
| 177 | `        /* copy: destination must equal source word for word; source unchanged */` | Comment: after a copy kernel the destination must equal the source word for word, and the source must be unchanged. |
| 178 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `b`. |
| 179 | `            ok &= b[i] == pattern(i, 1);` | Every word of `b` must hold the pattern value of the same word of `a`. `b` held 0 before the call. |
| 180 | `        check(ok, kd, "destination equals source", n);` | Prints the first result row of a copy kernel, with the check name `destination equals source`. |
| 181 | `        ok = 1;` | Sets `ok` back to 1 for the second check. |
| 182 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of `a`. |
| 183 | `            ok &= a[i] == pattern(i, 1);` | Every word of `a` must be unchanged. |
| 184 | `        check(ok, kd, "source unchanged", n);` | Prints the second result row of a copy kernel, with the check name `source unchanged`. |
| 185 | `    }` | Ends the `if` chain of line 164. |
| 186 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 187 | `    unguard(b, n);` | ... and the buffer `b`. |
| 188 | `}` | Ends the function `test_size`. |

### Function `test_block`: 256 B at a page start or at a page end (lines 189 to 222)

| Line | Source | Explanation |
|---:|---|---|
| 190 | `/* One block of 256 B (32 words) at word offset off inside one guarded page.` | Comment: `test_block` runs the kernel on one block of 256 B (32 words) at the word offset `off` inside one guarded page. |
| 191 | ` * Words of the page outside the 256 B must keep their old value. */` | Comment: the words of the page outside the 256 B must keep their old value. |
| 192 | `static void test_block(const struct kdef *kd, size_t off)` | Starts the function `test_block`. It runs the kernel on one block of 256 B (32 words) inside a buffer of one page. 256 B is the smallest range that a kernel may get. With `off` = 0 the block starts directly after the `PROT_NONE` page before the buffer. With the other value of `off` the block ends directly before the `PROT_NONE` page after the buffer (line 688). What it proves for every kernel: no load and no store up to one page before the block start (first case), and none up to one page after the block end (second case). Such an access ends the process. Write and copy kernel: every word of the page outside the block keeps its value. What it cannot prove: which bytes inside the 256 B a read kernel loads. The sum that an old read kernel returns is not compared here. |
| 193 | `{` | Opens the body of `test_block`. |
| 194 | `    size_t n = (size_t)page_bytes / 8, m = 32;` | `n`: the number of words of one page. `m`: the 32 words of the block (256 B). |
| 195 | `    struct thread t = { .a = guarded(n), .b = guarded(n) };` | `t`: a thread record with two guarded buffers of one page each. |
| 196 | `    uint64_t *a = t.a, *b = t.b;` | `a` and `b`: short names for the two buffers. |
| 197 | `    uint64_t v = 0x0123456789ABCDEFULL;` | `v`: the value that a write kernel must store. |
| 198 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 199 | `    int ok = 1;` | `ok`: the result of the check. 1 means passed. |
| 201 | `    for (size_t i = 0; i < n; i++) {` | Loop over all words of the page. |
| 202 | `        a[i] = pattern(i, 3);` | Fills the page of `a` with the pattern of the salt 3 ... |
| 203 | `        b[i] = pattern(i, 4);` | ... and the page of `b` with the pattern of the salt 4. So the two pages hold two different patterns. |
| 204 | `    }` | Ends the loop of line 201. |
| 205 | `    calling(kd, m);` | Prints the `call` line with the size 256. |
| 206 | `    call(kd, &t, off * 8, m * 8, v, &sink);` | Runs the kernel on 256 B (`m * 8`) at the byte offset `off * 8`. As in `test_size`, no `SIGSEGV` handler is installed. |
| 207 | `    if (is_read(kd)) {` | Branch for a read kernel. |
| 208 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 209 | `            ok &= a[i] == pattern(i, 3);` | Read kernel: every word of the page of `a` must be unchanged. |
| 210 | `        check(ok, kd, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);` | Prints the result row. The name of the check says `page start` for `off` = 0 and `page end` for the other value. The size field is 256. |
| 211 | `    } else if (kd->type == T_WRITE) {` | Branch for a write kernel. |
| 212 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 213 | `            ok &= a[i] == (i >= off && i < off + m ? v : pattern(i, 3));` | Write kernel: the 32 words of the block must hold `v`. Every other word of the page must keep its pattern value. |
| 214 | `        check(ok, kd, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);` | Prints the result row. The check name ends with `only those 256 B written`. |
| 215 | `    } else {` | Branch for a copy kernel. |
| 216 | `        for (size_t i = 0; i < n; i++)` | Loop over all words of the page. |
| 217 | `            ok &= b[i] == (i >= off && i < off + m ? pattern(i, 3) : pattern(i, 4)) && a[i] == pattern(i, 3);` | Copy kernel: in `b` the 32 words of the block must hold the values of `a`. Every other word of `b` must keep its own pattern value. `a` must be unchanged. |
| 218 | `        check(ok, kd, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);` | Prints the result row. The check name ends with `only those 256 B copied`. |
| 219 | `    }` | Ends the `if` chain of line 207. |
| 220 | `    unguard(a, n);` | Releases the buffer `a` ... |
| 221 | `    unguard(b, n);` | ... and the buffer `b`. |
| 222 | `}` | Ends the function `test_block`. |

### Functions `on_fault` and `test_touch`: a read kernel must touch every page (lines 223 to 264)

| Line | Source | Explanation |
|---:|---|---|
| 224 | `static void on_fault(int sig, siginfo_t *si, void *ctx)` | Starts the function `on_fault`, the `SIGSEGV` handler of `test_touch`. Linux calls it when a kernel accesses a page that it may not access. `si` holds the details of the fault. |
| 225 | `{` | Opens the body of `on_fault`. |
| 226 | `    (void)sig;` | Marks the argument `sig` as not used. Then the compiler does not warn about it. |
| 227 | `    (void)ctx;` | Marks the argument `ctx` as not used. |
| 228 | `    fault_addr = (uintptr_t)si->si_addr;` | Stores the address of the faulting access in `fault_addr`. |
| 229 | `    siglongjmp(fault_jmp, 1);` | Jumps back to the `sigsetjmp` call of line 252, which now returns 1. The kernel call that faulted does not continue. |
| 230 | `}` | Ends the function `on_fault`. |
| 232 | `/* Read kernels: a range of 3 pages, with one page inside it made PROT_NONE.` | Comment: for read kernels, `test_touch` uses a range of 3 pages, with one page inside it made `PROT_NONE`. |
| 233 | ` * The kernel must fault, and the fault address must lie in that page. This` | Comment: the kernel must fault, and the fault address must lie in that page. This ... |
| 234 | ` * shows that the kernel touches every page of its range. */` | Comment: ... shows that the kernel touches every page of its range. |
| 235 | `static void test_touch(const struct kdef *kd)` | Starts the function `test_touch`. It is for read kernels only. The buffer has 3 pages. The loop runs three times. Each time another one of the pages is `PROT_NONE`, and the kernel runs on the whole buffer. The kernel must fault, and the fault address must lie in that page. What it proves: the kernel accesses at least one byte of each of the 3 pages. A kernel that loads nothing, or that leaves out a page, fails. What it cannot prove: that every byte or every 64 B line of a page is loaded. One load per page passes. A page has 4096 B on CRB [Ref3]. The objdump listing is the evidence for the loads [Ref7]. It also cannot prove anything about a nop, a vector add, or the use of a loaded value. They change no memory and raise no fault. |
| 236 | `{` | Opens the body of `test_touch`. |
| 237 | `    size_t n = 3 * (size_t)page_bytes / 8;` | `n`: the number of words of 3 pages. |
| 238 | `    struct thread t = { .a = guarded(n) };` | `t`: a thread record with one guarded buffer of 3 pages. A read kernel needs no buffer `b`. |
| 239 | `    struct sigaction sa, old;` | `sa`: the new setting for the signal. `old`: the setting from before. |
| 240 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This function does not compare it. |
| 242 | `    memset(&sa, 0, sizeof sa);` | Sets every byte of `sa` to 0. |
| 243 | `    sa.sa_sigaction = on_fault;` | The handler is `on_fault`. |
| 244 | `    sa.sa_flags = SA_SIGINFO;` | The flag `SA_SIGINFO` makes Linux pass the fault address to the handler. |
| 245 | `    sigaction(SIGSEGV, &sa, &old);` | Installs `on_fault` as the handler of `SIGSEGV`. `old` keeps the setting from before. |
| 246 | `    for (volatile int j = 0; j < 3; j++) {` | The loop runs three times, once per page `j`. `j` is `volatile`: it keeps its value across the jump of line 229. |
| 247 | `        uint8_t *pg = (uint8_t *)t.a + (size_t)j * (size_t)page_bytes;` | `pg`: the address of page `j` of the buffer. |
| 248 | `        volatile int faulted = 0;` | `faulted`: becomes 1 when the kernel faulted. It is `volatile` for the same reason as `j`. |
| 249 | `        mprotect(pg, (size_t)page_bytes, PROT_NONE);` | `mprotect` makes this page `PROT_NONE`. |
| 250 | `        fault_addr = 0;` | Clears the fault address of the pass before. |
| 251 | `        calling(kd, n);` | Prints the `call` line. |
| 252 | `        if (sigsetjmp(fault_jmp, 1) == 0)` | `sigsetjmp` saves this place in `fault_jmp` and returns 0 at its direct call. The argument 1 saves the signal mask, and the jump restores it. So `SIGSEGV` can be caught again for the next page. |
| 253 | `            call(kd, &t, 0, n * 8, 0, &sink);` | The value 0: the kernel is called on the whole range of 3 pages. |
| 254 | `        else` | The other value: when the kernel faults, `on_fault` jumps back to line 252, and `sigsetjmp` returns 1 there. |
| 255 | `            faulted = 1;` | Then `faulted` becomes 1. |
| 256 | `        mprotect(pg, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | Makes the page readable and writable again. |
| 257 | `        check(faulted && fault_addr >= (uintptr_t)pg && fault_addr < (uintptr_t)pg + (uintptr_t)page_bytes, kd,` | The check passes when the kernel faulted and the fault address lies in the `PROT_NONE` page. The call goes on in the next three lines. |
| 258 | `              j == 0 ? "faults in page 0 of 3 when it is PROT_NONE"` | Continues the call of line 257: the name of the check gives the page number. This is the name for page 0. |
| 259 | `                     : j == 1 ? "faults in page 1 of 3 when it is PROT_NONE" : "faults in page 2 of 3 when it is PROT_NONE",` | Continues the call: the names for page 1 and for page 2. |
| 260 | `              n);` | Ends the call: the size of the range in words. The row prints it in bytes. |
| 261 | `    }` | Ends the loop of line 246. |
| 262 | `    sigaction(SIGSEGV, &old, NULL);` | Restores the `SIGSEGV` setting from before. |
| 263 | `    unguard(t.a, n);` | Releases the buffer. |
| 264 | `}` | Ends the function `test_touch`. |

### Functions `trial_check` and `kernel_named` (lines 265 to 283)

| Line | Source | Explanation |
|---:|---|---|
| 266 | `static void trial_check(int ok, const char *what, size_t bytes)` | Starts the function `trial_check`. It works like `check` (line 134), for a check that belongs to no single kernel. |
| 267 | `{` | Opens the body of `trial_check`. |
| 268 | `    printf("trial,%s,%zu,%s\n", what, bytes, ok ? "pass" : "FAIL");` | Prints one row with four fields: the word `trial`, the name of the check (`what`), a number of bytes, and `pass` or `FAIL`. |
| 269 | `    if (!ok)` | When the check failed ... |
| 270 | `        failures++;` | ... adds 1 to `failures`. The self-test continues. |
| 271 | `}` | Ends the function `trial_check`. |
| 273 | `static int kernel_named(const char *name)` | Starts the function `kernel_named`. It returns the index of the kernel with this name in the table `kernels[]`. |
| 274 | `{` | Opens the body of `kernel_named`. |
| 275 | `    int k = 0;` | `k`: the index, from 0. |
| 276 | `    while (k < K_COUNT && strcmp(name, kernels[k].name))` | Goes through the table until the name is equal (`strcmp` returns 0 then) or the table ends. `K_COUNT` is the number of entries of `kernels[]`. |
| 277 | `        k++;` | Goes to the next entry. |
| 278 | `    if (k == K_COUNT) {` | Tests whether the table ended. Then no kernel has the name. |
| 279 | `        fprintf(stderr, "selftest: no kernel %s\n", name);` | Prints the message `selftest: no kernel` with the name to the error output. |
| 280 | `        exit(2);` | Ends the process with exit status 2. |
| 281 | `    }` | Ends the `if` of line 278. |
| 282 | `    return k;` | Returns the index. |
| 283 | `}` | Ends the function `kernel_named`. |

### Function `test_trial`: the records of one trial (trial mode) (lines 284 to 355)

| Line | Source | Explanation |
|---:|---|---|
| 285 | `/* The trial mode on a guarded buffer of 1 MiB whose words all hold w.v. */` | Comment: `test_trial` runs the trial mode on a guarded buffer of 1 MiB whose words all hold the value `w.v`. |
| 286 | `static void test_trial(void)` | Starts the function `test_trial`. It runs trials on a guarded buffer of 1 MiB through `run_trial` of `bwx12.c`, the function that the trial mode uses. A trial is a list of timed windows that run one directly after the other. What it proves: `timed_sequence` writes consistent window records, and the sink check can pass and can fail. What it cannot prove: that the byte count of a window equals the bytes that the kernel read. The checks test multiples, not the number of kernel calls. It also cannot prove anything about the timing code of the whole-chip test. That code is the function `worker` of `bwx12.c` (interval mode), and no check of this file runs it [Ref1] [Ref6]. |
| 287 | `{` | Opens the body of `test_trial`. |
| 288 | `    size_t bytes = 1UL << 20, n = bytes / 8;` | `bytes`: the buffer size, 1 MiB (1048576 bytes). `n`: the same size in words (131072 words of 8 bytes). |
| 289 | `    int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");` | The indexes of three kernels in `kernels[]`: `oldread` (the old read kernel), `read` (the new read kernel, kept in the variable `rd`) and `asmread`. |
| 290 | `    struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,` | `p`: the plan of the trial (`struct trial` of the runner source). `.nwin = 3`: 3 target windows. `.win_ms = 12`: the requested duration of each target window is 12 ms. A window ends at the first clock read at or after its requested duration. So it lasts at least that long. `.count = CS_CLOSED`: the trial opens no counter group. `.bins = 1`: bins are on. |
| 291 | `                       .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },` | Continues the plan. `.prev`: 1 window of previous activity, `asmread` on 1 MiB for 4 ms. `.pfx`: 4 prefix windows of `oldread` on 1 MiB, 8 ms for all four, so 2 ms each. |
| 292 | `                       .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };` | Ends the plan. `.pred`: 1 predecessor window, `read` on 65536 B for 3 ms. `.tgt`: the target windows run `oldread` on 1 MiB. The 0 is the time field. A target window does not use it: its time is `win_ms`. |
| 293 | `    struct win win[9];` | `win`: the 9 window records of the trial. A window record holds the plan and the result of one window. |
| 294 | `    struct bin bin[9]; /* 3 target windows, window_bins() = 3 each */` | `bin`: storage for 9 bins. Comment: there are 3 target windows, and `window_bins` gives room for 3 bins in each. |
| 295 | `    struct trec r = { .win = win, .nw = trial_windows(&p) };` | `r`: the record of the trial (`struct trec` of the runner source). It points to the window records. `nw` is the number of windows that `trial_windows` of the runner source computes from the plan. |
| 296 | `    struct tw w;` | `w`: the worker record (`struct tw` of the runner source). It holds the state of the thread that runs the trials: the buffer, the counter group and the trace. In the self-test the main thread runs the trials. |
| 297 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum that an old read kernel returns. |
| 298 | `    int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1;` | Five result flags, one per check of the loop of lines 311 to 325. Each starts as 1. The value 1 stands for passed. |
| 300 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 301 | `    w.t.group_fd = -1;` | `group_fd = -1`: the worker has no counter group. |
| 302 | `    w.v = 0x9E3779B97F4A7C15ULL * 7;` | `w.v`: the value that every word of the buffer gets. `run_trial` computes the expected sum of an old read as `w.v` times the number of words. |
| 303 | `    w.t.a = guarded(n);` | The buffer of the worker: a guarded buffer of 1 MiB. |
| 304 | `    for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 305 | `        w.t.a[i] = w.v;` | Every word of the buffer gets the same value `w.v`. This is also the first write to the new buffer, outside every timed window. |
| 307 | `    trial_check(r.nw == 9 && window_bins(&p) == 3, "prev 1 + prefix 4 + pred 1 + target 3 windows", bytes);` | First check: the plan gives 9 windows (1 + 4 + 1 + 3), and a target window has room for 3 bins: 1 bin for the 10 ms that end inside the 12 ms, 1 bin for the end of the window, and 1 spare bin. |
| 308 | `    set_windows(&p, win, bin);` | `set_windows` of the runner source fills the plan fields of the 9 window records: kernel, range size, passes between two clock reads, duration and bin storage. |
| 309 | `    printf("call,trial,%zu\n", bytes);` | Prints the line `call,trial,1048576` before the trial runs. |
| 310 | `    run_trial(&w, &p, &r, &sink);` | `run_trial` runs the 9 windows through `timed_sequence` and then sets `r.sink_ok`. In `timed_sequence` each window reads the clock at its start and again after each group of passes. The window ends at the first clock read at or after its duration. |
| 311 | `    for (int i = 0; i < r.nw; i++) {` | Loop over the 9 window records after the trial. |
| 312 | `        const struct win *x = &win[i];` | `x`: the record of window `i`. |
| 313 | `        whole &= x->bytes > 0 && x->bytes % x->size == 0;` | `whole`: the window counted more than 0 bytes, and a multiple of its range size. |
| 314 | `        groups &= x->bytes % CHECK_BYTES == 0; /* every size here divides 8 MiB */` | `groups`: the bytes are a multiple of 8 MiB (`CHECK_BYTES`). The window loop reads the clock after each 8 MiB. Comment: every range size of this plan divides 8 MiB. |
| 315 | `        lasts &= x->t_end - x->t_start >= x->dur_ns;` | `lasts`: end time minus start time is at least the requested duration. All three values are in ns. |
| 316 | `        order &= x->t_end > x->t_start && (i == 0 \|\| x->t_start >= win[i - 1].t_end);` | `order`: the end is later than the start, and the start is not earlier than the end of the window before. |
| 317 | `        if (x->phase == PH_TARGET) {` | Branch for a target window. |
| 318 | `            bins_ok &= x->nbin >= 1 && x->nbin <= x->bin_cap && x->bin[x->nbin - 1].bytes == x->bytes &&` | `bins_ok`, target window: it has 1 to `bin_cap` bins, and the last bin holds the bytes of the window ... |
| 319 | `                       x->bin[x->nbin - 1].t_end == x->t_end;` | ... and the end time of the window. |
| 320 | `            for (int b = 1; b < x->nbin; b++)` | Loop over the bins after the first one. |
| 321 | `                bins_ok &= x->bin[b].t_end > x->bin[b - 1].t_end && x->bin[b].bytes > x->bin[b - 1].bytes;` | Time and bytes must rise from bin to bin. |
| 322 | `        } else {` | Branch for every other window. |
| 323 | `            bins_ok &= x->nbin == 0;` | `bins_ok`, other window: it has no bin. |
| 324 | `        }` | Ends the `if` of line 317. |
| 325 | `    }` | Ends the loop of line 311. |
| 326 | `    trial_check(whole, "every window holds whole passes and more than 0 bytes", bytes);` | Prints the result of `whole`, the first of the five results of the loop. |
| 327 | `    trial_check(groups, "every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);` | Prints the result of `groups`. |
| 328 | `    trial_check(lasts, "every window lasts at least its requested duration", bytes);` | Prints the result of `lasts`. |
| 329 | `    trial_check(order, "timestamps do not go back from window to window", bytes);` | Prints the result of `order`. |
| 330 | `    trial_check(bins_ok, "the last bin of a target window ends the window and holds its bytes", bytes);` | Prints the result of `bins_ok`. |
| 331 | `    trial_check(r.sink_ok == 1, "sink holds the sum after a trial that ends in old read", bytes);` | One more check: `r.sink_ok` is 1. So after a trial that ends with `oldread`, the sink holds the expected sum. |
| 333 | `    p.tgt.k = rd;` | Second trial: the target kernel is now `read`, the new read kernel. |
| 334 | `    set_windows(&p, win, bin);` | Fills the window records again from the changed plan. |
| 335 | `    run_trial(&w, &p, &r, &sink);` | Runs the second trial. |
| 336 | `    trial_check(r.sink_ok == 1, "sink holds the sum of the last old read when the target is new read", bytes);` | The last old read is now a prefix window. `sink_ok` must still be 1. So the `read` windows after it left the sink unchanged. |
| 338 | `    p.pfx.k = asmread;` | Third trial: the prefix kernel is now `asmread` too. So the trial holds no old read. |
| 339 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 340 | `    run_trial(&w, &p, &r, &sink);` | Runs the third trial. |
| 341 | `    trial_check(r.sink_ok == -1, "sink check is NA for a trial without old read", bytes);` | `sink_ok` must be -1. This value stands for not applicable. |
| 343 | `    /* The sink check must be able to fail: one changed word changes the sum. */` | Comment: the sink check must be able to fail. One changed word changes the sum. |
| 344 | `    p.tgt.k = oldread;` | Fourth trial: the target is `oldread` again. |
| 345 | `    w.t.a[n - 1] ^= 1;` | Flips the lowest bit of the last word of the buffer. The sum now differs from the expected sum by 1. |
| 346 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 347 | `    run_trial(&w, &p, &r, &sink);` | Runs the fourth trial. |
| 348 | `    trial_check(r.sink_ok == 0, "sink check fails after one word of the buffer is changed", bytes);` | So `sink_ok` must be 0. This proves that the sink check can fail, and that `oldread` reads the last word of its range. |
| 350 | `    struct counts c[3] = { { .enabled = 0, .running = 0 }, { .enabled = 100, .running = 100 }, { .enabled = 200, .running = 150 } };` | `c`: three counter readings that are written here. They stand for the borders of two target windows. `enabled` and `running` are the times in ns for which the counter group was enabled and for which it ran. In target window 1 (the second one, the count starts at 0) the counters ran 50 ns of 100 ns. |
| 351 | `    trial_check(first_multiplexed(c, 2) == 1, "running time below enabled time is found in target window 1", 0);` | Checks `first_multiplexed` of the runner source on the three readings. It must return 1: the index of the first target window whose counters ran for less time than they were enabled. |
| 352 | `    c[2].running = 200;` | Makes the running time of target window 1 equal to its enabled time. |
| 353 | `    trial_check(first_multiplexed(c, 2) == -1, "equal running and enabled time is not called multiplexed", 0);` | With equal times `first_multiplexed` must return -1. |
| 354 | `    unguard(w.t.a, n);` | Releases the buffer. |
| 355 | `}` | Ends the function `test_trial`. |

### Function `test_trial_hot`: the same checks with the option `--hot-copy` (lines 356 to 416)

| Line | Source | Explanation |
|---:|---|---|
| 357 | `/* bwx10+ */` | Comment: the marker `bwx10+`. The text up to the line with `bwx10-` (line 526) was added for bwx10. |
| 358 | `/* The window checks of test_trial() with --hot-copy: run_trial() then calls` | Comment: `test_trial_hot` holds the window checks of `test_trial` with the option `--hot-copy`. `run_trial` then calls ... |
| 359 | ` * timed_sequence_hot(). */` | Comment: ... `timed_sequence_hot`. |
| 360 | `static void test_trial_hot(void)` | Starts the function `test_trial_hot`. It holds the plan and the window checks of `test_trial`, with `plan.hot_copy = 1`. `run_trial` then calls `timed_sequence_hot` in place of `timed_sequence`. What it proves: `timed_sequence_hot` writes consistent window records too, and it leaves the plan fields of each record unchanged. What it cannot prove: anything about the whole-chip test. `--hot-copy` is an option of the trial mode only [Ref1]. |
| 361 | `{` | Opens the body of `test_trial_hot`. |
| 362 | `    size_t bytes = 1UL << 20, n = bytes / 8;` | `bytes`: the buffer size, 1 MiB. `n`: the same size in words. |
| 363 | `    int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");` | The indexes of the kernels `oldread`, `read` (in `rd`) and `asmread`, as in line 289. |
| 364 | `    struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,` | `p`: the same plan as in `test_trial` (lines 290 to 292): 3 target windows of 12 ms, no counters, bins on. |
| 365 | `                       .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },` | Continues the plan: 1 window of `asmread` for 4 ms, and 4 prefix windows of `oldread` with 2 ms each. |
| 366 | `                       .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };` | Ends the plan: 1 predecessor window of `read` on 65536 B for 3 ms, and `oldread` as the target kernel. |
| 367 | `    struct win win[9], win0[9];` | `win`: the 9 window records of the trial. `win0`: a second set of the 9 records. The trial does not use it. It keeps the plan fields for the comparison of lines 388 to 389. |
| 368 | `    struct bin bin[9];` | `bin`: storage for 9 bins. |
| 369 | `    struct trec r = { .win = win, .nw = trial_windows(&p) };` | `r`: the record of the trial, with the number of windows from `trial_windows`. |
| 370 | `    struct tw w;` | `w`: the worker record. |
| 371 | `    volatile uint64_t sink = 0;` | `sink`: the variable that receives the sum of an old read kernel. |
| 372 | `    int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1, kept = 1;` | Six result flags: the five of `test_trial` and `kept`. |
| 374 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 375 | `    w.t.group_fd = -1;` | `group_fd = -1`: the worker has no counter group. |
| 376 | `    w.v = 0x9E3779B97F4A7C15ULL * 11;` | `w.v`: the value of every word of the buffer. It differs from the value of `test_trial`. |
| 377 | `    w.t.a = guarded(n);` | The buffer of the worker: a guarded buffer of 1 MiB. |
| 378 | `    for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 379 | `        w.t.a[i] = w.v;` | Every word gets the value `w.v`. |
| 381 | `    plan.hot_copy = 1;` | Sets the global switch of the option `--hot-copy`. With it `run_trial` calls `timed_sequence_hot`. |
| 382 | `    set_windows(&p, win, bin);` | Fills `win` from the plan. |
| 383 | `    set_windows(&p, win0, bin);` | Fills `win0` from the same plan. |
| 384 | `    printf("call,trial_hot,%zu\n", bytes);` | Prints the line `call,trial_hot,1048576` before the trial runs. |
| 385 | `    run_trial(&w, &p, &r, &sink);` | Runs the trial on `win`. |
| 386 | `    for (int i = 0; i < r.nw; i++) {` | Loop over the 9 window records after the trial. |
| 387 | `        const struct win *x = &win[i], *x0 = &win0[i];` | `x`: the record of window `i` in `win`. `x0`: the same record in `win0`. |
| 388 | `        kept &= x->k == x0->k && x->phase == x0->phase && x->widx == x0->widx && x->size == x0->size &&` | `kept`: after the trial, the eight plan fields of the record in `win` equal those in `win0`. This line compares the kernel, the phase, the window index and the range size ... |
| 389 | `                x->passes == x0->passes && x->dur_ns == x0->dur_ns && x->bin == x0->bin && x->bin_cap == x0->bin_cap;` | ... and the passes between two clock reads, the duration, the bin storage and the bin capacity. |
| 390 | `        whole &= x->bytes > 0 && x->bytes % x->size == 0;` | `whole`: more than 0 bytes, and a multiple of the range size (line 313). |
| 391 | `        groups &= x->bytes % CHECK_BYTES == 0;` | `groups`: the bytes are a multiple of 8 MiB (line 314). |
| 392 | `        lasts &= x->t_end - x->t_start >= x->dur_ns;` | `lasts`: the window lasted at least its requested duration (line 315). |
| 393 | `        order &= x->t_end > x->t_start && (i == 0 \|\| x->t_start >= win[i - 1].t_end);` | `order`: the times do not go back (line 316). |
| 394 | `        if (x->phase == PH_TARGET) {` | Branch for a target window. |
| 395 | `            bins_ok &= x->nbin >= 1 && x->nbin <= x->bin_cap && x->bin[x->nbin - 1].bytes == x->bytes &&` | `bins_ok`, target window: 1 to `bin_cap` bins, and the last bin holds the bytes of the window ... |
| 396 | `                       x->bin[x->nbin - 1].t_end == x->t_end;` | ... and the end time of the window. |
| 397 | `            for (int b = 1; b < x->nbin; b++)` | Loop over the bins after the first one. |
| 398 | `                bins_ok &= x->bin[b].t_end > x->bin[b - 1].t_end && x->bin[b].bytes > x->bin[b - 1].bytes;` | Time and bytes must rise from bin to bin. |
| 399 | `        } else {` | Branch for every other window. |
| 400 | `            bins_ok &= x->nbin == 0;` | `bins_ok`, other window: it has no bin. |
| 401 | `        }` | Ends the `if` of line 394. |
| 402 | `    }` | Ends the loop of line 386. |
| 403 | `    trial_check(kept, "hot copy: the plan fields of every window record are unchanged", bytes);` | Prints the result of `kept`. Every check name of this function starts with `hot copy:`. |
| 404 | `    trial_check(whole, "hot copy: every window holds whole passes and more than 0 bytes", bytes);` | Prints the result of `whole`. |
| 405 | `    trial_check(groups, "hot copy: every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);` | Prints the result of `groups`. |
| 406 | `    trial_check(lasts, "hot copy: every window lasts at least its requested duration", bytes);` | Prints the result of `lasts`. |
| 407 | `    trial_check(order, "hot copy: timestamps do not go back from window to window", bytes);` | Prints the result of `order`. |
| 408 | `    trial_check(bins_ok, "hot copy: the last bin of a target window ends the window and holds its bytes", bytes);` | Prints the result of `bins_ok`. |
| 409 | `    trial_check(r.sink_ok == 1, "hot copy: sink holds the sum after a trial that ends in old read", bytes);` | The sink check: `r.sink_ok` must be 1 after this trial, which ends with `oldread`. |
| 410 | `    w.t.a[n - 1] ^= 1;` | Flips the lowest bit of the last word of the buffer. |
| 411 | `    set_windows(&p, win, bin);` | Fills the window records again. |
| 412 | `    run_trial(&w, &p, &r, &sink);` | Runs the trial again. |
| 413 | `    trial_check(r.sink_ok == 0, "hot copy: sink check fails after one word of the buffer is changed", bytes);` | The sink check must fail now: `r.sink_ok` must be 0. |
| 414 | `    plan.hot_copy = 0;` | Sets `plan.hot_copy` back to 0. |
| 415 | `    unguard(w.t.a, n);` | Releases the buffer. |
| 416 | `}` | Ends the function `test_trial_hot`. |

### `on_touch`, `struct toucher` and `toucher`: the helpers of `test_hot_touch` (lines 417 to 460)

| Line | Source | Explanation |
|---:|---|---|
| 418 | `static uint8_t *touch_page; /* the page that holds the window record of test_hot_touch */` | `touch_page`: the address of the page that holds the window record of `test_hot_touch`. |
| 419 | `static volatile int touch_faults;` | `touch_faults`: the count of the faults in that page. It is `volatile`: a signal handler changes it. |
| 421 | `/* A fault in the page of the window record: count it and make the page` | Comment: on a fault in the page of the window record the handler counts the fault and makes the page ... |
| 422 | ` * usable, so the access runs again. Any other fault ends the process. */` | Comment: ... usable, so the access runs again. Any other fault ends the process. |
| 423 | `static void on_touch(int sig, siginfo_t *si, void *ctx)` | Starts the function `on_touch`, the `SIGSEGV` handler of `test_hot_touch`. |
| 424 | `{` | Opens the body of `on_touch`. |
| 425 | `    uintptr_t at = (uintptr_t)si->si_addr;` | `at`: the address of the faulting access. |
| 426 | `    (void)ctx;` | Marks the argument `ctx` as not used. |
| 427 | `    if (at < (uintptr_t)touch_page \|\| at >= (uintptr_t)touch_page + (uintptr_t)page_bytes) {` | Tests whether the address lies outside the page of the window record. |
| 428 | `        signal(sig, SIG_DFL);` | A fault at any other address: the handler sets `SIGSEGV` back to its default action. |
| 429 | `        return;` | After the return the access faults again and ends the process. |
| 430 | `    }` | Ends the `if` of line 427. |
| 431 | `    touch_faults++;` | A fault inside this page: the handler adds 1 to the count ... |
| 432 | `    mprotect(touch_page, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | ... and makes the page readable and writable. After the return the access runs again and succeeds. |
| 433 | `}` | Ends the function `on_touch`. |
| 435 | `struct toucher {` | `struct toucher`: the data of the second thread of `test_hot_touch`. |
| 436 | `    struct tw *w;` | `w`: the worker record whose trace the second thread reads. |
| 437 | `    int found;              /* the first kernel call of the window was seen in the trace */` | `found`: the flag that the second thread sets when it has seen the first kernel call of the window in the trace. |
| 438 | `    int64_t t_none, t_done; /* after the page became PROT_NONE; after it became usable again */` | Two clock values in ns. `t_none`: read after the page became `PROT_NONE`. `t_done`: read after the page became usable again. |
| 439 | `};` | Ends the definition of `struct toucher`. |
| 441 | `static void *toucher(void *arg)` | Starts the function `toucher`, the body of the second thread. |
| 442 | `{` | Opens the body of `toucher`. |
| 443 | `    struct toucher *h = arg;` | `h`: the data of the thread, passed through `arg`. |
| 444 | `    struct timespec ms20 = { 0, 20000000L };` | `ms20`: a time of 0 s and 20000000 ns, which is 20 ms. |
| 445 | `    int64_t limit = now_ns() + 5000000000L;` | `limit`: the clock value 5 s after this moment. `now_ns` of the runner source reads the clock `CLOCK_MONOTONIC` in ns. |
| 446 | `    while (!h->found && now_ns() < limit) {` | Reads the trace of the worker again and again, for at most 5 s, until it holds the event. The loop does not sleep between two passes. |
| 447 | `        long nlog = *(volatile long *)&h->w->nlog;` | `nlog`: the number of events in the trace at this moment. The `volatile` cast makes the compiler read the number from memory in every pass. The other thread changes it. |
| 448 | `        for (long i = 0; i < nlog; i++)` | Loop over the events of the trace. |
| 449 | `            if (h->w->log[i].ev == EV_KERNEL_FIRST)` | Looks for the event `EV_KERNEL_FIRST`. The worker writes this event at the first kernel call of a window. |
| 450 | `                h->found = 1;` | The event was found. |
| 451 | `    }` | Ends the loop of line 446. |
| 452 | `    if (!h->found)` | If the event did not appear within 5 s ... |
| 453 | `        return NULL;` | ... the thread returns and changes nothing. |
| 454 | `    mprotect(touch_page, (size_t)page_bytes, PROT_NONE);` | Makes the page of the window record `PROT_NONE` ... |
| 455 | `    h->t_none = now_ns();` | ... and reads the clock (`t_none`). |
| 456 | `    nanosleep(&ms20, NULL);` | Sleeps 20 ms. |
| 457 | `    mprotect(touch_page, (size_t)page_bytes, PROT_READ \| PROT_WRITE);` | Makes the page readable and writable again ... |
| 458 | `    h->t_done = now_ns();` | ... and reads the clock (`t_done`). |
| 459 | `    return NULL;` | Ends the thread. |
| 460 | `}` | Ends the function `toucher`. |

### Functions `hot_touch_run` and `test_hot_touch` (lines 461 to 524)

| Line | Source | Explanation |
|---:|---|---|
| 462 | `/* One target window of 200 ms of asmread on 1 MiB, with or without` | Comment: `hot_touch_run` runs one target window of 200 ms of `asmread` on 1 MiB, with or without ... |
| 463 | ` * --hot-copy. faults: faults in the page of the window record. inside: the` | Comment: ... the option `--hot-copy`. The result `faults` is the number of faults in the page of the window record. The result `inside` says whether the ... |
| 464 | ` * time in which the page was PROT_NONE lies between the start clock read and` | Comment: ... time in which the page was `PROT_NONE` lies between the start clock read and ... |
| 465 | ` * the end clock read of the window. */` | Comment: ... the end clock read of the window. |
| 466 | `static void hot_touch_run(int hot, int *faults, int *inside)` | Starts the function `hot_touch_run`. `hot` selects the function under test: 0 is `timed_sequence`, 1 is `timed_sequence_hot`. Result `faults`: the number of faults in the page of the record. Result `inside`: 1 when the `PROT_NONE` time lay between the start clock read and the end clock read of the window. |
| 467 | `{` | Opens the body of `hot_touch_run`. |
| 468 | `    size_t bytes = 1UL << 20, n = bytes / 8, wn = (size_t)page_bytes / 8;` | `bytes` and `n`: the buffer size, 1 MiB, in bytes and in words. `wn`: the number of words of one page, for the page of the window record. |
| 469 | `    struct trial p = { .nwin = 1, .win_ms = 200, .count = CS_CLOSED, .bins = 0,` | `p`: the plan. One trial with a single target window of 200 ms. No counters (`CS_CLOSED`), no bins. |
| 470 | `                       .prev = { -1, 0, 0 }, .pfx = { -1, 0, 0 }, .pred = { -1, 0, 0 },` | Continues the plan: no other window. A kernel index of -1 means that the part is absent. |
| 471 | `                       .tgt = { kernel_named("asmread"), bytes, 0 } };` | Ends the plan: the target window runs `asmread` on 1 MiB. |
| 472 | `    struct win *win = (struct win *)guarded(wn);` | The window record `win` lies alone in a guarded page. So the page can be made `PROT_NONE` without an effect on other data. |
| 473 | `    struct trec r = { .win = win, .nw = 1 };` | `r`: the record of the trial, with 1 window. |
| 474 | `    struct tw w;` | `w`: the worker record. |
| 475 | `    struct toucher h = { .w = &w };` | `h`: the data of the second thread. It points to the worker record. |
| 476 | `    struct sigaction sa, old;` | `sa`: the new setting for `SIGSEGV`. `old`: the setting from before. |
| 477 | `    volatile uint64_t sink = 0;` | `sink`: the variable for the sum of an old read kernel. This trial runs no old read. |
| 478 | `    pthread_t tid;` | `tid`: the identifier of the second thread. |
| 480 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 481 | `    w.t.group_fd = -1;` | `group_fd = -1`: the worker has no counter group. |
| 482 | `    w.v = 0x9E3779B97F4A7C15ULL * 13;` | `w.v`: the value of every word of the buffer. |
| 483 | `    w.t.a = guarded(n);` | The buffer of the worker: a guarded buffer of 1 MiB. |
| 484 | `    for (size_t i = 0; i < n; i++)` | Loop over all words of the buffer. |
| 485 | `        w.t.a[i] = w.v;` | Every word gets the value `w.v`. |
| 486 | `    w.log = calloc(TRACE_CAP, sizeof *w.log); /* the trace shows the second thread that the window runs */` | Allocates a trace (`w.log`) with room for `TRACE_CAP` events. The runner source sets `TRACE_CAP` to 1048576 events. `run_trial` writes events to the trace, and the second thread reads them. Comment: the trace shows the second thread that the window runs. |
| 487 | `    w.cur_phase = -1;` | `cur_phase = -1` makes the first kernel call write the event `EV_KERNEL_FIRST`. |
| 488 | `    if (!w.log) {` | Tests whether the allocation failed. |
| 489 | `        perror("calloc");` | On failure: prints the word `calloc` and the reason. |
| 490 | `        exit(2);` | On failure: the process ends with exit status 2. |
| 491 | `    }` | Ends the `if` of line 488. |
| 492 | `    set_windows(&p, win, NULL);` | Fills the window record from the plan. `NULL`: there is no bin storage. |
| 493 | `    touch_page = (uint8_t *)win;` | Stores the address of the page of the record for the handler and for the second thread. |
| 494 | `    touch_faults = 0;` | Sets the fault count to 0. |
| 495 | `    memset(&sa, 0, sizeof sa);` | Sets every byte of `sa` to 0. |
| 496 | `    sa.sa_sigaction = on_touch;` | The handler is `on_touch`. |
| 497 | `    sa.sa_flags = SA_SIGINFO;` | The flag `SA_SIGINFO` makes Linux pass the fault address to the handler. |
| 498 | `    sigaction(SIGSEGV, &sa, &old);` | Installs `on_touch` for `SIGSEGV`. `old` keeps the setting from before. |
| 499 | `    plan.hot_copy = hot;` | Sets `plan.hot_copy` to `hot`. |
| 500 | `    printf("call,%s,%zu\n", hot ? "hot_touch_hot" : "hot_touch_plain", bytes);` | Prints the `call` line: `call,hot_touch_hot,1048576` or `call,hot_touch_plain,1048576`. |
| 501 | `    if (pthread_create(&tid, NULL, toucher, &h) != 0) {` | Starts the second thread with the function `toucher`. The self-test pins neither this thread nor the main thread to one CPU. |
| 502 | `        perror("pthread_create");` | On failure: prints the word `pthread_create` and the reason. |
| 503 | `        exit(2);` | On failure: the process ends with exit status 2. |
| 504 | `    }` | Ends the `if` of line 501. |
| 505 | `    run_trial(&w, &p, &r, &sink);` | Runs the trial in this thread. |
| 506 | `    pthread_join(tid, NULL);` | Waits for the second thread. |
| 507 | `    plan.hot_copy = 0;` | Sets `plan.hot_copy` back to 0. |
| 508 | `    sigaction(SIGSEGV, &old, NULL);` | Restores the `SIGSEGV` setting from before. |
| 509 | `    *faults = touch_faults;` | Result `faults`: the fault count. |
| 510 | `    *inside = h.found && h.t_none > win[0].t_start && h.t_done < win[0].t_end;` | `inside` is 1 when the event was found, `t_none` is later than the start clock read of the window, and `t_done` is earlier than its end clock read. |
| 511 | `    free(w.log);` | Releases the trace ... |
| 512 | `    unguard(w.t.a, n);` | ... the buffer ... |
| 513 | `    unguard((uint64_t *)win, wn);` | ... and the page of the record. |
| 514 | `}` | Ends the function `hot_touch_run`. |
| 516 | `static void test_hot_touch(void)` | Starts the function `test_hot_touch`. It runs `hot_touch_run` twice and makes three checks. What it proves: the machine code of `timed_sequence_hot` did not read or write the page of the record while it was `PROT_NONE` (20 ms). What it cannot prove: the same for the rest of the 200 ms window. Also, the whole-chip test does not use `--hot-copy` [Ref6]. |
| 517 | `{` | Opens the body of `test_hot_touch`. |
| 518 | `    int f_plain, in_plain, f_hot, in_hot;` | The four results: faults and `inside` of the plain run, faults and `inside` of the hot run. |
| 519 | `    hot_touch_run(0, &f_plain, &in_plain);` | First run, with `timed_sequence`. |
| 520 | `    hot_touch_run(1, &f_hot, &in_hot);` | Second run, with `timed_sequence_hot`. |
| 521 | `    trial_check(in_plain && in_hot, "hot touch: the 20 ms with the window record in a PROT_NONE page lie inside the window", 0);` | Check 1: in both runs the `PROT_NONE` time lay inside the window. |
| 522 | `    trial_check(f_plain >= 1, "hot touch: timed_sequence touches the window record between the first and the last pass", 0);` | Check 2: `timed_sequence` faulted at least once. It reads the record in every pass. So this run shows that the method can see a touch. |
| 523 | `    trial_check(f_hot == 0, "hot touch: timed_sequence_hot does not touch the window record between the first and the last pass", 0);` | Check 3: `timed_sequence_hot` did not fault. |
| 524 | `}` | Ends the function `test_hot_touch`. |

### Functions `map_lines` and `test_evict`: the evict step unmaps its memory (lines 525 to 555)

| Line | Source | Explanation |
|---:|---|---|
| 526 | `/* bwx10- */` | Comment: the marker `bwx10-`. It ends the block of text that was added for bwx10. |
| 527 | `/* bwx11+ */` | Comment: the marker `bwx11+`. The text up to the line with `bwx11-` (line 555) was added for bwx11. |
| 528 | `static long map_lines(void)` | Starts the function `map_lines`. It counts the lines of the file `/proc/self/maps`. Linux prints one line per memory mapping of the process in this file. |
| 529 | `{` | Opens the body of `map_lines`. |
| 530 | `    FILE *f = fopen("/proc/self/maps", "r");` | Opens the file for reading. |
| 531 | `    long n = 0;` | `n`: the count of lines. |
| 532 | `    int c;` | `c`: the character that was read last. |
| 533 | `    if (!f)` | If the file cannot be opened ... |
| 534 | `        return -1;` | ... the result is -1. |
| 535 | `    while ((c = getc(f)) != EOF)` | Reads the file character by character up to its end (`EOF`). |
| 536 | `        n += c == '\n';` | Adds 1 to `n` for every line end. |
| 537 | `    fclose(f);` | Closes the file. |
| 538 | `    return n;` | Returns the count. |
| 539 | `}` | Ends the function `map_lines`. |
| 541 | `static void test_evict(void)` | Starts the function `test_evict`. It checks the evict step of the trial mode (option `--evict-mb`) with 4 MiB. What it proves: the step returns no error, its second clock read is later than its first, and the number of mappings is the same as before. What it cannot prove: that the step removes the benchmark buffer from the caches. No check measures the content of a cache. The whole-chip test does not use `--evict-mb` [Ref6]. |
| 542 | `{` | Opens the body of `test_evict`. |
| 543 | `    long before = (map_lines(), map_lines()), saved = evict_mb; /* the first call lets stdio take its memory */` | Calls `map_lines` twice and keeps the second count in `before`. The comma operator gives the value of the second call. The comment gives the reason: the first call lets the C library take its memory for file reading. `saved` keeps the value of the global `evict_mb`, the size of the evict step in MiB. |
| 544 | `    int bad;` | `bad`: the return value of the step. |
| 545 | `    evict_mb = 4;` | Sets the size of the step to 4 MiB. |
| 546 | `    evict_t[0] = evict_t[1] = 0;` | Sets the two clock values of the step to 0. |
| 547 | `    bad = evict_step();` | Calls `evict_step` of the runner source. That function maps 4 MiB, writes one word per 64 B line in two passes, and unmaps the range. It returns 0, or -1 on an error. |
| 548 | `    evict_mb = saved;` | Sets `evict_mb` back to its old value. |
| 549 | `    trial_check(bad == 0, "evict: the step with 4 MiB returns no error", 0);` | Check 1: the step returned no error. |
| 550 | `    trial_check(evict_t[0] > 0 && evict_t[1] > evict_t[0], "evict: the clock read after the step is later than the one before it", 0);` | Check 2: the first clock value is above 0, and the second one is later than the first. `evict_step` reads the clock before its `mmap` and after its `munmap`. |
| 551 | `    trial_check(before > 0 && map_lines() == before, "evict: the range is unmapped again", 0);` | Check 3: the first count is above 0, and a new count of the mappings equals it. So the range is unmapped again. |
| 552 | `    evict_t[0] = evict_t[1] = 0;` | Sets the two clock values back to 0. |
| 553 | `}` | Ends the function `test_evict`. |
| 555 | `/* bwx11- */` | Comment: the marker `bwx11-`. It ends the block of line 527. |

### Function `test_round5`: the 26 new kernels in `kernels[]` (lines 556 to 593)

| Line | Source | Explanation |
|---:|---|---|
| 556 | `/* bwx12+ */` | Comment: the marker `bwx12+`. The text up to the line with `bwx12-` (line 593) was added for bwx12. |
| 557 | `/* Every kernel of round 5 stands in kernels[] exactly once, with the kind` | Comment: every kernel of round 5 must stand in `kernels[]` exactly once, with the kind ... |
| 558 | ` * that its name says. */` | Comment: ... that its name says. |
| 559 | `static void test_round5(void)` | Starts the function `test_round5`. `want` lists the 26 kernel names of round 5, each with the kind that its name says: 20 read, 4 write, 2 copy. What it proves: each name stands exactly once in `kernels[]` with that kind, and the table has 55 entries. The reason: the loop of `selftest` chooses the checks by the kind in `kernels[]`. A wrong kind gives a kernel the wrong checks. What it cannot prove: that the function behind a name holds the instructions that the name says, for example 256 nop in `read_nop256`. The objdump listing is the evidence [Ref7]. The name check covers no kernel of bwx11 or older. Of the six kernels of the whole-chip test it covers `read_nop256` only. The spec files `like.spec`, `cfwd.spec` and `crev.spec` of that test name the six. |
| 560 | `{` | Opens the body of `test_round5`. |
| 561 | `    static const struct {` | Starts the table `want`. It is constant and exists once for the whole program. |
| 562 | `        const char *name;` | `name`: the name of a kernel. |
| 563 | `        enum ktype type;` | `type`: the kind that the kernel must have in `kernels[]`. |
| 564 | `    } want[] = {` | Ends the type of one entry. The entries follow. |
| 565 | `        { "read_nop48", T_READ }, { "read_nop56", T_READ }, { "read_nop72", T_READ }, { "read_nop80", T_READ },` | Four read kernels with nop instructions: `read_nop48`, `read_nop56`, `read_nop72`, `read_nop80`. By the file comment of the runner source they are the `asmread` loop with that many nop after its 8 loads. The kind is `T_READ`, a read kernel that returns nothing. |
| 566 | `        { "read_nop88", T_READ }, { "read_nop112", T_READ }, { "read_nop160", T_READ }, { "read_nop192", T_READ },` | Four more of the same family: `read_nop88`, `read_nop112`, `read_nop160`, `read_nop192`. |
| 567 | `        { "read_nop256", T_READ },` | The last one of this family, `read_nop256`. |
| 568 | `        { "read_dadd2", T_READ }, { "read_dadd4", T_READ }, { "read_dadd8", T_READ }, { "read_dadd16", T_READ },` | Four read kernels with vector adds: `read_dadd2`, `read_dadd4`, `read_dadd8`, `read_dadd16`. By the file comment of the runner source they are the `asmread` loop with 2, 4, 8 or 16 vector adds after its 8 loads. Each add takes a register that the same loop pass loaded. |
| 569 | `        { "read_iadd16", T_READ },` | `read_iadd16`: the `asmread` loop with 16 vector adds that take no loaded register. By the same comment it is the control of `read_dadd16`. |
| 570 | `        { "read_sp24", T_READ }, { "read_sp32", T_READ }, { "read_sp40", T_READ }, { "read_sp48", T_READ },` | Four read kernels `read_sp24`, `read_sp32`, `read_sp40`, `read_sp48`. By the same comment they are the `read_sparse` loop (128 B and 4 loads per loop pass) with that many nop in place of 9. |
| 571 | `        { "read_sp56", T_READ },` | `read_sp56`, the last one of this family. |
| 572 | `        { "read_1pl_nop96", T_READ },` | `read_1pl_nop96`: by the same comment the `read_1pl` loop with 96 nop after its 4 loads. |
| 573 | `        { "write_nop32", T_WRITE }, { "write_nop96", T_WRITE }, { "write_nop128", T_WRITE }, { "write_nop256", T_WRITE },` | The four write kernels `write_nop32`, `write_nop96`, `write_nop128`, `write_nop256`, with the kind `T_WRITE`. By the same comment they are the `asmwrite` loop with that many nop after its 8 stores. |
| 574 | `        { "copy_nop96", T_COPY }, { "copy_nop192", T_COPY },` | The two copy kernels `copy_nop96` and `copy_nop192`, with the kind `T_COPY`. By the same comment they are the `asmcopy` loop with that many nop after its 8 stores. |
| 575 | `    };` | Ends the table `want`. |
| 576 | `    int ok = 1;` | `ok`: the result of the name check. 1 means passed. |
| 577 | `    for (size_t i = 0; i < sizeof want / sizeof want[0]; i++) {` | Loop over the entries of `want`. `sizeof want / sizeof want[0]` is the number of entries. |
| 578 | `        int found = 0, kind = 1;` | `found`: how many entries of `kernels[]` have the wanted name. `kind`: 1 as long as each of them has the wanted kind. |
| 579 | `        for (int k = 0; k < K_COUNT; k++)` | Loop over all entries of `kernels[]`. |
| 580 | `            if (!strcmp(want[i].name, kernels[k].name)) {` | Tests whether the names are equal (`strcmp` returns 0). |
| 581 | `                found++;` | Counts the entry. |
| 582 | `                kind &= kernels[k].type == want[i].type;` | Compares its kind with the wanted kind. |
| 583 | `            }` | Ends the `if` of line 580. |
| 584 | `        if (found != 1 \|\| !kind) {` | A name that is missing, that stands twice or more, or that has another kind ... |
| 585 | `            printf("# round 5: kernel %s stands %d times in kernels[]%s\n", want[i].name, found, kind ? "" : ", with another kind");` | ... prints a line that starts with `#`: the kernel name, how many times it stands in `kernels[]`, and the words `, with another kind` when a kind differs. |
| 586 | `            ok = 0;` | Then the name check fails. |
| 587 | `        }` | Ends the `if` of line 584. |
| 588 | `    }` | Ends the loop of line 577. |
| 589 | `    trial_check(ok, "round 5: each of the 26 new kernels stands once in kernels[] with its kind", 0);` | Prints the result row of the name check. Its check name starts with `round 5: each of the 26 new kernels`. |
| 590 | `    trial_check(K_COUNT == 55, "round 5: kernels[] has 55 entries (29 of bwx11 and 26 new)", 0);` | The statement of a second check: the number of entries of `kernels[]` must be 55. By the check name these are the 29 kernels of bwx11 and the 26 new ones. |
| 591 | `}` | Ends the function `test_round5`. |
| 593 | `/* bwx12- */` | Comment: the marker `bwx12-`. It ends the block of line 556. |

### Functions `has_line` and `emitted`: the text that `emit_trial` prints (lines 594 to 624)

| Line | Source | Explanation |
|---:|---|---|
| 594 | `static int has_line(const char *text, const char *line)` | Starts the function `has_line`. It is true when `text` holds `line` as a whole line. |
| 595 | `{` | Opens the body of `has_line`. |
| 596 | `    size_t n = strlen(line);` | `n`: the length of `line` in characters. |
| 597 | `    for (const char *s = text; (s = strstr(s, line)) != NULL; s += n)` | `strstr` finds the next place in the text that holds `line`. The loop goes from match to match until there is no more. |
| 598 | `        if ((s == text \|\| s[-1] == '\n') && s[n] == '\n')` | The match counts when it starts at the text start or directly after a line end, and a line end follows it. |
| 599 | `            return 1;` | Then the result is 1. |
| 600 | `    return 0;` | No such match: the result is 0. |
| 601 | `}` | Ends the function `has_line`. |
| 603 | `/* The text that emit_trial() prints for the record r of the trial p. stdout` | Comment: `emitted` returns the text that `emit_trial` prints for the record `r` of the trial `p`. The standard output ... |
| 604 | ` * is a memory stream during the call (glibc lets a program assign stdout). */` | Comment: ... is a memory stream during the call. The C library glibc lets a program assign `stdout`. |
| 605 | `static char *emitted(struct tw *w, struct trial *p, struct trec *r)` | Starts the function `emitted`. It returns the text that `emit_trial` of the runner source prints for a given plan and record. |
| 606 | `{` | Opens the body of `emitted`. |
| 607 | `    char *text = NULL;` | `text`: will point to the printed text. |
| 608 | `    size_t len = 0;` | `len`: will hold its length in bytes. |
| 609 | `    FILE *out = stdout, *mem = open_memstream(&text, &len);` | `out`: keeps the real standard output. `mem`: a stream that writes into memory (`open_memstream`). The C library sets `text` and `len` when the stream is flushed or closed. |
| 610 | `    if (!mem) {` | Tests whether the stream could not be opened. |
| 611 | `        perror("open_memstream");` | On failure: prints the word `open_memstream` and the reason. |
| 612 | `        exit(2);` | On failure: the process ends with exit status 2. |
| 613 | `    }` | Ends the `if` of line 610. |
| 614 | `    fflush(out);` | Writes out what the real standard output still holds in its buffer. |
| 615 | `    plan.tr = p;` | Points the global `plan.tr` to the test plan ... |
| 616 | `    rec = r;` | ... and the global `rec` to the test record. So `emit_trial(w, 0)` prints trial 0 from them. |
| 617 | `    stdout = mem;` | Replaces `stdout` by the memory stream. |
| 618 | `    emit_trial(w, 0);` | `emit_trial` prints the rows of trial 0. They go into memory, not to the output of the self-test. |
| 619 | `    stdout = out;` | Restores the real `stdout`. |
| 620 | `    fclose(mem);` | Closes the memory stream. After this `text` holds the whole printed text. |
| 621 | `    plan.tr = NULL;` | Sets `plan.tr` back to `NULL` ... |
| 622 | `    rec = NULL;` | ... and `rec` back to `NULL`. |
| 623 | `    return text;` | Returns the printed text. The caller frees it. |
| 624 | `}` | Ends the function `emitted`. |

### Function `test_emit`: the output rows of one trial (lines 625 to 674)

| Line | Source | Explanation |
|---:|---|---|
| 626 | `/* emit_trial() on a record with known values. Every value differs from the` | Comment: `test_emit` runs `emit_trial` on a record with known values. Every value differs from the ... |
| 627 | ` * value of the field beside it, so a row that prints the wrong field fails. */` | Comment: ... value of the field beside it. So a row that prints the wrong field fails. The record does not keep this rule in one place: reading 0 and reading 1 hold the same value for the enabled time and for the running time (lines 638 to 639). So the first C row must show 100 ns in both fields (line 653). The second C row must show 100 ns and 50 ns. So the check still fails for a row that swaps the two fields. |
| 628 | `static void test_emit(void)` | Starts the function `test_emit`. It writes a trial record by hand: 1 predecessor window, 2 target windows, three counter readings, two page snapshots, CPU times and context-switch counts. The record holds three intended defects: no huge-page value in the second snapshot (-1), counters that ran 50 ns of 100 ns in target window 1, and `sink_ok = 0`. What it proves: `emit_trial` prints the values of this record in the right fields of the C, P, E and X rows. What it cannot prove: anything about the rows of the whole-chip csv files. The interval mode prints its rows with other code [Ref1]. The W rows are printed here, and no check compares them. |
| 629 | `{` | Opens the body of `test_emit`. |
| 630 | `    int oldread = kernel_named("oldread");` | The index of the kernel `oldread` in `kernels[]`. |
| 631 | `    struct trial p = { .nwin = 2, .count = CS_READ };` | `p`: the plan. It has 2 target windows and the counter state `CS_READ`: the timed sequence reads the counter group at the borders of the target windows. |
| 632 | `    struct win win[3] = {` | `win`: three window records, written by hand. |
| 633 | `        { .k = oldread, .phase = PH_PRED, .widx = 0, .size = 4096, .bytes = 8192, .t_start = t_base_ns + 1000, .t_end = t_base_ns + 2000 },` | Window 0, the predecessor window: kernel `oldread`, range size 4096 B, 8192 bytes counted, start 1000 ns and end 2000 ns after `t_base_ns`. `t_base_ns` is the clock value at the start of the process. The rows print times relative to it. |
| 634 | `        { .k = oldread, .phase = PH_TARGET, .widx = 0, .size = 4096, .bytes = 12288, .t_start = t_base_ns + 2100, .t_end = t_base_ns + 3100 },` | Window 1, target window 0: 12288 bytes, from 2100 ns to 3100 ns. It starts 100 ns after the end of the predecessor window. |
| 635 | `        { .k = oldread, .phase = PH_TARGET, .widx = 1, .size = 4096, .bytes = 16384, .t_start = t_base_ns + 3400, .t_end = t_base_ns + 4400 },` | Window 2, target window 1: 16384 bytes, from 3400 ns to 4400 ns. It starts 300 ns after the end of target window 0. |
| 636 | `    };` | Ends the three window records. |
| 637 | `    /* three readings; the second window ran its counters for 50 of 100 ns */` | Comment: three counter readings follow. The second target window ran its counters for 50 ns of 100 ns. |
| 638 | `    struct counts c[3] = { { .cpu_ns = 500, .enabled = 1000, .running = 1000, .val = { 70 } },` | `c`: the three counter readings. Reading 0: thread CPU time 500 ns, enabled time 1000 ns, running time 1000 ns, event count 70. |
| 639 | `                           { .cpu_ns = 800, .enabled = 1100, .running = 1100, .val = { 75 } },` | Reading 1: thread CPU time 800 ns, enabled time 1100 ns, running time 1100 ns, event count 75. |
| 640 | `                           { .cpu_ns = 1400, .enabled = 1200, .running = 1150, .val = { 82 } } };` | Reading 2: thread CPU time 1400 ns, enabled time 1200 ns, running time 1150 ns, event count 82. So between reading 1 and reading 2 the counters were enabled for 100 ns and ran for 50 ns. This is the second intended defect. |
| 641 | `    struct trec r = { .win = win, .nw = 3, .cnt = c, .pg = { { 8192, 4096 }, { 8192, -1 } },` | `r`: the trial record. It has the 3 windows, the readings `c`, and two page snapshots. The first snapshot: 8192 kB, of them 4096 kB in huge pages. The second: 8192 kB and -1, which stands for no huge-page value. This is the first intended defect. |
| 642 | `                      .vm = { { 1, 2, 3, 4 }, { 5, 6, 7, 8 } }, .cpu = { 10000, 13000 },` | Continues the record: the four counters of `/proc/vmstat` in each snapshot (1 to 4, then 5 to 8), and the thread CPU time before and after the timed sequence (10000 ns and 13000 ns). |
| 643 | `                      .nvcsw = { 5, 7 }, .nivcsw = { 10, 13 }, .state = CS_READ, .sink_ok = 0 };` | Ends the record: 5 and 7 voluntary context switches before and after, 10 and 13 involuntary ones, the counter state `CS_READ`, and `sink_ok = 0`. The value 0 says that the sink check failed. This is the third intended defect. |
| 644 | `    struct tw w;` | `w`: a worker record for `emit_trial`. |
| 645 | `    int nev = cfg.nev;` | `nev`: keeps the value of `cfg.nev`, the number of counter events in the configuration of the runner. |
| 646 | `    char *text;` | `text`: the printed text. |
| 648 | `    memset(&w, 0, sizeof w);` | Sets every byte of the worker record to 0. |
| 649 | `    w.t.group_fd = 0; /* emit_trial() only asks whether a group is open */` | `group_fd = 0` makes `emit_trial` treat the counter group as open. Comment: `emit_trial` only asks whether a group is open. |
| 650 | `    w.t.nopen = 1;` | One event counts as open. |
| 651 | `    cfg.nev = 1;` | `cfg.nev = 1` makes `emit_trial` print one event column. |
| 652 | `    text = emitted(&w, &p, &r);` | Gets the text that `emit_trial` prints for this record. |
| 653 | `    trial_check(has_line(text, "C,0,0,100,100,300,5") && has_line(text, "C,0,1,100,50,600,7"),` | The C rows must be `C,0,0,100,100,300,5` and `C,0,1,100,50,600,7`. After the trial number and the window number come four differences of two readings: enabled time, running time, thread CPU time (all in ns) and the event count. |
| 654 | `                "C rows hold the differences of two readings", 0);` | Continues the call of line 653: the name of the check, and 0 for the bytes field. |
| 655 | `    trial_check(has_line(text, "P,0,pre,8192,4096,1,2,3,4") && has_line(text, "P,0,post,8192,NA,5,6,7,8"),` | The P rows must be `P,0,pre,8192,4096,1,2,3,4` and `P,0,post,8192,NA,5,6,7,8`. The row with `pre` holds the first snapshot. The row with `post` holds the second, with `NA` for the missing huge-page value. |
| 656 | `                "P rows: pre holds the first snapshot and post the second", 0);` | Continues the call of line 655: the name of the check. |
| 657 | `    trial_check(has_line(text, "E,0,3400,3000,2,3,100,300,0,read"),` | The E row must be `E,0,3400,3000,2,3,100,300,0,read`: wall time 3400 ns, CPU time 3000 ns, 2 voluntary and 3 involuntary context switches, a gap of 100 ns before the first target window, a largest gap of 300 ns, sink check 0, counter state `read`. |
| 658 | `                "E row holds wall time and CPU time and both switch counts and both gaps each in its own field", 0);` | Continues the call of line 657: the name of the check. |
| 659 | `    trial_check(strstr(text, "\nX,0,coverage_na,") != NULL, "X row coverage_na when a snapshot has no huge-page value", 0);` | X row for defect 1: the text must hold a line that starts with `X,0,coverage_na,`. |
| 660 | `    trial_check(strstr(text, "\nX,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100\n") != NULL,` | X row for defect 2: the text must hold the line `X,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100`. |
| 661 | `                "X row count_multiplexed names the window that ran its counters for less time", 0);` | Continues the call of line 660: the name of the check. |
| 662 | `    trial_check(strstr(text, "\nX,0,sink,") != NULL, "X row sink when the sink check failed", 0);` | X row for defect 3: the text must hold a line that starts with `X,0,sink,`. |
| 663 | `    free(text);` | Frees the text. |
| 665 | `    /* The same record without the three defects must print no X row. */` | Comment: the same record without the three defects must print no X row. |
| 666 | `    r.pg[1].kb_huge = 4096;` | Removes defect 1: the second snapshot gets a huge-page value of 4096 kB. |
| 667 | `    c[2].running = 1200;` | Removes defect 2: the running time of reading 2 becomes 1200 ns. So the counters of target window 1 ran for the whole 100 ns. |
| 668 | `    r.sink_ok = 1;` | Removes defect 3: the sink check counts as passed. |
| 669 | `    text = emitted(&w, &p, &r);` | Prints the record again into a new text. |
| 670 | `    trial_check(strstr(text, "\nX,") == NULL && has_line(text, "E,0,3400,3000,2,3,100,300,1,read"),` | The text must now hold no line that starts with `X,`, and the E row must show sink check 1: `E,0,3400,3000,2,3,100,300,1,read`. |
| 671 | `                "no X row for a record without a defect", 0);` | Continues the call of line 670: the name of the check. |
| 672 | `    free(text);` | Frees the text. |
| 673 | `    cfg.nev = nev;` | Restores `cfg.nev`. |
| 674 | `}` | Ends the function `test_emit`. |

### Function `selftest`: the entry point of the option `--selftest` (lines 675 to 711)

| Line | Source | Explanation |
|---:|---|---|
| 676 | `static int selftest(void)` | Starts the function `selftest`. `main` of `bwx12.c` calls it for the argument `--selftest` and returns its value as the exit status [Ref1]. The self-test runs in the main thread and computes no rate. Only the checks of the trial mode read the clock. |
| 677 | `{` | Opens the body of `selftest`. |
| 678 | `    setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */` | `setvbuf` with `_IOLBF` makes the output line-buffered: each line is written when it is complete. So a kernel that ends the process cannot remove earlier lines. |
| 679 | `    printf("# selftest: page_bytes=%ld kernels=%d (%s); columns: kernel,check,bytes,result\n", page_bytes, K_COUNT,` | Prints the header line. It gives the page size in bytes, the number of kernels and the kind of build (line 680). It also names the four columns of a result row: `kernel`, `check`, `bytes`, `result`. |
| 680 | `           STANDIN ? "STAND-IN kernels, not AArch64" : "aarch64");` | Continues the call of line 679: the kind of build. The text is `aarch64` for a build with the real kernels. It is `STAND-IN kernels, not AArch64` for a build on a machine that is not AArch64 (the 64-bit Arm instruction set). There plain C loops take the place of the NEON and asm kernels. |
| 681 | `    if (page_bytes % 256 != 0) {` | A page size that is not a multiple of 256 B ... |
| 682 | `        fprintf(stderr, "page size is not a multiple of 256\n");` | ... prints a message to the error output ... |
| 683 | `        return 2;` | ... and ends the self-test with the value 2. |
| 684 | `    }` | Ends the `if` of line 681. |
| 685 | `    /* whole buffers of 1 page, 3 pages and 1 MiB */` | Comment: `test_size` gets whole buffers of 1 page, 3 pages and 1 MiB. |
| 686 | `    size_t words[] = { (size_t)page_bytes / 8, 3 * (size_t)page_bytes / 8, (1UL << 20) / 8 };` | `words`: the three buffer sizes of `test_size`, in words of 8 bytes: 1 page, 3 pages and 1 MiB. The whole-chip test calls a kernel on other sizes: 256 MiB for the warm-up, and chunks of 2 MiB in the timed interval [Ref1] [Ref6]. |
| 687 | `    /* one block: at the start of a page (guard before it) and at the end (guard after it) */` | Comment: `test_block` gets one block at the start of a page, with a guard page before it, and one at the end, with a guard page after it. |
| 688 | `    size_t offs[] = { 0, (size_t)page_bytes / 8 - 32 };` | `offs`: the two block offsets of `test_block`, in words: 0 for the first 256 B of a page, and the page size minus 32 words for the last 256 B. |
| 689 | `/* bwx12+ */` | Comment: the marker `bwx12+`. The next line was added for bwx12. |
| 690 | `    test_round5();` | `test_round5` runs first, before the loop uses the kinds of `kernels[]`. |
| 691 | `/* bwx12- */` | Comment: the marker `bwx12-` ends the addition. |
| 692 | `    for (int k = 0; k < K_COUNT; k++) {` | The loop takes every kernel in the order of `kernels[]`. |
| 693 | `        for (size_t i = 0; i < sizeof words / sizeof words[0]; i++)` | Loop over the three sizes of `words`. |
| 694 | `            test_size(&kernels[k], words[i]);` | Per kernel: `test_size` with each of the three sizes. |
| 695 | `        for (size_t i = 0; i < 2; i++)` | Loop over the two block offsets. |
| 696 | `            test_block(&kernels[k], offs[i]);` | Per kernel: `test_block` at each of the two offsets. |
| 697 | `        if (is_read(&kernels[k]))` | For a read kernel in addition ... |
| 698 | `            test_touch(&kernels[k]);` | ... `test_touch`. |
| 699 | `    }` | Ends the loop of line 692. |
| 700 | `    test_trial();` | Then the checks of the trial mode follow. The first is `test_trial`. |
| 701 | `/* bwx10+ */` | Comment: the marker `bwx10+`. The next two lines were added for bwx10. |
| 702 | `    test_trial_hot();` | `test_trial_hot`: the window checks with `--hot-copy`. |
| 703 | `    test_hot_touch();` | `test_hot_touch`: `timed_sequence_hot` must not touch the window record. |
| 704 | `/* bwx10- */` | Comment: the marker `bwx10-` ends the addition. |
| 705 | `/* bwx11+ */` | Comment: the marker `bwx11+`. The next line was added for bwx11. |
| 706 | `    test_evict();` | `test_evict`: the evict step. |
| 707 | `/* bwx11- */` | Comment: the marker `bwx11-` ends the addition. |
| 708 | `    test_emit();` | `test_emit`: the output rows of a trial. |
| 709 | `    printf("# failures=%d\n", failures);` | The last line of the output is `# failures=N`. For the bwx12 binary of the whole-chip test, the self-test printed 457 `pass` lines, no `FAIL` line and `# failures=0` [Ref3]. |
| 710 | `    return failures ? 1 : 0;` | Return value: 1 if a check failed, else 0. `build12.sh` stops with status 4 when the value is not 0 [Ref2]. |
| 711 | `}` | Ends the function `selftest`. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: line 2900 includes this file. Lines 2908 to 2911 and 2919 to 2920: `main` sets `page_bytes`, limits the CPUs and calls `selftest`. Lines 461 to 475: one macro defines `oldread` and `oldread2` from the same source text. Lines 1454 to 1509: `kernels[]` and `call`. Lines 1632 to 1735: `worker` (interval mode), which calls `call`. Lines 1641 to 1646: it pins its thread when `--cpus` is given, allocates the buffer and writes the whole buffer with `k_write` (first touch). Line 1669: its warm-up call on the whole range of the sequence entry. Lines 2989 to 2990: a sequence entry without a size gets the size of `--bytes`. Lines 1693 to 1695: with `--stop common` its timed loop calls the kernel on chunks of 2 MiB. Lines 1995 to 2093: `timed_sequence` and `timed_sequence_hot`. Lines 2165 to 2256: `first_multiplexed`, `run_trial`, `trial_windows`, `window_bins`, `set_windows`. Lines 2317 to 2406: `emit_trial`. Lines 2428 to 2446: `evict_step`. Lines 2816 and 2828: `--hot-copy` and `--evict-mb` are options of the trial mode. Lines 3077 to 3103: the interval mode prints its I, T and C rows in `main`.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: lines 51 to 55: the script runs `bwx12 --selftest`, writes the output to selftest-bwx12.txt, and exits with status 4 when the self-test fails. Line 34: the script runs under `taskset -c 0-119`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/selftest-bwx12.txt`: the self-test output of the CRB build of 2026-11-15. 852 lines. Line 1: `page_bytes=4096 kernels=55 (aarch64)`. 457 lines end with `pass`, no line holds `FAIL`, 393 lines start with `call,`. Line 852: `# failures=0`. Lines 20 to 29: the `call` lines and the result lines of the kernel `write`. Counted with `grep -c` in this task.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: line 6: `## selftest bwx12 exit=0 # failures=0`. Lines 17 to 20: the sha256 values of bwx12.c, bwx12_selftest.c, build12.sh and the binary bwx12 (cd58e564...3546a). The sha256 of this source file, computed in this task, equals the value of line 18.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: lines 12, 13 and 23: the run stops unless the sha256 of the binary bwx12 is cd58e564...3546a, the value of build.txt. go2.sh in the same folder has the same test in lines 9, 10 and 19. Line 31 of go.sh and line 30 of go2.sh call rx.sh.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: line 11 reads one line of the spec file per process: a tag, the character `|`, and the arguments. Line 17 starts bwx12 with the arguments of the spec line and writes its standard output to the file `<tag>.csv`. The spec files like.spec, cfwd.spec and crev.spec in the folder /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17 hold `--seq`, `--cpus 0-63,64-119`, `--bytes 256M` and `--stop common`. They hold neither `--selftest` nor `--trial`, `--hot-copy` or `--evict-mb`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: the objdump text of every kernel of the binary. The file check_listing12.out in the same folder is the saved output of check_listing12.py for this listing.
