# PR 5186: fix for the Linux boot window review comment

Date: 2026-11-11 (UTC). PR head: 13418eb. Review comment: [Ref1]. Revision 3 of this description, after the second review.

## Short version

The review comment says a default Linux boot may fail once the AP system DRAM is timed, and the run window was never re-measured. The fix puts the new AUX timing behind a build define, `HEMI_GC_AUX_TIMING`, which is off by default, and the launcher now rejects a Linux boot on a timed image unless the caller gives an explicit run window. A fresh default build restores the base branch's AUX timing selection. Boot completion with the current asimov-os snapshot (v0.0.22) has not been verified.

The patch is in `pr5186-fix.patch` in this folder. It applies to the PR head. It has not been compiled and has not run on the emulator.

## Words used here

- **cfclk**: one cycle of the 2 GHz emulation base clock (0.5 ns).
- **AXI cycle**: one cycle of the 1 GHz lane clock. One AXI cycle is 2 cfclks.
- **AP**: the application processor, the CPU that boots Linux.
- **SCP**: the system control processor firmware that releases the AP.
- **asimov-os snapshot**: the versioned set of firmware and Linux images that the launcher boots.
- **AUX lanes**: Goldcrest pairs 16-17 (lanes 32-35). They hold the AP system DRAM.
- **DP lanes**: the 32 datapath lanes (Goldcrest pairs 0-15).
- **Gate**: the `DATAPATH_TIMING` parameter expression in `goldcrest_ew_fullconn_avip.sv`. It decides which pairs get the DDR timing profile.
- **Run window**: the `--run-cycles` value of a run, in cfclks. The default for a Linux boot comes from the helper.
- **Helper**: the bash function `asimov_os_linux_boot_cycles`, which returns the default run window.
- **Launcher**: `emu/hemi_tlm/scripts/run_emu.sh`.
- **Timed image**: an emulator image built with `HEMI_GC_AUX_TIMING`.
- **MANIFEST**: the file in the build directory that records the compiled defines.
- **LINUX verdict**: the line in the run summary that says whether the AP console reached `Run /sbin/... as init process`.
- **Mutation**: a deliberate wrong edit of the code, made to confirm that a test fails.

## The problem

- The PR changes the gate from `GC_PAIR_INDEX < 16` to `< 18` [Ref2].
- The AUX lanes then load the datapath reset profile. The read latency setting rises from 0 to 61 AXI cycles. The write response latency becomes 40 AXI cycles. A bandwidth limit of 38.4 GB/s applies.
- The run window stays at 1.0G cfclks for a release SCP at version 0.51.0 or later [Ref3].
- That window was set from a boot with untimed AUX lanes. Linux init was reached at 874M to 883M cfclks [Ref4].
- The margin is 126M cfclks at the 874M figure.
- Each AP DRAM read gains about 58 AXI cycles (est., from the PR text), which is 116 cfclks. So 126M / 116 = about 1.09M reads in series use up the whole margin.
- When init is not reached inside the window, the launcher exits with status 1 [Ref5].
- Host timing settings cannot relax the AUX lanes. They reach lanes 0-31 only.

## The fix

The fix has three parts.

### Part 1: the build define

Core change in `emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv`:

```systemverilog
`ifdef HEMI_GC_AUX_TIMING
  localparam int GC_TIMED_PAIRS = 18;
`else
  localparam int GC_TIMED_PAIRS = 16;
`endif
  hemi_gc_lane_avip #(
    .EMBEDDED        (1'b1),
    .DATAPATH_TIMING (GC_PAIR_INDEX >= 0 && GC_PAIR_INDEX < GC_TIMED_PAIRS)
  ) lane_bfm0 (
```

Both lane instances (`lane_bfm0` and `lane_bfm1`) use `GC_TIMED_PAIRS`.

| Build | Gate | AUX lanes | Default Linux boot |
| --- | --- | --- | --- |
| Default (no define), fresh build | `< 16` | Untimed. Same AUX timing selection as the base branch. | Not verified. The 874M cfclk init time was measured on snapshot v0.0.20 [Ref8]. The default snapshot is now v0.0.22 [Ref9]. No boot was run for this fix. |
| `--define HEMI_GC_AUX_TIMING` | `< 18` | Timed, as in the PR today | Rejected by the launcher unless the caller passes an explicit `--run-cycles`. No timed boot has been measured. |

### Part 2: the launcher check

A timed build and a default build write to the same build directory [Ref14]. Without a check, a default run after a timed build would boot Linux on timed AUX lanes inside the 1.0G window. That is the configuration the review comment is about.

The launcher now stops with an error in these cases:

- **Before a build.** A direct `run_emu.sh --build --define HEMI_GC_AUX_TIMING` call for a Linux boot, without `--run-cycles`.
- **Before the emulator starts.** Any Linux boot where the `defines:` line of the image's MANIFEST contains `HEMI_GC_AUX_TIMING` and the caller gave no `--run-cycles`. This covers a fresh build, a reused image and `--run-only`.

Details:

- The launcher re-starts itself on the emulator host over ssh and always forwards `--run-cycles`. A new internal flag, `--run-cycles-default`, tells the remote side that the caller did not choose the value.
- `--build-only` is accepted with the define. It does not run the emulator.
- Runs that do not boot Linux are not rejected.
- Through `emu/common/scripts/run.sh` (the common entry script), the build phase runs with `--build-only`. So the rejection comes at the run phase, after the build. No emulator run starts.

### Part 3: the tests

- `emu/hemi_tlm/tests/test_gc_timing_selection.py` (new, 1 test). It reads the wrapper source text. It evaluates the gate of both lane instances for pair indices -1, 0, 15, 16, 17 and 18, with the define absent and present.
- `emu/common/tests/test_hemi_notel.py` (5 new tests in class `HemiAuxTimingWindow`). They execute the real launcher blocks with test fixtures. They establish:
  - untimed image with the default window: accepted;
  - timed image with the default window: rejected before the emulator starts;
  - timed image with an explicit window: accepted;
  - a timed build without a window stops before the build;
  - the ssh re-start keeps the answer in both directions;
  - a timed image without a Linux boot keeps its default window.

### Files in the patch

7 files, 289 insertions, 23 deletions.

| File | Change |
| --- | --- |
| `emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv` | The `ifdef`, the `localparam`, both gates, the comment above them. |
| `emu/hemi_tlm/scripts/run_emu.sh` | The two checks, the `--run-cycles-default` flag, the ssh forwarding. 25 lines added. |
| `emu/hemi_tlm/tests/test_gc_timing_selection.py` | New test file, 109 lines. |
| `emu/common/tests/test_hemi_notel.py` | 5 new tests, 102 lines added. |
| `emu/hemi_tlm/doc/GC_DDR_TIMING.md` | Describes the AUX lanes as untimed by default. Describes the define, the launcher check and the new test. |
| `emu/hemi_tlm/doc/HOST_PROGRAM_V1.md` | One sentence: the AUX lanes are not programmable and are untimed by default. |
| `emu/hemi_tlm/scripts/setup_tree.sh` | Comment only. |

To apply, from the root of a full checkout of the PR branch:

```
git apply <path to this folder>/pr5186-fix.patch
```

## Why not raise the run window instead

The review comment offered two fixes. The other one is to re-measure the timed boot and raise the default `RUN_CYCLES`. That fix is not possible today, for these reasons.

- No boot with timed AUX lanes has been measured.
- The only transaction count in the repo is 1,782,918 reads and 2,867,850 writes [Ref6].
- The count is a full-chip logged total. It covers both hemispheres together.
  - Both hemispheres wrote to one log file, `fc_sys_mem.log` [Ref10].
  - The launcher of that time counted every read line and every write line in that file. It did not filter by hemisphere [Ref11].
- The count covers the whole run of 1.0G cfclks, not only the part up to Linux init [Ref6].
- The run used SCP 0.30.0 in a full-chip image on 2026-08-28 [Ref6]. The current release SCP is 0.51.0 or later.
- Insufficient data: the per-hemisphere read and write counts up to Linux init are not recorded.
  - The original `fc_sys_mem.log` would recover the per-hemisphere counts for the whole run. Each line carries an `h0` or `h1` tag [Ref10].
  - Counts up to init need more: evidence that ties transactions to the init event. A log line carries a sequence number and the transaction fields. It carries no time stamp and no init marker [Ref10].
  - Without both, a new run on the current firmware is needed.

Estimates from that count follow. They are not measurements.

Formulas:

- Added time for reads = reads charged x exposed fraction x 58 AXI cycles x 2 cfclks.
- Added time for writes = writes charged x 40 AXI cycles x 2 cfclks.
- Linux init (est.) = 874M cfclks + added time.

| Case | Assumption on the split | Reads charged | Exposed fraction | Writes charged | Added (est.) | Linux init (est.) | Fits 1.0G? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Equal traffic: half of the total | 891,459 | 50% | 0 | 51.7M cfclks | 925.7M cfclks | Yes, 7.4% margin |
| 2 | Equal traffic: half of the total | 891,459 | 100% | 0 | 103.4M cfclks | 977.4M cfclks | Yes, 2.3% margin |
| 3 | Equal traffic: half of the total | 891,459 | 100% | 1,433,925 | 218.1M cfclks | 1092.1M cfclks | No, 9.2% over |
| 4 | Artificial conservative: the whole total charged to one hemisphere | 1,782,918 | 100% | 0 | 206.8M cfclks | 1080.8M cfclks | No, 8.1% over |
| 5 | Artificial conservative: the whole total charged to one hemisphere | 1,782,918 | 100% | 2,867,850 | 436.2M cfclks | 1310.2M cfclks | No, 31.0% over |

How to read the table:

- "Equal traffic" is an assumption. The repo does not record the split between the two hemispheres.
- "Artificial conservative" is not a possible reading of the count. The count is a two-hemisphere total, so one hemisphere cannot have produced all of it. Cases 4 and 5 are upper limits only.
- "Exposed fraction" is the share of reads that add their full latency to the boot time. It is an assumption.
- All cases use the whole-run count. The count up to Linux init is smaller or equal.
- All cases leave out the 38.4 GB/s bandwidth limit.
- The count comes from SCP 0.30.0. The traffic of the current firmware is not known.

What the estimates show:

- Under the equal-traffic assumption, the reads alone fit the 1.0G window with 2.3% margin (case 2). With serial writes added, the boot does not fit (case 3).
- So the estimates do not decide whether a timed boot fits 1.0G. A measured timed boot is needed.
- A candidate window of 1.3G cfclks is below the case 5 upper limit of 1310.2M cfclks (est.).

Two more points:

- The earlier window changes each quote a measured init time. A window set from an estimate would break that convention.
- The helper is shared with `cmn_tlm` and `fc_tlm`, which stay untimed [Ref4]. A later raise belongs in the hemi launcher only. A change of the helper's return values would also break a unit test [Ref7].

## What was checked

All checks ran on a copy of the PR head files (`emu/hemi_tlm` and `emu/common`) with the patch applied.

- **Patch applies.** `git apply --check` passes in a fresh copy of the PR head. In the local clone it passes with `--cached` (against the index). The plain check fails there for one reason: the clone is sparse, and `emu/common/tests/test_hemi_notel.py` is not checked out.
- **Shell syntax.** `bash -n emu/hemi_tlm/scripts/run_emu.sh` passes.
- **Launcher tests.** `cd emu/common/tests && python3 -B -m unittest test_hemi_notel` ran 24 tests, all pass (19 existing, 5 new).
- **Goldcrest tests.** `python3 -B -m unittest discover -s emu/hemi_tlm/tests -p 'test_gc_*.py'` ran 30 tests, all pass (29 existing, 1 new).
- **Mutations of the wrapper.** Each of these makes the new selection test fail: default 16 changed to 18; define branch 18 changed to 16; one gate replaced by a literal `< 18`; one gate replaced by a literal `< 16`; `ifdef` changed to `ifndef`; the `>= 0` clause dropped; `&&` changed to `||`; the two instances given different expressions; `GC_TIMED_PAIRS` renamed in one place only.
- **Mutations of the launcher.** Each of these makes a new launcher test fail: the MANIFEST check removed; the pre-build check removed; the ssh forwarding without `--run-cycles-default`; the Linux-boot condition removed from the MANIFEST check.
- **Independent review.** Two review agents tried to refute the combined patch. They reported no blocker and no major problem.

Not checked:

- No SystemVerilog compile or elaboration. No simulator is installed on this machine.
- No emulator run. No Linux boot, timed or untimed.
- No real ssh re-start and no end-to-end run of the launcher. The launcher tests run extracted blocks of the script.
- The full test suites do not pass in the copy, with or without the patch. `emu/common/tests`: 15 failures and 47 errors of 205 tests. `emu/hemi_tlm/tests`: 20 failures and 14 errors of 199 tests. The failing sets are identical with and without the patch, apart from the new tests, which pass. The cause was not examined. The copy lacks most of the repo, which is a likely cause (hypothesis; a run in a full checkout would confirm it).
- No search of `emu/fc2_tlm`, which is absent from the local sparse checkout.

## Open items

- **Selection test reads source text.** It does not prove what a compiler elaborates. A `` `define HEMI_GC_AUX_TIMING `` placed outside the wrapper module would turn the timing on while the test still passes. A compile of both build modes would close this.
- **Simulation.** `run_sim.sh` has no `--define` option. Simulation always uses untimed AUX lanes.
- **Other run modes.** The launcher check covers Linux boots only. Other run modes on a timed image keep their default windows.
- **Usage text.** The usage header of the launcher does not mention the new rule. The error message states it.
- **Baseline age.** The 874M figure was measured on snapshot v0.0.20. The default snapshot is now v0.0.22.
- **PR text.** The PR summary and the risk list should say that the AUX timing is off by default.

## Measurement that later turns the timing on by default

The tree gives no absolute cfclk or simulated-time stamp for a console line.

- The launcher only searches `uartout/uart_1.log` for the text `Run /... as init process` [Ref5].
- The console log is written by the C++ side of the Cadence UART model, which is not in this repo [Ref12].
- The commit that introduced the 874M figure states "0.437 s (874M cfclks)". It does not say how the time was read [Ref8].

Insufficient data: a sample `uart_1.log`, or the documented log format of the Cadence UART model, would show whether a line carries a time stamp and what its time origin is. The author of commit 79450ae06 can say how 0.437 s was read.

Until then, bracket the init time with the run window. `--run-cycles N` stops the run after N cfclks [Ref13]. This procedure has not been executed.

1. Record the inputs once.
   - The firmware: the `firmware:` field of the run MANIFEST, and the SCP `semver` in `build-info.json` of the drop used.
   - The OS snapshot: the `asimov_os:` field of the run MANIFEST (default v0.0.22 [Ref9]).
   - The build defines: the `defines:` line of the build MANIFEST.
2. Confirm the default image. Run `emu/hemi_tlm/scripts/run_emu.sh --build`. Expect `LINUX    : BOOTED` and exit status 0. The `defines:` line must not contain `HEMI_GC_AUX_TIMING`.
3. Build the timed image and run the first, large window: `emu/hemi_tlm/scripts/run_emu.sh --build --define HEMI_GC_AUX_TIMING --run-cycles 1600000000 --timelimit 5400`. The `defines:` line must contain `HEMI_GC_AUX_TIMING`.
4. Read the verdict of each run from the run summary.
   - `LINUX    : BOOTED`: N is an upper bound on the init time.
   - `LINUX    : INCOMPLETE`: N is a lower bound, but only when the run passes the checks of step 5.
5. Exclude unrelated failures. Count an INCOMPLETE run as a lower bound only when all of these hold. Otherwise repeat the run.
   - `emu.log` contains `Ran until` with a time of N / 2 ns. This shows the run reached the window and was not cut by the wall-clock limit.
   - The summary shows `RUN END  : emulator run completed`.
   - `hemi_sys_mem.log` contains `=== PRELOAD PASS ===`.
   - `uartout/uart_1.log` is not empty. The verdict is not `NO AP CONSOLE OUTPUT`.
   - The last console line is a normal kernel boot line. It is not a panic, an oops, or a firmware error.
6. Get both bounds on the timed image before the midpoint search. Use the same firmware and snapshot for every run. Use `--run-only --run-cycles N` on the image of step 3. The untimed run of step 2 gives no bound for the timed image.
   - If the first timed run is INCOMPLETE and passes the checks of step 5: raise N (for example by 400M cfclks per run, with a larger `--timelimit`) until a run is BOOTED. That run gives the upper bound.
   - If the first timed run is BOOTED: lower N (for example 1.0G cfclks, then 874M cfclks) until a run is INCOMPLETE and passes the checks of step 5. That run gives the lower bound.
7. Then repeat on the same image with `--run-only --run-cycles N`. Choose N halfway between the highest lower bound and the lowest upper bound. Stop when the two bounds are closer than 50M cfclks (5% of the 1.0G window; the 50M value is a choice of this document).
   - Before each `--run-only` run, check that the `defines:` line of the build MANIFEST still contains `HEMI_GC_AUX_TIMING`. The timed and the default image share one build directory.
8. Record the result: the lowest N with verdict BOOTED (the passing upper bound), the highest valid INCOMPLETE N, the firmware and the OS snapshot from step 1, and the run directories.
9. Set the hemi-only window from the passing upper bound. The existing windows carry 12.8% margin (debug SCP: 1418M in 1.6G) and 14.4% margin (release SCP: 874M in 1.0G).
10. Check the wall-clock limits (3600 s plain, 5400 s over the PCIe VirtualBridge) against the measured run time.
11. Repeat for the debug SCP, which has its own 1.6G window.

## References

- [Ref1] https://github.com/Positron-AI-TSMC/asimov/pull/5186#discussion_r4532302835
- [Ref2] `emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv:647` and `:693`
- [Ref3] `emu/hemi_tlm/scripts/run_emu.sh:605-616`
- [Ref4] `emu/common/scripts/asimov_os_env.sh:68-95`
- [Ref5] `emu/hemi_tlm/scripts/run_emu.sh:2015-2029` and `:2322-2324`
- [Ref6] `emu/fc_tlm/doc/NIGHT_TASK_PLAN.md:218-225`
- [Ref7] `emu/common/tests/test_boot_firmware_selection.py:92-120`
- [Ref8] Commit 79450ae06 "emu: switch the boot stack to asimov-os v0.0.20 (scp-v0.51.0, tfa-v0.38.0)", commit message, last paragraph. The 874 figure first appears in `emu/common/scripts/asimov_os_env.sh` at commit 4810354a6.
- [Ref9] `emu/common/scripts/asimov_os_env.sh:24`
- [Ref10] `emu/fc_tlm/sim/fc_sys_mem.cpp:221-224` (one `fopen("fc_sys_mem.log", "w")` for both hemispheres) and `:141`, `:162` (the line format: `h%d` tag, `seq=`, transaction fields), at commit 2aeb9d4f4
- [Ref11] `emu/fc_tlm/scripts/run_emu.sh:482-484` at commit 2aeb9d4f4
- [Ref12] `emu/hemi_tlm/agents/hemi_uart_tty_xtor.sv:5-10`
- [Ref13] `emu/hemi_tlm/scripts/run_emu.sh:641` and `:1851`
- [Ref14] `emu/hemi_tlm/scripts/run_build.sh:386-401` and `emu/hemi_tlm/scripts/run_emu.sh:736-753`
