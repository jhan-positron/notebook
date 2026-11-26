# `local.sha` explained

- Source file: `local.sha` in this folder (text file, 5 lines, 372 bytes).
- sha256 of the source when this page was built: `dce73e4e22dd068e78806142d3a0a1b4bb54eaf4ba5e5b7012fdb0d6a9c2ab26`.
- Role in the whole-chip test: sha256 list of go.sh, ra.sh and the three spec files, written at launch.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The file lists the sha256 checksums that five run files of the rerun had at launch (the start of the rerun on 2026-11-17): go.sh, ra.sh, like.spec, cfwd.spec and crev.spec. The facts sheet calls it "written at launch", and build_facts.py later tested the five files against it (check 20 of the facts sheet).

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

1. Read each line as: checksum, two spaces, file name. The checksum has 64 hexadecimal digits (256 bits) (lines 1-5).
2. The names have no folder part. They name files in the folder of local.sha. The order is: the driver script, the script of part A, then the three spec files (lines 1-5).
3. The agent wrote the file with the command `sha256sum go.sh ra.sh like.spec cfwd.spec crev.spec > local.sha` in this folder. The same command line copied the five files and local.sha to the folder `~/cache-perf/w120-7200-20261117` on CRB and ran `sha256sum -c local.sha` there. The output shows `OK` for all 5 files [Ref7].
4. To test the files against the list, run `sha256sum -c local.sha` in this folder. The tool prints `name: OK` for each file with unchanged content. On 2026-11-21 all 5 files gave OK (run for this page). On 2026-11-24 it printed `go.sh: FAILED` and `OK` for the 4 other files. Line 20 of go.sh was edited on that day.
5. build_facts.py makes the same test for local.sha and go2.sha together and reports it as check 20 of the facts sheet. The facts sheet in this folder was built before the edit of go.sh. It says: pass, 6 files equal [Ref1] [Ref3]. Since the edit a new run of build_facts.py fails this check. It then stops and writes no file [Ref8].
6. facts_text.py reads the file time of local.sha. The facts sheet uses it in decision (h) of its section 2. The rules file has the file time 22:11:51, and local.sha has the file time 22:12:03 (2026-11-17 UTC, clock of the agent's server). go.sh started at 22:12:09 by the clock of CRB. The two clocks were not compared [Ref2] [Ref3].
7. The session record holds both steps with times of one clock, the clock of the agent's server. The command that wrote local.sha was sent at 22:12:03 UTC. The command that started go.sh was sent at 22:12:08 UTC [Ref7].

## Behavior a reader must know

- **What the list allows.** A reader can test whether a listed file still has the content that it had when local.sha was written (file time 22:12:03 UTC on 2026-11-17). When a file was changed later, `sha256sum -c` and check 20 fail. This is the case for go.sh since 2026-11-24. Line 20 of go.sh was edited on that day (the text of one message). local.sha was not changed. So line 1 still holds the checksum of the text that ran. With the old line 20 put back, go.sh has this checksum again [Ref8]. The page `go.sh.md` in this folder (the explanation of go.sh) shows the old line.
- **Local copies only.** The facts sheet treats the list as checksums of the local copies. Check 20 tests the files of this folder. So the list alone does not show what ran on CRB [Ref3]. Line 1 is the checksum that go.sh had at launch. Since 2026-11-24 it is not the checksum of the local go.sh.
- **Evidence that CRB ran the listed content.** All 5 files: the command `sha256sum -c local.sha` on CRB printed `OK` for each file about 5 s before go.sh was started. The session record holds no command of the agent between this test and the start of go.sh [Ref7]. ra.sh: in addition its own checksum in probe.txt (check 18) [Ref6]. The three spec files: in addition the launch lines in launches.txt (check 15). go.sh: the 2 logs, the 3 probe.txt files and the 9 env.txt files of the rerun hold no checksum of it (limit stated in check 26) [Ref3]. For go.sh the listed content is the text that ran. The local go.sh differs from it in line 20 since 2026-11-24.
- **Not in this list.** rx.sh and bwx12: go.sh holds their sha256 values and tests them on CRB before the first measurement [Ref4]. bw_old and bw_new: ra.sh tests them [Ref5]. go2.sh: it has the file time 22:23:30, 687 s after local.sha. Its checksum is in the file go2.sha.
- **Who wrote the file.** The agent wrote it. The session record holds the command: `sha256sum go.sh ra.sh like.spec cfwd.spec crev.spec > local.sha`, run in this folder [Ref7]. The facts sheet calls the file "written at launch" [Ref3].
- **Do not write the list again.** The command of step 3 would replace the listed checksums with those of the present files. It would also change the file time of local.sha. Decision (h) of the facts sheet prints that file time [Ref2]. For a later copy of the edited go.sh to CRB, write the checksum list of the copied files under another name.

## Call sequence in the whole-chip test

- `build_facts.py:main`: after the run: builds FACTS.md and facts.json
  - `build_facts.py:run_checks`: check 20: reads local.sha and go2.sha, tests the 6 files
    - `facts_data.py:sha256`: computes the sha256 of one named file
  - `facts_text.py:render`: reads the file time of local.sha for decision (h)
    - `facts_text.py:register`: puts local.sha into the file list as Ref15

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>One line per run file: checksum, then file name</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1  75bc50b00b26438c00c425cff0ed8620352f7c668eec6dc2831d9ab009b198e3  go.sh</pre></td><td valign="top">Checksum that <code>go.sh</code>, the driver script of the rerun, had at launch.<ul><li>Every line has the same format: the sha256 of the file content as 64 hexadecimal digits, then two spaces, then the file name. This is the output format of the tool <code>sha256sum</code>.</li><li>The local go.sh no longer has this checksum. Its line 20 was edited on 2026-11-24 (the text of one message). Its sha256 is now d68cf6c0468abeb658765b950b9bd86b34ff9556070efcd954824f6e936da2bd. With the old line 20 put back it has the listed value again [Ref8].</li><li>The facts sheet states that the 2 logs, the 3 probe.txt files and the 9 env.txt files of the rerun hold no sha256 of go.sh [Ref3].</li><li>The session record holds a test of the copy on CRB. The command that copied the five files of this list to CRB ran <code>sha256sum -c local.sha</code> there. It printed <code>go.sh: OK</code> about 5 s before go.sh was started [Ref7].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2  6d67715e69d5d1fc020aa4ef4b22e7a12c11d771457513ffd7d6d38553626254  ra.sh</pre></td><td valign="top">Checksum of <code>ra.sh</code>, the script of part A. ra.sh also writes its own sha256 into <code>probe.txt</code> on CRB [Ref5]. The 3 probe.txt files of part A hold this same value (check 18 of the facts sheet) [Ref6] [Ref3].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">3  9b331df92ae5494f81d3ec4473de3d750802581201f008f09f15e6b394c788be  like.spec
4  cc04ea263193e6106a37ee7b238f878dd4a86312fcca7b14d821228ebc15e3d8  cfwd.spec
5  1541a85cdea9b67bcf9ceca1cf9a98de26d4c729474ffce9ed1e3941a2221fd3  crev.spec</pre></td><td valign="top">Checksums of the three spec files:<ul><li><code>like.spec</code>: the argument line of part L and of control I.</li><li><code>cfwd.spec</code>: the argument line of part C in the order oldread, read, asmread.</li><li><code>crev.spec</code>: the argument line of part C in the order asmread, read, oldread.</li></ul>No script of the rerun computes a checksum of a spec file on CRB. The facts sheet compares the launch lines that rx.sh wrote on CRB with the text of the three files (check 15) [Ref1]. The command that copied the files to CRB tested the three copies there against this list. It printed <code>OK</code> for each [Ref7].</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: script that builds the facts sheet. Lines 772 to 780 of the function `run_checks` read local.sha and go2.sha, compute the sha256 of every named file of this folder, and report check 20. Lines 741 to 746 compare the launch lines with the spec files (check 15). The function `main` (lines 1033 to 1052) ends with status 1 when a check fails. It builds the text of the sheet in line 1037. It writes the files after that, in lines 1038 to 1041. The script `facts_text4.py` writes a part of that text. Its line 1461 stops the build when a check failed.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`: script that writes the text of the facts sheet. Lines 175 and 176 put local.sha and go2.sha into its file list. Lines 384 to 388 read the file time of local.sha and require that it is later than the file time of the rules file. Lines 1174 to 1180 print this file time in decision (h).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: facts sheet of the rerun. Used here: section 1.1 (start times of go.sh and go2.sh), section 1.4 (checks 2, 15, 18, 20 and 26), decisions (g) and (h) of section 2, and entries Ref15 and Ref16 of its file list (section 7).
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: driver script. Lines 13 and 14 hold the sha256 of bwx12 and of rx.sh. Lines 22 and 23 test them on CRB and stop the run when one differs.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: script of part A. Lines 16 to 20 test the sha256 of bw_old and bw_new. Line 35 writes the sha256 of the two binaries and of ra.sh itself into probe.txt.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/probe.txt`: probe.txt of part A, session 1. Line 14 holds the sha256 of the copy of ra.sh that ran on CRB. The probe.txt files of sessions 2 and 3 hold the same value in line 14.
- [Ref7] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: session record of 2026-11-17. The file lies outside the project folder. Line 309 holds the command line that wrote local.sha, packed the five files and local.sha with `tar` (a tool that joins files into one stream), sent them to CRB through `ssh` (the remote login tool), unpacked them in the folder `~/cache-perf/w120-7200-20261117` and ran `sha256sum -c local.sha` there. It was sent at 22:12:03 UTC. Line 310 holds its output with `OK` for the 5 files. Line 313 holds the command that started go.sh. It was sent at 22:12:08 UTC. Lines 311 and 312 hold no command.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24`: tests of 2026-11-24 for the edit of line 20 of go.sh. The files that end with `.out` hold their output. `go.sh.as-run-2026-11-17` is a copy of go.sh from before the edit. `check_line20.py` reads the local go.sh and puts the old line back in a copy of the text in memory. It does not change the file. That text has the sha256 that `local.sha` lists for go.sh. `check_facts_build.py` runs `build_facts.py` in a copy of this folder. With the edited go.sh the build ends with status 1 and writes no file. With the old line 20 it passes.
