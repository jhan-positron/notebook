# AMD machine test: does the AMX build fall back to AVX?

Test date 2026-09-11. Branch `jhan-amx-p0` at commit 47f6f2dceb (the head of PR #3879). Author: jhan.

Words used in all three versions: **tron** is the inference program under test and **runtron** its command-line tool. **AMX** (Intel Advanced Matrix Extensions) is a matrix instruction set that Intel Xeon 6 has and AMD EPYC does not. The **AVX path** is the existing attention code written with AVX-512 vector instructions, which both CPU makers support. **TRON_AMX_DISPATCH** is the build option that compiles the AMX code in; it defaults to off. **TRON_AMX_DISABLE** is the run-time kill switch (set to exactly `1` to turn AMX off). **available()** is tron's run-time probe that decides whether AMX may be used.

---

## Short version (about 200 words)

We built runtron with the AMX code compiled in, left AMX enabled, and ran the Qwen3-4B model on andoria-06, an AMD EPYC 9654 machine that has no AMX hardware. Attention ran on the CPU (`USE_HW_ATTN=0`), the only place the AMX code can run, and the kill switch stayed unset. We expected the program to detect the missing hardware and use the AVX path. It did.

The proof is the probe's one visible act. Before using AMX, available() asks Linux for permission with the system call `arch_prctl(ARCH_REQ_XCOMP_PERM)`. It makes that call only after the CPU has reported AMX support. A small logging shim recorded every such call. On the AMD machine the shim recorded none. On an Intel machine (delphi-3bda) the identical run recorded exactly one, so the method does see the call when AMX exists.

| Host | AMX in binary | Permission call with AMX enabled | Run |
|---|---|---|---|
| andoria-06 (AMD, no AMX) | yes | none | 29 tokens, exit 0 |
| delphi-3bda (Intel, AMX) | yes | one, granted | 29 tokens, exit 0 |

The AMD run also produced tokens identical to a second run with the kill switch on, and it finished without an illegal-instruction fault. Both agree with the AVX path having run.

---

## Mid-length version (about 500 words)

### What we wanted to know

PR #3879 adds an AMX fast path to tron's software attention. The code is compiled only when TRON_AMX_DISPATCH is on, and at run time it must step aside on CPUs without AMX. This test checks the second point on real AMD hardware: with everything AMX-related switched on, does the program still take the AVX path on an AMD EPYC machine?

### Setup

andoria-06 has two AMD EPYC 9654 processors (96 cores each) and eight FPGA accelerator cards. Its second half, cards 4 to 7 on the second CPU socket, was free, so the run used `SYSTEM_CONFIG=--instance 1,2`, tron's way of naming that half. runtron was built on the machine itself in a fresh build directory (`gen-amd`) with `-DTRON_AMX_DISPATCH=ON`; the build took 9 minutes. The binary contains 32 AMX tile instructions and 10 AMX kernel symbols, so the AMX code is present.

The model was `ingested-qwen-3-4b-instruct-2507-tp2` (Qwen3-4B split over two cards). Attention was forced onto the CPU with `USE_HW_ATTN=0`, because the AMX code lives only in CPU attention. The prompt was padded to 256 tokens, 32 tokens were requested, and the sampler ran at temperature 0 with deterministic scheduling so two runs can be compared.

### How the path was observed

available() checks, in order: the kill switch, the CPU's feature bits (CPUID), the operating system's AMX state, and finally Linux permission through `arch_prctl(ARCH_REQ_XCOMP_PERM)`. That system call is the only sign of the probe visible from outside. A 40-line LD_PRELOAD shim (a library loaded before the program that intercepts the C library's `syscall` function) logged every such call to a file. The usual tool, strace, could not be used: tracing runtron disables the privileged helper that mounts its statistics filesystem, and runtron exits before loading the model.

### Results

| Arm | Host | Kill switch | Permission call | Tokens generated | Speed | Exit |
|---|---|---|---|---|---|---|
| AMX enabled | andoria-06 (AMD) | unset | none | 29 | 333 tokens/s | 0 |
| AMX disabled | andoria-06 (AMD) | `1` | none | 29, identical to above | 334 tokens/s | 0 |
| AMX enabled (control) | delphi-3bda (Intel) | unset | `arch_prctl(0x1023, 18) = 0` | 29 | 232 tokens/s | 0 |
| AMX disabled (control) | delphi-3bda (Intel) | `1` | none | 29, identical to above | 229 tokens/s | 0 |

On AMD, the enabled arm made no permission call. The probe therefore returned false at the CPUID step, before the request, and the dispatch fell through to the AVX kernels. The Intel control shows that the same settings do reach the call when the hardware exists, so the empty log on AMD is a real result, not a blind spot in the method. Two supporting signs agree: the AMD run finished normally, while an AMX instruction on this CPU would have faulted, and its tokens match the kill-switch run exactly. Token identity alone is not proof, since the Intel pair was also identical over 29 tokens.

### Side effects

The run reused a stale 16 GiB hugepage slice file left by another user in that half of the machine and shrank it to 4 GiB; it was left in place. The three slice files this test created were removed afterwards, on both machines.

---

## Long version (about 1000 words)

### Purpose

PR #3879 adds an optional AMX fast path for the attention step of tron's CPU inference. Two safeguards are meant to keep it harmless on machines that cannot run it. The first is the build option TRON_AMX_DISPATCH: when it is off, the AMX source is not compiled at all. The second is the run-time probe available(): when it returns false, the existing AVX kernels run even in an AMX build. This test exercises the second safeguard on real AMD hardware: AMX compiled in, AMX enabled by every switch. The expected outcome is that the AMX path is not taken.

### The machine and the half we used

andoria-06 has two AMD EPYC 9654 processors, 96 cores each, 377 GB of memory, and eight FPGA accelerator cards. Its CPU flags list AVX-512 including the bf16 extension, but no `amx_*` flag. The first half of the machine was in use by colleagues, so the run took the second half: cards 4 to 7, on the second processor socket. tron names that half `--instance 1,2` (instance 1 of 2), which the login environment already sets in `SYSTEM_CONFIG`. The half's hugepage slices are files `slice-4-of-8` to `slice-7-of-8` in `/dev/hugepages`.

| Item | Value |
|---|---|
| Machine | andoria-06, Linux 6.8.0-138 |
| CPU | 2x AMD EPYC 9654, 384 hardware threads, no AMX |
| Half used | `--instance 1,2`: PCI devices 81:00.0, a1:00.0, c1:00.0, e1:00.0, NUMA node 1 |
| Source | `~/workspace/tron-amx`, commit 47f6f2dceb |
| Build | `cmake --preset cross-avx512 -B gen-amd -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON`, target runtron, 32 parallel jobs inside `nix develop`, 9 minutes |
| Binary check | `TRON_AMX_DISPATCH:BOOL=ON` in the cache; 32 `tdpbf16ps` instructions; 10 `amx_attn_h128g4` symbols |
| Model | `ingested-qwen-3-4b-instruct-2507-tp2` (Qwen3-4B, tensor-parallel over two cards) |
| Prompt | a 132-word text, padded to 256 tokens; 32 tokens requested; temperature 0; `--pay-for-determinism` |
| Environment | `USE_HW_ATTN=0` (attention on the CPU, where the AMX dispatch lives); `TRON_AMX_DISABLE` unset in the enabled arm, `1` in the disabled arm |

### Why the usual observation tools do not work

tron writes no log line and keeps no counter that says whether the AMX kernels ran. The probe itself is the observable. available() runs once per process and checks, in order: the kill switch, CPUID leaf 7 bits 22 and 24 (AMX-BF16 and AMX-TILE), the XCR0 register bits 17 and 18 (the operating system enabled the tile state), and finally the system call `arch_prctl(ARCH_REQ_XCOMP_PERM, XTILEDATA)` that asks Linux for permission. On a CPU without AMX the second check fails and the function returns false without making the call. So the presence or absence of that one system call tells us where the probe stopped.

strace, the standard system-call tracer, cannot be used on runtron. runtron mounts a small statistics filesystem through the setuid helper `fusermount3`, and Linux strips setuid privileges from any traced process, so the mount fails and runtron exits before loading the model. Instead, a 40-line C shim loaded with LD_PRELOAD intercepts the C library's `syscall` function, forwards every call unchanged, and appends a line to a file when the call is `arch_prctl` with request 0x1023. The shim also logs when it is loaded, so an empty result can be told apart from a shim that never ran. runtron links `syscall` dynamically, which is what makes the interception possible.

### Runs and results

Four runs were made: the two arms on andoria-06, and the same two arms on delphi-3bda, an Intel Xeon 6962P machine with AMX, using the runtron built there from the same commit. The Intel runs are the control.

| Run | Host | `TRON_AMX_DISABLE` | Shim loaded | Permission call | Attention mode (from the log) | Output | Wall time |
|---|---|---|---|---|---|---|---|
| AMD, AMX enabled | andoria-06 | unset | yes | none | CPU (`USE_HW_ATTN=0`) | 29 tokens in 0.087 s, 333 tokens/s, exit 0 | 13 s |
| AMD, kill switch | andoria-06 | `1` | yes | none | CPU | 29 tokens, byte-identical to the enabled arm, 334 tokens/s, exit 0 | 5 s |
| Intel, AMX enabled | delphi-3bda | unset | yes | `arch_prctl(0x1023, 18) = 0` | CPU | 29 tokens, 232 tokens/s, exit 0 | 6 s |
| Intel, kill switch | delphi-3bda | `1` | yes | none | CPU | 29 tokens, identical to the Intel enabled arm, 229 tokens/s, exit 0 | 6 s |

Wall time includes model loading from a warm file cache; the 13 s of the first AMD run includes the creation of the hugepage slice files. The two machines' speeds are not comparable and were not the point.

### What the results mean

On the AMD machine with AMX enabled, the shim was loaded and recorded no permission call. The probe therefore stopped before the request, which in the code can only be the CPUID check, and returned false. The dispatch site tests `amx_eligible && available()` before every use of the kernels, so the AVX kernels handled every attention page. The Intel control removes the alternative explanation that the method misses the call: with the same binary settings, model, prompt and environment, the call appeared exactly once on Intel, and it disappeared again when the kill switch was set. Two further observations are consistent. The AMD run completed normally, whereas executing an AMX tile instruction on this CPU would have raised an illegal-instruction fault. And the AMD run's tokens are byte-identical to the kill-switch run's. That identity is supporting evidence only: the Intel pair was identical too over 29 tokens, so identical tokens do not by themselves show which path ran.

### Side effects and clean-up

tron claims the hugepage slice files of its half at start-up. A stale 16 GiB file `slice-4-of-8`, owned by another user since 2026-09-03 and held open by nobody, was adopted and shrunk to 4 GiB; it kept its owner and was left in place. The three files this test created were removed after the runs, leaving 276 of the machine's 280 one-gigabyte hugepages free. The Intel control's four slice files were removed as well. No runtron process or statistics mount remained on either machine. The AMD build directory `gen-amd` stays under the shared home directory for reuse.

### Files

| Path (under `~/workspace/intel-AMX/exec/`) | Content |
|---|---|
| `amd-amx-20260911/amxprobe.c` | the LD_PRELOAD shim source |
| `amd-amx-20260911/run-andoria06.sh` | the run script (both arms, binary checks, token comparison) |
| `logs/amd-amx-20260911/andoria-06-{on,off}.{log,probe,tokens}` | AMD run logs, shim records, generated tokens |
| `logs/amd-amx-20260911/3bda-{on,off}.{log,probe,tokens}` | Intel control logs, shim records, tokens |
| `logs/amd-amx-20260911/andoria-06-run.txt` | console record of the AMD runs |
| `logs/andoria06-amd-build-20260911.log` | build log |
