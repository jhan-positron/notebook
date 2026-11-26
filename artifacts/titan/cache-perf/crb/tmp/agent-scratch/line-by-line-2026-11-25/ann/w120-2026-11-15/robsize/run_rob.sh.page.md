## Short version: purpose

`run_rob.sh` is the plain start script of the window test: it builds `robsize.c` with `gcc -O2` and runs `robsize` on CPU 2. It writes the output, with head lines for the machine, the compiler and the load, to a file `rob-TIME.csv` in its own folder and prints the step lines at the end. It has none of the checks of `go.sh`, the wrapper for CRB.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **`robsize`**: the window test program of this folder. It measures how many filler instructions of one kind fit in the out-of-order window of one core.
- **Kind**: one sort of filler instruction of `robsize`, chosen with the option `--kind`.
- **N**: the number of filler units after each of the two loads in the loop of `robsize`.
- **Step line**: a comment line of the output that starts with `# step`. It gives the N at which the time per loop pass steps up. A line that starts with `# cut` says where the series was cut before that search.
- **AArch64**: the 64-bit instruction set of Arm. `robsize.c` builds for it only.

## Main flow

1. Go to the folder of the script and set the CPU number and the name of the result file ({L5-9}).
2. Build `robsize` ({L11}).
3. Write four head lines to the screen and to the result file ({L13-18}).
4. Run `robsize` on CPU 2 with the arguments of the script, and copy its output to the result file ({L20}).
5. Append the load after the run, and print the path of the file and the step lines ({L22-25}).

## Behavior a reader must know

- The script does not check the marker file, does not wait for a quiet machine and sets no time limit. On CRB the wrapper `go.sh` does these things.
- The script does not limit the process to the CPUs 0 to 119 with `taskset`. The program itself refuses a CPU number above 119, and it pins itself to the CPU of `--cpu`.
- With `set -e` and `pipefail` a failed build or a failed run of `robsize` stops the script. The lines after the failed command do not run.
- The script itself times nothing. All times in the result file come from `robsize`.
