# facts.json: what the file holds

## Short version

`facts.json` is the data file of the facts sheet (the file `FACTS.md` of the same folder) for the whole-chip read rerun of 2026-11-17: a memory read benchmark with 120 threads on CRB (an Arm reference server), run at a memory speed of 7200 MT/s (million transfers per second).
Its list `intervals` holds 793 records, one per timed measurement, for the rerun and for the other runs that the rerun is compared with.
The field `GBps` of a record is the final rate of that measurement over all 120 threads, and the two other parts, `meta` and `verdicts`, hold the run record and the written results.

## What this file is

- **Explained file:** `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts.json`.
- **Written by:** the function `write_json` of the script `build_facts.py` [Ref1].
- **Step of the run:** analysis, after the benchmark runs. The script reads the result files that were copied back from CRB.
- **One record per what:** one record of `intervals` is one interval, which is one timed measurement inside one process of a benchmark binary.
- **Folders:** `R` = `/home/jhan/workspace/titan/cache-perf/crb/results` (result folders). `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17` (this folder). `meta.R` and `meta.S` hold these two full paths. Every other path in the file starts with `R/` or `S/`.
- **Units:** GB = 1e9 bytes. All times are UTC.
- **Rounding:** no floating-point number in the file has more than 3 decimals. `write_json` rounds every floating-point number of `verdicts` and of the interval records to 3 decimals when it writes the file. It writes `meta` without this step. The rates and the interval times inside `meta.hardware_error_records` are rounded to 3 decimals where that object is built [Ref1].
- **Safe write:** the script writes `facts.json.tmp` first and then renames it. So a reader never sees a part of the file [Ref1].
- **Self-description:** the file explains a part of itself. `meta.units` holds 6 notes on units, `meta.rate_kinds` holds 2 notes on the kinds of rate, and `meta.fields` holds 15 notes on fields. At least two of these notes are less exact than the field table below. The note `meta.units.min_ms` reads "shortest length of one interval". That holds for the part A form only (field 34). The note `meta.units.gap_s` names the previous process "of the rerun". For the step T72I2 the previous process is T72I1, a process of control I (field 39).
- **Size:** 3254 lines, 860769 bytes.

How the file is made and used (top to bottom):

```
raw files under R (csv files, logs, env.txt, probe.txt)
  |
  v
build_facts.py: collect()      reads them through facts_data.py
build_facts.py: run_checks()   27 integrity checks
facts_text.py:  render()       text of FACTS.md, object "verdicts"
  |
  +--> facts.json   written by write_json(): 793 interval records
  +--> FACTS.md     written by main() from the same records
         |
         v
make_report.py reads both and writes whole-chip-rerun-7200.html
```

The order of these steps is the order of the function `main` [Ref2].

## Line kinds

The file is one JSON object. The script writes every interval record on one line. So `grep` and `sed -n` work on single records.

| Lines | How to recognise it | What it holds |
|---|---|---|
| 1 | `{` | start of the JSON object |
| 2 | `"meta": {` | start of `meta` |
| 3 to 1233 | indented, 1 space per level | body of `meta`, one key or value per line |
| 1234 | `},` | end of `meta` |
| 1235 | `"verdicts": {` | start of `verdicts` |
| 1236 to 2457 | indented, 1 space per level | body of `verdicts` |
| 2458 | `},` | end of `verdicts` |
| 2459 | `"intervals": [` | start of the list of records |
| 2460 to 3252 | starts with `{"dataset":` | 793 interval records, one record per line, no spaces between the fields |
| 3253 | `]` | end of the list |
| 3254 | `}` | end of the JSON object |

Example: `sed -n '2706p' facts.json` prints the record of line 2706.

## Top-level keys

| Key | Type | Size | What it holds |
|---|---|---|---|
| `meta` | object | 16 keys | the run record: folders, units, machine state of the rerun, the 10 steps of the rerun and the 2 steps of control I, 27 integrity checks, record counts, notes on hardware error records (messages of the firmware in the Linux kernel log) and on firmware settings |
| `verdicts` | object | 13 keys | the written results: the answer to Q1 (old against new at 7200 MT/s) and to Q2 (7200 MT/s against 8000 MT/s), with the numbers that each answer quotes |
| `intervals` | list | 793 records | one record per timed interval. Every record has the same 40 fields |

## Columns

### The 40 fields of one record of `intervals`

Every record has all 40 keys, in the same order. A field that does not apply holds `null` [Ref3].

Two forms of record exist:

- **Part A form** (333 records): binaries `bw_old` and `bw_new`. The function `add_k120` builds it from one interval row of a csv file of the benchmark `bandwidth.c` [Ref4] [Ref7].
- **bwx form** (460 records): runner binaries `bwx12`, `bwx11` and `bwx`. The function `add_bwx` builds it from the 120 thread rows (T rows) of one interval of a bwx csv file [Ref5] [Ref8].

| No. | Field | Unit or type | Meaning |
|---|---|---|---|
| 1 | `dataset` | text | Label of the group of runs that the record belongs to. `rerun-A`, `rerun-L`, `rerun-C` are the three parts of the rerun. `control-I` is the control that was added later. Every other value is an earlier run. The table "Datasets" below lists all 26 values. |
| 2 | `part` | text | `A`, `L`, `C` or `I`. For the rerun it is the part. For an earlier run the script sets a fixed letter: `A` for A-1 to A-3, `L` for the 11 datasets whose folders were written by the run scripts `rx.sh` or `r0.sh`, `C` for the 8 datasets of runner `bwx` [Ref6]. So `part` alone does not select the rerun. Use `dataset`. |
| 3 | `role` | text | What the record is used for: `rerun`, a control, a baseline, a supporting row, a row of another binary, `not a baseline`, `10 modules`, or the earlier 7200 MT/s sample of the same boot (F72d12). 12 different texts occur. The table "Datasets" below lists them. |
| 4 | `speed_MTps` | MT/s | Memory speed of the boot in which the interval ran: 7200 or 8000. For the rerun, control I and F72d12 it comes from the saved file `try6.txt` of that boot (a record of the module count and the memory speed, written at 20:02:21 UTC). For an earlier run it comes from the DIMM report: one row of that report gives 8000 MT/s as the firmware setting until 2026-11-17 19:43 UTC [Ref10]. So the value 8000 is a firmware setting. The facts sheet states a limit for the boot of 2026-11-09, which holds 471 of the 493 records at 8000 MT/s: no reading of the applied speed was saved in that boot. |
| 5 | `modules` | count | Number of memory modules in that boot: 12 or 10 [Ref10]. |
| 6 | `boot` | text | Rerun, control I and F72d12: the boot id of Linux (`3bfc57a1-...`). The script takes this value from the saved file `try6.txt` [Ref10]. The integrity check with the key `boot` in `meta.checks` compares it with the 18 state lines of the two run logs and with the 3 `probe.txt` files of part A. The folder of F72d12 holds no boot id. `meta.F72d12_boot` holds the proof for that process. Earlier runs: a label such as `boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC)` [Ref10]. |
| 7 | `folder` | path | Result folder of the run, written as `R/...`. |
| 8 | `file` | file name | The csv file inside `folder` that holds the interval. |
| 9 | `line` | line number | Line of that csv file. Part A form: the interval row. bwx form: the I row (the summary row of the interval). The 120 T rows of the interval follow the I row. |
| 10 | `tag` | text | Rerun and control I: the folder tag (`T72A1` to `T72I2`). Earlier bwx runs of `rx.sh` or `r0.sh`: the csv file name without `.csv`. Runner `bwx`, A-2 and A-3: the tag of the `-- step` header line of the process. This line stands in the csv file before the rows of a process. It holds a tag, the binary, the load averages, the time and the arguments of the process [Ref7]. A-1: `null` (72 records) [Ref6]. |
| 11 | `session` | number | Rerun: the session of go.sh, 1 to 3. `null` for the fourth part C process T72C4, which ran after session 3. Control I: number of the control process (1 or 2). It is not a session. `null` for every earlier run. |
| 12 | `process` | number | Part A form only: place of the process in the list that the script read from the csv file, counted from 1. In `rerun-A`, A-1 and A-2 this is the number of the process inside its file. In A-3 the list holds only 3 of the processes of the file, so the value counts 1 to 3 [Ref4] [Ref6]. bwx form: `null`. |
| 13 | `proc_key` | text | One value per process. Part A form: `folder`, `file` and `process`, joined by `\|`, plus the tag of the header line when the header has one. bwx form: `folder`, `file` and `tag`. 169 different values occur. Two records with the same `proc_key` come from the same process. |
| 14 | `round` | number | Part A form: round of the run script, 1 or 2. In A-3 it is the repeat number, 1 to 3. bwx form: round of the kernel sequence inside the process, counted from 0. |
| 15 | `pos` | number | bwx form only: position of the kernel in the sequence of the process, counted from 0. |
| 16 | `interval` | number | Number of the interval inside the process, counted from 0. Part A form: the column `rep` of the csv row (0, 1 or 2). bwx form: `round` x length of the sequence + `pos`. |
| 17 | `kernel` | text | Name of the benchmark loop, as the binary names it. Part A form: `read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy`. bwx form: `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256`, `read_1pl`. |
| 18 | `kernel_before` | text | bwx form: the kernel that was timed directly before in the same process, or `none (first interval of the process)`. Part A form: binary and kernel of the process directly before in the same csv file, or `none (first process of the file)`. For A-3 the text `not listed (...)` marks a process whose direct predecessor is not in the list. The text `none (first process of the file)` says nothing about the work before the file (text of `meta.fields.kernel_before`). Example: the first process of session 2 of `rerun-A` has this text. Field 40 of the same records says that the session started 5 s after the 120-thread `bwx12` process T72C1. In 62 records of the bwx form the field names a kernel that has no record of its own in this file (`asmread2`, `read_nop32`, `read_sparse`, `read_1pl_nop96`, `read_pf1024`). The reason is that the script takes only a part of the intervals of some earlier runs. |
| 19 | `binary` | text | `bw_old`, `bw_new`, `bwx12`, `bwx11` or `bwx`. Part A form: the name in the header line of the process in the csv file. bwx form, earlier runs: the script takes the first 8 characters of `binary_sha256` and looks up the name in a fixed table. bwx form, rerun and control I: the script sets the fixed text `bwx12`. It does not derive it from a file [Ref6]. |
| 20 | `binary_sha256` | 64 hex characters | sha256 checksum of the binary. Part A form: read from a `probe.txt` file. bwx form: read from the file `env.txt` of the run folder. For the dataset R0 it is read from the run script `r0.sh` [Ref6]. The script does not compute the value. The binary files `bw_old`, `bw_new` and `bwx12` are not in the local folders. So their checksums are known only from these records. |
| 21 | `GBps` | GB/s | The rate of the interval over all 120 threads. This is the final throughput number. Part A form: the column `aggregate_GBps` of the csv row. The binary computes it as the sum of the bytes of all threads divided by the longest per-thread time, and prints 2 decimals [Ref15] [Ref19]. bwx form: the sum over the 120 T rows of bytes / elapsed_s / 1e9, rounded to 0.001 GB/s [Ref8]. |
| 22 | `rate_kind` | text | Says which of the two formulas of field 21 the record uses. The two formulas are different measures. For the same interval the first formula gives a value equal to or lower than the second. The reason: it divides all bytes by the longest thread time. |
| 23 | `mesh0_GBps` | GB/s | bwx form only: the part of `GBps` that comes from the threads on CPUs 0 to 63 (mesh 0) [Ref8]. |
| 24 | `mesh1_GBps` | GB/s | bwx form only: the part of `GBps` that comes from the threads on CPUs 64 and above (mesh 1). In a 120-thread run these are CPUs 64 to 119 [Ref8]. |
| 25 | `passes` | count | Part A form only: `total_bytes` divided by `bytes_per_thread` of the csv row, as a whole number [Ref7]. For `read`, `asmread`, `write` and `asmwrite` this is the number of buffer passes that all threads completed in the interval. For `copy` and `asmcopy` it is 2 x that number. The binary counts read plus written bytes for these two kernels (text of `meta.units.passes`). |
| 26 | `per_thread_min_GBps` | GB/s | Part A form only: column of the same name in the csv row, 2 decimals. The binary computes for each thread its bytes divided by its own elapsed time. This column is the lowest of these thread rates, so it is the rate of the slowest thread [Ref19]. |
| 27 | `per_thread_max_GBps` | GB/s | Part A form only: column of the same name. It is the highest of the thread rates, so it is the rate of the fastest thread [Ref19]. |
| 28 | `per_thread_avg_GBps` | GB/s | Part A form only: column of the same name. It is the sum of the thread rates divided by the number of threads (120 here) [Ref19]. So 120 x this value is the sum of the thread rates, exact to 0.6 GB/s (120 x the rounding of 0.005 GB/s). |
| 29 | `threads` | count | Number of threads of the interval. Part A form: the column `threads` of the csv row. bwx form: the number of T rows of the interval. It is 120 in all 793 records. |
| 30 | `is_64_56` | true or false | bwx form only: `true` when the interval has 64 T rows on CPUs 0 to 63 and 56 T rows on CPUs 64 to 119, on 120 different CPUs [Ref8]. It is `true` in all 460 records. |
| 31 | `flagged` | count | bwx form only: number of T rows of the interval whose last column `flags` is not `-`. It is 0 in all 460 records. In `bwx12` the only flag is `late`: with the common stop rule a thread started more than 100000 ns (0.1 ms) after the common start time [Ref17]. |
| 32 | `stop` | text | Stop rule of the timed interval. Part A form: `whole pass`. The script sets this text for every part A record [Ref4]. bwx form: the value `stop=` of the csv header. It is `common` in all 460 records. |
| 33 | `start` | text | bwx form only: the value `start=` of the csv header, `common` or `offset`. `offset` occurs only in 144 records of runner `bwx`. |
| 34 | `min_ms` | ms | Length setting of one timed interval. Part A form: 500 (0.5 s). The script sets this number for every part A record [Ref4]. The header line that the binary prints before the rows of a process holds the same value: `min_ms=500` in all 111 processes of the part A form [Ref15]. In part A it is the shortest timed length of a thread: a thread stops at the first clock read at which its timed length has reached this value [Ref19]. bwx form: the value `min_ms=` of the csv header, 6000 (6 s) or 4000 (4 s). With the common stop rule of `bwx12` it is the time from the common start to the common stop [Ref17]. There it is not a lower limit. Each thread reads the clock at its own start and at its own end. In the 8880 T rows of the rerun and control I the timed length of a thread (column `elapsed_s`) is 5.999979 s to 6.000457 s, and 89 rows are below 6 s. |
| 35 | `count` | 0 or 1 | bwx form only: the value `count=` of the csv header. In `bwx12` the value 1 means that the runner was started with the option `--count`. Then it also records hardware event counters of the CPU for each thread and interval (the C rows of the csv file) [Ref17]. |
| 36 | `thp` | text | bwx form only: the value `thp=` of the csv header. It is `madvise` in all 460 records. In `bwx12` this means that the runner asks Linux for huge pages (pages of 2 MiB) for its buffers [Ref17]. |
| 37 | `load1_at_launch` | load average (no unit) | 1-minute load average of Linux, read by the run script directly before it started the process. Part A form: from the header line of the process in the csv file. bwx form: from the launch line of `launches.txt`, or for runner `bwx` from the `-- step` header line [Ref6]. |
| 38 | `launch_utc` | time, UTC | Launch time of the process, for example `2026-11-17T22:14:41Z`. It comes from the same line as field 37. |
| 39 | `gap_s` | s | Rerun and control I only: seconds between the end of the previous 120-thread process of the rerun or of control I and this launch, at a resolution of 1 s [Ref9]. bwx form: every record of a process carries the gap of that process. Part A form: set only on the first process of sessions 2 and 3 (6 records). It is `null` for the first step T72A1 and for processes 2 to 24 of a session. The facts sheet states that a true gap can be up to 2 s longer than the value (est.). It gives two reasons. The time stamps have a resolution of 1 s. The run script `rx.sh` checks once per second whether its process still runs. |
| 40 | `start_state` | text | Rerun and control I only: one sentence on what ran before the step started. In part A it describes the first process of the session, and all 72 records of the session carry the same text [Ref9]. |

### Datasets (values of field 1)

The records of one dataset stand on consecutive lines of the file.

| Dataset | Lines of facts.json | Records | Processes | `part` | `binary` | `speed_MTps` | `modules` | `role` |
|---|---|---|---|---|---|---|---|---|
| `rerun-A` | 2460-2675 | 216 | 72 | A | bw_new, bw_old | 7200 | 12 | rerun |
| `rerun-L` | 2676-2705 | 30 | 3 | L | bwx12 | 7200 | 12 | rerun |
| `rerun-C` | 2706-2729 | 24 | 4 | C | bwx12 | 7200 | 12 | rerun |
| `control-I` | 2730-2749 | 20 | 2 | I | bwx12 | 7200 | 12 | control, added after the first numbers of parts A, L and C were seen |
| `A-1` | 2750-2821 | 72 | 24 | A | bw_new, bw_old | 8000 | 12 | baseline |
| `A-2` | 2822-2857 | 36 | 12 | A | bw_new, bw_old | 8000 | 12 | baseline |
| `A-3` | 2858-2866 | 9 | 3 | A | bw_old | 8000 | 12 | baseline |
| `L-1` | 2867-2876 | 10 | 1 | L | bwx12 | 8000 | 12 | baseline (identical argument line) |
| `L-2` | 2877-2884 | 8 | 2 | L | bwx12 | 8000 | 12 | supporting (4 s, other counter events) |
| `L-3` | 2885-2888 | 4 | 1 | L | bwx12 | 8000 | 12 | supporting (4 s, other counter events) |
| `L-4` | 2889-2894 | 6 | 3 | L | bwx12 | 8000 | 12 | supporting (4 s, other counter events) |
| `R0` | 2895-2902 | 8 | 2 | L | bwx11 | 8000 | 12 | other binary (bwx11) |
| `R0b` | 2903-2908 | 6 | 3 | L | bwx11 | 8000 | 12 | other binary (bwx11), 4 s |
| `X2d12` | 2909-2918 | 10 | 1 | L | bwx12 | 8000 | 12 | not a baseline (firmware test setting) |
| `X1d10` | 2919-2922 | 4 | 1 | L | bwx12 | 8000 | 10 | 10 modules |
| `X1d10b` | 2923-2926 | 4 | 1 | L | bwx12 | 8000 | 10 | 10 modules |
| `BASEd10` | 2927-2930 | 4 | 1 | L | bwx12 | 8000 | 10 | 10 modules |
| `F72d12` | 2931-2940 | 10 | 1 | L | bwx12 | 7200 | 12 | 7200 MT/s sample of the same boot, earlier visit, not part of the rerun |
| `B7a` | 2941-3036 | 96 | 8 | C | bwx | 8000 | 12 | other binary (bwx) |
| `B7b` | 3037-3132 | 96 | 8 | C | bwx | 8000 | 12 | other binary (bwx) |
| `C3a` | 3133-3180 | 48 | 4 | C | bwx | 8000 | 12 | other binary (bwx) |
| `C3b` | 3181-3228 | 48 | 4 | C | bwx | 8000 | 12 | other binary (bwx) |
| `B5a` | 3229-3234 | 6 | 2 | C | bwx | 8000 | 12 | other binary (bwx) |
| `B5b` | 3235-3240 | 6 | 2 | C | bwx | 8000 | 12 | other binary (bwx) |
| `B5a-rev` | 3241-3246 | 6 | 2 | C | bwx | 8000 | 12 | other binary (bwx), reverse kernel order, not in the list of rule V4 |
| `B5b-rev` | 3247-3252 | 6 | 2 | C | bwx | 8000 | 12 | other binary (bwx), reverse kernel order, not in the list of rule V4 |

- The four datasets of the run of 2026-11-17 at 7200 MT/s are `rerun-A`, `rerun-L`, `rerun-C` and `control-I`: 290 records.
- `F72d12` is one more process at 7200 MT/s in the same boot. It ran at 20:02 UTC, before the rerun.
- The other 21 datasets are earlier runs at 8000 MT/s: 493 records.
- From some earlier bwx runs the script takes only a part of the intervals: `oldread` at position 0 and `asmread` at position 1 (datasets L-2, L-3, L-4, R0, R0b, X1d10, X1d10b, BASEd10), or the kernels `oldread`, `read` and `asmread` (runner `bwx`) [Ref6].

### Example records

Four records of the rerun, all from session 1. The values are those of the named lines of `facts.json`.

- Line 2460: **old read kernel**, part A (`bw_old`, kernel `read`), session 1, round 1, first interval.
- Line 2463: **new read kernel**, part A (`bw_new`, kernel `read`), session 1, round 1, first interval.
- Line 2706: **old read kernel**, part C (`bwx12`, kernel `oldread`), process T72C1, round 0, position 0.
- Line 2707: **new read kernel**, part C (`bwx12`, kernel `read`), process T72C1, round 0, position 1. It was timed directly after the record of line 2706, in the same process.

| No. | Field | Line 2460 | Line 2463 | Line 2706 | Line 2707 |
|---|---|---|---|---|---|
| 1 | `dataset` | `"rerun-A"` | `"rerun-A"` | `"rerun-C"` | `"rerun-C"` |
| 2 | `part` | `"A"` | `"A"` | `"C"` | `"C"` |
| 3 | `role` | `"rerun"` | `"rerun"` | `"rerun"` | `"rerun"` |
| 4 | `speed_MTps` | `7200` | `7200` | `7200` | `7200` |
| 5 | `modules` | `12` | `12` | `12` | `12` |
| 6 | `boot` | `"3bfc57a1-e235-4fe5-8c09-a94642f9b60b"` | `"3bfc57a1-e235-4fe5-8c09-a94642f9b60b"` | `"3bfc57a1-e235-4fe5-8c09-a94642f9b60b"` | `"3bfc57a1-e235-4fe5-8c09-a94642f9b60b"` |
| 7 | `folder` | `"R/k120-T72A1-20261117T221209Z"` | `"R/k120-T72A1-20261117T221209Z"` | `"R/w120-T72C1-20261117T221436Z"` | `"R/w120-T72C1-20261117T221436Z"` |
| 8 | `file` | `"threads120.csv"` | `"threads120.csv"` | `"cfwd.csv"` | `"cfwd.csv"` |
| 9 | `line` | `4` | `11` | `128` | `490` |
| 10 | `tag` | `"T72A1"` | `"T72A1"` | `"T72C1"` | `"T72C1"` |
| 11 | `session` | `1` | `1` | `1` | `1` |
| 12 | `process` | `1` | `2` | `null` | `null` |
| 13 | `proc_key` | `"R/k120-T72A1-20261117T221209Z\|threads120.csv\|1"` | `"R/k120-T72A1-20261117T221209Z\|threads120.csv\|2"` | `"R/w120-T72C1-20261117T221436Z\|cfwd.csv\|T72C1"` | `"R/w120-T72C1-20261117T221436Z\|cfwd.csv\|T72C1"` |
| 14 | `round` | `1` | `1` | `0` | `0` |
| 15 | `pos` | `null` | `null` | `0` | `1` |
| 16 | `interval` | `0` | `0` | `0` | `1` |
| 17 | `kernel` | `"read"` | `"read"` | `"oldread"` | `"read"` |
| 18 | `kernel_before` | `"none (first process of the file)"` | `"bw_old read"` | `"none (first interval of the process)"` | `"oldread"` |
| 19 | `binary` | `"bw_old"` | `"bw_new"` | `"bwx12"` | `"bwx12"` |
| 20 | `binary_sha256` | `"e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa"` | `"fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6"` | `"cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a"` | `"cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a"` |
| 21 | `GBps` | `467.83` | `330.59` | `466.014` | `320.901` |
| 22 | `rate_kind` | `"aggregate_GBps column of the csv (sum of bytes / longest per-thread time)"` | `"aggregate_GBps column of the csv (sum of bytes / longest per-thread time)"` | `"sum over the T rows (threads) of bytes / elapsed_s / 1e9"` | `"sum over the T rows (threads) of bytes / elapsed_s / 1e9"` |
| 23 | `mesh0_GBps` | `null` | `null` | `308.388` | `178.202` |
| 24 | `mesh1_GBps` | `null` | `null` | `157.626` | `142.699` |
| 25 | `passes` | `954` | `664` | `null` | `null` |
| 26 | `per_thread_min_GBps` | `2.98` | `2.66` | `null` | `null` |
| 27 | `per_thread_max_GBps` | `4.93` | `3.0` | `null` | `null` |
| 28 | `per_thread_avg_GBps` | `3.99` | `2.84` | `null` | `null` |
| 29 | `threads` | `120` | `120` | `120` | `120` |
| 30 | `is_64_56` | `null` | `null` | `true` | `true` |
| 31 | `flagged` | `null` | `null` | `0` | `0` |
| 32 | `stop` | `"whole pass"` | `"whole pass"` | `"common"` | `"common"` |
| 33 | `start` | `null` | `null` | `"common"` | `"common"` |
| 34 | `min_ms` | `500` | `500` | `6000` | `6000` |
| 35 | `count` | `null` | `null` | `1` | `1` |
| 36 | `thp` | `null` | `null` | `"madvise"` | `"madvise"` |
| 37 | `load1_at_launch` | `0.07` | `0.07` | `94.97` | `94.97` |
| 38 | `launch_utc` | `"2026-11-17T22:12:14Z"` | `"2026-11-17T22:12:16Z"` | `"2026-11-17T22:14:41Z"` | `"2026-11-17T22:14:41Z"` |
| 39 | `gap_s` | `null` | `null` | `5.0` | `5.0` |
| 40 | `start_state` | `"started from an idle machine, 5 s after go.sh started (1-minute load average 0.07)"` | `"started from an idle machine, 5 s after go.sh started (1-minute load average 0.07)"` | `"started 5 s after the 120-thread bwx12 process T72L1"` | `"started 5 s after the 120-thread bwx12 process T72L1"` |

How to read the examples against the raw csv files:

- Line 2460 names line 4 of `threads120.csv` of session 1. That csv row holds `aggregate_GBps` = 467.83 and `total_bytes` = 256087425024. Divided by `bytes_per_thread` = 268435456 (256 MiB) this gives 954 passes [Ref15].
- Line 2706 names line 128 of `cfwd.csv` of T72C1. That line is the I row of the interval. It prints 466.01 GB/s, computed from the total bytes and the longest thread time. The record holds 466.014 GB/s, the sum of the 120 thread rates. The two methods differ by less than 0.01 GB/s here [Ref16].
- Lines 2706 and 2707 are two timed intervals of one process. The time between them is not timed. The T rows after line 128 of `cfwd.csv` end at 6.414 s after the process start, and the T rows after line 490 start at 6.523 s. So 0.109 s lie between the two intervals. In this time the main thread of `bwx12` prints the rows of the first interval and reads the page state of the buffers (how many kB of each buffer lie on 2 MiB pages). Then each thread runs one warm-up pass of the next kernel over its buffer [Ref16] [Ref17].
- In the bwx form `GBps` is `mesh0_GBps` plus `mesh1_GBps`. Line 2706: 308.388 + 157.626 = 466.014 GB/s. The three fields are rounded one by one. So in 111 of the 460 bwx records the sum of the two rounded parts differs from `GBps` by 0.001 GB/s.
- Line 2460 also shows how far the two formulas of field 21 differ in part A. 120 x `per_thread_avg_GBps` = 120 x 3.99 = 478.8 GB/s (est.) is the sum of the thread rates, which is the formula of the bwx form. `GBps` holds 467.83 GB/s, the formula of the part A form. With the whole-pass stop rule the threads stop at different times, and the part A formula divides all bytes by the longest per-thread time [Ref19].

### Keys of `meta`

| No. | Key | Type | What it holds |
|---|---|---|---|
| 1 | `title` | text | Title of the data set. |
| 2 | `written_by` | text | The scripts that wrote the file. |
| 3 | `R` | path | Full path of the results folder. |
| 4 | `S` | path | Full path of this folder. |
| 5 | `units` | object, 6 keys | Unit and meaning of `GBps`, `load1_at_launch`, `gap_s`, `passes`, `min_ms`, `speed_MTps`. |
| 6 | `rate_kinds` | object, 2 keys | The two formulas of the rate: `part_A` and `bwx`. |
| 7 | `fields` | object, 15 keys | Meaning of 14 record fields, and of the keys of `verdicts.q2_rows`. |
| 8 | `rerun` | object, 11 keys | Machine state of the rerun. See the table below. |
| 9 | `launches` | list, 12 records | The 10 steps of the rerun and the 2 steps of control I in time order: T72A1, T72L1, T72C1, T72A2, T72L2, T72C2, T72A3, T72L3, T72C3, T72C4, T72I1, T72I2. See the table below. |
| 10 | `checks` | list, 27 records | The integrity checks of the run. Each record has `key` (short name), `ok` (true or false) and `text` (what was checked and found). All 27 have `ok` = true in the stored file. A file with a failed check is not written. `facts_text4.py` stops the build when one check has `ok` = false [Ref12]. This happens before `build_facts.py` writes `facts.json` and FACTS.md [Ref2]. Since 2026-11-24 a new build gives the check `sha-local` (check 20) `ok` = false. Line 20 of `S/go.sh` was edited on that day. So `go.sh` no longer has the sha256 that the list `S/local.sha` holds for it. A new build then writes no file [Ref21]. Section 1.4 of FACTS.md prints the same 27 checks. |
| 11 | `counts` | object, 2 keys | `intervals` = 793, the number of records. `by_dataset` = records per dataset, 26 entries. `make_report.py` stops when `intervals` differs from the length of the list. |
| 12 | `rules` | text | Name of the file with the comparison rules that were fixed before the run (`S/baselines-and-rules.txt`). |
| 13 | `control_note` | text | Says that control I was added after the first numbers were seen. |
| 14 | `F72d12_boot` | object, 6 keys | The proof that the F72d12 process ran in the boot of the rerun: its start and end time, and the files and lines that hold the same boot id before and after it. |
| 15 | `hardware_error_records` | object, 6 keys | Hardware error records (messages of the firmware in the Linux kernel log) during 12 earlier processes at 8000 MT/s. The object holds 18 records in total. Each record has its time and its line in the saved journal (the log store of Linux, which keeps the Linux kernel log of earlier boots). 4 of them also name the interval that they fall into or touch. The key `rerun` says that the Linux kernel log was not read during or after the rerun. |
| 16 | `firmware_settings` | object, 5 keys | What the saved files show about firmware settings: 3 saved settings lists, 4 files with replies of the settings tool, and the last reading of the memory speed setting. |

Keys of `meta.rerun`:

| Key | Unit or type | Meaning | Value in the file |
|---|---|---|---|
| `boot_id` | text | Boot id of Linux during the rerun. | `3bfc57a1-e235-4fe5-8c09-a94642f9b60b` |
| `modules` | count | Memory modules in that boot. | 12 |
| `speed_MTps` | MT/s | Memory speed in that boot. | 7200 |
| `memtotal_kB` | kB | Usable memory that Linux reported (MemTotal). | 395392808 |
| `speed_proof` | text | Where the speed was read: file, line and time. The speed was not read during the rerun. A reading needs root rights. | text |
| `go_start`, `go_end` | time, UTC | First and last state line of the log of go.sh (the driver script). | `2026-11-17T22:12:09Z`, `2026-11-17T22:22:18Z` |
| `go2_start`, `go2_end` | time, UTC | The same for go2.sh (the script of control I). | `2026-11-17T22:23:35Z`, `2026-11-17T22:33:34Z` |
| `kernel_log_read` | true or false | Whether the Linux kernel log was read during or after the rerun. The script holds this value as a fixed constant. It does not derive it from a file [Ref1]. | false |
| `root_used` | true or false | Whether root rights were used. This value is a fixed constant of the script too [Ref1]. | false |

Keys of one record of `meta.launches` (one record per step of the rerun or of control I):

| Key | Unit or type | Meaning |
|---|---|---|
| `tag` | text | Folder tag of the step, for example `T72C1`. |
| `part` | text | `A`, `L`, `C` or `I`. |
| `session` | number | As field 11 of an interval record. |
| `script_start` | time, UTC | Time in the name of the result folder. The run script takes it when it starts. |
| `first_launch` | time, UTC | Launch of the first process of the step. |
| `end` | time, UTC | End of the last process of the step. |
| `gap_s` | s | `first_launch` minus `end` of the step before. `null` for the first step T72A1. It is 5 s for the 9 following steps of go.sh, and 287 s and 265 s for the two steps of control I. |
| `load1_at_first_launch` | load average | 1-minute load average at `first_launch`. |
| `start_state` | text | The same sentence as field 40 of the interval records of the step. |

### Keys of `verdicts`

The scripts `facts_text.py` and `facts_text4.py` build this object while they write the text of FACTS.md [Ref11] [Ref12].

| No. | Key | Type | What it holds |
|---|---|---|---|
| 1 | `q1` | text | The verdict for Q1: old read kernel against new read kernel at 7200 MT/s. It is the same text as the verdict paragraph of section 3.4 of FACTS.md after the words "**Verdict.**" [Ref20]. |
| 2 | `q2` | text | The verdict for Q2: 7200 MT/s against 8000 MT/s. It is `q2_old_read`, one space, and `q2_new_read`. |
| 3 | `q1_parts` | list, 9 records | The numbers that `q1` quotes: one record per kind of old-against-new pair. These are the 9 rows of the table in section 3.4 of FACTS.md. See the table below. |
| 4 | `q2_rows` | list, 42 records | The range comparisons for Q2: one record per comparison of a 7200 MT/s range with an 8000 MT/s range. `q2` quotes a part of them. See the table below. |
| 5 | `insufficient_data` | list, 11 texts | What the data do not show. 9 of the 11 texts also name a measurement that would resolve the point. Texts 7 and 9 name none. The same 11 items stand in section 6 of FACTS.md under "Not established". |
| 6 | `hypotheses` | list, 5 texts | Hypotheses H1 to H5, not tested. The same 5 items stand in section 6 of FACTS.md. |
| 7 | `rule_wordings` | object, 3 keys | The three fixed result texts: `differs` ("differs between the 8000 MT/s boot and the 7200 MT/s boot"), `same` ("no difference seen"), `no_read` ("Insufficient data: no 8000 MT/s run of kernel read with bwx12"). |
| 8 | `short_version` | object, 2 keys | `sentences`: the 3 result sentences of section 0 of FACTS.md. `detail`: the 12 bullets under them [Ref20]. |
| 9 | `q2_old_read` | text | Verdict for Q2, old read kernel. It is the first verdict paragraph of section 4.9 of FACTS.md after its bold label [Ref20]. |
| 10 | `q2_new_read` | text | Verdict for Q2, new read kernel. It is the second verdict paragraph of section 4.9 of FACTS.md after its bold label [Ref20]. |
| 11 | `same_boot` | object, 13 keys | The three times at which the argument line of part L ran in the 7200 MT/s boot (F72d12, part L, control I): lowest and highest `asmread` rate of each, in GB/s. The object also holds the highest minus the lowest of these rates (`spread_GBps`), the distances of part L above F72d12, and the distances of part L above the range of the 8000 MT/s datasets L-1 to L-4. |
| 12 | `pool_8000_by_start_state` | object, 8 keys | A view that was added after the numbers were seen: the 7 `bwx12` processes of the datasets L-1 to L-4 (8000 MT/s) split into the 2 that started at a load below 1.0 and the 5 that started after 120-thread work, with the `oldread` and `asmread` ranges of each group in GB/s. The other 4 `bwx12` processes at 8000 MT/s of this file (X2d12, X1d10, X1d10b, BASEd10) are not in the view. The object also holds the distances of part L and of part C to the second group, and the `oldread` ranges of the `bwx11` and `bwx` processes that started after 120-thread work. |
| 13 | `part_A_thread_rates` | list, 6 records | Part A, load-only kernels of session 1 against 8000 MT/s: the distance of the nearest ends in GB/s by two methods, one record per binary, kernel and round. |

Fields of one record of `verdicts.q1_parts`:

| No. | Field | Unit or type | Meaning |
|---|---|---|---|
| 1 | `part` | text | `C`, `L`, `A`, the control I, or F72d12. |
| 2 | `group` | text | Part C only: the load-only kernel of the pair and the kernel that ran directly before it, for example `read after oldread`. The value `asmread first` marks asmread as the first interval of a process. `null` for the other parts. |
| 3 | `pair` | text | Which two intervals form a pair. In the record of part A a pair is two processes: the medians of their 3 intervals are compared. |
| 4 | `smallest_drop_pct` | % | Smallest drop over the pairs. Drop = (1 - new rate / old rate) x 100. Rounded to 0.01 %. |
| 5 | `largest_drop_pct` | % | Largest drop over the pairs. |
| 6 | `n` | text | Number of pairs, intervals per kernel, processes, sessions and boots. |

The first record holds the main result: `part` = `C`, `group` = `read after oldread`, `smallest_drop_pct` = 30.48, `largest_drop_pct` = 31.17, from 4 pairs.

Fields of one record of `verdicts.q2_rows`:

| No. | Field | Unit or type | Meaning |
|---|---|---|---|
| 1 | `part` | text | `A`, `L` or `C`. |
| 2 | `kernel` | text | Kernel of the comparison. For part A the binary stands before it, for example `bw_old read`. For the kernel `read` of part C the value also names the kernel that ran before, for example `read after oldread`. |
| 3 | `row_7200` | text | Key of the 7200 MT/s set of intervals. The script keeps the key as it was in the earlier builds of the file. A tool can find the row by it. |
| 4 | `lo_7200` | GB/s | Lowest interval rate of the 7200 MT/s set. |
| 5 | `hi_7200` | GB/s | Highest interval rate of the 7200 MT/s set. |
| 6 | `n_7200` | count | Number of intervals in the set. |
| 7 | `processes_7200` | count | Number of processes in the set. |
| 8 | `scope_8000` | text | Key of the 8000 MT/s set that the row is compared with. |
| 9 | `lo_8000` | GB/s | Lowest interval rate of the 8000 MT/s set. |
| 10 | `hi_8000` | GB/s | Highest interval rate of the 8000 MT/s set. |
| 11 | `n_8000` | count | Number of intervals in the set. |
| 12 | `processes_8000` | count | Number of processes in the set. |
| 13 | `overlap` | true or false | `true` when the two ranges share at least one value. |
| 14 | `distance_GBps` | GB/s | Distance between the nearest ends of the two ranges. 0 when they overlap. Positive when the 7200 MT/s range is the higher one. |
| 15 | `wording` | text | The result text of the rule, only when `decides` is true. Otherwise `null`. |
| 16 | `decides` | true or false | `true` when this row is the one that the rule uses for the wording. 15 of the 42 rows have `true`. |
| 17 | `note` | text | A remark, or an empty text. |
| 18 | `row_7200_label` | text | The label of the 7200 MT/s set. In 34 of the 42 records it is the text that FACTS.md prints in the first column of a comparison table. The other 8 records have no row in a comparison table of FACTS.md: the 6 records of rule V3 and the 2 records of the kernel `read` of part C. In these 8 records the field repeats `row_7200`. |
| 19 | `scope_8000_label` | text | The label of the 8000 MT/s set. In the same 34 records it is the text that FACTS.md prints in the column "8000 MT/s range used" of that table row. In the other 8 records the field repeats `scope_8000`. FACTS.md does not print the texts of these 8 records. |

The 6 rows of part A for the load-only kernels follow another rule (rule V3). There `overlap` is `true` when at least one of the three intervals lies inside the 8000 MT/s range. `distance_GBps` is the smallest distance of an interval above that range to its upper end [Ref12]. In all 6 rows `decides` is `true` and `wording` is `outside (above)`. This text of rule V3 is not one of the three texts of `rule_wordings`.

## Old read kernel and new read kernel in this file

The kernel name alone does not tell old from new. The name `read` means the old read kernel in the binary `bw_old`, and the new read kernel in the binaries `bw_new` and `bwx12`.

| Kernel | Select the records with | Records in the file | Of these in the rerun and control I |
|---|---|---|---|
| Old read kernel, part A form | `binary` = `bw_old` and `kernel` = `read` | 39 | 18 (`rerun-A`) |
| New read kernel, part A form | `binary` = `bw_new` and `kernel` = `read` | 30 | 18 (`rerun-A`) |
| Old read kernel, `bwx12` | `binary` = `bwx12` and `kernel` = `oldread` | 39 | 18 (6 `rerun-L`, 8 `rerun-C`, 4 `control-I`) |
| New read kernel, `bwx12` | `binary` = `bwx12` and `kernel` = `read` | 8 | 8 (`rerun-C`) |
| asmread, `bwx12` (used in place of the new read kernel in part L and control I) | `binary` = `bwx12` and `kernel` = `asmread` | 39 | 18 (6 `rerun-L`, 8 `rerun-C`, 4 `control-I`) |

- The new read kernel of `bwx12` was timed only in part C of the rerun. No record at 8000 MT/s holds it (text of `verdicts.rule_wordings.no_read`).
- Parts L and control I time `asmread` in its place. The facts sheet states that it is the same loop of loads.
- The older runners also have kernels named `oldread`, `read` and `asmread`: 7 `oldread` and 7 `asmread` records of `bwx11`, and 104 records each of `oldread`, `read` and `asmread` of `bwx`. FACTS.md shows them as rows of another binary. They are not like-for-like baselines.

How to pair an old record with a new record:

- **bwx form, binary `bwx12`:** take the `oldread` record and the `read` record with the same `proc_key` and the same `round`. They were timed in the same process and the same round. Example: lines 2706 and 2707.
- **Part A form:** take the `bw_old` process and the `bw_new` process with the same `session` and the same `round`. Each process has 3 records (`interval` 0, 1, 2).

## Which code reads this file

| Script | What it reads | What it does with it |
|---|---|---|
| `make_report.py` (the generator of the report page `whole-chip-rerun-7200.html`) | all of `intervals`. Of `meta`: `counts.intervals`, `rerun`, `launches`. Of `verdicts`: `rule_wordings`, `q2_rows`, `q1_parts`, `same_boot` | It selects records and computes every rate, range and drop of the page. It compares a part of its results with `verdicts` and with FACTS.md. Of `verdicts` it compares 11 of the 42 records of `q2_rows`, 2 of the 9 records of `q1_parts`, and 7 values of `same_boot` (`spread_GBps`, and the 6 distances of part L above the 8000 MT/s datasets L-1 to L-4 and above F72d12) [Ref13]. |
| `test_make_report.py` (tests of the generator) | the whole file | It writes damaged copies (a changed `GBps`, a changed `boot`, a changed `load1_at_launch`, a removed record) and checks that the generator ends with an exit status other than 0 on each. It also runs the generator on one copy without damage and expects the exit status 0 [Ref14]. |

The subfolders of `S` (for example `final-check` and `review-scratch`) hold check scripts of earlier reviews. Some of them read `facts.json`. The scripts of the table above do not call them.

`build_facts.py` writes the file and does not read it back. It writes FACTS.md from the same records before they are rounded to 3 decimals. So a bwx value of FACTS.md can differ in its last printed digit from a value that is computed from this file.

Record fields that `make_report.py` reads: `dataset`, `part`, `speed_MTps`, `modules`, `boot`, `folder`, `file`, `line`, `tag`, `session`, `process`, `proc_key`, `round`, `pos`, `interval`, `kernel`, `kernel_before`, `binary`, `GBps`, `passes`, `threads`, `stop`, `start`, `min_ms`, `count`, `load1_at_launch`, `launch_utc`. It reads `gap_s` and `start_state` from `meta.launches`, not from the interval records.

How the final numbers come from the fields:

- **Rate of one interval.** Part A form: the value of `GBps`. bwx form: the generator opens the csv file that `folder` and `file` name, takes the 120 T rows after line `line`, and sums bytes / elapsed_s / 1e9 over them. It stops when this sum, rounded to 3 decimals, is not equal to `GBps` [Ref13]. So the `GBps` of every bwx record that the page uses is checked against the raw file at every build.
- **Old against new, bwx form.** For each pair with the same `proc_key` and `round`: drop = (1 - rate of the load-only kernel / rate of `oldread`) x 100. Example with lines 2706 and 2707: (1 - 320.901 / 466.014) x 100 = 31.1 %. FACTS.md prints 31.1 for this pair in the first row of the first table of its section 3.3 [Ref20].
- **Old against new, part A form.** For each session and round: the median of the 3 `GBps` values of the `bw_new` `read` process, divided by the median of the 3 values of the `bw_old` `read` process. Drop = (1 - this ratio) x 100. Example, session 1, round 1: medians 330.59 and 467.83 GB/s, ratio 0.707, drop 29.3 %. FACTS.md prints these values in the first row of the second table of its section 3.1 [Ref20].
- **7200 MT/s against 8000 MT/s.** The lowest and the highest `GBps` of a set of records form a range. Two ranges are compared for overlap. The results are the records of `verdicts.q2_rows`.

<details>
<summary>Words used here</summary>

The entries of the first list are copied word for word from the word list of FACTS.md [Ref18]. One entry has a change: the entry "Read kernel" says "On this page" where FACTS.md says "In this sheet".

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM. CRB has 12 slots.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Baseline, like-for-like**: an earlier 8000 MT/s run with 12 modules that used the same binary and method as a part of the rerun. The list was fixed before the run.
- **Supporting row, other-binary row**: earlier 8000 MT/s runs that differ in interval length or counter setup (supporting), or that used another runner binary (other binary).
- **Ranges overlap**: two min-to-max ranges share at least one value.
- **Rules V1 to V4, F1, F2**: the comparison rules in `baselines-and-rules.txt`.
- **est.**: estimated, not measured directly.

Added for this file. The entry "Load average" is a short form of the entry of FACTS.md:

- **Rerun**: the whole-chip read test that go.sh ran on CRB on 2026-11-17 (parts A, L and C), after the memory speed was lowered from 8000 MT/s to 7200 MT/s. Control I followed it on the same day.
- **Facts sheet**: the file `FACTS.md` of this folder. It is the detailed written record of the rerun.
- **Record**: one JSON object of the list `intervals`. It stands on one line of the file.
- **Dataset**: a group of records with one label, for example all records of part A of the rerun.
- **Part A form, bwx form**: the two forms of an interval record. They differ in which fields are filled.
- **F72d12**: one bwx12 process with the argument line of part L. It ran at 20:02 UTC in the boot of the rerun, 2 h 9 min before go.sh started.
- **go.sh, go2.sh**: the driver script of the rerun, and the script of control I.
- **rx.sh, r0.sh**: run scripts that start bwx processes. They write the files `env.txt` and `launches.txt` of a run folder.
- **probe.txt**: a file that the run script of part A writes into its result folder. It holds the machine state before and after the run and the sha256 values of the binaries.
- **Step**: one start of a run script by go.sh or go2.sh. It has one result folder with a tag such as `T72A1`.
- **DIMM report**: the file `/home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md`. It holds the boot history of CRB with the module count of each boot.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes.
- **Q1, Q2**: the two questions of the facts sheet. Q1: is the new read kernel still below the old read kernel at 7200 MT/s, and by how much. Q2: did either kernel's rate differ from the earlier runs at 8000 MT/s.
- **Drop**: how far the new rate lies below the old rate, in percent of the old rate.

</details>

## References

- [Ref1] `S/build_facts.py`, lines 899 to 1030: function `write_json` (the keys of `meta`, the rounding to 3 decimals, the layout with one record per line, the rename of the temporary file). Lines 400 to 405: function `hw_compare_json` (the rounded rates and interval times of `meta.hardware_error_records.all_intervals`).
- [Ref2] `S/build_facts.py`, lines 1033 to 1052: function `main` (order of the steps: the text of FACTS.md is built in line 1037, before the two output files are written in lines 1038 to 1041).
- [Ref3] `S/facts_data.py`, lines 421 to 433: function `base_record` (the 40 keys of a record and their order).
- [Ref4] `S/build_facts.py`, lines 119 to 140: function `add_k120` (records of the part A form, the fixed values of `stop` and `min_ms`).
- [Ref5] `S/build_facts.py`, lines 142 to 160: function `add_bwx` (records of the bwx form).
- [Ref6] `S/build_facts.py`, lines 162 to 284: the calls that set `dataset`, `part`, `role`, `session`, `tag`, the checksum, the load and the launch time for each group of runs, and that choose the kernels and positions taken from earlier runs. Line 178 holds the fixed text `bwx12`. `S/facts_data.py`, lines 393 to 394: the table `SHA_NAMES` (the name of a binary by the first 8 characters of its sha256).
- [Ref7] `S/facts_data.py`, lines 260 to 261 (the form of a `-- step` header line) and lines 264 to 304: function `read_k120` (columns of a part A csv row, `passes`).
- [Ref8] `S/facts_data.py`, lines 313 to 383: functions `read_bwx` and `bwx_intervals` (header values, T rows, sums per mesh, `is_64_56`, `flagged`, `kernel_before`).
- [Ref9] `S/build_facts.py`, lines 88 to 116: order of the steps in time, `gap_s`, `start_state`.
- [Ref10] `S/build_facts.py`, lines 56 to 64, and `S/facts_data.py`, lines 206 to 255 and 405 to 418: memory speed, module count and boot of a record.
- [Ref11] `S/facts_text.py`, lines 345 to 368 (start of the object `verdicts`, function `q2row`), lines 477 to 559 (`short_version`), lines 1423 to 1449 (`q1_parts`, `q1`).
- [Ref12] `S/facts_text4.py`, lines 736 to 744 (rows of rule V3), line 1461 (the build stops when an integrity check failed), lines 1312 to 1379 (`q2_old_read`, `q2_new_read`, `q2`), lines 1384 to 1433 (`same_boot`, `pool_8000_by_start_state`, `part_A_thread_rates`), lines 1554 and 1612 (`insufficient_data`, `hypotheses`).
- [Ref13] `S/make_report.py`, lines 176 to 189 (function `val`: the rate of a record), lines 234 to 239 (load of the file, count check), lines 272 to 336 (selections with their expected counts), lines 407 to 456 (pairs and drops of Q1), lines 770 to 809 (comparison with `verdicts`), lines 879 to 881 (`meta.launches`).
- [Ref14] `S/test_make_report.py`, lines 19 to 79: the damaged copies, the test cases, and the check of the exit statuses (line 79).
- [Ref15] `R/k120-T72A1-20261117T221209Z/threads120.csv`, lines 1 to 4 and 11: header lines of a part A csv file and the interval rows of the examples of lines 2460 and 2463. Line 2 is the header line that the binary prints, with `min_ms=500`. The 111 processes of the part A form stand in 6 csv files: `threads120.csv` of the folders of T72A1, T72A2 and T72A3 and of `R/kernels-20261113T181222Z`, and `A1.csv` and `A3.csv` of `R/partA-20261113T205055Z`. The header line of each of these processes holds `min_ms=500`.
- [Ref16] `R/w120-T72C1-20261117T221436Z/cfwd.csv`, lines 1 to 4, 128, 129 and 490: header lines of a bwx csv file, the I rows of the examples of lines 2706 and 2707, and the first T row. Lines 129 to 248 and 491 to 610: the T rows of the two intervals with the columns `elapsed_s`, `t_start_s` and `t_end_s`.
- [Ref17] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`, lines 133 and 1725 (flag `late`), line 448 (request for huge pages), line 1669 (warm-up pass before each timed interval), lines 1688 to 1701 (clock reads at the start and at the end of a timed interval with the common stop rule), lines 1727 to 1731 (the threads wait while the main thread reads the page state), lines 2929 to 2930 (option `--count`), lines 3018 to 3024 (the two header lines with `thp`, `stop`, `start`, `count`), lines 3059 to 3061 (common start time and common stop time), lines 3077 to 3078 (the rate that an I row prints), lines 3081 to 3084 (a T row with its column `flags`), lines 3105 to 3114 (the main thread reads the page state after it printed the rows of an interval). The local `bwx12.c` has the sha256 `e3d4442b...`. The build record `crb-build-1/build.txt` of the same folder holds this value (line 17) beside the sha256 of the binary `bwx12` (`cd58e564...`, line 20).
- [Ref18] `S/FACTS.md`, lines 38 to 89: the word list of the facts sheet.
- [Ref19] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`, lines 584 to 603 (source of `bw_new`), and `bandwidth.orig.c` of the same folder, lines 431 to 446 (source of `bw_old`): the rate of each thread, the lowest, the highest and the average of these rates, and `aggregate_GBps` as the total bytes divided by the longest thread time. `bandwidth.c`, lines 471 to 479, and `bandwidth.orig.c`, line 320: a thread stops at the first clock read at which its timed length has reached the minimum time. Limit of the citation of `bandwidth.c`: the records hold two texts of this file. The local file has the sha256 `f1985072...`. That is the value in `R/kernels-20261113T183218Z/probe.txt` (a build-only run of 18:32:18 UTC on 2026-11-13). The timed run of 18:12:22 UTC recorded the sha256 `c1406e02...` for `bandwidth.c` (`R/kernels-20261113T181222Z/probe.txt`, line 15). All three records of that day give the same sha256 for the binary `bw_new` (`fd7c14df...`). So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above the function `k_read` (the read kernel of `bandwidth.c`) with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). This record lies outside the project folder. With this edit reversed, the local text has the sha256 value of the earlier text (`c1406e02...`). No code line differs. No copy of the earlier text exists under `/home/jhan/workspace/titan/cache-perf`. `bandwidth.orig.c` has the recorded value `61228754...`.
- [Ref20] `S/FACTS.md`, lines 14, 16 and 18 (the three result sentences of section 0), lines 22 to 33 (the 12 detail bullets), line 346 (first row of the second table of section 3.1), line 394 (first row of the first table of section 3.3), line 432 (verdict paragraph of section 3.4), lines 892 and 894 (the two verdict paragraphs of section 4.9).
- [Ref21] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24/check_facts_build.py` and its output `check_facts_build.out` in the same folder: the test of 2026-11-24 that ran `build_facts.py` in a copy of `S`. With the edited `go.sh` the build ended with status 1 and wrote no file. With the old line 20 put back it ended with status 0 and printed `checks: 27, failed: 0`.
