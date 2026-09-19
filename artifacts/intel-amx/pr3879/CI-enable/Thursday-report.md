# Thursday report, 2026-09-17: the nightly CI package with AMX compiled in

Request (jhan, 2026-09-17): execute section 1 of the page "Was AMX in the last two nightly CI binaries?" on delphi-3bda. Confirm that AMX is compiled into a CI-style package. Confirm that AMX runs at run time with qwen3-4b. Write instructions for Rhys to try the package on the AMD nightly machine. Work done 2026-09-17 19:24 to 20:45 UTC. Section 8 lists what an adversarial verification pass corrected in this text.

## Short version

We built the tron apt package the way the nightly CI builds it, with one change: the AMX option is on in the "deb" preset. The packaged rinzler contains the AMX code (the same day's nightly package has none) and used it while serving qwen3-4b on delphi-3bda, with zero AMX activity once the kill switch was set. The package is ready for Rhys at `delphi-3bda:/var/tmp/jhan/ci-enable-deb/`, with step-by-step instructions in `for-Rhys-andoria-AMD-test.md`.

## Words used here

- **tron**: the inference program under test. **rinzler**: its production server binary. **runtron**: its command-line tool (not shipped in the package).
- **delphi-3bda**: the Intel Xeon 6 test machine that runs the nightly. **andoria-b1a3**: the AMD nightly machine. **DUT**: device under test, the machine the nightly installs on.
- **the models**: qwen3-4b (`ingested-qwen-3-4b-instruct-2507`), gpt-oss, llama-3.1-8b and the others named below are the language models tron serves in the nightly. "Ingested" models are converted from the public checkpoint by tron's ingest pipeline. The others (llama, mixtral, qwen-2.5, gemma) are hand-written in tron.
- **engine**: one rinzler process serving one model. **tp2 / tp4**: the model is split over 2 or 4 FPGA cards. **`--instance A,B`**: tron's flag that picks card set A of B on the machine (`1,2` is the second half; `2,4` is the third quarter, cards 90 and 93).
- **the nightly**: the System CI workflow in the repo positron-ai/systems_test. It installs tron from the apt server (`apt-get install -y tron`) and then runs functional, performance, MMLU and soak tests. It is scheduled at 03:30 UTC on delphi-3bda (the package was installed at about 03:39 UTC in the last runs) and at 03:00 UTC on andoria-b1a3 (run start and install at about 03:10 UTC). **TPS**: tokens per second per user in its performance test. **the qwen rows**: the rows of that test's result table for the qwen3-4b model.
- **the apt package, the deb, publish-deb.yml, the deb preset**: the file `tron_<version>_amd64.deb`. The tron workflow publish-deb.yml builds it once a day with `make deb`. It is scheduled at 01:17 UTC. The last runs started at 01:35 to 01:37 UTC and built the head of `main` at that moment. `make deb` configures CMake with the preset named "deb" (a preset is a named set of CMake options).
- **PR 3879**: the pull request that added the AMX attention kernels to tron, merged 2026-09-15. **lane**: one CI workflow of the tron repo (for example gcp-nix.yml, the default pull-request lane).
- **nix develop**: tron's developer shell, provided by the nix package manager. **uv**: the Python package manager the build uses for the model-ingest environments. **ccache**: a compiler cache that reuses earlier compile results.
- **AMX**: Intel Advanced Matrix Extensions, CPU instructions that multiply small matrices in one step. **TRON_AMX_DISPATCH**: the CMake option that compiles tron's AMX attention kernels in (default off). **TRON_AMX_DISABLE**: the run-time kill switch (exactly `1` turns AMX off).
- **the probe**: tron's one-time check whether AMX may be used. It checks the kill switch, then the CPU feature bits, then whether Linux enabled the tile state. Only when all three pass does it ask Linux for permission with the system call `arch_prctl(0x1023, 18)`. tron writes no log line about AMX. This system call is therefore the only outside sign of the probe. The **amxprobe shim** is a 36-line library loaded with LD_PRELOAD that writes that call to a file [exec/amd-amx-20260911/amxprobe.c].
- **EXE.AMX_BUSY**: a CPU performance counter, "cycles in which the AMX unit is busy". We read it with `perf stat` (raw event `cpu/event=0xb7,umask=0x02`). It is direct evidence that AMX instructions executed. Section 3.1 says how we validated it.
- **attention, CPU attention, FPGA attention, KV page**: attention is the per-token lookup over the earlier tokens of a request. For the ingested models tron computes it on the FPGA cards for token positions 127 and later. Positions 0 to 126 of every request stay on the CPU. `USE_HW_ATTN=0` forces all of it onto the CPU. The AMX kernels replace CPU attention only, and only for complete KV pages (64-token blocks of the key/value cache).
- **arm**: one test configuration, run as its own fresh engine.
- **our half, the Bill marker, the CI lease**: delphi-3bda is shared with Bill. Our half is socket 1 with the FPGA cards 90/93/b9/bc (`--instance 1,2`). All runs below used one engine on cards 90 and 93 (`--instance 2,4`), a placement we derived for the nightly's socket-1 tp2 engine by halving the production tp4 core list (the nightly's own tp2 instance file was not read). The marker file `/bill-has-instance-0,2` says Bill may use the first half. The lease file `/run/lock/systems-test-ci.lease` exists while the nightly holds the machine.
- **platformd, unit file, FUSE statistics mount, SYSTEM_CONFIG**: platformd is the service that starts and configures the rinzler engines on each machine. The unit file is the systemd service definition `rinzler@N`. The FUSE statistics mount is a directory rinzler mounts to expose its counters. SYSTEM_CONFIG is an environment variable that the login shell on delphi-3bda sets to `--instance 1,2`; tron applies it after the command line.
- **hugepage slice files**: tron's memory-backing files in `/dev/hugepages`, one per machine slice (`slice-4-of-8` and `slice-5-of-8` for `--instance 2,4`, 64 GiB each). HugePages_Free counts the free 1 GiB pages of the machine's pool of 512.
- **strings, objdump, nm**: three binary inspection tools. The package binary is stripped, so `nm` (function names) shows nothing there. `strings` (text constants) and `objdump -d` (machine instructions) work on a stripped binary.
- **prefix cache, prefill, decode**: the prefix cache stores already-computed prompt states. Prefill is the first pass over a prompt. Decode is the generation of new tokens, one per step.

## 1. What was done: the preset change, built the CI way

The page's section 1 says the fix is one line in the deb preset. We made that change: one added line, plus a comma on the line before it (2 insertions, 1 deletion). The worktree is a fresh checkout of tron `main` at e92da643f1 (2026-09-17 18:16 UTC) on delphi-3bda's local disk, `/var/tmp/jhan/tron-ci-enable`. The change is committed there on the branch `jhan-amx-deb-preset` as commit 6f37cd2ed9. The branch is local. Nothing was pushed and no pull request exists yet (see section 5).

    --- a/CMakePresets.json
    +++ b/CMakePresets.json
    @@ -76,7 +76,8 @@
             "BUILD_NATIVE": "OFF",
             "BUILD_PRODUCTION_MODELS": "ON",
             "BUILD_INGEST_MODELS": "ON",
    -        "ENABLE_FUSE_STATS": "ON"
    +        "ENABLE_FUSE_STATS": "ON",
    +        "TRON_AMX_DISPATCH": "ON"
           }
         },

Then we ran the package build the way publish-deb.yml runs it [.github/workflows/publish-deb.yml, step "Build .deb"]:

- from a plain shell, not inside `nix develop` (the makefile refuses `make deb` inside that shell);
- with the CI's path additions for `uv` and the Haskell toolchain.

| Step | Command | Time (UTC) | Result |
|---|---|---|---|
| 1 | `make ingest-deps` | 19:30:53 to 19:31:29 (36 s) | two Python environments for the model ingest |
| 2 | `make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb` | 19:31:29 to 19:42:19 (10 min 50 s) | 398 ninja steps, package written by cpack |
| 3 | `make test-deb-package-contents` | 19:42:19 to 19:42:58 (39 s) | passed (the chain returned 0) |

Build facts, from the build log and the package-check record [exec/results/ci-enable-20260917/make-deb.log, package-checks.txt]:

- The compiler was Clang 19.1.7. The CI package builder logged the same compiler version in its runs of 2026-09-16 and 2026-09-17 (runs 35044660449 and 35171163989).
- The "Preset CMake variables" block of the configure step lists `TRON_AMX_DISPATCH="ON"` (log line 272). Neither CI build log has such a line.
- Step 310 of 398 is `Building CXX object src/tron/CMakeFiles/tron.dir/kernels/amx_attn.cpp.o`. That is the one file that holds the AMX kernels. The two CI build logs never mention it. They have 397 steps, one fewer than ours.
- The build was launched with `taskset` on the socket-1 cores (our half) and `NPROC_BUILD=48` (48 parallel jobs requested). The launch command is recorded in package-checks.txt. The build log itself does not show it.
- The CI runner uses the makefile default of 16 jobs. The 12 minutes here therefore do not predict the CI time. The CI "Build .deb" step took 21 min 17 s on 2026-09-16 and 19 min 22 s on 2026-09-17.
- Differences from the CI builder that we know of:
  - the machine: delphi-3bda instead of the "heavy" self-hosted runner;
  - `uv` 0.11.21 from `~/.local/bin` came first on the path. CI uses 0.9.5. Both read the frozen lock files;
  - ccache was enabled with a cache directory that earlier builds on this machine had filled. The log records no hit statistics, so we cannot say how much it helped.
  - The compiler version and the preset values are the same.

The result:

| Item | Value |
|---|---|
| Package | `tron_2026.09.17-6f37cd2e-jhan-amx-deb-preset_amd64.deb` (the branch name is part of the version, so it cannot be confused with a nightly package) |
| Size | 137,904,212 bytes (the nightly package 2026.09.17-31b80a18 is 137,842,296 bytes) |
| sha256 | `a2dc67bafbd690bbfc9e795064ea7dd93484f44bae39bac1178f1b13b7ec8a87` |
| Copy for Rhys | `delphi-3bda:/var/tmp/jhan/ci-enable-deb/` (file mode 644, directory 755), next to a copy of his instructions (`README-for-Rhys.md`) |
| Original | `delphi-3bda:/var/tmp/jhan/tron-ci-enable/gen-deb/` |

## 2. Is AMX compiled into the CI-style package? Yes

We extracted the package (`dpkg-deb -x`) and inspected the rinzler inside it. The same checks were run on the unstripped build target and on the installed nightly package (`nm` on a stripped binary returns "no symbols") [exec/results/ci-enable-20260917/package-checks.txt].

| Binary | Size, bytes | `TRON_AMX_DISABLE` text (strings) | AMX tile instructions (objdump) | amx_attn functions (nm) | Reading |
|---|---|---|---|---|---|
| rinzler inside our package | 232,814,656 | 1 | 86 | 0 (stripped, as every package binary) | AMX code present |
| gen-deb/rinzler, the unstripped build target our package was made from | 945,658,640 | 1 | 86 | 10 | AMX code present |
| /opt/positron/bin/rinzler, the nightly package 2026.09.17-31b80a18 installed on delphi-3bda | 232,667,904 | 0 | 0 | 0 (stripped) | no AMX code |

Details:

- The 86 instructions are 32 `tdpbf16ps` (the tile multiply), 40 `tileloadd`, 12 `tilestored`, 1 `ldtilecfg`, 1 `tilerelease`. The binary also holds 12 `tilezero`, which the count does not include. These are the same numbers as our two developer builds of PR 3879 on this machine (86 instructions, 10 functions) [nightly-amx-check page, section 3b].
- The kill-switch text is one of 36 `TRON_*` environment-variable names in the packaged binary. The nightly package holds 35. The one extra name is `TRON_AMX_DISABLE` (diff of the two sorted lists).
- The 10 amx_attn functions occupy 8,343 bytes of code in the unstripped binary (`nm -S`). The packaged rinzler is 146,752 bytes larger than the nightly's. The two binaries come from different `main` commits (31b80a18 against e92da643f1, 10 merges apart). So that size difference is not a measure of the AMX code.

Commands, for reuse on any host:

    strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE          # 1 with AMX, 0 without
    objdump -d --no-show-raw-insn /opt/positron/bin/rinzler \
      | grep -c -E '(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)'  # 86 with AMX, 0 without

## 3. Does AMX run at run time with qwen3-4b? Yes

### 3.1 Method

We did not install the package on delphi-3bda. Installing it would replace the production package on a shared machine, and the nightly reinstalls its own package every morning anyway. Instead we extracted the package to `/var/tmp/jhan/ci-enable-root` and started the packaged rinzler from there as one engine on our half [exec/ci-enable-20260917/runtime-check.sh]. The engine environment:

- the three variables the nightly's engines get from platformd and the unit file: `TRON_USE_SPECULATION=0`, `RZ_FUSE_MOUNT_PRESCOPED=1`, `RZ_ENABLE_SAVE_TOKENS=1`, plus a FUSE statistics mount under `/var/tmp/jhan`;
- log level debug (`TRON_LOG_LEVEL=debug`, tron's default, which production does not override);
- `env -u SYSTEM_CONFIG`: the login shell's SYSTEM_CONFIG would override our `--instance 2,4`, so the variable is removed;
- `LD_LIBRARY_PATH` pointing at the package's own `lib/`, and the amxprobe shim in `LD_PRELOAD`;
- the two variables of the arm, listed in the table below.

The model was `ingested-qwen-3-4b-instruct-2507-tp2`. Each arm started a fresh engine, so the probe ran once per arm.

Three arms:

| Arm | Environment | What it stands for |
|---|---|---|
| cpu-on | `USE_HW_ATTN=0` | attention on the CPU, AMX allowed: the setting under which the AMX kernels do the whole attention |
| cpu-off | `USE_HW_ATTN=0 TRON_AMX_DISABLE=1` | the same, with the kill switch: the control arm |
| default | neither variable set | how the nightly runs the ingested qwen model: FPGA attention from token position 127 on |

Three kinds of evidence per arm:

1. **Which binary served.** `/proc/<pid>/exe` of the engine and the "Version:" banner in its log.
2. **The probe.** The amxprobe shim wrote the `arch_prctl(0x1023, 18)` call, if any, to a file.
3. **AMX execution.** `sudo perf stat -e cpu/event=0xb7,umask=0x02 -p <pid>` (EXE.AMX_BUSY) over two windows: 10 s with no requests, then 90 s during which 3 requests were sent.

We validated the counter before using it [exec/results/ci-enable-20260917/counter-validation.txt, exec/ci-enable-20260917/amxspin.c]:

- A test program that runs 20,000,000 `tdpbf16ps` tile multiplies counted 320,005,520 busy cycles. That is 16 busy cycles per multiply. It matches the documented throughput of the instruction, one tile multiply every 16 cycles, and not its latency of 52 cycles [Intel Optimization Reference Manual, Table 20-2, as recorded on 2026-09-02].
- The same program's scalar loop (2.9 billion instructions) counted 0.
- The production rinzler of the nightly package (no AMX code) counted 0 AMX-busy cycles in 3 s. The same window counted 742 billion CPU cycles summed over all threads of that process (63 spinning threads), so the counter was reading a busy process.
- We counted per process (`-p <pid>`), so only the engine's threads are counted. A first reading of this record claimed that per-CPU mode counts on idle CPUs. That was a misread of the CSV columns: the count was 0. The record carries a correction line.

The requests: one chat completion with a prompt of 803 words (910 tokens), at most 160 new tokens, temperature 0. A warm-up request with the same prompt preceded the measured requests. The engine's usage report says all 910 prompt tokens were served from the prefix cache in the measured requests. So the measured windows hold no prompt prefill. They hold decode work, plus at most one recompute of the last prompt position. Each request returned 131 to 136 tokens (the model stopped by itself).

### 3.2 Results

All three engines ran `/var/tmp/jhan/ci-enable-root/opt/positron/bin/rinzler` and logged `Version: 2026.09.17-6f37cd2e-jhan-amx-deb-preset` [exec/results/ci-enable-20260917/summary.tsv, runtime-check.log].

| Arm | Attention (engine log) | Probe call | AMX busy cycles, idle 10 s | AMX busy cycles, 3 requests | Tokens per second of client wall-clock, 3 requests (rough; client start-up included) | Crash words in the engine log while serving |
|---|---|---|---|---|---|---|
| cpu-on | "HW attention disabled ... USE_HW_ATTN=0" | `arch_prctl(0x1023, 18) = 0` (granted) | 0 | 873,318,988 | 218.6 / 219.3 / 219.3 | 0 |
| cpu-off | "HW attention disabled ... USE_HW_ATTN=0" | none (the shim was loaded) | 0 | 0 | 213.0 / 214.2 / 214.5 | 0 |
| default | "HW attention enabled ... engagement=127" | `arch_prctl(0x1023, 18) = 0` (granted) | 0 | 501,350,140 | 197.7 / 201.2 / 217.5 | 0 |

The crash-word grep (illegal, SIGILL, abort, terminate) ran before each engine was stopped. The archived logs each hold one later match, the shutdown line "Received signal: Terminated" from our own SIGTERM.

Reading:

- **The packaged rinzler uses AMX.** With CPU attention the probe was granted. The AMX unit was busy for 873 million cycles during 3 requests (about 0.2 s of work of one core at 4 GHz, spread over the attention workers). It was idle for 0 cycles when no request ran.
- **The kill switch works in the package.** With `TRON_AMX_DISABLE=1` the probe never asked for permission. The AMX unit counted 0 cycles during the same requests.
- **The nightly's qwen setting also engages AMX.** With FPGA attention (the nightly's default for qwen) the probe was granted. The AMX unit counted 501 million busy cycles, 57% of the CPU-attention arm's count. The page's section 1 expected the CPU share under FPGA attention to be about one KV page per query per layer, so a much smaller count. We do not know which work produced these cycles. `Insufficient data`: a build with the page-visit counters (CMake option `TRON_PAGE_SHARE_COUNTERS`) run in the same two arms would show how many pages the AMX kernels scored under FPGA attention. Until then, treat the page's claim that the qwen rows will barely move as unmeasured.
- The client-side speeds are about 2.4% apart between cpu-on and cpu-off (mean 219.1 against 213.9 tokens per second). This is one user and 3 short requests, and the number includes the client's own start-up. It is not a measurement of the AMX gain. The measurement of the gain is the CI harness at the nightly's user counts, AMX on against AMX off, in TPS: +13.9% in the round-1 run (llama-3.1-8b-good tp2, 8 users on one engine, commit 60d66d9c04) [exec/results/more-testing-r1/notes.md], and +8.4% in the nightly-layout run of 2026-09-13 (qwen tp2, 2 engines with 2 users each, CPU attention, commit 544ca05c7a) [PR3879/new-PRs/PR1/Sunday-CI-layout-results.html].
- The answer texts say nothing about AMX against AVX. Repeats of the same prompt inside one arm already differ from each other (the first difference falls between characters 385 and 640). One cpu-on answer is byte-identical to one cpu-off answer. The engine is not run-to-run deterministic in this setting (temperature 0, without tron's pay-for-determinism mode, the slower setting that makes repeated runs bit-identical).

## 4. What this means for the nightly

Nothing in this run contradicts the page's section 1. It confirms its two testable claims: the deb preset with the option on compiles the AMX kernel file (step 310 of the build log), and the packaged rinzler runs AMX on delphi-3bda without setting `USE_HW_ATTN` or `TRON_AMX_DISABLE` (the default arm). The remaining steps are unchanged:

1. Merge the preset change to `main` before about 01:00 UTC on the night it should take effect. publish-deb.yml is scheduled at 01:17 UTC. The last runs started at 01:35 to 01:37 UTC and build the head of `main` at that moment. The delphi-3bda nightly installs the package at about 03:39 UTC.
2. The morning after, run these checks:
   - Which package did the night install? `dpkg -l tron | tail -1` on the DUT, or the `Setting up tron (<version>)` line in the run log. A package can be built on time and published late (2026-09-15: built 01:37 UTC, published 16:26 UTC). In that case the night keeps the previous package.
   - Does the package build log show the `amx_attn.cpp.o` line and the `TRON_AMX_DISPATCH="ON"` preset line?
   - Do the two commands of section 2 give 1 and 86 on `/opt/positron/bin/rinzler` on the DUT?
   - Does no service environment file set the kill switch? `sudo sh -c 'grep -l TRON_AMX_DISABLE /etc/rinzler/instance-*.env /opt/positron/user/config.env'` must print no file name.
3. Where the change shows: llama-3.1-8b-instruct-good tp2, which runs CPU attention. Its goal is a mean of 144 TPS with every user above 140 TPS. The last three nights reported means of 139.78, 139.98 and 139.01 TPS. The qwen rows run FPGA attention. Section 3.2 shows AMX engages there too, at an unknown share of the work, so a movement of the qwen rows is possible.
4. The AMD machine (andoria-b1a3) receives the same package. Section 2 of `for-Rhys-andoria-AMD-test.md` lists what to check there, and its section 3 what to send back.

## 5. Open items and decisions

- **Pull request.** Commit 6f37cd2ed9 sits on the local branch `jhan-amx-deb-preset` in the worktree `/var/tmp/jhan/tron-ci-enable` on delphi-3bda (a worktree of the shared repo `~/workspace/tron`). `main` has moved 2 commits since. To open the PR from delphi-3bda, where `gh` is logged in as jhan-positron: `cd /var/tmp/jhan/tron-ci-enable && git push -u origin jhan-amx-deb-preset && gh pr create --base main --head jhan-amx-deb-preset`. The commit message states the reason and the AMD fallback. Nothing was pushed (jhan decides).
- **Rhys's AMD test.** Instructions and the file location are in `for-Rhys-andoria-AMD-test.md`, with a copy next to the package on delphi-3bda (`/var/tmp/jhan/ci-enable-deb/README-for-Rhys.md`; re-copy after edits). The package copy lives on delphi-3bda's local disk. It is not backed up. Rebuilding takes 12 minutes with the commands of section 1.
- **AMX under FPGA attention.** The share of the work that AMX does under FPGA attention is unmeasured (section 3.2, third bullet). The measurement that would settle it, a page-counter build run in both arms, is named there.
- **Pull-request CI lane.** The default pull-request lane (gcp-nix.yml) still builds without the option. So no default CI run executes AMX code. This is the separate item of the page's section 1, step 8 (Hannah-AMX-CI.html, issue 3997). The preset change does not touch it.
- **Not done on purpose.** The package was not installed on delphi-3bda (shared machine, production units running on Bill's half). The Ubuntu 22.04 container smoke test of publish-deb.yml (`ci-run-deb-package-jammy-runtime.sh`) was not run: it needs the apt server token and Docker. Rhys's install on andoria-b1a3 will be the first real install of this package.

## 6. Files

| What | Where |
|---|---|
| This report and the instructions for Rhys | `~/workspace/intel-AMX/PR3879/new-PRs/CI-enable/{Thursday-report.md, for-Rhys-andoria-AMD-test.md}` |
| Copy of the instructions next to the package | `delphi-3bda:/var/tmp/jhan/ci-enable-deb/README-for-Rhys.md` (re-copy after editing the local file) |
| Worktree with the commit | `delphi-3bda:/var/tmp/jhan/tron-ci-enable` (branch `jhan-amx-deb-preset`, commit 6f37cd2ed9, base e92da643f1) |
| Package and unstripped rinzler | `delphi-3bda:/var/tmp/jhan/tron-ci-enable/gen-deb/`, copy for Rhys in `/var/tmp/jhan/ci-enable-deb/` |
| Build log | `exec/results/ci-enable-20260917/make-deb.log` |
| Package checks (with the launch command and the post-verification additions) | `exec/results/ci-enable-20260917/package-checks.txt` |
| Run-time check script, counter test program | `exec/ci-enable-20260917/{runtime-check.sh, amxspin.c}` |
| Run-time results | `exec/results/ci-enable-20260917/{runtime-check.log, summary.tsv, *.probe, *.perf-idle, *.perf-req, *.answer, *.rinzler-lines.txt}` |
| Counter validation (with a correction line) | `exec/results/ci-enable-20260917/counter-validation.txt` |
| Engine logs (debug level, 20 KB each) and the request/answer JSON files | `delphi-3bda:/var/tmp/jhan/ci-enable-out/` |
| The page this executes | https://claude.ai/artifact/M7WV3mLkkAYt8J2GW1piDu (section 1) |

## 7. Machine state after the run (delphi-3bda, 20:12 UTC)

- Our three engines exited. No FUSE mount of ours remains. Two `tail -f` log followers of this session were still running at 20:02 UTC and were stopped at 20:12 UTC. After that no process of ours remains.
- The first version of the run-time script did not remove the two hugepage slice files our engine created (`slice-4-of-8`, `slice-5-of-8`, 64 GiB each). tron names these files by slice, not by the `--hugepage_file` argument. They were removed by hand at 19:54 UTC after a check that nothing mapped them. HugePages_Free is back at 256 pages of 1 GiB, the whole of our half's share. The script now removes them itself.
- The production unit `rinzler@1` (instance 0,2, Bill's half, running since 10:13 UTC) was not touched. The Bill marker file is present, as expected. The CI lease file is absent, so no nightly run was in progress.
- Left under `/var/tmp/jhan` for Rhys and for a possible rebuild: the worktree with its build tree (25,092,690,585 bytes, 23.4 GiB), the extracted package (335,798,734 bytes, 320 MiB) and the package copy directory (132 MiB).

## 8. Verification

An adversarial verification workflow (run wf_be0461e4-7a2, 9 agents, 177 tool calls) checked the first version of this report and of the Rhys instructions between 20:03 and 20:22 UTC. For each of four claim groups, one agent re-derived every number, identifier and quote from the primary files and from read-only commands on delphi-3bda. A second agent per group looked for alternative explanations, missing controls and steps that could not work as written. A ninth agent checked the plain-English rules. Verdict counts: 135 upheld, 42 refuted (34 of them plain-English rule violations), 55 imprecise, 8 missing, 7 unverifiable. The three conclusions (AMX compiled in, AMX used at run time, kill switch works) held under every check. Corrections applied to this text:

- the perf CSV misread (the count column was 0, so per-CPU mode is not faulty);
- 16 cycles per tile multiply is the documented throughput, not the latency;
- the answer texts are not evidence of anything: the engine is not run-to-run deterministic here;
- the 146,752-byte size difference is not the AMX code (different `main` commits);
- the CI build times (21 and 19 minutes, not 24), the nightly and package-build schedule wording, the goal's slowest-user floor and the third night's mean;
- the engine environment description (debug log level, `env -u SYSTEM_CONFIG`, `LD_LIBRARY_PATH`, the shim), the derived tp2 placement, the crash-word grep timing, the speed column's meaning;
- the PR command, the env-file grep command, the publish-late failure mode in the morning-after check, the hugepage removal time (19:54 UTC), the two leftover `tail` processes, binary versus decimal sizes, the copy of the instructions on the machine;
- language: a longer "Words used here" list, one claim per sentence, bullets for multi-point paragraphs, a shorter Short version.
