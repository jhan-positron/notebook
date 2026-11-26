# objcmp5022-20261119: object compare of the AMX kernel file for PR #5022

Short version. PR #5022's benchmarks were measured at commit 5061623a34, and the reviewer saw commit 4c4b7b8864.
These scripts compile `src/tron/kernels/amx_attn.cpp` at two commits with one compiler and one set of flags, then
compare the instruction listings function by function. The compare needs a compiler and no AMX hardware.

## Words used here

- AMX = the Intel tile-matrix instructions. The kernel file is the only file compiled with the AMX flags.
- object compare = compile one source file at two commits with the same compiler and flags, then compare the
  instruction listings function by function.
- thin LTO = thin link-time optimization. With it the compiler writes bitcode (its intermediate code), and the
  linker produces the instructions.
- delphi-3b35 = our default Granite Rapids test server since 2026-11-12. It has clang 19.1.7.

## Files

- `run-3b35.sh <results dir> <tag A> <tag B>`: runs ON delphi-3b35. It compiles each commit twice, pinned to our
  CPUs (96-143): once to a native object without link-time optimization, once to thin-LTO bitcode. It writes the
  disassembly, the symbol table and the bitcode as text. It reads the sources from `<results dir>/src-<tag>/`.
- `compare.py <results dir> <tag A> <tag B>`: runs anywhere. It splits the disassembly per function, counts
  instructions, diffs the two listings, diffs the two bitcode texts, and writes `objcmp.txt`.

The flags come from the compile command CMake recorded for this file in an earlier RelWithDebInfo build with
`TRON_AMX_DISPATCH=ON` (`~/workspace/ai-runs/tron-vnnik-typed/gen/compile_commands.json`, 2026-10-02). Three
defines that no file at 4c4b7b8864 sets or reads are dropped. The spdlog headers (v1.17.0, the pinned version)
come from that same build tree.

## How to run

    RES=~/workspace/intel-AMX/exec/results/objcmp5022-20261119
    for sha in <A> <B>; do mkdir -p $RES/src-$sha; git -C <tron worktree> archive $sha h src/tron/kernels/amx_attn.cpp | tar -x -C $RES/src-$sha; done
    ssh delphi-3b35 "bash ~/workspace/intel-AMX/exec/objcmp5022-20261119/run-3b35.sh $RES <A> <B>"
    python3 ~/workspace/intel-AMX/exec/objcmp5022-20261119/compare.py $RES <A> <B>

## Result of 2026-11-19 (5061623a34 against 4c4b7b8864)

- Compiler on both sides: Ubuntu clang version 19.1.7 (++20250114103320+cd708029e0b2-1~exp1~20250114103432.75).
  That string equals the one in `exec/results/glimext-20261018/build-g16h.txt`, the measured build.
- 11 functions compared. 10 have identical listings: both pack kernels (509 and 1,285 instructions), the 4-head QK
  kernel (204), both PV kernels (121 and 206), and the 5 other functions (90 in total).
- `qk_rowmajor_128x4<16>` has the same 207 instructions at both commits. Two neighbouring counter increments at the
  end of the outer loop changed places (`addq $0x40, %rdx` and `addq $0x400, %rsi`). See `diff-8.txt`.
- Cause: line 243 reads `s + r * TILE_ROWS_16` where the measured commit read `s + r * 16`. `r` is an `int` and
  `TILE_ROWS_16` is a `size_t`, so a signed 32-bit multiply became an unsigned 64-bit multiply.
- The thin-LTO bitcode differs in a flag (`nuw`) on four shift operations, two in each QK kernel, and in two
  source-position numbers of inline assembly. See `diff-ir.txt`.

Not covered: the linked binary, the call site in `h/tron/models/self_attention.hpp`, and any commit after
4c4b7b8864. Repeat the compare at the final head of the PR.

## Where results land

`exec/results/objcmp5022-20261119/`: `build-info.txt` (host, compiler, flags), `objcmp.txt` (the table),
`diff-8.txt`, `diff-ir.txt`, `out-<tag>/` (object, disassembly, symbols, bitcode text), `src-<tag>/` (the exported
sources).
