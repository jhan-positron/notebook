# Proposed replacement text for pr5186-fix.md (codex items 3 and 4)

Each block below names the lines of `pr5186-fix.md` it replaces. Text outside the blocks stays as it is.

---

## A. Short version (replaces line 7)

The review comment says a default Linux boot may fail once the AP system DRAM is timed, and the run window was never re-measured. The fix puts the new AUX timing behind a build define, `HEMI_GC_AUX_TIMING`, which is off by default. A fresh default build restores the base branch's AUX timing selection, and the timed image stays one build option away. Boot completion with the current asimov-os snapshot (v0.0.22) has not been verified.

---

## B. Behavior table (replaces lines 55-58)

| Build | Gate | AUX lanes | Default Linux boot |
| --- | --- | --- | --- |
| Default (no define), fresh build | `< 16` | Untimed. Same AUX timing selection as the base branch. | Not verified. The 874M cfclk init time was measured on snapshot v0.0.20 [Ref8]. The default snapshot is now v0.0.22 [Ref9]. No boot was run for this fix. |
| `--define HEMI_GC_AUX_TIMING` | `< 18` | Timed, as in the PR today | Needs an explicit, larger `--run-cycles`. No timed boot has been measured. |

---

## C. Estimate section (replaces lines 81-92 of "Why not raise the run window instead")

- No boot with timed AUX lanes has been measured.
- The only transaction count in the repo is 1,782,918 reads and 2,867,850 writes [Ref6].
- The count is a full-chip logged total. It covers both hemispheres together.
  - Both hemispheres wrote to one log file, `fc_sys_mem.log` [Ref10].
  - The launcher counted every read line and every write line in that file. It did not filter by hemisphere [Ref11].
- The count covers the whole run of 1.0G cfclks, not only the part up to Linux init [Ref6].
- The run used SCP 0.30.0 in a full-chip image (`fc_tlm`) on 2026-08-28 [Ref6]. The current release SCP is 0.51.0 or later.
- Insufficient data: the per-hemisphere read and write counts up to Linux init are not recorded. The original `fc_sys_mem.log` would give them. Each line carries an `h0` or `h1` tag [Ref10]. Without that log, a new run on the current firmware is needed.

Estimates from that count. They are not measurements.

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

(Lines 93-94 of the current text stay unchanged.)

---

## D. Measurement section (replaces steps 1-6 and the "Insufficient data" paragraph, lines 120-127)

The tree gives no absolute cfclk or simulated-time stamp for a console line.

- The launcher only searches `uartout/uart_1.log` for the text `Run /... as init process` [Ref5].
- The console log is written by the Cadence UART model's C++ side, which is not in this repo [Ref12].
- The commit that introduced the 874M figure states "0.437 s (874M cfclks)". It does not say how the time was read [Ref8].

Insufficient data: a sample `uart_1.log`, or the documented log format of the Cadence UART model, would show whether a line carries a time stamp and what its time origin is. The author of commit 79450ae06 can say how 0.437 s was read.

Until then, bracket the init time with the run window. `--run-cycles N` stops the run after N cfclks [Ref13].

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
6. Repeat on the same image with `--run-only --run-cycles N`. Choose N halfway between the highest lower bound and the lowest upper bound. Stop when the two bounds are closer than 50M cfclks (5% of the 1.0G window).
   - Before each `--run-only` run, check that the `defines:` line of the build MANIFEST still contains `HEMI_GC_AUX_TIMING`. The timed and the default image share one build directory.
7. Record the result: the lowest N with verdict BOOTED (the passing upper bound), the highest valid INCOMPLETE N, the firmware and the OS snapshot from step 1, and the run directories.
8. Set the hemi-only window from the passing upper bound. The existing windows carry 12.8% margin (debug SCP: 1418M in 1.6G) and 14.4% margin (release SCP: 874M in 1.0G).
9. Check the wall-clock limits (3600 s plain, 5400 s over the PCIe VirtualBridge) against the measured run time.
10. Repeat for the debug SCP, which has its own 1.6G window.

---

## E. References (append to the list; Ref6 text unchanged)

- [Ref8] Commit 79450ae06 "emu: switch the boot stack to asimov-os v0.0.20 (scp-v0.51.0, tfa-v0.38.0)", commit message, last paragraph. The 874 figure first appears in `emu/common/scripts/asimov_os_env.sh` at commit 4810354a6.
- [Ref9] `emu/common/scripts/asimov_os_env.sh:24`
- [Ref10] `emu/fc_tlm/sim/fc_sys_mem.cpp:221-224` (one `fopen("fc_sys_mem.log", "w")` for both hemispheres) and `:141`, `:162` (the `h%d` tag on each line), at commit 2aeb9d4f4
- [Ref11] `emu/fc_tlm/scripts/run_emu.sh:482-484` at commit 2aeb9d4f4
- [Ref12] `emu/hemi_tlm/agents/hemi_uart_tty_xtor.sv:5-10`
- [Ref13] `emu/hemi_tlm/scripts/run_emu.sh:641` and `:1851`
