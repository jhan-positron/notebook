# `test_make_report.py` explained

- Source file: `test_make_report.py` in this folder (Python script, 83 lines, 4760 bytes).
- sha256 of the source when this page was built: `df78a1818a3b9d145031b2893d6e025f6946e19791c9b302602b7bcb6ec85fe1`.
- Role in the whole-chip test: Test script: checks that make_report.py stops on damaged input data.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The script runs copies of the report generator make_report.py on damaged copies of its input file facts.json. It passes when the control without damage ends with exit status 0 and each of the 10 damaged cases ends with another exit status.

<details>
<summary>Words used here</summary>

- **make_report.py, generator**: the script that writes the report page of the rerun, `whole-chip-rerun-7200.html`. Its input is facts.json.
- **facts.json**: the data file of the facts sheet FACTS.md. The script build_facts.py writes both from the raw result files. Its list `intervals` holds one record per timed interval.
- **Record**: one entry of the list `intervals` of facts.json: one timed interval with its data set, kernel, binary, rate (`GBps`), process key (`proc_key`), load at launch (`load1_at_launch`), boot id (`boot`) and more fields [Ref3].
- **Data set**: the field `dataset` of a record. It names the group of runs that the record belongs to. `rerun-A`, `rerun-L`, `rerun-C` and `control-I` are the four parts of the rerun. All other names are earlier runs.
- **B7a, C3b, B5a-rev**: data sets of earlier runs at 8000 MT/s with the older runner bwx. B5a-rev ran the kernels in reverse order.
- **X1d10**: data set of an earlier bwx12 run at 8000 MT/s in a boot with 10 memory modules.
- **X2d12**: data set of an earlier bwx12 run at 8000 MT/s with 12 memory modules. Its boot is not the boot of the other 12-module runs at 8000 MT/s.
- **Rerun**: the read test of 2026-11-17 with 120 threads, run after the memory speed was lowered to 7200 MT/s (million transfers per second). Its parts are part A, part L, part C and control I.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **go.sh**: the driver script of the rerun: three sessions of parts A, L, C and a fourth part C process.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **GB, GB/s**: 1 GB is 1e9 bytes. Every rate is in GB/s.
- **Load at launch**: the 1-minute load average of Linux, read directly before a process starts.
- **threads120.csv**: the result file of a part A folder. It holds the output of the benchmark processes of that folder, with one csv line per timed interval. The generator calls such a line an interval row.
- **T rows**: the rows of a bwx csv file that hold one thread of one interval each. The generator sums their rates to get the rate of an interval.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Control**: in this test: the case that runs the generator on an unchanged copy of the facts.
- **STOP line, FAIL line**: lines that make_report.py prints. `STOP` comes with the reason when the script ends early. `FAIL` marks a failed entry of its self-check list.
- **Standard output, error output**: the two text streams of a process. Normal text goes to the first one, error messages to the second one.

</details>

## Main flow

1. Create a temporary folder under `test-tmp`. Read the text of make_report.py and the content of facts.json (lines 15-19).
2. Define `run`. It writes a damaged copy of the facts and a copy of the generator that reads this copy and writes its page into the temporary folder. It runs the copy, prints up to 4 of its `STOP`, `FAIL`, `NOT WRITTEN` and `wrote` lines, and returns its exit status (lines 21-35).
3. Define 9 damage functions. Each changes one detail of the facts: a record removed, a rate changed, a load value changed, or a boot id changed (lines 37-65).
4. Run 11 cases: the control without damage, the 9 damage functions, and one case that changes the text of the generator (a reference path that does not exist) (lines 66-77).
5. Print `PASS` or `FAIL` per case from the exit status. Delete the temporary folder. End with exit status 0 when every case behaved as required (lines 78-83).

## Behavior a reader must know

- The test works on copies. The damaged facts, the copies of the generator and their output pages go to a new folder under `test-tmp`, and the script deletes that folder at the end. The `assert` in line 27 stops the test when the output path of a copy was not replaced.
- The verdict uses the exit status only (lines 79 and 81). The control must give 0. Each damaged case must give a value other than 0. The usage text also requires that no page is written. The script prints that fact per case (line 32), and no code tests it.
- The test does not check which check of the generator found the damage. It prints up to 4 lines of the generator per case, so that a reader can see the reason.
- The copy of the generator still reads FACTS.md and the raw result files from their real folders. make_report.py holds these paths as fixed text [Ref1]. So the test needs these files.
- Result of a saved run: the control ended with exit status 0 and wrote its page. Each of the 10 damaged cases ended with exit status 1 and a `STOP` line, and wrote no page [Ref2]. A run of a copy of this script in a scratch folder on 2026-11-21 gave the same exit statuses and the same `STOP` lines.
- Link to the rates of the report: 4 cases change one rate of facts.json, by 5 GB/s in part A and by 0.5 GB/s for the runners bwx12 and bwx. In the saved run the generator found each change when it compared the record with the raw csv rows that the record names [Ref2].

## Call sequence in the whole-chip test

- `script body` (line 15): setup, 11 calls of `run`, verdict from the exit statuses
  - `run` (line 21): one case: damaged facts, patched generator copy, separate process
    - `mutate` (line 21): parameter: one of 9 damage functions (lines 37 to 65), or no change
    - `patch` (line 21): parameter: the last case (line 77) changes one path in the copy
    - `make_report.py:script body`: the patched copy runs as a separate Python process

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `run` | 21-35 | Runs one case: damaged facts copy, patched generator copy, separate process. Prints its `STOP`, `FAIL`, `NOT WRITTEN` and `wrote` lines. Returns the exit status. | `mutate`, `patch` | - |
| `drop_one` | 37-39 | Deletes the first part L record of `oldread` and lowers the stored record count by 1. | - | - |
| `change_a` | 40-42 | Raises the rate of one part A record of the new read kernel by 5.0 GB/s. | - | - |
| `change_bwx` | 43-45 | Raises the rate of the first part C record of kernel `read` by 0.5 GB/s. | - | - |
| `change_bwx_old` | 46-48 | Raises the rate of one `B7a` record (runner bwx, kernel `read`, position 6) by 0.5 GB/s. | - | - |
| `drop_bwx_old` | 49-51 | Deletes the first `asmread` record of `B5a-rev` and lowers the stored record count by 1. | - | - |
| `change_10mod` | 52-54 | Raises the rate of one `X1d10` record (10 memory modules, `asmread`, position 1) by 0.5 GB/s. | - | - |
| `drop_x2d12` | 55-57 | Deletes the first `oldread` record at position 0 of `X2d12` and lowers the stored record count by 1. | - | - |
| `bwx_load` | 58-62 | Raises the load at launch by 1.0 in every record of one `C3b` process. | - | - |
| `other_boot` | 63-65 | Gives the first `asmread` record of control I a boot id of zeros. | - | - |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/test_make_report.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (83 lines, 4760 bytes, sha256 `df78a1818a3b9d145031b2893d6e025f6946e19791c9b302602b7bcb6ec85fe1`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/test_make_report.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Usage text and imports (lines 1 to 14)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_make_report.py - fail-loud tests of make_report.py.` | Starts the usage text (a Python docstring): the file holds fail-loud tests of `make_report.py`. Fail-loud means here: the generator must stop with an error when its input is wrong, and it must not write a page. `make_report.py` is the generator of the report page of the rerun. |
| 4 | `Each case runs a copy of the generator on a damaged copy of facts.json.` | Usage text: each case runs a copy of the generator on a damaged copy of `facts.json`. `facts.json` is the input of the generator, the file with one record per timed interval. |
| 5 | `The generator must stop, or it must print a FAIL line and exit with status 1, and it must not write a page.` | Usage text: what every damaged case must show. The generator must stop, or it must print a `FAIL` line and end with exit status 1. It must not write a page. The code tests the exit status only (line 79). It prints whether a page was written (line 32), and it does not test that. |
| 6 | `The copies and their output go to a temporary folder under test-tmp of this folder. The real report and facts.json are not touched.` | Usage text: the copies and their output go to a temporary folder below `test-tmp` of this folder. The real report page and the real `facts.json` are not changed. |
| 7 | `Run: python3 test_make_report.py   (exit status 0 = all cases behave as required)"""` | Usage text: how to run the test. Exit status 0 means that all cases behave as required. The line also ends the usage text. |
| 8 | `import copy` | Loads the module `copy`. Line 22 uses it to copy the facts in memory. |
| 9 | `import json` | Loads the module `json`, which reads and writes JSON files. |
| 10 | `import os` | Loads the module `os`, which works on file paths and folders. |
| 11 | `import shutil` | Loads the module `shutil`. Line 82 uses it to delete the temporary folder. |
| 12 | `import subprocess` | Loads the module `subprocess`, which starts another program (line 30). |
| 13 | `import sys` | Loads the module `sys`: the path of the running Python program and the exit status of the script. |
| 14 | `import tempfile` | Loads the module `tempfile`, which creates a temporary folder (line 17). All seven modules belong to the Python standard library. |

### Setup: temporary folder and the two inputs (lines 15 to 20)

| Line | Source | Explanation |
|---:|---|---|
| 15 | `S = os.path.dirname(os.path.abspath(__file__))` | `S` is the folder of this script. |
| 16 | `os.makedirs(S + "/test-tmp", exist_ok=True)          # the copies stay inside the scratch folder of this rerun` | Creates the folder `test-tmp` in `S` when it is missing. Comment: the copies stay inside the scratch folder of this rerun. The code creates `test-tmp` beside this script. So the comment holds when the script lies in that scratch folder. |
| 17 | `T = tempfile.mkdtemp(prefix="test_make_report_", dir=S + "/test-tmp")` | `T` is a new temporary folder inside `S/test-tmp`. Its name starts with `test_make_report_`. Every file that the test writes goes there. |
| 18 | `src = open(S + "/make_report.py").read()` | `src` is the text of `make_report.py`, read from the folder `S`. |
| 19 | `facts = json.load(open(S + "/facts.json"))` | `facts` is the parsed content of `facts.json`, read from the folder `S`. |

### Function `run`: one test case (lines 21 to 36)

| Line | Source | Explanation |
|---:|---|---|
| 21 | `def run(name, mutate, patch=lambda s: s):` | Starts the function `run`. It runs one test case with the name `name`. `mutate` is a function that damages the facts. `patch` is a function that may change the text of the generator. Its default returns the text unchanged. |
| 22 | `    d = copy.deepcopy(facts)` | Copies the facts in memory. So the damage of one case does not reach the next case. |
| 23 | `    mutate(d)` | Damages the copy with `mutate`. |
| 24 | `    json.dump(d, open(f"{T}/facts-{name}.json", "w"))` | Writes the damaged copy to `facts-<name>.json` in the temporary folder. |
| 25 | `    code = src.replace('S + "/facts.json"', repr(f"{T}/facts-{name}.json"))` | In the text of the generator, replaces `S + "/facts.json"` by the path of the damaged copy, written as a Python text literal. This text occurs 2 times: where the generator reads the file, and in its reference list [Ref1]. |
| 26 | `    code = code.replace('OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"', f'OUT = "{T}/out-{name}.html"')` | Replaces the line that sets `OUT`, the path of the report page, by a path in the temporary folder (`out-<name>.html`). The line to replace is written out in full. So the replacement works only while `make_report.py` holds exactly this line. |
| 27 | `    assert code != src and f"{T}/out-{name}.html" in code` | The `assert` stops the test when the text did not change or when the new output path is not in it. |
| 28 | `    code = patch(code)` | `patch` may change the text once more. The default changes nothing. |
| 29 | `    open(f"{T}/gen-{name}.py", "w").write(code)` | Writes the text to `gen-<name>.py` in the temporary folder. |
| 30 | `    r = subprocess.run([sys.executable, f"{T}/gen-{name}.py"], capture_output=True, text=True)` | Runs the copy as a separate process with the same Python program (`sys.executable`). Collects its standard output and its error output as text. |
| 31 | `    lines = [l for l in (r.stdout + r.stderr).splitlines() if "FAIL" in l or "STOP" in l or "NOT WRITTEN" in l or l.startswith("wrote")]` | Keeps the lines that hold `FAIL`, `STOP` or `NOT WRITTEN`, or that start with `wrote`. The generator prints `STOP` when it ends early, `FAIL` for a failed self-check, `NOT WRITTEN` after a failed self-check, and `wrote` after it wrote the page [Ref1]. |
| 32 | `    print(f"--- {name}: exit status {r.returncode}; output file written: {os.path.exists(f'{T}/out-{name}.html')}")` | Prints the case name, the exit status, and whether the output file exists (`True` or `False`). |
| 33 | `    for l in lines[:4]:` | Loop over the first 4 kept lines. |
| 34 | `        print("    " + l[:230])` | Prints each of them, cut to 230 characters and indented by 4 spaces. |
| 35 | `    return r.returncode` | Returns the exit status of the generator copy. |

### The nine damage functions (lines 37 to 65)

| Line | Source | Explanation |
|---:|---|---|
| 37 | `def drop_one(d):` | Starts the damage function `drop_one`: one part L record removed. |
| 38 | `    i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "rerun-L" and r["kernel"] == "oldread")` | `i`: the index of the first part L record (data set `rerun-L`) of the kernel `oldread`. |
| 39 | `    del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1` | Deletes that record. It also lowers the stored record count by 1, so the generator's test of the total count still passes. In the saved run the generator stopped with: part L, oldread: expected 6 interval records, found 5 [Ref2]. |
| 40 | `def change_a(d):` | Starts the damage function `change_a`: one part A rate changed. |
| 41 | `    r = next(r for r in d["intervals"] if r["dataset"] == "rerun-A" and r["binary"] == "bw_new" and r["kernel"] == "read" and r["session"] == 1 and r["round"] == 1)` | `r`: the first record of part A (data set `rerun-A`) with binary `bw_new` and kernel `read` (the new read kernel) in session 1, round 1. |
| 42 | `    r["GBps"] = round(r["GBps"] + 5.0, 2)` | Raises the rate `GBps` of that record by 5.0 GB/s (from 330.59 to 335.59 GB/s with the current `facts.json`). In the saved run the generator stopped with a message that names the file `threads120.csv` and ends with `line 11: not the interval row of this record` [Ref2]. |
| 43 | `def change_bwx(d):` | Starts the damage function `change_bwx`: one part C rate changed. |
| 44 | `    r = next(r for r in d["intervals"] if r["dataset"] == "rerun-C" and r["kernel"] == "read")` | `r`: the first part C record (data set `rerun-C`) of the kernel `read`. |
| 45 | `    r["GBps"] = round(r["GBps"] + 0.5, 3)` | Raises the rate of that record by 0.5 GB/s. In the saved run the generator stopped with: sum of the T rows 320.900964 is not the record value 321.401 (both in GB/s) [Ref2]. |
| 46 | `def change_bwx_old(d):` | Starts the damage function `change_bwx_old`: one rate of the runner `bwx` changed. |
| 47 | `    r = next(r for r in d["intervals"] if r["dataset"] == "B7a" and r["kernel"] == "read" and r["pos"] == 6)` | `r`: the first record of the data set `B7a` with the kernel `read` at position 6. `B7a` is an earlier 8000 MT/s run with the older runner `bwx`. |
| 48 | `    r["GBps"] = round(r["GBps"] + 0.5, 3)` | Raises the rate of that record by 0.5 GB/s. In the saved run the generator stopped with: sum of the T rows 319.107060 is not the record value 319.607 (both in GB/s) [Ref2]. |
| 49 | `def drop_bwx_old(d):` | Starts the damage function `drop_bwx_old`: one record of the runner `bwx` removed. |
| 50 | `    i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "B5a-rev" and r["kernel"] == "asmread")` | `i`: the index of the first `asmread` record of the data set `B5a-rev`. `B5a-rev` is an earlier 8000 MT/s run with the runner `bwx` in reverse kernel order. |
| 51 | `    del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1` | Deletes that record and lowers the stored count by 1. In the saved run the generator stopped with: runner bwx, reverse order, asmread: expected 4 interval records, found 3 [Ref2]. |
| 52 | `def change_10mod(d):` | Starts the damage function `change_10mod`: one rate of a 10-module boot changed. |
| 53 | `    r = next(r for r in d["intervals"] if r["dataset"] == "X1d10" and r["kernel"] == "asmread" and r["pos"] == 1)` | `r`: the first record of the data set `X1d10` with the kernel `asmread` at position 1. `X1d10` is an earlier `bwx12` run in a boot with 10 memory modules. |
| 54 | `    r["GBps"] = round(r["GBps"] + 0.5, 3)` | Raises the rate of that record by 0.5 GB/s. In the saved run the generator stopped with: sum of the T rows 260.369381 is not the record value 260.869 (both in GB/s) [Ref2]. |
| 55 | `def drop_x2d12(d):` | Starts the damage function `drop_x2d12`: one record of the data set `X2d12` removed. |
| 56 | `    i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "X2d12" and r["kernel"] == "oldread" and r["pos"] == 0)` | `i`: the index of the first `oldread` record at position 0 of the data set `X2d12`. `X2d12` is an earlier `bwx12` run at 8000 MT/s with 12 memory modules. |
| 57 | `    del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1` | Deletes that record and lowers the stored count by 1. In the saved run the generator stopped with: X2d12, oldread at position 0: expected 2 interval records, found 1 [Ref2]. |
| 58 | `def bwx_load(d):` | Starts the damage function `bwx_load`: the load at launch of one process changed. |
| 59 | `    r = next(r for r in d["intervals"] if r["dataset"] == "C3b" and r["kernel"] == "read")` | `r`: the first `read` record of the data set `C3b`, an earlier 8000 MT/s run with the runner `bwx`. |
| 60 | `    for x in d["intervals"]:` | Loop over all interval records. |
| 61 | `        if x["proc_key"] == r["proc_key"]:` | Picks every record of the same process as `r` (same `proc_key`). |
| 62 | `            x["load1_at_launch"] = round(x["load1_at_launch"] + 1.0, 2)` | Raises `load1_at_launch`, the load at launch, by 1.0 in each of these records. In the saved run the generator stopped with: not the header line of the process of this record (tag, binary, launch time or load differs) [Ref2]. |
| 63 | `def other_boot(d):` | Starts the damage function `other_boot`: one record with another boot id. |
| 64 | `    r = next(r for r in d["intervals"] if r["dataset"] == "control-I" and r["kernel"] == "asmread")` | `r`: the first `asmread` record of control I (data set `control-I`). |
| 65 | `    r["boot"] = "00000000-0000-0000-0000-000000000000"` | Replaces the boot id of that record by an id of zeros. The record then looks like a record from another boot. In the saved run the generator stopped with: the 7200 MT/s records are not from one boot [Ref2]. |

### The 11 cases (lines 66 to 77)

| Line | Source | Explanation |
|---:|---|---|
| 66 | `res = {}` | `res`: the exit status of each case, stored under a description. Lines 67 to 77 call `run` once per case, one case after the other. |
| 67 | `res["control (no damage)"] = run("ok", lambda d: None)` | Case `ok`, the control: it changes nothing (`lambda d: None` is a function that does nothing). It shows that the patched copy of the generator runs to its end on undamaged facts. Without it, a generator that always stops would pass every other case. |
| 68 | `res["one part L record removed"] = run("count", drop_one)` | Case `count` with `drop_one` (line 37). It tests that the generator notices one missing record of part L, although the stored total count fits. |
| 69 | `res["one part A value changed by 5 GB/s"] = run("valueA", change_a)` | Case `valueA` with `change_a` (line 40). It tests that a changed rate of part A cannot pass. The generator requires that the row of the raw file `threads120.csv` holds the rate of the record. |
| 70 | `res["one bwx12 value changed by 0.5 GB/s"] = run("valueX", change_bwx)` | Case `valueX` with `change_bwx` (line 43). It tests the same for a rate of a `bwx12` process of the rerun. There the generator sums the T rows of the raw csv file and requires the value of the record. |
| 71 | `res["one record from another boot"] = run("boot", other_boot)` | Case `boot` with `other_boot` (line 63). It tests that the generator stops when the records of the rerun are not from one boot. |
| 72 | `res["one value of runner bwx changed by 0.5 GB/s"] = run("valueB", change_bwx_old)` | Case `valueB` with `change_bwx_old` (line 46). It tests the rate check for a record of the older runner `bwx`. |
| 73 | `res["one record of runner bwx removed"] = run("countB", drop_bwx_old)` | Case `countB` with `drop_bwx_old` (line 49). It tests the record count of a data set of the runner `bwx`. |
| 74 | `res["one asmread value of a 10-module boot changed by 0.5 GB/s"] = run("value10", change_10mod)` | Case `value10` with `change_10mod` (line 52). It tests the rate check for a record of a boot with 10 memory modules. |
| 75 | `res["one record of row X2d12 removed"] = run("countX2", drop_x2d12)` | Case `countX2` with `drop_x2d12` (line 55). It tests the record count of the data set `X2d12`. |
| 76 | `res["load at launch of one process of runner bwx changed by 1.0"] = run("loadB", bwx_load)` | Case `loadB` with `bwx_load` (line 58). It tests that the generator compares the load at launch of a record with the raw file. |
| 77 | `res["a reference path that does not exist"] = run("ref", lambda d: None, lambda s: s.replace('whole-chip-read-drop-easy-read.html"', 'no-such-file.html"'))` | Case `ref`, the last case. It leaves the facts unchanged and changes the text of the generator: the path of the earlier report gets a file name that does not exist. In the saved run the generator stopped with: the earlier report does not exist [Ref2]. The earlier report is the report page of 2026-11-15 (`whole-chip-read-drop-easy-read.html`). The generator reads it and lists it as a reference [Ref1]. |

### Verdict (lines 78 to 83)

| Line | Source | Explanation |
|---:|---|---|
| 78 | `print()` | Prints an empty line before the verdict. |
| 79 | `ok = res["control (no damage)"] == 0 and all(v != 0 for k, v in res.items() if k != "control (no damage)")` | `ok` is true when the control gave exit status 0 and every other case gave a value other than 0. Only the exit status is tested. The fact `output file written` of line 32 is printed for the reader, and no code tests it. An exit status other than 0 from a Python error that the generator does not catch would also count as a stop. |
| 80 | `for k, v in res.items():` | Loop over the cases, in the order in which they ran. |
| 81 | `    print(f"{'PASS' if (v == 0) == (k.startswith('control')) else 'FAIL'}  {k}: exit status {v}")` | Prints one line per case: `PASS` when the control gave 0 or a damaged case gave another value, else `FAIL`. The description and the exit status follow. |
| 82 | `shutil.rmtree(T, ignore_errors=True)` | Deletes the temporary folder with all copies. An error of the deletion is ignored. |
| 83 | `sys.exit(0 if ok else 1)` | Ends with exit status 0 when `ok` is true, else with 1. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`: lines 29 to 32: the fixed paths `S`, `R`, `OUT` and `EARLIER`. Lines 42 to 49: `stop` prints a `STOP` line and ends the script, and `need` calls it. Lines 234 and 1390: the two places with the text `S + "/facts.json"`. Lines 1384 to 1386 and 1455: the generator reads the earlier report and lists it as a reference. Lines 2820 to 2831: the `FAIL` lines, `NOT WRITTEN` with exit status 1, the only write of the page, and the `wrote` line.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/render/fail-loud-test-output.txt`: saved output of one run of this test: per case the exit status, the fact `output file written`, and the first kept line of the generator. Then the 11 `PASS` lines.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts.json`: the list `intervals` (793 records) and the stored count `meta.counts.intervals` (793).
