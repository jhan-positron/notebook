# `run_sudo.sh` explained, line by line

- Source file: `bench/run_sudo.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 180 lines, 12475 bytes).
- sha256 of the source when this page was built: `9904910869302ead039c9a836e3361c68e1ac3b796b0ded4302f80908bee7a2d`.

## Short version: purpose

`run_sudo.sh` runs the measurements on CRB that need root rights, in up to five numbered parts. Parts 1 and 2 run `homelat`, which measures the latency from each core to each part of the SLC, the last cache level. Parts 3 to 5 run `bandwidth` under `perf stat` and count events of the mesh and of one core during write and read streams.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh, CMN**: the network inside one half of the chip. It connects the cores, the SLC and the memory. Arm calls it CMN (Coherent Mesh Network).
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Mesh cache**: the word of the source for the SLC.
- **Home node**: a node of the mesh that owns a part of the memory addresses and holds one part of the SLC. Arm calls this node type HN-S. The event names of the home nodes start with `hns`.
- **Slice**: the part of the SLC that one home node holds.
- **Crosspoint**: a junction of the mesh. Cores, home nodes and other nodes are connected to its ports. The event names of a crosspoint start with `mxp`.
- **Flit**: one transfer unit on a link or a port of the mesh. The word is short for flow control unit.
- **Credit stall**: a cycle in which a flit cannot be sent and its sender waits for a credit from the receiver. The events whose names end with `txflit_stall` count these cycles.
- **DTC**: the debug and trace controller, the unit of the mesh that holds its counters. `dtc_cycles` is its cycle counter.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: a counter unit. `arm_cmn_0` and `arm_cmn_1` are the PMUs of the two meshes. `armv8_pmuv3_0` is the PMU of the cores.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **Event set**: the events that one `perf stat` run counts. The script keeps each set within the number of counters that the hardware has.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time.
- **Idle control**: a run of `perf stat` over `sleep 2`. It gives the counts of 2 s without a benchmark.
- **`homelat`**: the program built from `homelat.c`. It finds the home node of each line of a buffer and times a pointer chase from each core to the lines of each home node.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`, `asmwrite`**: two kernels of `bandwidth` that are written in assembly. `asmread` only loads, and `asmwrite` only stores.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Process group**: a set of processes that one signal can reach together.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` (lines 23 to 26).
2. Stop with exit status 4 when the user is not root. Stop with exit status 3 when the marker file exists (lines 27 to 30, line 48).
3. Create the result folder in the home folder of the user who called `sudo`. Set the command that gives the files back to that user at the end. Send all later output to `log.txt` too, and build the programs (lines 49 to 56).
4. Read `PARTS`, the list of the parts to run. The default is the parts 1 to 4 (lines 57 to 58).
5. Part 1: the self-test of `homelat` with a buffer of 16 MiB from CPU 3. Then print the number of home nodes per mesh from `nodes.csv`, and the files `chunks.csv` and `verify.csv` (lines 60 to 67).
6. Part 2: the full run of `homelat` with a buffer of 32 MiB from the CPUs 0 to 119 (lines 69 to 73).
7. Part 3: for 5 event sets an idle control, and then 9 cases of `asmwrite` and `asmread`. The function `counted` runs each case once short and once long under each event set (lines 91 to 103).
8. Part 4: for 4 event sets an idle control, and then 3 cases with 64 threads on one mesh or split over both meshes (lines 105 to 119).
9. Part 5, only when `PARTS` holds `5`: check that all event names exist, build 9 event sets for the mesh, one crosspoint and CPU 2, run an idle control per set, and then run 6 cases around CPU 2. The function `counted2` runs each case once short and once long under each set (lines 133 to 179).
10. Print the time and the path of the result folder (line 180).

## Behavior a reader must know

- The script times nothing itself. The times and rates come from `homelat` and `bandwidth`. The counts come from `perf stat`.
- The function `guard` starts every measurement. It runs the command in a process group of its own and looks for the marker file once per 5 s. When the file appears, it sends the termination signal to the group, waits 1 s, sends the kill signal, and ends the script with exit status 3 (lines 34 to 47).
- `guard` also looks only once per 5 s whether the command has ended. So up to 5 s pass between the end of one measurement and the start of the next one.
- Exit statuses of the script: 3 for the marker file, 4 when the user is not root, 5 when an event name of part 5 does not exist. Every other failed command ends the script with the status of that command (option `-e`). A failed check of `homelat` is such a case, with status 2.
- A short run asks `bandwidth` for one timed interval of at least 200 ms, and a long run for one of at least 2000 ms. `perf stat` counts for the whole `bandwidth` process, also for the first write of the buffers and the warm-up. The analysis scripts `subtract.py` and `analyze_writepath.py` subtract the short run from the long run to remove that part.
- With `-a`, `perf stat` counts for the whole system. So a count of a mesh event also holds the traffic of other programs. With `-C 2` it counts on CPU 2 only.
- Thread placement: `taskset` limits everything to the CPUs 0 to 119. `bandwidth` pins thread number `i` to entry `i` of its CPU list. In part 3 the threads use the CPUs 0 to 13 at most, all on mesh 0. In part 4 the 64 threads use the CPUs 0 to 63, or the CPUs 0 to 31 and 64 to 95. In part 5 the threads use the CPUs 2, 3, 4, 6 and 8.
- `homelat` in part 1 measures from CPU 3 and in part 2 from each of the CPUs 0 to 119. In both parts it runs its classification on the CPU of the mesh PMU (file `homelat.c`).
- The header comment says that part 1 probes 512 lines again. The command of part 1 asks for 256 (line 63).
- The trap of line 52 runs at every end of the script. It makes the user who called `sudo` the owner of the result folder and of the folder of the script.
- Files in the result folder: `log.txt`, the folders `selftest` and `full` with the output of `homelat`, `writebw.csv` (part 3), `crossmesh.csv` (part 4), `writepath.csv` (part 5), and one count file of `perf stat` per run (`perf-*.csv` and `perf5-*.csv`). In the three CSV files a line that starts with `--` names the run whose rows follow.

## Source and explanation, line by line

- Text shown: the file `bench/run_sudo.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (180 lines, 12475 bytes, sha256 `9904910869302ead039c9a836e3361c68e1ac3b796b0ded4302f80908bee7a2d`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: the five parts and the rules (lines 1 to 22)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_sudo.sh - the root-only measurements. Run on CRB as:  sudo ./run_sudo.sh` | Comment: the name and the purpose of the script: the measurements that need root rights. On CRB, the Arm reference server under test, it is started as `sudo ./run_sudo.sh`. |
| 3 | `# Root is needed for the mesh (CMN) counters: kernel.perf_event_paranoid is 2.` | Comment: root rights are needed for the counters of the mesh. CMN is the Arm name of the mesh, the network that connects the cores, the last cache level and the memory. The Linux setting `kernel.perf_event_paranoid`, which decides who may open counters, is 2. |
| 4 | `#   1. homelat self-test: 16 MiB buffer, core 3 only, 2048 lines per node as in the full run. Discovery must find 64 home nodes per` | Comment: part 1 is a self-test of `homelat`, the program that measures the latency from a core to each part of the last cache level. It uses a buffer of 16 MiB, core 3 only, and 2048 lines per home node as in the full run. The next sentence starts here: the discovery must find 64 home nodes per ... |
| 5 | `#      mesh, a 512-line re-check must agree 98 %, and 8 slices must show the expected cache` | Comment: ... mesh. A second probe of 512 lines must agree to 98 percent. The command of line 63 asks for 256 lines, not 512. And 8 slices must show the expected cache ... |
| 6 | `#      state (about 1 SLC access, 0 misses, 1 L2 refill per timed load). The tool aborts otherwise.` | Comment: ... state: about 1 access to the SLC, 0 misses and 1 L2 refill per timed load. SLC is the name of the project for the last cache level. By the comment the program stops in every other case. |
| 7 | `#   2. homelat full: 32 MiB buffer, every core 0-119 to every home node ("slice distance"); its` | Comment: part 2 is the full run of `homelat`: a buffer of 32 MiB, from every core 0 to 119 to every home node. The comment names the question slice distance. The sentence goes on in line 8. |
| 8 | `#      cache-state check (local-home residency, latency range, no multiplexing) is fatal, like part 1's;` | Comment: its cache-state check tests that the lines stay at the local home, the range of the latency and that no counter was multiplexed. A failed check ends the program, as in part 1. |
| 9 | `#      chunks.csv says which mesh homes each 2 MiB chunk ("two mesh halves").` | Comment: the file `chunks.csv` of that run says on which mesh the lines of each 2 MiB chunk have their home. The comment names the question two mesh halves. |
| 10 | `#   3. mesh-cache write bandwidth: home-node counters during asmwrite and asmread streams.` | Comment: part 3 looks at the write bandwidth of the mesh cache, the word of the source for the SLC. It reads the counters of the home nodes during streams of the kernels `asmwrite` and `asmread`. |
| 11 | `#      Two runs per case (short and long); the count difference divided by the byte difference` | Comment: each case has two runs, a short one and a long one. The difference of the counts divided by the difference of the bytes ... |
| 12 | `#      cancels buffer setup. Events in a run have different event ids, because two filter` | Comment: ... removes the setup of the buffers from the result. The next sentence starts here: the events of one run have different event ids. The reason: two filter ... |
| 13 | `#      variants of one id share a counter slot and get multiplexed (seen 2026-11-02 at 50 %).` | Comment: ... variants of one event id share one counter place and are then multiplexed. The comment saw this on 2026-11-02, at 50 percent. |
| 14 | `#   4. DRAM write collapse: the same counters for 64 writers on one mesh versus 32 on each mesh.` | Comment: part 4 looks at the collapse of the write rate to DRAM, the main memory: 64 writers on one mesh against 32 writers on each mesh. The comment says the same counters. Part 4 has its own event sets (line 109). |
| 15 | `#   5. single-core write path (2026-11-02, not in the default PARTS; note: dtc_cycles counted only ~6,500/s here, so it is not usable as a mesh clock): where is the 73 GB/s bound of one` | Comment: part 5 follows the write path of a single core. It dates from 2026-11-02 and is not in the default `PARTS`. A note inside the comment: the event `dtc_cycles` counted only about 6500 per second, so it cannot serve as a clock of the mesh. The comment still holds this old note. A correction of 2026-11-11 in the report of the project says that the counter did count the clock of the mesh, 2.0 GHz. By the report the 6500 per second were what remained after the script `analyze_writepath.py` subtracted the count of the idle control from the cycle count [Ref5]. The question of part 5: where is the limit of 73 GB/s of one ... |
| 16 | `#      writer? Core counters on CPU 2 (L1/L2 write allocation and write-back, bus writes), the flit and` | Comment: ... writer? Part 5 reads core counters on CPU 2: the allocation of written lines in L1 and L2, the write-back from these caches, and the writes on the bus. It also reads the flit and ... |
| 17 | `#      credit-stall counters of CPU 2's crosspoint (x=1, y=3, node id 0x98, core port p1), and the` | Comment: ... credit-stall counters of the crosspoint of CPU 2. A flit is one transfer unit on a link or a port of the mesh. A credit stall is a cycle in which the sender of a flit waits for a credit from the receiver [Ref5]. The crosspoint is at `x` 1 and `y` 3, its node id is `0x98`, and the core port is `p1`. It also reads the ... |
| 18 | `#      home-node queue occupancy on both meshes. Cases: one writer, partners 2+3 on one port, 2+4 on two` | Comment: ... occupancy of the home node queues on both meshes. The cases: one writer, the partner CPUs 2 and 3 on one port, the CPUs 2 and 4 on two ... |
| 19 | `#      ports, 4 ports, and one reader as control.  Run:  sudo PARTS=5 ./run_sudo.sh   (about 6 min)` | Comment: ... ports, 4 ports, and one reader as a control. Part 5 is started as `sudo PARTS=5 ./run_sudo.sh` and takes about 6 minutes (est.). |
| 20 | `# PARTS selects what runs, e.g.  sudo PARTS=12 ./run_sudo.sh  runs the two homelat parts only.` | Comment: the variable `PARTS` selects what runs. For example `sudo PARTS=12 ./run_sudo.sh` runs only the two `homelat` parts. |
| 21 | `# Shared-host rule: CPUs 0-119 only; every measurement is killed within 5 s if the RUNNING` | Comment: the rule of the shared machine: only the CPUs 0 to 119. Every measurement is killed within 5 s when the marker file ... |
| 22 | `# marker appears (guard below), and homelat checks the marker itself every second.` | Comment: ... appears. The function `guard` does this (lines 34 to 47). `homelat` also checks the marker file itself once per second. |

### Shell options, the CPUs 0 to 119, the root check and the marker check (lines 23 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 23 | `set -euo pipefail` | Three shell options. `-e`: the script stops when a command fails. `-u`: it stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any of its commands fails. |
| 24 | `if [[ -z ${_RUN_CRB_PINNED:-} ]]; then` | Tests whether the variable `_RUN_CRB_PINNED` is empty or not set. `${X:-}` gives an empty text for an unset variable, and `-z` is true for an empty text. The variable is empty in the first start of the script. |
| 25 | `    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"` | Then starts the script again under `taskset`. `exec` replaces the shell with `taskset -c 0-119`. That tool limits the process to the CPUs 0 to 119 and then runs the script (`$0`) with the same arguments (`$@`). `_RUN_CRB_PINNED=1` is set for the new start only, so the second start skips this block. Every process that the script starts inherits the CPU list. |
| 26 | `fi` | Ends the `if` of line 24. |
| 27 | `if [[ $(id -u) -ne 0 ]]; then echo "run as root: sudo $0" >&2; exit 4; fi` | Root check. `id -u` prints the number of the user, which is 0 for root. For every other user the script prints `run as root: sudo` with its own name to the error output (`>&2`) and ends with exit status 4. |
| 28 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. The file exists while another user runs a performance test on CRB. |
| 29 | `BENCH=$(cd "$(dirname "$0")" && pwd)` | `BENCH`: the folder of this script as an absolute path. `dirname` gives the folder part of the script path `$0`, `cd` goes there, and `pwd` prints the path. |
| 30 | `check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }` | Defines the function `check_marker` in one line. `-e` tests whether the marker file exists. `A && B` runs `B` only when `A` succeeds. So when the file exists, the function prints `exists: stopping` with the path to the error output and ends the script with exit status 3. In the other case `return 0` makes the function succeed, so the option `-e` does not stop the script. |

### Function `guard`: run one measurement and kill it when the marker file appears (lines 31 to 47)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `# guard CMD...: runs CMD in its own process group, polls the marker every 5 s, and if it appears` | Comment: `guard` runs a command in a process group of its own. It looks for the marker file every 5 s. A process group is a set of processes that one signal can reach together. The sentence goes on in line 32. |
| 32 | `# kills the whole group (perf and the bandwidth process under it) and exits 3. Worst case to stop:` | Comment: when the marker file appears, `guard` kills the whole group, which is `perf` and the `bandwidth` process below it, and ends the script with exit status 3. The longest time to stop ... |
| 33 | `# 5 s poll + 1 s grace. The kills and waits are guarded against set -e (reviewer's catch).` | Comment: ... is 5 s until the next look plus 1 s between the two signals. The `kill` and `wait` commands are protected against the option `-e`. By the comment a reviewer found that need. |
| 34 | `guard() {` | Starts the function `guard`. Its arguments are the command to run. |
| 35 | `    check_marker` | Marker check before the command starts. |
| 36 | `    setsid "$@" & local pid=$!` | Starts the command in the background (the single `&`). `setsid` runs it in a new session, which makes it the leader of a new process group. `pid`: the process id of that command (`$!`). It is also the number of the group. |
| 37 | `    while kill -0 "$pid" 2>/dev/null; do` | Loop as long as the command exists. `kill -0` sends no signal. It only tests whether the process exists. `2>/dev/null` discards its error message. |
| 38 | `        if [[ -e $MARKER ]]; then` | Tests whether the marker file exists. |
| 39 | `            echo "$MARKER appeared: killing process group $pid ($1)" >&2` | Then prints to the error output that the marker file appeared and that the process group is killed, with the group number and the name of the command. |
| 40 | `            kill -- -"$pid" 2>/dev/null \|\| true; sleep 1; kill -9 -- -"$pid" 2>/dev/null \|\| true` | Sends the termination signal to the whole group: the minus sign before the number means the group. Then waits 1 s. Then sends the signal 9 to the group. A process cannot ignore this signal. `\|\| true` keeps the script running when a `kill` fails, for example when the processes no longer exist. |
| 41 | `            wait "$pid" 2>/dev/null \|\| true` | Waits for the end of the command. Its error message and its failure are ignored. |
| 42 | `            exit 3` | Ends the script with exit status 3. |
| 43 | `        fi` | Ends the `if` of line 38. |
| 44 | `        sleep 5 & wait $! \|\| true` | Waits 5 s: `sleep 5` runs in the background, and `wait $!` waits for it. So the loop looks at the command and at the marker file once per 5 s. `guard` can notice the end of the command up to 5 s late. |
| 45 | `    done` | Ends the loop of line 37. |
| 46 | `    wait "$pid"` | `wait` gives the exit status of the command. A status other than 0 ends the script with that status (option `-e`). |
| 47 | `}` | Ends the function `guard`. |

### Marker check, result folder, owner of the files, log, build and the choice of the parts (lines 48 to 59)

| Line | Source | Explanation |
|---:|---|---|
| 48 | `check_marker` | The first marker check. Nothing was written up to here. |
| 49 | `HOME_DIR=$(getent passwd "${SUDO_USER:-root}" \| cut -d: -f6)` | `HOME_DIR`: the home folder of the user who called `sudo`. `sudo` puts the name of that user into `SUDO_USER`. `${SUDO_USER:-root}` gives `root` when the variable is not set or is empty. `getent passwd` prints the account line of the user, and `cut -d: -f6` takes its sixth field, the home folder. `\|` sends the output of the first command to the second. |
| 50 | `OUT=$HOME_DIR/cache-perf/results/sudo-$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder: `cache-perf/results/sudo-` plus the UTC time of this moment, below that home folder (`date -u` with a format). |
| 51 | `mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders. |
| 52 | `trap 'chown -R "${SUDO_USER:-root}": "$OUT" "$BENCH" 2>/dev/null \|\| true' EXIT` | Sets a command for the end of the script (`trap` with `EXIT`). It runs at every end, also after an error. `chown -R` gives the result folder and the folder of the script, with all files in them, to the user who called `sudo`. Without it the files that root wrote would belong to root. Errors of the command are ignored. |
| 53 | `exec > >(tee -a "$OUT/log.txt") 2>&1` | From here on the standard output of the script goes to the program `tee`. `tee` prints it and also appends it to `log.txt` in the result folder. `>( )` starts `tee` as a process of its own. `2>&1` sends the error output to the same place. |
| 54 | `echo "results: $OUT"; date -u; uname -r` | Prints the path of the result folder, the UTC date and time, and the release of the running Linux kernel (`uname -r`). |
| 55 | `make -C "$BENCH"` | Builds the programs: `make -C` runs `make` in the folder of the script. A failed build ends the script. |
| 56 | `H="$BENCH/homelat"; B="$BENCH/bandwidth"` | `H`: the path of the program `homelat`. `B`: the path of the program `bandwidth`. |
| 57 | `PARTS=${PARTS:-1234}` | `PARTS`: the parts to run. It keeps the value of the environment variable `PARTS` when that is set and not empty. In the other case it is `1234`, the parts 1 to 4. |
| 58 | `part() { [[ $PARTS == *$1* ]]; }` | Defines the function `part`. It succeeds when the text of `PARTS` holds its argument: the pattern `*$1*` matches every text that holds the argument. |

### Parts 1 and 2: the self-test and the full run of `homelat` (lines 60 to 74)

| Line | Source | Explanation |
|---:|---|---|
| 60 | `part 1 && {` | Part 1 runs when `PARTS` holds `1`: `A && { ... }` runs the group in braces only when `A` succeeds. The group ends in line 67. |
| 61 | `echo "== 1. homelat self-test (16 MiB, core 3)"; date -u` | Prints the title of part 1 and the UTC date and time. |
| 62 | `mkdir -p "$OUT/selftest"` | Creates the folder `selftest` in the result folder. |
| 63 | `guard "$H" --bytes 16M --cores 3 --reps 7 --verify-sample 256 --verify-slices 8 --out "$OUT/selftest"` | Runs `homelat` under `guard`. `--bytes 16M`: a buffer of 16 MiB. `--cores 3`: the latency is measured from CPU 3 only, and the buffer is first written there. `--reps 7`: 7 timed passes per set of lines. `--verify-sample 256`: 256 random lines are probed a second time. `--verify-slices 8`: the cache-state check runs for 8 slices. `--out`: the output files go to the folder `selftest`. `homelat` ends with exit status 2 when one of its checks fails, and that ends this script too. |
| 64 | `echo "-- nodes per mesh:"; awk -F, 'NR>1{n[$1]++} END{for (m in n) print "mesh " m ": " n[m] " home nodes"}' "$OUT/selftest/nodes.csv"` | Prints a title. Then `awk` counts the home nodes per mesh from `nodes.csv`. `-F,`: the fields are separated by commas. `NR>1` skips the header line. `n[$1]++` counts the lines by their first field, the mesh. `END` prints one line per mesh with its count. |
| 65 | `echo "-- chunk split (contiguous, mesh0 lines, mesh1 lines, unknown):"; cat "$OUT/selftest/chunks.csv"` | Prints a title and then the file `chunks.csv`: for each 2 MiB chunk of the buffer, how many of its lines have their home on mesh 0, on mesh 1, or have no known home. |
| 66 | `echo "-- cache state per slice:"; cat "$OUT/selftest/verify.csv"` | Prints a title and then the file `verify.csv`: the counter values of the cache-state check, one row per slice. |
| 67 | `}` | Ends the group of part 1. |
| 69 | `part 2 && {` | Part 2 runs when `PARTS` holds `2`. |
| 70 | `echo "== 2. homelat full (32 MiB, cores 0-119)"; date -u` | Prints the title of part 2 and the UTC date and time. |
| 71 | `mkdir -p "$OUT/full"` | Creates the folder `full` in the result folder. |
| 72 | `guard "$H" --bytes 32M --cores 0-119 --reps 7 --out "$OUT/full"` | Runs `homelat` under `guard`: a buffer of 32 MiB, measured from each of the CPUs 0 to 119, with 7 timed passes per set of lines. The output files go to the folder `full`. The command gives no `--verify-sample` and no `--verify-slices`, so the defaults of the program apply: 512 lines and 8 slices. It gives no `--verify-lenient`, so a failed cache-state check ends the program. |
| 73 | `}` | Ends the group of part 2. |

### Function `counted` and the event sets of part 3 (lines 75 to 90)

| Line | Source | Explanation |
|---:|---|---|
| 75 | `# counter runs: perf stat around a bandwidth run, short (0.2 s) and long (2 s) so that` | Comment: the counter runs put `perf stat` around a run of `bandwidth`: a short run of 0.2 s and a long run of 2 s. The sentence goes on in line 76. |
| 76 | `# (long - short) counts / (long - short) bytes is the rate of the streaming loop alone.` | Comment: so the counts of the long run minus the counts of the short run, divided by the bytes of the long run minus the bytes of the short run, are the rate of the streaming loop alone. |
| 77 | `# EV is a list of event names with distinct event ids; each is opened on both meshes.` | Comment: the comment names `EV`, a list of event names with different event ids. In the code the list is the third argument, `events`. Each event is opened on both meshes. |
| 78 | `counted() { # counted <csvfile> <tag> <events> -- bandwidth args` | Starts the function `counted`. By the comment its arguments are the CSV file, a tag for the case, the event names, and then the arguments for `bandwidth`. |
| 79 | `    local csv=$1 tag=$2 events=$3; shift 3` | `csv`, `tag`, `events`: the first three arguments. `shift 3` removes them, so `$@` holds only the arguments for `bandwidth`. |
| 80 | `    local ev=""; for e in ${events//,/ }; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done` | Builds the event list `ev` for `perf`. `${events//,/ }` replaces the commas with spaces, so the loop runs once per event name. Each name is added twice: as `arm_cmn_0/NAME/` for mesh 0 and as `arm_cmn_1/NAME/` for mesh 1. `${ev:+,}` gives a comma when the list is not empty. An event in this form names no node, so it counts the sum over all home nodes of its mesh [Ref2]. |
| 81 | `    for len in short long; do` | Loop: first the short run, then the long run. |
| 82 | `        local ms=200; [[ $len == long ]] && ms=2000` | `ms`: the minimum time of the timed interval of `bandwidth`: 200 ms for the short run and 2000 ms for the long run. |
| 83 | `        echo "-- $tag $len events $events args $*" >> "$csv"` | Appends a title line to the CSV file: the tag, `short` or `long`, the event names and the arguments of `bandwidth` (`$*`). |
| 84 | `        guard perf stat -a -x, -e "$ev" -o "$OUT/perf-$tag-$len-${events%%,*}.csv" -- "$B" "$@" --reps 1 --min-ms $ms >> "$csv"` | Runs `perf stat` under `guard`. `perf stat` starts the command after `--` and counts until that command ends [Ref1]. `-a`: it counts for the whole system, not only for the command. `-x,`: one line per event, with commas between the fields. `-e`: the events. `-o`: the counts go to a file `perf-TAG-LEN-EVENT.csv`, where `${events%%,*}` gives the first event name of the set. The command is `bandwidth` with the given arguments plus `--reps 1 --min-ms`: one timed interval of at least `ms` milliseconds. The output of `bandwidth` is appended to the CSV file. |
| 85 | `        grep -v '^#' "$OUT/perf-$tag-$len-${events%%,*}.csv" \| grep . >> "$csv"` | Appends the counts to the same CSV file. `grep -v '^#'` drops the comment lines of the count file, and `grep .` drops its empty lines. When no line is left, `grep .` fails and the script ends (options `-e` and `pipefail`). |
| 86 | `    done` | Ends the loop of line 81. |
| 87 | `}` | Ends the function `counted`. |
| 88 | `# event sets: distinct event ids per set (0x5 reqs, 0x3 fill, 0x1 miss, 0xd mc local, 0x3b mc remote, 0x2 access, 0x6 sf hit, 0xa eviction)` | Comment: each event set holds events with different event ids. The comment lists the ids: `0x5` requests, `0x3` fill, `0x1` miss, `0xd` memory requests of the kind local, `0x3b` memory requests of the kind remote, `0x2` access, `0x6` hits of the snoop filter, `0xa` eviction. |
| 89 | `SETS="hns_pocq_reqs_recvd_write,hns_cache_fill_all hns_cache_miss_all,hns_mc_reqs_local_all hns_mc_reqs_remote_all,hns_slc_sf_cache_access_all hns_pocq_reqs_recvd_read,hns_sf_hit_all hns_slc_eviction_all_all,hns_pocq_reqs_recvd_hbt"` | `SETS`: 5 event sets with 2 event names each. A space separates the sets, and a comma separates the two names of a set. The names start with `hns`, for the home nodes. Set 1: write requests received and cache fills. Set 2: cache misses and local memory requests. Set 3: remote memory requests and accesses to the SLC. Set 4: read requests received and hits of the snoop filter. Set 5: evictions from the SLC and the requests that a node received as the home of the line (`hbt`) [Ref3]. |

### Part 3: counters of the home nodes during write and read streams (lines 91 to 104)

| Line | Source | Explanation |
|---:|---|---|
| 91 | `part 3 && {` | Part 3 runs when `PARTS` holds `3`. |
| 92 | `echo "== 3. mesh-cache write bandwidth with home-node counters"; date -u` | Prints the title of part 3 and the UTC date and time. |
| 93 | `: > "$OUT/writebw.csv"` | Creates `writebw.csv` as an empty file. `:` does nothing, and `>` creates the file or empties it. |
| 94 | `echo "-- background control, 2 s idle" >> "$OUT/writebw.csv"` | Appends a title line for the idle control: 2 s without a benchmark. |
| 95 | `for set in $SETS; do ev=""; for e in ${set//,/ }; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done` | Loop over the 5 event sets. For each set the event list `ev` is built as in line 80: each name once for mesh 0 and once for mesh 1. |
| 96 | `    guard perf stat -a -x, -e "$ev" -o "$OUT/perf-idle-${set%%,*}.csv" -- sleep 2; grep -v '^#' "$OUT/perf-idle-${set%%,*}.csv" \| grep . >> "$OUT/writebw.csv"; done` | Counts the events for 2 s while only `sleep 2` runs. This is the background of the machine without a benchmark. The counts go to a file `perf-idle-EVENT.csv` and are then appended to `writebw.csv` without comment lines and empty lines. `done` ends the loop of line 95. |
| 97 | `for cfg in "asmwrite 8M 1" "asmwrite 8M 4" "asmwrite 8M 14" "asmwrite 1G 1" "asmwrite 1G 14" "asmread 8M 1" "asmread 8M 4" "asmread 8M 14" "asmread 1G 14"; do` | Loop over 9 cases. Each case is a kernel, a buffer size per thread and a thread count: `asmwrite` with 8 MiB and 1, 4 and 14 threads, `asmwrite` with 1 GiB and 1 and 14 threads, `asmread` with 8 MiB and 1, 4 and 14 threads, and `asmread` with 1 GiB and 14 threads. |
| 98 | `    set -- $cfg; k=$1; bytes=$2; t=$3` | Splits the case into its three words. `set --` makes them the arguments `$1`, `$2` and `$3`. `k`: the kernel. `bytes`: the buffer size. `t`: the thread count. |
| 99 | `    for set in $SETS; do` | Loop over the 5 event sets. |
| 100 | `        counted "$OUT/writebw.csv" "$k-$bytes-$t" "$set" --threads $t --cpus 0-119 --bytes $bytes --kernel $k` | Runs the case under the counters of this set (`counted`): a short and a long run. The tag is `KERNEL-SIZE-THREADS`. `--cpus 0-119`: `bandwidth` pins thread number `i` to entry `i` of the list, so the `t` threads sit on the CPUs 0 to `t - 1`, all on mesh 0. So each case runs 10 times: 5 sets times 2 lengths. |
| 101 | `    done` | Ends the loop of line 99. |
| 102 | `done` | Ends the loop of line 97. |
| 103 | `}` | Ends the group of part 3. |

### Part 4: 64 threads on one mesh or split over both meshes (lines 105 to 120)

| Line | Source | Explanation |
|---:|---|---|
| 105 | `part 4 && {` | Part 4 runs when `PARTS` holds `4`. |
| 106 | `echo "== 4. DRAM write collapse with writers on both meshes: home-node counters"; date -u` | Prints the title of part 4 and the UTC date and time. |
| 107 | `# followup3 (2026-11-02): 64 writers on mesh 0 alone write 394 GB/s, 32 on each mesh write 173 GB/s, reads do not collapse.` | Comment: a result of the script `run_followup3.sh` of 2026-11-02, as the comment gives it: 64 writers on mesh 0 alone write 394 GB/s, 32 writers on each mesh write 173 GB/s, and reads do not collapse. |
| 108 | `: > "$OUT/crossmesh.csv"` | Creates `crossmesh.csv` as an empty file. |
| 109 | `SETS4="hns_pocq_reqs_recvd_write,hns_pocq_retry_write hns_pocq_reqs_recvd_rnf,hns_mc_reqs_remote_all hns_pocq_reqs_recvd_ccgrn,hns_mc_reqs_local_all hns_sn_throttle_write,hns_mc_retries_remote_all"` | `SETS4`: the 4 event sets of part 4, with 2 event names each. By the notes of the project they pair a request count with a count of overload: write requests with write retries, requests from cores (`rnf`) with remote memory requests, requests from the gateway to the other mesh (`ccgrn`) with local memory requests, and write throttles at the memory nodes (`sn`) with remote retries [Ref4]. |
| 110 | `echo "-- background control, 2 s idle" >> "$OUT/crossmesh.csv"` | Appends a title line for the idle control: 2 s without a benchmark. |
| 111 | `for set in $SETS4; do ev=""; for e in ${set//,/ }; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done` | Loop over the 4 event sets. The event list `ev` is built as in line 80. |
| 112 | `    guard perf stat -a -x, -e "$ev" -o "$OUT/perf-idle4-${set%%,*}.csv" -- sleep 2; grep -v '^#' "$OUT/perf-idle4-${set%%,*}.csv" \| grep . >> "$OUT/crossmesh.csv"; done` | Counts the events for 2 s while only `sleep 2` runs. The counts go to a file `perf-idle4-EVENT.csv` and are appended to `crossmesh.csv`. `done` ends the loop of line 111. |
| 113 | `for cfg in "asmwrite 0-63 64" "asmwrite 0-31,64-95 64" "asmread 0-31,64-95 64"; do` | Loop over 3 cases. Each case is a kernel, a CPU list and a thread count: `asmwrite` on `0-63`, `asmwrite` on `0-31,64-95`, and `asmread` on `0-31,64-95`, each with 64 threads. |
| 114 | `    set -- $cfg; k=$1; cpus=$2; t=$3` | Splits the case into its three words: the kernel `k`, the CPU list `cpus` and the thread count `t`. |
| 115 | `    for set in $SETS4; do` | Loop over the 4 event sets. |
| 116 | `        counted "$OUT/crossmesh.csv" "cross-$k-${cpus//,/_}" "$set" --threads $t --cpus $cpus --bytes 256M --kernel $k` | Runs the case under the counters of this set (`counted`): a short and a long run with 256 MiB per thread. With the list `0-63` all 64 threads sit on mesh 0. With `0-31,64-95` the first 32 threads sit on the CPUs 0 to 31 (mesh 0) and the other 32 on the CPUs 64 to 95 (mesh 1). The tag is `cross-`, the kernel and the CPU list with `_` in the place of the comma (`${cpus//,/_}`). |
| 117 | `    done` | Ends the loop of line 115. |
| 118 | `done` | Ends the loop of line 113. |
| 119 | `}` | Ends the group of part 4. |

### Function `counted2`: a counter run with a given scope and event list (lines 121 to 132)

| Line | Source | Explanation |
|---:|---|---|
| 121 | `# counted2 <csv> <tag> <label> <perf opts> <-e string> -- bandwidth args: like counted(), but the event` | Comment: `counted2` takes the CSV file, a tag, a label of the event set, the options for `perf`, the event list, and then the arguments for `bandwidth`. It works like `counted`. The sentence goes on in line 122. |
| 122 | `# string and the perf scope (-a, or -C 2 for the core PMU) are given in full.` | Comment: but the caller gives the complete event list and the scope of `perf`: `-a`, or `-C 2` for the counter unit of the core. |
| 123 | `counted2() {` | Starts the function `counted2`. |
| 124 | `    local csv=$1 tag=$2 label=$3 popts=$4 ev=$5; shift 5` | `csv`, `tag`, `label`, `popts`, `ev`: the first five arguments. `shift 5` removes them, so `$@` holds only the arguments for `bandwidth`. |
| 125 | `    for len in short long; do` | Loop: first the short run, then the long run. |
| 126 | `        local ms=200; [[ $len == long ]] && ms=2000` | `ms`: 200 ms for the short run and 2000 ms for the long run. |
| 127 | `        echo "-- $tag $len set $label events $ev args $*" >> "$csv"` | Appends a title line to the CSV file: the tag, `short` or `long`, the label of the set, the event list and the arguments of `bandwidth`. |
| 128 | `        guard perf stat $popts -x, -e "$ev" -o "$OUT/perf5-$tag-$len-$label.csv" -- "$B" "$@" --reps 1 --min-ms $ms >> "$csv"` | Runs `perf stat` under `guard`, with the scope option of the set (`$popts`). The counts go to a file `perf5-TAG-LEN-LABEL.csv`. The command is `bandwidth` with the given arguments and one timed interval of at least `ms` milliseconds. Its output is appended to the CSV file. |
| 129 | `        grep -v '^#' "$OUT/perf5-$tag-$len-$label.csv" \| grep . >> "$csv"` | Appends the counts to the same CSV file, without comment lines and empty lines. |
| 130 | `    done` | Ends the loop of line 125. |
| 131 | `}` | Ends the function `counted2`. |

### Part 5: the crosspoint, the check of the event names and three helper functions (lines 133 to 150)

| Line | Source | Explanation |
|---:|---|---|
| 133 | `part 5 && {` | Part 5 runs when `PARTS` holds `5`. The default `1234` does not hold it. |
| 134 | `echo "== 5. single-core write path: core, crosspoint and home-queue counters"; date -u` | Prints the title of part 5 and the UTC date and time. |
| 135 | `XP=0x98   # crosspoint of CPUs 2 and 3: x=1, y=3 (node id = x<<7 \| y<<3), core port p1 [results/sudo-20261102T054936Z/core-positions.json, results/cmn-map.txt]` | `XP`: `0x98`, the node id of the crosspoint of the CPUs 2 and 3. A crosspoint is a junction of the mesh. By the comment it lies at `x` 1 and `y` 3, the node id is `x` shifted left by 7 bits plus `y` shifted left by 3 bits, and the two cores are connected to its port `p1`. The comment names two files as the source: `core-positions.json` and `cmn-map.txt`. |
| 136 | `# every event name is checked in sysfs first; a missing name stops the part before any measurement` | Comment: every event name is checked in the system files of Linux (sysfs) first. A name that is missing stops the part before any measurement. |
| 137 | `need_cmn="hns_qos_pocq_occupancy_write hns_qos_pocq_occupancy_all dtc_cycles mxp_n_dat_txflit_valid mxp_s_dat_txflit_valid mxp_e_dat_txflit_valid mxp_w_dat_txflit_valid mxp_n_dat_txflit_stall mxp_s_dat_txflit_stall mxp_e_dat_txflit_stall mxp_w_dat_txflit_stall mxp_p1_req_txflit_valid mxp_p1_rsp_txflit_valid mxp_p1_snp_txflit_valid mxp_p1_dat_txflit_valid mxp_p1_rsp_txflit_stall mxp_p1_dat_txflit_stall mxp_n_req_txflit_valid mxp_e_req_txflit_valid"` | `need_cmn`: the 19 event names of the mesh that part 5 uses. 2 are occupancy counts of the home node queues, 1 is `dtc_cycles`, the cycle counter of the mesh, and 16 start with `mxp`, the events of a crosspoint. |
| 138 | `need_core="l1d_cache l1d_cache_refill l1d_cache_wb l2d_cache l2d_cache_refill l2d_cache_wb bus_access mem_access stall_backend_mem bus_cycles"` | `need_core`: the 10 event names of the core that part 5 uses. |
| 139 | `missing=""` | `missing`: the list of names that were not found. It is empty at the start. |
| 140 | `for e in $need_cmn; do [[ -e /sys/bus/event_source/devices/arm_cmn_0/events/$e ]] \|\| missing="$missing arm_cmn_0/$e"; done` | Loop over the mesh names. `-e` tests whether the file of the event exists below `/sys/bus/event_source/devices/arm_cmn_0/events/`. `A \|\| B` runs `B` only when `A` fails. So a name without a file is added to `missing`. |
| 141 | `for e in $need_core; do [[ -e /sys/bus/event_source/devices/armv8_pmuv3_0/events/$e ]] \|\| missing="$missing armv8_pmuv3_0/$e"; done` | The same loop for the core names, below the folder of the PMU `armv8_pmuv3_0`, the counter unit of the cores. |
| 142 | `if [[ -n $missing ]]; then echo "part 5: event names not in sysfs:$missing" >&2; exit 5; fi` | Tests whether `missing` is not empty (`-n`). Then the script prints the names to the error output and ends with exit status 5. |
| 143 | `for e in hns_qos_pocq_occupancy_write dtc_cycles mxp_n_dat_txflit_valid; do echo "event $e: $(cat /sys/bus/event_source/devices/arm_cmn_0/events/$e)"; done` | Prints the description that Linux gives for three of the events, each read with `cat` from its file. So the log shows how this Linux encodes them. |
| 144 | `# event sets. Mesh-wide sets open each name on both meshes (two names per set: distinct event ids 0x0f, 0x14, and the DTC cycle counter).` | Comment: the event sets. A mesh-wide set opens each name on both meshes. It has two names. By the comment their event ids `0x0f` and `0x14` differ, and the cycle counter of the DTC is the third kind. A DTC (debug and trace controller) is the unit of the mesh that holds the counters. |
| 145 | `# Crosspoint sets are four events at XP 0x98 on mesh 0 (one crosspoint has four counters) plus the mesh-0 cycle counter.` | Comment: a crosspoint set is four events at the crosspoint `0x98` on mesh 0, plus the cycle counter of mesh 0. By the comment one crosspoint has four counters. |
| 146 | `# Core sets are six events on CPU 2 (six programmable counters). Raw ids: 0x41 L1D_CACHE_WR, 0x43 L1D_CACHE_REFILL_WR,` | Comment: a core set is six events on CPU 2. By the comment a core has six counters that can be programmed. Then the comment lists raw event numbers: `0x41` is `L1D_CACHE_WR` and `0x43` is `L1D_CACHE_REFILL_WR`. |
| 147 | `# 0x51 L2D_CACHE_WR, 0x53 L2D_CACHE_REFILL_WR, 0x61 BUS_ACCESS_WR, 0x67 MEM_ACCESS_WR (Arm architectural PMU event numbers).` | Comment: `0x51` is `L2D_CACHE_WR`, `0x53` is `L2D_CACHE_REFILL_WR`, `0x61` is `BUS_ACCESS_WR` and `0x67` is `MEM_ACCESS_WR`. By the comment these are event numbers of the Arm architecture. `WR` marks the count for writes only. |
| 148 | `xp() { local ev=""; for e in "$@"; do ev="$ev${ev:+,}arm_cmn_0/$e,bynodeid=1,nodeid=$XP/"; done; echo "$ev,arm_cmn_0/dtc_cycles/"; }` | Defines the function `xp`. It builds the event list of a crosspoint set. Each name becomes `arm_cmn_0/NAME,bynodeid=1,nodeid=0x98/`: the event on mesh 0, counted at the node with the id `XP` only. Then it adds `arm_cmn_0/dtc_cycles/`, the cycle counter. `echo` prints the list for the caller. |
| 149 | `both() { local ev=""; for e in "$@"; do ev="$ev${ev:+,}arm_cmn_0/$e/,arm_cmn_1/$e/"; done; echo "$ev"; }` | Defines the function `both`. It builds the event list of a mesh-wide set: each name once for mesh 0 and once for mesh 1, as in line 80. |
| 150 | `core() { local ev=""; for e in "$@"; do ev="$ev${ev:+,}armv8_pmuv3_0/$e/"; done; echo "$ev"; }` | Defines the function `core`. It builds the event list of a core set: each name as `armv8_pmuv3_0/NAME/`, an event of the counter unit of the cores. |

### Part 5: the nine event sets and their scope (lines 151 to 165)

| Line | Source | Explanation |
|---:|---|---|
| 151 | `declare -A SET5 OPT5` | Declares two tables whose entries are found by a name (`declare -A`). `SET5` will hold the event list of each set, and `OPT5` the scope option of `perf` for it. |
| 152 | `SET5[occw]=$(both hns_qos_pocq_occupancy_write dtc_cycles);            OPT5[occw]="-a"` | Set `occw`: the occupancy of the home node queues for writes, and the cycle counter, on both meshes. Scope `-a`: count for the whole system. |
| 153 | `SET5[occa]=$(both hns_qos_pocq_occupancy_all hns_txdat_stall);          OPT5[occa]="-a"` | Set `occa`: the occupancy of the home node queues for all requests, and the event `hns_txdat_stall`, on both meshes. Scope `-a`. |
| 154 | `if [[ ! -e /sys/bus/event_source/devices/arm_cmn_0/events/hns_txdat_stall ]]; then` | Tests whether Linux has no event with the name `hns_txdat_stall` on mesh 0. |
| 155 | `    echo "part 5: hns_txdat_stall is not an event name here; the occa set counts occupancy_all alone" >&2` | Then prints to the error output that the name does not exist here and that the set `occa` counts the occupancy alone. |
| 156 | `    SET5[occa]=$(both hns_qos_pocq_occupancy_all)` | Then builds the set `occa` again, with the occupancy event only. |
| 157 | `fi` | Ends the `if` of line 154. |
| 158 | `SET5[xpdat]=$(xp mxp_n_dat_txflit_valid mxp_s_dat_txflit_valid mxp_e_dat_txflit_valid mxp_w_dat_txflit_valid);  OPT5[xpdat]="-a"` | Set `xpdat`: the data flits that the crosspoint `0x98` sends on its four mesh links: north, south, east and west (`n`, `s`, `e`, `w`). The event names end with `txflit_valid`. Scope `-a`. |
| 159 | `SET5[xpstall]=$(xp mxp_n_dat_txflit_stall mxp_s_dat_txflit_stall mxp_e_dat_txflit_stall mxp_w_dat_txflit_stall); OPT5[xpstall]="-a"` | Set `xpstall`: the same four links with the events that end with `txflit_stall`. By the notes of the project such an event counts the cycles in which a flit had to wait [Ref4]. These are the credit stalls of the header comment (line 17). |
| 160 | `SET5[xpport]=$(xp mxp_p1_req_txflit_valid mxp_p1_rsp_txflit_valid mxp_p1_snp_txflit_valid mxp_p1_dat_txflit_valid); OPT5[xpport]="-a"` | Set `xpport`: the flits that the crosspoint sends on its port `p1`, the port of the two cores, on four channels: request, response, snoop and data (`req`, `rsp`, `snp`, `dat`). |
| 161 | `SET5[xpmix]=$(xp mxp_p1_rsp_txflit_stall mxp_p1_dat_txflit_stall mxp_n_req_txflit_valid mxp_e_req_txflit_valid);   OPT5[xpmix]="-a"` | Set `xpmix`: the waiting cycles of response flits and of data flits on port `p1`, and the request flits sent on the north link and on the east link. |
| 162 | `SET5[core1]=$(core l1d_cache l1d_cache_refill l1d_cache_wb l2d_cache l2d_cache_refill l2d_cache_wb);               OPT5[core1]="-C 2"` | Set `core1`: accesses, refills and write-backs of the L1 data cache and of the L2 cache. Scope `-C 2`: `perf` counts on CPU 2 only [Ref1]. |
| 163 | `SET5[core2]=$(core event=0x41 event=0x43 event=0x51 event=0x53 event=0x61 event=0x67);                            OPT5[core2]="-C 2"` | Set `core2`: the six raw events of lines 146 to 147, given by number (`event=0x41` and so on): the write-only variants of L1 access, L1 refill, L2 access, L2 refill, bus access and memory access. Scope `-C 2`. |
| 164 | `SET5[core3]=$(core bus_access mem_access stall_backend_mem bus_cycles cycles instructions);                        OPT5[core3]="-C 2"` | Set `core3`: bus accesses, memory accesses, the event `stall_backend_mem` (the notes of the project call it backend memory stalls [Ref4]), bus cycles, processor cycles and instructions. Scope `-C 2`. |
| 165 | `ORDER5="occw occa xpdat xpstall xpport xpmix core1 core2 core3"` | `ORDER5`: the order in which the 9 sets run. |

### Part 5: the idle controls, the six cases and the end of the script (lines 166 to 180)

| Line | Source | Explanation |
|---:|---|---|
| 166 | `: > "$OUT/writepath.csv"` | Creates `writepath.csv` as an empty file. |
| 167 | `echo "-- background control, 2 s idle" >> "$OUT/writepath.csv"` | Appends a title line for the idle control: 2 s without a benchmark. |
| 168 | `for l in $ORDER5; do` | Loop over the 9 sets. |
| 169 | `    echo "-- idle set $l events ${SET5[$l]}" >> "$OUT/writepath.csv"` | Appends a title line with the label of the set and its event list. |
| 170 | `    guard perf stat ${OPT5[$l]} -x, -e "${SET5[$l]}" -o "$OUT/perf5-idle-$l.csv" -- sleep 2` | Counts the events of the set for 2 s while only `sleep 2` runs, under `guard` and with the scope of the set. The counts go to a file `perf5-idle-LABEL.csv`. |
| 171 | `    grep -v '^#' "$OUT/perf5-idle-$l.csv" \| grep . >> "$OUT/writepath.csv"` | Appends these counts to `writepath.csv`, without comment lines and empty lines. |
| 172 | `done` | Ends the loop of line 168. |
| 173 | `for cfg in "w8M-c2 asmwrite 8M 1 2" "w1G-c2 asmwrite 1G 1 2" "w8M-c2c3 asmwrite 8M 2 2,3" "w8M-c2c4 asmwrite 8M 2 2,4" "w8M-c2c4c6c8 asmwrite 8M 4 2,4,6,8" "r8M-c2 asmread 8M 1 2"; do` | Loop over 6 cases. Each case is a tag, a kernel, a buffer size, a thread count and a CPU list. One `asmwrite` thread on CPU 2 with 8 MiB. One `asmwrite` thread on CPU 2 with 1 GiB. Two `asmwrite` threads on the CPUs 2 and 3. Two on the CPUs 2 and 4. Four on the CPUs 2, 4, 6 and 8. One `asmread` thread on CPU 2 with 8 MiB as the control. |
| 174 | `    set -- $cfg; tag=$1; k=$2; bytes=$3; t=$4; cpus=$5` | Splits the case into its five words: the tag, the kernel `k`, the buffer size `bytes`, the thread count `t` and the CPU list `cpus`. |
| 175 | `    for l in $ORDER5; do` | Loop over the 9 sets. |
| 176 | `        counted2 "$OUT/writepath.csv" "$tag" "$l" "${OPT5[$l]}" "${SET5[$l]}" --threads $t --cpus $cpus --bytes $bytes --kernel $k` | Runs the case under the counters of this set (`counted2`): a short and a long run. `bandwidth` pins thread number `i` to entry `i` of the CPU list. So a thread on CPU 2 exists in every case, and the core sets count on that CPU. |
| 177 | `    done` | Ends the loop of line 175. |
| 178 | `done` | Ends the loop of line 173. |
| 179 | `}` | Ends the group of part 5. |
| 180 | `echo "== done"; date -u; echo "$OUT"` | Prints the title `== done`, the UTC date and time, and the path of the result folder. |

## References

- [Ref1] external source: manual page `perf-stat(1)` (the command runs a program and counts events. `-a` counts on all CPUs of the system. `-C` counts only on the given CPUs. `-x` sets the field separator, `-e` the events and `-o` the output file).
- [Ref2] external source: Linux kernel documentation, page `admin-guide/perf/arm-cmn` (an event counts the sum over all nodes of its type. With `bynodeid=1` and a `nodeid` it counts at one node).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its section "Part 3" names the home node events: write and read requests received, cache access and miss, fill, memory requests (local), memory requests (remote), evictions and snoop-filter hits. Its section "State at 04:15 UTC" explains the filter `hbt` (home-bound traffic).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/perf-measurement-tech.html`: a page of the project on its measurement methods. Its section 3.4 gives the pairs of part 4: write requests with write retries, core requests with remote memory requests, gateway requests with local memory requests, and write throttles of the memory nodes with remote retries. Its word list says that the events `mxp_*_txflit_valid` count flits and that the events `mxp_*_txflit_stall` count the cycles in which a flit waited. Its section 3.4 also names the event `stall_backend_mem` as backend memory stalls.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/crb-memory-hierarchy.html`: the report page of the first tests. Its word list defines the flit (one transfer unit on a mesh link or port) and the credit stall (a sender needs one credit from the receiver for each flit, and a credit-stall cycle is one count of the link event for a stalled flit). Its paragraph that starts with "Corrected on 2026-11-11" says that the mesh cycle counter (event `dtc_cycles`) did count the mesh clock, 2.0 GHz, and that the earlier value of about 6,500 per second was what remained after `analyze_writepath.py` subtracted the count of the idle control from the cycle count.
