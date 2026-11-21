# Review of PR 5186 boot-window fix

**Short version.** Keep the opt-in AUX timing approach, but fix image reuse before treating the original review comment as resolved. The existing tests do not protect the new timing selection. The document also misidentifies the scope of the historical transaction count.

Reviewed `pr5186-fix.md` and its companion patch against commit `13418eb7c3ae5e828b4feea571497c7895c89f4b`. The source checkout was clean. No production files were changed.

**Terms used below**

- **AUX lanes:** the memory interfaces serving the application processor's system memory. A Goldcrest pair contains two lanes.
- **Datapath lanes:** the memory interfaces serving the compute datapath.
- **Timing selection:** `DATAPATH_TIMING`, the lane parameter controlling the added latency, bandwidth limit, and outstanding-transaction limits. `GC_PAIR_INDEX` identifies the pair.
- **Build manifest:** the `MANIFEST` file recording the compiled image's options.
- **cfclk:** one cycle of the 2 GHz emulation clock, or 0.5 ns.

**1. [P2] Make the image-reuse item part of the fix**

The proposal already identifies this problem in “Open items.” It directly defeats the promised default-boot behavior [R1].

```text
timed build -> shared image -> default run -> untimed boot budget
```

`run_build.sh` (the image builder) and `run_emu.sh` (the emulator launcher) select the same image directory with or without `HEMI_GC_AUX_TIMING`. Executing their tag-selection blocks confirmed this. The launcher selects the boot window from the firmware before reading the compiled defines. It has no AUX-timing check [R2].

After the documented timed-build command, a plain invocation can therefore reuse timed AUX memory with the default 1,000,000,000-cfclk release window. This restores the unmeasured configuration that prompted the original review. A timeout has not been demonstrated [R1, R2].

**Requested change:** inspect the actual build manifest before launching Linux. Reject a timed image when the caller has not supplied an explicit run window. A separate image variant is another option, but a manifest check is the smaller change. Cover fresh builds and reused images, including `--run-only`.

The launcher regression should establish these outcomes:

- Untimed image with the default window: accepted.
- Timed image with the default window: rejected before emulator execution.
- Timed image with an explicit window: accepted.

**2. [P2] Test the wrapper's timing selection in both build modes**

The proposed “No test” item asks only for an assertion that the default constant is 16. That would not catch a lane wired to the wrong parameter expression [R3].

The existing `aux` qualification instantiates `hemi_gc_lane_avip` (the individual lane implementation) with timing already disabled. It bypasses the outer wrapper that contains this patch. The port-order tests check signal connections, not timing selection [R4].

I changed only the default `GC_TIMED_PAIRS` value from 16 to 18 in an isolated patched copy. All 29 tests selected by `test_gc_*.py` still passed, with no skips. This deliberate error restores the original boot-window risk [R5].

**Requested change:** exercise both outer-wrapper lane instances with the define absent and present. Check pair indices `-1`, `0`, `15`, `16`, `17`, and `18`. The expected behavior is:

- Negative and out-of-range indices remain untimed in both builds.
- Datapath pairs remain timed in both builds.
- AUX pairs are untimed by default and timed only in the opt-in build.

Make the test fail when either lane receives the wrong timing parameter. Keep the existing lane-level qualification for latency and reset behavior.

**3. [P3] Correct the historical count's scope**

The estimate section says the recorded transaction count might belong to one hemisphere. The cited run report describes a combined end-of-run summary for both hemispheres. The historical launcher at commit `2aeb9d4f4` counts every read and write line in their shared log. It does not filter by hemisphere [R6].

The arithmetic is correct. The interpretation supporting the high cases is not. The values of 1,081 million cfclks (est.) and 1,310 million cfclks (est.) cannot be presented as consequences of an unresolved one-hemisphere count [R3, R6].

**Requested change:** identify the count as a full-chip logged total. Label assigning that entire total to one hemisphere as an artificial conservative assumption, or remove those cases. Halving the total is also an assumption about equal traffic. Insufficient data: per-hemisphere counts up to Linux init from the original run are needed to replace it.

This correction does not establish that timed boot fits. Keeping AUX timing opt-in remains justified by the absence of a measured timed boot.

**4. [P3] Separate restored behavior from a verified boot result**

The short version and behavior table say that the measured boot still applies. The same document discloses no emulator run and a change from operating-system snapshot v0.0.20 to v0.0.22 [R1, R3].

**Requested wording:** “A fresh default build restores the base branch's AUX timing selection. Boot completion with the current snapshot has not been verified.” Run the proposed default-image check before replacing that statement with a successful-boot claim.

The later measurement procedure also needs an executable way to obtain elapsed emulation time. The launcher only searches the console log for the init message. The inspected source does not establish an absolute cfclk timestamp for that message [R7].

Specify a timestamp extraction command and its time origin. Otherwise use the proposed failed/passed run-window brackets, after excluding unrelated failures. Record the successful upper bound and the exact firmware and operating-system images. Insufficient data: a console-log sample or documented timestamp format is needed to validate the current step 3.

**Verification performed**

- `git apply --check` passed against the stated commit. Patch statistics match: 4 files, 48 added lines, 22 deleted lines.
- On the patched temporary tree, `python3 -B -m unittest discover -s emu/hemi_tlm/tests -p 'test_gc_*.py' -v` passed all 29 tests, with no skips.
- `python3 -B -m unittest discover -s emu/hemi_tlm/tests -p 'test_real_gc_wrapper.py' -v` passed its 1 test, with no skips. The first attempt lacked a vendor-wrapper source omitted by the sparse checkout. The rerun used that tracked file from the same commit.
- `python3 -B -m unittest discover -s emu/hemi_tlm/tests -p 'test_host_ddr_timing.py' -v` passed all 25 host timing tests, with no skips. The first attempt lacked Git metadata in the temporary copy. That prerequisite was supplied before the rerun. The three patched-tree suites passed 55 tests in total.
- The deliberate wrong-default test passed all 29 tests. The temporary source was then restored [R5].
- Static inspection found both lane instances using the same limit. No defect was found in the proposed gate expression itself.
- No SystemVerilog compilation or emulator boot was run. The document's reported 44-test run was not reproduced as a complete suite.

**References**

- [R1] Proposal: [short version and behavior table](pr5186-fix.md), lines 7 and 55–58; image-reuse item, line 112; baseline age, line 115.
- [R2] At reviewed commit: [build-directory selection](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/scripts/run_build.sh#L386-L401); [boot-window selection](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/scripts/run_emu.sh#L605-L615); [run-directory selection](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/scripts/run_emu.sh#L736-L753); [compiled-image checks](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/scripts/run_emu.sh#L961-L1054). Local tag-check output: `/tmp/codex-pr5186-review/tag-check.json`.
- [R3] Proposal: [estimate section and validation items](pr5186-fix.md), lines 82–92, 104–115, and 120–127.
- [R4] [Lane qualification bypasses pair selection](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/tests/gc_avip_timing_tb.sv#L76-L95); [port-order assertions](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/tests/test_gc_port_order.py#L91-L110).
- [R5] Isolated test tree: `/tmp/pr5186-gate-review-b4avl_v0/repo`. Logs in its parent directory: `patched-test_gc.log`, `patched-test_real_gc_wrapper.log`, `patched-test_host_ddr_timing.log`, and `mutation-default18-test_gc.log`.
- [R6] [Historical run summary](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/fc_tlm/doc/NIGHT_TASK_PLAN.md#L222-L225); [historical aggregation code](https://github.com/Positron-AI-TSMC/asimov/blob/2aeb9d4f4a96f5ddabebe881972b556a7db04acf/emu/fc_tlm/scripts/run_emu.sh#L480-L487); [historical shared-log creation](https://github.com/Positron-AI-TSMC/asimov/blob/2aeb9d4f4a96f5ddabebe881972b556a7db04acf/emu/fc_tlm/sim/fc_sys_mem.cpp#L221-L224).
- [R7] [Console capture delegates to Cadence code](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/agents/hemi_uart_tty_xtor.sv#L5-L10); [launcher checks the init message](https://github.com/Positron-AI-TSMC/asimov/blob/13418eb7c3ae5e828b4feea571497c7895c89f4b/emu/hemi_tlm/scripts/run_emu.sh#L2015-L2024).

## session=20261111T0715Z-k7q2 round=1 role=worker status=START digest=- time=2026-11-11T07:08:01Z

Worker: Claude. Reviewer: codex.

- Initial file: `/home/jhan/workspace/titan/cache-perf/asimov/thuan-pr/pr5186-fix.md`
- Review file: `/home/jhan/workspace/titan/cache-perf/asimov/thuan-pr/codex-review-pr5186-fix.md`
- Companion patch: `/home/jhan/workspace/titan/cache-perf/asimov/thuan-pr/pr5186-fix.patch`

The review above this entry (findings 1 to 4) was written before this session started. This session treats it as the reviewer's first comments. The finding identifiers are F1 to F4, in the order of the review.

END ENTRY

## session=20261111T0715Z-k7q2 round=1 role=worker status=READY digest=b49eb95c7c8f6d911321d75c201c25744c70f9bd61b6b84bc5c201e60f008fae time=2026-11-11T07:08:01Z

**Short version.** I agree with all four findings. I checked each one against the code before acting on it. The patch and the description are both revised.

Submitted versions:

- `pr5186-fix.md`: SHA-256 `b49eb95c7c8f6d911321d75c201c25744c70f9bd61b6b84bc5c201e60f008fae`
- `pr5186-fix.patch`: SHA-256 `67bb1a59c19a55444c48bb90d0584fa71494dbdd70369f6e01028f42f0948082` (7 files, 289 insertions, 23 deletions, against commit 13418eb)

**F1 (image reuse): accepted, fixed in the patch.**

- Confirmed: the build directory is the same with and without the define. The launcher chose the Linux-boot window before it read the compiled defines.
- One more fact: the ssh re-start of the launcher always forwards `--run-cycles`. So the remote side could not tell whether the caller chose the value. A check on the existing state alone would never fire in a forwarded run.
- Change in `emu/hemi_tlm/scripts/run_emu.sh` (25 lines added):
  - A check on the MANIFEST `defines:` line of the image that will run. It sits right after the launcher reads that line, before elaboration and before the emulator starts. It covers a fresh build, a reused image and `--run-only`.
  - An earlier check on the `--define` list, so a direct `--build --define HEMI_GC_AUX_TIMING` call without a window stops before the build.
  - A new internal flag, `--run-cycles-default`, which the ssh re-start adds when the caller did not choose the window.
- Tests: 5 new tests in `emu/common/tests/test_hemi_notel.py`, class `HemiAuxTimingWindow`. They cover the three outcomes you listed, for no phase flag and for `--run-only`. They also cover the pre-build stop, two hops of the ssh re-start, the exact define match, and a run without a Linux boot.
- Checked: `cd emu/common/tests && python3 -B -m unittest test_hemi_notel` ran 24 tests, all pass. Four mutations each make a new test fail: MANIFEST check removed; pre-build check removed; forwarding without the new flag; Linux-boot condition removed.
- Limit: through `emu/common/scripts/run.sh`, the build phase runs with `--build-only`. The rejection then comes at the run phase, after the build. No emulator run starts.

**F2 (test the timing selection): accepted, test added.**

- Confirmed: with the default changed from 16 to 18, all 29 `test_gc_*.py` tests still passed.
- New file `emu/hemi_tlm/tests/test_gc_timing_selection.py`. It evaluates the gate of both lane instances for pair indices -1, 0, 15, 16, 17 and 18, with the define absent and present. The parser is strict. An unexpected expression form fails the test.
- Checked: `python3 -B -m unittest discover -s emu/hemi_tlm/tests -p 'test_gc_*.py'` ran 30 tests, all pass. Nine mutations each make the new test fail: default 16 to 18; define branch 18 to 16; one gate as literal `< 18`; one gate as literal `< 16`; `ifdef` to `ifndef`; `>= 0` dropped; `&&` to `||`; different expressions in the two instances; `GC_TIMED_PAIRS` renamed in one place.
- Limit: the test reads source text. No SystemVerilog tool is installed here (`command -v xrun verilator iverilog slang` prints nothing), so nothing was elaborated. One mutation is not caught: a `\`define HEMI_GC_AUX_TIMING` placed outside the wrapper module. The description lists this as an open item.

**F3 (scope of the historical count): accepted, description corrected.**

- Confirmed at commit 2aeb9d4f4: both hemispheres wrote to one `fc_sys_mem.log`, and the launcher counted all read and write lines without a hemisphere filter. The count also covers the whole 1.0G cfclk run, not only the part up to Linux init.
- The estimate table now calls the count a full-chip logged total. The half-total cases are labeled as an equal-traffic assumption. The whole-total cases are labeled artificial conservative upper limits. An "Insufficient data" line names the missing per-hemisphere counts up to Linux init.
- One case is new (case 3): half of the total, with serial writes added, gives 1092.1M cfclks (est.). So the equal-traffic assumption alone does not show that a timed boot fits.

**F4 (restored behavior against a verified boot): accepted, description corrected.**

- The short version and the behavior table now say that a fresh default build restores the base branch's AUX timing selection, and that boot completion with snapshot v0.0.22 has not been verified.
- Confirmed: nothing in the tree gives a time stamp for the init console line. The commit that introduced the 874M figure states "0.437 s (874M cfclks)" without a method.
- The measurement section is now a bracket procedure over `--run-cycles` values. It lists the checks that exclude unrelated failures, and it records the passing upper bound with the firmware and the snapshot. The time stamp question stays "Insufficient data" in the text.

**Not run.**

- No SystemVerilog compile or elaboration.
- No emulator run, no Linux boot.
- No real ssh re-start and no end-to-end launcher run. The launcher tests execute extracted blocks of the script.
- The bracket procedure was not executed.
- The full suites do not pass in my copy of the tree, with or without the patch: `emu/common/tests` 15 failures and 47 errors of 205; `emu/hemi_tlm/tests` 20 failures and 14 errors of 199. The failing sets are the same with and without the patch. The copy holds only `emu/hemi_tlm` and `emu/common`. I did not examine the cause.
- Plain `git apply --check` fails in the local sparse clone, since `emu/common/tests/test_hemi_notel.py` is not checked out there. It passes with `--cached` and in a fresh copy of the PR head files.

END ENTRY


## session=20261111T0715Z-k7q2 round=1 role=reviewer status=COMMENTS digest=- time=2026-11-11T18:34:32Z

**Short version.** F1 and F2 are resolved. F3's count scope and F4's boot-result wording are corrected. Two small documentation corrections remain; neither is a new implementation defect.

Reviewed the submitted description SHA-256 `b49eb95c7c8f6d911321d75c201c25744c70f9bd61b6b84bc5c201e60f008fae` and patch SHA-256 `67bb1a59c19a55444c48bb90d0584fa71494dbdd70369f6e01028f42f0948082`.

**F1 — resolved.** The manifest check rejects timed Linux boots with an implicit window. The new forwarding flag preserves that distinction across the launcher's ssh restart. The common entry script preserves explicit cycle arguments through its build/run split. Its build-only exception is accurately documented.

**F2 — resolved.** The new test evaluates both production lane expressions against independently stated expectations. It detects the original wrong default and a wrong expression in only one lane. The disclosed source-text limitation does not establish a defect in this patch.

**F3 — one evidence claim remains to correct [P3].** Location: `pr5186-fix.md:125`, “The original `fc_sys_mem.log` would give them.” Here, “them” means per-hemisphere counts up to Linux init. The hemisphere tags recover the whole-run split. The historical transaction records contain sequence numbers and transaction fields, but no timestamp or init marker. They do not identify the init cutoff by themselves [S1].

Requested correction: “The original log would recover per-hemisphere whole-run counts. Counts up to init also need evidence correlating transactions with the init event.” Keep the existing Insufficient data statement.

**F4 — boot-result wording resolved; initialize the bracket explicitly [P3].** Location: `pr5186-fix.md`, measurement steps 3–6. The first timed run supplies only one bound. Step 6 requires both a valid INCOMPLETE lower bound and a BOOTED upper bound. The untimed run from step 2 cannot supply the other bound.

Requested correction: before the midpoint search, obtain both bounds on the timed image with the same firmware. If the first timed run is INCOMPLETE, increase the window until it boots, subject to the existing failure checks. If it boots, reduce the window until a valid INCOMPLETE run supplies the lower bound. Then use the midpoint procedure.

**Independent verification**

- Patch application check and shell syntax check passed on a fresh temporary copy of commit `13418eb7c3ae5e828b4feea571497c7895c89f4b`.
- `python3 -B -m unittest test_hemi_notel -v`: 24 tests passed, no skips.
- `python3 -B -m unittest discover -s emu/hemi_tlm/tests -p 'test_gc_*.py' -v`: 30 tests passed, no skips.
- Three deliberate errors were detected: removing the forwarded default-window marker, changing the default pair limit to 18, and changing only lane 0's gate to literal `< 18`. All temporary changes were restored.
- Recomputed all five estimate rows and their percentages. They match the revised table.
- No SystemVerilog compilation, emulator boot, real ssh restart, or full-suite run was performed in this review. The worker's disclosed full-suite failures remain outside these targeted results.

**Evidence**

- [S1] Historical logger: [sequence number and write record](https://github.com/Positron-AI-TSMC/asimov/blob/2aeb9d4f4a96f5ddabebe881972b556a7db04acf/emu/fc_tlm/sim/fc_sys_mem.cpp#L123-L143), [read record](https://github.com/Positron-AI-TSMC/asimov/blob/2aeb9d4f4a96f5ddabebe881972b556a7db04acf/emu/fc_tlm/sim/fc_sys_mem.cpp#L154-L164).
- Launcher logs: `/tmp/codex-pr5186-r2-kr7xocre/launcher-tests.log` and `/tmp/codex-pr5186-r2-kr7xocre/mutation-forwarding.log`.
- Gate logs: `/tmp/pr5186-round2-gate-3j46q037/patched.log`, `mutation-default18.log`, and `mutation-lane0-literal18.log` in the same directory.

Awaiting the next READY entry for these documentation corrections.

END ENTRY

## session=20261111T0715Z-k7q2 round=2 role=worker status=READY digest=4056334c12903f83d59b28e3a6677d9501aed14e189e667be6b0eaad3ade2a7d time=2026-11-11T18:35:41Z

**Short version.** I agree with both remaining corrections. Both are made in `pr5186-fix.md`. The patch is unchanged.

Submitted versions:

- `pr5186-fix.md`: SHA-256 `4056334c12903f83d59b28e3a6677d9501aed14e189e667be6b0eaad3ade2a7d`
- `pr5186-fix.patch`: SHA-256 `67bb1a59c19a55444c48bb90d0584fa71494dbdd70369f6e01028f42f0948082` (unchanged from round 1)

**F3 (evidence claim on the original log): accepted, corrected.**

- Confirmed in the historical logger at commit 2aeb9d4f4: a log line carries the hemisphere tag, a sequence number and the transaction fields. It carries no time stamp and no init marker.
- The "Insufficient data" item in "Why not raise the run window instead" now has three sub-points. The original log would recover the per-hemisphere counts for the whole run. Counts up to init also need evidence that ties transactions to the init event. Without both, a new run on the current firmware is needed.
- The text of [Ref10] now names the line format, not only the hemisphere tag.

**F4 (initialize the bracket): accepted, corrected.**

- The measurement procedure has a new step 6, before the midpoint search. It requires both bounds on the timed image, with the same firmware and snapshot. It states that the untimed run of step 2 gives no bound for the timed image.
  - First timed run INCOMPLETE and valid by step 5: raise the window until a run is BOOTED.
  - First timed run BOOTED: lower the window until a run is INCOMPLETE and valid by step 5.
- The midpoint search is now step 7. The later steps are renumbered 8 to 11.
- The example step sizes in step 6 (400M cfclks up; 1.0G then 874M cfclks down) are choices of the document, marked "for example".

**Other change.** The date line now says "Revision 3 of this description, after the second review."

**Checks.**

- Documentation only. No code or patch change, so no test was rerun.
- The procedure of the measurement section was not executed.
- Everything in the round 1 "Not run" list still holds.

END ENTRY


## session=20261111T0715Z-k7q2 round=2 role=reviewer status=REVIEW_COMPLETE digest=4056334c12903f83d59b28e3a6677d9501aed14e189e667be6b0eaad3ade2a7d time=2026-11-12T03:53:18Z

No further comments.

- **F3 resolved.** The description now separates whole-run counts by hemisphere from counts up to Linux init. It explicitly requires additional evidence tying transactions to the init event (`pr5186-fix.md:125–128`).
- **F4 resolved.** Measurement step 6 obtains both bounds on the timed image with the same firmware and snapshot. It excludes the untimed run as a bound. Step 7 starts the midpoint search only after both bounds exist (`pr5186-fix.md:222–226`).
- **F1 and F2 remain resolved.** The patch is unchanged from the version checked in round 1: SHA-256 `67bb1a59c19a55444c48bb90d0584fa71494dbdd70369f6e01028f42f0948082`.

The description digest matches the latest READY entry. No tests were rerun for these documentation-only changes. The prior 54 targeted tests passed with no skips. The previously disclosed full-suite failures remain uninvestigated. SystemVerilog compilation and emulator boot validation remain unperformed.

Review complete for `/home/jhan/workspace/titan/cache-perf/asimov/thuan-pr/pr5186-fix.md`. The shared record is `/home/jhan/workspace/titan/cache-perf/asimov/thuan-pr/codex-review-pr5186-fix.md`.

END ENTRY
