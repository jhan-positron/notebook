## Short version: purpose

`decide.py` holds the decision rules of section B.10 of the handoff note as Python functions. Each rule says when a difference between two kernels, or a change of such a difference, counts as resolved against the difference between two copies of one loop. Started as a program, the file only tests these rules on invented values and reads no measurement.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan. Its section B.10 gives the decision rules in words.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Step**: one named batch of processes of the plan. The steps B1, B2, B3 and B6 run one thread. The steps B7 and B10 run 120 threads.
- **Session of the plan**: one run of all steps of Parts B and C. The plan asks for 2 sessions some hours apart. This is not the session of the later rerun.
- **A/A pair**: one loop that stands in the binary twice, under two names, for example `asmread` and `asmread2`.
- **A/A difference**: the difference between the rates of the two copies of an A/A pair. It shows how much two equal loops differ.
- **A/A spread**: the largest absolute A/A difference of a group of processes. It is never negative.
- **Reference interval**: an interval of `asmread` that is timed directly before or after a compared interval, to show the level at that time.
- **Level: low, high, changing**: the label of a rate of `asmread` with one thread and a buffer of 8 MiB. Low is below 69 GB/s, high is above 70.5 GB/s, and changing is every rate from 69 to 70.5 GB/s. The two limits are provisional.
- **Stable process**: a process whose reference intervals all have the label low, or all have the label high.
- **Pair value**: the rate of one kernel minus the rate of the other in two neighbouring intervals, in GB/s.
- **Process value**: one number per process. `d` is the median of the pair values of the kernel comparison. `e` is the median of the pair values of the A/A comparison.
- **Decision group**: the processes of one session, one buffer size, one CPU and one label.
- **Resolved**: the word for a difference that is larger than the A/A spread and has one sign in all processes.
- **Not resolved**: the word for a difference that lies inside the A/A spread, or whose sign changes between the processes.
- **Not observed**: the word for a case with too few processes for a decision.
- **Setting**: one combination of the timing options of a step with 120 threads: the stop method, the interval length and the start method.
- **`D`, `E`**: the two process values of a step with 120 threads. `D` is the difference between two kernels. `E` is the A/A difference of the same process.
- **Control**: in step B10, the largest absolute A/A difference of one setting: one for the total rate and one for the rate of each mesh.
- **H11**: a hypothesis of the plan: in some intervals the threads of one mesh run faster, and this makes the write totals differ.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.

## Main flow

1. Set the two limits of the level and define `level`, which labels one rate ({L11-14}).
2. Define the rules for the steps with one thread ({L16-78}). `process_value` gives one label and the values `d` and `e` per process. `resolved` decides one decision group. `decide_one_thread` applies it per CPU and joins the CPUs. `decide_b6_state` compares the low and the high processes of one CPU.
3. Define the rules for the steps with 120 threads ({L80-132}). `decide_setting` decides one setting, and `decide_change` decides a change between two settings. `controls_from_aa` computes the controls of step B10, and `decide_h11` applies them to hypothesis H11.
4. Started as a program, the file runs `_tests`: seven groups of tests on invented values ({L134-199}).

## Behavior a reader must know

- The file reads no result file and writes no file. Started as a program it prints one line when all tests pass. A failed test ends the program with an error.
- The rules are used by the analysis of Parts B and C: the script `analyze_bwx.py` imports this file and calls its functions.
- Every rule compares with an A/A spread or a control. A difference counts only when it is strictly larger. An equal value is not resolved.
- A group with too few processes gives `not observed`: fewer than 3 in `decide_one_thread`, fewer than 2 of one label in `decide_b6_state`, fewer than 4 in `decide_setting` and `decide_change`, fewer than 2 counted processes in `decide_h11`. A caller can give another count.
- Values of different CPUs are never pooled in the rules for one thread. `decide_one_thread` needs at least 2 CPUs that are resolved with the same sign.
- A process gives one value, however many intervals it has. The value is a median of its pair values.
- At 8 MiB a process gives a value only when all its reference intervals are low or all are high. At the other sizes no level is tested.
- `decide_h11` does not return which mesh rose. It returns only the word.
- All rates in the tests are invented. No test result is a measurement.
