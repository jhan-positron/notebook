# `Makefile` explained, line by line

- Source file: `bench/Makefile` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Makefile, 31 lines, 873 bytes).
- sha256 of the source when this page was built: `646394d6d6ee6cfac7d562eeda3d8dea43aba0c962057c260011fe1d217f4566`.

## Short version: purpose

`Makefile` tells the build tool `make` how to compile the three benchmark programs of the folder `bench` with `gcc`. On an AArch64 machine such as CRB it builds `latency`, `bandwidth` and `homelat`. On every other machine it builds `latency` only.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **AArch64**: the 64-bit Arm instruction set. The command `uname -m` prints `aarch64` on such a machine.
- **`make`**: the build tool that reads this file. It runs the recipe of a rule when the target does not exist or is older than one of the files that the rule names.
- **Target**: the name before the colon of a rule. It is a file to build, or a name such as `all` or `clean`.
- **Recipe**: the command lines of a rule. Each of them starts with a tab.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **`latency`**: the program built from `latency.c`. It measures the load latency per cache level with one thread.
- **`bandwidth`**: the program built from `bandwidth.c`. It measures how fast threads read, write and copy memory.
- **`homelat`**: the program built from `homelat.c`. It measures the latency of the SLC from each core to each part of the SLC.
- **NEON intrinsics**: C functions that map to Arm vector instructions.

## Main flow

1. Choose the compiler: `gcc`, unless the caller has set the variable `CC` (lines 1 to 5).
2. Set the compiler options for all programs (lines 6 to 9).
3. Choose what the target `all` builds: three programs on AArch64, one program on every other machine (lines 11 to 17).
4. Give one rule per program. Each rule compiles one C file into one program (lines 19 to 26).
5. Give the target `clean`, which removes the three programs (lines 28 to 29).
6. Declare that `all` and `clean` are not files (line 31).

## Behavior a reader must know

- Each of the three program rules names the `Makefile` as an input. So a change of the `Makefile` builds every program again.
- `-march=native` in line 9 fits the code to the processor of the build machine. The file `README.md` of this folder gives the build command for CRB: `make` in the folder `bench`.
- `make clean` removes all three program files, also on a machine where only `latency` was built. A file that does not exist causes no error.
- The file builds no test and starts no benchmark.

## Source and explanation, line by line

- Text shown: the file `bench/Makefile` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (31 lines, 873 bytes, sha256 `646394d6d6ee6cfac7d562eeda3d8dea43aba0c962057c260011fe1d217f4566`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `# make's built-in default CC is "cc"; use gcc unless CC comes from the` | Comment: `make` has a built-in value for the variable `CC`, the name of the C compiler. That value is `cc`. Lines 3 to 5 replace it with `gcc`, unless the caller has set `CC` in the environment or on the command line. The sentence ends in line 2. |
| 2 | `# environment or the command line.` | Comment: the end of the sentence of line 1: the two places where a caller can set `CC`. |
| 3 | `ifeq ($(origin CC),default)` | `$(origin CC)` gives a word that tells where the value of `CC` comes from. The word is `default` when nobody has set `CC`, so `make` would use its built-in value. `ifeq` compares the two texts in the parentheses. Line 4 is read only when they are equal. |
| 4 | `CC = gcc` | Sets the compiler to `gcc`. A `CC` from the environment or from the command line is kept, for example `make CC=clang`. |
| 5 | `endif` | Ends the condition of line 3. |
| 6 | `# -mcpu is avoided on purpose: gcc 14 on CRB resolves -mcpu=native to nothing.` | Comment: the options of line 9 hold no `-mcpu`, and this is intended. By the comment, `gcc` version 14 on CRB (the Arm reference server under test) resolves `-mcpu=native` to nothing. Line 9 uses `-march=native` in its place. |
| 7 | `# -fno-tree-loop-distribute-patterns keeps gcc from turning the write/copy` | Comment: the option `-fno-tree-loop-distribute-patterns` forbids `gcc` to replace a loop that writes or copies memory with a call of a library function. The sentence ends in line 8. |
| 8 | `# loops into memset/memcpy calls.` | Comment: the end of the sentence of line 7: the library functions are `memset` (fill memory with one value) and `memcpy` (copy memory). The comment names the write loop and the copy loop of the benchmark. |
| 9 | `CFLAGS = -O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11` | `CFLAGS`: the compiler options of every build rule of this file. `-O3`: the highest of the numbered optimization levels of `gcc`. `-march=native`: the compiler produces code for the instruction set of the machine on which it runs. `-fno-tree-loop-distribute-patterns`: see lines 7 to 8. `-pthread`: builds with support for POSIX threads. `-Wall -Wextra`: the compiler prints two large groups of warnings. `-std=gnu11`: the language is C of the 2011 standard with the GNU extensions. |
| 11 | `# homelat uses AArch64 cache-maintenance instructions and bandwidth uses NEON` | Comment: `homelat` uses cache maintenance instructions of AArch64, the 64-bit Arm instruction set. Such an instruction acts on one cache line, for example it removes the line from the caches. `bandwidth` uses NEON intrinsics (C functions that map to Arm vector instructions). The sentence ends in line 12. |
| 12 | `# intrinsics, so both are built only there.` | Comment: the end of the sentence of line 11: so both programs are built only on an AArch64 machine. |
| 13 | `ifeq ($(shell uname -m),aarch64)` | `$(shell uname -m)` runs the command `uname -m` and takes its output, the name of the processor type of this machine. `ifeq` tests whether the name is `aarch64`. The file `README.md` of this folder calls CRB an `aarch64` server. Line 14 is read in that case, and line 16 in every other case. |
| 14 | `all: latency bandwidth homelat` | On AArch64: the target `all` needs the three programs `latency`, `bandwidth` and `homelat`. `all` is the first target of the file. So the command `make` without an argument builds it. |
| 15 | `else` | Starts the other case of the condition of line 13: a machine that is not AArch64. |
| 16 | `all: latency` | On every other machine: the target `all` needs `latency` only. |
| 17 | `endif` | Ends the condition of line 13. |
| 19 | `latency: latency.c Makefile` | Rule for the program `latency`. It is built again when `latency.c` or this `Makefile` is newer than the program, or when the program does not exist. |
| 20 | `	$(CC) $(CFLAGS) -o $@ $<` | The recipe of the rule. A recipe line starts with a tab. `$@` stands for the target of the rule, here `latency`. `$<` stands for the first file after the colon of line 19, here `latency.c`. So the line runs the compiler of `CC` (`gcc` by line 4) with the options of line 9. The compiler reads `latency.c` and writes the program `latency` (`-o` names the output file). The compile step and the link step are one command. |
| 22 | `bandwidth: bandwidth.c Makefile` | Rule for the program `bandwidth`. It is built again when `bandwidth.c` or this `Makefile` is newer than the program. |
| 23 | `	$(CC) $(CFLAGS) -o $@ $<` | The recipe: the same command as in line 20. Here `$@` is `bandwidth` and `$<` is `bandwidth.c`. |
| 25 | `homelat: homelat.c Makefile` | Rule for the program `homelat`. It is built again when `homelat.c` or this `Makefile` is newer than the program. |
| 26 | `	$(CC) $(CFLAGS) -o $@ $<` | The recipe: the same command as in line 20. Here `$@` is `homelat` and `$<` is `homelat.c`. |
| 28 | `clean:` | Rule for the target `clean`. It needs no file. The command `make clean` runs it. |
| 29 | `	rm -f latency bandwidth homelat` | The recipe: removes the three programs. `-f`: `rm` prints no error and does not fail when a file does not exist. |
| 31 | `.PHONY: all clean` | `.PHONY` names the targets that are not files: `all` and `clean`. `make` then runs their rules also when a file with such a name exists. |
