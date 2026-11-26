# `go2.sha` explained

- Source file: `go2.sha` in this folder (text file, 1 lines, 73 bytes).
- sha256 of the source when this page was built: `0ff09f6f904d3e2c40f458f6f37b370cf51dc455fe613fbbc07a48d083d0278c`.
- Role in the whole-chip test: sha256 of go2.sh, the script of control I, written at launch.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The file holds one line: the sha256 checksum of the local file go2.sh, the script of control I. The facts sheet calls it "written at launch", and build_facts.py later tested go2.sh against it (check 20 of the facts sheet).

<details>
<summary>Words used here</summary>

- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **sha256sum**: the Linux tool that prints the sha256 of a file. With the option `-c` it reads a list such as this file and tests every named file against its checksum.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Rerun**: the whole-chip read test of 2026-11-17 at 7200 MT/s.
- **Run files**: the scripts and spec files of the rerun in this folder: go.sh, ra.sh, like.spec, cfwd.spec, crev.spec, and go2.sh, which was added later.
- **Agent**: the AI coding assistant (Claude Code) that ran the rerun on CRB for the user. FACTS.md calls it "the agent".
- **Local copy, agent's server**: the agent's server is the machine that holds this folder. The local copy of a run file is the file in this folder. CRB held its own copies under `~/cache-perf/w120-7200-20261117`.
- **Session record**: the record of the Claude Code session of 2026-11-17 in which the agent ran the rerun. It is a file with one JSON record per line. It holds the commands that the agent ran and their output. The times in it are from the clock of the agent's server. The file lies outside the project folder.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **go.sh**: the driver script of the rerun: three sessions of parts A, L, C and a fourth part C process.
- **ra.sh**: the script of part A.
- **go2.sh**: the script of control I: the part L line twice, each time from an idle machine.
- **rx.sh**: the runner script of the bwx12 processes (parts L, C, I). It reads a spec file and starts one process per line.
- **Spec file**: a text file for rx.sh. Each line has the form `tag|arguments` and starts one process. like.spec, cfwd.spec and crev.spec hold one line each.
- **Facts sheet**: the file FACTS.md in this folder. The script build_facts.py wrote it from the raw files. It is the source of the report of the rerun.
- **Check 2, check 15, check 18, check 20, check 26**: numbered integrity checks in section 1.4 of the facts sheet. build_facts.py runs them and writes one line per check.
- **Rules file**: baselines-and-rules.txt in this folder: the list of the 8000 MT/s baselines and the comparison rules, written before the run.
- **probe.txt**: a file that ra.sh writes on CRB at the start of part A. It holds the time, the load, the boot id, and the sha256 of bw_old, bw_new and ra.sh.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **launches.txt, launch line**: rx.sh writes one launch line per process into launches.txt on CRB. The line holds the tag and the arguments of the process.
- **env.txt**: a file that rx.sh writes on CRB when it starts. It holds the date, the Linux kernel release, the load, the logins, the busiest processes, and the path and the sha256 of the binary.
- **Logs**: the saved output of go.sh and of go2.sh: the files go-T72-20261117T221209Z.log and go2-T72-20261117T222335Z.log in the results folder.

</details>

## How to read this file

1. Read the line as: checksum (64 hexadecimal digits, 256 bits), two spaces, file name. The name has no folder part. It names go2.sh in the folder of go2.sha (line 1).
2. The checksum of go2.sh is not in local.sha. local.sha has the file time 22:12:03. go2.sh has the file time 22:23:30, 687 s later (2026-11-17 UTC, clock of the agent's server). The facts sheet says that control I was added after the first numbers of parts A, L and C were seen (decision (g)) [Ref3].
3. The agent wrote go2.sh and then this file in one command line. The part that wrote this file is `sha256sum go2.sh > go2.sha`. The same command line copied both files to the folder `~/cache-perf/w120-7200-20261117` on CRB and ran `sha256sum -c go2.sha` there. The output shows `go2.sh: OK` [Ref6].
4. To test go2.sh against the line, run `sha256sum -c go2.sha` in this folder. On 2026-11-21 it printed `go2.sh: OK` (run for this page).
5. build_facts.py reads this line together with the 5 lines of local.sha and reports the test as check 20 of the facts sheet. The facts sheet in this folder was built before line 20 of go.sh was edited on 2026-11-24. It says: pass, 6 files equal [Ref1] [Ref3].
6. go2.sha has the file time 22:23:30, less than 1 s after the file time of go2.sh. go2.sh started on CRB at 22:23:35 by the clock of CRB. The two clocks were not compared [Ref3].
7. The session record holds both steps with times of one clock, the clock of the agent's server. The command line that wrote go2.sh and go2.sha was sent at 22:23:30 UTC. The command that started go2.sh was sent at 22:23:35 UTC [Ref6].
8. facts_text.py lists the file as Ref16 of the facts sheet with the words "sha256 of go2.sh, written at launch" [Ref2].

## Behavior a reader must know

- **What the line allows.** A reader can test whether go2.sh still has the content that it had when go2.sha was written (file time 22:23:30 UTC on 2026-11-17). When go2.sh was changed later, `sha256sum -c` and check 20 fail. Check 20 also tests the 5 files of local.sha. Since 2026-11-24 a new run of build_facts.py fails check 20 because of go.sh. Line 20 of go.sh was edited on that day. The page `go.sh.md` in this folder (the explanation of go.sh) gives the proof. `sha256sum -c go2.sha` still prints `go2.sh: OK` (tested on 2026-11-24).
- **The copy on CRB.** The command `sha256sum -c go2.sha` on CRB printed `go2.sh: OK` about 5 s before go2.sh was started. The session record holds no command of the agent between this test and the start of go2.sh [Ref6]. The 2 logs, the 3 probe.txt files and the 9 env.txt files of the rerun hold no checksum of go2.sh (limit stated in check 26 of the facts sheet) [Ref3]. Check 20 tests the local copy only.
- **What the records of CRB do show.** The log of go2.sh ends with ALLDONE and holds no line that starts with FAILED (check 2 of the facts sheet) [Ref3]. go2.sh tests the sha256 of rx.sh and of bwx12 on CRB before the first measurement, with the same two values as go.sh [Ref5] [Ref4].
- **Who wrote the file.** The agent wrote it. The session record holds the command: `sha256sum go2.sh > go2.sha`, run in this folder [Ref6]. The facts sheet calls the file "written at launch" [Ref3].

## Call sequence in the whole-chip test

- `build_facts.py:main`: after the run: builds FACTS.md and facts.json
  - `build_facts.py:run_checks`: check 20: reads local.sha and go2.sha, tests the 6 files
    - `facts_data.py:sha256`: computes the sha256 of one named file
  - `facts_text.py:render`: writes the text of the facts sheet
    - `facts_text.py:register`: puts go2.sha into the file list as Ref16

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>The one line: checksum of go2.sh</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1  38edfa540997d706fa0cfb71e27d8c592122f27bf4fb7f1e1f91bfb197f02742  go2.sh</pre></td><td valign="top">Checksum of <code>go2.sh</code>, the script of control I.<ul><li>The line holds the sha256 of the file content as 64 hexadecimal digits, then two spaces, then the file name. This is the output format of the tool <code>sha256sum</code>.</li><li>build_facts.py tests the local copy of go2.sh against this value in check 20 of the facts sheet [Ref1].</li><li>The session record holds a test of the copy on CRB. The command that copied go2.sh to CRB ran <code>sha256sum -c go2.sha</code> there. It printed <code>go2.sh: OK</code> about 5 s before go2.sh was started [Ref6].</li></ul></td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: script that builds the facts sheet. Lines 772 to 780 of the function `run_checks` read local.sha and go2.sha, compute the sha256 of every named file of this folder, and report check 20. Lines 741 to 746 compare the launch lines with the spec files (check 15). The function `main` (lines 1033 to 1052) ends with status 1 when a check fails.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`: script that writes the text of the facts sheet. Lines 175 and 176 put local.sha and go2.sha into its file list. Lines 384 to 388 read the file time of local.sha and require that it is later than the file time of the rules file.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: facts sheet of the rerun. Used here: section 1.1 (start times of go.sh and go2.sh), section 1.4 (checks 2, 15, 18, 20 and 26), decisions (g) and (h) of section 2, and entries Ref15 and Ref16 of its file list (section 7).
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: driver script. Lines 13 and 14 hold the sha256 of bwx12 and of rx.sh. Lines 22 and 23 test them on CRB and stop the run when one differs.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go2.sh`: script of control I, the file that this checksum belongs to. Lines 18 and 19 test the sha256 of rx.sh and of bwx12 on CRB and stop the run when one differs.
- [Ref6] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: session record of 2026-11-17. The file lies outside the project folder. Line 353 holds the command line that wrote go2.sh and go2.sha, packed both files with `tar` (a tool that joins files into one stream), sent them to CRB through `ssh` (the remote login tool), unpacked them in the folder `~/cache-perf/w120-7200-20261117` and ran `sha256sum -c go2.sha` there. It was sent at 22:23:30 UTC. Line 354 holds its output with `go2.sh: OK`. Line 365 holds the command that started go2.sh. It was sent at 22:23:35 UTC. Lines 355 to 364 hold no command.
