# `rc3.spec` explained, line by line

- Source file: `w120-2026-11-15/rc3.spec` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (text file, 6 lines, 1508 bytes).
- sha256 of the source when this page was built: `ed95acbfd33fac989dc78ed3969ca582c75b8ae932d7ffc6927ed20378f58cf5`.

## Short version: purpose

`rc3.spec` is a spec file for the counter script `rgc.sh`: 6 lines, and each line gives one group of two runner processes that run at the same time, one on mesh 0 and one on mesh 1. The groups are six combinations of the kernels `asmread`, `read_nop96` and `read_nop256`. Each process runs one timed interval of 110 s, and the script reads many sets of mesh counters in this time.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. This file has the form of the scripts `rg.sh` and `rgc.sh`: each line gives one group of processes.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Group**: the processes of one line. The script starts them one after the other and waits until all of them have ended.
- **Item**: one process of a group, in the form `tag=arguments`. The items of a line are separated by ` ;; `. The script writes the output of an item to the file `GROUP.TAG.csv`.
- **Counter window**: the time for which one `perf stat` command of the script `rgc.sh` counts. The script takes one window per event set, one after the other, and writes each to a file `GROUP.SET.perf`.
- **`read_nop96`, `read_nop256`**: the `asmread` loop with 96 or 256 `nop` instructions after the 8 loads of each 256 B. A `nop` is an instruction that does nothing.

## Main flow

1. Read one line as one group. The text before the first `|` is the group name. The rest holds the items, with ` ;; ` between them (line 1).
2. Read one item as one process. The text before the first `=` is the tag of the item: `m0` for the process on mesh 0, `m1` for the process on mesh 1. The rest holds the arguments of the runner, as the function `main` of `bwx12.c` reads them.
3. The group name holds the kernel of mesh 0 and then the kernel of mesh 1.
4. `--threads` and `--cpus` give the number of threads and the CPU of each thread.
5. `--bytes` gives the size of the buffer that each thread owns and reads. `256M` means 256 MiB.
6. `--stop common` and `--min-ms` give the timing of the one interval of a process. The main thread of the process sets one start time and one stop time for its threads. Each thread reads its buffer in chunks of 2 MiB, reads the clock after each chunk and stops at the first clock reading at or after the stop time.
7. `--start common` makes each thread begin at the first byte of its buffer.
8. `--seq` names the kernel, and `--rounds 1` runs it for one interval.

## Behavior a reader must know

- The file holds no command. The script `rgc.sh` starts the processes of a line one after the other and limits each one to the CPUs 0 to 119.
- The lines turn on no core counter (no `--count`). The counters of these runs are read by the script from outside the processes.
- The common stop holds inside one process only. Each of the two processes sets its own start time and stop time. So the two intervals of a group overlap, but they do not begin at the same moment.
- The launch record of the result folder `w120-RC3-20261115T194737Z` holds 6 launch lines with the group names and the items of this file. Its `env.txt` names the binary `bwx12` and the values `WIN 3` and `DELAY 9`. Its `sets.ok` holds 25 event sets [Ref1].
- With these values the counter windows of one group need at least 9 s plus 25 times 3 s. That is 84 s of the 110 s.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/rc3.spec` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (6 lines, 1508 bytes, sha256 `ed95acbfd33fac989dc78ed3969ca582c75b8ae932d7ffc6927ed20378f58cf5`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `asmread_asmread\|m0=--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq asmread ;; m1=--threads 56 --cpus 64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq asmread` | Group `asmread_asmread`: two processes at the same time, one per mesh, both with the kernel `asmread`, in one long interval. Item `m0`: `--threads 64 --cpus 0-63` gives 64 threads, and thread number i is pinned to entry i of the list, so they run on mesh 0. Item `m1`: `--threads 56 --cpus 64-119` gives 56 threads on mesh 1. Both items: `--bytes 256M` (256 MiB per thread), `--stop common --start common` (all threads of a process stop at one common time, and each thread begins at the first byte of its buffer), `--rounds 1` and `--seq` (one interval with the one kernel), `--min-ms 110000` (the common stop is 110000 ms, which is 110 s, after the common start). The interval is this long for the counter script: the script takes all its counter windows while the threads read. The group name holds the two kernel names in the order mesh 0, mesh 1. |
| 2 | `asmread_read_nop256\|m0=--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq asmread ;; m1=--threads 56 --cpus 64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq read_nop256` | Group `asmread_read_nop256`: item `m0` runs `asmread` on mesh 0 (64 threads), and item `m1` runs `read_nop256` on mesh 1 (56 threads). The other arguments are those of line 1. |
| 3 | `read_nop256_asmread\|m0=--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq read_nop256 ;; m1=--threads 56 --cpus 64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq asmread` | Group `read_nop256_asmread`: the reverse of line 2. Item `m0` runs `read_nop256` on mesh 0, and item `m1` runs `asmread` on mesh 1. The other arguments are those of line 1. |
| 4 | `read_nop256_read_nop256\|m0=--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq read_nop256 ;; m1=--threads 56 --cpus 64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq read_nop256` | Group `read_nop256_read_nop256`: both processes run `read_nop256`, 64 threads on mesh 0 and 56 threads on mesh 1. The other arguments are those of line 1. |
| 5 | `read_nop96_read_nop96\|m0=--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq read_nop96 ;; m1=--threads 56 --cpus 64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq read_nop96` | Group `read_nop96_read_nop96`: both processes run `read_nop96`, 64 threads on mesh 0 and 56 threads on mesh 1. The other arguments are those of line 1. |
| 6 | `read_nop96_asmread\|m0=--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq read_nop96 ;; m1=--threads 56 --cpus 64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 110000 --seq asmread` | Group `read_nop96_asmread`: item `m0` runs `read_nop96` on mesh 0, and item `m1` runs `asmread` on mesh 1. The other arguments are those of line 1. |

## References

- [Ref1] test data: the files `launches.txt`, `env.txt` and `sets.ok` in the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC3-20261115T194737Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`.
