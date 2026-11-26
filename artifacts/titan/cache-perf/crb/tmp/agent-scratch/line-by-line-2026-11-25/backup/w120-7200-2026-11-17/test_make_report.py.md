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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  #!/usr/bin/env python3
 2  """test_make_report.py - fail-loud tests of make_report.py.
 3
 4  Each case runs a copy of the generator on a damaged copy of facts.json.
 5  The generator must stop, or it must print a FAIL line and exit with status 1, and it must not write a page.
 6  The copies and their output go to a temporary folder under test-tmp of this folder. The real report and facts.json are not touched.
 7  Run: python3 test_make_report.py   (exit status 0 = all cases behave as required)"""</pre></td><td valign="top">Usage text. "Fail-loud" means here: the generator must stop with an error when its input is wrong, and it must not write a page. make_report.py is the generator of the report page of the rerun. Its input is facts.json, the file with one record per timed interval.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 8  import copy
 9  import json
10  import os
11  import shutil
12  import subprocess
13  import sys
14  import tempfile</pre></td><td valign="top">Modules of the Python standard library.</td></tr>
<tr><td colspan="2"><b>Setup: temporary folder and the two inputs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">15  S = os.path.dirname(os.path.abspath(__file__))
16  os.makedirs(S + "/test-tmp", exist_ok=True)          # the copies stay inside the scratch folder of this rerun
17  T = tempfile.mkdtemp(prefix="test_make_report_", dir=S + "/test-tmp")
18  src = open(S + "/make_report.py").read()
19  facts = json.load(open(S + "/facts.json"))
20</pre></td><td valign="top"><ul><li><code>S</code> is the folder of this script.</li><li><code>T</code> is a new temporary folder inside <code>S/test-tmp</code>. Every file that the test writes goes there.</li><li><code>src</code> is the text of make_report.py.</li><li><code>facts</code> is the parsed content of facts.json.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>run</code>: one test case</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">21  def run(name, mutate, patch=lambda s: s):
22      d = copy.deepcopy(facts)
23      mutate(d)
24      json.dump(d, open(f"{T}/facts-{name}.json", "w"))
25      code = src.replace('S + "/facts.json"', repr(f"{T}/facts-{name}.json"))
26      code = code.replace('OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"', f'OUT = "{T}/out-{name}.html"')
27      assert code != src and f"{T}/out-{name}.html" in code
28      code = patch(code)
29      open(f"{T}/gen-{name}.py", "w").write(code)</pre></td><td valign="top">Prepare the case <code>name</code>:<ul><li>Copy the facts in memory, damage the copy with <code>mutate</code>, and write it to <code>facts-&lt;name&gt;.json</code> in the temporary folder.</li><li>In the text of the generator, replace <code>S + "/facts.json"</code> by the path of the damaged copy. This text occurs 2 times: where the generator reads the file, and in its reference list [Ref1].</li><li>Replace the line that sets <code>OUT</code>, the path of the report page, by a path in the temporary folder.</li><li>The <code>assert</code> stops the test when the text did not change or when the new output path is not in it.</li><li><code>patch</code> may change the text once more. The default changes nothing.</li><li>Write the text to <code>gen-&lt;name&gt;.py</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">30      r = subprocess.run([sys.executable, f"{T}/gen-{name}.py"], capture_output=True, text=True)
31      lines = [l for l in (r.stdout + r.stderr).splitlines() if "FAIL" in l or "STOP" in l or "NOT WRITTEN" in l or l.startswith("wrote")]
32      print(f"--- {name}: exit status {r.returncode}; output file written: {os.path.exists(f'{T}/out-{name}.html')}")
33      for l in lines[:4]:
34          print("    " + l[:230])
35      return r.returncode
36</pre></td><td valign="top"><ul><li>Run the copy as a separate process with the same Python program. Collect its standard output and its error output as text.</li><li>Keep the lines that hold <code>FAIL</code>, <code>STOP</code> or <code>NOT WRITTEN</code>, or that start with <code>wrote</code>. The generator prints <code>STOP</code> when it ends early, <code>FAIL</code> for a failed self-check, <code>NOT WRITTEN</code> after a failed self-check, and <code>wrote</code> after it wrote the page [Ref1].</li><li>Print the case name, the exit status, and whether the output file exists.</li><li>Print the first 4 kept lines, each cut to 230 characters.</li><li>Return the exit status.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>drop_one</code>: one part L record removed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">37  def drop_one(d):
38      i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "rerun-L" and r["kernel"] == "oldread")
39      del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1</pre></td><td valign="top"><code>drop_one</code> deletes the first part L record (<code>rerun-L</code>) of the kernel <code>oldread</code>. It also lowers the stored record count by 1, so the generator's test of the total count still passes. In the saved run the generator stopped with: part L, oldread: expected 6 interval records, found 5 [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>change_a</code>: one part A rate changed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">40  def change_a(d):
41      r = next(r for r in d["intervals"] if r["dataset"] == "rerun-A" and r["binary"] == "bw_new" and r["kernel"] == "read" and r["session"] == 1 and r["round"] == 1)
42      r["GBps"] = round(r["GBps"] + 5.0, 2)</pre></td><td valign="top"><code>change_a</code> takes the first record of part A (<code>rerun-A</code>) with binary <code>bw_new</code> and kernel <code>read</code> (the new read kernel) in session 1, round 1. It raises the rate <code>GBps</code> by 5.0 GB/s (from 330.59 to 335.59 GB/s with the current facts.json). In the saved run the generator stopped with: threads120.csv line 11: not the interval row of this record [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>change_bwx</code>: one part C rate changed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">43  def change_bwx(d):
44      r = next(r for r in d["intervals"] if r["dataset"] == "rerun-C" and r["kernel"] == "read")
45      r["GBps"] = round(r["GBps"] + 0.5, 3)</pre></td><td valign="top"><code>change_bwx</code> raises by 0.5 GB/s the rate of the first part C record (<code>rerun-C</code>) of the kernel <code>read</code>. In the saved run the generator stopped with: sum of the T rows 320.900964 is not the record value 321.401 (both in GB/s) [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>change_bwx_old</code>: one rate of runner bwx changed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">46  def change_bwx_old(d):
47      r = next(r for r in d["intervals"] if r["dataset"] == "B7a" and r["kernel"] == "read" and r["pos"] == 6)
48      r["GBps"] = round(r["GBps"] + 0.5, 3)</pre></td><td valign="top"><code>change_bwx_old</code> raises by 0.5 GB/s the rate of the first record of the data set <code>B7a</code> with the kernel <code>read</code> at position 6. <code>B7a</code> is an earlier 8000 MT/s run with the older runner bwx. In the saved run the generator stopped with: sum of the T rows 319.107060 is not the record value 319.607 (both in GB/s) [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>drop_bwx_old</code>: one record of runner bwx removed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">49  def drop_bwx_old(d):
50      i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "B5a-rev" and r["kernel"] == "asmread")
51      del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1</pre></td><td valign="top"><code>drop_bwx_old</code> deletes the first <code>asmread</code> record of the data set <code>B5a-rev</code> and lowers the stored count by 1. <code>B5a-rev</code> is an earlier 8000 MT/s run with the runner bwx in reverse kernel order. In the saved run the generator stopped with: runner bwx, reverse order, asmread: expected 4 interval records, found 3 [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>change_10mod</code>: one rate of a 10-module boot changed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">52  def change_10mod(d):
53      r = next(r for r in d["intervals"] if r["dataset"] == "X1d10" and r["kernel"] == "asmread" and r["pos"] == 1)
54      r["GBps"] = round(r["GBps"] + 0.5, 3)</pre></td><td valign="top"><code>change_10mod</code> raises by 0.5 GB/s the rate of the first record of the data set <code>X1d10</code> with the kernel <code>asmread</code> at position 1. <code>X1d10</code> is an earlier bwx12 run in a boot with 10 memory modules. In the saved run the generator stopped with: sum of the T rows 260.369381 is not the record value 260.869 (both in GB/s) [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>drop_x2d12</code>: one record of data set X2d12 removed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">55  def drop_x2d12(d):
56      i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "X2d12" and r["kernel"] == "oldread" and r["pos"] == 0)
57      del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1</pre></td><td valign="top"><code>drop_x2d12</code> deletes the first <code>oldread</code> record at position 0 of the data set <code>X2d12</code> and lowers the stored count by 1. <code>X2d12</code> is an earlier bwx12 run at 8000 MT/s with 12 memory modules. In the saved run the generator stopped with: X2d12, oldread at position 0: expected 2 interval records, found 1 [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>bwx_load</code>: load at launch of one process changed</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">58  def bwx_load(d):
59      r = next(r for r in d["intervals"] if r["dataset"] == "C3b" and r["kernel"] == "read")
60      for x in d["intervals"]:
61          if x["proc_key"] == r["proc_key"]:
62              x["load1_at_launch"] = round(x["load1_at_launch"] + 1.0, 2)</pre></td><td valign="top"><code>bwx_load</code> finds the first <code>read</code> record of the data set <code>C3b</code>, an earlier 8000 MT/s run with the runner bwx. In every record of the same process (same <code>proc_key</code>) it raises <code>load1_at_launch</code>, the load at launch, by 1.0. In the saved run the generator stopped with: not the header line of the process of this record (tag, binary, launch time or load differs) [Ref2].</td></tr>
<tr><td colspan="2"><b>Function <code>other_boot</code>: one record with another boot id</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">63  def other_boot(d):
64      r = next(r for r in d["intervals"] if r["dataset"] == "control-I" and r["kernel"] == "asmread")
65      r["boot"] = "00000000-0000-0000-0000-000000000000"</pre></td><td valign="top"><code>other_boot</code> replaces the boot id of the first <code>asmread</code> record of control I by an id of zeros. The record then looks like a record from another boot. In the saved run the generator stopped with: the 7200 MT/s records are not from one boot [Ref2].</td></tr>
<tr><td colspan="2"><b>The 11 cases</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">66  res = {}
67  res["control (no damage)"] = run("ok", lambda d: None)
68  res["one part L record removed"] = run("count", drop_one)
69  res["one part A value changed by 5 GB/s"] = run("valueA", change_a)
70  res["one bwx12 value changed by 0.5 GB/s"] = run("valueX", change_bwx)
71  res["one record from another boot"] = run("boot", other_boot)
72  res["one value of runner bwx changed by 0.5 GB/s"] = run("valueB", change_bwx_old)
73  res["one record of runner bwx removed"] = run("countB", drop_bwx_old)
74  res["one asmread value of a 10-module boot changed by 0.5 GB/s"] = run("value10", change_10mod)
75  res["one record of row X2d12 removed"] = run("countX2", drop_x2d12)
76  res["load at launch of one process of runner bwx changed by 1.0"] = run("loadB", bwx_load)
77  res["a reference path that does not exist"] = run("ref", lambda d: None, lambda s: s.replace('whole-chip-read-drop-easy-read.html"', 'no-such-file.html"'))</pre></td><td valign="top">Call <code>run</code> once per case, one case after the other, and store each exit status in <code>res</code> under a description.<ul><li>The first case changes nothing. It is the control.</li><li>The next 9 cases use one damage function each.</li><li>The last case leaves the facts unchanged. It changes the text of the generator: the path of the earlier report gets a file name that does not exist. In the saved run the generator stopped with: the earlier report does not exist [Ref2].</li><li>The earlier report is the report page of 2026-11-15 (<code>whole-chip-read-drop-easy-read.html</code>). The generator reads it and lists it as a reference [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b>Verdict</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">78  print()
79  ok = res["control (no damage)"] == 0 and all(v != 0 for k, v in res.items() if k != "control (no damage)")
80  for k, v in res.items():
81      print(f"{'PASS' if (v == 0) == (k.startswith('control')) else 'FAIL'}  {k}: exit status {v}")</pre></td><td valign="top"><ul><li><code>ok</code> is true when the control gave exit status 0 and every other case gave a value other than 0.</li><li>Print one line per case: <code>PASS</code> when the control gave 0 or a damaged case gave another value, else <code>FAIL</code>.</li><li>Only the exit status is tested. The fact <code>output file written</code> of line 32 is printed for the reader, and no code tests it.</li><li>An exit status other than 0 from a Python error that the generator does not catch would also count as a stop.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">82  shutil.rmtree(T, ignore_errors=True)
83  sys.exit(0 if ok else 1)</pre></td><td valign="top">Delete the temporary folder with all copies. End with exit status 0 when <code>ok</code> is true, else with 1.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`: lines 29 to 32: the fixed paths `S`, `R`, `OUT` and `EARLIER`. Lines 42 to 49: `stop` prints a `STOP` line and ends the script, and `need` calls it. Lines 234 and 1390: the two places with the text `S + "/facts.json"`. Lines 1384 to 1386 and 1455: the generator reads the earlier report and lists it as a reference. Lines 2820 to 2831: the `FAIL` lines, `NOT WRITTEN` with exit status 1, the only write of the page, and the `wrote` line.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/render/fail-loud-test-output.txt`: saved output of one run of this test: per case the exit status, the fact `output file written`, and the first kept line of the generator. Then the 11 `PASS` lines.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts.json`: the list `intervals` (793 records) and the stored count `meta.counts.intervals` (793).
