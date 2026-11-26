# `bwx12_selftest.c` explained

- Source file: `bwx12_selftest.c` in this folder (C source, 711 lines, 29959 bytes).
- sha256 of the source when this page was built: `d27ca7aa8e706ec1e79c10258539e8c48fb8249159c38a15069af755fed8b72e`.
- Role in the whole-chip test: Self-test of the runner bwx12. Runs at build time, never in a timed run.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File comment: checks added for bwx12 (round 5)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  /* bwx12+ */
  2  /*
  3   * bwx12_selftest.c - bwx11_selftest.c plus the checks of round 5. Every
  4   * addition stands between a line "bwx12+" and a line "bwx12-". Without these
  5   * blocks this file is bwx11_selftest.c byte for byte.
  6   *
  7   * The loop over kernels[] gives each of the 26 new kernels the checks of its
  8   * kind. The 20 read kernels: buffer unchanged, no guard page touched, a fault
  9   * in each page of a 3-page range. The 4 write kernels: every word equals v,
 10   * and only the 256 B of a block are written. The 2 copy kernels: destination
 11   * equals source, source unchanged, and only the 256 B of a block are copied.
 12   * The kind comes from kernels[]. test_round5: every new kernel is in
 13   * kernels[] once, with the kind that its name says, and kernels[] has 55
 14   * entries. A write kernel entered as a read kernel would pass the read
 15   * checks only by accident, so this check stands before them.
 16   *
 17   * Limits, in addition to the limits below. The test cannot see the vector
 18   * adds of read_dadd2 to read_iadd16 or any nop: they change no memory. The
 19   * objdump listing is the evidence (check_listing12.py). It does not check
 20   * that these kernels preserve d8-d15: check_listing12.py checks the stores
 21   * and loads of the listing.
 22   */
 23  /* bwx12- */</pre></td><td valign="top">A line <code>bwx12+</code> and the next line <code>bwx12-</code> enclose text that was added for bwx12. This comment lists the checks for the 26 kernels of round 5, and what these checks cannot see. Of the six kernels of the whole-chip test, only <code>read_nop256</code> belongs to round 5.</td></tr>
<tr><td colspan="2"><b>File comment: checks added for bwx11 (round 4)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 24  /* bwx11+ */
 25  /*
 26   * bwx11_selftest.c - bwx10_selftest.c plus the checks of round 4. Every
 27   * addition stands between a line "bwx11+" and a line "bwx11-". Without these
 28   * blocks this file is bwx10_selftest.c byte for byte.
 29   *
 30   * The three new kernels (read_nop64, read_nop96, read_nop128) are read
 31   * kernels, so the loop over kernels[] gives them the checks of every read
 32   * kernel.
 33   * test_evict: evict_step() with 4 MiB returns no error, its two clock reads
 34   * are in order, and the range is unmapped again (the mapping count of the
 35   * process in /proc/self/maps is the same before and after).
 36   */
 37  /* bwx11- */</pre></td><td valign="top">The same marking for the text that bwx11 added. Round 4 added three read kernels and the function <code>test_evict</code>. One of the three, <code>read_nop96</code>, runs in part L of the whole-chip test.</td></tr>
<tr><td colspan="2"><b>File comment: checks added for bwx10 (round 3)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 38  /* bwx10+ */
 39  /*
 40   * bwx10_selftest.c - bwx8_selftest.c plus the checks of round 3. Every
 41   * addition stands between a line "bwx10+" and a line "bwx10-". Without these
 42   * blocks this file is bwx8_selftest.c byte for byte.
 43   *
 44   * The five new kernels are read kernels, so the loop over kernels[] gives
 45   * them the checks of every read kernel. A read_pf kernel prefetches past the
 46   * end of its range, into the PROT_NONE page after the buffer: the test shows
 47   * that this does not fault. read_1pl reads 16 B of every 64 B line: the test
 48   * shows that it touches every page.
 49   *
 50   * test_trial_hot: the window checks of test_trial() with --hot-copy, so they
 51   * run through timed_sequence_hot().
 52   * test_hot_touch: the window record of a 200 ms window stands in a page of
 53   * its own. A second thread waits for the first kernel call of the window,
 54   * makes the page PROT_NONE for 20 ms, and makes it usable again. A fault in
 55   * that page is counted, and the handler makes the page usable. timed_sequence()
 56   * must fault (it reads the record after every pass), so the check can see a
 57   * touch. timed_sequence_hot() must not fault.
 58   */
 59  /* bwx10- */</pre></td><td valign="top">The same marking for the text that bwx10 added. Round 3 added five read kernels and the functions <code>test_trial_hot</code> and <code>test_hot_touch</code>. One of the five, <code>read_1pl</code>, runs in part L of the whole-chip test.</td></tr>
<tr><td colspan="2"><b>File comment: the base self-test (text written for bwx8)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 60  /*
 61   * bwx8_selftest.c - "bwx8 --selftest": checks what every kernel of bwx8.c
 62   * does to memory, and the accounting of the trial mode. bwx8.c includes this
 63   * file, so the test runs the machine code of the binary that is timed,
 64   * through the same call() as the benchmark. The kernel checks are the text of
 65   * bwx_selftest.c. test_trial() at the end is new.
 66   *
 67   * Every buffer ends at a page that cannot be read or written (PROT_NONE) and
 68   * starts after one. A kernel that touches a byte within one page before the
 69   * buffer or within one page after it dies with SIGSEGV. The line "call,..."
 70   * printed before each kernel call names the kernel that died.
 71   * Exit status 0 means every check passed.
 72   *</pre></td><td valign="top">This is the oldest part of the comment. It names bwx8. It holds for bwx12 in the same way: bwx12.c includes this file [Ref1].<ul><li>The self-test and a timed run are one binary. Both reach a kernel through <code>call</code> and the table <code>kernels[]</code>.</li><li>Each test buffer lies between two PROT_NONE pages. A load or a store up to one page outside the buffer is a fault. The fault ends the process, except in <code>test_touch</code> (line 235), which installs a handler.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 73   * Checks for every kernel that stores (write and copy kinds): every word is
 74   * compared, on whole buffers and on one 256 B block at a page start and at a
 75   * page end.
 76   * Checks for every read kernel: the buffer is unchanged and no guard page is
 77   * touched. The kernel must fault when one page inside its range is made
 78   * PROT_NONE, for each page of a 3-page range. oldread and oldread2 return a
 79   * sum: it must equal the sum of all words.
 80   *
 81   * Limits. For the read kernels that return nothing, the test proves that
 82   * every page of the range is touched, not every byte: the objdump listing is
 83   * the evidence for the bytes. It cannot see in which order a copy kernel
 84   * loads and stores. It does not check that a kernel preserves the
 85   * callee-saved registers d8-d15.
 86   *</pre></td><td valign="top">The checks per kind of kernel, and the limits.<ul><li><code>oldread</code> returns a sum. The test compares it with the sum of all words.</li><li>The new read kernel <code>read</code> and <code>asmread</code> return nothing. For them the test proves that every page of the range is touched. It does not prove that every byte is loaded.</li><li>For the bytes that such a kernel loads, the objdump listing is the evidence [Ref7].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 87   * Checks of the trial mode (test_trial): one trial with all phases and bins
 88   * runs through run_trial(), the function that the trial mode uses. Every
 89   * window must hold whole passes and whole groups of passes between clock
 90   * reads, must last at least its duration, and must not start before the
 91   * window before it ended. The last bin of a window must hold the bytes of
 92   * the window. The sink check must pass on a clean buffer and must fail after
 93   * one word of the buffer is changed.
 94   *
 95   * Checks of the rows (test_emit): emit_trial(), the function that prints the
 96   * rows of a trial, runs on a record with known values. The printed text is
 97   * compared: the C rows hold differences of two readings, the post P row holds
 98   * the second snapshot, the E row holds CPU time and the two context-switch
 99   * counts in their own fields, and the X rows coverage_na, count_multiplexed
100   * and sink are printed.
101   */</pre></td><td valign="top">The checks of the trial mode (<code>test_trial</code>) and of its output rows (<code>test_emit</code>). The whole-chip test does not use the trial mode [Ref6]. So these checks do not cover the function <code>worker</code> of bwx12.c, which timed the kernels in the whole-chip test.</td></tr>
<tr><td colspan="2"><b>Global variables</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">102  static int failures;
103  static sigjmp_buf fault_jmp;
104  static volatile uintptr_t fault_addr;
105</pre></td><td valign="top"><code>failures</code> counts the failed checks. <code>test_touch</code> uses <code>fault_jmp</code> and <code>fault_addr</code>: the place to continue after a fault, and the address of the fault.</td></tr>
<tr><td colspan="2"><b>Function <code>guarded</code>: a buffer between two PROT_NONE pages</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">106  /* n words whose first byte follows a PROT_NONE page and whose last byte
107   * precedes one. n * 8 must be a multiple of the page size. */
108  static uint64_t *guarded(size_t n)
109  {
110      size_t len = n * 8;
111      uint8_t *raw = mmap(NULL, len + 2 * (size_t)page_bytes, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
112      if (raw == MAP_FAILED || mprotect(raw + page_bytes, len, PROT_READ | PROT_WRITE) != 0) {
113          perror("guarded");
114          exit(2);
115      }
116      return (uint64_t *)(raw + page_bytes);
117  }
118</pre></td><td valign="top"><ul><li>Reserves <code>n</code> words (8 bytes each) plus one page before them and one page after them. The whole range is PROT_NONE at first.</li><li>Then it makes the <code>n</code> words readable and writable, and returns their address.</li><li>On an error it prints the reason and ends the process with status 2.</li><li>On CRB (page size 4096 B) every caller passes a multiple of the page size. So the last word ends directly before the PROT_NONE page.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>unguard</code>: releases a guarded buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">119  static void unguard(uint64_t *p, size_t n)
120  {
121      munmap((uint8_t *)p - page_bytes, n * 8 + 2 * (size_t)page_bytes);
122  }
123</pre></td><td valign="top">Unmaps the buffer and its two PROT_NONE pages.</td></tr>
<tr><td colspan="2"><b>Function <code>pattern</code>: test value of one word</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">124  static uint64_t pattern(size_t i, uint64_t salt)
125  {
126      return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;
127  }
128</pre></td><td valign="top">Returns <code>(i + 1)</code> times an odd 64-bit constant, then XOR <code>salt</code>. Two different word numbers <code>i</code> always give two different values. Two different <code>salt</code> values give two different patterns for the same <code>i</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>calling</code>: names the kernel before it runs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">129  static void calling(const struct kdef *kd, size_t n)
130  {
131      printf("call,%s,%zu\n", kd-&gt;name, n * 8);
132  }
133</pre></td><td valign="top">Prints <code>call,&lt;kernel&gt;,&lt;bytes&gt;</code>. The output is line-buffered (line 678), so this line is written before the kernel starts. If the kernel ends the process, this line names it.</td></tr>
<tr><td colspan="2"><b>Function <code>check</code>: one result line of a kernel check</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">134  static void check(int ok, const struct kdef *kd, const char *what, size_t n)
135  {
136      printf("%s,%s,%zu,%s\n", kd-&gt;name, what, n * 8, ok ? "pass" : "FAIL");
137      if (!ok)
138          failures++;
139  }
140</pre></td><td valign="top">Prints the kernel name, the name of the check, the bytes, and <code>pass</code> or <code>FAIL</code>. A failed check adds 1 to <code>failures</code>. The self-test continues after it.</td></tr>
<tr><td colspan="2"><b>Function <code>is_read</code>: read kernel or not</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">141  static int is_read(const struct kdef *kd)
142  {
143      return kd-&gt;type == T_READ || kd-&gt;type == T_OLDREAD;
144  }
145</pre></td><td valign="top">True for the two read kinds. <code>T_OLDREAD</code> is <code>oldread</code> and <code>oldread2</code>: they return a sum. <code>oldread2</code> is a second copy of <code>oldread</code>: the same source under another name [Ref1]. <code>T_READ</code> is every other read kernel, for example <code>read</code> and <code>asmread</code>: they return nothing.</td></tr>
<tr><td colspan="2"><b>Function <code>test_size</code>: one kernel on a whole guarded buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">146  /* The kernel on a whole guarded buffer of n words. */
147  static void test_size(const struct kdef *kd, size_t n)
148  {
149      struct thread t = { .a = guarded(n), .b = guarded(n) };
150      uint64_t *a = t.a, *b = t.b, sum = 0;
151      uint64_t v = 0xA5A5F00D12345678ULL + n;
152      volatile uint64_t sink = 0;
153      int ok = 1;</pre></td><td valign="top"><ul><li>Runs the kernel once on a whole guarded buffer. <code>selftest</code> passes three sizes: 1 page, 3 pages and 1 MiB.</li><li><b>Proves</b>, every kernel: no load and no store within one page outside its buffers. Such an access ends the process. A prefetch raises no fault, so the check does not see one.</li><li><b>Proves</b>, read kernel: the buffer is unchanged after the call.</li><li><b>Proves</b>, old read kernel: the returned sum equals the sum of all words.</li><li><b>Proves</b>, write and copy kernel: every word of the range holds the right value after the call.</li><li><b>Cannot prove</b>: that <code>read</code> or <code>asmread</code> load anything. A read kernel without a return value that loads nothing passes here. <code>test_touch</code> (line 235) checks a part of this.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">154
155      /* Every word of the source is different, so a store of the wrong vector
156       * or to the wrong offset is seen. */
157      for (size_t i = 0; i &lt; n; i++) {
158          a[i] = pattern(i, 1);
159          b[i] = 0;
160          sum += a[i];
161      }</pre></td><td valign="top">Gives every word of <code>a</code> its own value and sets <code>b</code> to 0. <code>sum</code> becomes the sum of all words of <code>a</code> in 64-bit arithmetic (an overflow wraps).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">162      calling(kd, n);
163      call(kd, &amp;t, 0, n * 8, v, &amp;sink);</pre></td><td valign="top">Prints the <code>call</code> line. Then runs the kernel on the whole buffer (offset 0, <code>n * 8</code> bytes) through <code>call</code> of bwx12.c.<ul><li><code>call</code> chooses the arguments by the kind. A read kernel gets <code>a</code>.</li><li>A write kernel gets <code>a</code> and the value <code>v</code>, which it stores in every word.</li><li>A copy kernel reads <code>a</code> and writes <code>b</code>.</li><li>The sum that an old read kernel returns goes to <code>sink</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">164      if (is_read(kd)) {
165          /* read: must leave every word as it was (and must not fault) */
166          for (size_t i = 0; i &lt; n; i++)
167              ok &amp;= a[i] == pattern(i, 1);
168          check(ok, kd, "buffer unchanged", n);
169          if (kd-&gt;type == T_OLDREAD)
170              check(sink == sum, kd, "returned sum equals the sum of all words", n);</pre></td><td valign="top"><ul><li>Read kernel: every word of <code>a</code> must still hold its pattern value.</li><li>Kind <code>T_OLDREAD</code> in addition: the sum in <code>sink</code> must equal <code>sum</code>. A kernel that skips one word, or adds one word twice, returns another sum.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">171      } else if (kd-&gt;type == T_WRITE) {
172          /* write: every word must hold v afterwards; no word may keep the old pattern */
173          for (size_t i = 0; i &lt; n; i++)
174              ok &amp;= a[i] == v;
175          check(ok, kd, "every word equals v", n);</pre></td><td valign="top">Write kernel: every word of <code>a</code> must hold <code>v</code>. A word that the kernel did not store keeps its pattern value, and no pattern value equals <code>v</code>. So a missing store fails the check.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">176      } else {
177          /* copy: destination must equal source word for word; source unchanged */
178          for (size_t i = 0; i &lt; n; i++)
179              ok &amp;= b[i] == pattern(i, 1);
180          check(ok, kd, "destination equals source", n);
181          ok = 1;
182          for (size_t i = 0; i &lt; n; i++)
183              ok &amp;= a[i] == pattern(i, 1);
184          check(ok, kd, "source unchanged", n);
185      }</pre></td><td valign="top">Copy kernel: every word of <code>b</code> must hold the pattern value of <code>a</code>. <code>b</code> held 0 before the call. Then every word of <code>a</code> must be unchanged. These are two result lines.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">186      unguard(a, n);
187      unguard(b, n);
188  }
189</pre></td><td valign="top">Releases both buffers.</td></tr>
<tr><td colspan="2"><b>Function <code>test_block</code>: 256 B at a page start or end</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">190  /* One block of 256 B (32 words) at word offset off inside one guarded page.
191   * Words of the page outside the 256 B must keep their old value. */
192  static void test_block(const struct kdef *kd, size_t off)
193  {
194      size_t n = (size_t)page_bytes / 8, m = 32;
195      struct thread t = { .a = guarded(n), .b = guarded(n) };
196      uint64_t *a = t.a, *b = t.b;
197      uint64_t v = 0x0123456789ABCDEFULL;
198      volatile uint64_t sink = 0;
199      int ok = 1;</pre></td><td valign="top"><ul><li>Runs the kernel on one block of 256 B (32 words) inside a buffer of one page. 256 B is the smallest range that a kernel may get.</li><li><code>off</code> = 0: the block starts directly after the PROT_NONE page before the buffer. The other value of <code>off</code>: the block ends directly before the PROT_NONE page after the buffer.</li><li><b>Proves</b>, every kernel: no load and no store up to one page before the block start (first case), and none up to one page after the block end (second case). Such an access ends the process.</li><li><b>Proves</b>, write and copy kernel: every word of the page outside the block keeps its value.</li><li><b>Cannot prove</b>: which bytes inside the 256 B a read kernel loads. The sum that an old read kernel returns is not compared here.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">200
201      for (size_t i = 0; i &lt; n; i++) {
202          a[i] = pattern(i, 3);
203          b[i] = pattern(i, 4);
204      }
205      calling(kd, m);
206      call(kd, &amp;t, off * 8, m * 8, v, &amp;sink);</pre></td><td valign="top">Fills the page of <code>a</code> and the page of <code>b</code> with two different patterns. Then runs the kernel on 256 B (<code>m * 8</code>) at byte offset <code>off * 8</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">207      if (is_read(kd)) {
208          for (size_t i = 0; i &lt; n; i++)
209              ok &amp;= a[i] == pattern(i, 3);
210          check(ok, kd, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);
211      } else if (kd-&gt;type == T_WRITE) {
212          for (size_t i = 0; i &lt; n; i++)
213              ok &amp;= a[i] == (i &gt;= off &amp;&amp; i &lt; off + m ? v : pattern(i, 3));
214          check(ok, kd, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);
215      } else {
216          for (size_t i = 0; i &lt; n; i++)
217              ok &amp;= b[i] == (i &gt;= off &amp;&amp; i &lt; off + m ? pattern(i, 3) : pattern(i, 4)) &amp;&amp; a[i] == pattern(i, 3);
218          check(ok, kd, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);
219      }</pre></td><td valign="top"><ul><li>Read kernel: every word of the page of <code>a</code> must be unchanged.</li><li>Write kernel: the 32 words of the block must hold <code>v</code>. Every other word of the page must keep its pattern value.</li><li>Copy kernel: in <code>b</code> the 32 words of the block must hold the values of <code>a</code>. Every other word of <code>b</code> must keep its own pattern value. <code>a</code> must be unchanged.</li><li>The name of the check says <code>page start</code> for <code>off</code> = 0 and <code>page end</code> for the other value.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">220      unguard(a, n);
221      unguard(b, n);
222  }
223</pre></td><td valign="top">Releases both buffers.</td></tr>
<tr><td colspan="2"><b>Function <code>on_fault</code>: SIGSEGV handler of <code>test_touch</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">224  static void on_fault(int sig, siginfo_t *si, void *ctx)
225  {
226      (void)sig;
227      (void)ctx;
228      fault_addr = (uintptr_t)si-&gt;si_addr;
229      siglongjmp(fault_jmp, 1);
230  }
231</pre></td><td valign="top">Stores the address of the faulting access in <code>fault_addr</code>. Then it jumps back to the <code>sigsetjmp</code> call of line 252, which now returns 1. The kernel call that faulted does not continue.</td></tr>
<tr><td colspan="2"><b>Function <code>test_touch</code>: a read kernel must touch every page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">232  /* Read kernels: a range of 3 pages, with one page inside it made PROT_NONE.
233   * The kernel must fault, and the fault address must lie in that page. This
234   * shows that the kernel touches every page of its range. */
235  static void test_touch(const struct kdef *kd)
236  {
237      size_t n = 3 * (size_t)page_bytes / 8;
238      struct thread t = { .a = guarded(n) };
239      struct sigaction sa, old;
240      volatile uint64_t sink = 0;</pre></td><td valign="top"><ul><li>For read kernels only. The buffer has 3 pages. The loop runs three times. Each time another one of the pages is PROT_NONE, and the kernel runs on the whole buffer.</li><li>The kernel must fault, and the fault address must lie in that page.</li><li><b>Proves</b>: the kernel accesses at least one byte of each of the 3 pages. A kernel that loads nothing, or that leaves out a page, fails.</li><li><b>Cannot prove</b>: that every byte or every 64 B line of a page is loaded. One load per page (4096 B on CRB) passes. The objdump listing is the evidence for the loads [Ref7].</li><li><b>Cannot prove</b>: anything about a nop, a vector add, or the use of a loaded value. They change no memory and raise no fault.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">241
242      memset(&amp;sa, 0, sizeof sa);
243      sa.sa_sigaction = on_fault;
244      sa.sa_flags = SA_SIGINFO;
245      sigaction(SIGSEGV, &amp;sa, &amp;old);</pre></td><td valign="top">Installs <code>on_fault</code> as the handler of SIGSEGV. The flag <code>SA_SIGINFO</code> makes Linux pass the fault address to the handler. <code>old</code> keeps the setting from before.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">246      for (volatile int j = 0; j &lt; 3; j++) {
247          uint8_t *pg = (uint8_t *)t.a + (size_t)j * (size_t)page_bytes;
248          volatile int faulted = 0;
249          mprotect(pg, (size_t)page_bytes, PROT_NONE);
250          fault_addr = 0;
251          calling(kd, n);
252          if (sigsetjmp(fault_jmp, 1) == 0)
253              call(kd, &amp;t, 0, n * 8, 0, &amp;sink);
254          else
255              faulted = 1;
256          mprotect(pg, (size_t)page_bytes, PROT_READ | PROT_WRITE);</pre></td><td valign="top"><ul><li><code>pg</code> is the address of page <code>j</code>. <code>mprotect</code> makes this page PROT_NONE.</li><li><code>sigsetjmp</code> returns 0 at its direct call. So the kernel is called on the whole range of 3 pages.</li><li>When the kernel faults, <code>on_fault</code> jumps back to line 252. <code>sigsetjmp</code> returns 1 there, and <code>faulted</code> becomes 1.</li><li>The argument 1 of <code>sigsetjmp</code> saves the signal mask, and the jump restores it. So SIGSEGV can be caught again for the next page.</li><li>Line 256 makes the page readable and writable again.</li><li><code>j</code> and <code>faulted</code> are <code>volatile</code>: they keep their values across the jump.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">257          check(faulted &amp;&amp; fault_addr &gt;= (uintptr_t)pg &amp;&amp; fault_addr &lt; (uintptr_t)pg + (uintptr_t)page_bytes, kd,
258                j == 0 ? "faults in page 0 of 3 when it is PROT_NONE"
259                       : j == 1 ? "faults in page 1 of 3 when it is PROT_NONE" : "faults in page 2 of 3 when it is PROT_NONE",
260                n);
261      }</pre></td><td valign="top">The check passes when the kernel faulted and the fault address lies in the PROT_NONE page. The name of the check gives the page number: 0, 1 or 2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">262      sigaction(SIGSEGV, &amp;old, NULL);
263      unguard(t.a, n);
264  }
265</pre></td><td valign="top">Restores the SIGSEGV setting from before and releases the buffer.</td></tr>
<tr><td colspan="2"><b>Function <code>trial_check</code>: one result line of another check</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">266  static void trial_check(int ok, const char *what, size_t bytes)
267  {
268      printf("trial,%s,%zu,%s\n", what, bytes, ok ? "pass" : "FAIL");
269      if (!ok)
270          failures++;
271  }
272</pre></td><td valign="top">Like <code>check</code> (line 134), for a check that belongs to no single kernel. The first field of the line is the word <code>trial</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>kernel_named</code>: index of a kernel name</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">273  static int kernel_named(const char *name)
274  {
275      int k = 0;
276      while (k &lt; K_COUNT &amp;&amp; strcmp(name, kernels[k].name))
277          k++;
278      if (k == K_COUNT) {
279          fprintf(stderr, "selftest: no kernel %s\n", name);
280          exit(2);
281      }
282      return k;
283  }
284</pre></td><td valign="top">Returns the index of the kernel with this name in <code>kernels[]</code>. If no kernel has the name, it prints a message and ends the process with status 2.</td></tr>
<tr><td colspan="2"><b>Function <code>test_trial</code>: the records of one trial (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">285  /* The trial mode on a guarded buffer of 1 MiB whose words all hold w.v. */
286  static void test_trial(void)
287  {
288      size_t bytes = 1UL &lt;&lt; 20, n = bytes / 8;
289      int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");
290      struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,
291                         .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },
292                         .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };
293      struct win win[9];
294      struct bin bin[9]; /* 3 target windows, window_bins() = 3 each */
295      struct trec r = { .win = win, .nw = trial_windows(&amp;p) };
296      struct tw w;
297      volatile uint64_t sink = 0;
298      int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1;</pre></td><td valign="top"><ul><li>Runs trials on a guarded buffer of 1 MiB through <code>run_trial</code> of bwx12.c, the function that the trial mode uses.</li><li>The plan <code>p</code>: 1 window of <code>asmread</code> (4 ms), 4 prefix windows of <code>oldread</code> (2 ms each), 1 window of <code>read</code> on 65536 B (3 ms), then 3 target windows of <code>oldread</code> (12 ms each). No counters. Bins are on.</li><li><b>Proves</b>: <code>timed_sequence</code> writes consistent window records, and the sink check can pass and can fail.</li><li><b>Cannot prove</b>: that the byte count of a window equals the bytes that the kernel read. The checks test multiples, not the number of kernel calls.</li><li><b>Cannot prove</b>: anything about the timing code of the whole-chip test. That code is the function <code>worker</code> of bwx12.c (interval mode), and no check of this file runs it [Ref1] [Ref6].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">299
300      memset(&amp;w, 0, sizeof w);
301      w.t.group_fd = -1;
302      w.v = 0x9E3779B97F4A7C15ULL * 7;
303      w.t.a = guarded(n);
304      for (size_t i = 0; i &lt; n; i++)
305          w.t.a[i] = w.v;</pre></td><td valign="top">Prepares the worker record <code>w</code> as the trial mode needs it: no counter group (<code>group_fd = -1</code>), and every word of the buffer holds the same value <code>w.v</code>. <code>run_trial</code> computes the expected sum of an old read as <code>w.v</code> times the number of words.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">306
307      trial_check(r.nw == 9 &amp;&amp; window_bins(&amp;p) == 3, "prev 1 + prefix 4 + pred 1 + target 3 windows", bytes);
308      set_windows(&amp;p, win, bin);
309      printf("call,trial,%zu\n", bytes);
310      run_trial(&amp;w, &amp;p, &amp;r, &amp;sink);</pre></td><td valign="top"><ul><li>First check: the plan gives 9 windows (1 + 4 + 1 + 3), and a target window has room for 3 bins: 1 bin for the 10 ms that end inside the 12 ms, 1 bin for the end of the window, and 1 spare bin.</li><li><code>set_windows</code> of bwx12.c fills the plan fields of the 9 window records.</li><li><code>run_trial</code> runs the 9 windows through <code>timed_sequence</code> and then sets <code>r.sink_ok</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">311      for (int i = 0; i &lt; r.nw; i++) {
312          const struct win *x = &amp;win[i];
313          whole &amp;= x-&gt;bytes &gt; 0 &amp;&amp; x-&gt;bytes % x-&gt;size == 0;
314          groups &amp;= x-&gt;bytes % CHECK_BYTES == 0; /* every size here divides 8 MiB */
315          lasts &amp;= x-&gt;t_end - x-&gt;t_start &gt;= x-&gt;dur_ns;
316          order &amp;= x-&gt;t_end &gt; x-&gt;t_start &amp;&amp; (i == 0 || x-&gt;t_start &gt;= win[i - 1].t_end);
317          if (x-&gt;phase == PH_TARGET) {
318              bins_ok &amp;= x-&gt;nbin &gt;= 1 &amp;&amp; x-&gt;nbin &lt;= x-&gt;bin_cap &amp;&amp; x-&gt;bin[x-&gt;nbin - 1].bytes == x-&gt;bytes &amp;&amp;
319                         x-&gt;bin[x-&gt;nbin - 1].t_end == x-&gt;t_end;
320              for (int b = 1; b &lt; x-&gt;nbin; b++)
321                  bins_ok &amp;= x-&gt;bin[b].t_end &gt; x-&gt;bin[b - 1].t_end &amp;&amp; x-&gt;bin[b].bytes &gt; x-&gt;bin[b - 1].bytes;
322          } else {
323              bins_ok &amp;= x-&gt;nbin == 0;
324          }
325      }</pre></td><td valign="top"><ul><li><code>whole</code>: the window counted more than 0 bytes, and a multiple of its range size.</li><li><code>groups</code>: the bytes are a multiple of 8 MiB (<code>CHECK_BYTES</code>). The window loop reads the clock after each 8 MiB.</li><li><code>lasts</code>: end time minus start time is at least the requested duration.</li><li><code>order</code>: the end is later than the start, and the start is not earlier than the end of the window before.</li><li><code>bins_ok</code>, target window: it has 1 to <code>bin_cap</code> bins, the last bin holds the bytes and the end time of the window, and time and bytes rise from bin to bin.</li><li><code>bins_ok</code>, other window: it has no bin.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">326      trial_check(whole, "every window holds whole passes and more than 0 bytes", bytes);
327      trial_check(groups, "every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);
328      trial_check(lasts, "every window lasts at least its requested duration", bytes);
329      trial_check(order, "timestamps do not go back from window to window", bytes);
330      trial_check(bins_ok, "the last bin of a target window ends the window and holds its bytes", bytes);
331      trial_check(r.sink_ok == 1, "sink holds the sum after a trial that ends in old read", bytes);</pre></td><td valign="top">Prints the five results of the loop. Then one more check: <code>r.sink_ok</code> is 1. So after a trial that ends with <code>oldread</code>, the sink holds the expected sum.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">332
333      p.tgt.k = rd;
334      set_windows(&amp;p, win, bin);
335      run_trial(&amp;w, &amp;p, &amp;r, &amp;sink);
336      trial_check(r.sink_ok == 1, "sink holds the sum of the last old read when the target is new read", bytes);
337
338      p.pfx.k = asmread;
339      set_windows(&amp;p, win, bin);
340      run_trial(&amp;w, &amp;p, &amp;r, &amp;sink);
341      trial_check(r.sink_ok == -1, "sink check is NA for a trial without old read", bytes);</pre></td><td valign="top"><ul><li>Second trial, target <code>read</code> (the new read kernel): the last old read is now a prefix window. <code>sink_ok</code> must still be 1. So the <code>read</code> windows after it left the sink unchanged.</li><li>Third trial, prefix <code>asmread</code> too: the trial holds no old read. <code>sink_ok</code> must be -1, which means not applicable.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">342
343      /* The sink check must be able to fail: one changed word changes the sum. */
344      p.tgt.k = oldread;
345      w.t.a[n - 1] ^= 1;
346      set_windows(&amp;p, win, bin);
347      run_trial(&amp;w, &amp;p, &amp;r, &amp;sink);
348      trial_check(r.sink_ok == 0, "sink check fails after one word of the buffer is changed", bytes);</pre></td><td valign="top">Fourth trial: the target is <code>oldread</code> again, and line 345 flips one bit of the last word of the buffer. The sum now differs from the expected sum by 1. So <code>sink_ok</code> must be 0. This proves that the sink check can fail, and that <code>oldread</code> reads the last word of its range.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">349
350      struct counts c[3] = { { .enabled = 0, .running = 0 }, { .enabled = 100, .running = 100 }, { .enabled = 200, .running = 150 } };
351      trial_check(first_multiplexed(c, 2) == 1, "running time below enabled time is found in target window 1", 0);
352      c[2].running = 200;
353      trial_check(first_multiplexed(c, 2) == -1, "equal running and enabled time is not called multiplexed", 0);
354      unguard(w.t.a, n);
355  }
356</pre></td><td valign="top">Checks <code>first_multiplexed</code> of bwx12.c on three counter readings that are written here. It must return 1: in target window 1 (the second one, the count starts at 0) the counters ran 50 ns of 100 ns. With equal times it must return -1. Line 354 releases the buffer.</td></tr>
<tr><td colspan="2"><b>Function <code>test_trial_hot</code>: the same checks with <code>--hot-copy</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">357  /* bwx10+ */
358  /* The window checks of test_trial() with --hot-copy: run_trial() then calls
359   * timed_sequence_hot(). */
360  static void test_trial_hot(void)
361  {
362      size_t bytes = 1UL &lt;&lt; 20, n = bytes / 8;
363      int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");
364      struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,
365                         .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },
366                         .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };
367      struct win win[9], win0[9];
368      struct bin bin[9];
369      struct trec r = { .win = win, .nw = trial_windows(&amp;p) };
370      struct tw w;
371      volatile uint64_t sink = 0;
372      int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1, kept = 1;</pre></td><td valign="top"><ul><li>The plan and the window checks of <code>test_trial</code>, with <code>plan.hot_copy = 1</code>. <code>run_trial</code> then calls <code>timed_sequence_hot</code> in place of <code>timed_sequence</code>.</li><li><code>win0</code> is a second set of the 9 window records. The trial does not use it.</li><li><b>Proves</b>: <code>timed_sequence_hot</code> writes consistent window records too, and it leaves the plan fields of each record unchanged.</li><li><b>Cannot prove</b>: anything about the whole-chip test. <code>--hot-copy</code> is an option of the trial mode only [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">373
374      memset(&amp;w, 0, sizeof w);
375      w.t.group_fd = -1;
376      w.v = 0x9E3779B97F4A7C15ULL * 11;
377      w.t.a = guarded(n);
378      for (size_t i = 0; i &lt; n; i++)
379          w.t.a[i] = w.v;
380
381      plan.hot_copy = 1;
382      set_windows(&amp;p, win, bin);
383      set_windows(&amp;p, win0, bin);
384      printf("call,trial_hot,%zu\n", bytes);
385      run_trial(&amp;w, &amp;p, &amp;r, &amp;sink);</pre></td><td valign="top">Prepares <code>w</code> and the buffer as in <code>test_trial</code>. Sets <code>plan.hot_copy</code>, fills <code>win</code> and <code>win0</code> from the same plan, and runs the trial on <code>win</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">386      for (int i = 0; i &lt; r.nw; i++) {
387          const struct win *x = &amp;win[i], *x0 = &amp;win0[i];
388          kept &amp;= x-&gt;k == x0-&gt;k &amp;&amp; x-&gt;phase == x0-&gt;phase &amp;&amp; x-&gt;widx == x0-&gt;widx &amp;&amp; x-&gt;size == x0-&gt;size &amp;&amp;
389                  x-&gt;passes == x0-&gt;passes &amp;&amp; x-&gt;dur_ns == x0-&gt;dur_ns &amp;&amp; x-&gt;bin == x0-&gt;bin &amp;&amp; x-&gt;bin_cap == x0-&gt;bin_cap;
390          whole &amp;= x-&gt;bytes &gt; 0 &amp;&amp; x-&gt;bytes % x-&gt;size == 0;
391          groups &amp;= x-&gt;bytes % CHECK_BYTES == 0;
392          lasts &amp;= x-&gt;t_end - x-&gt;t_start &gt;= x-&gt;dur_ns;
393          order &amp;= x-&gt;t_end &gt; x-&gt;t_start &amp;&amp; (i == 0 || x-&gt;t_start &gt;= win[i - 1].t_end);
394          if (x-&gt;phase == PH_TARGET) {
395              bins_ok &amp;= x-&gt;nbin &gt;= 1 &amp;&amp; x-&gt;nbin &lt;= x-&gt;bin_cap &amp;&amp; x-&gt;bin[x-&gt;nbin - 1].bytes == x-&gt;bytes &amp;&amp;
396                         x-&gt;bin[x-&gt;nbin - 1].t_end == x-&gt;t_end;
397              for (int b = 1; b &lt; x-&gt;nbin; b++)
398                  bins_ok &amp;= x-&gt;bin[b].t_end &gt; x-&gt;bin[b - 1].t_end &amp;&amp; x-&gt;bin[b].bytes &gt; x-&gt;bin[b - 1].bytes;
399          } else {
400              bins_ok &amp;= x-&gt;nbin == 0;
401          }
402      }</pre></td><td valign="top"><code>kept</code>: after the trial, the eight plan fields of each record in <code>win</code> equal those in <code>win0</code>. The other five flags are the checks of <code>test_trial</code> (lines 311 to 325).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">403      trial_check(kept, "hot copy: the plan fields of every window record are unchanged", bytes);
404      trial_check(whole, "hot copy: every window holds whole passes and more than 0 bytes", bytes);
405      trial_check(groups, "hot copy: every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);
406      trial_check(lasts, "hot copy: every window lasts at least its requested duration", bytes);
407      trial_check(order, "hot copy: timestamps do not go back from window to window", bytes);
408      trial_check(bins_ok, "hot copy: the last bin of a target window ends the window and holds its bytes", bytes);
409      trial_check(r.sink_ok == 1, "hot copy: sink holds the sum after a trial that ends in old read", bytes);
410      w.t.a[n - 1] ^= 1;
411      set_windows(&amp;p, win, bin);
412      run_trial(&amp;w, &amp;p, &amp;r, &amp;sink);
413      trial_check(r.sink_ok == 0, "hot copy: sink check fails after one word of the buffer is changed", bytes);
414      plan.hot_copy = 0;
415      unguard(w.t.a, n);
416  }
417</pre></td><td valign="top">Prints the six results and the sink check. Then it flips one bit of the last word and runs the trial again: the sink check must fail. Line 414 sets <code>plan.hot_copy</code> back to 0.</td></tr>
<tr><td colspan="2"><b>Function <code>on_touch</code>: SIGSEGV handler of <code>test_hot_touch</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">418  static uint8_t *touch_page; /* the page that holds the window record of test_hot_touch */
419  static volatile int touch_faults;
420
421  /* A fault in the page of the window record: count it and make the page
422   * usable, so the access runs again. Any other fault ends the process. */
423  static void on_touch(int sig, siginfo_t *si, void *ctx)
424  {
425      uintptr_t at = (uintptr_t)si-&gt;si_addr;
426      (void)ctx;
427      if (at &lt; (uintptr_t)touch_page || at &gt;= (uintptr_t)touch_page + (uintptr_t)page_bytes) {
428          signal(sig, SIG_DFL);
429          return;
430      }
431      touch_faults++;
432      mprotect(touch_page, (size_t)page_bytes, PROT_READ | PROT_WRITE);
433  }
434</pre></td><td valign="top"><ul><li><code>touch_page</code> is the page that holds the window record. <code>touch_faults</code> counts the faults in it.</li><li>A fault inside this page: the handler adds 1 to the count and makes the page readable and writable. After the return the access runs again and succeeds.</li><li>A fault at any other address: the handler sets SIGSEGV back to its default action. After the return the access faults again and ends the process.</li></ul></td></tr>
<tr><td colspan="2"><b><code>struct toucher</code> and function <code>toucher</code>: the second thread of <code>test_hot_touch</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">435  struct toucher {
436      struct tw *w;
437      int found;              /* the first kernel call of the window was seen in the trace */
438      int64_t t_none, t_done; /* after the page became PROT_NONE; after it became usable again */
439  };
440</pre></td><td valign="top">The data of the second thread: the worker record whose trace it reads, the flag <code>found</code>, and two clock values.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">441  static void *toucher(void *arg)
442  {
443      struct toucher *h = arg;
444      struct timespec ms20 = { 0, 20000000L };
445      int64_t limit = now_ns() + 5000000000L;
446      while (!h-&gt;found &amp;&amp; now_ns() &lt; limit) {
447          long nlog = *(volatile long *)&amp;h-&gt;w-&gt;nlog;
448          for (long i = 0; i &lt; nlog; i++)
449              if (h-&gt;w-&gt;log[i].ev == EV_KERNEL_FIRST)
450                  h-&gt;found = 1;
451      }
452      if (!h-&gt;found)
453          return NULL;
454      mprotect(touch_page, (size_t)page_bytes, PROT_NONE);
455      h-&gt;t_none = now_ns();
456      nanosleep(&amp;ms20, NULL);
457      mprotect(touch_page, (size_t)page_bytes, PROT_READ | PROT_WRITE);
458      h-&gt;t_done = now_ns();
459      return NULL;
460  }
461</pre></td><td valign="top"><ul><li>Reads the trace of the worker again and again, for at most 5 s, until it holds the event <code>EV_KERNEL_FIRST</code>. The worker writes this event at the first kernel call of a window.</li><li>Then it makes the page of the window record PROT_NONE and reads the clock (<code>t_none</code>).</li><li>It sleeps 20 ms, makes the page readable and writable again, and reads the clock (<code>t_done</code>).</li><li>If the event does not appear within 5 s, it returns and changes nothing.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>hot_touch_run</code>: one 200 ms window, record page made PROT_NONE</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">462  /* One target window of 200 ms of asmread on 1 MiB, with or without
463   * --hot-copy. faults: faults in the page of the window record. inside: the
464   * time in which the page was PROT_NONE lies between the start clock read and
465   * the end clock read of the window. */
466  static void hot_touch_run(int hot, int *faults, int *inside)
467  {
468      size_t bytes = 1UL &lt;&lt; 20, n = bytes / 8, wn = (size_t)page_bytes / 8;
469      struct trial p = { .nwin = 1, .win_ms = 200, .count = CS_CLOSED, .bins = 0,
470                         .prev = { -1, 0, 0 }, .pfx = { -1, 0, 0 }, .pred = { -1, 0, 0 },
471                         .tgt = { kernel_named("asmread"), bytes, 0 } };
472      struct win *win = (struct win *)guarded(wn);
473      struct trec r = { .win = win, .nw = 1 };
474      struct tw w;
475      struct toucher h = { .w = &amp;w };
476      struct sigaction sa, old;
477      volatile uint64_t sink = 0;
478      pthread_t tid;</pre></td><td valign="top"><ul><li>One trial with a single target window: <code>asmread</code> on 1 MiB for 200 ms. No other window, no bins, no counters.</li><li>The window record <code>win</code> lies alone in a guarded page. So the page can be made PROT_NONE without an effect on other data.</li><li><code>hot</code> selects the function under test: 0 is <code>timed_sequence</code>, 1 is <code>timed_sequence_hot</code>.</li><li>Result <code>faults</code>: the number of faults in the page of the record.</li><li>Result <code>inside</code>: 1 when the PROT_NONE time lay between the start clock read and the end clock read of the window.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">479
480      memset(&amp;w, 0, sizeof w);
481      w.t.group_fd = -1;
482      w.v = 0x9E3779B97F4A7C15ULL * 13;
483      w.t.a = guarded(n);
484      for (size_t i = 0; i &lt; n; i++)
485          w.t.a[i] = w.v;
486      w.log = calloc(TRACE_CAP, sizeof *w.log); /* the trace shows the second thread that the window runs */
487      w.cur_phase = -1;
488      if (!w.log) {
489          perror("calloc");
490          exit(2);
491      }</pre></td><td valign="top">Prepares the worker record and the buffer as in <code>test_trial</code>. It also allocates a trace (<code>w.log</code>). <code>run_trial</code> writes events to it, and the second thread reads them. <code>cur_phase = -1</code> makes the first kernel call write the event <code>EV_KERNEL_FIRST</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">492      set_windows(&amp;p, win, NULL);
493      touch_page = (uint8_t *)win;
494      touch_faults = 0;
495      memset(&amp;sa, 0, sizeof sa);
496      sa.sa_sigaction = on_touch;
497      sa.sa_flags = SA_SIGINFO;
498      sigaction(SIGSEGV, &amp;sa, &amp;old);
499      plan.hot_copy = hot;
500      printf("call,%s,%zu\n", hot ? "hot_touch_hot" : "hot_touch_plain", bytes);</pre></td><td valign="top">Fills the window record and stores its page address for the handler. Installs <code>on_touch</code> for SIGSEGV. Sets <code>plan.hot_copy</code> to <code>hot</code> and prints the <code>call</code> line.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">501      if (pthread_create(&amp;tid, NULL, toucher, &amp;h) != 0) {
502          perror("pthread_create");
503          exit(2);
504      }
505      run_trial(&amp;w, &amp;p, &amp;r, &amp;sink);
506      pthread_join(tid, NULL);
507      plan.hot_copy = 0;
508      sigaction(SIGSEGV, &amp;old, NULL);
509      *faults = touch_faults;
510      *inside = h.found &amp;&amp; h.t_none &gt; win[0].t_start &amp;&amp; h.t_done &lt; win[0].t_end;
511      free(w.log);
512      unguard(w.t.a, n);
513      unguard((uint64_t *)win, wn);
514  }
515</pre></td><td valign="top"><ul><li>Starts the second thread, runs the trial in this thread, and waits for the second thread.</li><li>Sets <code>plan.hot_copy</code> back to 0 and restores the SIGSEGV setting from before.</li><li><code>inside</code> is 1 when the event was found, <code>t_none</code> is later than the start clock read of the window, and <code>t_done</code> is earlier than its end clock read.</li><li>Releases the trace, the buffer and the page of the record.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>test_hot_touch</code>: <code>timed_sequence_hot</code> must not touch the window record</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">516  static void test_hot_touch(void)
517  {
518      int f_plain, in_plain, f_hot, in_hot;
519      hot_touch_run(0, &amp;f_plain, &amp;in_plain);
520      hot_touch_run(1, &amp;f_hot, &amp;in_hot);
521      trial_check(in_plain &amp;&amp; in_hot, "hot touch: the 20 ms with the window record in a PROT_NONE page lie inside the window", 0);
522      trial_check(f_plain &gt;= 1, "hot touch: timed_sequence touches the window record between the first and the last pass", 0);
523      trial_check(f_hot == 0, "hot touch: timed_sequence_hot does not touch the window record between the first and the last pass", 0);
524  }
525</pre></td><td valign="top"><ul><li>Runs <code>hot_touch_run</code> twice: with <code>timed_sequence</code>, then with <code>timed_sequence_hot</code>.</li><li>Check 1: in both runs the PROT_NONE time lay inside the window.</li><li>Check 2: <code>timed_sequence</code> faulted at least once. It reads the record in every pass. So this run shows that the method can see a touch.</li><li>Check 3: <code>timed_sequence_hot</code> did not fault.</li><li><b>Proves</b>: the machine code of <code>timed_sequence_hot</code> did not read or write the page of the record while it was PROT_NONE (20 ms).</li><li><b>Cannot prove</b>: the same for the rest of the 200 ms window. Also, the whole-chip test does not use <code>--hot-copy</code> [Ref6].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>map_lines</code>: number of memory mappings of the process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">526  /* bwx10- */
527  /* bwx11+ */
528  static long map_lines(void)
529  {
530      FILE *f = fopen("/proc/self/maps", "r");
531      long n = 0;
532      int c;
533      if (!f)
534          return -1;
535      while ((c = getc(f)) != EOF)
536          n += c == '\n';
537      fclose(f);
538      return n;
539  }
540</pre></td><td valign="top">Counts the lines of <code>/proc/self/maps</code>. Linux prints one line per memory mapping of the process in this file. The result is -1 if the file cannot be opened.</td></tr>
<tr><td colspan="2"><b>Function <code>test_evict</code>: the evict step runs and unmaps its memory</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">541  static void test_evict(void)
542  {
543      long before = (map_lines(), map_lines()), saved = evict_mb; /* the first call lets stdio take its memory */
544      int bad;
545      evict_mb = 4;
546      evict_t[0] = evict_t[1] = 0;
547      bad = evict_step();
548      evict_mb = saved;
549      trial_check(bad == 0, "evict: the step with 4 MiB returns no error", 0);
550      trial_check(evict_t[0] &gt; 0 &amp;&amp; evict_t[1] &gt; evict_t[0], "evict: the clock read after the step is later than the one before it", 0);
551      trial_check(before &gt; 0 &amp;&amp; map_lines() == before, "evict: the range is unmapped again", 0);
552      evict_t[0] = evict_t[1] = 0;
553  }
554</pre></td><td valign="top"><ul><li>Line 543 calls <code>map_lines</code> twice and keeps the second count. The comment gives the reason: the first call lets the C library take its memory for file reading.</li><li>Sets the size to 4 MiB and calls <code>evict_step</code> of bwx12.c. That function maps 4 MiB, writes one word per 64 B line in two passes, and unmaps the range.</li><li><b>Proves</b>: the step returns no error, its second clock read is later than its first, and the number of mappings is the same as before.</li><li><b>Cannot prove</b>: that the step removes the benchmark buffer from the caches. No check measures the content of a cache.</li><li>The whole-chip test does not use <code>--evict-mb</code> [Ref6].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>test_round5</code>: the 26 new kernels in <code>kernels[]</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">555  /* bwx11- */
556  /* bwx12+ */
557  /* Every kernel of round 5 stands in kernels[] exactly once, with the kind
558   * that its name says. */
559  static void test_round5(void)
560  {
561      static const struct {
562          const char *name;
563          enum ktype type;
564      } want[] = {
565          { "read_nop48", T_READ }, { "read_nop56", T_READ }, { "read_nop72", T_READ }, { "read_nop80", T_READ },
566          { "read_nop88", T_READ }, { "read_nop112", T_READ }, { "read_nop160", T_READ }, { "read_nop192", T_READ },
567          { "read_nop256", T_READ },
568          { "read_dadd2", T_READ }, { "read_dadd4", T_READ }, { "read_dadd8", T_READ }, { "read_dadd16", T_READ },
569          { "read_iadd16", T_READ },
570          { "read_sp24", T_READ }, { "read_sp32", T_READ }, { "read_sp40", T_READ }, { "read_sp48", T_READ },
571          { "read_sp56", T_READ },
572          { "read_1pl_nop96", T_READ },
573          { "write_nop32", T_WRITE }, { "write_nop96", T_WRITE }, { "write_nop128", T_WRITE }, { "write_nop256", T_WRITE },
574          { "copy_nop96", T_COPY }, { "copy_nop192", T_COPY },
575      };</pre></td><td valign="top"><ul><li><code>want</code> lists the 26 kernel names of round 5, each with the kind that its name says: 20 read, 4 write, 2 copy.</li><li><b>Proves</b>: each name stands exactly once in <code>kernels[]</code> with that kind, and the table has 55 entries.</li><li>Reason: the loop of <code>selftest</code> chooses the checks by the kind in <code>kernels[]</code>. A wrong kind gives a kernel the wrong checks.</li><li><b>Cannot prove</b>: that the function behind a name holds the instructions that the name says, for example 256 nop in <code>read_nop256</code>. The objdump listing is the evidence [Ref7].</li><li>The name check covers no kernel of bwx11 or older. Of the six kernels of the whole-chip test it covers <code>read_nop256</code> only.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">576      int ok = 1;
577      for (size_t i = 0; i &lt; sizeof want / sizeof want[0]; i++) {
578          int found = 0, kind = 1;
579          for (int k = 0; k &lt; K_COUNT; k++)
580              if (!strcmp(want[i].name, kernels[k].name)) {
581                  found++;
582                  kind &amp;= kernels[k].type == want[i].type;
583              }
584          if (found != 1 || !kind) {
585              printf("# round 5: kernel %s stands %d times in kernels[]%s\n", want[i].name, found, kind ? "" : ", with another kind");
586              ok = 0;
587          }
588      }
589      trial_check(ok, "round 5: each of the 26 new kernels stands once in kernels[] with its kind", 0);
590      trial_check(K_COUNT == 55, "round 5: kernels[] has 55 entries (29 of bwx11 and 26 new)", 0);
591  }
592</pre></td><td valign="top">For each wanted name the loop counts the entries of <code>kernels[]</code> with that name and compares their kind. A name that is missing, double or of another kind prints a line that starts with <code>#</code>, and the first check fails. The second check compares the number of entries with 55.</td></tr>
<tr><td colspan="2"><b>Function <code>has_line</code>: is a complete line in the text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">593  /* bwx12- */
594  static int has_line(const char *text, const char *line)
595  {
596      size_t n = strlen(line);
597      for (const char *s = text; (s = strstr(s, line)) != NULL; s += n)
598          if ((s == text || s[-1] == '\n') &amp;&amp; s[n] == '\n')
599              return 1;
600      return 0;
601  }
602</pre></td><td valign="top">True when <code>text</code> holds <code>line</code> as a whole line: the match starts at the text start or after a line end, and a line end follows it.</td></tr>
<tr><td colspan="2"><b>Function <code>emitted</code>: the text that <code>emit_trial</code> prints</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">603  /* The text that emit_trial() prints for the record r of the trial p. stdout
604   * is a memory stream during the call (glibc lets a program assign stdout). */
605  static char *emitted(struct tw *w, struct trial *p, struct trec *r)
606  {
607      char *text = NULL;
608      size_t len = 0;
609      FILE *out = stdout, *mem = open_memstream(&amp;text, &amp;len);
610      if (!mem) {
611          perror("open_memstream");
612          exit(2);
613      }
614      fflush(out);
615      plan.tr = p;
616      rec = r;
617      stdout = mem;
618      emit_trial(w, 0);
619      stdout = out;
620      fclose(mem);
621      plan.tr = NULL;
622      rec = NULL;
623      return text;
624  }
625</pre></td><td valign="top"><ul><li>Opens a stream that writes into memory (<code>open_memstream</code>).</li><li>Points the globals <code>plan.tr</code> and <code>rec</code> to the test plan and the test record. So <code>emit_trial(w, 0)</code> of bwx12.c prints trial 0 from them.</li><li>Replaces <code>stdout</code> by the memory stream for this one call, and restores it after the call.</li><li>Sets the two globals back to <code>NULL</code> and returns the printed text. The caller frees it.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>test_emit</code>: the output rows of one trial</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">626  /* emit_trial() on a record with known values. Every value differs from the
627   * value of the field beside it, so a row that prints the wrong field fails. */
628  static void test_emit(void)
629  {
630      int oldread = kernel_named("oldread");
631      struct trial p = { .nwin = 2, .count = CS_READ };
632      struct win win[3] = {
633          { .k = oldread, .phase = PH_PRED, .widx = 0, .size = 4096, .bytes = 8192, .t_start = t_base_ns + 1000, .t_end = t_base_ns + 2000 },
634          { .k = oldread, .phase = PH_TARGET, .widx = 0, .size = 4096, .bytes = 12288, .t_start = t_base_ns + 2100, .t_end = t_base_ns + 3100 },
635          { .k = oldread, .phase = PH_TARGET, .widx = 1, .size = 4096, .bytes = 16384, .t_start = t_base_ns + 3400, .t_end = t_base_ns + 4400 },
636      };
637      /* three readings; the second window ran its counters for 50 of 100 ns */
638      struct counts c[3] = { { .cpu_ns = 500, .enabled = 1000, .running = 1000, .val = { 70 } },
639                             { .cpu_ns = 800, .enabled = 1100, .running = 1100, .val = { 75 } },
640                             { .cpu_ns = 1400, .enabled = 1200, .running = 1150, .val = { 82 } } };
641      struct trec r = { .win = win, .nw = 3, .cnt = c, .pg = { { 8192, 4096 }, { 8192, -1 } },
642                        .vm = { { 1, 2, 3, 4 }, { 5, 6, 7, 8 } }, .cpu = { 10000, 13000 },
643                        .nvcsw = { 5, 7 }, .nivcsw = { 10, 13 }, .state = CS_READ, .sink_ok = 0 };</pre></td><td valign="top"><ul><li>Writes a trial record by hand: 1 predecessor window, 2 target windows, three counter readings, two page snapshots, CPU times and context-switch counts.</li><li>The record holds three intended defects: no huge-page value in the second snapshot (-1), counters that ran 50 ns of 100 ns in target window 1, and <code>sink_ok = 0</code>.</li><li><b>Proves</b>: <code>emit_trial</code> prints the values of this record in the right fields of the C, P, E and X rows.</li><li><b>Cannot prove</b>: anything about the rows of the whole-chip csv files. The interval mode prints its rows with other code [Ref1].</li><li>The W rows are printed here, and no check compares them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">644      struct tw w;
645      int nev = cfg.nev;
646      char *text;
647
648      memset(&amp;w, 0, sizeof w);
649      w.t.group_fd = 0; /* emit_trial() only asks whether a group is open */
650      w.t.nopen = 1;
651      cfg.nev = 1;
652      text = emitted(&amp;w, &amp;p, &amp;r);</pre></td><td valign="top">Prepares a worker record for <code>emit_trial</code>. <code>group_fd = 0</code> makes <code>emit_trial</code> treat the counter group as open. <code>cfg.nev = 1</code> makes <code>emit_trial</code> print one event column, and <code>nev</code> keeps the old value. Line 652 gets the printed text.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">653      trial_check(has_line(text, "C,0,0,100,100,300,5") &amp;&amp; has_line(text, "C,0,1,100,50,600,7"),
654                  "C rows hold the differences of two readings", 0);
655      trial_check(has_line(text, "P,0,pre,8192,4096,1,2,3,4") &amp;&amp; has_line(text, "P,0,post,8192,NA,5,6,7,8"),
656                  "P rows: pre holds the first snapshot and post the second", 0);
657      trial_check(has_line(text, "E,0,3400,3000,2,3,100,300,0,read"),
658                  "E row holds wall time and CPU time and both switch counts and both gaps each in its own field", 0);
659      trial_check(strstr(text, "\nX,0,coverage_na,") != NULL, "X row coverage_na when a snapshot has no huge-page value", 0);
660      trial_check(strstr(text, "\nX,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100\n") != NULL,
661                  "X row count_multiplexed names the window that ran its counters for less time", 0);
662      trial_check(strstr(text, "\nX,0,sink,") != NULL, "X row sink when the sink check failed", 0);
663      free(text);</pre></td><td valign="top"><ul><li>C rows <code>C,0,0,100,100,300,5</code> and <code>C,0,1,100,50,600,7</code>: after the trial number and the window number come four differences of two readings: enabled time, running time, thread CPU time (all in ns) and the event count.</li><li>P rows: <code>pre</code> holds the first snapshot. <code>post</code> holds the second, with <code>NA</code> for the missing huge-page value.</li><li>E row <code>E,0,3400,3000,2,3,100,300,0,read</code>: wall time 3400 ns, CPU time 3000 ns, 2 voluntary and 3 involuntary context switches, a gap of 100 ns before the first target window, a largest gap of 300 ns, sink check 0, counter state <code>read</code>.</li><li>X rows: one row for each of the three defects (<code>coverage_na</code>, <code>count_multiplexed</code>, <code>sink</code>).</li><li>Line 663 frees the text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">664
665      /* The same record without the three defects must print no X row. */
666      r.pg[1].kb_huge = 4096;
667      c[2].running = 1200;
668      r.sink_ok = 1;
669      text = emitted(&amp;w, &amp;p, &amp;r);
670      trial_check(strstr(text, "\nX,") == NULL &amp;&amp; has_line(text, "E,0,3400,3000,2,3,100,300,1,read"),
671                  "no X row for a record without a defect", 0);
672      free(text);
673      cfg.nev = nev;
674  }
675</pre></td><td valign="top">Removes the three defects from the record and prints it again. The text must now hold no X row, and the E row must show sink check 1. The last lines free the text and restore <code>cfg.nev</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>selftest</code>: entry point of <code>bwx12 --selftest</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">676  static int selftest(void)
677  {
678      setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */
679      printf("# selftest: page_bytes=%ld kernels=%d (%s); columns: kernel,check,bytes,result\n", page_bytes, K_COUNT,
680             STANDIN ? "STAND-IN kernels, not AArch64" : "aarch64");
681      if (page_bytes % 256 != 0) {
682          fprintf(stderr, "page size is not a multiple of 256\n");
683          return 2;
684      }
685      /* whole buffers of 1 page, 3 pages and 1 MiB */
686      size_t words[] = { (size_t)page_bytes / 8, 3 * (size_t)page_bytes / 8, (1UL &lt;&lt; 20) / 8 };
687      /* one block: at the start of a page (guard before it) and at the end (guard after it) */
688      size_t offs[] = { 0, (size_t)page_bytes / 8 - 32 };</pre></td><td valign="top"><ul><li><code>main</code> of bwx12.c calls it for the argument <code>--selftest</code> and returns its value as the exit status [Ref1].</li><li><code>setvbuf</code> makes the output line-buffered: each line is written when it is complete. So a kernel that ends the process cannot remove earlier lines.</li><li>The header line gives the page size, the number of kernels, and <code>aarch64</code> or <code>STAND-IN kernels</code>.</li><li>A page size that is not a multiple of 256 B ends the self-test with the value 2.</li><li><code>words</code>: the three buffer sizes of <code>test_size</code>. <code>offs</code>: the two block offsets of <code>test_block</code>, the first and the last 256 B of a page.</li><li>The whole-chip test calls a kernel on other sizes: 256 MiB for the warm-up, and chunks of 2 MiB in the timed interval [Ref1] [Ref6].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">689  /* bwx12+ */
690      test_round5();
691  /* bwx12- */
692      for (int k = 0; k &lt; K_COUNT; k++) {
693          for (size_t i = 0; i &lt; sizeof words / sizeof words[0]; i++)
694              test_size(&amp;kernels[k], words[i]);
695          for (size_t i = 0; i &lt; 2; i++)
696              test_block(&amp;kernels[k], offs[i]);
697          if (is_read(&amp;kernels[k]))
698              test_touch(&amp;kernels[k]);
699      }</pre></td><td valign="top"><ul><li><code>test_round5</code> runs first, before the loop uses the kinds of <code>kernels[]</code>.</li><li>The loop takes all 55 kernels in the order of <code>kernels[]</code>.</li><li>Per kernel: <code>test_size</code> with the three sizes, then <code>test_block</code> at the two offsets.</li><li>Per read kernel in addition: <code>test_touch</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">700      test_trial();
701  /* bwx10+ */
702      test_trial_hot();
703      test_hot_touch();
704  /* bwx10- */
705  /* bwx11+ */
706      test_evict();
707  /* bwx11- */
708      test_emit();
709      printf("# failures=%d\n", failures);
710      return failures ? 1 : 0;
711  }</pre></td><td valign="top"><ul><li>Then five checks of the trial mode: <code>test_trial</code>, <code>test_trial_hot</code>, <code>test_hot_touch</code>, <code>test_evict</code>, <code>test_emit</code>.</li><li>The last line of the output is <code># failures=N</code>.</li><li>Return value: 1 if a check failed, else 0. build12.sh stops with status 4 when the value is not 0 [Ref2].</li><li>For the bwx12 binary of the whole-chip test, the self-test printed 457 <code>pass</code> lines, no <code>FAIL</code> line and <code># failures=0</code> [Ref3].</li></ul></td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: line 2900 includes this file. Lines 2908 to 2911 and 2919 to 2920: `main` sets `page_bytes`, limits the CPUs and calls `selftest`. Lines 461 to 475: one macro defines `oldread` and `oldread2` from the same source text. Lines 1454 to 1509: `kernels[]` and `call`. Lines 1632 to 1735: `worker` (interval mode), which calls `call`. Lines 1641 to 1646: it pins its thread when `--cpus` is given, allocates the buffer and writes the whole buffer with `k_write` (first touch). Line 1669: its warm-up call on the whole range of the sequence entry. Lines 2989 to 2990: a sequence entry without a size gets the size of `--bytes`. Lines 1693 to 1695: with `--stop common` its timed loop calls the kernel on chunks of 2 MiB. Lines 1995 to 2093: `timed_sequence` and `timed_sequence_hot`. Lines 2165 to 2256: `first_multiplexed`, `run_trial`, `trial_windows`, `window_bins`, `set_windows`. Lines 2317 to 2406: `emit_trial`. Lines 2428 to 2446: `evict_step`. Lines 2816 and 2828: `--hot-copy` and `--evict-mb` are options of the trial mode. Lines 3077 to 3103: the interval mode prints its I, T and C rows in `main`.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: lines 51 to 55: the script runs `bwx12 --selftest`, writes the output to selftest-bwx12.txt, and exits with status 4 when the self-test fails. Line 34: the script runs under `taskset -c 0-119`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/selftest-bwx12.txt`: the self-test output of the CRB build of 2026-11-15. 852 lines. Line 1: `page_bytes=4096 kernels=55 (aarch64)`. 457 lines end with `pass`, no line holds `FAIL`, 393 lines start with `call,`. Line 852: `# failures=0`. Lines 20 to 29: the `call` lines and the result lines of the kernel `write`. Counted with `grep -c` in this task.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: line 6: `## selftest bwx12 exit=0 # failures=0`. Lines 17 to 20: the sha256 values of bwx12.c, bwx12_selftest.c, build12.sh and the binary bwx12 (cd58e564...3546a). The sha256 of this source file, computed in this task, equals the value of line 18.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: lines 12, 13 and 23: the run stops unless the sha256 of the binary bwx12 is cd58e564...3546a, the value of build.txt. go2.sh in the same folder has the same test in lines 9, 10 and 19. Line 31 of go.sh and line 30 of go2.sh call rx.sh.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: line 11 reads one line of the spec file per process: a tag, the character `|`, and the arguments. Line 17 starts bwx12 with the arguments of the spec line and writes its standard output to the file `<tag>.csv`. The spec files like.spec, cfwd.spec and crev.spec in the folder /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17 hold `--seq`, `--cpus 0-63,64-119`, `--bytes 256M` and `--stop common`. They hold neither `--selftest` nor `--trial`, `--hot-copy` or `--evict-mb`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: the objdump text of every kernel of the binary. The file check_listing12.out in the same folder is the saved output of check_listing12.py for this listing.
