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
2. Candidate 1, `k_cread`: 16 loads of 16 B in a `do` loop, then one empty asm statement with 16 inputs ({L7-36}).
3. Candidate 2, `k_cread_loop`: the same loads written as two loops, with one empty asm statement per load ({L38-46}).
4. Candidate 3, `k_cread_plain`: the two loops without an asm statement ({L48-56}).
5. Candidate 4, `k_cread_volatile`: standard C only, reads of 8 B through a `volatile` pointer ({L58-65}).

## Behavior a reader must know

- Nothing in this file is timed, and no function of it runs in a test.
- The machine code of the compile check, per loop pass [Ref1]: candidate 1 has 8 `ldp` loads for 256 B and 11 instructions. Candidate 2 has 8 `ldp` loads for 256 B and 12 instructions. Candidate 3 has no load. Candidate 4 has 16 loads of 8 B for 128 B and 19 instructions.
- So the two candidates with an empty asm statement keep their loads, and the candidate without one loses them [Ref1].
- The compiler chooses the machine code. These counts hold for gcc 14.2.0 with the flags that `remote.sh` sets [Ref1].
- The functions are not `static`. So the compiler must keep each of them in the object file, also when nothing calls it.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-cread/report/probe-cread.txt`: the record of a compile check of `cread.c` on CRB. Its first row gives the start time 2026-11-13 05:35:02 UTC. The file has the form of the output of `remote.sh`: the compiler (gcc 14.2.0), the sha256 of `cread.c`, the flags, the text `compile ok` and, under one heading per function, the machine-code listing of the four functions. The sha256 in it equals the sha256 of the file that this page explains.
