# `test_kernels12.py` explained

- Source file: `bwx12-2026-11-15/test_kernels12.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 296 lines, 14449 bytes).
- sha256 of the source when this page was built: `11de5c58900208af363e57c8399feea2da404c65fdc897facc649a1096eeea70`.
- Role in the whole-chip test: Local test of the bwx12 kernel source and its acceptance checker. It measures nothing.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/test_kernels12.py.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

This script tests the source of the runner bwx12 on the development machine (x86-64) and prints one PASS or FAIL line per check. It measures no rate and assembles no AArch64 code, so it does not prove what machine code ran on CRB.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Whole-chip test**: the run of 2026-11-17 on the whole chip. Of bwx12 it ran six kernels: `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`.
- **CRB build**: the run of `build12.sh` on CRB on 2026-11-15 that built the binary `bwx12` of the whole-chip test [Ref10]. The folder `crb-build-1` beside this script holds its records, without the binary [Ref6].
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Development machine**: the x86-64 machine on which this test runs. It has no compiler for AArch64.
- **AI agent, saved record**: an AI agent is an AI coding assistant (Claude Code) that worked on this project for the user. Claude Code saves each command of an agent, with its time and its output, in a record file with one JSON record per line.
- **AArch64**: the 64-bit instruction set of Arm CPUs. CRB uses it.
- **gcc -E**: with the option `-E`, gcc runs only its preprocessor. It expands macros and includes, and it compiles nothing. With `-D__aarch64__` the output holds the AArch64 branch of the source.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Write kernel, copy kernel**: loops of the same benchmark that write memory or copy it. In `bwx12.c` the function of a kernel is named `k_<name>`.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **asmwrite, asmcopy**: two of the 29 old kernels. They are hand-written loops, like asmread. Per 256 B, asmwrite has 8 "stp q" stores, and asmcopy has 8 "ldp q" loads and 8 "stp q" stores [Ref8]. "stp q" is the Arm instruction that stores two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Interval mode, trial mode**: the two modes of bwx12. Interval mode (option `--seq`): each thread runs a sequence of kernels, and the function `worker` times each kernel in one interval. The whole-chip test uses it. Trial mode (option `--trial`): the functions `timed_sequence` and `timed_sequence_hot` call and time the kernels. The whole-chip test does not use it.
- **read_smaps, tcount**: two more functions of `bwx12.c` [Ref3]. `read_smaps` reads from the Linux file `/proc/self/smaps` how many kB of a buffer lie on 2 MiB pages (transparent huge pages). `tcount` reads the event counters and the CPU time of the thread in the trial mode.
- **Round 5**: in this file: the name that the source gives to its additions of 2026-11-15. `bwx12.c` is `bwx11.c` plus these additions. It is not a round of a measurement.
- **New kernels, old kernels (in this file)**: the new kernels are the 26 kernels that round 5 added: 9 `read_nop`, 4 `read_dadd`, `read_iadd16`, 5 `read_sp`, `read_1pl_nop96`, 4 `write_nop`, 2 `copy_nop`. The old kernels are the 29 kernels that bwx11 already had. These words do not mean the new read kernel and the old read kernel.
- **Accepted build, ref-bwx11**: the build of bwx11 that the checker uses as its reference. The folder `ref-bwx11` beside the script holds its build record (`build.txt`), its listing and its offsets table.
- **NEON kernel, asm kernel**: two ways in which `bwx12.c` writes a kernel for AArch64. A NEON kernel is C code with NEON intrinsics (C functions that map to Arm vector instructions). An asm kernel is assembler text inside a gcc `__asm__` statement.
- **Stand-in**: a plain C loop that replaces a NEON or asm kernel when `bwx12.c` is compiled on a machine that is not AArch64. It touches the same bytes as the real kernel. Rates of a stand-in build mean nothing.
- **Self-test**: the run `bwx12 --selftest`. The binary runs every kernel on small buffers and prints one row per check: kernel, check, bytes, `pass` or `FAIL`.
- **build12.sh**: the build script of bwx12. It compiles `bwx12.c`, runs the self-test, and writes `build.txt`, `listing.txt` and `offsets.tsv` into its own folder.
- **taskset**: a Linux tool that starts a program limited to a list of CPUs.
- **Marker file**: by default `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. `build12.sh` and the run scripts of the whole-chip test stop when this file exists.
- **check_listing12.py, the checker**: the acceptance test of a bwx12 build. It compares a listing and an offsets table with the accepted bwx11 build and with the expected loop of each new kernel. Exit status 0: all rules passed. Exit status 1: a rule failed. Exit status 2: a file could not be used.
- **Listing, objdump**: `objdump` is a tool that prints the machine code of a binary as instruction text. The listing (`listing.txt`) holds one block per kernel: a title line `=== bwx12 <kernel> ===`, then one line per instruction with its address.
- **Offsets table**: the file `offsets.tsv`. One row per kernel: binary, kernel, function, start address, loop start address, loop start modulo 64.
- **Loop offset**: the address of the first instruction of the loop, modulo 64. The value is a number of bytes from 0 to 63. The plan is 20 B for a read kernel, 40 B for a write kernel and 52 B for a copy kernel of round 5.
- **PLACE, pad**: `PLACE(name)` is a macro of `bwx12.c` that stands directly before a kernel. It fills the code up to a 64 B boundary and then adds `pad` zero bytes. So the function starts at `pad` modulo 64.
- **Asm template, clobber list**: parts of a gcc `__asm__` statement. The template is the assembler text, written as string literals. The clobber list names the registers that the text changes.
- **.rept, .endr, 1:, 1b**: assembler syntax in the asm text. The lines between `.rept N` and `.endr` are repeated N times. `1:` is a label. `b.lo 1b` branches back to the label `1:` that stands before it.
- **Frame**: here: the instructions that the compiler adds before and after the asm text of a kernel. They store the registers d8 to d15 to the stack before the loop and load them back after it.
- **End-pointer instruction**: the instruction before the loop that computes the address at which the loop stops. For a read or write kernel it is `add x1, x0, x1, lsl #3`: end = start + 8 B per 64-bit word. The compiler makes it from a C statement of the kernel function. It is not part of the asm text.
- **v, q and d registers**: AArch64 has 32 vector registers, v0 to v31. q8 names the 16 bytes of v8, and d8 names its low 8 bytes. A function must return d8 to d15 unchanged to its caller.
- **ldp, stp, nop, movi, dup, b.lo**: Arm instructions. `ldp` loads two registers and `stp` stores two registers. `nop` does nothing. `movi` sets a vector register to a constant. `dup` copies a general register into each element of a vector register. `b.lo` branches when the compare found "lower". `objdump` prints it as `b.cc`.
- **sha256**: a checksum of 64 hexadecimal digits. Two files with the same sha256 are taken as equal, byte for byte.

</details>

## Main flow

1. A person or an AI agent starts the script on the development machine, with no argument: `python3 test_kernels12.py`. With `KEEP=1` in the environment the temporary folder is kept (lines 28-30).
2. The script finds its own folder and the folder `ref-bwx11`, and loads `check_listing12.py` as the module `cl` (lines 40-45).
3. `main` creates a temporary folder. The builds and the listings of the test are written there (line 281).
4. Step 1, `test_source` (2 checks): `bwx12.c` and `bwx12_selftest.c` without their marked additions must have the sha256 of the accepted `bwx11.c` and `bwx11_selftest.c` (lines 74-80).
5. Step 2, `test_standin` (6 checks): `build12.sh` builds the program with and without the 26 new kernels, as x86-64 code with stand-in kernels. Both builds must succeed. `--list` must print 55 names. The self-test must report no failure, with the expected number of passed rows per new kernel. The 29 old kernels must have the same machine code and the same loop offset in both builds. The functions `call` to `timed_sequence_hot` must start at the same address modulo 64 in both builds (lines 83-117).
6. Step 3, first part of `test_aarch64_text` (3 checks): the asm text of the 26 new kernels is taken from the output of `gcc -E -D__aarch64__` and written as a listing. The listing must pass the checker. Every vector register of the text must be in the clobber list (lines 212-240).
7. Step 4, second part of `test_aarch64_text` (7 checks): 7 changed copies of that listing must fail in the checker, each on the changed kernel only (lines 242-277).
8. `main` deletes the temporary folder if `KEEP` is not set. It prints `# failed checks: N`. The exit status is 1 if a check failed and 0 if not (lines 286-296).

## Behavior a reader must know

- How it is run: a person or an AI agent starts it with a command on the development machine. It is made for that machine, not for CRB. No script of the whole-chip test (`go.sh`, `go2.sh`, `ra.sh`, `rx.sh`) calls it. It times nothing and prints no rate.
- Names: in this file "new kernels" are the 26 kernels of round 5 and "old kernels" are the 29 kernels of bwx11. Of bwx12, the whole-chip test runs `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`. Of these, only `read_nop256` is a new kernel in the sense of this file. The other five are among the 29 old kernels.
- A full run prints 18 check lines and the line `# failed checks: N`. It prints fewer check lines when a build fails (lines 99-100). It also prints fewer when `aarch64_functions` stops with an error (lines 215-217): gcc fails, a kernel is not found in the gcc output, or an asm text does not end with `b.lo 1b`. Any other error in a test function ends the script with a Python traceback and exit status 1. The line `# failed checks: N` is then not printed.
- What a pass of step 1 proves: every line of `bwx12.c` and `bwx12_selftest.c` outside the marked blocks is the accepted bwx11 text, byte for byte. This covers the source of the five old kernels that the whole-chip test runs. It also covers `worker` and `call`, the functions that time and call the kernels in every bwx12 process of the whole-chip test [Ref3].
- What a pass of step 2 proves: in an x86-64 build with stand-in kernels, the additions change neither the instruction text nor the loop offset of the 29 old kernels. They also do not change the start modulo 64 of `call`, `read_smaps`, `tcount`, `timed_sequence` and `timed_sequence_hot`. This step proves nothing about AArch64 code.
- What a pass of step 3 proves: the asm text of each new kernel, after the expansion of macros and of `.rept`, is the instruction list that the checker expects. For `read_nop256` that is 8 `ldp`, 256 `nop`, `add`, `cmp` and the loop branch. One pass of this loop reads 256 B and uses no loaded value. The pads of the source give the planned loop offsets of 20 B, 40 B and 52 B, if gcc makes the assumed frame.
- What a pass of step 4 proves: the checker rejects 7 wrong listings and reports only the changed kernel. One of them is `read_nop256` with 255 `nop`.
- What the test does not prove: it assembles no AArch64 code. The test writes these parts itself, and no compiler made them: the frame (`FRAME`, `UNFRAME`), the end-pointer instruction, the `ret`, and the registers x0, x1 and x2. The evidence for the binary that ran on CRB is the checker result on the listing of the CRB build: 29 old kernels and 26 new kernels, 0 failed rows [Ref5]. The script `go.sh` of the whole-chip test stops before the first measurement when the binary `bwx12` does not have the sha256 of that build [Ref10].
- The old read kernel and the new read kernel: steps 3 and 4 look only at the 26 new kernels. So no step of this test checks AArch64 machine code of `oldread` or `read`. The test also does not read the binaries bw_old and bw_new of part A.
- Check made for this page on 2026-11-21, not by the test. `synth` wrote the 26 blocks with the start address 0x5c80, the address of the first new kernel in the CRB build. These blocks were compared with the 26 blocks of the listing of the CRB build. Every address and every instruction is equal, and the 26 rows of the offsets table are equal. So gcc made the assumed frame on CRB [Ref6].
- The local file `bwx12.c` has the sha256 `e3d4442b83d0aabdb8bf68ec62dfeb43d489df1d7c36de82e64e5482a1089127`. The build record of the CRB build lists the same value [Ref6]. So the text that this test reads is the text that was built on CRB.
- Run on record: on 2026-11-15 at 17:11:57 UTC an AI agent (Claude Code) ran the whole test on the development machine. The run printed 18 PASS lines and `# failed checks: 0`. The saved record of the agent's commands holds the command and the output [Ref11]. In the same record, a later command of 17:12:10 UTC copies the sources to CRB and starts `build12.sh` there. So the test passed before the CRB build. The record lies outside the project folder. The project folder holds no saved output of the test.
- The run on record used the present files. The evidence is the modification times: the test file and the seven files that it reads from its own folder were last written between 17:05:03 UTC and 17:08:48 UTC on 2026-11-15.
- For this page, `test_source` and `test_aarch64_text` were called on 2026-11-21 in a temporary work folder (gcc 11.4.0, x86-64). They printed 2 and 10 PASS lines and no FAIL line. `test_standin` was not called. It runs `build12.sh` and the built binary, and the rules of this task forbid that.
- Programs that the test starts: `build12.sh` 2 times, the binary of the folder `new` with `--list` 1 time, `gcc -E` 1 time, and `check_listing12.py` 9 times. Each run of `build12.sh` starts gcc, the built binary with `--selftest` and with `--list`, `objdump`, `nm` (a tool that lists the symbols of a binary) and small text tools [Ref4]. The builds work on copies in the temporary folder.

## Call sequence in the whole-chip test

- `main` (line 280): started by a command on the development machine, not by the whole-chip run
  - `test_source` (line 74): step 1: source without additions equals the accepted bwx11 source
    - `strip12` (line 54): removes the blocks between `bwx12+` and `bwx12-`
    - `check` (line 48): prints PASS or FAIL and counts a failure
  - `test_standin` (line 83): step 2: local builds with and without the new kernels
    - `run` (line 66): starts `bash build12.sh` in folder new, then in folder old
      - `build12.sh:(whole script)`: compiles, runs the self-test, writes listing.txt and offsets.tsv
        - `bwx12_selftest.c:selftest`: checks which bytes each kernel reads or writes (55 kernels, 29 in old)
          - `bwx12.c:k_<name>`: every kernel on x86-64, the NEON and asm kernels as stand-ins
    - `run` (line 66): starts the new binary with `--list`: 55 kernel names
    - `checker` (line 70): compares the 29 old kernels of both builds, with `--skip-new`
      - `check_listing12.py:main`: part 1 only: instruction text and loop offset of 29 kernels
  - `test_aarch64_text` (line 212): steps 3 and 4: asm text of the new kernels against the checker
    - `aarch64_functions` (line 124): runs `gcc -E`, returns pad, instructions and clobbers per new kernel
      - `spell` (line 182): writes immediate numbers in hexadecimal, as objdump does
    - `result` (line 222): step 3, called in line 229: the unchanged listing
      - `synth` (line 193): writes listing text and offsets rows of the 26 new kernels
      - `checker` (line 70): runs the checker on the accepted bwx11 listing plus the 26 blocks
        - `check_listing12.py:main`: part 1 on 29 old kernels, part 2 on 26 new kernels
    - `one_nop_less` (line 242): called 3 times (lines 268-270): each call returns a change function `f`
    - `result` (line 222): step 4, called 7 times in line 275: one change function per call
      - `synth` (line 193): writes the 26 blocks, calls the change function once per kernel
        - `f` (line 243): 3 cases: one `nop` less in the loop of one kernel
        - `other_source` (line 249): 1 case: an add of `read_dadd8` takes v24
        - `moved` (line 254): 1 case: `write_nop96` starts 4 B later
        - `no_d8` (line 257): 1 case: `read_iadd16` does not store d8 and d9
        - `no_init` (line 262): 1 case: `read_dadd2` lacks the `movi` of v16
      - `checker` (line 70): the checker must end with status 1 and report only the changed kernel
        - `check_listing12.py:main`: part 1 on 29 old kernels, part 2 on 26 new kernels

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `check` | 48-51 | Prints one PASS or FAIL line for a check and counts the failed checks in `fails`. | - | - |
| `strip12` | 54-63 | Returns a source text without the blocks between the marker lines `bwx12+` and `bwx12-`. | - | - |
| `run` | 66-67 | Starts a command, waits for it, and returns exit status, standard output and error output. | - | - |
| `checker` | 70-71 | Runs `check_listing12.py` with the given arguments. | `run` | - |
| `test_source` | 74-80 | Step 1: compares the sha256 of the bwx12 sources without their additions with the accepted bwx11 values. | `strip12`, `check` | - |
| `test_standin` | 83-117 | Step 2: builds the program with and without the new kernels on x86-64 and compares the 29 old kernels. | `run`, `checker`, `check` | - |
| `aarch64_functions` | 124-190 | Runs `gcc -E -D__aarch64__` and returns pad, instruction lists and operand text of each new kernel. | `run`, `spell` | - |
| `spell` | 182-184 | Inner function: writes the number of an `add` or `movi` in hexadecimal, as objdump prints it. | - | - |
| `synth` | 193-209 | Writes the listing text and the offsets rows of the 26 new kernels, with an optional change. | `f`, `other_source`, `moved`, `no_d8`, `no_init` | - |
| `test_aarch64_text` | 212-277 | Steps 3 and 4: the listing made from the asm text must pass the checker, and 7 changed copies must fail. | `aarch64_functions`, `result`, `one_nop_less`, `check` | - |
| `result` | 222-227 | Inner function: writes the accepted bwx11 listing plus the 26 blocks to files and runs the checker on them. | `synth`, `checker` | - |
| `one_nop_less` | 242-247 | Returns a change function that removes one `nop` from the loop of one kernel. | - | - |
| `f` | 243-246 | The change function that `one_nop_less` returns. | - | - |
| `other_source` | 249-252 | Change: one add of `read_dadd8` takes v24 in place of the loaded register v2. | - | - |
| `moved` | 254-255 | Change: `write_nop96` starts 4 B later. | - | - |
| `no_d8` | 257-260 | Change: `read_iadd16` does not store d8 and d9. | - | - |
| `no_init` | 262-266 | Change: `read_dadd2` lacks the `movi` of v16, and the loop keeps its address. | - | - |
| `main` | 280-292 | Creates the temporary folder, runs the three test functions, cleans up, and returns 1 if a check failed. | `test_source`, `test_standin`, `test_aarch64_text` | - |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `bwx12-2026-11-15/test_kernels12.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (296 lines, 14449 bytes, sha256 `11de5c58900208af363e57c8399feea2da404c65fdc897facc649a1096eeea70`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/test_kernels12.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Documentation text: what the test does and how to run it (lines 1 to 31)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_kernels12.py - local tests of the kernels of round 5 (bwx12).` | Starts the documentation text of the script (lines 2 to 31). Python does not execute it. This line: the script holds local tests of the kernels of round 5. Round 5 is the set of additions that makes `bwx12.c` from `bwx11.c`. It is not a round of a measurement. "New kernels" means the 26 kernels that round 5 added. It does not mean the new read kernel of the whole-chip test. |
| 4 | `Runs on the development machine (x86-64). There is no AArch64 compiler here,` | Documentation text: the test runs on the development machine, which has x86-64 CPUs. That machine has no compiler for AArch64, the instruction set of CRB (the Arm reference server under test) ... |
| 5 | `so the asm text of the new kernels is NOT assembled by this test. What it does:` | Documentation text: ... So the test never assembles the asm text of the new kernels. Four steps follow. |
| 7 | ` 1. source: bwx12.c and bwx12_selftest.c without their blocks "bwx12+" to` | Documentation text: step 1, the source text. `bwx12.c` marks each addition: a comment line `bwx12+` stands before it and a comment line `bwx12-` after it. The files `bwx12.c` and `bwx12_selftest.c` without these blocks ... |
| 8 | `    "bwx12-" are bwx11.c and bwx11_selftest.c byte for byte (sha256 of the` | Documentation text: ... must be `bwx11.c` and `bwx11_selftest.c`, byte for byte. The test compares the sha256 (a checksum) with the value of the ... |
| 9 | `    accepted build, ref-bwx11/build.txt).` | Documentation text: ... accepted bwx11 build. The value stands in `ref-bwx11/build.txt`, the record of that build. |
| 10 | ` 2. stand-in build: build12.sh builds bwx12.c here (plain C stand-in kernels),` | Documentation text: step 2, a local build. On x86-64, `bwx12.c` compiles each asm or NEON kernel as a plain C loop, a stand-in. The build script `build12.sh` builds `bwx12.c` here, ... |
| 11 | `    runs the self-test and writes listing.txt and offsets.tsv. --list must` | Documentation text: ... runs the self-test and writes `listing.txt` and `offsets.tsv`. The option `--list` of the binary prints the kernel names. It must ... |
| 12 | `    print 55 names. The same script text builds the bwx11 source (bwx12.c` | Documentation text: ... print 55 names: the 29 kernels of bwx11 plus the 26 new kernels. The same script text also builds the bwx11 source, which is `bwx12.c` ... |
| 13 | `    without its blocks) as the reference. check_listing12.py --skip-new must` | Documentation text: ... without its blocks, as the reference. The checker `check_listing12.py` with the option `--skip-new` must ... `--skip-new` leaves out its rules for the 26 new kernels. |
| 14 | `    find the 29 old kernels with the same machine code and the same loop` | Documentation text: ... find the same machine code and the same loop ... |
| 15 | `    offset in both builds: the new kernels do not move the old ones.` | Documentation text: ... offset for the 29 old kernels in both builds. The loop offset is the address of the loop start modulo 64. So the new kernels do not move the old ones. |
| 16 | ` 3. AArch64 text: gcc -E -D__aarch64__ expands the macros of the AArch64` | Documentation text: step 3, the AArch64 text. `gcc -E` runs only the preprocessor: it expands macros and includes. With `-D__aarch64__` it prints the AArch64 ... |
| 17 | `    branch. The test takes the asm template of every new kernel from that` | Documentation text: ... branch of the source. Nothing is compiled. The test takes the asm template of every new kernel from that ... |
| 18 | `    output, expands .rept, puts the registers in (x0, x1, x2 as in the` | Documentation text: ... output, expands the directive `.rept`, and puts the registers in: `x0`, `x1` and `x2`, as in the ... |
| 19 | `    accepted listings), and writes the function as objdump would print it,` | Documentation text: ... accepted listings. It writes the function in the format of an `objdump` listing, ... |
| 20 | `    with the frame that gcc 14.2 made for the same clobber list in the` | Documentation text: ... with the frame that gcc 14.2 made for the same clobber list in the ... The frame is what the compiler adds around the asm text of some kernels: stores of d8 to d15 before the loop and loads after it. The test cannot see the real frame. It writes the frame of the accepted bwx11 listing. |
| 21 | `    accepted build (an ASSUMPTION: 4 stores of d8-d15 when v8-v15 are` | Documentation text: ... accepted build. The text calls this an assumption: 4 stores of d8 to d15 when v8 to v15 are ... |
| 22 | `    clobbered, else none). The function start is the next 64 B boundary plus` | Documentation text: ... in the clobber list, and no store in every other case. The function start is the next 64 B boundary plus ... |
| 23 | `    the pad of PLACE(name), computed from the expanded text. This listing,` | Documentation text: ... the pad of the `PLACE` macro of the kernel, computed from the expanded text. This listing, ... |
| 24 | `    after the accepted listing of bwx11, must pass check_listing12.py.` | Documentation text: ... put after the accepted bwx11 listing, must pass the checker. |
| 25 | ` 4. changed copies of that listing must fail: one nop less, an add with` | Documentation text: step 4, changed copies. The test changes one kernel of that listing and runs the checker again. The checker must fail. The text names four kinds of change: one `nop` less, an add with ... |
| 26 | `    another source register, a loop moved by 4 B, a missing store of d8.` | Documentation text: ... another source register, a loop moved by 4 B, and a missing store of d8. The code runs seven cases (lines 268 to 274). One of them is of a fifth kind: a missing `movi`. |
| 28 | `Usage: test_kernels12.py            (KEEP=1 keeps the temporary folder)` | Documentation text: the usage. The script takes no argument, for example `python3 test_kernels12.py`. With the environment variable `KEEP=1` the temporary folder is kept. It holds the two builds and the listings. |
| 29 | `Output: one line per check, "PASS name" or "FAIL name: detail". Exit status 0` | Documentation text: the output is one line `PASS name` or `FAIL name: detail` per check. Exit status 0 ... |
| 30 | `only if every check passed.` | Documentation text: ... says that every check passed. |
| 31 | `"""` | Ends the documentation text. |

### Imports, paths and the count of failed checks (lines 32 to 46)

| Line | Source | Explanation |
|---:|---|---|
| 32 | `import hashlib` | Loads the module `hashlib` of the Python standard library. It computes sha256. |
| 33 | `import os` | Loads the module `os`: file paths, the environment and the CPU list of the process. |
| 34 | `import re` | Loads the module `re` for regular expressions. |
| 35 | `import shutil` | Loads the module `shutil`: it copies files and deletes the temporary folder. |
| 36 | `import subprocess` | Loads the module `subprocess`: it starts other programs. |
| 37 | `import sys` | Loads the module `sys`: the search path of modules and the exit status. |
| 38 | `import tempfile` | Loads the module `tempfile`: it creates the temporary folder. |
| 40 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder of this script. The paths of all source and reference files start from it, so the script can be started from any folder. |
| 41 | `REF = os.path.join(HERE, "ref-bwx11")` | `REF`: the path of the folder `ref-bwx11` beside the script. The test reads from it the build record, the listing and the offsets table of the accepted bwx11 build. |
| 42 | `sys.path.insert(0, HERE)` | Puts the folder of the script first in the list of folders in which Python looks for modules. |
| 43 | `import check_listing12 as cl  # noqa: E402` | Loads `check_listing12.py` of the same folder as the module `cl`. The test takes two things from it: the names of the 26 new kernels (the keys of its table `NEW`) and its two end-pointer instructions. The test does not read the expected loops of `NEW`. Only the checker process compares with them. The comment `noqa: E402` tells a style checker not to report an import that does not stand at the top of the file. |
| 45 | `fails = 0` | `fails`: the count of failed checks. |

### Helper functions `check`, `strip12`, `run` and `checker` (lines 47 to 73)

| Line | Source | Explanation |
|---:|---|---|
| 48 | `def check(name, ok, detail=""):` | Starts the function `check`. It prints the result line of one check. `ok` is the result of the check. `detail` is an optional text for a failure. |
| 49 | `    global fails` | The function changes the global variable `fails`. |
| 50 | `    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or detail == "" else ": %s" % (detail,)))` | Prints `PASS name` or `FAIL name: detail`. The detail is printed only when the check failed and a detail was given. |
| 51 | `    fails += not ok` | Adds 1 to `fails` for a failed check. A failed check does not stop the script. |
| 54 | `def strip12(text):` | Starts the function `strip12`. It returns `text` without its bwx12 blocks. |
| 55 | `    out, skip = [], False` | `out`: the lines that are kept. `skip`: true inside a block. |
| 56 | `    for line in text.splitlines(keepends=True):` | Loop over the lines of the text. Each line keeps its line end. |
| 57 | `        if line == "/* bwx12+ */\n":` | A line that is exactly `/* bwx12+ */` starts a block. |
| 58 | `            skip = True` | From here on the lines are dropped. |
| 59 | `        elif line == "/* bwx12- */\n":` | A line that is exactly `/* bwx12- */` ends the block. |
| 60 | `            skip = False` | From here on the lines are kept again. |
| 61 | `        elif not skip:` | Every other line that stands outside a block ... |
| 62 | `            out.append(line)` | ... is kept unchanged, with its line end. So the two marker lines and all lines between them are dropped. |
| 63 | `    return "".join(out)` | Returns the kept lines as one text. |
| 66 | `def run(cmd, **kw):` | Starts the function `run`. It starts the command `cmd` and waits until it ends. Extra arguments such as `env` are passed on. |
| 67 | `    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, **kw)` | `subprocess.run` returns an object that holds the exit status (`returncode`), the standard output and the error output as text. |
| 70 | `def checker(args):` | Starts the function `checker`. It runs `check_listing12.py` of the same folder as a separate process, with the arguments `args`. |
| 71 | `    return run([sys.executable, os.path.join(HERE, "check_listing12.py")] + args)` | `sys.executable` is the Python interpreter that runs this test. The result is the object that `run` returns. |

### Function `test_source` (step 1): the bwx12 source without its additions equals bwx11 (lines 74 to 82)

| Line | Source | Explanation |
|---:|---|---|
| 74 | `def test_source(tmp):` | Starts the function `test_source`. `tmp` is the temporary folder. A pass of its two checks proves this: every line outside the marked blocks is the text of the accepted bwx11 source, byte for byte. |
| 75 | `    digests = dict(reversed(l.split()) for l in open(os.path.join(REF, "build.txt")) if re.match(r"[0-9a-f]{64}  ", l))` | `digests`: a dictionary from a file name to its sha256. The line reads `ref-bwx11/build.txt` and keeps the lines that start with 64 hexadecimal digits and two spaces. These are the sha256 lines of the accepted bwx11 build [Ref1]. `l.split()` gives the value and the file name, and `reversed` puts the name first. |
| 76 | `    for new, old in (("bwx12.c", "bwx11.c"), ("bwx12_selftest.c", "bwx11_selftest.c")):` | The loop runs two times: for `bwx12.c` with `bwx11.c`, and for `bwx12_selftest.c` with `bwx11_selftest.c`. |
| 77 | `        text = strip12(open(os.path.join(HERE, new)).read())` | Reads the bwx12 file and removes the bwx12 blocks (`strip12`). |
| 78 | `        check("source: %s without its bwx12 blocks has the sha256 of the accepted %s" % (new, old),` | The check. Its name says that the file without its bwx12 blocks has the sha256 of the accepted bwx11 file. |
| 79 | `              hashlib.sha256(text.encode()).hexdigest() == digests.get(old), digests.get(old))` | Continues the call of line 78: the check passes when the sha256 of the rest equals the recorded sha256 of `bwx11.c` or `bwx11_selftest.c`. On a failure the detail is the recorded value. |
| 80 | `        open(os.path.join(tmp, old), "w").write(text)` | Writes the rest into the temporary folder under the bwx11 name. `test_standin` uses it as the reference source. |

### Function `test_standin` (step 2): a local build with and without the new kernels (lines 83 to 119)

| Line | Source | Explanation |
|---:|---|---|
| 83 | `def test_standin(tmp):` | Starts the function `test_standin`. It builds the runner two times on this machine, as x86-64 code with stand-in kernels: once with the 26 new kernels and once without them. |
| 84 | `    new, old = os.path.join(tmp, "new"), os.path.join(tmp, "old")` | `new` and `old`: the paths of two folders in the temporary folder. |
| 85 | `    os.mkdir(new)` | Creates the folder `new` ... |
| 86 | `    os.mkdir(old)` | ... and the folder `old`. |
| 87 | `    for name in ("bwx12.c", "bwx12_selftest.c", "build12.sh"):` | Loop over the three files `bwx12.c`, `bwx12_selftest.c` and `build12.sh`. |
| 88 | `        shutil.copy(os.path.join(HERE, name), new)` | `new` gets a copy of each. |
| 89 | `    # the reference: the bwx11 source under the names of bwx12, so the same build script builds it` | Comment: `old` gets the reference. It is the bwx11 source under the file names of bwx12. So the same build script builds it. |
| 90 | `    src = open(os.path.join(tmp, "bwx11.c")).read()` | `src`: the bwx11 text that `test_source` wrote (line 80). |
| 91 | `    open(os.path.join(old, "bwx12.c"), "w").write(src.replace('#include "bwx11_selftest.c"', '#include "bwx12_selftest.c"'))` | Saves it as `bwx12.c` in `old`. Its include line for the self-test is changed to name `bwx12_selftest.c`. |
| 92 | `    shutil.copy(os.path.join(tmp, "bwx11_selftest.c"), os.path.join(old, "bwx12_selftest.c"))` | Saves the bwx11 self-test text as `bwx12_selftest.c` in `old`. |
| 93 | `    shutil.copy(os.path.join(HERE, "build12.sh"), old)` | Copies the same `build12.sh` to `old`. So the same script builds both folders, and both binaries are named `bwx12`. |
| 94 | `    cpus = ",".join(str(c) for c in sorted(os.sched_getaffinity(0)) if c <= 119)` | `cpus`: the CPUs that this process may run on (`os.sched_getaffinity(0)`), without any CPU above 119, as a list with commas. |
| 95 | `    env = dict(os.environ, BWX_CPUS=cpus, BWX_MARKER=os.path.join(tmp, "no-marker"))` | `env`: the environment of this process plus two variables. `BWX_CPUS`: `build12.sh` restarts itself under `taskset` (a tool that limits a program to a list of CPUs) on this CPU list. Its default list is the CPUs 0 to 119, the CPUs that the tests use on CRB [Ref4]. So the two builds run only on CPUs that the test process may use. `BWX_MARKER`: `build12.sh` stops when its marker file exists (by default `/tmp/positron-perf.RUNNING`). The test names a file that does not exist, so this stop cannot happen here. |
| 96 | `    for d in (new, old):` | Loop over the two folders: `new` first, then `old`. |
| 97 | `        r = run(["bash", os.path.join(d, "build12.sh")], env=env)` | Runs `bash build12.sh` in the folder, with the two variables set. Each run compiles `bwx12.c` with gcc, runs the self-test of the binary, and writes `build.txt`, `listing.txt`, `offsets.tsv` and `selftest-bwx12.txt` into its folder [Ref4]. Both binaries are x86-64 programs with stand-in kernels. |
| 98 | `        check("stand-in build: build12.sh exit 0 in %s" % os.path.basename(d), r.returncode == 0, r.stderr[-400:])` | The check fails when the script ends with a status other than 0. The detail is the last 400 characters of its error output. `build12.sh` ends with status 5 when the compile fails, and with status 4 when the self-test fails. It ends with status 6 when its check of the branch targets of the two timed functions of the trial mode fails [Ref4]. |
| 99 | `        if r.returncode:` | After a failed build ... |
| 100 | `            return` | ... the function returns. The checks of lines 101 to 117 are then not run. |
| 101 | `    names = run([os.path.join(new, "bwx12"), "--list"]).stdout.split()` | Runs the new binary with `--list`. It prints one kernel name per line and ends [Ref3]. `names` is the list of the names. |
| 102 | `    check("stand-in build: --list prints 55 names, the 26 new ones last and in the order of check_listing12.py",` | The check of the names. Its text says that `--list` prints 55 names, with the 26 new ones last and in the order of `check_listing12.py`. |
| 103 | `          len(names) == 55 and names[29:] == list(cl.NEW), names[29:])` | Continues the call of line 102: the check passes when there are 55 names and the names 30 to 55 equal the keys of `NEW` in `check_listing12.py`, in the same order. The detail is that part of the list. |
| 104 | `    st = open(os.path.join(new, "selftest-bwx12.txt")).read()` | `st`: the self-test output of the new build. A result row has the fields kernel, check, bytes, result. |
| 105 | `    rows = [l.split(",") for l in st.splitlines() if not l.startswith(("#", "call,"))]` | `rows`: the result rows, each split at the commas. The comment lines, which start with `#`, and the lines that start with `call,` are dropped. |
| 106 | `    per = {k: sum(1 for r in rows if r[0] == k and r[-1] == "pass") for k in cl.NEW}` | `per`: for each new kernel, the count of the rows with the result `pass`. |
| 107 | `    want = {k: 8 if k.startswith("read") else 5 if k.startswith("write") else 8 for k in cl.NEW}` | `want`: the expected counts: 8 for a read kernel, 5 for a write kernel, 8 for a copy kernel [Ref7]. |
| 108 | `    check("stand-in build: the self-test has 8 passed checks per new read kernel, 5 per write kernel, 8 per copy kernel",` | The check of the self-test. Its text names the three expected counts. |
| 109 | `          per == want and "FAIL" not in st and st.rstrip().endswith("# failures=0"), per)` | Continues the call of line 108: the counts must be as expected, the text must contain no `FAIL`, and it must end with `# failures=0`. Here these rows test the stand-in loops, not the asm kernels. |
| 110 | `    r = checker([os.path.join(new, "listing.txt"), "--ref-listing", os.path.join(old, "listing.txt"),` | Runs the checker on the listing of `new`. The listing of `old` is the reference (`--ref-listing`) ... |
| 111 | `                 "--ref-offsets", os.path.join(old, "offsets.tsv"), "--ref-binary", "bwx12", "--skip-new"])` | ... and the offsets table of `old` too (`--ref-offsets`). `--ref-binary bwx12`: the blocks of the reference listing have the binary name bwx12 here. `--skip-new`: the rules for the 26 new kernels are left out. |
| 112 | `    check("stand-in build: the 29 old kernels have the same machine code and loop offset with and without the new kernels",` | The check of the old kernels. Its text says that the 29 old kernels have the same machine code and loop offset with and without the new kernels. |
| 113 | `          r.returncode == 0 and "kernels=29 failed_rows=0" in r.stdout, r.stdout[-600:])` | Continues the call of line 112: the check passes when the checker ends with status 0 and prints `kernels=29 failed_rows=0`. Meaning: each of the 29 kernels of bwx11 has the same instruction text and the same loop offset in both builds [Ref2]. The checker compares `objdump` text. Of the addresses it compares only the loop start modulo 64 and the distance of a branch target from the function start. This result holds for the x86-64 build only. |
| 114 | `    place = [l for l in open(os.path.join(new, "build.txt")) if l.startswith("## placement bwx12")]` | `place`: the lines of `build.txt` of `new` that start with `## placement bwx12`. `build12.sh` writes one such line. It lists the start address modulo 64 of `call`, `read_smaps`, `tcount`, `timed_sequence` and `timed_sequence_hot`, as far as the binary has these symbols [Ref4]. |
| 115 | `    place_old = [l for l in open(os.path.join(old, "build.txt")) if l.startswith("## placement bwx12")]` | `place_old`: the same lines of `build.txt` of `old`. |
| 116 | `    check("stand-in build: call() to timed_sequence_hot() start at the same offsets modulo 64 with and without the new kernels",` | The check of the placement. Its text says that `call` to `timed_sequence_hot` start at the same offsets modulo 64 with and without the new kernels. `call` runs one kernel on a part of a buffer. In the interval mode (option `--seq`) the thread function `worker` reads the clock and calls it [Ref3]. The whole-chip test uses this mode [Ref9]. `timed_sequence` and `timed_sequence_hot` are the timed functions of the trial mode. The whole-chip test does not use that mode. |
| 117 | `          place and place == place_old, (place, place_old))` | Continues the call of line 116: the check passes when both builds have this line and the two lines are equal. |

### The assumed frame of a kernel that uses v8 to v15 (lines 120 to 123)

| Line | Source | Explanation |
|---:|---|---|
| 120 | `FRAME = ["stp d8, d9, [sp, #-64]!", "END", "stp d10, d11, [sp, #16]", "stp d12, d13, [sp, #32]", "stp d14, d15, [sp, #48]"]` | `FRAME`: the instructions that the test writes before the loop of a kernel whose clobber list names v8. `stp` stores two registers. The four `stp` store d8 to d15 to the stack. `END` is a placeholder. Line 188 puts the end-pointer instruction there. This is the frame of `asmread` and `asmcopy` in the accepted bwx11 listing [Ref8]. For the new kernels it is an assumption of the test. |
| 121 | `UNFRAME = ["ldp d10, d11, [sp, #16]", "ldp d12, d13, [sp, #32]", "ldp d14, d15, [sp, #48]", "ldp d8, d9, [sp], #64"]` | `UNFRAME`: the four `ldp` that load d8 to d15 back after the loop. `ldp` loads two registers. |

### Function `aarch64_functions`: find the asm text of each new kernel (lines 124 to 160)

| Line | Source | Explanation |
|---:|---|---|
| 124 | `def aarch64_functions(tmp):` | Starts the function `aarch64_functions`. It takes the asm text of each new kernel from the preprocessor output of `bwx12.c`. |
| 125 | `    """{kernel: (pad, [instruction text before the loop], [loop], [after the loop])} from gcc -E -D__aarch64__"""` | Documentation text of the function: it returns a dictionary from a kernel name to its pad, the instruction text before the loop, the loop, and the text after the loop. The source is the output of `gcc -E -D__aarch64__`. |
| 126 | `    stub = os.path.join(tmp, "stub")` | `stub`: the path of a folder `stub` in the temporary folder. |
| 127 | `    os.mkdir(stub)` | Creates the folder. |
| 128 | `    open(os.path.join(stub, "arm_neon.h"), "w").write("")` | Writes an empty file `arm_neon.h` into it. The AArch64 branch of `bwx12.c` includes this header, and the x86-64 gcc does not have it. |
| 129 | `    r = run(["gcc", "-E", "-P", "-D__aarch64__", "-I", stub, os.path.join(HERE, "bwx12.c")])` | Runs `gcc -E -P -D__aarch64__` on `bwx12.c`. `-E`: expand macros and includes only, do not compile, assemble or link. `-P`: leave out the marker lines that give file name and line number. `-D__aarch64__`: select the AArch64 branch of the source. `-I`: search the folder `stub` for headers. |
| 130 | `    if r.returncode:` | When gcc fails ... |
| 131 | `        raise RuntimeError(r.stderr[-400:])` | ... the function stops with an error. The message is the last 400 characters of the gcc messages. |
| 132 | `    text = r.stdout` | `text`: the output of the preprocessor. |
| 133 | `    out = {}` | `out`: the result dictionary. |
| 134 | `    for k in cl.NEW:` | Loop over the names of the 26 new kernels, the keys of `NEW` in `check_listing12.py`. |
| 135 | `        m = re.search(r'__asm__\(((?:\s*"[^"]*")+)\s*\);\s*__attribute__\(\(noinline\)\) static void k_%s\(([^)]*)\)\s*\{(.*?)\n\}' % k,` | A pattern finds two things that stand one after the other in the gcc output. The first is the `PLACE` statement of the kernel: an `__asm__(...)` that holds only string literals (group 1). The second is the function `k_` plus the kernel name, with its parameter list (group 2) and its body (group 3). The body ends before the next line that starts with a closing brace. |
| 136 | `                      text, re.S)` | Continues the call of line 135: the text to search, and the flag `re.S`. With it a `.` of the pattern also matches a line end, so the body may hold many lines. |
| 137 | `        if not m:` | When a kernel is not found ... |
| 138 | `            raise RuntimeError("no function k_%s in the expanded text" % k)` | ... the function stops with an error that names the function. |
| 139 | `        place = "".join(re.findall(r'"([^"]*)"', m.group(1))).replace("\\n", "\n")` | `place`: the strings of the `PLACE` statement, joined to one text. The pattern takes the content of each string literal, the text between two double quotes. The two characters backslash and `n` of the C text become real line ends. |
| 140 | `        pad = eval(re.search(r"\.fill (.*), 1, 0", place).group(1))  # an expression of numbers, from our own source` | `pad`: the value of the expression that follows `.fill` in that text, computed with `eval`. The pattern takes the text between `.fill` and `, 1, 0`. The value is the number of zero bytes between the 64 B boundary and the function start [Ref3]. Comment: the expression holds numbers only and comes from the project source. |
| 141 | `        body = m.group(3)` | `body`: the body of the function. |
| 142 | `        a = body.index("__asm__ volatile(")` | `a`: the place of the first `__asm__ volatile(` in the body. A gcc asm statement has the form `__asm__ volatile(template : outputs : inputs : clobbers)`. The template is a row of string literals. The captured body can be longer than the function. gcc prints a kernel that a macro defines on one line, and the pattern ends the body at a line that starts with a closing brace. So only the first asm statement is used. |
| 143 | `        # the template: the string literals up to the first ':' that stands outside a string` | Comment: the template is made of the string literals up to the first `:` that stands outside a string. |
| 144 | `        i, lit = a + len("__asm__ volatile("), []` | `i`: the place directly after `__asm__ volatile(`. `lit`: the list of the literals found. |
| 145 | `        while True:` | Loop over the characters from there. |
| 146 | `            c = body[i]` | `c`: the character at place `i`. |
| 147 | `            if c == '"':` | A double quote starts a string literal. |
| 148 | `                j = i + 1` | `j`: goes through the literal from its first character. |
| 149 | `                while body[j] != '"':` | The literal ends at the next double quote ... |
| 150 | `                    j += 2 if body[j] == "\\" else 1` | ... A backslash and the character after it are skipped together. So an escaped double quote does not end the literal. |
| 151 | `                lit.append(body[i + 1:j])` | Adds the content of the literal, without its quotes, to `lit`. |
| 152 | `                i = j + 1` | Goes on after the closing quote. |
| 153 | `            elif c == ":":` | A colon outside a string ... |
| 154 | `                break` | ... ends the template and the loop. |
| 155 | `            else:` | Every other character ... |
| 156 | `                i += 1` | ... is skipped. |
| 157 | `        operands = body[i:body.index(");", i)]  # the operand and clobber lists of this asm statement only` | `operands`: the text from that colon to the next `);`. It holds the operand lists and the clobber list. Comment: of this asm statement only. |
| 158 | `        asm = "".join(lit).replace("\\n", "\n").replace("\\t", "\t")` | `asm`: the literals joined, with the escape sequences for line end and tab turned into real characters. This is the assembler text of the kernel. |
| 159 | `        copy = "restrict d" in m.group(2)` | `copy`: true for a copy kernel. A kernel is a copy kernel when its parameter list holds the words `restrict d`. |
| 160 | `        reg = {"s": "x1", "d": "x0", "end": "x2"} if copy else {"p": "x0", "end": "x1", "v": "x2"}` | `reg`: the register for each operand of the template. Copy kernels: source `s` in `x1`, destination `d` in `x0`, `end` in `x2`. Read and write kernels: pointer `p` in `x0`, `end` in `x1`, value `v` in `x2`. The test sets these registers. They are the registers of the same operands in the accepted bwx11 listing [Ref8]. |

### Function `aarch64_functions`: from the asm text to the instruction lists (lines 161 to 192)

| Line | Source | Explanation |
|---:|---|---|
| 161 | `        lines, rep = [], None` | `lines`: the flat list of instructions. `rep`: the repeat block that is open, or `None`. |
| 162 | `        for line in asm.split("\n"):` | Loop over the lines of the assembler text. |
| 163 | `            line = re.sub(r"%\[(\w+)\]", lambda g: reg[g.group(1)], line.strip())` | Removes the white space at both ends of the line and replaces each operand of the form `%[name]` by its register. |
| 164 | `            if not line:` | An empty line ... |
| 165 | `                continue` | ... is skipped. |
| 166 | `            g = re.fullmatch(r"\.rept (\d+)", line)` | Tests whether the line is the directive `.rept N`. The group holds N. `.rept N` and `.endr` are assembler directives: the lines between them are repeated N times. |
| 167 | `            if g:` | At `.rept` ... |
| 168 | `                rep = (int(g.group(1)), [])` | ... a repeat block opens: the count N and an empty list of lines. |
| 169 | `            elif line == ".endr":` | At `.endr` ... |
| 170 | `                lines += rep[1] * rep[0]` | ... the lines of the block are added N times to `lines`. For `read_nop256` this gives 256 `nop` lines. |
| 171 | `                rep = None` | The block is closed. |
| 172 | `            elif rep is not None:` | Inside a repeat block ... |
| 173 | `                rep[1].append(line)` | ... the line goes into the block. |
| 174 | `            else:` | Outside a repeat block ... |
| 175 | `                lines.append(line)` | ... the line goes directly into `lines`. |
| 176 | `        at = lines.index("1:")` | `at`: the place of the line `1:`. It is the label at the loop start. |
| 177 | `        init, loop = lines[:at], lines[at + 1:]` | `init`: the lines before the label. They run once per call. `loop`: the lines after it. |
| 178 | `        if loop[-1] != "b.lo 1b":` | The last line must be `b.lo 1b`: branch back to label 1 while the pointer is below the end. |
| 179 | `            raise RuntimeError("%s: the template does not end with b.lo 1b" % k)` | If it is not, the function stops with an error. |
| 180 | `        loop = loop[:-1]` | Removes this line from the loop. `synth` writes the branch later, with its address. |
| 181 | `        # the spelling of objdump: immediates of add and movi in hex` | Comment: `spell` gives the spelling of `objdump`, which prints the immediate values of `add` and `movi` in hexadecimal. |
| 182 | `        def spell(t):` | Starts the inner function `spell`. It writes a number in the way that `objdump` prints it. |
| 183 | `            t = re.sub(r"^(add x\d, x\d, )#(\d+)$", lambda g: "%s#0x%x" % (g.group(1), int(g.group(2))), t)` | In an `add` of two x registers, the decimal number after `#` becomes hexadecimal. Group 1 holds the text before the `#`, group 2 the number. Example: `add x0, x0, #256` becomes `add x0, x0, #0x100`. |
| 184 | `            return re.sub(r"^(movi v\d+\.4s, )#(\d+)$", lambda g: "%s#0x%x" % (g.group(1), int(g.group(2))), t)` | The same for a `movi` of a v register with 32-bit lanes. Example: `movi v16.4s, #0` becomes `movi v16.4s, #0x0`. |
| 185 | `        init, loop = [spell(t) for t in init], [spell(t) for t in loop]` | Applies `spell` to `init` and to the loop. |
| 186 | `        end = cl.COPY_END_POINTER if copy else cl.END_POINTER` | `end`: the end-pointer instruction, as `check_listing12.py` expects it. For a read or write kernel it is `add x1, x0, x1, lsl #3`: the end is the start plus 8 B per 64-bit word. The asm text does not hold this instruction. On CRB the compiler makes it from a C statement of the kernel function. The test writes it here. |
| 187 | `        framed = '"v8"' in operands` | `framed`: true when the clobber list names `v8`. |
| 188 | `        head = [end if t == "END" else t for t in FRAME] if framed else [end]` | `head`: a framed kernel gets the lines of `FRAME`, with the end-pointer instruction at the place of `END`. Any other kernel gets the end-pointer instruction only. |
| 189 | `        out[k] = (pad, head + init, loop, (UNFRAME if framed else []) + ["ret"], operands)` | Stores per kernel: the pad, the instructions before the loop (`head` plus `init`), the loop, the instructions after the loop, and the operand text. The instructions after the loop are `UNFRAME` for a framed kernel, then `ret`. The test adds the `ret` itself. |
| 190 | `    return out` | Returns the dictionary. |

### Function `synth`: write listing text and offsets rows (lines 193 to 211)

| Line | Source | Explanation |
|---:|---|---|
| 193 | `def synth(funcs, binary="bwx12", start=0x6000, change=None):` | Starts the function `synth`. It writes the 26 kernels one after the other. The first address is `start`, 0x6000 by default (a multiple of 64). The binary name is `bwx12` by default. |
| 194 | `    """(listing text, offsets rows) of the new kernels; change(kernel, pad, head, loop, tail) may alter one"""` | Documentation text of `synth`: it returns the listing text and the offsets rows of the new kernels. The function `change`, with the arguments kernel, pad, head, loop and tail, may alter one kernel. |
| 195 | `    text, rows, addr = [], [], start` | `text`: the lines of the listing. `rows`: the rows of the offsets table. `addr`: the address that is free next. |
| 196 | `    for k, (pad, head, loop, tail, _) in funcs.items():` | Loop over the kernels in the order of the dictionary. The operand text is not used here. |
| 197 | `        head, loop, tail = list(head), list(loop), list(tail)` | Makes copies of the three instruction lists. So a change does not alter the lists of `funcs`. |
| 198 | `        if change:` | When a function `change` was given ... |
| 199 | `            pad, head, loop, tail = change(k, pad, head, loop, tail)` | ... it may alter the pad or the instruction lists of this kernel. Step 4 uses this. |
| 200 | `        addr = (addr + 63) // 64 * 64 + pad` | The function start is the next multiple of 64 B, plus `pad`. This is the rule of the `PLACE` macro [Ref3]. |
| 201 | `        first, loop_at = addr, addr + 4 * len(head)` | `first`: the function start. `loop_at`: the loop start. The loop starts after the instructions of `head`. Each AArch64 instruction is 4 B long. |
| 202 | `        text.append("=== %s %s ===\n%016x <k_%s>:" % (binary, k, first, k))` | Writes the block title and the label line of the function in the format of `listing.txt`. The address has 16 hexadecimal digits. |
| 203 | `        for t in head + loop + ["b.cc %x <k_%s+0x%x>  // b.lo, b.ul, b.last" % (loop_at, k, loop_at - first)] + tail:` | Loop over all instructions of the function: `head`, the loop, then the loop branch, then `tail`. The loop branch is written as `objdump` prints it: `b.cc` to the loop start, with the comment `// b.lo, b.ul, b.last`. `b.cc` and `b.lo` are the same instruction. |
| 204 | `            op, _, arg = t.partition(" ")` | Splits the instruction at its first space into the name `op` and the operands `arg`. |
| 205 | `            text.append("    %x:\t%s\t%s" % (addr, op, arg))` | Writes one line per instruction: four spaces, the address in hexadecimal, a colon, a tab, the name, a tab and the operands. |
| 206 | `            addr += 4` | The next instruction stands 4 B later. |
| 207 | `        text.append("")` | An empty line ends the block. |
| 208 | `        rows.append("%s\t%s\tk_%s\t%x\t%x\t%d" % (binary, k, k, first, loop_at, loop_at % 64))` | Writes the row of the offsets table, with tabs between the fields: binary, kernel, function, start, loop start (both hexadecimal) and loop start modulo 64 (decimal). |
| 209 | `    return "\n".join(text) + "\n", "\n".join(rows) + "\n"` | Returns the listing text and the offsets rows, each as one text that ends with a line end. |

### Function `test_aarch64_text` (step 3): the asm text against the checker (lines 212 to 241)

| Line | Source | Explanation |
|---:|---|---|
| 212 | `def test_aarch64_text(tmp):` | Starts the function `test_aarch64_text`. It holds step 3 and step 4. |
| 213 | `    try:` | Starts the block in which an error of `aarch64_functions` is caught. |
| 214 | `        funcs = aarch64_functions(tmp)` | `funcs`: the 26 kernels from `aarch64_functions`. |
| 215 | `    except RuntimeError as e:` | When it stops with one of its three errors (line 131, line 138, line 179) ... |
| 216 | `        check("AArch64 text: the expanded source has the asm template of every new kernel", False, e)` | ... the check of line 218 fails here, with the error text as its detail ... |
| 217 | `        return` | ... and the function returns. No other check of step 3 and step 4 runs then. |
| 218 | `    check("AArch64 text: the expanded source has the asm template of every new kernel", len(funcs) == 26)` | If no error came, the check passes when 26 kernels were found. |
| 219 | `    ref_l = open(os.path.join(REF, "listing.txt")).read().replace("=== bwx11 ", "=== bwx12 ")` | `ref_l`: the listing of the accepted bwx11 build, with the binary name changed from bwx11 to bwx12 in the block titles. The checker then reads these blocks as the first 29 kernels of a bwx12 build. |
| 220 | `    ref_o = open(os.path.join(REF, "offsets.tsv")).read().replace("bwx11\t", "bwx12\t")` | `ref_o`: the offsets table of the accepted bwx11 build, with the same change of the binary name. |
| 222 | `    def result(change=None):` | Starts the inner function `result`. It builds one checker input and runs the checker. |
| 223 | `        l, o = synth(funcs, change=change)` | `l` and `o`: the listing text and the offsets rows of the 26 new kernels from `synth`, with the change if one is given. |
| 224 | `        lp, op = os.path.join(tmp, "syn-listing.txt"), os.path.join(tmp, "syn-offsets.tsv")` | `lp` and `op`: the paths of the two input files in the temporary folder, `syn-listing.txt` and `syn-offsets.tsv`. |
| 225 | `        open(lp, "w").write(ref_l + l)` | The listing file is the accepted bwx11 listing plus the 26 blocks of `synth`. |
| 226 | `        open(op, "w").write(ref_o + o)` | The offsets file is built the same way. |
| 227 | `        return checker([lp, op])` | Runs the checker on the two files, without options. Its reference is then the same accepted bwx11 build. So the 29 old kernels are compared with a copy of themselves and cannot differ. Only the rules for the 26 new kernels can fail. |
| 229 | `    r = result()` | Step 3: runs the checker on the unchanged listing. The checker rules for a new kernel are [Ref2]. The loop holds exactly the expected instructions with every operand. For `read_nop256`: 8 `ldp`, 256 `nop`, `add`, `cmp`. The loop ends with the branch `b.cc` to the loop start. Before the loop stand only the end pointer, stores of d registers and the expected `movi` or `dup`. After the loop stand only loads of d registers, and the last instruction is `ret`. The loop offset is 20 B for a read kernel, 40 B for a write kernel, 52 B for a copy kernel. It equals the loop offset of `asmread`, `asmwrite` or `asmcopy` in the same listing. The row of the offsets table gives the same value. The function has one backward branch and no other branch. Each of d8 to d15 that the loop uses is stored before the loop and loaded after it. |
| 230 | `    check("AArch64 text: the listing made from the source text passes check_listing12.py (26 new kernels, loop offsets 20, 40, 52)",` | The check of step 3. Its text says that the listing made from the source text passes the checker, with 26 new kernels and the loop offsets 20, 40 and 52. |
| 231 | `          r.returncode == 0 and "new_kernels=26 new_failed_rows=0" in r.stdout and "kernels=29 failed_rows=0" in r.stdout,` | Continues the call of line 230: the unchanged listing must pass. That needs exit status 0, 29 old rows without a failure and 26 new rows without a failure. The two texts `new_kernels=26 new_failed_rows=0` and `kernels=29 failed_rows=0` of the summary line of the checker show this. A pass shows that the asm text and the pads of `bwx12.c` agree with the checker, if the frame is as assumed. |
| 232 | `          "\n".join(l for l in r.stdout.splitlines() if "FAIL" in l)[:1500])` | Continues the call: on a failure the detail is the lines of the checker output that hold `FAIL`, at most 1500 characters. |
| 233 | `    # clobber lists: every v register of the text is named as a clobber` | Comment: the check of the clobber lists. Every v register of the text must be named as a clobber. |
| 234 | `    bad = []` | `bad`: the kernels that fail this check. |
| 235 | `    for k, (_, head, loop, _, operands) in funcs.items():` | Loop over the new kernels. |
| 236 | `        used = {int(n) for t in head + loop for n in re.findall(r"\b[qv](\d+)\b", t)}` | `used`: the numbers of all q and v registers in the instructions before the loop and in the loop. |
| 237 | `        named = {int(n) for n in re.findall(r'"v(\d+)"', operands)}` | `named`: the numbers of the v registers in the clobber list. The pattern takes the number from each text of the form `"v8"` in the operand text. |
| 238 | `        if not used <= named:` | When a used register is not named ... |
| 239 | `            bad.append((k, sorted(used - named)))` | ... the kernel and the missing numbers go into `bad`. |
| 240 | `    check("AArch64 text: every vector register that a new kernel uses is in its clobber list", not bad, bad)` | The check fails when `bad` holds a kernel. gcc does not read the asm text. The vector registers of the text are not operands. So gcc learns only from the clobber list that the text changes them. |

### Step 4: changed copies of the listing that the checker must reject (lines 242 to 279)

| Line | Source | Explanation |
|---:|---|---|
| 242 | `    def one_nop_less(victim):` | Starts the inner function `one_nop_less`. `one_nop_less(victim)` returns a change function for `synth`. |
| 243 | `        def f(k, pad, head, loop, tail):` | Starts the change function `f`. |
| 244 | `            if k == victim:` | For the kernel `victim` ... |
| 245 | `                loop.remove("nop")` | ... it removes one `nop` from the loop. |
| 246 | `            return pad, head, loop, tail` | All other kernels stay unchanged. |
| 247 | `        return f` | Returns the change function. |
| 249 | `    def other_source(k, pad, head, loop, tail):` | Starts the change function `other_source`. |
| 250 | `        if k == "read_dadd8":` | In `read_dadd8` ... |
| 251 | `            loop[loop.index("add v17.2d, v17.2d, v2.2d")] = "add v17.2d, v17.2d, v24.2d"` | ... one add gets the source register v24 in place of v2. The loop loads v2. It does not load v24. The number of instructions stays the same. |
| 252 | `        return pad, head, loop, tail` | Returns the four values. |
| 254 | `    def moved(k, pad, head, loop, tail):` | Starts the change function `moved`. |
| 255 | `        return (pad + 4 if k == "write_nop96" else pad), head, loop, tail` | Adds 4 B to the pad of `write_nop96`. The function and its loop start move by 4 B, the length of one instruction. The loop offset becomes 44 B in place of 40 B. |
| 257 | `    def no_d8(k, pad, head, loop, tail):` | Starts the change function `no_d8`. |
| 258 | `        if k == "read_iadd16":` | In `read_iadd16` ... |
| 259 | `            head[0] = "sub sp, sp, #0x40"` | ... the first frame instruction is replaced by `sub sp, sp, #0x40`. The original instruction stores d8 and d9 and moves the stack pointer down by 64 B. The replacement only moves the stack pointer. So d8 and d9 are never stored. |
| 260 | `        return pad, head, loop, tail` | Returns the four values. |
| 262 | `    def no_init(k, pad, head, loop, tail):` | Starts the change function `no_init`. |
| 263 | `        if k == "read_dadd2":` | In `read_dadd2` ... |
| 264 | `            head.remove("movi v16.4s, #0x0")` | ... the instruction `movi v16.4s, #0x0` is removed. It sets v16 to 0 before the loop. The first add of the loop collects its sum in v16. |
| 265 | `            pad += 4` | The pad grows by 4 B, so the loop start keeps its address. The loop offset rule can therefore not report this change. |
| 266 | `        return pad, head, loop, tail` | Returns the four values. |
| 268 | `    for name, change, kernel in (("one nop less in read_nop256", one_nop_less("read_nop256"), "read_nop256"),` | Starts the loop over 7 cases. Each case has a name, a change function and the name of the changed kernel. The first case is `read_nop256` with 255 `nop`. The whole-chip test runs this kernel in part L [Ref9]. |
| 269 | `                                 ("one nop less in copy_nop192", one_nop_less("copy_nop192"), "copy_nop192"),` | Case 2: one `nop` less in `copy_nop192`. |
| 270 | `                                 ("one nop less in read_sp56", one_nop_less("read_sp56"), "read_sp56"),` | Case 3: one `nop` less in `read_sp56`. |
| 271 | `                                 ("an add of read_dadd8 that takes v24 in place of a loaded register", other_source, "read_dadd8"),` | Case 4: an add of `read_dadd8` that takes v24 in place of a loaded register. |
| 272 | `                                 ("the loop of write_nop96 moved by 4 B", moved, "write_nop96"),` | Case 5: the loop of `write_nop96` moved by 4 B. |
| 273 | `                                 ("read_iadd16 without the store of d8 and d9", no_d8, "read_iadd16"),` | Case 6: `read_iadd16` without the store of d8 and d9. |
| 274 | `                                 ("read_dadd2 without the movi of v16", no_init, "read_dadd2")):` | Case 7: `read_dadd2` without the `movi` of v16. |
| 275 | `        r = result(change)` | Runs the checker on the changed listing, one change per run. |
| 276 | `        failed = [l.split("\t")[0] for l in r.stdout.splitlines() if "\tFAIL" in l]` | `failed`: the kernel names of the checker output rows that contain a tab followed by `FAIL`. The name is the first field of the row. |
| 277 | `        check("check_listing12.py fails, on this kernel only: %s" % name, r.returncode == 1 and failed == [kernel], failed)` | A check passes only when the checker ends with status 1 and `failed` holds exactly the changed kernel. So each check proves two things. The checker fails the row of the changed kernel. It fails no other row. The test does not compare the reason that the checker prints. |

### Function `main` and the start of the script (lines 280 to 296)

| Line | Source | Explanation |
|---:|---|---|
| 280 | `def main():` | Starts the function `main`. It runs the three test functions. |
| 281 | `    tmp = tempfile.mkdtemp(prefix="bwx12-test-")` | Creates a new temporary folder. Its name starts with `bwx12-test-`. |
| 282 | `    try:` | Starts a block whose end part (lines 286 to 290) runs in every case. |
| 283 | `        test_source(tmp)` | Step 1: `test_source`. |
| 284 | `        test_standin(tmp)` | Step 2: `test_standin`. It needs the files that `test_source` wrote. |
| 285 | `        test_aarch64_text(tmp)` | Steps 3 and 4: `test_aarch64_text`. |
| 286 | `    finally:` | The next lines run even when a test function stops with an error. |
| 287 | `        if os.environ.get("KEEP"):` | When the environment variable `KEEP` is set and not empty ... |
| 288 | `            print("# kept: %s" % tmp)` | ... the folder is kept and its path is printed. |
| 289 | `        else:` | If not ... |
| 290 | `            shutil.rmtree(tmp, ignore_errors=True)` | ... the folder is deleted. An error of the delete is ignored. |
| 291 | `    print("# failed checks: %d" % fails)` | Prints the number of failed checks in the line `# failed checks: N`. |
| 292 | `    return 1 if fails else 0` | The return value is 1 if a check failed and 0 if not. After an error that no test function handles, this line and the line before it are not run. Python then prints a traceback and ends with status 1. |
| 295 | `if __name__ == "__main__":` | This test is true when the file is started as a script. |
| 296 | `    sys.exit(main())` | The return value of `main` becomes the exit status of the process. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/ref-bwx11/build.txt`: Build record of the accepted bwx11 build. Lines 15 and 16 hold the sha256 of `bwx11.c` and `bwx11_selftest.c` that step 1 compares with.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py`: The checker. Lines 17-25: the rules for the 29 kernels of the reference. Lines 46-71: the rules for the 26 new kernels. Lines 117-131: the table `NEW` with the expected loops. Lines 364-366: the option `--skip-new`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: Lines 2-32: `bwx12.c` is `bwx11.c` plus marked blocks. Line 163: the macro `PLACE`. Lines 1077-1450: the kernels of round 5 and their pads. Line 1491: the function `call`. Lines 1515 and 1967: the functions `read_smaps` and `tcount`. Lines 1632-1714: `worker` reads the clock and calls `call`. Lines 1995 and 2056: the timed functions of the trial mode. Lines 2921-2924: the option `--list`.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: Lines 23-24: the exit statuses. Lines 31-34: `BWX_MARKER` and `BWX_CPUS`. Lines 47-75: build, self-test, `listing.txt` and `offsets.tsv`. Lines 77-82: the allowed branch targets of the two timed functions. Lines 107-115: the placement line of `build.txt`.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/check_listing12.out`: Output of the checker for the CRB build of 2026-11-15. Line 58, the last line: `kernels=29 failed_rows=0 new_kernels=26 new_failed_rows=0`.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/`: Files of the CRB build. `listing.txt` lines 1126-3921: the blocks of the 26 new kernels. `offsets.tsv` lines 31-56: their rows. `build.txt` line 17: the sha256 of `bwx12.c`. `build.txt` line 20: the sha256 of the binary `bwx12`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c`: Lines 7-11 and 692-699: the checks per kernel. 3 buffer sizes and 2 single blocks for every kernel, and 3 page checks more for a read kernel. A copy kernel prints 2 rows per buffer size.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/ref-bwx11/listing.txt`: Accepted listing of bwx11. Lines 59-81: `asmread` with the frame that the test assumes, pointer in x0, end in x1. Lines 83-98: `asmwrite`, value in x2. Lines 100-131: `asmcopy`, source in x1, end in x2.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec`: Argument line of part L of the whole-chip test. It holds `--seq oldread,asmread,read_nop96,read_nop256,read_1pl`. The files `cfwd.spec` and `crev.spec` of the same folder also hold `--seq` and no `--trial`.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: Driver of the whole-chip test. Line 13 holds the required sha256 of the binary `bwx12`. Line 23 stops the run when the binary has another sha256. The value equals line 20 of `build.txt` of the CRB build.
- [Ref11] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/4a6b911c-1987-43f1-be61-e96fcfc7261d/subagents/workflows/wf_0693c37a-c1b/agent-a15247d530cb60ec0.jsonl`: The saved record of the commands of an AI agent (Claude Code) of 2026-11-15, one JSON record per line. It lies outside the project folder. Line 29: the command that runs `python3 test_kernels12.py`. Line 30: its output. Line 37: the command that copies the sources to CRB and starts `build12.sh` there.
