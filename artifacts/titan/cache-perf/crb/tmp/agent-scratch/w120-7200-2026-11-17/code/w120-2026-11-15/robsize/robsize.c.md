# `robsize.c` explained, line by line

- Source file: `w120-2026-11-15/robsize/robsize.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 807 lines, 29021 bytes).
- sha256 of the source when this page was built: `f1fcc8111bae10c5da20ab4349199051e4c8145b70ccc3e663c3194fc757c65e`.

## Short version: purpose

`robsize.c` is the window test program: it measures how many filler instructions of one kind fit in the out-of-order window of one AArch64 core. It writes a loop at run time with two independent loads that miss the caches and N fillers after each load, times the loop for a list of N, and reports the N at which the time per pass steps from about one miss time to about two. The kinds whose name starts with `k_` use one loop body of a read kernel of `bwx12.c` as the unit, so they tell how many loop bodies, and so how many cache lines, one window covers.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **AArch64**: the 64-bit instruction set of Arm.
- **Out-of-order window**: the instructions that a core holds between fetch and retirement. By the README of this folder its size is limited by the reorder buffer, by the free physical registers and by the load queue.
- **Retire**: a core retires an instruction when the instruction and all instructions before it are finished. Only then does the instruction leave the window.
- **Filler**: an instruction placed between the two loads that miss the caches. It does not depend on those loads.
- **Kind**: one sort of filler. The table `kinds` holds 36 of them. The option `--kind` chooses.
- **N, unit**: N is the number of filler units after each of the two loads. For most kinds one unit is one instruction. For `iter256` it is 8 instructions, and for a kernel-body kind it is one whole loop body.
- **Kernel-body kind**: a kind whose name starts with `k_`. One unit of N is one loop body of a benchmark kernel of `bwx12.c`.
- **Chain**: a buffer of pointers that form one random cycle. Each load of a pointer gives the address of the next load, and each such load misses the caches.
- **Template**: an instruction that the assembler encodes at build time. The program copies its 4-byte word into the generated loop.
- **Pass**: one run through the generated loop: load A, N units, load B, N units, the counter step and the branch.
- **Miss time**: the time that one load takes when its data is not in a cache.
- **Scratch buffer**: 512 bytes that stay in the level 1 cache. The filler loads read its first 256 B. Two more cells of it point to themselves and serve the run without misses.
- **Filler cost (`hot_ns`)**: the time per pass of the same generated code when both loads hit the level 1 cache.
- **Plateau**: a flat part of the series of times over N. The low plateau is the mean of the first 3 points, the high plateau the mean of the last 3 points that are used.
- **Step position**: the N at which the series first crosses the midpoint between the two plateaus. The program prints it as `N_at_midpoint`.
- **`cbnz`**: the Arm instruction "compare and branch if not zero". It ends each pass of the generated loop.

## Main flow

1. `main` reads the options and checks them: `--cpu` is required and at most 119, `--reps` is 5 to 64, `--iters` is at least 200000, and every name of `--kind` must be in the table (lines 651 to 699).
2. Check the one change that the program makes to an instruction word: `patch_cbnz` puts the distance -300 into the `cbnz` template, and the result must be equal to the word that the assembler made for the same distance (lines 701 to 707).
3. Pin the program to the CPU of `--cpu` and test that it runs there (lines 709 to 715).
4. Build two pointer chains of `--mb` MiB each. `build_chain` writes every node, shuffles the nodes into one random cycle and turns the node numbers into addresses. Then read how much memory lies on huge pages (lines 717 to 722).
5. Prepare the scratch buffer and the code buffer, and print the head lines of the output (lines 724 to 748).
6. For each selected kind, in the order of the table, and for each N of its list: `emit_loop` writes the loop into the code buffer, and the buffer is made executable (lines 750 to 778).
7. Time the loop two times with `measure`: first without misses, 3 repetitions with the two cells that point to themselves, then with misses, `--reps` repetitions on the two chains. Print one data row for this N (lines 780 to 793).
8. After the last N of a kind, `report_step` finds the step in the series of the medians and in the series of the medians minus the filler cost, and prints one `# step` line for each (lines 795 to 799).

## Behavior a reader must know

- What is timed: one repetition is one call of the generated function with `--iters` passes. The clock `CLOCK_MONOTONIC` is read directly before and directly after the call (lines 540 to 542). The time per pass is the difference divided by the number of passes. The call holds the 7 instructions of the start code and the 5 of the end code once.
- What is not timed: the building of the chains, the writing of the loop, and the two warm-up calls of 20000 passes each (line 781, line 784).
- One pass does two loads of 8 bytes, one from each chain, and each loaded value is used: it is the address of the next load of the same chain. The program computes no byte count and no rate. Its result is ns per pass.
- Placement: the program pins itself to one CPU, and the chains are first written after that. By default the two chains take 2 times 1024 MiB. The program asks for transparent huge pages and prints a warning in its second head line when less than half of the chain memory is on them.
- The data row of an N holds the median and the minimum over the repetitions with misses, and the filler cost as the minimum of 3 repetitions without misses.
- The step search first cuts the series at the first N where the filler cost is above half of the low plateau of the run with misses. With fewer than 8 points left it prints `too few points` and no step position. A warning is added when the high plateau is below 1.4 times the low plateau.
- By the README of this folder, the window between load B and the next load A also holds the counter step and the branch. So the capacity is about the step position plus 2 to 3 instructions.
- The place in the two chains is never set back. Each N and each kind goes on where the one before it ended.
- For a kernel-body kind the unit differs from the real kernel in three points that the comment of lines 203 to 214 lists: the loads hit the level 1 cache, the loop branch is never taken, and the accumulators have no start value.
- Exit statuses: 0 after all kinds. 2 after the help text: an unknown option, an option without a value, a value that is not a whole number, or a CPU number that is missing or below 0. 1 for every other stop: a CPU above 119, a value outside its allowed range, an unknown kind, a failed patch check, a failed system call.
- The output goes to the standard output. Lines that start with `#` are comments. Each data row is written out at once.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/robsize/robsize.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (807 lines, 29021 bytes, sha256 `f1fcc8111bae10c5da20ab4349199051e4c8145b70ccc3e663c3194fc757c65e`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: the method and the generated loop (lines 1 to 39)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/*` | Starts the header comment of the file. |
| 2 | ` * robsize.c - measure how many filler instructions fit in the out-of-order` | Comment: `robsize.c` measures how many filler instructions fit in the out-of-order window of one core. The sentence goes on in line 3. |
| 3 | ` * window of one AArch64 core.` | Comment: the core is one AArch64 core, a core with the 64-bit instruction set of Arm. |
| 4 | ` *` | Comment: an empty line of the comment block. |
| 5 | ` * Method (Henry Wong, "Measuring Reorder Buffer Capacity", 2013):` | Comment: the method comes from Henry Wong, "Measuring Reorder Buffer Capacity", 2013. |
| 6 | ` * each loop iteration does two independent cache-missing loads. N filler` | Comment: each pass of the loop does two independent loads that miss the caches. N filler instructions follow each of them. |
| 7 | ` * instructions follow EACH load. While the fillers fit in the window, the` | Comment: continues line 6. As long as the fillers fit in the window, the two misses overlap. |
| 8 | ` * two misses run at the same time and one iteration costs about one miss.` | Comment: in that case the two misses run at the same time, and one pass costs about the time of one miss. |
| 9 | ` * When the fillers no longer fit, the second load cannot enter the window` | Comment: when the fillers no longer fit, the second load cannot enter the window before the first load has left it. |
| 10 | ` * before the first load retires. The misses then run one after the other,` | Comment: continues line 9. The first load leaves the window when it retires, which is after its data has arrived. So the two misses run one after the other. |
| 11 | ` * and one iteration costs about two misses. The N at that step is the` | Comment: one pass then costs about the time of two misses. The N at which the time steps up is the capacity. The sentence ends in line 12. |
| 12 | ` * capacity for that filler kind.` | Comment: the capacity holds for the filler kind that was measured. |
| 13 | ` *` | Comment: an empty line of the comment block. |
| 14 | ` * Generated loop (x0 = chain A pointer, x1 = chain B pointer,` | Comment: the registers of the generated loop: `x0` holds the pointer of chain A and `x1` the pointer of chain B. |
| 15 | ` * x2 = iteration count, x3 = hot 256 B scratch buffer):` | Comment: `x2` holds the number of passes that remain, and `x3` the address of the hot scratch buffer of 256 B. Hot means that it stays in the level 1 cache. |
| 16 | ` *` | Comment: an empty line of the comment block. |
| 17 | ` *     stp d8..d15 to the stack, x4 = x5 = x6 = 0   (7 instructions, once)` | Comment: the start of the generated code, run once per call: it stores the registers `d8` to `d15` on the stack and sets `x4`, `x5` and `x6` to 0. These are 7 instructions. |
| 18 | ` *   loop:` | Comment: the label of the loop start. |
| 19 | ` *     ldr  x0, [x0]                   load A: cache miss, chain A` | Comment: load A. It loads the next pointer of chain A from the address in `x0` into `x0`. The load misses the caches. |
| 20 | ` *     <N filler units>` | Comment: N filler units follow load A. |
| 21 | ` *     ldr  x1, [x1]                   load B: cache miss, chain B` | Comment: load B, the same for chain B with the register `x1`. |
| 22 | ` *     <N filler units>` | Comment: N filler units follow load B. |
| 23 | ` *     sub  x2, x2, #1` | Comment: the pass counter `x2` goes down by 1. |
| 24 | ` *     cbnz x2, loop` | Comment: `cbnz` branches back to the loop start as long as `x2` is not 0. |
| 25 | ` *     ldp d8..d15 from the stack, ret (5 instructions, once)` | Comment: the end of the generated code, run once per call: it loads `d8` to `d15` back from the stack and returns. These are 5 instructions. |
| 26 | ` *` | Comment: an empty line of the comment block. |
| 27 | ` * No instruction word is encoded by hand. Every instruction is assembled` | Comment: no instruction word is written by hand as a number. The assembler encodes every instruction. |
| 28 | ` * by the assembler in the "templates" block below, and the code generator` | Comment: the instructions stand in the "templates" block below (lines 61 to 201 and lines 236 to 285), and the code generator copies their 4-byte words. |
| 29 | ` * copies the 4-byte words. The only PC-relative copied instruction is the` | Comment: only one copied instruction holds an address relative to its own place. |
| 30 | ` * "b.lo" of the k_* kinds, which branches to the instruction after itself,` | Comment: it is the `b.lo` of the kinds whose name starts with `k_`. It branches to the instruction after itself, so a copy is right at any address. |
| 31 | ` * so a copy is valid at any address. The only word changed at run time is` | Comment: the only word that the program changes at run time is the offset field of the `cbnz` loop branch. |
| 32 | ` * the offset field (bits 23:5) of the "cbnz" loop branch. main() checks` | Comment: that field is the bits 5 to 23 of the word. The function `main` checks the change, as line 33 says. |
| 33 | ` * that patch against an assembler-encoded "cbnz" before any measurement.` | Comment: `main` compares the changed word with a `cbnz` that the assembler encoded, before any measurement (line 702). |
| 34 | ` *` | Comment: an empty line of the comment block. |
| 35 | ` * To review the encodings on the target:  objdump -d robsize \| less` | Comment: to review the encodings on the target machine, print the machine code of the binary with `objdump -d robsize`. |
| 36 | ` * and search for the labels t_nop, t_vadd, ... (all in .text.robtmpl).` | Comment: in that listing, search for the labels `t_nop`, `t_vadd` and so on. All of them lie in the section `.text.robtmpl`. |
| 37 | ` *` | Comment: an empty line of the comment block. |
| 38 | ` * Build: gcc -O2 -o robsize robsize.c        (AArch64 Linux only)` | Comment: the build command, `gcc -O2 -o robsize robsize.c`. The file builds on AArch64 Linux only. |
| 39 | ` */` | Ends the header comment. |

### Headers, target check and CPU limit (lines 40 to 56)

| Line | Source | Explanation |
|---:|---|---|
| 40 | `#define _GNU_SOURCE` | Defines `_GNU_SOURCE` before the headers. It turns on the Linux extensions of the C library that the file uses: `sched_setaffinity` with CPU sets, `sched_getcpu`, `MAP_ANONYMOUS` and `madvise`. |
| 41 | `#include <errno.h>` | Includes `errno.h`: the variable `errno`, the error number of the last failed library call. The functions `die` and `num` use it. |
| 42 | `#include <sched.h>` | Includes `sched.h`: the CPU set type and the functions `sched_setaffinity` and `sched_getcpu`, used in `main` to pin the program. |
| 43 | `#include <stdint.h>` | Includes `stdint.h`: integer types of a fixed size, `uint32_t` for one instruction word and `uint64_t` for one pointer cell. |
| 44 | `#include <stdio.h>` | Includes `stdio.h`: `printf`, `fprintf` and the file functions for the output and for `/proc`. |
| 45 | `#include <stdlib.h>` | Includes `stdlib.h`: `exit`, `malloc`, `qsort`, `strtol` and `posix_memalign`. |
| 46 | `#include <string.h>` | Includes `string.h`: `strcmp`, `strlen`, `memset` and `strerror`. |
| 47 | `#include <sys/mman.h>` | Includes `sys/mman.h`: `mmap`, `mprotect` and `madvise`, used for the chains and for the code buffer. |
| 48 | `#include <time.h>` | Includes `time.h`: `clock_gettime`, the clock of the measurement. |
| 49 | `#include <unistd.h>` | Includes `unistd.h`, the header of the basic POSIX system calls. |
| 51 | `#if !defined(__aarch64__) && !defined(ROBSIZE_SYNTAX_CHECK)` | A check at build time. The condition is true on a machine that is not AArch64, unless the macro `ROBSIZE_SYNTAX_CHECK` is defined. |
| 52 | `#error "robsize.c runs on AArch64 only"` | In that case the build stops with the message `robsize.c runs on AArch64 only`. |
| 53 | `#endif` | Ends the check of line 51. |
| 55 | `#define MAX_CPU 119 /* CPUs above this number are refused */` | `MAX_CPU`: 119, the highest CPU number that the program accepts. `main` refuses a higher number (line 675). This keeps the program on the CPUs 0 to 119 that our runs may use. |

### Templates: the fixed parts of the loop, the patch check and the kind `nop` (lines 57 to 106)

| Line | Source | Explanation |
|---:|---|---|
| 57 | `/* ------------------------------------------------------------------ */` | Comment: a divider line. |
| 58 | `/* Templates: the assembler encodes every instruction used at run time. */` | Comment: the title of the block: templates. The assembler encodes every instruction that the program uses at run time. |
| 59 | `/* ------------------------------------------------------------------ */` | Comment: a divider line. |
| 60 | `#ifdef __aarch64__` | The template block is compiled only on AArch64. With `ROBSIZE_SYNTAX_CHECK` on another machine it is left out. |
| 61 | `__asm__(` | Starts a block of assembler text at file level. The compiler hands the text to the assembler as it stands. The block ends in line 201. |
| 62 | `"    .pushsection .text.robtmpl,\"ax\",%progbits\n"` | `.pushsection` switches to the section `.text.robtmpl` and remembers the section before it. `"ax"` marks the section as loaded and executable. `%progbits` says that it holds bytes of the program. |
| 63 | `"    .balign 4\n"` | `.balign 4` aligns the next byte to a multiple of 4 bytes, the size of one instruction. |
| 64 | `/* skeleton */` | Comment: the next templates are the skeleton, the fixed parts of the generated function. |
| 65 | `"t_prologue:\n" /* v8..v15 low halves are callee-saved (AAPCS64) */` | The label `t_prologue` marks the first word of the start code. Comment: the low halves of the vector registers `v8` to `v15` (named `d8` to `d15`) must be kept by a called function. `AAPCS64` is the calling convention of AArch64. |
| 66 | `"    stp d8, d9, [sp, #-64]!\n"` | `stp d8, d9, [sp, #-64]!` first lowers the stack pointer by 64 bytes and then stores the two 8-byte registers `d8` and `d9` at the new address. So it reserves 64 bytes of stack and fills the first 16. |
| 67 | `"    stp d10, d11, [sp, #16]\n"` | Stores `d10` and `d11` at the stack pointer plus 16. |
| 68 | `"    stp d12, d13, [sp, #32]\n"` | Stores `d12` and `d13` at the stack pointer plus 32. |
| 69 | `"    stp d14, d15, [sp, #48]\n"` | Stores `d14` and `d15` at the stack pointer plus 48. |
| 70 | `/* x4, x5, x6 = 0 for the kernel-body kinds (k_*): "cmp x4, x5" then always` | Comment: `x4`, `x5` and `x6` are set to 0 for the kernel-body kinds, the kinds whose name starts with `k_`. The loop end of such a kind holds `cmp x4, x5`. |
| 71 | ` * gives "not lower", so their "b.lo" is never taken */` | Comment: continues line 70. With `x5` equal to 0 the compare never gives "lower". So the `b.lo` of these kinds is never taken. |
| 72 | `"    mov x4, #0\n"` | `mov x4, #0` sets the register `x4` to 0. |
| 73 | `"    mov x5, #0\n"` | Sets `x5` to 0. |
| 74 | `"    mov x6, #0\n"` | Sets `x6` to 0. |
| 75 | `"t_prologue_end:\n"` | The label `t_prologue_end` marks the end of the start code. The words between the two labels are the 7 instructions that are copied. |
| 76 | `"t_load_a:\n"` | The label `t_load_a` marks load A. |
| 77 | `"    ldr x0, [x0]\n"` | `ldr x0, [x0]` loads 8 bytes from the address in `x0` into `x0`. The loaded value is the address of the next node of chain A. So each load depends on the load before it in the same chain, and not on chain B. |
| 78 | `"t_load_a_end:\n"` | The label `t_load_a_end` marks the end of load A. |
| 79 | `"t_load_b:\n"` | The label `t_load_b` marks load B. |
| 80 | `"    ldr x1, [x1]\n"` | `ldr x1, [x1]` loads 8 bytes from the address in `x1` into `x1`: the next node of chain B. |
| 81 | `"t_load_b_end:\n"` | The label `t_load_b_end` marks the end of load B. |
| 82 | `"t_dec:\n"` | The label `t_dec` marks the counter step. |
| 83 | `"    sub x2, x2, #1\n"` | `sub x2, x2, #1` lowers the pass counter `x2` by 1. |
| 84 | `"t_dec_end:\n"` | The label `t_dec_end` marks the end of the counter step. |
| 85 | `"t_cbnz0:\n" /* offset field = 0; patched at run time */` | The label `t_cbnz0` marks the template of the loop branch. Comment: its offset field is 0, and the program patches it at run time. |
| 86 | `"    cbnz x2, t_cbnz0\n"` | `cbnz x2, t_cbnz0` branches when `x2` is not 0. Here the target is the instruction itself, so the assembler writes the offset 0. The function `patch_cbnz` later puts in the real distance to the loop start. |
| 87 | `"t_cbnz0_end:\n"` | The label `t_cbnz0_end` marks the end of that template. |
| 88 | `"t_epilogue:\n"` | The label `t_epilogue` marks the end code of the generated function. |
| 89 | `"    ldp d10, d11, [sp, #16]\n"` | `ldp d10, d11, [sp, #16]` loads the two registers back from the stack pointer plus 16. |
| 90 | `"    ldp d12, d13, [sp, #32]\n"` | Loads `d12` and `d13` back from the stack pointer plus 32. |
| 91 | `"    ldp d14, d15, [sp, #48]\n"` | Loads `d14` and `d15` back from the stack pointer plus 48. |
| 92 | `"    ldp d8, d9, [sp], #64\n"` | `ldp d8, d9, [sp], #64` loads `d8` and `d9` from the stack pointer and then raises the stack pointer by 64 bytes. This frees the stack space of line 66. |
| 93 | `"    ret\n"` | `ret` returns to the caller. The two chain pointers are still in `x0` and `x1`, and the caller gets them as the return value. |
| 94 | `"t_epilogue_end:\n"` | The label `t_epilogue_end` marks the end of the end code. |
| 95 | `/* reference for the cbnz patch check: branch back by 300 instructions */` | Comment: the next lines are a reference for the check of the branch patch: a `cbnz` that branches back by 300 instructions. |
| 96 | `"t_chk_target:\n"` | The label `t_chk_target` marks the target of the reference branch. |
| 97 | `"    .rept 300\n"` | `.rept 300` starts a block that the assembler repeats 300 times. |
| 98 | `"    nop\n"` | The repeated line: one `nop`, an instruction that does nothing. |
| 99 | `"    .endr\n"` | `.endr` ends the repeated block. So 300 `nop` instructions stand here. |
| 100 | `"t_chk_cbnz:\n"` | The label `t_chk_cbnz` marks the reference branch. |
| 101 | `"    cbnz x2, t_chk_target\n"` | `cbnz x2, t_chk_target` is a branch to the label 300 instructions before it. The assembler encodes the offset -300 into this word. No code runs this instruction: `main` only reads the word (line 702). |
| 102 | `"t_chk_cbnz_end:\n"` | The label `t_chk_cbnz_end` marks the end of the reference branch. |
| 103 | `/* filler kind: nop */` | Comment: the filler kind `nop`. |
| 104 | `"t_nop:\n"` | The label `t_nop` marks the template of the kind `nop`. |
| 105 | `"    nop\n"` | One `nop`. It does no work, but the core must keep it in the window until it retires. |
| 106 | `"t_nop_end:\n"` | The label `t_nop_end` marks the end of the template. |

### Templates: the other seven plain filler kinds (lines 107 to 202)

| Line | Source | Explanation |
|---:|---|---|
| 107 | `/* filler kind: vadd - NEON add, 16 accumulators v16..v31, source v0 */` | Comment: the filler kind `vadd`: an add of the NEON vector unit, with the 16 accumulator registers `v16` to `v31` and the source register `v0`. |
| 108 | `"t_vadd:\n"` | The label `t_vadd` marks the template of the kind `vadd`, 16 instructions. |
| 109 | `"    add v16.2d, v16.2d, v0.2d\n"` | `add v16.2d, v16.2d, v0.2d` adds the two 64-bit lanes of `v0` to the two 64-bit lanes of `v16` and writes the result to `v16`. So the instruction writes a vector register, and it must wait for the add before it that wrote `v16`. |
| 110 | `"    add v17.2d, v17.2d, v0.2d\n"` | The same add into the accumulator `v17`. |
| 111 | `"    add v18.2d, v18.2d, v0.2d\n"` | The same add into the accumulator `v18`. |
| 112 | `"    add v19.2d, v19.2d, v0.2d\n"` | The same add into the accumulator `v19`. |
| 113 | `"    add v20.2d, v20.2d, v0.2d\n"` | The same add into the accumulator `v20`. |
| 114 | `"    add v21.2d, v21.2d, v0.2d\n"` | The same add into the accumulator `v21`. |
| 115 | `"    add v22.2d, v22.2d, v0.2d\n"` | The same add into the accumulator `v22`. |
| 116 | `"    add v23.2d, v23.2d, v0.2d\n"` | The same add into the accumulator `v23`. |
| 117 | `"    add v24.2d, v24.2d, v0.2d\n"` | The same add into the accumulator `v24`. |
| 118 | `"    add v25.2d, v25.2d, v0.2d\n"` | The same add into the accumulator `v25`. |
| 119 | `"    add v26.2d, v26.2d, v0.2d\n"` | The same add into the accumulator `v26`. |
| 120 | `"    add v27.2d, v27.2d, v0.2d\n"` | The same add into the accumulator `v27`. |
| 121 | `"    add v28.2d, v28.2d, v0.2d\n"` | The same add into the accumulator `v28`. |
| 122 | `"    add v29.2d, v29.2d, v0.2d\n"` | The same add into the accumulator `v29`. |
| 123 | `"    add v30.2d, v30.2d, v0.2d\n"` | The same add into the accumulator `v30`. |
| 124 | `"    add v31.2d, v31.2d, v0.2d\n"` | The same add into the accumulator `v31`. |
| 125 | `"t_vadd_end:\n"` | The label `t_vadd_end` marks the end of the template. |
| 126 | `/* filler kind: vadd_nd - NEON add with no dependency between fillers:` | Comment: the filler kind `vadd_nd`: a NEON add with no dependency between the fillers. |
| 127 | ` * destinations v16..v31, sources v0 and v1 are never written */` | Comment: continues line 126. The destinations are `v16` to `v31`. The sources `v0` and `v1` are never written. |
| 128 | `"t_vadd_nd:\n"` | The label `t_vadd_nd` marks the template of the kind `vadd_nd`, 16 instructions. |
| 129 | `"    add v16.2d, v0.2d, v1.2d\n"` | `add v16.2d, v0.2d, v1.2d` adds the lanes of `v0` and `v1` and writes the result to `v16`. It writes the same register as line 109, but it reads no register that a filler writes. So no add waits for another add. |
| 130 | `"    add v17.2d, v0.2d, v1.2d\n"` | The same add with the destination `v17`. |
| 131 | `"    add v18.2d, v0.2d, v1.2d\n"` | The same add with the destination `v18`. |
| 132 | `"    add v19.2d, v0.2d, v1.2d\n"` | The same add with the destination `v19`. |
| 133 | `"    add v20.2d, v0.2d, v1.2d\n"` | The same add with the destination `v20`. |
| 134 | `"    add v21.2d, v0.2d, v1.2d\n"` | The same add with the destination `v21`. |
| 135 | `"    add v22.2d, v0.2d, v1.2d\n"` | The same add with the destination `v22`. |
| 136 | `"    add v23.2d, v0.2d, v1.2d\n"` | The same add with the destination `v23`. |
| 137 | `"    add v24.2d, v0.2d, v1.2d\n"` | The same add with the destination `v24`. |
| 138 | `"    add v25.2d, v0.2d, v1.2d\n"` | The same add with the destination `v25`. |
| 139 | `"    add v26.2d, v0.2d, v1.2d\n"` | The same add with the destination `v26`. |
| 140 | `"    add v27.2d, v0.2d, v1.2d\n"` | The same add with the destination `v27`. |
| 141 | `"    add v28.2d, v0.2d, v1.2d\n"` | The same add with the destination `v28`. |
| 142 | `"    add v29.2d, v0.2d, v1.2d\n"` | The same add with the destination `v29`. |
| 143 | `"    add v30.2d, v0.2d, v1.2d\n"` | The same add with the destination `v30`. |
| 144 | `"    add v31.2d, v0.2d, v1.2d\n"` | The same add with the destination `v31`. |
| 145 | `"t_vadd_nd_end:\n"` | The label `t_vadd_nd_end` marks the end of the template. |
| 146 | `/* filler kind: iadd - integer add, 14 accumulators x4..x17, source x3 */` | Comment: the filler kind `iadd`: an integer add, with the 14 accumulator registers `x4` to `x17` and the source register `x3`. |
| 147 | `"t_iadd:\n"` | The label `t_iadd` marks the template of the kind `iadd`, 14 instructions. |
| 148 | `"    add x4, x4, x3\n"` | `add x4, x4, x3` adds the 64-bit register `x3` to `x4` and writes the result to `x4`. It writes an integer register, and it must wait for the add before it that wrote `x4`. `x3` holds the address of the scratch buffer, which no filler changes. |
| 149 | `"    add x5, x5, x3\n"` | The same add into the accumulator `x5`. |
| 150 | `"    add x6, x6, x3\n"` | The same add into the accumulator `x6`. |
| 151 | `"    add x7, x7, x3\n"` | The same add into the accumulator `x7`. |
| 152 | `"    add x8, x8, x3\n"` | The same add into the accumulator `x8`. |
| 153 | `"    add x9, x9, x3\n"` | The same add into the accumulator `x9`. |
| 154 | `"    add x10, x10, x3\n"` | The same add into the accumulator `x10`. |
| 155 | `"    add x11, x11, x3\n"` | The same add into the accumulator `x11`. |
| 156 | `"    add x12, x12, x3\n"` | The same add into the accumulator `x12`. |
| 157 | `"    add x13, x13, x3\n"` | The same add into the accumulator `x13`. |
| 158 | `"    add x14, x14, x3\n"` | The same add into the accumulator `x14`. |
| 159 | `"    add x15, x15, x3\n"` | The same add into the accumulator `x15`. |
| 160 | `"    add x16, x16, x3\n"` | The same add into the accumulator `x16`. |
| 161 | `"    add x17, x17, x3\n"` | The same add into the accumulator `x17`. |
| 162 | `"t_iadd_end:\n"` | The label `t_iadd_end` marks the end of the template. |
| 163 | `/* filler kind: iadd_nd - integer add with no dependency between fillers:` | Comment: the filler kind `iadd_nd`: an integer add with no dependency between the fillers. |
| 164 | ` * destinations x4..x17, source x3 is never written */` | Comment: continues line 163. The destinations are `x4` to `x17`. The source `x3` is never written. |
| 165 | `"t_iadd_nd:\n"` | The label `t_iadd_nd` marks the template of the kind `iadd_nd`, 14 instructions. |
| 166 | `"    add x4, x3, x3\n"` | `add x4, x3, x3` adds `x3` to itself and writes the result to `x4`. It writes the same register as line 148, but it reads only `x3`. So no add waits for another add. |
| 167 | `"    add x5, x3, x3\n"` | The same add with the destination `x5`. |
| 168 | `"    add x6, x3, x3\n"` | The same add with the destination `x6`. |
| 169 | `"    add x7, x3, x3\n"` | The same add with the destination `x7`. |
| 170 | `"    add x8, x3, x3\n"` | The same add with the destination `x8`. |
| 171 | `"    add x9, x3, x3\n"` | The same add with the destination `x9`. |
| 172 | `"    add x10, x3, x3\n"` | The same add with the destination `x10`. |
| 173 | `"    add x11, x3, x3\n"` | The same add with the destination `x11`. |
| 174 | `"    add x12, x3, x3\n"` | The same add with the destination `x12`. |
| 175 | `"    add x13, x3, x3\n"` | The same add with the destination `x13`. |
| 176 | `"    add x14, x3, x3\n"` | The same add with the destination `x14`. |
| 177 | `"    add x15, x3, x3\n"` | The same add with the destination `x15`. |
| 178 | `"    add x16, x3, x3\n"` | The same add with the destination `x16`. |
| 179 | `"    add x17, x3, x3\n"` | The same add with the destination `x17`. |
| 180 | `"t_iadd_nd_end:\n"` | The label `t_iadd_nd_end` marks the end of the template. |
| 181 | `/* filler kind: ldrq - one 16-byte load of the hot scratch buffer */` | Comment: the filler kind `ldrq`: one load of 16 bytes from the hot scratch buffer. |
| 182 | `"t_ldrq:\n"` | The label `t_ldrq` marks the template of the kind `ldrq`. |
| 183 | `"    ldr q16, [x3]\n"` | `ldr q16, [x3]` loads 16 bytes from the address in `x3` into the vector register `q16`. The address is the scratch buffer, so the load hits the level 1 cache. The value is not used. |
| 184 | `"t_ldrq_end:\n"` | The label `t_ldrq_end` marks the end of the template. |
| 185 | `/* filler kind: ldpq - one 32-byte pair load of the hot scratch buffer */` | Comment: the filler kind `ldpq`: one pair load of 32 bytes from the hot scratch buffer. |
| 186 | `"t_ldpq:\n"` | The label `t_ldpq` marks the template of the kind `ldpq`. |
| 187 | `"    ldp q16, q17, [x3]\n"` | `ldp q16, q17, [x3]` loads 32 bytes from the address in `x3` into the two vector registers `q16` and `q17`. So one instruction writes two vector registers. The values are not used. |
| 188 | `"t_ldpq_end:\n"` | The label `t_ldpq_end` marks the end of the template. |
| 189 | `/* filler kind: iter256 - the benchmark body, 8 pair loads = 256 bytes */` | Comment: the filler kind `iter256`: the body of the benchmark, 8 pair loads, which is 256 bytes. |
| 190 | `"t_iter256:\n"` | The label `t_iter256` marks the template of the kind `iter256`, 8 instructions. |
| 191 | `"    ldp q0, q1, [x3]\n"` | `ldp q0, q1, [x3]` loads the bytes 0 to 31 of the scratch buffer into `q0` and `q1`. |
| 192 | `"    ldp q2, q3, [x3, #32]\n"` | Loads the bytes 32 to 63 into `q2` and `q3`. |
| 193 | `"    ldp q4, q5, [x3, #64]\n"` | Loads the bytes 64 to 95 into `q4` and `q5`. |
| 194 | `"    ldp q6, q7, [x3, #96]\n"` | Loads the bytes 96 to 127 into `q6` and `q7`. |
| 195 | `"    ldp q8, q9, [x3, #128]\n"` | Loads the bytes 128 to 159 into `q8` and `q9`. |
| 196 | `"    ldp q10, q11, [x3, #160]\n"` | Loads the bytes 160 to 191 into `q10` and `q11`. |
| 197 | `"    ldp q12, q13, [x3, #192]\n"` | Loads the bytes 192 to 223 into `q12` and `q13`. |
| 198 | `"    ldp q14, q15, [x3, #224]\n"` | Loads the bytes 224 to 255 into `q14` and `q15`. These 8 loads are the loads of one pass of the read kernel `asmread`, but all from the same hot 256 B. No value is used. |
| 199 | `"t_iter256_end:\n"` | The label `t_iter256_end` marks the end of the template. |
| 200 | `"    .popsection\n"` | `.popsection` goes back to the section that was active before line 62. |
| 201 | `);` | Ends the block of assembler text that began in line 61. |

### Templates: the kernel-body kinds (lines 203 to 287)

| Line | Source | Explanation |
|---:|---|---|
| 203 | `/*` | Starts a comment block on the kernel-body kinds. |
| 204 | ` * Kernel-body kinds (k_*): ONE unit is one loop body of a benchmark kernel` | Comment: for a kind whose name starts with `k_`, one unit of N is one loop body of a benchmark kernel. |
| 205 | ` * of bwx12.c, in the instruction order of that kernel. Differences from the` | Comment: the kernel is one of `bwx12.c`, and the instructions keep the order of that kernel. The templates differ from the kernel in three points. |
| 206 | ` * kernel, all needed by this harness:` | Comment: all three differences are needed by this test program. |
| 207 | ` *   - the loads and prefetches read the hot scratch buffer [x3], not [x4],` | Comment: difference 1: the loads and the prefetches read the hot scratch buffer at the address in `x3`, not the address in `x4`. |
| 208 | ` *     so they all hit L1 and do not depend on the pointer add;` | Comment: continues line 207. So all of them hit the level 1 cache, and none depends on the add of the pointer. |
| 209 | ` *   - the loop end "add x4,x4,#B; cmp x4,x5; b.lo" is kept, but the branch` | Comment: difference 2: the loop end `add x4,x4,#B`, `cmp x4,x5`, `b.lo` is kept. |
| 210 | ` *     goes to the next instruction and is never taken (x5 = 0);` | Comment: continues line 209. The branch goes to the next instruction and is never taken: `x5` is 0. |
| 211 | ` *   - the accumulators v16-v31 are not initialized (integer adds, so the` | Comment: difference 3: the accumulators `v16` to `v31` are not set to a start value. |
| 212 | ` *     values do not change the timing).` | Comment: continues line 211. The adds are integer adds, so the values do not change the timing. |
| 213 | ` * "b.lo 1f" is PC-relative with offset +4, so a copy is valid anywhere.` | Comment: `b.lo 1f` holds the offset +4 relative to its own address. So a copy of it is right at any address. |
| 214 | ` */` | Ends the comment block. |
| 215 | `#define KT(name, body) "t_" #name ":\n" body "t_" #name "_end:\n"` | `KT(name, body)`: a macro that builds the text of one template: the label `t_` with the name, the body, and the end label `t_` with the name and `_end`. `#name` turns the macro argument into text. |
| 216 | `#define LDP4 \` | `LDP4`: a macro for four pair loads. The text goes on in the next four lines. |
| 217 | `    "ldp q0, q1, [x3]\n" \` | `ldp q0, q1, [x3]` loads the bytes 0 to 31 of the scratch buffer into `q0` and `q1`. |
| 218 | `    "ldp q2, q3, [x3, #32]\n" \` | Loads the bytes 32 to 63 into `q2` and `q3`. |
| 219 | `    "ldp q4, q5, [x3, #64]\n" \` | Loads the bytes 64 to 95 into `q4` and `q5`. |
| 220 | `    "ldp q6, q7, [x3, #96]\n"` | Loads the bytes 96 to 127 into `q6` and `q7`. So `LDP4` stands for the 4 loads of 128 B. |
| 221 | `#define LDP8 LDP4 \` | `LDP8`: a macro for eight pair loads: the four of `LDP4` and four more. |
| 222 | `    "ldp q8, q9, [x3, #128]\n" \` | Loads the bytes 128 to 159 into `q8` and `q9`. |
| 223 | `    "ldp q10, q11, [x3, #160]\n" \` | Loads the bytes 160 to 191 into `q10` and `q11`. |
| 224 | `    "ldp q12, q13, [x3, #192]\n" \` | Loads the bytes 192 to 223 into `q12` and `q13`. |
| 225 | `    "ldp q14, q15, [x3, #224]\n"` | Loads the bytes 224 to 255 into `q14` and `q15`. So `LDP8` stands for the 8 loads of 256 B. |
| 226 | `#define LDR4 \` | `LDR4`: a macro for four single loads of 16 bytes, one per 64 B line. |
| 227 | `    "ldr q0, [x3]\n" \` | `ldr q0, [x3]` loads the bytes 0 to 15 of the scratch buffer into `q0`. |
| 228 | `    "ldr q1, [x3, #64]\n" \` | Loads the bytes 64 to 79 into `q1`. |
| 229 | `    "ldr q2, [x3, #128]\n" \` | Loads the bytes 128 to 143 into `q2`. |
| 230 | `    "ldr q3, [x3, #192]\n"` | Loads the bytes 192 to 207 into `q3`. |
| 231 | `#define NOPS(n) ".rept " #n "\nnop\n.endr\n"` | `NOPS(n)`: a macro for `n` `nop` instructions, written as a block that the assembler repeats `n` times. |
| 232 | `#define TAIL(bytes) "add x4, x4, #" #bytes "\ncmp x4, x5\nb.lo 1f\n1:\n"` | `TAIL(bytes)`: a macro for the loop end of a kernel. `add x4, x4, #bytes` adds the block size to `x4`, which stands for the pointer of the kernel. `cmp x4, x5` compares it with `x5`, which stands for the end pointer. `b.lo 1f` branches to the label `1` when `x4` is lower. The label stands directly after the branch, so the next instruction is the same in both cases. |
| 233 | `#define VADD(a, b) "add v" #a ".2d, v" #a ".2d, v" #b ".2d\n"` | `VADD(a, b)`: a macro for one vector add: it adds the two 64-bit lanes of the register `v` with the number `b` to the register `v` with the number `a`. |
| 234 | `#define K_NOP(n) KT(k_nop##n, LDP8 NOPS(n) TAIL(256))` | `K_NOP(n)`: a macro for the template `k_nop` with the number `n`: 8 pair loads, `n` `nop` instructions and the loop end for 256 B. `##` joins `k_nop` and the number to one name. |
| 235 | `#define K_SP(n) KT(k_sp##n, LDP4 NOPS(n) TAIL(128))` | `K_SP(n)`: a macro for the template `k_sp` with the number `n`: 4 pair loads, `n` `nop` instructions and the loop end for 128 B. |
| 236 | `__asm__(` | Starts the second block of assembler text at file level. It ends in line 285. |
| 237 | `"    .pushsection .text.robtmpl,\"ax\",%progbits\n"` | `.pushsection` switches to the section `.text.robtmpl`, as in line 62. |
| 238 | `"    .balign 4\n"` | `.balign 4` aligns the next byte to a multiple of 4 bytes. |
| 239 | `/* read_nopN: 8 ldp, N nop, add, cmp, b.lo */` | Comment: the templates for the kernels `read_nop` with a number: 8 `ldp`, N `nop`, `add`, `cmp`, `b.lo`. |
| 240 | `K_NOP(32) K_NOP(48) K_NOP(56) K_NOP(64) K_NOP(72) K_NOP(80) K_NOP(88)` | Seven templates, `k_nop32`, `k_nop48`, `k_nop56`, `k_nop64`, `k_nop72`, `k_nop80` and `k_nop88`. Each one is the loop body of the read kernel with that many `nop` instructions. |
| 241 | `K_NOP(96) K_NOP(112) K_NOP(128) K_NOP(160) K_NOP(192) K_NOP(256)` | Six more templates of the same form: `k_nop96`, `k_nop112`, `k_nop128`, `k_nop160`, `k_nop192` and `k_nop256`. |
| 242 | `/* read_daddK: 8 ldp, K adds that take loaded registers */` | Comment: the templates for the kernels `read_dadd` with a number: 8 `ldp` and K adds that take loaded registers. |
| 243 | `KT(k_dadd2, LDP8 VADD(16, 0) VADD(17, 8) TAIL(256))` | Template `k_dadd2`: 8 pair loads, then 2 vector adds (`v0` into `v16`, `v8` into `v17`), then the loop end for 256 B. Each add reads a register that a load of the same body wrote. |
| 244 | `KT(k_dadd4, LDP8 VADD(16, 0) VADD(17, 4) VADD(18, 8) VADD(19, 12) TAIL(256))` | Template `k_dadd4`: 8 pair loads, then 4 vector adds (`v0`, `v4`, `v8` and `v12` into `v16` to `v19`), then the loop end. |
| 245 | `KT(k_dadd8, LDP8` | Starts the template `k_dadd8`: 8 pair loads. |
| 246 | `   VADD(16, 0) VADD(17, 2) VADD(18, 4) VADD(19, 6)` | Continues `k_dadd8`: 4 vector adds, `v0`, `v2`, `v4` and `v6` into `v16` to `v19`. |
| 247 | `   VADD(20, 8) VADD(21, 10) VADD(22, 12) VADD(23, 14) TAIL(256))` | Ends `k_dadd8`: 4 more adds, `v8`, `v10`, `v12` and `v14` into `v20` to `v23`, then the loop end for 256 B. |
| 248 | `KT(k_dadd16, LDP8` | Starts the template `k_dadd16`: 8 pair loads. |
| 249 | `   VADD(16, 0) VADD(17, 1) VADD(18, 2) VADD(19, 3)` | Continues `k_dadd16`: 4 vector adds, `v0` to `v3` into `v16` to `v19`. |
| 250 | `   VADD(20, 4) VADD(21, 5) VADD(22, 6) VADD(23, 7)` | Continues `k_dadd16`: 4 adds, `v4` to `v7` into `v20` to `v23`. |
| 251 | `   VADD(16, 8) VADD(17, 9) VADD(18, 10) VADD(19, 11)` | Continues `k_dadd16`: 4 adds, `v8` to `v11` into `v16` to `v19` a second time. |
| 252 | `   VADD(20, 12) VADD(21, 13) VADD(22, 14) VADD(23, 15) TAIL(256))` | Ends `k_dadd16`: 4 adds, `v12` to `v15` into `v20` to `v23` a second time, then the loop end. So all 16 loaded registers are used, two per accumulator. |
| 253 | `/* read_iadd16: 8 ldp, 16 adds that take no loaded register */` | Comment: the template for the kernel `read_iadd16`: 8 `ldp` and 16 adds that take no loaded register. |
| 254 | `KT(k_iadd16, LDP8` | Starts the template `k_iadd16`: 8 pair loads. |
| 255 | `   VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27)` | Continues `k_iadd16`: 4 vector adds, `v24` to `v27` into `v16` to `v19`. The registers `v24` to `v31` are not written by a load. |
| 256 | `   VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31)` | Continues `k_iadd16`: 4 adds, `v28` to `v31` into `v20` to `v23`. |
| 257 | `   VADD(16, 24) VADD(17, 25) VADD(18, 26) VADD(19, 27)` | Continues `k_iadd16`: the 4 adds of line 255 a second time. |
| 258 | `   VADD(20, 28) VADD(21, 29) VADD(22, 30) VADD(23, 31) TAIL(256))` | Ends `k_iadd16`: the 4 adds of line 256 a second time, then the loop end for 256 B. |
| 259 | `/* oldread, 128 B per unit, order of the compiler listing: ldp, counter add,` | Comment: the template for `oldread`, with 128 B per unit. It keeps the order of the compiler listing: one `ldp`, the add of a counter, 3 `ldp`, the add of the pointer. |
| 260 | ` * 3 ldp, pointer add, 8 adds (one loaded register each), cmp, branch.` | Comment: continues line 259: then 8 adds, each with one loaded register, then the compare and the branch. |
| 261 | ` * 16 instructions, as the listing has. */` | Comment: these are 16 instructions, as the listing has. |
| 262 | `KT(k_old,` | Starts the template `k_old`. |
| 263 | `   "ldp q0, q1, [x3]\n"` | `k_old`: the first pair load, the bytes 0 to 31 of the scratch buffer into `q0` and `q1`. |
| 264 | `   "add x6, x6, #1\n"` | `k_old`: `add x6, x6, #1` adds 1 to `x6`, which stands for the counter of the old read loop. |
| 265 | `   "ldp q2, q3, [x3, #32]\n"` | `k_old`: the second pair load, the bytes 32 to 63. |
| 266 | `   "ldp q4, q5, [x3, #64]\n"` | `k_old`: the third pair load, the bytes 64 to 95. |
| 267 | `   "ldp q6, q7, [x3, #96]\n"` | `k_old`: the fourth pair load, the bytes 96 to 127. |
| 268 | `   "add x4, x4, #128\n"` | `k_old`: `add x4, x4, #128` adds 128 to `x4`, which stands for the pointer. |
| 269 | `   VADD(16, 0) VADD(17, 1) VADD(18, 2) VADD(19, 3)` | `k_old`: 4 vector adds, the loaded registers `v0` to `v3` into the accumulators `v16` to `v19`. |
| 270 | `   VADD(20, 4) VADD(21, 5) VADD(22, 6) VADD(23, 7)` | `k_old`: 4 more vector adds, `v4` to `v7` into `v20` to `v23`. So each of the 8 loaded registers is added once. |
| 271 | `   "cmp x4, x5\nb.lo 1f\n1:\n")` | Ends `k_old`: `cmp x4, x5` and `b.lo 1f` with its label, the loop end without the pointer add. |
| 272 | `/* read_sparse and read_spN: 4 ldp, N nop, add, cmp, b.lo per 128 B */` | Comment: the templates for `read_sparse` and the kernels `read_sp` with a number: 4 `ldp`, N `nop`, `add`, `cmp`, `b.lo` per 128 B. |
| 273 | `K_SP(9) K_SP(24) K_SP(32) K_SP(40) K_SP(48) K_SP(56)` | Six templates, `k_sp9`, `k_sp24`, `k_sp32`, `k_sp40`, `k_sp48` and `k_sp56`: 4 pair loads, that many `nop` instructions, and the loop end for 128 B. |
| 274 | `/* read_1pl: one 16 B load per 64 B line, 256 B per unit */` | Comment: the template for `read_1pl`: one load of 16 B per 64 B line, 256 B per unit. |
| 275 | `KT(k_1pl, LDR4 TAIL(256))` | Template `k_1pl`: the four single loads of `LDR4` and the loop end for 256 B. |
| 276 | `KT(k_1pl_nop96, LDR4 NOPS(96) TAIL(256))` | Template `k_1pl_nop96`: the four single loads, 96 `nop` instructions and the loop end for 256 B. |
| 277 | `/* read_pf2048: 8 ldp, 4 prefetches. Here the prefetches name the hot` | Comment: the template for `read_pf2048`: 8 `ldp` and 4 prefetches. Here the prefetches name the lines of the hot scratch buffer. |
| 278 | ` * scratch lines, so they take a slot and do not miss. */` | Comment: continues line 277. So each prefetch takes a slot in the core and does not miss. |
| 279 | `KT(k_pf2048, LDP8` | Starts the template `k_pf2048`: 8 pair loads. |
| 280 | `   "prfm pldl1keep, [x3]\n"` | `k_pf2048`: `prfm pldl1keep, [x3]` asks the core to bring the line at the address in `x3` into the level 1 data cache. It loads no data into a register. |
| 281 | `   "prfm pldl1keep, [x3, #64]\n"` | `k_pf2048`: the same prefetch for the line at offset 64. |
| 282 | `   "prfm pldl1keep, [x3, #128]\n"` | `k_pf2048`: the same prefetch for the line at offset 128. |
| 283 | `   "prfm pldl1keep, [x3, #192]\n" TAIL(256))` | Ends `k_pf2048`: the prefetch for the line at offset 192, then the loop end for 256 B. |
| 284 | `"    .popsection\n"` | `.popsection` goes back to the section that was active before line 237. |
| 285 | `);` | Ends the second block of assembler text. |
| 286 | `#endif` | Ends the `#ifdef` of line 60. |

### Declarations of the template labels (lines 288 to 320)

| Line | Source | Explanation |
|---:|---|---|
| 288 | `#define TMPL(name)                                                         \` | `TMPL(name)`: a macro that declares the two labels of one template for the C code. The text goes on in the next two lines. |
| 289 | `    extern const uint32_t name[] __attribute__((visibility("hidden")));    \` | The start label as an array of 32-bit words, one word per instruction. `extern` says that the array is defined elsewhere, here by the assembler text. `visibility("hidden")` says that the label lies inside this program. |
| 290 | `    extern const uint32_t name##_end[] __attribute__((visibility("hidden")))` | The end label, the name with `_end`, in the same way. The number of instructions of a template is the end label minus the start label. |
| 292 | `TMPL(t_prologue);` | Declares the labels of the start code, `t_prologue` and `t_prologue_end`. |
| 293 | `TMPL(t_load_a);` | Declares the labels of load A. |
| 294 | `TMPL(t_load_b);` | Declares the labels of load B. |
| 295 | `TMPL(t_dec);` | Declares the labels of the counter step. |
| 296 | `TMPL(t_cbnz0);` | Declares the labels of the loop branch with the offset 0. |
| 297 | `TMPL(t_epilogue);` | Declares the labels of the end code. |
| 298 | `TMPL(t_chk_cbnz);` | Declares the labels of the reference branch for the patch check. |
| 299 | `TMPL(t_nop);` | Declares the labels of the kind `nop`. |
| 300 | `TMPL(t_vadd);` | Declares the labels of the kind `vadd`. |
| 301 | `TMPL(t_vadd_nd);` | Declares the labels of the kind `vadd_nd`. |
| 302 | `TMPL(t_iadd);` | Declares the labels of the kind `iadd`. |
| 303 | `TMPL(t_iadd_nd);` | Declares the labels of the kind `iadd_nd`. |
| 304 | `TMPL(t_ldrq);` | Declares the labels of the kind `ldrq`. |
| 305 | `TMPL(t_ldpq);` | Declares the labels of the kind `ldpq`. |
| 306 | `TMPL(t_iter256);` | Declares the labels of the kind `iter256`. |
| 307 | `#define KERNEL_KINDS(X) \` | `KERNEL_KINDS(X)`: a macro that lists all 28 kernel-body kinds. Each entry calls the macro `X` with the name of the kind and its largest default N. The list is used two times with two different `X`: in line 318 and in line 355. |
| 308 | `    X(k_nop32, 16) X(k_nop48, 16) X(k_nop56, 16) X(k_nop64, 16) \` | Entries `k_nop32`, `k_nop48`, `k_nop56` and `k_nop64`, each with the largest N 16. |
| 309 | `    X(k_nop72, 16) X(k_nop80, 16) X(k_nop88, 16) X(k_nop96, 16) \` | Entries `k_nop72`, `k_nop80`, `k_nop88` and `k_nop96`, each with the largest N 16. |
| 310 | `    X(k_nop112, 16) X(k_nop128, 16) X(k_nop160, 12) X(k_nop192, 12) \` | Entries `k_nop112` and `k_nop128` with the largest N 16, `k_nop160` and `k_nop192` with 12. |
| 311 | `    X(k_nop256, 12) \` | Entry `k_nop256` with the largest N 12. |
| 312 | `    X(k_dadd2, 16) X(k_dadd4, 16) X(k_dadd8, 16) X(k_dadd16, 16) \` | Entries `k_dadd2`, `k_dadd4`, `k_dadd8` and `k_dadd16`, each with the largest N 16. |
| 313 | `    X(k_iadd16, 16) X(k_old, 24) \` | Entries `k_iadd16` with the largest N 16 and `k_old` with 24. |
| 314 | `    X(k_sp9, 30) X(k_sp24, 30) X(k_sp32, 30) X(k_sp40, 30) X(k_sp48, 30) \` | Entries `k_sp9`, `k_sp24`, `k_sp32`, `k_sp40` and `k_sp48`, each with the largest N 30. |
| 315 | `    X(k_sp56, 30) \` | Entry `k_sp56` with the largest N 30. |
| 316 | `    X(k_1pl, 60) X(k_1pl_nop96, 16) X(k_pf2048, 16)` | Entries `k_1pl` with the largest N 60, `k_1pl_nop96` and `k_pf2048` with 16. The list ends here. |
| 317 | `#define X(name, nmax) TMPL(t_##name);` | Defines `X` for the first use: one `TMPL` declaration for the template `t_` with the name. The largest N is not used here. |
| 318 | `KERNEL_KINDS(X)` | Expands the list. So the labels of all 28 kernel-body templates are declared. |
| 319 | `#undef X` | Removes this definition of `X`. |

### The table of kinds and its two helpers (lines 321 to 381)

| Line | Source | Explanation |
|---:|---|---|
| 321 | `/*` | Starts a comment block. |
| 322 | ` * One filler kind.` | Comment: the next type describes one filler kind. |
| 323 | ` * unit: instructions emitted per count of N. 0 means the whole template` | Comment: the field `unit` is the number of instructions that are emitted per count of N. The value 0 means the whole template. |
| 324 | ` * (see kunit()).` | Comment: the function `kunit` resolves that value 0. |
| 325 | ` * The i-th emitted instruction is tmpl[i % period].` | Comment: the instruction number i that is emitted is the template word with the index i modulo the length of the template. |
| 326 | ` */` | Ends the comment block. |
| 327 | `struct kind {` | Starts the type `struct kind`, one row of the table of kinds. |
| 328 | `    const char *name;` | `name`: the name of the kind, as the option `--kind` takes it. |
| 329 | `    const uint32_t *tmpl, *tmpl_end;` | `tmpl` and `tmpl_end`: the first word of the template and the place after its last word. |
| 330 | `    long unit;` | `unit`: the number of instructions per count of N, or 0 for the whole template. |
| 331 | `    long nmin, nmax, nstep; /* default list of N */` | `nmin`, `nmax`, `nstep`: the default list of N for this kind: the first value, the last value and the step. |
| 332 | `    const char *what;` | `what`: a short description, printed in the output and in the usage text. |
| 333 | `};` | Ends the type. |
| 335 | `static const struct kind kinds[] = {` | Starts the table `kinds`. The first 8 rows are the plain kinds, in which N counts single instructions or, for `iter256`, groups of 8. |
| 336 | `    { "nop",     t_nop,     t_nop_end,     1, 0, 1200, 10,` | Row `nop`: the template of lines 104 to 106, 1 instruction per N, N from 0 to 1200 in steps of 10. |
| 337 | `      "nop (reorder-buffer entries)" },` | The description of `nop`: by the text it measures entries of the reorder buffer. |
| 338 | `    { "vadd",    t_vadd,    t_vadd_end,    1, 0, 600, 5,` | Row `vadd`: the template of lines 108 to 125, 1 instruction per N, N from 0 to 600 in steps of 5. |
| 339 | `      "add vA.2d,vA.2d,v0.2d, 16 accumulators (free vector registers)" },` | The description of `vadd`: 16 accumulators, and by the text it measures free vector registers. |
| 340 | `    { "iadd",    t_iadd,    t_iadd_end,    1, 0, 1200, 10,` | Row `iadd`: the template of lines 147 to 162, 1 instruction per N, N from 0 to 1200 in steps of 10. |
| 341 | `      "add xA,xA,x3, 14 accumulators (free integer registers)" },` | The description of `iadd`: 14 accumulators, and by the text it measures free integer registers. |
| 342 | `    { "ldrq",    t_ldrq,    t_ldrq_end,    1, 0, 600, 5,` | Row `ldrq`: the template of lines 182 to 184, 1 instruction per N, N from 0 to 600 in steps of 5. |
| 343 | `      "ldr q16,[x3] (load-queue entries or vector registers)" },` | The description of `ldrq`: by the text it measures entries of the load queue or vector registers. |
| 344 | `    { "ldpq",    t_ldpq,    t_ldpq_end,    1, 0, 300, 2,` | Row `ldpq`: the template of lines 186 to 188, 1 instruction per N, N from 0 to 300 in steps of 2. |
| 345 | `      "ldp q16,q17,[x3] (2 vector register writes each)" },` | The description of `ldpq`: each instruction writes 2 vector registers. |
| 346 | `    { "iter256", t_iter256, t_iter256_end, 8, 0, 60, 1,` | Row `iter256`: the template of lines 190 to 199, 8 instructions per N, N from 0 to 60 in steps of 1. |
| 347 | `      "8 x ldp q0..q15 = one 256 B benchmark iteration per N" },` | The description of `iter256`: 8 pair loads, one 256 B pass of the benchmark per N. |
| 348 | `    { "vadd_nd", t_vadd_nd, t_vadd_nd_end, 1, 0, 600, 5,` | Row `vadd_nd`: the template of lines 128 to 145, 1 instruction per N, N from 0 to 600 in steps of 5. |
| 349 | `      "add vA.2d,v0.2d,v1.2d, no dependency chain (control for vadd)" },` | The description of `vadd_nd`: no dependency chain, the control for `vadd`. |
| 350 | `    { "iadd_nd", t_iadd_nd, t_iadd_nd_end, 1, 0, 1200, 10,` | Row `iadd_nd`: the template of lines 165 to 180, 1 instruction per N, N from 0 to 1200 in steps of 10. |
| 351 | `      "add xA,x3,x3, no dependency chain (control for iadd)" },` | The description of `iadd_nd`: no dependency chain, the control for `iadd`. |
| 352 | `#define X(name, nmax) \` | Defines `X` for the second use of the list: one table row per kernel-body kind. The text goes on in the next two lines. |
| 353 | `    { #name, t_##name, t_##name##_end, 0, 0, nmax, 1, \` | The row: the name as text, the two labels of the template, `unit` 0 (the whole template per N), N from 0 to the largest N of the list entry in steps of 1. |
| 354 | `      "one loop body of the benchmark kernel per N, loads from hot scratch" },` | The description of every kernel-body kind: one loop body of the benchmark kernel per N, with loads from the hot scratch buffer. |
| 355 | `    KERNEL_KINDS(X)` | Expands the list. So the table gets 28 more rows, 36 in all. |
| 356 | `#undef X` | Removes this definition of `X`. |
| 357 | `};` | Ends the table `kinds`. |
| 358 | `#define NKINDS ((int)(sizeof kinds / sizeof kinds[0]))` | `NKINDS`: the number of rows of the table, computed as the size of the table divided by the size of one row. |
| 360 | `/* Instructions per count of N. */` | Comment: the next function gives the instructions per count of N. |
| 361 | `static long kunit(const struct kind *k)` | Starts the function `kunit`. |
| 362 | `{` | Opens the body of `kunit`. |
| 363 | `    return k->unit ? k->unit : (long)(k->tmpl_end - k->tmpl);` | Returns the field `unit` when it is not 0. When it is 0, it returns the length of the template in words: the end label minus the start label. |
| 364 | `}` | Ends the function `kunit`. |
| 366 | ``/* Is `name` "all" or one entry of the comma-separated list `list`? */`` | Comment: the next function answers whether `name` is selected: the list is the word `all`, or `name` is one entry of the list with commas. |
| 367 | `static int kind_selected(const char *list, const char *name)` | Starts the function `kind_selected`. `list` is the text of the option `--kind`. |
| 368 | `{` | Opens the body of `kind_selected`. |
| 369 | `    size_t len = strlen(name);` | `len`: the length of the name. |
| 370 | `    if (!strcmp(list, "all"))` | Tests whether the list is exactly the word `all`. `strcmp` returns 0 for equal texts. |
| 371 | `        return 1;` | In that case every kind is selected: returns 1. |
| 372 | `    for (const char *p = list; *p;) {` | Starts the loop over the entries of the list. `p` points to the start of an entry. The loop ends at the end of the text. |
| 373 | `        const char *e = strchr(p, ',');` | `e`: the place of the next comma, or a null pointer when no comma follows. |
| 374 | `        size_t l = e ? (size_t)(e - p) : strlen(p);` | `l`: the length of this entry: up to the comma, or up to the end of the text. |
| 375 | `        if (l == len && !strncmp(p, name, len))` | Tests whether the entry has the same length as the name and the same characters. |
| 376 | `            return 1;` | In that case the kind is selected: returns 1. |
| 377 | `        p += l + (e != NULL);` | Moves `p` to the next entry: past the entry and, when there was one, past the comma. |
| 378 | `    }` | Ends the loop of line 372. |
| 379 | `    return 0;` | No entry was equal to the name: returns 0. |
| 380 | `}` | Ends the function `kind_selected`. |

### Small helpers: error exit, clock and random numbers (lines 382 to 412)

| Line | Source | Explanation |
|---:|---|---|
| 382 | `/* ------------------------------------------------------------------ */` | Comment: a divider line. |
| 384 | `static void die(const char *msg)` | Starts the function `die`. It ends the program after a failed system call. |
| 385 | `{` | Opens the body of `die`. |
| 386 | `    fprintf(stderr, "robsize: %s: %s\n", msg, strerror(errno));` | Prints `robsize:`, the message and the reason that the system gave (`strerror(errno)`) to the error output. |
| 387 | `    exit(1);` | Ends the program with exit status 1. |
| 388 | `}` | Ends the function `die`. |
| 390 | `static void fail(const char *msg)` | Starts the function `fail`. It ends the program after an error that has no system reason. |
| 391 | `{` | Opens the body of `fail`. |
| 392 | `    fprintf(stderr, "robsize: %s\n", msg);` | Prints `robsize:` and the message to the error output. |
| 393 | `    exit(1);` | Ends the program with exit status 1. |
| 394 | `}` | Ends the function `fail`. |
| 396 | `static double now_ns(void)` | Starts the function `now_ns`. It returns the time of this moment in ns. This is the only clock of the measurement. |
| 397 | `{` | Opens the body of `now_ns`. |
| 398 | `    struct timespec ts;` | `ts`: a time value with a field for seconds and a field for ns. |
| 399 | `    clock_gettime(CLOCK_MONOTONIC, &ts);` | Reads the clock `CLOCK_MONOTONIC`. This clock never jumps back. |
| 400 | `    return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;` | Returns the seconds times 1e9 plus the ns, as a floating point number. |
| 401 | `}` | Ends the function `now_ns`. |
| 403 | `static uint64_t rng_state;` | `rng_state`: the state of the random number generator, one 64-bit number. |
| 405 | `static uint64_t rng(void) /* xorshift64* */` | Starts the function `rng`. It returns the next random 64-bit number. The comment names the method, `xorshift64*`. |
| 406 | `{` | Opens the body of `rng`. |
| 407 | `    rng_state ^= rng_state >> 12;` | Mixes the state with itself, shifted right by 12 bits (`^=` is the exclusive or). |
| 408 | `    rng_state ^= rng_state << 25;` | Mixes the state with itself, shifted left by 25 bits. |
| 409 | `    rng_state ^= rng_state >> 27;` | Mixes the state with itself, shifted right by 27 bits. |
| 410 | `    return rng_state * 0x2545F4914F6CDD1DULL;` | Returns the state times a fixed odd number. The same start state always gives the same sequence. |
| 411 | `}` | Ends the function `rng`. |

### Functions `build_chain` and `anon_huge_kb`: the two pointer chains (lines 413 to 464)

| Line | Source | Explanation |
|---:|---|---|
| 413 | `/*` | Starts a comment block on the function `build_chain`. |
| 414 | `` * Build one pointer chain: `bytes` of memory, one 8-byte pointer every`` | Comment: the function builds one pointer chain in `bytes` of memory, with one pointer of 8 bytes at the start of every `stride` bytes. |
| 415 | `` * `stride` bytes. The pointers form ONE random cycle through all nodes`` | Comment: continues line 414. The pointers form one random cycle through all nodes. |
| 416 | ` * (Sattolo's shuffle), so a chase never repeats a node before it has` | Comment: the method is the shuffle of Sattolo. So a chase never comes back to a node before it has visited all nodes. |
| 417 | ` * visited all of them. Returns the address of node 0.` | Comment: continues line 416. The function returns the address of node 0. |
| 418 | ` */` | Ends the comment block. |
| 419 | `static uint64_t build_chain(size_t bytes, size_t stride, uint64_t seed)` | Starts the function `build_chain`. `bytes` is the size of the chain, `stride` the distance between two nodes in bytes, `seed` the start value of the random numbers. |
| 420 | `{` | Opens the body of `build_chain`. |
| 421 | `    const size_t huge = 2UL << 20;` | `huge`: 2 MiB, the size of a huge page (`2UL << 20` is 2 times `2^20`). |
| 422 | `    char *raw = mmap(NULL, bytes + huge, PROT_READ \| PROT_WRITE,` | `mmap` asks Linux for `bytes + huge` bytes of new memory. The extra 2 MiB make it possible to move the start to a 2 MiB boundary. `PROT_READ \| PROT_WRITE`: the program may read and write the memory. |
| 423 | `                     MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | Continues the call of line 422. `MAP_PRIVATE \| MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here. |
| 424 | `    if (raw == MAP_FAILED)` | Tests whether `mmap` failed. |
| 425 | `        die("mmap chain");` | On failure: `die` prints `mmap chain` with the reason and ends the program with exit status 1. |
| 426 | `    char *p = (char *)(((uintptr_t)raw + huge - 1) & ~(huge - 1));` | `p`: the start of the chain, `raw` rounded up to the next multiple of 2 MiB. The expression adds `huge - 1` and then clears the low 21 bits. |
| 427 | `    if (madvise(p, bytes, MADV_HUGEPAGE) != 0)` | `madvise` with `MADV_HUGEPAGE` asks Linux to use transparent huge pages for the chain. By the warning text of lines 743 to 744, a chain that is not on huge pages adds a walk of the page tables to every miss. A return value other than 0 means that the call failed. |
| 428 | `        fprintf(stderr, "robsize: warning: madvise(MADV_HUGEPAGE): %s\n",` | On failure: prints a warning with the reason to the error output. The program goes on. |
| 429 | `                strerror(errno));` | Continues the call of line 428: the reason text of the system. |
| 431 | `    size_t n = bytes / stride;` | `n`: the number of nodes, `bytes` divided by `stride`. With the defaults (1024 MiB, 64 B) these are 16777216 nodes, one per 64 B cache line. |
| 432 | `    if (n < 2)` | Tests whether the chain has fewer than 2 nodes. |
| 433 | `        fail("chain needs at least 2 nodes");` | In that case `fail` prints `chain needs at least 2 nodes` and ends the program. |
| 434 | `#define NODE(i) (*(uint64_t *)(p + (size_t)(i) * stride))` | `NODE(i)`: a macro for the 8-byte cell of node number `i`, at the address `p` plus `i` times `stride`. |
| 435 | `    for (size_t i = 0; i < n; i++)` | Starts a loop over all nodes. |
| 436 | `        NODE(i) = i;` | Writes into each node its own number. This is the first write to the memory of the chain. Linux assigns the pages at this moment, after `main` has pinned the program (line 712). |
| 437 | `    rng_state = seed;` | Sets the state of the random number generator to `seed`. So the same seed always gives the same chain. |
| 438 | `    for (size_t i = n - 1; i >= 1; i--) { /* Sattolo: j in [0, i) */` | Starts the shuffle: a loop from the last node down to node 1. Comment: in the method of Sattolo the index `j` is taken from 0 up to, but not including, `i`. |
| 439 | `        size_t j = (size_t)(((__uint128_t)rng() * i) >> 64);` | `j`: a random index below `i`. The 64-bit random number is multiplied by `i` in 128-bit arithmetic, and the upper 64 bits of the product are the result. |
| 440 | `        uint64_t t = NODE(i);` | Starts the swap of the cells `i` and `j`: `t` keeps the value of cell `i`. |
| 441 | `        NODE(i) = NODE(j);` | Cell `i` gets the value of cell `j`. |
| 442 | `        NODE(j) = t;` | Cell `j` gets the kept value. After the loop the cells hold a permutation of the node numbers that is one single cycle. |
| 443 | `    }` | Ends the loop of line 438. |
| 444 | `    for (size_t i = 0; i < n; i++)` | Starts a second loop over all nodes. |
| 445 | `        NODE(i) = (uint64_t)(uintptr_t)(p + NODE(i) * stride);` | Replaces the number in each cell by the address of the node with that number. So each cell now holds a pointer to another node, and a load of the cell gives the address of the next load. |
| 446 | `#undef NODE` | Removes the macro `NODE`. |
| 447 | `    return (uint64_t)(uintptr_t)p;` | Returns the address of node 0, the start of the chase. |
| 448 | `}` | Ends the function `build_chain`. |
| 450 | `/* Sum of AnonHugePages over the process, in kB; -1 when unreadable. */` | Comment: the next function gives the sum of `AnonHugePages` over the whole process in kB, or -1 when it cannot be read. `AnonHugePages` is the memory of the process that lies on transparent huge pages. |
| 451 | `static long anon_huge_kb(void)` | Starts the function `anon_huge_kb`. |
| 452 | `{` | Opens the body of `anon_huge_kb`. |
| 453 | `    FILE *f = fopen("/proc/self/smaps_rollup", "r");` | Opens the file `/proc/self/smaps_rollup`, in which Linux sums the memory figures of the process. |
| 454 | `    char line[256];` | `line`: a buffer for one text line. |
| 455 | `    long kb = -1;` | `kb`: the result, -1 until a value is found. |
| 456 | `    if (!f)` | Tests whether the file could not be opened. |
| 457 | `        return -1;` | In that case returns -1. |
| 458 | `    while (fgets(line, sizeof line, f))` | Starts a loop over the lines of the file. |
| 459 | `        if (sscanf(line, "AnonHugePages: %ld kB", &kb) == 1)` | Tests whether the line has the form `AnonHugePages:`, a number and `kB`. `sscanf` then stores the number in `kb` and returns 1. |
| 460 | `            break;` | Leaves the loop at the first such line. |
| 461 | `    fclose(f);` | Closes the file. |
| 462 | `    return kb;` | Returns the number of kB, or -1. |
| 463 | `}` | Ends the function `anon_huge_kb`. |

### Code generation: the loop for one kind and one N (lines 465 to 519)

| Line | Source | Explanation |
|---:|---|---|
| 465 | `/* ------------------------------------------------------------------ */` | Comment: a divider line. |
| 466 | `/* Code generation                                                     */` | Comment: the title of the block: code generation. |
| 467 | `/* ------------------------------------------------------------------ */` | Comment: a divider line. |
| 469 | `typedef struct {` | Starts the type `pair_t`. |
| 470 | `    uint64_t a, b;` | `a`, `b`: two 64-bit values, the pointers of chain A and of chain B. |
| 471 | `} pair_t; /* returned in x0, x1 (AAPCS64) */` | Ends the type. Comment: a function returns such a pair in the registers `x0` and `x1`, by the calling convention `AAPCS64`. |
| 473 | `typedef pair_t (*loop_fn)(uint64_t a, uint64_t b, uint64_t iters,` | Starts the type `loop_fn`: a pointer to a generated loop function. It takes the two chain pointers and the number of passes, which arrive in `x0`, `x1` and `x2`. |
| 474 | `                          void *scratch);` | Continues line 473: the fourth argument is the address of the scratch buffer, which arrives in `x3`. The function returns a `pair_t`: the two chain pointers after the last pass. |
| 476 | `/* Put a branch offset, counted in instructions, into bits 23:5 (imm19). */` | Comment: the next function puts a branch offset, counted in instructions, into the bits 5 to 23 of a word. The field has the name `imm19` and 19 bits. |
| 477 | `static uint32_t patch_cbnz(uint32_t word, long off_words)` | Starts the function `patch_cbnz`. `word` is the `cbnz` template and `off_words` the distance to the target in instructions. A negative value branches back. |
| 478 | `{` | Opens the body of `patch_cbnz`. |
| 479 | `    if (off_words < -(1L << 18) \|\| off_words >= (1L << 18))` | Tests whether the distance fits into 19 bits with a sign: from -262144 up to 262143 instructions. |
| 480 | `        fail("loop body too long for cbnz (limit 1 MiB)");` | If not, `fail` ends the program with the message that the loop body is too long. 262144 instructions of 4 bytes are 1 MiB. |
| 481 | `    return (word & ~(0x7FFFFu << 5)) \|` | Returns the word with a new offset field. `word & ~(0x7FFFFu << 5)` clears the bits 5 to 23. |
| 482 | `           (((uint32_t)off_words & 0x7FFFFu) << 5);` | Continues line 481: the low 19 bits of the distance are shifted to the bits 5 to 23 and put in with an or. |
| 483 | `}` | Ends the function `patch_cbnz`. |
| 485 | `static uint32_t *copy_words(uint32_t *p, const uint32_t *from,` | Starts the function `copy_words`. It copies the instruction words from `from` up to `end` to the place `p`. |
| 486 | `                            const uint32_t *end)` | Continues line 485: the third parameter, the end of the source. |
| 487 | `{` | Opens the body of `copy_words`. |
| 488 | `    while (from < end)` | Loops as long as words remain. |
| 489 | `        *p++ = *from++;` | Copies one 32-bit word and moves both pointers by one word. |
| 490 | `    return p;` | Returns the place after the last word written, where the next piece of code goes. |
| 491 | `}` | Ends the function `copy_words`. |
| 493 | `static uint32_t *emit_fillers(uint32_t *p, const struct kind *k, long n)` | Starts the function `emit_fillers`. It writes one filler block for the kind `k` and the count `n` to the place `p`. |
| 494 | `{` | Opens the body of `emit_fillers`. |
| 495 | `    long period = k->tmpl_end - k->tmpl;` | `period`: the length of the template in instructions. |
| 496 | `    for (long i = 0; i < n * kunit(k); i++)` | Loops over the instructions of the block. Their number is `n` times the instructions per N of the kind (`kunit`). |
| 497 | `        *p++ = k->tmpl[i % period];` | Writes the template word with the index `i` modulo `period`. So a template of 16 instructions starts again from its first word after its last word: the filler number 0 is its first word, the filler number 16 its first word again. |
| 498 | `    return p;` | Returns the place after the block. |
| 499 | `}` | Ends the function `emit_fillers`. |
| 501 | `#define CODE_BYTES (4UL << 20)` | `CODE_BYTES`: the size of the code buffer, 4 MiB. |
| 503 | `/* Write the loop for (kind, n) into code[]. code[] must be writable. */` | Comment: the next function writes the loop for one kind and one N into the buffer `code`, which must be writable at that time. |
| 504 | `static void emit_loop(uint32_t *code, const struct kind *k, long n)` | Starts the function `emit_loop`. |
| 505 | `{` | Opens the body of `emit_loop`. |
| 506 | `    if ((unsigned long)(n * kunit(k)) * 8 + 256 > CODE_BYTES)` | A size check. The loop holds two filler blocks, so each filler instruction needs 8 bytes. 256 bytes more are counted for the fixed parts. The sum must fit into the code buffer. |
| 507 | `        fail("N too large for the code buffer");` | If not, `fail` ends the program with the message `N too large for the code buffer`. |
| 508 | `    uint32_t *p = copy_words(code, t_prologue, t_prologue_end);` | Copies the start code (7 instructions) to the start of the buffer. `p` points behind it. |
| 509 | `    uint32_t *loop = p;` | `loop`: the address of the loop start, the target of the loop branch. |
| 510 | `    p = copy_words(p, t_load_a, t_load_a_end);` | Copies load A. |
| 511 | `    p = emit_fillers(p, k, n);` | Writes the first filler block: N units after load A. |
| 512 | `    p = copy_words(p, t_load_b, t_load_b_end);` | Copies load B. |
| 513 | `    p = emit_fillers(p, k, n);` | Writes the second filler block: N units after load B. |
| 514 | `    p = copy_words(p, t_dec, t_dec_end);` | Copies the counter step. |
| 515 | `    *p = patch_cbnz(t_cbnz0[0], loop - p);` | Writes the loop branch. `loop - p` is the distance from this word back to the loop start in instructions, a negative number. `patch_cbnz` puts it into the template word. |
| 516 | `    p++;` | Moves `p` behind the branch. |
| 517 | `    p = copy_words(p, t_epilogue, t_epilogue_end);` | Copies the end code (5 instructions). The generated function is complete. |
| 518 | `}` | Ends the function `emit_loop`. |

### Measurement: the timed call (lines 520 to 549)

| Line | Source | Explanation |
|---:|---|---|
| 520 | `/* ------------------------------------------------------------------ */` | Comment: a divider line. |
| 521 | `/* Measurement                                                         */` | Comment: the title of the block: measurement. |
| 522 | `/* ------------------------------------------------------------------ */` | Comment: a divider line. |
| 524 | `static int cmp_double(const void *x, const void *y)` | Starts the function `cmp_double`, the compare function that `qsort` needs for numbers of the type `double`. |
| 525 | `{` | Opens the body of `cmp_double`. |
| 526 | `    double a = *(const double *)x, b = *(const double *)y;` | `a`, `b`: the two numbers behind the two pointers. |
| 527 | `    return (a > b) - (a < b);` | Returns 1 when `a` is larger, -1 when `a` is smaller, and 0 when they are equal. |
| 528 | `}` | Ends the function `cmp_double`. |
| 530 | `/*` | Starts a comment block on the function `measure`. |
| 531 | `` * Run `reps` repetitions of `iters` iterations. The chase position is`` | Comment: the function runs `reps` repetitions of `iters` passes each. The place in the chase is kept between the repetitions. |
| 532 | ` * carried from one repetition to the next, so no repetition re-reads` | Comment: continues line 531: one repetition starts where the one before it ended. |
| 533 | ` * lines that an earlier one left in the cache.` | Comment: so no repetition reads lines again that an earlier repetition left in the cache. |
| 534 | ` */` | Ends the comment block. |
| 535 | `static void measure(loop_fn fn, pair_t *pos, void *scratch, uint64_t iters,` | Starts the function `measure`. `fn` is the generated loop, `pos` the place in the two chains, `scratch` the scratch buffer, `iters` the passes per repetition. |
| 536 | `                    int reps, double *median, double *min)` | Continues line 535: `reps` is the number of repetitions. The results go to `median` and `min`. |
| 537 | `{` | Opens the body of `measure`. |
| 538 | `    double t[64];` | `t`: the time per pass of each repetition, at most 64 values. `main` allows at most 64 repetitions (line 680). |
| 539 | `    for (int r = 0; r < reps; r++) {` | Starts the loop over the repetitions. |
| 540 | `        double t0 = now_ns();` | `t0`: the clock reading directly before the call. This starts the timed interval. |
| 541 | `        *pos = fn(pos->a, pos->b, iters, scratch);` | Calls the generated loop for `iters` passes, from the place `pos`. The loop returns the place at which it ended, and `pos` takes it. So the next call goes on from there. |
| 542 | `        t[r] = (now_ns() - t0) / (double)iters;` | Reads the clock again, which ends the timed interval. The time per pass is the difference of the two readings divided by `iters`, in ns. The interval holds the whole call: the start code, all passes and the end code. No clock is read inside the loop. |
| 543 | `    }` | Ends the loop of line 539. |
| 544 | `    qsort(t, reps, sizeof t[0], cmp_double);` | Sorts the times per pass in rising order. |
| 545 | `    *min = t[0];` | `min`: the smallest time per pass of the repetitions. |
| 546 | `    *median = (reps & 1) ? t[reps / 2]` | `median`: for an odd number of repetitions, the middle value of the sorted list. |
| 547 | `                         : 0.5 * (t[reps / 2 - 1] + t[reps / 2]);` | Continues line 546: for an even number, the mean of the two middle values. |
| 548 | `}` | Ends the function `measure`. |

### Function `report_step`: find the step in one series (lines 550 to 610)

| Line | Source | Explanation |
|---:|---|---|
| 550 | `/*` | Starts a comment block on the function `report_step`. |
| 551 | ` * Find the step in one series t[] over n[].` | Comment: the function finds the step in one series of times `t` over the values `n`. |
| 552 | ` * The series is cut at the first point where the fillers alone (hot[])` | Comment: the series is first cut. The cut is at the first point where the fillers alone (the series `hot`) cost more than a limit. The sentence ends in line 553. |
| 553 | ` * cost more than half of the low plateau of the miss run (miss_lo).` | Comment: the limit is half of the low plateau of the run with misses (`miss_lo`). |
| 554 | ` * Beyond that point the time grows with the filler cost, not with the` | Comment: behind that point the time grows with the cost of the fillers, not with the window. |
| 555 | ` * window, so those points must not define the high plateau.` | Comment: continues line 554. So those points must not define the high plateau. |
| 556 | ` * Low plateau = mean of the first 3 points, high plateau = mean of the` | Comment: the low plateau is the mean of the first 3 points. The high plateau is the mean of 3 points too, as line 557 says. |
| 557 | ` * last 3 points before the cut. The step position is the N where t first crosses the` | Comment: these are the last 3 points before the cut. The step position is the N at which `t` first crosses the midpoint. The sentence ends in line 558. |
| 558 | ` * midpoint, with linear interpolation between the two neighbours.` | Comment: the position between two measured N is found with a straight line between the two neighbours. |
| 559 | ` * The largest rise between two neighbours is printed as a second` | Comment: the largest rise between two neighbours is printed as a second estimate. The sentence ends in line 560. |
| 560 | ` * estimate that does not depend on the plateaus.` | Comment: this second estimate does not depend on the plateaus. |
| 561 | ` */` | Ends the comment block. |
| 562 | `static void report_step(const char *kind, const char *series, const long *n,` | Starts the function `report_step`. `kind` and `series` are names for the output. `n` holds the N values. |
| 563 | `                        const double *t, const double *hot, double miss_lo,` | Continues line 562: `t` is the series in which the step is searched, `hot` the cost of the fillers alone per N, `miss_lo` the low plateau of the run with misses, all in ns. |
| 564 | `                        int cnt)` | Continues line 562: `cnt` is the number of points. |
| 565 | `{` | Opens the body of `report_step`. |
| 566 | `    int full = cnt;` | `full`: the number of points before the cut. |
| 567 | `    for (int i = 0; i < full; i++)` | Starts the search for the cut: a loop over all points. |
| 568 | `        if (hot[i] > 0.5 * miss_lo) {` | Tests whether the fillers alone cost more than half of `miss_lo` at this point. |
| 569 | `            cnt = i;` | In that case the series ends before this point: `cnt` becomes its index. |
| 570 | `            break;` | Leaves the loop at the first such point. |
| 571 | `        }` | Ends the `if` of line 568. |
| 572 | `    if (cnt < full)` | Tests whether the series was cut. |
| 573 | `        printf("# cut,%s,%s,series cut at N=%ld: filler cost %.2f ns > "` | Prints a comment line that starts with `# cut`: the kind, the series name, the N at which the series was cut, the filler cost there in ns, and the low plateau in ns. |
| 574 | `               "0.5 x low plateau %.2f ns\n", kind, series, n[cnt], hot[cnt],` | Continues the call of line 573: the rest of the text and the first values. |
| 575 | `               miss_lo);` | Continues the call of line 573: the last value, `miss_lo`. |
| 576 | `    if (cnt < 8) {` | Tests whether fewer than 8 points remain. |
| 577 | `        printf("# step,%s,%s,too few points (%d, need 8)\n", kind, series,` | In that case prints a comment line that starts with `# step` and says `too few points`, with the number of points and the needed number 8. |
| 578 | `               cnt);` | Continues the call of line 577: the last value, `cnt`. |
| 579 | `        return;` | Returns without a step position. |
| 580 | `    }` | Ends the `if` of line 576. |
| 581 | `    double lo = (t[0] + t[1] + t[2]) / 3.0;` | `lo`: the low plateau of this series, the mean of its first 3 points, in ns per pass. |
| 582 | `    double hi = (t[cnt - 1] + t[cnt - 2] + t[cnt - 3]) / 3.0;` | `hi`: the high plateau, the mean of the last 3 points before the cut. |
| 583 | `    double mid = 0.5 * (lo + hi);` | `mid`: the midpoint, the mean of `lo` and `hi`. |
| 584 | `    int jump = 1;` | `jump`: the index of the point with the largest rise from its left neighbour. It starts at point 1. |
| 585 | `    for (int i = 2; i < cnt; i++)` | Starts a loop over the points from index 2 on. |
| 586 | `        if (t[i] - t[i - 1] > t[jump] - t[jump - 1])` | Tests whether the rise from the point before to this point is larger than the largest rise so far. |
| 587 | `            jump = i;` | In that case this point becomes `jump`. |
| 588 | `    double cross = -1.0;` | `cross`: the N at which the series crosses the midpoint. -1 means that it was not found. |
| 589 | `    for (int i = 1; i < cnt; i++)` | Starts a loop over the points from index 1 on. |
| 590 | `        if (t[i - 1] < mid && t[i] >= mid) {` | Tests whether the point before lies below the midpoint and this point at or above it. This is the first crossing from below. |
| 591 | `            cross = (double)n[i - 1] + (double)(n[i] - n[i - 1]) *` | Computes `cross` on the straight line between the two points: the N of the point before, plus a part of the distance to this N. The statement goes on in the next two lines. |
| 592 | `                                           (mid - t[i - 1]) /` | Continues line 591: the part is the distance from the time of the point before up to the midpoint. |
| 593 | `                                           (t[i] - t[i - 1]);` | Continues line 591: divided by the rise in time between the two points. |
| 594 | `            break;` | Leaves the loop at the first crossing. |
| 595 | `        }` | Ends the `if` of line 590. |
| 596 | `    printf("# step,%s,%s,low_ns=%.2f,high_ns=%.2f,midpoint_ns=%.2f,", kind,` | Prints the start of the `# step` line: the kind, the series name, `low_ns` (the low plateau), `high_ns` (the high plateau) and `midpoint_ns`, each with 2 decimals. The line is not ended yet. |
| 597 | `           series, lo, hi, mid);` | Continues the call of line 596: the values `series`, `lo`, `hi` and `mid`. |
| 598 | `    if (cross < 0.0)` | Tests whether no crossing was found. |
| 599 | `        printf("N_at_midpoint=none%s,",` | In that case prints `N_at_midpoint=none`. When the series was cut, a note follows: no step before the filler cost dominates. |
| 600 | `               cnt < full ? " (no step before filler cost dominates)" : "");` | Continues the call of line 599: the note or an empty text. |
| 601 | `    else` | The other case: a crossing was found. |
| 602 | `        printf("N_at_midpoint=%.1f,", cross);` | Prints `N_at_midpoint=` and the step position with 1 decimal. This is the capacity that the program reports for the kind. |
| 603 | `    printf("largest_rise=N %ld to %ld (+%.2f ns)", n[jump - 1], n[jump],` | Prints `largest_rise=`: the two neighbouring N with the largest rise between them, and the size of that rise in ns with 2 decimals. |
| 604 | `           t[jump] - t[jump - 1]);` | Continues the call of line 603: the rise, the time at `jump` minus the time before it. |
| 605 | `    if (hi < 1.4 * lo)` | Tests whether the high plateau is below 1.4 times the low plateau. |
| 606 | `        printf(",WARNING high plateau < 1.4 x low plateau: "` | In that case adds a warning to the line: the high plateau is below 1.4 times the low plateau. |
| 607 | `               "no clear step in this N range");` | Continues the text of line 606: no clear step lies in this range of N. |
| 608 | `    printf("\n");` | Ends the output line with a line break. |
| 609 | `}` | Ends the function `report_step`. |

### Functions `num` and `usage`: read a number, print the help text (lines 611 to 648)

| Line | Source | Explanation |
|---:|---|---|
| 611 | `static void usage(void);` | Declares the function `usage` before its definition in line 626. The function `num` calls it. |
| 613 | `/* Parse a whole decimal number; any other text is a usage error. */` | Comment: the next function reads a whole decimal number. Any other text is a usage error. |
| 614 | `static long num(const char *v)` | Starts the function `num`. `v` is the text of an option value. |
| 615 | `{` | Opens the body of `num`. |
| 616 | `    char *end;` | `end`: will point to the first character that `strtol` did not read. |
| 617 | `    errno = 0;` | Clears `errno`. After the call a value other than 0 then shows that the number was out of range for `strtol`. |
| 618 | `    long x = strtol(v, &end, 10);` | `x`: the text as a number in base 10. |
| 619 | `    if (end == v \|\| *end != '\0' \|\| errno != 0) {` | Tests three things: no digit was read, or text follows the number, or the value was out of range. |
| 620 | `        fprintf(stderr, "robsize: not a number: %s\n", v);` | In that case prints `robsize: not a number:` and the text to the error output. |
| 621 | `        usage();` | Then calls `usage`, which prints the help text and ends the program with exit status 2. |
| 622 | `    }` | Ends the `if` of line 619. |
| 623 | `    return x;` | Returns the number. |
| 624 | `}` | Ends the function `num`. |
| 626 | `static void usage(void)` | Starts the function `usage`. It prints the help text to the error output and ends the program. |
| 627 | `{` | Opens the body of `usage`. |
| 628 | `    fprintf(stderr,` | Starts the first print call. The text is in the next lines. |
| 629 | `        "usage: robsize --cpu C [--kind NAME[,NAME...]\|all] [--nmin N] [--nmax N]\n"` | Help text: the usage line with the options `--cpu`, `--kind`, `--nmin` and `--nmax`. |
| 630 | `        "               [--nstep N] [--reps R] [--iters I] [--mb M]\n"` | Help text: the usage line goes on with `--nstep`, `--reps`, `--iters` and `--mb`. |
| 631 | `        "               [--stride S]\n"` | Help text: the usage line ends with `--stride`. |
| 632 | `        "  --cpu C     CPU to pin to (required, 0..%d)\n"` | Help text: `--cpu C` is the CPU to pin to. It is required, from 0 to the value of `MAX_CPU`, which `%d` prints. |
| 633 | `        "  --kind K    filler kind, or all (default all). Kinds:\n",` | Help text: `--kind K` is the filler kind, or `all`, which is the default. The list of the kinds follows. |
| 634 | `        MAX_CPU);` | Ends the first print call: the value for `%d` is `MAX_CPU`, 119. |
| 635 | `    for (int i = 0; i < NKINDS; i++)` | Starts a loop over all rows of the table `kinds`. |
| 636 | `        fprintf(stderr, "                %-11s N=%ld..%ld step %ld  %s\n",` | Prints one help line per kind: the name in a field of 11 characters, the default N from the first to the last value with the step, and the description. |
| 637 | `                kinds[i].name, kinds[i].nmin, kinds[i].nmax, kinds[i].nstep,` | Continues the call of line 636: the name and the three default values. |
| 638 | `                kinds[i].what);` | Continues the call of line 636: the description. |
| 639 | `    fprintf(stderr,` | Starts the second print call. |
| 640 | `        "  --nmin/--nmax/--nstep  replace the default N list of every\n"` | Help text: `--nmin`, `--nmax` and `--nstep` replace the default list of N. |
| 641 | `        "              selected kind\n"` | Help text: continues line 640: of every kind that is selected. |
| 642 | `        "  --reps R    repetitions per point, 5..64 (default 5)\n"` | Help text: `--reps R` is the number of repetitions per point, from 5 to 64. The default is 5. |
| 643 | `        "  --iters I   iterations per repetition, >= 200000 (default 200000)\n"` | Help text: `--iters I` is the number of passes per repetition, at least 200000. The default is 200000. |
| 644 | `        "  --mb M      size of each pointer chain in MiB (default 1024)\n"` | Help text: `--mb M` is the size of each pointer chain in MiB. The default is 1024. |
| 645 | `        "  --stride S  bytes between pointers, multiple of 64 (default 64)\n");` | Help text: `--stride S` is the number of bytes between two pointers, a multiple of 64. The default is 64. |
| 646 | `    exit(2);` | Ends the program with exit status 2. |
| 647 | `}` | Ends the function `usage`. |

### Function `main`: the options and the checks before the run (lines 649 to 708)

| Line | Source | Explanation |
|---:|---|---|
| 649 | `int main(int argc, char **argv)` | Starts the function `main`. |
| 650 | `{` | Opens the body of `main`. |
| 651 | `    long cpu = -1, nmin = -1, nmax = -1, nstep = -1;` | `cpu`, `nmin`, `nmax`, `nstep`: the CPU number and the three values of the N list. -1 means not given. |
| 652 | `    long reps = 5, iters = 200000, mb = 1024, stride = 64;` | Four more settings with their defaults: `reps` 5 repetitions, `iters` 200000 passes per repetition, `mb` 1024 MiB per chain, `stride` 64 bytes between two nodes. |
| 653 | `    const char *kind_arg = "all";` | `kind_arg`: the text of the option `--kind`. The default is `all`. |
| 655 | `    for (int i = 1; i < argc; i++) {` | Starts the loop over the arguments. |
| 656 | `        const char *a = argv[i];` | `a`: the name of the option. |
| 657 | `        if (i + 1 >= argc)` | Tests whether no value follows the option. Every option of this program takes one value. |
| 658 | `            usage();` | In that case prints the help text and ends with exit status 2. |
| 659 | `        const char *v = argv[++i];` | `v`: the value, the next argument. `++i` moves the loop past it. |
| 660 | `        if (!strcmp(a, "--cpu")) cpu = num(v);` | `--cpu`: the CPU number, read by `num`. |
| 661 | `        else if (!strcmp(a, "--kind")) kind_arg = v;` | `--kind`: the kind, or a list of kinds with commas, kept as text. |
| 662 | `        else if (!strcmp(a, "--nmin")) nmin = num(v);` | `--nmin`: the first N. |
| 663 | `        else if (!strcmp(a, "--nmax")) nmax = num(v);` | `--nmax`: the last N. |
| 664 | `        else if (!strcmp(a, "--nstep")) nstep = num(v);` | `--nstep`: the step between two N. |
| 665 | `        else if (!strcmp(a, "--reps")) reps = num(v);` | `--reps`: the repetitions per N. |
| 666 | `        else if (!strcmp(a, "--iters")) iters = num(v);` | `--iters`: the passes per repetition. |
| 667 | `        else if (!strcmp(a, "--mb")) mb = num(v);` | `--mb`: the size of each chain in MiB. |
| 668 | `        else if (!strcmp(a, "--stride")) stride = num(v);` | `--stride`: the bytes between two nodes of a chain. |
| 669 | `        else usage();` | Any other option name: prints the help text and ends with exit status 2. |
| 670 | `    }` | Ends the loop of line 655. |
| 671 | `    if (cpu < 0) {` | Tests whether `--cpu` was not given. |
| 672 | `        fprintf(stderr, "robsize: --cpu is required\n");` | In that case prints `robsize: --cpu is required`. |
| 673 | `        usage();` | Then prints the help text and ends with exit status 2. |
| 674 | `    }` | Ends the `if` of line 671. |
| 675 | `    if (cpu > MAX_CPU) {` | Tests whether the CPU number is above `MAX_CPU`, 119. |
| 676 | `        fprintf(stderr, "robsize: refusing CPU %ld (limit is %d)\n", cpu,` | In that case prints that the program refuses this CPU, with the limit. |
| 677 | `                MAX_CPU);` | Continues the call of line 676: the limit `MAX_CPU`. |
| 678 | `        return 1;` | Ends the program with exit status 1. So the program cannot measure on a CPU that our runs must not use. |
| 679 | `    }` | Ends the `if` of line 675. |
| 680 | `    if (reps < 5 \|\| reps > 64)` | Tests the repetitions: fewer than 5 or more than 64 are not allowed. |
| 681 | `        fail("--reps must be 5..64");` | In that case `fail` ends the program with the message `--reps must be 5..64`. |
| 682 | `    if (iters < 200000)` | Tests the passes per repetition: fewer than 200000 are not allowed. |
| 683 | `        fail("--iters must be >= 200000");` | In that case `fail` ends the program. |
| 684 | `    if (mb < 1 \|\| stride < 64 \|\| stride % 64 != 0)` | Tests the chain settings: the size must be at least 1 MiB, and the stride at least 64 and a multiple of 64. |
| 685 | `        fail("--mb must be >= 1 and --stride a multiple of 64");` | In that case `fail` ends the program. |
| 686 | `    if (nstep == 0 \|\| (nmin >= 0 && nmax >= 0 && nmax < nmin))` | Tests the N list: a step of 0 is not allowed, and when both ends are given the last N must not be below the first. |
| 687 | `        fail("bad --nmin/--nmax/--nstep");` | In that case `fail` ends the program. |
| 688 | `    /* every name of the --kind list must be a kind */` | Comment: every name of the `--kind` list must be a kind. |
| 689 | `    for (const char *q = kind_arg; *q && strcmp(kind_arg, "all");) {` | Starts a loop over the entries of the `--kind` text. `q` points to the start of an entry. The loop does not run when the text is `all`. |
| 690 | `        const char *e = strchr(q, ',');` | `e`: the place of the next comma, or a null pointer. |
| 691 | `        size_t l = e ? (size_t)(e - q) : strlen(q);` | `l`: the length of this entry. |
| 692 | `        int found = 0;` | `found`: becomes 1 when a kind has this name. |
| 693 | `        for (int i = 0; i < NKINDS; i++)` | Starts a loop over all rows of the table `kinds`. |
| 694 | `            found \|= strlen(kinds[i].name) == l &&` | Sets `found` when the name of the row has the length `l` and the same characters as the entry. The statement ends in line 695. |
| 695 | `                     !strncmp(q, kinds[i].name, l);` | Continues line 694: the compare of the characters. |
| 696 | `        if (!found)` | Tests whether no kind has this name. |
| 697 | `            fail("unknown --kind");` | In that case `fail` ends the program with the message `unknown --kind`. |
| 698 | `        q += l + (e != NULL);` | Moves `q` to the next entry: past the entry and, when there was one, past the comma. |
| 699 | `    }` | Ends the loop of line 689. |
| 701 | `    /* Check the only run-time patch against the assembler. */` | Comment: the next lines check the only patch that is made at run time against the assembler. |
| 702 | `    if (patch_cbnz(t_cbnz0[0], -300) != t_chk_cbnz[0]) {` | Patches the `cbnz` template with the offset -300 and compares the result with the word of the reference branch of line 101, which the assembler encoded for the same distance. |
| 703 | `        fprintf(stderr,` | When the two words differ: prints an error message. The call goes on in the next two lines. |
| 704 | `                "robsize: cbnz patch check failed: got %08x, assembler %08x\n",` | Continues line 703: the text `cbnz patch check failed` with the two words as hexadecimal numbers. |
| 705 | `                patch_cbnz(t_cbnz0[0], -300), t_chk_cbnz[0]);` | Continues line 703: the two values. |
| 706 | `        return 1;` | Ends the program with exit status 1. So no loop runs with a branch that `patch_cbnz` encoded wrongly. |
| 707 | `    }` | Ends the `if` of line 702. |

### Function `main`: pinning, the chains, the scratch buffer and the head of the output (lines 709 to 749)

| Line | Source | Explanation |
|---:|---|---|
| 709 | `    cpu_set_t set;` | `set`: a CPU set, the Linux type for a list of CPUs. |
| 710 | `    CPU_ZERO(&set);` | Empties the set. |
| 711 | `    CPU_SET((int)cpu, &set);` | Adds the CPU of `--cpu` to the set. The set now holds this one CPU. |
| 712 | `    if (sched_setaffinity(0, sizeof set, &set) != 0)` | `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the program on this CPU only. A return value other than 0 means that the call failed. |
| 713 | `        die("sched_setaffinity");` | On failure `die` prints `sched_setaffinity` with the reason and ends the program. |
| 714 | `    if (sched_getcpu() != (int)cpu)` | Asks Linux on which CPU the program runs now, and compares it with the wanted CPU. |
| 715 | `        fail("not running on the requested CPU after sched_setaffinity");` | When they differ, `fail` ends the program. |
| 717 | `    /* Chains are built after pinning: pages land on this CPU's node. */` | Comment: the chains are built after the pinning. So their pages are assigned from the memory node of this CPU. |
| 718 | `    size_t bytes = (size_t)mb << 20;` | `bytes`: the size of one chain in bytes, `mb` times `2^20`. |
| 719 | `    pair_t miss_pos;` | `miss_pos`: the place of the chase in the two chains. It is kept over the whole run. |
| 720 | `    miss_pos.a = build_chain(bytes, (size_t)stride, 0x9E3779B97F4A7C15ULL);` | Builds chain A with a fixed seed. `miss_pos.a` gets the address of its node 0. |
| 721 | `    miss_pos.b = build_chain(bytes, (size_t)stride, 0xD1B54A32D192ED03ULL);` | Builds chain B with another fixed seed. So the two chains have different orders. They lie in two separate memory areas, and a load of one chain never depends on the other chain. |
| 722 | `    long huge_kb = anon_huge_kb();` | `huge_kb`: the memory of the process on transparent huge pages in kB, read after both chains were written. |
| 724 | `    /* Hot scratch: 256 B for the load fillers, then two self-pointing` | Comment: the hot scratch buffer: 256 B for the load fillers. |
| 725 | `     * cells (one cache line each) for the no-miss baseline. */` | Comment: continues line 724: then two cells that point to themselves, one cache line each. They serve the run without misses. |
| 726 | `    uint64_t *scratch;` | `scratch`: the address of the scratch buffer. |
| 727 | `    if (posix_memalign((void **)&scratch, 64, 512) != 0)` | Reserves 512 bytes that start at a multiple of 64 bytes, the size of a cache line. |
| 728 | `        fail("posix_memalign");` | On failure `fail` ends the program. |
| 729 | `    memset(scratch, 0, 512);` | Fills the 512 bytes with 0. |
| 730 | `    scratch[32] = (uint64_t)(uintptr_t)&scratch[32];` | The cell with the index 32, at byte 256 of the buffer, gets its own address. |
| 731 | `    scratch[40] = (uint64_t)(uintptr_t)&scratch[40];` | The cell with the index 40, at byte 320 and so in the next cache line, gets its own address. |
| 732 | `    pair_t hot_pos = { scratch[32], scratch[40] };` | `hot_pos`: the place for the run without misses: the addresses of these two cells. A load of such a cell gives the same address again. So `ldr x0, [x0]` reads the same line in every pass, and the line stays in the level 1 cache. |
| 734 | `    uint32_t *code = mmap(NULL, CODE_BYTES, PROT_READ \| PROT_WRITE,` | Reserves the code buffer: `CODE_BYTES` (4 MiB) of new memory that the program may read and write. |
| 735 | `                          MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0);` | Continues the call of line 734: private memory with no file behind it. |
| 736 | `    if (code == MAP_FAILED)` | Tests whether `mmap` failed. |
| 737 | `        die("mmap code");` | On failure `die` prints `mmap code` with the reason and ends the program. |
| 739 | `    printf("# robsize: cpu=%ld chain=%ld MiB x 2, stride=%ld B, reps=%ld, "` | Prints the first comment line of the output: the CPU, the chain size in MiB (`x 2` for two chains), the stride in bytes, the repetitions and the passes. |
| 740 | `           "iters=%ld\n", cpu, mb, stride, reps, iters);` | Continues the call of line 739: the five values. |
| 741 | `    printf("# AnonHugePages=%ld kB (expected about %ld kB)%s\n", huge_kb,` | Prints the second comment line: the kB on huge pages, and the expected number. The call goes on in the next three lines. |
| 742 | `           2 * mb * 1024,` | Continues line 741: the expected number is 2 times `mb` times 1024 kB, the size of both chains. |
| 743 | `           huge_kb < mb * 1024 ? " WARNING: chains are mostly NOT on huge "` | Continues line 741: when the kB on huge pages are below the size of one chain, a warning follows: the chains are mostly not on huge pages. |
| 744 | `                                 "pages; TLB walks add to every miss" : "");` | Continues the warning text: walks of the page tables then add to every miss. |
| 745 | `    printf("# columns: median_ns, min_ns = ns per iteration with two "` | Prints the third comment line, which explains the columns: `median_ns` and `min_ns` are ns per pass with two loads that miss the caches. |
| 746 | `           "cache-missing loads; hot_ns = same code, loads hit L1 "` | Continues the text of line 745: `hot_ns` is the same code with loads that hit the level 1 cache. |
| 747 | `           "(cost of the fillers alone, min of 3 repetitions)\n");` | Continues the text of line 745: this is the cost of the fillers alone, as the minimum of 3 repetitions. |
| 748 | `    printf("kind,N,filler_instrs_per_block,median_ns,min_ns,hot_ns\n");` | Prints the head line of the data rows: `kind`, `N`, `filler_instrs_per_block`, `median_ns`, `min_ns`, `hot_ns`. |

### Function `main`: the loop over the kinds and the N values (lines 750 to 807)

| Line | Source | Explanation |
|---:|---|---|
| 750 | `    for (int ki = 0; ki < NKINDS; ki++) {` | Starts the loop over all rows of the table `kinds`, in the order of the table. |
| 751 | `        const struct kind *k = &kinds[ki];` | `k`: the row of this kind. |
| 752 | `        if (!kind_selected(kind_arg, k->name))` | Tests whether the option `--kind` selects this kind. |
| 753 | `            continue;` | If not, goes to the next kind. |
| 754 | `        long lo = nmin >= 0 ? nmin : k->nmin;` | `lo`: the first N. It is the value of `--nmin` when that was given, and the default of the kind if not. |
| 755 | `        long hi = nmax >= 0 ? nmax : k->nmax;` | `hi`: the last N, from `--nmax` or from the default of the kind. |
| 756 | `        long st = nstep > 0 ? nstep : k->nstep;` | `st`: the step, from `--nstep` when it is above 0, or from the default of the kind. |
| 757 | `        if (hi < lo)` | Tests whether the last N is below the first. |
| 758 | `            fail("N range is empty");` | In that case `fail` ends the program with the message `N range is empty`. |
| 759 | `        int cnt = (int)((hi - lo) / st) + 1;` | `cnt`: the number of N values: the distance from `lo` to `hi` divided by the step, rounded down, plus 1. |
| 760 | `        long *ns = malloc(cnt * sizeof *ns);` | `ns`: memory for the N values of this kind. |
| 761 | `        double *med = malloc(cnt * sizeof *med);` | `med`: memory for the median time per pass at each N, with misses. |
| 762 | `        double *exc = malloc(cnt * sizeof *exc);` | `exc`: memory for the median minus the filler cost at each N. |
| 763 | `        double *hot = malloc(cnt * sizeof *hot);` | `hot`: memory for the filler cost at each N. |
| 764 | `        if (!ns \|\| !med \|\| !exc \|\| !hot)` | Tests whether one of the four requests for memory failed. |
| 765 | `            fail("out of memory");` | In that case `fail` ends the program. |
| 767 | `        printf("# kind %s: %s\n", k->name, k->what);` | Prints a comment line with the name and the description of the kind. |
| 768 | `        for (int i = 0; i < cnt; i++) {` | Starts the loop over the N values of this kind. |
| 769 | `            long n = lo + i * st;` | `n`: the N of this pass. |
| 770 | `            double mn, hot_med, hot_min;` | `mn`, `hot_med`, `hot_min`: results of the two measurements of this N. |
| 772 | `            if (mprotect(code, CODE_BYTES, PROT_READ \| PROT_WRITE) != 0)` | Makes the code buffer readable and writable. The new loop is written into it next. |
| 773 | `                die("mprotect RW");` | On failure `die` ends the program. |
| 774 | `            emit_loop(code, k, n);` | Writes the loop for this kind and this N into the code buffer (`emit_loop`). |
| 775 | `            if (mprotect(code, CODE_BYTES, PROT_READ \| PROT_EXEC) != 0)` | Makes the code buffer readable and executable. It is no longer writable. |
| 776 | `                die("mprotect RX");` | On failure `die` ends the program. |
| 777 | `            __builtin___clear_cache((char *)code, (char *)code + CODE_BYTES);` | Tells the processor that the code in this range has changed. The processor then drops older copies of it from its instruction cache. |
| 778 | `            loop_fn fn = (loop_fn)(uintptr_t)code;` | `fn`: the code buffer as a function that can be called. |
| 780 | `            /* warm-up: code pages, branch predictor */` | Comment: a warm-up for the pages of the code and for the branch predictor. |
| 781 | `            hot_pos = fn(hot_pos.a, hot_pos.b, 20000, scratch);` | Warm-up of the run without misses: 20000 passes with the two cells that point to themselves. Not timed. |
| 782 | `            measure(fn, &hot_pos, scratch, (uint64_t)iters, 3, &hot_med,` | The run without misses: `measure` times 3 repetitions of `iters` passes. Both loads hit the level 1 cache. So the time per pass is the cost of the code alone, mostly the fillers. |
| 783 | `                    &hot_min);` | Continues the call of line 782: the median goes to `hot_med`, which is not used again, and the minimum to `hot_min`. |
| 784 | `            miss_pos = fn(miss_pos.a, miss_pos.b, 20000, scratch);` | Warm-up of the run with misses: 20000 passes on the two chains. Not timed. The place in the chains moves on. |
| 785 | `            measure(fn, &miss_pos, scratch, (uint64_t)iters, (int)reps,` | The run with misses, the measurement itself: `measure` times `reps` repetitions of `iters` passes on the two chains. Each pass does one load of chain A and one of chain B, and both miss the caches. |
| 786 | `                    &med[i], &mn);` | Continues the call of line 785: the median goes to `med[i]` and the minimum to `mn`. |
| 788 | `            ns[i] = n;` | Stores the N. |
| 789 | `            exc[i] = med[i] - hot_min;` | Stores the excess: the median with misses minus the filler cost. |
| 790 | `            hot[i] = hot_min;` | Stores the filler cost, the minimum of the run without misses. |
| 791 | `            printf("%s,%ld,%ld,%.3f,%.3f,%.3f\n", k->name, n, n * kunit(k),` | Prints the data row of this N: the kind, N, the number of filler instructions per block (N times the instructions per N), the median and the minimum time per pass with misses, and the filler cost. The three times are in ns with 3 decimals. |
| 792 | `                   med[i], mn, hot_min);` | Continues the call of line 791: the last three values. |
| 793 | `            fflush(stdout);` | Writes the output out at once, so each row is visible when it is ready. |
| 794 | `        }` | Ends the loop over the N values (line 768). |
| 795 | `        double miss_lo = cnt >= 3 ? (med[0] + med[1] + med[2]) / 3.0` | `miss_lo`: the low plateau of the run with misses: the mean of the first 3 medians. The statement ends in line 796. |
| 796 | `                                  : med[0];` | Continues line 795: with fewer than 3 points it is the first median. |
| 797 | `        report_step(k->name, "median_ns", ns, med, hot, miss_lo, cnt);` | Finds and prints the step in the series of the medians, under the name `median_ns`. |
| 798 | `        report_step(k->name, "median_minus_hot_ns", ns, exc, hot, miss_lo,` | Finds and prints the step a second time, in the series of the medians minus the filler cost, under the name `median_minus_hot_ns`. This series takes out most of the slope that the filler cost adds at large N. |
| 799 | `                    cnt);` | Continues the call of line 798: the last argument, the number of points. |
| 800 | `        fflush(stdout);` | Writes the output out at once. |
| 801 | `        free(ns);` | Frees the memory of the N values. |
| 802 | `        free(med);` | Frees the memory of the medians. |
| 803 | `        free(exc);` | Frees the memory of the excess values. |
| 804 | `        free(hot);` | Frees the memory of the filler costs. |
| 805 | `    }` | Ends the loop over the kinds (line 750). |
| 806 | `    return 0;` | Ends the program with exit status 0. |
| 807 | `}` | Ends the function `main`. |
