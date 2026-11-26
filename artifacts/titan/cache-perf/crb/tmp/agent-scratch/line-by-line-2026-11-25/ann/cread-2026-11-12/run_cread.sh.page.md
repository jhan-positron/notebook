## Short version: purpose

`run_cread.sh` is the run script of the cread test on CRB. It builds the benchmark `bandwidth_cread`, writes a build record with the machine code of three read kernels, and then starts 16 processes with one thread each. Each process times the kernels `read`, `asmread` and `cread` at one buffer size on one CPU.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Cread test**: the test that compares the read kernels `read`, `asmread` and `cread` with one thread on CRB.
- **`bandwidth_cread`**: the benchmark binary of this test. The script builds it from the file `bandwidth_cread.c` of the same folder.
- **`read`**: in `bandwidth_cread` the kernel of the function `k_read`: C code with 16 running sums. Each load is followed by an add.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`cread`**: in `bandwidth_cread` the kernel of the function `k_cread`: C code that only loads, written with NEON intrinsics (C functions that map to Arm vector instructions).
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Build record**: the file `probe.txt` that this script writes into the result folder.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **gcc**: the GNU C compiler.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Set the shell options and start the script again under `taskset`, with the CPU list 0 to 119 ({L4-5}).
2. Stop when the marker file exists ({L6-8}).
3. Set the paths and create the result folder ({L9-12}).
4. Build the binary `bandwidth_cread` from `bandwidth_cread.c` ({L13-15}).
5. Write the build record `probe.txt`: the machine state, the compiler, the flags, three checksums and the machine-code listing of `k_cread`, `k_asmread` and `k_read` ({L16-26}).
6. Create the empty output file `cread.csv` ({L27}).
7. Start 16 processes, one after the other: 2 rounds, in each round CPU 0 and then CPU 2, and for each CPU the 4 buffer sizes. Before each process, check the marker file and write a header line to `cread.csv` ({L28-36}).
8. Append the load averages after the last process to `probe.txt` and print the path of the result folder ({L37-38}).

## Behavior a reader must know

- The script builds before it measures. The build of {L15} replaces the binary `bandwidth_cread` in the folder of the script.
- Stops: exit status 3 when the marker file exists at the start or before a process. A failed build, a failed `objdump` or a failed benchmark process also stops the script, with the exit status of that command (`set -e` and `pipefail`, {L4}).
- The marker file is checked before each process, not while a process runs. One process holds at least 4.5 s of timed work: 3 kernels times 3 intervals of at least 0.5 s.
- The script has no pause between two processes and no test of the load. It only records the load average before each process ({L32}).
- Thread placement: the script and its processes may run on the CPUs 0 to 119 only ({L5}). The benchmark pins its one worker thread to CPU 0 or CPU 2. The benchmark does not pin its main thread.
- Order inside each process: `read`, then `asmread`, then `cread`. The benchmark fixes this order, and the script never changes it. Round 2 repeats round 1 in the same order.
- The comment of {L3} says that the script writes only under `$HOME/cache-perf`. The binary is written into the folder of the script. So the comment holds only when the script lies under that folder.
