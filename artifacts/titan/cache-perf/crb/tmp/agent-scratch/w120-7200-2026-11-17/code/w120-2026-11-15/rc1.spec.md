# `rc1.spec` explained, line by line

- Source file: `w120-2026-11-15/rc1.spec` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (text file, 9 lines, 1125 bytes).
- sha256 of the source when this page was built: `b4cbf33359916869c7ce959e0bcf7c08e4576e58c027c78fa0f4b17ae781eb66`.

## Short version: purpose

`rc1.spec` is a spec file for the counter script `rc.sh`: 9 lines of the form `tag|arguments`, one runner process per line. Each process runs one read kernel in one timed interval of 115 s, and the script reads many sets of mesh counters in this time. The lines cover four kernels at 64 plus 56 threads, the kernel `asmread` in three other layouts, and the kernel `read_nop96` in two of these three.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. The scripts `rc.sh` and `rc2.sh` read the same form.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Tag**: the name of a process. The script writes the output of the process to the file `TAG.csv` and the counts of a counter window to `TAG.SET.perf`.
- **Layout**: the number of threads on mesh 0 and on mesh 1. "64 plus 56" means 64 threads on mesh 0 and 56 threads on mesh 1.
- **Counter window**: the time for which one `perf stat` command of the script counts. The script takes one window per event set, one after the other.
- **`read_nop96`**: the `asmread` loop with 96 `nop` instructions after the 8 loads of each 256 B. A `nop` is an instruction that does nothing.
- **`read_1pl`**: a read kernel with one load per 64 B line: four loads of 16 B per 256 B.

## Main flow

1. Read one line as one process. The text before the first `|` is the tag. The rest of the line holds the arguments of the runner, as the function `main` of `bwx12.c` reads them (line 1).
2. The tag names the kernel and the layout: `asm`, `nop96`, `old` and `onepl` stand for `asmread`, `read_nop96`, `oldread` and `read_1pl`. The four digits give the threads on mesh 0 and on mesh 1.
3. `--threads` and `--cpus` give the number of threads and the CPU of each thread.
4. `--bytes` gives the size of the buffer that each thread owns and reads. `256M` means 256 MiB.
5. `--stop common` and `--min-ms` give the timing of the interval. The main thread sets one start time and one stop time for all threads. Each thread reads its buffer in chunks of 2 MiB, reads the clock after each chunk and stops at the first clock reading at or after the stop time.
6. `--start common` makes each thread begin at the first byte of its buffer.
7. `--seq` names the one kernel, and `--rounds 1` runs it for one interval.

## Behavior a reader must know

- The file holds no command. The script `rc.sh` starts one process per line, in the order of the file, and limits each process to the CPUs 0 to 119.
- The lines turn on no core counter (no `--count`). The counters of these runs are the mesh counters that the script reads from outside the process.
- The launch record of the result folder `w120-RC1-20261115T190208Z` holds 9 launch lines with the tags and the arguments of this file. Its `env.txt` names the binary `bwx12` and the values `WIN 4` and `DELAY 9`. Its `sets.ok` holds 22 event sets [Ref1].
- With these values the counter windows of one process need at least 9 s plus 22 times 4 s. That is 97 s of the 115 s.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/rc1.spec` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (9 lines, 1125 bytes, sha256 `b4cbf33359916869c7ce959e0bcf7c08e4576e58c027c78fa0f4b17ae781eb66`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `asm6456\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq asmread` | Process `asm6456`: 120 threads read with `asmread` in one long interval. `--threads 120 --cpus 0-63,64-119`: thread number i is pinned to entry i of the list. So 64 threads run on mesh 0 (CPUs 0 to 63) and 56 on mesh 1 (CPUs 64 to 119). `--bytes 256M`: 256 MiB per thread. `--stop common --start common`: all threads stop at one common time, and each thread begins at the first byte of its buffer. `--rounds 1` and `--seq asmread`: one interval with the one kernel. `--min-ms 115000`: the common stop is 115000 ms (115 s) after the common start. The interval is this long for the counter script: the script takes all its counter windows while the threads read. |
| 2 | `nop96_6456\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq read_nop96` | Process `nop96_6456`: as line 1, with the kernel `read_nop96`. 120 threads, 64 on mesh 0 and 56 on mesh 1, one interval of 115 s. |
| 3 | `old6456\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq oldread` | Process `old6456`: as line 1, with the kernel `oldread`. 120 threads, 64 on mesh 0 and 56 on mesh 1, one interval of 115 s. |
| 4 | `onepl6456\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq read_1pl` | Process `onepl6456`: as line 1, with the kernel `read_1pl`. 120 threads, 64 on mesh 0 and 56 on mesh 1, one interval of 115 s. |
| 5 | `asm6400\|--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq asmread` | Process `asm6400`: `asmread` on mesh 0 alone. `--threads 64 --cpus 0-63`: 64 threads on the CPUs 0 to 63, and no thread on mesh 1. The other arguments are those of line 1. |
| 6 | `asm5656\|--threads 112 --cpus 0-55,64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq asmread` | Process `asm5656`: `asmread` in the layout 56 plus 56. `--threads 112 --cpus 0-55,64-119`: 56 threads on mesh 0 (CPUs 0 to 55) and 56 on mesh 1 (CPUs 64 to 119). The other arguments are those of line 1. |
| 7 | `nop96_5656\|--threads 112 --cpus 0-55,64-119 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq read_nop96` | Process `nop96_5656`: as line 6, with the kernel `read_nop96`. 56 threads on mesh 0 and 56 on mesh 1, one interval of 115 s. |
| 8 | `asm6432\|--threads 96 --cpus 0-63,64-95 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq asmread` | Process `asm6432`: `asmread` in the layout 64 plus 32. `--threads 96 --cpus 0-63,64-95`: 64 threads on mesh 0 (CPUs 0 to 63) and 32 on mesh 1 (CPUs 64 to 95). The other arguments are those of line 1. |
| 9 | `nop96_6432\|--threads 96 --cpus 0-63,64-95 --bytes 256M --stop common --start common --rounds 1 --min-ms 115000 --seq read_nop96` | Process `nop96_6432`: as line 8, with the kernel `read_nop96`. 64 threads on mesh 0 and 32 on mesh 1, one interval of 115 s. |

## References

- [Ref1] test data: the files `launches.txt`, `env.txt` and `sets.ok` in the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC1-20261115T190208Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`.
