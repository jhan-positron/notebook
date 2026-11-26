# `schedule_zs.py` explained, line by line

- Source file: `bwx11-2026-11-15/schedule_zs.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 45 lines, 2580 bytes).
- sha256 of the source when this page was built: `6d1b2f9fb6eafd1220d4a052885b6baec5f7cf2cb41783b401cbc941fb5e767c`.

## Short version: purpose

`schedule_zs.py` writes the schedule and the plan files of one more step of round 4, the step `ZS`, into the schedule folder that `schedule11.py` made. Each of its 52 processes per session runs `asmread` or `oldread` at one of 13 buffer sizes for 6 s, with the counters read for each window. The order of the processes is random, from a fixed seed per session.

## Words used here

- **Round 4**: the fourth set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Z`.
- **Step `ZS`**: a step of round 4 that was added after the other steps. It measures counters at 13 buffer sizes from 1 MiB to 32 MiB.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **Process**: one start of a benchmark binary.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `ZS.tsv`. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Trial, window**: a trial is one timed sequence inside a process. A window is one timed period of the kernel inside a trial.
- **Cell**: one kernel at one buffer size.
- **Nominal kernel work**: the sum of the planned durations of all windows. The real run time of a process is longer.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Run script**: the script `run_bwx11.sh`. It starts the processes of a schedule on CRB.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Set the 13 sizes, the 2 kernels, the 6 counter events and the base number of the seeds (lines 7 to 11).
2. For each session, start a random number generator with the seed `BASE` plus the session number (lines 14 to 16).
3. For each CPU of the session, shuffle the 26 cells and write one plan file and one schedule row per cell (lines 21 to 33).
4. Write the files `ZS.tsv`, `ZS.bin` and `ZS.seed` of the session (lines 34 to 41).
5. Print the number of processes and the nominal kernel work of the session (line 42).
6. Stop with an error unless both sessions together have 104 processes (line 44).

## Behavior a reader must know

- The order of the processes: first all 26 cells on the first CPU of the session, then all 26 cells on the second CPU. Inside a CPU the order is one random shuffle (line 23). Nothing is balanced beyond this: each cell runs once per CPU and session.
- The seeds are fixed: 2026111505 for session 1 and 2026111506 for session 2 (line 15). The program has no option. So every run writes the same files.
- The program writes into `sched11/s1` and `sched11/s2` beside the other schedules. It removes no file. It replaces files of the same names.
- The program does not change `MANIFEST.txt`. The seed of the step is recorded in the file `ZS.seed` (lines 40 to 41) and in the second line of every plan file (line 29).
- Each process is one trial of 20 windows of 300 ms with the counter mode `read`: 6 s of nominal kernel work (line 31). A session has 52 processes and 312 s of nominal kernel work.
- The sizes in the plan and in the tag are plain numbers of bytes, not texts such as `8M` (line 31, line 33).
- `main` runs whenever the file is loaded, also as a module (line 45).
- The test file `test_schedule11.py` does not test this program.

## Source and explanation, line by line

- Text shown: the file `bwx11-2026-11-15/schedule_zs.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (45 lines, 2580 bytes, sha256 `6d1b2f9fb6eafd1220d4a052885b6baec5f7cf2cb41783b401cbc941fb5e767c`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""schedule_zs.py - step ZS of round 4 ("size dose with counters"), added by hand after schedule11.py.` | Starts the description text of the file. The program writes the schedule of step `ZS` of round 4. By the text the step was added separately, after the generator `schedule11.py`. The words "size dose with counters" mean this: the buffer size is the dose, and the counters measure what changes with it. |
| 3 | `One trial per process: 20 windows of 300 ms with the counters read (binary bwx11).` | Text of the description: each process has one trial of 20 windows of 300 ms, and the runner reads the counters for each window. The binary is `bwx11`. |
| 4 | `Kernels asmread and oldread at 13 sizes from 1 MiB to 32 MiB, 1 process per kernel, size and CPU = 52 per session.` | Text of the description: the kernels `asmread` and `oldread` run at 13 sizes from 1 MiB to 32 MiB. There is 1 process per kernel, size and CPU. That gives 2 times 13 times 2 = 52 processes per session. |
| 5 | `Writes sched11/s<session>/ZS.tsv, ZS.bin and ZS/NNNN.plan beside this script. Deterministic (seed in ZS.seed)."""` | Text of the description: the program writes the schedule file `ZS.tsv`, the file `ZS.bin` and the plan files `ZS/NNNN.plan` into `sched11/s<session>/` in the folder of this script. The same run always gives the same files. The seed is saved in the file `ZS.seed`. The line also ends the description text. |
| 6 | `import os, random` | Loads the Python modules `os` (paths and folders) and `random` (the random number generator). |
| 7 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the full path of the folder that holds this file. |
| 8 | `SIZES = [1048576, 1572864, 2097152, 2621440, 3145728, 4194304, 5242880, 6291456, 8388608, 12582912, 16777216, 25165824, 33554432]` | `SIZES`: the 13 buffer sizes in bytes: 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 12, 16, 24 and 32 MiB. |
| 9 | `KERNELS = ["asmread", "oldread"]` | `KERNELS`: the two kernels of the step: the hand-written load-only loop `asmread` and the old read kernel `oldread`. |
| 10 | `EVENTS = "cpu_cycles=0x11,l1d_cache_lmiss_rd=0x39,l2d_cache_refill=0x17,l2d_cache_wb=0x18,bus_access=0x19,l2d_cache_lmiss_rd=0x4009"` | `EVENTS`: the 6 counter events, each as a name and an event code: core cycles, long misses of loads in the first-level cache, refills of the L2 cache, write-backs from the L2 cache, bus accesses, and long misses of loads in the L2 cache. The text is equal to the event list of step `ZC` in `schedule11.py`. |
| 11 | `BASE = 2026111504` | `BASE`: 2026111504, the number from which the two seeds are made. |
| 12 | `def main():` | Starts the function `main`. |
| 13 | `    total = 0` | `total`: the number of processes written for both sessions, 0 at first. |
| 14 | `    for session, cpus in ((1, (2, 41)), (2, (41, 2))):` | Starts the loop over the two sessions. Session 1 uses the CPUs 2 and then 41. Session 2 uses 41 and then 2. |
| 15 | `        seed = BASE + session` | `seed`: `BASE` plus the session number, that is 2026111505 for session 1 and 2026111506 for session 2. |
| 16 | `        rng = random.Random(seed)` | `rng`: a random number generator of its own for this session, started with that seed. The shuffles for both CPUs of the session use it, one after the other. |
| 17 | `        sdir = os.path.join(HERE, "sched11", "s%d" % session)` | `sdir`: the folder of the session, `sched11/s1` or `sched11/s2` in the folder of this file. The schedules of `schedule11.py` lie in the same folder. |
| 18 | `        pdir = os.path.join(sdir, "ZS")` | `pdir`: the folder `ZS` in it, for the plan files. |
| 19 | `        os.makedirs(pdir, exist_ok=True)` | Creates the folder `ZS` when it does not exist. An existing folder is kept, and its files are not removed. |
| 20 | `        rows = []` | `rows`: the rows of the schedule of this session, empty at first. |
| 21 | `        for cpu in cpus:` | Starts the loop over the two CPUs, in the order of the session. All processes of the first CPU come before those of the second CPU. |
| 22 | `            cells = [(k, s) for k in KERNELS for s in SIZES]` | `cells`: the 26 cells of one CPU: each of the 2 kernels at each of the 13 sizes. |
| 23 | `            rng.shuffle(cells)` | Shuffles the cells with `rng`. This is the only random choice: each CPU of each session gets its own random order of the 26 cells. |
| 24 | `            for k, s in cells:` | Starts the loop over the cells in the shuffled order. |
| 25 | `                idx = len(rows)` | `idx`: the number of the process in the schedule. It is the number of rows written up to now, so it counts from 0 through both CPUs. |
| 26 | `                plan = "%04d.plan" % idx` | `plan`: the name of the plan file: the `idx` with 4 digits and the ending `.plan`. |
| 27 | `                with open(os.path.join(pdir, plan), "w") as f:` | Opens the plan file for writing. A file with the same name is replaced. |
| 28 | `                    f.write("# bwx8-plan v1\n")` | Writes the first line of the plan: the fixed text `# bwx8-plan v1`, the name and the version of the plan format. |
| 29 | `                    f.write("# step=ZS session=%d cpu=%d bytes=%d proc=%d kernel=%s size=%d seed=%d test=0\n" % (session, cpu, s, idx, k, s, seed))` | Writes the second line: the header pairs. They give the step `ZS`, the session, the CPU, the buffer size in bytes, the number of the process, the kernel, the size once more, the seed, and `test=0` (a real plan, no test divisor). |
| 30 | `                    f.write("# trial cond rep prev pfx pred tgt nwin win_ms count bins\n")` | Writes the third line: the names of the 11 columns of a trial line. |
| 31 | `                    f.write("0 K=%s\|S=%d\|count=read 1 - - - %s@%d 20 300 read 0\n" % (k, s, k, s))` | Writes the one trial line. The fields are: trial 0. The condition label, for example `K=asmread\|S=8388608\|count=read`. Repeat 1. Three times `-`: no previous activity, no prefix and no predecessor. The target as kernel, `@` and size in bytes. 20 windows of 300 ms. The counter mode `read`. Bins 0. So the nominal kernel work of one process is 6000 ms. |
| 32 | `                args = "--trial --cpus %d --bytes %d --plan sched11/s%d/ZS/%s --pmu-type 11 --events %s" % (cpu, s, session, plan, EVENTS)` | `args`: the options of the process for the runner: `--trial` (the mode that runs a plan), `--cpus` with the one worker CPU, `--bytes` with the buffer size, `--plan` with the path of the plan relative to the folder of the run script, `--pmu-type 11` (the type number of the counter device of the cores on CRB) and `--events` with the 6 events. |
| 33 | `                rows.append((idx, "%s-%d-cpu%d" % (k, s, cpu), cpu, s, plan, args))` | Adds the row of the process: its `idx`, its tag (the kernel, the size in bytes and the CPU, for example `asmread-8388608-cpu2`), its CPU, its size, the name of its plan file and its options. |
| 34 | `        with open(os.path.join(sdir, "ZS.tsv"), "w") as f:` | After both CPUs: opens the schedule file `ZS.tsv` of the session for writing. |
| 35 | `            f.write("idx\ttag\tcpu\tbytes\tplan\targs\n")` | Writes the first row: the six column names `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`, with tabs between them. |
| 36 | `            for r in rows:` | Starts the loop over the rows. |
| 37 | `                f.write("\t".join(str(x) for x in r) + "\n")` | Writes one row: its six values as text, with tabs between them, and a newline. |
| 38 | `        with open(os.path.join(sdir, "ZS.bin"), "w") as f:` | Opens the file `ZS.bin` for writing. |
| 39 | `            f.write("bwx11\n")` | Writes the word `bwx11` and a newline. The run script reads this word to find the binary of the step. |
| 40 | `        with open(os.path.join(sdir, "ZS.seed"), "w") as f:` | Opens the file `ZS.seed` for writing. |
| 41 | `            f.write("%d\n" % seed)` | Writes the seed of the session and a newline. The second line of every plan file holds the seed too (line 29). The program does not change `MANIFEST.txt`. |
| 42 | `        print("ZS session %d: %d processes, nominal kernel work %.1f s" % (session, len(rows), len(rows) * 6.0))` | Prints one line per session: the number of processes and the nominal kernel work in seconds. The work is the number of processes times 6.0 s, the planned time of one trial. |
| 43 | `        total += len(rows)` | Adds the processes of the session to `total`. |
| 44 | `    assert total == 104` | After both sessions: the program stops with an error unless `total` is 104, that is 52 processes per session. The files are written before this test. |
| 45 | `main()` | Calls `main`. The call has no test for the way in which the file was started. So the program also runs when another Python file loads this file as a module. |
