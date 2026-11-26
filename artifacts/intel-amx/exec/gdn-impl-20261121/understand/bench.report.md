# Stand-alone benchmarks, clock probe, run recipe and prediction numbers for the GDN/AMX plan (tasks 1 to 6)

## Short version

- The stand-alone benchmark `bench_gdn.c` already holds the three task-1 cases (today's order at 128 KiB, column-half order in contiguous 32 KiB halves, one 32 KiB slice alone). It is single-thread only and it has never run on delphi-3b35: its three saved outputs come from the agent server (AMD Ryzen 9 9950X guest).
- The clock probe does not read a frequency counter itself. The calling shell script samples `/sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq` every 0.25 s while one loop runs for 4 s (no root). The same method works for a new AMX kernel if the kernel runs alone in one process for seconds.
- `predictions.json` gives TTFT per cell for 5 scenarios at 3 levels. The pass rules use the unrounded low and high TTFT fall as a percent of the base run (tables in section 4). `collect.py`, `predict.py` and `campaign.sh` hard-code two arms named `on`/`off`, one results folder and one build tag per campaign, so they need changes before they can compare base, Part 0, Part A, Part B and A+B.

Path shorthands used below:

- `C` = `/home/jhan/workspace/intel-AMX/exec/gdn-20261120`
- `VC` = `C/design-checks/verify-cost`
- `R` = `/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120`
- `W` = `/home/jhan/workspace/ai-runs/tron-qwen35-4b` (read-only tron worktree, commit 72e1191804)
- `DESIGN` = `/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/design.txt`

Nothing was run on the server. No file was changed.

---

## 1. What the existing sources time, and how

### 1.1 `VC/bench_gdn.c` (580 lines, plain C, single thread)

**Host and build.** It is a re-implementation, not tron code (`bench_gdn.c:1-4`). Build line in the source: `gcc -O3 -march=native -o bench_gdn bench_gdn.c -lm` (`bench_gdn.c:10`). Arguments: `argv[1]` = CPU to pin to (`sched_setaffinity`), `argv[2]` = `rounds_scale` multiplier (`bench_gdn.c:277-284`). The banner is hard-coded: `printf("host: design host, KVM guest on AMD Ryzen 9 9950X (Zen 5). NOT the Xeon 6962P.\n")` (`bench_gdn.c:557`). This session confirmed the agent server is that host (`hostname` = claude-agentsrv, `/proc/cpuinfo` model name AMD Ryzen 9 9950X, gcc 11.4.0).

**Timer.** `clock_gettime(CLOCK_MONOTONIC_RAW)` in ns (`bench_gdn.c:25-29`). Each row keeps the LOWEST time over many interleaved rounds (`upd()`, `bench_gdn.c:257-259`).

**Core clock.** `calib_tick()` times two dependent chains of 1,500,000 instructions: `imul` (3 cycles each) and scalar `vfmadd213sd` (4 cycles each). It keeps the HIGHEST GHz reading of the whole run in `g_ghz` (`bench_gdn.c:31-50`). Cycles per row = ns x `g_ghz` (`bench_gdn.c:561`). The rule is written for a shared guest whose clock moves between 1.5 and 5.3 GHz (`bench_gdn.c:32-34`).

**Sizes.** `KD 128` key rows, `VD 128` value columns, `NCH 8` zmm chunks per state row (`bench_gdn.c:21-23`). One value head = 128 x 128 FP32 = 64 KiB. `POOL 128` tokens = one prefill chain (`bench_gdn.c:240`).

**Inputs.** xorshift generator with a fixed seed (`bench_gdn.c:53-59`). K and Q are pre-normalized and rounded to bf16, Q is pre-multiplied by `1/sqrt(128)`; V is rounded to bf16; decay in 0.9..1.0, beta in 0.3..0.7 rounded to bf16 (`bench_gdn.c:287-312`). So rows (1) and (2) time the two recurrence loops only. They do NOT include normalization, decay, beta (the "prelude", timed apart in section 3) and no convolution.

**State layouts.**

- Standard: `S[h][i][c]`, chunk c of key row i at `S + i*VD + c*16` (same as tron, `W/h/tron/kernels/gated_delta_net.hpp:211`).
- Blocked: `[value head][8 value blocks][128 key rows][16 floats]`, chunk c of row i at `Sl + (c*KD + i)*16` (`bench_gdn.c:98-107`, converters `to_blocked` / `to_standard` at `bench_gdn.c:261-274`). One column half = 4 consecutive value blocks = 4 x 128 x 64 B = 32 KiB contiguous. The 4 chunks of one key row sit exactly 8,192 B apart.

**Kernels.**

- `token_step()` (`bench_gdn.c:69-96`): today's order. Loop 1 over 128 key rows x 8 chunks (`ds = S*decay; r = fma(k, ds, r)`), then delta, then loop 2 (`ns = fma(k, delta, S*decay); store; res = fma(q, ns, res)`). It mirrors `gated_delta_net.hpp:266-297`.
- `slice_step()` (`bench_gdn.c:102-141`): the same operations on 4 chunks (64 columns). `slice_window()` (`bench_gdn.c:142-148`) runs `ntok` tokens on one slice. Note the statement order in loop 2: 4 loads and FMAs, then 4 stores, then 4 FMAs (`bench_gdn.c:123-134`). tron's order is per chunk: load, fma, store, fma (`gated_delta_net.hpp:288-293`).
- Section 4 has the AVX-512 parts of the proposed AMX block kernel at C = 32: `split_pack_block()` (3-piece truncation split with mask `0xffff0000`, pair-interleaved pack into a 12 KiB scratch `[key block 4][piece 3][16 rows][64 B]`, `bench_gdn.c:178-203`), `triangle()` (`bench_gdn.c:205-231`) and the final `S = fma(gamma, S, T)` (`bench_gdn.c:538-551`). No tile instruction is in the file.

**Rows and their divisors.**

| Row | Code | What is timed | Unit |
|---|---|---|---|
| (1) token loop, H = 1, 2, 8, 16, 32 heads cycled (64 KiB to 2,048 KiB) | `bench_gdn.c:314-341`, 40 x scale rounds | all H heads stepped per token, 128 tokens | ns / (POOL x H) |
| (2) token loop, one key-head group | `bench_gdn.c:393-400`, 60 x scale rounds | 2 value heads = 128 KiB working copy, chain of 128 tokens | ns / (POOL x 2) |
| (2) slice replay G1, layout standard or blocked, window 32 / 128 / 8 | `bench_gdn.c:401-419` | per window, per head, per half: `slice_window` | ns / (POOL x 2) |
| (2) one 32 KiB slice held in L1 | `bench_gdn.c:433-437` | `slice_window(Sblk, 1, POOL, ...)` on half 0 of head 0 | 2 x ns / POOL |
| (2) layout conversion in + out | `bench_gdn.c:438-442` | `to_blocked` + `to_standard` of 2 heads | ns / (POOL x 2) |
| (3) prelude | `bench_gdn.c:449-475` | normalize one 128-wide vector; decay + beta | ns per call |
| (4) split + pack, triangle, final fma | `bench_gdn.c:477-554`, 200 x scale rounds | AVX-512 parts of the block kernel | ns / (H x C) or / C |

- The state reset (memcpy or `to_blocked`) is outside the timed region (`bench_gdn.c:405-409`).
- Round 0 compares outputs and final state with the token loop by `memcmp` (`bench_gdn.c:420-431`). All 6 slice variants print "IDENTICAL (outputs and state)".
- "Window" = tokens run on one half before the next half. Window 128 with the blocked layout is the Part 0 order of DESIGN section 5.2.

**Saved outputs (ns per token per value head; all on the AMD host).**

| Row | run1 (cpu 5, 5.249 GHz) | cpu21 (5.274 GHz) | cpu9 (5.249 GHz) |
|---|---|---|---|
| (1) 64 / 128 / 512 / 1024 / 2048 KiB | 922.2 / 843.7 / 845.3 / 1042.4 / 1239.7 | 1027.1 / 894.1 / 1001.1 / 1805.3 / 1562.8 | 995.4 / 884.9 / 755.4 / 1140.2 / 1390.3 |
| (2) token loop today, 128 KiB | 817.7 | 740.4 | 863.1 |
| (2) standard, window 32 / 128 / 8 | 806.2 / 681.9 / 733.9 | 693.2 / 561.7 / 564.9 | 710.2 / 650.2 / 680.0 |
| (2) blocked, window 32 / 128 / 8 | 513.7 / 506.9 / 529.9 | 508.3 / 507.0 / 525.4 | 505.9 / 494.7 / 520.9 |
| (2) one 32 KiB slice in L1 (x2) | 509.7 | 515.2 | 503.8 |
| (2) layout conversion | 8.3 | 8.8 | 10.3 |
| (3) normalize / decay + beta | 34.3 / 15.0 | 36.3 / 15.9 | 34.3 / 14.8 |
| (4) split / triangle / final | 23.8 / 34.8 / 13.0 | 24.7 / 34.2 / 10.5 | 24.0 / 34.1 / 11.1 |
| token loop 128 KiB / blocked window 128 | 1.61x | 1.46x | 1.74x |
| token loop 128 KiB / one slice in L1 | 1.60x | 1.44x | 1.71x |
| cycles per L2 line (derived) | 0.79 | 0.58 | 0.92 |

Files: `VC/bench_gdn.run1.out`, `VC/bench_gdn.run_cpu21.out`, `VC/bench_gdn.run_cpu9.out` (34 lines each). The values 1.46 and 1.74 are the source of the low case of Part 0 (`C/design_numbers.py:53-69`, `C/predict.py:60-61`).

**What an extension for task 1 needs.**

- Today's kernel order at a 128 KiB working copy: exists, row "(2) token loop today, one key-head group" (`r_tok`).
- Column-half order on contiguous 32 KiB halves: exists, row "(2) slice replay G1, blocked layout, window 128 tokens" (`r_sl[1][1]`).
- Recurrence on one 32 KiB slice alone: exists, row "(2) one 32 KiB slice held in L1" (`r_l1`).
- 16 threads: not in the file. It needs pthreads (or 16 pinned processes), one private 128 KiB state plus inputs per thread, and a start barrier.
- The banner, the host comments (`bench_gdn.c:6-8`, `557`) and the clock rule must change for delphi-3b35.
- `_mm512_cvtneps_pbh` (`bench_gdn.c:152`) needs AVX512_BF16 in the compile flags.

### 1.2 `VC/calib.c` and `VC/alias_test.c`

- `calib.c` cross-checks the clock calibration with four dependent chains (imul 3 cycles, 8 adds 8 cycles, scalar FMA 4 cycles, load chain 4 cycles), 20,000,000 iterations, best of 5, 3 repetitions (`calib.c:12-35`). Output `VC/calib.out`: 4.64 to 5.22 GHz. The first line of `calib.out` and of `alias_test.out` is a `/proc/loadavg` line of the AMD host (`24.08 25.31 29.56 ...`).
- `alias_test.c` times loop 2 only on one 32 KiB slice, in tron's statement order with a memory barrier after each store (`alias_test.c:18-32`), with block stride 128 lines (chunks 8,192 B apart, 4K-aliased) and 129 lines (not aliased), lowest of 400 rounds of 64 calls (`alias_test.c:42-55`). Result on the AMD host: 153.1 ns against 153.4 ns, ratio 1.00x (`VC/alias_test.out:3-5`). No Intel result exists.
- `VC/l1_check.out:2-5`: L1 model, lines from outside L1 per token: standard layout 2,048 state lines; blocked layout 32 (window 32) or 8 (window 128); inputs 48.

### 1.3 `C/clock_probe.cpp` (177 lines)

**What it measures.** One-core loops, each run alone for `--seconds S` (default 4.0) on `--cpu C` (`sched_setaffinity`, `clock_probe.cpp:82-96`). Modes (`--only`):

| Mode | Loop | Code |
|---|---|---|
| `fma` | 64 AVX-512 FP32 FMAs per block, 8 register accumulators x 8 rounds | `clock_probe.cpp:46-58`, `148-150` |
| `tdp` | 4 `_tile_dpbf16ps` into tiles 0..3, live 512-bit registers | `clock_probe.cpp:151-153` |
| `mix` | 4 tile products, then 64 FMAs, repeated | `clock_probe.cpp:155-158` |
| `tdpz` | tile products only, after `_mm256_zeroupper()` | `clock_probe.cpp:61-67`, `120` |
| `mixz` | 1 x (4 tile products) then 64 FMAs with memory accumulators and a zeroupper, repeated | `clock_probe.cpp:72-80`, `122` |
| `mixzp` | 1,024 x 4 = 4,096 tile products, then 256 x 64 = 16,384 FMAs, repeated | `clock_probe.cpp:124-127` |

**What the program reads.** Only `clock_gettime(CLOCK_MONOTONIC)` (`now_s`, `clock_probe.cpp:27-31`) and `__rdtsc()` (`clock_probe.cpp:116`, `131`, `144`, `163`). It prints wall seconds, `tsc_hz` (ticks / wall), ns per instruction and TSC ticks per instruction. It reads no MSR, no perf counter, no sysfs file. The header says so: "The caller samples /sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq while a loop runs" (`clock_probe.cpp:7`).

**AMX setup in the program.** `syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM /*0x1023*/, XFEATURE_XTILEDATA /*18*/)`, then `_tile_loadconfig` with palette 1, 8 tiles of 16 rows x 64 bytes, `_tile_loadd`, `_tile_zero`, and `_tile_release` at the end (`clock_probe.cpp:22-25`, `98-109`, `132-133`).

**How the core clock is read (the scripts).** `C/clock-probe.sh:24-40`:

```
F=/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_cur_freq
( while :; do cat "$F" >>"$samples"; sleep 0.25; done ) & local sp=$!
local line; line=$("$@" 2>&1 | tail -1)
... med=$(tail -n +5 "$samples" | sort -n | awk ...)   # drop the first 4 samples (1 s ramp), median of the rest
```

- No root is needed (`clock-probe.sh:7`). jhan has no sudo on delphi-3b35, and perf, turbostat and rdmsr are not usable there (memory note `delphi-3b35-default-server.md:47-49`).
- Cross-check without the sysfs file: the TSC runs at a constant 2.70 GHz (`tsc_hz 2699997283`), and the cycle cost of the instruction is known. So clock = cycles per instruction / ns per instruction, with 16.2 cycles per TDPBF16PS and 2.01 cycles per VDPBF16PS (`clock-probe.sh:10-11`).
- The helper keeps only the LAST output line of the program (`tail -1`).
- `clock-probe3.sh:21` drops 3 samples (not 4) of a 2 s loop.

**To read the clock while a new AMX kernel runs:** give the kernel benchmark the same interface (one mode per process, `--cpu`, `--only`, `--seconds` of 4 or more, one result line printed last) and call it through the `run()` function of `clock-probe.sh:30-40`. Cycles per item = ns per item x sampled GHz.

### 1.4 Results under `R/bench/` (3 files, no JSON)

`R/bench/clock-probe.txt` (23 lines, 2026-11-20T18:14:54Z, cpu 140, driver intel_pstate, governor performance, base 2,700,000 kHz, max 4,400,000 kHz, idle reading 800,000 kHz):

| Label | freq median (kHz) | Result |
|---|---|---|
| fma-1/2/3 | 2,700,000 | 0.2269 / 0.2269 / 0.2268 ns per FMA, 0.6126 ticks |
| tdp-1/2/3 | 1,895,498 / 1,895,857 / 1,895,607 | 8.5332 / 8.5362 / 8.5354 ns per TDPBF16PS, 23.04 ticks |
| mix-1/2/3 | 1,895,506 / 1,895,478 / 1,895,479 | 34.151 / 34.152 / 34.156 ns per round (4 tile products + 64 FMAs), 92.21 ticks |
| insn-vdp_tp16 | 2,700,000 | 0.7453 ns, 2.012 ticks per VDPBF16PS |
| insn-tdp_tp | 2,396,157 | 6.7310 ns, 18.174 ticks |
| insn-tdp_lat | 2,396,106 | 6.7319 ns, 18.176 ticks |
| insn-tld_l1 | 2,700,000 | 3.1031 ns, 8.378 ticks per TILELOADD |
| gdn-recurrence-1/2/3 | (not sampled) | mean 97.7555 / 99.5224 / 97.9121 us per step of 32 value heads (2 MiB state) |
| gdn-conv-1/2/3 | (not sampled) | mean 7.91788 / 8.00054 / 8.07028 us per step of 8,192 channels |

- Median recurrence 97.9121 us / 32 = 3.06 us per value head; convolution 8.00 us / 16 = 0.50 us per key head (`C/design_numbers.py:36-50`, `C/gen_design.py:135-137`).

`R/bench/clock-probe2.txt` (12 lines, cpu 140): fma 2,700,000 kHz, 0.2271 ns; tdpz 2,396,136 / 2,396,106 kHz, 6.7333 / 6.7328 ns per tile product; tdp 1,895,509 / 1,896,254 kHz, 8.5345 / 8.5353 ns; mixz 1,895,445 / 1,895,391 kHz, 8.8152 / 8.8139 ns total per tile product; mixzp 2,400,000 kHz, 8.0536 / 8.0409 ns total per tile product.

`R/bench/clock-probe3.txt` (31 lines, FMA loop of 2 s on 29 CPUs): 26 CPUs read 2,700,000 kHz (0.2272 to 0.2294 ns per FMA). CPU 108 reads 4,000,000 kHz (0.1534 ns), CPU 109 4,000,000 kHz (0.1533 ns), CPU 126 3,993,856 kHz (0.1536 ns). Probed CPUs: 96 97 100 101 102 107 108 109 110 111 113 119 120 125 126 131 132 137 138 140 143 223-230 (`C/clock-probe3.sh:15`).

---

## 2. How things were compiled and run on delphi-3b35

**bench_gdn.c, calib.c, alias_test.c: not run on delphi-3b35.** No script in `C` builds or runs them (search for `bench_gdn` in the `.sh` files: not found). Their outputs are from the AMD host.

**Clock probes (run ON delphi-3b35).**

- `clock-probe.sh:22`: `g++ -O2 -std=c++17 -march=x86-64-v4 -mamx-tile -mamx-bf16 clock_probe.cpp -o /var/tmp/jhan/gdn-probe/clock_probe`.
- `clock-probe.sh:23`: `g++ -O3 -std=c++17 -march=x86-64-v4 -mavx512bf16 -mamx-tile -mamx-bf16 exec/perf-model-20260903/src/insn_loops.cpp -o /var/tmp/jhan/gdn-probe/insn_loops`.
- `clock-probe2.sh:17`: same source and flags, binary name `clock_probe2`. `clock-probe3.sh:13` reuses `clock_probe2`.
- CPU: `CPU=${CPU:-140}` (`clock-probe.sh:14`). The program pins itself (`--cpu`); no `taskset` for it. The sampler subshell is not pinned.
- Guards: `[ "$(hostname)" = delphi-3b35 ]` and `pgrep -u "$(id -u)" -f '/gen/runtron '` refuses when one of our runtron processes runs (`clock-probe.sh:20-21`).
- The tron kernel benchmark is run from inside the build worktree with taskset (`clock-probe.sh:50-55`): `( cd /var/tmp/jhan/b35-gdn-base && SYSTEM_CONFIG="--instance 1,2" taskset -c "$CPU" gen/t_gated_delta_net "GatedDeltaNet recurrence step at the Qwen head geometry" --benchmark-samples 300 )`. Benchmark source: `W/t/t_gated_delta_net.cpp:1227-1274` (16 key heads, 32 value heads, 128 x 128, 2 MiB heap state, one `run_recurrence` call per sample) and `:599` (convolution).
- The clock-probe scripts take NO load snapshot.
- g++ version on delphi-3b35: not found in any saved file.

**tron build (`C/build-3b35.sh`).**

- Compiler: clang-19 / clang++-19 with ccache; `R/build-base.txt` records "Ubuntu clang version 19.1.7".
- Configure: `cmake --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DDEV_MODEL_CONFIG=$WT/models.gdn.yaml -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache` (`build-3b35.sh:29`, `61`). Build type RelWithDebInfo.
- CPUs: `PIN="nice -n10 taskset -c 96-143"`, `-j40` (`build-3b35.sh:27-34`).
- Worktree: `/var/tmp/jhan/b35-gdn-$TAG`, created with `git -C /home/jhan/workspace/tron worktree add --detach` at `SHA` (default 72e1191804ecb7591b23230439786a6a1ca784b8). The script fails if the worktree HEAD is not `SHA` (`build-3b35.sh:44-49`). `TAG` must be lowercase alphanumerics (`build-3b35.sh:37`).
- Targets: `runtron t_gated_delta_net` (`build-3b35.sh:30`). Dependencies: `make TOKENIZER_PYTHON_VERSION=3.12.7 ingest-deps` and `gen/tokenize_py`, PATH `/tools/uv/0.9.5:$HOME/.ghcup/bin` (`build-3b35.sh:53-60`).
- Post-checks: count of `tdpbf16ps` in `gen/runtron` above 0 (base build: 32), `TRON_ATTN_STATS` literal, model slug (`build-3b35.sh:70-86`). Outputs `R/build-$TAG.txt` and `R/build-$TAG.done`. The base build took 707 s.

**Load snapshot script:** `/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh` (108 lines, read-only, no root, 10 s sample plus about 2 s). Defaults `OUR_APP=96-143,223-230`, `OUR_DEV=75-78`, `OUR_NODE=1` (`load-snapshot.sh:19-22`). Section 2 prints `socket0`, `socket1`, `our-app-cores`, `our-dev-cores` with busy percent. `run-one.sh:54-59` calls it and parses those lines.

**Machine facts that matter for a benchmark.** L1d 48 KiB 12 ways 64 sets, L2 2 MiB 16 ways, 2 threads per core, node 1 CPUs 72-143 and 216-287 (`exec/3b35-inspect-20261112/cpu-firmware-delphi-3b35-lscpu-C.txt`, `...-topology.txt`). tron's app CPU list for instance 1,2: `223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143` (`R/rt-results.txt:5`).

---

## 3. Run recipe and how the values are extracted

### 3.1 One run: `C/run-one.sh`

- Inputs by environment: `RUN` (required), `MODEL` (default `ingested-qwen-3.5-4b-tp4`), `USERS`, `PROMPT`, `LEN` (256), `ARMENV` (default `TRON_ATTN_STATS=1`, note `${ARMENV-...}` without colon), `EXTRA`, `TAG` (binary `/var/tmp/jhan/b35-gdn-$TAG/gen/runtron`), `TMO` (2400 s), `NAME` (results folder) (`run-one.sh:23-36`).
- Skip rule: `grep -q "average tok/s" "$rlog" && ... already done; exit 0` (`run-one.sh:43`). Lock `/var/tmp/jhan/$NAME.run.lock` (`run-one.sh:44-45`).
- Load snapshot first, into `R/load/$RUN.txt`. Refusals (exit 3): one of our cards `0000:90:00.0 93 b9 bc` already open, or our app cores above 5.0 % busy (`run-one.sh:54-63`).
- Command (`run-one.sh:70-71`): `( cd "$WT" && env -u TRON_AMX_DISABLE -u USE_HW_ATTN SYSTEM_CONFIG="--instance 1,2" $ARMENV TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug timeout -k 60 "$TMO" "$BIN" stream-generate-text -m "$MODEL" -o --prompt-length "$PROMPT" -l "$LEN" -u "$USERS" --dont-stop $EXTRA )`.
- Outputs: `R/rt/$RUN.log`, a block in `R/rt-results.txt` (header `### run=... armenv=[...] bin=... tip=...`, a `load:` line, the grep lines, `RUN-OK`), and removal of our unmapped huge page files.

### 3.2 Campaign: `C/campaign.sh`

- 6 cells `key|model|users|prompt|len` (`campaign.sh:28-33`): `q35-tp4-{1u,8u}-p{1024,4096,8192}`, 256 generated tokens.
- Arms: `ARMS="on off"`, `ARM_ENV_on="TRON_ATTN_STATS=1"`, `ARM_ENV_off="TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"` (`campaign.sh:25-27`). Arm environments are looked up by name (`arm_env`, `campaign.sh:44`), so other arm names work in this script.
- Run name `<key>__<arm>__rep<N>` (`campaign.sh:52`). The arm order is reversed on even repetitions (`campaign.sh:47-48`). `sleep 5` between runs. 3 consecutive failed runs end the campaign (`campaign.sh:59`).
- One `TAG` and one `NAME` for the whole invocation (`campaign.sh:18-19`). The run name does not contain the tag.
- The 2026-11-20 baseline: 3 repetitions x 2 arms = 6 runs per cell, 36 runs, all `RUN-OK`. Load in every run: socket 0 43.1 to 43.2 % busy (another team), socket 1 at most 0.2 %, our app cores at most 0.2 % (`R/rt-results.txt` `load:` lines).

### 3.3 Leaves: `C/poll-leaves2.sh`

Per-layer and per-worker statistics exist only in the FUSE files. The poller copies `$WT/stats/.../attention/*` once per second into `R/leaves/<run>/` while one of our runtron processes runs, and keeps a snapshot only when `decode_like_forwards` holds `"forwards":[1-9]` (`poll-leaves2.sh:24-35`). Files per run: `summary`, `{decode_like,prompt_or_mixed}_{forwards,totals}`, 32 `_layer_N`, 55 `_worker_N`.

### 3.4 Traces: `C/trace.sh`

- Cells `key|users|prompt|len|passes` (`trace.sh:21-24`): `t-1u-p1024|1|1024|32|1-48`, `t-8u-p1024|8|1024|32|1-48`, `t-1u-p8192|1|8192|32|1-104`, `t-8u-p8192|8|8192|32|1-104`. The two p4096 traces were run with an override that is in no file; `R/rt-results.txt:831,841` shows `--trace-passes 1-72`, len 32.
- Run: `ARMENV="TRON_ATTN_STATS=1 TRON_TRACE_CATEGORIES=-*,+model,+scheduler"`, `EXTRA="--trace-gen $tracef --trace-passes $passes"`, through `run-one.sh` with `RUN=trace-$key` (`trace.sh:40-42`). Trace written to `/var/tmp/jhan/traces/$NAME/` and copied to `R/trace/`.
- A traced run generates 32 tokens and is slower: decode steps 3.0 to 27.9 % longer, prefill passes 0.2 to 3.1 % longer (`C/design-checks/review/r6_traced_vs_untraced.out:64-66`).

### 3.5 `C/collect.py` (run on the agent server, reads the NFS folder; `RES` hard-coded at line 21)

- TTFT: regex `Request with (\d+) tokens in and (\d+) out .* saw ([\d.]+) s TTFT and ([\d.]+) s TTLT` per user (`collect.py:35-37`). `ttft_max` = slowest user, `ttft_mean` (`collect.py:132`).
- Decode: regex `Generating (\d+) response tokens with (\d+) context took ([\d.]+) s at ([\d.]+) average tok/s` per user; `tps_mean` = mean over users, `tps_sum` (`collect.py:29-31`, `131`).
- Attention statistics: `[attn-stats] model \S+: {json}` -> `attn.summary`; `[attn-stats] (decode_like|prompt_or_mixed)\S* (totals|forwards): {json}` (`collect.py:38-43`).
- `derive()` per class (`collect.py:78-109`), with `hz = summary.tsc_hz`, `n = forwards.forwards`:
  - `forward_wall_ms = wall_cycles / n / hz * 1e3` (T1),
  - `attn_busy_cpu_ms_per_forward = totals.busy_cycles / n / hz * 1e3` (T2, summed over workers),
  - `attn_join_wait_cpu_ms_per_forward = totals.join_wait_cycles / n / hz * 1e3` (T5),
  - `attn_w0_wall_ms_per_forward = totals.wall_cycles_w0 / n / hz * 1e3` (T3),
  - `attn_workers = forwards.n_attn_workers_max` (40), `amx_k_tokens = ready_amx_k_tokens + pending_amx_k_tokens`, token jobs and visit counts.
- Run name parse: `re.match(r"(?:trace-)?(.*?)(?:__(on|off)__rep(\d+))?$", run)` (`collect.py:117`). Runs without an arm or traced runs are left out of `cells` (`collect.py:136-137`).
- Aggregate per cell and arm: `{"values", "median", "min", "max", "n"}` for `decode_tps_per_user` (from `tps_mean`), `decode_tps_all_users`, `ttft_max_s`, `ttft_mean_s`, and every derived number (`collect.py:144-158`).
- Output `R/collected.json`, top keys `runs` (43), `cells` (6), `traces` (6, from `trace/*.summary.json`), `bench` (empty: no JSON in `bench/`).

### 3.6 `C/analyze_trace.py` (usage `analyze_trace.py <trace file> <users>`, needs the `perfetto` Python module, present on the agent server under `~/.local/lib/python3.10`)

- A pass = slice named `forward`. Kind: `decode` when token jobs <= users, else `prefill` (`analyze_trace.py:46-66`).
- The first pass of each kind is skipped when the kind has more than 2 passes (`analyze_trace.py:80-81`).
- GDN slices: name `GatedDeltaNet` with argument `operation` (`analyze_trace.py:70-74`). tron emits one slice per worker thread and operation: `TRACE_EVENT("model", "GatedDeltaNet", "operation", ..., "chains", chains.size())` (`W/h/tron/models/gdn_execution.hpp:110-111`).
- GDN wall: for each (pass, operation) the time from the earliest slice start to the latest slice end over all threads; summed and divided by the passes used: `wall_span_ms_per_pass` (`analyze_trace.py:107-109`, `139-145`). `predict.py:176-177` uses this value as `gdn_ms`.
- Mean step: `cpu_us_per_group_step = sum of all GDN slice time / passes / (16 x token jobs per pass x operations)` (`analyze_trace.py:152`).
- Step per thread: `steps_per_thread_per_pass = 16.0 * jobs_per_pass * n_ops / n_thr`; `per_thread_step_us[thread name] = thr_gdn[utid] / n / 1e3 / steps_per_thread_per_pass` (`analyze_trace.py:155-162`). With 16 threads and 24 operations this is 128 x 24 = 3,072 steps per thread per pass with 1 user and 24,576 with 8 users. One step = one token of one key-head group (convolution, normalization, 2 value-head recurrences, norm, output gate).
- Outputs `slowest_thread_step_us`, `median_thread_step_us`, and `<trace>.summary.json`.

### 3.7 The "GDN step on a 2.70 GHz thread"

- Value today: `STEP_TODAY = 6.4  # us, GDN step on a 2.70 GHz thread in prefill (trace: 14 of 16 threads, 6.32 to 6.49)` (`C/design_numbers.py:23`).
- Thread names carry the CPU: `fmt::format("{:3d}/{}", core_id, fmt::format("{:x}", ccx_id))` + `-` + base name (`W/src/system/system.cpp:892-904`); the main thread is `"%d/?-work_queue"` (`W/h/tron/scheduler/work_queue.hpp:447`). The 16 GDN threads are `96/?-work_queue` and ` 97/1-worker` ... `111/1-worker`, so CPUs 96 to 111. 16 = 1 main + (55 x 2) / 7 = 15 main helpers (`W/h/tron/models/model.hpp:2526-2528`); pool workers take ascending CPUs (`W/h/tron/threading.hpp:646-652`).
- The 2.70 GHz threads are the 14 threads NOT on CPUs 108 and 109. `clock-probe3.txt` reads 4.00 GHz on CPUs 108, 109 and 126.
- Measured per cell (prefill, us per step, `R/predictions.json` `prefill.gdn_per_thread_us`): 14 threads 6.320 to 6.492; CPU 108 3.788 to 3.804; CPU 109 3.939 to 3.998; median thread 6.397 to 6.435; slowest 6.441 to 6.492; mean over 16 threads 6.083 to 6.117. Decode: median 13.60 to 16.08, mean 13.38 to 16.10.
- The page generator separates the two groups by a time threshold, not by CPU: `thr_fast = [v for v in thr_pf if v < 5.0]` (`C/gen_design.py:108-113`).

---

## 4. Prediction numbers

### 4.1 Formula (`C/predict.py:25-38`, code at `207-221`)

```
d_pf  = gdn_pf * (1 - 1/s_gdn)                         # if the scenario has a GDN factor
      + attn_full_pf * (1 - 1/s_attn_prefill)          # if attention is on
      - attn_other_pf * tax_attn_other                 # if attention is on
      - rest_pf * tax_rest_amx_gdn                     # if the scenario is amx_gdn or amx_both
d_dec = attn_dec * (1 - 1/s_attn_decode)               # if attention is on, else 0
t1_prefill_ms = t1_pf - d_pf
ttft_s        = ttft - passes * d_pf / 1e3
tps           = 1000.0 / (1000.0/tps - d_dec)
t1_decode_ms  = t1_dec - d_dec
```

- `rest_pf = t1_pf - gdn_pf - attn_pf`; `attn_other_pf = attn_pf - attn_full_pf - join_pf` (`predict.py:178-180`).
- `attn_pf` = median of `attn_busy_cpu_ms_per_forward` / 40 workers. Medians pool the runs of both arms (`predict.py:149-158`).
- `attn_full_pf` = slope x ready K tokens per pass, from a least-squares line of (busy - join wait) against K per user count (`predict.py:112-135`). Recomputed here: 1 user slope 1.6735997598674427e-06 ms per K token and worker (66.944 ns of CPU time per K token over 40 workers), intercept 1.5330 ms; 8 users slope 1.669062807384128e-06 (66.763 ns), intercept 6.4490 ms. Ready K tokens per pass: 1,835,008 / 8,126,464 / 16,515,072 (1 user) and 14,680,064 / 65,011,712 / 132,120,576 (8 users).

Scenarios (`predict.py:89-95`):

| Scenario key | Meaning | GDN factor | Attention on | Clock cost on the rest |
|---|---|---|---|---|
| `reorder` | Part 0 | `s_gdn_reorder` | no | no |
| `amx_gdn` | Part A (replaces Part 0) | `s_gdn_amx` | no | yes |
| `amx_attn` | Part B on today's GDN | none | yes | no |
| `reorder_attn` | Part 0 + Part B | `s_gdn_reorder` | yes | no |
| `amx_both` | Parts A and B | `s_gdn_amx` | yes | yes |

### 4.2 ASSUMPTIONS table (`predict.py:57-80`, identical in `R/predictions.json` `assumptions`)

| Factor | lo | mid | hi |
|---|---|---|---|
| `s_gdn_reorder` | 1.4 | 2.1 | 2.4 |
| `s_gdn_amx` | 2.0 | 3.2 | 3.7 |
| `s_gdn_decode` | 1.0 | 1.0 | 1.0 |
| `s_attn_prefill` | 1.6 | 2.3 | 2.9 |
| `s_attn_decode` | 0.9 | 1.0 | 1.17 |
| `tax_rest_amx_gdn` | 0.088 | 0.026 | 0.0 |
| `tax_attn_other` | 0.421 | 0.421 | 0.125 |

Implied GDN step on a 2.70 GHz thread (6.4 us / factor): Part 0 4.571 / 3.048 / 2.667 us; Part A 3.200 / 2.000 / 1.730 us.

### 4.3 Structure of `R/predictions.json`

`{"assumptions": {...}, "cells": {cell: {"users", "prompt", "samples", "prefill": {...}, "decode": {...}, "pred": {"lo"|"mid"|"hi": {scenario: {"t1_prefill_ms", "ttft_s", "tps", "t1_decode_ms"}}}}}}`

- `prefill` keys: `t1_ms, gdn_ms, attn_ms, attn_t3_ms, attn_wait_ms, attn_full_ms, attn_join_ms, attn_other_ms, rest_ms, passes, gdn_step_slow_us, gdn_step_median_us, gdn_per_thread_us, gdn_trace_share_pct, ttft_s, ttft_min_s, ttft_max_s, trace_pass_ms, gdn_step_us, gdn_cpu_ms`.
- `decode` keys: `t1_ms, gdn_ms, attn_ms, attn_t3_ms, attn_wait_ms, attn_join_ms, rest_ms, gdn_step_slow_us, gdn_step_median_us, gdn_per_thread_us, gdn_trace_share_pct, tps, tps_min, tps_max, ms_per_token, trace_pass_ms, gdn_step_us, gdn_cpu_ms`.
- The predicted GDN wall and the predicted attention busy time are NOT stored; only the four `pred` fields are.

### 4.4 Measured base values of 2026-11-20 (inputs of the prediction; 6 runs per cell)

Prefill, per pass (ms; attention values per attention worker):

| Cell | TTFT median s (min to max) | passes | pass wall T1 | GDN wall (trace) | attn busy | full-page | join wait | other attn | rest | T3 worker 0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1u p1024 | 0.3846585 (0.381452 to 0.385051) | 8 | 47.96524 | 20.32602 | 6.03798 | 3.07107 | 1.44877 | 1.51814 | 21.60125 | 8.62067 |
| 1u p4096 | 1.8971165 (1.895002 to 1.910843) | 32 | 59.14540 | 20.25693 | 17.28466 | 13.60045 | 2.12507 | 1.55914 | 21.60381 | 19.63351 |
| 1u p8192 | 4.7061145 (4.696053 to 4.709280) | 64 | 73.38280 | 20.16536 | 31.44486 | 27.63962 | 2.28337 | 1.52187 | 21.77258 | 33.83657 |
| 8u p1024 | 2.9073365 (2.899501 to 2.912990) | 8 | 362.18018 | 160.40192 | 34.11305 | 24.50195 | 3.21469 | 6.39641 | 167.66521 | 53.59480 |
| 8u p4096 | 14.28524 (14.278943 to 14.289228) | 32 | 445.02993 | 160.13565 | 118.94825 | 108.50863 | 3.89854 | 6.54108 | 165.94604 | 138.05997 |
| 8u p8192 | 35.7466015 (35.704544 to 35.759869) | 64 | 556.88168 | 160.13817 | 230.58408 | 220.51754 | 3.65697 | 6.40956 | 166.15944 | 249.60528 |

Decode, per step (ms):

| Cell | tok/s per user median (min to max) | step wall T1 | GDN wall (trace) | attn busy | join wait | rest |
|---|---|---|---|---|---|---|
| 1u p1024 | 273.176 (272.652 to 276.265) | 3.62154 | 0.54624 | 0.18655 | 0.018125 | 2.88875 |
| 1u p4096 | 252.6225 (251.555 to 254.144) | 3.89094 | 0.48392 | 0.42129 | 0.030503 | 2.98573 |
| 1u p8192 | 230.541 (229.196 to 233.610) | 4.23386 | 0.47450 | 0.72290 | 0.066563 | 3.03647 |
| 8u p1024 | 121.0549375 (120.75575 to 121.55375) | 8.09300 | 2.83902 | 1.05083 | 0.061910 | 4.20315 |
| 8u p4096 | 77.6411875 (77.331625 to 77.807375) | 12.44077 | 3.12334 | 4.71240 | 0.905286 | 4.60504 |
| 8u p8192 | 56.253125 (56.158125 to 56.329375) | 16.96857 | 3.21452 | 8.90033 | 1.392118 | 4.85372 |

- Decode forwards per run: 255. Token jobs per prefill pass: 128 x users.
- Spread of the prefill pass wall over the 6 runs (largest minus smallest, ms): 0.470, 0.488, 0.209 (1 user) and 1.686, 0.325, 0.907 (8 users) (recomputed from `R/collected.json`; same as `C/design-checks/review/r7_serial_path_numbers.out:15-20`).

### 4.5 Predicted TTFT per cell (s, unrounded, `pred[level][scenario].ttft_s`)

| Cell | base | Part 0 lo / mid / hi (`reorder`) | Part A lo / mid / hi (`amx_gdn`) |
|---|---|---|---|
| 1u p1024 | 0.3846585 | 0.33819903681632657 / 0.29948281749659866 / 0.2898037626666667 | 0.3185617195712479 / 0.27735847675644015 / 0.26599851970656374 |
| 1u p4096 | 1.8971165 | 1.711910306156682 / 1.5575718112872505 / 1.5189871875698926 | 1.633841990240699 / 1.4694384661341655 / 1.4240898697785527 |
| 1u p8192 | 4.7061145 | 4.337376532979592 / 4.030094893795918 / 3.953274484 | 4.183446226018349 / 3.855068339310616 / 3.7643378004478762 |
| 8u p1024 | 2.9073365 | 2.5407035514285714 / 2.2351760942857144 / 2.15879423 | 2.383765151295911 / 2.0600003322010645 / 1.9709361313513512 |
| 8u p4096 | 14.28524 | 12.821142646857142 / 11.601061519238094 / 11.296041237333334 | 12.19037368088954 / 10.900322849353728 / 10.545856219675676 |
| 8u p8192 | 35.7466015 | 32.818360729097506 / 30.378160086678758 / 29.768109926074075 | 31.557990106972618 / 28.97701145021305 / 28.267716287830112 |

| Cell | Part B lo / mid / hi (`amx_attn`) | Parts A and B lo / mid / hi (`amx_both`) | Part 0 + B lo / mid / hi (`reorder_attn`) |
|---|---|---|---|
| 1u p1024 | 0.3805583916283624 / 0.375885025837692 / 0.3700800036312289 | 0.3144616111996103 / 0.2685850025941321 / 0.25142002333779256 | 0.3340989284446889 / 0.2907093433342906 / 0.27522526629789557 |
| 1u p4096 | 1.7549158386567967 / 1.6721305017934924 / 1.6182126237359187 | 1.4916413288974957 / 1.2444524679276578 / 1.1451859935144713 | 1.5697096448134786 / 1.3325858130807429 / 1.2400833113058112 |
| 1u p8192 | 4.083768817372651 / 3.7472864804443824 / 3.5593315619623027 | 3.5611005433910004 / 2.896240319754998 / 2.617554862410179 | 3.7150308503522433 / 3.071266874240301 / 2.8064915459623023 |
| 8u p1024 | 2.855373771350048 / 2.8180881970398457 / 2.7853089049891344 | 2.331802422645959 / 1.9707520292409102 / 1.8489085363404858 | 2.4887408227786194 / 2.1459277913255597 / 2.0367666349891342 |
| 8u p4096 | 13.071257821228098 / 12.410770504875941 / 12.036464743027354 | 10.976391502117638 / 9.025853354229671 / 8.297080962703028 | 11.60716046808524 / 9.726592024114037 / 9.047265980360688 |
| 8u p8192 | 30.626879843405398 / 27.94231849307083 / 26.551349459158864 | 26.43826845037802 / 21.17272844328388 / 19.07246424698898 | 27.6986390725029 / 22.57387707974959 / 20.572857885232942 |

### 4.6 Pass-rule bounds: TTFT fall as a percent of the base TTFT (fall positive; lo bound / working / hi bound)

| Cell | Part 0 (task 2) | Part A (task 6) | Part B (task 5) | Parts A and B |
|---|---|---|---|---|
| 1u p1024 | 12.078106 / 22.143195 / 24.659467 | 17.183237 / 27.894879 / 30.848137 | 1.065909 / 2.280848 / 3.789984 | 18.249145 / 30.175727 / 34.638121 |
| 1u p4096 | 9.762510 / 17.897936 / 19.931792 | 13.877614 / 22.543583 / 24.933979 | 7.495621 / 11.859366 / 14.701463 | 21.373235 / 34.402950 / 39.635442 |
| 1u p8192 | 7.835295 / 14.364708 / 15.997061 | 11.106153 / 18.083839 / 20.011768 | 13.224193 / 20.374090 / 24.367935 | 24.330346 / 38.457929 / 44.379703 |
| 8u p1024 | 12.610613 / 23.119457 / 25.746668 | 18.008626 / 29.144757 / 32.208187 | 1.787297 / 3.069762 / 4.197230 | 19.795922 / 32.214519 / 36.405417 |
| 8u p4096 | 10.249022 / 18.789873 / 20.925086 | 14.664551 / 23.695207 / 26.176556 | 8.498157 / 13.121722 / 15.741949 | 23.162708 / 36.816929 / 41.918505 |
| 8u p8192 | 8.191662 / 15.018047 / 16.724643 | 11.717509 / 18.937716 / 20.921948 | 14.322261 / 21.832238 / 25.723430 | 26.039771 / 40.769954 / 46.645378 |

Predicted fall in seconds at the working values: Part 0 0.085176 / 0.339545 / 0.676020 / 0.672160 / 2.684178 / 5.368441; Part B 0.008773 / 0.224986 / 0.958828 / 0.089248 / 1.874469 / 7.804283; Part A over Part 0 (A/B run of task 6) 0.022 / 0.088 / 0.175 / 0.175 / 0.701 / 1.401 (`C/design-checks/review/paired_changes.out:227-232`, DESIGN lines 976-982).

Predicted decode with Part B (tok/s per user, lo / mid / hi; Parts 0 and A leave decode unchanged):

| Cell | lo | mid | hi | percent lo / hi |
|---|---|---|---|---|
| 1u p1024 | 271.6379012344715 | 273.176 | 275.21383817412817 | -0.563 / +0.746 |
| 1u p4096 | 249.67009061916556 | 252.6225 | 256.59035649674956 | -1.169 / +1.571 |
| 1u p8192 | 226.34958233172023 | 230.541 | 236.26211798620844 | -1.818 / +2.482 |
| 8u p1024 | 119.3677594049485 | 121.0549375 | 123.33456700179667 | -1.394 / +1.883 |
| 8u p4096 | 74.60814951081683 | 77.6411875 | 82.00045386676575 | -3.906 / +5.615 |
| 8u p8192 | 53.28866854816218 | 56.253125 | 60.666432975742204 | -5.270 / +7.845 |

Predicted per-pass values that follow from the formula (ms, lo / mid / hi; not stored in the JSON):

- GDN wall per prefill pass, Part 0: 1 user about 14.40 to 14.52 / 9.60 to 9.68 / 8.40 to 8.47; 8 users 114.38 to 114.57 / 76.26 to 76.38 / 66.72 to 66.83.
- GDN wall per prefill pass, Part A: 1 user 10.08 to 10.16 / 6.30 to 6.35 / 5.45 to 5.49; 8 users 80.07 to 80.20 / 50.04 to 50.13 / 43.28 to 43.35.
- Predicted pass wall: `pred[level][scenario].t1_prefill_ms` (for example 8u p8192: Part 0 511.128 / 473.000 / 463.468; Part A 491.435 / 451.107 / 440.024; Part B 476.886 / 434.940 / 413.206; A+B 411.439 / 329.165 / 296.348).

### 4.7 Pass rules of tasks 1 to 6 with their numbers (DESIGN lines 906-940, `C/design_numbers.py:526-545`)

| Task | Quantity | Rule |
|---|---|---|
| 1 | ratio = time of today's order / time of the column-half order, us per value head per token, 128 KiB working copy, 1 thread and 16 threads | 2.0 or more: the estimate from the counts holds. 1.46 to 2.0: Part 0 continues at its low case. Below 1.46: the Part 0 prediction is wrong. |
| 1 (hypothesis tests, DESIGN 540-543) | recurrence on one 32 KiB slice in L1 | estimate 0.95 to 1.16 us per value head; above 1.16 us supports hypothesis 1. The gap between the slice-alone time and the column-half time at 128 KiB tests hypothesis 2. |
| 2 | bytes of outputs and state against the base build | equal bytes |
| 2 | 100 x (TTFT base - TTFT Part 0) / TTFT base, per cell | inside the Part 0 column of section 4.6 (lo to hi) |
| 2 (falsifier) | GDN step on a 2.70 GHz thread | wrong if above 4.6 us (6.4 / 1.4 = 4.571); estimate 2.7 to 3.5 us; working value 3.05 us |
| 2 (method test, DESIGN 549-552) | fall of pass wall against fall of GDN wall, same kind of run | equal within the spread: 0.2 to 0.5 ms with 1 user, 0.3 to 1.7 ms with 8 users |
| 3 | us per value head per token of the AMX block kernel, and the core clock | 2 times faster than the column-half kernel of task 1 at the measured clock, else Part A stops. Estimate 972 to 1,286 cycles: 0.41 to 0.54 us at 2.40 GHz, 0.51 to 0.68 us at 1.90 GHz. |
| 4 | us per page unit, 256 x 4 attention kernel, data in cache and from main memory, and the core clock | 1.5 times faster than the AVX-512 path or more, with the data in cache |
| 5 | 100 x (TTFT with kill switch - TTFT without) / TTFT base, per cell | inside the Part B column of section 4.6 |
| 5 | decode tok/s with Part B against the kill-switch run | at most 1.1 % below (source value +1.09 %, `C/design-checks/review/same_code_spread.out:4,12`) |
| 5 | AMX K tokens in the attention statistics | above 0 |
| 5 (falsifier, DESIGN 556) | fall of pass wall against fall of attention busy time | wrong if the pass wall falls by less, by more than the spread |
| 6 | TTFT of the Part A run against the run with the GDN switch set | lower in all 6 cells |
| 6 | 100 x ((TTFT base - TTFT Part 0) + (TTFT GDN switch set - TTFT Part A)) / TTFT base | inside the Part A column of section 4.6 |
| 6 | error-band test | (no number in the plan table) |
| 6 (falsifier, DESIGN 546) | GDN step of the block kernel | wrong if not below the Part 0 step; estimate 1.7 to 2.5 us against 2.7 to 3.5 us |

---

## 5. What a comparison script needs

### 5.1 Run settings and their prediction keys (same mapping as `C/design-checks/review/paired_changes.py:33-47`)

| Measured setting | Build and switches (DESIGN 944-972, 858-861) | Scenario key | Runnable? |
|---|---|---|---|
| base | base build (no Parts 0, A, B; holds the new counters) | none (denominator) | yes |
| Part 0 | any build with Part 0, kill switch `TRON_AMX_DISABLE=1` set | `reorder` | yes |
| Part A, attention AVX-512 | build with Parts 0 and A but without B, no switch | `amx_gdn` | only in a build without Part B |
| Part B on today's GDN | none | `amx_attn` | no: no switch selects today's token loop in a build with Part 0 |
| Part 0 + Part B | build with 0 and B, kill switch not set (GDN switch set if the build holds A) | `reorder_attn` | yes |
| Parts A and B | build with 0, A and B, no switch set | `amx_both` | yes |

### 5.2 Quantities to compute (all per cell, medians as in `collect.py`: TTFT = median over runs of the slowest user, decode = median over runs of the mean over users)

- Task 2: `100 * (T_base - T_p0) / T_base` against `[reorder lo, reorder hi]`.
- Task 5: `100 * (T_killswitch - T_noswitch) / T_base` against `[amx_attn lo, amx_attn hi]`. The model is a sum, so Part B saves the same seconds on Part 0 as on the base build (`paired_changes.py:132-138`, largest difference below 1e-9 s).
- Task 6: `100 * ((T_base - T_p0) + (T_gdnswitch - T_parta)) / T_base` against `[amx_gdn lo, amx_gdn hi]`; plus `T_parta < T_gdnswitch` in all 6 cells.
- A+B total: `100 * (T_base - T_ab) / T_base` against `[amx_both lo, amx_both hi]` (listed in `paired_changes.py:168`; no pass rule in the plan table).
- Bounds: `100 * (base_ttft - pred[level][scenario].ttft_s) / base_ttft` with `base_ttft = cells[c].prefill.ttft_s` of `R/predictions.json`. The percent is then applied to the base run of the new session (DESIGN 952-956: every session has its own base run; the values of section 2 are not used as a denominator).
- Decode rule: `tps_partB >= tps_killswitch * (1 - 0.011)`; prediction band from `pred[level].amx_attn.tps`.
- Per pass: measured pass wall (T1) against `pred[level][scenario].t1_prefill_ms`; measured GDN wall against `prefill.gdn_ms / s`; attention busy per worker against `attn_ms - attn_full_ms * (1 - 1/s_attn_prefill) + attn_other_ms * tax_attn_other` (formula of the model; not stored).
- GDN step on a 2.70 GHz thread: per-thread step of the threads on CPUs other than 108 and 109, against 6.4 / s.

### 5.3 Changes the existing scripts need first

- `collect.py:21` `RES` is fixed to `gdn-20261120`; `collect.py:117` knows only the arms `on` and `off`; it parses only `[attn-stats]` lines (a new GDN statistics line needs its own regex and derived fields).
- `predict.py:98-109`, `145-158` pool both arms as baseline samples and read `cells[c]["on"]`.
- `campaign.sh` has one `TAG` per invocation and run names without the tag; `run-one.sh:43` skips a run whose log already exists.
- `run-one.sh:70` unsets only `TRON_AMX_DISABLE` and `USE_HW_ATTN`; a new GDN switch variable should be unset there too and set through `ARMENV`.
- `poll-leaves2.sh:28` finds only a directory named `attention` under `$WT/stats`.
- `analyze_trace.py:152-157` hard-codes 16 key-head groups.