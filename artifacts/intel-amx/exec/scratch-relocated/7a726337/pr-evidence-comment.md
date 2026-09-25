## Evidence tables for the description's Verification section

**Short version.** These are the raw result tables behind the description: the token-identity pairs, the 36 performance runs with their pass-rule comparison, the unit-test summary lines, the instruction comparison and the syntax check of the rebased tip. Every run was on delphi-3bda (Intel Xeon 6962P with AMX), our half of the machine (socket 1, CPUs 72-143 and 216-287, accelerator cards 90 and 93). The commit ids are the pre-rebase ids; the description's Verification section maps them to the commits of this PR.

### Token identity (Step D of the test plan; production code of the first commit, `85084e937c`)

Recipe: qwen3-4b tp2 (`ingested-qwen-3-4b-instruct-2507-tp2`), `runtron --instance 2,4` on cards 90:00.0 and 93:00.0, one user, runtron's built-in prompt of the requested length (`--prompt-length`), temperature 0, seed 1, `--pay-for-determinism`, 256 generated tokens. Arms: base = `main` `0a51385e95`, head = the branch, head2 = the branch run a second time (A/A control), baseoff / headoff = the same binaries with the kill switch `TRON_AMX_DISABLE=1`.

CPU attention, prompt 1024:

| Pair | Result |
|---|---|
| head vs head2 | identical for 256 tokens |
| head vs base | identical for 256 tokens |
| headoff vs baseoff | identical for 256 tokens |
| headoff vs head | identical for 256 tokens |
| baseoff vs base | identical for 256 tokens |

CPU attention, prompt 8192: the same five pairs, all identical for 256 tokens.

FPGA attention (`USE_HW_ATTN=1`), prompt 1024 and prompt 8192: head vs base identical for 256 tokens in both.

### Performance A/B (Step E; production code of the second commit, `682064f8fb`, against `main` `0a51385e95`)

8 users per run, 256 generated tokens, 3 interleaved repetitions per arm and cell, 36 runs, 0 failures, 0 early stops. TPS = decode tokens per second per user; TTFT = time to first token in seconds (the maximum over the 8 users). Values are the mean over the 3 repetitions with the sample standard deviation in parentheses.

| Cell | Arm | TPS (sd) | TTFT s (sd) |
|---|---|---|---|
| prompt 1024 | base | 79.02 (0.28) | 3.159 (0.002) |
| prompt 1024 | head | 79.18 (0.31) | 3.154 (0.004) |
| prompt 1024 | baseoff | 71.60 (0.35) | 3.962 (0.004) |
| prompt 1024 | headoff | 71.29 (0.08) | 3.956 (0.009) |
| prompt 2048 | base | 52.12 (0.12) | 7.261 (0.004) |
| prompt 2048 | head | 52.46 (0.18) | 7.242 (0.007) |
| prompt 2048 | baseoff | 44.97 (0.09) | 11.205 (0.018) |
| prompt 2048 | headoff | 45.29 (0.08) | 11.177 (0.007) |
| prompt 8192 | base | 17.04 (0.02) | 53.071 (0.229) |
| prompt 8192 | head | 17.06 (0.01) | 52.684 (0.172) |
| prompt 8192 | baseoff | 14.61 (0.02) | 123.200 (0.125) |
| prompt 8192 | headoff | 14.63 (0.01) | 123.071 (0.170) |

Pass rule, fixed before the runs: the absolute difference of the means lies inside the run-to-run band. The band is the larger of 2 x the larger of the two arms' standard deviations and the reference spread measured for this shape on 2026-09-14 (0.4 TPS, 0.15 s TTFT).

| Cell | Comparison | TPS delta | TPS abs. delta vs band | TTFT delta | TTFT abs. delta vs band |
|---|---|---|---|---|---|
| prompt 1024 | head vs base | +0.2 % | 0.161 vs 0.629: inside | -0.2 % | 0.006 vs 0.150: inside |
| prompt 1024 | headoff vs baseoff | -0.4 % | 0.314 vs 0.697: inside | -0.1 % | 0.006 vs 0.150: inside |
| prompt 2048 | head vs base | +0.7 % | 0.341 vs 0.400: inside | -0.3 % | 0.019 vs 0.150: inside |
| prompt 2048 | headoff vs baseoff | +0.7 % | 0.324 vs 0.400: inside | -0.3 % | 0.029 vs 0.150: inside |
| prompt 8192 | head vs base | +0.1 % | 0.019 vs 0.400: inside | -0.7 % | 0.387 vs 0.459: inside |
| prompt 8192 | headoff vs baseoff | +0.2 % | 0.026 vs 0.400: inside | -0.1 % | 0.129 vs 0.341: inside |

Every difference larger than 0.3 % has the branch faster. The two band definitions alone disagree on three comparisons: the reference floor alone (0.15 s) would flag the prompt-8192 TTFT difference (0.387 s, branch faster), and 2 x sd alone would flag the two prompt-2048 TPS differences (about +0.33 TPS, branch faster, with arm spreads of at most 0.09 TPS). The combined band above is the one the pass rule uses.

### Unit tests (16-lane, clang 19 from the Nix shell, RelWithDebInfo)

| Tree | Commit | Test | Summary line |
|---|---|---|---|
| AMX on | working tree of the first commit (production code = `85084e937c`) | t_amx_numerics, real AMX | All tests passed (12301 assertions in 4 test cases), no "AMX unavailable" warning |
| AMX on | same | t_amx_numerics, `TRON_AMX_DISABLE=1` | All tests passed (2060 assertions in 4 test cases), "AMX unavailable" printed for the QK and the PV case |
| AMX on | same | t_amx_dispatch_dtype | passed (4 sections) |
| AMX on | same | t_heterogeneous_scheduler | passed |
| AMX on | `c3c368d298` (pre-rebase tip) | t_llama_unit | All tests passed (199125 assertions in 43 test cases) |
| AMX off | `85084e937c` | t_llama_unit | All tests passed (176462 assertions in 43 test cases) |
| AMX off | `85084e937c` | t_heterogeneous_scheduler | passed (1852 assertions); t_amx_numerics and t_amx_dispatch_dtype run their "not compiled" placeholder (1 assertion each) |
| Debug, AMX off, no `TRON_IGNORE_NAN` | `85084e937c` | t_llama_unit `[kv_data]` | 29 of 29 cases passed (48958 assertions) |
| AMX off, host suite (`make build-test-host`, `make test-host`) | snapshot of `85084e937c` | 89 host tests | 669 targets built; 88 passed, 1 skipped (t_proxy_lib), 0 failed; `main` `0a51385e95` in the same tree configuration: the identical status set |

### Instruction comparison (Step F; branch `c3c368d298` production code against `main` `0a51385e95`)

Method: 19 `noinline` wrapper functions (set_v even/odd for bf16, fp16 and float; get_v even/odd for float and bf16; book::append; the scaled_v weighted sum; book construction; reclaimable free and restore; the set_v/get_v variants with a runtime token) compiled against both trees with t_llama_unit's exact clang-19 command, disassembled with `objdump -d -r`, and compared after normalising addresses and register names.

| Body | `main` | branch | Verdict |
|---|---|---|---|
| set_v even/odd for bf16, float, fp16; get_v even/odd for float, bf16 (constant token) | 63-83 instructions each | same | identical sequences |
| scaled_v weighted sum | 130 (8 vdpbf16ps, 31 vmovaps) | 130 | identical |
| set_v / get_v with a runtime token | 87-103 | 87-102 | vector instructions identical and in the same order; one fewer scalar add (scaled-index addressing) |
| book::append closure (copy_token bodies) | 409 | 417 | vector mnemonics unchanged; the difference is scalar address bookkeeping; no new call, no memcpy or memset change |
| book construction / reclaimable restore / scaled_v | 274 / 137 / 130 | 202 / 108 / 130 | the array construction stays out of line; no store through the arena pointer, no rep stos, no memset, no loop |

This comparison is of the pre-rebase code. On the rebased tip the array construction is called from `allocate_retained_storage` and once per chunk from `allocate_reclaimable_chunk`; that path is re-checked on the rebased build and the result is added here.

### Syntax check of the rebased tip (2026-09-23 05:06-05:08 UTC, during the nightly CI's lease, 2 CPUs, `nice 19`)

`-fsyntax-only` with the 16-lane AMX-on compile commands of the tree: `src/tron/kernels/amx_attn.cpp` (2 s), `t/t_amx_dispatch_dtype.cpp` (13 s), `t/t_amx_numerics.cpp` (8 s), `t/heterogeneous_scheduler_compile.cpp` (16 s), `t/t_llama_unit.cpp` (15 s): all rc 0. `clang-format-19 --dry-run -Werror` on the 12 changed files: rc 0. `make lint-notes`: rc 0.
