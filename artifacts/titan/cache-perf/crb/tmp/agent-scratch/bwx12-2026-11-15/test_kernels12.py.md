# `test_kernels12.py` explained

- Source file: `test_kernels12.py` in this folder (Python script, 296 lines, 14449 bytes).
- sha256 of the source when this page was built: `11de5c58900208af363e57c8399feea2da404c65fdc897facc649a1096eeea70`.
- Role in the whole-chip test: Local test of the bwx12 kernel source and its acceptance checker. It measures nothing.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File header: what the test is and how to run it</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  #!/usr/bin/env python3
  2  """test_kernels12.py - local tests of the kernels of round 5 (bwx12).
  3
  4  Runs on the development machine (x86-64). There is no AArch64 compiler here,
  5  so the asm text of the new kernels is NOT assembled by this test. What it does:</pre></td><td valign="top"><ul><li>The test runs on the development machine (x86-64 CPUs).</li><li>That machine has no compiler for AArch64, the instruction set of CRB. So the test never assembles the asm text of the kernels.</li><li><b>Round 5</b> is the set of additions that makes <code>bwx12.c</code> from <code>bwx11.c</code>. It is not a round of a measurement.</li><li><b>New kernels</b> means the 26 kernels that round 5 added. It does not mean the new read kernel of the whole-chip test.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  6
  7   1. source: bwx12.c and bwx12_selftest.c without their blocks "bwx12+" to
  8      "bwx12-" are bwx11.c and bwx11_selftest.c byte for byte (sha256 of the
  9      accepted build, ref-bwx11/build.txt).</pre></td><td valign="top">Step 1, the source text.<ul><li><code>bwx12.c</code> marks each addition: a comment line <code>bwx12+</code> stands before it and a comment line <code>bwx12-</code> after it.</li><li>Without these blocks the file must be <code>bwx11.c</code>, byte for byte. The test compares the sha256 with the value in <code>ref-bwx11/build.txt</code>, the record of the accepted bwx11 build.</li><li>The same rule holds for the self-test source.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 10   2. stand-in build: build12.sh builds bwx12.c here (plain C stand-in kernels),
 11      runs the self-test and writes listing.txt and offsets.tsv. --list must
 12      print 55 names. The same script text builds the bwx11 source (bwx12.c
 13      without its blocks) as the reference. check_listing12.py --skip-new must
 14      find the 29 old kernels with the same machine code and the same loop
 15      offset in both builds: the new kernels do not move the old ones.</pre></td><td valign="top">Step 2, a local build.<ul><li>On x86-64, <code>bwx12.c</code> compiles each asm or NEON kernel as a plain C loop, a <b>stand-in</b>.</li><li>The test builds two programs with the same script <code>build12.sh</code>: one from <code>bwx12.c</code>, one from the bwx11 text.</li><li><code>--list</code> prints the kernel names. 29 kernels of bwx11 plus 26 new kernels gives 55 names.</li><li>The checker <code>check_listing12.py</code> must find the same machine code and the same loop offset for the 29 kernels in both builds. <code>--skip-new</code> leaves out its rules for the 26 new kernels.</li><li><b>Loop offset</b>: the address of the loop start modulo 64.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 16   3. AArch64 text: gcc -E -D__aarch64__ expands the macros of the AArch64
 17      branch. The test takes the asm template of every new kernel from that
 18      output, expands .rept, puts the registers in (x0, x1, x2 as in the
 19      accepted listings), and writes the function as objdump would print it,
 20      with the frame that gcc 14.2 made for the same clobber list in the
 21      accepted build (an ASSUMPTION: 4 stores of d8-d15 when v8-v15 are
 22      clobbered, else none). The function start is the next 64 B boundary plus
 23      the pad of PLACE(name), computed from the expanded text. This listing,
 24      after the accepted listing of bwx11, must pass check_listing12.py.</pre></td><td valign="top">Step 3, the AArch64 text.<ul><li><code>gcc -E</code> runs only the preprocessor: it expands macros and includes. With <code>-D__aarch64__</code> it prints the AArch64 branch of the source. Nothing is compiled.</li><li>The test takes the asm text of each new kernel from that output and writes it in the format of an <code>objdump</code> listing.</li><li>The compiler adds a frame around some kernels: stores of d8 to d15 before the loop and loads after it. The test cannot see the real frame. It writes the frame of the accepted bwx11 listing. The comment calls this an assumption.</li><li>The function start is the next 64 B boundary plus the pad of the <code>PLACE</code> macro.</li><li>This listing, put after the accepted bwx11 listing, must pass the checker.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 25   4. changed copies of that listing must fail: one nop less, an add with
 26      another source register, a loop moved by 4 B, a missing store of d8.</pre></td><td valign="top">Step 4, changed copies.<ul><li>The test changes one kernel of that listing and runs the checker again. The checker must fail.</li><li>The comment names four kinds of change. The code runs seven cases (line 268). One of them is of a fifth kind: a missing <code>movi</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 27
 28  Usage: test_kernels12.py            (KEEP=1 keeps the temporary folder)
 29  Output: one line per check, "PASS name" or "FAIL name: detail". Exit status 0
 30  only if every check passed.
 31  """</pre></td><td valign="top"><ul><li>Start the script with no argument, for example <code>python3 test_kernels12.py</code>.</li><li>With the environment variable <code>KEEP=1</code> the temporary folder is kept. It holds the two builds and the listings.</li><li>Output: one line <code>PASS name</code> or <code>FAIL name: detail</code> per check.</li><li>Exit status 0 means that every check passed.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 32  import hashlib
 33  import os
 34  import re
 35  import shutil
 36  import subprocess
 37  import sys
 38  import tempfile
 39</pre></td><td valign="top">Modules of the Python standard library. <code>hashlib</code> computes sha256. <code>subprocess</code> starts other programs. <code>tempfile</code> creates the temporary folder.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 40  HERE = os.path.dirname(os.path.abspath(__file__))
 41  REF = os.path.join(HERE, "ref-bwx11")
 42  sys.path.insert(0, HERE)
 43  import check_listing12 as cl  # noqa: E402
 44
 45  fails = 0
 46
 47</pre></td><td valign="top"><ul><li><code>HERE</code>: the folder of this script. The paths of all source and reference files start from it, so the script can be started from any folder.</li><li><code>REF</code>: the folder <code>ref-bwx11</code> beside the script. It holds the build record, the listing and the offsets table of the accepted bwx11 build.</li><li>Lines 42-43 load <code>check_listing12.py</code> of the same folder as the module <code>cl</code>. The test takes two things from it: the names of the 26 new kernels (the keys of its table <code>NEW</code>) and its two end-pointer instructions. The test does not read the expected loops of <code>NEW</code>. Only the checker process compares with them.</li><li><code>fails</code> counts the failed checks.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>check</code>: print one result line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 48  def check(name, ok, detail=""):
 49      global fails
 50      print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or detail == "" else ": %s" % (detail,)))
 51      fails += not ok
 52
 53</pre></td><td valign="top">Prints <code>PASS name</code> or <code>FAIL name: detail</code> for one check.<ul><li><code>ok</code> is the result of the check.</li><li>The detail is printed only when the check failed and a detail was given.</li><li>Line 51 adds 1 to <code>fails</code> for a failed check. A failed check does not stop the script.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>strip12</code>: remove the bwx12 blocks</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 54  def strip12(text):
 55      out, skip = [], False
 56      for line in text.splitlines(keepends=True):
 57          if line == "/* bwx12+ */\n":
 58              skip = True
 59          elif line == "/* bwx12- */\n":
 60              skip = False
 61          elif not skip:
 62              out.append(line)
 63      return "".join(out)
 64
 65</pre></td><td valign="top">Returns <code>text</code> without its bwx12 blocks.<ul><li>A line that is exactly <code>/* bwx12+ */</code> starts a block.</li><li>A line that is exactly <code>/* bwx12- */</code> ends it.</li><li>The two marker lines and all lines between them are dropped.</li><li>Every other line is kept unchanged, with its line end.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>run</code>: start a program, keep its output</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 66  def run(cmd, **kw):
 67      return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, **kw)
 68
 69</pre></td><td valign="top">Starts the command <code>cmd</code> and waits until it ends. The returned object holds the exit status (<code>returncode</code>), the standard output and the error output as text. Extra arguments such as <code>env</code> are passed on.</td></tr>
<tr><td colspan="2"><b>Function <code>checker</code>: run check_listing12.py</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 70  def checker(args):
 71      return run([sys.executable, os.path.join(HERE, "check_listing12.py")] + args)
 72
 73</pre></td><td valign="top">Runs <code>check_listing12.py</code> of the same folder as a separate process, with the arguments <code>args</code>. <code>sys.executable</code> is the Python interpreter that runs this test.</td></tr>
<tr><td colspan="2"><b>Function <code>test_source</code>: bwx12 source without additions equals bwx11</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 74  def test_source(tmp):
 75      digests = dict(reversed(l.split()) for l in open(os.path.join(REF, "build.txt")) if re.match(r"[0-9a-f]{64}  ", l))</pre></td><td valign="top">Line 75 reads <code>ref-bwx11/build.txt</code> and keeps the lines that start with 64 hexadecimal digits and two spaces. These are the sha256 lines of the accepted bwx11 build [Ref1]. <code>digests</code> maps each file name to its sha256.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 76      for new, old in (("bwx12.c", "bwx11.c"), ("bwx12_selftest.c", "bwx11_selftest.c")):
 77          text = strip12(open(os.path.join(HERE, new)).read())
 78          check("source: %s without its bwx12 blocks has the sha256 of the accepted %s" % (new, old),
 79                hashlib.sha256(text.encode()).hexdigest() == digests.get(old), digests.get(old))
 80          open(os.path.join(tmp, old), "w").write(text)
 81
 82</pre></td><td valign="top">The loop runs for <code>bwx12.c</code> and for <code>bwx12_selftest.c</code>.<ul><li>Line 77 reads the file and removes the bwx12 blocks.</li><li>Lines 78-79: the check passes when the sha256 of the rest equals the recorded sha256 of <code>bwx11.c</code> or <code>bwx11_selftest.c</code>. On a failure the detail is the recorded value.</li><li>Line 80 writes the rest into the temporary folder under the bwx11 name. <code>test_standin</code> uses it as the reference source.</li><li>A pass proves this: every line outside the marked blocks is the text of the accepted bwx11 source, byte for byte.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>test_standin</code>: local build with and without the new kernels</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 83  def test_standin(tmp):
 84      new, old = os.path.join(tmp, "new"), os.path.join(tmp, "old")
 85      os.mkdir(new)
 86      os.mkdir(old)
 87      for name in ("bwx12.c", "bwx12_selftest.c", "build12.sh"):
 88          shutil.copy(os.path.join(HERE, name), new)</pre></td><td valign="top">Creates the folders <code>new</code> and <code>old</code> in the temporary folder. <code>new</code> gets copies of <code>bwx12.c</code>, <code>bwx12_selftest.c</code> and <code>build12.sh</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 89      # the reference: the bwx11 source under the names of bwx12, so the same build script builds it
 90      src = open(os.path.join(tmp, "bwx11.c")).read()
 91      open(os.path.join(old, "bwx12.c"), "w").write(src.replace('#include "bwx11_selftest.c"', '#include "bwx12_selftest.c"'))
 92      shutil.copy(os.path.join(tmp, "bwx11_selftest.c"), os.path.join(old, "bwx12_selftest.c"))
 93      shutil.copy(os.path.join(HERE, "build12.sh"), old)</pre></td><td valign="top"><code>old</code> gets the reference source under the file names of bwx12.<ul><li>Lines 90-91: the bwx11 text of <code>test_source</code> is saved as <code>bwx12.c</code>. Its include line for the self-test is changed to name <code>bwx12_selftest.c</code>.</li><li>Line 92: the bwx11 self-test text is saved as <code>bwx12_selftest.c</code>.</li><li>Line 93: the same <code>build12.sh</code> is copied.</li></ul>So the same script builds both folders, and both binaries are named <code>bwx12</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 94      cpus = ",".join(str(c) for c in sorted(os.sched_getaffinity(0)) if c &lt;= 119)
 95      env = dict(os.environ, BWX_CPUS=cpus, BWX_MARKER=os.path.join(tmp, "no-marker"))</pre></td><td valign="top"><ul><li>Line 94 lists the CPUs that this process may run on, without any CPU above 119.</li><li><code>BWX_CPUS</code>: <code>build12.sh</code> restarts itself under <code>taskset</code> (a tool that limits a program to a list of CPUs) on this CPU list. Its default list is CPUs 0-119, the CPUs that the tests use on CRB [Ref4]. So the two builds run only on CPUs that the test process may use.</li><li><code>BWX_MARKER</code>: <code>build12.sh</code> stops when its marker file exists (by default <code>/tmp/positron-perf.RUNNING</code>). The test names a file that does not exist, so this stop cannot happen here.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 96      for d in (new, old):
 97          r = run(["bash", os.path.join(d, "build12.sh")], env=env)
 98          check("stand-in build: build12.sh exit 0 in %s" % os.path.basename(d), r.returncode == 0, r.stderr[-400:])
 99          if r.returncode:
100              return</pre></td><td valign="top"><ul><li>Runs <code>bash build12.sh</code> in <code>new</code>, then in <code>old</code>, with the two variables set.</li><li>Each run compiles <code>bwx12.c</code> with gcc, runs the self-test of the binary, and writes <code>build.txt</code>, <code>listing.txt</code>, <code>offsets.tsv</code> and <code>selftest-bwx12.txt</code> into its folder [Ref4].</li><li>Both binaries are x86-64 programs with stand-in kernels.</li><li>The check fails when the script ends with a status other than 0. The detail is the last 400 characters of its error output.</li><li><code>build12.sh</code> ends with status 5 when the compile fails, and with status 4 when the self-test fails. It ends with status 6 when its check of the branch targets of the two timed functions of the trial mode fails [Ref4].</li><li>After a failed build the function returns. The checks of lines 101-117 are then not run.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">101      names = run([os.path.join(new, "bwx12"), "--list"]).stdout.split()
102      check("stand-in build: --list prints 55 names, the 26 new ones last and in the order of check_listing12.py",
103            len(names) == 55 and names[29:] == list(cl.NEW), names[29:])</pre></td><td valign="top">Runs the new binary with <code>--list</code>. It prints one kernel name per line and ends [Ref3]. The check passes when there are 55 names and names 30 to 55 equal the keys of <code>NEW</code> in <code>check_listing12.py</code>, in the same order.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">104      st = open(os.path.join(new, "selftest-bwx12.txt")).read()
105      rows = [l.split(",") for l in st.splitlines() if not l.startswith(("#", "call,"))]
106      per = {k: sum(1 for r in rows if r[0] == k and r[-1] == "pass") for k in cl.NEW}
107      want = {k: 8 if k.startswith("read") else 5 if k.startswith("write") else 8 for k in cl.NEW}
108      check("stand-in build: the self-test has 8 passed checks per new read kernel, 5 per write kernel, 8 per copy kernel",
109            per == want and "FAIL" not in st and st.rstrip().endswith("# failures=0"), per)</pre></td><td valign="top">Reads the self-test output of the new build. A result row has the fields kernel, check, bytes, result.<ul><li>Line 105 drops the comment lines and the <code>call,</code> lines.</li><li>Line 106 counts, for each new kernel, the rows with the result <code>pass</code>.</li><li>Line 107 holds the expected counts: 8 for a read kernel, 5 for a write kernel, 8 for a copy kernel [Ref7].</li><li>The text must also contain no <code>FAIL</code> and end with <code># failures=0</code>.</li></ul>Here these rows test the stand-in loops, not the asm kernels.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">110      r = checker([os.path.join(new, "listing.txt"), "--ref-listing", os.path.join(old, "listing.txt"),
111                   "--ref-offsets", os.path.join(old, "offsets.tsv"), "--ref-binary", "bwx12", "--skip-new"])
112      check("stand-in build: the 29 old kernels have the same machine code and loop offset with and without the new kernels",
113            r.returncode == 0 and "kernels=29 failed_rows=0" in r.stdout, r.stdout[-600:])</pre></td><td valign="top">Runs the checker on the listing of <code>new</code>. The listing and the offsets table of <code>old</code> are the reference.<ul><li><code>--ref-binary bwx12</code>: the blocks of the reference listing have the binary name bwx12 here.</li><li><code>--skip-new</code>: the rules for the 26 new kernels are left out.</li><li>The check passes when the checker ends with status 0 and prints <code>kernels=29 failed_rows=0</code>.</li><li>Meaning: each of the 29 kernels of bwx11 has the same instruction text and the same loop offset in both builds [Ref2]. The checker compares <code>objdump</code> text. Of the addresses it compares only the loop start modulo 64 and the distance of a branch target from the function start.</li><li>This result holds for the x86-64 build only.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">114      place = [l for l in open(os.path.join(new, "build.txt")) if l.startswith("## placement bwx12")]
115      place_old = [l for l in open(os.path.join(old, "build.txt")) if l.startswith("## placement bwx12")]
116      check("stand-in build: call() to timed_sequence_hot() start at the same offsets modulo 64 with and without the new kernels",
117            place and place == place_old, (place, place_old))
118
119</pre></td><td valign="top"><code>build12.sh</code> writes one line that starts with <code>## placement bwx12</code> into <code>build.txt</code>. It lists the start address modulo 64 of <code>call</code>, <code>read_smaps</code>, <code>tcount</code>, <code>timed_sequence</code> and <code>timed_sequence_hot</code>, as far as the binary has these symbols [Ref4].<ul><li><code>call</code> runs one kernel on a part of a buffer. In the interval mode (option <code>--seq</code>) the thread function <code>worker</code> reads the clock and calls it [Ref3]. The whole-chip test uses this mode [Ref9].</li><li><code>timed_sequence</code> and <code>timed_sequence_hot</code> are the timed functions of the trial mode. The whole-chip test does not use that mode.</li></ul>The check passes when both builds have this line and the two lines are equal.</td></tr>
<tr><td colspan="2"><b>Assumed frame of a kernel that uses v8 to v15</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">120  FRAME = ["stp d8, d9, [sp, #-64]!", "END", "stp d10, d11, [sp, #16]", "stp d12, d13, [sp, #32]", "stp d14, d15, [sp, #48]"]
121  UNFRAME = ["ldp d10, d11, [sp, #16]", "ldp d12, d13, [sp, #32]", "ldp d14, d15, [sp, #48]", "ldp d8, d9, [sp], #64"]
122
123</pre></td><td valign="top"><ul><li><code>FRAME</code>: the instructions that the test writes before the loop of a kernel whose clobber list names v8. <code>stp</code> stores two registers. The four <code>stp</code> store d8 to d15 to the stack.</li><li><code>END</code> is a placeholder. Line 188 puts the end-pointer instruction there.</li><li><code>UNFRAME</code>: the four <code>ldp</code> that load d8 to d15 back after the loop.</li><li>This is the frame of <code>asmread</code> and <code>asmcopy</code> in the accepted bwx11 listing [Ref8]. For the new kernels it is an assumption of the test.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>aarch64_functions</code>: asm text of each new kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">124  def aarch64_functions(tmp):
125      """{kernel: (pad, [instruction text before the loop], [loop], [after the loop])} from gcc -E -D__aarch64__"""
126      stub = os.path.join(tmp, "stub")
127      os.mkdir(stub)
128      open(os.path.join(stub, "arm_neon.h"), "w").write("")
129      r = run(["gcc", "-E", "-P", "-D__aarch64__", "-I", stub, os.path.join(HERE, "bwx12.c")])
130      if r.returncode:
131          raise RuntimeError(r.stderr[-400:])
132      text = r.stdout</pre></td><td valign="top"><ul><li>Lines 126-128 create a folder <code>stub</code> with an empty file <code>arm_neon.h</code>. The AArch64 branch of <code>bwx12.c</code> includes this header, and the x86-64 gcc does not have it.</li><li>Line 129 runs <code>gcc -E -P -D__aarch64__</code> on <code>bwx12.c</code>. <code>-E</code>: expand macros and includes only, do not compile, assemble or link. <code>-P</code>: leave out the marker lines that give file name and line number. <code>-D__aarch64__</code>: select the AArch64 branch of the source. <code>-I</code>: search the folder <code>stub</code> for headers.</li><li>Lines 130-131 stop with an error when gcc fails. The message is the last 400 characters of the gcc messages.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">133      out = {}
134      for k in cl.NEW:
135          m = re.search(r'__asm__\(((?:\s*"[^"]*")+)\s*\);\s*__attribute__\(\(noinline\)\) static void k_%s\(([^)]*)\)\s*\{(.*?)\n\}' % k,
136                        text, re.S)
137          if not m:
138              raise RuntimeError("no function k_%s in the expanded text" % k)
139          place = "".join(re.findall(r'"([^"]*)"', m.group(1))).replace("\\n", "\n")
140          pad = eval(re.search(r"\.fill (.*), 1, 0", place).group(1))  # an expression of numbers, from our own source</pre></td><td valign="top">For each of the 26 new kernels, the pattern of line 135 finds two things that stand one after the other in the gcc output:<ul><li>the <code>PLACE</code> statement of the kernel: an <code>__asm__(...)</code> that holds only string literals,</li><li>the function <code>k_&lt;name&gt;</code> with its parameter list and its body.</li></ul>Lines 137-138 stop with an error when a kernel is not found. Line 139 joins the strings of the <code>PLACE</code> statement. Line 140 takes the expression after <code>.fill</code> and computes its value. This value <code>pad</code> is the number of zero bytes between the 64 B boundary and the function start [Ref3].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">141          body = m.group(3)
142          a = body.index("__asm__ volatile(")
143          # the template: the string literals up to the first ':' that stands outside a string
144          i, lit = a + len("__asm__ volatile("), []
145          while True:
146              c = body[i]
147              if c == '"':
148                  j = i + 1
149                  while body[j] != '"':
150                      j += 2 if body[j] == "\\" else 1
151                  lit.append(body[i + 1:j])
152                  i = j + 1
153              elif c == ":":
154                  break
155              else:
156                  i += 1
157          operands = body[i:body.index(");", i)]  # the operand and clobber lists of this asm statement only
158          asm = "".join(lit).replace("\\n", "\n").replace("\\t", "\t")</pre></td><td valign="top">A gcc asm statement has the form <code>__asm__ volatile(template : outputs : inputs : clobbers)</code>. The template is a row of string literals.<ul><li>Lines 142-156 start at the first <code>__asm__ volatile(</code> of the body. They collect each string literal up to the first colon outside a string. This is the template.</li><li>Line 157 keeps the text from that colon to the next <code>);</code> as <code>operands</code>: the operand lists and the clobber list.</li><li>Line 158 joins the literals and turns the escape sequences for line end and tab into real characters. The result <code>asm</code> is the assembler text of the kernel.</li><li>The captured body can be longer than the function. gcc prints a kernel that a macro defines on one line, and the pattern ends the body at a line that starts with <code>}</code>. So only the first asm statement is used.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">159          copy = "restrict d" in m.group(2)
160          reg = {"s": "x1", "d": "x0", "end": "x2"} if copy else {"p": "x0", "end": "x1", "v": "x2"}</pre></td><td valign="top"><ul><li>Line 159: a kernel is a copy kernel when its parameter list holds the words <code>restrict d</code>.</li><li>Line 160 names the register for each operand of the template. Read and write kernels: pointer <code>p</code> in x0, <code>end</code> in x1, value <code>v</code> in x2. Copy kernels: destination <code>d</code> in x0, source <code>s</code> in x1, <code>end</code> in x2.</li><li>The test sets these registers. They are the registers of the same operands in the accepted bwx11 listing [Ref8].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">161          lines, rep = [], None
162          for line in asm.split("\n"):
163              line = re.sub(r"%\[(\w+)\]", lambda g: reg[g.group(1)], line.strip())
164              if not line:
165                  continue
166              g = re.fullmatch(r"\.rept (\d+)", line)
167              if g:
168                  rep = (int(g.group(1)), [])
169              elif line == ".endr":
170                  lines += rep[1] * rep[0]
171                  rep = None
172              elif rep is not None:
173                  rep[1].append(line)
174              else:
175                  lines.append(line)</pre></td><td valign="top">Turns the assembler text into a flat list of instructions.<ul><li>Line 163 removes the white space at both ends of a line and replaces each operand <code>%[name]</code> by its register.</li><li><code>.rept N</code> and <code>.endr</code> are assembler directives: the lines between them are repeated N times. Lines 166-173 do this repeat here. For <code>read_nop256</code> the result holds 256 <code>nop</code> lines.</li><li>Empty lines are skipped.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">176          at = lines.index("1:")
177          init, loop = lines[:at], lines[at + 1:]
178          if loop[-1] != "b.lo 1b":
179              raise RuntimeError("%s: the template does not end with b.lo 1b" % k)
180          loop = loop[:-1]</pre></td><td valign="top"><ul><li><code>1:</code> is the label at the loop start. The lines before it run once per call (<code>init</code>). The lines after it are the loop.</li><li>The last line must be <code>b.lo 1b</code>: branch back to label 1 while the pointer is below the end. If it is not, lines 178-179 stop with an error.</li><li>Line 180 removes this line. <code>synth</code> writes the branch later, with its address.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">181          # the spelling of objdump: immediates of add and movi in hex
182          def spell(t):
183              t = re.sub(r"^(add x\d, x\d, )#(\d+)$", lambda g: "%s#0x%x" % (g.group(1), int(g.group(2))), t)
184              return re.sub(r"^(movi v\d+\.4s, )#(\d+)$", lambda g: "%s#0x%x" % (g.group(1), int(g.group(2))), t)
185          init, loop = [spell(t) for t in init], [spell(t) for t in loop]</pre></td><td valign="top"><code>spell</code> writes a number as <code>objdump</code> prints it. The decimal number after <code>#</code> becomes hexadecimal in two instruction forms: <code>add</code> of x registers and <code>movi</code>. Example: <code>add x0, x0, #256</code> becomes <code>add x0, x0, #0x100</code>. Line 185 applies it to <code>init</code> and to the loop.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">186          end = cl.COPY_END_POINTER if copy else cl.END_POINTER
187          framed = '"v8"' in operands
188          head = [end if t == "END" else t for t in FRAME] if framed else [end]
189          out[k] = (pad, head + init, loop, (UNFRAME if framed else []) + ["ret"], operands)
190      return out
191
192</pre></td><td valign="top"><ul><li>Line 186: the end-pointer instruction, as <code>check_listing12.py</code> expects it. For a read or write kernel it is <code>add x1, x0, x1, lsl #3</code>: end = start + 8 B per 64-bit word.</li><li>The asm text does not hold the end-pointer instruction. On CRB the compiler makes it from a C statement of the kernel function. The test writes it here. Line 189 also adds the <code>ret</code> after the loop.</li><li>Line 187: <code>framed</code> is true when the clobber list names <code>v8</code>.</li><li>Line 188: a framed kernel gets the lines of <code>FRAME</code>, with the end-pointer instruction at the place of <code>END</code>. Any other kernel gets the end-pointer instruction only.</li><li>Line 189 stores per kernel: pad, instructions before the loop, loop, instructions after the loop, operand text.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>synth</code>: write listing text and offsets rows</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">193  def synth(funcs, binary="bwx12", start=0x6000, change=None):
194      """(listing text, offsets rows) of the new kernels; change(kernel, pad, head, loop, tail) may alter one"""
195      text, rows, addr = [], [], start
196      for k, (pad, head, loop, tail, _) in funcs.items():
197          head, loop, tail = list(head), list(loop), list(tail)
198          if change:
199              pad, head, loop, tail = change(k, pad, head, loop, tail)
200          addr = (addr + 63) // 64 * 64 + pad
201          first, loop_at = addr, addr + 4 * len(head)</pre></td><td valign="top">Writes the 26 kernels one after the other. The first address is <code>start</code>, 0x6000 by default (a multiple of 64).<ul><li>Lines 198-199: an optional function <code>change</code> may alter the pad or the instruction lists of a kernel. Step 4 uses it.</li><li>Line 200: the function start is the next multiple of 64 B, plus <code>pad</code>. This is the rule of the <code>PLACE</code> macro [Ref3].</li><li>Line 201: the loop starts after the instructions of <code>head</code>. Each AArch64 instruction is 4 B long.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">202          text.append("=== %s %s ===\n%016x &lt;k_%s&gt;:" % (binary, k, first, k))
203          for t in head + loop + ["b.cc %x &lt;k_%s+0x%x&gt;  // b.lo, b.ul, b.last" % (loop_at, k, loop_at - first)] + tail:
204              op, _, arg = t.partition(" ")
205              text.append("    %x:\t%s\t%s" % (addr, op, arg))
206              addr += 4
207          text.append("")
208          rows.append("%s\t%s\tk_%s\t%x\t%x\t%d" % (binary, k, k, first, loop_at, loop_at % 64))
209      return "\n".join(text) + "\n", "\n".join(rows) + "\n"
210
211</pre></td><td valign="top"><ul><li>Line 202 writes the block title and the function line in the format of <code>listing.txt</code>.</li><li>Lines 203-206 write one line per instruction, with its address. After the loop instructions they write the loop branch as <code>objdump</code> prints it: <code>b.cc</code> to the loop start. <code>b.cc</code> and <code>b.lo</code> are the same instruction.</li><li>Line 208 writes the row of the offsets table: binary, kernel, function, start, loop start, loop start modulo 64.</li><li>The function returns the listing text and the offsets rows.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>test_aarch64_text</code>: the asm text against the checker</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">212  def test_aarch64_text(tmp):
213      try:
214          funcs = aarch64_functions(tmp)
215      except RuntimeError as e:
216          check("AArch64 text: the expanded source has the asm template of every new kernel", False, e)
217          return
218      check("AArch64 text: the expanded source has the asm template of every new kernel", len(funcs) == 26)
219      ref_l = open(os.path.join(REF, "listing.txt")).read().replace("=== bwx11 ", "=== bwx12 ")
220      ref_o = open(os.path.join(REF, "offsets.tsv")).read().replace("bwx11\t", "bwx12\t")</pre></td><td valign="top"><ul><li>Lines 213-218: get the 26 kernels from <code>aarch64_functions</code>. When it stops with one of its three errors (lines 131, 138, 179), one check fails and the function returns. If not, the check passes when 26 kernels were found.</li><li>Lines 219-220 read the listing and the offsets table of the accepted bwx11 build. They change the binary name in them from bwx11 to bwx12. The checker then reads them as the first 29 kernels of a bwx12 build.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">221
222      def result(change=None):
223          l, o = synth(funcs, change=change)
224          lp, op = os.path.join(tmp, "syn-listing.txt"), os.path.join(tmp, "syn-offsets.tsv")
225          open(lp, "w").write(ref_l + l)
226          open(op, "w").write(ref_o + o)
227          return checker([lp, op])
228</pre></td><td valign="top"><code>result</code> builds one checker input and runs the checker.<ul><li>The listing file is the accepted bwx11 listing plus the 26 blocks of <code>synth</code>. The offsets file is built the same way.</li><li>The checker is called without options. Its reference is then the same accepted bwx11 build.</li><li>So the 29 old kernels are compared with a copy of themselves and cannot differ. Only the rules for the 26 new kernels can fail.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">229      r = result()
230      check("AArch64 text: the listing made from the source text passes check_listing12.py (26 new kernels, loop offsets 20, 40, 52)",
231            r.returncode == 0 and "new_kernels=26 new_failed_rows=0" in r.stdout and "kernels=29 failed_rows=0" in r.stdout,
232            "\n".join(l for l in r.stdout.splitlines() if "FAIL" in l)[:1500])</pre></td><td valign="top">Step 3. The unchanged listing must pass: exit status 0, 29 old rows and 26 new rows without a failure. The checker rules for a new kernel are [Ref2]:<ul><li>The loop holds exactly the expected instructions with every operand. For <code>read_nop256</code>: 8 <code>ldp</code>, 256 <code>nop</code>, <code>add</code>, <code>cmp</code>. The loop ends with the branch <code>b.cc</code> to the loop start.</li><li>Before the loop stand only the end pointer, stores of d registers and the expected <code>movi</code> or <code>dup</code>. After the loop stand only loads of d registers, and the last instruction is <code>ret</code>.</li><li>The loop offset is 20 B for a read kernel, 40 B for a write kernel, 52 B for a copy kernel. It equals the loop offset of <code>asmread</code>, <code>asmwrite</code> or <code>asmcopy</code> in the same listing. The row of the offsets table gives the same value.</li><li>The function has one backward branch and no other branch. Each of d8 to d15 that the loop uses is stored before the loop and loaded after it.</li></ul>A pass shows that the asm text and the pads of <code>bwx12.c</code> agree with the checker, if the frame is as assumed.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">233      # clobber lists: every v register of the text is named as a clobber
234      bad = []
235      for k, (_, head, loop, _, operands) in funcs.items():
236          used = {int(n) for t in head + loop for n in re.findall(r"\b[qv](\d+)\b", t)}
237          named = {int(n) for n in re.findall(r'"v(\d+)"', operands)}
238          if not used &lt;= named:
239              bad.append((k, sorted(used - named)))
240      check("AArch64 text: every vector register that a new kernel uses is in its clobber list", not bad, bad)
241</pre></td><td valign="top">Checks the clobber list of each new kernel.<ul><li><code>used</code>: the numbers of all q and v registers in the instructions before the loop and in the loop.</li><li><code>named</code>: the numbers of the v registers in the clobber list.</li><li>The check fails when a used register is not named.</li></ul>gcc does not read the asm text. The vector registers of the text are not operands. So gcc learns only from the clobber list that the text changes them.</td></tr>
<tr><td colspan="2"><b>Step 4: changed copies that the checker must reject</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">242      def one_nop_less(victim):
243          def f(k, pad, head, loop, tail):
244              if k == victim:
245                  loop.remove("nop")
246              return pad, head, loop, tail
247          return f
248</pre></td><td valign="top"><code>one_nop_less(victim)</code> returns a change function for <code>synth</code>. It removes one <code>nop</code> from the loop of the kernel <code>victim</code>. All other kernels stay unchanged.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">249      def other_source(k, pad, head, loop, tail):
250          if k == "read_dadd8":
251              loop[loop.index("add v17.2d, v17.2d, v2.2d")] = "add v17.2d, v17.2d, v24.2d"
252          return pad, head, loop, tail
253</pre></td><td valign="top">In <code>read_dadd8</code>, one add gets the source register v24 in place of v2. The loop loads v2. It does not load v24. The number of instructions stays the same.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">254      def moved(k, pad, head, loop, tail):
255          return (pad + 4 if k == "write_nop96" else pad), head, loop, tail
256</pre></td><td valign="top">Adds 4 B to the pad of <code>write_nop96</code>. The function and its loop start move by 4 B, the length of one instruction. The loop offset becomes 44 B in place of 40 B.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">257      def no_d8(k, pad, head, loop, tail):
258          if k == "read_iadd16":
259              head[0] = "sub sp, sp, #0x40"
260          return pad, head, loop, tail
261</pre></td><td valign="top">In <code>read_iadd16</code>, the first frame instruction is replaced by <code>sub sp, sp, #0x40</code>. The original instruction stores d8 and d9 and moves the stack pointer down by 64 B. The replacement only moves the stack pointer. So d8 and d9 are never stored.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">262      def no_init(k, pad, head, loop, tail):
263          if k == "read_dadd2":
264              head.remove("movi v16.4s, #0x0")
265              pad += 4
266          return pad, head, loop, tail
267</pre></td><td valign="top">In <code>read_dadd2</code>, the instruction <code>movi v16.4s, #0x0</code> is removed.<ul><li>It sets v16 to 0 before the loop. The first add of the loop collects its sum in v16.</li><li>The pad grows by 4 B, so the loop start keeps its address. The loop offset rule can therefore not report this change.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">268      for name, change, kernel in (("one nop less in read_nop256", one_nop_less("read_nop256"), "read_nop256"),
269                                   ("one nop less in copy_nop192", one_nop_less("copy_nop192"), "copy_nop192"),
270                                   ("one nop less in read_sp56", one_nop_less("read_sp56"), "read_sp56"),
271                                   ("an add of read_dadd8 that takes v24 in place of a loaded register", other_source, "read_dadd8"),
272                                   ("the loop of write_nop96 moved by 4 B", moved, "write_nop96"),
273                                   ("read_iadd16 without the store of d8 and d9", no_d8, "read_iadd16"),
274                                   ("read_dadd2 without the movi of v16", no_init, "read_dadd2")):
275          r = result(change)
276          failed = [l.split("\t")[0] for l in r.stdout.splitlines() if "\tFAIL" in l]
277          check("check_listing12.py fails, on this kernel only: %s" % name, r.returncode == 1 and failed == [kernel], failed)
278
279</pre></td><td valign="top">Runs the checker on 7 changed listings, one change per run.<ul><li><code>failed</code>: the kernel names of the checker output rows that contain <code>FAIL</code>.</li><li>A check passes only when the checker ends with status 1 and <code>failed</code> holds exactly the changed kernel.</li><li>So each check proves two things. The checker fails the row of the changed kernel. It fails no other row. The test does not compare the reason that the checker prints.</li><li>The first case is <code>read_nop256</code> with 255 <code>nop</code>. The whole-chip test runs this kernel in part L.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: run the three test functions</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">280  def main():
281      tmp = tempfile.mkdtemp(prefix="bwx12-test-")
282      try:
283          test_source(tmp)
284          test_standin(tmp)
285          test_aarch64_text(tmp)
286      finally:
287          if os.environ.get("KEEP"):
288              print("# kept: %s" % tmp)
289          else:
290              shutil.rmtree(tmp, ignore_errors=True)
291      print("# failed checks: %d" % fails)
292      return 1 if fails else 0
293
294</pre></td><td valign="top"><ul><li>Line 281 creates a new temporary folder. Its name starts with <code>bwx12-test-</code>.</li><li>Lines 283-285 run the three test functions in this order. <code>test_standin</code> needs the files that <code>test_source</code> wrote.</li><li>Lines 286-290 run even when a test function stops with an error. When the environment variable <code>KEEP</code> is set and not empty, the folder is kept and its path is printed. If not, the folder is deleted.</li><li>Lines 291-292 print the number of failed checks. The return value is 1 if a check failed and 0 if not. After an error that no test function handles, these two lines are not run. Python then prints a traceback and ends with status 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">295  if __name__ == "__main__":
296      sys.exit(main())</pre></td><td valign="top">When the file is started as a script, the return value of <code>main</code> becomes the exit status of the process.</td></tr>
</table>

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
