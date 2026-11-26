# `cread.c` explained, line by line

- Source file: `cread-2026-11-12/cread.c` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (C source, 65 lines, 2396 bytes).
- sha256 of the source when this page was built: `6b110b674b10908e3ce83533a30ca466003a1aff86dab47405010d4d39f13b30`.

## Short version: purpose

`cread.c` holds four candidates for a read loop in C that only loads memory and does no arithmetic. The file is only compiled: the script `remote.sh` compiles it on CRB and prints the machine code of the four functions, and no program calls them. The body of candidate 1, `k_cread`, equals the body of `k_cread` in the benchmark file `bandwidth_cread.c` of the same folder.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`k_asmread`**: the function of the kernel `asmread` in the benchmark source. `asmread` is a hand-written load-only loop with 8 `ldp q` loads per 256 B.
- **Candidate**: one of the four functions of this file. The comments call them `v1` to `v4`.
- **NEON intrinsics**: C functions that map to Arm vector instructions. Here: `vld1q_u64`, which loads 16 B into a vector.
- **Empty asm statement**: an inline-assembly statement with an empty instruction text. It adds no instruction. It only tells the compiler which values must be in registers at that place.
- **Loop pass**: one run of the loop body.
- **`ldp`**: here `ldp q`, the Arm instruction that loads two 16-byte vector registers (32 B).
- **`ldr`, `ldur`**: Arm instructions that load one register. In the listing of candidate 4 each one loads 8 B.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Compile check**: the compile of this file on CRB on 2026-11-13 whose record is [Ref1]. Nothing was run in it.
- **`remote.sh`**: the script of the same folder that compiles this file on CRB and prints the machine-code listing of the four functions.
- **Object file**: the output of the compiler for one source file, before linking. It cannot be run by itself.
- **gcc**: the GNU C compiler.
- **sha256**: a checksum. Two files with the same sha256 have the same content.

## Main flow

1. Nothing executes this file. It has no `main`. `remote.sh` compiles it to the object file `cread.o` and prints the machine code of each function.
2. Candidate 1, `k_cread`: 16 loads of 16 B in a `do` loop, then one empty asm statement with 16 inputs (lines 7 to 36).
3. Candidate 2, `k_cread_loop`: the same loads written as two loops, with one empty asm statement per load (lines 38 to 46).
4. Candidate 3, `k_cread_plain`: the two loops without an asm statement (lines 48 to 56).
5. Candidate 4, `k_cread_volatile`: standard C only, reads of 8 B through a `volatile` pointer (lines 58 to 65).

## Behavior a reader must know

- Nothing in this file is timed, and no function of it runs in a test.
- The machine code of the compile check, per loop pass [Ref1]: candidate 1 has 8 `ldp` loads for 256 B and 11 instructions. Candidate 2 has 8 `ldp` loads for 256 B and 12 instructions. Candidate 3 has no load. Candidate 4 has 16 loads of 8 B for 128 B and 19 instructions.
- So the two candidates with an empty asm statement keep their loads, and the candidate without one loses them [Ref1].
- The compiler chooses the machine code. These counts hold for gcc 14.2.0 with the flags that `remote.sh` sets [Ref1].
- The functions are not `static`. So the compiler must keep each of them in the object file, also when nothing calls it.

## Source and explanation, line by line

- Text shown: the file `cread-2026-11-12/cread.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (65 lines, 2396 bytes, sha256 `6b110b674b10908e3ce83533a30ca466003a1aff86dab47405010d4d39f13b30`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and include lines (lines 1 to 6)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `/* Candidates for a read loop written in C that only loads, like k_asmread.` | Comment: the file holds candidates for a read loop written in C that only loads, like `k_asmread`. `k_asmread` is the hand-written load-only loop of the benchmark. |
| 2 | ` * Compile check only. Not part of bench/bandwidth.c. */` | Comment: the file is for a compile check only. It is not part of the benchmark source `bandwidth.c` of the folder `bench`. So no program calls its functions. |
| 3 | `#include <arm_neon.h>` | Includes the header of the NEON intrinsics (C functions that map to Arm vector instructions). It gives the vector type `uint64x2_t` and the load function `vld1q_u64`. |
| 4 | `#include <stddef.h>` | Includes the type `size_t`. The functions use it for the element count `n`. |
| 5 | `#include <stdint.h>` | Includes the integer type `uint64_t` (64 bits). |

### Candidate 1, `k_cread`: 16 loads, then one empty asm statement with 16 inputs (lines 7 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 7 | `/* v1: 16 loads of 16 B, then one empty asm statement that names all 16` | Comment: version 1 (`v1`) has 16 loads of 16 B, then one empty asm statement. The statement names all 16 loaded values as inputs (the sentence ends in line 8). |
| 8 | ` * values as inputs. The statement emits no instruction. */` | Comment: the statement emits no instruction. |
| 9 | `__attribute__((noinline)) void k_cread(const uint64_t *a, size_t n)` | Starts the function `k_cread`, candidate 1. `a` is the start of the buffer. `n` is the number of 8-byte elements in it. `noinline` forbids the compiler to merge the function into a caller. The function is not `static`. So the compiler must keep it in the object file, also when nothing calls it. |
| 10 | `{` | Opens the body of `k_cread`. |
| 11 | `    const uint64_t *p = a;` | `p`: the read position. It starts at the first element of the buffer. |
| 12 | `    const uint64_t *end = a + n;` | `end`: the first address after the buffer, which is `a` plus `n` elements. |
| 13 | `    do {` | `do`: the loop body runs before the first test of the end (line 35). So the loop is right only for an `n` that is a multiple of 32 and not 0. With another `n` it would read beyond the buffer. |
| 14 | `        uint64x2_t v0 = vld1q_u64(p + 0);` | `vld1q_u64(p + 0)` loads 16 B, which is two 8-byte elements, from the read position into the vector variable `v0`. The type `uint64x2_t` is a vector of two 64-bit integers. This load reads the bytes 0 to 15 of the current block of 256 B. |
| 15 | `        uint64x2_t v1 = vld1q_u64(p + 2);` | Loads the 16 B at element 2 after the read position into `v1`: the bytes 16 to 31 of the block. |
| 16 | `        uint64x2_t v2 = vld1q_u64(p + 4);` | Loads the bytes 32 to 47 of the block into `v2`. |
| 17 | `        uint64x2_t v3 = vld1q_u64(p + 6);` | Loads the bytes 48 to 63 of the block into `v3`. |
| 18 | `        uint64x2_t v4 = vld1q_u64(p + 8);` | Loads the bytes 64 to 79 of the block into `v4`. |
| 19 | `        uint64x2_t v5 = vld1q_u64(p + 10);` | Loads the bytes 80 to 95 of the block into `v5`. |
| 20 | `        uint64x2_t v6 = vld1q_u64(p + 12);` | Loads the bytes 96 to 111 of the block into `v6`. |
| 21 | `        uint64x2_t v7 = vld1q_u64(p + 14);` | Loads the bytes 112 to 127 of the block into `v7`. |
| 22 | `        uint64x2_t v8 = vld1q_u64(p + 16);` | Loads the bytes 128 to 143 of the block into `v8`. |
| 23 | `        uint64x2_t v9 = vld1q_u64(p + 18);` | Loads the bytes 144 to 159 of the block into `v9`. |
| 24 | `        uint64x2_t v10 = vld1q_u64(p + 20);` | Loads the bytes 160 to 175 of the block into `v10`. |
| 25 | `        uint64x2_t v11 = vld1q_u64(p + 22);` | Loads the bytes 176 to 191 of the block into `v11`. |
| 26 | `        uint64x2_t v12 = vld1q_u64(p + 24);` | Loads the bytes 192 to 207 of the block into `v12`. |
| 27 | `        uint64x2_t v13 = vld1q_u64(p + 26);` | Loads the bytes 208 to 223 of the block into `v13`. |
| 28 | `        uint64x2_t v14 = vld1q_u64(p + 28);` | Loads the bytes 224 to 239 of the block into `v14`. |
| 29 | `        uint64x2_t v15 = vld1q_u64(p + 30);` | Loads the bytes 240 to 255 of the block into `v15`. One loop pass has 16 loads in the source. It reads 256 B, each byte once. In the compile check gcc joined each two neighbour loads into one `ldp` instruction, which loads 32 B into two 16-byte registers [Ref1]. |
| 30 | `        __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3),` | The empty asm statement. Its instruction text (`""`) is empty, so it adds no instruction to the loop. It names the 16 vectors as inputs that must be in vector registers (`"w"`). So the compiler must have all 16 values loaded at this point. `volatile` tells the compiler to keep the statement. This line names `v0` to `v3`. |
| 31 | `                         "w"(v4), "w"(v5), "w"(v6), "w"(v7),` | Continues the list of inputs: `v4` to `v7`. |
| 32 | `                         "w"(v8), "w"(v9), "w"(v10), "w"(v11),` | Continues the list of inputs: `v8` to `v11`. |
| 33 | `                         "w"(v12), "w"(v13), "w"(v14), "w"(v15));` | Ends the list of inputs and the statement: `v12` to `v15`. After this line nothing uses the values. They are dropped. |
| 34 | `        p += 32;` | Moves the read position forward by 32 elements, which is 256 B. |
| 35 | `    } while (p < end);` | Repeats the loop while the read position is below the end. In the compile check one loop pass of the machine code is 11 instructions for 256 B: 8 `ldp`, 1 `add`, 1 `cmp` and 1 branch [Ref1]. |
| 36 | `}` | Ends the function `k_cread`. |

### Candidate 2, `k_cread_loop`: two loops, one empty asm statement per load (lines 38 to 47)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `/* v2: same, written as two loops. One empty asm statement per load. */` | Comment: version 2 (`v2`) does the same as version 1, written as two loops. It has one empty asm statement per load. |
| 39 | `__attribute__((noinline)) void k_cread_loop(const uint64_t *a, size_t n)` | Starts the function `k_cread_loop`, candidate 2. It has the same parameters as `k_cread`. |
| 40 | `{` | Opens the body of `k_cread_loop`. |
| 41 | `    for (size_t i = 0; i < n; i += 32)` | The outer loop. One loop pass handles 32 elements, which is 256 B. |
| 42 | `        for (int j = 0; j < 32; j += 2) {` | The inner loop: 16 steps per outer loop pass. `j` goes from 0 to 30 in steps of 2 elements, so each step handles 16 B. |
| 43 | `            uint64x2_t v = vld1q_u64(a + i + j);` | Loads the 16 B at element `i + j` of the buffer into the vector variable `v`. |
| 44 | `            __asm__ volatile("" : : "w"(v));` | An empty asm statement with one input: `v` must be in a vector register at this point. The statement adds no instruction. So each of the 16 loads has its own statement. |
| 45 | `        }` | Ends the inner loop of line 42. In the compile check the machine code has no inner loop. One loop pass has 8 `ldp` loads (256 B), 2 `add`, 1 `cmp` and 1 branch, which is 12 instructions [Ref1]. |
| 46 | `}` | Ends the function `k_cread_loop`. |

### Candidate 3, `k_cread_plain`: no asm statement (lines 48 to 57)

| Line | Source | Explanation |
|---:|---|---|
| 48 | `/* v3: no asm statement at all. Expected: gcc deletes the loads. */` | Comment: version 3 (`v3`) has no asm statement at all. The comment expects that gcc deletes the loads. |
| 49 | `__attribute__((noinline)) void k_cread_plain(const uint64_t *a, size_t n)` | Starts the function `k_cread_plain`, candidate 3. It has the same parameters as `k_cread`. |
| 50 | `{` | Opens the body of `k_cread_plain`. |
| 51 | `    for (size_t i = 0; i < n; i += 32)` | The outer loop, as in line 41: 32 elements (256 B) per loop pass. |
| 52 | `        for (int j = 0; j < 32; j += 2) {` | The inner loop, as in line 42: 16 steps of 16 B each. |
| 53 | `            uint64x2_t v = vld1q_u64(a + i + j);` | Loads the 16 B at element `i + j` into the vector variable `v`, as in line 43. |
| 54 | `            (void)v;` | `(void)v` marks `v` as used, so the compiler gives no warning about a variable that is not used. It has no other effect. Nothing needs the loaded value. |
| 55 | `        }` | Ends the inner loop of line 52. In the compile check the machine code of this function holds no load. Its loop only counts: 1 `add`, 1 `cmp` and 1 branch [Ref1]. So gcc deleted the loads, as the comment of line 48 expects. |
| 56 | `}` | Ends the function `k_cread_plain`. |

### Candidate 4, `k_cread_volatile`: standard C with a `volatile` pointer (lines 58 to 65)

| Line | Source | Explanation |
|---:|---|---|
| 58 | `/* v4: ISO C only, volatile access. Expected: 8 B loads, no 16 B loads. */` | Comment: version 4 (`v4`) uses ISO C only, the standard C language without compiler extensions. It reads through a `volatile` pointer. The comment expects loads of 8 B and no loads of 16 B. |
| 59 | `__attribute__((noinline)) void k_cread_volatile(const uint64_t *a, size_t n)` | Starts the function `k_cread_volatile`, candidate 4. It has the same parameters as `k_cread`. |
| 60 | `{` | Opens the body of `k_cread_volatile`. |
| 61 | `    const volatile uint64_t *p = a;` | `p`: a pointer to `volatile` data, set to the start of the buffer. `volatile` tells the compiler that it must do every read of the data that the source holds. |
| 62 | `    for (size_t i = 0; i < n; i += 16)` | The outer loop. One loop pass handles 16 elements, which is 128 B. |
| 63 | `        for (int j = 0; j < 16; j++)` | The inner loop: 16 steps, one 8-byte element per step. |
| 64 | `            (void)p[i + j];` | Reads element `i + j` through the `volatile` pointer and drops the value. In the compile check one loop pass of the machine code has 16 loads of 8 B each (1 `ldr` and 15 `ldur`), 1 `add`, 1 `cmp` and 1 branch, which is 19 instructions [Ref1]. So it reads 128 B per loop pass with loads of 8 B, as the comment of line 58 expects. |
| 65 | `}` | Ends the function `k_cread_volatile`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-cread/report/probe-cread.txt`: the record of a compile check of `cread.c` on CRB. Its first row gives the start time 2026-11-13 05:35:02 UTC. The file has the form of the output of `remote.sh`: the compiler (gcc 14.2.0), the sha256 of `cread.c`, the flags, the text `compile ok` and, under one heading per function, the machine-code listing of the four functions. The sha256 in it equals the sha256 of the file that this page explains.
