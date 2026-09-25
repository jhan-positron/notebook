<!-- Snapshot of the body posted to https://github.com/positron-ai/tron/pull/4505 on 2026-09-21 UTC. The live text is on GitHub; this copy is the record. -->
## Short version

The nightly System CI installs the tron apt package that `publish-deb.yml` builds with `make deb` from the CMake preset `deb`, and that preset never set `TRON_AMX_DISPATCH`. The three packages built since PR #3879 merged therefore shipped without the AMX attention kernels, and the nightly could not show their effect. This PR adds `"TRON_AMX_DISPATCH": "ON"` to the `deb` preset and updates one paragraph of `README.ci.md`, and the resulting package keeps the AVX path on CPUs without AMX (check 3 below, on the AMD nightly machine).

## Words used here

- **tron, rinzler, engine**: tron is the inference program. rinzler is its production server binary, shipped by the apt package `tron` at `/opt/positron/bin/rinzler`. An engine is one rinzler process serving one model instance (systemd unit `rinzler@N`).
- **AMX, AVX**: AMX = Intel Advanced Matrix Extensions, CPU instructions that multiply small matrices in one step. AVX-512 = the older vector instruction set that the existing attention code uses. "The AVX path" = that existing code, which every CPU in the fleet supports.
- **The AMX attention kernels**: the software-attention fast path that PR #3879 added in `src/tron/kernels/amx_attn.cpp`. It handles a full KV page (a 64-token block of the key/value cache) that is entirely visible to the query, on a model with head size 128, 4 query heads per KV head and bf16 activations. Partial pages and every other shape stay on the AVX path [`h/tron/kernels/amx_attn_iface.hpp` lines 17-31].
- **`TRON_AMX_DISPATCH`**: the CMake option that compiles the kernels and their call sites (top-level `CMakeLists.txt` line 48, default OFF). **`TRON_AMX_DISABLE`**: the run-time kill switch. `TRON_AMX_DISABLE=1` in the engine environment keeps the AVX path even when the kernels are compiled in.
- **preset, the deb preset**: a preset is a named set of CMake cache variables in `CMakePresets.json`. The `deb` preset ("Build only what we want in a released .deb package") is the one `make deb` uses.
- **the nightly**: the System CI job of the systems_test repository. It runs every night on the Intel test machine (delphi-3bda, Granite Rapids, cron 03:30 UTC) and on the AMD test machine (andoria-b1a3, EPYC Genoa, cron 03:00 UTC). It installs the newest `tron` apt package, then runs the functional, performance, MMLU Pro (a multiple-choice accuracy benchmark) and soak (long-running stability) phases. **TPS**: decode tokens per second per user in the performance phase.
- **tp2, tp4**: tensor parallelism over 2 or 4 accelerator cards per engine. A test machine has 8 cards, so a tp2 config runs 4 engines and a tp4 config 2 engines, and the config's user count (8 or 32) is spread over them.
- **FPGA attention, `USE_HW_ATTN=0`**: for the ingested models (qwen-3-4b, gpt-oss-120b, gemma-4-31b) tron runs attention on the FPGA cards from token position 127 of a request on (engine log: "HW attention enabled ... engagement=127"). The first 127 positions of every request run CPU attention. `USE_HW_ATTN=0` in the engine environment turns FPGA attention off, so all attention runs on the CPU.
- **the probe**: tron's one-time check whether AMX may be used. It checks the kill switch, then the CPUID feature bits (CPUID = the CPU instruction that reports the processor's features, here the AMX-BF16 and AMX-TILE bits), then the XCR0 tile state (XCR0 = the register in which the operating system enables extended register state), and only then asks Linux for permission with `arch_prctl(ARCH_REQ_XCOMP_PERM)` [`src/tron/kernels/amx_attn.cpp` lines 58-72, and `available()` at lines 76-86 runs it once per process]. tron writes no log line about AMX. That system call is therefore the only sign of the probe visible from outside the process.
- **arm**: one configuration of a comparison, here one environment setting of the same package.

## The change

One added line in the `deb` preset of `CMakePresets.json`, plus a comma on the line before it (commit 6f37cd2ed9):

```diff
         "BUILD_INGEST_MODELS": "ON",
-        "ENABLE_FUSE_STATS": "ON"
+        "ENABLE_FUSE_STATS": "ON",
+        "TRON_AMX_DISPATCH": "ON"
```

A second commit updates the `TRON_AMX_DISPATCH` paragraph of `README.ci.md` (line 563 on current `main`). It said the option is "default OFF in every other build". It now says that the `deb` preset also sets it ON and that every other preset leaves it OFF. `.github/AGENTS.md` asks for a `README.ci.md` update when CI behavior changes.

## How the package is built, and what the line changes

- `publish-deb.yml` runs on a schedule (cron `17 1 * * *`, 01:17 UTC), on version tags (`v*`), on manual dispatch (with a `channel` input), and when another workflow calls it. It has no pull-request trigger. A push to a feature branch does not start it [`.github/workflows/publish-deb.yml` lines 2-24].
- Its `build` job runs `make ingest-deps` and then `make TOKENIZER_PYTHON_VERSION=3.12.7 deb` on a `[self-hosted, general, heavy]` runner [lines 82 and 106-110].
- The `deb` make target runs `cmake --preset deb -DENABLE_FUSE_STATS=... -DTRON_INGEST_PLUGIN_BUNDLE=""`, then `cmake --build gen-deb` (ninja compiles the tree), then `cpack` (writes the .deb file) [`GNUmakefile` lines 508-514]. The package build therefore sees only the preset's cache variables plus those two `-D` flags. Nothing set `TRON_AMX_DISPATCH`. The option therefore stayed at its default OFF [`CMakeLists.txt` line 48].
- With the option OFF, `src/tron/CMakeLists.txt` lines 193-198 add nothing. `kernels/amx_attn.cpp` is not compiled and the `TRON_AMX_DISPATCH` define is absent. The binary then contains only the AVX attention.
- With the option ON, that one file is compiled with `-mamx-tile -mamx-bf16` plus the AVX-512 flags. No other file receives AMX compile flags (`git grep mamx` finds only that line and comments). The define is PUBLIC on the `tron` library, so rinzler and the model plugins see it. It enables the dispatch call sites and a packed-query scratch buffer in `h/tron/models/self_attention.hpp` (lines 259-290, 1429, 1531, 1571, 1748), and a compile-time check that the build uses 16-wide AVX-512 chunks (lines 30-35, and the `deb` preset leaves `AVX512` at its default ON, so the check passes).
- Every trigger of the workflow configures with the same preset. Scheduled builds publish to the apt channel `unstable` (a channel = a named package stream on the server `apt.positron.internal`), tag builds to `testing` [`bin/ci/resolve-apt-channel.sh` lines 30-36]. Release packages built from version tags therefore carry the kernels too, with the same run-time probe. A developer's local `make deb` uses the same preset and now compiles the kernels as well.
- No job of `publish-deb.yml` runs rinzler. The `smoke-jammy` job installs the package in a container and runs `tokenize_py --help` [lines 134-157]. The first execution of the kernels from a CI-built package is therefore on the nightly test machines.
- The nightly workflow's first step, over ssh to the test machine, is `apt-get remove -y tron`, `apt-get update`, `apt-get install -y tron` (no version pin, so apt takes the newest package in the `unstable` channel) and `apt-get upgrade -y` [systems_test `.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml` lines 46-50 and `system_ci_genoa96_rinzler.yaml` lines 46-50].

Evidence that the shipped packages had no AMX code:

- Three packages were built after PR #3879 merged on 2026-09-15: 2026.09.16-f46e48ba, 2026.09.17-31b80a18 and 2026.09.18-3faba6d0. The build logs of the first two (GitHub Actions runs 35044660449 and 35171163989) never mention `amx_attn.cpp.o`. The third used the same preset.
- On the installed rinzler of package 2026.09.16-f46e48ba, `strings` (lists the text constants of a binary) piped to `grep -c -x TRON_AMX_DISABLE` prints 0, and `objdump -d` (disassembles the binary) finds 0 AMX tile instructions.
- A build with the option ON gives 1 and 86 (check 1).

## What is not affected

- **Pull-request CI.** The default pull-request lane (`gcp-nix.yml`) and the merge queue build with nix. That CMake configure line passes its own `-D` flags and no preset, so `CMakePresets.json` is never read there [`nix/cmake-tron-test-build.nix` lines 84-101]. This PR changes nothing in what CI compiles or tests for pull requests. Issue #3997 tracks that gap and stays open.
- **The legacy CMake lane** (`cmake-single-platform.yml` line 355) passes `-DTRON_AMX_DISPATCH=ON` on its own configure line and is unchanged. It runs only on manual dispatch and as the `test` job of tag-push or feature-branch package builds, not on pull requests.
- **The other presets** (`native`, `cross-avx512`, `darwin`, `asan`, `tsan`, `coverage`) are unchanged. A build from them still has the option OFF unless it is passed on the command line.
- **CPUs without AMX.** The probe reads CPUID leaf 7 (`amx_attn.cpp` lines 64-66). On AMD the AMX-BF16 and AMX-TILE bits are absent. `available()` therefore returns false before any AMX instruction executes, and the existing AVX-512 attention runs. Intel hosts whose operating system did not enable the tile state (XCR0 bits 17-18 clear, line 70) or whose kernel refuses `arch_prctl(ARCH_REQ_XCOMP_PERM)` (Linux older than 5.16, line 71) take the same AVX path.
- **Rollback without a rebuild.** Set `TRON_AMX_DISABLE=1` in `/opt/positron/user/config.env` (read by every `rinzler@` unit, `packaging/systemd/rinzler@.service` line 43) or in the platformd-written `/etc/rinzler/instance-N.env` (line 26), then restart the engines. On delphi-3bda the instance files as written by platformd on 2026-09-16 set neither `USE_HW_ATTN` nor `TRON_AMX_DISABLE`. The andoria-b1a3 files were not checked.

## Numerics on AMX hosts

For eligible pages the kernels change the attention arithmetic in two documented ways. The softmax weights are rounded to nearest even instead of truncated when converted to bf16, and the fp32 products are added in a different order [`h/tron/kernels/amx_attn_iface.hpp` lines 74-85]. Generated tokens can therefore differ from the AVX path where a bf16 tie flips. `t/t_amx_numerics.cpp` checks that the kernels stay inside the error band those two causes allow. The nightly tolerates such differences: the functional tests accept a response whose embedding similarity to a golden response is at least 0.60 [systems_test `functional_tests/test_api.py` line 322], and the MMLU Pro thresholds are the 30 % quantile over the last 14 runs [`thresholds/system_ci_mmlu_pro.yaml` lines 2-7]. The two eligible hand-written models (llama-3.1-8b, mixtral-8x7b) also run in the functional (tp4), MMLU Pro (tp2) and soak (llama-3.1-8b tp4) phases [systems_test `scripts/system_ci.py` model lists], so their scores there can move inside their run-to-run bands.

## Checks done

1. **Package built with the CI commands** (2026-09-17, delphi-3bda, outside `nix develop`, the project's nix developer shell, because `make deb` refuses to run inside it [`GNUmakefile` lines 502-506]). `make ingest-deps && make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb && make test-deb-package-contents` passed. Known differences from the CI builder: 48 parallel jobs pinned to one socket, ccache enabled, uv 0.11.21 instead of the CI's 0.9.5. Same as the CI builder: Clang 19.1.7 and the preset values. The configure log lists `TRON_AMX_DISPATCH="ON"`, and ninja step 310 of 398 compiles `kernels/amx_attn.cpp.o`. On the packaged rinzler `strings` counts 1 and `objdump` finds 86 AMX tile instructions. The same day's nightly package (2026.09.17-31b80a18) gives 0 and 0. Package version: `2026.09.17-6f37cd2e-jhan-amx-deb-preset`.

2. **Run time on Intel** (delphi-3bda, 2026-09-17). The packaged rinzler ran as one engine from the extracted package tree (not installed), with `ingested-qwen-3-4b-instruct-2507-tp2`, on half of the machine (`--instance 2,4`). Each arm got 3 requests whose prompt was served from the prefix cache, so the measured windows hold decode work only. `perf stat -e cpu/event=0xb7,umask=0x02` (EXE.AMX_BUSY, "cycles in which the AMX unit is busy") counted on the engine pid.

   | arm | arm variables | probe `arch_prctl(0x1023, 18)` | AMX-busy cycles, idle 10 s | AMX-busy cycles, 3 requests |
   |---|---|---|---|---|
   | CPU attention, AMX allowed | `USE_HW_ATTN=0` | granted | 0 | 873,318,988 |
   | CPU attention, kill switch | `USE_HW_ATTN=0 TRON_AMX_DISABLE=1` | not called | 0 | 0 |
   | nightly default for this model (FPGA attention) | none | granted | 0 | 501,350,140 |

   Every arm also carried the nightly engine's variables (`TRON_USE_SPECULATION=0`, `RZ_FUSE_MOUNT_PRESCOPED=1`, `RZ_ENABLE_SAVE_TOKENS=1`), debug log level, and an `LD_PRELOAD` shim that records the probe call. The cycle counts (summed over all engine threads) prove only that the AMX unit executed. They are not a speed measurement. The kill-switch arm's 0 is the control. The FPGA-attention row still shows AMX-busy cycles because the CPU handles the first 127 positions of each request. No engine crashed.

3. **AMD nightly machine** (andoria-b1a3, 2026-09-18, run by the systems-test owner). The package built from this branch (version `2026.09.18-6f37cd2e-jhan-amx-deb-preset`) installed. `strings` counts 1. The owner ran the nightly harness's performance phase by hand on 5 of the nightly's 12 configs. The functional, MMLU Pro and soak phases did not run. All 5 configs passed the enforced TPS thresholds (average and slowest user) [report post, https://positronai.slack.com/archives/C0AEHSNHCUX/p1789763819852589]. TPS was +0.4 % to +1.1 % against the plain package on the same machine and day (a by-hand rerun of the performance phase on tron 2026.09.18-3faba6d0, 12 configs, posted 26 minutes earlier):

   | config | this package, TPS | plain package, TPS | delta |
   |---|---|---|---|
   | llama-3.2-3b fast tp2, 32 users | 231.14 | 228.60 | +1.1 % |
   | llama-3.1-8b good tp2, 8 users | 150.64 | 149.77 | +0.6 % |
   | qwen-3-4b tp2, 8 users | 209.37 | 207.87 | +0.7 % |
   | qwen-3-4b tp4, 8 users | 187.35 | 186.55 | +0.4 % |
   | gpt-oss-120b tp4, 8 users | 123.73 | 122.71 | +0.8 % |

   Against the machine's scheduled nightly of 2026-09-16 (tron 2026.09.16-f46e48ba: 230.10, 150.79, 206.54, 184.47, 123.75 TPS) the deltas are -0.1 % to +1.6 %. Under the proposed YAML thresholds (posted next to the report, not enforced), llama-3.1-8b good tp2 reads 150.64 TPS against a 199.64 TPS threshold (75 %). The plain package reads 149.77 TPS (75 %) in the same day's rerun. That threshold is a calibration item in systems_test, not an effect of this package. An earlier check of the AVX fallback, with a developer build of runtron on andoria-06 on 2026-09-11, traced no `arch_prctl(ARCH_REQ_XCOMP_PERM)` call. That is the check the commit message cites.

4. **The Intel nightly's 12 performance configs, run manually** (delphi-3bda, 2026-09-18/19, the systems_test performance harness). New package: main 3faba6d0fd plus this preset line (2026.09.18-0594dc54-jhan-ci-canon). Base: the same day's nightly package 2026.09.18-3faba6d0, measured earlier that day with the same harness. Each arm ran once with 10 rounds per config, as in the nightly.
   - A change counts as resolved only when all three hold: a paired t test over the 10 rounds gives |t| >= 2.26 (the 5 % two-sided limit for 10 pairs), the change is at least 1 %, and the change exceeds the config's 13-night band (two standard deviations of its TPS over the nightlies of 2026-09-05 to 2026-09-17).
   - No config lost TPS by a resolved amount.
   - llama-3.1-8b good tp2, 8 users: +1.2 % (139.40 to 141.03 TPS, t +2.8, resolved). A separate 20 s `perf stat` window on that config's engines, run just before its benchmark with 4 short requests, counted 30.2 billion AMX-busy cycles (0 on the base package).
   - mixtral-8x7b tp2, 8 users, the other eligible CPU-attention config: -0.6 % (t -2.2, below the 1 % floor, not resolved). No AMX-busy probe ran on that config, so whether the kernel engaged there is not measured.
   - Two drops inside their 13-night bands, unresolved: gpt-oss-120b tp4 106.51 to 102.33 TPS (-3.9 %, t -2.6, band 5.7 %, and the 2026-09-18 nightly itself reported 101.16) and qwen-3-4b tp4 149.94 to 146.05 TPS (-2.6 %, t -3.7, band 7 %, above the 135 TPS goal). A repeat run would show whether they are real. Reviewers decide whether that repeat must happen before the merge.
   - Full report: internal HTML report, available on request.

## What to expect after the merge

- The first package with the kernels comes from the first `publish-deb.yml` run after the merge. The run is scheduled at 01:17 UTC and started between 01:31 and 01:40 UTC in the last week, building the head of `main` at that moment. A merge before about 01:00 UTC therefore lands in that night's package. The build step took 19 to 21 min in the last successful runs.
- The publish step can lag. On 2026-09-15 the package was built at 01:37 UTC but published at 16:26 UTC, and that night kept the previous package. The `dpkg -l tron` check below tells which package a night ran.
- Caveat: the scheduled `publish-deb.yml` runs of 2026-09-19, 09-20 and 09-21 UTC (runs 35413074014, 35481888971 and 35551712750) ended in `startup_failure` with no job started. `publish-deb.yml` itself is unchanged since the last successful run. The cause was not determined here. Until it is fixed, no new package reaches the `unstable` channel, with or without this PR, and the nightly keeps installing 2026.09.18-3faba6d0.
- Checks on the morning after the first nightly with the new package, on the test machine:
  - `dpkg -l tron` shows the new version.
  - `strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE` prints 1.
  - The publish-deb build log has the `amx_attn.cpp.o` step.
  - `grep -l TRON_AMX_DISABLE /etc/rinzler/instance-*.env /opt/positron/user/config.env` prints no file name (a kill-switch line there would turn AMX off without any trace in the package checks).
- Where a change can show on delphi-3bda. From the model table [`h/tron/plugins/llama.hpp` lines 1583-1594]: llama-3.1-8b (32 heads, 8 KV heads, head size 128) and mixtral-8x7b (32/8/128) have 4 query heads per KV head and bf16 activations, so they are eligible. llama-3.2-3b (24/8 = 3 per KV head), llama-3.3-70b (64/8 = 8), qwen-2.5-32b (40/8 = 5) and gemma-2-9b (16/8 = 2, head size 256) are not. Of the ingested models, qwen-3-4b has the eligible shape (32/8/128) but runs FPGA attention in the nightly, so the kernels act only on the first 127 positions of each request. gpt-oss-120b has head size 64, so it gets no kernel at all. gemma-4-31b was not checked.
- Expected size on the llama-3.1-8b row: about +1 %. The nightly serves llama-3.1-8b tp2 as 4 engines behind a proxy, and its per-user timing lines are consistent with 2 users per engine. Check 4 measured +1.2 % at that layout. The gain grows with users per engine: +0.2 %, +3.9 % and +12.9 % at 2, 4 and 8 users per engine on llama-3.1-8b (2026-09-18, systems_test performance harness, same binary with the kill switch against AMX on). That binary was the PR #4424 package (VNNI K layout compiled in, in both arms), so those are the kernel's gains on top of that layout, not this PR's package, and the 2-user point is inside the noise (t +0.5).
- On andoria-b1a3 no TPS change is expected. Check 3 measured 5 of the 12 configs at +0.4 % to +1.1 % against the plain package on the same day.

## Related

- PR #3879: the kernels (merged 2026-09-15).
- Issue #3997: no default CI lane compiles or runs the AMX code. Still open after this PR.
- PR #4424 (VNNI layout of the K cache) is independent of this change.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
