# Trying the AMX-enabled tron package on the AMD nightly machine (andoria-b1a3)

Written 2026-09-17 for Rhys. Author: jhan (with Claude). A copy of this file sits next to the package on delphi-3bda (`/var/tmp/jhan/ci-enable-deb/README-for-Rhys.md`).

## Short version

We built the tron apt package the way the nightly CI builds it, with one change: the AMX attention kernels are compiled in. On the Intel machine (delphi-3bda) the package has the AMX code and uses it at run time. Please install the same package on andoria-b1a3 (AMD, no AMX) and check that it installs, runs, and takes the existing AVX path.

## Words used here

- **tron**: the inference program under test. **rinzler**: its production server binary. The apt package `tron` ships rinzler at `/opt/positron/bin/rinzler`. **runtron**: tron's command-line tool (not in the package).
- **engine**: one rinzler process serving one model, run as the systemd unit `rinzler@N`. **platformd**: the service on each machine that starts and configures the engines. **unit file**: the systemd service definition of `rinzler@N`.
- **the nightly**: the System CI workflow in the repo positron-ai/systems_test. On andoria-b1a3 it is scheduled at 03:00 UTC. It ran from about 03:09 to about 12:45 UTC on 2026-09-15 and 2026-09-16. It writes the lease file `/run/lock/systems-test-ci.lease`, then runs `apt-get remove -y tron`, `apt-get update`, `apt-get install -y tron` and `apt-get upgrade -y` over ssh, then the functional, performance, MMLU and soak tests.
- **AMX**: Intel Advanced Matrix Extensions, CPU instructions that multiply small matrices in one step. Intel Xeon 6 has them. AMD EPYC does not.
- **the AVX path**: the existing attention code written with AVX-512 vector instructions. Both CPU makers support it.
- **TRON_AMX_DISPATCH**: the CMake build option that compiles the AMX code in. It was off in every nightly package so far. This test package has it on.
- **TRON_AMX_DISABLE**: the run-time kill switch. Setting it to exactly `1` in the engine environment turns AMX off even in this package.
- **the probe**: tron's one-time check whether AMX may be used. It checks the kill switch, then the CPU feature bits, then whether Linux enabled the tile state. Only when all three pass does it ask Linux for permission with the system call `arch_prctl(0x1023, 18)`. On an AMD CPU the feature bits say "absent", so the system call never happens. That system call is the only outside sign of the probe. tron writes no log line about AMX. The probe runs at the first attention call that could use AMX. Such a call needs a context of more than 64 tokens (one KV page, a 64-token block of the key/value cache) on an eligible model. The result is kept for the life of the process.
- **CPU attention / FPGA attention**: attention is the per-token lookup over the earlier tokens of a request. For the ingested models (qwen-3-4b, gpt-oss) tron computes it on the FPGA cards for token positions 127 and later. The hand-written models (the three llama models, mixtral, qwen-2.5-32b, gemma-2-9b) compute it on the CPU. The AMX code replaces CPU attention only. The models whose shape the AMX kernels accept are llama-3.1-8b-instruct-good and mixtral-8x7b (4 query heads per KV head, head size 128), and qwen-3-4b when its attention is forced onto the CPU with `USE_HW_ATTN=0`.
- **nix develop**: tron's developer shell, provided by the nix package manager. **uv**: the Python package manager the build uses. **ccache**: a compiler cache that reuses earlier compile results.

## 1. The package

| Item | Value |
|---|---|
| Source | tron `main` at e92da643f1 (2026-09-17 18:16 UTC) plus one commit, 6f37cd2ed9, on branch `jhan-amx-deb-preset` (not pushed) |
| The change | `CMakePresets.json`, preset `deb`: one added line `"TRON_AMX_DISPATCH": "ON"`, plus a comma on the line before it (2 insertions, 1 deletion) |
| Build command | `make ingest-deps` then `make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb`, outside `nix develop`, on delphi-3bda (Ubuntu 22.04.5, Clang 19.1.7; the CI package builder logged the same compiler version in runs 35044660449 and 35171163989) |
| Package version | `2026.09.17-6f37cd2e-jhan-amx-deb-preset` (the branch name is part of the version, so it cannot be confused with a nightly package) |
| File | `tron_2026.09.17-6f37cd2e-jhan-amx-deb-preset_amd64.deb` |
| Size | 137,904,212 bytes |
| sha256 | `a2dc67bafbd690bbfc9e795064ea7dd93484f44bae39bac1178f1b13b7ec8a87` |
| Where to get it | `delphi-3bda.positron.internal:/var/tmp/jhan/ci-enable-deb/`. The file is world-readable (directory 755, file 644), so the `positron` account can copy it. The exact `scp` command is in step 3 below. |
| Package contents check | `make test-deb-package-contents` passed on the file |
| Dependencies | the `Depends` field is identical to the nightly package's (checked with `dpkg-deb --field`) |

What we saw on delphi-3bda (Intel), details in `Thursday-report.md` next to this file:

- The package binary contains the AMX code: `strings` finds the `TRON_AMX_DISABLE` text once, and `objdump` finds 86 AMX tile instructions. The nightly package of the same day (2026.09.17-31b80a18) has 0 of both.
- The packaged rinzler used AMX while serving qwen3-4b (`ingested-qwen-3-4b-instruct-2507-tp2`) on delphi-3bda. With attention on the CPU, the probe made the `arch_prctl(0x1023, 18)` call and Linux granted it. The CPU's AMX unit logged 873 million busy cycles during 3 requests (about 0.2 s of one core at 4 GHz) and 0 while idle.
- With the kill switch `TRON_AMX_DISABLE=1` the same binary made no such call and logged 0 AMX-busy cycles.
- With the nightly's default setting for qwen (FPGA attention) the probe was also granted and the AMX unit logged 501 million busy cycles.
- No engine crashed.

## 2. What to check on andoria-b1a3, step by step

Expected outcome on AMD:

- the package installs like any nightly package;
- the engines start and serve, and none crashes;
- the probe never makes the `arch_prctl(0x1023, ...)` call;
- the performance numbers stay where they were (the AVX path runs as before).

We verified this fallback once before on andoria-06 with a developer build of runtron from the PR 3879 branch at 47f6f2dceb, before it merged (2026-09-11). The probe code has not changed since. This is the first check with the packaged rinzler.

**Where each step runs.** Steps 2, 4, 5, 6, 7 and 9 run on andoria-b1a3 (`ssh positron@andoria-b1a3.positron.internal`). Step 3 runs wherever you have ssh access to delphi-3bda. If that is the CI runner host, copy in two hops (to the runner, then to `positron@andoria-b1a3:/tmp/`). Step 8 runs on a host with a systems_test checkout.

**Before you start: the lease.** Run `cat /run/lock/systems-test-ci.lease` on andoria-b1a3. The nightly holds the machine only if the file exists, its `state` is `busy` and the current time is before `expires_at_epoch`. Otherwise the machine is free.

1. **Pick a time outside the nightly.** The nightly on andoria-b1a3 starts at 03:00 UTC and runs until about 12:45 UTC. Its first step removes and reinstalls `tron` from the apt server. So the next nightly replaces this test package by itself, and you do not need to roll back before it.

2. **Record what is installed now**, so the roll-back target is known:

        dpkg -l tron | tail -1
        strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE      # expect 0 today

3. **Copy the file and check it:**

        scp positron@delphi-3bda.positron.internal:/var/tmp/jhan/ci-enable-deb/tron_2026.09.17-6f37cd2e-jhan-amx-deb-preset_amd64.deb /tmp/
        sha256sum /tmp/tron_2026.09.17-6f37cd2e-jhan-amx-deb-preset_amd64.deb      # expect a2dc67bafbd690bbfc9e795064ea7dd93484f44bae39bac1178f1b13b7ec8a87

4. **Install it.** `apt-get install` with a path to the local `.deb` file (any argument containing a slash) installs that file and resolves its dependencies from the apt server. The dependencies are identical to the nightly package's:

        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/tron_2026.09.17-6f37cd2e-jhan-amx-deb-preset_amd64.deb

   If the installed version is newer than 2026.09.17 (for example the 2026.09.18 nightly package), apt treats this as a downgrade and needs `--allow-downgrades` (checked with `dpkg --compare-versions`). The package's post-install step creates the service directories, sets the setuid bit on `fusermount3`, refreshes the loader path (`ldconfig`) and reloads the systemd unit files. No package script stops or restarts a running engine [tron packaging/postinst]. Until step 6 the engines still run the old binary.

5. **Check the installed binary.** These two counts do not depend on the CPU, so they must match the Intel numbers:

        strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE                        # expect 1
        objdump -d --no-show-raw-insn /opt/positron/bin/rinzler | grep -c -E '(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)'   # expect 86

   `nm` does not work here: the package binary is stripped.

6. **Restart the engines and watch them come up.** Use your normal way (the `system_ci` or `perf` run provisions the engines through platformd, which restarts them, or `sudo systemctl restart rinzler@N`). Then:

        systemctl list-units 'rinzler@*' --no-legend                                   # every unit "active running"
        sudo journalctl -u 'rinzler@*' --since '-10 min' | grep -c 'Version:'          # one per started engine; a growing count means a restart loop
        sudo journalctl -u 'rinzler@*' --since '-10 min' | grep -m2 'Version:'         # expect 2026.09.17-6f37cd2e-jhan-amx-deb-preset
        sudo journalctl -u 'rinzler@*' --since '-10 min' | grep -E 'status=4/ILL|code=(killed|dumped)|Failed with result'   # expect no output

   tron has no handler for an illegal instruction. A crash from an AMX instruction on an AMD CPU would therefore appear only as systemd's line `Main process exited, code=killed, status=4/ILL` (or `code=dumped`). The probe is there to prevent exactly that.

7. **Show that the probe stops at the CPU check (the direct fallback proof).**

   7a. Find an engine that serves a CPU-attention model whose shape the AMX kernels accept (llama-3.1-8b-instruct-good or mixtral), its pid and its port. After a nightly the loaded models are whatever the last phase left, so llama-3.1-8b may not be loaded. Then provision it first, or use qwen-3-4b with `USE_HW_ATTN=0` in a hand-started engine.

        for u in $(systemctl list-units 'rinzler@*' --no-legend --plain | awk '{print $1}'); do echo "$u pid $(systemctl show -p MainPID --value $u)"; done
        sudo grep -h -E '^RZ_CLI_ARGS=' /etc/rinzler/instance-*.env      # the --model list and --port of every instance
        ps -o pid,args -C rinzler | cut -c1-200                            # the same, from the live processes

   7b. Attach strace to that engine before it serves its first request after the restart. Then send one request that builds a context longer than 64 tokens (one KV page). A shorter request never reaches the AMX gate, so it would prove nothing even on Intel.

        sudo strace -f -e trace=arch_prctl -p <pid>     # leave it attached
        # in another shell, to the engine's own port:
        python3 -c 'import json; print(json.dumps({"model": "llama-3.1-8b-instruct-good-tp2", "messages": [{"role": "user", "content": "Summarise in five sentences: " + ("The engineering team is analysing the cache hierarchy of a new server platform. " * 60)}], "max_tokens": 128}))' \
          | curl -s http://127.0.0.1:<port>/v1/chat/completions -H 'Content-Type: application/json' -d @- | head -c 300

   What to expect and what to mind:

   - Expected on AMD: strace prints nothing for `arch_prctl(0x1023, ...)`. This is a null result. It means "the probe stopped before the system call". It carries weight because the same request shape on Intel does produce the call.
   - The Intel control: on delphi-3bda the shim (below) recorded `arch_prctl(0x1023, 18) = 0` once per engine. With strace 5.16 the expected print form is `arch_prctl(0x1023 /* ARCH_??? */, 0x12) = 0` (strace does not know the request name). That strace line is expected output. We have not yet observed it with rinzler, because both earlier checks used the shim.
   - Attach to the running unit's process. Do not start rinzler under strace. The unit's environment, user and FUSE mount come from systemd, and an unprivileged strace also breaks `fusermount3`, the privileged helper that mounts rinzler's statistics directory (seen on 2026-09-11 with runtron).
   - strace pauses every thread at every system call while attached. Detach (Ctrl-C) as soon as the request has answered.
   - The probe result is cached for the life of the process. On Intel an engine that already answered a request before you attached will not show the call again. On AMD the call never happens, so attach timing only matters for an Intel control.
   - Alternative without strace: the 36-line LD_PRELOAD shim `~jhan/workspace/intel-AMX/exec/amd-amx-20260911/amxprobe.c` logs the same call to a file. Build it on andoria-b1a3 with `gcc -shared -fPIC -O2 -o amxprobe.so amxprobe.c -ldl`. Then put `LD_PRELOAD=/path/amxprobe.so AMXPROBE_FILE=/tmp/amxprobe.txt` in the engine environment. That fits a hand-started engine better than the systemd units.

8. **Run the usual numbers.** The nightly's own perf phase is the reference. It needs:

   - a systems_test checkout after `uv sync`;
   - ssh access as `positron@andoria-b1a3` (the script provisions the engines through platformd);
   - `HF_TOKEN` as the nightly exports it (for the tokenizers of gated models);
   - time: it covers all perf models one after another (llama 3b/8b/70b at tp2 and tp4, mixtral, qwen-2.5-32b, qwen-3-4b tp2 and tp4, gemma-2-9b, gpt-oss-120b) and takes as long as the nightly's perf phase. Without `PUBLISH=1` it posts nothing to Slack.

        PLATFORM_TYPE=genoa96_rinzler OPENAI_HOST=http://andoria-b1a3.positron.internal/v1 PLATFORMD_PORT=8081 OPENAI_TOKEN=token-secret uv run perf

   Expected: every row of the perf table stays inside its night-to-night range of the last seven nightly runs (the difference between the highest and the lowest value of that row). The nightly's posts in Slack #ci-cd-notifications hold the per-model rows for andoria-b1a3 (threshold 195/170 TPS for qwen-3-4b tp2). There is no reason for a change on AMD. A change larger than that range would be a finding in itself.

9. **Roll back if you want the machine back on the nightly package before 03:00 UTC:**

        sudo apt-get update
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades tron=<the version from step 2>

   If the apt server no longer holds that version, the recent nightly packages are still in `/var/cache/apt/archives/` on the machine: `sudo apt-get install -y --allow-downgrades /var/cache/apt/archives/tron_<version>_amd64.deb`.

## 3. What to send back

- The `dpkg -l tron` line after step 4.
- The two counts from step 5.
- The `Version:` line and the crash grep from step 6.
- Whether strace in step 7 printed an `arch_prctl(0x1023` line (expected: no), and which model, port and request you used.
- The perf rows from step 8, or the run's Slack post if you let it publish.

## 4. If you prefer to build the package yourself

Apply this change to `CMakePresets.json` on `main` and run `make deb` from a plain shell, not inside `nix develop`. The makefile refuses `make deb` inside that shell. The reason is that the bundled tokenizer (the text-to-token program shipped in the package) would then point at `/nix/store` paths and break on a plain Debian or Ubuntu machine.

    @@ -76,7 +76,8 @@
             "BUILD_NATIVE": "OFF",
             "BUILD_PRODUCTION_MODELS": "ON",
             "BUILD_INGEST_MODELS": "ON",
    -        "ENABLE_FUSE_STATS": "ON"
    +        "ENABLE_FUSE_STATS": "ON",
    +        "TRON_AMX_DISPATCH": "ON"
           }
         },

The build needs `clang-19`, `lld-19`, `ccache`, `ninja`, `cmake`, `uv`, and the Haskell toolchain from `ghcup` on the path (`export PATH="/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH"` on our machines). On delphi-3bda `make deb` took 10 min 50 s (12 minutes with `make ingest-deps` and the package-contents test) with `NPROC_BUILD=48` (48 parallel compile jobs; the makefile default is 16) and ccache enabled. The CI package builder's "Build .deb" step took 21 minutes on 2026-09-16 with 16 jobs. The build exports the ingested models with torch. On delphi-3bda it found the model configuration files in the Hugging Face cache without a token. On another machine it may need `HF_TOKEN`.
