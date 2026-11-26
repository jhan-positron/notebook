# How to read `baselines-and-rules.txt`

## Short version

`baselines-and-rules.txt` is a text file of 183 lines that was written on 2026-11-17 at 22:11:51 UTC, before the start of the whole-chip read rerun: a memory read benchmark with 120 threads on CRB (an Arm reference server), run at a memory speed of 7200 MT/s (million transfers per second).
It fixes which earlier runs at 8000 MT/s (the baselines) the rerun is compared with, and it holds six blocks of rules (V4, V1, V2, V3, F1, F2) for the comparison and for the wording of the result.
The analysis scripts do not parse the rules, and they apply them in hand-written code that names each rule in a comment or in a text.

## What this file is

Explained file: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt`

Short forms of folders in this text:

- `C` = `/home/jhan/workspace/titan/cache-perf/crb`
- `R` = `C/results` (the result folders that were copied back from the test machine)
- `S` = `C/tmp/agent-scratch/w120-7200-2026-11-17` (the run scripts and the analysis scripts of the rerun)

Terms such as baseline, part A, pool or session are defined in the folded list "Words used here" near the end.

- The file was written before the run. It holds no result of the rerun. Every measured rate in it comes from a run before the rerun.
- Size: 183 lines, 23282 bytes.
- Time: line 2 says "Written 2026-11-17T22:11:51Z, BEFORE the run (go.sh not yet started)". The file time is the same second.
- The driver script go.sh started at 22:12:09 UTC by the clock of CRB (the test machine) [Ref14]. That is 18 s after the time in line 2 (est.: the two clocks were not compared) [Ref8].
- Source of the texts (lines 2 and 3): six verified review findings (V4, V1, V2, V3, F1, F2) of the workflow wf_0bc1f5b1-423. The findings are about the design of the rerun. The texts were copied unchanged from the field `best_fix` of each verifier. The file `S/review-w1.json` is the record of that review [Ref12].
- One change against the copied texts (lines 4 to 6): go.sh got a fourth part C process (T72C4, with crev.spec). So where block V2 says "crev (session 2; 1 process)", the reader must read "crev (T72C2 and T72C4; 2 processes)".
- Line 16 states the purpose of the baseline list: "Fixed before the run. Do not add or drop a folder after the 7200 MT/s numbers are seen."

The rules use the two questions of the rerun. The file does not define question 1. The report page defines both [Ref13]:

- Q1: is the whole-chip read rate of the new read kernel still below that of the old read kernel at 7200 MT/s, and by how much.
- Q2: did the rate of either kernel differ from the earlier runs at 8000 MT/s. Line 66 of the rules file calls it "Question 2 (did 8000 -> 7200 MT/s move a rate)".

## Line kinds

The file has a header and six blocks. Each block holds one finding and its fix.

| Block | Lines | Kind |
|---|---|---|
| Header | 1 to 6 | - |
| V4 | 8 to 63 | validity |
| V1 | 65 to 88 | validity |
| V2 | 90 to 121 | validity |
| V3 | 123 to 151 | validity |
| F1 | 153 to 171 | fidelity |
| F2 | 173 to 183 | fidelity |

The file does not define "validity" and "fidelity". By their texts, the four V findings are about what a comparison can prove. The two F findings are about differences between the rerun and the earlier runs.

| Kind of line | How to recognise it | What it holds |
|---|---|---|
| Header comment | Lines 1 to 6, each starts with `#` | Name of the file, time of writing, source of the texts, the one change |
| Block separator | A line of 100 `=` characters (6 lines) | A new block starts |
| Finding line | Starts with `FINDING`, then the id and `(validity)` or `(fidelity)` (6 lines) | The problem that the review found in the design of the rerun |
| Fix separator | A line of 100 `-` characters (6 lines) | The fix starts on the next line |
| Fix text | All lines up to the next block separator | The baseline list, the rules as numbered points, shell commands, optional additions |
| List header | Lines 15 to 19, each starts with `#` | Title of the baseline list, the meaning of `R`, and three general rules for the list |
| Part line | Starts with `PART A`, `PART L` or `PART C` (lines 21, 27, 38) | The part. In brackets: the binaries and the method. Parts A and L give the first 8 characters of the sha256 checksum of each binary. Part C gives the kernel sequences of its two spec files |
| Baseline row | Starts with `A-1`, `A-2`, `A-3`, `L-1`, `L-2`, `L-3` or `L-4` | Id, csv file or files, a remark |
| Exclusion line | Starts with `Not like-for-like:`, `Not a baseline:` or `NOT VALID FOR ANY PART:` (lines 25, 34, 43) | Files and folders that must not be used as a baseline |
| Other line of the list | Lines 29, 33, 35, 36 and 39 to 41 | Line 29: the remark for rows L-2 to L-4. Line 33: the files of the other binary bwx11. Line 35: the 7200 MT/s sample F72d12. Line 36: asmread is used in place of the new read kernel in part L. Lines 39 to 41: which 8000 MT/s data each kernel of part C has |
| Shell command | Lines 47 to 53 | Commands that write converted copies of two csv files |

## Columns: the baseline list (lines 15 to 43, inside block V4)

A baseline row has three fields. Two samples, copied from the file:

Line 22:

```
A-1  R/kernels-20261113T181222Z/threads120.csv  - same process order as ra.sh
```

Line 28:

```
L-1  R/w120-R8-20261117T020549Z/a6456.csv  - identical argument line, load 0.00 at launch
```

| No. | Field | Meaning |
|---|---|---|
| 1 | Id | Name of the baseline row: A-1 to A-3 for part A, L-1 to L-4 for parts L and C |
| 2 | Path | The csv file or files of the row. `R` is the results folder (line 17). Lines 30 and 32 name several files of one folder. Line 24 adds the tags of the processes to use |
| 3 | Remark | After " - ": how the row relates to the 7200 MT/s run. Rows L-2 to L-4 have no remark of their own. Line 29 holds it for all three |

General rules of the list (lines 16, 18 and 19):

- The list is fixed before the run. No folder is added or dropped after the 7200 MT/s numbers are seen.
- Every baseline has 12 memory modules, 8000 MT/s, and the boot of 2026-11-09 (it ended on 2026-11-17 at 03:44 UTC).
- Each baseline is reported as its own row. A pooled range alone is not allowed.

Lines 13 and 15 call the list a new file `baselines.txt`. No file of that name is in `S`. The text of the list is lines 15 to 43 of this file.

### The rows of the list

The column "Name in facts.json" is the dataset name that `build_facts.py` gives the row [Ref9]. The rules file itself names only A-1 to A-3 and L-1 to L-4.
I checked that every csv file of this table exists under `R`.

| Id | Folder under `R` | Files | Binary and kernels | Method | Status in the list | Name in facts.json |
|---|---|---|---|---|---|---|
| A-1 | `kernels-20261113T181222Z` | `threads120.csv` | bw_old and bw_new | 120 threads, 256 MiB, whole-pass stop, 0.5 s, 3 intervals per process (line 21) | Baseline. Same process order as ra.sh | A-1 |
| A-2 | `partA-20261113T205055Z` | `A1.csv` | bw_old read, bw_new read, bw_new asmread and the write kernels. No copy kernels | Same binaries. Other process order. Line 23 calls the arguments the same. Line 166 names two differences: `--cpus 0-63,64-119` (the same 120 CPUs as `0-119` of A-1, written as two ranges) and `--per-thread`. Line 23 says that `--per-thread` only prints after the timing | Baseline | A-2 |
| A-3 | `partA-20261113T205055Z` | `A3.csv`, tags onebuf-ms500-1, -2, -3 | bw_old read only | Same arguments as A-2 | Baseline | A-3 |
| L-1 | `w120-R8-20261117T020549Z` | `a6456.csv` | bwx12 | The argument line of like.spec: 64+56 threads, common stop, 6 s, 2 rounds (line 27). Load 0.00 at launch | Baseline. Identical argument line | L-1 |
| L-2 | `w120-R1-20261115T185140Z` | `p1nop.csv`, `p2add.csv` | bwx12. Only oldread at position 0 and asmread at position 1 | 4 s, other counter events (line 29) | Supporting | L-2 |
| L-3 | `w120-R5-20261115T203152Z` | `thp.csv` | Same as L-2 | Same as L-2 | Supporting | L-3 |
| L-4 | `w120-R6-20261115T203438Z` | `st1.csv`, `st2.csv`, `st3.csv` | Same as L-2 | Same as L-2 | Supporting | L-4 |
| no id | `w120-R0-20261115T165608Z` | `p1.csv`, `p2.csv` | bwx11 (another binary) | 6 s | "Other binary", to be labelled so (line 33) | R0 |
| no id | `w120-R0b-20261115T170342Z` | `cA.csv`, `cB.csv`, `cC.csv` | bwx11 (another binary) | 4 s | "Other binary", to be labelled so (line 33) | R0b |
| no id | `B7-20261113T232859Z`, `B7-20261114T024352Z` | `B7.csv` in each folder [Ref9]. Tags common-6000-common-p1 to p4 | bwx (another binary). Sequence oldread, read, asmread, ... | - | "Nearest data" for kernel `read` of part C, to be labelled "other binary" (line 40) | B7a, B7b. Each holds 8 processes: every tag that starts with common-6000- (see "Where the rules contradict each other") |
| no id | `C3-*` (2 folders: `C3-20261114T022708Z`, `C3-20261114T054116Z`) | `C3.csv` in each folder [Ref9] | bwx (another binary) | - | "Nearest data" for kernel `read` of part C, to be labelled "other binary" (line 40) | C3a, C3b. Each holds 4 processes: every tag that starts with common-6000-. Line 40 names no tag for these folders |
| no id | `B5-*` (2 folders: `B5-20261114T011723Z`, `B5-20261114T043213Z`) | `B5.csv` in each folder [Ref9]. Tags b5-fwd-* | bwx (another binary) | - | "Nearest data" for kernel `read` of part C, to be labelled "other binary" (line 40) | B5a, B5b. The same two folders also hold processes with the tags b5-rev-*. Line 40 does not name them. They are the datasets B5a-rev and B5b-rev [Ref9] |
| no id | `w120-w120-F72d12-20261117T200231Z` | `a6456.csv` | bwx12 | The argument line of part L, at 7200 MT/s, in the boot of the rerun | "7200 MT/s sample, not a baseline". To be shown beside T72L1 to T72L3 (line 35) | F72d12 |

How many intervals of each baseline row the report page uses [Ref10]:

| Row | Old read kernel | Load-only loop |
|---|---|---|
| A-1 | 6 intervals of bw_old read (2 processes) | 6 intervals of bw_new read (2 processes) |
| A-2 | 6 intervals of bw_old read (2 processes) | 6 intervals of bw_new read (2 processes) |
| A-3 | 9 intervals of bw_old read (3 processes) | none |
| L-1 | 2 intervals of oldread at position 0 (1 process) | 2 intervals of asmread at position 1 |
| L-2 | 4 intervals (2 processes) | 4 intervals |
| L-3 | 2 intervals (1 process) | 2 intervals |
| L-4 | 3 intervals (3 processes) | 3 intervals |

- Rows A-1 to A-3 together are the "pool A-1 to A-3" of the report: 21 intervals from 7 processes.
- Rows L-1 to L-4 together are the "pool L-1 to L-4" of the report: 11 intervals from 7 processes per kernel.

### What the list excludes

| Line | Label in the file | Excluded | Reason given in the file |
|---|---|---|---|
| 25 | Not like-for-like (part A) | `A2.csv` | 6 s and 15 s |
| 25 | Not like-for-like (part A) | `A3.csv`, tags twobuf-* | `--kernel all` |
| 25 | Not like-for-like (part A) | `A3.csv`, tags onebuf-ms6000-* | 6 s |
| 25 | Not like-for-like (part A) | `A4.csv` | 6 s, 2 intervals, other layouts |
| 25 | Not like-for-like (part A) | `B7-*` and `C3-*` tags pass-500-*, and `SHORT-20261113T214338Z` | Binary bwx |
| 34 | Not a baseline (part L) | `w120-X1d10-*`, `w120-X1d10b-*`, `w120-BASEd10-*` | 10 memory modules |
| 34 | Not a baseline (part L) | `w120-X2d12-*` | Firmware test: TXREQ Max 1/4 and TXREQ Min 1/4 |
| 34 | Not a baseline (part L) | `w120-R5-*/nothp.csv` | 4 KiB pages |
| 34 | Not a baseline (part L) | `w120-RC*-*` | Root counter runs of 115 s or more |
| 34 | Not a baseline (part L) | Folders ending in g, `w120-R3-*`, `w120-R4-*`, `w120-R7-*` | Two processes at once, or a latency probe |
| 43 | Not valid for any part | Every run of the boots from 2026-10-22 to 2026-11-07, for example `R/sudo-20261102T*`, `R/followup*`, `R/20261030T193108Z` | 10 memory modules |

### The shell commands of block V4 (lines 47 to 53)

- Line 45 gives the purpose: the commands make rows A-2 and A-3 readable by `stat_k120.py` (a statistics tool for the csv files of part A), without a change to that script or to a result file.
- The commands write copies of `A1.csv` and `A3.csv` with converted header lines. Line 45 says that only the header lines change.
- The copy of `A3.csv` is not the whole file. The `awk` command of line 51 keeps only the three processes with the tags onebuf-ms500-1, onebuf-ms500-2 and onebuf-ms500-3. `A3.csv` holds 12 processes in 8772 lines, and the copy holds 3 processes in 1101 lines (my count).
- The copy of `A1.csv` has the same number of lines as `A1.csv`: 4404 (my count).
- The `sed` commands of lines 50 and 51 rewrite the header line of each process into the header form of a `threads120.csv` file of part A. Example: line 1463 of `A3.csv` is `-- step A3 tag onebuf-ms500-2 binary bw_old waited_s 0 loadavg 114.44 90.41 44.47 2/1074 logins 0 utc 20:58:28 args --threads 120 --cpus 0-63,64-119 --bytes 256M --per-thread --kernel read --reps 3 --min-ms 500`. Line 368 of the copy is `-- binary bw_old kernel read threads 120 cpus 0-63,64-119 bytes 256M round 2 load 114.44 utc 20:58:28`.
- The new header keeps only the first of the three load values. That is the 1-minute load average.
- The field `round` of the new header comes from the tag. In the copy of `A1.csv` it is the 1 or 2 after `-r` at the end of the tag. In the copy of `A3.csv` it is the number at the end of the tag (1, 2 or 3). So in the copy of `A3.csv` the field `round` counts the three repeats of the process. It is not a round of a script.
- The copies are `S/base8000/partA-A1/threads120.csv` and `S/base8000/partA-A3-onebuf500/threads120.csv`.
- Lines 52 and 53 give the expected counts: 12 and 3 lines that start with `-- binary`, and 0 lines that start with `-- step`. I counted the same values in the two copies.
- `build_facts.py` reads the raw `A1.csv` and `A3.csv` for its records. It uses the two copies only to cross-check its values with `stat_k120.py` [Ref9].

## The rules

### Each rule in short

| Rule | Lines | Problem that the review found | The rule |
|---|---|---|---|
| V4 | 9 to 63 | The design named no fixed list of baseline folders | Compare the rerun only with the 8000 MT/s runs of the fixed list, and show each of them as its own row. For the new read kernel in part A, show the result against A-1 and against A-2. Their two medians differ by 5.1 % (289.54 and 304.43 GB/s). A smaller difference between 7200 MT/s and 8000 MT/s must be reported as "no difference shown" |
| V1 | 66 to 88 | The design had no decision rule for Q2. At 8000 MT/s the new read kernel already varies by 4 % to 13 % between processes, visits and boots | Per part and kernel, compare the lowest-to-highest range of the 7200 MT/s intervals with that of the 8000 MT/s intervals. No overlap is worded "differs between the 8000 MT/s boot and the 7200 MT/s boot". Overlap is worded "no difference seen". Each speed has one boot. So never give a percent change of the new read kernel as an effect of the memory speed |
| V2 | 91 to 121 | The order of the kernels changes the rate of the new read kernel by about 3 % at 8000 MT/s, and part C mixes two orders | In part C, group the intervals by the kernel that ran directly before, not by spec file. Never pool `read` or asmread over both kernel orders |
| V3 | 124 to 151 | Part A cannot decide Q2 for the new read kernel. The 0.5 s whole-pass stop and the round both change its rate by more than any speed effect seen before | In part A, show the load-only kernels as one row per process with the pass counts. Compare only session 1 with the 8000 MT/s processes of the same round, with the wording "inside" or "outside" and no percent. Take the percent drop and the Q2 verdict of the load-only loop from parts L and C |
| F1 | 154 to 171 | The machine state before the first 120-thread process of part A differs from the run of 2026-11-13, and it differs between the three sessions | Show part A as one row per session and round, with the start state of the session in the row label. Word a 7200 MT/s value inside the 8000 MT/s reference range as "inside the range of the 8000 MT/s runs; no difference shown". State that the one-thread phase of 2026-11-13 was not repeated |
| F2 | 174 to 183 | Part C runs the bwx12 kernel `read`, and no earlier bwx12 result at 8000 MT/s holds this kernel | The 8000 MT/s cell of `read` must say "no bwx12 run". Compare the new read kernel between the two speeds in part A only, and bwx12 between the two speeds in part L only |

### The points of each rule, and the code that applies them

Rule V1 (the "Rule for 7200 MT/s against 8000 MT/s", lines 70 to 82):

| Point | What it asks | Code that applies it |
|---|---|---|
| 1 | One process is one sample. State n as intervals / processes / sessions / boots. Label the 7200 MT/s range as three sessions of one boot | Function `nns` of `facts_text.py` [Ref3]. The label text in `facts_text4.py`, which takes the time span from the go.sh log [Ref5] |
| 2 | Compare the two ranges. Give the fixed wording. On overlap, give the width of the 8000 MT/s range as the size that the test cannot exclude | Function `compare` of `facts_text.py`, with `overlap`, `gap` and `width_pct` of `facts_data.py` [Ref4]. Function `cmps` of `facts_text4.py` writes the table with the wording [Ref5]. `make_report.py` repeats the test for the page [Ref10] |
| 3 | No percent change of the new read kernel as an effect of the memory speed. Write the "Insufficient data" sentence that the rule gives | `facts_text4.py` writes the sentence as "Text required by rule V1 point 3" [Ref7] |
| 4 | Old read kernel: a difference above about 1 % may be reported as a difference between the two boots | `facts_text4.py` [Ref7]. It adds that the rule does not say which distance counts |
| 5 | Do not use 280 to 310 GB/s as the 8000 MT/s range of the new read kernel | `facts_text4.py` states the highest 8000 MT/s values under "Rule V1 point 5" [Ref7] |

Rule V2 (lines 95 to 115):

| Point | What it asks | Code that applies it |
|---|---|---|
| 1 | Six groups: `read` after oldread, `read` after asmread, asmread after `read`, asmread as first interval, asmread after oldread, and oldread (all intervals may be pooled) | Function `cgroup` of `facts_text.py` builds the five load-only groups from the field `kernel_before`. A table of the six groups follows [Ref6] |
| 2 | Never run `stat_bwx.py --pool` over the three T72C folders for `read` or asmread | This point is an instruction for the person who runs `stat_bwx.py`. `build_facts.py` does not run the command. It calls the function `interval_rows` of `stat_bwx.py` once per folder, and this function has no pool option [Ref9] |
| 3 | Give the drop of `read` against oldread for both `read` groups, inside the same process and round | Function `pairs` and the Q1 table of `facts_text.py` [Ref6] |
| 4 | Compare each group with the 8000 MT/s value of the same position from the runner bwx (folders B7 and C3, tags common-6000-*). For asmread after oldread, use the part L baseline. State that the bwx runs used another binary | `facts_text4.py`, section 4.5 of the facts sheet [Ref7]. On the report page: one note under Table 2 [Ref10] |
| 5 | State that part L and the forward order measure the lower of the two conditions, and that order and session cannot be separated | `facts_text.py` and `facts_text4.py` [Ref6] [Ref7] |

Rule V3 (lines 126 to 151):

| Point | What it asks | Code that applies it |
|---|---|---|
| 2 | `stat_k120.py` must show the pass count (four replacements, lines 130 to 141) | `stat_k120.py` holds the four new lines [Ref11] |
| 3, one row per process | bw_new read and asmread: one row per process with pass counts. No pooled range over rounds or sessions | The part A table of `facts_text.py`: one row is one process, a cell shows the rate and the pass count [Ref8] |
| 3, session 1 only | Compare session 1 round 1 with the two round-1 baselines, and session 1 round 2 with the two round-2 baselines. Sessions 2 and 3 are for Q1 only | `facts_text.py` builds the cells. `facts_text4.py` writes section 4.3. Its table has 6 rows: bw_new read, bw_new asmread and bw_old asmread, each in rounds 1 and 2. The code holds the wordings "outside (above)", "outside (below)" and "inside ...", and a count for a row whose 3 intervals do not all lie in the same place. All 6 rows got "outside (above)". The script stops unless the 3 intervals of every row lie above the range [Ref6] [Ref7]. `make_report.py` makes the same comparison for the two bw_new read rows of the page. It also stops when session 1 is not above the range [Ref10] |
| 3, no statement | No statement from the write, copy and asm write or copy rows of part A | `facts_text4.py`, section 5: "No statement is made from these rows (rule V3)" [Ref7] |

The table of rule V3 leaves out these parts of the rule:

- Point 1 (line 126): no change to ra.sh, go.sh and the spec files. No analysis code is needed for it.
- Point 3, line 145: the 8000 MT/s baseline of bw_new read is four processes, with a range for each. The table of section 4.3 of the facts sheet holds one row per round for bw_new read. Each row shows the three intervals of the A-1 process and the three intervals of the A-2 process of that round in two cells of their own [Ref7].
- Point 3, line 148: part A may give the Q2 verdict for the old read kernel. `facts_text.py` compares bw_old read of part A with rows A-1 to A-3 [Ref2].
- Point 3, line 149: the Q2 verdict and the percent drop of the load-only loop come from parts L and C, and their limit must be stated. The function `short_version` of `facts_text.py` writes the three sentences of the Short version of the facts sheet. It takes the percent drop of the first sentence from part C. Its Q2 sentence of the load-only loop names part L, control I, part C and F72d12. It does not name part A [Ref6].
- Point 3, line 150: describe two effects: (a) the whole-pass stop, and (b) the higher rates of round 2. `facts_text4.py` names "rule V3, effect a" in section 4.3 [Ref7]. No script names effect (b). I searched `facts_text.py`, `facts_text4.py` and `make_report.py` for "effect b" and "effect (b)". `facts_text4.py` states the fact of effect (b) for the rerun without this name. It counts the cells of part A in which the second-round process of a load-only kernel lies above the first-round process. Section 6 of the facts sheet gives this count under "Established", and the hypothesis H1 (not tested) of the same section uses it [Ref7].

Rule V4 (lines 11 to 63):

| Point | What it asks | Code that applies it |
|---|---|---|
| 1 | The fixed list | The folder names are typed into `build_facts.py`. Each record gets a dataset name and a role [Ref9]. `facts_text.py` and `make_report.py` select the pools by these names [Ref2] [Ref10] |
| 1, part L | "In part L, asmread stands in for the new read kernel (same loop: 8 ldp q per 256 B). Say so in the row label." (line 36). "Stands in for" means "is used in place of" | Constant `STANDIN` of `facts_text.py` [Ref2] |
| 2 | Converted copies of `A1.csv` and `A3.csv` | The copies exist under `S/base8000`. `build_facts.py` uses them for a cross-check [Ref9] |
| 3 | New read kernel of part A against A-1 and A-2 as two rows | `facts_text4.py` writes one sentence that starts with "Rule V4 point 3 for bw_new read". It gives the two 8000 MT/s medians (A-1 and A-2), the median of session 1, and the distance of that median to each. The table of section 4.3 shows A-1 and A-2 in two columns, not in two rows. The script stops unless both distances are larger than the distance between the two 8000 MT/s medians [Ref7] |

Rule F1 (lines 160 to 171):

| Point | What it asks | Code that applies it |
|---|---|---|
| 1 | One row per session and per round for bw_old read and bw_new read | The part A table of `facts_text.py` [Ref8] |
| 2 | Row labels with the start state: session 1 from an idle machine, sessions 2 and 3 "started N s after a 120-thread bwx12 process" | `build_facts.py` computes the gap N and the start-state text of every step [Ref9]. `facts_text.py` puts it into the column "Start state of the session" [Ref8] |
| 3 | The 8000 MT/s reference is both runs of 2026-11-13 (rows A-1 and A-2) | `facts_text.py` selects bw_old read of A-1 and A-2 for the text of point 5 [Ref8] |
| 4 | Inside the reference range: "inside the range of the 8000 MT/s runs; no difference shown" | The code of section 4.3 in `facts_text4.py` holds these words for a row whose 3 intervals of session 1 all lie inside the 8000 MT/s range of the same round [Ref7]. No row of the rerun got them. All 6 rows of the table of section 4.3 say "outside (above)", and my search of `FACTS.md` for "no difference shown" found no line. For bw_old read of part A the facts sheet and the report page use the wording of rule V1 point 2, "no difference seen" [Ref2] [Ref13] |
| 5 | Text about the one-thread phase that was not repeated | `facts_text.py` writes it as "Text required by rule F1 point 5" [Ref8] |

Rule F2 (lines 179 to 183):

| Point | What it asks | Code that applies it |
|---|---|---|
| 1 | New read kernel, 7200 against 8000 MT/s: part A only | `facts_text4.py`, section 4.5: the like-for-like baseline of the new read kernel is part A [Ref7] |
| 2 | bwx12, 7200 against 8000 MT/s: part L only | Not followed in full. See the next section |
| 3 | Part C at 7200 MT/s only. The 8000 MT/s cell of `read` says "no bwx12 run". A fixed sentence must be added | `facts_text4.py` writes the sentence as "Text required by rule F2 point 3" [Ref7]. Table 2 of the report page holds the cell "no bwx12 run" [Ref10]. The constant `NO_READ` of `facts_text.py` holds another text: the "Insufficient data" sentence that rule V4 gives for `read` in line 40 [Ref2] |
| 4 | Optional: a reference from the runner bwx (folders B5) | `facts_text4.py` quotes the range under "Rule F2 point 4" [Ref7] |
| 5 | Do not write that `read` was part of the 2026-11-15 data | A wording rule. No script names point 5 of rule F2. I searched the 8 Python scripts of `S` for "point 5" |

### Where the rules contradict each other

The facts sheet records three contradictions and the choice that was made for each [Ref8]. The report page repeats two of them in notes under its Table 2 [Ref10].

| Topic | One text | The other text | Choice |
|---|---|---|---|
| Row X2d12 (`w120-X2d12-20261117T040922Z`) | V4 lists it as "Not a baseline" (line 34) | V2 point 4 (line 112) and F2 point 2 (line 180) name it as a baseline of part L | V4 is followed. The row is shown and not used (decision (m) of the facts sheet) |
| Rows of the runner bwx for part C | V4 names the tags common-6000-common-p1 to p4 of the two B7 folders (line 40) | V2 point 4 names the tags common-6000-* of the B7 and C3 folders, 24 processes (line 107) | V2 point 4 is followed (decision (p)) |
| Part C against 8000 MT/s | F2 points 2 and 3 use part L only and show part C at 7200 MT/s only (lines 180 and 181) | V1 point 2 (line 72), V2 point 4 (lines 107 to 112) and the part C list of V4 (line 39) ask for a comparison | V1, V2 and V4 are followed for two rows of part C: oldread, and asmread directly after oldread (decision (r)). The choice was made after the numbers were seen |

The facts sheet lists 10 decisions, (i) to (r), that were made after the numbers were seen [Ref8]. Decisions (m), (p) and (r) are the three choices of the table above. Two more of the 10 decisions set the 8000 MT/s side of a comparison:

- The 8000 MT/s range for parts L and C is the pool of rows L-1 to L-4 (decision (k) of the facts sheet). The facts sheet shows the result against row L-1 alone beside it [Ref8].
- From every earlier row of bwx12 and bwx11 only oldread at position 0 and asmread at position 1 are used (decision (l)). These are the positions of part L [Ref8]. Rule F2 point 2 also lists the three other test loops of the part L line for the comparison: read_nop96, read_nop256 and read_1pl (line 180). Section 4.8 of the facts sheet shows their rates of part L beside those of row L-1 as a record only. It makes no statement from them [Ref7].

### Numbers inside the rule texts

- The ranges that the rule texts quote were computed by the reviewers before the run.
- Rule V1 says that a range must be replaced when the list of V4 names other processes (line 68).
- Example: rule V1 point 2 quotes "bwx12 465.5-470.1 GB/s, 20 intervals, 13 processes" for the old read kernel (line 75). The report uses the pool L-1 to L-4: 465.53 to 470.05 GB/s, 11 intervals from 7 processes [Ref13].
- Second example: for the old read kernel of part A, rule V1 point 2 (line 75), rule V3 (line 148) and rule F1 point 3 (line 167) quote one range from 12 intervals. Line 167 gives it as 464.42 to 467.06 GB/s. Lines 165 and 166 name the csv files of rows A-1 and A-2 as its source. The report uses the pool A-1 to A-3 of the list: 463.58 to 469.03 GB/s, 21 intervals from 7 processes [Ref13].
- The interval counts in rule V2 point 1 were written for three part C processes. Lines 97, 99 and 100 give 2, 1 and 1 intervals for the reverse order (crev), and line 101 gives 6 oldread intervals. With the fourth process T72C4 the rerun has 4, 2 and 2 intervals for the reverse order, and 8 oldread intervals [Ref10]. Lines 4 to 6 of the file state this change.
- Insufficient data: which 13 processes rule V1 counted for line 75. The script of the verifier who wrote that range would resolve it. I did not find the list of the 13 processes in the record of the review, `S/review-w1.json`.

### Optional additions in the file, and what was done

| Where | Optional addition | Done? |
|---|---|---|
| V4, lines 62 and 63 | A comment line in go.sh that names the fixed list | Yes. go.sh holds this comment line, with the file name `baselines-and-rules.txt` [Ref15] |
| V1, line 84 | List F72d12 as a separate, earlier visit of the 7200 MT/s boot. Do not pool it | Yes. The report shows F72d12 as its own row with the remark "Not pooled with part L" [Ref13] |
| V1, lines 86 to 88 | A wait of 1 h between sessions ("Not recommended as a requirement") | No. go.sh holds no sleep command [Ref15] |
| V2, lines 117 to 119 | A fourth part C process (T72C4, crev.spec) | Yes. go.sh runs it after the three sessions [Ref15]. Lines 4 to 6 of the rules file record it |
| V2, line 121 | One spec file with both kernel orders in every process | No. go.sh runs cfwd.spec and crev.spec [Ref15] |
| F1, line 156 | The one-thread phase of 2026-11-13 ("Do not add") | Not added. The report states that the rerun did not repeat it [Ref13] |

## Old read kernel and new read kernel in this file

| Kernel | Names in this file | Baseline rows that hold it |
|---|---|---|
| Old read kernel | "old read kernel", "old read", "old kernel", "bw_old read", "oldread" | A-1, A-2, A-3 (`read` of bw_old). L-1 to L-4 (`oldread` of bwx12 at position 0) |
| New read kernel | "new read kernel", "new read", "new kernel", "new C read kernel", "bw_new read", and `read` for bwx12 and bwx | A-1 and A-2 only (`read` of bw_new). Line 41 says: "The like-for-like 8000 MT/s baseline of the new read kernel is PART A (bw_new read), not part C." |
| asmread, in place of the new read kernel | "asmread" | L-1 to L-4 (`asmread` of bwx12 at position 1) |

- The bwx12 kernel `read` has no run at 8000 MT/s (line 40). The file names runs of the older binary bwx as the nearest data.
- Line 36 gives the reason why asmread is used in place of the new read kernel in part L. By that line it is the same loop, with 8 "ldp q" loads per 256 B.
- "Load-only kernels" (line 143) and "load-only loop" (line 149) mean the new read kernel and asmread together. Line 144 names both: "kernels bw_new read and asmread".

## Which code reads this file

- `facts_text.py` opens the file [Ref1]. It takes the time from line 2. It stops the build of the facts sheet unless four things hold:
  - The time in line 2 is before the start of go.sh.
  - The file time equals the time in line 2.
  - Line 2 holds the text "BEFORE the run (go.sh not yet started)".
  - The file `S/local.sha` (the sha256 list of go.sh, ra.sh and the three spec files) is newer than this file. Its file time is 12 s later.
- What the fourth check shows:
  - One command wrote `local.sha` on the agent server (the Linux server that holds `S` and sent the commands to CRB) and then copied go.sh, ra.sh, the three spec files and `local.sha` to CRB. A later command started go.sh on CRB. The record of the Claude Code session of 2026-11-17 (the agent session that sent these commands) holds both commands [Ref16].
  - The file times of the rules file and of `local.sha` are both on the clock of the agent server.
  - So the rules file got its present content before the run files were copied to CRB. This order does not use the clock of CRB.
- No script of the analysis chain takes a value from the baseline list or from the rule texts. A search of the 8 Python scripts and the 3 shell scripts at the top level of `S` for the file name found it in go.sh, `build_facts.py`, `facts_text.py` and `make_report.py` only. go.sh holds the name in a comment. `build_facts.py` holds it in a comment and in the text that it writes into the field `meta.rules` of `facts.json`. The folder names are typed into `build_facts.py` [Ref9]. The rules are hand-written code and text in `facts_text.py`, `facts_text4.py` and `make_report.py`.
- The file is cited, not read, by: a comment in go.sh [Ref15], the field `meta.rules` of `facts.json`, the file list of `FACTS.md`, and entry Ref26 of the reference list of the report page [Ref13].
- `make_report.py` does not read the file. It stops when the file does not exist, as it does for every path of its reference list [Ref10].

How the final wording of a comparison comes from the rules [Ref4]:

```
7200 MT/s intervals --> range a (lowest, highest)
8000 MT/s intervals --> range b (lowest, highest)
a and b overlap?  yes --> "no difference seen"
                  no  --> "differs between the 8000 MT/s boot
                           and the 7200 MT/s boot"
```

- Overlap means: lowest of a <= highest of b, and lowest of b <= highest of a.
- The distance that the tables print is 0 on overlap. Otherwise it is the gap between the nearest ends of the two ranges, in GB/s (1 GB = 1e9 bytes). It is positive when the 7200 MT/s range is the higher one.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **go.sh**: the driver script of the rerun.
- **ra.sh**: the script that runs part A.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Spec file, like.spec, cfwd.spec, crev.spec**: a spec file is a text file with the argument line of one bwx12 process. like.spec holds the line of part L. cfwd.spec and crev.spec hold the two lines of part C.
- **T72A1 to T72C4**: the names (tags) of the result folders of the rerun: T72, then the letter of the part, then a number.
- **F72d12**: one process of the part L line that ran at 20:02 UTC on 2026-11-17, in the same boot as the rerun and before it.
- **Baseline**: an earlier run at 8000 MT/s that a 7200 MT/s result is compared with.
- **Like-for-like**: by its use in this file, an earlier run that used the same binary and the same method as a part of the rerun. Under the label "Not like-for-like", line 25 excludes runs with another interval length, with `--kernel all`, with "other layouts" or with another binary. The argument line may differ in small points: row A-2 is a baseline, and line 166 names two options in which its arguments differ.
- **Supporting row**: rows L-2 to L-4. They used bwx12 with 4 s intervals and other counted hardware events. Only oldread at position 0 and asmread at position 1 are taken from them.
- **Pool**: the intervals of several rows taken together as one range.
- **Range**: the lowest and the highest value of a list of intervals.
- **n**: the number of measurements that a range comes from, written as intervals / processes / sessions / boots.
- **Boot**: one run of the machine from a start to the next restart.
- **Visit**: one time at which the same argument line was run.
- **Memory module**: one DIMM. CRB has 12 slots.
- **Load average, load at launch**: the load average is the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes. "Load at launch" is the 1-minute value read directly before a process starts.
- **X2d12**: one process of the part L line at 8000 MT/s with 12 modules, in another boot of 2026-11-17. Its result folder is `w120-X2d12-20261117T040922Z`.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Pass count**: the number of buffer passes that all 120 threads completed in one interval of part A. It is the column total_bytes divided by the column bytes_per_thread of the csv row. So it is the sum over the threads. Example: 600 passes are 5 passes per thread on average.
- **One-thread phase**: the part of the test of 2026-11-13 that ran one-thread processes before its 120-thread part.
- **Tag**: the name of one process inside a csv file or a folder name, for example onebuf-ms500-1 or common-6000-common-p1.
- **sha256**: a checksum of a file. Two files with the same sha256 value have the same content. This file prints the first 8 characters.
- **TXREQ**: a group of firmware settings that were changed for another investigation.
- **stat_k120.py, stat_bwx.py**: two statistics tools. stat_k120.py reads a csv file of part A. stat_bwx.py reads the csv files of bwx12.
- **Facts sheet**: the file FACTS.md with its data file facts.json. The script build_facts.py built it from the raw result files, with facts_data.py, facts_text.py and facts_text4.py.
- **Report page**: `C/new-test-kernel/whole-chip-rerun-7200.html`, written by make_report.py.
- **est.**: estimated, not measured directly.

</details>

## References

- [Ref1] `S/facts_text.py`, lines 353 and 380 to 388: the script opens the rules file, takes the time from its line 2, and checks the four conditions.
- [Ref2] `S/facts_text.py`, lines 18 to 33: the names of the baseline rows (`BW12`, `BW11`, `BWX`), the two fixed wordings (`DIFFERS`, `SAME`), `NO_READ`, `STANDIN` and `F2_NOTE`. Lines 413 to 425: the pools and the calls of `compare`.
- [Ref3] `S/facts_text.py`, lines 124 to 129: function `nns` (n as intervals / processes / sessions / boots, rule V1 point 1).
- [Ref4] `S/facts_text.py`, lines 333 to 336: function `compare`. `S/facts_data.py`, lines 471 to 485: functions `overlap`, `gap` and `width_pct`.
- [Ref5] `S/facts_text4.py`, lines 71 to 90 (function `cmps`: the table with the column "Wording by rule V1 point 2") and lines 132 to 160 (the rules in short, and the label of rule V1 point 1).
- [Ref6] `S/facts_text.py`, lines 304 to 316 (function `pairs`), 399 to 411 (function `cgroup`, rule V2), 427 to 439 (part A session 1 against the same round, rule V3), 477 to 505 (function `short_version`: the three sentences of the Short version of the facts sheet), 1375 to 1393 (table of the groups, rule V2 point 5), 1403 to 1430 (Q1 table, one row per group).
- [Ref7] `S/facts_text4.py`: lines 497 to 499 (rule V1 point 4), 714 to 770 (section 4.3: rule V3, rule V4 point 3, the wording of rule F1 point 4), 936 to 943 (rule F2 points 1 and 3), 966 to 971 and 1026 to 1030 (rule V2 points 4 and 5), 1115 to 1118 (rule V1 point 5), 1132 to 1137 (rule F2 point 4), 1196 to 1204 (rule V1 points 3 and 4), 1286 to 1298 (section 4.8: the three other test loops of the part L line, record only), 1436 to 1440 (section 5, rule V3), 1462 to 1468 and 1494 to 1495 (section 6: the count of the part A cells in which round 2 lies above round 1), 1566 to 1569 (hypothesis H1).
- [Ref8] `S/facts_text.py`, lines 1130 to 1138 (text of rule F1 point 5), 1159 to 1244 (the decisions (a) to (r) of the facts sheet, with the time of the rules file in decision (h)), 1252 to 1274 (part A table: one row per process, with the start state, rule F1 points 1 and 2).
- [Ref9] `S/build_facts.py`, lines 88 to 116 (gap and start state of every step), 182 to 204 (rows A-1 to A-3), 207 to 221 (rows of bwx12 and bwx11 with their folders and files), 258 to 267 (rows of the runner bwx), 798 to 834 (cross-checks with `stat_k120.py` and `stat_bwx.py`).
- [Ref10] `S/make_report.py`, lines 268 to 304 (the pools and the expected numbers of intervals and processes), 285 to 289 (the part C groups), 481 to 482 (function `wording`), 508 to 517 (rule V3), 815 to 818 and 1391 (function `addref` stops when a reference path does not exist, and the entry of the rules file), 2108 to 2112 (the cell "no bwx12 run"), 2136 to 2145 (the notes on the pool, on part C and on X2d12), 2146 to 2164 (the note on the rows of the runner bwx).
- [Ref11] `S/stat_k120.py`, lines 41, 55, 60 and 84: the four lines that rule V3 point 2 asks for.
- [Ref12] `S/review-w1.json`: the record of the review. It holds the field `best_fix` and the text of rule V1. `S/facts_text.py`, line 167, names it as the record of the review that produced the rules.
- [Ref13] `C/new-test-kernel/whole-chip-rerun-7200.html`: the report page. Table 2 (line 1119) holds the pools, the rows of F72d12, and the notes on the contradictions. Table 5 (line 1135) holds the fact about the one-thread phase. Entry Ref26 of its reference list (line 1143) cites the rules file.
- [Ref14] `S/facts.json`, field `meta.rerun.go_start`: "2026-11-17T22:12:09Z".
- [Ref15] `S/go.sh`, line 8 (the comment that names the rules file) and lines 40 to 46 (three sessions with like.spec and cfwd.spec or crev.spec, then T72C4 with crev.spec). A search of the whole file for "sleep" finds nothing.
- [Ref16] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`, line 309 (the command that wrote `local.sha` and copied the run files to CRB) and line 313 (the command that started go.sh): the record of the Claude Code session of 2026-11-17. This record lies outside the project folder.
