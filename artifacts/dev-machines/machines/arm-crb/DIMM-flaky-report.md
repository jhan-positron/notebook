# CRB: memory module count changes between boots

Report date: 2026-11-17. Machine: CRB, host address 192.168.2.45.

## Short version

CRB (the Arm reference server) started with only 10 of its 12 memory modules in 5 of 12 boots at the memory speed 8000 MT/s. The firmware removes the modules before Linux starts, so Linux is not the cause. After the change to 7200 MT/s, which Arm recommends for this firmware version, 6 of 6 reboots gave 12 modules, and the setting is still in place.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm Phoenix Reference Server. It has 128 Neoverse V3AE cores.
- **DIMM**: one memory module. CRB has 12 slots, 6 per half of the chip.
- **CP0, CP1**: the two halves of the chip in the slot names. `DIMM_CP0_5` is slot 5 of half 0.
- **DDR5**: the memory standard of the modules.
- **MT/s**: million transfers per second, the unit of memory speed.
- **GiB, KiB**: 2^30 bytes and 2^10 bytes. A "32 GB" module holds 32 GiB.
- **Firmware**: the software that starts the machine before Linux. Version on CRB: `AGI-CPU-CRB-v0.7.2`.
- **Training**: the step at power-on where the firmware tunes the signal timing of each memory module.
- **DCS**: a control signal of a DDR5 module. "DCS delay training" is one training step.
- **EVT0, EVT1**: revisions of the circuit board. EVT1 is the later one.
- **SMBIOS**: the table in which the firmware lists the hardware for the operating system. The command `dmidecode` prints it.
- **Journal**: the log store of Linux. It keeps the kernel log of earlier boots.
- **Boot**: one start of Linux. Boot 0 is the newest boot in the logs saved on 2026-11-17 06:30 UTC, and boot -11 is the oldest.
- **Error record**: a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the kernel log with the tag `[Hardware Error]`. Its severity is "corrected" (hardware repaired it) or "recoverable" (not repaired, system continues).
- **EDAC**: the Linux subsystem that counts memory errors.
- **BMC**: the management controller on the board. It works independently of Linux.
- **SCP**: the system control processor. It runs the first firmware stage.
- **TXREQ settings**: firmware settings that limit the read requests of the cores. They are not memory settings.
- **bwx12**: our memory benchmark program. Its "old read loop" (name `oldread`) loads data and adds it up. Its "load-only loop" (name `asmread`) only loads data.
- **120 threads**: 64 threads on half 0 plus 56 threads on half 1.
- **Load average**: the mean number of running or waiting processes over 1 minute, as Linux reports it.
- **UTC**: the time zone of all times in this report.
- **est.**: estimated, not measured directly.

</details>

## 1. The problem

- CRB has 12 memory modules of 32 GiB each.
- Some boots show all 12 modules. The kernel then reports 377.0 GiB of usable memory.
- Other boots show 10 modules. The kernel then reports 314.0 GiB.
- No boot in the saved logs shows 11 modules.
- The count can change at every reboot at the memory speed 8000 MT/s.

## 2. Hardware and software state

| Item | Value |
|---|---|
| Firmware | `AGI-CPU-CRB-v0.7.2`, date field `09/08/2026` |
| Board version | EVT0 (motherboard version field: A1DI0) |
| Kernel | `7.1.3-arm-agi-20260916-v0.7.2`, the same in all 12 saved boots |
| Memory modules | 12 x 32 GiB DDR5 registered modules, Micron, part `MTC20F2085S1RC80BH1 NCKK`, 2 ranks |
| Memory speed until 2026-11-17 19:43 UTC | 8000 MT/s (firmware setting "DIMM Frequency") |
| Options of "DIMM Frequency" | 3200, 6400, 7200, 8000 MT/s |
| "DIMM 0 Enable" to "DIMM 5 Enable" | all 1 (enabled) |
| Module supply voltage settings ("DIMM PMIC VDD", "DIMM PMIC VDDQ") | 1100 mV each |

- The firmware version, its date and the board version come from the identity output of the settings tool [Ref1].
- The motherboard version field comes from `dmidecode -t 2` [Ref12].
- The module data come from the SMBIOS module list [Ref2].
- The settings come from the firmware settings list [Ref3].

## 3. Boot history at 8000 MT/s

The table lists all 12 boots that the journal of CRB held on 2026-11-17 06:30 UTC.

| Boot | Linux start | Modules | Usable memory | Error records | Gap before this boot |
|---|---|---|---|---|---|
| -11 | 2026-09-29 01:42 | 12 | 377.0 GiB | 0 | not known |
| -10 | 2026-09-29 02:09 | 12 | 377.0 GiB | 1 recoverable | 535 s, type of restart not known |
| -9 | 2026-10-03 15:34 | **10** | 314.0 GiB | 0 in 35 s of log | 2 days |
| -8 | 2026-10-05 15:52 | 12 | 377.0 GiB | 0 | 2 days |
| -7 | 2026-10-20 19:06 | 12 | 377.0 GiB | 0 | 213 s, no shutdown logged |
| -6 | 2026-10-22 05:43 | **10** | 314.0 GiB | 301 corrected | 231 s |
| -5 | 2026-11-09 21:20 | 12 | 377.0 GiB | 321 corrected | 4 days |
| -4 | 2026-11-17 03:48 | **10** | 314.0 GiB | 4 corrected | 260 s |
| -3 | 2026-11-17 03:57 | **10** | 314.0 GiB | 5 corrected | 238 s |
| -2 | 2026-11-17 04:09 | 12 | 377.0 GiB | 0 | 203 s |
| -1 | 2026-11-17 04:17 | **10** | 314.0 GiB | 21 corrected | 237 s |
| 0 | 2026-11-17 05:45 | 12 | 377.0 GiB | 1 recoverable | 224 s |

- Totals: 7 boots with 12 modules, 5 boots with 10 modules.
- The module count comes from the kernel line `ghes_edac: This system has N DIMM sockets` [Ref4].
- The memory size comes from the kernel line `Memory: ...K/...K available` [Ref4]. The total in that line differs by exactly 64 GiB between the two states. That equals two modules.
- "Gap before this boot" is the time between the last journal line of the previous boot and the first kernel line of this boot. For a direct reboot it is an estimate of the firmware start time plus the Linux shutdown.
- The saved log of boot -9 covers only 35 s and ends at a clock jump. Its start time and record count are not reliable.
- Boots -4 to -1 are the four reboots of the settings test in section 6.1. The settings test did not start boot 0.

Periods in one state:

- 12 modules from 2026-10-05 to 2026-10-22 (boots -8 and -7, 16.6 days).
- 10 modules from 2026-10-22 to at least 2026-11-05 (boot -6, at least 14.7 days).
- 12 modules from 2026-11-09 to 2026-11-17 03:44 (boot -5, 7.3 days).

## 4. Which modules are missing

The two 10-module listings that were read miss the same two slots: slot 5 on each half.

```
Half 0 (CP0):  [0] [1] [2] [3] [4] [5 missing]
Half 1 (CP1):  [0] [1] [2] [3] [4] [5 missing]
```

| Slot | Serial number | In 12-module listing | In 10-module listing |
|---|---|---|---|
| `DIMM_CP0_5` | 00-2c-0f-26-09-568a26d4 | yes | no |
| `DIMM_CP1_5` | 00-2c-0f-26-09-568a449a | yes | no |

- The 12-module listing was taken on 2026-11-17 06:29 (boot 0) [Ref2].
- One 10-module listing was taken on 2026-10-30 (boot -6) [Ref5].
- A second 10-module listing was read on 2026-11-17 during a 10-module boot. It showed the same two slots missing. That output was not saved to a file.
- The other 10 slots carry the same serial numbers in both saved listings.
- Insufficient data for the other three 10-module boots: no module listing exists for them. A `dmidecode -t 17` output from each future 10-module boot would resolve it.

## 5. Checks done to exclude Linux and settings

All checks were read-only. They ran on 2026-11-17 at 06:30 with 12 modules present.

| Check | Result | Meaning |
|---|---|---|
| Memory total in the kernel log | 64 GiB smaller in a 10-module boot [Ref4] | The firmware removes the modules before Linux starts |
| SMBIOS module list | 10 entries in a 10-module boot, 12 entries otherwise [Ref2] [Ref5] | Same as above |
| Kernel version | The same in all 12 boots [Ref4] | No kernel change explains the difference |
| Kernel command line | Two forms. Boots -6 to 0 add CPU isolation and governor options. Both forms gave 10 and 12 modules [Ref4] | The command line does not explain the difference |
| Memory limit option on the command line | None in both forms [Ref4] | Linux does not limit memory |
| Offline memory blocks | 0 (read live, output not saved) | Linux has not switched memory off |
| Firmware settings | "DIMM 0 to 5 Enable" = 1 [Ref3] | No setting disables a module |
| Linux EDAC counters | 0 corrected, 0 uncorrected (read live, output not saved) | Not meaningful here. Section 7 gives the reason |
| Link from Linux to the BMC | No `/dev/ipmi*` device exists (read live, output not saved) | Linux cannot read the BMC logs |

- The load average was 0.00 during these checks (read live, output not saved).
- Conclusion: the firmware decides the module count. Linux only reports it.

## 6. Test results

### 6.1 Reboot test at 8000 MT/s

- On 2026-11-17 the TXREQ settings were changed for a different investigation.
- The test needed four reboots (boots -4 to -1).
- The module counts of these boots were 10, 10, 12, 10.
- The count did not follow the settings. One changed settings state gave 10 modules in two boots. The original settings gave 12 modules in boots -5 and 0, and 10 modules in boot -1.
- All settings were set back to the original values. The settings list after the revert has the same 1490 entries as the original list [Ref3]. 607 entries have a readable value. 883 entries show "value unavailable" in both lists, so their values were not compared.

### 6.2 Effect of the module count on memory read rates (8000 MT/s)

The table shows total read rates of bwx12 with the original firmware settings.

| Test case | 12 modules | 10 modules | Change |
|---|---|---|---|
| 120 threads, old read loop | 468.1 / 467.4 GB/s | 362.2 / 359.9 GB/s | -23 % |
| 120 threads, load-only loop | 300.2 / 298.7 GB/s | 274.5 / 271.8 GB/s | -9 % |
| 64 threads on half 0 only, old read loop | 348.1 GB/s | 346.7 GB/s | -0.4 % |
| 56 threads on half 1 only, old read loop | 318.6 GB/s | 319.3 GB/s | +0.2 % |
| 1 thread, old read loop | 33.1 GB/s | 31.6 GB/s | -4.6 % |

- The 120-thread rows give two measurement intervals of 6 s each. The 64-thread and 56-thread rows give one interval of 6 s. The 1-thread row gives one interval of 3 s.
- With the old read loop the 120-thread rate is 23 % lower with 10 modules.
- A full half alone (64 or 56 threads) changes by less than 1 %.
- So a comparison of whole-chip rates between a 10-module boot and a 12-module boot is invalid.
- Run folders: `w120-R8-20261117T020549Z` (12 modules) and `w120-BASEd10-20261117T041738Z` (10 modules) [Ref6].
- Each state has one run with the original settings. Three more runs with changed TXREQ settings exist from the same day [Ref6]. They repeat the old-read-loop values: 470.7 / 469.4 GB/s with 12 modules, and 361.5 / 359.6 and 361.2 / 359.6 GB/s with 10 modules.
- In those three runs the load-only loop with 10 modules is between 260 and 286 GB/s. So the -9 % of the load-only loop is one sample of a wider range.
- In those runs the 1-thread rate differs by 0.7 % between the states. So the -4.6 % of the 1-thread row is not confirmed.
- System load: the 1-minute load average at the 120-thread launch was 0.00 (12 modules) and 0.26 (10 modules). At the 64-thread launch it was 71.3 and 72.1. At the 1-thread launch it was 52.5 and 57.0. Hypothesis for the high values: they are the remainder of the script's own previous 120-thread launch. No other user was logged in.

### 6.3 Reboot test at 7200 MT/s

Arm's changelog recommends 7200 MT/s for firmware 0.7.2 [Ref8]. The machine owner approved the change on 2026-11-17.

- At 19:43 the setting "DIMM Frequency" was changed from `8000 MT/s` to `7200 MT/s`. The tool confirmed the change.
- CRB was then rebooted 6 times in a row. The number 6 was fixed before the first reboot.
- No other user was logged in, and the load average was 0.00 before the first reboot.

**How the speed was changed**

The change was made from Linux with `uefisettings`. This is a tool from Arm's support kit that reads and writes firmware settings. No firmware menu was used.

```
# 1. Read the current value (answer: "8000 MT/s").
cd ~/cache-perf/uefisettings-20261117
sudo ./uefisettings hii get "DIMM Frequency"

# 2. Write the new value. The reply must show: modified: true
sudo ./uefisettings hii set "DIMM Frequency" "7200 MT/s"

# 3. Read it again (answer: "7200 MT/s").
sudo ./uefisettings hii get "DIMM Frequency"

# 4. Reboot. The firmware applies the setting at the next start.
sudo systemctl reboot

# 5. After the reboot, check the speed and the module count.
sudo dmidecode -t 17 | grep "Configured Memory Speed" | sort | uniq -c
sudo dmesg | grep "DIMM sockets"
```

- The tool is a copy of the file `svk-release/phx-soc-utils/tools/uefisettings/bin/uefisettings` from Arm's kit. Its checksum was compared with the file `uefisettings.sha256` of the kit. It needs root rights.
- The reply of step 2 showed `answer: "7200 MT/s"` and `modified: true` [Ref12].
- Step 5 showed `12 Configured Memory Speed: 7200 MT/s` after each of the 6 reboots [Ref12].
- To go back to the old speed, run step 2 with `"8000 MT/s"` and reboot.
- Arm's changelog describes a second way: enter UEFI Setup at start, open the `Device Configuration` menu, change the speed setting from `8000 MT/s` to `7200 MT/s`, save, and reboot [Ref8]. This way was not used and not tested here.

**Reboot results**

| Try | Linux start | Modules | Module speed in SMBIOS | Error records | Gap before this boot |
|---|---|---|---|---|---|
| 1 | 19:46:07 | 12 | 7200 MT/s | 0 | 170 s |
| 2 | 19:49:20 | 12 | 7200 MT/s | 0 | 176 s |
| 3 | 19:52:35 | 12 | 7200 MT/s | 0 | 181 s |
| 4 | 19:55:49 | 12 | 7200 MT/s | 0 | 177 s |
| 5 | 19:59:05 | 12 | 7200 MT/s | 1 recoverable (DDS1_CP1, first second of the boot) | 182 s |
| 6 | 20:02:16 | 12 | 7200 MT/s | 0 | 181 s |

- Result: 6 of 6 boots show 12 modules [Ref12].
- At 8000 MT/s, 5 of 12 boots showed 10 modules. If that rate still applied, 6 boots with 12 modules would occur with a probability of 3.9 % (est., from (7/12)^6). So the result supports the speed as the cause, and it does not prove it.
- The gaps are 170 to 182 s. At 8000 MT/s the direct reboots had gaps of 203 to 260 s (section 3). So the firmware starts faster at 7200 MT/s.
- Tries 1 to 5 ran Linux for 10 to 17 s only. All 6 tries were warm reboots. A start after power-off was not tested.

Memory test at 7200 MT/s (in the boot of try 6, started 15 s after the Linux start):

| Test case (bwx12) | 8000 MT/s, 12 modules | 7200 MT/s, 12 modules | Change |
|---|---|---|---|
| 120 threads, old read loop | 468.1 / 467.4 GB/s | 468.5 / 467.4 GB/s | +0.0 % |
| 120 threads, load-only loop | 300.2 / 298.7 GB/s | 302.8 / 301.9 GB/s | +1.0 % |
| 120 threads, loop `read_nop256` (a load loop with padding instructions) | 547.8 / 547.6 GB/s | 560.9 / 561.2 GB/s | +2.4 % |
| 64 threads on half 0 only, old read loop | 348.1 GB/s | 349.2 GB/s | +0.3 % |
| 56 threads on half 1 only, old read loop | 318.6 GB/s | 319.8 GB/s | +0.4 % |
| 1 thread, old read loop | 33.1 GB/s | 31.0 GB/s | -6.3 % |

- The lower memory speed did not lower any multi-thread read rate of this benchmark. The largest change is +2.4 %.
- The 1-thread value is one interval of 3 s. It is not confirmed by a repeat.
- The two runs lasted 3.6 minutes in total with up to 120 threads. The kernel log showed 0 error records afterwards.
- System load: the 1-minute load average was 0.34 at the 120-thread launch. It was 72.0, 64.2 and 56.9 at the 64-thread, 56-thread and 1-thread launches. Hypothesis: these are the remainder of the script's own previous launch. No other user was logged in.
- Run folders: `w120-w120-F72d12-20261117T200231Z` and `w120-w120-F72d12g-20261117T200504Z` [Ref12].
- Each speed has one run. Write tests and mixed read and write tests were not run at 7200 MT/s.

State of CRB after the test (2026-11-17 20:06): "DIMM Frequency" = `7200 MT/s`, 12 modules, all other settings unchanged. The setting was not set back.

## 7. Error records in the kernel log

- The kernel log holds firmware error records of a vendor-specific type. The type identifier is `bf32d4d5-b427-4025-8495-8a9e5d4030e4`.
- Linux prints `section type: unknown` for this type. This is the reason why the EDAC counters stay at 0.
- No kernel message names a DIMM, DRAM or training error. The only DIMM line is the count line of section 3.
- Each record carries a source name such as `DDS2_CP0`. Insufficient data on the meaning of these names. Arm can decode the records.

Record counts per source name at 8000 MT/s [Ref4]:

| Boot | Modules | Records | Source names (count) |
|---|---|---|---|
| -6 | 10 | 301 corrected | DDS5_CP1 (112), DDS1_CP0 (98), DDS2_CP0 (38), DDS6_CP1 (36), DDS1_CP1 (2), DDS5_CP0 (2), no name logged (13) |
| -5 | 12 | 321 corrected | DDS3_CP0 (123), DDS7_CP1 (119), DDS2_CP0 (28), DDS6_CP1 (25), DDS1_CP0 (11), DDS5_CP1 (11), 4 other names (1 each) |
| -4 | 10 | 4 corrected | DDS1_CP0 (2), DDS5_CP1 (2) |
| -3 | 10 | 5 corrected | DDS6_CP1 (2), DDS1_CP1 (1), DDS2_CP0 (1), DDS5_CP0 (1) |
| -1 | 10 | 21 corrected | DDS6_CP1 (11), DDS2_CP0 (9), no name logged (1) |
| -10, 0 | 12 | 1 recoverable each | DDS1_CP1, in the first second of the boot |

Observations:

- Records appear in both states. So the errors are not limited to 10-module boots.
- The most frequent source names differ between the two long boots. In boot -6 (10 modules) they are DDS5_CP1 and DDS1_CP0. In boot -5 (12 modules) they are DDS3_CP0 and DDS7_CP1.
- In boot -5 no record appears for the first 3.9 days. The first record is at 2026-11-13 18:13:12. A bwx benchmark run had started at 18:12:22, and the record came during its 1-thread phase. The first 120-thread step of that run started at 18:17:21.
- In boots -4, -3 and -1 the first record comes 0 to 41 s after the launch of a 120-thread memory test.
- Boot -2 (12 modules) ran the same 120-thread test for about 3.5 minutes and logged 0 records.
- In boot -6, 68 records appear on 6 days before my first saved test folder of 2026-10-30. Insufficient data on the machine load on those days.
- Hypothesis: the records are corrected errors of the memory links, and memory traffic triggers them. The evidence is mixed, as the bullets above show. The decoding by Arm would confirm or reject it.

## 8. Likely cause

**Most likely: memory training fails for slot 5 at 8000 MT/s on this board. This is a hypothesis. The test of section 6.3 supports it.** The evidence from Arm's documents:

- Arm's user guide for firmware 0.9.0 lists a known open issue: "Intermittent DCS delay training failures remain under investigation. When a training failure occurs, the affected DIMM is isolated, and boot continues with fewer DIMMs." [Ref7] This matches the symptom.
- That issue text names no memory speed. The guide describes firmware 0.9.0. The kit does not say whether the same issue exists in firmware 0.7.2.
- Arm's changelog says: "firmware 0.7.2 defaults DIMM tuning to 8000 MT/s. Manually set the DIMM tuning to the recommended 7200 MT/s for this release." [Ref8]
- The user guide says: "DDR 8000 MT/s validation used EVT1 PCBs. Previous PCB versions might produce a higher error rate." [Ref7] CRB reports board version EVT0.
- The validated module lists of the user guide name `MTC20F2085S1RC80BH1 P8CH` (8000 and 7200 MT/s) and `MTC20F2085S1RC80BHY M8CC` (8000 MT/s only) [Ref7]. The CRB part `MTC20F2085S1RC80BH1 NCKK` is in neither list.
- The NCKK part appears in two Arm test reports of the kit, both at 8000 MT/s on firmware 0.9.0 [Ref11]. One of them names board version EVT1.

Evidence from the boot times (weak):

- The four direct reboots that gave 10 modules had gaps of 231, 237, 238 and 260 s.
- The two direct reboots that gave 12 modules had gaps of 203 and 224 s.
- Two more 12-module boots had gaps of 213 s (no shutdown logged) and 535 s (type of restart not known).
- Hypothesis: the firmware spends extra time on the failed training. The firmware console log would confirm or reject it.

**Less likely: one bad module or one bad slot contact.**

- All five 10-module boots miss two modules. The two boots that were checked miss one module per half, both at slot 5.
- Two independent bad contacts would sometimes give 11 modules. No boot shows 11.
- This does not exclude a shared hardware cause for slot 5, for example a signal route on this board revision that is close to its limit.

**What the Linux checks cannot decide:** a firmware defect and a board signal that is close to its limit give the same picture in Linux. The firmware training log would separate them. Linux cannot read that log on this machine.

## 9. Next steps

Done:

1. **"DIMM Frequency" set to 7200 MT/s.** Section 6.3 gives the result.

Open, in order of cost:

2. **Keep counting.** Record the module count after every future boot (`sudo dmesg | grep "DIMM sockets"`). One boot with 10 modules at 7200 MT/s would reject the speed as the only cause. A start after a power-off is the most useful next sample.
3. **Send the findings to Arm** with the questions of section 10. Arm asks for BMC and SCP logs with a support case [Ref10].
4. **Capture the firmware console during a boot** if a 10-module boot occurs again. Arm's validation report for BMC firmware 0.9.0 shows a serial console over SSH port 2200 [Ref9]. Insufficient data on whether the BMC firmware of CRB offers the same. A login to the CRB BMC would resolve it.
5. **Update the firmware to 0.9.0 (optional).**
   - It makes 7200 MT/s the default [Ref8]. It does not add a fix that the setting does not already give.
   - It contains two memory fixes: one for a self-test timeout with the Micron part `MTC20F2085S1RC80BHY M8CC`, and one for a training step [Ref7]. The first one names a different part than the CRB part.
   - The training issue of section 8 is still listed as open in 0.9.0 [Ref7].
6. **Hardware check (only if 10-module boots return).**
   - Swap the modules of slot 5 and slot 0 on one half.
   - If the missing module stays at slot 5, the module is not the cause.
   - If the missing slot moves to slot 0, the module is the cause.

## 10. Questions for Arm

1. Is the 10-of-12 module result on firmware 0.7.2 at 8000 MT/s the known "DCS delay training" issue?
2. Is the part `MTC20F2085S1RC80BH1 NCKK` validated on an EVT0 board, and at which speed?
3. What do the error records with type `bf32d4d5-b427-4025-8495-8a9e5d4030e4` and source names `DDS0` to `DDS7` mean?
4. Which log shows the training result per slot, and how do we read it?
5. Does our EVT0 board need a hardware change to run at 8000 MT/s?

## 11. Limits of this report

- The journal held only 12 boots at 8000 MT/s. Earlier boots are not known.
- The slot identity of the missing modules is known for two of the five 10-module boots.
- The gap values in section 3 are estimates from log timestamps.
- The read rates in section 6.2 come from one run per state with the original settings.
- Values marked "read live, output not saved" have no file as proof.
- Three independent review agents checked a draft of sections 1 to 8 against the saved files and the Arm documents. Their corrections are included. Section 6.3 and section 9 were written after that review.

## References

- [Ref1] Firmware version, date and board version: `~/workspace/titan/cache-perf/crb/results/uefisettings-20261117/identify.txt`. The kernel line `DMI: ... BIOS AGI-CPU-CRB-v0.7.2 09/08/2026` in `dimm-check-20261117/k0.txt` gives the same version and date.
- [Ref2] Module list with serial numbers, 12 modules: `~/workspace/titan/cache-perf/crb/results/dimm-check-20261117/dmi17-062957.txt`. Memory array summary: `dmi16-19.txt` in the same folder.
- [Ref3] Firmware settings list (1490 entries): `~/workspace/titan/cache-perf/crb/results/uefisettings-20261117/questions.json`. List after the revert: `fwtest-20261117/revert/questions.json`.
- [Ref4] Kernel logs per boot: `~/workspace/titan/cache-perf/crb/results/dimm-check-20261117/k-11.txt` to `k0.txt` (full log) and `h-11.txt` to `h0.txt` (module count line and error records).
- [Ref5] Module list with 10 modules: `~/workspace/titan/cache-perf/crb/results/dmidecode-t17-2026-10-30.txt`.
- [Ref6] Benchmark run folders under `~/workspace/titan/cache-perf/crb/results/`: `w120-R8-20261117T020549Z`, `w120-BASEd10-20261117T041738Z`; with changed TXREQ settings: `w120-X2d12-20261117T040922Z`, `w120-X1d10-20261117T034916Z`, `w120-X1d10b-20261117T040407Z`.
- [Ref7] `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf`: page 6 (default speed 7200 MT/s), page 9 (known issues and fixes), page 11 (training fix), pages 12 to 14 (validated modules, known limits).
- [Ref8] `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/gitlab-profile/CHANGELOG.md`, line 45 and lines 110 to 118.
- [Ref9] `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/Validation_Report/0_9_0_test_report.html`, lines 6519 to 6520.
- [Ref10] `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/docs/arm_agi_cpu_1ou_reference_server_quick_start_guide_112283_a0_01_en.pdf`, page 1.
- [Ref11] `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/tools/asct/reports/asct_run_output_a1_numa2_ddr_8000.txt`, lines 41 and 54; `tools/spec2017-toolkit/reports/spec2017-intrate-fw_0.9.0-ddr8000-numa2-a1-gcc15-golden-aarch64.pdf`, page 5.
- [Ref12] 7200 MT/s test: `~/workspace/titan/cache-perf/crb/results/dimm7200-20261117/` (`set.txt`, `try1.txt` to `try6.txt`, `gaps.txt`, `dmi17-7200.txt`, `dmi2.txt`) and the run folders `w120-w120-F72d12-20261117T200231Z`, `w120-w120-F72d12g-20261117T200504Z` in the same results folder.
